"""Blender rendering adapter for a fixed instrument and real photograph candidates."""
import argparse
import sys
import json
import time
import hashlib

def render_instrument(full,argv=None):
    bpy,ROOT,F,MANIFEST,PRESETS=full.bpy,full.ROOT,full.F,full.MANIFEST,full.PRESETS
    set_finish,full_signature=full.set_finish,full.full_signature
    full.BODY_MAT=bpy.data.materials['Photo wood / stain / perimeter burst / clearcoat'];full.HEAD_MAT=bpy.data.materials['Matching photographed maple headstock veneer']
    p=argparse.ArgumentParser();p.add_argument('--preset',choices=list(PRESETS)+['all'],default=F['default_preset']);p.add_argument('--candidate',action='append');p.add_argument('--all',action='store_true');p.add_argument('--camera',choices=['front','perspective','rear','carve','all'],default='front');p.add_argument('--preview',action='store_true');p.add_argument('--comparison',action='store_true');p.add_argument('--save-scene',action='store_true');args=p.parse_args(argv if argv is not None else (sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
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
       resolution,samples=render_profile(F,view,'preview' if args.preview else 'comparison' if args.comparison else 'hero')
       scene.render.resolution_x,scene.render.resolution_y=resolution;scene.cycles.samples=samples
       folder=ROOT/'renders/full_guitar'/('previews' if args.preview else 'comparisons' if args.comparison else 'hero')/preset;folder.mkdir(parents=True,exist_ok=True)
       path=folder/f"{candidate['source_filename']}.{view}.png";scene.render.filepath=str(path);start=time.time();bpy.ops.render.render(write_still=True)
       record={'candidate':candidate['source_filename'],'preset':preset,'bookmatch':candidate['status'],'camera':view,'geometry_signature':sig,'resolution':resolution,'samples':samples,'seed':17,'engine':scene.render.engine,'blender_version':bpy.app.version_string,'seconds':round(time.time()-start,2),'texture_placement':full.CFG['placements'].get(candidate['source_filename'],{}),'body_center_mm':F['body_center_thickness_mm'],'nominal_body_rim_mm':F['body_rim_thickness_mm']}
       record.update(finish_controls=PRESETS[preset],source_sha256=candidate['sha256'],texture_sha256=hashlib.sha256((ROOT/'assets/textures/bookmatched'/f"{candidate['source_filename']}.png").read_bytes()).hexdigest())
       path.with_suffix('.json').write_text(json.dumps(record,indent=2));records.append(record)
    if args.save_scene:
        before=full_signature()
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/last_render.blend'))
        assert full_signature()==before,'Saving the render changed the comparison scene'
    print('FULL GUITAR RENDERS',json.dumps(records))
    return records


def render_profile(settings,view,mode):
    """Resolution/sample profiles are shared by all candidates in a comparison."""
    from .project import SpecificationError
    front=view in ['front','rear']
    if mode=='preview':
        name='preview_carve_resolution' if view=='carve' else 'preview_front_resolution' if front else 'preview_perspective_resolution'
        fallback=[1000,1000] if view=='carve' else [650,1500] if front else [1000,1200]
        resolution=settings.get(name,fallback);samples=settings.get('preview_samples',24)
    elif mode=='comparison':
        resolution=settings.get('comparison_front_resolution',[800,1800]);samples=settings.get('comparison_samples',48)
    else:
        resolution=settings.get('carve_resolution',[1600,1600]) if view=='carve' else settings['front_resolution'] if front else settings['perspective_resolution']
        samples=settings['samples']
    if len(resolution)!=2 or any(not isinstance(v,int) or isinstance(v,bool) or v<32 for v in resolution):
        raise SpecificationError('Render resolution must contain two integers of at least 32 pixels')
    if not isinstance(samples,int) or isinstance(samples,bool) or samples<1:
        raise SpecificationError('Render samples must be a positive integer')
    return resolution,samples
