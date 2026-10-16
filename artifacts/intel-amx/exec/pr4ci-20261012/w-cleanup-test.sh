#!/usr/bin/env bash
# Fixture test of campaign.sh's restore_and_release, on_signal, abort_early, the takeover path and the retry block
# (PR4-handoff.md section 5.3, "Campaign W": Marker ownership, The takeover path, The recovered-pass count), with local
# stubs, never against the live machine. In the style of exec/pr3-20261012/cleanup-test.sh.
#
# How it works: campaign.sh is copied into a temp dir with exactly five constant lines rewritten (NAME, H, RES, ST, PY;
# the diff is counted and printed), a stub `ssh` first on PATH answers every remote command (dut.sh, bill-share.sh,
# stat, flock, test -e, pgrep, cat chain.done) and logs each call to calls.log and to the campaign's own
# status-history.log (one ordered stream of statuses and calls), and a stub python runs in place of the driver
# (st_ci_perf.py) and of summarize.py: a plan file gives the driver's outcome per invocation (ok | fail | rc9 | sleep,
# with the suffix " busy" = the stub CI lease turns busy after that run, and " arm-hwattn-clear" / " arm-ensure-base" =
# from that run on, the stub's hwattn-clear / ensure-base turns the lease busy as a side effect: the restore-phase
# triggers of cases 7a and 7b). Every case gets a fresh results dir.
# Cases (21; the handoff's acceptance list, plus 11 to 15):
#    1  SIGTERM while W waits for the CI lease             -> no bill-share.sh call, no dut.sh call except lease-free
#   1b  SIGTERM while W waits for the hand-off marker      -> the same
#   2a  abort_early (DEADLINE_START past) in the lease wait -> the same
#   2b  abort_early in the hand-off marker wait            -> the same
#    3  normal completion after the marker take (PASSES=base) -> exactly one `bill release`, the full restore, .done
#    4  SIGTERM after the marker take and after the first pass -> the full restore and exactly one release, .done-aborted
#    5  takeover between passes (lease busy before tag 2) -> no dut.sh mutation after the busy reading, restore-deferred.txt, no release
#    6  driver rc 9 (lease busy during a pass)            -> the same
#   7a  lease turns busy between hwattn-clear and ensure-base -> the same (hwattn-clear done, nothing after)
#   7b  lease turns busy between ensure-base and serving-down -> the same (ensure-base done, no serving call)
#    8  a free lease (PASSES="base target", chain.done = the host-suite exception) -> the normal restore, one release, .done
#    9  first attempt fails, the repeat succeeds           -> .done and "recovered passes: base-pass1"
#   10  two failed attempts                               -> .done-with-failures, "recovered passes: none"
#   11  chain.done not ok (and 11b: missing)              -> abort before the peer wait, no bill-share.sh call, no mutation
#   12  EXPECTED_BASE empty                               -> refused before any ssh call
#   13  abort in the preflight after the marker take      -> one release, no dut.sh mutation
#   14  the fork's scope: SW8K=0 (default), PASSES="base target target base", NEED_FLOOR_S=1800 -> exactly the four full-pass
#       tags, no hwattn-off, a restore without hwattn-clear, FULL_CONFIGS = subset3.json in the driver's environment
#  14b  SW8K=1 with PASSES="base target target base"      -> the eight tags (full pass then sw8k cell per arm pass), in order
#  15a  NEED_FLOOR_S=1800 with 40 min left before DRIVER_END_BY -> the pass starts
#  15b  the default floor (6600 s) with 40 min left             -> "not enough time before DRIVER_END_BY", no DUT change, one release
# Output: w-cleanup-test.log next to this script. Exit 0 only when every case passes. Runs about 3 min (the campaign's
# own `sleep 20` after each package switch and the 1-s polls are real).
set -u
D=$(cd "$(dirname "$0")" && pwd)
TMPROOT=/tmp/claude-0; [ -d "$TMPROOT" ] && [ -w "$TMPROOT" ] || TMPROOT=/tmp
T=$(mktemp -d "$TMPROOT/w-cleanup-test.XXXXXX")
LOGF=$D/w-cleanup-test.log
: >"$LOGF"
NIGHTLY_V=2026.10.13-0badf00d; NIGHTLY_SHA=$(printf 'a%.0s' $(seq 64))
BASE_V=2026.10.13-72308ec9-jhan-pr4ci-base; BASE_SHA=$(printf 'b%.0s' $(seq 64))
TARGET_V=2026.10.13-cafebabe-jhan-pr4ci-target; TARGET_SHA=$(printf 'c%.0s' $(seq 64))
HOLDER_SLEEP=123457; DRIVER_SLEEP=611   # distinctive durations: the cleanup kills exactly these
mkdir -p "$T/bin" "$T/h/talos_stub" "$T/res"
cp "$D/sw8k.json" "$T/h/sw8k.json"; cp "$D/subset3.json" "$T/h/subset3.json"; : >"$T/h/st_ci_perf.py"; : >"$T/h/summarize.py"
# ---- the campaign copy: exactly five constant lines rewritten
sed -e 's|^NAME=pr4ci-20261012$|NAME=w-cleanup-test|' \
    -e "s|^H=/home/jhan/workspace/intel-AMX/exec/\$NAME$|H=$T/h|" \
    -e "s|^RES=/home/jhan/workspace/intel-AMX/exec/results/\$NAME$|RES=$T/res|" \
    -e "s|^ST=/home/jhan/workspace/ai-runs/systems_test$|ST=$T|" \
    -e "s|^PY=\$ST/.venv/bin/python$|PY=$T/bin/python-stub|" "$D/campaign.sh" >"$T/campaign.sh"
# ---- the stub ssh
{ echo '#!/usr/bin/env bash'; echo '# stub ssh of w-cleanup-test: logs every remote command and emulates the ones campaign.sh sends'; echo "T=$T"; } >"$T/bin/ssh"
cat >>"$T/bin/ssh" <<'STUB'
seq=$(( $(cat "$T/seq" 2>/dev/null || echo 0) + 1 )); echo "$seq" >"$T/seq"
while [ $# -gt 0 ]; do case $1 in -o) shift 2;; delphi-3bda) shift; break;; *) shift;; esac; done
CMD="$*"
log() { echo "$seq STUB $*" >>"$T/calls.log"; mkdir -p "$T/res"; echo "$(date -u +%FT%TZ) STUB $*" >>"$T/res/status-history.log"; }
case "$CMD" in
  *"dut.sh "*)
    rest=${CMD#*dut.sh }; pre=${CMD%%bash *}
    set -- $rest; sub=$1
    case $sub in
      lease-free) if [ -e "$T/lease-busy" ]; then log "dut.sh ${pre}$rest -> busy"; echo busy; exit 1; else log "dut.sh ${pre}$rest -> free"; echo free; exit 0; fi;;
    esac
    log "dut.sh ${pre}$rest"
    case $sub in
      installed) cat "$T/installed"; exit 0;;
      preflight) printf '== installed tron: %s\n== target build: status=ok deb=target.deb\n== installed rinzler IS the target build'"'"'s (must be no at preflight): no\n== config.env bytes (must be 0): %s\n== bill marker: absent\n' "$(cat "$T/installed")" "$(cat "$T/cfgbytes")"; exit 0;;
      save-base-deb) echo "dut: deb $2 already saved as ${3:-nightly.deb}"; exit 0;;
      ensure-base) echo "$2 $3" >"$T/installed"; echo "dut: nightly package installed and verified: $2"; [ -e "$T/busy-after-ensure-base" ] && touch "$T/lease-busy"; exit 0;;
      ensure-target) echo "__TARGET_V__ __TARGET_SHA__" >"$T/installed"; echo "dut: target package installed and verified"; exit 0;;
      hwattn-off) echo 14 >"$T/cfgbytes"; echo "dut: hwattn-off: config.env is now 14 bytes"; exit 0;;
      hwattn-clear) echo 0 >"$T/cfgbytes"; echo "dut: hwattn-clear: config.env is now 0 bytes"; [ -e "$T/busy-after-hwattn-clear" ] && touch "$T/lease-busy"; exit 0;;
      verify-env) echo "dut: verify-env ok"; exit 0;;
      serving-down) echo "dut: serving down"; exit 0;;
      serving-up) echo "dut: serving up"; exit 0;;
      memsnap) echo '{}'; exit 0;;
      *) echo "dut: unknown $sub"; exit 2;;
    esac;;
  *bill-share.sh*)
    sub=${CMD##* }; log "bill-share.sh $sub"
    case $sub in
      status) if [ -e "$T/marker-present" ]; then echo "marker present: Bill may use the first half"; else echo "marker absent: the whole machine is ours"; fi; exit 0;;
      take) [ -e "$T/bill-active" ] && { echo "take REFUSED: Bill is active"; exit 2; }; rm -f "$T/marker-present"; echo "take: removed the marker"; exit 0;;
      release) touch "$T/marker-present"; echo "release: created the marker"; exit 0;;
      *) exit 64;;
    esac;;
  true) log "true (wait_dut)"; exit 0;;
  *"flock -n "*" -c "*) log "hold_lock: flock holder"; echo "held pid 424242"; exec sleep __HOLDER_SLEEP__;;
  *"flock -n "*" true") log "release_lock: kill holder + flock test"; exit 0;;
  *"pkill -u jhan -f '^sleep"*) log "pkill orphan holders"; exit 0;;
  *"test -e "*) log "test -e hand-off marker"; [ -e "$T/precheck-present" ] && exit 0 || exit 1;;
  *"pgrep -u jhan -f"*) log "pgrep peers"; exit 1;;
  *"chain.done"*) log "cat chain.done"; cat "$T/chain.done" 2>/dev/null;;
  *"stat -c %s"*) log "stat config.env"; cat "$T/cfgbytes";;
  *) log "UNKNOWN: $CMD"; exit 0;;
esac
STUB
sed -i -e "s|__TARGET_V__|$TARGET_V|; s|__TARGET_SHA__|$TARGET_SHA|; s|__HOLDER_SLEEP__|$HOLDER_SLEEP|" "$T/bin/ssh"
# ---- the stub python: the driver (plan-driven) and summarize.py
{ echo '#!/usr/bin/env bash'; echo "T=$T"; } >"$T/bin/python-stub"
cat >>"$T/bin/python-stub" <<'STUB'
case $(basename "${1:-}") in
  summarize.py) echo "stub summary"; exit 0;;
  st_ci_perf.py) ;;
  *) echo "python-stub: unexpected $*" >&2; exit 2;;
esac
n=$(( $(cat "$T/drv-n" 2>/dev/null || echo 0) + 1 )); echo "$n" >"$T/drv-n"
plan=$(sed -n "${n}p" "$T/plan"); [ -n "$plan" ] || plan=ok
echo "stub driver run $n tag=${CI_MIMIC_ARM:-?} plan=$plan"
mkdir -p "$(dirname "$CI_MIMIC_OUT")"
case $plan in sleep*) echo "Perf test for cell-a"; sleep __DRIVER_SLEEP__ & p=$!; trap 'kill $p 2>/dev/null; exit 143' TERM; wait $p; exit 0;; esac
echo "Perf test for cell-a"
rc=0
case $plan in
  ok*) echo '{"raw": []}' >"$CI_MIMIC_OUT";;
  fail*) echo "FAILED_CONFIGS cell-b@8u-p1024"; rc=1;;
  rc9*) echo "STOP: CI lease busy"; rc=9;;
esac
case $plan in *busy*) touch "$T/lease-busy";; esac
case $plan in *arm-hwattn-clear*) touch "$T/busy-after-hwattn-clear";; *arm-ensure-base*) touch "$T/busy-after-ensure-base";; esac   # arm a restore-phase trigger after this run
exit $rc
STUB
sed -i -e "s|__DRIVER_SLEEP__|$DRIVER_SLEEP|" "$T/bin/python-stub"
chmod +x "$T/bin/ssh" "$T/bin/python-stub"
cleanup() { pkill -f "^sleep $HOLDER_SLEEP\$" 2>/dev/null; pkill -f "^sleep $DRIVER_SLEEP\$" 2>/dev/null; }
trap cleanup EXIT

# ---- helpers
now_plus() { date -u -d "@$(( $(date -u +%s) + $1 ))" +%FT%TZ; }
reset_state() {   # fresh results dir and stub state: the lease free, the hand-off marker absent, Bill's marker present, the nightly installed, chain.done ok
  rm -rf "$T/res"; mkdir -p "$T/res"; rm -f "$T/calls.log" "$T/seq" "$T/drv-n" "$T/lease-busy" "$T/precheck-present" "$T/busy-after-hwattn-clear" "$T/busy-after-ensure-base" "$T/bill-active"
  echo 0 >"$T/cfgbytes"; echo "$NIGHTLY_V $NIGHTLY_SHA" >"$T/installed"; touch "$T/marker-present"; echo ok >"$T/chain.done"; : >"$T/plan"
}
CPID=; RC=
start_campaign() {   # $@ = extra VAR=value for the campaign (a later assignment wins); the common knobs put the window around now.
  # SW8K=1 here (not the fork's default 0): cases 3 to 10 drive the config.env path (hwattn-off, hwattn-clear in the restore)
  # through the sw8k tag; case 14 runs the fork's default SW8K=0.
  env PATH="$T/bin:$PATH" NOT_BEFORE="$(now_plus -60)" DEADLINE_START="$(now_plus 3600)" PASS_DEADLINE="$(now_plus 7200)" DRIVER_END_BY="$(now_plus 14400)" \
      EXPECTED_BASE="$BASE_V" EXPECTED_BASE_SHA="$BASE_SHA" PASSES=base SW8K=1 "$@" bash "$T/campaign.sh" >"$T/run.log" 2>&1 &
  CPID=$!
}
wait_status() { local i; for i in $(seq 1 "$2"); do grep -q -- "$1" "$T/res/status-history.log" 2>/dev/null && return 0; sleep 1; done; return 1; }
finish() { wait "$CPID"; RC=$?; }
cnt() { local n; n=$(grep -c -- "$1" "$2" 2>/dev/null); echo "${n:-0}"; }   # 0 when the file is missing
n_calls() { cnt "$1" "$T/calls.log"; }
MUT='dut.sh \(IDLE_MIN=[0-9]* \)\?\(ensure-base\|ensure-target\|hwattn-off\|hwattn-clear\|serving-down\|serving-up\)'
dut_non_lease() { grep 'STUB dut.sh' "$T/calls.log" 2>/dev/null | grep -vc lease-free || true; }
muts_after_busy() {   # dut.sh mutations logged after the FIRST busy lease reading
  local b; b=$(grep -m1 -n 'lease-free -> busy' "$T/calls.log" | cut -d: -f1); [ -n "$b" ] || { echo "no-busy-reading"; return; }
  tail -n +"$((b+1))" "$T/calls.log" | grep -c -- "$MUT" || true
}
restore_tail() {   # the status-history lines after the last driver-rc / signal / passes-stopped / abort line (= the restore phase)
  local b; b=$(grep -n 'driver rc=\|SIGNAL received\|passes stopped\|ABORT:' "$T/res/status-history.log" | tail -1 | cut -d: -f1); tail -n +"$((${b:-0}+1))" "$T/res/status-history.log"
}
restore_seq() { restore_tail | grep -o 'STUB dut.sh \(IDLE_MIN=[0-9]* \)\?[a-z-]*' | sed 's/STUB //' | tr '\n' ';'; }   # the dut.sh sub-commands of the restore phase, in order
restore_seq_matches() { restore_seq | grep -q -- "$1"; }
restore_has() { restore_tail | grep -q -- "$1"; }
restore_lacks() { ! restore_tail | grep -q -- "$1"; }
lease_before_each_mutation() {   # in the restore phase every mutation's previous dut.sh line must be a free lease reading
  local prev="" line ok=yes
  while IFS= read -r line; do
    case $line in *"STUB dut.sh "*)
      if echo "$line" | grep -q -- "STUB $MUT"; then case $prev in *"lease-free -> free"*) ;; *) ok=no; echo "  mutation without a lease test right before it: $line (prev: $prev)";; esac; fi
      prev=$line;;
    esac
  done < <(restore_tail)
  [ $ok = yes ]
}
OK=; NOTES=
expect() { local what=$1; shift; if "$@"; then NOTES="$NOTES; $what ok"; else NOTES="$NOTES; $what FAILED"; OK=no; fi; }
begin() { OK=yes; NOTES="rc=$RC take=$(n_calls 'bill-share.sh take') release=$(n_calls 'bill-share.sh release') mutations=$(n_calls "$MUT") dut-non-lease=$(dut_non_lease)"; }
verdict() { echo "CASE $1: $NOTES -> $([ "$OK" = yes ] && echo PASS || echo FAIL)"; }
no_driver_left() { ! pgrep -f "^sleep $DRIVER_SLEEP\$" >/dev/null; }
FULL_RESTORE='dut.sh hwattn-clear;.*dut.sh ensure-base;.*dut.sh IDLE_MIN=5 serving-down;.*dut.sh serving-up;'

{
echo "=== w-cleanup-test $(date -u +%FT%TZ) in $T ==="
echo "campaign copy differs from $D/campaign.sh in $(diff "$D/campaign.sh" "$T/campaign.sh" | grep -c '^<') lines (5 expected: NAME, H, RES, ST, PY):"; diff "$D/campaign.sh" "$T/campaign.sh" | grep '^>' | cut -c1-120

# ---- case 1: SIGTERM while waiting for the CI lease
reset_state; touch "$T/lease-busy"; start_campaign
wait_status "waiting: CI lease busy" 60 || echo "case 1: the lease wait was not reached"
sleep 1; kill -TERM "$CPID"; finish; begin
expect "rc 130" [ "$RC" = 130 ]; expect "no bill call" [ "$(n_calls 'bill-share.sh')" = 0 ]; expect "no dut.sh call except lease-free" [ "$(dut_non_lease)" = 0 ]
expect "marker left alone line" grep -q "marker not taken by this run, left alone" "$T/run.log"; expect ".done-aborted" [ -e "$T/res/.done-aborted" ]
verdict "1 SIGTERM in the lease wait"

# ---- case 1b: SIGTERM while waiting for the hand-off marker
reset_state; touch "$T/precheck-present"; start_campaign
wait_status "waiting: pre-check running" 60 || echo "case 1b: the marker wait was not reached"
sleep 1; kill -TERM "$CPID"; finish; begin
expect "rc 130" [ "$RC" = 130 ]; expect "no bill call" [ "$(n_calls 'bill-share.sh')" = 0 ]; expect "no dut.sh call except lease-free" [ "$(dut_non_lease)" = 0 ]
expect "marker left alone line" grep -q "marker not taken by this run, left alone" "$T/run.log"; expect ".done-aborted" [ -e "$T/res/.done-aborted" ]
verdict "1b SIGTERM in the hand-off marker wait"

# ---- case 2a: abort_early in the lease wait (DEADLINE_START already past)
reset_state; touch "$T/lease-busy"; start_campaign NOT_BEFORE="$(now_plus -7200)" DEADLINE_START="$(now_plus -3600)"; finish; begin
expect "rc 3" [ "$RC" = 3 ]; expect "no bill call" [ "$(n_calls 'bill-share.sh')" = 0 ]; expect "no dut.sh call except lease-free" [ "$(dut_non_lease)" = 0 ]
expect "outcome names the lease wait" grep -q "aborted: past DEADLINE_START while waiting for the CI lease" "$T/res/outcome.txt"; expect ".done-aborted" [ -e "$T/res/.done-aborted" ]
verdict "2a abort_early in the lease wait"

# ---- case 2b: abort_early in the hand-off marker wait
reset_state; touch "$T/precheck-present"; start_campaign NOT_BEFORE="$(now_plus -7200)" DEADLINE_START="$(now_plus -3600)"; finish; begin
expect "rc 3" [ "$RC" = 3 ]; expect "no bill call" [ "$(n_calls 'bill-share.sh')" = 0 ]; expect "no dut.sh call except lease-free" [ "$(dut_non_lease)" = 0 ]
expect "outcome names the marker wait" grep -q "aborted: past DEADLINE_START while the pre-check marker" "$T/res/outcome.txt"; expect ".done-aborted" [ -e "$T/res/.done-aborted" ]
verdict "2b abort_early in the hand-off marker wait"

# ---- case 3: normal completion (PASSES=base: base-pass1 then base-sw8k-pass1), every driver run ok
reset_state; printf 'ok\nok\n' >"$T/plan"; start_campaign; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect "one take" [ "$(n_calls 'bill-share.sh take')" = 1 ]; expect "exactly one release" [ "$(n_calls 'bill-share.sh release')" = 1 ]
expect ".done" [ -e "$T/res/.done" ]; expect "outcome recovered none" grep -q "recovered passes: none" "$T/res/outcome.txt"
expect "restore sequence hwattn-clear, ensure-base, serving-down IDLE_MIN=5, serving-up" restore_seq_matches "$FULL_RESTORE"
expect "a free lease reading right before each restore mutation" lease_before_each_mutation
expect "restored to the nightly" grep -q "restore ok: $NIGHTLY_V" "$T/res/status-history.log"; expect "no restore-deferred.txt" [ ! -e "$T/res/restore-deferred.txt" ]
verdict "3 normal completion after the marker take"
echo "  restore phase of case 3: $(restore_seq)"

# ---- case 4: SIGTERM after the marker take and after the first pass (during base-sw8k-pass1)
reset_state; printf 'ok\nsleep\n' >"$T/plan"; start_campaign
wait_status "base-sw8k-pass1: starting perf phase" 120 || echo "case 4: the second pass did not start"
sleep 2; kill -TERM "$CPID"; finish; begin
expect "rc 130" [ "$RC" = 130 ]; expect "one take" [ "$(n_calls 'bill-share.sh take')" = 1 ]; expect "exactly one release" [ "$(n_calls 'bill-share.sh release')" = 1 ]
expect "signal line" grep -q "SIGNAL received" "$T/res/status-history.log"; expect ".done-aborted" [ -e "$T/res/.done-aborted" ]
expect "full restore after the signal" restore_seq_matches "$FULL_RESTORE"
expect "a free lease reading right before each restore mutation" lease_before_each_mutation
expect "no stub driver left" no_driver_left
verdict "4 SIGTERM after the marker take and the first pass"
echo "  restore phase of case 4: $(restore_seq)"

# ---- case 5: takeover between passes (the lease turns busy after base-pass1)
reset_state; printf 'ok busy\nok\n' >"$T/plan"; start_campaign; finish; begin
expect "rc 0 (done with failures)" [ "$RC" = 0 ]; expect "no mutation after the busy reading" [ "$(muts_after_busy)" = 0 ]
expect "restore-deferred.txt" [ -s "$T/res/restore-deferred.txt" ]; expect "no release" [ "$(n_calls 'bill-share.sh release')" = 0 ]; expect "one take" [ "$(n_calls 'bill-share.sh take')" = 1 ]
expect "TAKEOVER status" grep -q "TAKEOVER: restore deferred before ensure-base" "$T/res/status-history.log"; expect "problem RESTORE-DEFERRED" grep -q "problems: RESTORE-DEFERRED" "$T/res/outcome.txt"
expect "stop reason lease busy before tag 2" grep -q "stop reason: CI lease busy before base-sw8k-pass1" "$T/res/outcome.txt"
expect "flock still released" [ "$(n_calls 'release_lock')" = 1 ]; expect ".done-with-failures" [ -e "$T/res/.done-with-failures" ]
verdict "5 takeover between passes"
echo "  restore phase of case 5: $(restore_seq)"; echo "  restore-deferred.txt of case 5:"; sed 's/^/    /' "$T/res/restore-deferred.txt"

# ---- case 6: driver rc 9 (the lease turned busy during base-pass1)
reset_state; printf 'rc9 busy\nok\n' >"$T/plan"; start_campaign; finish; begin
expect "rc 0 (done with failures)" [ "$RC" = 0 ]; expect "no mutation after the busy reading" [ "$(muts_after_busy)" = 0 ]
expect "restore-deferred.txt" [ -s "$T/res/restore-deferred.txt" ]; expect "no release" [ "$(n_calls 'bill-share.sh release')" = 0 ]
expect "TAKEOVER status" grep -q "TAKEOVER: restore deferred" "$T/res/status-history.log"; expect "stop reason driver rc 9" grep -q "driver rc 9" "$T/res/outcome.txt"
expect "flock still released" [ "$(n_calls 'release_lock')" = 1 ]; expect ".done-with-failures" [ -e "$T/res/.done-with-failures" ]
verdict "6 driver rc 9"
echo "  restore phase of case 6: $(restore_seq)"

# ---- case 7a: the lease turns busy between hwattn-clear and ensure-base in the restore
reset_state; printf 'ok\nok arm-hwattn-clear\n' >"$T/plan"; start_campaign; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect "hwattn-clear ran in the restore" restore_has 'STUB dut.sh hwattn-clear'
expect "no mutation after the busy reading" [ "$(muts_after_busy)" = 0 ]; expect "no ensure-base in the restore" restore_lacks 'STUB dut.sh ensure-base'
expect "restore-deferred.txt names ensure-base" grep -q "deferred before: ensure-base" "$T/res/restore-deferred.txt"; expect "no release" [ "$(n_calls 'bill-share.sh release')" = 0 ]
expect "flock still released" [ "$(n_calls 'release_lock')" = 1 ]
verdict "7a lease busy between hwattn-clear and ensure-base"
echo "  restore phase of case 7a: $(restore_seq)"

# ---- case 7b: the lease turns busy between ensure-base and serving-down in the restore
reset_state; printf 'ok\nok arm-ensure-base\n' >"$T/plan"; start_campaign; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect "ensure-base ran in the restore" restore_has 'STUB dut.sh ensure-base'
expect "no mutation after the busy reading" [ "$(muts_after_busy)" = 0 ]; expect "no serving call in the restore" restore_lacks 'STUB dut.sh .*serving-'
expect "restore-deferred.txt names serving-down" grep -q "deferred before: serving-down" "$T/res/restore-deferred.txt"; expect "no release" [ "$(n_calls 'bill-share.sh release')" = 0 ]
verdict "7b lease busy between ensure-base and serving-down"
echo "  restore phase of case 7b: $(restore_seq)"

# ---- case 8: a free lease keeps the normal restore (two arms, a package switch, chain.done = the host-suite exception)
reset_state; printf 'ok\nok\nok\nok\n' >"$T/plan"; echo "failed host=failed smoke=ok/ok/ok E=ok/ok bench=failed" >"$T/chain.done"; start_campaign PASSES="base target"; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect "chain gate passed on the exception" grep -q "chain end verdict 'failed host=failed smoke=ok/ok/ok E=ok/ok bench=failed': W may run" "$T/res/status-history.log"
expect "four driver runs" [ "$(cat "$T/drv-n")" = 4 ]; expect "exactly one release" [ "$(n_calls 'bill-share.sh release')" = 1 ]; expect ".done" [ -e "$T/res/.done" ]
expect "restored to the nightly" grep -q "restore ok: $NIGHTLY_V" "$T/res/status-history.log"; expect "full restore" restore_seq_matches "$FULL_RESTORE"
expect "a free lease reading right before each restore mutation" lease_before_each_mutation; expect "no restore-deferred.txt" [ ! -e "$T/res/restore-deferred.txt" ]
verdict "8 free lease keeps the normal restore"
echo "  restore phase of case 8: $(restore_seq)"

# ---- case 9: the first attempt of base-pass1 fails, the repeat succeeds
reset_state; printf 'fail\nok\nok\n' >"$T/plan"; start_campaign; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect ".done" [ -e "$T/res/.done" ]; expect "no .done-with-failures" [ ! -e "$T/res/.done-with-failures" ]
expect "recovered passes: base-pass1" grep -q "recovered passes: base-pass1" "$T/res/outcome.txt"; expect "incomplete none" grep -q "incomplete passes: none" "$T/res/outcome.txt"
expect "first attempt kept as base-pass1-failed1" [ -d "$T/res/base-pass1-failed1" ]; expect "three driver runs" [ "$(cat "$T/drv-n")" = 3 ]; expect "one release" [ "$(n_calls 'bill-share.sh release')" = 1 ]
verdict "9 first attempt failed, repeat ok"
echo "  outcome.txt of case 9: $(cat "$T/res/outcome.txt")"

# ---- case 10: both attempts of base-pass1 fail
reset_state; printf 'fail\nfail\nok\n' >"$T/plan"; start_campaign; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect ".done-with-failures" [ -e "$T/res/.done-with-failures" ]; expect "no .done" [ ! -e "$T/res/.done" ]
expect "incomplete passes: base-pass1" grep -q "incomplete passes: base-pass1" "$T/res/outcome.txt"; expect "recovered none" grep -q "recovered passes: none" "$T/res/outcome.txt"
expect "known systematic failure recorded" grep -q "known systematic failures: cell-b@8u-p1024" "$T/res/outcome.txt"; expect "one release" [ "$(n_calls 'bill-share.sh release')" = 1 ]
verdict "10 two failed attempts"
echo "  outcome.txt of case 10: $(cat "$T/res/outcome.txt")"

# ---- case 11: the chain's end verdict is not ok (and 11b: chain.done missing)
reset_state; echo "failed host=failed smoke=ok/ok/failed E=ok/ok bench=ok" >"$T/chain.done"; start_campaign; finish; begin
expect "rc 5" [ "$RC" = 5 ]; expect "no bill call" [ "$(n_calls 'bill-share.sh')" = 0 ]; expect "no mutation" [ "$(n_calls "$MUT")" = 0 ]
expect "no peer check reached" [ "$(n_calls 'pgrep peers')" = 0 ]; expect "outcome names the verdict" grep -q "aborted: the chain's end verdict is 'failed host=failed smoke=ok/ok/failed" "$T/res/outcome.txt"
verdict "11 chain.done not ok"
reset_state; rm -f "$T/chain.done"; start_campaign; finish; begin
expect "rc 5" [ "$RC" = 5 ]; expect "no bill call" [ "$(n_calls 'bill-share.sh')" = 0 ]; expect "outcome names the empty verdict" grep -q "aborted: the chain's end verdict is ''" "$T/res/outcome.txt"
verdict "11b chain.done missing"

# ---- case 12: EXPECTED_BASE empty
reset_state; start_campaign EXPECTED_BASE=; finish; begin
expect "rc 2" [ "$RC" = 2 ]; expect "no ssh call at all" [ ! -e "$T/calls.log" ]; expect "outcome names EXPECTED_BASE" grep -q "aborted: EXPECTED_BASE is empty" "$T/res/outcome.txt"
verdict "12 EXPECTED_BASE empty"

# ---- case 13: abort in the preflight after the marker take (the installed package is one of ours)
reset_state; echo "$BASE_V $BASE_SHA" >"$T/installed"; start_campaign; finish; begin
expect "rc 4" [ "$RC" = 4 ]; expect "one take" [ "$(n_calls 'bill-share.sh take')" = 1 ]; expect "exactly one release" [ "$(n_calls 'bill-share.sh release')" = 1 ]
expect "no mutation" [ "$(n_calls "$MUT")" = 0 ]; expect "outcome names ours" grep -q "is one of ours" "$T/res/outcome.txt"
verdict "13 abort in the preflight after the marker take"

# ---- case 14: the fork's scope (SW8K=0, four arm passes, NEED_FLOOR_S=1800)
reset_state; printf 'ok\nok\nok\nok\n' >"$T/plan"; start_campaign SW8K=0 PASSES="base target target base" NEED_FLOOR_S=1800; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect ".done" [ -e "$T/res/.done" ]
expect "exactly the four full-pass tags" grep -q "pass tags:  base-pass1 target-pass1 target-pass2 base-pass2$" "$T/res/status-history.log"
expect "four driver runs" [ "$(cat "$T/drv-n")" = 4 ]; expect "no hwattn-off anywhere" [ "$(n_calls 'dut.sh hwattn-off')" = 0 ]
expect "restore without hwattn-clear (config.env never set)" restore_seq_matches '^dut.sh lease-free;dut.sh ensure-base;dut.sh installed;dut.sh lease-free;dut.sh IDLE_MIN=5 serving-down;dut.sh lease-free;dut.sh serving-up;$'
expect "exactly one release" [ "$(n_calls 'bill-share.sh release')" = 1 ]; expect "configs-used says sw8k not run" grep -q "sw8k: not run (SW8K=0)" "$T/res/configs-used.txt"
expect "subset3.json copied as configs-used-full.json" cmp -s "$T/h/subset3.json" "$T/res/configs-used-full.json"
expect "the driver got subset3.json" grep -q "configs subset3.json" "$T/res/status-history.log"; expect "start line shows SW8K=0 NEED_FLOOR_S=1800" grep -q "SW8K=0 NEED_FLOOR_S=1800" "$T/res/status-history.log"
verdict "14 the fork's scope: SW8K=0, four passes, NEED_FLOOR_S=1800"
echo "  restore phase of case 14: $(restore_seq)"

# ---- case 14b: SW8K=1 gives the eight 2026-10-09 tags (checked on the tag line; no pass runs: 40 min left and the default floor)
reset_state; start_campaign SW8K=1 PASSES="base target target base" DEADLINE_START="$(now_plus 600)" PASS_DEADLINE="$(now_plus 1200)" DRIVER_END_BY="$(now_plus 2400)"; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect "exactly the eight tags, full pass then sw8k cell per arm pass" grep -q "pass tags:  base-pass1 base-sw8k-pass1 target-pass1 target-sw8k-pass1 target-pass2 target-sw8k-pass2 base-pass2 base-sw8k-pass2$" "$T/res/status-history.log"
expect "configs-used names sw8k.json" grep -q "sw8k: $T/h/sw8k.json" "$T/res/configs-used.txt"; expect "no driver run" [ ! -e "$T/drv-n" ]; expect "one take, one release" [ "$(n_calls 'bill-share.sh take')" = 1 ] && [ "$(n_calls 'bill-share.sh release')" = 1 ]
verdict "14b SW8K=1: the eight tags"

# ---- case 15a: NEED_FLOOR_S=1800 with 40 min left before DRIVER_END_BY: the pass starts
reset_state; printf 'ok\n' >"$T/plan"; start_campaign SW8K=0 NEED_FLOOR_S=1800 DEADLINE_START="$(now_plus 600)" PASS_DEADLINE="$(now_plus 1200)" DRIVER_END_BY="$(now_plus 2400)"; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect ".done" [ -e "$T/res/.done" ]; expect "one driver run" [ "$(cat "$T/drv-n")" = 1 ]; expect "one release" [ "$(n_calls 'bill-share.sh release')" = 1 ]
verdict "15a NEED_FLOOR_S=1800, 40 min left: the pass starts"

# ---- case 15b: the default floor (6600 s) with 40 min left: no pass, nothing changed on the DUT, the marker given back
reset_state; printf 'ok\n' >"$T/plan"; start_campaign SW8K=0 DEADLINE_START="$(now_plus 600)" PASS_DEADLINE="$(now_plus 1200)" DRIVER_END_BY="$(now_plus 2400)"; finish; begin
expect "rc 0" [ "$RC" = 0 ]; expect ".done-with-failures" [ -e "$T/res/.done-with-failures" ]; expect "no driver run" [ ! -e "$T/drv-n" ]
expect "stop reason not enough time (need about 110 min)" grep -q "stop reason: not enough time before DRIVER_END_BY for base-pass1 (need about 110 min)" "$T/res/outcome.txt"
expect "no DUT mutation" [ "$(n_calls "$MUT")" = 0 ]; expect "one take, one release" [ "$(n_calls 'bill-share.sh take')" = 1 ] && [ "$(n_calls 'bill-share.sh release')" = 1 ]
verdict "15b default floor 6600 s, 40 min left: no pass, no DUT change"

echo "=== $(grep -c ' -> PASS$' "$LOGF") PASS, $(grep -c ' -> FAIL$' "$LOGF") FAIL of 21 cases so far (this line is written before the summary below) ==="
} 2>&1 | tee -a "$LOGF"
n=$(grep -c ' -> PASS$' "$LOGF"); bad=$(grep -c ' -> FAIL$' "$LOGF")
echo "w-cleanup-test: $n of 21 cases PASS, $bad FAIL (temp dir $T removed)" | tee -a "$LOGF"
cleanup; rm -rf "$T"
[ "$n" = 21 ] && [ "$bad" = 0 ]
