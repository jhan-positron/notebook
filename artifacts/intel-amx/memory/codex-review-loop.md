---
name: codex-review-loop
description: How codex's PR #3879 review arrives and how jhan wants each finding handled (verify, fix, test, log to claude-report.md); codex's own checkout location
metadata:
  type: project
---

Since 2026-08-27 codex reviews tron PR #3879 continuously. Its findings are appended to
~/workspace/intel-AMX/PR3879-codex/review.md and review.html (one `### [Pn]` section each);
its draft failing tests live in its own checkout ~/workspace/intel-AMX/tron-pr3879-codex/
(uncommitted, e.g. t/t_llama_unit.cpp) - read them to align regression tests, never edit there.

jhan's standing instruction (2026-08-28): for each new codex issue, verify it; if you agree,
fix it, test it, add unit tests covering the gap, commit and push to jhan-amx-p0; queue anything
needing AMX hardware on delphi-3bda after CI (exec/p3-*.sh pattern); and log every issue's
verdict/fix/tests/verification in PR3879-codex/claude-report.md (one section per finding).

**Why:** the review is open-ended; the log is how jhan tracks what was accepted and shipped.
**How to apply:** keep a Monitor on PR3879-codex/review.md; one commit per finding, fix and
tests separated when the repo's small-commit style calls for it. Related:
[[claude-box-tron-build-env]], [[amx-tron-softattn-project]].
