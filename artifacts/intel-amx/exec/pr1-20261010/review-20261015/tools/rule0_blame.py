#!/usr/bin/env python3
"""For every line the commit removed, find (git blame at the parent) which commit introduced it; a line whose commit is not
in the PR's own range predates the PR."""
import subprocess, sys, re, collections
W, PARENT, COMMIT, BASE = sys.argv[1:5]
def git(*a): return subprocess.run(['git', '-C', W, *a], capture_output=True, text=True).stdout
pr_commits = set(git('rev-list', f'{BASE}..{PARENT}').split())
files = git('diff', '--name-only', PARENT, COMMIT).split()
viol = collections.defaultdict(list)
for f in files:
    # removed lines with their old line numbers
    diff = git('diff', '-U0', PARENT, COMMIT, '--', f)
    old = None
    for ln in diff.split('\n'):
        m = re.match(r'@@ -(\d+)(?:,(\d+))? \+', ln)
        if m: old = int(m.group(1)); continue
        if ln.startswith('-') and not ln.startswith('---'):
            removed_lines = [(old, ln[1:])]; old += 1
            for (n, text) in removed_lines:
                bl = git('blame', '-l', '-L', f'{n},{n}', PARENT, '--', f)
                sha = bl.split()[0].lstrip('^')
                if sha not in pr_commits and text.strip() not in ('', '//'):
                    viol[f].append((n, sha[:10], text))
        elif ln.startswith('+') and not ln.startswith('+++'): pass
for f, v in viol.items():
    print(f'== {f}: {len(v)} removed line(s) predate the PR')
    for n, sha, text in v: print(f'   old line {n} [{sha}] {text}')
print('files with pre-PR removals:', len(viol))
