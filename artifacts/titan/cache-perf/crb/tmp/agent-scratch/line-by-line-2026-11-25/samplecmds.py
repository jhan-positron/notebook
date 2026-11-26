#!/usr/bin/env python3
"""samplecmds.py SEED KEY... - print the sample command of a sampled review for each key (main session)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbl
seed = int(sys.argv[1])
m = lbl.manifest()
for i, key in enumerate(sys.argv[2:]):
    e = m[key]
    rows = e['nonblank']
    n = rows if rows <= 25 else min(150, max(20, round(0.25 * rows)))
    print('- `%s` (%d rows): `python3 T2/lbl_main.py sample %s %d %d`%s' % (key, rows, key, n, seed + i, ' (every row)' if n == rows else ''))
