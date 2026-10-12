import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.app import make_server

class AppRenderTests(unittest.TestCase):
    def test_preview_job_returns_a_real_blender_image_and_execution_record(self):
        with tempfile.TemporaryDirectory() as directory:
            server=make_server(ROOT/'projects/umbraeternal/project.json',Path(directory),port=0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base=f'http://127.0.0.1:{server.server_port}'
                payload={'preset':'prs_reference','candidate':'20261009_112804.jpg','view':'carve'}
                request=Request(base+'/api/preview',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
                with urlopen(request) as response:
                    self.assertEqual(response.status,202)
                deadline=time.monotonic()+90
                while time.monotonic()<deadline:
                    with urlopen(base+'/api/job') as response:
                        job=json.load(response)
                    if job['status'] in ['complete','failed']:
                        break
                    time.sleep(.25)
                self.assertEqual(job['status'],'complete',job)
                with urlopen(base+job['image']) as response:
                    self.assertEqual(response.read()[:8],b'\x89PNG\r\n\x1a\n')
                record=json.loads((Path(directory)/'renders/full_guitar/previews/prs_reference/20261009_112804.jpg.carve.json').read_text())
                self.assertEqual(record['engine'],'CYCLES')
                self.assertEqual(record['resolution'],[1000,1000])
            finally:
                server.shutdown();server.server_close();thread.join()
