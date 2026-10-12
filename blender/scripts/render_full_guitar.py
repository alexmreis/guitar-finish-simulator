"""Compatibility entry point for full-instrument rendering."""
import sys
from pathlib import Path
SCRIPT=Path(__file__).resolve()
sys.path.insert(0,str(SCRIPT.parent))
sys.path.insert(0,str(SCRIPT.parents[2]/'src'))
import full_guitar
from guitar_finish_simulator.rendering import render_instrument
render_instrument(full_guitar)
