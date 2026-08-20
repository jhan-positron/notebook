#!/usr/bin/env python3
"""Split the layer-35 boundary gap using site-7000 (fill_logits_buffer) records:
A_pre = barrier-exit(L35) -> fill start; B_fill = fill duration (incl sentinel);
C_post = fill end -> next step's first Q-wait start. Cycles/step means."""
import struct, sys, bisect

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn = []; fills = []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    if tag < 1000:
        if tag == 0: attn.append((t0, "q0"))
    elif 2000 <= tag < 3000:
        if tag == 2035: attn.append((t0 + dur, "b35"))
    elif tag == 7000:
        fills.append((t0, dur))
attn.sort(); fills.sort()
fstarts = [f[0] for f in fills]
A = B = C = 0; nb = 0
last_b35 = None
for t, kind in attn:
    if kind == "q0":
        if last_b35 is not None and 0 < t - last_b35 < 50_000_000:
            i = bisect.bisect_left(fstarts, last_b35)
            if i < len(fills) and fills[i][0] < t:
                f0, fd = fills[i]
                A += f0 - last_b35; B += fd; C += t - (f0 + fd); nb += 1
        last_b35 = None
    else:
        last_b35 = t
print(f"{nb},{A/max(nb,1):.0f},{B/max(nb,1):.0f},{C/max(nb,1):.0f}")
