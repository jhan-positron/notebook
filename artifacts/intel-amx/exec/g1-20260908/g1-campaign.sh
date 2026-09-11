#!/usr/bin/env bash
# G1 store-cost campaign on delphi-3bda, Tuesday 2026-09-08 (whole machine). Version 3
# (08:3x UTC): version 1 -> 23-agent review -> version 2 -> 22-agent delta review -> this
# (earlier versions kept as g1-campaign.sh.v1-20260908 / .v2-20260908).
#
# Words used here: TTFT = time to first token (prefill latency as the serving client
# sees it); canonical = the AMX kernel reads K as stored (PR 1); mirror = PR 2's second
# VNNI-layout copy of K in ordinary RAM; the probe binary rinzler.g1 / runtron.g1 = head
# 60d66d9c04 (round 1's head) plus commit fceeddc529 (branch jhan-dd-g1-store), whose
# environment variable TRON_DD_G1 selects the K store pattern: unset = mirror arm,
# "sonly" = scatter-only store into the arena (no canonical store), "inplace" = scatter
# into the page's own K plane (single-K storage proxy). runtron.g1canon = the same head
# built with TRON_AMX_K_MIRROR=OFF (same-head canonical reference for the runtron point).
# Numerics are wrong in the two probe modes; only timing is meaningful. Gate G1
# (breakup-PR3879.html section 5.2): kill single-K if the scatter-only store makes prefill
# or TTFT worse than canonical by more than the run-to-run spread (about 2%) at 8
# concurrent prefills. Not measured here: the gate's second kill criterion (save_k RX-worker
# time per row, kill if more than 2x today's 70 ns); G1 cannot be closed from this campaign
# alone.
#
# Order (jhan, 2026-09-08 06:xx UTC): start only after the nightly CI lease has cleared
# AND the other session's PR 0b chain (verify x2 + cost-data bench) has finished AND Bill
# is absent (the monitor exec/bill-watch.sh says CLEAR). Stop whatever is running when
# Bill returns (own 10-second watcher; the monitor's rinzler kill matches only a binary
# named exactly "rinzler").
#
# Phases: 1 build the probe binaries (socket 1 only, needs neither Bill absent nor the
# guard, so it runs BEFORE the whole-machine window) -> 0 waits (idle-serving takeover per
# round 1's recipe, PR 0b chain done, Bill gone, campaign guard) -> 2 the gate cells: 8
# users, qwen tp4 then llama tp2 -> 3 runtron qwen 8 users prompt 8192, 5 arms x 2 reps ->
# 4 1- and 4-user cells (mechanism), qwen then llama -> 5 2-user cells -> 6 canonical soak
# 60 min (filler). Each perf run = round 1's harness (st_perf.py: 10 rounds, prompt ~1000,
# generate 1536) at N users on round 1's placement (socket 0, cards 38/3b/10/13) so TTFT
# values extend round 1's table.
#
# Outputs: exec/results/g1-20260908/{cells/<model>__<arm>__u<N>/, runtron-8u8k.txt,
# soak__canon60/, summary.txt, summary.md}; log exec/logs/g1-20260908.log; status line
# exec/logs/g1-20260908.status; marker exec/logs/g1-20260908.done.
# Rules honoured: no new run between 01:30 and 11:00 UTC (before the campaign has started
# that window is a hold, not an abort); `env -u SYSTEM_CONFIG` on every tron process; the
# campaign flock is released while waiting for Bill and taken back before each run; kills
# match only this campaign's own processes (binary paths / result paths); never edit this
# file while it runs (bash reads it incrementally from NFS); a cell whose STATUS file says
# "done" is skipped, so a phase can be dropped from outside by writing that word.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
G=$EXEC/g1-20260908
H1=$EXEC/more-testing-r1
ST=/home/jhan/workspace/ai-runs/systems_test
PY=/var/tmp/jhan/st-venv/bin/python
RES=$EXEC/results/g1-20260908
LOG=$EXEC/logs/g1-20260908.log
MARKER=$EXEC/logs/g1-20260908.done
STATUS=$EXEC/logs/g1-20260908.status
PORT=13100
G1WT=/var/tmp/jhan/tron-g1
G1CWT=/var/tmp/jhan/tron-g1canon
G1SHA=${G1SHA:-fceeddc529}
export G1BIN=$G1WT/gen/rinzler.g1
G1RT=$G1WT/gen/runtron.g1
G1CRT=$G1CWT/gen/runtron.g1canon
FLAG=/var/tmp/jhan/bill-active.flag; STATE=/var/tmp/jhan/bill-watch.state
BILL_UID=1062305141
BILL_WORK_RE='eoe_engine|runtron|rinzler|gen/'
# bash 5.1 execs the LAST command of a -c list in place, so once the other session's chain
# reaches its bench step the wrapper's cmdline is "bash .../split-bench3.sh PR0b-test ...".
# Match every step by its own script name (the campaign's own cmdline contains neither).
PR0B_RE='^bash (-c KEEP_WT=1 )?[^ ]*split-(verify3|bench3)[.]sh PR0b-test'   # the wrapper's -c string, the verify child, the exec'd bench
PR0B_MARKER=$EXEC/logs/split-PR0b-test.bench-done
OUR_CPUS=72-143,216-287
OUR_RT_RE='^/var/tmp/jhan/tron-g1(canon)?/gen/runtron[.]'      # our runtron binaries by absolute path
QWEN4=ingested-qwen-3-4b-instruct-2507-tp4
QWEN2=ingested-qwen-3-4b-instruct-2507-tp2
LLAMA2=llama-3.1-8b-instruct-good-tp2
mkdir -p "$RES/cells" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer"   # whole-machine work: Bill counts
source "$G/rz.sh"
NIX=$(command -v nix || echo /home/jhan/.nix-profile/bin/nix)
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
T_START=""

# ---------- stop rules ----------
past_deadline() {  # 01:30-11:00 UTC: pre-CI hold, prep 02:45, lease ~03:37, nightly ends ~11:25
  local hm; hm=$((10#$(date -u +%H%M)))
  [ "$hm" -ge 130 ] && [ "$hm" -lt 1100 ]
}
bill_present() {  # same rule as exec/split-bench3.sh: monitor fresh and CLEAR, no flag, no work process of Bill's
  [ -e "$FLAG" ] && return 0
  local age; age=$(( $(date +%s) - $(stat -c %Y "$STATE" 2>/dev/null || echo 0) ))
  [ "$age" -gt 120 ] && { echo "$(ts) monitor state stale (${age}s) or missing: treating as Bill present"; return 0; }
  [[ "$(cat "$STATE" 2>/dev/null)" == *"CLEAR:"* ]] || return 0
  pgrep -u "$BILL_UID" -f "$BILL_WORK_RE" >/dev/null 2>&1
}
machine_free() { ! bill_present && ! ci_lease_busy && ! rinzler_active; }
wait_free() {  # 0 = free (guard held again if it had been released); 1 = deadline reached
  local waited=0
  while :; do
    past_deadline && return 1          # checked BEFORE the free test: no new run inside 01:30-11:00 UTC
    if machine_free; then
      if [ $waited = 1 ] && [ -n "$T_START" ]; then campaign_guard_acquire || { sleep 60; continue; }; fi
      return 0
    fi
    if [ $waited = 0 ]; then
      status "waiting: $(cat "$STATE" 2>/dev/null | cut -c1-100)"; waited=1
      [ -n "$T_START" ] && campaign_guard_release   # do not block other scripts while Bill works
    fi
    sleep 60
  done
}
kill_ours() {  # only this campaign's processes: harness by result path, tron binaries by absolute path
  pkill -TERM -u jhan -f "st_perf[.]py .*results/g1-20260908" 2>/dev/null
  # the soak's command line carries no path of ours, so match it by working directory: soak_canon runs it from
  # "$cell/work" under $RES; another session's `python -m scripts.soak` or a bash -c text naming it does not
  for p in $(pgrep -u jhan -f "scripts[.]soak" 2>/dev/null); do
    case "$(readlink /proc/$p/cwd 2>/dev/null)" in "$RES"/*) kill -TERM "$p" 2>/dev/null ;; esac
  done
  pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null
  pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null
}
watch_run() {  # background: stop our run within ~10 s when Bill returns, CI takes the lease or serving comes up
  local sf=$1 why
  while :; do
    why=""
    if [ -e "$FLAG" ]; then why="monitor: $(head -c 120 "$FLAG" 2>/dev/null)"
    elif pgrep -u "$BILL_UID" -f "$BILL_WORK_RE" >/dev/null 2>&1; then why="Bill process: $(pgrep -u "$BILL_UID" -af "$BILL_WORK_RE" 2>/dev/null | head -1 | cut -c1-100)"
    elif ci_lease_busy; then why="CI lease busy"
    elif rinzler_active; then why="rinzler@N unit active"
    fi
    # no return: keep killing every 10 s. A single kill can find nothing (the tron binary is not exec'd yet during
    # rz_start's preamble) or land in the warm-up, and then nothing would watch the rest of the run.
    if [ -n "$why" ]; then [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"; kill_ours; fi
    sleep 10
  done
}
WPID=""
stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
finish() {  # $1 = marker word
  stop_watcher
  rz_stop 2>/dev/null
  campaign_guard_release 2>/dev/null
  python3 "$G/g1-summary.py" "$RES" >/dev/null && echo "$(ts) summary written: $RES/summary.md" || echo "$(ts) SUMMARY FAILED (python traceback above)"
  echo "$1" >"$MARKER"; status "finished: $1"
  echo "=== g1 campaign done $(ts) marker=$1 ==="
}

# ---------- one perf cell ----------
perf_cell() {  # MODEL ARM TP USERS -> 0 done, 1 failed, 2 stopped
  local model=$1 arm=$2 tp=$3 users=$4
  local cell=$RES/cells/${model}__${arm}__u${users}
  [ "$(cat "$cell/STATUS" 2>/dev/null)" = done ] && { echo "$(ts) skip $cell (done)"; return 0; }
  mkdir -p "$cell/work"; ln -sfn "$ST/golden_responses" "$cell/work/golden_responses"
  echo running >"$cell/STATUS"; rm -f "$cell/STOPPED" "$cell/perf.json" "$cell/meta.json" "$cell/proof.txt"   # a retry must not inherit an interrupted attempt
  local t0; t0=$(date +%s)
  echo "$(ts) ### perf model=$model arm=$arm tp=$tp users=$users"
  # watcher first: during model load nothing else would stop rinzler.canon/.mirror/.g1 when Bill returns
  watch_run "$cell/STOPPED" & WPID=$!
  if ! rz_start "$arm" "$PORT" "$tp" "$cell/rinzler.log" "$model"; then
    stop_watcher; rz_stop
    [ -e "$cell/STOPPED" ] && { echo stopped >"$cell/STATUS"; echo "$(ts) start stopped: $(cat "$cell/STOPPED")"; return 2; }
    echo start-failed >"$cell/STATUS"; return 1
  fi
  local t1; t1=$(date +%s)
  ( cd "$cell/work" && env -u SYSTEM_CONFIG PYTHONPATH="$H1/talos_stub:$ST" OPENAI_HOST=http://delphi-3bda:$PORT/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
      HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false timeout 1500 "$PY" "$H1/st_perf.py" --model "$model" --users "$users" --out "$cell/perf.json" >"$cell/perf.log" 2>&1 )
  local rc=$?
  stop_watcher
  rz_stop
  # proof lines, one per fact (a head over the whole regex never reached the mode line: the footprint line repeats hundreds of times)
  { grep -m1 'DD G1 store mode' "$cell/rinzler.log"; grep -m1 'Configured instance' "$cell/rinzler.log"; grep -m1 'App CPU list' "$cell/rinzler.log";
    grep -m1 'HW attention' "$cell/rinzler.log"; grep -m1 'AMX' "$cell/rinzler.log"; grep 'KV cache footprint' "$cell/rinzler.log" | tail -1; } >"$cell/proof.txt" 2>/dev/null
  # Mode line: the only proof that the AMX store path ran (dd_g1_mode prints once, at the first save_k with
  # k_mirror_on). g1mirror runs with TRON_DD_G1 unset, so its line reads "unset (0)".
  local want=""
  case $arm in sonly) want='DD G1 store mode: sonly (1)' ;; inplace) want='DD G1 store mode: inplace (2)' ;; g1mirror) want='DD G1 store mode: unset (0)' ;; esac
  [ -n "$want" ] && ! grep -qF "$want" "$cell/proof.txt" && { echo "$(ts) $arm: mode line '$want' missing (perf rc was $rc), cell marked failed"; rc=99; }
  # Arena: sonly stores K only through set_k_mirror, a no-op when the arena is absent, while the mode line still
  # prints; such a cell would read as "scatter-only is free". The leading space keeps "70.00 GB K mirror" from
  # matching. canon/off print 0.00 by design and are not checked.
  case $arm in
    mirror|g1mirror|sonly) grep 'KV cache footprint' "$cell/proof.txt" | grep -qF ' 0.00 GB K mirror' && { echo "$(ts) $arm: arena absent (0.00 GB K mirror), cell marked failed"; rc=98; } ;;
  esac
  python3 - "$cell" "$model" "$arm" "$tp" "$users" "$rc" "$t0" "$t1" "$(rz_bin "$arm")" <<'PY'
import json, sys, os, subprocess, time
cell, model, arm, tp, users, rc, t0, t1, binf = sys.argv[1:10]
sha = subprocess.run(['sha256sum', binf], capture_output=True, text=True).stdout.split()[0] if os.path.exists(binf) else ''
perf = {}
try: perf = json.load(open(os.path.join(cell, 'perf.json')))
except Exception: pass
proof = open(os.path.join(cell, 'proof.txt')).read() if os.path.exists(os.path.join(cell, 'proof.txt')) else ''
dd = [l for l in proof.splitlines() if 'DD G1 store mode' in l]
fp = [l for l in proof.splitlines() if 'KV cache footprint' in l]
stopped = os.path.exists(os.path.join(cell, 'STOPPED'))
meta = {"model": model, "arm": arm, "tp": int(tp), "users": int(users), "binary": binf, "binary_sha256": sha, "perf_rc": int(rc),
        "start_seconds": int(t1) - int(t0), "perf_seconds": int(time.time()) - int(t1), "stopped": stopped,
        "dd_g1_line": dd[0].strip() if dd else "", "footprint_line": fp[-1].strip()[-120:] if fp else "",
        "ttft_mean_ms": perf.get("ttft_mean_ms"), "tps_mean": perf.get("tps_mean"), "tps_std_dev": perf.get("tps_std_dev"),
        "prefill_mean_tok_s": perf.get("prefill_mean_tok_s"), "cache_hit_pct": perf.get("cache_hit_pct"), "n_ttft": len(perf.get("ttfts_ms", [])),
        "ended": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
json.dump(meta, open(os.path.join(cell, 'meta.json'), 'w'), indent=1)
ok = int(rc) == 0 and bool(perf) and not stopped
st = 'done' if ok else ('stopped' if stopped else 'failed')
line = f"{model} {arm} u{users} ttft_ms={perf.get('ttft_mean_ms')} tps={perf.get('tps_mean') or 0:.2f} sd={perf.get('tps_std_dev') or 0:.2f} prefill_tok_s={perf.get('prefill_mean_tok_s') or 0:.0f} cache={perf.get('cache_hit_pct') or 0:.1f}% mode='{meta['dd_g1_line'][-22:]}' rc={rc} status={st}"
open(os.path.join(os.path.dirname(os.path.dirname(cell)), 'summary.txt'), 'a').write(time.strftime('%Y-%m-%dT%H:%M:%SZ ', time.gmtime()) + line + "\n")
print(line)
PY
  if [ -e "$cell/STOPPED" ]; then echo stopped >"$cell/STATUS"; echo "$(ts) run stopped: $(cat "$cell/STOPPED")"; return 2; fi
  if [ "$rc" -eq 0 ] && [ -s "$cell/perf.json" ]; then echo done >"$cell/STATUS"; return 0; fi
  echo failed >"$cell/STATUS"; echo "$(ts) perf rc=$rc (see $cell/perf.log)"; return 1
}
START_FAILS=0; PROBE_FAILS=0; PROBE_DEAD=0
run_perf() {  # retry once after a stop; returns 1 only at the deadline. 3 consecutive start failures of the round-1
              # binaries end the campaign; 3 consecutive start failures of the never-run probe binary rinzler.g1 only
              # drop the remaining probe cells (the other arms keep running).
  local tries=0 rc probe=0
  [ "$(rz_bin "$2")" = "$G1BIN" ] && probe=1
  [ $probe = 1 ] && [ "$PROBE_DEAD" = 1 ] && { echo "$(ts) skip $* (probe binary does not start)"; return 0; }
  while :; do
    wait_free || return 1
    perf_cell "$@"; rc=$?
    if [ $rc -eq 1 ] && [ "$(cat "$RES/cells/${1}__${2}__u${4}/STATUS" 2>/dev/null)" = start-failed ]; then
      if [ $probe = 1 ]; then
        PROBE_FAILS=$((PROBE_FAILS + 1))
        [ $PROBE_FAILS -ge 3 ] && { PROBE_DEAD=1; echo "$(ts) 3 consecutive start failures of $G1BIN; remaining probe cells are skipped"; echo "probe_dead=1" >>"$RES/probe-build.txt"; }
        return 0
      fi
      START_FAILS=$((START_FAILS + 1))
      if [ $START_FAILS -ge 3 ]; then
        echo "$(ts) 3 consecutive start failures ($*); ending the campaign"; grep -E '^HugePages_(Total|Free):' /proc/meminfo | xargs; ls -l /dev/hugepages
        finish start-failures; exit 0
      fi
      return 0
    fi
    [ $rc -ne 2 ] && { if [ $probe = 1 ]; then PROBE_FAILS=0; else START_FAILS=0; fi; return 0; }
    tries=$((tries + 1)); [ $tries -ge 2 ] && { echo "$(ts) giving up on $* after 2 stops"; return 0; }
    echo "$(ts) waiting for CLEAR, then retrying $*"; sleep 120
  done
}
PHASE=""
sweep() {  # MODEL TP ARMS_AT_8 ARMS_AT_OTHER USERS_LIST
  local model=$1 tp=$2 arms8=$3 armsn=$4 users_list=$5 u a arms
  for u in $users_list; do
    if [ "$u" = 8 ]; then arms=$arms8; else arms=$armsn; fi
    for a in $arms; do
      status "phase $PHASE sweep $model users=$u arm=$a +$(( ($(date +%s) - ${T_START:-$(date +%s)}) / 60 )) min"
      run_perf "$model" "$a" "$tp" "$u" || return 1
    done
  done
  return 0
}

# ---------- runtron point: qwen tp2, 8 users, prompt 8192 (August placement) ----------
runtron_8u8k() {
  local out=$RES/runtron-8u8k.txt
  # --dont-stop: in the sonly/inplace arms the sampled tokens are garbage, so a stop token could end a user's
  # 256-token decode early ("-o" is --optimize, not a stop override).
  local rtargs="stream-generate-text -m $QWEN2 --instance 0,4 --devices 10:00.0,13:00.0 --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 --numa 0 --hugepage_file /dev/hugepages/amx-g1rt --nr_hugepages 128 -o --dont-stop"
  local arms="g1canon:$G1CRT: g1kill:$G1RT:TRON_AMX_DISABLE=1 g1mirror:$G1RT: sonly:$G1RT:TRON_DD_G1=sonly inplace:$G1RT:TRON_DD_G1=inplace"
  [ "$G1_OK" = 1 ] || { echo "$(ts) runtron point skipped: probe binaries missing"; echo "# skipped: probe build failed $(ts)" >>"$out"; return 0; }
  {
    echo "# G1 runtron point: qwen-3-4b tp2, 8 users, prompt 8192, 256 generated, --dont-stop, USE_HW_ATTN=0, August placement (cards 10/13, socket 0), $(ts)"
    echo "# arms (all head 60d66d9c04): g1canon = runtron.g1canon (TRON_AMX_K_MIRROR=OFF, canonical AMX); g1kill = runtron.g1 with TRON_AMX_DISABLE=1 (AVX baseline, arena build); g1mirror = runtron.g1 (mirror arm); sonly / inplace = runtron.g1 with TRON_DD_G1"
    sha256sum "$G1CRT" "$G1RT" 2>/dev/null
  } >>"$out"
  local rep spec name bin envv res rc tries rlog f
  for rep in 1 2; do
    for spec in $arms; do
      IFS=: read -r name bin envv <<<"$spec"
      [ -x "$bin" ] || { echo "### arm=$name rep=$rep BINARY-MISSING $bin" >>"$out"; continue; }
      tries=0
      while :; do
        wait_free || return 1
        status "phase 3: runtron 8u/8K arm=$name rep=$rep"
        echo "### arm=$name rep=$rep bin=$bin env=${envv:-none} $(ts)" >>"$out"
        rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
        # the whole output goes to a file (a failed, stopped or misplaced run stays diagnosable); the result lines are
        # grepped from it. "K mirror" is in the KV footprint line, printed once per GB of growth: keep the last one only.
        rlog=$RES/runtron-${name}-rep${rep}-t${tries}.log
        (cd "$(dirname "$bin")/.." && env -u SYSTEM_CONFIG -u TRON_DD_G1 -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug ${envv:+$envv} timeout 900 "$bin" $rtargs --prompt-length 8192 -l 256 -u 8) >"$rlog" 2>&1
        rc=$?
        res=$( { grep -E "Parsing the prompt took|average tok/s|Configured instance|App CPU list|DD G1 store mode|tokens in and .* out" "$rlog"; grep 'K mirror' "$rlog" | tail -1; } 2>/dev/null )
        stop_watcher
        # with --instance the hugepage files are /dev/hugepages/slice-<k>-of-8 (the --hugepage_file basename only selects
        # the directory); runtron keeps them at exit and every later rz_start would snapshot them as pre-existing, so
        # remove the unmapped ones we own here (same owner + fuser test as rz_stop)
        for f in /dev/hugepages/slice-*-of-8; do
          [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage slice file $f (unmapped, ours)"
        done
        if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ]; then
          echo "RUN-STOPPED rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null) (full output: $rlog)" >>"$out"
          tries=$((tries + 1)); [ $tries -ge 2 ] && { echo "RUN-GIVEN-UP after 2 stops" >>"$out"; break; }
          sleep 120; continue
        fi
        if [ $rc -ne 0 ]; then { echo "RUN-FAILED rc=$rc (full output: $rlog)"; echo "$res"; } >>"$out"; else echo "$res" >>"$out"; fi
        break
      done
    done
  done
  return 0
}

# ---------- canonical-arm soak, 60 min, 25 users (filler) ----------
soak_canon() {
  local cell=$RES/soak__canon60 minutes=60 users=25 hm rc
  mkdir -p "$cell/work"
  [ "$(cat "$cell/STATUS" 2>/dev/null)" = done ] && return 0
  wait_free || return 1
  # own cutoff: 60 min + 25 min harness slack must end before the 02:45 UTC production start
  hm=$((10#$(date -u +%H%M))); if [ "$hm" -ge 45 ] && [ "$hm" -lt 1100 ]; then echo "$(ts) too late for the 60-min soak (UTC $hm); skipped"; return 0; fi
  status "phase 6: canonical soak 60 min, 25 users (llama tp2 + qwen tp2 on one engine)"
  echo running >"$cell/STATUS"; rm -f "$cell/STOPPED"
  echo "{\"arm\": \"canon\", \"models\": [\"$LLAMA2\", \"$QWEN2\"], \"minutes\": $minutes, \"users\": $users, \"started\": \"$(ts)\"}" >"$cell/meta.json"
  watch_run "$cell/STOPPED" & WPID=$!
  if ! rz_start canon "$PORT" 2 "$cell/rinzler.log" "$LLAMA2" "$QWEN2"; then stop_watcher; rz_stop; echo start-failed >"$cell/STATUS"; return 0; fi
  ( cd "$cell/work" && env -u SYSTEM_CONFIG PYTHONPATH="$H1/talos_stub:$ST" OPENAI_HOST=http://delphi-3bda:$PORT/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
      NUM_USERS=$users MAX_DURATION=$minutes SSH_USER=jhan SSH_PASS= timeout $(( minutes * 60 + 1500 )) "$PY" -m scripts.soak >"$cell/soak.log" 2>&1 )
  rc=$?
  stop_watcher
  rz_stop
  { grep -m1 'Configured instance' "$cell/rinzler.log"; grep 'KV cache footprint' "$cell/rinzler.log" | tail -1; } >"$cell/proof.txt" 2>/dev/null
  if [ -e "$cell/STOPPED" ]; then echo stopped; elif [ $rc -eq 0 ]; then echo done; else echo failed; fi >"$cell/STATUS"
  echo "$(ts) soak rc=$rc status=$(cat "$cell/STATUS")"
  return 0
}

# ---------- probe builds (socket 1; before the whole-machine window) ----------
build_probe() {  # sets G1_OK from the probe worktree only; a g1canon build failure only drops the phase-3 g1canon arm
  G1_OK=0
  local wt mirror targets rc t0 bins b ok
  for spec in "$G1WT:ON:rinzler runtron" "$G1CWT:OFF:runtron"; do
    IFS=: read -r wt mirror targets <<<"$spec"
    if [ "$mirror" = ON ]; then bins="$G1BIN $G1RT"; else bins="$G1CRT"; fi
    ok=1; for b in $bins; do [ -x "$b" ] || ok=0; done
    if [ $ok = 1 ] && [ -e "$wt/gen/.g1-built" ] && [ "$(git -C "$wt" rev-parse --short=10 HEAD 2>/dev/null)" = "$G1SHA" ]; then
      echo "$(ts) $wt already built"; [ "$mirror" = ON ] && G1_OK=1; continue
    fi
    while ci_lease_busy; do sleep 60; done   # a 96-job build must never run under the nightly
    ( cd /home/jhan/workspace/tron-amx && { [ -d "$wt" ] || git worktree add --detach "$wt" "$G1SHA"; } ) || { echo "$(ts) worktree add failed for $wt"; continue; }
    cd "$wt" || continue
    [ "$(git rev-parse --short=10 HEAD)" = "$G1SHA" ] || git checkout -q --detach "$G1SHA"
    t0=$(date +%s)
    nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c \
      "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=$mirror -DCMAKE_CXX_FLAGS= 2>&1 | tail -3 &&
       cmake --build gen --target $targets -j96 2>&1 | grep -E 'error|FAILED' | sed -n 1,40p; exit \${PIPESTATUS[0]}"
    rc=$?
    echo "$(ts) build $wt MIRROR=$mirror targets=[$targets] rc=$rc in $(( $(date +%s) - t0 )) s"
    if [ $rc -ne 0 ] || ! strings gen/runtron | grep -q 'ingested-qwen-3-4b-instruct-2507'; then echo "$(ts) BUILD FAILED or qwen plugin missing in $wt"; cd "$EXEC"; continue; fi
    if [ "$mirror" = ON ]; then
      cp gen/rinzler gen/rinzler.g1 && cp gen/runtron gen/runtron.g1 && sha256sum gen/rinzler.g1 gen/runtron.g1 && touch gen/.g1-built && G1_OK=1
    else
      cp gen/runtron gen/runtron.g1canon && sha256sum gen/runtron.g1canon && touch gen/.g1-built
    fi
    cd "$EXEC"
  done
  [ "$G1_OK" = 1 ] || echo "$(ts) PROBE BUILD FAILED: the sweeps run with the off / canon / canon2 / mirror arms only"
  [ -x "$G1CRT" ] || echo "$(ts) g1canon build missing: the runtron point runs without its same-head canonical arm"
  return 0
}

[ "${G1_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }   # test harnesses source the functions and stop here

# ======================= main flow =======================
exec >>"$LOG" 2>&1
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== g1 campaign started $(ts) pid $$ G1SHA=$G1SHA ==="

# Before anything: the 01:30-11:00 UTC window is a HOLD (an early nightly end or a one-poll lease flicker must not
# start a 96-job build under the nightly), and the lease must be clear.
status "phase 1: holding until the clock is past 11:00 UTC and the lease is clear"
while past_deadline || ci_lease_busy; do sleep 60; done
# phase 1: builds (socket 1 only). The bare campaign flock is held through the build: the other session's PR 0b chain
# serializes on that flock and its last step is a whole-machine cost-data bench that measures the socket-1 slots too;
# if production serving is already down at lease-clear nothing else would keep that bench out of our 96-job build.
# The bare flock, not campaign_guard_acquire: that refuses while serving is up or Bill is active, and a socket-1 build
# needs neither. Released right after the build; T_START is still empty, so wait_free does not touch the lock before
# phase 0 takes it for real.
status "phase 1: building rinzler.g1 + runtron.g1 (mirror ON) and runtron.g1canon (mirror OFF) from $G1SHA on socket 1, about 20 min"
exec {CAMPAIGN_LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$CAMPAIGN_LOCK_FD"; do echo "$(ts) campaign flock held by another script (a PR 0b chain step?); build waits"; sleep 30; done
build_probe
campaign_guard_release
echo "g1_ok=$G1_OK" >"$RES/probe-build.txt"
if [ "$G1_OK" = 1 ]; then
  ARMS8="canon inplace sonly g1mirror off mirror canon2"; ARMS8L="canon inplace sonly off mirror canon2"; ARMSN="canon inplace sonly mirror"
else
  ARMS8="canon off mirror canon2"; ARMS8L="canon off mirror canon2"; ARMSN="canon mirror"
fi

# phase 0: waits (the hold above already covered the clock and the lease; re-check the lease after the long build)
while past_deadline || ci_lease_busy; do sleep 60; done
echo "$(ts) CI lease clear"
# Idle-serving takeover, round 1's recipe (exec/more-testing-r1-build.sh Stage A): the 02:45 UTC timer brings
# rinzler@0-3 up and the nightly uses them; when they stay up afterwards with no client activity for 10 minutes,
# stop them so the machine is usable (this also unblocks the other session's whole-machine bench).
status "phase 0: checking idle production serving"
for _ in $(seq 1 40); do   # up to ~80 min of 2-min polls
  ci_lease_busy && break
  rinzler_active || break
  # fail closed on missing evidence: an empty journal read (sudo refused, journal unreadable) must not count as idle
  j=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>&1) || { echo "$(ts) journalctl failed (${j:0:100}); not touching serving"; sleep 120; continue; }
  [ -n "$j" ] || { echo "$(ts) journal empty for the last 10 min; not touching serving"; sleep 120; continue; }
  traffic=$(printf '%s\n' "$j" | grep -v '#EVT#' | grep -icE 'session|request|prompt|generat|token') || true
  busy=$(printf '%s\n' "$j" | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
  stats=$(printf '%s\n' "$j" | grep -c 'SYSTEM_STATS') || true   # diagnosis only: idle units log SYSTEM_STATS 1.5x less often per line (300, 450, 675, 1013 s ...), so a 10-min window often has none
  # readability probe, fail closed: the newest line the units ever logged (any age). Empty = sudo refused or the journal is
  # unreadable, so the traffic/busy zeros above prove nothing and serving is left alone.
  probe=$(sudo -n journalctl -u 'rinzler@*' -n 1 -o cat --no-pager 2>/dev/null) || true
  conns=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 or sport = :3000 or sport = :3001 or sport = :3002 or sport = :3003 )' 2>/dev/null | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  echo "$(ts) rinzler units active; journal-request-lines=${traffic:-?} non-idle-stats-lines=${busy:-?} stats-lines=${stats:-?} journal-readable=$([ -n "$probe" ] && echo yes || echo no) remote-conns=${conns:-?}"
  if [ -n "$probe" ] && [ "${traffic:-1}" -eq 0 ] && [ "${busy:-1}" -eq 0 ] && [ "${conns:-1}" -eq 0 ]; then
    echo "$(ts) stopping idle rinzler serving per the standing policy (round 1 recipe)"
    if sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3; then
      sleep 5
      # positron's slice files are unmapped now (systemctl stop is synchronous); fuser cannot show that, since another
      # user's /proc/<pid>/maps is unreadable, so the owner decides. Own files: the owner + fuser test of phase 3.
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
rinzler_active && { echo "$(ts) TAKEOVER NOT DONE: rinzler@N still active after the polls; the PR 0b bench and this campaign both wait for serving to stop"; status "phase 0: serving still active after the takeover polls; waiting"; }
status "phase 0: waiting for the PR 0b chain (marker or its steps gone)"
while [ ! -e "$PR0B_MARKER" ] && pgrep -f "$PR0B_RE" >/dev/null 2>&1; do
  past_deadline && { finish deadline-before-start; exit 0; }
  sleep 60
done
echo "$(ts) PR 0b chain: marker=$(cat "$PR0B_MARKER" 2>/dev/null || echo none) steps=$(pgrep -f "$PR0B_RE" >/dev/null 2>&1 && echo running || echo gone)"
status "phase 0: waiting for Bill to be absent (monitor CLEAR) and the campaign guard"
wait_free || { finish deadline-before-start; exit 0; }
until campaign_guard_acquire; do
  sleep 60
  wait_free || { finish deadline-before-start; exit 0; }
done
T_START=$(date +%s)
echo "$(ts) guard acquired; monitor: $(cat "$STATE" 2>/dev/null | cut -c1-100)"
echo "$(ts) plan (est. from round 1): phase 2 about 58 min, phase 3 about 25, phase 4 about 67, phase 5 about 35, soak about 63; total about 4 h 10 min"

# phase 2: the gate cells, 8 users, qwen tp4 then llama tp2
status "phase 2: 8-user cells, qwen tp4 then llama tp2 (gate G1 data first)"
PHASE=2
sweep "$QWEN4" 4 "$ARMS8" "$ARMSN" "8" || { finish deadline; exit 0; }
sweep "$LLAMA2" 2 "$ARMS8L" "$ARMSN" "8" || { finish deadline; exit 0; }
# phase 3: runtron qwen 8 users prompt 8192
status "phase 3: runtron qwen 8 users prompt 8192"
runtron_8u8k || { finish deadline; exit 0; }
# phase 4: 1- and 4-user cells (mechanism), qwen then llama
status "phase 4: 1- and 4-user cells, qwen tp4 then llama tp2"
PHASE=4
sweep "$QWEN4" 4 "$ARMS8" "$ARMSN" "1 4" || { finish deadline; exit 0; }
sweep "$LLAMA2" 2 "$ARMS8L" "$ARMSN" "1 4" || { finish deadline; exit 0; }
# phase 5: 2-user cells (completes the 1/2/4/8 series the gate text names)
status "phase 5: 2-user cells, qwen tp4 then llama tp2"
PHASE=5
sweep "$QWEN4" 4 "$ARMS8" "$ARMSN" "2" || { finish deadline; exit 0; }
sweep "$LLAMA2" 2 "$ARMS8L" "$ARMSN" "2" || { finish deadline; exit 0; }
# phase 6: canonical soak (filler)
soak_canon || { finish deadline; exit 0; }

echo "$(ts) campaign wall time $(( ($(date +%s) - T_START) / 60 )) min"
finish ok
