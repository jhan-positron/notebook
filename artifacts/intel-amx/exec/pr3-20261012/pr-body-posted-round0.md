## Short version

This pull request replaces the per-row store of the packed attention keys introduced by PR #4868 with a block save: a run of 2 to 16 consecutive tokens of one 16-token block is transposed in registers and written as 64-byte cache lines (masked to the run's tokens when the run is shorter than the block), and the main thread shares that store with its idle helper threads when a pass holds more than 16 tokens, while a single token, as in every decode step, keeps the per-row store. In the measured runs of the qwen3-4b model with a 1,024-token prompt, time to first token against the kernel PR's binary (PR #4887, the pull request this one is based on) at `0ee8671d35` changes by -153 ms (-4.7 %) at tp2 (the model split across 2 devices) and -243 ms (-10.2 %) at tp4 (4 devices), both beyond the 0.15 s decision band (the threshold below which a difference does not count as a change), against `main` at `72308ec90c` by -57 ms (-1.8 %) at tp2 and -75 ms (-3.4 %) at tp4, both inside the band, and decode throughput against the kernel PR's binary changes by +0.3 % (+0.22 tokens per second per user, TPS, inside the 0.88 TPS band) at tp2. The packed key layout remains disabled in every build preset, and the row-major tail block (a block whose rows stay row-major until all 16 are saved) and the `deb` package preset follow in the fourth PR.

### Background

With the option on, the layout PR stores the K rows of every 128-dimension head in the VNNI layout. Its `save_k` writes each token's K row with 4 scatters that put the token's 64 dimension pairs into 64 different 64-byte lines, 4 bytes per line. The row-major store of `main` writes 4 whole lines per token. Those partial line writes are a prefill cost.

The traces of 2026-09-14 on the Granite Rapids test machine measured that cost on the PR #4424 branch at commit `9928cb28` (qwen3-4b, 8 users, prompt length 1,024 tokens, CPU attention, 128 tokens of each user per pass). With the per-row scatter store, the K store of one prefill layer took 858 us at tp2, which is 105 ns per (token, KV head) row (a KV head is one key/value head). With the block save shared with the helpers it took 80 us at tp2 and 60 us at tp4. PR #3879 is the pull request that added the AMX attention kernels to `main`. The row-major store of its binary at commit `544ca05c7a` took 274 us at tp2 and 281 us at tp4 in a second trace set of the same day and settings. The V store, which this PR does not change, took 289 us to 316 us per layer in every arm of the two trace sets. These numbers are the reason for the design. The measurements of this PR are in the Measurements section.

The block save writes the same bytes as the per-row store. Only the write pattern differs. A page (a 64-token unit of the KV cache) has one K plane per KV head. A plane holds the 64 tokens in 4 blocks of 16. The K rows of one block are stored, per KV head, in 3 ways:

1. 16 tokens, a full block (typical in prefill): the store takes 4 steps, one per 32 dimensions. In each step, 16 AVX-512 registers are filled, one token each, with the token's 64-byte line of 16 dimension pairs for that step. The 16 registers are then transposed. After the transpose, each register holds one dimension pair of the 16 tokens. Each register is then written as one whole 64-byte line: 16 lines per step, 64 lines per block.
2. 2 to 15 tokens (prefill edges): the same, but each line store is masked to the run's tokens. The slots of the absent tokens are not written.
3. 1 token (decode): no transpose. Each of the 4 steps loads 64 bytes of the row into one register and scatters its 16 pairs into 16 cache lines, 4 bytes each: 4 scatters, 64 cache lines. This is the per-row store of the layout PR.

In a generated plugin (the model code that the code generator emits), the main thread runs `save_k` while its helper threads (the threads that run the per-token kernels) are idle. Their next kernel waits for the attention output. So the helpers take part in the store. The main thread cuts the pass's items into work units. A unit is a group of consecutive items in one 16-token block of one page with the same KV-write flag. A unit whose items have no KV work stores nothing. Every thread takes the next unit from one shared counter until no unit is left. The runtime's split heuristic (the rule that chooses how many helper threads a pass gets) sets the number of helpers once per pass. In the traced runs of 2026-09-14 it was 7 helpers plus the main thread at tp2, and 8 at tp4. Three cases are not shared and store on the thread that calls `save_k`. The first is a pass of at most 16 tokens, for example a decode step of the 8-user runs. The second is a caller that passes one worker: the handwritten plugins, and the unit tests except the three-thread section of `t_llama_unit` (the model and cache unit-test binary). The third is more than 128 workers.

## Words used here

| Term | Meaning |
|---|---|
| PR, main, stack, the layout PR, the kernel PR | PR means pull request. `main` is the target branch of the stack. The stack is the sequence of four dependent PRs replacing PR #4424 (the original single pull request for this work). This is the third PR. The layout PR is the first one, PR #4868, branch `jhan-vnnik-1-layout`. The kernel PR is the second one, PR #4887, branch `jhan-vnnik-2-amx`, based on the layout PR. This PR is based on the kernel PR. |
| tron, runtron | tron (the inference program under test), runtron (its command-line tool). |
| token, generated token, layer | A token is a unit of text processed by the model. A generated token is one output token. A layer is one stage of the model's computation. |
| attention, head, Q, K, V | Attention combines saved token information using scores. A head is one attention computation channel. Q holds query vectors, K holds key vectors, and V holds value vectors. The KV cache stores K and V for past tokens. |
| CPU, FPGA | CPU means central processing unit. FPGA means field-programmable gate array. Here it is the accelerator card that runs attention for the pages assigned to it. |
| AMX, AVX-512, VNNI | AMX (Advanced Matrix Extensions) and AVX-512 (Advanced Vector Extensions, 512-bit vectors) are CPU instruction sets. AMX supports tile matrix multiplication. VNNI means Vector Neural Network Instructions. The VNNI layout is an operand format read by VNNI instructions and AMX tile multiplication. |
| VNNI layout, packed | Two consecutive dimensions of one token are adjacent in memory. One 64-byte line holds that dimension pair for 16 consecutive tokens. This is the right-operand format of AMX tile multiplication. Packed means stored in the VNNI layout. Packed K, VNNI K and the layout mean the same thing in this PR. A packed slot or page is one whose K uses that layout. |
| row-major K | The layout `main` uses: one contiguous row of values per token. For the heads changed by the layout PR, each row holds 128 values. |
| plane, panel, token block, dimension step | A plane is the K or V storage of one page and one KV head. Unqualified, plane means the K plane here: 64 tokens x 128 dimensions x 2 bytes = 16 KiB. A dimension step is 32 dimensions. A 128-dimension head therefore has 4 steps. A token block is 16 consecutive tokens of a page. A page therefore has 4 blocks. Block c holds the page offsets c x 16 to c x 16 + 15. A panel is the 1 KiB part of the plane for one dimension step and one token block: 16 dimension-pair rows of 64 bytes. The plane holds 4 steps x 4 blocks = 16 panels. |
| line, dword, scatter, masked store | A line is a 64-byte CPU cache line. A dword is a 4-byte unit. A scatter is a vector store whose 16 dwords go to 16 separate addresses. A masked store writes only the dwords whose mask bit is set. |
| the kernel, the reader, the dotter | The kernel is `qk_vnni_128x4` of the kernel PR, the AMX routine that reads the packed plane as its right operand and scores one dense page (a full 64-token page that the query sees whole). The reader is `k_vnni::qk_group` of the layout PR, the AVX-512 routine that scores a query group (the query heads that share one KV head) against one packed page, one token per vector lane. The dotter is `main`'s software loop that computes one dot product per token from row-major K. |
| store_row, the per-row store, the scatter store | `store_row` writes one token's K row into a packed plane with 4 scatters of 16 dwords. Together they write 4 bytes into each of the token's 64 lines. `save_k` of the layout PR stores every token this way. The per-row store and the scatter store mean this store. |
| store_block, the block save, transpose | `store_block` (this PR) writes the K rows of up to 16 tokens of one token block into a packed plane. For each of the 4 dimension steps it loads one 64-byte line per present row, transposes the 16 registers in place (`transpose_16x16_epi32`: four stages of two-register shuffles, 64 shuffles in all) and writes each of the panel's 16 pair rows as one 64-byte store. The transpose turns 16 rows of 16 dwords (one token per register) into 16 registers of one dword per token. The block save means this store, with or without a mask. |
| present mask, masked partial block | A 16-bit mask whose bit t says that the row of block offset t is present. A full block has the mask 0xffff and uses unmasked line stores. A partial block (2 to 15 present tokens) uses line stores masked to the present lanes. The slots of absent tokens are not written. |
| set_k_row, set_k_block | The page accessors of the two store paths. `page::set_k_row` stores one token's row through `store_row`. `page::set_k_block` (this PR) stores one block through `store_block`, after a bound check of the block index. |
| run, work unit, unit table | A run is a sequence of consecutive tokens of one pass that fall into the same 16-token block of the same page. A work unit is a run of consecutive items of the pass's item list with the same KV-write flag, inside one block when the items write KV. The unit table (`unit_start[]`) holds the first item of every unit. A unit never crosses a page, a 16-token block or a change of the KV-write flag. A KV-writing unit is therefore one run, unless a page offset repeats inside it. |
| minibatch, item, KV-write flag | A minibatch (`batch` in the code) is one group of a pass's token jobs. Its items are the token jobs of the pass. A generated plugin has one minibatch per pass, so the minibatch holds the whole pass. The KV-write flag (`token_jobs_do_kv`) says whether an item writes K and V. |
| main thread, main helpers, worker index, n_workers | The main thread runs the schedule of a generated plugin. The main helpers are the threads of that plugin that run the per-token kernels. The worker index (`worker_ix`) is 0 for the main thread and 1 to n_workers - 1 for the helpers. `n_workers` is the count of main plus helpers. The defaults 0 and 1 store every row on the calling thread. |
| window, claim counter, join, watchdog | A window is one shared store: the state that the main thread opens in `save_k` and that the helpers join (`batch::k_store_window`). The claim counter (`next_unit`) assigns unit indices to every thread. The counters `opened` and `finished` count the windows opened in the pass and the helpers done with the open one. The join is the main thread's wait for every helper to finish the open window. The watchdog is the main thread's check during the join: it reads the clock once every 2^20 (about one million) pause loops and aborts with an error message that carries the counters when the join has not completed 120 s after the first clock read. |
| generated plugin, handwritten plugin, code generator, attention statement | A generated plugin is the model code that the code generator emits for an ingested model. A handwritten plugin is a model whose code is not generated. The code generator is tron's Haskell program (`ingest/src/TronCpp.hs`) that emits the generated plugins. The attention statement is the point of the generated schedule at which the main thread calls `save_k`. |
| LoopyTronSpec, cabal, Sydtest, fourmolu, lint-notes | `LoopyTronSpec.hs` is the code generator's test suite. cabal is the Haskell build tool. `bin/ingest-cabal test` runs the suite. Sydtest is its test framework. Its summary prints the counts of examples, passed and failed. fourmolu is the Haskell formatter. lint-notes is the repository's check that every `Note [...]` reference names a defined Note (a named comment block whose title line is underlined with tildes). |
| the option, CMake, preset | The option means `TRON_K_VNNI`, the CMake switch that selects VNNI K storage for every 128-dimension head. It defaults to OFF. No preset (a named CMake build configuration) enables it. |
| AMX dispatch | `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels and the code that selects them. |
| kill switch, AMX-on, AMX-off | The kill switch is `TRON_AMX_DISABLE=1`. It makes `amx_attn_h128g4::available()` false at run time. Then no AMX kernel runs and the reader scores every page. The store is the same with or without the switch. AMX-on allows those kernels when their other conditions hold. AMX-off disables them through this switch. |
| KV page, slot, geometry | A KV page is a 64-token unit allocated by the cache (`page` in the code). A slot is one persistent K/V storage region. Geometry means the head counts and dimensions. A packed slot uses packed K storage. A row-major slot stores K as contiguous rows. |
| KV head, kv_mul | A KV head is one key/value head. `kv_mul` means query heads per KV head. It is 4 heads for the qwen3-4b model. |
| prefill, decode, pass | A pass is one forward computation of the model over its current input. Prefill processes prompt tokens, usually many tokens per pass. Decode generates one output token per user per pass. A decode pass of the 8-user runs holds 8 items, so it is not shared. |
| owner, view | `k_vnni_tensor` owns one 16 KiB K plane as a 64-byte-aligned array. `k_vnni_view` refers to that plane. Views come only from an owner. |
| completion marks, dispatch credits | After the store, `save_k` marks each token's K as complete in its page and credits the dispatch counter of the token's attention group when the operation has a hardware slot. The main thread does both after the join. |
| bf16, fp32 | bf16 is the 16-bit brain floating-point format used for K and Q. fp32 is the 32-bit IEEE single format. IEEE is the standards organization specifying these formats. |
| Catch2, REQUIRE, SECTION, CAPTURE, SUCCEED | Catch2 is the C++ test framework of the unit tests. REQUIRE is its assertion macro. Each evaluation counts as one assertion. A SECTION is a sub-part of a test case. Catch2 runs the case once per leaf section. CAPTURE prints named values when an assertion fails. SUCCEED records one passing assertion. A placeholder case contains only SUCCEED, when the tested code is not compiled in. |
| mutation check | A deliberate code change that a test must catch. The test's failure proves that the test can fail. This PR reports two. |
| poison pattern | A fixed value written over a buffer before a check, so that an untouched byte stays recognizable. The block-save case uses the bf16 bit pattern 0xa5a5. |
| tp2, tp4, slice | `tp2` and `tp4`, also written `-tp2` and `-tp4` in a model name, split the model across 2 or 4 devices. A slice is one FPGA with its share of the host's CPU cores and memory. |
| TPS, TTFT | TPS is decode throughput in tokens per second per user. TTFT is time to first token. The measurement tables report the maximum TTFT over all 8 users. |
| base, new, new2, newoff, head, headoff | `base` is `main` at commit `72308ec90c` (the layout PR's merge base, the `main` commit it is based on), built as runtron with row-major K and AMX dispatch on. `new` is this branch at commit `80bce9a08d`, built with the option and AMX dispatch on. `new2` is a second run of `new` (the A/A repeat). `head` is the kernel PR at commit `0ee8671d35`, built the same way as `new`. `newoff` and `headoff` run `new` and `head` with the kill switch. |
| greedy run, A/A repeat | A greedy run uses temperature 0, a setting that chooses the highest-scoring token. `--pay-for-determinism` performs sums in a fixed order. An A/A repeat runs the same configuration twice as a control. |
| cell, band, standard deviation, paired t | A cell is one model, parallelism, prompt length, and attention configuration. Standard deviation measures variation between repetitions. The band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. The paired t statistic expresses the mean paired difference relative to its uncertainty. It is dimensionless. |
| CI, GCP Nix, legacy CMake lane | CI means continuous integration, the automated build and test system. GCP Nix is the default build-and-test workflow, `gcp-nix.yml`. Its Test ingest job runs the Haskell suite. Its C++ test build uses `nix/cmake-tron-test-build.nix`. The legacy CMake lane is `.github/workflows/cmake-single-platform.yml`. It runs by manual dispatch and from `publish-deb.yml`, the package-publishing workflow. |
| runner, Granite Rapids | A runner is a machine that executes CI jobs. Granite Rapids is the Intel CPU family of the Xeon 6962P test machine with AMX. The Granite Rapids machine below means that machine. |
| slice check, cost data | `bin/slice bench --check` checks registered tests for timing records in `config/test-benchmarks.json`. These records are cost data: test durations at 1, 2, and 4 slices. |
| worktree, translation unit | A worktree is a separate checkout used for one build. A translation unit is one source file after its included headers have been expanded. |

## The changes

The owner's header adds the block save. [h/tron/tensor/k_vnni.hpp]

- `store_block` takes the writable plane view, the block index c, the present mask and 16 row pointers. It checks the block index against the plane's block count, as `store_row` checks its token index. Each of the 4 dimension steps does the same work. It loads one 64-byte line per present row. An absent row's pointer may be null and is not read. It transposes the 16 registers in place. It then writes the step's panel, 16 pair rows, as 64-byte stores. When the block is partial, the stores are masked to the present lanes. Compared with `store_row` per token, a full block issues 64 whole-line stores instead of 64 scatters that each write 4 bytes into 16 lines. The same 4 KiB is written.
- `transpose_16x16_epi32` is the in-place transpose of 16 registers of 16 dwords: four stages of two-register shuffles, 64 shuffles in all.
- Two constants name the full mask (`FULL_BLOCK_0XFFFF`) and the dword count of one register (`LANES_16`). A new compile-time assertion ties the block size and the step size to the lane count. The assertion that every constant's name states its value gains the clause `LANES_16 == 16`.
- The comment above `store_row` says that only the token's own 64 slots are written. It adds that several threads may therefore store different tokens of one plane at the same time. The operation lists name `store_block`.

The cache header adds the page accessor and describes the two store paths. [h/tron/models/kv_cache.hpp]

- `page::set_k_block` takes the slot, the KV head, the block index, the present mask and the 16 row pointers. It checks the block index against the page size (4 blocks) and calls `store_block` on the typed view. It exists for packed slots only.
- Note [K VNNI storage] (the named comment block that documents the layout) item 1 describes the two store paths of `save_k`: the block save for a run of 2 to 16 consecutive tokens of one block, the per-row store for a run of one token, and the sharing with the idle main helpers for a pass of more than 16 tokens. The kill switch leaves both paths untouched. The typed-operations list names `store_block`.

The batch gains the window state. [h/tron/models/common.hpp]

- `batch::k_store_window_t` holds the claim counter `next_unit` on its own cache line (a claim must not invalidate the line the waiting threads poll), the counters `opened` and `finished`, the unit count, the unit table of `max_minibatch_size + 1` entries, and `helper_windows`, one counter per helper of the windows it has entered. The size of that array, 128, bounds the worker count of a shared store. One window state exists per minibatch. It holds the claim counter on its own 64-byte cache line, the counters `opened` and `finished` and the unit count (12 bytes), the unit table (4 bytes per entry, `max_minibatch_size + 1` entries) and the 512-byte `helper_windows` array. With the generated plugins' `max_minibatch_size` of 1,024 that is 4,736 bytes, alignment padding included.

The model header holds the store and its protocol. [h/tron/models/model.hpp]

- Note [Shared block save] states the protocol and the deadlock argument.
- `k_store_shared` decides whether a window exists: the option on, 1 < `n_workers` <= 128, and more than 16 items. The main thread and every helper compute it from the same inputs, so a helper never waits for a window the main thread does not open.
- `k_store_cut_units` cuts the item list into work units. A new unit starts at the first item, at a change of the KV-write flag, at a change of page and at a change of 16-token block. Only the main thread calls it, before it opens the window.
- `store_k_block` stores the K rows of the items of one unit, for every KV head. With the option on it builds runs of consecutive items in one block of one page (items without KV work are skipped and do not end a run, and a repeated page offset ends it). A run of one token takes `set_k_row`. A run of 2 to 16 tokens takes `set_k_block` with the run's mask. A K row that is not bf16 is converted to bf16 on the stack first, through the same row view the per-row store uses. With the option off, every token takes the row-major row store, as on `main`.
- `save_k_impl` takes the worker index and the worker count. An unshared store is the main thread's alone: a helper returns at once. In a shared store the main thread cuts the units, resets the claim counter and `finished` to 0, and increments `opened` with release ordering. Release and acquire are the C++ memory orders of atomic operations: every write a thread makes before its release increment is visible to the thread whose acquire read sees that increment. A helper's W-th shared call waits until `opened` reaches W with acquire ordering, so window W of a pass is the W-th shared `save_k` of that pass on both sides. Every thread claims units with an atomic add on the claim counter and stores each unit it claims. A helper increments `finished` with release ordering when its claim loop ends and returns. The main thread waits until `finished` equals `n_workers - 1` with acquire ordering. Every row store therefore happens before the main thread continues. The watchdog runs inside that wait.
- The completion marks and the dispatch credits stay on the main thread, after the join, in item order, one token at a time.
- The deadlock argument: the main thread waited for every token's K channel (the per-token channel of the generated code on which the rotated K rows arrive) before it called `save_k`, and the channel phase (the channel's per-layer cycle, which the main thread alone advances) cannot advance while the main thread is inside `save_k`. Nothing blocks between a helper's rope kernel (the kernel that rotates the K rows) and the attention statement. A helper therefore reaches its `save_k` call without the main thread's help. So the join cannot wait for a helper that waits for the main thread.
- The two `save_k` overloads take `worker_ix` and `n_workers` with the defaults 0 and 1. The handwritten plugins and the unit tests, except the three-thread section of `t_llama_unit`, pass the defaults and store on the calling thread.

Note [QK orientation] in the kernel interface names the K store, with its two store paths, and the reader as the two places the extra work of the flipped orientation moves to (the kernel takes the query rows as the left operand of the tile multiply and the packed K plane as the right operand, the reverse of `main`'s row-major AMX kernel). [h/tron/kernels/amx_attn_iface.hpp]

The code generator emits the helpers' call. [ingest/src/TronCpp.hs]

- For an attention statement whose operation writes KV, the helper function `run_main_help` calls `save_k` with the helper's `worker_ix` and the worker count `n_workers` of that function, at the same position of the statement list at which the main thread calls it. The main thread's call passes 0 and `n_workers`. An operation without a KV write emits nothing on the helper side.

The generator's test suite checks both call texts. [ingest/test/LoopyTronSpec.hs]

- In the two specs that count the attention calls, a KV-writing operation emits two `save_k` calls. The main-side call text ends in `,0,n_workers);` and the helper-side call text in `,worker_ix,n_workers);` after whitespace removal. The second operation of the shared-slot spec, which writes nothing, emits no call.

Tests change as follows:

- `t_k_vnni_layout`, the test of the packed layout, gains the case "VNNI K block save equals the per-token row store, bit for bit".
  - For each of the 4 blocks and 38 masks (14 fixed masks: the full block, the empty block, single tokens, halves, alternating lanes and mixed patterns, and 24 random masks) it stores the same rows with `store_row` and with `store_block` into two planes filled with the poison pattern, and compares the planes bit for bit: 152 comparisons.
  - The poison outside the block proves that the block save touches no other block.
  - The case calls `store_block` on an owner directly, so it runs whatever the option is.
- `t_llama_unit`, the model and cache unit-test binary, rewrites the `save_k` case as "save_k stores every token's K row once, grouped by page block, alone or with helper threads", with two sections over the same 48-item pass (a run that starts in the middle of a block, runs that cross a block boundary and a page boundary, a whole block, a token alone in its block, and jobs without KV work inside and after a run).
  - One thread: the grouping stores every row bit for bit, touches no other row of the book (the cache object that owns a group of pages), marks every KV job once, and opens no window.
  - Three threads: two helper threads and the main thread call `save_k` with their worker indices, on the operations of both layers, one layer after the other. The batch therefore sees two windows. The rows and the marks are checked the same way after each window. With the option on, the window state is checked too: the window count, the finished-helper count, each helper's own window count, the claim counter at the unit count plus the worker count (every claim loop ran until no unit was left), and the unit table. Every unit lies inside one page, one 16-token block and one KV-write flag value. A new unit starts only at a change of one of those, so the units are the maximal runs.
  - With the option off, both sections run the row-major store and no window opens.

This PR includes the masked partial-block path: `store_block`'s masked branch, the present mask of `set_k_block`, and the one-token branch of `store_k_block`. The fourth PR of the stack replaces it with the row-major tail block. [Open items below]

## Measurements

The measurements compare TTFT and decode TPS with the option on against the kernel PR's binary, and against `main`. They also measure the store under the reader, the kill switch inside this PR, and the kernel PR against `main` in the same session.

Configurations:

- `base`: `main` at `72308ec90c`, built as runtron with row-major K and AMX dispatch on.
- `new`: this branch at `80bce9a08d`, with the option and AMX dispatch on.
- `head`: the kernel PR at `0ee8671d35`, built the same way as `new`.
- `newoff` and `headoff`: those two binaries with the kill switch.

The experiment ran on 2026-10-12:

- Model: qwen3-4b, at tp2 and at tp4.
- Load: 8 users and 256 generated tokens.
- Attention: CPU, selected by `USE_HW_ATTN=0`.
- Cells: tp2 with prompt lengths 1,024 and 8,192 tokens, and tp4 with prompt length 1,024 tokens.
- Repetitions: 3, with the binaries run in alternating order.
- Allocation: the whole Granite Rapids test machine with production serving stopped (the tp4 cell needs its four FPGA cards and 256 huge pages, the large memory pages reserved for the run's buffers).

`base` and `head` are measured at tp4 for the first time at these revisions.

The decision band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. Bands are shown rounded to 0.01 TPS and 0.01 s. A difference beyond that band counts as a change. Paired t uses the 3 repetitions.

Each parenthesized value is the sample standard deviation over the 3 repetitions. TPS has units of tokens/s/user. Both TTFT and its standard deviation have units of seconds.

| Cell | Binary | TPS (tokens/s/user) | TTFT (s) |
|---|---|---|---|
| tp2, 1,024 tokens | base | 80.99 (0.29) | 3.178 (0.006) |
| tp2, 1,024 tokens | new | 85.15 (0.22) | 3.120 (0.004) |
| tp2, 1,024 tokens | newoff | 75.72 (0.11) | 3.888 (0.003) |
| tp2, 1,024 tokens | head | 84.94 (0.44) | 3.273 (0.003) |
| tp2, 1,024 tokens | headoff | 75.82 (0.38) | 3.937 (0.003) |
| tp2, 8,192 tokens | base | 17.30 (0.03) | 52.607 (0.117) |
| tp2, 8,192 tokens | new | 18.88 (0.01) | 51.780 (0.147) |
| tp2, 8,192 tokens | newoff | 15.49 (0.04) | 117.464 (0.111) |
| tp2, 8,192 tokens | head | 18.98 (0.01) | 51.952 (0.091) |
| tp2, 8,192 tokens | headoff | 15.51 (0.08) | 116.865 (0.106) |
| tp4, 1,024 tokens | base | 117.38 (0.48) | 2.211 (0.007) |
| tp4, 1,024 tokens | new | 121.36 (0.12) | 2.135 (0.010) |
| tp4, 1,024 tokens | newoff | 111.74 (0.36) | 2.403 (0.004) |
| tp4, 1,024 tokens | head | 120.28 (0.63) | 2.378 (0.003) |
| tp4, 1,024 tokens | headoff | 111.08 (0.67) | 2.535 (0.011) |

"Inside" and "beyond" refer to the decision band. The paired t values are dimensionless.

| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
| tp2, 1,024 tokens | new vs base | +5.1 % (+4.16 TPS, t +14.6), beyond | -57 ms (-1.8 %, t -22.5), inside | 0.58 TPS / 0.15 s |
| tp2, 1,024 tokens | new vs head | +0.3 % (+0.22 TPS, t +0.6), inside | -153 ms (-4.7 %, t -35.6), beyond | 0.88 TPS / 0.15 s |
| tp2, 1,024 tokens | newoff vs new | -11.1 % (-9.43 TPS, t -69.1), beyond | +768 ms (+24.6 %, t +198.9), beyond | 0.44 TPS / 0.15 s |
| tp2, 1,024 tokens | newoff vs headoff | -0.1 % (-0.10 TPS, t -0.6), inside | -50 ms (-1.3 %, t -150.3), inside | 0.76 TPS / 0.15 s |
| tp2, 1,024 tokens | head vs base | +4.9 % (+3.95 TPS, t +36.2), beyond | +95 ms (+3.0 %, t +20.3), inside | 0.88 TPS / 0.15 s |
| tp2, 8,192 tokens | new vs base | +9.1 % (+1.57 TPS, t +108.4), beyond | -827 ms (-1.6 %, t -8.6), beyond | 0.40 TPS / 0.29 s |
| tp2, 8,192 tokens | new vs head | -0.6 % (-0.10 TPS, t -8.7), inside | -172 ms (-0.3 %, t -2.3), inside | 0.40 TPS / 0.29 s |
| tp2, 8,192 tokens | newoff vs new | -18.0 % (-3.39 TPS, t -132.4), beyond | +65.7 s (+126.9 %, t +695.4), beyond | 0.40 TPS / 0.29 s |
| tp2, 8,192 tokens | newoff vs headoff | -0.1 % (-0.02 TPS, t -0.4), inside | +599 ms (+0.5 %, t +4.8), beyond | 0.40 TPS / 0.22 s |
| tp2, 8,192 tokens | head vs base | +9.7 % (+1.68 TPS, t +94.8), beyond | -655 ms (-1.2 %, t -5.8), beyond | 0.40 TPS / 0.23 s |
| tp4, 1,024 tokens | new vs base | +3.4 % (+3.98 TPS, t +15.3), beyond | -75 ms (-3.4 %, t -13.9), inside | 0.96 TPS / 0.15 s |
| tp4, 1,024 tokens | new vs head | +0.9 % (+1.08 TPS, t +2.6), inside | -243 ms (-10.2 %, t -45.2), beyond | 1.26 TPS / 0.15 s |
| tp4, 1,024 tokens | newoff vs new | -7.9 % (-9.63 TPS, t -44.5), beyond | +268 ms (+12.5 %, t +77.0), beyond | 0.72 TPS / 0.15 s |
| tp4, 1,024 tokens | newoff vs headoff | +0.6 % (+0.66 TPS, t +2.7), inside | -132 ms (-5.2 %, t -28.7), inside | 1.34 TPS / 0.15 s |
| tp4, 1,024 tokens | head vs base | +2.5 % (+2.90 TPS, t +4.8), beyond | +167 ms (+7.6 %, t +80.0), beyond | 1.26 TPS / 0.15 s |

### The TTFT gain of the block save (new vs head)

The kernel PR's description lists the per-row scatter store's cost in TTFT as an open item, and says that this PR is intended to remove it. [PR #4887, Open items] `new` and `head` differ only in the store: the layout, the kernel and the reader are the same.

- TTFT of `new` against `head`:
  - -153 ms (-4.7 %), beyond the 0.15 s band, paired t -35.6, at tp2, 1,024 tokens.
  - -172 ms (-0.3 %), inside the 0.29 s band, paired t -2.3, at tp2, 8,192 tokens.
  - -243 ms (-10.2 %), beyond the 0.15 s band, paired t -45.2, at tp4, 1,024 tokens.

The block save removes the scatter store's prefill cost. At prompt length 1,024 tokens, `new` reaches the first token 153 ms earlier than `head` at tp2 and 243 ms earlier at tp4, beyond the band in both cells. At 8,192 tokens the difference is 172 ms, inside the 0.29 s band. The prefill of that cell takes about 52 s. The 172 ms difference is 0.3 % of it. The K store's share of that prefill is not measured in this run.

### Decode TPS against the kernel PR (new vs head)

A decode pass of the 8-user runs holds 8 items. That is not more than 16, so no window opens. Each item is a run of one token. A run of one token takes the per-row store, as in the kernel PR. The store path still differs in three ways: a grouping pass runs before the scatter, the completion marks run in a separate loop, and every helper calls `save_k`, evaluates the sharing predicate and returns. The expectation is a TPS difference inside the band. The measured pair decides.

- TPS of `new` against `head`:
  - +0.3 % (+0.22 TPS, inside the 0.88 TPS band, paired t +0.6) at tp2, 1,024 tokens.
  - -0.6 % (-0.10 TPS, inside the 0.40 TPS band, paired t -8.7) at tp2, 8,192 tokens.
  - +0.9 % (+1.08 TPS, inside the 1.26 TPS band, paired t +2.6) at tp4, 1,024 tokens.

Decode TPS is inside the band in all three cells, so the expectation holds. The tp2 cell at prompt length 8,192 tokens shows a consistent -0.10 TPS (-0.6 %, paired t -8.7) inside the 0.40 TPS floor of the band. The three store-path differences named above run in every decode pass, so they are a candidate cause of a difference of that size. The measurement named under the reader pair below would settle it.

### This PR against `main` (new vs base)

- TPS of `new` against `base`:
  - +5.1 % (+4.16 TPS, beyond the 0.58 TPS band, paired t +14.6) at tp2, 1,024 tokens.
  - +9.1 % (+1.57 TPS, beyond the 0.40 TPS band, paired t +108.4) at tp2, 8,192 tokens.
  - +3.4 % (+3.98 TPS, beyond the 0.96 TPS band, paired t +15.3) at tp4, 1,024 tokens.
- TTFT of `new` against `base`:
  - -57 ms (-1.8 %), inside the 0.15 s band, paired t -22.5, at tp2, 1,024 tokens.
  - -827 ms (-1.6 %), beyond the 0.29 s band, paired t -8.6, at tp2, 8,192 tokens.
  - -75 ms (-3.4 %), inside the 0.15 s band, paired t -13.9, at tp4, 1,024 tokens.

`new` is above `main` in decode TPS in all three cells, as the kernel PR is. TTFT is below `main` in all three cells: inside the 0.15 s band at the two 1,024-token cells and beyond the band at 8,192 tokens. The net TTFT effect against `main` (the layout, the kernel and the store together) at tp2 prompt length 1,024 tokens is -57 ms here, against +100 ms in the kernel PR's run. Both values are inside the band. The scatter store's cost is no longer in the net effect.

### The store under the reader (newoff vs headoff)

Both binaries run the reader for every page with the kill switch. The store does not depend on the attention path, so the expected TTFT gain is about the same absolute size as `new` against `head`. A decode TPS difference beyond the band needs investigation, including the three store-path differences named above. The measurement that would settle such a difference: the K-store spans of a Perfetto trace (tron's timing trace) of the same decode workload for both arms.

- TPS of `newoff` against `headoff`:
  - -0.1 % (-0.10 TPS, inside the 0.76 TPS band, paired t -0.6) at tp2, 1,024 tokens.
  - -0.1 % (-0.02 TPS, inside the 0.40 TPS band, paired t -0.4) at tp2, 8,192 tokens.
  - +0.6 % (+0.66 TPS, inside the 1.34 TPS band, paired t +2.7) at tp4, 1,024 tokens.
- TTFT of `newoff` against `headoff`:
  - -50 ms (-1.3 %), inside the 0.15 s band, paired t -150.3, at tp2, 1,024 tokens.
  - +599 ms (+0.5 %), beyond the 0.22 s band, paired t +4.8, at tp2, 8,192 tokens.
  - -132 ms (-5.2 %), inside the 0.15 s band, paired t -28.7, at tp4, 1,024 tokens.

TPS is inside the band in all three cells. TTFT is lower with this PR's binary at both 1,024-token cells: 50 ms at tp2 and 132 ms at tp4, both inside the 0.15 s band. Those gains are smaller than the 153 ms and 243 ms of `new` against `head` in the same cells. The expectation of the same absolute size therefore does not hold under the reader. The cause of the smaller gain is not measured. TTFT is higher by 599 ms at tp2 prompt length 8,192 tokens, beyond the 0.22 s band (paired t +4.8). The TTFT of that cell is about 117 s under the reader, so the difference is 0.5 % of it. The store's expected effect at this prompt length is the 172 ms of the `new` against `head` pair, which is smaller than the difference. The cause is not measured. [Open items below]

### The kill switch inside this PR (newoff vs new)

The store is the same with or without the switch. The expectation is the kernel PR's measurement of its own binary: TPS -11.0 % and -18.3 %, TTFT +674 ms and +64.9 s, at tp2 prompt lengths 1,024 and 8,192 tokens. [PR #4887, Measurements]

- TPS of `newoff` against `new`:
  - -11.1 % (-9.43 TPS, beyond the 0.44 TPS band, paired t -69.1) at tp2, 1,024 tokens.
  - -18.0 % (-3.39 TPS, beyond the 0.40 TPS band, paired t -132.4) at tp2, 8,192 tokens.
  - -7.9 % (-9.63 TPS, beyond the 0.72 TPS band, paired t -44.5) at tp4, 1,024 tokens.
- TTFT of `newoff` against `new`:
  - +768 ms (+24.6 %), beyond the 0.15 s band, paired t +198.9, at tp2, 1,024 tokens.
  - +65.7 s (+126.9 %), beyond the 0.29 s band, paired t +695.4, at tp2, 8,192 tokens.
  - +268 ms (+12.5 %), beyond the 0.15 s band, paired t +77.0, at tp4, 1,024 tokens.

The two tp2 cells repeat the kernel PR's measurement of its own binary within 0.1 TPS, and within 0.1 s of TTFT at prompt length 1,024 tokens and 0.8 s at 8,192 tokens. The tp4 cell adds -7.9 % TPS and +268 ms TTFT. The store is the same with or without the switch, so these differences are the AMX page path's gain, as in the kernel PR.

### The kernel PR against `main` in this session (head vs base)

This pair repeats the kernel PR's claim in the same session as the other pairs. The kernel PR measured TPS +5.4 % and +9.5 % and TTFT +100 ms and -523 ms at tp2 prompt lengths 1,024 and 8,192 tokens on 2026-10-11. [PR #4887, Measurements] A deviation beyond the bands would say that the machine's speed changed between the two sessions. Such a change would limit what every other pair of this run can show.

- TPS of `head` against `base`:
  - +4.9 % (+3.95 TPS, beyond the 0.88 TPS band, paired t +36.2) at tp2, 1,024 tokens.
  - +9.7 % (+1.68 TPS, beyond the 0.40 TPS band, paired t +94.8) at tp2, 8,192 tokens.
  - +2.5 % (+2.90 TPS, beyond the 1.26 TPS band, paired t +4.8) at tp4, 1,024 tokens.
- TTFT of `head` against `base`:
  - +95 ms (+3.0 %), inside the 0.15 s band, paired t +20.3, at tp2, 1,024 tokens.
  - -655 ms (-1.2 %), beyond the 0.23 s band, paired t -5.8, at tp2, 8,192 tokens.
  - +167 ms (+7.6 %), beyond the 0.15 s band, paired t +80.0, at tp4, 1,024 tokens.

The kernel PR's TPS claim repeats within 0.5 percentage points at tp2: +4.9 % and +9.7 % here against +5.4 % and +9.5 % in its own run. Its TTFT claim repeats within 0.3 percentage points: +3.0 % (+95 ms, inside the band) and -1.2 % (-655 ms, beyond) here against +3.2 % (+100 ms) and -1.0 % (-523 ms). The two sessions differ by 0.41 TPS and 5 ms at prompt length 1,024 tokens and by 0.03 TPS and 132 ms at 8,192 tokens, all inside the bands. So no machine-speed change between the sessions limits the other pairs of this run. At tp4, measured for the first time, `head` is +2.5 % in TPS (beyond the 1.26 TPS band) and +167 ms in TTFT (beyond the 0.15 s band). That +167 ms is the net TTFT effect of the layout, the kernel and the scatter store together. The scatter store alone costs more at tp4: `new`, which removes it, is 243 ms below `head` and 75 ms below `base` (the first and third subsections above).

## Verification

Build provenance:

- Machine and date: Granite Rapids, Intel Xeon 6962P with AMX, 2026-10-12.
- Revision: `80bce9a08d`. It is based on the kernel PR at `0ee8671d35`. The kernel PR is based on the layout PR at `82d05e94be`. The layout PR includes `main` at `72308ec90c`.
- Environment: `nix develop`, the project's pinned build shell.
- Compiler: clang version 19.1.7.
- Preset: `native` (the Ninja build runner, the clang-19 compiler, the ccache compiler cache, the lld linker, build type `RelWithDebInfo`). The AVX-512 flags are explicit in `src/tron/CMakeLists.txt` and do not depend on the preset or on the build host.
- Build type: `RelWithDebInfo`, an optimized build with debug symbols.
- Each of the 3 configurations used a separate worktree.

`BUILD_INGEST_MODELS` controls compilation of the models produced by the ingest pipeline (the project's model conversion step).

| Configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | Targets | Build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | 873 s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | 271 s |
| option off | OFF | ON | OFF | the 6 tests below without `t_phase1_integration` | 289 s |

`t_heterogeneous_scheduler` tests scheduling across different attention geometries. `t_k_vnni_layout` tests the packed layout, its row and block operations and the reader. `t_phase1_integration` tests staging (the copy of K and V into buffers read by the FPGA) and dispatch integration.

The following unit-test binaries passed with a fake device (a simulated FPGA). `--skip-benchmarks` excluded their benchmark sections. Each result gives assertions / test cases.

| Test | Option on | Option on, no AMX dispatch | Option off |
|---|---|---|---|
| `t_k_vnni_layout` | 1011585 / 5 | 1011585 / 5 | 1011585 / 5 |
| `t_amx_dispatch_dtype` | 1618 / 1 | 1 / 1 (placeholder without dispatch) | 1618 / 1 |
| `t_amx_numerics` | 6669 / 5 (AMX cases ran, no "AMX unavailable" line) | 1 / 1 (placeholder without dispatch) | 6669 / 5 (AMX cases ran) |
| `t_llama_unit` | 269326 / 66 | 269326 / 66 | 269067 / 66 |
| `t_heterogeneous_scheduler` | 2783 / 3 | 2783 / 3 | 2783 / 3 |
| `t_phase1_integration` | 6220 / 64 | 6220 / 64 | not built |

`t_k_vnni_layout` reports 5 test cases in every build: the block-save case runs whatever the option is. The `save_k` case of `t_llama_unit` runs both sections in every build. With the option off it runs the row-major store and opens no window. The identity case of `t_amx_numerics` (the kernel PR's bit-identity check of the AMX kernel) ran on real AMX in the option-on build and in the option-off build. Neither `t_amx_numerics` run printed an "AMX unavailable" line.

Kill-switch results in the option-on build:

- `t_llama_unit`: 269326 assertions passed in 66 cases. This matches the AMX-on count.
- `t_amx_numerics`: 4108 assertions passed in 5 cases. Its QK precision, identity and PV precision cases reported "AMX unavailable".

Two mutation checks ran in the option-on worktree.

- The block store: the panel address of `store_block` was changed from `(s * k_vnni::TOKEN_BLOCKS_4 + c)` to `(s * k_vnni::TOKEN_BLOCKS_4 + (c ^ 1))`. Block c's rows are then written into the panels of block c ^ 1 (c XOR 1: block 0 swaps with block 1, and block 2 with block 3). The block-save case, run alone, then fails. The run reports 1 of 1 test cases failed and 1 of 1 assertions failed, at the `REQUIRE` of `t/t_k_vnni_layout.cpp:257`. With the file restored, `t_k_vnni_layout` passes again with 1011585 assertions in 5 cases.
- The work-unit cut: the block condition of `k_store_cut_units` was inverted (`block != run_block` to `block == run_block`). A run that crosses a block boundary then becomes one unit, and consecutive items of one block are cut into single-item units. The `save_k` case, run alone, then fails in its three-thread section at the unit invariant. The run reports 1 of 1 test cases failed and 1 of 2592 assertions failed, at the `REQUIRE` of `t/t_llama_unit.cpp:4052` (2591 earlier assertions passed). The captured values are unit 10, its first item 10, its end 32 (the first item of the next unit) and the failing item 11. The mutated cut made the 22 items 10 to 31 one unit. Item 11 (token 16) lies in a different 16-token block from item 10 (token 15), the unit's first item. With the file restored, `t_llama_unit` passes again with 269326 assertions in 66 cases.

The Haskell suite ran on the test machine in the option-on worktree (`bin/ingest-cabal test`): return code 0, "Test suite ingest-tests: PASS", 1,363 tests passed and 0 failed over 17,302 examples (a property test counts as one test and runs over many generated inputs), in 112 s including the package build.

The generated plugins were checked after the option-on build. For each of the 19 generated plugins, three counts are equal and positive: the `save_v` calls (one per KV-writing operation), the main-side `save_k` calls (argument list ending in `0, n_workers`) and the helper-side `save_k` calls (ending in `worker_ix, n_workers`). No `save_k` call has another argument tail. The symbol `save_k_helper`, which no file of this branch defines, does not occur in any plugin.

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

All of these checks pass at `80bce9a08d`:

- clang-format version 19.1.7, the source formatter, with `--dry-run --Werror` on all 7 changed C++ files.
- fourmolu in check mode on the 2 changed Haskell files, with the repository's hook options.
- `git diff --check`, the whitespace check, against the kernel PR's head.
- A search for the prohibited `<cassert>` header in the diff.
- `make lint-notes`, the Note-reference check, in the repository's lint shell.

Syntax-only compilation used clang version 19 with the product's compile flags. It covered 38 configurations with 0 errors and 0 warnings:

- All 4 combinations of AMX dispatch on/off and the option on/off for 9 translation units: `t_llama_unit`, `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `heterogeneous_scheduler_compile` (heterogeneous scheduling compilation), `scheduler/full.cpp` (the full scheduler), `gof.cpp` (staging), `t_gof_dma` (staging DMA, direct memory access transfers), and `t_kv_oom_subcases` (out-of-memory cases).
- `kernels/amx_attn.cpp` (the AMX kernels) with dispatch on and the option on/off.

The compiler flag is `-fsyntax-only`. The Haskell files are outside this check. Their compile is the Haskell suite above.

### Host test suite and token identity (2026-10-12)

The checks ask two questions. Does the host suite (the unit tests run by `make test-host` with a fake device) meet the exception rules listed under Acceptance rules below? Are the generated tokens identical across the selected configurations? `base` and `head` are the comparators defined in Measurements.

Host-suite setup:

- `make build-test-host` compiled the host tests.
- `make test-host` ran them with a fake device in the option-on worktree.
- The host suite ran on one CPU socket of the Granite Rapids test machine (half of its cores), with production serving stopped. The cells under Measurements used the whole machine.

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
- `new` must match `head` for all 256 generated tokens in each cell. This is the correctness claim of the PR: the block save writes the same bytes as the per-row store, and the sharing changes only which thread writes them.
- `newoff` against `new` is expected to repeat the kernel PR's result: identical at prompt length 8,192 tokens with CPU attention and at 1,024 tokens with FPGA attention, and a first difference at generated token 247 at prompt length 1,024 tokens with CPU attention. The kernel PR's forced-run check (a run that feeds both binaries the same token sequence and compares their scores at every step) showed an exact tie of the two best tokens at that step, decided by one bf16 step (the distance between two adjacent bf16 values at that magnitude) of the AMX-versus-reader numerics. This PR changes no score path. [PR #4887, Verification]
- The comparison with `base` is informational. [Issue #4444]

Host-suite result:

- All test targets compiled.
- 93 tests passed.
- 1 test skipped. The captured suite output reports the count and not the test's name. The acceptance rules permit one skip, `t_proxy_lib`, for the missing `t/proxy/.venv`.
- 1 test failed: `t_proxy_llama31`, reporting "ERROR: t/proxy/.venv missing".
- Total suite time: 110 s.
- The CMake cache retained `TRON_K_VNNI=ON` throughout the make targets.

| Cell | new vs new2 | new vs head | newoff vs new | new vs base | head vs base |
|---|---|---|---|---|---|
| CPU attention, prompt length 1024 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | first difference at generated token 247 | first difference at generated token 83 | first difference at generated token 83 |
| CPU attention, prompt length 8192 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens |
| FPGA attention, prompt length 1024 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | first difference at generated token 83 | first difference at generated token 83 |

Outcome of the acceptance rules:

- Every binary exited with status 0 and produced 256 tokens in every cell.
- `new2` matched `new` in every cell.
- `new` matched `head` for all 256 tokens in every cell.
- `newoff` against `new`. CPU attention, prompt length 1024 tokens: first difference at generated token 247 of 256 (token id 624, the token's integer index in the model's vocabulary, under the kill switch and 13 without it). CPU attention, prompt length 8192 tokens: identical, 256 of 256 tokens. FPGA attention, prompt length 1024 tokens: identical, 256 of 256 tokens. This matches the kernel PR's result.
- At prompt length 1,024 tokens, both CPU and FPGA attention first differ from `main` at generated token 83 of 256, with the same token ids as `head` against `base`. At prompt length 8,192 tokens with CPU attention, all 256 generated tokens match.

### CI coverage

The GCP Nix test build enables neither `TRON_AMX_DISPATCH` nor `TRON_K_VNNI`. [nix/cmake-tron-test-build.nix]

- In that configuration the block-save case still tests the packed storage: it compares `store_block` against `store_row` on a `k_vnni_tensor` owner, whatever the option is.
- The `save_k` case runs both sections there with the row-major store. No window opens.
- The option-on paths of the store (`set_k_block` through `save_k`, the window and the shared store) run on the Granite Rapids test machine and in the legacy CMake lane, which compiles both options on. [.github/workflows/cmake-single-platform.yml]
- The Haskell suite runs in the required CI's Test ingest job once the PR is not a draft. It ran on the test machine as reported above.
- At review time, this PR is a draft without the `Run CI` label. GCP Nix skips its product test jobs (Build Tron, Test host, Test FPGA and Test ingest) on a draft without that label. Its lint and infrastructure checks passed in [run 38270438657](https://github.com/positron-ai/tron/actions/runs/38270438657). The separate Debian smoke check (`deb-smoke.yml`, a workflow that checks authenticated access to the Debian package repository and builds no tron binary) also runs.
- The author explicitly accepts this limitation for this PR. Issue #4865 tracks enabling both options in the required test build.

## Open items

**The masked partial-block path.**

- A run of 2 to 15 present tokens of one block is stored with masked line stores: `store_block`'s masked branch, the present mask of `set_k_block`, and the one-token branch of `store_k_block`, about 20 lines in all.
- This is the tested form of the store, with the measurements above.
- The fourth PR of the stack replaces it with the row-major tail block: a run shorter than a block is stored row by row into a row-major block. That block converts to the packed layout when all 16 rows are saved. The fourth PR also removes the present mask parameter of `set_k_block`.

**The single-token store of decode steps.**

- A run of one token, as in every decode step, keeps the per-row scatter store: 4 scatters that touch 64 lines per (token, KV head) row.
- Under FPGA attention that per-token column access is the decode loss of issue #4500. The fourth PR's row-major tail block is its subject.

**The join watchdog and the worker cap.**

- The main thread aborts the process when a shared store's join has not completed 120 s after its first clock read. The message carries the finished-helper count and the claimed-unit count.
- A pass with more than 128 workers stores on the main thread alone (`helper_windows` has 128 entries). The runtime's split heuristic sets the worker count once per pass. The traced runs used 8 and 9 workers.

**128-dimension heads with kv_mul other than 4 query heads.**

- The kernel serves kv_mul 4 only. Other groups retain the packed layout and use the reader wherever `main` uses the dotter, as in the kernel PR. The store does not depend on kv_mul.
- Decode TPS of those groups is not measured at `80bce9a08d`. No AMD host is measured at this head either.
- The measurement that settles it: decode TPS of llama-3.2-3b (kv_mul 3) and qwen-3-30b-a3b (kv_mul 8) at this head against `main` at `72308ec90c`, 3 repetitions, the band rule of the Measurements section.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]**

- With the option on, the kill switch gives an AMX-off run of the same binary through the reader. It does not reproduce the tokens of a clean binary, meaning a build with both options off. The store is the same with or without the switch.
- At prompt length 1,024 tokens, both CPU and FPGA attention first differ from `main` at generated token 83 of 256, with the same token ids as `head` against `base`. At prompt length 8,192 tokens with CPU attention, all 256 generated tokens match. [Verification above]
- `newoff` against `new`. CPU attention, prompt length 1024 tokens: first difference at generated token 247 of 256 (token id 624 under the kill switch, 13 without it). CPU attention, prompt length 8192 tokens: identical, 256 of 256 tokens. FPGA attention, prompt length 1024 tokens: identical, 256 of 256 tokens. [Verification above]
- The rollback contract (the documented promise of what the kill switch restores) promises AMX off with the same AVX dotter and clean-binary numerical results. A packed binary with the switch runs the reader, not the dotter. [Item 4 of Note [AMX attention dispatch], h/tron/kernels/amx_attn_iface.hpp]
- Issue #4444 records two choices:
  1. Accept the narrower rollback contract. Add "with `TRON_K_VNNI` off" to item 4.
  2. Keep a row-major binary as the deployment rollback artifact. Document that requirement.

**A control difference beyond the band.**

- `newoff` against `headoff` at tp2 prompt length 8,192 tokens: +599 ms (+0.5 %) of TTFT, beyond the 0.22 s band, paired t +4.8. TPS is -0.1 % (-0.02 TPS), inside the 0.40 TPS band. Both binaries run the reader for every page, and the store's work is the same on both sides of the switch. The store's expected effect at this prompt length is the `new` against `head` difference of the same cell, which is smaller. The cause is not measured.
- The measurement that would settle it: the K-store spans of a Perfetto trace (tron's timing trace) of one 8,192-token prefill for both arms, and a repeat of the cell with 5 repetitions.

**Cost data of t_k_vnni_layout and t_llama_unit.**

The block-save case and the three-thread section add run time to `t_k_vnni_layout` and `t_llama_unit`. Their Granite Rapids rows in `config/test-benchmarks.json` are not refreshed here. The refresh is planned with the fourth PR's cost-row update. The slice check needs a timing row in at least one platform block, and both binaries have rows. The check is therefore expected to pass. Not run at `80bce9a08d`.

**Benchmark binary mismatch, inherited from PR #3879. Reviewers decide.**

- The legacy CMake workflow's `build` job compiles runtron with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`. It transfers that binary to its `benchmark` job.
- A successful transfer benchmarks the AMX kernels and packed K with the block save.
- After a failed transfer, the benchmark job builds runtron through `make`. That build sets neither option. It benchmarks row-major K without AMX kernels.
- PR #3879 introduced the mismatch for AMX dispatch. The layout PR added the layout option to the same configure line. This PR changes neither.
- The GCP Nix benchmark configuration is unchanged. Its binary has neither option enabled.

**CI coverage gap. [Issue #4865]**

When the GCP Nix product tests run, their current configuration runs the block-save case on the owner and the `save_k` case on the row-major store, and never opens a window. The option-on store runs on the Granite Rapids test machine and in the legacy lane. The build and test evidence of this PR is the Granite Rapids run reported under Verification. [CI coverage above]

## The stack

PR #4424 uses branch `jhan-amx-vnniK` and adds 4,054 lines. Four dependent PRs replace it. Each is based on the preceding PR. PR #4424 remains open as a reference until all four are open.

| Order | PR branch and base | What it adds | State |
|---|---|---|---|
| 1 | PR #4868, `jhan-vnnik-1-layout`, based on `main` | Packed K layout, owner and views, per-row store, reader, FPGA staging gather, the option disabled in presets, and tests | ready for review |
| 2 | PR #4887, `jhan-vnnik-2-amx`, based on PR #4868 | The AMX QK kernel `qk_vnni_128x4` and query packer `pack_q_rows_128x4`. A bit-identity test compares with the row-major kernel. The temporary gate and comments are removed. | draft until PR #4868 merges |
| 3 | this PR, `jhan-vnnik-3-shared-save`, based on PR #4887 | Shared saves of 16-token blocks, transposed in registers and written as whole cache lines by the main thread and idle helper threads (worker threads with no work of their own at that moment). This provides PR #4424's TTFT improvement. | draft until PR #4887 merges |
| 4 | `jhan-vnnik-4-tail-block`, based on this PR | A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the packed layout when all 16 rows are saved. A row-major policy under hardware attention (FPGA attention) addresses issue #4500. The `deb` package-build preset enables the option in the released package. | to follow as a draft |

The option stays off in every preset until PR 4. Intermediate states therefore do not enter production through those presets.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
