#!/usr/bin/env bash
# l8bload-20260918: does the AMX gain on llama-3.1-8b grow with the load per engine?
# jhan 2026-09-18 19:5x UTC ("Let's do it. Go ahead.") on the hypothesis from the ci-mimic report:
# the AMX kernel speeds up only the attention part of a decode step, so its gain tracks the
# attention work per step (users x context) against the fixed dense-layer time. Nightly layout
# (2 users per engine) gave +0.8 %, runtron with 8 users on one engine gave +17 %.
#
# Words used here: tron = the inference program under test; rinzler = the production server;
# engine = one rinzler process; platformd = the production process manager (its API brings the
# production engines down and up); AMX = the Intel matrix instruction set the target build uses
# for CPU attention; TPS = tokens per second per user during decode; TTFT = time to first token;
# CI harness = the nightly's throughput benchmark (systems_test testlib/tps.py through
# exec/more-testing-r1/st_perf.py: prompt 1024 from the sharegpt set, generate 1536, 10 rounds,
# TPS captured between generated tokens 896 and 1024, users arriving 0.1 s apart).
#
# Cells: llama-3.1-8b-instruct-good-tp2 on OUR half (socket 1): 2 engines placed exactly like the
# nightly's instance-2/3 engines (rz.sh), one harness client per engine with U users each,
# U in LEVELS (2 = the nightly's load, 4, 8 = the runtron regime; 8 added by Claude as a third
# point, jhan approved 2 and 4), arms off (TRON_AMX_DISABLE=1) and on (unset), REPS repetitions.
# Arms alternate inside each repetition (odd reps off->on, even reps on->off) so a drift of the
# machine lands on both arms alike. USE_HW_ATTN is never set: with it unset tron keeps hardware
# attention off for this hand-written model, exactly as the nightly runs it (rinzler log 16:28 UTC:
# "HW attention disabled ... default off for this model").
# Binary: the ci-mimic TARGET deb's rinzler (2026.09.18-29a8a547, AMX + VNNI K compiled), the same
# file the target arm of the ci-mimic campaign served (sha256 3ee9c8f0...), extracted, not installed.
# Proof per cell: 20 s of the EXE.AMX_BUSY counter on both engine pids while the benchmark runs
# (amx_busy.txt), plus the engines' Version / placement / HW-attention lines (proof.txt).
#
# Machine handling: runs ON delphi-3bda (client pinned to socket-1 cores no engine uses). Waits for
# the CI lease and never runs inside the 01:40-03:45 UTC pre-CI hold. The 4 production engines
# left running by the ci-mimic restore (platformd, idle) are taken down through platformd's API
# only when the rinzler journal shows no request for 10 min (fail closed), and brought back up at
# the end (also on the abort path). Every cell takes the campaign guard (lease + flock + no runtron
# + serving down) and a 10-s watcher kills OUR processes if the lease turns busy or serving comes up.
# Bill's activity is not a reason to wait (our-half work); it is recorded per cell.
# Resume: relaunch; a cell whose STATUS says done is skipped. Never edit this file while it runs.
# Outputs: exec/results/l8bload-20260918/cells/<U>u__<arm>__rep<N>/{meta.json, perf.json (pooled),
# perf-e<k>.json/.log, rinzler-e<k>.log, amx_busy.txt, proof.txt, STATUS}, summary.md, summary.json;
# log exec/logs/l8bload-20260918.log; status exec/logs/l8bload-20260918.status; marker .done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/l8bload-20260918
H1=$EXEC/more-testing-r1
ST=/home/jhan/workspace/ai-runs/systems_test
PY=/var/tmp/jhan/st-venv/bin/python
RES=$EXEC/results/l8bload-20260918
LOG=$EXEC/logs/l8bload-20260918.log
MARKER=$EXEC/logs/l8bload-20260918.done
STATUS=$EXEC/logs/l8bload-20260918.status
export RZ_BIN=/var/tmp/jhan/ci-mimic-20260918/root/opt/positron/bin/rinzler
RZ_SHA_WANT=3ee9c8f059bc5282
MODEL=llama-3.1-8b-instruct-good-tp2
LEVELS=${LEVELS:-"2 4 8"}
REPS=${REPS:-3}
CLIENT_CPUS=87-95,231-239   # socket-1 cores no engine uses (engines: app 96-143 + 223-230, dev 75-78, launcher 73,74,217,218)
HARNESS_RE='st_perf[.]py .*results/l8bload-20260918'
BILL_UID=1062305141
PLATFORMD=http://localhost:8080
mkdir -p "$RES/cells" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
source "$C/rz.sh"
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
SERVING_TAKEN_DOWN=0

# ---------- stop rules ----------
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler@N unit active"; return 0; }
  return 1
}
wait_clear() {
  local why waited=0
  while why=$(blocked); do
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    sleep 120
  done
}
take_guard() {
  local waited=0
  until campaign_guard_acquire; do
    [ $waited = 0 ] && { status "waiting: campaign guard refused (see the GUARD line in the log)"; waited=1; }
    sleep 60; wait_clear
  done
}
kill_ours() {
  pkill -TERM -u jhan -f "$HARNESS_RE" 2>/dev/null
  pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null
}
watch_run() {  # background: stop our run within ~10 s when CI takes the lease or production serving comes up
  local sf=$1 why main=$$
  [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
  while :; do
    kill -0 "$main" 2>/dev/null || { kill_ours; sleep 10; pkill -KILL -u jhan -f "$OUR_RZ_RE" 2>/dev/null; exit 0; }
    why=""
    if ci_lease_busy; then why="CI lease busy"; elif rinzler_active; then why="rinzler@N unit active"; fi
    if [ -n "$why" ]; then [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"; kill_ours; fi
    sleep 10
  done
}
WPID=""
stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
machine_line() {
  local bill; bill=$(ps -u "$BILL_UID" -o pcpu= -o comm= 2>/dev/null | awk '{n++; c+=$1} END {printf "bill_procs=%d bill_cpu_pct=%.0f", n, c}')
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) $bill"
}

# ---------- production serving down / up through platformd ----------
serving_units_active() { systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active$'; }
serving_down() {  # 0 = production engines are down and their hugepages are free; fail closed on live use
  local j traffic busy conns n f try
  for try in $(seq 1 10); do   # up to 20 min of 2-min polls
    [ "$(serving_units_active)" = 0 ] && break
    j=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>&1) || { echo "$(ts) journalctl failed (${j:0:100}); not touching serving"; sleep 120; continue; }
    traffic=$(printf '%s\n' "$j" | grep -v '#EVT#' | grep -icE 'Parsing the prompt|response tokens|chat/completions|Request [0-9]+\]') || true
    busy=$(printf '%s\n' "$j" | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
    conns=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 or sport = :3000 or sport = :3001 or sport = :3002 or sport = :3003 or sport = :80 )' 2>/dev/null | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
    echo "$(ts) production engines active; last 10 min: request-lines=${traffic:-?} non-idle-stats=${busy:-?} remote-conns=${conns:-?}"
    if [ "${traffic:-1}" -eq 0 ] && [ "${busy:-1}" -eq 0 ] && [ "${conns:-1}" -eq 0 ]; then
      echo "$(ts) taking production serving down through platformd (idle for 10 min): $(curl -s -m 60 -X POST $PLATFORMD/api/inference/down | head -c 200)"
      SERVING_TAKEN_DOWN=1
      for _ in $(seq 1 24); do [ "$(serving_units_active)" = 0 ] && break; sleep 5; done
      break
    fi
    sleep 120
  done
  [ "$(serving_units_active)" = 0 ] || { echo "$(ts) production serving still active; not proceeding"; return 1; }
  sleep 5
  # positron's slice files stay allocated until unlinked. The units are inactive (synchronous stop), so
  # the owner decides: positron's files go, ours only when unmapped, anyone else's stay (Bill's live engine).
  for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/rinzler-*; do
    [ -e "$f" ] || continue
    if [ "$(stat -c %U "$f" 2>/dev/null)" = positron ]; then rm -f "$f" && echo "$(ts) removed $f (production engines down)"
    elif [ -O "$f" ]; then ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed $f (unmapped, ours)"
    else echo "$(ts) $f belongs to $(stat -c %U "$f" 2>/dev/null || echo '?'), left alone"
    fi
  done
  n=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo)
  echo "$(ts) HugePages_Free=$n after takedown"
  [ "$n" -ge 256 ] || { echo "$(ts) fewer than 256 free hugepages; our two engines need 256"; return 1; }
  return 0
}
serving_up() {  # bring the production engines back (what the ci-mimic restore left running)
  [ "$SERVING_TAKEN_DOWN" = 1 ] || return 0
  echo "$(ts) bringing production serving up through platformd: $(curl -s -m 60 -X POST $PLATFORMD/api/inference/up | head -c 200)"
  for _ in $(seq 1 60); do [ "$(serving_units_active)" = 4 ] && break; sleep 5; done
  echo "$(ts) production units active: $(serving_units_active) of 4; $(machine_line)"
  SERVING_TAKEN_DOWN=0
}

finish() {  # $1 = marker word; also the abort path (EXIT trap after an operator's kill)
  stop_watcher
  if [ "$1" = aborted ]; then
    trap '' TERM
    [ "$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')" = "$$" ] && kill -TERM -- -$$ 2>/dev/null
  fi
  kill_ours
  for _ in $(seq 1 60); do pgrep -u jhan -f "$HARNESS_RE" >/dev/null 2>&1 || break; sleep 1; done
  rz_stop_all 2>/dev/null
  campaign_guard_release 2>/dev/null
  python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
  serving_up
  echo "$1" >"$MARKER"
  status "finished: $1"
  echo "=== campaign finished $(ts): $1 ==="
}

# ---------- one cell ----------
amx_probe_bg() {  # $1 cell: 75 s into the benchmark, 20 s of EXE.AMX_BUSY on both engine pids (raw event 0xb7 umask 0x02)
  local cell=$1 pids
  [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
  sleep 75
  pids=$(printf '%s,' "${RZ_PIDS[@]}"); pids=${pids%,}
  { echo "pids=$pids start=$(ts)"; sudo -n perf stat -x, -e cpu/event=0xb7,umask=0x02,name=amx_busy/ -p "$pids" -- sleep 20 2>&1; } >"$cell/amx_busy.txt"
}
run_cell() {  # $1 users-per-engine  $2 arm  $3 rep
  local users=$1 arm=$2 rep=$3 cell t0 rc key port i ok p r ppid
  local -a pids=()
  cell=$RES/cells/${users}u__${arm}__rep${rep}
  [ "$(cat "$cell/STATUS" 2>/dev/null)" = done ] && { echo "$(ts) cell ${users}u $arm rep$rep already done"; return 0; }
  mkdir -p "$cell"
  if [ -e "$cell/STATUS" ]; then
    local prev="$cell/prev-$(date -u +%Y%m%dT%H%M%S)"; mkdir -p "$prev"
    for f in "$cell"/STATUS "$cell"/STOPPED "$cell"/meta.json "$cell"/perf.json "$cell"/perf-e* "$cell"/rinzler-e*.log "$cell"/proof.txt "$cell"/amx_busy.txt; do [ -e "$f" ] && mv -f "$f" "$prev/"; done
  fi
  wait_clear; take_guard
  status "cell ${users}u arm=$arm rep=$rep (2 engines x $users users)"
  echo running >"$cell/STATUS"; rm -f "$cell/STOPPED"
  local eng_json="" ; i=0
  for key in $ENGINE_KEYS; do
    eng_json="$eng_json$([ -n "$eng_json" ] && echo ,)"'{"index":'$i',"key":"'$key'","port":'$(engine_port "$key")',"users":'$users',"launcher_cores":"'$(engine_affinity "$key")'","placement":"'$(engine_sysargs "$key")'"}'
    i=$((i + 1))
  done
  python3 - "$cell/meta.json" "$MODEL" "$arm" "$users" "$rep" "$RZ_BIN" "[$eng_json]" "$(machine_line)" "$CLIENT_CPUS" <<'PY'
import json, sys, subprocess, datetime
p, model, arm, users, rep, binf, engines, machine, client_cpus = sys.argv[1:10]
sha = subprocess.run(['sha256sum', binf], capture_output=True, text=True).stdout.split()[0]
env = {"off": {"TRON_AMX_DISABLE": "1"}, "on": {"TRON_AMX_DISABLE": "(unset)"}}[arm]
env.update({"USE_HW_ATTN": "(unset: hardware attention default off for this model)", "TRON_USE_SPECULATION": "0", "SYSTEM_CONFIG": "(unset)", "RZ_FUSE_MOUNT_PRESCOPED": "1", "RZ_ENABLE_SAVE_TOKENS": "1"})
json.dump({"model": model, "arm": arm, "users_per_engine": int(users), "rep": int(rep), "binary": binf, "binary_sha256": sha,
           "binary_origin": "tron_2026.09.18-29a8a547-jhan-ci-mimic-target_amd64.deb (ci-mimic target: main 3faba6d0 + PR #4424 30c4ac82cb, deb preset with TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON)",
           "started": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), "engines": json.loads(engines), "machine": machine,
           "env": env, "client_cores": client_cpus,
           "harness": "systems_test testlib/tps.py via exec/more-testing-r1/st_perf.py --users <users per engine>: one client per engine at the same time, prompt 1024 (sharegpt), generate 1536, 10 rounds, capture 896-1024; perf.json pools every user of the cell",
           "phases": {}}, open(p, 'w'), indent=1)
PY
  watch_run "$cell/STOPPED" & WPID=$!
  t0=$(date +%s); ok=1; i=0
  for key in $ENGINE_KEYS; do rz_launch "$arm" "$key" "$cell/rinzler-e$i.log" "$MODEL" || ok=0; i=$((i + 1)); done
  if [ $ok = 1 ]; then for key in $ENGINE_KEYS; do rz_ready "$key" "$MODEL" || { ok=0; break; }; done; fi
  if [ $ok != 1 ]; then
    stop_watcher; rz_stop_all; campaign_guard_release
    if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"; echo "$(ts) cell ${users}u $arm rep$rep: start stopped: $(cat "$cell/STOPPED")"; return 2; fi
    echo start-failed >"$cell/STATUS"; echo "$(ts) cell ${users}u $arm rep$rep: engine start failed"; return 1
  fi
  python3 - "$cell/meta.json" start 0 $(( $(date +%s) - t0 )) <<'PY'
import json, sys
p, ph, rc, secs = sys.argv[1:5]; d = json.load(open(p)); d["phases"][ph] = {"rc": int(rc), "seconds": int(secs)}; json.dump(d, open(p, 'w'), indent=1)
PY
  t0=$(date +%s); i=0
  for key in $ENGINE_KEYS; do
    port=$(engine_port "$key"); mkdir -p "$cell/work-e$i"
    ( cd "$cell/work-e$i" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG PYTHONPATH="$H1/talos_stub:$ST" OPENAI_HOST=http://delphi-3bda:$port/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
        HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false timeout 3000 taskset -c "$CLIENT_CPUS" "$PY" "$H1/st_perf.py" --model "$MODEL" --users "$users" --out "$cell/perf-e$i.json" >"$cell/perf-e$i.log" 2>&1 ) &
    pids+=($!)
    i=$((i + 1))
  done
  amx_probe_bg "$cell" & ppid=$!
  rc=0
  local -a done_flags=()
  for p in "${pids[@]}"; do done_flags+=(0); done
  while :; do
    local alive=0
    for i in "${!pids[@]}"; do
      [ "${done_flags[$i]}" = 1 ] && continue
      if kill -0 "${pids[$i]}" 2>/dev/null; then alive=1; continue; fi
      wait "${pids[$i]}"; r=$?; done_flags[$i]=1
      if [ $r -ne 0 ] && [ $rc -eq 0 ]; then
        rc=$r; echo "$(ts) cell ${users}u $arm rep$rep: client $i exited rc=$r; stopping the other client"
        pkill -TERM -u jhan -f "st_perf[.]py .*${cell}/perf-e" 2>/dev/null
      fi
    done
    [ $alive = 1 ] || break
    sleep 2
  done
  wait "$ppid" 2>/dev/null
  stop_watcher
  {
    i=0
    for key in $ENGINE_KEYS; do
      echo "== engine $i ($key, port $(engine_port "$key"))"
      grep -E "Version:|Configured instance|App CPU list|HW attention" "$cell/rinzler-e$i.log" | head -6
      grep 'KV cache footprint' "$cell/rinzler-e$i.log" | tail -1
      i=$((i + 1))
    done
    echo "== amx_busy"; cat "$cell/amx_busy.txt" 2>/dev/null
  } >"$cell/proof.txt" 2>/dev/null
  rz_stop_all
  campaign_guard_release
  python3 - "$cell/meta.json" perf "$rc" $(( $(date +%s) - t0 )) <<'PY'
import json, sys, datetime
p, ph, rc, secs = sys.argv[1:5]; d = json.load(open(p)); d["phases"][ph] = {"rc": int(rc), "seconds": int(secs)}
d["ended"] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'); json.dump(d, open(p, 'w'), indent=1)
PY
  python3 "$EXEC/p0perf-20260913/combine.py" "$cell" 2 || echo "$(ts) cell ${users}u $arm rep$rep: combine failed"
  if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"
  elif [ $rc -eq 0 ] && [ -s "$cell/perf.json" ]; then echo done >"$cell/STATUS"
  else echo failed >"$cell/STATUS"; fi
  echo "$(ts) cell ${users}u $arm rep$rep rc=$rc status=$(cat "$cell/STATUS") $(cat "$cell/STOPPED" 2>/dev/null) amx=$(grep amx_busy "$cell/amx_busy.txt" 2>/dev/null | cut -d, -f1) $(for f in "$cell"/perf-e*.log; do tail -1 "$f" 2>/dev/null | cut -c1-120; done | tr '\n' ' ')"
  case $(cat "$cell/STATUS") in done) return 0 ;; stopped) return 2 ;; *) return 1 ;; esac
}

[ "${L8B_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
instck=$(mktemp /tmp/l8bload-instck.XXXXXX)
pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/l8bload-20260918/campaign[.]sh$' >"$instck"
others=$(grep -vx "$$" "$instck" | tr '\n' ' '); rm -f "$instck"
if [ -n "$others" ]; then echo "$(ts) another campaign.sh instance is running (pids $others); this one exits"; exit 1; fi
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== l8bload-20260918 campaign started $(ts) pid $$ MODEL=$MODEL LEVELS=[$LEVELS] REPS=$REPS ==="
[ -x "$RZ_BIN" ] || { status "ABORT: binary missing $RZ_BIN"; finish binary-missing; exit 1; }
have=$(sha256sum "$RZ_BIN" | cut -c1-16)
[ "$have" = "$RZ_SHA_WANT" ] || { status "ABORT: binary sha $have, wanted $RZ_SHA_WANT"; finish binary-mismatch; exit 1; }
echo "$(ts) binary $RZ_BIN sha256 $have (= the ci-mimic target deb's rinzler)"
kill_ours; sleep 3; rz_stop_all
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"

# phase 0: lease clear, then production serving down (under the bare campaign flock)
status "phase 0: waiting for the CI lease, then taking idle production serving down"
while preci_hold || ci_lease_busy; do sleep 60; done
exec {CAMPAIGN_LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$CAMPAIGN_LOCK_FD"; do echo "$(ts) campaign flock held by another script; waiting"; sleep 30; done
serving_down || { campaign_guard_release; finish serving-not-down; exit 1; }
campaign_guard_release
echo "$(ts) $(machine_line)"

# phase 1: cells
fail=0
for rep in $(seq 1 "$REPS"); do
  if [ $((rep % 2)) -eq 1 ]; then arms="off on"; else arms="on off"; fi
  for users in $LEVELS; do
    for arm in $arms; do
      for try in 1 2 3; do
        run_cell "$users" "$arm" "$rep"; rc=$?
        [ $rc -eq 2 ] && [ $try -lt 3 ] && { echo "$(ts) cell ${users}u $arm rep$rep stopped; retry $((try + 1)) after the machine is clear"; sleep 120; continue; }
        break
      done
      [ $rc -eq 0 ] || fail=$((fail + 1))
    done
  done
  echo "$(ts) repetition $rep done, failed cells so far: $fail"
done

# phase 2: summary, then production serving back up
status "phase 2: summary"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md" || { echo "summarize.py failed:"; cat "$RES/summary.err"; }
if [ $fail -eq 0 ]; then finish ok; else finish "check-output (failed cells $fail)"; fi
exit 0
