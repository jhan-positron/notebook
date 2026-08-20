#!/usr/bin/env python3
"""Arm A extraction: fpga_use 1 s poller windows from a draw's kvwait.bin.

Arm A (fpgastat-20260817T013917Z) recorded, per device and ~1 s window,
kvwait records with tags 8000 + dev*100 + field, field 0..8 =
hbm_timer, hbm_read_cycles, mm_timer, mm_bp, mm_in_prog, mm_rmem_bp,
mm_wmem_bp, cb_stat(raw), rmem_ctrl(raw). One row per (window t0, device),
absolute counters plus derived shares. Preamble records (t0 <= 1e12) kept
out. Used to build the durable arm A archive (RUNBOOK-fpgastat-armB.md §5).

Usage: fpgause_poller_dump.py kvwait.bin out.csv
"""
import sys

import numpy as np

FIELDS = ("hbm_timer", "hbm_read", "mm_timer", "mm_bp", "mm_in_prog",
          "mm_rmem_bp", "mm_wmem_bp", "cb_stat", "rmem_ctrl")
NDEV = 4

raw = np.fromfile(sys.argv[1], dtype=np.uint64)
n = int(raw[0])
body = raw[1:1 + 3 * ((raw.size - 1) // 3)].reshape(-1, 3)
if body.shape[0] < n:
    sys.exit(f"FAIL truncated: header {n}, present {body.shape[0]}")
recs = body[:n].astype(np.int64)
recs = recs[recs[:, 0] > 10**12]

groups = {}
m = (recs[:, 2] >= 8000) & (recs[:, 2] < 8000 + NDEV * 100)
for t0, dur, tag in recs[m]:
    rel = int(tag) - 8000
    dev, field = divmod(rel, 100)
    if field > 8:
        continue
    groups.setdefault((int(t0), dev), {})[field] = int(dur)

with open(sys.argv[2], "w") as fh:
    fh.write("t0,dev," + ",".join(FIELDS)
             + ",hbm_duty,share_in_prog,share_bp,share_wmem_bp\n")
    for (t0, dev), f in sorted(groups.items()):
        vals = [f.get(i, -1) for i in range(9)]
        hbm_t, hbm_r, mm_t, mm_bp, mm_ip = vals[0], vals[1], vals[2], vals[3], vals[4]
        if hbm_t > 0 and mm_t > 0:
            der = (hbm_r / hbm_t, mm_ip / mm_t, mm_bp / mm_t, vals[6] / mm_t)
        else:
            der = (-1.0, -1.0, -1.0, -1.0)
        fh.write(f"{t0},{dev}," + ",".join(str(v) for v in vals)
                 + "," + ",".join(f"{d:.6g}" for d in der) + "\n")
print(f"{sys.argv[2]}: {len(groups)} windows")
