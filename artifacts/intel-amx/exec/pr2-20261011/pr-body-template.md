## Short version

This pull request adds the AMX QK kernel that reads the packed K plane of the layout PR (PR #4868) as the right operand of the tile multiply and computes `S = Q * K^T` directly, without the register transpose of the row-major kernel. The temporary gate of the layout PR is gone, so a dense page of a packed slot takes the AMX page path again, while partial pages, the kill switch, hosts without AMX and 128-dimension heads with kv_mul other than 4 keep the AVX-512 reader. The CMake option that selects the layout stays off in every preset, and against `main` the measured decode TPS changes by {{SHORT_TPS_1024}} at prompt length 1,024 tokens and by {{SHORT_TPS_8192}} at 8,192 tokens.

### Background

AMX tile multiplication accepts a row-major matrix only as its left operand. Its right operand must use the VNNI layout.

`main` stores K as one 128-value row per token. Its AMX QK kernel, added by PR #3879, therefore puts the K page (64 tokens x 128 dimensions) on the left. Packed queries go on the right. The resulting score matrix S is transposed. An AVX-512 register transpose then writes the 4 query columns as score rows. [PR #3879]

With the option on, the layout PR stores the K rows of every 128-dimension head in the VNNI layout. That layout is pair-interleaved (two consecutive dimensions of one token sit next to each other in memory) and transposed. The stored data are therefore K^T in the form the right operand needs. The packed plane uses the same number of bytes as row-major K. The kernel of this PR computes `S = Q * K^T` directly.

```text
main:     S^T = K * Q^T
            K page (64 tokens x 128 dimensions, row-major) is the left operand.
            Packed Q^T is the right operand. S = transpose(S^T) in AVX-512 registers.
this PR:  S = Q * K^T
            The 4 query rows, padded to 16 rows, are the left operand.
            The 16 K panels of the page are the right operand. No transpose.
```

- Heads of other sizes keep the row-major layout (for example the 64-dimension heads of the gpt-oss-120b model).
- Dense pages (full 64-token pages) score bit for bit the same as under the row-major kernel, by unit test.
- Partial pages go through the AVX-512 reader of the layout PR. So does every page when the AMX kernel does not run: under the kill switch `TRON_AMX_DISABLE=1`, on hosts without AMX, and for 128-dimension heads with kv_mul other than 4.

## Words used here

| Term | Meaning |
|---|---|
| PR, main, stack, the layout PR | PR means pull request. `main` is the target branch of the stack. The stack is the sequence of four dependent PRs replacing PR #4424 (the original single pull request for this work). This is the second PR. The layout PR is the first one, PR #4868, branch `jhan-vnnik-1-layout`. This PR is based on it. |
| tron, runtron | tron (the inference program under test), runtron (its command-line tool). |
| token, generated token, layer | A token is a unit of text processed by the model. A generated token is one output token. A layer is one stage of the model's computation. |
| attention, head, Q, K, V | Attention combines saved token information using scores. A head is one attention computation channel. Q holds query vectors, K holds key vectors, and V holds value vectors. The KV cache stores K and V for past tokens. |
| CPU, FPGA | CPU means central processing unit. FPGA means field-programmable gate array. Here it is the accelerator card that runs attention for the pages assigned to it. |
| AMX, AVX-512, VNNI | AMX (Advanced Matrix Extensions) and AVX-512 (Advanced Vector Extensions, 512-bit vectors) are CPU instruction sets. AMX supports tile matrix multiplication. VNNI means Vector Neural Network Instructions. The VNNI layout is an operand format read by VNNI instructions and AMX tile multiplication. |
| tile, A operand, B operand, C tiles, TDPBF16PS, tile region | A tile is a 2-dimensional AMX register of 16 rows by 64 bytes. TDPBF16PS is the tile instruction that multiplies two bf16 tiles and adds the products into an fp32 tile. Its left matrix is the A operand (row-major). Its right matrix is the B operand (VNNI layout). The C tiles are the accumulator tiles that hold the running sums. An AMX tile region is the code section between the tile configuration and the tile release. |
| VNNI layout, packed | Two consecutive dimensions of one token are adjacent in memory. One 64-byte line holds that dimension pair for 16 consecutive tokens. This is the B-operand format of AMX tile multiplication. Packed means stored in the VNNI layout. Packed K, VNNI K and the layout mean the same thing in this PR. A packed slot or page is one whose K uses that layout. |
| row-major K | The layout `main` uses: one contiguous row of values per token. For the heads changed by the layout PR, each row holds 128 values. |
| plane, panel, token block, dimension step | A plane is the K or V storage of one page and one KV head. Unqualified, plane means the K plane here: 64 tokens x 128 dimensions x 2 bytes = 16 KiB (16 x 1,024 bytes). A dimension step is 32 dimensions. A 128-dimension head therefore has 4 steps. A token block is 16 consecutive tokens of a page. A page therefore has 4 blocks. A panel is the 1 KiB part of the plane for one dimension step and one token block: 16 dimension-pair rows of 64 bytes, exactly one B tile. The plane holds 4 steps x 4 blocks = 16 panels. |
| the kernel, the row-major kernel, the packers | The kernel is `qk_vnni_128x4`, added here. It takes the padded Q rows as the A operand and the 16 K panels as the B operand. It writes `S[query][token]` (one score row per query head, one column per token). The row-major kernel is `qk_rowmajor_128x4` of `main` (PR #3879, the pull request that added the AMX attention kernels). It takes the K page as the A operand and the packed queries as the B operand. It stores the tiles into an internal buffer and transposes the 4 query rows out of that buffer into score rows. The packers prepare Q. `pack_q_rows_128x4` (this PR) copies the 4 query rows of one group as the A operand. `pack_q_group_128x4` (`main`) packs them as the B operand. `amx_attn_h128g4` is the namespace of these entry points (the functions that other code calls), named for head size 128 and kv_mul 4. |
| padded Q rows, query-pack slot | The A operand of the kernel: 16 rows of 128 bf16 values (4,096 bytes). Rows 0 to 3 are the 4 query heads of one group. Rows 4 to 15 are zero padding. A query-pack slot is one 4,096-byte buffer per query token of an attention call. It holds that token's packed queries. It serves either packer. |
| CMake, preset, option | CMake configures the build. A preset is a named build configuration. The option means `TRON_K_VNNI`, which defaults to OFF. When enabled, it selects VNNI K storage for every 128-dimension head. No preset enables it. |
| AMX dispatch | `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels and the code that selects them. The kernel and its call sites sit inside that option. |
| layout gate, dense page, dense predicate | The layout gate is `k_vnni::layout_on<head_size>`, a compile-time constant: true for 128-dimension heads when the option is on, false otherwise. It chooses the packer at the pack site and the kernel at the dense-page site. A dense page is a full 64-token page that the query sees whole. The dense predicate, `is_dense_amx_page`, is the run-time check that a page is dense for the AMX page path. |
| the temporary gate | The clause `&& !k_vnni::layout_on<operation_head_size>` that the layout PR places on the dense AMX page path. In that PR it sends every page of a packed slot to the reader. This PR removes it. |
| kill switch, AMX-on, AMX-off | The kill switch is `TRON_AMX_DISABLE=1`. It makes `amx_attn_h128g4::available()` false at run time. Then no AMX kernel and no query pack (one packer call for one query token) runs. AMX-on allows those kernels when their other conditions hold. AMX-off disables them through this switch. |
| KV page, block, slot, geometry | A KV page is a 64-token unit allocated by the cache (`kv_block` in the code). In this PR, block alone means a 16-token token block. A slot is one persistent K/V storage region, usually one per layer or shared between layers. Geometry means the head counts and dimensions. A packed slot uses packed K storage. A row-major slot stores K as contiguous rows. |
| KV head, kv_mul | A KV head is one key/value head. `kv_mul` means query heads per KV head. A query group is the kv_mul query heads that share one KV head. It is 4 heads for the qwen3-4b and llama-3.1-8b models, 3 heads for llama-3.2-3b, and 8 heads for qwen-3-30b-a3b. |
| prefill, decode, pass | A pass is one forward computation of the model over its current input. Prefill processes prompt tokens, usually many tokens per pass. Decode generates one output token per user per pass. |
| owner, view, k_vnni_access | `k_vnni_tensor` owns one 16 KiB K plane as a 64-byte-aligned array. `k_vnni_view` refers to that plane. Views come only from an owner. `detail::k_vnni_access` is the one route from a view to the plane address. Its callers are the typed row operations, the two layout-specific score kernels and the test-only `book::fill_random`, which fills a whole book (the cache object that owns a group of pages) with random values. |
| reader, dotter | The reader is `k_vnni::qk_group` of the layout PR, the AVX-512 routine that scores a query group against one packed K page, one token per vector lane (element position). The dotter is `main`'s software loop that computes one dot product per token from row-major K. |
| store_row, scatter store | `store_row` writes one token's K row into a packed plane with 4 AVX-512 scatters (vector stores to separate addresses) of 16 dwords (4-byte units). Together they write 4 bytes into each of the token's 64 memory lines (64-byte CPU cache lines). `save_k`, the routine that copies a pass's K rows into the cache, stores every token this way in the layout PR (the per-row scatter store). |
| bf16, fp32, float | bf16 is the 16-bit brain floating-point format used for K and Q. fp32, called `float` here, is the 32-bit IEEE single format. IEEE is the standards organization specifying these formats. |
| QK, PV, softmax | QK is the query-key score product. Softmax converts scores into attention weights using exponentials and normalization. PV multiplies those weights by V. |
| identity case | The case "AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K" of `t_amx_numerics` (the AMX numerical-accuracy test binary). It stores the same K values row-major and, through `store_row`, into a packed owner. It packs the same queries both ways. It runs both kernels on real AMX. It compares the 4 x 64 fp32 scores (4 query rows by 64 tokens) bit for bit. It needs AMX hardware, and without it the case returns early with a warning. |
| fakes, probe | Stand-in implementations of every `amx_attn_h128g4` entry point, including `available()`, that `t_amx_dispatch_dtype` (the dispatch test) defines in its own translation unit. They count calls into a probe (a call counter) instead of running AMX. The linker therefore never links the kernel's object file. |
| Catch2, REQUIRE, STATIC_REQUIRE, SUCCEED, WARN | Catch2 is the C++ test framework of the unit tests. REQUIRE is its assertion macro; each evaluation counts as one assertion. STATIC_REQUIRE is a compile-time check that also counts as one assertion. SUCCEED records one passing assertion. A placeholder case (a test case that contains only SUCCEED, used when the tested code is not compiled in) passes through it. WARN prints a warning without failing the case. |
| mutation check | A deliberate code change that a test must catch. The test's failure proves that the test can fail. |
| tp2, slice | `tp2`, also written `-tp2` in a model name, splits the model across 2 devices. A slice is one FPGA with its share of the host's CPU cores and memory. |
| TPS, TTFT | TPS is decode throughput in tokens per second per user. TTFT is time to first token. The measurement tables report the maximum TTFT over all 8 users. |
| base, new, new2, newoff, head, headoff | `base` is `main` at commit `72308ec90c` (the layout PR's merge base, the `main` commit it is based on), built as runtron with row-major K and AMX dispatch on. `new` is this branch at commit `{{HEAD_SHORT}}`, built with the option and AMX dispatch on. `new2` is a second run of `new` (the A/A repeat). `head` is the layout PR at commit `82d05e94be`, built the same way as `new`. `newoff` and `headoff` run `new` and `head` with the kill switch. |
| greedy run, A/A repeat | A greedy run uses temperature 0, a setting that chooses the highest-scoring token. `--pay-for-determinism` performs sums in a fixed order. An A/A repeat runs the same configuration twice as a control. |
| cell, band, standard deviation, paired t | A cell is one model, prompt length, and attention configuration. Standard deviation measures variation between repetitions. The band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. The paired t statistic expresses the mean paired difference relative to its uncertainty. It is dimensionless. |
| CI, required CI, legacy CMake lane | CI means continuous integration, the automated build and test system. Required CI is the workflow `gcp-nix.yml`, plus `deb-smoke.yml`, an APT (Debian package manager) package check that builds no tron binary. The C++ test build of `gcp-nix.yml` uses `nix/cmake-tron-test-build.nix`. The legacy CMake lane is `.github/workflows/cmake-single-platform.yml`. It runs by manual dispatch and from `publish-deb.yml`, the package-publishing workflow. |
| runner, Granite Rapids | A runner is a machine that executes CI jobs. The CI jobs named below ask for the runner labels `self-hosted`, `fpga`, `test` and `avx512`. Granite Rapids is the Intel CPU family of the Xeon 6962P test machine with AMX. The Granite Rapids machine below means that machine. Genoa is the AMD CPU family of the runners without AMX. |
| slice check, cost data | `bin/slice bench --check` checks registered tests for timing records in `config/test-benchmarks.json`. These records are cost data: test durations at 1, 2, and 4 slices. |
| worktree, translation unit | A worktree is a separate checkout used for one build. A translation unit is one source file after its included headers have been expanded. |

## The changes

The kernel file adds the packer and the kernel. [src/tron/kernels/amx_attn.cpp]

- `pack_q_rows_128x4` copies the 4 query rows of one group as stored, 256 bytes each, into rows 0 to 3 of the padded Q rows. It writes nothing else. Rows 4 to 15 are zero padding that the caller keeps zero.
- `qk_vnni_128x4` takes the padded Q rows as the A operand in tile 4. In each of the 4 dimension steps, it loads the K panels of the 4 token blocks as the B operand, into tiles 5 and 6 in turn. Each panel is multiplied into the accumulator tile of its token block (tiles 0 to 3). The result is `S[query][token]`, unscaled fp32 (not yet multiplied by the attention scale).
- The tile stores write 16 rows (one per A row) into a 4 KiB buffer inside the kernel. Only the 4 query rows are copied out into the caller's score rows. The caller's buffer therefore needs 4 rows.
- The plane address is taken once, through `detail::k_vnni_access::plane`. The kernel is one of the two layout-specific readers allowed to take it. The reader is the other.
- Compile-time assertions tie the plane constants of `h/tron/tensor/k_vnni.hpp` (page tokens, head size, dimensions per step, tokens per block, pairs per step, line bytes, panel bytes) to the kernel constants (tile rows, tile row bytes, dimension step).

The interface header declares the two entry points. The kernel's K argument is a typed view. [h/tron/kernels/amx_attn_iface.hpp]

- `qk_vnni_128x4` takes the page's packed K plane as its read-only `k_vnni_view`. A native (row-major) K view, a packed V plane or a bare pointer therefore cannot be handed in by mistake. The row-major kernel keeps its native K view. A packed K plane therefore cannot be handed to it.
- Note [QK orientation] (a named comment block in the header) describes the flipped orientation. With the option on, the stored K plane is the B-operand layout. The kernel therefore takes the padded Q rows as the A operand and the K panels as the B operand. No transpose is needed. The extra work moves to the K store (the per-row scatter store) and to the reader for partial pages.
- The dispatch diagram (the text diagram in the header that shows which routine serves each path) names the kernel beside the row-major kernel. Note [AMX attention dispatch] says that with the option the operand roles swap. The note on 16-row tile stores covers both kernels. The declaration of the kernel states the bit-identity contract with the row-major kernel, and names the identity case as its check.

Software attention (attention computed on the CPU) selects the packer and the kernel at compile time. [h/tron/models/self_attention.hpp]

- At the pack site, the layout gate chooses `pack_q_rows_128x4` for a packed slot and `pack_q_group_128x4` for a row-major slot. The query-pack slots are zero-filled when they are created (`resize()`). Each packer writes only its 4 live rows or columns. The padding both packers rely on therefore stays zero across calls and slot reuse.
- At the dense-page site, the layout gate chooses `qk_vnni_128x4` with `page::k_packed` (the read-only plane view) for a packed slot and `qk_rowmajor_128x4` with the native K view for a row-major slot. The kernel writes into the same 4 x 64 score array that the software loop fills.
- The temporary gate is removed. The compile-time condition of the dense AMX page path is the eligibility predicate alone (`amx_attn_h128g4::eligible`, the compile-time check of head size, kv_mul and query type). The run-time condition, a packed query and a dense page, is unchanged. A dense page of a packed slot therefore takes the AMX page path, as a dense page of a row-major slot does on `main`.
- The query-pack slot comment names both packers and their shared alignment contract. The pack-site comment defines the A and B operands before it uses them.

Three headers update their comments. [h/tron/models/kv_cache.hpp, h/tron/tensor/k_vnni.hpp, h/tron/kernels/k_vnni.hpp]

- Note [K VNNI storage] names the two layout-specific score kernels as the readers of the plane, and says that the dense AMX page path passes `page::k_packed` to the kernel. Its consumer list says that every other visit of a packed slot uses the reader with the same view: partial or partly visible pages, the kill switch, hosts without AMX, builds without AMX dispatch, and the shapes and query types outside the AMX gate. Its "Why" paragraph says that the kernel reads the plane directly as its B operand.
- The kill-switch paragraph says that with `TRON_AMX_DISABLE=1` a packed binary runs the reader: an AMX-off run of the same layout, not a rollback to the row-major binary's numerical results.
- The owner's alignment comment and the reader's header name the kernel as the second reader of the plane. The reader's header lists the same set of pages the reader serves. The owner is aligned to 64 bytes because every pair row is one 64-byte line and the kernel reads the plane in 64-byte tile rows.

Tests change as follows:

- `t_amx_numerics`, the AMX numerical-accuracy test, gains the identity case. It fills a packed owner through `store_row` in scrambled token order (stride 37, offset 11, so that every token is visited once), packs the same queries both ways, runs the row-major kernel and the kernel inside one AMX tile region on the same inputs, and compares the 4 x 64 fp32 scores bit for bit, for 2 seeds. Both kernels add the same four 32-dimension partial dot products in the same order inside TDPBF16PS. The scores must therefore match bit for bit. A wrong panel or a wrong dimension pair would not reproduce them. The two score arrays start with different fill patterns. An element a kernel fails to write therefore cannot match. The packer case gains a section for `pack_q_rows_128x4`: with the padding rows filled with a poison pattern, rows 0 to 3 must hold the query rows bit for bit and rows 4 to 15 must keep the poison. That section runs on every host. [Verification below]
- `t_amx_dispatch_dtype`, the test of dispatch for different activation types (the number formats of the model's intermediate values), adds fakes for the packer and the kernel of this PR beside the fakes of `main`'s packer, QK kernel and PV kernel. The fakes of both packers and of both QK kernels count into the same probe, and the fake of the VNNI packer counts a second time. So a full page expects one pack, one QK and one PV call under either layout, and a partial page expects one pack and no kernel call. The VNNI packer count checks that the dispatch picks the packer of the build's K layout. The two packers share one signature, so the types cannot pin that choice. The kernel choice is pinned by its view type. The dense predicate of the test has no layout clause: it expects the kernels for every full page that packs.
- `t_llama_unit`, the model and cache unit-test binary, adds six compile-time checks (two STATIC_REQUIRE and four STATIC_REQUIRE_FALSE) to the typed-boundary case: the kernel accepts the packed K view, read-only or writable, and rejects raw pointers, the native K view and the V view. The alignment comment names the AMX tile rows.
- `README.ci.md` names the identity case among the tests that exercise the packed layout, and says that it executes AMX only on a Granite Rapids runner.

## Measurements

The measurements compare decode TPS and TTFT with the option on against `main`, and against the layout PR's binary. They also measure the kill switch inside this PR and two controls (comparison runs that each isolate one factor).

Configurations:

- `base`: `main` at `72308ec90c`, built as runtron with row-major K and AMX dispatch on.
- `new`: this branch at `{{HEAD_SHORT}}`, with the option and AMX dispatch on.
- `head`: the layout PR at `82d05e94be`, built the same way as `new`.
- `newoff` and `headoff`: those two binaries with the kill switch.

The experiment ran on {{E_DATE}}:

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
{{ARM_ROWS}}

"Inside" and "beyond" refer to the decision band. The paired t values are dimensionless.

| Prompt length (tokens) | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
{{PAIR_ROWS}}

### This PR against `main` (new vs base)

{{AGAINST_MAIN}}

### The recovery of the layout PR's loss (new vs head)

The layout PR alone loses decode TPS against `main`: -6.4 % at prompt length 1,024 tokens and -11.6 % at 8,192 tokens. Its TTFT rises by 25.8 % and 119.6 % in the same cells. [PR #4868 at `82d05e94be`, measured 2026-10-10, same base and cells] Its description attributes the loss to the temporary gate. That gate sends every page of a packed slot to the reader. The description says that a measurement at this PR's head must establish the recovery.

{{RECOVERY}}

### The kill switch inside this PR (newoff vs new)

With the kill switch, a packed binary packs no query and runs the reader for every page. Without it, a dense page takes the kernel. So this pair measures the cost of the reader against the kernel inside one binary.

{{KILL_SWITCH}}

### Control: AMX off on both binaries (newoff vs headoff)

Both `newoff` and `headoff` run the reader for every page and pack no query. A difference beyond the band would show that the two binaries differ in work outside the kernel.

{{CONTROL_NEWOFF_HEADOFF}}

### Control: the kill switch inside the layout PR's binary (head vs headoff)

`head` with AMX enabled allocates the query-pack slots, enters the AMX tile region and packs the queries for a path its temporary gate never takes. `headoff` skips that preparation. The layout PR's description reports this pair at `82d05e94be` on 2026-10-10 as `headoff` minus `head` (its `newoff` vs `new`): TPS -0.5 % and +0.3 %, and TTFT -65 ms and -425 ms, at prompt length 1,024 and 8,192 tokens. All four differences are inside the band. [PR #4868, Measurements]

{{CONTROL_HEAD_HEADOFF}}

## Verification

Build provenance:

- Machine and date: Granite Rapids, Intel Xeon 6962P with AMX, {{BUILD_DATE}}.
- Revision: `{{HEAD_SHORT}}`, based on the layout PR at `82d05e94be`, which includes `main` at `72308ec90c`.
- Environment: `nix develop`, the project's pinned build shell.
- Compiler: clang version 19.1.7.
- Preset: `native`, which supplies explicit AVX-512 flags.
- Build type: `RelWithDebInfo`, an optimized build with debug symbols.
- Each of the 3 configurations used a separate worktree.

`BUILD_INGEST_MODELS` controls compilation of generated models.

| Configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | Targets | Build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | {{BUILD_PR2}} s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | {{BUILD_PR2ND}} s |
| option off | OFF | ON | OFF | the 5 layout-independent tests | {{BUILD_PR2RM}} s |

`t_heterogeneous_scheduler` tests scheduling across different attention geometries. `t_k_vnni_layout` tests the packed layout, its row operations and the reader. `t_phase1_integration` tests staging (the copy of K and V into buffers read by the FPGA) and dispatch integration.

The following unit-test binaries passed with a fake device (a simulated FPGA). `--skip-benchmarks` excluded their benchmark sections. Each result gives assertions / test cases.

| Test | Option on | Option on, no AMX dispatch | Option off |
|---|---|---|---|
{{TEST_ROWS}}

The identity case ran on real AMX in the option-on build and in the option-off build. The packed owner and the kernel are compiled whether the option is on or off. Neither `t_amx_numerics` run printed an "AMX unavailable" line.

With the option off, the kernel compiles but no packed slot exists. The option-off build's tests back the claim that behaviour is unchanged there. Without AMX dispatch, `t_amx_numerics` and `t_amx_dispatch_dtype` are one-case placeholders.

Kill-switch results in the option-on build:

{{KILLSWITCH_LINES}}

A mutation check of the identity case, in the option-on worktree: with the second panel load of the kernel changed to read token block 2 instead of block 1 (`(step * TOKEN_BLOCKS_4 + 1)` to `+ 2`), the identity case fails. {{MUTATION}} With the file restored, the binary passes again with {{RESTORED_COUNTS}}.

All of these checks are clean at `{{HEAD_SHORT}}`:

- clang-format version 19.1.7, the source formatter, with `--dry-run --Werror` on all 9 changed C++ files.
- `git diff --check`, the whitespace check, against the layout PR's head.
- A search for the prohibited `<cassert>` header in the diff.

Syntax-only compilation used clang version 19 with the product's compile flags. It covered 38 configurations with 0 errors and 0 warnings:

- All 4 combinations of AMX dispatch on/off and the option on/off for 9 translation units: `t_llama_unit`, `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `heterogeneous_scheduler_compile` (heterogeneous scheduling compilation), `scheduler/full.cpp` (the full scheduler), `gof.cpp` (staging), `t_gof_dma` (staging DMA, direct memory access transfers), and `t_kv_oom_subcases` (out-of-memory cases).
- `kernels/amx_attn.cpp` (the AMX kernels, with the kernel of this PR) with dispatch on and the option on/off.

The compiler flag is `-fsyntax-only`.

### Host test suite and token identity ({{SMOKE_DATE}})

The checks ask two questions. Does the host suite (the unit tests run by `make test-host` with a fake device) meet the exception rules listed under Acceptance rules below? Are the generated tokens identical across the selected configurations? `base` and `head` are the comparators defined in Measurements.

Host-suite setup:

- `make build-test-host` compiled the host tests.
- `make test-host` ran them with a fake device in the option-on worktree.
- The experiment used its half of the machine with production serving stopped.

Token-identity setup:

- runtron with qwen3-4b, tp2, and 1 user.
- Temperature setting 0, `--pay-for-determinism`, random seed identifier 1, and 256 generated tokens.
- CPU attention at prompt lengths 1,024 and 8,192 tokens.
- FPGA attention at prompt length 1,024 tokens.
- Binaries: `new`, `new2` (the A/A repeat), `newoff`, `head`, and `base`.

Acceptance rules:

- The host suite permits only the existing Python-environment exceptions. `t_proxy_lib`, a proxy-library test, may skip. `t_proxy_llama31`, a Llama proxy test, may fail. Both lack the virtual environment `t/proxy/.venv`, the isolated Python dependency directory.
- Every binary exits with status 0 (success) and produces exactly 256 generated tokens.
- `new2` must match `new` for all 256 generated tokens in each cell.
- `newoff` must match `new` for those same tokens.
- The comparison with `base` is informational. [Issue #4444] The comparison with `head` is expected identical when `newoff` matches `new`. The measured result is reported either way.

Host-suite result:

{{HOST_LINES}}

| Cell | new vs new2 | newoff vs new | new vs head | new vs base | head vs base |
|---|---|---|---|---|---|
{{SMOKE_ROWS}}

### CI coverage

Required CI builds with both CMake options off. Neither `TRON_AMX_DISPATCH` nor `TRON_K_VNNI` is enabled in its test build. [nix/cmake-tron-test-build.nix]

- There, `t_amx_dispatch_dtype` runs its placeholder case, and `t_amx_numerics` runs its placeholder case. The fakes compile, but nothing calls them.
- The identity case needs AMX hardware.
- The legacy CMake lane compiles both options on. [.github/workflows/cmake-single-platform.yml]
- The required test jobs and the legacy CMake lane's jobs ask for the same runner labels. That runner pool holds Granite Rapids hosts with AMX and Genoa hosts without it.
- No job asks for a label that routes it to an AMX host.
- The identity case therefore executes in the legacy lane only when its job is scheduled on a Granite Rapids runner. It also executes on the Granite Rapids test machine by hand, as reported above.
- The author explicitly accepts this limitation for this PR. Issue #4865 tracks enabling both options in the required test build and an AMX runner for this case.

## Open items

**128-dimension heads with kv_mul other than 4 query heads.**

The kernel serves kv_mul 4 only. Other groups retain the packed layout and use the reader wherever `main` uses the dotter, as in the layout PR. Not measured at `{{HEAD_SHORT}}`. No AMD host was measured at this head either. On such a host the kernel never runs, and the reader serves every packed page, as in the layout PR. The measurement that settles it: decode TPS of llama-3.2-3b (kv_mul 3) and qwen-3-30b-a3b (kv_mul 8) at this head against `main` at `72308ec90c`, 3 repetitions, the band rule of the Measurements section.

Earlier measurements on the PR #4424 branch, whose reader is this PR's, give the expected direction:

| Model and load | Prompt length | Decode TPS change | Repetitions and interpretation | Revisions and date |
|---|---|---|---|---|
| llama-3.2-3b, tp2, kv_mul 3 query heads, 32 users | 200 tokens per user plus an 800-token prompt prefix shared by all users | -1.4 % | Resolved in two independent pairs of benchmark passes with the nightly benchmark settings | `9d5c7a389b` vs `main` `be0d5565b3`, 2026-10-09 |
| qwen-3-30b-a3b, kv_mul 8 query heads, 8 users, tp2 | 1024 tokens | +1.5 % | 6 repetitions, within reported measurement variation | `65a1c41d72` vs `main` `c7844ca2ce`, 2026-09-16 |
| same | 2048 tokens | -4.1 % | 3 repetitions | same revisions and date |
| same | 8192 tokens | +24.1 % | 3 repetitions | same revisions and date |

"Resolved" is the earlier report's classification: a difference is resolved when the paired t statistic is at least 2.26 in magnitude (the two-sided 95 % threshold of the t distribution for that report's 10 rounds) and the difference is at least 1 %.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]**

- With this PR, the kill switch gives an AMX-off run of the same binary through the reader. It does not reproduce the tokens of a clean binary, meaning a build with both options off.
- {{DIVERGENCE}}
- {{NEWOFF_NEW}}
- The rollback contract (the documented promise of what the kill switch restores) promises clean-binary tokens. [Item 4 of Note [AMX attention dispatch], h/tron/kernels/amx_attn_iface.hpp]
- Issue #4444 records two choices:
  1. Accept the narrower rollback contract. Add "with `TRON_K_VNNI` off" to item 4.
  2. Keep a row-major binary as the deployment rollback artifact. Document that requirement.

**The per-row scatter store's cost in TTFT.**

- `save_k` of the layout PR stores each token's K row with 4 scatters that touch 64 memory lines. The row-major store writes 4 whole lines. Those extra line writes are a prefill cost.
- {{SCATTER_TTFT}}
- The third PR of the stack, the shared block save (a K save that transposes 16 tokens in registers and writes every line of a block whole), is intended to remove it.

**Cost data of t_amx_numerics.**

The identity case and the new packer section add run time to `t_amx_numerics`. Its Granite Rapids row in `config/test-benchmarks.json` is not refreshed here. The refresh is planned with the fourth PR's cost-row update. The slice check passes with the existing row.

**Benchmark binary mismatch, inherited from PR #3879. Reviewers decide.**

- The legacy CMake workflow's `build` job compiles runtron with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`. It transfers that binary to its `benchmark` job.
- A successful transfer benchmarks the AMX kernels and packed K.
- After a failed transfer, the benchmark job builds runtron through `make`. That build sets neither option. It benchmarks row-major K without AMX kernels.
- PR #3879 introduced the mismatch for AMX dispatch. The layout PR added the layout option to the same configure line. This PR changes neither.
- Required CI is unaffected. Its benchmark binary has neither option enabled.

**CI coverage gap. [Issue #4865]**

Required CI runs the placeholder cases of `t_amx_dispatch_dtype` and `t_amx_numerics` and never the identity case. The build and test evidence of this PR is the Granite Rapids run reported under Verification. [CI coverage above]

## The stack

PR #4424 uses branch `jhan-amx-vnniK` and adds 4,054 lines. Four dependent PRs replace it. Each is based on the preceding PR. PR #4424 remains open as a reference until all four are open.

| Order | PR branch and base | What it adds | State |
|---|---|---|---|
| 1 | PR #4868, `jhan-vnnik-1-layout`, based on `main` | Packed K layout, owner and views, per-row store, reader, FPGA staging gather, the option disabled in presets, and tests | ready for review |
| 2 | this PR, `jhan-vnnik-2-amx`, based on PR #4868 | The AMX QK kernel `qk_vnni_128x4` and query packer `pack_q_rows_128x4`. A bit-identity test compares with the row-major kernel. The temporary gate and comments are removed. | draft until PR #4868 merges |
| 3 | `jhan-vnnik-3-shared-save`, based on this PR | Shared saves of 16-token blocks, transposed in registers and written as whole cache lines by the main thread and idle helper threads (worker threads with no work of their own at that moment). This provides PR #4424's TTFT improvement. | to follow as a draft |
| 4 | `jhan-vnnik-4-tail-block`, based on PR 3 | A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the packed layout when all 16 rows are saved. A row-major policy under hardware attention addresses issue #4500. The `deb` package-build preset enables the option in the released package. | to follow as a draft |

The option stays off in every preset until PR 4. Intermediate states therefore do not enter production through those presets.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
