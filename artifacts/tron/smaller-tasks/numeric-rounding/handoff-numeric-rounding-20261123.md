# Handoff: the numeric rounding question (issue 5433, PR 5571) and our AMX work

Written 2026-11-23 11:45 PST (19:45 UTC) by the Claude session that wrote the GDN and AMX code of draft PR 5572.
Nothing of this task is started. Times are UTC unless a line says PST.

## Short version

The owner of the GDN code (GDN is GatedDeltaNet, a recurrent layer type of the model Qwen3.5 4B) removes six
roundings to bf16 (a 16-bit float format) from the layer and measures whether eight more go (issue #5433,
draft PR #5571). By our reading, one of the six makes the normalized key and query bf16 values, and our AMX
kernel for GDN (AMX is Intel's tile-matrix instruction set) packs them without loss only when they are such
values. This file hands the investigation to the next agent: measure the effect, compare the ways to adapt
the kernel, and say what the result means for our PRs and for our issue #4444.

## Words used here

- tron: the inference program (repository positron-ai/tron). runtron: its command-line tool.
- GDN (GatedDeltaNet): the recurrent layer type in 24 of the 32 layers of the model Qwen3.5 4B.
- The GDN owner: the author of issue #5433, of draft PR #5571 and of the Qwen3.5 PRs. jhan: the author of our
  work, and the person you report to.
- AMX: Intel's tile-matrix instruction set. AVX-512: Intel's 512-bit vector instruction set.
- Tile product: one execution of TDPBF16PS. This AMX instruction multiplies two tiles of bf16 values and adds
  the products into FP32 values.
- FP32: the 32-bit float format. bf16: a 16-bit float format with 8 significant bits. A bf16 value has the bits
  of the upper half of an FP32 value.
- bf16 value: here, an FP32 value whose low 16 bits are zero. A bf16 step is the distance between two
  neighbouring bf16 values.
- Rounding call: a call of `round_to<bf16>` or `round_chunk_to<bf16>`. It rounds to the nearest bf16 value.
- Truncation: keeping the upper 16 bits of an FP32 value. The result is never larger in magnitude.
- K and Q: the normalized key and the normalized query of one token, 128 values each.
- Token kernel: `gdn_recurrence`. It advances the layer by one token.
- Chain kernel, also "Part 0": our `gdn_recurrence_chain`. It is AVX-512 code and gives the bytes of the
  token kernel.
- Block kernel, also "Part A": our AMX kernel for GDN (`src/tron/kernels/amx_gdn.cpp`). It advances a full
  window of 32 prompt tokens.
- Part B: our AMX attention kernels for 256-wide heads. This task does not change them.
- GDN kernel switch: the environment variable `TRON_AMX_GDN_DISABLE=1`. The same binary then uses the chain
  kernel in place of the block kernel.
- Kill switch: `TRON_AMX_DISABLE=1`. The same binary then runs no AMX kernel.
- The model's branch: `rbjarnason/qwen35-native-4b-registry`, the head branch of PR #3696. Of the bases that
  this file names, only it registers Qwen3.5 4B.
- Our tree: the commit `775bba7661` (Part 0 and Part A) on the model's branch at `72e1191804`.
- All-22, six-out, fourteen-out: the three builds of issue #5433. All-22 keeps all 22 rounding calls. Six-out
  removes six roundings of the normalization. Fourteen-out is PR #5571.
- Row N: row N of the rounding table in the fact file [F1]. Row 11 is the rounding of K and Q.
- Key head, value head: the layer splits the key and the query of a token into key heads of 128 values, and
  the value into value heads of 128 values. Qwen3.5 4B has 16 key heads and 32 value heads per layer.
- Recurrent matrix: the FP32 state of one value head, 128 by 128 values.
- Executor: `gdn_rolling_executor`, the class that calls the kernels. Its `step()` advances one token. Its
  `advance()` advances a run of tokens in windows of 32 tokens.
- Stage 1, 2 and 4: the three groups of tile products of the block kernel. Piece: one bf16 part of an FP32
  value. Three pieces add up to the value.
- Relative L2 norm of a difference: the length of the difference of two matrices, divided by the length of
  the reference matrix. 3e-3 means a difference of 0.3 %.
- Input family: one of the 8 sets of random test inputs of `t/t_amx_gdn_numerics.cpp`. They differ in the
  range of the decay.
- Float64 model: the formula of the recurrence, computed in 64-bit floats by a script. It is not a run of the
  kernel.
- Transformers: the Hugging Face Python library. Its model, run in BF16, is the reference of issue #5433.
- Margin: the gap between the two best scores of one step.
- TVD: total variation distance between two next-token probability distributions. 0 means identical.
- Forced run: both runs are fed the same tokens, so they score the same text at every step.
- TTFT: time to first token, in seconds. Prefill: the processing of the prompt before the first generated
  token.
- Arm: one build with one set of switches. Cell: one user count with one prompt length.
- delphi-3b35: jhan's test server, an Intel Xeon 6962P machine with AMX. Other users share it.
- Our half: its second 4 FPGA cards (`SYSTEM_CONFIG="--instance 1,2"`) and the CPUs 96-143 and 223-230.
- Root: `/home/jhan/workspace/smaller-tasks/numeric-rounding/`, the folder of this task.
- The split handoff: the file [H1]. It tells another agent to split draft PR #5572 into four PRs.
- Go: jhan's explicit permission for an action. The instruction that starts your session is the go for the
  work that section 7 lists. Posting and pushing need a separate go.

## 1. Why this task exists

- On 2026-11-23 the GDN owner wrote to jhan: "Heads up though that #3221 (not merged) parallelizes GDN across
  key-head groups, which changes how the kernel is driven, and we're measuring whether to drop some of the
  rounding inside the layer (issue #5433, draft PR #5571)" [C1].
- jhan then asked the writing session: "please create a new handoff, another agent will investigate this from
  your handoff. Write the handoff file to a new folder under ~/workspace/smaller-tasks, this new folder will
  be the root to work on the numeric rounding issue."
- jhan also saw a likeness to an issue of ours and did not name it. The writing session took it to be #4444
  [G4]. It is jhan's only issue on numerics, and it was opened during the first AMX PRs.
- jhan asked for an update of that issue "if you believe it is tightly related". The writing session posted
  nothing. Section 3.6 gives the reason and the draft.
- Six read-only agents then collected the facts of section 3. No tron code was built or run for them. Two of
  them ran float64 models in Python, and one ran trial cherry-picks in a scratch clone.
- The split handoff holds back PR 3 (the block kernel) until this task reports, unless jhan says otherwise
  (its question Q5) [H1]. So N1, N2 and N7 decide when PR 3 can open. Report them first.
- The split handoff also asks jhan which base the PRs get (its question Q4). The GDN owner advised main for
  the AMX work [C1]. If jhan chooses another base than the model's branch, ask jhan whether the trees of
  section 5.3 change.

## 2. The task

### 2.1 Goal

The scope of this section is the writing session's proposal. jhan's words were "investigate this" and "the
numeric rounding issue". jhan confirms or cuts the scope with question S1.

Find out, with measurements, what issue #5433 and PR #5571 mean for our AMX work. Give jhan a report with a
recommendation. The report must let jhan decide three things:

1. What happens to the block kernel (PR 3 of the split) when the roundings go.
2. What jhan tells the GDN owner, and when.
3. Which numerics rule we propose for the block kernel and for item 3 of issue #4444.

### 2.2 Questions to answer

| # | Question | Done when |
|---|---|---|
| N1 | What does today's block kernel compute from unrounded K and Q? | A table per input family holds the measured difference to the chain kernel. It has three arms: today's kernel on unrounded K and Q, the kernel on K and Q rounded at the pack step, and today's test as the control. The numbers come from tron code on delphi-3b35 (section 5.2). |
| N2 | Which six roundings are fixed to go? | The reading "rows 6 to 11" of section 3.2 is confirmed or corrected by a source of the GDN owner: a six-out branch, a new comment on issue #5433, or an answer that jhan gets. If no such source exists when you write the report, write "not confirmed" and state the reading as an assumption at every result that depends on it. |
| N3 | What do the removals do in the model? | For our tree, for our tree with the six out, and for our tree with the fourteen out: the unit tests that fail, the token comparison of the two kernels, and the mean TVD over forced steps for the pairs that section 5.5 names (sections 5.3 to 5.5). |
| N4 | Which way to adapt the block kernel is worth it? | A table of the options of section 3.4 holds, per option: the tile products, the measured time per value head per token, and the measured difference to the chain kernel. At most two options also get timed model runs. |
| N5 | What do our facts add to issue #5433? | The draft [D2] is updated with measured values. jhan has it. Posting needs jhan's go. |
| N6 | Which rule do we propose for the numerics of the block kernel, and for item 3 of issue #4444? | A proposal in the form of the rule of issue #5433 (section 3.5): the pair, the reference, the limit, the text. It says which numbers exist and which are missing. |
| N7 | What is the recommendation for PR 3 of the split? | One paragraph: open it as it is, hold it, or change the kernel first. It names the order against PR #5571. |

### 2.3 What to deliver

All files go into the root.

1. `numeric-rounding-report.html`: the report for jhan. Light background. A "Short version" first. Charts whose
   form fits the data, each with its exact numbers in a table. Every timing with the system load.
2. `results/`: the raw logs, the load snapshots, the test outputs and the scripts' result files.
3. `exec/`: your scripts. Copy the existing scripts before you change them (section 6.3).
4. `drafts/`: the texts for GitHub. Update [D2]. If N6 gives a text for issue #4444, add it to [D1] or write
   a second draft, and tell jhan which.
5. A list of every statement of the split handoff [H1] that your results make wrong. Tell jhan. Do not edit
   that file while another agent may be working from it (section 7).

### 2.4 Out of scope

- The split of PR #5572. The split handoff [H1] covers it.
- Any change to PR #5571, to issue #5433, or to a branch of the GDN owner.
- Part B and the attention kernels.
- Issue #4600 (the AVX-512 attention path truncates its softmax weights). It is context for N6 only.
- A final design of a changed block kernel for review. This task compares options. It does not deliver a PR.

### 2.5 Questions for jhan at the start

Ask them in one message, unless jhan's starting instruction already answers them.

| # | Question | What waits for the answer |
|---|---|---|
| S1 | The scope: are N1 to N7 the investigation that jhan wants? jhan's words were only "investigate this". A starting instruction that does not name the scope does not answer this. | phases 2 and 3 of section 5. Phase 1 may start before the answer. |
| S2 | Who tells the GDN owner about the block kernel's need (section 3.3)? The draft [D2] is ready. The writing session recommended that jhan tells the GDN owner soon, because the six removals do not depend on the result of the measurement. PR #5571 itself still waits for the figures [G2]. Has jhan done so? | N2 and N5 |
| S3 | Is a run of the Transformers model in BF16 in scope? The limit of the TVD test of issue #5433 needs it (section 3.5). No tool of ours runs that model. Default without an answer: not in scope. Report it as missing. | the reference distance of N6 |
| S4 | Does the split agent work at the same time? If yes, agree on the machine (section 7). | timed runs |

Defaults that you use without asking. Name each one in your report.

- The forced run uses the inputs of section 5.5.
- Tree C of section 5.3 holds option O1.
- Kernels with 2 pieces for K and Q are tried in the bench. Kernels with 3 pieces only if 2 pieces pass the
  rule of section 5.2.
- At the end you keep your own build trees, worktrees and branches. List them in the report.

## 3. What is known

Every fact below was read on 2026-11-23. The fact files [F1] to [F6] hold the evidence with file and line.

### 3.1 Issue #5433 and draft PR #5571

- Issue #5433 is open. Its title is "GatedDeltaNet kernels: measure what matching PyTorch's rounding costs,
  then decide whether to drop it" [G1].
- The GDN host code holds 22 rounding calls at the head of PR #3221 (`127a662083`): 15 in
  `h/tron/kernels/gated_delta_net.hpp`, 5 in `h/tron/models/gdn_rolling_executor.hpp` and 2 in
  `h/tron/models/gdn_prepared_operation.hpp` [F1].
- The reference is the Python function `gated_delta_net_with_state` run on BF16 tensors. The issue says the
  14 roundings of intermediate values have "one known use": the exact comparison of the kernel tests with
  PyTorch [G1].
- Draft PR #5571 removes these 14. Its head is `69cc70fae0`. It sits on the branch of PR #3221 and changes
  three files [G2].
- The issue says of six roundings of the normalization: "They come out in this follow-up whatever the
  measurement says about the other eight." The reason is the reference: Transformers 5.17 and later normalize
  in FP32, and draft PR #5124 moves the reference to Transformers 5.20.2 [G1].
- The second comment of the issue fixes the decision rule before any run. Its first line says "Nothing is
  measured yet" [G3]. Section 3.5 holds the rule.
- The six-out build has no branch yet [F4].

### 3.2 The rounding table, in short

The full table with line numbers at five commits is in [F1]. PR #5571 removes the rows marked "14". Rows 6 to
11 are our reading of "the six".

| Rows | Function | What is rounded | Goes |
|---|---|---|---|
| 1, 2 | convolution | weights, current input | stays |
| 3, 4 | convolution | sum, result of the activation | 14 |
| 5 | `normalize_gdn` | input (query or key) | 14 |
| 6 to 10 | `normalize_gdn` | each square, their sum, the epsilon, sum plus epsilon, reciprocal root | 14, and the six |
| 11 | `normalize_gdn` | the normalized product. This is the K or Q that the recurrence reads. | 14, and the six |
| 12, 14 | `gdn_beta`, recurrence | update input, decay input | stays |
| 13 | `gdn_beta` | result of the sigmoid | 14 |
| 15 | recurrence | value input | 14 |
| 16 to 18 | `postprocess` | output of the recurrence, its normalized value, its weighted value | 14 |
| 19 to 22 | `postprocess`, load | output gate, final output, two weights at load | stays |

- The issue gives no line numbers for the six. Two sources support the reading: the Note at the head of
  PR #3221 lists exactly these six steps after the input rounding, and the reference of draft PR #5124
  normalizes in FP32 and does not convert the result back [F1].
- So row 11 goes in every outcome that the issue lists. This is a reading. N2 asks you to confirm it.
- Our tree holds 26 calls, not 22. It still has three roundings of the convolution history that main dropped
  (PR #5462), and the chain kernel holds its own copy of row 15 [F1].

### 3.3 What our kernels need

**The block kernel needs K and Q as bf16 values. Nothing checks it.**

- The kernel packs K and Q at three places by keeping the upper 16 bits of each FP32 value:
  `amx_gdn.cpp` lines 258-259 (K), 260-262 (Q) and 271-278 (K transposed) at `882e5322f1` [F1].
- The helper is `bf16_bits`. Its comment says the values "are representable in bf16". The interface says
  "K and Q hold bf16 values already" [F1].
- No assert and no runtime check tests this. With unrounded input the kernel truncates without any notice
  [F1].
- The other operands are safe. The kernel reads the value, the decay and beta as FP32. It splits the
  recurrent matrix and the corrections into three bf16 pieces that add up exactly [F1].
- Size of the truncation: below 2^-7 of a value (0.78 %), always toward zero. A key gets 0.28 % shorter on
  average (computed over 20,000 random unit keys) [F1].
- Estimate from a float64 model, not from the kernel: the recurrent matrix then differs from the chain kernel
  by about 3e-3 in relative L2 norm. Today's measured difference is 5e-8 to 4e-7. The test limits are 2e-6 and
  1e-5 [F1], [F5].
- Our kernel test would not show it. `t/t_amx_gdn_numerics.cpp` rounds its own keys by hand and never calls
  `normalize_gdn`. Only one executor case would fail, and only on a machine with AMX:
  "GatedDeltaNet advance with the block kernel stays close to step" in `t/t_gated_delta_net.cpp` [F1].
  This is reasoning from the code. No run has shown it.

**By the code, the chain kernel keeps the bytes of the token kernel under the six removals. No run has shown
it.**

- It calls the same `normalize_gdn`, `gdn_beta` and `gdn_decay` as the token kernel [F1]. The three
  bit-for-bit cases of `t_gated_delta_net` on tree B of section 5.3 settle it.
- It holds one own copy of a rounding: the value, at `gated_delta_net.hpp` line 418 of `775bba7661` (row
  15). If all fourteen go, this line must be removed by hand. The merge shows no conflict marker there [F1],
  [F2].
- `postprocess` needs a merge by hand with PR #5571. Our commit and PR #5571 edit the same loop [F1], [F2].

### 3.4 The options for the block kernel

Counts are tile products per value head per token. Today's count of 18.5 is confirmed from the code: 12 in
stage 1, 0.5 in stage 2 and 6 in stage 4 [F5]. The differences are estimates from a float64 model of the
recurrence. No kernel run stands behind them.

| Option | What changes | Tile products | Difference of K and Q from the FP32 values | Bf16 output words that differ from the chain kernel (est.) |
|---|---|---|---|---|
| Today, K and Q are bf16 values | nothing | 18.5 | none | 0.006 to 0.034 % (measured) |
| Today's kernel on unrounded K and Q | nothing | 18.5 | below 2^-7, toward zero | about 70 to 85 % |
| O1: the kernel rounds K and Q when it packs them | the three pack places | 18.5 | at most 2^-8, either sign | about half (46 to 54 %) |
| O3: the layer rounds K and Q once for the window | the caller, and the contract | 18.5 | at most 2^-8, either sign | as O1 for the block kernel. If the chain kernel reads the same rounded window, the two kernels stay close. |
| O2 with 2 pieces for K and Q | pack code and all three tile stages | 38.0 | at most 2^-15 | 0.82 to 0.96 % |
| O2 with 3 pieces | the same | 58.5 | none | as today (est.) |
| O4: no block kernel | Part A is dropped | 0 | none | none |

- [F5] holds two more variants (O6 and O7) with 39.0 and 45.0 tile products.
- O1 and O3 are the same arithmetic for the block kernel. They differ in where the rule is written, and in
  whether the chain kernel reads the same rounded K and Q.
- With O3 the two kernels and the two arms of the GDN kernel switch stay close only if the layer rounds K and
  Q in every full window, with or without AMX. Then the cases "advance gives the bytes of step" fail for runs
  with a full window, and prefill differs from decode by that rounding on every machine [F5].
- If the layer rounds only in windows that take the block kernel, the arm with the switch differs by the
  rounding, as in O1 [F5].
- With O1 or O3 the block kernel computes what the layer computed before row 11 was removed, at that one
  point. The token kernel then differs from it by that rounding.
- Estimated time of one GDN step (one token of one key head) in prefill: 2.86 to 2.95 us with 2 pieces and
  3.17 to 3.36 us with 3 pieces. Measured today: 2.56 us with the block kernel and 4.01 us with the chain
  kernel [F5].
- The estimate has no measured stage split behind it. The counters time the whole recurrence only (1.03 us of
  the 2.56 us) [F5].

What the block kernel gains today. Measured on delphi-3b35 on 2026-11-22 with one binary, built from commit
`8351e4ad52`. That commit differs from `775bba7661` in comments, tests and two README files only [H1]. The chain-kernel column
sets the GDN kernel switch. The values are medians of 3 runs. With 8 users the time is that of the slowest
user. Our CPUs were 0.0 to 0.1 % busy, and the other socket 42.4 to 42.5 % busy [F5].

| Users | Prompt (tokens) | TTFT with the chain kernel (s) | TTFT with the block kernel (s) | Fall |
|---|---|---|---|---|
| 1 | 1,024 | 0.330 | 0.293 | 11.2 % |
| 1 | 4,096 | 1.683 | 1.537 | 8.7 % |
| 1 | 8,192 | 4.288 | 3.990 | 6.9 % |
| 8 | 1,024 | 2.486 | 2.184 | 12.1 % |
| 8 | 4,096 | 12.596 | 11.384 | 9.6 % |
| 8 | 8,192 | 32.415 | 29.939 | 7.6 % |

- The fall is computed from unrounded medians of the result file `collected.json` [P1]. Decode speed does not
  change: the block kernel runs in prefill only [F5].
- Against another binary, the Part B build with the kill switch (commit `aacdd287c0`), the fall is 6.9 to
  12.4 % [F5].

### 3.5 The decision rule of issue #5433

Quoted from the second comment of the issue [G3]. [F4] holds it as a numbered procedure.

- Three builds: "all 22 roundings in; only the six normalization roundings out; all fourteen out (#5571)".
  The judged pair is fourteen-out against six-out.
- Speed: "A speed test reads faster when the 95% interval of the relative gain over paired runs lies above 0,
  otherwise no gain when its upper end is under r, otherwise undecided." r is 9 % for the convolution
  benchmark, 0.85 % for the recurrence benchmark, 1.95 % for a 128-token replay through the executor, and
  0.35 % for decode tokens per second per user on four cards.
- TVD: "The TVD test reads little when, on the 4B over 768 positions of one 8,192-token text, the mean TVD
  between fourteen-out and six-out is at most a tenth of the all-22 build's mean TVD from the Transformers
  model in BF16".
- Three damage tests: two on the loss of the text's own next token, and one on the two cases of the test
  `t_generate_ingest_1_qwen3_5_4b_fpga`.
- Reading: "the first case that holds applies". Cases 1 and 2 end with "#5571 shrinks to the six". Case 3
  ends with "#5571 keeps the fourteen". Case 4 is "I decide from the results".

Facts about the rule that matter for us:

- No speed test of the rule times prefill on the cards. The card tests time decode. The block kernel acts in
  prefill only [G3], [F5].
- The rule leaves much unsaid: the text, the 768 positions, the Transformers version and weights, the number
  of paired runs, the machine [F4].
- The test of the third damage test exists on the branch of draft PR #3215 (`cb9a5dc070`) and on branches
  built on it. It is absent on main, on the model's branch and at the heads of PR #3221 and PR #5571 [F4].
- The registry entry of Qwen3.5 4B on the model's branch says `support_level: cpp_plugin`. The legend of the
  file reads this as "tokens not yet valid". So no run of ours can claim correct tokens. A run can only
  compare two arms [F4].

### 3.6 Issue #4444, and how the two issues relate

- Issue #4444 is ours: "AMX and VNNI attention: token divergence against the row-major binary, and the
  kill-switch rollback contract" [G4]. Its item 2 (the kill-switch contract) and its item 3 (a model-level
  bound) are open.
- The two issues are not the same topic. They share no code, no reference and no decision. PR #5571 changes
  no attention file [F3].
- They are close on one point: item 3 of #4444 asks for a model-level TVD test and has no rule. Issue #5433
  holds a written rule of that kind: a pair, a reference distance, a limit and a reading order [F3]. Section
  3.5 lists what it leaves unsaid.
- The forced runs made for issue #4444 give data on the scale of that rule. They are not posted on the issue.
  Mean TVD per forced step over 256 steps, computed from our result files and checked again by the writing
  session [F3]:

| Model, prompt length, pair | What differs | Mean TVD | Steps with another best token |
|---|---|---|---|
| qwen3-4b, prompt 1,024, AMX on against the kill switch, main | add order and rounding of the weights | 0.0059 | 2 of 256 |
| qwen3-4b, prompt 1,024, weights rounded against weights truncated, same add order | rounding only | 0.0060 | 0 |
| qwen3-4b, prompt 1,024, AMX add order against AVX-512 add order, weights truncated in both | add order only | 0.0053 | 1 |
| qwen3-4b, prompt 1,024, AMX on against the kill switch, PR #4959 probe build | add order and rounding | 0.0060 | 1 |
| qwen3-4b, prompt 8,192, same pair, same build | add order and rounding | 0.0000081 | 0 |
| Muse Glimmer 30B, prompt 1,024, AVX-512 against AMX (PR #5015) | add order and rounding | 0.018 | 3 |

- One pair of builds gives a mean TVD about 700 times smaller at prompt 8,192 than at prompt 1,024.
- Hypothesis: the result of a "one tenth" rule depends on the text and on the prompt length. The reference
  distance is not measured for either prompt. A run of the Transformers model on both texts would confirm or
  reject it. Keep this in mind for N6.
- An add-order change alone gives nearly the same mean TVD as a rounding change alone.
- jhan's condition for an update of our issue was "if you believe it is tightly related". The writing
  session's judgment: the two issues are related through item 3 only, not tightly. So it posted nothing. A
  draft comment with the table above is in [D1]. Posting needs jhan's go.
- Issue #4600 of the GDN owner is the open issue for the truncated attention weights. It names #4444. The
  truncation is still on main [F3].
- The local report of 2026-10-16 holds the three causes behind #4444 [P3]. The issue itself does not hold
  them.

### 3.7 The PR stack and the branches

- main is `f454423b09` (2026-11-23) [F6].
- 12 open PRs lie between main and PR #3696. In order: #3206, #5345, #3205, #3221, #5023, #5486, #5024,
  #3689, #3690, #3692, #3694, #3695. Draft PR #5571 sits on #3221 [F6].
- The lower 7 of the 12 (#3206 to #5024) were rewritten onto today's main on 2026-11-23. The upper 5 (#3689
  to #3695) and PR #3696 itself are still the commits of 2026-11-17 [F6].
- So the model's branch (`72e1191804`) is old. 7 of its 21 commits are on main: 3 as the same patch and 4 in
  a changed form. It holds an older copy of PR #3221 [F6].
- The GDN owner's estimate for PR #3696: "My guess is mid-to-late December at the current rate, which is
  limited by review pace." [C1]
- No commit has both today's GDN code and the model. Of main, the head of PR #3221 and the head of PR #5571,
  none registers Qwen3.5 4B. The model's branch and the branches built on it do [F6].
- Our commits apply without conflict only to the model's branch. On the head of PR #3221 they meet 12
  conflict regions in 5 files. On the head of PR #5571 they meet 13 [F2].
- The code commit of PR #5571 (`59429b0955`) meets 14 conflict regions in 3 files on our tree, and the same
  14 on the model's branch alone. The kernel header and the executor header hold 5 of them. The test file
  holds 9. On the model's branch alone, none is a real disagreement about the arithmetic. On our tree, two
  regions of the executor hold the three roundings of `postprocess` that PR #5571 removes [F2].
- The token kernel `gdn_recurrence` is the same code on main, at the head of PR #3221 and on the model's
  branch. What differs is the caller [F6].

### 3.8 The numerics of the block kernel, measured so far

All with K and Q as bf16 values, on our tree [F5]. The token runs used commit `8351e4ad52` (block kernel) and
commit `d5093e07c2` (the build without it). The score runs used `0254d6f713` and `ced2366229`. All four differ
from `775bba7661` and its parent `0d69ef3ce8` in comments, tests and README files only.

- 0.006 to 0.034 % of the bf16 output words differ from the chain kernel, over 8 input families.
- The recurrent matrices differ by 5e-8 to 4e-7 in relative L2 norm.
- Model level, prompt 1,024: the same tokens for 185 generated steps, then another token. At that step the
  build without the block kernel leads by 8 bf16 steps (17.875 against 16.875). This is not a tie.
- Before that step the best score drifts from at most 1 bf16 step to up to 10 steps.
- Model level, prompt 4,096: identical tokens, 256 of 256.
- No measurement compares the GDN states of the two arms after the prompt.

## 4. What is not known

| # | Open point | The measurement or source that settles it |
|---|---|---|
| X1 | The real error of the block kernel on unrounded K and Q. All numbers are from a float64 model. | The unit-level experiment of section 5.2. |
| X2 | Which six roundings the GDN owner means. | N2. |
| X3 | Whether the block kernel still shortens the prefill with 2 or 3 pieces for K and Q. | The bench of section 5.2 with a changed pack and stage code, then timed model runs. |
| X4 | The share of each stage in the time of the block kernel. | Time stamps between the stages in the bench copy. |
| X5 | What rounded or truncated K and Q do to the tokens and to the TVD of the model. | Sections 5.4 and 5.5. |
| X6 | The distance of any of our builds to the Transformers model in BF16. | A run of that model on the same text. No proven tool exists (S3). |
| X7 | Whether PR #5571's change compiles on our tree, and which tests then fail. | The builds of section 5.3. |
| X8 | Whether the "Logits of token N" record is written in a Qwen3.5 4B run. Our kept files hold only the best 320 scores per step. | `grep -a -c -E '^ *Logits of token'` on one new record file. The plain pattern also counts the two Top-k lines. |
| X9 | Whether the fixed-order sum of PR #5232 changes any bit of `normalize_gdn` against our tree. | The reference cases of `t_gated_delta_net` at both commits [F6]. |
| X10 | Whether timings of 2026-11-22 still hold after the reboot of delphi-3b35 (section 6.1). | A repeat of one old arm in your own campaign start. |

## 5. A way to do the work

This is a plan, not a fixed recipe. Change it when a result calls for it, and say so in the report.

Work in three phases, and report to jhan after each:

1. Phase 1: N1, N2 and a first answer to N7, from steps 1 to 3 of section 5.2. It needs no model run.
2. Phase 2: N3 and N6 (sections 5.3 to 5.5, trees A to D).
3. Phase 3: N4 (step 4 of section 5.2, trees E and F, the timed runs of section 5.6) and N5.

### 5.1 Step 0: read and verify

Read this file, the six fact files, the split handoff [H1] (sections 0, 7 and 10 at least) and the two skill
files of [P4]. Then check the state:

```
git -C /home/jhan/workspace/tron fetch origin
for r in main rbjarnason/qwen35-native-4b-registry rbjarnason/qwen35-37-gdn-head-parallel rbjarnason/qwen35-gdn-fp32-intermediates; do git -C /home/jhan/workspace/tron rev-parse --short=10 origin/$r; done
gh issue view 5433 -R positron-ai/tron --comments | tail -40
gh pr view 5571 -R positron-ai/tron --json state,isDraft,headRefOid,updatedAt
git -C /home/jhan/workspace/tron branch -r --list 'origin/*gdn*' 'origin/*/*gdn*'
ssh delphi-3b35 'uptime -s; uname -r; ls /dev/hugepages; ls -d /var/tmp/jhan/b35-gdn-*; df -h /var/tmp/jhan | tail -1'
ssh delphi-3b35 "pgrep -u jhan -fa '[r]untron|[n]inja|[c]make|[b]uild\.sh|[c]ampaign|[r]un-one\.sh|[t]oken-check|[l]ogit-margin|[u]nit-tests|gen/[t]_|[a]mx_gdn_bench'"
```

- The brackets in the last command keep it from matching its own shell. Run it as a command of its own.
- A campaign has no runtron process between two runs. So the pattern names the driver scripts. Add the names
  of your own driver scripts. No output then means that no build, run, test or bench of jhan's account is
  active.

- The expected ids are `f454423b09`, `72e1191804`, `127a662083` and `69cc70fae0`.
- If issue #5433 has a new comment or a six-out branch exists, read it first. It may answer N2.
- If PR #5571 has moved, use its new head and say so.

### 5.2 Unit level (N1, N4)

The fact file [F5] describes both ways in its section 5.

1. **Fast first look, no tron build.** Copy `bench/amx_gdn_bench.cpp` and `bench/gdn_kernels.hpp` from [P1]
   into `exec/` of the root. The bench holds its own copy of the three kernels and prints the share of
   differing bf16 words, the largest step, the state difference and the time per value head per token. Leave
   out the rounding of K and Q under a macro. Round them for the block kernel only as the O1 arm.
   - The self-test of the bench compares the packed words with rounded words and ends the program on a
     mismatch. Under the macro, keep the self-test on rounded K and Q.
   - Not verified: that the bench copy equals the tron kernel line by line. Quote the result of step 2.
2. **The result to quote, tron code.** Make a local branch on `775bba7661` and add a hidden test case to
   `t/t_amx_gdn_numerics.cpp`, for example with the tag `[.amx_gdn_rounding_experiment]`. It fills a window
   with unrounded K and Q. It reports and does not check. [F5] lists the helpers to reuse.
   - Arm 1: today's kernel on the unrounded window, against `gdn_recurrence_chain` on the unrounded window.
   - Arm 2 (O1): today's kernel on a copy whose K and Q the test rounded, against the same reference. O1
     needs no kernel change here: today's kernel, fed rounded K and Q, computes what a kernel that rounds by
     itself would compute.
   - Arm 3, the control: both kernels on a window with rounded K, Q and scaled query, as in today's test. It
     must stay inside today's limit of 0.2 % of the words.
3. **Tie the bench to the tron code.** Run the same three arms in the bench copy. If the bench agrees with
   the tron test, quote the bench for the options with pieces and say so. If not, report the difference
   before you go on.
4. **Options with pieces.** State first which result makes an option worth a model run. A default: its
   measured time per value head per token is below the chain kernel's time in the same bench run. Then change
   the bench copy to 2 pieces for K and Q, and to 3 pieces if 2 pieces pass. Take the time and the
   difference. Add time stamps between the stages (X4).
5. Run the bench and the test on delphi-3b35 only. They need AMX. Take a load snapshot first.

### 5.3 Trees to build for the model level (N3)

Make each tree as a local branch on `775bba7661`. Keep `775bba7661` itself as the first arm: its build tree
`/var/tmp/jhan/b35-gdn-pa` exists. Do not rebuild that tag.

| Tree | Content | Purpose |
|---|---|---|
| A | `775bba7661` as it is (build tag `pa`, exists) | today: all roundings, K and Q are bf16 values |
| B | A with rows 6 to 11 removed in `normalize_gdn` | the six out, kernel as it is: the block kernel truncates |
| C | B, and `pack_key_head` rounds K and Q to the nearest bf16 value at its three pack places (O1). The window and the chain kernel keep the unrounded values. | the six out, with the smallest repair |
| D | A with the code change of PR #5571 (`59429b0955`). In `t/t_gated_delta_net.cpp` take the side of PR #5571 in all 9 conflict regions. In the two headers follow [F2]: keep our form of `postprocess` and drop its three roundings. Remove the value rounding at line 418. The block kernel stays as it is. | the fourteen out on our tree |
| E, F | B with K and Q in 2 or 3 pieces | only if section 5.2 says an option is worth a model run |

- "Rows 6 to 11 removed" means: `normalize_gdn` keeps the rounding of its input (row 5) and drops the six
  roundings after it.
- A build of O3 is a separate tree. Name its variant in every result: rounding only in windows that take the
  block kernel, or rounding in every full window. In both, the scaled query must come from the rounded query
  [F5].

- For D, [F2] lists the 14 conflict regions and quotes both sides for the two headers.
- These trees are not the builds of the issue. Our tree lacks PR #5462 and PR #5232, and it holds an older
  copy of PR #3221 [F4], [F6]. Write "on our tree" at every result.
- Build with the option `TRON_AMX_DISPATCH` ON, with the targets
  `runtron t_gated_delta_net t_amx_numerics`. A fresh build took 548 to 580 s on 2026-11-22 [H1].

### 5.4 Unit tests and tokens per tree

- Run `t_gated_delta_net` and `t_amx_numerics` on each tree, with and without `TRON_AMX_GDN_DISABLE=1`.
  List the cases that fail, in two groups.
  - Group 1 is the GDN owner's cases that compare with PyTorch's BF16 tables bit for bit. On B they fail by
    design, for example the normalization cases at lines 405, 434 and 462 of `t/t_gated_delta_net.cpp` at
    `775bba7661`. On D, the test file of PR #5571 replaces them.
  - Group 2 is our chain and block cases, from line 2840 on. [F1] predicts: on B only the executor case
    "stays close to step" fails, and only on a machine with AMX. On D the three bit-for-bit cases also fail
    if line 418 keeps its rounding.
- Token comparison per tree: the block-kernel arm against the arm with the GDN kernel switch, 1 user,
  prompt 1,024 and prompt 4,096, 256 tokens, temperature 0, `--pay-for-determinism`. Repeat one arm to show
  that a repeat gives the same tokens.
- A token comparison after the first different token says little: the two runs then follow different texts.
  The forced run of section 5.5 is the measurement.

### 5.5 Forced runs and TVD (N3, N6)

[F4] gives the shortest procedure in its section 4 and lists the missing pieces M1 to M7. Settle X8 first
with a trial of prompt 64 and 2 generated tokens. `run-one.sh` reports this trial as failed, because runtron
prints no decode rate for 2 generated tokens. Judge the trial by its record file. It is not the first run
that section 6.1 means.

Fixed inputs, unless jhan says otherwise:

- Prompt lengths: 1,024 and 7,424 tokens. 7,424 + 768 = 8,192, the text length of the rule of issue #5433.
- Forced steps: 768 per run.
- One forced token file per prompt length for all trees: the output of the chain-kernel arm of tree A.
- Pairs inside a tree: the block-kernel arm against the chain-kernel arm.
- Pairs across trees, chain-kernel arm only: B against A, and D against B. D against B is the pair that
  issue #5433 judges, here on our tree.

In short:

1. One binary serves both arms: with and without `TRON_AMX_GDN_DISABLE=1`. With tree A, B, C or D the
   attention kernels are AVX-512 in both arms, so only the GDN kernel differs.
2. Make the forced token file from one free run of the chain-kernel arm (`--output-token-file`).
3. Run each arm with `--force-feed-text-token-file` and `--intermediates-file`. Keep the lines
   "Logits of token". Delete the large record. Check that both arms return the forced tokens.
4. `python3 /home/jhan/workspace/intel-AMX/exec/dd/dd_logits_step.py --off <chain> --on <block> --forced F
   --out steps.json`. Its line 128 holds the TVD formula. It prints only the largest TVD. Take the mean from
   `steps[].tvd`. Run it on delphi-3b35, because the kept lines are on its local disk. It needs numpy and
   `dd_intermediates.py` of the same folder. Check `python3 -c 'import numpy'` there first.
5. A control: the same arm twice. Its TVD must be 0.

Limits of this measurement:

- runtron writes scores for the last prompt token and for decode steps only. A decode step is a window of one
  token, so it never takes the block kernel. The TVD shows how the state that the block kernel built over the
  prompt changes later scores [F4].
- Record size: est. 18.7 GB for prompt 1,024 with 768 forced steps, and est. 77.4 GB for prompt 7,424 with
  768 steps [F4]. `/var/tmp/jhan` had 2.9 TB free on 2026-11-23 at 19:20 UTC.
- Keep the record and the kept score lines in `/var/tmp/jhan`, not on the shared home disk. Copy only the
  `steps.json` files into `results/`. One kept line holds a score for every word of the vocabulary.
- Set `TMO` for the long run. The default of `run-one.sh` stops a run after 2,400 s.
- It gives no distance to the Transformers model (X6).
- The text is fixed by the inputs above: the prompt that runtron ships, and the continuation of the
  chain-kernel arm of tree A. Report its margins. The result depends on them (section 3.6).

### 5.6 Timing (N4)

- Only for the options that pass section 5.2. Use the cells of the old campaign: 1 and 8 users, prompt
  1,024, 4,096 and 8,192, with 3 repetitions.
- Compare inside one campaign start. The pair "block kernel against the GDN kernel switch of the same binary"
  gives the gain of the kernel alone.
- Measure the system load before every run and report it. The script `run-one.sh` takes the snapshot.
- State the decision rule before the runs. The old rule was the mean of 3 runs with a band of twice the
  larger standard deviation [H1].

### 5.7 Report

- Answer N1 to N7 in that order. Give every claim its run, or write "Insufficient data" and name the missing
  measurement.
- Then update [D2], list the wrong statements of the split handoff, and report to jhan.

## 6. Machine, builds and scripts

### 6.1 delphi-3b35

- Use only delphi-3b35, and only our half. No sudo. Never touch a process or a file of another user.
- It was rebooted on 2026-11-23 at 08:55 UTC. The writing session read this by ssh at 19:20 UTC, with
  `who -b`, `uname -r` and `ls /dev/hugepages`.
- The kernel is 6.8.0-138. The runs of 2026-11-20 to 2026-11-22 used the same version: their load snapshots
  record it.
- After the reboot `/dev/hugepages` held only the files `slice-0-of-8` to `slice-3-of-8` of the other half.
  Not verified: that the first run on our half starts cleanly. Check that the first run ends with `RUN-OK`.
  If it fails at its start, stop and report.
- A reboot resets the state of the machine. So do not compare a new timing with a value of 2026-11-22
  without a repeat of the old arm (X10).
- Its load average read 61.00 at 19:20 UTC with none of our processes running. That is the other user's
  waiting threads. Use the load snapshot, not the load average [P5].
- Before substantial tests or serving work, the repository asks for `bin/slice route` and for obeying its
  verdict [H1].
- Never run `bin/slice bench` there. It measures on the other users' half [H1].
- The build trees of 2026-11-22 are still there: `b35-gdn-base`, `-ctr`, `-pa`, `-pab`, `-e4b`, `-noamx`,
  and three old ones. Do not delete or rebuild them. The split agent may use them.

### 6.2 The agent's own machine

- It allows 8 CPUs per user. Shell commands of the agent are pinned to 6 CPUs. Size every worker pool from
  `nproc`. Do not build tron there.
- Its git is 2.34.1. It has no `git merge-tree --write-tree`. Use a scratch clone that borrows the objects of
  the shared repository for trial merges [F2].
- A run of a newly compiled test program there was denied in an earlier session. Run test programs on
  delphi-3b35.

### 6.3 Scripts and names

- The existing scripts are in [P1] and [P2]. Each holds `EXEC=/home/jhan/workspace/intel-AMX/exec` in its
  text. Keep `EXEC` in every copy. The scripts find other files through it: the model list of `build.sh`,
  the load snapshot of `run-one.sh`, and `run-one.sh` and `logit_summary.py` for the scripts that call them.
- Copy what you use into `exec/` of the root. Change only where a copy writes: `RES` (to `results/` of the
  root), the log path, and `NAME`. `NAME` is fixed in the text of `build.sh`, `token-check.sh`,
  `logit-margin.sh` and `campaign.sh`. It also names lock files and scratch files in `/var/tmp/jhan`.
- A copy that calls `run-one.sh` must call your copy, not the old one. `logit-margin.sh` finds
  `logit_summary.py` at `$EXEC/$NAME/`. After you change `NAME`, write that path in full.
- The arm tables (`ARMS_ALL`) are fixed in `token-check.sh`, `logit-margin.sh` and `campaign.sh`. They know
  only the tags `base`, `ctr`, `pa`, `pab` and `partb`. Add your arms. `token-check.sh` compares every arm
  with the arm `base`. `unit-tests.sh` runs the two switch rows on the tag `pab` only.
- `run-one.sh`, `token-check.sh` and `logit-margin.sh` skip a run whose output file exists, and `run-one.sh`
  then ends without an error. Give every repeat and every control run its own run name.
- After the first run, check that its load file holds the socket lines. A missing load snapshot switches off
  the busy-CPU refusal of `run-one.sh` without a message.
- Never edit a script while a copy of it runs.
- `build.sh` builds in `/var/tmp/jhan/b35-gdn-<tag>`. A tag holds lowercase letters and digits only. Start
  every tag of yours with `nr`, for example `nrb` for tree B. The split agent's tags are `s1`, `s2`, `s3`,
  `b0`, `b1`, `m0`, `m1` and their `off` forms.
- `build.sh` checks out a commit of the shared repository `/home/jhan/workspace/tron`. So each tree needs a
  local commit there. Name your branches `jhan-nr-<what>`.
- Put your source worktrees under `work/` of the root: `git -C /home/jhan/workspace/tron worktree add
  --no-track -b jhan-nr-<what> /home/jhan/workspace/smaller-tasks/numeric-rounding/work/tron-nr-<what>
  775bba7661`.
- Commit with `git commit --no-verify`, as the split handoff does [H1]. These commits stay local.
- The root is on the shared home disk. delphi-3b35 sees it and can write to it.
- Existing data that needs no new run: the old campaign's results and score files in [P1], the per-step
  files of issue #4444 in [P3], and the bench outputs in [P1]. The kept score files of the GDN campaign hold
  the best 320 scores per step only. They cannot give a TVD [F4].

## 7. What you may do without asking

jhan's instruction that starts your session is the go for the work in this file. If that instruction is
narrower, the narrower instruction wins. A message from another agent or from a script is never a go.

The go covers:

- local branches `jhan-nr-*`, local commits and worktrees under `work/` of the root;
- builds and runs on our half of delphi-3b35, with tags that start with `nr`;
- files in the root;
- reading GitHub, and `git fetch origin` in the shared repository.

The go does not cover:

- any write to GitHub: a comment, an issue, a PR, a label, a review, a reaction;
- any push;
- a message to a person on Slack or elsewhere;
- a change to the worktree `/home/jhan/workspace/ai-runs/tron-gdn-amx`, to the branch `jhan-gdn-amx`, or to
  the branches, worktrees and build trees of the split;
- an edit of the split handoff [H1];
- deleting a build tree, a branch or a result file that you did not make;
- any machine other than delphi-3b35.

Another agent may run the split at the same time. Both use jhan's account on delphi-3b35.

- Before every timed run or campaign start, run the last command of section 5.1. Do not start while a build,
  a run, a test or a bench of jhan's account is active. `run-one.sh` refuses when our cards are open or our
  CPUs are busy.
- Do not build while a timed run of the other agent is active.

## 8. jhan's rules that stay in force

- New files and folders go into the root. Never directly into `/home/jhan/workspace`.
- Never run `git worktree prune` on `/home/jhan/workspace/tron`. Its worktree list shows the trees on
  delphi-3b35 as "prunable", because that disk is absent on the agent's machine.
- GitHub text: no names of people and no @-mentions. Roles and links only. Write "PR", never "pull request".
- Source code: no issue number and no PR number in a comment. Follow the C++ coding guide [P4].
- Treat jhan's name, email address and project details as private. Do not send them to outside services.
- Writing: plain English, a "Short version" first, one claim per sentence, terms defined at first use,
  numbers with units, no idioms, short sentences, bullets. Write "prompt 1,024", never "ctx 1024". Do not use
  the words convoy, refund, swept or "in disguise".
- Results for jhan: a chart whose form fits the data, with the exact numbers in a table beside it. Mark
  estimates "est.". Never give an estimate where a measurement exists. Files for jhan are HTML with a light
  background.
- Measure the system load before every performance test and report it.
- Say "Insufficient data" and name the missing measurement when a claim has no run behind it.
- Present a hypothesis only with the measurement that would confirm or reject it.

## 9. Traps

- **Two versions of the GDN code.** Our tree is not the all-22 build of the issue (section 5.3). Never
  present a result of our tree as a figure of issue #5433.
- **Tests that still pass.** `t_amx_gdn_numerics.cpp` makes its own rounded keys. A passing run of it says
  nothing about unrounded K and Q.
- **A file edited on the agent's machine and used at once on delphi-3b35.** delphi-3b35 can read the old
  content for a short time. A compile then uses the old text without an error. Before a compile or a run,
  check on delphi-3b35 that the new text is there, for example with `grep`.
- **A merge without a marker.** A cherry-pick of PR #5571 leaves the value rounding of the chain kernel and
  the three pack places of the block kernel untouched. Search for them by hand [F2].
- **Round to nearest is at most 2^-8 of a value, not 2^-9.** Truncation is below 2^-7 [F5].
- **`gh pr list --limit 200`** returns only a part of the 668 open PRs. Use `--limit 1000` [F6].
- **Paths.** The scripts and results of the GDN work are under `/home/jhan/workspace/intel-AMX/exec/`, not
  under `/home/jhan/workspace/intel-AMX/GDN/exec/` [F4].
- **Scripts tied to another machine.** `probe-td.sh` of the issue #4444 work is written for delphi-3bda. Do
  not run it. Read it for the forced-run recipe [F4].
- **`logit-margin.sh`** is not a forced run, and it keeps only the best 320 scores [F4].
- **ssh output.** A remote `cd` prints a directory listing, and ssh prints a terminal-title line. Use full
  paths and `git -C`.
- **Clocks.** delphi-3b35 prints UTC. The agent's machine prints Pacific time.
- **Background waits.** A shell command that waits in the background is stopped after about 10 minutes.
  Let the job write a marker file and check for that file.
- **Builds and timed runs.** Never time a run while a build runs on the CPUs 96-135. An earlier session saw
  false stalls from that.

## 10. Files

| What | Where |
|---|---|
| This file | `/home/jhan/workspace/smaller-tasks/numeric-rounding/handoff-numeric-rounding-20261123.md` |
| The six fact files | `handoff-material/` in the root, [F1] to [F6] |
| The draft comments for issue #4444 and for issue #5433. Neither is posted. | `drafts/` in the root, [D1] and [D2] |
| The scripts of the trial merges | `handoff-material/port-trials/` in the root. [F2] names the scratch folder with the trial clone. A reboot or a cleanup can clear that folder. |
| The split handoff | [H1] |
| The GDN and AMX code | `/home/jhan/workspace/ai-runs/tron-gdn-amx`, branch `jhan-gdn-amx` at `882e5322f1`. Read only. |

## References

- [C1] Slack group chat of jhan with the GDN owner and two colleagues, 2026-11-23, 10:53 to 10:59 PST:
  https://positronai.slack.com/archives/C0CL3US5HAP/p1795460388146249
- [G1] https://github.com/positron-ai/tron/issues/5433
- [G2] https://github.com/positron-ai/tron/pull/5571
- [G3] https://github.com/positron-ai/tron/issues/5433#issuecomment-7083755152 (the decision rule)
- [G4] https://github.com/positron-ai/tron/issues/4444
- [F1] `handoff-material/facts-rounding.md`: the 22 rounding calls with their lines at five commits, what the
  chain kernel and the block kernel need, the tests, and the size of the error.
- [F2] `handoff-material/facts-port.md`: the trial cherry-picks of our commits and of PR #5571, with every
  conflict region.
- [F3] `handoff-material/facts-4444.md`: issue #4444 against today's main, the three merged rounding PRs,
  issue #4600, the comparison of the two issues, and the TVD table.
- [F4] `handoff-material/facts-method.md`: the method of issue #5433 as a procedure, what it leaves unsaid,
  the tools in the repository and in our folders, and the shortest TVD procedure for our kernel.
- [F5] `handoff-material/facts-parta-options.md`: the tile-product counts, the options, the measured stake,
  the measured numerics, and the unit-level experiment.
- [F6] `handoff-material/facts-stack.md`: the PR stack, the age of the model's branch, the GDN files at three
  commits, and the three candidate bases.
- [D1] `drafts/comment-4444-draft.md`: a draft comment for our issue #4444. Not posted.
- [D2] `drafts/comment-5433-draft.md`: a draft for the GDN owner's issue. Not posted.
- [H1] `/home/jhan/workspace/intel-AMX/GDN/status/handoff-gdn-pr-split-20261122.md`. Its section 0 holds the
  news of 2026-11-23. Its section 7 holds the build tags, the campaign scripts and the old values.
- [P1] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/` (`build.sh`, `campaign.sh`, `unit-tests.sh`,
  `token-check.sh`, `logit-margin.sh`, `logit_summary.py`, `bench/`) and its results in
  `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/`.
- [P2] `/home/jhan/workspace/intel-AMX/exec/gdn-20261120/` (`run-one.sh`, `models.gdn.yaml`) and
  `/home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh`.
- [P3] `/home/jhan/workspace/intel-AMX/exec/dd/` (`dd_logits_step.py`, `dd_first_divergence.py`),
  `/home/jhan/workspace/intel-AMX/exec/td-20261016/`, the per-step files in
  `/home/jhan/workspace/intel-AMX/exec/results/td-20261016/`, `td2-20261016/` and
  `glimext-20261018/margin/`, and the report
  `/home/jhan/workspace/intel-AMX/token-divergence-4444/token-divergence-issue4444-report.html`.
- [P4] `/home/jhan/.claude/skills/plain-english/SKILL.md`, `/home/jhan/.claude/skills/cpp-coding-guide/SKILL.md`,
  `/home/jhan/.claude/CLAUDE.md` and `/home/jhan/workspace/intel-AMX/CLAUDE.md`.
- [P5] `/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/MEMORY.md` is the index of the
  agent's memory notes. Notes used here: `gdn-amx-project.md`, `delphi-3b35-default-server.md`,
  `i4444-root-cause-campaign.md`, `no-names-in-github-issues.md`, `worktree-prune-nfs-trap.md`,
  `nfs-attr-cache-build-trap.md`.
