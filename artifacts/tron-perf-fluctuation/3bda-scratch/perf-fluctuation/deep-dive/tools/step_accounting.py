#!/usr/bin/env python3
"""Full step accounting from worker-0 stamps (all layers):
in_attention = sum over ops of (q_wait_start -> barrier_end)
gap(L) = barrier_end(L) -> q_wait_start(L+1 or next step's 0)
Outputs per step means: boundary_gap(L35), other_gaps_total, in_attention_total."""
import struct, sys
raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
ev = []
for i in range(n):
    t0, dur, tag = struct.unpack_from("<QQQ", raw, 8+24*i)
    if tag < 1000: ev.append((t0, 0, int(tag)))            # q-wait start, layer
    elif 2000 <= tag < 3000: ev.append((t0+dur, 1, int(tag)-2000))  # barrier end, layer
ev.sort()
boundary = other = attn = 0; nsteps = 0
prev = None  # (time, kind, layer)
for t, kind, layer in ev:
    if prev is not None:
        dt = t - prev[0]
        if 0 < dt < 50_000_000:
            if prev[1] == 0 and kind == 1 and prev[2] == layer:
                attn += dt                       # inside op: q start -> barrier end
            elif prev[1] == 1 and kind == 0:
                if prev[2] == 35 and layer == 0:
                    boundary += dt; nsteps += 1  # step boundary gap
                elif layer == prev[2] + 1:
                    other += dt                  # per-layer gap
    prev = (t, kind, layer)
print(f"{nsteps},{boundary/max(nsteps,1):.0f},{other/max(nsteps,1):.0f},{attn/max(nsteps,1):.0f}")
