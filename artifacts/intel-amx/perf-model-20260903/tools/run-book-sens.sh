#!/usr/bin/env bash
# run-book-sens.sh - sensitivity run added after the campaign: Tron's book layout
# (pages adjacent within books of 24 pages, each book its own arena; found in
# kv_cache.hpp / full.hpp, book capacity 1600 tokens = 25 pages, 24 used with
# 128-token prompt chunks). Run ON delphi-3bda under the campaign guard.
set -u
EXEC=~/workspace/intel-AMX/exec
HERE=$EXEC/perf-model-20260903
SRC=$HERE/src
OUT=$EXEC/results/perf-model-20260903
BIN=/var/tmp/jhan/perf-model-bin
APP27="24-35,48-59,151-153"
LOG=$OUT/book-sens.log
. "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
echo "=== book sensitivity start $(date -u +%FT%TZ)"
ci_lease_busy && { echo "CI lease busy - not running"; exit 1; }
campaign_guard_acquire || { echo "guard refused"; exit 1; }
trap 'campaign_guard_release' EXIT
ok=0; for i in $(seq 1 24); do (cd "$SRC" && sha256sum -c --quiet SHA256SUMS >/dev/null 2>&1) && { ok=1; break; }; sleep 15; done
[ "$ok" = 1 ] || { echo "sources do not match SHA256SUMS"; exit 1; }
g++ -O3 -std=c++17 -march=x86-64-v4 -mavx512bf16 -mamx-tile -mamx-bf16 -pthread "$SRC/unit_bench.cpp" -o "$BIN/unit_bench" || { echo build-failed; exit 1; }
sha256sum "$BIN/unit_bench"
numactl --membind=0 "$BIN/unit_bench" --check --variant amx --pages 3 --threads 1 --cpus 24 --huge none | tail -1
run_ub() { local name=$1; shift; echo "## $name  $(date -u +%FT%TZ)"; numactl --membind=0 "$BIN/unit_bench" "$@" --cpus "$APP27" --json "$OUT/m3-$name.json" 2>&1 | tail -2; }
for rep in 1 2 3; do
  for v in avx amx; do
    run_ub "$v-p130-t27-book24-r$rep" --variant $v --pages 130 --threads 27 --passes 300 --warmup 20 --huge 1g --book-pages 24
    run_ub "$v-p130-t27-ctl-r$rep"    --variant $v --pages 130 --threads 27 --passes 300 --warmup 20 --huge 1g
  done
done
echo "=== book sensitivity done $(date -u +%FT%TZ)"
echo ok >"$OUT/book-sens.done"
