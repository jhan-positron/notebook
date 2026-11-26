#!/usr/bin/env python3
"""Independent checks for the code-fit verifier.
[1] L1 model (64 sets x 12 ways, LRU): state lines fetched from outside L1 per
    token per value head, token loop vs slice replay, standard vs blocked layout.
[2] Share of a chain's tokens that fall into full 32-token blocks on an
    absolute grid, as a function of the chain's start height.
[3] Tile-instruction counts of the 128x4 kernel (walk of the loops in
    amx_attn.cpp) and of the same loops at width 256.
[4] Scratch and working-set byte counts from the struct at
    gdn_rolling_executor.hpp:189-211.
"""
from collections import OrderedDict

LINE = 64
class L1:
    def __init__(self, sets=64, ways=12):
        self.sets = [OrderedDict() for _ in range(sets)]
        self.nsets, self.ways = sets, ways
        self.miss = {}
    def touch(self, addr, nbytes, kind):
        first, last = addr // LINE, (addr + nbytes - 1) // LINE
        for ln in range(first, last + 1):
            s = self.sets[ln % self.nsets]
            if ln in s:
                s.move_to_end(ln)
            else:
                self.miss[kind] = self.miss.get(kind, 0) + 1
                s[ln] = True
                if len(s) > self.ways:
                    s.popitem(last=False)

ROWS = COLS = 128
def state_addr(layout, base, i, c):
    if layout == "standard":            # [key row][value column]
        return base + (i * COLS + c) * 4
    vb, c16 = divmod(c, 16)             # [value block][key row][16 columns]
    return base + ((vb * ROWS + i) * 16 + c16) * 4

def run(layout, mode, window, n_tokens=128):
    c = L1()
    S = 0x10000000
    K = 0x20000040; Q = 0x30000080; V = 0x400000c0; O = 0x50000100   # one row of 512 B per token
    def loops(t, cols):
        for i in range(ROWS):                               # loop 1
            c.touch(K + t * 512 + i * 4, 4, "input")
            for c0 in cols:
                c.touch(state_addr(layout, S, i, c0), 64, "state")
        for c0 in cols:
            c.touch(V + t * 512 + c0 * 4, 64, "input")
        for i in range(ROWS):                               # loop 2
            c.touch(K + t * 512 + i * 4, 4, "input")
            c.touch(Q + t * 512 + i * 4, 4, "input")
            for c0 in cols:
                c.touch(state_addr(layout, S, i, c0), 64, "state")
        for c0 in cols:
            c.touch(O + t * 512 + c0 * 4, 64, "input")
    if mode == "token":
        for t in range(n_tokens):
            loops(t, range(0, COLS, 16))
    else:
        for w0 in range(0, n_tokens, window):
            for sl in range(2):
                cols = range(sl * 64, sl * 64 + 64, 16)
                for t in range(w0, min(w0 + window, n_tokens)):
                    loops(t, cols)
    return c.miss.get("state", 0) / n_tokens, c.miss.get("input", 0) / n_tokens

print("[1] L1 model, lines from outside L1 per token per value head (state, inputs)")
for layout, mode, window in (("standard", "token", 0), ("standard", "slice", 32),
                             ("blocked", "slice", 32), ("blocked", "slice", 128)):
    s, i = run(layout, mode, window)
    print(f"    {mode:5s} {layout:8s} window {window:3d}: state {s:7.1f}  inputs {i:5.1f}")

print("[2] tokens of a 128-token chain inside full blocks of an absolute 32-token grid")
def covered(start, length, C=32):
    first = -(-start // C) * C
    end = start + length
    return max(0, (end - first) // C) * C if first <= end else 0
tot = 0
for s in range(32):
    tot += covered(s, 128)
print("    start on the grid (s=0):", covered(0, 128), "of 128")
print("    start off the grid (s=1..31):", sorted({covered(s, 128) for s in range(1, 32)}), "of 128")
print(f"    mean over the 32 start offsets: {tot/32:.2f} of 128 = {100*tot/32/128:.1f} % in blocks,"
      f" {100 - 100*tot/32/128:.1f} % on the slice replay")
for L in (2, 8, 31, 40, 63, 100):
    m = sum(covered(s, L) for s in range(32)) / 32
    print(f"    chain of {L:3d} tokens: mean {m:5.1f} tokens in blocks ({100*m/L:4.1f} %)")

print("[3] tile instruction counts per (query token, page, KV head)")
def attn_counts(width):
    steps = width // 32
    qk = dict(tdp=steps * 4, loads=steps * (1 + 4), stores=4)
    groups = width // 64
    pv = dict(tdp=groups * 2 * 4, loads=groups * 2 * (1 + 4), stores=groups * 4)
    return qk, pv
for w in (128, 256):
    qk, pv = attn_counts(w)
    tot = {k: qk[k] + pv[k] for k in qk}
    cyc = tot["tdp"] * 16.2 + tot["loads"] * 8.4 + tot["stores"] * 16.1
    avx = (64 * 4 * (w // 32)) + (4 * 32 * (w // 16))
    print(f"    width {w}: QK {qk}  PV {pv}  total {tot}  = {cyc:.0f} cycles (est., L1);"
          f" AVX-512 VDPBF16PS {avx} = {avx*2.0:.0f} cycles (est.); ratio {avx*2.0/cyc:.2f}")
print("    bytes per visit at width 256: K block", 64*256*2, " V block", 64*256*2,
      " packed Q", 16*256*2, " PV store target", 16*256*4, " (real rows", 4*256*4, ")")
print("    bytes per visit at width 128: K block", 64*128*2, " V block", 64*128*2,
      " packed Q", 16*128*2, " PV store target", 16*128*4)

print("[4] working_set of gdn_rolling_head_executor at 16 key heads x 128, 32 value heads x 128")
state_copy = 2 * 128 * 128 * 4
hist_copy = 8192 * 3 * 4
conv_qkv = 512 * 4
rec_out = 256 * 4
chunk_map = (512 // 16) * 8
ptrs = 5 * 8
print("    recurrent_state_copy", state_copy, " convolution_history_copy", hist_copy,
      " convolution_qkv", conv_qkv, " recurrence_output", rec_out, " source_chunks", chunk_map,
      " pointers+group", ptrs)
print("    sum without pointers", state_copy + hist_copy + conv_qkv + rec_out + chunk_map,
      " with pointers", state_copy + hist_copy + conv_qkv + rec_out + chunk_map + ptrs)
print("    history bytes that one group really uses:", 512 * 3 * 4)
g1 = 32768 + 65536 + 131072
g2 = 16384 + 8192 + 32768 + 24576 + 12288 + 16384
print("    spec scratch: G1 adds", g1, " G2 adds", g2, " sum of additions", g1 + g2,
      " with today's 232,704:", g1 + g2 + 232704)
print("    I2 rows: 16 GDN workers x 24 operations x 64 B =", 16 * 24 * 64, " (spec: 56 x 24 x 64 =", 56*24*64, ")")
