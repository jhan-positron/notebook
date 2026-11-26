---
name: herdr-restart-restore-agentsrv
description: On claude-agentsrv a herdr server restart restores layout only; agent conversations do not auto-resume because the Claude Code and Codex herdr integrations are not installed and session.json has no session ids. Use `herdr update --handoff` (live handoff) to upgrade without killing panes. Facts gathered 2026-11-08 for the 0.9.1 -> 0.9.5 upgrade.
metadata:
  type: project
---

herdr (terminal workspace manager) named session `claude-agentsrv`, server pid 484465 started 2026-10-03, version 0.9.1, 14 workspaces / 28 tabs / 31 panes, 25 agent panes (20 claude, 5 codex) on 2026-11-08.

What a restart does (herdr docs, session-state page, verified against local state):
- Layout, cwd, focus come back from `~/.config/herdr/sessions/claude-agentsrv/session.json` (schema v3).
- Processes end. Pane screen history is off (`experimental.pane_history = false`).
- Agent auto-resume needs official integrations (`herdr integration status`: all "not installed") and session refs in session.json (none found: zero keys containing session/agent/resume). So agents come back as empty shells; recover by hand with `claude --resume` / `codex resume` in each pane's saved cwd.

Live handoff (`herdr update --handoff`, or `herdr server live-handoff --import-exe <bin> --expected-version V --expected-protocol N`): transfers PTYs and processes to the new server. Experimental. Conditions checked 2026-11-08: private protocol 22 on 0.9.1 and 0.9.5; 31 panes < old-server 64-pane limit; server not under systemd (issue #4972 kills panes only under systemd); API listener healthy (issue #4601 fixed in 0.9.2 only matters if CLI is already unreachable). Known after-effect: stale Kitty keyboard flags in some panes (#5291); fix by restarting the app in that pane or sending `CSI = 0 u`.

Claude Code sessions run INSIDE panes of this server (this session was w14:p1), so any restart or handoff includes the session doing the work.

Backup of session.json + config.toml taken 2026-11-08 to the session scratchpad `herdr-backup-20261108/`.

**Why:** the user asked whether spaces/agents/panes survive a herdr update + restart before installing herdr-reviewr (needs herdr >= 0.9.3).
**How to apply:** prefer `herdr update --handoff` over `herdr session stop`; before any restart, install `herdr integration install claude` and `codex` so NEW agent sessions report resume ids (already-running sessions do not). Related: [[herdr-code-review-plugins]], [[herdr-agentsrv-topology-2026-10-03]].

Update 2026-11-08 12:49 PST: jhan ran `herdr update --handoff` on sw-dev-01 (bash history, shared NFS). That wrote `~/.local/bin/herdr` 0.9.5 for every machine (shared home), but the agentsrv server stayed 0.9.1 (`server_binary_stale: yes`); the handoff only targeted sw-dev-01's session. Remaining step for agentsrv: `herdr --session claude-agentsrv server live-handoff --import-exe ~/.local/bin/herdr --expected-version 0.9.5 --expected-protocol 22` from a shell outside any pane. Guide written for jhan: `~/workspace/random/from-claude/install-herdr-reviewr.md`. CLI commands from a shell outside a pane need `--session claude-agentsrv`, otherwise they hit the empty default session.

**Update 2026-11-09:** live handoff ran at 08:55:28 PST (new server pid 1497791, `--handoff-import` from 484465) and imported exactly 1 pane [session server log `handoff import ready panes=1`]; that pane shell survived (reparented to pid 1). The 29 panes / 23 agent panes counted on 2026-11-08 are UNRECONCILED: step 2 backup session.json (08:45 PST) had 1 pane, no pane-exit log lines after 2026-10-23, and the only other agents in the container are 4 claude + 1 codex under tmux (pid 274). Hypotheses: a host-side server answered on the shared NFS socket path (see [[herdr-agentsrv-topology-2026-10-03]]) or panes were closed unlogged. Resolve with jhan's own step 2 numbers and `herdr status`/`pane list` on the agentsrv host outside the container.

**Resolved 2026-11-09:** jhan confirmed they closed many panes between the 11-08 count (29 panes / 23 agents) and the handoff. The 0.9.1 session server log recorded none of those closes (no pane-exit lines after 10-23), so that log is not a record of pane closes.
