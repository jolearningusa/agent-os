#!/usr/bin/env python3
"""Export locked core wheel requirements or verify downloaded artifacts; no execution."""

import argparse
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def wheel_index(packages, expected):
    result = {}
    for name, version in expected.items():
        matches = [p for p in packages if re.sub(r'[-_.]+', '-', p['name']).lower() == name
                   and p['version'] == version]
        if len(matches) != 1 or matches[0]['source'] != {'registry': 'https://pypi.org/simple'}:
            raise ValueError('unapproved package source')
        wheels = matches[0].get('wheels', [])
        if not wheels:
            raise ValueError('no locked wheels')
        for wheel in wheels:
            url = urlsplit(wheel['url'])
            filename = Path(unquote(url.path)).name
            checksum = wheel['hash'].removeprefix('sha256:')
            if (url.scheme != 'https' or url.hostname != 'files.pythonhosted.org'
                    or not filename.endswith('.whl') or filename in result
                    or not re.fullmatch(r'[0-9a-f]{64}', checksum)):
                raise ValueError('invalid wheel provenance')
            result[filename] = (name, version, checksum)
    return result


def requirements(index):
    grouped = {}
    for name, version, checksum in index.values():
        grouped.setdefault((name, version), set()).add(checksum)
    return '\n'.join(f'{name}=={version} ' + ' '.join(
        f'--hash=sha256:{checksum}' for checksum in sorted(hashes))
        for (name, version), hashes in sorted(grouped.items())) + '\n'


def verify(folder, index, expected):
    selected = {}
    names = set()
    if folder.is_symlink():
        raise ValueError('symlink wheel directory')
    for path in folder.iterdir():
        if path.is_symlink() or not path.is_file() or path.name not in index:
            raise ValueError('unexpected artifact')
        name, version, checksum = index[path.name]
        if name in names or digest(path) != checksum:
            raise ValueError('duplicate or changed artifact')
        names.add(name)
        selected[path.name] = (name, version, checksum)
    if names != set(expected):
        raise ValueError('incomplete artifact set')
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['export', 'verify'])
    parser.add_argument('--source', type=Path, default=ROOT / '.local/harness-lab/probe/source')
    parser.add_argument('--wheel-dir', type=Path)
    parser.add_argument('--requirements', action='store_true')
    args = parser.parse_args(argv)
    if args.mode == 'verify' and args.wheel_dir is None:
        parser.error('verify requires --wheel-dir')
    try:
        lock = json.loads((ROOT / 'harness.lock.json').read_text())
        if digest(args.source / 'uv.lock') != lock['source_files_sha256']['uv.lock']:
            raise ValueError('source lock hash differs')
        expected = json.loads((ROOT / 'configs/probe-runtime-macos-arm64.json').read_text())['packages']
        packages = tomllib.loads((args.source / 'uv.lock').read_text())['package']
        index = wheel_index(packages, expected)
        if args.mode == 'export':
            output = requirements(index)
        else:
            selected = verify(args.wheel_dir, index, expected)
            output = requirements(selected) if args.requirements else json.dumps({
                'result': 'pass', 'packages': len(selected), 'locked_wheel_hashes_verified': True}) + '\n'
    except (OSError, ValueError, KeyError, TypeError):
        print('FAIL: approved wheel artifacts could not be verified', file=sys.stderr)
        return 1
    print(output, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
