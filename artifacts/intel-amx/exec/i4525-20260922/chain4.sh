#!/usr/bin/env bash
# i4525-20260922 chain4 (runs ON delphi-3bda, launched with nohup): the machine steps of
# (chain4.sh = chain3.sh + the "final commit" switch: the branch author removes a hot-path TRON_ASSERT from v_vnni.hpp after
#  snapshot 48ab31f7. When the file $RES/EPRIME.request holds that commit's sha before Step E starts, the head runtron is
#  rebuilt from it into /var/tmp/jhan/tron-i4525rt2 and Step E measures the final commit; when the sha arrives during
#  Step E, a reduced perf A/B (base vs final, prompt 1024 and 8192, 2 repetitions) runs after E, before the host suite.
#  Step D always uses the snapshot binary: an assert changes no token. Same log file as chain2/chain3.)
# (chain2.sh = chain.sh relaunched 21:0x UTC after the base build failed on a short-sha fetch; the two runtron builds and the
#  Step C build started by chain.sh keep running; this driver waits for their markers instead of starting them.)
# issue4525/status/first-3bda-test-plan.md that the plan's author left to us, in this order:
#   1. build the two runtron binaries with the qwen3-4b plugin: base = main 0a51385e95 in /var/tmp/jhan/tron-main0922,
#      head = snapshot commit $SNAP of the branch working tree in /var/tmp/jhan/tron-i4525rt (AMX on, 16 lanes, RelWithDebInfo);
#      in parallel the Step C tree /var/tmp/jhan/tron-i4525c (branch snapshot, 16 lanes, AMX OFF = the CI feature set) is
#      configured and `make build-test-host` starts (nice 15; paused with SIGSTOP while Step E measures).
#   2. Step D: greedy token identity, CPU attention at prompt 1024 and 8192 (arms base head head2 baseoff headoff), FPGA
#      attention at 1024 and 8192 (arms base head). smoke.sh takes serving down through the idle takeover when needed.
#   3. Step E: runtron 8 users x prompt 1024/2048/8192 x arms base head baseoff headoff x 3 repetitions (campaign.sh).
#   4. Step C: `make test-host` in the AMX-off tree (host-suite.sh; the build half must be done first).
#   5. Step F data: objdump of the A1 t_llama_unit binaries of the plan author's trees (analysis is done off the machine).
#   6. production serving back up through platformd; evidence copied to issue4525/evidence/3bda-first-test/.
# Deadline: every runtron step stops at 01:30 UTC (campaign.sh DEADLINE_HHMM); the chain skips remaining steps after
# END_BY (default 01:35 UTC) and always tries the serving-up at the end. The 02:45 UTC timer brings inference up anyway.
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4525-20260922
export NAME=${NAME:-i4525-20260922}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain2.log
T=/var/tmp/jhan/tron-issue4525-tests           # the plan's log directory (section 3)
SNAP=${SNAP:-$(head -1 "$C/SNAPSHOT.sha")}
BASE_COMMIT=${BASE_COMMIT:-0a51385e95}
REPO=/home/jhan/workspace/tron                 # owner of the /var/tmp/jhan worktrees; holds the snapshot ref (NFS)
RT_BASE=/var/tmp/jhan/tron-main0922/gen/runtron.main0922
RT_HEAD=/var/tmp/jhan/tron-i4525rt/gen/runtron.i4525rt
END_BY=${END_BY:-2026-09-23T01:35:00Z}
END_EPOCH=$(date -u -d "$END_BY" +%s)
RT_CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
C_CONFIGURE='--preset native -DAVX512=ON -DTRON_AMX_DISPATCH=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_INGEST_MODELS=OFF -DBUILD_TEST_MODELS=OFF -DBUILD_PRODUCTION_MODELS=OFF'
mkdir -p "$RES" "$T" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$END_EPOCH" ]; }
exec >>"$LOG" 2>&1
echo "=== $NAME chain started $(ts) pid $$ on $(hostname) snapshot=$SNAP base=$BASE_COMMIT END_BY=$END_BY ==="
echo "$(ts) machine: lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }

# ---- 1. builds: started by chain.sh (head runtron, Step C tree) and by hand (base runtron with build2.sh); wait for the markers ----
# The Step C build (make build-test-host in /var/tmp/jhan/tron-i4525c) was started by chain.sh in its own process group
# (setsid). Its group id is read from the make process; c_running also catches compiler/ingest processes of that tree.
c_group() { local p; p=$(pgrep -u jhan -f 'make build-test-host' | head -1); [ -n "$p" ] && ps -o pgid= -p "$p" | tr -d ' '; }
c_running() { [ -n "$(c_group)" ] || pgrep -u jhan -f '/var/tmp/jhan/tron-i4525c/' >/dev/null; }
pause_c() { local g; g=$(c_group); [ -n "$g" ] && kill -STOP -- "-$g" 2>/dev/null; pgrep -u jhan -f '/var/tmp/jhan/tron-i4525c/' | xargs -r kill -STOP 2>/dev/null; echo "$(ts) Step C build paused (SIGSTOP to group ${g:-none} + tree processes)"; }
resume_c() { local g; g=$(c_group); [ -n "$g" ] && kill -CONT -- "-$g" 2>/dev/null; pgrep -u jhan -f '/var/tmp/jhan/tron-i4525c/' | xargs -r kill -CONT 2>/dev/null; echo "$(ts) Step C build resumed (SIGCONT to group ${g:-none})"; }
echo "$(ts) Step C build group: $(c_group || echo none) running=$(c_running && echo yes || echo no)"
until [ -s "$RES/build-main0922.done" ] && [ "$(cat "$RES/build-main0922.done")" != checkout-failed ] && [ -s "$RES/build-i4525rt.done" ]; do
  past_end && { step_done builds "builds not finished by END_BY"; echo chain-failed-builds >"$RES/chain.done"; exit 1; }
  sleep 30
done
echo "$(ts) runtron builds: base=$(cat "$RES/build-main0922.done" 2>/dev/null) head=$(cat "$RES/build-i4525rt.done" 2>/dev/null)"
for b in "$RT_BASE" "$RT_HEAD"; do
  [ -x "$b" ] && n=$(strings "$b" | grep -c ingested-qwen-3-4b-instruct-2507) || n=0
  echo "$(ts) plugin check $b: qwen3-4b strings=$n"
  [ "${n:-0}" -gt 0 ] || { step_done builds "FAILED: $b missing or without the qwen3-4b plugin"; echo "chain-failed-builds" >"$RES/chain.done"; g=$(c_group); [ -n "$g" ] && kill -- "-$g" 2>/dev/null; exit 1; }
done
step_done builds "ok base=$RT_BASE head=$RT_HEAD (Step C build-test-host group: $(c_group || echo finished))"

# ---- 2. Step D: token identity (smoke.sh takes serving down through the idle takeover when needed) ----
export RT_BASE RT_HEAD ARM_ENV_baseoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1
for spec in "cpu 1024 base head head2 baseoff headoff" "cpu 8192 base head head2 baseoff headoff" "fpga 1024 base head" "fpga 8192 base head"; do
  past_end && { step_done D "skipped $spec: past END_BY"; continue; }
  set -- $spec; attn=$1; prompt=$2; shift 2
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$C/smoke.sh"
  step_done D "$attn p$prompt: $(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null)"
done

# ---- 3. Step E: performance A/B (the Step C build is paused meanwhile so it does not disturb the measurement) ----
RT_FINAL=/var/tmp/jhan/tron-i4525rt2/gen/runtron.i4525rt2
E_USED_FINAL=0
build_final() {  # $1 = sha; synchronous; returns 0 when $RT_FINAL exists with the qwen plugin
  echo "$(ts) building the final commit $1 into /var/tmp/jhan/tron-i4525rt2"
  RES=$RES SRC=$REPO COMMIT=$1 WT=/var/tmp/jhan/tron-i4525rt2 SUFFIX=i4525rt2 CONFIGURE_ARGS="$RT_CONFIGURE" TARGETS=runtron TESTS= JOBS=48 bash "$C/build2.sh"
  echo "$(ts) final build: $(cat "$RES/build-i4525rt2.done" 2>/dev/null) plugin strings=$( [ -x "$RT_FINAL" ] && strings "$RT_FINAL" | grep -c ingested-qwen-3-4b-instruct-2507 || echo 0)"
  [ -x "$RT_FINAL" ] && [ "$(cat "$RES/build-i4525rt2.done" 2>/dev/null)" = ok ]
}
if past_end; then step_done E "skipped: past END_BY"; else
  pause_c
  if [ -s "$RES/EPRIME.request" ]; then
    FINAL_SHA=$(head -1 "$RES/EPRIME.request")
    if build_final "$FINAL_SHA"; then RT_HEAD=$RT_FINAL; E_USED_FINAL=1; step_done E-head "Step E uses the FINAL commit $FINAL_SHA ($RT_FINAL)"; else step_done E-head "final build failed; Step E uses the snapshot binary"; fi
  else step_done E-head "no EPRIME.request before Step E; Step E uses the snapshot binary $RT_HEAD"; fi
  export RT_HEAD
  CELLS_ALL=$'q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024\nq3-4b-tp2-8u-p2048|ingested-qwen-3-4b-instruct-2507-tp2|2|8|2048\nq3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192' \
    ARMS="base head baseoff headoff" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 bash "$C/campaign.sh"
  step_done E "$(cat "$EXEC/logs/$NAME.done" 2>/dev/null) (head binary: $RT_HEAD)"
  # the sha arrived during Step E: reduced perf A/B on the final commit before the host suite
  if [ "$E_USED_FINAL" = 0 ] && [ -s "$RES/EPRIME.request" ] && ! past_end; then
    FINAL_SHA=$(head -1 "$RES/EPRIME.request")
    if build_final "$FINAL_SHA"; then
      RT_HEAD=$RT_FINAL NAME=i4525-final-20260922 CELLS_ALL=$'q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024\nq3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192' \
        ARMS="base head" ATTNS=cpu REPS=2 DEADLINE_HHMM=0130 bash "$C/campaign.sh"
      step_done E-final "$(cat "$EXEC/logs/i4525-final-20260922.done" 2>/dev/null) (final commit $FINAL_SHA vs base, prompt 1024/8192, 2 reps)"
    else step_done E-final "final build failed; no reduced A/B"; fi
  fi
  resume_c
fi

# ---- 4. Step C: test-host in the AMX-off tree (needs the build half; serving down, no runtron) ----
if past_end; then step_done C "skipped: past END_BY"; else
  while c_running && ! past_end; do sleep 60; done
  if c_running; then step_done C "build-test-host still running at END_BY; test-host skipped (build left running, group $(c_group || echo ?))"; else
    echo "$(ts) build-test-host result: $(grep -E 'rc=' "$RES/build-test-host-i4525c.txt" | tr '\n' ' ')"
    if ! grep -q 'build-test-host rc=0' "$RES/build-test-host-i4525c.txt"; then
      # main 0a51385e95 itself fails to compile t/t_rinzler.cpp in some configurations (peer session, 21:05 UTC): build the
      # remaining host test targets with ninja -k 0 so that one broken target does not hide the rest, and record what is missing
      echo "$(ts) build-test-host failed; rebuilding the host targets with -k 0"
      ( cd /var/tmp/jhan/tron-i4525c && nice -n10 taskset -c 72-143,216-287 /home/jhan/.nix-profile/bin/nix develop --command bash -c '
          set -o pipefail; targets=$(bin/slice build-targets --build-dir=gen --filter=host); echo "host targets: $(wc -w <<<"$targets")"
          cmake --build gen --target $targets -j 48 -- -k 0 2>&1 | grep -E "error:|FAILED:" | head -40; echo "build-k0 rc=${PIPESTATUS[0]}"
          for t in $targets; do [ -x "gen/$t" ] || echo "missing binary: $t"; done' ) >"$RES/build-test-host-k0-i4525c.txt" 2>&1
      echo "$(ts) -k 0 rebuild: $(grep -E 'rc=|missing binary|host targets' "$RES/build-test-host-k0-i4525c.txt" | tr '\n' ' ' | cut -c1-600)"
    fi
    if grep -q 'build-test-host rc=0' "$RES/build-test-host-i4525c.txt" || grep -q 'build-k0 rc=' "$RES/build-test-host-k0-i4525c.txt" 2>/dev/null; then
      while rinzler_active && ! past_end; do rinzler_takeover_if_idle || sleep 120; done
      if past_end; then step_done C "skipped test-host: past END_BY"; else
        ( cd /var/tmp/jhan/tron-i4525c && nice -n10 taskset -c 72-143,216-287 /home/jhan/.nix-profile/bin/nix develop --command bash -c '
            set -o pipefail; SYSTEM_CONFIG="--instance 1,2" timeout -k 60 5400 make test-host 2>&1 | tail -100; echo "test-host rc=${PIPESTATUS[0]}"' ) >"$RES/test-host-i4525c.txt" 2>&1
        step_done C "$(grep -E 'test-host rc=|passed|failed' "$RES/test-host-i4525c.txt" | tail -3 | tr '\n' ' ')"
      fi
    else step_done C "build-test-host failed; test-host skipped"; fi
  fi
fi

# ---- 5. Step F data: objdump of the plan author's A1 t_llama_unit binaries ----
for tree in tron-issue4525 tron-issue4525-base; do
  b=/var/tmp/jhan/$tree/gen/t_llama_unit
  if [ -x "$b" ]; then ( cd /var/tmp/jhan/$tree && nice -n10 objdump -d -l --no-show-raw-insn -C gen/t_llama_unit > "$T/objdump.$tree.txt" 2>"$T/objdump.$tree.err"; echo "$(ts) objdump $tree: $(wc -l < "$T/objdump.$tree.txt") lines, sha $(sha256sum "$b" | cut -c1-16), tip $(git rev-parse --short HEAD 2>/dev/null), status $(git status --short 2>/dev/null | wc -l) changed files" ); else echo "$(ts) objdump $tree: no binary"; fi
done
step_done F "objdump files in $T (analysis off-machine)"

# ---- 6. serving back up, evidence copy ----
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
EV=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/3bda-first-test
mkdir -p "$EV" && cp -r "$RES"/. "$EV/" 2>/dev/null; [ -d "$EXEC/results/i4525-final-20260922" ] && mkdir -p "$EV/final" && cp -r "$EXEC/results/i4525-final-20260922"/. "$EV/final/" 2>/dev/null; cp "$T"/*.log "$EV/" 2>/dev/null; cp "$LOG" "$EXEC/logs/$NAME.log" "$EXEC/logs/i4525-final-20260922.log" "$EV/" 2>/dev/null
echo "chain-finished" >"$RES/chain.done"
echo "=== $NAME chain finished $(ts) ==="
