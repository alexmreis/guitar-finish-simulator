"""Blender scene and adjustable photo-derived finish material."""
import bpy, bmesh, json, math, hashlib, struct, os
from surface_normals import apply as apply_surface_normals
from pathlib import Path
from mathutils import Vector
ROOT=Path(os.environ.get('GFS_PROJECT_ROOT',Path(__file__).resolve().parents[2])).resolve()
CFG=json.loads((ROOT/'config/project.json').read_text())
OUTLINE=json.loads((ROOT/'geometry/outline.json').read_text())
MANIFEST=json.loads((ROOT/'assets/textures/processed/manifest.json').read_text())
PRESETS=json.loads((ROOT/'config/finishes.json').read_text())
CY=OUTLINE['height_mm']/2000

def color(hexcolor):
    rgb=[int(hexcolor[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb)+(1,)

def image_node(nodes,path,name,noncolor=False):
    n=nodes.new('ShaderNodeTexImage'); n.name=name; n.label=name
    n.image=bpy.data.images.load(str(path),check_existing=True)
    n.image.filepath=str(path)
    if noncolor: n.image.colorspace_settings.name='Non-Color'
    n.extension='EXTEND'
    return n

def material():
    m=bpy.data.materials.new('Photo wood / stain / perimeter burst / clearcoat'); m.use_nodes=True
    ns=m.node_tree.nodes; ns.clear(); links=m.node_tree.links
    def node(kind,name):
        n=ns.new(kind); n.name=name; n.label=name; return n
    def wire(a,b): links.new(a,b)
    def mathnode(op,name,a,b=None):
        n=node('ShaderNodeMath',name); n.operation=op
        if hasattr(a,'bl_idname'): wire(a,n.inputs[0])
        else: n.inputs[0].default_value=a
        if b is not None:
            if hasattr(b,'bl_idname'): wire(b,n.inputs[1])
            else: n.inputs[1].default_value=b
        return n.outputs[0]
    def control(name,val):
        n=node('ShaderNodeValue',name); n.outputs[0].default_value=val; return n.outputs[0]
    uv=node('ShaderNodeUVMap','Fixed body UV'); uv.uv_map='BodyUV'
    center=node('ShaderNodeVectorMath','Center blank coordinates'); center.operation='SUBTRACT'; center.inputs[1].default_value=(.5,.5,0); wire(uv.outputs[0],center.inputs[0])
    domain=node('ShaderNodeVectorMath','UV to physical millimeters'); domain.operation='MULTIPLY'; domain.inputs[1].default_value=(CFG['texture_width_mm'],CFG['texture_height_mm'],1); wire(center.outputs[0],domain.inputs[0])
    rotation=node('ShaderNodeVectorRotate','Blank rotation about seam center'); rotation.rotation_type='Z_AXIS'; wire(domain.outputs[0],rotation.inputs['Vector'])
    mapping=node('ShaderNodeMapping','Blank placement (translation / rotation)'); wire(rotation.outputs[0],mapping.inputs['Vector'])
    wood=image_node(ns,ROOT/'assets/textures/bookmatched'/f"{MANIFEST[0]['source_filename']}.png",'Actual wood photograph')
    figure=image_node(ns,ROOT/'assets/textures/processed'/f"{MANIFEST[0]['source_filename']}.figure.png",'Photo-derived figure',True)
    for n in (wood,figure): wire(mapping.outputs['Vector'],n.inputs['Vector'])
    distance=image_node(ns,ROOT/'geometry/perimeter-distance.png','Actual perimeter distance / local half-width',True); wire(uv.outputs[0],distance.inputs['Vector'])
    controls={name:control(name,value) for name,value in PRESETS['prs_reference'].items() if isinstance(value,(int,float))}
    # Contrast around middle gray, then sandback raises lighter photographed figure.
    f=mathnode('SUBTRACT','Figure midpoint',figure.outputs['Color'],.5)
    f=mathnode('MULTIPLY','Figure contrast',f,controls['figure_contrast'])
    f=mathnode('ADD','Figure offset',f,.5)
    f=mathnode('MAXIMUM','Clamp figure low',f,0); f=mathnode('MINIMUM','Clamp figure high',f,1)
    exponent=mathnode('SUBTRACT','Sandback exponent',2.4,controls['sandback_strength'])
    f=mathnode('POWER','Sandback approximation',f,exponent)
    ramp=node('ShaderNodeValToRGB','Neutral charcoal palette'); wire(f,ramp.inputs[0]); ramp.color_ramp.interpolation='EASE'
    colors=[(0,'#08090A'),(.45,'#18191B'),(.8,'#64676C'),(1,'#888B90')]
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    for i,(pos,col) in enumerate(colors):
        e=ramp.color_ramp.elements[0] if i==0 else ramp.color_ramp.elements.new(pos); e.position=pos; e.color=color(col)
    brightness=mathnode('MULTIPLY','Highlight and darkness',controls['highlight_brightness'],controls['overall_darkness'])
    dim=node('ShaderNodeMixRGB','Stain brightness'); dim.blend_type='MULTIPLY'; dim.inputs[0].default_value=1
    wire(ramp.outputs[0],dim.inputs[1]); wire(brightness,dim.inputs[2])
    warmth=node('ShaderNodeMixRGB','Warmth from actual maple'); wire(controls['warmth'],warmth.inputs[0]); wire(dim.outputs[0],warmth.inputs[1]); wire(wood.outputs['Color'],warmth.inputs[2])
    stain=node('ShaderNodeMixRGB','Black dye / natural blend'); wire(controls['dye_intensity'],stain.inputs[0]); wire(wood.outputs[0],stain.inputs[1]); wire(warmth.outputs[0],stain.inputs[2])
    width=mathnode('MULTIPLY','Burst transition position',controls['burst_width'],controls['transition_position'])
    width=mathnode('MAXIMUM','Nonzero burst width',width,.0001)
    effective=mathnode('SUBTRACT','Distance after solid black edge',distance.outputs['Color'],controls['edge_hold'])
    effective=mathnode('MAXIMUM','Clamp edge plateau',effective,0)
    transition=mathnode('SUBTRACT','Burst transition length',width,controls['edge_hold'])
    transition=mathnode('MAXIMUM','Nonzero transition',transition,.0001)
    inward=mathnode('DIVIDE','Nearest edge / burst width',effective,transition)
    inward=mathnode('MINIMUM','Limit inward distance',inward,1)
    # Smoothstep 3t^2-2t^3, inverted toward the perimeter.
    square=mathnode('MULTIPLY','Distance squared',inward,inward)
    factor=mathnode('SUBTRACT','Smoothstep factor',3,mathnode('MULTIPLY','2t',inward,2))
    smooth=mathnode('MULTIPLY','Smoothstep',square,factor)
    burst=mathnode('SUBTRACT','Edge gradient',1,smooth)
    burst=mathnode('POWER','Burst falloff',burst,controls['burst_exponent'])
    opacityrange=mathnode('SUBTRACT','Opacity range',controls['edge_opacity'],controls['inner_opacity'])
    burst=mathnode('ADD','Burst opacity',mathnode('MULTIPLY','Opacity gradient',burst,opacityrange),controls['inner_opacity'])
    mix=node('ShaderNodeMixRGB','Transparent perimeter burst'); wire(burst,mix.inputs[0]); wire(stain.outputs[0],mix.inputs[1]); mix.inputs[2].default_value=color('#08090A')
    bsdf=node('ShaderNodeBsdfPrincipled','Gloss clearcoat'); wire(mix.outputs[0],bsdf.inputs['Base Color'])
    for key,socket in [('coat_weight','Coat Weight'),('coat_roughness','Coat Roughness'),('base_roughness','Roughness'),('ior','IOR'),('specular_ior_level','Specular IOR Level')]:
        if key in controls:wire(controls[key],bsdf.inputs[socket])
    bump=node('ShaderNodeBump','Optional restrained photo bump'); wire(controls['bump_strength'],bump.inputs['Strength']); bump.inputs['Distance'].default_value=.00003; wire(figure.outputs[0],bump.inputs['Height']); wire(bump.outputs[0],bsdf.inputs['Normal'])
    output=node('ShaderNodeOutputMaterial','Surface output'); wire(bsdf.outputs[0],output.inputs[0])
    # Legible editable nodes grouped by position; controls in a column.
    for i,n in enumerate(ns): n.location=((i%7)*240,-(i//7)*240)
    for i,k in enumerate(controls): ns[k].location=(-650,-i*100)
    return m

def set_finish(preset,candidate):
    m=bpy.data.materials['Photo wood / stain / perimeter burst / clearcoat']; ns=m.node_tree.nodes
    ns['Gloss clearcoat'].inputs['Specular IOR Level'].default_value=PRESETS[preset].get('specular_ior_level',.5)
    for key,value in PRESETS[preset].items():
        if key in ns and isinstance(value,(float,int)): ns[key].outputs[0].default_value=value
    for element,hexcolor in zip(ns['Neutral charcoal palette'].color_ramp.elements,PRESETS[preset]['palette']): element.color=color(hexcolor)
    ns['Transparent perimeter burst'].inputs[2].default_value=color(PRESETS[preset]['burst_color'])
    name=candidate['source_filename']
    for nodekey,path,noncolor in [('Actual wood photograph',ROOT/'assets/textures/bookmatched'/f'{name}.png',False),('Photo-derived figure',ROOT/'assets/textures/processed'/f'{name}.figure.png',True)]:
        im=bpy.data.images.load(str(path),check_existing=True); im.filepath=str(path)
        if noncolor: im.colorspace_settings.name='Non-Color'
        ns[nodekey].image=im
    # Body UV uses a common physical domain. Aspect is preserved by one isotropic
    # assumed mm/pixel scale per blank; no independent width/height stretching.
    placement=CFG['placements'].get(name,{})
    mapping=ns['Blank placement (translation / rotation)']
    mapping.inputs['Scale'].default_value=(1/candidate['assumed_width_mm'],1/candidate['assumed_height_mm'],1)
    mapping.inputs['Location'].default_value=(.5+placement.get('x_mm',0)/candidate['assumed_width_mm'],.5+placement.get('y_mm',0)/candidate['assumed_height_mm'],0)
    ns['Blank rotation about seam center'].inputs['Angle'].default_value=math.radians(placement.get('rotation_deg',0))
    m['candidate']=name; m['preset']=preset; m['bookmatch']=candidate['status']

def look(obj,point): obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()

def hardware(name,location,size,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location); o=bpy.context.object; o.name=name; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat); mod=o.modifiers.new('Hardware rounded corners','BEVEL'); mod.width=.002; mod.segments=3
    o.hide_render=not CFG['hardware_visible']; return o

def configure_render_defaults():
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=CFG['samples']; scene.cycles.use_denoising=True; scene.cycles.seed=17
    if scene.world is None:scene.world=bpy.data.worlds.new('World')
    scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.12,.12,1); scene.world.node_tree.nodes['Background'].inputs[1].default_value=.25
    scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=0; scene.view_settings.gamma=1
    scene.render.film_transparent=False; scene.render.image_settings.file_format='PNG'; scene.render.resolution_percentage=100; scene.render.resolution_x=scene.render.resolution_y=CFG['comparison_resolution']
    scene.render.image_settings.color_mode='RGBA'; scene.render.image_settings.color_depth='8'
    scene['project_root']=str(ROOT)

def build():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    pts=[(x/1000,y/1000-CY) for x,y in OUTLINE['points_mm']]; n=len(pts); t=CFG['body_thickness_mm']/1000
    vertices=[(x,y,z) for z in (-t/2,t/2) for x,y in pts]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new('Fixed actual silhouette body'); mesh.from_pydata(vertices,[],faces); mesh.update()
    body=bpy.data.objects.new('Guitar Body',mesh); bpy.context.collection.objects.link(body); bpy.context.view_layer.objects.active=body; body.select_set(True)
    bevel=body.modifiers.new('Rounded front and back perimeter','BEVEL'); bevel.width=.0035; bevel.segments=5
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm=bmesh.new(); bm.from_mesh(body.data); bmesh.ops.triangulate(bm,faces=list(bm.faces)); bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True); bmesh.ops.triangulate(bm,faces=list(bm.faces))
    for v in bm.verts:
        x,y,z=v.co
        if z>t/2-.0001:
            # Approximate shallow forearm slope, away from pickup area.
            w=max(0,min(1,(-x-.06)/.10))*max(0,min(1,(.025-y)/.15))
            v.co.z-=.007*w*w
        elif z<-t/2+.0001:
            w=max(0,min(1,(x-.035)/.10))*max(0,min(1,(y+.12)/.16))
            v.co.z+=.006*w*w
    bm.to_mesh(body.data); bm.free(); body.data.update()
    # Two provisional shallow pickup pockets, aligned from the illustration.
    for label,y in [('Neck',.075),('Bridge',-.025)]:
        bpy.ops.mesh.primitive_cube_add(size=1,location=(0,y,t/2-.004)); cutter=bpy.context.object; cutter.dimensions=(.069,.039,.020)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bpy.context.view_layer.objects.active=body; mod=body.modifiers.new(label+' pickup pocket','BOOLEAN'); mod.operation='DIFFERENCE'; mod.object=cutter; mod.solver='EXACT'; bpy.ops.object.modifier_apply(modifier=mod.name); bpy.data.objects.remove(cutter,do_unlink=True)
    repair=bmesh.new(); repair.from_mesh(body.data)
    bmesh.ops.remove_doubles(repair,verts=list(repair.verts),dist=.000001)
    bmesh.ops.dissolve_degenerate(repair,edges=list(repair.edges),dist=.0000001)
    boundary=[e for e in repair.edges if e.is_boundary]
    if boundary: bmesh.ops.holes_fill(repair,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(repair,faces=list(repair.faces))
    repair.to_mesh(body.data); repair.free()
    uv=body.data.uv_layers.new(name='BodyUV')
    for poly in body.data.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            v=body.data.vertices[body.data.loops[li].vertex_index].co
            uv.data[li].uv=(v.x/(CFG['texture_width_mm']/1000)+.5,v.y/(CFG['texture_height_mm']/1000)+.5)
    body.data.set_sharp_from_angle(angle=math.radians(35))
    apply_surface_normals(body,t)
    body.data.materials.clear(); body.data.materials.append(material())
    for poly in body.data.polygons: poly.material_index=0
    bm=bmesh.new(); bm.from_mesh(body.data)
    invalid=sum(not e.is_manifold for e in bm.edges); bm.free(); assert invalid==0,f'{invalid} nonmanifold edges'
    metal=bpy.data.materials.new('Neutral dark hardware'); metal.diffuse_color=(.035,.04,.045,1); metal.use_nodes=True; metal.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.8
    for label,y in [('Neck',.075),('Bridge',-.025)]: hardware(label+' pickup',(0,y,t/2+.002),(.067,.037,.012),metal)
    hardware('Middle single coil',(0,.026,t/2+.006),(.074,.018,.011),metal)
    hardware('Bridge',(0,-.081,t/2+.006),(.073,.037,.014),metal)
    for x,y in [(.076,-.073),(.109,-.127)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.009,depth=.014,location=(x,y,t/2+.008)); o=bpy.context.object; o.name='Control knob'; o.data.materials.append(metal); o.hide_render=not CFG['hardware_visible']
    for name,loc,target,lens in [('Front',(0,0,1.2),(0,0,0),50),('Perspective',(.58,-.67,.86),(0,0,0),65),('Detail',(.08,-.06,.55),(0,-.035,0),75)]:
        bpy.ops.object.camera_add(location=loc); cam=bpy.context.object; cam.name=name; look(cam,target); cam.data.lens=lens
        if name=='Front': cam.data.type='ORTHO'; cam.data.ortho_scale=.54
    for name,loc,power,size in [('Softbox key',(-.38,.28,.75),15,.55),('Subtle fill',(.4,-.15,.65),5,.5),('Edge softbox',(.08,.42,.4),7,.35)]:
        bpy.ops.object.light_add(type='AREA',location=loc); o=bpy.context.object; o.name=name; o.data.energy=power; o.data.shape='RECTANGLE'; o.data.size=size; o.data.size_y=size*.55; look(o,(0,0,0))
    scene=bpy.context.scene;scene.camera=bpy.data.objects['Front'];configure_render_defaults();scene['geometry_generated_once']=True
    bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active=body
    bpy.ops.wm.obj_export(filepath=str(ROOT/'geometry/body_mesh.obj'),export_selected_objects=True,export_materials=False)
    set_finish('prs_reference' if 'prs_reference' in PRESETS else next(iter(PRESETS)),MANIFEST[min(4,len(MANIFEST)-1)])
    # Pack source images for a portable, editable saved scene.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.region_3d.view_distance=.75
                area.spaces.active.region_3d.view_location=(0,0,0)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/guitar.blend'))
    validation={'blender_version':bpy.app.version_string,'render_engine':scene.render.engine,'vertices':len(body.data.vertices),'faces':len(body.data.polygons),'nonmanifold_edges':invalid,'width_mm':CFG['body_width_mm'],'thickness_mm':CFG['body_thickness_mm'],'samples':scene.cycles.samples,'seed':17,'resolution':CFG['comparison_resolution'],'view_transform':scene.view_settings.view_transform,'exposure':0,'hardware_visible':CFG['hardware_visible']}
    (ROOT/'geometry/mesh-validation.json').write_text(json.dumps(validation,indent=2))
    print('SCENE VALIDATED',validation)

def signature():
    body=bpy.data.objects['Guitar Body']; scene=bpy.context.scene
    normal_hash=hashlib.sha256(b''.join(struct.pack('<fff',*normal.vector) for normal in body.data.corner_normals)).hexdigest()
    data={'normal_hash':normal_hash,'vertices':[list(v.co) for v in body.data.vertices],'polygons':[list(p.vertices) for p in body.data.polygons],'uv':[list(d.uv) for d in body.data.uv_layers['BodyUV'].data],'sharp_edges':[e.use_edge_sharp for e in body.data.edges],'smooth_faces':[p.use_smooth for p in body.data.polygons],'body_matrix':[list(row) for row in body.matrix_world],
      'camera_matrix':[list(row) for row in scene.camera.matrix_world],'camera_type':scene.camera.data.type,'ortho_scale':scene.camera.data.ortho_scale,'lens':scene.camera.data.lens,'exposure':scene.view_settings.exposure,'view_transform':scene.view_settings.view_transform,
      'look':scene.view_settings.look,'gamma':scene.view_settings.gamma,'world_color':list(scene.world.node_tree.nodes['Background'].inputs[0].default_value),'world_strength':scene.world.node_tree.nodes['Background'].inputs[1].default_value,'hardware_visibility':[(o.name,o.hide_render) for o in scene.objects if o.type=='MESH' and o!=body],
      'lights':[(o.name,[list(row) for row in o.matrix_world],o.data.energy,o.data.size,o.data.size_y) for o in scene.objects if o.type=='LIGHT']}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
