"""Compatibility CLI for deterministic wood preparation."""
import argparse
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from guitar_finish_simulator.wood import prepare_wood

def main():
    root = Path(os.environ.get('GFS_PROJECT_ROOT', ROOT)).resolve()
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=root / 'assets/originals')
    args = parser.parse_args()
    prepare_wood(root, args.input)

if __name__ == '__main__':
    main()
