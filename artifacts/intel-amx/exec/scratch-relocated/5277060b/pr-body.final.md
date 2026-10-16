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

Head f52d634c32. The delphi-3bda chain below ran at 19ae84d95a; f52d634c32 adds the K-mark checks to the `t_llama_unit` test and rewords one generator comment, so the measured runtron code is the same. The final commit's `t_llama_unit` (both K layouts) and the ingest tests were rerun at f52d634c32 (last bullet).

On delphi-3bda (our half, socket 1; chain `exec/savek-20261006/chain.sh` in jhan's intel-AMX workspace, 2026-10-06 17:54 to 18:44 UTC, rerun of one cell 18:55 to 19:13 UTC; results under `exec/results/savek-20261006/`, `savek-E-cpu/`, `savek-E-fpga/`, `savek-E-cpu8k/`):

- VNNI build (cross-avx512 preset, AMX dispatch on, ingest models on, 610 s): `t_k_vnni_layout` 63426 assertions / 5 cases, `t_amx_dispatch_dtype` 1559 / 1, `t_amx_numerics` 4621 / 5 on real AMX (no "AMX unavailable" line), `t_llama_unit` 128261 / 42, `t_heterogeneous_scheduler` 782 / 1, `t_phase1_integration` 2124 / 64, all pass. Kill-switch control (`TRON_AMX_DISABLE=1`): `t_amx_numerics` 2060 assertions with the three "AMX unavailable" warnings.
- The generated plugins carry one main-side call (`..., 0, n_workers)`) and one helper-side call (`..., worker_ix, n_workers)`) per KV-writing operation and no `save_k_helper`: qwen3-4b 36 and 36, qwen3-30b-moe 48 and 48, gpt-oss-120b 36 and 36.
- Ingest Haskell tests (`bin/ingest-cabal test`): 1 of 1 test suites passed.
- Row-major build (`TRON_K_VNNI=OFF`): the five layout-independent tests pass.
- Whole host suite (`make build-test-host`, `make test-host`, VNNI build): 89 passed, 1 skipped (`t_proxy_lib`), 0 failed, makespan 107 s. The PR #4424 reference is 89 / 1 / 0.
- Token identity (runtron, qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens): the new binary produced the same 256 tokens as the PR #4424 binary (30c4ac82cb) in every cell: CPU attention prompt 1024 (also the A/A repeat and the kill-switch pair), FPGA attention prompt 1024, CPU attention prompt 8192.
- Performance (8 users, 256 tokens, arms interleaved; band = max(2 x max sd, 0.4 TPS / 0.15 s)). TPS = decode tokens per second per user, TTFT = prefill time in seconds (max over the users).

| attention | prompt | n | head TPS | new TPS | TPS delta | head TTFT s | new TTFT s | TTFT delta |
|---|---|---|---|---|---|---|---|---|
| CPU | 1024 | 3 | 83.39 | 83.83 | +0.5 % | 3.139 | 3.136 | -3 ms |
| CPU | 8192 | 3 | 18.90 | 18.80 | -0.5 % | 52.74 | 55.94 | +3.2 s (one repetition at 61.5 s, the other two at 53.1 and 53.2 s) |
| CPU | 8192, rerun, new first | 5 | 18.91 | 18.79 | -0.7 % | 52.82 | 52.99 | +0.17 s (+0.3 %) |
| FPGA | 1024 | 3 | 125.18 | 124.98 | -0.2 % | 3.181 | 3.187 | +6 ms |

  The prompt-8192 cell was run again with five repetitions and the arm order reversed because of the 61.5-s repetition. In the rerun no repetition is above 53.2 s. The decode TPS of that cell is 0.5 to 0.7 % below head in both runs; this is inside the band. A decode step has at most 16 items, so the store is not shared there and both binaries take the same early return in the helpers.
- Final commit f52d634c32: `t_llama_unit` 128453 assertions / 42 cases in the VNNI build and 128510 / 42 in the row-major build (192 more than at 19ae84d95a: the K-mark checks), `bin/ingest-cabal test` 1 of 1 test suites passed.

## Open items

- PR #4737 (the issue #4500 fix, stacked on PR #4424) and PR #4746 (PR #4424 ported onto the typed KV tensors of PR #4557) still call `save_k_helper`. Each needs the same fold after this change lands on `jhan-amx-vnniK`.
- The PR #4424 description names `save_k_helper` in three places (sharing bullet, `model.hpp` bullet, code-generator bullet, and the gpt-oss-120b table row). jhan edits that description on GitHub.


🤖 Generated with [Claude Code](https://claude.com/claude-code)
