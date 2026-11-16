#!/usr/bin/env python3
"""Read-only L02a audit; run with the isolated Hermes venv's Python -I."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def audit_packages(installed, locked, expected):
    """Reject drift, duplicate distributions and non-registry lock sources."""
    pairs = [(normalize(name), version) for name, version in installed]
    if len(dict(pairs)) != len(pairs) or dict(pairs) != expected:
        return ['installed package set differs from approved core set']
    for name, version in expected.items():
        matches = [p for p in locked
                   if normalize(p['name']) == name and p['version'] == version]
        if len(matches) != 1 or matches[0]['source'] != {'registry': 'https://pypi.org/simple'}:
            return ['core lock source is ambiguous or not the approved registry']
    return []


def audit_runtime(manifest, version, system, machine):
    if (manifest['python']['version'], manifest['platform']) != (
            version, {'system': system, 'machine': machine}):
        return ['Python version or platform differs from approved runtime']
    return []


def read_resolution(text):
    pairs = []
    for line in text.splitlines():
        if line.lstrip().startswith('+'):
            match = re.fullmatch(r'\s*\+ ([a-z0-9-]+)==([^\s]+)', line)
            if not match:
                raise ValueError('unsupported resolution entry')
            pairs.append(match.groups())
    return pairs


def audit_source(source, lock):
    for name, expected in lock['source_files_sha256'].items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            return ['source file hash differs from harness lock']
    def git(*args):
        return subprocess.check_output(
            ['git', '-c', 'core.fsmonitor=false', '-C', str(source), *args],
            text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
    if git('rev-parse', 'HEAD') != lock['commit'] or git('status', '--porcelain'):
        return ['source commit differs or source worktree is dirty']
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/harness-lab/probe/source')
    parser.add_argument('--resolution-log', type=Path,
                        help='audit an empty-environment uv dry-run before installation')
    args = parser.parse_args(argv)
    try:
        manifest = json.loads((ROOT / 'configs/probe-runtime-macos-arm64.json').read_text())
        lock = json.loads((ROOT / 'harness.lock.json').read_text())
        errors = audit_source(args.source, lock)
        packages = tomllib.loads((args.source / 'uv.lock').read_text())['package']
        if args.resolution_log:
            installed = read_resolution(args.resolution_log.read_text())
        else:
            errors += audit_runtime(manifest, platform.python_version(), platform.system(), platform.machine())
            installed = [(d.metadata['Name'], d.version) for d in importlib.metadata.distributions()]
        errors += audit_packages(installed, packages, manifest['packages'])
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('FAIL: runtime audit input or source state could not be verified', file=sys.stderr)
        return 1
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(json.dumps({
        'result': 'pass', 'expected_python': manifest['python']['version'],
        'mode': 'resolution' if args.resolution_log else 'installed-runtime',
        'target_platform': manifest['platform'], 'packages': len(installed),
        'source_commit': lock['commit'], 'verified_source_hashes': len(lock['source_files_sha256']),
        'registry_only': True, 'source_clean': True,
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
