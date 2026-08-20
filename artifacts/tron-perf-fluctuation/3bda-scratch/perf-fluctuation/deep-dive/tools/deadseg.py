#!/usr/bin/env python3
"""Classify dead segments inside each inter-attention gap.
A dead segment is a span not covered by any in-flight [tx,rx] interval.
Classes: 'mid' (ends with the next tx dispatch) vs 'tail' (runs to gap end).
Output: nmid/step, mid_total/step, mid_median, ntail/step, tail_total/step.
"""
import struct, sys, bisect

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn = []; tx = {}; rx = {}
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    s = int(tag) // 1000
    if s == 0 or tag < 1000: attn.append((t0, 0))
    elif s == 2: attn.append((t0 + dur, 2))
    elif s == 3: tx.setdefault(tag - 3000, []).append(t0)
    elif s == 4: rx.setdefault(tag - 4000, []).append(t0)
attn.sort()
ivals = []
for c in set(tx) & set(rx):
    a, b = sorted(tx[c]), sorted(rx[c])
    for i in range(min(len(a), len(b))):
        if b[i] > a[i]: ivals.append((a[i], b[i]))
ivals.sort()
starts = [iv[0] for iv in ivals]
# merge intervals globally
merged = []
for s0, e0 in ivals:
    if merged and s0 <= merged[-1][1]:
        if e0 > merged[-1][1]: merged[-1] = (merged[-1][0], e0)
    else:
        merged.append((s0, e0))
mstarts = [m[0] for m in merged]

mid = []; tail = []
ngap = 0
last_be = None
for t, kind in attn:
    if kind == 0:
        if last_be is not None and 0 < t - last_be < 50_000_000:
            gs, ge = last_be, t
            ngap += 1
            i = bisect.bisect_left(mstarts, gs)
            if i > 0 and merged[i-1][1] > gs: i -= 1
            cur = gs
            while i < len(merged) and merged[i][0] < ge:
                s0, e0 = merged[i]
                if s0 > cur:
                    mid.append(min(s0, ge) - cur)   # dead span ended by a dispatch
                cur = max(cur, min(e0, ge))
                i += 1
            if cur < ge:
                tail.append(ge - cur)
        last_be = None
    else:
        last_be = t
steps = max(1, ngap / 36)
mid.sort()
med = mid[len(mid)//2] if mid else 0
print(f"{len(mid)/steps:.1f},{sum(mid)/steps:.0f},{med},{len(tail)/steps:.1f},{sum(tail)/steps:.0f}")
