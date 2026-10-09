"""Contact sheets and output acceptance checks, using actual Cycles PNGs."""
import json, hashlib, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/'assets/textures/processed/manifest.json').read_text())
PRESETS=json.loads((ROOT/'config/finishes.json').read_text())
PROJECT=json.loads((ROOT/'config/project.json').read_text())
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
FONT=ImageFont.truetype(fontpath,22); SMALL=ImageFont.truetype(fontpath,17)

def paste_fit(canvas,im,box):
    im=im.convert('RGB'); im.thumbnail((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
    canvas.paste(im,(box[0]+(box[2]-box[0]-im.width)//2,box[1]+(box[3]-box[1]-im.height)//2))

def calibration():
    sheet=Image.new('RGB',(1800,850),'#202020'); d=ImageDraw.Draw(sheet)
    source=Image.open(ROOT/'assets/references/prs.png').crop((15,85,956,765)).rotate(90,expand=True)
    paste_fit(sheet,source,(10,70,590,820)); d.text((20,20),'Supplied PRS reference photograph',font=FONT,fill='white')
    for i,name in enumerate(['20261009_113100.jpg','20261009_113155.jpg'],1):
        paste_fit(sheet,Image.open(ROOT/'renders/prs_reference'/f'{name}.png'),(i*600,70,(i+1)*600,820))
        d.text((i*600+20,20),name+' / Cycles',font=FONT,fill='white')
    sheet.save(ROOT/'renders/calibration/reference-comparison.png')
    (ROOT/'renders/calibration/calibration.json').write_text(json.dumps({'candidates':['20261009_113100.jpg','20261009_113155.jpg'],'reference':'prs.png','initial_issue':'Too much silver across the face; initial black perimeter was too weak; cool grey highlights needed the PRS reference natural-maple warmth','changes':{'light_power_watts':[15,5,7],'sandback_exponent':'2.4 - sandback_strength','highlight_brightness':.65,'overall_darkness':.75,'edge_opacity':1,'edge_hold':.12,'burst_width':.42,'minimum_burst_halfwidth_mm':100,'highlight_palette':PRESETS['prs_reference']['palette'][2:]},'assessment':'Neutral dark charcoal, pale natural-maple highlights from the photo-derived figure, black shadows and perimeter; studio highlight placement and source grain differ from PRS. Pencil layout marks retained. Artistic visual calibration, not measured material recovery.'},indent=2))

def main():
    # Rasterize the exported real mesh UV edges for easy inspection.
    uv=Image.new('RGB',(1024,1024),'#202020'); uvdraw=ImageDraw.Draw(uv)
    for segment in re.findall(r'M ([\d.-]+),([\d.-]+) L ([\d.-]+),([\d.-]+)',(ROOT/'geometry/uv-mesh.svg').read_text()): uvdraw.line(tuple(map(float,segment)),fill='#7592ab',width=1)
    uvdraw.line((512,0,512,1024),fill='#ff6655',width=2); uv.save(ROOT/'geometry/uv-layout.png')
    records=[]
    for preset,spec in PRESETS.items():
        sheet=Image.new('RGB',(3200,1400),'#202020'); d=ImageDraw.Draw(sheet)
        for i,candidate in enumerate(MANIFEST):
            name=candidate['source_filename']; x=(i%4)*800; y=(i//4)*700
            raw=Image.open(ROOT/'assets/textures/processed'/f'{name}.original-crop.png')
            angle=PROJECT['placements'].get(name,{}).get('rotation_deg',0)
            if angle: raw=raw.rotate(-angle,expand=True)
            path=ROOT/'renders'/preset/f'{name}.png'; finished=Image.open(path)
            record=json.loads(path.with_suffix('.render.json').read_text())
            assert record['candidate']==name and record['preset']==preset
            assert finished.size==tuple(record['resolution'])
            if preset=='prs_reference': assert min(finished.size)>=1600
            assert hashlib.sha256((ROOT/'assets/originals'/name).read_bytes()).hexdigest()==candidate['sha256']
            records.append(record)
            d.text((x+16,y+14),name,font=FONT,fill='white')
            d.text((x+16,y+44),spec['label'],font=SMALL,fill='#cccccc')
            label='Physical photographed pair' if candidate['status']=='physical' else 'SIMULATED bookmatch from one board'
            d.text((x+16,y+71),label,font=SMALL,fill='#bbbbbb')
            d.text((x+20,y+108),'Raw rectified bookmatch',font=SMALL,fill='white')
            d.text((x+355,y+108),'Finished body / fixed front camera',font=SMALL,fill='white')
            paste_fit(sheet,raw,(x+12,y+145,x+335,y+675)); paste_fit(sheet,finished,(x+340,y+145,x+795,y+675))
        sheet.save(ROOT/'renders/comparisons'/f'{preset}.png')
    assert len(records)==32
    signatures={r['signature'] for r in records}; assert len(signatures)==1,'Geometry/camera/light invariant differs'
    calibration()
    validation={'candidate_count':8,'physical_bookmatches':4,'simulated_bookmatches':4,'render_count':32,'finish_count':4,'prs_min_resolution':[1600,1600],'invariant_signature':next(iter(signatures)),'all_front_scene_signatures_identical':True,'source_hashes_verified':True,'saved_scene':json.loads((ROOT/'blender/scene-validation.json').read_text()),'mesh':json.loads((ROOT/'geometry/mesh-validation.json').read_text()),'outline':json.loads((ROOT/'geometry/outline-validation.json').read_text())}
    (ROOT/'renders/validation.json').write_text(json.dumps(validation,indent=2))
    print(json.dumps(validation,indent=2))
if __name__=='__main__': main()
