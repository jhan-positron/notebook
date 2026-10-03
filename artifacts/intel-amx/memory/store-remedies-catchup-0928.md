---
name: store-remedies-catchup-0928
description: "2026-09-28: section 0 '9/28 catch-up' inserted at the top of VNNIed-K-in-place/status/store-remedies-report.html (lines 23-178, ASCII, rest byte-identical; backup in the session scratchpad); it is the current one-page status of the VNNI-K project; verified facts + traps found by 3 review rounds (299 agents)"
metadata:
  node_type: memory
  type: project
  originSessionId: ea765415-6b15-42b8-857a-d38b306eaa6b
  modified: 2026-09-28T21:04:37.661Z
---

jhan (2026-09-28): "Is store-remedies-report.html the right file to catch up the project? Insert a 9/28 catch-up section at top."
Answer given: partly. The report is the record of the K save remedies (2026-09-14/17), not the latest status. Section 0
(added 2026-09-28) is now the one-page status: Words table, timeline 09-15 to 09-28, issue #4500 root cause, the
maintainer's review, the section-6 open items today, what comes next, where to read more. Insert script + backup:
session scratchpad insert_catchup.py / store-remedies-report.before-catchup.html (ea765415 session).

Verified facts worth reusing (all checked against GitHub/pages/results by refuter pairs):
- PR #4424: base main since 2026-09-15 23:54 UTC (not 09-16); rebased head force-pushed 09-16 02:00 UTC; head 30c4ac82cb
  pushed 09-17 13:31 UTC (3 commits on jhan's 09-16 "tidy up"); 22 commits; description text unchanged since 09-17 06:29 UTC
  (three 09-25 edits netted zero); CONFLICTING with main ee2d5be0f1: real conflicts in config/test-benchmarks.json,
  h/tron/models/common.hpp, h/tron/models/model.hpp (git 2.34: use 3-arg merge-tree + grep '+<<<<<<<').
- TRAP: pre-rebase commit ids in handoff/memory are NOT in the PR: ec1be6dde4 -> ab94854999 (switch removal),
  10fc7c724c -> 804a08e074 (two-helper test, dated 2026-09-14 23:27 UTC). Cite the rebased ids.
- "shared block save" = the whole K save scheme (block save + sharing); old PR title "striped block store", old code Note
  was Note [Striped K store] (k_store_striped, MAX_STRIPED_WORKERS_128).
- Ben's 09-21 comments = 3 GitHub objects: review 5270304492 (empty body, carries inline 4065141577 TronCpp.hs:2338
  worker-index question, unanswered), review 5270587330 (encapsulate VNNI, vnni_tensor), issue comment 5765866077 (API
  sketch layout/storage/view). Two answered in PR #4557 body table; none replied on #4424.
- PR #4557: opened 09-23 05:28 UTC, ready 13:38 UTC; verification numbers from the 09-22 pre-rebase test (4/4 specs =
  12 token pairs identical, 12/12 in band, host 88/0/1); #4587 folded 09-24 (head c73e7fb2f9, 12 commits); reviewers
  requested 09-28 16:38 UTC (axch, mcherba, BillBaumann, bgamari-positron); no human review yet; open: Q5 allocation
  question (not posted), ~132 (recount 134) 0/1 literals, cost-data row refresh, #4588.
- PR #4596: ready 09-25 22:32 UTC with 5 reviewers (incl. Wado-posi); bot defect fixed 09-26 (1430736b2a); Wade review
  09-28 17:16 UTC = 5 inline comments (2 design questions: per-forward class, per-worker row sizing; T5 SW poll untimed;
  two writers of forwards record; silent range guards).
- Issue #4500: 0 comments; root cause only in the local page; the MIN_B=1 mitigation is NOT in the issue body (issue lists
  4 options). Issue #4444: 2 open parts (reviewer choice between Note condition vs row-major rollback build; forced-run
  near-tie test). Issue #4347 step 1 done by #4505 but not recorded on the issue. Issue #4600 (09-24, colleague):
  AVX-512 scaled_v truncates softmax weights to bf16, bias 0.06-0.27 %; touches scaled_v_expr (moved by #4557).
- Nightly qwen-3-4b tp4 row reads 172.1-174.7 TPS on 09-23..09-28 (141-153 before), cause open (#4534 candidate) -> the
  "-11 % flips the 135 threshold" claim is dated to the 09-18 package.
- wedperf: 1536-token gains (+21.8/+17.0/+8.8 %) were never split main-vs-branch; the split exists only at 256 tokens
  (qwen tp2: main +12.2 %, branch +4.5 %). gpt-oss-120b FPGA "-5.0 %" is not established (layout off; conflicting blocks).
- 09-21/22 prefill FPGA-vs-CPU pairs at 1024: CI harness -1 % (512 vs 518 ms), runtron +2 % (3.20 vs 3.14 s); the
  "-1.9..+4.6 %" range is 09-13 data with the kill switch on.
- Report's runs: TPS/TTFT cells 256 tokens, traces 32, smoke 128; nightly 1536 (845 llama-3.2-3b).
- Nightly configs: 12 rows = 9 models; 8 users in 9 rows (incl. 70b tp2), 4 users in two other 70b rows, 32 users llama-3b;
  13th "AMX benchmark" row since 09-22.

Process facts: 3 workflow rounds (186 + 82 + 31 agents): 35 -> 16 -> 2 fact findings, 69 -> 43 -> 24 English flags,
18 gaps; every fact finding survived 2 refuters (only 1 refuted across rounds). Round-1 Words table had to move to 0.1
(Rule 1: terms before use). Memory-note timestamps of the 09-15/16 rebase were off by 1-2 h vs GitHub.

UPDATE 2026-09-28 (session 6602673a, ultracode): jhan found section 0 too detailed ("no top down view") and asked where the
#4500 fix is. Verified: PR #4424 head 30c4ac82cb (09-17) predates the issue (09-18); no branch/worktree carries a #4500 fix;
the "solution" = the block-wise fix idea (paper only) + the existing main switch TRON_HWATTN_EARLY_LAUNCH_MIN_B (model.hpp:95-120),
both only in issue4500/root-cause-debug.html. Edits: new 0.0 "The project in one picture" (ASCII tree, lines 26-52) inserted before
0.1, and 0.5 rewritten problem -> suggested fixes -> details at 388 words (was 735; 12-agent draft/verify/judge workflow, then
hand fixes from the final refuter). Short-version line 24 now points to 0.0. Backup: session scratchpad
store-remedies-report.before-0928b.html. Rest of the file byte-identical. Section 0.5 now states "Nothing is built or pushed to PR #4424".

**How to apply:** when jhan asks for project status again, start from section 0 of the report and re-check GitHub for
changes after 2026-09-28; when citing commits of PR #4424, use the rebased ids. The artifact copy of the report
(E8czhhjwBmC2qqPvVKPthD) does NOT carry section 0 yet. Related: [[vnnied-k-in-place-project]],
[[issue-4500-root-cause-campaign]], [[issue4525-implementation]], [[attn-stats-pr-implementation]],
[[pr4424-description-on-github]].
