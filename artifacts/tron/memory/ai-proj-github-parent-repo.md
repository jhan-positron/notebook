---
name: ai-proj-github-parent-repo
description: "ai-proj parent repository (GitHub jhan-positron/ai-proj, private) at ~/workspace/ai-proj; level-2 project directories, level-3 code repositories planned as submodules"
metadata:
  node_type: memory
  type: project
  originSessionId: b45687fe-2ac0-4f08-9c7a-a8dc5289437a
  modified: 2026-11-23T03:41:35.336Z
---

Created 2026-11-22 at jhan's request.

- GitHub: `jhan-positron/ai-proj`, private, branch `main`. Local clone: `~/workspace/ai-proj` (jhan named this top-level location, so it is a user-directed container under [[workspace-ai-runs-layout]]).
- Layout jhan described: level 1 `ai-proj`; level 2 one directory per project plus common tooling and lib; level 3 real code repositories. Everything stays under the `jhan-positron` user account, not a separate organization.
- First level-2 directory: `arm-crb/` (holds only `.gitkeep` so far).
- Plan I proposed and jhan accepted with "ok, please go ahead": add each level-3 repository as a git submodule under its level-2 directory, name it `ai-proj-<level 2>-<name>`, and tag it with topics. No submodule exists yet.
- The machine has no global git identity. The repo-local identity is `jhan` with the GitHub noreply address `277609589+jhan-positron@users.noreply.github.com` (my choice, to link commits to the account without publishing the work address).
