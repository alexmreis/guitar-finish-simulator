"""Physical perimeter fields shared by photograph and CAD outline import."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

def write_perimeter_fields(root, points, cfg):
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
    Image.fromarray(np.uint16(np.clip(dist/local_halfwidth,0,1)*65535)).save(root/'geometry/perimeter-distance.png')
    Image.fromarray(bodymask).save(root/'geometry/uv-layout.png')

def prepare_cad_body(root, points):
    """Derive the same physical texture/perimeter fields from a CAD body contour."""
    from .cad import validate_contour
    from .project import SpecificationError
    validate_contour(points)
    points=np.array(points,dtype=float)
    points[:,1]-=points[:,1].min()
    area=np.sum(points[:,0]*np.roll(points[:,1],-1)-points[:,1]*np.roll(points[:,0],-1))/2
    if area<0:
        points=points[::-1]
    cfg=json.loads((root/'config/project.json').read_text())
    width=float(np.ptp(points[:,0]));height=float(np.ptp(points[:,1]))
    if abs(width-cfg['body_width_mm'])>.1:
        raise SpecificationError(f'CAD width {width:.3f} mm disagrees with specified body width {cfg["body_width_mm"]} mm')
    if np.max(np.abs(points[:,0]))>=cfg['texture_width_mm']/2 or height>=cfg['texture_height_mm']:
        raise SpecificationError('Body does not fit the physical texture domain; enlarge the domain explicitly')
    (root/'geometry/outline.json').write_text(json.dumps({'points_mm':points.tolist(),'width_mm':width,'height_mm':height,'source_kind':'cad'},indent=2))
    svgpoints=' '.join(f'{x:.4f},{-y:.4f}' for x,y in points)
    (root/'geometry/body_outline.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{points[:,0].min()} {-height} {width} {height}"><polygon id="BODY" points="{svgpoints}" fill="none" stroke="black" stroke-width="0.5"/></svg>')
    write_perimeter_fields(root,points,cfg)
    (root/'geometry/outline-validation.json').write_text(json.dumps({'closed':True,'self_intersections':0,'width_mm':width,'height_mm':height,'source_kind':'cad'},indent=2))
