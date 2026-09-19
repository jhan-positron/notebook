## Short version

This branch stores the K cache of 128-dimension heads (attention heads whose key vector has 128 values) in the AMX VNNI layout at the moment it is written. The AMX attention kernel then reads K without a transpose, and no second copy of K exists. At prompt 1024 the time to first token drops by 56 ms (-1.8%) at tp2 and by 77 ms (-3.5%) at tp4, and decode throughput is unchanged or higher.

## Status

The K store itself was made fast enough for that result. The PR is a draft on top of `jhan-amx-p0` (PR #3879). The re-verification of this exact head (the latest commit of the branch, `bb325d0a6e`) on delphi-3bda (the shared Intel Granite Rapids test machine) is listed in section 5.

## Words used here

| Term | Meaning |
|---|---|
| tron, runtron | tron is the inference program. runtron is its command-line tool. runtron produced every number below. |
| AMX, AVX-512 | Intel Advanced Matrix Extensions (instructions that multiply tiles, 16-row by 64-byte register blocks) and Intel Advanced Vector Extensions 512 (512-bit vector instructions). The CPU attention path uses both. |
| VNNI layout | The pair-interleaved K layout: the two values of one dimension pair sit next to each other, and one 64-byte row holds that dimension pair for 16 tokens. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. |
| K, V, KV page | The key and value caches of attention. A KV page holds 64 tokens. |
| row-major K | The layout of PR #3879 and of `main`: one row of 128 values per token. |
| bf16, fp32 | 16-bit brain floating point (the storage format of K and V) and 32-bit float (the accumulator format). |
| prefill, decode | prefill is the batched processing of the prompt tokens. decode is the generation of tokens, one token per user per step. |
| pass | One forward call of the model over one minibatch. In the measured runs a prefill pass covers 128 tokens of each of 8 users, and a decode pass covers one token per user. |
| main thread, main helpers | The generated plugin (the model code that the code generator emits) runs a pass on one main thread. A fixed set of helper threads runs the per-token kernels in stripes (interleaved slices of the token range, where each of the n helpers takes every n-th token). |
| save_k, Save K | The function (`model.hpp`) that copies the K rows of one pass into the KV cache, once per layer (one of the model's repeated transformer blocks) per pass. |
| shared block save | The K store of this branch. The pass's tokens are cut into work units (runs of consecutive tokens inside one 16-token block of a page). The main thread and the idle main helpers claim the units from one counter. A unit of two or more tokens is written with 16 rows transposed in registers and one full 64-byte cache line per store. A unit of one token is written with a scatter (many small stores, each to a separate address). |
| dotter | The per-token AVX-512 dot-product loop of the software attention path (`tron/kernels/dotter.hpp`). |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels and runs the software path. |
| FPGA | Field-programmable gate array: the accelerator card that runs the matrix multiplies and, in the nightly setup (the continuous-integration run, CI, that executes every night), the attention. |
| TTFT, TPS | Time to first token (runtron's "Parsing the prompt took", the batched prefill of 8 prompts) and generated tokens per second per user in decode. |
| tp2, tp4 | The model split over two or four FPGA cards. |
| base | The PR #3879 binary (commit 544ca05c7a, row-major K). |
| delphi-3bda, our half | The shared Intel Granite Rapids test machine (Xeon 6962P). Another engineer uses the other half. Our half is one CPU socket and four FPGA cards. |
| greedy run, A/A repeat | A run with temperature 0 (always pick the top-scoring token) and deterministic reductions (sums performed in a fixed order, so the result does not depend on thread timing). The same binary then produces the same tokens twice. An A/A repeat is the same configuration run twice as a control. |
| qwen3-4b and the other models | qwen3-4b is the 4-billion-parameter Qwen3 model (128-dimension heads). It is the model of every measurement in sections 3 and 5 unless a row names another model. Section 5 also runs gpt-oss-120b, llama-3.1-8b and qwen-3-30b-a3b. |
| slot | One persistent K/V storage region of the cache (one per layer, or shared between layers), described by a `kv_slot_spec`. A row-major slot keeps K in the row-major layout. |
| Perfetto trace | An in-process timeline of tron's spans (named, timed code intervals), used to measure Save K per layer. |
| slice check, cost data | `bin/slice bench --check` in the CMake CI job requires a timing row for every registered test in `config/test-benchmarks.json`. The rows are called cost data. genoa96 and granite_rapids_6962p are the platform blocks of that file. |

## 1. What changes

- New header `h/tron/kernels/k_vnni.hpp`. Everything in it is AVX-512. No AMX instruction is in it. It holds:
  - the layout (index map),
  - the per-token scatter store and gather load,
  - the 16-token block save (transpose in registers, full-line stores),
  - an AVX-512 reader of the layout for partial pages, hosts without AMX and the kill switch.
- `kv_cache.hpp`: Note [K VNNI storage] (a named comment block in the header that documents the layout). The row view `page::k()` exists only for row-major slots (see the Words table). Layout-independent `set_k_row`, `get_k_row` and `set_k_block` serve both layouts. Page copies move whole pages with one memcpy. Other ranges are copied token by token.
- `model.hpp`: Note [Shared block save]. `save_k` cuts the pass into work units. It shares the store with the main helpers (`save_k_helper`). The workers are joined on one counter with a 120-s watchdog (the join aborts with an error if the helpers have not finished after 120 s). The handwritten plugins pass one worker and store serially. The unit tests pass one worker. The exception is the shared-save case of `t_llama_unit`. That case passes three workers.
- `common.hpp`: the state of one shared block save, called a window in the code (`batch::k_store_window`: claim counter, open and finished counters, the unit table).
- `self_attention.hpp`, `amx_attn.cpp`, `amx_attn_iface.hpp`: the dense AMX page reads the VNNI plane as its B operand (`qk_vnni_128x4`). A dense page is a full 64-token page, all of it visible to the query. It is the case the AMX kernel handles. The VNNI plane is the K storage in the VNNI layout. `qk_vnni_128x4` is bit-identical to the row-major kernel by test. The software path scores the live tokens (the tokens present in the page) in one AVX-512 loop over the page.
- FPGA staging, the code that copies K and V rows into the buffers the FPGA reads (`gof.hpp`, `gof.cpp`, `full.hpp`): `k_head_fn` writes a token's K row into a scratch buffer (temporary memory) that the caller owns. `v_head_fn` already worked that way. `gof::populate` allocates the scratch. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the parameter.
- Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k_helper` at the attention statement of every KV-writing operation. `save_k` receives the worker count.
- CMake option `TRON_K_VNNI` (default OFF, requires `TRON_AMX_DISPATCH`, the CMake option of PR #3879 that compiles the AMX kernels). Files: `CMakeLists.txt`, `src/tron/CMakeLists.txt`. The CMake CI job sets it ON (`.github/workflows/cmake-single-platform.yml`). `README.ci.md` documents the flag.
- Tests: `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`), a bit-identity case in `t_amx_numerics`, fakes (stand-in implementations used only by the test) in `t_amx_dispatch_dtype`, a model-level shared-save case and layout-independent accessors in `t_llama_unit`, call-text checks in `LoopyTronSpec.hs`.

## 2. Commits, in order

- `73125f5464` kv_cache: store K of 128-dim heads in the VNNI layout (TRON_K_VNNI)
- `351732f4b9` k_vnni: fp16 queries take the float path (static_assert moved into the else branch)
- `18ba069c95` clang-format-19 over the VNNI K change
- `85766f2fdc` t_k_vnni_layout: finite fill patterns and bit-exact row comparison
- `900de8c7b4` t_k_vnni_layout: keep the fill patterns distinct per token (bit 12 was masked out)
- `f66bb07542` save_k scatters a bf16 K row straight from the buffer; test anchors and guard
- `5e45ae55ae` clang-format-19 over the review fixes
- `9928cb2849` save_k: 16-token block store and helper striping for the VNNI K plane
- `10fc7c724c` save_k: page-block work units, one join counter, model-level test of the store
- `ec1be6dde4` save_k: remove the TRON_K_VNNI_BLOCK and TRON_K_VNNI_STRIPE measurement switches
- `58779d3ed6` VNNI K: apply the C++ coding guide to the code this branch adds
- `f3418e627f` ci: build and test the CMake lane with TRON_K_VNNI=ON
- `87f82708d7` VNNI K: plain English in the comments this branch adds
- `dc950be5f2` VNNI K: review corrections to comments, compile-time pins and the CI readme
- `bb325d0a6e` test: cost data for t_k_vnni_layout, t_llama_unit and t_amx_numerics (granite_rapids_6962p)

The first nine commits are the branch as measured. The last of them, `10fc7c724c`, is the binary of section 3. The next six are the cleanup for this PR:

- the two measurement switches removed. Both were on by default. The binary's behaviour is therefore unchanged.
- the C++ coding guide applied to the added code (named constants with their value in the name, braces on every control-flow body that is not on one physical line).
- the CI lane.
- the comments rewritten in plain English, with six factual corrections listed in that commit's message.
- corrections from a read-only review of the pushed head (listed in that commit's message).
- the cost-data rows of the new and changed tests, measured on delphi-3bda.

Base-line check of the cleanup commits (a base line is a line that exists in `jhan-amx-p0`):

- The cleanup commits change no C++ or Haskell base line.
- This was checked with a guard script that runs `git blame` on every changed file. The script reports any changed line that already existed in `jhan-amx-p0`.
- The CI commit appends a line-continuation backslash to one base line each in `cmake-single-platform.yml` and `README.ci.md`.
- The branch as a whole edits 105 base lines. All of them are in the first nine commits.

## 3. Measurements (qwen3-4b, 8 users, our half of delphi-3bda, CPU attention with AMX)

- Binaries: the prompt 1024 numbers come from commit `10fc7c724c`, the last commit before the cleanup (2 repetitions) [`exec/results/vnnik2-confirm-20260915`]. The prompt 2048 and 8192 numbers come from commit `9928cb2849` with both measurement switches on, which is the same store as `10fc7c724c` before its work units were aligned to page blocks (2 to 3 repetitions of binary ab) [`exec/results/vnnik2-20260915`]. Both folders are in the intel-AMX workspace.
- The cleanup removed the two measurement switches, which were both on, renamed constants and rewrote comments. So the behaviour of the head is the behaviour of `10fc7c724c`. Section 5 confirms this on the head itself.
- The full campaign report is `status/store-remedies-report.html`.

| prompt | binary | tp2 TTFT | tp4 TTFT | tp2 TPS/user | tp4 TPS/user |
|---|---|---|---|---|---|
| 1024 | base (PR #3879) | 3.150 s | 2.194 s | 79.7 | 103.6 |
| 1024 | this branch | 3.095 s (-56 ms) | 2.117 s (-77 ms) | 83.9 (+5.3%) | 103.9 (+0.2%) |
| 2048 | this branch vs base | -112 ms (base 7.254 s, -1.5%) | -120 ms (base 4.719 s, -2.5%) | +7.1% | -0.7% |
| 8192 | this branch vs base | -1.37 s (base 53.369 s, -2.6%) | -0.52 s (base 30.487 s, -1.7%) | +10.1% | +8.0% |

The tp4 decode numbers have a run-to-run spread of 1 to 3 TPS. That is 1 to 3% of 104 TPS. It is larger than the +0.2% and -0.7% deltas. So those two deltas are noise.

- Decode gain: the AMX kernel reads K without a transpose. The gain grows with the prompt length.
- TTFT gain: the shared block save. Save K per prefill layer went from 274 us (base) to 60 to 80 us (this branch), measured with in-process Perfetto traces.
- The per-token scatter store of the first version cost 859 us per layer and +171 ms TTFT at tp4. That version is not in this PR.

## 4. Numerics

- The AMX kernel that reads the VNNI plane is bit-identical to the row-major AMX kernel (`t_amx_numerics`, real AMX on delphi-3bda).
- The block save is bit-identical to the per-token scatter (`t_k_vnni_layout`, 152 mask cases: 38 present-masks x 4 token blocks). A present-mask is a bit mask that says which of the 16 tokens of a block are present. The model-level store test checks every row of a pass of 48 jobs (one job = one token of the pass) against its source, alone and with two helper threads (`t_llama_unit`).
- The AVX-512 reader of the layout adds the same exact bf16 products in fp32 as the row-major dotter. Only the add order differs (the numerics contract of Note [AMX attention dispatch]). On a VNNI binary the kill switch runs the AVX-512 VNNI reader, not the row-major dotter.
- Greedy runs (1 user, prompt 1024, 128 tokens) produced identical tokens across every store variant (each setting of the two measurement switches `TRON_K_VNNI_BLOCK` and `TRON_K_VNNI_STRIPE`) and the A/A repeat.

## 5. Verification of this head

Done on delphi-3bda. Setup: `nix develop` (the project's pinned build shell), clang 19, `TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON`, worktree `/var/tmp/jhan/tron-vnnik4`, binary `runtron.vnnik4`. Results:

- clang-format-19 (the code formatter) reports no change on every changed C++ file.
- Full build of runtron and the four unit tests (641 s on 72 cores): finished with no errors.
- `t_k_vnni_layout` 5 cases / 63426 assertions, `t_amx_numerics` 5 / 4621 (real AMX), `t_amx_dispatch_dtype` 1 / 1559, `t_llama_unit` 30 / 122438: all pass, the same counts as before the cleanup.
- Haskell code-generator test suite (`cabal test` of the `tron-ingest` package in `ingest/`): pass.

Cells (one cell = one measured configuration of prompt length, tp and binary) on the head (prompt 1024, 8 users, 2 repetitions, CPU attention with AMX, `exec/results/vnnik4-20260915`):

| tp | binary | TTFT | TPS/user |
|---|---|---|---|
| tp2 | base | 3.141 s | 79.8 |
| tp2 | this head | 3.083 s (-59 ms, -1.9%) | 84.2 (+5.5%) |
| tp4 | base | 2.193 s | 105.6 |
| tp4 | this head | 2.120 s (-73 ms, -3.3%) | 106.8 (+1.2%) |

These reproduce the section 3 numbers of the measured binary (-56 ms and -77 ms). The greedy smoke test (1 user, 128 generated tokens) of this head produced the same 128 tokens as the measured binary `runtron.vnnik3` (the binary of commit `10fc7c724c`). Its A/A repeat matched too.

The whole host test suite (the tests that run on the CPU host without an FPGA) ran with `TRON_K_VNNI=ON` on our half of the machine. Commands: `make build-test-host`, then `make test-host` (= `bin/slice run --filter=host --exclude-tag=slow`). Result: all 302 test targets compile. 90 tests ran under the host filter without slow tests: 89 passed, 1 skipped, 0 failed. Total wall-clock time 107 s. `t_k_vnni_layout` passed under slice with 63426 assertions.

The one skipped host test is `t_proxy_lib`. Its Python venv (virtual environment) is absent on the machine. The test is unrelated to this branch.

Other generated models and FPGA attention were run at tp2 on our half with prompt 1024. A smoke run is 1 user, greedy, 128 tokens. A cell is 8 users, 256 tokens, one run each. Results are in `exec/results/vnnik4-models-20260915`.

| run | attention | smoke tokens, base vs this head | cell TTFT base / head | cell TPS/user base / head |
|---|---|---|---|---|
| qwen3-4b, FPGA attention (`USE_HW_ATTN` unset, the default of the nightly CI run) | FPGA | identical, 128 of 128 | 3.155 / 3.162 s | 125.4 / 123.7 (-1.4%) |
| gpt-oss-120b (64-dimension heads: layout off, `save_k_helper` returns at once) | CPU | identical, 128 of 128 | 4.311 / 4.304 s | 63.7 / 62.6 (-1.7%) |
| llama-3.1-8b (128-dimension heads, kv_mul 4 = four query heads per KV head, 32 layers) | CPU with AMX | first difference at token 46 | 4.309 / 4.279 s (-30 ms) | 78.6 / 83.1 (+5.7%) |
| qwen-3-30b-a3b (128-dimension heads, kv_mul 8: layout on, AMX kernel not eligible) | CPU, software path | first difference at token 5 | 5.204 / 4.835 s (-369 ms) | 36.3 / 34.3 (-5.4%) |

Reading:

- FPGA-attention run: the tokens are identical to base. So the K rows reach the FPGA correctly through `get_k_row`.
- gpt-oss-120b: untouched by the layout, as designed.
- llama-3.1-8b: behaves like qwen3-4b (decode gain, small TTFT gain).
- Token divergence of llama-3.1-8b and of the mixture-of-experts model qwen-3-30b-a3b (MoE: each token runs only a subset of the layer's expert sub-networks): both come from the software reader of the layout. That reader adds the fp32 products in a different order than the row-major dotter. Both outputs are fluent continuations of the same text. This attribution is the numerics contract of Note [AMX attention dispatch], not a measurement of the scores themselves.
- qwen-3-30b-a3b decode (-5.4% TPS, one run): see section 6.
- Log gap: in the gpt-oss-120b cell of this head one of the eight completion lines is missing from the log. The other seven agree. The base run had one early stop at 110 tokens.

Cost data: `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics` ran on the idle machine after the runs above. The resulting rows are in the last commit.

## 6. Open items

- **128-dimension heads with kv_mul other than 4 (measure before merging).** For qwen-3-30b-a3b (kv_mul 8) the VNNI layout is on. The AMX kernel is not eligible for that shape. So every page goes through the AVX-512 reader of the layout instead of the row-major dotter. The decode store also scatters into cold lines (64-byte cache lines not yet present in the CPU cache). One run showed -5.4% decode TPS (a loss: 34.3 vs 36.3 TPS/user) and -7% TTFT (a gain of 369 ms; lower TTFT is better) against base. If more repetitions confirm the decode loss, the layout gate `k_vnni::layout_on<head_size>` should also require the AMX shape (kv_mul 4), or the reader needs work for larger groups (more query heads per KV head). Not measured further here.
- **Cost data.** The row of `t_k_vnni_layout` and refreshed rows of `t_llama_unit` and `t_amx_numerics` are in the head (granite_rapids_6962p block). The genoa96 block gets its rows from the weekly refresh.
- **Benchmark artifact (reviewer decision).** The CMake build job bundles its `gen/runtron` as the benchmark artifact. With this PR that binary stores K in the VNNI layout. So the CI benchmark job measures the VNNI layout when it uses the artifact. When it rebuilds locally, it measures the row-major layout. PR #3879 already did the same with `TRON_AMX_DISPATCH=ON`. If that mix is unwanted, the option needs its own configuration instead of the build job.
- **Decode store (not blocking).** In decode, Save K takes 28 to 35 us per layer for the 8 tokens of a decode pass (the 1024-token prefill pass takes 60 to 80 us). Decode writes one token per user per step. Every line it writes is therefore cold. Today the store overlaps with work that the attention workers already have ready. So it adds no wall-clock time. Candidates: stripe decode tokens over the helpers, or prefetch the token's lines early in the layer. Unmeasured.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
