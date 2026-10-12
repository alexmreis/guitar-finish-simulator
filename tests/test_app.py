import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

class CalibrationAppTests(unittest.TestCase):
    def test_local_editor_reads_project_and_persists_finish_changes(self):
        from guitar_finish_simulator.app import make_server
        with tempfile.TemporaryDirectory() as directory:
            server=make_server(ROOT/'projects/umbraeternal/project.json',Path(directory),port=0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base=f'http://127.0.0.1:{server.server_port}'
                with urlopen(base+'/api/project') as response:
                    project=json.load(response)
                self.assertEqual(project['name'],'Umbraeternal')
                request=Request(base+'/api/finish',data=json.dumps({'preset':'prs_reference','controls':{'coat_weight':.06}}).encode(),headers={'Content-Type':'application/json'},method='POST')
                with urlopen(request) as response:
                    self.assertEqual(json.load(response)['coat_weight'],.06)
                with urlopen(base+'/api/project') as response:
                    saved=json.load(response)
                self.assertEqual(saved['config']['finishes']['prs_reference']['coat_weight'],.06)
            finally:
                server.shutdown();server.server_close();thread.join()
