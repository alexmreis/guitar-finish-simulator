import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from guitar_finish_simulator.pipeline import Pipeline

class CacheTests(unittest.TestCase):
    def test_reuses_verified_model_and_repairs_a_modified_scene(self):
        pipeline=Pipeline(ROOT/'projects/umbraeternal/project.json',ROOT/'.work/tests/cache')
        path=pipeline.build()
        timestamp=path.stat().st_mtime_ns
        pipeline.build()
        self.assertEqual(path.stat().st_mtime_ns,timestamp,'Unchanged model should be reused')
        path.write_bytes(b'corrupted artifact')
        pipeline.build()
        self.assertGreater(path.stat().st_size,1000000)
        self.assertNotEqual(path.stat().st_mtime_ns,timestamp)
