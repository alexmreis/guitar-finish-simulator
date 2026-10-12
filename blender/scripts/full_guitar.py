"""Full spec-sheet instrument. Run against the existing finish-study scene."""
import bpy,bmesh,json,math,sys,hashlib,struct
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon,delaunay_2d_cdt
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scene import ROOT,CFG,OUTLINE,MANIFEST,PRESETS,color,set_finish,look
F=json.loads((ROOT/'config/full_guitar.json').read_text())
from hardware_layout import layout
LAYOUT=layout(F)
with np.load(ROOT/'geometry/full_guitar/carve-field.npz') as packed_field:
    FIELD={key:packed_field[key] for key in packed_field.files}
SCALE=F['scale_length_mm']/1000;SADDLE_Y=F.get('bridge_saddle_y_mm',-72)/1000;NUT_Y=SADDLE_Y+SCALE
LAST_DISTANCE=SCALE*(1-2**(-F['fret_count']/12));BOARD_END=NUT_Y-LAST_DISTANCE-.008
RADIUS=F['fretboard_radius_mm']/1000;BOARD_TOP=.028
HEAD_ROOT=None;HEAD_MAT=None

def sample_field(x,y,key='height_mm'):
    a=FIELD[key];xx=(x*1000-float(FIELD['x0_mm']))/float(FIELD['step_mm']);yy=(y*1000-float(FIELD['y0_mm']))/float(FIELD['step_mm'])
    ix=max(0,min(a.shape[1]-2,int(math.floor(xx))));iy=max(0,min(a.shape[0]-2,int(math.floor(yy))));tx=max(0,min(1,xx-ix));ty=max(0,min(1,yy-iy))
    val=float((1-ty)*((1-tx)*a[iy,ix]+tx*a[iy,ix+1])+ty*((1-tx)*a[iy+1,ix]+tx*a[iy+1,ix+1]))
    return val/1000 if key=='height_mm' else val

def finish_material(name,hexcolor,metal=0,rough=.3,coat=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=color(hexcolor);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Coat Weight'].default_value=coat;p.inputs['Coat Roughness'].default_value=.12
    m.diffuse_color=color(hexcolor);return m

def mesh_object(name,verts,faces,mat=None,smooth=False,parent=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
    orient=bmesh.new();orient.from_mesh(mesh)
    if orient.edges and all(e.is_manifold for e in orient.edges) and orient.calc_volume(signed=True)<0:
        bmesh.ops.reverse_faces(orient,faces=list(orient.faces));orient.to_mesh(mesh)
    orient.free()
    if mat:o.data.materials.append(mat)
    for p in mesh.polygons:p.use_smooth=smooth
    if parent:o.parent=parent
    return o

def bevel(o,width=.001,segments=3,apply=False):
    m=o.modifiers.new('Rounded machining edges','BEVEL');m.width=width;m.segments=segments
    if apply:bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=m.name)
    return o

def cube(name,loc,size,mat,rounding=.001,parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.location=loc;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if rounding:bevel(o,rounding)
    if parent:o.parent=parent
    return o

def cylinder(name,loc,radius,depth,mat,parent=None,axis=None,vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat)
    if axis:o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(axis))
    if parent:o.parent=parent
    bevel(o,min(.0004,radius/5),3)
    for p in o.data.polygons:p.use_smooth=abs(p.normal.z)<.5
    return o

def line(name,points,radius,mat,parent=None,resolution=3):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=12;curve.bevel_depth=radius;curve.bevel_resolution=resolution
    s=curve.splines.new('POLY');s.points.add(len(points)-1)
    for p,co in zip(s.points,points):p.co=(*co,1)
    o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o);o.data.materials.append(mat)
    if parent:o.parent=parent
    return o

def screw(name,loc,mat,parent=None,axis=None,r=.0016):
    c=cylinder(name,loc,r,.00065,mat,parent,axis,24)
    # Physical recessed drive is represented by a small dark slot.
    slot=cube(name+' drive',tuple(Vector(loc)+(Vector(axis).normalized() if axis else Vector((0,0,1)))*.00038),(.0022,.0004,.00015),BLACK_PLASTIC,.0001,parent)
    if axis:slot.rotation_mode='QUATERNION';slot.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(axis))
    return c

def prism(name,points,zlo,zhi,mat,parent=None):
    n=len(points);verts=[(x,y,z) for z in [zlo,zhi] for x,y in points]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh_object(name,verts,faces,mat,False,parent)

def refined_outline_triangles(points,max_edge=.004):
    # Uniform interior samples and constrained Delaunay retain every silhouette edge.
    coords=[Vector((x,y)) for x,y in points];n=len(coords)
    xs=[x for x,y in points];ys=[y for x,y in points]
    row=0;y=min(ys)+max_edge
    while y<max(ys):
        x=min(xs)+max_edge+(max_edge/2 if row%2 else 0)
        while x<max(xs):
            if sample_field(x,y,'distance_mm')>1.2:coords.append(Vector((x,y)))
            x+=max_edge
        y+=max_edge*math.sqrt(3)/2;row+=1
    output=delaunay_2d_cdt(coords,[(i,(i+1)%n) for i in range(n)],[list(range(n))],1,1e-7,False)
    vertices=[(v.x,v.y) for v in output[0]];clean=[];edges={}
    for face in output[2]:
        assert len(face)==3
        a,b,c=face;va,vb,vc=vertices[a],vertices[b],vertices[c]
        if (vb[0]-va[0])*(vc[1]-va[1])-(vb[1]-va[1])*(vc[0]-va[0])<0:b,c=c,b
        clean.append((a,b,c))
        for u,v in [(a,b),(b,c),(c,a)]:edges.setdefault(tuple(sorted((u,v))),[]).append((u,v))
    boundary=[pairs[0] for pairs in edges.values() if len(pairs)==1]
    print('Uniform carved cap:',len(vertices),'vertices,',len(clean),'triangles',flush=True)
    return vertices,clean,boundary

def apply_carve_normals(body):
    mesh=body.data;mesh.update();normals=[tuple(n.vector) for n in mesh.corner_normals]
    for face in mesh.polygons:
        if abs(face.normal.z)<.45:continue
        for li in face.loop_indices:
            x,y,z=mesh.vertices[mesh.loops[li].vertex_index].co
            if abs(abs(z)-sample_field(x,y))>.00007:continue
            normals[li]=tuple(Vector((-sample_field(x,y,'dx'),-sample_field(x,y,'dy'),1 if z>0 else -1)).normalized())
    mesh.normals_split_custom_set(normals)

def cut(body,loc,size,name):
    print('Routing:',name,flush=True)
    cutter=cube(name+' cutting tool',loc,size,BLACK_PLASTIC,.001)
    bpy.context.view_layer.objects.active=cutter
    if cutter.modifiers:bpy.ops.object.modifier_apply(modifier=cutter.modifiers[0].name)
    bpy.context.view_layer.objects.active=body;m=body.modifiers.new(name,'BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cutter,do_unlink=True)

def build_body():
    points=[(x/1000,y/1000-OUTLINE['height_mm']/2000) for x,y in OUTLINE['points_mm']]
    xy,tris,boundary=refined_outline_triangles(points);n=len(xy);vertices=[(x,y,-sample_field(x,y)) for x,y in xy]+[(x,y,sample_field(x,y)) for x,y in xy]
    faces=[(c,b,a) for a,b,c in tris]+[(a+n,b+n,c+n) for a,b,c in tris]+[(a,b,b+n,a+n) for a,b in boundary]
    body=mesh_object('Guitar Body',vertices,faces,None,True);body.data.materials.append(BODY_MAT);body.data.materials.append(TRANS_BLACK)
    for p in body.data.polygons:p.material_index=0 if p.center.z>0 and p.normal.z>.4 else 1
    print('Carved shell constructed; rounding perimeter',flush=True)
    bevel(body,F['edge_round_mm']/1000,5,True)
    for label,y in [('Neck',LAYOUT['neck_pickup_y_mm']/1000),('Bridge',LAYOUT['bridge_pickup_y_mm']/1000)]:cut(body,(0,y,.016),(.071,.040,.020),label+' pickup route')
    cut(body,(0,LAYOUT['single_pickup_y_mm']/1000,.017),(.075,.019,.016),'Single-width pickup route')
    cut(body,(0,SADDLE_Y-.007,.020),(.088,.044,.009),'Recessed 510 tremolo')
    bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000007);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0000001);boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();body.data.update()
    uv=body.data.uv_layers.new(name='BodyUV')
    for p in body.data.polygons:
        p.use_smooth=True;p.material_index=0 if p.center.z>0 and p.normal.z>.4 else 1
        for li in p.loop_indices:
            v=body.data.vertices[body.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x/(CFG['texture_width_mm']/1000)+.5,v.y/(CFG['texture_height_mm']/1000)+.5)
    body.data.set_sharp_from_angle(angle=math.radians(45));apply_carve_normals(body)
    bm=bmesh.new();bm.from_mesh(body.data);bad=sum(not e.is_manifold for e in bm.edges);volume=bm.calc_volume();bm.free();assert bad==0,f'Carved body nonmanifold edges: {bad}'
    body['nominal_center_mm']=F['body_center_thickness_mm'];body['nominal_rim_mm']=F['body_rim_thickness_mm'];body['maple_top_nominal_mm']=F['maple_top_mm'];body['carve']='Continuous nearest-perimeter smootherstep on front and rear'
    return body,{'body_vertices':len(body.data.vertices),'body_faces':len(body.data.polygons),'nonmanifold_edges':bad,'volume_m3':volume,'center_thickness_mm':F['body_center_thickness_mm'],'nominal_rim_thickness_mm':F['body_rim_thickness_mm'],'edge_round_mm':F['edge_round_mm']}

def board_width(y):return F['nut_width_mm']/1000+(F['last_fret_width_mm']-F['nut_width_mm'])/1000*min(1,max(0,(NUT_Y-y)/LAST_DISTANCE))
def board_z(x):return BOARD_TOP-(RADIUS-math.sqrt(max(0,RADIUS*RADIUS-x*x)))

def flush_inlay(name,x0,x1,y0,y1):
    xs=np.linspace(x0,x1,17);verts=[(float(x),y,board_z(float(x))+.000025) for y in [y0,y1] for x in xs]
    faces=[(i,i+1,i+18,i+17) for i in range(16)]
    return mesh_object(name,verts,faces,INLAY,True)

def build_neck():
    ys=np.linspace(BOARD_END,NUT_Y,90);profile_count=83;vertices=[];stripe=F['walnut_stripe_mm']/1000
    for y in ys:
        half=board_width(y)/2-.0005;distance=NUT_Y-y;first=SCALE*(1-2**(-1/12));twelfth=SCALE/2;alpha=max(0,min(1,(distance-first)/(twelfth-first)));total=(F['neck_thickness_first_mm']+(F['neck_thickness_twelfth_mm']-F['neck_thickness_first_mm'])*alpha)/1000;depth=total-.006
        heel=max(0,min(1,(.205-y)/.060));heel=heel*heel*heel*(heel*(heel*6-15)+10);depth=depth*(1-heel)+(.022+sample_field(0,float(y))-.0012)*heel
        # C profile; physical walnut boundaries remain 2.5 mm wide through the taper.
        xs=sorted(set([float(x) for x in np.linspace(-half,half,79)]+[-.0055-stripe/2,-.0055+stripe/2,.0055-stripe/2,.0055+stripe/2]))
        assert len(xs)==profile_count
        for x in xs:
            back=.022-depth*math.sqrt(max(0,1-(x/half)**2))
            if heel>.8:back=max(back,-sample_field(x,float(y))+.0010)
            vertices.append((x,float(y),back))
    faces=[]
    for j in range(len(ys)-1):
        for i in range(profile_count-1):a=j*profile_count+i;faces.append((a,a+1,a+profile_count+1,a+profile_count))
        faces.append((j*profile_count,(j+1)*profile_count,(j+1)*profile_count+profile_count-1,j*profile_count+profile_count-1))
    faces.extend([tuple(range(profile_count-1,-1,-1)),tuple(range((len(ys)-1)*profile_count,len(ys)*profile_count))]);neck=mesh_object('Three-piece maple / two walnut neck laminations',vertices,faces,MAPLE,True);neck.data.materials.append(WALNUT)
    for p in neck.data.polygons:
        x=p.center.x
        if .0055-stripe/2<abs(x)<.0055+stripe/2:p.material_index=1
    # Fretboard shell: explicit radius rather than a flat plank.
    verts=[];rows=90;cols=32
    for y in ys:
        half=board_width(y)/2
        for x in np.linspace(-half,half,cols+1):verts.append((float(x),float(y),board_z(float(x))))
    n=len(verts);verts += [(x,y,.022) for x,y,z in verts];fs=[]
    for row in range(rows-1):
        for col in range(cols):a=row*(cols+1)+col;b=a+1;c=b+cols+1;d=a+cols+1;fs.extend([(a,b,c,d),(d+n,c+n,b+n,a+n)])
    for row in range(rows-1):
        a=row*(cols+1);b=a+cols+1;fs.append((a,b,b+n,a+n));a+=cols;b+=cols;fs.append((a+n,b+n,b,a))
    fs += [tuple(list(range(cols,-1,-1))+list(range(n,n+cols+1))),tuple(list(range((rows-1)*(cols+1),n))+list(range(2*n-1,n+(rows-1)*(cols+1)-1,-1)))]
    board=mesh_object('9.5 inch radius maple fretboard',verts,fs,MAPLE,True)
    # Narrow black one-ply binding and 2 mm side dots.
    for sign in [-1,1]:
        points=[(sign*board_width(y)/2,float(y),board_z(board_width(y)/2)-.0012) for y in ys];line('Black fretboard binding '+str(sign),points,.00065,BLACK_PLASTIC)
    fret_positions=[]
    for number in range(1,F['fret_count']+1):
        y=NUT_Y-SCALE*(1-2**(-number/12));fret_positions.append(y);half=board_width(y)/2-.00035
        # Elliptical jumbo crown, 2.8 mm along the string direction.
        vv=[];sections=36;profile=10
        for x in np.linspace(-half,half,sections+1):
            for a in np.linspace(0,math.pi,profile):vv.append((float(x),y+F['fret_width_mm']/2000*math.cos(a),board_z(float(x))+.0011*math.sin(a)+.00008))
        ff=[]
        for i in range(sections):
            for j in range(profile-1):a=i*profile+j;ff.append((a,a+profile,a+profile+1,a+1))
            a=i*profile;ff.append((a+profile-1,a+2*profile-1,a+profile,a))
        ff.extend([tuple(range(profile-1,-1,-1)),tuple(range(sections*profile,(sections+1)*profile))]);mesh_object(f'Fret {number:02d} / 2.8 mm stainless',vv,ff,STAINLESS,True)
    for number in [3,5,7,9,15,17,19,21]:
        a=NUT_Y if number==1 else fret_positions[number-2];b=fret_positions[number-1];y=(a+b)/2;available=a-b;half=board_width(y)/2
        height=min(.015,available*.6);width=half*.95;flush_inlay(f'Black block inlay {number}',-width/2,width/2,y-height/2,y+height/2)
    y12=(fret_positions[10]+fret_positions[11])/2;loop_y=y12+.006
    ring=[];steps=64
    for rx,ry in [(.0053,.0073),(.0036,.0056)]:
        for angle in np.linspace(0,2*math.pi,steps,endpoint=False):
            x=rx*math.cos(angle);ring.append((x,loop_y+ry*math.sin(angle),board_z(x)+.000025))
    faces=[(i,(i+1)%steps,(i+1)%steps+steps,i+steps) for i in range(steps)]
    mesh_object('Black Ankh loop / twelfth fret',ring,faces,INLAY,True)
    flush_inlay('Ankh stem',-.0009,.0009,y12-.015,y12+.003)
    flush_inlay('Ankh crossbar',-.0075,.0075,y12-.0019,y12-.0001)
    for number in [3,5,7,9,12,15,17,19,21]:
        y=(fret_positions[number-2]+fret_positions[number-1])/2
        for offset in ([-.0025,.0025] if number==12 else [0]):cylinder('White 2 mm side dot',( -board_width(y)/2-.0004,y+offset,.0246),.001,.00035,WHITE,axis=(-1,0,0),vertices=24)
    nut_mat=finish_material('Black Tusq nut satin polymer','#070807',rough=.5)
    nut=cube('Black Tusq nut',(0,NUT_Y,BOARD_TOP-.0001),(F['nut_width_mm']/1000,.0035,.003),nut_mat,.00045)
    bpy.context.view_layer.objects.active=nut;bpy.ops.object.modifier_apply(modifier=nut.modifiers[0].name)
    for xn,gauge in zip(np.linspace(-.01725,.01725,6),[.046,.036,.026,.016,.011,.009]):
        radius=gauge*.0254/2;z=board_z(float(xn))+.00118+radius+.00020
        cutter=cylinder('Nut slot cutting tool',(float(xn),NUT_Y,z),radius+.00006,.009,nut_mat,axis=(0,1,0),vertices=24)
        bpy.context.view_layer.objects.active=cutter;bpy.ops.object.modifier_apply(modifier=cutter.modifiers[0].name)
        bpy.context.view_layer.objects.active=nut;mod=nut.modifiers.new('Tusq string slot','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;mod.solver='EXACT';bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    return fret_positions

def sync_headstock():
    body=BODY_MAT.node_tree.nodes;head=HEAD_MAT.node_tree.nodes
    for key in ['candidate','preset','bookmatch']:
        HEAD_MAT[key]=BODY_MAT[key]
    head['Gloss clearcoat'].inputs['Specular IOR Level'].default_value=body['Gloss clearcoat'].inputs['Specular IOR Level'].default_value
    for n in body:
        if n.type=='VALUE' and n.name in head:head[n.name].outputs[0].default_value=n.outputs[0].default_value
    for a,b in zip(body['Neutral charcoal palette'].color_ramp.elements,head['Neutral charcoal palette'].color_ramp.elements):b.color=a.color
    head['Transparent perimeter burst'].inputs[2].default_value=body['Transparent perimeter burst'].inputs[2].default_value
    for key in ['Actual wood photograph','Photo-derived figure']:head[key].image=body[key].image
    for socket in ['Scale','Location']:head['Blank placement (translation / rotation)'].inputs[socket].default_value=body['Blank placement (translation / rotation)'].inputs[socket].default_value
    head['Blank rotation about seam center'].inputs['Angle'].default_value=body['Blank rotation about seam center'].inputs['Angle'].default_value

def build_headstock():
    global HEAD_ROOT,HEAD_MAT
    points=[(x/1000,y/1000) for x,y in json.loads((ROOT/'geometry/full_guitar/headstock-outline.json').read_text())['points_mm']]
    HEAD_ROOT=bpy.data.objects.new('Angled headstock assembly / 12 degrees',None);bpy.context.collection.objects.link(HEAD_ROOT);HEAD_ROOT.location=(0,NUT_Y,.019);HEAD_ROOT.rotation_euler.x=-math.radians(F['headstock_angle_deg'])
    HEAD_MAT=BODY_MAT.copy();HEAD_MAT.name='Matching photographed maple headstock veneer';head=prism('Illustrated 4L 2R headstock',points,-.0075,.0075,HEAD_MAT,HEAD_ROOT);head.data.materials.append(MAPLE);bevel(head,.001,4,True)
    bounds=json.loads((ROOT/'geometry/full_guitar/headstock-bounds.json').read_text());lo=np.array(bounds['min_mm'])/1000;hi=np.array(bounds['max_mm'])/1000;center=(lo+hi)/2
    uv=head.data.uv_layers.new(name='BodyUV');burst=head.data.uv_layers.new(name='HeadBurstUV')
    for p in head.data.polygons:
        p.use_smooth=True;p.material_index=0 if p.normal.z>.5 and p.center.z>0 else 1
        for li in p.loop_indices:
            v=head.data.vertices[head.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x/(CFG['texture_width_mm']/1000)+.5,(v.y-center[1])/(CFG['texture_height_mm']/1000)+.5);burst.data[li].uv=((v.x-lo[0])/(hi[0]-lo[0]),(v.y-lo[1])/(hi[1]-lo[1]))
    head.data.set_sharp_from_angle(angle=math.radians(35))
    nodes=HEAD_MAT.node_tree.nodes;edge=nodes['Actual perimeter distance / local half-width'];edge.image=bpy.data.images.load(str(ROOT/'geometry/full_guitar/headstock-distance.png'),check_existing=True);edge.image.colorspace_settings.name='Non-Color'
    hUV=nodes.new('ShaderNodeUVMap');hUV.uv_map='HeadBurstUV';hUV.name='Headstock perimeter UV';HEAD_MAT.node_tree.links.new(hUV.outputs[0],edge.inputs['Vector']);sync_headstock()
    # Left side has four machines; right side has two. All positions are inside the illustrated outline.
    def edges_at(y):
        hits=[]
        for a,b in zip(points,points[1:]+points[:1]):
            if min(a[1],b[1])<=y<max(a[1],b[1]):hits.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        return min(hits),max(hits)
    posts=[]
    for side,ys in [(-1,[.024,.053,.082,.109]),(1,[.027,.060])]:
        for i,y in enumerate(ys):
            lo_x,hi_x=edges_at(y);x=lo_x+.009 if side<0 else hi_x-.009;posts.append((side,x,y))
            cylinder('Tuner mounting bushing',(x,y,.0087),.005,.002,BLACK_METAL,HEAD_ROOT)
            cylinder('Tuner string post / 6 mm',(x,y,.013),.003,.009,BLACK_METAL,HEAD_ROOT)
            cylinder('Circular locking tuner housing',(x,y,-.012),.00775,.009,BLACK_METAL,HEAD_ROOT)
            cylinder('Rear locking wheel',(x,y,-.017),.0068,.003,BLACK_METAL,HEAD_ROOT)
            tab=prism('Tuner fixing tab',[(x,y-.003),(x+side*.01515,y-.004),(x+side*.014,y-.011),(x,y-.008)],-.013,-.011,BLACK_METAL,HEAD_ROOT);bevel(tab,.001)
            screw('Tuner 2.4 mm fixing screw',(x+side*.0078,y-.0078,-.0138),BLACK_METAL,HEAD_ROOT,axis=(0,0,-1),r=.0012)
            cylinder('Tuner button shaft',(x+side*.0155,y,-.012),.00205,.017,BLACK_METAL,HEAD_ROOT,axis=(side,0,0))
            # Button outline comes from the final supplied dimensioned drawing.
            button_profile=json.loads((ROOT/'geometry/full_guitar/tuner-button-outline.json').read_text())['points_mm']
            outward=max(v/1000 for u,v in button_profile);center_x=.03125-outward
            button_points=[(x+side*(center_x+v/1000),y+u/1000) for u,v in button_profile]
            if side<0:button_points=button_points[::-1]
            button=prism('Rounded black metal tuner button',button_points,-.016,-.008,BLACK_METAL,HEAD_ROOT);bevel(button,.0007,4)
    # Truss-rod cover is an exterior component only.
    cover=prism('Black truss rod access cover',[(-.006,.006),(.006,.006),(.004,.035),(-.004,.035)],.0076,.0083,BLACK_PLASTIC,HEAD_ROOT);bevel(cover,.0005)
    screw('Truss cover screw',(0,.010,.0087),BLACK_METAL,HEAD_ROOT,r=.0013)
    bpy.context.view_layer.update()
    return posts

def lathe(name,profile,mat,parent=None,segments=64,knurl=False):
    verts=[]
    for radius,z in profile:
        for i in range(segments):
            a=i*2*math.pi/segments;r=radius*(1+.012*math.cos(32*a)) if knurl and z<.010 else radius;verts.append((r*math.cos(a),r*math.sin(a),z))
    faces=[]
    for j in range(len(profile)-1):
        for i in range(segments):a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    faces += [tuple(range(segments-1,-1,-1)),tuple(range((len(profile)-1)*segments,len(profile)*segments))]
    return mesh_object(name,verts,faces,mat,True,parent)

def build_hardware():
    for label,y in [('Neck',LAYOUT['neck_pickup_y_mm']/1000),('Bridge',LAYOUT['bridge_pickup_y_mm']/1000)]:
        cube('Fishman '+label+' brushed black nickel cover',(0,y,.023),(.070,.038,.011),BRUSHED_NICKEL,.003)
        for x in [-.039,.039]:cube(label+' direct-mount tab',(x,y,.018),(.010,.012,.003),BLACK_METAL,.001);screw(label+' height screw',(x,y,.020),BLACK_METAL,r=.0013)
    cube('Fishman single-width black cover',(0,LAYOUT['single_pickup_y_mm']/1000,.0245),(.069,.016,.008),BLACK_PLASTIC,.0035)
    for x in [-.0355,.0355]:screw('Single-width direct mounting',(x,LAYOUT['single_pickup_y_mm']/1000,.0255),BLACK_METAL,r=.0014)
    # 510 dimensions: 83.5 x 40 plate, 54 mm spread, 56 mm pivot posts.
    cube('Gotoh 510TS-FE1 black baseplate',(0,SADDLE_Y-.007,.0218),(F['bridge_plate_width_mm']/1000,F['bridge_plate_depth_mm']/1000,.0026),BLACK_METAL,.001)
    cube('Gotoh tremolo block',(0,SADDLE_Y-.012,0),(.064,.012,.042),BLACK_METAL,.0007)
    for x in [-F['bridge_pivot_pitch_mm']/2000,F['bridge_pivot_pitch_mm']/2000]:cylinder('510 pivot stud / 10 mm',(x,SADDLE_Y+.010,.0235),F['bridge_stud_diameter_mm']/2000,.004,BLACK_METAL);screw('Pivot hex socket',(x,SADDLE_Y+.010,.0258),BLACK_PLASTIC,r=.002)
    for i,x in enumerate(np.linspace(-F['bridge_string_spread_mm']/2000,F['bridge_string_spread_mm']/2000,6)):
        z=.02758-(RADIUS-math.sqrt(RADIUS*RADIUS-x*x));cube(f'510 saddle {i+1}',(float(x),SADDLE_Y-.002,z),(.0088,.017,.010),BLACK_METAL,.0007)
        for dx in [-.0024,.0024]:screw('Saddle height grub screw',(float(x)+dx,SADDLE_Y+.001,z+.0053),STAINLESS,r=.00065)
        cylinder('Saddle intonation screw',(float(x),SADDLE_Y-.019,z-.0008),.0013,.011,BLACK_METAL,axis=(0,1,0),vertices=24)
    arm=[(.034,SADDLE_Y-.007,.026),(.040,SADDLE_Y+.006,.036),(.059,SADDLE_Y+.055,.043),(.066,SADDLE_Y+.115,.042)];line('Gotoh black tremolo arm / 6 mm',arm,F['bridge_arm_diameter_mm']/2000,BLACK_METAL,resolution=5)
    for x,y,label in [(*[v/1000 for v in LAYOUT['volume_mm']],'Volume push-pull'),(*[v/1000 for v in LAYOUT['tone_mm']],'Tone push-pull')]:
        z=sample_field(x,y);normal=Vector((-sample_field(x,y,'dx'),-sample_field(x,y,'dy'),1)).normalized();root=bpy.data.objects.new(label+' control',None);bpy.context.collection.objects.link(root);root.location=(x,y,z);root.rotation_mode='QUATERNION';root.rotation_quaternion=Vector((0,0,1)).rotation_difference(normal)
        cylinder(label+' mounting washer',(0,0,.0008),.011,.001,BLACK_METAL,root)
        lathe(label+' black dome speed knob',[(.0095,0),(.0095,.002),(.0093,.010),(.0085,.013),(.006,.015),(.002,.016),(.0003,.0162)],BLACK_METAL,root,knurl=True)
    x,y=[v/1000 for v in LAYOUT['selector_mm']];z=sample_field(x,y)
    cube('Freeway HSH selector mounting plate',(x,y,z+.001),(.014,.043,.0018),BLACK_PLASTIC,.005)
    line('Freeway selector slot',[(x,y-.015,z+.0023),(x,y+.015,z+.0023)],.0012,INLAY)
    line('Freeway selector lever',[(x,y-.004,z+.002),(x+.005,y-.008,z+.019)],.0012,BLACK_METAL)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=(x+.005,y-.008,z+.020));tip=bpy.context.object;tip.name='Black selector cap';tip.scale=(.003,.003,.005);tip.data.materials.append(BLACK_PLASTIC)
    # Security locks and barrel jack use the illustrated body edge positions.
    for x,y in [(-.102636,.22387),(0,-.2235)]:
        normal=Vector((0,1 if y>0 else -1,0));cylinder('Schaller security strap lock',(x,y,0),.0055,.008,BLACK_METAL,axis=normal)
    cylinder('Side barrel output jack',(.148,-.121,0),.0065,.014,BLACK_METAL,axis=(1,-.15,0));cylinder('Output jack bore',(.155,-.122,0),.0033,.0005,INLAY,axis=(1,-.15,0))

def rear_cover(name,points,mat):
    xy,tris,boundary=refined_outline_triangles(points,.003)
    verts=[(x,y,-sample_field(x,y)-.0008) for x,y in xy]
    o=mesh_object(name,verts,[tuple(reversed(t)) for t in tris],mat,True)
    solid=o.modifiers.new('Cover thickness','SOLIDIFY');solid.thickness=.0008
    for x,y in points:screw(name+' fastening',(x,y,-sample_field(x,y)-.0013),BLACK_METAL,axis=(0,0,-1),r=.0015)
    return o

def build_rear():
    rear_cover('Black tremolo spring cover',[(-.047,.014),(.047,.014),(.047,-.123),(-.047,-.123)],BLACK_PLASTIC)
    rear_cover('Black electronics cavity cover',[(.057,-.045),(.101,-.054),(.121,-.130),(.079,-.167),(.051,-.142)],BLACK_PLASTIC)
    # Snap-in battery enclosure: exterior approximation rather than invented routing.
    x=-.076;y=-.142;z=-sample_field(x,y)-.001
    cube('Gotoh snap-in rear battery pack',(x,y,z),(.033,.062,.002),BLACK_PLASTIC,.002)
    cube('Battery cover latch',(x,y-.024,z-.0018),(.010,.007,.002),BLACK_PLASTIC,.001)

def build_strings(posts):
    gauges=[.046,.036,.026,.016,.011,.009]
    ordered=posts[:4]+[posts[5],posts[4]]
    for i,(xb,xn,gauge,post) in enumerate(zip(np.linspace(-F['bridge_string_spread_mm']/2000,F['bridge_string_spread_mm']/2000,6),np.linspace(-.01725,.01725,6),gauges,ordered)):
        r=gauge*.0254/2;zn=board_z(float(xn))+.00118+r+.00020;zb=board_z(float(xb))+.00118+r+.00340;side,px,py=post;end=HEAD_ROOT.matrix_world@Vector((px,py,.015))
        line(f'String {i+1} / {gauge:.3f} inch E standard',[(float(xb),SADDLE_Y,zb),(float(xn),NUT_Y,zn),tuple(end)],r,STAINLESS,resolution=3)

def frame_camera(camera,margin=.035):
    scene=bpy.context.scene;scene.camera=camera;bpy.context.view_layer.update()
    objects=[o for o in scene.objects if o.type in ['MESH','CURVE'] and not o.hide_render]
    for iteration in range(30):
        coords=[world_to_camera_view(scene,camera,o.matrix_world@Vector(corner)) for o in objects for corner in o.bound_box]
        if all(margin<c.x<1-margin and margin<c.y<1-margin for c in coords):return
        if camera.data.type=='ORTHO':camera.data.ortho_scale*=1.035
        else:camera.data.lens/=1.035
    raise RuntimeError('Could not frame instrument')

def apply_studio_lighting():
    configured={spec['name'] for spec in F['studio_lights']}
    for obj in list(bpy.context.scene.objects):
        if obj.type=='LIGHT' and obj.name not in configured:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value=F.get('studio_world_strength',.25)
    receivers=bpy.data.collections.get('Hardware reflection receivers') or bpy.data.collections.new('Hardware reflection receivers')
    for obj in bpy.context.scene.objects:
        if obj.type not in ['MESH','CURVE']:continue
        metallic=any(m and m.use_nodes and m.node_tree.nodes.get('Principled BSDF') and m.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value>.4 for m in obj.data.materials)
        if metallic and obj.name not in receivers.objects:receivers.objects.link(obj)
    for spec in F['studio_lights']:
        o=bpy.data.objects.get(spec['name'])
        if o is None:
            bpy.ops.object.light_add(type='AREA');o=bpy.context.object;o.name=spec['name']
        o.location=spec['location'];o.data.energy=spec['energy'];o.data.shape='RECTANGLE';o.data.size=spec['width'];o.data.size_y=spec['height'];o.data.specular_factor=spec['specular_factor'];o.data.diffuse_factor=1;o.visible_glossy=spec.get('visible_glossy',True)
        o.light_linking.receiver_collection=receivers if spec.get('hardware_only') else None
        look(o,(0,.26,0))

def configure_studio():
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=F['samples'];scene.cycles.use_denoising=True;scene.cycles.seed=17
    for o in list(scene.objects):
        if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
    apply_studio_lighting()
    center=.25
    for name,loc,target,lens,ortho in [('Full Front',(0,center,2.2),(0,center,0),50,1.06),('Full Perspective',(.7,-.52,1.65),(0,center,0),85,None),('Full Rear',(0,center,-2.2),(0,center,0),50,1.06),('Carve Detail',(.43,-.50,.64),(0,-.02,0),70,None)]:
        bpy.ops.object.camera_add(location=loc);cam=bpy.context.object;cam.name=name;look(cam,target);cam.data.lens=lens
        if ortho:cam.data.type='ORTHO';cam.data.ortho_scale=ortho
        if name=='Full Rear':cam.rotation_euler=(0,math.pi,0)
        if name!='Carve Detail':
            res=F['perspective_resolution'] if name=='Full Perspective' else F['front_resolution'];scene.render.resolution_x,scene.render.resolution_y=res;frame_camera(cam)
    scene.camera=bpy.data.objects['Full Front'];scene.render.resolution_x,scene.render.resolution_y=F['front_resolution'];scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.resolution_percentage=100

def full_signature():
    values=[]
    for o in sorted(bpy.context.scene.objects,key=lambda o:o.name):
        if o.type=='MESH':
            blob=b''.join(struct.pack('<fff',*v.co) for v in o.data.vertices)+b''.join(struct.pack('<I',v) for p in o.data.polygons for v in p.vertices)+b''.join(struct.pack('<fff',*n.vector) for n in o.data.corner_normals)
            for uv in o.data.uv_layers:blob+=b''.join(struct.pack('<ff',*v.uv) for v in uv.data)
            data=hashlib.sha256(blob).hexdigest();modifiers=[(m.type,getattr(m,'width',None),getattr(m,'segments',None),getattr(m,'thickness',None)) for m in o.modifiers];values.append((o.name,o.type,data,modifiers,[list(r) for r in o.matrix_world],o.hide_render))
        elif o.type=='CURVE':values.append((o.name,o.type,[[list(p.co) for p in s.points] for s in o.data.splines],o.data.bevel_depth,[list(r) for r in o.matrix_world]))
        elif o.type=='LIGHT':values.append((o.name,o.type,o.data.energy,o.data.size,o.data.size_y,o.data.specular_factor,o.data.diffuse_factor,o.visible_glossy,o.light_linking.receiver_collection.name if o.light_linking.receiver_collection else None,list(o.data.color),[list(r) for r in o.matrix_world]))
        elif o.type=='CAMERA':values.append((o.name,o.type,o.data.lens,o.data.ortho_scale,[list(r) for r in o.matrix_world]))
    scene=bpy.context.scene;values.append(('color_management',scene.view_settings.view_transform,scene.view_settings.look,scene.view_settings.exposure,scene.view_settings.gamma));values.append(('world',list(scene.world.node_tree.nodes['Background'].inputs[0].default_value),scene.world.node_tree.nodes['Background'].inputs[1].default_value))
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()

def build_full():
    global BODY_MAT,MAPLE,WALNUT,BLACK_METAL,BLACK_PLASTIC,TRANS_BLACK,INLAY,STAINLESS,WHITE,BRUSHED_NICKEL
    BODY_MAT=bpy.data.materials['Photo wood / stain / perimeter burst / clearcoat']
    BODY_MAT.node_tree.nodes['UV to physical millimeters'].inputs[1].default_value=(CFG['texture_width_mm'],CFG['texture_height_mm'],1)
    for o in list(bpy.context.scene.objects):
        if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
    MAPLE=finish_material('Satin maple neck and fretboard','#D5B77E',rough=.42);WALNUT=finish_material('Walnut lamination stripes','#493021',rough=.4)
    BLACK_METAL=finish_material('Black finished hardware','#202326',metal=.92,rough=.23);BLACK_PLASTIC=finish_material('Black polymer and binding','#0A0B0C',rough=.30)
    TRANS_BLACK=finish_material('Gloss trans-black rear and sides visual approximation','#0B0E0E',rough=.25,coat=1);INLAY=finish_material('Black block and Ankh inlay','#030404',rough=.58);INLAY.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.2
    STAINLESS=finish_material('Stainless frets and strings','#9EA5AA',metal=1,rough=.18);WHITE=finish_material('White side dots','#E4E6D6',rough=.35)
    BRUSHED_NICKEL=finish_material('Fishman brushed black nickel','#32363A',metal=.9,rough=.34);BRUSHED_NICKEL.node_tree.nodes['Principled BSDF'].inputs['Anisotropic'].default_value=.5
    body,report=build_body();print('Body validated; constructing neck',flush=True);frets=build_neck();print('Constructing headstock and hardware',flush=True);posts=build_headstock();build_hardware();build_rear();build_strings(posts)
    set_finish(F['default_preset'],next(c for c in MANIFEST if c['source_filename']==F['default_candidate']));sync_headstock();configure_studio()
    bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
    bpy.ops.wm.obj_export(filepath=str(ROOT/'geometry/full_guitar/carved_body.obj'),export_selected_objects=True,export_materials=False)
    bpy.ops.file.pack_all()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.region_3d.view_distance=1.4
    bpy.context.scene['geometry_generated_once']=True
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/full_guitar.blend'))
    report.update(blender_version=bpy.app.version_string,engine=bpy.context.scene.render.engine,scale_length_mm=F['scale_length_mm'],frets=len(frets),nut_width_mm=F['nut_width_mm'],last_fret_width_mm=F['last_fret_width_mm'],fretboard_radius_mm=F['fretboard_radius_mm'],tuners_left=sum(p[0]<0 for p in posts),tuners_right=sum(p[0]>0 for p in posts),string_count=6,bridge_width_mm=F['bridge_plate_width_mm'],bridge_string_spread_mm=F['bridge_string_spread_mm'],samples=F['samples'],assumptions=F['assumptions'],geometry_signature=full_signature())
    (ROOT/'geometry/full_guitar/model-validation.json').write_text(json.dumps(report,indent=2));print('FULL GUITAR VALIDATED',report)

if __name__=='__main__':build_full()
