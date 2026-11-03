#!/usr/bin/env bash
# i5097-20261021 chain2.sh = pr5047-20261020/chain.sh for issue 5097: builds b47f (PR 5098 head + the dense-page live-mask fast
# path b79dfb9fed) and b47c1 (PR 5047 commit 1 alone e17a12ff09), reuses b47b/b47h; identity fix vs head; the kill-switch cell with
# four arms, the shipped p8192 cell with three, p1024 head/fix; tests of b47f; report. Waits for NOT_BEFORE before anything.
# pr5047-20261020 chain (runs ON delphi-3bda, detached): does PR 5047 (Ben's refactor of PR 4956's K-layout code) change
# throughput? Four binaries from two commits x two values of the CMake option TRON_K_VNNI, on our half of the machine.
# Fork of exec/glimext-20261018/chain2.sh. Steps, each with a marker under RES (resume = relaunch; done steps are skipped):
#   B builds     : build.sh four times in parallel (b47b = base OFF, b47h = head OFF, b47bv = base ON, b47hv = head ON),
#                  same recipe. The option-off pair is required; when an option-on build fails the chain drops the arms
#                  basev/headv (ARM_FILTER) and continues with the option-off comparison.
#   I identity   : smoke.sh per cell of IDENTITY_CELLS (1 user, temperature 0, pay-for-determinism, 256 tokens).
#   D campaign   : campaign.sh (cells x arms x REPS, TRON_ATTN_STATS=1 in every arm, SKIP_SERVING_UP=1).
#   T tests      : tests.sh (the head builds' three AMX test binaries + the kill-switch repeat). A failure is recorded and
#                  the chain CONTINUES to the report. T runs after D so the measurements get the free window first.
#   R report     : gen_report.py -> RES/results.md + results.json.
# Deadline: no run starts after DEADLINE_HHMM (01:30 UTC; the pre-CI hold is 01:40-03:45 UTC). A step that stops at the
# deadline is resumed after NOT_BEFORE (default 2026-10-21T13:30:00Z, after the nightly), done runs skipped. Production
# serving (taken down through platformd by the campaign functions when idle) is brought back before a long sleep and at exit.
# Usage (on 3bda): [BASE_SHA=...] [HEAD_SHA=...] [NOT_BEFORE=2026-10-21T13:30:00Z] [STEPS="B I D T R"] [REPS=4] [CELLS="<keys>"] bash chain.sh
# Log: exec/logs/pr5047-20261020-chain.log; status: exec/logs/pr5047-20261020-chain.status; marker RES/chain.done.
# Words: the lease = /run/lock/systems-test-ci.lease (nightly CI); our half = socket 1 + cards 90/93/b9/bc; base = PR 4956
# head a5697f86d3 (= PR 5047's base); head = PR 5047 head ade89a9d9c; the option = TRON_K_VNNI (OFF in every preset).
# Never edit this file while it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i5097-20261021
NAME=${NAME:-i5097-20261021}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
STATUS=$EXEC/logs/$NAME-chain.status
BASE_SHA=${BASE_SHA:-a5697f86d318e6a87badd4a751a005da52a9c25c}
HEAD_SHA=${HEAD_SHA:-ade89a9d9c83f887270c89d6ae6c02bced3f037e}
FIX_SHA=${FIX_SHA:-b79dfb9fed9a780282b277812ba9f378ee056f47}
C1_SHA=${C1_SHA:-e17a12ff09ea284ebd2616d1bf0531d7502e118d}
export NOT_BEFORE=${NOT_BEFORE:-2026-10-22T04:00:00Z}
DEADLINE_HHMM=${DEADLINE_HHMM:-0130}
STEPS=${STEPS:-"B I D T R"}
RT_BASE=/var/tmp/jhan/tron-b47b/gen/runtron.b47b
RT_HEAD=/var/tmp/jhan/tron-b47h/gen/runtron.b47h
RT_BASEV=/var/tmp/jhan/tron-b47bv/gen/runtron.b47bv
RT_HEADV=/var/tmp/jhan/tron-b47hv/gen/runtron.b47hv
RT_FIX=/var/tmp/jhan/tron-b47f/gen/runtron.b47f
RT_C1=/var/tmp/jhan/tron-b47c1/gen/runtron.b47c1
export RT_BASE RT_HEAD RT_BASEV RT_HEADV RT_FIX RT_C1
MAX_CAMPAIGN_PASSES=${MAX_CAMPAIGN_PASSES:-3}
export REPS=${REPS:-4} ARMS=${ARMS:-"base head fix c1"}
export ARM_FILTER=${ARM_FILTER:-}
export SKIP_SERVING_UP=1
[ -n "${CELLS_ALL:-}" ] && export CELLS_ALL
export CELLS=${CELLS:-}
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
# identity cells: key|model|tp|attn|prompt|arms|must-match pairs|informational pairs. head:head2 = the A/A control.
IDENTITY_CELLS=${IDENTITY_CELLS:-$'l8b-tp2-cpu-p1024|llama-3.1-8b-instruct-good-tp2|2|cpu|1024|head fix fix2|fix:fix2 fix:head|
l8b-tp2-cpu-p1024-off|llama-3.1-8b-instruct-good-tp2|2|cpu|1024|headoff fixoff|fixoff:headoff|'}
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
machine_line() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) lease=$(ci_lease_busy 600 && echo busy || echo clear) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | tr '\n' ' ') marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
nb=$(date -u -d "$NOT_BEFORE" +%s 2>/dev/null) || { echo "$(ts) bad NOT_BEFORE '$NOT_BEFORE'; not starting"; exit 1; }
case $DEADLINE_HHMM in ''|*[!0-9]*) echo "$(ts) DEADLINE_HHMM='$DEADLINE_HHMM' is not HHMM digits; not starting"; exit 1 ;; esac
DEADLINE_HHMM=$((10#$DEADLINE_HHMM))
export DEADLINE_HHMM
DEADLINE_HHMM=$(printf '%04d' "$DEADLINE_HHMM")
next_deadline() {
  local e; e=$(date -u -d "today $(printf '%02d:%02d' $((10#$DEADLINE_HHMM / 100)) $((10#$DEADLINE_HHMM % 100)))" +%s)
  [ "$e" -gt "$(date -u +%s)" ] || e=$((e + 86400)); echo "$e"
}
DEADLINE_EPOCH=$(next_deadline)
exec {CHAIN_LOCK_FD}>"/var/tmp/jhan/$NAME.chain.lock"
flock -n "$CHAIN_LOCK_FD" || { echo "$(ts) another chain.sh holds /var/tmp/jhan/$NAME.chain.lock; exit"; exit 1; }
rm -f "$RES/chain.done"
echo "=== $NAME chain started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') on $(hostname) BASE_SHA=$BASE_SHA HEAD_SHA=$HEAD_SHA NOT_BEFORE=$NOT_BEFORE DEADLINE_HHMM=$DEADLINE_HHMM STEPS=[$STEPS] REPS=$REPS ARMS=[$ARMS] ARM_FILTER=[$ARM_FILTER] CELLS=[${CELLS:-all}] deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) ==="
echo "$(ts) machine: $(machine_line)"
wait_for() { local label=$1 waited=0; shift; until "$@"; do [ $waited = 0 ] && { status "waiting: $label"; waited=1; }; sleep 60; done; [ $waited = 1 ] && echo "$(ts) $label: condition met"; return 0; }
not_before_passed() { [ "$(date -u +%s)" -ge "$nb" ]; }
sleep_until_not_before() {
  if not_before_passed; then nb=$(( $(date -u +%s) + 3600 )); NOT_BEFORE=$(date -u -d @"$nb" +%FT%TZ); echo "$(ts) NOT_BEFORE already passed; next attempt not before $NOT_BEFORE (one hour from now)"; fi
  serving_restore
  wait_for "NOT_BEFORE $NOT_BEFORE" not_before_passed
  DEADLINE_EPOCH=$(next_deadline); echo "$(ts) deadline for the next window: $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ)"
}
slot_free() { ! preci_hold && ! ci_lease_busy 600 && ! other_user_active 2>/dev/null && ! blackout_active; }
wait_slot() { wait_for "$1: pre-CI hold, CI lease busy (600 s grace), another person active or blackout" slot_free; echo "$(ts) $1 may start: $(machine_line)"; }
past_deadline() { [ "$(date -u +%s)" -ge "$DEADLINE_EPOCH" ]; }
SERVING_UP_HELPER=$EXEC/q4b-fpga-20260921/dut.sh
serving_restore() {
  [ -e "$RES/serving-taken-down.marker" ] || return 0
  if ci_lease_busy 600; then echo "$(ts) serving_restore: CI lease busy, leaving serving alone"; return 0; fi
  if rinzler_active; then echo "$(ts) serving_restore: rinzler units already active"; rm -f "$RES/serving-taken-down.marker"; return 0; fi
  echo "$(ts) serving_restore: production was taken down by this campaign and is not back; dut.sh serving-up"
  if timeout 900 bash "$SERVING_UP_HELPER" serving-up; then rm -f "$RES/serving-taken-down.marker"; else echo "$(ts) serving_restore: serving-up returned rc=$? (jhan: check platformd)"; fi
}
trap 'serving_restore; echo "$(ts) chain exit: $(machine_line)"' EXIT
trap 'echo "$(ts) TERM received"; exit 143' TERM
fail_chain() { status "chain stopped: $*"; echo "stopped: $*" >"$RES/chain.done"; exit 1; }
report_step() {
  if python3 "$C/gen_report2.py" "$RES" >"$RES/results.md" 2>"$RES/gen_report.err"; then
    echo "$(ts) report written: $RES/results.md ($(wc -l <"$RES/results.md") lines), $RES/results.json"
  else
    echo "$(ts) gen_report.py FAILED: $(tail -3 "$RES/gen_report.err" | tr '\n' ' ')"
  fi
}
build_settled() { local m; m=$(cat "$RES/build-$1.done" 2>/dev/null); [ "$m" = ok ] || [ "${m#failed}" != "$m" ]; }
builds_settled() { build_settled b47f && build_settled b47c1 && { [ -x "$RT_BASE" ] || build_settled b47b; } && { [ -x "$RT_HEAD" ] || build_settled b47h; }; }
build_ok() { [ "$(cat "$RES/build-$1.done" 2>/dev/null)" = ok ]; }
wt_sha() { git -C "/var/tmp/jhan/tron-$1" rev-parse HEAD 2>/dev/null; }
apply_filter() {  # when an option-on build is not ok, drop its arms
  if ! build_ok b47bv || ! build_ok b47hv; then
    ARM_FILTER="basev headv"; export ARM_FILTER
    echo "$(ts) option-on builds not both ok (b47bv=[$(cat "$RES/build-b47bv.done" 2>/dev/null)] b47hv=[$(cat "$RES/build-b47hv.done" 2>/dev/null)]): arms basev/headv dropped (ARM_FILTER=[$ARM_FILTER])"
  fi
}
if ! not_before_passed; then status "waiting for NOT_BEFORE $NOT_BEFORE (the machine is in use until then)"; wait_for "NOT_BEFORE $NOT_BEFORE" not_before_passed; DEADLINE_EPOCH=$(next_deadline); echo "$(ts) deadline for this window: $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ)"; fi
wait_slot "chain start"
for step in $STEPS; do
  case $step in
    B)
      # b47b and b47h come from the pr5047-20261020 campaign when present (binary present at the expected sha), else they are rebuilt here.
      reuse_ok() { [ -x "$1" ] && [ "$(wt_sha "$2")" = "$3" ]; }
      if build_ok b47f && build_ok b47c1 && [ -x "$RT_FIX" ] && [ -x "$RT_C1" ] && [ "$(wt_sha b47f)" = "$FIX_SHA" ] && [ "$(wt_sha b47c1)" = "$C1_SHA" ] \
         && reuse_ok "$RT_BASE" b47b "$BASE_SHA" && reuse_ok "$RT_HEAD" b47h "$HEAD_SHA"; then echo "$(ts) step B already done"; continue; fi
      status "step B: builds (b47f = $FIX_SHA, b47c1 = $C1_SHA; b47b/b47h reused when present)"
      build_ok b47f || { env TAG=b47f SHA="$FIX_SHA" VNNI=OFF bash "$C/build3.sh" & }
      build_ok b47c1 || { env TAG=b47c1 SHA="$C1_SHA" VNNI=OFF bash "$C/build3.sh" & }
      reuse_ok "$RT_BASE" b47b "$BASE_SHA" || { env TAG=b47b SHA="$BASE_SHA" VNNI=OFF bash "$C/build3.sh" & }
      reuse_ok "$RT_HEAD" b47h "$HEAD_SHA" || { env TAG=b47h SHA="$HEAD_SHA" VNNI=OFF bash "$C/build3.sh" & }
      wait_for "step B: the build markers" builds_settled
      wait
      for t in b47f b47c1 b47b b47h; do echo "$(ts) step B: build $t marker [$(cat "$RES/build-$t.done" 2>/dev/null || echo reused)]"; done
      for t in b47b b47h; do for f in build-$t.txt hetero-$t.txt build-symbols-$t.txt; do [ -e "$RES/$f" ] || cp "$EXEC/results/pr5047-20261020/$f" "$RES/$f" 2>/dev/null; done; done   # the reused builds' records, for the report
      build_ok b47f || fail_chain "step B: build b47f [$(cat "$RES/build-b47f.done" 2>/dev/null)], see $EXEC/logs/$NAME-build-b47f.log"
      if ! build_ok b47c1; then ARM_FILTER="c1 c1off"; export ARM_FILTER; echo "$(ts) step B: build b47c1 failed [$(cat "$RES/build-b47c1.done" 2>/dev/null)]: arms c1/c1off dropped"; fi
      [ -x "$RT_BASE" ] && [ -x "$RT_HEAD" ] && [ -x "$RT_FIX" ] || fail_chain "step B: a binary is missing although the markers are ok"
      [ "$(wt_sha b47f)" = "$FIX_SHA" ] || fail_chain "step B: tron-b47f is not at $FIX_SHA"
      [ "$(wt_sha b47b)" = "$BASE_SHA" ] || fail_chain "step B: tron-b47b is not at $BASE_SHA"
      [ "$(wt_sha b47h)" = "$HEAD_SHA" ] || fail_chain "step B: tron-b47h is not at $HEAD_SHA" ;;
    I)
      if [ "$(cat "$RES/identity.done" 2>/dev/null)" = ok ]; then echo "$(ts) step I already done: ok"; continue; fi
      [ -x "$RT_BASE" ] && [ -x "$RT_HEAD" ] && [ -x "$RT_FIX" ] || fail_chain "step I: binaries missing (step B not done)"
      ipass=0
      while :; do
        ipass=$((ipass + 1))
        status "step I: identity smokes (pass $ipass)"
        verdict=ok
        while IFS='|' read -r key model tp attn prompt arms must info; do
          [ -n "$key" ] || continue
          sm=$RES/smoke/$key
          if [ "$(cat "$sm/smoke.done" 2>/dev/null)" = ok ]; then echo "$(ts) step I: $key already ok"; continue; fi
          past_deadline && { echo "$(ts) step I: deadline before $key"; verdict=deadline; break; }
          status "step I: smoke $key"
          env KEY="$key" MODEL="$model" TP="$tp" ATTN="$attn" PROMPT="$prompt" LEN=256 SMOKE_ARMS="$arms" MUST_MATCH="$must" INFO_PAIRS="$info" bash "$C/smoke2.sh" </dev/null
          v=$(cat "$sm/smoke.done" 2>/dev/null)
          nfail=$(tac "$sm/smoke.txt" 2>/dev/null | awk '/^SMOKE-VERDICT/{c++; next} c==1 && /^SMOKE-FAILED/{n++} END{print n+0}')
          echo "$(ts) step I: $key -> [$v] failed-lines=$nfail; $(grep -E ' vs .*(identical|first difference)' "$sm/smoke.txt" | tail -5 | cut -c1-140 | tr '\n' ';')"
          if [ "$v" != ok ] && { past_deadline || tac "$sm/smoke.txt" 2>/dev/null | awk '/^SMOKE-VERDICT/{c++; next} c==1 && /^SMOKE-FAILED arm=[a-z0-9]*: deadline/{f=1} END{exit !f}'; }; then
            echo "$(ts) step I: deadline during $key"; verdict=deadline; break
          fi
          [ "$v" = ok ] && [ "${nfail:-0}" = 0 ] || verdict="failed-$key"
        done <<<"$IDENTITY_CELLS"
        {
          echo "# identity $(ts): per cell the LAST verdict and pair lines of smoke/<key>/smoke.txt (1 user, temperature 0, pay-for-determinism, seed 1, 256 tokens, --dont-stop)"
          while IFS='|' read -r key model tp attn prompt arms must info; do
            [ -n "$key" ] || continue
            echo "## $key model=$model tp=$tp attn=$attn prompt=$prompt arms=[$arms] must_match=[$must] info=[$info] verdict=$(cat "$RES/smoke/$key/smoke.done" 2>/dev/null || echo missing)"
            grep -E '^(smoke token rows|[a-z0-9]+ vs [a-z0-9]+:|SMOKE-FAILED|SMOKE-STOPPED)' "$RES/smoke/$key/smoke.txt" 2>/dev/null | tail -9
          done <<<"$IDENTITY_CELLS"
        } >"$RES/identity.txt"
        echo "$verdict" >"$RES/identity.done"; echo "$(ts) step I pass $ipass result: [$verdict]"
        [ "$verdict" = deadline ] || break
        [ $ipass -lt "$MAX_CAMPAIGN_PASSES" ] || fail_chain "step I: deadline reached in $ipass passes (resume with STEPS='I D T R')"
        status "step I: deadline; sleeping until NOT_BEFORE $NOT_BEFORE, then resuming (done cells are skipped)"
        sleep_until_not_before; wait_slot "step I pass $((ipass + 1))"
      done ;;
    D)
      if [ "$(cat "$EXEC/logs/$NAME.done" 2>/dev/null)" = ok ]; then echo "$(ts) step D already done: ok"; continue; fi
      [ -x "$RT_BASE" ] && [ -x "$RT_HEAD" ] && [ -x "$RT_FIX" ] || fail_chain "step D: binaries missing (step B not done)"
      pass=0
      while :; do
        pass=$((pass + 1))
        past_deadline && { status "step D: past the deadline; sleeping until NOT_BEFORE $NOT_BEFORE"; sleep_until_not_before; wait_slot "step D pass $pass"; }
        status "step D: campaign pass $pass (arms [$ARMS] minus [$ARM_FILTER] x REPS $REPS; cells ${CELLS:-all of the campaign.sh table})"
        env NAME="$NAME" bash "$C/campaign2.sh"
        m=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null); echo "$(ts) step D pass $pass result: [$m]"
        case $m in
          ok) break ;;
          ok-with-*) echo "$(ts) step D: some runs failed; relaunch with STEPS='D T R' to retry them"; break ;;
          deadline)
            [ $pass -lt "$MAX_CAMPAIGN_PASSES" ] || { report_step; fail_chain "step D: deadline reached in $pass passes (partial report written; resume with STEPS='D T R')"; }
            status "step D: campaign stopped at the deadline; sleeping until NOT_BEFORE $NOT_BEFORE, then resuming (done runs are skipped)"
            sleep_until_not_before; wait_slot "step D pass $((pass + 1))" ;;
          *) report_step; fail_chain "step D ended with marker [$m] (partial report written; resume with STEPS='D T R')" ;;
        esac
      done ;;
    T)
      if [ "$(cat "$RES/tests.done" 2>/dev/null)" = ok ]; then echo "$(ts) step T already done: ok"; continue; fi
      if past_deadline || preci_hold; then status "step T: inside the deadline window; sleeping until NOT_BEFORE $NOT_BEFORE"; sleep_until_not_before; wait_slot "step T"; fi
      status "step T: tests.sh"
      env SHA="$FIX_SHA" TAGS="b47f" bash "$C/tests2.sh"; trc=$?
      m=$(cat "$RES/tests.done" 2>/dev/null); echo "$(ts) step T result: rc=$trc marker=[$m]"
      [ "$m" = ok ] || echo "$(ts) step T: TESTS NOT OK [$m] (see $RES/tests.txt); the chain continues to the report, which flags it" ;;
    R)
      status "step R: report"; report_step ;;
    *) echo "$(ts) unknown step $step" ;;
  esac
done
serving_restore
echo "ok" >"$RES/chain.done"; status "chain finished"
echo "=== $NAME chain finished $(ts): B=$(cat "$RES/build-b47f.done" 2>/dev/null)/$(cat "$RES/build-b47c1.done" 2>/dev/null)/b47b:$(cat "$RES/build-b47b.done" 2>/dev/null || echo reused)/b47h:$(cat "$RES/build-b47h.done" 2>/dev/null || echo reused) I=$(cat "$RES/identity.done" 2>/dev/null) D=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null) T=$(cat "$RES/tests.done" 2>/dev/null) R=$([ -s "$RES/results.md" ] && echo written || echo missing) ==="
