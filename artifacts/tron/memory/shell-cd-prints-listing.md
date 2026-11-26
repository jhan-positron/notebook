---
name: shell-cd-prints-listing
description: "in jhan's shell a `cd DIR` inside a Bash tool command prints the listing of DIR; cd into /tmp floods the tool output"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 59c0ff77-e70e-4ae6-800a-130e4fcb789d
  modified: 2026-11-20T18:14:07.760Z
---

In this environment `cd DIR` in a Bash tool command prints a listing of DIR before the command's own output. On 2026-11-20 `cd /tmp && ...` put about 900 entries into the tool result.

**Why:** the listing uses context and hides the real output. My interpretation: a shell function from jhan's bashrc does it. I did not read the bashrc to confirm.

**How to apply:** use absolute paths and no `cd`. If `cd` is needed, write `cd DIR >/dev/null`. A `cd` inside a script file run by bash is not affected.
