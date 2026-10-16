## Short version

This pull request replaces the per-row store of the packed attention keys introduced by PR #4868 with a block save: a run of 2 to 16 consecutive tokens of one 16-token block is transposed in registers and written as whole 64-byte cache lines, and the main thread shares that store with its idle helper threads when a pass holds more than 16 tokens, while a single token, as in every decode step, keeps the per-row store. In the measured Qwen3-4B runs with a 1,024-token prompt, time to first token against the kernel PR's binary at `0ee8671d35` changes by {{S_TTFT_HEAD_TP2}} at tp2 and {{S_TTFT_HEAD_TP4}} at tp4, against `main` at `72308ec90c` by {{S_TTFT_BASE_TP2}} at tp2 and {{S_TTFT_BASE_TP4}} at tp4, and decode throughput against the kernel PR's binary changes by {{S_TPS_HEAD_TP2}} at tp2. The packed key layout remains disabled in every build preset, and the row-major tail block and the package preset follow in the fourth PR.

### Background

With the option on, the layout PR stores the K rows of every 128-dimension head in the VNNI layout. Its `save_k` writes each token's K row with 4 scatters that put the token's 64 dimension pairs into 64 different 64-byte lines, 4 bytes per line. The row-major store of `main` writes 4 whole lines per token. Those partial line writes are a prefill cost.

The traces of 2026-09-14 on the Granite Rapids test machine measured that cost on the PR #4424 branch (qwen3-4b, 8 users, prompt length 1,024 tokens, CPU attention, 128 tokens of each user per pass). With the per-row scatter store, the K store of one prefill layer took 858 us at tp2, which is 105 ns per (token, KV head) row. With the block save shared with the helpers it took 80 us at tp2 and 60 us at tp4. The row-major store of the PR #3879 binary took 274 us at tp2 and 281 us at tp4 in the same traces. The V store, which this PR does not change, took 289 us to 316 us per layer in every arm. These numbers are the reason for the design. The measurements of this PR are in the Measurements section.

The block save writes the same bytes as the per-row store. Only the write pattern differs. A page's K plane holds 64 tokens in 4 blocks of 16. The K rows of one block are stored, per KV head, in 3 ways:

1. 16 tokens, a full block (typical in prefill): 16 AVX-512 registers are filled, one token each. The filling takes 4 steps. Each step covers 32 dimensions and loads one 64-byte line of 16 dimension pairs per token. The registers are transposed, so that each register holds one dimension pair of the 16 tokens. Each register is then written as one whole 64-byte line.
2. 2 to 15 tokens (prefill edges): the same, but each line store is masked to the run's tokens. The slots of the absent tokens are not written.
3. 1 token (decode): no transpose. Each of the 4 steps loads 64 bytes of the row into one register and scatters its 16 pairs into 16 cache lines, 4 bytes each: 4 scatters, 64 cache lines. This is the per-row store of the layout PR.

In a generated plugin (the model code that the code generator emits), the main thread runs `save_k` while its helper threads (the threads that run the per-token kernels) are idle. Their next kernel waits for the attention output. So the helpers take part in the store. Each run is one work unit. Every thread takes the next unit from one shared counter until no unit is left. The runtime's split heuristic sets the number of helpers once per pass. In the traced runs of 2026-09-14 it was 7 helpers plus the main thread at tp2, and 8 at tp4. Three cases are not shared and store on the thread that calls `save_k`: a pass of at most 16 tokens (for example a decode step of the 8-user runs), a caller that passes one worker (the handwritten plugins, and the unit tests except the three-thread section of `t_llama_unit`), and more than 128 workers.

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
| the kernel, the reader, the dotter | The kernel is `qk_vnni_128x4` of the kernel PR, the AMX routine that reads the packed plane as its right operand and scores one dense page. The reader is `k_vnni::qk_group` of the layout PR, the AVX-512 routine that scores a query group against one packed page, one token per vector lane. The dotter is `main`'s software loop that computes one dot product per token from row-major K. |
| store_row, the per-row store, the scatter store | `store_row` writes one token's K row into a packed plane with 4 scatters of 16 dwords. Together they write 4 bytes into each of the token's 64 lines. `save_k` of the layout PR stores every token this way. The per-row store and the scatter store mean this store. |
| store_block, the block save, transpose | `store_block` (this PR) writes the K rows of up to 16 tokens of one token block into a packed plane. For each of the 4 dimension steps it loads one 64-byte line per present row, transposes the 16 registers in place (`transpose_16x16_epi32`: four stages of two-register shuffles, 64 shuffles in all) and writes each of the panel's 16 pair rows as one 64-byte store. The transpose turns 16 rows of 16 dwords (one token per register) into 16 registers of one dword per token. The block save means this store, with or without a mask. |
| present mask, masked partial block | A 16-bit mask whose bit t says that the row of block offset t is present. A full block has the mask 0xffff and uses unmasked line stores. A partial block (2 to 15 present tokens) uses line stores masked to the present lanes. The slots of absent tokens are not written. |
| set_k_row, set_k_block | The page accessors of the two store paths. `page::set_k_row` stores one token's row through `store_row`. `page::set_k_block` (this PR) stores one block through `store_block`, after a bound check of the block index. |
| run, work unit, unit table | A run is a sequence of consecutive tokens of one pass that fall into the same 16-token block of the same page. A work unit is a run of consecutive items of the pass's item list inside one block, with the same KV-write flag. The unit table (`unit_start[]`) holds the first item of every unit. A unit never crosses a page, a 16-token block or a change of the KV-write flag. |
| minibatch, item, KV-write flag | A minibatch (`batch` in the code) is one group of a pass's token jobs. Its items are the token jobs of the pass. A generated plugin has one minibatch per pass, so the minibatch holds the whole pass. The KV-write flag (`token_jobs_do_kv`) says whether an item writes K and V. |
| main thread, main helpers, worker index, n_workers | The main thread runs the schedule of a generated plugin. The main helpers are the threads of that plugin that run the per-token kernels. The worker index (`worker_ix`) is 0 for the main thread and 1 to n_workers - 1 for the helpers. `n_workers` is the count of main plus helpers. The defaults 0 and 1 store every row on the calling thread. |
| window, claim counter, join, watchdog | A window is one shared store: the state that the main thread opens in `save_k` and that the helpers join (`batch::k_store_window`). The claim counter (`next_unit`) hands out unit indices to every thread. The counters `opened` and `finished` count the windows opened in the pass and the helpers done with the open one. The join is the main thread's wait for every helper to finish the open window. The watchdog is the main thread's check during the join: it reads the clock once every 2^20 pause loops and aborts with an error message that carries the counters when the join has not completed 120 s after the first clock read. |
| generated plugin, handwritten plugin, code generator, attention statement | A generated plugin is the model code that the code generator emits for an ingested model. A handwritten plugin is a model whose code is not generated. The code generator is tron's Haskell program (`ingest/src/TronCpp.hs`) that emits the generated plugins. The attention statement is the point of the generated schedule at which the main thread calls `save_k`. |
| LoopyTronSpec, cabal, Sydtest, fourmolu, lint-notes | `LoopyTronSpec.hs` is the code generator's test suite. cabal is the Haskell build tool. `bin/ingest-cabal test` runs the suite. Sydtest is its test framework. Its summary prints the counts of examples, passed and failed. fourmolu is the Haskell formatter. lint-notes is the repository's check that every `Note [...]` reference names a defined Note (a named comment block whose title line is underlined with tildes). |
| the option, CMake, preset | The option means `TRON_K_VNNI`, the CMake switch that selects VNNI K storage for every 128-dimension head. It defaults to OFF. No preset (a named CMake build configuration) enables it. |
| AMX dispatch | `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels and the code that selects them. |
| kill switch, AMX-on, AMX-off | The kill switch is `TRON_AMX_DISABLE=1`. It makes `amx_attn_h128g4::available()` false at run time. Then no AMX kernel runs and the reader scores every page. The store is the same with or without the switch. AMX-on allows those kernels when their other conditions hold. AMX-off disables them through this switch. |
| KV page, slot, geometry | A KV page is a 64-token unit allocated by the cache (`page` in the code). A slot is one persistent K/V storage region. Geometry means the head counts and dimensions. A packed slot uses packed K storage. A row-major slot stores K as contiguous rows. |
| KV head, kv_mul | A KV head is one key/value head. `kv_mul` means query heads per KV head. It is 4 heads for the qwen3-4b model. |
| prefill, decode, pass | A pass is one forward computation of the model over its current input. Prefill processes prompt tokens, usually many tokens per pass. Decode generates one output token per user per pass. A decode pass of the 8-user runs holds 8 items, so it is not shared. |
| owner, view | `k_vnni_tensor` owns one 16 KiB K plane as a 64-byte-aligned array. `k_vnni_view` refers to that plane. Views come only from an owner. |
| completion marks, dispatch credits | After the store, `save_k` marks each token's K as complete in its page and credits the dispatch counter of the token's attention group. The main thread does both after the join. |
| bf16, fp32 | bf16 is the 16-bit brain floating-point format used for K and Q. fp32 is the 32-bit IEEE single format. IEEE is the standards organization specifying these formats. |
| Catch2, REQUIRE, SECTION, CAPTURE, SUCCEED | Catch2 is the C++ test framework of the unit tests. REQUIRE is its assertion macro. Each evaluation counts as one assertion. A SECTION is a sub-part of a test case. Catch2 runs the case once per leaf section. CAPTURE prints named values when an assertion fails. SUCCEED records one passing assertion. A placeholder case contains only SUCCEED, when the tested code is not compiled in. |
| mutation check | A deliberate code change that a test must catch. The test's failure proves that the test can fail. This PR reports two. |
| poison pattern | A fixed value written over a buffer before a check, so that an untouched byte stays recognizable. The block-save case uses the bf16 bit pattern 0xa5a5. |
| tp2, tp4, slice | `tp2` and `tp4`, also written `-tp2` and `-tp4` in a model name, split the model across 2 or 4 devices. A slice is one FPGA with its share of the host's CPU cores and memory. |
| TPS, TTFT | TPS is decode throughput in tokens per second per user. TTFT is time to first token. The measurement tables report the maximum TTFT over all 8 users. |
| base, new, new2, newoff, head, headoff | `base` is `main` at commit `72308ec90c` (the layout PR's merge base, the `main` commit it is based on), built as runtron with row-major K and AMX dispatch on. `new` is this branch at commit `{{HEAD_SHORT}}`, built with the option and AMX dispatch on. `new2` is a second run of `new` (the A/A repeat). `head` is the kernel PR at commit `0ee8671d35`, built the same way as `new`. `newoff` and `headoff` run `new` and `head` with the kill switch. |
| greedy run, A/A repeat | A greedy run uses temperature 0, a setting that chooses the highest-scoring token. `--pay-for-determinism` performs sums in a fixed order. An A/A repeat runs the same configuration twice as a control. |
| cell, band, standard deviation, paired t | A cell is one model, parallelism, prompt length, and attention configuration. Standard deviation measures variation between repetitions. The band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. The paired t statistic expresses the mean paired difference relative to its uncertainty. It is dimensionless. |
| CI, GCP Nix, legacy CMake lane | CI means continuous integration, the automated build and test system. GCP Nix is the default build-and-test workflow, `gcp-nix.yml`. Its Test ingest job runs the Haskell suite. Its C++ test build uses `nix/cmake-tron-test-build.nix`. The legacy CMake lane is `.github/workflows/cmake-single-platform.yml`. It runs by manual dispatch and from `publish-deb.yml`, the package-publishing workflow. |
| runner, Granite Rapids | A runner is a machine that executes CI jobs. Granite Rapids is the Intel CPU family of the Xeon 6962P test machine with AMX. The Granite Rapids machine below means that machine. |
| slice check, cost data | `bin/slice bench --check` checks registered tests for timing records in `config/test-benchmarks.json`. These records are cost data: test durations at 1, 2, and 4 slices. |
| worktree, translation unit | A worktree is a separate checkout used for one build. A translation unit is one source file after its included headers have been expanded. |

## The changes

The owner's header adds the block store. [h/tron/tensor/k_vnni.hpp]

- `store_block` takes the writable plane view, the block index c, the present mask and 16 row pointers. It checks the block index against the plane's block count, as `store_row` checks its token index. For each of the 4 dimension steps it loads one 64-byte line per present row (an absent row's pointer may be null and is not read), transposes the 16 registers in place and writes the panel's 16 pair rows as 64-byte stores, masked to the present lanes when the block is partial. Compared with `store_row` per token, a full block issues 64 whole-line stores instead of 64 scatters that each write 4 bytes into 16 lines. The same 4 KiB is written.
- `transpose_16x16_epi32` is the in-place transpose of 16 registers of 16 dwords: four stages of two-register shuffles, 64 shuffles in all.
- Two constants name the full mask (`FULL_BLOCK_0XFFFF`) and the dword count of one register (`LANES_16`). Two compile-time assertions tie the block size and the step size to the lane count.
- The comment above `store_row` says that only the token's own 64 slots are written, so that several threads may store different tokens of one plane at the same time. The operation lists name `store_block`.

The cache header adds the page accessor and describes the two store paths. [h/tron/models/kv_cache.hpp]

- `page::set_k_block` takes the slot, the KV head, the block index, the present mask and the 16 row pointers. It checks the block index against the page size (4 blocks) and calls `store_block` on the typed view. It exists for packed slots only.
- Note [K VNNI storage] (the named comment block that documents the layout) item 1 describes the two store paths of `save_k`: the block save for a run of 2 to 16 consecutive tokens of one block, the per-row store for a run of one token, and the sharing with the idle main helpers for a pass of more than 16 tokens. The kill switch leaves both paths untouched. The typed-operations list names `store_block`.

The batch gains the window state. [h/tron/models/common.hpp]

- `batch::k_store_window_t` holds the claim counter `next_unit` on its own cache line (a claim must not invalidate the line the waiting threads poll), the counters `opened` and `finished`, the unit count, the unit table of `max_minibatch_size + 1` entries, and `helper_windows`, one counter per helper of the windows it has entered. The size of that array, 128, bounds the worker count of a shared store. One window state exists per minibatch, 1,088 bytes plus the unit table.

The model header holds the store and its protocol. [h/tron/models/model.hpp]

- Note [Shared block save] states the protocol and the deadlock argument.
- `k_store_shared` decides whether a window exists: the option on, 1 < `n_workers` <= 128, and more than 16 items. The main thread and every helper compute it from the same inputs, so a helper never waits for a window the main thread does not open.
- `k_store_cut_units` cuts the item list into work units. A new unit starts at the first item, at a change of the KV-write flag, at a change of page and at a change of 16-token block. Only the main thread calls it, before it opens the window.
- `store_k_block` stores the K rows of the items of one unit, for every KV head. With the option on it builds runs of consecutive items in one block of one page (items without KV work are skipped and do not end a run; a repeated page offset ends it). A run of one token takes `set_k_row`. A run of 2 to 16 tokens takes `set_k_block` with the run's mask. A K row that is not bf16 is converted to bf16 on the stack first, through the same row view the per-row store uses. With the option off, every token takes the row-major row store, as on `main`.
- `save_k_impl` takes the worker index and the worker count. An unshared store is the main thread's alone: a helper returns at once. In a shared store the main thread cuts the units, resets the claim counter and `finished` to 0, and increments `opened` with release ordering. A helper's W-th call waits until `opened` reaches W with acquire ordering, so window W of a pass is the W-th shared `save_k` of that pass on both sides. Every thread claims units with an atomic add on the claim counter and stores each unit it claims. A helper increments `finished` with release ordering when its claim loop ends and returns. The main thread waits until `finished` equals `n_workers - 1` with acquire ordering. Every row store therefore happens before the main thread continues. The watchdog runs inside that wait.
- The completion marks and the dispatch credits stay on the main thread, after the join, in item order, one token at a time.
- The deadlock argument: the main thread waited for every token's K channel before it called `save_k`, and the channel phase cannot advance while it is inside `save_k`. A helper reaches its `save_k` call without the main thread's help, because nothing blocks between its rope kernel (the kernel that rotates the K rows) and the attention statement. So the join cannot wait for a helper that waits for the main thread.
- The two `save_k` overloads take `worker_ix` and `n_workers` with the defaults 0 and 1. The handwritten plugins and the unit tests pass the defaults and store on the calling thread.

Note [QK orientation] in the kernel interface names the two store paths as the places the extra work of the flipped orientation moves to. [h/tron/kernels/amx_attn_iface.hpp]

The code generator emits the helpers' call. [ingest/src/TronCpp.hs]

- For an attention statement whose operation writes KV, the helper function `run_main_help` calls `save_k` with the helper's `worker_ix` and the worker count `n_workers` of that function, at the same position of the statement list at which the main thread calls it. The main thread's call passes 0 and `n_workers`. An operation without a KV write emits nothing on the helper side.

The generator's test suite checks both call texts. [ingest/test/LoopyTronSpec.hs]

- In the two specs that count the attention calls, a KV-writing operation emits two `save_k` calls. The main-side call text ends in `,0,n_workers);` and the helper-side call text in `,worker_ix,n_workers);` after whitespace removal. The second operation of the shared-slot spec, which writes nothing, emits no call.

Tests change as follows:

- `t_k_vnni_layout`, the test of the packed layout, gains the case "VNNI K block save equals the per-token row store, bit for bit".
  - For each of the 4 blocks and 38 masks (14 fixed masks: the full block, the empty block, single tokens, halves, alternating lanes and mixed patterns; 24 random masks) it stores the same rows with `store_row` and with `store_block` into two planes filled with the poison pattern, and compares the planes bit for bit: 152 comparisons.
  - The poison outside the block proves that the block save touches no other block.
  - The case calls `store_block` on an owner directly, so it runs whatever the option is.
- `t_llama_unit`, the model and cache unit-test binary, rewrites the `save_k` case as "save_k stores every token's K row once, grouped by page block, alone or with helper threads", with two sections over the same 48-item pass (a run that starts in the middle of a block, runs that cross a block boundary and a page boundary, a whole block, a token alone in its block, and jobs without KV work inside and after a run).
  - One thread: the grouping stores every row bit for bit, touches no other row of the book, marks every KV job once, and opens no window.
  - Three threads: two helper threads and the main thread call `save_k` with their worker indices, on the operations of both layers in turn, so that the batch sees two windows. The rows and the marks are checked the same way after each window. With the option on, the window state is checked too: the window count, the finished-helper count, each helper's own window count, the claim counter at the unit count plus the worker count (every claim loop ran to exhaustion), and the unit table. Every unit lies inside one page, one 16-token block and one KV-write flag value. A new unit starts only at a change of one of those, so the units are the maximal runs.
  - With the option off, both sections run the row-major store and no window opens.

This PR ships the masked partial-block path: `store_block`'s masked branch, the present mask of `set_k_block`, and the one-token branch of `store_k_block`. The fourth PR of the stack replaces it with the row-major tail block. [Open items below]

## Measurements

The measurements compare TTFT and decode TPS with the option on against the kernel PR's binary, and against `main`. They also measure the store under the reader, the kill switch inside this PR, and the kernel PR against `main` in the same session.

Configurations:

- `base`: `main` at `72308ec90c`, built as runtron with row-major K and AMX dispatch on.
- `new`: this branch at `{{HEAD_SHORT}}`, with the option and AMX dispatch on.
- `head`: the kernel PR at `0ee8671d35`, built the same way as `new`.
- `newoff` and `headoff`: those two binaries with the kill switch.

The experiment ran on {{E_DATE}}:

- Model: qwen3-4b, at tp2 and at tp4.
- Load: 8 users and 256 generated tokens.
- Attention: CPU, selected by `USE_HW_ATTN=0`.
- Cells: tp2 with prompt lengths 1,024 and 8,192 tokens, and tp4 with prompt length 1,024 tokens.
- Repetitions: 3, with the binaries run in alternating order.
- Allocation: the whole Granite Rapids test machine with production serving stopped (the tp4 cell needs its four FPGA cards and 256 huge pages).

`base` and `head` are measured at tp4 for the first time at these revisions.

The decision band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. Bands are shown rounded to 0.01 TPS and 0.01 s. A difference beyond that band counts as a change. Paired t uses the 3 repetitions.

Each parenthesized value is the sample standard deviation over the 3 repetitions. TPS has units of tokens/s/user. Both TTFT and its standard deviation have units of seconds.

| Cell | Binary | TPS (tokens/s/user) | TTFT (s) |
|---|---|---|---|
{{ARM_ROWS}}

"Inside" and "beyond" refer to the decision band. The paired t values are dimensionless.

| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
{{PAIR_ROWS}}

### The TTFT gain of the block save (new vs head)

The kernel PR's description lists the per-row scatter store's cost in TTFT as an open item, and says that this PR is intended to remove it. [PR #4887, Open items] `new` and `head` differ only in the store: the layout, the kernel and the reader are the same.

{{TTFT_GAIN}}

{{TTFT_GAIN_TEXT}}

### Decode TPS against the kernel PR (new vs head)

A decode pass of the 8-user runs holds 8 items. That is not more than 16, so no window opens, and each item is a run of one token that takes the per-row store, as in the kernel PR. The store path still differs in three ways: a grouping pass runs before the scatter, the completion marks run in a separate loop, and every helper calls `save_k`, evaluates the sharing predicate and returns. The expectation is a TPS difference inside the band. The measured pair decides.

{{TPS_HEAD}}

{{TPS_HEAD_TEXT}}

### This PR against `main` (new vs base)

{{AGAINST_MAIN}}

{{AGAINST_MAIN_TEXT}}

### The store under the reader (newoff vs headoff)

Both binaries run the reader for every page with the kill switch. The store does not depend on the attention path, so the expected TTFT gain is about the same absolute size as `new` against `head`. A decode TPS difference beyond the band needs investigation, including the three store-path differences named above. The measurement that would settle one: the K-store spans of a Perfetto trace (tron's timing trace) of the same decode workload for both arms.

{{READER_STORE}}

{{READER_STORE_TEXT}}

### The kill switch inside this PR (newoff vs new)

The store is the same with or without the switch. The expectation is the kernel PR's measurement of its own binary: TPS -11.0 % and -18.3 %, TTFT +674 ms and +64.9 s, at tp2 prompt lengths 1,024 and 8,192 tokens. [PR #4887, Measurements]

{{KILL_SWITCH}}

{{KILL_SWITCH_TEXT}}

### The kernel PR against `main` in this session (head vs base)

This pair repeats the kernel PR's claim in the same session as the other pairs. The kernel PR measured TPS +5.4 % and +9.5 % and TTFT +100 ms and -523 ms at tp2 prompt lengths 1,024 and 8,192 tokens on 2026-10-11. [PR #4887, Measurements] A deviation beyond the bands says that the machine's speed changed between the two sessions, which qualifies every other pair of this run.

{{HEAD_BASE}}

{{HEAD_BASE_TEXT}}

## Verification

Build provenance:

- Machine and date: Granite Rapids, Intel Xeon 6962P with AMX, {{BUILD_DATE}}.
- Revision: `{{HEAD_SHORT}}`, based on the kernel PR at `0ee8671d35`, which is based on the layout PR at `82d05e94be`, which includes `main` at `72308ec90c`.
- Environment: `nix develop`, the project's pinned build shell.
- Compiler: clang version 19.1.7.
- Preset: `native` (Ninja, clang-19, ccache, lld, build type `RelWithDebInfo`). The AVX-512 flags are explicit in `src/tron/CMakeLists.txt` and do not depend on the preset or on the build host.
- Build type: `RelWithDebInfo`, an optimized build with debug symbols.
- Each of the 3 configurations used a separate worktree.

`BUILD_INGEST_MODELS` controls compilation of the models produced by the ingest pipeline (the project's model conversion step).

| Configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | Targets | Build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | {{BUILD_PR3}} s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | {{BUILD_PR3ND}} s |
| option off | OFF | ON | OFF | the 6 tests below without `t_phase1_integration` | {{BUILD_PR3RM}} s |

`t_heterogeneous_scheduler` tests scheduling across different attention geometries. `t_k_vnni_layout` tests the packed layout, its row and block operations and the reader. `t_phase1_integration` tests staging (the copy of K and V into buffers read by the FPGA) and dispatch integration.

The following unit-test binaries passed with a fake device (a simulated FPGA). `--skip-benchmarks` excluded their benchmark sections. Each result gives assertions / test cases.

| Test | Option on | Option on, no AMX dispatch | Option off |
|---|---|---|---|
{{TEST_ROWS}}

`t_k_vnni_layout` reports 5 test cases in every build: the block-save case runs whatever the option is. The `save_k` case of `t_llama_unit` runs both sections in every build. With the option off it runs the row-major store and opens no window. The identity case of `t_amx_numerics` (the kernel PR's bit-identity check of the AMX kernel) ran on real AMX in the option-on build and in the option-off build. Neither `t_amx_numerics` run printed an "AMX unavailable" line.

Kill-switch results in the option-on build:

{{KILLSWITCH_LINES}}

Two mutation checks ran in the option-on worktree.

- The block store: the panel address of `store_block` was changed so that block c's rows land in block c ^ 1's panels (`(s * TOKEN_BLOCKS_4 + c)` to `(s * TOKEN_BLOCKS_4 + (c ^ 1))`). The block-save case, run alone, then fails. {{MUTATION1}} With the file restored, `t_k_vnni_layout` passes again with {{RESTORED1}}.
- The work-unit cut: the block condition of `k_store_cut_units` was inverted (`block != run_block` to `block == run_block`), so that a run that crosses a block boundary becomes one unit and consecutive items of one block are cut into single-item units. The `save_k` case, run alone, then fails in its three-thread section at the unit invariant. {{MUTATION2}} With the file restored, `t_llama_unit` passes again with {{RESTORED2}}.

The Haskell suite ran on the test machine in the option-on worktree (`bin/ingest-cabal test`): {{HASKELL}}

The generated plugins were checked after the option-on build. For each of the 19 generated plugins, the count of `save_v` calls (one per KV-writing operation), of main-side `save_k` calls (argument list ending in `0, n_workers`) and of helper-side `save_k` calls (ending in `worker_ix, n_workers`) are equal and positive, no `save_k` call has another argument tail, and `save_k_helper` (the name of an earlier design) does not occur.

| Plugin | KV-writing operations | Main-side `save_k` calls | Helper-side `save_k` calls |
|---|---|---|---|
{{PLUGIN_ROWS}}

All of these checks pass at `{{HEAD_SHORT}}`:

- clang-format version 19.1.7, the source formatter, with `--dry-run --Werror` on all 7 changed C++ files.
- fourmolu in check mode on the 2 changed Haskell files, with the repository's hook options.
- `git diff --check`, the whitespace check, against the kernel PR's head.
- A search for the prohibited `<cassert>` header in the diff.
- {{LINT_NOTES}}

Syntax-only compilation used clang version 19 with the product's compile flags. It covered 38 configurations with 0 errors and 0 warnings:

- All 4 combinations of AMX dispatch on/off and the option on/off for 9 translation units: `t_llama_unit`, `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `heterogeneous_scheduler_compile` (heterogeneous scheduling compilation), `scheduler/full.cpp` (the full scheduler), `gof.cpp` (staging), `t_gof_dma` (staging DMA, direct memory access transfers), and `t_kv_oom_subcases` (out-of-memory cases).
- `kernels/amx_attn.cpp` (the AMX kernels) with dispatch on and the option on/off.

The compiler flag is `-fsyntax-only`. The Haskell files are outside this check. Their compile is the Haskell suite above.

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
- `new` must match `head` for all 256 generated tokens in each cell. This is the correctness claim of the PR: the block save writes the same bytes as the per-row store, and the sharing changes only which thread writes them.
- `newoff` against `new` is expected to repeat the kernel PR's result: identical at prompt length 8,192 tokens with CPU attention and at 1,024 tokens with FPGA attention, and a first difference at generated token 247 at prompt length 1,024 tokens with CPU attention. The kernel PR's forced-run check showed an exact tie of the two best tokens at that step, decided by one bf16 step of the AMX-versus-reader numerics. This PR changes no score path. [PR #4887, Verification]
- The comparison with `base` is informational. [Issue #4444]

Host-suite result:

{{HOST_LINES}}

| Cell | new vs new2 | new vs head | newoff vs new | new vs base | head vs base |
|---|---|---|---|---|---|
{{SMOKE_ROWS}}

Outcome of the acceptance rules:

- Every binary exited with status 0 and produced 256 tokens in every cell.
- `new2` matched `new` in every cell.
- {{NEW_HEAD}}
- {{NEWOFF_NEW_V}}
- {{DIVERGENCE_V}}

### CI coverage

The GCP Nix test build enables neither `TRON_AMX_DISPATCH` nor `TRON_K_VNNI`. [nix/cmake-tron-test-build.nix]

- In that configuration the block-save case still tests the packed storage: it compares `store_block` against `store_row` on a `k_vnni_tensor` owner, whatever the option is.
- The `save_k` case runs both sections there with the row-major store. No window opens.
- The option-on paths of the store (`set_k_block` through `save_k`, the window and the shared store) run on the Granite Rapids test machine and in the legacy CMake lane, which compiles both options on. [.github/workflows/cmake-single-platform.yml]
- The Haskell suite runs in the required CI's Test ingest job once the PR is not a draft. It ran on the test machine as reported above.
- At review time, this PR is a draft without the `Run CI` label. GCP Nix runs its lint and infrastructure checks only. {{CI_STATUS}}
- The author explicitly accepts this limitation for this PR. Issue #4865 tracks enabling both options in the required test build.

## Open items

**The masked partial-block path.**

- A run of 2 to 15 present tokens of one block is stored with masked line stores: `store_block`'s masked branch, the present mask of `set_k_block`, and the one-token branch of `store_k_block`, about 15 lines in all.
- This is the tested form of the store, with the measurements above.
- The fourth PR of the stack replaces it with the row-major tail block: a run shorter than a block is stored row by row into a row-major block, which converts to the packed layout when all 16 rows are saved. The mask parameter goes with it.

**The single-token store of decode steps.**

- A run of one token, as in every decode step, keeps the per-row scatter store: 4 scatters that touch 64 lines per (token, KV head) row.
- Under FPGA attention that per-token column access is the decode loss of issue #4500. The fourth PR's row-major tail block is its subject.

**The join watchdog and the worker cap.**

- The main thread aborts the process when a shared store's join has not completed 120 s after its first clock read. The message carries the finished-helper count and the claimed-unit count.
- A pass with more than 128 workers stores on the main thread alone (`helper_windows` has 128 entries). The runtime's split heuristic sets the worker count once per pass. The traced runs used 8 and 9 workers.

**128-dimension heads with kv_mul other than 4 query heads.**

- The kernel serves kv_mul 4 only. Other groups retain the packed layout and use the reader wherever `main` uses the dotter, as in the kernel PR. The store does not depend on kv_mul.
- Decode TPS of those groups is not measured at `{{HEAD_SHORT}}`. No AMD host is measured at this head either.
- The measurement that settles it: decode TPS of llama-3.2-3b (kv_mul 3) and qwen-3-30b-a3b (kv_mul 8) at this head against `main` at `72308ec90c`, 3 repetitions, the band rule of the Measurements section.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]**

- With the option on, the kill switch gives an AMX-off run of the same binary through the reader. It does not reproduce the tokens of a clean binary, meaning a build with both options off. The store is the same with or without the switch.
- {{DIVERGENCE}}
- {{NEWOFF_NEW}}
- The rollback contract (the documented promise of what the kill switch restores) promises AMX off with the same AVX dotter and clean-binary numerical results. A packed binary with the switch runs the reader, not the dotter. [Item 4 of Note [AMX attention dispatch], h/tron/kernels/amx_attn_iface.hpp]
- Issue #4444 records two choices:
  1. Accept the narrower rollback contract. Add "with `TRON_K_VNNI` off" to item 4.
  2. Keep a row-major binary as the deployment rollback artifact. Document that requirement.

**A control difference beyond the band.**

- `newoff` against `headoff` at tp2 prompt length 8,192 tokens: {{CTRL_8192}} Both binaries run the reader for every page, and the store's work is the same on both sides of the switch. The store's expected effect at this prompt length is the `new` against `head` difference of the same cell, which is smaller. The cause is not measured.
- The measurement that would settle it: the K-store spans of a Perfetto trace (tron's timing trace) of one 8,192-token prefill for both arms, and a repeat of the cell with 5 repetitions.

**Cost data of t_k_vnni_layout and t_llama_unit.**

The block-save case and the three-thread section add run time to `t_k_vnni_layout` and `t_llama_unit`. Their Granite Rapids rows in `config/test-benchmarks.json` are not refreshed here. The refresh is planned with the fourth PR's cost-row update. The slice check needs a timing row in at least one platform block, and both binaries have rows. The check is therefore expected to pass. Not run at `{{HEAD_SHORT}}`.

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
