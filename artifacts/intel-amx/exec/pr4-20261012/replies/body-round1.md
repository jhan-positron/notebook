## Short version

This pull request keeps short writes to the attention-key cache in contiguous rows until a complete block can be packed for faster reading.
The measured accelerator-assisted throughput differs from the main branch by less than the experiment’s threshold for a change.
Token mismatches, slower throughput with matrix acceleration disabled, and a pending package campaign remain open.

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
| row-major K, row-major tail block, row_major_row | Row-major K is the layout `main` uses: one contiguous row of values per token. A row-major tail block (this PR) is a 16-token block of a packed slot whose rows are stored row-major, one contiguous 256-byte row per token, inside the block's own 4 KiB, until conversion after all 16 rows are saved. Short writes for hardware-scored operations remain row-major. `row_major_row` is the typed view of one token's row in such a block: 4 lines, 64-byte aligned. |
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
| base, new, new2, newoff, head, headoff | `base` is `main` at commit `72308ec90c` (the `main` commit included in the layout PR), built as runtron with row-major K and AMX dispatch on. `new` is this branch at commit `ea94e95a4e`, built with the option and AMX dispatch on. `new2` is a second run of `new` (the A/A repeat). `head` is the block-save PR at commit `dfafd13dce`, built the same way as `new`. `newoff` and `headoff` run `new` and `head` with the kill switch. |
| base deb, target deb, restore deb | The base deb is the Debian package built from `main` at `72308ec90c` with the `deb` preset of that commit (AMX dispatch on, row-major K), version `2026.10.12-72308ec9-jhan-pr4ci-base`. The target deb is the package built from this branch at `ea94e95a4e` with the `deb` preset of this PR (both switches on), version `2026.10.12-ea94e95a-jhan-pr4ci-target`. The restore deb is whatever package was installed when the campaign started; it is reinstalled at the end. |
| greedy run, A/A repeat | A greedy run uses temperature 0, a setting that chooses the highest-scoring token. `--pay-for-determinism` performs sums in a fixed order. An A/A repeat runs the same configuration twice as a control. |
| arm, cell, band, standard deviation, paired t | An arm is one binary with its runtime settings. A cell is one model, parallelism, user count, prompt length and attention configuration. Standard deviation measures variation between repetitions. The band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. The paired t statistic expresses the mean paired difference relative to its uncertainty. It is dimensionless. |
| the nightly, the perf phase, the harness, rounds, resolved | The nightly is the nightly test job of the systems_test repository that installs the newest tron deb on the Granite Rapids test machine and runs its phases. Its perf phase runs 14 configurations (model, parallelism, users, prompt length) with 10 rounds of one request per user, TPS captured over generated tokens 896 to 1024. The harness is that repository's checkout at commit `14f0ce4`; the campaign below drives its own perf code by hand for the chosen configurations. A cell is resolved when its target differs from its base beyond noise: the paired t over the rounds of both pass pairs is at least 2.26 in magnitude (the campaign's stated threshold) and the difference is at least 1 % (for TTFT also at least 1 ms). An unresolved cell does not establish a difference under this rule. |
| VmHWM, VmRSS | Fields of `/proc/<pid>/status` read per rinzler process after every provisioning and every benchmark of the campaign: the peak resident set size and the current resident set size, in MiB. |
| CI, GCP Nix, legacy CMake lane | CI means continuous integration, the automated build and test system. GCP Nix is the default build-and-test workflow, `gcp-nix.yml`. Its C++ test build uses `nix/cmake-tron-test-build.nix`. The legacy CMake lane is `.github/workflows/cmake-single-platform.yml`. It runs by manual dispatch and from `publish-deb.yml`, the package-publishing workflow. |
| runner, Granite Rapids | A runner is a machine that executes CI jobs. Granite Rapids is the Intel CPU family of the Xeon 6962P test machine with AMX and 8 FPGA cards. The Granite Rapids machine below means that machine. |
| slice check, cost rows, bin/slice bench | `bin/slice bench --check` checks registered tests for timing records in `config/test-benchmarks.json`. These records are the cost rows: test durations at 1, 2 and 4 slices and the peak memory, per host. `bin/slice bench --update <tests>` measures the named tests at the three widths and rewrites their rows. The slice check is the CI job that runs when that file changes. |
| lint-notes, Note | lint-notes is the repository's check that every `Note [...]` reference names a defined Note (a named comment block whose title line is underlined with tildes). This PR adds two Notes. |
| worktree, translation unit | A worktree is a separate checkout used for one build. A translation unit is one source file after its included headers have been expanded. |

### Background

The previous packed layout writes one generated token's K row across 64 cache lines.
FPGA staging then gathers that row from those lines.
This PR stores a short run as contiguous rows inside the same block storage.
Each row occupies 4 cache lines, or 256 bytes.

Issue #4500 records the earlier FPGA-attention throughput loss for qwen3-4b, the Qwen3 model with 4 billion parameters.
The 2026-09-16 runtron comparison reported losses of 2.2 % at tp2 and 9.7 % at tp4.
The 2026-09-18 nightly-layout comparison reported losses of 5.0 % and 11.0 %, respectively.
Those historical runs are background evidence. The tables below use this PR's own binaries.

## The changes

- **Storage and conversion.** `h/tron/tensor/k_vnni.hpp` adds contiguous rows inside each 16-token block. `block_to_vnni` converts a complete block through a 64-byte-aligned temporary array. `block_to_rows` reverses the conversion. The conversion tests compare the complete plane with the existing per-token store.
- **Page state.** `h/tron/models/kv_cache.hpp` tracks saved rows and converted blocks separately for every storage slot. The EAGLE storage has its own entry. Row access follows the converted-block bit. A whole-block save publishes its bits after every KV head is written.
- **Page reuse and copies.** Forgetting an offset clears saved-row state at and above that offset. A converted block with retained rows is first returned to row-major form when its storage is readable. Page copies carry the state with the rows. Partial copies convert the destination blocks as needed.
- **Stable storage references.** `k_storage_ref` pairs physical storage with its state entry. The pending-conversion list captures that pair during the save. A later storage-view change cannot redirect the conversion.
- **Save and forward completion.** `h/tron/models/model.hpp` stores a full 16-token run directly in VNNI form. Shorter runs use row stores. For software-scored operations, a short run that completes a block queues its conversion. The forward path converts queued blocks after the plugin joins its workers and `wait_for_coop_gof` drains staging. Logit delivery follows the conversion.
- **Hardware-attention policy.** Short writes for an operation selected for hardware attention do not record saved-row bits or queue conversion. Those blocks stay row-major. Whole-block saves still write VNNI form. CPU fallback for a hardware operation follows the recorded layout.
- **Scoring.** `h/tron/models/self_attention.hpp` permits the dense AMX path only when every block of the page is VNNI. Otherwise, the reader scores converted blocks and the dotter scores row-major rows. The kernel comments describe this split.
- **Staging.** `h/tron/scheduler/full.hpp` returns row-major K rows directly to staging. Converted rows are gathered into caller-owned scratch. Staging copies either representation into the existing transfer buffers.
- **Packaging.** `CMakePresets.json` enables `TRON_K_VNNI` in the `deb` preset alongside `TRON_AMX_DISPATCH`. Other presets retain the default OFF setting. `README.ci.md` documents the choice.
- **Tests and timing records.** Existing test binaries cover conversion, page state, EAGLE storage, page append, mixed-layout scoring, the hardware-operation policy, and dense-path selection. `config/test-benchmarks.json` contains refreshed durations and memory records for four tests.

The partial-block masked save is removed from `save_k`.
`store_block` retains its mask parameter for the existing block-store test.
Its production callers pass the full mask.

## Measurements

### Revisions and setup

The runtron measurements were collected on 2026-10-12 on the Granite Rapids test machine.
The measured implementation is `ea94e95a4e`.
The published head, `e7d06a1267`, differs only in four benchmark-record rows.

- `base`: `main` at `72308ec90c`, with row-major K and AMX dispatch enabled.
- `new`: this PR at `ea94e95a4e`, with VNNI K and AMX dispatch enabled.
- `head`: the parent PR #4898 at `dfafd13dce`, with both options enabled.
- `newoff` and `headoff`: the corresponding binaries with `TRON_AMX_DISABLE=1`.

The throughput experiment uses qwen3-4b, 8 users, and 256 generated tokens.
Each cell has 3 repetitions in alternating binary order.
CPU attention uses `USE_HW_ATTN=0`. FPGA attention leaves that variable unset.
Production serving was stopped during these whole-machine runs.

The band is twice the larger sample standard deviation of the compared arms.
It has a minimum of 0.4 tokens/s/user for TPS and 0.15 s for TTFT.
A difference beyond the band counts as a change under this experiment's rule.
An inside-band result does not prove equivalence.
Parentheses in the arm tables give sample standard deviations.
TTFT is the maximum over the 8 users.

### CPU attention

| Cell | Binary | TPS (tokens/s/user) | TTFT (s) |
|---|---|---|---|
| tp2, 1,024 tokens | base | 80.98 (0.10) | 3.181 (0.004) |
| tp2, 1,024 tokens | new | 84.75 (0.12) | 3.125 (0.006) |
| tp2, 1,024 tokens | newoff | 73.19 (0.14) | 3.905 (0.007) |
| tp2, 1,024 tokens | head | 85.36 (0.33) | 3.116 (0.003) |
| tp2, 1,024 tokens | headoff | 75.80 (0.23) | 3.894 (0.003) |
| tp2, 8,192 tokens | base | 17.31 (0.02) | 52.549 (0.091) |
| tp2, 8,192 tokens | new | 18.95 (0.03) | 51.852 (0.148) |
| tp2, 8,192 tokens | newoff | 15.05 (0.07) | 117.812 (0.103) |
| tp2, 8,192 tokens | head | 18.90 (0.02) | 51.622 (0.141) |
| tp2, 8,192 tokens | headoff | 15.49 (0.06) | 117.359 (0.047) |
| tp4, 1,024 tokens | base | 117.36 (0.49) | 2.215 (0.004) |
| tp4, 1,024 tokens | new | 120.22 (0.39) | 2.142 (0.004) |
| tp4, 1,024 tokens | newoff | 109.03 (0.39) | 2.417 (0.009) |
| tp4, 1,024 tokens | head | 120.78 (0.77) | 2.137 (0.011) |
| tp4, 1,024 tokens | headoff | 111.27 (0.50) | 2.402 (0.003) |

| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
| tp2, 1,024 tokens | new vs base | +4.7 % (+3.77 TPS, t +65.8), beyond | -56 ms (-1.8 %, t -9.8), inside | 0.40 TPS / 0.15 s |
| tp2, 1,024 tokens | new vs head | -0.7 % (-0.61 TPS, t -2.4), inside | +9 ms (+0.3 %, t +1.9), inside | 0.66 TPS / 0.15 s |
| tp2, 1,024 tokens | newoff vs new | -13.6 % (-11.56 TPS, t -150.9), beyond | +780 ms (+24.9 %, t +109.8), beyond | 0.40 TPS / 0.15 s |
| tp2, 1,024 tokens | newoff vs headoff | -3.4 % (-2.61 TPS, t -12.4), beyond | +10 ms (+0.3 %, t +2.4), inside | 0.46 TPS / 0.15 s |
| tp2, 1,024 tokens | head vs base | +5.4 % (+4.38 TPS, t +21.3), beyond | -65 ms (-2.0 %, t -47.4), inside | 0.66 TPS / 0.15 s |
| tp2, 8,192 tokens | new vs base | +9.4 % (+1.63 TPS, t +76.5), beyond | -697 ms (-1.3 %, t -5.1), beyond | 0.40 TPS / 0.30 s |
| tp2, 8,192 tokens | new vs head | +0.2 % (+0.04 TPS, t +1.5), inside | +231 ms (+0.4 %, t +1.4), inside | 0.40 TPS / 0.30 s |
| tp2, 8,192 tokens | newoff vs new | -20.6 % (-3.90 TPS, t -69.7), beyond | +66.0 s (+127.2 %, t +600.1), beyond | 0.40 TPS / 0.30 s |
| tp2, 8,192 tokens | newoff vs headoff | -2.9 % (-0.45 TPS, t -45.2), beyond | +453 ms (+0.4 %, t +8.9), beyond | 0.40 TPS / 0.21 s |
| tp2, 8,192 tokens | head vs base | +9.2 % (+1.59 TPS, t +122.2), beyond | -928 ms (-1.8 %, t -20.5), beyond | 0.40 TPS / 0.28 s |
| tp4, 1,024 tokens | new vs base | +2.4 % (+2.86 TPS, t +6.2), beyond | -73 ms (-3.3 %, t -85.4), inside | 0.98 TPS / 0.15 s |
| tp4, 1,024 tokens | new vs head | -0.5 % (-0.56 TPS, t -0.9), inside | +5 ms (+0.2 %, t +1.4), inside | 1.54 TPS / 0.15 s |
| tp4, 1,024 tokens | newoff vs new | -9.3 % (-11.18 TPS, t -28.2), beyond | +275 ms (+12.8 %, t +72.5), beyond | 0.78 TPS / 0.15 s |
| tp4, 1,024 tokens | newoff vs headoff | -2.0 % (-2.24 TPS, t -4.4), beyond | +15 ms (+0.6 %, t +2.5), inside | 1.00 TPS / 0.15 s |
| tp4, 1,024 tokens | head vs base | +2.9 % (+3.42 TPS, t +7.9), beyond | -78 ms (-3.5 %, t -17.5), inside | 1.54 TPS / 0.15 s |

The cells are ordered as tp2 with 1,024 prompt tokens, tp2 with 8,192 prompt tokens, and tp4 with 1,024 prompt tokens.

- **This PR versus its parent, AMX enabled:** TPS and TTFT are inside their bands in all three cells. The largest TPS difference is -0.7 %. The 8,192-token TTFT difference is +231 ms, within its 0.30 s band.
- **This PR versus main:** TPS increases by 4.7 %, 9.4 %, and 2.4 %. Each increase is beyond its band. TTFT decreases by 56 ms, 697 ms, and 73 ms. Only the 8,192-token TTFT decrease is beyond its band.
- **AMX disabled versus enabled in this PR:** TPS changes by -13.6 %, -20.6 %, and -9.3 %. TTFT increases by 780 ms, 66.0 s, and 275 ms. These differences are beyond their bands.
- **Both binaries with AMX disabled:** This PR is 3.4 %, 2.9 %, and 2.0 % slower than its parent in TPS. Each difference is beyond its band. TTFT increases by 453 ms at 8,192 prompt tokens, beyond its 0.21 s band. The shorter-prompt TTFT differences are inside their bands.
- **Parent versus main in this session:** TPS gains are 5.4 %, 9.2 %, and 2.9 %. TTFT decreases by 65 ms, 928 ms, and 78 ms. These results are consistent with the parent's earlier report within the stated bands. They do not exclude every possible change in machine performance.

The AMX-disabled comparison changes storage, conversion, and scoring together.
It does not isolate the cost of any one operation.
The cause of the slowdown is unmeasured.
Perfetto records timed operations as spans.
The relevant spans are `Save K`, `convert_k_blocks`, and the attention spans.

One hypothesis is unnecessary dotter construction for fully converted pages.
The changed software loop constructs dotters before it knows whether any row needs them.
For the measured `bf16`, 128-value path, the specialized dotter loads four vectors.
It does not convert the query to fp32 at construction. [dotter implementation](https://github.com/positron-ai/tron/blob/e7d06a126766272f73483ef886c77d37c807a5ff/h/tron/kernels/dotter.hpp#L174)
Another hypothesis is the added per-token layout branching.
Neither hypothesis establishes the measured cause.
The planned comparison uses a variant that constructs dotters only at the first row-major row.
That comparison is pending.

### FPGA attention

| Cell | Binary | TPS (tokens/s/user) | TTFT (s) | HW-attention losses per run |
|---|---|---|---|---|
| tp2, 1,024 tokens | base | 132.07 (0.24) | 3.192 (0.021) | 0.0 |
| tp2, 1,024 tokens | new | 132.84 (0.48) | 3.171 (0.012) | 0.0 |
| tp2, 1,024 tokens | head | 129.60 (0.10) | 3.157 (0.011) | 0.0 |
| tp4, 1,024 tokens | base | 163.49 (1.06) | 2.232 (0.002) | 0.0 |
| tp4, 1,024 tokens | new | 163.07 (0.83) | 2.192 (0.010) | 0.0 |
| tp4, 1,024 tokens | head | 145.44 (0.48) | 2.170 (0.013) | 0.0 |

| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
| tp2, 1,024 tokens | new vs base | +0.6 % (+0.77 TPS, t +2.3), inside | -21 ms (-0.6 %, t -1.1), inside | 0.96 TPS / 0.15 s |
| tp2, 1,024 tokens | new vs head | +2.5 % (+3.24 TPS, t +12.1), beyond | +14 ms (+0.5 %, t +1.1), inside | 0.96 TPS / 0.15 s |
| tp2, 1,024 tokens | head vs base | -1.9 % (-2.47 TPS, t -26.1), beyond | -35 ms (-1.1 %, t -5.6), inside | 0.48 TPS / 0.15 s |
| tp4, 1,024 tokens | new vs base | -0.3 % (-0.42 TPS, t -0.6), inside | -40 ms (-1.8 %, t -8.5), inside | 2.12 TPS / 0.15 s |
| tp4, 1,024 tokens | new vs head | +12.1 % (+17.63 TPS, t +24.4), beyond | +22 ms (+1.0 %, t +1.6), inside | 1.66 TPS / 0.15 s |
| tp4, 1,024 tokens | head vs base | -11.0 % (-18.05 TPS, t -33.2), beyond | -62 ms (-2.8 %, t -7.2), inside | 2.12 TPS / 0.15 s |

This PR differs from main by +0.6 % TPS at tp2 and -0.3 % at tp4.
Both results are inside their bands.
The parent loses 1.9 % and 11.0 % against main, beyond the bands.
This PR improves on the parent by 2.5 % and 12.1 %, beyond the bands.
These cells support recovery of the issue #4500 loss under the measured conditions.
Every FPGA-attention TTFT comparison is inside the 0.15 s band.
No run reported a loss of hardware attention.

### Whole-machine package campaign — pending

The campaign compares the base and target Debian packages through the nightly's performance harness.
The packages are installed through the package manager.
The service manager starts the serving engines.

- **Question:** Does the target retain the earlier package gains for Llama and maintain parity for GPT-OSS?
- **Comparator:** Base package `2026.10.12-72308ec9-jhan-pr4ci-base` against target package `2026.10.12-ea94e95a-jhan-pr4ci-target`.
- **Cells:** llama-3.1-8b at tp2 with 8 users and 1,024 prompt tokens, llama-3.1-8b at tp2 with 32 users and 4,096 prompt tokens, and gpt-oss-120b at tp4 with 8 users and 1,024 prompt tokens. All use FPGA attention.
- **Order:** Base, target, target, base. Each pass contains 10 rounds. TPS is sampled over generated tokens 896 through 1024.
- **Decision rule:** The absolute paired t must be at least 2.26 and the absolute difference at least 1 %. A TTFT difference must also reach 1 ms. The campaign pools both pass pairs under its stated rule.
- **Memory:** Record VmHWM and VmRSS after provisioning and after each benchmark. Sum the serving processes across engines.
- **Status:** Scheduled after the nightly CI of 2026-10-13, no earlier than 13:00 UTC. Results are not available in this description.

The base package uses the main commit included in this stack.
It does not use the latest nightly package.
Insufficient data: comparison with that nightly requires a separate campaign using it as the base.

### Token identity

The token comparison uses qwen3-4b at tp2 with 1 user.
Each run uses temperature 0, `--pay-for-determinism`, seed identifier 1, and 256 generated tokens.
`new2` repeats `new` as a control.
The run date is 2026-10-12.

| Cell | new vs new2 | new vs base | new vs head | newoff vs new | head vs base |
|---|---|---|---|---|---|
| CPU attention, prompt length 1024 tokens | identical, 256 of 256 tokens | first difference at generated token 83 | identical, 256 of 256 tokens | first difference at generated token 247 | first difference at generated token 83 |
| CPU attention, prompt length 8192 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens |
| FPGA attention, prompt length 1024 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | first difference at generated token 83 | identical, 256 of 256 tokens | first difference at generated token 83 |

Every binary exited successfully and produced 256 tokens in each cell.
The repeated `new` runs matched in all cells.

Three pre-run expectations did not hold:

- **CPU, 1,024 prompt tokens:** `new` and `head` match each other. Both first differ from `base` at generated token 83. Their token identifier is 1499, versus 258 for `base`.
- **FPGA, 1,024 prompt tokens:** `new` matches `base`. `head` first differs from both at generated token 83. The token identifier is 258 for `head`, versus 1499 for `new` and `base`.
- **Kill switch, CPU, 1,024 prompt tokens:** `newoff` first differs from `new` at generated token 247. The token identifiers are 624 and 13, respectively.

The 8,192-token CPU cell matches across all reported pairs.
These results do not establish general token identity with main or with the parent.

Different floating-point addition orders are a possible explanation for the mismatches.
Insufficient data: the current head needs a forced-token comparison of logits at token 83 and, for the kill switch, token 247. That probe is scheduled on the test machine for 2026-10-13, after the package campaign and the dotter measurement, with this binary in every arm.
That experiment feeds the same token sequence to both binaries and records their output scores.
The earlier parent-PR probe found an exact tie at token 247.
Matching token identifiers here do not prove that the same tie occurred in this binary.
The current investigation remains pending.

## Verification

### Builds and focused tests

The implementation was built at `ea94e95a4e` on the Granite Rapids machine on 2026-10-12.
The environment was the pinned Nix development shell with clang 19.1.7.
The `native` preset used `RelWithDebInfo`, an optimized build with debug information.
Each configuration had a separate checkout.
`BUILD_INGEST_MODELS` controls compilation of generated model plugins.

| Configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | Targets | Build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | 817 s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | 321 s |
| option off | OFF | ON | OFF | the 6 tests below without `t_phase1_integration` | 286 s |

The test binaries use a fake device, a simulated FPGA.
The `--skip-benchmarks` argument excludes benchmark sections.
Each cell below gives the assertion count followed by the test-case count.

| Test | Option on | Option on, no AMX dispatch | Option off |
|---|---|---|---|
| `t_k_vnni_layout` | 1041241 / 10 | 1041241 / 10 | 1039161 / 10 |
| `t_amx_dispatch_dtype` | 2144 / 1 | 1 / 1 (placeholder without dispatch) | 2144 / 1 |
| `t_amx_numerics` | 6669 / 5 (AMX cases ran, no "AMX unavailable" line) | 1 / 1 (placeholder without dispatch) | 6669 / 5 (AMX cases ran) |
| `t_llama_unit` | 277775 / 66 | 277775 / 66 | 277486 / 66 |
| `t_heterogeneous_scheduler` | 2783 / 3 | 2783 / 3 | 2783 / 3 |
| `t_phase1_integration` | 6220 / 64 | 6220 / 64 | not built |

The owner-level conversion case runs with the layout option either enabled or disabled.
The page-state cases use the row-major branch when the option is disabled.
The saved-block assertions in `t_llama_unit` are compiled out in that configuration.
The no-dispatch builds of the AMX-specific tests contain placeholder cases.
They do not exercise AMX dispatch or arithmetic.

The AMX-enabled numerical runs reported no unavailable-hardware skip.
With `TRON_AMX_DISABLE=1`:

- `t_llama_unit` passed 277775 assertions in 66 cases.
- `t_amx_numerics` passed 4108 assertions in 5 cases. Its QK precision, QK identity, and PV precision checks reported AMX unavailable and skipped those checks.

### Mutation checks

- **Saved-row completion:** Reversing the completion comparison caused 1 assertion to fail in 1 case of `t_k_vnni_layout`. The captured token offset was 0. Restoring the source returned the full binary to 1041241 passing assertions in 10 cases.
- **Hardware-operation policy:** Reversing the hardware-policy condition caused 4 of 5115 assertions to fail in the `save_k` case of `t_llama_unit`. Each leaf section detected the wrong converted-block set. Restoring the source returned the full binary to 277775 passing assertions in 66 cases.

These mutations test the completion predicate and operation policy.
They do not test deletion or reordering of the production forward-end conversion call.

### Debian packages

Both packages were built with `make deb` outside Nix on one socket, using 48 build jobs.
The build environment included uv 0.9.5 and the ghcup Haskell toolchain manager.

- **Base:** `2026.10.12-72308ec9-jhan-pr4ci-base`, from `72308ec90c`, built in 915 s. AMX dispatch was enabled. The preset did not set the VNNI K option. Binary inspection found the kill-switch string once and 86 AMX tile instructions.
- **Target:** `2026.10.12-ea94e95a-jhan-pr4ci-target`, from `ea94e95a4e`, built in 953 s. Both options were enabled. Binary inspection found the kill-switch string once and 126 AMX tile instructions.

These build and inspection results do not replace the pending package campaign.

### Generated plugins

This PR changes no file under `ingest/`, the code-generator directory.
The Haskell suite was not repeated for this PR.
It passed 1,363 tests with 0 failures on the parent revision on 2026-10-12.

The generated-plugin check was repeated on this PR's option-on build.
All 19 plugins had equal, positive counts of KV-writing operations, main-side K saves, and helper-side K saves.
No unexpected K-save argument form or `save_k_helper` call was found.
This check compares call forms and counts. It does not establish byte-identical generated files.

| Plugin | KV-writing operations | Main-side `save_k` calls | Helper-side `save_k` calls |
|---|---|---|---|
| `gemma_4_12b_it_permuted.hpp` | 48 | 48 | 48 |
| `gemma_4_31b_it.hpp` | 60 | 60 | 60 |
| `gemma_4_a4b_it.hpp` | 30 | 30 | 30 |
| `gemma_4_e4b_it.hpp` | 24 | 24 | 24 |
| `gemma_4_e4b_it_permuted.hpp` | 24 | 24 | 24 |
| `ingested_chinese_alpaca_2_7b.hpp` | 32 | 32 | 32 |
| `ingested_gemma_3_27b_it.hpp` | 62 | 62 | 62 |
| `ingested_gemma_3_4b_it.hpp` | 34 | 34 | 34 |
| `ingested_gpt_oss_120b.hpp` | 36 | 36 | 36 |
| `ingested_gpt_oss_20b.hpp` | 24 | 24 | 24 |
| `ingested_granite_3p3_8b.hpp` | 40 | 40 | 40 |
| `ingested_llama_3p1_8b.hpp` | 32 | 32 | 32 |
| `ingested_llama_3p1_8b_permuted.hpp` | 32 | 32 | 32 |
| `ingested_meta_models_Muse_Glimmer_30B.hpp` | 52 | 52 | 52 |
| `ingested_meta_models_Muse_Glimmer_30B_permuted.hpp` | 52 | 52 | 52 |
| `ingested_mixtral_8x7b.hpp` | 32 | 32 | 32 |
| `ingested_phi_4.hpp` | 40 | 40 | 40 |
| `qwen_3_30b_moe.hpp` | 48 | 48 | 48 |
| `qwen_3_4b_instruct_2507.hpp` | 36 | 36 | 36 |

### Source checks and host suite

- clang-format 19.1.7 passed with `--dry-run --Werror` on all 10 changed C++ files.
- `git diff --check` passed against the parent revision.
- The diff contained no prohibited `<cassert>` include.
- `make lint-notes` passed. Both new named comments and their references resolved.
- Syntax-only compilation covered 38 configurations with 0 errors. The two no-dispatch configurations of `t_amx_dispatch_dtype` each reported two unused-constant warnings. The remaining 36 configurations had no warnings.

The syntax checks covered all four combinations of the layout and dispatch options for nine translation units.
Those units were the four layout/AMX/model test files, heterogeneous scheduling, the full scheduler, staging, staging-transfer tests, and cache out-of-memory tests.
The AMX kernel source was also checked with dispatch enabled and the layout option both enabled and disabled.

The host suite built every test target with the layout option enabled.
Its result was **93 tests passed, 1 skipped, and 1 failed** in 111.8 s.
The failed test was `t_proxy_llama31`, which reported a missing `t/proxy/.venv` Python environment.
The skipped test was `t_proxy_lib`. Its log reads `SKIP: t/proxy/.venv missing — run make proxy-test-deps`, the permitted Python-environment exception.
The suite's exit status was a failure. It is not reported as a clean pass.

### Benchmark records

The timing refresh ran on 2026-10-13 at implementation revision `ea94e95a4e`.
The command was `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics t_amx_dispatch_dtype`.
Serving was stopped on the whole test machine.
Commit `e7d06a1267` records the four updated rows for `granite_rapids_6962p`.

| Test | Old (1 / 2 / 4 slices, s) | New (1 / 2 / 4 slices, s) |
|---|---|---|
| `t_k_vnni_layout` | 0.9 / 0.907 / 0.91 | 0.903 / 0.896 / 0.898 |
| `t_llama_unit` | 28.081 / 28.287 / 28.294 | 5.623 / 5.598 / 5.763 |
| `t_amx_numerics` | 0.81 / 0.832 / 0.743 | 0.749 / 0.746 / 0.724 |
| `t_amx_dispatch_dtype` | 0.778 / 0.775 / 0.873 | 0.806 / 0.733 / 0.733 |

The shorter `t_llama_unit` duration is a measurement difference from the earlier record.
Its cause has not been established here.

### CI coverage

The GCP Nix workflow's C++ test configuration enables neither layout nor AMX dispatch.
Its product tests therefore do not cover the shipped combination of these options. [Nix test configuration](https://github.com/positron-ai/tron/blob/e7d06a126766272f73483ef886c77d37c807a5ff/nix/cmake-tron-test-build.nix)
The legacy **CMake and CTest** workflow configures both options ON. [CMake configuration](https://github.com/positron-ai/tron/blob/e7d06a126766272f73483ef886c77d37c807a5ff/.github/workflows/cmake-single-platform.yml#L355)
It runs by manual dispatch or through the package-publishing workflow's tag/feature-branch gate. [publishing trigger](https://github.com/positron-ai/tron/blob/e7d06a126766272f73483ef886c77d37c807a5ff/.github/workflows/publish-deb.yml#L55)
Issue #4865 tracks the missing default-workflow coverage.
The author accepts this documented limitation for the stack.

This draft has no `Run CI` label.
The GCP Nix product build, host tests, FPGA tests, ingest tests, and benchmarks were skipped.
The following checks passed at `e7d06a1267`:

- Lint, CI machinery contracts, CI machinery tests, Nix Toolchain Contracts, and Fresh Cabal plan. [GCP Nix run 38343432613](https://github.com/positron-ai/tron/actions/runs/38343432613)
- The Debian-repository smoke check. It checks repository access and builds no tron binary. [Run 38343432617](https://github.com/positron-ai/tron/actions/runs/38343432617)
- Slice tooling tests. The benchmark-record change triggered this workflow. The tests use their own fixtures rather than validating these measured row values. [Run 38343432618](https://github.com/positron-ai/tron/actions/runs/38343432618)

GitHub reported no required checks for this PR's current target branch when queried during review.
The passing draft checks are not evidence that the changed product paths ran in CI.

## Open items

- **Token mismatches:** The exact observations and pending forced-token probe are in Token identity. A numerical explanation remains a hypothesis.
- **AMX-disabled slowdown:** The three measured CPU cells lose 2.0 % to 3.4 % TPS against the parent. The deferred-dotter variant and timing trace remain pending. This path also serves hosts without AMX.
- **Package campaign:** The three selected nightly configurations remain pending. The package build alone does not establish serving performance.
- **Hardware-operation fallback:** Before hardware engagement, after card-memory exhaustion, or under a raised engagement threshold, software may score rows from a hardware-designated operation. Blocks completed by short writes remain row-major in those cases. Their scores can differ from packed-reader scores through addition order.
- **Conversion cost:** The main thread converts completed blocks after each pass. Each conversion reads and writes 4 KiB of plane data per block and KV head, with temporary-stack traffic as well. Insufficient data: a `convert_k_blocks` trace is needed to measure its serial cost.
- **Forward-path coverage:** The new conversion assertions call helpers directly. A test through the real forward path is still needed to protect the conversion call and its ordering after staging.
- **EAGLE:** Unit tests cover its storage-view state. No EAGLE model run is reported here.
- **Other shapes and hosts:** There is no throughput measurement at this revision for 128-dimension heads with a query-head ratio other than 4, or for an AMD host.
- **Shared-save limits:** The inherited helper join has a 120 s watchdog. A pass with more than 128 workers stores on the main thread alone.
- **Rollback contract, issue #4444:** The kill switch disables AMX but keeps packed storage and its reader. It does not generally reproduce a build with both options disabled. The open choices are to narrow the documented numerical promise or retain a row-major binary as the deployment rollback artifact.
- **Inherited benchmark fallback:** The legacy workflow initially builds with both options enabled. If transfer to the benchmark job fails, its `make` fallback enables neither option. This PR does not change that fallback.
- **Default CI and nightly comparator:** Issue #4865 tracks option-on coverage. The pending package campaign uses the stack's main revision rather than the latest nightly package.
- **Reference PR:** PR #4424 remains open until its author closes it.

## The stack

This is the fourth and final dependent PR replacing PR #4424.
Each PR targets its predecessor.
Only the first PR is ready for review.

| Order | PR branch and base | What it adds | State |
|---|---|---|---|
| 1 | PR #4868, `jhan-vnnik-1-layout`, based on `main` | Packed K layout, owner and views, per-row store, reader, FPGA staging gather, the option disabled in presets, and tests | ready for review |
| 2 | PR #4887, `jhan-vnnik-2-amx`, based on PR #4868 | The AMX QK kernel `qk_vnni_128x4` and query packer `pack_q_rows_128x4`. A bit-identity test compares with the row-major kernel. | draft until PR #4868 merges |
| 3 | PR #4898, `jhan-vnnik-3-shared-save`, based on PR #4887 | Shared saves of 16-token blocks, transposed in registers and written as whole cache lines by the main thread and idle helper threads. This provides PR #4424's TTFT improvement. | draft until PR #4887 merges |
| 4 | this PR, `jhan-vnnik-4-tail-block`, based on PR #4898 | A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the packed layout when all 16 rows are saved. A row-major policy under hardware attention (FPGA attention) addresses issue #4500. The `deb` package-build preset enables the option in the released package. | draft until PR #4898 merges |

Only this PR's `deb` preset enables VNNI K storage.
The intermediate stack presets keep it disabled.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

