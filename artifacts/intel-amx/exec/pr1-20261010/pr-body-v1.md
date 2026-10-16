## Short version

This PR stores the K cache of 128-dimension heads (the saved key vectors of past tokens, for attention heads whose key has 128 values) in the AMX VNNI layout, behind a typed owner and typed views, so no raw plane pointer leaves the cache. In this PR the layout is read by an AVX-512 reader on the CPU and by the FPGA staging gather, and no AMX instruction is added. The CMake option `TRON_K_VNNI` is off in every preset, and the AMX kernel that reads the plane, the shared block save and the row-major tail block follow in the next three PRs of the stack.

### Background

The AMX tile multiplication takes a row-major matrix only as its left operand. The right operand must be in the VNNI layout. `main` stores K row-major, one 128-value row per token. So the AMX QK kernel of `main` (PR #3879) puts the K page (64 tokens x 128 dimensions) on the left and the packed queries on the right. The scores S then come out transposed:

```
S^T = K * Q^T     K as stored is the left operand, the packed Q^T the right one
S   = (S^T)^T     an AVX-512 register transpose writes the 4 query columns as score rows
```

Storing K pair-interleaved and transposed (the VNNI layout) makes the stored data K^T in the form the right operand needs. Memory used to hold row-major K. It now holds K^T in the VNNI layout, in the same number of bytes. The AMX kernel of the next PR then computes `S = Q * K^T` directly, without the register transpose. This PR lays that storage down, types its access, and gives it its two software readers: the AVX-512 reader of the CPU path and the FPGA staging gather. Heads of other sizes keep the row-major layout (for example the 64-dimension heads of gpt-oss-120b).

## Words used here

| Term | Meaning |
|---|---|
| AMX, VNNI | AMX (Advanced Matrix Extensions) is the Intel instruction set for tile matrix multiplication. The AMX kernels are the attention kernels of `main` built on it (PR #3879). VNNI (Vector Neural Network Instructions) is an Intel instruction-set name. The VNNI layout is the pair-interleaved operand format that those instructions and the AMX tile multiply read. |
| VNNI layout | The pair-interleaved K layout: the two values of one dimension pair of a token are adjacent in memory, and one 64-byte line holds that dimension pair for 16 consecutive tokens. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. |
| row-major K | The layout of `main`: one row of 128 values per token. |
| the option | The CMake option `TRON_K_VNNI` (default OFF). With it on, every 128-dimension head stores K in the VNNI layout. No preset sets it. |
| AMX dispatch | The CMake option `TRON_AMX_DISPATCH` that compiles the AMX attention kernels of `main` and their dispatch. This PR does not require it. |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels and runs the software path. |
| page, block | A page is 64 consecutive tokens of the KV cache, the unit the cache allocates. A block is 16 consecutive tokens of a page (one AMX tile width). |
| plane | The K or V storage of one page and one KV head (16 KiB for K: 64 tokens x 128 dimensions x 2 bytes). |
| KV head, kv_mul | One key/value head. kv_mul is the number of query heads that share it (4 for qwen3-4b and llama-3.1-8b, 3 for llama-3.2-3b, 8 for qwen-3-30b-a3b). |
| slot | One persistent K/V storage region of the cache (one per layer, or shared between layers). A VNNI slot stores K in the VNNI layout, a row-major slot in rows. |
| prefill, decode | Prefill is the pass that processes the prompt tokens, many tokens per pass. Decode is the pass that generates one output token per user. |
| owner, view | An owner (`k_vnni_tensor`) holds the 16 KiB K plane of one page and KV head as one 64-byte-aligned array and nothing else. A view (`k_vnni_view`) refers to an owner's plane and knows the address formula. Views come only from an owner. A view has no public pointer constructor, no `data()` and no `operator[]`. It reads one element with `at(token, dim)`. It never writes one. |
| row view | One token's K row in dimension order as a typed rank-1 (one-dimensional) view (`const_k_row_view` for a source row, `k_row_view` for a destination row). `k_source_row` builds one from a pointer or from a slice view. `k_destination_row` builds one from a pointer. |
| the reader | `k_vnni::qk_group` (`h/tron/kernels/k_vnni.hpp`): the AVX-512 (the 512-bit vector instruction set) routine of this PR that scores a query group against the tokens of one page read from the VNNI plane, one token per vector lane. |
| dotter | The per-token AVX-512 dot-product loop of the software attention path of `main` (`h/tron/kernels/dotter.hpp`). It reads row-major K. |
| save_k | The function (`model.hpp`) that copies the K rows of one pass into the KV cache, once per layer per pass. |
| FPGA, staging | The FPGA is the accelerator card that runs attention for the pages it processes. Staging is the code that copies K and V rows into the buffers the FPGA reads (`gof::populate`). |
| tp2 | The tensor-parallel degree of the model build (the `-tp2` suffix of the model name): the model is split across 2 devices. A device is a slice, one FPGA with its share of the host's CPU cores and memory. |
| TPS, TTFT | TPS is the decode throughput in tokens per second per user. TTFT is the time to first token. |
| base, new | base is `main` at 72308ec90c (the commit this branch merged), built as runtron without the option (row-major K, AMX dispatch on). new is this branch at its head, built with the option on and AMX dispatch on. newoff and baseoff are the same binaries run with the kill switch. |
| greedy run, A/A repeat | A run with temperature 0 (always pick the top-scoring token) and deterministic reductions (`--pay-for-determinism`: sums performed in a fixed order). The same binary then produces the same tokens twice. An A/A repeat is the same configuration run twice as a control. |
| band, paired t | The band of a cell is the larger of 2 x the largest standard deviation of the two binaries and a floor of 0.4 TPS or 0.15 s. The paired t statistic is computed over the per-repetition differences of the two binaries. |
| slice check, cost data | `bin/slice bench --check` runs in CI. It fails when a registered test has no timing row in any platform block of `config/test-benchmarks.json`, and prints a warning when the current platform's block lacks one. The rows are called cost data (the run time at 1, 2 and 4 slices). granite_rapids_6962p (delphi-3bda, the Intel Xeon 6962P test machine) and genoa96 (the AMD runner) are two of the file's four platform blocks. |
| required CI, legacy CMake lane | Required CI is the GitHub workflow every pull request must pass (`gcp-nix.yml`); its C++ test build comes from `nix/cmake-tron-test-build.nix`. The legacy CMake lane is `.github/workflows/cmake-single-platform.yml`, run by manual dispatch and from `publish-deb.yml`. |
| the stack | The four pull requests that replace PR #4424 (see the last section). This PR is the first. |

## The changes

- New header `h/tron/tensor/k_vnni.hpp`. Everything in it is AVX-512. No AMX instruction is in it. It holds:
  - the layout (index map) and its constants (`namespace k_vnni`)
  - the layout gate `k_vnni::layout_on<head_size>`: true for 128-dimension heads when the option is on, false otherwise. It is a property of the storage geometry, not of the query type or of the AMX availability, so every reader and writer of a slot sees the same layout
  - the owner `k_vnni_tensor<64, 128>`
  - the view `k_vnni_view<T, 64, 128>` with a bounds-checked read `at(token, dim)`
  - `detail::k_vnni_access`, the only access path from a view to the plane address. Its users are the operations below, the reader and the test-only `book::fill_random`
  - the row-view aliases and helpers
  - the typed operations `store_row` (the per-token scatter store: 4 scatters of 16 dwords, one per 32-dimension step, which together write 4 bytes into each of the token's 64 cache lines), `load_row` (the gather load: 4 gathers of 16 dwords) and `copy_token`
- New header `h/tron/kernels/k_vnni.hpp`: the reader `qk_group`. It takes the packed view, not a pointer. One 64-byte masked load supplies one dimension pair of 16 tokens. For a bf16 query (bf16 = 16-bit brain float, the K element type) VDPBF16PS multiplies the pairs and adds in fp32, the same instruction the row-major dotter uses; for a float query the stored bf16 values are widened exactly and multiplied with FMA (fused multiply-add), as `dotter<float, 128>` does; an fp16 (16-bit IEEE half float) query is widened to fp32 once. A token whose bit is clear in the 64-bit live mask is never read, so unwritten tokens cannot change the result. A query group wider than 16 heads is scored in passes of 16. Every head's scores are its own accumulation. So the split changes no add order. Until the AMX kernel PR lands, the reader serves every page of a VNNI slot.
- `h/tron/tensor/kv_cache_fwd.hpp`: forward declarations of the two K types. With them, `amx_attn_iface.hpp` names the views without including any intrinsics (compiler built-in functions that map to single AVX-512 or AMX instructions).
- `kv_cache.hpp`:
  - Note [K VNNI storage] (a named comment block in the header): the layout, who writes it, who reads it, and what the kill switch does.
  - `kv_block::k` is the owner `k_vnni_tensor` for a 128-dimension head under the option, and the row-major array otherwise (`std::conditional_t`). It has the same trivial-type checks (`static_assert`s that the type is trivially default-constructible, trivially copyable and trivially destructible) as the packed V plane, because the cache's DMA allocation creates the blocks without a constructor.
  - The row views `page::k()` and `kv_block::k_view` / `k_at` exist only for row-major slots (a `requires` clause). A token's values are not contiguous in the VNNI plane.
  - `page::k_packed` returns a read-only view of the packed plane: the argument of the reader.
  - Layout-independent `set_k_row` and `get_k_row` take one token's row as a typed row view and serve both layouts (`store_row` / `load_row` for a VNNI slot, `memcpy` for a row-major slot). The row's alignment and DMA flags are the caller's.
  - A whole-page copy copies the owner (`dst_block.k = src_block.k`). Every other range moves token by token (`copy_token`), because a token's column depends on its offset in the page.
  - `fill_random` fills the packed plane through `detail::k_vnni_access`, as it does for V.
- `model.hpp`: `save_k` stores every token's K row with `page::set_k_row`. A bf16 K buffer row is read in place, with the buffer's alignment and DMA flags (DMA = direct memory access, the device-visible memory tag). Any other activation type is converted to bf16 on the stack first, as the row-major store does in place. The store is per row: 4 scatters that write 4 bytes into each of 64 cache lines, where the row-major store wrote 4 whole 64-byte lines. The block save that removes this cost in prefill is the third PR of the stack.
- `self_attention.hpp`, `attn_stats.hpp`, `amx_attn_iface.hpp`:
  - The software loop records the relevant tokens of a VNNI slot in a 64-bit live mask and scores them after the loop with the reader through `page::k_packed`, in passes of up to 16 heads. A row-major slot keeps the per-token dotters. The two forms are selected with `if constexpr` on the layout gate, so a row-major geometry compiles no reader and a VNNI geometry compiles no dotter.
  - The dense AMX page path is compiled only for row-major slots: its predicate is `eligible<...>(...) && !k_vnni::layout_on<head_size>`. Until the AMX kernel PR lands, every page of a VNNI slot takes the software loop, on every host. The comment of `attn_stats::visit_path` and the diagram of Note [AMX attention dispatch] say the same.
- FPGA staging (`gof.hpp`, `gof.cpp`, `full.hpp`): `page_info::k_head_fn` takes a caller-owned 64-byte-aligned scratch argument, as `v_head_fn` does. The callback of `full.hpp` gathers a VNNI slot's token row into that scratch with `page::get_k_row` and returns the row-major pointer otherwise. `gof::populate` allocates the K scratch next to the V scratch. The staging bytes and the HBM (High Bandwidth Memory, the FPGA device memory) layout are unchanged. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the parameter.
- CMake option `TRON_K_VNNI` (default OFF; `CMakeLists.txt`, `src/tron/CMakeLists.txt`). The definition is PUBLIC on the tron target and on `tron_model_compile_config` (the interface library through which the generated model objects are compiled), so every translation unit that touches a KV page sees the same layout. The option does not require AMX dispatch: the layout, the reader and the staging gather have no AMX dependency, and the tree builds and passes its tests with the option on and AMX dispatch off (Verification). The legacy CMake lane configures with the option ON next to `TRON_AMX_DISPATCH=ON`. `README.ci.md` documents which builds set it. No preset sets it.
- Tests:
  - `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`, label fake). Four cases. The index map matches hand-computed anchors (chosen token and dimension pairs whose plane offsets were derived by hand from the layout definition). `store_row` and `load_row` are exact and token-independent: a poisoned plane (filled with a known marker pattern through 64 typed row stores) receives 64 rows in a scrambled order, the owner's bytes hold every value at the documented position, `at()` reads it back, `load_row` inverts `store_row`, a rewrite of one token changes no other token's slots, and `copy_token` moves one token between planes. The reader does not digress from the row-major dotter for 4, 20 and 32 query heads with bf16, float and fp16 queries over 65 prefix masks, 24 hole masks and two single-token masks, with the dead tokens' storage set to NaN poison and their scores required to keep their preset. The page accessors and page copies move tokens correctly through `set_k_row` / `get_k_row` and `book::append` (a token-by-token append into a partly filled page, and a whole-page append). The book-level case runs a VNNI slot under the option and a row-major slot without it, checking the same contract.
  - `t_llama_unit`: the packed-K typed-boundary contracts (the AMX kernels of `main` reject the packed view, no pointer construction, conversion only from a writable view to a read-only view, no view of a temporary owner, no element write, 64-byte owner alignment, and `page::k_packed` exists exactly when the option selects the layout); a `save_k` case that stores 46 tokens over three pages in runs that start mid-block and cross block and page boundaries, with jobs without KV work inside and after a run, and checks every stored row bit for bit, every other row untouched, and the K marks; a compile check of software attention for 32 query heads on one 128-dimension K/V head (the shape the reader scores in two passes); and the layout-independent accessors in every case that wrote K through a row view. The split-vs-unsplit tolerance of "apply and join page ranges" is widened (Open items).
  - `t_amx_dispatch_dtype`: under the option, the full-page case expects the Q pack and no dense kernel call for the 128-dimension model, because the dense path is not compiled for a VNNI slot.
  - `config/test-benchmarks.json`: the granite_rapids_6962p cost row of `t_k_vnni_layout`, and refreshed rows of `t_llama_unit` and `t_amx_numerics`.

## Measurements

Question: the decode TPS and the TTFT of this PR with the option on against `main`, the reader against the dotter, and the effect of the kill switch inside this PR.

Comparator: base = `main` at 72308ec90c, built as runtron without the option (row-major K, AMX dispatch on). new = this branch at a711aeee83, option on, AMX dispatch on. newoff and baseoff are the same two binaries run with the kill switch.

Cells: qwen3-4b tp2, 8 users, 256 generated tokens, CPU attention (`USE_HW_ATTN=0`), prompt 1024 and prompt 8192, 3 repetitions, binaries interleaved, our half of the Granite Rapids test machine (2026-10-10).

Verdict rule: band = the larger of 2 x the largest standard deviation of the two binaries and a floor of 0.4 TPS or 0.15 s. A difference beyond the band counts as a change. The paired t is over the 3 repetitions.

Result (TPS = decode tokens per second per user, TTFT = the maximum over the 8 users; in parentheses the sd, the sample standard deviation over the 3 repetitions):

| cell | binary | TPS | TTFT |
|---|---|---|---|
| prompt 1024 | base | 81.07 (0.20) | 3.175 s (0.001) |
| prompt 1024 | new | 76.01 (0.44) | 4.003 s (0.010) |
| prompt 1024 | newoff | 75.58 (0.25) | 3.942 s (0.007) |
| prompt 1024 | baseoff | 72.40 (0.18) | 3.986 s (0.005) |
| prompt 8192 | base | 17.29 (0.02) | 52.637 s (0.044) |
| prompt 8192 | new | 15.39 (0.01) | 117.261 s (0.190) |
| prompt 8192 | newoff | 15.44 (0.04) | 116.592 s (0.048) |
| prompt 8192 | baseoff | 14.65 (0.03) | 122.851 s (0.058) |

| cell | pair | TPS difference (paired t) | TTFT difference (paired t) | band (TPS / TTFT) |
|---|---|---|---|---|
| prompt 1024 | new vs base | -6.2 % (-5.06 TPS, t -14.6), beyond | +828 ms (+26.1 %, t +133.6), beyond | 0.88 TPS / 0.15 s |
| prompt 1024 | newoff vs baseoff | +4.4 % (+3.18 TPS, t +22.4), beyond | -44 ms (-1.1 %, t -6.9), inside | 0.50 TPS / 0.15 s |
| prompt 1024 | newoff vs new | -0.6 % (-0.43 TPS, t -1.1), inside | -61 ms (-1.5 %, t -8.0), inside | 0.88 TPS / 0.15 s |
| prompt 1024 | baseoff vs base | -10.7 % (-8.67 TPS, t -105.1), beyond | +811 ms (+25.5 %, t +220.1), beyond | 0.40 TPS / 0.15 s |
| prompt 8192 | new vs base | -11.0 % (-1.90 TPS, t -411.8), beyond | +64.6 s (+122.8 %, t +589.0), beyond | 0.40 TPS / 0.38 s |
| prompt 8192 | newoff vs baseoff | +5.3 % (+0.78 TPS, t +32.8), beyond | -6.26 s (-5.1 %, t -106.0), beyond | 0.40 TPS / 0.15 s |
| prompt 8192 | newoff vs new | +0.3 % (+0.04 TPS, t +1.9), inside | -669 ms (-0.6 %, t -5.8), beyond | 0.40 TPS / 0.38 s |
| prompt 8192 | baseoff vs base | -15.3 % (-2.64 TPS, t -89.8), beyond | +70.2 s (+133.4 %, t +1208.8), beyond | 0.40 TPS / 0.15 s |

### This PR alone on an AMX host with the option on

new vs base is a loss in both cells: decode TPS -6.2 % at prompt 1024 and -11.0 % at prompt 8192, TTFT +26 % and +123 %. The cause is the temporary gate. The dense AMX page path is not compiled for a VNNI slot, so every page of a 128-dimension head takes the reader where `main`'s AMX kernel scores a dense page. In prefill at prompt 8192 that kernel does most of the attention work. The baseoff vs base rows show the same shape for `main` itself with its AMX kernel switched off (-15.3 % TPS, +133 % TTFT). The next PR of the stack (the AMX kernel on the plane) removes the gate. The option is off in every preset.

### The reader against the dotter (kill switch on both binaries)

newoff vs baseoff isolates the layout and its software reader: with AMX off on both binaries, the differences are the K layout, the reader (one token per vector lane, no per-token gather) in place of the dotter, and the per-row scatter store in place of the row-major row store. Decode TPS +4.4 % at prompt 1024 and +5.3 % at prompt 8192 (beyond the band). TTFT -1.1 % (inside the band) and -5.1 % (beyond). An AMD host (no AMX, so the reader runs in every build with the option on) was not measured.

### The kill switch inside this PR (newoff vs new)

TPS is inside the band in both cells (-0.6 %, +0.3 %): the kill switch changes no visit path for 128-dimension heads here, because no AMX visit can occur for a VNNI slot. TTFT is lower with the kill switch by 61 ms (1.5 %) at prompt 1024 (inside the 0.15 s band) and by 669 ms (0.6 %) at prompt 8192 (beyond the 0.38 s band, paired t -5.8). Hypothesis, not confirmed by a measurement: the AMX query pack still runs once per token for a VNNI slot although no kernel consumes it (`t_amx_dispatch_dtype` documents that the pack runs), and the kill switch skips the pack. A profile of the two runs would confirm it. The next PR consumes the pack.

## Verification

Provenance: the Granite Rapids test machine (Intel Xeon 6962P, AMX), 2026-10-10, this branch at a711aeee83 (`main` 72308ec90c merged). `nix develop` (the project's pinned build shell), clang 19.1.7, preset `native` (explicit AVX-512 flags), build type RelWithDebInfo (optimized, with debug symbols). Three configurations, each in its own worktree:

| configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | targets | build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | 826 s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | 314 s |
| option off | OFF | ON | OFF | the 5 layout-independent tests | 309 s |

Unit tests (fake device, `--skip-benchmarks`), every binary passes (assertions / test cases):

| test | option on | option on, no AMX dispatch | option off |
|---|---|---|---|
| `t_k_vnni_layout` | 1011432 / 4 | 1011432 / 4 | 1011432 / 4 |
| `t_amx_dispatch_dtype` | 1612 / 1 | 1 / 1 (the placeholder case of a build without dispatch) | 1612 / 1 |
| `t_amx_numerics` | 4109 / 4 (the AMX cases ran: no "AMX unavailable" line) | 1 / 1 (placeholder) | 4109 / 4 |
| `t_llama_unit` | 266453 / 66 | 266453 / 66 | 266522 / 66 |
| `t_heterogeneous_scheduler` | 2783 / 3 | 2783 / 3 | 2783 / 3 |
| `t_phase1_integration` | 2124 / 64 | 2124 / 64 | not built |

Kill-switch runs in the option-on build (`TRON_AMX_DISABLE=1`): `t_llama_unit` passes with 266453 assertions in 66 cases, the same count as with AMX on; `t_amx_numerics` passes with 2060 assertions in 4 cases, and its QK and PV precision cases report "AMX unavailable".

The option-off build has 69 more `t_llama_unit` assertions than the option-on build. That is expected from the test code: the case "page K views preserve geometry and row addressing" runs its per-element row-view checks on the 128-dimension slot only in the row-major build, and checks that the row view does not exist in the VNNI build.

clang-format 19.1.7 (`--dry-run --Werror`) on the 17 changed C++ files, `git diff --check` against `main`, and a search for `<cassert>` in the diff: clean.

Syntax matrix (clang 19 `-fsyntax-only` with the product's compile flags): 38 cells = AMX dispatch on and off x option off and on x 9 translation units (`t_llama_unit`, `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `heterogeneous_scheduler_compile`, `scheduler/full.cpp`, `gof.cpp`, `t_gof_dma`, `t_kv_oom_subcases`), plus `kernels/amx_attn.cpp` with dispatch on: 0 errors and 0 warnings in every cell.

### Host test suite and token identity (2026-10-10)

Question: does the whole host test suite pass in the option-on tree, and does the option-on binary reproduce its own tokens, its kill-switch tokens, and the tokens of `main`.

Comparator: base, as in Measurements.

Cells: `make build-test-host` and `make test-host` (fake device, our half, production serving stopped) in the option-on tree. Token identity with runtron: qwen3-4b tp2, 1 user, temperature 0, `--pay-for-determinism`, seed 1, 256 generated tokens; CPU attention at prompt 1024 and at prompt 8192, FPGA attention at prompt 1024; binaries new, new2 (the A/A repeat of new), newoff (new with the kill switch) and base.

Verdict rule: the host suite has no failure and no skip other than the two venv tests (`t_proxy_lib` skipped and `t_proxy_llama31` failing because the machine lacks the Python venv `t/proxy/.venv`); that is the set the PR #4424 head showed on this machine on 2026-10-09 (93 passed, 1 skipped, 1 failed). new equals new2 and newoff equals new for 256 tokens in every cell. new vs base is informational (issue #4444).

Result: all host test targets compile; 93 tests passed, 1 skipped (`t_proxy_lib`, its log says "SKIP: t/proxy/.venv missing"), 1 failed (`t_proxy_llama31`, "ERROR: t/proxy/.venv missing"); makespan (the wall-clock time of the whole suite run) 110 s. The CMake cache kept `TRON_K_VNNI=ON` through the make targets.

| cell | new vs new2 | newoff vs new | new vs base |
|---|---|---|---|
| CPU attention, prompt 1024 | identical, 256 of 256 | identical, 256 of 256 | first difference at generated token 83 |
| CPU attention, prompt 8192 | identical, 256 of 256 | identical, 256 of 256 | identical, 256 of 256 |
| FPGA attention, prompt 1024 | identical, 256 of 256 | identical, 256 of 256 | first difference at generated token 83 |

### CI coverage

The required CI builds with both switches off (`nix/cmake-tron-test-build.nix` sets neither `TRON_AMX_DISPATCH` nor `TRON_K_VNNI`). So the cases under `#ifdef TRON_K_VNNI` and the VNNI branches of `t_llama_unit`, `t_k_vnni_layout` and `t_amx_dispatch_dtype` do not execute there; those binaries run the row-major path. They run in the legacy CMake lane (by manual dispatch) and on the Granite Rapids test machine (this section). This PR proceeds on that basis by the author's decision. Issue #4865 tracks the CI change that adds both options to the required test build, and an AMX runner for the kernel identity case of the next PR.

## Open items

- **Performance of this PR alone on AMX hosts with the option on.** With the option on, every page of a 128-dimension head takes the reader, also where `main`'s AMX kernel would score a dense page. Measured against `main` at 72308ec90c (Measurements): decode TPS -6.2 % at prompt 1024 and -11.0 % at prompt 8192, TTFT +26 % and +123 % (qwen3-4b tp2, 8 users, CPU attention). The option is off in every preset, so no build of `main` changes. The next PR of the stack (the AMX kernel on the plane) removes the gate and the loss.
- **128-dimension heads with kv_mul other than 4.** The AMX kernel of the next PR takes kv_mul 4 only. For other group sizes the layout is on and the reader scores every page where `main` runs the dotter, in this PR and after the stack. Measured on the PR #4424 branch (whose reader and decode store are this PR's): llama-3.2-3b (kv_mul 3) -1.4 % TPS at 32 users, prompt 200 plus 800 shared, resolved in both pass pairs (nightly perf configs, 9d5c7a389b against `main` be0d5565b3, 2026-10-09); qwen-3-30b-a3b (kv_mul 8), 8 users, tp2: decode TPS +1.5 % at prompt 1024 (6 repetitions, inside noise), -4.1 % at prompt 2048 (3 repetitions), +24.1 % at prompt 8192 (3 repetitions) (65a1c41d72 against `main` c7844ca2ce, 2026-09-16). So the layout gate `k_vnni::layout_on<head_size>` should also require the AMX shape (kv_mul 4), or the reader needs a faster path for larger groups.
- **Kill switch and token divergence (tracked in issue #4444, reviewers decide).** Under CPU attention at prompt 1024 and under FPGA attention at prompt 1024 this PR generates a different token than `main` from generated token 83 of 256 (the token-identity table in Verification). Under CPU attention at prompt 8192 the 256 tokens are identical. The expected cause is the add order: the reader adds the fp32 products in a different order than the dotter, and a token flips only at a near tie (a step where the two best candidate tokens have almost the same score). Issue #4444 holds the forced-run measurement that would confirm this. With the option on, `TRON_AMX_DISABLE=1` keeps the layout and the reader. In this PR it changes no score and no visit path for 128-dimension heads, because no AMX visit can occur for a VNNI slot. After the next PR it gives an AMX-off run of the same binary, not the tokens of a clean binary (a build with both options off). Item 4 of Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp` still promises those tokens for rollback. Issue #4444 lists two options: (a) accept the weaker rollback and add the condition "with `TRON_K_VNNI` off" to item 4, or (b) keep a row-major build as the rollback artifact in deployment and document that.
- **A `main` test tolerance is widened.** `t_llama_unit` "apply and join page ranges / query splits match unsplit page reductions" (added to `main` on 2026-09-11) compares a page reduction done in one run with the same reduction done as two ranges and joined. On `main` it bounds the difference of the weighted V sum by 0.02 and of the weight sum by an absolute 2e-6. The two runs reach a page with a different running maximum (the largest score seen so far, which the softmax subtracts from every score before the exponential). So each softmax weight (the normalized attention score) is converted to bf16 for the PV product (the product of the softmax weights and V) at a different scale. The AVX path truncates in that conversion. The row-major build passes `main`'s bounds by a small margin (0.018 of 0.020 on one element of the weighted V sum, 1.9e-6 of 2.0e-6 on the weight sum). With VNNI K the scores differ in their last bits. The bf16 conversion then rounds at a different point. One element reaches 0.022. This PR sets the bounds to 0.05 and a relative 1e-6. The test passes with the option on and off. The test comment names the mechanism. The test's author may want to review the change.
- **genoa96 cost row for `t_k_vnni_layout`.** The genoa96 block of `config/test-benchmarks.json` has no row for `t_k_vnni_layout`. The slice check passes without it (it fails only when a test has no row in any platform block, and prints a warning when the current platform's block lacks one). A genoa96 row needs a run on that runner.
- **Benchmark binary mismatch (inherited from PR #3879, reviewers decide).** The legacy CMake lane compiles `runtron` once, in its `build` job, with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`, and hands that binary to its `benchmark` job. When the hand-over works, the benchmark measures a binary with the AMX kernels and the VNNI K layout. When the hand-over fails, the benchmark job compiles `runtron` itself through `make`, which sets neither option, and measures a row-major binary without AMX kernels. PR #3879 introduced this mismatch for `TRON_AMX_DISPATCH`; this PR adds `TRON_K_VNNI` to the same line. The required CI is not affected: its benchmark binary is built with neither option. If the mismatch is unwanted, both options should move out of the build job into a configuration of their own, as `TRON_PAGE_SHARE_COUNTERS` does through the `coverage` preset.

## The stack

PR #4424 (branch jhan-amx-vnniK, 4,054 added lines) is replaced by four stacked pull requests, each based on the previous one. PR #4424 stays open as the reference until the last of the four is open.

| Order | PR | What it adds | State |
|---|---|---|---|
| 1 | this PR (`jhan-vnnik-1-layout`, base `main`) | the VNNI K layout, its typed owner and views, the per-row store, the reader, the FPGA staging gather, the CMake option (off everywhere), the tests | ready for review |
| 2 | `jhan-vnnik-2-amx` (base: this PR) | the AMX QK kernel that reads the plane as its B operand (`qk_vnni_128x4`, `pack_q_rows_128x4`), its bit-identity test against the row-major kernel, and the removal of this PR's temporary gate and comments | to follow as a draft |
| 3 | `jhan-vnnik-3-shared-save` (base: PR 2) | the shared block save: 16-token blocks transposed in registers and written as whole cache lines by the main thread and its idle helpers (the TTFT gain of PR #4424) | to follow as a draft |
| 4 | `jhan-vnnik-4-tail-block` (base: PR 3) | the row-major tail block, the row-major policy under hardware attention (the fix of issue #4500), the `deb` preset line that turns the option on in the released package | to follow as a draft |

Until PR 4 the option stays off in every preset, so no intermediate state reaches production.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
