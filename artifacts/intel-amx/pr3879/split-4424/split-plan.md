# Split plan for PR 4424 (VNNI K)

Written 2026-10-10 00:xx UTC by Claude, for jhan. Codex reviews this file and writes split-plan-codex.md. The update after that review is appended at the end of this file.

## Short version

PR 4424 is not one integral change. It is four features with one-directional dependencies, and two of the three cuts already existed as separate tested PRs (PR 4774 and PR 4737) before they were merged into 4424 on 2026-10-08. The split is technically sound: a probe built the candidate first PR (the layout, its AVX-512 reader, the FPGA staging, the build files) as a real git tree, and it passes a 22-cell clang syntax matrix with 0 errors; the recommended stack is PR-1 layout + readers (about 1,850 lines, 52 % tests), PR-2 AMX kernel on the plane (about 280 lines), PR-3 shared block save (about 670 lines), PR-4 row-major tail block + hardware-attention policy + deb preset (about 1,460 lines), merged in that order.

## Words used here

- PR 4424: positron-ai/tron pull request "VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save". Draft, base main, head 0a5334ccb6, merge base be0d5565b3, 29 files, +4054/-198 lines.
- AMX: Intel Advanced Matrix Extensions, the tile instruction set. AVX-512: the 512-bit vector instruction set. VNNI layout: the pair-interleaved operand layout the AMX tile multiply reads as its right operand.
- K cache: the saved key vectors of past tokens. KV page: a 64-token block of the K and V caches. kv_mul: the number of query heads that share one KV head.
- Concern: one feature of the PR, named by a letter below (L, R, G, A, S, T, B).
- Stack: a chain of PRs where each one is based on the previous one. The repo rule (AGENTS.md:12-13): only the PR based on main may be ready for review; every descendant stays draft; after the parent merges, promote only the next PR.
- Probe: a scratch git branch (jhan-split-probe, worktree ~/workspace/ai-runs/tron-split-probe) built tonight to test whether the cuts compile. Nothing of it is pushed.
- lcheck: a clang 19 syntax-only compile of one translation unit with the product flags (~/workspace/ai-runs/lcheck). It checks syntax and template instantiation only, not link or runtime.
- Temporary code: a line that PR-N needs only because PR-N+1 has not landed, and that PR-N+1 removes.
- TPS: decode tokens per second per user. TTFT: time to first token. "n.r." = not resolved, the paired t-test did not separate the two arms.

## 1. What PR 4424 contains

Every hunk of the 29 files was labeled by concern (8 classifier agents, counts by script over the per-file diffs, non-blank lines). The totals at the head 0a5334ccb6 against the merge base:

| Concern | What it is | Added | Removed |
|---|---|---|---|
| L | K VNNI layout, storage, views, the minimal per-row store (h/tron/tensor/k_vnni.hpp, kv_cache.hpp integration, kv_cache_fwd.hpp, CMake option) | 1026 | 116 |
| R | AVX-512 reader of the layout (h/tron/kernels/k_vnni.hpp qk_group, the software loop in self_attention.hpp) | 427 | 13 |
| G | FPGA staging (gof.hpp, gof.cpp, full.hpp k_head_fn scratch, three test lambdas) | 37 | 17 |
| A | AMX dense kernel on the VNNI plane (amx_attn.cpp qk_vnni_128x4 + pack_q_rows_128x4, amx_attn_iface.hpp, two if-constexpr dispatch sites, t_amx_numerics, t_amx_dispatch_dtype fakes) | 247 | 18 |
| S | Shared block save (store_block + transpose, page::set_k_block, save_k work units / window / worker_ix, common.hpp window, TronCpp.hs, LoopyTronSpec.hs, tests) | 813 | 17 |
| T | Row-major tail block + hardware-attention policy (the PR 4737 content: saved-row bits, pending conversion, row_major_row, dense gate, dotter for tail rows, tests) | 1338 | 10 |
| B | Build, CI flag, deb preset, README, cost rows, test registration | 30 | 5 |

The dependency graph (an arrow means "needs"):

```
main ──> L ──> R ──> G            (PR-1: L+R+G+B)
          │
          ├──> A                  (PR-2, needs L only)
          │
          ├──> S                  (PR-3, needs L only)
          │
          └──> T  needs A, S, R, G (PR-4, last)
```

Facts behind the graph (verified by 5 seam agents and 10 refuters, and by the probe):

- A uses 15 L symbols and 107 main symbols and nothing from S, T, R or G. Its only mentions of the others are comment lines.
- S uses L only (save_k signature, page::set_k_block, batch::k_store_window). No L, R, G or A code line references an S symbol.
- T needs A (the dense gate k_layout_dense sits in the AMX dense branch), S (block_to_vnni calls store_block; the row-bit loop sits inside S's save_k), R (the dotter scoring of tail rows is in R's software loop) and G (k_row_if_row_major in full.hpp). S and T are coupled in both directions at the head, so T must come after S.
- L without R does not compile with the option on: the software loop calls page::k(), which L constrains to row-major slots. So R stays with L in PR-1.
- The history already holds three of the stack's trees, all built and tested on delphi-3bda: 6b939d25d2 (L+R+G+A+S with the save_k_helper form), ba69cb513e (same with the worker fold, differs from the tested 45e6bb266d by one comment), 9d5c7a389b (+T).

## 2. Is the split technically sound

Yes, with the evidence below. The two cuts that history does not already prove (A out, S out) were built and checked tonight.

### 2.1 The probe

Starting tree: ba69cb513e (the head minus the 4737 merge minus the preset commit). Two commits on the scratch branch jhan-split-probe:

| Stage | Commit | What was removed | Files | Lines vs the stage before |
|---|---|---|---|---|
| A-off | 3c56db9a95 | the AMX kernel on the plane (concern A) | 9 | +61/-279 |
| S-off | 76a0160b72 | the shared block save (concern S) | 8 | +72/-673 |

Result sizes (git diff --shortstat, actual trees):

| Candidate PR | Tree | Files | Lines |
|---|---|---|---|
| PR-1 = L+R+G+B | 76a0160b72 vs be0d5565b3 | 23 | +1846/-160 |
| PR-2 = A | ba69cb513e vs 3c56db9a95 | 9 | +279/-61 |
| PR-3 = S | 3c56db9a95 vs 76a0160b72 | 8 | +673/-72 |
| PR-4 = T | 9d5c7a389b vs ba69cb513e | 10 | +1459/-113 |
| deb preset | 0a5334ccb6 vs 9d5c7a389b | 2 | +7/-2 |

The sum (4,264 added) is 210 lines above the PR's 4,054 added lines. The difference is the temporary gate, the comment rewrites, and the per-row save_k that PR-3 replaces again.

Syntax check: 22 cells = trees gen (AMX dispatch on) and gen-amxoff, each with TRON_K_VNNI off and on, over t_llama_unit, t_k_vnni_layout, t_amx_dispatch_dtype, t_amx_numerics, heterogeneous_scheduler_compile, plus amx_attn.cpp in gen. The untouched ba69cb513e tree gives 0 errors in all 22 cells. Both probe stages give 0 errors in all 22 cells on the first try, with no fix-up round. An independent verifier re-ran the matrix (0 errors), ran two negative controls (a wrong static_assert gives 1 error; naming the removed store_block gives 2 errors, so the checker sees the real headers), and found 0 leftover symbols of the removed concerns and nothing wrongly removed.

What the probe does not cover: link, code generation, the generated model translation units, runtime, GCC, and the two Haskell files (which are at main's content in PR-1). The full build and the unit tests on delphi-3bda remain to be done per PR (section 5).

### 2.2 What PR-1 carries as temporary code

Three places, all removed by PR-2:

- self_attention.hpp apply_page_tok: the dense AMX gate becomes `eligible<...>(...) && !k_vnni::layout_on<operation_head_size>`, with a comment "Temporary until the VNNI AMX kernel lands". A VNNI slot then always takes the software loop (the AVX-512 reader). Row-major geometries and the option-off build are unchanged.
- t_amx_dispatch_dtype: the "dense" expectation carries `&& !k_vnni::layout_on<head_size>`; under the option the 128/4 geometry expects no kernel call.
- One diagram line in amx_attn_iface.hpp and one item of Note [K VNNI storage] say the same in prose.

Comment residue: five sentences still describe the AMX kernel reading the plane (h/tron/kernels/k_vnni.hpp:3-5 and 44-45, h/tron/tensor/k_vnni.hpp:178-179, src/tron/CMakeLists.txt:232-234, t/t_llama_unit.cpp:429). PR-1 must reword them. The CMake one is the stated reason for `FATAL_ERROR "TRON_K_VNNI requires TRON_AMX_DISPATCH=ON"`; that reason is gone in PR-1, and the AMX-off + VNNI-on cells compile clean, so PR-1 should drop the requirement (decision D2).

### 2.3 The premise "VNNI-K is independent of AMX"

At the code level the premise holds. The layout header, the reader header and model.hpp have zero TRON_AMX_DISPATCH guards. The reader call in self_attention.hpp (line 2046 at the head) is outside the `#ifdef TRON_AMX_DISPATCH` region (lines 1895-1945). The tron target has `-mavx512bf16` as a PUBLIC compile option (src/tron/CMakeLists.txt:285), so the reader's VDPBF16PS needs no AMX flag. The probe's AMX-off + VNNI-on cells compile with 0 errors. The README of the head says the same: "the layout does not depend on AMX, only the reader does".

At the benefit level the premise does not hold on an AMX host. Without PR-2, a build with the option on takes the software reader for every page of a 128-dimension head, and the AMX dense kernel never runs for that shape. The only measurement of that state is the 2026-09-14 kill-switch arm (qwen3-4b, tp2, 8 users, runtron, base 544ca05c7a, arms "vnnioff" vs "off" and vs "base"):

| Prompt | VNNI reader without AMX vs row-major dotter without AMX (decode TPS, kill-switch arms) | VNNI reader without AMX vs main's AMX kernel (decode TPS, kill-switch arm as a proxy for PR-1) |
|---|---|---|
| 1024 | +5.2 % | -7.1 % (73.93 vs 79.59 TPS) |
| 2048 | +3.7 % | -10.3 % (47.31 vs 52.76 TPS) |
| 8192 | +4.2 % | -11.1 % (15.37 vs 17.29 TPS) |

So PR-1 alone is a gain on hosts without AMX and a loss on AMX hosts if the option is on. PR-1 ships with the option OFF in every preset (the deb preset line moves to PR-4), so main's default build does not change. PR-1's value is as the base of the stack. The reviewers should see PR-2 open as a draft next to it.

## 3. Recommended stack and merge order

```
PR-1 layout + readers ──> PR-2 AMX kernel ──> PR-3 shared save ──> PR-4 tail block + policy + deb preset
   ready for review          draft                draft                 draft
```

Merge order and the reason for each edge:

1. PR-1 first. Everything else needs the layout, the typed views and the reader.
2. PR-2 (A) second. It needs L only. It is the smallest PR and it restores the AMX path for 128-dimension heads, which PR-1 gates off. After PR-2 the stack beats main's AMX kernel on decode TPS (section 3.2).
3. PR-3 (S) third. It needs L only. It removes the prefill store cost of the per-row scatter. PR-2 and PR-3 could land in either order; A first is recommended because A is small and because the decode loss of PR-1 on AMX hosts is the larger number.
4. PR-4 (T) last. It needs A (the dense gate), S (block_to_vnni uses store_block), R and G. It also carries the deb preset line, because the preset turns the layout on in production, and production runs qwen3-4b under FPGA attention, where issue #4500 is open until T lands.

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

### 3.2 What the stack delivers at each step (CPU-attention qwen3-4b tp2 8 users, old-base data, signs only)

| After | Decode TPS vs main's AMX | TTFT prompt 1024 | FPGA-attention decode (qwen) | Tokens vs main (CPU attention) |
|---|---|---|---|---|
| PR-1 (option on) | -7 to -11 % (kill-switch arm as proxy) | about equal | -4 / -12 % (#4500) | diverge at a near tie (#4444) |
| PR-2 | +6 to +10 % | +2 % tp2, +8 % tp4 | -4 / -12 % | diverge |
| PR-3 | +6 to +10 % | -1 to -4 % | -4 / -12 % | diverge |
| PR-4 | +5 to +10 % | -1 to -4 % | within noise | identical |

Until PR-4 the option stays off in every preset, so none of the intermediate rows reaches production.

## 4. Construction method

All four trees exist or are one patch away. No hunk-level reconstruction by hand is needed.

1. PR-1 branch (new, from the merge base, then merge origin/main): the tree of probe commit 76a0160b72, rewritten as 4 to 6 topical commits (tensor type + forward declarations; kv_cache integration + per-row save_k; AVX-512 reader + software loop; FPGA staging; tests; CMake option + CI flag + README + cost rows). Then: the five comment rewrites of section 2.2, drop the CMake FATAL_ERROR (D2), remove the README deb paragraph, merge origin/main (165 commits since the merge base; 1 file of the stack, t_llama_unit, changed by +122 there).
2. PR-2 branch (from PR-1): apply `git diff 3c56db9a95 ba69cb513e` (the A diff) minus the S/T comment sentences in amx_attn_iface.hpp, remove the temporary gate and the t_amx_dispatch_dtype clause. One or two commits.
3. PR-3 branch (from PR-2): apply `git diff 76a0160b72 3c56db9a95` (the S diff). The result equals ba69cb513e's tree modulo comment wording; check with `git diff ba69cb513e`. Take the save_k test from blob 522acb4792. Two or three commits (store + window; code generator; tests).
4. PR-4 branch (from PR-3): apply `git diff ba69cb513e 9d5c7a389b` (the T diff, which is byte-identical to the 4737 merge diff) plus the preset commit's diff, plus the README deb paragraph. The result must equal today's head 0a5334ccb6 modulo the comment rewrites of PR-1; check with `git diff 0a5334ccb6`.
5. Keep jhan-amx-vnniK untouched until PR-4 is open. Tag today's head (for example pr4424-pre-split-0a5334ccb6) before anything is force-pushed.

Review history: PR 4424 has two COMMENTED reviews by Ben and no inline thread other than the answered r4065141577, so rewriting the commit history costs no review state. The 4424 description's four protected sections are jhan's text; each new PR needs its own Short version and Background.

## 5. Verification before opening each PR

Each PR, on delphi-3bda (our half, next to serving; whole machine only for the cells), in this order:

| Step | PR-1 | PR-2 | PR-3 | PR-4 |
|---|---|---|---|---|
| Build, option on and off | yes, plus AMX dispatch off with the option on | yes | yes | yes |
| Unit tests: t_k_vnni_layout, t_llama_unit, t_amx_numerics, t_amx_dispatch_dtype, t_heterogeneous_scheduler, t_phase1_integration | yes | yes (real AMX for t_amx_numerics) | yes | yes |
| Ingest cabal test (code generator) | no change | no change | yes | no change |
| Host test suite, serving down | yes | yes | yes | yes |
| Token identity (runtron, 1 user, greedy): A/A, kill switch, vs main | yes (CPU and FPGA attention) | yes | yes | yes |
| Cells vs the latest main (final head of the PR) | qwen3-4b tp2 8u prompt 1024 / 8192 CPU attention, AMX on and kill switch | same | same, plus tp4 prompt 1024 (the TTFT claim) | the 14 nightly configs + qwen 8k software attention, whole machine |
| clang-format 19, diff --check, fourmolu (PR-3) | yes | yes | yes | yes |

The author rule for PR bodies applies per PR: present tense, measurements of the final head against the latest main only. The cell sets above are the minimum that backs each PR's claim. Estimated machine time: PR-1 to PR-3 about 2 h each (build 10 min, tests 15 min, host suite 2 min, smokes 20 min, cells 1 h); PR-4 about 10 h (the whole-machine campaign, after a nightly).

## 6. PR bodies and open items

The current body's "The changes" bullets map to the PRs as follows:

- PR-1: the h/tron/tensor/k_vnni.hpp bullet minus the row-major tail block operations and store_block; the h/tron/kernels/k_vnni.hpp bullet; kv_cache_fwd.hpp; the kv_cache.hpp bullets on Note [K VNNI storage], kv_block::k, page::k(), page::k_packed, set_k_row / get_k_row (without "follow the block's recorded layout"), the whole-page copy, fill_random; model.hpp: the per-row store only; self_attention.hpp: the software loop with qk_group; the FPGA staging bullet; CMake option, CI flag, README; tests: t_k_vnni_layout layout / reader / copy cases, t_llama_unit accessors and typed-boundary contracts, the gof test lambdas.
- PR-2: the self_attention.hpp / amx_attn.cpp / amx_attn_iface.hpp bullets on qk_vnni_128x4 and the bit-identity test; the t_amx_dispatch_dtype fakes.
- PR-3: Note [Shared block save], the save_k bullets on work units, sharing, the join, the window state in common.hpp, the code generator bullet, LoopyTronSpec.hs, the shared-save case of t_llama_unit, the block-save test.
- PR-4: the row-major tail block operations, the K layout state bullets, pending_k_blocks / convert_pending_k_blocks, the dense gate, the dotter for tail rows, Note [Row-major blocks under hardware attention], the deb preset sentence, the tail-block tests.

Open items of the current body, by PR: genoa96 cost row (PR-1); kv_mul 3/8 reader slowdown (PR-1); benchmark binary mismatch (PR-1, the CI flag); kill switch and token divergence #4444 (PR-1 introduces the divergence, PR-4 removes it under CPU attention); widened test tolerance (PR-1); cost rows refresh (PR-4).

The protected sections of the 4424 body (Short version, Background, "Remove the Score transpose", "Use shared block in saving K") split naturally: the first two and the third go to PR-1 and PR-2, the fourth to PR-3. The standing wording proposal for those sections (masked partial-block stores and the 64-line decode scatter are gone since 4737) applies to PR-4's text, where the tail block lives.

## 7. Costs and risks

- Four reviews instead of one. Each is smaller, but PR-1 (about 1,850 added lines, 965 of them tests) is still at the repo's p95 of merged PR size (1,798 lines, September count). It cannot be cut further without adding code with no consumer (a tensor type without its store and reader), which Ben declined on PR 4557.
- PR-1 alone is a loss on AMX hosts if the option is on (section 2.3). The option stays off; the PR body must say so plainly, and PR-2 must be open as a draft at the same time.
- Temporary code in PR-1 (three places) and five comment rewrites that PR-2 reverts.
- Re-measurement: each PR's claim needs cells against the latest main at its final head (about 2 h of 3bda per PR, 10 h for PR-4). The 2026-10-09 whole-machine data stays valid only for PR-4.
- Main drift: 165 commits since the merge base, 442 lines in TronCpp.hs. Each child PR must take main after its parent merges (the repo convention is a merge of main, not a rebase, for reviewed branches).
- Stack discipline: descendants stay draft; a reviewer who reads PR-1 without PR-2 sees a layout with no AMX consumer. Mitigation: PR-1's body links PR-2 to PR-4 and states the stack order.
- The probe is syntax-only. The real build and the unit tests of PR-1 and PR-3 in their reduced form have not run yet. Expected risk is low (0 syntax errors in 22 cells, and the pre-S / pre-A states existed in history), but it is a step of section 5, not a given.
- T before S is not possible without a full-block store in T (block_to_vnni calls store_block). The order of section 3 avoids that.

## 8. Alternatives considered

- Keep one PR. Rejected: the dependency graph is one-directional, two cuts existed as separate tested PRs, the probe shows the third cut is clean, and the author judges the PR unreviewable by hand at 4,054 lines.
- Three PRs (A folded into PR-1, then S, then T). Technically equal; PR-1 grows by 280 lines and gains its AMX consumer and a positive standalone decode claim, but every reviewer of the layout must then read AMX intrinsics. The 4-PR stack follows the author's premise and keeps PR-1 free of AMX instructions. If the AMX reviewers prefer to see the consumer next to the layout, fold A into PR-1 (the probe's A-off commit is the one to skip).
- Five PRs (R out of PR-1 behind a gather-and-dotter stand-in). Rejected: the stand-in is throwaway code, and R is the software consumer of the layout.
- S before A. Possible (the probe's A-off tree is PR-1 + S), but A is smaller and removes the AMX-host decode loss of PR-1 first.
- Cut T into tail-block mechanics and hardware-attention policy. Not recommended unless asked (section 3.1).

## 9. Decisions for jhan

- D1: 4-PR stack as in section 3, or the 3-PR variant (A folded into PR-1). Recommended: 4.
- D2: drop the CMake requirement "TRON_K_VNNI requires TRON_AMX_DISPATCH" in PR-1. Its stated reason (the AMX kernel in the dispatch translation unit) leaves with A; the AMX-off + VNNI-on configuration compiles. Recommended: drop; PR-2 does not need it back (the dense path is inside `#ifdef TRON_AMX_DISPATCH`).
- D3: in PR-1, gate amx_eligible for VNNI slots too (so a VNNI build does not pack Q and open the tile region for nothing), or keep the minimal one-clause gate. Recommended: minimal; PR-2 removes it.
- D4: order PR-2 (A) before PR-3 (S). Recommended as in section 3.
- D5: the cell sets of section 5 per PR, or fewer. Recommended as listed.
- D6: who writes the four Short versions and Backgrounds (the protected sections are jhan's).
- D7: tag the current head and keep PR 4424 open as the reference until PR-4 is open, or close 4424 when PR-1 opens.

## Appendix: data provenance

- Hunk classification: workflow wf_b3743267-d3e (8 classifiers, 5 seam agents, 10 refuters; per-agent results in the session's subagents/workflows directory).
- Probe: workflow wf_71e43fda-5f0; branch jhan-split-probe at 76a0160b72 (parent 3c56db9a95, parent ba69cb513e) in ~/workspace/ai-runs/tron-split-probe; matrix logs and edit scripts in the session scratchpad under probe/ and probe-verify/.
- 2026-09-14 arms (off / base / vnni / vnnioff): exec/results/vnnik-20260914 (VNNIed-K-in-place). 2026-09-15 shared-save arms: exec/results/vnnik2-20260915. 2026-10-09 whole machine: exec/results/pr4424ci-20261009/summary.md; precheck token identity: exec/results/merge4737-precheck.
- GitHub: PR 4424 reviews 5270304492 and 5270587330 (Ben, 2026-09-21), issue comment 5765866077 (the typed-tensor sketch), thread r4065141577; PR 4774 merged 2026-10-08T21:33Z, PR 4737 merged 2026-10-08T23:57Z.

---

## Update 1 (2026-10-10, after the codex review in split-plan-codex.md)

Short version: codex supports the four-PR stack and the merge order, and raises five corrections and three smaller ones. Four of the five are accepted after verification against the source and change the text of sections 2, 3, 4 and 5. The fifth (the dependency wording) is accepted as a rewording. Of the smaller ones, the size and CMake-option points are accepted and the build-location point is refused with a reason. The recommendation (section 3) stands.

### U1.1 Point 1, the PR-4 invariant: accepted, text corrected

Codex: "block VNNI iff its 16 bits are set" is false. Verified at the head: a page keeps two bit sets per storage slot, the saved-row bits (k_rows_saved_, one per page offset) and the converted-block bits (k_vnni_blocks_, one per 16-token block) [h/tron/models/kv_cache.hpp:683-686, 2484-2485]. note_k_row_saved returns true when the block's 16 rows are saved and the block is not converted yet; the main thread then queues the block, and the conversion runs at the forward end after the cooperative staging drained [kv_cache.hpp:2157-2183, model.hpp:1847]. So a complete block may stay row-major until the forward end.

Replacement for the "what a reviewer checks" line of PR-4 in section 3.1: the converted-block bit selects the layout; a converted block has all 16 rows saved; a complete block may remain row-major while its conversion is pending; the three writers of the bits (save_k, clear, copy) and the readers (dense gate, software loop, staging) all read the converted-block bit. The existing t_llama_unit case that checks the state before and after the conversion stays with PR-4.

### U1.2 Point 2, required CI coverage: accepted, new section 5.1

Codex: the cited workflow does not run on pull requests, so the enabled paths have no required CI coverage. Verified:

- The PR CI is gcp-nix.yml (triggers: push to main, pull_request). Its test build (nix/cmake-tron-test-build.nix:80-93) passes neither TRON_K_VNNI nor TRON_AMX_DISPATCH.
- cmake-single-platform.yml, the workflow that carries `-DTRON_K_VNNI=ON`, runs on workflow_dispatch only, and as the test gate of publish-deb.yml (workflow_call).
- AGENTS.md "Test policy": every committed test must run in a required CI suite; local execution is not sufficient.
- With the option off, t_k_vnni_layout's owner-level cases (index map, store_row / load_row, the reader on an owner) run, and its book-level cases are compiled out (#ifdef TRON_K_VNNI); t_llama_unit's VNNI branches take the row-major path; the VNNI case of t_amx_numerics returns early without AMX hardware [t/t_amx_numerics.cpp:208-211].

This gap is inherited: PR 4424 has it today, and PR 3879 had it for TRON_AMX_DISPATCH (memory: the legacy lane is the only one that compiles the option). The split does not create it, but each PR of the stack commits tests that the required CI does not execute with the option on. Section 5 gains the following subsection.

5.1 CI coverage of the enabled paths (new). Before PR-1 opens, one of these must be chosen (decision D8):

- (a) Add `-DTRON_K_VNNI=ON` to the Nix test build (nix/cmake-tron-test-build.nix). The whole PR suite then runs on the VNNI layout; the row-major layout keeps the coverage preset and the deb-smoke lane. The AMX kernel case of t_amx_numerics still runs only on an AMX runner (it returns early elsewhere).
- (b) Add a second Nix test configuration with the option on, next to the default one. Doubles the PR build time of the C++ suite.
- (c) Accept the gap as PR 3879 did, and state it in each PR body under Verification, with the manual-dispatch lane as the way to run the enabled suite. This needs the explicit approval the test policy requires.

Recommended: (a), asked of the CI owner before PR-1 opens, because the deb preset of PR-4 ships the layout on every host and the released configuration should be the tested one. For PR-2 the body must separate the fake-dispatch tests (run everywhere) from the numerical identity case (runs only on an AMX runner, t_amx_numerics returns early otherwise).

### U1.3 Point 3, the PR-2 tree: accepted, probe extended

Codex: the recommended order needs "PR-1 + A without S", which the probe did not build; `git apply --check` of the A diff on the PR-1 tree fails at h/tron/models/kv_cache.hpp:666 and h/tron/tensor/k_vnni.hpp:29. Verified: the same two failures reproduce here (comment context that S changed). The sentence "No hunk-level reconstruction by hand is needed" in section 4 was too strong; the repair is small but it is a hand edit.

The PR-2 tree now exists: commit 4d3a042225 on the scratch branch jhan-split-probe-pr2 (parent 76a0160b72, the PR-1 tree). Facts:

- Construction: `git apply --3way` of the A diff applied 8 of 9 files cleanly. One real conflict remained, the "Consumers of a VNNI slot" list of Note [K VNNI storage] in kv_cache.hpp. The second file of the plain `--check` failure, h/tron/tensor/k_vnni.hpp, merged by itself without S words.
- Hand repairs, both comment-only: (1) that consumers list (PR-1's item 1 on the per-row store kept, A's items 2 and 3 on qk_vnni_128x4 and qk_group taken); (2) the three S sentences of Note [QK orientation] in amx_attn_iface.hpp replaced by one sentence: "The price moves to the K store (a scatter of 64 dimension pairs per token, in save_k) and to the software reader k_vnni::qk_group for partial pages."
- The A diff's clean hunks already remove PR-1's temporary gate, the dispatch-test clause, the diagram line and the README sentence. Grep: 0 hits for "temporary until", store_block, set_k_block, Shared block save, work unit, Row-major tail block, k_vnni_blocks, note_k_row_saved; qk_vnni_128x4 present in 8 files, pack_q_rows_128x4 in 5.
- Size: PR-2 = 9 files, +277/-61 (added/removed lines by git numstat) against the PR-1 tree. What still separates PR-2 from the tested tree ba69cb513e is S plus the two comment wordings: 9 files, +678/-75.
- Syntax matrix on 4d3a042225: 22 of 22 cells at 0 errors (46 s wall). A deliberate syntax error in an untracked file gave 1 error through both checker variants, so the counter is live.
- Side effect to know: git rerere is active in the shared repo ~/workspace/tron and recorded the kv_cache.hpp resolution. An identical conflict in any worktree of that repo would auto-resolve to this text. Harmless for the probe.

The four candidate trees of the stack are therefore all real commits: PR-1 = 76a0160b72, PR-2 = 4d3a042225, PR-1 + S = 3c56db9a95 (the PR-3 content on PR-1, to be re-based on PR-2), PR-4 = the 4737 merge diff on top. Three of them (PR-1, PR-2, PR-1 + S) pass the syntax matrix; ba69cb513e and 9d5c7a389b were built and tested on delphi-3bda.

Section 4, step 2, becomes: apply the A diff with `git apply --3way`, repair the two comment hunks (Note [K VNNI storage] consumer list in kv_cache.hpp, the header comment of tensor/k_vnni.hpp) and the Note [QK orientation] paragraph of amx_attn_iface.hpp so they name only L, R, G and A, remove PR-1's temporary gate, run the syntax matrix, commit.

Section 4, step 4, the final comparison: compare the PR-4 tree against the original head 0a5334ccb6 merged with the same main, and list the allowed differences explicitly: (1) the CMake decoupling of D2 (src/tron/CMakeLists.txt FATAL_ERROR block and the option text in CMakeLists.txt:47), (2) the comment rewrites that PR-1 and PR-2 carry and PR-3 / PR-4 restore in their own wording, (3) nothing else. Every other difference must be explained or removed.

Codex also notes that the syntax-only probe does not validate the CMake configuration after the FATAL_ERROR is dropped. Correct; that is the configure step of section 5 (build with the option on and AMX dispatch off, PR-1 column).

### U1.4 Point 4, dependencies versus extraction order: accepted as a rewording

Codex: T needs the block-store primitive (store_block), consistent readers and writers, and the conversion timing, not helper-thread sharing; and the dense gate adapts the AMX path rather than being a prerequisite. Verified: block_to_vnni calls store_block [h/tron/tensor/k_vnni.hpp:508]; the unshared save branch stores through the same store_k_block and the row-bit loop follows it [h/tron/models/model.hpp:3418-3439]; without A, PR-1 already keeps VNNI pages out of the AMX dispatch (the temporary gate).

Section 1's graph keeps "T after A and S" as the order of this extraction (the T diff is the 4737 merge diff, and it lands on the tree that has S and A). The intrinsic dependency of T is on store_block (76 lines of S) and on R and G. A T-before-S order would need those 76 lines moved into T and the row-bit hook relocated into the per-row save_k (about 34 lines, per the seam check). No extra PR is proposed for this.

### U1.5 Point 5, token identity and performance claims: accepted, text limited to the measured cells

Codex: PR-4 does not establish general token identity with main under CPU attention, because converted blocks of a partial page are still scored by the packed reader (k_vnni::qk_group), whose fp32 add order differs from the row-major dotter. Verified at the head: in the software loop, a token of a converted block sets its bit in `live` and is scored by qk_group after the loop; only the rows of a row-major tail block go through the dotter [h/tron/models/self_attention.hpp:2025-2047]; the reader documents the different add order [h/tron/kernels/k_vnni.hpp:51-54].

The measured identity (exec/results/merge4737-precheck/smoke, 2026-10-09): ingested-qwen-3-4b-instruct-2507-tp2, 1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens; CPU attention at prompt 1024 and prompt 8192: identical to main for 256 of 256 tokens; FPGA attention at prompt 1024: first difference at generated token 52 (as before PR 4737). Sections 3.1 and 3.2 now say "identical to main in those two cells", not "identical under CPU attention".

Codex also notes that the kill-switch arm on an AMX host does not establish a gain on hosts without AMX. Accepted: the table in section 2.3 is kill-switch data on delphi-3bda (Granite Rapids); the numbers for an AMD host are Insufficient data (a run of the PR-1 head against main on andoria or genoa96 would resolve it).

### U1.6 Smaller points

- Sizes: accepted. By `git diff --numstat be0d5565b3 76a0160b72`, the test sources of PR-1 are +965/-90, which is 52 % of the 1,846 added lines (section 3.1 said 57 % and mixed added with changed lines). t_llama_unit.cpp is +469/-78 (not "+547"), t_k_vnni_layout.cpp +474/-0. The code share of PR-1 is therefore about 880 added lines, not 790. The stack sum of 4,264 added lines stands.
- CMake option text: accepted. D2 also covers CMakeLists.txt:47, whose help text says "requires TRON_AMX_DISPATCH", and keeps both compile definitions (the tron target and tron_model_compile_config, src/tron/CMakeLists.txt:235-240 and 342-348).
- Build location: refused in part. Builds cannot run on claude-box (sw-dev-01) today: /nix is an empty directory and ~/.nix-profile/bin/nix does not exist (checked 2026-10-10 00:5x UTC), so no tron build is possible there, and the syntax matrix is the most claude-box can do. Builds therefore stay on delphi-3bda, on our half next to serving, under the CI lease and the campaign guard, as every chain of this project has done. The scheduling wording is accepted: section 5 now says "under the live CI lease, the campaign guard (campaign_guard_acquire) and the between-run checks (ci_took_dut)", not "after a nightly".

### U1.7 Changes to the decisions list

- D2 is extended to the option help text.
- New D8: the CI coverage choice of U1.2 (a / b / c). Recommended (a).

### U1.8 Corrections to the original text (from the plain-English and number check)

A check of the original text found 5 number errors and 78 style violations (41 undefined terms, 26 sentences with two claims or a semicolon, 4 numbers without a unit or meaning, 6 idioms, 1 Short version sentence with five claims). The number errors are corrected in place, on the same lines, so codex's line references still hold. The in-place edits:

- Short version: "57 % tests" is now "52 % tests".
- Section 3.1, PR-1: the per-file numbers were changed-line counts (added plus removed) labeled as added lines. They are now added/removed pairs by git numstat: tests +965/-90 (t_k_vnni_layout +474, t_llama_unit +469/-78, t_amx_dispatch_dtype +16/-7, three gof test lambdas +5/-5, t/CMakeLists.txt +1); code +881/-70 (tensor/k_vnni.hpp +335, kv_cache.hpp +235/-38, kernels/k_vnni.hpp +128, self_attention.hpp +53/-9, gof.hpp + gof.cpp + full.hpp +39/-12, model.hpp +23/-1, kv_cache_fwd.hpp +16/-3, attn_stats.hpp +4/-3, amx_attn_iface.hpp +1, CMake option + CI flag + README + cost rows +47/-5).
- Section 3.1, PR-3 and PR-4: the per-file numbers are now numstat pairs (PR-3: tensor +85/-6, kv_cache +35/-7, model +298/-36, common +29, TronCpp.hs +24/-3, LoopyTronSpec.hs +24/-2, t_k_vnni_layout +90, t_llama_unit +88/-18; PR-4 tests: t_k_vnni_layout +500/-2, t_llama_unit +140/-4, t_amx_dispatch_dtype +35/-5).
- Section 2.3 and table 3.2: the "est." labels are gone. Both columns are measured ratios of two kill-switch arms on delphi-3bda; the second column is a proxy for PR-1, and the table now says so. The PR-1 row of table 3.2 reads "-7 to -11 %", as section 3.1 does.
- Section 7: "1,050 of them tests" is now "965 of them tests".

Corrected stack sizes (added/removed lines by git numstat, actual trees):

| PR | Tree | Files | Added | Removed | Of which tests (added) |
|---|---|---|---|---|---|
| PR-1 L+R+G+B | 76a0160b72 vs be0d5565b3 | 23 | 1846 | 160 | 965 (52 %) |
| PR-2 A | 4d3a042225 vs 76a0160b72 | 9 | 277 | 61 | 98 (35 %) |
| PR-3 S | 3c56db9a95 vs 76a0160b72 | 8 | 673 | 72 | 178 (26 %) |
| PR-4 T | 9d5c7a389b vs ba69cb513e | 10 | 1459 | 113 | 675 (46 %) |
| deb preset | 0a5334ccb6 vs 9d5c7a389b | 2 | 7 | 2 | 0 |

The style violations of the original text are not edited in place (that would move codex's line references). The terms the check found undefined are defined here, so the document as a whole meets the first-use rule:

Words used here (supplement to the original list):

- Codex: the second, automated reviewer of this plan. tron: the inference program under test. runtron: its command-line tool. delphi-3bda: the Intel Granite Rapids test machine; "our half" is the half of it not reserved for Bill. genoa96: the AMD benchmark runner of the CI. sw-dev-01 / claude-box: the AMD development host this session runs on.
- FPGA: the accelerator card that runs attention for the pages it processes. Hardware attention: attention computed on the FPGA. FPGA staging: the gather that copies K rows into the buffers the FPGA reads; gof is the module that does it. Software attention: attention computed on the CPU.
- Prefill: the processing of the prompt. Decode: the token-by-token generation that follows. tp2 / tp4: tensor-parallel degree 2 / 4 (the number of FPGA cards one engine spans).
- The option: the CMake switch TRON_K_VNNI. Kill switch: TRON_AMX_DISABLE=1, the runtime switch that turns AMX off. Arm: one binary under test in a measurement; "vnnioff" is the VNNI binary with the kill switch, "off" the row-major binary with the kill switch, "base" the row-major binary with AMX.
- Dense page: a full 64-token page that the AMX path scores in one kernel call. VNNI plane: the VNNI-ordered K storage of one page and one KV head (16 KiB). B operand: the right-hand matrix of the AMX tile multiply. Dotter: the row-major dot-product reader of K. Intrinsics: compiler built-in functions that emit single AVX-512 or AMX instructions. VDPBF16PS: the AVX-512 bf16 dot-product instruction.
- Per-row store: each token's K row written on its own into the VNNI layout (4 AVX-512 scatters per row); "scatter store" names the same thing. Shared block save: the K store that writes one whole 16-token block at a time (a register transpose and whole-line stores) and shares the work with the idle main helpers (the helper threads of the main loop, idle during the K store). Join watchdog: the main thread's wait for the helpers aborts with an error after 120 s. Row-major tail block: the last, partly filled 16-token block of a page, kept in plain row order until its 16th row is saved. Converted block: a block whose rows have been transposed into the VNNI layout.
- save_k_helper form: the shared save as a separate helper function (the first version). Worker fold: the same save folded into save_k with a worker index (Ben's thread r4065141577, PR 4774).
- Note [...]: a named long comment block in a header. Row-major geometry: a head-size and kv_mul pair that keeps the row layout (every head size other than 128).
- TronCpp.hs: the Haskell code generator that emits each model's plugin, including the save_k calls. LoopyTronSpec.hs: its test suite. Ingest: the code-generator package. cabal: the Haskell build tool. fourmolu: the Haskell formatter.
- Cell (measurement): one model, parallelism, user count, prompt length and attention mode. Cell (syntax matrix): one compile configuration (tree x option x file). Smoke test: a short end-to-end run of one user, greedy (temperature 0, the top token at every step), compared token by token. A/A: two runs of the same binary, to measure run-to-run noise.
- Cost rows: the per-test timing rows of config/test-benchmarks.json that the CI's bench check reads. Benchmark-binary mismatch: the legacy CMake workflow benchmarks the runtron of its build job (options on) when the hand-over works, and a locally rebuilt runtron (options off) when it does not.
- Classifier / seam / refuter agents: sub-tasks of this analysis; classifiers labeled each hunk by concern, seam agents checked each boundary between two concerns, refuters tried to disprove each seam verdict.
- Issue #4500: the FPGA-attention decode loss caused by the per-token 64-line column access of the VNNI layout. Issue #4444: the token divergence against the row-major binary and the kill-switch rollback contract. p95: the 95th percentile.
- "Built tonight" / "checked tonight" in the original text means 2026-10-09 evening PDT (2026-10-10 00:xx UTC).

A clean second version of the whole plan, with the style fixes applied in the text, is a separate step once the decisions D1 to D8 are made.

### U1.9 Planner's verification of Update 1 (2026-10-10 01:0x UTC)

Short version: the planner re-checked every accepted point of Update 1 against the source, the probe trees and the measurement records. Update 1 stands. Four facts are added or made more precise below.

- The PR-2 tree (PR-1 + A) was built three times by independent agents, and all three compile. Probe commit 4d3a042225 (branch jhan-split-probe-pr2): 22 of 22 syntax cells at 0 errors. A second build (scratchpad refute1/stacked): 14 of 14 cells at 0 errors. A third build (scratchpad refuter2/laTree): 16 of 16 cells at 0 errors. The control for keeping R in PR-1 also exists: a tree with L and A but without R fails with the option on at self_attention.hpp:1920 and :1955 (the software loop's page::k call), in 3 of 16 cells, and never at an A line (scratchpad refute1/strict and refuter2/laNoR).
- Sizes by git numstat (added/removed), with the test share: PR-1 23 files +1846/-160, tests +965/-90; PR-2 9 files +277/-61, tests +98/-15; PR-3 re-based on PR-2 (4d3a042225 to ba69cb513e) 9 files +678/-75, tests +178/-18, ingest +48/-5; PR-4 10 files +1459/-113, tests +675/-11; deb preset 2 files +7/-2. The stack sum is 4,267 added lines with that PR-3, not 4,264. The old figure used PR-2 = 279 (ba69cb513e vs 3c56db9a95). The 5 extra lines of PR-3 restore the two comment wordings that PR-2 changes (amx_attn_iface.hpp +5/-3, the store_block mentions of tensor/k_vnni.hpp).
- Token identity, from exec/results/merge4737-precheck/smoke (qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism, 256 tokens): at CPU attention and prompt 1024 the tree with T (9d5c7a389b) is identical to main for 256 of 256 tokens, and the tree without T (45e6bb266d, the state of PR-3) differs from main at generated token 52. At prompt 8192 all three are identical. At FPGA attention and prompt 1024 both trees differ from main at token 52. The kill-switch arm of the T tree is identical to its AMX-on arm at CPU prompt 1024. So "PR-4 removes the #4444 divergence" holds in exactly one measured cell, and PR-1 to PR-3 carry that divergence in that cell. Section 3.2's last column should read "differ at token 52 (cpu p1024)" for PR-1 to PR-3 and "identical (cpu p1024, cpu p8192)" for PR-4.
- Build location: the workspace instructions do not ask for builds on sw-dev-01. They name delphi-3bda for real tests. The host of this session (claude-agentsrv, the claude-box) has no nix tonight (/nix is empty, ~/.nix-profile/bin/nix is absent), as memory recorded on 2026-10-07. The refusal in U1.6 stands. The guard names of U1.6 are real: campaign_guard_acquire and ci_took_dut are functions of ~/workspace/intel-AMX/exec/lib-guard.sh, and the notebook rules require them (handoffs/check-CI.md:258-272).

## Update 1 addendum (planner round 2, 2026-10-10 00:4x UTC)

Short version: Update 1 was re-checked against the source, the probe worktree and the measurement records, and every checked fact holds. This addendum adds four facts that change section 5 and the PR bodies (the PR-2 tree residue check, the "Run CI" label for draft PRs, the precedent for the AMX-only numerics case, the token-identity cells) and corrects one host name. The recommendation and the merge order do not change.

### U1A.1 The PR-2 tree, re-checked (U1.3)

- The probe worktree is on the branch jhan-split-probe-pr2 at 4d3a042225 (parent 76a0160b72, the PR-1 tree). `git diff --numstat 76a0160b72 4d3a042225` gives 9 files, +277/-61 lines. The matrix summary lists 22 cells, each with 0 errors [scratchpad probe-pr2/out/pr2-r1/summary.txt].
- No temporary gate remains. A grep for "temporary until" and for `!k_vnni::layout_on<operation_head_size>` in self_attention.hpp, and for `layout_on<head_size>` in t_amx_dispatch_dtype.cpp, returns nothing.
- No S or T symbol remains. A grep over h/, src/, t/ and ingest/ for store_block, set_k_block, k_store_window, note_k_row_saved, note_k_block_saved, k_vnni_blocks, k_layout_dense, block_to_vnni, row_major_row, k_row_if_row_major, convert_pending_k_blocks, FULL_BLOCK_0XFFFF, LANES_16 and transpose_16x16 finds only main's own worker_ix uses in threading.hpp and plugins/llama.hpp, which are not S code.
- PR-2 against the tested tree ba69cb513e differs by 9 files, +75/-678 lines: the S code, plus the comment wordings of amx_attn_iface.hpp (8 lines), kv_cache.hpp, tensor/k_vnni.hpp and t_llama_unit.cpp.
- The comment-only differences between PR-1 and PR-2 are in four files, not two: tensor/k_vnni.hpp (two hunks, lines 29-37 and 117-121, "the two layout-specific score kernels"), kv_cache.hpp (the Why paragraph of Note [K VNNI storage], consumer items 2 and 3, the page::k_packed comment), amx_attn_iface.hpp (the Note [QK orientation] paragraph, 3 lines in the first-commit wording), and README.ci.md (the t_amx_numerics sentence restored). None of them is code.

### U1A.2 Draft PRs and the Nix suite (adds to section 5.1 and to the decisions)

- gcp-nix.yml is the pull-request workflow (triggers: pull_request opened / synchronize / reopened / ready_for_review, merge_group, push to main). Its Note [Draft PR Filtering and Label Override] says that draft PRs run lint, machinery and fresh-plan checks only, and that the label "Run CI" enables the product pipeline. The build and test jobs carry that condition [.github/workflows/gcp-nix.yml:5, 189-191, 315-317, 403-405].
- AGENTS.md keeps PR-2, PR-3 and PR-4 as drafts until their parent merges. So each descendant needs the label "Run CI", or its build and tests do not run in CI at all. PR 4424 is in that state today: its recorded check runs list Build Tron, Test host and Test as skipped (the A-off refutation, from the check-runs API).
- New decision D9: label every draft PR of the stack "Run CI" when it is opened. Recommended: yes. It costs runner time on each push to a draft; without it only PR-1 is tested by CI before its merge.
- Which checks branch protection requires today is Insufficient data. The 2026-09-11 reading (build, lint, test, test-fpga, test-host, ci-machinery-tests) predates the cutover to gcp-nix.yml. `gh api repos/positron-ai/tron/branches/main/protection` would resolve it.

### U1A.3 The AMX-only numerics case of PR-2 (codex point 2, second half)

- The new case of t_amx_numerics warns and returns when amx_attn_h128g4::available() is false [t/t_amx_numerics.cpp:208-211]. That is the pattern of the file's existing QK and PV cases. Main merged those cases with PR 3879 [memory amx-ci-coverage-facts: t_amx_numerics.cpp:145-148 and 189-192 at that time].
- The PR-2 body therefore says two things. The fake-dispatch cases (t_amx_dispatch_dtype) run on every runner. The identity case executes AMX only on an Intel runner (Granite Rapids) and on delphi-3bda, and warns elsewhere.
- Whether that is an approved exception to the test policy or a gap carried over from PR 3879 is jhan's call. It is part of D8.

### U1A.4 Token-identity records, for the PR bodies (U1.5)

The record is exec/results/merge4737-precheck/smoke (ingested-qwen-3-4b-instruct-2507-tp2, 1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens). The arms: base = main be0d5565b3; head = 45e6bb266d, the PR-3 state (it differs from ba69cb513e by comment lines only); new = 9d5c7a389b, the PR-4 state; newoff = new with TRON_AMX_DISABLE=1.

- CPU attention, prompt 1024: head vs base differ at generated token 52 of 256. new vs base: identical for 256 of 256 tokens. newoff vs new: identical for 256 of 256.
- CPU attention, prompt 8192: head, new and base are all identical, 256 of 256.
- FPGA attention, prompt 1024: head vs base differ at token 52. new vs base differ at token 52. new vs head: identical.

Meaning for the bodies: the divergence at token 52 under CPU attention at prompt 1024 (#4444) is present in the PR-1 to PR-3 state and absent in the PR-4 state, in that cell. The kill switch of the PR-4 state changed no token in that cell. T changes no FPGA-attention token (new vs head identical), so the FPGA-attention divergence against main at token 52 comes from PR-1's reader. These are the three measured cells. The bodies make no wider claim.

### U1A.5 Host-name correction (U1.6 and the supplement of U1.8)

- This session's container runs on the host claude-agentsrv, not on sw-dev-01. The notebook records the container's moves: alpha, then sw-dev-01, then agentsrv on 2026-08-27 [notebook artifacts/dev-machines/README.md:4].
- In this container /nix is an empty directory and ~/.nix-profile/bin/nix does not exist (checked 2026-10-10 00:4x UTC). So no tron build runs here. The memory note of 2026-09-30 ("nix is back on claude-box") does not hold for this container today.
- Whether sw-dev-01 itself has nix today is Insufficient data: ssh from this container to sw-dev-01 is refused (the host key changed).
- The conclusion of U1.6 stands: builds and tests stay on delphi-3bda, in an isolated worktree under /var/tmp/jhan, under the guard. The definition in U1.8 should read: "claude-box: the development container this session runs in, on the host claude-agentsrv; sw-dev-01: its previous host".

### U1A.6 What does not change

The recommendation (the four-PR stack, merged PR-1, PR-2, PR-3, PR-4), the construction method with the PR-2 hand repairs of U1.3, section 5 with the new 5.1, and decisions D1 to D8 stand as Update 1 states them. D9 is added above.

---

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

The 4737 merge diff removes `#include <cstring>` from h/tron/kernels/k_vnni.hpp. Both endpoints of PR 4737 keep the line, so the removal is an artifact of the conflict resolution in the merge [ba69cb513e has it at h/tron/kernels/k_vnni.hpp:15; the head 0a5334ccb6 has it only in h/tron/tensor/k_vnni.hpp:46]. The header still calls std::memcpy [h/tron/kernels/k_vnni.hpp:104 at the head] and reaches it through the tensor header. PR-4 keeps the line (1 line); that is one hunk of the T diff to drop.

### U2.3 PR-1 verification: two test runs that have never happened

In every t_llama_unit run with TRON_K_VNNI=ON so far, AMX was available (delphi-3bda). So a full VNNI page was scored by the AMX kernel of concern A. In PR-1 that kernel does not exist. A full VNNI page then takes the AVX-512 reader k_vnni::qk_group. No t_llama_unit run of that path exists. The kill-switch step of the earlier chains ran t_amx_numerics only [exec/sync4424b-20261007/chain.sh:78, exec/merge4737-20261008/build-test.sh:42].

Section 5, PR-1 column, gains two runs: t_llama_unit on the PR-1 tree with TRON_K_VNNI=ON, and the same binary with TRON_AMX_DISABLE=1. The widened tolerance of the "apply and join page ranges" case reached 0.022 of its 0.05 bound with the AMX kernel present [commit 37064d72b2, message]. Where the reader path lands inside that bound is Insufficient data until the run.

### U2.4 Changes to the decisions list

- New D10 (U2.1; D9 is the "Run CI" label of U1A.2): keep the masked partial-block path in PR-3 (a), or pre-simplify it (b). Recommended (a).
- Sizes: the StructuredOutput of the planner uses U1.9's figures (PR-3 re-based on PR-2 = +678/-75; stack sum 4,267 added lines).

## Update 2 (2026-10-10 01:0x UTC, the planning panel's verdict and two new decisions)

Short version: three planners (minimal-change, concern-first, skeptic) and one judge produced the same four-PR stack in the same order as section 3. The judge chose the skeptic plan (8 of 10) with grafts from the other two and added two decisions, D9 (the "Run CI" label on the draft PRs) and D10 (keep PR-3 as the tested shared-save form). The recommendation of section 3 stands.

### U2.1 Who wrote what in this file

- Sections 1 to 9, the appendix, and Update 1 (U1.1 to U1.8): Claude, the session that owns this file.
- Sections "U1.9 Planner's verification of Update 1" and "Update 1 addendum (planner round 2)": two planner agents of the analysis workflow appended them on their own, between 00:40 and 01:00 UTC. They were not asked to write to this file. Their facts were checked afterwards (U2.3) and the sections stay, because every checked fact holds and two of them correct Update 1 (the host name, the PR-3 size on PR-2).
- The judge's verdict was not written by the judge (read-only); it is summarized here.

### U2.2 The panel

| Plan | Score | Why |
|---|---|---|
| skeptic | 8 of 10 | same stack; limits every claim to a measured cell; correct handling of the `<cstring>` include and of the two build lines PR-1 must carry (test registration and cost row) |
| concern-first | 7 of 10 | most complete on the CI facts (D8, D9) and the Muse-Glimmer row; but recommends a pre-simplified PR-3 whose tree equals no tested tree (D10 option b) |
| minimal-change | 6 of 10 | same stack and correct sizes; does not say that draft PRs get no CI build without the label (D9); misplaces the `<cstring>` fix |

All three plans and the judge agree with sections 3 and 4 and with Update 1 on: the stack PR-1 (L+R+G+B) -> PR-2 (A) -> PR-3 (S) -> PR-4 (T + deb preset); A before S; the temporary gate of PR-1; D2 (drop the CMake requirement); the CI coverage gap D8.

The judge's statement of the author's premise: at the code level it holds, with one clause of temporary code, and "the VNNI-K changes" must mean L+R+G, not L alone (an L-only tree does not compile with the option on; an L+A tree without R fails at the software loop's page::k calls in 3 of 16 cells, control refuter2/laNoR). At the benefit level it does not hold on an AMX host (the -7 to -11 % decode TPS of section 2.3); an AMD-host number is Insufficient data.

### U2.3 Facts of U1.9 and the addendum, checked by the file owner (2026-10-10 01:0x UTC)

- Host: `hostname` is claude-agentsrv. The notebook (artifacts/dev-machines/README.md:3-4) records the container's moves alpha -> sw-dev-01 -> agentsrv on 2026-08-27. So U1.6 and the term list of U1.8 should say "claude-box: the development container of this session, on the host claude-agentsrv". The build-location conclusion of U1.6 is unchanged: no nix in the container, builds stay on delphi-3bda.
- Run CI: gcp-nix.yml has Note [Draft PR Filtering and Label Override] at line 3-5, and the build and test jobs run on a draft PR only with the label "Run CI" (lines 190-191, 316-317, 404-405). AGENTS.md:16-18 forbids adding that label without the user's explicit direction. So D9 is a question for jhan, not a recommendation.
- The three independent PR-2 trees: the matrix summaries exist and report 0 errors in every cell (probe-pr2/out/pr2-r1 22 cells; refute1/out/stacked 14 cells; refuter2/out/laTree 16 cells; pr1check/out 38 cells on the PR-1 tree). The two controls with errors exist too (refuter2/out/laNoR, the L+A tree without R; refute1/out/strict).
- D10 facts: at ba69cb513e (the PR-3 state) model.hpp has k_scatter_run_len = 1 (line 3141), the `present` mask (3245) and the branch `n == k_scatter_run_len` (3260), and kv_cache.hpp's set_k_block takes `__mmask16 present` (2039-2042). At the head set_k_block has no mask parameter (2277). So PR-3 in its tested form ships about 15 lines of masked partial-block logic that PR-4 replaces.
- `#include <cstring>`: in h/tron/kernels/k_vnni.hpp at ba69cb513e (and in the PR-1 and PR-2 trees), moved to h/tron/tensor/k_vnni.hpp at 9d5c7a389b. Both states compile (the tensor header is included by the kernel header). No action beyond "do not add a second include".
- PR-3 size on PR-2: `git diff --numstat 4d3a042225 ba69cb513e` = 9 files, +678/-75 (tests +178/-18). The stack sum of added lines with that PR-3 is 4,267. The table of U1.8 lists PR-3 as +673/-72 (against the PR-1 tree); the difference is the two comment wordings PR-2 changes and PR-3 restores.
- Token-identity cells: the addendum's reading of exec/results/merge4737-precheck/smoke matches the files (U1.5).
- Branch protection: `gh api repos/positron-ai/tron/branches/main/protection` returns 404 for this account. Which checks are required today is Insufficient data; the repository may use rulesets, which that endpoint does not show.

### U2.4 Decisions added

- D9: do you direct adding the label "Run CI" to the draft PRs PR-2, PR-3 and PR-4 when they open? Without it, the drafts get no CI build or test run before each is promoted (PR 4424's own check runs show Build Tron, Test host and Test as skipped today), and the only test evidence is the delphi-3bda runs of section 5. AGENTS.md leaves this to the user.
- D10: keep PR-3 as the tested shared-save form (option a, recommended: its tree equals ba69cb513e, built and tested on delphi-3bda on 2026-10-08, and the T diff applies on it unchanged; it ships about 15 lines of masked partial-block logic that PR-4 replaces), or pre-simplify PR-3 to full blocks only (option b: 10 to 15 lines less, a tree that equals no tested tree, and the T diff needs a hand repair).

Open questions the judge adds for jhan, beyond D1 to D10: whether to measure PR-1 (option on, no AMX) on an AMD host (genoa96 or andoria) before PR-1 opens, or to state it as Insufficient data in the body; whether to ask Ben whether a four-PR stack or the three-PR variant suits him before PR-1 opens (no reviewer has asked for a split); and that "Skip benchmarks" goes on every new PR by default (AGENTS.md:14-15).

### U2.5 Facts still to verify before acting (the judge's list, condensed)

- A CMake configure of the PR-1 tree with TRON_K_VNNI=ON and TRON_AMX_DISPATCH=OFF after D2. The syntax matrix injected -D flags and never ran CMake.
- Full build, link and the generated model translation units of the reduced trees (PR-1, PR-2, PR-3 on PR-2) on delphi-3bda. The probe evidence is syntax-only with product flags for 4 of 9 translation units.
- t_llama_unit on the PR-1 tree with the option on, and the same binary with TRON_AMX_DISABLE=1. The dense-page path through k_vnni::qk_group has never run in that test on any host; where it lands inside the 0.05 tolerance is Insufficient data.
- That `git apply --3way` of the S diff on 4d3a042225 reproduces ba69cb513e modulo the comment wordings and the D2 lines (the size is computed, the apply has not been done).
- That the PR-4 tree built from PR-3 plus the 4737 merge diff plus the preset diff differs from 0a5334ccb6 merged with the same main only in the allowed ways of U1.3.
- Cells against the latest main at each PR's final head (section 5). Every performance number in this file is old-base (2026-09-14/15) or whole-head (2026-10-09) data.
- The CI owner's answer on D8 (a), and whether an Intel runner exists in the required suite for the t_amx_numerics identity case of PR-2.
- Re-measured cost rows for the four tests at each PR's final content (the head rows were refreshed at 6b939d25d2, before T's 675 test lines).

### U2.6 State of the scratch material

- Branch jhan-split-probe (worktree ~/workspace/ai-runs/tron-split-probe): 3c56db9a95 (A-off) and 76a0160b72 (S-off = PR-1 tree). Branch jhan-split-probe-pr2: 4d3a042225 (PR-2 tree), checked out, clean. Nothing is pushed. The worktree stays until the split is decided or dropped; removal is `git worktree remove`, never a prune of the shared repository.
- git rerere in ~/workspace/tron holds the PR-2 kv_cache.hpp resolution (rr-cache, 54 entries). An identical conflict in any worktree of that repository resolves to that text automatically.
- Workflow records: wf_b3743267-d3e (classification, seams, panel, 27 agents) and wf_71e43fda-5f0 (probe, 2 agents), plus the PR-2 probe agent and the plain-English check agent, under the session's subagents directory. Matrix logs and edit scripts in the session scratchpad (probe/, probe-verify/, probe-pr2/, pr1check/, refute1/, refuter2/).
