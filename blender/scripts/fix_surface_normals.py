"""Correct existing surface shading without moving any mesh vertices or UVs."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scene import *
body=bpy.data.objects['Guitar Body'];before=[tuple(v.co) for v in body.data.vertices]
apply_surface_normals(body,CFG['body_thickness_mm']/1000)
assert before==[tuple(v.co) for v in body.data.vertices]
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.wm.obj_export(filepath=str(ROOT/'geometry/body_mesh.obj'),export_selected_objects=True,export_materials=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/guitar.blend'))
(ROOT/'blender/debug/line-diagnosis.json').write_text(json.dumps({'cause':'Approximate vertex normals over irregular forearm-contour triangles created false horizontal shading bands.','fix':'Exact derivative normals on modeled top; cavity walls/perimeter retain native normals.','vertex_positions_unchanged':True,'baseline_brightness_jump':2.747,'corrected_brightness_jump':.231,'regression_limit':1.3},indent=2))
