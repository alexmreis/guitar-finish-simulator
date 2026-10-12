import json
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.calibration import CalibrationSession
from guitar_finish_simulator.pipeline import Pipeline

class MaterialEditTests(unittest.TestCase):
    def test_material_edit_changes_reflections_and_reuses_geometry_and_studio(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            session=CalibrationSession(ROOT/'projects/umbraeternal/project.json',root/'draft')
            workspace=root/'run'
            Pipeline(session.path,workspace).render('prs_reference',['20261009_112804.jpg'],'carve',True)
            path=workspace/'renders/full_guitar/previews/prs_reference/20261009_112804.jpg.carve.png'
            before=np.asarray(Image.open(path).convert('RGB'),dtype=float)
            first=json.loads(path.with_suffix('.json').read_text())
            timestamp=(workspace/'blender/full_guitar.blend').stat().st_mtime_ns
            session.update_finish('prs_reference',{'coat_weight':.9,'coat_roughness':.09,'base_roughness':.23})
            Pipeline(session.path,workspace).render('prs_reference',['20261009_112804.jpg'],'carve',True)
            second=json.loads(path.with_suffix('.json').read_text())
            after=np.asarray(Image.open(path).convert('RGB'),dtype=float)
            self.assertGreater(np.abs(before-after).mean(),1)
            self.assertEqual(first['geometry_signature'],second['geometry_signature'])
            self.assertEqual(timestamp,(workspace/'blender/full_guitar.blend').stat().st_mtime_ns)
            self.assertEqual(first['source_sha256'],second['source_sha256'])
