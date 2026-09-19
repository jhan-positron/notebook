#!/usr/bin/env bash
# canon-ci campaign 2026-09-18: the nightly System CI perf phase, run by hand on the WHOLE of delphi-3bda,
# ONE arm only:
#   canon = the canonical-AMX .deb: main 3faba6d0fd (the commit of the 2026-09-18 nightly deb and of both
#           ci-mimic arms) + the deb preset line TRON_AMX_DISPATCH=ON (6f37cd2ed9). No PR #4424 code.
#           Built by build-canon.sh into /var/tmp/jhan/canon-ci-20260918/target.deb.
# The comparison arms are NOT re-run: base = the ci-mimic base arm of 2026-09-18 (nightly deb, no AMX),
# target = the ci-mimic target arm (PR #4424 + AMX + VNNI-K), both in exec/results/ci-mimic-20260918/.
# Same client code as the nightly (systems_test scripts/perf.py test_performance through the Caddy proxy,
# platformd provisioning per config, USE_HW_ATTN untouched), run from this host with st_ci_perf.py
# (copied unchanged from exec/ci-mimic-20260918, the version that completed the target arm 16:14-17:57 UTC).
#
# Forked from exec/ci-mimic-20260918/campaign.sh. Changes: one arm; Bill's marker is taken by launch.sh (operator
# step on jhan's order of 2026-09-18 22:0x UTC, Bill idle; bill-share.sh's rule: never from the campaign itself);
# the end state is a HANDOFF to the issue4500-20260918 campaign of session vnnied-k-in-place-c3: nightly deb
# reinstalled, production engines DOWN through platformd (HANDOFF=down, default), positron's slice files removed,
# marker released, flock released. HANDOFF=up brings serving back instead (the ci-mimic restore recipe).
# A TERM/INT/HUP to this script stops the driver and runs the same restore + release path (review 2026-09-18).
# To stop the arm early by hand: kill this script's pid (NOT -9), or pkill -TERM -f st_ci_perf.py.
#
# Runs on the CLIENT host (claude-agentsrv), detached (launch.sh). DUT steps go over ssh (dut.sh).
# Env knobs: DEADLINE_START (no arm starts after this UTC instant), ARMS (default canon),
#            AMX_PROBE (default 1: 20 s EXE.AMX_BUSY sample before the llama-8b and qwen-3-4b tp2 benchmarks,
#            the same two models as the ci-mimic arms), HANDOFF (down|up, default down),
#            NO_WAIT=1 (skip the lease wait), DRIVER_TIMEOUT (s, default 8400, also capped so the driver ends by
#            DRIVER_END_BY), DRIVER_END_BY (UTC instant, default 2026-09-19T02:05:00Z).
# Traps carried over from 2026-09-18: never ${VAR:+x} with a 0/1 flag; the remote flock holder's pid must
# be killed explicitly and the kill verified; never edit st_ci_perf.py while an arm runs; apt never restarts engines.
set -u
NAME=canon-ci-20260918
H=/home/jhan/workspace/intel-AMX/exec/$NAME
RES=/home/jhan/workspace/intel-AMX/exec/results/$NAME
ST=/home/jhan/workspace/ai-runs/systems_test
PY=$ST/.venv/bin/python
DUT_ALIAS=delphi-3bda
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ServerAliveCountMax=4"
LOCK=/var/tmp/jhan/3bda-campaign.lock
HOLDER_LIFE=16200   # s; the remote holder dies by itself after 4.5 h if everything else fails (22:55Z start -> 03:25Z)
DEADLINE_START=${DEADLINE_START:-2026-09-18T23:30:00Z}   # arm ~80-105 min + ~15 min restore/handoff must end before the peer's 01:40 UTC hold
DRIVER_END_BY=${DRIVER_END_BY:-2026-09-19T02:05:00Z}     # hard: 02:45 UTC ci-runner-stop timer, 03:39 UTC nightly apt reinstall
NO_WAIT=${NO_WAIT:-0}; AMX_PROBE=${AMX_PROBE:-1}; HANDOFF=${HANDOFF:-down}; DRIVER_TIMEOUT=${DRIVER_TIMEOUT:-8400}
ARMS=${ARMS:-canon}
mkdir -p "$RES"
STATUS=$RES/.status
say() { echo "$(date -u +%FT%TZ) $*"; }
status() { say "$*"; echo "$(date -u +%FT%TZ) $*" >"$STATUS"; }
dut() { ssh $SSH_OPTS "$DUT_ALIAS" bash "$H/dut.sh" "$@"; }
dut_t() { local t=$1; shift; timeout "$t" ssh $SSH_OPTS "$DUT_ALIAS" bash "$H/dut.sh" "$@"; }   # with a command timeout (rc 124)
bill() { ssh $SSH_OPTS "$DUT_ALIAS" bash ~/workspace/intel-AMX/exec/bill-share.sh "$@"; }
now_s() { date -u +%s; }
ts() { date -u -d "$1" +%s; }
past() { [ "$(now_s)" -gt "$(ts "$1")" ]; }

# ---- the host-wide campaign flock on the DUT, held for the whole run by a remote sleep whose pid we record
LOCK_PID=; REMOTE_LOCK_PID=
hold_lock() {
  : >"$RES/.lock.out"
  ssh $SSH_OPTS "$DUT_ALIAS" "flock -n $LOCK -c 'echo held pid \$\$; exec sleep $HOLDER_LIFE'" >"$RES/.lock.out" 2>&1 &
  LOCK_PID=$!
  local i
  for i in $(seq 1 60); do   # poll while the ssh is alive: a slow login must not be mistaken for a refused flock
    grep -q "^held pid" "$RES/.lock.out" && break
    kill -0 "$LOCK_PID" 2>/dev/null || break
    sleep 1
  done
  if grep -q "^held pid" "$RES/.lock.out"; then REMOTE_LOCK_PID=$(awk '/^held pid/{print $3}' "$RES/.lock.out"); return 0; fi
  if kill -0 "$LOCK_PID" 2>/dev/null; then   # still connecting after 60 s: give up on this attempt and remove any orphan holder of ours
    kill "$LOCK_PID" 2>/dev/null; wait "$LOCK_PID" 2>/dev/null
    ssh $SSH_OPTS "$DUT_ALIAS" "pkill -u jhan -f '^sleep $HOLDER_LIFE\$'" 2>/dev/null
    say "hold_lock: ssh did not answer within 60 s (no 'held pid'); local ssh killed, orphan holders removed"
  else
    say "campaign flock on the DUT is HELD by another campaign: $(head -c 200 "$RES/.lock.out")"
  fi
  LOCK_PID=; return 1
}
release_lock() {   # kill the remote holder and VERIFY the flock is free; report either way
  local try
  if [ -n "$REMOTE_LOCK_PID" ]; then
    for try in 1 2 3; do
      if ssh $SSH_OPTS "$DUT_ALIAS" "kill $REMOTE_LOCK_PID 2>/dev/null; pkill -P $REMOTE_LOCK_PID 2>/dev/null; sleep 1; flock -n $LOCK true"; then
        say "flock released (remote holder $REMOTE_LOCK_PID gone)"; REMOTE_LOCK_PID=; break
      fi
      say "release_lock: attempt $try failed; retrying"; sleep 10
    done
    [ -n "$REMOTE_LOCK_PID" ] && { say "WARNING: remote flock holder $REMOTE_LOCK_PID may STILL hold $LOCK (it dies by itself after $HOLDER_LIFE s)"; LOCK_STILL_HELD=1; }
  fi
  [ -n "$LOCK_PID" ] && { kill "$LOCK_PID" 2>/dev/null; wait "$LOCK_PID" 2>/dev/null; }
  LOCK_PID=
}
LOCK_STILL_HELD=0

# ---- restore + handoff + release: runs exactly once, on the normal path AND on a signal
BASE_VERSION=; BASE_SHA=; DRIVER_PID=; RESTORED=0; problems=""
restore_and_release() {
  [ "$RESTORED" = 1 ] && return 0; RESTORED=1
  if [ -n "$BASE_VERSION" ]; then
    if dut_t 900 ensure-base "$BASE_VERSION" "$BASE_SHA"; then status "restore ok: $(dut installed)"; else problems="$problems RESTORE-FAILED"; status "RESTORE FAILED: $(dut installed) (wanted $BASE_VERSION); jhan must reinstall tron by hand"; fi
    if [ "$HANDOFF" = up ]; then
      # engines of the last config still run the deleted canon binary until restarted: down, then up (skip up when down failed)
      if dut_t 1500 serving-down; then dut_t 600 serving-up || { problems="$problems SERVING-UP-FAILED"; say "WARNING serving-up did not complete"; }
      else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log); engines may still run the deleted canon binary"; fi
    else
      if dut_t 1500 serving-down; then status "handoff: production engines down, hugepages free; the issue4500 campaign may start"
      else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log); a unit may still be up or fewer than 256 hugepages are free"; fi
    fi
  else
    say "no base identity recorded (aborted before preflight): nothing to restore"
  fi
  local rel_out rel_rc
  rel_out=$(bill release 2>&1); rel_rc=$?; printf '%s\n' "$rel_out" | tail -1
  [ "$rel_rc" -eq 0 ] || { problems="$problems MARKER-NOT-RELEASED"; say "WARNING: bill-share release rc=$rel_rc; run bill-share.sh release by hand"; }
  release_lock
  [ "$LOCK_STILL_HELD" = 1 ] && problems="$problems FLOCK-STILL-HELD"
}
on_signal() {
  trap '' TERM INT HUP
  status "SIGNAL received: stopping the driver, then restoring"
  pkill -TERM -f "$H/st_ci_perf.py" 2>/dev/null
  [ -n "$DRIVER_PID" ] && { kill -TERM "$DRIVER_PID" 2>/dev/null; wait "$DRIVER_PID" 2>/dev/null; }
  for _ in $(seq 1 60); do pgrep -f "$H/st_ci_perf.py" >/dev/null || break; sleep 1; done
  pkill -KILL -f "$H/st_ci_perf.py" 2>/dev/null
  restore_and_release
  status "campaign ABORTED by signal; problems:${problems:- none}"; touch "$RES/.done-aborted"
  exit 130
}
trap on_signal TERM INT HUP
trap release_lock EXIT

run_arm() {  # $1 arm -> rc of the driver
  local arm=$1 dir=$RES/$1 tmo rc
  mkdir -p "$dir"
  tmo=$(( $(ts "$DRIVER_END_BY") - $(now_s) )); [ "$tmo" -gt "$DRIVER_TIMEOUT" ] && tmo=$DRIVER_TIMEOUT
  [ "$tmo" -gt 600 ] || { status "arm $arm: less than 10 min left before DRIVER_END_BY; not starting"; return 3; }
  status "arm $arm: starting perf phase ($(dut installed)); driver timeout $tmo s"
  ( cd "$ST" && env PYTHONPATH="$H/talos_stub:$ST" \
      OPENAI_HOST=http://delphi-3bda.positron.internal/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
      PLATFORM_TYPE=granite_rapids_72_rinzler SYSTEM_CI_SPECULATION=0 SSH_USER=jhan SSH_PASS= \
      HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false \
      CI_MIMIC_ARM=$arm CI_MIMIC_OUT=$dir/perf.json TALOS_STUB_OUT=$dir/talos.json CI_MIMIC_MODELS="" \
      CI_MIMIC_AMX_PROBE=$AMX_PROBE \
      timeout "$tmo" "$PY" "$H/st_ci_perf.py" >"$dir/driver.log" 2>&1 ) &
  DRIVER_PID=$!
  wait "$DRIVER_PID"; rc=$?; DRIVER_PID=
  grep -E "Perf test for|RESULT|Running averages|engine count|deleted|Error|Traceback" "$dir/driver.log" | tail -40 >"$dir/summary.txt"
  status "arm $arm: driver rc=$rc ($(grep -c 'Perf test for' "$dir/driver.log") configs completed)"
  return $rc
}

status "campaign start (ARMS=$ARMS DEADLINE_START=$DEADLINE_START HANDOFF=$HANDOFF)"
# ---- wait for the machine: CI lease (600 s grace), then the campaign flock BEFORE anything else; the deadline applies while waiting
if [ "$NO_WAIT" != 1 ]; then
  until dut_t 120 lease-free >/dev/null 2>&1; do
    past "$DEADLINE_START" && { status "ABORT: past DEADLINE_START while waiting for the CI lease"; exit 3; }
    status "waiting: CI lease busy (or the DUT did not answer)"; sleep 120
  done
  status "CI lease free"
fi
until hold_lock; do
  past "$DEADLINE_START" && { status "ABORT: past DEADLINE_START while waiting for the campaign flock"; exit 3; }
  status "waiting: campaign flock held by another campaign"; sleep 60
done
past "$DEADLINE_START" && { status "ABORT: past DEADLINE_START before starting"; exit 3; }

# ---- Bill's marker must already be taken (launch.sh does it on jhan's order); refuse to run on a shared machine otherwise
if bill status 2>&1 | grep -q "marker present"; then status "ABORT: Bill's marker is present; run bill-share.sh take (jhan's decision) before launching"; exit 6; fi

# ---- preflight (read-only) and the base identity = whatever the nightly installed today
PF=$RES/preflight.txt
dut_t 300 preflight >"$PF" 2>&1; say "preflight written ($PF)"
read -r BASE_VERSION BASE_SHA < <(dut_t 120 installed)
say "base package = $BASE_VERSION rinzler sha $BASE_SHA"
abort_early() { status "ABORT: $1"; BASE_VERSION=; restore_and_release; exit "$2"; }   # nothing installed yet: only the marker and the flock go back
case $BASE_VERSION in 2026.*) ;; *) abort_early "unexpected installed tron version '$BASE_VERSION'" 4;; esac
case $BASE_VERSION in *jhan*) abort_early "installed package '$BASE_VERSION' is one of ours, not the nightly's; restore by hand first" 4;; esac
grep -q "canon build: status=ok" "$PF" || abort_early "canon build not ok (see $PF)" 5
if grep -q "num-expert-replicas count: [1-9]" "$PF"; then say "WARNING: the rinzler unit file carries a hand edit (--num-expert-replicas); the nightly's deb file has none"; fi
echo "$BASE_VERSION $BASE_SHA" >"$RES/base-identity.txt"
dut_t 300 save-base-deb "$BASE_VERSION" || say "WARNING: could not save a local copy of the nightly deb; ensure-base will use the apt repository"

# ---- the arm(s)
fails=0
for arm in $ARMS; do
  if past "$DEADLINE_START"; then status "deadline reached before $arm; stopping"; fails=$((fails+1)); break; fi
  if dut_t 900 ensure-canon; then :; else status "package step for $arm failed rc=$?; stopping"; fails=$((fails+1)); break; fi
  sleep 20  # let platformd notice the package change before the harness patches its config
  if run_arm "$arm"; then :; else fails=$((fails+1)); fi
done

# ---- restore the nightly's package, the handoff state, Bill's marker, the flock
restore_and_release
if [ $fails -eq 0 ] && [ -z "$problems" ]; then status "campaign done"; touch "$RES/.done"
else status "campaign done with $fails arm failure(s); problems:${problems:- none}"; touch "$RES/.done-with-failures"; fi
