---
name: agent-cpu-guard
description: "agentsrv: since 2026-11-20 every shell command of Claude Code and Codex is pinned to CPUs 26-31 (nproc=6) by ~/.config/agent-cpu-guard/guard.sh via BASH_ENV; how it loads, how to bypass for tests, what it does not cover, and the tmux-client burst found on the way"
metadata:
  node_type: memory
  type: project
  originSessionId: 7cfe37b4-21a7-4543-b6b6-92b7c8bbe48d
  modified: 2026-11-21T04:56:55.014Z
---

Installed 2026-11-20 (about 20:26 PST) after the throttling incident in
[[agentsrv-per-user-slice-caps]]. jhan asked for a fix that works for both
Claude Code and Codex.

What exists (all files, nothing has to keep running):
- `~/.config/agent-cpu-guard/guard.sh`: sourced through `BASH_ENV`. On
  HOSTNAME `agentsrv` or `claude-agentsrv` it runs `taskset -pc 26-31 $$` and
  exports `AGENT_CPU_GUARD=26-31` (the marker makes nested shells skip it).
  Any other host: no-op. It must print nothing and never fail.
- `~/.claude/settings.json`: `"env": {"BASH_ENV": "<guard>"}` (shared NFS home,
  so it is set on every host).
- `~/codex-home-claude-agentsrv/config.toml` and
  `~/codex-home-agentsrv/config.toml`: `[shell_environment_policy.set]`
  `BASH_ENV = "<guard>"`. The container one lives on the host disk in
  `/var/tmp/jhan/persist/codex-home` (mounted by claude-box).
- `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`: section "agentsrv and its
  claude-dev container" (size pools from nproc, do not widen the pin, report
  if nproc prints 32).
- Report with charts: `~/workspace/random/from-claude/agent-cpu-guard.html`;
  scripts and raw data in `from-claude/agent-cpu-guard-data/` (loadtest.py,
  burst_sampler.py, fill_report.py + report-template.html).

Why it works for both tools: both start each command as `/bin/bash -c ...`
(Codex inside bwrap; `codex exec` uses `-lc`), and bash reads BASH_ENV for
non-interactive shells. Observed on 2026-11-20: Claude Code 2.1.330 applies a
changed `env` in settings.json to already running sessions from their next
command; the running Codex daemon (app-server 0.167.2) applies config.toml to
new threads without a restart. Existing Codex threads were not observed.

Measured (36 busy processes, container cpu.pressure "full"): no pin 77.1%
stalled; pinned 2.7-6.3%; pinned after the tmux cleanup 0.01-0.65%. Width test
4/5/6/7 CPUs gave 1.84/2.25/2.72/3.81% (tmux bursts still present).

Second cause found: tmux ran `continuum_save.sh` (in status-right,
status-interval 5) once per attached client. 54 clients, all attached in
September and idle 53-69 days, cost 2.07 CPU-s every 5 s when idle and at
least 2.2 CPUs during a real batch. Detached with `tmux detach-client` on
2026-11-20 20:44 with jhan's approval (plain detach, no -P). `~/.tmux.conf` is
unchanged, so this can come back: check `tmux list-clients | wc -l`.

**Why:** agents size jobs from the 32 visible CPUs; the per-user quota is 8;
quota exhaustion pauses every process of the user. A shared pin is a hard
ceiling on the sum of all agent commands and needs no privileges (the
container cgroup tree is read-only and has no cpu controller).

**How to apply:**
- On agentsrv my own Bash commands are pinned. A test harness that must be
  unpinned needs `taskset -c 0-31 env -u AGENT_CPU_GUARD -u BASH_ENV <cmd>`.
  A nested `claude -p` or `codex exec` started from a guarded shell inherits
  the pin and the marker, so launch it the same way to test config pickup.
- `pgrep -f PATTERN` matches my own command line; anchor it (`'^sleep 13'`).
- The guard does nothing, silently, if the hostname changes, the machine has
  fewer than 32 CPUs, or a tool stops passing BASH_ENV. Check: `nproc` = 6.
- Not verified: host-side sessions on agentsrv (ssh from the container was
  denied by the auto-mode classifier), the host `nr_throttled` counter.
- jhan asked on 2026-11-20 whether the change survives a container or machine
  reboot. Say so up front for any install on these hosts (my reading: state
  persistence with each config change).
- The unpinned control run deliberately stalls every session of jhan; keep it
  to a few seconds and say so in the report.
