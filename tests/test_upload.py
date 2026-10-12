import json
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.app import make_server
from guitar_finish_simulator.project import Project

@contextmanager
def editor(folder):
    server=make_server(ROOT/'projects/compact/project.json',folder,port=0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}',server
    finally:
        server.shutdown();server.server_close();thread.join()

def upload(base,name,content,**options):
    query=urlencode({'filename':name,'bookmatch':'physical','figure_type':'flame',**options})
    request=Request(base+'/api/upload?'+query,data=content,headers={'Content-Type':'application/octet-stream'},method='POST')
    return urlopen(request)

class WoodUploadTests(unittest.TestCase):
    def test_uploaded_photo_is_selectable_persistent_and_preserved_byte_for_byte(self):
        name='20261009_112804.jpg'
        content=(ROOT/'assets/originals'/name).read_bytes()
        source_spec=(ROOT/'projects/compact/project.json').read_bytes()
        with tempfile.TemporaryDirectory() as directory,editor(Path(directory)) as (base,server):
            with upload(base,name,content) as response:
                self.assertEqual(response.status,201)
                result=json.load(response)
            self.assertEqual(result['candidate'],name)
            with urlopen(base+'/api/project') as response:
                data=json.load(response)
            candidate=data['inputs']['candidates'][name]
            self.assertEqual(candidate['status'],'physical')
            self.assertEqual(len(candidate['quads']),2)
            self.assertTrue(candidate['crop_review_required'])
            project=Project.load(server.session.path)
            self.assertEqual((project.resolve(project.data['inputs']['photos'])/name).read_bytes(),content)
            self.assertEqual((ROOT/'projects/compact/project.json').read_bytes(),source_spec)
            self.assertEqual((ROOT/'assets/originals'/name).read_bytes(),content)

    def test_invalid_uploads_and_duplicate_names_never_replace_sources_or_the_draft(self):
        content=(ROOT/'assets/originals/20261009_112804.jpg').read_bytes()
        with tempfile.TemporaryDirectory() as directory,editor(Path(directory)) as (base,server):
            before=server.session.path.read_bytes()
            for name,body in [('../outside.jpg',content),('invalid.jpg',b'not a photograph'),('grain.txt',content),('20261009_113155.jpg',content)]:
                with self.subTest(filename=name):
                    try:
                        upload(base,name,body)
                        self.fail('Invalid upload was accepted')
                    except HTTPError as error:
                        with error:
                            self.assertEqual(error.code,400)
                            self.assertIn('error',json.load(error))
                    self.assertEqual(server.session.path.read_bytes(),before)
            self.assertFalse((Path(directory)/'.calibration/photos').exists())

    def test_preview_waits_for_explicit_crop_review(self):
        content=(ROOT/'assets/originals/20261009_112804.jpg').read_bytes()
        with tempfile.TemporaryDirectory() as directory,editor(Path(directory)) as (base,server):
            with upload(base,'20261009_112804.jpg',content) as response:response.read()
            request=Request(base+'/api/preview',data=json.dumps({'candidate':'20261009_112804.jpg','preset':'prs_reference','view':'carve'}).encode(),headers={'Content-Type':'application/json'},method='POST')
            try:
                urlopen(request)
                self.fail('Unreviewed full-photo crop was rendered')
            except HTTPError as error:
                with error:
                    self.assertEqual(error.code,400)
                    self.assertIn('crop',json.load(error)['error'])
            with urlopen(base+'/api/job') as response:
                self.assertEqual(json.load(response)['status'],'idle')

    def test_phone_exif_orientation_uses_the_same_coordinates_in_editor_and_processing(self):
        import io
        from PIL import Image
        from guitar_finish_simulator.wood import prepare_wood
        with Image.open(ROOT/'assets/originals/20261009_112804.jpg') as photo:
            original_size=photo.size
            exif=Image.Exif();exif[274]=6
            stream=io.BytesIO();photo.save(stream,format='JPEG',exif=exif)
        content=stream.getvalue()
        with tempfile.TemporaryDirectory() as directory,editor(Path(directory)) as (base,server):
            with upload(base,'Phone maple.jpg',content,bookmatch='simulated') as response:
                result=json.load(response)
            self.assertEqual(result['pixels'],[original_size[1],original_size[0]])
            with urlopen(base+'/api/source?'+urlencode({'candidate':'Phone maple.jpg'})) as response:
                with Image.open(io.BytesIO(response.read())) as image:
                    self.assertEqual(image.size,tuple(result['pixels']))
            project=Project.load(server.session.path)
            workspace=project.materialize(Path(directory)/'prepared')
            prepare_wood(workspace,workspace/'assets/originals')
            record=json.loads((workspace/'assets/textures/processed/Phone maple.jpg.json').read_text())
            self.assertTrue(record['exif_orientation_applied'])
            self.assertEqual(record['bookmatched_pixels'],[2*(original_size[1]-1),original_size[0]-1])
            self.assertEqual((project.resolve(project.data['inputs']['photos'])/'Phone maple.jpg').read_bytes(),content)

    def test_pending_upload_does_not_enter_preparation_until_reviewed(self):
        from guitar_finish_simulator.pipeline import Pipeline
        from guitar_finish_simulator.project import SpecificationError
        with tempfile.TemporaryDirectory() as directory,editor(Path(directory)) as (base,server):
            content=(ROOT/'assets/originals/20261009_112804.jpg').read_bytes()
            with upload(base,'20261009_112804.jpg',content) as response:response.read()
            workspace=Path(directory)/'prepared'
            with self.assertRaisesRegex(SpecificationError,'112804.*crop'):
                Pipeline(server.session.path,workspace).prepare()
            Pipeline(server.session.path,workspace).prepare(skip_pending=True)
            manifest=json.loads((workspace/'assets/textures/processed/manifest.json').read_text())
            self.assertEqual([c['source_filename'] for c in manifest],['20261009_113155.jpg'])
