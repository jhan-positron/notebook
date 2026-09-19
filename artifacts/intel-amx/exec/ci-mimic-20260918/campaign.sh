#!/usr/bin/env bash
# ci-mimic campaign 2026-09-18: the nightly System CI perf phase, run by hand on the WHOLE of delphi-3bda
# after the nightly ends, once per arm:
#   base   = the tron .deb the nightly installed today (no AMX code compiled)
#   target = our .deb: PR #4424 (VNNI K) merged into the same main commit, deb preset with
#            TRON_AMX_DISPATCH=ON and TRON_K_VNNI=ON  (/var/tmp/jhan/ci-mimic-20260918/target.deb)
# Same client code as the nightly (systems_test scripts/perf.py test_performance through the Caddy proxy,
# platformd provisioning per config, USE_HW_ATTN untouched), run from this host with st_ci_perf.py.
#
# Runs on the CLIENT host (claude-agentsrv), detached (launch.sh). DUT steps go over ssh (dut.sh).
# Order per pass: pass 1 = base, target; pass 2 = target, base (saves one package swap).
# Env knobs: PASSES (default 1; jhan 2026-09-18: 1 pass), DEADLINE_START (no arm starts after this UTC instant),
#            SMOKE=1 (one config, base only, no swap/restore/marker; for tooling checks),
#            SMOKE_MODELS (comma list for SMOKE, default ingested-qwen-3-4b-instruct-2507-tp2),
#            AMX_PROBE (default 1: 20 s EXE.AMX_BUSY sample before the llama-8b and qwen-3-4b tp2 benchmarks),
#            NO_WAIT=1 (skip the lease wait; SMOKE implies it).
# Approved by jhan 2026-09-18 02:1x UTC: package swap + restore on 3bda, marker release, PASSES=1, AMX probe kept.
set -u
NAME=ci-mimic-20260918
H=/home/jhan/workspace/intel-AMX/exec/$NAME
RES=/home/jhan/workspace/intel-AMX/exec/results/$NAME
ST=/home/jhan/workspace/ai-runs/systems_test
PY=$ST/.venv/bin/python
DUT_ALIAS=delphi-3bda
PASSES=${PASSES:-1}
DEADLINE_START=${DEADLINE_START:-2026-09-18T21:30:00Z}   # no arm starts after this (Sat nightly prep begins 02:45 UTC)
EARLIEST_START=${EARLIEST_START:-2026-09-18T04:30:00Z}   # never take the machine during the pre-nightly window
SMOKE=${SMOKE:-0}; NO_WAIT=${NO_WAIT:-$SMOKE}; AMX_PROBE=${AMX_PROBE:-1}
SMOKE_MODELS=${SMOKE_MODELS:-ingested-qwen-3-4b-instruct-2507-tp2}
mkdir -p "$RES"
STATUS=$RES/.status
say() { echo "$(date -u +%FT%TZ) $*"; }
status() { say "$*"; echo "$(date -u +%FT%TZ) $*" >"$STATUS"; }
dut() { ssh -o BatchMode=yes -o ConnectTimeout=20 "$DUT_ALIAS" bash "$H/dut.sh" "$@"; }
now_s() { date -u +%s; }
ts() { date -u -d "$1" +%s; }

LOCK_PID=; REMOTE_LOCK_PID=
hold_lock() {  # hold the host-wide campaign flock on the DUT for the whole run; the remote holder prints its pid
  # (killing the local ssh alone leaves the remote sleep alive and the lock held: seen 13:19 and 13:36 UTC)
  ssh -o BatchMode=yes -o ServerAliveInterval=30 "$DUT_ALIAS" 'flock -n /var/tmp/jhan/3bda-campaign.lock -c "echo held pid \$\$; exec sleep 50000"' >"$RES/.lock.out" 2>&1 &
  LOCK_PID=$!; sleep 3
  grep -q "^held pid" "$RES/.lock.out" || { say "campaign flock on the DUT is HELD by another campaign"; return 1; }
  REMOTE_LOCK_PID=$(awk '/^held pid/{print $3}' "$RES/.lock.out")
  return 0
}
cleanup() {
  [ -n "$REMOTE_LOCK_PID" ] && ssh -o BatchMode=yes "$DUT_ALIAS" "kill $REMOTE_LOCK_PID 2>/dev/null; pkill -P $REMOTE_LOCK_PID 2>/dev/null" 2>/dev/null
  [ -n "$LOCK_PID" ] && kill "$LOCK_PID" 2>/dev/null
}
trap cleanup EXIT

run_arm() {  # $1 arm $2 pass -> rc of the driver
  local arm=$1 pass=$2 dir=$RES/$1-pass$2 models=
  mkdir -p "$dir"
  [ "$SMOKE" = 1 ] && models=$SMOKE_MODELS
  status "arm $arm pass $pass: starting perf phase ($(dut installed))"
  ( cd "$ST" && env PYTHONPATH="$H/talos_stub:$ST" \
      OPENAI_HOST=http://delphi-3bda.positron.internal/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
      PLATFORM_TYPE=granite_rapids_72_rinzler SYSTEM_CI_SPECULATION=0 SSH_USER=jhan SSH_PASS= \
      HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false \
      CI_MIMIC_ARM=$arm CI_MIMIC_OUT=$dir/perf.json TALOS_STUB_OUT=$dir/talos.json CI_MIMIC_MODELS="$models" \
      CI_MIMIC_AMX_PROBE=$AMX_PROBE \
      timeout 18000 "$PY" "$H/st_ci_perf.py" >"$dir/driver.log" 2>&1 )
  local rc=$?
  grep -E "Perf test for|RESULT|Running averages|engine count|deleted|Error|Traceback" "$dir/driver.log" | tail -40 >"$dir/summary.txt"
  status "arm $arm pass $pass: driver rc=$rc ($(grep -c 'Perf test for' "$dir/driver.log") configs completed)"
  return $rc
}

status "campaign start (PASSES=$PASSES SMOKE=$SMOKE DEADLINE_START=$DEADLINE_START)"
# ---- wait for the machine: earliest-start, CI lease (600 s grace), campaign flock
if [ "$NO_WAIT" != 1 ]; then
  while [ "$(now_s)" -lt "$(ts "$EARLIEST_START")" ]; do status "waiting for EARLIEST_START $EARLIEST_START"; sleep 600; done
  until dut lease-free >/dev/null 2>&1; do status "waiting: CI lease busy"; sleep 120; done
  status "CI lease free"
fi
until hold_lock; do status "waiting: campaign flock held by another campaign"; kill "$LOCK_PID" 2>/dev/null; sleep 300; done
if [ "$(now_s)" -gt "$(ts "$DEADLINE_START")" ]; then status "ABORT: past DEADLINE_START before starting"; exit 3; fi

# ---- preflight (read-only) and the base identity = whatever the nightly installed today
PF=$RES/preflight.txt; [ "$SMOKE" = 1 ] && PF=$RES/preflight-smoke.txt   # (${SMOKE:+x} also fires for SMOKE=0; that aborted the 13:19 UTC launch)
dut preflight >"$PF" 2>&1; say "preflight written ($PF)"
read -r BASE_VERSION BASE_SHA < <(dut installed)
say "base package = $BASE_VERSION rinzler sha $BASE_SHA"
case $BASE_VERSION in 2026.*) ;; *) status "ABORT: unexpected installed tron version '$BASE_VERSION'"; exit 4;; esac
if [ "$SMOKE" != 1 ]; then
  grep -q "target build: status=ok" "$PF" || { status "ABORT: target build not ok (see $PF)"; exit 5; }
  if grep -q "num-expert-replicas count: [1-9]" "$PF"; then say "WARNING: the rinzler unit file carries a hand edit (--num-expert-replicas); the nightly's deb file has none"; fi
  echo "$BASE_VERSION $BASE_SHA" >"$RES/base-identity.txt"
fi

# ---- passes
fails=0
for pass in $(seq 1 "$PASSES"); do
  if [ $((pass % 2)) -eq 1 ]; then order="base target"; else order="target base"; fi
  [ -n "${ARMS:-}" ] && order=$ARMS   # e.g. ARMS=target to re-run one arm after a driver failure (2026-09-18 16:0x UTC)
  [ "$SMOKE" = 1 ] && order="base"
  for arm in $order; do
    if [ "$(now_s)" -gt "$(ts "$DEADLINE_START")" ]; then status "deadline reached before $arm pass $pass; stopping"; break 2; fi
    if [ "$SMOKE" != 1 ]; then
      if [ "$arm" = target ]; then dut ensure-target; else dut ensure-base "$BASE_VERSION" "$BASE_SHA"; fi
      rc=$?; [ $rc -eq 0 ] || { status "package step for $arm failed rc=$rc; stopping"; fails=$((fails+1)); break 2; }
      sleep 20  # let platformd notice the package change before the harness patches its config
    fi
    if run_arm "$arm" "$pass"; then fails=0; else fails=$((fails+1)); [ $fails -ge 2 ] && { status "two consecutive arm failures; stopping"; break 2; }; fi
  done
done

# ---- restore the nightly's package and give Bill his half back
if [ "$SMOKE" != 1 ]; then
  if dut ensure-base "$BASE_VERSION" "$BASE_SHA"; then status "restore ok: $(dut installed)"; else status "RESTORE FAILED: $(dut installed) (wanted $BASE_VERSION); jhan must reinstall tron by hand"; fi
  ssh -o BatchMode=yes "$DUT_ALIAS" bash ~/workspace/intel-AMX/exec/bill-share.sh release 2>&1 | tail -2
fi
status "campaign done"
if [ "$SMOKE" = 1 ]; then touch "$RES/.done-smoke"; else touch "$RES/.done"; fi
