---
name: minor-design-readings-decide-not-ask
description: "User finds questions about small implementation readings over-cautious; decide, record, proceed"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 44fe6d73-add7-4628-9e21-cd5ce085d9ec
  modified: 2026-11-15T00:28:10.285Z
---

On 2026-11-14, after the bwx8 implementation of tackle-8mb.md, I listed five "decisions for you". The user approved only the real one (CRB login and runs) and said of the other four: "over cautious, no need of that". The four were: who reviews the runner before use, a listing-check exemption, a schedule balance reading, and a threshold I chose where the design was silent.

**Why:** these were choices I could make and record myself; asking delayed the work.

**How to apply:** ask the user only for authorization of shared-machine use or irreversible actions. For small readings of a design, pick one, record it in the decisions file, mention it in one line, and proceed. (The scope "small readings" is my interpretation.)
