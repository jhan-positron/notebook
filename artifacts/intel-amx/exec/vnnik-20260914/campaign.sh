#!/usr/bin/env bash
# vnnik-20260914: TPS and TTFT of qwen3-4b with K stored in the VNNI layout (branch
# jhan-amx-vnniK, design in VNNIed-K-in-place/design/claude-VNNIed-K.html), against the
# AMX baseline (PR #3879, row-major K) and AMX off, on OUR half of delphi-3bda after the
# nightly CI. Fork of exec/p0perf-20260913/campaign.sh (runtron cells only, no rinzler).
#
# Words used here: tron = the inference program under test; runtron = its command-line
# tool; rinzler = the production server binary; AMX = the Intel matrix instruction set the
# branch uses for CPU attention; VNNI layout = the AMX B-operand (pair-interleaved) layout
# the new branch stores K in; TPS = generated tokens per second per user during decode;
# TTFT = time to first token, here runtron's "Parsing the prompt took" time (the batched
# prefill of the 8 prompts).
#
# Arms (all CPU attention, USE_HW_ATTN=0):
#   off     = runtron.p0perf13 (base commit 544ca05c7a, row-major K) with TRON_AMX_DISABLE=1
#   base    = runtron.p0perf13, switch unset                     (PR #3879: row-major AMX)
#   vnni    = runtron.vnnik (this branch, TRON_K_VNNI=ON), switch unset
#   vnnioff = runtron.vnnik with TRON_AMX_DISABLE=1  (AVX-512 VNNI reader + scatter store, no AMX)
# Cells: qwen-3-4b tp2 (--instance 2,4, cards 90/93), 8 users, 256 generated, prompt 1024 /
# 2048 / 8192, RT_REPS (default 3) repetitions with the four arms interleaved inside each
# repetition; then the same at tp4 (--instance 1,2, all four of our cards) with TP4_REPS
# (default 2) repetitions.
#
# Order: wait for the CI lease to be clear for 3 polls (never inside the 01:40-03:45 UTC
# pre-CI hold) -> build runtron + the four unit tests from TIP in a fresh worktree on local
# disk, socket 1 -> run the unit tests (a failure ends the campaign) -> idle-serving
# takeover (round 1 / G1 recipe, fail closed) -> greedy-agreement smoke (1 user, temperature
# 0) -> tp2 cells -> tp4 cells -> summary. Every run takes the campaign guard (lease + flock
# + no other runtron + serving down) and is watched by a 10-second watcher that kills OUR
# processes (absolute binary paths) if the lease turns busy or serving comes up. Bill's
# activity is not a reason to wait (our-half work); it is recorded per run.
# `env -u SYSTEM_CONFIG` on every tron process (the login environment exports
# "--instance 1,2", which tron applies AFTER the command line).
#
# Resume: relaunch; a run whose log already has "average tok/s" is skipped. Never edit this
# file while it runs (bash reads it incrementally from NFS).
#
# Outputs: exec/results/vnnik-20260914/{build.txt, tests.txt, smoke/, rt-results.txt,
# rt/<log per run>, summary.json, summary.md}; log exec/logs/vnnik-20260914.log; status
# exec/logs/vnnik-20260914.status; marker exec/logs/vnnik-20260914.done (ok | ...).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/vnnik-20260914
RES=$EXEC/results/vnnik-20260914
LOG=$EXEC/logs/vnnik-20260914.log
MARKER=$EXEC/logs/vnnik-20260914.done
STATUS=$EXEC/logs/vnnik-20260914.status
SRC_WT=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K   # the branch worktree (NFS)
WT=/var/tmp/jhan/tron-vnnik                                               # build worktree (local disk)
BASE_WT=/var/tmp/jhan/tron-p0perf13
BASE_TIP=544ca05c7a954f892f0e23ccb465f74ad46bea5e
RT_BASE=$BASE_WT/gen/runtron.p0perf13
RT_VNNI=$WT/gen/runtron.vnnik
OUR_CPUS=72-143,216-287
OUR_RT_RE='^/var/tmp/jhan/tron-(vnnik|p0perf13)/gen/runtron[.](vnnik|p0perf13) '   # both binaries this campaign runs (watcher + abort path)
VNNI_RT_RE='^/var/tmp/jhan/tron-vnnik/gen/runtron[.]vnnik '                          # only ours by construction (start-up + normal-end sweep)
OUR_TEST_RE='^/var/tmp/jhan/tron-vnnik/gen/t_(k_vnni_layout|amx_numerics|amx_dispatch_dtype|llama_unit)( |$)'
export GUARD_RUNTRON_USER=jhan   # lib-guard's no-runtron check looks at our runtron only (Bill's is not a reason to wait, see the header)
RT_REPS=${RT_REPS:-3}; TP4_REPS=${TP4_REPS:-2}
PROMPTS=${PROMPTS:-"1024 2048 8192"}
ARMS="off base vnni vnnioff"
TESTS="t_k_vnni_layout t_amx_numerics t_amx_dispatch_dtype t_llama_unit"
QWEN2=ingested-qwen-3-4b-instruct-2507-tp2
QWEN4=ingested-qwen-3-4b-instruct-2507-tp4
BILL_UID=1062305141
mkdir -p "$RES/rt" "$RES/smoke" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"   # our-half work: Bill's activity is not a reason to wait
NIX=$(command -v nix || echo /home/jhan/.nix-profile/bin/nix)
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }

placement() {  # $1 = tp
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
    *) return 1 ;;
  esac
}
arm_bin() { case $1 in off|base) echo "$RT_BASE" ;; vnni|vnnioff) echo "$RT_VNNI" ;; *) return 1 ;; esac; }
arm_env() { case $1 in off|vnnioff) echo "TRON_AMX_DISABLE=1" ;; base|vnni) echo "" ;; *) return 1 ;; esac; }

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
wait_clear() {
  local why waited=0
  while why=$(blocked); do
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    sleep 120
  done
  return 0
}
wait_lease_clear_3() {
  local n=0
  while :; do
    if preci_hold || ci_lease_busy; then n=0; else n=$((n + 1)); [ "$n" -ge 3 ] && return 0; fi
    sleep 60
  done
}
take_guard() {
  local waited=0
  until campaign_guard_acquire; do
    [ $waited = 0 ] && { status "waiting: campaign guard refused (see the GUARD line in the log)"; waited=1; pgrep -a -x 'runtron(\.[a-z0-9]+)?' 2>/dev/null | cut -c1-160 | sed 's/^/  runtron seen: /'; }
    sleep 60; wait_clear
  done
}
kill_ours() {  # both binaries (a stopped cell of ours may be either one); logs what it hit
  local pids; pids=$(pgrep -u jhan -f "$OUR_RT_RE" | tr '\n' ' ')
  [ -n "$pids" ] && { echo "$(ts) kill_ours: TERM runtron pids $pids"; pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null; }
  return 0
}
kill_vnni_only() {  # start-up and normal-end sweep: never touch a runtron.p0perf13 someone started by hand
  local pids; pids=$(pgrep -u jhan -f "$VNNI_RT_RE" | tr '\n' ' ')
  [ -n "$pids" ] && { echo "$(ts) sweep: TERM leftover runtron.vnnik pids $pids"; pkill -TERM -u jhan -f "$VNNI_RT_RE" 2>/dev/null; }
  pids=$(pgrep -u jhan -f '^/var/tmp/jhan/tron-p0perf13/gen/runtron[.]p0perf13 ' | tr '\n' ' ')
  [ -n "$pids" ] && echo "$(ts) sweep: runtron.p0perf13 pids $pids are running and NOT ours to kill; the guard waits for them"
  return 0
}
kill_our_tests() {  # the unit tests run under timeout in their own process group; the abort path must reach them by path
  local pids; pids=$(pgrep -u jhan -f "$OUR_TEST_RE" | tr '\n' ' ')
  [ -n "$pids" ] && { echo "$(ts) abort: TERM unit-test pids $pids"; pkill -TERM -u jhan -f "$OUR_TEST_RE" 2>/dev/null; }
  return 0
}
watch_run() {
  local sf=$1 why main=$$
  [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
  while :; do
    kill -0 "$main" 2>/dev/null || { kill_ours; sleep 10; pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null; sleep 2; remove_our_slice_files; exit 0; }
    why=""
    if ci_lease_busy; then why="CI lease busy"
    elif rinzler_active; then why="rinzler@N unit active"
    fi
    if [ -n "$why" ]; then [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"; kill_ours; fi
    sleep 10
  done
}
WPID=""
stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
finish() {
  stop_watcher
  if [ "$1" = aborted ]; then
    trap '' TERM
    [ "$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')" = "$$" ] && kill -TERM -- -$$ 2>/dev/null
    kill_ours; kill_our_tests
    for _ in $(seq 1 60); do pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || break; sleep 1; done
    pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null && { echo "$(ts) finish: SIGKILL to our runtron"; sleep 2; }
  else
    kill_vnni_only   # a normal end has no run of ours left; the base binary may be someone else's manual run
  fi
  remove_our_slice_files
  campaign_guard_release 2>/dev/null
  python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
  echo "$1" >"$MARKER"
  status "finished: $1"
  echo "=== campaign finished $(ts): $1 ==="
}
machine_line() {
  local bill; bill=$(ps -u "$BILL_UID" -o pcpu= -o comm= 2>/dev/null | awk '{n++; c+=$1} END {printf "bill_procs=%d bill_cpu_pct=%.0f", n, c}')
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) $bill"
}
remove_our_slice_files() {
  local f
  for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/amx-vnnik*; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage file $f (unmapped, ours)"
  done
}

# ---------- phase 1: build runtron + unit tests from TIP ----------
resolve_tip() {  # VNNIK_TIP wins; else, once results exist, the tip they were measured with; else the branch worktree's head
  if [ -n "${VNNIK_TIP:-}" ]; then echo "$VNNIK_TIP"; return; fi
  if [ -s "$WT/gen/.vnnik-built" ] && { ls "$RES"/rt/*.log "$RES"/smoke/*.tokens >/dev/null 2>&1; }; then
    echo "$(ts) resume: results exist, keeping the built tip $(cat "$WT/gen/.vnnik-built") (a new branch head is NOT picked up; set VNNIK_TIP or move the results to start over)" >&2
    cat "$WT/gen/.vnnik-built"; return
  fi
  git -C "$SRC_WT" rev-parse HEAD
}
build() {
  TIP=$(resolve_tip) || { echo "$(ts) cannot resolve TIP"; return 1; }
  echo "$(ts) TIP=$TIP ($(git -C /home/jhan/workspace/tron-amx log -1 --format='%ci %s' "$TIP" 2>/dev/null))"
  if [ -x "$RT_VNNI" ] && [ -e "$WT/gen/.vnnik-built" ] && [ "$(cat "$WT/gen/.vnnik-built" 2>/dev/null)" = "$TIP" ]; then
    echo "$(ts) $WT already built for $TIP"; return 0
  fi
  ( cd /home/jhan/workspace/tron-amx && { [ -d "$WT" ] || git worktree add --detach "$WT" "$TIP"; } ) || { echo "$(ts) worktree add failed for $WT"; return 1; }
  cd "$WT" || return 1
  [ "$(git rev-parse HEAD)" = "$TIP" ] || git checkout -q --detach "$TIP" || { echo "$(ts) checkout $TIP failed"; cd "$EXEC"; return 1; }
  rm -f gen/.vnnik-built gen/.vnnik-tested
  local t0 rc; t0=$(date +%s)
  nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c \
    "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= 2>&1 | tail -3 &&
     cmake --build gen --target runtron $TESTS -j96 2>&1 | grep -E 'error|FAILED' | sed -n 1,60p; exit \${PIPESTATUS[0]}"
  rc=$?
  echo "$(ts) build $WT DISPATCH=ON K_VNNI=ON targets=[runtron $TESTS] rc=$rc in $(( $(date +%s) - t0 )) s"
  if [ $rc -ne 0 ]; then echo "$(ts) BUILD FAILED"; cd "$EXEC"; return 1; fi
  strings gen/runtron | grep -q 'ingested-qwen-3-4b-instruct-2507' || { echo "$(ts) qwen plugin MISSING in gen/runtron"; cd "$EXEC"; return 1; }
  cp gen/runtron gen/runtron.vnnik || { cd "$EXEC"; return 1; }
  {
    echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
    echo "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= ; targets runtron $TESTS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS"
    sha256sum gen/runtron.vnnik
    ./gen/runtron.vnnik --version 2>&1 | head -2
    echo "base binary: $RT_BASE (commit $(git -C "$BASE_WT" rev-parse HEAD 2>/dev/null), expected $BASE_TIP)"
    sha256sum "$RT_BASE"
  } >"$RES/build.txt"
  echo "$TIP" >gen/.vnnik-built
  cd "$EXEC"
  return 0
}

# ---------- phase 1b: unit tests (fake device; SYSTEM_CONFIG="--instance 1,2" for the core set only) ----------
run_tests() {
  local t rc fails=0
  if [ "$(cat "$WT/gen/.vnnik-tested" 2>/dev/null)" = "$TIP" ]; then echo "$(ts) unit tests already passed for $TIP"; cat "$RES/tests.txt"; return 0; fi
  : >"$RES/tests.txt"
  for t in $TESTS; do
    status "phase 1b: unit test $t"
    # absolute path so that the abort path can find the process (timeout puts it in its own process group)
    ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 2400 "$WT/gen/$t" ) >"$RES/tests-$t.out" 2>&1
    rc=$?
    echo "$t rc=$rc tip=$TIP $(grep -E 'test cases:|All tests passed|FAILED|AMX unavailable' "$RES/tests-$t.out" | tr '\n' ' ' | cut -c1-300)" >>"$RES/tests.txt"
    [ $rc -eq 0 ] || fails=$((fails + 1))
  done
  cat "$RES/tests.txt"
  [ $fails -eq 0 ] && echo "$TIP" >"$WT/gen/.vnnik-tested"
  return $fails
}

# ---------- phase 2: greedy-agreement smoke (1 user, temperature 0, deterministic planning) ----------
SMOKE_FAIL=0
run_smoke() {  # every arm on the same prompt, plus an A/A repeat of the two AMX arms (base2, vnni2); token id files compared afterwards
  local arm base_arm bin envv rc out stops
  for arm in base vnni off vnnioff base2 vnni2; do
    base_arm=${arm%2}; bin=$(arm_bin "$base_arm"); envv=$(arm_env "$base_arm"); out=$RES/smoke/$arm; stops=0
    while :; do
      [ -s "$out.tokens" ] && { echo "$(ts) smoke $arm already done"; break; }
      wait_clear; take_guard
      status "phase 2: smoke $arm"
      echo "### smoke arm=$arm bin=$bin env=${envv:-unset} tip=$TIP prompt=1024 len=128 users=1 temperature=0 pay-for-determinism $(ts) $(machine_line)" >>"$RES/smoke/smoke.txt"
      rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
      (cd "$WT" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=info ${envv:+$envv} \
          timeout 600 "$bin" stream-generate-text -m "$QWEN2" $(placement 2) --hugepage_file /dev/hugepages/amx-vnnik -o \
          --prompt-length 1024 -l 128 -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$out.tokens") >"$out.log" 2>&1
      rc=$?
      stop_watcher; campaign_guard_release; remove_our_slice_files
      echo "smoke $arm rc=$rc $(grep -E 'average tok/s|Parsing the prompt took' "$out.log" | tr '\n' ' ' | cut -c1-200)" >>"$RES/smoke/smoke.txt"
      if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ] || [ $rc -eq 124 ]; then
        echo "SMOKE-STOPPED arm=$arm rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null)" >>"$RES/smoke/smoke.txt"
        rm -f "$out.tokens"; stops=$((stops + 1))
        [ $stops -ge 3 ] && { echo "SMOKE-GIVEN-UP arm=$arm after 3 stops" >>"$RES/smoke/smoke.txt"; SMOKE_FAIL=$((SMOKE_FAIL + 1)); break; }
        sleep 120; continue
      fi
      [ $rc -eq 0 ] && [ -s "$out.tokens" ] || { echo "SMOKE-FAILED arm=$arm rc=$rc" >>"$RES/smoke/smoke.txt"; SMOKE_FAIL=$((SMOKE_FAIL + 1)); }
      break
    done
  done
  python3 "$C/compare_tokens.py" "$RES/smoke" >>"$RES/smoke/smoke.txt" 2>&1 || true
  tail -10 "$RES/smoke/smoke.txt"
}

# ---------- phase 3: runtron cells ----------
run_rt() {  # $1 tp  $2 prompt  $3 arm  $4 rep
  local tp=$1 prompt=$2 arm=$3 rep=$4 model rlog attempt stops=0 rc res envv bin
  case $tp in 2) model=$QWEN2 ;; 4) model=$QWEN4 ;; esac
  bin=$(arm_bin "$arm"); envv=$(arm_env "$arm")
  rlog=$RES/rt/tp${tp}__p${prompt}__${arm}__rep${rep}.log
  if grep -q "average tok/s" "$rlog" 2>/dev/null; then echo "$(ts) runtron tp$tp p$prompt $arm rep$rep already done"; return 0; fi
  attempt=$(ls "$rlog".attempt* 2>/dev/null | wc -l)
  while :; do
    attempt=$((attempt + 1))
    wait_clear; take_guard
    status "phase 3: runtron tp$tp prompt=$prompt arm=$arm rep=$rep attempt=$attempt"
    echo "### runtron tp=$tp prompt=$prompt arm=$arm rep=$rep attempt=$attempt bin=$bin tip=$([ "$arm" = off ] || [ "$arm" = base ] && echo "$BASE_TIP" || echo "$TIP") env=${envv:-TRON_AMX_DISABLE unset} len=256 users=8 $(ts) $(machine_line)" >>"$RES/rt-results.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    (cd "$WT" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug ${envv:+$envv} \
        timeout 1200 "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file /dev/hugepages/amx-vnnik -o \
        --prompt-length "$prompt" -l 256 -u 8) >"$rlog.attempt$attempt" 2>&1
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

[ "${VNNIK_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
instck=$(mktemp /tmp/vnnik-instck.XXXXXX)
pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign[.]sh$' >"$instck"
others=$(grep -vx "$$" "$instck" | tr '\n' ' '); rm -f "$instck"
if [ -n "$others" ]; then echo "$(ts) another campaign.sh instance is running (pids $others); this one exits"; exit 1; fi
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== vnnik-20260914 campaign started $(ts) pid $$ RT_REPS=$RT_REPS TP4_REPS=$TP4_REPS PROMPTS=[$PROMPTS] ARMS=[$ARMS] ==="
kill_vnni_only; sleep 3; remove_our_slice_files
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
[ -x "$RT_BASE" ] || { echo "$(ts) base binary $RT_BASE missing"; finish no-base-binary; exit 1; }
[ "$(git -C "$BASE_WT" rev-parse HEAD 2>/dev/null)" = "$BASE_TIP" ] || echo "$(ts) WARNING: $BASE_WT is not at $BASE_TIP"

# phase 1: build after the lease is clear (a 96-job build must never run under the nightly), on socket 1.
status "phase 1: waiting for the CI lease to be clear (3 polls), then building on socket 1"
wait_lease_clear_3
echo "$(ts) CI lease clear (3 polls); $(machine_line)"
exec {CAMPAIGN_LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$CAMPAIGN_LOCK_FD"; do echo "$(ts) campaign flock held by another script; build waits"; sleep 30; done
build || { campaign_guard_release; finish build-failed; exit 1; }
cat "$RES/build.txt"
status "phase 1b: unit tests"
if ! run_tests; then campaign_guard_release; finish tests-failed; exit 1; fi
campaign_guard_release

# phase 0: idle-serving takeover (round 1 / G1 recipe, fail closed)
wait_lease_clear_3
status "phase 0: checking idle production serving"
for _ in $(seq 1 40); do
  ci_lease_busy && break
  rinzler_active || break
  j=$(sudo -n journalctl -q -u 'rinzler@*' --since '-10 min' --no-pager 2>&1) || { echo "$(ts) journalctl failed (${j:0:100}); not touching serving"; sleep 120; continue; }
  [ -n "$j" ] || { echo "$(ts) journal empty for the last 10 min; not touching serving"; sleep 120; continue; }
  traffic=$(printf '%s\n' "$j" | grep -v '#EVT#' | grep -icE 'session|request|prompt|generat|token') || true
  busy=$(printf '%s\n' "$j" | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
  probe=$(sudo -n journalctl -u 'rinzler@*' -n 1 -o cat --no-pager 2>/dev/null) || true
  sso=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 or sport = :3000 or sport = :3001 or sport = :3002 or sport = :3003 )' 2>/dev/null) || sso='ss-failed - - unknown:0'   # fail closed: an ss failure counts as a connection
  conns=$(printf '%s\n' "$sso" | awk 'NF && $4 !~ /^127\.0\.0\.1:/' | wc -l)
  echo "$(ts) rinzler units active; journal-request-lines=${traffic:-?} non-idle-stats-lines=${busy:-?} journal-readable=$([ -n "$probe" ] && echo yes || echo no) remote-conns=${conns:-?}"
  if [ -n "$probe" ] && [ "${traffic:-1}" -eq 0 ] && [ "${busy:-1}" -eq 0 ] && [ "${conns:-1}" -eq 0 ]; then
    echo "$(ts) stopping idle rinzler serving per the standing policy (round 1 recipe)"
    if sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3; then
      sleep 5
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
rinzler_active && { echo "$(ts) TAKEOVER NOT DONE: rinzler@N still active after the polls; the runs wait for serving to stop"; status "phase 0: serving still active; waiting"; }

# phase 2: smoke
run_smoke

# phase 3: cells
{
  echo "# vnnik-20260914 runtron results: qwen-3-4b, 8 users, 256 generated, prompts [$PROMPTS]; host $(hostname); started $(ts)"
  echo "# vnni tip $(cat "$WT/gen/.vnnik-built"); base tip $BASE_TIP"
  echo "# placement tp2: $(placement 2)"
  echo "# placement tp4: $(placement 4)"
  echo "# arms: off = base binary + TRON_AMX_DISABLE=1; base = base binary; vnni = vnnik binary; vnnioff = vnnik binary + TRON_AMX_DISABLE=1; USE_HW_ATTN=0 in all; env -u SYSTEM_CONFIG; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug"
  sha256sum "$RT_BASE" "$RT_VNNI"
} >>"$RES/rt-results.txt"
rt_fail=0
for rep in $(seq 1 "$RT_REPS"); do
  for prompt in $PROMPTS; do
    for arm in $ARMS; do
      run_rt 2 "$prompt" "$arm" "$rep" || rt_fail=$((rt_fail + 1))
    done
  done
done
echo "$(ts) tp2 cells done, failed runs: $rt_fail"
for rep in $(seq 1 "$TP4_REPS"); do
  for prompt in $PROMPTS; do
    for arm in $ARMS; do
      run_rt 4 "$prompt" "$arm" "$rep" || rt_fail=$((rt_fail + 1))
    done
  done
done
echo "$(ts) tp4 cells done, failed runs total: $rt_fail"

# phase 4: summary
status "phase 4: summary"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md" || { echo "summarize.py failed:"; cat "$RES/summary.err"; }
remove_our_slice_files
if [ $rt_fail -eq 0 ] && [ $SMOKE_FAIL -eq 0 ]; then finish ok; else finish "check-output (runtron failures $rt_fail, smoke failures $SMOKE_FAIL)"; fi
exit 0
