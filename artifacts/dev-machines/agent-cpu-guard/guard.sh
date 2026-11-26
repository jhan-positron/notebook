# agent-cpu-guard: keeps the shell commands of coding agents inside the
# per-user CPU quota of a shared host.
#
# How it gets loaded
#   Claude Code and Codex start every shell command as `/bin/bash -c ...`.
#   Both tools set BASH_ENV to this file:
#     ~/.claude/settings.json   "env": { "BASH_ENV": "<this file>" }
#     $CODEX_HOME/config.toml   [shell_environment_policy] set = { BASH_ENV = "<this file>" }
#   bash reads the file named by BASH_ENV before each non-interactive command.
#   Interactive shells and /bin/sh do not read it.
#
# What it does
#   On a host listed below, it pins the shell to a fixed CPU list. Child
#   processes inherit the pin, and `nproc` reports the pinned count.
#
# Why
#   agentsrv allows each user 8 CPUs (systemd CPUQuota=800%), but programs
#   see 32. When a wide batch uses up the quota, the kernel pauses every
#   process of the user, the agents included. All agent commands share the
#   same 6 CPUs here, so together they cannot use more than 6.
#   Measurements: ~/workspace/random/from-claude/agent-cpu-guard.html
#
# Rules for this file
#   Print nothing. Never fail. Stay fast. It runs before every command.
#
# Run one command on all CPUs:   taskset -c 0-31 <command>
# Switch the guard off:          remove BASH_ENV from the two config files
#                                above, or delete the host line below.

# An outer shell already pinned this process tree. Do not pin again, so
# that a deliberate `taskset -c 0-31 bash script.sh` stays wide.
[ -n "${AGENT_CPU_GUARD:-}" ] && return 0

case "${HOSTNAME:-}" in
  # The host and its claude-dev container share one quota, so they share
  # one CPU list.
  agentsrv|claude-agentsrv) _acg_cpus=26-31 ;;
  *) return 0 ;;
esac

if taskset -pc "$_acg_cpus" $$ >/dev/null 2>&1; then
  export AGENT_CPU_GUARD=$_acg_cpus
fi
unset _acg_cpus
return 0
