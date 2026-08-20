#!/usr/bin/env python3
"""Dump per-token fence segments for one draw's kvwait.bin.

Same gap bracketing and hygiene as fence3_split.py (tag-2035 end -> next
tag-0 start, positional decode filter, preamble drop). One row per valid
decode gap, in encounter order: gap_ix, F1F3, openF1, F3end, gap, F3period.
The 4095 decode gaps cover generated tokens 2..4096 - the first token is
produced by the prefill pass and is excluded by construction.

Usage: fence3_dump.py kvwait.bin out.csv
"""
import bisect
import sys

import numpy as np

GAP_MAX_CYC = 50_000_000

raw = np.fromfile(sys.argv[1], dtype=np.uint64)
n = int(raw[0])
recs = raw[1:1 + 3 * ((len(raw) - 1) // 3)].reshape(-1, 3)
recs = recs[:min(n, recs.shape[0])]
recs = recs[recs[:, 0] > 10**12]
t0, dur, tag = recs[:, 0], recs[:, 1], recs[:, 2]


def series(sel, use_end=False):
    m = tag == sel
    s = t0[m] + (dur[m] if use_end else 0)
    d = dur[m]
    o = np.argsort(s)
    return s[o].tolist(), d[o].tolist()


q0s, _ = series(0)
b35es, _ = series(2035, use_end=True)
f3_s, f3_d = series(7600)
f1_e, f1_d = series(7601, use_end=True)
al_s, al_d = series(7100)
fi_s, fi_d = series(7000)
cb_s, cb_d = series(7400)

rows = []
for qi in range(1, len(q0s)):
    g1 = q0s[qi]
    prev_q0 = q0s[qi - 1]
    bi = bisect.bisect_left(b35es, g1) - 1
    if bi < 0:
        continue
    g0 = b35es[bi]
    if not (prev_q0 < g0 < g1) or not (0 < g1 - g0 < GAP_MAX_CYC):
        continue
    # same association requirements as fence3_split.py, so the row set is
    # identical to the analyzer's nb=4095 decode gaps (prefill edges out)
    i = bisect.bisect_left(al_s, g0)
    j = bisect.bisect_left(fi_s, g0)
    if not (i < len(al_s) and al_s[i] < g1 and j < len(fi_s) and fi_s[j] < g1):
        continue
    fe = fi_s[j] + fi_d[j]
    k = bisect.bisect_left(cb_s, fe - 1000)
    if not (k < len(cb_s) and cb_s[k] < g1):
        continue
    k3 = bisect.bisect_left(f3_s, g0)
    if not (k3 < len(f3_s) and f3_s[k3] < g1):
        continue
    k1 = bisect.bisect_left(f1_e, g0)
    if not (k1 < len(f1_e) and f1_e[k1] < g1):
        continue
    f3e = f3_s[k3] + f3_d[k3]
    f1e = f1_e[k1]
    period = ""
    if k3 + 1 < len(f3_s):
        p = (f3_s[k3 + 1] + f3_d[k3 + 1]) - f3e
        if 0 < p < GAP_MAX_CYC:
            period = int(p)
    rows.append((len(rows), int(f3e - f1e), int(f1e - g0), int(g1 - f3e),
                 int(g1 - g0), period, int(f3e)))

with open(sys.argv[2], "w") as f:
    f.write("gap_ix,F1F3,openF1,F3end,gap,F3period,t_f3\n")
    for r in rows:
        f.write(",".join(str(x) for x in r) + "\n")
print(f"{len(rows)} gaps -> {sys.argv[2]}")
