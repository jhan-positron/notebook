#!/usr/bin/env python3
"""mklist.py SEED KEY... - review list for seeded keys: a sample of the writer's rows and a small sample of all rows (main session)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbl
m = lbl.manifest()
seed0 = int(sys.argv[1])
for i, k in enumerate(sys.argv[2:]):
    errs = []
    own, seed, parts = lbl.load_ann(k, errs)
    src = lbl.source_lines(m[k]['src'])[0]
    need = [j for j in range(1, len(src) + 1) if src[j - 1].strip()]
    nown = len([j for j in need if j in own])
    nseed = len(need) - nown
    a = nown if nown <= 25 else min(150, max(20, round(0.25 * nown)))
    b = min(40, max(10, round(0.03 * nseed))) if nseed else 0
    line = '- `%s` (%d rows: %d of the writer, %d taken over): `python3 T2/lbl_main.py sample %s %d %d 0 0 own` (rows of the writer)' % (k, len(need), nown, nseed, k, a, seed0 + 2 * i)
    if b:
        line += ', then `python3 T2/lbl_main.py sample %s %d %d` (rows of the whole file, skip those already checked)' % (k, b, seed0 + 2 * i + 1)
    print(line)
