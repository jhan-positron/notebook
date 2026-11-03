#!/usr/bin/env bash
# glimpl-20261017 chain (runs ON delphi-3bda, detached by jhan): the Muse Glimmer kv_mul-16 AMX machine test on our half of
# the machine. Fork of exec/attnstats-20261002/chain.sh; the build is NOT a step here (jhan launches build.sh separately).
# Steps, each with a marker under RES (resume = relaunch; done steps are skipped):
#   B build-wait : wait for RES/build.done = ok (written by build.sh); "failed: ..." stops the chain.
#   T tests      : tests.sh (this folder) -> RES/tests.done must be ok (it waits for the probe markers and an idle half itself).
#   G go-wait    : wait for EVERY probe marker in WAIT_MARKERS (default: exec/results/td-20261016/probe.done,
#                  td2-20261016/probe.done and td3-20261016/probe.done = the other session's three probe rounds are
#                  finished; a fourth is added with WAIT_MARKERS="..." at launch) AND the go file exec/glimpl-20261017/go.marker
#                  (jhan creates it by hand after the other session says it is done). Deadline: no run starts after
#                  DEADLINE_HHMM (01:30 UTC). When the go condition is not met by then, the chain sleeps until NOT_BEFORE
#                  (default 2026-10-17T13:00:00Z, after the nightly) and then waits for the CI lease to clear (600 s grace).
#   D campaign   : campaign.sh (this folder): 9 cells x arms amxon/amxoff x REPS (default 2), TRON_ATTN_STATS=1 in both arms.
#                  A campaign that stops at its deadline is resumed after NOT_BEFORE (done runs are skipped).
#   R report     : gen_compare.py -> RES/attn-stats-compare.md and RES/results.json.
# Usage (on 3bda): SHA=<full sha> [NOT_BEFORE=2026-10-17T13:00:00Z] [STEPS="B T G D R"] [REPS=2] [WAIT_MARKERS="..."] bash chain.sh
# Log: exec/logs/glimpl-20261017-chain.log; status: exec/logs/glimpl-20261017-chain.status; marker RES/chain.done.
# Words: the lease = /run/lock/systems-test-ci.lease (nightly CI); our half = socket 1 + cards 90/93/b9/bc;
# amxon = TRON_AMX_DISABLE unset (the AMX kernel serves dense pages); amxoff = TRON_AMX_DISABLE=1 (the kill switch:
# the same binary scores every page with the AVX software loop).
# Never edit this file while it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
SHA=${SHA:?SHA=<full 40-hex commit sha of jhan-amx-kvmul16> is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/glimpl-20261017
NAME=${NAME:-glimpl-20261017}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
STATUS=$EXEC/logs/$NAME-chain.status
export NOT_BEFORE=${NOT_BEFORE:-2026-10-17T13:00:00Z}
DEADLINE_HHMM=${DEADLINE_HHMM:-0130}
STEPS=${STEPS:-"B T G D R"}
WT=/var/tmp/jhan/tron-g16q
RT=$WT/gen/runtron.g16q
GO_FILE=$C/go.marker
# the other session's probe rounds; a fourth is added by launching with WAIT_MARKERS="<file> <file> ..." (no edit after launch)
WAIT_MARKERS=${WAIT_MARKERS:-"$EXEC/results/td-20261016/probe.done $EXEC/results/td2-20261016/probe.done $EXEC/results/td3-20261016/probe.done"}
MAX_CAMPAIGN_PASSES=${MAX_CAMPAIGN_PASSES:-3}
export REPS=${REPS:-2} ARMS=${ARMS:-"amxon amxoff"}
# the arm environments come from the launch (launch.sh passes ARM_ENV_amxon / ARM_ENV_amxoff); the defaults are the kill-switch A/B
export ARM_ENV_amxon="${ARM_ENV_amxon:-TRON_ATTN_STATS=1}"
export ARM_ENV_amxoff="${ARM_ENV_amxoff:-TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1}"
[ -n "${CELLS_ALL:-}" ] && export CELLS_ALL     # the default cell table lives in campaign.sh
export CELLS=${CELLS:-}
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
machine_line() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) lease=$(ci_lease_busy 600 && echo busy || echo clear) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
nb=$(date -u -d "$NOT_BEFORE" +%s 2>/dev/null) || { echo "$(ts) bad NOT_BEFORE '$NOT_BEFORE' (use 2026-10-17T13:00:00Z); not starting"; exit 1; }
case $DEADLINE_HHMM in ''|*[!0-9]*) echo "$(ts) DEADLINE_HHMM='$DEADLINE_HHMM' is not HHMM digits; not starting"; exit 1 ;; esac
DEADLINE_HHMM=$((10#$DEADLINE_HHMM))
next_deadline() {  # the next occurrence of DEADLINE_HHMM UTC after now
  local e; e=$(date -u -d "today $(printf '%02d:%02d' $((DEADLINE_HHMM / 100)) $((DEADLINE_HHMM % 100)))" +%s)
  [ "$e" -gt "$(date -u +%s)" ] || e=$((e + 86400)); echo "$e"
}
DEADLINE_EPOCH=$(next_deadline)   # fixed at start; moved to the next window only after a NOT_BEFORE sleep
exec {CHAIN_LOCK_FD}>"/var/tmp/jhan/$NAME.chain.lock"
flock -n "$CHAIN_LOCK_FD" || { echo "$(ts) another chain.sh holds /var/tmp/jhan/$NAME.chain.lock; exit"; exit 1; }
rm -f "$RES/chain.done"
echo "=== $NAME chain started $(ts) pid $$ on $(hostname) SHA=$SHA NOT_BEFORE=$NOT_BEFORE DEADLINE_HHMM=$(printf '%04d' "$DEADLINE_HHMM") STEPS=[$STEPS] REPS=$REPS ARMS=[$ARMS] CELLS=[${CELLS:-all}] deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) WAIT_MARKERS=[$WAIT_MARKERS] ==="
# wait_for <label> <check command...>: loop until the command succeeds; one log line when the wait starts and one when it ends
wait_for() { local label=$1 waited=0; shift; until "$@"; do [ $waited = 0 ] && { status "waiting: $label"; waited=1; }; sleep 60; done; [ $waited = 1 ] && echo "$(ts) $label: condition met"; return 0; }
not_before_passed() { [ "$(date -u +%s)" -ge "$nb" ]; }
not_before_wait() { wait_for "NOT_BEFORE $NOT_BEFORE" not_before_passed; }
sleep_until_not_before() {  # after a missed deadline: NOT_BEFORE is moved to the configured time, or to tomorrow's if that is already past
  if not_before_passed; then nb=$(( $(date -u +%s) + 3600 )); NOT_BEFORE=$(date -u -d @"$nb" +%FT%TZ); echo "$(ts) NOT_BEFORE already passed; next attempt not before $NOT_BEFORE (one hour from now)"; fi
  not_before_wait
  DEADLINE_EPOCH=$(next_deadline); echo "$(ts) deadline for the next window: $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ)"
}
slot_free() { ! preci_hold && ! ci_lease_busy 600 && ! other_user_active 2>/dev/null && ! blackout_active; }
wait_slot() { wait_for "$1: pre-CI hold, CI lease busy (600 s grace), another person active or blackout" slot_free; echo "$(ts) $1 may start: $(machine_line)"; }
past_deadline() { [ "$(date -u +%s)" -ge "$DEADLINE_EPOCH" ]; }
# Second chance for production serving: campaign.sh marks every takeover it did (serving-taken-down.marker) and brings
# serving back in its own finish(); if it died before that, this chain does it (after step D and on exit).
SERVING_UP_HELPER=$EXEC/q4b-fpga-20260921/dut.sh
serving_restore() {
  [ -e "$RES/serving-taken-down.marker" ] || return 0
  if ci_lease_busy 600; then echo "$(ts) serving_restore: CI lease busy, leaving serving alone"; return 0; fi
  if rinzler_active; then echo "$(ts) serving_restore: rinzler units already active"; rm -f "$RES/serving-taken-down.marker"; return 0; fi
  echo "$(ts) serving_restore: production was taken down by the campaign and is not back; dut.sh serving-up"
  if timeout 900 bash "$SERVING_UP_HELPER" serving-up; then rm -f "$RES/serving-taken-down.marker"; else echo "$(ts) serving_restore: serving-up returned rc=$? (jhan: check platformd)"; fi
}
trap 'serving_restore' EXIT
trap 'echo "$(ts) TERM received"; exit 143' TERM
fail_chain() { status "chain stopped: $*"; echo "stopped: $*" >"$RES/chain.done"; exit 1; }
report_step() {
  if python3 "$C/gen_compare.py" "$RES" >"$RES/attn-stats-compare.md" 2>"$RES/gen_compare.err"; then
    echo "$(ts) report written: $RES/attn-stats-compare.md ($(wc -l <"$RES/attn-stats-compare.md") lines), $RES/results.json"
  else
    echo "$(ts) gen_compare.py FAILED: $(tail -3 "$RES/gen_compare.err" | tr '\n' ' ')"
  fi
}
build_settled() { local m; m=$(cat "$RES/build.done" 2>/dev/null); [ "$m" = ok ] || [ "${m#failed}" != "$m" ]; }
go_ready() { local m; for m in $WAIT_MARKERS; do [ -s "$m" ] || return 1; done; [ -e "$GO_FILE" ]; }
go_ready_or_deadline() { go_ready || past_deadline; }
for step in $STEPS; do
  case $step in
    B)
      wait_for "step B: build.done from build.sh (launch it separately: SHA=$SHA bash $C/build.sh)" build_settled
      m=$(cat "$RES/build.done"); echo "$(ts) step B: build marker [$m]"
      [ "$m" = ok ] || fail_chain "step B: build marker [$m], see $EXEC/logs/$NAME-build.log"
      [ -x "$RT" ] || fail_chain "step B: $RT missing although build.done is ok"
      [ "$(git -C "$WT" rev-parse HEAD 2>/dev/null)" = "$SHA" ] || fail_chain "step B: $WT is not at $SHA" ;;
    T)
      if [ "$(cat "$RES/tests.done" 2>/dev/null)" = ok ]; then echo "$(ts) step T already done: ok"; continue; fi
      status "step T: tests.sh"
      env SHA="$SHA" bash "$C/tests.sh"; trc=$?
      m=$(cat "$RES/tests.done" 2>/dev/null); echo "$(ts) step T result: rc=$trc marker=[$m]"
      [ "$m" = ok ] || fail_chain "step T: tests marker [$m], see $RES/tests.txt and $EXEC/logs/$NAME-tests.log" ;;
    G)
      while :; do
        wait_for "step G: probe markers [$WAIT_MARKERS] and go file $GO_FILE (deadline $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ))" go_ready_or_deadline
        go_ready && { echo "$(ts) step G: go condition met: $(machine_line)"; break; }
        status "step G: deadline $(printf '%04d' "$DEADLINE_HHMM") UTC passed without the go condition; sleeping until NOT_BEFORE $NOT_BEFORE"
        sleep_until_not_before
        wait_slot "step G after NOT_BEFORE"
      done ;;
    D)
      if [ "$(cat "$EXEC/logs/$NAME.done" 2>/dev/null)" = ok ]; then echo "$(ts) step D already done: ok"; continue; fi
      [ -x "$RT" ] || fail_chain "step D: $RT missing (build.sh not done)"
      pass=0
      while :; do
        pass=$((pass + 1))
        status "step D: campaign pass $pass (arms [$ARMS] x REPS $REPS; cells ${CELLS:-all of the campaign.sh table})"
        env RT_MAIN="$RT" NAME="$NAME" bash "$C/campaign.sh"
        m=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null); echo "$(ts) step D pass $pass result: [$m]"
        serving_restore
        case $m in
          ok) break ;;
          ok-with-*) echo "$(ts) step D: some runs failed; relaunch with STEPS='D R' to retry them"; break ;;
          deadline)
            [ $pass -lt "$MAX_CAMPAIGN_PASSES" ] || { report_step; fail_chain "step D: deadline reached in $pass passes (partial report written; resume with STEPS='G D R')"; }
            status "step D: campaign stopped at the deadline; sleeping until NOT_BEFORE $NOT_BEFORE, then resuming (done runs are skipped)"
            sleep_until_not_before; wait_slot "step D pass $((pass + 1))" ;;
          *) report_step; fail_chain "step D ended with marker [$m] (partial report written; resume with STEPS='D R')" ;;
        esac
      done ;;
    R)
      status "step R: report"; report_step ;;
    *) echo "$(ts) unknown step $step" ;;
  esac
done
echo "ok" >"$RES/chain.done"; status "chain finished"
echo "=== $NAME chain finished $(ts): B=$(cat "$RES/build.done" 2>/dev/null) T=$(cat "$RES/tests.done" 2>/dev/null) D=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null) R=$([ -s "$RES/attn-stats-compare.md" ] && echo written || echo missing) ==="
