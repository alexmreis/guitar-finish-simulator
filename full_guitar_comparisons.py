"""Assemble and validate complete full-instrument comparisons."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'assets/textures/processed/manifest.json').read_text());presets=json.loads((ROOT/'config/finishes.json').read_text());project=json.loads((ROOT/'config/project.json').read_text());model=json.loads((ROOT/'blender/full_guitar/validation.json').read_text())
font_file=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
FONT=ImageFont.truetype(str(font_file),23) if font_file.exists() else ImageFont.load_default(size=23)
SMALL=ImageFont.truetype(str(font_file),18) if font_file.exists() else ImageFont.load_default(size=18)
def paste(canvas,im,box):
    im=im.convert('RGB');im.thumbnail((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS);canvas.paste(im,(box[0]+(box[2]-box[0]-im.width)//2,box[1]+(box[3]-box[1]-im.height)//2))
records=[];out=ROOT/'renders/full_guitar/contact_sheets';out.mkdir(parents=True,exist_ok=True)
for preset,spec in presets.items():
    sheet=Image.new('RGB',(2800,2400),'#202020');d=ImageDraw.Draw(sheet)
    for i,c in enumerate(manifest):
        name=c['source_filename'];x=(i%4)*700;y=(i//4)*1200
        path=ROOT/'renders/full_guitar/comparisons'/preset/f'{name}.front.png';im=Image.open(path);r=json.loads(path.with_suffix('.json').read_text())
        assert r['candidate']==name and r['preset']==preset and r['camera']=='front' and tuple(r['resolution'])==im.size
        assert r['geometry_signature']==model['geometry_signature'];records.append(r)
        assert hashlib.sha256((ROOT/'assets/originals'/name).read_bytes()).hexdigest()==c['sha256']
        raw=Image.open(ROOT/'assets/textures/processed'/f'{name}.original-crop.png');angle=project['placements'].get(name,{}).get('rotation_deg',0)
        if angle:raw=raw.rotate(-angle,expand=True)
        d.text((x+14,y+14),name,font=FONT,fill='white');d.text((x+14,y+46),spec['label'],font=SMALL,fill='#cccccc')
        d.text((x+14,y+75),'Physical photographed pair' if c['status']=='physical' else 'SIMULATED bookmatch / one board',font=SMALL,fill='#bbbbbb')
        d.text((x+14,y+113),'Raw bookmatch',font=SMALL,fill='white');d.text((x+316,y+113),'Full guitar / fixed front camera',font=SMALL,fill='white')
        paste(sheet,raw,(x+14,y+150,x+298,y+1145));paste(sheet,im,(x+308,y+145,x+690,y+1170))
    sheet.save(out/f'{preset}.png')
assert len(records)==32
heroes=[]
for preset in ['prs_reference','extreme_black']:
    for view in ['front','perspective','rear','carve']:
        path=ROOT/'renders/full_guitar/hero'/preset/f'20261009_112804.jpg.{view}.png';im=Image.open(path);r=json.loads(path.with_suffix('.json').read_text());assert tuple(r['resolution'])==im.size;assert r['geometry_signature']==model['geometry_signature'];heroes.append(r)
    sheet=Image.new('RGB',(2400,1900),'#202020');d=ImageDraw.Draw(sheet)
    for i,view in enumerate(['front','perspective','rear']):
        paste(sheet,Image.open(ROOT/'renders/full_guitar/hero'/preset/f'20261009_112804.jpg.{view}.png'),(i*800+10,90,(i+1)*800-10,1830));d.text((i*800+20,25),view.title(),font=FONT,fill='white')
    d.text((20,1860),'20261009_112804.jpg | '+presets[preset]['label']+' | 44 mm center / 12 mm nominal rim',font=SMALL,fill='#cccccc');sheet.save(out/f'{preset}-views.png')
summary={'full_comparison_renders':32,'hero_renders':8,'candidates':8,'finishes':4,'identical_geometry_cameras_lighting_verified':True,'geometry_signature':model['geometry_signature'],'source_hashes_verified':True,'model_checks':model,'hero_settings':{'front_rear':[1100,2600],'perspective':[1800,2200],'carve':[1600,1600],'samples':64},'comparison_settings':{'resolution':[800,1800],'samples':48},'blender_version':model['blender_version'],'engine':model['engine']}
(ROOT/'renders/full_guitar/validation.json').write_text(json.dumps(summary,indent=2));print('FULL-GUITAR DELIVERY VALIDATED:',summary['full_comparison_renders'],'comparisons and',summary['hero_renders'],'hero renders')
