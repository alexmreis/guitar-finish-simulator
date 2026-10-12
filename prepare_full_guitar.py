"""Prepare reproducible body carve fields and the illustrated headstock outline."""
import json, os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt,gaussian_filter,map_coordinates
ROOT=Path(os.environ.get('GFS_PROJECT_ROOT',Path(__file__).resolve().parent)).resolve()
cfg=json.loads((ROOT/'config/full_guitar.json').read_text());outline=json.loads((ROOT/'geometry/outline.json').read_text())
points=np.array(outline['points_mm']);points[:,1]-=outline['height_mm']/2
surface=json.loads((ROOT/'config/project.json').read_text())
step=.5;x0=-surface['texture_width_mm']/2;y0=-surface['texture_height_mm']/2;shape=(round(surface['texture_height_mm']/step)+1,round(surface['texture_width_mm']/step)+1)
mask=np.zeros(shape,np.uint8);pix=np.round((points-[x0,y0])/step).astype(np.int32);cv2.fillPoly(mask,[pix],255)
inside=distance_transform_edt(mask>0,sampling=step);outside=distance_transform_edt(mask==0,sampling=step)
distance=gaussian_filter(inside-outside,2/step)
t=np.clip(distance/cfg['carve_transition_mm'],0,1);blend=t*t*t*(t*(t*6-15)+10)
height=cfg['body_rim_thickness_mm']/2+(cfg['body_center_thickness_mm']-cfg['body_rim_thickness_mm'])/2*blend
height=np.maximum(height,cfg['body_rim_thickness_mm']/2)
dy,dx=np.gradient(height,step,step)
np.savez_compressed(ROOT/'geometry/full_guitar/carve-field.npz',height_mm=height.astype(np.float32),distance_mm=distance.astype(np.float32),dx=dx.astype(np.float32),dy=dy.astype(np.float32),step_mm=step,x0_mm=x0,y0_mm=y0)
Image.fromarray(np.uint8((height-cfg['body_rim_thickness_mm']/2)/max((cfg['body_center_thickness_mm']-cfg['body_rim_thickness_mm'])/2,.001)*255)[::-1]).save(ROOT/'geometry/full_guitar/carve-height.png')
head_input=ROOT/'geometry/full_guitar/headstock-input.json'
if head_input.exists():
    head_spec=json.loads(head_input.read_text());head=np.array(head_spec['points_mm'])
    (ROOT/'geometry/full_guitar/headstock-outline.json').write_text(json.dumps(head_spec,indent=2))
else:
    # Use the supplied headstock silhouette, not the different Sabre reference headstock.
    im=np.array(Image.open(ROOT/'assets/references/Umbraeternal.JPG').convert('RGB').resize((1376,1790)))
    headmask=np.uint8(np.min(im,axis=2)<190)*255;region=np.zeros_like(headmask);region[5:278,250:420]=255;headmask &= region
    contours,_=cv2.findContours(headmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);c=max(contours,key=cv2.contourArea).reshape(-1,2)
    c=cv2.approxPolyDP(c[:,None,:].astype(np.float32),.6,True).reshape(-1,2)
    scale=cfg['nut_width_mm']/78
    head=np.column_stack([(c[:,0]-338)*scale,(277-c[:,1])*scale])
    area=np.sum(head[:,0]*np.roll(head[:,1],-1)-head[:,1]*np.roll(head[:,0],-1))/2
    if area<0:head=head[::-1]
    (ROOT/'geometry/full_guitar/headstock-outline.json').write_text(json.dumps({'points_mm':head.tolist(),'source_reference':'Umbraeternal.JPG','reference_scale_mm_per_pixel':scale},indent=2))
    overlay=im[:300,240:430].copy();cv2.polylines(overlay,[np.int32(c-[240,0])],True,(30,220,80),2);Image.fromarray(overlay).save(ROOT/'geometry/full_guitar/headstock-overlay.png')
# Headstock-specific distance field for its own outline-following black finish.
lo=head.min(0)-3;hi=head.max(0)+3;size=512;uv=(head-lo)/(hi-lo);hm=np.zeros((size,size),np.uint8);cv2.fillPoly(hm,[np.int32(np.column_stack([uv[:,0],1-uv[:,1]])*(size-1))],255)
hd=distance_transform_edt(hm>0,sampling=((hi[1]-lo[1])/(size-1),(hi[0]-lo[0])/(size-1)))
Image.fromarray(np.uint16(np.clip(hd/((hi[0]-lo[0])/2),0,1)*65535)).save(ROOT/'geometry/full_guitar/headstock-distance.png')
(ROOT/'geometry/full_guitar/headstock-bounds.json').write_text(json.dumps({'min_mm':lo.tolist(),'max_mm':hi.tolist()}))
# Thickness cross-section through the broad lower bout.
y=-85.;hits=[]
for a,b in zip(points,np.roll(points,-1,axis=0)):
    if min(a[1],b[1])<=y<max(a[1],b[1]):hits.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
xs=np.linspace(min(hits),max(hits),500);z=map_coordinates(height,[(np.full(500,y)-y0)/step,(xs-x0)/step],order=1)
profile=[(float(x),float(v)) for x,v in zip(xs,z)]
path=' '.join(f'{x+180:.3f},{35-v:.3f}' for x,v in profile)+' '+' '.join(f'{x+180:.3f},{35+v:.3f}' for x,v in profile[::-1])
(ROOT/'geometry/full_guitar/body-section.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="250" viewBox="0 0 360 83"><polygon points="{path}" fill="#bfa681" stroke="#202020" stroke-width=".5"/><text x="125" y="80" font-size="5">{cfg['body_center_thickness_mm']} mm center / {cfg['body_rim_thickness_mm']} mm rim, before {cfg['edge_round_mm']} mm edge rounding</text></svg>')
print('Prepared body carve and headstock; center',height.max()*2,'mm; rim',cfg['body_rim_thickness_mm'],'mm')

# Clean surveyed silhouette: exclude the dimension extension line touching the button.
button=np.array([[273,143],[286,144],[300,147],[314,153],[328,161],[333,166],[335,218],[324,222],[311,226],[296,231],[274,235],[252,231],[237,227],[224,223],[211,219],[213,166],[218,160],[228,153],[241,147],[256,144]],dtype=np.float32)
center=(button.max(0)+button.min(0))/2;mm_per_pixel=39/260
button_xy=np.column_stack([(button[:,0]-center[0])*mm_per_pixel,(center[1]-button[:,1])*mm_per_pixel])
area=np.sum(button_xy[:,0]*np.roll(button_xy[:,1],-1)-button_xy[:,1]*np.roll(button_xy[:,0],-1))/2
if area<0:button_xy=button_xy[::-1]
(ROOT/'geometry/full_guitar/tuner-button-outline.json').write_text(json.dumps({'points_mm':button_xy.tolist(),'width_mm':float(np.ptp(button_xy[:,0])),'height_mm':float(np.ptp(button_xy[:,1])),'calibration':'39 mm dimension spans approximately 260 source pixels; manually surveyed outer silhouette excludes dimension line'},indent=2))
