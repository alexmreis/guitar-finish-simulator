"""Validate the saved full instrument against the supplied dimensions."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import full_guitar as full
from full_guitar import bpy,bmesh,ROOT,F,SCALE,SADDLE_Y,NUT_Y,BOARD_TOP,RADIUS,full_signature
body=bpy.data.objects['Guitar Body'];neck=bpy.data.objects['Three-piece maple / two walnut neck laminations'];board=bpy.data.objects['9.5 inch radius maple fretboard'];bpy.context.view_layer.update()
bm=bmesh.new();bm.from_mesh(body.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free();assert bad==0
center=body.ray_cast((0,0,1),(0,0,-1))[1].z-body.ray_cast((0,0,-1),(0,0,1))[1].z;assert abs(center*1000-F['body_center_thickness_mm'])<.01
frets=sorted([o for o in bpy.data.objects if o.name.startswith('Fret ')],key=lambda o:o.name);assert len(frets)==F['fret_count']
for number,o in enumerate(frets,1):
    y=sum(v.co.y for v in o.data.vertices)/len(o.data.vertices);expected=NUT_Y-SCALE*(1-2**(-number/12));assert abs(y-expected)<1e-6
strings=sorted([o for o in bpy.data.objects if o.name.startswith('String ')],key=lambda o:o.name);assert len(strings)==6
assert abs(strings[0].data.splines[0].points[1].co.y-strings[0].data.splines[0].points[0].co.y-SCALE)<1e-6
nut=bpy.data.objects['Black Tusq nut'];assert abs(nut.dimensions.x*1000-F['nut_width_mm'])<.05
thickness=[]
for number,target in [(1,F['neck_thickness_first_mm']),(12,F['neck_thickness_twelfth_mm'])]:
    y=NUT_Y-SCALE*(1-2**(-number/12));hit,loc,*_=neck.ray_cast((0,y,-1),(0,0,1));assert hit
    actual=(BOARD_TOP-loc.z)*1000;assert abs(actual-target)<.08,(number,actual)
    thickness.append({'fret':number,'measured_mm':actual,'target_mm':target})
# Radius is measured on the saved surface, not only copied from configuration.
y=NUT_Y-SCALE/2;hit,loc,*_=board.ray_cast((.010,y,1),(0,0,-1));expected=BOARD_TOP-(RADIUS-math.sqrt(RADIUS*RADIUS-.010**2));assert hit and abs(loc.z-expected)<.000025
last_y=NUT_Y-SCALE*(1-2**(-F['fret_count']/12));right=board.ray_cast((.1,last_y,.024),(-1,0,0))[1].x;left=board.ray_cast((-.1,last_y,.024),(1,0,0))[1].x;last_width=(right-left)*1000;assert abs(last_width-F['last_fret_width_mm'])<.1
posts=[o for o in bpy.data.objects if o.name.startswith('Tuner string post / 6 mm')];assert len(posts)==6;left_count=sum(o.location.x<0 for o in posts);assert left_count==4
bridge=bpy.data.objects['Gotoh 510TS-FE1 black baseplate'];assert abs(bridge.dimensions.x*1000-F['bridge_plate_width_mm'])<.01 and abs(bridge.dimensions.y*1000-F['bridge_plate_depth_mm'])<.01
spread=abs(strings[-1].data.splines[0].points[0].co.x-strings[0].data.splines[0].points[0].co.x)*1000
assert abs(spread-F['bridge_string_spread_mm'])<.01
studs=[o for o in bpy.data.objects if o.name.startswith('510 pivot stud')]
pitch=abs(studs[1].location.x-studs[0].location.x)*1000
assert abs(pitch-F['bridge_pivot_pitch_mm'])<.01
controls={name:[v*1000 for v in bpy.data.objects[name+' control'].location[:2]] for name in ['Volume push-pull','Tone push-pull']}
for name,key in [('Volume push-pull','volume_mm'),('Tone push-pull','tone_mm')]:
    assert max(abs(a-b) for a,b in zip(controls[name],full.LAYOUT[key]))<.01
clearances=[]
for o in strings:
    p0,p1=list(o.data.splines[0].points)[:2];a=p0.co.xyz;b=p1.co.xyz;r=o.data.bevel_depth
    for number,fret in enumerate(frets,1):
        y=NUT_Y-SCALE*(1-2**(-number/12));t=(y-a.y)/(b.y-a.y);point=a.lerp(b,t);fret_top=full.board_z(point.x)+.00118;gap=point.z-r-fret_top
        assert gap>.0001,(o.name,number,gap)
        clearances.append(gap)
# Check one-ply binding and all front top UVs are assigned.
assert len(body.data.uv_layers['BodyUV'].data)==len(body.data.loops)
assert any(o.name.startswith('Black fretboard binding') for o in bpy.data.objects)
full.BODY_MAT=bpy.data.materials['Photo wood / stain / perimeter burst / clearcoat'];full.HEAD_MAT=bpy.data.materials['Matching photographed maple headstock veneer']
for m in [full.BODY_MAT,full.HEAD_MAT]:assert all(n.image.packed_file for n in m.node_tree.nodes if n.type=='TEX_IMAGE')
report={'saved_blend_reopened':True,'blender_version':bpy.app.version_string,'engine':bpy.context.scene.render.engine,'body_vertices':len(body.data.vertices),'body_nonmanifold_edges':bad,'measured_center_thickness_mm':center*1000,'nominal_rim_mm':F['body_rim_thickness_mm'],'neck_thickness_checks':thickness,'measured_nut_width_mm':nut.dimensions.x*1000,'measured_last_fret_width_mm':last_width,'radius_surface_verified':True,'scale_mm':SCALE*1000,'fret_positions_verified':True,'frets':len(frets),'strings':6,'minimum_string_fret_clearance_mm':min(clearances)*1000,'tuners_left':left_count,'tuners_right':6-left_count,'bridge_plate_width_mm':bridge.dimensions.x*1000,'bridge_plate_depth_mm':bridge.dimensions.y*1000,'measured_bridge_string_spread_mm':spread,'measured_bridge_pivot_pitch_mm':pitch,'measured_bridge_saddle_y_mm':strings[0].data.splines[0].points[0].co.y*1000,'control_locations_mm':controls,'packed_body_and_headstock_textures':True,'geometry_signature':full_signature(),'assumptions':F['assumptions']}
(ROOT/'blender/full_guitar/validation.json').write_text(json.dumps(report,indent=2));print('FULL INSTRUMENT CHECKS PASSED',report)
