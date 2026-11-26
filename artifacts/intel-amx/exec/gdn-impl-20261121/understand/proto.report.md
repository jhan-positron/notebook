# Part A block algorithm: specification extracted from the Python prototypes

## Short version

- The prototypes agree on the algebra. They differ in four numeric details: split rule, order of the stage-1 sums, place of the query scale, and form of the final write. The form that matches design.txt 5.3/5.4 is `block_spec` in vm_engine.py [V1]: truncation split, key block outer and pieces lo-mid-hi inner, scale inside the FP32 coefficients, final write `S = fma(g_B, S0, T)` with T built from zeroed tiles.
- That form was checked against the token loop on 9 scenarios [V2] and on 42 more runs of 128 tokens that I ran with unmodified copies of the engines [X]. Worst differences at 128 tokens: outputs 7.8e-7 of max|o| (10 FP32 spacings), state 1.23e-6 of max|S| (15 spacings), 0.117 % of bf16 output words.
- Three things are not covered by any script: a fallback that works (the two guards of the old specification miss an overflow case), overflow of tile product 3, and the state layout the kernel sees.

## Words used here

- bf16: 16-bit float, the top 16 bits of an FP32 pattern. FP32 spacing ("sp"): gap between neighbouring FP32 values at the largest magnitude of a quantity, `2^(floor(log2 m) - 23)` [V1]:325-327.
- Token path: `gdn_recurrence` [T1]. Block form: 32 tokens at once. Split: one FP32 value written as 3 bf16 pieces. TDPBF16PS: the AMX tile product of bf16 pairs.
- B = 32 tokens per block, DK = 128 key rows, DV = 128 value columns, 2 value heads per key head.

## Files read (tags used below)

| Tag | Absolute path |
|---|---|
| T1 | /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/kernels/gated_delta_net.hpp |
| T2 | /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/gdn_rolling_executor.hpp |
| T3 | /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/common/numerics/bf16.hpp |
| T4 | /home/jhan/workspace/ai-runs/tron-qwen35-4b/src/tron/kernels/amx_attn.cpp |
| T5 | /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_gated_delta_net.cpp |
| K0 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/kernel/gdn_common.py |
| K1 | .../design-checks/kernel/01_block_algebra_check.py and .out (same folder as K0) |
| K2 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/kernel/02_split3_exhaustive.py and .out |
| K3 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/kernel/03_amx_emulation.py and .out |
| K4 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/kernel/04_cost_model.py and .out |
| K7 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/kernel/07_tile_layout_check.py and .out |
| P | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/proto/gdn_block_proto.py and .out |
| L1 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/lead/lead_numerics.py and .out |
| L2 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/lead/lead_l1_sim.py and .out |
| L3 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/lead/lead_costs.py and .out |
| V1 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-math/vm_engine.py |
| V2 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-math/vm_checks.py and .out |
| V3 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-math/vm_cross.py and .out |
| V4 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-math/vm_longmem.py and .out |
| V5 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-math/vm_subnormal.py and .out |
| R1 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/review/r3_split_facts.py and .out |
| R2 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/review/r3_rule_variants.py and .out |
| R3 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/review/r4_scale_check.py and .out |
| I1 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/integration/gdn_block_math.py (no saved output) |
| C1 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-cost/bench_gdn.c (not in my list, holds C code of the AVX-512 parts) |
| C2 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-cost/recount_tiles.py and .out |
| S1 | /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/skeptic/numerics_check.out |
| D | /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/design.txt |
| X | /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/blockspec-reader/band128.py and band128.out (my run, copies of V1, V2, P unchanged) |

Identical copies: lead/proto_copy.py, verify-math/proto_copy.py, verify-math/proto_rerun.py = P (same md5). verify-math/lead_numerics_rerun.py = L1; its output differs from L1's only in the run-time line. Not about Part A: 05_forward_estimate.py, 06_decode_fused_check.py (decode idea of design 5.7), integration/cost_arith.py, lead_costs forward part.

## 1. Token form as the C++ computes it

Source [T1]:231-300. All arithmetic is FP32, round to nearest even, one `__m512` chunk = 16 value columns.

- Scale: `static_cast<float>(1.0 / std::sqrt(static_cast<double>(key_head_dim)))` [T1]:242-243. For 128 this is 0x3DB504F3 = 0.0883883461 [R3] out line 1.
- Per key head: q and k go through `normalize_gdn` [T1]:250-253. Its last operation rounds to bf16 [T1]:192. So q and k are bf16 values held in FP32.
- Per value head: `decay = std::exp(-A_exp[vh] * gdn_softplus(round_to<bf16>(decay_input[vh]) + dt_bias[vh]))` [T1]:259-262. Decay is a true FP32 scalar, not rounded. `beta = round_to<bf16>(sigmoid(round_to<bf16>(update_input)))` [T1]:196-199, 264.
- Loop 1 [T1]:266-275, key coordinate i ascending 0..127, accumulator starts at +0:
  - `decayed_state = state[vh][i].chunk(c) * decay_values` (multiply, rounded)
  - `remembered_value[c] = fma(normalized_key, decayed_state, remembered_value[c])`
- Delta [T1]:277-282: `value_values = round_chunk_to<bf16>(value.chunk(...))`, then `delta[c] = (value_values - remembered_value[c]) * beta`. That is a subtract and then a multiply, two roundings. It is not an fma.
- Loop 2 [T1]:284-294, i ascending, result starts at +0:
  - `scaled_query(normalized_query_values[i] * query_scale)`: scalar FP32 multiply, rounded once, then broadcast [T1]:287.
  - `new_state = fma(normalized_key, delta[c], state[vh][i].chunk(c) * decay_values)`, stored [T1]:289-291.
  - `result[c] = fma(scaled_query, new_state, result[c])` [T1]:292.
- Output is stored FP32 and unrounded [T1]:296-297. `fma` is `_mm512_fmadd_ps` (/home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/simd/fp32.hpp:584-586).
- Rounded to bf16 in the token path: q, k, v, the decay input, beta (before and after sigmoid). Not rounded: decay, state, delta, the scaled query, the output [T1]:36-39.
- The first act of `postprocess` rounds the recurrence output to bf16 [T2]:450-452. So "bf16 output words" in every prototype are the words that postprocess would see.
- bf16 rounding rule [T3]:91-97: NaN keeps top bits and sets 0x0040; exponent field 0 (zero or subnormal) becomes signed zero; else `(bits + 0x7fff + ((bits >> 16) & 1)) >> 16`.
- The executor rejects NaN in a start state, not infinity: "Infinities retain their IEEE 754 meaning" [T2]:108-109, check at [T2]:419-437. tron sets no flush-to-zero mode (grep for MXCSR/DAZ/FTZ in h/ and src/ found only fp8 comments and host_matvec.hpp:25).

## 2. Block form

### Definitions (design figure 12, [D]:634) and script names

Tokens t = 1..B inside a block, d_t the decay of token t.

- g_t = d_1 ... d_t. w_tu = d_(u+1) ... d_t for u < t, w_tt = 1.
- KS0 = K S0 (B x 128), QS0 = Q S0 (B x 128). G = K K^T, H = Q K^T (B x B).
- r_t = g_t (KS0)_t + sum over u<t of w_tu G_tu delta_u.
- delta_t = beta_t (v_t - r_t).
- o_t = scale (g_t (QS0)_t + sum over u<=t of w_tu H_tu delta_u).
- S_B = g_B S0 + K^T (w . Delta), row u of (w . Delta) = w_Bu delta_u.

Name collision to watch: the design's G and H are `KK`/`QK` in [V1], [P], [L1], `A`/`B` in [K1], [K3], and `G`/`H` in [I1]. In [V1], [P], [L1] the name `G` is the decay-product matrix (design's w, with column 0 = g). In [K1], [K3] `G` is the vector g and `Gam` is w. In [K7] `G` is the Gram result.

Algebra proof: float64 block form equals float64 token form to 1.3e-15 [K1] out line 23. Exact rational check with three mutations [V2]:29-82 and out lines 4-8. The mutations pin three index facts: o_t includes the u = t term, r_t uses g_t (not g_(t-1)), and W uses row B of w (not row B-1).

### Decay products "by multiplication only"

[V1]:219-232 (same code in [P]:285-297 and [L1]:58-63):

```
G = np.zeros((H, C + 1, C + 1), f32)
G[:, 0, 0] = 1
for t in range(1, C + 1):
    G[:, t, :t] = G[:, t - 1, :t] * d[:, t - 1, None]
    G[:, t, t] = 1
gam = G[:, :, 0]
```

- So w_tu = fl(...fl(fl(d_(u+1) * d_(u+2)) * d_(u+3))... * d_t): row t is row t-1 times d_t, one rounded FP32 multiply per entry. g_t = G[t][0] is built the same way. The diagonal is exactly 1.
- The form to avoid is `gam_c[:, :, None] / gam_c[:, None, :]` [P]:291-296. With decay 0.05-0.5 and C = 64 it gives output differences of 1.08e-4 and 2,454 of 524,288 differing bf16 words; at C = 128 it gives 486,272 non-finite outputs [P] out lines 342-345. [V2] F2 repeats it: 2.183e-05 and 260 words against 7.451e-09 and 14 words by products [V2] out, part F.
- With products every value stayed finite, also when G underflows: 661 subnormal and 3,655 zero entries of 8,448 in scenario tinydecay [V2] out.

### Stage 3 (forward substitution), exact FP32 order

Specified form [V1]:258-274 ([L1]:67-82 and [P]:311-335 are the same order):

```
Gt = G[:, 1:, 1:]
CK = Gt * KK                      # one multiply
CQ = (Gt * QK) * SCALE            # two multiplies, in this order
sg = gam[:, 1:] * SCALE           # one multiply
for t in range(C):
    r = gam[:, t + 1, None] * R0[:, t]          # multiply, not fma
    for u in range(t):
        r = fma32(CK[:, t, u, None], Delta[:, u], r)      # u ascending
    Delta[:, t] = (Vc[:, t] - r) * b[:, t, None]          # subtract, then multiply
    o = sg[:, t, None] * U0[:, t]               # multiply
    for u in range(t + 1):
        o = fma32(CQ[:, t, u, None], Delta[:, u], o)      # u ascending, last term uses the new Delta[t]
    O[:, t0 + t] = o
```

- R0 = K S0, U0 = Q S0 (the design's KS0, QS0). CQ[t][t] = fl(QK[t][t] * scale) because G[t][t] = 1.
- The same loop in C with intrinsics exists: `triangle` in [C1]:206-231 (`_mm512_mul_ps` for the two starts, `_mm512_fmadd_ps` in the u loop, `mul(sub(V, r), b)`, last `fmadd(cq_tt, d, o)`).
- Operation count: 8 x 32 x 31 + 40 x 32 = 9,216 zmm operations per block and value head [V2] out part G; coefficients 223 [C2] out line 56.

### Where the scale 1/sqrt(128) is applied

- Specified form: inside the FP32 coefficients, `CQ = (Gt * QK) * SCALE` and `sg = gam * SCALE` [V1]:262-263. This matches [D]:689-690 ("applies the scale to the coefficients of the read sum") and figure 12 note "scale = 1 / sqrt(128), in the FP32 coefficients" [R3]:45.
- Deviations: [K3]:102 applies it once at the end, `out = (scale * acc_o)`. [I1]:125 applies it to the tile result UQ and uses `Qs K^T` in FP32 for H [I1]:119,130. Both give other bits. Use the specified form.
- Q enters the tile products as plain bf16 q (scale x q is not a bf16 value).

### Final write

- Specified form (update "Y"): tile product 3 starts from zero, then one fma. [V1]:276-283:
  ```
  W = G[:, C, 1:, None] * Delta          # one multiply per value; W[B] = Delta[B]
  wp = split(W, pieces)
  Tm = np.zeros((H, DK, DV), f32)
  for p in wp:                           # lo, mid, hi
      for tb in range(0, C, 32):
          Tm = tdp_block(KT[:, :, tb:tb + 32], p[:, tb:tb + 32, :], Tm, ftz)
  S = fma32(gam[:, C, None, None], S, Tm)
  ```
  With B = 32 there is one token block, so per element T = ((0 + P_lo) + P_mid) + P_hi and S_B = fma(g_B, S0, T).
- This matches [D]:620 ("writes the decayed start state plus the update for these values (64 FMAs)") and the counts of [L3]:67-79 and [C2].
- Deviation (update "X"): the accumulator tile starts at fl(g_B * S0) and the tile products add into it. Used by [K3]:104-110, [P]:338,344, [K7]:93-101, [K4]:94-115. [L1] ran both: results differ in a few words only (for example 35 against 36 differing words, [L1] out lines 8-9).

### What the prototypes round or truncate

- Only the split truncates (section 3). Every other step is FP32 round to nearest. Nothing inside the block form is rounded to bf16. The output is unrounded FP32.
- [K0]:47-55 `fma32` is a double-rounding emulation ("can differ from a true fma in rare ties"). [P]:62-83 and [V1]:69-79 emulate a true fma (TwoSum plus round to odd, checked against rational arithmetic: 0 wrong of 22,000 and of 4,000). Take [V1]/[P] as the bit reference, not [K3].

## 3. Split rule and TDPBF16PS model

### Rule as checked

[V1]:41-54 (same in [K3]:27-32, [L1]:30-41, [K2]:34-35, [R1]:104-105):

```
def trunc16(x):  return (x.view(u32) & u32(0xFFFF0000)).view(f32)
hi  = trunc16(x)
rem = x - hi          # FP32 subtract
mid = trunc16(rem)
lo  = rem - mid       # FP32 subtract, kept as it is
```

- Pieces are consumed smallest first: lo, mid, hi.
- The tile reads the top 16 bits of each piece [R1]:124-127. For |x| >= 2^-110 the third piece already has its low 16 bits clear.
- [P]:199-208 uses round to nearest for all three pieces. That is the other rule; do not use it.

### Proven range (every finite FP32 pattern of both signs, 4,278,190,080 patterns)

Source [R1] out lines 15-21 and [V2] out part C.

| Band of abs(x) | Patterns | Sum hi+mid+lo = x | Third piece is bf16 | A subnormal piece | Largest part the tile does not read |
|---|---|---|---|---|---|
| 2^-103 (0x0C000000) to largest FP32 | 3,875,536,896 | all | all | 0 | 0 |
| 2^-110 to 2^-103 | 117,440,512 | all | all | 30,603,008 | 1.166311e-38 |
| 2^-126 to 2^-110 | 268,435,456 | all | 251,658,496 are not | 267,251,712 | 1.175476e-38 |
| below 2^-126 | 16,777,216 | all | 16,776,960 are not | 16,777,214 | 1.175494e-38 (2^-126) |

- No piece is ever non-finite under truncation; no piece has a sign different from x [V2] out part C.
- Largest part that three bf16 values cannot hold at all: 9.183409e-41, below 2^-133 [R1] out.
- Split of the largest FP32 0x7F7FFFFF: 0x7F7F0000, 0x7B7F0000, 0x777F0000 (3.3895314e38, 1.3240357e36, 5.1720144e33).
- Split of inf gives hi = inf, mid = NaN, lo = NaN. Split of -0.0 gives -0.0, 0, 0 [V2] out part C.
- Round to nearest fails at the top: 65,536 patterns (abs(x) >= 2^128 - 2^119 = 0x7F7F8000) give an infinite first piece [R1] out part D.
- Two pieces are not enough: state error 7.5e-8 to 1.6e-5 [V2] variants, [P] check summary.

### TDPBF16PS as the emulation models it

Statement in the scripts: "starts two FP32 temporaries at zero, adds the 16 products of the even inner elements into one and the 16 products of the odd inner elements into the other (round to nearest even at every add, input subnormals read as zero, output subnormals flushed to zero), adds the two temporaries, then adds that sum to C[m][n]" [K3]:5-11; "DAZ=FTZ=1" quoted from the SDM pseudo-code [K2]:19-20. The scripts say the SDM text was checked on 2026-11-20; I did not re-check it.

Literal model with DAZ and FTZ [V1]:122-123, 148-157:

```
TINY = f32(2.0 ** -126)
def _flush(x): return np.where(np.abs(x) < TINY, f32(0.0), x).astype(f32)

def tdpbf16ps_literal(C, A, B):
    """A [16][32], B [16][32] (row k holds 16 pairs: B[k][2n], B[k][2n+1]), C [16][16]. DAZ and FTZ on."""
    A, B, C = _flush(A), _flush(B), _flush(C)
    te = np.zeros((16, 16), f32)
    to = np.zeros((16, 16), f32)
    for k in range(16):
        te = _flush(fma32(A[:, 2 * k, None], B[None, k, 0::2], te))
        to = _flush(fma32(A[:, 2 * k + 1, None], B[None, k, 1::2], to))
    return _flush(C + _flush(te + to))
```

Model without DAZ/FTZ, the one [K7] compares against [K7]:24-31:

```
for m in range(16):
    t = np.zeros(32, F32)
    for k in range(16):
        t[0::2] = (t[0::2] + a[m, 2 * k] * b[k, 0::2]).astype(F32)
        t[1::2] = (t[1::2] + a[m, 2 * k + 1] * b[k, 1::2]).astype(F32)
    c[m] = (c[m] + (t[0::2] + t[1::2]).astype(F32)).astype(F32)
```

- C scalar reference: per (m, n) keep `te`, `to` = +0; for k = 0..15 ascending `te = ftz(fmaf(daz(A[m][2k]), daz(B[k][2n]), te))`, `to = ftz(fmaf(daz(A[m][2k+1]), daz(B[k][2n+1]), to))`; then `C[m][n] = ftz(daz(C[m][n]) + ftz(te + to))`. daz/ftz: magnitude below 2^-126 becomes 0.
- A bf16 word is subnormal exactly when the FP32 piece is below 2^-126.
- DAZ/FTZ changed no bit in three scenarios: "no DAZ/FTZ ... 0 FP32 output values, 0 FP32 state values, 0 bf16 words differ" [V2] out (base, testmag, repkeys).
- The real kernel call order is `_tile_dpbf16ps(accumulator, A, B)` as in [T4]:167. Tiles are 16 rows by 64 bytes, all 8 configured in `begin_region` [T4]:115-123.

## 4. Tile layouts verified bit for bit

[K7] cuts real 16 x 32-element tiles out of buffers and compares with the logical product; all three print True [K7] out. [V2] part D repeats it with DAZ/FTZ and with tile product 3 from zero: "384 / 32 / 192 literal tile products; bits equal to the logical form: True" [V2] out.

Buffers [K7]:9-16:

```
KQ_a   [2C rows][128]            row-major, rows 0..C-1 = K, C..2C-1 = Q
S_p    [64 key pairs][128][2]    piece p of S0; (j, c, e) = piece(S0[2j+e][c])
KT_b   [C/16][4][16 pairs][16 tokens][2]   (cb, kb, j, n, e) = K[16cb+n][32kb+2j+e]
KT_a   [128 key coords][C]       (i, t) = K[t][i]
W_p    [C/2 token pairs][128][2] (j, c, e) = piece(W[2j+e][c])
```

Rule for every product: A tile is row-major (row m = output row, 32 bf16 = inner index 2k+e). B tile is pair-interleaved (row k = inner pair, element 2n+e = (inner 2k+e, output column n)).

| | Tile product 1: [K;Q] x S0 | Tile product 2: [K;Q] x K^T | Tile product 3: K^T x (w . Delta) |
|---|---|---|---|
| A operand | KQ_a rows 16r..16r+15, elements 32kb..32kb+31 (stride 256 B) | same | KT_a rows 16rb..16rb+15, elements 32tb.. (stride 64 B at B = 32) |
| B operand | piece p of S0: B[k][2n+e] = piece(S0[32kb+2k+e][16col+n]) | KT_b[cb][kb]: B[j][2n+e] = K[16cb+n][32kb+2j+e] | piece p of W: B[k][2n+e] = piece(W[32tb+2k+e][16col+n]) |
| C tile | RU[16r..][16col..], RU = [64][128] FP32: rows 0..31 = K S0, rows 32..63 = Q S0 | GH[16r..][16cb..], GH = [64][32] FP32: rows 0..31 = K K^T, 32..63 = Q K^T | T[16rb..][16col..], T = [128][128] |
| Loop nest (verified) | col 0..7 > r 0..3 > kb 0..3 > piece lo, mid, hi [K7]:50-56 | cb 0..1 > r 0..3 > kb 0..3 [K7]:73-78 | col 0..7 > rb 0..7 > tb > piece lo, mid, hi [K7]:95-101 |
| Kernel loop (cost scripts) | col > zero T0-T3 > kb: load 3 pieces to T4-T6; r: load A to T7, 3 products [C2] gdn_p1 | cb > zero T0-T3 > kb: load B to T4; r: load A to T7, 1 product [C2] gdn_gram | col > group g 0..1 > zero T0-T3 > load 3 W pieces; r: load A to T7, 3 products; store 4 tiles [C2] gdn_update |
| Per block: TDPBF16PS / loads / stores / zeros | 384 / 224 / 32 / 32 per value head | 32 / 40 / 8 / 8 per key head | 192 / 112 / 64 / 64 per value head (from zero). Form X: 192 / 176 / 64 / 0 [K4] out. With W tiles kept over both groups: 88 loads [C2] out line 49 |

- Per value head with the Gram halved: 592 products, 356 loads, 100 stores = 18.5 products per token [C2] out, [L3] out.
- All 8 tile registers are live in products 1 and 3 [C2] out ("registers live at once 8 of 8"). Today's attention kernel uses 7.
- The accumulation order per element in product 1 is key block outer, pieces inner. [K7] and [V2] part D verify exactly this order.

Buffer sizes for B = 32 ([L3] out line 132, [C1]:179):

- Split buffer of 16 value columns: 4 key blocks x 3 pieces x 1 KiB = 12,288 B. Layout in [C1]:194: `scratch + kb*3*1024 + piece*1024 + row*64`, piece 0 = lo, 1 = mid, 2 = hi.
- KQ_a 16,384 B. KT_a 8,192 B. KT_b 8 tiles = 8,192 B. RU 32,768 B. GH 8,192 B. W pieces 24,576 B per value head. T scratch 4 tiles = 4,096 B. Coefficients CK, CQ 4,096 B each per value head. Delta 16,384 B.
- K is needed in three bf16 layouts (KQ_a, KT_a, KT_b). The Gram B packing is "not in the spec's list" [C2] out line 60. KT_b[cb][kb] is the 16 x 16 transpose of 32-bit lanes: lane (j, n) = pair lane 16kb+j of key row 16cb+n.
- AVX-512 operation counts per block and value head [C2] out lines 52-60: split of S0 8,192 (4 split + 3 pack + 1 guard per zmm), triangle 9,216, scale+split of W 2,304, final fma 1,024, coefficients 223, packs 256 + 320 + 256 per key head halves.

## 5. Fallback rule and the overflow case

- Design rule [D]:751-758: a block takes the column-half path "when its start state or an intermediate result is not finite. The state is still untouched at that point." Values below 2^-103 take no fallback.
- What the scripts model: only two guards, on S0 and on W. [V2]:395: "the two guards of the specification test S0 and W only". The guard in C is `guard = _mm512_fmadd_ps(x, zero, guard)` per zmm inside the split pass [C1]:182-186 (inf x 0 and NaN x 0 give NaN).
- Overflow case found [V2]:383-394 and out part F3: one head, 32 tokens, seed 55, start state = 5e37 x sign(q_1[i]) in every column, decay of token 1 = 0.01, other decays 0.4-0.6, beta 0.2-0.8.
  - Token loop: 0 non-finite outputs, largest abs(o_1) = 4.008e35.
  - Block form: 128 non-finite outputs (all of token 1), state finite. Cause: Q S0 is formed before the decay is applied. S0 and W are finite, so neither guard fires.
- No prototype implements or tests a fallback.
- A start state with infinity is legal in the token path [T2]:108-109, and its split gives NaN pieces. So the S0 guard is required for bit parity, not only for safety.
- Reader's inference, not checked by a script: a guard on S0, on the 32 output rows and on W catches every non-finite value of stages 1 to 3 (K S0 -> delta -> W, Q S0 -> o). It does not catch an overflow inside tile product 3 or in the final fma; see open questions.

## 6. Measured differences, inputs, proposed thresholds

### Saved results (all Python emulation, synthetic inputs)

| Check | Form | bf16 output words that differ from the token loop | Block against token loop | Error against float64 as a multiple of the token loop |
|---|---|---|---|---|
| [P] out check summary, 4 heads x 1,024 tokens, 5 scenarios, worst over C = 8..128 | round-to-nearest split, pieces outer, write X | 0.0050 % to 0.0317 % | outputs 4.5 to 7.0 sp, state 1.0 to 4.0 sp | outputs 0.30 to 0.65, state 0.55 to 1.75 |
| [L1] out, 4 x 256 tokens, C = 32 and 64 | truncation, pieces outer, X and Y | 0.0038 % to 0.0275 % | not printed | outputs up to 0.47, state up to 1.71 |
| [V2] out part E, 9 scenarios, C = 32 | specified form | 0.0061 % to 0.1015 % | outputs 3.5 to 10.0 sp, state 1.0 to 6.5 sp (33.0 sp in longmem at 1,024 tokens) | outputs 0.28 to 1.11, state 0.27 to 1.94 |
| [K3] out, 1 head x 128 tokens, C = 32 | scale at end, X, approximate fma | 0.018 % to 0.043 % | 1.5e-8 to 6.7e-8 abs | not printed as ratio |
| [S1], 8 heads x 128 tokens | bf16x3, B = 32 | 290 and 427 ppm | 3.35e-8 and 9.31e-8 abs | state 3.15 (2.34e-07 / 7.42e-08) |

- Step size: outputs at or above 1 % of the rms output differ by at most 1 bf16 step in every run. Outputs nearer to zero differ by up to 67 steps at C = 32 ([P] out line 110), 84 at C = 128.
- The first token of a block already differs in FP32 bits ("first token of the chain: FP32 output bits equal False"), and 0 bf16 words differ in tokens 1-4 [V2] out.
- Long chains [V4] out: decay 0.998-1.0, state difference block against token grows 4.5, 6.0, 11.0, 10.5, 24.0, 33.0 sp at 32..1,024 tokens. The token loop itself is 27.2 sp from float64 at 1,024 tokens.
- Loop order of product 1 matters for bits: key block outer against pieces outer differ in 3,571 of 16,384 FP32 outputs and 5,010 of 32,768 state values [V3] out 1c; 0 to 46 bf16 words [V2] variants.
- Truncation against round to nearest: 0 to 56 of 131,072 words differ; error ratio 0.99 to 1.13 [R2] out.
- Absolute 1e-7 is not a usable band: the token loop itself reaches 1.049e-07 in scenario normal [P] out line 144.

### My run for chains of 128 tokens [X]

Specified form ([V1] `block_spec` defaults), 4 heads x 128 tokens, 14 scenarios (9 of [V2], 5 of [P]) x 3 seeds = 42 runs. All finite. Worst values:

- Outputs: 10.0 sp = 7.78e-7 of max abs(o).
- State at any block end: 15.0 sp = 1.23e-6 of max abs(S). Relative L2 per head: 5.56e-7.
- bf16 words: 0.0061 % to 0.1175 %. At or above 1 % of rms: 1 step at most.
- Error against float64 as a multiple of the token loop: outputs 1.24, state 2.36.

### Input distributions used

- [K0]:59-76 `make_chain`: q, k = N(0,1), bf16, L2-normalized, bf16; v = bf16(v_scale x N(0,1)), v_scale 1.0 or 0.006; beta = bf16(sigmoid(N(0,1))); decay uniform 0.90-0.9999, or 0.5-1.0, or 1e-3 on every 7th token, or exactly 1; S0 = s_scale x N(0,1), 0.05 or 0.0015.
- [P]:418-466, seeds 101..505: k = N(0,1) with AR(1) correlation rho; q = a k + sqrt(1-a^2) N; both through the kernel's normalize; v log-uniform magnitude 0.01-1 with random sign, or uniform +-0.10; beta uniform, bf16.
  - normal: decay 0.9-1.0, beta 0-1, S0 N(0, 0.01). hard: decay 0.3-1.0. testmag: decay 0.70-0.85, beta 0.3-0.7, S0 uniform +-0.0035, a = 0.6. underflow: decay 0.05-0.5. corrkeys: rho 0.9, a = 0.7.
- [V2]:149-170, seeds 9000 + 17 i: base; testmag; longmem (decay exp(-U(0, 2e-3)) with 25 % exactly 1.0, beta 0-0.2, v and S0 N(0, 0.3)); bigmag (v N(0, 20), S0 N(0, 5), decay 0.5-1.0); tinydecay (decay 10^U(-6,-2)); lowdecay (0.02-0.10); zerostart (S0 = 0); repkeys (rho 0.99, a 0.7, beta 0.9-1.0, decay 0.99-1.0); rowspike (every 32nd key row of S0 x 1e5).
- Existing C++ generator for a 128-wide test: `recurrence_test_value` [T5]:55-58, used at [T5]:720-783.

### Proposed thresholds for the C++ error-band test (block path against token path, chains of 128 tokens or fewer, 128 x 128)

| Quantity | Worst observed | Proposed limit | Margin |
|---|---|---|---|
| max abs(o_block - o_token) per value head / max abs(o_token) | 7.8e-7 (10 sp) [X] | 4e-6 | 5.1x |
| max abs(S_block - S_token) at each block end / max abs(S_token) | 1.23e-6 (15 sp) [X] | 6e-6 | 4.9x |
| Relative L2 of the state difference per head | 5.6e-7 [X] | 3e-6 | 5.4x |
| Share of bf16 output words that differ | 0.1175 % [X], 0.1015 % [V2] | 0.5 % | 4.3x |
| bf16 step of outputs at or above 1 % of rms(o_token) | 1 step, every run | 1 step (2 if a margin is wanted) | none at 1 |
| Every value finite | yes in all runs | required | - |

- Optional float64 reference: state error at most 6x the token path's, outputs at most 2.5x (observed 3.15x [S1] and 1.24x [X]).
- For a 1,024-token test use 64 sp for outputs and 128 sp for the state (observed 20.0 and 33.0 sp [V4]).
- Do not put a step limit on outputs near zero.
- These limits come from the emulation on synthetic inputs. They are estimates for the C++ kernel until it is run.

## 7. Facts the design text does not give

- The accumulation order of tile product 1 (key block outer; lo, mid, hi inner) and that another order changes bits [V3], [V2].
- CQ is two multiplies in a fixed order, `(w * H) * scale`; `sg = g * scale`; r and o start with a multiply, not an fma; delta is subtract then multiply [V1]:258-274.
- W[B] = Delta[B] exactly, because w_BB = 1.
- Decay and beta are per value head [T1]:259-264. So g, w, CK, CQ, sg are per value head. Only the packs of K, Q and G, H are per key head.
- The pack in [C1]:195-196 is `or(srli(le, 16), lo)`, where `lo` is here the third piece of the odd key row. Below 2^-110 that piece has low bits set ([R1]: 268,435,456 patterns) and the OR would corrupt the even word. The stored word must be the top 16 bits only. `_mm512_mask_blend_epi16(0xAAAAAAAA, _mm512_srli_epi32(even, 16), odd)` does it with the same operation count (reader's proposal). The self-check in [C1] used normal values only and does not catch this.
- [K7] verified the final write in form X (TILELOADD from S). The from-zero form of the design is verified in [V2] part D.
- Subnormal decay products appear in the AVX-512 parts with small decays: 5.4 of 528 per block (lowdecay) and 41.3 of 528, in 23 of 64 zmm registers (tinydecay); the token loop has none [V5] out. tron sets no FTZ, so these take the slow path of the CPU.
- A 16-spacing band against float64 was proposed in the old specification and is too tight: the token loop is 16.3 and 27.2 sp away at 512 and 1,024 tokens [V4]; the worst-case error of g_32 alone is 15.5 to 31 sp [V2] out F4.
- bf16 words after postprocess differ about as often as the recurrence words: 0.6x to 1.2x [V2] out ("est., unit weight, random gate").
- L1 model: tile-load lines found in L1 at B = 32: 86.6 % for product 1, 68.3 % (row-major state) or 71.4 % (state in blocks of 16 columns) for product 3 [L2] out. The product-1 model assumes the state is stored as [value block of 16 columns][128 rows][16] [L2]:38, as does `split_pack_block` [C1]:178-180.
- No written "block_algorithm" / "tile_mapping" text exists under /home/jhan/workspace/intel-AMX/exec/gdn-20261120 (searched md, json, txt, html). [V1] `block_spec` and [V2] part D are its executable form.

## Pseudo-code: one key head (2 value heads), one block of 32 tokens

```c
enum { B = 32, DK = 128, DV = 128, NVH = 2 };
static const float scale = 0x1.6a09e6p-4f;          /* bits 0x3DB504F3 = (float)(1.0 / sqrt(128.0)) */

/* inputs from phase 1 of advance() */
const float Kf[B][DK], Qf[B][DK];                   /* normalized, bf16-exact, per key head            */
const float V[NVH][B][DV];                          /* bf16-exact                                       */
const float d[NVH][B], beta[NVH][B];                /* decay: FP32. beta: bf16-exact                    */
float S[NVH][DK][DV];                               /* state [key row i][value column c], in and out    */
float O[NVH][B][DV];                                /* recurrence output, FP32, not rounded             */

/* scratch */
bf16  KQ_a[2*B][DK];            /* 16 KiB  rows 0..31 = K, rows 32..63 = Q                             */
bf16  KT_b[B/16][4][16][16][2]; /*  8 KiB  [cb][kb][j][n][e] = K[16cb+n][32kb+2j+e]                    */
bf16  KT_a[DK][B];              /*  8 KiB  [i][t] = K[t][i]                                            */
float GH[2*B][B];               /*  8 KiB  GH[t][u] = k_t.k_u ; GH[32+t][u] = q_t.k_u                  */
float Wm[B][B+1];               /* Wm[a][0] = g_a ; Wm[a][b+1] = w_ab (b <= a) ; Wm[a][a+1] = 1        */
float CK[B][B], CQ[B][B], sg[B];
bf16  Ssplit[4][3][16][16][2];  /* 12 KiB  [kb][piece 0 lo,1 mid,2 hi][k][n][e] = piece(S[32kb+2k+e][16col+n]) */
float RU[2*B][DV];              /* 32 KiB  rows 0..31 = K S0 (R0), rows 32..63 = Q S0 (U0)             */
float Delta[B][DV];
bf16  Wp[8][3][16][16][2];      /* 24 KiB  [col][piece][j][n][e] = piece(W[2j+e][16col+n])             */
float Tscr[4][16][16];          /*  4 KiB                                                              */

/* split of one FP32 value; word = top 16 bits of the piece */
split3(x): h = x & 0xFFFF0000 (bit op); r = x - h; m = r & 0xFFFF0000; l = r - m;   /* FP32 subtracts */
           words: hi = bits(h) >> 16, mid = bits(m) >> 16, lo = bits(l) >> 16
/* pair pack of two rows (even e, odd o) of one piece into 16 lanes of 32 bits:
   lane n = (bits(e[n]) >> 16) | (bits(o[n]) & 0xFFFF0000)                                           */

/* ---- once per key head ---- */
for t, i: KQ_a[t][i] = bf16(Kf[t][i]); KQ_a[B+t][i] = bf16(Qf[t][i]);        /* exact */
build KT_a, KT_b from K
/* tile product 2: 32 products, 40 loads, 8 stores */
for cb in 0..1:
  zero T0..T3
  for kb in 0..3:
    T4 <- KT_b[cb][kb]                                  (stride 64 B)
    for r in 0..3: T7 <- &KQ_a[16r][32kb] (stride 256 B); TDPBF16PS(Tr, T7, T4)
  for r in 0..3: Tr -> &GH[16r][16cb]                   (stride 128 B)

/* ---- per value head h ---- */
/* decay products, multiplication only */
for a in 0..31:
  for c in 0..a: Wm[a][c] = (a == 0) ? d[h][0] : Wm[a-1][c] * d[h][a];   /* row a-1 has Wm[a-1][a] = 1 */
  Wm[a][a+1] = 1.0f;
/* coefficients */
for a in 0..31:
  sg[a] = Wm[a][0] * scale;
  for b in 0..a-1: CK[a][b] = Wm[a][b+1] * GH[a][b];
  for b in 0..a:   CQ[a][b] = (Wm[a][b+1] * GH[B+a][b]) * scale;          /* two multiplies, this order */

/* stage 1: split + tile product 1, 16 value columns at a time: 384 products, 224 loads, 32 stores */
guardS = 0
for col in 0..7:
  for j in 0..63:                                       /* key rows 2j, 2j+1 */
    xe = S[h][2j][16col..16col+15]; xo = S[h][2j+1][16col..16col+15];
    guardS = fma(xe, 0, guardS); guardS = fma(xo, 0, guardS);
    split3 both; Ssplit[j/16][piece][j%16] = pair pack(piece_e, piece_o) for piece = lo, mid, hi
  zero T0..T3
  for kb in 0..3:
    T4 <- Ssplit[kb][lo]; T5 <- Ssplit[kb][mid]; T6 <- Ssplit[kb][hi]   (stride 64 B)
    for r in 0..3:
      T7 <- &KQ_a[16r][32kb]                            (stride 256 B)
      TDPBF16PS(Tr, T7, T4); TDPBF16PS(Tr, T7, T5); TDPBF16PS(Tr, T7, T6)   /* lo, mid, hi */
  for r in 0..3: Tr -> &RU[16r][16col]                  (stride 512 B)
if guardS is not all zero: return FALLBACK              /* state untouched */

/* stage 3: forward substitution, per zmm chunk of 16 columns, a ascending */
for a in 0..31:
  r = Wm[a][0] * RU[a]            /* mul */
  o = sg[a]    * RU[B+a]          /* mul */
  for b in 0..a-1: r = fma(CK[a][b], Delta[b], r); o = fma(CQ[a][b], Delta[b], o)
  Delta[a] = (V[h][a] - r) * beta[h][a]                 /* sub, then mul */
  O[h][a]  = fma(CQ[a][a], Delta[a], o)

/* stage 4a: scale and split Delta */
guardW = 0; guardO = 0
for j in 0..15, col in 0..7:                            /* token rows 2j, 2j+1 */
  we = Wm[31][2j+1] * Delta[2j][16col..]; wo = Wm[31][2j+2] * Delta[2j+1][16col..];   /* w_Bu; Wm[31][32] = 1 */
  guardW = fma(we, 0, guardW); guardW = fma(wo, 0, guardW);
  split3 both; Wp[col][piece][j] = pair pack(piece_e, piece_o)
for a: guardO = fma(O[h][a], 0, guardO)                 /* not in the scripts; needed for case F3 */
if guardW or guardO is not all zero: return FALLBACK    /* state untouched; O is recomputed by the fallback */

/* stage 4b: tile product 3 from zero + final write: 192 products, 112 loads, 64 stores */
gB = Wm[31][0]
for col in 0..7:
  for rg in 0..1:
    zero T0..T3
    T4 <- Wp[col][lo]; T5 <- Wp[col][mid]; T6 <- Wp[col][hi]            (stride 64 B)
    for r in 0..3:
      T7 <- &KT_a[16*(4rg + r)][0]                      (stride 64 B)
      TDPBF16PS(Tr, T7, T4); TDPBF16PS(Tr, T7, T5); TDPBF16PS(Tr, T7, T6)
    for r in 0..3: Tr -> Tscr[r]                        (stride 64 B)
    for i in 0..63: S[h][64rg + i][16col..16col+15] = fma(gB, S[h][64rg + i][16col..16col+15], Tscr[i/16][i%16][0..15])
```

Index formulas for the pair-interleaved operands: element (k, 2n+e) of a B tile holds (inner index 2k+e, output column n). Element (m, 2k+e) of an A tile holds (output row m, inner index 2k+e). Call order `_tile_dpbf16ps(accumulator, A, B)`.