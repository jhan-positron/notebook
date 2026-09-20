#!/usr/bin/env bash
# issue4500 block m6: CI-layout confirmation on OUR half of delphi-3bda with rinzler (the production server)
# and the nightly's own client (systems_test testlib/tps.py through exec/more-testing-r1/st_perf.py: prompt 1024
# sharegpt, generate 1536, 10 rounds, TPS captured between generated tokens 896 and 1024). One engine per cell,
# placed like the nightly's instance-2 (tp2) or the tp4 engine (instance 1,2), USE_HW_ATTN unset (FPGA attention).
# Words used here: arm = one rinzler binary plus environment; cell = (tp, users per engine, arm); rep = repetition.
# Arms: base = the installed nightly deb rinzler (2026.09.18-3faba6d0, no AMX code); target = the ci-mimic target
#   deb rinzler (main 3faba6d0 + PR 4424 30c4ac82cb, TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON); targetkill = target +
#   TRON_AMX_DISABLE=1; targetminb1 = target + TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 (early launch at 2 users);
#   baseminb1 = base + the same knob (the knob exists in both binaries: strings check 2026-09-19).
# Cells: tp2 x 2 users (the nightly's tp2 load): base baseminb1 target targetkill targetminb1; tp4 x 4 users (the
#   nightly's tp4 load, already an early launch): base target targetkill. REPS interleaved (odd reps forward, even reversed).
# Machine handling as in campaign.sh: waits (never acts) while a rinzler@N unit is active or fewer than 256
# hugepages are free; the pre-CI hold 01:40-03:45 UTC ends the block; guard per cell; watcher kills OUR rinzler only.
# Outputs: exec/results/issue4500-20260918/m6/cells/<tp>__<users>u__<arm>__rep<N>/{meta.json, perf-e0.json/.log,
#   rinzler-e0.log, amx_busy.txt, proof.txt, perf.json, STATUS}, m6/summary.md; log exec/logs/issue4500-m6.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/issue4500-20260918
H1=$EXEC/more-testing-r1
ST=/home/jhan/workspace/ai-runs/systems_test
PY=/var/tmp/jhan/st-venv/bin/python
RES=$EXEC/results/issue4500-20260918/m6
LOG=$EXEC/logs/issue4500-m6.log
MARKER=$EXEC/logs/issue4500-m6.done
STATUS=$EXEC/logs/issue4500-m6.status
REPS=${REPS:-2}
CLIENT_CPUS=87-95,231-239
BILL_UID=1062305141
BIN_base=/opt/positron/bin/rinzler
BIN_target=/var/tmp/jhan/ci-mimic-20260918/root/opt/positron/bin/rinzler
QWEN2=ingested-qwen-3-4b-instruct-2507-tp2
QWEN4=ingested-qwen-3-4b-instruct-2507-tp4
OUR_RZ_RE='^(/opt/positron/bin/rinzler|/var/tmp/jhan/ci-mimic-20260918/root/opt/positron/bin/rinzler) .*--hugepage_file /dev/hugepages/amx-i4500m6'
HARNESS_RE='st_perf[.]py .*issue4500-20260918/m6'
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES/cells" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
hp_free() { awk '/^HugePages_Free/{print $2}' /proc/meminfo; }
machine_line() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(hp_free) units_active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active$') bill_procs=$(ps -u $BILL_UID -o pid= 2>/dev/null | wc -l)"; }
arm_bin() { case $1 in base|baseminb1) echo "$BIN_base" ;; target|targetkill|targetminb1) echo "$BIN_target" ;; *) return 1 ;; esac; }
arm_env() { case $1 in targetkill) echo "TRON_AMX_DISABLE=1" ;; targetminb1|baseminb1) echo "TRON_HWATTN_EARLY_LAUNCH_MIN_B=1" ;; *) echo "" ;; esac; }
engine_sysargs() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
  esac
}
model_of() { case $1 in 2) echo "$QWEN2" ;; 4) echo "$QWEN4" ;; esac; }
PORT=13100; LAUNCH_CORES=73,217
HPFILE=/dev/hugepages/amx-i4500m6-$PORT

preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler@N unit active"; return 0; }
  [ "$(hp_free)" -ge 256 ] || { echo "only $(hp_free) free hugepages"; return 0; }
  return 1
}
PRECI_STOP=0
wait_clear() { local why waited=0; while why=$(blocked); do [ $waited = 0 ] && { status "waiting: $why"; waited=1; }; if preci_hold; then PRECI_STOP=1; return 1; fi; sleep 60; done; return 0; }
take_guard() { local waited=0; until campaign_guard_acquire; do [ $waited = 0 ] && { status "waiting: guard refused"; waited=1; }; sleep 60; wait_clear || return 1; done; return 0; }
kill_ours() { pkill -TERM -u jhan -f "$HARNESS_RE" 2>/dev/null; pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null; return 0; }
RZ_PID=""
rz_stop() {
  [ -n "$RZ_PID" ] && kill -0 "$RZ_PID" 2>/dev/null && { kill -TERM "$RZ_PID" 2>/dev/null; for _ in $(seq 1 60); do kill -0 "$RZ_PID" 2>/dev/null || break; sleep 1; done; kill -0 "$RZ_PID" 2>/dev/null && kill -KILL "$RZ_PID" 2>/dev/null; wait "$RZ_PID" 2>/dev/null; }
  pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null; sleep 2; pkill -KILL -u jhan -f "$OUR_RZ_RE" 2>/dev/null
  fusermount3 -uz /var/tmp/jhan/rz-fuse/$PORT 2>/dev/null
  for f in "$HPFILE"* /dev/hugepages/slice-*-of-8; do [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f"; done
  RZ_PID=""; echo "rz_stop: done $(ts); HugePages_Free=$(hp_free)"
}
watch_run() { local sf=$1 why main=$$; [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; while :; do kill -0 "$main" 2>/dev/null || { kill_ours; exit 0; }; why=""; if ci_lease_busy; then why="CI lease busy"; elif rinzler_active; then why="rinzler@N unit active"; fi; [ -n "$why" ] && { [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"; kill_ours; }; sleep 10; done; }
WPID=""; stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
finish() { stop_watcher; [ "$1" = aborted ] && { trap '' TERM; [ "$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')" = "$$" ] && kill -TERM -- -$$ 2>/dev/null; }; kill_ours; sleep 2; rz_stop 2>/dev/null; campaign_guard_release 2>/dev/null; python3 "$C/m6_summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true; echo "$1" >"$MARKER"; status "finished: $1"; echo "=== m6 finished $(ts): $1 ==="; }

rz_launch() {  # ARM TP LOGFILE
  local arm=$1 tp=$2 logf=$3 bin envw model
  bin=$(arm_bin "$arm") || return 1; model=$(model_of "$tp")
  fusermount3 -uz /var/tmp/jhan/rz-fuse/$PORT 2>/dev/null; mkdir -p /var/tmp/jhan/rz-fuse/$PORT
  local envc=(env -u TRON_AMX_DISABLE -u USE_HW_ATTN -u SYSTEM_CONFIG -u TRON_HWATTN_EARLY_LAUNCH_MIN_B TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug RZ_FUSE_MOUNT_PATH=/var/tmp/jhan/rz-fuse/$PORT RZ_FUSE_MOUNT_PRESCOPED=1 RZ_ENABLE_SAVE_TOKENS=1 TRON_USE_SPECULATION=0)
  envw=$(arm_env "$arm"); [ -n "$envw" ] && envc+=("$envw")
  sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null
  echo "rz_launch arm=$arm tp=$tp bin=$bin env=[${envw:-none}] model=$model $(ts)"
  # cwd must be writable by jhan: rinzler writes alderaan.log into its working directory (the installed
  # /opt/positron/bin is root-owned; first launch 2026-09-19 17:54 UTC failed with "Permission denied"). The
  # binaries find their libraries through RUNPATH $ORIGIN, so the working directory does not matter for them.
  mkdir -p /var/tmp/jhan/i4500m6-cwd
  (cd /var/tmp/jhan/i4500m6-cwd || exit 1; [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; exec "${envc[@]}" taskset -c "$LAUNCH_CORES" "$bin" --model "$model" --port "$PORT" $(engine_sysargs "$tp") --hugepage_file "$HPFILE" >"$logf" 2>&1) &
  RZ_PID=$!
}
rz_ready() {  # TP LOGFILE
  local model deadline; model=$(model_of "$1"); deadline=$(( $(date +%s) + 600 ))
  while :; do
    kill -0 "$RZ_PID" 2>/dev/null || { echo "rz_ready: rinzler exited early"; tail -15 "$2" | cut -c1-200; return 1; }
    curl -s -m 5 "http://127.0.0.1:$PORT/v1/models" | grep -q "\"$model\"" && break
    [ "$(date +%s)" -ge "$deadline" ] && { echo "rz_ready: health timeout"; tail -15 "$2" | cut -c1-200; return 1; }
    sleep 5
  done
  curl -s -m 120 "http://127.0.0.1:$PORT/v1/chat/completions" -H 'Content-Type: application/json' -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello.\"}],\"max_tokens\":8}" | head -c 200; echo
  echo "rz_ready: port $PORT ready $(ts)"
}
amx_probe_bg() { local cell=$1 pid=$2; [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; sleep 75; { echo "pid=$pid start=$(ts)"; sudo -n perf stat -x, -e cpu/event=0xb7,umask=0x02,name=amx_busy/ -p "$pid" -- sleep 20 2>&1; } >"$cell/amx_busy.txt"; }

run_cell() {  # TP USERS ARM REP
  local tp=$1 users=$2 arm=$3 rep=$4 cell rc t0 ppid model
  cell=$RES/cells/tp${tp}__${users}u__${arm}__rep${rep}; model=$(model_of "$tp")
  [ "$(cat "$cell/STATUS" 2>/dev/null)" = done ] && { echo "$(ts) cell tp$tp ${users}u $arm rep$rep already done"; return 0; }
  mkdir -p "$cell"; wait_clear || return 2; take_guard || return 2
  status "cell tp$tp ${users}u arm=$arm rep=$rep"
  echo running >"$cell/STATUS"; rm -f "$cell/STOPPED"
  python3 - "$cell/meta.json" "$model" "$arm" "$tp" "$users" "$rep" "$(arm_bin "$arm")" "$(arm_env "$arm")" "$(engine_sysargs "$tp")" "$(machine_line)" <<'PY'
import json, sys, subprocess, datetime
p, model, arm, tp, users, rep, binf, envw, place, machine = sys.argv[1:11]
sha = subprocess.run(['sha256sum', binf], capture_output=True, text=True).stdout.split()[0]
json.dump({"model": model, "arm": arm, "tp": int(tp), "users_per_engine": int(users), "rep": int(rep), "binary": binf, "binary_sha256": sha, "env": envw or "(none)",
           "placement": place, "machine": machine, "started": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
           "harness": "systems_test testlib/tps.py via exec/more-testing-r1/st_perf.py: prompt 1024 (sharegpt), generate 1536, 10 rounds, capture 896-1024; one client, one engine; USE_HW_ATTN unset (FPGA attention)"}, open(p, 'w'), indent=1)
PY
  watch_run "$cell/STOPPED" & WPID=$!
  rz_launch "$arm" "$tp" "$cell/rinzler-e0.log" || { stop_watcher; rz_stop; campaign_guard_release; echo start-failed >"$cell/STATUS"; return 1; }
  if ! rz_ready "$tp" "$cell/rinzler-e0.log"; then stop_watcher; rz_stop; campaign_guard_release; if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"; return 2; fi; echo start-failed >"$cell/STATUS"; return 1; fi
  t0=$(date +%s); mkdir -p "$cell/work-e0"
  ( cd "$cell/work-e0" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG PYTHONPATH="$H1/talos_stub:$ST" OPENAI_HOST=http://delphi-3bda:$PORT/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false timeout 3000 taskset -c "$CLIENT_CPUS" "$PY" "$H1/st_perf.py" --model "$model" --users "$users" --out "$cell/perf-e0.json" >"$cell/perf-e0.log" 2>&1 ) &
  local cpid=$!
  amx_probe_bg "$cell" "$RZ_PID" & ppid=$!
  wait "$cpid"; rc=$?; wait "$ppid" 2>/dev/null
  stop_watcher
  { echo "== engine (tp$tp, port $PORT, arm $arm)"; grep -E "Version:|Configured instance|App CPU list|HW attention" "$cell/rinzler-e0.log" | head -6 | cut -c1-240; echo "== amx_busy"; cat "$cell/amx_busy.txt" 2>/dev/null; } >"$cell/proof.txt"
  rz_stop; campaign_guard_release
  python3 "$EXEC/p0perf-20260913/combine.py" "$cell" 1 2>/dev/null || echo "$(ts) combine failed for $cell"
  if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"; elif [ $rc -eq 0 ] && [ -s "$cell/perf.json" ]; then echo done >"$cell/STATUS"; else echo failed >"$cell/STATUS"; fi
  echo "$(ts) cell tp$tp ${users}u $arm rep$rep rc=$rc status=$(cat "$cell/STATUS") $(cat "$cell/STOPPED" 2>/dev/null) amx=$(grep amx_busy "$cell/amx_busy.txt" 2>/dev/null | cut -d, -f1) $(tail -1 "$cell/perf-e0.log" 2>/dev/null | cut -c1-140) secs=$(( $(date +%s) - t0 ))"
  case $(cat "$cell/STATUS") in done) return 0 ;; stopped) return 2 ;; *) return 1 ;; esac
}

exec >>"$LOG" 2>&1
pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/issue4500-20260918/m6[.]sh$' | grep -vx "$$" | grep -q . && { echo "$(ts) another m6.sh runs; exit"; exit 1; }
rm -f "$MARKER"; trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== issue4500 m6 started $(ts) pid $$ REPS=$REPS ==="
for a in base target; do b=$(arm_bin $a); [ -x "$b" ] || { status "ABORT: missing $b"; finish binary-missing; exit 1; }; echo "$(ts) $a = $b sha256 $(sha256sum "$b" | cut -c1-16)"; done
kill_ours; sleep 2; rz_stop
status "phase 0: waiting for a free machine"; echo "$(ts) $(machine_line)"
wait_clear || { finish preci-hold-before-start; exit 0; }
fail=0
for rep in $(seq 1 "$REPS"); do
  arms2="base baseminb1 target targetkill targetminb1"; arms4="base target targetkill"
  [ $((rep % 2)) -eq 0 ] && { arms2=$(echo $arms2 | tr ' ' '\n' | tac | tr '\n' ' '); arms4=$(echo $arms4 | tr ' ' '\n' | tac | tr '\n' ' '); }
  for arm in $arms2; do run_cell 2 2 "$arm" "$rep"; rc=$?; [ $rc -eq 0 ] || fail=$((fail+1)); [ $PRECI_STOP = 1 ] && break 2; done
  for arm in $arms4; do run_cell 4 4 "$arm" "$rep"; rc=$?; [ $rc -eq 0 ] || fail=$((fail+1)); [ $PRECI_STOP = 1 ] && break 2; done
  echo "$(ts) m6 repetition $rep done, failed so far: $fail"
done
if [ $PRECI_STOP = 1 ]; then finish "preci-hold (failed $fail)"; elif [ $fail -eq 0 ]; then finish ok; else finish "check-output (failed $fail)"; fi
exit 0
