# Facts: the AMX block kernel for GDN when the normalized key and query stop being bf16 values

Written 2026-11-23. Code references are at commit 882e5322f1 of the worktree
`/home/jhan/workspace/ai-runs/tron-gdn-amx`, unless a reference names another commit.
Nothing was built and no kernel was run for this report.

## Short version

Today the AMX block kernel for GDN keeps only the upper 16 bits of each normalized key and query value, so it needs those values to be bf16 values.
Issue #5433 removes the rounding that makes them bf16 values, and the kernel as built would then cut them off toward zero with no error and no refusal.
Rounding them, in the kernel or in the layer, keeps the 18.5 tile products but makes about half of the bf16 output words differ from the chain kernel (est., float64 model), and splitting them into two or three pieces costs 38.0 or 58.5 tile products (derived), with only three pieces exact.

## Words used here

- **tron**: the inference program under test. **GDN**: GatedDeltaNet, the recurrent layer type of the model Qwen3.5 4B.
- **AMX**: Intel Advanced Matrix Extensions. A **tile** is an AMX register of 16 rows by 64 bytes.
- **tile product**: one execution of the AMX instruction TDPBF16PS (`_tile_dpbf16ps` in the code). It multiplies two tiles of bf16 values and adds the products into a tile of FP32 values.
- **bf16**: a 16-bit floating-point format with 8 significant bits. **FP32** has 24 significant bits. A **bf16 step** is the distance between two neighbouring bf16 values.
- **K, Q**: the normalized keys and queries of one key head. Each token has one row of 128 values.
- **S0**: the state matrix of one value head at the start of a block, 128 by 128 FP32 values. **Delta**: the 32 correction rows of a block. **w.Delta**: Delta with each row scaled by the decay up to the end of the block.
- **token kernel** (`gdn_recurrence`), **chain kernel** (`gdn_recurrence_chain`), **block kernel** (`pack_key_head` plus `advance_value_head`): three routines for the GDN recurrence. The first takes one token. The second takes a run of tokens and gives the bits of the first. The third takes 32 tokens at once with AMX.
- **window, block**: the executor entry `advance()` cuts a chain into windows of at most 32 tokens. A full window of 32 tokens is a block.
- **piece**: one of the bf16 values that an FP32 value is split into. The sum of the pieces is the value.
- **GDN step**: the work of one token of one key head. One key head serves 2 value heads.
- **TTFT**: time to first token.
- **arms** of the campaign of 2026-11-22: `base` (counters only), `p0` (chain kernel, kill switch set), `a0` (chain kernel, GDN switch set), `a` (block kernel), `b` and `ab` (the same two with the AMX attention kernels).
- **relative L2**: the L2 norm of a difference divided by the L2 norm of the reference. **RMS**: root of the mean square.
- **est.**: an estimate. **derived**: a count or bound that follows from the code by arithmetic, with no run. **model**: a float64 computation of the recurrence in Python that ran for this report. It is not the kernel.
- **Part 0, Part A**: Part 0 is the chain kernel. Part A is the block kernel. Both are in commit 775bba7661.

## 1. Tile products today

### Where the kernel assumes bf16 values

- The kernel reads K and Q at three places only. All three are in `pack_key_head` [R1].
- Each place keeps the upper 16 bits of the FP32 bit pattern. No place rounds [R1].
- The interface states the assumption in words: the key row "holds KEY_DIM_128 values that are representable in bf16" [R2].
- No assertion and no refusal rule checks the assumption [R1].
- The value, the decay and beta are read as FP32 values in AVX-512 code. They carry no bf16 assumption [R3].

So an unrounded K or Q is truncated toward zero, and the kernel reports nothing.

### Count per stage

One call of `pack_key_head` serves one key head and one block. One call of `advance_value_head` serves one value head and one block [R4].

| Stage | Product | Loop bounds | Tile products | Row-major operand | Second operand |
|---|---|---|---|---|---|
| 1 | K S0 and Q S0 | 8 value groups x 4 key steps x 12 | 384 per value head per block | K and Q, 1 piece (already bf16) | S0, 3 pieces |
| 2 | K K^T and Q K^T | 2 token tiles x 4 key steps x 4 | 32 per key head per block | K and Q, 1 piece (already bf16) | K^T, 1 piece (already bf16) |
| 3 | corrections and outputs | AVX-512 only | 0 | none | none |
| 4 | K^T (w.Delta) | 8 value groups x 2 parts x 12 | 192 per value head per block | K^T, 1 piece (already bf16) | w.Delta, 3 pieces |

Sources of the loop bounds: stage 1 [R5], stage 2 [R6], stage 3 [R7], stage 4 [R8], constants [R9].

- The 12 of stage 1 is 4 accumulator tiles times 3 pieces of S0.
- The 12 of stage 4 is 4 accumulator tiles times 3 pieces of w.Delta.
- The file holds 28 `_tile_dpbf16ps` calls: 4 in stage 2, 12 in stage 1 and 12 in stage 4 [R10].

### Total

- Per value head per block: 384 + 192 + 32 / 2 = 592 tile products. The 32 of stage 2 are shared by the 2 value heads of a key head [R11].
- Per value head per token: 592 / 32 = **18.5**. This is 12 (stage 1) + 0.5 (stage 2) + 6 (stage 4).
- Per GDN step (2 value heads): 37.

The design text says 18.5 tile products per value head per token [R12]. **The code confirms it.**

One small difference from the design table: the design counts 3.5 tile loads per token for stage 4. The code has 2.75, because it loads the three piece tiles once per value group and not once per part [R8]. This changes no tile-product count.

## 2. Options when K and Q are FP32 values with 24 significant bits

### Which change makes this happen

- At our base, `normalize_gdn` rounds at seven points. The last one rounds the normalized product, and it is the one that makes K and Q bf16 values [R13].
- Issue #5433 says that six of the seven "(after each normalization step)" are removed "whatever the measurement says about the other eight" [R14]. The seventh is the rounding of the input.
- So the rounding of the normalized product is one of the six. This is a reading of the issue text and of the list in PR #5571 [R14][R15].
- The decision rule of the issue (comment of 2026-11-22) has four cases. Cases 1 to 3 all remove the six. Case 4 leaves the decision open [R14].
- At the head of PR #5571 (69cc70fae0) `normalize_gdn` rounds nowhere. It returns `result.chunk(chunk) * inverse_norm` [R15].
- Not verified: the build with only the six removed. No branch with such a name was found in the local clone. Command: `git -C ~/workspace/tron branch -r | grep -i -E "six|rounding|fp32-intermediates"`.

### Size of one rounding of K and Q

- A value in [2^e, 2^(e+1)) has a bf16 step of 2^(e-7). Round to nearest moves it by at most half a step, 2^(e-8).
- Relative to the value this is 2^-8 (0.39 %) at the bottom of the range and 2^-9 (0.20 %) at the top.
- **Correction to the task text: the bound for round to nearest is 2^-8, not 2^-9.** PR #5571 states the same bound: "rounding moves a normal value by at most 2^-8 of itself" [R15].
- Truncation, which the kernel does today, moves a value by up to a full step: up to 2^-7 (0.78 %). It always moves toward zero.

Computed on 20,000 random unit vectors of 128 values (script A, no tron code):

| Rule | Largest relative error per coordinate | RMS relative error per coordinate | Relative L2 error of a key vector, mean | Change of the key length, mean |
|---|---|---|---|---|
| Round to nearest even (O1, O3) | 3.89e-3 (2^-8.0) | 1.66e-3 (2^-9.2) | 1.65e-3 | -0.0002 % |
| Truncation (the kernel as built) | 7.75e-3 (2^-7.0) | 3.31e-3 (2^-8.2) | 3.30e-3 | -0.28 % (range -0.40 to -0.18 %) |
| Two truncating pieces (O2 with 2 pieces) | 3.03e-5 (2^-15.0) | 9.7e-6 (2^-16.7) | not computed | not computed |
| Three truncating pieces (O2 with 3 pieces) | 0 (exact for all 131,072 key values of script C) | 0 | 0 | 0 |

### Option table

Tile-product counts are derived with the arithmetic of section 1. p is the number of bf16 pieces of K and of Q. S0 and w.Delta keep 3 pieces.

- Stage 1: 8 x 4 x 4 x 3 x p = 384 p per value head per block.
- Stage 2: 2 x 4 x 4 x p x p = 32 p^2 per key head per block. Both operands are K or Q.
- Stage 4: 8 x 2 x 4 x 3 x p = 192 p per value head per block.

| Option | Stage 1 per token | Stage 2 per token | Stage 4 per token | Total per value head per token (derived) | Factor against today | Difference of K and Q from the FP32 values |
|---|---|---|---|---|---|---|
| Today (K, Q are bf16 values) | 12 | 0.5 | 6 | 18.5 | 1.00 | none |
| Kernel as built, fed unrounded values | 12 | 0.5 | 6 | 18.5 | 1.00 | up to 2^-7, biased toward zero |
| O1: kernel rounds | 12 | 0.5 | 6 | 18.5 | 1.00 | up to 2^-8 |
| O2 with 2 pieces | 24 | 2.0 | 12 | 38.0 | 2.05 | up to 2^-15 |
| O2 with 3 pieces | 36 | 4.5 | 18 | 58.5 | 3.16 | none (exact from 2^-103 up) |
| O3: layer rounds for the AMX path | 12 | 0.5 | 6 | 18.5 | 1.00 | up to 2^-8 |
| O4: no block kernel | 0 | 0 | 0 | 0 | 0 | none |
| O6: 3 pieces, low piece pairs dropped | 24 | 3.0 | 12 | 39.0 | 2.11 | none in K and Q. Dropped products below 2^-22 each |
| O7: K in 3 pieces, Q rounded | 24 | 3.0 | 18 | 45.0 | 2.43 | K none, Q up to 2^-8 |

### O1: the kernel rounds K and Q itself

- **Code change**: `pack_key_head` only. The helper `bf16_bits` and the store at the transposed keys must round to nearest even in place of the shift [R1].
- tron's own rule for this rounding is round to nearest, ties to even. Its SIMD form is the instruction behind `_mm512_cvtneps_pbh` [R16].
- `amx_gdn.cpp` is already compiled with `-mavx512bf16`, so that intrinsic is available there with no build change [R16].
- The interface comment and Note [AMX GatedDeltaNet block kernel] must change: K and Q are then FP32 inputs that the kernel rounds [R2].
- **Tile products**: 18.5, as today. `advance_value_head` does not change.
- **Numerical meaning**: the block kernel uses rounded K and Q. The chain kernel, the token kernel and the fallback of a refused value head use the unrounded values.
  - Full prefill windows on an AMX machine get the rounding. Decode steps and partial windows do not.
  - The state after the prompt is built from rounded keys. Decode then continues with unrounded keys.
- **Effect on the error band of `t/t_amx_gdn_numerics.cpp`** (est., from the model of script B, not verified by a run):

| Check in the test [R17] | Band | Measured today | O1 against the unrounded chain kernel (est., model) |
|---|---|---|---|
| bf16 output words that differ | at most 0.2 % (`0.002 * compared_words`) | 0.006 to 0.034 % | 47 to 52 % |
| Largest step of an output above 1 % of the RMS output | at most 2 bf16 steps | 1 | 28 to 160 |
| State difference, relative L2 | at most 2e-6 | 5e-8 to 4e-7 | 1.6e-3 to 1.7e-3 |
| Output error against float64 | at most 2 times the chain kernel's | 0.37 to 0.61 times | output relative L2 1.9e-3 to 2.5e-3, against about 2e-7 to 3e-7 for the chain kernel |

  - So with O1 every check of the band case fails if the reference stays the chain kernel on unrounded values. Not verified by a run.
  - The band holds as it is when both kernels get the same rounded values. This is what the test does today: `fill_block` rounds K and Q before both kernels run [R17].
  - The executor-level case "advance with the block kernel stays close to step" runs the real `normalize_gdn`. Its bounds are 1e-5 for the state and 2 % of the output words [R18]. With O1 on unrounded values it would fail too (est.: state 1.6e-3, about half of the words).

### O2: K and Q split into two or three bf16 pieces, like S0

- **Code change**:
  - `scratch_layout`: the arrays `kq`, `kt_rows` and `kt_pairs` get a piece dimension. They hold 16, 8 and 8 KiB today, so each extra piece adds 32,768 bytes to `BLOCK_SCRATCH_BYTES_118144` (derived) [R19].
  - `pack_key_head`: split K and Q with the existing `split()` and store every piece. Stage 2 runs p x p products per accumulator [R1][R6].
  - `advance_value_head`: stages 1 and 4 load the row-major tile once per piece of K or Q and run 3 products for each load [R5][R8].
  - No tile shortage up to 3 pieces (derived): tiles 0 to 3 accumulate, tiles 4 to 6 hold up to three pieces of the second operand, and tile 7 takes the row-major pieces one after the other [R9].
- **Tile products**: 38.0 per value head per token with 2 pieces (2.05 times today). 58.5 with 3 pieces (3.16 times today).
- **Numerical meaning with 3 pieces**: K and Q are exact, so the kernel adds the same real products as the chain kernel in another order. Today's band then applies unchanged. A value below 2^-103 loses the part below 2^-126, as S0 does today [R2].
- **Numerical meaning with 2 pieces**: K and Q are truncated after 16 significant bits.
  - Model (script C, est.): 0.82 to 0.96 % of the bf16 output words differ, and the state differs by 9.6e-6 to 1.1e-5 in relative L2.
  - Both are above the band of the test (0.2 % and 2e-6). Not verified by a run.
  - The design page measured two pieces for the state, not for K: "Two pieces are not enough for the split" [R12].
- **Cost in time (est., from the cost model of the design page, not a timing)** [R12]:

| | Today | O2 with 2 pieces (est.) | O2 with 3 pieces (est.) | Chain kernel (measured) |
|---|---|---|---|---|
| Tile cycles per value head per token (products, loads, stores) | 436 | 807 | 1,194 | none |
| Kernel cycles per value head per token | 972 to 1,286 | 1,343 to 1,657 | 1,730 to 2,044 | none |
| Recurrence per GDN step (us) | 1.03 (measured) | 1.33 to 1.42 | 1.64 to 1.83 | 2.45 |
| GDN step (us) | 2.56 (measured) | 2.86 to 2.95 | 3.17 to 3.36 | 4.01 |
| Share of Part A's step gain over Part 0 that stays | 100 % | 73 to 80 % | 45 to 58 % | 0 % |

  - The estimate scales the measured 1.03 us by the ratio of the model's cycle totals. It leaves out the extra packing work and the larger scratch memory.
  - Upper bound if all of the 1.03 us were tile products: 2.12 us (2 pieces) and 3.26 us (3 pieces) per GDN step. The second is above the chain kernel's 2.45 us.

### O3: the layer keeps one rounding of K and Q for the AMX path

- **It is the same arithmetic as O1 inside a block window**: rounded K and Q, 18.5 tile products, the same differences against unrounded values.
- **Code change**: none in the kernel. The rounding goes after `normalize_gdn` in `gdn_prepare_recurrence_token`, which fills the window that both kernels read [R20].
  - `advance()` knows whether a window takes the block kernel before it prepares the tokens of that window [R20].
  - The window field `scaled_query` must then come from the rounded query, because the chain kernel reads it [R20].
- **What differs from O1**:
  - **Where the contract is written.** O1 hides the rounding inside an AMX source file. O3 puts it in the layer, in the file of Note [GatedDeltaNet BF16 rounding points]. PR #5571 rewrites that note [R13][R15].
  - **What the fallback sees.** With O3 a refused value head runs the chain kernel on the same rounded values. With O1 it runs on unrounded values [R4].
  - **What the tests compare.** With O3 the band case of `t_amx_gdn_numerics.cpp` stays as it is, because it already feeds rounded values to both kernels [R17].
  - **Whether AMX on and AMX off stay comparable.** This depends on when the layer rounds:

| Variant of O3 | AMX on against AMX off | What it breaks |
|---|---|---|
| (i) Round only in windows that take the block kernel | Differ by the rounding in every full prefill window, as in O1 (est. about half of the bf16 output words) | The executor-level band case [R18] |
| (ii) Round in every full window on the 32-token grid, with or without AMX | Differ by today's band only | "advance gives the bytes of step" for runs with a full window [R18]. Prefill and decode then differ by the rounding on every machine |
| (iii) Keep the rounding of the normalized product in `normalize_gdn` for all paths | Differ by today's band only | No test of ours. Not verified for the changed tests of PR #5571. It contradicts the stated plan of issue #5433 for the six roundings [R14] |

  - All three variants are derived from the code. None was built.

### O4: no AMX block kernel for GDN

- **Code change**: drop `amx_gdn.cpp`, `amx_gdn_iface.hpp`, `t_amx_gdn_numerics.cpp`, the block path of the executor and the block counters. The chain kernel stays.
- **Tile products**: 0.
- **Numerical meaning**: every GDN path gives the bits of the token kernel. No error band is needed for GDN.
- **Cost**: the gain of Part A over Part 0 is lost. Section 3 gives it: 6.9 to 12.4 % of the TTFT of the Part 0 run.

### Further options found in the code

- **O5: a refusal rule or an assertion for values that are not bf16 values.**
  - The kernel already refuses a block and leaves the state untouched. The executor then runs the chain kernel for that value head [R4].
  - A check in `pack_key_head` that the low 16 bits of every K and Q value are zero would use the same path. `pack_key_head` returns `void` today, so its signature would change [R2].
  - With unrounded K and Q nearly every block would be refused. The result is then O4 plus the cost of the pack. Its use is as a guard: a rebase onto unrounded values cannot truncate without notice.
- **O4 without a code removal**: `TRON_AMX_GDN_DISABLE=1` turns only this kernel off, and `gdn_block_kernel::off` does the same for tests [R21].
- **O6: three pieces, low piece pairs dropped (derived, not in the code).**
  - Piece i of a value is below 2^(-8(i-1)+1) of the value. A product of piece i with piece j of the other operand is dropped when i + j is above 4.
  - 6 of 9 pairs stay. Each dropped product is below 2^-22 of the product of the two values (derived).
  - Count: 24 + 3 + 12 = 39.0 per value head per token, 2.11 times today. Accuracy not verified.
- **O7: K exact, Q rounded (derived, not in the code).**
  - The state after a block depends on K only. Q enters the outputs only [R2].
  - So a rounded Q changes the outputs of its own token and never the state of the layer.
  - Count with K in 3 pieces and Q in 1 piece: 24 + 3 + 18 = 45.0, 2.43 times today. With K in 2 pieces: 18 + 1.5 + 12 = 31.5, 1.70 times.
- No code in the tree uses the fp16 tile product. Command: `grep -rn -i -E "dpfp16|amx_fp16" src h t` gives no line.

## 3. What our measurements say about the stake

All runs: delphi-3b35, 2026-11-22 UTC, session 2, 3 repetitions per cell and arm. Before every run our 56 CPUs were 0.0 to 0.1 % busy, and the other socket was 42.4 to 42.5 % busy [R22].

### TTFT per cell

Medians of 3 runs, from the results page, section "3. Time to first token" [R22]:

| Users | Prompt (tokens) | Base run (s) | Part 0 (s) | Part 0: fall against base (%) | Part A (s) | Part A: fall against base (%) |
|---|---|---|---|---|---|---|
| 1 | 1,024 | 0.385 | 0.332 | 13.8 | 0.293 | 23.8 |
| 1 | 4,096 | 1.902 | 1.690 | 11.2 | 1.537 | 19.2 |
| 1 | 8,192 | 4.711 | 4.285 | 9.0 | 3.990 | 15.3 |
| 8 | 1,024 | 2.903 | 2.493 | 14.1 | 2.184 | 24.8 |
| 8 | 4,096 | 14.271 | 12.621 | 11.6 | 11.384 | 20.2 |
| 8 | 8,192 | 35.715 | 32.421 | 9.2 | 29.939 | 16.2 |

Part A against Part 0, computed for this report from the medians in `collected.json` [R23]:

| Users | Prompt (tokens) | Arm `a` against arm `p0` (%) | Seconds saved | Arm `a` against arm `a0`, same build (%) | Arm `ab` against arm `b`, with AMX attention (%) |
|---|---|---|---|---|---|
| 1 | 1,024 | 11.6 | 0.038 | 11.2 | 11.5 |
| 1 | 4,096 | 9.0 | 0.152 | 8.7 | 10.2 |
| 1 | 8,192 | 6.9 | 0.295 | 6.9 | 9.5 |
| 8 | 1,024 | 12.4 | 0.309 | 12.1 | 12.1 |
| 8 | 4,096 | 9.8 | 1.237 | 9.6 | 11.1 |
| 8 | 8,192 | 7.7 | 2.481 | 7.6 | 9.9 |

- The results page gives the same range for the same-build pair: "Fall of the GDN-switch pair 6.9 to 12.1 % of its run with the switch set" [R22].
- The PR body gives means of 3 in place of medians. Its rows for `base`, `p0` and `a` are: 0.385, 0.331 (-13.9), 0.293 (-23.9). 1.903, 1.690 (-11.2), 1.537 (-19.3). 4.707, 4.285 (-9.0), 3.985 (-15.3). 2.901, 2.492 (-14.1), 2.184 (-24.7). 14.266, 12.616 (-11.6), 11.387 (-20.2). 35.717, 32.416 (-9.2), 29.938 (-16.2) [R24].
- Decode is not at stake. The block kernel runs in prefill only, and the GDN kernels change decode by -0.7 to +0.5 %, inside the band [R24].

### GDN step times

- "One GDN step (one token of one key head) takes 6.08 us in `base`, 4.01 us in `p0` and 2.56 us in `a`" [R24]. These are means over the 16 GDN threads in the cell with 1 user, prompt 1,024 [R22].
- The recurrence inside the step, for 2 value heads: 5.95 us (base run, the whole step loop), 2.45 us (chain kernel), 1.03 us (block kernel) [R22].
- Over the 6 cells, arm `a` has a step of 2.53 to 2.56 us and a recurrence of 1.02 to 1.03 us [R23].
- So the recurrence is 40 % of the Part A step (1.03 of 2.56 us, measured).
- "With Part 0 the pass wall fell by 99 to 101 % of the fall of the GDN wall. With Part A it fell by 99 to 101 %." [R22]. So a longer GDN step lengthens the prefill pass by about the same time.

### Share of the tile products in the Part A step

**Insufficient data for a measured stage split.**

- The counters time the block kernel with one pair of time stamps around the whole recurrence of a window. They do not split the stages [R25].
- Keys in `collected.json` that count or time the block kernel [R23][R25]:
  - raw counters: `amx_recurrence_cycles`, `amx_head_tokens`, `amx_blocks`, `amx_fallback_blocks`, `chain_full_block_tokens`
  - values that `collect.py` derives: `recurrence_amx_us`, `step_recurrence_us`, `share_amx`, and the other parts of the step: `step_us`, `step_start_us`, `step_pre_us`, `step_post_us`, `step_write_us`
- The stand-alone bench prints one time per kernel: 476.2 ns per value head per token for the block kernel in the short runs, and 570 to 593 ns in loops of 4 s at 1.89 to 2.10 GHz [R26].
- Task 4 times the attention kernel, not GDN [R26].

Estimate from the cost model of the design page (est., cycle counts, not timings) [R12]:

- Tile work (products, loads and stores) is 443 of 972 to 1,286 cycles: 34 to 46 % of the recurrence (est.).
- The 18.5 tile products alone are 299 cycles at 16.17 cycles each: 23 to 31 % of the recurrence (est.).
- As a share of the Part A step of 2.56 us: tile work 14 to 18 % (est.), tile products alone 9 to 12 % (est.).

The measurement that would give the split: `bench/amx_gdn_bench.cpp` with a time stamp counter read between the stages of the block kernel copy in `bench/gdn_kernels.hpp`, run with `bench/task3.sh` on delphi-3b35 after a load snapshot [R26]. A second way is a build variant of the bench with K in 2 or 3 pieces, which gives the cost of O2 directly.

## 4. The numerics of the block kernel as measured so far

Every row compares the block kernel with a kernel that reads the same K and Q. In all of them K and Q are bf16 values.

| Statement | Value | Source |
|---|---|---|
| bf16 output words that differ from the chain kernel, 8 input families, 128 tokens | 0.006 to 0.034 % | test comment [R17], results page section 9 [R22], raw table [R26] |
| Largest difference of an output above 1 % of the typical size | 1 bf16 step (0 in one family) | same |
| Largest difference of any output | 1 to 2 bf16 steps in 7 families, 16 with a zero start state | results page section 9 [R22] |
| State difference against the chain kernel, relative L2 | 5.2e-8 to 3.7e-7 ("5e-8 to 4e-7" in the test) | same |
| Output error against float64, block kernel over token kernel | 0.37 to 0.61 times | results page section 9 [R22] |
| State error against float64, block kernel over token kernel | 0.48 to 1.30 times | same |
| Output error against float64, absolute | token kernel 2.08e-7 to 3.26e-7, block kernel 7.63e-8 to 1.82e-7 (relative L2) | raw table [R26] |
| Scores at generated token 0, arm `a` against `base` | 319 of 320 token ids in both lists, 73 scores differ, by at most 1 bf16 step | results page "What the scores show" [R22] |
| Generated tokens, prompt 1,024, arm `a` | the same tokens for 185 steps, then another token. 236 of 256 tokens equal | results page [R22], PR body [R24] |
| Margin at the flip | `base` leads by 8 bf16 steps (17.875 against 16.875). Arm `a` scores 16.5 and 16.625 | raw score lines [R27] |
| Drift of the best score before the flip | at most 1 bf16 step in steps 0 to 79, up to 10 bf16 steps later | results page [R22], PR body [R24] |
| Generated tokens, prompt 4,096, arm `a` | identical, 256 of 256 | PR body [R24] |
| Refused blocks in the campaign | 0 | results page section 9 [R22] |
| GDN states after the prompt, arm `a` against `base` | "No measurement compares the GDN states of the two binaries after the prompt" | PR body [R24] |

The bounds that the tests enforce today:

- Kernel level: 0.2 % of the words, 2 bf16 steps, 2e-6 for the state, 2 times and 4 times the float64 errors of the chain kernel [R17].
- Executor level: 1e-5 for the state, 2 % of the output words, largest difference 2 % of the largest output [R18].

### Is today's difference smaller or larger than what O1 would add?

**Smaller, by three to four orders of magnitude.**

| Quantity | Today's block kernel (measured) | One rounding of K and Q (O1 or O3) | Ratio |
|---|---|---|---|
| Size of the cause | FP32 sums in another order. One FP32 rounding is at most 2^-24, about 6e-8 (derived) | 1.66e-3 RMS per coordinate, 3.9e-3 at most (computed, script A) | about 28,000 |
| State difference, relative L2 | 5.2e-8 to 3.7e-7 | 1.6e-3 to 1.7e-3 (est., model, script B) | 4,200 to 33,000 |
| bf16 output words that differ | 0.006 to 0.034 % | 47 to 52 % (est., model, script B) | 1,400 to 8,700 |

- The left column is a measurement of the kernel. The right column is a float64 model of the recurrence with rounded against unrounded K and Q. The model has no AMX code in it.
- Insufficient data for the O1 values from the kernel itself. The experiment of section 5 gives them.
- Insufficient data for what O1 does to generated tokens. Today's much smaller difference already changed a token after 185 steps at prompt 1,024. The measurement is `token-check.sh` and `logit-margin.sh` of the campaign folder, on a build with O1 against a build with the chain kernel, both on a base with unrounded K and Q [R27].
- For scale: the kernel as built, fed unrounded values, would be about twice as far away as O1 (est., model: 72 to 85 % of the words, state 3.3e-3 to 3.7e-3).

## 5. A unit-level experiment without the model

Goal: feed unrounded normalized keys and queries to the block kernel as it is today, report the error against `gdn_recurrence_chain`, and report the same for O1. Not run for this report.

Key fact that keeps the change small: **O1 needs no kernel change in the experiment.** `bf16_bits` returns the bf16 word of a value that is already a bf16 value [R1]. So today's kernel, fed K and Q rounded by the test, computes bit for bit what a kernel that rounds by itself would compute.

### Way A: a new case in `t/t_amx_gdn_numerics.cpp` (the tron code itself)

1. Give `fill_block` a flag. With the flag off it stores the normalized key and query without `round_to_bf16`, and it computes `scaled_query` from the unrounded query [R17].
2. Copy the loop of the band case into a new hidden case, for example with the tag `[.amx_gdn_rounding_experiment]`. The leading dot keeps the case out of the default run. Keep `families`, `MASTER_SEED_20261121` and `BLOCKS_4` [R17].
3. Per block, fill `window` with unrounded K and Q. Then make two copies of it, each with its own state:
   - arm "today": the plain copy. The kernel truncates.
   - arm "O1": the copy with `normalized_key` and `normalized_query` passed through `round_to_bf16`.
4. References, both on the unrounded `window`: `tron::gdn_recurrence_chain(*window, BLOCK_TOKENS_32, chain_state->values)` and `run_float64` [R17].
5. Run each arm with `run_block_kernel(*scratch, *copy, *state)` [R17].
6. Report per family and arm, with `WARN` or `printf`, and with no `CHECK`: the share of differing bf16 words (`bf16_word`), the largest step of a large output, the state difference in relative L2, and the errors against float64 (`relative_l2`) [R17].
   - The line `REQUIRE((chain_word & 0x8000) == (block_word & 0x8000))` must become a count. A sign can differ when the differences are this large.
7. Control arm: round K, Q and `scaled_query` in `window` itself. This is today's test. It must stay inside today's band of 0.2 %. The test comment gives 0.006 to 0.034 % [R17].
8. Build and run on delphi-3b35, because the case needs AMX. The test binary is `t_amx_numerics`, built with `TRON_AMX_DISPATCH=ON` [R28]. Run line, after the recipe of the campaign: `SYSTEM_CONFIG="--instance 1,2" taskset -c 96-143 ./gen/t_amx_numerics "[amx_gdn_rounding_experiment]"` [R28]. The band case takes 0.2 s [R28].

### Way B: the stand-alone bench (no tron build)

- Program: `bench/amx_gdn_bench.cpp` with `bench/gdn_kernels.hpp` in the campaign folder. Its header says "NOT tron code". It holds its own copy of the three kernels, in a file dated 2026-11-21 [R26].
- Not verified: whether that copy equals the tron kernel at 882e5322f1 in every line. So Way A is the result to quote, and Way B is the fast first look.
- Its block kernel packs K and Q with the same shift as the tron kernel [R26].
- Its table already prints what is needed: the share of differing bf16 output words, the largest step, the state difference in relative L2 against the token kernel, and the errors against float64 [R26].
- Smallest change:
  - In `make_case`, leave out `bf16_round` for `c.kn` and `c.qn` under a macro, for example `-DUNROUNDED_KQ` [R26].
  - For the O1 arm, round `w.kn` and `w.qn` with `bf16_round` in `fill_window` when the window goes to the block kernel [R26].
- Build line from the file header: `clang++-19 -O3 -std=c++20 -march=native -mamx-tile -mamx-bf16 -o amx_gdn_bench amx_gdn_bench.cpp`. Run line: `taskset -c CPU ./amx_gdn_bench --cpu CPU` [R26].
- Work on a copy under `~/workspace/smaller-tasks/numeric-rounding/`. The campaign folder is the record of the measured results.
- The same bench is the place to time O2: it prints ns per value head per token.

### Expected result (est., model, scripts B and C)

| Arm against the unrounded chain kernel | bf16 output words that differ | State difference, relative L2 |
|---|---|---|
| Control (both rounded), measured today | 0.006 to 0.034 % | 5e-8 to 4e-7 |
| O1 (rounded K and Q in the block kernel) | 47 to 52 % | 1.6e-3 to 1.7e-3 |
| Today's kernel on unrounded K and Q (truncation) | 72 to 85 % | 3.3e-3 to 3.7e-3 |
| O2 with 2 pieces | 0.82 to 0.96 % | 9.6e-6 to 1.1e-5 |

## 6. Not verified

- No run of the block kernel on unrounded K and Q exists. Every O1, O2 and truncation value above is a float64 model or a derived bound. The experiment of section 5 settles it.
- The time of O2. The values in section 2 scale a cost model. A bench variant with pieces of K and Q settles it.
- The stage split of the block kernel. See section 3.
- Which rounding stays in the build with six roundings removed. The reading here is that the input rounding stays and the product rounding goes. The six-out commit, when it is pushed, settles it: `git show <commit>:h/tron/kernels/gated_delta_net.hpp`.
- Whether the executor-level band case fails after a rebase onto unrounded values. Est. yes (state 3.3e-3 against a bound of 1e-5). A run of `t_gated_delta_net` on such a rebase settles it.
- The effect of O1 or O3 on generated tokens and on the next-token distribution. See section 4.

## References

- **[R1]** `src/tron/kernels/amx_gdn.cpp`.
  - :181-186 `bf16_bits`: "The upper 16 bits of each FP32 lane: the bf16 bit patterns of 16 values that are representable in bf16." Body: `_mm512_cvtepi32_epi16(_mm512_srli_epi32(_mm512_castps_si512(values), BF16_SHIFT_16))`.
  - :252-281 `pack_key_head`: `bf16_bits(_mm512_load_ps(key + first))` at :259, the same for the query at :262, and `_mm512_cvtepi32_epi16(_mm512_srli_epi32(rows[i], BF16_SHIFT_16))` at :278 for the transposed keys.
  - Command: `grep -n -E "normalized_key|normalized_query|scaled_query" src/tron/kernels/amx_gdn.cpp` gives lines 255, 256 and 272 only.
  - :224-231 `split`, the rule for three truncating pieces.
- **[R2]** `h/tron/kernels/amx_gdn_iface.hpp`.
  - :47-53 "TDPBF16PS takes bf16 inputs. K and Q hold bf16 values already. S0 and w . Delta are FP32, and each of their values is split into three bf16 pieces whose sum is the value."
  - :129-131 "Token t's normalized key starts at normalized_key + t * key_stride and holds KEY_DIM_128 values that are representable in bf16. normalized_query holds the query in the same way, without the query scale."
  - :32-38 the block form: `S_B = g_(B-1) S0 + K^T (w_(B-1) . Delta)` has no q.
  - :76-85 the refusal rules. :149 `void pack_key_head(...)`.
- **[R3]** `src/tron/kernels/amx_gdn.cpp` :412 decay, :447-448 beta (`_mm512_set1_ps`), :472 value (`_mm512_load_ps`).
- **[R4]** `h/tron/models/gdn_rolling_executor.hpp` :716 `pack_key_head` once per key head, :717-722 `advance_value_head` per value head, :723-726 a refused head takes `gdn_recurrence_chain_head`.
- **[R5]** Stage 1: `amx_gdn.cpp` :354 `value_group < VALUE_GROUPS_8`, :371 `step < KEY_STEPS_4`, 12 `_tile_dpbf16ps` at :377-391.
- **[R6]** Stage 2: `amx_gdn.cpp` :306 `token_tile < TOKEN_TILES_2`, :311 `step < KEY_STEPS_4`, 4 `_tile_dpbf16ps` at :315, :317, :319, :321.
- **[R7]** Stage 3: `amx_gdn.cpp` :404-490, AVX-512 only.
- **[R8]** Stage 4: `amx_gdn.cpp` :495 `value_group < VALUE_GROUPS_8`, :508-510 three piece loads per value group, :512 `part < STATE_PARTS_2`, 12 `_tile_dpbf16ps` at :520-537.
- **[R9]** `amx_gdn.cpp` :30-45 the tile map, :53 `KEY_STEPS_4`, :55 `VALUE_GROUPS_8`, :58 `TOKEN_TILES_2`, :60 `N_PIECES_3`, :62 `STATE_PARTS_2`.
- **[R10]** Command: `grep -c "_tile_dpbf16ps" src/tron/kernels/amx_gdn.cpp` gives 28.
- **[R11]** Two value heads per key head: `t/t_amx_gdn_numerics.cpp` :35-36 "One key head with two value heads, the grouping of the Qwen3.5 layers". Generated plugin `/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/plugin/qwen_3p5_4b.hpp` :42 `gdn_geometry{.n_key_heads = 16, .n_value_heads = 32, .key_head_dim = 128, .value_head_dim = 128, ...}`.
- **[R12]** Design page `/home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html`.
  - Section 5.3: "The block kernel needs 18.5 tile products and about 680 AVX-512 operations per value head per token (est. count)."
  - Section 5.3, cost table: tile product 1 = 269 cycles, tile product 2 = 15, tile product 3 = 159, AVX-512 work 340 to 417, data movement 189 to 426, total 972 to 1,286 cycles per value head per token (all est.). Unit costs: "16.17 cycles per tile product", "8.38 cycles per tile load", "16.1 cycles per tile store".
  - Section 5.4: "Two pieces are not enough for the split. In the three checks their state error against float64 is 7.5e-8 to 1.6e-5. That is 5 to 227 times the error of today's kernel".
- **[R13]** `h/tron/kernels/gated_delta_net.hpp` :179-196 `normalize_gdn`. The seven roundings are at :184, :186, :189, :190, :191, :192 and :194. Line 194: `result.store_chunk(chunk, round_chunk_to<bf16>(result.chunk(chunk) * inverse_norm));`. Note [GatedDeltaNet BF16 rounding points] is at :24-44.
- **[R14]** Issue #5433, https://github.com/positron-ai/tron/issues/5433, read 2026-11-23.
  - Body: "Six of the seven (after each normalization step) follow Transformers 5.15.1, which normalizes in BF16; 5.17 and later normalize in float32 ... They come out in this follow-up whatever the measurement says about the other eight."
  - Comment of 2026-11-22T18:38:17Z: "1. The TVD test reads not little: the eight stay and #5571 shrinks to the six. 2. Every speed test reads no gain: #5571 shrinks to the six. 3. ... #5571 keeps the fourteen. 4. Anything else: I decide from the results, and #5571 does not change before that."
- **[R15]** PR #5571, https://github.com/positron-ai/tron/pull/5571, draft, head 69cc70fae0.
  - Description: "`normalize_gdn` stops rounding at its seven points (input, each square, their sum, epsilon, sum with epsilon, reciprocal root, product)" and "rounding moves a normal value by at most 2^-8 of itself".
  - `git -C ~/workspace/tron show 69cc70fae0:h/tron/kernels/gated_delta_net.hpp` :200-216: `fp32s const values = input.chunk(chunk);` at :205 and `result.store_chunk(chunk, result.chunk(chunk) * inverse_norm);` at :214.
- **[R16]** Rounding rule and tools.
  - `h/common/numerics/bf16.hpp` :104-116 Note [BF16 rounding on FP32 bits]: "Other finite values round to nearest, ties to even". Zero and subnormal inputs become a zero of their sign.
  - `h/tron/simd/bf16.hpp` :61-64 `fp32s_to_bf16s` uses `_mm512_cvtneps_pbh`. `h/tron/simd/auto.hpp` :118-122 `round_chunk_to`.
  - `src/tron/CMakeLists.txt` :221-223: the options of `amx_attn.cpp` and `amx_gdn.cpp` include `-mavx512bf16`.
- **[R17]** `t/t_amx_gdn_numerics.cpp`.
  - :58-68 `round_to_bf16`, `bf16_word`. :73-105 `fill_block`, which rounds K and Q at :89-92 and computes `scaled_query` at :93. :107-119 `block_of`. :122-135 `run_block_kernel`. :139-167 `run_float64`. :169-177 `relative_l2`.
  - :191-200 the 8 families. :208 `MASTER_SEED_20261121`. :226-258 the loop over 4 blocks. :229 the chain kernel call. :250 the sign `REQUIRE`.
  - :260-262 "Measured on a Xeon 6962P: 0.006 to 0.034 % of the words differ, an output above 1 % of the typical size differs by one bf16 increment, and the matrices differ by 5e-8 to 4e-7 in relative L2 norm."
  - The band: :263-264 `CHECK(static_cast<double>(differing_words) <= 0.002 * static_cast<double>(compared_words));`, :265 `CHECK(largest_step_of_large_outputs <= 2);`, :274 `CHECK(std::sqrt(state_error) <= 2e-6 * std::sqrt(state_norm));`, :279 `CHECK(block_output_error <= 2.0 * chain_output_error + 1e-9);`, :284 `CHECK(block_state_error <= 4.0 * chain_state_error + 1e-9);`.
- **[R18]** `t/t_gated_delta_net.cpp` :2863-2910 "GatedDeltaNet advance with the block kernel stays close to step": :2895 `CHECK(std::sqrt(state_error) <= 1e-5 * std::sqrt(state_norm));`, :2908 `CHECK(differing_outputs * 50 <= result.stepped_output.size());`, :2909 `CHECK(largest_difference <= 0.02 * largest_output);`. The equal-bytes cases are at :2840-2861.
- **[R19]** `amx_gdn.cpp` :105-139 `scratch_layout`: `kq[KQ_ROWS_64][KEY_DIM_128]` (16 KiB), `kt_rows[KEY_DIM_128][BLOCK_TOKENS_32]` (8 KiB), `kt_pairs[...]` (8 KiB), all `uint16_t`. `amx_gdn_iface.hpp` :122 `BLOCK_SCRATCH_BYTES_118144`.
- **[R20]** Window preparation.
  - `h/tron/kernels/gated_delta_net.hpp` :377-425 `gdn_prepare_recurrence_token`: `normalize_gdn` at :400-403, the three stores at :406-413, with `scaled_query` = normalized query times the scale at :412-413.
  - :582-583 the chain kernel reads `window.normalized_key` and `window.scaled_query`.
  - `h/tron/models/gdn_rolling_executor.hpp` :704-707 the block kernel reads `window.normalized_key` and `window.normalized_query`. :538 `bool const block_window = use_block_kernel && full_window;` comes before the prepare loop at :541-545. :655-675 `prepare_window_token`.
- **[R21]** `amx_gdn.cpp` :148-155 `TRON_AMX_GDN_DISABLE`. `gdn_rolling_executor.hpp` :87-97 `enum class gdn_block_kernel { off, when_available }`.
- **[R22]** Results page `/home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html`: sections "2. How it was measured" (load table), "3. Time to first token" (table), "6. Measurement against the prediction" (pass rules, "Where the GDN step time goes", "From the GDN step to the pass"), "9. Numerics and tests" (family table, "Generated tokens", "What the scores show").
- **[R23]** `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/collected.json`: `cells[<cell>][<arm>]["ttft_max_s"]["median"]` and `cells[<cell>][<arm>]["gdn_prompt_or_mixed"][<key>]["median"]`. The six cells are `q35-tp4-{1u,8u}-p{1024,4096,8192}`.
- **[R24]** PR body `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/pr-body.md` (the task named it under `GDN/exec/`, which does not exist): :83 and :95-97 token identity, :107-114 the TTFT table, :119 the GDN step times, :136 decode, :142 "No measurement compares the GDN states of the two binaries after the prompt."
- **[R25]** Counters: `h/tron/models/gdn_stats.hpp` :183-206 the tally fields, :541 the key `"{}_recurrence_cycles"`. `gdn_rolling_executor.hpp` :540-567: the stamps `prepared_cycles` (:546) and `advanced_cycles` (:553) surround the whole call of `advance_window_with_block_kernel`.
- **[R26]** Stand-alone bench, sources in `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/bench/`, results in `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/bench/`.
  - `amx_gdn_bench.cpp` :1-8 header with the build and run lines, :44-50 `bf16_round`, :70-104 `make_case` (rounds at :91-92), :106-118 `fill_window`, :168-193 `run_windows`, :202-232 `compare`, :434-461 the table.
  - `gdn_kernels.hpp` :223-226 `fp32_to_bf16_bits` (the same shift), :275-281 its use in `block_pack_key_head`.
  - `task3-table-cpu140-run1.txt`: the family table and "block kernel (Part A) 476.2 = 5.39x vs today, 2.66x vs the chain kernel". `task3-clock-cpu140.txt`: `block-1 | freq_khz_median 1900019 ... ns_per_token_per_value_head 591.03`. `task3.sh` passes `${DEFS:-}` and `TAG` to the build.
  - `task4_attn256.cpp` and `task4-*.txt` are the attention kernel.
- **[R27]** `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/tokens/logits-summary-p1024-l190.txt` :186 "arm base generated 185: best 6351 17.875, second 198 16.875, margin 1 = 8 bf16 steps" and :376 "arm a generated 185: best 198 16.625, second 6351 16.5, margin 0.125 = 1 bf16 steps". Scripts: `token-check.sh`, `logit-margin.sh`, `logit_summary.py` in `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/`.
- **[R28]** `t/CMakeLists.txt` :690-695 `add_catch_test(NAME t_amx_numerics FILES t_amx_numerics.cpp t_amx_gdn_numerics.cpp ...)`. Run recipe: `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/unit-tests.sh`. Build recipe: `build.sh` in the same folder. Timing of the band case: `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/unit/pab__t_amx_numerics__none.txt` :37-38 (06:30:03.416 to 06:30:03.628).

## Appendix: the scripts that ran for this report

All three are plain Python with numpy. They ran on the agent server with one thread. They call no tron code.
The scripts print bare numbers. The output blocks below show the same numbers with labels added by hand.

### Script A: size of one rounding of a unit key vector

```python
import numpy as np
rng=np.random.default_rng(20261123)
def rne_bf16(x):   # round to nearest even, the rule of h/common/numerics/bf16.hpp:91-96
    b=x.astype(np.float32).view(np.uint32).astype(np.uint64)
    return ((((b+0x7fff+((b>>16)&1))>>16)<<16).astype(np.uint32)).view(np.float32)
def trunc_bf16(x): # what bf16_bits() of amx_gdn.cpp does
    return (x.astype(np.float32).view(np.uint32)&np.uint32(0xffff0000)).view(np.float32)
k=rng.standard_normal((20000,128)); k/=np.linalg.norm(k,axis=1,keepdims=True); k=k.astype(np.float32)
for name,f in (("round to nearest even",rne_bf16),("truncation",trunc_bf16)):
    r=f(k).astype(np.float64); kk=k.astype(np.float64); rel=np.abs(r-kk)/np.abs(kk)
    vec=np.linalg.norm(r-kk,axis=1)/np.linalg.norm(kk,axis=1); n=np.linalg.norm(r,axis=1)/np.linalg.norm(kk,axis=1)-1
    print(name,rel.max(),np.sqrt((rel**2).mean()),vec.mean(),n.mean(),n.min(),n.max())
```

Output:

```
round to nearest even: per coordinate max 3.891e-03 (2^-8.01), rms 1.659e-03 (2^-9.24); key vector relative L2 mean 1.651e-03; key length change mean -1.837e-06
truncation:            per coordinate max 7.752e-03 (2^-7.01), rms 3.311e-03 (2^-8.24); key vector relative L2 mean 3.295e-03; key length change mean -2.806e-03, min -3.956e-03, max -1.805e-03
```

### Script B: the recurrence with rounded or truncated K and Q against unrounded K and Q

The recurrence is the algebra of `run_float64` (`t/t_amx_gdn_numerics.cpp` :139-167) in float64. The inputs are drawn like `fill_block` (:73-105): 4 blocks of 32 tokens, 1 key head, 2 value heads, the 8 families of the test. The random generator is numpy's, so the values are not those of the test.

```python
import numpy as np
KD=VD=128; VH=2; T=128
def rne(x):
    b=np.asarray(x,dtype=np.float32).view(np.uint32).astype(np.uint64)
    return ((((b+0x7fff+((b>>16)&1))>>16)<<16).astype(np.uint32)).view(np.float32)
def trunc(x): return (np.asarray(x,dtype=np.float32).view(np.uint32)&np.uint32(0xffff0000)).view(np.float32)
def word(x): return (rne(x).view(np.uint32)>>16).astype(np.int64)
fam=[("decay 0.90-1.00",0.9,1.0,0.02,1.0),("decay 0.999-1.00",0.999,1.0,0.5,1.0),("decay 0.50-1.00",0.5,1.0,0.02,1.0),
     ("decay 0.01-0.30",0.01,0.3,1.0,1.0),("decay 0.001-0.05",0.001,0.05,1.0,1.0),("zero start",0.9,1.0,0.0,1.0),
     ("large values",0.9,1.0,30.0,30.0),("small values",0.9,1.0,1e-20,1e-20)]
scale=np.float32(1.0/np.sqrt(KD))
def run(K,Q,V,D,Bt,S0):
    S=S0.astype(np.float64).copy(); O=np.zeros((T,VH,VD))
    K=np.asarray(K,dtype=np.float64); QS=(np.asarray(Q,dtype=np.float32)*scale).astype(np.float64)
    for t in range(T):
        Sd=S*D[t][:,None,None]; rem=np.einsum('k,hkv->hv',K[t],Sd)
        delta=(V[t]-rem)*Bt[t][:,None]; S=Sd+K[t][None,:,None]*delta[:,None,:]
        O[t]=np.einsum('k,hkv->hv',QS[t],S)
    return S,O
for i,(name,lo,hi,ss,vs) in enumerate(fam):
    g=np.random.default_rng(20261123+i)
    k=g.standard_normal((T,KD)); q=g.standard_normal((T,KD))
    k=(k/np.linalg.norm(k,axis=1,keepdims=True)).astype(np.float32); q=(q/np.linalg.norm(q,axis=1,keepdims=True)).astype(np.float32)
    V=rne((vs*g.standard_normal((T,VH,VD))).astype(np.float32)).astype(np.float64)
    D=(lo+(hi-lo)*g.random((T,VH))).astype(np.float32).astype(np.float64)
    Bt=rne((0.05+0.9*g.random((T,VH))).astype(np.float32)).astype(np.float64)
    S0=(ss*g.standard_normal((VH,KD,VD))).astype(np.float32)
    Sr,Or=run(k,q,V,D,Bt,S0); rms=np.sqrt((Or**2).mean())
    for arm,f in (("O1",rne),("trunc",trunc)):
        Sa,Oa=run(f(k),f(q),V,D,Bt,S0); wr,wa=word(Or.astype(np.float32)),word(Oa.astype(np.float32))
        d=(wr!=wa); big=np.abs(Or)>0.01*rms; same=((wr&0x8000)==(wa&0x8000)); step=np.abs(wr-wa)[d&big&same]
        print(name,arm,100*d.mean(),int(step.max()),np.linalg.norm(Sa-Sr)/max(np.linalg.norm(Sr),1e-300),
              np.linalg.norm(Oa-Or)/max(np.linalg.norm(Or),1e-300))
```

Output (columns: bf16 output words that differ in %, largest step of an output above 1 % of the RMS output, state relative L2, output relative L2):

```
decay 0.90-1.00                  | O1    | 52.1 | 160 | 1.65e-03 | 2.49e-03
decay 0.90-1.00                  | trunc | 81.9 | 370 | 3.37e-03 | 6.08e-03
decay 0.999-1.00, long memory    | O1    | 47.9 | 127 | 1.66e-03 | 2.12e-03
decay 0.999-1.00, long memory    | trunc | 71.6 | 220 | 3.58e-03 | 4.89e-03
decay 0.50-1.00                  | O1    | 50.5 | 156 | 1.65e-03 | 2.37e-03
decay 0.50-1.00                  | trunc | 83.5 | 240 | 3.52e-03 | 6.20e-03
decay 0.01-0.30, fast forgetting | O1    | 50.7 |  96 | 1.58e-03 | 2.52e-03
decay 0.01-0.30, fast forgetting | trunc | 81.1 | 263 | 3.35e-03 | 5.91e-03
decay 0.001-0.05                 | O1    | 46.5 |  28 | 1.66e-03 | 2.23e-03
decay 0.001-0.05                 | trunc | 84.9 |  93 | 3.67e-03 | 6.75e-03
zero start matrix                | O1    | 51.2 | 126 | 1.73e-03 | 2.34e-03
zero start matrix                | trunc | 82.2 | 132 | 3.46e-03 | 6.01e-03
large values                     | O1    | 49.6 | 153 | 1.71e-03 | 1.87e-03
large values                     | trunc | 76.8 | 336 | 3.33e-03 | 4.04e-03
small values                     | O1    | 48.8 | 122 | 1.64e-03 | 1.87e-03
small values                     | trunc | 77.3 |  95 | 3.58e-03 | 4.29e-03
```

A step count above 127 means that the two outputs lie in different powers of two. This happens for outputs just above 1 % of the RMS output, where a change of 0.2 % of the RMS output is a large share of the value.

### Script C: K and Q as two truncating pieces

Script B with one more arm. The arm replaces each value by the sum of its first two pieces under the rule of `split()` (`amx_gdn.cpp` :224-231): `hi = trunc(x)`, `mid = trunc(float32(x - hi))`, value `hi + mid`. The same script checks that three pieces give back every key value exactly.

Output:

```
ranges over the 8 families: words that differ 0.818 to 0.958 %, state relative L2 9.60e-06 to 1.14e-05, output relative L2 1.14e-05 to 1.89e-05
2 pieces, per coordinate relative error: max 3.028e-05 (2^-15.01), rms 9.749e-06 (2^-16.65)
```

### Count and cost arithmetic of section 2

```
pieces p of K and Q:  stage 1 = 8*4*4*3*p,  stage 2 = 2*4*4*p*p (per key head, halved per value head),  stage 4 = 8*2*4*3*p
p=1: 384 + 16 + 192 =   592 per value head per block = 18.5 per token
p=2: 768 + 64 + 384 = 1,216 per value head per block = 38.0 per token (2.054 times)
p=3: 1,152 + 144 + 576 = 1,872 per value head per block = 58.5 per token (3.162 times)
O6 (pairs with i + j <= 4, 6 of 9): 768 + 96 + 384 = 1,248 = 39.0 per token (2.108 times)
O7 (K 3 pieces, Q 1 piece): stage 1 = 8*4*(2*3+2*1)*3 = 768, stage 2 = 2*4*(2*9+2*3) = 192 per key head, stage 4 = 576: 1,440 = 45.0 per token (2.432 times)
tile cycles per value head per token at 16.17 per product, 8.38 per load, 16.1 per store (design values, est.):
p=1: 12 products, 7 loads, 1 store (268.8) + 0.5, 0.625, 0.125 (15.3) + 6, 2.75, 2 (152.3) =   436.4
p=2: 24, 11, 1 (496.4) + 2, 1.25, 0.125 (44.8) + 12, 4.75, 2 (266.0)              =   807.2  (+371)
p=3: 36, 15, 1 (723.9) + 4.5, 1.875, 0.125 (90.5) + 18, 6.75, 2 (379.8)           = 1,194.2  (+758)
kernel total (design, est.) 972 to 1,286 cycles; with p=2: 1,343 to 1,657 (1.29 to 1.38 times); with p=3: 1,730 to 2,044 (1.59 to 1.78 times)
```
