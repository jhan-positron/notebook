"""Shared helpers for the GDN (GatedDeltaNet) block-form checks.

Notation follows the tron kernel gdn_recurrence
(h/tron/kernels/gated_delta_net.hpp:231-300), for ONE value head:

  S      state, FP32, [key coordinate i][value coordinate c], 128 x 128
  k, q   normalized key / query of the token (bf16-exact values held in FP32)
  v      value of the token (bf16-exact)
  g      decay of the token (true FP32 scalar)
  beta   update gate of the token (bf16-exact scalar)
  scale  1/sqrt(key_head_dim)
"""
import numpy as np

F32 = np.float32
F64 = np.float64


# ---------------------------------------------------------------- bf16 helpers
def bf16_rne(x):
    """Round FP32 to bf16 (nearest, ties to even), result held in FP32.

    Same rule as tron round_fp32_bits (h/common/numerics/bf16.hpp:91-97):
    zero and subnormal inputs become a signed zero.
    """
    x = np.asarray(x, dtype=F32)
    bits = x.view(np.uint32).astype(np.uint64)
    is_nan = (bits & 0x7FFFFFFF) > 0x7F800000
    is_small = (bits & 0x7F800000) == 0
    r = (bits + 0x7FFF + ((bits >> 16) & 1)) >> 16
    r = np.where(is_small, (bits >> 16) & 0x8000, r)
    r = np.where(is_nan, (bits >> 16) | 0x0040, r)
    return ((r & 0xFFFF) << 16).astype(np.uint32).view(F32)


def bf16_trunc(x):
    """Drop the low 16 bits of the FP32 pattern (round toward zero)."""
    x = np.asarray(x, dtype=F32)
    return (x.view(np.uint32) & np.uint32(0xFFFF0000)).view(F32)


def is_bf16_exact(x):
    x = np.asarray(x, dtype=F32)
    return (x.view(np.uint32) & np.uint32(0xFFFF)) == 0


def fma32(a, b, c):
    """FP32 fused multiply-add, emulated through float64.

    a*b is exact in float64 (24 + 24 bits <= 53). The add rounds once to 53
    bits and once more to 24 bits. That double rounding can differ from a true
    fma in rare ties. It does not matter for the tolerance-level comparisons
    made here.
    """
    return (np.asarray(a, F64) * np.asarray(b, F64) + np.asarray(c, F64)).astype(F32)


# ------------------------------------------------------------ test data maker
def make_chain(rng, n_tokens, dk=128, dv=128, decay_lo=0.90, decay_hi=0.9999,
               v_scale=1.0, s_scale=0.05, tiny_decay_every=0):
    """Inputs of one value head for a chain of n_tokens, already at the
    precision the kernel sees them (q, k, v, beta bf16-exact, g FP32)."""
    def l2norm_bf16(x):
        x = bf16_rne(x.astype(F32))
        n = np.sqrt((x.astype(F64) ** 2).sum(-1, keepdims=True) + 1e-6)
        return bf16_rne((x / n).astype(F32))

    q = l2norm_bf16(rng.standard_normal((n_tokens, dk)))
    k = l2norm_bf16(rng.standard_normal((n_tokens, dk)))
    v = bf16_rne((v_scale * rng.standard_normal((n_tokens, dv))).astype(F32))
    beta = bf16_rne((1.0 / (1.0 + np.exp(-rng.standard_normal(n_tokens)))).astype(F32))
    g = rng.uniform(decay_lo, decay_hi, n_tokens).astype(F32)
    if tiny_decay_every:
        g[::tiny_decay_every] = F32(1e-3)
    S0 = (s_scale * rng.standard_normal((dk, dv))).astype(F32)
    return dict(q=q, k=k, v=v, beta=beta, g=g, S0=S0)


# ------------------------------------------------- token-by-token references
def token_loop_f64(ch):
    """The recurrence in float64 (the oracle). Returns (outputs, final S)."""
    q, k, v, beta, g = (ch[n].astype(F64) for n in ("q", "k", "v", "beta", "g"))
    S = ch["S0"].astype(F64).copy()
    dk = S.shape[0]
    scale = 1.0 / np.sqrt(F64(dk))
    out = np.zeros((len(g), S.shape[1]), F64)
    for t in range(len(g)):
        S = S * g[t]
        r = k[t] @ S
        delta = (v[t] - r) * beta[t]
        S = S + np.outer(k[t], delta)
        out[t] = (q[t] * scale) @ S
    return out, S


def token_loop_f32_kernel_order(ch):
    """The recurrence in FP32 in the operation order of gdn_recurrence
    (gated_delta_net.hpp:266-294): loop 1 fma over key coordinates, delta,
    loop 2 fma state update and fma output."""
    q, k, v, beta, g = (ch[n] for n in ("q", "k", "v", "beta", "g"))
    S = ch["S0"].copy()
    dk, dv = S.shape
    scale = F32(1.0 / np.sqrt(F64(dk)))
    out = np.zeros((len(g), dv), F32)
    for t in range(len(g)):
        dec = (S * g[t]).astype(F32)
        r = np.zeros(dv, F32)
        for i in range(dk):
            r = fma32(k[t, i], dec[i], r)
        delta = ((v[t] - r).astype(F32) * beta[t]).astype(F32)
        res = np.zeros(dv, F32)
        for i in range(dk):
            new = fma32(k[t, i], delta, dec[i])
            S[i] = new
            res = fma32(F32(q[t, i] * scale), new, res)
        out[t] = res
    return out, S
