"""Artifact checks use synthetic bytes only; no downloads, imports or installation."""

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('probe_dependencies', ROOT / 'scripts/probe_dependencies.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.expected = {'demo': '1.0'}
        self.name = 'demo-1.0-py3-none-any.whl'
        self.content = b'synthetic artifact; never executed'
        self.checksum = hashlib.sha256(self.content).hexdigest()
        self.package = {'name': 'demo', 'version': '1.0',
                        'source': {'registry': 'https://pypi.org/simple'}, 'wheels': [{
                            'url': 'https://files.pythonhosted.org/' + self.name,
                            'hash': 'sha256:' + self.checksum}]}
        self.index = checker.wheel_index([self.package], self.expected)

    def test_exact_artifact_and_requirements(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / self.name).write_bytes(self.content)
            selected = checker.verify(Path(folder), self.index, self.expected)
            self.assertEqual(checker.requirements(selected),
                             f'demo==1.0 --hash=sha256:{self.checksum}\n')

    def test_missing_changed_extra_directory_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                checker.verify(root, self.index, self.expected)
            wheel = root / self.name
            wheel.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                checker.verify(root, self.index, self.expected)
            wheel.write_bytes(self.content)
            for kind in ['file', 'directory', 'symlink']:
                extra = root / 'extra'
                if kind == 'file':
                    extra.write_bytes(b'extra')
                elif kind == 'directory':
                    extra.mkdir()
                else:
                    extra.symlink_to(wheel)
                with self.assertRaises(ValueError):
                    checker.verify(root, self.index, self.expected)
                extra.rmdir() if extra.is_dir() else extra.unlink()
            wheel.unlink()
            wheel.symlink_to(ROOT / 'harness.lock.json')
            with self.assertRaises(ValueError):
                checker.verify(root, self.index, self.expected)

    def test_duplicate_package_wheels_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            index = dict(self.index)
            other = 'demo-1.0-cp314-none-any.whl'
            index[other] = index[self.name]
            for name in index:
                (root / name).write_bytes(self.content)
            with self.assertRaises(ValueError):
                checker.verify(root, index, self.expected)

    def test_non_registry_ambiguous_or_unapproved_host_rejected(self):
        for source in [{'git': 'https://example.invalid'}, {'registry': 'https://example.invalid'}]:
            with self.assertRaises(ValueError):
                checker.wheel_index([dict(self.package, source=source)], self.expected)
        with self.assertRaises(ValueError):
            checker.wheel_index([self.package, self.package], self.expected)
        for wheels in [[], [{'url': 'https://example.invalid/demo.whl', 'hash': 'sha256:' + self.checksum}],
                       [{'url': 'https://files.pythonhosted.org/demo.whl', 'hash': 'not-sha256'}]]:
            with self.assertRaises(ValueError):
                checker.wheel_index([dict(self.package, wheels=wheels)], self.expected)

    def test_cli_rejects_lock_drift_without_echoing_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'uv.lock').write_text('synthetic-private-sentinel')
            result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/probe_dependencies.py'),
                                     'export', '--source', folder], text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(folder, result.stderr)
            self.assertNotIn('synthetic-private-sentinel', result.stderr)
            self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
