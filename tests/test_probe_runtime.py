"""Offline audit regressions: no installation and no Hermes imports."""

import hashlib
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('probe_runtime', ROOT / 'scripts/check_probe_runtime.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ProbeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.expected = {'demo-package': '1.0'}
        self.installed = [('Demo_Package', '1.0')]
        self.locked = [{'name': 'demo-package', 'version': '1.0',
                        'source': {'registry': 'https://pypi.org/simple'}}]

    def test_exact_core_set(self):
        self.assertEqual(checker.audit_packages(self.installed, self.locked, self.expected), [])

    def test_missing_extra_drift_and_duplicate_rejected(self):
        for installed in [[], self.installed + [('extra', '1.0')],
                          [('demo-package', '2.0')], self.installed * 2]:
            with self.subTest(installed=installed):
                self.assertTrue(checker.audit_packages(installed, self.locked, self.expected))

    def test_git_url_and_ambiguous_sources_rejected(self):
        for source in [{'git': 'https://example.invalid/source'},
                       {'url': 'https://example.invalid/wheel'},
                       {'registry': 'https://example.invalid/simple'}]:
            locked = [dict(self.locked[0], source=source)]
            self.assertTrue(checker.audit_packages(self.installed, locked, self.expected))
        self.assertTrue(checker.audit_packages(self.installed, self.locked * 2, self.expected))

    def test_wrong_platform_or_python_rejected(self):
        manifest = {'python': {'version': '3.14.10'},
                    'platform': {'system': 'Darwin', 'machine': 'arm64'}}
        self.assertEqual(checker.audit_runtime(manifest, '3.14.10', 'Darwin', 'arm64'), [])
        for values in [('3.13.0', 'Darwin', 'arm64'), ('3.14.10', 'Linux', 'x86_64')]:
            self.assertTrue(checker.audit_runtime(manifest, *values))

    def test_resolution_log_rejects_unknown_or_empty_package_set(self):
        pairs = checker.read_resolution('Would install 1 package\n + demo-package==1.0\n')
        self.assertEqual(checker.audit_packages(pairs, self.locked, self.expected), [])
        self.assertTrue(checker.audit_packages(checker.read_resolution(''), self.locked, self.expected))
        with self.assertRaises(ValueError):
            checker.read_resolution(' + extra @ https://example.invalid/wheel')

    def test_source_hash_commit_and_dirty_state_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            (source / 'uv.lock').write_bytes(b'locked')
            lock = {'commit': 'fixed', 'source_files_sha256': {
                'uv.lock': hashlib.sha256(b'locked').hexdigest()}}
            for outputs, fails in [(['fixed', 'H uv.lock\0', ''], False), (['other'], True),
                                   (['fixed', 'H uv.lock\0', ' M tracked'], True)]:
                with patch.object(checker.subprocess, 'check_output', side_effect=outputs):
                    self.assertEqual(bool(checker.audit_source(source, lock)), fails)
            (source / 'uv.lock').write_bytes(b'changed')
            self.assertTrue(checker.audit_source(source, lock))

    def test_real_git_rejects_ignored_and_hidden_untracked_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            # No remote, global config, template hooks or user signing setup.
            env = {'PATH': os.environ['PATH'], 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_CONFIG_GLOBAL': os.devnull}

            def git(*args):
                return subprocess.check_output(
                    ['git', '-C', folder, *args], env=env, text=True,
                    stderr=subprocess.DEVNULL, timeout=10).strip()

            git('init', '-q', '--template=')
            (source / '.gitignore').write_text('*.pyc\nignored.py\nhidden/\n')
            (source / 'uv.lock').write_bytes(b'locked')
            (source / 'tracked.py').write_bytes(b'original')
            git('add', '.gitignore', 'uv.lock', 'tracked.py')
            git('-c', 'user.name=Harness Fixture', '-c', 'user.email=fixture@example.invalid',
                '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                'commit', '-qm', 'synthetic fixture')
            git('config', 'status.showUntrackedFiles', 'no')
            lock = {'commit': git('rev-parse', 'HEAD'), 'source_files_sha256': {
                'uv.lock': hashlib.sha256(b'locked').hexdigest()}}
            self.assertEqual(checker.audit_source(source, lock), [])
            for name in ['ignored.pyc', 'ignored.py', 'hidden/extra.pth', 'untracked.py']:
                with self.subTest(name=name):
                    path = source / name
                    path.parent.mkdir(exist_ok=True)
                    path.write_bytes(b'synthetic fixture; never executed')
                    self.assertTrue(checker.audit_source(source, lock))
                    self.assertTrue(path.exists(), 'auditor must not delete files')
                    path.unlink()
                    if path.parent != source:
                        path.parent.rmdir()
                    self.assertEqual(checker.audit_source(source, lock), [])
            for flags in [('--assume-unchanged',), ('--skip-worktree',),
                          ('--assume-unchanged', '--skip-worktree')]:
                with self.subTest(flags=flags):
                    for flag in flags:
                        git('update-index', flag, 'tracked.py')
                    (source / 'tracked.py').write_bytes(b'changed; never executed')
                    self.assertEqual(git('status', '--porcelain'), '')
                    self.assertTrue(checker.audit_source(source, lock))
                    self.assertEqual((source / 'tracked.py').read_bytes(), b'changed; never executed')
                    for flag in ['--no-assume-unchanged', '--no-skip-worktree']:
                        git('update-index', flag, 'tracked.py')
                    (source / 'tracked.py').write_bytes(b'original')
                    self.assertEqual(checker.audit_source(source, lock), [])


if __name__ == '__main__':
    unittest.main()
