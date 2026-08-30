#!/usr/bin/env bash
# P2 increment 1b: AMX PV (pv_128x4) added in the same apply_page_tok seam as
# the increment-1 QK. Build runtron + same-binary A/B (TRON_AMX_DISABLE=1 vs 0).
#
# Machine schedule (user-confirmed 2026-08-18; earlier note had it backwards):
#   nightly CI prep starts 03:30 UTC (20:30 PDT), normally done by 09:30 UTC.
#   ci-runner-stop@ timer fires 02:45 UTC ("stop runner + inference up") -
#   production inference may come up then. So this script runs IMMEDIATELY in
#   the evening-UTC free window and refuses to start any run at/after 02:00 UTC.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/p2-inc1b.txt
LOG=$EXEC/logs/p2-inc1b.log
MARKER=$EXEC/logs/p2-inc1b.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p2-inc1b start $(date -u +%FT%TZ) ==="

hhmm() { echo $((10#$(date -u +%H%M))); }
# Stop guard: no new run in [02:00, 21:00) UTC. Handles the midnight crossing:
# tonight's window is ~22:10 -> 02:00.
ci_guard() { t=$(hhmm); [ "$t" -ge 200 ] && [ "$t" -lt 2100 ]; }

if ci_guard; then
  echo "started outside the free window - refusing to run"
  echo guard-stop >"$MARKER"
  exit 1
fi

# Rinzler policy: stop lingering services only after a zero-traffic check.
active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null \
  | grep -c '^active') || true
if [ "${active:-0}" -gt 0 ]; then
  echo "rinzler active ($active of 4), running zero-traffic check"
  tries=0
  while [ "$tries" -lt 3 ]; do
    traffic=$(journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
      | grep -icE 'session|request|prompt|generate|token') || true
    if [ "${traffic:-0}" -eq 0 ]; then break; fi
    echo "journal shows activity ($traffic lines in 10 min), waiting 10 min"
    sleep 600
    tries=$((tries + 1))
  done
  if [ "$tries" -ge 3 ]; then
    echo "rinzler still serving after 3 checks - aborting, not touching it"
    echo rinzler-busy >"$MARKER"
    exit 1
  fi
  sudo systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3
  sleep 5
  if ! fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null; then
    rm -f /dev/hugepages/slice-*-of-8
    echo "hugepage slices removed (fuser: no open handles)"
  else
    echo "hugepage slices still have open handles - leaving them"
  fi
else
  echo "no rinzler services active"
fi

echo "=== build start $(date -u +%FT%TZ) ==="
cd ~/workspace/tron-amx
nix develop --command bash -c \
  'cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS= &&
   cmake --build gen --target runtron -j96' \
  || { echo build-failed >"$MARKER"; exit 1; }
sha256sum gen/runtron

RT="./gen/runtron stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-p2b --nr_hugepages 128 -o"
{
  echo "# P2 increment 1b (QK+PV on AMX) same-binary A/B, $(date -u +%FT%TZ)"
  sha256sum gen/runtron
  for mode in "TRON_AMX_DISABLE=1" "TRON_AMX_DISABLE=0"; do
    for w in "2048 256 1" "8192 256 1" "2048 256 8"; do
      set -- $w
      for rep in 1 2 3; do
        if ci_guard; then echo GUARD-STOP; break 3; fi
        echo "### mode=$mode ctx=$1 len=$2 users=$3 rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 900 $RT --prompt-length "$1" -l "$2" -u "$3" 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-p2b* 2>/dev/null
if grep -q GUARD-STOP "$OUT"; then
  echo guard-stop >"$MARKER"
else
  echo ok >"$MARKER"
fi
echo "=== p2-inc1b done $(date -u +%FT%TZ) ==="
