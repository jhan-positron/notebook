# Value-suffixed names that PR 4557 added to shared files

Date: 2026-10-06. PR head: c5d44bd86f (branch jhan-kv-typed-tensors, merge base with main dd6e85226b).
Trigger: Wade's comment on PR 4557 [https://github.com/positron-ai/tron/pull/4557#issuecomment-6021333114].

## Short version

Wade accepts value-suffixed names (constants spelled `NAME_<value>`, such as `V_PAIR_TOKENS_2`) inside the AMX kernel files, which already use that style. He asks that shared code keep its existing idiom instead. This page lists the 24 such names the PR added to the four shared files, with their uses, so they can be reverted to the surrounding style.

## Words used here

- **Value-suffixed name**: Wade's term for a `constexpr` constant whose name ends in its own value, for example `V_ROW_WIDTH_MULTIPLE_32 = 32` or `V_ODD_TOKEN_LANE_MASK_0XFFFF0000`. Our C++ guide produces this form (its "Named values" section, rule "rename the variable ... so the suffix matches the new value").
- **Shared file**: a file that code outside the AMX kernels also owns or reads. Here: `h/tron/tensor/v_vnni.hpp`, `t/t_llama_unit.cpp`, `t/t_heap_v2.cpp`. `v_vnni.hpp` is new in this PR, but it holds the V set/get/append bodies moved out of `kv_cache.hpp`, and the AVX (non-AMX) path calls them. Wade names it explicitly.
- **AMX kernel file**: `src/tron/kernels/amx_attn.cpp` and `h/tron/kernels/amx_attn_iface.hpp`. Wade: "Fair enough for the AMX kernel files: they already use this style throughout". The value-suffixed style stays in these two files.
- **Literal-plus-named-local idiom**: the existing spelling of a mask in `kv_cache.hpp`: `const __m512i hi_16_of_32 = _mm512_set1_epi32(0xffff0000);`. The literal stays in the code, and a lower-case local name says what it selects.
- **Moved code**: the set_v / get_v / append bodies that main keeps in `kv_cache.hpp` and the PR moves into `v_vnni.hpp`. On main those bodies use bare literals.

## 1. What Wade wrote

Full text of the comment (2026-10-06 17:03 UTC):

> Fair enough for the AMX kernel files: they already use this style throughout, so the tile constants are consistent there. Outside your own files, though, the codebase does not use value-suffixed names, and the `_0X...` mask names are new. In shared code I care most about local consistency: `scaled_v_expr` in kv_cache.hpp still writes `_mm512_set1_epi32(0xffff0000)` as `hi_16_of_32`, while its partner code in v_vnni.hpp spells the same mask `V_ODD_TOKEN_LANE_MASK_0XFFFF0000`. Could the v_vnni.hpp masks follow the existing literal-plus-named-local idiom?
>
> This is simply a non-blocking nit though ;-p. Not stopping approval.

Verified: `scaled_v_expr` at PR head still initialises its member as `hi_16_of_32(_mm512_set1_epi32(0xffff0000))` [h/tron/models/kv_cache.hpp:2260]. The same mask appears four times in `v_vnni.hpp` as `_mm512_set1_epi32(V_ODD_TOKEN_LANE_MASK_0XFFFF0000)` [h/tron/tensor/v_vnni.hpp:281, 328, 358].

One factual note on Wade's "the codebase does not use value-suffixed names": main already holds 90 such constant definitions outside the AMX files, all from our earlier merged PRs (t/t_attn_stats.cpp 46, t/heterogeneous_scheduler_compile.cpp 27, h/tron/models/attn_stats.hpp 12, t/t_llama_unit.cpp 3, h/tron/kernels/page_share_counters.hpp 1, h/tron/models/kv_cache.hpp `KV_BLOCK_PLANES_2` 1). This does not change the decision for PR 4557. It is recorded so the revert does not reach into files this PR did not touch.

## 2. Inventory method

Every added line of the PR (diff of merge base dd6e85226b to head c5d44bd86f) was scanned for identifiers matching `[A-Z][A-Z0-9_]*_(0X<hex>|<digits>)`. Each hit was then checked against `origin/main`. Names already on main (`PAGE_TOKENS_64`, `HEAD_SIZE_128`, `TILE_ROWS_16`, `DIM_STEP_32`, `TILE_ROW_BYTES_64`, `N_LAYERS_1`, `N_ATTN_WORKERS_1`, `N_ATTN_WORKERS_2`) are not this PR's additions and are excluded. Line counts below are "lines in the file at PR head that mention the name", including the definition line.

Files of the PR with no new value-suffixed name: `h/system/memory.hpp`, `h/tron/models/kv_cache.hpp`, `h/tron/models/model.hpp`, `h/tron/models/self_attention.hpp`, `h/tron/scheduler/full.hpp`, `h/tron/tensor/kv_cache_fwd.hpp`, `h/tron/kernels/amx_attn_iface.hpp`, `t/heterogeneous_scheduler_compile.cpp`, `t/t_amx_dispatch_dtype.cpp`, `t/t_amx_numerics.cpp`.

## 3. Shared files: names to revert (24)

### 3.1 h/tron/tensor/v_vnni.hpp (6 names)

Definitions sit at lines 68 to 85. The moved bodies on main spell every one of these as a bare literal.

| Name | Def. line | Lines using it (this file) | Also used in | Form in main's moved code | Suggested revert |
|---|---|---|---|---|---|
| `V_PAIR_TOKENS_2 = 2` | 68 | 28 | amx_attn.cpp (4 lines), t_llama_unit.cpp (4 lines) | `% 2`, `/ 2`, `* 2`, `i * 2` | literal `2` in v_vnni.hpp and t_llama_unit.cpp; definition moves to amx_attn.cpp, see note A |
| `V_PLANE_ALIGNMENT_64 = 64` | 72 | 3 (two `alignas(...)`, one definition) | t_llama_unit.cpp:406 `STATIC_REQUIRE(alignof(v_owner_t) == ...)` | `alignas(64)` | `alignas(64)`; guide allows literals in `alignas` |
| `V_ROW_WIDTH_MULTIPLE_32 = 32` | 77 | 3 (two `requires(Cols % ... == 0)`) | none | `geometry.head_size % 32 == 0` | `requires(Cols % 32 == 0)` |
| `BF16_BITS_16 = 16` | 81 | 8 (shift counts in `_mm512_slli/srli_epi32`) | t_llama_unit.cpp:3542, 3562 | `_mm512_slli_epi32(x, 16)` | literal `16` |
| `V_ODD_TOKEN_LANE_MASK_0XFFFF0000` | 84 | 4 (lines 281, 328, 358 + def.) | none | `const __m512i hi_16_of_32 = _mm512_set1_epi32(0xffff0000);` | that idiom (Wade's request) |
| `V_EVEN_TOKEN_LANE_MASK_0X0000FFFF` | 85 | 2 (line 267 + def.) | none | `const __m512i lo_16_of_32 = _mm512_set1_epi32(0x0000ffff);` | that idiom |

Note A: `V_PAIR_TOKENS_2` is the only one of the six that an AMX kernel file (`amx_attn.cpp`) also uses, at the four `v_pairs + s * TILE_ROWS_16 * HEAD_SIZE_128 * V_PAIR_TOKENS_2` address lines. Decision (jhan, 2026-10-06): the four kernel uses keep the name, and the definition `constexpr size_t V_PAIR_TOKENS_2 = 2;` moves from the header into `amx_attn.cpp`, next to the existing file-scope constants `N_TILES_8` and `DIM_STEP_32` [src/tron/kernels/amx_attn.cpp:35-40 on main]. The header and the tests use the literal `2`. The alternative, keeping the definition in the header for the kernel alone, was rejected: it leaves a value-suffixed name in shared code with a usage rule nothing enforces.

Note B: the two uses of `V_PAIR_TOKENS_2` in the `static_assert(Rows % V_PAIR_TOKENS_2 == 0, ...)` at lines 100 and 157 and the `Rows * Cols` storage are new code, not moved code. They have no main counterpart. Revert form there is the reader's choice; a literal `2` matches the rest of the file after the revert.

### 3.2 t/t_heap_v2.cpp (2 names)

| Name | Def. line | Lines using it | Form in main | Suggested revert |
|---|---|---|---|---|
| `REQUEST_BYTES_1024 = 1024` | 1215 | 2 | `try_make_unique_dma_for_overwrite<uint8_t[]>(1024, std::align_val_t{64})` [main t/t_heap_v2.cpp:1213] | literal `1024` |
| `ARENA_ALIGNMENT_64 = 64` | 1216 | 3 (call, new `CHECK(tron::is_aligned(live.get(), ...))`) | `std::align_val_t{64}` | literal `64` in both the call and the new check |

The same test file keeps its other constants in the repo style: `constexpr int kIters = 500;` [main t/t_heap_v2.cpp:880], `constexpr size_t N = 4096;` [main t/t_heap_v2.cpp:1043], `constexpr size_t N_TRIALS = 50;` [main t/t_heap_v2.cpp:1697]. Note that the two unchanged sibling calls in the same file (PR head lines 1233 and 1255) still write `std::align_val_t{64}`, so the PR's naming made one of three identical calls look different.

### 3.3 t/t_llama_unit.cpp (16 names)

Local idiom on main: lower-case `constexpr` names (`static constexpr size_t x_bytes = 0;`, `constexpr size_t n_tokens = 3;`, `constexpr kv_geometry geometry_64{1, 64};`) and bare literals for test sizes (`const size_t dst_tokens = 3; const size_t src_tokens = 4;` [main t/t_llama_unit.cpp:3187], `set_v(..., kv_head, 7, nan_buf)` [main t/t_llama_unit.cpp:3221]).

File-scope (new append parity case):

| Name | Def. line | Lines using it | Suggested revert |
|---|---|---|---|
| `EVEN_START_DST_TOKENS_2 = 2` | 90 | 2 (def. + `GENERATE(...)` at 3639) | `GENERATE(2, 3)` with the existing comment at 87-89 explaining the parities |
| `ODD_START_DST_TOKENS_3 = 3` | 91 | 3 (def., 3279, 3639) | literal `3` |

Poison-section test (existing case, PR edited it):

| Name | Def. line | Lines using it | Suggested revert |
|---|---|---|---|
| `APPENDED_TOKENS_7 = 7` | 3267 | 3 (def., 3280, 3314) | main had `src_tokens = 4` and a literal `7` in the `set_v` call; either restore those or keep a lower-case local `appended_tokens = 7` next to the existing `x_bytes` |

New test case "packed V rows keep their bits through set_v, get_v and at()" (starts line 3461):

| Name | Def. line | Lines using it | Suggested revert |
|---|---|---|---|
| `HEAD_SIZE_64 = 64` | 3462 | 46 | the file already has `constexpr kv_geometry geometry_64{1, 64};` at line 156; reuse `geometry_64` and `geometry_64.head_size`, or a lower-case `head_size = 64` |
| `N_SLOTS_1 = 1` | 3463 | 2 | literal `1` in `uniform_kv_cache<1, geometry, 0>` |
| `X_BYTES_0 = 0` | 3464 | 2 | literal `0` (guide already allows literal `0`) |
| `N_PAGES_1 = 1` | 3465 | 4 | literal `1` in `book_t bk(1)` and the two books at 3641-3642 |
| `PATTERN_BASE_0X3C00 = 0x3c00` | 3467 | 2 (def. + 3485) | lower-case `pattern_base = 0x3c00` or the literal inside the `pattern` lambda |
| `SPECIALS_EVEN_TOKEN_2 = 2` | 3469 | 5 | literal token index, or lower-case locals |
| `SPECIALS_ODD_TOKEN_3 = 3` | 3470 | 6 | same |
| `FLOAT_ROW_EVEN_TOKEN_4 = 4` | 3471 | 3 | same |
| `FLOAT_ROW_ODD_TOKEN_5 = 5` | 3472 | 2 | same |
| `FP16_ROW_EVEN_TOKEN_6 = 6` | 3473 | 5 | same |
| `FP16_ROW_ODD_TOKEN_7 = 7` | 3474 | 5 | same |

New test case "append_v_row matches the independent packed-V formula" (starts line 3693):

| Name | Def. line | Lines using it | Suggested revert |
|---|---|---|---|
| `ROWS_64 = 64` | 3694 | 5 | `amx_attn_h128g4::PAGE_TOKENS_64` is already used at lines 370-377 for the AMX view type aliases, or a lower-case `rows = 64` |
| `COLS_128 = 128` | 3695 | 9 | `amx_attn_h128g4::HEAD_SIZE_128`, or lower-case `cols = 128` |
| `PATTERN_BASE_0X3C00 = 0x3c00` (second definition) | 3697 | 2 (def. + 3699) | as above |

Uses in this file of names defined in `v_vnni.hpp` (follow the section 3.1 revert): `V_PAIR_TOKENS_2` at 3714, 3716, 3718, 3719; `V_PLANE_ALIGNMENT_64` at 406; `BF16_BITS_16` at 3542, 3562.

Already on main before this PR, in the same file, no action: `N_LAYERS_1`, `N_ATTN_WORKERS_1`, `N_ATTN_WORKERS_2`, `STATS_ON_TRUE`, `NOT_EAGLE_FALSE` (lines 2214-2291, from the attention-stats PR 4596).

## 4. AMX kernel files: names that stay (11 new, 1 moved in, plus 8 pre-existing)

`src/tron/kernels/amx_attn.cpp` adds tile-register and slice constants. Wade accepts these. Listed for completeness so the revert does not touch them.

| Name | Lines using it |
|---|---|
| `ACCUMULATOR_TILE_0` .. `ACCUMULATOR_TILE_3` | 7 each |
| `K_EVEN_BLOCK_TILE_4`, `K_ODD_BLOCK_TILE_5` | 5 each |
| `Q_TILE_6` | 6 |
| `P_TILE_4` | 6 |
| `V_EVEN_SLICE_TILE_5`, `V_ODD_SLICE_TILE_6` | 5 each |
| `PV_TILES_PER_HALF_4` | 5 |

Pre-existing on main in the AMX files and reused by the PR: `TILE_ROWS_16`, `TILE_ROW_BYTES_64`, `PAGE_TOKENS_64`, `HEAD_SIZE_128`, `GROUP_HEADS_4`, `Q_PACK_ELEMS_2048`, `N_TILES_8`, `DIM_STEP_32` [main h/tron/kernels/amx_attn_iface.hpp:129-142, src/tron/kernels/amx_attn.cpp:35-40].

The only cross-file dependency between the two groups is `V_PAIR_TOKENS_2`. Its definition moves into this file (Note A in section 3.1), so after the revert the kernel file holds 12 new value-suffixed constants and the header holds none.

## 5. Revert summary

| File | Names to revert | Lines affected (est., from the per-name line counts) |
|---|---|---|
| h/tron/tensor/v_vnni.hpp | 6 | 48 |
| t/t_heap_v2.cpp | 2 | 5 |
| t/t_llama_unit.cpp | 16 (+7 lines using v_vnni.hpp names) | about 110 |
| src/tron/kernels/amx_attn.cpp | 0 reverted; 1 definition added (`V_PAIR_TOKENS_2`, moved from the header) | 1 |

After the revert, a full rebuild on 3bda and the three test binaries (t_llama_unit, t_amx_numerics, t_heap_v2) confirm nothing but spelling changed. A pure rename produces identical object code, so the objdump comparison used in the first 3bda campaign [status/first-3bda-test-plan.md, Step F] is the strongest check.

## 6. Conflict with our C++ guide (recorded, not resolved here)

Our guide's "Named values" rule asks for named `constexpr` values with the value as suffix, and the 2026-09-23 round applied it across every file of the PR. Wade's request and the decision taken on 2026-10-06 (jhan: "I do want to respect consistency, so we will revert the code style changes at shared files") narrow the rule's reach to files the AMX work owns. Files that other code owns follow their own local idiom. The guide text itself is unchanged by this page.

## 7. Revert applied (2026-10-06)

Draft PR #4775 [https://github.com/positron-ai/tron/pull/4775], branch jhan-kv-typed-tensors-plain-names, commit 425a0e8239, base jhan-kv-typed-tensors (the PR 4557 branch). Diff: 4 files, 147 insertions, 176 deletions. Scripts and logs: exec/style-revert-20261006/ (build-test.sh, run.log, pr-body.final.md).

Verification on delphi-3bda (socket 1, fresh worktree /var/tmp/jhan/tron-i4525-style, clang 19.1.7, RelWithDebInfo, AVX512 + TRON_AMX_DISPATCH on):

- The disassembly of libtron.a (120126 lines) is identical before and after the change, apart from objdump's file-path header line. The four library objects that include v_vnni.hpp through kv_cache.hpp (amx_attn, cache, gof, token_tree) were recompiled and produced the same code.
- t_amx_numerics and t_amx_dispatch_dtype: disassembly identical apart from the path header. t_heap_v2 and t_llama_unit differ in string addresses only, because Catch embeds each REQUIRE's expression text and those texts got shorter.
- Tests: t_llama_unit 249115 assertions / 62 cases, t_amx_numerics 4109 / 4 (real AMX, no "unavailable" warning), t_heap_v2 8242 / 45, t_amx_dispatch_dtype 1612 / 1, all passed.
- clang-format --dry-run -Werror (repo toolchain), make lint-notes and git diff --check all pass.

Trap met: bin/lint-notes without file arguments exits 1 with a usage line. The hook runs `make lint-notes`, which supplies the file set.
