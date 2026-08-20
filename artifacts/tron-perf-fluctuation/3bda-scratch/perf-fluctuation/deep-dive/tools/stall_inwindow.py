#!/usr/bin/env python3
import struct, sys, glob, statistics as st
TSC = 2.7e9
root = sys.argv[1]
prof = [0.0]*30
early_late = []
for f in sorted(glob.glob(f"{root}/results/draw_*/kvwait.bin")):
    raw = open(f, "rb").read()
    n = struct.unpack_from("<Q", raw, 0)[0]
    n = min(n, (len(raw) - 8) // 24)
    fills = []
    for i in range(n):
        t0, dur, tag = struct.unpack_from("<QQQ", raw, 8+24*i)
        if tag == 7000: fills.append((t0, dur))
    fills.sort()
    if not fills: continue
    med = st.median(x[1] for x in fills)
    w0 = fills[0][0]
    dmass = [0.0]*30
    for t, dur in fills:
        if dur > med:
            b = int((t - w0)/TSC)
            if 0 <= b < 30: dmass[b] += (dur - med)/TSC
    tot = sum(dmass)
    if tot > 0:
        for b in range(30): prof[b] += dmass[b]/tot
        half = sum(dmass[:12]); early_late.append((half/tot, f.split("/")[-2]))
ndraws = len(early_late)
print("mean fraction of excess-fill mass per 1s bin since window start (16 draws):")
print(" ".join(f"{100*prof[b]/ndraws:4.1f}" for b in range(24)))
fr = [x for x,_ in early_late]
print(f"first-12s share: mean {100*st.mean(fr):.0f}%  min {100*min(fr):.0f}%  max {100*max(fr):.0f}%")
