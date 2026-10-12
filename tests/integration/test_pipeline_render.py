import json
import subprocess
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

class PipelineRenderTests(unittest.TestCase):
    def test_render_command_records_material_source_and_fixed_scene(self):
        workspace=ROOT/'.work/tests/umbraeternal'
        result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'render',str(ROOT/'projects/umbraeternal/project.json'),'--workspace',str(workspace),'--preset','extreme_black','--candidate','20261009_113155.jpg','--view','carve','--preview'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-3000:])
        path=workspace/'renders/full_guitar/previews/extreme_black/20261009_113155.jpg.carve.json'
        record=json.loads(path.read_text())
        model=json.loads((workspace/'blender/full_guitar/validation.json').read_text())
        self.assertEqual(record['geometry_signature'],model['geometry_signature'])
        self.assertEqual(record['finish_controls']['coat_weight'],.12)
        self.assertEqual(len(record['source_sha256']),64)
        self.assertEqual(len(record['texture_sha256']),64)

        scene=workspace/'blender/last_render.blend'
        self.assertTrue(scene.exists(),'Editable scene must match the latest explicit render')
        import os,shutil
        blender=os.environ.get('BLENDER',shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender')
        expression="import bpy; names=['Photo wood / stain / perimeter burst / clearcoat','Matching photographed maple headstock veneer']; assert all(bpy.data.materials[n]['candidate']=='20261009_113155.jpg' and bpy.data.materials[n]['preset']=='extreme_black' for n in names)"
        reopened=subprocess.run([blender,'-b',str(scene),'--python-exit-code','1','--python-expr',expression],capture_output=True,text=True)
        self.assertEqual(reopened.returncode,0,reopened.stdout+reopened.stderr)
