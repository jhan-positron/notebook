#!/usr/bin/env python3
"""Exact parent (boundary gap) total per step + the alloc_end->fill_start piece
missing from boundary_v7 columns. Output: n, parent_total, missing_piece."""
import struct, sys, bisect
raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn=[]; fills=[]; allocs=[]
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8+24*i)
    if tag == 0: attn.append((t0,"q0"))
    elif tag == 2035: attn.append((t0+dur,"b35"))
    elif tag == 7000: fills.append((t0,dur))
    elif tag == 7100: allocs.append((t0,dur))
attn.sort(); fills.sort(); allocs.sort()
fs=[f[0] for f in fills]; als=[a[0] for a in allocs]
tot=miss=0; nb=0
last=None
for t,kind in attn:
    if kind=="q0":
        if last is not None and 0 < t-last < 50_000_000:
            i=bisect.bisect_left(fs,last); j=bisect.bisect_left(als,last)
            if i<len(fills) and fills[i][0]<t and j<len(allocs) and allocs[j][0]<t:
                f0,fd=fills[i]; a0,ad=allocs[j]
                m = f0 - (a0+ad)
                if m >= 0:
                    tot += t-last; miss += m; nb += 1
        last=None
    else: last=t
print(f"{nb},{tot/max(nb,1):.0f},{miss/max(nb,1):.0f}")
