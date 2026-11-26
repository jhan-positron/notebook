"""Check 3: the AMX block algorithm, emulated in FP32 with the exact add
order of TDPBF16PS, against the token-by-token kernel order and a float64
oracle.

TDPBF16PS semantics (Intel SDM operation section, checked 2026-11-20 on
felixcloutier.com/x86/tdpbf16ps): for each output element C[m][n] the
instruction starts two FP32 temporaries at zero, adds the 16 products of the
even inner elements into one and the 16 products of the odd inner elements
into the other (round to nearest even at every add, input subnormals read as
zero, output subnormals flushed to zero), adds the two temporaries, then adds
that sum to C[m][n].

The block algorithm emulated here is the design in the answer:
  1. split S0 (FP32) into 3 bf16 planes by truncation
  2. [K;Q] x S0       tile products, per inner block: lo, mid, hi piece
  3. [K;Q] x K^T      tile products (all operands bf16-exact)
  4. forward substitution in FP32 with fma, earlier tokens first
  5. W = Gam[C] * Delta, split into 3 bf16 planes
  6. S = G[C]*S0 loaded as the accumulator tile, += K^T x W tile products
"""
import sys
import numpy as np
from gdn_common import (F32, F64, bf16_rne, bf16_trunc, is_bf16_exact, fma32,
                        make_chain, token_loop_f64, token_loop_f32_kernel_order)


def split3_trunc(x):
    hi = bf16_trunc(x)
    r1 = (x - hi).astype(F32)
    mid = bf16_trunc(r1)
    lo = (r1 - mid).astype(F32)
    return hi, mid, lo


N_TDP = 0  # counts emulated inner-block products (in units of one 32-wide block)


def tile_dp(acc, a_blk, b_blk):
    """acc[M][N] += a_blk[M][<=32] x b_blk[<=32][N] in TDPBF16PS add order.

    One call stands for the tile products of one 32-wide inner block; the
    result of an element does not depend on how rows and columns are cut
    into 16 x 16 tiles."""
    global N_TDP
    assert is_bf16_exact(a_blk).all() and is_bf16_exact(b_blk).all()
    M, kd = a_blk.shape
    N = b_blk.shape[1]
    even = np.zeros((M, N), F32)
    odd = np.zeros((M, N), F32)
    for p in range(0, kd, 2):
        even = (even + a_blk[:, p, None] * b_blk[None, p, :]).astype(F32)
        odd = (odd + a_blk[:, p + 1, None] * b_blk[None, p + 1, :]).astype(F32)
    acc += (even + odd).astype(F32)
    N_TDP += 1
    return acc


def block_form_amx_f32(ch, C, products="amx"):
    q, k, v, beta, g = (ch[n] for n in ("q", "k", "v", "beta", "g"))
    S = ch["S0"].copy()
    dk, dv = S.shape
    scale = F32(1.0 / np.sqrt(F64(dk)))
    n = len(g)
    out = np.zeros((n, dv), F32)
    for c0 in range(0, n, C):
        K, Q, V = k[c0:c0 + C], q[c0:c0 + C], v[c0:c0 + C]
        gg, bb = g[c0:c0 + C], beta[c0:c0 + C]
        c = len(gg)
        Gam = np.zeros((c, c), F32)
        G = np.zeros(c, F32)
        for t in range(c):
            if t:
                Gam[t, :t] = (Gam[t - 1, :t] * gg[t]).astype(F32)
            Gam[t, t] = 1.0
            G[t] = gg[t] if t == 0 else F32(G[t - 1] * gg[t])
        KQ = np.concatenate([K, Q], 0)                      # (2c, dk) bf16-exact
        if products == "amx":
            pieces = split3_trunc(S)
            R0Q0 = np.zeros((2 * c, dv), F32)
            for kb in range(0, dk, 32):
                for piece in pieces[::-1]:                  # lo, mid, hi
                    tile_dp(R0Q0, KQ[:, kb:kb + 32], piece[kb:kb + 32, :])
            AB = np.zeros((2 * c, c), F32)
            KT = np.ascontiguousarray(K.T)
            for kb in range(0, dk, 32):
                tile_dp(AB, KQ[:, kb:kb + 32], KT[kb:kb + 32, :])
        else:                                               # FP32 products (AVX fallback)
            R0Q0 = (KQ @ S).astype(F32)
            AB = (KQ @ K.T).astype(F32)
        R0, Q0, A, B = R0Q0[:c], R0Q0[c:], AB[:c], AB[c:]
        Mc = (Gam * A).astype(F32)
        Nc = (Gam * B).astype(F32)
        Delta = np.zeros((c, dv), F32)
        for t in range(c):
            acc = (G[t] * R0[t]).astype(F32)
            acc_o = (G[t] * Q0[t]).astype(F32)
            for i in range(t):
                acc = fma32(Mc[t, i], Delta[i], acc)
                acc_o = fma32(Nc[t, i], Delta[i], acc_o)
            Delta[t] = ((V[t] - acc).astype(F32) * bb[t]).astype(F32)
            acc_o = fma32(Nc[t, t], Delta[t], acc_o)
            out[c0 + t] = (scale * acc_o).astype(F32)
        W = (Gam[c - 1][:, None] * Delta).astype(F32)
        S = (G[c - 1] * S).astype(F32)                      # accumulator tile start
        if products == "amx":
            wp = split3_trunc(W)
            KT = np.ascontiguousarray(K.T)                  # (dk, c)
            for tb in range(0, c, 32):
                for piece in wp[::-1]:
                    tile_dp(S, KT[:, tb:tb + 32], piece[tb:tb + 32, :])
        else:
            S = (S + (K.T @ W).astype(F32)).astype(F32)
    return out, S


def ulp32(x):
    return np.spacing(np.abs(np.asarray(x, F32)))


def report(name, ch, Cs=(16, 32, 64)):
    o64, S64 = token_loop_f64(ch)
    o_tok, S_tok = token_loop_f32_kernel_order(ch)
    mo, mS = np.abs(o64).max(), np.abs(S64).max()
    print(f"\n== {name}: {len(ch['g'])} tokens, max|out| = {mo:.4f}, max|S| = {mS:.4f}")
    print(f"   FP32 notch at max|out| = {ulp32(mo):.2e}, at max|S| = {ulp32(mS):.2e}")
    print(f"   {'variant':30s} {'out err vs f64':>15s} {'S err vs f64':>13s} "
          f"{'out diff vs tok':>16s} {'bf16(out) words that differ from tok':>38s}")
    e_o, e_S = np.abs(o_tok - o64).max(), np.abs(S_tok - S64).max()
    print(f"   {'token loop FP32 (kernel order)':30s} {e_o:15.2e} {e_S:13.2e} {'-':>16s} {'-':>38s}")
    rows = []
    for C in Cs:
        for prod in ("amx", "fp32"):
            o_b, S_b = block_form_amx_f32(ch, C, prod)
            e_o, e_S = np.abs(o_b - o64).max(), np.abs(S_b - S64).max()
            d = np.abs(o_b - o_tok).max()
            flips = int((bf16_rne(o_b).view(np.uint32) != bf16_rne(o_tok).view(np.uint32)).sum())
            tot = o_b.size
            lab = f"block C={C} " + ("AMX 3-piece" if prod == "amx" else "FP32 products")
            print(f"   {lab:30s} {e_o:15.2e} {e_S:13.2e} {d:16.2e} "
                  f"{flips:10d} of {tot} ({100.0 * flips / tot:.3f} %)")
            rows.append((C, prod, e_o, e_S, d, flips, tot))
    return rows


if __name__ == "__main__":
    rng = np.random.default_rng(1120)
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    report("typical magnitudes, decay 0.90..0.9999", make_chain(rng, 128))
    report("strong forgetting, decay 0.5..1.0", make_chain(rng, 128, decay_lo=0.5, decay_hi=1.0))
    report("decay 1e-3 on every 7th token", make_chain(rng, 128, tiny_decay_every=7))
    report("no decay (g = 1), state grows", make_chain(rng, 128, decay_lo=1.0, decay_hi=1.0))
    report("test-like small magnitudes (state 0.0015, value 0.006)",
           make_chain(rng, 128, v_scale=0.006, s_scale=0.0015))
    if not quick:
        report("long chain, drift check", make_chain(rng, 1024), Cs=(64,))
    print(f"\nemulated inner-block tile products: {N_TDP}")
