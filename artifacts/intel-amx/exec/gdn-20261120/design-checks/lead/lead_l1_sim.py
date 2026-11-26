#!/usr/bin/env python3
"""Lead designer: L1 data cache model for the two GDN prefill paths.

Model: 48 KiB, 12 ways, 64-byte lines = 64 sets, LRU, no prefetcher, no L2.
It counts lines that must come from outside L1. It is a model, not a
measurement: the real core has prefetchers and a 2 MiB L2 behind L1.
"""
from collections import OrderedDict

SETS, WAYS = 64, 12


class L1:
    def __init__(self):
        self.sets = [OrderedDict() for _ in range(SETS)]
        self.miss = 0
        self.by = {}

    def touch(self, line, tag="other"):
        s = self.sets[line % SETS]
        if line in s:
            s.move_to_end(line)
            return True
        self.miss += 1
        self.by[tag] = self.by.get(tag, 0) + 1
        s[line] = True
        if len(s) > WAYS:
            s.popitem(last=False)
        return False


ROWS = 128
STATE = 0                 # line address of one value head's state (1024 lines)
INPUTS = 1 << 20
SCRATCH = 2 << 20


def blocked(vb, row):     # layout [value block][key row][16 columns]: 1 line per row
    return STATE + vb * ROWS + row


def standard(row, chunk):  # layout [key row][128 columns]: 8 lines per row
    return STATE + row * 8 + chunk


def token_inputs(c, t, slice_ix=None):
    base = INPUTS + t * 64
    for l in range(16):                      # k and q rows of the token (FP32)
        c.touch(base + l, "inputs")
    cols = range(8) if slice_ix is None else range(slice_ix * 4, slice_ix * 4 + 4)
    for l in cols:                           # v row and o row of this value head
        c.touch(base + 16 + l, "inputs")
        c.touch(base + 24 + l, "inputs")


def sim_token_loop(tokens):
    c = L1()
    for t in range(tokens):
        token_inputs(c, t)
        for _ in range(2):
            for r in range(ROWS):
                for k in range(8):
                    c.touch(standard(r, k), "state")
    return c


def sim_slice(tokens, window, layout):
    """64-column slices; all tokens of a window on one slice, then the next slice."""
    c = L1()
    for w0 in range(0, tokens, window):
        for s in range(2):
            for t in range(w0, min(w0 + window, tokens)):
                token_inputs(c, t, s)
                for _ in range(2):           # loop 1, loop 2
                    for r in range(ROWS):
                        for k in range(4):
                            if layout == "blocked":
                                c.touch(blocked(4 * s + k, r), "state")
                            else:
                                c.touch(standard(r, 4 * s + k), "state")
    return c


def sim_p1(C, pieces_packed=True):
    """[K;Q] x S0 for one value head: per value block, split into an L1 scratch, then tile products."""
    c = L1()
    loads = hits = 0
    kq_base = SCRATCH                        # bf16 rows [2C][128]: 4 lines per row
    split_base = SCRATCH + (1 << 16)         # 12 tiles x 16 lines, reused for every value block
    out_base = SCRATCH + (2 << 16)           # R0/Q0 [2C][128] FP32: 8 lines per row
    rb = 2 * C // 16
    for vb in range(8):
        for r in range(ROWS):
            c.touch(blocked(vb, r), "state")
        for l in range(12 * 16):
            c.touch(split_base + l, "split scratch write")
        for g in range(0, rb, 4):
            for kb in range(4):
                for p in range(3):
                    for l in range(16):
                        loads += 1
                        hits += c.touch(split_base + (kb * 3 + p) * 16 + l, "B tile load")
                for r in range(g, min(g + 4, rb)):
                    for row in range(16):    # A tile: 16 token rows, 64 bytes each, 256-byte stride
                        loads += 1
                        hits += c.touch(kq_base + (r * 16 + row) * 4 + kb, "A tile load")
            for r in range(g, min(g + 4, rb)):
                for row in range(16):
                    c.touch(out_base + (r * 16 + row) * 8 + vb, "R0/Q0 store")
    return c, loads, hits


def sim_update(C, layout):
    """Form Y: T = K^T x W from zero, stored to a 4 KiB scratch; then S = fma(G_C, S, T) with AVX-512."""
    c = L1()
    loads = hits = 0
    w_base = SCRATCH                         # tile-packed [vb][token block][piece]: 16 lines per tile
    kt_base = SCRATCH + (1 << 16)            # tile-packed [key-row block][token block]
    t_base = SCRATCH + (2 << 16)             # 4 result tiles, reused
    tb = -(-C // 32)

    def s_line(vb, row):
        return blocked(vb, row) if layout == "blocked" else standard(row, vb)

    for vb in range(8):
        for g in range(2):
            for t in range(tb):
                for p in range(3):
                    for l in range(16):
                        loads += 1
                        hits += c.touch(w_base + ((vb * tb + t) * 3 + p) * 16 + l, "W tile load")
                for kr in range(g * 4, g * 4 + 4):
                    for l in range(16):
                        loads += 1
                        hits += c.touch(kt_base + (kr * tb + t) * 16 + l, "K^T tile load")
            for l in range(64):              # tile stores into the scratch
                c.touch(t_base + l, "T scratch")
            for r in range(g * 64, g * 64 + 64):   # AVX: S = fma(G_C, S, T)
                c.touch(t_base + (r - g * 64), "T scratch")
                c.touch(s_line(vb, r), "state")
    return c, loads, hits


if __name__ == "__main__":
    T = 128
    print("L1 model: 64 sets x 12 ways x 64 B = 48 KiB, LRU, no prefetcher")
    print("\nA. token paths, one value head, chain of 128 tokens: lines from outside L1 per token")
    c = sim_token_loop(T)
    print(f"   token loop today (standard layout)           state {c.by.get('state', 0) / T:7.1f}   inputs {c.by.get('inputs', 0) / T:5.1f}")
    for layout in ("standard", "blocked"):
        for window in (32, 128):
            c = sim_slice(T, window, layout)
            print(f"   slice replay, {layout:8s} layout, window {window:3d}    state {c.by.get('state', 0) / T:7.1f}   inputs {c.by.get('inputs', 0) / T:5.1f}")
    print("\nB. AMX block, P1 = [K;Q] x S0, one value head: tile-load lines found in L1")
    for C in (32, 64):
        c, loads, hits = sim_p1(C)
        print(f"   C = {C}: {hits} of {loads} tile-load lines in L1 ({hits / loads * 100:.1f} %); misses by kind {dict(sorted(c.by.items()))}")
    print("\nC. AMX block, update T = K^T x W then S = fma(G_C, S, T), one value head: tile-load lines found in L1")
    for layout in ("standard", "blocked"):
        for C in (32, 64):
            c, loads, hits = sim_update(C, layout)
            print(f"   {layout:8s} layout, C = {C}: {hits} of {loads} lines in L1 ({hits / loads * 100:.1f} %); misses by kind {dict(sorted(c.by.items()))}")
