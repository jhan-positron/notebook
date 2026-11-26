---
name: tron-precommit-hook-agentsrv
description: "On agentsrv the pre-commit hook of ~/workspace/tron exits 127 (lefthook path under /nix/store is missing), so commits from there skip all 13 lint checks unless the hook is repaired"
metadata:
  node_type: memory
  type: project
  originSessionId: 9e4b2a33-7940-4569-b4c2-5871971b6be0
  modified: 2026-11-23T00:15:30.029Z
---

Measured 2026-11-22 on agentsrv (claude-dev container):

- `~/workspace/tron/.git/hooks/pre-commit` is `exec /nix/store/s9v44368pp8gcdwx3jj9bnhgpkadiih4-lefthook/bin/lefthook run pre-commit "$@"`. `/nix/store` does not exist on agentsrv, so `sh pre-commit` prints "lefthook: not found" and exits 127.
- `core.hooksPath` is that folder, so every tron worktree uses the same hook.
- `lefthook`, `nix`, `clang-format`, `clang-tidy`, `ruff` are not on PATH there.
- A text search of the 150 Claude Code session logs changed in the prior 60 days found `git commit ... --no-verify` in 51 and the "lefthook: not found" error in 9.
- CI runs the same checks as the Nix check `lint-toolchain` (flake.nix), so from agentsrv the lint acts only after the push.

**Why:** a commit from agentsrv fails at the hook, and `--no-verify` skips whitespace, clang-format, no-cassert and the other lefthook commands without any message.

**How to apply:** when committing in a tron worktree on agentsrv, say in the report that the local pre-commit checks did not run, and do not present the commit as lint-clean. jhan had not decided on a repair as of 2026-11-22 (my interpretation: install lefthook 2.1.6, the version flake.nix pins, or add a Claude Code PostToolUse hook; both are described in [[lint-tla-lean-tron-page-2026-11-22]]). The hook file is on the NFS home, so hosts with Nix must keep working.
