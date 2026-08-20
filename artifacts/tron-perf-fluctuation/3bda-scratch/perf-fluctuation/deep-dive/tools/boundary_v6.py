#!/usr/bin/env python3
"""v6: adds sampler split of C. Per boundary gap:
A1, A2(alloc), B(fill), C1(fill end->sample start), C2(sample dur), C3(sample end->next q0)."""
import struct, sys, bisect

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn = []; fills = []; allocs = []; samples = []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    if tag == 0: attn.append((t0, "q0"))
    elif tag == 2035: attn.append((t0 + dur, "b35"))
    elif tag == 7000: fills.append((t0, dur))
    elif tag == 7100: allocs.append((t0, dur))
    elif tag == 7300: samples.append((t0, dur))
attn.sort(); fills.sort(); allocs.sort(); samples.sort()
fs = [f[0] for f in fills]; als = [a[0] for a in allocs]; sms = [s0 for s0, _ in samples]
agg = [0]*6; nb = 0
last = None
for t, kind in attn:
    if kind == "q0":
        if last is not None and 0 < t - last < 50_000_000:
            i = bisect.bisect_left(fs, last); j = bisect.bisect_left(als, last)
            if i < len(fills) and fills[i][0] < t and j < len(allocs) and allocs[j][0] < t:
                f0, fd = fills[i]; a0, ad = allocs[j]
                fe = f0 + fd
                k = bisect.bisect_left(sms, fe)
                if k < len(samples) and samples[k][0] < t:
                    s0, sd = samples[k]
                    vals = (a0 - last, ad, fd, s0 - fe, sd, t - (s0 + sd))
                    if all(v >= 0 for v in vals):
                        for x in range(6): agg[x] += vals[x]
                        nb += 1
        last = None
    else:
        last = t
print(",".join([str(nb)] + [f"{v/max(nb,1):.0f}" for v in agg]))
