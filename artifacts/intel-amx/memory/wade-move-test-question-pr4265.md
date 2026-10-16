---
name: wade-move-test-question-pr4265
description: "2026-09-09 Wade (Wado-posi) asked on PR 4265 (r3970127694) to move the t_kv_footprint_memorder test into t_llama_unit with _GLIBCXX_ASSERTIONS on that target; reply drafted (v2 + numbers), wade-exp MEASURED on 3bda 18:08 UTC (define costs +2% time, 0 RSS, nothing else fires; 13/27 cases detect the bug alone); move recommended, jhan decides/posts"
metadata:
  type: project
---

Wade's only review comment on PR 0b (#4265, head 7a7699b338), 2026-09-09 15:23 UTC: why a new
test binary; `t_llama_unit` already constructs/destroys KV books (which run `log_kv_footprint`);
put `_GLIBCXX_ASSERTIONS` on that target and move the test there. jhan asked for a reply drafted
in chat only (not posted). Draft: scratchpad wade/draft-reply.md of session 667a90d8 (2026-09-09).

Position taken in the draft: agree (AGENTS.md test policy: extend the closest existing test),
move = DEFINES on t_llama_unit + keep the #error guard + one explicit case reusing t_llama_unit's
existing `assertion_signal` fork helper (line ~227) + delete the binary and its cost entry +
refresh t_llama_unit's cost entry. Keep the explicit case because (a) the implicit detection via
book constructors gives an unexplained SIGABRT in "attention operations resolve to typed KV slots"
(first book construction, line ~289), (b) it relies on the test TU's constructor instantiations
having no duplicate in libtron.a (nm on the Aug-31/Sep-4 tron-amx build: 15 in the test object,
12 in libtron.a, 0 shared).

Measurement queued: exec/wade-exp-20260909.sh (+ -inner) on delphi-3bda, waits for the other
session's qwen8u8k-pr1-half / gptoss120b-pr1-half campaigns (.done markers), then guard, fresh
worktree /var/tmp/jhan/tron-wade-exp of 7a7699b338, socket 1. E1 baseline, E2 t_llama_unit with the
define (what else fires, time/RSS delta), E3 main's header (a80b102c18) + define: whole binary and
per-case detection, control without define, E4 nm + lld link map. Results:
exec/logs/wade-exp.{txt,log,done}. Not yet run as of 2026-09-09 17:30 UTC.

Verification round (workflow wf_b62bf8f5, 11 agents, 2026-09-09 17:4x UTC) changed the draft (v2 =
scratchpad wade/draft-reply-v2.md):
- DROPPED the "two COMDAT copies" risk: lld (release/19.x InputFiles.cpp, comdatGroups.try_emplace)
  and GNU ld (measured, ld 2.38) keep the FIRST COMDAT copy, and CMake's link line puts the test
  objects before libtron.a, so the checked copy wins even for shared instantiations. Real residual:
  a constructor reached only through a non-inline libtron function, or log_kv_footprint moving to a .cpp.
- The explicit case MUST be declared before the first book-constructing TEST_CASE (line ~250,
  "attention operations resolve to typed KV slots"): Catch2 3.7.1 default order is declaration
  order and the whole binary is one ctest test, so otherwise the process aborts before the named case.
- Policy quote is AGENTS.md:53-54 "Prefer extending the closest existing test with the smallest
  case that proves the behavior"; "rather than add a binary" is NOT in AGENTS.md. AGENTS.md:51-52
  ("If existing coverage already catches the failure, do not add a duplicate test") can be used
  against the explicit case.
- Cost rows: t_llama_unit 2.55-5.39 s / 291-642 MB over 4 platform blocks (genoa96, genoa32,
  granite_rapids_6960p, granite_rapids_6962p; 6962p row 3.38 s / 329 MB); bench --check tests only
  row presence (bin/slice:1760-1793).
- ABI wording: GCC wiki LibstdcxxDebugMode: _GLIBCXX_ASSERTIONS "ABI compatible with normal mode",
  "must not cause changes to the linkage names, sizes or layout of types"; the manual's Macros page
  labels only three other macros ABI-changing and does not label _GLIBCXX_DEBUG.
- Process is multi-threaded at fork because system_init() starts a detached TSC-calibration thread
  (src/system/system.cpp ~2078), not because of TBB (pos_startup's parallel_for range is empty).
  TRON_LOG_KV_GRANULARITY=0/1 makes the child log (harmless); non-numeric makes stoll throw (false fail).
- t_llama_unit is in TEST_INSTALL_TARGETS (t/CMakeLists.txt:860-869); the standalone target is not.
- Use tag "[kv_data]" (file convention); move as two commits (fix; test+bench) instead of add-then-delete.

RESULTS 2026-09-09 18:08 UTC (exec/logs/wade-exp.txt, build 130 s, socket 1, --instance 1,2):
- E1/E2 t_llama_unit fixed header, 3 runs each: without define 6.53/6.27/6.34 s, with define
  6.72/6.38/6.44 s (mean +0.13 s = +2.0%, inside the 0.26 s spread); RSS 655340 KB in all six runs;
  all 27 cases / 120054 assertions pass with the define -> nothing else fires.
- E3 main's header + define: whole binary aborts in case 2 ("attention operations resolve to typed
  KV slots"), atomic_base.h:498 Assertion '__b != memory_order_release'; alone, 13 of 27 cases abort
  (2,3,7,11,17,18,20,21,23,24,25,26,27); control (main's header, no define) passes all 27; the PR's
  own test with main's header fails rc=42 as before.
- E4 PR-head build (BUILD_INGEST_MODELS=OFF): 14 book ctor instantiations in the test object, 6 in
  libtron.a, 0 shared; lld map: all 14 ctor sections come from t_llama_unit.cpp.o.
- Note: measured t_llama_unit time/RSS (6.3 s, 640 MiB) differ from the recorded 6962p bench row
  (3.38 s, 329 MB): different placement/bench conditions; only the paired delta is meaningful.

STATE 2026-09-10 00:5x UTC: MOVE COMMITTED LOCALLY, NOT PUSHED. ~/workspace/ai-runs/tron-pr0b branch
jhan-kv-footprint-memorder = e2f22c7a09 (fix) -> <see PR0b/move-commits.txt> "test: check log_kv_footprint's
memory order in t_llama_unit" (tree identical to the verified 7a5919f178; message amended twice: test: prefix,
paragraph 1, cost-row sentence, 72-column wrap). Verified on 3bda: split-move-head passes (28 cases, 120057
assertions, clang-format patch empty); split-move-reverted (twin ebaeee2c79, main's header) fails the new
first case 6 == 0 then aborts in the first book case, exit 134. Review workflow wf_6bf0fd0e: no must-fix.
CTest registers the whole binary as ONE test (add_catch_test: cmake_parse_arguments always defines
TEST_SIMPLE=FALSE, so the catch_discover_tests branch is dead; CTestTestfile shows one add_test) -> the
"declared first" comment holds in CI. Remote still at 7a7699b338 (old 3-commit history).
jhan's steps: (1) force-push with lease (command in PR0b/move-test-commit-messages.md), (2) gh pr edit 4265
--body-file PR0b/pr-body.v3-move.md, (3) post PR0b/wade-reply.post.md as a reply to r3970127694.
Cost row for t_llama_unit NOT refreshed (bench = whole machine; Bill active).

**Why:** the reply's two open numbers (anything else firing under the define; cost delta on a
2.6-4.6 s / 330-640 MB test) decide whether to move the test; jhan posts the reply, and the move (test moved into t_llama_unit) changes
PR 0b's commit list (dc5d496d06 test, 7a7699b338 cost data).
**How to apply:** when wade-exp.done appears, read wade-exp.txt, fill the two numbers into the
reply, then jhan decides move vs keep. Related: [[pr3879-split-progress]],
[[libstdcxx-assertions-memorder-guard]], [[3bda-shared-with-bill]].

Wording (jhan 2026-09-09): say "move the test into t_llama_unit", not "fold"; "fold" is not a tron term
and was undefined shorthand. Files: PR0b/wade-reply.md, PR0b/move-test-commit-messages.md.
