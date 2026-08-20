#!/usr/bin/env python3
"""Per boundary gap: relate the fill window [f0,f0+fd] to wcls ring events.
Outputs per-step means: fill_before_lastrx (overlap with in-flight job),
fill_after_lastrx (fill continuing after last wcls completion),
lastrx_to_fillend sign stats."""
import struct, sys, bisect

raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
attn = []; fills = []; rx = []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    if tag == 0: attn.append((t0, "q0"))
    elif tag == 2035: attn.append((t0 + dur, "b35"))
    elif tag == 7000: fills.append((t0, dur))
    elif 4000 <= tag < 5000: rx.append(t0)
attn.sort(); fills.sort(); rx.sort()
fstarts = [f[0] for f in fills]
before = after = 0; nb = 0
last_b35 = None
for t, kind in attn:
    if kind == "q0":
        if last_b35 is not None and 0 < t - last_b35 < 50_000_000:
            i = bisect.bisect_left(fstarts, last_b35)
            if i < len(fills) and fills[i][0] < t:
                f0, fd = fills[i]
                fe = f0 + fd
                j = bisect.bisect_left(rx, fe)
                # last rx completion within this gap before fill end
                j2 = bisect.bisect_left(rx, last_b35)
                last_rx = rx[j-1] if j-1 >= j2 else last_b35
                b = max(0, min(last_rx, fe) - f0)
                a = max(0, fe - max(last_rx, f0))
                before += b; after += a; nb += 1
        last_b35 = None
    else:
        last_b35 = t
print(f"{nb},{before/max(nb,1):.0f},{after/max(nb,1):.0f}")
