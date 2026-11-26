#!/usr/bin/env python3
"""Numeric prototype of the GatedDeltaNet (GDN) recurrence in two forms.

Form 1  token by token, as h/tron/kernels/gated_delta_net.hpp:259-297 computes it.
Form 2  block form: a chunk of C tokens at once (derivation in block_form()).
Form 3  block form whose big matrix products use only bf16 operands, the way an
        AMX TDPBF16PS kernel would: every FP32 operand is split into 3 (or 2)
        bf16 pieces.

Stand-alone: python3 + numpy only. Nothing here touches tron.
"""
import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import math
import sys
import time
from fractions import Fraction
from multiprocessing import Pool

import numpy as np

f32, f64 = np.float32, np.float64
DK = 128  # key rows of one value head's state
DV = 128  # value columns of one value head's state
# gated_delta_net.hpp:242-243: static_cast<float>(1.0 / std::sqrt(double(key_head_dim)))
SCALE32 = f32(1.0 / math.sqrt(float(DK)))
CHUNKS = (8, 16, 32, 64, 128)
F11_TOL = 1e-7


# --------------------------------------------------------------------------
# bf16 rounding on FP32 bit patterns (h/common/numerics/bf16.hpp:91-97)
# --------------------------------------------------------------------------
def round_bf16(x):
    """Round float32 values to bf16, nearest even; result is float32 holding
    the bf16 value. Zero and FP32 subnormal -> signed zero. NaN -> quiet NaN."""
    x = np.ascontiguousarray(x, dtype=f32)
    b = x.view(np.uint32)
    nan = (b & np.uint32(0x7FFFFFFF)) > np.uint32(0x7F800000)
    tiny = (b & np.uint32(0x7F800000)) == 0
    r = (b + np.uint32(0x7FFF) + ((b >> np.uint32(16)) & np.uint32(1))) >> np.uint32(16)
    r = np.where(tiny, (b >> np.uint32(16)) & np.uint32(0x8000), r)
    r = np.where(nan, (b >> np.uint32(16)) | np.uint32(0x0040), r)
    return ((r & np.uint32(0xFFFF)) << np.uint32(16)).astype(np.uint32).view(f32)


def bf16_bits(x):
    """bf16 word (uint16 held in uint32) of round_bf16(x)."""
    return round_bf16(x).view(np.uint32) >> np.uint32(16)


def bits32(u):
    return np.array(u, dtype=np.uint32).view(f32)


# --------------------------------------------------------------------------
# exact float32 fma emulation
# --------------------------------------------------------------------------
def add_round_f32(p64, c64):
    """float32 round-to-nearest-even of the exact value p64 + c64.

    p64 is an exact product of two float32 values held in float64, c64 is a
    float32 value held in float64. The float64 sum is first rounded to odd
    (TwoSum gives the exact rounding error), then rounded once to float32.
    Rounding to odd at 53 bits and then to nearest at 24 bits equals one
    correct rounding, so this is a true fma(a, b, c) in float32."""
    s = p64 + c64
    bb = s - p64
    err = (p64 - (s - bb)) + (c64 - bb)
    nz = err != 0.0
    if nz.any():
        fix = nz & ((s.view(np.int64) & 1) == 0)
        if fix.any():
            s = np.where(fix, np.nextafter(s, np.where(err > 0, np.inf, -np.inf)), s)
    return s.astype(f32)


def fma32(a, b, c):
    """fma(a, b, c) on float32 arrays, correctly rounded."""
    return add_round_f32(a.astype(f64) * b.astype(f64), c.astype(f64))


# --------------------------------------------------------------------------
# input kernels of the recurrence (gated_delta_net.hpp:169-199)
# --------------------------------------------------------------------------
def normalize_gdn(x):
    """normalize_gdn (gated_delta_net.hpp:177-194) on [..., width] float32."""
    x = np.ascontiguousarray(x, dtype=f32)
    lead = x.shape[:-1]
    width = x.shape[-1]
    values = round_bf16(x)
    sq = round_bf16(values * values).reshape(lead + (width // 16, 16))
    squared = np.zeros(lead + (16,), f32)
    for chunk in range(width // 16):  # per-lane FP32 sum over chunks
        squared = squared + sq[..., chunk, :]
    # _mm512_reduce_add_ps: halves, then quarters, then pairs
    y = squared[..., 0:8] + squared[..., 8:16]
    z = y[..., 0:4] + y[..., 4:8]
    w = z[..., 0:2] + z[..., 2:4]
    total = w[..., 0] + w[..., 1]
    quadrance = round_bf16(total)
    eps = round_bf16(np.array([1e-6], f32))[0]
    norm_squared = round_bf16(quadrance + eps)
    inv = round_bf16(f32(1.0) / np.sqrt(norm_squared))
    return round_bf16(values * inv[..., None])


def libm_f32(fn, x):
    """A float32 libm call, modelled as the correctly rounded result."""
    return fn(np.asarray(x, f32).astype(f64)).astype(f32)


def gdn_decay(a, A_exp, dt_bias):
    """gated_delta_net.hpp:259-262."""
    x = round_bf16(a) + np.asarray(dt_bias, f32)
    sp = np.where(x > f32(20.0), x, libm_f32(np.log1p, libm_f32(np.exp, x)))
    return libm_f32(np.exp, (-np.asarray(A_exp, f32)) * sp.astype(f32))


def gdn_beta(b):
    """gated_delta_net.hpp:197-199; sigmoid = recip(exp(-x) + 1.0f) (simd/fp32.hpp:965)."""
    xb = round_bf16(b)
    e = libm_f32(np.exp, -xb)
    return round_bf16(f32(1.0) / (e + f32(1.0)))


# --------------------------------------------------------------------------
# Form 1: token by token (gated_delta_net.hpp:266-297)
# --------------------------------------------------------------------------
def token_form_f32(S0, K, Q, V, D, Bt, snap_every=8):
    """S0 [H][key row i][value column c] float32. K, Q [H][T][128] bf16-exact.
    V [H][T][128] bf16-exact. D, Bt [H][T]. Returns outputs [H][T][128],
    final state, and state snapshots every snap_every tokens."""
    H, T, _ = K.shape
    S = S0.astype(f32).copy()
    K64 = K.astype(f64)
    SQ64 = (Q * SCALE32).astype(f64)  # fl32(q * scale), line 287
    O = np.empty((H, T, DV), f32)
    snaps = []
    for t in range(T):
        Sd64 = (S * D[:, t, None, None]).astype(f64)  # fl32(state * decay), lines 270-271, 290
        k64 = K64[:, t]
        P = k64[:, :, None] * Sd64  # exact products k[i] * decayed
        r = np.zeros((H, DV), f64)
        for i in range(DK):  # lines 267-275: one fma chain per value column
            r = add_round_f32(P[:, i, :], r).astype(f64)
        delta = (V[:, t] - r.astype(f32)) * Bt[:, t, None]  # line 281
        # line 289: new = fma(k[i], delta[c], state*decay); rows are independent
        S = add_round_f32(k64[:, :, None] * delta.astype(f64)[:, None, :], Sd64)
        P2 = SQ64[:, t][:, :, None] * S.astype(f64)  # exact products
        res = np.zeros((H, DV), f64)
        for i in range(DK):  # line 292: fma chain over key rows
            res = add_round_f32(P2[:, i, :], res).astype(f64)
        O[:, t] = res.astype(f32)
        if (t + 1) % snap_every == 0:
            snaps.append(S.copy())
    return O, S, snaps


def token_form_f64(S0, K, Q, V, D, Bt, snap_every=8):
    """Same recurrence in float64 (the oracle; sum order is irrelevant here)."""
    H, T, _ = K.shape
    S = S0.astype(f64).copy()
    K64, Q64, V64 = K.astype(f64), Q.astype(f64), V.astype(f64)
    D64, B64 = D.astype(f64), Bt.astype(f64)
    scale = f64(SCALE32)
    O = np.empty((H, T, DV), f64)
    snaps = []
    for t in range(T):
        Sd = S * D64[:, t, None, None]
        k = K64[:, t]
        r = np.matmul(k[:, None, :], Sd)[:, 0, :]
        delta = (V64[:, t] - r) * B64[:, t, None]
        S = Sd + k[:, :, None] * delta[:, None, :]
        O[:, t] = np.matmul((Q64[:, t] * scale)[:, None, :], S)[:, 0, :]
        if (t + 1) % snap_every == 0:
            snaps.append(S.copy())
    return O, S, snaps


# --------------------------------------------------------------------------
# matrix-product engines for the block form
# --------------------------------------------------------------------------
def mm_fma(A, B, init=None):
    """FP32 product, one fma chain per output element over the inner index in
    ascending order (what a plain AVX-512 FP32 kernel does)."""
    H, M, Kd = A.shape
    N = B.shape[2]
    acc = np.zeros((H, M, N), f64) if init is None else init.astype(f64)
    A64, B64 = A.astype(f64), B.astype(f64)
    for kk in range(Kd):
        acc = add_round_f32(A64[:, :, kk, None] * B64[:, None, kk, :], acc).astype(f64)
    return acc.astype(f32)


def split_bf16(x, n_pieces):
    """x = hi + mid + lo with every piece bf16-representable.
    Returned smallest piece first (the accumulation order used)."""
    hi = round_bf16(x)
    r1 = x - hi
    mid = round_bf16(r1)
    if n_pieces == 2:
        return [mid, hi]
    lo = round_bf16(r1 - mid)
    return [lo, mid, hi]


def tdp_mm(A, pieces, init=None):
    """Accumulating TDPBF16PS tile products: init + sum over pieces of A @ piece.

    A [H][M][Kd] and every piece [H][Kd][N] hold bf16-exact float32 values, so
    each product is exact in float32 and each add rounds once, like the
    instruction's FP32 fma. Add order follows the Intel SDM operation text for
    TDPBF16PS: per tile product (32 values of the inner index = 16 bf16 pairs)
    an even chain and an odd chain start at +0 and take 16 adds each, then
    (even + odd) is added to the accumulator tile."""
    H, M, Kd = A.shape
    N = pieces[0].shape[2]
    acc = np.zeros((H, M, N), f32) if init is None else init.astype(f32).copy()
    for P in pieces:
        for k0 in range(0, Kd, 32):
            te = np.zeros((H, M, N), f32)
            to = np.zeros((H, M, N), f32)
            for j in range(16):
                ke = k0 + 2 * j
                if ke < Kd:
                    te += A[:, :, ke, None] * P[:, None, ke, :]
                if ke + 1 < Kd:
                    to += A[:, :, ke + 1, None] * P[:, None, ke + 1, :]
            acc += te + to
    return acc


# --------------------------------------------------------------------------
# Form 2 / 3: block form
# --------------------------------------------------------------------------
def block_form(S0, K, Q, V, D, Bt, C, mode, ratio="prod", piece_order="small_first"):
    """Process C tokens per step.

    Per chunk, with d_t the decay of token t (t = 1..C), S_0 the state at the
    chunk start, k_t, q_t the normalized key and query, v_t, beta_t:

      G[t][u] = d_{u+1} * ... * d_t   (u < t),  G[t][t] = 1,  gamma_t = G[t][0]
      A   = K S_0          (C x 128)       Bq = Q S_0         (C x 128)
      KK  = K K^T          (C x C)         QK = Q K^T         (C x C)
      r_t     = gamma_t A[t] + sum_{u<t}  (G[t][u] KK[t][u]) delta_u
      delta_t = (v_t - r_t) beta_t                                  (forward substitution)
      o_t     = scale gamma_t Bq[t] + sum_{u<=t} (scale G[t][u] QK[t][u]) delta_u
      S_C     = gamma_C S_0 + K^T (w * Delta),   w_u = G[C][u]

    G is built by products only (ratio="prod"); ratio="div" builds it as
    gamma_t / gamma_u to show what division does when gamma underflows.

    mode: "f64"    all float64 (proves the algebra)
          "f32"    float32, fma chains everywhere
          "split3" the three big products (K S_0, Q S_0, K^T (w*Delta)) and the two
                   Gram products use tdp_mm; S_0 and w*Delta are split in 3 bf16 pieces
          "split2" same with 2 pieces (hi + mid)
    The two triangular C x C steps have FP32 on both sides (coefficient and
    delta), so they stay float32 fma chains in every float32 mode."""
    H, T, _ = K.shape
    fl = f64 if mode == "f64" else f32
    n_pieces = {"split3": 3, "split2": 2}.get(mode, 0)
    S = S0.astype(fl).copy()
    O = np.empty((H, T, DV), fl)
    snaps = []
    scale = fl(SCALE32)
    one = fl(1.0)

    def pieces_of(x):
        p = split_bf16(x, n_pieces)
        return p if piece_order == "small_first" else p[::-1]

    for t0 in range(0, T, C):
        Kc = np.ascontiguousarray(K[:, t0:t0 + C]).astype(fl)
        Qc = np.ascontiguousarray(Q[:, t0:t0 + C]).astype(fl)
        Vc = V[:, t0:t0 + C].astype(fl)
        d = D[:, t0:t0 + C].astype(fl)
        b = Bt[:, t0:t0 + C].astype(fl)
        KT = np.ascontiguousarray(Kc.transpose(0, 2, 1))

        G = np.zeros((H, C + 1, C + 1), fl)
        G[:, 0, 0] = one
        if ratio == "prod":
            for t in range(1, C + 1):
                G[:, t, :t] = G[:, t - 1, :t] * d[:, t - 1, None]
                G[:, t, t] = one
        else:  # gamma_t / gamma_u, the form to avoid
            gam_c = np.ones((H, C + 1), fl)
            for t in range(1, C + 1):
                gam_c[:, t] = gam_c[:, t - 1] * d[:, t - 1]
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                G = np.tril(gam_c[:, :, None] / gam_c[:, None, :])
        gam = G[:, :, 0]

        if mode == "f64":
            A, Bq = Kc @ S, Qc @ S
            KK, QK = Kc @ KT, Qc @ KT
        elif mode == "f32":
            A, Bq = mm_fma(Kc, S), mm_fma(Qc, S)
            KK, QK = mm_fma(Kc, KT), mm_fma(Qc, KT)
        else:
            sp = pieces_of(S)
            A, Bq = tdp_mm(Kc, sp), tdp_mm(Qc, sp)
            KK, QK = tdp_mm(Kc, [KT]), tdp_mm(Qc, [KT])

        with np.errstate(invalid="ignore", over="ignore"):
            CK = G[:, 1:, 1:] * KK
            CQ = (G[:, 1:, 1:] * QK) * scale
            sg = gam[:, 1:] * scale
            Delta = np.empty((H, C, DV), fl)
            for t in range(C):
                if mode == "f64":
                    r = gam[:, t + 1, None] * A[:, t] + np.einsum(
                        "hu,huc->hc", CK[:, t, :t], Delta[:, :t])
                    Delta[:, t] = (Vc[:, t] - r) * b[:, t, None]
                    O[:, t0 + t] = sg[:, t, None] * Bq[:, t] + np.einsum(
                        "hu,huc->hc", CQ[:, t, :t + 1], Delta[:, :t + 1])
                else:
                    D64 = Delta.astype(f64)
                    r = (gam[:, t + 1, None] * A[:, t]).astype(f64)
                    ck = CK[:, t].astype(f64)
                    for u in range(t):
                        r = add_round_f32(ck[:, u, None] * D64[:, u], r).astype(f64)
                    Delta[:, t] = (Vc[:, t] - r.astype(f32)) * b[:, t, None]
                    D64t = Delta[:, t].astype(f64)
                    o = (sg[:, t, None] * Bq[:, t]).astype(f64)
                    cq = CQ[:, t].astype(f64)
                    for u in range(t):
                        o = add_round_f32(cq[:, u, None] * D64[:, u], o).astype(f64)
                    o = add_round_f32(cq[:, t, None] * D64t, o)
                    O[:, t0 + t] = o

            WD = G[:, C, 1:, None] * Delta
            base = gam[:, C, None, None] * S
            if mode == "f64":
                S = base + KT @ WD
            elif mode == "f32":
                S = mm_fma(KT, WD, init=base)
            else:
                S = tdp_mm(KT, pieces_of(WD), init=base)
        snaps.append(S.copy())
    return O, S, snaps


# --------------------------------------------------------------------------
# comparison helpers
# --------------------------------------------------------------------------
def diff_stats(x, ref):
    """max abs diff, max element-wise relative diff, RMS diff over RMS ref."""
    x64, r64 = np.asarray(x, f64), np.asarray(ref, f64)
    if not (np.isfinite(x64).all() and np.isfinite(r64).all()):
        return float("nan"), float("nan"), float("nan")
    dabs = np.abs(x64 - r64)
    nz = r64 != 0
    max_rel = float((dabs[nz] / np.abs(r64[nz])).max()) if nz.any() else 0.0
    rms_ref = float(np.sqrt(np.mean(r64 * r64)))
    rms_rel = float(np.sqrt(np.mean(dabs * dabs)) / rms_ref) if rms_ref > 0 else 0.0
    return float(dabs.max()), max_rel, rms_rel


def flips(x, ref):
    """bf16-rounded outputs that differ between x and ref.

    Returns (n, total, max_steps, n_big, total_big, max_steps_big). "big" keeps
    only outputs with |ref| >= 1 % of the RMS of ref: an output that is close
    to zero by cancellation has a coarse relative error, so a tiny absolute
    difference can move it by several bf16 steps."""
    xr = np.asarray(x, f32)
    rr = np.asarray(ref, f32)
    a = bf16_bits(xr).astype(np.int64)
    b = bf16_bits(rr).astype(np.int64)
    ne = a != b
    n = int(ne.sum())

    def ordinal(w):  # monotone integer order of bf16 words
        return np.where(w & 0x8000, -(w & 0x7FFF), w & 0x7FFF)

    dist = np.abs(ordinal(a) - ordinal(b))
    step = int(dist[ne].max()) if n else 0
    rms = float(np.sqrt(np.mean(rr.astype(f64) ** 2)))
    big = np.abs(rr) >= 0.01 * rms
    neb = ne & big
    nb = int(neb.sum())
    stepb = int(dist[neb].max()) if nb else 0
    return n, int(ne.size), step, nb, int(big.sum()), stepb


def flips_txt(fl):
    return (f"{fl[0]:>5d} of {fl[1]} (max {fl[2]} steps); above 1 % of rms: "
            f"{fl[3]:>5d} of {fl[4]} (max {fl[5]} steps)")


def oracle_restart(starts, ends, O_form, K, Q, V, D, Bt, C):
    """F11-style error: a float64 token-by-token oracle restarts at every chunk
    start from the form's own float32 state, runs C tokens, and is compared with
    the form's outputs in that chunk and its state at the chunk end."""
    T = K.shape[1]
    mo = ms = 0.0
    for j in range(T // C):
        sl = slice(j * C, (j + 1) * C)
        O64, S64, _ = token_form_f64(starts[j], K[:, sl], Q[:, sl], V[:, sl],
                                     D[:, sl], Bt[:, sl], snap_every=10 ** 9)
        of, sf = np.asarray(O_form[:, sl], f64), np.asarray(ends[j], f64)
        if not (np.isfinite(of).all() and np.isfinite(sf).all()):
            return float("nan"), float("nan")
        mo = max(mo, float(np.abs(of - O64).max()))
        ms = max(ms, float(np.abs(sf - S64).max()))
    return mo, ms


# --------------------------------------------------------------------------
# scenarios
# --------------------------------------------------------------------------
SCENARIOS = {
    # name: decay range, beta range, value magnitudes, state scale, key correlation
    "normal": dict(seed=101, decay=(0.9, 1.0), beta=(0.0, 1.0), v=("log", 0.01, 1.0),
                   state=("normal", 0.01), rho=0.0,
                   note="decay 0.9-1.0, beta 0-1, |v| 0.01-1 (log-uniform), state sigma 0.01"),
    "hard": dict(seed=202, decay=(0.3, 1.0), beta=(0.0, 1.0), v=("log", 0.01, 1.0),
                 state=("normal", 0.01), rho=0.0,
                 note="decay 0.3-1.0, beta 0-1, |v| 0.01-1 (log-uniform), state sigma 0.01"),
    "testmag": dict(seed=303, decay=(0.70, 0.85), beta=(0.3, 0.7), v=("uni", 0.0, 0.10),
                    state=("uniform", 0.0035), rho=0.0, q_from_k=0.6,
                    note="magnitudes like t_gated_delta_net.cpp literals: decay 0.70-0.85, "
                         "beta 0.3-0.7, v uniform +-0.10, state uniform +-0.0035, q correlated with k"),
    "underflow": dict(seed=404, decay=(0.05, 0.5), beta=(0.0, 1.0), v=("log", 0.01, 1.0),
                      state=("normal", 0.01), rho=0.0,
                      note="decay 0.05-0.5 so gamma underflows FP32 inside a 64- or 128-token chunk"),
    "corrkeys": dict(seed=505, decay=(0.9, 1.0), beta=(0.0, 1.0), v=("log", 0.01, 1.0),
                     state=("normal", 0.01), rho=0.9, q_from_k=0.7,
                     note="EXTRA (not in the brief): as 'normal' but consecutive keys correlated "
                          "(AR(1), rho 0.9) and q correlated with k"),
}


def make_inputs(p, H, T):
    rng = np.random.default_rng(p["seed"])
    noise = rng.standard_normal((H, T, DK))
    kraw = np.empty_like(noise)
    rho = p.get("rho", 0.0)
    kraw[:, 0] = noise[:, 0]
    for t in range(1, T):
        kraw[:, t] = rho * kraw[:, t - 1] + math.sqrt(1.0 - rho * rho) * noise[:, t]
    qn = rng.standard_normal((H, T, DK))
    a = p.get("q_from_k", 0.0)
    qraw = a * kraw + math.sqrt(1.0 - a * a) * qn
    K = normalize_gdn(kraw.astype(f32))
    Q = normalize_gdn(qraw.astype(f32))
    kind, lo, hi = p["v"]
    if kind == "log":
        mag = np.exp(rng.uniform(math.log(lo), math.log(hi), (H, T, DV)))
        V = round_bf16((mag * rng.choice([-1.0, 1.0], (H, T, DV))).astype(f32))
    else:
        V = round_bf16(rng.uniform(-hi, hi, (H, T, DV)).astype(f32))
    D = rng.uniform(p["decay"][0], p["decay"][1], (H, T)).astype(f32)
    Bt = round_bf16(rng.uniform(p["beta"][0], p["beta"][1], (H, T)).astype(f32))
    skind, sscale = p["state"]
    if skind == "normal":
        S0 = (rng.standard_normal((H, DK, DV)) * sscale).astype(f32)
    else:
        S0 = rng.uniform(-sscale, sscale, (H, DK, DV)).astype(f32)
    return S0, K, Q, V, D, Bt


def run_scenario(args):
    name, H, T = args
    p = SCENARIOS[name]
    t_start = time.time()
    S0, K, Q, V, D, Bt = make_inputs(p, H, T)
    out = []
    w = out.append
    w("=" * 118)
    w(f"SCENARIO {name}: {p['note']}")
    w(f"  heads {H}, tokens per chain {T}, state {DK} x {DV}; outputs compared per chain: {H * T * DV}")

    O_ref, S_ref, snaps8 = token_form_f32(S0, K, Q, V, D, Bt)
    O64, S64, snaps64 = token_form_f64(S0, K, Q, V, D, Bt)
    kn = np.sqrt((K.astype(f64) ** 2).sum(-1))
    gram1 = np.abs((K[:, 1:].astype(f64) * K[:, :-1].astype(f64)).sum(-1))
    w(f"  magnitudes (token form, FP32): |o| max {np.abs(O_ref).max():.6e} rms {np.sqrt(np.mean(O_ref.astype(f64)**2)):.6e}"
      f" | |S_final| max {np.abs(S_ref).max():.6e} rms {np.sqrt(np.mean(S_ref.astype(f64)**2)):.6e}")
    w(f"  key norm min {kn.min():.6f} max {kn.max():.6f}; |k_t . k_(t-1)| mean {gram1.mean():.4f} max {gram1.max():.4f}")
    smax_all = max(float(np.abs(s).max()) for s in snaps8)
    w(f"  |S| max over all snapshots {smax_all:.6e}")

    # baseline: token form FP32 against the float64 oracle
    a, r, q = diff_stats(O_ref, O64)
    fb = flips(O_ref, O64.astype(f32))
    tot = fb[1]
    sa, sr, sq = diff_stats(S_ref, S64)
    w("  BASELINE token-form FP32 vs token-form float64 (free running, whole chain):")
    w(f"    outputs  max_abs {a:.6e}  max_rel {r:.6e}  rms_rel {q:.6e}  bf16 flips {flips_txt(fb)}")
    w(f"    state    max_abs {sa:.6e}  max_rel {sr:.6e}  rms_rel {sq:.6e}")

    rows = {"base": dict(o_abs=a, s_abs=sa, flips=fb, omax=float(np.abs(O_ref).max()), smax=smax_all,
                         orms=float(np.sqrt(np.mean(O_ref.astype(f64) ** 2))))}
    for C in CHUNKS:
        nb = T // C
        ref_ends = [snaps8[(j + 1) * C // 8 - 1] for j in range(nb)]
        ref_starts = [S0] + ref_ends[:-1]
        ref64_ends = [snaps64[(j + 1) * C // 8 - 1] for j in range(nb)]
        # float64 block vs float64 token: the algebra
        Ob, Sb, snb = block_form(S0, K, Q, V, D, Bt, C, "f64")
        a, r, q = diff_stats(Ob, O64)
        sa, sr, sq = diff_stats(Sb, S64)
        sall = max(float(np.abs(x - y).max()) for x, y in zip(snb, ref64_ends))
        rows[(C, "f64")] = dict(o=(a, r, q), s=(sa, sr, sq), sall=sall,
                                gam_min=None)
        # token form F11-style
        tmo, tms = oracle_restart(ref_starts, ref_ends, O_ref, K, Q, V, D, Bt, C)
        rows[(C, "token")] = dict(f11=(tmo, tms))
        for mode in ("f32", "split3", "split2"):
            Ob, Sb, snb = block_form(S0, K, Q, V, D, Bt, C, mode)
            finite = bool(np.isfinite(Ob).all() and np.isfinite(Sb).all())
            a, r, q = diff_stats(Ob, O_ref)
            fl = flips(Ob, O_ref) if finite else (-1, O_ref.size, -1, -1, 0, -1)
            sa, sr, sq = diff_stats(Sb, S_ref)
            sall = max(float(np.abs(x.astype(f64) - y.astype(f64)).max())
                       for x, y in zip(snb, ref_ends)) if finite else float("nan")
            q1 = float(np.abs(Ob[:, :128].astype(f64) - O_ref[:, :128].astype(f64)).max())
            q4 = float(np.abs(Ob[:, -128:].astype(f64) - O_ref[:, -128:].astype(f64)).max())
            oa, orl, oq = diff_stats(Ob, O64)
            n64 = flips(Ob, O64.astype(f32))[0] if finite else -1
            osa, _, _ = diff_stats(Sb, S64)
            fo, fs = oracle_restart([S0] + snb[:-1], snb, Ob, K, Q, V, D, Bt, C)
            rows[(C, mode)] = dict(finite=finite, o=(a, r, q), fl=fl, s=(sa, sr, sq),
                                   sall=sall, q1=q1, q4=q4, orc=(oa, osa, n64), f11=(fo, fs))

    w("  (a) ALGEBRA, float64 block form vs float64 token form:")
    w("      C   | out max_abs   out max_rel   | state max_abs  state max_rel | state max_abs, all chunk ends")
    for C in CHUNKS:
        x = rows[(C, "f64")]
        w(f"      {C:<3d} | {x['o'][0]:.6e}  {x['o'][1]:.6e}  | {x['s'][0]:.6e}   {x['s'][1]:.6e}  | {x['sall']:.6e}")

    label = {"f32": "(a,b) block FP32 (fma chains)", "split3": "(c) block, 3 bf16 pieces (AMX-style)",
             "split2": "(d) block, 2 bf16 pieces (hi+mid)"}
    for mode in ("f32", "split3", "split2"):
        w(f"  {label[mode]} vs token-form FP32, whole {T}-token chain:")
        w("      C   | out max_abs   out max_rel   out rms_rel   | bf16 flips: all outputs; outputs above 1 % of rms | "
          "final-state max_abs  max_rel       rms_rel      | state max_abs all chunk ends | out max_abs tokens 0-127 / last 128")
        for C in CHUNKS:
            x = rows[(C, mode)]
            w(f"      {C:<3d} | {x['o'][0]:.6e}  {x['o'][1]:.6e}  {x['o'][2]:.6e}  | "
              f"{flips_txt(x['fl'])} | "
              f"{x['s'][0]:.6e}         {x['s'][1]:.6e}  {x['s'][2]:.6e} | {x['sall']:.6e}                | "
              f"{x['q1']:.6e} / {x['q4']:.6e}" + ("" if x["finite"] else "   NON-FINITE VALUES"))

    w("  DISTANCE TO THE float64 ORACLE (free running, whole chain): out max_abs | final-state max_abs | bf16 flips vs oracle")
    a, _, _ = diff_stats(O_ref, O64)
    sa, _, _ = diff_stats(S_ref, S64)
    n = flips(O_ref, O64.astype(f32))[0]
    w(f"      token form FP32      | {a:.6e} | {sa:.6e} | {n} of {tot}")
    for C in CHUNKS:
        for mode in ("f32", "split3", "split2"):
            x = rows[(C, mode)]
            w(f"      C={C:<3d} {mode:<6s}         | {x['orc'][0]:.6e} | {x['orc'][1]:.6e} | {x['orc'][2]} of {tot}")

    w(f"  (e) F11-STYLE error: float64 oracle restarted at each chunk start from the form's own FP32 state; tolerance {F11_TOL:.0e}")
    w("      C   | token form: out, state        | block FP32: out, state        | 3 pieces: out, state          | 2 pieces: out, state")
    for C in CHUNKS:
        t_ = rows[(C, "token")]["f11"]
        cells = [f"{t_[0]:.6e} {t_[1]:.6e}"]
        for mode in ("f32", "split3", "split2"):
            v = rows[(C, mode)]["f11"]
            cells.append(f"{v[0]:.6e} {v[1]:.6e}")
        w(f"      {C:<3d} | " + " | ".join(cells))
    worst = {m: max(max(rows[(C, m)]["f11"]) for C in CHUNKS) for m in ("token", "f32", "split3", "split2")}
    w("      worst over C: " + ", ".join(f"{m} {v:.6e} ({'PASS' if v <= F11_TOL else 'FAIL'} at 1e-7)"
                                         for m, v in worst.items()))

    if name == "underflow":
        w("  (f) GAMMA UNDERFLOW inside one chunk:")
        tiny32 = float(np.finfo(f32).tiny)
        for C in CHUNKS:
            gam = np.cumprod(D[:, :T].reshape(H, T // C, C).astype(f32), axis=2, dtype=f32)
            gam64 = np.cumprod(D[:, :T].reshape(H, T // C, C).astype(f64), axis=2)
            nzero = int((gam == 0).sum())
            nsub = int(((gam != 0) & (np.abs(gam) < tiny32)).sum())
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                gdiv = gam[:, :, :, None] / gam[:, :, None, :]
            tri = np.tril(np.ones((C, C), bool))
            bad = int((~np.isfinite(gdiv[:, :, tri])).sum())
            w(f"      C={C:<3d} FP32 gamma at chunk end: min {gam[:, :, -1].min():.6e} (float64 value {gam64[:, :, -1].min():.6e}); "
              f"gamma entries exactly 0: {nzero}, subnormal: {nsub}, of {gam.size}; "
              f"gamma_t/gamma_u entries not finite: {bad} of {int(tri.sum()) * H * (T // C)}")
        for C in (64, 128):
            for mode in ("f32", "split3"):
                with np.errstate(all="ignore"):
                    Ob, Sb, _ = block_form(S0, K, Q, V, D, Bt, C, mode, ratio="div")
                    okm = np.isfinite(Ob)
                    dfin = float(np.abs(Ob.astype(f64) - O_ref.astype(f64))[okm].max()) if okm.any() else float("nan")
                    nfl = int((bf16_bits(Ob) != bf16_bits(O_ref))[okm].sum())
                w(f"      C={C:<3d} {mode:<6s} with ratios built by DIVISION: non-finite outputs "
                  f"{int((~okm).sum())} of {Ob.size}, non-finite final-state values "
                  f"{int((~np.isfinite(Sb)).sum())} of {Sb.size}; among the finite outputs: max abs diff vs token form "
                  f"{dfin:.6e}, bf16 words that differ {nfl} of {int(okm.sum())}")
        w("      with ratios built by PRODUCTS (the tables above): every value finite = "
          + str(all(rows[(C, m)]["finite"] for C in CHUNKS for m in ("f32", "split3", "split2"))))

    if name == "normal":
        C = 32
        Ob, Sb, _ = block_form(S0, K, Q, V, D, Bt, C, "split3", piece_order="large_first")
        a, r, q = diff_stats(Ob, O_ref)
        fo_ = flips(Ob, O_ref)
        sa, sr, sq = diff_stats(Sb, S_ref)
        w(f"  ORDER SENSITIVITY (C=32, 3 pieces, pieces added hi -> mid -> lo instead of lo -> mid -> hi) vs token form:")
        w(f"      out max_abs {a:.6e} max_rel {r:.6e} rms_rel {q:.6e} | bf16 flips {flips_txt(fo_)} | final-state max_abs {sa:.6e}")

    w(f"  [scenario wall time {time.time() - t_start:.1f} s]")
    return name, "\n".join(out), rows


# --------------------------------------------------------------------------
# self tests of the helpers
# --------------------------------------------------------------------------
def exact_round_f32(v):
    """Correctly rounded float32 of a Fraction."""
    c = np.float32(float(v))
    cands = {float(c), float(np.nextafter(c, f32(np.inf))), float(np.nextafter(c, f32(-np.inf)))}
    best = None
    for x in cands:
        if not math.isfinite(x):
            continue
        dist = abs(Fraction(x) - v)
        even = (int(np.array(x, f32).view(np.uint32)) & 1) == 0
        key = (dist, 0 if even else 1)
        if best is None or key < best[0]:
            best = (key, x)
    return best[1]


def self_tests():
    print("SELF TESTS OF THE HELPERS")
    ok_all = True
    # bf16 rounding against literals of t/t_gated_delta_net.cpp:157-205
    src = bits32([0xBFDB94A6, 0x3F80F60E, 0x3FA57E16, 0xBE57B897, 0x3F0F38EB, 0xBEC2325B, 0x3F0DF2F1,
                  0x3F83F4C4, 0xBF4E81AF, 0xBC38BBDE, 0xBD5F6017, 0x3F808000, 0x3F818000, 0x00000001,
                  0x007FFFFF, 0x80000001, 0x7F7FFFFF, 0x7F800000])
    exp = np.array([0xBFDC, 0x3F81, 0x3FA5, 0xBE58, 0x3F0F, 0xBEC2, 0x3F0E, 0x3F84, 0xBF4F, 0xBC39,
                    0xBD5F, 0x3F80, 0x3F82, 0x0000, 0x0000, 0x8000, 0x7F80, 0x7F80], np.uint32)
    ok = bool((bf16_bits(src) == exp).all())
    ok_all &= ok
    print(f"  round_bf16 against 18 literal words (11 from the torch tables, 7 edge words): {'PASS' if ok else 'FAIL'}")
    # beta against torch_beta tables (t_gated_delta_net.cpp:230-233)
    bsrc = bits32([0xC0C10000, 0xBF810000, 0xBEA90000, 0xBE9B6000, 0x00000000, 0x3E940000, 0x3F820000, 0x40BF0000])
    bexp = np.array([0x3B1D, 0x3E89, 0x3ED6, 0x3EDA, 0x3F00, 0x3F12, 0x3F3C, 0x3F7F], np.uint32)
    ok = bool((gdn_beta(bsrc).view(np.uint32) >> 16 == bexp).all())
    ok_all &= ok
    print(f"  gdn_beta against the 8 torch_beta words: {'PASS' if ok else 'FAIL'}")
    # normalization against torch_norm tables (16 wide) and torch_epsilon (128 wide)
    nsrc = bits32([0xBC5929CF, 0xBD1CCEFD, 0x3C7843DA, 0x3CCA0F23, 0x3A163A7B, 0x3BAB8F4F, 0xBBF9460E,
                   0x3C264788, 0x3CA996C9, 0xBB06BEC1, 0xBB3BBC5E, 0xBA10AA02, 0x3D06F51A, 0x3AFD8ACB,
                   0x3BD423CB, 0xBC654D70])
    nexp = np.array([0xBE4C, 0xBF14, 0x3E69, 0x3EBE, 0x3C0D, 0x3DA2, 0xBDEA, 0x3E1C, 0x3EA0, 0xBCFE,
                     0xBD31, 0xBC09, 0x3EFE, 0x3CEF, 0x3DC8, 0xBE58], np.uint32)
    ok = bool((normalize_gdn(nsrc).view(np.uint32) >> 16 == nexp).all())
    ok &= bool((normalize_gdn(nsrc[::-1].copy()).view(np.uint32) >> 16 == nexp[::-1]).all())
    esrc = bits32([0xB6BA7FFF, 0xB7CF7FFF])
    eexp = np.array([0xBBB3, 0xBCC7], np.uint32)
    q = np.array([esrc[i % 2] for i in range(128)], f32)
    ok &= bool((normalize_gdn(q).view(np.uint32) >> 16 == np.array([eexp[i % 2] for i in range(128)])).all())
    ok_all &= ok
    print(f"  normalize_gdn against torch_norm (16 words, both orders) and torch_epsilon (128 words): {'PASS' if ok else 'FAIL'}")
    # fma emulation against exact rational arithmetic
    rng = np.random.default_rng(7)
    n = 20000
    a = (rng.standard_normal(n) * np.exp(rng.uniform(-20, 20, n))).astype(f32)
    b = (rng.standard_normal(n) * np.exp(rng.uniform(-20, 20, n))).astype(f32)
    c = (rng.standard_normal(n) * np.exp(rng.uniform(-20, 20, n))).astype(f32)
    c[: n // 2] = (-(a[: n // 2].astype(f64) * b[: n // 2].astype(f64)) * (1 + rng.uniform(-1e-6, 1e-6, n // 2))).astype(f32)
    # double-rounding traps: a*b lands exactly on a float32 tie, c is far below
    ta = np.full(2000, 1.0 + 2.0 ** -12, f32)
    tb = np.full(2000, 1.0 + 2.0 ** -12, f32)
    tc = (rng.choice([-1.0, 1.0], 2000) * 2.0 ** rng.integers(-100, -40, 2000)).astype(f32)
    a, b, c = np.concatenate([a, ta]), np.concatenate([b, tb]), np.concatenate([c, tc])
    got = fma32(a, b, c)
    naive = (a.astype(f64) * b.astype(f64) + c.astype(f64)).astype(f32)
    bad = 0
    naive_bad = 0
    for i in range(a.size):
        want = exact_round_f32(Fraction(float(a[i])) * Fraction(float(b[i])) + Fraction(float(c[i])))
        bad += float(got[i]) != want
        naive_bad += float(naive[i]) != want
    ok = bad == 0
    ok_all &= ok
    print(f"  fma32 against exact rational arithmetic, {a.size} triples (2000 double-rounding traps): "
          f"{bad} wrong ({'PASS' if ok else 'FAIL'}); the naive float64 route gets {naive_bad} wrong")
    # tile product: products are exact, and the result is close to float64 matmul
    A = round_bf16(rng.standard_normal((2, 16, 128)).astype(f32))
    X = (rng.standard_normal((2, 128, 128)) * 0.01).astype(f32)
    P = split_bf16(X, 3)
    exact_prod = all(bool(((A[:, :, :, None] * p[:, None, :, :]).astype(f64) ==
                           A[:, :, :, None].astype(f64) * p[:, None, :, :].astype(f64)).all()) for p in P)
    ref = A.astype(f64) @ X.astype(f64)
    e3 = np.abs(tdp_mm(A, P).astype(f64) - ref).max()
    e2 = np.abs(tdp_mm(A, split_bf16(X, 2)).astype(f64) - ref).max()
    e1 = np.abs(tdp_mm(A, [round_bf16(X)]).astype(f64) - ref).max()
    ef = np.abs(mm_fma(A, X).astype(f64) - ref).max()
    ok_all &= exact_prod
    print(f"  tile product: every bf16 x bf16 product exact in FP32: {'PASS' if exact_prod else 'FAIL'}")
    print(f"  K*S (16 x 128 times 128 x 128, |S| about 0.01, |result| max {np.abs(ref).max():.6e}) max abs error vs float64:")
    print(f"      FP32 fma chain {ef:.6e} | 3 pieces {e3:.6e} | 2 pieces {e2:.6e} | 1 piece (plain bf16 state) {e1:.6e}")
    return ok_all


# --------------------------------------------------------------------------
# check of the three-way split on raw float32 values
# --------------------------------------------------------------------------
def split_check_block(u):
    """u: uint32 bit patterns. Returns per-pattern failure flags."""
    x = u.view(f32)
    finite = (u & np.uint32(0x7F800000)) != np.uint32(0x7F800000)
    with np.errstate(invalid="ignore", over="ignore"):
        hi = round_bf16(x)
        r1 = x - hi
        mid = round_bf16(r1)
        lo = r1 - mid  # raw remainder, NOT rounded
        total = hi.astype(f64) + mid.astype(f64) + lo.astype(f64)
        two = hi.astype(f64) + mid.astype(f64)
    hi_inf = finite & ~np.isfinite(hi)
    with np.errstate(invalid="ignore"):
        sum_bad = finite & ~(total == x.astype(f64))
    lob = lo.view(np.uint32)
    lo_not_bf16 = finite & ((lob & np.uint32(0xFFFF)) != 0)

    def subn(v):
        b = v.view(np.uint32)
        return ((b & np.uint32(0x7F800000)) == 0) & ((b & np.uint32(0x007FFFFF)) != 0)

    piece_subnormal = finite & (subn(hi) | subn(mid) | subn(lo))
    ef = (u >> np.uint32(23)) & np.uint32(0xFF)
    clean = finite & (ef >= 24) & (ef <= 253)  # exponent fields where the 3-way split is exact
    with np.errstate(invalid="ignore", divide="ignore"):
        rel2 = np.where(clean, np.abs((x.astype(f64) - two) / x.astype(f64)), 0.0)
    return finite, hi_inf, sum_bad, lo_not_bf16, piece_subnormal, rel2


def split_tests():
    print("=" * 118)
    print("THREE-WAY SPLIT  x = hi + mid + lo,  hi = bf16(x), mid = bf16(x - hi), lo = x - hi - mid   (float32 arithmetic)")
    rng = np.random.default_rng(12345)
    names = ["hi overflows to inf", "hi+mid+lo != x", "lo not bf16-representable", "a piece is subnormal (TDPBF16PS reads it as 0)"]

    def run(label, u_all, per_exp=None):
        nfin, f, r2 = 0, [0, 0, 0, 0], 0.0
        for s0 in range(0, u_all.size, 1 << 20):  # slices that stay in cache
            u = np.ascontiguousarray(u_all[s0:s0 + (1 << 20)])
            fin, a, b, c, d, rel2 = split_check_block(u)
            if per_exp is not None:
                e = ((u >> np.uint32(23)) & np.uint32(0xFF)).astype(np.int64)
                for k, flag in enumerate((a, b, c, d)):
                    per_exp[k] += np.bincount(e[flag], minlength=256)
                per_exp[4] += np.bincount(e[fin], minlength=256)
            nfin += int(fin.sum())
            f = [x + int(y.sum()) for x, y in zip(f, (a, b, c, d))]
            r2 = max(r2, float(rel2.max()))
        return nfin, f, r2

    # 1. uniform random bit patterns: every exponent field equally likely
    per_exp = [np.zeros(256, np.int64) for _ in range(5)]
    tot = 0
    fails = [0, 0, 0, 0]
    rel2max = 0.0
    n_rand = 0
    for _ in range(16):
        u = rng.integers(0, 2 ** 32, 4_000_000, dtype=np.uint64).astype(np.uint32)
        n_rand += u.size
        n, f, r2 = run("rand", u, per_exp)
        tot += n
        fails = [x + y for x, y in zip(fails, f)]
        rel2max = max(rel2max, r2)
    print(f"  1. {n_rand} uniform random bit patterns ({tot} finite; the rest are inf/NaN and skipped):")
    for nm, f in zip(names, fails):
        print(f"       {nm}: {f}")
    for k, nm in enumerate(names):
        idx = np.nonzero(per_exp[k])[0]
        if idx.size:
            print(f"       '{nm}' occurs only for exponent fields {idx.min()}..{idx.max()} "
                  f"(|x| from {float(bits32(np.uint32(max(idx.min(), 0)) << 23)):.6e} "
                  f"to below {float(bits32(np.uint32(min(idx.max() + 1, 255)) << 23)):.6e})")
    clean = [e for e in range(1, 255) if all(per_exp[k][e] == 0 for k in range(4))]
    print(f"       exponent fields with zero failures of any kind: {clean[0]}..{clean[-1]} "
          f"(|x| from {float(bits32(np.uint32(clean[0]) << 23)):.6e} to below {float(bits32(np.uint32(clean[-1] + 1) << 23)):.6e}), contiguous: {clean == list(range(clean[0], clean[-1] + 1))}")
    print(f"       two-way split (hi + mid only), exponent fields 24..253: max |x - hi - mid| / |x| = {rel2max:.6e}  (2^-16 = {2.0**-16:.6e})")

    # 2. exhaustive: all 2^23 mantissas, both signs, for chosen exponent fields
    mant = np.arange(2 ** 23, dtype=np.uint32)
    ex_fields = [127, 120, 100, 60, 40, 30, 26, 25, 24, 23, 22, 17, 16, 10, 9, 8, 2, 1, 0, 200, 253, 254]
    print(f"  2. exhaustive over all 2^23 mantissas x 2 signs for {len(ex_fields)} exponent fields "
          f"({len(ex_fields) * 2 * 2**23} values):")
    print("       exp field | binade starts at | hi inf | sum != x | lo not bf16 | piece subnormal")
    total_ex = 0
    for e in ex_fields:
        f = [0, 0, 0, 0]
        for sign in (0, 1):
            u = (np.uint32(sign) << np.uint32(31)) | (np.uint32(e) << np.uint32(23)) | mant
            n, ff, _ = run("ex", u)
            total_ex += n
            f = [x + y for x, y in zip(f, ff)]
        lo_edge = float(bits32(np.uint32(e) << 23)) if e > 0 else 0.0
        print(f"       {e:>9d} | {lo_edge:.6e}     | {f[0]:>6d} | {f[1]:>8d} | {f[2]:>11d} | {f[3]:>8d}")
    # 3. edge cases for every exponent field
    lows = np.array([0x0000, 0x0001, 0x007F, 0x0080, 0x0081, 0x00FF, 0x0100, 0x0180, 0x0280, 0x4080,
                     0x7F7F, 0x7F80, 0x7F81, 0x7FFF, 0x8000, 0x8001, 0x807F, 0x8080, 0x8081, 0x80FF,
                     0xC080, 0xFF7F, 0xFF80, 0xFF81, 0xFFFF, 0x8100, 0x7F00], np.uint32)
    his = np.arange(128, dtype=np.uint32) << np.uint32(16)
    ee = np.arange(1, 255, dtype=np.uint32) << np.uint32(23)
    u = (ee[:, None, None] | his[None, :, None] | lows[None, None, :]).ravel()
    u = np.concatenate([u, u | np.uint32(0x80000000)])
    fin, a, b, c, d, _ = split_check_block(u)
    e = ((u >> np.uint32(23)) & np.uint32(0xFF)).astype(np.int64)
    print(f"  3. edge patterns for every normal exponent field 1..254: all 128 retained mantissas x {lows.size} low-16-bit "
          f"patterns (ties 0x8000, second-level ties 0x..80, neighbours of powers of two) x 2 signs = {u.size} values:")
    for nm, flag in zip(names, (a, b, c, d)):
        ex = e[flag]
        rng_txt = f"exponent fields {ex.min()}..{ex.max()}" if ex.size else "none"
        print(f"       {nm}: {int(flag.sum())} ({rng_txt})")
    mid_band = (e >= 24) & (e <= 253)
    print(f"       failures of any kind for exponent fields 24..253: {int((a | b | c | d)[mid_band].sum())} of {int(mid_band.sum())}")
    # 4. tiny and large
    sub = np.concatenate([np.arange(1, 2 ** 23, 7, dtype=np.uint32)])
    fin, a, b, c, d, _ = split_check_block(sub)
    print(f"  4. FP32 subnormals ({sub.size} values): hi = mid = 0 for all: "
          f"{bool((round_bf16(sub.view(f32)) == 0).all())}; lo not bf16-representable: {int(c.sum())}; lo subnormal: {int(d.sum())}")
    big = np.arange(0x7F7F0000, 0x7F800000, dtype=np.uint32)
    fin, a, b, c, d, _ = split_check_block(big)
    first_bad = big[a][0] if a.any() else None
    print(f"     largest binade top ({big.size} values from 0x7f7f0000): hi overflows to inf for {int(a.sum())} values"
          + (f", first at bit pattern 0x{int(first_bad):08x} = {float(bits32(first_bad)):.9e}" if first_bad is not None else ""))
    print(f"     totals checked: random {n_rand}, exhaustive {total_ex}, edge {u.size}, subnormal {sub.size}, top {big.size}")


# --------------------------------------------------------------------------
# the PyTorch-literal test of t/t_gated_delta_net.cpp:720-783, reproduced
# --------------------------------------------------------------------------
def tv(index, salt, scale):
    """recurrence_test_value, t/t_gated_delta_net.cpp:55-58."""
    index = np.asarray(index, np.int64)
    centered = ((index * 29 + salt * 17) % 47) - 23
    return centered.astype(f32) * f32(scale)


def torch_literal_test():
    print("=" * 118)
    print("(e1) THE TEST 'recurrence matches PyTorch literals at the Qwen head width' (t/t_gated_delta_net.cpp:720-783), reproduced")
    out_idx = [0, 1, 17, 63, 127, 128, 145, 255]
    st_idx = [(0, 0, 0), (0, 17, 63), (0, 127, 127), (1, 0, 127), (1, 63, 17), (1, 127, 0)]
    t_out = np.array([[0.00087535847, 0.000047066962, -0.00025644459, 0.00042827096, -0.00064919307,
                       0.00045332118, -0.00015550695, -0.00037600446],
                      [-0.0022180416, 0.00090248784, 0.0020263176, -0.0012328973, 0.0030584019,
                       -0.0020030176, 0.0029436699, 0.004234735]], f32)
    t_st = np.array([[0.0059774681, 0.00036260593, 0.003035421, -0.0030345041, -0.0015512522, -0.00086717296],
                     [0.0025854968, 0.0003074088, 0.0030644191, 0.0077428417, -0.0090234084, -0.0010860839]], f32)
    H, T = 2, 2
    idx = np.arange(H * DK * DV).reshape(H, DK, DV)
    S0 = tv(idx, 3, 0.00015)
    A_exp = np.array([0.45, 0.52], f32)
    dt_bias = np.array([-0.18, -0.13], f32)
    K = np.empty((H, T, DK), f32)
    Q = np.empty((H, T, DK), f32)
    V = np.empty((H, T, DV), f32)
    D = np.empty((H, T), f32)
    Bt = np.empty((H, T), f32)
    for s in range(T):
        qn = normalize_gdn(tv(np.arange(DK), 5 + 2 * s, 0.012))
        kn = normalize_gdn(tv(np.arange(DK), 11 + 3 * s, 0.009))
        Q[:, s] = qn
        K[:, s] = kn
        V[:, s] = round_bf16(tv(np.arange(H * DV), 19 + 5 * s, 0.006)).reshape(H, DV)
        D[:, s] = gdn_decay(tv(np.arange(H), 23 + s, 0.025), A_exp, dt_bias)
        Bt[:, s] = gdn_beta(tv(np.arange(H), 29 + 2 * s, 0.035))
    print(f"  decay per value head: step 0 {D[:, 0].tolist()}, step 1 {D[:, 1].tolist()}; beta: {Bt[:, 0].tolist()}, {Bt[:, 1].tolist()}")

    def pick_o(O):
        return np.array([[O[i // DV, s, i % DV] for i in out_idx] for s in range(T)], f64)

    def pick_s(S):
        return np.array([S[a, b, c] for a, b, c in st_idx], f64)

    O_ref, S_ref, sn = token_form_f32(S0, K, Q, V, D, Bt, snap_every=1)
    eo = np.abs(pick_o(O_ref) - t_out.astype(f64)).max()
    es = max(np.abs(pick_s(sn[s]) - t_st[s].astype(f64)).max() for s in range(T))
    print(f"  torch literal magnitudes: |output| {np.abs(t_out).min():.6e} .. {np.abs(t_out).max():.6e}; |state| {np.abs(t_st).min():.6e} .. {np.abs(t_st).max():.6e}")
    print(f"  token form (this script) vs torch literals: outputs (16 values) max abs {eo:.6e}; states (12 values) max abs {es:.6e}; "
          f"tolerance 1e-7: {'PASS' if max(eo, es) <= F11_TOL else 'FAIL'}")
    res = {"token": max(eo, es)}
    for mode in ("f32", "split3", "split2"):
        for C in (1, 2):
            O, S, snb = block_form(S0, K, Q, V, D, Bt, C, mode)
            eo = np.abs(pick_o(O) - t_out.astype(f64)).max()
            if C == 1:
                es = max(np.abs(pick_s(snb[s]) - t_st[s].astype(f64)).max() for s in range(T))
                stxt = "states after both steps (12 values)"
            else:
                es = np.abs(pick_s(S) - t_st[1].astype(f64)).max()
                stxt = "state after step 2 only (6 values; the block form has no state after step 1)"
            n, tot = flips(O, O_ref)[:2]
            dm = np.abs(O.astype(f64) - O_ref.astype(f64)).max()
            dsm = np.abs(S.astype(f64) - S_ref.astype(f64)).max()
            res[(mode, C)] = max(eo, es)
            print(f"  block {mode:<6s} C={C} vs torch literals: outputs max abs {eo:.6e}; {stxt} max abs {es:.6e}; "
                  f"1e-7: {'PASS' if max(eo, es) <= F11_TOL else 'FAIL'} | vs token form over all 512 outputs: max abs {dm:.6e}, "
                  f"bf16 flips {n} of {tot}; all 32768 final-state values: max abs {dsm:.6e}")
    return res


def short_chain_from_zero():
    """The situation of the one bit-pinned test (F11): a chain of 4 tokens from a
    zero state, bf16 words of the 4th token's recurrence output."""
    print("=" * 118)
    print("BIT-PIN SITUATION (extra): chain of 4 tokens from a ZERO state; bf16 words of the 4th token's recurrence output;")
    print("  block form with C=4 against the token form; 128 x 128 heads (the pinned test uses 16 x 80 heads), inputs as scenario testmag")
    H, T, batches = 512, 4, 4
    tally = {m: [0, 0, 0, 0.0] for m in ("f32", "split3", "split2")}  # words differ, words, heads, max diff
    for batch in range(batches):
        p = dict(SCENARIOS["testmag"])
        p["seed"] = 606 + batch
        S0, K, Q, V, D, Bt = make_inputs(p, H, T)
        S0 = np.zeros_like(S0)
        O_ref, S_ref, _ = token_form_f32(S0, K, Q, V, D, Bt, snap_every=4)
        for mode in tally:
            O, S, _ = block_form(S0, K, Q, V, D, Bt, 4, mode)
            ne = bf16_bits(O[:, 3]) != bf16_bits(O_ref[:, 3])
            t = tally[mode]
            t[0] += int(ne.sum())
            t[1] += int(ne.size)
            t[2] += int(ne.any(axis=1).sum())
            t[3] = max(t[3], float(np.abs(O[:, 3].astype(f64) - O_ref[:, 3].astype(f64)).max()))
    for mode, t in tally.items():
        rate = t[0] / t[1]
        print(f"  block {mode:<6s}: 4th-token words that differ {t[0]} of {t[1]} (rate {rate:.6e}); heads with at least one "
              f"differing word {t[2]} of {H * batches}; max abs output diff {t[3]:.6e}; "
              f"est. chance that 320 words all match = (1 - rate)^320 = {(1.0 - rate) ** 320:.4f}")


def op_counts():
    print("=" * 118)
    print("OPERATION COUNTS per value head (128 x 128 state), from the structure of the two forms (arithmetic, not a timing)")
    print("  token form, per token: FP32 fma 49152, FP32 mul 32768; state passes: 2 reads + 1 write of 65536 bytes per token")
    print("  C   | block FP32 multiply-adds per token (3 big products + 2 Gram + 2 triangular) | TDPBF16PS per token with 3 pieces"
          " (K*S0, Q*S0, K^T*(w*Delta), 2 Gram) | state passes per chunk")
    for C in CHUNKS:
        big = 3 * C * DK * DV
        gram = 2 * C * C * DK
        tri = (C * (C - 1) // 2 + C * (C + 1) // 2) * DV
        mac = (big + gram + tri) / C
        rows16 = math.ceil(C / 16)
        t_ks = 3 * rows16 * (DK // 32) * (DV // 16)          # per product, 3 pieces
        t_upd = 3 * (DK // 16) * (DV // 16) * math.ceil(C / 32)
        t_gram = 2 * rows16 * (DK // 32) * math.ceil(C / 16)
        tot = 2 * t_ks + t_upd + t_gram
        print(f"  {C:<3d} | {mac:>10.0f} = {big // C} + {gram // C} + {tri // C}"
              f"                                   | {tot / C:>8.2f} ({2 * t_ks} + {t_upd} + {t_gram} per chunk)"
              f"                          | 2 reads + 1 write per {C} tokens")


def ulp32(x):
    """Spacing of float32 values at magnitude x."""
    return float(np.spacing(f32(abs(x))))


def check_summary(results):
    """One line per scenario and form, with the pass rules stated here:
      algebra     float64 block vs float64 token: max abs diff <= 1e-12 x largest magnitude
      accuracy    free-running distance to the float64 oracle (outputs and final state)
                  is at most 2 x the token form's own distance
      bit-equal   zero bf16 output words differ from the token form
      F11         F11-style error (oracle restarted per chunk) <= 1e-7
      finite      no inf or NaN"""
    print("=" * 118)
    print("CHECK SUMMARY (worst value over C = 8, 16, 32, 64, 128)")
    print("  pass rules: algebra = float64 diff <= 1e-12 x largest magnitude; accuracy = distance to the float64 oracle at most")
    print("  2 x the token form's own distance (outputs and final state); bit-equal = 0 bf16 words differ; F11 = error <= 1e-7")
    names = {"f32": "block FP32", "split3": "3 pieces", "split2": "2 pieces"}
    for name, _, rows in results:
        base = rows["base"]
        a64o = max(rows[(C, "f64")]["o"][0] for C in CHUNKS)
        a64s = max(rows[(C, "f64")]["sall"] for C in CHUNKS)
        ok64 = a64o <= 1e-12 * base["omax"] and a64s <= 1e-12 * base["smax"]
        print(f"  {name}: largest |o| {base['omax']:.6e} (FP32 spacing {ulp32(base['omax']):.3e}), largest |S| {base['smax']:.6e} "
              f"(FP32 spacing {ulp32(base['smax']):.3e})")
        print(f"    algebra float64: out max_abs {a64o:.6e}, state max_abs {a64s:.6e}: {'PASS' if ok64 else 'FAIL'}")
        tf11 = max(max(rows[(C, 'token')]['f11']) for C in CHUNKS)
        print(f"    token form itself: distance to oracle out {base['o_abs']:.6e}, state {base['s_abs']:.6e}; "
              f"bf16 words that differ from the oracle {base['flips'][0]} of {base['flips'][1]}; F11-style {tf11:.6e} "
              f"{'PASS' if tf11 <= F11_TOL else 'FAIL'}")
        for mode in ("f32", "split3", "split2"):
            R = [rows[(C, mode)] for C in CHUNKS]
            finite = all(r["finite"] for r in R)
            o_abs = max(r["o"][0] for r in R)
            s_abs = max(r["sall"] for r in R)
            fmin = min(r["fl"][0] for r in R)
            fmax = max(r["fl"][0] for r in R)
            tot = R[0]["fl"][1]
            bmin = min(r["fl"][3] for r in R)
            bmax = max(r["fl"][3] for r in R)
            do = max(r["orc"][0] for r in R)
            ds = max(r["orc"][1] for r in R)
            f11 = max(max(r["f11"]) for r in R)
            acc = do <= 2 * base["o_abs"] and ds <= 2 * base["s_abs"]
            print(f"    {names[mode]:<10s} vs token form: out max_abs {o_abs:.6e} ({o_abs / ulp32(base['omax']):.1f} spacings), "
                  f"state max_abs {s_abs:.6e} ({s_abs / ulp32(base['smax']):.1f} spacings); "
                  f"bf16 words that differ {fmin}..{fmax} of {tot} ({100.0 * fmin / tot:.4f} %..{100.0 * fmax / tot:.4f} %), "
                  f"above 1 % of rms {bmin}..{bmax}")
            print(f"    {'':<10s} distance to oracle: out {do:.6e} ({do / base['o_abs']:.2f} x token form), "
                  f"state {ds:.6e} ({ds / base['s_abs']:.2f} x token form) | F11-style {f11:.6e}")
            print(f"    {'':<10s} finite {'PASS' if finite else 'FAIL'} | accuracy {'PASS' if acc else 'FAIL'} | "
                  f"bit-equal {'PASS' if fmax == 0 else 'FAIL'} | F11 {'PASS' if f11 <= F11_TOL else 'FAIL'}")


def main():
    H, T = 4, 1024
    names = list(SCENARIOS)
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        T = 128
    print(f"numpy {np.__version__}; chain length {T} tokens; heads per scenario {H}; query scale {float(SCALE32)!r}")
    t0 = time.time()

    def lap(what):
        nonlocal t0
        print(f"[{what}: {time.time() - t0:.1f} s]", file=sys.stderr, flush=True)
        t0 = time.time()

    ok = self_tests()
    print(f"  all helper self tests: {'PASS' if ok else 'FAIL'}")
    lap("self tests")
    split_tests()
    lap("split tests")
    torch_literal_test()
    short_chain_from_zero()
    op_counts()
    lap("literal test, short chain, op counts")
    sys.stdout.flush()
    with Pool(len(names)) as pool:
        results = pool.map(run_scenario, [(n, H, T) for n in names])
    for name, text, rows in results:
        print(text)
    lap("scenarios")
    check_summary(results)
    print("=" * 118)
    print("DONE")


if __name__ == "__main__":
    main()
