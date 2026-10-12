import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.calibration import CalibrationSession
from guitar_finish_simulator.pipeline import Pipeline

class UploadPreparationTests(unittest.TestCase):
    def test_ninth_candidate_is_visible_in_preparation_sheet_and_portable_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            session=CalibrationSession(ROOT/'projects/umbraeternal/project.json',root/'draft')
            content=(ROOT/'assets/originals/20261009_112804.jpg').read_bytes()
            session.upload_wood('Extra flame.jpg',content,bookmatch='physical')
            original=session.data()['inputs']['candidates']['20261009_112804.jpg']
            session.update_wood('Extra flame.jpg',{'quads':original['quads'],'rotation':0})
            workspace=Pipeline(session.path,root/'prepared').prepare()
            with Image.open(workspace/'renders/comparisons/preprocessed.png') as sheet:
                self.assertEqual(sheet.size,(1600,1500))
                self.assertGreater(max(sheet.crop((0,1000,400,1500)).getextrema())[1],100)
            from guitar_finish_simulator.project import Project
            snapshot=Project.load(workspace/'project.snapshot.json')
            self.assertEqual(len(snapshot.candidates),9)
            self.assertTrue(snapshot.validate_inputs()['valid'])
            self.assertEqual((snapshot.resolve(snapshot.data['inputs']['photos'])/'Extra flame.jpg').read_bytes(),content)
