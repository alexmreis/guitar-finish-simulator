"""Millimeter anchors for the current six-string HSH hardware family."""
DEFAULTS={
    'neck_pickup_y_mm':75,'bridge_pickup_y_mm':-25,'single_pickup_y_mm':26,
    'volume_mm':[76,-73],'tone_mm':[109,-127],'selector_mm':[107,-31]
}

def layout(instrument):
    return {**DEFAULTS,**instrument.get('hardware_layout',{})}
