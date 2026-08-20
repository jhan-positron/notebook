#!/usr/bin/env python3
"""Timing forensics on fill (tag 7000) stall events.
Stall = fill duration > 2x median. Reports: count, rate, inter-arrival stats
(wall seconds), top inter-arrival clusters, and phase concentration vs 1s/10s
periods (circular concentration R: 1.0 = perfectly periodic at that period)."""
import struct, sys, math, statistics as st
TSC = 2.7e9
raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
fills = []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    if tag == 7000: fills.append((t0, dur))
fills.sort()
durs = [d for _, d in fills]
med = st.median(durs)
thr = 2 * med
stalls = [(t, d) for t, d in fills if d > thr]
print(f"fills={len(fills)} median={med:,.0f} thr={thr:,.0f} stalls={len(stalls)} ({100*len(stalls)/len(fills):.1f}%) stall_mass={sum(d for _,d in stalls)/max(sum(durs),1)*100:.1f}% of fill time")
if len(stalls) < 5:
    sys.exit(0)
t0s = [t for t, _ in stalls]
ia = [(b - a) / TSC for a, b in zip(t0s, t0s[1:])]
ia_s = sorted(ia)
print(f"inter-arrival s: median {ia_s[len(ia_s)//2]:.3f}  p10 {ia_s[int(0.1*len(ia_s))]:.3f}  p90 {ia_s[int(0.9*len(ia_s))]:.3f}")
for period in (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0):
    # circular concentration of stall times modulo the period
    xs = [math.cos(2*math.pi*((t/TSC) % period)/period) for t in t0s]
    ys = [math.sin(2*math.pi*((t/TSC) % period)/period) for t in t0s]
    R = math.hypot(st.mean(xs), st.mean(ys))
    print(f"  period {period:5.2f}s  concentration R={R:.3f}")
