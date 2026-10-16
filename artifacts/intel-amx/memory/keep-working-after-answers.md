---
name: keep-working-after-answers
description: User expects continuous autonomous progress - answer questions AND resume queued work in the same turn
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3a96feab-43b5-493a-97f2-e9a59a459e74
  modified: 2026-08-18T19:04:20.536Z
---

The user runs long autonomous work sessions and repeatedly asked "why are you stopped?" /
"are you stopped?" (2026-08-18/19, AMX project). Standing directive: "I will stop you if I
see need, just proceed."

**Why:** ending a turn after only answering a question wastes wall-clock time; the user
treats the task queue as always-on.

**How to apply:** when the user asks a question mid-project, answer it AND launch/continue
the next queued task in the same turn (background jobs where possible). End a turn idle only
when the queue is empty or blocked on the user. Also update the status HTML files at each
step ([[amx-tron-softattn-project]]).

**2026-08-19 reinforcement (user: "Why are you stopped? ... How many times do you need me to
remind you the CI time?")**: finishing a milestone is NOT a stopping point. During a free
machine window on delphi-3bda, immediately start the next queued task (QUEUE.md order) and
keep going until CI prep at 03:30 UTC - treat 03:30Z as the usable window end, not the 02:45Z
timer (user has said the full window is usable). Stop only when the queue is empty or the
window closes.
