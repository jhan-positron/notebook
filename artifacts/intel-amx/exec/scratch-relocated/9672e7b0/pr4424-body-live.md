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
| VNNI layout | The pair-interleaved K layout: the two values of one dimension pair sit next to each other, and one 64-byte row holds that dimension pair for 16 tokens. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. |
| row-major K | The layout of PR #3879 and of `main`: one row of 128 values per token. |
| main thread, main helpers | The generated plugin (the model code that the code generator emits) runs a pass on one main thread. A fixed set of helper threads runs the per-token kernels in stripes (interleaved slices of the token range, where each of the n helpers takes every n-th token). |
| save_k, Save K | The function (`model.hpp`) that copies the K rows of one pass into the KV cache, once per layer (one of the model's repeated transformer blocks) per pass. |
| shared block save | The K store of this branch. The pass's tokens are cut into work units (runs of consecutive tokens inside one 16-token block of a page). The main thread and the idle main helpers claim the units from one counter. A unit of two or more tokens is written with 16 rows transposed in registers, one 64-byte line at a time, masked when the unit does not fill the block. A unit of one token is written with a scatter (many small stores, each to a separate address). |
| dotter | The per-token AVX-512 dot-product loop of the software attention path (`tron/kernels/dotter.hpp`). |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels and runs the software path. |
| base | The PR #3879 binary (commit 544ca05c7a, row-major K; the base of this branch before the 2026-09-15 rebase). |
| greedy run, A/A repeat | A run with temperature 0 (always pick the top-scoring token) and deterministic reductions (sums performed in a fixed order, so the result does not depend on thread timing). The same binary then produces the same tokens twice. An A/A repeat is the same configuration run twice as a control. |
| slot | One persistent K/V storage region of the cache (one per layer, or shared between layers), described by a `kv_slot_spec`. A row-major slot keeps K in the row-major layout. |
| slice check, cost data | `bin/slice bench --check` in the CMake CI job requires a timing row for every registered test in `config/test-benchmarks.json`. The rows are called cost data. genoa96 and granite_rapids_6962p are the platform blocks of that file. |


## The changes

- New header `h/tron/kernels/k_vnni.hpp`. Everything in it is AVX-512. No AMX instruction is in it. It holds:
  - the layout (index map),
  - the per-token scatter store and gather load,
  - the 16-token block save (transpose in registers, full cache line stores),
  - an AVX-512 reader of the layout for partial pages, hosts without AMX and the kill switch.
- `kv_cache.hpp`: Note [K VNNI storage] (a named comment block in the header that documents the layout). The row views `page::k()` (per token, and main's whole-page view) exist only for row-major slots (see the Words table). Layout-independent `set_k_row`, `get_k_row` and `set_k_block` serve both layouts. Page copies move whole pages with one memcpy. Other ranges are copied token by token.
- `model.hpp`: Note [Shared block save]. `save_k` cuts the pass into work units. It shares the store with the main helpers (`save_k_helper`). The workers are joined on one counter with a 120-s watchdog (the join aborts with an error if the helpers have not finished after 120 s). The handwritten plugins pass one worker and store serially. The unit tests pass one worker. The exception is the shared-save case of `t_llama_unit`. That case passes three workers.
- `common.hpp`: the state of one shared block save, called a window in the code (`batch::k_store_window`: claim counter, open and finished counters, the unit table).
- `self_attention.hpp`, `amx_attn.cpp`, `amx_attn_iface.hpp`: the dense AMX page reads the VNNI plane as its B operand (`qk_vnni_128x4`). A dense page is a full 64-token page, all of it visible to the query. It is the case the AMX kernel handles. The VNNI plane is the K storage in the VNNI layout. `qk_vnni_128x4` is bit-identical to the row-major kernel by test. The software path scores the live tokens (the tokens present in the page) in one AVX-512 loop over the page.
- FPGA staging, the code that copies K and V rows into the buffers the FPGA reads (`gof.hpp`, `gof.cpp`, `full.hpp`): `k_head_fn` writes a token's K row into a scratch buffer (temporary memory) that the caller owns. `v_head_fn` already worked that way. `gof::populate` allocates the scratch. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the parameter.
- Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k_helper` at the attention statement of every KV-writing operation. `save_k` receives the worker count.
- CMake option `TRON_K_VNNI` (default OFF, requires `TRON_AMX_DISPATCH`, the CMake option of PR #3879 that compiles the AMX kernels). Files: `CMakeLists.txt`, `src/tron/CMakeLists.txt`. The legacy CMake workflow sets it ON (`.github/workflows/cmake-single-platform.yml`; on `main` that workflow runs by manual dispatch and from `publish-deb.yml`). `README.ci.md` documents the flag.
- Tests: `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`), a bit-identity case in `t_amx_numerics`, fakes (stand-in implementations used only by the test) in `t_amx_dispatch_dtype`, a model-level shared-save case and layout-independent accessors in `t_llama_unit`, call-text checks in `LoopyTronSpec.hs`.

## Measurements (qwen3-4b, 8 users, half of delphi-3bda, sw attention with AMX)

| prompt | binary | tp2 TTFT | tp4 TTFT | tp2 TPS/user | tp4 TPS/user |
|---|---|---|---|---|---|
| 1024 | base (PR #3879) | 3.150 s | 2.194 s | 79.7 | 103.6 |
| 1024 | this branch | 3.095 s (-56 ms) | 2.117 s (-77 ms) | 83.9 (+5.3%) | 103.9 (+0.2%) |
| 2048 | this branch vs base | -112 ms (base 7.254 s, -1.5%) | -120 ms (base 4.719 s, -2.5%) | +7.1% | -0.7% |
| 8192 | this branch vs base | -1.37 s (base 53.369 s, -2.6%) | -0.52 s (base 30.487 s, -1.7%) | +10.1% | +8.0% |

The tp4 decode numbers have a run-to-run spread of 1 to 3 TPS, that's 1 to 3% of 104 TPS. So the +0.2% and -0.7% at 1k and 2k are noises. 

- Decode gain: the gain grows with the prompt length.
- TTFT gain: the shared block save. Save K per prefill layer went from 274 us (base) to 60 to 80 us (this branch), measured with in-process Perfetto traces.

## Verification

All results in this section are of the pre-rebase head `bb325d0a6e`. The build and test results of the rebased head are under "Rebase verification" in the Status section.

Done on delphi-3bda. Setup: `nix develop` (the project's pinned build shell), clang 19, `TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON`. Results:

- clang-format-19 (the code formatter) reports no change on every changed C++ file.
- Full build of runtron and the four unit tests (641 s on 72 cores): finished with no errors.
- `t_k_vnni_layout` 5 cases / 63426 assertions, `t_amx_numerics` 5 / 4621 (real AMX), `t_amx_dispatch_dtype` 1 / 1559, `t_llama_unit` 30 / 122438: all pass, the same counts as before the cleanup.
- Haskell code-generator test suite (`cabal test` of the `tron-ingest` package in `ingest/`): pass.

Test (prompt 1024, 8 users, 2 repetitions, CPU attention with AMX):

| tp | binary | TTFT | TPS/user |
|---|---|---|---|
| tp2 | base | 3.141 s | 79.8 |
| tp2 | this head | 3.083 s (-59 ms, -1.9%) | 84.2 (+5.5%) |
| tp4 | base | 2.193 s | 105.6 |
| tp4 | this head | 2.120 s (-73 ms, -3.3%) | 106.8 (+1.2%) |

The base rows are another measurement of the same base binary. They differ from the Measurements table by 0.1 TPS at tp2 and 1.9 TPS at tp4, inside the run-to-run spread.

These reproduce the measurement section numbers (-56 ms and -77 ms). The greedy smoke test (1 user, 128 generated tokens) of this head produced the same 128 tokens as the measured binary. Its A/A repeat matched too.

The whole host test suite (the tests that run on the CPU host without an FPGA) ran with `TRON_K_VNNI=ON` on half of the machine. Commands: `make build-test-host`, then `make test-host` (= `bin/slice run --filter=host --exclude-tag=slow`). Result: all 302 test targets compile. 90 tests ran under the host filter without slow tests: 89 passed, 1 skipped, 0 failed. Total wall-clock time 107 s. `t_k_vnni_layout` passed under slice with 63426 assertions.

The one skipped host test is `t_proxy_lib`. Its Python venv (virtual environment) is absent on the machine. The test is unrelated to this branch.

Other generated models and FPGA attention were run at tp2 with prompt 1024. A smoke run is 1 user, greedy, 128 tokens. A cell is 8 users, 256 tokens, one run each.

| run | attention | smoke tokens, base vs this head | TTFT base / head | TPS/user base / head |
|---|---|---|---|---|
| qwen3-4b, FPGA attention (`USE_HW_ATTN` unset, the default of the nightly CI run) | FPGA | identical, 128 of 128 | 3.155 / 3.162 s | 125.4 / 123.7 (-1.4%) |
| gpt-oss-120b (64-dimension heads: layout off, `save_k_helper` returns at once) | CPU | identical, 128 of 128 | 4.311 / 4.304 s | 63.7 / 62.6 (-1.7%) |
| llama-3.1-8b (128-dimension heads, kv_mul 4 = four query heads per KV head, 32 layers) | CPU with AMX | first difference at token 46 | 4.309 / 4.279 s (-30 ms) | 78.6 / 83.1 (+5.7%) |
| qwen-3-30b-a3b (128-dimension heads, kv_mul 8: layout on, AMX kernel not eligible) | CPU, software path | first difference at token 5 | 5.204 / 4.835 s (-369 ms) | 36.3 / 34.3 (-5.4%) |

Reading:

- FPGA-attention run: the tokens are identical to base. 
- gpt-oss-120b: untouched by the layout, as designed.
- llama-3.1-8b: behaves like qwen3-4b (decode gain, small TTFT gain).
- Token divergence of llama-3.1-8b and of the mixture-of-experts model qwen-3-30b-a3b (MoE: each token runs only a subset of the layer's expert sub-networks). The scores of those runs were not recorded, so the cause is not measured. It follows from the numerics contract in the code and from the tests that enforce it:
  - Note [AMX attention dispatch] (`h/tron/kernels/amx_attn_iface.hpp`, paragraph "Numerics") says: "both code paths (AVX-512 and AMX) multiply bf16 inputs and add the products in fp32, in QK and in PV. For inputs that are finite and not subnormal, their outputs differ for exactly two reasons: 1. the bf16 rounding of the PV weights P = exp(s - max) [...]; 2. the order in which the fp32 products are added."
  - The VNNI software reader (`k_vnni::qk_group` in `h/tron/kernels/k_vnni.hpp`) states the same contract against the row-major dotter: "exact bf16 x bf16 products added in fp32 by VDPBF16PS. This is the same instruction the row-major dotter<bf16, 128> uses. Only the order of the fp32 adds differs (see Note [AMX attention dispatch])." The test case "VNNI K reader does not digress from the row-major dotter" in `t_k_vnni_layout` checks it: 91 live-token masks, bf16 and fp32 queries, envelope 1e-4 of the absolute-product mass plus 1e-6.
  - The dense AMX pages cannot differ at all: the test case "AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K" in `t_amx_numerics` requires equal bits.
  - So in llama-3.1-8b (kv_mul 4, AMX eligible) only the partial pages, which the software reader scores, can move a score. In qwen-3-30b-a3b (kv_mul 8, AMX not eligible) every page can. Each moved score stays inside the envelope above. A generated token changes only where the two best candidates are closer than that difference (a near tie). This last step is a hypothesis. The measurement that would confirm it is a forced run (teacher forcing) of both binaries on the same prompt, comparing the Top-k Logits record at the first divergent step.
  - Both outputs are fluent continuations of the same text.
- qwen-3-30b-a3b decode (-5.4% TPS, one run): see open items.

## Open items

- **Repeat the measurements against a `main` binary (before merging).** The rebased head builds and passes the unit tests and the host suite (Status). The TTFT and throughput cells and the model smoke runs in this description were measured before the rebase against the PR #3879 binary of that time. 
- **128-dimension heads with kv_mul other than 4 (measure before merging).** For qwen-3-30b-a3b (kv_mul 8) the VNNI layout is on. The AMX kernel is not eligible for that shape. So every page goes through the AVX-512 reader of the layout instead of the row-major dotter. The decode store also scatters into cold lines (64-byte cache lines not yet present in the CPU cache). One run showed -5.4% decode TPS (a loss: 34.3 vs 36.3 TPS/user) and -7% TTFT (a gain of 369 ms; lower TTFT is better) against base. If more repetitions confirm the decode loss, the layout gate `k_vnni::layout_on<head_size>` should also require the AMX shape (kv_mul 4), or the reader needs work for larger groups (more query heads per KV head). 
- **Benchmark binary mismatch (reviewers decide).** The legacy CMake workflow compiles `runtron` once, in its `build` job, with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`, and hands that binary to its `benchmark` job. When the hand-over works, the benchmark measures a binary with the AMX kernels and the VNNI K layout. When the hand-over fails, the benchmark job compiles `runtron` itself through `make`, which sets neither option, and measures a binary with row-major K and no AMX kernels. PR #3879 introduced this mismatch for `TRON_AMX_DISPATCH`. This PR adds `TRON_K_VNNI` to the same line. The default CI (GCP Nix) is not affected: its benchmark binary is built with neither option. If the mismatch is unwanted, both options should move out of the build job into a configuration of their own, as was done for `TRON_PAGE_SHARE_COUNTERS` with the `coverage` preset.
- **Kill switch** With `TRON_K_VNNI` on, `TRON_AMX_DISABLE=1` runs the VNNI reader (this PR's AVX-512 routine that scores tokens from the VNNI layout) instead of the row-major dotter for 128-dimension heads. The kill switch still gives an AMX-off run of the same binary. It no longer gives the tokens of a clean binary (a build with both options off). Item 4 of Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp` still promises those tokens for rollback. It needs the condition "with `TRON_K_VNNI` off". Note [K VNNI storage] in `kv_cache.hpp` describes the new behavior. 

🤖 Generated with [Claude Code](https://claude.com/claude-code)





