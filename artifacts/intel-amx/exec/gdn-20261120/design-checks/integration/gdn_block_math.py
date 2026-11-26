#!/usr/bin/env python3
"""Check the block form of the GatedDeltaNet recurrence against the per-token form.

Per-token form (gated_delta_net.hpp:259-297), one value head, state S[key i][value c]:
    r      = sum_i k[i] * (S[i][:] * decay)
    delta  = (v - r) * beta
    S[i][:] = fma(k[i], delta, S[i][:] * decay)
    o      = sum_i (q[i] * scale) * S_new[i][:]

Block form over C tokens (what a block kernel would compute):
    D(j->t) = prod_{i=j+1..t} decay_i
    UK = K S0, UQ = Qs S0                (one pass over S0, 2C vectors)
    G  = K K^T (strict lower), H = Qs K^T (lower with diagonal)
    delta_t = beta_t * (v_t - D(0->t) UK_t - sum_{j<t} D(j->t) G[t][j] delta_j)
    o_t     = D(0->t) UQ_t + sum_{j<=t} D(j->t) H[t][j] delta_j
    S_C     = D(0->C) S0 + K^T diag(D(j->C)) Delta     (one pass over S)

The script answers three questions.
  1. Is the block form algebraically equal to the per-token form?  (float64, both forms)
  2. How far apart are the two forms in FP32, where the order of the sums differs?
  3. How many final bf16 output words change?
It also emulates the "3 bf16 pieces" split of an FP32 operand that an AMX tile product
needs (there is no FP32 tile product), to see what that does to the FP32 result.
"""
import sys
import numpy as np

F32 = np.float32
F64 = np.float64
KD = 128  # key head width
VD = 128  # value head width
SCALE = F32(1.0 / np.sqrt(128.0))


def bf16_rne(x):
    """Round FP32 to bf16 (nearest even), return FP32 holding the bf16 value."""
    b = np.asarray(x, dtype=F32).view(np.uint32).astype(np.uint64)
    b = b + 0x7FFF + ((b >> 16) & 1)
    b = (b >> 16) << 16
    return b.astype(np.uint32).view(F32)


def fma32(a, b, c):
    """FP32 fused multiply-add, emulated through float64 (product exact in float64)."""
    return (a.astype(F64) * b.astype(F64) + c.astype(F64)).astype(F32)


def l2norm_bf16(x):
    """Stand-in for normalize_gdn: bf16 in, bf16-exact unit vector out."""
    x = bf16_rne(x)
    n = F32(1.0) / np.sqrt(np.sum(x.astype(F64) ** 2) + 1e-6)
    return bf16_rne((x * F32(n)).astype(F32))


def make_tokens(rng, n):
    q = np.stack([l2norm_bf16(rng.standard_normal(KD).astype(F32)) for _ in range(n)])
    k = np.stack([l2norm_bf16(rng.standard_normal(KD).astype(F32)) for _ in range(n)])
    v = bf16_rne((0.5 * rng.standard_normal((n, VD))).astype(F32))
    decay = rng.uniform(0.90, 0.999, n).astype(F32)          # true FP32 scalar
    beta = bf16_rne(rng.uniform(0.05, 0.95, n).astype(F32))  # bf16(sigmoid(.))
    return q, k, v, decay, beta


def seq_f32(S, q, k, v, decay, beta):
    """Per-token form in FP32, sums in the order of the C++ loops."""
    S = S.copy()
    out = np.empty((len(q), VD), F32)
    for t in range(len(q)):
        d = decay[t]
        r = np.zeros(VD, F32)
        for i in range(KD):
            r = fma32(np.full(VD, k[t, i], F32), S[i] * d, r)
        delta = ((v[t] - r) * beta[t]).astype(F32)
        o = np.zeros(VD, F32)
        qs = (q[t] * SCALE).astype(F32)
        for i in range(KD):
            S[i] = fma32(np.full(VD, k[t, i], F32), delta, S[i] * d)
            o = fma32(np.full(VD, qs[i], F32), S[i], o)
        out[t] = o
    return S, out


def seq_f64(S, q, k, v, decay, beta):
    """Per-token form in float64 (the oracle)."""
    S = S.astype(F64)
    out = np.empty((len(q), VD), F64)
    for t in range(len(q)):
        d = F64(decay[t])
        r = (S * d).T @ k[t].astype(F64)
        delta = (v[t].astype(F64) - r) * F64(beta[t])
        S = S * d + np.outer(k[t].astype(F64), delta)
        # the C++ scales the query in FP32 (gated_delta_net.hpp:287), so the oracle
        # takes the FP32-rounded scaled query as its input
        out[t] = S.T @ (q[t] * SCALE).astype(F32).astype(F64)
    return S, out


def split3_bf16(x):
    """x (FP32) = h + m + l with each piece a bf16 value. Returns pieces and max residual."""
    h = bf16_rne(x)
    r1 = (x - h).astype(F32)
    m = bf16_rne(r1)
    r2 = (r1 - m).astype(F32)
    l = bf16_rne(r2)
    resid = np.max(np.abs(x.astype(F64) - (h.astype(F64) + m.astype(F64) + l.astype(F64))))
    return (h, m, l), resid


def block(S0, q, k, v, decay, beta, dtype, split_pieces=False):
    """Block form over all the given tokens. dtype = arithmetic type of every sum.

    split_pieces: route the two products that have an FP32 operand (S0 and Delta)
    through three bf16 pieces each, summed piece by piece, as tile products would.
    """
    C = len(q)
    T = dtype
    S0t = S0.astype(T)
    K = k.astype(T)
    Qs = (q * SCALE).astype(F32).astype(T)
    resid = 0.0
    if split_pieces:
        pieces, resid = split3_bf16(S0.astype(F32))
        UK = sum((K @ p.astype(T)).astype(T) for p in pieces)
        # q*scale is not a bf16 value; a tile kernel would use bf16 q and scale afterwards
        UQ = sum((q.astype(T) @ p.astype(T)).astype(T) for p in pieces) * T(SCALE)
    else:
        UK = (K @ S0t).astype(T)
        UQ = (Qs @ S0t).astype(T)
    G = (K @ K.T).astype(T)
    H = (Qs @ K.T).astype(T)
    # D[j][t] = prod_{i=j+1..t} decay_i, 0 <= j <= t <= C  (token t is 1-based here)
    D = np.ones((C + 1, C + 1), T)
    for j in range(C + 1):
        for t in range(j + 1, C + 1):
            D[j, t] = T(D[j, t - 1] * T(decay[t - 1]))
    Delta = np.zeros((C, VD), T)
    out = np.zeros((C, VD), T)
    for t in range(1, C + 1):
        r = D[0, t] * UK[t - 1]
        for j in range(1, t):
            r = r + (D[j, t] * G[t - 1, j - 1]) * Delta[j - 1]
        Delta[t - 1] = (v[t - 1].astype(T) - r) * T(beta[t - 1])
        o = D[0, t] * UQ[t - 1]
        for j in range(1, t + 1):
            o = o + (D[j, t] * H[t - 1, j - 1]) * Delta[j - 1]
        out[t - 1] = o
    W = (D[1:, C][:, None] * Delta).astype(T)   # decay-weighted deltas, FP32 values
    if split_pieces:
        pieces, r2 = split3_bf16(W.astype(F32))
        resid = max(resid, r2)
        upd = sum((K.T @ p.astype(T)).astype(T) for p in pieces)
    else:
        upd = (K.T @ W).astype(T)
    S = (D[0, C] * S0t + upd).astype(T)
    return S, out, resid


def run_blocks(S0, toks, C, dtype, split_pieces=False):
    q, k, v, decay, beta = toks
    S = S0.astype(dtype)
    outs = []
    worst = 0.0
    for b in range(0, len(q), C):
        sl = slice(b, b + C)
        S, o, resid = block(S, q[sl], k[sl], v[sl], decay[sl], beta[sl], dtype, split_pieces)
        outs.append(o)
        worst = max(worst, resid)
    return S, np.concatenate(outs), worst


def bf16_words(x):
    """bf16 word of each value on a monotonic integer scale (one step = one bf16 notch)."""
    w = (bf16_rne(x.astype(F32)).view(np.uint32) >> 16).astype(np.int64)
    return np.where(w < 0x8000, w, -(w & 0x7FFF))


def report(name, S, o, S_ref, o_ref, S_seq, o_seq):
    smax = np.max(np.abs(S_ref))
    omax = np.max(np.abs(o_ref))
    eS = np.max(np.abs(S.astype(F64) - S_ref)) / smax
    eO = np.max(np.abs(o.astype(F64) - o_ref)) / omax
    dS = np.max(np.abs(S.astype(F64) - S_seq.astype(F64))) / smax
    dO = np.max(np.abs(o.astype(F64) - o_seq.astype(F64))) / omax
    w = bf16_words(o)
    ws = bf16_words(o_seq)
    changed = np.mean(w != ws)
    notch = np.max(np.abs(w - ws)) if changed > 0 else 0
    print(f"  {name:<34} vs oracle: state {eS:.2e} out {eO:.2e} | vs per-token FP32: "
          f"state {dS:.2e} out {dO:.2e} | bf16 output words changed {100*changed:.3f} % "
          f"(max {notch} notch)")
    return dict(eS=eS, eO=eO, dS=dS, dO=dO, changed=changed)


def main():
    n_tokens = int(sys.argv[1]) if len(sys.argv) > 1 else 128
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20261120
    rng = np.random.default_rng(seed)
    toks = make_tokens(rng, n_tokens)
    S0 = np.zeros((KD, VD), F32)

    # 1. Algebra: block form in float64 against per-token form in float64.
    S_ref, o_ref = seq_f64(S0, *toks)
    print(f"tokens = {n_tokens}, key width {KD}, value width {VD}, one value head")
    print(f"max |state| = {np.max(np.abs(S_ref)):.3f}, max |output| = {np.max(np.abs(o_ref)):.3f}")
    print("1. Algebra check (float64 block form minus float64 per-token form, relative to max):")
    for C in (16, 32, 64):
        S_b, o_b, _ = run_blocks(S0, toks, C, F64)
        print(f"  C = {C:<3} state {np.max(np.abs(S_b - S_ref))/np.max(np.abs(S_ref)):.2e}"
              f"  output {np.max(np.abs(o_b - o_ref))/np.max(np.abs(o_ref)):.2e}")

    # 2 and 3. FP32: per-token form (C++ order, fma) against block forms.
    S_seq, o_seq = seq_f32(S0, *toks)
    print("2. FP32 results, relative to the largest magnitude (FP32 epsilon = 6.0e-08):")
    report("per-token FP32 (today's kernel)", S_seq, o_seq, S_ref, o_ref, S_seq, o_seq)
    for C in (16, 32, 64):
        S_b, o_b, _ = run_blocks(S0, toks, C, F32)
        report(f"block C={C} FP32", S_b, o_b, S_ref, o_ref, S_seq, o_seq)
    for C in (16, 32, 64):
        S_b, o_b, resid = run_blocks(S0, toks, C, F32, split_pieces=True)
        report(f"block C={C} FP32, 3 bf16 pieces", S_b, o_b, S_ref, o_ref, S_seq, o_seq)
        print(f"      largest |x - (h+m+l)| of the 3-piece split: {resid:.1e} (0 = exact)")

    # Absolute numbers for the existing test tolerance (1e-7 absolute).
    S_b, o_b, _ = run_blocks(S0, toks, 32, F32)
    print("3. Absolute differences, block C=32 FP32 against per-token FP32:")
    print(f"  state  max |diff| = {np.max(np.abs(S_b - S_seq)):.2e}  (test tolerance 1e-7 absolute)")
    print(f"  output max |diff| = {np.max(np.abs(o_b - o_seq)):.2e}  (test tolerance 1e-7 absolute)")
    print(f"  per-token FP32 against the float64 oracle: state {np.max(np.abs(S_seq - S_ref)):.2e}, "
          f"output {np.max(np.abs(o_seq - o_ref)):.2e}")


if __name__ == "__main__":
    main()
