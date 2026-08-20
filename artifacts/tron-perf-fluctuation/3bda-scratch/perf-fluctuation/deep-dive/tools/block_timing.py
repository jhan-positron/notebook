#!/usr/bin/env python3
"""Per-block stream-consume timing inside each fill (tags 7500+).
Per draw: blocks/fill, and the split of fill time into:
  pre_first  = fill start -> first block consumed
  interblock = sum of gaps between consecutive block consumes
  tail       = last block consumed -> fill end (patch/finish work)
Arrival-limited fills show large pre_first/interblock; consumer-limited show
tight bursts with small gaps."""
import struct, sys, bisect, statistics as st
raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
fills = []; blocks = []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    if tag == 7000: fills.append((t0, dur))
    elif 7500 <= tag < 7800: blocks.append(t0)
fills.sort(); blocks.sort()
pre = inter = tail = 0; nb = 0; bc = []
for f0, fd in fills:
    fe = f0 + fd
    i = bisect.bisect_left(blocks, f0)
    j = bisect.bisect_left(blocks, fe)
    bs = blocks[i:j]
    if len(bs) < 2: continue
    pre += bs[0] - f0
    inter += bs[-1] - bs[0] - 0  # total span between first and last consume
    tail += fe - bs[-1]
    bc.append(len(bs)); nb += 1
print(f"{nb},{st.mean(bc):.0f},{pre/max(nb,1):.0f},{inter/max(nb,1):.0f},{tail/max(nb,1):.0f}")
