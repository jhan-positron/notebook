#!/usr/bin/env python3
"""Within-draw, per-step correlation between boundary segments (A1, B, Crest)."""
import struct, sys, bisect, statistics as st
raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn=[]; fills=[]; allocs=[]; cbs=[]
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8+24*i)
    if tag == 0: attn.append((t0,"q0"))
    elif tag == 2035: attn.append((t0+dur,"b35"))
    elif tag == 7000: fills.append((t0,dur))
    elif tag == 7100: allocs.append((t0,dur))
    elif tag == 7400: cbs.append((t0,dur))
attn.sort(); fills.sort(); allocs.sort(); cbs.sort()
fs=[f[0] for f in fills]; als=[a[0] for a in allocs]; cs=[c[0] for c in cbs]
rows=[]
last=None
for t,kind in attn:
    if kind=="q0":
        if last is not None and 0 < t-last < 50_000_000:
            i=bisect.bisect_left(fs,last); j=bisect.bisect_left(als,last)
            if i<len(fills) and fills[i][0]<t and j<len(allocs) and allocs[j][0]<t:
                f0,fd=fills[i]; a0,_=allocs[j]; fe=f0+fd
                k=bisect.bisect_left(cs,fe-1000)
                if k<len(cbs) and cbs[k][0]<t:
                    c0,cd=cbs[k]
                    rows.append((a0-last, fd, t-(c0+cd)))
        last=None
    else: last=t
def corr(x,y):
    mx,my=st.mean(x),st.mean(y)
    sx=sum((a-mx)**2 for a in x)**.5; sy=sum((b-my)**2 for b in y)**.5
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/(sx*sy) if sx*sy else 0
A1=[r[0] for r in rows]; B=[r[1] for r in rows]; CR=[r[2] for r in rows]
print(f"steps={len(rows)}  perstep corr: A1~B {corr(A1,B):+.2f}  A1~Crest {corr(A1,CR):+.2f}  B~Crest {corr(B,CR):+.2f}")
print(f"  medians A1 {st.median(A1):,.0f}  B {st.median(B):,.0f}  Crest {st.median(CR):,.0f}")
print(f"  p90     A1 {sorted(A1)[int(0.9*len(A1))]:,.0f}  B {sorted(B)[int(0.9*len(B))]:,.0f}  Crest {sorted(CR)[int(0.9*len(CR))]:,.0f}")
