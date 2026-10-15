"""Tie installer version and payload to the same completed application build."""
import hashlib
import json
from pathlib import Path
from app_version import VERSION

REQUIRED = ('客行录.exe', '_internal/certifi/cacert.pem',
            '_internal/base_library.zip', '_internal/python314.dll',
            '_internal/assets/notebook_reader.html',
            '_internal/flet_desktop/app/flet/flet.exe',
            '_internal/flet_desktop/app/flet/flutter_windows.dll',
            '_internal/flet_desktop/app/flet/data/app.so',
            '_internal/flet_desktop/app/flet/data/icudtl.dat')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_manifest(folder):
    folder=Path(folder)
    hashes={name:digest(folder/name) for name in REQUIRED}
    (folder/'build-manifest.json').write_text(json.dumps(
        {'version':VERSION, 'sha256':hashes}, ensure_ascii=False, indent=2),encoding='utf-8')


def verify_manifest(folder, installer_version):
    folder=Path(folder)
    manifest=json.loads((folder/'build-manifest.json').read_text(encoding='utf-8'))
    if manifest['version'] != VERSION or installer_version != VERSION:
        raise ValueError('安装器和程序版本不一致，请重新构建')
    for name in REQUIRED:
        if digest(folder/name) != manifest['sha256'].get(name):
            raise ValueError(f'安装组件与构建记录不一致：{name}')
