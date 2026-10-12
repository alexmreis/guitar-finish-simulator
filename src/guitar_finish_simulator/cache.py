"""Content-verified artifacts; existence alone is never a cache hit."""
import hashlib
import json
from pathlib import Path

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def reusable(root,stage,key):
    path=root/'.cache'/f'{stage}.json'
    if not path.exists():
        return False
    try:
        record=json.loads(path.read_text())
        return record['key']==key and all((root/name).is_file() and digest(root/name)==sha for name,sha in record['outputs'].items())
    except (ValueError,KeyError,OSError):
        return False

def record(root,stage,key,paths):
    folder=root/'.cache';folder.mkdir(exist_ok=True)
    outputs={str(p.relative_to(root)):digest(p) for p in paths if p.is_file()}
    (folder/f'{stage}.json').write_text(json.dumps({'key':key,'outputs':outputs},indent=2))
