"""Render the same full instrument across real wood candidates and finishes."""
import argparse,sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import full_guitar as full
from full_guitar import bpy,ROOT,F,MANIFEST,PRESETS,set_finish,full_signature
full.BODY_MAT=bpy.data.materials['Photo wood / stain / perimeter burst / clearcoat'];full.HEAD_MAT=bpy.data.materials['Matching photographed maple headstock veneer']
p=argparse.ArgumentParser();p.add_argument('--preset',choices=list(PRESETS)+['all'],default=F['default_preset']);p.add_argument('--candidate',action='append');p.add_argument('--all',action='store_true');p.add_argument('--camera',choices=['front','perspective','rear','carve','all'],default='front');p.add_argument('--preview',action='store_true');p.add_argument('--comparison',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
scene=bpy.context.scene
candidates=MANIFEST if args.all else [c for c in MANIFEST if c['source_filename'] in (args.candidate or [F['default_candidate']])]
assert candidates,'No matching candidates'
presets=list(PRESETS) if args.preset=='all' else [args.preset]
views=['front','perspective','rear','carve'] if args.camera=='all' else [args.camera]
cameras={'front':'Full Front','perspective':'Full Perspective','rear':'Full Rear','carve':'Carve Detail'}
sig=full_signature();records=[]
for preset in presets:
 for candidate in candidates:
  set_finish(preset,candidate);full.sync_headstock();assert full_signature()==sig,'Full instrument changed between candidates'
  for view in views:
   scene.camera=bpy.data.objects[cameras[view]]
   if args.preview:resolution=[650,1500] if view in ['front','rear'] else [1000,1200];samples=24
   elif args.comparison:resolution=[800,1800];samples=48
   else:resolution=F['front_resolution'] if view in ['front','rear'] else F['perspective_resolution'];samples=F['samples']
   if view=='carve':resolution=[1600,1600] if not args.preview else [1000,1000]
   scene.render.resolution_x,scene.render.resolution_y=resolution;scene.cycles.samples=samples
   folder=ROOT/'renders/full_guitar'/('previews' if args.preview else 'comparisons' if args.comparison else 'hero')/preset;folder.mkdir(parents=True,exist_ok=True)
   path=folder/f"{candidate['source_filename']}.{view}.png";scene.render.filepath=str(path);start=time.time();bpy.ops.render.render(write_still=True)
   record={'candidate':candidate['source_filename'],'preset':preset,'bookmatch':candidate['status'],'camera':view,'geometry_signature':sig,'resolution':resolution,'samples':samples,'seed':17,'engine':scene.render.engine,'blender_version':bpy.app.version_string,'seconds':round(time.time()-start,2),'texture_placement':full.CFG['placements'].get(candidate['source_filename'],{}),'body_center_mm':F['body_center_thickness_mm'],'nominal_body_rim_mm':F['body_rim_thickness_mm']}
   path.with_suffix('.json').write_text(json.dumps(record,indent=2));records.append(record)
print('FULL GUITAR RENDERS',json.dumps(records))
