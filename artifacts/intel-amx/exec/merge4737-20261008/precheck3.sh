#!/usr/bin/env bash
# merge4737 AFTER-CHECK, tonight's run (precheck3.sh = precheck2.sh with NOT_BEFORE now, END_BY 01:30Z and Bill's marker taken
# for the whole-machine steps; precheck2.sh, runs ON delphi-3bda, detached): the correctness steps of the whole-machine window
# of 2026-10-09, run AFTER the pr4424ci-20261009 perf campaign (client on claude-box) wrote its end marker. (precheck.sh
# raced the campaign: both waited for the same lease event and the campaign passed its marker test before the marker
# existed; precheck.sh was stopped at 15:1x UTC while blocked on the campaign flock.)
#   new  = the merged PR 4424 head (COMMIT, built by build-test.sh into /var/tmp/jhan/tron-m4737, runtron.m4737)
#   head = the PR 4424 head before this merge (45e6bb266d, /var/tmp/jhan/tron-savek2/gen/runtron.savek2)
#   base = main be0d5565b3 (the main the branch is synced to; /var/tmp/jhan/tron-main1007/gen/runtron.main1007)
# Steps (every step waits for the CI lease with 600 s grace and for other people's activity to end; bill is excluded):
#   0.  wait until the campaign's end marker exists (exec/results/pr4424ci-20261009/.done*, written after its restore
#       and release), then the lease; no step starts after END_BY (the next nightly takes the lease ~03:38 UTC).
#       The marker /var/tmp/jhan/pr4424ci-precheck.running is held while this chain runs.
#   1.  production serving down through platformd (exec/q4b-fpga-20260921/dut.sh serving-down, 5-min idle test).
#   2.  the whole host test suite in the VNNI build tree (make build-test-host + make test-host, fake device, our half;
#       exec/i4525-20260922/host-suite.sh). References: 2026-10-08 sync chain 93 passed / 1 skipped / 1 failed
#       (t_proxy_llama31: missing venv, machine not code); 2026-10-06 savek chain 89/1/0.
#   3.  token identity (runtron, 1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens, qwen3-4b tp2,
#       exec/sync4424-20261002/smoke.sh): cpu p1024 arms base head new new2 newoff; fpga p1024 base head new;
#       cpu p8192 base head new. Must match: new == new2 (A/A), newoff == new (AMX on vs the kill switch).
#       Informational: new vs head (expected to differ under CPU attention: the row-major tail block is scored by the
#       dotter, the previous head scored it with the VNNI reader; expected identical under FPGA attention), new vs
#       base (expected to differ from generated token 52, issue 4444).
#   3b. runtron performance (exec/sync4424-20261002/campaign.sh): qwen3-4b tp2, 8 users, 256 tokens, CPU attention,
#       prompts 1024 and 8192, arms base and new interleaved, 3 repetitions (results exec/results/m4737-E-cpu/).
#   4.  serving up again (the campaign cycles it per arm) and the marker removed; precheck.done = ok | failed-<step>
#       (the verdict covers steps 2 and 3; step 3b is a measurement).
# Usage (on 3bda): COMMIT=<full sha> [NOT_BEFORE=2026-10-10T13:00:00Z] [END_BY=2026-10-11T01:40:00Z] bash precheck2.sh
# (see launch-precheck2.sh). Smokes with tokens on disk, runtron runs with results and done cells are skipped by the
# step scripts, so a rerun completes what the first chain left.
# Step order here: serving down, smokes (3), runtron cells, host suite, serving up (the cells and smokes feed the PR
# body; the host suite is last so a late end costs it first).
# Never edit this file while it runs (bash re-reads a running script; NFS stale-handle trap).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=merge4737-precheck
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
COMMIT=${COMMIT:?COMMIT (full sha of the merged branch) is required}
NOT_BEFORE=${NOT_BEFORE:-2026-10-09T22:50:00Z}
END_BY=${END_BY:-2026-10-10T01:30:00Z}
CAMP=$EXEC/results/pr4424ci-20261009
MARKER=/var/tmp/jhan/pr4424ci-precheck.running
WT=/var/tmp/jhan/tron-m4737
export RT_NEW=$WT/gen/runtron.m4737
export RT_HEAD=/var/tmp/jhan/tron-savek2/gen/runtron.savek2
export RT_BASE=/var/tmp/jhan/tron-main1007/gen/runtron.main1007
export ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_baseoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
DUT=$EXEC/q4b-fpga-20260921/dut.sh
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy or another person active"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
finish() { rm -f "$MARKER"; echo "$(ts) marker removed"; [ "${MARKER_TAKEN:-0}" = 1 ] && { bash "$EXEC/bill-share.sh" release 2>&1 | tail -1; echo "$(ts) Bill marker released"; }; }
trap finish EXIT
exec >>"$LOG" 2>&1
rm -f "$RES/precheck.done"
echo "=== $NAME (precheck2) started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT NOT_BEFORE=$NOT_BEFORE END_BY=$END_BY ==="
[ -x "$RT_NEW" ] && [ "$(git -C "$WT" rev-parse HEAD)" = "$COMMIT" ] || { step_done start "new binary $RT_NEW missing or $WT not at $COMMIT: abort"; echo failed-start >"$RES/precheck.done"; exit 1; }
[ -x "$RT_HEAD" ] && [ -x "$RT_BASE" ] || { step_done start "reference binary missing: abort"; echo failed-start >"$RES/precheck.done"; exit 1; }

# ---- 0. NOT_BEFORE, the campaign's end marker, the lease, our marker ----
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
nb=$(date -u -d "$NOT_BEFORE" +%s)
while [ "$(date -u +%s)" -lt "$nb" ]; do left=$(( nb - $(date -u +%s) )); [ "$left" -gt 1800 ] && left=1800; echo "$(ts) waiting: NOT_BEFORE $NOT_BEFORE ($((left/60)) min)"; sleep "$left"; done
# precheck.sh (the raced first chain) may still be running its steps: wait until it is gone
while pgrep -u jhan -f 'merge4737-20261008/precheck[.]sh' >/dev/null; do echo "$(ts) waiting: precheck.sh still runs"; sleep 300; done
# whole-machine steps: take Bill's marker (refused while Bill is active: then stop here), release it at the end
MARKER_TAKEN=0
tout=$(bash "$EXEC/bill-share.sh" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) step_done 0 "Bill marker not taken (rc $trc): abort"; echo failed-0-marker >"$RES/precheck.done"; exit 1;; esac
until [ -e "$CAMP/.done" ] || [ -e "$CAMP/.done-with-failures" ] || [ -e "$CAMP/.done-aborted" ]; do
  past_end && { step_done 0 "END_BY $END_BY reached while the campaign still runs: abort"; echo failed-0-end-by >"$RES/precheck.done"; exit 1; }
  echo "$(ts) waiting: campaign end marker absent ($(cat "$CAMP/.status" 2>/dev/null | cut -c1-120))"; sleep 300
done
echo "$(ts) campaign end marker: $(ls "$CAMP"/.done* 2>/dev/null | xargs -n1 basename | tr '\n' ' ') outcome: $(cat "$CAMP/outcome.txt" 2>/dev/null | cut -c1-200)"
sleep 60   # the campaign's release_lock and bill release follow the marker by seconds
wait_slot "step 1"
touch "$MARKER"; echo "$(ts) marker $MARKER created (the perf campaign waits for it to disappear)"
echo "$(ts) machine: lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"

# ---- 1. serving down ----
past_end && { step_done 1 "skipped: past END_BY"; echo failed-1-end-by >"$RES/precheck.done"; exit 1; }
if rinzler_active; then
  IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); the steps below retry through the guard"
fi
step_done 1 "serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo)"

# ---- 3. token identity ----
export MUST_MATCH="new:new2 newoff:new"
export NAME DEADLINE_HHMM=0145
for spec in "cpu 1024 base head new new2 newoff" "fpga 1024 base head new" "cpu 8192 base head new"; do
  past_end && { step_done 3 "skipped $spec: past END_BY"; continue; }
  set -- $spec; attn=$1; prompt=$2; shift 2
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$EXEC/sync4424-20261002/smoke.sh"
  step_done 3 "$attn p$prompt: $(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null)"
done

# ---- 3b. runtron performance: base vs new, CPU attention, 8 users, 256 tokens, 3 repetitions interleaved ----
#       (the Measurements rows of the PR body: the final head against the main it is synced to; the FPGA-attention
#        cells come from the campaign's nightly configs)
S=$EXEC/sync4424-20261002
cells() { local p out=""; for p in "$@"; do out+="q3-4b-tp2-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp2|2|8|$p"$'\n'; done; printf '%s' "${out%$'\n'}"; }
run_e() {  # $1 name $2 attns $3 arms $4 pairs $5.. prompts
  local name=$1 attns=$2 arms=$3 pairs=$4; shift 4
  NAME=$name CELLS_ALL="$(cells "$@")" ARMS="$arms" ATTNS="$attns" REPS=3 DEADLINE_HHMM=0145 \
    WEDPERF_ARMS="$arms" WEDPERF_PAIRS="$pairs" bash "$S/campaign.sh"
  step_done "$name" "$(cat "$EXEC/logs/$name.done" 2>/dev/null)"
}
past_end && step_done 3b "skipped: past END_BY" || run_e m4737-E-cpu cpu "base new" "new:base" 1024 8192

# ---- 2. host suite (last: a late end costs it first) ----
if past_end; then step_done 2 "skipped: past END_BY"; else
wait_slot "step 2"
env RES="$RES" WT="$WT" SUFFIX=m4737 bash "$EXEC/i4525-20260922/host-suite.sh"
step_done 2 "$(cat "$RES/host-suite-m4737.done" 2>/dev/null) $(grep -E '^(build-test-host|test-host) rc=|passed|skipped|failed' "$RES/host-suite-m4737.txt" 2>/dev/null | tr '\n' ' ' | cut -c1-200)"
fi

# ---- 4. serving up, verdict ----
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$DUT" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
h=$(cat "$RES/host-suite-m4737.done" 2>/dev/null)
s1=$(cat "$RES/smoke/cpu-p1024/smoke.done" 2>/dev/null); s2=$(cat "$RES/smoke/fpga-p1024/smoke.done" 2>/dev/null); s3=$(cat "$RES/smoke/cpu-p8192/smoke.done" 2>/dev/null)
if [ "$h" = ok ] && [ "$s1" = ok ] && [ "$s2" = ok ] && [ "$s3" = ok ]; then echo ok >"$RES/precheck.done"; else echo "failed host=$h smoke=$s1/$s2/$s3" >"$RES/precheck.done"; fi
step_done end "$(cat "$RES/precheck.done")"
echo "=== $NAME finished $(ts): $(cat "$RES/precheck.done") ==="
