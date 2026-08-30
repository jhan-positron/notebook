#!/usr/bin/env bash
# P2 increment 2 SMOKE: build with TRON_AMX_K_MIRROR=ON and run a short A/B.
# Full 18-run suite runs in the next free window; tonight verifies: it builds,
# it runs end to end (a mirror indexing bug would trip the NaN m_star assert
# or produce garbage), first-cut decode/prefill numbers, and a deterministic
# token canary. Guard: no new run at/after 01:45 UTC (inference-up timer 02:45,
# CI prep 03:30).
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/p2-inc2-smoke.txt
DIR=$EXEC/results/slot1/inc2-smoke-logs
LOG=$EXEC/logs/p2-inc2-smoke.log
MARKER=$EXEC/logs/p2-inc2-smoke.done
mkdir -p "$DIR"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p2-inc2-smoke start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
ci_guard() { t=$(hhmm); [ "$t" -ge 145 ] && [ "$t" -lt 2100 ]; }

cd ~/workspace/tron-amx
# Preserve the inc-1b binary before reconfiguring gen/ with the mirror flag.
[ -f gen/runtron.inc1b ] || cp gen/runtron gen/runtron.inc1b
nix develop --command bash -c \
  'cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON -DCMAKE_CXX_FLAGS= &&
   cmake --build gen --target runtron -j96' \
  || { echo build-failed >"$MARKER"; exit 1; }
sha256sum gen/runtron gen/runtron.inc1b

RT="./gen/runtron stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-p2c --nr_hugepages 128 -o"
{
  echo "# P2 increment 2 (K mirror) SMOKE, $(date -u +%FT%TZ)"
  sha256sum gen/runtron
  for mode in "TRON_AMX_DISABLE=1" "TRON_AMX_DISABLE=0"; do
    for ctx in 2048 8192; do
      if ci_guard; then echo GUARD-STOP; break 2; fi
      echo "### mode=$mode ctx=$ctx len=256 users=1 rep=1"
      env USE_HW_ATTN=0 $mode timeout 900 $RT --prompt-length "$ctx" -l 256 -u 1 \
        >"$DIR/$mode-$ctx.log" 2>&1 || echo RUN-FAILED
      grep -E "Parsing the prompt took|average tok/s" "$DIR/$mode-$ctx.log" || echo NO-TIMING-LINES
    done
  done
  # Deterministic token canary: mirror QK changes the reduction topology, so
  # tokens may differ from the canonical-K run - record, do not judge.
  if ! ci_guard; then
    echo "### canary: greedy deterministic, ctx=2048, AMX ON (mirror)"
    env USE_HW_ATTN=0 TRON_AMX_DISABLE=0 timeout 900 $RT --prompt-length 2048 -l 256 -u 1 \
      --temperature 0 -s 42 --pay-for-determinism >"$DIR/canary-2048.log" 2>&1 || echo RUN-FAILED
    grep -cE "average tok/s" "$DIR/canary-2048.log"
  fi
} >"$OUT"
rm -f /dev/hugepages/amx-p2c* 2>/dev/null
grep -q "RUN-FAILED\|GUARD-STOP\|NO-TIMING-LINES" "$OUT" && echo check-output >"$MARKER" || echo ok >"$MARKER"
echo "=== p2-inc2-smoke done $(date -u +%FT%TZ) ==="
