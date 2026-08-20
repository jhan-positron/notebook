#!/usr/bin/env python3
"""Per-card (per-TP-tile) block-arrival attribution from kvwait 7500+ix stamps.

The 7500 stamp lives in the per-tile stream_result_t::try_consume with the
TILE-LOCAL block index; the ptensor wrapper sweeps tiles 0..3 in fixed order
each poll pass. Decode: each tile's index sequence increments 0..k; walk the
stamps assigning each to the cyclically-next tile whose expected index matches.

Per fill: per-tile last-arrival offset (us from fill start), block count.
Per draw: mean per-tile last-offset, laggard-tile histogram.
Usage: percard_arrival.py <campaign_root> [ntiles=4]
"""
import glob, os, struct, sys
import statistics as st

ROOT = sys.argv[1]
NT = int(sys.argv[2]) if len(sys.argv) > 2 else 4
TSC = 2.7e3  # ticks per us

def analyze(path):
    raw = open(path, "rb").read()
    n = struct.unpack_from("<Q", raw, 0)[0]
    recs = []
    for i in range(n):
        t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
        recs.append((t0, dur, tag))
    recs.sort()
    fills = [(t0, dur) for t0, dur, tag in recs if tag == 7000]
    stamps = [(t0, tag - 7500) for t0, dur, tag in recs if 7500 <= tag < 7756]
    si = 0
    per_tile_last = [[] for _ in range(NT)]  # us offsets, per fill
    laggard = [0] * NT
    bad = 0
    for ft, fd in fills:
        fe = ft + fd
        while si < len(stamps) and stamps[si][0] < ft:
            si += 1
        j = si
        seq = []
        while j < len(stamps) and stamps[j][0] <= fe:
            seq.append(stamps[j]); j += 1
        si = j
        if len(seq) < NT * 2:
            continue
        nxt = [0] * NT
        cur = 0
        last = [None] * NT
        ok = True
        for t, v in seq:
            for k in range(NT):
                cand = (cur + k) % NT
                if nxt[cand] == v:
                    cur = cand
                    nxt[cand] += 1
                    last[cand] = t
                    break
            else:
                ok = False
                break
        if not ok or any(l is None for l in last):
            bad += 1
            continue
        offs = [(l - ft) / TSC for l in last]
        for k in range(NT):
            per_tile_last[k].append(offs[k])
        laggard[offs.index(max(offs))] += 1
    return per_tile_last, laggard, len(fills), bad

results = []
for d in sorted(glob.glob(os.path.join(ROOT, "results", "draw_*"))):
    f = os.path.join(d, "kvwait.bin")
    if not os.path.exists(f):
        continue
    ptl, lag, nfills, bad = analyze(f)
    if not ptl[0]:
        continue
    name = os.path.basename(d)
    means = [st.mean(x) for x in ptl]
    results.append((name, nfills, bad, means, lag))

print(f"{'draw':10} {'fills':>6} {'undec':>6} | last-arrival mean us per tile 0..3 | laggard% per tile")
for name, nf, bad, means, lag in results:
    tot = sum(lag) or 1
    m = " ".join(f"{x:7.1f}" for x in means)
    l = " ".join(f"{100*x/tot:4.0f}" for x in lag)
    print(f"{name:10} {nf:6d} {bad:6d} | {m} | {l}")
