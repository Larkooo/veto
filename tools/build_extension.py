"""Build a reproducible, self-contained unpacked extension and release ZIP."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from build_network import build as build_network

ROOT = Path(__file__).resolve().parents[1]


def main():
    build_network()
    source = ROOT / 'extension'
    manifest = json.loads((source / 'manifest.json').read_text())
    package = json.loads((ROOT / 'package.json').read_text())
    if manifest['version'] != package['version']:
        raise ValueError('Package and extension versions must match')
    if manifest['manifest_version'] != 3:
        raise ValueError('Expected a Manifest V3 extension')
    files = sorted(path for path in source.rglob('*') if path.is_file() and
                   (path.suffix in {'.js', '.css', '.html', '.png'} or path.name in {'manifest.json', 'network-rules.json'}))
    names = {path.relative_to(source).as_posix() for path in files}
    required = [rule['path'] for rule in manifest.get('declarative_net_request', {}).get('rule_resources', [])]
    required += [manifest['background']['service_worker'], manifest['action']['default_popup']]
    for content_script in manifest['content_scripts']:
        required.extend(content_script.get('js', []))
        required.extend(content_script.get('css', []))
    for name in required:
        if name not in names:
            raise ValueError(f'Missing runtime resource: {name}')
    artifact = json.loads((source / 'model.json').read_text())
    embedded = (source / 'model.js').read_text().removeprefix('globalThis.WebGuardModel = ').strip().removesuffix(';')
    if json.loads(embedded) != artifact:
        raise ValueError('Embedded model differs from the training artifact')
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    archive = dist / f"{package['name']}-{manifest['version']}.zip"
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            entry = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            bundle.writestr(entry, path.read_bytes())
        license_entry = zipfile.ZipInfo('LICENSE', date_time=(2020, 1, 1, 0, 0, 0))
        license_entry.compress_type = zipfile.ZIP_DEFLATED
        license_entry.external_attr = 0o100644 << 16
        bundle.writestr(license_entry, (ROOT / 'LICENSE').read_bytes())
    unpacked = dist / package['name']
    if unpacked.exists():
        shutil.rmtree(unpacked)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        bundle.extractall(unpacked)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (dist / 'SHA256SUMS').write_text(f'{digest}  {archive.name}\n')
    print(json.dumps({'archive': str(archive), 'unpacked': str(unpacked), 'bytes': archive.stat().st_size,
                      'sha256': digest, 'runtime_files': len(files), 'model_version': artifact['version']}, indent=2))


if __name__ == '__main__':
    main()
