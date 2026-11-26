"""Check 7: the memory layouts and tile coordinates given in the design
produce the intended matrix products.

Real 16 x 32-element tiles are cut out of buffers that have the documented
layouts, a literal TDPBF16PS is applied (Intel SDM operation section), and the
result is compared BIT FOR BIT with the logical product in TDPBF16PS add order
(the emulation used by 03_amx_emulation.py).

Layouts (bf16 values are held in FP32 here; the layout is the index order):
  KQ_a   [2C rows][128]            row-major, rows 0..C-1 = K, C..2C-1 = Q
  S_p    [64 key pairs][128][2]    piece p of S0; (j, c, e) = piece(S0[2j+e][c])
  KT_b   [C/16][4][16 pairs][16 tokens][2]   (cb, kb, j, n, e) = K[16cb+n][32kb+2j+e]
  KT_a   [128 key coords][C]       (i, t) = K[t][i]
  W_p    [C/2 token pairs][128][2] (j, c, e) = piece(W[2j+e][c])
  S      [128][128] FP32           accumulator tiles are cut out of S itself
"""
import numpy as np
from gdn_common import F32, bf16_rne, bf16_trunc, make_chain

import importlib
emu = importlib.import_module("03_amx_emulation")


def tdpbf16ps(c, a, b):
    """c: 16x16 FP32, a: 16 x 32 bf16, b: 16 x 32 bf16 (16 pairs per row)."""
    for m in range(16):
        t = np.zeros(32, F32)
        for k in range(16):
            t[0::2] = (t[0::2] + a[m, 2 * k] * b[k, 0::2]).astype(F32)
            t[1::2] = (t[1::2] + a[m, 2 * k + 1] * b[k, 1::2]).astype(F32)
        c[m] = (c[m] + (t[0::2] + t[1::2]).astype(F32)).astype(F32)


def tile(buf2d, row0, elem0):
    """16 rows x 32 elements starting at (row0, elem0) of a 2-D buffer."""
    return buf2d[row0:row0 + 16, elem0:elem0 + 32]


if __name__ == "__main__":
    rng = np.random.default_rng(3)
    C, dk, dv = 32, 128, 128
    ch = make_chain(rng, C)
    K, Q, S0 = ch["k"], ch["q"], ch["S0"]
    KQ_a = np.concatenate([K, Q], 0)
    pieces = emu.split3_trunc(S0)                              # hi, mid, lo
    S_p = [np.stack([p[0::2], p[1::2]], -1).reshape(64, 256) for p in pieces]

    # ---- P1: [K;Q] x S0 --------------------------------------------------
    R = np.zeros((2 * C, dv), F32)
    for col in range(8):
        for r in range(2 * C // 16):
            acc = np.zeros((16, 16), F32)                      # TILEZERO
            for kb in range(4):
                for p in (2, 1, 0):                            # lo, mid, hi
                    tdpbf16ps(acc, tile(KQ_a, 16 * r, 32 * kb), tile(S_p[p], 16 * kb, 32 * col))
            R[16 * r:16 * r + 16, 16 * col:16 * col + 16] = acc  # TILESTORED
    ref = np.zeros((2 * C, dv), F32)
    for kb in range(0, dk, 32):
        for p in pieces[::-1]:
            emu.tile_dp(ref, KQ_a[:, kb:kb + 32], p[kb:kb + 32, :])
    print("P1  [K;Q] x S0 : tiles equal logical product bit for bit:",
          bool((R.view(np.uint32) == ref.view(np.uint32)).all()))
    assert (R.view(np.uint32) == ref.view(np.uint32)).all()

    # ---- Gram: [K;Q] x K^T ----------------------------------------------
    KT_b = np.zeros((C // 16, 4, 16, 16, 2), F32)
    for cb in range(C // 16):
        for kb in range(4):
            for j in range(16):
                for n in range(16):
                    KT_b[cb, kb, j, n] = K[16 * cb + n, 32 * kb + 2 * j:32 * kb + 2 * j + 2]
    G = np.zeros((2 * C, C), F32)
    for cb in range(C // 16):
        for r in range(2 * C // 16):
            acc = np.zeros((16, 16), F32)
            for kb in range(4):
                tdpbf16ps(acc, tile(KQ_a, 16 * r, 32 * kb), KT_b[cb, kb].reshape(16, 32))
            G[16 * r:16 * r + 16, 16 * cb:16 * cb + 16] = acc
    ref = np.zeros((2 * C, C), F32)
    KT = np.ascontiguousarray(K.T)
    for kb in range(0, dk, 32):
        emu.tile_dp(ref, KQ_a[:, kb:kb + 32], KT[kb:kb + 32, :])
    print("Gram [K;Q] x K^T: tiles equal logical product bit for bit:",
          bool((G.view(np.uint32) == ref.view(np.uint32)).all()))
    assert (G.view(np.uint32) == ref.view(np.uint32)).all()

    # ---- update: S += K^T x W -------------------------------------------
    W = bf16_rne(rng.standard_normal((C, dv)).astype(F32)) * F32(1.2345678)  # any FP32
    W = W.astype(F32)
    wp = emu.split3_trunc(W)
    W_p = [np.stack([p[0::2], p[1::2]], -1).reshape(C // 2, 256) for p in wp]
    KT_a = np.ascontiguousarray(K.T)                           # [128][C]
    S = (F32(0.75) * S0).astype(F32)                           # stands for G[C]*S0
    S_ref = S.copy()
    for col in range(8):
        for rb in range(8):
            acc = S[16 * rb:16 * rb + 16, 16 * col:16 * col + 16].copy()   # TILELOADD from S
            for tb in range(C // 32):
                for p in (2, 1, 0):
                    tdpbf16ps(acc, tile(KT_a, 16 * rb, 32 * tb), tile(W_p[p], 16 * tb, 32 * col))
            S[16 * rb:16 * rb + 16, 16 * col:16 * col + 16] = acc           # TILESTORED to S
    for tb in range(0, C, 32):
        for p in wp[::-1]:
            emu.tile_dp(S_ref, KT_a[:, tb:tb + 32], p[tb:tb + 32, :])
    print("update S += K^T x W: tiles equal logical product bit for bit:",
          bool((S.view(np.uint32) == S_ref.view(np.uint32)).all()))
    assert (S.view(np.uint32) == S_ref.view(np.uint32)).all()
    exact = (KT_a.astype(np.float64) @ W.astype(np.float64)) + (0.75 * S0.astype(np.float64))
    print(f"   max |S - float64 product| = {np.abs(S - exact).max():.2e} "
          f"(max |S| = {np.abs(exact).max():.3f})")
    print("PASS")
