#!/usr/bin/env bash
# run_kernels.sh - on CRB: build the old and the new bandwidth.c, print the
# machine code of the kernels, run the self-test, then time old and new.
# Usage: run_kernels.sh probe | all
#   probe: build, machine code and self-test only (no timing)
#   all:   probe, then the timed runs
# Writes only under $HOME/cache-perf. Uses CPUs 0-119 only. No sudo.
set -euo pipefail
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi
MODE=${1:-probe}
MARKER=/tmp/positron-perf.RUNNING
case $MODE in probe|all) ;; *) echo "usage: $0 probe|all" >&2; exit 2;; esac
check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }
check_marker
SRC=$(cd "$(dirname "$0")" && pwd)
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=$HOME/cache-perf/results/kernels-$TS
mkdir -p "$OUT"
CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11"
load() { cut -d' ' -f1-3 /proc/loadavg; }
{
  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(load) logins=$(who | wc -l) mode=$MODE"
  echo "## gcc=$(gcc --version | head -1)"
  echo "## CFLAGS=$CFLAGS"
  echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"
  echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu | head -6
} > "$OUT/probe.txt"
# old = the source before the change; new = the changed source
build() { gcc $CFLAGS "$@" 2>> "$OUT/build.txt" || { echo "build failed: $OUT/build.txt" >&2; cat "$OUT/build.txt" >&2; exit 5; }; }
: > "$OUT/build.txt"
build -o "$SRC/bw_old" "$SRC/bandwidth.orig.c"
build -o "$SRC/bw_new" "$SRC/bandwidth.c"
build -o "$SRC/selftest" "$SRC/selftest.c"
build -c -o "$SRC/probe.o" "$SRC/probe.c"
echo "## build output bytes: $(wc -c < "$OUT/build.txt")" >> "$OUT/probe.txt"
{
  echo "## sha256:"; (cd "$SRC" && sha256sum bandwidth.orig.c bandwidth.c selftest.c probe.c run_kernels.sh bw_old bw_new selftest)
  sha256sum "$HOME/cache-perf/bench/bandwidth.c"
  for b in bw_new bw_old; do
    for f in k_read k_write k_copy k_asmread k_asmwrite k_asmcopy; do
      echo "=== $b $f ==="
      objdump -d --no-show-raw-insn --disassemble=$f "$SRC/$b" | sed -n '/>:$/,/^$/p'
    done
  done
  for f in copy_barrier copy_plain copy_plain_norestrict; do
    echo "=== probe.o $f ==="
    objdump -d --no-show-raw-insn --disassemble=$f "$SRC/probe.o" | sed -n '/>:$/,/^$/p'
  done
  for b in latency homelat; do
    echo "=== bench/$b chase ==="
    objdump -d --no-show-raw-insn --disassemble=chase "$HOME/cache-perf/bench/$b" | sed -n '/>:$/,/^$/p' || echo "(not available)"
  done
} >> "$OUT/probe.txt"
check_marker
"$SRC/selftest" > "$OUT/selftest.txt" 2>&1 && echo "## selftest exit=0" >> "$OUT/probe.txt" || { echo "## selftest exit=$?" >> "$OUT/probe.txt"; echo "selftest failed" >&2; echo "$OUT"; exit 4; }
if [[ $MODE != all ]]; then echo "## load_after=$(load) utc=$(date -u +%FT%TZ)" >> "$OUT/probe.txt"; echo "$OUT"; exit 0; fi

# One process per (binary, kernel): no kernel is timed after another kernel
# in the same process. Round 2 reverses the order of binaries and kernels.
one() { # csv binary kernel threads cpus bytes round
  check_marker
  echo "-- binary $2 kernel $3 threads $4 cpus $5 bytes $6 round $7 load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T)" >> "$1"
  "$SRC/$2" --threads "$4" --cpus "$5" --bytes "$6" --kernel "$3" --reps 3 --min-ms 500 >> "$1"
}
K1="read write copy asmread asmwrite asmcopy"; K2="asmcopy asmwrite asmread copy write read"
for round in 1 2; do
  if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi
  for cpu in 0 2; do
    for bytes in 32K 1M 8M 1G; do
      for k in $KS; do for b in $BINS; do one "$OUT/one-thread.csv" $b $k 1 $cpu $bytes $round; done; done
    done
  done
done
echo "## one-thread done load=$(load) utc=$(date -u +%FT%TZ)" >> "$OUT/probe.txt"
for round in 1 2; do
  if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi
  for k in $KS; do for b in $BINS; do one "$OUT/threads120.csv" $b $k 120 0-119 256M $round; done; done
done
echo "## load_after=$(load) utc=$(date -u +%FT%TZ)" >> "$OUT/probe.txt"
echo "$OUT"
