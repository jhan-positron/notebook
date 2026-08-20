#!/usr/bin/env python3
"""Per-job P5->P6 pairing (FIFO per card) + inter-completion spacing.
Output: draw, njobs/card, median job latency, p90 job latency, median rx spacing (busy bursts).
"""
import struct, sys, statistics as st

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
tx = {}; rx = {}
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    s = int(tag) // 1000
    if s == 3: tx.setdefault(tag - 3000, []).append(t0)
    elif s == 4: rx.setdefault(tag - 4000, []).append(t0)
lat = []; spacing = []
for c in sorted(set(tx) & set(rx)):
    a, b = sorted(tx[c]), sorted(rx[c])
    m = min(len(a), len(b))
    # FIFO pairing; drop first/last 100 for warmup/teardown edges
    for i in range(100, m - 100):
        d = b[i] - a[i]
        if 0 < d < 20_000_000: lat.append(d)
    # spacing between consecutive completions when the ring is busy
    # (next tx already issued before this rx -> pipeline busy)
    ti = 0
    for i in range(101, m - 100):
        gap = b[i] - b[i-1]
        # busy if some tx was pending before b[i-1]
        if a[min(i+1, m-1)] < b[i-1] and 0 < gap < 5_000_000:
            spacing.append(gap)
lat.sort(); spacing.sort()
def pct(v, p): return v[int(p*len(v))] if v else 0
print(f"{len(lat)},{pct(lat,0.5)},{pct(lat,0.9)},{len(spacing)},{pct(spacing,0.5)},{pct(spacing,0.9)}")
