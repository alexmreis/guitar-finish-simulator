"""Execute the public Blender renderer against the saved approved scene."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BLENDER = os.environ.get('BLENDER', shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender')

class RenderCharacterization(unittest.TestCase):
    def test_flame_and_quilt_render_with_approved_geometry_and_appearance(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for name in ['blender/scripts', 'config', 'geometry', 'assets/textures']:
                shutil.copytree(ROOT / name, project / name)
            if (ROOT / 'src').exists():
                shutil.copytree(ROOT / 'src', project / 'src')
            shutil.copy2(ROOT / 'blender/full_guitar.blend', project / 'blender')
            command = [BLENDER, '-b', str(project / 'blender/full_guitar.blend'), '--python-exit-code', '1', '--python', str(ROOT / 'blender/scripts/render_full_guitar.py'), '--', '--preset', 'prs_reference', '--candidate', '20261009_112804.jpg', '--candidate', '20261009_113155.jpg', '--camera', 'carve', '--preview']
            result = subprocess.run(command, capture_output=True, text=True, env={**os.environ, 'GFS_PROJECT_ROOT': str(project)})
            self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
            for candidate in ['20261009_112804.jpg', '20261009_113155.jpg']:
                output = project / 'renders/full_guitar/previews/prs_reference' / f'{candidate}.carve.png'
                baseline = ROOT / 'tests/fixtures' / output.name
                record = json.loads(output.with_suffix('.json').read_text())
                approved = json.loads(baseline.with_suffix('.json').read_text())
                self.assertEqual(record['geometry_signature'], approved['geometry_signature'])
                self.assertEqual(record['engine'], 'CYCLES')
                self.assertEqual(record['samples'], 24)
                actual = np.asarray(Image.open(output).convert('RGB'), dtype=float)
                expected = np.asarray(Image.open(baseline).convert('RGB'), dtype=float)
                self.assertEqual(actual.shape, expected.shape)
                self.assertLess(np.abs(actual - expected).mean(), 0.15, candidate)
                self.assertLess(np.percentile(np.abs(actual - expected), 99), 2, candidate)
