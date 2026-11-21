#!/usr/bin/env python3
"""Best aggregate rate of every case in the loop-rate files of 2026-10-30.
A case is one header line ("-- ...") plus kernel, threads and bytes per thread.
Prints: file line of the best row, header, kernel, threads, size, best GB/s, all reps.
Usage: rates.py <csv> [filter substring ...]"""
import sys, collections
path = sys.argv[1]; filt = sys.argv[2:]
hdr = ""; cases = collections.OrderedDict()
for n, line in enumerate(open(path, encoding="utf-8"), 1):
    line = line.rstrip("\n")
    if line.startswith("--"): hdr = line[2:].strip(); continue
    if not line or line.startswith("#") or line.startswith("kernel,"): continue
    f = line.split(",")
    if len(f) < 10: continue
    key = (hdr, f[0], int(f[1]), int(f[2]))
    cases.setdefault(key, []).append((float(f[6]), n, f[3]))
def size(b):
    for u, s in (("G", 1 << 30), ("M", 1 << 20), ("K", 1 << 10)):
        if b % s == 0: return f"{b // s}{u}"
    return str(b)
for (hdr, k, t, b), rows in cases.items():
    text = f"{hdr} | {k} | T={t} | {size(b)}"
    if filt and not all(x in text for x in filt): continue
    best = max(rows)
    print(f"L{best[1]:<4} {text:<60} best {best[0]:7.2f}  reps {[r[0] for r in rows]}")
