## Short version

This pull request stores the saved key vectors of 128-dimension attention heads in the AMX VNNI layout, behind a typed owner and typed views. In this pull request the layout is read by an AVX-512 routine on the CPU and by the FPGA staging gather, and no AMX instruction is added. The CMake option that selects the layout is off in every build preset, and three later pull requests are planned to add the AMX kernel that reads the layout, a faster block save and a row-major tail block (both described under The stack).

### Background

AMX tile multiplication accepts a row-major matrix only as its left operand. Its right operand must use the VNNI layout.

`main` stores K as one 128-value row per token. Its AMX QK kernel therefore puts the K page on the left. The page has 64 tokens × 128 dimensions. Packed queries go on the right. The resulting score matrix S is transposed. [PR #3879]

```text
S^T = K * Q^T
  K is the left operand. Packed Q^T is the right operand.
S = transpose(S^T)
  AVX-512 writes the 4 query columns as score rows.
```

The new memory layout stores K^T in the format required by the right operand. It uses the same number of bytes as row-major K. The next PR's AMX kernel is intended to compute `S = Q * K^T` directly, without the register transpose.

This PR provides:

- The new storage layout and typed access. No raw plane pointer leaves the cache interface.
- The AVX-512 reader used by CPU attention.
- The gather used for FPGA staging.

No AMX instruction is added. Other head sizes retain row-major K. For example, gpt-oss-120b has 64-dimension heads.

## Words used here

| Term | Meaning |
|---|---|
| PR, main, stack | PR means pull request. `main` is the target branch. The stack is the sequence of four dependent PRs replacing PR #4424. This is the first PR. |
| tron, runtron | tron (the inference program under test), runtron (its command-line tool). |
| token, generated token, layer | A token is a unit of text processed by the model. A generated token is one output token. A layer is one stage of the model's computation. |
| attention, head, Q, K, V | Attention combines saved token information using scores. A head is one attention computation channel. Q holds query vectors, K holds key vectors, and V holds value vectors. The KV cache stores K and V for past tokens. |
| CPU, FPGA | CPU means central processing unit. FPGA means field-programmable gate array. Here it is the accelerator card that runs attention for the pages assigned to it. |
| AMX, AVX-512, VNNI | AMX (Advanced Matrix Extensions) and AVX-512 (Advanced Vector Extensions, 512-bit vectors) are CPU instruction sets. AMX supports tile matrix multiplication. A tile is a 2-dimensional AMX register of 16 rows by 64 bytes. VNNI means Vector Neural Network Instructions. The VNNI layout is an operand format read by VNNI instructions and AMX tile multiplication. |
| AMX kernels | The attention routines introduced by PR #3879. A kernel is a routine specialized for one computation. |
| VNNI layout | Two consecutive dimensions of one token are adjacent in memory. One 64-byte line holds that dimension pair for 16 consecutive tokens. This is the B-operand format, meaning the right-hand matrix format, of AMX tile multiplication. |
| row-major K | The existing layout: one contiguous row of values per token. For the heads changed here, each row holds 128 values. |
| CMake, preset, option | CMake configures the build. A preset is a named build configuration. The option means `TRON_K_VNNI`, which defaults to OFF. When enabled, it selects VNNI K storage for every 128-dimension head. No preset enables it. |
| AMX dispatch | `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels and the code that selects them. This PR does not require it. |
| kill switch, AMX-on, AMX-off | The kill switch is `TRON_AMX_DISABLE=1`. It prevents use of the AMX kernels. AMX-on allows those kernels when their other conditions hold. AMX-off disables them through this switch. |
| KV page, block, plane | A KV page is a 64-token block allocated by the cache. Within this PR, a block means 16 consecutive tokens of a page, or one AMX tile width. A plane is K or V storage for one page and one KV head. A K plane occupies 16 KiB, or 16 × 1,024 bytes: 64 tokens × 128 dimensions × 2 bytes per value. |
| KV head, kv_mul | A KV head is one key/value head. `kv_mul` means query heads per KV head. It is 4 heads for the qwen3-4b and llama-3.1-8b models, 3 heads for llama-3.2-3b, and 8 heads for qwen-3-30b-a3b. gpt-oss-120b is another model mentioned below. |
| slot, geometry | A slot is one persistent K/V storage region, usually one per layer or shared between layers. Geometry means the head counts and dimensions. A VNNI slot uses packed K storage. A row-major slot stores K as contiguous rows. |
| prefill, decode, pass | A pass is one forward computation of the model over its current input. Prefill processes prompt tokens, usually many tokens per pass. Decode generates one output token per user per pass. |
| owner, view | `k_vnni_tensor` owns one 16 KiB K plane as a 64-byte-aligned array. `k_vnni_view` refers to that plane. It computes element addresses. Views come only from an owner. They have no public pointer constructor, `data()` accessor, or `operator[]`. `at(token, dim)` reads one element. It cannot write an element. |
| row view | A typed view of one token's K values in dimension order. `const_k_row_view` is the source type. `k_row_view` is the destination type. `k_source_row` wraps a pointer or an existing slice view. `k_destination_row` wraps a destination pointer. A transfer row is one token's 128 K values in a contiguous buffer, used to move a row into or out of the cache. |
| packed, packed V | Packed means stored in the VNNI layout. Packed K, VNNI K and the new layout mean the same thing in this PR. A packed view, slot or page is one whose K uses that layout. `main` already stores V in a VNNI layout (packed V). Its helpers (`v_vnni_access`) are the pattern the new K helpers follow. |
| dense page, live mask, book | A dense page is a full 64-token page that the query sees whole. The AMX page kernel of `main` can process it in one call. A live mask is a 64-bit mask with one bit per token of a page: a set bit means that token's K is written and is scored. A book is the cache object that owns a group of pages. |
| reader, dotter | The reader is `k_vnni::qk_group`, the routine that scores a query group against one packed K page. It puts one token in each vector lane, or element position. The dotter is `main`'s software loop that computes one dot product per token from row-major K. Their headers are `h/tron/kernels/k_vnni.hpp` and `h/tron/kernels/dotter.hpp`. |
| save_k, staging | `save_k` copies a pass's K rows into the cache, once per layer per pass. Staging copies K and V into buffers read by the FPGA. `gof::populate` performs that staging. |
| bf16, fp16, fp32, float | bf16 is the 16-bit brain floating-point format used for K. fp16 is the 16-bit IEEE half format. fp32, called `float` here, is the 32-bit IEEE single format. IEEE is the standards organization specifying the fp16 and fp32 formats named here. |
| QK, PV, softmax | QK is the query-key score product. Softmax converts scores into attention weights using exponentials and normalization. PV multiplies those weights by V. |
| VDPBF16PS, FMA, NaN | VDPBF16PS multiplies bf16 pairs and accumulates their products in fp32. FMA means fused multiply-add. NaN means not a number, an invalid floating-point result. |
| scatter, gather, dword | A scatter writes vector elements to separate addresses. A gather reads them from separate addresses. A dword is a 32-bit, or 4-byte, unit. |
| DMA, HBM | DMA means direct memory access. A view's DMA flag identifies device-visible memory. HBM means High Bandwidth Memory, the FPGA's device memory. |
| tp2, slice | `tp2`, also written `-tp2` in a model name, splits the model across 2 devices. A slice is one FPGA with its share of the host's CPU cores and memory. |
| TPS, TTFT | TPS is decode throughput in tokens per second per user. TTFT is time to first token. The measurement tables report the maximum TTFT over all 8 users. |
| base, new, baseoff, newoff | `base` is `main` at commit `72308ec90c` (this PR's merge base), built as runtron with row-major K and AMX dispatch on. `new` is this branch at commit `82d05e94be`, built with both options on. `baseoff` and `newoff` run those respective binaries with the kill switch. |
| greedy run, A/A repeat, forced run | A greedy run uses temperature 0, a setting that chooses the highest-scoring token. `--pay-for-determinism` performs sums in a fixed order. An A/A repeat runs the same configuration twice as a control. A forced run means teacher forcing via `--force-feed-text-token-file`: both binaries consume the same prescribed token sequence. |
| cell, band, standard deviation, paired t | A cell is one model, prompt length, and attention configuration. Standard deviation measures variation between repetitions. The band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. The paired t statistic expresses the mean paired difference relative to its uncertainty. It is dimensionless. |
| CI, required CI, legacy CMake lane | CI means continuous integration, the automated build and test system. Required CI is the workflow `gcp-nix.yml`, plus `deb-smoke.yml`, an APT package check that builds no tron binary. The C++ test build of `gcp-nix.yml` uses `nix/cmake-tron-test-build.nix`. The legacy CMake lane is `.github/workflows/cmake-single-platform.yml`. It runs by manual dispatch and from `publish-deb.yml`, the package-publishing workflow. |
| slice check, cost data | `bin/slice bench --check` checks registered tests for timing records in `config/test-benchmarks.json`. It runs in CI. These records are cost data: test durations at 1, 2, and 4 slices. A test with no record in any platform block fails the check. A missing record for the current platform produces a warning. |
| test platforms | `granite_rapids_6962p` identifies delphi-3bda, the Intel Xeon 6962P test machine. `genoa96` identifies the AMD runner. These are two of the timing file's four platform blocks. Intel and AMD are processor vendors. Granite Rapids is the name of that Intel CPU family. The Granite Rapids machine below means delphi-3bda. |
| worktree, translation unit | A worktree is a separate checkout used for one build. A translation unit is one source file after its included headers have been expanded. |

## The changes

The new storage header defines typed access to the packed K plane. Its vector operations use AVX-512. It contains no AMX instruction. [h/tron/tensor/k_vnni.hpp]

- `namespace k_vnni` holds the index map and layout constants.
- `k_vnni::layout_on<head_size>` selects 128-dimension heads when the option is on. This layout gate (the compile-time condition that selects the layout) depends only on storage geometry. Every reader and writer of a slot therefore selects the same layout. Query type and AMX availability do not affect it.
- `k_vnni_tensor<64, 128>` owns the plane.
- `k_vnni_view<T, 64, 128>` provides the bounds-checked `at(token, dim)` read.
- `detail::k_vnni_access` provides the only route from a view to the plane address. Its callers are the typed operations, the score reader, and `book::fill_random`, the test-only whole-book initializer.
- Row-view aliases and helpers describe contiguous transfer rows.
- `store_row` scatters one token's row. It uses 4 scatters of 16 dwords, one per 32-dimension step. Together they write 4 bytes into each of the token's 64 memory lines (64-byte CPU cache lines, not KV cache pages).
- `load_row` gathers a row using 4 gathers of 16 dwords.
- `copy_token` copies one token between packed positions.
- `store_row` and `load_row` assert that the token index is below the plane's 64 tokens. The packed-V operations make the same check in `v_vnni_access::pair_base`. `copy_token` inherits both checks.

The new reader accepts a packed view. One masked 64-byte load supplies one dimension pair for 16 tokens. [h/tron/kernels/k_vnni.hpp]

- For bf16 queries, VDPBF16PS multiplies pairs and accumulates in fp32. The row-major dotter uses the same instruction.
- For float queries, K is widened exactly to fp32. FMA computes the products and sums, as in `dotter<float, 128>`.
- For fp16 queries, the query is widened once to fp32.
- A clear bit in the 64-bit live mask prevents that token's K from being read. Unwritten tokens therefore cannot change the result.
- Groups wider than 16 query heads run in passes of 16 heads. Each head has its own accumulator. Splitting the group therefore preserves each head's add order.
- Until the next AMX kernel PR is merged, this reader serves every page of a VNNI slot.

The forward-declaration header names the two packed K types. [h/tron/tensor/kv_cache_fwd.hpp] The next PR's kernel declarations in the AMX interface header are intended to name their views through it, without including intrinsics (the compiler functions for individual vector or tile instructions). At this head that header names no packed K type. Its only change here is two lines of the dispatch diagram.

The cache gains these operations and constraints. [h/tron/models/kv_cache.hpp]

- Note [K VNNI storage] is the named comment explaining the layout, its writers and readers, and the kill switch.
- `kv_block::k`, the block's K member, is a `k_vnni_tensor` for a 128-dimension head when the option is on. Otherwise it is a row-major array. `std::conditional_t` selects the type at compile time.
- Compile-time assertions require trivial default construction, copying, and destruction. Packed V has the same checks. The cache's DMA allocation creates these blocks without calling constructors.
- The row accessors `page::k()`, `kv_block::k_view`, and `k_at` exist only for row-major slots. C++ `requires` clauses enforce that restriction. A packed token's values are not contiguous.
- `page::k_packed` returns the reader's read-only packed view.
- `set_k_row` and `get_k_row` accept typed transfer rows for either layout. They use `store_row` and `load_row` for packed storage. They use `memcpy`, the byte-copy operation, for row-major storage. The caller supplies the row's alignment and DMA flags.
- A full-page copy assigns the owner: `dst_block.k = src_block.k`. Other ranges use `copy_token`. A token's packed column depends on its page offset.
- `fill_random` accesses packed K through `detail::k_vnni_access`. It already uses the corresponding access helper for V.

`save_k` writes each token through `page::set_k_row`. A bf16 source row is read in place with its existing alignment and DMA flags. Other activation types (the number format of the model's intermediate values: fp16 or fp32) are converted to bf16 in a stack buffer first. That buffer is named through `k_destination_row`, the helper for a contiguous K transfer row. The row-major path performs that conversion in place. [h/tron/models/model.hpp]

Each packed row store uses 4 scatters. Together, the scatters write 4 bytes into each of 64 memory lines. The row-major store writes 4 whole 64-byte lines. The packed store therefore touches 64 lines per token where the row-major store touches 4. That extra line traffic is a prefill cost. The third PR is intended to remove it with block saves.

Software attention selects its scoring path at compile time. [h/tron/models/self_attention.hpp]

- For packed K, the loop records relevant tokens in a 64-bit live mask. The reader then scores them through `page::k_packed`, in passes of up to 16 heads.
- Row-major K retains the per-token dotters.
- `if constexpr` selects the path from the layout gate. A row-major geometry compiles no packed reader. A packed geometry compiles no dotter.
- The dense AMX path uses the predicate `eligible<...>(...) && !k_vnni::layout_on<operation_head_size>`. It is compiled only for row-major slots. This predicate is the temporary gate referred to under Measurements and Open items. Every packed page therefore uses the software loop on every host until the next kernel PR is merged.

The visit-path comment and dispatch diagram describe those same choices. `attn_stats::visit_path` records the path that served a page. [h/tron/models/attn_stats.hpp, Note [AMX attention dispatch] in h/tron/kernels/amx_attn_iface.hpp]

FPGA staging gains a K scratch buffer. [h/tron/gof.hpp, src/tron/gof.cpp, h/tron/scheduler/full.hpp]

- `page_info::k_head_fn`, the callback returning one token's K row, receives caller-owned scratch aligned to 64 bytes. The existing V callback, `v_head_fn`, has the same argument.
- The scheduler callback gathers packed K through `page::get_k_row`. For row-major K, it returns the existing row pointer.
- `gof::populate` allocates K scratch beside V scratch.
- Staging bytes and the HBM layout are unchanged.
- The K callbacks gain the scratch parameter in three tests: `t_gof_dma` (staging transfers), `t_gof_staging_leaks` (staging allocation and lifetime), and `t_phase1_integration` (staging and dispatch integration).
- The populate case of `t_phase1_integration` stages K rows through the scratch. Its K callbacks gather each head's row out of a packed K plane into the scratch row supplied by `populate`. The scheduler's callback does the same for a VNNI slot. After `populate`, every staged value is compared per token, head and element through the K swizzle (the element transposition the FPGA expects). `populate` collects every head's pointer before it copies the rows. A wrong per-head scratch stride (the byte distance between consecutive heads' scratch rows) would therefore stage one head's data for every head. That deliberate change fails the case. [Verification below]

The new CMake option defaults to OFF. [CMakeLists.txt, src/tron/CMakeLists.txt]

- Its definition is PUBLIC on the tron library target and INTERFACE on `tron_model_compile_config`, the interface library used to compile generated model objects. Every translation unit touching a KV page therefore receives the same definition.
- Storage, the reader, and staging have no AMX dependency. The option-on build also passes the listed unit tests with AMX dispatch off. [Verification below]
- The legacy CMake lane explicitly enables this option beside `TRON_AMX_DISPATCH=ON`.
- The build combinations are documented. [README.ci.md]
- No preset enables the option.

Tests change as follows:

- `t_k_vnni_layout` is a new test binary with 4 cases. It is registered with the `fake` label, meaning it uses a simulated device. [t/CMakeLists.txt]
  - The index map matches hand-computed addresses for selected (token, dimension) pairs.
  - Store/load checks fill a plane with a marker using 64 row stores. They then store 64 rows in scrambled order. They check physical positions, `at()` reads, and exact load results. Rewriting one token must preserve other tokens. `copy_token` must move one token correctly between planes.
  - Reader checks compare against the dotter for 4, 20, and 32 query heads with bf16, float, and fp16 queries. Inputs include 65 prefix masks (masks in which only the first N tokens are live), 24 masks with gaps, and 2 single-token masks. Dead-token storage contains NaN poison, meaning invalid values used to check that dead-token data does not reach live scores. Dead-token scores must retain their preset values. The test does not detect a stray read of dead-token K: an unmasked load would place the NaNs in vector lanes that the masked store discards.
  - The cache case checks row access and `book::append`, the operation that appends one book's tokens to another. It covers token copies into a partly filled page and a full-page copy. This case uses packed cache storage with the option on and row-major cache storage with it off.
- `t_llama_unit`, the model and cache unit-test binary, adds these checks:
  - Existing AMX kernels reject packed K views. A raw pointer cannot construct a packed view. Writable views convert only to read-only views. A temporary owner cannot produce a view. Elements cannot be written through `at()`. The owner is aligned to 64 bytes. `page::k_packed` exists exactly when the option selects packed storage.
  - The `save_k` case stores 46 tokens across 3 pages. Token runs (contiguous sequences of saved tokens) begin within a block and cross block and page boundaries. Jobs (one token's work item in a pass) without KV work appear inside and after a run. Assertions check stored rows bit for bit, untouched rows, and the K completion marks (the per-token counters that record a saved K row).
  - A compile check covers 32 query heads sharing one 128-dimension KV head. The reader handles this shape in 2 passes.
  - Existing cases write K through the layout-independent accessors instead of row views.
  - The split-versus-unsplit tolerance in “apply and join page ranges” is widened for the VNNI layout only. The row-major build keeps `main`'s bounds. [Open items below]
- `t_amx_dispatch_dtype`, the test of dispatch for different activation types, changes its full-page expectation under the option. The 128-dimension model prepares Q, but it makes no dense AMX kernel call. That path is not compiled for packed K.
- The timing file gains a Granite Rapids row for `t_k_vnni_layout`. It refreshes the rows for `t_llama_unit` and `t_amx_numerics`, the AMX numerical-accuracy test. [config/test-benchmarks.json]

## Measurements

The measurements compare decode TPS and TTFT with the option on against `main`. They also compare the reader against the dotter and measure the kill switch within this PR.

Configurations:

- `base`: `main` at `72308ec90c`, built as runtron with row-major K and AMX dispatch on.
- `new`: this branch at `82d05e94be`, with both options on.
- `baseoff` and `newoff`: those same binaries with the kill switch.

The experiment ran on 2026-10-10:

- Model: qwen3-4b, tp2.
- Load: 8 users and 256 generated tokens.
- Attention: CPU, selected by `USE_HW_ATTN=0`.
- Prompt lengths: 1,024 tokens and 8,192 tokens.
- Repetitions: 3, with the binaries run in alternating order.
- Allocation: the experiment's half of the Granite Rapids test machine.

The decision band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. A difference beyond that band counts as a change. Paired t uses the 3 repetitions.

Each parenthesized value is the sample standard deviation over the 3 repetitions. TPS has units of tokens/s/user. Both TTFT and its standard deviation have units of seconds.

| Prompt length (tokens) | Binary | TPS (tokens/s/user) | TTFT (s) |
|---|---|---|---|
| 1024 | base | 80.61 (0.16) | 3.185 (0.010) |
| 1024 | new | 75.45 (0.11) | 4.005 (0.002) |
| 1024 | newoff | 75.07 (0.14) | 3.941 (0.000) |
| 1024 | baseoff | 72.62 (0.19) | 3.981 (0.007) |
| 8192 | base | 17.26 (0.01) | 53.510 (1.634) |
| 8192 | new | 15.26 (0.03) | 117.516 (0.160) |
| 8192 | newoff | 15.30 (0.05) | 117.090 (0.301) |
| 8192 | baseoff | 14.64 (0.03) | 122.938 (0.126) |

“Inside” and “beyond” refer to the decision band. The paired t values are dimensionless.

| Prompt length (tokens) | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
| 1024 | new vs base | -6.4 % (-5.16 TPS, t -36.5), beyond | +820 ms (+25.8 %, t +158.8), beyond | 0.40 TPS / 0.15 s |
| 1024 | newoff vs baseoff | +3.4 % (+2.45 TPS, t +36.3), beyond | -41 ms (-1.0 %, t -10.5), inside | 0.40 TPS / 0.15 s |
| 1024 | newoff vs new | -0.5 % (-0.37 TPS, t -5.4), inside | -65 ms (-1.6 %, t -65.2), inside | 0.40 TPS / 0.15 s |
| 1024 | baseoff vs base | -9.9 % (-7.99 TPS, t -150.2), beyond | +796 ms (+25.0 %, t +209.4), beyond | 0.40 TPS / 0.15 s |
| 8192 | new vs base | -11.6 % (-2.00 TPS, t -174.6), beyond | +64.0 s (+119.6 %, t +69.6), beyond | 0.40 TPS / 3.27 s |
| 8192 | newoff vs baseoff | +4.5 % (+0.66 TPS, t +13.4), beyond | -5.8 s (-4.8 %, t -23.9), beyond | 0.40 TPS / 0.60 s |
| 8192 | newoff vs new | +0.3 % (+0.04 TPS, t +0.9), inside | -425 ms (-0.4 %, t -1.8), inside | 0.40 TPS / 0.60 s |
| 8192 | baseoff vs base | -15.2 % (-2.63 TPS, t -199.0), beyond | +69.4 s (+129.7 %, t +69.3), beyond | 0.40 TPS / 3.27 s |

### This PR alone on an AMX host with the option on

- `new` loses decode throughput against `base`: -6.4 % at prompt length 1,024 tokens and -11.6 % at 8,192 tokens.
- TTFT increases by approximately 26 % and 120 %, respectively. These are rounded forms of the measured table values.
- The temporary gate excludes the dense AMX kernel for packed slots. Those pages use the reader instead.
- `main` itself shows the same pattern of losses when its AMX kernels are switched off: `baseoff` against `base` is -9.9 % and -15.2 % TPS and approximately +25 % and +130 % TTFT. So at prompt length 8,192 tokens those kernels do most of the prefill attention work.
- The next PR is planned to remove the temporary gate by adding an AMX kernel for this layout. The option remains off in every preset.

The four binaries decompose the loss:

- `baseoff` minus `base` is the throughput contributed by `main`'s AMX kernels.
- `newoff` minus `baseoff` is the effect of the layout, the reader and the row store, with AMX off on both binaries.
- Their sum, from the unrounded run means, is -5.54 TPS at prompt length 1,024 tokens and -1.96 TPS at 8,192 tokens.
- The measured `new` minus `base` is -5.16 TPS and -2.00 TPS.
- The residuals, +0.37 TPS and -0.04 TPS, equal `new` minus `newoff`. That difference is inside the band at both prompt lengths.
- So the loss is the disabled AMX kernels, partly offset by the reader. The comparison does not separate the reader's gain from the row store's cost. [Open items below]

### The reader against the dotter (kill switch on both binaries)

Both `newoff` and `baseoff` disable AMX. Their remaining differences are:

- Packed versus row-major K storage.
- The reader versus the per-token dotter. The reader uses one token per vector lane and no per-token gather.
- Scatter stores versus contiguous row stores.

Results for prompt lengths 1,024 and 8,192 tokens, respectively:

- Decode TPS increases by 3.4 % and 4.5 %. Both changes exceed the band.
- TTFT changes by -1.0 % and -4.8 %. The first is inside the band. The second is beyond it.

An AMD host was not measured. Such a host has no AMX support. The reader therefore serves every packed page there. [Open items below]

### The kill switch inside this PR (newoff vs new)

TPS changes are inside the band at 1,024 tokens (-0.5 %) and inside it at 8,192 tokens (+0.3 %). The switch changes no scoring path for 128-dimension heads in this PR. Packed slots cannot use the dense AMX kernel.

TTFT is lower with the switch, inside the band in both cells:

- Prompt length 1,024 tokens: 65 ms, or 1.6 %. The band is 0.15 s.
- Prompt length 8,192 tokens: 425 ms, or 0.4 %. The band is 0.60 s. Paired t is -1.8.

One known difference between the two runs is work whose output nothing uses:

- The AMX query pack (the step that rearranges query vectors into the AMX operand format) runs once per token for a packed slot.
- No kernel consumes it in this PR.
- The kill switch skips it.

A profile is needed to tell whether that work is measurable. [Open items below] The next PR is intended to consume the packed query data.

## Verification

Build provenance:

- Machine and date: Granite Rapids, Intel Xeon 6962P with AMX, 2026-10-10.
- Revision: `82d05e94be`, including `main` at `72308ec90c`.
- Environment: `nix develop`, the project's pinned build shell.
- Compiler: clang version 19.1.7.
- Preset: `native`, which supplies explicit AVX-512 flags.
- Build type: `RelWithDebInfo`, an optimized build with debug symbols.
- Each of the 3 configurations used a separate worktree.

`BUILD_INGEST_MODELS` controls compilation of generated models.

| Configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | Targets | Build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | 597 s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | 284 s |
| option off | OFF | ON | OFF | the 5 layout-independent tests | 292 s |

`t_heterogeneous_scheduler` tests scheduling across different attention geometries.

The following unit-test binaries passed with a fake device. `--skip-benchmarks` excluded their benchmark sections. Each result gives assertions / test cases.

| Test | Option on | Option on, no AMX dispatch | Option off |
|---|---|---|---|
| `t_k_vnni_layout` | 1011432 / 4 | 1011432 / 4 | 1011432 / 4 |
| `t_amx_dispatch_dtype` | 1612 / 1 | 1 / 1 (placeholder without dispatch) | 1612 / 1 |
| `t_amx_numerics` | 4109 / 4 (AMX cases ran, no “AMX unavailable” line) | 1 / 1 (placeholder) | 4109 / 4 |
| `t_llama_unit` | 266453 / 66 | 266453 / 66 | 266522 / 66 |
| `t_heterogeneous_scheduler` | 2783 / 3 | 2783 / 3 | 2783 / 3 |
| `t_phase1_integration` | 6220 / 64 | 6220 / 64 | not built |

Kill-switch results in the option-on build:

- `t_llama_unit`: 266453 assertions passed in 66 cases. This matches the AMX-on count.
- `t_amx_numerics`: 2060 assertions passed in 4 cases. Its QK and PV precision cases reported “AMX unavailable”.

The option-off build has 69 more `t_llama_unit` assertions. The “page K views preserve geometry and row addressing” case checks individual elements of the 128-dimension slot in the row-major build. In the packed build it instead checks that the row view is absent. The row-major build passes the split-versus-unsplit case under `main`'s bounds, and the packed builds pass it under the VNNI bounds. [Open items below]

A mutation check (a deliberate code change that the test must catch) of the staging test, in the option-on worktree: with `+ h * HW_BAKED_HEAD_SIZE` (the FPGA's fixed head size, the per-head offset) removed from the scratch address in `gof::populate`, `t_phase1_integration` fails its populate case. The run reports 1 of 1 test cases failed and 1 of 3 assertions failed, at the `REQUIRE` of `t/t_phase1_integration.cpp:920`. With the file restored, the binary passes again with 6220 assertions in 64 cases.

All of these checks are clean at `82d05e94be`:

- clang-format version 19.1.7, the source formatter, with `--dry-run --Werror` on all 17 changed C++ files.
- `git diff --check`, the whitespace check, against `main`.
- A search for the prohibited `<cassert>` header in the diff.

Syntax-only compilation used clang version 19 with the product's compile flags. It covered 38 configurations with 0 errors and 0 warnings:

- All 4 combinations of AMX dispatch on/off and the option on/off for 9 translation units: `t_llama_unit`, `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `heterogeneous_scheduler_compile` (heterogeneous scheduling compilation), `scheduler/full.cpp` (the full scheduler), `gof.cpp` (staging), `t_gof_dma` (staging DMA), and `t_kv_oom_subcases` (out-of-memory cases).
- `kernels/amx_attn.cpp` (the AMX kernels) with dispatch on and the option on/off.

The compiler flag is `-fsyntax-only`.

### Host test suite and token identity (2026-10-10)

The checks ask two questions. Does the host suite (the unit tests run by `make test-host` with a fake device) meet the exception rules listed under Acceptance rules below? Are the generated tokens identical across the selected configurations? `base` is the comparator defined in Measurements.

Host-suite setup:

- `make build-test-host` compiled the host tests.
- `make test-host` ran them with a fake device in the option-on worktree.
- The experiment used its half of the machine with production serving stopped.

Token-identity setup:

- runtron with qwen3-4b, tp2, and 1 user.
- Temperature setting 0, `--pay-for-determinism`, random seed identifier 1, and 256 generated tokens.
- CPU attention at prompt lengths 1,024 and 8,192 tokens.
- FPGA attention at prompt length 1,024 tokens.
- Binaries: `new`, `new2` (the A/A repeat), `newoff`, and `base`.

Acceptance rules:

- The host suite permits only the existing Python-environment exceptions. `t_proxy_lib`, a proxy-library test, may skip. `t_proxy_llama31`, a Llama proxy test, may fail. Both lack the virtual environment `t/proxy/.venv`, the isolated Python dependency directory.
- `new2` must match `new` for all 256 generated tokens in each cell.
- `newoff` must match `new` for those same tokens.
- The comparison with `base` is informational. [Issue #4444]

Host-suite result:

- All test targets compiled.
- 93 tests passed.
- 1 test skipped: `t_proxy_lib`. Its per-test log reports “SKIP: t/proxy/.venv missing”.
- 1 test failed: `t_proxy_llama31`, reporting “ERROR: t/proxy/.venv missing”.
- Total suite time: 112 s.
- The CMake cache retained `TRON_K_VNNI=ON` throughout the make targets.

| Cell | new vs new2 | newoff vs new | new vs base |
|---|---|---|---|
| CPU attention, prompt length 1024 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | first difference at generated token 83 |
| CPU attention, prompt length 8192 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens |
| FPGA attention, prompt length 1024 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | first difference at generated token 83 |

### CI coverage

Required CI builds with both CMake options off. Neither `TRON_AMX_DISPATCH` nor `TRON_K_VNNI` is enabled in its test build. [nix/cmake-tron-test-build.nix]

- The first 3 cases of `t_k_vnni_layout` exercise the packed owner, storage operations, and reader. They run independently of the layout option.
- Only that binary's fourth case, the cache integration case, selects row-major cache storage when the option is off.
- The option-dependent packed-cache branches of `t_llama_unit` do not execute in required CI.
- With AMX dispatch off, `t_amx_dispatch_dtype` runs a `SUCCEED` placeholder. That placeholder is a passing test case without dispatch-path coverage.

The option-dependent paths run in the manually dispatched legacy CMake lane and in the Granite Rapids verification reported above. The author explicitly accepts the current required-CI limitation for this PR. Issue #4865 tracks enabling both options in the required test build. It also tracks an AMX runner for the next PR's kernel-identity case (the test that compares the new AMX kernel's output bit for bit with the row-major kernel's).

## Open items

**Performance of this PR alone on AMX hosts with the option on.**

- Every page of a 128-dimension head uses the reader. That includes dense pages served by `main`'s AMX kernel.
- Against `main` at `72308ec90c`, decode TPS falls 6.4 % at prompt length 1,024 tokens and 11.6 % at 8,192 tokens. TTFT increases by approximately 26 % and 120 %. The test used qwen3-4b, tp2, 8 users, and CPU attention. [Measurements above]
- The option is off in every preset. Existing preset builds therefore keep their current layout.
- The next PR is intended to remove the temporary gate and, with it, this performance loss. A measurement at that PR's head must establish the result.

**Measurements not made at this head.**

- AMD host: the question is whether the reader gains decode TPS where no AMX exists. The measurement: `newoff` against `baseoff` on the genoa96 runner at the same two cells.
- Reader gain against row-store cost: the question is how much of the `newoff` against `baseoff` gain is the reader and how much the scatter store costs. The measurement: a per-function profile of `newoff` at prompt length 8,192 tokens, splitting `save_k` time from `k_vnni::qk_group` time.
- Unconsumed query pack: the question is whether the AMX query pack that no kernel consumes costs measurable time. The measurement: the same profile on `new`, with the pack's share of a decode step.

**128-dimension heads with kv_mul other than 4 query heads.**

The next AMX kernel is planned to support only 4 query heads per KV head. Other groups retain the packed layout and use the reader wherever `main` uses the dotter. This applies both in this PR and after the stack. Not measured at `82d05e94be`. The measurement that settles it: decode TPS of llama-3.2-3b (kv_mul 3) and qwen-3-30b-a3b (kv_mul 8) at this head against `main` at `72308ec90c`, 3 repetitions, the band rule of the Measurements section.

Earlier measurements on the PR #4424 branch, whose reader and decode store are this PR's, give the expected direction:

| Model and load | Prompt length | Decode TPS change | Repetitions and interpretation | Revisions and date |
|---|---|---|---|---|
| llama-3.2-3b, tp2, kv_mul 3 query heads, 32 users | 200 tokens per user plus an 800-token prompt prefix shared by all users | -1.4 % | Resolved in two independent pairs of benchmark passes with the nightly benchmark settings | `9d5c7a389b` vs `main` `be0d5565b3`, 2026-10-09 |
| qwen-3-30b-a3b, kv_mul 8 query heads, 8 users, tp2 | 1024 tokens | +1.5 % | 6 repetitions, within reported measurement variation | `65a1c41d72` vs `main` `c7844ca2ce`, 2026-09-16 |
| same | 2048 tokens | -4.1 % | 3 repetitions | same revisions and date |
| same | 8192 tokens | +24.1 % | 3 repetitions | same revisions and date |

“Resolved” is the earlier report's classification: a difference is resolved when the paired t statistic is at least 2.26 in magnitude (the two-sided 95 % threshold of the t distribution for that report's 10 rounds) and the difference is at least 1 %.

The proposed alternatives are to restrict `k_vnni::layout_on<head_size>` to the AMX group shape or to improve the reader for larger groups. Restricting the layout gate would require it to account for the group size.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]**

- At prompt length 1,024 tokens, both CPU and FPGA attention first differ from `main` at generated token 83 of 256.
- At prompt length 8,192 tokens with CPU attention, all 256 generated tokens match. [Verification above]
- Hypothesis: the different fp32 add order changes a near tie between the two highest-scoring token candidates. A forced-run measurement is needed to confirm or reject this explanation. That measurement is tracked in issue #4444.
- With the option on, the kill switch preserves the packed layout and reader. It changes no score or scoring path for 128-dimension heads in this PR. Those slots cannot use AMX here.
- After the next PR, the switch is expected to provide an AMX-off run of the same binary. It is not expected to reproduce the tokens of a clean binary, meaning a build with both options off.
- The rollback contract (the documented promise of what the kill switch restores) promises clean-binary tokens. [Item 4 of Note [AMX attention dispatch], h/tron/kernels/amx_attn_iface.hpp]

Issue #4444 records two choices:

1. Accept the narrower rollback contract. Add “with `TRON_K_VNNI` off” to item 4.
2. Keep a row-major binary as the deployment rollback artifact. Document that requirement.

**A main test tolerance is widened.**

The `t_llama_unit` case “apply and join page ranges / query splits match unsplit page reductions” was added to `main` on 2026-09-11. It compares one page reduction (the attention sum over all tokens of one page) with two separately computed ranges joined afterward.

- `main` permits an absolute difference of 0.02 in a weighted-V output element. It permits an absolute difference of 2e-6 in the weight sum. Both are dimensionless numerical quantities in this test.
- The two computations can reach a page with different running maxima. The running maximum is the largest score seen so far. Softmax subtracts it before exponentiation.
- The weights are therefore converted to bf16 at different scales for the PV product. The AVX path truncates during that conversion.
- The row-major result approaches `main`'s limits: 0.018 against 0.020 for one weighted-V element, and 1.9e-6 against 2.0e-6 for the weight sum.
- Packed K changes the last bits of the scores. The bf16 conversion then rounds at a different point. One weighted-V element reaches an absolute difference of 0.022.
- With the option on, this PR uses 0.05 absolute difference for weighted V and 1e-6 relative difference for the weight sum. A relative difference of 1e-6 is one part per million.
- With the option off, the bounds are `main`'s. The selection is a compile-time check of the layout gate.
- The test passes in both builds. Its comment explains the mechanism. [Verification above]

Open question for the test's author: is 0.05 (2.3 times the observed 0.022) the right bound for weighted V under VNNI K, or should it be the observed maximum plus a margin, such as 0.03?

**Missing genoa96 timing for t_k_vnni_layout.**

The genoa96 platform block has no timing row for `t_k_vnni_layout`. Another platform has a row. The slice check therefore passes. A missing current-platform row produces a warning. A genoa96 run is needed to add its timing. [config/test-benchmarks.json]

**Benchmark binary mismatch, inherited from PR #3879. Reviewers decide.**

- The legacy CMake workflow's `build` job compiles runtron with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`. It transfers that binary to its `benchmark` job.
- A successful transfer benchmarks AMX kernels and packed K.
- After a failed transfer, the benchmark job builds runtron through `make`. That build sets neither option. It benchmarks row-major K without AMX kernels.
- PR #3879 introduced the mismatch for AMX dispatch. This PR adds the layout option to the same configure line.
- Required CI is unaffected. Its benchmark binary has neither option enabled.

One remedy is a separate configuration containing both options. `TRON_PAGE_SHARE_COUNTERS`, the page-sharing instrumentation option, already uses that arrangement through the `coverage` preset.

## The stack

PR #4424 uses branch `jhan-amx-vnniK` and adds 4,054 lines. Four dependent PRs replace it. Each is based on the preceding PR. PR #4424 remains open as a reference until all four are open.

| Order | PR branch and base | What it adds | State |
|---|---|---|---|
| 1 | this PR, `jhan-vnnik-1-layout`, based on `main` | Packed K layout, owner and views, per-row store, reader, FPGA staging gather, the option disabled in presets, and tests | ready for review |
| 2 | `jhan-vnnik-2-amx`, based on this PR | The AMX QK kernel `qk_vnni_128x4` and query packer `pack_q_rows_128x4`. A bit-identity test compares with the row-major kernel. The temporary gate and comments are removed. | to follow as a draft |
| 3 | `jhan-vnnik-3-shared-save`, based on PR 2 | Shared saves of 16-token blocks, transposed in registers and written as whole cache lines by the main thread and idle helper threads (worker threads with no work of their own at that moment). This provides PR #4424's TTFT improvement. | to follow as a draft |
| 4 | `jhan-vnnik-4-tail-block`, based on PR 3 | A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the packed layout when all 16 rows are saved. A row-major policy under hardware attention addresses issue #4500. The `deb` package-build preset enables the option in the released package. | to follow as a draft |

The option stays off in every preset until PR 4. Intermediate states therefore do not enter production through those presets.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
