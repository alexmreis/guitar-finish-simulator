import json
import subprocess
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

class AnchorBuildTests(unittest.TestCase):
    def test_cad_anchors_place_bridge_and_controls_on_the_saved_instrument(self):
        folder=ROOT/'.work/tests/anchor-spec';folder.mkdir(parents=True,exist_ok=True)
        data=json.loads((ROOT/'projects/compact/project.json').read_text())
        for key,value in list(data['inputs'].items()):
            if isinstance(value,str):data['inputs'][key]=str((ROOT/'projects/compact'/value).resolve())
        for key,value in list(data['config'].items()):
            if isinstance(value,str):data['config'][key]=str((ROOT/'projects/compact'/value).resolve())
        for value in data['geometry'].values():value['path']=str((ROOT/'projects/compact'/value['path']).resolve())
        anchors={'BRIDGE':(0,-70),'VOLUME':(70,-90),'TONE':(100,-130),'SELECTOR':(105,-35)}
        path=folder/'anchors.dxf';text='0\nSECTION\n2\nENTITIES\n'
        for name,(x,y) in anchors.items():text+=f'0\nPOINT\n8\n{name}\n10\n{x}\n20\n{y}\n'
        path.write_text(text+'0\nENDSEC\n0\nEOF\n')
        data['geometry']['anchors']={'path':str(path),'units':'mm','frame':'body_center'}
        spec=folder/'project.json';spec.write_text(json.dumps(data))
        root=ROOT/'.work/tests/anchors'
        result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'build',str(spec),'--workspace',str(root)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-3000:])
        report=json.loads((root/'blender/full_guitar/validation.json').read_text())
        self.assertAlmostEqual(report['measured_bridge_saddle_y_mm'],-70,delta=.01)
        self.assertAlmostEqual(report['control_locations_mm']['Volume push-pull'][0],70,delta=.01)
        self.assertAlmostEqual(report['control_locations_mm']['Volume push-pull'][1],-90,delta=.01)
