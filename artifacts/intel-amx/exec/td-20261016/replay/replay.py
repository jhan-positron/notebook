#!/usr/bin/env python3
"""replay.py: offline numpy replay of tron's software attention on REAL logged Q/K/V
(issue #4444, td-20261016 campaign, qwen3-4b tp2, 1 user, prompt 1024 + 256 generated).

Each arithmetic path of tron is emulated in fp32 with the add ORDER of the kernel
(verified by the sibling kernel test exec/td-20261016/ktest/results.txt where noted):
  D  dotter<bf16,128>  (row-major AVX-512 path; h/tron/kernels/dotter.hpp:211-221)
     16 lanes x VDPBF16PS, odd-product-first, lanewise sum1 + sum2, halving reduce
     (ktest T3: 100 % bit-identical to this model).
  R  k_vnni::qk_group  (VNNI reader; h/tron/kernels/k_vnni.hpp:60-99)
     one sequential VDPBF16PS chain over the 64 dimension pairs (ktest T4: 100 %).
  A  AMX tile QK       (qk_vnni_128x4; src/tron/kernels/amx_attn.cpp:233-290)
     4 TDPBF16PS steps of 16 pairs. The hardware's internal order is NOT a simple fp32
     chain (ktest T5: best simple model 'step_exact_then_add' matches 79 %); this
     script models it as AMX_MODEL below and labels every A number as a model.
  PV AVX  scaled_v_expr (kv_cache.hpp:2961-2976): P TRUNCATED to bf16, VDPBF16PS over
     token pairs, odd token first (one chain per output dim).
  PV AMX  weights_times_v_128x4 (amx_attn.cpp:292-350): P RNE to bf16, 2 TDPBF16PS
     steps of 16 token pairs (modelled like A).
Shared epilogue (self_attention.hpp:2048-2069 and 1788-1823): s *= scale (fp32),
m_page = max(m*, max s), P = tron exp (fp32.hpp:925-937, emulated exactly incl. fma),
sum(P) in the expr.hpp:599 order, corr = expf(m*_old - m_page),
v* = bf16_rne(fma(v*, corr, PV))  <-- v* is STORED AS bf16 (dmatensor<bf16>) after every
page, s* = s* * corr + sum(P), output = bf16_rne(v* / s*).

Run on delphi-3bda:  nice -n10 taskset -c 72-143 python3 replay.py --qkv <extract.txt> ...
"""
import argparse
import json
import os
import re
import sys
import time
from fractions import Fraction

import numpy as np

# ------------------------------------------------------------------ parameters
LAYER = 0
PROMPT = 1024              # prompt tokens 0..1023; generated steps follow
PASS_TOKENS = 128          # prefill pass size (8 passes of 128)
PAGE = 64                  # KV page (tokens)
BLOCK = 16                 # VNNI K block (tokens)
HEAD = 128
N_Q_HEADS = 32
N_KV_HEADS = 8
KV_MUL = 4
# the attention scale the plugin passes (llama.hpp:326 form: 1.0f / sqrtf(head_size))
SCALE32 = np.float32(1.0) / np.sqrt(np.float32(HEAD))
SCALE64 = 1.0 / np.sqrt(128.0)
WITHIN_PAIR_ORDERS = ("odd_first", "even_first", "pair_sum_first")
WITHIN_PAIR_ORDER = "odd_first"       # ktest T0: VDPBF16PS = (acc + p_odd) + p_even, 100 %
AMX_MODELS = ("step_exact", "seq")
AMX_MODEL = "step_exact"              # per TDPBF16PS: exact sum of the 32 products, RNE, acc +
S_STAR_FMA = True                     # s* = s* * corr + sum: compilers contract this to one fma
FTZ = True                            # VDPBF16PS / TDPBF16PS flush denormal products and sums
# decode token at a page end (T % 64 == 63): row-major K (base): the page passes is_dense_amx_page and
# goes through the AMX kernels; VNNI K (new): its last block converts only at the forward end, so the
# page is still 'partial'. Measured: logged WO base vs poc differ exactly at tokens 1087, 1151, 1215.
OWN_PAGE_COMPLETE_IS_DENSE = {"rowmajor": True, "vnni": False}
DECODE_FULL_BLOCK_VNNI_SAME_FORWARD = False  # block completed by this very token: still row-major
# token sample: pass 0 (no AMX anywhere), pass 1 (pages 0,1 dense), decode steps
SAMPLE_TOKENS = list(range(0, 192)) + [1024, 1039, 1040, 1056, 1087, 1090, 1150, 1200, 1278]
BIAS_SCALING_TOKENS = [0, 15, 63, 127, 1087]   # 1, 16, 64, 128, 1088 attended tokens

f32 = np.float32
f64 = np.float64
u32 = np.uint32
MIN_NORMAL32 = f32(2.0 ** -126)

# ------------------------------------------------------------------ bf16 / fp32 helpers
def bf16_rne(x):
    x = np.asarray(x, dtype=f32)
    u = x.view(u32)
    r = ((u >> 16) & 1) + u32(0x7FFF)
    out = (((u + r) >> 16) << 16).view(f32)
    nan = np.isnan(x)
    if nan.any():
        out = out.copy()
        out[nan] = x[nan]
    return out


def bf16_trunc(x):
    x = np.asarray(x, dtype=f32)
    return (x.view(u32) & u32(0xFFFF0000)).view(f32)


def ftz(x):
    if not FTZ:
        return x
    return np.where(np.abs(x) < MIN_NORMAL32, f32(0.0), x).astype(f32)


def ulp_dist(a, b):
    def key(x):
        u = np.asarray(x, dtype=f32).view(np.int32).astype(np.int64)
        return np.where(u < 0, -(u & 0x7FFFFFFF), u)
    return np.abs(key(a) - key(b))


def _round_fraction_to_f32(fr):
    """Correctly rounded fp32 of an exact rational (RNE)."""
    d = float(fr)                      # RN53
    r = f32(d)
    # if d is exactly a fp32 midpoint, decide with the exact value
    db = np.array([d], dtype=f64).view(np.uint64)[0]
    if (db & ((1 << 29) - 1)) == (1 << 28):
        lo = np.nextafter(r, f32(-np.inf)) if Fraction(float(r)) > fr else r
        hi = np.nextafter(lo, f32(np.inf))
        if fr == Fraction(d):
            # true tie: ties-to-even on the fp32 mantissa
            if (np.array([lo]).view(u32)[0] & 1) == 0:
                return lo
            return hi
        return hi if fr > Fraction(d) else lo
    return r


def fma32(a, b, c):
    """fp32 fused multiply-add (one rounding), vectorized; exact fallback for double-rounding cases."""
    a64 = np.asarray(a, dtype=f64)
    b64 = np.asarray(b, dtype=f64)
    c64 = np.asarray(c, dtype=f64)
    t = a64 * b64 + c64                 # product exact in fp64; one rounding to 53 bits
    r = t.astype(f32)
    tb = np.ascontiguousarray(t).view(np.uint64)
    mid = ((tb & ((1 << 29) - 1)) == (1 << 28)) & np.isfinite(t) & (t != 0)
    sub = (np.abs(r) < MIN_NORMAL32) & (r != 0)
    bad = mid | sub
    if bad.any():
        r = r.copy()
        ab, bb, cb = np.broadcast_arrays(a64, b64, c64)
        for idx in zip(*np.nonzero(bad)):
            fr = Fraction(float(ab[idx])) * Fraction(float(bb[idx])) + Fraction(float(cb[idx]))
            r[idx] = _round_fraction_to_f32(fr)
    return r


# tron's vector exp (h/tron/simd/fp32.hpp:925-937), constants at fp32.hpp:831,846-851
EXP_MIN = f32(-88.3762626647949)
C_LOG2E = f32(1.4426950408889634)
C_LN2 = f32(0.6931471805599453)
E7 = [None, None, f32(0.5), f32(0.16666664183139801025390625), f32(4.16664592921733856201171875e-2),
      f32(8.333896286785602569580078125e-3), f32(1.39354146085679531097412109375e-3),
      f32(1.95693559362553060054779052734375e-4)]


def tron_exp(x):
    x = np.asarray(x, dtype=f32)
    kz = ~(x < EXP_MIN)                                   # _CMP_NLT_UQ
    xs = np.where(kz, x, f32(0.0)).astype(f32)            # keep -inf lanes finite for the math
    fx = np.floor(fma32(xs, C_LOG2E, f32(0.5))).astype(f32)
    xr = fma32(fx, -C_LN2, xs)
    x2 = (xr * xr).astype(f32)
    y = fma32(xr, E7[7], E7[6])
    y = fma32(y, x2, fma32(xr, E7[5], E7[4]))
    y = fma32(y, x2, fma32(xr, E7[3], E7[2]))
    y = fma32(y, x2, (xr + f32(1.0)).astype(f32))
    out = np.ldexp(y, fx.astype(np.int32)).astype(f32)    # vscalefps
    out[~kz] = f32(0.0)
    return out


def expf_scalar(x):
    return np.exp(np.asarray(x, dtype=f64)).astype(f32)


# ------------------------------------------------------------------ the dot-product orders
def dp(acc, pe, po, order):
    """One VDPBF16PS lane: acc + (even product, odd product) in the given order, fp32 RNE."""
    acc = np.asarray(acc, dtype=f32)
    if order == "odd_first":
        return ftz((ftz(acc + po) + pe).astype(f32))
    if order == "even_first":
        return ftz((ftz(acc + pe) + po).astype(f32))
    if order == "pair_sum_first":
        return ftz((acc + ftz((pe + po).astype(f32))).astype(f32))
    raise ValueError(order)


def score_D(prod, order):
    """dotter<bf16,128>: prod[..., 128] exact fp32 products -> fp32 score."""
    z = f32(0.0)
    s1 = dp(z, prod[..., 0:32:2], prod[..., 1:32:2], order)
    s1 = dp(s1, prod[..., 64:96:2], prod[..., 65:96:2], order)
    s2 = dp(z, prod[..., 32:64:2], prod[..., 33:64:2], order)
    s2 = dp(s2, prod[..., 96:128:2], prod[..., 97:128:2], order)
    t = (s1 + s2).astype(f32)
    a = (t[..., 0:8] + t[..., 8:16]).astype(f32)     # _mm512_reduce_add_ps halving tree
    b = (a[..., 0:4] + a[..., 4:8]).astype(f32)
    c = (b[..., 0:2] + b[..., 2:4]).astype(f32)
    return (c[..., 0] + c[..., 1]).astype(f32)


def score_R(prod, order):
    """k_vnni::qk_group: sequential chain over the 64 dimension pairs."""
    acc = np.zeros(prod.shape[:-1], dtype=f32)
    for j in range(64):
        acc = dp(acc, prod[..., 2 * j], prod[..., 2 * j + 1], order)
    return acc


def exact_sum_f32(block):
    """RNE fp32 of the exact sum over the last axis (products are 16-bit-significand fp32:
    the 80-bit long double sum is exact for the exponent spreads seen here)."""
    return ftz(block.astype(np.longdouble).sum(axis=-1).astype(f32))


def score_A(prod, model, order):
    """AMX qk_vnni_128x4: 4 TDPBF16PS steps of 16 dimension pairs, modelled."""
    if model == "seq":
        return score_R(prod, order)
    acc = np.zeros(prod.shape[:-1], dtype=f32)
    for st in range(4):
        acc = ftz((acc + exact_sum_f32(prod[..., 32 * st:32 * st + 32])).astype(f32))
    return acc


def pv_avx(Pb, V, order):
    """scaled_v_expr: Pb (H,64) bf16-valued weights, V (64,128) bf16 values -> (H,128)."""
    acc = np.zeros((Pb.shape[0], HEAD), dtype=f32)
    for p in range(PAGE // 2):
        pe = ftz((Pb[:, 2 * p, None] * V[None, 2 * p, :]).astype(f32))
        po = ftz((Pb[:, 2 * p + 1, None] * V[None, 2 * p + 1, :]).astype(f32))
        acc = dp(acc, pe, po, order)
    return acc


def pv_amx(Pb, V, model, order):
    """weights_times_v_128x4: 2 TDPBF16PS steps of 16 token pairs (32 tokens), modelled."""
    if model == "seq":
        return pv_avx(Pb, V, order)
    acc = np.zeros((Pb.shape[0], HEAD), dtype=f32)
    for st in range(2):
        prods = ftz((Pb[:, 32 * st:32 * st + 32, None] * V[None, 32 * st:32 * st + 32, :]).astype(f32))
        acc = ftz((acc + exact_sum_f32(np.swapaxes(prods, 1, 2))).astype(f32))
    return acc


def sum64(P):
    """expr.hpp:599 sum of a tensor<64>: two lane accumulators over chunks (0,2) and (1,3), then halving."""
    c = [P[:, 16 * i:16 * i + 16] for i in range(4)]
    acc1 = ((f32(0.0) + c[0]).astype(f32) + c[2]).astype(f32)
    acc2 = ((f32(0.0) + c[1]).astype(f32) + c[3]).astype(f32)
    t = (acc1 + acc2).astype(f32)
    a = (t[:, 0:8] + t[:, 8:16]).astype(f32)
    b = (a[:, 0:4] + a[:, 4:8]).astype(f32)
    cc = (b[:, 0:2] + b[:, 2:4]).astype(f32)
    return (cc[:, 0] + cc[:, 1]).astype(f32)


# ------------------------------------------------------------------ page / block kinds
def n_pages(T):
    return T // PAGE + 1


def page_is_dense(T, k, layout="vnni"):
    """Whether page k (tokens 64k..64k+63) is a dense page for query token T (AMX-eligible)."""
    if T < PROMPT:
        first_own_page = (T // PASS_TOKENS) * PASS_TOKENS // PAGE
        return k < first_own_page
    if k < T // PAGE:
        return True
    return OWN_PAGE_COMPLETE_IS_DENSE[layout] and (T % PAGE == PAGE - 1)


def block_is_vnni(T, c):
    """Whether K block c (tokens 16c..16c+15) is in the VNNI layout when token T attends."""
    if T < PROMPT:
        return True                        # the whole pass's K is saved before its attention
    last = BLOCK * c + BLOCK - 1
    if last < T:
        return True
    if last == T:
        return DECODE_FULL_BLOCK_VNNI_SAME_FORWARD
    return False


# ------------------------------------------------------------------ parsing the extracts
KEY_RE = re.compile(r"^(?P<label>.*?)(?: layer (?P<layer>\d+))? of token (?P<tok>\d+)$")
LABELS = {"WQ roped": ("Q", N_Q_HEADS * HEAD), "WK roped": ("K", N_KV_HEADS * HEAD),
          "WV": ("V", N_KV_HEADS * HEAD), "WO": ("O", 2560)}


def parse_values(s):
    try:
        return np.fromstring(s, sep=" ", dtype=f64)
    except Exception:
        return np.array(s.split(), dtype=f64)


def load_extract(path, layer, want=("Q", "K", "V", "O")):
    """Return dict name -> (ntok, n) float32 array of the exact bf16 values; also the
    count of values that did not print decimal-exactly (recovered by bf16 RNE)."""
    arrs = {}
    seen = {}
    inexact = 0
    total = 0
    with open(path, "r") as fh:
        for line in fh:
            key = line[0:50].strip()
            m = KEY_RE.match(key)
            if not m or m.group("layer") is None or int(m.group("layer")) != layer:
                continue
            lab = m.group("label")
            if lab not in LABELS:
                continue
            name, n = LABELS[lab]
            if name not in want:
                continue
            tok = int(m.group("tok"))
            rest = line[51:]
            close = rest.find("): ")
            v = parse_values(rest[close + 3:])
            if v.size != n:
                raise ValueError(f"{key}: {v.size} values, expected {n}")
            if name not in arrs:
                arrs[name] = np.zeros((1300, n), dtype=f32)
                seen[name] = np.zeros(1300, dtype=bool)
            v32 = v.astype(f32)
            vb = bf16_rne(v32)
            inexact += int(np.count_nonzero(vb != v32))
            total += v.size
            arrs[name][tok] = vb
            seen[name][tok] = True
    ntok = min(int(np.count_nonzero(seen[n])) for n in arrs)
    for n in arrs:
        last = np.max(np.nonzero(seen[n])[0])
        if np.count_nonzero(seen[n]) != last + 1:
            raise ValueError(f"{n}: {np.count_nonzero(seen[n])} tokens but last is {last}")
        arrs[n] = arrs[n][:last + 1]
    return arrs, inexact, total


# ------------------------------------------------------------------ the replay of one token
MODELS = ("clean", "newoff", "base", "new", "trunc", "clean_rne")
ALIASES = {"baseoff": "clean", "pocoff": "clean", "poc": "base"}


def model_spec(name):
    """(dense QK, dense PV kind, dense P rounding, partial QK, partial PV kind, partial P rounding, K layout)."""
    return {
        "clean":     ("D", "avx", "trunc", "D", "avx", "trunc", "rowmajor"),
        "newoff":    ("RD", "avx", "trunc", "RD", "avx", "trunc", "vnni"),
        "base":      ("A", "amx", "rne", "D", "avx", "trunc", "rowmajor"),
        "new":       ("A", "amx", "rne", "RD", "avx", "trunc", "vnni"),
        "trunc":     ("A", "amx", "trunc", "RD", "avx", "trunc", "vnni"),
        "clean_rne": ("D", "avx", "rne", "D", "avx", "rne", "rowmajor"),
    }[name]


def select_scores(kind, T, k, sD, sR, sA):
    """Raw scores of page k for the 4 heads of a group under QK kind: (4, 64) with -inf padding."""
    lo = k * PAGE
    hi = min(lo + PAGE - 1, T)
    cnt = hi - lo + 1
    out = np.full((KV_MUL, PAGE), -np.inf, dtype=f32)
    if kind == "D":
        out[:, :cnt] = sD[:, lo:hi + 1]
    elif kind == "A":
        out[:, :cnt] = sA[:, lo:hi + 1]
    elif kind == "RD":
        for c in range(PAGE // BLOCK):
            b0 = lo + c * BLOCK
            if b0 > hi:
                break
            b1 = min(b0 + BLOCK - 1, hi)
            src = sR if block_is_vnni(T, (lo // BLOCK) + c) else sD
            out[:, b0 - lo:b1 - lo + 1] = src[:, b0:b1 + 1]
    else:
        raise ValueError(kind)
    return out, cnt


def run_model(name, T, sD, sR, sA, V, order, amx_model, want_mass=False):
    """One query token, one KV group: returns (out32 (4,128), out_bf16, s_star, mass ratios)."""
    dq, dpv, dr, pq, ppv, pr, layout = model_spec(name)
    valid = False
    m_star = s_star = v_star = None
    mt = np.zeros(KV_MUL, dtype=f64)
    mtr = np.zeros(KV_MUL, dtype=f64)
    mrn = np.zeros(KV_MUL, dtype=f64)
    for k in range(n_pages(T)):
        dense = page_is_dense(T, k, layout)
        qk, pvk, prnd = (dq, dpv, dr) if dense else (pq, ppv, pr)
        s_raw, cnt = select_scores(qk, T, k, sD, sR, sA)
        s_page = (s_raw * SCALE32).astype(f32)
        m_page = np.max(s_page, axis=1)
        if valid:
            m_page = np.maximum(m_star, m_page)
        P = tron_exp((s_page - m_page[:, None]).astype(f32))
        ssum = sum64(P)
        Vp = np.zeros((PAGE, HEAD), dtype=f32)
        Vp[:cnt] = V[k * PAGE:k * PAGE + cnt]
        Pb = bf16_rne(P) if prnd == "rne" else bf16_trunc(P)
        Pb = ftz(Pb)                                     # DAZ inside the dot instructions
        pv = pv_amx(Pb, Vp, amx_model, order) if pvk == "amx" else pv_avx(Pb, Vp, order)
        if want_mass:
            corr64 = np.exp((m_star - m_page).astype(f64)) if valid else 0.0
            mt = mt * corr64 + P.astype(f64).sum(axis=1)
            mtr = mtr * corr64 + ftz(bf16_trunc(P)).astype(f64).sum(axis=1)
            mrn = mrn * corr64 + ftz(bf16_rne(P)).astype(f64).sum(axis=1)
        if valid:
            corr = expf_scalar(m_star - m_page)
            v_star = bf16_rne(fma32(v_star, corr[:, None], pv))
            if S_STAR_FMA:
                s_star = fma32(s_star, corr, ssum)
            else:
                s_star = ((s_star * corr).astype(f32) + ssum).astype(f32)
        else:
            v_star = bf16_rne(pv)
            s_star = ssum
            valid = True
        m_star = m_page
    out32 = (v_star / s_star[:, None]).astype(f32)
    mass = (mtr / mt, mrn / mt) if want_mass else None
    return out32, bf16_rne(out32), s_star, mass


def exact_reference(q, K, V, T):
    """float64 attention from the same bf16 Q, K, V: (4,128) output and the fp64 scores."""
    s = (q.astype(f64) @ K[:T + 1].astype(f64).T) * SCALE64
    w = np.exp(s - s.max(axis=1, keepdims=True))
    return (w @ V[:T + 1].astype(f64)) / w.sum(axis=1, keepdims=True), s


# ------------------------------------------------------------------ statistics helpers
def rel_stats(a, b, floor_rel=1e-30):
    """Elementwise |a-b| / |b| for b != 0; returns (frac_differ, median_rel, max_rel, median_ulp, max_ulp)."""
    a = np.asarray(a, dtype=f32).ravel()
    b = np.asarray(b, dtype=f32).ravel()
    diff = a != b
    nz = b != 0
    rel = np.abs(a[nz].astype(f64) - b[nz].astype(f64)) / np.abs(b[nz].astype(f64))
    ul = ulp_dist(a, b)
    return {
        "n": int(a.size), "n_differ": int(diff.sum()), "frac_differ": float(diff.mean()),
        "median_rel_of_differing": float(np.median(rel[diff[nz]])) if diff[nz].any() else 0.0,
        "max_rel": float(rel.max()) if rel.size else 0.0,
        "median_ulp_of_differing": float(np.median(ul[diff])) if diff.any() else 0.0,
        "max_ulp": int(ul.max()) if ul.size else 0,
    }


def out_vs_exact(o, o64):
    """o (4,128) fp32 path output vs o64 exact: mass-weighted bias, relative L2, max elementwise
    relative error over elements with |o64| >= 0.1 * rms(row)."""
    o = o.astype(f64)
    d = o - o64
    mass_bias = float((d * np.sign(o64)).sum() / np.abs(o64).sum())
    rel_l2 = float(np.sqrt((d ** 2).sum() / (o64 ** 2).sum()))
    rms = np.sqrt((o64 ** 2).mean(axis=1, keepdims=True))
    big = np.abs(o64) >= 0.1 * rms
    rel = np.abs(d[big]) / np.abs(o64[big])
    signed = (d[big] / o64[big])
    return {"mass_bias": mass_bias, "rel_l2": rel_l2, "max_rel_big": float(rel.max()),
            "mean_signed_rel_big": float(signed.mean()), "n_big": int(big.sum())}


def pair_stats(a16, b16, a32, b32):
    """bf16 outputs a16/b16 and fp32 outputs a32/b32 of two models, (H,128) each."""
    a16 = a16.ravel(); b16 = b16.ravel(); a32 = a32.astype(f64).ravel(); b32 = b32.astype(f64).ravel()
    differ = a16 != b16
    denom = np.maximum(np.abs(a32), np.abs(b32))
    nz = denom > 0
    rel = np.abs(a32[nz] - b32[nz]) / denom[nz]
    rms = np.sqrt((b32 ** 2).mean())
    return {"n": int(a16.size), "n_bf16_differ": int(differ.sum()), "frac_bf16_differ": float(differ.mean()),
            "median_rel32": float(np.median(rel)) if rel.size else 0.0,
            "max_rel32": float(rel.max()) if rel.size else 0.0,
            "max_abs32_over_rms": float(np.abs(a32 - b32).max() / rms) if rms > 0 else 0.0}


def agg(list_of_dicts, keys_median=(), keys_max=(), keys_sum=()):
    out = {}
    for k in keys_sum:
        out[k] = int(sum(d[k] for d in list_of_dicts))
    for k in keys_median:
        out["median_" + k] = float(np.median([d[k] for d in list_of_dicts]))
    for k in keys_max:
        out["max_" + k] = float(np.max([d[k] for d in list_of_dicts]))
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qkv", required=True, help="extract file of the arm whose Q/K/V are replayed (base)")
    ap.add_argument("--check-arms", nargs="*", default=[], help="other arms' extracts: name=path, Q/K/V identity check")
    ap.add_argument("--layer", type=int, default=LAYER)
    ap.add_argument("--tokens", default=None, help="comma list or a-b ranges; default SAMPLE_TOKENS")
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--layers-json", default=None, help="campaign layers-base-vs-new.json for M4b")
    ap.add_argument("--quick", action="store_true", help="skip the sensitivity variants")
    args = ap.parse_args()
    t0 = time.time()
    layer = args.layer
    if args.tokens:
        toks = []
        for part in args.tokens.split(","):
            if "-" in part:
                a, b = part.split("-"); toks += list(range(int(a), int(b) + 1))
            else:
                toks.append(int(part))
    else:
        toks = list(SAMPLE_TOKENS)

    print(f"# replay.py layer={layer} order={WITHIN_PAIR_ORDER} amx_model={AMX_MODEL} s_star_fma={S_STAR_FMA} ftz={FTZ}")
    print(f"# scale32={SCALE32!r} (1.0f/sqrtf(128)) float32(1/sqrt(128))={f32(SCALE64)!r}")
    arrs, inexact, total = load_extract(args.qkv, layer)
    ntok = arrs["Q"].shape[0]
    print(f"# loaded {args.qkv}: tokens={ntok} values={total} not-decimal-exact-but-bf16-roundtrip={inexact}")
    toks = [t for t in toks if t < ntok]
    results = {"params": {"layer": layer, "within_pair_order": WITHIN_PAIR_ORDER, "amx_model": AMX_MODEL,
                          "s_star_fma": S_STAR_FMA, "ftz": FTZ, "scale32": float(SCALE32),
                          "own_page_complete_is_dense": OWN_PAGE_COMPLETE_IS_DENSE,
                          "decode_full_block_vnni_same_forward_": DECODE_FULL_BLOCK_VNNI_SAME_FORWARD,
                          "decode_full_block_vnni_same_forward": DECODE_FULL_BLOCK_VNNI_SAME_FORWARD,
                          "tokens": toks, "qkv_file": args.qkv, "n_tokens_logged": ntok,
                          "values_not_decimal_exact": inexact, "values_total": total},
               "qkv_identity": {}, "M1": {}, "M2": {}, "M3": {}, "M4": {}}

    # ---- Q/K/V identity across arms (layer 0: nothing upstream of attention differs)
    for spec in args.check_arms:
        name, path = spec.split("=", 1)
        other, _, _ = load_extract(path, layer, want=("Q", "K", "V"))
        rep = {}
        for nm in ("Q", "K", "V"):
            n = min(other[nm].shape[0], arrs[nm].shape[0])
            d = int(np.count_nonzero(other[nm][:n] != arrs[nm][:n]))
            rep[nm] = {"tokens_compared": n, "values_differ": d}
        results["qkv_identity"][name] = rep
        print(f"# Q/K/V identity vs {name}: {rep}")

    Q = arrs["Q"]; K = arrs["K"]; V = arrs["V"]
    # ---- per-token replay
    m1_DR, m1_RA, m1_DA, m1_RA_seq = [], [], [], []
    m1_order = {o: {"D": 0, "R": 0, "n": 0} for o in WITHIN_PAIR_ORDERS}
    m2 = {}
    m3 = {m: [] for m in MODELS}
    m3_bf16 = {m: [] for m in MODELS}
    mass = []
    tok0_identical = None
    per_token = {}
    pairs = [("clean", "newoff"), ("newoff", "new"), ("base", "new"), ("clean", "base"), ("new", "trunc"),
             ("clean", "clean_rne"), ("newoff", "trunc"), ("clean", "new")]
    for pr in pairs:
        m2["%s_vs_%s" % pr] = []
    m2_seq = {"newoff_vs_new": [], "base_vs_new": []}
    for ti, T in enumerate(toks):
        tt = time.time()
        N = T + 1
        outs = {m: [] for m in MODELS}
        outs16 = {m: [] for m in MODELS}
        outs_seq = {m: [] for m in ("newoff", "base", "new")}
        ex = []
        sD_all = []; sR_all = []; sA_all = []; sAseq_all = []
        sD_ord = {o: [] for o in WITHIN_PAIR_ORDERS}; sR_ord = {o: [] for o in WITHIN_PAIR_ORDERS}
        tok_mass = []
        for g in range(N_KV_HEADS):
            q = Q[T, g * KV_MUL * HEAD:(g + 1) * KV_MUL * HEAD].reshape(KV_MUL, HEAD)
            Kg = K[:N, g * HEAD:(g + 1) * HEAD]
            Vg = V[:N, g * HEAD:(g + 1) * HEAD]
            prod = (q[:, None, :] * Kg[None, :, :]).astype(f32)      # exact bf16 x bf16 products
            sD = score_D(prod, WITHIN_PAIR_ORDER)
            sR = score_R(prod, WITHIN_PAIR_ORDER)
            sA = score_A(prod, AMX_MODEL, WITHIN_PAIR_ORDER)
            sD_all.append(sD); sR_all.append(sR); sA_all.append(sA)
            if not args.quick:
                sAseq = score_A(prod, "seq", WITHIN_PAIR_ORDER)
                sAseq_all.append(sAseq)
                for o in WITHIN_PAIR_ORDERS:
                    sD_ord[o].append(score_D(prod, o)); sR_ord[o].append(score_R(prod, o))
            o64, _ = exact_reference(q, Kg, Vg, T)
            ex.append(o64)
            for m in MODELS:
                o32, o16, _, ms = run_model(m, T, sD, sR, sA, Vg, WITHIN_PAIR_ORDER, AMX_MODEL, want_mass=(m == "clean"))
                outs[m].append(o32); outs16[m].append(o16)
                if ms is not None:
                    tok_mass.append(ms)
            if not args.quick:
                for m in outs_seq:
                    o32, o16, _, _ = run_model(m, T, sD, sR, sAseq, Vg, WITHIN_PAIR_ORDER, "seq")
                    outs_seq[m].append((o32, o16))
        sD_all = np.concatenate(sD_all); sR_all = np.concatenate(sR_all); sA_all = np.concatenate(sA_all)
        # M1
        m1_DR.append(dict(token=T, **rel_stats(sD_all, sR_all)))
        m1_RA.append(dict(token=T, **rel_stats(sA_all, sR_all)))
        m1_DA.append(dict(token=T, **rel_stats(sA_all, sD_all)))
        if not args.quick:
            sAseq_all = np.concatenate(sAseq_all)
            m1_RA_seq.append(dict(token=T, **rel_stats(sAseq_all, sR_all)))
            for o in WITHIN_PAIR_ORDERS:
                dD = np.concatenate(sD_ord[o]); dR = np.concatenate(sR_ord[o])
                m1_order[o]["D"] += int(np.count_nonzero(dD != sD_all))
                m1_order[o]["R"] += int(np.count_nonzero(dR != sR_all))
                m1_order[o]["n"] += int(dD.size)
        # M2
        O = {m: np.concatenate(outs[m]) for m in MODELS}
        O16 = {m: np.concatenate(outs16[m]) for m in MODELS}
        for a, b in pairs:
            m2["%s_vs_%s" % (a, b)].append(dict(token=T, **pair_stats(O16[a], O16[b], O[a], O[b])))
        if not args.quick:
            Os = {m: (np.concatenate([x[0] for x in outs_seq[m]]), np.concatenate([x[1] for x in outs_seq[m]])) for m in outs_seq}
            m2_seq["newoff_vs_new"].append(dict(token=T, **pair_stats(Os["newoff"][1], Os["new"][1], Os["newoff"][0], Os["new"][0])))
            m2_seq["base_vs_new"].append(dict(token=T, **pair_stats(Os["base"][1], Os["new"][1], Os["base"][0], Os["new"][0])))
        # M3
        E = np.concatenate(ex)
        for m in MODELS:
            m3[m].append(dict(token=T, **out_vs_exact(O[m], E)))
            m3_bf16[m].append(dict(token=T, **out_vs_exact(O16[m].astype(f64), E)))
        tm = np.array(tok_mass)        # (8, 2, 4)
        mass.append({"token": T, "attended": N,
                     "trunc_ratio_mean": float(tm[:, 0, :].mean()), "trunc_ratio_min": float(tm[:, 0, :].min()),
                     "trunc_ratio_max": float(tm[:, 0, :].max()),
                     "rne_ratio_mean": float(tm[:, 1, :].mean()), "rne_ratio_min": float(tm[:, 1, :].min()),
                     "rne_ratio_max": float(tm[:, 1, :].max())})
        if T == 0:
            tok0_identical = all(np.array_equal(O16[m], O16["clean"]) and np.array_equal(O[m], O["clean"]) for m in MODELS)
            v0 = V[0].reshape(N_KV_HEADS, HEAD)
            results["M4"]["token0_all_models_identical"] = bool(tok0_identical)
            results["M4"]["token0_output_equals_V0_bf16"] = bool(all(
                np.array_equal(O16["clean"][g * KV_MUL + h], v0[g]) for g in range(N_KV_HEADS) for h in range(KV_MUL)))
        per_token[T] = {"M1_D_vs_R": m1_DR[-1], "M1_A_vs_R": m1_RA[-1],
                        "M2": {k: v[-1] for k, v in m2.items()},
                        "M3_fp32": {m: m3[m][-1] for m in MODELS}, "mass": mass[-1]}
        if ti % 16 == 0 or T >= PROMPT:
            print(f"token {T:5d} (attended {N:5d}, pages {n_pages(T)}): D!=R {m1_DR[-1]['frac_differ']:.3f} "
                  f"A!=R {m1_RA[-1]['frac_differ']:.3f} | bf16 out differ: clean/newoff {m2['clean_vs_newoff'][-1]['frac_bf16_differ']:.4f} "
                  f"newoff/new {m2['newoff_vs_new'][-1]['frac_bf16_differ']:.4f} base/new {m2['base_vs_new'][-1]['frac_bf16_differ']:.4f} "
                  f"| mass trunc {mass[-1]['trunc_ratio_mean'] - 1:+.2e} rne {mass[-1]['rne_ratio_mean'] - 1:+.2e} "
                  f"| bias clean {m3['clean'][-1]['mass_bias']:+.2e} base {m3['base'][-1]['mass_bias']:+.2e} "
                  f"({time.time() - tt:.1f}s)")

    # ---- aggregates
    def classes(T):
        if T < 128: return "pass0_0-127"
        if T < 192: return "pass1_128-191"
        return "decode"
    def by_class(lst, fn):
        out = {}
        for cls in ("pass0_0-127", "pass1_128-191", "decode", "all"):
            sub = [d for d in lst if cls == "all" or classes(d["token"]) == cls]
            if sub:
                out[cls] = fn(sub)
        return out
    def m1_agg(sub):
        n = sum(d["n"] for d in sub); nd = sum(d["n_differ"] for d in sub)
        return {"tokens": len(sub), "scores": n, "frac_differ_pooled": nd / n,
                "median_over_tokens_of_median_rel_of_differing": float(np.median([d["median_rel_of_differing"] for d in sub])),
                "max_rel": float(max(d["max_rel"] for d in sub)),
                "median_over_tokens_of_median_ulp_of_differing": float(np.median([d["median_ulp_of_differing"] for d in sub])),
                "max_ulp": int(max(d["max_ulp"] for d in sub))}
    results["M1"] = {"D_vs_R": by_class(m1_DR, m1_agg), "A_vs_R_model_%s" % AMX_MODEL: by_class(m1_RA, m1_agg),
                     "A_vs_D_model_%s" % AMX_MODEL: by_class(m1_DA, m1_agg),
                     "within_pair_order_sensitivity": m1_order}
    if m1_RA_seq:
        results["M1"]["A_vs_R_model_seq"] = by_class(m1_RA_seq, m1_agg)
    def m2_agg(sub):
        n = sum(d["n"] for d in sub); nd = sum(d["n_bf16_differ"] for d in sub)
        return {"tokens": len(sub), "elements": n, "frac_bf16_differ_pooled": nd / n,
                "median_over_tokens_frac_bf16_differ": float(np.median([d["frac_bf16_differ"] for d in sub])),
                "max_frac_bf16_differ": float(max(d["frac_bf16_differ"] for d in sub)),
                "median_over_tokens_median_rel32": float(np.median([d["median_rel32"] for d in sub])),
                "max_rel32": float(max(d["max_rel32"] for d in sub)),
                "max_abs32_over_rms": float(max(d["max_abs32_over_rms"] for d in sub))}
    results["M2"] = {k: by_class(v, m2_agg) for k, v in m2.items()}
    if m2_seq["newoff_vs_new"]:
        results["M2"]["amx_model_seq"] = {k: by_class(v, m2_agg) for k, v in m2_seq.items()}
    def m3_agg(sub):
        return {"tokens": len(sub), "mean_mass_bias": float(np.mean([d["mass_bias"] for d in sub])),
                "median_mass_bias": float(np.median([d["mass_bias"] for d in sub])),
                "min_mass_bias": float(min(d["mass_bias"] for d in sub)), "max_mass_bias": float(max(d["mass_bias"] for d in sub)),
                "rms_rel_l2": float(np.sqrt(np.mean([d["rel_l2"] ** 2 for d in sub]))),
                "median_rel_l2": float(np.median([d["rel_l2"] for d in sub])),
                "max_rel_big": float(max(d["max_rel_big"] for d in sub)),
                "mean_signed_rel_big": float(np.mean([d["mean_signed_rel_big"] for d in sub]))}
    results["M3"] = {"fp32_output": {m: by_class(m3[m], m3_agg) for m in MODELS},
                     "bf16_output": {m: by_class(m3_bf16[m], m3_agg) for m in MODELS},
                     "weight_mass": by_class(mass, lambda sub: {
                         "tokens": len(sub),
                         "trunc_ratio_minus1_mean": float(np.mean([d["trunc_ratio_mean"] for d in sub]) - 1),
                         "trunc_ratio_minus1_min": float(min(d["trunc_ratio_min"] for d in sub) - 1),
                         "trunc_ratio_minus1_max": float(max(d["trunc_ratio_max"] for d in sub) - 1),
                         "rne_ratio_minus1_mean": float(np.mean([d["rne_ratio_mean"] for d in sub]) - 1),
                         "rne_ratio_minus1_min": float(min(d["rne_ratio_min"] for d in sub) - 1),
                         "rne_ratio_minus1_max": float(max(d["rne_ratio_max"] for d in sub) - 1)}),
                     "bias_vs_attended": [{"token": T, "attended": T + 1,
                                           "trunc_mass_ratio_minus1": per_token[T]["mass"]["trunc_ratio_mean"] - 1,
                                           "rne_mass_ratio_minus1": per_token[T]["mass"]["rne_ratio_mean"] - 1,
                                           "clean_output_mass_bias": per_token[T]["M3_fp32"]["clean"]["mass_bias"],
                                           "clean_rne_output_mass_bias": per_token[T]["M3_fp32"]["clean_rne"]["mass_bias"],
                                           "base_output_mass_bias": per_token[T]["M3_fp32"]["base"]["mass_bias"],
                                           "new_output_mass_bias": per_token[T]["M3_fp32"]["new"]["mass_bias"]}
                                          for T in BIAS_SCALING_TOKENS if T in per_token]}
    # ---- M4b: campaign first divergence
    if args.layers_json and os.path.exists(args.layers_json):
        with open(args.layers_json) as fh:
            lj = json.load(fh)
        results["M4"]["layers_base_vs_new"] = {"summary": lj.get("summary"), "WO": lj.get("by_label", {}).get("WO"),
                                               "WQ roped": lj.get("by_label", {}).get("WQ roped")}
    results["per_token"] = {str(k): v for k, v in per_token.items()}
    results["params"]["wall_s"] = time.time() - t0
    with open(args.out, "w") as fh:
        json.dump(results, fh, indent=1, default=float)
    print(json.dumps({k: results[k] for k in ("M1", "M2", "M3", "M4", "qkv_identity")}, indent=1, default=float))
    print(f"# done in {time.time() - t0:.0f} s -> {args.out}")


if __name__ == "__main__":
    main()
