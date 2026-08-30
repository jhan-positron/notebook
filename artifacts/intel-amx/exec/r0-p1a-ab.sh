#!/usr/bin/env bash
# P1a Phase M: same-binary A/B of TRON_CPU_ROUTER off (FPGA router baseline)
# vs on (host CPU router), per exec/results/router/P1A-preregistration.md.
# Spike binary: tron-router-p0 runtron with the hand-edited 20b header.
# Sequence per config: smoke+numerics (both arms, token comparison), then
# tok/s reps in the pre-registered order off,on,on,off,off,on (3 per arm;
# extension to 6 is a separate rerun decision), then one traced rep per arm.
# Marker values: ok / guard-stop / serving-busy / build-missing / check-output / aborted.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/router
LOG=$EXEC/logs/r0-p1a-ab.log
MARKER=$EXEC/logs/r0-p1a-ab.done
TRON=~/workspace/tron-router-p0
RT=$TRON/gen/runtron
mkdir -p "$OUT" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== r0-p1a-ab start $(date -u +%FT%TZ) ==="
trap '[ -e "$MARKER" ] || { rm -f /dev/hugepages/amx-r1* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

source "$EXEC/lib-guard.sh"
[ -x "$RT" ] || { echo "runtron missing"; echo build-missing >"$MARKER"; exit 1; }
[ "$(cat "$EXEC/logs/r0-build.done" 2>/dev/null)" = ok ] \
  || { echo "r0-build.done != ok"; echo build-missing >"$MARKER"; exit 1; }
# The binary must carry the spike branch: the marker string must be in the header
grep -q 'SPIKE ARTIFACT' "$TRON/gen/src/tron/h/tron/plugins/ingested_gpt_oss_20b.hpp" \
  || { echo "spike marker missing from header - wrong tree state"; echo build-missing >"$MARKER"; exit 1; }
echo "host=$(hostname) date=$(date -u +%FT%TZ) HEAD=$(git -C "$TRON" rev-parse HEAD)"
sha256sum "$RT"
if ci_lease_busy; then echo "CI holds the DUT"; echo guard-stop >"$MARKER"; exit 1; fi
if rinzler_active; then echo "serving active - this campaign does not stop serving"; echo serving-busy >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-stop >"$MARKER"; exit 1; fi

cd "$TRON" || { campaign_guard_release; echo build-missing >"$MARKER"; exit 1; }
RTARGS="stream-generate-text -m ingested-gpt-oss-20b-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-r1 --nr_hugepages 128 -o"
FAIL=0
RES=$OUT/p1a-ab.txt
echo "# P1a A/B $(date -u +%FT%TZ) binary=$(sha256sum "$RT" | cut -c1-16)" >>"$RES"

run_one() { # $1=arm(off|on) $2=U $3=CTX $4=len $5=outfile $6=extra-args
  local envs=()
  [ "$1" = on ] && envs=(TRON_CPU_ROUTER=1)
  echo "+ env ${envs[*]:-<none>} timeout 1800 ./gen/runtron $RTARGS $6 --prompt-length $3 -l $4 -u $2"
  env "${envs[@]}" timeout 1800 ./gen/runtron $RTARGS $6 --prompt-length "$3" -l "$4" -u "$2" \
    >"$5" 2>&1
  return $?
}

# --- numerics smoke: identical run, both arms, token-text comparison ----------
echo "--- numerics smoke $(date -u +%FT%TZ) ---"
for arm in off on; do
  if ! run_one $arm 1 2048 32 "$OUT/p1a-smoke-$arm.txt" ""; then
    echo "RUN-FAILED smoke arm=$arm"; tail -25 "$OUT/p1a-smoke-$arm.txt"
    rm -f /dev/hugepages/amx-r1* 2>/dev/null; campaign_guard_release
    echo check-output >"$MARKER"; exit 1
  fi
done
# strip the [timestamp|thread|cpu] prefixes, keep content lines, diff
norm() { sed -E 's/^\[[0-9:.]+\|thread [0-9]+\|cpu [0-9]+\] //' "$1" \
  | grep -vE 'took|tok/s|ms/tok|Parsing'; }
if diff <(norm "$OUT/p1a-smoke-off.txt") <(norm "$OUT/p1a-smoke-on.txt") \
     >"$OUT/p1a-numerics-diff.txt" 2>&1; then
  echo "NUMERICS: token output identical between arms"
  echo "identical" >"$OUT/p1a-numerics-verdict.txt"
else
  echo "NUMERICS: DIVERGENCE recorded (see p1a-numerics-diff.txt) - tok/s still measured, claim gated on investigation"
  echo "divergence" >"$OUT/p1a-numerics-verdict.txt"
fi

# --- tok/s reps: pre-registered order off,on,on,off,off,on per config ---------
for cfg in "1 2048" "1 8192" "8 2048" "8 8192"; do
  set -- $cfg; U=$1; CTX=$2
  if ci_took_dut; then
    echo "CI took the DUT at u=$U ctx=$CTX"
    rm -f /dev/hugepages/amx-r1* 2>/dev/null; campaign_guard_release
    echo guard-stop >"$MARKER"; exit 1
  fi
  echo "--- reps u=$U ctx=$CTX $(date -u +%FT%TZ) ---"
  rep=0
  for arm in off on on off off on; do
    rep=$((rep+1))
    F=$OUT/p1a-u$U-ctx$CTX-rep$rep-$arm.txt
    if run_one $arm "$U" "$CTX" 256 "$F" ""; then
      line=$(grep -m1 'average tok/s' "$F" || true)
      echo "REP u=$U ctx=$CTX rep=$rep arm=$arm ${line:-NO-TIMING}" | tee -a "$RES"
    else
      echo "RUN-FAILED u=$U ctx=$CTX rep=$rep arm=$arm" | tee -a "$RES"; FAIL=1
    fi
  done
done

# --- one traced rep per config per arm (boundary attribution) -----------------
for cfg in "1 2048" "8 2048"; do   # traces for the two primary-context cells
  set -- $cfg; U=$1; CTX=$2
  if ci_took_dut; then
    echo "CI took the DUT before traced reps u=$U"
    rm -f /dev/hugepages/amx-r1* 2>/dev/null; campaign_guard_release
    echo guard-stop >"$MARKER"; exit 1
  fi
  for arm in off on; do
    T=$OUT/p1a-u$U-ctx$CTX-$arm.perfetto-trace
    if ! run_one $arm "$U" "$CTX" 256 "$OUT/p1a-traced-u$U-ctx$CTX-$arm.txt" "--trace-gen $T"; then
      echo "RUN-FAILED traced u=$U ctx=$CTX arm=$arm" | tee -a "$RES"; FAIL=1
    fi
  done
done

rm -f /dev/hugepages/amx-r1* 2>/dev/null
campaign_guard_release
if [ "$FAIL" -ne 0 ]; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== r0-p1a-ab done $(date -u +%FT%TZ) ==="
