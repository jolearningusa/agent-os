"""L05 schema and lifecycle regression fixtures, all synthetic."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_context_events import validate_events
from check_harness_config import read_json

SCRIPT = ROOT / 'scripts/check_context_events.py'


class EventContractTests(unittest.TestCase):
    def setUp(self):
        self.events = read_json(ROOT / 'tests/fixtures/context-events.json')

    def run_cli(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.json'
            path.write_text(text)
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path)],
                cwd=folder, capture_output=True, text=True, timeout=15,
            )

    def test_complete_calls_and_unknown_usage_without_network(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            self.assertEqual(validate_events(self.events), ([], 0))
        result = self.run_cli(json.dumps(self.events))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('open_attempts=0', result.stdout)

    def test_optional_future_fields_and_incomplete_call(self):
        self.events[0]['future_optional_field'] = {'revision': 2}
        self.assertEqual(validate_events(self.events[:2]), ([], 2))
        result = self.run_cli(json.dumps(self.events[:1]))
        self.assertEqual(result.returncode, 0)
        self.assertIn('open_attempts=1', result.stdout)

    def test_schema_failure_fixtures(self):
        cases = [
            ('schema_version', 2, 'schema_version'),
            ('event_id', 'bad-id\n', 'event_id'),
            ('timestamp', '2026-02-30T12:00:00Z', 'timestamp'),
            ('timestamp', '2026-11-15T12:00:00+08:00', 'timestamp'),
            ('sequence', True, 'sequence'),
            ('status', 'completed', 'status'),
            ('parent_call_id', 123, 'parent_call_id'),
            ('event_type', 'made_up', 'event_type'),
        ]
        for field, value, expected in cases:
            events = copy.deepcopy(self.events)
            events[0][field] = value
            with self.subTest(field=field):
                errors, _ = validate_events(events)
                self.assertTrue(any(expected in error for error in errors), errors)
        for field in self.events[0]:
            events = copy.deepcopy(self.events)
            del events[0][field]
            with self.subTest(missing=field):
                self.assertTrue(validate_events(events)[0])

    def test_retry_identity_and_precise_timestamp(self):
        start = {**self.events[0], 'event_id': 'retry-start', 'sequence': 5, 'attempt_id': 'attempt-2',
                 'timestamp': '2026-11-15T12:00:00.123456Z'}
        finish = {**self.events[-1], 'event_id': 'retry-finish', 'sequence': 6, 'attempt_id': 'attempt-2'}
        self.assertEqual(validate_events(self.events + [start, finish]), ([], 0))

    def test_terminal_states_and_usage(self):
        for status in ['completed', 'failed', 'cancelled', 'unknown']:
            events = copy.deepcopy(self.events)
            events[-1]['status'] = status
            self.assertEqual(validate_events(events), ([], 0))
        for field in ['usage', 'latency_ms', 'finish_reason']:
            events = copy.deepcopy(self.events)
            del events[-1][field]
            self.assertTrue(validate_events(events)[0])
        self.events[-1]['usage']['input_tokens'] = -1
        self.assertTrue(validate_events(self.events)[0])

    def test_parent_relationships(self):
        for parent, expected in [('call-summary', 'self reference'), ('absent', 'has not started')]:
            events = copy.deepcopy(self.events)
            events[1]['parent_call_id'] = parent
            errors, _ = validate_events(events)
            self.assertTrue(any(expected in error for error in errors), errors)
        self.events[1]['session_id'] = 'session-b'
        self.events[2]['session_id'] = 'session-b'
        self.assertTrue(any('different session' in error for error in validate_events(self.events)[0]))

    def test_instance_boundaries_and_sequence(self):
        second = copy.deepcopy(self.events)
        for index, event in enumerate(second):
            event['instance_id'] = 'instance-b'
            event['event_id'] = f'other-{index}'
        self.assertEqual(validate_events(self.events + second), ([], 0))
        second[0]['parent_call_id'] = 'call-main'
        self.assertTrue(validate_events(second)[0])
        self.events[1]['sequence'] = 1
        self.assertTrue(any('sequence' in error for error in validate_events(self.events)[0]))

    def test_duplicate_and_changed_identity(self):
        events = copy.deepcopy(self.events)
        events[1]['event_id'] = events[0]['event_id']
        self.assertTrue(any('duplicate event' in error for error in validate_events(events)[0]))
        duplicate = {**self.events[-1], 'sequence': 5, 'event_id': 'duplicate-finish'}
        self.assertTrue(any('duplicate finish' in error for error in validate_events(self.events + [duplicate])[0]))
        self.events[-1]['turn_id'] = 'different-turn'
        self.assertTrue(any('identity changed' in error for error in validate_events(self.events)[0]))

    def test_missing_start_and_duplicate_start(self):
        self.assertTrue(any('missing start' in error for error in validate_events(self.events[2:])[0]))
        duplicate = {**self.events[0], 'sequence': 5, 'event_id': 'duplicate-start'}
        self.assertTrue(any('duplicate start' in error for error in validate_events(self.events + [duplicate])[0]))

    def test_cli_rejects_bad_input_without_echoing_values(self):
        secret = 'synthetic-private-marker'
        self.events[0]['status'] = secret
        result = self.run_cli(json.dumps(self.events))
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(secret, result.stdout + result.stderr)
        for text in ['[]', '{}', '{', '[{"schema_version": 1, "schema_version": 2}]', '[NaN]']:
            result = self.run_cli(text)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
