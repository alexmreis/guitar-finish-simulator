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
