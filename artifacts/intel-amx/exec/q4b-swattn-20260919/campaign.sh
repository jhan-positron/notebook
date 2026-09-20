#!/usr/bin/env bash
# q4b-swattn campaign 2026-09-19/20: the AMX attention kernel's gain on qwen3-4b tp2 with SOFTWARE attention forced on both
# arms (USE_HW_ATTN=0), against prompt length, at the nightly's load of 2 users per engine, run per
# CI-test/status/qwen3-4b-Saturday-plan.md on the WHOLE of delphi-3bda with the nightly's own client (systems_test
# scripts/perf.py through st_ci_perf.py) against rinzler engines provisioned by platformd in the nightly layout (4 tp2
# engines behind Caddy). Two arms, interleaved, three passes each:
#   base  = the nightly deb 2026.09.18-3faba6d0 (no AMX code), saved copy /var/tmp/jhan/canon-ci-20260918/nightly.deb;
#           dut.sh ensure-base installs it (EXPECTED_BASE / EXPECTED_BASE_SHA = the base ARM identity, plan section 1)
#   canon = tron_2026.09.18-0594dc54-jhan-ci-canon (main 3faba6d0 + deb preset TRON_AMX_DISPATCH=ON, no PR #4424),
#           /var/tmp/jhan/canon-ci-20260918/target.deb; dut.sh ensure-canon
# Every pass runs the 9 qwen3-4b tp2 configs of configs-full.json (prompt 1024 to 8192 at 8 users, plan section 5).
# Before the first pass one canon cell at 8 users x prompt 8192 checks that the longest prompt works (plan section 6);
# if it fails the 8192 cell is dropped and the check is repeated at 7168 (plan section 2a). CHECK_ONLY=1 runs exactly
# that (preflight, hwattn-off, check cell, restore) and no pass: the Saturday-night run ahead of the Sunday passes.
#
# Copied 2026-09-19 from exec/l8b-levers-20260919/campaign.sh (reviewed twice there: review-findings.txt,
# review2-findings.txt). Rules carried over: engine RESTART after every package switch (apt never restarts engines and the
# legacy platformd path never restarts a same-model engine); check-cell verdict rules; one repeat of a failed pass after an
# engine restart; deadlines DEADLINE_START (campaign start), PASS_DEADLINE (no later pass start), DRIVER_END_BY (hard end);
# a busy CI lease before a pass stops the campaign safely; Bill's marker retried every 30 min while he is active.
# New here (plan section 4):
#   * software attention on BOTH arms: dut.sh hwattn-off writes USE_HW_ATTN=0 to /opt/positron/user/config.env after the
#     preflight (the unit reads it at engine START, EnvironmentFile=- last, so it wins over instance-N.env); every engine
#     start in the campaign follows a serving-down; dut.sh verify-env after every serving-up and st_ci_perf.py after every
#     provisioning (CI_MIMIC_REQUIRE_HWATTN0=1, driver rc 8) prove that every engine carries the key; one engine restart
#     if not, then a safe stop (plan 2a). The restore clears the file FIRST (hwattn-clear), before production comes up.
#   * restore-target rule (plan section 1): the package found installed at preflight is the RESTORE target (saved as
#     restore.deb when it differs from the base arm's nightly.deb) and is reinstalled at the end; the base ARM stays
#     EXPECTED_BASE. Tonight both are the same deb; after the Sunday nightly they differ.
#   * NOT_BEFORE: the Sunday launch sleeps until this time before the lease wait (no lease file exists before the nightly
#     takes it at about 03:38 UTC, so a lease-free test alone would start the campaign at once).
#   * the check cell also fails when the server-counted prompt tokens are outside [prompt_length - 400, prompt_length + 400]
#     (plan section 6: a silent truncation, as with llama-3.1-8b at 4096, would make the cell measure something else).
#   * analyze.py and gen_report.py run at the end (plan sections 7 and 9); the render check and the artifact publish are
#     the agent's steps.
# End state (HANDOFF=up, plan section 2): config.env 0 bytes, the restore-target deb reinstalled, production engines up
# (FPGA attention again), Bill's marker released, flock released.
#
# TO STOP EARLY: kill -TERM <pid of this script> (the pid launch.sh printed; NOT -9). That stops the driver and runs
# the restore + release path (hwattn-clear first). Do NOT pkill st_ci_perf.py alone: a driver killed by a signal
# (rc 130/137/143) is read as an operator stop and ends the campaign, but only this script runs the restore.
# RECOVERY if this script died without its trap (SIGKILL, OOM, host reboot): on delphi-3bda
#   kill $(awk '/^held pid/{print $3}' ~/workspace/intel-AMX/exec/results/q4b-swattn-20260919/.lock.out); flock -n /var/tmp/jhan/3bda-campaign.lock true && echo flock free
#   bash ~/workspace/intel-AMX/exec/q4b-swattn-20260919/dut.sh hwattn-clear          (config.env must print 0 bytes)
#   cat ~/workspace/intel-AMX/exec/results/q4b-swattn-20260919/base-identity.txt   (line "restore VERSION SHA FILE")
#   bash .../dut.sh ensure-base VERSION SHA FILE
#   IDLE_MIN=5 bash .../dut.sh serving-down && bash .../dut.sh serving-up
#   bash ~/workspace/intel-AMX/exec/bill-share.sh release; stat -c %s /opt/positron/user/config.env   (must print 0)
# RESUME: PASS_TAGS="canon-pass2 base-pass3 canon-pass3" CHECK=0 launch.sh reruns only those tags (a tag whose
# perf.json exists is skipped unless RESUME_OVERWRITE=1); CHECK=0 reuses configs-used.txt from the earlier check.
#
# Runs on the CLIENT host (claude-agentsrv), detached (launch.sh). DUT steps go over ssh (dut.sh).
# Env knobs: NOT_BEFORE, DEADLINE_START, PASS_DEADLINE, DRIVER_END_BY, DRIVER_TIMEOUT (s per pass, default 5400), CHECK_TIMEOUT
#            (s for the section-6 cell, default 1200), PASSES (default "base canon base canon base canon") or PASS_TAGS,
#            CHECK (1|0), CHECK_ONLY (0|1), AMX_PROBE (1|0), HANDOFF (up|down), NO_WAIT=1 (skip the lease wait),
#            EXPECTED_BASE, EXPECTED_BASE_SHA, REPORT (html path), IDLE_MIN_SWITCH (journal-quiet minutes before an
#            intra-campaign engine restart, default 1; handoff uses 5).
# Traps carried over: never ${VAR:+x} with a 0/1 flag; the remote flock holder's pid must be killed explicitly and the
# kill verified; never edit st_ci_perf.py or this file while a pass runs; apt never restarts engines; pgrep -f patterns
# anchored so a checker does not match itself; `rc=$?` after `if cmd` reads the if-statement's status, capture rc first;
# config.env is read at engine start only (write or clear, then serving-down, then start).
set -u
NAME=q4b-swattn-20260919
H=/home/jhan/workspace/intel-AMX/exec/$NAME
RES=/home/jhan/workspace/intel-AMX/exec/results/$NAME
ST=/home/jhan/workspace/ai-runs/systems_test
PY=$ST/.venv/bin/python
DUT_ALIAS=delphi-3bda
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ServerAliveCountMax=4"
LOCK=/var/tmp/jhan/3bda-campaign.lock
HOLDER_LIFE=50400   # s; recomputed before hold_lock from DRIVER_END_BY + 2 h (review 2026-09-19: a fixed 14 h from a 13:00 start ended before the passes)
EXPECTED_BASE=${EXPECTED_BASE:-2026.09.18-3faba6d0}     # the base ARM (plan section 1): the nightly deb canon was built from; installed from the saved nightly.deb
EXPECTED_BASE_SHA=${EXPECTED_BASE_SHA:-27e6883c2e8696b861589272470d5f6a4ec5485f6e8cd2ad163ae699f1dc6616}   # sha256 of its /opt/positron/bin/rinzler (l8b-levers base-identity.txt)
NOT_BEFORE=${NOT_BEFORE:-}                                # Sunday launch: sleep until this UTC time before the lease wait (no lease file exists before the nightly takes it)
DEADLINE_START=${DEADLINE_START:-2026-09-20T19:30:00Z}   # plan section 2, Sunday window: the campaign (lease, flock, marker wait, first pass) must START by this
PASS_DEADLINE=${PASS_DEADLINE:-2026-09-20T23:45:00Z}     # no further pass starts after this
DRIVER_END_BY=${DRIVER_END_BY:-2026-09-21T01:00:00Z}     # hard: the restore needs up to 16 min; pre-CI hold 01:40Z, ci-runner-stop 02:45Z, nightly apt reinstall ~03:39Z
NO_WAIT=${NO_WAIT:-0}; AMX_PROBE=${AMX_PROBE:-1}; HANDOFF=${HANDOFF:-up}
DRIVER_TIMEOUT=${DRIVER_TIMEOUT:-5400}; CHECK_TIMEOUT=${CHECK_TIMEOUT:-1200}
CHECK_ONLY=${CHECK_ONLY:-0}                              # 1 = preflight, hwattn-off, check cell, restore; no pass (the Saturday-night run, plan section 6)
REPORT=${REPORT:-/home/jhan/workspace/intel-AMX/CI-test/status/Saturday-qwen3-4b.html}
PASSES=${PASSES:-"base canon base canon base canon"}
PASS_TAGS=${PASS_TAGS:-}
RESUME_OVERWRITE=${RESUME_OVERWRITE:-0}
CHECK=${CHECK:-1}
IDLE_MIN_SWITCH=${IDLE_MIN_SWITCH:-1}
CHECK8192=ingested_qwen_3_4b_instruct_2507_tp2_8u_p8192
CHECK7168=ingested_qwen_3_4b_instruct_2507_tp2_8u_p7168
mkdir -p "$RES"
# the check-only run and the Sunday run share this directory: keep the previous run's end state under prev-<time>-<name> (review 2026-09-19)
for f in .done .done-with-failures .done-aborted .done-check outcome.txt outcome-check.txt preflight.txt .status; do
  [ -e "$RES/$f" ] && mv -f "$RES/$f" "$RES/prev-$(date -u +%Y%m%dT%H%M%SZ)-${f#.}"
done
STATUS=$RES/.status
say() { echo "$(date -u +%FT%TZ) $*"; }
nap() { sleep "$1" & wait $!; }   # interruptible sleep: a TERM/INT/HUP runs the trap at once (a foreground sleep defers it until it ends)
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
  verify_hwattn || { say "switch_to $arm: engines without USE_HW_ATTN=0"; return 1; }
  return 0
}
HWATTN_BROKEN=0; VERIFY_FAIL=""
verify_hwattn() {   # plan 2a: every engine must carry USE_HW_ATTN=0 after it starts; one engine restart if not; still failing -> the caller stops safely
  local rc try
  for try in 1 2; do
    dut_retry_ssh 300 verify-env; rc=$?   # ssh-level failures retried; dut.sh's own rc 1/2 is final
    case $rc in
      0) VERIFY_FAIL=""; return 0;;
      1) VERIFY_FAIL="an engine lacks USE_HW_ATTN=0 (verify-env rc 1)";;
      2) VERIFY_FAIL="rinzler pid count differs from platformd's configured engine count (verify-env rc 2)";;
      *) VERIFY_FAIL="verify-env rc $rc (ssh or script failure)";;
    esac
    [ "$try" = 1 ] || break
    status "verify-env: $VERIFY_FAIL; restarting the engines once and re-checking (plan 2a)"
    restart_engines "$IDLE_MIN_SWITCH" || { say "verify_hwattn: engine restart failed"; return 1; }
  done
  [ $rc -eq 1 ] && HWATTN_BROKEN=1
  status "verify-env after a restart: $VERIFY_FAIL; the caller stops safely"; return 1
}

# ---- restore + handoff + release: runs exactly once, on the normal path AND on a signal
BASE_VERSION=; BASE_SHA=; RESTORE_VERSION=; RESTORE_SHA=; RESTORE_FILE=nightly.deb; HWATTN_SET=0; DRIVER_PID=; RESTORED=0; problems=""
restore_and_release() {
  [ "$RESTORED" = 1 ] && return 0; RESTORED=1
  # the DUT outage that stopped the campaign may still last: wait for it (bounded 30 min), then retry ssh-level failures (D1)
  wait_dut 1800 || { problems="$problems DUT-UNREACHABLE"; status "RESTORE: DUT unreachable for 30 min; steps below will fail; see the RECOVERY sequence in the header"; }
  # config.env FIRST (plan section 4): production engines must never start with USE_HW_ATTN=0 (they would run software attention)
  if [ "$HWATTN_SET" = 1 ]; then
    if dut_retry_ssh 120 hwattn-clear; then HWATTN_SET=0; say "hwattn-clear ok: config.env 0 bytes"
    else
      local cb; cb=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" 'stat -c %s /opt/positron/user/config.env' 2>/dev/null)
      if [ "$cb" = 0 ]; then HWATTN_SET=0; say "hwattn-clear reported a failure but config.env is 0 bytes: treated as cleared"
      else problems="$problems HWATTN-CLEAR-FAILED"; status "HWATTN-CLEAR FAILED (config.env ${cb:-unread} bytes): USE_HW_ATTN=0 may still be set; production is NOT brought up (jhan: sudo truncate -s 0 /opt/positron/user/config.env, then dut.sh serving-down, serving-up)"; fi
    fi
  fi
  if [ -n "$RESTORE_VERSION" ]; then
    local restored=0
    if dut_retry_ssh 900 ensure-base "$RESTORE_VERSION" "$RESTORE_SHA" "$RESTORE_FILE"; then restored=1; status "restore ok: $(dut_retry 120 installed)"; else problems="$problems RESTORE-FAILED"; status "RESTORE FAILED: $(dut_retry 120 installed) (wanted $RESTORE_VERSION from $RESTORE_FILE); jhan must reinstall tron by hand"; fi
    if [ "$HANDOFF" = up ] && [ $restored = 1 ] && [ "$HWATTN_SET" = 0 ]; then
      # engines of the last pass still run the deleted binary until restarted: down, then up (skip up when down failed)
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then dut_retry_ssh 900 serving-up || { problems="$problems SERVING-UP-FAILED"; say "WARNING serving-up did not complete"; }
      else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log); engines may still run a deleted binary"; fi
    elif [ "$HANDOFF" = up ]; then
      # never bring production up on a binary that is not the nightly's, or with USE_HW_ATTN=0 still in config.env: down only, jhan decides
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then status "restore failed or config.env not cleared: production engines taken DOWN (not brought up)"; else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: restore failed (or config.env not cleared) and serving-down failed"; fi
    else
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then status "handoff: production engines down, hugepages free"
      else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log)"; fi
    fi
    local cfgbytes n
    for n in 1 2 3; do cfgbytes=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" 'stat -c %s /opt/positron/user/config.env' 2>/dev/null); [ -n "$cfgbytes" ] && break; sleep 30; done
    if [ "$cfgbytes" = 0 ]; then say "config.env is 0 bytes (ok)"; else problems="$problems CONFIG-ENV-${cfgbytes:-unread}-BYTES"; say "WARNING: /opt/positron/user/config.env has '${cfgbytes:-unread}' bytes (must be 0)"; fi
  else
    say "no restore target recorded (aborted before preflight): nothing to restore"
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
abort_early() { status "ABORT: $1"; RESTORE_VERSION=; restore_and_release; echo "aborted: $1" >"$RES/outcome.txt"; touch "$RES/.done-aborted"; exit "$2"; }

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
      CI_MIMIC_CONFIGS_JSON=$cfg CI_MIMIC_INSTALLED_SHA=$sha CI_MIMIC_AMX_PROBE=$AMX_PROBE CI_MIMIC_REQUIRE_HWATTN0=${REQUIRE_HWATTN0:-1} \
      CI_MIMIC_LEASE_CHECK=${LEASE_CHECK:-1} CI_MIMIC_DUT_HELPER=$H/dut.sh \
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
PT_BAND_LOW=${PT_BAND_LOW:-800}; PT_BAND_HIGH=${PT_BAND_HIGH:-400}   # server-counted prompt tokens accepted in [plen - LOW, plen + HIGH] (plan section 6; qwen template counts below the harness's llama-header count)
check_cell_ok() {   # $1 perf.json, $2 prompt_length, $3 AMX_PROBE (1|0) -> rc 0 ok | 1 prompt tokens outside the band | 2 record incomplete | 3 AMX-busy missing or below 10 G | 4 FUSE limit below the cell's need
  python3 - "$1" "$2" "$3" "$PT_BAND_LOW" "$PT_BAND_HIGH" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); L = int(sys.argv[2]); probe = sys.argv[3] == "1"; blo = int(sys.argv[4]); bhi = int(sys.argv[5])
raw = d.get("raw") or []
if not raw:
    print("no config record in perf.json"); sys.exit(2)
r = raw[0]
pt = r.get("prompt_tokens") or []
if not pt:
    print("no server-counted prompt tokens recorded"); sys.exit(2)
lo, hi = min(pt), max(pt)
amx = r.get("amx_busy_cycles")
lim = r.get("fuse_limits") or {}
vals = [(k, v.get("max_prompt_tokens"), v.get("max_total_tokens")) for k, v in sorted(lim.items(), key=lambda kv: str(kv[0]))]
need_total = L + int(r.get("generate_length") or 1536)
msg = [f"server-counted prompt tokens {lo} to {hi} for prompt_length {L} over {len(pt)} requests (band {L - blo} to {L + bhi})",
       f"AMX-busy {amx} cycles" + ("" if probe else " (probe off)"),
       "FUSE limits per engine (max_prompt_tokens/max_total_tokens): " + (", ".join(f"{k}: {p}/{t}" for k, p, t in vals) or "NOT RECORDED")]
print("; ".join(msg))
if not (lo >= L - blo and hi <= L + bhi):
    sys.exit(1)
if probe and (amx is None or amx < 10e9):
    sys.exit(3)
if not vals:
    print("WARNING FUSE limits not recorded (/var/run/rinzler/N/rinzler/config/ unread); the prompt-token band is the truncation test")
    sys.exit(0)
if any((p is None or t is None or p < L or t < need_total) for _, p, t in vals):
    sys.exit(4)
sys.exit(0)
PY
}
CHECK_VERDICT=; CHECK_RC=; CHECK_RC1=; CHECK_WHY=
run_check() {   # $1 config name, $2 configs json, $3 tag suffix -> CHECK_VERDICT (ok|fails|unknown|lease|stop), CHECK_RC, CHECK_WHY
  local name=$1 json=$2 tag=check-$3 rc v plen ctxt crc left
  plen=${name##*_p}; CHECK_WHY=; CHECK_RC1=
  left=$(( $(ts "$DRIVER_END_BY") - $(now_s) ))
  if [ "$left" -lt $(( CHECK_TIMEOUT + 60 )) ]; then   # never run the check with a capped timeout: a cap would read as a prompt-length failure (review 2026-09-19)
    CHECK_VERDICT=unknown; CHECK_RC=3; CHECK_WHY="only $((left/60)) min left before DRIVER_END_BY, less than CHECK_TIMEOUT $CHECK_TIMEOUT s: the check cannot run with its full timeout (no evidence about the prompt length)"; status "$tag: $CHECK_WHY"; return
  fi
  run_pass "$tag" "$json" "$CHECK_TIMEOUT"; rc=$?; CHECK_RC1=$rc
  if [ $rc -eq 9 ]; then CHECK_VERDICT=lease; CHECK_RC=$rc; CHECK_WHY="CI lease became busy during the check cell (driver rc 9)"; return; fi
  v=$(check_verdict "$rc" "$name" "$RES/$tag")
  if [ "$v" = unknown ] && [ "$DRIVER_KILLED" != 1 ]; then
    status "$tag: rc $rc is not evidence about the prompt length (driver or provisioning fault); engine restart and one repeat"
    rm -rf "$RES/$tag-failed1"; mv "$RES/$tag" "$RES/$tag-failed1"
    restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the check repeat failed"
    left=$(( $(ts "$DRIVER_END_BY") - $(now_s) ))
    if [ "$left" -lt $(( CHECK_TIMEOUT + 60 )) ]; then CHECK_VERDICT=unknown; CHECK_RC=3; CHECK_WHY="first run rc $rc; no time left for a repeat with the full timeout"; status "$tag: $CHECK_WHY"; return; fi
    run_pass "$tag" "$json" "$CHECK_TIMEOUT"; rc=$?
    if [ $rc -eq 9 ]; then CHECK_VERDICT=lease; CHECK_RC=$rc; CHECK_WHY="CI lease became busy during the check repeat (driver rc 9)"; return; fi
    v=$(check_verdict "$rc" "$name" "$RES/$tag")
  fi
  if [ "$v" = ok ]; then   # plan section 6: prompt tokens (no silent truncation), AMX-busy (canon identity), FUSE limits (server capacity)
    ctxt=$(check_cell_ok "$RES/$tag/perf.json" "$plen" "$AMX_PROBE"); crc=$?
    say "$tag: $ctxt"
    case $ctxt in *"FUSE limits not recorded"*) problems="$problems FUSE-LIMITS-UNREAD";; esac
    case $crc in
      0) ;;
      1) v=fails; CHECK_WHY="server-counted prompt tokens outside the band: the cell does not measure prompt $plen (plan 2a drop rule)";;
      4) v=fails; CHECK_WHY="a rinzler FUSE limit is below what the cell needs: the server would cap the prompt (plan 2a drop rule)";;
      3) v=stop; CHECK_WHY="AMX-busy below 10 G cycles or unreadable on the canonical deb: the arm's identity is not shown (plan section 6)";;
      *) v=stop; CHECK_WHY="check record incomplete (check_cell_ok rc $crc)";;
    esac
    [ "$v" = ok ] || status "$tag: $CHECK_WHY"
  fi
  [ -n "$CHECK_WHY" ] || CHECK_WHY="driver rc $rc (first run rc $CHECK_RC1)"
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
# ---- knob sanity (review 2026-09-19): every date knob must parse (ts() prints nothing for a bad one and past() would then never fire),
# the deadlines must be ordered, and a launch far ahead of its window must carry NOT_BEFORE (no lease file exists before the nightly takes it)
for v in NOT_BEFORE DEADLINE_START PASS_DEADLINE DRIVER_END_BY; do
  [ -z "${!v}" ] && continue
  ts "${!v}" >/dev/null 2>&1 || abort_early "knob $v='${!v}' is not a date that 'date -u -d' accepts" 2
done
[ "$(ts "$DEADLINE_START")" -lt "$(ts "$PASS_DEADLINE")" ] && [ "$(ts "$PASS_DEADLINE")" -lt "$(ts "$DRIVER_END_BY")" ] || abort_early "deadline order wrong: need DEADLINE_START ($DEADLINE_START) < PASS_DEADLINE ($PASS_DEADLINE) < DRIVER_END_BY ($DRIVER_END_BY)" 2
[ -z "$NOT_BEFORE" ] || [ "$(ts "$NOT_BEFORE")" -lt "$(ts "$DEADLINE_START")" ] || abort_early "NOT_BEFORE $NOT_BEFORE is not before DEADLINE_START $DEADLINE_START" 2
past "$DRIVER_END_BY" && abort_early "DRIVER_END_BY $DRIVER_END_BY is already past" 2
[ -n "$NOT_BEFORE" ] || [ $(( $(ts "$DEADLINE_START") - $(now_s) )) -le 28800 ] || abort_early "the start is more than 8 h before DEADLINE_START and NOT_BEFORE is empty: the campaign would start now and could run into the nightly (plan section 2); set NOT_BEFORE" 3
status "campaign start (PASSES=$PASSES PASS_TAGS=${PASS_TAGS:-none} CHECK=$CHECK CHECK_ONLY=$CHECK_ONLY NOT_BEFORE=${NOT_BEFORE:-none} DEADLINE_START=$DEADLINE_START PASS_DEADLINE=$PASS_DEADLINE DRIVER_END_BY=$DRIVER_END_BY HANDOFF=$HANDOFF EXPECTED_BASE=$EXPECTED_BASE DRIVER_TIMEOUT=$DRIVER_TIMEOUT CHECK_TIMEOUT=$CHECK_TIMEOUT PT_BAND=-$PT_BAND_LOW/+$PT_BAND_HIGH)"
# ---- Sunday launch: sleep until NOT_BEFORE. The nightly takes the lease at about 03:38 UTC; before that no lease file exists, so a
# lease-free test alone would start the campaign at once and run into the CI window (plan section 2).
if [ -n "$NOT_BEFORE" ]; then
  nb=$(ts "$NOT_BEFORE")
  while [ "$(now_s)" -lt "$nb" ]; do
    left=$(( nb - $(now_s) )); [ "$left" -gt 1800 ] && left=1800; [ "$left" -ge 1 ] || left=1
    status "waiting: NOT_BEFORE $NOT_BEFORE (next check in $((left/60)) min)"; nap "$left"
  done
  status "NOT_BEFORE $NOT_BEFORE passed; waiting for the CI lease next"
fi
# ---- wait for the machine: CI lease (600 s grace), then the campaign flock; the deadline applies while waiting
if [ "$NO_WAIT" != 1 ]; then
  until dut_t 120 lease-free >/dev/null 2>&1; do
    past "$DEADLINE_START" && abort_early "past DEADLINE_START while waiting for the CI lease" 3
    status "waiting: CI lease busy (or the DUT did not answer)"; nap 120
  done
  status "CI lease free"
fi
# another session's campaign (runtron cells on our half, e.g. issue4500-20260918) may run without holding the campaign
# flock: wait until no runtron process and no other campaign.sh of ours runs on the DUT (2026-09-19 13:45 UTC coordination)
while :; do   # pgrep rc 1 = no process; rc 0 = a peer runs; anything else = ssh failure (never read as 'no process'; review 2026-09-19)
  timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" "pgrep -u jhan -f '[r]untron[. ]|[i]ssue4500.*campaign[.]sh' >/dev/null"; prc=$?
  case $prc in
    1) break;;
    0) past "$DEADLINE_START" && abort_early "past DEADLINE_START while waiting for another campaign's runtron processes to end" 3
       status "waiting: another campaign (runtron) is running on the DUT"; nap 120;;
    *) past "$DEADLINE_START" && abort_early "DUT did not answer the runtron check until DEADLINE_START" 3
       status "waiting: DUT did not answer the runtron check (rc $prc); retry in 2 min"; nap 120;;
  esac
done
status "no runtron process on the DUT"
HOLDER_LIFE=$(( $(ts "$DRIVER_END_BY") + 7200 - $(now_s) )); [ "$HOLDER_LIFE" -gt 3600 ] || HOLDER_LIFE=3600   # the remote flock holder outlives the hard end by 2 h
until hold_lock; do
  past "$DEADLINE_START" && abort_early "past DEADLINE_START while waiting for the campaign flock" 3
  status "waiting: campaign flock held by another campaign"; nap 60
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
           if [ "$NO_WAIT" != 1 ]; then case $(lease_state) in free) ;; busy) abort_early "CI lease became busy while waiting for Bill's marker (plan 2a)" 3;; *) abort_early "DUT did not answer the lease check while waiting for Bill's marker" 3;; esac; fi
           status "waiting: Bill is active (marker present); retry in 30 min"; nap 1800;;
        *) abort_early "bill-share take rc=$trc (sudo or file error), not 'Bill active'" 6;;
      esac;;
    *) past "$DEADLINE_START" && abort_early "DUT did not answer the marker check until DEADLINE_START" 3
       status "waiting: DUT did not answer the marker check; retry in 2 min"; nap 120;;
  esac
done

# ---- preflight (read-only) and the base identity = what the nightly installed today; must be the plan's clean arm
PF=$RES/preflight.txt
dut_retry 300 preflight >"$PF" 2>&1 || say "WARNING: preflight did not complete cleanly (see $PF)"
read -r RESTORE_VERSION RESTORE_SHA < <(dut_retry 120 installed | tail -1)
say "installed at preflight = $RESTORE_VERSION rinzler sha $RESTORE_SHA (the RESTORE target); base ARM = $EXPECTED_BASE sha $EXPECTED_BASE_SHA (plan section 1)"
case $RESTORE_VERSION in 2026.*) ;; *) abort_early "unexpected installed tron version '$RESTORE_VERSION'" 4;; esac
case $RESTORE_VERSION in *jhan*) abort_early "installed package '$RESTORE_VERSION' is one of ours, not the nightly's; restore by hand first" 4;; esac
[[ $RESTORE_SHA =~ ^[0-9a-f]{64}$ ]] || abort_early "installed rinzler sha unreadable" 4
BASE_VERSION=$EXPECTED_BASE; BASE_SHA=$EXPECTED_BASE_SHA
grep -q "canon build: status=ok" "$PF" || abort_early "canon build not ok (see $PF)" 5
grep -q "config.env bytes (must be 0): 0" "$PF" || abort_early "config.env is not 0 bytes (see $PF)" 5
grep -q "^== bill marker: absent" "$PF" || abort_early "Bill's marker is present at preflight (see $PF)" 6
if grep -q "num-expert-replicas count: [1-9]" "$PF"; then say "WARNING: the rinzler unit file carries a hand edit (--num-expert-replicas); the nightly's deb file has none"; fi
if [ "$RESTORE_VERSION" = "$BASE_VERSION" ]; then RESTORE_FILE=nightly.deb; else RESTORE_FILE=restore.deb; say "restore target $RESTORE_VERSION differs from the base arm: saved as restore.deb and reinstalled at the end (plan section 1)"; fi
{ echo "base $BASE_VERSION $BASE_SHA nightly.deb"; echo "restore $RESTORE_VERSION $RESTORE_SHA $RESTORE_FILE"; } >"$RES/base-identity.txt"
dut_retry 300 save-base-deb "$BASE_VERSION" nightly.deb || abort_early "the base arm's deb $BASE_VERSION is not saved as nightly.deb and could not be downloaded" 5
if [ "$RESTORE_FILE" = restore.deb ]; then dut_retry 300 save-base-deb "$RESTORE_VERSION" restore.deb || abort_early "could not save a local copy of the installed deb $RESTORE_VERSION (the restore target)" 5; fi

# ---- the waits above (runtron, flock, Bill's marker retries) can last until DEADLINE_START: re-test the CI lease right before the first
# state change (plan 2a: lease busy = stop safely). Nothing is written or installed yet, so abort_early (marker and flock back) is enough.
if [ "$NO_WAIT" != 1 ]; then
  case $(lease_state) in free) ;; busy) abort_early "CI lease busy after the waits, before hwattn-off and the check cell (plan 2a)" 3;; *) abort_early "DUT did not answer the lease check before hwattn-off" 3;; esac
fi
# ---- software attention on BOTH arms (plan sections 1 and 4): USE_HW_ATTN=0 through config.env, read at every engine start. Every
# engine start from here on follows a serving-down (switch_to, restart_engines, or platformd's own restart at a model change), and the
# restore clears the file BEFORE production comes up. HWATTN_SET is raised before the write so a half-written file is still cleared.
HWATTN_SET=1
dut_retry_ssh 120 hwattn-off || stop_safely "hwattn-off failed: config.env not written" HWATTN-OFF-FAILED 5

# ---- section 6: the check cell on canon (8 users x prompt 8192, then 7168 if that fails); decides the config file
CONFIGS=$H/configs-full.json
if [ "$CHECK" != 1 ] && [ ! -s "$RES/configs-used.txt" ]; then
  status "CHECK=$CHECK but no configs-used.txt from an earlier check cell (plan section 6 requires the check before the first pass): running the check cell now"
  CHECK=1
fi
if [ "$CHECK" = 1 ]; then
  switch_to canon || stop_safely "switch to canon before the check cell failed: ${VERIFY_FAIL:-package or restart step} (plan 2a)" CHECK-SWITCH-FAILED 5
  run_check "$CHECK8192" "$H/check-8u-p8192.json" 8u-p8192
  case $CHECK_VERDICT in
    ok) status "check 8u x 8192 ok in $((LAST_RUN_S/60)) min ($CHECK_WHY): all 9 configs stay";;
    fails)
      status "check 8u x 8192 FAILED ($CHECK_WHY; rc $CHECK_RC, ${LAST_COMPLETED} configs completed${LAST_FAILED_CONFIGS:+, failed: $LAST_FAILED_CONFIGS}): dropping the prompt-8192 cell; repeating the check at 7168 (plan 2a)"
      restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the 7168 check failed"
      run_check "$CHECK7168" "$H/check-8u-p7168.json" 8u-p7168
      case $CHECK_VERDICT in
        ok) CONFIGS=$H/configs-no8192.json; status "check 8u x 7168 ok in $((LAST_RUN_S/60)) min ($CHECK_WHY): 8 configs (no 8192)";;
        fails) CONFIGS=$H/configs-no7168.json; status "check 8u x 7168 FAILED too ($CHECK_WHY; rc $CHECK_RC): dropping the 7168 cell as well; 7 configs";;
        lease) stop_safely "CI lease became busy during the 7168 check (plan 2a)" LEASE-BUSY 3;;
        stop) stop_safely "check 8u x 7168: $CHECK_WHY; jhan decides" CHECK-IDENTITY 5;;
        *) stop_safely "check 8u x 7168 gave no evidence about the prompt length ($CHECK_WHY; rc $CHECK_RC, first run rc ${CHECK_RC1:-none}, driver killed: $DRIVER_KILLED); jhan decides" CHECK-DRIVER-FAILED 5;;
      esac;;
    lease) stop_safely "CI lease became busy during the check cell (plan 2a)" LEASE-BUSY 3;;
    stop) stop_safely "check 8u x 8192: $CHECK_WHY; jhan decides" CHECK-IDENTITY 5;;
    *) stop_safely "check 8u x 8192 gave no evidence about the prompt length ($CHECK_WHY; rc $CHECK_RC, first run rc ${CHECK_RC1:-none}, driver killed: $DRIVER_KILLED); jhan decides" CHECK-DRIVER-FAILED 5;;
  esac
elif [ -s "$RES/configs-used.txt" ]; then
  CONFIGS=$(cat "$RES/configs-used.txt"); status "CHECK=0: reusing the config file of the earlier check: $CONFIGS"   # review K6
fi
echo "$CONFIGS" >"$RES/configs-used.txt"; cp "$CONFIGS" "$RES/configs-used.json"
if [ "$CHECK_ONLY" = 1 ]; then
  status "CHECK_ONLY=1: check cell done; the passes will use $(basename "$CONFIGS"); no pass in this run (plan section 2: the six passes run in the Sunday window)"
  restore_and_release
  echo "check-only run: configs $(basename "$CONFIGS"); problems:${problems:- none}" >"$RES/outcome-check.txt"
  if [ -z "$problems" ]; then status "check-only run done"; touch "$RES/.done-check"; else status "check-only run done with problems:$problems"; touch "$RES/.done-with-failures"; fi
  exit 0
fi

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
  if ! switch_to "$arm"; then stop_reason="switch to $arm before $tag failed: ${VERIFY_FAIL:-package or restart step} (plan 2a: stop safely)"; fails=$((fails+1)); break; fi
  run_pass "$tag" "$CONFIGS" "$DRIVER_TIMEOUT"; rc=$?
  [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during $tag: operator stop"; fails=$((fails+1)); break; fi
  if [ $rc -eq 9 ]; then stop_reason="CI lease became busy during $tag (driver rc 9; plan 2a: stop safely)"; incomplete="$incomplete $tag"; fails=$((fails+1)); break; fi
  if [ "$LAST_COMPLETED" -eq 0 ]; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi
  [ $rc -eq 0 ] && continue
  fails=$((fails+1))
  if [ $rc -eq 124 ]; then status "$tag: the driver ran past its timeout (rc 124); no repeat, completed configs stay in perf.json raw records (D6)"; incomplete="$incomplete $tag"; continue; fi
  if [ $(( $(ts "$DRIVER_END_BY") - $(now_s) )) -lt "$need" ]; then stop_reason="no time for a repeat of $tag before DRIVER_END_BY (review C23)"; incomplete="$incomplete $tag"; break; fi
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken (review C21)"; incomplete="$incomplete $tag"; break; fi
  # plan 2a: restart the engines and repeat the pass once, unless every failed config is a known systematic failure (failed twice before)
  systematic=1
  if [ -z "$LAST_FAILED_CONFIGS" ]; then systematic=0; else for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$known_failed" || systematic=0; done; fi
  if [ $systematic = 1 ]; then status "$tag: the failed configs ($LAST_FAILED_CONFIGS) are known systematic failures; not repeating"; incomplete="$incomplete $tag"; continue; fi
  status "$tag: repeating the pass once after an engine restart (plan 2a)"
  rm -rf "$RES/$tag-failed1"; mv "$RES/$tag" "$RES/$tag-failed1"
  first_failed=$LAST_FAILED_CONFIGS
  restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the repeat failed"
  run_pass "$tag" "$CONFIGS" "$DRIVER_TIMEOUT"; rc=$?
  [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during the repeat of $tag: operator stop"; break; fi
  if [ $rc -eq 9 ]; then stop_reason="CI lease became busy during the repeat of $tag (driver rc 9; plan 2a: stop safely)"; incomplete="$incomplete $tag"; break; fi
  if [ "$LAST_COMPLETED" -eq 0 ]; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi
  if [ $rc -eq 0 ]; then say "$tag: repeat ok"; continue; fi
  if [ $rc -eq 8 ]; then stop_reason="engines without USE_HW_ATTN=0 after provisioning in both runs of $tag (driver rc 8; plan 2a: stop safely)"; incomplete="$incomplete $tag"; break; fi
  status "$tag: failed twice (rc $rc); continuing with the next pass (gap reported)"; incomplete="$incomplete $tag"
  for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$first_failed" && known_failed="$known_failed $c"; done   # systematic = failed in both runs (review C11/C12)
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken (review C21)"; break; fi
done
[ -n "$stop_reason" ] && status "passes stopped: $stop_reason"

# ---- restore: config.env cleared first, then the restore-target package, production up, Bill's marker, the flock
restore_and_release
echo "incomplete passes:${incomplete:- none}; stop reason: ${stop_reason:-none}; problems:${problems:- none}; known systematic failures:${known_failed:- none}" >"$RES/outcome.txt"
# ---- analysis and report (plan sections 7 and 9); their failure does not change the campaign outcome
python3 "$H/analyze.py" "$RES" >"$RES/analyze.log" 2>&1; arc=$?
if [ $arc -eq 0 ]; then say "analyze.py ok: $RES/summary.txt"; else say "WARNING analyze.py rc=$arc (see $RES/analyze.log)"; fi
python3 "$H/gen_report.py" "$RES" "$REPORT" >"$RES/gen_report.log" 2>&1; grc=$?
if [ $grc -eq 0 ]; then say "gen_report.py ok: $REPORT (the cairosvg render check and the artifact publish are the agent's steps)"; else say "WARNING gen_report.py rc=$grc (see $RES/gen_report.log)"; fi
if [ $fails -eq 0 ] && [ -z "$problems" ] && [ -z "$stop_reason" ]; then status "campaign done"; touch "$RES/.done"
else status "campaign done with $fails pass failure(s); incomplete:${incomplete:- none}; stop: ${stop_reason:-none}; problems:${problems:- none}"; touch "$RES/.done-with-failures"; fi
