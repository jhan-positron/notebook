#!/usr/bin/env bash
# Post-CI verification of the mirror-eligibility gate change (2026-08-25):
# wait for System CI to release the DUT, rinzler-policy cleanup, then build
# the MIRROR config (gen/ as configured) and run the AMX unit tests +
# t_llama_unit; then reconfigure CANONICAL, build the same tests, run them,
# and reconfigure back to mirror. Marker + log as usual.
set -u
EXEC=~/workspace/intel-AMX/exec
LOG=$EXEC/logs/p2-verify-after-ci.log
MARKER=$EXEC/logs/p2-verify-after-ci.done
OUT=$EXEC/logs/p2-verify-after-ci.txt
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== verify-after-ci queued $(date -u +%FT%TZ) ==="
source "$EXEC/lib-guard.sh"
wait_for_ci_release 28800 || { echo ci-never-released >"$MARKER"; exit 1; }
echo "=== CI released $(date -u +%FT%TZ) ==="
# rinzler policy: stop only if idle (sudo journal + non-loopback conns)
if rinzler_active; then
  traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null | grep -icE 'session|request|prompt|generat|token') || true
  conns=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 )' 2>/dev/null | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  if [ "${traffic:-0}" -eq 0 ] && [ "${conns:-0}" -eq 0 ]; then
    sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 && sleep 5
    fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null || rm -f /dev/hugepages/slice-*-of-8
    echo "rinzlers stopped per policy (idle)"
  else
    echo "serving in use (journal=$traffic conns=$conns) - building pinned/niced instead"
  fi
fi
if rinzler_active; then J="-j6"; PIN="nice -n19 taskset -c 23,24,36,167,168,180"; else J="-j96"; PIN=""; fi
if ! campaign_guard_acquire --allow-serving; then echo guard-refused >"$MARKER"; exit 1; fi
cd ~/workspace/tron-amx
: >"$OUT"
run_tests() {  # $1 = label
  for t in t_amx_arena_leak t_amx_mirror t_amx_numerics t_llama_unit; do
    printf "%s %s: " "$1" "$t" >>"$OUT"
    $PIN ./gen/$t 2>/dev/null | grep -E "All tests passed|FAILED|failed|assertions" | tail -1 >>"$OUT" || echo "NO-RESULT" >>"$OUT"
  done
}
build() {  # $1 = K_MIRROR value
  $PIN nix develop --command bash -c \
    "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=$1 -DCMAKE_CXX_FLAGS= >/dev/null &&
     cmake --build gen --target t_amx_arena_leak t_amx_mirror t_amx_numerics t_llama_unit runtron $J 2>&1 | grep -E 'error|FAILED|warning: unused' | head -20; exit \${PIPESTATUS[0]}"
}
echo "### mirror build $(date -u +%FT%TZ)" >>"$OUT"
build ON && run_tests mirror || echo "mirror BUILD FAILED" >>"$OUT"
echo "### canonical build $(date -u +%FT%TZ)" >>"$OUT"
build OFF && run_tests canonical || echo "canonical BUILD FAILED" >>"$OUT"
echo "### restore mirror config $(date -u +%FT%TZ)" >>"$OUT"
build ON >/dev/null 2>&1 || echo "restore-build FAILED" >>"$OUT"
campaign_guard_release
if grep -qE "FAILED|NO-RESULT" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== verify-after-ci done $(date -u +%FT%TZ) ==="
