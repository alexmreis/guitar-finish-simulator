"""Strict 2D contour import. Unsupported CAD entities fail instead of disappearing."""
from pathlib import Path
import math
import re
import xml.etree.ElementTree as ET
from .project import SpecificationError

def read_outline(path, *, layer='BODY', units='mm', origin_mm=(0, 0)):
    path = Path(path)
    if units not in {'mm','cm','m','in'}:
        raise SpecificationError('CAD units must be mm, cm, m, or in')
    if path.suffix.lower() == '.svg':
        document = ET.parse(path).getroot()
        if any('transform' in e.attrib for e in document.iter()):
            raise SpecificationError('Flatten SVG transforms before exporting')
        selected = [e for e in document.iter() if e.attrib.get('id') == layer]
        if not selected:
            selected = [e for e in document.iter() if e.tag.endswith('}polygon') or e.tag == 'polygon']
        if len(selected) != 1 or not selected[0].tag.endswith('polygon'):
            raise SpecificationError('SVG needs one polygon with the selected id; flatten paths before export')
        values = [float(v) for v in re.split(r'[\s,]+', selected[0].attrib['points'].strip())]
        scale = {'mm':1, 'cm':10, 'm':1000, 'in':25.4}[units]
        points = [(values[i]*scale-origin_mm[0], -values[i+1]*scale-origin_mm[1]) for i in range(0,len(values),2)]
        validate_contour(points)
        return points
    if path.suffix.lower() != '.dxf':
        raise SpecificationError('Supported CAD exports are DXF LWPOLYLINE and SVG polygon')
    lines = path.read_text().splitlines()
    pairs = [(int(lines[i].strip()), lines[i+1].strip()) for i in range(0, len(lines), 2)]
    entities = []
    current = []
    for code, value in pairs:
        if code == 0:
            if current:
                entities.append(current)
            current = [(code, value)]
        else:
            current.append((code, value))
    if current:
        entities.append(current)
    selected = [e for e in entities if (8, layer) in e]
    if len(selected) != 1 or selected[0][0] != (0, 'LWPOLYLINE'):
        raise SpecificationError(f'{path.name}: layer {layer} must contain one closed LWPOLYLINE')
    entity = selected[0]
    if not int(dict(entity).get(70, 0)) & 1:
        raise SpecificationError('CAD contour must be closed')
    if any(code == 42 and float(value) != 0 for code,value in entity):
        raise SpecificationError('Tessellate curved DXF bulges to a polyline before export')
    points = []
    for code, value in entity:
        if code == 10:
            points.append([float(value), None])
        elif code == 20:
            points[-1][1] = float(value)
    scale = {'mm': 1, 'cm': 10, 'm': 1000, 'in': 25.4}[units]
    points = [(x * scale-origin_mm[0], y * scale-origin_mm[1]) for x,y in points]
    validate_contour(points)
    return points


def validate_contour(points):
    """Reject degeneracy, crossings and non-adjacent touching edges in mm."""
    if len(points) < 3 or not all(math.isfinite(v) for p in points for v in p):
        raise SpecificationError('Contour needs at least three finite vertices')
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on_segment(a, b, p):
        return abs(cross(a,b,p)) < 1e-9 and min(a[0],b[0])-1e-9 <= p[0] <= max(a[0],b[0])+1e-9 and min(a[1],b[1])-1e-9 <= p[1] <= max(a[1],b[1])+1e-9
    edges = list(zip(points, points[1:]+points[:1]))
    for i,(a,b) in enumerate(edges):
        if math.dist(a,b) < 1e-8:
            raise SpecificationError('Contour contains a zero-length edge')
        for j in range(i+2,len(edges)):
            if i == 0 and j == len(edges)-1:
                continue
            c,d=edges[j]
            crossing=cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0
            touching=any([on_segment(a,b,c),on_segment(a,b,d),on_segment(c,d,a),on_segment(c,d,b)])
            if crossing or touching:
                raise SpecificationError('Contour has a self-intersection')
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in edges)/2
    if abs(area)<1e-6:
        raise SpecificationError('Contour has zero area')
