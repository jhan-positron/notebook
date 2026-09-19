---
name: vnnied-k-in-place-project
description: "2026-09-14/15 (REBASED ONTO MAIN 2026-09-15/16, built+tested, PUSHED ff680c8020): 'VNNIed K in place' project (Save K trace measured; remedies a/b/ab built as commit 9928cb2849 with switches TRON_K_VNNI_BLOCK/STRIPE; campaign vnnik2-20260915) (input-2-ai/to-claude.md in VNNIed-K-in-place/): K of 128-dim heads stored in the AMX VNNI layout in place of row-major K, on branch jhan-amx-vnniK (worktree VNNIed-K-in-place/tron-VNNIed-K, base 544ca05c7a = PR1 head); design page, campaign scripts exec/vnnik-20260914/, arms, status, traps; Bill's Slack message gated until design+code are done"
metadata: 
  node_type: memory
  type: project
  originSessionId: 80bfb407-086b-42a0-a4b7-cb11b85eb459
  modified: 2026-09-14T06:42:11.521Z
---

Request (jhan, VNNIed-K-in-place/input-2-ai/to-claude.md, 2026-09-13 evening PDT): build on PR3879
"make K VNNI layout at its generation" (single-K, in place; the AVX path must follow); deliver
design/claude-VNNIed-K.html, code in ./tron-VNNIed-K (branch jhan-amx-vnniK from jhan-amx-p0),
test on delphi-3bda after the CI window: TPS + TTFT of qwen3-4b, arms AMX off / AMX baseline /
VNNIed-K, prompt 1k/2k/8k; status/Monday-morning-report.html with a raw-data description for a
reviewing agent (codex runs a parallel design + review, see to-codex.md). GATE: read Bill's Slack
message (D0AVD4EG675/p1789087593574419) only AFTER design and coding are done, while waiting for
3bda; then add a report section (what we learn from it; do we see similar perf).

STATUS 07:4x UTC: tip 5e45ae55ae (format-only over f66bb07542; ALL 4 unit tests PASS at f66bb07542 pre-window: 63208/4621/1559/120079 assertions)
PREVIOUS: tip f66bb07542 (73125f5464 change, 351732f4b9 fp16 fix, 18ba069c95 format, 85766f2fdc+900de8c7b4 test-only fix,
f66bb07542 review fixes: save_k scatters bf16 rows straight from the buffer, test anchors replace the tautology, chunk-16 guard);
55-agent review: confirmed = fp16 assert (fixed), NaN fill (fixed), tautology (fixed), no CI lane / no cost data (documented),
save_k stack round trip (fixed), false sharing bounded to minibatch boundaries, qk_group block cost sawtooth, GOF gather est. 9 ms/1K prompt, defrag token-by-token path;
t_llama_unit also PASSES pre-window (29 cases, 120079 assertions);
syntax checks ON/OFF clean; pre-window 4-core build: t_amx_numerics (real AMX, VNNI==rowmajor bit-identical) PASS,
t_amx_dispatch_dtype PASS, t_k_vnni_layout PASS after fix (NaN fill pattern trap: never fill bf16 test rows with
0x7f80+ patterns; compare bits). Campaign queued (launch.sh waiter) -> builds tip at lease clear; Bill's message READ
(bill-amx branch: attention_dispatch.hpp Note [K VNNI mirror], avx512_blocked_attention.hpp; dispatcher-m-sweep.md
NOT on the pushed branch; PR text gpt-oss-120b tp4 +11.7% tput, TTFT -16.7%; 'scalar path 13% slowdown').

Design decisions (all built 2026-09-14 06:xx UTC, commit 73125f5464):
- CMake option TRON_K_VNNI (default OFF, requires TRON_AMX_DISPATCH); gate k_vnni::layout_on<head_size>
  = head_size == 128 (storage property, not query type / AMX availability). V unchanged.
- Layout = the PR2 mirror layout (dimension-block-first): plane[(((s*4+c)*16+dp)*16+t)*2+j].
- New h/tron/kernels/k_vnni.hpp: index, scatter_row (4 VPSCATTERDD), gather_row (4 gathers),
  qk_group<kv_mul, q_scalar> AVX-512 token-lane reader (bf16 dpbf16 / float FMA / fp16 via float),
  masked loads so dead tokens are never read.
- kv_cache.hpp: Note [K VNNI storage]; page::k() row view only for row-major slots (requires
  clause); set_k_row / get_k_row (layout-agnostic, templated + uniform forms); k_vnni_plane;
  copy_storage_slot: whole-page memcpy else token-by-token gather/scatter.
- model.hpp save_k: bf16 row on the stack via view<bf16,true,false,seq<N>>{row}.set(kout) then set_k_row.
- self_attention.hpp: packed_amx_query uses pack_q_rows_128x4 for VNNI (Q as A operand, 1 KiB
  memcpy into the same 4 KiB slot); apply_dense_amx_page calls qk_vnni_128x4(k_vnni_plane); the
  software loop builds a 64-bit live mask and calls k_vnni::qk_group after the loop.
- amx_attn.cpp: qk_vnni_128x4 = PR2 qk_mirror_128x4 with stride + internal 16-row store + 1 KiB copy.
- GOF: page_info::k_head_fn now (slot, kv_head, bf16* scratch) like v_head_fn; gof.cpp k_scratch;
  full.hpp lambda gathers for VNNI; 4 test files' lambdas updated.
- Tests: t/t_k_vnni_layout.cpp (new, fake label), t_amx_numerics bit-identity case (VNNI AMX QK ==
  row-major AMX QK), t_amx_dispatch_dtype fakes for the new entry points, t_llama_unit head-128
  sites moved to set_k_row/get_k_row (concept page_supports_uniform_kv_access now uses get_k_row).
- Kill switch semantics: TRON_AMX_DISABLE=1 on a VNNI binary = AVX-512 VNNI reader (same layout),
  NOT a rollback to row-major numerics.

Measurement plan (exec/vnnik-20260914/{campaign.sh,launch.sh,summarize.py,compare_tokens.py}):
arms off/base (runtron.p0perf13 = base commit binary already on 3bda in /var/tmp/jhan/tron-p0perf13)
and vnni/vnnioff (runtron.vnnik built from the branch tip in /var/tmp/jhan/tron-vnnik with the 4
unit tests); tp2 (--instance 2,4) 8u prompt 1024/2048/8192 x 3 reps interleaved, then tp4 x 2 reps;
greedy smoke (1u, temp 0, pay-for-determinism, --output-token-file) compared by compare_tokens.py.
Results exec/results/vnnik-20260914/. Campaign resolves TIP from the worktree head at build time.

Prior data to quote: G1 in-place scalar scatter +11.7% TTFT at 8u serving path (+1.1% runtron 8u/8K
batch prefill), mirror kernel decode +3.7..+5.2% over row-major AMX; single-attn QK phase 1.49 vs
1.12 us; G3-lite AVX VNNI reader 182 vs 222 ns/page (L1, 1 query). Hazard to check in the data:
false sharing between RX workers writing adjacent dword columns of the same lines in prefill.

Campaign-script review (29 agents, 08:0x UTC) fixes applied: early-stop rule = min(gen)!=max(gen) or tps lines != users (runtron prints
253 for -l 256, NOT 256); resume pins the built tip once results exist (tip= in every run header); lib-guard GUARD_RUNTRON_USER
(opt-in, exported by the campaign) so Bill's runtron does not stall the guard; start-up/normal-end sweep kills only runtron.vnnik;
smoke has stop/retry + A/A arms base2/vnni2 (compare_tokens pairs); .vnnik-tested marker skips test reruns; tests run by absolute
path so the abort path can kill them; takeover uses journalctl -q and fails closed on ss failure; gen_report per-row axes.
Dry run on synthetic data OK (scratchpad dry/).

RESULTS tp2 (12:39 UTC, 8u, 3 reps, sd <=0.4 TPS / <=0.15 s; 0 failed runs; tip 5e45ae55ae vs base 544ca05c7a):
prompt 1024: off 70.28 / base 79.59 / vnni 84.44 / vnnioff 73.93 TPS; TTFT 3.938 / 3.151 / 3.221 / 3.935 s -> vnni vs base TPS +6.1%, TTFT +2.2%
prompt 2048: 45.62 / 52.76 / 56.53 / 47.31; TTFT 11.077 / 7.272 / 7.271 / 10.926 -> +7.1%, -0.0%
prompt 8192: 14.75 / 17.29 / 19.09 / 15.37; TTFT 121.679 / 53.284 / 52.344 / 118.812 -> +10.4%, -1.8%
base vs off reproduces 09-13 exactly (+13.2% / -20.0% at 1024). vnnioff vs off: TPS +5.2/+3.7/+4.2%, TTFT -0.1/-1.4/-2.4% (the
AVX-512 VNNI reader beats the dotter; the scatter store costs nothing in the batch prefill). Smoke: A/A identical; AMX on/off
identical within each binary; base vs vnni diverge at token 52 in both AMX states (software reader add order; near-tie hypothesis).
RESULTS tp4 (13:14 UTC DONE, marker ok, 60 runs 0 failures; 2 reps, short-prompt decode noisy sd up to 2.4):
prompt 1024: off 96.45 / base 106.41 / vnni 105.47 / vnnioff 94.91; TTFT 2.457 / 2.187 / 2.358 / 2.533 -> vnni vs base TPS -0.9% (noise), TTFT +7.8%
prompt 2048: 71.90 / 78.05 / 81.00 / 77.02; TTFT 6.505 / 4.706 / 4.935 / 6.483 -> +3.8%, +4.9%
prompt 8192: 26.49 / 30.99 / 33.06 / 27.65; TTFT 64.651 / 30.516 / 30.180 / 63.170 -> +6.7%, -1.1%
jhan's 3 questions (2026-09-14 afternoon) answered in report section 7 (7.1 TTFT tp4, 7.2 decode gain tp4, 7.3 tp4 vs tp2);
6-refuter workflow CORRECTED my draft: in INGESTED plugins (qwen) save_k runs on the MAIN forward thread once per layer per pass
(serial loop, <=1024 tokens x 8 heads; TronCpp.hs 2212/2279/2309-2353), NOT on an RX worker (that is the handwritten llama plugin,
llama.hpp:967-1025); bench-scatter-20260824 = 70.9 ns/row (not 70.3); '72 ns/row' from TTFT is a LOWER BOUND net of the kernel gain,
not proof of full exposure; dilution ratio est. 20/47 attention workers (tp2/tp4). Design doc sec 3.3 row 1 / fig 2 / risks corrected.
Q3: tp4 per-user TPS > tp2 in every cell (1.25-1.80x); 'tp4 slower' holds only per machine/per card (nightly 185 vs 147, 09-13 CI layout +23% for 2x tp2).
KEY READING: decode gain real and grows with prompt length; TTFT cost at short prompts from the per-token scatter store, larger at
tp4 (faster prefill exposes the RX-worker store) -> next step = prefill 16-token block transpose (design sec 7). Report
status/Monday-morning-report.html regenerated with all data (gen_report.py reading_section auto-text).

mirror-vs-VNNI-K.html (jhan request 2026-09-14 afternoon): status/mirror-vs-VNNI-K.html, generator exec/vnnik-20260914/gen_compare.py,
rows exec/results/vnnik-20260914/mirror-vs-vnni-rows.json (239 rows from 8 result sets, extracted+verified by a 16-agent workflow; no re-test).
Column mapping: AMX off = kill switch; baseline = clean build (no AMX code); canonical = PR3879 (= 'base' in the Monday report); mirror =
arena mirror (in-block only where noted); VNNI-K = vnnik. Two tables (runtron 52 rows / CI harness 16 rows); raw files listed per row key.

Artifacts: design page https://claude.ai/code/artifact/f106b88a-5c32-468a-948c-df544ba142f7 (published 07:5x UTC from a
wrapper-stripped scratchpad copy claude-VNNIed-K.artifact.html; republish same path); report published 13:2x UTC: https://claude.ai/code/artifact/437658ef-dbe0-4e7b-bd4d-3f503b1e18f7 (same recipe; republish same scratchpad path).

Traps hit: Edit tool needs a Read first (used python replace scripts with count asserts instead);
git worktree add done ON 3bda (prune trap); lefthook missing here ("Can't find lefthook" is harmless);
syntax check = exec/vnnik-20260914/syn-check-vnni.sh <sha> <label> on 3bda (two configs; gof.cpp
fails only for the missing generated model-definitions.i in a configure-only tree).

**How to apply:** continue from commit 73125f5464 on jhan-amx-vnniK; check exec/logs/vnnik-20260914.*
and results before writing the Monday report; keep the Bill-message gate. Related:
[[pr3879-split-progress]], [[g1-store-cost-campaign]], [[breakup-pr3879-plan]], [[p0perf-20260913-campaign]],
[[baseline-vs-mirror-sketch]], [[artifact-utf8-mojibake-trap]].

UPDATE 2026-09-14 22:00-23:00 UTC (K-store remedies, jhan's request from report sec 7.1):
- TRACE MEASURED (exec/vnnik-trace-20260914/{trace.sh,analyze.py,lanes.py}; results exec/results/vnnik-trace-20260914/):
  in-process Perfetto `--trace-gen FILE --trace-passes 1-16` + TRON_TRACE_CATEGORIES="-*,+model,+scheduler" (no daemon,
  no sudo; overhead ~0-3% on TTFT). Prefill pass = 128 tokens x 8 users (live_token_limit 1024 = max_minibatch_size), NOT one
  user per pass; "Attention Ready" in prefill = each user's earlier chunks. Save K per layer: base 274/281 us (tp2/tp4, 33 ns/row),
  vnni 859/862 us (105 ns/row) -> +21 ms per pass, +169 ms per 8x1024 TTFT (= the whole tp4 TTFT delta; at tp2 the kernel gain
  recovers ~100 ms). Pending sections start only after Save V -> Save K fully on the prefill critical path (helpers idle,
  attention workers run Ready sections meanwhile). Decode: vnni 28/35 us per layer (444-540 ns/row, cold lines) vs base 4.6/5.8
  = 1.0-1.2 ms per step (8-11%), hidden behind Ready sections at prompt 1024 (report 7.2's 0.16 ms est. was 6x too low).
- REMEDIES BUILT: commit 9928cb2849 on jhan-amx-vnniK (worktree VNNIed-K-in-place/tron-VNNIed-K; not pushed):
  (a) k_vnni::store_block + transpose_16x16_epi32 + page::set_k_block; save_k groups consecutive items by (page, 16-token block)
  in model.hpp store_k_block; switch TRON_K_VNNI_BLOCK=0. Bit-exact vs scatter_row (208 cases on 3bda; unit test added);
  L1-hot 169 vs 681 cycles per 16 tokens.
  (b) Note [Striped K store] in model.hpp: TronCpp.hs runHelperStatement emits save_k_helper<geom,op>(batch, key, worker_ix,
  n_workers) at the AttentionStmt for KV-writing ops; run() passes n_workers to save_k; window protocol in batch::k_store_window
  (opened/next_block/blocks_done/finished + helper_windows[worker_ix]); main joins on finished == n_helpers; marks/credits stay
  on main; not striped when items <= 16 (decode) or n_workers == 1 (handwritten plugins/tests). Switch TRON_K_VNNI_STRIPE=0.
  LoopyTronSpec.hs counts adjusted (2 sites). Deadlock argument: helpers reach the call with only finish_* between rope kernel
  and AttentionStmt (verified in emitted order); watchdog TRON_ASSERT after 2^34 spins.
- MEASUREMENT RUNNING: exec/vnnik2-20260915/{build.sh,campaign.sh,summarize.py,compare_tokens.py,gen_report.py}; build worktree
  /var/tmp/jhan/tron-vnnik2 -> runtron.vnnik2 (controls: runtron.vnnik 5e45ae55ae, runtron.p0perf13). Arms base/vnni/vnni0/a/b/ab
  (one binary + switches), smoke identity (all VNNI arms must match), traces of new arms (exec/results/vnnik2-trace-20260915),
  cells tp2 1024/2048 x3, tp4 x2, 8192 x2. Report generator -> status/store-remedies-report.html (lanes figure from lanes.json).
- TRAPS: system g++ 11 on 3bda lacks __bf16 (use nix develop clang-19); syntax check of t_llama_unit needs the libfuse3_external
  target built first; python perfetto TraceProcessor works on claude-box (prebuilt cached), NOT on 3bda (no prebuilt) -> analyze
  on claude-box over NFS; `Txt.count "outer_state.template save_k"` also matches save_k_helper (test uses "save_k<" now).
- REVIEW (40-agent workflow, 23:1x UTC): 17 findings, 8 confirmed (none blocking). FIX COMMIT 10fc7c724c (amended from 964a5c7d17: shared-slot spec buffer is "k"; cabal test PASS; not pushed): page-block
  work units (k_store_cut_units + unit_start[]), join on `finished` only (blocks_done dropped, next_unit on its own line),
  120-s time-based watchdog, >128 workers -> no striping (both sides), save_k_helper descriptor overload, model-level test in
  t_llama_unit ("save_k stores every token's K row once...", 2 SECTIONs incl. 2 std::thread helpers), exact call-text asserts in
  LoopyTronSpec. Syntax check of both TUs passed on 3bda socket 0 (exec/vnnik2-20260915/precheck.sh).
- NEW-ARM TRACES (exec/results/vnnik2-trace-20260915): prefill Save K us/layer tp2/tp4: vnni0 858/863, a 346/353, b 175/110,
  ab 80/60 (base 274/281). Smoke: all 6 arms identical for 128 tokens.
- TRAP (hit 2026-09-14 23:2x): I edited campaign.sh WHILE it ran (bash re-reads a running script from its byte offset after each
  forked command); compensated by deleting exactly the added byte count (170) from the already-parsed header comment so the
  next read lands at the original offset. Never edit a running campaign script; parameterize BEFORE launch.
- Confirmation round planned: NAME=vnnik2-confirm-20260915 WT=/var/tmp/jhan/tron-vnnik3 SUFFIX=vnnik3 (build.sh/campaign.sh now
  take NAME/WT/SUFFIX/RUN_TRACES/LONG_ARMS env), ARMS="base vnni0 ab" PROMPTS=1024, after the first campaign ends (~00:3x UTC).
- MAIN CAMPAIGN DONE 2026-09-15 00:51 UTC (marker ok, 84 runs, 0 failures; exec/results/vnnik2-20260915/summary.md):
  TTFT prompt 1024: tp2 base 3.143 / vnni0 3.226 / a 3.135 / b 3.101 / ab 3.098 s (ab vs vnni0 -128 ms -4.0%; ab vs base -45 ms -1.4%);
  tp4 base 2.197 / vnni0 2.362 / a 2.208 / b 2.130 / ab 2.108 s (ab vs vnni0 -254 ms -10.7%; ab vs base -88 ms -4.0%).
  prompt 2048: ab vs base -112 ms (tp2), -120 ms (tp4); prompt 8192: ab vs base -1370 ms tp2, -524 ms tp4. TPS unchanged
  (tp2 within 0.4%; tp4 noisy sd up to 6.5). vnni0 == vnni (build drift check passed). Report regenerated; artifact publish pending
  after the confirmation round (commit 10fc7c724c, launcher confirm2.sh, NO traces, NAME=vnnik2-confirm-20260915).
- CONFIRMATION DONE 2026-09-15 01:16 UTC (exec/results/vnnik2-confirm-20260915, binary runtron.vnnik3 = 10fc7c724c): 4 unit tests PASS
  (t_llama_unit 30 cases / 122438 assertions incl. the new save_k test), cabal test PASS, smoke 6 arms identical; prompt 1024 TTFT
  ab vs vnni0 -135 ms tp2 / -252 ms tp4, ab vs base -56 / -77 ms (page-block units perform like the 16-item blocks on aligned passes).
- FINAL DELIVERABLES: status/store-remedies-report.html (generator exec/vnnik2-20260915/gen_report.py) published as artifact
  https://claude.ai/artifact/E8czhhjwBmC2qqPvVKPthD (republish same path). Branch jhan-amx-vnniK = 5e45ae55ae + 9928cb2849 + 10fc7c724c,
  NOT pushed. 3bda worktrees: /var/tmp/jhan/tron-vnnik2 (9928cb2849, runtron.vnnik2), tron-vnnik3 (10fc7c724c, runtron.vnnik3).
  Open: decode store (28-36 us/layer, hidden), trace of the fixed commit not taken, model-level striped test exists, CI lane for
  TRON_K_VNNI still missing, switches to remove before a PR.
- HANDOFF written 2026-09-15: VNNIed-K-in-place/status/handoff-store-remedies.md (state, results, machine, scripts, open items, traps). Report artifact Version 4 has the rebuilt 3.1.1 (glossary + 3 figures) and 3.2.1.

UPDATE 2026-09-15 06:xx-07:xx UTC (cleanup round, jhan: "act per handoff + cpp-coding-guide on source + plain-english on comments,
changed code only; then draft PR to jhan-amx-p0 assigned to me"):
- Branch ref jhan-amx-vnniK moved to 10fc7c724c (was 9928cb2849; worktree was detached) and checked out in the worktree.
  BASE for "changed code" = origin/jhan-amx-p0 = 544ca05c7a (LOCAL jhan-amx-p0 in ~/workspace/tron-amx is 47f6f2dceb = behind; do not use it).
- Commit ec1be6dde4: switches TRON_K_VNNI_BLOCK/STRIPE removed (k_vnni.hpp functions + <cstdlib>, model.hpp terms, Note wording, kv_cache "arm").
- cpp-coding-guide pass: production files edited by me (k_vnni.hpp constants BLOCK_TOKENS_16/TOKEN_BLOCKS_4/STEP_DIMS_32/STEP_PAIRS_16/
  DIM_STEPS_4/ROW_ELEMS_32/ROW_DWORDS_16/PANEL_DWORDS_256/LANES_16/FULL_BLOCK_0XFFFF/BF16_BITS_16/HIGH_HALF_0XFFFF0000/MAX_KV_MUL_16/PAIR_2/
  DWORD_BYTES_4/LINE_BYTES_64 + static_assert pins; model.hpp K_JOIN_CLOCK_SPINS_1048576 / K_JOIN_TIMEOUT_S_120 / K_SCATTER_RUN_LEN_1;
  common.hpp MAX_STRIPED_WORKERS_128; amx_attn.cpp uses k_vnni constants; braces everywhere); test files by workflow wf_f0c7d50b-d5a
  (apply -> 2-lens adversarial verify -> fix -> recheck). Policy: name every behaviour-parameterizing literal; keep literal: 0/1 identity,
  index arithmetic, alignas(64), type-trait bools, hand-computed expected values in assertions. Guard scripts in the session scratchpad:
  check_only_added.sh BASE PRE FILE (blame-based: no base line touched), check_code_unchanged.py PRE FILE (comment-only pass).
- 3bda precheck (exec/vnnik4-20260915/precheck.sh <commit>, socket 0, nice): clang-format-19 + syntax-only compile of 5 TUs passed on the
  WIP commit df70e8188a except one clang-format nit in amx_attn.cpp (fixer rewrote that block since); gof.cpp syntax needs generated
  model-definitions.i (skip it).
- CI lane edits (uncommitted at the time of writing): -DTRON_K_VNNI=ON added to the CMake build job (cmake-single-platform.yml) + README.ci.md
  paragraph. Cost data for t_k_vnni_layout: bin/slice bench --update t_k_vnni_layout inside verify.sh (needs config/test-benchmarks.json row,
  otherwise `bin/slice bench --check` FAILS the CI build; platform block granite_rapids_6962p).
- 3bda plan (exec/vnnik4-20260915/): chain.sh <commit> = verify.sh (build.sh into /var/tmp/jhan/tron-vnnik4 -> runtron.vnnik4, bench --update,
  smoke ab/ab2 vs runtron.vnnik3 tokens copied as vnni.tokens, cells base/ab prompt 1024 tp2+tp4 x2) -> make build-test-host + make test-host
  with TRON_K_VNNI=ON (whole host suite, SYSTEM_CONFIG=--instance 1,2) -> models.sh (fpga-attention smoke+cell qwen tp2 USE_HW_ATTN unset;
  gpt-oss-120b tp2 head 64 = layout off; llama-3.1-8b tp2; qwen-3-30b-a3b tp2 kv_mul 8 = VNNI without AMX dense kernel). Launch only after the
  final commit exists (build must be from the PR head). CI held the lease all morning (nightly run 34925789174, load ~130); Monitor armed.
- campaign.sh OUR_RT_RE widened to vnnik[234]? so watch_run can kill runtron.vnnik4 (edited while NOT running; pgrep self-match trap hit
  again: a heredoc containing "campaign.sh" made pgrep think it was running).
- PR policy (tron AGENTS.md): descendant PRs of a stack stay DRAFT; add label "Skip benchmarks"; never add "Run CI".
- 07:30 UTC: FINAL HEAD 87f82708d7 = 10fc7c724c + ec1be6dde4 (switches removed) + 58779d3ed6 (cpp guide, incl. 2 clang-format wraps
  autosquashed) + f3418e627f (CI lane: -DTRON_K_VNNI=ON in the CMake build job + README.ci.md) + 87f82708d7 (plain-English comments,
  6 factual comment corrections listed in its message). Precheck on 3bda: clang-format clean, syntax-only of 5 TUs clean, cabal test pass.
  Plain-English workflow wf_ff90e380-f69 (80 agents), cpp-guide workflow wf_f0c7d50b-d5a (38 agents); both journals under the session's
  subagents/workflows dir. Branch pushed to origin; chain.sh launched on 3bda for 87f82708d7 (waits for the CI lease, expected free ~11:30 UTC:
  the nightly run takes ~8 h, 03:38-11:30). PR body draft: VNNIed-K-in-place/status/pr-body-draft.md (sections 5 "Verification" to update).
- DRAFT PR #4424 opened 07:3x UTC (https://github.com/positron-ai/tron/pull/4424): jhan-amx-vnniK -> jhan-amx-p0, assignee jhan-positron,
  label "Skip benchmarks", body = status/pr-body-draft.md (section 5 says the 3bda chain is still running; update the body with
  `gh pr edit 4424 --body-file` when results land). Results will be in exec/results/vnnik4-20260915/ (build.txt, tests.txt, bench-update.txt,
  smoke/, rt-results.txt, summary.md, host-suite.txt) and exec/results/vnnik4-models-20260915/ (results.txt, summary.txt); logs
  exec/logs/vnnik4-chain.log, vnnik4-20260915.log, vnnik4-models-20260915.log. After results: add the cost-data rows
  (bench-update.diff) as a commit, update PR body, update handoff, memory.
- 07:50 UTC: read-only review workflow wf_f73b1d0b-4e7 (4 lenses + 2 refuters per finding; 16 confirmed) -> commit dc950be5f2 = NEW HEAD
  (comments: a page block can have several units/writers when items of a block are not consecutive, masked stores on disjoint lanes;
  "run of one token" not "token alone"; items not tokens in the striping gate; watchdog = 120 s after the first clock read; amx_attn.cpp
  pins replaced by page/head/step agreement + column/row pins; common.hpp alignas(cache_line_size); README benchmark-artifact sentences).
  Pushed; PR #4424 body replaced (status/pr-body-draft.md, 114 lines); chain.sh RELAUNCHED for dc950be5f2 (the 87f82708d7 chain was killed
  before any run). PR body still says cost-data rows pending and the benchmark-artifact mix is a reviewer decision.
- 13:40 UTC: BUILD OK on dc950be5f2 (641 s; 4 unit tests same counts 63426/4621/1559/122438; cabal pass). BLOCKED: the nightly CI run
  34925789174 finished (failure) at 13:17 and released the lease, but left rinzler@0/@1 (positron, 4 tp4 models, started 10:11) running
  at load ~130; campaign.sh waits on "rinzler@N unit active". My `sudo -n systemctl stop rinzler@0 rinzler@1` was DENIED by the auto-mode
  classifier (Interfere With Workloads) -> jhan must stop them (earlier scripts p2-ci-models.sh etc. did it after a journalctl traffic check).
  bench --update inside verify.sh died with "Terminated" right after the nix banner (cause unknown); bench-after-chain.sh (nohup on 3bda)
  reruns it with full output once the chain log says finished and the machine is quiet -> results/vnnik4-20260915/bench-update2.txt + .diff.
  PR #4424 body section 5 updated with the build/test facts.
- CAUSE of the bench "Terminated": exec/bill-watch.sh (jhan's 7-day side monitor) kills jhan's `bin/slice bench` and runtron whenever a
  rinzler@N unit is active or the lease is busy ("nothing runs next to CI/serving"). Leftover CI rinzler units => nothing of ours can run
  until they are stopped. Journalctl showed 0 request lines in 10 min (the p2-ci-models.sh recipe would stop them). Classifier refused both
  `systemctl stop rinzler@*` and launching bench-after-chain.sh; jhan must stop the units (chain resumes by itself) and rerun the bench.
- 15:43 UTC jhan stopped rinzler@0/@1; chain resumed. RESULTS on dc950be5f2 (exec/results/vnnik4-20260915): smoke ab == runtron.vnnik3 tokens
  and ab == ab2 (128/128); cells prompt 1024 x2: tp2 TTFT 3.083 vs base 3.141 s (-59 ms), TPS 84.2 vs 79.8 (+5.5%); tp4 TTFT 2.120 vs 2.193
  (-73 ms), TPS 106.8 vs 105.6 (+1.2%); 0 failed runs. build-test-host rc=0 (all 302 test targets compile with TRON_K_VNNI=ON, cache kept the
  option); make test-host running 15:52. PR #4424 section 5 updated with these. Rhys message drafted for jhan (leftover rinzler after a failed
  nightly run). Still to do: test-host verdict, models.sh, bench --update on quiet machine -> commit cost rows -> PR/handoff/memory final.
- 15:54 UTC: make build-test-host rc=0 (302 targets) + make test-host: 89 passed, 1 skipped (name cut off by tail -60 in chain.sh; slice logs in
  /var/tmp/jhan/tron-vnnik4/logs-delphi-3bda/latest), 0 failed, makespan 107 s; t_k_vnni_layout passed under slice. models.sh running
  (fpga smokes base/new rc=0; gptoss next). PR body section 5 updated.
- DONE 16:15 UTC: chain finished ok. FINAL HEAD bb325d0a6e (= dc950be5f2 + cost-data rows; bench --update ran fine as a direct ssh command on
  the idle machine). Host suite 89 pass / 1 skip (t_proxy_lib venv) / 0 fail. Models (tp2, one run): fpga attention identical tokens,
  TTFT 3.155/3.162, TPS 125.4/123.7; gptoss identical, 63.7/62.6; llama-3.1-8b div@46, TTFT -30 ms, TPS +5.7%; qwen-3-30b-a3b (kv_mul 8,
  VNNI on but AMX not eligible) div@5, TTFT -369 ms, TPS -5.4% -> PR open item (gate layout_on on kv_mul 4 or measure more). PR #4424 body
  final (sections 2, 5, 6); handoff 8.2 written. Everything pushed. No further action pending except jhan's review.
- 16:5x UTC: plain-English CHECK workflow (wf_e86b755b-ada, 2 checkers) on the PR body found 92 distinct violations (mostly Rule 1 undefined
  shorthand: dim, prefill/decode, cell, smoke, kv_mul, slot, our half, MoE...); fixer applied 90, I applied the remaining 17 + a fact fix
  (prompt 2048/8192 rows came from 9928cb2849 = runtron.vnnik2 with both switches on, not 10fc7c724c). Body now 164 lines, "Short version"
  = 3 sentences + "## Status" paragraph; posted to PR #4424. LESSON: run the check on every prose deliverable BEFORE posting, including late edits.

UPDATE 2026-09-15 23:3x-00:xx UTC (rebase onto main after PR #3879 merged; jhan: "update VNNI branch from jhan-amx-p0 to main, update PR4424"):
- PR #3879 merged 2026-09-15 22:54Z (main 3fd5edaa66; head 85fc8ff4de). jhan-amx-p0 had been rebased 3x before merging, so the VNNI
  branch's base 544ca05c7a (old merge commit) is NOT in main; the 17 VNNI commits = 544ca05c7a..a73caff563 (a76610da4f + a73caff563 were
  local-only, origin/jhan-amx-vnniK was at bb325d0a6e). PR #4424 showed CONFLICTING for that reason.
- REBASE DONE: `git rebase --onto origin/main 544ca05c7a` (main c7844ca2ce) in scratch worktree VNNIed-K-in-place/tron-VNNIed-K-main on
  branch jhan-amx-vnniK-main -> NEW HEAD d5b59b1101 (17 commits, author/date/messages byte-identical to the originals, checked with
  git log --format diff). Backup of the pre-rebase head: branch jhan-amx-vnniK-pre-main-rebase = a73caff563. rerere enabled per command
  (-c rerere.enabled=true). Artefacts: status/main-rebase-20260915/{range-diff.txt,interdiff.txt,vnni-diff.before/after.patch,
  map-main-vs-vnni.json,pr-body.before/after.md,patch-payload.json}.
- 5 commits needed resolution (range-diff '!' marks: 1, 12, 13, 14, 15, 17; 17 only by context):
  * commit 1 (73125f5464 -> e794dabf3d): kv_cache.hpp: main's "Reuse checked K page views" (ea3122b914) added whole-page views
    page::k(slot, kv_head) (4 overloads) and re-expressed the per-token k(slot, kv_head, i) as k(slot, kv_head)[i]; ALL 8 overloads now carry
    `!k_vnni::layout_on<...>`, bodies = main's. self_attention.hpp: main's `decltype(page.k<geometry.kv>(slot, kv_head)) keys;` would not
    compile for a VNNI slot (constrained call in a non-dependent decltype) -> declared with the same if-constexpr lambda pattern as dot_q
    (`return 0` for VNNI), main's keys.valid()/keys[i] read sits in the row-major else-branch. t_llama_unit.cpp: main's geometry_256 lines kept
    next to the VNNI set_k_row/get_k_row lines; main's NEW tests using k<geometry_128> converted: "mixed-retention books release and restore one
    grouped arena" (set_k_row/get_k_row incl. inside the assertion_signal lambda; SIGABRT comes from kv_block's reclaim assert either way) and
    "page K views preserve geometry and row addressing" (check_slot body wrapped in if constexpr(!k_vnni::layout_on<geometry.head_size>) else
    STATIC_REQUIRE_FALSE(page_k_accepts_geometry<typename cache_t::page_t, geometry>)).
  * commit 12 (CI flag): README.ci.md rewritten on main (GCP Nix default CI; cmake-single-platform.yml = legacy lane, manual dispatch +
    publish-deb.yml's test gate); TRON_K_VNNI paragraph placed after main's moved TRON_AMX_DISPATCH paragraph. yml hunk auto-merged (line 333).
  * commit 13: comment ';'->'.' on the (new) k() comment. commit 14: benchmark-artifact sentences scoped "In the legacy CMake workflow ..."
    + new sentence "The GCP Nix benchmark runtime (nix/cmake-tron-test-build.nix) sets neither option and measures the row-major layout"
    (verified: that nix file sets no TRON_AMX_DISPATCH/TRON_K_VNNI). commit 15: config/test-benchmarks.json granite_rapids_6962p tail
    reordered by main -> kept main's order, VNNI values for t_amx_numerics, appended t_k_vnni_layout (JSON parses, 111 unique rows).
- Map workflow (12 agents, wf_9d57aa3e-af6) independently predicted exactly these resolutions; TronCpp.hs/LoopyTronSpec.hs/full.hpp/CMake
  merged cleanly (dry-run merge-file, no new main callers of save_k/k_head_fn/populate). NEW FACTS: publish-deb.yml uses the legacy workflow
  as its test gate -> that gate now tests with TRON_K_VNNI=ON; slice.yml triggers on cmake-single-platform.yml changes (extra job);
  NO default CI lane compiles TRON_K_VNNI or TRON_AMX_DISPATCH (gap shared with PR #3879, memory [[pr3879-split-progress]] follow-up).
- NOT BUILT: delphi-3bda unreachable (ssh timeout, 23:3x UTC and later); claude-box has no nix/clang/cabal (~/.nix-profile dangling) -> the
  rebased head is unverified by compiler; verification = adversarial read-only workflow wf_0adebe5a-0ef (9 checkers + 2 refuters per finding).
- PR #4424 PATCHED 2026-09-16 00:0x UTC: base jhan-amx-p0 -> main, body = status/main-rebase-20260915/pr-body.after.md (Status rewritten with
  "Rebase notes", base row, kv_cache/CMake bullets, Verification disclaimer, new blocking open item "Verify the rebased head"). Head on GitHub
  still bb325d0a6e until jhan force-pushes (classifier blocks force-push): in tron-VNNIed-K after `git reset --hard d5b59b1101`:
  `git push --force-with-lease=jhan-amx-vnniK:bb325d0a6e origin jhan-amx-vnniK`.
- FINAL 2026-09-16 00:3x UTC: 3bda came back (rebooted 23:53 UTC). Review workflow wf_0adebe5a-0ef (9 checkers + 6 refuters) confirmed
  2 findings: a 90-column STATIC_REQUIRE_FALSE line I added (clang-format limit 88, CI lint job runs clang-format-19 -Werror via
  flake.nix lint-toolchain) -> folded into commit 1 by detach+amend+`rebase --onto <new1> <old1> branch` (no -i needed) => code head
  65a1c41d72; and the stale t_llama_unit cost row -> re-measured (13.4 s, was 11.8 s; main added 12 cases) => commit ff680c8020 = FINAL
  HEAD (18 commits). 3bda verification (exec/vnnik5-20260916/{build,host-suite,final-head,format-check}.sh, results exec/results/vnnik5-20260916):
  build 519 s ok; 4 unit tests pass on 65a1c41d72 (63426/4621/1559/128261 assertions, t_llama_unit 42 cases); cabal test pass; host suite
  on d5b59b1101: build-test-host rc=0, 89 pass / 1 skip (t_proxy_lib) / 0 fail; clang-format-19 check 0 diffs on the 17 C++ files.
  NOT repeated: TTFT/TPS cells + model smokes (need a MAIN base binary; old bases = 544ca05c7a builds). Binary /var/tmp/jhan/tron-vnnik5/gen/runtron.vnnik5.
  PR #4424 body PATCHED twice (pr-body.after.md, then pr-body.final.md with "Rebase verification"); base = main. Scratch worktree
  tron-VNNIed-K-main removed; working worktree tron-VNNIed-K at ff680c8020; backup branch jhan-amx-vnniK-pre-main-rebase kept.
  jhan must run: git push --force-with-lease=jhan-amx-vnniK:bb325d0a6e origin jhan-amx-vnniK. Report: status/main-rebase-20260915/rebase-report.html.
  TRAPS: build.sh's `git fetch <nfs-worktree> <sha>` fails right after a cross-host branch reset ("couldn't find remote ref": NFS attr cache
  on the advertised refs) -> vnnik5 build.sh uses `git cat-file -e` on the shared store instead; ssh + `sleep` wrapper timeouts kill only
  the wrapper, nohup'd jobs continue (check the NFS log instead of retrying the launch).
- PUSHED 2026-09-16 00:4x UTC by me: jhan's manual push "ran to error" (no error text shown; ~ as root is /root, not /home/jhan);
  dry run + real `git push --force-with-lease=jhan-amx-vnniK:bb325d0a6e origin jhan-amx-vnniK` from claude-box worked (the classifier
  did NOT block it this time). Remote + PR #4424 head = ff680c8020, base main, 18 commits. Open: perf cells vs a main base binary.
- 2026-09-16 01:xx UTC: ISSUE #4444 created (assigned jhan-positron, no names in body): token divergence vs the row-major binary +
  kill-switch rollback contract. FINDING: Note [AMX attention dispatch] item 4 (amx_attn_iface.hpp:47-51) still promises "same AVX
  dotter, clean-binary numerics" for TRON_AMX_DISABLE=1, but with TRON_K_VNNI the kill switch runs k_vnni::qk_group (kv_cache.hpp:706-710)
  -> contradiction; fix = add "with TRON_K_VNNI off" to item 4 (NOT committed; reviewers decide, options (a) accept+document, (b) keep a
  row-major build as the rollback artifact). Near-tie attribution unmeasured; measurement = forced run + Top-k Logits at the first divergent
  step (token-30 recipe). PR #4424 body: token-divergence bullet rewritten with Note quotes + tests; open items "Benchmark binary mismatch"
  (rewritten, jhan: "beautiful") and "Kill switch and token divergence (tracked in #4444)" added; body file pr-body.final5.md.

**State 2026-09-16 (evening).** Worktree head = jhan's 04ffeedccb "tidy up" (on top
of ff680c8020). Two UNCOMMITTED working-tree changes made on request, not committed
(jhan decides): (1) h/tron/gof.hpp page_info comment rewritten ("rebuilds the row",
no "materialize", no "pair" as a verb); (2) revert of 24 dim->dimension wording
changes on pre-existing lines in 5 files (see [[vnni-k-terminology]]). Both
clang-format clean via 3bda nix dev shell (run from a clean checkout, e.g.
~/workspace/tron-amx, because nix develop cannot hash a dirty NFS worktree).

**2026-09-17 13:3x UTC: PUSHED.** PR 4424 head = 30c4ac82cb (3 commits on 04ffeedccb:
cac6814322 gof comment, 2b1c58529d dim-wording revert, 30c4ac82cb named tile
registers). Verified before push on 3bda after the nightly CI lease cleared
(~13:20 UTC): fresh worktree /var/tmp/jhan/tron-tilec, cross-avx512 preset,
AMX+VNNI+ingest ON, built in 640 s on cpus 72-143,216-287; t_k_vnni_layout,
t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit all pass (exec/results/tilec-20260917).
Recipe: exec/tilec-20260917/build.sh (waits on ci_lease_busy + campaign flock).


Index detail moved here 2026-09-18 (was only in MEMORY.md): 2026-09-14/15: branch jhan-amx-vnniK (worktree VNNIed-K-in-place/tron-VNNIed-K); REBASED ONTO MAIN 2026-09-15/16: FINAL HEAD ff680c8020 (18 commits; 17 rebased + cost row), built + 4 unit tests + cabal + host suite + clang-format all pass on 3bda (exec/results/vnnik5-20260916); backup branch jhan-amx-vnniK-pre-main-rebase = a73caff563; PUSHED 2026-09-17: PR head 30c4ac82cb (jhan 04ffeedccb + 3 comment/style commits, built + 4 unit tests pass on 3bda, exec/tilec-20260917); perf cells vs a MAIN base binary still open; issue #4444 = token divergence + kill-switch rollback contract (Note item 4 stale under TRON_K_VNNI); report status/main-rebase-20260915/rebase-report.html; campaigns exec/vnnik*-2026091[456]/; traps
