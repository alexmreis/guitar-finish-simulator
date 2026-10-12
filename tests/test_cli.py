import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class CliTests(unittest.TestCase):
    def test_prepare_consumes_specification_cad_and_photos_in_isolated_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'output'
            result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'prepare',str(ROOT/'projects/umbraeternal/project.json'),'--workspace',str(root)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            outline=json.loads((root/'geometry/outline.json').read_text())
            self.assertAlmostEqual(outline['width_mm'],320,places=5)
            self.assertEqual(outline['source_kind'],'cad')
            self.assertEqual(len(json.loads((root/'assets/textures/processed/manifest.json').read_text())),8)
            self.assertTrue((root/'geometry/full_guitar/carve-field.npz').exists())

    def test_validate_reports_missing_photographs_without_creating_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            spec=json.loads((ROOT/'projects/umbraeternal/project.json').read_text())
            for key in spec['config']:
                spec['config'][key]=str((ROOT/'projects/umbraeternal'/spec['config'][key]).resolve())
            spec['inputs']['candidates']=str(ROOT/'config/candidates.json')
            spec['inputs']['photos']=str(Path(directory)/'missing')
            path=Path(directory)/'project.json';path.write_text(json.dumps(spec))
            output=Path(directory)/'output'
            result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'validate',str(path),'--workspace',str(output)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('20261009_111903.jpg',result.stderr)
            self.assertFalse(output.exists())

    def test_render_rejects_any_unknown_candidate_before_building_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'output'
            result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'render',str(ROOT/'projects/umbraeternal/project.json'),'--workspace',str(root),'--candidate','20261009_112804.jpg','--candidate','missing.jpg','--preview'],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('missing.jpg',result.stderr)
            self.assertFalse((root/'blender/full_guitar.blend').exists())
