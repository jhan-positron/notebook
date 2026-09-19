---
name: pr4424-description-on-github
description: "2026-09-15: the VNNI-K PR is positron-ai/tron #4424 (branch jhan-amx-vnniK, base MAIN since 2026-09-16 00:0x UTC, was jhan-amx-p0); its description is edited by jhan ON GITHUB, so 'update the PR description' means gh api PATCH on the PR body, not the local draft status/pr-body-draft.md"
metadata:
  type: project
---

The VNNI-K work is PR #4424 in positron-ai/tron (branch jhan-amx-vnniK, base
main since the 2026-09-15 rebase; it was jhan-amx-p0 until PR #3879 merged).
The 2026-09-15/16 rebase body (status/main-rebase-20260915/pr-body.final.md) has a
"Rebase notes" and a "Rebase verification" subsection under Status and the open item
"Repeat the measurements against a main binary"; GitHub head ff680c8020 since 2026-09-16 00:4x UTC.
On 2026-09-16 (~01:00 UTC) jhan DELETED the whole "## Status" section (rebase notes +
rebase verification) from the body and renamed "Cells (...)" to "Test (...)"; do not
reinstate it (see [[deleted-comments-stay-deleted]]). The token-divergence bullet was
rewritten at jhan's request to quote Note [AMX attention dispatch] and cite the two
tests (t_k_vnni_layout reader-vs-dotter envelope 1e-4, t_amx_numerics bit-identity);
current body = status/main-rebase-20260915/pr-body.final5.md (2026-09-16 01:xx UTC: benchmark item rewritten, kill-switch/divergence item added, issue #4444). jhan edits the PR description directly on GitHub (CRLF line
endings, 2026-09-15 removed the "Commits, in order" section there).

**Why:** on 2026-09-15 I edited the local draft
VNNIed-K-in-place/status/pr-body-draft.md and jhan said "I do not see PR
description change" and gave the PR link. The draft is stale and not the
source of truth.

**How to apply:** for any PR-description edit, fetch the body byte-exactly
(`gh api repos/positron-ai/tron/pulls/4424`, write d['body'] in binary), apply
the change, print the line diff, PATCH with `gh api -X PATCH ... --input
payload.json`, re-fetch and compare. Keep CRLF in the payload; note (2026-09-16) that the REST PATCH stores the body with LF
only (a re-fetch showed 0 CR), so compare bodies after normalizing line endings, never
byte-exactly, or a benign mismatch will block the next PATCH. Update the title too when it
carries the same term. See [[vnni-k-terminology]] and
[[vnnied-k-in-place-project]].
