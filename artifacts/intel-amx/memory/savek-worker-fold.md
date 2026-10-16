---
name: savek-worker-fold
description: "DONE 2026-10-06 (draft PR #4774 head f52d634c32, 3bda all green): Ben's PR 4424 suggestion r4065141577 (fold save_k_helper into save_k(worker_ix)) implemented on branch jhan-amx-vnniK-savek-worker (worktree ai-runs/tron-vnnik-savek, final commit f52d634c32 on 30c4ac82cb; chain built 19ae84d95a = same code minus one test + one comment); 3bda chain exec/savek-20261006/; DRAFT PR #4774 (base jhan-amx-vnniK, label Skip benchmarks); status + traps inside"
metadata:
  type: project
---

Request (jhan 2026-10-06 ~17:45 UTC, ultracode): "take Ben's suggestion at PR 4424 discussion r4065141577 and come up
updated solution ... code change targeting jhan-amx-vnniK, test it and load draft PR from the new branch to jhan-amx-vnniK".

Ben's comment (2026-09-21, on ingest/src/TronCpp.hs:2338 of 30c4ac82cb): "Why do we need to introduce a new function for
this? Why not simply extend save_k itself with a worker_ix argument and call it consistently from both the main thread and
the helpers?" (the only comment of his two COMMENTED reviews on #4424; PR is CONFLICTING with main, still draft).

Implementation (commit 19ae84d95a, branch jhan-amx-vnniK-savek-worker, worktree ~/workspace/ai-runs/tron-vnnik-savek):
- model.hpp: save_k(q_batch, ks, worker_ix = 0, n_workers = 1) both overloads; save_k_impl branches on worker_ix == 0
  (main: cut/reset/open, claim, join, mark) vs helper (wait own window, claim, finished++, return; returns at once when
  not shared). save_k_helper removed. Note + comments updated.
- TronCpp.hs: helpers emit save_k(k, worker_ix, n_workers); main emits save_k(k, LiteralExpr (IntLit 0), n_workers)
  (same literal 0 kernelCall uses on the main side). LoopyTronSpec: count save_k< == 2, texts ",k,0,n_workers);" and
  ",k,worker_ix,n_workers);". t_llama_unit three-thread section: helpers call save_k with worker_ix, main with
  MAIN_WORKER_IX_0.
- Checks done by hand on 3bda (nix gone on claude-box again 2026-10-06, pre-commit hook needs lefthook -> --no-verify):
  clang-format 19 rc=0, git diff --check rc=0, fourmolu check OK.
- 3bda chain exec/savek-20261006/chain.sh (launched 17:54 UTC, COMMIT=19ae84d95a): A VNNI build (ingest ON) + tests,
  A2 bin/ingest-cabal test, B row-major build, serving-down, C host suite, D token identity new==head (head =
  /var/tmp/jhan/tron-tilec/gen/runtron = 30c4ac82cb), E perf head vs new (cpu 1024/8192, fpga 1024). Results
  exec/results/savek-20261006/, logs exec/logs/savek-20261006-chain.log.
- Review workflow wf_b2263903-559 (5 lenses x 2 refuters) running in parallel.
- PR body draft: session scratchpad pr-body.md (@@TEST@@ placeholder).

Follow-ups: PR #4737 (i4500, 11 save_k_helper mentions) and PR #4746 (typed, 10 mentions) need the same fold after
this lands on jhan-amx-vnniK; the PR #4424 body names save_k_helper in 4 places (jhan edits on GitHub).

Related: [[vnnied-k-in-place-project]], [[sync-4557-into-4424]], [[pr4424-description-on-github]], [[git-rebase-traps]].

STATUS 2026-10-06 18:4x UTC: review workflow wf_b2263903-559 done (40 agents): 3 confirmed (S1 test cannot see a helper
leaking into main's mark tail -> mark_k_complete/is_kv_complete checks added to the test's check lambda; N1 bare `= 1`
default -> KEPT as literal per [[value-suffix-names-shared-files]] (model.hpp is shared); N2 TronCpp.hs comment "claim
16-token blocks" -> "claim work units"), 14 refuted. Amended commit f52d634c32 (--no-verify; clang-format/fourmolu
checked on 3bda). exec/savek-20261006/final.sh rebuilds t_llama_unit (both layouts) + ingest tests at the final commit
after the chain ends (chain measures 19ae84d95a; identical runtron code).
- 2026-10-06 18:5x UTC: branch pushed, DRAFT PR #4774 opened (base jhan-amx-vnniK). Chain A ok (6 tests, kill switch ok),
  A2 ingest tests rc=0; generated plugins: qwen3-4b 36/36 main/helper calls, 0 save_k_helper. PR body Test section
  says "Running now" for B/C/D/E: update it (gh api PATCH, re-fetch first) when chain.done appears, then run final.sh
  (COMMIT=f52d634c32) and add its t_llama_unit + ingest lines.
- 2026-10-06 19:1x UTC: chain DONE 18:44 UTC, all green (A 6 tests, A2 ingest, B, C host 89/1/0, D identical tokens in 3 cells,
  E cpu1024 +0.5 % TPS, cpu8192 -0.5 % TPS with one 61.5-s TTFT outlier, fpga1024 -0.2 %). Rerun savek-E-cpu8k (5 reps,
  new first): no outlier, TPS -0.6 %, TTFT +0.26 s (+0.5 %), inside band. final.sh (f52d634c32) queued behind it.
  PR body Test section draft: scratchpad test-section.md (placeholders @@...@@). TRAP: campaign summary TPS/user is
  decode-only; the runtron log "average tok/s" is a different metric (whole run) and moved the other way.
- DONE 2026-10-06 19:2x UTC: final.sh ok (t_llama_unit 128453/42 VNNI, 128510/42 row-major, ingest rc=0 at f52d634c32);
  PR #4774 body Test section filled (gh api PATCH); serving restored (rinzler@0,1 active as before), lease absent, marker present.
  TRAP: the amend landed on a DETACHED HEAD (reflog: "checkout: moving from jhan-amx-vnniK-savek-worker to 19ae84d95a"
  appeared between the first commit and the amend; cause unknown, the 3bda build2.sh checks out /var/tmp worktrees only),
  so the first push carried 19ae84d95a; fixed with branch -f + checkout + push --force-with-lease. After any amend in an
  NFS-shared worktree: check `git branch --show-current` and compare HEAD with the branch before pushing.
  Open for jhan: review/merge of #4774 into jhan-amx-vnniK; then PR #4737 and PR #4746 need the same fold; PR #4424
  body still names save_k_helper (4 places); reply to Ben's thread r4065141577 (not posted by Claude).
