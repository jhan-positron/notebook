---
name: herdr-code-review-plugins
description: herdr has no built-in code review; community marketplace plugins herdr-reviewr (needs herdr >= 0.9.3) and herdr-hunk-diff (needs the hunk viewer) let a human review an agent's diff and send comments back; AI review stays in Claude Code skills. Checked 2026-11-08.
metadata:
  type: reference
---

herdr (terminal workspace manager for AI coding agents) ships no code-review feature. Its agent skill file only documents a workflow: start a second agent named "reviewer" in a sibling pane and prompt it to review the diff.

herdr has a plugin system (`herdr plugin install owner/repo`, manifest `herdr-plugin.toml`). Marketplace = GitHub topic `herdr-plugin`, index at https://herdr.dev/plugins (unreviewed community code).

Review plugins found 2026-11-08:
- persiyanov/herdr-reviewr: human reads agent diff in a pane, line comments go back to Claude Code/Codex/OpenCode/Pi. 975 stars, MIT, needs herdr >= 0.9.3.
- jhochenbaum/herdr-hunk-diff: same idea via the external `hunk` diff viewer. 150 stars, MIT, needs herdr >= 0.8.0 plus hunk installed.
- zhuravel/magnum: AI agents review GitHub PRs in herdr panes, judge agent, posts one GitHub review. macOS only (launchd daemon), 4 stars.

State on claude-agentsrv 2026-11-08: herdr 0.9.1 client and server, `herdr plugin list` empty. Latest stable was 0.9.5 (2026-10-14). `herdr update` needed before installing reviewr.

AI-driven review is a Claude Code concern, not herdr: built-in `/code-review`, `engineering:code-review` (synced engineering plugin), plus user skills tron-code-review, folks-code-review (named Wade-code-review until 2026-11-19), ben-review, positron-code-review.

Related: [[herdr-agentsrv-topology-2026-10-03]], [[herdr-pane-shell-dash-fix-2026-10-04]]

**Update 2026-11-09:** herdr-reviewr 0.52.1 (plugin id persiyanov.reviewr, commit aede179) installed on agentsrv from the NFS home, so sw-dev-01 sees it too. Needed `TAR_OPTIONS=--no-same-owner` in front of `herdr plugin install` (see [[agentsrv-container-single-uid-namespace]]). The claude-agentsrv server is on 0.9.5 since the live handoff. `plugin action list --plugin persiyanov.reviewr` shows close/open/toggle, and an unknown id gives an empty list, not an error.

**Update 2026-11-09 (verified):** reviewr pane opens and shows the uncommitted diff (tabs Changes/Files/PR, footer `? · tab diff · e edit file · z hide`). `herdr plugin action invoke` resolves to the FOCUSED workspace, not the calling shell; in a non-git dir it exits 1 with `reviewr: no repo to review` and `herdr plugin log list` shows it. Added `[[keys.command]] prefix+f -> plugin_action persiyanov.reviewr.toggle` to the shared ~/.config/herdr/config.toml (reload applied; key press itself not yet tested by jhan). `herdr integration install codex` done (v10 hook in ~/codex-home-claude-agentsrv, `[features] hooks = true`). `herdr integration install claude` was BLOCKED by the Claude Code auto-mode classifier (it edits ~/.claude/settings.json hooks); jhan must run it from a plain shell. Test workspace w1B `reviewr-test` at ~/workspace/ai-runs/reviewr-test-20261109 left open.

**Update 2026-11-09 09:55 PST:** jhan confirmed reviewr works. Two prefix+f presses logged two successful toggle actions. jhan ran `herdr integration install claude` from a plain shell at 09:53 (v11): settings.json gained one SessionStart hook (matcher ^(startup|resume|clear|compact|fork)$, command `bash ~/.claude/hooks/herdr-agent-state.sh session`, timeout 10 s). Both integrations report current. Backups of settings.json and the codex config.toml are in ~/workspace/ai-runs/herdr-backup-20261109/.
