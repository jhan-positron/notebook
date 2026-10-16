## Words used here

| Term | Meaning |
|---|---|
| VNNI layout | The pair-interleaved K layout: the two values of one dimension pair sit next to each other, and one 64-byte row holds that dimension pair for 16 tokens. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. |
| row-major K | The layout of `main`: one row of 128 values per token. |
| PR #4557, typed KV-cache tensors | Merged to `main` on 2026-10-07. It gives the KV cache typed owners and views: `v_vnni_tensor` / `v_vnni_view` for the packed V plane, `const_native_k_view` for the row-major K plane. This branch builds on it. |
| owner, view | An owner (`k_vnni_tensor`) holds the 16 KiB K plane of one page and KV head as one 64-byte-aligned array and nothing else. A view (`k_vnni_view`) refers to an owner's plane and knows the address formula. Views come only from an owner. A view has no public pointer constructor, no `data()` and no `operator[]`; it reads one element with `at(token, dim)` and never writes one. |
| row view | One token's K row in dimension order as a typed rank-1 view (`const_k_row_view` for a source row, `k_row_view` for a destination row). The helpers `k_source_row` / `k_destination_row` build one from a pointer or from a slice view. |
| main thread, main helpers | The generated plugin (the model code that the code generator emits) runs a pass on one main thread. A fixed set of helper threads runs the per-token kernels in stripes (interleaved slices of the token range, where each of the n helpers takes every n-th token). |
| save_k, Save K | The function (`model.hpp`) that copies the K rows of one pass into the KV cache, once per layer (one of the model's repeated transformer blocks) per pass. |
| shared block save | The K store of this branch. The pass's tokens are cut into work units (runs of consecutive tokens inside one 16-token block of a page). The main thread and the idle main helpers claim the units from one counter. A unit of two or more tokens is written with 16 rows transposed in registers, one 64-byte line at a time, masked when the unit does not fill the block. A unit of one token is written with a scatter (many small stores, each to a separate address). |
| dotter | The per-token AVX-512 dot-product loop of the software attention path (`tron/kernels/dotter.hpp`). |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels and runs the software path. |
| base | A `main` binary built without `TRON_K_VNNI` (row-major K). The Measurements table also cites the older base of the first campaign, the PR #3879 binary (commit 544ca05c7a). |
| greedy run, A/A repeat | A run with temperature 0 (always pick the top-scoring token) and deterministic reductions (sums performed in a fixed order, so the result does not depend on thread timing). The same binary then produces the same tokens twice. An A/A repeat is the same configuration run twice as a control. |
| slot | One persistent K/V storage region of the cache (one per layer, or shared between layers), described by a `kv_slot_spec`. A row-major slot keeps K in the row-major layout. |
| dense page | A full 64-token page, all of it visible to the query: the case the AMX QK kernel handles. |
| slice check, cost data | `bin/slice bench --check` in the CMake CI job requires a timing row for every registered test in `config/test-benchmarks.json`. The rows are called cost data. genoa96 and granite_rapids_6962p are the platform blocks of that file. |

## The changes

- New header `h/tron/tensor/k_vnni.hpp`: the layout (index map) and its constants, the owner `k_vnni_tensor<64, 128>`, the view `k_vnni_view<T, 64, 128>` with a bounds-checked read `at(token, dim)`, `detail::k_vnni_access` (the one route from a view to the plane address, for the operations below, the two score kernels and the test-only `book::fill_random`), the row-view aliases and helpers, and the typed operations `store_row` (the per-token scatter store), `load_row` (the gather load), `store_block` (the 16-token block save: transpose in registers, full cache line stores) and `copy_token`. Everything in it is AVX-512. No AMX instruction is in it.
- `h/tron/kernels/k_vnni.hpp`: the AVX-512 reader `qk_group` of the layout for partial pages, hosts without AMX and the kill switch. It takes the packed view, not a pointer. It scores a query group wider than 16 heads in passes of 16 (every head's scores are its own accumulation, so the split changes no add order).
- `h/tron/tensor/kv_cache_fwd.hpp`: forward declarations of the two K types, so `amx_attn_iface.hpp` stays free of intrinsics.
- `kv_cache.hpp`: Note [K VNNI storage] (a named comment block in the header that documents the layout). `kv_block::k` is the owner `k_vnni_tensor` for a 128-dimension head under `TRON_K_VNNI` and the row-major array otherwise (`std::conditional_t`), with the same trivial-type checks the packed V plane has. The row views `page::k()` exist only for row-major slots (see the Words table). `page::k_packed` hands out a read-only view of the packed plane. Layout-independent `set_k_row`, `get_k_row` (typed row views) and `set_k_block` serve both layouts. A whole-page copy copies the owner (`dst_block.k = src_block.k`). Other ranges are copied token by token with `copy_token`. `fill_random` fills the packed plane through `detail::k_vnni_access`, as it does for V.
- `model.hpp`: Note [Shared block save]. `save_k` cuts the pass into work units. It shares the store with the main helpers (`save_k_helper`). The workers are joined on one counter with a 120-s watchdog (the join aborts with an error if the helpers have not finished after 120 s). The handwritten plugins pass one worker and store serially. The unit tests pass one worker. The exception is the shared-save case of `t_llama_unit`. That case passes three workers. `save_k` passes typed source rows to the store (the K buffer's row view keeps its alignment and DMA flags).
- `common.hpp`: the state of one shared block save, called a window in the code (`batch::k_store_window`: claim counter, open and finished counters, the unit table).
- `self_attention.hpp`, `amx_attn.cpp`, `amx_attn_iface.hpp`: the dense AMX page reads the VNNI plane as its B operand (`qk_vnni_128x4`). The kernel takes `k_vnni_view<const bf16, 64, 128>` by value and reads the plane once through `detail::k_vnni_access::plane`, as `weights_times_v_128x4` does for V. The VNNI plane is the K storage in the VNNI layout. `qk_vnni_128x4` is bit-identical to the row-major kernel by test. The software path scores the live tokens (the tokens present in the page) in one AVX-512 loop over the page. Both paths receive `page::k_packed`.
- FPGA staging, the code that copies K and V rows into the buffers the FPGA reads (`gof.hpp`, `gof.cpp`, `full.hpp`): `k_head_fn` writes a token's K row into a scratch buffer (temporary memory) that the caller owns, through a typed destination row. `v_head_fn` already worked that way. `gof::populate` allocates the scratch. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the parameter.
- Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k_helper` at the attention statement of every KV-writing operation. `save_k` receives the worker count.
- CMake option `TRON_K_VNNI` (default OFF, requires `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels). Files: `CMakeLists.txt`, `src/tron/CMakeLists.txt`. The option is also defined for `tron_model_compile_config`, the interface library through which `main` compiles the generated model objects, so those objects see the same K layout as the tron library. The legacy CMake workflow sets the option ON (`.github/workflows/cmake-single-platform.yml`; on `main` that workflow runs by manual dispatch and from `publish-deb.yml`). `README.ci.md` documents the flag.
- Tests: `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`; runs on real owners: poison through 64 typed row stores, layout checks on the owner's bytes, the index anchors, an `at()` section, a `copy_token` section, and the reader check for 4, 20 and 32 query heads with bf16, float and fp16 queries), a bit-identity case in `t_amx_numerics` (fills a `k_vnni_tensor` through `store_row`), fakes (stand-in implementations used only by the test) in `t_amx_dispatch_dtype` that take the typed view, a model-level shared-save case, a software-attention case for 32 query heads on one 128-dimension K/V head, layout-independent accessors and the K typed-boundary contracts (the VNNI QK kernel accepts the packed view only, the other kernels reject it, no pointer construction, writable-to-read-only only, no view of a temporary owner, no element write, 64-byte owner alignment) in `t_llama_unit`, call-text checks in `LoopyTronSpec.hs`.
- Constant spelling: the AMX kernel files and this branch's own K headers and tests name every value-carrying constant `NAME_<value>`. Code added to shared files (`t_llama_unit.cpp`, `model.hpp`, `common.hpp`) keeps those files' own spelling (literals and lower_snake names), as the parent PR settled with its reviewers.

## Measurements (qwen3-4b, 8 users, half of delphi-3bda, sw attention with AMX)

The table below is the first campaign (2026-09-15, pre-rebase head bb325d0a6e against the PR #3879 binary 544ca05c7a). The Verification section carries the 2026-10-08 cells against a `main` binary.

| prompt | binary | tp2 TTFT | tp4 TTFT | tp2 TPS/user | tp4 TPS/user |
|---|---|---|---|---|---|
| 1024 | base (PR #3879) | 3.150 s | 2.194 s | 79.7 | 103.6 |
| 1024 | this branch | 3.095 s (-56 ms) | 2.117 s (-77 ms) | 83.9 (+5.3%) | 103.9 (+0.2%) |
| 2048 | this branch vs base | -112 ms (base 7.254 s, -1.5%) | -120 ms (base 4.719 s, -2.5%) | +7.1% | -0.7% |
| 8192 | this branch vs base | -1.37 s (base 53.369 s, -2.6%) | -0.52 s (base 30.487 s, -1.7%) | +10.1% | +8.0% |

The tp4 decode numbers have a run-to-run spread of 1 to 3 TPS, that's 1 to 3% of 104 TPS. So the +0.2% and -0.7% at 1k and 2k are noises. 

- Decode gain: the gain grows with the prompt length.
- TTFT gain: the shared block save. Save K per prefill layer went from 274 us (base) to 60 to 80 us (this branch), measured with in-process Perfetto traces.

@@MAIN_MEAS@@


## Verification

Head 4bbf97ef78. The delphi-3bda runs below were taken at 37064d72b2. The one commit after it (4bbf97ef78) changes comments and writes one `static_assert` as a zero comparison, so the compiled code is the same. @@FINAL_TIP_CHECK@@

Setup on delphi-3bda, 2026-10-08 (chain `exec/sync4424b-20261007/chain.sh` in jhan's intel-AMX workspace, results under `exec/results/sync4424b-20261007/`): `nix develop` (the project's pinned build shell), clang 19, preset `native` (explicit AVX-512 flags), `TRON_AMX_DISPATCH=ON`, `BUILD_INGEST_MODELS=ON`.

Unit tests, VNNI build (`TRON_K_VNNI=ON`), real AMX, our half of the machine:

| test | result |
|---|---|
| `t_k_vnni_layout` | pass, 1011650 assertions, 5 cases |
| `t_amx_dispatch_dtype` | pass, 1612 / 1 |
| `t_amx_numerics` | pass, 4621 / 5 (the AMX cases ran: no "AMX unavailable" line) |
| `t_llama_unit` | pass, 251563 / 64 |
| `t_heterogeneous_scheduler` | pass, 2783 / 3 |
| `t_phase1_integration` | pass, 2124 / 64 |
| `t_amx_numerics` with the kill switch (`TRON_AMX_DISABLE=1`) | pass, 2060 / 5, the three AMX cases report "AMX unavailable" |
| Haskell code-generator suite (`bin/ingest-cabal test`) | pass |

Row-major build (`TRON_K_VNNI=OFF`): `t_k_vnni_layout` 1011650 / 5, `t_amx_dispatch_dtype` 1612 / 1, `t_amx_numerics` 4621 / 5, `t_llama_unit` 251478 / 64, `t_heterogeneous_scheduler` 2783 / 3, all pass.

One test of `main` needed a wider tolerance (commit 37064d72b2): `t_llama_unit` "apply and join page ranges / query splits match unsplit page reductions" compares a page reduction done in one run with the same reduction done as two ranges and joined. The two runs reach a page with a different running maximum, so each softmax weight is converted to bf16 for the PV product at a different scale (the AVX path truncates). The row-major build passes the old bounds with little to spare (0.018 of 0.020 on one element of the weighted V sum, 1.9e-6 of 2.0e-6 on the weight sum). With VNNI K the scores differ in their last bits, the conversion lands elsewhere, and one element reaches 0.022. The bounds are now 0.05 and a relative 1e-6. Measured with the option on and off.

Whole host test suite (`make build-test-host`, `make test-host`, VNNI build, fake device, our half): all host test targets compile; 93 passed, 1 skipped (`t_proxy_lib`), 1 failed (`t_proxy_llama31`, new on `main`: "t/proxy/.venv missing", the same absent Python venv that skips `t_proxy_lib`; the machine, not the code). Makespan 128 s.

Token identity (runtron, qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens). `new` = this branch, `head` = the previous PR head 30c4ac82cb (row-major port not yet applied), `base` = `main` at be0d5565b3 (row-major K, AMX dispatch on):

| cell | new vs head | new vs its A/A repeat | kill-switch pairs | new vs base |
|---|---|---|---|---|
| CPU attention, prompt 1024 | identical, 256 of 256 | identical | `newoff` = `headoff` = `head` = `new` | first difference at generated token 52 |
| FPGA attention, prompt 1024 | identical, 256 of 256 | - | - | first difference at generated token 52 (`head` vs `base` the same) |
| CPU attention, prompt 8192 | identical, 256 of 256 | - | - | identical, 256 of 256 |

So the typed port and the merge of `main` change no token against the previous head. The divergence against `base` is PR #4424's known one (issue #4444). It appears under FPGA attention too: the software path still scores the pages the FPGA does not take, with the VNNI reader.

Performance (8 users, 256 tokens, 3 repetitions interleaved; band = max(2 x max sd, 0.4 TPS / 0.15 s); TPS = decode tokens per second per user, TTFT = time to first token, max over the users):

@@PERF_TABLE@@


## Open items

@@OPEN_ITEMS@@
