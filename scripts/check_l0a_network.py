#!/usr/bin/env python3
"""Probe macOS Seatbelt network isolation without running Hermes or a model."""

import json
import platform
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def listener():
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen()
    server.settimeout(0.2)
    return server


def main():
    if platform.system() != 'Darwin':
        raise SystemExit('This probe requires macOS and /usr/bin/sandbox-exec')
    with listener() as allowed, listener() as blocked:
        allowed_port = allowed.getsockname()[1]
        blocked_port = blocked.getsockname()[1]
        profile = f'''(version 1)
(allow default)
(deny network*)
(allow network-outbound (remote ip "localhost:{allowed_port}"))
'''
        client = '''import errno, json, socket, sys
results = {}
for name, host, port in [
    ('allowed_loopback', '127.0.0.1', int(sys.argv[1])),
    ('blocked_loopback', '127.0.0.1', int(sys.argv[2])),
    ('blocked_external', '192.0.2.1', 443),
]:
    try:
        with socket.create_connection((host, port), timeout=1):
            results[name] = 'connected'
    except OSError as exc:
        results[name] = 'denied' if exc.errno in (errno.EPERM, errno.EACCES) else 'inconclusive'
print(json.dumps(results))
'''
        with tempfile.TemporaryDirectory(prefix='agent-os-network-') as folder:
            policy = Path(folder) / 'network.sb'
            policy.write_text(profile)
            command = [
                '/usr/bin/sandbox-exec', '-f', str(policy),
                sys.executable, '-I', '-c', client,
                str(allowed_port), str(blocked_port),
            ]
            process = subprocess.run(command, capture_output=True, text=True, timeout=15)
        if process.returncode:
            raise SystemExit(f'sandbox probe failed: {process.stderr.strip()}')
        results = json.loads(process.stdout)
        expected = {
            'allowed_loopback': 'connected',
            'blocked_loopback': 'denied',
            'blocked_external': 'denied',
        }
        # Both ports have live listeners. A timeout/refusal is insufficient denial evidence.
        connection, _ = allowed.accept()
        connection.close()
        try:
            connection, _ = blocked.accept()
        except socket.timeout:
            results['blocked_listener'] = 'no_connection'
        else:
            connection.close()
            results['blocked_listener'] = 'unexpected_connection'
        passed = results == {**expected, 'blocked_listener': 'no_connection'}
        print(json.dumps({
            'probe': 'l0a-network-v1',
            'platform': platform.system(),
            'os_version': platform.mac_ver()[0],
            'architecture': platform.machine(),
            'scope': 'network-only; exact allowed localhost port; no Hermes/Ollama',
            'results': results,
            'status': 'pass' if passed else 'fail',
        }, indent=2))
        return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
