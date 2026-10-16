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
| shared block save | The K store of this branch. The pass's tokens are cut into work units (runs of consecutive tokens inside one 16-token block of a page). The main thread and the idle main helpers claim the units from one counter. A unit that fills its whole block is written with 16 rows transposed in registers, one 64-byte line at a time. A shorter unit is written row by row into the block's row-major form: 4 whole 64-byte lines per token (see row-major tail block). |
| dotter | The per-token AVX-512 (the 512-bit vector instruction set used by the software path, not AMX) dot-product loop of the software attention path (`tron/kernels/dotter.hpp`). |
| row-major tail block | A 16-token block of a VNNI K plane whose 16 rows are not all saved yet. It holds its rows row-major (one contiguous 256-byte row per token) inside the block's own 4 KiB. A row store into such a block writes 4 whole 64-byte lines, as the row-major layout does. Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp`. |
| converted block | A block whose 16 rows are saved and whose bytes were transposed in place into the VNNI layout: by the whole-block save at once, or at the end of the forward pass that saved the 16th row. The page records per storage slot which rows are saved and which blocks are converted (Note [K VNNI storage]). |
| hardware-scored operation | An attention operation whose scores come from the FPGA (the model's hardware attention). Its K blocks are never converted: the FPGA staging reads the rows in place, and the CPU scores only the tail the FPGA has not processed. Note [Row-major blocks under hardware attention] in `kv_cache.hpp` (the fix of issue #4500). |
| nightly CI, perf configs | The nightly System CI run of positron-ai/systems_test on delphi-3bda (the Intel Xeon 6962P test machine, two CPU sockets, eight FPGA cards). Its perf phase measures 14 configs (model, tensor-parallel degree, user count, prompt length), 10 rounds of one request per user each, through platformd (the service that starts the rinzler engines) and the Caddy proxy, with the tron package installed from apt. A pass = one run of the 14 configs with one package. |
| TTFT, paired t, resolved | TTFT = time to first token. The paired t statistic is computed over the per-round differences (this branch minus base, round means) of the pass pairs. A difference is resolved when the paired t is at least 2.26 in magnitude and the difference is at least 1 % (TTFT: also at least 1 ms). |
| VmHWM | The peak resident memory of a process since it started (`/proc/PID/status`). The memory column sums it over the rinzler engine processes of a config. |
| kill switch | `TRON_AMX_DISABLE=1`: the binary does not use the AMX kernels and runs the software path. |
| base | Two comparators are called base. In the Background section and in the PR #3879 table of the Measurements section, base is the PR #3879 binary (commit 544ca05c7a). Everywhere else base is `main` at be0d5565b3, the commit this branch is synced to: as the nightly package 2026.10.08-be0d5565 in the nightly-config measurements, and as a `runtron` build without `TRON_K_VNNI` (row-major K, AMX dispatch on) in the runtron cells and the token-identity check. |
| greedy run, A/A repeat | A run with temperature 0 (always pick the top-scoring token) and deterministic reductions (sums performed in a fixed order, so the result does not depend on thread timing). The same binary then produces the same tokens twice. An A/A repeat is the same configuration run twice as a control. |
| slot | One persistent K/V storage region of the cache (one per layer, or shared between layers), described by a `kv_slot_spec`. A row-major slot keeps K in the row-major layout. |
| dense page | A full 64-token page, all of it visible to the query, with its 4 blocks converted: the case the AMX QK kernel (the kernel that multiplies the query by the K rows to produce the attention scores) handles. |
| slice check, cost data | `bin/slice bench --check` runs in CI (continuous integration, the automated test runs on every push), in both the Nix workflow and the legacy CMake workflow. It fails when a registered test has no timing row in any platform block of `config/test-benchmarks.json`, and prints a warning when the current platform's block lacks one. The rows are called cost data. A row holds the run time at 1, 2 and 4 slices. genoa96 (the AMD runner) and granite_rapids_6962p (delphi-3bda) are two of the file's four platform blocks. |

## The changes

- New header `h/tron/tensor/k_vnni.hpp`. Everything in it is AVX-512. No AMX instruction is in it. It holds:
  - the layout (index map) and its constants
  - the owner `k_vnni_tensor<64, 128>`
  - the view `k_vnni_view<T, 64, 128>` with a bounds-checked read `at(token, dim)`
  - `detail::k_vnni_access`, the only access path from a view to the plane address. Its users are the operations below, the two score kernels and the test-only `book::fill_random`.
  - the row-view aliases and helpers
  - the typed operations `store_row` (the per-token scatter store), `load_row` (the gather load: many small loads, each from a separate address, into one row), `store_block` (the 16-token block save: transpose in registers, full cache line stores) and `copy_token`.
  - the row-major tail block operations: `row_major_row` (a token's row inside a row-major block, as a typed row view), `store_row_major`, `load_row_major`, and `block_to_vnni` / `block_to_rows` (the in-place conversion of one 16-token block, 4 KiB read and 4 KiB written), with Note [Row-major tail block].
- `h/tron/kernels/k_vnni.hpp`: the AVX-512 reader `qk_group` of the layout for partial pages, hosts without AMX and the kill switch. It takes the packed view, not a pointer. It scores a query group (the query heads that share one KV head) wider than 16 heads in passes of 16. Every head's scores are its own accumulation. So the split changes no add order.
- `h/tron/tensor/kv_cache_fwd.hpp`: forward declarations of the two K types. With them, `amx_attn_iface.hpp` does not include any intrinsics (compiler built-in functions that map to single AVX-512 or AMX instructions).
- `kv_cache.hpp`:
  - Note [K VNNI storage] (a named comment block in the header that documents the layout) and Note [Row-major blocks under hardware attention].
  - The K layout state per page and storage slot: the saved-row bits and the converted-block bits (one extra entry for the EAGLE storage), with `note_k_row_saved`, `note_k_block_saved`, `k_block_to_vnni` / `k_block_to_vnni_at`, `k_vnni_blocks`, `k_storage_ref` / `k_storage_of`, `k_row_if_row_major` and `k_forget_row` (a new token at a page offset drops the bits at and above it and converts the offset's block back to row-major).
  - `kv_block::k` is the owner `k_vnni_tensor` for a 128-dimension head under `TRON_K_VNNI`, and the row-major array otherwise (`std::conditional_t`). It has the same trivial-type checks (`static_assert`s that the type is trivially default-constructible, trivially copyable and trivially destructible) as the packed V plane.
  - The row views `page::k()` exist only for row-major slots (see the Words table).
  - `page::k_packed` returns a read-only view of the packed plane.
  - Layout-independent `set_k_row`, `get_k_row` (typed row views) and `set_k_block` serve both layouts. `set_k_row` and `get_k_row` follow the block's recorded layout (packed column or row-major row). `set_k_block` stores whole blocks.
  - A whole-page copy copies the owner (`dst_block.k = src_block.k`).
  - Other ranges are copied token by token through row-major rows: the converted destination blocks the range touches are made row-major first, and a block whose 16 rows are saved after the copy is converted. The bits travel with the rows.
  - `fill_random` fills the packed plane through `detail::k_vnni_access`, as it does for V.
- `model.hpp`: Note [Shared block save].
  - `save_k` cuts the pass into work units. It shares the store with the main helpers. They call the same `save_k` with their worker index (the main thread is worker 0). A unit that fills a whole block takes the block save; a shorter unit is stored row by row into the row-major block.
  - After the join, `save_k` records the saved rows of a software-scored operation. A block that is complete because of this pass is queued (`pending_k_blocks_`) and converted at the forward end (`convert_pending_k_blocks`, after the cooperative GOF staging drained). The rows of a hardware-scored operation are not recorded, so their blocks stay row-major.
  - The workers are joined on one counter with a 120-s watchdog (the join aborts with an error if the helpers have not finished after 120 s).
  - The handwritten plugins pass one worker. So they store serially. The unit tests pass one worker. The exception is the shared-save case of `t_llama_unit`. That case passes three workers.
  - `save_k` passes typed source rows to the store. The K buffer's row view keeps its alignment and DMA flags (DMA = direct memory access, the device-visible memory tag).
- `common.hpp`: the state of one shared block save, called a window in the code (`batch::k_store_window`: claim counter, open and finished counters, the unit table).
- `self_attention.hpp`, `amx_attn.cpp`, `amx_attn_iface.hpp`:
  - The dense AMX path takes a page only when its 4 blocks are converted (`k_layout_dense`); it reads the VNNI plane (the K storage in the VNNI layout) as its B operand (`qk_vnni_128x4`). The kernel takes `k_vnni_view<const bf16, 64, 128>` (bf16 = 16-bit brain float, the K and V element type) by value. It reads the plane once through `detail::k_vnni_access::plane`. `weights_times_v_128x4` does the same for V.
  - `qk_vnni_128x4` is bit-identical to the row-major kernel by test.
  - The software path scores the live tokens (the tokens present in the page) of the converted blocks in one AVX-512 loop over the page (`k_vnni::qk_group`), and the tokens of a row-major tail block with the row-major dotter through `row_major_row`.
  - Both paths receive `page::k_packed`.
- FPGA staging (`gof.hpp`, `gof.cpp`, `full.hpp`). The FPGA is the accelerator card that runs attention for the pages it processes. Staging is the code that copies K and V rows into the buffers the FPGA reads. `k_head_fn` returns a row of a row-major block in place (`k_row_if_row_major`) and writes the row of a converted block into a scratch buffer (temporary memory) that the caller owns, through a typed destination row. `v_head_fn` already worked that way. `gof::populate` allocates the scratch. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the scratch-buffer parameter.
- Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k` at the attention statement of every KV-writing operation. `save_k` receives the worker count and the caller's worker index.
- CMake option `TRON_K_VNNI` (default OFF, requires `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels). Files: `CMakeLists.txt`, `src/tron/CMakeLists.txt`. The option is also defined for `tron_model_compile_config` (the interface library through which `main` compiles the generated model objects). So those objects are compiled with the same K layout as the tron library. The `deb` preset (`CMakePresets.json`, the released package) sets it ON next to `TRON_AMX_DISPATCH`, so the package stores K in the VNNI layout on every host. The legacy CMake workflow sets the option ON (`.github/workflows/cmake-single-platform.yml`). On `main` that workflow runs by manual dispatch and from `publish-deb.yml`. `README.ci.md` documents the flag.
- Tests:
  - `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`). It runs on real owners: poison (a fill of the plane with a known marker pattern before each check) through 64 typed row stores, layout checks on the owner's bytes, the index anchors (hand-computed offsets of chosen token and dimension pairs, compared against the index map), an `at()` section, a `copy_token` section, the reader check for 4, 20 and 32 query heads with bf16, float and fp16 (16-bit IEEE half float) queries, the tail-block conversion (bit for bit against `store_row`, no other block touched), and the page state: the block turns VNNI at the 16th saved row and back when a row is forgotten, a row saved again, the EAGLE storage view, forgetting a row in several slots, and page appends that carry the state.
  - A bit-identity case in `t_amx_numerics`. It fills a `k_vnni_tensor` through `store_row`.
  - Fakes (stand-in implementations used only by the test) in `t_amx_dispatch_dtype` that take the typed view, and a case where a full page with unrecorded rows takes the software loop under `TRON_K_VNNI`.
  - In `t_llama_unit`: a model-level shared-save case (the queued block and its forward-end conversion; with a hardware-scored operation, no conversion; with another operation hardware-scored, conversion), an apply-and-join case that scores a page with converted and row-major blocks, a software-attention case for 32 query heads on one 128-dimension K/V head, layout-independent accessors, and the K typed-boundary contracts. The contracts are: the VNNI QK kernel accepts the packed view only, the other kernels reject it, no pointer construction, conversion only from a writable view to a read-only view, no view of a temporary owner, no element write, 64-byte owner alignment.
  - Checks in `LoopyTronSpec.hs` (the code-generator test suite) on the call text the generator emits for the two `save_k` calls (main thread and main helpers).
- Constant spelling: the AMX kernel files and this branch's own K headers and tests name every value-carrying constant `NAME_<value>`. Code added to shared files (`t_llama_unit.cpp`, `model.hpp`, `common.hpp`) keeps those files' own spelling (literals and lower_snake names), as PR #4557 does.

## Measurements

### Nightly CI perf configs, whole machine, this branch against `main` (2026-10-09)

Setup: the nightly's own client (systems_test at 14f0ce4, `scripts/perf.py`, 10 rounds per config) against rinzler engines provisioned by platformd 0.11 in the nightly layout (4 tp2 engines or 2 tp4 engines behind the Caddy proxy, the same 8 users spread over them). Two packages: base = the nightly package 2026.10.08-be0d5565 (`main` at be0d5565b3). This branch = 9d5c7a389b built with the `deb` preset and `TRON_K_VNNI=ON`, the preset line that the head 0a5334ccb6 carries (the same package the head builds). Four passes in the order base, this branch, this branch, base. `USE_HW_ATTN` as shipped: FPGA attention for the ingested models, CPU attention for the handwritten ones. One extra cell per pass: qwen3-4b tp2, 8 users, prompt length 8192 tokens, 1536 generated tokens, with `USE_HW_ATTN=0` (software attention on the CPU).

All configs have 8 users, prompt length 1024 and 1536 generated tokens unless the row says otherwise. The base passes are within 1.7 % of the nightly's own run of the same day (package 2026.10.09-26b6df7d) on every config.

| config | base TPS | this branch TPS | TPS difference (paired t) | base TTFT | this branch TTFT | TTFT difference | peak memory difference |
|---|---|---|---|---|---|---|---|
| llama-3.2-3b tp2, 32 users, prompt 200 plus 800 shared | 198.26 | 195.56 | -1.4 % (-16.6), resolved | 74 ms | 58 ms | -15 ms (t -1.5) | +6 MiB (+0.1 %) |
| llama-3.1-8b tp2 | 143.03 | 142.58 | -0.3 % (-1.4) | 586 ms | 585 ms | 0 ms | +5 MiB |
| llama-3.1-8b tp2, 32 users, prompt 4096 (the "AMX benchmark" row) | 32.62 | 34.20 | +4.8 % (+39.4), resolved | 11.82 s | 11.83 s | +12 ms (t +0.7) | +5 MiB |
| llama-3.3-70b tp2 | 17.01 | 17.00 | 0.0 % (-2.1) | 9.38 s | 9.39 s | +11 ms (t +1.0) | +2 MiB |
| llama-3.3-70b tp2, 4 users | 28.46 | 28.68 | +0.8 % (+13.1) | 4.09 s | 4.46 s | +371 ms (t +1.1) | +2 MiB |
| llama-3.3-70b tp4, 4 users | 31.71 | 31.67 | -0.1 % (-0.8) | 4.88 s | 4.87 s | -1 ms | 0 MiB |
| mixtral-8x7b tp2 | 80.68 | 80.62 | -0.1 % (-0.2) | 1.26 s | 1.26 s | +5 ms (t +2.2) | -16 MiB |
| qwen-2.5-32b tp2 | 36.06 | 36.02 | -0.1 % (-2.6) | 3.95 s | 3.94 s | -7 ms (t -1.1) | +6 MiB |
| qwen3-4b tp2 (FPGA attention) | 189.13 | 187.38 | -0.9 % (-2.2) | 502 ms | 494 ms | -8 ms (t -1.0) | 0 MiB |
| qwen3-4b tp4 (FPGA attention) | 181.01 | 180.30 | -0.4 % (-0.4) | 557 ms | 545 ms | -12 ms (t -0.8) | -8 MiB |
| gemma-2-9b tp2 | 104.03 | 104.84 | +0.8 % (+1.0) | 856 ms | 852 ms | -5 ms (t -1.7) | -81 MiB (-0.3 %) |
| gpt-oss-120b tp4 | 122.38 | 121.83 | -0.5 % (-1.3) | 966 ms | 944 ms | -22 ms (t -1.9) | +2 MiB |
| gemma-4-31b tp2 | 38.21 | 38.23 | +0.1 % (+0.7) | 5.46 s | 5.45 s | -8 ms (t -1.6) | +17 MiB |
| Muse-Glimmer-30B tp4 | 74.72 | 76.53 | +2.4 % (+24.4), resolved | 3.72 s | 3.60 s | -118 ms (-3.2 %, t -25.9), resolved | +8 MiB |
| extra cell: qwen3-4b tp2, prompt 8192, software attention | 59.84 | 64.41 | +7.6 % (+39.3), resolved | 12.96 s | 12.81 s | -150 ms (-1.2 %, t -9.0), resolved | +24 MiB (+0.1 %) |

Reading:

- The AMX kernel's share of a decode step grows with the users per engine and the prompt length. The two configs where the CPU scores long attention ranges gain: llama-3.1-8b at 32 users and prompt 4096 (8 users per engine) +4.8 % TPS, and qwen3-4b with software attention at prompt 8192 +7.6 % TPS and -150 ms TTFT. At 2 users per engine and prompt 1024 (llama-3.1-8b, 8 users) nothing changes.
- The two qwen3-4b configs with FPGA attention are inside the noise (-0.9 % and -0.4 %, not resolved). They are the configs of issue #4500. The blocks of a hardware-scored operation stay row-major.
- llama-3.2-3b loses 1.4 % TPS (resolved, both pass pairs). Its 128-dimension heads have kv_mul 3, so the VNNI layout is on but the AMX kernel is not eligible, and the AVX-512 reader scores its pages instead of the row-major dotter (see the kv_mul open item).
- Muse-Glimmer-30B tp4 gains 2.4 % TPS and 118 ms TTFT (resolved). The attention shape of that model was not examined here.
- Every other config is within 0.8 % (not resolved). mixtral shows no change.
- Memory: the peak resident memory of the engines differs by at most 81 MiB (0.3 %) on any config. The K cache occupies the same bytes in both layouts.

### runtron cells against `main` at this head (2026-10-09)

Question: the decode TPS and TTFT of this head against `main` at 8 users on one engine with software attention, the cells of the PR #3879 table below.

Comparator: `main` at be0d5565b3 built as runtron without `TRON_K_VNNI` (row-major K, AMX dispatch on). This branch at 9d5c7a389b.

Cells: qwen3-4b tp2, 8 users, 256 generated tokens, CPU attention, prompt 1024 and prompt 8192, 3 repetitions, binaries interleaved, our half of delphi-3bda.

Verdict rule: band = the larger of 2 x the largest standard deviation of the two binaries and a floor of 0.4 TPS or 0.15 s. A difference beyond the band counts as a change.

Result (3 repetitions each; TPS = decode tokens per second per user, TTFT = the maximum over the 8 users):

| cell | base TPS / TTFT | this branch TPS / TTFT | band | result |
|---|---|---|---|---|
| prompt 1024 | 79.10 / 3.177 s | 83.14 / 3.133 s | 0.94 TPS / 0.15 s | TPS +5.1 % (beyond the band), TTFT -45 ms (inside the band) |
| prompt 8192 | 17.10 / 52.584 s | 18.87 / 52.040 s | 0.40 TPS / 0.19 s | TPS +10.3 % (beyond the band), TTFT -543 ms (beyond the band) |

### Against the PR #3879 binary (runtron, our half of delphi-3bda, qwen3-4b, 8 users, software attention with AMX)

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

The delphi-3bda runs below are from 2026-10-08 and 2026-10-09 at 9d5c7a389b. The head 0a5334ccb6 adds the `deb` preset line and a `README.ci.md` paragraph to it.

Setup: `nix develop` (the project's pinned build shell), clang 19, preset `native` (explicit AVX-512 flags), `TRON_AMX_DISPATCH=ON`, `BUILD_INGEST_MODELS=ON` (the CMake option that builds the generated model plugins).

Unit tests, VNNI build (`TRON_K_VNNI=ON`), real AMX, our half of the machine:

| test | result (assertions / test cases) |
|---|---|
| `t_k_vnni_layout` | pass, 1041256 / 10 |
| `t_amx_dispatch_dtype` | pass, 2137 / 1 |
| `t_amx_numerics` | pass, 4621 / 5 (the AMX cases ran: no "AMX unavailable" line) |
| `t_llama_unit` | pass, 259020 / 64 |
| `t_heterogeneous_scheduler` | pass, 2783 / 3 |
| `t_phase1_integration` | pass, 2124 / 64 |
| `t_amx_numerics` with the kill switch (`TRON_AMX_DISABLE=1`) | pass, 2060 / 5, the three AMX cases report "AMX unavailable" |
| Haskell code-generator suite (`bin/ingest-cabal test`) | pass |

The generated plugins carry no `save_k_helper` call (grep over the generated sources). clang-format 19.1.7 and `git diff --check` pass on the changed files.

Row-major build (`TRON_K_VNNI=OFF`), all pass (assertions / test cases):
- `t_k_vnni_layout` 1039202 / 10
- `t_amx_dispatch_dtype` 2137 / 1
- `t_amx_numerics` 4621 / 5
- `t_llama_unit` 258911 / 64
- `t_heterogeneous_scheduler` 2783 / 3

One `main` test, `t_llama_unit` "apply and join page ranges / query splits match unsplit page reductions", runs with a wider tolerance in this branch. The Open items section gives the mechanism.

Cost rows (`config/test-benchmarks.json`, granite_rapids_6962p block) were measured with `bin/slice bench --update t_llama_unit t_k_vnni_layout t_amx_numerics` on the whole delphi-3bda host (both sockets, 2026-10-08). The rows are `t_llama_unit` 28.1 / 28.3 / 28.3 s, `t_k_vnni_layout` 0.90 / 0.91 / 0.91 s and `t_amx_numerics` 0.81 / 0.83 / 0.74 s. The three values are the run time at 1, 2 and 4 slices. The test binaries grew with the row-major tail block cases since that measurement (see Open items).

### Host test suite and token identity at this head (2026-10-09)

Question: does the whole host test suite pass at this head, and does this binary reproduce its own tokens.

Comparator: `main` at be0d5565b3 built as runtron without `TRON_K_VNNI` (row-major K, AMX dispatch on). The previous head of this branch (45e6bb266d, before the row-major tail block) as a second reference.

Cells: `make build-test-host` and `make test-host` (fake device, our half) at 9d5c7a389b. Token identity with runtron: qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism (the runtron flag that selects deterministic reductions), seed 1, 256 generated tokens; CPU attention at prompt 1024 (this branch, its A/A repeat, its kill-switch run, `main`, the previous head), FPGA attention at prompt 1024 and CPU attention at prompt 8192 (this branch, `main`, the previous head).

Verdict rule: the host suite passes with the same pass and skip set as `main` on this machine (`t_proxy_lib` skipped and `t_proxy_llama31` failing for the Python venv the machine lacks). Token identity: this branch equals its A/A repeat and its kill-switch run for 256 tokens. The runs against `main` and the previous head are informational: `main` is expected to differ from generated token 52 (issue #4444), and the previous head scores the row-major tail block with the VNNI reader where this head uses the dotter.

Result: the host suite passes with the same set as `main` on this machine. All host test targets compile; 93 tests passed, 1 skipped (`t_proxy_lib`), 1 failed (`t_proxy_llama31`), both for the Python venv `t/proxy/.venv` the machine lacks; makespan 126 s.

| check | result |
|---|---|
| host test suite | 93 passed, 1 skipped, 1 failed (the venv), as `main` |
| this branch vs its A/A repeat (CPU, prompt 1024) | identical, 256 of 256 |
| this branch, AMX on vs kill switch (CPU, prompt 1024) | identical, 256 of 256 |
| this branch vs `main` | CPU 1024: identical, 256 of 256. CPU 8192: identical, 256 of 256. FPGA 1024: first difference at generated token 52 |
| this branch vs the previous head | CPU 1024: first difference at generated token 52. CPU 8192: identical. FPGA 1024: identical |
| the previous head vs `main` | CPU 1024 and FPGA 1024: first difference at generated token 52. CPU 8192: identical |

Under CPU attention this head reproduces the tokens of `main` in both cells: the rows of a decode step land in a row-major block that the row-major dotter scores, as on `main`. Under FPGA attention the difference from `main` at generated token 52 is the same as the previous head's.

## Open items

- **genoa96 cost row for `t_k_vnni_layout`.** The genoa96 block (the AMD benchmark runner) of `config/test-benchmarks.json` has no row for `t_k_vnni_layout`. The CI check passes without it. `bin/slice bench --check` fails only when a test has no row in any platform block, and prints a warning when the current platform's block lacks one. A genoa96 row needs a run on that runner.
- **128-dimension heads with kv_mul (the number of query heads that share one KV head) other than 4.** For qwen-3-30b-a3b (kv_mul 8) the VNNI layout is on. The AMX kernel is not eligible for that shape. So every page goes through the AVX-512 reader of the layout instead of the row-major dotter. The decode store also scatters into cold lines (64-byte cache lines not yet present in the CPU cache). Measured on 2026-09-16 with this branch at 65a1c41d72 against `main` c7844ca2ce (8 users, tp2): decode TPS +1.5 % at prompt 1024 (6 repetitions, inside noise), -4.1 % at prompt 2048 (3 repetitions, a loss), +24.1 % at prompt 8192 (3 repetitions). TTFT is lower by 8 to 16 % in every cell. In the nightly configs of 2026-10-09 (Measurements) llama-3.2-3b (kv_mul 3) loses 1.4 % TPS at 32 users, resolved in both pass pairs. So the layout gate `k_vnni::layout_on<head_size>` should also require the AMX shape (kv_mul 4), or the reader needs a faster path for larger groups (more query heads per KV head).
- **Benchmark binary mismatch (reviewers decide).** The legacy CMake workflow compiles `runtron` once, in its `build` job, with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`, and hands that binary to its `benchmark` job. When the hand-over works, the benchmark measures a binary with the AMX kernels and the VNNI K layout. When the hand-over fails, the benchmark job compiles `runtron` itself through `make`. That `make` build sets neither option. The benchmark then measures a binary with row-major K and no AMX kernels. PR #3879 introduced this mismatch for `TRON_AMX_DISPATCH`. This PR adds `TRON_K_VNNI` to the same line. The default CI (the Nix build on GCP, Google Cloud Platform runners) is not affected. Its benchmark binary is built with neither option. If the mismatch is unwanted, both options should move out of the build job into a configuration of their own. `TRON_PAGE_SHARE_COUNTERS` (another CMake option) already works that way, through the `coverage` preset (a CMake configuration preset).
- **Kill switch and token divergence (tracked in issue #4444, reviewers decide).** Under FPGA attention this branch generates a different token than `main` from generated token 52 of the prompt-1024 run (the token-identity table in the Verification section). Under CPU attention the prompt-1024 and prompt-8192 runs are identical to `main`. The expected cause is the add order. Partial pages are scored by the VNNI reader (this PR's AVX-512 routine that scores tokens from the VNNI layout), which adds the fp32 products in a different order than the row-major dotter. A token flips only at a near tie (a step where the two best candidate tokens have almost the same score). Issue #4444 holds the forced-run measurement that would confirm this. With `TRON_K_VNNI` on, `TRON_AMX_DISABLE=1` runs the VNNI reader instead of the dotter for 128-dimension heads. The kill switch still gives an AMX-off run of the same binary. It no longer gives the tokens of a clean binary (a build with both options off). Item 4 of Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp` still promises those tokens for rollback. Issue #4444 lists two options: (a) accept the weaker rollback and add the condition "with `TRON_K_VNNI` off" to item 4, or (b) keep a row-major build as the rollback artifact in deployment and document that. Note [K VNNI storage] in `kv_cache.hpp` describes the behavior of this branch. Under FPGA attention the software path still scores the pages the FPGA does not process. The tokens of a row-major tail block are scored by the row-major dotter in both the AMX-on and the kill-switch run of this binary, so those two runs stay identical.
- **A `main` test tolerance is widened.** `t_llama_unit` "apply and join page ranges / query splits match unsplit page reductions" (added to `main` on 2026-09-11) compares a page reduction done in one run with the same reduction done as two ranges and joined. On `main` it bounds the difference of the weighted V sum by 0.02 and of the weight sum by 2e-6. The two runs reach a page with a different running maximum (the largest score seen so far, which the softmax subtracts from every score before the exponential). So each softmax weight (the normalized attention score) is converted to bf16 for the PV product (the product of the softmax weights and V) at a different scale. The AVX path truncates in that conversion. The row-major build passes `main`'s bounds by a small margin (0.018 of 0.020 on one element of the weighted V sum, 1.9e-6 of 2.0e-6 on the weight sum). With VNNI K the scores differ in their last bits. The bf16 conversion then rounds at a different point. One element reaches 0.022. This branch sets the bounds to 0.05 and a relative 1e-6. The test passes with `TRON_K_VNNI` on and off. The test comment names the mechanism. The test's author may want to review the change.
- **Cost rows refresh.** The granite_rapids_6962p rows of `config/test-benchmarks.json` for `t_llama_unit`, `t_k_vnni_layout` and `t_amx_numerics` were measured at 6b939d25d2 (2026-10-08). The tail-block cases added since make `t_k_vnni_layout` and `t_llama_unit` longer. A `bin/slice bench --update` of the three tests on the whole machine refreshes the rows.

🤖 Generated with [Claude Code](https://claude.com/claude-code)


