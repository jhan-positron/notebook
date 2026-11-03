## Short version

This PR is PR #4959 (the row-major tail block: rows saved below a whole block stay row-major and convert to the VNNI layout at the end of the pass that completes the block) re-expressed on the structure of PR #5047, in which the cache alone knows the K layout. The dense-page gate and the scoring of unconverted blocks move inside the cache's two scoring operations, the pending-block record becomes a type the page owns, and the tests reach K only through page operations. The `deb` preset change that turns the layout on in the released package is a commit of PR #4959 itself and is not part of this diff.

## Background

PR #4959 keeps the CPU attention loop and the FPGA staging path aware of the per-block layout: the attention code checks that every block of a page is converted before the AMX path and scores unconverted tokens with its own dotter loop, and the staging path takes a raw pointer into a row-major block. PR #5047 moves these decisions into the cache and copies every staged K row.

This PR keeps PR #4959's storage state, its conversion at the end of the pass and its hardware-attention policy, and expresses them behind `page::score_k` and `page::try_score_k_amx`. Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp` and Notes [K VNNI storage] and [Row-major blocks under hardware attention] in `h/tron/models/kv_cache.hpp` explain the mechanism. This PR drops the staging pointer path of PR #4959 and keeps PR #5047's copy [Open items].

## Words used here

| Term | Meaning |
|---|---|
| the cache | h/tron/models/kv_cache.hpp: `struct page` (one 64-token KV page) and `struct book` (the pages of one model instance) |
| the attention code | h/tron/models/self_attention.hpp, the CPU attention loop that calls the cache |
| the model code | h/tron/models/model.hpp, the per-layer code that stores K and V rows and marks tokens complete |
| the option | the CMake option TRON_K_VNNI. When it is on, the K cache of 128-dimension heads is stored in the AMX VNNI layout |
| a VNNI slot | a K storage slot that uses that layout. A row-major slot stores one token's row after another |
| a block | 16 consecutive tokens of a KV page, one AMX tile width. The store granule is `page::k_block_tokens` |
| a converted block | a block of a VNNI slot whose rows are in the VNNI layout. An unconverted (row-major) block holds its rows one after another until the conversion at the end of a pass |
| a dense page | a full 64-token page that the query sees whole. It is the only page shape the AMX path scores |
| the dotter | `dotter` in h/tron/kernels/dotter.hpp, the AVX-512 dot-product loop of software attention. It scores one token's row at a time |
| hardware attention | attention computed on the FPGA. The staging path (h/tron/scheduler/full.hpp, h/tron/gof.hpp) copies K and V rows out of the cache for it |
| the kill switch | TRON_AMX_DISABLE=1, which turns the AMX attention path off at run time and keeps the layout |
| the syntax matrix | 22 compiler runs (two generated trees x the option off/on x five test files, plus the AMX kernel file) that parse and instantiate the code without linking or running it |
| 3bda | delphi-3bda, the Intel server where the builds and unit tests run |

## How to review this PR

**Does the cache alone decide the dense-page gate and the scoring of a page with row-major blocks?**
- `h/tron/models/kv_cache.hpp`: `page::try_score_k_amx` declines a VNNI slot unless its four blocks are converted. It returns false and leaves the scores and the storage untouched. `page::score_k` splits the live-token mask by the converted-block bits. The tokens of converted blocks go to `k_vnni::qk_group` (the AVX-512 reader of the VNNI layout). The tokens of row-major blocks and of row-major slots go to the dotter through one `score_rows` lambda.
- `h/tron/models/self_attention.hpp`: PR #5047's token loop fills one 64-bit live mask and calls `score_k` once. `apply_dense_amx_page` returns the cache's answer. The file names no layout.
- `h/tron/models/model.hpp` and `h/tron/scheduler/full.hpp`: no layout symbol on any code line. `model.hpp` names `page::k_block_tokens` only.
- Claim: a declined visit costs the 1 KiB zero fill of the score buffer that precedes the call. A page declines in the pass between the run that completes its last block and the forward end, and on every visit while a block stays row-major under hardware attention.
- Verification: the dispatch test (`t_amx_dispatch_dtype`, which counts calls of stand-in kernels) expects one pack and no kernel call for a full page with unrecorded rows with the option on, and one pack, one QK and one PV call for a full page with recorded rows under either value of the option. The scores of a page with both block kinds are under Pending measurement.

**Is the block state right at every point of a pass: saved rows, converted blocks, the conversion at the forward end, page copies and forgets?**
- `h/tron/models/kv_cache.hpp`: `set_k_block` with 16 valid rows stores the block transposed and records its 16 row bits and its block bit. Fewer rows go through `set_k_row`, which follows the block's recorded layout and leaves the row bit to `save_k`. `note_k_row_saved` records one row and answers a `k_pending_block` when the row completes an unconverted block. `k_block_to_vnni` converts from that record. `k_plan_copy` and `copy_k_rows` carry the bits with the rows of a page copy, and `k_forget_row` converts a block back when a live row stays below the forgotten offset. Note [K VNNI storage] states the four points at which a block changes its layout.
- `h/tron/models/model.hpp`: `save_k` records a row inside the loop that marks it complete. `convert_pending_k_blocks` converts the recorded blocks at the forward end, after the staging drain.
- `h/tron/tensor/k_vnni.hpp`: `block_to_vnni` and `block_to_rows` are the two public conversions. The per-row operations of a row-major block are in namespace `detail`. Note [Row-major tail block] says why.
- Claim: the four read-modify-writes that publish the bits use `memory_order_release`. The `k_rows_saved_` field comment names every reader and what orders it [Open items].
- Verification: `t_k_vnni_layout`, the page cases (conversion at the 16th saved row and back on a forget, the EAGLE storage entry, forgets per slot, appends in three shapes) and the tensor case (a row-major tail block converts to VNNI and back, bit for bit). The save_k case of `t_llama_unit` checks the marks, the block bits and the conversion after a one-thread and a three-thread store.

**Does a block saved under hardware attention stay row-major, and does the staging copy read every row right?**
- `h/tron/models/model.hpp`, `save_k`: the record is skipped when `cached_operation_uses_hw` holds for the operation. So no block that decode completes under hardware attention is converted, at the forward end or by a page copy. Note [Row-major blocks under hardware attention] gives the reason.
- `h/tron/scheduler/full.hpp`, `k_head_fn`: every staged K row is copied through `page::get_k_row`, which reads the row in the block's recorded layout. No pointer into K storage leaves the cache.
- Claim: the copy is one 4-line read and 256 bytes per row for a row-major block, and a 64-line gather for a converted block.
- Verification: the hetero test (`t_heterogeneous_scheduler`, source `t/heterogeneous_scheduler_compile.cpp`) converts the block a decode step completes at the forward end, and keeps it row-major when the hardware scores the operation. Two sections of the save_k case of `t_llama_unit` check that the policy is per operation. The FPGA cells are under Pending measurement.

## Verification

Head `38ad10f25c` is PR #4959's head `6b081187e1` merged with the third PR of the stack at `2c501a9390`, followed by 12 commits. The syntax matrix runs on the development host with zig clang 19 at the head. The builds and unit tests run on 3bda on 2026-10-21 with clang 19, the `native` preset, `BUILD_INGEST_MODELS` and `TRON_AMX_DISPATCH` on, in two configurations: `bp4` (the option off) and `bp4v` (the option on). No performance run exists at this head.

### Builds and tests

The syntax matrix is clean at the head: 22 cells, 0 errors, 0 warnings. It proves parsing, template instantiation and every `static_assert`, and nothing about object code, linking or run time.

Clean: clang-format on the changed C++ files, `git diff --check`, no `<cassert>`, no issue or PR number in a new comment. The two Haskell changes are comment lines only and arrive with the third PR.

Unit tests on 3bda (fake device, `--skip-benchmarks`, software attention):

BDA_TABLE_PR4

### Pending measurement

- Question: do the FPGA-attention cells keep PR #4959's decode gain with every staged K row copied, and does the cost of a declined visit show under CPU attention?
- Comparator: PR #4959's head `6b081187e1` built the same way. Its own table, measured at `ea94e95a4e`, shows +2.5 % TPS at tp2 and +12.1 % at tp4 under FPGA attention (qwen3-4b, 8 users, prompt 1,024 tokens), and the CPU cells inside the band.
- Cells: qwen3-4b, 8 users, 256 generated tokens. Under FPGA attention: tp2 and tp4 at prompt 1,024 tokens. Under CPU attention: tp2 at prompt 1,024 and 8,192 tokens, and tp4 at prompt 1,024 tokens. Token identity against PR #4959's head with 1 user at tp2, prompt 1,024 tokens, under CPU attention.
- Expected verdict: the FPGA cells inside the band against PR #4959's head. PR #5047's copy of every staged row measures inside the band against its own base in every FPGA cell (2026-10-21 campaign: +0.2 % and -0.8 % TPS). The CPU cells inside the band: the stored bytes, the conversion and the scoring loops are those of PR #4959. Identical tokens.

## Open items

**The staging pointer path.** PR #4959 lets the staging path read a row-major block in place through a raw pointer. This PR copies every staged K row, as PR #5047 does. A pointer path is a separate follow-up with its own FPGA cells, if the measurement under Pending measurement asks for it.

**The K layout state as a type. Reviewers decide.** `k_block_complete` and `k_block_converted` name the two bit tests at their nine sites. A `k_layout_state` type with named operations would replace the remaining bit arithmetic in the cache. Whether it belongs in this PR is open.

**The page-range emulation bound. Reviewers decide.** The page-range case of `t_llama_unit` compares the weighted V sum with an fp32 emulation while the PV product truncates each softmax weight to bf16, up to 0.03 per element (measured). Under the option this head uses the case's own 5e-2 bound from its split comparison. The alternative is a reference that truncates its weights the same way, with a bound near 1e-3.

**The memory order of the state writes. Reviewers decide.** The release order of the four state writes [How to review this PR, second question] rests on the field comment's argument: every reader runs after its writers were joined. No thread-sanitizer run checks it.

**Split before merging. Reviewers decide.** The diff separates into the tail block with its conversion and the hardware-attention policy. The `deb` preset change and the benchmark rows are PR #4959's own commits below this diff.

**Performance at this head.** The run under Pending measurement. The session owner runs it after the stack's three drafts are gated. One inherited fact for the CPU cells: PR #5047's own kill-switch cell (llama-3.1-8b, prompt 8,192 tokens, every K token through the software scoring loop) measures prefill +2.9 % against its base. This head inherits that loop.

STACK_SECTION

🤖 Generated with [Claude Code](https://claude.com/claude-code)
