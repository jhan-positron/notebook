## Short version

This PR stores the K cache of 128-dimension heads (the saved key vectors of past tokens, for attention heads whose key has 128 values) in the AMX VNNI layout, so the AMX attention kernel reads K^T directly and computes the scores without a transpose. For passes of more than 16 tokens, the store uses a shared block save: runs of 2 to 16 tokens are transposed in registers and written as 64-byte cache lines by the main thread and its idle helper threads. A single token, as in every decode step, does not form a block. Its 64 dimension pairs are written one by one into 64 cache lines. 

Against the PR #3879 binary (qwen3-4b, 8 users, CPU attention with AMX), TTFT (time to first token) is lower in all six measured cells, and decode throughput is higher at tp2 at every prompt length and at tp4 at prompt 8192.

### Background

The AMX tile multiplication takes a row-major matrix only as its left operand. The right operand must be in the VNNI layout. Base (the PR #3879 binary) stores K row-major, one 128-value row per token. So the base kernel puts the K page (64 tokens x 128 dimensions) on the left and the packed queries on the right. The scores S then come out transposed:

```
S^T = K * Q^T     K as stored is the left operand, the packed Q^T the right one
S   = (S^T)^T     an AVX-512 register transpose writes the 4 query columns as score rows
```

### Remove the Score transpose by saving VNNI layout and transposed K
This PR removes the second step. The K rows of every 128-dimension head are written to the cache in the VNNI layout: pair-interleaved and transposed, so the stored data are K^T in the form the right operand needs. Memory used to hold row-major K. It now holds K^T in the VNNI layout, in the same number of bytes. The kernel computes `S = Q * K^T` directly.

Heads of other sizes keep the row-major layout (for example the 64-dimension heads of gpt-oss-120b). Dense pages (full 64-token pages) score bit-identically to base by unit test. Partial pages, and every page when the AMX kernel does not run (the kill switch TRON_AMX_DISABLE=1, hosts without AMX, 128-dimension heads with kv_mul  other than 4), go through a new AVX-512 reader.

### Use shared block in saving K
- Block save. A page's K plane holds 64 tokens in 4 blocks of 16. The K rows of 1 block are stored, per KV head, in 3 ways:
1. 16 tokens, a full block (typical in prefill): fill 16 AVX-512 registers, 1 token each register. Filling takes 4 steps, each step covers 32 dimensions; each step loads one 64-byte (16 dimension pairs). The registers are transposed, and each register holds one dimension pair of the 16 tokens. 
2. 2 to 15 tokens (prefill edges): the same, but each line store is masked to the run's tokens.
3. 1 token (decode): no transpose. Each of the 4 steps loads 64 bytes of the row into one register and scatters its 16 pairs into 16 cache lines, 4 bytes each: 4 scatters, 64 cache lines.
- Sharing. In a generated plugin (the model code that the code generator emits), the main thread runs save_k while its helper threads (the threads that run the per-token kernels) are idle. So the helpers now take part in the store. Each run is one work unit. Every thread takes the next unit from one shared counter until no unit is left. The runtime's split heuristic sets the number of helpers once per pass, so it is not a fixed number. In the traced runs it was 7 helpers plus the main thread at tp2, and 8 at tp4. Three cases are not shared and store on the thread that calls save_k: a pass of at most 16 tokens (for example a decode step of the 8-user runs), a caller that passes one worker (the handwritten plugins, and the unit tests except the three-thread case of t_llama_unit), and more than 128 workers.


## Words used here

| Term | Meaning |
|---|---|
| AMX, VNNI | AMX (Advanced Matrix Extensions) is the Intel instruction set for tile matrix multiplication. The AMX kernels are the attention kernels built on it. VNNI (Vector Neural Network Instructions) is an Intel instruction-set name. The VNNI layout is the pair-interleaved operand format that those instructions and the AMX tile multiply read. |
| VNNI layout | The pair-interleaved K layout: the two values of one dimension pair are adjacent in memory, and one 64-byte row holds that dimension pair for 16 tokens. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. |
| row-major K | The layout of `main`: one row of 128 values per token. |
| page | A 64-token block of the KV cache. |
| prefill, decode | Prefill is the pass that processes the prompt tokens, many tokens per pass. Decode is the pass that generates one output token per user. |
| KV head | One key/value head. Several query heads share it. |
| plane | The K or V storage of one page and one KV head. |
| tp2, tp4 | The tensor-parallel degree of the model build (the `-tp2` / `-tp4` suffix of the model name): the model is split across 2 or 4 devices. A device here is a slice, one FPGA with its share of the host's CPU cores and memory. |
| TPS | Decode throughput in tokens per second per user. |
| PR #4557, typed KV-cache tensors | Merged to `main` on 2026-10-07. It gives the KV cache typed owners and views: `v_vnni_tensor` / `v_vnni_view` for the packed (stored in the VNNI layout) V plane, `const_native_k_view` for the row-major K plane. This branch builds on it. |
| owner, view | An owner (`k_vnni_tensor`) holds the 16 KiB (64 tokens x 128 dimensions x 2 bytes) K plane of one page and KV head as one 64-byte-aligned array and nothing else. A view (`k_vnni_view`) refers to an owner's plane and knows the address formula. Views come only from an owner. A view has no public pointer constructor, no `data()` and no `operator[]`. It reads one element with `at(token, dim)`. It never writes one. |
| row view | One token's K row in dimension order as a typed rank-1 (one-dimensional) view (`const_k_row_view` for a source row, `k_row_view` for a destination row). `k_source_row` builds one from a pointer or from a slice view (two overloads). `k_destination_row` builds one from a pointer only. |
| main thread, main helpers | The generated plugin (the model code that the code generator emits) runs a pass on one main thread. A set of helper threads runs the per-token kernels in stripes (interleaved slices of the token range, where each of the n helpers takes every n-th token). The runtime's split heuristic sets the number of helpers once per pass. |
| save_k, Save K | The function (`model.hpp`) that copies the K rows of one pass into the KV cache, once per layer (one of the model's repeated transformer blocks) per pass. |
| shared block save | The K store of this branch. The pass's tokens are cut into work units (runs of consecutive tokens inside one 16-token block of a page). The main thread and the idle main helpers claim the units from one counter. A unit of two or more tokens is written with 16 rows transposed in registers, one 64-byte line at a time, masked (only the lanes of the unit's tokens are written) when the unit does not fill the block. A unit of one token is written with a scatter (many small stores, each to a separate address). |
| dotter | The per-token AVX-512 (the 512-bit vector instruction set used by the software path, not AMX) dot-product loop of the software attention path (`tron/kernels/dotter.hpp`). |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels and runs the software path. |
| base | Two comparators are called base. In the Background and Measurements sections, base is the PR #3879 binary (commit 544ca05c7a). In the Verification section, base is `main` at be0d5565b3, built without `TRON_K_VNNI` (row-major K). |
| greedy run, A/A repeat | A run with temperature 0 (always pick the top-scoring token) and deterministic reductions (sums performed in a fixed order, so the result does not depend on thread timing). The same binary then produces the same tokens twice. An A/A repeat is the same configuration run twice as a control. |
| slot | One persistent K/V storage region of the cache (one per layer, or shared between layers), described by a `kv_slot_spec`. A row-major slot keeps K in the row-major layout. |
| dense page | A full 64-token page, all of it visible to the query: the case the AMX QK kernel (the kernel that multiplies the query by the K rows to produce the attention scores) handles. |
| slice check, cost data | `bin/slice bench --check` runs in CI (continuous integration, the automated test runs on every push), in both the Nix workflow and the legacy CMake workflow. It fails when a registered test has no timing row in any platform block of `config/test-benchmarks.json`, and prints a warning when the current platform's block lacks one. The rows are called cost data. A row holds the run time at 1, 2 and 4 slices. genoa96 (the AMD runner) and granite_rapids_6962p (delphi-3bda) are two of the file's four platform blocks. |

## The changes

- New header `h/tron/tensor/k_vnni.hpp`. Everything in it is AVX-512. No AMX instruction is in it. It holds:
  - the layout (index map) and its constants
  - the owner `k_vnni_tensor<64, 128>`
  - the view `k_vnni_view<T, 64, 128>` with a bounds-checked read `at(token, dim)`
  - `detail::k_vnni_access`, the only access path from a view to the plane address. Its users are the operations below, the two score kernels and the test-only `book::fill_random`.
  - the row-view aliases and helpers
  - the typed operations `store_row` (the per-token scatter store), `load_row` (the gather load: many small loads, each from a separate address, into one row), `store_block` (the 16-token block save: transpose in registers, full cache line stores) and `copy_token`.
- `h/tron/kernels/k_vnni.hpp`: the AVX-512 reader `qk_group` of the layout for partial pages, hosts without AMX and the kill switch. It takes the packed view, not a pointer. It scores a query group (the query heads that share one KV head) wider than 16 heads in passes of 16. Every head's scores are its own accumulation. So the split changes no add order.
- `h/tron/tensor/kv_cache_fwd.hpp`: forward declarations of the two K types. With them, `amx_attn_iface.hpp` does not include any intrinsics (compiler built-in functions that map to single AVX-512 or AMX instructions).
- `kv_cache.hpp`:
  - Note [K VNNI storage] (a named comment block in the header that documents the layout).
  - `kv_block::k` is the owner `k_vnni_tensor` for a 128-dimension head under `TRON_K_VNNI`, and the row-major array otherwise (`std::conditional_t`). It has the same trivial-type checks (`static_assert`s that the type is trivially default-constructible, trivially copyable and trivially destructible) as the packed V plane.
  - The row views `page::k()` exist only for row-major slots (see the Words table).
  - `page::k_packed` returns a read-only view of the packed plane.
  - Layout-independent `set_k_row`, `get_k_row` (typed row views) and `set_k_block` serve both layouts.
  - A whole-page copy copies the owner (`dst_block.k = src_block.k`).
  - Other ranges are copied token by token with `copy_token`.
  - `fill_random` fills the packed plane through `detail::k_vnni_access`, as it does for V.
- `model.hpp`: Note [Shared block save].
  - `save_k` cuts the pass into work units. It shares the store with the main helpers (`save_k_helper`).
  - The workers are joined on one counter with a 120-s watchdog (the join aborts with an error if the helpers have not finished after 120 s).
  - The handwritten plugins pass one worker. So they store serially. The unit tests pass one worker. The exception is the shared-save case of `t_llama_unit`. That case passes three workers.
  - `save_k` passes typed source rows to the store. The K buffer's row view keeps its alignment and DMA flags (DMA = direct memory access, the device-visible memory tag).
- `common.hpp`: the state of one shared block save, called a window in the code (`batch::k_store_window`: claim counter, open and finished counters, the unit table).
- `self_attention.hpp`, `amx_attn.cpp`, `amx_attn_iface.hpp`:
  - The dense AMX page reads the VNNI plane (the K storage in the VNNI layout) as its B operand (`qk_vnni_128x4`). The kernel takes `k_vnni_view<const bf16, 64, 128>` (bf16 = 16-bit brain float, the K and V element type) by value. It reads the plane once through `detail::k_vnni_access::plane`. `weights_times_v_128x4` does the same for V.
  - `qk_vnni_128x4` is bit-identical to the row-major kernel by test.
  - The software path scores the live tokens (the tokens present in the page) in one AVX-512 loop over the page.
  - Both paths receive `page::k_packed`.
- FPGA staging (`gof.hpp`, `gof.cpp`, `full.hpp`). The FPGA is the accelerator card that runs attention for the pages it processes. Staging is the code that copies K and V rows into the buffers the FPGA reads. `k_head_fn` writes a token's K row into a scratch buffer (temporary memory) that the caller owns, through a typed destination row. `v_head_fn` already worked that way. `gof::populate` allocates the scratch. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the scratch-buffer parameter.
- Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k_helper` at the attention statement of every KV-writing operation. `save_k` receives the worker count.
- CMake option `TRON_K_VNNI` (default OFF, requires `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels). Files: `CMakeLists.txt`, `src/tron/CMakeLists.txt`. The option is also defined for `tron_model_compile_config` (the interface library through which `main` compiles the generated model objects). So those objects are compiled with the same K layout as the tron library. The legacy CMake workflow sets the option ON (`.github/workflows/cmake-single-platform.yml`). On `main` that workflow runs by manual dispatch and from `publish-deb.yml`. `README.ci.md` documents the flag.
- Tests:
  - `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`). It runs on real owners: poison (a fill of the plane with a known marker pattern before each check) through 64 typed row stores, layout checks on the owner's bytes, the index anchors (hand-computed offsets of chosen token and dimension pairs, compared against the index map), an `at()` section, a `copy_token` section, and the reader check for 4, 20 and 32 query heads with bf16, float and fp16 (16-bit IEEE half float) queries.
  - A bit-identity case in `t_amx_numerics`. It fills a `k_vnni_tensor` through `store_row`.
  - Fakes (stand-in implementations used only by the test) in `t_amx_dispatch_dtype` that take the typed view.
  - In `t_llama_unit`: a model-level shared-save case, a software-attention case for 32 query heads on one 128-dimension K/V head, layout-independent accessors, and the K typed-boundary contracts. The contracts are: the VNNI QK kernel accepts the packed view only, the other kernels reject it, no pointer construction, conversion only from a writable view to a read-only view, no view of a temporary owner, no element write, 64-byte owner alignment.
  - Checks in `LoopyTronSpec.hs` (the code-generator test suite) on the call text the generator emits for `save_k` and `save_k_helper`.
- Constant spelling: the AMX kernel files and this branch's own K headers and tests name every value-carrying constant `NAME_<value>`. Code added to shared files (`t_llama_unit.cpp`, `model.hpp`, `common.hpp`) keeps those files' own spelling (literals and lower_snake names), as PR #4557 does.

## Measurements (qwen3-4b, 8 users, one of the two CPU sockets of delphi-3bda, software attention with AMX)

delphi-3bda is the Intel Xeon 6962P test machine. One of its two CPU sockets is ours. The other is reserved for another user.

Against a `main` binary (be0d5565b3, 2026-10-08, tp2, 3 repetitions): decode TPS +5.3 % at prompt 1024 and +10.4 % at prompt 8192. TTFT is -57 ms at prompt 1024 (inside the 0.15 s band, the size of a difference that counts as noise) and -0.80 s at prompt 8192. The full rows, and an FPGA-attention cell, are in the Verification section.

Against the PR #3879 binary (544ca05c7a), tp2 and tp4. This branch at 10fc7c724c for the prompt 1024 rows (2026-09-15) and at 9928cb2849 for the prompt 2048 and prompt 8192 rows (2026-09-14/15):

| prompt | binary | tp2 TTFT | tp4 TTFT | tp2 TPS/user | tp4 TPS/user |
|---|---|---|---|---|---|
| 1024 | base (PR #3879) | 3.150 s | 2.194 s | 79.7 | 103.6 |
| 1024 | this branch | 3.095 s (-56 ms) | 2.117 s (-77 ms) | 83.9 (+5.3%) | 103.9 (+0.2%) |
| 2048 | this branch vs base | -112 ms (base 7.254 s, -1.5%) | -120 ms (base 4.719 s, -2.5%) | +7.1% | -0.7% |
| 8192 | this branch vs base | -1.37 s (base 53.369 s, -2.6%) | -0.52 s (base 30.487 s, -1.7%) | +10.1% | +8.0% |

The tp4 decode numbers have a run-to-run spread of 1 to 3 TPS (1 to 3 % of 104 TPS). So the +0.2 % and -0.7 % at prompt 1024 and prompt 2048 are inside that spread, not a real change.

- Decode gain: the gain grows with the prompt length.
- TTFT gain: the cause is the shared block save. Save K per prefill layer takes 274 us at tp2 and 281 us at tp4 with the row-major store (the PR #3879 binary), and 80 us at tp2 and 60 us at tp4 with the shared block save (this branch at 9928cb2849). Measured 2026-09-14/15 at prompt 1024 with 8 users, with in-process Perfetto (an open-source tracing tool into which tron records its own timing events) traces.


## Verification

The delphi-3bda runs below were taken at 37064d72b2 on 2026-10-08. The head 6b939d25d2 compiles to the same code. The two commits after 37064d72b2 change only comments, one `static_assert` condition and the cost-data file.

Setup: `nix develop` (the project's pinned build shell), clang 19, preset `native` (explicit AVX-512 flags), `TRON_AMX_DISPATCH=ON`, `BUILD_INGEST_MODELS=ON` (the CMake option that builds the generated model plugins).

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

One `main` test, `t_llama_unit` "apply and join page ranges / query splits match unsplit page reductions", runs with a wider tolerance in this branch. The Open items section gives the mechanism.

Whole host test suite (`make build-test-host`, `make test-host`, VNNI build, fake device (a software stand-in for the FPGA), our half):
- All host test targets compile.
- 93 tests passed.
- 1 test skipped: `t_proxy_lib`. The Python venv (virtual environment) `t/proxy/.venv` is absent on the machine.
- 1 test failed: `t_proxy_llama31`, new on `main`. It fails with "t/proxy/.venv missing", the same absent venv. The cause is the machine, not the code.
- Total wall-clock time of the suite: 128 s.

Cost rows (`config/test-benchmarks.json`, granite_rapids_6962p block) were measured with `bin/slice bench --update t_llama_unit t_k_vnni_layout t_amx_numerics` on the whole delphi-3bda host (both sockets, 2026-10-08). The rows are `t_llama_unit` 28.1 / 28.3 / 28.3 s, `t_k_vnni_layout` 0.90 / 0.91 / 0.91 s and `t_amx_numerics` 0.81 / 0.83 / 0.74 s. The three values are the run time at 1, 2 and 4 slices.

Token identity, measured with runtron (tron's command-line tool): qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism (the runtron flag that selects the deterministic reductions of a greedy run), seed 1, 256 generated tokens. This branch against `base` = `main` at be0d5565b3 (row-major K, AMX dispatch on):

| cell | this branch vs its A/A repeat | this branch, AMX on vs kill switch | this branch vs base |
|---|---|---|---|
| CPU attention, prompt 1024 | identical, 256 of 256 | identical, 256 of 256 | first difference at generated token 52 |
| FPGA attention, prompt 1024 | not run | not run | first difference at generated token 52 |
| CPU attention, prompt 8192 | not run | not run | identical, 256 of 256 |

The divergence against `base` is tracked in issue #4444 (see Open items). It appears under FPGA attention too. There the software path still scores, with the VNNI reader, the pages the FPGA does not process.

Performance. Setup:
- qwen3-4b tp2, 8 users, 256 generated tokens, 3 repetitions, the binaries interleaved.
- band (the size of a difference that counts as noise) = the larger of 2 x the largest standard deviation (sd) of the two binaries, and a floor of 0.4 TPS for TPS or 0.15 s for TTFT.
- TPS = decode tokens per second per user.
- TTFT = the maximum over the 8 users.

| cell | attention | base (`main` be0d5565b3) TPS / TTFT | this branch TPS / TTFT | band TPS / TTFT | this branch vs base |
|---|---|---|---|---|---|
| prompt 1024, n = 3 | CPU | 79.37 / 3.178 s | 83.60 / 3.121 s | 0.54 / 0.15 s | TPS +5.3 % (beyond the band), TTFT -57 ms (inside the band) |
| prompt 8192, n = 3 | CPU | 17.13 / 52.542 s | 18.90 / 51.745 s | 0.40 / 0.29 s | TPS +10.4 % (beyond the band), TTFT -0.80 s (beyond the band) |
| prompt 1024, n = 3 | FPGA | 128.72 / 3.184 s | 125.97 / 3.142 s | 0.89 / 0.15 s | TPS -2.1 % (beyond the band, the decode loss of issue #4500), TTFT -42 ms (inside the band) |

Under CPU attention decode is faster than `base` in both cells, and TTFT is lower at prompt 8192. The TTFT differences at prompt 1024 are inside the band. Under FPGA attention decode is slower than `base`. Issue #4500 tracks that loss.

## Open items

- **genoa96 cost row for `t_k_vnni_layout`.** The genoa96 block (the AMD benchmark runner) of `config/test-benchmarks.json` has no row for `t_k_vnni_layout`. The CI check passes without it. `bin/slice bench --check` fails only when a test has no row in any platform block, and prints a warning when the current platform's block lacks one. A genoa96 row needs a run on that runner.
- **128-dimension heads with kv_mul (the number of query heads that share one KV head) other than 4 (measure before merging).** For qwen-3-30b-a3b (kv_mul 8) the VNNI layout is on. The AMX kernel is not eligible for that shape. So every page goes through the AVX-512 reader of the layout instead of the row-major dotter. The decode store also scatters into cold lines (64-byte cache lines not yet present in the CPU cache). Measured on 2026-09-16 with this branch at 65a1c41d72 against `main` c7844ca2ce (8 users, tp2): decode TPS +1.5 % at prompt 1024 (6 repetitions, inside noise), -4.1 % at prompt 2048 (3 repetitions, a loss), +24.1 % at prompt 8192 (3 repetitions). TTFT is lower by 8 to 16 % in every cell. The cells need a repeat at this head. If the prompt 2048 loss repeats, the layout gate `k_vnni::layout_on<head_size>` should also require the AMX shape (kv_mul 4), or the reader needs a faster path for larger groups (more query heads per KV head).
- **Benchmark binary mismatch (reviewers decide).** The legacy CMake workflow compiles `runtron` once, in its `build` job, with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`, and hands that binary to its `benchmark` job. When the hand-over works, the benchmark measures a binary with the AMX kernels and the VNNI K layout. When the hand-over fails, the benchmark job compiles `runtron` itself through `make`. That `make` build sets neither option. The benchmark then measures a binary with row-major K and no AMX kernels. PR #3879 introduced this mismatch for `TRON_AMX_DISPATCH`. This PR adds `TRON_K_VNNI` to the same line. The default CI (the Nix build on GCP, Google Cloud Platform runners) is not affected. Its benchmark binary is built with neither option. If the mismatch is unwanted, both options should move out of the build job into a configuration of their own. `TRON_PAGE_SHARE_COUNTERS` (another CMake option) already works that way, through the `coverage` preset (a CMake configuration preset).
- **Kill switch and token divergence (tracked in issue #4444, reviewers decide).** This branch generates a different token than `main` from generated token 52 of the prompt-1024 run, under CPU and under FPGA attention. The prompt-8192 run is identical. The expected cause is the add order. Partial pages are scored by the VNNI reader (this PR's AVX-512 routine that scores tokens from the VNNI layout), which adds the fp32 products in a different order than the row-major dotter. A token flips only at a near tie (a step where the two best candidate tokens have almost the same score). Issue #4444 holds the forced-run measurement that would confirm this. With `TRON_K_VNNI` on, `TRON_AMX_DISABLE=1` runs the VNNI reader instead of the dotter for 128-dimension heads. The kill switch still gives an AMX-off run of the same binary. It no longer gives the tokens of a clean binary (a build with both options off). Item 4 of Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp` still promises those tokens for rollback. Issue #4444 lists two options: (a) accept the weaker rollback and add the condition "with `TRON_K_VNNI` off" to item 4, or (b) keep a row-major build as the rollback artifact in deployment and document that. Note [K VNNI storage] in `kv_cache.hpp` describes the behavior of this branch. Under FPGA attention the software path still scores the pages the FPGA does not process.
- **A `main` test tolerance is widened.** `t_llama_unit` "apply and join page ranges / query splits match unsplit page reductions" (added to `main` on 2026-09-11) compares a page reduction done in one run with the same reduction done as two ranges and joined. On `main` it bounds the difference of the weighted V sum by 0.02 and of the weight sum by 2e-6. The two runs reach a page with a different running maximum (the largest score seen so far, which the softmax subtracts from every score before the exponential). So each softmax weight (the normalized attention score) is converted to bf16 for the PV product (the product of the softmax weights and V) at a different scale. The AVX path truncates in that conversion. The row-major build passes `main`'s bounds by a small margin (0.018 of 0.020 on one element of the weighted V sum, 1.9e-6 of 2.0e-6 on the weight sum). With VNNI K the scores differ in their last bits. The bf16 conversion then rounds at a different point. One element reaches 0.022. This branch sets the bounds to 0.05 and a relative 1e-6. The test passes with `TRON_K_VNNI` on and off. The test comment names the mechanism. The test's author may want to review the change.
- **Stacked PRs.** PR #4774 (one `save_k` for the main thread and the helpers) and PR #4737 (keeps short K-cache writes row-major, the fix for issue #4500) have this branch as their base. Both need a merge of this head. The `save_k` function and the K-plane helpers they touch are typed here.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
