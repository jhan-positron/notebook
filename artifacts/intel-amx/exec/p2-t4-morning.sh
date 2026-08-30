#!/usr/bin/env bash
# T4 first pass, self-serve (user authorization 2026-08-19: no Rhys coordination
# needed; after the nightly CI window - normally done by 09:30 UTC / 02:30 PDT -
# verify CI is done, clean leftover rinzlers per the standing policy, and use
# the machine).
# Stages: wait for 09:30Z -> verify quiet -> cleanup -> build clean baseline
# binary (all AMX flags OFF) -> 3-binary symmetric suite (36 runs) -> per-arm
# turbostat power capture at 8u/8K -> capacity probe (16/24 users at ctx 8192).
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/t4
OUT=$DIR/t4-suite.txt
LOG=$EXEC/logs/p2-t4-morning.log
MARKER=$EXEC/logs/p2-t4-morning.done
mkdir -p "$DIR"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== t4-morning queued $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }

# Stage A: wait for 09:30Z, then for a quiet machine (rinzler zero-traffic or
# inactive). Give up at 13:00Z.
while [ "$(hhmm)" -lt 930 ]; do sleep 300; done
echo "=== window reached $(date -u +%FT%TZ), checking for CI completion ==="
quiet=0
while [ "$(hhmm)" -lt 1300 ]; do
  active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null \
    | grep -c '^active') || true
  if [ "${active:-0}" -eq 0 ]; then quiet=1; break; fi
  traffic=$(journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
    | grep -icE 'session|request|prompt|generate|token') || true
  if [ "${traffic:-0}" -eq 0 ]; then
    echo "rinzlers active but zero traffic for 10 min - treating nightly as done"
    sudo systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3
    sleep 5
    if ! fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null; then
      rm -f /dev/hugepages/slice-*-of-8
      echo "hugepage slices removed (fuser: no open handles)"
    fi
    quiet=1; break
  fi
  echo "nightly still active ($traffic journal lines in 10 min), waiting"
  sleep 600
done
if [ "$quiet" != 1 ]; then echo nightly-never-quiet >"$MARKER"; exit 1; fi
echo "=== machine quiet $(date -u +%FT%TZ) ==="

cd ~/workspace/tron-amx
# Stage B: clean baseline binary - all AMX flags OFF (our worktree's AMX code
# is entirely flag-gated, so this build is functionally clean main; sha below).
nix develop --command bash -c \
  'cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=OFF -DTRON_AMX_K_MIRROR=OFF -DTRON_AMX_K_MIRROR_LAYOUT_ONLY=OFF -DCMAKE_CXX_FLAGS= &&
   cmake --build gen --target runtron -j96' \
  || { echo build-failed >"$MARKER"; exit 1; }
cp gen/runtron gen/runtron.clean
sha256sum gen/runtron.clean gen/runtron.inc1b gen/runtron.inc2mir

RTARGS="stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-t4 --nr_hugepages 128 -o"
guard() { t=$(hhmm); [ "$t" -ge 2000 ] && [ "$t" -lt 2100 ]; }

{
  echo "# T4 first pass: symmetric 3-binary suite, $(date -u +%FT%TZ)"
  sha256sum gen/runtron.clean gen/runtron.inc1b gen/runtron.inc2mir
  for arm in "runtron.clean clean TRON_AMX_DISABLE=1" \
             "runtron.inc1b canonical-amx TRON_AMX_DISABLE=0" \
             "runtron.inc2mir mirror-amx TRON_AMX_DISABLE=0"; do
    set -- $arm; bin=$1; name=$2; mode=$3
    for w in "2048 1" "8192 1" "2048 8" "8192 8"; do
      set -- $w; ctx=$1; users=$2
      for rep in 1 2 3; do
        if guard; then echo GUARD-STOP; break 3; fi
        echo "### arm=$name ctx=$ctx len=256 users=$users rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 900 ./gen/$bin $RTARGS \
          --prompt-length "$ctx" -l 256 -u "$users" 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
  # Stage E: per-arm package power + clock at 8u/8K (turbostat alongside one run)
  for arm in "runtron.clean clean TRON_AMX_DISABLE=1" \
             "runtron.inc1b canonical-amx TRON_AMX_DISABLE=0" \
             "runtron.inc2mir mirror-amx TRON_AMX_DISABLE=0"; do
    set -- $arm; bin=$1; name=$2; mode=$3
    if guard; then echo GUARD-STOP; break; fi
    echo "### power arm=$name ctx=8192 users=8"
    env USE_HW_ATTN=0 $mode timeout 900 ./gen/$bin $RTARGS \
      --prompt-length 8192 -l 512 -u 8 >"$DIR/power-$name.log" 2>&1 &
    rpid=$!
    sleep 45  # inside prefill/decode
    sudo -n turbostat --quiet --show Avg_MHz,Bzy_MHz,PkgWatt --interval 5 \
      --num_iterations 8 2>/dev/null | tail -20
    wait "$rpid" 2>/dev/null
    grep -m1 -E "average tok/s" "$DIR/power-$name.log" || echo NO-TIMING
  done
  # Stage F: capacity probe - user counts beyond the usual, full logs kept
  for arm in "runtron.inc1b canonical-amx" "runtron.inc2mir mirror-amx"; do
    set -- $arm; bin=$1; name=$2
    for users in 16 24; do
      if guard; then echo GUARD-STOP; break 2; fi
      echo "### capacity arm=$name ctx=8192 users=$users rep=1"
      env USE_HW_ATTN=0 TRON_AMX_DISABLE=0 timeout 1200 ./gen/$bin $RTARGS \
        --prompt-length 8192 -l 128 -u "$users" >"$DIR/cap-$name-u$users.log" 2>&1 \
        || echo "RUN-EXIT-NONZERO (see cap-$name-u$users.log)"
      grep -cE "average tok/s" "$DIR/cap-$name-u$users.log" || true
      grep -icE "fail|abort|cannot|out of" "$DIR/cap-$name-u$users.log" || true
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-t4* 2>/dev/null
if grep -q "GUARD-STOP\|RUN-FAILED" "$OUT"; then
  echo check-output >"$MARKER"
else
  echo ok >"$MARKER"
fi
echo "=== t4-morning done $(date -u +%FT%TZ) ==="
