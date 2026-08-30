#!/usr/bin/env bash
# Perf round on the latest jhan-amx-p0 (jhan request 2026-08-25 00:45Z, before
# tonight's CI): two arms per model - canonical (TRON_AMX_DISPATCH=ON,
# TRON_AMX_K_MIRROR=OFF) and mirror-on (both ON) - on the three PR models.
# NOT a full A/B: no kill-switch / clean arms. Rep-major order so a complete
# rep 1 lands before the window closes.
#
# Window: CI prep starts ~03:30Z; stop launching runs at 03:10Z, and yield
# if the 02:45Z ci-runner-stop timer brings rinzler serving back.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/perf-round-20260825
OUT=$DIR/perf-round.txt
LOG=$EXEC/logs/p2-perf-round-20260825.log
MARKER=$EXEC/logs/p2-perf-round-20260825.done
mkdir -p "$DIR" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== perf-round start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
source "$EXEC/lib-guard.sh"

# Stage A: rinzler policy - clean up only if serving shows zero traffic.
active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active') || true
if [ "${active:-0}" -gt 0 ]; then
  # jhan cannot read the system journal without sudo (an unprivileged
  # journalctl silently returns nothing), so read it via sudo -n.
  traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
    | grep -icE 'session|request|prompt|generat|token') || true
  # Second, journal-independent signal: established client connections on
  # the serving ports from NON-loopback peers (the four 127.0.0.1 keepalives
  # are local plumbing, present even when idle).
  conns=$(sudo -n ss -Htn state established \
    '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 )' 2>/dev/null \
    | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  if [ "${traffic:-0}" -ne 0 ] || [ "${conns:-0}" -ne 0 ]; then
    echo "rinzler serving looks in use (journal request lines=$traffic, remote conns=$conns) - not touching it"
    echo serving-in-use >"$MARKER"; exit 1
  fi
  echo "rinzlers active, zero journal traffic (10 min) and no remote client connections - stopping per policy"
  sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 || { echo stop-failed >"$MARKER"; exit 1; }
  sleep 5
  if ! fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null; then
    rm -f /dev/hugepages/slice-*-of-8
    echo "hugepage slices removed (fuser: no open handles)"
  fi
fi

# Stage B: cross-session campaign guard.
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi

# Stage C: build both arms from the current tree.
cd ~/workspace/tron-amx
echo "tree: $(git rev-parse --short HEAD) $(git status --short | tr '\n' ' ')"
build() {  # $1 = K_MIRROR value, $2 = output name
  nix develop --command bash -c \
    "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=$1 -DCMAKE_CXX_FLAGS= >/dev/null &&
     cmake --build gen --target runtron -j96 2>&1 | tail -2" \
    || { echo "build-failed-$2" >"$MARKER"; exit 1; }
  cp gen/runtron "gen/$2"
}
build OFF runtron.canon
build ON runtron.mirror     # leaves gen/ in its usual mirror-ON configuration
sha256sum gen/runtron.canon gen/runtron.mirror
echo "=== builds done $(date -u +%FT%TZ) ==="

# Stage D: runs. Stop on: clock >= 03:10Z, CI lease busy, or rinzler back.
stop_now() {
  [ "$(hhmm)" -ge 310 ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }
  return 1
}
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-perf --nr_hugepages 128 -o"
{
  echo "# perf round on jhan-amx-p0 $(git rev-parse --short HEAD), $(date -u +%FT%TZ)"
  echo "# arms: canon = TRON_AMX_DISPATCH=ON K_MIRROR=OFF; mirror = both ON. USE_HW_ATTN=0."
  sha256sum gen/runtron.canon gen/runtron.mirror
  for rep in 1 2 3; do
    for spec in "ingested-qwen-3-4b-instruct-2507-tp2 2048 1 900" \
                "ingested-qwen-3-4b-instruct-2507-tp2 8192 1 900" \
                "ingested-qwen-3-4b-instruct-2507-tp2 2048 8 900" \
                "ingested-qwen-3-4b-instruct-2507-tp2 8192 8 900" \
                "ingested-llama-3.1-8b-tp2 8192 1 900" \
                "ingested-llama-3.1-8b-tp2 2048 8 900" \
                "mixtral-8x7b-instruct-v0.1-tp2 2048 8 1800" \
                "mixtral-8x7b-instruct-v0.1-tp2 8192 8 1800"; do
      set -- $spec; model=$1; ctx=$2; users=$3; tmo=$4
      for arm in canon mirror; do
        if stop_now; then break 3; fi
        echo "### model=$model arm=$arm ctx=$ctx len=256 users=$users rep=$rep"
        env USE_HW_ATTN=0 timeout "$tmo" ./gen/runtron.$arm stream-generate-text -m "$model" $COMMON \
          --prompt-length "$ctx" -l 256 -u "$users" 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT"
rm -f /dev/hugepages/amx-perf* 2>/dev/null || true
campaign_guard_release
if grep -qE "RUN-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== perf-round done $(date -u +%FT%TZ) ==="
