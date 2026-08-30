#!/usr/bin/env bash
# R0 addendum 2: retake the P0a prefill capture. The campaign's --trace
# attempt produced a 773-byte file: the legacy whole-run tracer's 5 s
# duration cap (perf.cpp perfetto_duration_ms) expires during model load.
# Uses the patched runtron (TRON_TRACE_GEN_FROM_PARSE=1: phased trace starts
# at prompt-parse begin, no duration cap; commit on jhan-router-p0).
# Marker values: ok / guard-stop / build-missing / check-output / aborted.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/router
LOG=$EXEC/logs/r0-prefill-retake.log
MARKER=$EXEC/logs/r0-prefill-retake.done
TRON=~/workspace/tron-router-p0
mkdir -p "$OUT" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== r0-prefill-retake start $(date -u +%FT%TZ) ==="
trap '[ -e "$MARKER" ] || { rm -f /dev/hugepages/amx-r0* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

source "$EXEC/lib-guard.sh"
[ -x "$TRON/gen/runtron" ] || { echo "runtron missing"; echo build-missing >"$MARKER"; exit 1; }
sha256sum "$TRON/gen/runtron"
if ! campaign_guard_acquire; then echo guard-stop >"$MARKER"; exit 1; fi

cd "$TRON" || { campaign_guard_release; echo build-missing >"$MARKER"; exit 1; }
RTARGS="stream-generate-text -m ingested-gpt-oss-20b-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-r0 --nr_hugepages 128 -o"
TRACE=$OUT/gptoss20b-prefill8k-parse.perfetto-trace
echo "+ TRON_TRACE_GEN_FROM_PARSE=1 timeout 900 ./gen/runtron $RTARGS --trace-gen $TRACE --prompt-length 8192 -l 8 -u 1"
FAIL=0
TRON_TRACE_GEN_FROM_PARSE=1 timeout 900 ./gen/runtron $RTARGS \
    --trace-gen "$TRACE" --prompt-length 8192 -l 8 -u 1 2>&1 \
  | tee "$OUT/gptoss20b-prefill8k-parse.txt" \
  | grep -E "Parsing the prompt took|average tok/s"
PS=("${PIPESTATUS[@]}")
if [ "${PS[0]}" -ne 0 ] || [ "${PS[1]}" -ne 0 ]; then
  echo "RUN-FAILED prefill retake (runtron=${PS[0]} tee=${PS[1]}; 124 = timeout)"
  FAIL=1
fi
# The point of the retake is a non-empty prefill trace - verify size.
sz=$(stat -c %s "$TRACE" 2>/dev/null || echo 0)
echo "trace size: $sz bytes"
[ "$sz" -ge 10000000 ] || { echo "trace too small ($sz B < 10 MB) - prefill still not captured"; FAIL=1; }

rm -f /dev/hugepages/amx-r0* 2>/dev/null
campaign_guard_release
if [ "$FAIL" -ne 0 ]; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== r0-prefill-retake done $(date -u +%FT%TZ) ==="
