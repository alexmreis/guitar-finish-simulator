"""Bootstrap the shared photo shader without generating any guitar geometry."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scene import bpy,ROOT,MANIFEST,PRESETS,material,set_finish,configure_render_defaults
bpy.ops.wm.read_factory_settings(use_empty=True)
configure_render_defaults()
material().use_fake_user=True
set_finish('prs_reference' if 'prs_reference' in PRESETS else next(iter(PRESETS)),MANIFEST[0])
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/material_template.blend'))
report={'mesh_objects':sum(o.type=='MESH' for o in bpy.context.scene.objects),'blender_version':bpy.app.version_string,'engine':bpy.context.scene.render.engine}
(ROOT/'blender/full_guitar/template-validation.json').write_text(json.dumps(report,indent=2))
print('MATERIAL TEMPLATE VALIDATED',report)
