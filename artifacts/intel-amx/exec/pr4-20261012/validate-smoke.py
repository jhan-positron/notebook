#!/usr/bin/env python3
"""validate-smoke.py <smoke dir> <LEN> <arm>...: the smoke validator of PR3-handoff.md step 6 D (a copy of exec/pr2-20261011/validate-smoke.py).
Exit 0 and print "VALIDATE ok" when every named arm has a "smoke <arm> rc=0" line in smoke.txt (the LAST rc line of that
arm; smoke.txt is appended to across reruns) and <arm>.tokens holds exactly LEN tokens (the integers of its first non-blank
line, read as smoke.sh reads them). Otherwise print every shortfall and exit 1. smoke.sh's own verdict compares only the common
prefix of two token rows and ignores exit codes, so this check is required next to smoke.done."""
import os, re, sys
d, n, arms = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
p = os.path.join(d, 'smoke.txt')
txt = open(p, errors='replace').read() if os.path.exists(p) else ''
bad = []
for a in arms:
    rcs = re.findall(rf'^smoke {re.escape(a)} rc=(\d+)', txt, re.M)
    if not rcs: bad.append(f'{a}: no "smoke {a} rc=" line in smoke.txt')
    elif rcs[-1] != '0': bad.append(f'{a}: rc={rcs[-1]}')
    t = os.path.join(d, a + '.tokens')
    if not os.path.exists(t): bad.append(f'{a}: {a}.tokens missing'); continue
    lines = [l for l in open(t, errors='replace').read().splitlines() if l.strip()]
    toks = re.findall(r'-?\d+', lines[0]) if lines else []
    if len(toks) != n: bad.append(f'{a}: {len(toks)} tokens in {a}.tokens (expected {n})')
print('VALIDATE ' + ('ok' if not bad else 'failed: ' + '; '.join(bad)))
sys.exit(0 if not bad else 1)
