#!/usr/bin/env python3
"""Check repository Markdown and acceptance references without network access."""

import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
INLINE_LINK = re.compile(r'\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+[\'\"][^\'\"]*[\'\"])?\s*\)')
REFERENCE_LINK = re.compile(r'^ {0,3}\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)', re.MULTILINE)
INLINE_CODE = re.compile(r'(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)', re.DOTALL)
DEFINITION = re.compile(r'^\s*-\s+([LV]\d{2})(?=\s|[:：])', re.MULTILINE)
REFERENCE = re.compile(r'\b[LV]\d{2}\b')


def visible_markdown(text, label, errors):
    visible = []
    opened = None
    for number, line in enumerate(text.splitlines(), 1):
        if line != line.rstrip():
            errors.append(f'{label}:{number}: trailing whitespace')
        fence = FENCE.match(line)
        if opened is not None:
            if fence and fence[1][0] == opened[0] and len(fence[1]) >= opened[1] and not fence[2].strip():
                opened = None
            visible.append('')
        elif fence:
            opened = (fence[1][0], len(fence[1]), number)
            visible.append('')
        else:
            visible.append(line)
    if opened is not None:
        errors.append(f'{label}:{opened[2]}: unclosed code fence')
    if not text.endswith('\n'):
        errors.append(f'{label}: missing final newline')
    return '\n'.join(visible)


def check_prevention_list(text, label, errors):
    in_summary = False
    seen_rule = False
    blank_since_rule = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith('## '):
            in_summary = line == '## 预防规则汇总'
            seen_rule = False
            blank_since_rule = False
        elif in_summary and re.match(r'^\d+\. ', line):
            if seen_rule and blank_since_rule:
                errors.append(f'{label}:{number}: blank line between prevention rules')
            seen_rule = True
            blank_since_rule = False
        elif in_summary and not line.strip():
            blank_since_rule = True


def heading_anchors(text):
    anchors = set()
    counts = {}
    for heading in re.findall(r'^ {0,3}#{1,6}\s+(.+)$', text, re.MULTILINE):
        heading = re.sub(r'\s+#+\s*$', '', heading)
        heading = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', heading)
        heading = re.sub(r'<[^>]+>', '', heading)
        slug = re.sub(r'[^\w -]', '', heading.lower()).strip().replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(f'{slug}-{count}' if count else slug)
    return anchors


def check_docs(root):
    root = Path(root).resolve()
    files = sorted(set(root.glob('*.md')) | set((root / 'docs').rglob('*.md')) | set((root / '.github').glob('*.md')))
    errors = []
    documents = {}
    for path in files:
        label = path.relative_to(root).as_posix()
        if not path.resolve().is_relative_to(root):
            errors.append(f'{label}: document leaves repository')
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            errors.append(f'{label}: unreadable UTF-8 Markdown')
            continue
        documents[path.resolve()] = visible_markdown(text, label, errors)
    if not files:
        errors.append('repository: no Markdown files found')
    definitions = {}
    for path, text in documents.items():
        if path.relative_to(root).parts[:2] == ('docs', 'plans'):
            for match in DEFINITION.finditer(text):
                label = path.relative_to(root).as_posix()
                if match[1] in definitions:
                    errors.append(f'{label}: duplicate acceptance ID {match[1]}')
                definitions[match[1]] = path
    for path, text in documents.items():
        label = path.relative_to(root).as_posix()
        for match in REFERENCE.finditer(text):
            if match[0] not in definitions:
                line = text.count('\n', 0, match.start()) + 1
                errors.append(f'{label}:{line}: undefined acceptance ID {match[0]}')
        if label == 'docs/agent-self-improvement.zh-CN.md':
            check_prevention_list(text, label, errors)
        paragraphs = re.split(r'(\n[ \t]*\n)', text)
        link_text = ''.join(
            INLINE_CODE.sub(lambda match: re.sub(r'[^\n]', ' ', match[0]), paragraph)
            for paragraph in paragraphs
        )
        for pattern in (INLINE_LINK, REFERENCE_LINK):
            for match in pattern.finditer(link_text):
                line = text.count('\n', 0, match.start()) + 1
                location = f'{label}:{line}'
                try:
                    url = urlsplit(match[1].strip('<>'))
                except ValueError:
                    errors.append(f'{location}: malformed link')
                    continue
                if url.scheme or url.netloc:
                    continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                if not target.is_relative_to(root):
                    errors.append(f'{location}: link leaves repository')
                elif not target.exists():
                    errors.append(f'{location}: relative link target missing')
                elif url.fragment and target.suffix.lower() == '.md':
                    if target not in documents:
                        errors.append(f'{location}: Markdown anchor target outside checked documents')
                    elif unquote(url.fragment) not in heading_anchors(documents[target]):
                        errors.append(f'{location}: heading anchor missing')
    return sorted(set(errors)), len(files), len(definitions)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    errors, count, definitions = check_docs(args.root)
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'PASS: {count} Markdown files; {definitions} acceptance IDs')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
