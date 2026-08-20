#!/usr/bin/env python3
"""Bypass-activation proof + drain-tail stats for one draw's kvwait.bin.

Per device d (0..3): count tag-7700+d records (bypass hold, dur = hold+memset+
callback), and pair each with the first tag-4000+d completion instant at or
after its end -> drain_tail = t4000 - t7700_end (cycles).

Usage: wcls7700.py kvwait.bin out.csv
"""
import bisect
import sys

import numpy as np

raw = np.fromfile(sys.argv[1], dtype=np.uint64)
n = int(raw[0])
recs = raw[1:1 + 3 * ((len(raw) - 1) // 3)].reshape(-1, 3)
recs = recs[:min(n, recs.shape[0])]
recs = recs[recs[:, 0] > 10**12]
t0, dur, tag = recs[:, 0].astype(np.int64), recs[:, 1].astype(np.int64), recs[:, 2]

rows = []
for d in range(4):
    h_t0, h_dur = t0[tag == 7700 + d], dur[tag == 7700 + d]
    h_end = h_t0 + h_dur
    c_end = np.sort(t0[tag == 4000 + d] + dur[tag == 4000 + d])
    tails = []
    for i in range(len(h_end)):
        j = bisect.bisect_left(c_end, h_end[i])
        tail = int(c_end[j] - h_end[i]) if j < len(c_end) else -1
        tails.append(tail)
        rows.append((d, i, int(h_t0[i]), int(h_dur[i]), tail))
    ta = np.array([t for t in tails if t >= 0])
    if len(h_dur):
        print(f"dev{d}: n7700={len(h_dur)} hold_p50={np.percentile(h_dur,50):.0f}cyc "
              f"p99={np.percentile(h_dur,99):.0f} max={h_dur.max()} "
              f"drain_p50={np.percentile(ta,50):.0f} p99={np.percentile(ta,99):.0f} "
              f"max={ta.max()}")
    else:
        print(f"dev{d}: n7700=0")

with open(sys.argv[2], "w") as f:
    f.write("dev,ix,t0,hold_dur,drain_tail\n")
    for r in rows:
        f.write(",".join(str(x) for x in r) + "\n")
