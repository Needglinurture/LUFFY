#!/usr/bin/env python3
"""Rebuild the README 'Complete TODO List' section from the main baseline.

Rules:
- Start from the TODO list in origin/main's README.md (the baseline).
- For .py files changed between main and dev (excluding this temporary helper),
  re-extract TODOs from the dev working tree.
- Keep all baseline entries for unchanged files untouched.
- Sort by file path (lexicographic) then line number (ascending).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

README = Path('README.md')
HEADING = '### \U0001F4DD Complete TODO List'
ENTRY_RE = re.compile(r'^- \[ \] \*\*(?P<path>.+?):(?P<line>\d+)\*\* - (?P<text>.*)$')


def git_show(ref, path):
    return subprocess.check_output(
        ['git', 'show', f'{ref}:{path}'], text=True, encoding='utf-8')


def extract_todos(filepath):
    entries = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            idx = line.find('TODO')
            if idx == -1:
                continue
            text = line[idx + 4:].lstrip()
            if text.startswith(':'):
                text = text[1:]
            entries.append((filepath.replace(os.sep, '/'), lineno, text.strip()))
    return entries


def changed_py_files():
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', 'origin/main...HEAD', '--', '*.py'],
        text=True, stderr=subprocess.DEVNULL)
    files = [line.strip() for line in out.splitlines() if line.strip()]
    # Ignore the temporary helper / workflow internals; only real source changes count.
    files = [p for p in files if not p.startswith('tools/') and not p.startswith('.github/')]
    return files


def parse_entries(readme_text):
    lines = readme_text.split('\n')
    h = lines.index(HEADING)
    e = None
    for i in range(h + 1, len(lines)):
        if lines[i].startswith('## '):
            e = i
            break
    if e is None:
        raise RuntimeError('next heading not found')
    entries = []
    for line in lines[h + 1:e]:
        m = ENTRY_RE.match(line)
        if m:
            entries.append((m.group('path'), int(m.group('line')), m.group('text')))
    return lines, h, e, entries


def build_entry_lines(baseline_entries, changed):
    kept = [entry for entry in baseline_entries if entry[0] not in changed]
    new_entries = []
    for path in changed:
        if Path(path).exists():
            extracted = extract_todos(path)
            print(f'  {path}: {len(extracted)} TODO(s) in dev')
            for entry in extracted:
                print('   ', entry)
            new_entries.extend(extracted)
        else:
            print(f'  {path}: deleted in dev')
    all_entries = kept + new_entries
    seen = set()
    deduped = []
    for entry in all_entries:
        if entry not in seen:
            seen.add(entry)
            deduped.append(entry)
    deduped.sort(key=lambda item: (item[0], item[1]))
    entry_lines = [f'- [ ] **{path}:{lineno}** - {text}'
                   for path, lineno, text in deduped]
    return entry_lines, len(deduped)


def main():
    baseline_readme = git_show('origin/main', 'README.md')
    _, _, _, baseline_entries = parse_entries(baseline_readme)
    print('Baseline TODO entries from origin/main:', len(baseline_entries))

    changed = changed_py_files()
    print('Changed source .py files (main..dev):', changed)

    entry_lines, new_count = build_entry_lines(baseline_entries, changed)

    current_text = README.read_text(encoding='utf-8')
    lines, h, e, current_entries = parse_entries(current_text)
    print('Current TODO entries:', len(current_entries), '-> corrected:', new_count)

    new_lines = lines[:h + 1] + [''] + entry_lines + [''] + lines[e:]
    new_text = '\n'.join(new_lines)

    if new_text == current_text:
        print('No README changes needed.')
        return
    README.write_text(new_text, encoding='utf-8')
    print('README TODO section rebuilt successfully.')


if __name__ == '__main__':
    main()
