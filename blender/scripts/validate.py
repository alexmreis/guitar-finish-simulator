"""Open saved scene and verify mesh, packed textures, UV coverage, cameras."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scene import *
body=bpy.data.objects['Guitar Body']; bm=bmesh.new(); bm.from_mesh(body.data)
assert all(e.is_manifold for e in bm.edges); bm.free()
assert all(math.isfinite(v) for vert in body.data.vertices for v in vert.co)
assert set(['Front','Perspective','Detail']).issubset(bpy.data.objects.keys())
assert bpy.context.scene.render.engine=='CYCLES'
material=body.data.materials[0]
assert material.use_nodes
saved_preset=material['preset']
saved_palette=[list(element.color) for element in material.node_tree.nodes['Neutral charcoal palette'].color_ramp.elements]
for actual,expected in zip(saved_palette,PRESETS[saved_preset]['palette']):
    assert max(abs(a-b) for a,b in zip(actual,color(expected)))<1e-6,'Saved palette differs from preset config'
assert all(n.image.packed_file for n in material.node_tree.nodes if n.type=='TEX_IMAGE')
assert len(body.data.uv_layers['BodyUV'].data)==len(body.data.loops)
# Save actual projected UV edge layout as SVG, as well as image-processing body mask.
segments=[]
uv=body.data.uv_layers['BodyUV'].data
for face in body.data.polygons:
    if face.normal.z<.5: continue
    coords=[uv[i].uv for i in face.loop_indices]
    for a,b in zip(coords,coords[1:]+coords[:1]): segments.append(f'M {a.x*1024:.2f},{(1-a.y)*1024:.2f} L {b.x*1024:.2f},{(1-b.y)*1024:.2f}')
(ROOT/'geometry/uv-mesh.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024"><rect width="1024" height="1024" fill="#202020"/><path d="'+' '.join(segments)+'" stroke="#8aafca" stroke-width="0.3" fill="none"/><path d="M512,0L512,1024" stroke="#ff6655"/></svg>')
# Validate each placement stays on photographed wood, without EXTEND sampling on front.
coverage=[]
for c in MANIFEST:
    set_finish('prs_reference',c)
    theta=math.radians(CFG['placements'].get(c['source_filename'],{}).get('rotation_deg',0)); placement=CFG['placements'].get(c['source_filename'],{})
    count=0
    for vert in body.data.vertices:
        if vert.co.z<0: continue
        x,y=vert.co.x*1000,vert.co.y*1000
        tx=x*math.cos(theta)-y*math.sin(theta)+placement.get('x_mm',0)
        ty=x*math.sin(theta)+y*math.cos(theta)+placement.get('y_mm',0)
        u=tx/c['assumed_width_mm']+.5; v=ty/c['assumed_height_mm']+.5
        if not (0<=u<=1 and 0<=v<=1): count+=1
    assert count==0,f"Blank placement outside photographed area: {c['source_filename']}"
    coverage.append({'candidate':c['source_filename'],'outside_vertices':count})
report={'blend_reopened':True,'packed_textures_verified':True,'manifold':True,'uv_assigned':True,'saved_preset':saved_preset,'saved_palette_verified':True,'saved_palette_hex':PRESETS[saved_preset]['palette'],'coverage':coverage,'signature':signature(),'blender_version':bpy.app.version_string}
(ROOT/'blender/scene-validation.json').write_text(json.dumps(report,indent=2)); print('SAVED SCENE VALIDATED',report)
