#!/usr/bin/env python3
"""Numerics of the GDN recurrence variants, on SYNTHETIC data.

The token form mirrors gdn_recurrence (h/tron/kernels/gated_delta_net.hpp
lines 259-297): FP32 state, fma with one rounding, sums over the key
coordinate in ascending order.  fma(a,b,c) is emulated as
float32(float64(a)*float64(b) + float64(c)); the product is exact in float64.

Variants:
  token      : today's kernel (reference for "bit-identical or not")
  half_major : same arithmetic, loop order "column half outer, token inner"
  block_fp32 : block form over B tokens, FP32 only
  block_amx  : block form, FP32 operands split into 3 bf16 pieces
  block_fp16 : block form, FP32 operands split into 2 fp16 pieces
  state_bf16 / state_fp16 : token form with the stored state rounded
  oracle     : token form in float64

Data are random (not model data): q,k ~ N(0,1) then L2-normalised and rounded
to bf16; v ~ bf16(N(0,1)); decay = exp(-A*softplus(a+bias)); beta =
bf16(sigmoid(b)).  The recurrence is linear in v, so absolute errors scale
with the size of v; relative errors do not.
"""
import numpy as np

f32, f64 = np.float32, np.float64
KD = VD = 128
SCALE = f32(1.0 / np.sqrt(f64(KD)))


def bf16(x):
    x = np.asarray(x, dtype=f32)
    b = x.view(np.uint32).astype(np.uint64)
    b = (b + 0x7FFF + ((b >> 16) & 1)) & 0xFFFF0000
    return b.astype(np.uint32).view(f32).reshape(x.shape)


def fp16(x):
    return np.asarray(x, dtype=f32).astype(np.float16).astype(f32)


def fma(a, b, c):
    return (a.astype(f64) * b.astype(f64) + c.astype(f64)).astype(f32)


def make_tokens(rng, T, H, a_mean=0.0):
    q = rng.standard_normal((T, H, KD)).astype(f32)
    k = rng.standard_normal((T, H, KD)).astype(f32)

    def norm(x):
        x = bf16(x)
        n = np.sqrt((x.astype(f64) ** 2).sum(-1, keepdims=True) + 1e-6)
        return bf16(x * bf16((1.0 / n).astype(f32)))

    q, k = norm(q), norm(k)
    v = bf16(rng.standard_normal((T, H, VD)).astype(f32))
    a = bf16(rng.standard_normal((T, H)).astype(f32) * f32(1.5) + f32(a_mean))
    A = rng.uniform(0.3, 1.2, (1, H)).astype(f32)
    bias = rng.uniform(-0.3, 0.3, (1, H)).astype(f32)
    d = np.exp(-A * np.log1p(np.exp(a + bias))).astype(f32)
    beta = bf16((1.0 / (1.0 + np.exp(-bf16(rng.standard_normal((T, H)).astype(f32) * f32(1.5))))).astype(f32))
    return dict(q=q, k=k, v=v, d=d, beta=beta, qs=(q * SCALE).astype(f32))


def token_form(S, tok, t0, t1, cols=slice(None), state_round=None, dtype=f32):
    """Advance S (H,KD,ncols) in place over tokens [t0,t1). Returns outputs."""
    out = []
    S = S.astype(dtype)
    for t in range(t0, t1):
        k = tok["k"][t].astype(dtype)
        qs = tok["qs"][t].astype(dtype) if dtype is f32 else (tok["q"][t].astype(f64) * f64(SCALE))
        d = tok["d"][t].astype(dtype)[:, None]
        v = tok["v"][t][:, cols].astype(dtype)
        beta = tok["beta"][t].astype(dtype)[:, None]
        r = np.zeros_like(v)
        for i in range(KD):
            sd = S[:, i, :] * d
            r = fma(k[:, i, None], sd, r) if dtype is f32 else r + k[:, i, None] * sd
        delta = (v - r) * beta
        o = np.zeros_like(v)
        for i in range(KD):
            sd = S[:, i, :] * d
            new = fma(k[:, i, None], delta, sd) if dtype is f32 else sd + k[:, i, None] * delta
            o = fma(qs[:, i, None], new, o) if dtype is f32 else o + qs[:, i, None] * new
            S[:, i, :] = new if state_round is None else state_round(new)
        out.append(o)
    return np.stack(out), S


def split(x, kind):
    if kind is None:
        return [x]
    rnd, n = {"bf16x3": (bf16, 3), "bf16x2": (bf16, 2), "fp16x2": (fp16, 2)}[kind]
    pieces, rest = [], x.astype(f32)
    for _ in range(n):
        p = rnd(rest)
        pieces.append(p)
        rest = (rest.astype(f64) - p.astype(f64)).astype(f32)
    return pieces


def block_form(S0, tok, t0, B, kind=None):
    """One block of B tokens. kind=None: FP32 only. Otherwise the FP32
    operand of each big product is split into bf16 / fp16 pieces."""
    K, Qs, V = tok["k"][t0:t0 + B], tok["qs"][t0:t0 + B], tok["v"][t0:t0 + B]
    d, beta = tok["d"][t0:t0 + B], tok["beta"][t0:t0 + B]
    H = S0.shape[0]
    R0 = np.zeros((B, H, VD), f32)
    U0 = np.zeros((B, H, VD), f32)
    # the query scale cannot ride on a bf16 tile operand: tiles take q, the
    # scale is applied to the tile result (kind != None)
    Qop = Qs if kind is None else tok["q"][t0:t0 + B]
    for s in range(0, KD, 32):
        for P in split(S0, kind):
            for i in range(s, s + 32):
                R0 = fma(K[:, :, i, None], P[None, :, i, :], R0)
                U0 = fma(Qop[:, :, i, None], P[None, :, i, :], U0)
    if kind is not None:
        U0 = (U0 * SCALE).astype(f32)
    Gkk = np.zeros((B, B, H), f32)
    Gqk = np.zeros((B, B, H), f32)
    for i in range(KD):
        Gkk = fma(K[:, None, :, i], K[None, :, :, i], Gkk)
        Gqk = fma(Qs[:, None, :, i], K[None, :, :, i], Gqk)
    delta = np.zeros((B, H, VD), f32)
    O = np.zeros((B, H, VD), f32)
    g = np.ones(H, f32)
    coef = np.zeros((B, H), f32)       # coef[j] = product of decays after token j
    for t in range(B):
        g = (g * d[t]).astype(f32)
        coef[:t] = coef[:t] * d[t]
        r = (g[:, None] * R0[t]).astype(f32)
        for j in range(t):
            r = fma((coef[j] * Gkk[t, j]).astype(f32)[:, None], delta[j], r)
        delta[t] = (V[t] - r) * beta[t][:, None]
        coef[t] = 1.0
        o = (g[:, None] * U0[t]).astype(f32)
        for j in range(t + 1):
            o = fma((coef[j] * Gqk[t, j]).astype(f32)[:, None], delta[j], o)
        O[t] = o
    S = (g[:, None, None] * S0).astype(f32)
    W = (coef[:, :, None] * delta).astype(f32)      # decayed deltas, FP32
    for P in split(W, kind):
        for j in range(B):
            S = fma(K[j][:, :, None], P[j][:, None, :], S)
    return O, S


def run_blocks(S0, tok, t0, t1, B, kind=None):
    outs, S = [], S0.copy()
    for b0 in range(t0, t1, B):
        O, S = block_form(S, tok, b0, min(B, t1 - b0), kind)
        outs.append(O)
    return np.concatenate(outs), S


def report(name, O, S, Oref, Sref, Oor, Sor):
    words = O.size
    flips = int((bf16(O).view(np.uint32) != bf16(Oref).view(np.uint32)).sum())
    print(f"  {name:11s} | out vs oracle max abs {np.abs(O - Oor).max():.2e}"
          f" | state vs oracle max abs {np.abs(S - Sor).max():.2e}"
          f" | out vs token max abs {np.abs(O.astype(f64) - Oref).max():.2e}"
          f" | bf16(out) words != token: {flips} of {words} ({flips / words * 1e6:.0f} ppm)"
          f" | state bytes equal to token: {bool((S.view(np.uint32) == Sref.view(np.uint32)).all())}")


if __name__ == "__main__":
    H, WARM, T = 8, 64, 128
    for regime, a_mean in (("fast decay", 0.0), ("slow decay", -5.0)):
        rng = np.random.default_rng(20261120)
        tok = make_tokens(rng, WARM + T, H, a_mean)
        S0 = np.zeros((H, KD, VD), f32)
        _, S0 = token_form(S0, tok, 0, WARM)                 # realistic non-zero start
        print(f"\n=== regime '{regime}': synthetic data, {H} value heads, {WARM} warm-up tokens, then a chain of {T} tokens ===")
        print(f"decay min {tok['d'].min():.3f}, median {np.median(tok['d']):.3f}, max {tok['d'].max():.3f};"
              f" |state| max {np.abs(S0).max():.2f}, rms {np.sqrt((S0.astype(f64)**2).mean()):.3f}")

        Oref, Sref = token_form(S0.copy(), tok, WARM, WARM + T)
        Oor, Sor = token_form(S0.astype(f64), tok, WARM, WARM + T, dtype=f64)
        print(f"|output| rms {np.sqrt((Oref.astype(f64)**2).mean()):.3f}; one bf16 step at 1.0 = {2.0**-7:.1e}; one FP32 step at 1.0 = {2.0**-23:.1e}")

        print("[1] loop order 'column half outer, token inner' (bit-identity check)")
        halves = [token_form(S0[:, :, c].copy(), tok, WARM, WARM + T, cols=c) for c in (slice(0, 64), slice(64, 128))]
        Oh = np.concatenate([h[0] for h in halves], axis=-1)
        Sh = np.concatenate([h[1] for h in halves], axis=-1)
        print(f"  outputs bit-identical: {bool((Oh.view(np.uint32) == Oref.view(np.uint32)).all())};"
              f" state bit-identical: {bool((Sh.view(np.uint32) == Sref.view(np.uint32)).all())}")

        print("[2] block forms against today's token form and the float64 oracle (v ~ N(0,1))")
        report("token", Oref, Sref, Oref, Sref, Oor, Sor)
        for B in (16, 32):
            O, S = run_blocks(S0, tok, WARM, WARM + T, B)
            report(f"fp32  B={B}", O, S, Oref, Sref, Oor, Sor)
        for kind in ("bf16x3", "fp16x2", "bf16x2"):
            O, S = run_blocks(S0, tok, WARM, WARM + T, 32, kind)
            report(f"{kind} B=32", O, S, Oref, Sref, Oor, Sor)
        print("  note: tests use abs tolerance 1e-7 with v of size 0.006; multiply the 'max abs' columns by 0.006 for that scale")

    rng = np.random.default_rng(3)
    print("\n[3] exactness of splitting FP32 into pieces (1e6 random FP32 values, N(0,1))")
    x = rng.standard_normal(1_000_000).astype(f32)
    big = np.abs(x) >= 2.0 ** -10
    for kind in ("bf16x3", "bf16x2", "fp16x2"):
        p = split(x, kind)
        res = np.abs(x.astype(f64) - sum(q.astype(f64) for q in p))
        rel = (res / np.abs(x))[big]
        print(f"  {kind}: exact for {float((res == 0).mean()) * 100:.2f} % of values; max abs residual {res.max():.2e};"
              f" max relative residual for |x| >= 2^-10: {rel.max():.2e} = {rel.max() / 2.0**-24:.1f} x half an FP32 step")

    print("\n[4] reduced-precision stored state, token form (error against the FP32 token form)")
    for regime, a_mean in (("fast decay", 0.0), ("slow decay", -5.0)):
        for T2 in (16, 128, 512):
            tok2 = make_tokens(np.random.default_rng(7), T2, H, a_mean)
            Z = np.zeros((H, KD, VD), f32)
            O32, S32 = token_form(Z.copy(), tok2, 0, T2)
            for name, rnd in (("bf16", bf16), ("fp16", fp16)):
                O, S = token_form(Z.copy(), tok2, 0, T2, state_round=rnd)
                last = slice(max(0, T2 - 16), T2)
                rel = np.sqrt(((O[last].astype(f64) - O32[last]) ** 2).mean()) / np.sqrt((O32[last].astype(f64) ** 2).mean())
                flips = (bf16(O[last]).view(np.uint32) != bf16(O32[last]).view(np.uint32)).mean()
                print(f"  {regime}, state {name}, {T2:4d} tokens: output rel. RMS error (last 16 tokens) {rel:.2e};"
                      f" bf16(out) words changed {flips * 100:.1f} %; state max abs error {np.abs(S.astype(f64) - S32).max():.2e}")
