#!/usr/bin/env python3
"""Per-gap dead time: gap duration minus union of in-flight [tx_i, rx_i] intervals
(FIFO pairing per card, union across all 4 cards). Also covered time."""
import struct, sys, bisect

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn = []; tx = {}; rx = {}
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    s = int(tag) // 1000
    if s == 0 or tag < 1000: attn.append((t0, 0))
    elif s == 2: attn.append((t0 + dur, 2))
    elif s == 3: tx.setdefault(tag - 3000, []).append(t0)
    elif s == 4: rx.setdefault(tag - 4000, []).append(t0)
attn.sort()
# FIFO-paired intervals per card, merged into one sorted list
ivals = []
for c in set(tx) & set(rx):
    a, b = sorted(tx[c]), sorted(rx[c])
    m = min(len(a), len(b))
    for i in range(m):
        if b[i] > a[i]: ivals.append((a[i], b[i]))
ivals.sort()
starts = [iv[0] for iv in ivals]

def covered(gs, ge):
    i = bisect.bisect_left(starts, gs) 
    # step back: an interval starting before gs may overlap
    if i > 0 and ivals[i-1][1] > gs: i -= 1
    cov = 0; cur = gs
    while i < len(ivals) and ivals[i][0] < ge:
        s0, e0 = ivals[i]
        s0 = max(s0, cur); e0 = min(e0, ge)
        if e0 > s0:
            cov += e0 - s0; cur = e0
        i += 1
    return cov

dead = cov_tot = gtot = 0; ngap = 0
last_be = None
for t, kind in attn:
    if kind == 0:
        if last_be is not None and 0 < t - last_be < 50_000_000:
            c = covered(last_be, t)
            g = t - last_be
            dead += g - c; cov_tot += c; gtot += g; ngap += 1
        last_be = None
    else:
        last_be = t
steps = max(1, ngap / 36)
print(f"{ngap},{dead/steps:.0f},{cov_tot/steps:.0f},{gtot/steps:.0f}")
