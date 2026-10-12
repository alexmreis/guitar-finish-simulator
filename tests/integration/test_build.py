import json
import os
import shutil
import subprocess
import sys
import unittest
import numpy as np
from PIL import Image
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

class BuildTests(unittest.TestCase):
    def test_cad_project_builds_reopens_and_validates_the_approved_instrument(self):
        workspace=ROOT/'.work/tests/umbraeternal'
        result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'build',str(ROOT/'projects/umbraeternal/project.json'),'--workspace',str(workspace)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-3000:])
        report=json.loads((workspace/'blender/full_guitar/validation.json').read_text())
        baseline=json.loads((ROOT/'blender/full_guitar/validation.json').read_text())
        self.assertEqual(report['body_vertices'],17457)
        self.assertEqual(report['body_nonmanifold_edges'],0)
        self.assertAlmostEqual(report['measured_center_thickness_mm'],44,delta=.01)
        self.assertTrue(report['saved_blend_reopened'])

        blender=os.environ.get('BLENDER',shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender')
        result=subprocess.run([blender,'-b',str(workspace/'blender/full_guitar.blend'),'--python-exit-code','1','--python',str(ROOT/'blender/scripts/render_full_guitar.py'),'--','--preset','prs_reference','--candidate','20261009_112804.jpg','--candidate','20261009_113155.jpg','--camera','carve','--preview'],env={**os.environ,'GFS_PROJECT_ROOT':str(workspace)},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-3000:])
        for candidate in ['20261009_112804.jpg','20261009_113155.jpg']:
            path=workspace/'renders/full_guitar/previews/prs_reference'/f'{candidate}.carve.png'
            rendered=json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(rendered['geometry_signature'],report['geometry_signature'])
            actual=np.asarray(Image.open(path).convert('RGB'),dtype=float)
            expected=np.asarray(Image.open(ROOT/'tests/fixtures'/path.name).convert('RGB'),dtype=float)
            self.assertLess(np.abs(actual-expected).mean(),.15)
            self.assertLess(np.percentile(np.abs(actual-expected),99),2)
