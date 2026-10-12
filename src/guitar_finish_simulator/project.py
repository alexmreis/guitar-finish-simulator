"""Versioned project inputs; relative paths resolve beside the specification."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil

class SpecificationError(ValueError):
    """An input cannot be used without an explicit correction."""

@dataclass(frozen=True)
class Project:
    path: Path
    data: dict
    configs: dict
    candidates: dict

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        data = json.loads(path.read_text())
        if data.get('version') != 1:
            raise SpecificationError('project.version must be 1')
        def read(value):
            return value if isinstance(value, dict) else json.loads((path.parent / value).read_text())
        configs = {key: read(data['config'][key]) for key in ['surface', 'instrument', 'finishes']}
        instrument = configs['instrument']
        if not 0 < instrument['body_rim_thickness_mm'] <= instrument['body_center_thickness_mm']:
            raise SpecificationError('body rim thickness must be positive and no greater than center thickness')
        from .finishes import validate_finish
        for preset,controls in configs['finishes'].items():
            validate_finish(preset,controls)
        candidates = read(data['inputs']['candidates'])
        if not candidates:
            raise SpecificationError('At least one wood photograph is required')
        for name,spec in candidates.items():
            if spec.get('status') not in ['physical','simulated']:
                raise SpecificationError(f'{name}: bookmatch status must be physical or simulated')
            if 'width_mm' in spec and (not isinstance(spec['width_mm'],(int,float)) or not math.isfinite(spec['width_mm']) or spec['width_mm']<=0):
                raise SpecificationError(f'{name}: width_mm must be a positive finite number')
            count=len(spec.get('quads',[]))
            if spec['status']=='physical' and count!=2:
                raise SpecificationError(f'{name}: physical bookmatches require two photographed halves')
            if spec['status']=='simulated' and count!=1:
                raise SpecificationError(f'{name}: simulated bookmatches require one photographed board')
            if spec.get('rotation',0) not in [0,90,180,270]:
                raise SpecificationError(f'{name}: crop rotation must be 0, 90, 180 or 270 degrees')
        return cls(path, data, configs, candidates)

    def resolve(self, value):
        return (self.path.parent / value).resolve()

    def materialize(self, destination):
        """Copy declared inputs; never mutate originals or reuse another project's files."""
        root = Path(destination).resolve()
        for name in ['config','assets/originals','assets/references','assets/textures/processed',
                     'geometry/full_guitar','blender/full_guitar','renders/comparisons']:
            (root / name).mkdir(parents=True, exist_ok=True)
        files = {}
        for name in self.candidates:
            source = self.resolve(self.data['inputs']['photos']) / name
            target = root / 'assets/originals' / name
            if source.resolve()!=target.resolve():
                shutil.copy2(source, target)
            files[str(target.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
        for key, filename in [('design_reference','Umbraeternal.JPG'), ('finish_reference','prs.png')]:
            if key not in self.data['inputs']:
                continue
            source = self.resolve(self.data['inputs'][key])
            target = root / 'assets/references' / filename
            if source.resolve()!=target.resolve():
                shutil.copy2(source, target)
            files[str(target.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
        for key, filename in [('surface','project.json'),('instrument','full_guitar.json'),('finishes','finishes.json')]:
            (root / 'config' / filename).write_text(json.dumps(self.configs[key], indent=2))
        (root / 'config/candidates.json').write_text(json.dumps(self.candidates, indent=2))
        geometry={}
        for role,spec in self.data['geometry'].items():
            source=self.resolve(spec['path'])
            target=root/'assets/references/cad'/role/source.name
            target.parent.mkdir(parents=True,exist_ok=True)
            if source.resolve()!=target.resolve():
                shutil.copy2(source,target)
            relative=str(target.relative_to(root))
            geometry[role]={**spec,'path':relative}
            files[relative]=hashlib.sha256(source.read_bytes()).hexdigest()
        snapshot={**self.data,'inputs':{'photos':'assets/originals','candidates':'config/candidates.json','finish_reference':'assets/references/prs.png'},
                  'config':{'surface':'config/project.json','instrument':'config/full_guitar.json','finishes':'config/finishes.json'},'geometry':geometry}
        if 'design_reference' in self.data['inputs']:
            snapshot['inputs']['design_reference']='assets/references/Umbraeternal.JPG'
        (root/'project.snapshot.json').write_text(json.dumps(snapshot,indent=2))
        lock = {'version': 1, 'name': self.data['name'], 'specification': self.data,
                'configs': self.configs, 'candidates': self.candidates, 'sources': files}
        (root / 'project.lock.json').write_text(json.dumps(lock, indent=2))
        return root

    def validate_inputs(self):
        """Fail before creating output when declared source data is missing."""
        from .cad import read_outline,read_anchors
        missing=[]
        for name in self.candidates:
            if Path(name).name != name:
                raise SpecificationError('Photo identifiers must be source filenames, without directories')
            source=self.resolve(self.data['inputs']['photos'])/name
            if not source.is_file():
                missing.append(str(source))
        if missing:
            raise SpecificationError('Missing wood photographs: '+', '.join(missing))
        from .photographs import open_photograph
        from .cad import validate_contour
        for name,spec in self.candidates.items():
            with open_photograph(self.resolve(self.data['inputs']['photos'])/name,spec) as image:
                width,height=image.size
            for quad in spec['quads']:
                if len(quad)!=4 or any(len(p)!=2 for p in quad):
                    raise SpecificationError(f'{name}: a crop needs four 2D corners')
                if any(not 0<=x<width or not 0<=y<height for x,y in quad):
                    raise SpecificationError(f'{name}: crop corner outside original photograph')
                validate_contour([tuple(p) for p in quad])
        required=['finish_reference']+([] if 'headstock' in self.data['geometry'] else ['design_reference'])
        for key in required:
            if key not in self.data['inputs']:
                raise SpecificationError(f'Missing {key}; supply headstock CAD or a design photograph')
            source=self.resolve(self.data['inputs'][key])
            if not source.is_file():
                raise SpecificationError(f'Missing {key}: {source}')
        for key, spec in self.data['geometry'].items():
            source=self.resolve(spec['path'])
            if not source.is_file():
                raise SpecificationError(f'Missing {key} CAD: {source}')
            if key=='anchors':
                read_anchors(source,units=spec['units'],origin_mm=spec.get('origin_mm',(0,0)))
            else:
                read_outline(source,layer=spec.get('layer',key.upper()),units=spec['units'],origin_mm=spec.get('origin_mm',(0,0)))
        return {'valid':True,'name':self.data['name'],'candidates':len(self.candidates),'finishes':len(self.configs['finishes'])}
