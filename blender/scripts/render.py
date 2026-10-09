import argparse, sys, json, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scene import *
p=argparse.ArgumentParser(); p.add_argument('--preset',choices=list(PRESETS)+['all'],default='all'); p.add_argument('--all',action='store_true'); p.add_argument('--candidate',action='append'); p.add_argument('--resolution',type=int); p.add_argument('--camera',choices=['Front','Perspective','Detail'],default='Front'); p.add_argument('--diagnostics',action='store_true'); p.add_argument('--output-dir',type=Path)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
scene=bpy.context.scene; scene.camera=bpy.data.objects[args.camera]
candidates=[c for c in MANIFEST if not args.candidate or c['source_filename'] in args.candidate]
if args.candidate: assert len(candidates)==len(set(args.candidate)),'Unknown candidate filename'
presets=list(PRESETS) if args.preset=='all' else [args.preset]
records=[]; invariant=signature()
for preset in presets:
    for candidate in candidates:
        set_finish(preset,candidate)
        assert signature()==invariant,'Comparison scene changed'
        resolution=args.resolution or (CFG['enlarged_resolution'] if preset=='prs_reference' else CFG['comparison_resolution'])
        scene.render.resolution_x=scene.render.resolution_y=resolution
        out=(args.output_dir if args.output_dir else ROOT/'renders')/preset; out.mkdir(parents=True,exist_ok=True)
        suffix='' if args.camera=='Front' else '.'+args.camera.lower()
        scene.render.filepath=str(out/f"{candidate['source_filename']}{suffix}.png")
        start=time.time(); bpy.ops.render.render(write_still=True)
        record={'candidate':candidate['source_filename'],'preset':preset,'bookmatch':candidate['status'],'signature':invariant,'resolution':[resolution,resolution],'camera':args.camera,'seconds':round(time.time()-start,2),'blender_version':bpy.app.version_string,'engine':scene.render.engine,'samples':scene.cycles.samples,'seed':scene.cycles.seed,'texture_placement':CFG['placements'].get(candidate['source_filename'],{})}
        records.append(record); (out/f"{candidate['source_filename']}{suffix}.render.json").write_text(json.dumps(record,indent=2))
if args.diagnostics:
    set_finish('natural',MANIFEST[0])
    for camera in ['Front','Perspective','Detail']:
        scene.camera=bpy.data.objects[camera]; scene.render.resolution_x=scene.render.resolution_y=800
        scene.render.filepath=str(ROOT/'geometry'/f'model-{camera.lower()}.png'); bpy.ops.render.render(write_still=True)
print('RENDER RECORDS',json.dumps(records))
