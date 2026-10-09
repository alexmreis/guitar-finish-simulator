"""Regression signal for the straight waist crease under a uniform finish."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
path=Path(sys.argv[1])
im=np.array(Image.open(path))[:,:,:3].mean(2)
profile=im[405:413,240:315].mean(1)
jump=float(np.abs(np.diff(profile)).max())
print(f'Waist horizontal brightness jump: {jump:.3f}; limit 1.3')
assert jump<1.3,'Artificial straight shading crease remains'
