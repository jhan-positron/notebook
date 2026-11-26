# Cutting 775bba7661 into Part 0 and Part A, and what the counters commit holds

## Short version
- 775bba7661 splits cleanly by file for 12 of its 15 files. Three files need a cut inside the file: `gdn_rolling_executor.hpp`, `gdn_execution.hpp` (one line) and `t/t_gated_delta_net.cpp`.
- Part 0 (P0, the chain kernel and `advance()`) must sit on the counters commit, because `advance()` takes a `gdn_stats::work_tally*`. Part A (PA, the AMX block kernel) then adds one enum, one parameter of `advance()`, and the AMX files.
- The counters commit 0d69ef3ce8 already defines and documents every chain and AMX counter. Ten of those keys have no production writer until 775bba7661.

Conventions: every line number is a line of the file at 775bba7661 unless another commit is named. Evidence commands: `git show 775bba7661 -- <file>`, `git show 775bba7661:<file>`, `git grep`. Nothing was built or run.

## 1. The 15 files of 775bba7661 (measured: +2488 / -100 lines)

| File | +/- | Class | Evidence / note |
|---|---|---|---|
| `h/tron/kernels/gated_delta_net.hpp` | +322/-4 | P0 | Blob c49f1fa914 equals the blob at WIP commit 64cde700af. See note N1. |
| `h/tron/models/gdn_stats.hpp` | +3/-2 | P0 | L23-24 name `gdn_recurrence_chain`; L143 says the executor checks the window size (the check is executor L253). |
| `h/tron/models/gdn_execution.hpp` | +28/-13 | MIXED | PA is L168 only. |
| `h/tron/models/gdn_rolling_executor.hpp` | +405/-48 | MIXED | PA ranges in section 2. |
| `t/t_gated_delta_net.cpp` | +444/-12 | MIXED | PA ranges in section 2. |
| `h/tron/kernels/amx_gdn_iface.hpp` | +161 new | PA | |
| `src/tron/kernels/amx_gdn.cpp` | +553 new | PA | |
| `t/t_amx_gdn_numerics.cpp` | +535 new | PA | |
| `h/tron/models/model.hpp` | +10/-3 | PA | L49, L1734, L1737, L1739-1745. |
| `src/tron/CMakeLists.txt` | +11/-9 | PA | L207-215 comment, L221-222 adds `kernels/amx_gdn.cpp`. |
| `t/CMakeLists.txt` | +6/-1 | PA | L690-695 adds `t_amx_gdn_numerics.cpp` to binary `t_amx_numerics`. |
| `CMakeLists.txt` | +1/-1 | PA | L46 option text names the GDN block kernel and `amx_gdn_iface.hpp`. |
| `README.ci.md` | +5/-3 | PA | L586-590 names `amx_gdn_iface.hpp`. |
| `h/tron/kernels/amx_attn_iface.hpp` | +2/-2 | PA | L4-5, comment only. |
| `src/tron/kernels/amx_attn.cpp` | +2/-2 | PA | L2-3, comment only. |

For every PA file, the Part 0 version is the file as 0d69ef3ce8 has it (for example `model.hpp` stays at blob 782a1d9e3a).

N1. `gdn_recurrence_window::normalized_query` (gated_delta_net.hpp L366, stored at L408-409, named in the Note at L339-340) is written in Part 0 code but read only by Part A code: executor L706-707, `amx_gdn.cpp:256`, `t_amx_gdn_numerics.cpp:91-110`. The chain kernel reads `scaled_query` only (L435, L470, L583). The old WIP Part 0 commit already carried the member. Keeping it in Part 0 leaves a stored field with no reader in PR 2.

## 2. MIXED files: PA line ranges and the Part 0-only form

### h/tron/models/gdn_rolling_executor.hpp (835 lines)

| Lines | PA content | Part 0-only form |
|---|---|---|
| 20-21 | includes `amx_attn_iface.hpp`, `amx_gdn_iface.hpp` | both includes disappear |
| 87-98 | `enum class gdn_block_kernel { off, when_available }` | enum disappears |
| 131-139 | Note paragraph "A full window can take the AMX block kernel" | paragraph disappears |
| 241-248 | `block_kernel_shape` with its `#ifdef TRON_AMX_DISPATCH` | disappears |
| 249-252 | comment, `static_assert(gdn_window_tokens == amx_gdn_k128v128::BLOCK_TOKENS_32)`, `static_assert(gdn_slice_chunks * chunk_size == amx_gdn_k128v128::SLICE_COLUMNS_64)` | both asserts disappear; the comment is reworded for L253 |
| 254-257 | `no_block_scratch`, `block_scratch_type` | disappear |
| 297-299 | member `working_set::block_scratch` (`tron_no_unique_address`) | disappears |
| 337-346 | `static bool block_kernel_available()` | disappears |
| 505 | parameter `gdn_block_kernel block_kernel` of `advance()` | disappears; signature is `advance(tokens, first_position, rows, tally = nullptr)` |
| 520-531 | `to_boundary`, `use_block_kernel`, `begin_tile_region()`, `tron::finally release_tiles` | disappear |
| 538 | `bool const block_window` | disappears |
| 547-552 | `if (block_window) advance_window_with_block_kernel(tally); else ...` | only the `gdn_recurrence_chain(...)` call of L550-551 stays |
| 559-560 | path is `amx_block` or `chain` | path is `gdn_stats::gdn_path::chain` |
| 563 | `if (full_window && !block_window)` | `if (full_window)` |
| 677-690 | `begin_tile_region()`, `end_tile_region()` | disappear |
| 691-735 | `advance_window_with_block_kernel()` (calls `pack_key_head`, `advance_value_head`, fallback `gdn_recurrence_chain_head`, counts `amx_blocks` / `amx_fallback_blocks` at L728) | disappears |

Stays in Part 0:
- L253 `static_assert(gdn_window_tokens == gdn_stats::BLOCK_TOKENS_32)`. Part 0 counts `chain_full_block_tokens` on that grid (L537, L563).
- L24 include of `gdn_stats.hpp`, the `tally` parameter (L511) and the stamps and tally writes at L540-566.
- `gdn_token_rows` (L61-76), `convolve_token` (L611-648), `prepare_window_token` (L650-675), `postprocess_window_token` (L736-745), the slice-layout working copy (L287-296, L361-368, L389-403, L426-432, L769-771), `postprocess(float*)` (L792-826).
- After the removals the file holds no text matching `amx`, `block_kernel`, `tile` or `finally` (text check on a scratch copy, not a compile).

### h/tron/models/gdn_execution.hpp (200 lines)
- PA: L168 `gdn_block_kernel::when_available,` only.
- Part 0-only form: `executor.advance(chain.order, chain.source_height.i, gdn_token_rows{...}, stats_enabled ? &tally : nullptr);`.
- P0: comment hunks L45-49, L59-61, L125-127; the `in_place` / `advance()` branch L162-171; the tally change L176-186.

### t/t_gated_delta_net.cpp (3009 lines)

| Lines | Item | Part |
|---|---|---|
| 25 | `#include "tron/kernels/amx_gdn_iface.hpp"` | PA |
| 2366-2390, 2397-2398, 2402-2404 | changed checks of the replay stats test (TEST_CASE at L2294) | P0 |
| 2589-2606 | `wide_chain_geometry`, `narrow_chain_geometry` | P0 |
| 2608-2643 | `chain_case_rows` | P0 |
| 2645-2658 | `chain_case_result` | P0, except L2656-2657 `recurrent_state_bytes` (read only at L2877-2887, a PA test) |
| 2660 | `no_value_head` | PA |
| 2662-2778 | `run_chain_case` | P0, except: L2667-2668 comment tail, L2672 parameter `block_kernel`, L2673 parameter `infinite_value_head`, L2678 `head_floats`, L2700-2705 infinity injection, the `block_kernel` argument at L2746 and L2760, L2776 |
| 2780-2783 | `same_floats` | P0 |
| 2785-2798 | `check_whole_matches_groups` | both. Callers L2874, L2935, L2981; none of the two pure P0 tests calls it |
| 2800-2812 | `check_advance_matches_step` | P0; the words "With the block kernel off" (L2800) and the argument `gdn_block_kernel::off` (L2807) are PA |
| 2814-2823 | `full_window_tokens` | both; only caller L2931 |
| 2825-2836 | `block_kernel_expected()` with `#ifdef TRON_AMX_DISPATCH` and `static_assert(amx_gdn_k128v128::shape_ok(...))` | PA |
| 2840-3009 | six TEST_CASEs | see section 4 |

Part 0-only form of the test file: no L25 include, `run_chain_case(first_position, n_tokens)` with two parameters, `from_checkpoint = first_position != 0`, three-argument... `advance(order, first_position, gdn_token_rows{...}, &tally)` calls without the kernel argument, no `block_kernel_expected()`, no `no_value_head`, no `head_floats`.

### Other files named in the task
- `model.hpp`, PA. L49 adds the include. L1734 moves `kernel_0_geometry` above the `#ifdef` (old L1739 at 0d69ef3ce8), but the new `#ifdef` code reads `gdn_kernels[0].geometry` directly (L1742-1743), so the move is not needed by it. L1737 shortens the comment that said "No AMX kernel serves GDN". L1739-1745 set `facts.amx_gdn_enabled = amx_gdn_k128v128::available()` under `if constexpr (shape_ok(...))`.
- `gdn_stats.hpp`, P0. Both hunks are comments (L23-24, L143). No symbol changes.
- `t/CMakeLists.txt`, `src/tron/CMakeLists.txt`, `CMakeLists.txt`, `README.ci.md`: PA as a whole. Each names `amx_gdn.cpp`, `t_amx_gdn_numerics.cpp` or `amx_gdn_iface.hpp`, files that do not exist in Part 0.

## 3. The small hunks in amx_attn_iface.hpp and amx_attn.cpp
- `amx_attn_iface.hpp` L4-5: "the only translation unit compiled with -mamx-tile/-mamx-bf16" becomes "which is compiled with ...".
- `amx_attn.cpp` L2-3: "The ONLY translation unit" becomes "One of the two translation units ... The other is amx_gdn.cpp."
- Both are comment-only. Part A needs them, because `amx_gdn.cpp` becomes the second file built with the AMX flags (`src/tron/CMakeLists.txt` L221-222).
- Part B (882e5322f1) does not need them and does not touch those lines. Its first hunks start at `amx_attn_iface.hpp` L13 and `amx_attn.cpp` L225 (`git show -U0 882e5322f1`).
- PR #5022's branch (ddf843ad97) still has the old text at these lines, the same as 72e1191804.
- Part A code uses these existing symbols of `amx_attn_h128g4`: `available()`, `begin_region()`, `end_region()`, `TILE_ROWS_16`, `TILE_ROW_BYTES_64` (`amx_gdn.cpp:12,19-20,154`; executor L682, L687). All exist at 72e1191804 (`amx_attn_iface.hpp:130-131,171,242-243` at 72e1191804).

## 4. TEST_CASEs of t/t_gated_delta_net.cpp that 775bba7661 adds or changes

| Line | TEST_CASE | Added / changed | Part | Block kernel use |
|---|---|---|---|---|
| 2294 | "GatedDeltaNet replay counts its work items, tokens and jobs in the GDN path stats" | changed (L2366-2404) | P0 | Does not name `gdn_block_kernel`. Reaches `advance(..., when_available)` through `run_gdn_operation` (gdn_execution.hpp L168). The kernel cannot run: `executor_geometry` is 16 by 80 (L1280-1286) and the long chain has 3 tokens (L2307). |
| 2840 | "... advance gives the bytes of step at the Qwen matrix shape" | added | P0 | Passes `gdn_block_kernel::off` through `check_advance_matches_step` (L2807). Never calls the block kernel. |
| 2851 | "... advance gives the bytes of step for narrower value heads" | added | P0 | Same as L2840. |
| 2863 | "... advance with the block kernel stays close to step" | added | PA | `when_available` (L2873). Calls the block kernel where AMX is available. |
| 2912 | "... advance gives full windows to the block kernel and counts them" | added | both | `GENERATE(off, when_available)` (L2926-2927), `block_kernel_expected()` (L2930). The `off` arm is the only test that checks `chain_full_block_tokens` above zero (L2942-2943). |
| 2955 | "... advance gives a refused block to the chain kernel" | added | PA | `when_available` with an infinite start value (L2972), `block_kernel_expected()` (L2983). |
| 2993 | "... advance needs a working copy" | added | P0 | Passes `gdn_block_kernel::off` (L3005). Aborts before any kernel runs. |

No test in `t/` calls `gdn_recurrence_chain` directly except `t_amx_gdn_numerics.cpp:229` (PA). Part 0 tests the chain kernel only through `advance()` against `step()`.

## 5. Counters commit 0d69ef3ce8: names for the chain and AMX paths, and their writers
Line numbers in this section are lines at 0d69ef3ce8.

| Symbol / key (gdn_stats.hpp) | Line | Writer at 0d69ef3ce8 outside tests | First production writer |
|---|---|---|---|
| `gdn_path::token` | 132 | yes, gdn_execution.hpp:166-170 | counters commit |
| `gdn_path::chain`, keys `chain_head_tokens`, `chain_recurrence_cycles` | 132, 134, 530-542 | none | 775bba7661 executor L559-565 (P0) |
| `gdn_path::amx_block`, keys `amx_head_tokens`, `amx_recurrence_cycles` | 132, 134, 530-542 | none | 775bba7661 executor L559-565 (PA) |
| `work_tally::amx_blocks`, `amx_fallback_blocks` | 186, 189 | none | 775bba7661 executor L728 (PA) |
| `work_tally::chain_full_block_tokens` | 194 | none | 775bba7661 executor L563 (P0) |
| `work_tally::pre_cycles`, `post_cycles` | 198, 205 | none | 775bba7661 executor L564, L566 (P0) |
| `header_facts::amx_gdn_enabled` (summary key) | 273, 575 | none; model.hpp:1735-1736 says it keeps `false` | 775bba7661 model.hpp L1744 (PA) |
| `header_facts::amx_compiled`, `amx_available` | 271-272 | yes, model.hpp:1734, 1737 | counters commit |
| `BLOCK_TOKENS_32`, `header_facts::block_tokens` (summary key) | 143, 274 | yes, model.hpp:1740 | counters commit; the executor first ties to it at 775bba7661 L253 |

- Same fields repeat in `worker_op_row` (L214-222), `row_sums::add` (L470-485), `put_counts` (L527-551) and the stderr report line "head_tokens per op (token/chain/amx)" (L667-675, L683-687).
- Header comment L18-35 describes the chain kernel and the AMX block kernel, the refusal rule and `amx_fallback_blocks / (amx_blocks + amx_fallback_blocks)`.
- `README.stats.md` at 0d69ef3ce8 documents `chain_head_tokens`, `amx_head_tokens` (L336-339), `amx_blocks`, `amx_fallback_blocks`, `block_tokens` (L340-346), `chain_full_block_tokens` (L347-348), `pre_cycles`, `post_cycles`, `chain_recurrence_cycles`, `amx_recurrence_cycles` (L349-357).
- `README.stats.md` and `t/t_gdn_stats.cpp` have the same blob at 0d69ef3ce8, 775bba7661 and 882e5322f1. Part 0 and Part A do not touch them.
- Test writers only at 0d69ef3ce8: `t/t_gdn_stats.cpp:88-98, 412-417` fill the fields by hand to test rendering. `t/t_gated_delta_net.cpp:2368-2381` checks that they read zero.
- Result: PR 1 holds ten keys without a production writer: `chain_head_tokens`, `amx_head_tokens`, `chain_recurrence_cycles`, `amx_recurrence_cycles`, `amx_blocks`, `amx_fallback_blocks`, `chain_full_block_tokens`, `pre_cycles`, `post_cycles`, `amx_gdn_enabled`. The stated rule is "A path that a build does not have reads zero" (gdn_stats.hpp:29-30, README.stats.md:339). Five get their writer in PR 2 and five in PR 3.

## 6. Old WIP commits, file lists only
- 64cde700af "WIP Part 0" (parent 72e1191804, no counters): 4 files, +712/-31: `gated_delta_net.hpp`, `gdn_execution.hpp`, `gdn_rolling_executor.hpp`, `t/t_gated_delta_net.cpp`.
- a72caf7e40 "WIP Part A" (parent 64cde700af): 8 files, +1198/-29: `amx_gdn_iface.hpp`, `gdn_execution.hpp`, `gdn_rolling_executor.hpp`, `src/tron/CMakeLists.txt`, `amx_gdn.cpp`, `t/CMakeLists.txt`, `t_amx_gdn_numerics.cpp`, `t/t_gated_delta_net.cpp`.
- Agreement: yes. Every WIP Part 0 file is P0 or MIXED here. Every WIP Part A file is PA or MIXED here. The same three files are shared by both parts.
- Files in 775bba7661 that neither WIP list has: `gdn_stats.hpp` (P0) and `model.hpp` (PA), both tied to the counters commit that the WIP stack did not have; `CMakeLists.txt`, `README.ci.md`, `amx_attn_iface.hpp`, `amx_attn.cpp` (PA, text only).
- Only two blobs are unchanged from the WIP commits: `gated_delta_net.hpp` (c49f1fa914) and `src/tron/CMakeLists.txt` (79ea01a443). All other files differ. Neither WIP commit is an ancestor of 775bba7661.

## 7. Size of the two commits (est.)
Method: a script built a Part 0-only text of the three MIXED files from the ranges above, then `git diff --no-index --numstat` counted counters-commit to Part 0, and Part 0 to 775bba7661. The text was not compiled and not formatted with clang-format.

| Commit | Added lines (est.) | Removed lines (est.) |
|---|---|---|
| Part 0, test L2912 kept in a chain-only form | 942 | 79 |
| Part 0, test L2912 and its helpers moved whole to Part A | 878 | 79 |
| Part A, after the first Part 0 variant | 1573 | 48 |
| Part A, after the second Part 0 variant | 1625 | 36 |

Per file (est., first variant). Part 0: `gated_delta_net.hpp` +322/-4, `t_gated_delta_net.cpp` +314/-12, `gdn_rolling_executor.hpp` +276/-48, `gdn_execution.hpp` +27/-13, `gdn_stats.hpp` +3/-2. Part A: `amx_gdn.cpp` +553, `t_amx_gdn_numerics.cpp` +535, `amx_gdn_iface.hpp` +161, `t_gated_delta_net.cpp` +152/-22, `gdn_rolling_executor.hpp` +134/-5, `src/tron/CMakeLists.txt` +11/-9, `model.hpp` +10/-3, `t/CMakeLists.txt` +6/-1, `README.ci.md` +5/-3, `amx_attn_iface.hpp` +2/-2, `amx_attn.cpp` +2/-2, `CMakeLists.txt` +1/-1, `gdn_execution.hpp` +1/-0.

The two parts add up to more than the measured +2488, because Part A rewrites some lines that Part 0 writes in a simpler form.

Scratch copies (may be cleared, not a source of truth): `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/cut/p0/` and the script `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/cut/build_p0.py`.

## Risks for the cut
1. Part 0 cannot go before the counters commit. `advance()` takes `gdn_stats::work_tally*` (executor L511) and uses `stamp_if`, `path_ix`, `BLOCK_TOKENS_32` (L253, L540-566).
2. The executor includes `amx_gdn_iface.hpp` outside any `#ifdef` (L21), and L251-252, L255-257 use `amx_gdn_k128v128` names outside `#ifdef TRON_AMX_DISPATCH`. Any of these left in Part 0 fails to compile, because the header arrives with Part A. The same holds for L25 of the test file.
3. The changed checks of the replay stats test (L2366-2404) must go with Part 0. With `advance()` in place, the old checks of 0d69ef3ce8 (`head_tokens[token_path] == n_key_heads * (long_chain_tokens + 1)`, `pre_cycles == 0`) fail.
4. Test L2912 is the only test of `chain_full_block_tokens` above zero and of the window grid count. If it moves whole to Part A, PR 2 ships that counter with no test. A chain-only form in Part 0 needs `full_window_tokens` (L2814-2823) and the tallies of `chain_case_result` (L2653-2655).
5. Part A changes the signature of `advance()`. It must touch all four call sites: gdn_execution.hpp L168 and test L2746, L2760, L3005, plus `run_chain_case` (L2672) and its caller L2807.
6. `gdn_stats.hpp` L143 says "The executor checks that this is its window size". That is true in PR 2 only if executor L253 stays in Part 0.
7. `gdn_stats.hpp` L23-24 name `gdn_recurrence_chain`. That hunk belongs to Part 0, not to PR 1, where the function does not exist.
8. `model.hpp` L49 and L1742-1744 name `amx_gdn_k128v128`. They belong to Part A. The comment at 0d69ef3ce8 model.hpp:1735-1736 ("No AMX kernel serves GDN") stays true through PR 2.
9. `CMakeLists.txt` L46, `README.ci.md` L586-590 and `src/tron/CMakeLists.txt` L207-222 name files that exist only from Part A on.
10. Left in Part 0 by a careless cut, these become unused: `head_floats` (L2678), `no_value_head` (L2660), `chain_case_result::recurrent_state_bytes` (L2656-2657), and `normalized_query` of the window (note N1). The build uses `-Wall -Wextra` (CMakeLists.txt L584). No `-Werror` for compiles was found in `CMakeLists.txt`, `CMakePresets.json` or `flake.nix`.
11. `flake.nix` L2343 runs `clang-format-19 --dry-run -Werror`. Removing the kernel argument changes the wrapping of the four `advance()` calls, so each cut commit needs a format pass.
12. The commit message of 775bba7661 describes both parts. Its paragraphs split as: chain kernel to Part 0, AMX block kernel and `TRON_AMX_GDN_DISABLE` to Part A, stats and tests to both.
13. Side finding for PR 4: the `t/CMakeLists.txt` hunk of 882e5322f1 has the Part A line `FILES t_amx_numerics.cpp t_amx_gdn_numerics.cpp` as context (hunk at L693 of 882e5322f1). That hunk will not apply unchanged on PR #5022's branch.

## Not verified
- That the Part 0-only text compiles or passes tests. No build and no test run were allowed.
- Whether an unused variable or member fails any CI lane.
- Whether `TRON_CHUNK_SIZE` is 16 in every build (h/tron/simd/auto.hpp:52). The 128 by 128 claim for `wide_chain_geometry` rests on the `static_assert` at test L2830-2831, which is compiled only with `TRON_AMX_DISPATCH`.
- CI lane coverage of the AMX tests. `t_amx_gdn_numerics.cpp` L184, L291, L361, L399, L441 print a warning and skip on a host without AMX.
