#!/usr/bin/env bash
# Campaign W of PR-4 (pr4ci-20261012): the nightly System CI perf phase, run BY HAND on the WHOLE of delphi-3bda after
# the 2026-10-13 nightly ends and after the PR-4 chain's whole-machine session, with the nightly's own client
# (systems_test scripts/perf.py through st_ci_perf.py, harness at origin/main 14f0ce4) against rinzler engines
# provisioned by platformd 0.11 in the nightly layout, for two packages ("binaries" in the reports), both built by the
# chain's step deb with build-deb.sh (local branches jhan-pr4ci-base / jhan-pr4ci-target; both versions carry "jhan"):
#   base    the deb of main at 72308ec90c, /var/tmp/jhan/pr4ci-20261012/base.deb, copied to nightly.deb (the file name
#           dut.sh expects for the base arm); version 2026.10.<build day>-72308ec9-jhan-pr4ci-base = EXPECTED_BASE
#   target  the deb of PR-4's head, /var/tmp/jhan/pr4ci-20261012/target.deb (deb preset TRON_AMX_DISPATCH ON +
#           TRON_K_VNNI ON from the branch itself); version 2026.10.<build day>-<8 chars>-jhan-pr4ci-target
# Forked 2026-10-12 from exec/pr4424ci-20261009/campaign.sh (itself from exec/q4b-fpga-20260921; rules, traps and the
# restore path kept). The fork's changes (PR4-handoff.md section 5.3, "Campaign W"):
#   * EXPECTED_BASE and EXPECTED_BASE_SHA have NO default: the run refuses to start when either is empty;
#   * two gates: launch.sh needs the chain's all.done = ok; this script, after the hand-off marker wait, needs the
#     chain's chain.done to start with ok or to be the known host-suite exception (see "chain end verdict" below);
#   * marker ownership (codex point 1): W_TOOK_MARKER (1 after our own `bill take`) gates the `bill release`, and
#     W_TOOK_MACHINE (1 from right before the first ensure_state) gates every restore step, so a stop while W still
#     waits (lease, hand-off marker, peers, flock) touches neither the marker nor the DUT;
#   * the takeover path (codex point 2): the restore re-tests the CI lease before EACH mutation (hwattn-clear,
#     ensure-base, serving-down, serving-up); a busy reading defers the rest of the restore and the marker release
#     (restore-deferred.txt, status "TAKEOVER: restore deferred", problem RESTORE-DEFERRED); the flock is still released;
#   * the recovered-pass count (codex point 3): a pass whose first driver run failed and whose repeat succeeded is
#     counted as recovered (outcome.txt field "recovered passes:"), not as a failure; the first attempt stays in
#     <tag>-failed1.
#
# SCOPE of this fork (jhan, 2026-10-12): one arm pass = a FULL pass over THREE of the nightly's 14 perf configs
# (FULL_CONFIGS = subset3.json, the three entries of nightly14.json verbatim: llama-3.1-8b-instruct-good-tp2 at 8 users
# prompt 1024 and at 32 users prompt 4096, ingested-gpt-oss-120b-tp4 at 8 users prompt 1024) with USE_HW_ATTN untouched
# (config.env 0 bytes = the nightly as shipped: FPGA attention), tag <arm>-pass<k>; NO sw8k cell (SW8K=0, the default:
# the <arm>-sw8k-pass<k> tags are left out of TAGS; SW8K=1 restores the 2026-10-09 behaviour, the sw8k.json cell with
# software attention after every full pass). Pass order (ABBA, PASSES): base target target base -> base-pass1
# target-pass1 target-pass2 base-pass2. The 2026-10-09 full-suite run took 106 to 110 min per full pass; a 3-config pass
# is shorter (Insufficient data until measured), so the need rule's floor is the knob NEED_FLOOR_S (default 6600 s = 110
# min, the 2026-10-09 value; the launch passes 1800). FULL_CONFIGS="" (set, empty) selects the harness's own 14-entry list
# (CI_MIMIC_CONFIGS_JSON="" = scripts.perf.configs); unset = subset3.json; a path = that file.
# Attention mode changes are made LAZILY at the next tag that needs another mode: after a sw8k cell config.env is
# cleared again at the next transition (the switch to the next arm, the same arm's next full pass, or the restore),
# each time with an engine restart and a verify-env check. Every pass boundary therefore costs one restart, not two.
# Verification per state change: dut.sh verify-env (VERIFY_HWATTN=set after hwattn-off: every engine pid carries
# USE_HW_ATTN=0 once; unset after hwattn-clear: no pid carries it) after every engine start, and the driver's own
# check after every provisioning (CI_MIMIC_REQUIRE_HWATTN0=1 or CI_MIMIC_REQUIRE_HWATTN_UNSET=1, rc 8 on failure; one
# engine restart, then a safe stop). The driver also records a memory snapshot (dut.sh memsnap) after every
# provisioning and after every benchmark (the PR's "no meaningful memory increase" claim); campaign.sh does nothing for it.
#
# Restore target: the deb installed at preflight (tonight's nightly installs a NEWER deb than the base arm); it is
# saved as restore.deb and reinstalled at the end (restore-target rule of q4b-fpga). The base ARM stays nightly.deb.
# End state (HANDOFF=up): config.env 0 bytes, restore.deb reinstalled, production engines up (platformd's current engine
# config), Bill's marker released, flock released. summarize.py then writes $RES/summary.md and summary.json.
#
# TO STOP EARLY: kill -TERM <pid of this script> (the pid launch.sh printed; NOT -9). That stops the driver and runs
# the restore + release path (hwattn-clear first). Do NOT pkill st_ci_perf.py alone. Never stop W, and never let its
# DEADLINE_START pass, while the chain holds the whole machine (between the chain's marker take and its exit handler):
# the ownership flags make such a stop harmless to the marker, and the rule stays as a second layer.
# RECOVERY if this script died without its trap (SIGKILL, OOM, host reboot), or after "TAKEOVER: restore deferred"
# (then only after the CI lease clears, about 13:25 UTC; light work only until then; see restore-deferred.txt): on delphi-3bda
#   kill $(awk '/^held pid/{print $3}' ~/workspace/intel-AMX/exec/results/pr4ci-20261012/.lock.out); flock -n /var/tmp/jhan/3bda-campaign.lock true && echo flock free
#   bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh hwattn-clear          (config.env must print 0 bytes)
#   cat ~/workspace/intel-AMX/exec/results/pr4ci-20261012/base-identity.txt   (line "restore VERSION SHA FILE")
#   bash .../dut.sh ensure-base VERSION SHA FILE
#   IDLE_MIN=5 bash .../dut.sh serving-down && bash .../dut.sh serving-up
#   bash ~/workspace/intel-AMX/exec/bill-share.sh release (only when this run took the marker; restore-deferred.txt says so); stat -c %s /opt/positron/user/config.env   (must print 0)
# RESUME: PASS_TAGS="target-pass2 target-sw8k-pass2 base-pass2 base-sw8k-pass2" bash launch.sh reruns only those tags
# (a tag whose perf.json exists is skipped unless RESUME_OVERWRITE=1); the preflight needs the nightly's deb installed.
#
# Wait order: NOT_BEFORE, CI lease free, the hand-off marker /var/tmp/jhan/pr4424ci-precheck.running absent (the PR-4
# chain exec/pr4-20261012/chain2.sh writes it at launch and its exit handler removes it after serving is back up and
# Bill's marker is released; so W and the chain never wait for the same lease event), the chain's end verdict (gate),
# no runtron/campaign peer, campaign flock, Bill's marker; DEADLINE_START applies to every wait.
# Runs on the CLIENT host (claude-box), detached (launch.sh). DUT steps go over ssh (dut.sh).
# Env knobs: NOT_BEFORE, DEADLINE_START, PASS_DEADLINE, DRIVER_END_BY, DRIVER_TIMEOUT (s per full pass, default 9000),
#            SW8K_TIMEOUT (s per sw8k cell, default 1800), PASSES (space list of arm names in order; default below) or
#            PASS_TAGS, HANDOFF (up|down), NO_WAIT=1 (skip the lease wait), EXPECTED_BASE and EXPECTED_BASE_SHA (REQUIRED, no
#            default: the base deb's Version field and its rinzler sha256 from $OUT/manifest-base.json on delphi-3bda),
#            IDLE_MIN_SWITCH (default 1), AMX_PROBE (1|0, informational 20 s EXE.AMX_BUSY sample before the llama-8b and
#            qwen-3-4b tp2 benchmarks), FULL_CONFIGS (a configs json for the full pass; unset = $H/subset3.json, the
#            three-config scope; "" = the harness list), SW8K (0 = no sw8k tags, the default; 1 = the sw8k cell after every
#            full pass), NEED_FLOOR_S (the floor of the full-pass need rule in s, default 6600),
#            HF_OFFLINE (1 = HF_HUB_OFFLINE=1 for the driver; every tokenizer is in the local HF cache, checked 2026-10-08).
# Traps carried over: never ${VAR:+x} with a 0/1 flag; the remote flock holder's pid must be killed explicitly and the
# kill verified; never edit st_ci_perf.py, dut.sh or this file while a pass runs (NFS stale handle); apt never restarts
# engines; pgrep -f patterns anchored so a checker does not match itself; `rc=$?` after `if cmd` reads the if-statement's
# status, capture rc first; config.env is read at engine start only (write or clear, then serving-down, then start);
# platformd 0.11 restarts units stopped with systemctl, so serving down/up go through POST /api/inference/down|up.
set -u
NAME=pr4ci-20261012
H=/home/jhan/workspace/intel-AMX/exec/$NAME
RES=/home/jhan/workspace/intel-AMX/exec/results/$NAME
ST=/home/jhan/workspace/ai-runs/systems_test
PY=$ST/.venv/bin/python
DUT_ALIAS=delphi-3bda
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ServerAliveCountMax=4"
LOCK=/var/tmp/jhan/3bda-campaign.lock
HOLDER_LIFE=50400   # s; recomputed before hold_lock from DRIVER_END_BY + 2 h
EXPECTED_BASE=${EXPECTED_BASE:-}                         # REQUIRED (no default): the base ARM's deb Version field (2026.10.<build day>-72308ec9-jhan-pr4ci-base, manifest-base.json "version"); installed from the saved nightly.deb (= base.deb)
EXPECTED_BASE_SHA=${EXPECTED_BASE_SHA:-}                 # REQUIRED (no default): sha256 of its /opt/positron/bin/rinzler (manifest-base.json "rinzler_sha256")
NOT_BEFORE=${NOT_BEFORE:-2026-10-13T13:05:00Z}           # option (a): five minutes after the chain's START_NOT_BEFORE; sleep until here before the lease wait (the nightly's lease clears about 13:20 to 13:36 UTC)
DEADLINE_START=${DEADLINE_START:-2026-10-14T01:35:00Z}   # option (a): the campaign (lease, hand-off marker, flock, Bill's marker, first pass) must START by this; after the chain's END_BY 01:30, so W never aborts while the chain can still hold the whole machine
PASS_DEADLINE=${PASS_DEADLINE:-2026-10-14T01:40:00Z}     # option (a): no further FULL pass starts after this (sw8k cells may start until DRIVER_END_BY minus their need); the need rule below is the tighter bound
DRIVER_END_BY=${DRIVER_END_BY:-2026-10-14T02:05:00Z}     # hard: the restore needs up to 16 min; ci-runner-stop timer 02:45 UTC
NO_WAIT=${NO_WAIT:-0}; AMX_PROBE=${AMX_PROBE:-1}; HANDOFF=${HANDOFF:-up}; HF_OFFLINE=${HF_OFFLINE:-1}
DRIVER_TIMEOUT=${DRIVER_TIMEOUT:-9000}; SW8K_TIMEOUT=${SW8K_TIMEOUT:-1800}
PASSES=${PASSES:-"base target target base"}
PASS_TAGS=${PASS_TAGS:-}
RESUME_OVERWRITE=${RESUME_OVERWRITE:-0}
IDLE_MIN_SWITCH=${IDLE_MIN_SWITCH:-1}
FULL_CONFIGS=${FULL_CONFIGS-$H/subset3.json}   # unset = the three-config scope (subset3.json); "" (set, empty) = the harness's own scripts.perf.configs (14 entries); a file path replaces it
SW8K=${SW8K:-0}                           # 0 = no <arm>-sw8k-pass<k> tags (this fork's scope); 1 = the sw8k cell after every full pass (2026-10-09 behaviour)
NEED_FLOOR_S=${NEED_FLOOR_S:-6600}        # the floor of the full-pass need rule: a full pass starts only when max(longest measured pass + 600 s, NEED_FLOOR_S) remains before DRIVER_END_BY
CHAIN_DONE_ACCEPT=${CHAIN_DONE_ACCEPT:-}  # optional: one exact chain.done text the gate below also accepts (the executor's explicit decision, recorded in split-status.md, for a verdict that is not ok only in fields that do not concern W); empty = the two forms of the gate only
SW8K_CONFIGS=$H/sw8k.json
mkdir -p "$RES"
# a check-only run and the real run share this directory: keep the previous run's end state under prev-<time>-<name>
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
dut_retry() { local t=$1 n; shift; for n in 1 2 3; do dut_t "$t" "$@" && return 0; say "dut_retry: $1 attempt $n failed" >&2; sleep 20; done; return 1; }   # ssh hiccups; messages to stderr, callers capture stdout
# retry ONLY ssh-level failures (rc 255 could not connect, rc 124 command timeout with no output); dut.sh's own rc 1 is final
dut_retry_ssh() { local t=$1 n rc; shift; for n in 1 2 3 4 5; do dut_t "$t" "$@"; rc=$?; case $rc in 0) return 0;; 255|124) say "dut_retry_ssh: $1 attempt $n rc=$rc (ssh); retry in 60 s" >&2; sleep 60;; *) return $rc;; esac; done; return $rc; }
wait_dut() {   # wait (bounded, $1 s) until the DUT answers; 0 = answered, 1 = gave up
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
installed_sha() { local v; v=$(dut_retry 120 installed | awk '{print $2}' | tail -1); [[ $v =~ ^[0-9a-f]{64}$ ]] && echo "$v"; }   # only a real sha256, else empty
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

# ---- engine restart after a package switch or a config.env change: the running engines still map the old binary / old environment
restart_engines() {   # $1 = IDLE_MIN for the idle test (1 between passes: only our own traffic; 5 at the handoff)
  local idle=${1:-$IDLE_MIN_SWITCH} rc
  dut_env_t 1500 "IDLE_MIN=$idle" serving-down; rc=$?
  [ $rc -eq 0 ] || { say "restart_engines: serving-down rc=$rc (see log)"; return 1; }
  dut_t 900 serving-up; rc=$?
  [ $rc -eq 0 ] || { say "restart_engines: serving-up rc=$rc"; return 1; }
  return 0
}

# ---- tags: <arm>-pass<k> (full pass, FPGA attention as shipped) and <arm>-sw8k-pass<k> (the sw8k cell, software attention)
arm_of() { echo "${1%%-*}"; }
kind_of() { case $1 in *-sw8k-pass*) echo sw8k;; *-pass*) echo full;; *) echo unknown;; esac; }
attn_of_kind() { case $1 in full) echo fpga;; sw8k) echo cpu;; *) echo unknown;; esac; }
arm_known() { case $1 in base|target) return 0;; esac; return 1; }
CUR_ATTN=; CUR_ARM=
# ---- set config.env for an attention mode (no restart here); HWATTN_SET is raised before a write so the restore clears a half-written file too
set_hwattn() {   # $1 = cpu|fpga
  if [ "$1" = cpu ]; then HWATTN_SET=1; dut_retry_ssh 120 hwattn-off || { say "set_hwattn: hwattn-off failed"; return 1; }
  else dut_retry_ssh 120 hwattn-clear || { say "set_hwattn: hwattn-clear failed"; return 1; }; HWATTN_SET=0; fi
  CUR_ATTN=$1
  return 0
}
# ---- bring the DUT to (arm, attention mode): package step only when the arm changes; config.env + restart + verify-env when anything changes
ensure_state() {
  local arm=$1 attn=$2 rc
  arm_known "$arm" || { say "ensure_state: unknown arm $arm"; return 2; }
  if [ "$arm" = "$CUR_ARM" ] && [ "$attn" = "$CUR_ATTN" ]; then say "arm $arm with $attn attention already in place; the harness re-provisions the engines at the start of the run"; return 0; fi
  if [ "$arm" != "$CUR_ARM" ]; then
    case $arm in
      base)   dut_t 900 ensure-base "$BASE_VERSION" "$BASE_SHA"; rc=$? ;;
      target) dut_t 900 ensure-target; rc=$? ;;
    esac
    [ $rc -eq 0 ] || { say "ensure_state $arm: package step rc=$rc"; return 1; }
    CUR_ARM=$arm
    sleep 20  # let platformd notice the package change before anything else
  fi
  set_hwattn "$attn" || return 1
  restart_engines "$IDLE_MIN_SWITCH" || { say "ensure_state $arm/$attn: engine restart failed"; return 1; }
  verify_hwattn || { say "ensure_state $arm/$attn: engine environment wrong for attention mode $attn"; return 1; }
  return 0
}
HWATTN_BROKEN=0; VERIFY_FAIL=""
verify_hwattn() {   # every engine environment must match the attention mode after it starts; one engine restart if not; still failing -> the caller stops safely
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
    status "verify-env: $VERIFY_FAIL; restarting the engines once and re-checking"
    restart_engines "$IDLE_MIN_SWITCH" || { say "verify_hwattn: engine restart failed"; return 1; }
  done
  [ $rc -eq 1 ] && HWATTN_BROKEN=1
  status "verify-env after a restart: $VERIFY_FAIL; the caller stops safely"; return 1
}

# ---- restore + handoff + release: runs exactly once, on the normal path AND on a signal.
# W_TOOK_MARKER (codex point 1): 1 right after our own successful `bill take`; only then does this run `bill release`.
# W_TOOK_MACHINE (codex point 1): 1 from right before the first ensure_state; only then do the restore steps run at all
# (the RESTORE_VERSION test still covers the package part; the flag covers the serving calls too).
# RESTORE_DEFERRED (codex point 2): 1 once the CI lease read busy before a restore step; from then on no dut.sh
# mutation and no `bill release`; restore-deferred.txt tells the executor what is left to do by hand after the lease clears.
BASE_VERSION=; BASE_SHA=; RESTORE_VERSION=; RESTORE_SHA=; RESTORE_FILE=nightly.deb; HWATTN_SET=0; DRIVER_PID=; RESTORED=0; problems=""
W_TOOK_MARKER=0; W_TOOK_MACHINE=0; RESTORE_DEFERRED=0
defer_restore() {   # $1 = the restore step that was about to run when the lease read busy
  RESTORE_DEFERRED=1; problems="$problems RESTORE-DEFERRED"
  local cb; cb=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" 'stat -c %s /opt/positron/user/config.env' 2>/dev/null)
  {
    echo "time: $(date -u +%FT%TZ)"
    echo "deferred before: $1 (the CI lease read busy; no dut.sh mutation and no bill-share.sh release by this run from here on)"
    echo "restore target: RESTORE_VERSION=${RESTORE_VERSION:-none} RESTORE_SHA=${RESTORE_SHA:-none} RESTORE_FILE=$RESTORE_FILE"
    echo "config.env bytes: ${cb:-unread} (14 = USE_HW_ATTN=0 still set, 0 = cleared); HWATTN_SET=$HWATTN_SET"
    echo "marker taken by this run and still taken: $W_TOOK_MARKER (1 = run bill-share.sh release by hand after the restore)"
    echo "by hand after the lease clears (about 13:25 UTC; light work only until then): dut.sh hwattn-clear when config.env is not 0 bytes; dut.sh ensure-base ${RESTORE_VERSION:-VERSION} ${RESTORE_SHA:-SHA} $RESTORE_FILE when the installed package is not the nightly's; IDLE_MIN=5 dut.sh serving-down; dut.sh serving-up; then bill-share.sh release when the marker line says 1; record each result in split-status.md"
  } >"$RES/restore-deferred.txt"
  status "TAKEOVER: restore deferred before $1 (CI lease busy); no further DUT change and no marker release by this run; see $RES/restore-deferred.txt"
}
restore_step_ok() {   # $1 = the restore step about to run. 0 = lease free, go on; 1 = deferred (busy now, or earlier)
  [ "$RESTORE_DEFERRED" = 1 ] && return 1
  local st; st=$(lease_state)
  case $st in
    free) say "lease free before $1"; return 0;;
    busy) defer_restore "$1"; return 1;;
    *) problems="$problems LEASE-UNKNOWN-BEFORE-$1"; say "WARNING: the lease check before $1 answered '$st' 3 times; going on (the DUT answered wait_dut; a busy lease would have printed busy)"; return 0;;
  esac
}
restore_and_release() {
  [ "$RESTORED" = 1 ] && return 0; RESTORED=1
  if [ "$W_TOOK_MACHINE" = 1 ]; then
    # the DUT outage that stopped the campaign may still last: wait for it (bounded 30 min), then retry ssh-level failures
    wait_dut 1800 || { problems="$problems DUT-UNREACHABLE"; status "RESTORE: DUT unreachable for 30 min; steps below will fail; see the RECOVERY sequence in the header"; }
    # config.env FIRST: production engines must never start with USE_HW_ATTN=0 (they would run software attention)
    if [ "$HWATTN_SET" = 1 ] && restore_step_ok hwattn-clear; then
      if dut_retry_ssh 120 hwattn-clear; then HWATTN_SET=0; say "hwattn-clear ok: config.env 0 bytes"
      else
        local cb; cb=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" 'stat -c %s /opt/positron/user/config.env' 2>/dev/null)
        if [ "$cb" = 0 ]; then HWATTN_SET=0; say "hwattn-clear reported a failure but config.env is 0 bytes: treated as cleared"
        else problems="$problems HWATTN-CLEAR-FAILED"; status "HWATTN-CLEAR FAILED (config.env ${cb:-unread} bytes): USE_HW_ATTN=0 may still be set; production is NOT brought up (jhan: sudo truncate -s 0 /opt/positron/user/config.env, then dut.sh serving-down, serving-up)"; fi
      fi
    fi
    if [ -n "$RESTORE_VERSION" ]; then
      local restored=0
      if restore_step_ok ensure-base; then
        if dut_retry_ssh 900 ensure-base "$RESTORE_VERSION" "$RESTORE_SHA" "$RESTORE_FILE"; then restored=1; status "restore ok: $(dut_retry 120 installed)"; else problems="$problems RESTORE-FAILED"; status "RESTORE FAILED: $(dut_retry 120 installed) (wanted $RESTORE_VERSION from $RESTORE_FILE); jhan must reinstall tron by hand"; fi
      fi
      if [ "$RESTORE_DEFERRED" = 1 ]; then :   # the serving steps and the config.env check stay with the executor (restore-deferred.txt)
      elif [ "$HANDOFF" = up ] && [ $restored = 1 ] && [ "$HWATTN_SET" = 0 ]; then
        # engines of the last pass still run the deleted binary until restarted: down, then up (skip up when down failed)
        if restore_step_ok serving-down; then
          if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then
            if restore_step_ok serving-up; then dut_retry_ssh 900 serving-up || { problems="$problems SERVING-UP-FAILED"; say "WARNING serving-up did not complete"; }; fi
          else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log); engines may still run a deleted binary"; fi
        fi
      elif [ "$HANDOFF" = up ]; then
        # never bring production up on a binary that is not the nightly's, or with USE_HW_ATTN=0 still in config.env: down only, jhan decides
        if restore_step_ok serving-down; then
          if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then status "restore failed or config.env not cleared: production engines taken DOWN (not brought up)"; else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: restore failed (or config.env not cleared) and serving-down failed"; fi
        fi
      else
        if restore_step_ok serving-down; then
          if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then status "handoff: production engines down, hugepages free"
          else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log)"; fi
        fi
      fi
      if [ "$RESTORE_DEFERRED" != 1 ]; then
        local cfgbytes n
        for n in 1 2 3; do cfgbytes=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" 'stat -c %s /opt/positron/user/config.env' 2>/dev/null); [ -n "$cfgbytes" ] && break; sleep 30; done
        if [ "$cfgbytes" = 0 ]; then say "config.env is 0 bytes (ok)"; else problems="$problems CONFIG-ENV-${cfgbytes:-unread}-BYTES"; say "WARNING: /opt/positron/user/config.env has '${cfgbytes:-unread}' bytes (must be 0)"; fi
      fi
    else
      say "no restore target recorded (aborted before preflight): nothing to restore"
    fi
  else
    say "no DUT state changed by this run (W_TOOK_MACHINE=0): nothing to restore"
  fi
  if [ "$W_TOOK_MARKER" != 1 ]; then say "marker not taken by this run, left alone"
  elif [ "$RESTORE_DEFERRED" = 1 ]; then say "Bill's marker stays taken: the restore is deferred (see $RES/restore-deferred.txt); release it by hand after the restore"
  else
    local rel_out rel_rc n
    for n in 1 2 3; do rel_out=$(bill release 2>&1); rel_rc=$?; [ "$rel_rc" -eq 0 ] && break; say "bill release attempt $n rc=$rel_rc"; sleep 30; done
    printf '%s\n' "$rel_out" | tail -1
    [ "$rel_rc" -eq 0 ] || { problems="$problems MARKER-NOT-RELEASED"; say "WARNING: bill-share release rc=$rel_rc; run bill-share.sh release by hand"; }
  fi
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
# any early exit after the marker was taken must give it back: RESTORE_VERSION empty = nothing installed yet
abort_early() { status "ABORT: $1"; RESTORE_VERSION=; restore_and_release; echo "aborted: $1" >"$RES/outcome.txt"; touch "$RES/.done-aborted"; exit "$2"; }

# ---- one driver run: $1 tag (results subdir), $2 configs json ("" = the harness list), $3 timeout s -> rc of the driver
LAST_RUN_S=0; LAST_FAILED_CONFIGS=""; LAST_COMPLETED=0; DRIVER_KILLED=0
run_pass() {
  local tag=$1 cfg=$2 tmo=$3 dir=$RES/$1 rc t0 sha cfglabel
  mkdir -p "$dir"
  local left=$(( $(ts "$DRIVER_END_BY") - $(now_s) )); [ "$tmo" -gt "$left" ] && tmo=$left
  [ "$tmo" -gt 600 ] || { status "$tag: less than 10 min left before DRIVER_END_BY; not starting"; return 3; }
  sha=$(installed_sha); [ -n "$sha" ] || say "WARNING: installed sha unreadable; the driver falls back to the snapshot's own sha line"
  if [ -n "$cfg" ]; then cfglabel=$(basename "$cfg"); else cfglabel="the harness's own perf list (scripts.perf.configs)"; fi
  status "$tag: starting perf phase ($(dut_t 120 installed); attention $CUR_ATTN); configs $cfglabel; driver timeout $tmo s"
  t0=$(now_s); DRIVER_KILLED=0
  ( cd "$ST" && env PYTHONPATH="$H/talos_stub:$ST" \
      OPENAI_HOST=http://delphi-3bda.positron.internal/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
      PLATFORM_TYPE=granite_rapids_72_rinzler SYSTEM_CI_SPECULATION=0 SSH_USER=jhan SSH_PASS= \
      HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_OFFLINE=$HF_OFFLINE TOKENIZERS_PARALLELISM=false \
      CI_MIMIC_ARM=$tag CI_MIMIC_OUT=$dir/perf.json TALOS_STUB_OUT=$dir/talos.json CI_MIMIC_MODELS="" \
      CI_MIMIC_CONFIGS_JSON="$cfg" CI_MIMIC_INSTALLED_SHA=$sha CI_MIMIC_AMX_PROBE=$AMX_PROBE \
      CI_MIMIC_REQUIRE_HWATTN0=$([ "$CUR_ATTN" = cpu ] && echo 1 || echo 0) CI_MIMIC_REQUIRE_HWATTN_UNSET=$([ "$CUR_ATTN" = fpga ] && echo 1 || echo 0) \
      CI_MIMIC_LEASE_CHECK=${LEASE_CHECK:-1} CI_MIMIC_DUT_HELPER=$H/dut.sh \
      timeout "$tmo" "$PY" "$H/st_ci_perf.py" >"$dir/driver.log" 2>&1 ) &
  DRIVER_PID=$!
  wait "$DRIVER_PID"; rc=$?; DRIVER_PID=
  LAST_RUN_S=$(( $(now_s) - t0 ))
  case $rc in 130|137|143) DRIVER_KILLED=1;; esac
  grep -E "Perf test for|CONFIG DONE|MEMSNAP|RESULT|engine count|deleted|STOP|FAILED_CONFIGS|pass stopped|Error|Traceback|configs without results" "$dir/driver.log" | tail -120 >"$dir/summary.txt"
  # the driver's last line names the cells without results, comma-separated ids without spaces (model@users-pLEN)
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

lease_state() {   # free | busy | unknown (3 attempts)
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
# ---- knob sanity: every date knob must parse (ts() prints nothing for a bad one and past() would then never fire),
# the deadlines must be ordered, and a launch far ahead of its window must carry NOT_BEFORE (no lease file exists before the nightly takes it)
for v in NOT_BEFORE DEADLINE_START PASS_DEADLINE DRIVER_END_BY; do
  [ -z "${!v}" ] && continue
  ts "${!v}" >/dev/null 2>&1 || abort_early "knob $v='${!v}' is not a date that 'date -u -d' accepts" 2
done
[ "$(ts "$DEADLINE_START")" -lt "$(ts "$PASS_DEADLINE")" ] && [ "$(ts "$PASS_DEADLINE")" -lt "$(ts "$DRIVER_END_BY")" ] || abort_early "deadline order wrong: need DEADLINE_START ($DEADLINE_START) < PASS_DEADLINE ($PASS_DEADLINE) < DRIVER_END_BY ($DRIVER_END_BY)" 2
[ -z "$NOT_BEFORE" ] || [ "$(ts "$NOT_BEFORE")" -lt "$(ts "$DEADLINE_START")" ] || abort_early "NOT_BEFORE $NOT_BEFORE is not before DEADLINE_START $DEADLINE_START" 2
past "$DRIVER_END_BY" && abort_early "DRIVER_END_BY $DRIVER_END_BY is already past" 2
[ -n "$NOT_BEFORE" ] || [ $(( $(ts "$DEADLINE_START") - $(now_s) )) -le 28800 ] || abort_early "the start is more than 8 h before DEADLINE_START and NOT_BEFORE is empty: the campaign would start now and could run into the nightly; set NOT_BEFORE" 3
[ -z "$FULL_CONFIGS" ] || [ -s "$FULL_CONFIGS" ] || abort_early "FULL_CONFIGS=$FULL_CONFIGS is not a readable file" 2
# the base arm's identity has no default in this fork: both come from the base deb's manifest ($OUT/manifest-base.json on the DUT)
[ -n "$EXPECTED_BASE" ] || abort_early "EXPECTED_BASE is empty (no default): set it to the base deb's Version field (dpkg-deb -f base.deb Version; manifest-base.json \"version\")" 2
[[ $EXPECTED_BASE_SHA =~ ^[0-9a-f]{64}$ ]] || abort_early "EXPECTED_BASE_SHA '$EXPECTED_BASE_SHA' is empty or not a sha256 (no default): set it to the base deb's rinzler sha256 (manifest-base.json \"rinzler_sha256\")" 2
[ "$SW8K" != 1 ] || [ -s "$SW8K_CONFIGS" ] || abort_early "sw8k.json missing ($SW8K_CONFIGS); run configs.py" 2
case $SW8K in 0|1) ;; *) abort_early "SW8K='$SW8K' must be 0 or 1" 2;; esac
[[ $NEED_FLOOR_S =~ ^[0-9]+$ ]] || abort_early "NEED_FLOOR_S='$NEED_FLOOR_S' must be a number of seconds" 2
status "campaign start (PASSES=$PASSES PASS_TAGS=${PASS_TAGS:-none} SW8K=$SW8K NEED_FLOOR_S=$NEED_FLOOR_S NOT_BEFORE=${NOT_BEFORE:-none} DEADLINE_START=$DEADLINE_START PASS_DEADLINE=$PASS_DEADLINE DRIVER_END_BY=$DRIVER_END_BY HANDOFF=$HANDOFF EXPECTED_BASE=$EXPECTED_BASE DRIVER_TIMEOUT=$DRIVER_TIMEOUT SW8K_TIMEOUT=$SW8K_TIMEOUT FULL_CONFIGS=${FULL_CONFIGS:-harness-list} AMX_PROBE=$AMX_PROBE HF_OFFLINE=$HF_OFFLINE)"
# ---- sleep until NOT_BEFORE. The nightly takes the lease at about 03:38 UTC; before that no lease file exists, so a
# lease-free test alone would start the campaign at once and run into the CI window.
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
# the hand-off marker: the PR-4 chain (exec/pr4-20261012/chain2.sh) writes it at launch and holds it through its
# whole-machine session (steps D, E, C, the bench); its exit handler removes it after serving is back up and Bill's marker
# is released. The file name is the 2026-10-09 campaign's, unchanged. An ssh failure counts as "wait and retry", never as "absent".
PRECHECK_MARKER=/var/tmp/jhan/pr4424ci-precheck.running
while :; do
  timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" "test -e $PRECHECK_MARKER"; mrc=$?
  case $mrc in
    1) break;;
    0) past "$DEADLINE_START" && abort_early "past DEADLINE_START while the pre-check marker $PRECHECK_MARKER is present" 3
       status "waiting: pre-check running (marker $PRECHECK_MARKER present)"; nap 120;;
    *) past "$DEADLINE_START" && abort_early "DUT did not answer the pre-check marker test until DEADLINE_START" 3
       status "waiting: DUT did not answer the pre-check marker test (rc $mrc); retry in 2 min"; nap 120;;
  esac
done
status "pre-check marker absent"
# ---- the chain's end verdict (new in the fork): W runs only after the PR-4 chain ended with ok or with the one known
# host-suite exception (t_proxy_llama31 failed for the missing t/proxy/.venv; the smoke and E fields must be ok too,
# because every failed verdict of a normal run starts with "failed host=failed"; the bench field stays open, a bench
# failure is not a stop condition for W). Read on the DUT, where the chain wrote it (claude-box's NFS attribute cache
# could serve a stale copy). A missing file (the chain was killed: its handler removes the marker and writes no verdict)
# aborts too; that abort runs after the chain's exit handler, and this run has taken nothing yet.
CHAIN_DONE=/home/jhan/workspace/intel-AMX/exec/results/pr4-20261012/chain.done
for try in 1 2 3; do   # an ssh-level failure (rc 255, 124) is retried; cat's rc 1 (no file) is final
  v=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" "cat $CHAIN_DONE 2>/dev/null"); vrc=$?
  case $vrc in 0|1) break;; *) say "chain.done read attempt $try rc=$vrc (ssh); retry in 60 s"; nap 60;; esac
done
case $v in
  ok*|"failed host=failed smoke=ok/ok/ok E=ok/ok bench="*) status "chain end verdict '$v': W may run";;
  *) if [ -n "$CHAIN_DONE_ACCEPT" ] && [ "$v" = "$CHAIN_DONE_ACCEPT" ]; then
       status "chain end verdict '$v' accepted by CHAIN_DONE_ACCEPT (jhan's decision of 2026-10-13): W may run"
     else
       abort_early "the chain's end verdict is '$v': not ok and not the known host-suite exception" 5
     fi;;
esac
# another session's campaign (runtron cells on our half) may run without holding the campaign flock: wait until no
# runtron process and no other campaign.sh of ours runs on the DUT
while :; do   # pgrep rc 1 = no process; rc 0 = a peer runs; anything else = ssh failure (never read as 'no process')
  timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" "pgrep -u jhan -f '[r]untron[. ]|[c]ampaign[.]sh' >/dev/null"; prc=$?
  case $prc in
    1) break;;
    0) past "$DEADLINE_START" && abort_early "past DEADLINE_START while waiting for another campaign's processes to end" 3
       status "waiting: another campaign (runtron or campaign.sh) is running on the DUT"; nap 120;;
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

# ---- Bill's marker: taken here (whole machine); if Bill is active, retry take every 30 min until DEADLINE_START; only jhan can decide to interrupt Bill
while :; do
  out=$(bill status 2>&1)
  case $out in
    *"marker absent"*) say "Bill's marker already absent (not taken by this run: this run will not release it)"; break;;
    *"marker present"*)
      tout=$(bill take 2>&1); trc=$?; printf '%s\n' "$tout" | tail -1
      case $trc in
        0) status "Bill's marker taken (whole machine)"; W_TOOK_MARKER=1; break;;
        2) past "$DEADLINE_START" && abort_early "Bill's marker still present at DEADLINE_START (Bill active); jhan decides" 6
           if [ "$NO_WAIT" != 1 ]; then case $(lease_state) in free) ;; busy) abort_early "CI lease became busy while waiting for Bill's marker" 3;; *) abort_early "DUT did not answer the lease check while waiting for Bill's marker" 3;; esac; fi
           status "waiting: Bill is active (marker present); retry in 30 min"; nap 1800;;
        *) abort_early "bill-share take rc=$trc (sudo or file error), not 'Bill active'" 6;;
      esac;;
    *) past "$DEADLINE_START" && abort_early "DUT did not answer the marker check until DEADLINE_START" 3
       status "waiting: DUT did not answer the marker check; retry in 2 min"; nap 120;;
  esac
done

# ---- preflight (read-only) and the identities: the RESTORE target = what is installed now (tonight's nightly); the base ARM = EXPECTED_BASE
PF=$RES/preflight.txt
dut_retry 300 preflight >"$PF" 2>&1 || say "WARNING: preflight did not complete cleanly (see $PF)"
read -r RESTORE_VERSION RESTORE_SHA < <(dut_retry 120 installed | tail -1)
say "installed at preflight = $RESTORE_VERSION rinzler sha $RESTORE_SHA (the RESTORE target); base ARM = $EXPECTED_BASE sha $EXPECTED_BASE_SHA"
case $RESTORE_VERSION in 2026.*) ;; *) abort_early "unexpected installed tron version '$RESTORE_VERSION'" 4;; esac
case $RESTORE_VERSION in *jhan*) abort_early "installed package '$RESTORE_VERSION' is one of ours, not the nightly's; restore by hand first" 4;; esac
[[ $RESTORE_SHA =~ ^[0-9a-f]{64}$ ]] || abort_early "installed rinzler sha unreadable" 4
grep -q "installed rinzler IS the target build's (must be no at preflight): no" "$PF" || abort_early "the installed rinzler is the target build's binary (or the line is missing; see $PF); restore by hand first" 4
BASE_VERSION=$EXPECTED_BASE; BASE_SHA=$EXPECTED_BASE_SHA
grep -q "target build: status=ok" "$PF" || abort_early "target build not ok (see $PF; run build-target.sh first)" 5
grep -q "config.env bytes (must be 0): 0" "$PF" || abort_early "config.env is not 0 bytes (see $PF)" 5
grep -q "^== bill marker: absent" "$PF" || abort_early "Bill's marker is present at preflight (see $PF)" 6
if grep -q "num-expert-replicas count: [1-9]" "$PF"; then say "WARNING: the rinzler unit file carries a hand edit (--num-expert-replicas); the nightly's deb file has none"; fi
if [ "$RESTORE_VERSION" = "$BASE_VERSION" ]; then RESTORE_FILE=nightly.deb; say "restore target equals the base arm (tonight's nightly did not install a newer deb): restored from nightly.deb"
else RESTORE_FILE=restore.deb; say "restore target $RESTORE_VERSION differs from the base arm $BASE_VERSION: saved as restore.deb and reinstalled at the end (restore-target rule)"; fi
{ echo "base $BASE_VERSION $BASE_SHA nightly.deb"; echo "restore $RESTORE_VERSION $RESTORE_SHA $RESTORE_FILE"; } >"$RES/base-identity.txt"
dut_retry 300 save-base-deb "$BASE_VERSION" nightly.deb || abort_early "the base arm's deb $BASE_VERSION is not saved as nightly.deb and could not be downloaded" 5
if [ "$RESTORE_FILE" = restore.deb ]; then dut_retry 300 save-base-deb "$RESTORE_VERSION" restore.deb || abort_early "could not save a local copy of the installed deb $RESTORE_VERSION (the restore target)" 5; fi

# ---- the waits above can last until DEADLINE_START: re-test the CI lease right before the first state change
if [ "$NO_WAIT" != 1 ]; then
  case $(lease_state) in free) ;; busy) abort_early "CI lease busy after the waits, before the first package switch" 3;; *) abort_early "DUT did not answer the lease check before the first package switch" 3;; esac
fi
# ---- configs used: the harness list (dumped by configs.py as nightly14.json for the record) and the sw8k cell
{ echo "full: ${FULL_CONFIGS:-harness scripts.perf.configs ($ST at $(git -C "$ST" rev-parse --short HEAD 2>/dev/null))}"; if [ "$SW8K" = 1 ]; then echo "sw8k: $SW8K_CONFIGS"; else echo "sw8k: not run (SW8K=0)"; fi; } >"$RES/configs-used.txt"
[ -n "$FULL_CONFIGS" ] && cp "$FULL_CONFIGS" "$RES/configs-used-full.json"
[ "$SW8K" = 1 ] && cp "$SW8K_CONFIGS" "$RES/configs-used-sw8k.json"; [ -s "$H/nightly14.json" ] && cp "$H/nightly14.json" "$RES/configs-used-nightly14.json"

# ---- the passes: PASSES = arm names (per arm k: <arm>-pass<k>, then <arm>-sw8k-pass<k> only with SW8K=1); or PASS_TAGS for a resume
declare -A ARMCOUNT
if [ -n "$PASS_TAGS" ]; then TAGS=$PASS_TAGS; else
  TAGS=""
  for item in $PASSES; do
    arm_known "$item" || abort_early "PASSES contains an unknown arm '$item' (base|target)" 2
    ARMCOUNT[$item]=$(( ${ARMCOUNT[$item]:-0} + 1 )); TAGS="$TAGS $item-pass${ARMCOUNT[$item]}"; [ "$SW8K" = 1 ] && TAGS="$TAGS $item-sw8k-pass${ARMCOUNT[$item]}"
  done
fi
status "pass tags: $TAGS"
fails=0; incomplete=""; known_failed=""; recovered=""; stop_reason=""; PASS_S=0; SW8K_S=0; first=1; zero_runs=0; need=$NEED_FLOOR_S
for tag in $TAGS; do
  arm=$(arm_of "$tag"); kind=$(kind_of "$tag"); attn=$(attn_of_kind "$kind")
  arm_known "$arm" && [ "$kind" != unknown ] || { stop_reason="bad pass tag '$tag' (want <arm>-pass<k> or <arm>-sw8k-pass<k>)"; break; }
  case $kind in
    sw8k) cfg=$SW8K_CONFIGS; tmo=$SW8K_TIMEOUT;;
    full) cfg=$FULL_CONFIGS; tmo=$DRIVER_TIMEOUT;;
  esac
  if [ -e "$RES/$tag/perf.json" ] && [ "$RESUME_OVERWRITE" != 1 ]; then status "$tag: results already exist; skipping (RESUME_OVERWRITE=1 to redo)"; continue; fi
  if [ $first = 1 ] && past "$DEADLINE_START"; then stop_reason="past DEADLINE_START before the first pass ($tag)"; break; fi
  if [ "$kind" = full ] && past "$PASS_DEADLINE"; then stop_reason="past PASS_DEADLINE before $tag"; break; fi
  ls_state=$(lease_state)
  case $ls_state in
    free) ;;
    busy) stop_reason="CI lease busy before $tag; stopping safely"; break;;
    *) stop_reason="DUT did not answer the lease check 3 times before $tag; stopping safely"; break;;
  esac
  if [ "$kind" = sw8k ]; then need=$(( SW8K_S + 600 )); [ "$need" -lt 1200 ] && need=1200   # the sw8k cell: measured run + 10 min, at least 20 min
  else need=$(( PASS_S + 600 )); [ "$need" -lt "$NEED_FLOOR_S" ] && need=$NEED_FLOOR_S; fi   # a full pass must be able to finish before DRIVER_END_BY (measured pass + 10 min, at least NEED_FLOOR_S; 6600 = 110 min was the 14-config value)
  if [ $(( $(ts "$DRIVER_END_BY") - $(now_s) )) -lt "$need" ]; then stop_reason="not enough time before DRIVER_END_BY for $tag (need about $((need/60)) min)"; break; fi
  first=0
  W_TOOK_MACHINE=1   # from here on the DUT may differ from the preflight's state: the restore path runs (codex point 1)
  if ! ensure_state "$arm" "$attn"; then stop_reason="switch to $arm with $attn attention before $tag failed: ${VERIFY_FAIL:-package or restart step} (stop safely)"; fails=$((fails+1)); break; fi
  run_pass "$tag" "$cfg" "$tmo"; rc=$?
  if [ "$kind" = sw8k ]; then [ "$LAST_RUN_S" -gt "$SW8K_S" ] && SW8K_S=$LAST_RUN_S; else [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S; fi
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during $tag: operator stop"; fails=$((fails+1)); break; fi
  if [ $rc -eq 9 ]; then stop_reason="CI lease became busy during $tag (driver rc 9; stop safely)"; incomplete="$incomplete $tag"; fails=$((fails+1)); break; fi
  if [ "$LAST_COMPLETED" -eq 0 ]; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi
  [ $rc -eq 0 ] && continue
  fails=$((fails+1))
  if [ $rc -eq 124 ]; then status "$tag: the driver ran past its timeout (rc 124); no repeat, completed configs stay in perf.json raw records"; incomplete="$incomplete $tag"; continue; fi
  if [ $(( $(ts "$DRIVER_END_BY") - $(now_s) )) -lt "$need" ]; then stop_reason="no time for a repeat of $tag before DRIVER_END_BY"; incomplete="$incomplete $tag"; break; fi
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken"; incomplete="$incomplete $tag"; break; fi
  # restart the engines and repeat the run once, unless every failed cell is a known systematic failure (failed twice before)
  systematic=1
  if [ -z "$LAST_FAILED_CONFIGS" ]; then systematic=0; else for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$known_failed" || systematic=0; done; fi
  if [ $systematic = 1 ]; then status "$tag: the failed cells ($LAST_FAILED_CONFIGS) are known systematic failures; not repeating"; incomplete="$incomplete $tag"; continue; fi
  status "$tag: repeating the run once after an engine restart"
  # the first attempt's results directory is kept as <tag>-failed1 (an older copy of that name is removed; both names are
  # guarded with :? so an empty variable can never widen the removal)
  rm -rf "${RES:?}/${tag:?}-failed1"; mv "$RES/$tag" "$RES/$tag-failed1"
  first_failed=$LAST_FAILED_CONFIGS
  restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the repeat failed"
  run_pass "$tag" "$cfg" "$tmo"; rc=$?
  if [ "$kind" = sw8k ]; then [ "$LAST_RUN_S" -gt "$SW8K_S" ] && SW8K_S=$LAST_RUN_S; else [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S; fi
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during the repeat of $tag: operator stop"; break; fi
  if [ $rc -eq 9 ]; then stop_reason="CI lease became busy during the repeat of $tag (driver rc 9; stop safely)"; incomplete="$incomplete $tag"; break; fi
  if [ "$LAST_COMPLETED" -eq 0 ]; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi
  if [ $rc -eq 0 ]; then fails=$((fails-1)); recovered="$recovered $tag"; status "$tag: repeat ok (recovered pass; the first attempt is kept as $tag-failed1)"; continue; fi
  if [ $rc -eq 8 ]; then stop_reason="engine environment wrong for the attention mode after provisioning in both runs of $tag (driver rc 8; stop safely)"; incomplete="$incomplete $tag"; break; fi
  status "$tag: failed twice (rc $rc); continuing with the next pass (gap reported)"; incomplete="$incomplete $tag"
  for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$first_failed" && known_failed="$known_failed $c"; done   # systematic = failed in both runs
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken"; break; fi
done
[ -n "$stop_reason" ] && status "passes stopped: $stop_reason"

# ---- restore: config.env cleared first, then the restore-target package, production up, Bill's marker, the flock
restore_and_release
echo "incomplete passes:${incomplete:- none}; stop reason: ${stop_reason:-none}; problems:${problems:- none}; known systematic failures:${known_failed:- none}; recovered passes:${recovered:- none}" >"$RES/outcome.txt"
# ---- summary (never fatal): base vs target per config, the sw8k cell, memory; summary.md + summary.json in $RES
if "$PY" "$H/summarize.py" --res "$RES" >"$RES/summary.md" 2>"$RES/summarize.err"; then say "summary written: $RES/summary.md"; else say "WARNING: summarize.py failed (see $RES/summarize.err)"; fi
if [ $fails -eq 0 ] && [ -z "$problems" ] && [ -z "$stop_reason" ]; then status "campaign done"; touch "$RES/.done"
else status "campaign done with $fails pass failure(s); incomplete:${incomplete:- none}; stop: ${stop_reason:-none}; problems:${problems:- none}; recovered:${recovered:- none}"; touch "$RES/.done-with-failures"; fi
