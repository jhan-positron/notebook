#!/usr/bin/env bash
# i4500fix-20260928 cells (runs ON delphi-3bda, our half): the issue #4500 fix measured the way block m6 of
# exec/issue4500-20260918/m6.sh measured the loss: one rinzler engine per cell on our half, driven by the nightly's
# own client (systems_test testlib/tps.py through st_perf2.py: sharegpt prompts, generate 1536, 10 rounds, TPS captured
# between generated tokens 896 and 1024), USE_HW_ATTN unset (FPGA attention for the ingested qwen model, CPU attention
# for the hand-written llama plugin, exactly the nightly's modes).
# Words used here: binary (arm in the code) = one rinzler binary; cell = (model, tp, users per engine, prompt, binary);
# rep = repetition. Binaries:
#   base    = exec/canon-ci-20260918 deb rinzler: main 3faba6d0fd + deb preset AMX ON, row-major K (the canonical AMX build)
#   vnni    = exec/ci-mimic-20260918 target deb rinzler: main 3faba6d0fd + PR #4424 30c4ac82cb, AMX + VNNI K (the loss)
#   fix     = build-deb.sh: the vnni package + the fix commit (row-major tail block)
#   nightly = /opt/positron/bin/rinzler, whatever the nightly installed (a reference against today's main; optional)
# Cells (CELLS, "model|tp|users|prompt" per line): qwen-3-4b tp2 with 2 users and tp4 with 4 users at prompt 1024 (the
# m6 cells = the nightly's loads), llama-3.1-8b tp2 with 8 users at prompt 4096 (jhan's request of 2026-09-28).
# REPS repetitions, binaries interleaved (odd reps forward, even reversed). Resume: a cell whose STATUS is done is skipped.
# Machine handling: lib.sh (NOT_BEFORE, lease, other person, idle takeover of the production engines, pre-CI hold).
# Production serving is brought back up at the end when this script took it down (platformd POST /api/inference/up).
# Outputs: exec/results/i4500fix-20260928/cells/<model>__tp<N>__<U>u__p<P>__<arm>__rep<R>/{meta.json, perf-e0.json/.log,
#   rinzler-e0.log, amx_busy.txt, proof.txt, perf.json, STATUS}, summary.md/json; log exec/logs/i4500fix-20260928.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4500fix-20260928
H1=$EXEC/more-testing-r1
ST=/home/jhan/workspace/ai-runs/systems_test
PY=/var/tmp/jhan/st-venv/bin/python
RES=$EXEC/results/i4500fix-20260928
LOG=$EXEC/logs/i4500fix-20260928.log
STATUS=$EXEC/logs/i4500fix-20260928.status
MARKER=$RES/campaign.done
REPS=${REPS:-3}
ARMS=${ARMS:-"base vnni fix nightly"}
CELLS=${CELLS:-"qwen3-4b|2|2|1024
qwen3-4b|4|4|1024
llama-8b|2|8|4096"}
CLIENT_CPUS=87-95,231-239
BIN_base=/var/tmp/jhan/canon-ci-20260918/root/opt/positron/bin/rinzler
BIN_vnni=/var/tmp/jhan/ci-mimic-20260918/root/opt/positron/bin/rinzler
BIN_fix=/var/tmp/jhan/i4500fix-20260928/root/opt/positron/bin/rinzler
BIN_nightly=/opt/positron/bin/rinzler
PORT=13100; LAUNCH_CORES=73,217
HPFILE=/dev/hugepages/amx-i4500fix-$PORT
OUR_RZ_RE="rinzler .*--hugepage_file $HPFILE"
HARNESS_RE='st_perf2[.]py .*results/i4500fix-20260928'
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES/cells" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
source "$C/lib.sh"
model_of() { case $1 in qwen3-4b) echo "ingested-qwen-3-4b-instruct-2507-tp$2" ;; llama-8b) echo "llama-3.1-8b-instruct-good-tp$2" ;; *) return 1 ;; esac; }
arm_bin() { local v="BIN_$1"; echo "${!v:-}"; }
engine_sysargs() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
  esac
}
kill_ours() { pkill -TERM -u jhan -f "$HARNESS_RE" 2>/dev/null; pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null; return 0; }
RZ_PID=""
rz_stop() {
  [ -n "$RZ_PID" ] && kill -0 "$RZ_PID" 2>/dev/null && { kill -TERM "$RZ_PID" 2>/dev/null; for _ in $(seq 1 60); do kill -0 "$RZ_PID" 2>/dev/null || break; sleep 1; done; kill -0 "$RZ_PID" 2>/dev/null && kill -KILL "$RZ_PID" 2>/dev/null; wait "$RZ_PID" 2>/dev/null; }
  pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null; sleep 2; pkill -KILL -u jhan -f "$OUR_RZ_RE" 2>/dev/null
  fusermount3 -uz /var/tmp/jhan/rz-fuse/$PORT 2>/dev/null
  remove_our_hugepage_files "$HPFILE"
  RZ_PID=""; echo "rz_stop: done $(ts); HugePages_Free=$(hp_free)"
}
finish() { stop_watcher; [ "$1" = aborted ] && { trap '' TERM; [ "$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')" = "$$" ] && kill -TERM -- -$$ 2>/dev/null; }; kill_ours; sleep 2; rz_stop 2>/dev/null; campaign_guard_release 2>/dev/null; python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true; serving_restore; echo "$1" >"$MARKER"; status "finished: $1"; echo "=== i4500fix campaign finished $(ts): $1 ==="; }
rz_launch() {  # ARM TP MODEL LOGFILE
  local arm=$1 tp=$2 model=$3 logf=$4 bin; bin=$(arm_bin "$arm"); [ -x "$bin" ] || return 1
  fusermount3 -uz /var/tmp/jhan/rz-fuse/$PORT 2>/dev/null; mkdir -p /var/tmp/jhan/rz-fuse/$PORT /var/tmp/jhan/i4500fix-cwd
  local envc=(env -u TRON_AMX_DISABLE -u USE_HW_ATTN -u SYSTEM_CONFIG -u TRON_HWATTN_EARLY_LAUNCH_MIN_B TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug RZ_FUSE_MOUNT_PATH=/var/tmp/jhan/rz-fuse/$PORT RZ_FUSE_MOUNT_PRESCOPED=1 RZ_ENABLE_SAVE_TOKENS=1 TRON_USE_SPECULATION=0)
  sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null
  echo "rz_launch arm=$arm tp=$tp bin=$bin model=$model $(ts)"
  # cwd must be writable by jhan: rinzler writes alderaan.log into its working directory (m6 trap 2026-09-19).
  (cd /var/tmp/jhan/i4500fix-cwd || exit 1; [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; exec "${envc[@]}" taskset -c "$LAUNCH_CORES" "$bin" --model "$model" --port "$PORT" $(engine_sysargs "$tp") --hugepage_file "$HPFILE" >"$logf" 2>&1) &
  RZ_PID=$!
}
rz_ready() {  # MODEL LOGFILE
  local model=$1 deadline; deadline=$(( $(date +%s) + 600 ))
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
run_cell() {  # MODELKEY TP USERS PROMPT ARM REP
  local mk=$1 tp=$2 users=$3 prompt=$4 arm=$5 rep=$6 cell rc t0 ppid model bin
  model=$(model_of "$mk" "$tp") || { echo "$(ts) unknown model key $mk"; return 1; }
  bin=$(arm_bin "$arm"); [ -x "$bin" ] || { echo "$(ts) binary of $arm missing ($bin); cell skipped"; return 1; }
  # The installed package changes at the nightly's reinstall (~02:00 UTC): a nightly cell whose binary differs from the
  # one recorded at the campaign start is skipped, so one arm name never pools two packages.
  if [ "$arm" = nightly ] && [ "$(sha256sum "$bin" | cut -c1-16)" != "$(cat "$RES/nightly.sha" 2>/dev/null)" ]; then echo "$(ts) nightly binary changed since the campaign start; cell skipped"; return 1; fi
  cell=$RES/cells/${mk}__tp${tp}__${users}u__p${prompt}__${arm}__rep${rep}
  [ "$(cat "$cell/STATUS" 2>/dev/null)" = done ] && { echo "$(ts) cell $(basename "$cell") already done"; return 0; }
  mkdir -p "$cell"; NEED_HUGEPAGES=$([ "$tp" = 4 ] && echo 256 || echo 128) wait_clear || return 2; take_guard || return 2
  status "cell $(basename "$cell")"
  echo running >"$cell/STATUS"; rm -f "$cell/STOPPED"
  python3 - "$cell/meta.json" "$model" "$arm" "$tp" "$users" "$prompt" "$rep" "$bin" "$(engine_sysargs "$tp")" "$(machine_line)" <<'PY'
import json, sys, subprocess, datetime
p, model, arm, tp, users, prompt, rep, binf, place, machine = sys.argv[1:11]
sha = subprocess.run(['sha256sum', binf], capture_output=True, text=True).stdout.split()[0]
json.dump({"model": model, "arm": arm, "tp": int(tp), "users_per_engine": int(users), "prompt_length": int(prompt), "rep": int(rep), "binary": binf, "binary_sha256": sha,
           "env": "USE_HW_ATTN unset, TRON_AMX_DISABLE unset, TRON_USE_SPECULATION=0", "placement": place, "machine": machine,
           "started": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
           "harness": "systems_test testlib/tps.py via exec/i4500fix-20260928/st_perf2.py: sharegpt prompts of the given length, generate 1536, 10 rounds, capture 896-1024; one client, one engine"}, open(p, 'w'), indent=1)
PY
  watch_run "$cell/STOPPED" "$OUR_RZ_RE|$HARNESS_RE" "$HPFILE" & WPID=$!
  rz_launch "$arm" "$tp" "$model" "$cell/rinzler-e0.log" || { stop_watcher; rz_stop; campaign_guard_release; echo start-failed >"$cell/STATUS"; return 1; }
  if ! rz_ready "$model" "$cell/rinzler-e0.log"; then stop_watcher; rz_stop; campaign_guard_release; if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"; return 2; fi; echo start-failed >"$cell/STATUS"; return 1; fi
  t0=$(date +%s); mkdir -p "$cell/work-e0"
  ( cd "$cell/work-e0" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG PYTHONPATH="$H1/talos_stub:$ST" OPENAI_HOST=http://delphi-3bda:$PORT/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false timeout 3600 taskset -c "$CLIENT_CPUS" "$PY" "$C/st_perf2.py" --model "$model" --users "$users" --prompt-length "$prompt" --out "$cell/perf-e0.json" >"$cell/perf-e0.log" 2>&1 ) &
  local cpid=$!
  amx_probe_bg "$cell" "$RZ_PID" & ppid=$!
  wait "$cpid"; rc=$?; wait "$ppid" 2>/dev/null
  stop_watcher
  { echo "== engine (tp$tp, port $PORT, arm $arm)"; grep -E "Version:|Configured instance|App CPU list|HW attention" "$cell/rinzler-e0.log" | head -6 | cut -c1-240; echo "== amx_busy"; cat "$cell/amx_busy.txt" 2>/dev/null; } >"$cell/proof.txt"
  rz_stop; campaign_guard_release
  python3 "$EXEC/p0perf-20260913/combine.py" "$cell" 1 2>/dev/null || echo "$(ts) combine failed for $cell"
  if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"; elif [ $rc -eq 0 ] && [ -s "$cell/perf.json" ]; then echo done >"$cell/STATUS"; else echo failed >"$cell/STATUS"; fi
  echo "$(ts) cell $(basename "$cell") rc=$rc status=$(cat "$cell/STATUS") $(cat "$cell/STOPPED" 2>/dev/null) amx=$(grep amx_busy "$cell/amx_busy.txt" 2>/dev/null | cut -d, -f1) $(tail -1 "$cell/perf-e0.log" 2>/dev/null | cut -c1-140) secs=$(( $(date +%s) - t0 ))"
  case $(cat "$cell/STATUS") in done) return 0 ;; stopped) return 2 ;; *) return 1 ;; esac
}

exec >>"$LOG" 2>&1
pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/i4500fix-20260928/campaign[.]sh$' | grep -vx "$$" | grep -q . && { echo "$(ts) another campaign.sh runs; exit"; exit 1; }
rm -f "$MARKER"; trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== i4500fix campaign started $(ts) pid $$ REPS=$REPS ARMS=[$ARMS] NOT_BEFORE=${NOT_BEFORE:-} ==="
for a in $ARMS; do b=$(arm_bin "$a"); [ -x "$b" ] && echo "$(ts) $a = $b sha256 $(sha256sum "$b" | cut -c1-16)" || echo "$(ts) WARNING $a binary missing: $b (its cells will be skipped)"; done
[ -s "$RES/nightly.sha" ] || sha256sum "$BIN_nightly" | cut -c1-16 >"$RES/nightly.sha"
echo "$(ts) nightly binary at start: $(cat "$RES/nightly.sha") $(dpkg-query -W -f='${Version}' tron 2>/dev/null)"
kill_ours; sleep 2; rz_stop
status "phase 0: waiting for a free machine"; echo "$(ts) $(machine_line)"
wait_clear || { finish preci-hold-before-start; exit 0; }
fail=0
for rep in $(seq 1 "$REPS"); do
  arms=$ARMS; [ $((rep % 2)) -eq 0 ] && arms=$(echo $ARMS | tr ' ' '\n' | tac | tr '\n' ' ')
  while IFS='|' read -r mk tp users prompt; do
    [ -n "$mk" ] || continue
    for arm in $arms; do
      run_cell "$mk" "$tp" "$users" "$prompt" "$arm" "$rep"; rc=$?; [ $rc -eq 0 ] || fail=$((fail+1))
      [ $PRECI_STOP = 1 ] && break 3
    done
  done <<<"$CELLS"
  echo "$(ts) repetition $rep done, failed so far: $fail"
done
if [ $PRECI_STOP = 1 ]; then finish "preci-hold (failed $fail)"; elif [ $fail -eq 0 ]; then finish ok; else finish "check-output (failed $fail)"; fi
exit 0
