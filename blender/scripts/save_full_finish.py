"""Save a configured body/headstock finish without rebuilding the instrument."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import full_guitar as full
from full_guitar import bpy,ROOT,F,MANIFEST,PRESETS,set_finish,full_signature
p=argparse.ArgumentParser();p.add_argument('--preset',choices=list(PRESETS),default=F['default_preset']);p.add_argument('--candidate',default=F['default_candidate']);args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
full.BODY_MAT=bpy.data.materials['Photo wood / stain / perimeter burst / clearcoat'];full.HEAD_MAT=bpy.data.materials['Matching photographed maple headstock veneer']
before=full_signature();set_finish(args.preset,next(c for c in MANIFEST if c['source_filename']==args.candidate));full.sync_headstock();assert full_signature()==before
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/full_guitar.blend'));print('Saved full instrument finish:',args.preset,args.candidate)
