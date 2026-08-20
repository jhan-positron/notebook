#!/usr/bin/env python3
"""Per-card round-trip window inside each inter-attention gap (probe v3)."""
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
for d in tx: tx[d].sort()
for d in rx: rx[d].sort()
cards = sorted(set(tx) & set(rx))
win = {c: 0 for c in cards}; ngap = 0
last_be = None
for t, kind in attn:
    if kind == 0:
        if last_be is not None and 0 < t - last_be < 50_000_000:
            ok = True; w = {}
            for c in cards:
                i1 = bisect.bisect_left(tx[c], last_be); i2 = bisect.bisect_left(tx[c], t)
                j1 = bisect.bisect_left(rx[c], last_be); j2 = bisect.bisect_left(rx[c], t)
                if i2 > i1 and j2 > j1 and tx[c][i1] <= rx[c][j2-1]:
                    w[c] = rx[c][j2-1] - tx[c][i1]
                else:
                    ok = False; break
            if ok:
                for c, v in w.items(): win[c] += v
                ngap += 1
        last_be = None
    else:
        last_be = t
steps = max(1, ngap / 36)
print(",".join([str(ngap)] + [f"{win[c]/steps:.0f}" for c in cards]))
