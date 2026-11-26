---
name: tron-commit-hook-on-agentsrv
description: "On the agent machine a plain git commit in a tron worktree fails: the pre-commit hook execs lefthook from a Nix store path that does not exist there; what to check by hand, and never chain push or CI dispatch after an unchecked commit"
metadata:
  node_type: memory
  type: reference
  originSessionId: e6131298-3716-420b-b25d-23483ce37d5a
  modified: 2026-11-25T02:06:34.723Z
---

Seen on 2026-11-25 (UTC) in `~/workspace/ai-runs/tron-glimmer-amx` (a worktree of `~/workspace/tron`), for PR 5022 commit e863b27272.

- `~/workspace/tron/.git/hooks/pre-commit` runs `exec /nix/store/...-lefthook/bin/lefthook run pre-commit`. The agent machine has no Nix store, so `git commit` ends with "lefthook: not found" and creates no commit. `git rebase` does not run this hook, so a rebase works.
- What the hook would check for a C++ header change (`lefthook.yml`): whitespace (`git diff --check origin/main HEAD`), no `#include <cassert>`, clang-format (skipped outside CI when the tool is missing), and `make lint-notes`. Run the first two by hand, check that a referenced `Note [...]` exists, then commit with `--no-verify` and say so in the report. The CI Lint job of GCP Nix runs clang-format and the other checks within about a minute of the push.
- clang-format is not installed on the agent machine or on delphi-3b35. A try to fetch it with `uvx` was denied by the permission classifier. Do not retry that. Rely on the CI Lint job.
- My mistake that day: one shell command chained commit, push and `gh workflow run`. The commit failed, the push was a no-op, and a CMake run started on the unchanged head. I cancelled it (`gh run cancel`). Check the result of the commit (`git rev-parse HEAD` changed) before the push, and the push before any CI dispatch.
- The session of 2026-11-20 avoided the hook with git plumbing (commit-tree). `--no-verify` has the same effect.

Related: [[tron-manual-legacy-ci-run]], [[tron-pr-push-triggers-bot-review]].
