---
name: no-names-in-github-issues
description: "jhan 2026-09-09: GitHub issues Claude drafts for jhan must not @-mention or name any person; refer to people by role and cite reviews/comments by link only"
metadata:
  type: feedback
---

When drafting a GitHub issue (or similar public tracking text) for jhan, do not
@-mention anyone and do not use personal names (no "Wade", "Ben"). Refer to
people by role ("the approving reviewer", "the reviewer who asked for FUSE")
and cite their reviews or comments by link or id.

**Why:** jhan said on 2026-09-09, while the FUSE follow-up issue for PR #4267
was being drafted: "do not mention anyone at the issue writing". An @-mention
notifies the person; a name in a public issue also puts words in their mouth
without their say. Consistent with jhan's earlier choice to answer the FUSE
question in chat, not on the PR ([[wade-fuse-question-pr4267]]).

**How to apply:** before posting any issue or PR text, grep the body for "@"
and for teammate first names; replace with roles and links. Ask only if a role
description would be ambiguous.
