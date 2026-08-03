#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 OUTPUT" >&2
  exit 2
fi

output=$1
exec > >(tee "$output") 2>&1

printf 'checked_utc=%s\n' "$(date -u +%FT%TZ)"
printf 'host=%s\n' "$(hostname)"
printf '\nlogin_sessions:\n'
w -h
printf '\nworkload_processes:\n'
pgrep -a -f '[r]untron|[b]enchmark_run.py|[r]un_suite.sh' || true
printf '\ntop_processes:\n'
ps -eo user,pid,etimes,pcpu,pmem,args --sort=-pcpu | head -20
printf '\naggregate_cpu:\n'
if command -v mpstat >/dev/null 2>&1; then
  mpstat 1 3
else
  top -bn2 -d1 | grep -E '^%Cpu' | tail -1
fi
printf '\nhugepages:\n'
grep -E '^HugePages_(Total|Free|Rsvd|Surp):' /proc/meminfo
