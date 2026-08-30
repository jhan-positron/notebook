#!/usr/bin/env bash
# Resume of the 2026-08-25 perf round after tonight's CI (jhan: "if you cannot
# complete the tests before CI, stop tonight and resume tomorrow morning after
# CI"). Waits for 09:30Z, then a quiet machine (rinzler policy cleanup), then
# the campaign guard, and runs ONLY the (model, ctx, users, arm, rep) cells not
# already present in perf-round.txt. Reuses gen/runtron.canon and
# gen/runtron.mirror built by p2-perf-round-20260825.sh (no rebuild).
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/perf-round-20260825
OUT=$DIR/perf-round.txt
LOG=$EXEC/logs/p2-perf-round-resume.log
MARKER=$EXEC/logs/p2-perf-round-resume.done
mkdir -p "$DIR" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== perf-round-resume queued $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
source "$EXEC/lib-guard.sh"

# Nothing left? Exit before touching the machine.
remaining() {
  local n=0
  for rep in 1 2 3; do
    for spec in "ingested-qwen-3-4b-instruct-2507-tp2 2048 1" "ingested-qwen-3-4b-instruct-2507-tp2 8192 1" \
                "ingested-qwen-3-4b-instruct-2507-tp2 2048 8" "ingested-qwen-3-4b-instruct-2507-tp2 8192 8" \
                "ingested-llama-3.1-8b-tp2 8192 1" "ingested-llama-3.1-8b-tp2 2048 8" \
                "mixtral-8x7b-instruct-v0.1-tp2 2048 8" "mixtral-8x7b-instruct-v0.1-tp2 8192 8"; do
      set -- $spec
      for arm in canon mirror; do
        grep -qF "### model=$1 arm=$arm ctx=$2 len=256 users=$3 rep=$rep" "$OUT" 2>/dev/null || n=$((n+1))
      done
    done
  done
  echo $n
}
if [ "$(remaining)" -eq 0 ]; then echo "nothing remaining"; echo ok-nothing-left >"$MARKER"; exit 0; fi
echo "$(remaining) cells remaining at queue time"

# Stage A: wait for the post-CI window, then a quiet machine (rinzler policy).
# Only wait if we are before 09:30Z; if launched later in the day, go now.
if [ "$(hhmm)" -lt 930 ] || [ "$(hhmm)" -ge 2000 ]; then
  while [ "$(hhmm)" -lt 930 ] || [ "$(hhmm)" -ge 2000 ]; do sleep 300; done
fi
echo "=== window reached $(date -u +%FT%TZ) ==="
# Re-check: tonight's run may have finished everything after we queued.
if [ "$(remaining)" -eq 0 ]; then echo "nothing remaining after wait"; echo ok-nothing-left >"$MARKER"; exit 0; fi
wait_for_ci_release 21600 || { echo ci-never-released >"$MARKER"; exit 1; }
quiet=0
while [ "$(hhmm)" -lt 1400 ]; do
  active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active') || true
  if [ "${active:-0}" -eq 0 ]; then quiet=1; break; fi
  traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
    | grep -icE 'session|request|prompt|generat|token') || true
  conns=$(sudo -n ss -Htn state established \
    '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 )' 2>/dev/null \
    | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  if [ "${traffic:-0}" -eq 0 ] && [ "${conns:-0}" -eq 0 ]; then
    echo "rinzlers active, zero journal traffic (10 min), no remote conns - stopping per policy"
    sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 || { echo stop-failed >"$MARKER"; exit 1; }
    sleep 5
    if ! fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null; then
      rm -f /dev/hugepages/slice-*-of-8; echo "hugepage slices removed"
    fi
    quiet=1; break
  fi
  echo "serving in use (journal=$traffic conns=$conns), waiting"; sleep 600
done
if [ "$quiet" != 1 ]; then echo never-quiet >"$MARKER"; exit 1; fi

# Stage B: guard.
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi

# Stage C: remaining cells, same rep-major order. Stop at 20:00Z... the
# window is the whole day; still re-check the lease and rinzler between runs.
cd ~/workspace/tron-amx
[ -x gen/runtron.canon ] && [ -x gen/runtron.mirror ] || { echo binaries-missing >"$MARKER"; exit 1; }
stop_now() {
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }
  [ "$(hhmm)" -ge 2000 ] && { echo CLOCK-STOP; return 0; }
  return 1
}
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-perf --nr_hugepages 128 -o"
{
  echo "# resume after CI $(date -u +%FT%TZ): remaining cells only, same binaries"
  sha256sum gen/runtron.canon gen/runtron.mirror
  for rep in 1 2 3; do
    for spec in "ingested-qwen-3-4b-instruct-2507-tp2 2048 1 900" "ingested-qwen-3-4b-instruct-2507-tp2 8192 1 900" \
                "ingested-qwen-3-4b-instruct-2507-tp2 2048 8 900" "ingested-qwen-3-4b-instruct-2507-tp2 8192 8 900" \
                "ingested-llama-3.1-8b-tp2 8192 1 900" "ingested-llama-3.1-8b-tp2 2048 8 900" \
                "mixtral-8x7b-instruct-v0.1-tp2 2048 8 1800" "mixtral-8x7b-instruct-v0.1-tp2 8192 8 1800"; do
      set -- $spec; model=$1; ctx=$2; users=$3; tmo=$4
      for arm in canon mirror; do
        hdr="### model=$model arm=$arm ctx=$ctx len=256 users=$users rep=$rep"
        grep -qF "$hdr" "$OUT" && continue
        if stop_now; then break 3; fi
        echo "$hdr"
        env USE_HW_ATTN=0 timeout "$tmo" ./gen/runtron.$arm stream-generate-text -m "$model" $COMMON \
          --prompt-length "$ctx" -l 256 -u "$users" 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
  echo "### resume complete $(date -u +%FT%TZ), remaining=$(remaining)"
} >>"$OUT"
rm -f /dev/hugepages/amx-perf* 2>/dev/null || true
campaign_guard_release
if grep -qE "RUN-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== perf-round-resume done $(date -u +%FT%TZ) ==="
