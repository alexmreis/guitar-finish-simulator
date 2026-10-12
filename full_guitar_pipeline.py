"""Rebuild the full specified instrument and reproduce every delivery render."""
import argparse,subprocess,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--blender',default=shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender');args=p.parse_args()
def run(argv):
    print('Running:', ' '.join(map(str,argv)),flush=True);subprocess.run(list(map(str,argv)),cwd=ROOT,check=True)
# Rebuild photo derivatives and the shared shader scene from current source/config.
# This also prevents an older packed image from surviving a crop/figure-map edit.
run([sys.executable,'preprocess.py'])
run([sys.executable,'extract_outline.py'])
run([args.blender,'-b','--python-exit-code','1','--python','blender/scripts/build.py'])
run([sys.executable,'prepare_full_guitar.py'])
run([args.blender,'-b','blender/guitar.blend','--python-exit-code','1','--python','blender/scripts/full_guitar.py'])
run([args.blender,'-b','blender/full_guitar.blend','--python-exit-code','1','--python','blender/scripts/validate_full_guitar.py'])
for preset in ['prs_reference','extreme_black']:
    run([args.blender,'-b','blender/full_guitar.blend','--python-exit-code','1','--python','blender/scripts/render_full_guitar.py','--','--preset',preset,'--camera','all'])
run([args.blender,'-b','blender/full_guitar.blend','--python-exit-code','1','--python','blender/scripts/render_full_guitar.py','--','--preset','all','--all','--comparison'])
run([sys.executable,'full_guitar_comparisons.py'])
