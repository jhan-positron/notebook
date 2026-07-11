#!/usr/bin/env bash
# apply_tron84_rinzler_AB.sh — plan item 6, rinzler-focused: arm tonight's
# nightly as the rinzler-boost side of the A/B.
# Waits until 02:55 UTC 2026-07-12 (after ci-runner-stop@delphi-3bda fires at
# 02:45 UTC and the GitHub runner goes offline; before the talos nightly),
# then applies "tron84": tron80 workers + rinzler cores 24,48,72,96 (+HT
# siblings) -> CLOS0 ~4100; everything else stays CLOS3 <= 2700.
# Baseline side = the 2026-07-10 and 2026-07-11 strict-tron80 nightlies
# (gpt-oss @8u decode 93.28 / 94.18).
# Revert: reboot (PR#165 boot service reapplies strict tron80) or
#   source flat_freq_utils.sh && flat_freq_apply 27-46,51-70,75-94,99-118
# Uses ONLY the NOPASSWD isst binary — no other privileges needed.
set -u
D=/scratch/jhan/flat_freq_tests/20260712_tron84-rinzler-nightly-AB
mkdir -p "$D"
LOG="$D/apply.log"
log(){ echo "$(date -u '+%F %T') $*" >> "$LOG"; }
log "armed pid=$$; waiting for 2026-07-12 02:55 UTC"

TARGET=$(date -ud "2026-07-12 02:55:00" +%s)
NOW=$(date +%s)
[ "$TARGET" -gt "$NOW" ] && sleep $((TARGET - NOW))

# refuse if a GitHub job is somehow still executing after the 02:45 stop
if pgrep -f "Runner.Worker" > /dev/null 2>&1; then
  log "ABORT: Runner.Worker still present after 02:55 — leaving shape alone"
  echo aborted-runner-busy > "$D/RESULT"; exit 1
fi
log "runner service: $(systemctl is-active actions.runner.positron-ai.delphi-3bda-0.service 2>&1)"

# preflight: current shape must read strict tron80 (worker fast, rinzler slow)
ISST="sudo -n /opt/intel-speed-select/intel-speed-select"
pre27=$($ISST --cpu 27 core-power get-assoc 2>&1 | grep -o "clos:[0-9]" | head -1)
pre24=$($ISST --cpu 24 core-power get-assoc 2>&1 | grep -o "clos:[0-9]" | head -1)
log "preflight cpu27=$pre27 cpu24=$pre24"
if [ "$pre27" != "clos:0" ] || [ "$pre24" != "clos:3" ]; then
  log "ABORT: unexpected pre-shape (want cpu27 clos:0, cpu24 clos:3)"
  echo aborted-bad-preshape > "$D/RESULT"; exit 1
fi

log "applying tron84 (workers + rinzler 24,48,72,96 + HT sibs -> CLOS0)"
source /home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh >> "$LOG" 2>&1
flat_freq_apply 24,27-46,48,51-70,72,75-94,96,99-118 >> "$LOG" 2>&1
log "flat_freq_apply rc=$?"

# verify: rinzler cores fast, drivers + others still slow
for c in 27 24 48 72 96 216 25 2; do
  echo -n "cpu$c " ; $ISST --cpu $c core-power get-assoc 2>&1 | grep -m1 clos:
done > "$D/shape_readback_0255.txt" 2>&1
if grep -q "cpu24 .*clos:0" "$D/shape_readback_0255.txt" \
   && grep -q "cpu96 .*clos:0" "$D/shape_readback_0255.txt" \
   && grep -q "cpu25 .*clos:3" "$D/shape_readback_0255.txt" \
   && grep -q "cpu2 .*clos:3"  "$D/shape_readback_0255.txt"; then
  echo applied > "$D/RESULT"
else
  echo verify-failed > "$D/RESULT"
fi
log "RESULT: $(cat "$D/RESULT")"

# second provenance probe right before the nightly usually starts (~07:00 UTC)
sleep 14400
for c in 27 24 48 72 96 2; do
  echo -n "cpu$c " ; $ISST --cpu $c core-power get-assoc 2>&1 | grep -m1 clos:
done > "$D/shape_readback_0655.txt" 2>&1
log "0655 provenance probe recorded"
