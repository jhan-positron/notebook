#!/usr/bin/env python3
"""Verifier: where subnormal FP32 values appear in the AVX-512 parts.

tron sets no flush-to-zero mode, so an AVX-512 operation with a subnormal
operand or result is handled by a slow path of the CPU. This script only
COUNTS such values; it measures no time.
- block form: decay products G (step 0), coefficients CK and CQ (step 3),
  weighted deltas W (step 5).
- token loop: the decayed state S x decay and the new state.
"""
import numpy as np

import vm_engine as E
from vm_checks import SCEN, SEEDS, H

f32 = np.float32


def sub(x):
    return (x != 0) & (np.abs(x) < E.TINY)


def count(name):
    T, kw, note = SCEN[name]
    S0, K, Q, V, D, Bt = E.make(SEEDS[name], H, T, **kw)
    C = 32
    nblk = H * (T // C)
    # block form step 0, one row of G = 32 values = 2 zmm registers
    g_vals = g_vec = 0
    for t0 in range(0, T, C):
        d = D[:, t0:t0 + C]
        G = np.zeros((H, C + 1, C + 1), f32)
        G[:, 0, 0] = 1
        for t in range(1, C + 1):
            G[:, t, :t] = G[:, t - 1, :t] * d[:, t - 1, None]
            G[:, t, t] = 1
        body = G[:, 1:, :32]  # rows 1..32, columns 0..31
        s = sub(body)
        g_vals += int(s.sum())
        g_vec += int(s.reshape(H, C, 2, 16).any(-1).sum())
    # token loop: subnormal values in S x decay and in the new state
    S = S0.copy()
    tok_sub = 0
    for t in range(T):
        Sd = S * D[:, t, None, None]
        tok_sub += int(sub(Sd).sum())
        r = np.einsum("hi,hic->hc", K[:, t].astype(np.float64), Sd.astype(np.float64)).astype(f32)
        delta = (V[:, t] - r) * Bt[:, t, None]
        S = (Sd.astype(np.float64) + K[:, t, :, None].astype(np.float64) * delta[:, None, :]).astype(f32)
        tok_sub += int(sub(S).sum())
    print(f"{name:10s} ({note})")
    print(f"   block form: subnormal decay products per block per value head {g_vals / nblk:7.1f} of 528; "
          f"zmm registers of G that hold one {g_vec / nblk:6.1f} of 64")
    print(f"   token loop: subnormal state values in {T} tokens x {H} heads: {tok_sub}")


for n in ("base", "lowdecay", "tinydecay"):
    count(n)
