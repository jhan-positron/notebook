#!/usr/bin/env bash
# Perf round on the latest jhan-amx-p0 (jhan request 2026-08-30): verify the
# commits since the 2026-08-25 round (bbb55ae5f..HEAD, 25 commits: dispatch
# gate on the executor's activation scalar, mirror write-through fill change,
# scheduler factory contract, arena RAM visibility) did not regress perf.
#
# Arms per AMX-boosted model (same protocol as p2-perf-round-20260825.sh so
# cells compare directly): canon = TRON_AMX_DISPATCH=ON K_MIRROR=OFF,
# mirror = both ON. USE_HW_ATTN=0 (all-software attention) everywhere.
# gpt-oss-120b (AMX-ineligible geometry, 64Q/8KV/head64) has no prior
# same-protocol reference, so it gets a third arm: disable = canon binary
# with TRON_AMX_DISABLE=1 (kill switch) as the within-round baseline.
#
# Launched in the evening free window (~20:40Z). CI prep starts ~03:30Z:
# stop_now refuses any launch whose timeout would cross 03:30Z. The clock is
# advisory; the CI lease and rinzler checks between runs are authoritative.
# Reviewed 2026-08-30 (3-lens adversarial pass): pipefail in builds,
# PIPESTATUS-based RUN-FAILED, env -u TRON_AMX_DISABLE, OUT rotation,
# lease check before the rinzler stage, trap kills surviving runtron.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/perf-round-20260830
OUT=$DIR/perf-round.txt
LOG=$EXEC/logs/p2-perf-round-20260830.log
MARKER=$EXEC/logs/p2-perf-round-20260830.done
mkdir -p "$DIR" "$EXEC/logs"
# A relaunch must not append to a previous attempt's data (the parser would
# merge both attempts under the same cell keys).
[ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== perf-round start $(date -u +%FT%TZ) ==="
source "$EXEC/lib-guard.sh"
trap '[ -e "$MARKER" ] || { pkill -TERM -f "gen/runtron\." 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-perf* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

# Stage A: rinzler policy - the CI lease is the authority on whether we may
# touch rinzler at all; then clean up only if serving shows zero traffic.
if ci_lease_busy; then
  echo "CI lease busy - not launching"
  echo guard-refused >"$MARKER"; exit 1
fi
active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active') || true
if [ "${active:-0}" -gt 0 ]; then
  # jhan cannot read the system journal without sudo (an unprivileged
  # journalctl silently returns nothing), so read it via sudo -n.
  traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
    | grep -icE 'session|request|prompt|generat|token') || true
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

# Stage C: build both arms from the current tree. pipefail inside the inner
# shell so a failed `cmake --build` is not masked by `tail`.
cd ~/workspace/tron-amx || { echo build-failed-cd >"$MARKER"; exit 1; }
echo "tree: $(git rev-parse --short HEAD) $(git status --short | tr '\n' ' ')"
build() {  # $1 = K_MIRROR value, $2 = output name
  nix develop --command bash -c \
    "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=$1 -DCMAKE_CXX_FLAGS= >/dev/null &&
     cmake --build gen --target runtron -j96 2>&1 | tail -2" \
    || { echo "build-failed-$2" >"$MARKER"; exit 1; }
  cp gen/runtron "gen/$2" || { echo "build-failed-cp-$2" >"$MARKER"; exit 1; }
}
build OFF runtron.canon
build ON runtron.mirror     # leaves gen/ in its usual mirror-ON configuration
if cmp -s gen/runtron.canon gen/runtron.mirror; then
  echo "canon and mirror binaries are byte-identical - build wiring broken"
  echo build-identical >"$MARKER"; exit 1
fi
sha256sum gen/runtron.canon gen/runtron.mirror
echo "=== builds done $(date -u +%FT%TZ) ==="

# Stage D: runs. stop_now refuses a launch when: the next run's timeout
# (+5 min margin) would cross the next 03:30Z CI prep start, the CI lease is
# busy, or rinzler serving is back.
stop_now() {  # $1 = the next run's timeout in seconds
  local tmo=${1:-0} now prep
  now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s)
  [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now + tmo + 300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }
  return 1
}
# The two builds took unattended minutes: re-check before the first run.
if stop_now 900; then
  echo "stopped after builds, before any run"
  campaign_guard_release; echo guard-stop >"$MARKER"; exit 1
fi
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-perf --nr_hugepages 128 -o"
run_arm() {  # $1 arm, $2 model, $3 ctx, $4 users, $5 timeout
  local arm=$1 model=$2 ctx=$3 users=$4 tmo=$5 bin rc
  case $arm in
    canon)   bin=./gen/runtron.canon ;;
    mirror)  bin=./gen/runtron.mirror ;;
    disable) bin=./gen/runtron.canon ;;
  esac
  # env -u pins the kill switch off even if the launching shell leaked it;
  # the disable arm sets it to exactly "1" (the only value that disables).
  if [ "$arm" = disable ]; then
    env USE_HW_ATTN=0 TRON_AMX_DISABLE=1 timeout "$tmo" $bin stream-generate-text -m "$model" $COMMON \
      --prompt-length "$ctx" -l 256 -u "$users" 2>&1 \
      | grep -E "Parsing the prompt took|average tok/s"
  else
    env -u TRON_AMX_DISABLE USE_HW_ATTN=0 timeout "$tmo" $bin stream-generate-text -m "$model" $COMMON \
      --prompt-length "$ctx" -l 256 -u "$users" 2>&1 \
      | grep -E "Parsing the prompt took|average tok/s"
  fi
  rc=("${PIPESTATUS[@]}")
  # rc[0] = timeout/runtron (124 = killed at the cap), rc[1] = grep
  # (1 = no timing lines at all). Either one nonzero means the cell's data
  # is missing or truncated - say so where the parser counts it.
  if [ "${rc[0]}" -ne 0 ] || [ "${rc[1]}" -ne 0 ]; then
    echo "RUN-FAILED rc=${rc[0]}/${rc[1]}"
  fi
}

RUN120B=1
{
  echo "# perf round on jhan-amx-p0 $(git rev-parse --short HEAD), $(date -u +%FT%TZ)"
  echo "# arms: canon = TRON_AMX_DISPATCH=ON K_MIRROR=OFF; mirror = both ON;"
  echo "# disable (gpt-oss-120b only) = canon binary with TRON_AMX_DISABLE=1. USE_HW_ATTN=0."
  echo "# reference: perf-round-20260825/perf-round.txt at bbb55ae5f (same cells, same protocol)."
  sha256sum gen/runtron.canon gen/runtron.mirror

  # gpt-oss-120b smoke: fail fast (and loud) if the ingest build or weights
  # are missing, instead of discovering it an hour in. rep=0 = not a cell.
  echo "### smoke model=ingested-gpt-oss-120b-tp2 arm=canon ctx=128 len=8 users=1 rep=0"
  env -u TRON_AMX_DISABLE USE_HW_ATTN=0 timeout 900 ./gen/runtron.canon stream-generate-text \
    -m ingested-gpt-oss-120b-tp2 $COMMON --prompt-length 128 -l 8 -u 1 2>&1 \
    | grep -E "Parsing the prompt took|average tok/s"
  smoke_rc=("${PIPESTATUS[@]}")
  if [ "${smoke_rc[0]}" -ne 0 ] || [ "${smoke_rc[1]}" -ne 0 ]; then
    echo "SMOKE-120B-FAILED rc=${smoke_rc[0]}/${smoke_rc[1]} - skipping all gpt-oss-120b cells"
    RUN120B=0
  fi

  for rep in 1 2 3; do
    for spec in "ingested-qwen-3-4b-instruct-2507-tp2 2048 1 900 canon mirror" \
                "ingested-qwen-3-4b-instruct-2507-tp2 8192 1 900 canon mirror" \
                "ingested-qwen-3-4b-instruct-2507-tp2 2048 8 900 canon mirror" \
                "ingested-qwen-3-4b-instruct-2507-tp2 8192 8 900 canon mirror" \
                "ingested-llama-3.1-8b-tp2 8192 1 900 canon mirror" \
                "ingested-llama-3.1-8b-tp2 2048 8 900 canon mirror" \
                "mixtral-8x7b-instruct-v0.1-tp2 2048 8 1800 canon mirror" \
                "mixtral-8x7b-instruct-v0.1-tp2 8192 8 1800 canon mirror" \
                "ingested-gpt-oss-120b-tp2 2048 1 1800 canon mirror disable" \
                "ingested-gpt-oss-120b-tp2 8192 1 1800 canon mirror disable" \
                "ingested-gpt-oss-120b-tp2 2048 8 1800 canon mirror disable" \
                "ingested-gpt-oss-120b-tp2 8192 8 2400 canon mirror disable"; do
      set -- $spec; model=$1; ctx=$2; users=$3; tmo=$4; shift 4; arms="$*"
      if [ "$model" = ingested-gpt-oss-120b-tp2 ] && [ "$RUN120B" = 0 ]; then continue; fi
      for arm in $arms; do
        if stop_now "$tmo"; then break 3; fi
        echo "### model=$model arm=$arm ctx=$ctx len=256 users=$users rep=$rep"
        run_arm "$arm" "$model" "$ctx" "$users" "$tmo"
      done
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT"
rm -f /dev/hugepages/amx-perf* 2>/dev/null || true
campaign_guard_release
if grep -qE "RUN-FAILED|SMOKE-120B-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== perf-round done $(date -u +%FT%TZ) ==="
