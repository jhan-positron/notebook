#!/usr/bin/env python3
"""v5 boundary decomposition per step:
A1 = barrier(L35) exit -> alloc-wait record start (host prep + dispatch)
A2 = alloc wait duration (7100: card ready to stream)
PR = stream prepare (7200)
A3 = prepare end -> fill start (residual notify path)
B  = fill duration (7000), C = fill end -> next q0.
"""
import struct, sys, bisect

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn = []; fills = []; allocs = []; preps = []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    if tag == 0: attn.append((t0, "q0"))
    elif tag == 2035: attn.append((t0 + dur, "b35"))
    elif tag == 7000: fills.append((t0, dur))
    elif tag == 7100: allocs.append((t0, dur))
    elif tag == 7200: preps.append((t0, dur))
attn.sort(); fills.sort(); allocs.sort(); preps.sort()
fs = [f[0] for f in fills]; als = [a[0] for a in allocs]; prs = [p[0] for p in preps]
agg = [0]*6; nb = 0
last = None
for t, kind in attn:
    if kind == "q0":
        if last is not None and 0 < t - last < 50_000_000:
            i = bisect.bisect_left(fs, last)
            j = bisect.bisect_left(als, last)
            k = bisect.bisect_left(prs, last)
            if i < len(fills) and fills[i][0] < t and j < len(allocs) and allocs[j][0] < t and k < len(preps) and preps[k][0] < t:
                f0, fd = fills[i]; a0, ad = allocs[j]; p0, pd = preps[k]
                vals = (a0 - last, ad, pd, max(0, f0 - (p0 + pd)), fd, t - (f0 + fd))
                if all(v >= 0 for v in vals):
                    for x in range(6): agg[x] += vals[x]
                    nb += 1
        last = None
    else:
        last = t
print(",".join([str(nb)] + [f"{v/max(nb,1):.0f}" for v in agg]))
