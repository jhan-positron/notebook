### 3.1 The four PRs

PR-1 "VNNI K: the layout, its AVX-512 reader and the FPGA staging path" (base main, ready for review)

- Content: L + R + G + B minus the deb preset line and the README deb paragraph. 23 files, +1846/-160 (added/removed lines by git numstat), of which 965 added lines are tests (t_k_vnni_layout +474, t_llama_unit +469/-78, t_amx_dispatch_dtype +16/-7, the three gof test lambdas +5/-5, t/CMakeLists.txt +1) and 881 added lines are code (tensor/k_vnni.hpp +335, kv_cache.hpp +235/-38, kernels/k_vnni.hpp +128, self_attention.hpp +53/-9, gof.hpp + gof.cpp + full.hpp +39/-12, model.hpp +23/-1, kv_cache_fwd.hpp +16/-3, attn_stats.hpp +4/-3, amx_attn_iface.hpp +1, CMake option + CI flag + README + cost rows +47/-5).
- Purpose and consumer: the typed VNNI K tensor and views (Ben's 2026-09-21 request), the per-row store in save_k, the AVX-512 reader as the software path, the FPGA staging gather. The consumers inside the PR are the reader, the staging path and the tests. The CI lane compiles it (`-DTRON_K_VNNI=ON` in cmake-single-platform.yml).
- Standalone claim: with the option off, no behaviour change. With the option on and no AMX: decode TPS +4 to +5 % vs the row-major dotter (table in 2.3, old base, needs a re-run against the latest main). With the option on and AMX: -7 to -11 % decode TPS until PR-2 (same table, the kill-switch arm as a proxy).
- What a reviewer checks: the index map and its anchors, the typed owner and the constness rules of the views, page::k() constrained to row-major slots, set_k_row / get_k_row, copy_storage_slot, the reader's masked loads and add order, the staging scratch contract, the CMake PUBLIC definition for the generated model objects.
- Temporary code: the three places of section 2.2.
- Known items it inherits from the 4424 body: the genoa96 cost row, the kv_mul 3/8 reader slowdown (llama-3.2-3b -1.4 %, qwen-3-30b-a3b), the benchmark-binary mismatch of the legacy workflow, the kill-switch and token divergence item (#4444: the reader replaces the dotter for partial pages), the widened test tolerance in t_llama_unit.

PR-2 "VNNI K: the AMX QK kernel reads the plane as its B operand" (base PR-1, draft)

- Content: A. 9 files, +279/-61: amx_attn.cpp (pack_q_rows_128x4, qk_vnni_128x4, tile names), amx_attn_iface.hpp (declarations, Note [QK orientation] paragraph), the two if-constexpr sites in self_attention.hpp, the bit-identity case of t_amx_numerics, the t_amx_dispatch_dtype fakes, the typed-boundary probe in t_llama_unit, and the removal of PR-1's temporary gate.
- Purpose: the reason the layout exists. The kernel computes S = Q K^T without the register transpose.
- Standalone claim: decode TPS +6.1 / +7.1 / +10.4 % at prompt 1024 / 2048 / 8192 vs main's AMX kernel (qwen3-4b tp2 8 users, 2026-09-14, old base); TTFT +2.2 / 0.0 / -1.8 % at tp2 and +7.8 % at tp4 prompt 1024 (the per-row scatter cost, removed by PR-3). Needs a re-run against the latest main.
- What a reviewer checks: the tile orientation, the padded Q rows, the 16-row tile store and the 4-row copy-out, bit identity against qk_rowmajor_128x4 (t_amx_numerics), the dispatch under the option.
- Reviewers: the AMX readers (Ben, Bill). This is the PR where the user's premise pays: PR-1 has no AMX instruction, so the non-AMX reviewers can review it without the kernel.

PR-3 "VNNI K: shared block save" (base PR-2, draft)

- Content: S. 8 files, +673/-72: store_block + transpose_16x16_epi32 (tensor/k_vnni.hpp +85/-6), page::set_k_block (kv_cache.hpp +35/-7), save_k work units, window, worker_ix / n_workers, Note [Shared block save], the join watchdog (model.hpp +298/-36), batch::k_store_window_t (common.hpp +29), the helper-side save_k emission (TronCpp.hs +24/-3, LoopyTronSpec.hs +24/-2), the block-save test (t_k_vnni_layout +90) and the three-thread save_k case (t_llama_unit +88/-18); added/removed lines by git numstat. Ben's only inline thread (r4065141577, the worker_ix fold) lives here and is already answered by the code.
- Purpose: the per-row scatter store of PR-1 costs 105 ns per (token, KV head) row in prefill (0.86 ms per layer, 2026-09-14 trace). The block save and the sharing with the idle main helpers remove it.
- Standalone claim: TTFT at prompt 1024 -128 ms at tp2 and -254 ms at tp4 vs the scatter store, and -45 / -88 ms vs main's AMX base; TPS unchanged within 0.4 % (2026-09-15, exec/results/vnnik2-20260915). Needs a re-run against the latest main.
- What a reviewer checks: the window protocol (acquire / release pairs, the join), the work-unit cut (a unit never crosses a page, a block or a change of token_jobs_do_kv), the generated call sites on both sides, the deadlock argument, the watchdog.
- Construction note: the save_k unit test of this PR should be taken from the pre-T blob 522acb4792 of t_llama_unit.cpp (the S-only form), not rebuilt by hand.
- Main drift: main changed TronCpp.hs by 442 lines since the merge base. The two Haskell hunks of S are the ones most likely to conflict when the stack takes main.

PR-4 "VNNI K: keep short K-cache writes row-major; convert at the forward end; row-major under hardware attention; deb preset" (base PR-3, draft)

- Content: T + the preset commit. 12 files, +1466/-115: the saved-row and converted-block bits, note_k_row_saved / note_k_block_saved, pending_k_blocks and convert_pending_k_blocks, block_to_vnni / block_to_rows, row_major_row / k_row_if_row_major, k_forget_row, the dense gate k_layout_dense, the dotter scoring of tail rows, Note [Row-major tail block], Note [Row-major blocks under hardware attention], the tests (t_k_vnni_layout +500/-2, t_llama_unit +140/-4, t_amx_dispatch_dtype +35/-5; added/removed lines by git numstat), CMakePresets.json deb line, the README deb paragraph.
- Purpose: issue #4500 (the FPGA-attention decode loss of the per-token 64-line column access) and token identity with main under CPU attention.
- Standalone claim: qwen3-4b FPGA attention decode from -3.8 % (tp2) / -11.8 % (tp4) to within noise (-0.9 % / -0.4 % n.r., 2026-10-09 whole machine); tokens identical to main under CPU attention at prompt 1024 and 8192 (2026-10-09 precheck). The final stack vs main on the 14 nightly configs: llama-8b 32 users at 4096 +4.8 % TPS, qwen 8k software attention +7.6 %, llama-3.2-3b -1.4 % (kv_mul 3 item of PR-1), memory within 0.3 %. These numbers are valid for PR-4 as long as its final tree equals today's head modulo main drift.
- What a reviewer checks: the invariant "block VNNI iff its 16 bits are set", the three writers of the bits (save_k, clear, copy), the readers (dense gate, software loop, staging), the forward-end conversion after wait_for_coop_gof, the static policy per operation under hardware attention.
- Optional further cut: the hardware-attention policy (commit 452b2052c9 content, about 60 code lines + 2 test sections) could be a PR-5. Not recommended unless a reviewer asks: it is small and its measurement (qwen tp4 TTFT -6.4 %) belongs with T.
## Update 2 (2026-10-10, facts from the seam checks that Update 1, U1.9 and the addendum do not carry)

Short version: three facts from the seam checks change the plan text. None changes the recommendation of section 3. They add one decision (D10), one line to PR-4's construction, and two test runs to PR-1's verification. The token-identity cells, the build-location point and the PR-2 tree check are already in U1.9 and the addendum (U1A.1 to U1A.5) and are not repeated here.

### U2.1 PR-3 carries a masked partial-block path that PR-4 deletes (new decision D10)

At the S stage of the probe (3c56db9a95, the tree of PR-1 + S), a run of 2 to 15 consecutive tokens of one block goes through a masked block store. The code: `k_scatter_run_len = 1` [h/tron/models/model.hpp:3141 at 3c56db9a95], the branch test `if (n == k_scatter_run_len)` [:3260], the call `set_k_block(slot, kv_head, c, present, rows)` with a 16-bit present mask [:3292], and page::set_k_block with its `__mmask16 present` parameter [h/tron/models/kv_cache.hpp:2040-2046 at 3c56db9a95].

PR 4737 replaced that path. A run shorter than a block is stored row by row into the row-major tail block, the branch test is `n < k_store_block`, and set_k_block has no mask [head h/tron/models/model.hpp:3300, h/tron/models/kv_cache.hpp:2277-2284]. So with the recommended order PR-3 ships about 15 lines of partial-block logic that PR-4 removes. The reviewer of PR-3 reads them once for nothing. At the head, store_block's masked branch is reached only by the test t_k_vnni_layout [h/tron/tensor/k_vnni.hpp:410-416; the two production callers kv_cache.hpp:2283 and tensor/k_vnni.hpp:508 pass the full mask].

Decision D10, two options:

- (a) Keep PR-3 as the tested tree (the content of 3c56db9a95, re-based on PR-2). The masked path is live production code in PR-3 and PR-4 replaces it. PR-3's body says so. Cost: about 15 lines of review churn.
- (b) Pre-simplify PR-3: a run shorter than a block takes the per-row store (set_k_row), only a whole block takes set_k_block, and the mask parameter goes. Est. 10 to 15 changed lines in model.hpp and kv_cache.hpp plus the mask rows of the block-save test [t/t_k_vnni_layout.cpp:237-261]. Cost: PR-3's tree then differs from the tested 3c56db9a95, the T diff needs a hand repair at those lines, and the 2026-09-15 TTFT numbers were measured with the masked path.

Recommended: (a). Reason: every stack tree stays equal to a tested tree, and the per-PR re-measurement of section 5 costs the same either way.

### U2.2 PR-4 construction: keep `#include <cstring>` in h/tron/kernels/k_vnni.hpp
