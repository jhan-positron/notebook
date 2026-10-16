---
name: deleted-comments-stay-deleted
description: "When jhan deletes comment content (e.g. measurement rationale), do not restore a condensed version; answer reviewers on demand instead"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 96d03035-947f-47ab-b02f-d3c208a8e1ea
  modified: 2026-08-24T19:22:56.540Z
---

In the [[amx-tron-softattn-project]] PR 3879 review response (2026-08-24), jhan deleted the
measured-decision paragraph from Note [K mirror parallel arena] in kv_cache.hpp. I restored a
condensed version (numbers without the rampup citation) and flagged it. jhan removed it again:
"I deleted the measurement decision. If reviewers bring up question, we will answer. No need
to be proactive here."

**Why:** jhan treats a deletion in their working tree as a decision, not an accident; source
comments should stay minimal and reviewer questions get answered in the review thread, not
preempted in code.

**How to apply:** when jhan has deleted comment text, take the deletion at face value — clean
up whatever the review item requires (e.g. artifact references) but never reinstate deleted
content, condensed or otherwise. If I think the deletion loses something, say so in the chat
summary only.
