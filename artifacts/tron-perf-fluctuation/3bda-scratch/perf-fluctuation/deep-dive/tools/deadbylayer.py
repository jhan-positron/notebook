#!/usr/bin/env python3
"""Dead time per gap position (gap after layer L), cycles/step."""
import struct, sys, bisect

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn = []; ivals = []
tx = {}; rx = {}
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    s = int(tag) // 1000
    if s == 0 or tag < 1000: attn.append((t0, 0, tag if tag < 1000 else 0))
    elif s == 2: attn.append((t0 + dur, 2, tag - 2000))
    elif s == 3: tx.setdefault(tag - 3000, []).append(t0)
    elif s == 4: rx.setdefault(tag - 4000, []).append(t0)
attn.sort()
for c in set(tx) & set(rx):
    a, b = sorted(tx[c]), sorted(rx[c])
    for i in range(min(len(a), len(b))):
        if b[i] > a[i]: ivals.append((a[i], b[i]))
ivals.sort()
merged = []
for s0, e0 in ivals:
    if merged and s0 <= merged[-1][1]:
        if e0 > merged[-1][1]: merged[-1] = (merged[-1][0], e0)
    else: merged.append((s0, e0))
mstarts = [m[0] for m in merged]

dead_by_layer = {}
ngap = 0; last = None
for t, kind, layer in attn:
    if kind == 0:
        if last is not None:
            gs, ge, gl = last[0], t, last[1]
            if 0 < ge - gs < 50_000_000:
                ngap += 1
                i = bisect.bisect_left(mstarts, gs)
                if i > 0 and merged[i-1][1] > gs: i -= 1
                cur = gs; dead = 0
                while i < len(merged) and merged[i][0] < ge:
                    s0, e0 = merged[i]
                    if s0 > cur: dead += min(s0, ge) - cur
                    cur = max(cur, min(e0, ge)); i += 1
                if cur < ge: dead += ge - cur
                dead_by_layer[gl] = dead_by_layer.get(gl, 0) + dead
        last = None
    else:
        last = (t, layer)
steps = max(1, ngap / 36)
top = sorted(dead_by_layer.items(), key=lambda kv: -kv[1])[:4]
rest = sum(v for k, v in dead_by_layer.items()) - sum(v for _, v in top)
print(",".join(f"L{k}:{v/steps:.0f}" for k, v in top) + f",rest:{rest/steps:.0f}")
