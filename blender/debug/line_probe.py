"""Minimal render probe: isolate the reported waist line from wood textures."""
import bpy,bmesh,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
body=bpy.data.objects['Guitar Body']
material=bpy.data.materials.new('Diagnostic uniform gloss');material.use_nodes=True
bsdf=material.node_tree.nodes['Principled BSDF'];bsdf.inputs['Base Color'].default_value=(.04,.04,.04,1);bsdf.inputs['Roughness'].default_value=.23;bsdf.inputs['Coat Weight'].default_value=1;bsdf.inputs['Coat Roughness'].default_value=.1
body.data.materials.clear();body.data.materials.append(material)
for p in body.data.polygons:p.material_index=0
if '--triangulate' in sys.argv:
 bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();body.data.set_sharp_from_angle(angle=.610865)
if '--smooth' in sys.argv:
 for edge in body.data.edges:edge.use_edge_sharp=False
if '--analytic' in sys.argv:
 sys.path.insert(0,str(root/'blender/scripts'))
 from surface_normals import apply
 apply(body,.044)
scene=bpy.context.scene;scene.camera=bpy.data.objects['Front'];scene.render.resolution_x=scene.render.resolution_y=800
scene.render.filepath=str(root/'blender/debug'/('line-analytic.png' if '--analytic' in sys.argv else 'line-smooth.png' if '--smooth' in sys.argv else 'line-triangulated.png' if '--triangulate' in sys.argv else 'line-baseline.png'));bpy.ops.render.render(write_still=True)
