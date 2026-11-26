#!/usr/bin/env python3
"""R4: the query scale of the GDN read step, and the size of the proposed figure strings.

It computes:
  1. the query scale of tron's token kernel for a key head of 128 values, as the kernel computes it
     (gated_delta_net.hpp lines 242-243: static_cast<float>(1.0 / std::sqrt(double(key_head_dim)))),
     and the factor by which the output changes when the scale is left out;
  2. the length of every proposed figure string against its limit:
     figure 2 formula: at most 34 characters (monospace, 7.5 px per character, from x = 631.5 in a figure 960 px wide),
     figure 12 note  : at most 52 characters.

Inputs: none (constants only). The proposed strings are typed in below.
Output: text on stdout (saved beside this script as r4_scale_check.out). Pure python, deterministic.
"""
import math
import struct

KEY_HEAD_DIM = 128
scale64 = 1.0 / math.sqrt(float(KEY_HEAD_DIM))
scale32 = struct.unpack("f", struct.pack("f", scale64))[0]   # the FP32 value that the kernel uses
print(f"query scale = 1 / sqrt({KEY_HEAD_DIM}) = {scale64:.10f} (float64), {scale32:.10f} as FP32, rounded for the figure: {scale32:.4f}")
print(f"output without the scale / output with the scale = sqrt({KEY_HEAD_DIM}) = {math.sqrt(KEY_HEAD_DIM):.4f}")
print()

FIG2_X0, FIG2_PX, FIG_W = 631.5, 7.5, 960
fig2_formulas = [
    ("line 1, unchanged", "r = decay x (k times S)"),
    ("line 2, unchanged", "delta = beta x (v - r)"),
    ("line 3, unchanged", "S = decay x S + (k outer delta)"),
    ("line 4, old", "o = q times S"),
    ("line 4, new", "o = (scale x q) times S"),
]
print("figure 2, formula column (limit 34 characters):")
for name, s in fig2_formulas:
    end = FIG2_X0 + FIG2_PX * len(s)
    print(f"  {len(s):2d} characters, ends at x = {end:5.1f} of {FIG_W} px  {'OK ' if len(s) <= 34 else 'TOO LONG'}  {name}: {s}")
fig2_notes = [
    ("note 1, unchanged", "k, q, v are bf16 values. S, decay and delta are FP32."),
    ("note 2, new", "scale = 1 / sqrt(128) = 0.0884. It multiplies q in FP32."),
]
print("figure 2, note lines (proportional font, 12 px, from x = 534; checked by rendering, see render/after/token_flow.png):")
for name, s in fig2_notes:
    print(f"  {len(s):2d} characters  {name}: {s}")
fig12_notes = [
    ("note 6, new", "scale = 1 / sqrt(128), in the FP32 coefficients."),
]
print("figure 12, note lines (limit 52 characters):")
for name, s in fig12_notes:
    print(f"  {len(s):2d} characters  {'OK ' if len(s) <= 52 else 'TOO LONG'}  {name}: {s}")
for _, s in fig2_formulas + fig2_notes + fig12_notes:
    assert all(ord(ch) < 128 for ch in s) and ";" not in s
print()
print("all proposed strings are ASCII and hold no semicolon")
