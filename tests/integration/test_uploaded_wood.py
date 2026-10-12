import hashlib
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from guitar_finish_simulator.app import make_server
from guitar_finish_simulator.pipeline import Pipeline
from test_upload import upload

class UploadedWoodRenderTests(unittest.TestCase):
    def test_reviewed_upload_renders_with_source_provenance_and_reuses_the_instrument(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            server=make_server(ROOT/'projects/compact/project.json',root,port=0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                Pipeline(server.session.path,root).build()
                scene=root/'blender/full_guitar.blend';timestamp=scene.stat().st_mtime_ns
                baseline=json.loads((root/'blender/full_guitar/validation.json').read_text())
                base=f'http://127.0.0.1:{server.server_port}'
                name='20261009_112804.jpg';content=(ROOT/'assets/originals'/name).read_bytes()
                with upload(base,name,content) as response:response.read()
                controls=json.loads((ROOT/'config/candidates.json').read_text())[name]
                request=Request(base+'/api/wood',data=json.dumps({'candidate':name,'controls':{'quads':controls['quads'],'rotation':0}}).encode(),headers={'Content-Type':'application/json'},method='POST')
                with urlopen(request) as response:self.assertFalse(json.load(response)['crop_review_required'])
                request=Request(base+'/api/preview',data=json.dumps({'candidate':name,'preset':'prs_reference','view':'carve'}).encode(),headers={'Content-Type':'application/json'},method='POST')
                with urlopen(request) as response:self.assertEqual(response.status,202)
                deadline=time.monotonic()+90
                while time.monotonic()<deadline:
                    with urlopen(base+'/api/job') as response:job=json.load(response)
                    if job['status'] in ['complete','failed']:break
                    time.sleep(.25)
                self.assertEqual(job['status'],'complete',job)
                record=json.loads((root/'renders/full_guitar/previews/prs_reference'/f'{name}.carve.json').read_text())
                self.assertEqual(record['source_sha256'],hashlib.sha256(content).hexdigest())
                self.assertEqual(record['bookmatch'],'physical')
                self.assertEqual(record['geometry_signature'],baseline['geometry_signature'])
                self.assertEqual(scene.stat().st_mtime_ns,timestamp,'Adding a wood photo must reuse the saved instrument')
            finally:
                server.shutdown();server.server_close();thread.join()

    def test_crop_edit_refreshes_packed_photo_textures_without_rebuilding_geometry(self):
        import numpy as np
        from PIL import Image
        from guitar_finish_simulator.calibration import CalibrationSession
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            session=CalibrationSession(ROOT/'projects/compact/project.json',root/'.calibration')
            name='20261009_113155.jpg'
            Pipeline(session.path,root).render('prs_reference',[name],'carve',True)
            path=root/'renders/full_guitar/previews/prs_reference'/f'{name}.carve.png'
            before=np.asarray(Image.open(path).convert('RGB'),dtype=float)
            timestamp=(root/'blender/full_guitar.blend').stat().st_mtime_ns
            spec=session.data()['inputs']['candidates'][name]
            moved=[[[x+4,y] for x,y in quad] for quad in spec['quads']]
            session.update_wood(name,{'quads':moved})
            Pipeline(session.path,root).render('prs_reference',[name],'carve',True)
            after=np.asarray(Image.open(path).convert('RGB'),dtype=float)
            self.assertGreater(np.abs(before-after).mean(),.1,'Crop edit must reach Blender, not just texture metadata')
            self.assertEqual((root/'blender/full_guitar.blend').stat().st_mtime_ns,timestamp)
