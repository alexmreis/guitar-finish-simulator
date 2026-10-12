"""Deterministic photograph rectification; editable surveyed corners are in config/."""
import hashlib, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

def save(path, a):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a).save(path)

def align_halves(left, right, spec):
    """Register photographed seam-adjacent figure; translation only, common crop.

    Mirroring is used only to compare corresponding seam neighborhoods, never
    to replace a physical half. Automatic shifts can be overridden in the spec.
    """
    height,width=left.shape[:2]
    strip_fraction=.08 if spec.get('figure_type')=='quilt' else .18
    strip_width=max(12,round(width*strip_fraction))
    margin=max(2,round(width*.025))
    def feature(strip):
        lum=cv2.cvtColor(strip,cv2.COLOR_RGB2GRAY).astype(np.float32)/255
        # Remove broad illumination, retain dark flame bands / quilt cell boundaries.
        normalized=lum-cv2.GaussianBlur(lum,(0,0),8)
        profile=np.median(normalized,axis=1)
        profile=cv2.GaussianBlur(profile[:,None],(1,0),1.1).ravel()
        return profile
    lp=feature(left[:,width-margin-strip_width:width-margin])
    rp=feature(right[:,margin:margin+strip_width])
    limit=round(height*spec.get('alignment_max_shift_fraction',.045))
    trim=max(limit,round(height*.08))
    def score(shift):
        ys=np.arange(trim,height-trim)
        a=lp[ys]; b=rp[ys+shift]
        a=a-a.mean(); b=b-b.mean()
        return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-10))
    scores=[(score(shift),shift) for shift in range(-limit,limit+1)]
    best,shift=max(scores,key=lambda pair:pair[0]-.002*abs(pair[1])/max(limit,1))
    baseline=score(0)
    # Reject incidental matches unless alignment improves correlation measurably.
    if best<baseline+.025: shift=0
    if 'alignment_shift_px' in spec: shift=int(spec['alignment_shift_px'])
    assert abs(shift)<=limit,'Manual alignment outside conservative shift limit'
    lo=max(0,-shift); hi=min(height,height-shift)
    result={'method':'seam-adjacent dark-feature cross-correlation; vertical translation and overlap crop',
            'right_sample_offset_px':shift,'left_crop_rows':[lo,hi],
            'right_crop_rows':[lo+shift,hi+shift],
            'correlation_before':baseline,'correlation_after':score(shift),
            'max_shift_px':limit,'figure_type':spec.get('figure_type','flame'),
            'no_half_replaced_or_synthesized':True}
    return left[lo:hi],right[lo+shift:hi+shift],result

def prepare_wood(root: Path, input_dir: Path):
    """Write corrected textures and provenance into an isolated project directory."""
    specs=json.loads((root/'config/candidates.json').read_text())
    project=json.loads((root/'config/project.json').read_text())
    metadata=[]
    for name,spec in specs.items():
        source=input_dir/name
        rgb=np.array(Image.open(source).convert('RGB'))
        annotation=rgb.copy(); halves=[]; transforms=[]
        for quad in spec['quads']:
            q=np.float32(quad)
            w=round((np.linalg.norm(q[1]-q[0])+np.linalg.norm(q[2]-q[3]))/2)
            h=round((np.linalg.norm(q[3]-q[0])+np.linalg.norm(q[2]-q[1]))/2)
            target=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
            matrix=cv2.getPerspectiveTransform(q,target)
            crop=cv2.warpPerspective(rgb,matrix,(w,h),flags=cv2.INTER_CUBIC)
            if spec['rotation']: crop=np.rot90(crop,spec['rotation']//90).copy()
            halves.append(crop)
            transforms.append(matrix.tolist())
            cv2.polylines(annotation,[q.astype(np.int32)],True,(255,40,40),3)
        stem=name
        save(root/'assets/textures/processed'/f'{stem}.crop-diagnostic.png',annotation)
        # Preserve aspect ratio under rectification. For two halves use conservative
        # center crops to equal height; neither half is mirrored or independently stretched.
        height=min(a.shape[0] for a in halves)
        halves=[a[(a.shape[0]-height)//2:(a.shape[0]-height)//2+height] for a in halves]
        if spec['status']=='physical':
            width=min(a.shape[1] for a in halves)
            halves=[halves[0][:,-width:],halves[1][:,:width]]
            left,right,alignment=align_halves(halves[0],halves[1],spec)
            raw=np.concatenate([left,right],axis=1)
        else:
            half=halves[0]
            if spec.get('seam_edge','right')=='left': half=half[:,::-1]
            raw=np.concatenate([half,half[:,::-1]],axis=1)
            alignment={'method':'exact mirror about board edge; figure continuous at seam','right_sample_offset_px':0,'no_synthetic_detail':True,'seam_edge':spec.get('seam_edge','right')}
        save(root/'assets/textures/processed'/f'{stem}.original-crop.png',raw)
        source_crop=raw if spec['status']=='physical' else halves[0]
        save(root/'assets/textures/processed'/f'{stem}.source-crop.png',source_crop)
        # Small multiplicative illumination correction: at most +/-6%; fine figure survives.
        linear=raw.astype(np.float32)/255
        gray=cv2.cvtColor(linear,cv2.COLOR_RGB2GRAY)
        illumination=cv2.GaussianBlur(gray,(0,0),max(raw.shape[:2])/10)
        gain=np.clip(np.median(illumination)/np.maximum(illumination,.05),.94,1.06)
        corrected=np.clip(linear*gain[:,:,None],0,1)
        means=corrected.mean(axis=(0,1))
        balance=np.clip(means.mean()/means,.97,1.03)
        corrected=np.uint8(np.clip(corrected*balance,0,1)*255)
        save(root/'assets/textures/corrected'/f'{stem}.png',corrected if spec['status']=='physical' else corrected[:,:corrected.shape[1]//2])
        save(root/'assets/textures/bookmatched'/f'{stem}.png',corrected)
        luminance=cv2.cvtColor(corrected,cv2.COLOR_RGB2GRAY).astype(np.float32)/255
        low=cv2.GaussianBlur(luminance,(0,0),max(raw.shape[:2])/22)
        if spec.get('figure_filter')=='horizontal_flame':
            # Emphasize photographed cross-grain curl, suppress longitudinal preparation
            # lines in the dye-response proxy. Original albedo remains unfiltered.
            directional=cv2.GaussianBlur(luminance,(0,0),sigmaX=4,sigmaY=.6)
            baseline=cv2.GaussianBlur(directional,(1,0),sigmaX=0,sigmaY=14)
            curl=directional-baseline
            calibration=[]
            if spec.get('balance_figure_halves') and spec['status']=='physical':
                seam=curl.shape[1]//2
                for start,end in [(0,seam),(seam,curl.shape[1])]:
                    half=curl[:,start:end]
                    margin=max(4,round(half.shape[1]*.1))
                    lo,hi=np.percentile(half[:,margin:-margin],[2,98])
                    curl[:,start:end]=np.clip((half-lo)/max(hi-lo,.01),0,1)
                    calibration.append({'columns':[start,end],'curl_percentiles':[float(lo),float(hi)]})
            else:
                lo,hi=np.percentile(curl,[2,98])
                curl=np.clip((curl-lo)/max(hi-lo,.01),0,1)
            fine=np.clip(.5+(luminance-low)*2,0,1)
            figure=.88*curl+.12*fine
        else:
            figure=.65*luminance+.35*np.clip(.5+(luminance-low)*2,0,1)
            lo,hi=np.percentile(figure,[2,98]); figure=np.clip((figure-lo)/max(hi-lo,.01),0,1)
        save(root/'assets/textures/processed'/f'{stem}.figure.png',np.uint8(figure*255))
        assumed_width=project['texture_width_mm']
        entry={'source_filename':name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            **spec,'figure_calibration':calibration if spec.get('figure_filter')=='horizontal_flame' else [],'alignment':alignment,'homographies':transforms,'bookmatched_pixels':[raw.shape[1],raw.shape[0]],
            'seam_u':.5,'assumed_width_mm':assumed_width,
            'assumed_height_mm':assumed_width*raw.shape[0]/raw.shape[1],
            'dimensions_measured':False,'illumination_gain_bounds':[.94,1.06],
            'notes':'Pencil marks, knots, and spalting retained. Crop corners manually surveyed from source. Width is a visual-study assumption, not evidence of usable blank size.'}
        # Enlarged seam diagnostic makes horizontal flame/quilt alignment reviewable.
        seam=raw.shape[1]//2; band=raw[:,max(0,seam-100):seam+100]
        save(root/'assets/textures/processed'/f'{stem}.seam.png',band)
        metadata.append(entry)
        (root/'assets/textures/processed'/f'{stem}.json').write_text(json.dumps(entry,indent=2))
    (root/'assets/textures/processed/manifest.json').write_text(json.dumps(metadata,indent=2))
    sheet=Image.new('RGB',(1600,1000),'#20242a'); draw=ImageDraw.Draw(sheet)
    for i,entry in enumerate(metadata):
        x=(i%4)*400; y=(i//4)*500
        im=Image.open(root/'assets/textures/bookmatched'/f"{entry['source_filename']}.png")
        im.thumbnail((360,420)); sheet.paste(im,(x+(400-im.width)//2,y+55))
        draw.text((x+15,y+10),entry['source_filename'],fill='white')
        draw.text((x+15,y+30),entry['status']+' bookmatch',fill='white')
    sheet.save(root/'renders/comparisons/preprocessed.png')
    print(f'Processed {len(metadata)} candidates')
    return metadata
