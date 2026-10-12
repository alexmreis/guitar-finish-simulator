"""Versioned project inputs; relative paths resolve beside the specification."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil

class SpecificationError(ValueError):
    """An input cannot be used without an explicit correction."""

@dataclass(frozen=True)
class Project:
    path: Path
    data: dict
    configs: dict
    candidates: dict

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        data = json.loads(path.read_text())
        if data.get('version') != 1:
            raise SpecificationError('project.version must be 1')
        def read(value):
            return value if isinstance(value, dict) else json.loads((path.parent / value).read_text())
        configs = {key: read(data['config'][key]) for key in ['surface', 'instrument', 'finishes']}
        instrument = configs['instrument']
        if not 0 < instrument['body_rim_thickness_mm'] <= instrument['body_center_thickness_mm']:
            raise SpecificationError('body rim thickness must be positive and no greater than center thickness')
        candidates = read(data['inputs']['candidates'])
        return cls(path, data, configs, candidates)

    def resolve(self, value):
        return (self.path.parent / value).resolve()

    def materialize(self, destination):
        """Copy declared inputs; never mutate originals or reuse another project's files."""
        root = Path(destination).resolve()
        for name in ['config','assets/originals','assets/references','assets/textures/processed',
                     'geometry/full_guitar','blender/full_guitar','renders/comparisons']:
            (root / name).mkdir(parents=True, exist_ok=True)
        files = {}
        for name in self.candidates:
            source = self.resolve(self.data['inputs']['photos']) / name
            target = root / 'assets/originals' / name
            shutil.copy2(source, target)
            files[str(target.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
        for key, filename in [('design_reference','Umbraeternal.JPG'), ('finish_reference','prs.png')]:
            source = self.resolve(self.data['inputs'][key])
            target = root / 'assets/references' / filename
            shutil.copy2(source, target)
            files[str(target.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
        for key, filename in [('surface','project.json'),('instrument','full_guitar.json'),('finishes','finishes.json')]:
            (root / 'config' / filename).write_text(json.dumps(self.configs[key], indent=2))
        (root / 'config/candidates.json').write_text(json.dumps(self.candidates, indent=2))
        lock = {'version': 1, 'name': self.data['name'], 'specification': self.data,
                'configs': self.configs, 'candidates': self.candidates, 'sources': files}
        (root / 'project.lock.json').write_text(json.dumps(lock, indent=2))
        return root
