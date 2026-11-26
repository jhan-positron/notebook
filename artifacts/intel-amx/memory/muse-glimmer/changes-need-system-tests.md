---
name: changes-need-system-tests
description: "jhan 2026-11-19 - every change must run thorough system tests, a PR stays scoped to its stated purpose, and review replies do not promise tracking issues unless jhan says so"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6
  modified: 2026-11-20T01:41:54.869Z
---

jhan, 2026-11-19, deciding point D4 of the PR 5022 review response (reviewer Isaac asked to add kv_mul 8): "keep 8 out of this PR. All changes need to run thorough system tests, this PR is scoped to support the shape for Muse Glimmer. Do not mention we will file tracking issue." In the same message, about new tracking issues for other comments: "list them and let me review first."

**Why:** jhan's words give the reason: a change that has not run the system tests does not go in, and PR 5022 exists to support one shape.

**How to apply:**
- When a reviewer proposes widening a PR's scope, the default answer is to decline unless the system tests for the addition have run. Give that as the reason in the reply.
- Do not write "I will open a follow-up issue" in a reply draft on my own. List proposed new issues with a draft text and wait for jhan's review. Nothing gets filed before that.
- Not a blanket rule against small reviewer-suggested edits on a measured path. On 2026-11-19 I raised that the I5 and I6 edits of PR 5022 would land without a throughput number. jhan kept them: "yes, let us do this `the PR body will say that the benchmarks predate them`. Basically we take this small risk and will see the result from nightly CI." jhan also asked to run the pre-merge CI process first ([[tron-manual-legacy-ci-run]]). My reading: for a small edit jhan accepts the nightly systems test as the check, if the PR body states plainly what was not measured.
- jhan approved the one proposed follow-up issue for PR 5022 ("looks good", 2026-11-19). File it together with the review replies.
