#!/usr/bin/env bash
# p0perf-20260911: AMX perf test after the nightly CI on delphi-3bda, OUR half of the machine
# (jhan, 2026-09-11 06:2x UTC: "Run AMX perf test after CI ... use the latest branch jhan-amx-p0").
#
# Words used here: tron = the inference program under test; runtron = its command-line tool;
# rinzler = the production server binary; AMX = the Intel matrix instruction set the branch
# uses for CPU attention; AMX-off = the AMX build run with TRON_AMX_DISABLE=1 (the kill
# switch); AMX-on = the same binary with the variable unset; TPS = tokens per second per
# user during decode; TTFT = time to first token (prefill latency); "CI setup" = the nightly
# System CI's perf harness (positron-ai/systems_test, testlib/tps.py through
# exec/more-testing-r1/st_perf.py: 8 users, prompt 1024, generate 1536, 10 rounds, TPS
# captured between generated tokens 896 and 1024) driven against ONE rinzler engine built
# from the branch, as round 1 did (exec/more-testing-r1). The nightly itself runs the same
# harness through the platformd proxy over 4 tp2 / 2 tp4 engines of the apt-installed tron
# with FPGA attention, so its numbers are not comparable to these.
#
# Cells (all qwen-3-4b, 8 users, prompt 1024):
#   runtron: tp2 off, tp2 on, tp4 off, tp4 on          x RT_REPS (default 3), 256 generated
#   CI:      tp2 off, tp2 on, tp4 off, tp4 on          x CI_REPS (default 2)
# Arms are interleaved inside each repetition (off then on) so a slow drift of the machine
# lands on both arms alike.
#
# Placement: our half only (half-split with Bill since 2026-09-06): socket 1, cards
# 90/93/b9/bc; see half_sysargs in rz.sh. `env -u SYSTEM_CONFIG` on every tron process
# (the login environment exports "--instance 1,2", which tron applies AFTER the command
# line). USE_HW_ATTN=0 in every arm (CPU attention; AMX can only engage there).
#
# Order of events: wait for the CI lease to be clear for 3 polls in a row (and never inside
# the 01:40-03:45 UTC pre-CI hold) -> build runtron + rinzler from TIP in a fresh worktree on
# socket 1 (nice, taskset) -> idle-serving takeover (round 1 / G1 recipe: stop rinzler@0-3
# only when the journal shows no client activity for 10 min, fail closed) -> runtron cells
# -> CI cells -> summary. Every run takes the campaign guard (lease + flock + no other
# runtron + serving down) and is watched by a 10-second watcher that kills OUR processes
# (matched by absolute binary path) if the lease turns busy or serving comes up. Bill's
# activity is not a reason to wait (our-half work); it is recorded per cell instead.
#
# Resume: relaunch the script; a runtron run whose log already has "average tok/s" and a CI
# cell whose STATUS says done are skipped. Never edit this file while it runs (bash reads
# it incrementally from NFS).
#
# Outputs: exec/results/p0perf-20260911/{build.txt, rt-results.txt, rt/<log per run>,
# cells/<model>__<arm>__rep<N>/{meta.json,perf.json,perf.log,rinzler.log,proof.txt,STATUS},
# summary.json, summary.md}; log exec/logs/p0perf-20260911.log; status line
# exec/logs/p0perf-20260911.status; marker exec/logs/p0perf-20260911.done (ok | aborted | ...).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/p0perf-20260911
H1=$EXEC/more-testing-r1
ST=/home/jhan/workspace/ai-runs/systems_test
PY=/var/tmp/jhan/st-venv/bin/python
RES=$EXEC/results/p0perf-20260911
LOG=$EXEC/logs/p0perf-20260911.log
MARKER=$EXEC/logs/p0perf-20260911.done
STATUS=$EXEC/logs/p0perf-20260911.status
PORT=13100
WT=/var/tmp/jhan/tron-p0perf
TIP=${P0PERF_TIP:-47f6f2dcebfa69d3c0b2d94096c8ce9bf3718511}   # jhan-amx-p0 head, 2026-09-11 03:31 UTC
RT=$WT/gen/runtron.p0perf
export RZ_BIN=$WT/gen/rinzler.p0perf
OUR_CPUS=72-143,216-287
OUR_RT_RE='^/var/tmp/jhan/tron-p0perf/gen/runtron[.]p0perf '   # our runtron by absolute path
RT_REPS=${RT_REPS:-3}; CI_REPS=${CI_REPS:-2}
QWEN2=ingested-qwen-3-4b-instruct-2507-tp2
QWEN4=ingested-qwen-3-4b-instruct-2507-tp4
BILL_UID=1062305141
mkdir -p "$RES/cells" "$RES/rt" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"   # our-half work: Bill's activity is not a reason to wait
source "$C/rz.sh"
NIX=$(command -v nix || echo /home/jhan/.nix-profile/bin/nix)
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }

# ---------- stop rules ----------
preci_hold() {  # 01:40-03:45 UTC: production comes up at 02:45, the nightly takes the lease ~03:38
  local hm; hm=$((10#$(date -u +%H%M)))
  [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]
}
blocked() {     # 0 = must not run now, prints why
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler@N unit active"; return 0; }
  return 1
}
wait_clear() {  # waits (2-min polls) until not blocked
  local why waited=0
  while why=$(blocked); do
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    sleep 120
  done
  return 0
}
wait_lease_clear_3() {  # the lease must read "not busy" on 3 polls 60 s apart (a heartbeat gap must not start us)
  local n=0
  while :; do
    if preci_hold || ci_lease_busy; then n=0; else n=$((n + 1)); [ "$n" -ge 3 ] && return 0; fi
    sleep 60
  done
}
take_guard() {  # campaign_guard_acquire with retries; the guard refuses next to serving, another runtron or the flock
  local waited=0
  until campaign_guard_acquire; do
    [ $waited = 0 ] && { status "waiting: campaign guard refused (see the GUARD line in the log)"; waited=1; }
    sleep 60; wait_clear
  done
}
kill_ours() {   # only this campaign's processes: tron binaries by absolute path, the harness by result path
  pkill -TERM -u jhan -f "st_perf[.]py .*results/p0perf-20260911" 2>/dev/null
  pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null
  pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null
}
watch_run() {   # background: stop our run within ~10 s when CI takes the lease or serving comes up
  local sf=$1 why main=$$   # $$ inside the backgrounded function is the main shell's pid
  [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-   # the subshell must not keep the campaign flock alive after a kill -9 of the main shell
  while :; do
    # main shell gone (kill -9, OOM): stop our run, remove our slice files, leave (review 2026-09-11, C5/C10)
    kill -0 "$main" 2>/dev/null || { kill_ours; sleep 10; pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null; pkill -KILL -u jhan -f "$OUR_RZ_RE" 2>/dev/null; sleep 2; remove_our_slice_files; exit 0; }
    why=""
    if ci_lease_busy; then why="CI lease busy"
    elif rinzler_active; then why="rinzler@N unit active"
    fi
    # no return: keep killing every 10 s (a single kill can land before the binary is exec'd)
    if [ -n "$why" ]; then [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"; kill_ours; fi
    sleep 10
  done
}
WPID=""
stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
finish() {  # $1 = marker word; also the abort path (EXIT trap after an operator's kill): stop OUR processes first
  stop_watcher
  if [ "$1" = aborted ]; then
    # bash runs the EXIT trap on SIGTERM but leaves the foreground child alive. The process group ($$ is its leader
    # under launch.sh's setsid) reaches the build chain (nice -> taskset -> nix -> cmake); `timeout` puts runtron and
    # the harness in their own groups, so kill_ours (absolute paths) covers those.
    trap '' TERM
    [ "$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')" = "$$" ] && kill -TERM -- -$$ 2>/dev/null   # only when we lead the group (launch.sh's setsid)
  fi
  kill_ours   # no-op at a normal end; after an external kill it stops the orphaned runtron / harness / rinzler
  for _ in $(seq 1 60); do   # wait until our runtron and harness are gone: a still-mapped slice file is never removed
    pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || pgrep -u jhan -f "st_perf[.]py .*results/p0perf-20260911" >/dev/null 2>&1 || break
    sleep 1
  done
  pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null && { echo "$(ts) finish: SIGKILL to our runtron"; sleep 2; }
  rz_stop 2>/dev/null
  remove_our_slice_files
  campaign_guard_release 2>/dev/null
  [ "$1" = ok ] || python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true   # partial summary on every other path
  echo "$1" >"$MARKER"
  status "finished: $1"
  echo "=== campaign finished $(ts): $1 ==="
}
machine_line() {  # one line of context per run: load, free hugepages, Bill's processes (count, summed %CPU)
  local bill; bill=$(ps -u "$BILL_UID" -o pcpu= -o comm= 2>/dev/null | awk '{n++; c+=$1} END {printf "bill_procs=%d bill_cpu_pct=%.0f", n, c}')
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) $bill"
}
remove_our_slice_files() {  # with --instance the hugepage files are /dev/hugepages/slice-<k>-of-8; runtron keeps them at exit
  local f
  for f in /dev/hugepages/slice-*-of-8; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage slice file $f (unmapped, ours)"
  done
}

# ---------- phase 1: build ----------
build() {  # 0 = both binaries present for TIP
  if [ -x "$RT" ] && [ -x "$RZ_BIN" ] && [ -e "$WT/gen/.p0perf-built" ] && [ "$(git -C "$WT" rev-parse HEAD 2>/dev/null)" = "$TIP" ]; then
    echo "$(ts) $WT already built for $TIP"; return 0
  fi
  ( cd /home/jhan/workspace/tron-amx && { [ -d "$WT" ] || git worktree add --detach "$WT" "$TIP"; } ) || { echo "$(ts) worktree add failed for $WT"; return 1; }
  cd "$WT" || return 1
  [ "$(git rev-parse HEAD)" = "$TIP" ] || git checkout -q --detach "$TIP" || { echo "$(ts) checkout $TIP failed"; cd "$EXEC"; return 1; }
  rm -f gen/.p0perf-built
  local t0 rc; t0=$(date +%s)
  nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c \
    "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS= 2>&1 | tail -3 &&
     cmake --build gen --target runtron rinzler -j96 2>&1 | grep -E 'error|FAILED' | sed -n 1,40p; exit \${PIPESTATUS[0]}"
  rc=$?
  echo "$(ts) build $WT DISPATCH=ON targets=[runtron rinzler] rc=$rc in $(( $(date +%s) - t0 )) s"
  if [ $rc -ne 0 ]; then echo "$(ts) BUILD FAILED"; cd "$EXEC"; return 1; fi
  for b in runtron rinzler; do
    strings "gen/$b" | grep -q 'ingested-qwen-3-4b-instruct-2507' || { echo "$(ts) qwen plugin MISSING in gen/$b"; cd "$EXEC"; return 1; }
  done
  cp gen/runtron gen/runtron.p0perf && cp gen/rinzler gen/rinzler.p0perf || { cd "$EXEC"; return 1; }
  {
    echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
    echo "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS= ; targets runtron rinzler; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS"
    sha256sum gen/runtron.p0perf gen/rinzler.p0perf
    ./gen/runtron.p0perf --version 2>&1 | head -2
  } >"$RES/build.txt"
  touch gen/.p0perf-built
  cd "$EXEC"
  return 0
}

# ---------- phase 2: runtron cells ----------
run_rt() {  # $1 tp  $2 arm  $3 rep
  local tp=$1 arm=$2 rep=$3 model rlog attempt stops=0 rc res envv=""
  case $tp in 2) model=$QWEN2 ;; 4) model=$QWEN4 ;; esac
  [ "$arm" = off ] && envv="TRON_AMX_DISABLE=1"
  rlog=$RES/rt/tp${tp}__${arm}__rep${rep}.log
  if grep -q "average tok/s" "$rlog" 2>/dev/null; then echo "$(ts) runtron tp$tp $arm rep$rep already done"; return 0; fi
  attempt=$(ls "$rlog".attempt* 2>/dev/null | wc -l)   # continue the numbering across relaunches; attempt logs are never overwritten
  while :; do
    attempt=$((attempt + 1))
    wait_clear; take_guard
    status "phase 2: runtron tp$tp arm=$arm rep=$rep attempt=$attempt"
    echo "### runtron tp=$tp arm=$arm rep=$rep attempt=$attempt env=${envv:-TRON_AMX_DISABLE unset} prompt=1024 len=256 users=8 $(ts) $(machine_line)" >>"$RES/rt-results.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    # the whole output goes to the log; the result lines are grepped from it afterwards. -o = optimize (as usual).
    (cd "$WT" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug ${envv:+$envv} \
        timeout 900 "$RT" stream-generate-text -m "$model" $(half_sysargs "$tp") --hugepage_file /dev/hugepages/amx-p0perf -o \
        --prompt-length 1024 -l 256 -u 8) >"$rlog.attempt$attempt" 2>&1
    rc=$?
    stop_watcher
    campaign_guard_release
    remove_our_slice_files
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s" "$rlog.attempt$attempt" 2>/dev/null)
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ]; then
      echo "RUN-STOPPED rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null) (full output: $rlog.attempt$attempt)" >>"$RES/rt-results.txt"
      stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "RUN-GIVEN-UP after 3 stops" >>"$RES/rt-results.txt"; return 1; }
      sleep 120; continue
    fi
    if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res"; then
      { echo "RUN-FAILED rc=$rc (full output: $rlog.attempt$attempt)"; echo "$res"; } >>"$RES/rt-results.txt"; return 1
    fi
    cp "$rlog.attempt$attempt" "$rlog"
    echo "$res" >>"$RES/rt-results.txt"
    return 0
  done
}

# ---------- phase 3: CI-harness cells ----------
run_ci() {  # $1 tp  $2 arm  $3 rep
  local tp=$1 arm=$2 rep=$3 model cell t0 rc
  case $tp in 2) model=$QWEN2 ;; 4) model=$QWEN4 ;; esac
  cell=$RES/cells/${model}__${arm}__rep${rep}
  [ "$(cat "$cell/STATUS" 2>/dev/null)" = done ] && { echo "$(ts) CI cell $model $arm rep$rep already done"; return 0; }
  mkdir -p "$cell/work"
  if [ -e "$cell/STATUS" ]; then   # an earlier attempt (stopped / failed / killed invocation): keep its files for diagnosis
    local prev="$cell/prev-$(date -u +%Y%m%dT%H%M%S)"; mkdir -p "$prev"
    for f in STATUS STOPPED meta.json perf.json perf.log rinzler.log proof.txt; do [ -e "$cell/$f" ] && mv -f "$cell/$f" "$prev/"; done
    echo "$(ts) CI cell $model $arm rep$rep: earlier attempt moved to $prev"
  fi
  wait_clear; take_guard
  status "phase 3: CI harness $model arm=$arm rep=$rep"
  echo running >"$cell/STATUS"; rm -f "$cell/STOPPED"
  python3 - "$cell/meta.json" "$model" "$arm" "$tp" "$rep" "$RZ_BIN" "$WT" "$(half_sysargs "$tp")" "$(machine_line)" <<'PY'
import json, sys, subprocess, datetime
p, model, arm, tp, rep, binf, wt, place, machine = sys.argv[1:10]
sha = subprocess.run(['sha256sum', binf], capture_output=True, text=True).stdout.split()[0]
head = subprocess.run(['git', '-C', wt, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
json.dump({"model": model, "arm": arm, "tp": int(tp), "rep": int(rep), "binary": binf, "binary_sha256": sha, "tron_head": head,
           "started": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), "port": 13100, "placement": place, "machine": machine,
           "env": {"USE_HW_ATTN": "0", "TRON_AMX_DISABLE": "1" if arm == 'off' else "(unset)", "TRON_USE_SPECULATION": "0", "SYSTEM_CONFIG": "(unset)"},
           "harness": "systems_test 470aca1 testlib/tps.py via exec/more-testing-r1/st_perf.py: 8 users, prompt 1024 (sharegpt), generate 1536, 10 rounds, capture 896-1024",
           "phases": {}}, open(p, 'w'), indent=1)
PY
  watch_run "$cell/STOPPED" & WPID=$!
  t0=$(date +%s)
  if ! rz_start "$arm" "$PORT" "$tp" "$cell/rinzler.log" "$model"; then
    stop_watcher; rz_stop; campaign_guard_release
    if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"; echo "$(ts) CI cell $model $arm rep$rep: start stopped: $(cat "$cell/STOPPED")"; return 2; fi
    echo start-failed >"$cell/STATUS"; echo "$(ts) CI cell $model $arm rep$rep: rinzler start failed"; return 1
  fi
  python3 - "$cell/meta.json" start 0 $(( $(date +%s) - t0 )) <<'PY'
import json, sys
p, ph, rc, secs = sys.argv[1:5]; d = json.load(open(p)); d["phases"][ph] = {"rc": int(rc), "seconds": int(secs)}; json.dump(d, open(p, 'w'), indent=1)
PY
  t0=$(date +%s)
  ( cd "$cell/work" && env -u SYSTEM_CONFIG PYTHONPATH="$H1/talos_stub:$ST" OPENAI_HOST=http://delphi-3bda:$PORT/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
      HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false timeout 3000 "$PY" "$H1/st_perf.py" --model "$model" --out "$cell/perf.json" >"$cell/perf.log" 2>&1 )
  rc=$?
  stop_watcher
  rz_stop
  campaign_guard_release
  python3 - "$cell/meta.json" perf "$rc" $(( $(date +%s) - t0 )) <<'PY'
import json, sys, datetime
p, ph, rc, secs = sys.argv[1:5]; d = json.load(open(p)); d["phases"][ph] = {"rc": int(rc), "seconds": int(secs)}
d["ended"] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'); json.dump(d, open(p, 'w'), indent=1)
PY
  { grep -E "Version:|Configured instance|App CPU list|HW attention" "$cell/rinzler.log" | head -6; grep 'KV cache footprint' "$cell/rinzler.log" | tail -1; } >"$cell/proof.txt" 2>/dev/null
  if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"
  elif [ $rc -eq 0 ] && [ -s "$cell/perf.json" ]; then echo done >"$cell/STATUS"
  else echo failed >"$cell/STATUS"; fi
  echo "$(ts) CI cell $model $arm rep$rep rc=$rc status=$(cat "$cell/STATUS") $(cat "$cell/STOPPED" 2>/dev/null) $(tail -1 "$cell/perf.log" 2>/dev/null | cut -c1-160)"
  case $(cat "$cell/STATUS") in done) return 0 ;; stopped) return 2 ;; *) return 1 ;; esac
}

[ "${P0PERF_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }   # test harnesses source the functions and stop here

# ======================= main flow =======================
exec >>"$LOG" 2>&1
# Self-match trap (11:32Z): a $(...) subshell and the not-yet-exec'd members of a pipeline are forks of this bash with the
# same command line, so a pgrep inside them finds them. Run pgrep directly from the main shell into a file instead.
instck=$(mktemp /tmp/p0perf-instck.XXXXXX)
pgrep -f 'p0perf-20260911/campaign[.]sh' >"$instck"
others=$(grep -vx "$$" "$instck" | tr '\n' ' '); rm -f "$instck"
if [ -n "$others" ]; then echo "$(ts) another campaign.sh instance is running (pids $others); this one exits"; exit 1; fi
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== p0perf-20260911 campaign started $(ts) pid $$ TIP=$TIP RT_REPS=$RT_REPS CI_REPS=$CI_REPS ==="
# leftovers of a previous invocation that was killed (kill -9): our rinzler on port 13100 (it would hold the inherited
# campaign flock and the port), our runtron, our unmapped slice files. Matched by absolute path only.
kill_ours; sleep 3; rz_stop; remove_our_slice_files
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"

# phase 1: build after the lease is clear (a 96-job build must never run under the nightly), on socket 1.
status "phase 1: waiting for the CI lease to be clear (3 polls), then building from $TIP on socket 1"
wait_lease_clear_3
echo "$(ts) CI lease clear (3 polls); $(machine_line)"
# the bare campaign flock during the build serializes with any other chain of ours; not the full guard, which
# refuses while serving is up (irrelevant to a socket-1 build)
exec {CAMPAIGN_LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$CAMPAIGN_LOCK_FD"; do echo "$(ts) campaign flock held by another script; build waits"; sleep 30; done
build || { campaign_guard_release; finish build-failed; exit 1; }
campaign_guard_release
cat "$RES/build.txt"

# phase 0: idle-serving takeover (round 1 / G1 recipe, fail closed). The 02:45 UTC timer brings rinzler@0-3 up
# and the nightly uses them; when they stay up afterwards with no client activity for 10 minutes, stop them so
# the hugepages and the FPGA cards are free (standing policy; nothing restarts them).
wait_lease_clear_3
status "phase 0: checking idle production serving"
for _ in $(seq 1 40); do   # up to ~80 min of 2-min polls
  ci_lease_busy && break
  rinzler_active || break
  j=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>&1) || { echo "$(ts) journalctl failed (${j:0:100}); not touching serving"; sleep 120; continue; }
  [ -n "$j" ] || { echo "$(ts) journal empty for the last 10 min; not touching serving"; sleep 120; continue; }
  traffic=$(printf '%s\n' "$j" | grep -v '#EVT#' | grep -icE 'session|request|prompt|generat|token') || true
  busy=$(printf '%s\n' "$j" | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
  probe=$(sudo -n journalctl -u 'rinzler@*' -n 1 -o cat --no-pager 2>/dev/null) || true   # readability probe, fail closed
  conns=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 or sport = :3000 or sport = :3001 or sport = :3002 or sport = :3003 )' 2>/dev/null | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  echo "$(ts) rinzler units active; journal-request-lines=${traffic:-?} non-idle-stats-lines=${busy:-?} journal-readable=$([ -n "$probe" ] && echo yes || echo no) remote-conns=${conns:-?}"
  if [ -n "$probe" ] && [ "${traffic:-1}" -eq 0 ] && [ "${busy:-1}" -eq 0 ] && [ "${conns:-1}" -eq 0 ]; then
    echo "$(ts) stopping idle rinzler serving per the standing policy (round 1 recipe)"
    if sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3; then
      sleep 5
      # positron's slice files are unmapped now (systemctl stop is synchronous); fuser cannot show that, since
      # another user's /proc/<pid>/maps is unreadable, so the owner decides. Own files: owner + fuser test.
      # Any other owner (Bill's live engine) is left alone.
      for f in /dev/hugepages/slice-*-of-8; do
        [ -e "$f" ] || continue
        if [ "$(stat -c %U "$f" 2>/dev/null)" = positron ]; then rm -f "$f" && echo "$(ts) removed $f (rinzler@N stopped)"
        elif [ -O "$f" ]; then ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed $f (unmapped, ours)"
        else echo "$(ts) $f belongs to $(stat -c %U "$f" 2>/dev/null || echo '?'), left alone"
        fi
      done
    else
      echo "$(ts) systemctl stop returned nonzero; slice files left alone"
    fi
    break
  fi
  sleep 120
done
grep -E '^HugePages_(Total|Free):' /proc/meminfo | xargs
rinzler_active && { echo "$(ts) TAKEOVER NOT DONE: rinzler@N still active after the polls; the runs wait for serving to stop"; status "phase 0: serving still active after the takeover polls; waiting"; }
echo "$(ts) plan: phase 2 runtron 4 cells x $RT_REPS reps (about 2 min each), phase 3 CI harness 4 cells x $CI_REPS reps (about 6 min each)"

# phase 2: runtron cells, interleaved arms inside each repetition
echo "# p0perf-20260911 runtron results: qwen-3-4b tp2 and tp4, 8 users, prompt 1024, 256 generated; tip $TIP; host $(hostname); started $(ts)" >>"$RES/rt-results.txt"
echo "# placement tp2: $(half_sysargs 2)" >>"$RES/rt-results.txt"
echo "# placement tp4: $(half_sysargs 4)" >>"$RES/rt-results.txt"
echo "# arms: off = TRON_AMX_DISABLE=1 (kill switch), on = variable unset; USE_HW_ATTN=0 in both; env -u SYSTEM_CONFIG; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug" >>"$RES/rt-results.txt"
sha256sum "$RT" >>"$RES/rt-results.txt"
rt_fail=0
for rep in $(seq 1 "$RT_REPS"); do
  for tp in 2 4; do
    for arm in off on; do
      run_rt "$tp" "$arm" "$rep" || rt_fail=$((rt_fail + 1))
    done
  done
done
echo "$(ts) phase 2 done, failed runs: $rt_fail"

# phase 3: CI-harness cells, interleaved arms inside each repetition
ci_fail=0
for rep in $(seq 1 "$CI_REPS"); do
  for tp in 2 4; do
    for arm in off on; do
      for try in 1 2 3; do
        run_ci "$tp" "$arm" "$rep"; rc=$?
        [ $rc -eq 2 ] && [ $try -lt 3 ] && { echo "$(ts) CI cell tp$tp $arm rep$rep stopped; retry $((try + 1)) after the machine is clear"; sleep 120; continue; }
        break
      done
      [ $rc -eq 0 ] || ci_fail=$((ci_fail + 1))
    done
  done
done
echo "$(ts) phase 3 done, failed cells: $ci_fail"

# phase 4: summary
status "phase 4: summary"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md" || { echo "summarize.py failed:"; cat "$RES/summary.err"; }
remove_our_slice_files
if [ $rt_fail -eq 0 ] && [ $ci_fail -eq 0 ]; then finish ok; else finish "check-output (runtron failures $rt_fail, CI failures $ci_fail)"; fi
exit 0
