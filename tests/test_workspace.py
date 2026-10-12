import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from guitar_finish_simulator.project import Project

class WorkspaceTests(unittest.TestCase):
    def test_legacy_preprocessing_cli_can_target_another_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Project.load(ROOT / 'projects/umbraeternal/project.json').materialize(directory)
            result = subprocess.run([sys.executable, str(ROOT / 'preprocess.py')], env={**os.environ, 'GFS_PROJECT_ROOT': str(root)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'assets/textures/processed/manifest.json').exists())
