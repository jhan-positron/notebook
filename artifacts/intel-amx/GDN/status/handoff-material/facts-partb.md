# Part B port onto PR #5022, and the measurement-only build: verified facts

## Short version
- A cherry-pick of Part B (882e5322f1) onto PR #5022's head (ddf843ad97) conflicts in 5 of its 7 files, 29 regions in total. The other 2 files apply without conflict.
- Part B needs nothing from the GDN commit 775bba7661. The two sides collide in design: PR #5022 varies the group size by a template parameter, and Part B varies the head size by a second namespace.
- For the measurement-only build, a merge of ddf843ad97 into the model's branch conflicts in 9 files that come from main. PR #5022's net change alone applies onto 72e1191804 with 0 conflicts.

## Method (read this first)
- The host git is 2.34.1. It has no `git merge-tree --write-tree` (it prints `usage: git merge-tree <base-tree> <branch1> <branch2>`).
- Replacement: a throwaway repository inside my scratchpad, with `objects/info/alternates` pointing at `/home/jhan/workspace/tron/.git/objects`. I ran the real `git cherry-pick -n` and `git merge --no-commit` there (merge strategy "ort"), then deleted it.
- Nothing was written to the user's repository. Afterwards the worktree `/home/jhan/workspace/ai-runs/tron-gdn-amx` was still at HEAD 882e5322f1, branch jhan-gdn-amx, `git status --short` empty.
- Cross-check with `git merge-file -p` (Myers diff) on the 7 files gave the same counts, except t/t_amx_numerics.cpp (6 regions instead of 7).
- No build and no test was run. Every "compiles" statement below is from reading only.

## 1. Simulated cherry-pick of 882e5322f1 onto ddf843ad97 (base 775bba7661)

| File | Result | Regions | What conflicts |
|---|---|---|---|
| h/tron/kernels/amx_attn_iface.hpp | conflict | 6 | All 6 are comment text (region 5 also repeats 2 identical constant lines). The new namespace `amx_attn_h256g4` is appended without conflict. |
| h/tron/models/self_attention.hpp | conflict | 6 | 1 comment; 1 `amx_qpack.resize`; 3 kernel call sites (pack, QK, PV); 1 PV output row copy. |
| h/tron/tensor/v_vnni.hpp | clean | 0 | Comment-only change. The file is identical at 775bba7661 and ddf843ad97 (blob db5e59b88c). |
| src/tron/kernels/amx_attn.cpp | clean (text only) | 0 | 1 comment line changed, 233 lines appended (namespace `amx_attn_h256g4`). |
| t/CMakeLists.txt | conflict | 1 | Registration of `t_amx_numerics`. |
| t/t_amx_dispatch_dtype.cpp | conflict | 9 | Header comment (2), probe struct, `exercise_page` signature, probe checks, 3 fakes, the appended 256 fakes. |
| t/t_amx_numerics.cpp | conflict | 7 (6 with Myers) | using-lines, `qk_inputs`/`fill_qk`, the Q-pack, QK and PV test bodies. |

- Copies of the 7 files as the cherry-pick left them are in `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/portb/cp_sim/` (temporary; names use `_` for `/`).

## 2. Dependence on 775bba7661, and branch jhan-gdn-partb

The two 4-line hunks of 775bba7661 are comments only:

```
h/tron/kernels/amx_attn_iface.hpp @@ -1,8 +1,8 @@
-// src/tron/kernels/amx_attn.cpp, the only translation unit compiled with
-// -mamx-tile/-mamx-bf16. See Note [AMX attention dispatch].
+// src/tron/kernels/amx_attn.cpp, which is compiled with -mamx-tile/-mamx-bf16.
+// See Note [AMX attention dispatch].
src/tron/kernels/amx_attn.cpp @@ -1,6 +1,6 @@
-// (in amx_attn_iface.hpp). The ONLY translation unit compiled with
-// -mamx-tile/-mamx-bf16.
+// (in amx_attn_iface.hpp). One of the two translation units compiled with
+// -mamx-tile/-mamx-bf16. The other is amx_gdn.cpp.
```

- Part B does not need them. The added lines of 882e5322f1 contain no GDN name (grep of `+` lines for `gdn|gateddelta|gated_delta`: 0 hits).
- The only GDN text in Part B's diff is one context line, `FILES t_amx_numerics.cpp t_amx_gdn_numerics.cpp` (882e5322f1:t/CMakeLists.txt:693).
- Files touched by both Part B and the two GDN commits: amx_attn_iface.hpp, amx_attn.cpp, t/CMakeLists.txt.
- On ddf843ad97 the "only translation unit" wording is still true, and the cherry-pick keeps it. It becomes false once PR 3 (amx_gdn.cpp) and PR 4 are both present.

jhan-gdn-partb = 8376a86d8a, parent 72e1191804, commit date 2026-11-21 14:36:47 -0800. 882e5322f1 has the same author date (14:19:05) and a later commit date (22:14:11).

`git diff --stat 882e5322f1 8376a86d8a` over the 7 files:
```
 h/tron/kernels/amx_attn_iface.hpp |  4 ++--
 h/tron/models/self_attention.hpp  |  7 +------
 src/tron/kernels/amx_attn.cpp     |  6 +++---
 t/CMakeLists.txt                  | 15 ++-------------
 4 files changed, 8 insertions(+), 24 deletions(-)
```
- amx_attn_iface.hpp, amx_attn.cpp: 8376a86d8a has the pre-GDN comment wording, and "one of the two layout-specific readers" where 882e5322f1 says "one of the layout-specific readers".
- self_attention.hpp: 882e5322f1 has 2 extra `static_assert(amx_serves_128x4<geometry>, "this branch calls the 128 x 4 kernel")` (882e5322f1:1806-1807, 1841-1842) and `tensor<operation_head_size> scratch{uninitialized};` (882e5322f1:1851-1852). 8376a86d8a has neither.
- t/CMakeLists.txt: 8376a86d8a lacks the GDN test wiring (t_gdn_stats.cpp, t_amx_gdn_numerics.cpp).
- v_vnni.hpp, t_amx_numerics.cpp, t_amx_dispatch_dtype.cpp: identical.
- So 882e5322f1 holds the newer Part B text. Port from 882e5322f1, not from 8376a86d8a.

## 3. Structures the port must fit

### PR #5022 side (line numbers at ddf843ad97)
- amx_attn_iface.hpp: one namespace `tron::amx_attn_h128g4` (119-263).
  - Constants: `TILE_ROWS_16`, `TILE_ROW_BYTES_64` (129-130); `PAGE_TOKENS_64`, `HEAD_SIZE_128`, `GROUP_HEADS_4`, `GROUP_HEADS_16` (133-136).
  - View aliases `const_k_row_major_plane_view`, `const_v_vnni_plane_view` (142-143).
  - `group_heads_ok(size_t)`: true for 4 or 16 (150-152).
  - `shape_ok(head_size, kv_mul)` = head size 128 and `group_heads_ok(kv_mul)` (159-161). `query_scalar_ok<T>` (169-170). `eligible<T>(head_size, kv_mul)` (173-176). `available()` (181).
  - Kernels are function templates `template <size_t group_heads> requires(group_heads_ok(group_heads))`: `pack_q_group_128x4` (197-199), `qk_rowmajor_128x4` (237-242), `weights_times_v_128x4` (251-256). `begin_region`/`end_region` (260-261).
  - The header comment says the names keep `h128g4` and `_128x4` although kv_mul 16 is served (13-17).
- amx_attn.cpp: namespace 32-256. Tile numbers and 128-based row strides in an anonymous namespace (33-96). QK template calls `transpose_scores<group_heads>` (180). PV template has a `thread_local` P per instantiation (198). Explicit instantiations for `GROUP_HEADS_4` and `GROUP_HEADS_16` (244-254).
- amx_attn_transpose.hpp (new, 94 lines), namespace `tron::amx_attn_h128g4`: `TILE_FP32S` (15), `LANES_EVEN_0X88`, `LANES_ODD_0XDD` (17-18), `ROWS_PER_LANE_4` (20), `store_transposed_rows<lane>` (28-42), `transpose_scores<group_heads>` (46-92). It uses AVX-512 only and does not depend on the head size.
- self_attention.hpp:
  - No named per-geometry predicate. The expression `amx_attn_h128g4::eligible<typename model::activation_scalar>(head size, kv_mul)` is written 3 times: 1535-1537 (`amx_eligible` in `apply_page_range`), 1743-1745 (static_assert in `apply_dense_amx_page`), 1879-1880 (`if constexpr` in `apply_page_tok`).
  - Run time: `amx_on = amx_eligible && amx_attn_h128g4::available()` (1538). Per page: `is_dense_amx_page` (1710-1721).
  - Kernel calls: pack in `packed_amx_query` (1695-1696, with `<operation_kv_mul>`), reached from 1631-1632; QK 1761-1763; PV 1789-1791; `begin_region` 1554; `end_region` 1559.
  - Query pack size: `amx_qpack_slot { bf16 v[amx_attn_h128g4::Q_PACK_ELEMS_2048]; }` (258-260) = 2048 bf16 = 4096 bytes, the same for 4 and 16 heads. `amx_qpack.resize(items.size())` (1553).
  - PV output row is read through a `const_view` named `row` (1796-1798). PR #5022 removed `#include <cstring>` from this file.

### Part B side (line numbers at 882e5322f1)
- amx_attn_iface.hpp: two namespaces.
  - `amx_attn_h128g4` (120-252): `shape_ok` = head 128 and kv_mul == 4 (154-156); the 3 kernels are plain functions (193, 228-231, 240-244).
  - `amx_attn_h256g4` (254-315): imports `GROUP_HEADS_4`, `PAGE_TOKENS_64`, `query_scalar_ok`, `TILE_ROW_BYTES_64`, `TILE_ROWS_16` (261-265); `HEAD_SIZE_256` (266); `Q_PACK_ELEMS_4096` = 4096 bf16 = 8192 bytes (270-271); `shape_ok` = head 256 and kv_mul == 4 (275-277); `eligible<T>` (280-283); `pack_q_group_256x4` (293), `qk_rowmajor_256x4` (300-303), `weights_times_v_256x4` (309-313). `available`, `begin_region`, `end_region` exist in `amx_attn_h128g4` only.
- amx_attn.cpp: namespace `amx_attn_h256g4` (280-511). It imports the tile numbers, `DIM_STEP_32`, `TILE_FP32S`, `V_PAIR_TOKENS_2` from `amx_attn_h128g4` (286-298). Own transposing store `store_query_rows` (339-375) with `TRANSPOSE_ROWS_4`, `TRANSPOSE_ROW_GROUPS_4`, `LANES_0_AND_2_0X88` (329-332). `weights_to_bf16` (381-393). Pack 397-414, QK 421-458, PV 464-509.
- self_attention.hpp:
  - `amx_serves_128x4<geometry>` (226-229), `amx_serves_256x4<geometry>` (230-233), `amx_serves<geometry>` (234-236).
  - `amx_q_pack_elems` (241-250): 4096 elements when any entry of `plugin::attention_kernels` passes `amx_attn_h256g4::shape_ok`, else 2048. Slot `bf16 v[amx_q_pack_elems]` (290-292). `plugin::attention_kernels` also exists at ddf843ad97 (h/tron/plugins/llama.hpp:230, mock.hpp:115).
  - `amx_eligible = amx_serves<geometry>` (1564). Grow-only `if (amx_qpack.size() < items.size()) amx_qpack.resize(...)` (1583).
  - Kernel selection by `if constexpr (amx_serves_256x4<geometry>)`: pack 1726-1737, QK 1802-1810, PV 1836-1846. PV row copy by `scratch{uninitialized}` + `std::memcpy` (1851-1854). `if constexpr (amx_serves<geometry>)` in `apply_page_tok` (1935).
  - `is_dense_amx_page` (1751-1762) is text-identical to ddf843ad97:1710-1721 (diff of the two blocks is empty).

### Collisions (same job, different name or shape)

| # | Job | PR #5022 | Part B | Consequence for the port |
|---|---|---|---|---|
| C1 | Gate of the 128 shape | kv_mul 4 or 16 | kv_mul 4 only | The cherry-pick keeps PR #5022's gate. |
| C2 | Per-geometry predicate | inline `eligible<...>`, 3 places | `amx_serves_128x4` / `_256x4` / `amx_serves` | The 3 use sites merge to Part B's names without conflict. The name `amx_serves_128x4` then also covers 128 x 16. |
| C3 | Calls of the 128 kernels | need `<operation_kv_mul>` | no template argument | Part B's 128 branch does not match PR #5022's declarations: `group_heads` is in no function parameter, so it cannot be deduced (by reading). |
| C4 | Axis of generalization | group size = template parameter in one namespace | head size = second namespace, 4 heads fixed | Neither side serves 256 x 16. `g4` is literal in `h256g4` and historical in `h128g4`. |
| C5 | Transposing store of QK | `transpose_scores<group_heads>` in amx_attn_transpose.hpp | `store_query_rows` in amx_attn.cpp | Two implementations of the 4-head case; duplicate constants (`LANES_0_AND_2_0X88` vs `LANES_EVEN_0X88`, `TRANSPOSE_ROWS_4` vs `ROWS_PER_LANE_4`). |
| C6 | Home of `TILE_FP32S` | amx_attn_transpose.hpp:15 | anonymous namespace, amx_attn.cpp:59 | Part B's `using amx_attn_h128g4::TILE_FP32S;` still names an existing constant (by reading). |
| C7 | Packed-query slot size | fixed `Q_PACK_ELEMS_2048` | `amx_q_pack_elems` per plugin | No text conflict; Part B's form results. |
| C8 | `amx_qpack` resize | plain resize, short comment | grow-only, comment says "the 4 live columns" | Conflict; Part B's comment is wrong for 16 heads. |
| C9 | PV output row | `const_view row`, no `<cstring>` | `scratch` + `memcpy` | Conflict; the lines after it use `row`, so PR #5022's side must stay. |
| C10 | `exercise_page` 2nd template parameter (dispatch test) | `n_heads` (3rd `n_kv_heads`, argument `kv_head`) | `head_size` | Same position, different meaning. |
| C11 | `qk_inputs` / `fill_qk` template parameter (numerics test) | `group_heads` | `head_size` | Same names, different meaning. |
| C12 | Probe of the dispatch test | `pack/qk/pv_group_heads`, per-row PV values, state check after 2 visits | `wrong_shape_calls`, `note_shape`, zero-filled PV | Both checks are wanted; fakes of the 128 kernels are templates on PR #5022's side. |
| C13 | Layout of the numerics test | `check_*<group_heads>` helpers + one SECTION per group size | `TEMPLATE_TEST_CASE` over `shape_128x4`, `shape_256x4` | The merge leaves both layouts in the file. |
| C14 | Host without AMX (numerics test) | `SKIP(...)`, test registered with `SKIP_RETURN_CODE 4` | `WARN` + `return` (from the base) | PR #5022 also removed the placeholder case for builds without TRON_AMX_DISPATCH; Part B still has it. |

## 4. Tests (names and counts)

Base blobs are the same on both sides: t_amx_numerics.cpp eb8af17c27, t_amx_dispatch_dtype.cpp 1411183b50 (at 775bba7661 and at 3bea58b788).

| File | Measure | Base | PR #5022 | Part B |
|---|---|---|---|---|
| t_amx_numerics.cpp | lines | 288 | 404 | 356 |
| | test-case macros | 5 | 5 | 5 (2 TEST_CASE + 3 TEMPLATE_TEST_CASE x 2 shapes) |
| | SECTION | 1 | 8 | 1 |
| | STATIC_REQUIRE lines | 12 | 15 | 18 |
| t_amx_dispatch_dtype.cpp | lines | 288 | 404 | 350 |
| | TEST_CASE / SECTION | 2 / 5 | 2 / 9 | 2 / 7 |
| t_llama_unit.cpp | TEST_CASE / SECTION | 51 / 32 (72e1191804) | 52 / 35 | 51 / 32 (untouched) |

- PR #5022 adds to t_amx_numerics.cpp:
  - case "AMX QK transpose writes the group_heads score rows" `[amx_numerics][transpose]`, 2 sections, outside the TRON_AMX_DISPATCH guard;
  - a "4 heads ..." and a "16 heads ..." section in each of the Q packer, QK and PV cases (6 sections);
  - helpers `check_transpose`, `check_q_pack`, `check_qk`, `check_pv`;
  - 3 gate checks (GROUP_HEADS_16 accepted; KV_MUL_8 and KV_MUL_32 refused);
  - it removes "AMX numerics tests skipped (dispatch not compiled)".
- Part B adds to t_amx_numerics.cpp: structs `shape_128x4`, `shape_256x4`; the Q packer, QK and PV cases run once per shape (3 cases, 6 runs); 6 gate checks for `amx_attn_h256g4::eligible`.
- PR #5022 adds 4 sections to t_amx_dispatch_dtype.cpp: "host_bf16, 16 heads, full page ...", "host_bf16, 16 heads, partial page ...", "host_bf16, 16 heads, full page, available() false ...", "host_bf16, 32 heads / 2 KV heads, KV head 1, full page ...".
- Part B adds 2 sections: "host_bf16, 256-dim heads, full page ...", "host_bf16, 256-dim heads, partial page ...", plus fakes of the 3 `amx_attn_h256g4` entry points.
- t_llama_unit.cpp: Part B does not touch it (blob 957e6a3727 at 72e1191804, 775bba7661, 882e5322f1). PR #5022 changes 6 lines: the probes `amx_qk_accepts` and `amx_pv_accepts` (ddf843ad97:101, 107) pass `<amx_attn_h128g4::GROUP_HEADS_4>`. It adds no case; the 52 / 35 count comes from main.

## 5. Measurement-only build "model's branch + PR #5022 + Part B"

| Fact | Value |
|---|---|
| `git merge-base 72e1191804 ddf843ad97` | 54476c65812b, 2026-11-16 07:43:19 +0000, "Execute forward plans over decoder-layer ranges (#5184)" |
| `git merge-base origin/main ddf843ad97` | 3bea58b78867, 2026-11-19 23:07:18 +0000, "Plan GatedDeltaNet dependency chains (#3204)" |
| origin/main (local, fetched 2026-11-22 14:53 -0800) | 7eddde7895, 2026-11-21 17:36:45 +0000 |
| ddf843ad97 vs origin/main | 7 commits ahead, 10 behind |
| 72e1191804 vs origin/main | 21 ahead, 48 behind; merge base 54476c65812b |

Merge of ddf843ad97 into 72e1191804 (simulated): 9 conflicting files.

| File | Kind | Regions |
|---|---|---|
| config/test-benchmarks.json | content | 1 |
| doc/memory_pressure_governor.md | content | 1 |
| h/tron/kernels/gated_delta_net.hpp | add/add | 5 |
| h/tron/models/gdn_rolling_executor.hpp | add/add | 11 |
| h/tron/scheduler/token_cache_policy.hpp | content | 1 |
| ingest/src/TronCpp.hs | content | 1 |
| src/system/fuse_tronstats_manifest.cpp | content | 1 |
| src/tron/scheduler/token_cache_control.cpp | content | 2 |
| t/t_gated_delta_net.cpp | add/add | 50 |

- No AMX attention file conflicts in this merge.
- 8 of the 9 files are not among PR #5022's 12 files. They conflict because the merge also brings 38 commits of main (54476c6581..3bea58b788). Only config/test-benchmarks.json is in both lists.

Extra simulation (not asked, same scratch method): PR #5022's net change alone (diff 3bea58b788..ddf843ad97, 12 files) as one cherry-pick.

| Applied onto | Conflicts |
|---|---|
| 72e1191804 (model's branch) | 0 |
| 775bba7661 (model + counters + Part 0 + Part A) | 3 files, 1 region each: README.ci.md, src/tron/CMakeLists.txt, t/CMakeLists.txt |

- After the apply onto 72e1191804, 7 files are byte-identical to ddf843ad97: amx_attn_iface.hpp, amx_attn_transpose.hpp, v_vnni.hpp, amx_attn.cpp, t_amx_dispatch_dtype.cpp, t_amx_numerics.cpp, src/tron/CMakeLists.txt.
- 3 files differ from ddf843ad97 there: self_attention.hpp, t/CMakeLists.txt, t/t_llama_unit.cpp. For self_attention.hpp the difference is one comment hunk near line 850 (`git diff 72e1191804 3bea58b78867`, 6 insertions, 2 deletions).
- The 3 conflicts on 775bba7661 are Part A against PR #5022: the comment on the AMX translation units, and the registration of `t_amx_numerics` (Part A adds `t_amx_gdn_numerics.cpp` to it; PR #5022 adds `SKIP_RETURN_CODE 4` and the label `skip_return_code_4`).

## 6. Models in config/models.yaml

| Commit | Entry | Lines | slug | executors | tags |
|---|---|---|---|---|---|
| ddf843ad97 | gemma_4_e4b_it | 843-856 | ingested-gemma-4-e4b-it | [tp1, tp2, tp4] | [test] |
| ddf843ad97 | gemma_4_e4b_it_permuted | 858-872 | ingested-gemma-4-e4b-it-permuted | [perm_tp1] | [test] |
| ddf843ad97 | qwen_3p5 | none | 0 matches for `qwen_3p5`, `qwen3.5`, `qwen35` | | |
| 72e1191804 | qwen_3p5_4b | 812-824 | ingested-qwen-3.5-4b | [tp1, tp2, tp4] | [test] |
| 72e1191804 | gemma_4_e4b_it | 857-870 | ingested-gemma-4-e4b-it | [tp1, tp2, tp4] | [test] |
| 72e1191804 | gemma_4_e4b_it_permuted | 872-886 | ingested-gemma-4-e4b-it-permuted | [perm_tp1] | [test] |

- All three entries have `support_level: cpp_plugin` and `source: generated`.
- Both models exist at 72e1191804. Only the two Gemma entries exist at ddf843ad97. origin/main also has 0 `qwen_3p5` matches.
- The model's branch adds 14 lines to config/models.yaml against the merge base; ddf843ad97 changes none.

## 7. State of PR #5022
```
{"baseRefName":"main","headRefName":"jhan-amx-kvmul16","headRefOid":"ddf843ad97f8602fc1171458e42036ef03b6e4c4","isDraft":false,"mergeStateStatus":"BLOCKED","mergeable":"MERGEABLE","reviewDecision":"CHANGES_REQUESTED","state":"OPEN","updatedAt":"2026-11-20T18:27:51Z"}
```
- Title: "AMX attention: serve kv_mul 16 (Muse Glimmer) with a group_heads template parameter".
- The review decision is CHANGES_REQUESTED, so the head may move. Check `headRefOid` again before the port starts.

## Port plan facts
- Source: commit 882e5322f1. Target: a new branch off ddf843ad97.
- A plain `git cherry-pick 882e5322f1` gives 5 conflicted files and 29 regions (git 2.34.1). The hand work, in dependency order:
  1. h/tron/tensor/v_vnni.hpp: no hand work.
  2. h/tron/kernels/amx_attn_iface.hpp: 6 comment regions. The code part (namespace `amx_attn_h256g4`) is already in place. Settle the naming questions C2 and C4 here, as the later files use the names.
  3. src/tron/kernels/amx_attn.cpp: no text conflict, but review C5 and C6 by hand (`store_query_rows` duplicates `transpose_scores<GROUP_HEADS_4>`).
  4. h/tron/models/self_attention.hpp: 6 regions.
     - Regions 3-5 (pack, QK, PV): keep Part B's `if constexpr (amx_serves_256x4<geometry>)` branch, and in the else branch keep PR #5022's call with `<operation_kv_mul>`.
     - Region 6: keep PR #5022's `row` view.
     - Region 2: Part B's grow-only resize is its behavior change; rewrite the comment for 4 or 16 heads.
     - Region 1: comment.
  5. t/CMakeLists.txt: 1 region. Keep PR #5022's registration (ddf843ad97:621-625). Take only Part B's comment for `t_amx_dispatch_dtype` (882e5322f1:696). Do not take `FILES t_amx_numerics.cpp t_amx_gdn_numerics.cpp`: that file does not exist at ddf843ad97.
  6. t/t_amx_dispatch_dtype.cpp: 9 regions. PR #5022's version is the larger one (404 lines); the head size must become a further template parameter of `exercise_page` (C10), plus the 3 `amx_attn_h256g4` fakes and the 2 new sections.
  7. t/t_amx_numerics.cpp: 7 regions. Two test layouts must be made one (C11, C13, C14).
- Outside the 7 files:
  - changelog.d/README.md (ddf843ad97) asks for a fragment `<PR>.<section>.md` per notable PR; PR #5022 has changelog.d/5022.changed.md.
  - config/test-benchmarks.json has rows for both tests (ddf843ad97:151-152, 494-495).
- Must stay untouched of PR #5022's code:
  - `group_heads_ok`, `GROUP_HEADS_16`, the 128 `shape_ok`;
  - the 3 kernel templates and their 6 explicit instantiations;
  - amx_attn_transpose.hpp;
  - the `<operation_kv_mul>` call sites, `s_pages{uninitialized}`, the `row` view, the removal of `<cstring>`;
  - the `SKIP` handling and the `SKIP_RETURN_CODE 4` registration;
  - the 16-head and 32-head sections, the transpose case;
  - the 2 probes in t_llama_unit.cpp, changelog.d/5022.changed.md, the `skip_return_codes` rows.
- Measurement build: applying PR #5022's net change onto the model's branch (0 conflicts) avoids the 9 conflicts of the full merge. With Part A present, 3 one-region conflicts appear.

## Not verified
- No compile and no test run of any merged result.
- The attention shape of Gemma 4 E4B (head size, kv_mul) is not stated in the repository files I read. Whether a model on PR #5022's branch uses the 256 x 4 kernels is therefore not verified; the generated plugin header of ingested-gemma-4-e4b-it would resolve it.
- Conflict counts under a git newer than 2.34.1.
- Whether the ported Part B commit applies cleanly onto "72e1191804 + PR #5022's net change" (that commit does not exist yet).
- The review comments behind CHANGES_REQUESTED on PR #5022 were not read.
