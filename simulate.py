"""Run the simulator directly from a checkout."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from guitar_finish_simulator.cli import main
if __name__=='__main__':
    main()
