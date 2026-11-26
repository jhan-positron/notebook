#!/usr/bin/env bash
# go2.sh - control for the rerun of 2026-11-17: the 120-thread line of r8.spec (like.spec), started from an idle machine, twice.
# Reason: in go.sh every bwx12 process started about 5 s after other 120-thread work. The earlier runs of this line
# (w120-R8 at 8000 MT/s, w120-w120-F72d12 at 7200 MT/s) started from an idle machine (1-minute load average 0.00 and 0.34).
# "Idle" here = 1-minute load average below 1.0. No root. CPUs 0-119 only. rx.sh stops if /tmp/positron-perf.RUNNING exists.
set -u
D=$HOME/cache-perf/w120-7200-20261117
RX=$HOME/cache-perf/w120-20261115/rx.sh
BW=$HOME/cache-perf/bwx12-20261115/bwx12
SHA=cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a
RXSHA=d315814fa650c53538af1d76df4f1f927ccb4b0c99dc45fd4cc1f4a94f590aab
BOOT=3bfc57a1-e235-4fe5-8c09-a94642f9b60b
state() { echo "== $1 utc $(date -u +%FT%TZ) boot $(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo | tr -s ' ') load $(cat /proc/loadavg) users $(who | wc -l) marker $([ -e /tmp/positron-perf.RUNNING ] && echo present || echo absent) processes per user: $(ps -eo user= | sort | uniq -c | tr -s ' ' | tr '\n' ';')"; }
fail() { echo "FAILED: $1"; state abort; exit 1; }
echo "go2.sh pid $$ (stop everything: kill -TERM -- -$$)"
[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"
exec 9> "$HOME/cache-perf/results/go-T72.lock"; flock -n 9 || fail "another go.sh holds the lock"
echo "$RXSHA  $RX" | sha256sum -c - > /dev/null || fail "rx.sh is not the script of 2026-11-15"
echo "$SHA  $BW" | sha256sum -c - > /dev/null || fail "bwx12 is not the binary of 2026-11-15"
[ -s "$D/like.spec" ] || fail "missing $D/like.spec"
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] || fail "boot id is not the boot checked at 12 modules, 7200 MT/s"
[ "$(awk '/^MemTotal/{print $2}' /proc/meminfo)" -ge 395000000 ] || fail "MemTotal below 395000000 kB: not 12 modules"
rxok() { local l; l=$(ls -d "$HOME"/cache-perf/results/w120-"$1"-*/launches.txt 2>/dev/null | tail -1); [ -n "$l" ] && [ "$(grep -c '^rc ' "$l")" = 1 ] && [ "$(grep -c '^rc 0 ' "$l")" = 1 ]; }
# wait until the 1-minute load average is below 1.0 (at most 15 min)
waitidle() { local i; for i in $(seq 180); do [ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"; awk '{exit !($1 < 1.0)}' /proc/loadavg && return 0; sleep 5; done; fail "1-minute load average not below 1.0 after 15 min"; }
state start
for i in 1 2; do
  waitidle
  state "idle before T72I$i"
  bash "$RX" T72I$i "$BW" "$SHA" < "$D/like.spec" || fail "rx.sh T72I$i rc $?"
  rxok T72I$i || fail "bwx12 T72I$i: exit status not 0 (launches.txt, stderr.txt)"
  state "after T72I$i"
done
state end
echo ALLDONE
