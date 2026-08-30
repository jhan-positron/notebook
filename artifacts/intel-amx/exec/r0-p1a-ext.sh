#!/usr/bin/env bash
# P1a Phase M rep extension (pre-registered: extend to 6 reps/arm when CIs
# are too wide). Configs: u1/ctx8192 and u8/ctx2048 (upper CI >= +1% at n=3).
# Adds reps 7-12 in order on,off,off,on,on,off (3 more per arm).
# Marker values: ok / guard-stop / serving-busy / build-missing / check-output / aborted.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/router
LOG=$EXEC/logs/r0-p1a-ext.log
MARKER=$EXEC/logs/r0-p1a-ext.done
TRON=~/workspace/tron-router-p0
RES=$OUT/p1a-ab.txt
mkdir -p "$OUT" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== r0-p1a-ext start $(date -u +%FT%TZ) ==="
trap '[ -e "$MARKER" ] || { rm -f /dev/hugepages/amx-r1* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

source "$EXEC/lib-guard.sh"
[ -x "$TRON/gen/runtron" ] || { echo build-missing >"$MARKER"; exit 1; }
if ci_lease_busy; then echo guard-stop >"$MARKER"; exit 1; fi
if rinzler_active; then echo serving-busy >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-stop >"$MARKER"; exit 1; fi
cd "$TRON" || { campaign_guard_release; echo build-missing >"$MARKER"; exit 1; }

RTARGS="stream-generate-text -m ingested-gpt-oss-20b-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-r1 --nr_hugepages 128 -o"
FAIL=0
echo "# P1a rep extension $(date -u +%FT%TZ)" >>"$RES"
for cfg in "1 2048" "1 8192" "8 2048" "8 8192"; do
  set -- $cfg; U=$1; CTX=$2
  if ci_took_dut; then
    rm -f /dev/hugepages/amx-r1* 2>/dev/null; campaign_guard_release
    echo guard-stop >"$MARKER"; exit 1
  fi
  echo "--- ext reps u=$U ctx=$CTX $(date -u +%FT%TZ) ---"
  rep=6
  for arm in on off off on on off; do
    rep=$((rep+1))
    envs=(); [ "$arm" = on ] && envs=(TRON_CPU_ROUTER=1)
    F=$OUT/p1a-u$U-ctx$CTX-rep$rep-$arm.txt
    echo "+ env ${envs[*]:-<none>} timeout 1800 ./gen/runtron $RTARGS --prompt-length $CTX -l 256 -u $U"
    if env "${envs[@]}" timeout 1800 ./gen/runtron $RTARGS --prompt-length "$CTX" -l 256 -u "$U" >"$F" 2>&1; then
      line=$(grep -m1 'average tok/s' "$F" || true)
      echo "REP u=$U ctx=$CTX rep=$rep arm=$arm ${line:-NO-TIMING}" | tee -a "$RES"
    else
      echo "RUN-FAILED u=$U ctx=$CTX rep=$rep arm=$arm" | tee -a "$RES"; FAIL=1
    fi
  done
done
rm -f /dev/hugepages/amx-r1* 2>/dev/null
campaign_guard_release
if [ "$FAIL" -ne 0 ]; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== r0-p1a-ext done $(date -u +%FT%TZ) ==="
