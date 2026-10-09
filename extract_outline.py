"""Extract front-body perimeter with explicitly editable neck/hardware exclusions."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.interpolate import splprep, splev
ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/'config/project.json').read_text())
im=np.array(Image.open(ROOT/'assets/references/Umbraeternal.JPG').convert('RGB').resize(tuple(cfg['outline_reference_size'])))
mask=np.uint8(np.min(im,axis=2)<190)*255
x0,y0,x1,y1=cfg['outline_roi']; region=np.zeros_like(mask); region[y0:y1,x0:x1]=255; mask &= region
x0,y0,x1,y1=cfg['neck_exclusion']; mask[y0:y1,x0:x1]=0
# Strap pins are hardware rather than body wood.
mask[880:904,135:172]=0; mask[1746:,:]=0
contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
contour=max(contours,key=cv2.contourArea).reshape(-1,2)
# Uniform sampling before periodic smoothing prevents pixel staircase weighting.
delta=np.linalg.norm(np.diff(np.vstack([contour,contour[0]]),axis=0),axis=1)
arc=np.r_[0,np.cumsum(delta)]; target=np.linspace(0,arc[-1],700,endpoint=False)
closed=np.vstack([contour,contour[0]])
xy=np.column_stack([np.interp(target,arc,closed[:,j]) for j in [0,1]])
tck,_=splprep(xy.T,s=cfg['spline_smoothing'],per=True)
outline=np.array(splev(np.linspace(0,1,cfg['outline_samples'],endpoint=False),tck)).T
# Set centerline from the fretboard center, not the asymmetric body's bounding box.
center_x=338.0; bottom=outline[:,1].max(); scale=cfg['body_width_mm']/np.ptp(outline[:,0])
points=np.column_stack([(outline[:,0]-center_x)*scale,(bottom-outline[:,1])*scale])
area=np.sum(points[:,0]*np.roll(points[:,1],-1)-points[:,1]*np.roll(points[:,0],-1))/2
if area<0: points=points[::-1]; outline=outline[::-1]

def intersects(a,b,c,d):
    def cross(u,v,w):
        a=v-u; b=w-u
        return a[0]*b[1]-a[1]*b[0]
    return cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0
n=len(points)
for i in range(n):
    for j in range(i+2,n):
        if (j+1)%n==i: continue
        assert not intersects(points[i],points[(i+1)%n],points[j],points[(j+1)%n]),'Self-intersection'
(ROOT/'geometry/outline.json').write_text(json.dumps({'points_mm':points.tolist(),'centerline_source_x':center_x,'mm_per_reference_pixel':scale,'width_mm':cfg['body_width_mm'],'height_mm':float(np.ptp(points[:,1])),'reference_points':outline.tolist()},indent=2))
svgpoints=' '.join(f'{x:.4f},{-y:.4f}' for x,y in points)
(ROOT/'geometry/body_outline.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{points[:,0].min()} {-points[:,1].max()} {np.ptp(points[:,0])} {np.ptp(points[:,1])}"><polygon points="{svgpoints}" fill="none" stroke="black" stroke-width="0.5"/></svg>')
lines=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES','0','LWPOLYLINE','100','AcDbEntity','8','BODY','100','AcDbPolyline','90',str(n),'70','1']
for x,y in points: lines+=['10',str(x),'20',str(y)]
lines+=['0','ENDSEC','0','EOF']; (ROOT/'geometry/body_outline.dxf').write_text('\n'.join(lines)+'\n')
overlay=im.copy(); cv2.polylines(overlay,[contour.astype(np.int32)],True,(255,100,20),2); cv2.polylines(overlay,[outline.astype(np.int32)],True,(20,230,70),2)
cv2.line(overlay,(338,885),(338,1750),(80,150,255),1)
Image.fromarray(overlay).save(ROOT/'geometry/silhouette-overlay.png')
Image.fromarray(overlay[875:1760,10:670]).save(ROOT/'geometry/spline-comparison.png')
# Distance to nearest actual outline edge, including concave cutaways. Unit: 160mm.
size=1024; tw=cfg['texture_width_mm']; th=cfg['texture_height_mm']; cy=np.ptp(points[:,1])/2
uv=np.column_stack([points[:,0]/tw+.5,(points[:,1]-cy)/th+.5])
bodymask=np.zeros((size,size),np.uint8); pix=np.column_stack([uv[:,0]*(size-1),(1-uv[:,1])*(size-1)])
cv2.fillPoly(bodymask,[np.int32(pix)],255)
# Exact Euclidean distances using physically isotropic pixels in an intermediate grid.
from scipy.ndimage import distance_transform_edt
dist=distance_transform_edt(bodymask>0,sampling=(th/(size-1),tw/(size-1)))
local_halfwidth=np.full_like(dist,cfg['minimum_burst_halfwidth_mm'])
for row in range(size):
    occupied=np.flatnonzero(bodymask[row]>0)
    if len(occupied):
        # Separate disjoint horn spans so cutaway gaps are not counted as wood.
        splits=np.split(occupied,np.flatnonzero(np.diff(occupied)>1)+1)
        for span in splits:
            local_halfwidth[row,span]=max(cfg['minimum_burst_halfwidth_mm'],len(span)*tw/(size-1)/2)
Image.fromarray(np.uint16(np.clip(dist/local_halfwidth,0,1)*65535)).save(ROOT/'geometry/perimeter-distance.png')
Image.fromarray(bodymask).save(ROOT/'geometry/uv-layout.png')
(ROOT/'geometry/outline-validation.json').write_text(json.dumps({'closed':True,'self_intersections':0,'samples':n,'width_mm':float(np.ptp(points[:,0])),'height_mm':float(np.ptp(points[:,1])),'neck_interface':'manual neck exclusion, unseen interface provisional','strap_buttons_excluded':True},indent=2))
print('Validated outline',n,'points;',np.ptp(points[:,1]),'mm tall')
