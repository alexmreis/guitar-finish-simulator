"""Command line entry point for specification-driven projects."""
import argparse
import json
from .project import SpecificationError
from pathlib import Path
from .pipeline import Pipeline

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','prepare','build','render','serve','batch'])
    parser.add_argument('specification',type=Path)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--blender')
    parser.add_argument('--preset')
    parser.add_argument('--candidate',action='append',default=[])
    parser.add_argument('--view',choices=['front','perspective','rear','carve','all'],default='front')
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-hero',action='store_true',help='Batch comparisons and enlarged PRS renders without the default instrument views')
    args=parser.parse_args(argv)
    try:
        pipeline=Pipeline(args.specification,args.workspace,args.blender)
        if args.command=='validate':
            print(json.dumps(pipeline.project.validate_inputs(),indent=2))
        elif args.command=='serve':
            from .app import make_server
            server=make_server(args.specification,args.workspace,args.port,args.blender)
            print(f'Calibration workbench: http://127.0.0.1:{server.server_port}',flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        elif args.command=='batch':
            print(json.dumps(pipeline.batch(hero_views=not args.no_hero),indent=2))
        elif args.command=='render':
            pipeline.render(args.preset,args.candidate,args.view,args.preview)
        else:
            getattr(pipeline,args.command)()
    except (SpecificationError,FileNotFoundError,RuntimeError,ValueError) as error:
        parser.exit(2,str(error)+'\n')

if __name__=='__main__':
    main()
