"""Loopback-only calibration editor; project files are the source of truth."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import mimetypes
import threading
from urllib.parse import urlparse,parse_qs,unquote
from .pipeline import Pipeline
from .project import Project
from pathlib import Path
from .calibration import CalibrationSession
from .project import SpecificationError

def make_server(specification,workspace,port=8765,blender=None):
    root=Path(workspace).resolve()
    session=CalibrationSession(specification,root/'.calibration')
    state={'status':'idle'}
    lock=threading.RLock()

    def preview(payload):
        try:
            pipeline=Pipeline(session.path,root,blender)
            pipeline.render(payload['preset'],[payload['candidate']],payload['view'],True)
            image=root/'renders/full_guitar/previews'/payload['preset']/f"{payload['candidate']}.{payload['view']}.png"
            with lock:
                state.update(status='complete',image='/artifacts/'+str(image.relative_to(root)),**payload)
        except Exception as error:
            with lock:
                state.update(status='failed',error=str(error))
    class Handler(BaseHTTPRequestHandler):
        def send(self,value,status=200):
            payload=json.dumps(value).encode()
            self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)

        def file(self,path):
            if not path.is_file():
                return self.send({'error':'Artifact not yet available'},404)
            payload=path.read_bytes()
            self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(path))[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)

        def do_GET(self):
            url=urlparse(self.path)
            if url.path=='/api/project':
                self.send(session.data())
            elif url.path=='/api/controls':
                from .finishes import BOUNDS
                self.send(BOUNDS)
            elif url.path=='/api/job':
                with lock:
                    self.send(dict(state))
            elif url.path=='/api/source':
                candidate=parse_qs(url.query).get('candidate',[''])[0]
                project=Project.load(session.path)
                if candidate not in project.candidates:
                    return self.send({'error':'Unknown photograph'},404)
                source=project.resolve(project.data['inputs']['photos'])/candidate
                if project.candidates[candidate].get('exif_orientation_applied'):
                    import io
                    from .photographs import open_photograph
                    stream=io.BytesIO()
                    with open_photograph(source,project.candidates[candidate]) as image:
                        image.save(stream,format='PNG')
                    payload=stream.getvalue()
                    self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
                else:
                    self.file(source)
            elif url.path=='/api/reference':
                project=Project.load(session.path)
                self.file(project.resolve(project.data['inputs']['finish_reference']))
            elif url.path=='/api/export':
                self.send(session.data())
            elif url.path.startswith('/artifacts/'):
                path=(root/unquote(url.path[len('/artifacts/'):])).resolve()
                if not path.is_relative_to(root) or path.suffix.lower() not in ['.png','.json','.svg']:
                    return self.send({'error':'Unknown artifact'},404)
                self.file(path)
            elif url.path=='/':
                self.file(Path(__file__).parent/'ui/index.html')
            else:
                self.send({'error':'Unknown endpoint'},404)

        def do_POST(self):
            try:
                with lock:
                    if state['status']=='running':
                        return self.send({'error':'Wait for the current preview to finish before changing its inputs'},409)
                    url=urlparse(self.path)
                    length=int(self.headers.get('Content-Length','0'))
                    if url.path=='/api/upload':
                        if not 0<length<=25*1024*1024:
                            return self.send({'error':'Photograph must be between 1 byte and 25 MB'},413)
                        query=parse_qs(url.query)
                        result=session.upload_wood(query.get('filename',[''])[0],self.rfile.read(length),bookmatch=query.get('bookmatch',['simulated'])[0],figure_type=query.get('figure_type',['flame'])[0],rotation=query.get('rotation',[0])[0],width_mm=query.get('width_mm',[None])[0])
                        return self.send(result,201)
                    data=json.loads(self.rfile.read(length))
                    if self.path=='/api/finish':
                        self.send(session.update_finish(data['preset'],data['controls']))
                    elif self.path=='/api/wood':
                        self.send(session.update_wood(data['candidate'],data['controls']))
                    elif self.path=='/api/placement':
                        self.send(session.update_placement(data['candidate'],data['controls']))
                    elif self.path=='/api/spec':
                        session.save(data);self.send(session.data())
                    elif self.path=='/api/sample':
                        from .calibration import sample_reference
                        project=Project.load(session.path)
                        self.send(sample_reference(project.resolve(project.data['inputs']['finish_reference']),data['regions']))
                    elif self.path=='/api/preview':
                        project=Project.load(session.path)
                        if data.get('candidate') not in project.candidates or data.get('preset') not in project.configs['finishes'] or data.get('view') not in ['front','perspective','rear','carve']:
                            raise SpecificationError('Select a known photograph, finish and camera')
                        if project.candidates[data['candidate']].get('crop_review_required'):
                            raise SpecificationError('Review the uploaded crop and orientation, then save wood settings before rendering')
                        state.clear();state.update(status='running')
                        threading.Thread(target=preview,args=(data,),daemon=True).start()
                        self.send(dict(state),202)
                    else:
                        self.send({'error':'Unknown endpoint'},404)
            except (SpecificationError,ValueError,KeyError,TypeError) as error:
                self.send({'error':str(error)},400)

        def log_message(self,*args):
            pass
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.session=session
    return server
