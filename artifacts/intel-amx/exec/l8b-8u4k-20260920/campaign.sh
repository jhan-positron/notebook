#!/usr/bin/env bash
# l8b-8u4k campaign 2026-09-20: ONE cell, llama-3.1-8b at 8 users per engine (32 users in total) and prompt length 4096,
# run per CI-test/status/llama-3.1-8b-8u-4k-plan.md on the WHOLE of delphi-3bda with the nightly's own client
# (systems_test scripts/perf.py through st_ci_perf.py) against rinzler engines provisioned by platformd in the nightly
# layout (4 tp2 engines behind Caddy). Two arms, interleaved, three passes each:
#   base  = the nightly deb (2026.09.18-3faba6d0, no AMX code); dut.sh ensure-base reinstalls the saved copy
#   canon = tron_2026.09.18-0594dc54-jhan-ci-canon (main 3faba6d0 + deb preset TRON_AMX_DISPATCH=ON, no PR
#           #4424), /var/tmp/jhan/canon-ci-20260918/target.deb; dut.sh ensure-canon
# Every pass runs the one config of configs-full.json (plan section 5). No check cell (CHECK=0, plan section 6: the
# Saturday check cell and the Saturday 2-users prompt-4096 cell showed the shape works on both sides).
# Copied from exec/l8b-levers-20260919/campaign.sh (the Saturday campaign, reviewed twice); only NAME, the deadlines,
# DRIVER_TIMEOUT and the CHECK default changed (plan section 4). The check-cell code is kept but not used.
#
# Forked from exec/canon-ci-20260918/campaign.sh; reviewed 2026-09-19 (review-findings.txt). Rules implemented:
#   * engine RESTART after every package switch (dut.sh serving-down, then serving-up, which waits for platformd
#     idle): apt never restarts engines and every pass provisions the same model, so without it a pass would run
#     the previous arm's deleted binary (plan section 1). st_ci_perf.py stops the pass (rc 7) if a pid still runs
#     a deleted or foreign binary after provisioning.
#   * check cell verdict (plan 2a "engine error, timeout, no output"): rc 124, or rc 2 with the check config named
#     in FAILED_CONFIGS and no provisioning fault in driver.log = the cell FAILS (cells dropped); any other rc
#     (1 crash, 7 stale binary, ssh faults) is NOT evidence about the prompt length: one engine restart and one
#     repeat of the same check, then a safe stop (jhan decides) if it is still not evidence.
#   * a failed pass is repeated once after an engine restart (plan 2a); a config counts as a known systematic
#     failure only after it failed twice in one pass-run, and a later pass whose failed configs are all known
#     systematic failures is not repeated; two consecutive driver runs with 0 completed configs stop the campaign.
#   * the campaign starts (lease, flock, marker, check cell, first pass) by DEADLINE_START; later passes start
#     by PASS_DEADLINE; a pass that cannot finish before DRIVER_END_BY does not start (plan 2a says "do not start
#     a pass after 19:30 UTC" with the reasoning "the campaign needs 5.3 h before the 01:40 hold": read here as the
#     campaign-start deadline so a late lease does not cost pass 3; the hard limit is DRIVER_END_BY either way).
#   * a busy CI lease before a pass stops the campaign safely (an unreachable DUT is retried 3 times first);
#     Bill's marker is retried every 30 min while he is active; the base identity must equal EXPECTED_BASE.
# End state (HANDOFF=up, plan section 2): nightly deb reinstalled, production engines up, Bill's marker
# released, flock released, /opt/positron/user/config.env still 0 bytes.
#
# TO STOP EARLY: kill -TERM <pid of this script> (the pid launch.sh printed; NOT -9). That stops the driver and runs
# the restore + release path. Do NOT pkill st_ci_perf.py alone: a driver killed by a signal (rc 130/137/143) is read
# as an operator stop and ends the campaign, but only this script runs the restore.
# RECOVERY if this script died without its trap (SIGKILL, OOM, host reboot): on delphi-3bda
#   pkill -u jhan -f '^sleep 50400$'; flock -n /var/tmp/jhan/3bda-campaign.lock true && echo flock free
#   bash ~/workspace/intel-AMX/exec/l8b-8u4k-20260920/dut.sh ensure-base 2026.09.18-3faba6d0 27e6883c2e8696b861589272470d5f6a4ec5485f6e8cd2ad163ae699f1dc6616
#   IDLE_MIN=5 bash .../dut.sh serving-down && bash .../dut.sh serving-up
#   bash ~/workspace/intel-AMX/exec/bill-share.sh release; stat -c %s /opt/positron/user/config.env   (must print 0)
# RESUME: PASS_TAGS="canon-pass2 base-pass3 canon-pass3" CHECK=0 launch.sh reruns only those tags (a tag whose
# perf.json exists is skipped unless RESUME_OVERWRITE=1); CHECK=0 reuses configs-used.txt from the earlier check.
#
# Runs on the CLIENT host (claude-agentsrv), detached (launch.sh). DUT steps go over ssh (dut.sh).
# Env knobs: DEADLINE_START, PASS_DEADLINE, DRIVER_END_BY, DRIVER_TIMEOUT (s per pass, default 2400), CHECK_TIMEOUT (s for
#            the section-6 cell, default 2400), PASSES (default "base canon base canon base canon") or PASS_TAGS,
#            CHECK (1|0), AMX_PROBE (1|0), HANDOFF (up|down), NO_WAIT=1 (skip the lease wait), EXPECTED_BASE,
#            IDLE_MIN_SWITCH (journal-quiet minutes before an intra-campaign engine restart, default 1; handoff uses 5).
# Traps carried over: never ${VAR:+x} with a 0/1 flag; the remote flock holder's pid must be killed explicitly and the
# kill verified; never edit st_ci_perf.py or this file while a pass runs; apt never restarts engines; pgrep -f patterns
# anchored so a checker does not match itself; `rc=$?` after `if cmd` reads the if-statement's status, capture rc first.
set -u
NAME=l8b-8u4k-20260920
H=/home/jhan/workspace/intel-AMX/exec/$NAME
RES=/home/jhan/workspace/intel-AMX/exec/results/$NAME
ST=/home/jhan/workspace/ai-runs/systems_test
PY=$ST/.venv/bin/python
DUT_ALIAS=delphi-3bda
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ServerAliveCountMax=4"
LOCK=/var/tmp/jhan/3bda-campaign.lock
HOLDER_LIFE=50400   # s; the remote flock holder dies by itself after 14 h if everything else fails
EXPECTED_BASE=${EXPECTED_BASE:-2026.09.18-3faba6d0}
DEADLINE_START=${DEADLINE_START:-2026-09-20T22:00:00Z}   # plan section 2: the campaign (lease, flock, marker wait, first pass) must START by this
PASS_DEADLINE=${PASS_DEADLINE:-2026-09-21T00:20:00Z}     # plan section 2: no further pass starts after this (a 40-min pass then ends before DRIVER_END_BY)
DRIVER_END_BY=${DRIVER_END_BY:-2026-09-21T01:00:00Z}     # hard: the restore needs up to 16 min; pre-CI hold 01:40Z, ci-runner-stop 02:45Z, nightly apt reinstall ~03:39Z
NO_WAIT=${NO_WAIT:-0}; AMX_PROBE=${AMX_PROBE:-1}; HANDOFF=${HANDOFF:-up}
DRIVER_TIMEOUT=${DRIVER_TIMEOUT:-2400}; CHECK_TIMEOUT=${CHECK_TIMEOUT:-2400}   # plan section 4: one cell of 11-13 min plus provisioning per pass
PASSES=${PASSES:-"base canon base canon base canon"}
PASS_TAGS=${PASS_TAGS:-}
RESUME_OVERWRITE=${RESUME_OVERWRITE:-0}
CHECK=${CHECK:-0}   # plan section 6: no check cell
IDLE_MIN_SWITCH=${IDLE_MIN_SWITCH:-1}
CHECK8192=llama_3_1_8b_instruct_good_tp2_32u_p8192
CHECK7168=llama_3_1_8b_instruct_good_tp2_32u_p7168
mkdir -p "$RES"; rm -f "$RES"/.done "$RES"/.done-with-failures "$RES"/.done-aborted
STATUS=$RES/.status
say() { echo "$(date -u +%FT%TZ) $*"; }
status() { say "$*"; echo "$(date -u +%FT%TZ) $*" >"$STATUS"; echo "$(date -u +%FT%TZ) $*" >>"$RES/status-history.log"; }
dut() { ssh $SSH_OPTS "$DUT_ALIAS" bash "$H/dut.sh" "$@"; }
dut_t() { local t=$1; shift; timeout "$t" ssh $SSH_OPTS "$DUT_ALIAS" "${DUT_ENV:+$DUT_ENV }bash $H/dut.sh $*"; }   # with a command timeout (rc 124)
dut_env_t() { local t=$1 e=$2; shift 2; timeout "$t" ssh $SSH_OPTS "$DUT_ALIAS" "$e bash $H/dut.sh $*"; }   # with one VAR=value for dut.sh
DUT_ENV=   # when set (VAR=value), dut_t prepends it to the remote command (used by the handoff's IDLE_MIN=5 serving-down)
dut_retry() { local t=$1 n; shift; for n in 1 2 3; do dut_t "$t" "$@" && return 0; say "dut_retry: $1 attempt $n failed" >&2; sleep 20; done; return 1; }   # ssh hiccups (review K2); messages to stderr, callers capture stdout (D4)
# retry ONLY ssh-level failures (rc 255 could not connect, rc 124 command timeout with no output); dut.sh's own rc 1 is final (D1)
dut_retry_ssh() { local t=$1 n rc; shift; for n in 1 2 3 4 5; do dut_t "$t" "$@"; rc=$?; case $rc in 0) return 0;; 255|124) say "dut_retry_ssh: $1 attempt $n rc=$rc (ssh); retry in 60 s" >&2; sleep 60;; *) return $rc;; esac; done; return $rc; }
wait_dut() {   # wait (bounded, $1 s) until the DUT answers; 0 = answered, 1 = gave up (D1)
  local limit=${1:-1800} t0; t0=$(now_s)
  until timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" true >/dev/null 2>&1; do
    [ $(( $(now_s) - t0 )) -gt "$limit" ] && { say "wait_dut: DUT did not answer for $limit s"; return 1; }
    status "restore: DUT not answering; retry in 60 s"; sleep 60
  done
  return 0
}
bill() { ssh $SSH_OPTS "$DUT_ALIAS" bash ~/workspace/intel-AMX/exec/bill-share.sh "$@"; }
now_s() { date -u +%s; }
ts() { date -u -d "$1" +%s; }
past() { [ "$(now_s)" -gt "$(ts "$1")" ]; }
installed_sha() { local v; v=$(dut_retry 120 installed | awk '{print $2}' | tail -1); [[ $v =~ ^[0-9a-f]{64}$ ]] && echo "$v"; }   # only a real sha256, else empty (D4/D5/D8)
in_list() { case " $2 " in *" $1 "*) return 0;; esac; return 1; }   # $1 word, $2 space-separated list

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
  if kill -0 "$LOCK_PID" 2>/dev/null; then
    kill "$LOCK_PID" 2>/dev/null; wait "$LOCK_PID" 2>/dev/null
    ssh $SSH_OPTS "$DUT_ALIAS" "pkill -u jhan -f '^sleep $HOLDER_LIFE\$'" 2>/dev/null
    say "hold_lock: ssh did not answer within 60 s (no 'held pid'); local ssh killed, orphan holders removed"
  else
    say "campaign flock on the DUT is HELD by another campaign: $(head -c 200 "$RES/.lock.out")"
  fi
  LOCK_PID=; return 1
}
LOCK_STILL_HELD=0
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

# ---- engine restart after a package switch: the running engines still map the old (deleted) binary
restart_engines() {   # $1 = IDLE_MIN for the idle test (1 between passes: only our own traffic; 5 at the handoff)
  local idle=${1:-$IDLE_MIN_SWITCH} rc
  dut_env_t 1500 "IDLE_MIN=$idle" serving-down; rc=$?
  [ $rc -eq 0 ] || { say "restart_engines: serving-down rc=$rc (see log)"; return 1; }
  dut_t 900 serving-up; rc=$?
  [ $rc -eq 0 ] || { say "restart_engines: serving-up rc=$rc"; return 1; }
  return 0
}

# ---- package switch + restart; $1 = base|canon
switch_to() {
  local arm=$1 rc
  case $arm in
    base)  dut_t 900 ensure-base "$BASE_VERSION" "$BASE_SHA"; rc=$? ;;
    canon) dut_t 900 ensure-canon; rc=$? ;;
    *) say "switch_to: unknown arm $arm"; return 2 ;;
  esac
  [ $rc -eq 0 ] || { say "switch_to $arm: package step rc=$rc"; return 1; }
  sleep 20  # let platformd notice the package change before anything else
  restart_engines "$IDLE_MIN_SWITCH" || { say "switch_to $arm: engine restart failed"; return 1; }
  return 0
}

# ---- restore + handoff + release: runs exactly once, on the normal path AND on a signal
BASE_VERSION=; BASE_SHA=; DRIVER_PID=; RESTORED=0; problems=""
restore_and_release() {
  [ "$RESTORED" = 1 ] && return 0; RESTORED=1
  # the DUT outage that stopped the campaign may still last: wait for it (bounded 30 min), then retry ssh-level failures (D1)
  wait_dut 1800 || { problems="$problems DUT-UNREACHABLE"; status "RESTORE: DUT unreachable for 30 min; steps below will fail; see the RECOVERY sequence in the header"; }
  if [ -n "$BASE_VERSION" ]; then
    local restored=0
    if dut_retry_ssh 900 ensure-base "$BASE_VERSION" "$BASE_SHA"; then restored=1; status "restore ok: $(dut_retry 120 installed)"; else problems="$problems RESTORE-FAILED"; status "RESTORE FAILED: $(dut_retry 120 installed) (wanted $BASE_VERSION); jhan must reinstall tron by hand"; fi
    if [ "$HANDOFF" = up ] && [ $restored = 1 ]; then
      # engines of the last pass still run the deleted binary until restarted: down, then up (skip up when down failed)
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then dut_retry_ssh 900 serving-up || { problems="$problems SERVING-UP-FAILED"; say "WARNING serving-up did not complete"; }
      else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log); engines may still run a deleted binary"; fi
    elif [ "$HANDOFF" = up ]; then
      # never bring production up on a binary that is not the nightly's: leave the engines as they are, jhan decides
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then status "restore failed: production engines taken DOWN (not brought up on a non-nightly binary)"; else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: restore failed and serving-down failed"; fi
    else
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then status "handoff: production engines down, hugepages free"
      else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log)"; fi
    fi
    local cfgbytes n
    for n in 1 2 3; do cfgbytes=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" 'stat -c %s /opt/positron/user/config.env' 2>/dev/null); [ -n "$cfgbytes" ] && break; sleep 30; done
    if [ "$cfgbytes" = 0 ]; then say "config.env is 0 bytes (ok)"; else problems="$problems CONFIG-ENV-${cfgbytes:-unread}-BYTES"; say "WARNING: /opt/positron/user/config.env has '${cfgbytes:-unread}' bytes (must be 0)"; fi
  else
    say "no base identity recorded (aborted before preflight): nothing to restore"
  fi
  local rel_out rel_rc n
  for n in 1 2 3; do rel_out=$(bill release 2>&1); rel_rc=$?; [ "$rel_rc" -eq 0 ] && break; say "bill release attempt $n rc=$rel_rc"; sleep 30; done
  printf '%s\n' "$rel_out" | tail -1
  [ "$rel_rc" -eq 0 ] || { problems="$problems MARKER-NOT-RELEASED"; say "WARNING: bill-share release rc=$rel_rc; run bill-share.sh release by hand"; }
  release_lock
  [ "$LOCK_STILL_HELD" = 1 ] && problems="$problems FLOCK-STILL-HELD"
}
on_signal() {
  if [ "$RESTORED" = 1 ]; then say "signal received during the restore: letting the restore finish"; return 0; fi
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
# any early exit after launch.sh took Bill's marker must give it back (review C4/C19): BASE_VERSION empty = nothing installed yet
abort_early() { status "ABORT: $1"; BASE_VERSION=; restore_and_release; echo "aborted: $1" >"$RES/outcome.txt"; touch "$RES/.done-aborted"; exit "$2"; }

# ---- one driver run: $1 tag (results subdir), $2 configs json, $3 timeout s -> rc of the driver
LAST_RUN_S=0; LAST_FAILED_CONFIGS=""; LAST_COMPLETED=0; DRIVER_KILLED=0
run_pass() {
  local tag=$1 cfg=$2 tmo=$3 dir=$RES/$1 rc t0 sha
  mkdir -p "$dir"
  local left=$(( $(ts "$DRIVER_END_BY") - $(now_s) )); [ "$tmo" -gt "$left" ] && tmo=$left
  [ "$tmo" -gt 600 ] || { status "$tag: less than 10 min left before DRIVER_END_BY; not starting"; return 3; }
  sha=$(installed_sha); [ -n "$sha" ] || say "WARNING: installed sha unreadable; the driver falls back to the snapshot's own sha line"
  status "$tag: starting perf phase ($(dut_t 120 installed)); configs $(basename "$cfg"); driver timeout $tmo s"
  t0=$(now_s); DRIVER_KILLED=0
  ( cd "$ST" && env PYTHONPATH="$H/talos_stub:$ST" \
      OPENAI_HOST=http://delphi-3bda.positron.internal/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
      PLATFORM_TYPE=granite_rapids_72_rinzler SYSTEM_CI_SPECULATION=0 SSH_USER=jhan SSH_PASS= \
      HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
      CI_MIMIC_ARM=$tag CI_MIMIC_OUT=$dir/perf.json TALOS_STUB_OUT=$dir/talos.json CI_MIMIC_MODELS="" \
      CI_MIMIC_CONFIGS_JSON=$cfg CI_MIMIC_INSTALLED_SHA=$sha CI_MIMIC_AMX_PROBE=$AMX_PROBE \
      timeout "$tmo" "$PY" "$H/st_ci_perf.py" >"$dir/driver.log" 2>&1 ) &
  DRIVER_PID=$!
  wait "$DRIVER_PID"; rc=$?; DRIVER_PID=
  LAST_RUN_S=$(( $(now_s) - t0 ))
  case $rc in 130|137|143) DRIVER_KILLED=1;; esac
  grep -E "Perf test for|CONFIG DONE|RESULT|engine count|deleted|STOP|FAILED_CONFIGS|pass stopped|Error|Traceback|configs without results" "$dir/driver.log" | tail -80 >"$dir/summary.txt"
  # the driver's last line names the configs without results, comma-separated names without spaces
  LAST_FAILED_CONFIGS=$(grep -oE "FAILED_CONFIGS [^ ]+" "$dir/driver.log" | tail -1 | awk '{print $2}' | tr ',' ' ')
  LAST_COMPLETED=$(grep -c 'Perf test for' "$dir/driver.log")
  status "$tag: driver rc=$rc in $((LAST_RUN_S/60)) min ($LAST_COMPLETED configs completed, $(grep -c 'anomalous tps' "$dir/driver.log") anomalous-sample lines${LAST_FAILED_CONFIGS:+; failed: $LAST_FAILED_CONFIGS})"
  return $rc
}

# ---- check-cell verdict (review C5-C8): ok | fails (evidence about the prompt length) | unknown (driver or provisioning fault)
check_verdict() {   # $1 rc, $2 config name, $3 results dir
  local rc=$1 name=$2 dir=$3
  [ "$rc" -eq 0 ] && { echo ok; return; }
  if [ "$rc" -eq 124 ]; then   # ran past CHECK_TIMEOUT: evidence only if the benchmark had started (a stuck provisioning is not; D2)
    if grep -q 'Running round' "$dir/driver.log" 2>/dev/null; then echo fails; else echo unknown; fi; return
  fi
  if [ "$rc" -eq 2 ] && in_list "$name" "$LAST_FAILED_CONFIGS" && ! grep -q -E "Failed to provision model|STOP: engines do not run" "$dir/driver.log" 2>/dev/null; then
    echo fails; return                               # the config ran and failed at request level (engine error, no output)
  fi
  echo unknown
}
CHECK_VERDICT=; CHECK_RC=
run_check() {   # $1 config name, $2 configs json, $3 tag suffix -> CHECK_VERDICT, CHECK_RC
  local name=$1 json=$2 tag=check-$3 rc v
  run_pass "$tag" "$json" "$CHECK_TIMEOUT"; rc=$?
  v=$(check_verdict "$rc" "$name" "$RES/$tag")
  if [ "$v" = unknown ] && [ "$DRIVER_KILLED" != 1 ]; then
    status "$tag: rc $rc is not evidence about the prompt length (driver or provisioning fault); engine restart and one repeat"
    rm -rf "$RES/$tag-failed1"; mv "$RES/$tag" "$RES/$tag-failed1"
    restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the check repeat failed"
    run_pass "$tag" "$json" "$CHECK_TIMEOUT"; rc=$?
    v=$(check_verdict "$rc" "$name" "$RES/$tag")
  fi
  CHECK_VERDICT=$v; CHECK_RC=$rc
}
stop_safely() {   # $1 reason, $2 problem tag, $3 exit code
  status "STOP: $1"; problems="$problems $2"
  restore_and_release
  echo "stopped: $1; problems:$problems" >"$RES/outcome.txt"
  status "campaign done with problems:$problems"; touch "$RES/.done-with-failures"; exit "$3"
}

lease_state() {   # free | busy | unknown (3 attempts; review C9/C10)
  local out rc try
  for try in 1 2 3; do
    out=$(dut_t 120 lease-free 2>&1); rc=$?
    [ $rc -eq 0 ] && { echo free; return; }
    case $out in *busy*) echo busy; return;; esac
    sleep 60
  done
  echo unknown
}
[ "${CAMPAIGN_LIB_ONLY:-0}" = 1 ] && return 0   # unit tests source the functions only
status "campaign start (PASSES=$PASSES PASS_TAGS=${PASS_TAGS:-none} CHECK=$CHECK DEADLINE_START=$DEADLINE_START PASS_DEADLINE=$PASS_DEADLINE DRIVER_END_BY=$DRIVER_END_BY HANDOFF=$HANDOFF EXPECTED_BASE=$EXPECTED_BASE)"
# ---- wait for the machine: CI lease (600 s grace), then the campaign flock; the deadline applies while waiting
if [ "$NO_WAIT" != 1 ]; then
  until dut_t 120 lease-free >/dev/null 2>&1; do
    past "$DEADLINE_START" && abort_early "past DEADLINE_START while waiting for the CI lease" 3
    status "waiting: CI lease busy (or the DUT did not answer)"; sleep 120
  done
  status "CI lease free"
fi
# another session's campaign (runtron cells on our half, e.g. issue4500-20260918) may run without holding the campaign
# flock: wait until no runtron process and no other campaign.sh of ours runs on the DUT (2026-09-19 13:45 UTC coordination)
until ! timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" "pgrep -u jhan -f '[r]untron[. ]|[i]ssue4500.*campaign[.]sh' >/dev/null"; do
  past "$DEADLINE_START" && abort_early "past DEADLINE_START while waiting for another campaign's runtron processes to end" 3
  status "waiting: another campaign (runtron) is running on the DUT"; sleep 120
done
status "no runtron process on the DUT"
until hold_lock; do
  past "$DEADLINE_START" && abort_early "past DEADLINE_START while waiting for the campaign flock" 3
  status "waiting: campaign flock held by another campaign"; sleep 60
done
past "$DEADLINE_START" && abort_early "past DEADLINE_START before starting" 3

# ---- Bill's marker: launch.sh takes it on jhan's order (2026-09-19, whole machine); if it is present (Bill was active at
# launch time), retry take every 30 min until DEADLINE_START (plan 2a); only jhan can decide to interrupt Bill (review K1, C20)
while :; do
  out=$(bill status 2>&1)
  case $out in
    *"marker absent"*) break;;
    *"marker present"*)
      tout=$(bill take 2>&1); trc=$?; printf '%s\n' "$tout" | tail -1
      case $trc in
        0) status "Bill's marker taken (whole machine)"; break;;
        2) past "$DEADLINE_START" && abort_early "Bill's marker still present at DEADLINE_START (Bill active); jhan decides" 6
           status "waiting: Bill is active (marker present); retry in 30 min"; sleep 1800;;
        *) abort_early "bill-share take rc=$trc (sudo or file error), not 'Bill active'" 6;;
      esac;;
    *) past "$DEADLINE_START" && abort_early "DUT did not answer the marker check until DEADLINE_START" 3
       status "waiting: DUT did not answer the marker check; retry in 2 min"; sleep 120;;
  esac
done

# ---- preflight (read-only) and the base identity = what the nightly installed today; must be the plan's clean arm
PF=$RES/preflight.txt
dut_retry 300 preflight >"$PF" 2>&1 || say "WARNING: preflight did not complete cleanly (see $PF)"
read -r BASE_VERSION BASE_SHA < <(dut_retry 120 installed | tail -1)
say "base package = $BASE_VERSION rinzler sha $BASE_SHA"
case $BASE_VERSION in 2026.*) ;; *) abort_early "unexpected installed tron version '$BASE_VERSION'" 4;; esac
case $BASE_VERSION in *jhan*) abort_early "installed package '$BASE_VERSION' is one of ours, not the nightly's; restore by hand first" 4;; esac
[ "$BASE_VERSION" = "$EXPECTED_BASE" ] || abort_early "installed nightly deb is $BASE_VERSION, the plan's clean arm is $EXPECTED_BASE (canon was built from that source); not comparable, jhan decides" 4
[ -n "$BASE_SHA" ] || abort_early "installed rinzler sha unreadable" 4
grep -q "canon build: status=ok" "$PF" || abort_early "canon build not ok (see $PF)" 5
grep -q "config.env bytes (must be 0): 0" "$PF" || abort_early "config.env is not 0 bytes (see $PF)" 5
grep -q "^== bill marker: absent" "$PF" || abort_early "Bill's marker is present at preflight (see $PF)" 6
if grep -q "num-expert-replicas count: [1-9]" "$PF"; then say "WARNING: the rinzler unit file carries a hand edit (--num-expert-replicas); the nightly's deb file has none"; fi
echo "$BASE_VERSION $BASE_SHA" >"$RES/base-identity.txt"
dut_retry 300 save-base-deb "$BASE_VERSION" || abort_early "could not save a local copy of the nightly deb $BASE_VERSION; ensure-base would depend on the apt repository" 5

# ---- section 6: the check cell on canon (32 users x prompt 8192, then 7168 if that fails); decides the config file
CONFIGS=$H/configs-full.json
if [ "$CHECK" = 1 ]; then
  switch_to canon || stop_safely "package/restart step for the check cell failed" CHECK-SWITCH-FAILED 5
  run_check "$CHECK8192" "$H/check-32u-p8192.json" 32u-p8192
  case $CHECK_VERDICT in
    ok) status "check 32u x 8192 ok in $((LAST_RUN_S/60)) min: all 10 configs stay";;
    fails)
      status "check 32u x 8192 FAILED (rc $CHECK_RC, ${LAST_COMPLETED} configs completed${LAST_FAILED_CONFIGS:+, failed: $LAST_FAILED_CONFIGS}): dropping the prompt-8192 cells; repeating the check at 7168 (plan 2a)"
      restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the 7168 check failed"
      run_check "$CHECK7168" "$H/check-32u-p7168.json" 32u-p7168
      case $CHECK_VERDICT in
        ok) CONFIGS=$H/configs-no8192.json; status "check 32u x 7168 ok in $((LAST_RUN_S/60)) min: 9 configs (no 8192)";;
        fails) CONFIGS=$H/configs-no7168.json; status "check 32u x 7168 FAILED too (rc $CHECK_RC): dropping the 7168 cells as well (the 16K pair is lost); 7 configs";;
        *) stop_safely "check 32u x 7168 failed twice for reasons unrelated to the prompt length (rc $CHECK_RC${DRIVER_KILLED:+, driver killed: $DRIVER_KILLED}); jhan decides" CHECK-DRIVER-FAILED 5;;
      esac;;
    *) stop_safely "check 32u x 8192 failed twice for reasons unrelated to the prompt length (rc $CHECK_RC, driver killed: $DRIVER_KILLED); jhan decides" CHECK-DRIVER-FAILED 5;;
  esac
elif [ -s "$RES/configs-used.txt" ]; then
  CONFIGS=$(cat "$RES/configs-used.txt"); status "CHECK=0: reusing the config file of the earlier check: $CONFIGS"   # review K6
fi
echo "$CONFIGS" >"$RES/configs-used.txt"; cp "$CONFIGS" "$RES/configs-used.json"

# ---- the passes: base canon base canon base canon (pass index k counts the base passes), or PASS_TAGS for a resume (review K7)
if [ -n "$PASS_TAGS" ]; then TAGS=$PASS_TAGS; else TAGS=""; k=0; for arm in $PASSES; do [ "$arm" = base ] && k=$((k+1)); TAGS="$TAGS $arm-pass$k"; done; fi
fails=0; incomplete=""; known_failed=""; stop_reason=""; PASS_S=0; first=1; zero_runs=0; need=3000
for tag in $TAGS; do
  arm=${tag%%-*}
  case $arm in base|canon) ;; *) stop_reason="bad pass tag '$tag'"; break;; esac
  if [ -e "$RES/$tag/perf.json" ] && [ "$RESUME_OVERWRITE" != 1 ]; then status "$tag: results already exist; skipping (RESUME_OVERWRITE=1 to redo)"; continue; fi
  if [ $first = 1 ] && past "$DEADLINE_START"; then stop_reason="past DEADLINE_START before the first pass ($tag)"; break; fi
  if past "$PASS_DEADLINE"; then stop_reason="past PASS_DEADLINE before $tag"; break; fi
  ls_state=$(lease_state)
  case $ls_state in
    free) ;;
    busy) stop_reason="CI lease busy before $tag; stopping safely (plan 2a)"; break;;
    *) stop_reason="DUT did not answer the lease check 3 times before $tag; stopping safely"; break;;
  esac
  need=$(( PASS_S + 600 )); [ "$need" -lt 3000 ] && need=3000   # a pass must be able to finish before DRIVER_END_BY (measured pass + 10 min, at least 50 min)
  if [ $(( $(ts "$DRIVER_END_BY") - $(now_s) )) -lt "$need" ]; then stop_reason="not enough time before DRIVER_END_BY for $tag (need about $((need/60)) min)"; break; fi
  first=0
  if ! switch_to "$arm"; then stop_reason="package/restart step for $tag failed"; fails=$((fails+1)); break; fi
  run_pass "$tag" "$CONFIGS" "$DRIVER_TIMEOUT"; rc=$?
  [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during $tag: operator stop"; fails=$((fails+1)); break; fi
  if [ "$LAST_COMPLETED" -eq 0 ] && ! grep -q 'Running round' "$RES/$tag/driver.log" 2>/dev/null; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi   # one-config campaign (review 2026-09-20): count only runs that never reached the benchmark; a request-level failure follows plan 2a (repeat once, then next pass)
  [ $rc -eq 0 ] && continue
  fails=$((fails+1))
  if [ $rc -eq 124 ]; then status "$tag: the driver ran past its timeout (rc 124); no repeat, completed configs stay in perf.json raw records (D6)"; incomplete="$incomplete $tag"; continue; fi
  if [ $(( $(ts "$DRIVER_END_BY") - $(now_s) )) -lt "$need" ]; then stop_reason="no time for a repeat of $tag before DRIVER_END_BY (review C23)"; incomplete="$incomplete $tag"; break; fi
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken (review C21)"; incomplete="$incomplete $tag"; break; fi
  # plan 2a: restart the engines and repeat the pass once, unless every failed config is a known systematic failure (failed twice before)
  systematic=0   # one-config campaign (review 2026-09-20): plan 2a repeats EVERY failed pass once; the Saturday known-failure shortcut would skip the repeat after one double failure
  # (Saturday logic, disabled: systematic=1; if [ -z "$LAST_FAILED_CONFIGS" ]; then systematic=0; else for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$known_failed" || systematic=0; done; fi)
  if [ $systematic = 1 ]; then status "$tag: the failed configs ($LAST_FAILED_CONFIGS) are known systematic failures; not repeating"; incomplete="$incomplete $tag"; continue; fi
  status "$tag: repeating the pass once after an engine restart (plan 2a)"
  rm -rf "$RES/$tag-failed1"; mv "$RES/$tag" "$RES/$tag-failed1"
  first_failed=$LAST_FAILED_CONFIGS
  restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the repeat failed"
  run_pass "$tag" "$CONFIGS" "$DRIVER_TIMEOUT"; rc=$?
  [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during the repeat of $tag: operator stop"; break; fi
  if [ "$LAST_COMPLETED" -eq 0 ] && ! grep -q 'Running round' "$RES/$tag/driver.log" 2>/dev/null; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi   # one-config campaign (review 2026-09-20): count only runs that never reached the benchmark; a request-level failure follows plan 2a (repeat once, then next pass)
  if [ $rc -eq 0 ]; then say "$tag: repeat ok"; continue; fi
  status "$tag: failed twice (rc $rc); continuing with the next pass (gap reported)"; incomplete="$incomplete $tag"
  for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$first_failed" && known_failed="$known_failed $c"; done   # systematic = failed in both runs (review C11/C12)
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken (review C21)"; break; fi
done
[ -n "$stop_reason" ] && status "passes stopped: $stop_reason"

# ---- restore the nightly's package, production up, Bill's marker, the flock
restore_and_release
echo "incomplete passes:${incomplete:- none}; stop reason: ${stop_reason:-none}; problems:${problems:- none}; known systematic failures:${known_failed:- none}" >"$RES/outcome.txt"
if [ $fails -eq 0 ] && [ -z "$problems" ] && [ -z "$stop_reason" ]; then status "campaign done"; touch "$RES/.done"
else status "campaign done with $fails pass failure(s); incomplete:${incomplete:- none}; stop: ${stop_reason:-none}; problems:${problems:- none}"; touch "$RES/.done-with-failures"; fi
