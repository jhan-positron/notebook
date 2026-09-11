#!/usr/bin/env bash
# gpt-oss-120b tp2 regression guard on OUR HALF of delphi-3bda (jhan, 2026-09-09), run after
# qwen8u8k-pr1-half.sh on the same two binaries (exec/logs/qwen8u8k-prep.bins) and the same
# placement: --instance 2,4 on cards 90:00.0 and 93:00.0 (socket 1), --numa 1.
# gpt-oss-120b's shape (64 query heads, 8 KV heads, head size 64) fails the AMX gate at
# compile time, so all three arms should agree within noise: this run guards the shared
# attention code, not the AMX path.
# Arms: clean  = runtron.pr1clean (built without the option)
#       amxoff = runtron.pr1amx with TRON_AMX_DISABLE=1 (the kill switch)
#       amxon  = runtron.pr1amx with TRON_AMX_DISABLE=0
# Cells: prompt 2048 and prompt 8192, 8 users, 256 generated, REPS rounds (default 2), as in
# exec/p2-perf-round-20260830.sh (which used the same hugepage arguments for this model).
# Waits for the pre-build and for the qwen run's .done marker, so the two campaigns never
# interleave on the slot. Same guard rules as the qwen half script (Bill is not a reason to
# wait; CI lease, serving and the pre-CI hold are).
# Output: exec/results/gptoss120b-pr1-half-<date>.txt; log exec/logs/gptoss120b-pr1-half.{log,done}
set -u
EXEC=~/workspace/intel-AMX/exec
REPS=${REPS:-2}
OUT=$EXEC/results/gptoss120b-pr1-half-$(date -u +%Y%m%dT%H%M).txt
LOG=$EXEC/logs/gptoss120b-pr1-half.log; MARKER=$EXEC/logs/gptoss120b-pr1-half.done
WAIT=${GPTOSS_WAIT_SEC:-86400}
mkdir -p "$EXEC/results" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== gptoss120b-pr1-half queued $(date -u +%FT%TZ) reps=$REPS wait=$WAIT s ==="
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"   # our-half work: Bill's activity is not a reason to wait
HOLD_FROM=${PRECI_HOLD_FROM:-140}; HOLD_TO=345
blocked() {     # returns 0 = must not run now, and prints why
  local hm; hm=$((10#$(date -u +%H%M)))
  [ "$hm" -ge "$HOLD_FROM" ] && [ "$hm" -lt "$HOLD_TO" ] && { echo "pre-CI hold ($HOLD_FROM-$HOLD_TO UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler serving active"; return 0; }
  return 1
}
wait_clear() {  # waits until not blocked; returns 1 at the deadline
  local why
  while why=$(blocked); do
    [ "$(date +%s)" -ge "$deadline" ] && return 1
    echo "$(date -u +%FT%TZ) waiting: $why"; sleep 120
  done
  return 0
}
deadline=$(( $(date +%s) + WAIT ))
until [ "$(cat "$EXEC/logs/qwen8u8k-prep.done" 2>/dev/null)" = ok ]; do
  m=$(cat "$EXEC/logs/qwen8u8k-prep.done" 2>/dev/null)
  case "$m" in build-failed|dut-never-free|guard-never-free|worktree-failed|no-checkout|no-worktree) echo "prep failed: $m"; echo prep-failed >"$MARKER"; exit 1;; esac
  [ "$(date +%s)" -ge "$deadline" ] && { echo prep-never-done >"$MARKER"; exit 1; }
  echo "$(date -u +%FT%TZ) waiting for the pre-build (qwen8u8k-prep.done)"; sleep 300
done
BIN_AMX=$(awk '$1=="amx"{print $2}' "$EXEC/logs/qwen8u8k-prep.bins"); BIN_CLEAN=$(awk '$1=="clean"{print $2}' "$EXEC/logs/qwen8u8k-prep.bins")
[ -x "$BIN_AMX" ] && [ -x "$BIN_CLEAN" ] || { echo "binaries missing: '$BIN_AMX' '$BIN_CLEAN'"; echo no-binaries >"$MARKER"; exit 1; }
# Run after the qwen campaign: its script removes its marker at start and writes it at the end.
until [ -s "$EXEC/logs/qwen8u8k-pr1-half.done" ]; do
  [ "$(date +%s)" -ge "$deadline" ] && { echo qwen-never-done >"$MARKER"; exit 1; }
  echo "$(date -u +%FT%TZ) waiting for the qwen run (qwen8u8k-pr1-half.done)"; sleep 120
done
TIP=$(git -C "$(dirname "$(dirname "$BIN_AMX")")" rev-parse --short=10 HEAD 2>/dev/null)
wait_clear || { echo "never clear before the deadline"; echo dut-never-free >"$MARKER"; exit 1; }
trap 'campaign_guard_release; rm -f /dev/hugepages/amx-p2f* 2>/dev/null' EXIT   # the flock is taken per run, inside the loop
echo "=== start $(date -u +%FT%TZ) ==="
RTARGS="stream-generate-text -m ingested-gpt-oss-120b-tp2 \
  --instance 2,4 --devices 90:00.0,93:00.0 \
  --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 \
  --numa 1 --hugepage_file /dev/hugepages/amx-p2f --nr_hugepages 128 -o"
{
  echo "# gpt-oss-120b tp2, 8 users, prompts 2048 and 8192, 256 generated; PR 1 tip $TIP; started $(date -u +%FT%TZ); host $(hostname)"
  echo "# OUR-HALF placement (same as qwen8u8k-pr1-half.sh): --instance 2,4, cards 90:00.0,93:00.0, socket-1 app cores 223-224,96-101,120-125,225-226,102-107,126-131, dev cores 75,76, --numa 1"
  echo "# gpt-oss-120b fails the AMX shape gate, so the three arms are expected to agree within noise."
  sha256sum "$BIN_CLEAN" "$BIN_AMX"
} >"$OUT"
gave_up=0
for rep in $(seq 1 "$REPS"); do
  for PL in 2048 8192; do
    for arm in "clean $BIN_CLEAN TRON_AMX_DISABLE=0" "amxoff $BIN_AMX TRON_AMX_DISABLE=1" "amxon $BIN_AMX TRON_AMX_DISABLE=0"; do
      set -- $arm; name=$1; bin=$2; mode=$3
      attempt=0
      while :; do
        attempt=$((attempt + 1))
        if ! wait_clear; then echo "### GAVE-UP before $name prompt=$PL rep=$rep (deadline)" >>"$OUT"; gave_up=1; break 4; fi
        if [ -z "${CAMPAIGN_LOCK_FD:-}" ]; then
          until campaign_guard_acquire; do
            [ "$(date +%s)" -ge "$deadline" ] && { echo "### GAVE-UP before $name prompt=$PL rep=$rep (guard)" >>"$OUT"; gave_up=1; break 5; }
            sleep 60; wait_clear || { echo "### GAVE-UP before $name prompt=$PL rep=$rep (deadline)" >>"$OUT"; gave_up=1; break 5; }
          done
        fi
        echo "### arm=$name mode=$mode prompt=$PL len=256 users=8 rep=$rep attempt=$attempt $(date -u +%FT%TZ)" >>"$OUT"
        # env -u SYSTEM_CONFIG: the login environment exports "--instance 1,2"; tron applies SYSTEM_CONFIG after the
        # command line and it would replace the placement below. The kept lines prove the placement that ran.
        res=$(env -u SYSTEM_CONFIG USE_HW_ATTN=0 $mode timeout 1800 "$bin" $RTARGS --prompt-length "$PL" -l 256 -u 8 2>&1 | grep -E "Parsing the prompt took|average tok/s|Configured instance|App CPU list|environment system config"; exit ${PIPESTATUS[0]})
        rc=$?
        echo "$res" >>"$OUT"
        campaign_guard_release   # taken again at the top of the next attempt/arm
        if grep -q "average tok/s" <<<"$res" && [ $rc -eq 0 ]; then break; fi
        if { [ $rc -eq 143 ] || [ $rc -eq 137 ]; } && [ $attempt -lt 4 ]; then
          echo "### RUN-STOPPED rc=$rc attempt=$attempt (killed); will repeat this arm when clear" >>"$OUT"; rm -f /dev/hugepages/amx-p2f* 2>/dev/null
          continue
        fi
        echo "### RUN-FAILED rc=$rc attempt=$attempt" >>"$OUT"; rm -f /dev/hugepages/amx-p2f* 2>/dev/null; break
      done
    done
  done
done
echo "=== done $(date -u +%FT%TZ) -> $OUT ==="
if [ $gave_up -eq 1 ]; then echo gave-up >"$MARKER"; elif grep -q "RUN-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
