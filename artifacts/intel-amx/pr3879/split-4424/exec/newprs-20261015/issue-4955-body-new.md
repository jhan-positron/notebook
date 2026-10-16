## Short version

PR #4959 converts the K blocks a pass completed at the forward end, after the cooperative FPGA staging has drained. No test checks that order. If the call moved before the drain, every test would still pass. This issue tracks the test fixture that would catch such a move.

## Words used here

| Term | Meaning |
|---|---|
| the conversion | `convert_pending_k_blocks` in `h/tron/models/model.hpp`: at the end of a forward pass it rewrites, in place, every 16-token K block whose 16th row that pass saved, from row-major into the VNNI layout (PR #4959). |
| cooperative staging | The copying of K and V rows of a GOF (group of four consecutive tokens) into the buffer that DMA moves to the FPGA card, done by the pass's worker threads next to the compute (`gof_rodeo`). `wait_for_coop_gof` waits until it has finished. |
| the drain | The `wait_for_coop_gof()` call at the forward end. After it, no staging read of a completed block is in flight. |
| the fixture | `heterogeneous_scheduler_plugin` in `t/heterogeneous_scheduler_compile.cpp`, the fake-device scheduler the forward-path test runs on. |

## What is tested today

- The forward-path case of `t_heterogeneous_scheduler` ("model::state::forward converts the K block its decode step completes at the forward end") proves that the conversion runs: it completes a block in a decode step and checks the converted-block bit after the forward.
- The mutation check of PR #4959 proves that the test can fail: with the `convert_pending_k_blocks()` call removed from the forward, the case fails at its block check (71 of 72 assertions pass).

## What is not tested

The position of the call. The forward calls `wait_for_coop_gof()` and then `convert_pending_k_blocks()` [h/tron/models/model.hpp:1840-1844]. The order matters: the cooperative staging of an earlier minibatch can still be reading a completed block's rows in their row-major form, and converting under that read would hand the FPGA a mixed block. The fixture runs no cooperative staging, so a test that moved the conversion before the drain would still pass. The order is defended by the comment above the call and by Note [K VNNI storage] in `h/tron/models/kv_cache.hpp` only.

## What would close this issue

A test on a fixture with cooperative staging:

1. A pass completes a block by a short run (the block becomes pending).
2. Cooperative staging of an earlier minibatch reads that block during the same forward, and the read is held open until the forward reaches the drain (a fake `gof_rodeo` that blocks on a latch).
3. The test asserts that the staging read saw row-major bytes, and that the block's converted bit is set only after the read returned.
4. A mutation check: with the conversion moved before `wait_for_coop_gof()`, the test must fail.

## Where this came from

PR #4959, section Open items ("The conversion"). The cost half of that item was measured on 2026-10-15 (the `convert_k_blocks` span: 1.1 to 1.2 ms per 16 decode steps, 0.6 to 0.8 % of decode time) and is in the PR body. The ordering half is this issue.

