## Short version

`save_k` now takes the caller's worker index. The main thread (worker 0) and the main helpers (workers 1 .. n_workers - 1) call the same function at the same point of the schedule. `save_k_helper` is gone. Stored bytes, kernels and numerics are unchanged against the PR #4424 head.

This draft PR targets PR #4424's branch `jhan-amx-vnniK`. It answers the PR #4424 review question "Why do we need to introduce a new function for this? Why not simply extend `save_k` itself with a `worker_ix` argument and call it consistently from both the main thread and the helpers?" (https://github.com/positron-ai/tron/pull/4424#discussion_r4065141577).

## Words used here

| Term | Meaning |
|---|---|
| PR #4424 | "VNNI K": the K cache of 128-dimension heads stored in the AMX VNNI layout, with a shared block save (branch `jhan-amx-vnniK`, head 30c4ac82cb). This PR is one commit on top of it. |
| save_k | The function in `h/tron/models/model.hpp` that copies the K rows of one pass into the KV cache, once per layer per pass. |
| K store window | The protocol of Note [Shared block save] in `model.hpp`: the main thread cuts the pass into work units, opens a window, every thread claims units from one counter, the main thread joins the helpers. |
| main thread, main helpers | In a generated plugin, `run()` is the main thread and `run_main_help(worker_ix, n_workers)` runs on the helper threads. Worker 0 is the main thread, as the generated kernel calls already use it. |
| generated plugin | The model code that the code generator (`ingest/src/TronCpp.hs`) emits from the ingested model. |
| AMX, VNNI | Intel Advanced Matrix Extensions (the tile instruction set) and the pair-interleaved K layout the tile multiply reads. |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels. |

## What changes

- `h/tron/models/model.hpp`: both `save_k` overloads take `size_t worker_ix = 0, size_t n_workers = 1` after the K buffer. `save_k_impl` checks `worker_ix < n_workers` and branches once on `worker_ix == 0`. Worker 0 cuts the work units, resets the counters, opens the window, claims units, joins the helpers, then marks the tokens and credits the hardware queue as before. A worker 1 .. n_workers - 1 waits for its window, claims units, increments `finished` and returns. When the store is not shared (`k_store_shared` false: at most 16 items, one worker, or the row-major K layout) a helper returns at once and worker 0 stores every row itself. The claim loop, every memory order and the 120-s join watchdog are the ones of the PR #4424 head. The two `save_k_helper` overloads are removed. Note [Shared block save] and the comments name the single entry point.
- `ingest/src/TronCpp.hs`: the generated `run()` calls `save_k<geometry, op>(q_batch->outer_batch, k, 0, n_workers)` and the generated `run_main_help` calls `save_k<geometry, op>(q_batch->outer_batch, k, worker_ix, n_workers)` at the same statement position. The literal 0 for the main thread is the one `kernelCall` already emits for the main-side kernel calls.
- `ingest/test/LoopyTronSpec.hs`: the two generated-code checks expect two `save_k` calls per KV-writing operation (the main-side text ending in `,k,0,n_workers);` and the helper-side text ending in `,k,worker_ix,n_workers);`) and no `save_k_helper`.
- `t/t_llama_unit.cpp`: the three-thread section of the `save_k` test case calls `save_k` on every thread, the helpers with their worker index and the main thread with worker index 0.
- Not changed: the handwritten plugins (`h/tron/plugins/llama.hpp`, `t/heterogeneous_scheduler_compile.cpp`) keep their calls and take the defaults (worker 0 of 1: every row on the calling thread). `save_v` is unchanged.

## Test

@@TEST@@

## Open items

- PR #4737 (the issue #4500 fix, stacked on PR #4424) and PR #4746 (PR #4424 ported onto the typed KV tensors of PR #4557) still call `save_k_helper`. Each needs the same fold after this change lands on `jhan-amx-vnniK`.
- The PR #4424 description names `save_k_helper` in three places (sharing bullet, `model.hpp` bullet, code-generator bullet, and the gpt-oss-120b table row). jhan edits that description on GitHub.
