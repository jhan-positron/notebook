---
name: issue-4500-fix-implementation
description: "2026-09-28/29: the issue #4500 fix (row-major tail block for the VNNI K layout) implemented on branch jhan-amx-vnniK-i4500 (6 commits, head f34b0fe2ec; deb line head 8198eab4cc; measured package 98a5accb8b) and MEASURED 2026-09-29 on 3bda: it recovers little of the loss (qwen tp2 2u -3.8 -> -2.3 %, tp4 4u -11.8 -> -8.8 %, both fix-vs-PR n.r. at n=3; llama 8u p4096 unchanged); design, invariants, chain exec/i4500fix-20260928/, results + report paths, what remains open"
metadata:
  node_type: memory
  type: project
  originSessionId: 4434dec4-1336-4a21-aa7d-620e0effca90
  modified: 2026-09-28T23:01:30.436Z
---

Request (jhan 2026-09-28 22:1x UTC, ultracode): build and test the proposed #4500 fix; test qwen3-4b "as before"
(block m6 cells: rinzler on our half, tp2 2 users + tp4 4 users, prompt 1024, FPGA attention) and
llama-3.1-8b-instruct-good-tp2 with 8 users per engine at prompt 4096. Then (23:0x UTC): "Rhys needs to use 3bda,
please hold launching test, please schedule to use the machine tomorrow morning after CI".

DESIGN (commit 78e2da7511, branch jhan-amx-vnniK-i4500, worktree VNNIed-K-in-place/tron-i4500; parent = PR #4424
head 30c4ac82cb; deb commit 96a39b8278 = ci-mimic target 29a8a54740 (main 3faba6d0fd + PR 4424 + preset) + the
fix, worktree ~/workspace/ai-runs/tron-i4500-deb, cherry-pick clean):
- A 16-token K block of a VNNI slot holds its rows ROW-MAJOR inside its own 4 KiB (k_vnni::row_ptr: token t of block
  c at panel (t/4, c) + (t%4)*256 B) until all 16 rows are saved; then main converts it in place
  (k_vnni::block_to_vnni = 4 KiB stack copy + store_block). Note [Row-major tail block] in k_vnni.hpp.
- State: page::k_rows_saved_[n_slots + 1] (atomic uint64 bitmap per storage slot, entry n_slots = EAGLE storage;
  k_state_ix maps slot 0 to it while book::eagle_view_active()). Invariant: block VNNI <=> its 16 bits set.
  Writers: save_k_impl loop 1 (after the stores, BEFORE marks/credits/latch) note_k_row_saved -> k_block_to_vnni
  when the 16th bit lands; full 16-token runs: set_k_block (VNNI) + note_k_block_saved (any thread of the shared
  window, fetch_or); clear_kv_complete_at -> k_forget_row: block_to_rows before dropping a bit (scheduler thread,
  tree lock); copy_from/copy_storage_slot carry bits, un-convert touched dst blocks, copy rows row-major, convert
  completed ones; page move ctor copies bits.
- Readers: dense AMX gate needs k_vnni_blocks == 0xF (fallback = software loop, never abort); the software loop
  scores VNNI blocks with qk_group (live mask) and row-major blocks with the row-major dotter via row_ptr
  (fp32 add order differs from qk_group -> tail-block scores may differ at bf16 ties vs the PR head);
  get_k_row (FPGA staging) = memcpy 256 B from a row-major block, gather from a VNNI block; set_k_row scatters
  only into a complete block (a row saved again).
- set_k_block lost its `present` parameter (full blocks only). K_SCATTER_RUN_LEN_1 removed.
- Tests: t_k_vnni_layout.cpp (+3 TEST_CASEs: kernel round trip, page state across 16th row / clear / re-save,
  append with mixed layouts); t_amx_dispatch_dtype.cpp records rows like save_k (else the dense gate falls back and
  the test's qk_calls==1 expectation fails). Syntax-checked (zig clang 19 via ~/workspace/ai-runs/lcheck, EXTRA=
  -DTRON_K_VNNI variant lcheck2.sh in the session scratchpad) for t_k_vnni_layout, t_llama_unit, t_amx_dispatch_dtype,
  t_gof_dma in both builds; clang-format 19 clean. NOT compiled for real, NOT run: that is chain step A/E.
- Known limitation: the EAGLE view + VNNI shares nothing wrongly now (extra bitmap entry), but no test covers it.
- Reviews: workflow wf_3b4b5a79-160 (6 lenses x 3 refuters) on the code; wf_8c2bb5ff-aa0 on the scripts; apply
  their confirmed findings before launch (check this file's UPDATE lines).

CHAIN exec/i4500fix-20260928/ (README.md there): launch.sh (claude-box) -> chain.sh detached on 3bda with
NOT_BEFORE=2026-09-29T13:00:00Z; steps A build+tests (build2.sh of i4525, /var/tmp/jhan/tron-i4500, cross-avx512
AMX+VNNI+ingest, 7 tests fake device), B build-deb.sh (/var/tmp/jhan/tron-i4500deb -> /var/tmp/jhan/i4500fix-20260928/
{fix.deb,root/}; extracts canon root too), C smoke.sh (runtron tokens: vnni=/var/tmp/jhan/tron-tilec/gen/runtron
30c4ac82cb vs fix vs fix2, cpu+fpga, p1024+p1000), D campaign.sh (cells qwen3-4b tp2 2u p1024, tp4 4u p1024,
llama-8b tp2 8u p4096; binaries base=canon root, vnni=ci-mimic root, fix, nightly=/opt/positron/bin/rinzler; REPS 3;
st_perf2.py = st_perf + --prompt-length; combine.py; summarize.py), E row-major build + 3 tests. Every step waits
for the lease (600 s grace) and other_user_active (Rhys blocks, bill excluded); D takes idle production down through
lib-guard rinzler_takeover_if_idle (in the main shell, latch kept) and brings it back (dut.sh serving-up) at the end.
Results exec/results/i4500fix-20260928/; logs exec/logs/i4500fix-20260928-chain.{log,status}, i4500fix-20260928.{log,status}.
Reference to beat (m6 09-19, n=2): qwen tp2 2u vnni -4.3 %, tp4 4u -13.4 % vs the no-AMX nightly; canon base ~ that nightly.

UPDATE 2026-09-29 19:3x UTC (session 6602673a, jhan: "generate report fix-4500.html, use /plain-english"): page written at
VNNIed-K-in-place/issue4500/fix-4500.html (3963 visible words, pure ASCII, light theme, 2 inline SVGs; scratch copies +
facts bundle in the 6602673a scratchpad fix4500/). Chain RESULT at 617cb8333f (chain 13:00-16:47Z): smoke tokens identical
fix vs PR head under FPGA attention (both prompts) and A/A identical, CPU attention DIFFERS (first diff token 52/128 at
p1024, token 6 at p1000; row-major dotter vs qk_group add order, not proven); cells (rinzler, our half, n=3, canonical AMX
base): qwen tp2 2u vnni -3.8 % / fix -2.3 % (fix vs vnni +1.5 %, t 1.6 NOT resolved); qwen tp4 4u vnni -11.8 % / fix
-8.8 % (fix vs vnni +3.4 %, t 1.8 NOT resolved; sd 14-17 TPS bimodal); llama-8b tp2 8u p4096 vnni +8.9 % / fix +8.5 %
(fix vs vnni -0.4 %, t 3.4); nightly tp4 177.1 = +12.9 % over canonical base (the 09-23 rise, cause open). Unit tests at
617cb8333f: t_k_vnni_layout EAGLE-view case aborted (test defect: book type x_bytes=0 -> DMA alloc assert, fails in both
builds) and t_llama_unit "apply and join page ranges" aborted (VNNI build only: k_state_ix assert on a 0-slot book, read of
layout state before the relevance check = code defect). Later commits 63740b0232 (tests), 675df85c94 (code: state read at
first relevant token), f34b0fe2ec (tests) -> re-test 10/10 + 42/42 in both builds; TPS and tokens NOT re-measured at
f34b0fe2ec. Branch still local, PR 4424 untouched, issue 4500 0 comments (checked 18:26Z). Also: the other session wrote
issue4500/fix-results.html (its own generator gen_report.py); store-remedies-report.html sections 0.0/0.5 were updated on
09-29 to say the fix is built on the side branch and under test (numbers not yet added there).

**How to apply:** after the chain: read summary.md (fix vs vnni and vs base), smoke.txt (fix==fix2 required; fix vs
vnni differences are admissible), tests-fix.txt / tests-fixrm.txt; write the report into VNNIed-K-in-place/issue4500/
and comment on issue #4500; the branch is NOT pushed and PR #4424 is untouched (jhan decides). Related:
[[issue-4500-root-cause-campaign]], [[issue-4500-fpga-attention-vnni-tps]], [[vnnied-k-in-place-project]],
[[store-remedies-catchup-0928]], [[claude-box-tron-build-env]], [[platformd-011-restarts-stopped-units]].

UPDATE 2026-09-28 ~23:40 UTC: first review (wf_3b4b5a79-160, 93 agents) confirmed 18 findings; the 3 real defects were
(1) a block split across two minibatches of one pass (grains of 8) raced the earlier minibatch's readers (pending attention,
coop GOF populate) with the in-place transpose in save_k; (2) clear_kv_complete_at touched storage during a private KV
restore (invalidate_restored_book before finish_reclaimable_kv_restore) -> TRON_ASSERT abort; (3) row-major build failed a
new test (bits dropped only for VNNI slots). Second commit 78582b7ba3 ("convert completed blocks at the forward end;
explicit converted-block state"): two bit sets per storage slot (k_rows_saved_, k_vnni_blocks_), conversion deferred to
run_forward after wait_for_coop_gof (state::pending_k_blocks_, convert_pending_k_blocks; tests call it explicitly),
k_forget_row drops bits >= offset + block bits, transposes back only the offset's block when readable
(k_storage_readable), page::k_storage_of/k_block_to_vnni_at keep the storage offset for the EAGLE view. Deb commit now
a6da845065 (worktree ~/workspace/ai-runs/tron-i4500-deb). Script review (wf_8c2bb5ff-aa0) fixed: serving restore keyed
on results/serving-taken-down.marker (lib.sh serving_restore, chain trap), summarize.py regex ([\w-]+), smoke.done only
when complete (+3 retries), FPGA tests (t_gof_dma, t_gof_staging_leaks) built but not run, build watcher on the lease,
NOT_BEFORE validated, nightly binary sha guard. Second code review wf_f74c0069-5bb launched on 78582b7ba3.

UPDATE 2026-09-29 00:2x UTC: second review (wf_f74c0069-5bb, 46 agents) confirmed 11 (no blocker): row-major build
would fail the "row saved again" REQUIRE (note_k_row_saved kept returning true) -> third commit 617cb8333f: note_k_row_saved
is geometry-templated and returns false / keeps no bits for row-major slots; comments corrected (the concurrent reader is
the coop GOF staging gather, not the attention workers: a pending page is read only after all writer minibatches ticked
the latch; the in-place transposes of clear/copy rely on the tree-lock rule like book relocation; OOM-rescue append
mid-forward is a pre-existing hazard class); EAGLE-view state test + blocks-above test added. Deb commit 98a5accb8b.
Chain relaunched on 3bda with COMMIT_FIX=617cb8333f COMMIT_DEB=98a5accb8b, NOT_BEFORE 2026-09-29T13:00:00Z. Reviewer
suggestions NOT taken (deliberately): a "forward in flight" tripwire assert (would need a new state flag; noted in the
Note instead). Report generator: exec/i4500fix-20260928/gen_report.py -> issue4500/fix-results.html (run after the chain).

RESULTS 2026-09-29 (chain 13:00-16:47 UTC, our half, rinzler + nightly client, 3 reps interleaved, exec/results/i4500fix-20260928/,
report VNNIed-K-in-place/issue4500/fix-results.html from exec/i4500fix-20260928/gen_report.py):
- qwen-3-4b FPGA attention prompt 1024: tp2 2u/engine base 193.5 / vnni 186.2 (-3.8 %) / fix 189.0 (-2.3 % vs base; +1.5 % vs vnni,
  t -1.6 n.r.) / nightly 194.4 TPS; tp4 4u base 156.8 / vnni 138.3 (-11.8 %, rep2 bimodal 118) / fix 143.0 (-8.8 %; +3.4 % vs vnni,
  t -1.8 n.r.; rep2 127) / nightly 177.1 (main since 09-23 is +12.9 % at tp4, separate open item).
- llama-3.1-8b CPU attention tp2 8u/engine prompt 4096: base 39.60 / vnni 43.13 (+8.9 %) / fix 42.97 (+8.5 %; fix vs vnni -0.37 %,
  t +3.35 n.r.) / nightly 39.69. AMX-busy ~63 G (base) vs ~69 G (vnni/fix) cycles per 20 s.
- smoke (runtron, 1 user, temp 0): fix == fix2 in all 4 cells; FPGA attention fix == vnni (128/128, p1024 and p1000); CPU attention
  fix vs vnni differ from token 52 (p1024) / 6 (p1000) = the dotter-vs-qk_group add order on the tail block (admissible, expected).
- unit tests (fake device): VNNI build 3/5 pass; t_k_vnni_layout EAGLE-view test aborted "KV cache DMA allocation failed" (book
  without x bytes cannot carry EAGLE storage -> test now uses uniform_kv_cache<1, geom, 16>) and t_llama_unit apply-and-join
  aborted TRON_ASSERT slot.i < logical_slot_count() (0 >= 0: rows recorded before the pages got tokens -> block moved after the
  pages loop); row-major build: the same layout test. Test-only fix commit 63740b0232 (deb line 8f39279c88); rerun launched
  16:5x UTC (retest.sh, results tests-retest*.txt). No product-code change after the measurement.
- VERDICT: the per-token 64-line access of the incomplete block is NOT the main exposed cost of the VNNI layout in FPGA decode;
  the fix removes it (smoke proves the new path runs) but recovers ~1/3 of the loss at best (n.r.). Candidates left: qk_group vs
  dotter on the engagement-prefix page (positions 64..126 scored on CPU every step, converted blocks), the tp4 AMX-side component
  (kill switch +6.8 % on 09-19), forward-end conversions (est. 0.05 ms/step at 2u, unmeasured). MIN_B=1 (+6.2 %) remains the best lever.
- Machine: production serving restored 16:42 UTC by the campaign (serving-taken-down marker path worked); chain trap no-op after.

UPDATE 2026-09-29 17:3x UTC: retest at 63740b0232: layout test passes both builds; t_llama_unit apply-and-join still aborted in the
VNNI build: addr2line (no gdb on 3bda; `addr2line -f -C -i -e gen/t_llama_unit <offset>` takes ~5 min on the 1 GB binary) showed
k_vnni_blocks -> k_state_ix assert from apply_page_tok, called by the test's "book with no active KV slots" case (book_t empty_cache(1, 0),
window excludes all). Reader fix commit 675df85c94 (deb line 634cddec22): the software loop fetches vnni_blocks/plane at the first
relevant token; the dense gate reads the state after the dense predicate. Rerun launched (retest.sh, markers build-retest*.done).
The measured package (98a5accb8b) differs from the head only by the test fixes and this lazy read; decode paths unchanged.
TRAP: a book with logical_slot_count() == 0 exists in tests; never touch page K state before a token is relevant.

FINAL 2026-09-29 17:33 UTC: all tests pass in both builds at f34b0fe2ec (t_k_vnni_layout 10 cases, t_llama_unit 42 cases; the
chain's other 3 binaries passed at 617cb8333f). Last two fixes were test-side: (1) reader fix 675df85c94 (state read at the first
relevant token; the "book with no active KV slots" case of apply-and-join); (2) f34b0fe2ec: the test stores the row-major build's
K rows first so both builds score one instance (the other instance missed the v_star tolerance by 0.016 with exact scores:
consistent with scaled_v's bf16 weight truncation, issue #4600, hypothesis). Product code differs from the measured package
98a5accb8b only by the lazy state read. Report: VNNIed-K-in-place/issue4500/fix-results.html (gen_report.py; chart checked with
cairosvg). Branch NOT pushed; PR 4424 untouched; issue #4500 has no comment yet (jhan decides).
