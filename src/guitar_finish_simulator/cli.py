"""Command line entry point for specification-driven projects."""
import argparse
from pathlib import Path
from .pipeline import Pipeline

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','build'])
    parser.add_argument('specification',type=Path)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--blender')
    args=parser.parse_args(argv)
    pipeline=Pipeline(args.specification,args.workspace,args.blender)
    getattr(pipeline,args.command)()

if __name__=='__main__':
    main()
