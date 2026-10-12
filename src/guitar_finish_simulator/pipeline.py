"""Execute project stages in a dedicated workspace; Blender owns all 3D renders."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import time
import sys
from dataclasses import replace
from .project import Project,SpecificationError
from .cache import digest, fingerprint, reusable, record
from .wood import prepare_wood
from .cad import read_outline,read_anchors
from .geometry import prepare_cad_body,validate_texture_coverage

CODE_ROOT=Path(__file__).resolve().parents[2]

class Pipeline:
    def __init__(self, specification, workspace, blender=None):
        self.project=Project.load(specification)
        self.root=Path(workspace).resolve()
        self.blender=blender or os.environ.get('BLENDER') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'

    def run_script(self, name, executable=None, arguments=()):
        command=[executable or sys.executable,str(CODE_ROOT/name),*arguments]
        subprocess.run(command,env={**os.environ,'GFS_PROJECT_ROOT':str(self.root)},check=True)

    def prepare(self,skip_pending=False):
        pending=[name for name,spec in self.project.candidates.items() if spec.get('crop_review_required')]
        if pending and not skip_pending:
            raise SpecificationError(', '.join(pending)+': review uploaded crop corners and save wood settings before preparation')
        if pending:
            ready={name:spec for name,spec in self.project.candidates.items() if not spec.get('crop_review_required')}
            self.project=replace(self.project,candidates=ready)
        self.project.validate_inputs()
        self.project.materialize(self.root)
        prepare_wood(self.root,self.root/'assets/originals')
        body=self.project.data['geometry']['body']
        points=read_outline(self.project.resolve(body['path']),layer=body.get('layer','BODY'),units=body['units'],origin_mm=body.get('origin_mm',(0,0)))
        prepare_cad_body(self.root,points)
        anchors=self.project.data['geometry'].get('anchors')
        if anchors:
            locations=read_anchors(self.project.resolve(anchors['path']),units=anchors['units'],origin_mm=anchors.get('origin_mm',(0,0)))
            center_y=(min(p[1] for p in points)+max(p[1] for p in points))/2
            if anchors.get('frame','cad')=='cad':
                locations={k:[x,y-center_y] for k,(x,y) in locations.items()}
            elif anchors['frame']!='body_center':
                raise ValueError('Anchor frame must be cad or body_center')
            instrument=json.loads((self.root/'config/full_guitar.json').read_text())
            layout=instrument.setdefault('hardware_layout',{})
            for name,point in locations.items():
                if name in ['BRIDGE','NECK_PICKUP','BRIDGE_PICKUP','SINGLE_PICKUP']:
                    if abs(point[0])>1e-6:
                        raise ValueError(f'{name} must lie on the instrument centerline')
                    if name=='BRIDGE':instrument['bridge_saddle_y_mm']=point[1]
                    else:layout[name.lower()+'_y_mm']=point[1]
                elif name in ['VOLUME','TONE','SELECTOR']:
                    layout[name.lower()+'_mm']=point
                else:
                    raise ValueError(f'Unsupported hardware anchor: {name}')
            (self.root/'config/full_guitar.json').write_text(json.dumps(instrument,indent=2))
            (self.root/'geometry/hardware-anchors.json').write_text(json.dumps(locations,indent=2))
        head=self.project.data['geometry'].get('headstock')
        head_input=self.root/'geometry/full_guitar/headstock-input.json'
        if head:
            points=read_outline(self.project.resolve(head['path']),layer=head.get('layer','HEADSTOCK'),units=head['units'],origin_mm=head.get('origin_mm',(0,0)))
            head_input.write_text(json.dumps({'points_mm':points,'source_kind':'cad'}))
        elif head_input.exists():
            head_input.unlink()
        validate_texture_coverage(self.root)
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

    def build(self,skip_pending=False):
        self.prepare(skip_pending=skip_pending)
        key=self.model_key()
        if reusable(self.root,'model',key):
            print('Reusing verified model',self.root/'blender/full_guitar.blend')
            return self.root/'blender/full_guitar.blend'
        self.blender_script('material_template.py')
        self.blender_script('full_guitar.py','blender/material_template.blend')
        self.blender_script('validate_full_guitar.py','blender/full_guitar.blend')
        outputs=[self.root/p for p in ['blender/material_template.blend','blender/full_guitar/template-validation.json','blender/full_guitar.blend','blender/full_guitar/validation.json','geometry/full_guitar/model-validation.json','geometry/full_guitar/carved_body.obj']]
        record(self.root,'model',key,outputs)
        return self.root/'blender/full_guitar.blend'

    def model_key(self):
        surface={k:v for k,v in self.project.configs['surface'].items() if k!='placements'}
        instrument=json.loads((self.root/'config/full_guitar.json').read_text())
        code=[*list((CODE_ROOT/'blender/scripts').glob('*.py')),CODE_ROOT/'prepare_full_guitar.py',*list((CODE_ROOT/'src/guitar_finish_simulator').glob('*.py'))]
        geometry=[self.root/'geometry/outline.json',self.root/'geometry/full_guitar/headstock-outline.json',self.root/'geometry/full_guitar/carve-field.npz']
        executable=Path(self.blender).resolve()
        return fingerprint({'surface':surface,'instrument':instrument,'code':{str(p.relative_to(CODE_ROOT)):digest(p) for p in code},'artifacts':{str(p.relative_to(self.root)):digest(p) for p in geometry},'blender':[str(executable),executable.stat().st_size,executable.stat().st_mtime_ns]})

    def render(self, preset=None, candidates=(), view='front', preview=False, comparison=False):
        preset=preset or self.project.configs['instrument']['default_preset']
        unknown=set(candidates)-set(self.project.candidates)
        if unknown:
            raise SpecificationError('Unknown candidate filenames: '+', '.join(sorted(unknown)))
        if preset!='all' and preset not in self.project.configs['finishes']:
            raise SpecificationError(f'Unknown finish preset: {preset}')
        requested=candidates or [self.project.configs['instrument']['default_candidate']]
        if any(self.project.candidates[name].get('crop_review_required') for name in requested):
            raise SpecificationError('Review the uploaded crop and save wood settings before rendering')
        self.build(skip_pending=True)
        arguments=['--preset',preset,'--camera',view,'--save-scene']
        for name in candidates:
            arguments+=['--candidate',name]
        if preview:
            arguments.append('--preview')
        if comparison:
            arguments+=['--comparison','--all']
        self.blender_script('render_full_guitar.py','blender/full_guitar.blend',arguments)

    def batch(self,hero_views=True):
        """Render complete comparisons and enlarged PRS views against one built model."""
        from .delivery import validate_delivery,create_contact_sheets
        self.build()
        self.blender_script('render_full_guitar.py','blender/full_guitar.blend',['--preset','all','--all','--comparison'])
        if hero_views:
            for preset in [p for p in ['prs_reference','extreme_black'] if p in self.project.configs['finishes']]:
                self.blender_script('render_full_guitar.py','blender/full_guitar.blend',['--preset',preset,'--camera','all'])
        self.blender_script('render_full_guitar.py','blender/full_guitar.blend',['--preset','prs_reference','--all','--camera','carve'])
        report=validate_delivery(self.root,require_enlarged=True,hero_views=hero_views)
        create_contact_sheets(self.root,hero_views=hero_views)
        return report
