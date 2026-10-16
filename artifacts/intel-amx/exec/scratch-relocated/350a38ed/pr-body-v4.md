## Short version

`save_k` takes the caller's worker index, and the main thread (worker 0) and the main helpers (workers 1 .. n_workers - 1) call it at the same statement of the generated code. `save_k_helper` is removed. The K store window protocol, the stored bytes and the kernels are those of the PR #4424 head.

## Background

This draft PR targets PR #4424's branch `jhan-amx-vnniK` at its head 6b939d25d2. It answers the PR #4424 review question "Why do we need to introduce a new function for this? Why not simply extend `save_k` itself with a `worker_ix` argument and call it consistently from both the main thread and the helpers?" [https://github.com/positron-ai/tron/pull/4424#discussion_r4065141577]. This PR replaces PR #4774 (the same change, against the previous PR #4424 head).

## Words used here

| Term | Meaning |
|---|---|
| PR #4424 | "VNNI K": the K cache (the attention key rows kept per token) of 128-dimension heads, stored in the AMX VNNI layout, with the shared block save (the main helpers store part of every 16-token K block together with the main thread). Branch `jhan-amx-vnniK`, head 6b939d25d2. That head contains main at be0d5565b3. |
| PR #4774 | The same change as one commit (f52d634c32) on the previous PR #4424 head 30c4ac82cb. This PR merges that commit onto the current head. |
| save_k | The function in `h/tron/models/model.hpp` that copies the K rows of one pass (one forward step of a batch of tokens) into the KV cache (the per-token key and value rows that attention reads), once per layer (transformer block) per pass. |
| K store window | The protocol described in the comment block Note [Shared block save] in `model.hpp`. The main thread cuts the pass into work units (runs of consecutive tokens inside one 16-token block of a page). It then opens a window (the span in which the helpers may claim units). Every thread claims units from one shared counter. The main thread joins the helpers (waits until every helper reports that it is finished). |
| generated plugin | The model code that the code generator (`ingest/src/TronCpp.hs`) emits from the ingested model. |
| main thread, main helpers | In a generated plugin, `run()` runs on the main thread, and `run_main_help(q_batches, worker_ix, n_workers)` runs on each helper thread. The main thread is worker 0. The generated kernel calls already pass 0 for the main thread. |
| n_workers | The thread count of one generated plugin run: the main thread plus its main helpers. `run_main_help` receives it. The handwritten plugins use the default 1. |
| KV-writing operation | An attention operation that writes the K and V rows of the pass's tokens into the KV cache. |
| AMX, VNNI | Intel Advanced Matrix Extensions (the tile instruction set) and the pair-interleaved K layout the tile multiply reads. |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels. |
| row-major build | A build with `TRON_K_VNNI=OFF`: K stays row-major and the K store is never shared. |

## What changes

- `h/tron/models/model.hpp`:
  - Both `save_k` overloads take `size_t worker_ix = 0, size_t n_workers = 1` after the K buffer. `save_k_impl` asserts `worker_ix < n_workers`. It computes `is_main = worker_ix == 0` once and tests it at three points: the early return of an unshared store, open-or-wait, leave-or-join.
  - Worker 0 cuts the work units, resets the counters, opens the window, claims units and joins the helpers. It then marks the tokens (raises each token's KV completion count in its page) and credits the hardware queue (advances the dispatch counter of the FPGA attention path, Note [GOF dispatch synchronization] in `model.hpp`).
  - A worker 1 .. n_workers - 1 waits for its window, claims units, increments `finished` (the count of helpers that are done) and returns.
  - When the store is not shared, a helper returns at once and worker 0 stores every row itself. `k_store_shared` is false for a pass of at most 16 items (one K block, such as a decode step), for one worker, for more than 128 workers (the size of the per-helper window table) and in the row-major build.
  - The claim loop, every memory order and the join watchdog (`k_join_timeout_s`: the main thread aborts after 120 s of waiting for the helpers) are those of the PR #4424 head. The two `save_k_helper` overloads are removed. Note [Shared block save] and the comments name the single entry point.
- `ingest/src/TronCpp.hs`: the generated `run()` calls `save_k<geometry, op>(q_batch->outer_batch, k, 0, n_workers)` and the generated `run_main_help` calls `save_k<geometry, op>(q_batch->outer_batch, k, worker_ix, n_workers)` at the same statement position. The literal 0 for the main thread is the one `kernelCall` already emits for the main-side kernel calls.
- `ingest/test/LoopyTronSpec.hs`: the two generated-code checks expect two `save_k` calls per KV-writing operation. The main-side call text ends in `,k,0,n_workers);`. The helper-side call text ends in `,k,worker_ix,n_workers);`. The two `save_k_helper` count checks are removed.
- `t/t_llama_unit.cpp`: the three-thread section of the `save_k` test case calls `save_k` on every thread, the helpers with their worker index and the main thread with `main_worker_ix` (0). The check lambda of the test case also verifies the K marks (the per-token KV completion count in the page, which the K save and the V save each raise by one). Three checks:
  - `save_k` marks K of every job (batch entry) with KV work exactly once.
  - K alone does not complete the token (completion needs the V mark too).
  - A job without KV work has no mark.
  A helper that ran the main thread's mark loop would fail these checks.
- Not changed: the handwritten plugins (`h/tron/plugins/llama.hpp`, `t/heterogeneous_scheduler_compile.cpp`) keep their calls and take the defaults (worker 0 of 1: every row on the calling thread). `save_v` is unchanged.

## Test

Head 45e6bb266d (the merge commit). Comparator: the PR #4424 head 6b939d25d2 (the first parent).

### Build and unit tests on delphi-3bda (the Intel AMX test machine)

- Question: does the merged head build and pass the unit tests in both K layouts, and does the generated code carry the two `save_k` call forms and no `save_k_helper`?
- Where: our half of the machine (the socket reserved for this work, the machine is shared) with the fake device (the test device that stands in for the FPGA), on 2026-10-08.
- Cells (one cell = one build or check):
  - VNNI build (CMake preset `native`, AMX dispatch on, ingest models on) with `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics` (also under the kill switch), `t_llama_unit`, `t_heterogeneous_scheduler`, `t_phase1_integration`.
  - The generated-plugin text (the plugin headers under `gen/src/tron/h/tron/plugins/` of the VNNI build): every `save_k<...>(...);` call, classified by its last two arguments, compared with the `save_v<...>(...);` count.
  - The ingest Haskell tests (`bin/ingest-cabal test`).
  - The row-major build with the five layout-independent tests.
  - clang-format, fourmolu (the Haskell formatter) and `git diff --check`.
- Verdict rule, all three:
  - every test passes
  - the plugin text has one main-side and one helper-side `save_k` call per KV-writing operation and no `save_k_helper`
  - the format checks pass
- Status: done 2026-10-08, verdict pass (every cell in the table).

| check | result |
|---|---|
| VNNI build + 6 unit tests | pass: `t_k_vnni_layout` 1011650 assertions / 5 cases, `t_amx_dispatch_dtype` 1612 / 1, `t_amx_numerics` 4621 / 5 on real AMX (no "AMX unavailable" line), `t_llama_unit` 251755 / 64, `t_heterogeneous_scheduler` 2783 / 3, `t_phase1_integration` 2124 / 64 |
| `t_amx_numerics` under the kill switch | pass: 2060 assertions / 5 cases with the three "AMX unavailable" warnings (the AVX path) |
| generated plugin text | pass: in each of the 19 generated plugins the number of main-side `save_k` calls (last two arguments `0, n_workers`) and the number of helper-side `save_k` calls (last two arguments `worker_ix, n_workers`) both equal the number of KV-writing operations (counted as `save_v` calls, which the generator emits once per KV-writing operation on the main side only). No `save_k` call has any other last two arguments. No plugin names `save_k_helper`. The per-plugin counts are in the table below. |
| ingest Haskell tests | pass: 1 of 1 test suites |
| row-major build + 5 unit tests | pass: `t_k_vnni_layout` 1011650 / 5, `t_amx_dispatch_dtype` 1612 / 1, `t_amx_numerics` 4621 / 5, `t_llama_unit` 251670 / 64, `t_heterogeneous_scheduler` 2783 / 3 |
| clang-format, fourmolu, `git diff --check` | pass (all three return 0) |

<details>
<summary>Generated plugin counts at 45e6bb266d (kv_ops = `save_v` calls, main_k = main-side `save_k` calls, helper_k = helper-side `save_k` calls, other_k = `save_k` calls with other last two arguments, helper_fn = `save_k_helper` mentions)</summary>

| plugin | kv_ops | main_k | helper_k | other_k | helper_fn |
|---|---|---|---|---|---|
| gemma_4_12b_it_permuted | 48 | 48 | 48 | 0 | 0 |
| gemma_4_31b_it | 60 | 60 | 60 | 0 | 0 |
| gemma_4_a4b_it | 30 | 30 | 30 | 0 | 0 |
| gemma_4_e4b_it | 24 | 24 | 24 | 0 | 0 |
| gemma_4_e4b_it_permuted | 24 | 24 | 24 | 0 | 0 |
| ingested_chinese_alpaca_2_7b | 32 | 32 | 32 | 0 | 0 |
| ingested_gemma_3_27b_it | 62 | 62 | 62 | 0 | 0 |
| ingested_gemma_3_4b_it | 34 | 34 | 34 | 0 | 0 |
| ingested_gpt_oss_120b | 36 | 36 | 36 | 0 | 0 |
| ingested_gpt_oss_20b | 24 | 24 | 24 | 0 | 0 |
| ingested_granite_3p3_8b | 40 | 40 | 40 | 0 | 0 |
| ingested_llama_3p1_8b | 32 | 32 | 32 | 0 | 0 |
| ingested_llama_3p1_8b_permuted | 32 | 32 | 32 | 0 | 0 |
| ingested_meta_models_Muse_Glimmer_30B | 52 | 52 | 52 | 0 | 0 |
| ingested_meta_models_Muse_Glimmer_30B_permuted | 52 | 52 | 52 | 0 | 0 |
| ingested_mixtral_8x7b | 32 | 32 | 32 | 0 | 0 |
| ingested_phi_4 | 40 | 40 | 40 | 0 | 0 |
| qwen_3_30b_moe | 48 | 48 | 48 | 0 | 0 |
| qwen_3_4b_instruct_2507 | 36 | 36 | 36 | 0 | 0 |

</details>

### Token identity and performance (not run at this head)

- Question: does this head generate the same tokens as the comparator, and are TPS (decode tokens per second per user) and TTFT (time to the first token) inside the run-to-run band?
- Comparator: the PR #4424 head 6b939d25d2.
- Status: not run. The diff against 6b939d25d2 touches no kernel and no stored byte. [The same change was measured at the earlier PR #4424 head: PR #4774, section Test.]

## Open items

- PR #4737 (the fix for issue #4500, the FPGA-attention TPS loss under VNNI K, based on the PR #4424 branch) still calls `save_k_helper` (15 mentions in 4 files) and has merge conflicts with the branch head. After this change is merged into `jhan-amx-vnniK`, PR #4737 needs a merge of the branch head and the same replacement of its `save_k_helper` calls by `save_k` calls with the worker index.
- The PR #4424 description names `save_k_helper` in three places (the sharing bullet, the code-generator bullet and the `LoopyTronSpec.hs` test bullet). jhan edits that description on GitHub.
- PR #4774 is to be closed in favor of this PR (jhan).


🤖 Generated with [Claude Code](https://claude.com/claude-code)
