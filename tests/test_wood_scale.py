import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.project import Project
from guitar_finish_simulator.wood import prepare_wood

class WoodScaleTests(unittest.TestCase):
    def test_explicit_crop_width_changes_physical_scale_without_resampling_grain(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Project.load(ROOT/'projects/umbraeternal/project.json').materialize(directory)
            specs=json.loads((root/'config/candidates.json').read_text())
            specs['20261009_112804.jpg']['width_mm']=500
            (root/'config/candidates.json').write_text(json.dumps(specs))
            prepare_wood(root,root/'assets/originals')
            record=json.loads((root/'assets/textures/processed/20261009_112804.jpg.json').read_text())
            self.assertEqual(record['assumed_width_mm'],500)
            self.assertAlmostEqual(record['assumed_height_mm'],709.07079646,places=6)
            path='assets/textures/bookmatched/20261009_112804.jpg.png'
            approved=json.loads((ROOT/'tests/fixtures/artifact-hashes.json').read_text())[path]
            self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(),approved)
