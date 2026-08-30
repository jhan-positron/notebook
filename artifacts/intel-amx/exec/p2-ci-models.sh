#!/usr/bin/env bash
# CI-model A/B round (jhan request 2026-08-21): of the nightly-CI model list,
# only mixtral-8x7b-instruct-v0.1-tp2 @8u is (a) served by the current AMX
# dispatch gate (head 128, kv_mul 4) and (b) not yet A/B-tested.
# Excluded: llama-3.2-3b (kv_mul 3), llama-3.3-70b tp2/tp4 (kv_mul 8),
# qwen-2.5-32b (kv_mul 5); llama-3.1-8b-tp2 already tested (t4-shapes).
# Runs after tonight's nightly: wait 09:30Z -> quiet check -> rinzler policy
# cleanup -> campaign guard -> 3-arm suite at 8 users, ctx 2048/8192, 3 reps.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/ci-models
OUT=$DIR/mixtral-ab.txt
LOG=$EXEC/logs/p2-ci-models.log
MARKER=$EXEC/logs/p2-ci-models.done
mkdir -p "$DIR"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p2-ci-models queued $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }

# Stage A: wait for 09:30Z, then for a quiet machine; rinzler policy cleanup.
while [ "$(hhmm)" -lt 930 ]; do sleep 300; done
echo "=== window reached $(date -u +%FT%TZ) ==="
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

# Stage B: cross-session campaign guard (lease + flock + no-runtron).
source "$EXEC/lib-guard.sh"
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi

cd ~/workspace/tron-amx
sha256sum gen/runtron.inc1b gen/runtron.inc3arena

RTARGS="stream-generate-text -m mixtral-8x7b-instruct-v0.1-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-cimodels --nr_hugepages 128 -o"
guard() { t=$(hhmm); [ "$t" -ge 2000 ] && [ "$t" -lt 2100 ]; }

{
  echo "# CI-model A/B: mixtral-8x7b-instruct-v0.1-tp2, 8 users, $(date -u +%FT%TZ)"
  echo "# arms: baseline = arena binary kill-switched (validated at clean speed),"
  echo "#       canonical = inc1b ON (the default-candidate build),"
  echo "#       mirror    = inc3arena ON (the opt-in build)"
  sha256sum gen/runtron.inc1b gen/runtron.inc3arena
  for arm in "runtron.inc3arena baseline TRON_AMX_DISABLE=1" \
             "runtron.inc1b canonical TRON_AMX_DISABLE=0" \
             "runtron.inc3arena mirror TRON_AMX_DISABLE=0"; do
    set -- $arm; bin=$1; name=$2; mode=$3
    for ctx in 2048 8192; do
      for rep in 1 2 3; do
        if guard; then echo GUARD-STOP; break 3; fi
        if ci_took_dut; then echo CI-TOOK-DUT; break 3; fi
        echo "### arm=$name ctx=$ctx len=256 users=8 rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 1800 ./gen/$bin $RTARGS \
          --prompt-length "$ctx" -l 256 -u 8 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
} >>"$OUT"

rm -f /dev/hugepages/amx-cimodels 2>/dev/null || true
echo ok >"$MARKER"
echo "=== done $(date -u +%FT%TZ) ==="
