---
name: workflow-journal-reconstruction-trap
description: "2026-09-30: rebuilding Workflow results from journal.jsonl: ids like R1-N follow the SCRIPT's parallel() input order (LENSES array), not the journal's agent-start order; a big synthesis agent that re-emits ~100 findings hits the 64k output limit and loops; dedup agents must return id plans, not full findings"
metadata:
  node_type: memory
  type: feedback
  originSessionId: c1e2475d-c671-4e92-9fc3-579c9ced20ea
  modified: 2026-09-30T03:14:36.250Z
---

Facts learned during the PR 4596 review (session 2026-09-29/30, workflow wf_9d1f4e76-619):

- `parallel()` and `pipeline()` return results in INPUT order. The journal records agent starts in
  scheduling order, which differs. A reconstruction script that numbers raw findings by journal
  order attaches refuter votes and merge plans to the wrong findings. Validate a rebuild by
  reading each refuter's first user message (it embeds the finding JSON) and comparing titles.
- An agent asked to re-emit every finding in full (dedup returning full objects, or a synthesis
  over ~100 findings) exceeds the 64,000 output-token limit and then loops on "Output token limit
  hit" forever; the workflow never finishes. Make such agents return only ids and plans (merge
  groups, per-id triage rows) and do the joins in code. Split synthesis into 5-6 agents that read
  the data from files (pass file paths, not JSON, in the prompt).
- When an agent reads its inputs from files, changing the files does NOT invalidate the cache:
  a resume replays the old result. Launch a fresh run (no resumeFromRunId) after regenerating inputs.
- A background Agent whose build command ran with run_in_background ends its turn at the first
  "waiting for completion" and never resumes; the orchestrator must run the follow-up itself.

**Why:** these four cost about two hours of wall time in one session.
**How to apply:** for any review workflow, write the reconstruction script up front (script-order
ids), keep every agent's output under ~20k tokens, and pass file paths for large inputs.
