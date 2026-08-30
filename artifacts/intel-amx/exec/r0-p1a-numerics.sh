#!/usr/bin/env bash
# P1a numerics addendum: SEEDED token comparison with an off-vs-off control.
# The campaign's first numerics smoke ran unseeded (runtron picks a random
# seed per run), so its divergence verdict is void. This addendum runs
# --seed 42 three ways: off#1, off#2 (control), on. If off#1 != off#2 the
# token comparison is not a valid instrument in this harness and numerics
# falls to the P2 logits pin (pre-registration allows recording exactly that).
# Marker values: ok / guard-stop / serving-busy / build-missing / check-output / aborted.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/router
LOG=$EXEC/logs/r0-p1a-numerics.log
MARKER=$EXEC/logs/r0-p1a-numerics.done
TRON=~/workspace/tron-router-p0
mkdir -p "$OUT" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== r0-p1a-numerics start $(date -u +%FT%TZ) ==="
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
  --numa 0 --hugepage_file /dev/hugepages/amx-r1 --nr_hugepages 128 -o \
  --seed 42 --prompt-length 2048 -l 32 -u 1"
FAIL=0
run() { # $1 tag, $2 env
  echo "+ env ${2:-<none>} timeout 600 ./gen/runtron $RTARGS"
  env $2 timeout 600 ./gen/runtron $RTARGS >"$OUT/p1a-num-$1.txt" 2>&1 \
    || { echo "RUN-FAILED $1"; FAIL=1; }
}
run off1 ""
run off2 ""
run on   "TRON_CPU_ROUTER=1"

norm() { sed -E 's/^\[[0-9:.]+\|thread [0-9]+\|cpu [0-9]+\] //' "$1" \
  | grep -E $'\x1b\[38' ; }   # keep only token-stream (colored) lines
V=$OUT/p1a-numerics-verdict.txt
if ! diff <(norm "$OUT/p1a-num-off1.txt") <(norm "$OUT/p1a-num-off2.txt") \
     >"$OUT/p1a-num-ctl-diff.txt" 2>&1; then
  echo "CONTROL DIVERGES: seeded off-vs-off differs - token comparison invalid in this harness"
  echo "instrument-invalid (seeded off-vs-off differs; numerics falls to P2 logits pin)" >"$V"
else
  if diff <(norm "$OUT/p1a-num-off1.txt") <(norm "$OUT/p1a-num-on.txt") \
       >"$OUT/p1a-num-ab-diff.txt" 2>&1; then
    echo "NUMERICS: seeded token output IDENTICAL off vs on"
    echo "identical (seeded)" >"$V"
  else
    n=$(wc -l <"$OUT/p1a-num-ab-diff.txt")
    echo "NUMERICS: seeded divergence, $n diff lines (control clean) - expert-set flips or logits deltas; investigate"
    echo "divergence (seeded, control clean, $n diff lines)" >"$V"
  fi
fi

rm -f /dev/hugepages/amx-r1* 2>/dev/null
campaign_guard_release
if [ "$FAIL" -ne 0 ]; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== r0-p1a-numerics done $(date -u +%FT%TZ) ==="
