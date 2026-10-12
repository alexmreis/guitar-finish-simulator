"""Human-selected reference samples and persistent, reproducible calibration."""
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from .project import SpecificationError

def sample_reference(path, regions):
    image=np.asarray(Image.open(path).convert('RGB'))
    height,width=image.shape[:2]
    if len(regions)!=4:
        raise SpecificationError('Select four reference regions: shadows, base, figure, bright figure')
    palette=[]
    for region in regions:
        x0,y0,x1,y1=map(int,region)
        if not 0<=x0<x1<=width or not 0<=y0<y1<=height:
            raise SpecificationError('Reference region is empty or outside the photograph')
        values=np.median(image[y0:y1,x0:x1],axis=(0,1)).astype(int)
        palette.append('#'+''.join(f'{v:02X}' for v in values))
    return {'palette':palette,'regions':regions,'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'limitation':'Reference pixels include unknown lighting, exposure and processing; these are palette suggestions, not recovered material properties.'}

class CalibrationSession:
    def __init__(self,specification,folder):
        import json
        from .project import Project
        self.folder=Path(folder).resolve();self.folder.mkdir(parents=True,exist_ok=True)
        self.path=self.folder/'project.json'
        if not self.path.exists():
            project=Project.load(specification)
            data=json.loads(json.dumps(project.data))
            data['config']=project.configs
            data['inputs']={k:str(project.resolve(v)) for k,v in data['inputs'].items() if k!='candidates'}
            data['inputs']['candidates']=project.candidates
            data['geometry']={k:{**v,'path':str(project.resolve(v['path']))} for k,v in data['geometry'].items()}
            self.path.write_text(json.dumps(data,indent=2))

    def data(self):
        import json
        return json.loads(self.path.read_text())

    def save(self,data):
        import json
        from .project import Project
        path=self.folder/'project.pending.json'
        path.write_text(json.dumps(data,indent=2,allow_nan=False))
        try:
            Project.load(path).validate_inputs()
            path.replace(self.path)
        finally:
            path.unlink(missing_ok=True)

    def update_finish(self,preset,controls):
        data=self.data()
        if preset not in data['config']['finishes']:
            raise SpecificationError('Unknown finish preset')
        existing=data['config']['finishes'][preset]
        for key,value in controls.items():
            if key not in existing:
                raise SpecificationError(f'Unknown finish control: {key}')
        existing.update(controls)
        self.save(data)
        return existing

    def update_wood(self,candidate,controls):
        data=self.data()
        if candidate not in data['inputs']['candidates']:
            raise SpecificationError('Unknown source photograph')
        allowed={'quads','rotation','alignment_shift_px','seam_edge','width_mm'}
        if set(controls)-allowed:
            raise SpecificationError('Unknown wood calibration control')
        if controls.get('alignment_shift_px','auto') is None:
            controls=dict(controls)
            controls.pop('alignment_shift_px')
            data['inputs']['candidates'][candidate].pop('alignment_shift_px',None)
        data['inputs']['candidates'][candidate].update(controls)
        self.save(data)
        return data['inputs']['candidates'][candidate]

    def update_placement(self,candidate,controls):
        import math
        data=self.data()
        if candidate not in data['inputs']['candidates'] or set(controls)-{'x_mm','y_mm','rotation_deg'}:
            raise SpecificationError('Unknown photograph or placement control')
        if not all(isinstance(value,(int,float)) and math.isfinite(value) for value in controls.values()):
            raise SpecificationError('Placement controls must be finite numbers')
        data['config']['surface'].setdefault('placements',{}).setdefault(candidate,{}).update(controls)
        self.save(data)
        return data['config']['surface']['placements'][candidate]
