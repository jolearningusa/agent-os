"""L00 regression fixtures for configuration and source-lock validation."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_harness_config.py'
spec = importlib.util.spec_from_file_location('check_harness_config', SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ConfigContractTests(unittest.TestCase):
    def setUp(self):
        self.config = checker.read_json(ROOT / 'configs/local-hermes.json')
        self.lock = checker.read_json(ROOT / 'harness.lock.json')

    def run_cli(self, text, lock=None):
        with tempfile.TemporaryDirectory() as folder:
            config_path = Path(folder) / 'config.json'
            config_path.write_text(text)
            command = [sys.executable, str(SCRIPT), str(config_path)]
            if lock is not None:
                lock_path = Path(folder) / 'harness.lock.json'
                lock_path.write_text(json.dumps(lock))
                command += ['--lock', str(lock_path)]
            return subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=15)

    def test_valid_presets_without_network(self):
        ollama = copy.deepcopy(self.config)
        ollama['inference'].update(mode='ollama', port=11434, model=self.lock['model']['name'])
        captured = copy.deepcopy(self.config)
        captured['privacy']['capture_body'] = True
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            for config in [self.config, ollama, captured]:
                with self.subTest(mode=config['inference']['mode']):
                    self.assertEqual(checker.validate(config, self.lock), [])
        result = self.run_cli(json.dumps(self.config))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_config_fixtures_through_cli(self):
        # path, replacement, expected field: each fixture alters one valid input.
        cases = [
            (('source_commit',), 'main', 'config.source_commit'),
            (('source_commit',), '0' * 40, 'config.source_commit'),
            (('harness',), 'other', 'config.harness'),
            (('schema_version',), 2, 'config.schema_version'),
            (('inference', 'model'), '', 'config.inference.model'),
            (('inference', 'port'), 0, 'config.inference.port'),
            (('inference', 'port'), 65536, 'config.inference.port'),
            (('inference', 'port'), True, 'config.inference.port'),
            (('inference', 'host'), 'example.com', 'config.inference.host'),
            (('inference', 'api_path'), '/v1?key=secret', 'config.inference.api_path'),
            (('inference', 'context_length_tokens'), 4096, 'config.inference.context_length_tokens'),
            (('limits', 'concurrency'), 2, 'config.limits.concurrency'),
            (('limits', 'max_calls'), 0, 'config.limits.max_calls'),
            (('limits', 'timeout_seconds'), 121, 'config.limits.timeout_seconds'),
            (('privacy', 'synthetic'), False, 'config.privacy.synthetic'),
        ]
        for path, value, expected in cases:
            config = copy.deepcopy(self.config)
            parent = config
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = value
            with self.subTest(path=path, value=value):
                result = self.run_cli(json.dumps(config))
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, result.stderr)
        del self.config['inference']['model']
        result = self.run_cli(json.dumps(self.config))
        self.assertEqual(result.returncode, 1)
        self.assertIn('config.inference.model', result.stderr)

    def test_unknown_fields_and_secrets_are_not_echoed(self):
        secret = 'synthetic-secret-do-not-log'
        self.config['api_key'] = secret
        self.config['inference']['mode'] = secret
        result = self.run_cli(json.dumps(self.config))
        self.assertEqual(result.returncode, 1)
        self.assertIn('additionalProperties', result.stderr)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_source_lock_drift_rejected(self):
        for field in ['commit', 'source_files_sha256', 'model']:
            lock = copy.deepcopy(self.lock)
            if field == 'commit':
                lock[field] = '0' * 40
            elif field == 'model':
                lock[field]['manifest_sha256'] = '0' * 64
            else:
                lock[field]['LICENSE'] = '0' * 64
            with self.subTest(field=field):
                result = self.run_cli(json.dumps(self.config), lock)
                self.assertEqual(result.returncode, 1)
                self.assertIn(f'lock.{field}', result.stderr)

    def test_ollama_must_match_approved_model_and_endpoint(self):
        self.config['inference'].update(mode='ollama', port=11434, model=self.lock['model']['name'])
        for field, value in [('model', 'different-model'), ('port', 18080), ('max_output_tokens', 128)]:
            config = copy.deepcopy(self.config)
            config['inference'][field] = value
            with self.subTest(field=field):
                result = self.run_cli(json.dumps(config))
                self.assertEqual(result.returncode, 1)
                self.assertIn(f'config.inference.{field}', result.stderr)

    def test_strict_json_and_invalid_root(self):
        for text in ['{"harness":"hermes","harness":"other"}', '{"x": NaN}', '{', '[]', '{"x": 1e309}', '{"x": -1e309}']:
            with self.subTest(text=text):
                result = self.run_cli(text)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr)

    def test_missing_files_report_failure(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), '/no-such-agent-os-config.json'],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
