"""L06 checks use temporary repositories and never mutate real documents."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_docs.py'
spec = importlib.util.spec_from_file_location('check_docs', SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class DocumentCheckTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.write('README.md', '# Sample\n\n[Plan](docs/plans/plan.md#验收)\n\nUse L00.\n')
        self.write('docs/plans/plan.md', '# Plan\n\n## 验收\n\n- L00 input is valid.\n')

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def run_cli(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), '--root', str(self.root)],
            cwd=self.root, capture_output=True, text=True, timeout=10,
        )

    def test_valid_documents_without_network(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            errors, files, definitions = checker.check_docs(self.root)
        self.assertEqual((errors, files, definitions), ([], 2, 1))
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_each_bad_fixture_fails_then_recovers(self):
        cases = [
            ('# Bad  \n', 'trailing whitespace'),
            ('# Bad', 'final newline'),
            ('```python\nx = 1\n', 'unclosed code fence'),
            ('[Broken](missing.md)\n', 'target missing'),
            ('[Bad anchor](docs/plans/plan.md#absent)\n', 'anchor missing'),
            ('Undefined L99.\n', 'undefined acceptance ID'),
        ]
        original = (self.root / 'README.md').read_text()
        for content, expected in cases:
            with self.subTest(rule=expected):
                self.write('README.md', content)
                result = self.run_cli()
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, result.stdout)
                self.assertNotIn('Traceback', result.stderr)
                self.write('README.md', original)
                self.assertEqual(self.run_cli().returncode, 0)

    def test_duplicate_ids_across_plans_are_rejected(self):
        self.write('docs/plans/other.md', '# Other\n\n- L00 duplicate.\n')
        self.assertTrue(any('duplicate acceptance ID' in e for e in checker.check_docs(self.root)[0]))

    def test_fences_exclude_example_links_and_ids(self):
        self.write('docs/examples.md', '# Examples\n\n````md\n```\n[Missing](missing.md) L99\n````\n\n~~~text\nL98\n~~~\n')
        self.assertEqual(checker.check_docs(self.root)[0], [])
        self.write('docs/examples.md', '~~~text\n```\n')
        self.assertTrue(any('unclosed code fence' in e for e in checker.check_docs(self.root)[0]))

    def test_reference_image_and_encoded_links(self):
        self.write('docs/a b.md', '# Repeated\n\n## Same\n\n## Same\n')
        self.write('README.md', '# Links\n\n[Angle](<docs/a b.md#same-1>)\n[Encoded](docs/a%20b.md)\n![image](docs/a%20b.md)\n[ref]: docs/a%20b.md#same\n[web](https://example.invalid/unavailable)\n')
        self.assertEqual(checker.check_docs(self.root)[0], [])
        self.write('README.md', '# Links\n\n[ref]: missing.md\n')
        self.assertTrue(any('target missing' in e for e in checker.check_docs(self.root)[0]))

    def test_external_files_and_symlinks_are_not_read(self):
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / 'private.md'
            path.write_text('# Outside\n')
            (self.root / 'docs/escape.md').symlink_to(path)
            self.write('README.md', f'[Outside]({path.as_posix()})\n')
            errors = checker.check_docs(self.root)[0]
            self.assertTrue(any('document leaves repository' in e for e in errors))
            self.assertTrue(any('link leaves repository' in e for e in errors))

    def test_inline_code_examples_do_not_hide_real_links(self):
        self.write('README.md', '# Examples\n\n`[sample](missing.md)`\n\n``[sample](also-missing.md) with `ticks` ``\n')
        self.assertEqual(checker.check_docs(self.root)[0], [])
        with (self.root / 'README.md').open('a') as stream:
            stream.write('\n[Real](missing.md)\n')
        self.assertTrue(any('target missing' in e for e in checker.check_docs(self.root)[0]))

    def test_unmatched_code_ticks_cannot_cross_paragraphs(self):
        for blank in ['\n\n', '\n \t\n']:
            with self.subTest(blank=repr(blank)):
                self.write('README.md', '# Example\n\nFirst ` marker.' + blank + '[Real](missing.md)' + blank + 'Last ` marker.\n')
                self.assertTrue(any('target missing' in e for e in checker.check_docs(self.root)[0]))
        self.write('README.md', '# Example\n\n`First line\n[sample](missing.md) last line`\n')
        self.assertEqual(checker.check_docs(self.root)[0], [])

    def test_crlf_normalization_preserves_space_checks(self):
        path = self.root / 'README.md'
        path.write_bytes(b'# Valid\r\n')
        self.assertEqual(checker.check_docs(self.root)[0], [])
        path.write_bytes(b'# Invalid  \r\n')
        self.assertTrue(any('trailing whitespace' in e for e in checker.check_docs(self.root)[0]))

    def test_prevention_rules_require_compact_numbering(self):
        name = 'docs/agent-self-improvement.zh-CN.md'
        self.write(name, '# Log\n\n## 预防规则汇总\n\n1. First.\n\n2. Second.\n')
        self.assertTrue(any('blank line between prevention rules' in e for e in checker.check_docs(self.root)[0]))
        self.write(name, '# Log\n\n## 预防规则汇总\n\n1. First.\n2. Second.\n\n## Other\n\n1. First.\n\n2. Second.\n')
        self.assertEqual(checker.check_docs(self.root)[0], [])

    def test_unreadable_utf8_and_empty_scope_fail(self):
        (self.root / 'README.md').write_bytes(b'\xff')
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn('unreadable UTF-8', result.stdout)
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(checker.check_docs(empty)[0], ['repository: no Markdown files found'])


if __name__ == '__main__':
    unittest.main()
