---
name: peer-fyi-notes-trigger-code-changes
description: "A note sent to a peer Claude session is acted on at once (2026-11-19: a code edit 37 s after my FYI); report code observations to jhan first, and write 'no code change' in any note that mentions code"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 68a7918d-f12e-464b-b249-eda4aaac93c7
  modified: 2026-11-20T14:26:32.574Z
---

On 2026-11-19 at 20:14:17 PST I sent the peer session muse-glimmer-b2 an FYI whose first line ended "No reply needed". One part was my own observation: its I6 edit for PR 5022 passed bare `true, false` as template arguments of `tron::const_view`, and the cpp-coding-guide asks for named bools there. The peer changed `h/tron/models/self_attention.hpp:1796` to `VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE` at 20:14:54 PST, 37 seconds later, and carried the change into `respond-2-Isaac.html`. The hash of that tree was test evidence.

jhan, 2026-11-20, after reading my report of the observation: "Let's not bother this. Please inform peer session not to make more code changes because of this".

**Why (my reading, not jhan's words):** jhan had not asked for the note. A style point on a PR in a review round was not worth a code change. An idle peer session starts a turn when a message arrives, and it treats an observation as work to do.

**How to apply:**
- Report a code observation about another session's work to jhan first. Send it to the peer only when jhan asks.
- Keep a note to a peer to the fact it needs (a rename, a moved file). If the note must mention code, write "do not change code for this" in it.
- Read a peer's tree again just before describing it to jhan. My report of 2026-11-20 still described the bare form, although the peer had changed the line the evening before.

Related: [[changes-need-system-tests]], [[review-replies-keep-simple]], [[isaac-reviews-are-agent-pipeline]].
