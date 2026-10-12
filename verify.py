"""Run public-boundary tests and write executed verification evidence."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rendering',action='store_true',help='Include actual Blender builds/renders; requires Blender')
parser.add_argument('--report',type=Path,default=ROOT/'.work/verification/report.json')
args=parser.parse_args()
suite=unittest.TestSuite([unittest.TestLoader().discover(str(ROOT/'tests'))])
if args.rendering:
    suite.addTests(unittest.TestLoader().discover(str(ROOT/'tests/integration')))
started=time.monotonic()
result=unittest.TextTestRunner(verbosity=2).run(suite)
files=sorted([*list((ROOT/'src').rglob('*.py')),*list((ROOT/'blender/scripts').glob('*.py')),ROOT/'prepare_full_guitar.py'])
code_hash=hashlib.sha256(b''.join(str(p.relative_to(ROOT)).encode()+p.read_bytes() for p in files)).hexdigest()
report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'success':result.wasSuccessful(),'includes_actual_blender_execution':args.rendering,'seconds':round(time.monotonic()-started,3),'pipeline_code_sha256':code_hash,'failed_tests':[test.id() for test,_ in result.failures+result.errors]}
if args.rendering:
    import numpy as np
    from PIL import Image
    model=ROOT/'.work/tests/umbraeternal/blender/full_guitar/validation.json'
    if model.exists():report['model_evidence']=json.loads(model.read_text())
    report['golden_image_metrics']={}
    for name in ['20261009_112804.jpg','20261009_113155.jpg']:
        path=ROOT/'.work/tests/umbraeternal/renders/full_guitar/previews/prs_reference'/f'{name}.carve.png'
        if path.exists():
            actual=np.asarray(Image.open(path).convert('RGB'),dtype=float)
            expected=np.asarray(Image.open(ROOT/'tests/fixtures'/path.name).convert('RGB'),dtype=float)
            error=np.abs(actual-expected)
            report['golden_image_metrics'][name]={'mean_rgb_error':float(error.mean()),'p99_rgb_error':float(np.percentile(error,99))}
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,indent=2))
print('Verification evidence:',args.report)
sys.exit(0 if result.wasSuccessful() else 1)
