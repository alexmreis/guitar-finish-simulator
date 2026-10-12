import json
import sys
import unittest
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))

class DeliveryTests(unittest.TestCase):
    def test_delivery_verifies_requested_candidate_matrix_and_enlarged_renders(self):
        from guitar_finish_simulator.delivery import validate_delivery
        root=ROOT/'.work/tests/compact'
        result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'batch',str(ROOT/'projects/compact/project.json'),'--workspace',str(root),'--no-hero'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-3000:])
        report=validate_delivery(root,require_enlarged=True,hero_views=False)
        self.assertEqual(report['full_comparison_renders'],4)
        self.assertEqual(report['enlarged_prs_renders'],1)
        self.assertTrue(report['identical_geometry_cameras_lighting_verified'])
