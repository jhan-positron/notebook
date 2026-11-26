#!/usr/bin/env python3
"""Verifier (math and numerics lens): checks of the GDN block specification.

Parts
 A  fma emulation against exact rational arithmetic
 B  block algebra in exact rational arithmetic (small geometry) + mutations
 C  truncation split, every finite FP32 bit pattern of both signs
 D  tile layouts of tile_mapping against the logical products, bit for bit
 E  FP32 emulation of the specified block form on my own scenarios
 F  edge cases: zero start, slice replay, decay ratios by division,
    overflow of U0 before decay, loop order of P1
 G  small arithmetic checks
"""
import math
import random
import sys
import time
from fractions import Fraction
from multiprocessing import Pool

import numpy as np

import vm_engine as E

f32, f64, u32 = np.float32, np.float64, np.uint32


# =============================================================== part B
def exact_algebra(mutation=None, seed=5):
    rnd = random.Random(seed)
    dk, dv, C, nb = 4, 3, 6, 2
    T = C * nb

    def fr(lo=-40, hi=40):
        return Fraction(rnd.randint(lo, hi), rnd.randint(1, 23))

    S0 = [[fr() for _ in range(dv)] for _ in range(dk)]
    K = [[fr() for _ in range(dk)] for _ in range(T)]
    Q = [[fr() for _ in range(dk)] for _ in range(T)]
    V = [[fr() for _ in range(dv)] for _ in range(T)]
    d = [Fraction(rnd.randint(1, 30), 31) for _ in range(T)]
    be = [Fraction(rnd.randint(0, 30), 31) for _ in range(T)]
    scale = Fraction(5, 17)
    # token form (F6)
    S = [row[:] for row in S0]
    O_tok = []
    for t in range(T):
        Sd = [[S[i][c] * d[t] for c in range(dv)] for i in range(dk)]
        r = [sum(K[t][i] * Sd[i][c] for i in range(dk)) for c in range(dv)]
        delta = [(V[t][c] - r[c]) * be[t] for c in range(dv)]
        S = [[Sd[i][c] + K[t][i] * delta[c] for c in range(dv)] for i in range(dk)]
        O_tok.append([sum(Q[t][i] * scale * S[i][c] for i in range(dk)) for c in range(dv)])
    S_tok = S
    # block form (steps 0-6), tokens are 1..C inside a block
    S = [row[:] for row in S0]
    O_blk = []
    for b0 in range(0, T, C):
        Kc, Qc, Vc, dc, bc = K[b0:b0 + C], Q[b0:b0 + C], V[b0:b0 + C], d[b0:b0 + C], be[b0:b0 + C]
        G = [[Fraction(0)] * (C + 1) for _ in range(C + 1)]
        G[0][0] = Fraction(1)
        for t in range(1, C + 1):
            for u in range(t):
                G[t][u] = G[t - 1][u] * dc[t - 1]
            G[t][t] = Fraction(1)
        R0 = [[sum(Kc[t][i] * S[i][c] for i in range(dk)) for c in range(dv)] for t in range(C)]
        U0 = [[sum(Qc[t][i] * S[i][c] for i in range(dk)) for c in range(dv)] for t in range(C)]
        KK = [[sum(Kc[t][i] * Kc[u][i] for i in range(dk)) for u in range(C)] for t in range(C)]
        QK = [[sum(Qc[t][i] * Kc[u][i] for i in range(dk)) for u in range(C)] for t in range(C)]
        Delta = []
        for t in range(1, C + 1):
            gam_r = G[t - 1][0] if mutation == "gamma_prev" else G[t][0]
            r = [gam_r * R0[t - 1][c] + sum(G[t][u] * KK[t - 1][u - 1] * Delta[u - 1][c] for u in range(1, t))
                 for c in range(dv)]
            Delta.append([(Vc[t - 1][c] - r[c]) * bc[t - 1] for c in range(dv)])
            last = t if mutation == "o_before_update" else t + 1
            O_blk.append([scale * (G[t][0] * U0[t - 1][c] +
                                   sum(G[t][u] * QK[t - 1][u - 1] * Delta[u - 1][c] for u in range(1, last)))
                          for c in range(dv)])
        row = C - 1 if mutation == "w_prev_row" else C
        W = [[G[row][u] * Delta[u - 1][c] for c in range(dv)] for u in range(1, C + 1)]
        S = [[G[C][0] * S[i][c] + sum(Kc[u][i] * W[u][c] for u in range(C)) for c in range(dv)] for i in range(dk)]
    return O_blk == O_tok, S == S_tok


# =============================================================== part C
def split_worker(idx):
    """2^22 bit patterns starting at idx << 22. Returns counters."""
    b = (np.arange(1 << 22, dtype=np.uint64) + (np.uint64(idx) << np.uint64(22))).astype(u32)
    e = (b >> u32(23)) & u32(0xFF)
    fin = e != 255
    b = b[fin]
    e = e[fin]
    x = b.view(f32)
    lo, mid, hi = E.split_trunc(x, 3)
    exact = (hi.astype(f64) + mid.astype(f64) + lo.astype(f64)) == x.astype(f64)
    lb, mb, hb = lo.view(u32), mid.view(u32), hi.view(u32)
    clean = ((lb | mb | hb) & u32(0xFFFF)) == 0

    def sub(p):  # nonzero with exponent field 0
        return (((p >> u32(23)) & u32(0xFF)) == 0) & ((p & u32(0x7FFFFFFF)) != 0)

    anysub = sub(lb) | sub(mb) | sub(hb)
    same_sign = ((lb >> u32(31)) == (b >> u32(31))) | ((lb & u32(0x7FFFFFFF)) == 0)
    same_sign &= ((mb >> u32(31)) == (b >> u32(31))) | ((mb & u32(0x7FFFFFFF)) == 0)
    big = e >= 24
    loss = (np.where(sub(lb), np.abs(lo.astype(f64)), 0.0) + np.where(sub(mb), np.abs(mid.astype(f64)), 0.0) +
            np.where(sub(hb), np.abs(hi.astype(f64)), 0.0))
    small = ~big
    return dict(
        n=int(fin.sum()), n_big=int(big.sum()),
        big_not_exact=int((big & ~exact).sum()), big_not_clean=int((big & ~clean).sum()),
        big_sub=int((big & anysub).sum()),
        small_not_exact=int((small & ~exact).sum()), small_not_clean=int((small & ~clean).sum()),
        small_sub=int((small & anysub).sum()),
        small_max_loss=float(loss[small].max()) if small.any() else 0.0,
        sign_bad=int((~same_sign).sum()),
    )


# =============================================================== part E
def u(lo, hi):
    return lambda rng, shape: rng.uniform(lo, hi, shape)


def logu(lo, hi):
    return lambda rng, shape: np.exp(rng.uniform(math.log(lo), math.log(hi), shape)) * rng.choice([-1.0, 1.0], shape)


def normal(s):
    return lambda rng, shape: rng.standard_normal(shape) * s


def decay_longmem(rng, shape):
    d = np.exp(-rng.uniform(0.0, 2e-3, shape))
    d[rng.uniform(size=shape) < 0.25] = 1.0
    return d


def decay_log(lo, hi):
    return lambda rng, shape: 10.0 ** rng.uniform(lo, hi, shape)


def s0_rowspike(rng, shape):
    s = rng.standard_normal(shape) * 0.01
    s[:, ::32, :] *= 1e5
    return s


SCEN = {
    # name: (T, kwargs, note)
    "base": (256, dict(decay=u(0.9, 1.0), beta=u(0, 1), v=logu(0.01, 1.0), s0=normal(0.01)),
             "decay 0.9-1.0, beta 0-1, |v| 0.01-1, start state sigma 0.01"),
    "testmag": (256, dict(decay=u(0.70, 0.85), beta=u(0.3, 0.7), v=u(-0.1, 0.1), s0=u(-0.0035, 0.0035), qk=0.6),
                "magnitudes like the tron test literals"),
    "longmem": (1024, dict(decay=decay_longmem, beta=u(0, 0.2), v=normal(0.3), s0=normal(0.3)),
                "decay 0.998-1.0 with 25 % exactly 1.0, beta 0-0.2, v sigma 0.3, start state sigma 0.3"),
    "bigmag": (256, dict(decay=u(0.5, 1.0), beta=u(0, 1), v=normal(20.0), s0=normal(5.0)),
               "v sigma 20, start state sigma 5"),
    "tinydecay": (128, dict(decay=decay_log(-6, -2), beta=u(0, 1), v=logu(0.01, 1.0), s0=normal(0.01)),
                  "decay 1e-6 to 1e-2 (log-uniform): G underflows inside a 32-token block"),
    "lowdecay": (128, dict(decay=u(0.02, 0.10), beta=u(0, 1), v=logu(0.01, 1.0), s0=normal(0.01)),
                 "decay 0.02-0.10: G crosses the subnormal range inside a 32-token block"),
    "zerostart": (64, dict(decay=u(0.9, 1.0), beta=u(0, 1), v=logu(0.01, 1.0), s0=normal(0.0)),
                  "start state exactly zero (first tokens of a sequence)"),
    "repkeys": (256, dict(decay=u(0.99, 1.0), beta=u(0.9, 1.0), v=logu(0.01, 1.0), s0=normal(0.01), rho=0.99,
                          qk=0.7),
                "consecutive keys correlated 0.99, beta 0.9-1.0, decay 0.99-1.0"),
    "rowspike": (128, dict(decay=u(0.9, 1.0), beta=u(0, 1), v=logu(0.01, 1.0), s0=s0_rowspike),
                 "4 of 128 key rows of the start state are 1e5 times larger (sigma 1e3)"),
}
SEEDS = {name: 9000 + 17 * i for i, name in enumerate(SCEN)}
H = 4


def run_scen(name):
    t0 = time.time()
    T, kw, note = SCEN[name]
    S0, K, Q, V, D, Bt = E.make(SEEDS[name], H, T, **kw)
    keep = {128, T}
    O_t, S_t, sn_t = E.token_f32(S0, K, Q, V, D, Bt, keep)
    O_o, S_o, sn_o = E.token_f64(S0, K, Q, V, D, Bt, keep)
    info = {}
    with np.errstate(all="ignore"):
        O_b, S_b, sn_b = E.block_spec(S0, K, Q, V, D, Bt, info=info, keep=keep)
    out = dict(name=name, note=note, T=T, info=info, finite=bool(np.isfinite(O_b).all() and np.isfinite(S_b).all()))
    omax, smax = float(np.abs(O_o).max()), float(np.abs(S_o).max())
    out.update(omax=omax, orms=float(np.sqrt(np.mean(O_o ** 2))), smax=smax)
    so, ss = E.spacing(omax), E.spacing(smax)

    def err(x, ref):
        return float(np.abs(x.astype(f64) - ref.astype(f64)).max())

    out["tok_o"], out["blk_o"] = err(O_t, O_o), err(O_b, O_o)
    out["tok_s"], out["blk_s"] = err(S_t, S_o), err(S_b, S_o)
    out["bt_o"], out["bt_s"] = err(O_b, O_t), err(S_b, S_t)
    out["sp_o"], out["sp_s"] = so, ss
    if T > 128:
        n = 128
        so1 = E.spacing(float(np.abs(O_o[:, :n]).max()))
        ss1 = E.spacing(float(np.abs(sn_o[n]).max()))
        out["first128"] = dict(tok_o=err(O_t[:, :n], O_o[:, :n]) / so1, blk_o=err(O_b[:, :n], O_o[:, :n]) / so1,
                               tok_s=err(sn_t[n], sn_o[n]) / ss1, blk_s=err(sn_b[n], sn_o[n]) / ss1,
                               bt_o=err(O_b[:, :n], O_t[:, :n]) / so1)
        out["last128_bt_o"] = err(O_b[:, -n:], O_t[:, -n:]) / E.spacing(float(np.abs(O_o[:, -n:]).max()))
    out["wd"] = E.word_diff(O_b, O_t)
    out["wd_tok_oracle"] = E.word_diff(O_t, O_o.astype(f32))
    out["wd_blk_oracle"] = E.word_diff(O_b, O_o.astype(f32))
    gate = np.random.default_rng(77).standard_normal(O_t.shape).astype(f32)
    pa, pb = E.postprocess(O_t, gate), E.postprocess(O_b, gate)
    out["post_n"] = int((E.bf16_word(pa) != E.bf16_word(pb)).sum())
    out["first4"] = E.word_diff(O_b[:, :4], O_t[:, :4])["n"]
    out["first1_bits_equal"] = bool((O_b[:, 0].view(u32) == O_t[:, 0].view(u32)).all())
    var = {}
    if name in ("base", "repkeys", "testmag"):
        for label, kwv in (("P1 pieces outer (prototype order)", dict(p1_order="piece_outer")),
                           ("round-to-nearest split", dict(split=E.split_nearest)),
                           ("2 pieces", dict(pieces=2)),
                           ("no DAZ/FTZ", dict(ftz=False))):
            Ov, Sv, _ = E.block_spec(S0, K, Q, V, D, Bt, **kwv)
            var[label] = dict(wd=E.word_diff(Ov, O_t), o=err(Ov, O_o), s=err(Sv, S_o),
                              vs_spec_o_bits=int((Ov.view(u32) != O_b.view(u32)).sum()),
                              vs_spec_s_bits=int((Sv.view(u32) != S_b.view(u32)).sum()),
                              vs_spec_words=E.word_diff(Ov, O_b)["n"], s_bt=err(Sv, S_t))
    out["var"] = var
    out["time"] = time.time() - t0
    return out


# =============================================================== main
def main():
    T0 = time.time()
    P = print
    P("PART A  fma emulation against exact rational arithmetic")
    bad, n = E.fma32_selftest()
    P(f"  {n} triples (1/4 built to cancel): {bad} wrong")

    P("\nPART B  block algebra in exact rational arithmetic (4 key rows x 3 value columns, 2 blocks of 6 tokens)")
    for mut in (None, "o_before_update", "gamma_prev", "w_prev_row"):
        eo, es = exact_algebra(mut)
        label = "specification" if mut is None else f"mutation {mut}"
        P(f"  {label:28s}: outputs equal {eo}, final state equal {es}")

    P("\nPART C  truncation split on every finite FP32 bit pattern (both signs)")
    with Pool(28) as pool:
        res = pool.map(split_worker, range(1024), chunksize=4)
    tot = {k: (max if k == "small_max_loss" else sum)(r[k] for r in res) for k in res[0]}
    P(f"  finite patterns {tot['n']}; with exponent field >= 24 (|x| >= 2^-103): {tot['n_big']}")
    P(f"    |x| >= 2^-103: sum not exact {tot['big_not_exact']}; a piece with low 16 bits set {tot['big_not_clean']}; "
      f"a subnormal piece {tot['big_sub']}")
    P(f"    |x| <  2^-103: sum not exact {tot['small_not_exact']}; a piece with low 16 bits set "
      f"{tot['small_not_clean']}; values with a subnormal piece {tot['small_sub']}; largest part lost when "
      f"subnormal pieces count as zero {tot['small_max_loss']:.6e} (2^-126 = {2.0 ** -126:.6e})")
    P(f"    pieces with a sign different from x: {tot['sign_bad']}")
    with np.errstate(all="ignore"):
        lo, mid, hi = E.split_trunc(np.array([np.inf, -np.inf, np.nan, 3.4028235e38, -0.0], f32))
    P(f"    split of [inf, -inf, nan, FLT_MAX, -0.0]: hi {hi} mid {mid} lo {lo}")

    P("\nPART D  tile layouts of tile_mapping against the logical products (1 head, 1 block of 32 tokens)")
    S0, K, Q, V, D, Bt = E.make(4242, 1, 32, decay=u(0.9, 1.0), beta=u(0, 1), v=logu(0.01, 1.0), s0=normal(0.3))
    Kc, Qc, S = K[0], Q[0], S0[0]
    KQ = np.concatenate([Kc, Qc], axis=0)  # [64][128]
    sp = E.split_trunc(S, 3)
    # logical, loop of tile_mapping: key block outer, pieces inner
    acc = np.zeros((1, 64, 128), f32)
    for kb in range(4):
        for p in sp:
            acc = E.tdp_block(KQ[None, :, 32 * kb:32 * kb + 32], p[None, 32 * kb:32 * kb + 32, :], acc)
    lit = np.zeros((64, 128), f32)
    for vb in range(8):
        for kb in range(4):
            Bt_ = []
            for p in sp:
                B = np.zeros((16, 32), f32)
                B[:, 0::2] = p[32 * kb + 0:32 * kb + 32:2, 16 * vb:16 * vb + 16]
                B[:, 1::2] = p[32 * kb + 1:32 * kb + 32:2, 16 * vb:16 * vb + 16]
                Bt_.append(B)
            for rb in range(4):
                A = KQ[16 * rb:16 * rb + 16, 32 * kb:32 * kb + 32]
                for B in Bt_:
                    lit[16 * rb:16 * rb + 16, 16 * vb:16 * vb + 16] = E.tdpbf16ps_literal(
                        lit[16 * rb:16 * rb + 16, 16 * vb:16 * vb + 16], A, B)
    P(f"  P1 (R0, U0): 384 literal tile products; bits equal to the logical form: "
      f"{bool((lit.view(u32) == acc[0].view(u32)).all())}; max |P1 - float64 K S0| = "
      f"{np.abs(lit.astype(f64) - KQ.astype(f64) @ S.astype(f64)).max():.3e}")
    KT = np.ascontiguousarray(Kc.T)  # [128][32]
    acc = np.zeros((1, 64, 32), f32)
    for kb in range(4):
        acc = E.tdp_block(KQ[None, :, 32 * kb:32 * kb + 32], KT[None, 32 * kb:32 * kb + 32, :], acc)
    lit = np.zeros((64, 32), f32)
    for cb in range(2):
        for kb in range(4):
            B = np.zeros((16, 32), f32)
            B[:, 0::2] = Kc[16 * cb:16 * cb + 16, 32 * kb + 0:32 * kb + 32:2].T
            B[:, 1::2] = Kc[16 * cb:16 * cb + 16, 32 * kb + 1:32 * kb + 32:2].T
            for rb in range(4):
                A = KQ[16 * rb:16 * rb + 16, 32 * kb:32 * kb + 32]
                lit[16 * rb:16 * rb + 16, 16 * cb:16 * cb + 16] = E.tdpbf16ps_literal(
                    lit[16 * rb:16 * rb + 16, 16 * cb:16 * cb + 16], A, B)
    P(f"  Gram (KK, QK): 32 literal tile products; bits equal to the logical form: "
      f"{bool((lit.view(u32) == acc[0].view(u32)).all())}; max |Gram - float64| = "
      f"{np.abs(lit.astype(f64) - KQ.astype(f64) @ Kc.astype(f64).T).max():.3e}")
    W = (np.random.default_rng(3).standard_normal((32, 128)) * 0.2).astype(f32)
    wp = E.split_trunc(W, 3)
    acc = np.zeros((1, 128, 128), f32)
    for p in wp:
        acc = E.tdp_block(KT[None], p[None], acc)
    lit = np.zeros((128, 128), f32)
    for vb in range(8):
        for krb in range(8):
            A = KT[16 * krb:16 * krb + 16, :]  # 16 key rows x 32 tokens
            for p in wp:
                B = np.zeros((16, 32), f32)
                B[:, 0::2] = p[0::2, 16 * vb:16 * vb + 16]
                B[:, 1::2] = p[1::2, 16 * vb:16 * vb + 16]
                lit[16 * krb:16 * krb + 16, 16 * vb:16 * vb + 16] = E.tdpbf16ps_literal(
                    lit[16 * krb:16 * krb + 16, 16 * vb:16 * vb + 16], A, B)
    P(f"  Update (K^T W): 192 literal tile products; bits equal to the logical form: "
      f"{bool((lit.view(u32) == acc[0].view(u32)).all())}; max |T - float64 K^T W| = "
      f"{np.abs(lit.astype(f64) - Kc.astype(f64).T @ W.astype(f64)).max():.3e}")

    P("\nPART E  specified block form (C = 32, truncation split, P1 key block outer, step 6 by fma, DAZ/FTZ on)")
    P(f"  {H} value heads per scenario, 128 x 128 state. 'sp' = FP32 spacing at the largest magnitude of the quantity.")
    with Pool(len(SCEN)) as pool:
        rs = pool.map(run_scen, list(SCEN))
    for r in rs:
        P(f"\n  SCENARIO {r['name']} ({r['note']}); {r['T']} tokens; {r['time']:.0f} s")
        P(f"    largest |o| {r['omax']:.3e} (rms {r['orms']:.3e}), largest final |S| {r['smax']:.3e}; "
          f"every block value finite: {r['finite']}")
        P(f"    error against the float64 oracle, whole chain:")
        P(f"      outputs: token loop {r['tok_o']:.3e} ({r['tok_o'] / r['sp_o']:.1f} sp)   block "
          f"{r['blk_o']:.3e} ({r['blk_o'] / r['sp_o']:.1f} sp)   ratio {r['blk_o'] / r['tok_o']:.2f}x")
        P(f"      state  : token loop {r['tok_s']:.3e} ({r['tok_s'] / r['sp_s']:.1f} sp)   block "
          f"{r['blk_s']:.3e} ({r['blk_s'] / r['sp_s']:.1f} sp)   ratio {r['blk_s'] / r['tok_s']:.2f}x")
        P(f"    block against token loop: outputs {r['bt_o']:.3e} ({r['bt_o'] / r['sp_o']:.1f} sp), "
          f"state {r['bt_s']:.3e} ({r['bt_s'] / r['sp_s']:.1f} sp)")
        if "first128" in r:
            f = r["first128"]
            P(f"    first 128 tokens, in sp: outputs token {f['tok_o']:.1f} block {f['blk_o']:.1f}; state at token 128 "
              f"token {f['tok_s']:.1f} block {f['blk_s']:.1f}; block vs token outputs first 128: {f['bt_o']:.1f}, "
              f"last 128: {r['last128_bt_o']:.1f}")
        w = r["wd"]
        P(f"    bf16 recurrence words, block != token loop: {w['n']} of {w['total']} ({100.0 * w['n'] / w['total']:.4f} %), "
          f"largest step {w['max_step']}; above 1 % of rms: {w['n_big']} of {w['total_big']}, largest step "
          f"{w['max_step_big']}")
        P(f"    bf16 recurrence words against the oracle: token loop {r['wd_tok_oracle']['n']}, block "
          f"{r['wd_blk_oracle']['n']}")
        P(f"    bf16 words after postprocess (est., unit weight, random gate), block != token loop: {r['post_n']} of "
          f"{w['total']} ({100.0 * r['post_n'] / w['total']:.4f} %) = {r['post_n'] / max(w['n'], 1):.1f}x the recurrence words")
        P(f"    first token of the chain: FP32 output bits equal {r['first1_bits_equal']}; words that differ in tokens "
          f"1-4: {r['first4']}")
        i = r["info"]
        P(f"    decay products G below the diagonal: {i['G_n']}; subnormal {i['G_sub']}; exactly zero {i['G_zero']}")
        for label, v in r["var"].items():
            P(f"    variant [{label}]: words != token {v['wd']['n']} (above 1 % rms {v['wd']['n_big']}, step "
              f"{v['wd']['max_step_big']}); error vs oracle outputs {v['o']:.3e} state {v['s']:.3e}; state vs token "
              f"{v['s_bt'] / r['sp_s']:.1f} sp; against the specified form: {v['vs_spec_o_bits']} FP32 output values, "
              f"{v['vs_spec_s_bits']} FP32 state values, {v['vs_spec_words']} bf16 words differ")

    P("\nPART F  edge cases")
    # F1 slice replay
    S0, K, Q, V, D, Bt = E.make(31, 2, 40, decay=u(0.3, 1.0), beta=u(0, 1), v=logu(0.01, 1.0), s0=normal(0.05))
    O_full, S_full, _ = E.token_f32(S0, K, Q, V, D, Bt)
    ok = True
    for width in (64, 16):
        for c0 in range(0, 128, width):
            O_s, S_s, _ = E.token_f32(np.ascontiguousarray(S0[:, :, c0:c0 + width]), K, Q,
                                      np.ascontiguousarray(V[:, :, c0:c0 + width]), D, Bt)
            ok &= bool((O_s.view(u32) == O_full[:, :, c0:c0 + width].view(u32)).all())
            ok &= bool((S_s.view(u32) == S_full[:, :, c0:c0 + width].view(u32)).all())
    P(f"  F1 slice replay (all 40 tokens on one column slice, then the next slice; widths 64 and 16): "
      f"output and state bits equal to the full token loop: {ok}")
    # F2 decay ratios by division, C = 64, decay 0.05-0.5
    S0, K, Q, V, D, Bt = E.make(404, 4, 128, decay=u(0.05, 0.5), beta=u(0, 1), v=logu(0.01, 1.0), s0=normal(0.01))
    O_t, S_t, _ = E.token_f32(S0, K, Q, V, D, Bt)
    for gdiv in (False, True):
        with np.errstate(all="ignore"):
            O_b, S_b, _ = E.block_spec(S0, K, Q, V, D, Bt, C=64, gdiv=gdiv)
        fin = np.isfinite(O_b)
        d_ = float(np.abs(O_b.astype(f64) - O_t.astype(f64))[fin].max())
        P(f"  F2 C = 64, decay 0.05-0.5, ratios by {'DIVISION' if gdiv else 'products'}: non-finite outputs "
          f"{int((~fin).sum())} of {O_b.size}; largest finite output difference from the token loop {d_:.3e}; "
          f"bf16 words that differ {int((E.bf16_word(O_b) != E.bf16_word(O_t))[fin].sum())}")
    # F3 U0 overflows before the decay is applied; S0 and W stay finite
    S0, K, Q, V, D, Bt = E.make(55, 1, 32, decay=u(0.4, 0.6), beta=u(0.2, 0.8), v=logu(0.01, 1.0), s0=normal(0.0))
    S0[0] = (np.sign(Q[0, 0])[:, None] * f32(5e37)).astype(f32)
    D[0, 0] = f32(0.01)
    with np.errstate(all="ignore"):
        O_t, S_t, _ = E.token_f32(S0, K, Q, V, D, Bt)
        O_b, S_b, _ = E.block_spec(S0, K, Q, V, D, Bt)
    P(f"  F3 start state = 5e37 x sign(q_1), finite; decay of token 1 = 0.01:")
    P(f"     token loop: non-finite outputs {int((~np.isfinite(O_t)).sum())}, non-finite state {int((~np.isfinite(S_t)).sum())}; "
      f"largest |o_1| {np.abs(O_t[0, 0]).max():.3e}")
    P(f"     block form: non-finite outputs {int((~np.isfinite(O_b)).sum())} (token 1: {int((~np.isfinite(O_b[0, 0])).sum())}), "
      f"non-finite state {int((~np.isfinite(S_b)).sum())}")
    P("     the two guards of the specification test S0 and W only; here both are finite, so no fallback happens.")
    # F4 scale of the proposed 16-spacing band against worst-case accumulation
    P(f"  F4 worst-case relative error of gamma_32 built by 31 rounded multiplies: 31 x 2^-24 = {31 * 2.0 ** -24:.3e} "
      f"= {31 * 2.0 ** -24 / 2.0 ** -23:.1f} to {31 * 2.0 ** -24 / 2.0 ** -24:.1f} FP32 spacings of the value")

    P("\nPART G  arithmetic")
    for rate, tag in ((12 / 262144, "block FP32"), (10 / 262144, "3 pieces")):
        P(f"  (1 - {rate:.6e})^320 = {(1 - rate) ** 320:.4f} ({tag})")
    P(f"  triangle zmm operations per block: 8 x 32 x 31 + 40 x 32 = {8 * 32 * 31 + 40 * 32}")
    P(f"  16 FP32 spacings relative to the value: {16 * 2.0 ** -24:.3e} to {16 * 2.0 ** -23:.3e}")
    P(f"\nrun time {time.time() - T0:.0f} s")


if __name__ == "__main__":
    main()
