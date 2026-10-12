import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.calibration import CalibrationSession
from guitar_finish_simulator.pipeline import Pipeline

class RenderProfileTests(unittest.TestCase):
    def test_preview_uses_specified_resolution_and_sample_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            session=CalibrationSession(ROOT/'projects/compact/project.json',root/'draft')
            data=session.data();data['config']['instrument'].update(preview_carve_resolution=[256,256],preview_samples=8)
            session.save(data)
            Pipeline(session.path,root/'run').render('prs_reference',['20261009_113155.jpg'],'carve',True)
            record=json.loads((root/'run/renders/full_guitar/previews/prs_reference/20261009_113155.jpg.carve.json').read_text())
            self.assertEqual(record['resolution'],[256,256])
            self.assertEqual(record['samples'],8)
