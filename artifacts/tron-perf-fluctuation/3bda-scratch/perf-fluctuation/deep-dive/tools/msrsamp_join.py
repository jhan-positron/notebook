#!/usr/bin/env python3
"""Join the 150us MSR sampler stream with kvwait fill spans (tag 7000).

For each draw:
  - classify fill spans: stalled (dur > 2x median) vs quick
  - for samples inside each class of span, and for a control slice taken
    3.5..0.5 ms BEFORE each stalled span (mid forward pass), report:
      eff_ghz : mean effective frequency  = dAPERF/dMPERF * base_ghz
      c0_frac : mean C0 residency         = dMPERF/dTSC
      watts   : package power from dENERGY/dt
      coreC/pkgC : temperatures
Usage: msrsamp_join.py <campaign_root> [base_ghz=2.7] [unit_uj=61.0]
"""
import glob, os, struct, sys
import statistics as st

ROOT = sys.argv[1]
BASE = float(sys.argv[2]) if len(sys.argv) > 2 else 2.7
UNIT = float(sys.argv[3]) if len(sys.argv) > 3 else 61.0  # uJ per energy count
TJMAX = 107
REC = struct.Struct("<QQQIQQIII")


def load_samples(path):
    data = open(path, "rb").read()
    out = []
    for i in range(0, len(data) - REC.size + 1, REC.size):
        out.append(REC.unpack_from(data, i))
    return out


def load_fills(path):
    # kvwait records after the u64 count header: u64 t0, u64 dur, u64 tag
    data = open(path, "rb").read()
    n = struct.unpack_from("<Q", data, 0)[0]
    fills = []
    off = 8
    for _ in range(n):
        t0, dur, tag = struct.unpack_from("<QQQ", data, off)
        off += 24
        if tag == 7000:
            fills.append((t0, dur))
    return fills


def slice_stats(samples, lo, hi):
    # consecutive-pair deltas fully inside [lo, hi]
    da = dm = dt = de = 0
    temps_c = []
    temps_p = []
    prev = None
    for s in samples:
        if s[0] < lo:
            prev = s
            continue
        if s[0] > hi:
            break
        if prev is not None and prev[0] >= lo:
            da += s[1] - prev[1]
            dm += s[2] - prev[2]
            dt += s[0] - prev[0]
            de += (s[7] - prev[7]) & 0xFFFFFFFF
        temps_c.append(TJMAX - ((s[3] >> 16) & 0x7F))
        temps_p.append(TJMAX - ((s[8] >> 16) & 0x7F))
        prev = s
    if dt == 0 or dm == 0:
        return None
    return (da / dm * BASE, dm / dt, de * UNIT * 1e-6 / (dt / (BASE * 1e9)),
            st.mean(temps_c), st.mean(temps_p))


def bisect_left(samples, t):
    lo, hi = 0, len(samples)
    while lo < hi:
        mid = (lo + hi) // 2
        if samples[mid][0] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo


print(f"{'draw':8} {'class':8} {'n':>5} {'eff_ghz':>8} {'c0_frac':>8} {'watts':>7} {'coreC':>6} {'pkgC':>6}")
for d in sorted(glob.glob(os.path.join(ROOT, "results", "draw_*"))):
    name = os.path.basename(d)
    mfile, kfile = os.path.join(d, "msrsamp.bin"), os.path.join(d, "kvwait.bin")
    if not (os.path.exists(mfile) and os.path.exists(kfile)):
        continue
    samples = load_samples(mfile)
    fills = load_fills(kfile)
    if not samples or not fills:
        continue
    med = st.median(f[1] for f in fills)
    classes = {"stalled": [], "quick": [], "control": []}
    for t0, dur in fills:
        cls = "stalled" if dur > 2 * med else "quick"
        classes[cls].append((t0, t0 + dur))
        if cls == "stalled":
            classes["control"].append((t0 - int(3.5e-3 * BASE * 1e9), t0 - int(0.5e-3 * BASE * 1e9)))
    for cls in ("stalled", "quick", "control"):
        acc = []
        for lo, hi in classes[cls]:
            i = bisect_left(samples, lo)
            r = slice_stats(samples[max(0, i - 1):i + 40], lo, hi)
            if r:
                acc.append(r)
        if acc:
            cols = [st.mean([a[k] for a in acc]) for k in range(5)]
            print(f"{name:8} {cls:8} {len(acc):5d} {cols[0]:8.2f} {cols[1]:8.3f} {cols[2]:7.0f} {cols[3]:6.1f} {cols[4]:6.1f}")
