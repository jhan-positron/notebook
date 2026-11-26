#!/usr/bin/env python3
"""L1 data cache simulation for the GDN recurrence loop orders and state layouts.

Model: L1d = 48 KiB, 12 ways, 64-byte lines -> 64 sets, LRU per set.
(Xeon 6962P L1d geometry. The model has no prefetcher and no L2. It counts
how many state lines must come from outside L1 per token per value head.)

State of one value head: 128 key rows x 128 value columns, FP32 = 64 KiB.
One key-head group = 2 value heads = 128 KiB (the prefill working copy).

Loop orders / layouts compared, per value head and token:
  today        : [head][row][col] layout. loop 1 reads all 128 rows, then
                 loop 2 reads and writes all 128 rows.
  halves_stride: same layout, but each head is processed as two column
                 halves (64 columns = 4 lines per row); loop 1 + loop 2 on
                 one half, then the other half.
  halves_contig: layout changed to [head][half][row][64 cols] (one half is
                 32 KiB contiguous); loop 1 + loop 2 on one half, then the
                 next half. Token-major (all halves for token t, then t+1).
  halves_token_inner: layout as halves_contig, loop order changed to
                 half-major: for each half, run all tokens of the chain,
                 then go to the next half.
Small per-token inputs (k, q: 8 lines each; v, output: 4 lines per half) are
included as separate streams so the simulation does not flatter any option.
"""
from collections import OrderedDict

SETS, WAYS, LINE = 64, 12, 64


class L1:
    def __init__(self):
        self.sets = [OrderedDict() for _ in range(SETS)]
        self.miss = 0
        self.hit = 0

    def touch(self, line):
        s = self.sets[line % SETS]
        if line in s:
            s.move_to_end(line)
            self.hit += 1
        else:
            self.miss += 1
            s[line] = True
            if len(s) > WAYS:
                s.popitem(last=False)


ROWS, CHUNKS = 128, 8          # 8 chunks of 16 FP32 = 8 lines per row
HEADS = 2                      # value heads in one key-head group
STATE_BASE = 0                 # line address of the group state
INPUT_BASE = 1 << 20           # per-token inputs live elsewhere


def state_line_today(head, row, chunk):
    return STATE_BASE + head * ROWS * CHUNKS + row * CHUNKS + chunk


def state_line_contig(head, half, row, c4):
    return STATE_BASE + head * ROWS * CHUNKS + half * ROWS * 4 + row * 4 + c4


def inputs(c, t, head, half=None):
    base = INPUT_BASE + t * 64
    for l in range(16):                 # k and q of the token (shared by heads)
        c.touch(base + l)
    lines = range(8) if half is None else range(half * 4, half * 4 + 4)
    for l in lines:                     # v and output of this head
        c.touch(base + 16 + head * 16 + l)
        c.touch(base + 16 + head * 16 + 8 + l)


def run(option, tokens):
    c = L1()
    state_misses = 0

    def st(line):
        nonlocal state_misses
        before = c.miss
        c.touch(line)
        state_misses += c.miss - before

    if option == "today":
        for t in range(tokens):
            for h in range(HEADS):
                inputs(c, t, h)
                for _ in range(2):                    # loop 1, loop 2
                    for r in range(ROWS):
                        for k in range(CHUNKS):
                            st(state_line_today(h, r, k))
    elif option == "halves_stride":
        for t in range(tokens):
            for h in range(HEADS):
                for half in range(2):
                    inputs(c, t, h, half)
                    for _ in range(2):
                        for r in range(ROWS):
                            for k in range(4):
                                st(state_line_today(h, r, half * 4 + k))
    elif option == "halves_contig":
        for t in range(tokens):
            for h in range(HEADS):
                for half in range(2):
                    inputs(c, t, h, half)
                    for _ in range(2):
                        for r in range(ROWS):
                            for k in range(4):
                                st(state_line_contig(h, half, r, k))
    elif option == "halves_token_inner":
        for h in range(HEADS):
            for half in range(2):
                for t in range(tokens):
                    inputs(c, t, h, half)
                    for _ in range(2):
                        for r in range(ROWS):
                            for k in range(4):
                                st(state_line_contig(h, half, r, k))
    return state_misses / (tokens * HEADS), c.miss / (tokens * HEADS)


if __name__ == "__main__":
    T = 128
    print(f"L1d model: {SETS} sets x {WAYS} ways x {LINE} B = {SETS*WAYS*LINE//1024} KiB, LRU, no prefetcher")
    print(f"chain of {T} tokens, one key-head group (2 value heads, 128 KiB of state)")
    print(f"{'option':22s} {'state lines from outside L1':>30s} {'all L1 misses':>16s}   (per token per value head)")
    base = None
    for opt in ("today", "halves_stride", "halves_contig", "halves_token_inner"):
        sm, am = run(opt, T)
        if base is None:
            base = sm
        print(f"{opt:22s} {sm:30.1f} {am:16.1f}   state traffic = {sm/base*100:5.1f} % of today")
    # set-aliasing arithmetic for the stride variant
    lines_per_set_half_stride = ROWS * 4 / (SETS // 2)
    print()
    print("Why halves_stride does not help: a 512-byte row stride maps the 4 lines of a")
    print(f"half row to only {SETS//2} of {SETS} sets -> {lines_per_set_half_stride:.0f} lines per set, more than {WAYS} ways.")
    print(f"Contiguous half: {ROWS*4} lines over {SETS} sets = {ROWS*4/SETS:.0f} lines per set (fits in {WAYS} ways).")
