"""Check 6: the "one fused pass" form for decode (AVX-512 only, no AMX).

Idea: do not apply the rank-one update of token t-1 in its own pass. Keep it
pending as (k_p, delta_p, g_p). The single pass of token t then does, per
state row i:

    s_i   = fma(k_p[i], delta_p, g_p * Sbar[i])   # the row the kernel would have stored
    store s_i
    acc_r += k_t[i] * s_i                         # for r_t
    acc_q += q_t[i] * s_i                         # for o_t

and afterwards
    r_t     = g_t * acc_r
    delta_t = (v_t - r_t) * beta_t
    o_t     = scale * (g_t * acc_q + (q_t . k_t) * delta_t)
    pending = (k_t, delta_t, g_t)

So every token reads the state once and writes it once. The existing kernel
reads it twice and writes it once, and decode adds a NaN scan (a third read).
"""
import numpy as np
from gdn_common import F32, F64, fma32, bf16_rne, make_chain, token_loop_f64, \
    token_loop_f32_kernel_order


def fused(ch, dtype):
    q, k, v, beta, g = (ch[n].astype(dtype) for n in ("q", "k", "v", "beta", "g"))
    S = ch["S0"].astype(dtype).copy()
    dk, dv = S.shape
    scale = dtype(1.0 / np.sqrt(F64(dk)))
    kp, dp, gp = np.zeros(dk, dtype), np.zeros(dv, dtype), dtype(1.0)
    out = np.zeros((len(g), dv), dtype)
    passes = 0
    for t in range(len(g)):
        acc_r, acc_q = np.zeros(dv, dtype), np.zeros(dv, dtype)
        for i in range(dk):
            if dtype is F32:
                s = fma32(kp[i], dp, (S[i] * gp).astype(F32))
                acc_r, acc_q = fma32(k[t, i], s, acc_r), fma32(q[t, i], s, acc_q)
            else:
                s = kp[i] * dp + S[i] * gp
                acc_r, acc_q = acc_r + k[t, i] * s, acc_q + q[t, i] * s
            S[i] = s
        passes += 1
        r = (g[t] * acc_r).astype(dtype)
        delta = ((v[t] - r) * beta[t]).astype(dtype)
        qk = dtype((q[t].astype(F64) * k[t].astype(F64)).sum())
        out[t] = (scale * (g[t] * acc_q + qk * delta)).astype(dtype)
        kp, dp, gp = k[t], delta, g[t]
    # flush the pending update only to compare final states
    S = (S * gp + np.outer(kp, dp)).astype(dtype)
    return out, S, passes


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    ch = make_chain(rng, 48)
    o64, S64 = token_loop_f64(ch)
    of, Sf, _ = fused(ch, F64)
    print("float64 fused pass vs float64 token loop: "
          f"max|out diff| = {np.abs(of - o64).max():.2e}, max|S diff| = {np.abs(Sf - S64).max():.2e}")
    assert np.abs(of - o64).max() < 1e-13 and np.abs(Sf - S64).max() < 1e-13
    o_tok, S_tok = token_loop_f32_kernel_order(ch)
    o32, S32, passes = fused(ch, F32)
    flips = int((bf16_rne(o32).view(np.uint32) != bf16_rne(o_tok).view(np.uint32)).sum())
    print(f"FP32 token loop  : out err vs f64 {np.abs(o_tok - o64).max():.2e}, "
          f"S err {np.abs(S_tok - S64).max():.2e}")
    print(f"FP32 fused pass  : out err vs f64 {np.abs(o32 - o64).max():.2e}, "
          f"S err {np.abs(S32 - S64).max():.2e}; bf16(out) words that differ from the "
          f"token loop: {flips} of {o32.size} ({100.0 * flips / o32.size:.3f} %)")
    print(f"state passes per token: fused 1 read + 1 write; kernel 2 reads + 1 write "
          f"(+1 read for the NaN scan in decode)")
    ops_now, ops_fused = (2 + 3) * 1024, (1 + 3) * 1024
    print(f"zmm multiply/fma per value head per token: kernel {ops_now}, fused {ops_fused}")
