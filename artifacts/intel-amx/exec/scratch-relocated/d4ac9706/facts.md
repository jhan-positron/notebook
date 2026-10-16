# Fact base for the PR 4424 description proposal (written 2026-10-08 by the main agent)

## Task
PR #4424 (positron-ai/tron, branch jhan-amx-vnniK, base main, draft) is the "VNNI K" PR. Its description lives on GitHub
and MUST NOT be changed by any agent. The owner (jhan) wants a PROPOSAL of the description changes that the merge below
makes necessary. Constraints: the proposed new text totals at most 100 words (count = words of inserted/replacement
text, deleted text does not count; `code identifiers` count as one word each); the text follows the plain-English rules
(CLAUDE.md / plain-english skill); present tense, no change narration (no "was", "now", "previously", "replaced",
"removed"; a PR description reads as if written today); the four protected sections (body lines 1-27: "Short version",
"Background", "Remove the Score transpose by saving VNNI layout and transposed K", "Use shared block in saving K") are
FINAL: never propose text for them (if something there is stale, report it separately as "protected, informational").

## What was merged
- 2026-10-08 ~21:4x UTC: branch jhan-amx-vnniK was fast-forwarded 6b939d25d2 -> ba69cb513e and pushed. PR #4424 head is
  now ba69cb513e (MERGEABLE, draft).
- ba69cb513e = 6b939d25d2 + 45e6bb266d ("VNNI K: one save_k for main and the main helpers (merge of PR 4774)", a merge
  commit with parents 6b939d25d2 and f52d634c32 = PR #4774 head) + ba69cb513e ("Fix grammar in save_k worker comment",
  comment-only, model.hpp 4+/3-).
- Diff 6b939d25d2..ba69cb513e: h/tron/models/model.hpp 118 lines, ingest/src/TronCpp.hs 17, ingest/test/LoopyTronSpec.hs 30,
  t/t_llama_unit.cpp 17 (91+/91-). The full diff is in fold.diff (this directory). `git grep save_k_helper` at ba69cb513e
  finds 0 mentions.
- Content of the fold (verified in PR #4812's review): both `save_k` overloads take `size_t worker_ix = 0, size_t
  n_workers = 1`; `save_k_impl` asserts worker_ix < n_workers; worker 0 (main) cuts the work units, opens the window,
  claims, joins the helpers, marks the tokens; workers 1..n_workers-1 (main helpers) wait for their window, claim, count
  themselves finished, return; `save_k_helper` does not exist. The generator (TronCpp.hs) emits
  `save_k<geometry, op>(q_batch->outer_batch, k, 0, n_workers)` in run() and `save_k<...>(..., k, worker_ix, n_workers)`
  in run_main_help, at the same statement of every KV-writing operation. LoopyTronSpec.hs expects two `save_k` calls per
  KV-writing operation with those two call texts. t_llama_unit's three-thread shared-save case calls save_k on every
  thread (helpers with their worker index, main with main_worker_ix = 0) and checks the K marks.
- PR status: PR #4812 (the fold merged onto 6b939d25d2) is CLOSED by jhan at 21:30 UTC (not merged on GitHub; its
  branch tip ba69cb513e is now the PR #4424 head). PR #4774 (the fold on the previous head) is still OPEN draft, jhan
  closes it. PR #4737 (fix for issue #4500) is OPEN, CONFLICTING with the branch, still names save_k_helper (15 mentions
  in 4 files); it needs a merge of the new head and the same replacement.

## Measured facts at 45e6bb266d (the fold commit; ba69cb513e differs only in one comment)
Source: /home/jhan/workspace/intel-AMX/exec/results/savek2-20261008/ (steps.txt, tests-savek2.txt, tests-savek2rm.txt,
ingest-test-savek2.txt, format-savek2.txt, plugin-calls.txt). delphi-3bda, our half, 2026-10-08, same build setup as the
description's Verification section (nix develop, clang 19, preset native, TRON_AMX_DISPATCH=ON, BUILD_INGEST_MODELS=ON).
- VNNI build (TRON_K_VNNI=ON), real AMX: t_k_vnni_layout 1011650 assertions / 5 cases, t_amx_dispatch_dtype 1612 / 1,
  t_amx_numerics 4621 / 5, t_llama_unit 251755 / 64, t_heterogeneous_scheduler 2783 / 3, t_phase1_integration 2124 / 64,
  all pass. t_amx_numerics under the kill switch TRON_AMX_DISABLE=1: 2060 / 5 pass with three "AMX unavailable" lines.
- ingest Haskell suite (bin/ingest-cabal test): rc=0.
- Row-major build (TRON_K_VNNI=OFF): t_k_vnni_layout 1011650 / 5, t_amx_dispatch_dtype 1612 / 1, t_amx_numerics 4621 / 5,
  t_llama_unit 251670 / 64, t_heterogeneous_scheduler 2783 / 3, all pass.
- clang-format rc=0, fourmolu rc=0, git diff --check rc=0.
- Generated plugins (19): main-side save_k calls == helper-side save_k calls == save_v calls per plugin; 0 save_k_helper.
- NOT run at 45e6bb266d or ba69cb513e: token identity, the performance cells, the whole host suite, the cost rows. Those
  rows in the description were taken at 37064d72b2 / 6b939d25d2 (2026-10-08). The fold changes the generated save_k
  calls and model.hpp's save_k, not a kernel and not a stored byte. The same code change was measured at the previous
  PR #4424 head (PR #4774, 2026-10-06): tokens identical, TPS/TTFT inside the band. Per jhan's rule, a PR body reports
  the final head against the latest main only: say so if the proposal must note that these cells predate the fold.

## Files (all readable)
- pr4424-live-body.md: the LIVE PR #4424 description (CRLF line endings; 190 lines; line numbers as `tr -d '\r' | cat -n`).
- pr4812-body.md: the PR #4812 description (final; its wording of the fold was checked by a reviewer agent).
- fold.diff: `git diff 6b939d25d2 ba69cb513e`.
- Code at the new head: worktree /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K (checked out at
  ba69cb513e, branch jhan-amx-vnniK). READ ONLY. Never run git commands that change it.
- Earlier memory notes for jhan's description rules: /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/
  pr-description-no-history.md, vnni-k-terminology.md, flag-only-decision-changing-facts.md,
  pr-body-pending-measurement-subsection.md, no-names-in-github-issues.md, value-suffix-names-shared-files.md.

## Wording rules of this PR (jhan)
- "shared block save" (never "striped block store"); "save" = the operation, "store" = the CPU instruction.
- "main thread", "main helpers" as the body's Words table defines them. "worker index" for worker_ix in prose.
- Never name people. No clock times, no paths into the author's workspace, no comparison with an earlier head's
  assertion counts in the Test/Verification section.
- Keep the author's own sentences wherever the head keeps them true (change the minimum).
