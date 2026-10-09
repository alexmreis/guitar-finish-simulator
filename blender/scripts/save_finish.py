"""Apply a configured finish to the existing scene without rebuilding geometry."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scene import *
p=argparse.ArgumentParser();p.add_argument('--preset',choices=list(PRESETS),default='prs_reference');p.add_argument('--candidate',default='20261009_113100.jpg')
args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
candidate=next(c for c in MANIFEST if c['source_filename']==args.candidate)
before=signature();set_finish(args.preset,candidate)
assert signature()==before,'Scene invariants changed while applying finish'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/guitar.blend'))
print('SAVED FINISH',args.preset,args.candidate,'with invariant signature',before)
