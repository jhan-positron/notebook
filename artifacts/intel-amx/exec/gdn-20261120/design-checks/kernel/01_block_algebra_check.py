"""Check 1: the block form is algebraically equal to the token-by-token loop.

Everything here is float64, so only the ALGEBRA is tested (rounding is tested
in 03_amx_emulation.py).

Block form for a chunk of C tokens t = 1..C of one value head
(derived from gated_delta_net.hpp:266-294):

  G[t]     = g[1] * ... * g[t]                 cumulative decay, G[0] = 1
  Gam[t,i] = g[i+1] * ... * g[t]  (i <= t)     decay from token i to token t
  R0 = K S0   (C x dv)      Q0 = Q S0  (C x dv)        <- dense products
  A  = K K^T  (C x C)       B  = Q K^T (C x C)         <- dense products
  for t = 1..C (forward substitution, C x C triangle):
      Delta[t] = beta[t] * ( v[t] - G[t]*R0[t] - sum_{i<t} Gam[t,i]*A[t,i]*Delta[i] )
      o[t]     = scale   * (        G[t]*Q0[t] + sum_{i<=t} Gam[t,i]*B[t,i]*Delta[i] )
  W[i] = Gam[C,i] * Delta[i]
  S_C  = G[C]*S0 + K^T W                                <- dense product
"""
import numpy as np
from gdn_common import make_chain, token_loop_f64, F64


def block_form_f64(ch, C):
    q, k, v, beta, g = (ch[n].astype(F64) for n in ("q", "k", "v", "beta", "g"))
    S = ch["S0"].astype(F64).copy()
    dk, dv = S.shape
    scale = 1.0 / np.sqrt(F64(dk))
    n = len(g)
    out = np.zeros((n, dv), F64)
    for c0 in range(0, n, C):
        K, Q, V = k[c0:c0 + C], q[c0:c0 + C], v[c0:c0 + C]
        gg, bb = g[c0:c0 + C], beta[c0:c0 + C]
        c = len(gg)
        # Gam[t, i] = prod_{j=i+1..t} g[j]; built by a recurrence, no division.
        Gam = np.zeros((c, c), F64)
        for t in range(c):
            if t:
                Gam[t, :t] = Gam[t - 1, :t] * gg[t]
            Gam[t, t] = 1.0
        G = np.cumprod(gg)
        R0, Q0 = K @ S, Q @ S          # dense: [K;Q] x S0
        A, B = K @ K.T, Q @ K.T        # dense: [K;Q] x K^T
        Delta = np.zeros((c, dv), F64)
        for t in range(c):
            acc = G[t] * R0[t] + (Gam[t, :t] * A[t, :t]) @ Delta[:t]
            Delta[t] = (V[t] - acc) * bb[t]
            acc_o = G[t] * Q0[t] + (Gam[t, :t + 1] * B[t, :t + 1]) @ Delta[:t + 1]
            out[c0 + t] = scale * acc_o
        W = Gam[c - 1][:, None] * Delta
        S = G[c - 1] * S + K.T @ W      # dense: K^T x W
    return out, S


if __name__ == "__main__":
    rng = np.random.default_rng(20261120)
    print("float64 block form vs float64 token loop (pure algebra check)")
    print(f"{'case':34s} {'C':>3s} {'max|out diff|':>14s} {'max|S diff|':>14s} "
          f"{'max|out|':>9s} {'max|S|':>9s}")
    cases = [
        ("decay 0.90..0.9999", dict()),
        ("decay 0.5..1.0", dict(decay_lo=0.5, decay_hi=1.0)),
        ("decay 1e-3 every 7th token", dict(tiny_decay_every=7)),
        ("decay exactly 1 (no decay)", dict(decay_lo=1.0, decay_hi=1.0)),
    ]
    worst = 0.0
    for name, kw in cases:
        ch = make_chain(rng, 128, **kw)
        o_ref, S_ref = token_loop_f64(ch)
        for C in (16, 32, 64, 128, 50):   # 50 = ragged chunk, last chunk short
            o_blk, S_blk = block_form_f64(ch, C)
            do, dS = np.abs(o_blk - o_ref).max(), np.abs(S_blk - S_ref).max()
            worst = max(worst, do, dS)
            print(f"{name:34s} {C:3d} {do:14.3e} {dS:14.3e} "
                  f"{np.abs(o_ref).max():9.3f} {np.abs(S_ref).max():9.3f}")
    print(f"worst difference over all cases: {worst:.3e} "
          f"(float64 ulp at 1.0 is 2.2e-16)")
    assert worst < 1e-11
    print("PASS: block form == token loop up to float64 rounding")
