#!/usr/bin/env bash
# more-testing round 1 (jhan request 2026-09-04, input-2-ai/more-testing.md):
# stage 1 = free the machine per the rinzler policy and build the two rinzler
# arms from the PR3879 head (jhan-amx-p0 @ 60d66d9c04):
#   rinzler.canon  = TRON_AMX_DISPATCH=ON  TRON_AMX_K_MIRROR=OFF
#   rinzler.mirror = TRON_AMX_DISPATCH=ON  TRON_AMX_K_MIRROR=ON
# The AMX-off arm is rinzler.canon run with TRON_AMX_DISABLE=1 (kill switch),
# same protocol as exec/p2-perf-round-20260830.sh. Only the rinzler target is
# built (systems_test drives rinzler over HTTP; runtron is not needed).
set -u
EXEC=~/workspace/intel-AMX/exec
LOG=$EXEC/logs/more-testing-r1-build.log
MARKER=$EXEC/logs/more-testing-r1-build.done
mkdir -p "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== build stage start $(date -u +%FT%TZ) ==="
source "$EXEC/lib-guard.sh"

# Stage A: rinzler policy. The CI lease is the authority; then stop serving
# only if it shows zero client activity. The periodic "#EVT# SYSTEM_STATS"
# journal line contains the words Sessions/Tokens, so exclude #EVT# lines
# before counting request-like lines (the 20260830 grep counted them).
if ci_lease_busy; then echo "CI lease busy - not touching the machine"; echo guard-refused >"$MARKER"; exit 1; fi
active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active') || true
if [ "${active:-0}" -gt 0 ]; then
  traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
    | grep -v '#EVT#' | grep -icE 'session|request|prompt|generat|token') || true
  busy=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
    | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
  conns=$(sudo -n ss -Htn state established \
    '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 or sport = :3000 or sport = :3001 or sport = :3002 or sport = :3003 )' 2>/dev/null \
    | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  echo "rinzler active=$active journal-request-lines=$traffic non-idle-stats-lines=$busy remote-conns=$conns"
  if [ "${traffic:-0}" -ne 0 ] || [ "${busy:-0}" -ne 0 ] || [ "${conns:-0}" -ne 0 ]; then
    echo "rinzler serving looks in use - not touching it"; echo serving-in-use >"$MARKER"; exit 1
  fi
  echo "stopping idle rinzler serving per policy (nightly finished 11:18Z)"
  sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 || { echo stop-failed >"$MARKER"; exit 1; }
  sleep 5
  if ! fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null; then
    rm -f /dev/hugepages/slice-*-of-8
    echo "hugepage slices removed (fuser: no open handles)"
  fi
fi
grep -E '^HugePages_(Total|Free):' /proc/meminfo | xargs
if pgrep -x 'runtron(\.[a-z0-9]+)?' >/dev/null || pgrep -x 'rinzler(\.[a-z0-9]+)?' >/dev/null; then
  echo "another runtron/rinzler process is running - refusing to build"; pgrep -a 'runtron|rinzler'; echo busy >"$MARKER"; exit 1
fi

# Stage B: builds (perf-round pattern: pipefail so a failed compile is not
# masked by tail; cmp so canon != mirror is verified).
cd ~/workspace/tron-amx || { echo build-failed-cd >"$MARKER"; exit 1; }
echo "tree: $(git rev-parse --short HEAD) $(git status --short | tr '\n' ' ')"
build() {  # $1 = K_MIRROR value, $2 = output name
  nix develop --command bash -c \
    "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=$1 -DCMAKE_CXX_FLAGS= >/dev/null &&
     cmake --build gen --target rinzler -j96 2>&1 | tail -3" \
    || { echo "build-failed-$2" >"$MARKER"; exit 1; }
  cp gen/rinzler "gen/$2" || { echo "build-failed-cp-$2" >"$MARKER"; exit 1; }
  echo "built $2 $(date -u +%FT%TZ)"
}
build OFF rinzler.canon
build ON rinzler.mirror     # leaves gen/ in its usual mirror-ON configuration
if cmp -s gen/rinzler.canon gen/rinzler.mirror; then
  echo "canon and mirror binaries are byte-identical - build wiring broken"; echo build-identical >"$MARKER"; exit 1
fi
sha256sum gen/rinzler.canon gen/rinzler.mirror
./gen/rinzler.canon --version 2>&1 | head -2
echo ok >"$MARKER"
echo "=== build stage done $(date -u +%FT%TZ) ==="
