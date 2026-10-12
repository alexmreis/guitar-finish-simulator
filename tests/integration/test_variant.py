import json
import subprocess
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.project import Project

class VariantBuildTests(unittest.TestCase):
    def test_second_cad_instrument_uses_its_own_dimensions_and_physical_quilt(self):
        original=Project.load(ROOT/'projects/umbraeternal/project.json')
        folder=ROOT/'.work/tests/compact-spec';folder.mkdir(parents=True,exist_ok=True)
        points=json.loads((ROOT/'geometry/outline.json').read_text())['points_mm']
        (folder/'body.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><polygon id="BODY" points="'+' '.join(f'{x*.95},{-y*.95}' for x,y in points)+'"/></svg>')
        data=json.loads(json.dumps(original.data))
        data['name']='Compact 24-fret validation instrument'
        data['inputs']={k:str(original.resolve(v)) for k,v in data['inputs'].items()}
        data['inputs']['candidates']={'20261009_113155.jpg':original.candidates['20261009_113155.jpg']}
        data['config']=original.configs
        data['config']['surface']['body_width_mm']=304
        data['config']['instrument'].update(scale_length_mm=635,nut_width_mm=43,last_fret_width_mm=57,fret_count=24,body_center_thickness_mm=42,body_rim_thickness_mm=14,neck_thickness_first_mm=20.5,neck_thickness_twelfth_mm=21.5,bridge_plate_width_mm=82.5,bridge_string_spread_mm=52,bridge_pivot_pitch_mm=54,default_candidate='20261009_113155.jpg')
        data['geometry']={'body':{'path':'body.svg','units':'mm'},'headstock':{'path':str(ROOT/'projects/umbraeternal/headstock.svg'),'units':'mm'}}
        spec=folder/'project.json';spec.write_text(json.dumps(data,indent=2))
        workspace=ROOT/'.work/tests/compact'
        result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'build',str(spec),'--workspace',str(workspace)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-3000:])
        report=json.loads((workspace/'blender/full_guitar/validation.json').read_text())
        self.assertEqual(report['frets'],24)
        self.assertAlmostEqual(report['measured_center_thickness_mm'],42,delta=.01)
        self.assertAlmostEqual(report['measured_nut_width_mm'],43,delta=.05)
        self.assertAlmostEqual(report['bridge_plate_width_mm'],82.5,delta=.01)
        self.assertAlmostEqual(report['measured_bridge_string_spread_mm'],52,delta=.01)
        self.assertAlmostEqual(report['measured_bridge_pivot_pitch_mm'],54,delta=.01)
        self.assertEqual(report['body_nonmanifold_edges'],0)
        head=json.loads((workspace/'geometry/full_guitar/headstock-outline.json').read_text())
        self.assertEqual(head['source_kind'],'cad')
