"""Public CLI characterization of the approved photograph preparation outputs."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class WoodCharacterization(unittest.TestCase):
    def test_supplied_photographs_reproduce_approved_textures_and_provenance(self):
        expected = json.loads((ROOT / 'tests/fixtures/artifact-hashes.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            shutil.copy2(ROOT / 'preprocess.py', project)
            shutil.copytree(ROOT / 'src', project / 'src')
            shutil.copytree(ROOT / 'config', project / 'config')
            shutil.copytree(ROOT / 'assets/originals', project / 'assets/originals')
            (project / 'renders/comparisons').mkdir(parents=True)
            subprocess.run([sys.executable, str(project / 'preprocess.py')], check=True, capture_output=True)
            for name, digest in expected.items():
                if name.startswith('assets/textures/') and not name.endswith('validation.json'):
                    with self.subTest(artifact=name):
                        self.assertEqual(hashlib.sha256((project / name).read_bytes()).hexdigest(), digest)

class OutlineCharacterization(unittest.TestCase):
    def test_legacy_outline_cli_preserves_outline_and_distance_field(self):
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory)
            shutil.copy2(ROOT/'extract_outline.py',project)
            shutil.copytree(ROOT/'src',project/'src')
            shutil.copytree(ROOT/'config',project/'config')
            shutil.copytree(ROOT/'assets/references',project/'assets/references')
            (project/'geometry').mkdir()
            subprocess.run([sys.executable,str(project/'extract_outline.py')],check=True,capture_output=True)
            for name in ['outline.json','perimeter-distance.png','body_outline.dxf']:
                self.assertEqual((project/'geometry'/name).read_bytes(),(ROOT/'geometry'/name).read_bytes(),name)
