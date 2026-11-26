# Facts: issue #4444 against today's main, and its link to issue #5433

Read on 2026-11-23. All work was read-only. Nothing was changed on GitHub or in any repository.

## Short version

Issue #4444 (ours, attention kernels) and issue #5433 (GDN owner, GatedDeltaNet kernels) are not the same topic: they share no code, no reference and no decision, and they are closely related only on item 3 of #4444 (the model-level bound), for which the second comment of #5433 gives a written TVD rule.
None of the merged PRs #4366, #4722 and #4975 changes a file that #4444 names, and at main f454423b09 the AVX-512 path still truncates the softmax weights, the AMX path still rounds them, and the dotter still adds in its own order.
Two facts matter for any update of #4444: the weight truncation has its own open issue #4600 (written by the GDN owner) that #4444 never links, and the three-cause result of 2026-10-16 exists only in a local report, not on the GitHub issue.

## Words used here

- **tron, runtron**: tron is the inference program under test. runtron is its command-line tool.
- **AMX, AVX-512**: two Intel CPU instruction sets. AMX multiplies 16-row tiles. AVX-512 works on 16-lane vectors.
- **bf16, fp32, ulp**: bf16 is the 16-bit float of the activations and the KV cache. fp32 is the 32-bit float the sums are formed in. A ulp is one step of the format at the size of the value: 0.39 % to 0.78 % of the value for bf16, about 1e-7 of the value for fp32.
- **RNE**: round to nearest, ties to even.
- **GDN**: GatedDeltaNet, the recurrent layer of the model Qwen3.5.
- **GDN owner**: the author of issue #5433, issue #4600 and PRs #4366, #4722, #4975, #5571 (one author login for all six, read with `gh ... --json author`).
- **dotter**: the AVX-512 loop that scores one query against one key token (`h/tron/kernels/dotter.hpp`).
- **VNNI K layout, VNNI reader**: a K cache layout that the AMX tile multiply reads directly (build option `TRON_K_VNNI`). The VNNI reader (`k_vnni::qk_group`) is the AVX-512 routine that scores keys from that layout.
- **AMX kernels**: `qk_rowmajor_128x4` (the scores) and `weights_times_v_128x4` (the PV product) in `src/tron/kernels/amx_attn.cpp`. Build option `TRON_AMX_DISPATCH`.
- **P, PV**: P are the softmax weights exp(score - max). PV is the product of P with the stored values V.
- **kill switch**: the environment variable `TRON_AMX_DISABLE=1`. The same binary runs with the AMX kernels off.
- **clean binary, row-major binary**: a build with `TRON_AMX_DISPATCH` off.
- **KV page, dense page**: a KV page is 64 tokens of the cache. A dense page is a full page that the AMX kernels take whole.
- **kv_mul**: the number of query heads per KV head.
- **logits, margin, flip**: logits are the per-word scores of one step. The margin is the gap between the two best logits. A flip is a step where two runs pick a different best token.
- **forced run**: teacher forcing. Both runs are fed the same tokens, so they score the same context at every step.
- **TVD**: total variation distance between two next-token probability distributions. 0 means identical. 1 means no shared tokens.
- **Note [AMX attention dispatch]**: a named comment block in `h/tron/kernels/amx_attn_iface.hpp`.
- **the 2026-10-16 report**: the local file `/home/jhan/workspace/intel-AMX/token-divergence-4444/token-divergence-issue4444-report.html` [R23].
- **all-22, six-out, fourteen-out**: the three builds of issue #5433. All-22 keeps all 22 bf16 rounding calls of the GDN host code. Six-out removes the six normalization roundings. Fourteen-out is PR #5571.

## 1. What was read, and the three merged PRs

State of the two issues:

- Issue #4444 is open. It has a body of 2026-09-16 and three comments (2026-10-14, 2026-10-18, 2026-10-19). Its last update is 2026-10-19 [R1][R2][R3][R4].
- Issue #5433 is open. It has a body of 2026-11-18 and two comments of 2026-11-22. The second comment holds the thresholds. It says "Nothing is measured yet" [R5][R6][R7].
- The body and the three comments of #4444 do not contain the three causes. Comment 2 cites "the 2026-10-16 report of this issue" and "cause 2 of the 2026-10-16 report". That report is a local file [R3][R23].
- Neither issue links the other. The timeline of #4444 has no cross-reference from #5433 or #5571. The timeline of #5433 has cross-references from PRs #3178, #3471, #5462, #3203 and #5571 only [R31].

### PR #4366 "Round BF16 stores to nearest even" (merged 2026-10-08, merge commit f681622f24) [R8]

1. Code: the shared fp32-to-bf16 vector conversion, the striped stores of the wide kernels and the V cache writes (`append_v_row`) changed from truncation to RNE. They now use the AVX-512 BF16 convert instruction [R26].
2. Measured: mean TVD against stored Hugging Face logits fell in four of five test configurations. GPT-OSS 20B with the CPU router went from 0.0482 to 0.0114 (20 positions). Gemma 4 31B went from 0.0227 to 0.0049 (21 positions). Gemma 4 26B-A4B went from 0.2763 to 0.1644 (22 positions). Llama 3.1 8B with two layers went from 0.0042 to 0.0028 (40 positions). GPT-OSS 20B with the FPGA router rose from 0.0523 to 0.0534.
3. Measured: throughput of eight models moved by -0.39 % to +0.54 %, and the PR body says that no change is outside run-to-run variation.
4. Decided: RNE is the rule for every bf16 store, with two stated exceptions. One exception is the attention path: "the AVX-512 attention code, which truncates its softmax weights before a dot product and never stores them (#4600)".

### PR #4722 "Tighten the GPT-OSS 20B golden-logit limit" (merged 2026-10-10, merge commit 83d8f2fbe7) [R9]

1. Code: one test file, `t/t_generate_ingest_1_gpt_oss_20b.cpp`. No kernel code.
2. Change: the TVD limit per position fell from 0.10 to 0.05. The allowance for 2 of 20 positions above the limit (cap 0.30) was removed.
3. Measured: at main 6970c42347 on 8 cards the largest TVD is 0.0409 and the mean is 0.0114. A return to truncating stores would fail the new limit (8 of 20 positions above 0.05, up to 0.166).
4. Decided: every position must be at most 0.05, which leaves a margin of about 18 %.

### PR #4975 "Merge row_dot's accumulators in FP32" (merged 2026-10-31, commit 10e54cd34a) [R10]

1. Code: `row_dot_block` in `h/tron/kernels/host_matvec.hpp` is the bf16 product of the CPU router of mixture-of-experts models. It now merges its two fp32 accumulators in fp32 (`reduce_sum(a[j] + c[j])`). The fp64 merge helper `reduce_sum_fp64` and the test that fixed it were deleted [R25].
2. Measured: an offline replay on 37,985 token-layers of GPT-OSS 120B router inputs. The two merges disagree on 44.6 % of the single router logits, by a few fp32 ulps. After the bf16 store 0.003 % still differ. The chosen top-4 experts are identical in every token-layer.
3. Measured: on the card, `t_generate_ingest_1_gpt_oss_20b` gives bit-identical logits with both merges (mean TVD 0.01140, largest 0.04091). Gemma 4 26B-A4B, Qwen3 30B-A3B and throughput were not measured.
4. Decided: the fp64 merge is not needed and was removed. The PR closed issue #4792.

`row_dot_block` is not the attention dotter. The name is similar. The file is different [R17][R25].

### PR #5571 "Keep the GatedDeltaNet layer's intermediate values in FP32" (draft, open) [R11]

- It sits on the branch of PR #3221 (127a662083). It has two commits: 59429b0955 and 69cc70fae0.
- It changes three files: `h/tron/kernels/gated_delta_net.hpp`, `h/tron/models/gdn_rolling_executor.hpp`, `t/t_gated_delta_net.cpp`.
- Its body says: "Neither side has been measured; #5433 decides whether this lands once its figures are in."

## 2. Do the three merged PRs change code that issue #4444 names?

No. The table compares the file list of each PR (`gh pr view N --json files`) with the code that #4444 names.

| Code that #4444 names | #4366 | #4722 | #4975 |
|---|---|---|---|
| dotter accumulators and merge (`h/tron/kernels/dotter.hpp`, `reduce_sum` in `h/tron/simd/fp32.hpp`) | not touched | not touched | not touched |
| truncation of P (`interleave_bf16_ps` in `h/tron/models/kv_cache.hpp`) | not touched, left to #4600 by name | not touched | not touched |
| VNNI reader `k_vnni::qk_group` | not on main | not on main | not on main |
| AMX kernels (`src/tron/kernels/amx_attn.cpp`) | not touched | not touched | not touched |
| Note [AMX attention dispatch] (`h/tron/kernels/amx_attn_iface.hpp`) | not touched | not touched | not touched |

Supporting facts:

- The four attention kernel files have no commit between 72308ec90c (the main that #4444 measured) and f454423b09. The command in [R19] prints nothing for `dotter.hpp`, `dotter2.hpp`, `amx_attn_iface.hpp`, `amx_attn.cpp` and `t_amx_numerics.cpp`.
- `interleave_bf16_ps` has the same body at 72308ec90c and at f454423b09. Only its line number moved, from 2315 to 2400 [R13].
- PR #4366 is an ancestor of both measured mains (72308ec90c and 6198824246). PR #4722 is an ancestor of 6198824246 only. PR #4975 is an ancestor of neither [R20].

### Statements of #4444 that the three PRs make out of date

Only one group of statements is affected, and comment 1 already withdrew it.

- Old statements (body, "What was observed"): "llama-3.1-8b first different token at step 46; qwen-3-30b-a3b (kv_mul 8, where every page goes through the VNNI reader) first different token at step 5" and "base and VNNI binaries diverged at step 52" [R1].
- These runs are from September 2026. PR #4366 merged on 2026-10-08. So they ran with truncating bf16 stores.
- New fact: on main the shared conversion rounds. `h/tron/simd/bf16.hpp:62-63` at f454423b09 reads `return std::bit_cast<bf16x16>(_mm512_cvtneps_pbh(x.data));` [R26]. PR #4366 measured that this changes logits (Llama 3.1 8B with two layers: mean TVD 0.0042 to 0.0028) [R8].
- For qwen-3-30b-a3b one more input changed. Its config entry sets `moe_router: cpu`, and PR #4975 changed the merge of that router product (`h/tron/kernels/host_matvec.hpp:163` at f454423b09) [R25].
- Comment 1 already says: "The September observations above (PR #4424, steps 46, 5 and 52) were made without score records and are superseded by these two runs" [R2].
- Not verified: that the step numbers 46, 5 and 52 differ on today's main. A rerun of those three cells would settle it.

All measurements in the three comments already include PR #4366 [R20]. The Glimmer measurement of comment 2 (main 6198824246) predates PR #4975. The four `moe_router: cpu` entries of `config/models.yaml` are GPT-OSS 20B, GPT-OSS 120B, Gemma 4 A4B and Qwen3 30B. None is a Glimmer entry [R25].

### Statements of #4444 that are out of date for other reasons

- Body, Related: "PR #4424 (VNNI K layout, open)". PR #4424 is still open, as a draft. The stack #4956 to #4959 replaces it, as comment 1 says [R21].
- Body, item 2: "Decide the kill-switch contract (reviewers of PR #4424)". The reviewers are now those of the stack [R2][R21].
- Body links to `k_vnni.hpp`, `t_k_vnni_layout.cpp` and `kv_cache.hpp` lines 706-710 at ff680c8020. Those files and lines belong to the PR #4424 branch. `k_vnni.hpp` and `t_k_vnni_layout.cpp` do not exist at f454423b09 [R22].
- Body links to Note [AMX attention dispatch] lines 74-85 and 47-51 at ff680c8020. On main the same text sits at the same line numbers [R16].
- Comment 2 names PR #5015. It was closed without merge on 2026-10-19. PR #5022 replaces it, as comment 3 says [R21].
- Comment 2 cites "the 2026-10-16 report of this issue". No comment holds that report [R3][R23].
- No statement of #4444 names issue #4600. Issue #4600 names #4444 [R12].

## 3. Today's main (f454423b09)

### Cause 2 (truncation of P on the AVX-512 path against RNE on the AMX path): still present

AVX-512 path. The caller forms the weights and passes them to `scaled_v` [R14]:

```
1960:         exp_s_minus_m = exp(s_page - m_page);
1966:               page.template scaled_v<geometry.kv>(
1967:                   slot, kv_head, exp_s_minus_m, scratch)));
1968:           head_sp.s_star = head_sp.s_star * exp_m_star_minus_m + sum(exp_s_minus_m);
```

`scaled_v` narrows two weight vectors per token pair with `interleave_bf16_ps` [R13]:

```
2400:   bf16x32 interleave_bf16_ps(fp32x16 lo_fp32, fp32x16 hi_fp32) const noexcept {
2401:     bf16x32 lo_bf16 = _mm512_srli_epi32(_mm512_castps_si512(lo_fp32), 16);
2402:     bf16x32 hi_bf16 = _mm512_castps_si512(hi_fp32);
2403:     return _mm512_ternarylogic_epi32(
2404:         lo_bf16, hi_bf16, hi_16_of_32, _MM_TERNLOG_A | (_MM_TERNLOG_B & _MM_TERNLOG_C));
```

- Line 2401 shifts the low weight right by 16 bits. That drops its low 16 bits.
- Lines 2403-2404 keep only the upper 16 bits of the high weight (`hi_16_of_32` is `0xffff0000`, line 2347).
- Both are truncation toward zero. The divisor `s_star` on line 1968 is summed from the unrounded weights.
- The call sites are lines 2274, 2354 and 2368 (head sizes 256/512, 64 and 128).

AMX path [R15]:

```
235:       __m512 lo = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c);
236:       __m512 hi = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c + 16);
239:       _mm512_storeu_si512(P[q] + c, (__m512i)_mm512_cvtne2ps_pbh(hi, lo));
```

`_mm512_cvtne2ps_pbh` rounds to nearest even.

The Note still documents the difference [R16]:

```
77: //   1. the bf16 rounding of the PV weights P = exp(s - max): the AVX path
78: //      truncates (drops the low 16 bits), the AMX path rounds to nearest
79: //      even (VCVTNE2PS2BF16). A truncating version is a one-line change
80: //      at the cvtne2ps_pbh call if AVX-style rounding is ever required;
```

Issue #4600 is the open issue for exactly this truncation [R12]:

- Title: "AVX-512 scaled_v truncates softmax weights to BF16, biasing attention output low". Created 2026-09-24. Open. No comments.
- It proposes to round the weights before the interleave and to update the Note and `t_amx_numerics.cpp`.
- It says: "Switching the AVX path to RNE would remove one of the two documented sources of AVX/AMX divergence (see #4444)."
- It asks to "Re-run the attention-sensitive accuracy fixtures (GPT-OSS 20B, two-layer Llama, dense Gemma 31B) and record the TVD changes."
- Its scalar model gives a mean bias of -0.057 % to -0.266 % for truncation and about 0 for RNE. The 2026-10-16 report measured -0.08 % on real qwen3-4b data [R23].

### Cause 1 (three fp32 add orders): the dotter is as described, and its order is now fixed in source

The dotter for head size 128 keeps 2 accumulators of 16 lanes [R17]:

```
216:     fp32x16 sum1 = _mm512_dpbf16_ps(_mm512_setzero_ps(), x01, y01);
217:     fp32x16 sum2 = _mm512_dpbf16_ps(_mm512_setzero_ps(), x23, y23);
218:     sum1 = _mm512_dpbf16_ps(sum1, x45, y45);
219:     sum2 = _mm512_dpbf16_ps(sum2, x67, y67);
220:     return reduce_sum(sum1 + sum2);
```

`reduce_sum` is the halving tree [R17]:

```
680: // reduce_sum(fp32x16) adds lane i + 8 to lane i, then lane i + 4, then lane i + 2,
681: // then lane 1 to lane 0, in plain adds that the compiler keeps in order. This is the
682: // tree clang 19 emits for _mm512_reduce_add_ps, whose order is unspecified: ...
```

- New since the issue: PR #5232 (merged 2026-11-21) replaced `_mm512_reduce_add_ps` by this explicit tree. Its body states that no result bit changes for sums that are not NaN [R18].
- So the dotter order that the 2026-10-16 report found by test (halving j+8, j+4, j+2, 0+1) is now written in the source [R23][R18].
- `row_dot` is not part of cause 1. It exists only in `h/tron/kernels/host_matvec.hpp` (the router product) [R25].
- The VNNI reader order exists only on the stack branches. `k_vnni::qk_group` has no match at f454423b09 [R22].
- The AMX tile order is in `amx_attn.cpp`, unchanged since 2026-10-07 [R19].

### Item 4 of Note [AMX attention dispatch] today

`h/tron/kernels/amx_attn_iface.hpp:47-51` at f454423b09 [R16]:

```
47: //   4. runtime disable: TRON_AMX_DISABLE=1 in the environment makes
48: //      available() false. Contract: AMX off, same layout, same AVX dotter,
49: //      clean-binary numerics; it exists for same-binary A/B tests and for
50: //      rollback. It will be listed in the TRON environment-variable document
51: //      (https://github.com/positron-ai/tron/issues/4338).
```

- The text is the one that #4444 quotes. It is unchanged at ff680c8020, 72308ec90c and f454423b09.
- The same text stands at the heads of PR #4956 (a5697f86d3), PR #4957 (26b86a279a), PR #4959 (6b081187e1), PR #5022 (ddf843ad97) and at our GDN worktree head 882e5322f1 [R16]. So neither option (a) nor option (b) of item 2 has been written into any branch.
- At main 72308ec90c the contract held. The 2026-10-16 report found the clean binary and main under the kill switch identical in all 416,443 compared records and all 256 logit vectors [R23]. This was not measured again at f454423b09. The attention kernel files are unchanged since then [R19].

## 4. State of the PRs that issue #4444 names

Read with `gh pr view N --json state,isDraft,mergedAt,closedAt` on 2026-11-23 [R21].

| PR | State | Merged | Note |
|---|---|---|---|
| #3879 AMX software attention | MERGED | 2026-09-15T22:54:27Z | on main |
| #4424 VNNI K (single PR) | OPEN, draft | no | replaced by the stack below |
| #4956 VNNI K layout and readers | OPEN | no | base main, head a5697f86d3 |
| #4957 VNNI K in AMX attention | OPEN | no | head 26b86a279a |
| #4958 16-token block saves | OPEN | no | head b39765ec29 |
| #4959 row-major tail block, deb preset | OPEN | no | head 6b081187e1 |
| #5015 kv_mul 16 (Glimmer) | CLOSED, not merged | no | closed 2026-10-19T00:37:55Z |
| #5022 kv_mul 16 (Glimmer), ours | OPEN | no | head ddf843ad97, updated 2026-11-20 |

Is the VNNI K layout on main? No [R22].

- `git grep TRON_K_VNNI f454423b09` finds no file.
- `CMakeLists.txt:46` at f454423b09 has only `option(TRON_AMX_DISPATCH ... OFF)`.
- `CMakePresets.json:57-70` at f454423b09: the `deb` preset sets `"TRON_AMX_DISPATCH": "ON"` (line 68) and has no VNNI K entry. PR #4505 added that line (merged 2026-09-22).
- At the PR #4959 head the option exists (`CMakeLists.txt:47`) and the `deb` preset sets `"TRON_K_VNNI": "ON"` (`CMakePresets.json:69`).

Consequence for #4444 on main: causes 1 and 2 exist only as the AMX-against-dotter pair. The reader-against-dotter pair and cause 3 (the page-end path choice of PR #4959) exist only on the open stack branches.

## 5. The link between the two issues

### Comparison

| | Issue #4444 (ours) | Issue #5433 (GDN owner) |
|---|---|---|
| Code | Software attention: dotter, VNNI reader, AMX kernels, the PV loop in `kv_cache.hpp` [R13][R15][R17] | GDN host code: `gated_delta_net.hpp`, `gdn_rolling_executor.hpp`, `gdn_prepared_operation.hpp`, `t_gated_delta_net.cpp` [R5][R11] |
| Reference | Another tron run: the row-major (clean) binary, or the kill-switch run of the same binary. No outside reference [R1] | The Transformers (PyTorch) model in BF16, and the all-22 build [R7] |
| Trial | The binary with the AMX kernels or the VNNI K layout on [R1] | Six-out and fourteen-out (PR #5571) [R7] |
| Kind of difference | Three fp32 add orders in the score. Truncation of P against RNE in PV. One path choice at a page end (PR #4959 only) [R23] | A round-to-bf16 call (RNE) is present or absent at 14 points. The values stay fp32 instead [R11] |
| Size of one difference | Add order: a median of one fp32 ulp of a score, at most 2 bf16 ulps where the sum cancels. Rounding of P: 0 or 1 bf16 step per weight, always toward zero, with a measured output bias of -0.08 % [R23] | "rounding moves a normal value by at most 2^-8 of itself" (half a bf16 step, no fixed sign). First-order bounds in PR #5571: 4.1 x 2^-8 (1.6 %) and 5.5 x 2^-8 (2.15 %) for the normalization, 11 x 2^-8 (4.3 %) for an executor row [R11] |
| How the effect is measured | Token identity over 256 greedy tokens. Forced runs: flips, margin in bf16 ulps, TVD per step between two tron runs, relative change of logged records [R2][R3][R23] | Mean TVD over 768 positions of one 8,192-token text. Loss on the text's own next token. The two cases of one golden test. Kernel and card speed tests [R7] |
| Decision rule | None written. Item 3 is "Optional" and "Not started". Only kernel-level error bands exist in unit tests [R1][R2][R32] | Written before the measurement: the TVD test, three damage tests, speed tests, a four-case reading rule [R7] |
| Who decides | "reviewers of PR #4424" for the kill-switch contract [R1] | The GDN owner: "I read the results once" and "I decide from the results" [R7] |
| Still open | Item 2 (kill-switch contract). Item 3 (model-level bound). Which arm's rounding is preferable. Issue #4600 [R2][R12] | Everything: "Nothing is measured yet". The six-out build does not exist yet [R7] |

### The thresholds of #5433, quoted from its second comment [R7]

The TVD test:

> The TVD test reads little when, on the 4B over 768 positions of one 8,192-token text, the mean TVD between fourteen-out and six-out is at most a tenth of the all-22 build's mean TVD from the Transformers model in BF16 (the issue has the all-float32 model); above that it reads not little. The logits come from card runs, where the issue sketches Python, because a card run executes the kernels themselves.

The three damage tests:

> Three damage tests run on the 4B. Loss is the mean negative log-probability of that text's own next token. The first passes when the 95% interval of the rise in loss ends at or under a tenth of the all-22 build's loss gap to the Transformers model. The second passes when the interval of that rise's growth from the text's first quarter to its last does too. The third passes when six-out and fourteen-out each pass both cases of `t_generate_ingest_1_qwen3_5_4b_fpga`.

The speed tests:

> A speed test reads faster when the 95% interval of the relative gain over paired runs lies above 0, otherwise no gain when its upper end is under r, otherwise undecided.

> r is 9% for `gdn_conv1d_silu<8192>`, 0.85% for `gdn_recurrence<16, 32, 128, 128> step`, 1.95% for a 128-token replay through the executor, and 0.35% for decode tokens a second per user on four cards (Qwen3.5-4B and 27B, each at 1, 2, 4 and 8 users, eight tests; 1,991-token prompts).

The four-case reading rule:

> I read the results once, when every run above has ended, and the first case that holds applies:
>
> 1. The TVD test reads not little: the eight stay and #5571 shrinks to the six.
> 2. Every speed test reads no gain: #5571 shrinks to the six.
> 3. The TVD test reads little, every speed test reads faster and every damage test passes: #5571 keeps the fourteen.
> 4. Anything else: I decide from the results, and #5571 does not change before that.

One more rule: "A test whose runs break the rules fixed for them beforehand reads undecided, whatever its figures."

Fact about the third damage test: the file `t/t_generate_ingest_1_qwen3_5_4b_fpga.cpp` does not exist at main f454423b09, at the PR #3696 head 72e1191804, at the PR #3221 head 127a662083 or at the PR #5571 head 69cc70fae0. It exists on later branches of the Qwen3.5 stack, for example at cb9a5dc070, the head of draft PR #3215 [R27].

### Data that #4444 already holds on the TVD scale

Computed today from the per-step files of our campaigns [R24]. TVD is half the sum of the absolute differences of the two softmax rows over the whole vocabulary, per forced step.

| Model, prompt length, pair | What differs | Mean TVD | Largest TVD | Flips in 256 steps |
|---|---|---|---|---|
| qwen3-4b, prompt 1024, kill switch against AMX on main | add order and rounding of P | 0.00585 | 0.032 | 2 |
| qwen3-4b, prompt 1024, RNE against truncated P, same AMX order | rounding of P only | 0.00598 | 0.057 | 0 |
| qwen3-4b, prompt 1024, AMX order against AVX order, both truncated | add order only | 0.00533 | 0.049 | 1 |
| qwen3-4b, prompt 1024, VNNI reader against dotter, kill switch on both | add order only | 0.00526 | 0.037 | 2 |
| qwen3-4b, prompt 1024, clean binary against main with the kill switch | nothing | 0 | 0 | 0 |
| qwen3-4b, prompt 1024, kill switch against AMX on the stack | add order and rounding of P | 0.00596 | 0.055 | 1 |
| qwen3-4b, prompt 8192, kill switch against AMX on the stack | add order and rounding of P | 0.0000081 | 0.0017 | 0 |
| Muse Glimmer 30B, prompt 1024, AVX against AMX (PR #5015) | add order and rounding of P | 0.0182 | 0.49 | 3 |

What the table shows:

- A pure add-order change (one fp32 ulp in a score) gives nearly the same mean TVD as the rounding change of P (0.0053 against 0.0060).
- The same pair of runs (the stack binary with and without the kill switch) gives a mean TVD about 700 times smaller at prompt 8192 than at prompt 1024 (0.0000081 against 0.00596). The report explains this with the margins: the median margin is 19.75 logit units at prompt 8192 and 3.9 at prompt 1024 [R23].
- These are TVD values between two tron runs. No TVD of tron against a Transformers model exists for qwen3-4b in these records.

### (a) Could the thresholds of #5433 serve as the model-level bound of item 3?

Yes for the form of the rule, no for the numbers. The TVD test of #5433 has two parts: a pair of builds whose mean TVD is measured, and a reference distance (the all-22 build against the Transformers model in BF16) of which the pair may use one tenth. Item 3 of #4444 asks for "a test that compares the logits of the clean binary and the VNNI binary on a fixed prompt (for example total variation distance per step)" [R1]. The adaptation needs four changes. First, the pair becomes the AMX run against the kill-switch run of one binary. At main 72308ec90c the kill-switch run equalled the clean binary bit for bit, so one binary is enough on main [R23]. Second, the reference distance must be measured for an AMX-served model: the kill-switch run against a Transformers model in BF16 on the same text. No such number exists for qwen3-4b. Main has no golden-logit test for qwen3-4b [R28]. Third, the text must be long enough for dense pages. The AMX kernels take full 64-token pages only. The existing golden-logit tests for Llama 3.1 8B and Muse Glimmer force 21 and 9 tokens, so they never reach an AMX kernel [R28]. The 768 positions of an 8,192-token text of #5433 would reach them. Fourth, the text must be chosen with the margins in mind. Our two cells differ by a factor of about 700 in mean TVD for the same pair of paths, so one text can pass and another fail the same "one tenth" rule. The loss tests of #5433 could be taken over unchanged in form. Our campaigns hold no loss number, because the forced tokens were the model's own output and not a given text [R23]. Insufficient data: whether the AMX-against-kill-switch pair would pass. The measurement that settles it is the reference distance for one AMX-served model on the chosen text.

### (b) Does anything in #5433 or PR #5571 change code on the attention paths of #4444?

No. PR #5571 changes three files, all GDN (`git diff --stat 127a662083 69cc70fae0`) [R11]. A search of the three GDN host files at 69cc70fae0 for `dotter`, `scaled_v`, `amx_attn` and `interleave_bf16_ps` finds nothing [R11]. Issue #5433 names only GDN files and `ingest/runtime/tron_ingest_runtime/ops.py` [R5]. The only attention-related rounding change that the GDN owner has proposed is issue #4600, and no PR implements it: the truncation is still on main [R12][R13].

### (c) Statements of #5433 that the data of #4444 answers or contradicts

- #5433 says: "Measured elsewhere, for other models and other roundings: #4366, #4722, #4975." The list is incomplete, not wrong. Issue #4444 and the 2026-10-16 report hold a fourth measurement of this kind (attention, qwen3-4b and Glimmer), and issue #4600 a fifth (a scalar model of the weight truncation) [R3][R12][R23].
- On how often a rounding-size change flips a token, #4444 has numbers. On qwen3-4b at prompt 1024, each pair of paths changes 74 % to 82 % of the logits by at least one bf16 ulp at the median step. The best token changes at 0 to 2 of 256 forced steps per pair. All flips sit at margins of 0 to 2 bf16 ulps. At prompt 8192 no step flips [R23]. On Glimmer 3 of 256 forced steps flip, at base margins of 21 ulps, 0 and 9 ulps [R3].
- The GDN code has one add-order difference from PyTorch today, and the rounding hides it. The Note on main says: "The squares are added per lane and then across lanes in FP32; that order differs from PyTorch's, so only the rounded total is matched" [R29]. PR #5571 removes the rounding of that total (the point "their sum" of the seven) [R11]. So after PR #5571 an add order of the kind of cause 1 becomes visible against PyTorch at fp32 size. Issue #5433 does not mention this.
- A free-running token comparison is not usable as a damage test. After the first flip the two runs follow different texts: on Glimmer 200 to 249 of 256 positions differ after the first difference [R3]. The damage tests of #5433 use forced positions and loss, which avoids this.
- The golden test of the third damage test demands the same best token only where the reference margin is at least 3.0 (`kReferenceStrictTop1Margin = 3.0f` at cb9a5dc070) [R27]. On Glimmer, one AMX-against-AVX flip happened at a base margin of 4.5 logit units [R3]. This is another model and another pair, so it is an observation and not a contradiction.
- Hypothesis, not measured for GDN: the mean TVD between fourteen-out and six-out will depend more on the chosen text than on the size of the removed roundings. The basis is the table above (equal mean TVD for a one-fp32-ulp change and a one-bf16-step change, and a factor of about 700 between two prompts). The measurement that would test it is a control pair in the #5433 runs that differs only in an fp32 add order.
- #5433 says the 14 roundings have "one known use", the exact comparison of the kernel tests with PyTorch [R5]. Our GDN AMX block kernel is a second use on our branch. It packs the normalized key and query with `bf16_bits()`, which keeps the upper 16 bits of each fp32 value, and its comment requires "values that are representable in bf16" [R30]. At the PR #5571 head the Note says "Query/key normalization uses the query and the key as given" and "The recurrence uses query, key and value as given" [R29]. This fact concerns our GDN work, not issue #4444. The shift by 16 bits is the same operation as line 2401 of `interleave_bf16_ps`, so on fp32 input it would be a truncation of the kind that cause 2 describes.

## 6. Verdict

The two issues are not the same topic. They are closely related on one part only: item 3 of #4444, the model-level bound. On code, on the reference, on the decision and on the owner they are loosely related.

The three strongest facts for "closely related":

1. Item 3 of #4444 asks for a model-level TVD test and has no rule. The second comment of #5433 is a complete written rule of that kind (a pair, a reference distance, a one-tenth limit, loss tests, a reading order) [R1][R7].
2. The GDN owner treats these roundings as one family and has already tied the attention path to it. PR #4366 names the attention weight truncation as its exception. Issue #4600, by the same author, is cause 2 of #4444 and cites #4444. Issue #5433 lists PR #4366, #4722 and #4975 as earlier measurements of "other roundings" [R8][R12][R5].
3. #4444 already holds data on the exact quantity that #5433 will measure: mean TVD per forced step between two builds, the flip rate, and their dependence on the text (section 5) [R24].

The three strongest facts against "closely related":

1. No code is shared. PR #5571 changes three GDN files. None of #4366, #4722, #4975 or #5571 changes a file that #4444 names [R8][R9][R10][R11].
2. The comparison and the decision differ. #4444 compares two tron paths for the same arithmetic and its main open item is a rollback contract (what the kill switch promises). #5433 compares tron with PyTorch and decides whether to delete rounding calls for speed. The text of #5433 has no kill switch, no add-order question and no rollback question [R1][R5][R7].
3. The kind of numeric difference differs. #4444 is an add order (unavoidable between two kernels) plus a one-sided truncation with a measured bias. #5433 removes RNE calls, which have no fixed sign. The models, the deciders and the test named in the rule (a Qwen3.5 4B golden test that is not on main) also differ [R23][R11][R27].

What an update of #4444 could state without going beyond these facts: a pointer to #5433 as a written TVD rule that item 3 could adopt, a pointer to #4600 as the open issue for cause 2, and the three-cause result with the TVD table of section 5. The facts do not support merging the two issues or moving the kill-switch item to #5433.

## 7. Not verified

- Whether the body of #4444 ever held the 2026-10-16 result in an earlier edit. The edit history was not read. The command would be a GraphQL query of `userContentEdits` on the issue.
- Whether the September step numbers (46, 5, 52) repeat on today's main. A rerun of those cells would settle it.
- The reference distance (tron against a Transformers model in BF16) for qwen3-4b, llama-3.1-8b or Glimmer on a text with dense pages. A forced run of the kill-switch binary and of the Transformers model on one text of at least 128 tokens would give it.
- Which six of the seven normalization roundings #5433 means by "after each normalization step". The wording suggests that the rounding of the normalized product is one of the six (est.). A statement by the GDN owner or a six-out build would settle it.
- Whether Muse Glimmer uses the CPU router product that PR #4975 changed. `config/models.yaml` shows `moe_router: cpu` on four other models only. Reading the Glimmer plugin source would settle it.
- Nothing was built or run on a test machine for this report. Every number is taken from a GitHub page or from an existing result file.

## References

- **[R1]** Issue #4444, body: https://github.com/positron-ai/tron/issues/4444 . Read with `gh issue view 4444 --repo positron-ai/tron --json title,state,createdAt,updatedAt,body,comments`. State OPEN, created 2026-09-16T03:13:36Z, updated 2026-10-19T00:40:01Z, 3 comments.
- **[R2]** Issue #4444, comment 1 of 2026-10-14 ("Status after the four stack PRs"): https://github.com/positron-ai/tron/issues/4444#issuecomment-6158706248
- **[R3]** Issue #4444, comment 2 of 2026-10-18 (Muse Glimmer): https://github.com/positron-ai/tron/issues/4444#issuecomment-6255615621
- **[R4]** Issue #4444, comment 3 of 2026-10-19 (PR #5022 replaces #5015): https://github.com/positron-ai/tron/issues/4444#issuecomment-6257210309
- **[R5]** Issue #5433, body: https://github.com/positron-ai/tron/issues/5433 . State OPEN, created 2026-11-18T16:25:34Z, updated 2026-11-22T18:38:17Z, 2 comments.
- **[R6]** Issue #5433, comment 1 of 2026-11-22T03:32:04Z: https://github.com/positron-ai/tron/issues/5433#issuecomment-7073599234
- **[R7]** Issue #5433, comment 2 of 2026-11-22T18:38:17Z (the thresholds): https://github.com/positron-ai/tron/issues/5433#issuecomment-7083755152
- **[R8]** PR #4366: https://github.com/positron-ai/tron/pull/4366 . `gh pr view 4366 --repo positron-ai/tron --json title,body,mergedAt,mergeCommit,files`: merged 2026-10-08T18:01:30Z, merge commit f681622f24. Files: `h/common/numerics/bf16.hpp`, `h/tron/emulation/debug.hpp`, `h/tron/emulation/matmul.hpp`, `h/tron/kernels/host_matvec.hpp` (+0 -1), `h/tron/kernels/wide.hpp`, `h/tron/models/mixture_of_experts.hpp`, `h/tron/simd/bf16.hpp`, `h/tron/tensor/v_vnni.hpp`, `ingest/src/TronCpp.hs` and seven test files. `gh pr diff 4366` has no hunk in a file whose path contains dotter, kv_cache, amx_attn, k_vnni or self_attention.
- **[R9]** PR #4722: https://github.com/positron-ai/tron/pull/4722 . Merged 2026-10-10T21:28:12Z, merge commit 83d8f2fbe7. One file: `t/t_generate_ingest_1_gpt_oss_20b.cpp` (+6 -12).
- **[R10]** PR #4975: https://github.com/positron-ai/tron/pull/4975 . Merged 2026-10-31T00:21:32Z, commit 10e54cd34a. Files: `config/test-benchmarks.json`, `h/tron/kernels/host_matvec.hpp` (+6 -20), `t/t_host_matvec.cpp` (+0 -24).
- **[R11]** PR #5571: https://github.com/positron-ai/tron/pull/5571 . Draft, OPEN, base `rbjarnason/qwen35-37-gdn-head-parallel`. `git -C /home/jhan/workspace/tron log --format='%h %cs %s' 127a662083..69cc70fae0` lists 69cc70fae0 and 59429b0955. `git diff --stat 127a662083 69cc70fae0` lists three files: `h/tron/kernels/gated_delta_net.hpp`, `h/tron/models/gdn_rolling_executor.hpp`, `t/t_gated_delta_net.cpp`. `git grep -n -E "dotter|scaled_v|amx_attn|interleave_bf16_ps" 69cc70fae0 -- h/tron/kernels/gated_delta_net.hpp h/tron/models/gdn_rolling_executor.hpp h/tron/models/gdn_prepared_operation.hpp` prints nothing. Lines that contain `round_to<bf16>` or `round_chunk_to<bf16>` in the three GDN host files: 21 at 127a662083 and at f454423b09, 8 at 69cc70fae0.
- **[R12]** Issue #4600: https://github.com/positron-ai/tron/issues/4600 . State OPEN, created and last updated 2026-09-24T23:19:20Z, no comments, same author login as #5433. The timeline of #4444 lists a cross-reference from #4600 on 2026-09-24.
- **[R13]** `h/tron/models/kv_cache.hpp` at f454423b09: `interleave_bf16_ps` lines 2399-2405, call sites 2274, 2354, 2368, `hi_16_of_32(_mm512_set1_epi32(0xffff0000))` line 2347. At 72308ec90c the function is at line 2315, at the PR #4959 head 6b081187e1 at line 2996. A `diff` of the function body between 72308ec90c and f454423b09 reports no difference.
- **[R14]** `h/tron/models/self_attention.hpp` at f454423b09: AVX-512 page loop lines 1957-1973, AMX score call line 1764, AMX PV call line 1791. `git diff 72308ec90c f454423b09 -- h/tron/models/self_attention.hpp` shows changes in hardware-plan and wait code only (lines 630 to 860).
- **[R15]** `src/tron/kernels/amx_attn.cpp` at f454423b09, `weights_times_v_128x4`, lines 218-241.
- **[R16]** `h/tron/kernels/amx_attn_iface.hpp` at f454423b09: item 4 lines 47-51, numerics lines 74-85. `git show <commit>:h/tron/kernels/amx_attn_iface.hpp | grep -n -A4 "4. runtime disable"` gives the same text at ff680c8020 (line 47), 72308ec90c (47), a5697f86d3 (47), 26b86a279a (49), 6b081187e1 (49), ddf843ad97 (50), 882e5322f1 (50). A `diff` of lines 74-85 between ff680c8020 and f454423b09 reports no difference.
- **[R17]** `h/tron/kernels/dotter.hpp` at f454423b09, `dotter<bf16, 128, aligned>::dot`, lines 211-221. `h/tron/simd/fp32.hpp` at f454423b09, Note [Fixed-order reduce_sum] and `reduce_sum(fp32x16)`, lines 678-695.
- **[R18]** PR #5232 "simd: Reduce fp32x16 sums in a fixed order": https://github.com/positron-ai/tron/pull/5232 . Merged 2026-11-21T18:15:29Z. `git log --format='%h %cs %s' 72308ec90c..f454423b09 -- h/tron/simd/fp32.hpp` prints `7eddde7895 2026-11-21 simd: Reduce fp32x16 sums in a fixed order (#5232)`.
- **[R19]** `git -C /home/jhan/workspace/tron log --format='%h %cs %s' 72308ec90c..f454423b09 -- h/tron/kernels/dotter.hpp h/tron/kernels/dotter2.hpp h/tron/kernels/amx_attn_iface.hpp src/tron/kernels/amx_attn.cpp t/t_amx_numerics.cpp` prints nothing. Last commits on main: `dotter.hpp` 8d64eeed81 (2026-09-30), `amx_attn.cpp` 654e3ceac0 (2026-10-07), `amx_attn_iface.hpp` and `t_amx_numerics.cpp` 72083ab161 (2026-10-07). Main has 457 commits after 72308ec90c and 283 after 6198824246.
- **[R20]** `git merge-base --is-ancestor`: f681622f24 (#4366) is an ancestor of 72308ec90c and of 6198824246. 83d8f2fbe7 (#4722) is an ancestor of 6198824246 and not of 72308ec90c. 10e54cd34a (#4975) is an ancestor of neither. All three are ancestors of f454423b09. Commit dates: 72308ec90c 2026-10-10 01:26 UTC, 6198824246 2026-10-16 18:11 UTC.
- **[R21]** `gh pr view N --repo positron-ai/tron --json state,isDraft,mergedAt,closedAt,baseRefName,headRefOid,updatedAt` for N in 3879, 4424, 4956, 4957, 4958, 4959, 5015, 5022, read 2026-11-23. Values are in the table of section 4.
- **[R22]** At f454423b09: `git grep -I -c TRON_K_VNNI f454423b09` matches no file. `git grep -n qk_group f454423b09` matches nothing. `git ls-tree -r --name-only f454423b09 | grep -i k_vnni` matches nothing. `CMakeLists.txt:46` holds the `TRON_AMX_DISPATCH` option (OFF). `CMakePresets.json:57-70` holds the `deb` preset with `"TRON_AMX_DISPATCH": "ON"` on line 68. At 6b081187e1: `CMakeLists.txt:47` `option(TRON_K_VNNI ... OFF)` and `CMakePresets.json:69` `"TRON_K_VNNI": "ON"`. PR #4505 (deb preset, AMX on) merged 2026-09-22T21:08:26Z.
- **[R23]** The 2026-10-16 report: `/home/jhan/workspace/intel-AMX/token-divergence-4444/token-divergence-issue4444-report.html` (file date 2026-10-16). Sections used: 2 (pairs), 3 (cause 1, kernel test lines T1, T2, T3), 4 (cause 2), 6 (logits and flips), 7.2 (prompt 8192), 7.3 (near ties), 9 (verdict). Its scripts and records: `/home/jhan/workspace/intel-AMX/exec/td-20261016/` and `/home/jhan/workspace/intel-AMX/exec/results/td-20261016/`.
- **[R24]** Per-step files: `/home/jhan/workspace/intel-AMX/exec/results/td-20261016/steps-*.json` (prompt 1024), `.../td2-20261016/steps-*.json` (prompt 8192), `.../glimext-20261018/margin/steps-base-vs-head.json` (Glimmer). Command: `python3 -I -c "import json,glob,statistics as s; [print(f, len(t), s.mean(t), max(t)) for f in sorted(glob.glob('/home/jhan/workspace/intel-AMX/exec/results/td-20261016/steps-*.json')) for t in [[x['tvd'] for x in json.load(open(f))['steps'] if x.get('tvd') is not None]]]"`. Output for prompt 1024 (mean, largest): baseoff-vs-base 0.00585, 0.03163. new-vs-trunc 0.00598, 0.05705. newoff-vs-trunc 0.00533, 0.04864. baseoff-vs-newoff 0.00526, 0.03675. clean-vs-baseoff 0, 0. base-vs-new 0.00587, 0.05588. new-vs-newoff 0.00596, 0.05480. For prompt 8192: new-vs-newoff 0.0000081, 0.00173. base-vs-new 0.0000091, 0.00225. For Glimmer: 0.0182279, 0.49160. The TVD formula is line 128 of `/home/jhan/workspace/intel-AMX/exec/dd/dd_logits_step.py`: `0.5 * np.abs(softmax(lo) - softmax(ln)).sum()`. Flip steps are the `flip_steps` field of each file.
- **[R25]** `h/tron/kernels/host_matvec.hpp` at f454423b09, lines 159-163 (`result[m + j] = reduce_sum(a[j] + c[j]);`). `git grep -n row_dot f454423b09 -- h src t` matches only `host_matvec.hpp` and `t/t_host_matvec.cpp`. `config/models.yaml` at f454423b09: `moe_router: cpu` on lines 643, 672, 883, 899 (entries `ingested_gpt_oss_20b`, `ingested_gpt_oss_120b`, `gemma_4_a4b_it`, `qwen_3_30b_moe`). The Glimmer entries start at line 684.
- **[R26]** `h/tron/simd/bf16.hpp` at f454423b09, lines 55-71 (`_mm256_cvtneps_pbh`, `_mm512_cvtneps_pbh`, `_mm512_cvtne2ps_pbh`). The `append_v_row` change is the `h/tron/tensor/v_vnni.hpp` hunk of `gh pr diff 4366`: "bf16 input keeps its bits; fp16 and float input are rounded to bf16".
- **[R27]** `git ls-tree -r --name-only <commit> | grep qwen3_5` finds no `t/t_generate_ingest_1_qwen3_5_4b_fpga.cpp` at f454423b09, 72e1191804, 127a662083, 69cc70fae0. The file exists at cb9a5dc070 (`origin/rbjarnason/qwen35-33-e2e-goldens`, head of draft PR #3215 "Add the Qwen3.5 4B FPGA golden test"). Its two cases are "Qwen3.5-4B FPGA free-runs unambiguous CPU HuggingFace references" (line 135) and "Qwen3.5-4B FPGA tracks CPU HuggingFace reference logits" (line 167). Constants on lines 39-50: `kReferenceTopK = 10`, `kReferenceUltraLowMarginTopK = 32`, `kReferenceStrictTop1Margin = 3.0f`, `kReferenceUltraLowMargin = 0.25f`.
- **[R28]** Golden-logit tests at f454423b09: `t/t_generate_ingest_1_llama.cpp` lines 19-50 (`--max-tokens 21`, `golden_tvd = 0.05`), `t/t_generate_ingest_1_muse_glimmer.cpp` lines 28-46 (`--max-tokens 9`, `golden_tvd = 0.18`), `t/t_generate_ingest_1_gpt_oss_20b.cpp` line 55 (`golden_tvd = 0.05`). Helpers `check_golden_logits` and `compute_tvds`: `t/testutil.hpp` lines 214-232. `git grep -l -i -E "tvd|total variation" f454423b09 -- t` lists no file for qwen-3-4b.
- **[R29]** Note [GatedDeltaNet BF16 rounding points]: `h/tron/kernels/gated_delta_net.hpp` lines 21-50 at f454423b09 and lines 22-53 at 69cc70fae0 (quotes from lines 39 and 42-43).
- **[R30]** `src/tron/kernels/amx_gdn.cpp` at 882e5322f1, lines 181-186 (`bf16_bits`: `_mm512_srli_epi32(_mm512_castps_si512(values), BF16_SHIFT_16)`) and lines 259 and 262 (key and query packing).
- **[R31]** `gh api "repos/positron-ai/tron/issues/4444/timeline?per_page=100"` and the same for 5433, read 2026-11-23.
- **[R32]** `t/t_amx_numerics.cpp` at f454423b09, lines 1-11: the admissible differences are "(a) fp32 accumulation order" and "(b) for PV, the weight rounding mode - AVX scaled_v truncates fp32->bf16, AMX rounds to nearest even".
