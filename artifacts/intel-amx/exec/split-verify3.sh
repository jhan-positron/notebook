#!/usr/bin/env bash
# Build + test one commit of the PR 3879 split on delphi-3bda in an ISOLATED
# worktree on local disk (the NFS checkouts may be mid-edit elsewhere).
#
# v3 (2026-09-06 22:xx UTC): the machine is shared with Bill by halves
# (~/workspace/notebook/handoffs/delphi-3bda-guard.md): Bill has the first
# four FPGA cards and socket 0, jhan has the second four cards and socket 1
# (`--instance 1,2`). Consequences for this script, compared with v2:
#   - the build and the tests are pinned to the socket-1 cores
#     (NUMA node 1 = cpus 72-143,216-287 on the Xeon 6962P);
#   - the tests run WITH SYSTEM_CONFIG="--instance 1,2" (v2 unset it). The
#     tests here are `fake`-labelled host tests: pos_fake's pos_startup() only
#     parses SYSTEM_CONFIG for the core set and never opens a hugepage slice
#     file (src/pos/fake.cpp pos_startup_host; the hugepage heap setup in
#     src/system/memory.cpp is the real driver's path), so the setting only
#     keeps their threads on our socket;
#   - the guard must ignore Bill's activity: the launcher exports
#     GUARD_EXCLUDE_USERS="jhan nobody positron packer bill" (the guard doc's
#     fix 2); the CI lease and any third person still block;
#   - rule 1 of the guard doc ("any rinzler@N active: do not launch") is
#     followed literally: no --allow-serving, no light build next to serving;
#     the step waits (up to 12 h) until serving stops;
#   - BENCH= is no longer run here. `bin/slice bench --update` launches the
#     test under --instance i,n for every slot of the box, i.e. also on Bill's
#     half, and the guard doc allows whole-machine measurements only when Bill
#     is not using the machine. KEEP_WT=1 keeps the worktree so that
#     split-bench3.sh can run the bench later under the default guard;
#   - advisory pre-CI hold: no step STARTS its build between 01:40 and 03:45
#     UTC (the nightly prep starts at 02:45, the lease appears about 03:37; a
#     step takes up to about 50 min); between build and tests the step also
#     stops if the lease or serving appeared meanwhile (marker ci-took-dut).
#   - each test binary runs under `timeout -k 60 2400` (40 min).
#
# Usage: split-verify3.sh <label> <commit> <DISPATCH ON|OFF> <K_MIRROR ON|OFF> \
#                         <PAGE_SHARE ON|OFF> <test> [<test>...]
# Env: FORMAT=1   run clang-format-19 on the C++ files the commit changes vs its
#                 merge base with origin/main; save the patch; build the
#                 formatted tree.
#      KEEP_WT=1  do not remove the worktree at exit (split-bench3.sh uses it).
# Output: exec/logs/split-<label>.{log,txt,done}; the .txt has one line per
# test binary with the Catch2 summary line, plus the build result; the full
# output of each test is exec/logs/split-<label>-<test>.out.
set -u
EXEC=~/workspace/intel-AMX/exec
LABEL=${1:?label}; COMMIT=${2:?commit}; DISPATCH=${3:?}; MIRROR=${4:?}; PSC=${5:?}; shift 5
TESTS="$*"
TAG=split-$LABEL
LOG=$EXEC/logs/$TAG.log; MARKER=$EXEC/logs/$TAG.done; OUT=$EXEC/logs/$TAG.txt
WT=/var/tmp/jhan/tron-$TAG
OUR_CPUS=72-143,216-287          # socket 1 (NUMA node 1) on delphi-3bda
OUR_INSTANCE="--instance 1,2"    # slices 4-7 = the second half of the machine
HOLD_FROM=${PRECI_HOLD_FROM:-140}; HOLD_TO=345   # UTC hhmm, see header
mkdir -p $EXEC/logs
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== $TAG queued $(date -u +%FT%TZ) commit=$COMMIT DISPATCH=$DISPATCH MIRROR=$MIRROR PSC=$PSC host=$(hostname) GUARD_EXCLUDE_USERS=${GUARD_EXCLUDE_USERS:-<default>} ==="
source "$EXEC/lib-guard.sh"
# Advisory clock hold (see header). 10#: "0210" would otherwise be read as octal.
preci_hold() {
  local hm
  while :; do
    hm=$((10#$(date -u +%H%M)))
    if [ "$hm" -ge "$HOLD_FROM" ] && [ "$hm" -lt "$HOLD_TO" ]; then
      echo "=== pre-CI hold $(date -u +%FT%TZ): not starting between $HOLD_FROM and $HOLD_TO UTC ==="
      sleep 300
    else
      break
    fi
  done
}
preci_hold
wait_for_dut_free 43200 || { echo dut-never-free >"$MARKER"; exit 1; }
echo "=== DUT free $(date -u +%FT%TZ) ==="
deadline=$(( $(date +%s) + 43200 ))
until preci_hold; campaign_guard_acquire; do
  [ "$(date +%s)" -ge "$deadline" ] && { echo guard-never-free >"$MARKER"; exit 1; }
  sleep 120
  wait_for_dut_free 43200 || { echo dut-never-free >"$MARKER"; exit 1; }
done
J="-j96"; PIN="nice -n10 taskset -c $OUR_CPUS"
echo "=== guard acquired $(date -u +%FT%TZ); PIN='$PIN' J=$J ==="
cleanup() {
  if [ "${KEEP_WT:-0}" = "1" ]; then echo "=== worktree kept at $WT (KEEP_WT=1) ==="
  else cd ~/workspace/tron-amx && git worktree remove --force "$WT" 2>/dev/null; fi
  campaign_guard_release
}
cd ~/workspace/tron-amx || { echo no-checkout >"$MARKER"; campaign_guard_release; exit 1; }
git worktree remove --force "$WT" 2>/dev/null
git worktree prune
git worktree add --detach "$WT" "$COMMIT" || { echo worktree-failed >"$MARKER"; campaign_guard_release; exit 1; }
trap cleanup EXIT
cd "$WT" || exit 1
: >"$OUT"
echo "commit $(git rev-parse HEAD) $(git log -1 --format=%s)" >>"$OUT"
echo "config DISPATCH=$DISPATCH K_MIRROR=$MIRROR PAGE_SHARE_COUNTERS=$PSC" >>"$OUT"
echo "placement cpus=$OUR_CPUS SYSTEM_CONFIG=\"$OUR_INSTANCE\" host=$(hostname) cpu=$(lscpu | sed -n 's/^Model name: *//p' | head -1)" >>"$OUT"
# FORMAT=1: run the repo's clang-format on every C++ file this commit changes
# against its merge base with origin/main, save the resulting patch next to the
# log, and build the FORMATTED tree (whitespace only). The patch is applied to
# the branch later.
if [ "${FORMAT:-0}" = "1" ]; then
  FILES=$(git diff --name-only --diff-filter=d $(git merge-base origin/main HEAD) HEAD -- '*.cpp' '*.hpp' | tr '\n' ' ')
  $PIN nix develop --command bash -c "clang-format-19 -i $FILES" 2>&1 | tail -3
  git diff > "$EXEC/logs/$TAG-format.patch"
  echo "format patch: $(git diff --numstat | awk '{a+=$1;d+=$2} END {print a"+/"d"-"}') lines -> exec/logs/$TAG-format.patch" >>"$OUT"
fi
# Only pass options the tree defines (PR 0 defines TRON_PAGE_SHARE_COUNTERS, the
# rebased full tree does not); an unknown option is only a CMake warning.
# pipefail: a configure failure stops the && chain; `sed -n 1,40p` (not head)
# reads to EOF so ninja never dies of SIGPIPE; the exit is ninja's own status.
OPTS="-DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=$DISPATCH -DTRON_AMX_K_MIRROR=$MIRROR -DTRON_PAGE_SHARE_COUNTERS=$PSC"
t0=$(date +%s)
$PIN nix develop --command bash -c \
  "set -o pipefail; cmake --preset cross-avx512 $OPTS -DCMAKE_CXX_FLAGS= 2>&1 | tail -3 &&
   cmake --build gen --target $TESTS $J 2>&1 | grep -E 'error|FAILED|warning: unused' | sed -n 1,40p; exit \${PIPESTATUS[0]}"
rc=$?
echo "build rc=$rc in $(( $(date +%s) - t0 )) s" >>"$OUT"
if [ $rc -ne 0 ]; then echo build-failed >"$MARKER"; exit 1; fi
# The lease is the authority: if CI or serving took the machine during the
# build, do not run the tests now (re-queue this step later).
if ci_lease_busy || rinzler_active; then
  echo "CI lease or rinzler serving appeared during the build; tests not run" >>"$OUT"
  echo ci-took-dut >"$MARKER"; exit 1
fi
for t in $TESTS; do
  printf "%s: " "$t" >>"$OUT"
  if [ -x ./gen/$t ]; then
    $PIN env SYSTEM_CONFIG="$OUR_INSTANCE" timeout -k 60 2400 ./gen/$t > "$EXEC/logs/$TAG-$t.out" 2>&1
    trc=$?
    line=$(grep -E "All tests passed|FAILED|failed|assertions|test cases" "$EXEC/logs/$TAG-$t.out" | tail -1)
    echo "${line:-NO-RESULT}" >>"$OUT"
    [ $trc -ne 0 ] && echo "  (exit code $trc$( [ $trc -eq 124 ] && echo ', timeout 2400 s'))" >>"$OUT"
    grep -m1 -i "AMX unavailable" "$EXEC/logs/$TAG-$t.out" >/dev/null && echo "  (printed 'AMX unavailable')" >>"$OUT"
  else
    echo "NO-BINARY" >>"$OUT"
  fi
done
echo "=== done $(date -u +%FT%TZ) ==="
echo ok >"$MARKER"
