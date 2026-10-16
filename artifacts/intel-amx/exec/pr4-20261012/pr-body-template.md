## Short version

This PR (pull request) keeps a 16-token block of the packed attention keys row-major until the block's 16th row is saved, converts the block to the VNNI layout at the end of the pass that saved that row, leaves the blocks that the FPGA scores row-major, and turns the layout on in the `deb` package-build preset. Under FPGA attention, the decode TPS of qwen3-4b is inside the band against `main` at tp2 and at tp4, where the block-save PR's binary loses 1.9 % and 11.0 %: the claim of issue #4500 holds. Under CPU attention with AMX on, decode TPS and TTFT are inside the band against the block-save PR in the three measured cells, and the gains against `main` (+4.7 %, +9.4 % and +2.4 % TPS) repeat. Two open items need the reviewers: with AMX off, this PR's binary is 2.0 % to 3.4 % slower in decode TPS than the block-save PR's in all three CPU cells, and the generated tokens equal `main`'s in some measured cells and the block-save PR's in others, not `main`'s in every CPU cell as expected. The whole-machine campaign is pending. This is the last PR of the stack: the option is on in the `deb` preset and off in every other preset.

### Background

The qwen3-4b model used below is the Qwen3 4-billion-parameter instruction-following model. The detailed results, decision thresholds and comparison revisions are in Measurements. Words used here defines the technical terms.

Issue #4500 reports that qwen3-4b with FPGA attention loses decode throughput under the VNNI K layout of PR #4424. The records it cites measured the layout without this PR's tail block against row-major `main`: on 2026-09-16 with runtron, one engine, 8 users, prompt length 1,024 tokens, 6 repetitions, decode TPS was -2.2 % at tp2 and -9.7 % at tp4; on 2026-09-18 with the nightly's own layout (the CI harness, 10 rounds, 8 users over 4 tp2 engines or 2 tp4 engines) it was -5.0 % at tp2 (186.13 to 176.75 TPS) and -11.0 % at tp4 (149.94 to 133.44 TPS, below the CI threshold of 135 TPS). The generated tokens under FPGA attention were identical between the two binaries.

The cause is the per-token store of the layout. In decode every step saves one token per user. The scatter store of the layout PR writes that token's 64 dimension pairs into 64 different 64-byte lines, 4 bytes each. The FPGA staging (the copy of K rows into the buffer that the card reads) then gathers the row back out of 64 lines for every generated token. The row-major store of `main` writes and reads 4 whole lines per token.

The design has three parts:

1. A block stays row-major until it is complete. Token t of block c owns 256 contiguous bytes (its 128 bf16 values in dimension order, 4 lines) inside the block's own 4 KiB. A decode step stores 4 whole lines. The staging reads the row in place.
2. The block whose 16th row a pass saves is converted to the VNNI layout at the forward end of that pass, after the cooperative staging has drained (`wait_for_coop_gof`). That staging gather is the last reader of the pass that can hold a block's rows row-major. A run of 16 tokens that fills a block (prefill) takes the block save of PR #4898 and holds the VNNI layout at once.
3. For an operation the FPGA scores, no row is recorded and no block is converted. Past the engagement point (the first sequence position the FPGA scores, 127 by default), the FPGA holds the K and V of every complete GOF (a group of four consecutive tokens) and the CPU scores only the tail above them. So the AMX kernel never reads a block that decode completes there, and the conversion would cost a serial copy on the main thread for nothing.

The result is bit-identical to the layout PR's store: `block_to_vnni` writes the same bytes as `store_row` per token. The page records which layout each block holds, per storage slot, and every reader and writer of a row takes the layout from that record.

The expectation for the whole-machine campaign comes from the 2026-10-09 run of the PR #4424 branch (the nightly deb 2026.10.08-be0d5565 of `main` at `be0d5565b3` against the PR #4424 deb, four passes of 10 rounds, the resolution rule of Measurements): llama-3.1-8b at tp2 with 32 users and prompt length 4,096 tokens +4.8 % TPS (resolved), gpt-oss-120b at tp4 -0.5 % TPS and -22 ms TTFT (not resolved), qwen3-4b with FPGA attention -0.9 % at tp2 and -0.4 % at tp4 (not resolved: the loss of issue #4500 is gone), every other configuration within +/-1 % and not resolved.

## Words used here

| Term | Meaning |
|---|---|
| PR, main, stack, the layout PR, the kernel PR, the block-save PR | PR means pull request. `main` is the target branch of the stack. The stack is the sequence of four dependent PRs replacing PR #4424 (the original single pull request for this work). This is the fourth and last PR. The layout PR is the first one, PR #4868, branch `jhan-vnnik-1-layout`. The kernel PR is the second one, PR #4887, branch `jhan-vnnik-2-amx`, based on the layout PR. The block-save PR is the third one, PR #4898, branch `jhan-vnnik-3-shared-save`, based on the kernel PR. This PR is based on the block-save PR. |
| tron, runtron, rinzler | tron (the inference program under test), runtron (its command-line tool), rinzler (its production server binary, installed by the Debian package). |
| token, generated token, layer | A token is a unit of text processed by the model. A generated token is one output token. A layer is one stage of the model's computation. |
| attention, head, Q, K, V, QK, PV | Attention combines saved token information using scores. A head is one attention computation channel. Q holds query vectors. K holds key vectors. V holds value vectors. The KV cache stores K and V for past tokens. QK is the query-key score calculation. PV combines attention probabilities with value vectors. |
| CPU, FPGA | CPU means central processing unit. FPGA means field-programmable gate array. Here it is the accelerator card that runs attention for the pages assigned to it. |
| hardware attention, software attention, USE_HW_ATTN, engagement point | Hardware attention (FPGA attention) scores the tokens from the engagement point on with the FPGA cards. Software attention (CPU attention) scores every token on the CPU. The environment variable `USE_HW_ATTN=0` selects software attention; unset, the released package runs hardware attention for ingested models. The engagement point (`hw_attn_engagement_point`, 127 by default) is the first sequence position the FPGA scores. The CPU scores every position below it and the tail above the last complete GOF. |
| GOF, staging, scratch | A GOF (group of four) is the hardware KV cache's unit of 4 consecutive tokens of K and V. The staging (`gof::populate`) copies a GOF's rows into a buffer that DMA (direct memory access) moves to the FPGA card. Cooperative staging is that work done by the pass's worker threads next to the compute; `wait_for_coop_gof` waits until it has finished. Scratch is a caller-owned temporary buffer; the staging gathers a packed row into it. |
| AMX, AVX-512, VNNI | AMX (Advanced Matrix Extensions) and AVX-512 (Advanced Vector Extensions, 512-bit vectors) are CPU instruction sets. AMX supports tile matrix multiplication. VNNI means Vector Neural Network Instructions. The VNNI layout is an operand format read by VNNI instructions and AMX tile multiplication. |
| VNNI layout, packed | Two consecutive dimensions of one token are adjacent in memory. One 64-byte line holds that dimension pair for 16 consecutive tokens. This is the right-operand format of AMX tile multiplication. Packed means stored in the VNNI layout. Packed K, VNNI K and the layout mean the same thing in this PR. A packed slot is one whose K uses that layout. A VNNI block is a block that holds the layout now. |
| row-major K, row-major tail block, row_major_row | Row-major K is the layout `main` uses: one contiguous row of values per token. A row-major tail block (this PR) is a 16-token block of a packed slot whose rows are stored row-major, one contiguous 256-byte row per token, inside the block's own 4 KiB, until all 16 rows are saved. `row_major_row` is the typed view of one token's row in such a block: 4 lines, 64-byte aligned. |
| plane, panel, token block, dimension step | A plane is the K or V storage of one page and one KV head. Unqualified, plane means the K plane here: 64 tokens x 128 dimensions x 2 bytes = 16 KiB. A dimension step is 32 dimensions. A 128-dimension head therefore has 4 steps. A token block is 16 consecutive tokens of a page. A page therefore has 4 blocks. Block c holds the page offsets c x 16 to c x 16 + 15. A panel is the 1 KiB part of the plane for one dimension step and one token block: 16 dimension-pair rows of 64 bytes. The plane holds 4 steps x 4 blocks = 16 panels. In a row-major block, panel (t / 4, c) holds the rows of tokens 4 (t / 4) to 4 (t / 4) + 3 of block c, 256 bytes each. |
| line, dword, scatter | A line is a 64-byte CPU cache line. A dword is a 4-byte unit. A scatter is a vector store whose 16 dwords go to 16 separate addresses. |
| the kernel, the reader, the dotter | The kernel is `qk_vnni_128x4` of the kernel PR, the AMX routine that reads the packed plane as its right operand and scores one dense page (a full 64-token page that the query sees whole). The reader is `k_vnni::qk_group` of the layout PR, the AVX-512 routine that scores a query group (the query heads that share one KV head) against the VNNI blocks of one page, one token per vector lane. The dotter is `main`'s software loop that computes one dot product per token from a row-major row. With this PR it also scores the rows of a row-major tail block. |
| store_row, the per-row store, the scatter store | `store_row` writes one token's K row into a packed plane with 4 scatters of 16 dwords. Together they write 4 bytes into each of the token's 64 lines. With this PR `set_k_row` takes it only for a row saved again into a block that is already VNNI. |
| store_block, the block save | `store_block` (the block-save PR) writes the K rows of up to 16 tokens of one token block into a packed plane: a register transpose and whole-line stores. Its mask parameter stays for its test. Every other caller passes the full mask. The block save means `page::set_k_block`, which stores one whole block through it. |
| block_to_vnni, block_to_rows, the conversion, the forward end | `block_to_vnni` converts one block in place from row-major to the VNNI layout: the 16 rows are copied to a 64-byte aligned stack array, then `store_block` writes the block with the full mask. `block_to_rows` is the inverse. The conversion means `block_to_vnni` of a complete block. The forward end is the point of a pass, after the plugin's `run()` joined its workers and the cooperative staging drained, at which `convert_pending_k_blocks` converts the blocks that the pass completed. |
| saved-row bits, converted-block bits, note_k_row_saved, note_k_block_saved, pending block | The page keeps, per storage slot, one bit per page offset that says the row is saved (`k_rows_saved_`) and one bit per block that says the block holds the VNNI layout (`k_vnni_blocks_`, read through `page::k_vnni_blocks`). `note_k_row_saved` sets a row bit and returns true when the row's block has all 16 rows saved and is not converted yet. `note_k_block_saved` sets the 16 row bits and the block bit after a whole-block save. A pending block is a block whose 16th row a pass saved row-major; `save_k` queues it (`pending_k_blocks_`, main thread only) and the forward end converts it. |
| k_forget_row, k_row_if_row_major, storage ref, EAGLE view | `k_forget_row` runs when a new token takes a page offset (`clear_kv_complete_at`): it drops the saved-row bits of that offset and of every offset above it, and the converted-block bits of those blocks, in every storage slot; the offset's own block is converted back to row-major first when it was converted and keeps rows below the offset. `k_row_if_row_major` returns a token's row in place when its block is row-major; the staging reads it directly. A storage ref (`page::k_storage_ref`) is a storage slot and its layout-state entry, taken at the save (`k_storage_of`), so that a later storage-view change cannot redirect a pending conversion. The EAGLE view is the separate storage view of EAGLE speculative decoding (a draft-model technique); it has its own layout state. |
| dense gate | The third condition of the dense AMX path (`k_layout_dense` in `self_attention.hpp`), after the query packing and the dense page predicate: every block of the page must hold the VNNI layout (`page::k_vnni_blocks` equal to the mask `BLOCKS_PER_PAGE_MASK_0XF`, binary 1111). Otherwise the page takes the software loop. |
| hardware-attention policy | Note [Row-major blocks under hardware attention] in `kv_cache.hpp`: when the FPGA scores an operation's K (`cached_operation_uses_hw`, decided once per model), `save_k` records no saved-row bits for the rows a short run stores and queues no conversion. A block completed by short runs stays row-major. A whole-block save still writes the VNNI layout. |
| set_k_row, get_k_row, set_k_block | The page accessors. `page::set_k_row` and `page::get_k_row` store and load one token's row and follow the block's recorded layout. `page::set_k_block` stores one whole block in the VNNI layout. It has no mask parameter. |
| run, work unit | A run is a sequence of consecutive tokens of one pass that fall into the same 16-token block of the same page. A work unit is a run of consecutive items of the pass's item list with the same KV-write flag, inside one block when the items write KV (the block-save PR). |
| minibatch, item, KV-write flag | A minibatch (`batch` in the code) is one group of a pass's token jobs. Its items are the token jobs of the pass. A generated plugin has one minibatch per pass, so the minibatch holds the whole pass. The KV-write flag (`token_jobs_do_kv`) says whether an item writes K and V. |
| main thread, main helpers, window, join, watchdog | The main thread runs the schedule of a generated plugin. The main helpers are the threads of that plugin that run the per-token kernels. A window is one shared store of the block-save PR: the state that the main thread opens in `save_k` and that the helpers join. The join is the main thread's wait for every helper to finish the open window. The watchdog aborts when the join has not completed 120 s after its first clock read. This PR changes none of them. |
| generated plugin, handwritten plugin, code generator | A generated plugin is the model code that the code generator emits for an ingested model. A handwritten plugin is a model whose code is not generated. The code generator is tron's Haskell program (`ingest/src/TronCpp.hs`) that emits the generated plugins. This PR changes no file of it. |
| the option, CMake, preset, the deb preset, the released package | The option means `TRON_K_VNNI`, the CMake switch that selects VNNI K storage for every 128-dimension head. CMake is the build-configuration tool. A preset is a named CMake build configuration. The `deb` preset builds the released Debian package (`make deb`), the package the nightly installs and production serving runs. This PR sets the option ON in that preset and leaves every other preset at the default OFF. |
| AMX dispatch | `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels and the code that selects them. The `deb` preset has it ON since PR #4505. |
| kill switch, AMX-on, AMX-off | The kill switch is `TRON_AMX_DISABLE=1`. It makes `amx_attn_h128g4::available()` false at run time. Then no AMX kernel runs. The reader scores the VNNI blocks and the dotter scores the row-major tail rows. The store is the same with or without the switch. |
| KV page, slot, storage slot, geometry | A KV page is a 64-token unit allocated by the cache (`page` in the code). A slot is one persistent K/V storage region. A storage slot is a slot's physical storage; the EAGLE view maps logical slot zero onto an extra storage slot. Geometry means the head counts and dimensions. A packed slot uses packed K storage. A row-major slot stores K as contiguous rows and keeps no layout state. |
| KV head, kv_mul | A KV head is one key/value head. `kv_mul` means query heads per KV head. It is 4 heads for the qwen3-4b model. |
| prefill, decode, pass, TTFT, TPS | A pass is one forward computation of the model over its current input. Prefill processes prompt tokens, usually many tokens per pass. Decode generates one output token per user per pass. TTFT is time to first token; the runtron tables report the maximum over all 8 users. TPS is decode throughput in tokens per second per user. |
| owner, view | `k_vnni_tensor` owns one 16 KiB K plane as a 64-byte-aligned array. `k_vnni_view` refers to that plane. Views come only from an owner. A test that works on an owner directly uses no page and runs whatever the option is. |
| completion marks, dispatch credits | After the store, `save_k` marks each token's K as complete in its page and credits the dispatch counter of the token's attention group when the operation has a hardware slot. The main thread does both after the join. |
| bf16, fp32 | bf16 is the 16-bit brain floating-point format used for K and Q. fp32 is the 32-bit IEEE single format. IEEE is the standards organization specifying these formats. |
| Catch2, REQUIRE, SECTION, CAPTURE, SUCCEED | Catch2 is the C++ test framework of the unit tests. REQUIRE is its assertion macro. Each evaluation counts as one assertion. A SECTION is a sub-part of a test case. Catch2 runs the case once per leaf section. CAPTURE prints named values when an assertion fails. SUCCEED records one passing assertion. A placeholder case contains only SUCCEED, when the tested code is not compiled in. |
| mutation check | A deliberate code change that a test must catch. The test's failure proves that the test can fail. This PR reports two. |
| poison pattern | A fixed value written over a buffer before a check, so that an untouched byte stays recognizable. The tail-block tests use the bf16 bit pattern 0xa5a5. |
| tp2, tp4, slice, engine | `tp2` and `tp4`, also written `-tp2` and `-tp4` in a model name, split the model across 2 or 4 devices. A slice is one FPGA with its share of the host's CPU cores and memory. An engine is one tron process that holds one copy of a model over its slices; under rinzler, platformd (the service manager of the test machine) starts the engines. |
| base, new, new2, newoff, head, headoff | `base` is `main` at commit `72308ec90c` (the layout PR's merge base, the `main` commit it is based on), built as runtron with row-major K and AMX dispatch on. `new` is this branch at commit `{{HEAD_SHORT}}`, built with the option and AMX dispatch on. `new2` is a second run of `new` (the A/A repeat). `head` is the block-save PR at commit `{{PR3_SHORT}}`, built the same way as `new`. `newoff` and `headoff` run `new` and `head` with the kill switch. |
| base deb, target deb, restore deb | The base deb is the Debian package built from `main` at `72308ec90c` with the `deb` preset of that commit (AMX dispatch on, row-major K), version `{{W_BASE_VERSION}}`. The target deb is the package built from this branch at `{{HEAD_SHORT}}` with the `deb` preset of this PR (both switches on), version `{{W_TARGET_VERSION}}`. The restore deb is whatever package was installed when the campaign started; it is reinstalled at the end. |
| greedy run, A/A repeat | A greedy run uses temperature 0, a setting that chooses the highest-scoring token. `--pay-for-determinism` performs sums in a fixed order. An A/A repeat runs the same configuration twice as a control. |
| arm, cell, band, standard deviation, paired t | An arm is one binary with its runtime settings. A cell is one model, parallelism, user count, prompt length and attention configuration. Standard deviation measures variation between repetitions. The band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. The paired t statistic expresses the mean paired difference relative to its uncertainty. It is dimensionless. |
| the nightly, the perf phase, the harness, rounds, resolved | The nightly is the nightly test job of the systems_test repository that installs the newest tron deb on the Granite Rapids test machine and runs its phases. Its perf phase runs 14 configurations (model, parallelism, users, prompt length) with 10 rounds of one request per user, TPS captured over generated tokens 896 to 1024. The harness is that repository's checkout at commit `14f0ce4`; the campaign below drives its own perf code by hand for the chosen configurations. A cell is resolved when its target differs from its base beyond noise: the paired t over the rounds of both pass pairs is at least 2.26 in magnitude (the two-sided 5 % threshold for 9 degrees of freedom) and the difference is at least 1 % (for TTFT also at least 1 ms). A cell that is not resolved is read as noise. |
| VmHWM, VmRSS | Fields of `/proc/<pid>/status` read per rinzler process after every provisioning and every benchmark of the campaign: the peak resident set size and the current resident set size, in MiB. |
| CI, GCP Nix, legacy CMake lane | CI means continuous integration, the automated build and test system. GCP Nix is the default build-and-test workflow, `gcp-nix.yml`. Its C++ test build uses `nix/cmake-tron-test-build.nix`. The legacy CMake lane is `.github/workflows/cmake-single-platform.yml`. It runs by manual dispatch and from `publish-deb.yml`, the package-publishing workflow. |
| runner, Granite Rapids | A runner is a machine that executes CI jobs. Granite Rapids is the Intel CPU family of the Xeon 6962P test machine with AMX and 8 FPGA cards. The Granite Rapids machine below means that machine. |
| slice check, cost rows, bin/slice bench | `bin/slice bench --check` checks registered tests for timing records in `config/test-benchmarks.json`. These records are the cost rows: test durations at 1, 2 and 4 slices and the peak memory, per host. `bin/slice bench --update <tests>` measures the named tests at the three widths and rewrites their rows. The slice check is the CI job that runs when that file changes. |
| lint-notes, Note | lint-notes is the repository's check that every `Note [...]` reference names a defined Note (a named comment block whose title line is underlined with tildes). This PR adds two Notes. |
| worktree, translation unit | A worktree is a separate checkout used for one build. A translation unit is one source file after its included headers have been expanded. |

## The changes

The owner's header adds the row-major form of a block and the in-place conversion. [h/tron/tensor/k_vnni.hpp]

- Note [Row-major tail block] describes the form: token t of block c owns 256 contiguous bytes at `row_major_row`, inside the block's own 4 panels. A row-major block and a VNNI block occupy the same 4 KiB, and neither layout touches another block.
- `row_major_row` returns the typed row view of one token of a row-major block: 128 contiguous bf16 values on a 64-byte line. The caller knows from the page's state that the block is row-major; the view does not say so.
- `store_row_major` and `load_row_major` move one token's row in and out of that form: 4 whole 64-byte lines, the same lines the row-major layout's store writes.
- `block_to_vnni` converts block c in place from row-major to the VNNI layout. The 16 rows are copied to a 64-byte aligned stack array first, because `store_block` writes panel (s, c) while the rows of tokens 4 s to 4 s + 3 still live there. Then `store_block` writes the block with the full mask. `block_to_rows` is the inverse: it loads the 16 rows out of the VNNI columns and stores them row-major.
- Four names: `PANEL_ROWS_4` (the token rows one panel holds in the row-major form), `BLOCKS_PER_PAGE_MASK_0XF` (the 4 blocks of a page as a bit mask), `block_bit(c)` (bit c of a block mask) and `offset_bit(offset)` (bit `offset` of a page-offset mask). Two compile-time assertions tie them to the block count.
- `store_block` is unchanged. Its mask parameter stays for the block-save test. Every other caller passes the full mask.

The cache header records the layout per block and converts at the boundaries. [h/tron/models/kv_cache.hpp]

- The page keeps two bit sets per storage slot: the saved rows (`k_rows_saved_`, one 64-bit word, one bit per page offset) and the converted blocks (`k_vnni_blocks_`, one byte, one bit per block). Entry `n_slots` is the EAGLE storage. The bits exist for every slot; only a packed slot's readers and writers take their layout from them.
- `note_k_row_saved` sets the row's bit and returns true when the row's block now has all 16 rows saved and is not converted yet. A row saved again into a block that waits for its conversion returns true again (the conversion is idempotent). A row of a converted block returns false. A row-major slot keeps no bits and returns false.
- `note_k_block_saved` sets the 16 row bits and the block bit after a whole-block save. The caller stores every KV head first, so that no reader sees the block bit before every head holds the layout.
- `k_vnni_blocks` returns the converted blocks of a slot, one bit per block.
- `k_storage_ref` pairs a storage slot with its layout-state entry. `k_storage_of` resolves a logical slot under the current storage view. The pending list of `save_k` keeps the resolved pair, so a storage-view change between the save and the forward end cannot redirect the conversion.
- `k_block_to_vnni_at` converts block c of every KV head when its 16 rows are saved and it is not converted yet, then sets the block bit. It refuses an incomplete or converted block.
- `set_k_row` and `get_k_row` follow the block's recorded layout: the VNNI column of a converted block, the row-major row otherwise.
- `set_k_block` has no mask parameter. It stores one whole block through `store_block` with the full mask.
- `k_row_if_row_major` returns a token's row in place when its block is row-major, and an invalid view for a converted block. The staging reads it directly.
- `k_forget_row` runs from `clear_kv_complete_at` when a new token takes a page offset. It drops the saved-row bits of that offset and of every offset above it, and the converted-block bits of those blocks, in every storage slot. When the offset's own block was converted, keeps rows below the offset (the offset is not a block start) and the storage is readable, the block is converted back to row-major first, so those rows stay readable. Blocks above hold no live row: their bits are dropped and their bytes are left alone. A decode append whose offset has no bit set makes two loads per slot and returns.
- Page copies carry the state with the rows. A whole-page copy copies the owner, bits included. A token-by-token copy converts the destination blocks it touches back to row-major first, copies every row row-major (loading a VNNI source row into the row-major destination row, or copying row to row), and converts the destination blocks whose 16 rows are saved after the copy. The EAGLE storage is copied the same way with its own state entry.
- Note [Row-major blocks under hardware attention] states the policy and its reason, and the cost it accepts: a range that the software scores although the operation is a hardware one (before the engagement point, a prompt shorter than 128 tokens, a shard without HBM, a raised engagement point) scores the blocks decode completed with the dotter, where the conversion would have let the AMX kernel score a page of them.
- Note [K VNNI storage] gains the state paragraph (who sets, clears and reads the bits, and why the conversion runs at the forward end and not inside `save_k`). Its six consumer items say what each consumer does now: the two store paths, the dense gate, the software loop's two readers, the staging's direct read, the copies, and the layout-following accessors.

The model header queues the completed blocks and converts them at the forward end. [h/tron/models/model.hpp]

- `store_k_block`'s rule is `n < k_store_block`: a run shorter than 16 tokens is stored row by row with `set_k_row`, into the block's row-major form or into the VNNI column of a block that is complete already. A run of 16 tokens takes `set_k_block` and `note_k_block_saved`. A `TRON_ASSERT` (the check that stops the process with a message) requires that such a run covers its block. The constant `k_scatter_run_len` and the masked partial-block store are gone.
- `pending_k_block` and `pending_k_blocks_` hold the blocks that this pass completed through short runs: the page, the storage ref and the block index. Only the main thread touches the list.
- After the join, `save_k_impl` records every stored row with `note_k_row_saved` and queues a block that completes, unless the hardware attention scores this operation's K (`cached_operation_uses_hw`): then no row is recorded and the block stays row-major.
- `convert_pending_k_blocks` converts the queued blocks and clears the list. The forward end calls it after `wait_for_coop_gof` and before the logit delivery, under the trace event `convert_k_blocks` (a span of tron's Perfetto timing trace).
- Note [Shared block save] item 1 describes the two store paths and the conversion.

The attention header gates the dense AMX path and scores the tail rows with the dotters. [h/tron/models/self_attention.hpp]

- `k_layout_dense` is the third gate of the dense AMX path, after the query packing and `is_dense_amx_page`: every block of the page must hold the VNNI layout. It is read after the dense predicate, so a page nothing is relevant for is never asked for its state (a book, the cache object that owns a group of pages, may have no active KV slot). A row-major slot keeps no state and the gate is always open there.
- The software loop of a packed slot fetches the page's block mask and its packed plane at the first relevant token. A token of a VNNI block sets its bit in the `live` mask, and the reader scores those tokens after the loop when `live` is not zero. A token of a row-major block is scored inside the loop by the dotters through `row_major_row`. The dotter array exists in VNNI builds now.

The kernel interface and the reader name the two store paths. [h/tron/kernels/amx_attn_iface.hpp, h/tron/kernels/k_vnni.hpp]

- Note [QK orientation] says that the extra work of the flipped orientation moves to the K save: the block save for a run of 16 tokens, the row-major store for a shorter run, the in-place transpose at the forward end.
- The reader's comment states the live-bit rule: every block with a live bit holds the VNNI layout. The caller scores the tokens of a row-major block with the dotter and keeps their bits clear. The header includes `<cstring>` for the `std::memcpy` of its query load.

The scheduler's staging reads a row-major row in place. [h/tron/scheduler/full.hpp]

- The K callback of the staging returns the row pointer from `k_row_if_row_major` for a row-major block (the usual case under hardware attention) and gathers a converted block's row into the scratch buffer with `get_k_row`, as before. The staging bytes and the card's memory layout are unchanged.

The `deb` preset compiles the layout. [CMakePresets.json, README.ci.md]

- The `deb` preset sets `TRON_K_VNNI` ON next to `TRON_AMX_DISPATCH`. Every other preset leaves it OFF. README.ci.md says so in its `TRON_K_VNNI` paragraph: the layout does not depend on AMX, only the reader does.

Tests change as follows:

- `t_k_vnni_layout`, the test of the packed layout, gains five cases.
  - "row-major tail block converts to the VNNI layout and back, bit for bit": for each of the 4 blocks, 16 random rows are stored with `store_row` into a poisoned reference plane and with `store_row_major` into a second poisoned plane; `block_to_vnni` must make the planes bit-identical, `block_to_rows` must give back every row, and the other blocks must still hold the poison after both conversions. A section checks that the 64 `row_major_row` rows are 64-byte aligned, distinct and inside their block's panels. The case works on an owner, so it runs whatever the option is.
  - "page K blocks turn VNNI at the 16th saved row and back when a row is forgotten": rows 0 to 20 are saved and recorded as `save_k` and the forward end do; block 0 converts at row 15 and block 1 stays row-major; every row stays readable through `get_k_row` across the transitions, and the raw plane holds the VNNI columns of block 0 and the row-major rows of block 1. Then a new token at offset 3 converts block 0 back and keeps rows 0 to 2; saving rows 3 to 20 again converts it again; a row saved again into the converted block keeps it VNNI; a new token at offset 18 keeps block 0 and drops block 1's rows above 17; a new token at offset 16 drops block 1's bits only; a new token at offset 3 with blocks 0 and 1 converted converts block 0 back and leaves block 1's bytes untouched. With the option off, the page-state branch records nothing and the checks expect no VNNI block.
  - "the EAGLE storage view keeps its own K layout state": 16 rows saved and converted in the primary view, 16 other rows saved and converted under the EAGLE view, each view reads its own rows and sees its own state, and a forgotten offset converts both back.
  - "forgetting a row acts on every slot's own block": two slots, converted in one of them only; a forgotten offset drops the bits of both and converts the converted one back.
  - "page append carries the K layout state with the rows": a token-by-token append into a partly filled page (the destination's blocks are VNNI exactly where 16 rows are saved after the copy), an append into a converted destination block (converted back for the copy, kept rows on both sides, converted again), and a whole-page append of a fully VNNI page.
- `t_llama_unit`, the model and cache unit-test binary:
  - The apply-and-join case ("apply and join page ranges") gives the VNNI build the K instance of the row-major build: the raw bytes that `fill_random` wrote, read as consecutive 128-value rows, stored through `set_k_row`, then recorded as `save_k` and the forward end would: page 0 whole (4 VNNI blocks, the dense AMX shape) and every later page up to row 40 (blocks 0 and 1 VNNI, block 2 a row-major tail of 9 rows, block 3 row-major and unrecorded). The reference reads the rows through `get_k_row`, so the mixed pages are scored against the same values as the row-major build.
  - The `save_k` case gains two sections. "hardware attention scores the operation: the completed block stays row-major, the whole-block save is still VNNI" marks the saving operation as hardware-scored: after the pass and after the forward-end conversion, page 0 holds block 3 (the whole-block save) and no other block in the VNNI layout. "hardware attention scores another operation: this one still converts" marks another operation's id (operation 1, which is not layer 0 and not KV slot 0): the saving operation still converts block 0. Every section of the case now marks rows 0 to 4 and row 8 of page 0 as saved before the pass, so the pass's run of rows 5 to 15 completes block 0 through `save_k`; it checks the completion marks, and page 0's converted blocks before the conversion (block 3 only) and after it (blocks 0 and 3), and that pages 1 and 2 have none. The three-thread section runs those checks after each of its two windows.
- `t_amx_dispatch_dtype`, the dispatch probe, records the stored rows as `save_k` and the forward end do, so a full page's blocks hold the VNNI layout under the option. A new section stores a full page without recording its rows: the dispatch must pack the query and call no kernel, because the blocks are row-major.
- The masked partial-block path of the block-save PR is gone from `save_k`. `store_block`'s masked branch is reachable from the block-save test only.

## Measurements

The measurements have three parts. The runtron cells compare decode TPS and TTFT of this PR's binary against the block-save PR's binary and against `main`, under CPU attention and under FPGA attention. The whole-machine campaign compares the released package built from this PR against the package built from `main` for three nightly configurations. The token-identity runs compare the generated tokens of five arms.

### Runtron cells

Configurations:

- `base`: `main` at `72308ec90c`, built as runtron with row-major K and AMX dispatch on.
- `new`: this branch at `{{HEAD_SHORT}}`, with the option and AMX dispatch on.
- `head`: the block-save PR at `{{PR3_SHORT}}`, built the same way as `new`.
- `newoff` and `headoff`: those two binaries with the kill switch.

The experiment ran on {{E_DATE}}:

- Model: qwen3-4b, at tp2 and at tp4.
- Load: 8 users and 256 generated tokens.
- CPU cells: CPU attention, selected by `USE_HW_ATTN=0`; tp2 with prompt lengths 1,024 and 8,192 tokens, and tp4 with prompt length 1,024 tokens; all five arms.
- FPGA cells: FPGA attention, `USE_HW_ATTN` unset as in the released package; tp2 and tp4 with prompt length 1,024 tokens; the arms `base`, `new` and `head`.
- Repetitions: 3, with the binaries run in alternating order.
- Allocation: the whole Granite Rapids test machine with production serving stopped (the tp4 cells need their four FPGA cards and 256 huge pages, the large memory pages reserved for the run's buffers; the FPGA cells need their cards).

The decision band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. Bands are shown rounded to 0.01 TPS and 0.01 s. A difference beyond that band counts as a change. Paired t uses the 3 repetitions. "Inside" and "beyond" refer to the band.

Each parenthesized value is the sample standard deviation over the 3 repetitions. TPS has units of tokens/s/user. Both TTFT and its standard deviation have units of seconds. The FPGA table's last column is the mean count per run of the "lose HW attention" warning (a shard that got no card memory and was scored on the CPU instead); 0 means every shard ran on the cards.

CPU attention:

| Cell | Binary | TPS (tokens/s/user) | TTFT (s) |
|---|---|---|---|
{{ARM_ROWS_CPU}}

| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
{{PAIR_ROWS_CPU}}

FPGA attention:

| Cell | Binary | TPS (tokens/s/user) | TTFT (s) | HW-attention losses per run |
|---|---|---|---|---|
{{ARM_ROWS_FPGA}}

| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
{{PAIR_ROWS_FPGA}}

### The FPGA-attention decode of qwen3-4b (new vs base, head vs base, new vs head)

This is the claim of issue #4500. Under FPGA attention the layout without the tail block stores and stages 64 lines per generated token where `main` stores and stages 4. The records cited in Background measured that loss at -2.2 % (tp2) and -9.7 % (tp4) with runtron and at -5.0 % and -11.0 % with the nightly's own layout. The expectation here: `head` against `base` shows a loss of that order at both parallelisms. `new` against `base` is inside the band or within a few percent. `new` against `head` is the recovery. The tp4 cell has a large spread in every record of this layout, so a tp4 difference inside the band is not read as a change, and the standard deviations are reported. No earlier record runs this PR's content at 8 users on one engine under FPGA attention: the measured pairs decide.

{{FPGA_PAIRS}}

The claim holds in both cells. `head` loses 1.9 % of decode TPS against `base` at tp2 and 11.0 % at tp4, beyond the bands. `new` is inside the band against `base` in both cells: +0.6 % at tp2 and -0.3 % at tp4. `new` against `head` is the recovery: +2.5 % at tp2 and +12.1 % at tp4, beyond the bands. TTFT is inside the 0.15 s band in every FPGA pair. No run lost hardware attention.

The tp4 loss of `head`, 11.0 %, repeats the 9.7 % of the runtron record and the 11.0 % of the nightly-layout record within 1.3 percentage points. The tp2 loss, 1.9 %, is within 0.3 percentage points of the runtron record's 2.2 %.

### The CPU cells against the block-save PR (new vs head)

A 1,024-token prompt fills whole blocks, so prefill takes the block save as in the block-save PR and no block waits for the forward end. TTFT is expected inside the band. In decode a run of one token now stores 4 whole lines into the row-major tail block instead of 64 scattered dwords. The block whose 16th row a pass saves is converted at the forward end: one 4 KiB copy per block, KV head and layer, once per 16 steps per user, on the main thread. The page being filled takes the software loop (the reader for its converted blocks, the dotters for the tail) instead of the AMX kernel until all its blocks are converted. The expectation is TPS inside the band at tp2. The tp4 cell is reported with its spread.

{{TPS_HEAD}}
{{TTFT_HEAD}}

Decode TPS is inside the band in all three cells. This meets the expectation. The largest difference is -0.7 % at tp2 prompt length 1,024 tokens, paired t -2.4, inside the 0.66 TPS band. TTFT is inside the band in all three cells. At tp2 prompt length 8,192 tokens the difference is +231 ms, inside the 0.30 s band. The prefill of that cell takes about 52 s, and 231 ms is 0.4 % of it.

So the tail block, the forward-end conversion and the software loop on the page being filled cost nothing beyond the bands with AMX on in these cells. The AMX-off pair below measures the same code without the AMX kernel.

### This PR against `main` (new vs base)

The block-save PR measured, against the same `main`, TPS +5.1 %, +9.1 % and +3.4 % and TTFT -57 ms, -827 ms and -75 ms at tp2 prompt length 1,024 tokens, tp2 prompt length 8,192 tokens and tp4 prompt length 1,024 tokens. [PR #4898, Measurements] The expectation is the same within the bands.

{{AGAINST_MAIN}}

`new` is above `main` in decode TPS in all three cells, beyond the bands. TTFT is below `main` in all three cells: inside the 0.15 s band at the two 1,024-token cells, and beyond the 0.30 s band at 8,192 tokens, where the prefill is 697 ms (1.3 %) shorter.

The block-save PR's TPS gains repeat within 0.4 percentage points at tp2: +4.7 % and +9.4 % here against +5.1 % and +9.1 % in its run. The tp4 cell is 1.0 percentage point lower here, +2.4 % against +3.4 %. That cell has the largest spread of the three: `base` sd 0.49 TPS and `new` sd 0.39 TPS. The session control below moves the block-save PR's own binary by 0.5 percentage points in the same cell between the two sessions. The TTFT gains repeat within 130 ms: -56 ms, -697 ms and -73 ms here against -57 ms, -827 ms and -75 ms.

### The kill switch inside this PR (newoff vs new)

The store is the same with or without the switch. The scoring paths differ from the block-save PR's: with the switch, the reader scores the converted blocks and the dotter scores the row-major tail rows. Without it, the AMX kernel reads a page only when all its blocks are converted. The block-save PR measured, for its own binary, TPS -11.1 %, -18.0 % and -7.9 % and TTFT +768 ms, +65.7 s and +268 ms in the three CPU cells. [PR #4898, Measurements] That is a provisional expectation. The measured pair decides.

{{KILL_SWITCH}}

The three cells show the AMX page path's gain, as in the block-save PR. TPS is -13.6 %, -20.6 % and -9.3 % and TTFT is +780 ms, +66.0 s and +275 ms under the switch, beyond the bands. The TTFT values repeat the block-save PR's +768 ms, +65.7 s and +268 ms within 0.3 s. The TPS gaps are 2.5, 2.6 and 1.4 percentage points wider than that PR's -11.1 %, -18.0 % and -7.9 %.

The wider gaps are the AMX-off arm's loss of the next pair, not a gain of the AMX-on arm: `new` is inside the band against `head` above.

### The two AMX-off arms (newoff vs headoff)

Both arms disable AMX. `headoff` scores every relevant token of a packed slot through the reader: the block-save PR has no row-major tail path. `newoff` scores a converted block through the reader and an unconverted block through the dotter. So this pair measures the storage, the conversion and the scoring of unconverted blocks together. It does not isolate the store. The expectation is inside the band for TPS and TTFT. A difference beyond the band needs the Save K span, the `convert_k_blocks` span and the attention spans of a Perfetto trace (tron's timing trace) of the same decode workload for both arms.

{{AMX_OFF}}

TPS is beyond the band in all three cells. `newoff` is 3.4 %, 2.9 % and 2.0 % below `headoff`, with paired t -12.4, -45.2 and -4.4. This does not meet the expectation. TTFT is inside the 0.15 s band at the two 1,024-token cells. At 8,192 tokens TTFT is +453 ms, beyond the 0.21 s band. The prefill of that cell takes about 117 s under the switch, and 453 ms is 0.4 % of it.

The cause is not measured. The Perfetto trace named above was not taken. Hypothesis, labelled: the software loop of `self_attention.hpp` builds the array of `operation_kv_mul` dotters for every page and KV head it visits of a VNNI slot, before it knows whether the slot holds a row-major block. The generic dotter converts its 128-value query row to fp32 at construction. The block-save PR's loop built no dotter for a VNNI slot. With the switch, every page of every layer takes that loop. A second hypothesis, labelled: the per-token tests of the block bit and of the row-major branch inside the loop.

The measurement that would decide: the same three cells with a variant that builds the dotters of a VNNI slot at its first row-major row only, with the switch (against `newoff` and `headoff`) and with AMX on (against `new` and `head`). That variant is prepared and not measured at the time of writing. [Open items]

### The block-save PR against `main` in this session (head vs base)

This pair repeats the block-save PR's claim in the same session as the other pairs: TPS +5.1 %, +9.1 % and +3.4 % and TTFT -57 ms, -827 ms and -75 ms on 2026-10-12. [PR #4898, Measurements] A deviation beyond the bands would say that the machine's speed changed between the two sessions. Such a change would limit what every other pair of this run can show.

{{HEAD_BASE}}

The block-save PR's TPS claim repeats within 0.5 percentage points: +5.4 %, +9.2 % and +2.9 % here against +5.1 %, +9.1 % and +3.4 % in its own run. Its TTFT claim repeats within 101 ms: -65 ms, -928 ms and -78 ms here against -57 ms, -827 ms and -75 ms. Each of those differences is inside the band of its cell. So no machine-speed change between the two sessions limits the other pairs of this run.

### The whole-machine campaign (base deb vs target deb)

The campaign re-runs the nightly's perf code by hand on the whole Granite Rapids test machine, with the packages installed through the machine's package manager and the engines started by platformd, as the nightly does.

- Packages: the base deb (`main` at `72308ec90c`, version `{{W_BASE_VERSION}}`) and the target deb (this branch at `{{HEAD_SHORT}}`, version `{{W_TARGET_VERSION}}`). Both were built on the test machine with the `make deb` recipe of the repository.
- Configurations: three of the nightly's 14, chosen for this PR: llama-3.1-8b at tp2 with 8 users and prompt length 1,024 tokens, llama-3.1-8b at tp2 with 32 users and prompt length 4,096 tokens, and gpt-oss-120b at tp4 with 8 users and prompt length 1,024 tokens. FPGA attention as shipped. The llama-3.1-8b rows test that this PR keeps the decode and prefill gains of PR #4424; the gpt-oss-120b row tests parity.
- Passes: base, target, target, base ({{W_PASSES}}), 10 rounds of one request per user each. TPS is captured over generated tokens 896 to 1024. The paired t pools the rounds of both pass pairs.
- Dates: {{W_DATES}}.
- Memory: VmHWM and VmRSS of every rinzler process, summed over the engines, read after every provisioning and every benchmark.

A cell is resolved when its target differs from its base beyond noise: the paired t is at least 2.26 in magnitude and the difference is at least 1 % (for TTFT also at least 1 ms). TPS has units of tokens/s/user; TTFT is in ms; memory is in MiB.

| Cell | Base TPS (sd over passes) | Target TPS | Delta | Paired t (rounds) | Resolved | Base TTFT | Target TTFT | Delta | TTFT resolved | Base VmHWM | Target VmHWM | Delta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
{{W_ROWS}}

{{W_TEXT}}

{{W_MEM_TEXT}}

### Token identity

Setup ({{SMOKE_DATE}}):

- runtron with qwen3-4b, tp2, and 1 user.
- Temperature setting 0, `--pay-for-determinism`, random seed identifier 1, and 256 generated tokens.
- CPU attention at prompt lengths 1,024 and 8,192 tokens.
- FPGA attention at prompt length 1,024 tokens.
- Binaries: `new`, `new2` (the A/A repeat), `newoff`, `head`, and `base`.

Acceptance rules:

- Every binary exits with status 0 (success) and produces exactly 256 generated tokens.
- `new2` must match `new` for all 256 generated tokens in each cell.
- CPU attention: `new` must match `base` for all 256 generated tokens. This is the correctness claim of the PR for the measured cells: the dotter scores the blocks a decode step completes until the forward end converts them, a converted block holds the same values, and the generated tokens therefore equal `main`'s. The claim is for the measured cells: a converted block of a partial page is scored by the reader, whose fp32 add order differs from the dotter's.
- FPGA attention: `new` must match `head` for all 256 generated tokens. The tail block changes no FPGA-scored token.
- `newoff` against `new` is expected identical in every cell. The block-save PR and the kernel PR measured a first difference at generated token 247 at CPU prompt length 1,024 tokens for their binaries (an exact tie of the two best tokens, decided by the AMX-versus-reader numerics). With the tail block the scored sequence of that cell changes, so the tie is not expected to recur.

| Cell | new vs new2 | new vs base | new vs head | newoff vs new | head vs base |
|---|---|---|---|---|---|
{{SMOKE_ROWS}}

Outcome of the acceptance rules:

{{IDENTITY_TEXT}}

## Verification

Build provenance:

- Machine and date: Granite Rapids, Intel Xeon 6962P with AMX, {{BUILD_DATE}}.
- Revision: `{{HEAD_SHORT}}`, three commits on the block-save PR at `{{PR3_SHORT}}`. The head of this PR, `{{PUSHED_SHORT}}`, adds one commit to it: the cost rows of `config/test-benchmarks.json` measured below, a measurement record and no source. The measurements and the checks below are at `{{HEAD_SHORT}}`. The block-save PR is based on the kernel PR at `0ee8671d35`, the kernel PR on the layout PR at `82d05e94be`, and the layout PR includes `main` at `72308ec90c`.
- Environment: `nix develop`, the project's pinned build shell.
- Compiler: clang version 19.1.7.
- Preset: `native` (the Ninja build runner, the clang-19 compiler, the ccache compiler cache, the lld linker, build type `RelWithDebInfo`). The AVX-512 flags are explicit in `src/tron/CMakeLists.txt` and do not depend on the preset or on the build host.
- Build type: `RelWithDebInfo`, an optimized build with debug symbols.
- Each of the 3 configurations used a separate worktree.

`BUILD_INGEST_MODELS` controls compilation of the models produced by the ingest pipeline (the project's model conversion step).

| Configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | Targets | Build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | {{BUILD_PR4}} s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | {{BUILD_PR4ND}} s |
| option off | OFF | ON | OFF | the 6 tests below without `t_phase1_integration` | {{BUILD_PR4RM}} s |

`t_heterogeneous_scheduler` tests scheduling across different attention geometries. `t_k_vnni_layout` tests the packed layout, its row and block operations, the tail-block conversion, the page's layout state and the reader. `t_phase1_integration` tests staging (the copy of K and V into buffers read by the FPGA) and dispatch integration.

The following unit-test binaries passed with a fake device (a simulated FPGA). `--skip-benchmarks` excluded their benchmark sections. Each result gives assertions / test cases.

| Test | Option on | Option on, no AMX dispatch | Option off |
|---|---|---|---|
{{TEST_ROWS}}

`t_k_vnni_layout` reports 10 test cases in every build: the cases that work on an owner run whatever the option is, and the page-state cases take the row-major branch with the option off (no row is recorded and no block converts). The `save_k` case of `t_llama_unit` runs its four sections in every build; with the option off it runs the row-major store and the block checks are compiled out. The identity case of `t_amx_numerics` (the kernel PR's bit-identity check of the AMX kernel) ran on real AMX in the option-on build and in the option-off build. Neither `t_amx_numerics` run printed an "AMX unavailable" line. The option-on build without AMX dispatch compiles `t_amx_dispatch_dtype` as a placeholder; its two file-scope constants for the dispatch sections are then unused, and the compiler reports two `-Wunused-const-variable` warnings. The build has no `-Werror`, and the constants are kept as they are in the reviewed tree.

Kill-switch results in the option-on build:

{{KILLSWITCH_LINES}}

Two mutation checks ran in the option-on worktree.

- The page state: the completion test of `note_k_row_saved` in `kv_cache.hpp` was inverted (`==` to `!=` in the comparison of the block's 16 row bits). Every row of an incomplete block then reports "complete" and the 16th row reports "not complete", so no block is converted through the row path. The page-state case of `t_k_vnni_layout`, run alone, then fails at its first `REQUIRE`. {{MUTATION1}} With the file restored, `t_k_vnni_layout` passes again with {{RESTORED1}}.
- The hardware-attention policy: the condition `if (!cached_operation_uses_hw(binding.operation))` of `save_k_impl` in `model.hpp` lost its negation. Rows are then recorded only for hardware-scored operations. The `save_k` case of `t_llama_unit`, run alone, then fails in `check_blocks` in each of its four leaf sections: the one-thread section, the other-operation section and the three-thread section expect blocks 0 and 3 converted and find block 3 only, and the hardware-scored section expects block 3 only and finds blocks 0 and 3. {{MUTATION2}} With the file restored, `t_llama_unit` passes again with {{RESTORED2}}.

The two Debian packages of the campaign were built on the test machine with `make deb` (outside nix, uv 0.9.5 and the ghcup toolchain on the path, 48 jobs on one socket):

{{DEB_LINES}}

The Haskell suite is not repeated: this PR changes no file under `ingest/`, so the code generator is untouched. The suite ran on the block-save PR's head on 2026-10-12 (1,363 tests passed, 0 failed). The generated-plugin check of the block-save PR was repeated on this PR's option-on build: for each of the 19 generated plugins, the `save_v` calls, the main-side `save_k` calls and the helper-side `save_k` calls are equal and positive, no `save_k` call has another argument tail, and `save_k_helper` does not occur. The check compares call forms and counts, not bytes. Its verdict line: {{PLUGIN_PASS}}

| Plugin | KV-writing operations | Main-side `save_k` calls | Helper-side `save_k` calls |
|---|---|---|---|
{{PLUGIN_ROWS}}

All of these checks pass at `{{HEAD_SHORT}}`:

- clang-format version 19.1.7, the source formatter, with `--dry-run --Werror` on all 10 changed C++ files.
- `git diff --check`, the whitespace check, against the block-save PR's head.
- A search for the prohibited `<cassert>` header in the diff.
- {{LINT_NOTES}}

Syntax-only compilation used clang version 19 with the product's compile flags. It covered 38 configurations with 0 errors. 36 configurations had 0 warnings; the two AMX-dispatch-off configurations of `t_amx_dispatch_dtype` reported the two unused-constant warnings named above.

- All 4 combinations of AMX dispatch on/off and the option on/off for 9 translation units: `t_llama_unit`, `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `heterogeneous_scheduler_compile` (heterogeneous scheduling compilation), `scheduler/full.cpp` (the full scheduler), `gof.cpp` (staging), `t_gof_dma` (staging DMA, direct memory access transfers), and `t_kv_oom_subcases` (out-of-memory cases).
- `kernels/amx_attn.cpp` (the AMX kernels) with dispatch on and the option on/off.

The compiler flag is `-fsyntax-only`.

Host test suite (`make build-test-host` and `make test-host` with a fake device, in the option-on worktree, on one socket of the test machine with production serving stopped):

{{HOST_LINES}}

The suite permits only the existing Python-environment exceptions: `t_proxy_lib`, a proxy-library test, may skip, and `t_proxy_llama31`, a Llama proxy test, may fail. Both lack the virtual environment `t/proxy/.venv`, the isolated Python dependency directory.

Cost rows: `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics t_amx_dispatch_dtype` ran on the whole test machine with serving stopped, in the option-on worktree, and rewrote the four rows of the `granite_rapids_6962p` block of `config/test-benchmarks.json`. The commit `{{PUSHED_SHORT}}` carries them.

{{BENCH_LINES}}

### CI coverage

The GCP Nix test build enables neither `TRON_AMX_DISPATCH` nor `TRON_K_VNNI`. [nix/cmake-tron-test-build.nix]

- In that configuration the tail-block cases that work on an owner still run. The page-state cases take the row-major branch: no row is recorded and no block converts. The `save_k` sections run the row-major store with the block checks compiled out. The dense gate is not compiled.
- The option-on paths run on the Granite Rapids test machine, as reported above, and in the legacy CMake lane, which compiles both options on. [.github/workflows/cmake-single-platform.yml]
- The `deb` preset now compiles the option into the released package. The required CI therefore tests a configuration that the package does not ship. The whole-machine campaign of this PR and the nightly after the merge test the shipped one.
- At review time, this PR is a draft without the `Run CI` label. GCP Nix skips its product test jobs (Build Tron, Test host, Test FPGA and Test ingest) on a draft without that label. Its lint and infrastructure checks (Lint, CI machinery contracts, CI machinery tests, Nix Toolchain Contracts, Fresh Cabal plan) passed in [run 38343432613](https://github.com/positron-ai/tron/actions/runs/38343432613) at `{{PUSHED_SHORT}}`. The separate Debian smoke check (`deb-smoke.yml`, a workflow that checks authenticated access to the Debian package repository and builds no tron binary) passed in [run 38343432617](https://github.com/positron-ai/tron/actions/runs/38343432617). The Slice tooling check (`slice.yml`) ran because the cost-row commit changes `config/test-benchmarks.json`. It tests the tooling with its own fixtures and does not read the row values. It passed in [run 38343432618](https://github.com/positron-ai/tron/actions/runs/38343432618).
- The author explicitly accepts this limitation for this PR. Issue #4865 tracks enabling both options in the required test build.

## Open items

**Decode-completed blocks under software attention for a hardware operation.**

- When the software scores a range although the operation is a hardware one (before the engagement point, a prompt shorter than 128 tokens, a shard without card memory, a raised engagement point), the blocks that decode completed stay row-major and the dotter scores them, where the conversion would have let the AMX kernel score a page of them. Every reader takes its layout from the block bit, and no stored token is missed.
- Both layouts hold the same K values. The fp32 add order of the dotter and of the reader differs, so a score can differ by that add order alone, and so can a generated token. [Note [Row-major blocks under hardware attention], h/tron/models/kv_cache.hpp]

**The forward-end conversion's serial cost.**

- Every block that a pass completes through short runs is converted on the main thread at the forward end: one 4 KiB read and write per block, KV head and layer, once per 16 decode steps per user.
- Not measured here. The measurement that would decide it: the `convert_k_blocks` span of a Perfetto trace of a decode workload.

**The storage-view (EAGLE) state is tested by the unit tests only.**

- The EAGLE case of `t_k_vnni_layout` and the copy semantics of the page are the evidence. No EAGLE model is run here.

**128-dimension heads with kv_mul other than 4 query heads.**

- The kernel serves kv_mul 4 only. Other groups retain the packed layout and use the reader for the converted blocks and the dotter for the tail rows. The store does not depend on kv_mul.
- Decode TPS of those groups under runtron is not measured at `{{HEAD_SHORT}}`. No AMD host is measured at this head either.

**The join watchdog and the worker cap.**

- The shared save of the block-save PR is unchanged here: the main thread aborts the process when a shared store's join has not completed 120 s after its first clock read, and a pass with more than 128 workers stores on the main thread alone.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]**

- With the option on, the kill switch gives an AMX-off run of the same binary: the reader scores the converted blocks and the dotter scores the tail rows. It does not reproduce the tokens of a clean binary, meaning a build with both options off, in general. In the measured cells this PR's tokens equal `main`'s under FPGA attention and at CPU prompt length 8,192 tokens, and equal the block-save PR's under CPU attention at prompt length 1,024 tokens, where both first differ from `main` at generated token 83. [Measurements, Token identity; Open items, Token identity]
- {{NEWOFF_NEW_V}}
- {{DIVERGENCE_V}}
- The rollback contract (the documented promise of what the kill switch restores) promises AMX off with the same AVX dotter and clean-binary numerical results. A packed binary with the switch runs the reader for its converted blocks. [Item 4 of Note [AMX attention dispatch], h/tron/kernels/amx_attn_iface.hpp]
- Issue #4444 records two choices:
  1. Accept the narrower rollback contract. Add "with `TRON_K_VNNI` off" to item 4.
  2. Keep a row-major binary as the deployment rollback artifact. Document that requirement.

**Token identity against `main` and against the block-save PR. Reviewers decide.**

- The expectation before the run: `new` equals `base` in the CPU cells and `head` in the FPGA cell. The measured pattern differs. At CPU prompt length 1,024 tokens `new` equals `head`, and both first differ from `base` at generated token 83 (token id 1499 against 258). At FPGA prompt length 1,024 tokens `new` equals `base`, and `head` first differs from both at token 83. At CPU prompt length 8,192 tokens every pair is identical over 256 tokens. The A/A repeat is identical in every cell. [Measurements, Token identity]
- Hypothesis, labelled: no defect. Dense pages are scored bit-identically in every arm (the identity case of `t_amx_numerics`: the VNNI AMX kernel equals the row-major AMX kernel), so only a partial page can differ. The block-save PR and this PR both score the converted blocks of a partial page with the reader, where `main` uses the dotter, and the two fp32 add orders differ. A near tie of the two best tokens decided by that order hits both PRs alike: the CPU cell. The block-save PR scores the row-major tail with the reader and this PR with the dotter, as `main` does. A tie decided there hits the block-save PR alone: the FPGA cell. Whether such a tie occurs within 256 tokens depends on the token stream of the cell.
- The measurement that would confirm or reject it: the forced-run probe of the kernel PR (every step's logits, with the arms force-fed the same token sequence) at token 83, for `new` against `base` in the CPU cell and for `head` against `new` in the FPGA cell. A near tie of the two best tokens, decided by the add order, confirms it. A large logit gap rejects it. Not run at `ea94e95a4e`. This item is under investigation at the time of posting: the probe is scheduled on the test machine, and this description is updated with its result.
- `newoff` against `new` first differs at generated token 247 in the CPU cell at prompt length 1,024 tokens, with the token ids of the block-save PR's and the kernel PR's records (624 against 13). The expectation that this tie would not recur assumed a changed token stream. The stream equals the block-save PR's in that cell, as the `new` against `head` row shows, so the kernel PR's exact tie recurs. [PR #4887, Measurements]
- The claim this PR makes for the measured cells is the measured statement: under FPGA attention this PR's generated tokens equal `main`'s where the block-save PR's differ. Under CPU attention they equal the block-save PR's at prompt length 1,024 tokens and `main`'s at 8,192 tokens.

**Decode TPS with AMX off, against the block-save PR. Reviewers decide.**

- `newoff` against `headoff` is -3.4 %, -2.9 % and -2.0 % TPS in the three CPU cells, beyond the bands, and +453 ms TTFT at prompt length 8,192 tokens, beyond the 0.21 s band. [Measurements, The two AMX-off arms] With AMX on, `new` against `head` is inside the band in the same cells.
- The hypotheses and the deciding measurement are stated under that pair. The variant that builds the dotters of a VNNI slot at its first row-major row only is prepared and not measured at `ea94e95a4e`. This item is under investigation at the time of posting: the measurement of that variant against `new`, `newoff`, `head` and `headoff` in the three CPU cells is scheduled on the test machine after the whole-machine campaign, and this description is updated with its result. If the variant recovers the difference, the change joins this PR as a further commit, the chain's checks and the three cells are re-run on the new head, and this body says so.
- The AMX-off path is the kill switch's path and the path of a host without AMX. The shipped package runs the AMX kernel on the Granite Rapids hosts.

**Benchmark binary mismatch, inherited from PR #3879. Reviewers decide.**

- The legacy CMake workflow's `build` job compiles runtron with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`. It transfers that binary to its `benchmark` job.
- After a failed transfer, the benchmark job builds runtron through `make`. That build sets neither option. It benchmarks row-major K without AMX kernels.
- PR #3879 introduced the mismatch for AMX dispatch. The layout PR added the layout option to the same configure line. This PR changes neither.
- The GCP Nix benchmark configuration is unchanged. Its binary has neither option enabled.

**CI coverage gap. [Issue #4865]**

- When the GCP Nix product tests run, their configuration runs the owner-level tail-block cases, the page-state cases on the row-major branch and the `save_k` case on the row-major store, and never compiles the dense gate. The `deb` preset ships the option. The build and test evidence of this PR is the Granite Rapids run reported under Verification and the whole-machine campaign under Measurements. [CI coverage above]

**The campaign's base package is built from the stack's `main`, not from the nightly's.**

- The base deb is `main` at `72308ec90c`, the `main` inside the layout PR, so that every comparison of the stack has the same base. The nightly's package of the day carries the commits `main` gained since then. What that package would have measured instead: Insufficient data. The resume form of the campaign with the nightly's package as its base would give it.

**PR #4424 stays open as the reference.**

- The stack is complete with this PR. PR #4424 remains open until its author closes it.

## The stack

PR #4424 uses branch `jhan-amx-vnniK` and adds 4,054 lines. Four dependent PRs replace it. Each is based on the preceding PR. The stack is complete with this PR. PR #4424 remains open as a reference until it is closed.

| Order | PR branch and base | What it adds | State |
|---|---|---|---|
| 1 | PR #4868, `jhan-vnnik-1-layout`, based on `main` | Packed K layout, owner and views, per-row store, reader, FPGA staging gather, the option disabled in presets, and tests | ready for review |
| 2 | PR #4887, `jhan-vnnik-2-amx`, based on PR #4868 | The AMX QK kernel `qk_vnni_128x4` and query packer `pack_q_rows_128x4`. A bit-identity test compares with the row-major kernel. | draft until PR #4868 merges |
| 3 | PR #4898, `jhan-vnnik-3-shared-save`, based on PR #4887 | Shared saves of 16-token blocks, transposed in registers and written as whole cache lines by the main thread and idle helper threads. This provides PR #4424's TTFT improvement. | draft until PR #4887 merges |
| 4 | this PR, `jhan-vnnik-4-tail-block`, based on PR #4898 | A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the packed layout when all 16 rows are saved. A row-major policy under hardware attention (FPGA attention) addresses issue #4500. The `deb` package-build preset enables the option in the released package. | draft until PR #4898 merges |

The option is on in the `deb` preset of this PR and off in every other preset. The intermediate states of the stack do not enter production through those presets.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
