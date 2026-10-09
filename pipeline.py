"""Reproduce every asset and render, stopping on any failed stage."""
import argparse, subprocess, sys, shutil, json, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(); p.add_argument('--blender',default=shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'); args=p.parse_args()
# Bootstrap missing copies from the supplied root assets without overwriting edits.
for directory in ['assets/originals','assets/references','geometry','renders/comparisons','blender']:
    (ROOT/directory).mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(ROOT/'drafttops.zip') as archive:
    for name in json.loads((ROOT/'config/candidates.json').read_text()):
        target=ROOT/'assets/originals'/name
        if not target.exists(): target.write_bytes(archive.read(name))
    reference=ROOT/'assets/references/Umbraeternal.JPG'
    if not reference.exists():
        source=ROOT/'Umbraeternal.JPG'
        reference.write_bytes(source.read_bytes() if source.exists() else archive.read('Umbraeternal.JPG'))
prs=ROOT/'assets/references/prs.png'
if not prs.exists(): shutil.copyfile(ROOT/'prs.png',prs)
def run(argv):
    print('Running:', ' '.join(map(str,argv)),flush=True)
    subprocess.run(list(map(str,argv)),cwd=ROOT,check=True)
run([sys.executable,'preprocess.py'])
run([sys.executable,'extract_outline.py'])
run([args.blender,'-b','--python-exit-code','1','--python','blender/scripts/build.py'])
run([args.blender,'-b','blender/guitar.blend','--python-exit-code','1','--python','blender/scripts/render.py','--','--preset','all','--all','--diagnostics'])
run([args.blender,'-b','blender/guitar.blend','--python-exit-code','1','--python','blender/scripts/validate.py'])
run([sys.executable,'comparisons.py'])
