"""Build the self-contained portable model package for Hugging Face."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    target = ROOT / 'dist' / 'huggingface'
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in ['core.js', 'model.js', 'model.json', 'types.d.ts']:
        shutil.copyfile(ROOT / 'extension' / name, target / name)
    for name in ['veto.mjs', 'veto.d.mts', 'example.mjs', 'README.md']:
        shutil.copyfile(ROOT / 'model' / name, target / name)
    shutil.copyfile(ROOT / 'LICENSE', target / 'LICENSE')
    artifact = json.loads((target / 'model.json').read_text())
    embedded = (target / 'model.js').read_text().removeprefix('globalThis.WebGuardModel = ').strip().removesuffix(';')
    if json.loads(embedded) != artifact:
        raise ValueError('Model artifacts differ')
    package = {'name': '@veto/local-model', 'version': artifact['version'], 'type': 'module', 'license': 'MIT',
               'exports': {'.': {'types': './veto.d.mts', 'import': './veto.mjs'}}}
    (target / 'package.json').write_text(json.dumps(package, indent=2) + '\n')
    (target / 'SHA256SUMS').write_text(''.join(
        f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n'
        for path in sorted(target.iterdir()) if path.is_file()))
    return target


if __name__ == '__main__':
    print(build())
