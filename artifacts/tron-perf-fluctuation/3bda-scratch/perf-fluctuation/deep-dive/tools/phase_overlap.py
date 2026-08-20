#!/usr/bin/env python3
"""Across all draws of a campaign: build the 60s-phase profile of stall mass,
then per draw compute overlap of its fill window with the burst phase band.
Usage: phase_overlap.py <campaign_root>"""
import struct, sys, glob, math, statistics as st
TSC = 2.7e9; PERIOD = 60.0
root = sys.argv[1]
draws = {}
for f in sorted(glob.glob(f"{root}/results/draw_*/kvwait.bin")):
    d = f.split("/")[-2]
    raw = open(f, "rb").read()
    n = struct.unpack_from("<Q", raw, 0)[0]
    n = min(n, (len(raw) - 8) // 24)
    fills = []
    for i in range(n):
        t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
        if tag == 7000: fills.append((t0, dur))
    fills.sort()
    if fills: draws[d] = fills
# global phase histogram of EXCESS fill time (dur - draw median), 60 bins
bins = [0.0] * 60
for d, fills in draws.items():
    med = st.median(x[1] for x in fills)
    for t, dur in fills:
        if dur > med:
            ph = (t / TSC) % PERIOD
            bins[int(ph)] += (dur - med) / TSC
tot = sum(bins)
# find the burst band: smallest set of contiguous bins (circular) holding 60% of mass
best = None
for width in range(1, 40):
    for s in range(60):
        m = sum(bins[(s + k) % 60] for k in range(width))
        if m >= 0.6 * tot:
            if best is None or width < best[0]: best = (width, s, m)
            break
    if best and best[0] == width: break
width, s0, m = best
print(f"burst band: phase [{s0}s..{(s0+width)%60}s) of each minute holds {100*m/tot:.0f}% of excess fill mass (width {width}s)")
# per draw: overlap of [first fill, last fill] with band vs TPS
import csv
tps = {}
for r in csv.DictReader(open(f"{root}/results.csv")):
    if r["status"] == "ok": tps[r["draw"]] = float(r["generate_tok_s"])
rows = []
band = set((s0 + k) % 60 for k in range(width))
for d, fills in draws.items():
    if d not in tps: continue
    a, b = fills[0][0] / TSC, fills[-1][0] / TSC
    # seconds of the window falling in the band
    ov = sum(1 for x in range(int(a), int(b)) if int(x % 60) in band)
    rows.append((tps[d], d, ov, b - a))
rows.sort(reverse=True)
for t, d, ov, span in rows:
    print(f"  {d} tps {t:7.2f}  window {span:5.1f}s  overlap-with-burst {ov:4.1f}s")
xs = [r[0] for r in rows]; ys = [r[2] for r in rows]
mx, my = st.mean(xs), st.mean(ys)
sx = sum((x-mx)**2 for x in xs)**.5; sy = sum((y-my)**2 for y in ys)**.5
print(f"corr(TPS, burst-overlap-seconds) = {sum((a-mx)*(b-my) for a,b in zip(xs,ys))/(sx*sy):+.2f}" if sx*sy else "n/a")
