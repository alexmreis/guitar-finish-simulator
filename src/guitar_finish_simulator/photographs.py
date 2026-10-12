"""Decode source photographs in an explicit, reproducible coordinate system."""
from PIL import Image,ImageOps

def open_photograph(source,spec):
    with Image.open(source) as image:
        if spec.get('exif_orientation_applied'):
            image=ImageOps.exif_transpose(image)
        return image.convert('RGB')
