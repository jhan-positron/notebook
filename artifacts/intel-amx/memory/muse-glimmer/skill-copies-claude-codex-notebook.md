---
name: skill-copies-claude-codex-notebook
description: "jhan's personal skills exist in three places (~/.claude/skills, ~/.codex/skills shared by all codex-home-* links, notebook/artifacts/claude-skills); the Claude and Codex copies are kept byte-identical; descriptions must stay within 1,024 characters"
metadata:
  node_type: memory
  type: reference
  originSessionId: 68a7918d-f12e-464b-b249-eda4aaac93c7
  modified: 2026-11-20T04:14:06.427Z
---

jhan's personal skills live in three places (checked 2026-11-19):

- `~/.claude/skills/<name>/`: the copy Claude Code loads. It has no version control.
- `~/.codex/skills/<name>/`: the copy Codex loads. Every `~/codex-home-*/skills` is a symlink to it, so one folder serves all machines. `ben-review` and `inter-agent-review-loop` in the Claude folder are symlinks into it.
- `~/workspace/notebook/artifacts/claude-skills/` and `artifacts/codex-setup/skills/`: preserved snapshots in the notebook git repository ("Preserve artifact" commits). They are not live copies.

On 2026-11-19 the Claude and Codex copies of tron-code-review, cpp-coding-guide and the Wade skill were byte-identical before my edit (name case aside). The intel-AMX project memory `wade-code-review-skill` records for 2026-10-07: keep the two copies in sync and re-install to Codex after every Claude-side change. My reading: that sentence is an earlier session's rule, built on jhan's one-time request "Install the new version wade-code-review to codex skill". I followed it on 2026-11-19 after updating three skills and renaming Wade-code-review to folks-code-review (see [[isaac-reviews-are-agent-pipeline]] for the review those updates came from).

**How to apply:** after editing a skill under `~/.claude/skills`, compare it with `~/.codex/skills/<name>` (`diff -rq`), then re-install the copy and say so in the report. Back up first, because there is no git: the 2026-11-19 backup is `~/workspace/ai-runs/skills-backup-20261119/`. Keep each skill description within 1,024 characters: `python3 -m scripts.quick_validate <skill dir>` in the skill-creator folder rejects a longer one. Leave the notebook snapshots alone unless jhan asks for a new preservation batch.
