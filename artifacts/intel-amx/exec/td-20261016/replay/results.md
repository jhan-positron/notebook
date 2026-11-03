# Offline replay of software attention on real Q/K/V (issue #4444, td-20261016)

## Short version

The order in which the AVX dotter and the VNNI reader add the 128 products changes 64 % of the raw scores by one fp32 ulp (about 1e-7 relative), and that changes one or two bf16 output elements at roughly a third of the tokens. The bf16 rounding of the softmax weights is a far bigger mechanism: the AVX path truncates them (a systematic -0.16 % weight loss, output bias -0.08 %), the AMX path rounds them to nearest (bias about 0), and the two outputs differ in 20-30 % of their bf16 elements at every token that has a dense page. The replay reproduces the binary: the first token where the logged base and new arms differ is token 26 in both, and the replay's output pushed through the o_proj weights matches the logged WO record at the o_proj's own rounding floor.

## Words used here

- tron: the inference program under test. runtron: its command-line tool. The arms are runs of runtron on delphi-3bda with the same input tokens, the same weights and the full intermediates log (probe-td.sh).
- Arms (binary and setting): base (main, AMX on, row-major K), new (PR #4959 head: VNNI K + AMX), poc (new with the VNNI blocks unpacked and scored by the row-major dotter), newoff (new with the AMX kill switch TRON_AMX_DISABLE=1), trunc (new with the AMX PV weights truncated like the AVX path), baseoff (base with the kill switch), pocoff (poc with the kill switch), clean (main built without AMX).
- AMX: Intel Advanced Matrix Extensions, the tile instructions (TDPBF16PS). AVX-512: the vector instructions (VDPBF16PS). VNNI K: the K cache layout of PR #4959 (dimension pairs interleaved per 16-token block).
- bf16: 16-bit brain float (8 bits of mantissa, relative spacing 2^-8 = 0.39 %). fp32: 32-bit float (24-bit mantissa, relative spacing 2^-23 = 1.2e-7). ulp: one unit in the last place, the spacing between two neighbouring floats at that magnitude. "One fp32 ulp" is about 1e-7 of the value. "One bf16 notch" is 0.39 % of the value.
- RNE: round to nearest, ties to even. Truncation: drop the low bits (always rounds toward zero).
- Score paths (how q . k is summed, all with exact bf16 x bf16 products in fp32):
  - D: the row-major dotter (dotter<bf16,128>, h/tron/kernels/dotter.hpp:211-221): 16 lanes of VDPBF16PS, then a halving tree.
  - R: the VNNI reader (k_vnni::qk_group, h/tron/kernels/k_vnni.hpp:60-99): one sequential chain over the 64 dimension pairs.
  - A: the AMX tile kernel (qk_vnni_128x4, src/tron/kernels/amx_attn.cpp:233-290): 4 TDPBF16PS steps of 16 pairs. Its internal order is not public and not a simple fp32 chain (kernel test T5, exec/td-20261016/ktest/results.txt). The replay MODELS it as "step_exact": each step adds the exactly summed 32 products to the accumulator with one fp32 rounding. Every A number below is a model number.
- PV paths (how the softmax weights P multiply V): AVX PV (scaled_v_expr, kv_cache.hpp:2961-2976): P truncated to bf16, one VDPBF16PS chain over token pairs. AMX PV (weights_times_v_128x4, amx_attn.cpp:292-350): P rounded RNE to bf16, 2 TDPBF16PS steps of 16 token pairs (modelled like A).
- Page: 64 tokens of the KV cache. Dense page: a complete page written by an earlier prefill pass or an earlier decode step; the AMX arms run it through A + AMX PV. Partial page: the query's own page in prefill (prefill runs in 8 passes of 128 tokens) or the decode tail page; it goes through D or R + AVX PV. Block: 16 tokens of a VNNI page.
- Running softmax state per (query token, head): m* (running max score), s* (running sum of weights), v* (running weighted V). v* is STORED AS bf16 after every page (dmatensor<bf16>, h/tron/hardware/btensor.hpp:21, dmatensor.hpp:381): that rounding is part of every path.
- Model names of the replay (which path on which page kind): clean = D + AVX PV everywhere (also stands for baseoff and pocoff). newoff = R on VNNI blocks, D on the row-major tail block, AVX PV everywhere. base = A + AMX PV on dense pages, D + AVX PV on partial pages (also stands for poc). new = A + AMX PV on dense pages, R/D + AVX PV on partial pages. trunc = new with truncated P in the AMX PV. clean_rne = clean with P rounded RNE instead of truncated (a hypothetical arm that isolates the rounding mode).
- Mass-weighted bias of an output o against the exact output e (4 heads x 128 elements of one token and KV group): sum((o - e) * sign(e)) / sum(|e|). For a pure scale error o = (1 - x) e it equals -x. Relative L2 error: ||o - e|| / ||e||.
- Weight-mass ratio: sum(bf16(P)) / sum(P) over all attended tokens of one (query token, head), with P the fp32 weights exp(s - m) as the path computes them. The AVX path uses the truncated P in the numerator but the unrounded sum in the denominator, so a ratio below 1 is a systematic scale-down of the output.
- WO: the logged o_proj output ('WO layer 0 of token T', 2560 values), the first logged value downstream of attention. The attention output itself is not logged for this plugin.

## Data and method

- Logs: /var/tmp/jhan/td/<arm>.full on delphi-3bda, all 8 arms (finished 20:24-21:03 UTC). Extracts (layer 0 and 1 of WQ roped, WK roped, WV, WO, 275 MB per arm): /var/tmp/jhan/td/replay/<arm>-L01.txt, made by extract.sh.
- The logged values are bf16 printed with 8 significant digits. 126,553 of the 11,132,416 layer-0 values do not print decimal-exactly; every value is recovered as the nearest bf16 (RNE on the fp32 bits).
- Q, K and V of layer 0 are identical in all 8 arms (0 of 1279 x (4096 + 1024 + 1024) values differ in any arm against base). Layer 0 sits upstream of any attention, so the replay of every path model uses the same inputs. At layer 1 the arms' inputs already differ (new vs base: 319,003 Q values, 66,984 K values, 104,513 V values of 1279 tokens), so the layer-1 replay runs every model on the base arm's inputs.
- Replay: replay.py (numpy, 61 s per layer on 3bda). Sampled query tokens: all of 0..191 (prefill pass 1 = tokens 0..127 with no dense page anywhere, pass 2 = tokens 128..191 with pages 0 and 1 dense) plus the decode steps 1024, 1039, 1040, 1056, 1087, 1090, 1150, 1200, 1278 (the log holds tokens 0..1278). 201 tokens, 32 heads each.
- Arithmetic emulated exactly: fp32 RNE adds and multiplies, the VDPBF16PS lane order (acc + odd product) + even product (kernel test T0: 100 % of 2,000,000 cases), the dotter's lane layout and halving reduce (kernel test T3: 100 %), the reader's chain (kernel test T4: 100 %), tron's vector exp including its fused multiply-adds (h/tron/simd/fp32.hpp:925-937, fma emulated with an exact fallback), the sum order of expr.hpp:599, the bf16 store of v* after each page, the final v* / s* and bf16 store.
- Approximations (listed with their expected size): (1) the AMX kernels' internal order (see A above). (2) The page order: the replay folds pages in token order; tron splits the pages of one token into sections that are joined afterwards (self_attention.hpp:2095-2137), which changes the fp32 association at the ulp level and can flip a bf16 v* element. (3) The scalar exp of the running-max correction (std::exp) is taken as the fp64 exp rounded to fp32. (4) s* = s* * corr + sum is taken as one fused multiply-add (compiler contraction). (5) In prefill, every VNNI block of the query's own pass is taken as converted (R), the kill switch and new arms alike; in decode the block that this token completes is taken as still row-major (D). (6) A decode token at a page end (T % 64 == 63) completes its own page: for row-major K (base) that page is taken as dense, for VNNI K (new, poc) as partial. This asymmetry is measured, not assumed: the logged WO of base and poc differ exactly at tokens 1087, 1151 and 1215 and nowhere else.
- Exact reference: fp64 attention from the same bf16 Q, K, V, no rounding of P, no bf16 state.

## M1: raw scores, path against path (layer 0, 912,032 scores = 201 tokens x 32 heads x keys)

| pair | scores differing | median difference of the differing scores | max relative difference |
|---|---:|---:|---:|
| D vs R | 64.1 % | 1 fp32 ulp (1.05e-7 relative) | 2.1e-2 (262,144 ulps, a near-zero score) |
| A (model) vs R | 60.6 % | 1 ulp (1.03e-7) | 1.6e-2 |
| A (model) vs D | 48.8 % | 1 ulp (0.93e-7) | 8.3e-3 |
| A (model "seq", a sequential chain like R) vs R | 0 % | identical | identical |

- The kernel test measured the hardware A against R and D on random data: 49.5 % and 50.1 % of scores differ (kernel test T1, T2), with the same ulp-level size. The hardware A is therefore NOT the reader's chain (a sequential-chain A would equal R exactly, last row). The "step_exact" model gives the same magnitude as the hardware (60.6 % and 48.8 %).
- Decode tokens (1025-1279 keys) differ slightly more often than prefill tokens (68.8 % vs 61.8 % for D vs R) and the median grows to 2 ulps, because the scores of a long context are larger relative to their rounding.
- Within-pair order (the odd/even order inside one VDPBF16PS lane), measured on the hardware as odd product first (kernel test T0). Changing it to even-first changes 14,086 of 912,032 D scores (1.5 %) and 208,447 R scores (22.9 %); pair-sum-first changes 13,079 D scores (1.4 %) and 171,484 R scores (18.8 %). The dotter is less sensitive because its first add per lane starts from zero, where the order does not matter. The order assumption therefore matters for R and A, and the odd-first measurement is the one used.
- Layer 1 (base arm inputs): D vs R 58.5 %, A vs R 55.0 %, A vs D 43.0 %, median 1 ulp, max 5.2e-3 relative.

## M2: attention output, model against model (layer 0, 4096 bf16 elements per token)

| pair (what differs) | prefill 0-127 | prefill 128-191 | decode (9 steps) | tokens with any bf16 difference (of 201) |
|---|---:|---:|---:|---:|
| clean vs newoff (score order only: D vs R everywhere) | 0.06 % | 0.03 % | 0.03 % | 88 (49 of them exactly one element) |
| base vs new (D vs R on partial pages only) | 0.06 % | 0.01 % | 2.5 % (token 1087 alone: 22.5 %, the page-end asymmetry) | 72 (40 exactly one element) |
| newoff vs new (AVX PV truncated P vs AMX PV RNE P on dense pages) | 0 % | 19.5 % | 28.4 % | 73 (every sampled token >= 128) |
| clean vs base (same mechanism as the row above) | 0 % | 19.5 % | 29.9 % | 73 |
| new vs trunc (RNE P vs truncated P inside the AMX PV) | 0 % | 19.5 % | 28.4 % | 73 |
| newoff vs trunc (AVX chain vs AMX model, both truncated) | 0 % | 0.02 % | 0.02 % | 23 (14 exactly one element) |
| clean vs clean_rne (truncation vs RNE of P, AVX chain, all pages) | 34.3 % | 36.1 % | 40.3 % | 200 |

Numbers are the pooled fraction of bf16 output elements that differ. Per token the rounding pairs differ in 15-40 % of the elements (median 17.7 % in pass 2, 27.2 % in decode); the order-only pairs differ in 0-53 elements (median 0, max 1.29 %). The fp32 outputs of the order-only pairs differ by a median of 2e-7 relative, about one fp32 ulp of the output.

- Order-only differences are one-element events: in 49 of the 88 tokens where clean and newoff differ, exactly one of the 4096 bf16 elements differs, by one bf16 notch.
- The rounding-mode difference is a bulk effect: with P truncated on one side and RNE on the other, 20-30 % of the output elements land on a different bf16 value at every token that has a dense page, and the maximum element difference is 7-9 % of the output's rms.
- The AMX model choice does not change these numbers: with A and the AMX PV modelled as a sequential chain instead of step_exact, newoff vs new gives 19.5 % / 28.4 % (same), base vs new 0.06 % / 0.01 % / 0.00 % (same).
- Layer 1: clean vs newoff 0.09 % (119 tokens with a difference), newoff vs new 24.7 % / 28.8 %, clean vs clean_rne 41.1 %.

## M3: each path against the exact fp64 attention (layer 0)

fp32 output (v* / s* before the final bf16 store), per token 32 heads x 128 elements:

| model (P rounding on partial / dense pages) | mean mass-weighted bias | range over tokens | RMS relative L2 error | median relative L2 |
|---|---:|---:|---:|---:|
| clean (truncated / truncated) | -7.8e-4 (-0.078 %) | -1.76e-3 to 0 | 2.00e-3 | 1.95e-3 |
| newoff (truncated / truncated) | -7.8e-4 | same as clean | 2.00e-3 | 1.95e-3 |
| trunc (truncated / truncated) | -7.8e-4 | same | 2.00e-3 | 1.95e-3 |
| base (truncated / RNE) | -6.3e-4 (pass 2 and decode: -4.4e-4) | -1.63e-3 to +6.9e-5 | 1.91e-3 | 1.87e-3 |
| new (truncated / RNE) | -6.3e-4 (pass 2 and decode: -4.4e-4) | -1.63e-3 to 0 | 1.91e-3 | 1.87e-3 |
| clean_rne (RNE / RNE) | -1.6e-5 (-0.0016 %) | -3.6e-4 to +1.7e-4 | 1.60e-3 | 1.57e-3 |

- The truncated-P paths are biased low by 0.08 % of the output on average, up to 0.18 % at single tokens; the RNE-P path has no bias (its mean is 50 times smaller and changes sign from token to token). The AMX arms sit in between because their partial pages still truncate.
- The RMS relative error of the truncated-P paths is 1.25 times that of the RNE-P path (2.00e-3 vs 1.60e-3). The remaining 1.6e-3 is the bf16 storage of v* after every page plus the bf16 rounding of P itself; it is common to every path.
- bf16 output (what the next layer sees): clean bias -6.9e-4, relative L2 2.57e-3; clean_rne bias +7.6e-5, relative L2 2.28e-3; base/new bias -5.4e-4, 2.50e-3.
- Layer 1: clean bias -1.08e-3, base/new -8.7e-4, clean_rne -6e-6; relative L2 2.35e-3 / 2.25e-3 / 1.88e-3.

Weight mass kept by the bf16 rounding of P (sum(bf16(P)) / sum(P) - 1, per token and head, 201 tokens x 32 heads):

| token class | truncation: mean | truncation: min | truncation: max | RNE: mean | RNE: min | RNE: max |
|---|---:|---:|---:|---:|---:|---:|
| prefill 0-127 | -1.55e-3 | -3.44e-3 | 0 | +1.7e-6 | -1.5e-3 | +1.3e-3 |
| prefill 128-191 | -1.70e-3 | -3.31e-3 | -5.8e-8 | -8.0e-7 | -9.6e-4 | +1.2e-3 |
| decode | -2.03e-3 | -3.05e-3 | -1.3e-6 | +5.6e-6 | -6.6e-4 | +1.2e-3 |
| all 201 | -1.62e-3 (-0.16 %) | -3.44e-3 | 0 | +1.1e-6 | -1.5e-3 | +1.3e-3 |

- Truncation loses 0.16 % of the softmax mass on average; RNE loses nothing on average (+1e-6). For a weight whose mantissa bits are uniformly placed, truncation to bf16 loses 2^-8 x ln2 = 0.28 % on average; the measured loss is smaller because the largest weight of every page is exactly 1 (exp(0)), which truncation leaves intact, and that weight carries a large share of the mass.
- The output bias is about half the mass loss (-0.078 % vs -0.16 %) because the weights that dominate each output element are the large ones, and the largest weight of every page is exactly 1 (exp(0)), which truncation leaves intact. The kernel test on random data shows the same ratio (T7a: mass -1.46e-3, output bias -7.6e-4).

Bias against the number of attended tokens (one token each, mean over its 32 heads):

| attended tokens | token | truncation mass ratio - 1 | RNE mass ratio - 1 | clean output bias | clean_rne output bias | base output bias | new output bias |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 16 | 15 | -1.50e-3 | +3.0e-5 | -6.8e-4 | -1.5e-5 | -6.8e-4 | -6.8e-4 |
| 64 | 63 | -1.80e-3 | -5.1e-6 | -9.8e-4 | -2.4e-6 | -9.8e-4 | -9.8e-4 |
| 128 | 127 | -1.86e-3 | -8.6e-6 | -8.5e-4 | +3.5e-5 | -8.5e-4 | -8.5e-4 |
| 1088 | 1087 | -2.22e-3 | +3.4e-5 | -1.49e-3 | +7.0e-5 | +6.9e-5 | -5.4e-4 |

- With one attended token every path is exact (P = 1 exactly). From 16 tokens on the truncation loss is already at its full size (-0.15 %) and grows slowly with the context (-0.22 % at 1088 tokens) as more small weights share the mass. The RNE loss stays within +-3e-5.
- At token 1087 the base arm's own page is dense (every page through the AMX PV), so its bias vanishes (+6.9e-5); the new arm's own page is still partial and keeps a third of the truncation bias (-5.4e-4).

## M4: validation against the binary

- (a) Token 0: every model gives the identical output, equal to V_0 in bf16 (P = 1 on one token). Verified.
- (b) Logged WO records (layer 0, all 1279 tokens, every arm, from arms_wo.py; Q, K and V of layer 0 are identical in all 8 arms):

| arm pair (what differs) | tokens where the logged WO differs (pass 1 / rest of prompt / decode) | first differing token | median relative L2 of the WO difference (when it differs) | max |
|---|---:|---:|---:|---:|
| clean vs baseoff (same arithmetic) | 0 of 1279 | none | identical | identical |
| baseoff vs pocoff (same arithmetic) | 0 of 1279 | none | identical | identical |
| base vs poc (same arithmetic except the page-end rule) | 3 of 1279 (0 / 0 / 3: tokens 1087, 1151, 1215) | 1087 | 1.7e-3 | 2.6e-3 |
| clean vs newoff (score order D vs R everywhere) | 689 of 1279 (37 / 513 / 139) | 26 | 9.2e-5 | 1.8e-3 |
| base vs new (D vs R on partial pages) | 352 of 1279 (37 / 301 / 14) | 26 | 1.1e-4 | 2.6e-3 (token 1087) |
| newoff vs trunc (AVX chain vs AMX order, both truncated P) | 484 of 1279 (0 / 360 / 124) | 129 | 7.3e-5 | 1.2e-3 |
| newoff vs new (truncated vs RNE P on dense pages) | 1151 of 1279 (0 / 896 / 255) | 128 | 2.2e-3 | 5.0e-3 |
| new vs trunc (RNE vs truncated P inside the AMX PV) | 1151 of 1279 (0 / 896 / 255) | 128 | 2.2e-3 | 5.0e-3 |
| clean vs base, baseoff vs base (same mechanism as newoff vs new) | 1151 of 1279 (0 / 896 / 255) | 128 | 2.2e-3 | 5.0e-3 |
| clean vs new (both mechanisms) | 1188 of 1279 (37 / 896 / 255) | 26 | 2.1e-3 | 5.0e-3 |

  Two clear classes: the order-only pairs differ at 27-54 % of the tokens by a median of 7e-5 to 1.1e-4 relative L2, the rounding-mode pairs differ at every token with a dense page (100 % from token 128 on) by a median of 2.2e-3, 20 to 30 times more. The three same-arithmetic pairs are identical record for record (except the page-end rule of base vs poc).
  Set overlap on the 201 sampled tokens (logged WO differs / replay predicts a bf16 output difference / both): newoff vs new 73 / 73 / 73, clean vs base 73 / 73 / 73, new vs trunc 73 / 73 / 73; clean vs newoff 67 / 88 / 55; base vs new 55 / 72 / 43; clean vs new 110 / 123 / 105; newoff vs trunc 25 / 23 / 11 (the AMX-order pair, where the replay's A model is weakest). The first differing token is the same in the log and in the replay for every pair (26 for the order pairs, 128 for the rounding pairs, except newoff vs trunc: 129 logged, 128 predicted).
  For base vs new, of the 55 sampled tokens where the logged WO differs, the replay predicts 43; it predicts 29 more that the log does not show (26 of them single-element flips, which the o_proj's own bf16 rounding can hide) and misses 12 (unmodelled ulp-level effects: the section join order, the AMX internal order, the scalar exp). The replay's predicted WO difference (output difference pushed through the dequantized o_proj) for newoff vs new is 1.0e-3 to 2.4e-3 relative L2 at the 7 checked tokens against 1.7e-3 to 3.9e-3 logged; for base vs new at tokens 100 and 127 it is 10 times smaller than logged (4.9e-6 vs 4.8e-5, 2.1e-5 vs 2.9e-4): the replay flips smaller elements than the binary did at those two tokens.
  The size ratio between the two mechanisms in the binary is the same as in the replay: the logged WO difference of newoff vs new (2.2e-3) is 20 times that of base vs new (1.1e-4).
- (c) Full WO check (wo_check.py): the replay's bf16 attention output (base model, base arm) multiplied by the dequantized o_proj weight (GPTQ int4, group 64, symmetric, from the checkpoint the run loaded) against the logged WO, 14 tokens:

| token | replay output through Wo vs logged WO (relative L2) | exact fp64 output through Wo | wrong head order (control) |
|---:|---:|---:|---:|
| 0 | 1.61e-3 | 1.61e-3 | 1.61e-3 (at token 0 every head of a group has the same output) |
| 1, 2, 5, 17, 64 | 1.60e-3 to 2.41e-3 | 2.19e-3 to 2.89e-3 | 0.53 to 0.85 |
| 100, 127, 128, 150, 191 | 1.37e-3 to 2.36e-3 | 1.65e-3 to 2.98e-3 | 0.59 to 0.71 |
| 1024, 1090, 1278 | 1.97e-3 to 2.22e-3 | 2.24e-3 to 2.70e-3 | 0.54 to 0.72 |

  At token 0 the attention output is V_0 exactly in every path and in the exact reference, so its 1.61e-3 is the floor of the o_proj numerics themselves (the FPGA's int4 x bf16 matmul and the bf16 store of WO). The replay matches the logged WO at that floor at every token (1.4e-3 to 2.4e-3), closer than the exact fp64 output (which lacks the bf16 roundings of the real path). A deliberately wrong head order is 300 times farther. An ulp-level match is not possible through the FPGA matmul; this check validates the structure (head mapping, page kinds, path assignment) and the size of every rounding the replay models.

## What this means for issue #4444

- Two mechanisms, two sizes. The score order (D vs R, and the AMX tile order) moves scores by one fp32 ulp and the output by one bf16 notch in one or two elements at a third of the tokens. The softmax-weight rounding (truncation in the AVX PV, RNE in the AMX PV) moves 20-30 % of the output elements by one bf16 notch at every token with a dense page, and it carries a systematic -0.08 % bias on the truncating side.
- Which path is closer to exact: the RNE paths. Truncation costs a -0.16 % weight loss and a 1.25 times larger RMS error than RNE on the same data; the AMX arms are unbiased on their dense pages and keep the truncation bias only on their partial pages.
- The kill switch (newoff) is not the row-major binary (clean): they differ by the score order (one-element flips at 88 of 201 tokens), and newoff differs from new by the rounding mechanism at every token from 128 on.
- A fix that removes the rounding-mode mismatch (the trunc arm, or RNE on the AVX side) leaves only the order mechanism: newoff vs trunc differs in 0.02 % of the output elements (23 of 201 tokens, 14 of them one element), which is the floor set by the add order alone.

## Files

- /home/jhan/workspace/intel-AMX/exec/td-20261016/replay/replay.py: the replay (parameters at the top; --layer, --tokens, --check-arms, --quick).
- extract.sh: the ssh/grep extraction. wo_check.py: the o_proj check. arms_wo.py: the logged WO comparison across arms and the set overlap with the replay. render_md.py: the tables.
- results.json (= results-L0.json plus the arms_wo layer-0 pair table under M4), results-L1.json, wo_check-base-L0.json, wo_check-newoff-L0.json, wo_check-trunc-L0.json, arms_wo-L0.json, tables-L0.md, tables-L1.md: all numbers, per token.
- On delphi-3bda, /var/tmp/jhan/td/replay/: <arm>-L01.txt extracts (275 MB each), the logs full-L0.log and full-L1.log.
