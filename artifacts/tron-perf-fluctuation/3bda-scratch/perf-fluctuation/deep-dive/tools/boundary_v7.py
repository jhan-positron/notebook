#!/usr/bin/env python3
"""v7: C split by listener callback. Per boundary gap:
A1, A2, B(fill), Ccb_pre(fill end->cb start), Ccb(callback dur), Crest(cb end->next q0)."""
import struct, sys, bisect
raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn = []; fills = []; allocs = []; cbs = []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    if tag == 0: attn.append((t0, "q0"))
    elif tag == 2035: attn.append((t0 + dur, "b35"))
    elif tag == 7000: fills.append((t0, dur))
    elif tag == 7100: allocs.append((t0, dur))
    elif tag == 7400: cbs.append((t0, dur))
attn.sort(); fills.sort(); allocs.sort(); cbs.sort()
fs=[f[0] for f in fills]; als=[a[0] for a in allocs]; cs=[c[0] for c in cbs]
agg=[0]*6; nb=0
last=None
for t, kind in attn:
    if kind == "q0":
        if last is not None and 0 < t - last < 50_000_000:
            i=bisect.bisect_left(fs,last); j=bisect.bisect_left(als,last)
            if i<len(fills) and fills[i][0]<t and j<len(allocs) and allocs[j][0]<t:
                f0,fd=fills[i]; a0,ad=allocs[j]; fe=f0+fd
                k=bisect.bisect_left(cs,fe-1000)
                if k<len(cbs) and cbs[k][0]<t:
                    c0,cd=cbs[k]
                    vals=(a0-last, ad, fd, max(0,c0-fe), cd, t-(c0+cd))
                    if all(v>=0 for v in vals):
                        for x in range(6): agg[x]+=vals[x]
                        nb+=1
        last=None
    else:
        last=t
print(",".join([str(nb)]+[f"{v/max(nb,1):.0f}" for v in agg]))
