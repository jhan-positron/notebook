#!/usr/bin/env bash
# attnstats-20261002 chain (runs ON delphi-3bda, detached): attention path stats of tron main with the AMX kernel
# enabled and disabled, three models, on our half of the machine. jhan 2026-10-01: "queue a machine test at 3bda after
# CI finishes tomorrow morning" -> NOT_BEFORE (default 2026-10-02T13:00:00Z; the nightly's lease clears ~13:20 UTC), then
# every step waits for the CI lease (600 s grace), for other people's activity to end (bill excluded by the half-split
# agreement) and for no blackout. Steps, each with a marker under RES (resume = relaunch; done steps are skipped):
#   F fetch    : git fetch origin main in /home/jhan/workspace/tron; COMMIT = that tip (or the COMMIT variable when set);
#                written to RES/main.sha; re-done on every launch. A failed fetch falls back to COMMIT_FALLBACK.
#   A build    : exec/i4525-20260922/build2.sh -> /var/tmp/jhan/tron-main1002 at COMMIT, cross-avx512, AMX dispatch ON,
#                ingest models ON, target runtron only (copied to gen/runtron.main1002). A failed build stops the chain.
#   D campaign : campaign.sh (this folder): cells x arms amxon/amxoff, TRON_ATTN_STATS=1 in both arms.
#   R report   : gen_compare.py -> RES/attn-stats-compare.md, copied to PR3879/new-PRs/new-counters/attn-stats-compare.md
#                (the working folder of the request) as the first version for the plain-English pass.
# Log: exec/logs/attnstats-20261002-chain.log; status: exec/logs/attnstats-20261002-chain.status; marker RES/chain.done.
# Words: the lease = /run/lock/systems-test-ci.lease (nightly CI); our half = socket 1 + cards 90/93/b9/bc;
# amxon = TRON_AMX_DISABLE unset (the AMX kernel serves dense pages); amxoff = TRON_AMX_DISABLE=1 (the kill switch:
# the same binary scores every page with the AVX software loop).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/attnstats-20261002
NAME=${NAME:-attnstats-20261002}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
STATUS=$EXEC/logs/$NAME-chain.status
REPORT_COPY=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/attn-stats-compare.md
export NOT_BEFORE=${NOT_BEFORE:-2026-10-02T13:00:00Z}
COMMIT=${COMMIT:-}                          # pin main to this commit; empty = fetch origin/main at step F
COMMIT_FALLBACK=${COMMIT_FALLBACK:-9c88327931}   # origin/main as seen 2026-10-01 23:5x UTC
STEPS=${STEPS:-"F A D R"}
WT=/var/tmp/jhan/tron-main1002
SUFFIX=main1002
CONF='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON'   # cross-avx512 was removed from main 2026-09-30 (8d64eeed81); native = gen/, RelWithDebInfo
export REPS=${REPS:-1} ARMS=${ARMS:-"amxon amxoff"}
export ARM_ENV_amxon="TRON_ATTN_STATS=1"
export ARM_ENV_amxoff="TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"
# key|model|tp|users|prompt|attn|len. jhan's final list (2026-10-02 02:5x UTC): the request's situations at prompt 1024
# (llama = software attention, gpt-oss and qwen = attention on the FPGA) plus one qwen CPU-attention control (fitting shape
# under software attention), and llama + qwen again at prompt 8192. Dropped by jhan: every gpt-oss CPU cell (gpt-oss always
# runs AoF), gpt-oss at 8192, the llama USE_HW_ATTN=1 cells, qwen CPU at 8192. attn=fpga1 stays supported but unused.
CELLS_ALL=${CELLS_ALL:-$'l8b-8u-p1024-cpu|llama-3.1-8b-instruct-good-tp2|2|8|1024|cpu|256
gptoss-8u-p1024-fpga|ingested-gpt-oss-120b-tp4|4|8|1024|fpga|256
q3-4b-8u-p1024-fpga|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024|fpga|256
q3-4b-8u-p1024-cpu|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024|cpu|256
l8b-8u-p8192-cpu|llama-3.1-8b-instruct-good-tp2|2|8|8192|cpu|256
q3-4b-8u-p8192-fpga|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192|fpga|256'}
export CELLS_ALL
export CELLS=${CELLS:-}
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
machine_line() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) lease=$(ci_lease_busy 600 && echo busy || echo clear) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
nb=$(date -u -d "$NOT_BEFORE" +%s 2>/dev/null) || { echo "$(ts) bad NOT_BEFORE '$NOT_BEFORE' (use 2026-10-02T13:00:00Z); not starting"; exit 1; }
exec {CHAIN_LOCK_FD}>"/var/tmp/jhan/$NAME.chain.lock"
flock -n "$CHAIN_LOCK_FD" || { echo "$(ts) another chain.sh holds /var/tmp/jhan/$NAME.chain.lock; exit"; exit 1; }
rm -f "$RES/chain.done"
echo "=== $NAME chain started $(ts) pid $$ on $(hostname) NOT_BEFORE=$NOT_BEFORE STEPS=[$STEPS] REPS=$REPS ARMS=[$ARMS] COMMIT=${COMMIT:-fetch} ==="
not_before_wait() { local waited=0; while [ "$(date -u +%s)" -lt "$nb" ]; do [ $waited = 0 ] && { status "waiting: NOT_BEFORE $NOT_BEFORE"; waited=1; }; sleep 60; done; return 0; }
# Builds and the fetch need only the lease, no pre-CI hold and an idle machine of other people; they leave the production engines alone.
wait_slot() { local waited=0; not_before_wait; while preci_hold || ci_lease_busy 600 || other_user_active 2>/dev/null || blackout_active; do [ $waited = 0 ] && { status "waiting before $1: pre-CI hold, CI lease busy (600 s grace), another person active or blackout"; waited=1; }; sleep 120; done; echo "$(ts) $1 may start: $(machine_line)"; }
# Run a build step in the background and stop it (its process group) if the CI lease turns busy meanwhile.
# Returns 0 when the build ran to its end, 3 when this watcher stopped it for a busy lease.
BUILD_PGID=""
run_build() { local killed=0; setsid bash -c "$1" & local bp=$!; BUILD_PGID=$bp; while kill -0 $bp 2>/dev/null; do if ci_lease_busy; then echo "$(ts) CI lease busy during $2: stopping the build"; killed=1; kill -TERM -- -$bp 2>/dev/null; sleep 5; kill -KILL -- -$bp 2>/dev/null; fi; sleep 60; done; wait $bp; BUILD_PGID=""; [ $killed = 0 ] || return 3; }
# Second chance for production serving: campaign.sh marks every takeover it did (serving-taken-down.marker) and brings
# serving back in its own finish(); if it died before that, this chain does it (after step D and on exit).
SERVING_UP_HELPER=$EXEC/q4b-fpga-20260921/dut.sh
serving_restore() {
  [ -e "$RES/serving-taken-down.marker" ] || return 0
  if ci_lease_busy 600; then echo "$(ts) serving_restore: CI lease busy, leaving serving alone"; return 0; fi
  if rinzler_active; then echo "$(ts) serving_restore: rinzler units already active"; rm -f "$RES/serving-taken-down.marker"; return 0; fi
  echo "$(ts) serving_restore: production was taken down by the campaign and is not back; dut.sh serving-up"
  if timeout 900 bash "$SERVING_UP_HELPER" serving-up; then rm -f "$RES/serving-taken-down.marker"; else echo "$(ts) serving_restore: serving-up returned rc=$? (jhan: check platformd)"; fi
}
on_exit() { [ -n "$BUILD_PGID" ] && { echo "$(ts) exit: stopping the build process group $BUILD_PGID"; kill -TERM -- -$BUILD_PGID 2>/dev/null; sleep 3; kill -KILL -- -$BUILD_PGID 2>/dev/null; }; serving_restore; }
trap 'on_exit' EXIT
trap 'echo "$(ts) TERM received"; exit 143' TERM
fail_chain() { status "chain stopped: $*"; echo "stopped: $*" >"$RES/chain.done"; exit 1; }
report_step() {
  if python3 "$C/gen_compare.py" "$RES" >"$RES/attn-stats-compare.md" 2>"$RES/gen_compare.err"; then
    [ -e "$REPORT_COPY" ] && cp -p "$REPORT_COPY" "$REPORT_COPY.$(date -u +%Y%m%dT%H%M%SZ).bak" && echo "$(ts) previous report copy saved as .bak"
    cp "$RES/attn-stats-compare.md" "$REPORT_COPY" && echo "$(ts) report written: $RES/attn-stats-compare.md and $REPORT_COPY ($(wc -l <"$RES/attn-stats-compare.md") lines)"
  else
    echo "$(ts) gen_compare.py FAILED: $(tail -3 "$RES/gen_compare.err" | tr '\n' ' ')"
  fi
}
for step in $STEPS; do
  case $step in
    F)
      # always re-fetched (a pre-built tree from an earlier run is rebuilt by step A only when main moved)
      wait_slot "step F (fetch main)"
      if [ -n "$COMMIT" ]; then
        echo "$(ts) step F: COMMIT pinned to $COMMIT"
      elif git -C /home/jhan/workspace/tron fetch -q origin main 2>>"$RES/fetch.err"; then
        COMMIT=$(git -C /home/jhan/workspace/tron rev-parse --short=10 origin/main)
        echo "$(ts) step F: origin/main fetched: $COMMIT ($(git -C /home/jhan/workspace/tron log -1 --format='%ci %s' origin/main | cut -c1-120))"
      else
        COMMIT=$COMMIT_FALLBACK
        echo "$(ts) step F: fetch FAILED ($(tail -1 "$RES/fetch.err" 2>/dev/null)); using the fallback tip $COMMIT"
      fi
      git -C /home/jhan/workspace/tron cat-file -e "$COMMIT^{commit}" 2>/dev/null || fail_chain "step F: commit $COMMIT is not in /home/jhan/workspace/tron"
      echo "$COMMIT" >"$RES/main.sha" ;;
    A)
      [ -n "$COMMIT" ] || COMMIT=$(cat "$RES/main.sha" 2>/dev/null) || fail_chain "step A: no commit (run step F)"
      if [ "$(cat "$RES/build-$SUFFIX.done" 2>/dev/null)" = ok ] && [ -x "$WT/gen/runtron.$SUFFIX" ] && [ "$(git -C "$WT" rev-parse --short=10 HEAD 2>/dev/null)" = "$(git -C /home/jhan/workspace/tron rev-parse --short=10 "$COMMIT")" ]; then
        echo "$(ts) step A already done at $COMMIT"; continue
      fi
      [ -e /var/tmp/jhan/tron-main0916/.git ] || fail_chain "step A: build2.sh finds the owner repo through /var/tmp/jhan/tron-main0916, which is missing"
      tries=0
      while :; do
        tries=$((tries + 1))
        wait_slot "step A (build runtron)"; status "step A: build of main $COMMIT in $WT (try $tries)"
        run_build "env RES='$RES' SRC=/home/jhan/workspace/tron COMMIT='$COMMIT' WT='$WT' SUFFIX='$SUFFIX' CONFIGURE_ARGS='$CONF' TARGETS='runtron' TESTS='' bash $EXEC/i4525-20260922/build2.sh" "step A"
        brc=$?; r=$(cat "$RES/build-$SUFFIX.done" 2>/dev/null); echo "$(ts) step A result: rc=$brc marker=[$r]"
        [ $brc -eq 3 ] && [ $tries -lt 3 ] && { echo "$(ts) step A: build stopped for a busy lease; waiting and retrying"; continue; }
        break
      done
      [ "$r" = ok ] || fail_chain "step A build failed (marker [$r]), see $RES/build-$SUFFIX.log"
      # the binary must carry the AMX kernel and the stats switch (stripped binary: count AMX tile instructions in the disassembly)
      command -v objdump >/dev/null || fail_chain "step A: objdump not found"
      objdump -d --no-show-raw-insn "$WT/gen/runtron.$SUFFIX" >"$RES/runtron-$SUFFIX.dis" 2>"$RES/objdump.err" || fail_chain "step A: objdump failed: $(tail -1 "$RES/objdump.err")"
      n_amx=$(grep -c -E '\b(tdpbf16ps|tdpfp16ps|tdpbssd|tdpbsud|tdpbusd|tdpbuud|tileloadd|tilestored|ldtilecfg|tilerelease)\b' "$RES/runtron-$SUFFIX.dis" || true)
      n_sw=$(grep -c -a 'TRON_ATTN_STATS' "$WT/gen/runtron.$SUFFIX" || true)
      rm -f "$RES/runtron-$SUFFIX.dis"
      echo "$(ts) step A: AMX tile instructions in runtron.$SUFFIX: $n_amx; TRON_ATTN_STATS strings: $n_sw" | tee -a "$RES/build-$SUFFIX.txt"
      [ "${n_amx:-0}" -gt 0 ] || fail_chain "step A: the binary has no AMX tile instructions (TRON_AMX_DISPATCH did not take)"
      [ "${n_sw:-0}" -gt 0 ] || fail_chain "step A: TRON_ATTN_STATS literal missing from the binary (PR #4596 not in $COMMIT?)" ;;
    D)
      if [ "$(cat "$EXEC/logs/$NAME.done" 2>/dev/null)" = ok ]; then echo "$(ts) step D already done: ok"; continue; fi
      [ -x "$WT/gen/runtron.$SUFFIX" ] || fail_chain "step D: $WT/gen/runtron.$SUFFIX missing (run step A)"
      not_before_wait; status "step D: campaign ($(wc -l <<<"$CELLS_ALL") cells x arms [$ARMS] x REPS $REPS)"
      env RT_MAIN="$WT/gen/runtron.$SUFFIX" NAME="$NAME" bash "$C/campaign.sh"
      m=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null); echo "$(ts) step D result: [$m]"
      serving_restore
      case $m in
        ok) ;;
        ok-with-*) echo "$(ts) step D: some runs failed; relaunch with STEPS='D R' to retry them" ;;
        *) report_step; fail_chain "step D ended with marker [$m] (partial report written; resume with STEPS='D R')" ;;
      esac ;;
    R)
      status "step R: report"; report_step ;;
    *) echo "$(ts) unknown step $step" ;;
  esac
done
echo "ok" >"$RES/chain.done"; status "chain finished"
echo "=== $NAME chain finished $(ts): F=$(cat "$RES/main.sha" 2>/dev/null) A=$(cat "$RES/build-$SUFFIX.done" 2>/dev/null) D=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null) R=$([ -s "$RES/attn-stats-compare.md" ] && echo written || echo missing) ==="
