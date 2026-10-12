"""Execute project stages in a dedicated workspace; Blender owns all 3D renders."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import time
import sys
from .project import Project
from .wood import prepare_wood
from .cad import read_outline
from .geometry import prepare_cad_body

CODE_ROOT=Path(__file__).resolve().parents[2]

class Pipeline:
    def __init__(self, specification, workspace, blender=None):
        self.project=Project.load(specification)
        self.root=Path(workspace).resolve()
        self.blender=blender or os.environ.get('BLENDER') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'

    def run_script(self, name, executable=None, arguments=()):
        command=[executable or sys.executable,str(CODE_ROOT/name),*arguments]
        subprocess.run(command,env={**os.environ,'GFS_PROJECT_ROOT':str(self.root)},check=True)

    def prepare(self):
        self.project.materialize(self.root)
        prepare_wood(self.root,self.root/'assets/originals')
        body=self.project.data['geometry']['body']
        points=read_outline(self.project.resolve(body['path']),layer=body.get('layer','BODY'),units=body['units'],origin_mm=body.get('origin_mm',(0,0)))
        prepare_cad_body(self.root,points)
        self.run_script('prepare_full_guitar.py')
        return self.root

    def blender_script(self, name, scene=None, arguments=()):
        command=[self.blender,'-b']
        if scene:
            command.append(str(self.root/scene))
        command+=['--python-exit-code','1','--python',str(CODE_ROOT/'blender/scripts'/name)]
        if arguments:
            command+=['--',*arguments]
        log=self.root/'blender/full_guitar'/f'{Path(name).stem}.log'
        started=time.time()
        with log.open('w') as stream:
            result=subprocess.run(command,env={**os.environ,'GFS_PROJECT_ROOT':str(self.root)},stdout=stream,stderr=subprocess.STDOUT)
        record={'command':command,'returncode':result.returncode,'seconds':round(time.time()-started,3)}
        log.with_suffix('.execution.json').write_text(json.dumps(record,indent=2))
        if result.returncode:
            raise RuntimeError(f'Blender failed: {log}\n'+log.read_text()[-2500:])

    def build(self):
        self.prepare()
        self.blender_script('build.py')
        self.blender_script('full_guitar.py','blender/guitar.blend')
        self.blender_script('validate_full_guitar.py','blender/full_guitar.blend')
        return self.root/'blender/full_guitar.blend'
