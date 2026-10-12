import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

class ProjectSpecificationTests(unittest.TestCase):
    def test_existing_project_materializes_independent_workspace(self):
        from guitar_finish_simulator.project import Project
        project = Project.load(ROOT / 'projects/umbraeternal/project.json')
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'run'
            project.materialize(destination)
            self.assertEqual(len(json.loads((destination / 'config/candidates.json').read_text())), 8)
            self.assertEqual((destination / 'assets/originals/20261009_112804.jpg').read_bytes(), (ROOT / 'assets/originals/20261009_112804.jpg').read_bytes())
            self.assertEqual(json.loads((destination / 'config/full_guitar.json').read_text())['body_center_thickness_mm'], 44)
            self.assertTrue((destination / 'project.lock.json').is_file())

    def test_rejects_impossible_carve_before_creating_outputs(self):
        from guitar_finish_simulator.project import Project, SpecificationError
        original = Project.load(ROOT / 'projects/umbraeternal/project.json')
        data = dict(original.data)
        data['config'] = dict(original.configs)
        data['config']['instrument'] = {**original.configs['instrument'], 'body_rim_thickness_mm': 45}
        data['inputs'] = {**data['inputs'], 'candidates': original.candidates}
        with tempfile.TemporaryDirectory() as directory:
            spec = Path(directory) / 'project.json'
            spec.write_text(json.dumps(data))
            with self.assertRaisesRegex(SpecificationError, 'rim.*center'):
                Project.load(spec)
