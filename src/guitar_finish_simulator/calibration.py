"""Human-selected reference samples and persistent, reproducible calibration."""
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
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
        if 'quads' in controls and 'crop_review_required' in data['inputs']['candidates'][candidate]:
            data['inputs']['candidates'][candidate]['crop_review_required']=False
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

    def upload_wood(self,filename,content,*,bookmatch='simulated',figure_type='flame',rotation=0,width_mm=None):
        """Register an actual photograph in workspace-owned storage, without rewriting it."""
        import io
        import shutil
        from .project import Project
        if not filename or Path(filename).name!=filename or '\\' in filename or '\x00' in filename or filename.startswith('.'):
            raise SpecificationError('Use a source filename without directories')
        if Path(filename).suffix.lower() not in ['.jpg','.jpeg','.png','.webp']:
            raise SpecificationError('Upload a JPEG, PNG or WebP photograph')
        if bookmatch not in ['physical','simulated'] or figure_type not in ['flame','quilt','other']:
            raise SpecificationError('Choose a single board or physical pair and a figure type')
        if not 0<len(content)<=25*1024*1024:
            raise SpecificationError('Photograph must be between 1 byte and 25 MB')
        data=self.data()
        if filename.casefold() in {name.casefold() for name in data['inputs']['candidates']}:
            raise SpecificationError(f'A photograph named {filename} already exists; originals are never overwritten')
        try:
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in ['JPEG','PNG','WEBP']:
                    raise SpecificationError('Upload a JPEG, PNG or WebP photograph')
                image.load();width,height=ImageOps.exif_transpose(image).size
        except (OSError,Image.DecompressionBombError) as error:
            raise SpecificationError('The uploaded file is not a readable photograph') from error
        if min(width,height)<64:
            raise SpecificationError('Photograph must be at least 64 pixels on each side')
        right,bottom=width-1,height-1
        quads=[[[0,0],[right,0],[right,bottom],[0,bottom]]]
        if bookmatch=='physical':
            seam=right/2
            quads=[[[0,0],[seam,0],[seam,bottom],[0,bottom]],[[seam,0],[right,0],[right,bottom],[seam,bottom]]]
        spec={'status':bookmatch,'rotation':int(rotation),'figure_type':figure_type,'quads':quads,
              'alignment_max_shift_fraction':.045,'crop_review_required':True,'exif_orientation_applied':True}
        if width_mm is not None:spec['width_mm']=float(width_mm)
        project=Project.load(self.path)
        photos=self.folder/'photos';photos.mkdir(exist_ok=True)
        for name in project.candidates:
            target=photos/name
            if not target.exists():shutil.copy2(project.resolve(project.data['inputs']['photos'])/name,target)
        target=photos/filename
        if target.exists():
            raise SpecificationError(f'A photograph named {filename} already exists; originals are never overwritten')
        with target.open('xb') as stream:stream.write(content)
        data['inputs']['photos']=str(photos)
        data['inputs']['candidates'][filename]=spec
        try:
            self.save(data)
        except Exception:
            target.unlink();raise
        return {'candidate':filename,'specification':spec,'pixels':[width,height],
                'source_sha256':hashlib.sha256(content).hexdigest(),'message':'Review the crop corners and orientation, then save wood settings before rendering.'}
