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

    def test_complete_cad_input_does_not_require_a_design_photograph(self):
        original=__import__('guitar_finish_simulator.project',fromlist=['Project']).Project.load(ROOT/'projects/umbraeternal/project.json')
        data=json.loads(json.dumps(original.data))
        data['config']=original.configs
        data['inputs']={k:str(original.resolve(v)) for k,v in data['inputs'].items() if k not in ['candidates','design_reference']}
        data['inputs']['candidates']=original.candidates
        data['geometry']['body']['path']=str(ROOT/'geometry/body_outline.dxf')
        data['geometry']['headstock']={'path':str(ROOT/'projects/umbraeternal/headstock.svg'),'units':'mm'}
        from guitar_finish_simulator.project import Project
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'project.json';path.write_text(json.dumps(data))
            self.assertTrue(Project.load(path).validate_inputs()['valid'])

    def test_workspace_snapshot_can_recreate_a_project_without_original_paths(self):
        from guitar_finish_simulator.project import Project
        original=Project.load(ROOT/'projects/umbraeternal/project.json')
        with tempfile.TemporaryDirectory() as directory:
            first=Path(directory)/'first';original.materialize(first)
            snapshot=first/'project.snapshot.json'
            self.assertTrue(snapshot.exists())
            portable=Project.load(snapshot)
            self.assertTrue(portable.validate_inputs()['valid'])
            second=Path(directory)/'second';portable.materialize(second)
            self.assertEqual((first/'assets/originals/20261009_112804.jpg').read_bytes(),(second/'assets/originals/20261009_112804.jpg').read_bytes())
