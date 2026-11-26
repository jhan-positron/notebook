#!/usr/bin/env python3
"""Verifier (math and numerics lens): independent arithmetic engine.

Written from F6 and gated_delta_net.hpp:242-297 without importing the
prototype. FP32 is emulated exactly:
- fma32: exact product in float64, TwoSum, round to odd, one rounding to FP32.
- TDPBF16PS: per tile product an even chain and an odd chain of 16 FP32 fmas
  from +0, then tmp = even + odd, then acc = acc + tmp (Intel SDM operation
  text). Optional DAZ (subnormal inputs read as zero) and FTZ (subnormal
  results flushed to zero).
"""
import math
from fractions import Fraction

import numpy as np

f32, f64, u32 = np.float32, np.float64, np.uint32
DK = 128
DV = 128
SCALE = f32(1.0 / math.sqrt(128.0))  # gated_delta_net.hpp:242-243
TINY = f32(2.0 ** -126)  # smallest normal FP32


# ---------------------------------------------------------------- rounding
def rbf16(x):
    """bf16.hpp:91-97: nearest even on the FP32 bits; subnormal -> signed zero."""
    x = np.ascontiguousarray(x, dtype=f32)
    b = x.view(u32)
    nan = (b & u32(0x7FFFFFFF)) > u32(0x7F800000)
    tiny = (b & u32(0x7F800000)) == 0
    r = (b + u32(0x7FFF) + ((b >> u32(16)) & u32(1))) >> u32(16)
    r = np.where(tiny, (b >> u32(16)) & u32(0x8000), r)
    r = np.where(nan, (b >> u32(16)) | u32(0x0040), r)
    return ((r & u32(0xFFFF)) << u32(16)).astype(u32).view(f32)


def bf16_word(x):
    return (rbf16(x).view(u32) >> u32(16)).astype(np.int64)


def trunc16(x):
    return (np.ascontiguousarray(x, dtype=f32).view(u32) & u32(0xFFFF0000)).view(f32)


def split_trunc(x, n=3):
    """Specification step 1: hi = low 16 bits cleared; rem = x - hi; mid; lo."""
    x = np.ascontiguousarray(x, dtype=f32)
    hi = trunc16(x)
    rem = x - hi
    mid = trunc16(rem)
    if n == 2:
        return [mid, hi]
    lo = rem - mid
    return [lo, mid, hi]


def split_nearest(x, n=3):
    """The prototype's split (round to nearest)."""
    x = np.ascontiguousarray(x, dtype=f32)
    hi = rbf16(x)
    r1 = x - hi
    mid = rbf16(r1)
    if n == 2:
        return [mid, hi]
    return [rbf16(r1 - mid), mid, hi]


# ---------------------------------------------------------------- exact fma
def fma32(a, b, c):
    """Correctly rounded FP32 fma(a, b, c) on float32 arrays."""
    p = np.asarray(a, f32).astype(f64) * np.asarray(b, f32).astype(f64)  # exact (48 bits)
    c64 = np.asarray(c, f32).astype(f64)
    s = p + c64
    bb = s - p
    err = (p - (s - bb)) + (c64 - bb)  # TwoSum: s + err = p + c exactly
    fix = (err != 0.0) & ((s.view(np.int64) & 1) == 0)
    if fix.any():
        s = np.where(fix, np.nextafter(s, np.where(err > 0, np.inf, -np.inf)), s)
    return s.astype(f32)


def fma32_selftest(n=4000, seed=1):
    """Compare fma32 with exact rational arithmetic."""
    rng = np.random.default_rng(seed)
    a = rng.standard_normal(n).astype(f32)
    b = rng.standard_normal(n).astype(f32)
    c = (rng.standard_normal(n) * 10.0 ** rng.integers(-9, 3, n)).astype(f32)
    # hard cases: c close to -a*b, and c exactly at a rounding tie of a*b
    c[: n // 4] = (-(a[: n // 4].astype(f64) * b[: n // 4].astype(f64))).astype(f32)
    got = fma32(a, b, c)
    bad = 0
    for i in range(n):
        exact = Fraction(float(a[i])) * Fraction(float(b[i])) + Fraction(float(c[i]))
        # correctly rounded float32 of an exact rational
        want = round_fraction_f32(exact)
        if want != float(got[i]) and not (want == 0.0 and float(got[i]) == 0.0):
            bad += 1
    return bad, n


def round_fraction_f32(v):
    """Round an exact Fraction to FP32, nearest even (normal range only)."""
    if v == 0:
        return 0.0
    sign = -1 if v < 0 else 1
    v = abs(v)
    e = math.floor(math.log2(float(v)))
    while Fraction(2) ** e > v:
        e -= 1
    while Fraction(2) ** (e + 1) <= v:
        e += 1
    e = max(e, -126)
    q = v / (Fraction(2) ** (e - 23))
    n = q.numerator // q.denominator
    rem = q - n
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and n % 2 == 1):
        n += 1
    return sign * float(Fraction(n) * Fraction(2) ** (e - 23))


# ---------------------------------------------------------------- tile product
def _flush(x):
    return np.where(np.abs(x) < TINY, f32(0.0), x).astype(f32)


def tdp_block(A, B, acc, ftz=True):
    """One TDPBF16PS per 16 x 16 output tile, in logical index form.

    A [..., M, 32] (rows x 32 inner values), B [..., 32, N] (inner x columns),
    acc [..., M, N]. Inner values 2j go to the even chain, 2j+1 to the odd one.
    """
    if ftz:
        A, B, acc = _flush(A), _flush(B), _flush(acc)
    te = np.zeros(acc.shape, f32)
    to = np.zeros(acc.shape, f32)
    for j in range(16):
        te = fma32(A[..., :, 2 * j, None], B[..., None, 2 * j, :], te)
        to = fma32(A[..., :, 2 * j + 1, None], B[..., None, 2 * j + 1, :], to)
        if ftz:
            te, to = _flush(te), _flush(to)
    tmp = te + to
    if ftz:
        tmp = _flush(tmp)
    out = acc + tmp
    return _flush(out) if ftz else out


def tdpbf16ps_literal(C, A, B):
    """C1 formula on one tile triple. A [16][32], B [16][32] (row k holds 16
    pairs: B[k][2n], B[k][2n+1]), C [16][16]. DAZ and FTZ on."""
    A, B, C = _flush(A), _flush(B), _flush(C)
    te = np.zeros((16, 16), f32)
    to = np.zeros((16, 16), f32)
    for k in range(16):
        te = _flush(fma32(A[:, 2 * k, None], B[None, k, 0::2], te))
        to = _flush(fma32(A[:, 2 * k + 1, None], B[None, k, 1::2], to))
    return _flush(C + _flush(te + to))


# ---------------------------------------------------------------- token form
def token_f32(S0, K, Q, V, D, Bt, keep=None):
    """gated_delta_net.hpp:266-294 for H value heads at once.
    S0 [H][128][cols], K, Q [H][T][128], V [H][T][cols], D, Bt [H][T]."""
    H, T, _ = K.shape
    S = S0.astype(f32).copy()
    O = np.empty((H, T, S.shape[2]), f32)
    snaps = {}
    for t in range(T):
        Sd = S * D[:, t, None, None]  # line 271 and 290 (same value)
        r = np.zeros((H, S.shape[2]), f32)
        for i in range(DK):  # lines 267-275
            r = fma32(K[:, t, i, None], Sd[:, i, :], r)
        delta = (V[:, t] - r) * Bt[:, t, None]  # line 281
        S = fma32(K[:, t, :, None], delta[:, None, :], Sd)  # line 289
        sq = Q[:, t] * SCALE  # line 287
        o = np.zeros((H, S.shape[2]), f32)
        for i in range(DK):  # line 292
            o = fma32(sq[:, i, None], S[:, i, :], o)
        O[:, t] = o
        if keep and (t + 1) in keep:
            snaps[t + 1] = S.copy()
    return O, S, snaps


def token_f64(S0, K, Q, V, D, Bt, keep=None):
    H, T, _ = K.shape
    S = S0.astype(f64).copy()
    K, Q, V, D, Bt = (x.astype(f64) for x in (K, Q, V, D, Bt))
    O = np.empty((H, T, S.shape[2]), f64)
    snaps = {}
    for t in range(T):
        Sd = S * D[:, t, None, None]
        r = np.einsum("hi,hic->hc", K[:, t], Sd)
        delta = (V[:, t] - r) * Bt[:, t, None]
        S = Sd + K[:, t, :, None] * delta[:, None, :]
        O[:, t] = np.einsum("hi,hic->hc", Q[:, t] * f64(SCALE), S)
        if keep and (t + 1) in keep:
            snaps[t + 1] = S.copy()
    return O, S, snaps


# ---------------------------------------------------------------- block form
def block_spec(S0, K, Q, V, D, Bt, C=32, split=split_trunc, pieces=3, p1_order="kb_outer",
               ftz=True, gdiv=False, info=None, keep=None):
    """Steps 0 to 6 of the specification's block_algorithm, FP32.

    p1_order "kb_outer": key block outer, pieces inner (the loop of tile_mapping).
    p1_order "piece_outer": pieces outer, key blocks inner (the prototype's tdp_mm).
    """
    H, T, _ = K.shape
    assert T % C == 0 and C % 32 == 0
    S = S0.astype(f32).copy()
    O = np.empty((H, T, DV), f32)
    snaps = {}
    for t0 in range(0, T, C):
        Kc = np.ascontiguousarray(K[:, t0:t0 + C])
        Qc = np.ascontiguousarray(Q[:, t0:t0 + C])
        Vc, d, b = V[:, t0:t0 + C], D[:, t0:t0 + C], Bt[:, t0:t0 + C]
        # step 0
        G = np.zeros((H, C + 1, C + 1), f32)
        G[:, 0, 0] = 1
        if not gdiv:
            for t in range(1, C + 1):
                G[:, t, :t] = G[:, t - 1, :t] * d[:, t - 1, None]
                G[:, t, t] = 1
        else:
            g = np.ones((H, C + 1), f32)
            for t in range(1, C + 1):
                g[:, t] = g[:, t - 1] * d[:, t - 1]
            with np.errstate(all="ignore"):
                G = np.tril(g[:, :, None] / g[:, None, :]).astype(f32)
        gam = G[:, :, 0]
        if info is not None:
            tri = np.tril(np.ones((C + 1, C + 1), bool), -1)
            g_ = G[:, tri]
            info["G_sub"] = info.get("G_sub", 0) + int(((g_ != 0) & (np.abs(g_) < TINY)).sum())
            info["G_zero"] = info.get("G_zero", 0) + int((g_ == 0).sum())
            info["G_n"] = info.get("G_n", 0) + int(g_.size)
        # step 1
        KQ = np.concatenate([Kc, Qc], axis=1)  # [H][2C][128]
        sp = split(S, pieces)
        acc = np.zeros((H, 2 * C, DV), f32)
        if p1_order == "kb_outer":
            for kb in range(4):
                for p in sp:
                    acc = tdp_block(KQ[:, :, 32 * kb:32 * kb + 32], p[:, 32 * kb:32 * kb + 32, :], acc, ftz)
        else:
            for p in sp:
                for kb in range(4):
                    acc = tdp_block(KQ[:, :, 32 * kb:32 * kb + 32], p[:, 32 * kb:32 * kb + 32, :], acc, ftz)
        R0, U0 = acc[:, :C], acc[:, C:]
        # step 2
        KT = np.ascontiguousarray(Kc.transpose(0, 2, 1))  # [H][128][C]
        acc = np.zeros((H, 2 * C, C), f32)
        for kb in range(4):
            acc = tdp_block(KQ[:, :, 32 * kb:32 * kb + 32], KT[:, 32 * kb:32 * kb + 32, :], acc, ftz)
        KK, QK = acc[:, :C], acc[:, C:]
        # step 3
        with np.errstate(all="ignore"):
            Gt = G[:, 1:, 1:]
            CK = Gt * KK
            CQ = (Gt * QK) * SCALE
            sg = gam[:, 1:] * SCALE
            # step 4
            Delta = np.zeros((H, C, DV), f32)
            for t in range(C):
                r = gam[:, t + 1, None] * R0[:, t]
                for u in range(t):
                    r = fma32(CK[:, t, u, None], Delta[:, u], r)
                Delta[:, t] = (Vc[:, t] - r) * b[:, t, None]
                o = sg[:, t, None] * U0[:, t]
                for u in range(t + 1):
                    o = fma32(CQ[:, t, u, None], Delta[:, u], o)
                O[:, t0 + t] = o
            # step 5
            W = G[:, C, 1:, None] * Delta
            wp = split(W, pieces)
            # step 6
            Tm = np.zeros((H, DK, DV), f32)
            for p in wp:
                for tb in range(0, C, 32):
                    Tm = tdp_block(KT[:, :, tb:tb + 32], p[:, tb:tb + 32, :], Tm, ftz)
            S = fma32(gam[:, C, None, None], S, Tm)
        if keep and (t0 + C) in keep:
            snaps[t0 + C] = S.copy()
    return O, S, snaps


# ---------------------------------------------------------------- inputs
def normalize_gdn(x):
    """gated_delta_net.hpp:177-194 (reduce order simplified; result is bf16-exact)."""
    v = rbf16(np.asarray(x, f32))
    sq = rbf16(v * v)
    lanes = sq.reshape(sq.shape[:-1] + (8, 16))
    acc = np.zeros(sq.shape[:-1] + (16,), f32)
    for ch in range(8):
        acc = acc + lanes[..., ch, :]
    y = acc[..., :8] + acc[..., 8:]
    z = y[..., :4] + y[..., 4:]
    w = z[..., :2] + z[..., 2:]
    quad = rbf16(w[..., 0] + w[..., 1])
    ns = rbf16(quad + rbf16(np.array([1e-6], f32))[0])
    inv = rbf16(f32(1.0) / np.sqrt(ns))
    return rbf16(v * inv[..., None])


def make(seed, H, T, decay, beta, v, s0, rho=0.0, qk=0.0):
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((H, T, DK))
    kraw = np.empty_like(noise)
    kraw[:, 0] = noise[:, 0]
    for t in range(1, T):
        kraw[:, t] = rho * kraw[:, t - 1] + math.sqrt(1 - rho * rho) * noise[:, t]
    qraw = qk * kraw + math.sqrt(1 - qk * qk) * rng.standard_normal((H, T, DK))
    K = normalize_gdn(kraw.astype(f32))
    Q = normalize_gdn(qraw.astype(f32))
    V = rbf16(v(rng, (H, T, DV)).astype(f32))
    D = decay(rng, (H, T)).astype(f32)
    Bt = rbf16(beta(rng, (H, T)).astype(f32))
    S0 = s0(rng, (H, DK, DV)).astype(f32)
    return S0, K, Q, V, D, Bt


# ---------------------------------------------------------------- metrics
def spacing(m):
    """FP32 spacing (gap between neighbours) at magnitude m."""
    return 2.0 ** (math.floor(math.log2(m)) - 23) if m > 0 else 2.0 ** -149


def word_diff(x, ref):
    """bf16 words that differ; and the same for |ref| >= 1 % of rms(ref)."""
    a, b = bf16_word(x), bf16_word(ref)
    ne = a != b

    def ordinal(w):
        return np.where(w & 0x8000, -(w & 0x7FFF), w & 0x7FFF)

    dist = np.abs(ordinal(a) - ordinal(b))
    rms = float(np.sqrt(np.mean(np.asarray(ref, f64) ** 2)))
    big = np.abs(ref) >= 0.01 * rms
    return dict(n=int(ne.sum()), total=int(ne.size), max_step=int(dist[ne].max()) if ne.any() else 0,
                n_big=int((ne & big).sum()), total_big=int(big.sum()),
                max_step_big=int(dist[ne & big].max()) if (ne & big).any() else 0)


def postprocess(o, gate, eps=1e-6):
    """gdn_rolling_executor.hpp:446-467 with unit weight (est.: the sum order of
    the quadrance is not the kernel's). o [..., 128] FP32, gate [..., 128]."""
    x = rbf16(o)
    q = (x.astype(f64) ** 2).sum(-1).astype(f32)
    ooss = f32(1.0) / np.sqrt(q / f32(128.0) + f32(eps))
    normalized = rbf16(ooss[..., None] * x)
    weighted = rbf16(normalized * f32(1.0))
    g = rbf16(gate)
    sw = (g / (f32(1.0) + np.exp(-g.astype(f64)).astype(f32))).astype(f32)
    return rbf16(weighted * sw)
