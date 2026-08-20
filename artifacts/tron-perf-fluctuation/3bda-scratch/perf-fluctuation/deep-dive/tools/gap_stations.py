#!/usr/bin/env python3
"""Split each inter-attention gap into stations using probe-v3 records.

Tags: 0xx Q-wait (t0=start,dur=wait), 1xxx KV latch, 2xxx barrier,
3xxx tx_launch instant, 4xxx rx completion instant.
Stations per gap [barrier_end -> next q_start]:
  A = first_tx - gap_start (host dispatch lag)
  B = last_rx - first_tx   (card execute + DMA window)
  C = gap_end - last_rx    (completion -> release lag)
Usage: gap_stations.py <kvwait.bin>  -> one CSV line: sums per step
"""
import struct, sys, bisect

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn, tx, rx = [], [], []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    s = int(tag) // 1000
    if s == 0 or tag < 1000:
        attn.append((t0, dur, 0, tag))
    elif s == 2:
        attn.append((t0, dur, 2, tag - 2000))
    elif s == 3:
        tx.append(t0)
    elif s == 4:
        rx.append(t0)
attn.sort(); tx.sort(); rx.sort()
A = B = C = G = 0
ngap = 0
last_barrier_end = None
for t0, dur, kind, layer in attn:
    if kind == 0:
        if last_barrier_end is not None:
            gs, ge = last_barrier_end, t0
            g = ge - gs
            if 0 < g < 50_000_000:
                i1 = bisect.bisect_left(tx, gs); i2 = bisect.bisect_left(tx, ge)
                j1 = bisect.bisect_left(rx, gs); j2 = bisect.bisect_left(rx, ge)
                if i2 > i1 and j2 > j1:
                    ft, lr = tx[i1], rx[j2 - 1]
                    if gs <= ft <= ge and gs <= lr <= ge and ft <= lr:
                        A += ft - gs; B += lr - ft; C += ge - lr; G += g
                        ngap += 1
        last_barrier_end = None
    else:
        last_barrier_end = t0 + dur
steps = max(1, ngap / 36)
print(f"{ngap},{A/steps:.0f},{B/steps:.0f},{C/steps:.0f},{G/steps:.0f}")
