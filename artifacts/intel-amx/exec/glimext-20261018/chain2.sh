#!/usr/bin/env bash
# glimext-20261018 chain2 = chain.sh with the fixes of the 2026-10-18 script review (new file name: the first chain ran from chain.sh
# and a running script is never edited; relaunch THIS file to resume). Changes: step I loops over passes like step D and detects
# a deadline inside a cell; the SMOKE-FAILED count looks at the current pass only; step D checks the deadline before starting;
# step E's bound is relative (E_MIN_HOURS before the deadline) next to E_NOT_AFTER; step B re-checks binaries before skipping;
# smoke2.sh (--dont-stop) replaces smoke.sh; children of the identity loop read /dev/null.
# glimext-20261018 chain (runs ON delphi-3bda, detached): the extended test of PR #5015 (AMX attention kernels for kv_mul 16,
# Muse Glimmer) on our half of the machine. Fork of exec/glimmer-20261016/chain.sh. Steps, each with a marker under RES
# (resume = relaunch; done steps are skipped):
#   B builds     : build.sh twice, in parallel (TAG=g16b = the PR merge base BASE_SHA, TAG=g16h = the PR head HEAD_SHA),
#                  same recipe; waits for RES/build-g16b.done and build-g16h.done = ok.
#   T tests      : tests.sh (the head's three AMX test binaries + the kill-switch repeat + the preservation check against the
#                  base build). A failure is recorded in RES/tests.done and the chain log and the chain CONTINUES (the
#                  measurements are the goal; the same commit passed these tests on 2026-10-16 and in CI).
#   I identity   : smoke.sh per cell of IDENTITY_CELLS (1 user, temperature 0, pay-for-determinism, 256 tokens): arms base,
#                  head, head2, headoff; the must-match pairs per cell are in the table. Summary RES/identity.txt; marker identity.done.
#   D campaign   : campaign.sh (cells x arms base/head x REPS, TRON_ATTN_STATS=1 in both arms, SKIP_SERVING_UP=1).
#   E margin     : margin.sh when the Glimmer CPU identity cell shows head (AMX) and base (AVX) differing and the clock is
#                  before E_NOT_AFTER (two teacher-forced records runs, tens of GB each; the issue #4444 near-tie measurement).
#   R report     : gen_report.py -> RES/results.md + results.json; exec/sync4424-20261002/summarize.py -> RES/summary.md.
# Deadline: no run starts after DEADLINE_HHMM (01:30 UTC; the pre-CI hold is 01:40-03:45 UTC). A campaign that stops at the
# deadline is resumed after NOT_BEFORE (default 2026-10-19T13:30:00Z, after the nightly), done runs skipped. Production
# serving (taken down through platformd by the campaign functions when idle) is brought back before a long sleep and at exit.
# Usage (on 3bda): [BASE_SHA=...] [HEAD_SHA=...] [NOT_BEFORE=2026-10-19T13:30:00Z] [STEPS="B T I D E R"] [REPS=4] [CELLS="<keys>"] [E_MIN_HOURS=3] bash chain2.sh
# Log: exec/logs/glimext-20261018-chain.log; status: exec/logs/glimext-20261018-chain.status; marker RES/chain.done.
# Words: the lease = /run/lock/systems-test-ci.lease (nightly CI); our half = socket 1 + cards 90/93/b9/bc; base = main
# 6198824246 (without PR #5015); head = 5061623a34 (with PR #5015); headoff = head with the kill switch TRON_AMX_DISABLE=1.
# Never edit this file while it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/glimext-20261018
NAME=${NAME:-glimext-20261018}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
STATUS=$EXEC/logs/$NAME-chain.status
BASE_SHA=${BASE_SHA:-61988242460342b26f153ae5e05ec0b294174904}
HEAD_SHA=${HEAD_SHA:-5061623a346ba5e8d22a6de8b3ab4cc058023214}
export NOT_BEFORE=${NOT_BEFORE:-2026-10-19T13:30:00Z}
DEADLINE_HHMM=${DEADLINE_HHMM:-0130}
STEPS=${STEPS:-"B T I D E R"}
E_NOT_AFTER=${E_NOT_AFTER:-2026-12-31T00:00:00Z}   # absolute bound for step E (optional); the relative bound below is the one that matters
E_MIN_HOURS=${E_MIN_HOURS:-3}                     # step E starts only when at least this many hours remain before the deadline
RT_BASE=/var/tmp/jhan/tron-g16b/gen/runtron.g16b
RT_HEAD=/var/tmp/jhan/tron-g16h/gen/runtron.g16h
export RT_BASE RT_HEAD
KSYM_BASE='amx_attn_h128g4(17qk_rowmajor_128x4|18pack_q_group_128x4|21weights_times_v_128x4)E'; KSYM_BASE_N=4
KSYM_HEAD='amx_attn_h128g4(17qk_rowmajor_128x4|18pack_q_group_128x4|21weights_times_v_128x4)ILm(4|16)E'; KSYM_HEAD_N=8
MAX_CAMPAIGN_PASSES=${MAX_CAMPAIGN_PASSES:-3}
export REPS=${REPS:-4} ARMS=${ARMS:-"base head"}
export SKIP_SERVING_UP=1
[ -n "${CELLS_ALL:-}" ] && export CELLS_ALL     # the default cell table lives in campaign.sh
export CELLS=${CELLS:-}
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
# identity cells: key|model|tp|attn|prompt|must-match pairs (space separated a:b). head:head2 = the A/A control everywhere.
# llama (kv_mul 4): base and head run the same AMX kernel -> head:base must match. qwen and gpt-oss (FPGA attention): the PR
# does not touch their path -> head:base must match. Glimmer: head (AMX on the 39 sliding layers) against base (AVX) is
# expected to differ at a near tie (issue #4444) -> informational; the kill switch must give base's tokens -> headoff:base.
IDENTITY_CELLS=${IDENTITY_CELLS:-$'l8b-tp2-cpu-p1024|llama-3.1-8b-instruct-good-tp2|2|cpu|1024|head:head2 head:base
q4b-tp2-fpga-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|fpga|1024|head:head2 head:base
gptoss-tp4-fpga-p1024|ingested-gpt-oss-120b-tp4|4|fpga|1024|head:head2 head:base
glm-tp2-fpga-p1024|ingested-meta-models--Muse-Glimmer-30B-tp2|2|fpga|1024|head:head2 headoff:base
glm-tp2-cpu-p1024|ingested-meta-models--Muse-Glimmer-30B-tp2|2|cpu|1024|head:head2 headoff:base
glm-tp2-fpga-p2048|ingested-meta-models--Muse-Glimmer-30B-tp2|2|fpga|2048|head:head2 headoff:base
glm-tp4-fpga-p1024|ingested-meta-models--Muse-Glimmer-30B-tp4|4|fpga|1024|head:head2 headoff:base'}
MARGIN_CELL=${MARGIN_CELL:-glm-tp2-cpu-p1024}
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
machine_line() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) lease=$(ci_lease_busy 600 && echo busy || echo clear) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | tr '\n' ' ') marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
nb=$(date -u -d "$NOT_BEFORE" +%s 2>/dev/null) || { echo "$(ts) bad NOT_BEFORE '$NOT_BEFORE'; not starting"; exit 1; }
ena=$(date -u -d "$E_NOT_AFTER" +%s 2>/dev/null) || { echo "$(ts) bad E_NOT_AFTER '$E_NOT_AFTER'; not starting"; exit 1; }
case $DEADLINE_HHMM in ''|*[!0-9]*) echo "$(ts) DEADLINE_HHMM='$DEADLINE_HHMM' is not HHMM digits; not starting"; exit 1 ;; esac
DEADLINE_HHMM=$((10#$DEADLINE_HHMM))
export DEADLINE_HHMM   # campaign.sh, smoke.sh and margin.sh read it (digits again after the 10# step; printf below keeps 4 digits)
DEADLINE_HHMM=$(printf '%04d' "$DEADLINE_HHMM")
next_deadline() {  # the next occurrence of DEADLINE_HHMM UTC after now
  local e; e=$(date -u -d "today $(printf '%02d:%02d' $((10#$DEADLINE_HHMM / 100)) $((10#$DEADLINE_HHMM % 100)))" +%s)
  [ "$e" -gt "$(date -u +%s)" ] || e=$((e + 86400)); echo "$e"
}
DEADLINE_EPOCH=$(next_deadline)
exec {CHAIN_LOCK_FD}>"/var/tmp/jhan/$NAME.chain.lock"
flock -n "$CHAIN_LOCK_FD" || { echo "$(ts) another chain.sh holds /var/tmp/jhan/$NAME.chain.lock; exit"; exit 1; }
rm -f "$RES/chain.done"
echo "=== $NAME chain started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') on $(hostname) BASE_SHA=$BASE_SHA HEAD_SHA=$HEAD_SHA NOT_BEFORE=$NOT_BEFORE DEADLINE_HHMM=$DEADLINE_HHMM STEPS=[$STEPS] REPS=$REPS ARMS=[$ARMS] CELLS=[${CELLS:-all}] E_NOT_AFTER=$E_NOT_AFTER deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) ==="
echo "$(ts) machine: $(machine_line)"
wait_for() { local label=$1 waited=0; shift; until "$@"; do [ $waited = 0 ] && { status "waiting: $label"; waited=1; }; sleep 60; done; [ $waited = 1 ] && echo "$(ts) $label: condition met"; return 0; }
not_before_passed() { [ "$(date -u +%s)" -ge "$nb" ]; }
sleep_until_not_before() {  # after a missed deadline: NOT_BEFORE as configured, or one hour from now when it is already past
  if not_before_passed; then nb=$(( $(date -u +%s) + 3600 )); NOT_BEFORE=$(date -u -d @"$nb" +%FT%TZ); echo "$(ts) NOT_BEFORE already passed; next attempt not before $NOT_BEFORE (one hour from now)"; fi
  serving_restore
  wait_for "NOT_BEFORE $NOT_BEFORE" not_before_passed
  DEADLINE_EPOCH=$(next_deadline); echo "$(ts) deadline for the next window: $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ)"
}
slot_free() { ! preci_hold && ! ci_lease_busy 600 && ! other_user_active 2>/dev/null && ! blackout_active; }
wait_slot() { wait_for "$1: pre-CI hold, CI lease busy (600 s grace), another person active or blackout" slot_free; echo "$(ts) $1 may start: $(machine_line)"; }
past_deadline() { [ "$(date -u +%s)" -ge "$DEADLINE_EPOCH" ]; }
# Production serving: the campaign functions mark every takeover (RES/serving-taken-down.marker); this chain brings serving
# back before a long sleep, after the last machine step and on exit.
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
  if python3 "$C/gen_report.py" "$RES" >"$RES/results.md" 2>"$RES/gen_report.err"; then
    echo "$(ts) report written: $RES/results.md ($(wc -l <"$RES/results.md") lines), $RES/results.json"
  else
    echo "$(ts) gen_report.py FAILED: $(tail -3 "$RES/gen_report.err" | tr '\n' ' ')"
  fi
  if [ -s "$RES/rt-results.txt" ]; then
    WEDPERF_ARMS="base head" WEDPERF_PAIRS="head:base" SUMMARY_TITLE="# $NAME summary (base = PR #5015 merge base, main 6198824246; head = PR #5015 head 5061623a34; attn = cpu or fpga)" \
      python3 "$EXEC/sync4424-20261002/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && echo "$(ts) summary written: $RES/summary.md" || echo "$(ts) summarize.py FAILED: $(tail -2 "$RES/summary.err" | tr '\n' ' ')"
  fi
}
build_settled() { local m; m=$(cat "$RES/build-$1.done" 2>/dev/null); [ "$m" = ok ] || [ "${m#failed}" != "$m" ]; }
builds_settled() { build_settled g16b && build_settled g16h; }
smoke_field() { local line; line=$(grep -m1 "^$1|" <<<"$IDENTITY_CELLS") || return 1; cut -d'|' -f"$2" <<<"$line"; }
first_diff_step() {  # $1 smoke dir: the 0-based index of the first head-vs-base difference, or "identical", or ""
  local l; l=$(grep -E '^head vs base: ' "$1/smoke.txt" 2>/dev/null | tail -1)
  case $l in *identical*) echo identical ;; *"first difference at generated token "*) sed -E 's/.*first difference at generated token ([0-9]+).*/\1/' <<<"$l" ;; *) echo "" ;; esac
}
for step in $STEPS; do
  case $step in
    B)
      if [ "$(cat "$RES/build-g16b.done" 2>/dev/null)" = ok ] && [ "$(cat "$RES/build-g16h.done" 2>/dev/null)" = ok ] && [ -x "$RT_BASE" ] && [ -x "$RT_HEAD" ] \
         && [ "$(git -C /var/tmp/jhan/tron-g16b rev-parse HEAD 2>/dev/null)" = "$BASE_SHA" ] && [ "$(git -C /var/tmp/jhan/tron-g16h rev-parse HEAD 2>/dev/null)" = "$HEAD_SHA" ]; then echo "$(ts) step B already done: both builds ok"; continue; fi
      status "step B: builds (g16b = $BASE_SHA, g16h = $HEAD_SHA)"
      # build.sh holds a per-tag lock: a copy launched while another runs exits at once and leaves the marker alone
      [ "$(cat "$RES/build-g16b.done" 2>/dev/null)" = ok ] || { env TAG=g16b SHA="$BASE_SHA" KSYM_RE="$KSYM_BASE" KSYM_N=$KSYM_BASE_N bash "$C/build.sh" & }
      [ "$(cat "$RES/build-g16h.done" 2>/dev/null)" = ok ] || { env TAG=g16h SHA="$HEAD_SHA" KSYM_RE="$KSYM_HEAD" KSYM_N=$KSYM_HEAD_N bash "$C/build.sh" & }
      wait_for "step B: build markers build-g16b.done and build-g16h.done" builds_settled
      wait   # the background build processes
      for t in g16b g16h; do m=$(cat "$RES/build-$t.done"); echo "$(ts) step B: build $t marker [$m]"; [ "$m" = ok ] || fail_chain "step B: build $t [$m], see $EXEC/logs/$NAME-build-$t.log"; done
      [ -x "$RT_BASE" ] && [ -x "$RT_HEAD" ] || fail_chain "step B: a binary is missing although the markers are ok"
      [ "$(git -C /var/tmp/jhan/tron-g16b rev-parse HEAD 2>/dev/null)" = "$BASE_SHA" ] || fail_chain "step B: tron-g16b is not at $BASE_SHA"
      [ "$(git -C /var/tmp/jhan/tron-g16h rev-parse HEAD 2>/dev/null)" = "$HEAD_SHA" ] || fail_chain "step B: tron-g16h is not at $HEAD_SHA" ;;
    T)
      if [ "$(cat "$RES/tests.done" 2>/dev/null)" = ok ]; then echo "$(ts) step T already done: ok"; continue; fi
      status "step T: tests.sh"
      env SHA="$HEAD_SHA" bash "$C/tests.sh"; trc=$?
      m=$(cat "$RES/tests.done" 2>/dev/null); echo "$(ts) step T result: rc=$trc marker=[$m]"
      [ "$m" = ok ] || echo "$(ts) step T: TESTS NOT OK [$m] (see $RES/tests.txt); the chain continues with the measurements, the report flags it" ;;
    I)
      if [ "$(cat "$RES/identity.done" 2>/dev/null)" = ok ]; then echo "$(ts) step I already done: ok"; continue; fi
      [ -x "$RT_BASE" ] && [ -x "$RT_HEAD" ] || fail_chain "step I: binaries missing (step B not done)"
      ipass=0
      while :; do
        ipass=$((ipass + 1))
        status "step I: identity smokes (pass $ipass)"
        verdict=ok
        while IFS='|' read -r key model tp attn prompt must; do
          [ -n "$key" ] || continue
          sm=$RES/smoke/$key
          if [ "$(cat "$sm/smoke.done" 2>/dev/null)" = ok ]; then echo "$(ts) step I: $key already ok"; continue; fi
          past_deadline && { echo "$(ts) step I: deadline before $key"; verdict=deadline; break; }
          status "step I: smoke $key"
          env KEY="$key" MODEL="$model" TP="$tp" ATTN="$attn" PROMPT="$prompt" LEN=256 MUST_MATCH="$must" bash "$C/smoke2.sh" </dev/null
          v=$(cat "$sm/smoke.done" 2>/dev/null)
          # the current pass only: the lines after the previous SMOKE-VERDICT line (smoke.txt is appended to across reruns)
          nfail=$(tac "$sm/smoke.txt" 2>/dev/null | awk '/^SMOKE-VERDICT/{c++; next} c==1 && /^SMOKE-FAILED/{n++} END{print n+0}')
          echo "$(ts) step I: $key -> [$v] failed-lines=$nfail; $(grep -E ' vs .*(identical|first difference)' "$sm/smoke.txt" | tail -4 | cut -c1-140 | tr '\n' ';')"
          if [ "$v" != ok ] && { past_deadline || tac "$sm/smoke.txt" 2>/dev/null | awk '/^SMOKE-VERDICT/{c++; next} c==1 && /^SMOKE-FAILED arm=[a-z0-9]*: deadline/{f=1} END{exit !f}'; }; then
            echo "$(ts) step I: deadline during $key"; verdict=deadline; break
          fi
          [ "$v" = ok ] && [ "${nfail:-0}" = 0 ] || verdict="failed-$key"
        done <<<"$IDENTITY_CELLS"
        {
          echo "# identity $(ts): per cell the LAST verdict and pair lines of smoke/<key>/smoke.txt (1 user, temperature 0, pay-for-determinism, seed 1, 256 tokens, --dont-stop)"
          while IFS='|' read -r key model tp attn prompt must; do
            [ -n "$key" ] || continue
            echo "## $key model=$model tp=$tp attn=$attn prompt=$prompt must_match=[$must] verdict=$(cat "$RES/smoke/$key/smoke.done" 2>/dev/null || echo missing)"
            grep -E '^(smoke token rows|[a-z0-9]+ vs [a-z0-9]+:|SMOKE-FAILED|SMOKE-STOPPED)' "$RES/smoke/$key/smoke.txt" 2>/dev/null | tail -8
          done <<<"$IDENTITY_CELLS"
        } >"$RES/identity.txt"
        echo "$verdict" >"$RES/identity.done"; echo "$(ts) step I pass $ipass result: [$verdict]"
        [ "$verdict" = deadline ] || break
        [ $ipass -lt "$MAX_CAMPAIGN_PASSES" ] || fail_chain "step I: deadline reached in $ipass passes (resume with STEPS='I D E R')"
        status "step I: deadline; sleeping until NOT_BEFORE $NOT_BEFORE, then resuming (done cells are skipped)"
        sleep_until_not_before; wait_slot "step I pass $((ipass + 1))"
      done ;;
    D)
      if [ "$(cat "$EXEC/logs/$NAME.done" 2>/dev/null)" = ok ]; then echo "$(ts) step D already done: ok"; continue; fi
      [ -x "$RT_BASE" ] && [ -x "$RT_HEAD" ] || fail_chain "step D: binaries missing (step B not done)"
      pass=0
      while :; do
        pass=$((pass + 1))
        past_deadline && { status "step D: past the deadline; sleeping until NOT_BEFORE $NOT_BEFORE"; sleep_until_not_before; wait_slot "step D pass $pass"; }
        status "step D: campaign pass $pass (arms [$ARMS] x REPS $REPS; cells ${CELLS:-all of the campaign.sh table})"
        env NAME="$NAME" bash "$C/campaign.sh"
        m=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null); echo "$(ts) step D pass $pass result: [$m]"
        case $m in
          ok) break ;;
          ok-with-*) echo "$(ts) step D: some runs failed; relaunch with STEPS='D E R' to retry them"; break ;;
          deadline)
            [ $pass -lt "$MAX_CAMPAIGN_PASSES" ] || { report_step; fail_chain "step D: deadline reached in $pass passes (partial report written; resume with STEPS='D E R')"; }
            status "step D: campaign stopped at the deadline; sleeping until NOT_BEFORE $NOT_BEFORE, then resuming (done runs are skipped)"
            sleep_until_not_before; wait_slot "step D pass $((pass + 1))" ;;
          *) report_step; fail_chain "step D ended with marker [$m] (partial report written; resume with STEPS='D E R')" ;;
        esac
      done ;;
    E)
      if [ "$(cat "$RES/margin/margin.done" 2>/dev/null)" = ok ]; then echo "$(ts) step E already done: ok"; continue; fi
      sm=$RES/smoke/$MARGIN_CELL; fd=$(first_diff_step "$sm")
      if [ -z "$fd" ]; then echo "$(ts) step E skipped: no head-vs-base line for $MARGIN_CELL (step I not done?)"; echo "skipped-no-identity" >"$RES/margin.done"
      elif [ "$fd" = identical ]; then echo "$(ts) step E skipped: head and base identical in $MARGIN_CELL (nothing to explain)"; echo "skipped-identical" >"$RES/margin.done"
      elif [ "$(date -u +%s)" -ge "$ena" ]; then echo "$(ts) step E skipped: past E_NOT_AFTER $E_NOT_AFTER (relaunch with STEPS='E R' E_NOT_AFTER=<later> when the machine is free)"; echo "skipped-late" >"$RES/margin.done"
      elif [ $(( DEADLINE_EPOCH - $(date -u +%s) )) -lt $(( E_MIN_HOURS * 3600 )) ]; then echo "$(ts) step E skipped: less than $E_MIN_HOURS h before the deadline $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) (relaunch with STEPS='E R' in a free window)"; echo "skipped-late" >"$RES/margin.done"
      elif past_deadline; then echo "$(ts) step E skipped: past the deadline"; echo "skipped-deadline" >"$RES/margin.done"
      else
        status "step E: margin probe (first free-running difference at index $fd -> step $((fd + 1)))"
        env FORCED="$sm/base.tokens" MARK=$((fd + 1)) MODEL="$(smoke_field "$MARGIN_CELL" 2)" TP="$(smoke_field "$MARGIN_CELL" 3)" PROMPT="$(smoke_field "$MARGIN_CELL" 5)" LEN=256 END_BY="$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ)" bash "$C/margin.sh"
        cp "$RES/margin/margin.done" "$RES/margin.done" 2>/dev/null || echo "failed-no-marker" >"$RES/margin.done"
        echo "$(ts) step E result: [$(cat "$RES/margin.done")] $(grep -E '^(MARGIN|MARKED)' "$RES/margin/margin.txt" 2>/dev/null | tail -2 | cut -c1-300 | tr '\n' ';')"
      fi ;;
    R)
      status "step R: report"; report_step ;;
    *) echo "$(ts) unknown step $step" ;;
  esac
done
serving_restore
echo "ok" >"$RES/chain.done"; status "chain finished"
echo "=== $NAME chain finished $(ts): B=$(cat "$RES/build-g16b.done" 2>/dev/null)/$(cat "$RES/build-g16h.done" 2>/dev/null) T=$(cat "$RES/tests.done" 2>/dev/null) I=$(cat "$RES/identity.done" 2>/dev/null) D=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null) E=$(cat "$RES/margin.done" 2>/dev/null) R=$([ -s "$RES/results.md" ] && echo written || echo missing) ==="
