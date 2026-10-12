import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.pipeline import Pipeline

class SingleGeometryBuildTests(unittest.TestCase):
    def test_material_bootstrap_does_not_generate_an_intermediate_guitar_body(self):
        root=ROOT/'.work/tests/single-build'
        Pipeline(ROOT/'projects/compact/project.json',root).build()
        report=root/'blender/full_guitar/template-validation.json'
        self.assertTrue(report.exists())
        self.assertEqual(json.loads(report.read_text())['mesh_objects'],0)
        self.assertTrue((root/'geometry/full_guitar/carved_body.obj').exists())
