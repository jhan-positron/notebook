# Facts: the bf16 rounding map of the GDN host code, and which roundings our kernels depend on

Written 2026-11-23 by a fact-reading agent. Read-only work: no build, no test run, no ssh, no change to any repository or to GitHub.

## Short version

- PR #5571 removes 14 of the 22 bf16 rounding calls of the GDN host code, and issue #5433 removes six of them in every outcome, one of which is the rounding of the normalized key and query.
- Our AMX block kernel needs exactly those two values in bf16 form: it keeps the upper 16 bits of each FP32 value without a check, so it would cut each key and query value toward zero by up to 0.78 % (2^-7) of the value.
- Our chain kernel stays bit-identical to the token kernel under the six removals, and needs one hand edit (its own copy of the value rounding) if all 14 go.

## Words used here

- **GDN**: GatedDeltaNet, the recurrent layer of the model Qwen3.5 4B.
- **tron**: the C++ inference program (repository positron-ai/tron).
- **FP32**: 32-bit floating point. **bf16**: bfloat16, a 16-bit floating-point format with 8 significant bits. A bf16 value has the same bits as the upper half of an FP32 value.
- **bf16-representable**: an FP32 value whose low 16 bits are zero.
- **Rounding call**: a call of `round_to<bf16>` (one value) or `round_chunk_to<bf16>` (16 values). Both round to the nearest bf16 value, ties to even.
- **Truncation**: keeping the upper 16 bits of an FP32 value and dropping the low 16 bits. The result is never larger in magnitude than the input.
- **One increment**: the distance between two neighbouring bf16 values. For a value in [2^e, 2^(e+1)) it is 2^(e-7).
- **Token kernel**: `gdn_recurrence`, which advances the layer by one token.
- **Chain kernel** ("Part 0"): our `gdn_recurrence_chain`, an AVX-512 kernel that advances up to 32 tokens and must give the bits of the token kernel.
- **Block kernel** ("Part A"): our AMX kernel (`amx_gdn_k128v128::pack_key_head` and `advance_value_head`), which advances a block of 32 tokens. AMX is the Intel tile-matrix instruction set. AVX-512 is the Intel 512-bit vector instruction set.
- **Tile product**: one execution of TDPBF16PS, the AMX instruction that multiplies two tiles of bf16 values and adds the products into FP32 values.
- **K, Q**: the normalized key and the normalized query of a token (128 values each). **S0**: the FP32 recurrent matrix at the start of a block. **delta**: the correction of one token, computed inside the kernels.
- **`normalize_gdn`**: the function that divides a key or a query by its length. **`gdn_beta`**: the sigmoid gate. **`gdn_decay`**: our helper that computes the decay of one token.
- **Executor**: `gdn_rolling_executor`. Its `step()` advances one token with the token kernel. Its `advance()` advances a run of tokens in windows of 32 tokens with the chain kernel or the block kernel.
- **SiLU**: the activation function x * sigmoid(x), named `swish` in the code.
- **Relative L2 error**: the length of the difference of two vectors divided by the length of the reference vector.
- **The six**: the six normalization roundings that issue #5433 removes in every outcome. **The fourteen**: the 14 calls that PR #5571 removes.
- **File letters**: G = `h/tron/kernels/gated_delta_net.hpp`, E = `h/tron/models/gdn_rolling_executor.hpp`, P = `h/tron/models/gdn_prepared_operation.hpp`, A = `src/tron/kernels/amx_gdn.cpp`, I = `h/tron/kernels/amx_gdn_iface.hpp`, TG = `t/t_gated_delta_net.cpp`, TA = `t/t_amx_gdn_numerics.cpp`.
- **Commit labels**: `3221` = 127a662083 (head of PR #3221), `5571` = 69cc70fae0 (head of draft PR #5571), `main` = f454423b09, `base` = 72e1191804 (head of PR #3696, the base of our commits), `ours` = 775bba7661 (our Part 0 and Part A commit). The seven files G, E, P, A, I, TG and TA are the same at 775bba7661 and at our tip 882e5322f1 [R1].

## 1. The 22 rounding calls

The count is 22 at the head of PR #3221: 15 in G, 5 in E and 2 in P [R2]. This equals the count of issue #5433. There is no difference to report.

The issue groups them as 4 in the convolution, 11 in the recurrence, 2 at load and 5 in the executor [R3]. These are rows 1-4, rows 5-15, rows 21-22 and rows 16-20 of the table.

| # | file:line at `3221` | function | value that is rounded | PR #5571 removes it | one of the six | line at `base` | line at `main` | line at `ours` |
|---|---|---|---|---|---|---|---|---|
| 1 | G:120 | `prepare_gdn_conv1d_weights` | convolution weights, when an operation is prepared | no | no | G:91 | G:105 | G:93 |
| 2 | G:159 | `gdn_conv1d_silu` | current input of the convolution | no | no | G:138 | G:133 | G:140 |
| 3 | G:168 | `gdn_conv1d_silu` | sum of the convolution | yes | no | G:146 | G:142 | G:148 |
| 4 | G:172 | `gdn_conv1d_silu` | SiLU result (the convolved query, key and value) | yes | no | G:150 | G:146 | G:152 |
| 5 | G:204 | `normalize_gdn` | input (query or key) | yes | no | G:182 | G:178 | G:184 |
| 6 | G:206 | `normalize_gdn` | each square | yes | yes | G:184 | G:180 | G:186 |
| 7 | G:209 | `normalize_gdn` | sum of the squares | yes | yes | G:187 | G:183 | G:189 |
| 8 | G:210 | `normalize_gdn` | the epsilon operand | yes | yes | G:188 | G:184 | G:190 |
| 9 | G:211 | `normalize_gdn` | sum plus epsilon | yes | yes | G:189 | G:185 | G:191 |
| 10 | G:212 | `normalize_gdn` | reciprocal square root | yes | yes | G:190 | G:186 | G:192 |
| 11 | G:214 | `normalize_gdn` | normalized product (the K or Q that the recurrence reads) | yes | yes | G:192 | G:188 | G:194 |
| 12 | G:220 (inner call) | `gdn_beta` | update input, before the sigmoid | no | no | G:198 | G:194 | G:200 |
| 13 | G:220 (outer call) | `gdn_beta` | result of the sigmoid (beta) | yes | no | G:198 | G:194 | G:200 |
| 14 | G:284 | `gdn_recurrence` | decay input | no | no | G:262 | G:257 | G:207 (moved into `gdn_decay`) |
| 15 | G:302 | `gdn_recurrence` | value input | yes | no | G:280 | G:275 | G:287, and a second copy at G:418 |
| 16 | E:469 | `postprocess` | output of the recurrence | yes | no | E:452 | E:294 | E:808 |
| 17 | E:479 | `postprocess` | RMS-normalized value | yes | no | E:461 | E:304 | E:818 |
| 18 | E:480 | `postprocess` | value times the output normalization weight | yes | no | E:462 | E:305 | E:819 |
| 19 | E:482 | `postprocess` | output gate | no | no | E:464 | E:307 | E:821 |
| 20 | E:483 | `postprocess` | final output | no | no | E:465 | E:308 | E:822 |
| 21 | P:105 | `reject_non_finite` | a convolution weight, inside an assertion | no | no | P:105 | P:105 | P:105 |
| 22 | P:116 | `prepare_output_norm_weight` | output normalization weight | no | no | P:116 | P:116 | P:116 |

Facts about the table:

- PR #5571 removes rows 3, 4, 5-11, 13, 15, 16, 17 and 18. That is 14 calls [R4]. Eight calls remain at `5571`: G:122, G:161, G:220, G:282, E:475, E:476, P:105 and P:116 [R2].
- The issue does not give line numbers for the six. It says "Six of the seven (after each normalization step)" [R3]. I read the six as rows 6-11 and the seventh as row 5 (the input). Two sources support this reading:
  - The Note at `3221` lists one input rounding and then six roundings "after each square, the reduction, the epsilon operand and its addition, the reciprocal square root, and the normalized multiply" [R5].
  - The Python reference at the head of PR #5124 (d9df90c99d, open draft) converts the bf16 query and key to FP32 first and then normalizes. It does not convert the result back [R6]. The reference on `main` normalizes in bf16 and converts afterwards [R6].
- So row 11, the rounding of the normalized product, goes in every outcome that the issue lists. Cases 1, 2 and 3 of the decision rule all remove at least the six [R7].
- A build with only the six removed is named in the issue [R7]. No branch with that build was found by a name search of the remote branches. Not verified beyond the name search. Command: `git -C /home/jhan/workspace/tron branch -r --list 'origin/*gdn*' 'origin/*/*gdn*'`.
- The last comment of the issue is dated 2026-11-22 and says "Nothing is measured yet." No later comment existed when I read the issue on 2026-11-23 [R7].
- Our `base` holds 25 calls, not 22. The three extra calls round the convolution history entries (G:133, G:135, G:137 at `base`). The issue says PR #5462 removed them on main [R2] [R3].
- `ours` holds 26 calls: the 25 of `base` plus the chain kernel's copy of row 15 at G:418 [R2].

## 2. Our chain kernel (Part 0)

`gdn_prepare_recurrence_token` (G:381-425 at `ours`) fills one token of a window. It is the only chain function that rounds. `gdn_recurrence_slice` (G:447-521) and the other chain functions hold no rounding call [R2].

| place at `ours` | code | row of section 1 | same function as the token kernel, or own copy | effect of the removals |
|---|---|---|---|---|
| G:400-403 | `gated_delta_net_detail::normalize_gdn<key_head_dim>(...)` for query and key | 5-11 | SAME function. The token kernel calls it at G:259-262. | A change inside `normalize_gdn` reaches the chain kernel without an edit. |
| G:412-413 | `normalized_query.chunk(chunk) * query_scale` | none | no rounding | none |
| G:416-418 | `round_chunk_to<bf16>(value.chunk(chunk)).data` | 15 | OWN COPY. The token kernel has its copy at G:286-287. | If row 15 goes, this line must be removed by hand. |
| G:420-421 | `gated_delta_net_detail::gdn_decay(decay_input[value_head], A_exp[value_head], dt_bias[value_head])` | 14 | SAME function. `gdn_decay` (G:203-208) is our helper, and the token kernel calls it at G:268-269. | Row 14 stays in every outcome. Upstream has the expression inline (G:281-284 at `3221`), so a port must keep our helper. |
| G:422-423 | `gated_delta_net_detail::gdn_beta(update_input[value_head])` | 12, 13 | SAME function. The token kernel calls it at G:271. | A change inside `gdn_beta` reaches the chain kernel without an edit. |

The executor code around the chain kernel:

- The window path convolves with the same `gdn_conv1d_silu` call as `step()` [R8]. Rows 2-4 are therefore shared.
- The window path postprocesses with the same `postprocess` function as `step()` [R8]. Rows 16-20 are therefore shared.
- Our commit rewrote the first loop of `postprocess` (E:805-809 at `ours`), which holds row 16. PR #5571 deletes the same loop [R9]. The two changes edit the same lines, so that function needs a merge by hand. The result of a textual merge is Not verified. Command: cherry-pick 775bba7661 onto 69cc70fae0 in a scratch worktree. (git 2.34.1 on this host has no `merge-file --object-id`, and this task allowed no temporary files.)
- Our Notes state the old rounding in words. The chain Note says the window holds "the value rounded to BF16" and that preparing a token "computes these exactly as gdn_recurrence does" [R10]. The executor Note says the recurrence "reads the value from the window, rounded to BF16" [R10].

Tests that compare the chain kernel with the token kernel bit for bit, all in TG at `ours`:

| TEST_CASE | lines | what is compared |
|---|---|---|
| "GatedDeltaNet advance gives the bytes of step at the Qwen matrix shape" | TG:2840-2849 | checkpoint bytes and output rows of `advance()` with the block kernel off against `step()`, for 4 start positions times 8 run lengths |
| "GatedDeltaNet advance gives the bytes of step for narrower value heads" | TG:2851-2861 | the same, for two narrower shapes (two SECTIONs) |
| "GatedDeltaNet advance gives a refused block to the chain kernel" | TG:2955-2991 | the matrix bytes of a value head that the block kernel refuses against `step()` |

- The helper `check_advance_matches_step` (TG:2803-2812) does the comparison with `gdn_block_kernel::off` [R11].
- No test calls `gdn_recurrence_chain` and `gdn_recurrence` side by side. The comparison goes through the executor: `step()` in place runs `gdn_recurrence`, and `advance()` runs `gdn_recurrence_chain` [R8] [R11].
- Reasoning for the six removals only: both kernels call the same `normalize_gdn`, and row 15 stays in both copies. The three cases keep passing. Not verified by a run.
- Reasoning for the fourteen removals with G:418 left in place: `step()` would read an unrounded value (rows 4 and 15 gone), and `advance()` would round it. The bytes would differ, and the three cases would fail. Not verified by a run.

## 3. Our AMX block kernel (Part A)

Production takes the block kernel for every full window where AMX is available [R12].

| operand | (a) where it is produced, and which rounding made it | (b) how the kernel reads it | (c) what happens if it is not bf16-representable | requires bf16 today |
|---|---|---|---|---|
| K, normalized key | `gdn_prepare_recurrence_token` stores it in `window.normalized_key` (G:402-407). Row 11 made it bf16-representable. The executor passes the address at E:704-705. | Packed three times by keeping the upper 16 bits. A:258-259: `bf16_bits(_mm512_load_ps(key + first))`. A:278: `_mm512_cvtepi32_epi16(_mm512_srli_epi32(rows[i], BF16_SHIFT_16))` for K transposed. A:292-302 builds the pair-interleaved K from that. | The low 16 bits are dropped. This is truncation toward zero. No assert, no check and no message [R13]. The kernel then computes K S0, K K^T, Q K^T and K^T (w . delta) from the truncated key. | **YES** |
| Q, normalized query (without the query scale) | Stored in `window.normalized_query` (G:400-409). Row 11 made it bf16-representable. Passed at E:706-707. | A:260-262: `bf16_bits(_mm512_load_ps(query + first))`. | The same truncation, with no check [R13]. The kernel computes Q S0 and Q K^T from the truncated query. | **YES** |
| value | Stored in `window.value` (G:416-418). The chain's copy of row 15 rounds it. Row 4 already made the input bf16. | FP32 in AVX-512. A:472: `_mm512_load_ps(token_value + group * LANES_16)`. | Nothing is dropped. The full FP32 value enters the subtraction. | no |
| decay | `gdn_decay` (G:420-421). Row 14 rounds the decay input. The result of `std::exp` is FP32 and is not rounded today. | FP32 scalar. A:412: `const float decay = block.decay[token * block.scalar_stride + value_head];` | Not applicable. It is not bf16 today. | no |
| beta | `gdn_beta` (G:422-423). Rows 12 and 13. bf16-representable today. | FP32 scalar. A:447-448: `_mm512_set1_ps(block.beta[token * block.scalar_stride + value_head])`. | Nothing is dropped. | no |
| S0, recurrent matrix | The working copy of the executor (E:719-720). FP32, never rounded. | Split into three bf16 pieces that add up to the value. A:357-365 with `split` (A:224-231) and `pair_row` (A:237-241). The last pass reads it as FP32 (A:545-546). | The split is exact for a magnitude of 2^-103 or larger [R14]. A test checks this [R14]. | no |
| delta, corrections | Computed inside the kernel in FP32 (A:471-475). | FP32 in AVX-512 in stage 3 (A:461-464). Split into three bf16 pieces in stage 4 (A:498-506). | The same exact split as S0. | no |

Plain statement: **only the normalized key and the normalized query require a bf16-representable value today.** There are three pack sites: A:258-259 (K), A:260-262 (Q) and A:271-278 (K transposed).

More facts:

- The helper is `bf16_bits` (A:181-186). Its comment states the assumption: "The upper 16 bits of each FP32 lane: the bf16 bit patterns of 16 values that are representable in bf16." [R13]
- The interface states the assumption twice: "K and Q hold bf16 values already" (I:47) and "KEY_DIM_128 values that are representable in bf16" (I:129-130) [R13].
- The only runtime checks of the kernel are the refusal checks: a correction of 2^100 or more, or an output that is not finite (A:484-490). Truncation makes neither. The other asserts in A are `static_assert` lines on constants [R13].
- The chain kernel reads the key and the scaled query as full FP32 values (G:457, G:488-490 at `ours`). The chain kernel runs for partial windows, for refused blocks, and when the switch `TRON_AMX_GDN_DISABLE=1` is set [R12]. After the removal the two kernels would compute from different keys and queries.
- Tile products per block today, counted from the loops: 32 per key head in stage 2 (A:306-322), 384 per value head in stage 1 (A:354-392) and 192 per value head in stage 4 (A:495-537). With two value heads per key head this is 1,184 tile products per key head and block. The two-value-head grouping comes from a test comment (TA:35-36). Not verified against the model registry.
- Derivation, not a measurement: an FP32 value has 24 significant bits and a bf16 value has 8. An exact K or Q therefore needs three bf16 pieces, as S0 does. With N pieces for K and for Q, stage 1 and stage 4 need N times their tile products, and stage 2 needs N^2 times. That is 2,432 for N = 2 and 3,744 for N = 3, against 1,184 today.

## 4. Tests that encode the assumption

**TA (`t/t_amx_gdn_numerics.cpp`)**

- The tests do not call `normalize_gdn`. The string does not occur in the file [R15].
- `fill_block` (TA:73-105) draws random FP32 keys and queries, normalizes them in float64, and rounds them by hand: `round_to_bf16(static_cast<float>(key[i] / std::sqrt(key_square)))` (TA:89-92). `round_to_bf16` is `static_cast<float>(tron::bf16(x))` (TA:58-60).
- The values and beta are also rounded by hand (TA:96, TA:102). The decay is not rounded (TA:99-101).
- The other cases set keys and queries to 0, to 1.0 or to `round_to_bf16(1e30f)` (TA:380-382, TA:484). All are bf16-representable.
- The reference is the chain kernel on the same window (TA:229), plus a float64 model (TA:231).
- Answer: if `normalize_gdn` returned unrounded FP32 values, every case of this file would still pass, since no case calls `normalize_gdn`. Not verified by a run. So this file would not detect the truncation in production.

**TG, the chain and block cases (`t/t_gated_delta_net.cpp`, TG:2587-3009 at `ours`)**

- These cases feed raw FP32 rows to the executor. `chain_case_rows::fill` (TG:2619-2636) uses `recurrence_test_value`, an integer from -23 to 23 times a scale (TG:57-60). The values are not bf16.
- The rows pass through the production path: convolution, then `normalize_gdn`, then the kernel [R8].
- "GatedDeltaNet advance with the block kernel stays close to step" (TG:2863-2910) is the only case that sends keys from `normalize_gdn` into the block kernel and bounds the result. Its bounds are in section 5.
  - With unrounded keys the block kernel would truncate K and Q. The float64 model of section 5 gives a matrix error near 3e-3 relative L2. The bound of this case is 1e-5. So I expect the case to fail on a machine with AMX. Not verified by a run.
  - On a machine without AMX the case takes the chain kernel and passes. The test comment says so (TG:2865-2868).
  - Not verified: whether the CI host that runs `t_gated_delta_net` has AMX. Check: the tally `amx_blocks` of TG:2912-2953 in a CI log, or `grep amx_tile /proc/cpuinfo` on the CI host.
- "GatedDeltaNet advance gives full windows to the block kernel and counts them" (TG:2912-2953) checks counts. It expects no refused block (TG:2948). Truncation makes no value non-finite, so I expect it to pass. Not verified by a run.
- The three bit-for-bit cases are covered in section 2.

## 5. Size of the rounding as an error

**One rounding**

- The rule: bf16 keeps FP32 bits 31..16 and drops bits 15..0. Finite normal values round to nearest, ties to even. Zero and subnormal inputs become a zero of their sign [R16].
- PR #5571 states the size: "rounding moves a normal value by at most 2^-8 of itself" [R4].
- Derivation: for a value in [2^e, 2^(e+1)) one increment is 2^(e-7). Rounding to nearest moves the value by at most half an increment, 2^(e-8). That is at most 2^-8 of the value (0.39 %). The error has either sign.

**Truncation (derivation, the code does not state it)**

- Keeping the upper 16 bits moves the value by less than one increment, 2^(e-7). That is less than 2^-7 of the value (0.78 %). The error always points toward zero.

**Computed check of both, over all 8,388,608 FP32 values in [1, 2)** [R17]

| | largest relative error | mean relative error | sign |
|---|---|---|---|
| rounding to nearest | 3.891e-3 (bound 2^-8 = 3.906e-3) | 1.354e-3 | either sign, signed mean 1.3e-6 |
| truncation | 7.752e-3 (bound 2^-7 = 7.813e-3) | 2.705e-3 | always toward zero |

**Computed for 20,000 random unit keys of 128 values, normalized in FP32 without rounding** [R17]

| key given to the kernel | relative L2 error of the key, mean | length of the key against the exact key, mean |
|---|---|---|
| truncated | 3.30e-3 | 0.99719 (0.28 % shorter) |
| rounded to nearest | 1.65e-3 | 0.999998 |

**A float64 model of the recurrence** [R18]

This is a model of the formula in float64. It is not a run of the kernel. The reference uses unrounded FP32 keys and queries. The other side uses the same keys and queries after truncation, or after rounding to nearest. Each case runs 4 blocks of 32 tokens with 2 value heads, with the input families of TA:191-195.

| family | K and Q given to the model | matrix, relative L2 error | recurrence output, relative L2 error | share of bf16 output words that differ |
|---|---|---|---|---|
| decay 0.90-1.00 | truncated | 3.33e-3 | 6.00e-3 | 81.6 % |
| decay 0.90-1.00 | rounded | 1.67e-3 | 2.31e-3 | 49.7 % |
| decay 0.999-1.00 | truncated | 3.73e-3 | 4.90e-3 | 71.3 % |
| decay 0.999-1.00 | rounded | 1.68e-3 | 2.13e-3 | 48.1 % |
| decay 0.50-1.00 | truncated | 3.11e-3 | 6.02e-3 | 81.5 % |
| decay 0.50-1.00 | rounded | 1.62e-3 | 2.37e-3 | 50.6 % |
| decay 0.01-0.30 | truncated | 2.70e-3 | 5.86e-3 | 81.5 % |
| decay 0.01-0.30 | rounded | 1.53e-3 | 2.62e-3 | 53.4 % |

**The error band that our code states today**

- Note [AMX GatedDeltaNet block kernel]: "A small share of the bf16-rounded outputs differ. An output above 1 % of the typical output size differs by one increment in the measurements. An output nearer to zero can differ by more. The matrices differ by about 1e-7 in relative L2 norm" (I:58-62).
- TA, measured values in a comment: "0.006 to 0.034 % of the words differ, an output above 1 % of the typical size differs by one bf16 increment, and the matrices differ by 5e-8 to 4e-7 in relative L2 norm" (TA:260-262).
- TA, the checks (TA:263-284):
  - at most 0.2 % of the bf16 output words differ (`differing_words <= 0.002 * compared_words`);
  - an output above 1 % of the typical size differs by at most 2 increments;
  - the matrices differ by at most 2e-6 in relative L2 norm;
  - against float64, the output error is at most 2 times that of the chain kernel, and the matrix error at most 4 times.
- TG, the executor case (TG:2895, TG:2908-2909): the matrices differ by at most 1e-5 in relative L2 norm, at most 2 % of the output values differ, and the largest difference is at most 2 % of the largest output.

**Comparison**

- Truncated K and Q: the model gives a matrix error of 2.7e-3 to 3.7e-3. That is about 1,400 to 1,900 times the 2e-6 bound of TA, and about 270 to 370 times the 1e-5 bound of TG (est., from the model).
- K and Q rounded to nearest at the pack step: the model gives 1.5e-3 to 1.7e-3. That is still about 770 to 840 times the 2e-6 bound (est., from the model).
- So one bf16 piece for K and Q cannot keep the block kernel within today's band of a chain kernel that reads FP32 keys, whichever way the piece is made (est., from the model).
- For scale: PR #5571 sets its own test tolerances against the PyTorch tables at 2 % and 2.5 % for the normalization and at 4.3 % for the executor row [R4]. Those compare tron with PyTorch. Our band compares the block kernel with the chain kernel. They are different comparisons.
- Insufficient data: the error of the real kernel on real model keys. A run of the `[chain]` cases of `t_gated_delta_net` and of `t_amx_gdn_numerics` on an AMX machine, with row 11 removed from `normalize_gdn`, would give it.

## What breaks in our code when PR #5571 or the six normalization removals land

Ordered by severity. Items 1-3 hold for the six alone and for all fourteen. Items 4-5 hold only if all fourteen go.

1. **The block kernel computes from truncated keys and queries, with no check.** Row 11 is one of the six. After it goes, `normalize_gdn` returns FP32 values with nonzero low bits. The three pack sites (A:258-259, A:260-262, A:271-278) drop those bits. Each value moves toward zero by up to 0.78 % (2^-7), and a key gets 0.28 % shorter on average (computed, section 5). This is the production path [R12].
2. **The block kernel and the chain kernel stop agreeing closely.** The model gives a matrix difference near 3e-3 relative L2, against about 1e-7 stated today (est., from the model). The same tokens would then give visibly different results in full windows and in partial windows, and with the switch `TRON_AMX_GDN_DISABLE` on and off. The Notes at I:47, I:55-62 and I:129-130 and the comment at A:181-182 would be false.
3. **The tests would mostly not show it.** TA makes its own bf16 keys and would stay green. Only "GatedDeltaNet advance with the block kernel stays close to step" (TG:2863) would fail, and only on a machine with AMX. Not verified by a run.
4. **Fourteen only: the chain kernel loses its bit-identity until G:418 is edited.** The chain's own copy of the value rounding must be removed by hand. Until then the three bit-for-bit cases of section 2 would fail. Not verified by a run.
5. **Fourteen only: `postprocess` needs a merge by hand.** Our rewrite of its first loop (E:805-809) meets the deletion of the same loop in PR #5571. `step()` and `advance()` share the function, so the two paths stay equal to each other either way. A wrong merge would keep a rounding that upstream removed.
6. **Comments and Notes.** G:340-342 and E:154-160 at `ours` describe the value as "rounded to BF16". TA:70-72 describes its inputs as "rounded to bf16". They need new words after either change.
7. **Not affected.** `gdn_decay` keeps its rounding (row 14 stays). `gdn_beta` is shared, and the block kernel reads beta as FP32. The block kernel reads the value, the decay, S0 and delta as FP32 or through the exact three-piece split.
8. **Separate, but met in the same port.** Our `base` still rounds the three convolution history entries, which main no longer does (PR #5462). Our commits do not depend on those three calls. Not verified beyond reading: no chain or block code reads the history.

## Gaps

- No build and no test was run. Every "would pass" and "would fail" above is reasoning from the code.
- The mapping of "the six" to rows 6-11 is my reading of the issue text, supported by [R5] and [R6]. The GDN owner has not published the six-out build under a branch name that the search found.
- The textual result of putting our commits on 69cc70fae0 is Not verified (see section 2).
- The model of section 5 uses Gaussian random keys. Keys of the real model may be distributed differently.

## References

- [R1] `git -C /home/jhan/workspace/tron diff --stat 775bba7661 882e5322f1` lists only `amx_attn_iface.hpp`, `self_attention.hpp`, `v_vnni.hpp`, `amx_attn.cpp`, `t/CMakeLists.txt`, `t_amx_dispatch_dtype.cpp` and `t_amx_numerics.cpp`. The worktree `/home/jhan/workspace/ai-runs/tron-gdn-amx` is at 882e5322f1 with no local change.
- [R2] Count command, run for each commit: `git -C /home/jhan/workspace/tron show <commit>:<file> | grep -o -E "round_to<bf16>|round_chunk_to<bf16>" | wc -l`. Output (G, E, P): 72e1191804 = 18, 5, 2. f454423b09 = 15, 5, 2. 127a662083 = 15, 5, 2. 69cc70fae0 = 4, 2, 2. 775bba7661 = 19, 5, 2. Line numbers come from the same command with `grep -n`. At 775bba7661 the calls in G are at lines 93, 135, 137, 139, 140, 148, 152, 184, 186, 189, 190, 191, 192, 194, 200 (two calls), 207, 287 and 418.
- [R3] Issue #5433 body, https://github.com/positron-ai/tron/issues/5433 : "that leaves 22 places: 4 in the convolution (#3178), 11 in the recurrence (#3471), 2 at load (#3317), 5 in the executor (#3203)", "#5462 drops the three roundings on the convolution's history entries", and "Six of the seven (after each normalization step) follow Transformers 5.15.1, which normalizes in BF16; 5.17 and later normalize in float32, and #5124 moves the reference to 5.20.2. They come out in this follow-up whatever the measurement says about the other eight."
- [R4] `git -C /home/jhan/workspace/tron diff 127a662083 69cc70fae0 -- h/tron/kernels/gated_delta_net.hpp h/tron/models/gdn_rolling_executor.hpp h/tron/models/gdn_prepared_operation.hpp` (P has no change). PR #5571 body, https://github.com/positron-ai/tron/pull/5571 : "rounding moves a normal value by at most 2^-8 of itself", "This PR takes the 14 out", "Eight roundings stay", and the tolerances "within 2%", "within 2.5%", "at most 11 × 2^-8 (4.3%)".
- [R5] G:32-34 at 127a662083: "Query/key normalization rounds the query and the key to BF16 and rounds again after each square, the reduction, the epsilon operand and its addition, the reciprocal square root, and the normalized multiply."
- [R6] `ingest/runtime/tron_ingest_runtime/ops.py:668-669`. At 127a662083 and at f454423b09: `q = _qwen_l2norm(q).float()`. At d9df90c99d (head of PR #5124, open draft, read with `gh pr view 5124 --repo positron-ai/tron --json headRefOid,state,isDraft`): `q = _qwen_l2norm(q.float())`.
- [R7] Issue #5433 comments. https://github.com/positron-ai/tron/issues/5433#issuecomment-7073599234 : "neither side has been measured". https://github.com/positron-ai/tron/issues/5433#issuecomment-7083755152 (2026-11-22T18:38:17Z, the last comment): "Nothing is measured yet.", "Three builds: all 22 roundings in; only the six normalization roundings out; all fourteen out (#5571)", and the four decision cases, of which case 1 and case 2 end with "#5571 shrinks to the six" and case 3 with "#5571 keeps the fourteen".
- [R8] E at 775bba7661. `step()` in place: E:466 `convolve_token`, E:475 `gdn_recurrence<...>`, E:485 `postprocess`. `step()` on a working copy: E:457-463, the chain kernel with one token. `advance()`: E:543 `prepare_window_token`, E:547-552 block kernel or `gdn_recurrence_chain`, E:556 `postprocess_window_token`. `prepare_window_token`: E:662 `convolve_token`, E:665 `gdn_prepare_recurrence_token`. `convolve_token`: E:642 `gdn_conv1d_silu`. `postprocess_window_token`: E:743 `postprocess`. `postprocess`: E:796-826.
- [R9] `git -C /home/jhan/workspace/tron diff 72e1191804 775bba7661 -- h/tron/models/gdn_rolling_executor.hpp`, hunk `@@ -447,12 +802,14 @@`, replaces the loop `values.store_chunk(local_head_chunk + chunk, round_chunk_to<bf16>(values.chunk(local_head_chunk + chunk)));` and changes the first parameter to `float* values`. The diff of [R4] deletes the same loop at E:467-469 of 127a662083 and changes the first parameter to `tensor<group_value_width> const& recurrence_output`.
- [R10] G:338-343 at 775bba7661: "the value rounded to BF16, the decay and beta of each value head, and the FP32 output. Preparing a token computes these exactly as gdn_recurrence does." E:154-160 at 775bba7661: "On a working copy the recurrence reads the value from the window, rounded to BF16".
- [R11] TG at 775bba7661. TG:2803-2812 `check_advance_matches_step`: `run_chain_case<geometry>(first_position, n_tokens, gdn_block_kernel::off)` and `CHECK(result.advanced_checkpoint == result.stepped_checkpoint)`. TG:2731-2736: the stepped side calls `executor.step` with `gdn_checkpoint_access::in_place`. TG:2743-2751: the advanced side calls `executor.advance` on a working copy. `grep -rn gdn_recurrence_chain t/` in the worktree finds the name only in TA.
- [R12] `h/tron/models/gdn_execution.hpp:167-168` at 775bba7661: `executor.advance(chain.order, chain.source_height.i, gdn_block_kernel::when_available, ...`. E:524-526: `use_block_kernel = block_kernel == gdn_block_kernel::when_available && n_tokens >= to_boundary + gdn_window_tokens && block_kernel_available()`. E:696-734: `advance_window_with_block_kernel`, with the fallback to `gdn_recurrence_chain_head` at E:723-726. A:148-155: `detect()` reads `TRON_AMX_GDN_DISABLE`.
- [R13] A at 775bba7661. A:181-186 `bf16_bits`: `return _mm512_cvtepi32_epi16(_mm512_srli_epi32(_mm512_castps_si512(values), BF16_SHIFT_16));`. A:484-490: the refusal test. `grep -n -i -E "representable|TRON_ASSERT|assert\(" src/tron/kernels/amx_gdn.cpp h/tron/kernels/amx_gdn_iface.hpp` finds only `static_assert` lines (A:21, 28, 71, 74, 100, 138, 140) and the three comments (A:182, I:47, I:130). E:696-734 holds no assert.
- [R14] I:47-53 at 775bba7661: "The three pieces add up to the value exactly when its magnitude is 2^-103 or larger." TA:437-533: TEST_CASE "The AMX GatedDeltaNet block kernel reads the start matrix through an exact split from 2^-103 up".
- [R15] `grep -n normalize_gdn /home/jhan/workspace/ai-runs/tron-gdn-amx/t/t_amx_gdn_numerics.cpp` prints nothing.
- [R16] `h/common/numerics/bf16.hpp:104-116` at 127a662083, Note [BF16 rounding on FP32 bits]: "BF16 keeps FP32 bits 31..16 (the retained bits) and drops bits 15..0 (the discarded bits)", "Zero and subnormal inputs ... become a zero of their sign", "Other finite values round to nearest, ties to even". The same file, line 138: `static constexpr int digits = 8;`. `h/tron/simd/auto.hpp:118-129` at 127a662083 defines `round_chunk_to` and `round_to`.
- [R17] Script 1 of the appendix, run on 2026-11-23 with numpy 2.2.6. Its three output lines, in order: `0.007751820616235141 0.002705021853001515 0.0038910505836575876 0.0013538012244073074 1.2716742436975116e-06` (truncation largest, truncation mean, rounding largest, rounding mean, rounding signed mean), then `0.003294976824484044 0.9971939151043387` (truncated key: relative L2 error, length ratio), then `0.0016507616486772922 0.9999981767991216` (rounded key).
- [R18] Script 2 of the appendix, run on 2026-11-23 with numpy 2.2.6. Its eight output lines hold the matrix error, the output error and the share of differing words, in the row order of the model table of section 5. The first two lines are `0.0033322147747662854 0.006000107891728556 0.815887451171875` and `0.0016681460513187163 0.00231120667026238 0.4967041015625`.

## Appendix: the two scripts

Both ran with `OMP_NUM_THREADS=1 python3 -` and wrote no file.

Script 1 (error of one rounding and of one truncation):

```python
import numpy as np
rng = np.random.default_rng(20261123)
def trunc_bf16(x):
    return (x.astype(np.float32).view(np.uint32) & np.uint32(0xffff0000)).view(np.float32)
def round_bf16(x):  # nearest, ties to even, normal values only
    b = x.astype(np.float32).view(np.uint32).astype(np.uint64)
    return (((b + 0x7fff + ((b >> 16) & 1)) >> 16) << 16).astype(np.uint32).view(np.float32)
m = (np.arange(1 << 23, dtype=np.uint32) | np.uint32(0x3f800000)).view(np.float32)  # all of [1, 2)
x = m.astype(np.float64)
rt = (x - trunc_bf16(m)) / x
rr = (x - round_bf16(m)) / x
print(rt.max(), rt.mean(), np.abs(rr).max(), np.abs(rr).mean(), rr.mean())
k = rng.standard_normal((20000, 128)).astype(np.float32)
q2 = (k * k).sum(axis=1, dtype=np.float32) + np.float32(1e-6)
kn = (k * (np.float32(1.0) / np.sqrt(q2))[:, None]).astype(np.float32)
for f in (trunc_bf16, round_bf16):
    a = f(kn).astype(np.float64); e = kn.astype(np.float64)
    print(np.sqrt(((a - e) ** 2).sum(1) / (e ** 2).sum(1)).mean(),
          np.sqrt((a ** 2).sum(1) / (e ** 2).sum(1)).mean())
```

Script 2 (float64 model of the recurrence; `trunc_bf16` and `round_bf16` as in script 1):

```python
KEY = 128; VAL = 128; HEADS = 2; TOK = 32; BLOCKS = 4
scale = 1.0 / np.sqrt(KEY)
def word(x):
    return (round_bf16(x.astype(np.float32)).view(np.uint32) >> 16).astype(np.int64)
def run(S, K, Q, V, D, B):
    S = S.copy(); outs = []
    for t in range(K.shape[0]):
        for h in range(HEADS):
            Sd = S[h] * D[t, h]
            delta = (V[t, h] - K[t] @ Sd) * B[t, h]
            S[h] = Sd + np.outer(K[t], delta)
            outs.append((Q[t] * scale) @ S[h])
    return S, np.array(outs)
families = [(0.9, 1.0, 0.02, 1.0), (0.999, 1.0, 0.5, 1.0), (0.5, 1.0, 0.02, 1.0), (0.01, 0.3, 1.0, 1.0)]
for fi, (dl, dh, ss, vs) in enumerate(families):
    rng = np.random.default_rng(1000 + fi)
    S0 = ss * rng.standard_normal((HEADS, KEY, VAL)); n = TOK * BLOCKS
    def unit(a):
        a = a.astype(np.float32)
        q2 = (a * a).sum(1, dtype=np.float32) + np.float32(1e-6)
        return (a * (np.float32(1) / np.sqrt(q2))[:, None]).astype(np.float32)
    K = unit(rng.standard_normal((n, KEY))); Q = unit(rng.standard_normal((n, KEY)))
    V = round_bf16((vs * rng.standard_normal((n, HEADS, VAL))).astype(np.float32)).astype(np.float64)
    D = dl + (dh - dl) * rng.random((n, HEADS)); B = 0.05 + 0.9 * rng.random((n, HEADS))
    Sref, Oref = run(S0, K.astype(np.float64), Q.astype(np.float64), V, D, B)
    for f in (trunc_bf16, round_bf16):
        S1, O1 = run(S0, f(K).astype(np.float64), f(Q).astype(np.float64), V, D, B)
        print(np.sqrt(((S1 - Sref) ** 2).sum() / (Sref ** 2).sum()),
              np.sqrt(((O1 - Oref) ** 2).sum() / (Oref ** 2).sum()),
              (word(Oref) != word(O1)).mean())
```
