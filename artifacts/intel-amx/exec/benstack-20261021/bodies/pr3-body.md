## Short version

This PR is PR #4958 (the 16-token block save of VNNI-packed keys, shared between the main thread and the idle helper threads) re-expressed on the structure of PR #5047, in which the cache alone knows the K layout. One `page::set_k_block` serves every slot and chooses the physical store inside the cache, so the model code holds no layout code. The shared store becomes a phase of a `tron::barrier`, the project's existing resettable barrier, in place of hand-written counters and a 120 s abort.

## Background

PR #4958 writes the K rows of up to 16 tokens of one block as whole cache lines after a register transpose, and lets the idle helpers of a generated plugin share that store with the main thread. That is the time-to-first-token gain of the stack. Its model code decides the layout at each store (`k_vnni::layout_on`, a present mask, a scatter run length) and drives the helpers with its own counters (`opened`, `finished`, `helper_windows`) and a clock-based join.

PR #5047 removes every layout decision from the model code, and `tron::barrier` already provides the phase protocol the shared store needs (Note [Resettable Barrier Design] in `h/tron/threading.hpp`). This PR keeps PR #4958's store, its run scan and its tests, and expresses them with those two facts: the cache stores a block, and a barrier phase shares the work. Note [Shared VNNI K store] in `h/tron/models/model.hpp` states the protocol and the deadlock argument.

## Words used here

| Term | Meaning |
|---|---|
| the cache | h/tron/models/kv_cache.hpp: `struct page` (one 64-token KV page) and `struct book` (the pages of one model instance) |
| the model code | h/tron/models/model.hpp, the per-layer code that stores K and V rows and marks tokens complete |
| the option | the CMake option TRON_K_VNNI. When it is on, the K cache of 128-dimension heads is stored in the AMX VNNI layout |
| a VNNI slot | a K storage slot that uses that layout. A row-major slot stores one token's row after another |
| a block | 16 consecutive tokens of a KV page, one AMX tile width. The store granule is `page::k_block_tokens` |
| the block save | `page::set_k_block`: the K rows of up to 16 tokens of one block stored as whole 64-byte lines after a register transpose (`store_block` in h/tron/tensor/k_vnni.hpp) |
| the per-row store | `page::set_k_row` into a VNNI slot: 4 scatters of 4 bytes into the token's 64 lines |
| the main thread, the helpers | the threads of a generated plugin (the model code the generator ingest/src/TronCpp.hs emits): worker 0 runs the schedule, workers 1 to n_workers - 1 run the per-token kernels |
| the barrier | `tron::barrier` (h/tron/threading.hpp), a resettable barrier with `next_phase`, `wait`, `done` and `wait_for_all`. `batch::k_store_barrier` is the one the shared store uses |
| a work unit | a run of consecutive items of one block of one page, the unit a worker claims through `greedy_range` |
| the syntax matrix | 22 compiler runs (two generated trees x the option off/on x five test files, plus the AMX kernel file) that parse and instantiate the code without linking or running it |
| 3bda | delphi-3bda, the Intel server where the builds and unit tests run |

## How to review this PR

**Does the model code hold no layout code, and does the cache choose the physical store?**
- `h/tron/models/kv_cache.hpp`: `page::set_k_block` is one operation for every declared geometry. It takes the rows of up to 16 tokens of one block as typed row views in a `std::array`. An absent lane is an invalid view. A VNNI slot scatters one valid row with `store_row` and transposes two or more valid rows with `store_block`. A row-major slot stores each valid row in place. Rows of a scalar type other than bf16 are converted on the page's own stack, as `set_k_row` converts one row.
- `h/tron/models/model.hpp`: `store_k_block` is one loop over the runs `next_k_run` finds and makes one `set_k_block` call per run and KV head, for every slot layout. The one layout fact the file keeps is `page::k_store_scatters`, which decides whether the store is shared. The file holds no `k_vnni::` symbol, no lane mask type and no conversion buffer.
- `h/tron/tensor/k_vnni.hpp`: `store_block` takes the typed row views `store_row` takes. The page overload that took 16 raw pointers and a mask no longer exists.
- Verification: the save_k case of `t_llama_unit` reads every K row of the slot back through `page::get_k_row` after a save with one thread and after a save with three threads. It compares each stored row with its source bits and requires every other row unchanged. `t_k_vnni_layout` compares `store_block` bit for bit with the scatter store.

**Does the barrier phase pair every helper with its phase, and can it deadlock?**
- `h/tron/models/common.hpp`: `batch::k_store_barrier` is a `tron::barrier`, and `batch::k_store_units` is the unit table. `reset_channels` resets the barrier with the main worker count.
- `h/tron/models/model.hpp`, `save_k_impl` and Note [Shared VNNI K store]: main cuts the units, opens the phase, stores its share, calls `done` and waits for all. A helper waits for its phase, stores its share and calls `done`. `k_store_shared` gives the same answer on every thread, so a helper never waits for a phase main does not open. Every thread claims units with `greedy_range`.
- `ingest/src/TronCpp.hs`: the generated `run()` calls `reset_channels` with the worker count before it launches the helpers. Main and every helper call `save_k` at the same statement with that count.
- `h/tron/threading.hpp`, Note [Resettable Barrier Design]: a helper's W-th `wait` meets the W-th phase. Main cannot open phase W + 1 before every participant called `done` for phase W.
- Claim: threads whose `save_k` call counts differ wait instead of aborting after 120 s, and the `TRON_LATCH_WATCHDOG` environment variable logs the latch states. The cap of 128 workers on sharing is gone with the per-helper window array.
- Verification: the save_k case of `t_llama_unit` calls `reset_channels(0, 3)` and drives one phase with main and two helper threads. It checks the bytes right after main's `save_k` returns and before it joins the helpers. So the production wait, not the join, must have seen the helpers' stores. A generated plugin with main helpers at this head is the run under Pending measurement.

**Are the stored bytes and the unit boundaries those of PR #4958?**
- `h/tron/models/model.hpp`: `k_store_cut_units` cuts a unit at a change of page, block or KV flag, as PR #4958 does. `next_k_run` is PR #4958's run scan over a span of items. Both read the item list only.
- `h/tron/models/kv_cache.hpp`: the VNNI branch of `set_k_block` calls the `store_row` and `store_block` of PR #4958 with the mask of the valid lanes, which PR #4958 computed in the model code.
- Verification: the save_k case asserts the unit boundaries and the claim counter (one failed claim per worker after the last unit). `t_k_vnni_layout` and the byte check above cover the bytes. The time-to-first-token cells are under Pending measurement.

## Verification

Head `2c501a9390` is PR #4958's head `b39765ec29` merged with the second PR of the stack at `9a8045836a` (which carries PR #5047's head `ade89a9d9c`), followed by four commits. The merge has 4 conflict hunks and one hunk that merged without a marker and did not compile (the row-major store called a page operation that no longer exists). The syntax matrix runs on the development host with zig clang 19 at the head. The builds and unit tests run on 3bda on 2026-10-21 with clang 19, the `native` preset, `BUILD_INGEST_MODELS` and `TRON_AMX_DISPATCH` on, in two configurations: `bp3` (the option off) and `bp3v` (the option on). No performance run exists at this head. PR #4958's table is measured at `80bce9a08d`.

### Builds and tests

The syntax matrix is clean at the head: 22 cells, 0 errors, 0 warnings. Every commit of the branch passes it on its own. It proves parsing, template instantiation and every `static_assert`, and nothing about object code, linking or run time.

Clean: clang-format on the 15 changed C++ files, `git diff --check`, no `<cassert>` in the diff, no issue or PR number in a new comment. The two Haskell changes are comment lines only.

Unit tests on 3bda (fake device, `--skip-benchmarks`, software attention):

BDA_TABLE_PR3

### Pending measurement

- Question: does this head keep PR #4958's time-to-first-token gain and its decode throughput?
- Comparator: PR #4958's head `b39765ec29` built the same way (its own table is measured at `80bce9a08d` on PR #4957 at `0ee8671d35`: against the kernel PR, time to first token falls by 153 ms at tp2 and 243 ms at tp4 at prompt 1,024 tokens, decode throughput inside the band).
- Cells: qwen3-4b, 8 users, 256 generated tokens, CPU attention: tp2 at prompt 1,024 and 8,192 tokens, tp4 at prompt 1,024 tokens.
- Expected verdict: inside the band. The stored bytes, the run scan and the sharing condition are those of PR #4958. The barrier phase replaces a spin on two counters with a spin on one latch per phase.

## Open items

**Two run definitions. Reviewers decide.** `k_store_cut_units` cuts the work units, and `next_k_run` scans the runs inside a unit with a guard against a repeated page offset. One definition for both would change the unit boundaries the save_k case asserts. Whether one should serve both is open.

**Performance at this head.** The run under Pending measurement. The session owner runs it after the stack's three drafts are gated. One inherited fact for the CPU cells: PR #5047's own kill-switch cell (llama-3.1-8b, prompt 8,192 tokens, every K token through the software scoring loop) measures prefill +2.9 % against its base. This head inherits that loop.

STACK_SECTION

🤖 Generated with [Claude Code](https://claude.com/claude-code)
