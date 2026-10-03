## Short version

This draft PR is PR #4424 (VNNI K: the K cache of 128-dimension heads stored in the AMX VNNI layout) ported onto PR #4557 (typed KV-cache tensors). The K plane of a VNNI slot is now a typed owner (`k_vnni_tensor`) reached through typed views (`k_vnni_view`), the same shape PR #4557 gave the packed V plane. No raw K-plane pointer crosses the cache or kernel boundary any more. Stored bytes, kernels and numerics are unchanged against the PR #4424 head.

The base of this PR is the PR #4557 branch `jhan-kv-typed-tensors`. It stays a draft until PR #4557 merges to `main`. Then the base moves to `main` and PR #4424 is replaced by this branch (or this branch is pushed to `jhan-amx-vnniK`, jhan's call).

## Words used here

| Term | Meaning |
|---|---|
| PR #4557, the parent | "Typed KV-cache tensors for packed V and native K" (branch `jhan-kv-typed-tensors`). It gives the KV cache typed owners and views: `v_vnni_tensor` / `v_vnni_view` for packed V, `const_native_k_view` for the row-major K plane. |
| PR #4424, the child | "VNNI K" (branch `jhan-amx-vnniK`, head 30c4ac82cb). This PR carries all of its commits, then a merge of the parent, then the adaptation commits listed below. |
| VNNI layout | The pair-interleaved K layout: the two values of one dimension pair sit next to each other, and one 64-byte row holds that dimension pair for 16 tokens. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. |
| owner, view | An owner (`k_vnni_tensor`) holds the 16 KiB plane as one 64-byte-aligned array and nothing else. A view (`k_vnni_view`) refers to an owner's plane and knows the address formula. Views come only from an owner. A view has no public pointer constructor, no `data()` and no `operator[]`. |
| row view | One token's K row in dimension order as a typed rank-1 view (`const_k_row_view` for a source row, `k_row_view` for a destination row). The helpers `k_source_row` / `k_destination_row` build one from a pointer or from a slice view. |
| AMX, AVX-512 | Intel Advanced Matrix Extensions (the tile instruction set) and the 512-bit vector instruction set. |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels and runs the AVX-512 reader of the VNNI layout. |
| dense page | A full 64-token page, all of it visible to the query: the case the AMX QK kernel handles. |

## What changes against PR #4424

- New header `h/tron/tensor/k_vnni.hpp`: the owner `k_vnni_tensor<64, 128>`, the view `k_vnni_view<T, 64, 128>` with bounds-checked `at(token, dim)`, the index map and its constants (`namespace k_vnni`, unchanged), `detail::k_vnni_access` (the one route from a view to the plane address, for the operations below and the two score kernels), the row-view aliases and helpers, and the typed operations `store_row` (was `k_vnni::scatter_row`), `load_row` (was `gather_row`), `store_block` and `copy_token`. The vector bodies moved verbatim: same scatters, gathers, transposes and masked stores.
- `h/tron/kernels/k_vnni.hpp` keeps only the AVX-512 reader `qk_group`. It takes the packed view, not a pointer. It scores a query group wider than 16 heads in passes of 16 (every head's scores are its own accumulation, so the split changes no add order); PR #4424 rejected such groups at compile time, which broke software attention for geometries such as 32 query heads on one 128-dimension K/V head (review finding on this PR).
- `h/tron/tensor/kv_cache_fwd.hpp`: forward declarations of the two K types, so `amx_attn_iface.hpp` stays free of intrinsics.
- `kv_cache.hpp`: `kv_block::k` is `std::conditional_t<k_vnni::layout_on<head_size>, k_vnni_tensor<page_size, head_size>, bf16[page_size * head_size]>`, with the same trivial-type checks the parent has for V. `k_view()` / `k_at()` exist for the array branch only. `page::k_vnni_plane` (a raw pointer) is replaced by `page::k_packed` (a read-only view). `set_k_row` / `get_k_row` take typed row views and call `store_row` / `load_row`. `set_k_block` calls `store_block` on the owner's writable view. `copy_storage_slot` copies a whole page as `dst_block.k = src_block.k` and other ranges with `copy_token`. `fill_random` fills the packed plane through `detail::k_vnni_access`, as it does for V. Note [K VNNI storage] describes the typed plane.
- `amx_attn_iface.hpp`, `amx_attn.cpp`: `qk_vnni_128x4` takes `k_vnni_view<const bf16, 64, 128>` by value and reads the plane once through `detail::k_vnni_access::plane`, as `weights_times_v_128x4` does for V. Its tile registers use the file's naming scheme (`Q_ROWS_TILE_4`, `K_EVEN_PANEL_TILE_5`, `K_ODD_PANEL_TILE_6`, `ACCUMULATOR_TILE_0..3`): identifiers only, same registers, same instruction order.
- `self_attention.hpp`: the dense AMX page and the software loop pass `page::k_packed` to the kernels. The file includes the kernel header itself.
- `model.hpp`, `full.hpp`: `save_k` passes typed source rows (the K buffer's row view keeps its alignment and DMA flags), the FPGA staging callback passes a typed destination row for its scratch.
- `src/tron/CMakeLists.txt`: `TRON_K_VNNI` is also defined for `tron_model_compile_config`, the interface library that `main` (commit 0128331632) now uses for the generated model objects. Without it those objects compiled the KV cache with the row-major layout while the tron library used VNNI. PR #4424 predates that `main` change.
- Tests: `t_k_vnni_layout` runs on real owners (poison through 64 typed row stores, layout checks on the owner's bytes, the index anchors unchanged, a new `at()` section and a `copy_token` section). `t_amx_numerics`' bit-identity case fills a `k_vnni_tensor` through `store_row`. `t_amx_dispatch_dtype`'s fake takes the typed view. `t_llama_unit` passes typed rows at every K row call and gains the K typed-boundary contracts next to the parent's V ones (the VNNI QK kernel accepts the packed view only; the other kernels reject it; no pointer construction; writable-to-read-only only; no view of a temporary owner; owner size 16384 bytes and alignment 64; storage selection per build option).

## Merge resolution (commit 61fee9b017)

Seven files had textual conflicts: `kv_cache.hpp`, `self_attention.hpp`, `amx_attn.cpp`, `t_amx_dispatch_dtype.cpp`, `t_llama_unit.cpp`, `common.hpp`, `config/test-benchmarks.json`. Every conflict was two additions at the same place; both sides were kept. Two auto-merged places did not compile and were fixed in the same commit: the bit-identity test's `qk_rowmajor_128x4` call (now a `const_native_k_view`), and `main`'s sliding-chunk test, which writes the 128-dimension slot through `set_k_row` / `get_k_row` (the row view does not exist for a VNNI slot).

## Decisions

- Merge, not rebase. The branch is PR #4424's history plus a merge of the parent plus adaptation commits. Later parent changes come in as small merges, and PR #4737 (stacked on PR #4424) keeps a valid merge base.
- No `k_vnni_row` and no expression base. The parent dropped `v_vnni_row` on review ("do not add code which has no consumer"), and the issue #4525 design says to drop the K counterpart then.
- `at(token, dim)` is kept on the K view, as on the V view. Its consumers are the layout test and the contract probes.
- The K row operations keep the caller's `aligned` and `dma` flags (they use unaligned vector loads and stores). The packed V rows require aligned rows; K does not.
- Not done here: the issue #4525 design's "worker-index request" (fold `save_k_helper` into `save_k(..., worker_ix, n_workers)`, with a code-generator change). It is independent of the typed tensors and overlaps PR #4737; it is left for its own change.
- Cost rows (`config/test-benchmarks.json`): the parent's `t_llama_unit` row is kept and understates the merged binary. The refresh (`bin/slice bench --update t_llama_unit t_k_vnni_layout t_amx_numerics`) needs the whole delphi-3bda host and is deferred. PR #4424's measured rows were 13.436 / 13.388 / 13.618 s for `t_llama_unit` and 0.709 / 0.697 / 0.696 s for `t_k_vnni_layout`.

## Verification

Head 76ef81e2fc. The delphi-3bda token-identity and performance results below were taken at 0c2630583a. The commits after it change comments and named literals (719cdcd565, 76ef81e2fc) and the wide-group split in `qk_group` (977826a272), which is not reached by qwen3-4b (4 query heads per K/V head), so they do not change the measured code.

At 76ef81e2fc on delphi-3bda (VNNI build with ingest models, real AMX): `t_k_vnni_layout` 1011650 assertions / 5 cases (reader check for 4, 20 and 32 heads with bf16, float and fp16 queries), `t_llama_unit` 246843 / 46 (including the new `apply_page_tok` instantiation for 32 query heads on one 128-dimension K/V head), `t_amx_numerics` 12813 / 5, `t_amx_dispatch_dtype` 1559 / 1, `t_heterogeneous_scheduler` 1900 / 2, `t_phase1_integration` 2124 / 64, all pass. On claude-box both trees (TRON_K_VNNI on and off) pass the five relevant binaries.


On claude-box (clang 19, preset native, AMX dispatch on, fake device, no AMX hardware), both at 0c2630583a and at 719cdcd565: `t_k_vnni_layout` (79810 assertions, 5 cases), `t_amx_dispatch_dtype` (1559), `t_amx_numerics` (2060, the three AMX cases skipped on that host), `t_heterogeneous_scheduler` (1900) and `t_llama_unit` (246842 assertions, 45 cases) pass with `TRON_K_VNNI=ON`; the same five pass with it OFF (`t_llama_unit` 246898). `make lint-notes` and clang-format are clean.

On delphi-3bda (our half, socket 1; chain `exec/sync4424-20261002/chain.sh` in jhan's intel-AMX workspace, 2026-10-02 18:14 to 19:20 UTC; results under `exec/results/sync4424-20261002/`, `sync4424-E-cpu/`, `sync4424-E-fpga/`):

- VNNI build (cross-avx512 preset, AMX dispatch on, ingest models on) at 0c2630583a: `t_k_vnni_layout` 79810 / 5, `t_amx_dispatch_dtype` 1559 / 1, `t_amx_numerics` 12813 / 5 on real AMX (no "AMX unavailable" line), `t_llama_unit` 246842 / 45, `t_heterogeneous_scheduler` 1900 / 2, `t_phase1_integration` 2124 / 64, all pass. Kill-switch control (`TRON_AMX_DISABLE=1`): `t_amx_numerics` 2060 assertions with the three "AMX unavailable" warnings.
- Row-major build (`TRON_K_VNNI=OFF`): the five layout-independent tests pass.
- Whole host suite (`make build-test-host`, `make test-host`, VNNI build): 90 passed, 1 skipped (`t_proxy_lib`), 0 failed, makespan 121 s. A first pass while the production engines still held the hugepage slices failed 6 tests at `heap_setup`; that is the machine, not the code.
- Token identity (runtron, qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens): the synced binary (`new`) produced the same 256 tokens as the PR #4424 binary (`head`, 30c4ac82cb) in every cell: CPU attention prompt 1024 (also `new` vs its A/A repeat, and the kill-switch pair `newoff` vs `headoff`), FPGA attention prompt 1024, CPU attention prompt 8192. Against the PR #4557 binary (`base`, c12df586b6, row-major K) both VNNI binaries diverge at generated token 52 of prompt 1024; that is PR #4424's known divergence (issue #4444), unchanged by this port.
- Performance (8 users, 256 tokens, 3 repetitions interleaved; band = max(2 x max sd, 0.4 TPS / 0.15 s)):

| cell | attention | base (PR #4557) TPS / TTFT | head (PR #4424) TPS / TTFT | new (this PR) TPS / TTFT | new vs head |
|---|---|---|---|---|---|
| prompt 1024 | CPU | 79.59 / 3.178 s | 83.45 / 3.147 s | 83.53 / 3.121 s | TPS +0.1 %, TTFT -26 ms, inside band |
| prompt 8192 | CPU | 17.06 / 52.870 s | 18.92 / 52.799 s | 18.86 / 52.179 s | TPS -0.3 %, TTFT -620 ms (sd 0.5 s), inside band |
| prompt 1024 | FPGA | 128.02 / 3.105 s | 125.04 / 3.198 s | 125.20 / 3.060 s | TPS +0.1 %, TTFT -138 ms, inside band |

TPS = decode tokens per second per user; TTFT = time to first token (prefill), max over the users. `new` vs `base` reproduces PR #4424's picture (CPU decode +4.9 % and +10.6 %, FPGA decode -2.2 %, issue #4500). Production serving was restored after the run.

## Open items

- PR #4737 (row-major tail block for issue #4500) must be re-merged onto this branch. Its raw-pointer helpers (`row_ptr`, `block_to_vnni`, `block_to_rows`) need typed forms.
- The cost-row refresh above.
- After PR #4557 merges: merge `main`, retarget to `main`, decide the fate of PR #4424.

🤖 Generated with [Claude Code](https://claude.com/claude-code)



