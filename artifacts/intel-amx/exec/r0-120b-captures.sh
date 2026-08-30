#!/usr/bin/env bash
# R0 addendum 3: gpt-oss-120b decode captures. Runnability was verified in
# r0-campaign.sh (RUNNABLE: yes, 128 hugepages, tp2). The plan bars 20b->120b
# arithmetic scaling from deciding G0 for 120b - these captures measure it.
# Same configs as 20b: decode 1u/8u x 2K/8K, production attention mode.
# Marker values: ok / guard-stop / build-missing / check-output / aborted.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/router
LOG=$EXEC/logs/r0-120b-captures.log
MARKER=$EXEC/logs/r0-120b-captures.done
TRON=~/workspace/tron-router-p0
mkdir -p "$OUT" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== r0-120b-captures start $(date -u +%FT%TZ) ==="
trap '[ -e "$MARKER" ] || { rm -f /dev/hugepages/amx-r0* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

source "$EXEC/lib-guard.sh"
[ -x "$TRON/gen/runtron" ] || { echo "runtron missing"; echo build-missing >"$MARKER"; exit 1; }
sha256sum "$TRON/gen/runtron"
if ! campaign_guard_acquire; then echo guard-stop >"$MARKER"; exit 1; fi
cd "$TRON" || { campaign_guard_release; echo build-missing >"$MARKER"; exit 1; }

RTARGS="stream-generate-text -m ingested-gpt-oss-120b-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-r0 --nr_hugepages 128 -o"
CAP_FAIL=0
for cfg in "1 2048" "1 8192" "8 2048" "8 8192"; do
  set -- $cfg; U=$1; CTX=$2
  if ci_took_dut; then
    echo "CI took the DUT before u=$U ctx=$CTX"
    rm -f /dev/hugepages/amx-r0* 2>/dev/null; campaign_guard_release
    echo guard-stop >"$MARKER"; exit 1
  fi
  TRACE=$OUT/gptoss120b-u$U-ctx$CTX-hwattn.perfetto-trace
  echo "### 120b decode capture u=$U ctx=$CTX len=256 $(date -u +%FT%TZ)"
  echo "+ timeout 1800 ./gen/runtron $RTARGS --trace-gen $TRACE --prompt-length $CTX -l 256 -u $U"
  timeout 1800 ./gen/runtron $RTARGS --trace-gen "$TRACE" \
      --prompt-length "$CTX" -l 256 -u "$U" 2>&1 \
    | tee "$OUT/gptoss120b-u$U-ctx$CTX.txt" \
    | grep -E "Parsing the prompt took|average tok/s"
  PS=("${PIPESTATUS[@]}")
  if [ "${PS[0]}" -ne 0 ] || [ "${PS[1]}" -ne 0 ]; then
    echo "RUN-FAILED u=$U ctx=$CTX (runtron=${PS[0]} tee=${PS[1]}; 124 = timeout)"
    CAP_FAIL=1
  elif [ "${PS[2]}" -ne 0 ]; then
    echo "NO-TIMING u=$U ctx=$CTX"
  fi
done

rm -f /dev/hugepages/amx-r0* 2>/dev/null
campaign_guard_release
if [ "$CAP_FAIL" -ne 0 ]; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== r0-120b-captures done $(date -u +%FT%TZ) ==="
