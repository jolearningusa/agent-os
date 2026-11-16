#!/usr/bin/env python3
"""Validate offline Hermes call lifecycle events and their relationships."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from jsonschema import FormatChecker

from check_harness_config import ROOT, read_json, schema_errors

EVENT_FORMATS = FormatChecker(formats=[])


@EVENT_FORMATS.checks('date-time', raises=ValueError)
def is_utc_datetime(value):
    if not isinstance(value, str):
        return True  # The schema type validator handles non-strings.
    datetime.fromisoformat(value)
    return value.endswith('Z')


IDENTITY_FIELDS = ('session_id', 'turn_id', 'parent_call_id', 'model', 'harness_commit', 'config_hash')


def validate_events(events):
    if not isinstance(events, list) or not events:
        return ['events: expected a non-empty JSON array'], 0
    errors = []
    for index, event in enumerate(events):
        errors.extend(schema_errors(
            event, ROOT / 'schemas/context-event.json', f'events[{index}]',
            format_checker=EVENT_FORMATS,
        ))
    if errors:
        return errors, 0
    event_ids = set()
    sequences = {}
    calls = {}
    attempts = set()
    finished = set()
    for index, event in enumerate(events):
        label = f'events[{index}]'
        instance = event['instance_id']
        call_key = (instance, event['call_id'])
        attempt_key = (*call_key, event['attempt_id'])
        identity = tuple(event[name] for name in IDENTITY_FIELDS)
        if event['event_id'] in event_ids:
            errors.append(f'{label}.event_id: duplicate event')
        event_ids.add(event['event_id'])
        if event['sequence'] <= sequences.get(instance, 0):
            errors.append(f'{label}.sequence: must increase within instance')
        sequences[instance] = event['sequence']
        if event['event_type'] == 'call_started':
            if attempt_key in attempts:
                errors.append(f'{label}.attempt_id: duplicate start')
            attempts.add(attempt_key)
            if call_key in calls and calls[call_key] != identity:
                errors.append(f'{label}.call_id: call identity changed')
            parent = event['parent_call_id']
            if parent is not None:
                parent_key = (instance, parent)
                if parent == event['call_id']:
                    errors.append(f'{label}.parent_call_id: self reference')
                elif parent_key not in calls:
                    errors.append(f'{label}.parent_call_id: parent has not started')
                elif calls[parent_key][0] != event['session_id']:
                    errors.append(f'{label}.parent_call_id: different session')
            calls.setdefault(call_key, identity)
        else:
            if attempt_key not in attempts:
                errors.append(f'{label}.attempt_id: missing start')
            if calls.get(call_key) != identity:
                errors.append(f'{label}.call_id: call identity changed')
            if attempt_key in finished:
                errors.append(f'{label}.attempt_id: duplicate finish')
            finished.add(attempt_key)
    return errors, len(attempts - finished)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events', type=Path)
    args = parser.parse_args(argv)
    try:
        events = read_json(args.events)
        errors, open_attempts = validate_events(events)
    except (ValueError, OSError, UnicodeError):
        print('FAIL: events could not be read as strict UTF-8 JSON', file=sys.stderr)
        return 1
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'PASS: event contract validated; events={len(events)}; open_attempts={open_attempts}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
