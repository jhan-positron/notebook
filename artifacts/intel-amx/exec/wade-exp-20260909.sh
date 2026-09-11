#!/usr/bin/env bash
# wade-exp-20260909.sh: measurements for Wade's question on PR 4265
# (discussion r3970127694): can t_kv_footprint_memorder be folded into
# t_llama_unit by putting _GLIBCXX_ASSERTIONS on that target?
#
# Runs on delphi-3bda, socket 1 only (jhan's half), in a fresh worktree of the
# PR head on local disk. Waits for the other session's queued perf campaigns
# (qwen8u8k-pr1-half, then gptoss120b-pr1-half) so their TPS numbers are not
# disturbed, then takes the campaign guard (flock + lease + other-user check).
#
# Steps (the inner script does E1-E4 inside `nix develop`):
#  E1 baseline: build t_llama_unit + t_kv_footprint_memorder as the PR defines
#     them; run each 3x; record the Catch2 summary, wall time, max RSS.
#  E2 fold cost: recompile t_llama_unit.cpp with -D_GLIBCXX_ASSERTIONS (fixed
#     header), relink with the recorded link line; run 3x. Anything else that
#     fires under the define shows up here, and so does the time/RSS delta.
#  E3 detection: same as E2 but with main's kv_cache.hpp (the release load,
#     `git show a80b102c18`) first on the include path; run the whole binary
#     (expect SIGABRT) and every test case alone (which cases detect it);
#     control: wrong header WITHOUT the define (expect pass); sanity: the PR's
#     own test with the wrong header (expect fail).
#  E4 symbols: book constructor instantiations in the E2 object vs libtron.a,
#     and the lld link map (which input file provides each constructor).
# Output: exec/logs/wade-exp.{log,txt,done}; per-run outputs exec/logs/wade-exp-*.out
set -u
EXEC=~/workspace/intel-AMX/exec
COMMIT=${COMMIT:-7a7699b338}
BASE=${BASE:-a80b102c18}
TAG=wade-exp
LOG=$EXEC/logs/$TAG.log; OUT=$EXEC/logs/$TAG.txt; MARKER=$EXEC/logs/$TAG.done
WT=/var/tmp/jhan/tron-$TAG
X=/var/tmp/jhan/$TAG-work
OUR_CPUS=72-143,216-287          # socket 1 (NUMA node 1) on delphi-3bda
export SYSTEM_CONFIG="--instance 1,2"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p $EXEC/logs
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== $TAG queued $(date -u +%FT%TZ) commit=$COMMIT base=$BASE host=$(hostname) ==="
source "$EXEC/lib-guard.sh"

# 1. Wait for the other session's campaign chain (its last member writes
#    gptoss120b-pr1-half.done; it waits for the qwen run itself).
deadline=$(( $(date +%s) + 12*3600 ))
until [ -s "$EXEC/logs/gptoss120b-pr1-half.done" ]; do
  [ "$(date +%s)" -ge "$deadline" ] && { echo campaigns-never-done >"$MARKER"; exit 1; }
  echo "$(date -u +%FT%TZ) waiting for gptoss120b-pr1-half.done (prep=$(cat $EXEC/logs/qwen8u8k-prep.done 2>/dev/null) qwen=$(cat $EXEC/logs/qwen8u8k-pr1-half.done 2>/dev/null))"
  sleep 300
done
echo "=== campaigns done $(date -u +%FT%TZ): gptoss120b marker=$(cat $EXEC/logs/gptoss120b-pr1-half.done) ==="

# 2. Guard: CI lease, other users, blackout; then the cross-session flock.
wait_for_dut_free 43200 || { echo dut-never-free >"$MARKER"; exit 1; }
deadline=$(( $(date +%s) + 43200 ))
until campaign_guard_acquire; do
  [ "$(date +%s)" -ge "$deadline" ] && { echo guard-never-free >"$MARKER"; exit 1; }
  sleep 120
  wait_for_dut_free 43200 || { echo dut-never-free >"$MARKER"; exit 1; }
done
echo "=== guard acquired $(date -u +%FT%TZ) ==="
PIN="nice -n10 taskset -c $OUR_CPUS"
cleanup() {
  cd ~/workspace/tron-amx && git worktree remove --force "$WT" 2>/dev/null
  campaign_guard_release
}
cd ~/workspace/tron-amx || { echo no-checkout >"$MARKER"; campaign_guard_release; exit 1; }
git worktree remove --force "$WT" 2>/dev/null
git worktree prune
git worktree add --detach "$WT" "$COMMIT" || { echo worktree-failed >"$MARKER"; campaign_guard_release; exit 1; }
trap cleanup EXIT
rm -rf "$X"; mkdir -p "$X"
cd "$WT" || exit 1
: >"$OUT"
echo "commit $(git rev-parse HEAD) $(git log -1 --format=%s)" >>"$OUT"
echo "base   $BASE (main at the PR base: the release load)" >>"$OUT"
echo "host $(hostname) cpus=$OUR_CPUS SYSTEM_CONFIG=\"$SYSTEM_CONFIG\" cpu=$(lscpu | sed -n 's/^Model name: *//p' | head -1)" >>"$OUT"
t0=$(date +%s)
$PIN nix develop --command bash -c \
  "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DCMAKE_CXX_FLAGS= 2>&1 | tail -3 &&
   cmake --build gen --target t_llama_unit t_kv_footprint_memorder -j96 2>&1 | grep -E 'error|FAILED' | sed -n 1,40p; exit \${PIPESTATUS[0]}"
rc=$?
echo "build rc=$rc in $(( $(date +%s) - t0 )) s" >>"$OUT"
if [ $rc -ne 0 ]; then echo build-failed >"$MARKER"; exit 1; fi
if ci_took_dut; then echo "=== DUT taken after the build; not running ==="; echo ci-took-dut >"$MARKER"; exit 1; fi
$PIN nix develop --command bash "$EXEC/wade-exp-inner-20260909.sh" "$WT" "$X" "$BASE" "$OUT" "$EXEC/logs"
irc=$?
echo "inner rc=$irc; finished $(date -u +%FT%TZ)" >>"$OUT"
if [ $irc -ne 0 ] || grep -q "FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
