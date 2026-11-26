#!/usr/bin/env python3
"""Verifier (cost lens): L1 model re-run with my own code and with shifted buffer placements.

Model: 48 KiB, 12 ways, 64 sets, LRU, no prefetcher (same model class as the lead's lead_l1_sim.py).
Questions:
  1. Slice replay (G1): lines from outside L1 per token per value head, for both layouts.
  2. Is the result robust when the scratch buffers start at other set offsets?
  3. P1 of the AMX block (G2): which lines miss, and why. Does a blocked R0/U0 store layout help?
A model, not a measurement.
"""
import random
from collections import OrderedDict

SETS, WAYS = 64, 12


class L1:
    def __init__(self):
        self.s = [OrderedDict() for _ in range(SETS)]
        self.miss = {}

    def touch(self, line, tag):
        st = self.s[line % SETS]
        if line in st:
            st.move_to_end(line)
            return True
        self.miss[tag] = self.miss.get(tag, 0) + 1
        st[line] = 1
        if len(st) > WAYS:
            st.popitem(last=False)
        return False


def slice_replay(tokens, window, layout, off_state=0, off_in=0, block_lines=128):
    c = L1()
    ST, IN = (1 << 22) + off_state, (2 << 22) + off_in
    for w0 in range(0, tokens, window):
        for s in range(2):
            for t in range(w0, min(w0 + window, tokens)):
                base = IN + t * 64
                for l in range(16):
                    c.touch(base + l, "inputs")            # k_t and q_t x scale rows (2 x 512 B)
                for l in range(s * 4, s * 4 + 4):
                    c.touch(base + 16 + l, "inputs")       # v_t slice
                    c.touch(base + 24 + l, "inputs")       # o_t slice
                for _pass in range(2):
                    for r in range(128):
                        for k in range(4):
                            if layout == "blocked":
                                c.touch(ST + (4 * s + k) * block_lines + r, "state")
                            else:
                                c.touch(ST + r * 8 + 4 * s + k, "state")
    return c


def p1(C, out_blocked, off=(0, 0, 0, 0)):
    """[K;Q] x S0 for one value head; split per value block into a 12 KiB scratch; loop order of tile_mapping."""
    c = L1()
    ST, KQ, SP, OUT = (1 << 22) + off[0], (2 << 22) + off[1], (3 << 22) + off[2], (4 << 22) + off[3]
    rb = 2 * C // 16
    loads = hits = 0
    for vb in range(8):
        for r in range(128):
            c.touch(ST + vb * 128 + r, "state read by the split")
        for l in range(192):
            c.touch(SP + l, "split scratch write")
        for g in range(0, rb, 4):
            for kb in range(4):
                for p in range(3):
                    for l in range(16):
                        loads += 1
                        hits += c.touch(SP + (kb * 3 + p) * 16 + l, "B tile load")
                for r in range(g, min(g + 4, rb)):
                    for row in range(16):
                        loads += 1
                        hits += c.touch(KQ + (r * 16 + row) * 4 + kb, "A tile load")
            for r in range(g, min(g + 4, rb)):
                for row in range(16):
                    if out_blocked:
                        c.touch(OUT + vb * 2 * C + r * 16 + row, "R0/U0 store")       # [value block][token][16]
                    else:
                        c.touch(OUT + (r * 16 + row) * 8 + vb, "R0/U0 store")         # [token][128], 512-byte stride
    return c, loads, hits


if __name__ == "__main__":
    T = 128
    print("1. SLICE REPLAY (G1), one value head, chain of 128 tokens: lines from outside L1 per token")
    for layout in ("standard", "blocked"):
        for window in (32, 128):
            c = slice_replay(T, window, layout)
            print(f"   {layout:8s} layout, window {window:3d}: state {c.miss.get('state', 0) / T:7.1f}  inputs {c.miss.get('inputs', 0) / T:5.1f}")
    print("   (lead: 2,048 state lines with the standard layout; 32 and 8 with the blocked layout; inputs 48)")

    random.seed(7)
    worst = 0
    for trial in range(200):
        c = slice_replay(T, 32, "blocked", random.randrange(64), random.randrange(64))
        worst = max(worst, c.miss.get("state", 0) / T)
    print(f"2. blocked layout, window 32, 200 random placements of state and inputs: worst state lines per token = {worst:.1f}")
    c = slice_replay(T, 32, "blocked", block_lines=129)
    print(f"   blocked layout with a 129-line block stride (no 4 KiB aliasing between the chunks of one key row): state {c.miss.get('state', 0) / T:.1f}")

    print("3. AMX BLOCK P1 (G2), one value head: tile-load lines found in L1")
    for C in (32, 64):
        for ob in (False, True):
            c, loads, hits = p1(C, ob)
            print(f"   C = {C}, R0/U0 stored {'blocked by value block' if ob else 'as [token][128] rows  '}:"
                  f" {hits} of {loads} tile-load lines in L1 ({100 * hits / loads:.1f} %); misses {dict(sorted(c.miss.items()))}")
    lo, hi = 101.0, 0.0
    for trial in range(200):
        off = tuple(random.randrange(64) for _ in range(4))
        c, loads, hits = p1(32, False, off)
        lo, hi = min(lo, 100 * hits / loads), max(hi, 100 * hits / loads)
    print(f"   C = 32, [token][128] rows, 200 random placements: {lo:.1f} % to {hi:.1f} % of tile-load lines in L1 (lead: 86.6 %)")
    print("   Reason for the A-tile misses at C = 32: a tile store into [token][128] rows has a 512-byte row stride,")
    print("   so the 64 lines of one value block fall into 8 of the 64 L1 sets (8 lines per set, 12 ways).")
    print("   State lines per block that no layout avoids: 1,024 read by the split + 1,024 read and written by the final fma.")
