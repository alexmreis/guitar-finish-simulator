"""Update only the saved studio rig from config/full_guitar.json."""
import sys,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from full_guitar import *
def fixed_model():
    return [(o.name,[list(row) for row in o.matrix_world],[(tuple(v.co)) for v in o.data.vertices] if o.type=='MESH' else None) for o in bpy.context.scene.objects if o.type!='LIGHT']
before=fixed_model();apply_studio_lighting();bpy.context.view_layer.update();assert before==fixed_model(),'Lighting update moved instrument/camera'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/full_guitar.blend'))
print('Saved reflection-controlled lighting; instrument/cameras unchanged')
