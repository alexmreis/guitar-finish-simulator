import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

class CalibrationTests(unittest.TestCase):
    def test_samples_selected_reference_regions_without_changing_pixels(self):
        from guitar_finish_simulator.calibration import sample_reference
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'reference.png'
            image=Image.new('RGB',(40,10));colors=['#08090A','#18191B','#8E806D','#B8A48A']
            for i,color in enumerate(colors):
                image.paste(color,(i*10,0,(i+1)*10,10))
            image.save(path);original=path.read_bytes()
            result=sample_reference(path,[[0,0,10,10],[10,0,20,10],[20,0,30,10],[30,0,40,10]])
            self.assertEqual(result['palette'],colors)
            self.assertEqual(path.read_bytes(),original)
            self.assertIn('lighting',result['limitation'])

    def test_finish_adjustment_saves_a_draft_without_touching_sources_or_lighting(self):
        from guitar_finish_simulator.calibration import CalibrationSession
        from guitar_finish_simulator.project import Project
        source=ROOT/'projects/umbraeternal/project.json';original=source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            session=CalibrationSession(source,Path(directory))
            before=Project.load(session.path)
            session.update_finish('prs_reference',{'coat_weight':.08,'base_roughness':.4})
            saved=Project.load(session.path)
            self.assertEqual(saved.configs['finishes']['prs_reference']['coat_weight'],.08)
            self.assertEqual(saved.configs['instrument'],before.configs['instrument'])
            self.assertEqual(saved.candidates,before.candidates)
            self.assertEqual(source.read_bytes(),original)

    def test_invalid_material_control_does_not_replace_the_last_valid_draft(self):
        from guitar_finish_simulator.calibration import CalibrationSession
        from guitar_finish_simulator.project import SpecificationError
        with tempfile.TemporaryDirectory() as directory:
            session=CalibrationSession(ROOT/'projects/umbraeternal/project.json',Path(directory))
            original=session.path.read_bytes()
            with self.assertRaisesRegex(SpecificationError,'coat_weight'):
                session.update_finish('prs_reference',{'coat_weight':1.5})
            self.assertEqual(session.path.read_bytes(),original)

    def test_physical_bookmatch_requires_both_photographed_halves(self):
        import json
        from guitar_finish_simulator.project import Project, SpecificationError
        original=Project.load(ROOT/'projects/umbraeternal/project.json')
        data=json.loads(json.dumps(original.data));data['config']=original.configs
        data['inputs']['candidates']=original.candidates
        data['inputs']['candidates']['20261009_112804.jpg']['quads']=data['inputs']['candidates']['20261009_112804.jpg']['quads'][:1]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'project.json';path.write_text(json.dumps(data))
            with self.assertRaisesRegex(SpecificationError,'physical.*two'):
                Project.load(path)

    def test_wood_crop_cannot_extend_outside_the_original_photo(self):
        from guitar_finish_simulator.calibration import CalibrationSession
        from guitar_finish_simulator.project import SpecificationError
        with tempfile.TemporaryDirectory() as directory:
            session=CalibrationSession(ROOT/'projects/umbraeternal/project.json',Path(directory))
            before=session.path.read_bytes()
            with self.assertRaisesRegex(SpecificationError,'outside'):
                session.update_wood('20261009_112804.jpg',{'quads':[[[-10,0],[10,0],[10,20],[0,20]],[[20,0],[30,0],[30,20],[20,20]]]})
            self.assertEqual(session.path.read_bytes(),before)

    def test_texture_placement_cannot_sample_beyond_the_photographed_blank(self):
        from guitar_finish_simulator.calibration import CalibrationSession
        from guitar_finish_simulator.pipeline import Pipeline
        from guitar_finish_simulator.project import SpecificationError
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            session=CalibrationSession(ROOT/'projects/umbraeternal/project.json',root/'draft')
            session.update_placement('20261009_112804.jpg',{'x_mm':600,'rotation_deg':180})
            with self.assertRaisesRegex(SpecificationError,'112804.*outside'):
                Pipeline(session.path,root/'run').prepare()
