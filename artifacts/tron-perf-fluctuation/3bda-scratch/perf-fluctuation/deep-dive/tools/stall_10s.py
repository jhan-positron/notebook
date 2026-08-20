#!/usr/bin/env python3
"""Per-draw: stall count/mass + Rayleigh test at candidate periods."""
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
stalls = [(t, d) for t, d in fills if d > 2 * med]
out = [str(len(stalls)), f"{100*sum(d for _,d in stalls)/max(sum(durs),1):.1f}"]
for period in (1.0, 5.0, 10.0, 30.0, 60.0):
    if len(stalls) >= 5:
        xs = [math.cos(2*math.pi*((t/TSC) % period)/period) for t,_ in stalls]
        ys = [math.sin(2*math.pi*((t/TSC) % period)/period) for t,_ in stalls]
        R = math.hypot(st.mean(xs), st.mean(ys))
        z = len(stalls)*R*R
        out.append(f"{R:.3f}/{z:.0f}")
    else:
        out.append("-")
print(",".join(out))
