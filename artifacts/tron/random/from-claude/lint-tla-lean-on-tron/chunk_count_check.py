#!/usr/bin/env python3
"""Test the two statements of ChunkCount.lean on a finite range of inputs.

A test can only cover a range. The Lean theorems claim every natural number.
Run: python3 -I chunk_count_check.py
"""
CAP = 128        # max_minibatch_size of the llama plugin
N_MAX = 1_000_000


def target_chunks(n):
    return (n + CAP - 1) // CAP   # h/tron/models/model.hpp:246


bad_room = sum(1 for n in range(N_MAX + 1) if not n <= target_chunks(n) * CAP)
bad_spare = sum(1 for n in range(1, N_MAX + 1)
                if not (target_chunks(n) - 1) * CAP < n)
print(f"enough_room    : n = 0 .. {N_MAX:,}: {bad_room} failures")
print(f"no_spare_chunk : n = 1 .. {N_MAX:,}: {bad_spare} failures")
print("examples:", {n: target_chunks(n) for n in (0, 1, 128, 129, 300)})
raise SystemExit(1 if bad_room or bad_spare else 0)
