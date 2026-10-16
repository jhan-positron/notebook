## Words used here

| Term | Meaning |
|---|---|
| VNNI layout | The pair-interleaved K layout: the two values of one dimension pair are adjacent in memory, and one 64-byte row holds that dimension pair for 16 tokens. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. |
| row-major K | The layout of `main`: one row of 128 values per token. |
| page | A 64-token block of the KV cache. |
| KV head | One key/value head. Several query heads share it. |
| plane | The K or V storage of one page and one KV head. |
| PR #4557, typed KV-cache tensors | Merged to `main` on 2026-10-07. It gives the KV cache typed owners and views: `v_vnni_tensor` / `v_vnni_view` for the packed V plane, `const_native_k_view` for the row-major K plane. This branch builds on it. |
| owner, view | An owner (`k_vnni_tensor`) holds the 16 KiB (64 tokens x 128 dimensions x 2 bytes) K plane of one page and KV head as one 64-byte-aligned array and nothing else. A view (`k_vnni_view`) refers to an owner's plane and knows the address formula. Views come only from an owner. A view has no public pointer constructor, no `data()` and no `operator[]`. It reads one element with `at(token, dim)`. It never writes one. |
| row view | One token's K row in dimension order as a typed rank-1 (one-dimensional) view (`const_k_row_view` for a source row, `k_row_view` for a destination row). `k_source_row` builds one from a pointer or from a slice view (two overloads). `k_destination_row` builds one from a pointer only. |
| main thread, main helpers | The generated plugin (the model code that the code generator emits) runs a pass on one main thread. A fixed set of helper threads runs the per-token kernels in stripes (interleaved slices of the token range, where each of the n helpers takes every n-th token). |
| save_k, Save K | The function (`model.hpp`) that copies the K rows of one pass into the KV cache, once per layer (one of the model's repeated transformer blocks) per pass. |
| shared block save | The K store of this branch. The pass's tokens are cut into work units (runs of consecutive tokens inside one 16-token block of a page). The main thread and the idle main helpers claim the units from one counter. A unit of two or more tokens is written with 16 rows transposed in registers, one 64-byte line at a time, masked (only the lanes of the unit's tokens are written) when the unit does not fill the block. A unit of one token is written with a scatter (many small stores, each to a separate address). |
| dotter | The per-token AVX-512 (the 512-bit vector instruction set used by the software path, not AMX) dot-product loop of the software attention path (`tron/kernels/dotter.hpp`). |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels and runs the software path. |
| base | A `main` binary built without `TRON_K_VNNI` (row-major K). The Measurements table also cites the older base of the first campaign, the PR #3879 binary (commit 544ca05c7a). |
| greedy run, A/A repeat | A run with temperature 0 (always pick the top-scoring token) and deterministic reductions (sums performed in a fixed order, so the result does not depend on thread timing). The same binary then produces the same tokens twice. An A/A repeat is the same configuration run twice as a control. |
| slot | One persistent K/V storage region of the cache (one per layer, or shared between layers), described by a `kv_slot_spec`. A row-major slot keeps K in the row-major layout. |
| dense page | A full 64-token page, all of it visible to the query: the case the AMX QK kernel (the kernel that multiplies the query by the K rows to produce the attention scores) handles. |
| slice check, cost data | `bin/slice bench --check` in the CMake CI (continuous integration, the automated test runs on every push) job requires a timing row for every registered test in `config/test-benchmarks.json`. The rows are called cost data. genoa96 and granite_rapids_6962p are the platform blocks of that file. |

## The changes

- New header `h/tron/tensor/k_vnni.hpp`. Everything in it is AVX-512. No AMX instruction is in it. It holds:
  - the layout (index map) and its constants
  - the owner `k_vnni_tensor<64, 128>`
  - the view `k_vnni_view<T, 64, 128>` with a bounds-checked read `at(token, dim)`
  - `detail::k_vnni_access`, the only access path from a view to the plane address. Its users are the operations below, the two score kernels and the test-only `book::fill_random`.
  - the row-view aliases and helpers
  - the typed operations `store_row` (the per-token scatter store), `load_row` (the gather load: many small loads, each from a separate address, into one row), `store_block` (the 16-token block save: transpose in registers, full cache line stores) and `copy_token`.
- `h/tron/kernels/k_vnni.hpp`: the AVX-512 reader `qk_group` of the layout for partial pages, hosts without AMX and the kill switch. It takes the packed view, not a pointer. It scores a query group wider than 16 heads in passes of 16. Every head's scores are its own accumulation. So the split changes no add order.
- `h/tron/tensor/kv_cache_fwd.hpp`: forward declarations of the two K types. With them, `amx_attn_iface.hpp` does not include any intrinsics (compiler built-in functions that map to single AVX-512 or AMX instructions).
- `kv_cache.hpp`:
  - Note [K VNNI storage] (a named comment block in the header that documents the layout).
  - `kv_block::k` is the owner `k_vnni_tensor` for a 128-dimension head under `TRON_K_VNNI`, and the row-major array otherwise (`std::conditional_t`). It has the same trivial-type checks as the packed V plane.
  - The row views `page::k()` exist only for row-major slots (see the Words table).
  - `page::k_packed` returns a read-only view of the packed plane.
  - Layout-independent `set_k_row`, `get_k_row` (typed row views) and `set_k_block` serve both layouts.
  - A whole-page copy copies the owner (`dst_block.k = src_block.k`).
  - Other ranges are copied token by token with `copy_token`.
  - `fill_random` fills the packed plane through `detail::k_vnni_access`, as it does for V.
- `model.hpp`: Note [Shared block save]. `save_k` cuts the pass into work units. It shares the store with the main helpers (`save_k_helper`). The workers are joined on one counter with a 120-s watchdog (the join aborts with an error if the helpers have not finished after 120 s). The handwritten plugins pass one worker. So they store serially. The unit tests pass one worker. The exception is the shared-save case of `t_llama_unit`. That case passes three workers. `save_k` passes typed source rows to the store. The K buffer's row view keeps its alignment and DMA flags (DMA = direct memory access, the device-visible memory tag).
- `common.hpp`: the state of one shared block save, called a window in the code (`batch::k_store_window`: claim counter, open and finished counters, the unit table).
- `self_attention.hpp`, `amx_attn.cpp`, `amx_attn_iface.hpp`: the dense AMX page reads the VNNI plane as its B operand (`qk_vnni_128x4`). The kernel takes `k_vnni_view<const bf16, 64, 128>` by value. It reads the plane once through `detail::k_vnni_access::plane`. `weights_times_v_128x4` does the same for V. The VNNI plane is the K storage in the VNNI layout. `qk_vnni_128x4` is bit-identical to the row-major kernel by test. The software path scores the live tokens (the tokens present in the page) in one AVX-512 loop over the page. Both paths receive `page::k_packed`.
- FPGA (the accelerator card that runs attention for the pages it processes) staging, the code that copies K and V rows into the buffers the FPGA reads (`gof.hpp`, `gof.cpp`, `full.hpp`): `k_head_fn` writes a token's K row into a scratch buffer (temporary memory) that the caller owns, through a typed destination row. `v_head_fn` already worked that way. `gof::populate` allocates the scratch. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the parameter.
- Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k_helper` at the attention statement of every KV-writing operation. `save_k` receives the worker count.
- CMake option `TRON_K_VNNI` (default OFF, requires `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels). Files: `CMakeLists.txt`, `src/tron/CMakeLists.txt`. The option is also defined for `tron_model_compile_config` (the interface library through which `main` compiles the generated model objects). So those objects are compiled with the same K layout as the tron library. The legacy CMake workflow sets the option ON (`.github/workflows/cmake-single-platform.yml`). On `main` that workflow runs by manual dispatch and from `publish-deb.yml`. `README.ci.md` documents the flag.
- Tests:
  - `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`). It runs on real owners: poison (a fill of the plane with a known marker pattern before each check) through 64 typed row stores, layout checks on the owner's bytes, the index anchors (hand-computed offsets of chosen token and dimension pairs, compared against the index map), an `at()` section, a `copy_token` section, and the reader check for 4, 20 and 32 query heads with bf16 (16-bit brain float, the K and V element type), float and fp16 (16-bit IEEE half float) queries.
  - A bit-identity case in `t_amx_numerics`. It fills a `k_vnni_tensor` through `store_row`.
  - Fakes (stand-in implementations used only by the test) in `t_amx_dispatch_dtype` that take the typed view.
  - In `t_llama_unit`: a model-level shared-save case, a software-attention case for 32 query heads on one 128-dimension K/V head, layout-independent accessors, and the K typed-boundary contracts. The contracts are: the VNNI QK kernel accepts the packed view only, the other kernels reject it, no pointer construction, writable-to-read-only only, no view of a temporary owner, no element write, 64-byte owner alignment.
  - Call-text checks in `LoopyTronSpec.hs`.
- Constant spelling: the AMX kernel files and this branch's own K headers and tests name every value-carrying constant `NAME_<value>`. Code added to shared files (`t_llama_unit.cpp`, `model.hpp`, `common.hpp`) keeps those files' own spelling (literals and lower_snake names). PR #4557 (the parent PR) agreed on this rule with its reviewer.

## Measurements (qwen3-4b, 8 users, one of the two CPU sockets of delphi-3bda, software attention with AMX)

delphi-3bda is the Intel Xeon 6962P test machine. One of its two CPU sockets is ours. The other is reserved for another user.

The table below is the first campaign against the PR #3879 binary 544ca05c7a. Its prompt 1024 rows were measured at branch commit 10fc7c724c (campaign vnnik2-confirm, 2026-09-15). Its prompt 2048 and prompt 8192 rows were measured at branch commit 9928cb2849 (campaign vnnik2, 2026-09-14/15). The Verification section carries the 2026-10-08 cells against a `main` binary.

| prompt | binary | tp2 TTFT | tp4 TTFT | tp2 TPS/user | tp4 TPS/user |
|---|---|---|---|---|---|
| 1024 | base (PR #3879) | 3.150 s | 2.194 s | 79.7 | 103.6 |
| 1024 | this branch | 3.095 s (-56 ms) | 2.117 s (-77 ms) | 83.9 (+5.3%) | 103.9 (+0.2%) |
| 2048 | this branch vs base | -112 ms (base 7.254 s, -1.5%) | -120 ms (base 4.719 s, -2.5%) | +7.1% | -0.7% |
| 8192 | this branch vs base | -1.37 s (base 53.369 s, -2.6%) | -0.52 s (base 30.487 s, -1.7%) | +10.1% | +8.0% |

The tp4 decode numbers have a run-to-run spread of 1 to 3 TPS (1 to 3 % of 104 TPS). So the +0.2 % and -0.7 % at prompt 1024 and prompt 2048 are inside that spread, not a real change.

- Decode gain: the gain grows with the prompt length.
- TTFT gain: the cause is the shared block save. Save K per prefill layer went from 274 us (base) to 60 to 80 us (this branch), measured with in-process Perfetto (an open-source tracing tool into which tron records its own timing events) traces.

Against a `main` binary (be0d5565b3, 2026-10-08, tp2 only, 3 repetitions): decode +5.3 % at prompt 1024 and +10.4 % at prompt 8192, TTFT -57 ms and -0.82 s. This branch at prompt 8192 has 2 repetitions. The chain (the script that runs the campaign steps in order) reached its 01:30 UTC cutoff before the third. The full rows are in the Verification section.


## Verification

Head 4bbf97ef78. The delphi-3bda runs below were taken at 37064d72b2. The one commit after it (4bbf97ef78) changes comments and writes one `static_assert` as a zero comparison. So the compiled code is the same. @@FINAL_TIP_CHECK@@

The runs below used this setup on delphi-3bda on 2026-10-08. The chain is `exec/sync4424b-20261007/chain.sh` in jhan's intel-AMX workspace, and the results are under `exec/results/sync4424b-20261007/`. Setup: `nix develop` (the project's pinned build shell), clang 19, preset `native` (explicit AVX-512 flags), `TRON_AMX_DISPATCH=ON`, `BUILD_INGEST_MODELS=ON` (the CMake option that builds the generated model plugins).

Unit tests, VNNI build (`TRON_K_VNNI=ON`), real AMX, our half of the machine:

| test | result (assertions / test cases) |
|---|---|
| `t_k_vnni_layout` | pass, 1011650 / 5 |
| `t_amx_dispatch_dtype` | pass, 1612 / 1 |
| `t_amx_numerics` | pass, 4621 / 5 (the AMX cases ran: no "AMX unavailable" line) |
| `t_llama_unit` | pass, 251563 / 64 |
| `t_heterogeneous_scheduler` | pass, 2783 / 3 |
| `t_phase1_integration` | pass, 2124 / 64 |
| `t_amx_numerics` with the kill switch (`TRON_AMX_DISABLE=1`) | pass, 2060 / 5, the three AMX cases report "AMX unavailable" |
| Haskell code-generator suite (`bin/ingest-cabal test`) | pass |

Row-major build (`TRON_K_VNNI=OFF`), all pass (assertions / test cases):
- `t_k_vnni_layout` 1011650 / 5
- `t_amx_dispatch_dtype` 1612 / 1
- `t_amx_numerics` 4621 / 5
- `t_llama_unit` 251478 / 64
- `t_heterogeneous_scheduler` 2783 / 3

One test of `main` needed a wider tolerance (commit 37064d72b2): `t_llama_unit` "apply and join page ranges / query splits match unsplit page reductions" compares a page reduction done in one run with the same reduction done as two ranges and joined. The two runs reach a page with a different running maximum. So each softmax weight (the normalized attention score) is converted to bf16 for the PV product (the product of the softmax weights and V) at a different scale. The AVX path truncates in that conversion. The row-major build passes the old bounds by a small margin (0.018 of 0.020 on one element of the weighted V sum, 1.9e-6 of 2.0e-6 on the weight sum). With VNNI K the scores differ in their last bits. The bf16 conversion then rounds at a different point. One element reaches 0.022. The bounds are now 0.05 and a relative 1e-6. Measured with the option on and off.

Whole host test suite (`make build-test-host`, `make test-host`, VNNI build, fake device (a software stand-in for the FPGA), our half):
- All host test targets compile.
- 93 tests passed.
- 1 test skipped: `t_proxy_lib`. The Python venv `t/proxy/.venv` is absent on the machine.
- 1 test failed: `t_proxy_llama31`, new on `main`. It fails with "t/proxy/.venv missing", the same absent venv. The cause is the machine, not the code.
- Total wall-clock time of the suite: 128 s.

Token identity, measured with runtron (tron's command-line tool): qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism (the runtron flag that selects the deterministic reductions of a greedy run), seed 1, 256 generated tokens. `new` = this branch, `head` = the previous PR head 30c4ac82cb (VNNI K already, before the typed-tensor port and the merge of `main`), `base` = `main` at be0d5565b3 (row-major K, AMX dispatch on):

| cell | new vs head | new vs its A/A repeat | kill-switch pairs | new vs base |
|---|---|---|---|---|
| CPU attention, prompt 1024 | identical, 256 of 256 | identical | `newoff` = `headoff` = `head` = `new` (`newoff` and `headoff` are the `new` and `head` binaries run with the kill switch) | first difference at generated token 52 |
| FPGA attention, prompt 1024 | identical, 256 of 256 | - | - | first difference at generated token 52 (`head` vs `base` the same) |
| CPU attention, prompt 8192 | identical, 256 of 256 | - | - | identical, 256 of 256 |

So the typed port and the merge of `main` change no token against the previous head. The divergence against `base` is the known PR #4424 divergence (issue #4444). It appears under FPGA attention too. There the software path still scores, with the VNNI reader, the pages the FPGA does not process.

Performance. Setup:
- 8 users, 256 generated tokens, 3 repetitions interleaved. The `new` arm at prompt 8192 has 2 repetitions. The chain reached its 01:30 UTC cutoff before its third.
- band (the size of a difference that counts as noise) = the larger of 2 x the largest standard deviation (sd) across the three binaries, and a floor of 0.4 TPS for TPS or 0.15 s for TTFT.
- TPS = decode tokens per second per user.
- TTFT = the maximum over the 8 users.

| cell | attention | base (`main` be0d5565b3) TPS / TTFT | head (30c4ac82cb) TPS / TTFT | new (this branch) TPS / TTFT | new vs head | new vs base |
|---|---|---|---|---|---|---|
| prompt 1024, n = 3 | CPU | 79.37 / 3.178 s | 83.32 / 3.147 s | 83.60 / 3.121 s | TPS +0.3 % (inside band), TTFT -26 ms (inside band) | TPS +5.3 %, TTFT -57 ms |
| prompt 8192, n = 3 (new: 2) | CPU | 17.13 / 52.542 s | 18.93 / 52.849 s | 18.92 / 51.719 s | TPS +0.0 % (inside band), TTFT -1.13 s (beyond the band) | TPS +10.4 %, TTFT -0.82 s |
| prompt 1024 | FPGA | pending: runs after the nightly CI window of 2026-10-08 | | | | |

`new` vs `base` reproduces the first campaign's result against a `main` binary (CPU decode +5.3 % at prompt 1024 and +10.4 % at prompt 8192, TTFT lower in both cells). `new` vs `head`: decode is inside the band in both cells. TTFT is lower by 26 ms at prompt 1024 (inside the band, which is 0.15 s there) and by 1.13 s at prompt 8192 (beyond the band, which is 0.38 s there). `head` is the 2026-09-17 binary. So the TTFT difference carries 916 `main` commits (query splitting, attention path stats, the chunk-size removal, K and V projections on separate device halves) as well as the typed port. A comparator binary that has the merge of `main` but not the typed port (commit c6ec38813d) is measured after the nightly CI window to attribute it (open items). Production serving was restored after the run.


## Open items

- **FPGA-attention performance cell, cost rows and the TTFT attribution (running).** The 2026-10-08 chain reached its pre-CI cutoff (01:30 UTC, the time at which our runs must stop to leave the machine to the nightly CI) before the FPGA-attention cell (prompt 1024) and the cost-row refresh (`bin/slice bench --update t_llama_unit t_k_vnni_layout t_amx_numerics`, a whole-machine measurement). Both run after the nightly CI window, together with the comparator cells (commit c6ec38813d, the merge of `main` without the typed port, against `new`) that attribute the TTFT difference between `new` and the 2026-09-17 head. This section is updated then. The previous FPGA-attention cell (2026-10-02, against the old PR #4557 head) was inside the band.
- **128-dimension heads with kv_mul (the number of query heads that share one KV head) other than 4 (measure before merging).** For qwen-3-30b-a3b (kv_mul 8) the VNNI layout is on. The AMX kernel is not eligible for that shape. So every page goes through the AVX-512 reader of the layout instead of the row-major dotter. The decode store also scatters into cold lines (64-byte cache lines not yet present in the CPU cache). One run (2026-09-15) against base showed -5.4 % decode TPS (a loss: 34.3 vs 36.3 TPS/user). The same run showed -7 % TTFT, a gain of 369 ms (lower TTFT is better). If more repetitions confirm the decode loss, the layout gate `k_vnni::layout_on<head_size>` should also require the AMX shape (kv_mul 4), or the reader needs a faster path for larger groups (more query heads per KV head).
- **Benchmark binary mismatch (reviewers decide).** The legacy CMake workflow compiles `runtron` once, in its `build` job, with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`, and hands that binary to its `benchmark` job. When the hand-over works, the benchmark measures a binary with the AMX kernels and the VNNI K layout. When the hand-over fails, the benchmark job compiles `runtron` itself through `make`. That `make` build sets neither option. The benchmark then measures a binary with row-major K and no AMX kernels. PR #3879 introduced this mismatch for `TRON_AMX_DISPATCH`. This PR adds `TRON_K_VNNI` to the same line. The default CI (the Nix build on GCP, Google Cloud Platform runners) is not affected: its benchmark binary is built with neither option. If the mismatch is unwanted, both options should move out of the build job into a configuration of their own. `TRON_PAGE_SHARE_COUNTERS` (another CMake option) already works that way, through the `coverage` preset (a CMake configuration preset).
- **Kill switch and token divergence (tracked in #4444).** With `TRON_K_VNNI` on, `TRON_AMX_DISABLE=1` runs the VNNI reader (this PR's AVX-512 routine that scores tokens from the VNNI layout) instead of the row-major dotter for 128-dimension heads. The kill switch still gives an AMX-off run of the same binary. It no longer gives the tokens of a clean binary (a build with both options off). Item 4 of Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp` still promises those tokens for rollback. It needs the condition "with `TRON_K_VNNI` off". Note [K VNNI storage] in `kv_cache.hpp` describes the new behavior. The 2026-10-08 identity runs add one fact. The divergence against `main` (generated token 52 of the prompt-1024 run) appears under FPGA attention as well. Under FPGA attention the software path still scores the pages the FPGA does not process.
- **A `main` test tolerance was widened (commit 37064d72b2).** `t_llama_unit` "apply and join page ranges / query splits match unsplit page reductions" (added to `main` on 2026-09-11) bounds the split-vs-unsplit difference of the weighted V sum by 0.02 and of the weight sum by 2e-6. The row-major build passes those bounds with 0.018 and 1.9e-6. The VNNI scores move one element to 0.022. The bounds are now 0.05 and a relative 1e-6. The test comment names the mechanism (bf16 conversion of the PV weights at a different scale). The test's author may want to review the change.
- **Stacked PRs.** PR #4774 (one `save_k` for the main thread and the helpers, Ben's suggestion) and PR #4737 (row-major tail block for issue #4500) have this branch as their base. Both were written against its previous head 30c4ac82cb. Both need a merge of this head: `save_k` and the K-plane helpers they touch are now typed. PR #4746 (the same port on the old PR #4557 head) is replaced by this head. It can be closed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
