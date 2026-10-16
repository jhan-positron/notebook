## Short version

`save_k` takes the caller's worker index. The main thread (worker 0) and the main helpers (workers 1 .. n_workers - 1) call the same function at the same point of the schedule. `save_k_helper` is gone. The store protocol, the stored bytes and the kernels are those of the PR #4424 head.

This draft PR targets PR #4424's branch `jhan-amx-vnniK` at its head 6b939d25d2. It answers the PR #4424 review question "Why do we need to introduce a new function for this? Why not simply extend `save_k` itself with a `worker_ix` argument and call it consistently from both the main thread and the helpers?" (https://github.com/positron-ai/tron/pull/4424#discussion_r4065141577). PR #4774 is the same change against the previous PR #4424 head; this PR replaces it.

## Words used here

| Term | Meaning |
|---|---|
| PR #4424 | "VNNI K": the K cache of 128-dimension heads stored in the AMX VNNI layout, with a shared block save (branch `jhan-amx-vnniK`, head 6b939d25d2 = main be0d5565b3 merged, K cache on the typed KV tensors of PR #4557). This PR is one merge commit on top of it. |
| PR #4774 | The same change as one commit (f52d634c32) on the previous PR #4424 head 30c4ac82cb. This PR merges that commit onto the current head. |
| save_k | The function in `h/tron/models/model.hpp` that copies the K rows of one pass into the KV cache, once per layer per pass. |
| K store window | The protocol of Note [Shared block save] in `model.hpp`: the main thread cuts the pass into work units, opens a window, every thread claims units from one counter, the main thread joins the helpers. |
| main thread, main helpers | In a generated plugin, `run()` is the main thread and `run_main_help(worker_ix, n_workers)` runs on the helper threads. Worker 0 is the main thread, as the generated kernel calls already use it. |
| generated plugin | The model code that the code generator (`ingest/src/TronCpp.hs`) emits from the ingested model. |
| AMX, VNNI | Intel Advanced Matrix Extensions (the tile instruction set) and the pair-interleaved K layout the tile multiply reads. |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels. |
| row-major build | A build with `TRON_K_VNNI=OFF`: K stays row-major and the K store is never shared. |

## What changes

- `h/tron/models/model.hpp`: both `save_k` overloads take `size_t worker_ix = 0, size_t n_workers = 1` after the K buffer. `save_k_impl` checks `worker_ix < n_workers` and branches once on `worker_ix == 0`. Worker 0 cuts the work units, resets the counters, opens the window, claims units, joins the helpers, then marks the tokens and credits the hardware queue as before. A worker 1 .. n_workers - 1 waits for its window, claims units, increments `finished` and returns. When the store is not shared (`k_store_shared` false: at most 16 items, one worker, more than 128 workers, or the row-major K layout) a helper returns at once and worker 0 stores every row itself. The claim loop, every memory order and the join watchdog (`k_join_timeout_s`, 120 s) are the ones of the PR #4424 head. The two `save_k_helper` overloads are removed. Note [Shared block save] and the comments name the single entry point.
- `ingest/src/TronCpp.hs`: the generated `run()` calls `save_k<geometry, op>(q_batch->outer_batch, k, 0, n_workers)` and the generated `run_main_help` calls `save_k<geometry, op>(q_batch->outer_batch, k, worker_ix, n_workers)` at the same statement position. The literal 0 for the main thread is the one `kernelCall` already emits for the main-side kernel calls.
- `ingest/test/LoopyTronSpec.hs`: the two generated-code checks expect two `save_k` calls per KV-writing operation (the main-side text ending in `,k,0,n_workers);` and the helper-side text ending in `,k,worker_ix,n_workers);`) and no `save_k_helper`.
- `t/t_llama_unit.cpp`: the three-thread section of the `save_k` test case calls `save_k` on every thread, the helpers with their worker index and the main thread with `main_worker_ix` (0). The check lambda of the test case also verifies the K marks: `save_k` marks every job with KV work once, K alone does not complete the token, and a job without KV work has no mark. A helper that ran the main thread's mark loop would fail it.
- Not changed: the handwritten plugins (`h/tron/plugins/llama.hpp`, `t/heterogeneous_scheduler_compile.cpp`) keep their calls and take the defaults (worker 0 of 1: every row on the calling thread). `save_v` is unchanged.

## Test

Head 45e6bb266d (the merge commit). Comparator: the PR #4424 head 6b939d25d2 (the first parent).

### Build and unit tests on delphi-3bda (running)

- Question: does the merged head build and pass the unit tests in both K layouts, and does the generated code carry the two `save_k` call forms and no `save_k_helper`?
- Cells (our half of the machine, fake device for the tests; script `exec/savek2-20261008/build-test.sh` in jhan's intel-AMX workspace, results under `exec/results/savek2-20261008/`): VNNI build (preset native, AMX dispatch on, ingest models on) with `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics` (also under the kill switch), `t_llama_unit`, `t_heterogeneous_scheduler`, `t_phase1_integration`; the generated-plugin text; the ingest Haskell tests (`bin/ingest-cabal test`); the row-major build with the five layout-independent tests; clang-format, fourmolu and `git diff --check`.
- Verdict rule: every test passes, the plugin text has one main-side and one helper-side `save_k` call per KV-writing operation and no `save_k_helper`, the format checks pass.
- Status: running since 2026-10-08 19:17 UTC.

| check | result |
|---|---|
| VNNI build + 6 unit tests | pending |
| `t_amx_numerics` under the kill switch | pending |
| generated plugin text | pending |
| ingest Haskell tests | pending |
| row-major build + 5 unit tests | pending |
| clang-format, fourmolu, `git diff --check` | pending |

### Token identity and performance

Not run at this head. PR #4774 ran them for the same change at the previous PR #4424 head (https://github.com/positron-ai/tron/pull/4774, section Test): identical tokens in three cells and TPS/TTFT inside the band in four cells. The merge diff against 6b939d25d2 is PR #4774's diff with the branch head's constant spellings; it touches no kernel and no stored byte.

## Open items

- PR #4737 (the issue #4500 fix, stacked on PR #4424) still calls `save_k_helper` (15 mentions in 4 files) and is conflicting with the branch head. It needs a merge of the branch head and the same fold after this change lands on `jhan-amx-vnniK`.
- The PR #4424 description names `save_k_helper` in three places (the sharing bullet, the code-generator bullet and the `LoopyTronSpec.hs` test bullet). jhan edits that description on GitHub.
- PR #4774 is to be closed in favor of this PR (jhan).


🤖 Generated with [Claude Code](https://claude.com/claude-code)
