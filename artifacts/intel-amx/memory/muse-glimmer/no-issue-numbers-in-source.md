---
name: no-issue-numbers-in-source
description: "jhan's rule - no issue or PR number in source code comments (2026-10-18, reaffirmed 2026-11-19); leave existing lines with issue links untouched"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6
  modified: 2026-11-20T01:41:49.066Z
---

jhan's rule, first stated on PR 5015 thread r4308443563 (2026-10-18): "Issue# should not appear in source code." Reaffirmed on 2026-11-19 for PR 5022 ("keep my rule") when reviewer Isaac suggested a header comment ending in "(#5021)". The same rule is also recorded in the memory folder of the parent project (`-home-jhan-workspace-intel-AMX`, file `no-issue-numbers-in-source.md`).

**Why:** jhan's stated reason is not recorded. My wording in the PR 5022 draft reply, which jhan accepted: a comment describes the design as it is, and a tracker link goes stale once the issue closes.

**How to apply:**
- Never put an issue number, PR number or tracker link into new source comment text. Link the issue from the PR body instead.
- My interpretation, applied on 2026-11-19 and not yet confirmed by jhan: do not reword an existing line that already carries an issue link (example: the `TODO(jhan)` line with the #3997 link in `src/tron/CMakeLists.txt`). Leave it byte-identical, so the PR adds no issue number and removes none.
- Scope, answered by jhan on 2026-11-19 for `README.ci.md`: "it is not source code, rule does not cover it". Documentation files may carry an issue link.
