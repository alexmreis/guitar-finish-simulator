import json
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.calibration import CalibrationSession
from guitar_finish_simulator.pipeline import Pipeline

class CarveDomainTests(unittest.TestCase):
    def test_carve_field_and_section_follow_the_declared_project_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            session=CalibrationSession(ROOT/'projects/compact/project.json',root/'draft')
            data=session.data();data['config']['surface'].update(texture_width_mm=600,texture_height_mm=800)
            session.save(data)
            workspace=Pipeline(session.path,root/'run').prepare()
            with np.load(workspace/'geometry/full_guitar/carve-field.npz') as field:
                self.assertEqual(float(field['x0_mm']),-300)
                self.assertEqual(float(field['y0_mm']),-400)
                self.assertEqual(field['height_mm'].shape,(1601,1201))
            self.assertIn('42 mm center / 14 mm rim',(workspace/'geometry/full_guitar/body-section.svg').read_text())
