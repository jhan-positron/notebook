#!/usr/bin/env bash
# benstack-20261021 driver (runs ON delphi-3bda, detached): build the six trees (two at a time, -j18 each, our cpus,
# production serving left alone) and then run tests.sh. The three shas are the heads of the re-expressed branches
# jhan-vnnik-2-amx-5047 / -3-shared-save-5047 / -4-tail-block-5047 as committed in the shared repo (no push needed:
# /home/jhan/workspace/tron is the same repository on both hosts).
# Usage (on 3bda): SHA2=<40 hex> SHA3=<40 hex> SHA4=<40 hex> bash run-all.sh   [JOBS=18] [SKIP_BUILD=1]
# Log: exec/logs/benstack-20261021-run-all.log. Marker: exec/results/benstack-20261021/run-all.done = "ok" or "failed: <why>".
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
SHA2=${SHA2:?SHA2=<full sha of jhan-vnnik-2-amx-5047> is required}
SHA3=${SHA3:?SHA3=<full sha of jhan-vnnik-3-shared-save-5047> is required}
SHA4=${SHA4:?SHA4=<full sha of jhan-vnnik-4-tail-block-5047> is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=benstack-20261021
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-run-all.log
D=$EXEC/$NAME
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
mark() { echo "$1" >"$RES/run-all.done"; echo "=== run-all finished $(ts): $1 ==="; }
rm -f "$RES/run-all.done"
echo "=== run-all started $(ts) pid $$ on $(hostname) sha2=$SHA2 sha3=$SHA3 sha4=$SHA4 ==="
build() { TAG=$1 SHA=$2 VNNI=$3 JOBS=${JOBS:-18} bash "$D/build.sh"; }
if [ "${SKIP_BUILD:-0}" != 1 ]; then
  for pair in "bp2 $SHA2 OFF bp2v $SHA2 ON" "bp3 $SHA3 OFF bp3v $SHA3 ON" "bp4 $SHA4 OFF bp4v $SHA4 ON"; do
    set -- $pair
    echo "$(ts) building $1 and $4 ($2)"
    build "$1" "$2" "$3" & p1=$!
    build "$4" "$5" "$6" & p2=$!
    wait $p1; wait $p2
    echo "$(ts) build markers: $1=[$(cat "$RES/build-$1.done" 2>/dev/null)] $4=[$(cat "$RES/build-$4.done" 2>/dev/null)]"
  done
fi
fails=0
for tag in bp2 bp2v bp3 bp3v bp4 bp4v; do [ "$(cat "$RES/build-$tag.done" 2>/dev/null)" = ok ] || fails=$((fails + 1)); done
echo "$(ts) builds not ok: $fails of 6"
bash "$D/tests.sh"; trc=$?
echo "$(ts) tests.sh rc=$trc marker=[$(cat "$RES/tests.done" 2>/dev/null)]"
if [ "$fails" -eq 0 ] && [ "$trc" -eq 0 ]; then mark ok; else mark "failed: builds-not-ok=$fails tests=[$(cat "$RES/tests.done" 2>/dev/null)]"; fi
