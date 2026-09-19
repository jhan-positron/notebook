## Short version

This branch stores the K cache of 128-dimension heads (attention heads whose key vector has 128 values) in the AMX VNNI layout at the moment it is written. The AMX attention kernel then reads K without a transpose, and no second copy of K exists. Compared to baseline AMX (PR #3879), TTFT, Time To First Token, is faster and decode throughput is higher at 2K or longer prompts.

## Status

This PR is a draft on top of `jhan-amx-p0` (PR #3879). The re-verification of this exact head (the latest commit of the branch, `bb325d0a6e`) on delphi-3bda (the shared Intel Granite Rapids CI machine).

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
| base | The PR #3879 binary (commit 544ca05c7a, row-major K). |
| greedy run, A/A repeat | A run with temperature 0 (always pick the top-scoring token) and deterministic reductions (sums performed in a fixed order, so the result does not depend on thread timing). The same binary then produces the same tokens twice. An A/A repeat is the same configuration run twice as a control. |
| slot | One persistent K/V storage region of the cache (one per layer, or shared between layers), described by a `kv_slot_spec`. A row-major slot keeps K in the row-major layout. |
| slice check, cost data | `bin/slice bench --check` in the CMake CI job requires a timing row for every registered test in `config/test-benchmarks.json`. The rows are called cost data. genoa96 and granite_rapids_6962p are the platform blocks of that file. |

## The changes

- New header `h/tron/kernels/k_vnni.hpp`. Everything in it is AVX-512. No AMX instruction is in it. It holds:
  - the layout (index map),
  - the per-token scatter store and gather load,
  - the 16-token block save (transpose in registers, full cache line stores),
  - an AVX-512 reader of the layout for partial pages, hosts without AMX and the kill switch.
- `kv_cache.hpp`: Note [K VNNI storage] (a named comment block in the header that documents the layout). The row view `page::k()` exists only for row-major slots (see the Words table). Layout-independent `set_k_row`, `get_k_row` and `set_k_block` serve both layouts. Page copies move whole pages with one memcpy. Other ranges are copied token by token.
- `model.hpp`: Note [Shared block save]. `save_k` cuts the pass into work units. It shares the store with the main helpers (`save_k_helper`). The workers are joined on one counter with a 120-s watchdog (the join aborts with an error if the helpers have not finished after 120 s). The handwritten plugins pass one worker and store serially. The unit tests pass one worker. The exception is the shared-save case of `t_llama_unit`. That case passes three workers.
- `common.hpp`: the state of one shared block save, called a window in the code (`batch::k_store_window`: claim counter, open and finished counters, the unit table).
- `self_attention.hpp`, `amx_attn.cpp`, `amx_attn_iface.hpp`: the dense AMX page reads the VNNI plane as its B operand (`qk_vnni_128x4`). A dense page is a full 64-token page, all of it visible to the query. It is the case the AMX kernel handles. The VNNI plane is the K storage in the VNNI layout. `qk_vnni_128x4` is bit-identical to the row-major kernel by test. The software path scores the live tokens (the tokens present in the page) in one AVX-512 loop over the page.
- FPGA staging, the code that copies K and V rows into the buffers the FPGA reads (`gof.hpp`, `gof.cpp`, `full.hpp`): `k_head_fn` writes a token's K row into a scratch buffer (temporary memory) that the caller owns. `v_head_fn` already worked that way. `gof::populate` allocates the scratch. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the parameter.
- Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k_helper` at the attention statement of every KV-writing operation. `save_k` receives the worker count.
- CMake option `TRON_K_VNNI` (default OFF, requires `TRON_AMX_DISPATCH`, the CMake option of PR #3879 that compiles the AMX kernels). Files: `CMakeLists.txt`, `src/tron/CMakeLists.txt`. The CMake CI job sets it ON (`.github/workflows/cmake-single-platform.yml`). `README.ci.md` documents the flag.
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

Done on delphi-3bda. Setup: `nix develop` (the project's pinned build shell), clang 19, `TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON`. Results:

- clang-format-19 (the code formatter) reports no change on every changed C++ file.
- Full build of runtron and the four unit tests (641 s on 72 cores): finished with no errors.
- `t_k_vnni_layout` 5 cases / 63426 assertions, `t_amx_numerics` 5 / 4621 (real AMX), `t_amx_dispatch_dtype` 1 / 1559, `t_llama_unit` 30 / 122438: all pass, the same counts as before the cleanup.
- Haskell code-generator test suite (`cabal test` of the `tron-ingest` package in `ingest/`): pass.

Cells (one cell = one measured configuration of prompt length, tp and binary) on the head (prompt 1024, 8 users, 2 repetitions, CPU attention with AMX):

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
- Token divergence of llama-3.1-8b and of the mixture-of-experts model qwen-3-30b-a3b (MoE: each token runs only a subset of the layer's expert sub-networks): both come from the software reader of the layout. That reader adds the fp32 products in a different order than the row-major dotter. Both outputs are fluent continuations of the same text. This attribution is the numerics contract of Note [AMX attention dispatch], not a measurement of the scores themselves.
- qwen-3-30b-a3b decode (-5.4% TPS, one run): see section 6.
- Log gap: in the gpt-oss-120b cell of this head one of the eight completion lines is missing from the log. The other seven agree. The base run had one early stop at 110 tokens.

Cost data: `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics` ran on the idle machine after the runs above. The resulting rows are in the last commit.

## Open items

- **128-dimension heads with kv_mul other than 4 (measure before merging).** For qwen-3-30b-a3b (kv_mul 8) the VNNI layout is on. The AMX kernel is not eligible for that shape. So every page goes through the AVX-512 reader of the layout instead of the row-major dotter. The decode store also scatters into cold lines (64-byte cache lines not yet present in the CPU cache). One run showed -5.4% decode TPS (a loss: 34.3 vs 36.3 TPS/user) and -7% TTFT (a gain of 369 ms; lower TTFT is better) against base. If more repetitions confirm the decode loss, the layout gate `k_vnni::layout_on<head_size>` should also require the AMX shape (kv_mul 4), or the reader needs work for larger groups (more query heads per KV head). Not measured further here.
- **Cost data.** The row of `t_k_vnni_layout` and refreshed rows of `t_llama_unit` and `t_amx_numerics` are in the head (granite_rapids_6962p block). The genoa96 block gets its rows from the weekly refresh.
- **Benchmark artifact (reviewer decision).** The CMake build job bundles its `gen/runtron` as the benchmark artifact. With this PR that binary stores K in the VNNI layout. So the CI benchmark job measures the VNNI layout when it uses the artifact. When it rebuilds locally, it measures the row-major layout. PR #3879 already did the same with `TRON_AMX_DISPATCH=ON`. If that mix is unwanted, the option needs its own configuration instead of the build job.
- **Decode store (not blocking).** In decode, Save K takes 28 to 35 us per layer for the 8 tokens of a decode pass (the 1024-token prefill pass takes 60 to 80 us). Decode writes one token per user per step. Every line it writes is therefore cold. Today the store overlaps with work that the attention workers already have ready. So it adds no wall-clock time. Candidates: stripe decode tokens over the helpers, or prefetch the token's lines early in the layer. Unmeasured.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

