#!/usr/bin/env bash
# benstack-20261021 per-branch driver (runs ON delphi-3bda, detached): build ONE re-expressed branch with the option OFF and
# ON (two builds at a time, -j18 each, our cpus, production serving left alone), then run tests.sh for its two tags.
# Used instead of run-all.sh when the branches become final one at a time (the PR 5047 chain owns the machine from
# 13:30 UTC, so each branch is gated as soon as it is ready).
# Usage (on 3bda): N=2|3|4 SHA=<full 40-hex sha of jhan-vnnik-N-...-5047> bash run-one.sh   [JOBS=18] [SKIP_BUILD=1]
# Log: exec/logs/benstack-20261021-run-one-bpN.log. Marker: exec/results/benstack-20261021/run-one-bpN.done = "ok" or "failed: <why>".
# tests.sh writes exec/results/benstack-20261021/tests.done and appends to tests.txt (one block per launch).
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
N=${N:?N=2|3|4 is required}
SHA=${SHA:?SHA=<full sha> is required}
case $N in 2|3|4) ;; *) echo "N must be 2, 3 or 4"; exit 1 ;; esac
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=benstack-20261021
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-run-one-bp$N.log
D=$EXEC/$NAME
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
mark() { echo "$1" >"$RES/run-one-bp$N.done"; echo "=== run-one bp$N finished $(ts): $1 ==="; }
rm -f "$RES/run-one-bp$N.done"
echo "=== run-one bp$N started $(ts) pid $$ on $(hostname) sha=$SHA ==="
build() { TAG=$1 SHA=$2 VNNI=$3 JOBS=${JOBS:-18} bash "$D/build.sh"; }
if [ "${SKIP_BUILD:-0}" != 1 ]; then
  echo "$(ts) building bp$N and bp${N}v ($SHA)"
  build "bp$N" "$SHA" OFF & p1=$!
  build "bp${N}v" "$SHA" ON & p2=$!
  wait $p1; wait $p2
  echo "$(ts) build markers: bp$N=[$(cat "$RES/build-bp$N.done" 2>/dev/null)] bp${N}v=[$(cat "$RES/build-bp${N}v.done" 2>/dev/null)]"
fi
fails=0
for tag in bp$N bp${N}v; do [ "$(cat "$RES/build-$tag.done" 2>/dev/null)" = ok ] || fails=$((fails + 1)); done
echo "$(ts) builds not ok: $fails of 2"
TAGS="bp$N bp${N}v" bash "$D/tests.sh"; trc=$?
echo "$(ts) tests.sh rc=$trc marker=[$(cat "$RES/tests.done" 2>/dev/null)]"
if [ "$fails" -eq 0 ] && [ "$trc" -eq 0 ]; then mark ok; else mark "failed: builds-not-ok=$fails tests=[$(cat "$RES/tests.done" 2>/dev/null)]"; fi
