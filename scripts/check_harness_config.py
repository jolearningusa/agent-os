#!/usr/bin/env python3
"""Validate the local Hermes configuration without executing the harness."""

import argparse
import json
import math
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    raise SystemExit('Install requirements-config.txt in the configuration-check venv')

ROOT = Path(__file__).resolve().parents[1]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-standard JSON number')


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('non-finite JSON number')
    return number


def read_json(path):
    return json.loads(
        Path(path).read_text(encoding='utf-8'),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
        parse_float=finite_float,
    )


def schema_errors(value, schema_path, label, format_checker=None):
    schema = read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = []
    for error in Draft202012Validator(schema, format_checker=format_checker).iter_errors(value):
        # Do not use error.message: it can echo user-provided credentials.
        parts = [str(part) for part in error.absolute_path]
        if error.validator == 'required':
            parts.append(next(name for name in error.validator_value if name not in error.instance))
        location = '.'.join([label, *parts])
        errors.append(f'{location}: violates {error.validator}')
    return sorted(set(errors))


def validate(config, lock):
    errors = schema_errors(lock, ROOT / 'schemas/harness-lock.schema.json', 'lock')
    errors += schema_errors(config, ROOT / 'configs/schema.json', 'config')
    if errors:
        return errors
    approved = read_json(ROOT / 'docs/evidence/l0a-source-inventory.json')
    expected = {key: value for key, value in approved.items() if key != 'model'}
    expected['model'] = {
        key: value for key, value in approved['model'].items()
        if key not in ('downloaded', 'purpose')
    }
    for field in expected:
        if lock[field] != expected[field]:
            errors.append(f'lock.{field}: differs from accepted L0a inventory')
    if config['source_commit'] != lock['commit']:
        errors.append('config.source_commit: differs from lock.commit')
    inference = config['inference']
    if inference['mode'] == 'ollama':
        if inference['port'] != 11434:
            errors.append('config.inference.port: Ollama requires locked port 11434')
        for field, locked_field in [('model', 'name'), ('context_length_tokens', 'context_length_tokens'),
                                    ('max_output_tokens', 'max_output_tokens')]:
            if inference[field] != lock['model'][locked_field]:
                errors.append(f'config.inference.{field}: differs from locked model')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--lock', type=Path, default=ROOT / 'harness.lock.json')
    args = parser.parse_args(argv)
    try:
        errors = validate(read_json(args.config), read_json(args.lock))
    except (ValueError, OSError, UnicodeError):
        print('FAIL: config or lock could not be read as strict UTF-8 JSON', file=sys.stderr)
        return 1
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('PASS: Hermes configuration and source lock validated')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
