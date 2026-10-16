---
name: workspace-ai-runs-layout
description: ~/workspace reorganized 2026-09-01 — agent-created folders live in ~/workspace/ai-runs/; never create new entries directly at ~/workspace
metadata:
  type: project
---

On 2026-09-01 the user reorganized /home/jhan/workspace: Claude-created entries moved into /home/jhan/workspace/ai-runs/. Moved: tron-fpgause, tron-kvprobe, tron-llama8b, tron-pfgate, tron-pr2934-reconciled, tron-router-p0, tron-wadefix, tron-wclsbypass, tron-wclsbypass-pr (git worktrees of ~/workspace/tron, relinked with `git worktree move`), llm_fpga, reviewers, alpha-build-scaffold, tron-build-fail-alpha.md. tron-dd and tron-fence-amx were moved on 2026-09-01 ~22:00Z by the AMX session (jhan request; exec/ scripts repointed). tron-amx (branch jhan-amx-p0, the PR #3879 tree) still sits at ~/workspace/tron-amx - jhan has not asked for it to move.

**Why:** the user wants their own folders separated from agent-created ones at the workspace top level.
**How to apply:** never create files or folders directly at /home/jhan/workspace — put new worktrees, clones, scratch dirs, and report files under /home/jhan/workspace/ai-runs/ (or inside an existing project folder). Absolute paths recorded before 2026-09-01 to the moved entries are stale; resolve them via ~/workspace/ai-runs/<name>.
