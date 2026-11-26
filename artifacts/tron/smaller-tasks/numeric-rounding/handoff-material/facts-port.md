# Trial applications of our GDN commits and of PR #5571

Written 2026-11-23 by a fact-reading agent. Nothing was built and nothing was run except git and gh (read only).

## Short version

Every trial cherry-pick stopped with conflicts: no base takes our commits cleanly, and the model's branch does not take PR #5571 cleanly.
PR #5571's code commit conflicts with our Part 0 + Part A commit in 3 files and 14 conflict regions, and the same 14 regions appear when it is applied to the model's branch alone, so the cause is the age of the model's branch and not mainly our code.
The merge also leaves two mismatches in our code without any conflict marker: our chain kernel still rounds the value to bf16, and our AMX block kernel still keeps only the upper 16 bits of the normalized key and query, which PR #5571 stops rounding.

## Words used here

- **tron**: the C++ inference program (repository positron-ai/tron).
- **GDN**: GatedDeltaNet, the recurrent layer of the model Qwen3.5 4B.
- **FP32**: the 32-bit floating-point format. **bf16**: bfloat16, a 16-bit floating-point format with 8 significant bits. A bf16 value has the same bit pattern as the upper 16 bits of an FP32 value.
- **token kernel**: the function `gdn_recurrence`. It advances the layer's state by one token.
- **chain kernel**: our function `gdn_recurrence_chain` (Part 0). It advances the state over several tokens. It is written to give the same bits as the token kernel.
- **AMX block kernel**: our kernel `amx_gdn_k128v128` (Part A, file `src/tron/kernels/amx_gdn.cpp`). It advances 32 tokens at a time with AMX (a CPU instruction set for matrix products). Its results are close to the chain kernel's results, not equal.
- **window**: our struct `gdn_recurrence_window`. It holds the prepared inputs of up to 32 tokens for the chain kernel and the AMX block kernel.
- **executor**: the class `gdn_rolling_executor` in `h/tron/models/gdn_rolling_executor.hpp`. Its `step()` runs the token kernel for one token. Our `advance()` runs the chain kernel or the AMX block kernel for a run of tokens. Its `postprocess` function normalizes and gates the kernel's output.
- **model's branch**: the head of PR #3696 ("Register Qwen3.5 4B"), commit 72e1191804.
- **conflict region**: one block between a `<<<<<<<` line and a `>>>>>>>` line that git writes into a file it could not merge.
- **"deleted by us"**: git's label for a file that the picked commit changes and that does not exist on the base.
- **squash commit**: one commit that holds the changes of several commits.
- Commit ids used here:
  - f454423b09 = main today.
  - 127a662083 = head of PR #3221 (main plus 4 commits).
  - 59429b0955 = the code commit of PR #5571. 69cc70fae0 = the head of PR #5571 (one more commit that reformats 2 test lines).
  - 72e1191804 = the model's branch.
  - 0d69ef3ce8 = our counters commit. 775bba7661 = our Part 0 + Part A commit. 882e5322f1 = our Part B commit (not part of these trials).

## How the trials were run

- The scratch clone is `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/port-trials/tron-trial`. It was made with `git clone --shared --no-checkout /home/jhan/workspace/tron <scratch>/tron-trial` [R1].
- In the clone only: `user.name` is "trial", `user.email` is "trial@example.invalid", and the push URL of `origin` is set to the word `DISABLED-no-push` [R1].
- All nine commit ids of the setting answer `commit` to `git cat-file -t` in the clone [R2].
- git 2.34.1 has no `--no-verify` option for `cherry-pick`. Every git command of a trial ran with `-c core.hooksPath=/dev/null`, so no hook could run [R1].
- No cherry-pick reached the commit step. Every one stopped with conflicts and was ended with `git cherry-pick --abort` [R3].
- One trial is one call of the script `run_trial.sh <trial> <base> <commit>...` [R1]. For each trial the script runs these commands, where `G` stands for `git -C <scratch>/tron-trial -c core.hooksPath=/dev/null` and the environment holds `GIT_LFS_SKIP_SMUDGE=1`:

```
G cherry-pick --abort          # only clears a leftover state; error ignored
G reset -q --hard
G checkout -q -f -B trial/<trial> <base>
G clean -fdxq
G cherry-pick <commit>         # exit status recorded
G status --porcelain           # recorded
grep -c '^<<<<<<<' <file>      # for each unmerged file
G cherry-pick --abort
```

- After the last trial the clone has 0 changed files and no cherry-pick in progress. The shared repository has 0 refs with "trial" in the name. Our worktree is still at 882e5322f1 [R4].

## Facts about the bases that explain the results

1. The model's branch is an older copy of the stack below it.
   - The model's branch was committed on 2026-11-17. The head of PR #3221 was committed again on 2026-11-23, on top of main of 2026-11-23 [R5].
   - The model's branch is 21 commits ahead of its merge base with main (54476c6581, 2026-11-16), and main is 49 commits ahead of that merge base [R6].
   - The model's branch holds its own older copy of the commit "Parallelize the GDN recurrence across heads" (2ce07371db). The head of PR #3221 is the newer copy of that commit (127a662083) [R6].
2. Only the model's branch can run Qwen3.5 4B.
   - The entry `qwen_3p5_4b` in `config/models.yaml` exists at 72e1191804. It does not exist at 69cc70fae0, at 127a662083 or at f454423b09 [R7].
   - By commit subject, 11 of the 21 commits of the model's branch have no counterpart in the history of 127a662083. They include the registration and 5 commits that change files under `ingest/` (the step that turns a model into tron code) [R6]. A commit with a changed subject would not be found by this check.
3. Main has no file `h/tron/models/gdn_execution.hpp`.
   - That file holds `run_gdn_operation` (the function that runs one GDN operation over the scheduler's chains). Our counters and our `advance()` call are hooked into it.
   - The file is added by commit 1f705f0140, which is one of the 4 commits of PR #3221 on top of main [R8].
   - Main's executor has no head groups and no working copy: the names `gdn_checkpoint_access` and `value_heads_per_group` occur 0 times in main's `gdn_rolling_executor.hpp`, and 9 times and 16 times at 127a662083 [R9].
4. The model's branch still rounds the three history entries of the convolution when it reads them.
   - Main dropped these three roundings in commit 2559c133df ("Stop rounding GDN convolution history entries on read (#5462)") [R10].
   - So the kernel header has 18 bf16 rounding calls at 72e1191804 and 15 at 127a662083 [R11].
5. GitHub agrees with the commit ids of the setting. PR #5571 is an open draft with head 69cc70fae0. PR #3221 is open with head 127a662083. PR #3696 is open with head 72e1191804 and was last updated on 2026-11-18 [R12].

## T1: our commits on main (f454423b09)

### T1a: `run_trial.sh T1a f454423b09 0d69ef3ce8`

- `git cherry-pick 0d69ef3ce8`: exit status 1.
- `git status --porcelain`:

```
M  README.stats.md
DU h/tron/models/gdn_execution.hpp
A  h/tron/models/gdn_stats.hpp
UU h/tron/models/model.hpp
UU ingest/src/TronCpp.hs
M  t/CMakeLists.txt
UU t/t_gated_delta_net.cpp
A  t/t_gdn_stats.cpp
```

- Conflict regions: `h/tron/models/model.hpp` 1, `ingest/src/TronCpp.hs` 1, `t/t_gated_delta_net.cpp` 2.
- "deleted by us": `h/tron/models/gdn_execution.hpp`. "deleted by them": none. "added by them": none.
- What the conflicts are about: main has no `gdn_execution.hpp`, so the counters have no function to hook into (fact 3). The other regions are our added include lines, the generator function `gdnExecutionCall` in `TronCpp.hs` (30 lines, of which our commit changes 4; main does not have the function), and a 568-line block of the test file (our 135 added lines together with replay tests of the model's branch that main does not have) [R13].

### T1b: `run_trial.sh T1b f454423b09 775bba7661`

- `git cherry-pick 775bba7661`: exit status 1.
- `git status --porcelain`:

```
M  CMakeLists.txt
M  README.ci.md
M  h/tron/kernels/amx_attn_iface.hpp
A  h/tron/kernels/amx_gdn_iface.hpp
M  h/tron/kernels/gated_delta_net.hpp
DU h/tron/models/gdn_execution.hpp
UU h/tron/models/gdn_rolling_executor.hpp
DU h/tron/models/gdn_stats.hpp
UU h/tron/models/model.hpp
M  src/tron/CMakeLists.txt
M  src/tron/kernels/amx_attn.cpp
A  src/tron/kernels/amx_gdn.cpp
M  t/CMakeLists.txt
A  t/t_amx_gdn_numerics.cpp
UU t/t_gated_delta_net.cpp
```

- Conflict regions: `h/tron/models/gdn_rolling_executor.hpp` 12, `h/tron/models/model.hpp` 2, `t/t_gated_delta_net.cpp` 1.
- "deleted by us": `h/tron/models/gdn_execution.hpp` and `h/tron/models/gdn_stats.hpp`. "deleted by them": none. "added by them": none.
- What the conflicts are about: main's executor is the form before head groups (fact 3), so our `advance()`, our working copy in the slice layout and our `postprocess` meet code with other names in 12 places [R13]. `gdn_stats.hpp` is "deleted by us" only because this trial skips the counters commit that adds the file.
- The kernel header `h/tron/kernels/gated_delta_net.hpp` merged without a conflict. The chain kernel is added below the token kernel as plain new text.

### T1c: `run_trial.sh T1c f454423b09 0d69ef3ce8 775bba7661`

- The first cherry-pick stops as in T1a (exit status 1). The second commit was not attempted, because the task says to resolve nothing.

## T2: our commits on the head of PR #3221 (127a662083)

### T2a: `run_trial.sh T2a 127a662083 0d69ef3ce8`

- `git cherry-pick 0d69ef3ce8`: exit status 1.
- `git status --porcelain`:

```
M  README.stats.md
UU h/tron/models/gdn_execution.hpp
A  h/tron/models/gdn_stats.hpp
UU h/tron/models/model.hpp
UU ingest/src/TronCpp.hs
M  t/CMakeLists.txt
UU t/t_gated_delta_net.cpp
A  t/t_gdn_stats.cpp
```

- Conflict regions: `h/tron/models/gdn_execution.hpp` 4, `h/tron/models/model.hpp` 1, `ingest/src/TronCpp.hs` 1, `t/t_gated_delta_net.cpp` 1.
- "deleted by us", "deleted by them", "added by them": none.
- What the conflicts are about: `run_gdn_operation` has another signature at 127a662083 (it takes `geometry`; on the model's branch it takes `operation_descriptor` and `kernel_spec`), and the generator in `TronCpp.hs` calls it as a method of `outer_state` and not as the free function `tron::run_gdn_operation` [R13]. The other regions are include lines and the comment above the function. All 7 regions are short: the longest side has 23 lines.

### T2b: `run_trial.sh T2b 127a662083 775bba7661`

- `git cherry-pick 775bba7661`: exit status 1.
- `git status --porcelain`:

```
M  CMakeLists.txt
M  README.ci.md
M  h/tron/kernels/amx_attn_iface.hpp
A  h/tron/kernels/amx_gdn_iface.hpp
M  h/tron/kernels/gated_delta_net.hpp
UU h/tron/models/gdn_execution.hpp
UU h/tron/models/gdn_rolling_executor.hpp
DU h/tron/models/gdn_stats.hpp
UU h/tron/models/model.hpp
M  src/tron/CMakeLists.txt
M  src/tron/kernels/amx_attn.cpp
A  src/tron/kernels/amx_gdn.cpp
M  t/CMakeLists.txt
A  t/t_amx_gdn_numerics.cpp
UU t/t_gated_delta_net.cpp
```

- Conflict regions: `h/tron/models/gdn_execution.hpp` 3, `h/tron/models/gdn_rolling_executor.hpp` 5, `h/tron/models/model.hpp` 2, `t/t_gated_delta_net.cpp` 1.
- "deleted by us": `h/tron/models/gdn_stats.hpp` (the trial skips the counters commit). "deleted by them": none. "added by them": none.
- What the conflicts are about: in the executor, 3 regions come from our working copy in the slice layout (against the base's member `recurrent_state_copy`) and from our added function `block_kernel_available()`, and 2 regions are our pointer form of `postprocess` against the base's tensor form [R13]. The regions in `gdn_execution.hpp`, `model.hpp` and the test file are places where our commit extends the counters code that this trial did not apply.
- The kernel header merged without a conflict.

### T2c: `run_trial.sh T2c 127a662083 0d69ef3ce8 775bba7661`

- The first cherry-pick stops as in T2a (exit status 1). The second commit was not attempted.

## T3: our commits on the head of PR #5571 (69cc70fae0)

### T3a: `run_trial.sh T3a 69cc70fae0 0d69ef3ce8`

- `git cherry-pick 0d69ef3ce8`: exit status 1.
- `git status --porcelain`: the same 8 lines as in T2a.
- Conflict regions: `h/tron/models/gdn_execution.hpp` 4, `h/tron/models/model.hpp` 1, `ingest/src/TronCpp.hs` 1, `t/t_gated_delta_net.cpp` 1.
- "deleted by us", "deleted by them", "added by them": none.
- What the conflicts are about: the text of all 7 regions is identical to T2a on both sides [R14]. PR #5571 changes none of the lines that the counters commit touches.

### T3b: `run_trial.sh T3b 69cc70fae0 775bba7661`

- `git cherry-pick 775bba7661`: exit status 1.
- `git status --porcelain`: the same 15 lines as in T2b.
- Conflict regions: `h/tron/models/gdn_execution.hpp` 3, `h/tron/models/gdn_rolling_executor.hpp` 6, `h/tron/models/model.hpp` 2, `t/t_gated_delta_net.cpp` 1.
- "deleted by us": `h/tron/models/gdn_stats.hpp` (the trial skips the counters commit). "deleted by them": none. "added by them": none.
- What the conflicts are about: the regions in `gdn_execution.hpp`, `model.hpp` and the test file have the same text as in T2b [R14]. The executor has 6 regions: the 3 of T2b for the working copy and `block_kernel_available()`, and 3 where PR #5571's `postprocess` without the three roundings meets our pointer form of `postprocess`, which still has them [R13].
- The kernel header merged without a conflict, and that is the trap. The merged file has PR #5571's token kernel without the value rounding, and at merged line 437 it has our line `round_chunk_to<bf16>(value.chunk(chunk)).data` in `gdn_prepare_recurrence_token` [R15]. See T5.

### T3c: `run_trial.sh T3c 69cc70fae0 0d69ef3ce8 775bba7661`

- The first cherry-pick stops as in T3a (exit status 1). The second commit was not attempted.

## T4: PR #5571 on our Part 0 + Part A commit (775bba7661)

### Result

- Command: `run_trial.sh T4 775bba7661 59429b0955 69cc70fae0`.
- `git cherry-pick 59429b0955`: exit status 1. The second commit, 69cc70fae0, was not attempted in this sequence.
- `git status --porcelain`:

```
UU h/tron/kernels/gated_delta_net.hpp
UU h/tron/models/gdn_rolling_executor.hpp
UU t/t_gated_delta_net.cpp
```

- Conflict regions: `h/tron/kernels/gated_delta_net.hpp` 1, `h/tron/models/gdn_rolling_executor.hpp` 4, `t/t_gated_delta_net.cpp` 9. Total: 3 files, 14 regions.
- "deleted by us", "deleted by them", "added by them": none.
- What the conflicts are about: the single region in the kernel header is the comment block "Note [GatedDeltaNet BF16 rounding points]", and all code changes of PR #5571 in that header merged by themselves. The executor regions are the comment about postprocessing and the three roundings in `postprocess`, and the 9 regions of the test file are test code of the base that PR #5571 rewrites [R13].
- Comparison with T6 (the same commit on the model's branch without our commits): the same 14 regions appear there. 11 of them have identical text on both sides. In the other 3 (executor regions 1 to 3) our commit changed the text of our side [R14]. So most of this conflict belongs to the model's branch, not to our commit.
- Extra trial T4b: `run_trial.sh T4b 775bba7661 69cc70fae0` (the second commit alone). Exit status 1, 1 file (`t/t_gated_delta_net.cpp`) with 1 region of 2 lines per side. The commit only reformats a line that 59429b0955 adds [R16].

### Conflict region in `h/tron/kernels/gated_delta_net.hpp`

**Region 1** (merged file lines 26-77; our side 19 lines, PR #5571 side 30 lines)

Our side (HEAD = 775bba7661):

```cpp
// Qwen GatedDeltaNet activations are BF16 values, which C++ may carry as FP32.
// The kernels round to BF16 where the reference does:
// gated_delta_net_with_state in ingest/runtime/tron_ingest_runtime/ops.py,
// which follows Transformers' PyTorch fallback. Convolution rounds the three
// history entries and the current input, starts an FP32 sum at +0.0, adds the
// products oldest tap first, rounds that sum once, and rounds again after SiLU.
// Query/key normalization rounds the query and the key to BF16 and rounds again
// after each square, the reduction, the epsilon operand and its addition, the
// reciprocal square root, and the normalized multiply. The squares are added
// per lane and then across lanes in FP32; that order differs from PyTorch's, so
// only the rounded total is matched. The reciprocal square root is computed in
// FP32 and rounded once. Beta rounds to BF16 before and after sigmoid. The
// recurrence rounds its five runtime inputs to BF16: query and key in
// normalization, value, the decay input, and the update input in beta. A_exp
// and dt_bias are used as given. The recurrent matrix, decay, rank-one state
... (4 more lines not quoted)
```

PR #5571 side (59429b0955):

```cpp
// A Qwen GatedDeltaNet layer's input activations are BF16 values, which C++
// may carry as FP32. The kernels round to BF16 those they read, so an FP32
// value gives the result of the BF16 value it rounds to: convolution rounds
// its current input, and the recurrence rounds its decay input and, in beta,
// its update input. prepare_gdn_conv1d_weights rounds the convolution weights.
// Every value the kernels compute from those is FP32.
// The reference is gated_delta_net_with_state in
// ingest/runtime/tron_ingest_runtime/ops.py, which follows Transformers'
// PyTorch fallback. On BF16 tensors it also holds BF16 at the convolution's
// sum, at the convolution's SiLU output, after each step of query/key
// normalization, and at beta, so the kernels' results differ from its results
// by that rounding.
// Convolution starts an FP32 sum at +0.0, adds the products oldest tap first,
// and applies SiLU to that sum. It uses the three history entries as they are;
// Note [Prepared GatedDeltaNet convolution] says what they must hold.
... (15 more lines not quoted)
```

What merged by itself in this file, read from the merged copy [R17]:

- `normalize_gdn` has no rounding left (merged lines 211 to 227).
- `gdn_beta` is `return sigmoid(round_to<bf16>(update_input));` (merged line 231).
- The token kernel reads the value without rounding: `fp32s const value_values = value.chunk(value_head * n_value_chunks + chunk);` (merged line 315).
- The convolution no longer rounds its sum or its SiLU result: `output.store_chunk(chunk, swish(sum));` (merged line 184).
- Our chain kernel text is unchanged: merged lines 337 to 648 are identical to lines 309 to 620 at 775bba7661.

### Conflict regions in `h/tron/models/gdn_rolling_executor.hpp`

**Region 1** (merged file lines 153-172; our side 8 lines, PR #5571 side 9 lines)

Our side (HEAD = 775bba7661):

```cpp
// value suffix in the convolution buffer and writes a separate output tensor.
// Postprocessing reuses that tensor in place. On a working copy the recurrence
// reads the value from the window, rounded to BF16, and writes the output rows
// of the window. Postprocessing reuses those rows in place. See Note
// [GatedDeltaNet chain recurrence]. Postprocessing follows
// Qwen3NextRMSNormGated. Recurrent output, RMS-normalized output,
// normalization-weight output, and the final gated output are rounded to BF16
// in that order. RMS normalization and output-gate SiLU are evaluated in FP32.
```

PR #5571 side (59429b0955):

```cpp
// value suffix in the convolution buffer and writes a separate output tensor,
// which postprocessing reads. Postprocessing follows Qwen3NextRMSNormGated: it
// RMS-normalizes each value head of the recurrence's output, multiplies by the
// output normalization weight and by SiLU of the output gate, and rounds that
// product to BF16, so an FP32 output row holds the values a BF16 row stores.
// It rounds the output gate where it reads it; everything else before the
// final rounding is FP32. The reference also holds BF16 at the recurrence's
// output, at its RMS-normalized value and at the weighted value; see
// Note [GatedDeltaNet BF16 rounding points].
```

**Region 2** (merged file lines 808-812; our side 1 lines, PR #5571 side 1 lines)

Our side (HEAD = 775bba7661):

```cpp
  static void postprocess(float* values,
```

PR #5571 side (59429b0955):

```cpp
  static void postprocess(tensor<group_value_width> const& recurrence_output,
```

**Region 3** (merged file lines 820-834; our side 9 lines, PR #5571 side 3 lines)

Our side (HEAD = 775bba7661):

```cpp
      for (size_t chunk = 0; chunk < value_head_chunks; ++chunk) {
        float* const chunk_values = values + (local_head_chunk + chunk) * chunk_size;
        tron_mm_store_ps(chunk_values,
            round_chunk_to<bf16>(fp32s(tron_mm_load_ps(chunk_values))).data);
      }

      auto const recurrent_head =
          gdn_const_float_view<value_head_dim>(values + local_head * value_head_dim);
      auto const normalized_head =
```

PR #5571 side (59429b0955):

```cpp
      auto const recurrent_head = gdn_const_float_view<value_head_dim>(
          recurrence_output.data.data() + local_head * value_head_dim);
      auto const normalized_expression =
```

**Region 4** (merged file lines 839-846; our side 3 lines, PR #5571 side 2 lines)

Our side (HEAD = 775bba7661):

```cpp
        fp32s const normalized = round_chunk_to<bf16>(normalized_head.chunk(chunk));
        fp32s const weighted = round_chunk_to<bf16>(
            operation.output_norm_weight.chunk(chunk) * normalized);
```

PR #5571 side (59429b0955):

```cpp
        fp32s const normalized = normalized_expression.chunk(chunk);
        fp32s const weighted = operation.output_norm_weight.chunk(chunk) * normalized;
```

Two notes on these regions:

- In region 3 our side uses the variable `local_head_chunk`. The automatic merge already removed its definition (`size_t const local_head_chunk = local_head * value_head_chunks;`, line 802 at 775bba7661), because PR #5571 deletes that line [R17]. So "keep our side" does not compile as it stands. This was read from the text, not compiled.
- Our `postprocess` takes `float* values` because `advance()` passes the output rows of the window (`working.window.output[token]`, line 743 at 775bba7661). PR #5571's `postprocess` takes a tensor reference. A resolution must keep our pointer form and drop the three roundings.

### Conflict regions in `t/t_gated_delta_net.cpp` (9, not quoted in full)

| Region | Merged lines | Our side | PR #5571 side | Subject |
|---|---|---|---|---|
| 1 | 66-84 | 1 line | 15 lines | PR #5571 adds a helper `bf16_word` and the constant `convolution_scale` |
| 2 | 153-179 | 10 lines | 14 lines | convolution check: exact bits on our side, relative tolerance 1e-6 on the PR's side |
| 3 | 231-252 | 19 lines | 0 lines | PR #5571 deletes two PyTorch tables (`torch_weight_bits`, `torch_norm_*`) |
| 4 | 560-585 | 5 lines | 18 lines | comment and setup of the PyTorch convolution test |
| 5 | 1645-1653 | 4 lines | 2 lines | fields of `executor_postprocess_policy` |
| 6 | 1665-1672 | 5 lines | 0 lines | the reference `postprocess` rounds the recurrence output on our side |
| 7 | 1682-1690 | 4 lines | 2 lines | the reference `postprocess` rounds the normalized and the weighted value on our side |
| 8 | 1797-1804 | 5 lines | 0 lines | three "is observable" checks that PR #5571 deletes |
| 9 | 1857-1874 | 3 lines | 12 lines | PR #5571 adds a check that rounding the update input changes beta |

- All 9 regions have identical text in T6 [R14]. None of them is in the test cases that our commit adds.
- The test cases that our commit adds for the chain kernel and the AMX block kernel (from line 2840 of the file at 775bba7661) merged without a conflict marker. The last conflict region ends at merged line 1874.

## T5: places in our code that keep a rounding, or assume one, that PR #5571 removes

Search done: `round_to<bf16>`, `round_chunk_to<bf16>`, `bf16_bits` and "representable" in the five files at 775bba7661. The files `amx_gdn.cpp`, `amx_gdn_iface.hpp`, `t_amx_gdn_numerics.cpp`, `gated_delta_net.hpp` and `gdn_rolling_executor.hpp` are identical at 775bba7661 and at 882e5322f1, so the line numbers hold for both [R18].

### 5a. A rounding call that stays, with no conflict marker

| File:line at 775bba7661 | Code | Why it matters |
|---|---|---|
| `h/tron/kernels/gated_delta_net.hpp:416-418` (merged lines 444-446 in T4, merged line 437 in T3b) | `tron_mm_store_ps(window.value[token] + chunk * chunk_size,` / `round_chunk_to<bf16>(value.chunk(chunk)).data);` in `gdn_prepare_recurrence_token` | The token kernel has the same rounding at lines 286-287 at 775bba7661. PR #5571 removes it there. Ours stays. |

- Before PR #5571 this rounding changes nothing in practice. The value comes from the convolution, and the convolution stores `round_chunk_to<bf16>(swish(sum))` (line 152 at 775bba7661) [R19].
- With PR #5571 the convolution stores `swish(sum)` unrounded (line 173 at 69cc70fae0) [R19]. Then our chain kernel computes with a rounded value and the token kernel computes with the unrounded value.
- The executor uses the token kernel for a chain of one token and `advance()` for a longer chain (`h/tron/models/gdn_execution.hpp:147-149` at 775bba7661) [R20]. So tokens of a prompt run and single tokens would be computed with different values.
- Hypothesis: with PR #5571 applied and this line kept, our tests "GatedDeltaNet advance gives the bytes of step ..." (`t/t_gated_delta_net.cpp:2840` and `:2851` at 775bba7661, byte comparison at `:2803-2812`) fail. Measurement that settles it: build `t_gated_delta_net` on the merged tree and run the cases tagged `[chain]`.

### 5b. Places that have no rounding call but assume a rounding that PR #5571 removes

PR #5571 removes all roundings inside `normalize_gdn`, including the last one, `round_chunk_to<bf16>(result.chunk(chunk) * inverse_norm)` (line 194 at 775bba7661). Our window gets the normalized key and query from that function (lines 400-409 at 775bba7661). The AMX block kernel then reads them as follows [R21].

| File:line at 775bba7661 | Code | Why it matters |
|---|---|---|
| `src/tron/kernels/amx_gdn.cpp:181-186` | `// The upper 16 bits of each FP32 lane: the bf16 bit patterns of 16 values that` / `// are representable in bf16.` / `__m256i bf16_bits(__m512 values) noexcept {` ... `_mm512_srli_epi32(_mm512_castps_si512(values), BF16_SHIFT_16)` | The helper cuts the low 16 bits. It does not round. |
| `src/tron/kernels/amx_gdn.cpp:258-259` | `_mm256_store_si256(reinterpret_cast<__m256i*>(s.kq[token] + first),` / `bf16_bits(_mm512_load_ps(key + first)));` | The normalized key is packed for the tile products. |
| `src/tron/kernels/amx_gdn.cpp:260-262` | `_mm256_store_si256(` ... `bf16_bits(_mm512_load_ps(query + first)));` | The normalized query is packed for the tile products. |
| `src/tron/kernels/amx_gdn.cpp:271-278` | `rows[j] = _mm512_castps_si512(_mm512_load_ps(block.normalized_key + ...));` ... `_mm512_cvtepi32_epi16(_mm512_srli_epi32(rows[i], BF16_SHIFT_16))` | The transposed key is packed with the same shift. This site does not call `bf16_bits`, so a search for that name misses it. |
| `h/tron/kernels/amx_gdn_iface.hpp:47` | `// TDPBF16PS takes bf16 inputs. K and Q hold bf16 values already. S0 and` | The stated contract of the kernel. |
| `h/tron/kernels/amx_gdn_iface.hpp:129-131` | `// Token t's normalized key starts at normalized_key + t * key_stride and holds` / `// KEY_DIM_128 values that are representable in bf16. normalized_query holds` / `// the query in the same way, without the query scale.` | The stated contract of the caller. |
| `h/tron/models/gdn_rolling_executor.hpp:703-707` | `.normalized_key = working.window.normalized_key[0] + key_head * key_head_dim,` / `.normalized_query = working.window.normalized_query[0] + key_head * key_head_dim,` | The executor hands the window's rows to the kernel with no check. |

- The kernel has no check that the key and the query are representable in bf16. Its only refusal test looks at non-finite values and at corrections of 2^100 or more (`amx_gdn.cpp:485-489`, `amx_gdn_iface.hpp:76-85` at 775bba7661) [R21].
- So with PR #5571 the AMX block kernel would compute with a key and a query cut toward zero. The cut is below one bf16 step, which is below 2^-7 of the value (0.78 %, est. from the format, not measured). Rounding to nearest, as today, is within 2^-8 (0.39 %, est.).
- The kernel does have a way to take full FP32 operands: it splits the start matrix and the corrections into three bf16 pieces (`amx_gdn_iface.hpp:47-53` at 775bba7661). It does not do that for the key and the query. Cost and error of doing so: Not verified, no measurement exists.
- The switch `TRON_AMX_GDN_DISABLE=1` turns only this kernel off (`amx_gdn_iface.hpp:87-90` at 775bba7661). The chain kernel then runs every window.
- Hypothesis: with PR #5571 applied and the kernel unchanged, the test "GatedDeltaNet advance with the block kernel stays close to step" (`t/t_gated_delta_net.cpp:2863-2910` at 775bba7661) fails its bounds. The bounds are 1e-5 for the relative L2 error of the matrices, 2 % of outputs that differ, and 2 % of the largest output for the largest difference. Measurement that settles it: build and run that case on an AMX machine.

### 5c. Tests of ours that would keep passing and stop covering the real inputs

| File:line at 775bba7661 | Code | Why it matters |
|---|---|---|
| `t/t_amx_gdn_numerics.cpp:58-60` | `float round_to_bf16(float x) noexcept {` / `return static_cast<float>(tron::bf16(x));` | A local helper. The four search words find 0 matches in this file because of this name. |
| `t/t_amx_gdn_numerics.cpp:89-92` | `window.normalized_key[token][i] =` / `round_to_bf16(static_cast<float>(key[i] / std::sqrt(key_square)));` and the same for `normalized_query` | The test writes rounded keys and queries straight into the window. It does not call `gdn_prepare_recurrence_token`. |
| `t/t_amx_gdn_numerics.cpp:96` | `window.value[token][i] = round_to_bf16(family.value_scale * normal(generator));` | The value is rounded in the test input. |
| `t/t_amx_gdn_numerics.cpp:102` | `window.beta[token][head] = round_to_bf16(0.05f + 0.9f * uniform(generator));` | Beta is rounded in the test input. PR #5571 stops rounding beta after the sigmoid. |
| `t/t_amx_gdn_numerics.cpp:345`, `:352`, `:381` | `round_to_bf16(3e38f)`, `round_to_bf16(0x1p+99f)`, `round_to_bf16(1e30f)` | Inputs of the refusal cases. |

- The error band of the AMX block kernel (`t/t_amx_gdn_numerics.cpp:260-265`: at most 0.2 % of the output words differ, at most 2 bf16 steps for a large output) was measured with rounded keys, queries, values and betas only. No number exists for unrounded inputs.
- `t/t_gated_delta_net.cpp`: the lines that our commit adds contain no `round_to<bf16>`, no `round_chunk_to<bf16>` and no `reference_bf16` [R18]. Our cases there compare `advance()` with `step()`, so they would show the mismatch (5a and 5b) and need no edit for the rounding itself.

### 5d. Places that the cherry-pick does flag with a conflict

- `h/tron/models/gdn_rolling_executor.hpp:805-809` at 775bba7661: the in-place rounding of the recurrence output in our `postprocess` (T4 executor region 3).
- `h/tron/models/gdn_rolling_executor.hpp:818` and `:819-820` at 775bba7661: the rounding of the normalized and of the weighted value (T4 executor region 4).
- `h/tron/models/gdn_rolling_executor.hpp:153-160` at 775bba7661: our comment about postprocessing (T4 executor region 1).

### 5e. Comments of ours that become wrong, with no conflict marker

- `h/tron/kernels/gated_delta_net.hpp:338-342` at 775bba7661: "the value rounded to BF16 ... Preparing a token computes these exactly as gdn_recurrence does."
- `h/tron/models/gdn_rolling_executor.hpp:792-793` at 775bba7661: "They are rounded to BF16 in place."

### 5f. Places that follow PR #5571 with no edit

- `gdn_prepare_recurrence_token` calls the shared helpers `normalize_gdn`, `gdn_decay` and `gdn_beta` (`gated_delta_net.hpp:400-403` and `:420-423` at 775bba7661). The 7 roundings of the normalization and the rounding of beta therefore leave the chain kernel together with the token kernel.
- `advance()` uses the same convolution as `step()` (`convolve_token`, `gdn_rolling_executor.hpp:662` at 775bba7661). The 2 roundings of the convolution leave both paths together.

### 5g. What issue #5433 says about these places

- The issue says: "Six of the seven (after each normalization step) ... come out in this follow-up whatever the measurement says about the other eight." [R22]
- Reading of that text: the six are the roundings after the square, the sum, the epsilon, the addition, the reciprocal square root and the normalized multiply. The seventh is the rounding of the query and key on entry.
- The code comment at 775bba7661 supports this reading. It says the normalization "rounds the query and the key to BF16 and rounds again after each square, the reduction, the epsilon operand and its addition, the reciprocal square root, and the normalized multiply" (`h/tron/kernels/gated_delta_net.hpp:32-34` at 775bba7661). That is one rounding on entry and six after a step.
- The issue does not list the six by line, so the reading is Not verified. The owner of the GDN code can confirm it.
- If the reading is right, the normalized key and query stop being bf16 values in every outcome of the measurement. Then the AMX block kernel (5b) needs a change in every outcome.
- The value rounding (5a) is one of "the other eight". It matters only if the eight are dropped.

## T6: PR #5571's code commit on the model's branch (72e1191804)

- Command: `run_trial.sh T6 72e1191804 59429b0955`.
- `git cherry-pick 59429b0955`: exit status 1. So the change does not apply cleanly to the model's branch.
- `git status --porcelain`:

```
UU h/tron/kernels/gated_delta_net.hpp
UU h/tron/models/gdn_rolling_executor.hpp
UU t/t_gated_delta_net.cpp
```

- Conflict regions: `h/tron/kernels/gated_delta_net.hpp` 1, `h/tron/models/gdn_rolling_executor.hpp` 4, `t/t_gated_delta_net.cpp` 9. Total: 3 files, 14 regions.
- "deleted by us", "deleted by them", "added by them": none.
- What the conflicts are about: the model's branch has older text than PR #5571's base in the rounding comment, in the names inside `postprocess` (`values` and `normalized_head` against `recurrence_output` and `normalized_expression`), and in the test file [R13]. None of the 14 regions is a real disagreement about the arithmetic.

What a measurement build "model's branch + PR #5571" needs:

- Kernel header: resolve 1 comment region. The code merged by itself. Lines 150 to 330 of the merged file differ from PR #5571's file in 4 places only, and all 4 are older text of the model's branch: the three history roundings on read, the form of one assertion, `fp32s{}` against `fp32s(0.0f)`, and one `TRON(noinline)` [R23].
- Executor header: resolve 4 regions (1 comment, 3 code). The 3 code regions are the three roundings of `postprocess`. Our side there has at most 4 lines.
- Test file: 9 regions. They matter only if the test program `t_gated_delta_net` is built.
- The three history roundings on read stay in this build (`gated_delta_net.hpp:133-137` at 72e1191804). They act on values that the kernel itself stored rounded (line 149 at 72e1191804 stores the rounded `current`), so they should not change a model run. This is read from the code. Not verified by a run.
- Hypothesis: PR #5571's convolution test would fail on this build, because its pattern 5 detects "a history entry rounded on read" (PR #5571 side of T4 test region 4). Measurement that settles it: build and run `t_gated_delta_net "[conv1d]"`.
- Not verified: that the resolved headers compile and that `runtron` (tron's command-line tool) builds. Nothing was built in this task.
- The other way round is not cheaper: the head of PR #5571 cannot run Qwen3.5 4B, because the model's registration and 10 more commits are missing there (fact 2).

## Extra trials that the task did not ask for

The sequence "0d69ef3ce8, then 775bba7661" could not be tried, because the first commit never applies. To get one number for both commits together, a squash commit was made in the scratch clone only: `git commit-tree 775bba7661^{tree} -p 72e1191804`, id e678607b1e. It has the tree of 775bba7661 and the parent 72e1191804. The shared repository does not hold this object [R24].

| Trial | Base | Exit status | Unmerged files and conflict regions |
|---|---|---|---|
| T1d | f454423b09 (main) | 1 | `gdn_execution.hpp` "deleted by us"; `gdn_rolling_executor.hpp` 12; `model.hpp` 1; `TronCpp.hs` 1; `t_gated_delta_net.cpp` 2 |
| T2d | 127a662083 (PR #3221) | 1 | `gdn_execution.hpp` 4; `gdn_rolling_executor.hpp` 5; `model.hpp` 1; `TronCpp.hs` 1; `t_gated_delta_net.cpp` 1 |
| T3d | 69cc70fae0 (PR #5571) | 1 | `gdn_execution.hpp` 4; `gdn_rolling_executor.hpp` 6; `model.hpp` 1; `TronCpp.hs` 1; `t_gated_delta_net.cpp` 1 |

- Reading: a port of both commits to the head of PR #3221 meets 12 regions in 5 files. A port to the head of PR #5571 meets 13 regions in 5 files. The one extra region is in `postprocess`.
- A region count is a lower bound of the work. It does not count text that merges and is then wrong, such as the value rounding in T3b.

## Result table

| Trial | Base | Commit(s) picked | Result |
|---|---|---|---|
| T1a | f454423b09 (main) | 0d69ef3ce8 | exit 1; 3 files with 4 conflict regions; 1 file with no target file (`gdn_execution.hpp`, "deleted by us") |
| T1b | f454423b09 (main) | 775bba7661 alone | exit 1; 3 files with 15 conflict regions; 2 files with no target file (`gdn_execution.hpp`, `gdn_stats.hpp`) |
| T1c | f454423b09 (main) | 0d69ef3ce8, then 775bba7661 | stops at the first commit as T1a; second not attempted |
| T2a | 127a662083 (PR #3221) | 0d69ef3ce8 | exit 1; 4 files with 7 conflict regions |
| T2b | 127a662083 (PR #3221) | 775bba7661 alone | exit 1; 4 files with 11 conflict regions; 1 file with no target file (`gdn_stats.hpp`) |
| T2c | 127a662083 (PR #3221) | 0d69ef3ce8, then 775bba7661 | stops at the first commit as T2a; second not attempted |
| T3a | 69cc70fae0 (PR #5571) | 0d69ef3ce8 | exit 1; 4 files with 7 conflict regions (same text as T2a) |
| T3b | 69cc70fae0 (PR #5571) | 775bba7661 alone | exit 1; 4 files with 12 conflict regions; 1 file with no target file (`gdn_stats.hpp`); kernel header merges with the value rounding left in |
| T3c | 69cc70fae0 (PR #5571) | 0d69ef3ce8, then 775bba7661 | stops at the first commit as T3a; second not attempted |
| T4 | 775bba7661 (ours) | 59429b0955, then 69cc70fae0 | exit 1 at the first commit; 3 files with 14 conflict regions; second not attempted |
| T4b (extra) | 775bba7661 (ours) | 69cc70fae0 alone | exit 1; 1 file with 1 conflict region |
| T5 | (reading of T4) | - | 1 rounding call left with no marker; 3 packing sites and 2 contract comments that assume bf16 keys and queries; 1 test file with rounded inputs |
| T6 | 72e1191804 (model's branch) | 59429b0955 | exit 1; 3 files with 14 conflict regions |
| T1d (extra) | f454423b09 (main) | squash e678607b1e | exit 1; 4 files with 16 conflict regions; 1 file with no target file |
| T2d (extra) | 127a662083 (PR #3221) | squash e678607b1e | exit 1; 5 files with 12 conflict regions |
| T3d (extra) | 69cc70fae0 (PR #5571) | squash e678607b1e | exit 1; 5 files with 13 conflict regions |

No trial was clean. No trial reported "deleted by them" or "added by them".

## Not verified

- No conflict was resolved and nothing was compiled. Every statement about what a resolved tree does is read from text.
- The three hypotheses about failing tests (5a, 5b, T6) need a build and a test run.
- The size of the error from cutting the key and the query to 16 bits is an estimate from the number format. A measurement needs a build with PR #5571 and the AMX block kernel, on an AMX machine.
- Which six normalization roundings issue #5433 means was read from one sentence. The owner of the GDN code can confirm it.
- Whether the 11 commits of the model's branch that were not found by subject exist under another subject on the head of PR #3221. `git range-diff 54476c6581..72e1191804 54476c6581..127a662083` would settle it.
- Part B (882e5322f1) was not part of these trials.

## References

Paths below are relative to the scratch directory `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/port-trials` unless they start with `/` or name a commit. The scratch directory can be cleared by a reboot.

- [R1] `run_trial.sh` (the trial script), `tron-trial/.git/config` (identity and push URL), `tron-trial/.git/objects/info/alternates` (points at `/home/jhan/workspace/tron/.git/objects`).
- [R2] `git -C tron-trial cat-file -t <id>` printed `commit` for f454423b09, 72e1191804, 127a662083, 69cc70fae0, 59429b0955, ddf843ad97, 0d69ef3ce8, 775bba7661 and 882e5322f1.
- [R3] `results/<trial>/log.txt` for each trial: the commands, exit statuses, `git status --porcelain` output and region counts. `results/<trial>/cherry-pick-<commit>.log` holds git's own messages.
- [R4] `git -C tron-trial status --porcelain | wc -l` printed 0; `git -C /home/jhan/workspace/tron for-each-ref | grep -c trial` printed 0; `git -C /home/jhan/workspace/ai-runs/tron-gdn-amx rev-parse --short=10 HEAD` printed 882e5322f1.
- [R5] `git log -1 --format='%h %cd' --date=format:'%Y-%m-%d %H:%M %z'`: 72e1191804 2026-11-17 11:42 -0500; 127a662083 2026-11-23 12:47 -0500; f454423b09 2026-11-23 17:37 +0000; 59429b0955 2026-11-21 18:56 -0500; 54476c6581 2026-11-16 07:43 +0000.
- [R6] `git rev-list --left-right --count f454423b09...72e1191804` printed `49 21`. `git log --format='%h %s' 54476c6581..72e1191804` lists the 21 commits. Subjects not found in `git log --format=%s 54476c6581..127a662083`: 6b0e9d2ddc, 4fa8ec8856, be4f6d8b0e, 738b6684c7, 875abe88ec, 5326fa4fd7, 00202eb454, 4e34e13e00, bd9f93bbaa, 451ba42be4, 72e1191804.
- [R7] `git show <id>:config/models.yaml | grep -c -i -E 'qwen3\.5|qwen35|qwen3_5'` printed 5 for 72e1191804 and 0 for 69cc70fae0, 127a662083 and f454423b09. The entry is added by 72e1191804 (`git show 72e1191804 -- config/models.yaml`, 14 added lines).
- [R8] `git ls-tree -r --name-only f454423b09 | grep gdn` has no `gdn_execution.hpp`. `git log --stat f454423b09..127a662083 -- h/tron/models/gdn_execution.hpp` shows 1f705f0140 (111 added lines) and 127a662083.
- [R9] `git show <id>:h/tron/models/gdn_rolling_executor.hpp | grep -c <name>`: `gdn_checkpoint_access` 0 at f454423b09 and 9 at 127a662083; `value_heads_per_group` 0 and 16; `recurrent_state_slices` 0 at 127a662083 and 9 at 775bba7661.
- [R10] `git log --format='%h %s' 54476c6581..f454423b09` contains `2559c133df Stop rounding GDN convolution history entries on read (#5462)`. 72e1191804 `h/tron/kernels/gated_delta_net.hpp:133-137` still has `round_chunk_to<bf16>(tron_mm_loadu_ps(chunk_history ...))` three times.
- [R11] `git show <id>:<file> | grep -o -E 'round_(chunk_)?to<bf16>' | wc -l`: kernel header 18 at 72e1191804, 19 at 775bba7661, 15 at 127a662083, 4 at 69cc70fae0; executor header 5, 5, 5, 2. `gdn_prepared_operation.hpp` has 2 more at 127a662083, which gives the 22 of issue #5433.
- [R12] `gh pr view <n> --repo positron-ai/tron --json state,isDraft,headRefOid,updatedAt` on 2026-11-23: #5571 OPEN, draft, head 69cc70fae0, 3 files, +243 -181 lines; #3221 OPEN, head 127a662083; #3696 OPEN, head 72e1191804, updated 2026-11-18T04:25:52Z. https://github.com/positron-ai/tron/pull/5571 , https://github.com/positron-ai/tron/pull/3221 , https://github.com/positron-ai/tron/pull/3696
- [R13] Copies of the unmerged files with their markers: `results/<trial>/conflicted/<path>`. `show_regions.py <file> <n>` prints both sides of every region.
- [R14] `regions.py same <fileA> <fileB>` compares the regions of two trials. T4 against T6: kernel header 1 of 1 identical; test file 9 of 9 identical; executor region 4 identical, regions 1 and 2 identical on the PR's side only, region 3 different on both sides. T2a against T3a: all 7 identical. T2b against T3b: `gdn_execution.hpp` 3 of 3, `model.hpp` 2 of 2, test file 1 of 1 identical.
- [R15] `results/T3b/automerged/h/tron/kernels/gated_delta_net.hpp`: `grep -n -E 'round_(chunk_)?to<bf16>'` prints 5 lines: 124, 163, 222, 229 and 437.
- [R16] `results/T4b/log.txt`; `git show 69cc70fae0` changes 5 lines of `t/t_gated_delta_net.cpp` (2 added, 3 removed).
- [R17] `results/T4/conflicted/h/tron/kernels/gated_delta_net.hpp` and `results/T4/conflicted/h/tron/models/gdn_rolling_executor.hpp` (the merged copies with markers). `diff <(git show 775bba7661:h/tron/kernels/gated_delta_net.hpp | sed -n '309,$p') <(sed -n '337,$p' <merged copy>)` printed nothing.
- [R18] `git diff --stat 775bba7661 882e5322f1 -- <the five files and amx_gdn_iface.hpp>` printed nothing. `git diff -U0 0d69ef3ce8 775bba7661 -- t/t_gated_delta_net.cpp | grep -E '^\+.*(round_to<bf16>|round_chunk_to<bf16>|reference_bf16)'` printed nothing.
- [R19] 775bba7661 `h/tron/kernels/gated_delta_net.hpp:152`: `output.store_chunk(chunk, round_chunk_to<bf16>(swish(sum)));`. 69cc70fae0 `h/tron/kernels/gated_delta_net.hpp:173`: `output.store_chunk(chunk, swish(sum));`. 775bba7661 `h/tron/models/gdn_rolling_executor.hpp:664-668` passes the convolved buffer as the value.
- [R20] 775bba7661 `h/tron/models/gdn_execution.hpp:147-149`: `gdn_checkpoint_access const access = chain.order.size() == 1 ? gdn_checkpoint_access::in_place : gdn_checkpoint_access::working_copy;`. 775bba7661 `h/tron/models/gdn_rolling_executor.hpp:475` calls `gdn_recurrence` in `step()`; `:547-552` calls `advance_window_with_block_kernel` or `gdn_recurrence_chain` in `advance()`.
- [R21] 775bba7661 `src/tron/kernels/amx_gdn.cpp:181-186, 252-281, 485-489`; 775bba7661 `h/tron/kernels/amx_gdn_iface.hpp:47-53, 76-90, 127-134`; 775bba7661 `h/tron/kernels/gated_delta_net.hpp:179-196, 398-425`.
- [R22] https://github.com/positron-ai/tron/issues/5433 , body as of 2026-11-22T18:38:17Z, section "Where to start".
- [R23] `diff <(sed -n '150,330p' results/T6/conflicted/h/tron/kernels/gated_delta_net.hpp) <(sed -n '140,330p' results/pr5571-gated_delta_net.hpp)`, comment lines left out.
- [R24] `squash-commit-id.txt` holds e678607b1e133c4cac090bcd53b3dd8b2e8f0996. `git -C /home/jhan/workspace/tron cat-file -t e678607b1e` fails with "could not get object info". Logs: `results/T1d/log.txt`, `results/T2d/log.txt`, `results/T3d/log.txt`.
