#!/usr/bin/env bash
# q4b-fpga campaign 2026-09-21: prefill (TTFT) and decode of qwen3-4b tp2 against prompt length with attention on the
# FPGA against attention on the CPU, at the nightly's load of 2 users per engine, on the WHOLE of delphi-3bda with the
# nightly's own client (systems_test scripts/perf.py through st_ci_perf.py) against rinzler engines provisioned by
# platformd 0.11 (explicit named engines default-0..3, test proxy "default" on port 80) in the nightly layout.
# Forked 2026-09-21 from exec/q4b-swattn-20260919/campaign.sh (its rules, traps and restore path are kept; see .orig/).
# The measurement closes the gap named in CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html section 6 (no FPGA-attention
# TTFT of qwen3-4b above prompt 1024 existed).
#
# Arms = a deb x an attention mode (USE_HW_ATTN through /opt/positron/user/config.env, read at engine start):
#   base      nightly deb 2026.09.18-3faba6d0 (no AMX code)          + USE_HW_ATTN=0   (CPU attention, AVX)
#   canon     canonical-AMX deb 2026.09.18-0594dc54-jhan-ci-canon    + USE_HW_ATTN=0   (CPU attention, AMX)
#   vnnik     PR 4424 deb 2026.09.18-29a8a547-jhan-ci-mimic-target   + USE_HW_ATTN=0   (CPU attention, AMX + VNNI K)
#   fpgabase  nightly deb                                            + USE_HW_ATTN unset (FPGA attention, the nightly as shipped)
#   fpgacanon canonical-AMX deb                                      + USE_HW_ATTN unset (FPGA attention, AMX build)
#   fpgavnnik PR 4424 deb                                            + USE_HW_ATTN unset (FPGA attention, VNNI-K build)
# A pass = the 9 cells of configs-full.json (prompt 1024 .. 8192, 8 users = 2 per engine, 1536 generated tokens).
# A cold cell = one driver run with a single cell (cold-p<len>.json): the harness re-provisions the engines at the
# start of every driver run, so the first cell of a run always meets an empty prefix cache; cold cells at 4096 and
# 8192 give the cold TTFT that a full pass only has at 1024 (the later cells of a pass reuse the same ShareGPT seeds).
# Pass tags: <arm>-pass<k> (k counts that arm's passes) and <arm>-cold-p<len>.
# Verification per arm: dut.sh verify-env (VERIFY_HWATTN=set for CPU arms: every engine pid carries USE_HW_ATTN=0 once;
# unset for FPGA arms: no pid carries it) after every engine start, and the driver's own check after every provisioning
# (CI_MIMIC_REQUIRE_HWATTN0=1 or CI_MIMIC_REQUIRE_HWATTN_UNSET=1, rc 8 on failure; one engine restart, then a safe stop).
# No check cell (CHECK=0): the 8192 cell was validated 2026-09-19/20 with the canon deb (check-8u-p8192, rc 0).
#
# End state (HANDOFF=up): config.env 0 bytes, the restore-target deb (the one installed at preflight) reinstalled,
# production engines up (platformd's current engine config), Bill's marker released, flock released.
#
# TO STOP EARLY: kill -TERM <pid of this script> (the pid launch.sh printed; NOT -9). That stops the driver and runs
# the restore + release path (hwattn-clear first). Do NOT pkill st_ci_perf.py alone.
# RECOVERY if this script died without its trap (SIGKILL, OOM, host reboot): on delphi-3bda
#   kill $(awk '/^held pid/{print $3}' ~/workspace/intel-AMX/exec/results/q4b-fpga-20260921/.lock.out); flock -n /var/tmp/jhan/3bda-campaign.lock true && echo flock free
#   bash ~/workspace/intel-AMX/exec/q4b-fpga-20260921/dut.sh hwattn-clear          (config.env must print 0 bytes)
#   cat ~/workspace/intel-AMX/exec/results/q4b-fpga-20260921/base-identity.txt   (line "restore VERSION SHA FILE")
#   bash .../dut.sh ensure-base VERSION SHA FILE
#   IDLE_MIN=5 bash .../dut.sh serving-down && bash .../dut.sh serving-up
#   bash ~/workspace/intel-AMX/exec/bill-share.sh release; stat -c %s /opt/positron/user/config.env   (must print 0)
# RESUME: PASS_TAGS="fpgacanon-pass2 canon-pass2 ..." launch.sh reruns only those tags (a tag whose perf.json exists is
# skipped unless RESUME_OVERWRITE=1).
#
# Runs on the CLIENT host (claude-agentsrv), detached (launch.sh). DUT steps go over ssh (dut.sh).
# Env knobs: NOT_BEFORE, DEADLINE_START, PASS_DEADLINE, DRIVER_END_BY, DRIVER_TIMEOUT (s per pass, default 5400), COLD_TIMEOUT
#            (s per cold cell, default 1500), PASSES (space list of arms and cold tags; default below) or PASS_TAGS,
#            HANDOFF (up|down), NO_WAIT=1 (skip the lease wait), EXPECTED_BASE, EXPECTED_BASE_SHA, IDLE_MIN_SWITCH (default 1),
#            AMX_PROBE (1|0, informational: under FPGA attention the AMX kernel runs on the CPU share only).
# Traps carried over: never ${VAR:+x} with a 0/1 flag; the remote flock holder's pid must be killed explicitly and the
# kill verified; never edit st_ci_perf.py or this file while a pass runs; apt never restarts engines; pgrep -f patterns
# anchored so a checker does not match itself; `rc=$?` after `if cmd` reads the if-statement's status, capture rc first;
# config.env is read at engine start only (write or clear, then serving-down, then start).
set -u
NAME=q4b-fpga-20260921
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
DEADLINE_START=${DEADLINE_START:-2026-09-22T00:30:00Z}   # tonight's window: the campaign (lease, flock, marker, first pass) must START by this
PASS_DEADLINE=${PASS_DEADLINE:-2026-09-22T01:20:00Z}     # no further full pass starts after this (cold cells may start until DRIVER_END_BY minus their need)
DRIVER_END_BY=${DRIVER_END_BY:-2026-09-22T02:15:00Z}     # hard: the restore needs up to 16 min; ci-runner-stop 02:45Z, nightly lease ~03:38Z
NO_WAIT=${NO_WAIT:-0}; AMX_PROBE=${AMX_PROBE:-1}; HANDOFF=${HANDOFF:-up}
DRIVER_TIMEOUT=${DRIVER_TIMEOUT:-5400}; COLD_TIMEOUT=${COLD_TIMEOUT:-1500}
PASSES=${PASSES:-"fpgabase fpgacanon canon fpgacanon-cold-p8192 fpgacanon-cold-p4096 fpgabase-cold-p8192 fpgabase-cold-p4096"}
PASS_TAGS=${PASS_TAGS:-}
RESUME_OVERWRITE=${RESUME_OVERWRITE:-0}
IDLE_MIN_SWITCH=${IDLE_MIN_SWITCH:-1}
CONFIGS=$H/configs-full.json
mkdir -p "$RES"
# the check-only run and the Sunday run share this directory: keep the previous run's end state under prev-<time>-<name> (review 2026-09-19)
for f in .done .done-with-failures .done-aborted outcome.txt preflight.txt .status; do
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

# ---- arms: deb and attention mode
arm_deb() { case $1 in base|fpgabase) echo base;; canon|fpgacanon) echo canon;; vnnik|fpgavnnik) echo vnnik;; *) echo unknown;; esac; }
arm_attn() { case $1 in fpga*) echo fpga;; base|canon|vnnik) echo cpu;; *) echo unknown;; esac; }
CUR_ATTN=; CUR_ARM=
# ---- package switch + attention mode + restart; $1 = arm
switch_to() {
  local arm=$1 rc deb attn
  deb=$(arm_deb "$arm"); attn=$(arm_attn "$arm")
  [ "$deb" != unknown ] && [ "$attn" != unknown ] || { say "switch_to: unknown arm $arm"; return 2; }
  case $deb in
    base)  dut_t 900 ensure-base "$BASE_VERSION" "$BASE_SHA"; rc=$? ;;
    canon) dut_t 900 ensure-canon; rc=$? ;;
    vnnik) dut_t 900 ensure-vnnik; rc=$? ;;
  esac
  [ $rc -eq 0 ] || { say "switch_to $arm: package step rc=$rc"; return 1; }
  # attention mode through config.env (read at engine start): CPU arms write USE_HW_ATTN=0, FPGA arms clear the file.
  # HWATTN_SET is raised before a write so the restore clears a half-written file too.
  if [ "$attn" = cpu ]; then HWATTN_SET=1; dut_retry_ssh 120 hwattn-off || { say "switch_to $arm: hwattn-off failed"; return 1; }
  else dut_retry_ssh 120 hwattn-clear || { say "switch_to $arm: hwattn-clear failed"; return 1; }; HWATTN_SET=0; fi
  CUR_ATTN=$attn
  sleep 20  # let platformd notice the package change before anything else
  restart_engines "$IDLE_MIN_SWITCH" || { say "switch_to $arm: engine restart failed"; return 1; }
  verify_hwattn || { say "switch_to $arm: engine environment wrong for attention mode $attn"; return 1; }
  CUR_ARM=$arm
  return 0
}
HWATTN_BROKEN=0; VERIFY_FAIL=""
verify_hwattn() {   # plan 2a: every engine environment must match the arm's attention mode after it starts; one engine restart if not; still failing -> the caller stops safely
  local rc try mode
  case $CUR_ATTN in cpu) mode=set;; fpga) mode=unset;; *) VERIFY_FAIL="verify_hwattn: CUR_ATTN '$CUR_ATTN' not set"; return 1;; esac
  for try in 1 2; do
    DUT_ENV="VERIFY_HWATTN=$mode" dut_retry_ssh 300 verify-env; rc=$?   # ssh-level failures retried; dut.sh's own rc 1/2 is final
    case $rc in
      0) VERIFY_FAIL=""; return 0;;
      1) VERIFY_FAIL="an engine environment does not match attention mode $CUR_ATTN (verify-env rc 1, mode $mode)";;
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
  status "$tag: starting perf phase ($(dut_t 120 installed); attention $CUR_ATTN); configs $(basename "$cfg"); driver timeout $tmo s"
  t0=$(now_s); DRIVER_KILLED=0
  ( cd "$ST" && env PYTHONPATH="$H/talos_stub:$ST" \
      OPENAI_HOST=http://delphi-3bda.positron.internal/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
      PLATFORM_TYPE=granite_rapids_72_rinzler SYSTEM_CI_SPECULATION=0 SSH_USER=jhan SSH_PASS= \
      HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
      CI_MIMIC_ARM=$tag CI_MIMIC_OUT=$dir/perf.json TALOS_STUB_OUT=$dir/talos.json CI_MIMIC_MODELS="" \
      CI_MIMIC_CONFIGS_JSON=$cfg CI_MIMIC_INSTALLED_SHA=$sha CI_MIMIC_AMX_PROBE=$AMX_PROBE \
      CI_MIMIC_REQUIRE_HWATTN0=$([ "$CUR_ATTN" = cpu ] && echo 1 || echo 0) CI_MIMIC_REQUIRE_HWATTN_UNSET=$([ "$CUR_ATTN" = fpga ] && echo 1 || echo 0) \
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
status "campaign start (PASSES=$PASSES PASS_TAGS=${PASS_TAGS:-none} NOT_BEFORE=${NOT_BEFORE:-none} DEADLINE_START=$DEADLINE_START PASS_DEADLINE=$PASS_DEADLINE DRIVER_END_BY=$DRIVER_END_BY HANDOFF=$HANDOFF EXPECTED_BASE=$EXPECTED_BASE DRIVER_TIMEOUT=$DRIVER_TIMEOUT COLD_TIMEOUT=$COLD_TIMEOUT)"
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
# ---- configs: the 9-cell grid validated 2026-09-19/20 (check-8u-p8192 rc 0 on the canon deb); no check cell here
echo "$CONFIGS" >"$RES/configs-used.txt"; cp "$CONFIGS" "$RES/configs-used.json"

# ---- the passes: PASSES = arms (a full 9-cell pass each; tag <arm>-pass<k>, k = that arm's count) and cold tags
# (<arm>-cold-p<len>: one driver run with the single cell cold-p<len>.json); or PASS_TAGS for a resume
declare -A ARMCOUNT
if [ -n "$PASS_TAGS" ]; then TAGS=$PASS_TAGS; else
  TAGS=""
  for item in $PASSES; do
    case $item in
      *-cold*-p*) TAGS="$TAGS $item";;
      *) ARMCOUNT[$item]=$(( ${ARMCOUNT[$item]:-0} + 1 )); TAGS="$TAGS $item-pass${ARMCOUNT[$item]}";;
    esac
  done
fi
fails=0; incomplete=""; known_failed=""; stop_reason=""; PASS_S=0; COLD_S=0; first=1; zero_runs=0; need=3000
for tag in $TAGS; do
  arm=${tag%%-*}
  [ "$(arm_deb "$arm")" != unknown ] || { stop_reason="bad pass tag '$tag'"; break; }
  case $tag in
    *-cold*-p*) cold=1; plen=${tag##*-p}; cfg=$H/cold-p$plen.json; tmo=$COLD_TIMEOUT; [ -s "$cfg" ] || { stop_reason="no config for cold tag '$tag' ($cfg)"; break; };;   # <arm>-cold-p<len> or <arm>-cold2-p<len> (a second cold run of the same cell)
    *) cold=0; cfg=$CONFIGS; tmo=$DRIVER_TIMEOUT;;
  esac
  if [ -e "$RES/$tag/perf.json" ] && [ "$RESUME_OVERWRITE" != 1 ]; then status "$tag: results already exist; skipping (RESUME_OVERWRITE=1 to redo)"; continue; fi
  if [ $first = 1 ] && past "$DEADLINE_START"; then stop_reason="past DEADLINE_START before the first pass ($tag)"; break; fi
  if [ $cold = 0 ] && past "$PASS_DEADLINE"; then stop_reason="past PASS_DEADLINE before $tag"; break; fi
  ls_state=$(lease_state)
  case $ls_state in
    free) ;;
    busy) stop_reason="CI lease busy before $tag; stopping safely (plan 2a)"; break;;
    *) stop_reason="DUT did not answer the lease check 3 times before $tag; stopping safely"; break;;
  esac
  if [ $cold = 1 ]; then need=$(( COLD_S + 600 )); [ "$need" -lt 1200 ] && need=1200   # a cold cell: measured cold run + 10 min, at least 20 min
  else need=$(( PASS_S + 600 )); [ "$need" -lt 3000 ] && need=3000; fi            # a pass must be able to finish before DRIVER_END_BY (measured pass + 10 min, at least 50 min)
  if [ $(( $(ts "$DRIVER_END_BY") - $(now_s) )) -lt "$need" ]; then stop_reason="not enough time before DRIVER_END_BY for $tag (need about $((need/60)) min)"; break; fi
  first=0
  if [ "$arm" != "$CUR_ARM" ]; then
    if ! switch_to "$arm"; then stop_reason="switch to $arm before $tag failed: ${VERIFY_FAIL:-package or restart step} (plan 2a: stop safely)"; fails=$((fails+1)); break; fi
  else
    say "$tag: arm $arm already in place (deb and attention mode unchanged); the harness re-provisions the engines at the start of the run"
  fi
  run_pass "$tag" "$cfg" "$tmo"; rc=$?
  if [ $cold = 1 ]; then [ "$LAST_RUN_S" -gt "$COLD_S" ] && COLD_S=$LAST_RUN_S; else [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S; fi
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during $tag: operator stop"; fails=$((fails+1)); break; fi
  if [ $rc -eq 9 ]; then stop_reason="CI lease became busy during $tag (driver rc 9; plan 2a: stop safely)"; incomplete="$incomplete $tag"; fails=$((fails+1)); break; fi
  if [ "$LAST_COMPLETED" -eq 0 ]; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi
  [ $rc -eq 0 ] && continue
  fails=$((fails+1))
  if [ $rc -eq 124 ]; then status "$tag: the driver ran past its timeout (rc 124); no repeat, completed configs stay in perf.json raw records (D6)"; incomplete="$incomplete $tag"; continue; fi
  if [ $(( $(ts "$DRIVER_END_BY") - $(now_s) )) -lt "$need" ]; then stop_reason="no time for a repeat of $tag before DRIVER_END_BY (review C23)"; incomplete="$incomplete $tag"; break; fi
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken (review C21)"; incomplete="$incomplete $tag"; break; fi
  # plan 2a: restart the engines and repeat the run once, unless every failed config is a known systematic failure (failed twice before)
  systematic=1
  if [ -z "$LAST_FAILED_CONFIGS" ]; then systematic=0; else for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$known_failed" || systematic=0; done; fi
  if [ $systematic = 1 ]; then status "$tag: the failed configs ($LAST_FAILED_CONFIGS) are known systematic failures; not repeating"; incomplete="$incomplete $tag"; continue; fi
  status "$tag: repeating the run once after an engine restart (plan 2a)"
  rm -rf "$RES/$tag-failed1"; mv "$RES/$tag" "$RES/$tag-failed1"
  first_failed=$LAST_FAILED_CONFIGS
  restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the repeat failed"
  run_pass "$tag" "$cfg" "$tmo"; rc=$?
  if [ $cold = 1 ]; then [ "$LAST_RUN_S" -gt "$COLD_S" ] && COLD_S=$LAST_RUN_S; else [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S; fi
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during the repeat of $tag: operator stop"; break; fi
  if [ $rc -eq 9 ]; then stop_reason="CI lease became busy during the repeat of $tag (driver rc 9; plan 2a: stop safely)"; incomplete="$incomplete $tag"; break; fi
  if [ "$LAST_COMPLETED" -eq 0 ]; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi
  if [ $rc -eq 0 ]; then say "$tag: repeat ok"; continue; fi
  if [ $rc -eq 8 ]; then stop_reason="engine environment wrong for the attention mode after provisioning in both runs of $tag (driver rc 8; plan 2a: stop safely)"; incomplete="$incomplete $tag"; break; fi
  status "$tag: failed twice (rc $rc); continuing with the next pass (gap reported)"; incomplete="$incomplete $tag"
  for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$first_failed" && known_failed="$known_failed $c"; done   # systematic = failed in both runs (review C11/C12)
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken (review C21)"; break; fi
done
[ -n "$stop_reason" ] && status "passes stopped: $stop_reason"

# ---- restore: config.env cleared first, then the restore-target package, production up, Bill's marker, the flock
restore_and_release
echo "incomplete passes:${incomplete:- none}; stop reason: ${stop_reason:-none}; problems:${problems:- none}; known systematic failures:${known_failed:- none}" >"$RES/outcome.txt"
# ---- analysis: exec/prefill-amx-vs-fpga-20260921/ (the page generator) reads the perf.json files after the run; nothing here
if [ $fails -eq 0 ] && [ -z "$problems" ] && [ -z "$stop_reason" ]; then status "campaign done"; touch "$RES/.done"
else status "campaign done with $fails pass failure(s); incomplete:${incomplete:- none}; stop: ${stop_reason:-none}; problems:${problems:- none}"; touch "$RES/.done-with-failures"; fi
