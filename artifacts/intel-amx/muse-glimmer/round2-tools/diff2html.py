#!/usr/bin/env python3
"""Render `git diff A B -- PATH` as the <pre class="diff"> block of the reply pages.

Each line shows the old and the new line number, so a reader can find the line in either commit.
Usage: diff2html.py REPO A B PATH [CONTEXT]
"""
import html, re, subprocess, sys

repo, a, b, path = sys.argv[1:5]
ctx = sys.argv[5] if len(sys.argv) > 5 else '3'
out = subprocess.run(['git', '-C', repo, 'diff', f'-U{ctx}', a, b, '--', path],
                     check=True, capture_output=True, text=True).stdout.split('\n')
rows, old, new, first = [], 0, 0, True
for ln in out:
    m = re.match(r'^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', ln)
    if m:
        old, new = int(m.group(1)), int(m.group(2))
        if not first:
            rows.append(('ctx', '', '', '...'))
        first = False
        continue
    if first or ln.startswith('\\'):
        continue
    if ln.startswith('-'):
        rows.append(('del', str(old), '', '-' + ln[1:])); old += 1
    elif ln.startswith('+'):
        rows.append(('add', '', str(new), '+' + ln[1:])); new += 1
    elif ln.startswith(' ') or ln == '':
        if ln == '' and (old == 0):
            continue
        rows.append(('ctx', str(old), str(new), ' ' + ln[1:])); old += 1; new += 1
while rows and rows[-1][3].strip() == '' and rows[-1][0] == 'ctx':
    rows.pop()
w = max([len(r[1]) for r in rows] + [len(r[2]) for r in rows] + [3])
print('<pre class="diff"><code>' + '\n'.join(
    f'<span class="{k}">{o:>{w}} {n:>{w}} {html.escape(t)}</span>' for k, o, n, t in rows) + '</code></pre>')
