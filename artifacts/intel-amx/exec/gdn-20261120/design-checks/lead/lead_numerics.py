#!/usr/bin/env python3
"""Lead designer: numeric checks of the merged design.

Reuses the engine of the prototype (proto_copy.py = a copy of
design/proto/gdn_block_proto.py): exact FP32 fma emulation, the token form in
kernel order, the float64 oracle, the emulated TDPBF16PS add order.

[1] Slice replay: the token form run on a subset of value columns gives the same
    bits as the same columns of the full run (so column slices may be replayed
    one after the other over all tokens).
[2] The block form exactly as the merged specification states it:
    truncation split into 3 bf16 pieces, pieces added lo, mid, hi, scale folded
    into the output coefficients, and two forms of the state update:
      X: accumulator tile starts at fl(G_C * S0), tile products add K^T x W
      Y: tile products from zero give T; then S = fma(G_C, S0, T)
[3] Truncation split: exactness on random and edge bit patterns; what happens
    to infinity.
"""
import sys
import time

import numpy as np

import proto_copy as P

f32, f64 = np.float32, np.float64
MASK = np.uint32(0xFFFF0000)


def trunc16(x):
    return (np.ascontiguousarray(x, dtype=f32).view(np.uint32) & MASK).view(f32)


def split3_trunc(x):
    """x = hi + mid + lo; every piece has its low 16 bits clear. Smallest first."""
    x = np.ascontiguousarray(x, dtype=f32)
    hi = trunc16(x)
    r = x - hi
    mid = trunc16(r)
    lo = r - mid
    return [lo, mid, hi]


def block_spec(S0, K, Q, V, D, Bt, C, update="Y"):
    """Block form of the merged specification, FP32, emulated tile products."""
    H, T, _ = K.shape
    S = S0.astype(f32).copy()
    O = np.empty((H, T, P.DV), f32)
    scale = f32(P.SCALE32)
    ends = []
    for t0 in range(0, T, C):
        Kc = np.ascontiguousarray(K[:, t0:t0 + C]).astype(f32)
        Qc = np.ascontiguousarray(Q[:, t0:t0 + C]).astype(f32)
        Vc = V[:, t0:t0 + C].astype(f32)
        d = D[:, t0:t0 + C].astype(f32)
        b = Bt[:, t0:t0 + C].astype(f32)
        KT = np.ascontiguousarray(Kc.transpose(0, 2, 1))
        G = np.zeros((H, C + 1, C + 1), f32)
        G[:, 0, 0] = 1
        for t in range(1, C + 1):
            G[:, t, :t] = G[:, t - 1, :t] * d[:, t - 1, None]
            G[:, t, t] = 1
        gam = G[:, :, 0]
        sp = split3_trunc(S)
        A, Bq = P.tdp_mm(Kc, sp), P.tdp_mm(Qc, sp)
        KK, QK = P.tdp_mm(Kc, [KT]), P.tdp_mm(Qc, [KT])
        CK = G[:, 1:, 1:] * KK
        CQ = (G[:, 1:, 1:] * QK) * scale
        sg = gam[:, 1:] * scale
        Delta = np.empty((H, C, P.DV), f32)
        for t in range(C):
            D64 = Delta.astype(f64)
            r = (gam[:, t + 1, None] * A[:, t]).astype(f64)
            ck = CK[:, t].astype(f64)
            for u in range(t):
                r = P.add_round_f32(ck[:, u, None] * D64[:, u], r).astype(f64)
            Delta[:, t] = (Vc[:, t] - r.astype(f32)) * b[:, t, None]
            o = (sg[:, t, None] * Bq[:, t]).astype(f64)
            cq = CQ[:, t].astype(f64)
            for u in range(t):
                o = P.add_round_f32(cq[:, u, None] * D64[:, u], o).astype(f64)
            O[:, t0 + t] = P.add_round_f32(cq[:, t, None] * Delta[:, t].astype(f64), o)
        WD = G[:, C, 1:, None] * Delta
        wp = split3_trunc(WD)
        if update == "X":
            S = P.tdp_mm(KT, wp, init=gam[:, C, None, None] * S)
        else:
            Tm = P.tdp_mm(KT, wp)
            S = P.add_round_f32(gam[:, C, None, None].astype(f64) * S.astype(f64), Tm.astype(f64))
        ends.append(S.copy())
    return O, S, ends


def main():
    t_start = time.time()
    # ------------------------------------------------------------------ [1]
    print("[1] slice replay: token form on column subsets against the full token form")
    S0, K, Q, V, D, Bt = P.make_inputs(P.SCENARIOS["normal"], 2, 48)
    O_full, S_full, _ = P.token_form_f32(S0, K, Q, V, D, Bt)
    saved = P.DV
    ok = True
    for width in (64, 16):
        P.DV = width
        for c0 in range(0, 128, width):
            cols = slice(c0, c0 + width)
            O_s, S_s, _ = P.token_form_f32(np.ascontiguousarray(S0[:, :, cols]), K, Q,
                                           np.ascontiguousarray(V[:, :, cols]), D, Bt)
            same = (O_s.view(np.uint32) == O_full[:, :, cols].view(np.uint32)).all() and \
                   (S_s.view(np.uint32) == S_full[:, :, cols].view(np.uint32)).all()
            ok &= bool(same)
    P.DV = saved
    print(f"    2 heads x 48 tokens, slices of 64 and of 16 columns: outputs and state bit-identical: {ok}")

    # ------------------------------------------------------------------ [2]
    print("\n[2] block form of the specification (truncation split, lo-mid-hi, emulated TDPBF16PS)")
    H, T = 4, 256
    print(f"    {H} heads x {T} tokens per scenario, 128 x 128 state, {H * T * 128} bf16 output words per row")
    hdr = f"    {'scenario':10s} {'variant':14s} {'out err vs f64':>15s} {'state err vs f64':>17s} {'words != token':>15s} {'words != f64':>13s}"
    print(hdr)
    worst_ratio_o = worst_ratio_s = 0.0
    flip_rates = []
    for name in ("normal", "hard", "testmag", "underflow", "corrkeys"):
        S0, K, Q, V, D, Bt = P.make_inputs(P.SCENARIOS[name], H, T)
        O_tok, S_tok, _ = P.token_form_f32(S0, K, Q, V, D, Bt)
        O64, S64, _ = P.token_form_f64(S0, K, Q, V, D, Bt)
        eo = float(np.abs(O_tok.astype(f64) - O64).max())
        es = float(np.abs(S_tok.astype(f64) - S64).max())
        fo = P.flips(O_tok, O64.astype(f32))
        print(f"    {name:10s} {'token loop':14s} {eo:15.3e} {es:17.3e} {'-':>15s} {fo[0]:>13d}")
        for C in (32, 64):
            for upd in ("X", "Y"):
                O_b, S_b, _ = block_spec(S0, K, Q, V, D, Bt, C, upd)
                assert np.isfinite(O_b).all() and np.isfinite(S_b).all()
                bo = float(np.abs(O_b.astype(f64) - O64).max())
                bs = float(np.abs(S_b.astype(f64) - S64).max())
                ft = P.flips(O_b, O_tok)
                f6 = P.flips(O_b, O64.astype(f32))
                worst_ratio_o = max(worst_ratio_o, bo / eo)
                worst_ratio_s = max(worst_ratio_s, bs / es)
                flip_rates.append(ft[0] / ft[1])
                print(f"    {name:10s} {'C=%d update %s' % (C, upd):14s} {bo:15.3e} {bs:17.3e} "
                      f"{ft[0]:>8d} ({ft[0] / ft[1] * 100:.3f} %) {f6[0]:>8d}   max steps {ft[2]}, above 1 % of rms {ft[5]}")
    print(f"    worst block error as a multiple of the token loop's error: outputs {worst_ratio_o:.2f}x, state {worst_ratio_s:.2f}x")
    print(f"    bf16 output words that differ from the token loop: {min(flip_rates) * 100:.4f} % to {max(flip_rates) * 100:.4f} %")

    # ------------------------------------------------------------------ [3]
    print("\n[3] truncation split")
    rng = np.random.default_rng(7)
    bits = rng.integers(0, 2 ** 32, 40_000_000, dtype=np.uint64).astype(np.uint32)
    expo = (bits >> np.uint32(23)) & np.uint32(0xFF)
    edge_m = np.array([0, 1, 0x7FFF, 0x8000, 0x8001, 0xFFFF, 0x10000, 0x7F7FFF, 0x7F8000, 0x7FFFFF, 0x00FF00, 0x0000FF],
                      dtype=np.uint32)
    edges = (np.arange(1, 255, dtype=np.uint32)[:, None] << np.uint32(23) | edge_m[None, :]).ravel()
    edges = np.concatenate([edges, edges | np.uint32(0x80000000)])
    for label, b in (("random bit patterns", bits), ("edge mantissas, every exponent field 1..254", edges)):
        x = b.view(f32) if b.flags["C_CONTIGUOUS"] else np.ascontiguousarray(b).view(f32)
        e = (b >> np.uint32(23)) & np.uint32(0xFF)
        normal = (e >= 24) & (e <= 254)
        xs = np.ascontiguousarray(x[normal])
        lo, mid, hi = split3_trunc(xs)
        exact = (hi.astype(f64) + mid.astype(f64) + lo.astype(f64)) == xs.astype(f64)
        clean = ((lo.view(np.uint32) | mid.view(np.uint32) | hi.view(np.uint32)) & np.uint32(0xFFFF)) == 0

        def not_subnormal(p):
            pe = (p.view(np.uint32) >> np.uint32(23)) & np.uint32(0xFF)
            return (pe != 0) | ((p.view(np.uint32) & np.uint32(0x7FFFFFFF)) == 0)

        ns = not_subnormal(lo) & not_subnormal(mid) & not_subnormal(hi)
        bad = int((~(exact & clean & ns)).sum())
        print(f"    {label}: {xs.size} finite values with exponent field 24..254 (|x| >= 2^-103): {bad} fail"
              f" (sum exact, 3 pieces bf16, no subnormal piece)")
        tiny = np.ascontiguousarray(x[(e >= 1) & (e < 24)])
        if tiny.size:
            lo, mid, hi = split3_trunc(tiny)

            def lost(p):
                pe = (p.view(np.uint32) >> np.uint32(23)) & np.uint32(0xFF)
                return np.where(pe == 0, np.abs(p.astype(f64)), 0.0)

            worst = float((lost(lo) + lost(mid) + lost(hi)).max())
            print(f"    {label}: {tiny.size} values with exponent field 1..23: largest part lost when subnormal pieces"
                  f" count as zero = {worst:.3e} (2^-126 = {2.0 ** -126:.3e})")
    inf = np.array([np.inf, -np.inf, np.nan, 3.4028235e38], f32)
    with np.errstate(invalid="ignore"):
        lo, mid, hi = split3_trunc(inf)
    print(f"    split of [inf, -inf, nan, FLT_MAX]: hi {hi}, mid {mid}, lo {lo}")
    print(f"\nrun time {time.time() - t_start:.1f} s")


if __name__ == "__main__":
    main()
