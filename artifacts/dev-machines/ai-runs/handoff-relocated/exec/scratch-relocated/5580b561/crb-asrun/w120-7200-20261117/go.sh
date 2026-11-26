#!/usr/bin/env bash
# go.sh - whole-chip rerun at 7200 MT/s. Three sessions. Each session runs, one after the other:
#   A: ra.sh            (the 120-thread part of the 2026-11-13 test, same binaries, whole-pass stop, 0.5 s)
#   L: rx.sh like.spec  (runner bwx12, common stop, 6 s, the 120-thread line of r8.spec unchanged)
#   C: rx.sh cfwd.spec or crev.spec (bwx12: old C read, new C read, asm read; session 2 in reverse order)
# After session 3 one more C process runs in reverse order (2 forward and 2 reverse processes in total).
# No root. CPUs 0-119 only. ra.sh and rx.sh stop if /tmp/positron-perf.RUNNING exists.
# 8000 MT/s baselines for the comparison: fixed list in baselines-and-rules.txt (same folder), fixed before this run.
set -u
D=$HOME/cache-perf/w120-7200-20261117
RX=$HOME/cache-perf/w120-20261115/rx.sh
BW=$HOME/cache-perf/bwx12-20261115/bwx12
SHA=cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a
RXSHA=d315814fa650c53538af1d76df4f1f927ccb4b0c99dc45fd4cc1f4a94f590aab
# The boot in which results/dimm7200-20261117/try6.txt recorded 12 modules at 7200 MT/s.
BOOT=3bfc57a1-e235-4fe5-8c09-a94642f9b60b
state() { echo "== $1 utc $(date -u +%FT%TZ) boot $(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo | tr -s ' ') load $(cat /proc/loadavg) users $(who | wc -l) marker $([ -e /tmp/positron-perf.RUNNING ] && echo present || echo absent) processes per user: $(ps -eo user= | sort | uniq -c | tr -s ' ' | tr '\n' ';')"; }
fail() { echo "FAILED: $1"; state abort; exit 1; }
echo "go.sh pid $$ (stop everything: kill -TERM -- -$$)"
[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"
exec 9> "$HOME/cache-perf/results/go-T72.lock"; flock -n 9 || fail "another go.sh holds the lock"
echo "$RXSHA  $RX" | sha256sum -c - > /dev/null || fail "rx.sh is not the script of 2026-11-15"
echo "$SHA  $BW" | sha256sum -c - > /dev/null || fail "bwx12 is not the binary of 2026-11-15"
for f in "$D/ra.sh" "$BW"; do [ -x "$f" ] || fail "not executable: $f"; done
for f in like cfwd crev; do [ -s "$D/$f.spec" ] || fail "missing $D/$f.spec"; done
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] || fail "boot id is not the boot checked at 12 modules, 7200 MT/s"
[ "$(awk '/^MemTotal/{print $2}' /proc/meminfo)" -ge 395000000 ] || fail "MemTotal below 395000000 kB: not 12 modules"
# rx.sh ends with status 0 also when bwx12 failed: it only writes "rc N tag" to launches.txt. Each spec file has one line, so exactly one "rc 0" line is required.
rxok() { local l; l=$(ls -d "$HOME"/cache-perf/results/w120-"$1"-*/launches.txt 2>/dev/null | tail -1); [ -n "$l" ] && [ "$(grep -c '^rc ' "$l")" = 1 ] && [ "$(grep -c '^rc 0 ' "$l")" = 1 ]; }
runx() { # name spec
  bash "$RX" "$1" "$BW" "$SHA" < "$2" || fail "rx.sh $1 rc $?"
  rxok "$1" || fail "bwx12 $1: exit status not 0 (launches.txt, stderr.txt)"
  state "after $1"
}
echo "== cmdline $(cat /proc/cmdline)"
echo "== governors of CPUs 0-119: $(for c in $(seq 0 119); do cat /sys/devices/system/cpu/cpu$c/cpufreq/scaling_governor; done | sort | uniq -c | tr -s ' ' | tr '\n' ';') cpu0 scaling_cur_freq $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)"
echo "== thp enabled $(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag $(cat /sys/kernel/mm/transparent_hugepage/defrag)"
echo "== affinity of this shell: $(taskset -cp $$)"
state start
for s in 1 2 3; do
  "$D/ra.sh" T72A$s || fail "ra.sh session $s rc $?"
  state "after T72A$s"
  runx T72L$s "$D/like.spec"
  if [ "$s" = 2 ]; then runx T72C$s "$D/crev.spec"; else runx T72C$s "$D/cfwd.spec"; fi
done
runx T72C4 "$D/crev.spec"
state end
echo ALLDONE
