#!/usr/bin/env bash
# Post-CI verification on delphi-3bda of the AMX Q-scalar gate (codex P1 on
# PR #3879, 2026-08-28). Builds the given commit in an ISOLATED worktree on
# local disk: ~/workspace/tron-amx and its gen/ are NFS-shared with
# alpha/claude-box and may be mid-edit there, so nothing here touches them.
#
#   phase 1  mirror config    (TRON_AMX_K_MIRROR=ON):  unit tests + t_llama_unit
#                              + t_generate_host (llama-3-8b-host, 400 tokens =
#                              6 dense pages, HF golden logits; the executor that
#                              hit the bug) + t_amx_logit_ab A/B on
#                              llama-3-8b-host if that binary exists (the two
#                              dumps must be identical: host never takes AMX).
#   phase 2  canonical config (TRON_AMX_K_MIRROR=OFF): same tests.
#   phase 3  NEGATIVE CONTROL: the five gate headers from the unfixed base
#                              commit with t_generate_host -> expected FAILED.
#
# Usage: p3-q-scalar-gate.sh <commit-sha> [<unfixed-base-sha>]   (marker + log as usual)
#   The negative control checks out the five gate headers from <unfixed-base-sha>
#   (default 609dabba83, the PR head before any codex fix).
set -u
EXEC=~/workspace/intel-AMX/exec
TAG=p3-q-scalar-gate
LOG=$EXEC/logs/$TAG.log
MARKER=$EXEC/logs/$TAG.done
OUT=$EXEC/logs/$TAG.txt
COMMIT=${1:?usage: $0 <commit-sha> [unfixed-base-sha]}
BASE=${2:-609dabba83}
WT=/var/tmp/jhan/tron-$TAG
FIX_FILES="h/tron/kernels/amx_attn_iface.hpp h/tron/models/self_attention.hpp h/tron/models/model.hpp h/tron/models/kv_cache.hpp h/tron/scheduler/full.hpp"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== $TAG queued $(date -u +%FT%TZ) commit=$COMMIT host=$(hostname) ==="
source "$EXEC/lib-guard.sh"
wait_for_ci_release 28800 || { echo ci-never-released >"$MARKER"; exit 1; }
echo "=== CI released $(date -u +%FT%TZ) ==="
# rinzler policy (as p2-verify-after-ci.sh): stop only if idle.
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
if rinzler_active; then J="-j6"; PIN="nice -n19 taskset -c 23,24,36,167,168,180"; else J="-j96"; PIN="nice -n10"; fi
if ! campaign_guard_acquire --allow-serving; then echo guard-refused >"$MARKER"; exit 1; fi
cleanup() {
  cd ~/workspace/tron-amx && git worktree remove --force "$WT" 2>/dev/null
  campaign_guard_release
}
cd ~/workspace/tron-amx || { echo no-checkout >"$MARKER"; campaign_guard_release; exit 1; }
git worktree remove --force "$WT" 2>/dev/null
git worktree add --detach "$WT" "$COMMIT" || { echo worktree-failed >"$MARKER"; campaign_guard_release; exit 1; }
trap cleanup EXIT
cd "$WT" || exit 1
: >"$OUT"
echo "commit $(git rev-parse HEAD) $(git log -1 --format=%s)" >>"$OUT"

TESTS="t_amx_arena_leak t_amx_mirror t_amx_numerics t_llama_unit t_generate_host"
build() {  # $1 = K_MIRROR value, $2.. = targets. INGEST OFF: the worktree has no
           # ingest/traces (git-ignored) and t_generate_host uses the hand-written
           # llama_3_8b plugin, tag test, compiled regardless.
  local mirror=$1; shift
  $PIN nix develop --command bash -c \
    "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=$mirror -DCMAKE_CXX_FLAGS= >/dev/null &&
     cmake --build gen --target $* $J 2>&1 | grep -E 'error|FAILED' | head -20; exit \${PIPESTATUS[0]}"
}
run_tests() {  # $1 = label
  for t in $TESTS; do
    printf "%s %s: " "$1" "$t" >>"$OUT"
    $PIN ./gen/$t 2>/dev/null | grep -E "All tests passed|FAILED|failed|assertions" | tail -1 >>"$OUT" || echo "NO-RESULT" >>"$OUT"
  done
  # host must never take the AMX path: the AMX-on and AMX-off logit dumps of
  # llama-3-8b-host must be byte-identical after the fix.
  if [ -x ./gen/t_amx_logit_ab ]; then
    AMX_MODEL=llama-3-8b-host AMX_LOGIT_OUT=/var/tmp/jhan/$TAG-avx.bin TRON_AMX_DISABLE=1 $PIN ./gen/t_amx_logit_ab >/dev/null 2>&1
    AMX_MODEL=llama-3-8b-host AMX_LOGIT_OUT=/var/tmp/jhan/$TAG-amx.bin TRON_AMX_DISABLE=0 $PIN ./gen/t_amx_logit_ab >/dev/null 2>&1
    if cmp -s /var/tmp/jhan/$TAG-avx.bin /var/tmp/jhan/$TAG-amx.bin; then
      echo "$1 logit_ab llama-3-8b-host: dumps identical (host never takes AMX)" >>"$OUT"
    else
      echo "$1 logit_ab llama-3-8b-host: dumps DIFFER - FAILED" >>"$OUT"
    fi
  else
    echo "$1 logit_ab: binary not built (INGEST off) - skipped" >>"$OUT"
  fi
}
echo "### phase 1 mirror build $(date -u +%FT%TZ)" >>"$OUT"
build ON $TESTS runtron && run_tests mirror || echo "mirror BUILD FAILED" >>"$OUT"
ci_took_dut && { echo "CI took the DUT after phase 1" >>"$OUT"; echo ci-interrupted >"$MARKER"; exit 2; }
echo "### phase 2 canonical build $(date -u +%FT%TZ)" >>"$OUT"
build OFF $TESTS runtron && run_tests canonical || echo "canonical BUILD FAILED" >>"$OUT"
ci_took_dut && { echo "CI took the DUT after phase 2" >>"$OUT"; echo ci-interrupted >"$MARKER"; exit 2; }
echo "### phase 3 NEGATIVE CONTROL: unfixed headers from $BASE, t_generate_host must FAIL $(date -u +%FT%TZ)" >>"$OUT"
git checkout "$BASE" -- $FIX_FILES && git diff --stat "$COMMIT" -- $FIX_FILES | tail -1 >>"$OUT"
if build OFF t_generate_host; then
  # Keep stderr (Catch2 reports a fatal signal there), disable core dumps
  # (apport spent 25 min on a 6 GB core on 2026-08-28), bound the run, and
  # record the exit code: the unfixed gate must make this fail or abort.
  printf "negative t_generate_host: " >>"$OUT"
  ( ulimit -c 0; $PIN timeout 20m ./gen/t_generate_host 2>&1 | grep -E "All tests passed|FAILED|failed|assertions|SIGABRT|fatal" | tail -2 | tr "\n" " "; echo "exit=${PIPESTATUS[0]}" ) >>"$OUT"
  echo "(expected outcome: a Catch2 failure or a nonzero exit; 134 = SIGABRT)" >>"$OUT"
else
  echo "negative BUILD FAILED" >>"$OUT"
fi
git checkout "$COMMIT" -- $FIX_FILES
echo "### done $(date -u +%FT%TZ)" >>"$OUT"
# Verdict: phases 1-2 must have no FAILED/NO-RESULT; phase 3 must show a
# failure or a nonzero exit (the annotation lines carry no such words).
if sed -n '/phase 1/,/phase 3/p' "$OUT" | grep -qE "FAILED|NO-RESULT|DIFFER"; then echo check-output >"$MARKER"
elif ! grep "^negative t_generate_host:" "$OUT" | grep -qE "FAILED|failed|SIGABRT|exit=[1-9]"; then echo negative-control-did-not-fail >"$MARKER"
else echo ok >"$MARKER"; fi
echo "=== $TAG done $(date -u +%FT%TZ) marker=$(cat "$MARKER") ==="
