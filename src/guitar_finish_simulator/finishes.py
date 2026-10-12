"""Finish controls have physical/artistic bounds independent of the studio rig."""
import math
import re
from .project import SpecificationError

BOUNDS={
    'coat_weight':(0,1),'coat_roughness':(0,1),'base_roughness':(0,1),
    'specular_ior_level':(0,1),'ior':(1,3),'bump_strength':(0,1),
    'dye_intensity':(0,1),'sandback_strength':(0,1),'warmth':(0,1),
    'figure_contrast':(.01,5),'highlight_brightness':(0,2),'overall_darkness':(0,2),
    'burst_width':(0,1),'edge_opacity':(0,1),'inner_opacity':(0,1),
    'burst_exponent':(.01,5),'transition_position':(.01,2),'edge_hold':(0,1)
}

def validate_finish(preset,controls):
    for key,(lo,hi) in BOUNDS.items():
        value=controls.get(key,.5 if key=='specular_ior_level' else None)
        if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or not lo<=value<=hi:
            raise SpecificationError(f'{preset}.{key} must be between {lo} and {hi}')
    if len(controls.get('palette',[]))!=4:
        raise SpecificationError(f'{preset}.palette needs four colors')
    for value in [*controls['palette'],controls.get('burst_color','')]:
        if not isinstance(value,str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}',value):
            raise SpecificationError(f'{preset} colors must be #RRGGBB')
    if controls['inner_opacity']>controls['edge_opacity']:
        raise SpecificationError('Burst inner opacity cannot exceed edge opacity')
    if controls['edge_hold']>controls['burst_width']*controls['transition_position']:
        raise SpecificationError('Solid edge width cannot exceed the burst transition')
