# Classification of diff-vs-ref.patch (the PR-4 stack invariant)

## Short version

The diff ~/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material/probe-pr4/diff-vs-ref.patch has 56 hunks in 16 files (+340/-199 lines). Every hunk is explained: 3 are D2, 10 are PR-1 review fixes, 24 are PR-2 pre-review edits, 14 are PR-3 step-2/step-5 edits, 4 are probe resolutions, 1 is the cstring include, 0 are main drift, 0 are UNEXPLAINED. Three things need the author's attention: the allowed-difference list of split-handoff.md step 4.3 does not cover the review-fix code lines that are in the stack, the kv_cache.hpp D2 comment line is not in that list, and the probe keeps `#include <cstring>` in two files where step 4.2 says "exactly one".

## Words used here

- Reference: commit c4bf86005a in the worktree ~/workspace/ai-runs/tron-split-probe-pr4ref. Its parents are 0a5334ccb6 (the PR 4424 head) and 72308ec90c (main) [git log -1 c4bf86005a: "reference: main 72308ec90c merged into the PR 4424 head 0a5334ccb6"].
- Probe tree: the worktree ~/workspace/ai-runs/tron-split-probe-pr4 at HEAD 80bce9a08d (the PR-3 head) with 12 staged files (the T and B patches applied and resolved) [git status --short in that worktree].
- The patch: `git diff c4bf86005a` run in the probe tree. I re-ran it: the working-tree diff and the index diff (`--cached`) are both byte-identical to the patch file (cmp exit 0).
- D2: the decision to drop the CMake rule "TRON_K_VNNI requires TRON_AMX_DISPATCH" [split-handoff.md:41]. PR-1 did it in commit c3334a079f "VNNI K: the layout needs no AMX dispatch".
- PR-1 review fixes: commits dbe32b8af4, 07f072bdf1, 7633d56c8f, 82d05e94be on jhan-vnnik-1-layout (the last four commits before the head 82d05e94be) [git log --first-parent be0d5565b3..82d05e94be].
- PR-2 pre-review edits: text that is in PR-2's commits (de39dc3de7, 0ee8671d35) but not in the A patch handoff-material/ref/PR2-diff-76a0..4d3a.patch (the PR-2 content as it is inside PR 4424). pr2 diff = `git diff 82d05e94be 0ee8671d35`.
- PR-3 edits: pr3 diff = `git diff 0ee8671d35 80bce9a08d`. Step 2 = the k_destination_row edit in store_k_block; step 5 = the seven pre-review items of split-status.md [split-status.md:322-331].
- Probe resolution: one of the six conflict blocks CONFLICTS[0..5] or the two EDITS of handoff-material/probe-pr4/resolve.py.
- A patch: handoff-material/ref/PR2-diff-76a0..4d3a.patch. T patch: handoff-material/ref/T-4737-merge.diff. B patch: handoff-material/ref/B-preset.diff.
- Patch line: the line number inside diff-vs-ref.patch where the hunk header sits.

## UNEXPLAINED hunks

None. 0 of 56.

## Main drift

None possible and none found. PR-1's main merge a711aeee83 has the second parent 72308ec90c [git log -1 --format=%P a711aeee83]. The reference c4bf86005a has the same second parent 72308ec90c. So both trees contain the same main commit, and every hunk below is attributed to a stack commit or to the probe.

## The --stat of the patch

`git apply --numstat` on the patch file (added / deleted lines):

| File | + | - |
|---|---|---|
| CMakeLists.txt | 1 | 1 |
| README.ci.md | 5 | 3 |
| h/tron/kernels/amx_attn_iface.hpp | 31 | 20 |
| h/tron/kernels/k_vnni.hpp | 12 | 8 |
| h/tron/models/kv_cache.hpp | 17 | 15 |
| h/tron/models/model.hpp | 18 | 18 |
| h/tron/models/self_attention.hpp | 11 | 11 |
| h/tron/tensor/k_vnni.hpp | 15 | 7 |
| ingest/src/TronCpp.hs | 5 | 5 |
| src/tron/CMakeLists.txt | 0 | 6 |
| src/tron/kernels/amx_attn.cpp | 6 | 1 |
| t/t_amx_dispatch_dtype.cpp | 12 | 5 |
| t/t_amx_numerics.cpp | 40 | 13 |
| t/t_k_vnni_layout.cpp | 3 | 34 |
| t/t_llama_unit.cpp | 111 | 45 |
| t/t_phase1_integration.cpp | 53 | 7 |
| total: 16 files | 340 | 199 |

This equals handoff-material/probe-pr4/diff-vs-ref-stat.txt ("16 files changed, 340 insertions(+), 199 deletions(-)"). Two staged files of the probe, CMakePresets.json and h/tron/scheduler/full.hpp, show no difference against the reference: the T and B patches applied there cleanly and the result equals the PR 4424 head.

## Count per class

| Class | Hunks | Hunk numbers |
|---|---|---|
| UNEXPLAINED | 0 | - |
| main drift resolved differently | 0 | - |
| D2 | 3 | 1, 13, 35 |
| PR-1 review fix dbe32b8af4 | 3 | 28, 29, 31 |
| PR-1 review fix 07f072bdf1 | 3 | 54, 55, 56 |
| PR-1 review fix 7633d56c8f | 2 | 50, 51 |
| PR-1 review fix 82d05e94be | 2 | 47, 48 |
| PR-2 pre-review wording | 24 | 2, 3, 4, 5, 6, 8, 9, 10, 14, 16, 24, 25, 26, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 49 |
| PR-3 step-2 edit | 2 | 19, 20 |
| PR-3 step-5 edit | 12 | 17, 18, 21, 22, 23, 30, 32, 33, 34, 46, 52, 53 |
| probe resolution | 4 | 7, 12, 15, 27 (hunk 53 also contains CONFLICTS[4], CONFLICTS[5] and EDITS 1-2, counted under PR-3) |
| cstring include (U2.2) | 1 | 11 |
| total | 56 | |

## Hunk by hunk

Column "evidence" names the commit or diff that carries the same lines. "pr2 diff" and "pr3 diff" are defined above. "identical blob ids" means the hunk's index line in the patch has the same before/after blob ids as the named commit, so the whole file differs only by that commit.

| # | File | Hunk header (patch line) | What changes | Class | Evidence |
|---|---|---|---|---|---|
| 1 | CMakeLists.txt | @@ -44,7 +44,7 @@ (5) | The TRON_K_VNNI option help drops "(requires TRON_AMX_DISPATCH; ...)". | D2 | c3334a079f, same hunk, identical blob ids 1127ae1a28..bf4296125c |
| 2 | README.ci.md | @@ -597,9 +597,11 @@ (18) | The reference's one sentence naming the three tests becomes three sentences: t_k_vnni_layout and save_k exercise the store, reader and page copy; the VNNI kernel case of t_amx_numerics exercises the store and qk_vnni_128x4; it compiles in every TRON_AMX_DISPATCH=ON build. | PR-2 pre-review wording | pr2 diff README.ci.md @@ -594,7 +594,10 @@, identical added lines; the reference's sentence is in the A patch |
| 3 | h/tron/kernels/amx_attn_iface.hpp | @@ -24,7 +24,9 @@ (37) | Adds "With TRON_K_VNNI the roles swap: Q is the A operand ... K plane is the B operand". | PR-2 pre-review wording | pr2 diff @@ -24,7 +24,9 @@; "the roles" absent from the A patch |
| 4 | amx_attn_iface.hpp | @@ -102,9 +104,10 @@ (48) | "Both QK kernels store their result tiles into a buffer inside the kernel (s_transposed ..., s16 ...)". | PR-2 pre-review wording | pr2 diff @@ -103,9 +104,10 @@ |
| 5 | amx_attn_iface.hpp | @@ -139,8 +142,9 @@ (62) | The Q_PACK_ELEMS_2048 comment describes the output of either packer. | PR-2 pre-review wording | pr2 diff @@ -140,8 +142,9 @@ |
| 6 | amx_attn_iface.hpp | @@ -151,8 +155,9 @@ (74) | The scalar gate comment names both query packers. | PR-2 pre-review wording | pr2 diff @@ -152,8 +155,9 @@ |
| 7 | amx_attn_iface.hpp | @@ -217,15 +222,17 @@ (86) | Note [QK orientation], the VNNI paragraph: keeps PR-2's panel definition "(a panel is 16 dimension-pair rows x 16 tokens, one B tile; ...)" and "The extra work moves to the K save.", then the T patch's store-path sentences (block save, row-major short run, in-place transpose, the tail block keeps the dotter). | probe resolution, resolve.py CONFLICTS[0] | resolve.py block 1 (its "resolution" text equals the added lines); PR-2 wrote the panel definition (pr2 diff @@ -214,18 +218,55 @@); PR-3 rewrote the tail to "two places" (pr3 diff @@ -224,9 +224,11 @@); the removed lines are the T patch's |
| 8 | amx_attn_iface.hpp | @@ -243,8 +250,9 @@ (113) | pack_q_rows_128x4 contract: "One query-pack slot (amx_qpack_slot in self_attention.hpp) therefore serves either layout. The build's K layout picks one packer and one kernel (k_vnni::layout_on)." | PR-2 pre-review wording | pr2 diff, the pack_q_rows_128x4 declaration block; "One slot" (reference) is in the A patch |
| 9 | amx_attn_iface.hpp | @@ -256,7 +264,10 @@ (125) | qk_vnni_128x4 contract adds "For the same K and Q the scores are bit-identical to qk_rowmajor_128x4's ... (t_amx_numerics checks the identity)." | PR-2 pre-review wording | pr2 diff, the qk_vnni_128x4 declaration block |
| 10 | h/tron/kernels/k_vnni.hpp | @@ -1,8 +1,11 @@ (141) | File header: "It serves every page the AMX kernel qk_vnni_128x4 does not take: partial or partly visible pages, hosts without AMX, the kill switch, builds without TRON_AMX_DISPATCH, and the shapes and query types outside the AMX gate". | PR-2 pre-review wording | pr2 diff @@ -1,9 +1,11 @@, identical; the reference's "It serves partial pages, hosts" is the A patch's |
| 11 | kernels/k_vnni.hpp | @@ -12,6 +15,7 @@ (156) | `#include <cstring>` added. | cstring include (U2.2) | PR-3 head has it at kernels/k_vnni.hpp:18 and not in tensor/k_vnni.hpp; the PR 4424 head has it at tensor/k_vnni.hpp:46 only; the probe has both (kernels:18, tensor:46) |
| 12 | kernels/k_vnni.hpp | @@ -44,11 +48,11 @@ (164) | qk_group comment: "one of the two layout-specific score kernels allowed to take the plane address (the other is amx_attn_h128g4::qk_vnni_128x4)". | probe resolution, resolve.py CONFLICTS[1] | resolve.py block 2; the naming is PR-2's (pr2 diff @@ -42,9 +44,10 @@); the T patch's live-bit sentences stay (context lines) |
| 13 | h/tron/models/kv_cache.hpp | @@ -650,8 +650,8 @@ (185) | Note [K VNNI storage] first sentence: "(CMake option, default OFF, requires TRON_AMX_DISPATCH)" becomes "(CMake option, default OFF)". | D2 | c3334a079f kv_cache.hpp @@ -650,8 +650,8 @@, identical lines; neither pr2 diff nor pr3 diff touches line 650. NOT in the step 4.3 D2 list (see concerns) |
| 14 | kv_cache.hpp | @@ -669,9 +669,9 @@ (196) | The "Why" paragraph: "the AMX QK kernel (qk_vnni_128x4) reads the VNNI plane directly as its B operand. It computes ... the softmax wants. So ...". | PR-2 pre-review wording | pr2 diff @@ -666,14 +666,13 @@; the reference's form is in the A patch |
| 15 | kv_cache.hpp | @@ -782,14 +782,16 @@ (209) | Consumer item 3: "every other visit of a VNNI slot reads the VNNI blocks with k_vnni::qk_group, with the same view: partial or partly visible pages, the kill switch, hosts without AMX, builds without TRON_AMX_DISPATCH, and the shapes and query types outside the AMX gate ..." plus the T patch's tail-block sentence. | probe resolution, resolve.py CONFLICTS[2] | resolve.py block 3; the visit list is PR-2's item 3 (pr2 diff @@ -681,13 +680,15 @@) |
| 16 | kv_cache.hpp | @@ -2107,8 +2109,8 @@ (234) | k_packed accessor comment: "and the AVX-512 reader k_vnni::qk_group reads it one token per lane". | PR-2 pre-review wording | pr2 diff @@ -1986,8 +1985,9 @@ |
| 17 | h/tron/models/model.hpp | @@ -3086,12 +3086,14 @@ (249) | Note [Shared block save] opening: "and one set_k_row scatter per token on the main thread alone", "the test server delphi-3bda", "model qwen3-4b", "for that per-token store". | PR-3 step-5 edit, item 2 | pr3 diff line 161; split-status.md:324 |
| 18 | model.hpp | @@ -3150,6 +3152,7 @@ (270) | Comment on k_store_block: "Tokens per page block: the size of one block save and the longest run." | PR-3 step-5 edit, item 3 (wade-9) | pr3 diff line 220; split-status.md:325 |
| 19 | model.hpp | @@ -3310,9 +3313,7 @@ (278) | In store_k_block's per-row path, the converted row is built with `k_destination_row<geometry.kv.head_size>(conv[0]).set(kout)` instead of the spelled-out view type. | PR-3 step-2 edit | pr3 diff line 352 (conv[0]); PR-1's 82d05e94be used `row`, which PR-3 replaced (pr3 diff line 478 removes it) |
| 20 | model.hpp | @@ -3329,9 +3330,7 @@ (289) | The block path: `k_destination_row<...>(conv[i]).set(kout)`. | PR-3 step-2 edit | pr3 diff line 366 |
| 21 | model.hpp | @@ -3358,8 +3357,8 @@ (300) | worker_ix assert message "save_k: worker_ix {} is not below n_workers {}" formats n_workers, not n_workers - 1. | PR-3 step-5 edit, item 3 (concurrency-3) | pr3 diff line 394; split-status.md:325 |
| 22 | model.hpp | @@ -3408,7 +3407,7 @@ (311) | Join-watchdog message: "units claimed). The helpers' ..." (no semicolon). | PR-3 step-5 edit, item 3 (plain-5) | pr3 diff line 443 |
| 23 | model.hpp | @@ -3458,9 +3457,10 @@ (320) | save_k overload comment: "run() passes 0 and n_workers, and run_main_help passes its worker_ix and n_workers." | PR-3 step-5 edit, item 3 | pr3 diff line 497 |
| 24 | h/tron/models/self_attention.hpp | @@ -254,10 +254,10 @@ (338) | amx_qpack_slot comment: names Note [K VNNI storage], "both packers' 64-byte alignment contract". | PR-2 pre-review wording | pr2 diff @@ -254,9 +254,10 @@ |
| 25 | self_attention.hpp | @@ -1698,12 +1698,12 @@ (353) | The pack comment reordered: "A and B are the left and right matrices ..." first; ends "(pair-interleaved columns)". | PR-2 pre-review wording | pr2 diff @@ -1693,8 +1695,20 @@ |
| 26 | self_attention.hpp | @@ -1763,7 +1763,7 @@ (372) | "It reads K straight from storage" becomes "It reads K directly from storage". | PR-2 pre-review wording | pr2 diff @@ -1748,11 +1762,15 @@ |
| 27 | h/tron/tensor/k_vnni.hpp | @@ -6,9 +6,9 @@ (385) | File header names "the AMX QK kernel in h/tron/kernels/amx_attn_iface.hpp" next to the AVX-512 reader; keeps the T patch's conversion sentence. | probe resolution, resolve.py CONFLICTS[3] | resolve.py block 4; the kernel sentence is PR-2's (pr2 diff @@ -3,8 +3,9 @@), kept by PR-3's header resolution (pr3 diff @@ -3,9 +3,9 @@) |
| 28 | tensor/k_vnni.hpp | @@ -345,12 +345,15 @@ (398) | store_row: `TRON_ASSERT_LT(token, Rows);` and the three comment lines on the index check. | PR-1 review fix dbe32b8af4 | dbe32b8af4 @@ -283,11 +283,15 @@, identical lines |
| 29 | tensor/k_vnni.hpp | @@ -363,12 +366,13 @@ (415) | load_row: `TRON_ASSERT_LT(token, Rows);` and "The token index is checked as in store_row." | PR-1 review fix dbe32b8af4 | dbe32b8af4 @@ -300,12 +304,13 @@ |
| 30 | tensor/k_vnni.hpp | @@ -390,13 +394,16 @@ (430) | store_block: `TRON_ASSERT_LT(c, Rows / k_vnni::BLOCK_TOKENS_16);` and three comment lines. | PR-3 step-5 edit, item 1 | pr3 diff lines 661-670; split-status.md:323 |
| 31 | tensor/k_vnni.hpp | @@ -422,7 +429,8 @@ (448) | copy_token comment: "Both token indices are checked by those two operations." | PR-1 review fix dbe32b8af4 | dbe32b8af4 @@ -319,7 +324,8 @@ |
| 32 | ingest/src/TronCpp.hs | @@ -2866,9 +2866,9 @@ (462) | Helper-side comment in short sentences ("Main passes worker index 0 ... The helpers pass their own worker_ix."). | PR-3 step-5 edit, item 4 (plain-9) | pr3 diff lines 710-711; split-status.md:326 |
| 33 | TronCpp.hs | @@ -2879,7 +2879,7 @@ (475) | Helper side: `Var "worker_ix", Var "n_workers"` instead of `ExprLit`. | PR-3 step-5 edit, item 4 (wade-10, tron-3) | pr3 diff line 723 |
| 34 | TronCpp.hs | @@ -2941,7 +2941,7 @@ (484) | Main side: `Var "n_workers"` instead of `ExprLit "n_workers"`. | PR-3 step-5 edit, item 4 | pr3 diff line 739 |
| 35 | src/tron/CMakeLists.txt | @@ -229,13 +229,7 @@ (497) | The three justification comment lines and the `if(NOT TRON_AMX_DISPATCH)` FATAL_ERROR block removed. | D2 | c3334a079f, same hunk, identical blob ids da5ca0cca4..9a659b3368 |
| 36 | src/tron/kernels/amx_attn.cpp | @@ -262,9 +262,14 @@ (515) | Two static_asserts (LINE_BYTES_64 == TILE_ROW_BYTES_64; PANEL_BYTES_1024 == TILE_ROWS_16 * TILE_ROW_BYTES_64) and the comment "Token block b (0..3) accumulates its scores in accumulator tile b". CODE: 4 static_assert lines. | PR-2 pre-review wording | pr2 diff, the qk_vnni_128x4 body carries both static_asserts and the comment; "k_vnni::LINE_BYTES_64 == TILE_ROW_BYTES_64" is absent from the A patch |
| 37 | t/t_amx_dispatch_dtype.cpp | @@ -6,12 +6,15 @@ (535) | File header: both packers count into the probe, the VNNI packer counts a second time; "values. The dense QK and PV kernels run once each." | PR-2 pre-review wording | pr2 diff @@ -5,15 +5,16 @@ |
| 38 | t_amx_dispatch_dtype.cpp | @@ -58,6 +61,7 @@ (556) | Probe field `size_t rows_pack_calls = 0;`. CODE. | PR-2 pre-review wording | pr2 diff @@ -59,6 +60,7 @@; "rows_pack_calls" absent from the A patch |
| 39 | t_amx_dispatch_dtype.cpp | @@ -213,6 +217,8 @@ (564) | `REQUIRE(probe.rows_pack_calls == (packs && k_vnni::layout_on<head_size> ? 1 : 0));`. CODE. | PR-2 pre-review wording | pr2 diff @@ -192,6 +192,8 @@ |
| 40 | t_amx_dispatch_dtype.cpp | @@ -278,6 +284,7 @@ (573) | `++probe.rows_pack_calls;` in the pack_q_rows_128x4 fake. CODE. | PR-2 pre-review wording | pr2 diff, the pack_q_rows_128x4 fake |
| 41 | t/t_amx_numerics.cpp | @@ -9,6 +9,8 @@ (585) | File header: "The VNNI QK case pins qk_vnni_128x4 to qk_rowmajor_128x4 bit for bit instead". | PR-2 pre-review wording | pr2 diff @@ -9,12 +9,15 @@ |
| 42 | t_amx_numerics.cpp | @@ -117,8 +119,9 @@ (594) | Packer case comment names both packers. | PR-2 pre-review wording | pr2 diff @@ -115,8 +119,9 @@ |
| 43 | t_amx_numerics.cpp | @@ -145,6 +148,26 @@ (606) | New SECTION "A operand rows, pack_q_rows_128x4": poison 0x7f7f padding, rows 0..3 compared, padding rows must stay. CODE: 20 lines. | PR-2 pre-review wording | pr2 diff @@ -143,6 +148,26 @@, identical; the section name is absent from the A patch |
| 44 | t_amx_numerics.cpp | @@ -195,16 +218,18 @@ (633) | The identity case's comment rewritten (A and B defined, "steps 0 to 3 into one zeroed accumulator", "32-bit dword"). | PR-2 pre-review wording | pr2 diff, the identity TEST_CASE; the reference's form is in the A patch |
| 45 | t_amx_numerics.cpp | @@ -230,8 +255,10 @@ (662) | `s_row` zero-initialised and `std::memset(s_vnni, 0xff, ...)` with the comment "Different fill patterns". CODE: 2 lines. | PR-2 pre-review wording | pr2 diff, the identity TEST_CASE; "std::memset(s_vnni, 0xff" absent from the A patch |
| 46 | t/t_k_vnni_layout.cpp | @@ -264,37 +264,6 @@ (678) | The SECTION "a block save on top of other blocks changes only its own block" (31 lines) is absent. | PR-3 step-5 edit, item 5 (wade-2) | 0 hits for the section name at 80bce9a08d and at 0ee8671d35, 1 hit in the reference; split-status.md:327 |
| 47 | t_k_vnni_layout.cpp | @@ -384,8 +353,8 @@ (716) | Poison comment: "The check is that dead-token values do not reach live scores." | PR-1 review fix 82d05e94be | 82d05e94be @@ -216,8 +216,8 @@, identical lines |
| 48 | t_k_vnni_layout.cpp | @@ -397,7 +366,7 @@ (727) | "Dead-token score slots must retain this preset." | PR-1 review fix 82d05e94be | 82d05e94be @@ -229,7 +229,7 @@ |
| 49 | t/t_llama_unit.cpp | @@ -414,7 +414,8 @@ (740) | "The VNNI QK kernel accepts the view, and no other type, as its K argument. The other two kernels reject it." | PR-2 pre-review wording | pr2 diff @@ -407,8 +413,9 @@; "QK kernel takes its view and nothing else" (reference) is in the A patch |
| 50 | t_llama_unit.cpp | @@ -2790,18 +2791,28 @@ (750) | `v_star_tolerance` (5e-2 VNNI, 2e-2 row-major), the s_star matcher WithinRel for VNNI / WithinAbs 2e-6 for row-major, and the comment. CODE: 11 lines. | PR-1 review fix 7633d56c8f | 7633d56c8f @@ -2725,18 +2725,28 @@, identical lines |
| 51 | t_llama_unit.cpp | @@ -2934,7 +2945,8 @@ (783) | The second assert_allclose site uses `v_star_tolerance`. CODE. | PR-1 review fix 7633d56c8f | 7633d56c8f @@ -2869,7 +2879,8 @@ |
| 52 | t_llama_unit.cpp | @@ -3954,7 +3966,9 @@ (793) | `kv_slot_id slot` is no longer const, with the comment why. CODE. | PR-3 step-5 edit, item 6 | pr3 diff line 931; split-status.md:328 |
| 53 | t_llama_unit.cpp | @@ -4101,70 +4115,122 @@ (804) | The three-thread section rewritten: the name says "every row is stored once"; `shared_save`, `token_of`, `kv_of`, `block_of` lambdas; `check_window(n)` with helper_windows == n, `next_unit == n_units + n_workers`, the never-crosses loop and the new cut-only-at-a-change loop; a second window on `active_attention_operations[1]`. Inside this hunk the probe's EDITS 1 and 2 (resolve.py) re-add the reference's six post-join check lines (`check(before); check_marks(); check_blocks(false); convert_pending_k_blocks(); check_blocks(true); check(before)`) after each `shared_save`, and `pre_save();` before the second window's snapshot. CODE: whole section. | PR-3 step-5 edit, item 6 (plus resolve.py CONFLICTS[4], CONFLICTS[5], EDITS 1-2) | pr3 diff line 964 and the following section body; resolve.py CONFLICTS[4], [5] and EDITS; split-status.md:328 |
| 54 | t/t_phase1_integration.cpp | @@ -36,6 +36,7 @@ (969) | `#include "tron/tensor/k_vnni.hpp"`. | PR-1 review fix 07f072bdf1 | 07f072bdf1, same hunk, identical blob ids 43c9246041..579bbe012f |
| 55 | t_phase1_integration.cpp | @@ -834,30 +835,60 @@ (977) | The populate case stores K rows into one packed plane per head and its K callback gathers the row into the scratch. CODE. | PR-1 review fix 07f072bdf1 | 07f072bdf1, identical |
| 56 | t_phase1_integration.cpp | @@ -875,6 +906,21 @@ (1045) | Every staged K value checked through the K swizzle. CODE. | PR-1 review fix 07f072bdf1 | 07f072bdf1, identical |

## Checks that back the "PR-2 pre-review" class

- The PR-2 hunks' added text is absent from the A patch (0 lines for "the roles", "Both QK kernels store their result tiles", "rows_pack_calls", "A operand rows, pack_q_rows_128x4", "std::memset(s_vnni, 0xff", "k_vnni::LINE_BYTES_64 == TILE_ROW_BYTES_64").
- The reference-side text of those hunks is present in the A patch (1 line each for "One slot", "q_rows = the pack_q_rows_128x4 output.", "It reads K straight from storage" (2), "Token block b accumulates its scores in ACCUMULATOR_TILE_b", "The layouts are row-major, or under TRON_K_VNNI the VNNI", "QK kernel takes its view and nothing else", "the software path for partial pages, the kill switch", "Why: the AMX QK kernel reads the VNNI plane directly as its B operand. It"). So the reference carries the A patch's text and PR-2's commits carry edited text.

## PR-1-only sentences

All absent from the probe tree, as step 2.3 requires: 0 hits in the probe for "No AMX visit can occur", "Until the VNNI AMX kernel", "the layout-specific reader allowed", "temporary until". "and the AMX tile rows" is present in the probe at t/t_llama_unit.cpp:445 and in the reference at :444 (the same sentence, restored by PR-2). "requires TRON_AMX_DISPATCH": 0 hits in the probe, 4 in the reference (kv_cache.hpp:653, src/tron/CMakeLists.txt:234 and :237, CMakeLists.txt:47). These four reference lines are exactly hunks 13, 35 and 1.

## Items of the allowed list that produce no hunk today

- (3) config/test-benchmarks.json: no hunk. The probe's cost rows equal the reference's. The rows will differ after `bin/slice bench --update`.
- (4) D8 CI change: no hunk under nix/ (D8 is option c).


--- concerns ---
- Step 4.3 of split-handoff.md allows only D2 lines, comment wording, cost rows and the D8 change, and says "Nothing else in code". The probe tree differs from the reference in code at these explained places: PR-1 dbe32b8af4 (2 TRON_ASSERT_LT lines, hunks 28-29), 07f072bdf1 (t_phase1_integration rewrite, hunks 54-56), 7633d56c8f (v_star_tolerance and the s_star matcher, hunks 50-51); PR-2 pre-review (4 static_assert lines in amx_attn.cpp, hunk 36; the rows_pack_calls counter, REQUIRE and increment, hunks 38-40; the 20-line SECTION in t_amx_numerics, hunk 43; the memset lines, hunk 45); PR-3 (k_destination_row in store_k_block, hunks 19-20; the store_block TRON_ASSERT_LT, hunk 30; the assert message, hunk 21; the three Var tokens, hunks 33-34; the removed 31-line SECTION of t_k_vnni_layout, hunk 46; the rewritten three-thread section and the non-const slot, hunks 52-53). PR4-handoff.md must list these as allowed, by commit, or the executor's stop condition ("an unexplained code difference") fires on a correct tree.
- Hunk 13 (h/tron/models/kv_cache.hpp @@ -650,8 +650,8 @@: the Note [K VNNI storage] first sentence without "requires TRON_AMX_DISPATCH") comes from the D2 commit c3334a079f, but the step 4.3 list names only CMakeLists.txt:47 and the FATAL_ERROR block as D2. Add this line to the D2 item.
- The probe keeps `#include <cstring>` in both h/tron/kernels/k_vnni.hpp (line 18) and h/tron/tensor/k_vnni.hpp (line 46). split-handoff.md step 4.2 says "Keep exactly one include". kernels/k_vnni.hpp uses std::memcpy itself (line 108) and includes tensor/k_vnni.hpp (line 25), so either choice compiles (the probe's 38-cell matrix passed: pr4probe-38.log "MATRIX OK: 38 cells"). The author should state the choice in PR4-handoff.md: keep both (each file includes what it uses; hunk 11 stays an allowed difference) or drop the kernels one (hunk 11 disappears).
- Hunk 53 is one hunk with two sources: PR-3's step-5 rewrite of the three-thread section and the probe's EDITS 1-2 (resolve.py), which relocate the reference's post-join checks after each shared_save and add pre_save() before the second window. If the handoff asks the executor to classify hunks one by one, this hunk needs the two-source note or it looks partly unexplained.
- The classification of the 24 PR-2 hunks as "pre-review wording" rests on text comparison with the A patch (PR2-diff-76a0..4d3a.patch), not on a commit-level record of the pre-review edits. The task's list of ten PR-2 files matches the ten files that carry these hunks (README.ci.md, amx_attn_iface.hpp, kernels/k_vnni.hpp, kv_cache.hpp, self_attention.hpp, amx_attn.cpp, tensor/k_vnni.hpp, t_amx_numerics.cpp, t_amx_dispatch_dtype.cpp, t_llama_unit.cpp). No PR-2 hunk falls outside those files.
- The patch is a diff against the working tree; I confirmed the index diff is byte-identical, so the staged state equals the working tree. After the executor commits PR-4 and refreshes the cost rows, the step 4.3 comparison must be re-run on the pushed commit (the handoff already says twice), and config/test-benchmarks.json will then be a 17th file.
