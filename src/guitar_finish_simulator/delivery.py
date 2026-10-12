"""Validate a complete candidate/finish matrix and assemble photograph comparisons."""
import hashlib
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .project import SpecificationError


def validate_delivery(root, *, require_enlarged=False, hero_views=True, require_controls=True):
    root=Path(root)
    manifest=json.loads((root/'assets/textures/processed/manifest.json').read_text())
    presets=json.loads((root/'config/finishes.json').read_text())
    surface=json.loads((root/'config/project.json').read_text())
    instrument=json.loads((root/'config/full_guitar.json').read_text())
    model=json.loads((root/'blender/full_guitar/validation.json').read_text())
    signature=model['geometry_signature']
    def verify(path,candidate,preset,view):
        record=json.loads(path.with_suffix('.json').read_text())
        with Image.open(path) as image:
            size=image.size
        expected={'candidate':candidate['source_filename'],'preset':preset,'camera':view,'geometry_signature':signature,'bookmatch':candidate['status'],'resolution':list(size),'engine':'CYCLES','seed':17,'texture_placement':surface.get('placements',{}).get(candidate['source_filename'],{})}
        for key,value in expected.items():
            if record.get(key)!=value:
                raise SpecificationError(f'{path}: mismatched {key}')
        if require_controls and record.get('finish_controls')!=presets[preset]:
            raise SpecificationError(f'{path}: stale finish controls; rerender before delivery')
        if require_controls:
            actual=hashlib.sha256((root/'assets/textures/bookmatched'/f"{candidate['source_filename']}.png").read_bytes()).hexdigest()
            if record.get('source_sha256')!=candidate['sha256'] or record.get('texture_sha256')!=actual:
                raise SpecificationError(f'{path}: stale photograph or texture')
        return record
    for candidate in manifest:
        path=root/'assets/originals'/candidate['source_filename']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=candidate['sha256']:
            raise SpecificationError(f'Source photograph changed: {path}')
    comparisons=[]
    for preset in presets:
        for candidate in manifest:
            path=root/'renders/full_guitar/comparisons'/preset/f"{candidate['source_filename']}.front.png"
            comparisons.append(verify(path,candidate,preset,'front'))
    settings={(tuple(r['resolution']),r['samples'],r['seed']) for r in comparisons}
    if len(settings)!=1:
        raise SpecificationError('Comparison resolution, samples or seed changed across candidates')
    default=next(c for c in manifest if c['source_filename']==instrument['default_candidate'])
    hero_presets=[p for p in ['prs_reference','extreme_black'] if p in presets]
    heroes=[]
    if hero_views:
        for preset in hero_presets:
            for view in ['front','perspective','rear','carve']:
                path=root/'renders/full_guitar/hero'/preset/f"{default['source_filename']}.{view}.png"
                heroes.append(verify(path,default,preset,view))
    enlarged=[]
    if require_enlarged:
        for candidate in manifest:
            path=root/'renders/full_guitar/hero/prs_reference'/f"{candidate['source_filename']}.carve.png"
            record=verify(path,candidate,'prs_reference','carve')
            if min(record['resolution'])<1600:
                raise SpecificationError(f'{path}: enlarged PRS render must be at least 1600 x 1600')
            enlarged.append(record)
    report={'full_comparison_renders':len(comparisons),'hero_renders':len(heroes),'enlarged_prs_renders':len(enlarged),'candidates':len(manifest),'finishes':len(presets),'identical_geometry_cameras_lighting_verified':True,'geometry_signature':signature,'source_hashes_verified':True,'finish_controls_verified':require_controls,'model_checks':model,'blender_version':model['blender_version'],'engine':model['engine']}
    folder=root/'renders/full_guitar';folder.mkdir(parents=True,exist_ok=True)
    (folder/'validation.json').write_text(json.dumps(report,indent=2))
    return report


def create_contact_sheets(root, *, hero_views=True):
    root=Path(root)
    manifest=json.loads((root/'assets/textures/processed/manifest.json').read_text())
    presets=json.loads((root/'config/finishes.json').read_text())
    surface=json.loads((root/'config/project.json').read_text())
    instrument=json.loads((root/'config/full_guitar.json').read_text())
    font_file=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
    font=ImageFont.truetype(str(font_file),23) if font_file.exists() else ImageFont.load_default(size=23)
    small=ImageFont.truetype(str(font_file),18) if font_file.exists() else ImageFont.load_default(size=18)
    def paste(canvas,image,box):
        image=image.convert('RGB');image.thumbnail((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
        canvas.paste(image,(box[0]+(box[2]-box[0]-image.width)//2,box[1]+(box[3]-box[1]-image.height)//2))
    out=root/'renders/full_guitar/contact_sheets';out.mkdir(parents=True,exist_ok=True)
    columns=min(4,len(manifest));rows=math.ceil(len(manifest)/columns)
    for preset,controls in presets.items():
        sheet=Image.new('RGB',(columns*700,rows*1200),'#202020');draw=ImageDraw.Draw(sheet)
        for i,candidate in enumerate(manifest):
            name=candidate['source_filename'];x=(i%columns)*700;y=(i//columns)*1200
            with Image.open(root/'assets/textures/processed'/f'{name}.original-crop.png') as original:
                raw=original.copy()
            angle=surface.get('placements',{}).get(name,{}).get('rotation_deg',0)
            if angle:raw=raw.rotate(-angle,expand=True)
            draw.text((x+14,y+14),name,font=font,fill='white');draw.text((x+14,y+46),controls['label'],font=small,fill='#cccccc')
            draw.text((x+14,y+75),'Physical photographed pair' if candidate['status']=='physical' else 'SIMULATED bookmatch / one board',font=small,fill='#bbbbbb')
            draw.text((x+14,y+113),'Raw bookmatch',font=small,fill='white');draw.text((x+316,y+113),'Full guitar / fixed front camera',font=small,fill='white')
            paste(sheet,raw,(x+14,y+150,x+298,y+1145))
            with Image.open(root/'renders/full_guitar/comparisons'/preset/f'{name}.front.png') as image:
                paste(sheet,image,(x+308,y+145,x+690,y+1170))
        sheet.save(out/f'{preset}.png')
    if hero_views:
        name=instrument['default_candidate']
        for preset in [p for p in ['prs_reference','extreme_black'] if p in presets]:
            sheet=Image.new('RGB',(2400,1900),'#202020');draw=ImageDraw.Draw(sheet)
            for i,view in enumerate(['front','perspective','rear']):
                with Image.open(root/'renders/full_guitar/hero'/preset/f'{name}.{view}.png') as image:
                    paste(sheet,image,(i*800+10,90,(i+1)*800-10,1830))
                draw.text((i*800+20,25),view.title(),font=font,fill='white')
            draw.text((20,1860),f"{name} | {presets[preset]['label']} | {instrument['body_center_thickness_mm']} mm center / {instrument['body_rim_thickness_mm']} mm nominal rim",font=small,fill='#cccccc')
            sheet.save(out/f'{preset}-views.png')
    return out
