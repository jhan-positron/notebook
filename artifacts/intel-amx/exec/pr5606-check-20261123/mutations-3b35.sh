#!/usr/bin/env bash
# pr5606-check-20261123 mutation check. Runs ON delphi-3b35, by default in the option-OFF tree
# /var/tmp/jhan/b35-pr5606-off at state S2 (both commits of PR 5606). Uses our CPUs only (96-143, low priority), the fake device, no FPGA
# card, no huge page. Adapted from exec/pr5022-final-20261119/mutation-exit-code-3b35.sh.
#
# Question: does gen/t_amx_dispatch_dtype, as it runs in a build with TRON_AMX_DISPATCH=OFF, fail when the
# dispatch code in h/tron/models/self_attention.hpp is broken?
#
# Part 1, the faults of mutations.tsv. For each fault: mutate.py changes one line inside an
#   `#ifdef TRON_AMX_DISPATCH` region, the script rebuilds only t_amx_dispatch_dtype, runs it, records the diff
#   line, the exit code and the Catch2 summary, and restores the header with `git checkout --`.
#   A fault that does not compile is recorded as such. It does not count as a caught fault.
# Part 2, the define itself. The words `DEFINES TRON_AMX_DISPATCH` are removed from the registration line of the
#   test in t/CMakeLists.txt, at S2 (case m-define-S2) and at S1 (case m-define-S1, where the placeholder case
#   still exists). The script rebuilds, runs and records what happens.
# At the end the tree is back at S2 without changes, the four targets are rebuilt and the test runs again.
# The same restore runs when the script stops early (trap).
# Options for an extra run:
#   ONLY="id id+id ..."  the faults to apply. "a+b" applies two faults of mutations.tsv together (a control, not
#                        a one-line fault).
#   PART2=0              skips part 2.
#   OPT=on               uses the option-ON tree /var/tmp/jhan/b35-pr5606-on instead.
#   SUFFIX=-name         writes mutations-name.txt and mutations-name.done, so the first record is kept.
# Usage (on 3b35): [ONLY="m01-gate-inverted ..."] [PART2=0] [OPT=on] [SUFFIX=-extra] bash mutations-3b35.sh
# Record: exec/results/pr5606-check-20261123/mutations<SUFFIX>.txt; test logs in mutations/<opt><SUFFIX>-<id>.log. Marker: mutations<SUFFIX>.done.
# Logs: exec/logs/pr5606-check-20261123-mutations.log and -mutation-<opt><SUFFIX>-<id>-ninja.log.
set -u
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
only_3b35
OPT=${OPT:-off}
SUFFIX=${SUFFIX:-}
PART2=${PART2:-1}
WT=$(wt_of "$OPT") || { echo "OPT must be off or on"; exit 1; }
HDR=h/tron/models/self_attention.hpp
CML=t/CMakeLists.txt
TSV=$HERE/mutations.tsv
OUT=$RES/mutations$SUFFIX.txt
DONE=$RES/mutations$SUFFIX.done
LOG=$LOGDIR/$NAME-mutations.log
# the targets that build-3b35.sh built in this tree
if [ "$OPT" = off ]; then ALL_TARGETS='t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_page_share_counters'
else ALL_TARGETS='t_amx_dispatch_dtype t_amx_numerics t_llama_unit'; fi
N_SECTIONS=9   # SECTION blocks of the test case in t/t_amx_dispatch_dtype.cpp
mkdir -p "$RES/mutations" "$LOGDIR"
rm -f "$DONE"
exec {LOCK_FD}>"$WT/gen/keep/build.lock"
flock -n "$LOCK_FD" || { echo "another build or mutation run uses $WT"; exit 1; }
# build <id> [targets]: rebuilds, full ninja output in its own log
build() {
  local id=$1; shift
  local targets=${*:-t_amx_dispatch_dtype}
  # shellcheck disable=SC2086
  ( cd "$WT" >/dev/null 2>&1 && $PIN cmake --build gen --target $targets -j"$JOBS" ) >"$LOGDIR/$NAME-mutation-$OPT$SUFFIX-$id-ninja.log" 2>&1
}
restore() {
  git -C "$WT" checkout -- "$HDR" "$CML" >>"$LOG" 2>&1
  [ "$(git -C "$WT" rev-parse HEAD)" = "$S2" ] || git -C "$WT" checkout --detach "$S2" >>"$LOG" 2>&1
  # shellcheck disable=SC2086
  build restore $ALL_TARGETS
}
on_exit() { restore; echo "failed: stopped early" >"$DONE"; }
trap on_exit EXIT
# runtest <id>: prints the exit code, the Catch2 summary lines and the failed sections
runtest() {
  local id=$1 f=$RES/mutations/$OPT$SUFFIX-$1.log rc
  ( cd "$WT" >/dev/null 2>&1 && $PIN env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 600 gen/t_amx_dispatch_dtype --skip-benchmarks ) >"$f" 2>&1
  rc=$?
  echo "  run: exit code $rc | $(grep -E '^(test cases|assertions|All tests passed)' "$f" | tr -s ' ' | tr '\n' ';')"
  [ $rc -eq 0 ] || python3 "$HERE/catch-failures.py" "$f" "$N_SECTIONS" | sed 's/^/  /'
  return $rc
}
define_count() {   # how often the define appears in the compile command of the test's translation unit
  python3 "$HERE/compile-commands.py" "$WT" | grep -A1 'commands for t/t_amx_dispatch_dtype.cpp' | tail -1 | sed 's/^ *//'
}
caught=0; survived=0; nocompile=0
{
  echo "# mutation check on $(hostname), started $(ts); build tree $WT; option $(grep -E '^TRON_AMX_DISPATCH:' "$WT/gen/CMakeCache.txt")"
  echo "# load average $(cut -d' ' -f1-3 /proc/loadavg)"
  [ "$(git -C "$WT" rev-parse HEAD)" = "$S2" ] || { echo "the tree is not at S2 $S2"; exit 1; }
  [ -z "$(dirty_of "$WT")" ] || { echo "the tree has changes"; exit 1; }
  echo "tree before: HEAD $(git -C "$WT" rev-parse HEAD), git tree hash $(git -C "$WT" rev-parse 'HEAD^{tree}') (S2: $S2_TREE)"
  SHA_BEFORE=$(sha256sum "$WT/gen/t_amx_dispatch_dtype" | cut -c1-64)
  echo "sha256 of gen/t_amx_dispatch_dtype before: $SHA_BEFORE"
  echo
  echo "== unmutated"
  runtest unmutated
  echo
  echo "== part 1: one-line faults in $HDR"
  for id in ${ONLY:-$(python3 "$HERE/mutate.py" ids "$TSV")}; do
    echo "== $id: $(for part in ${id//+/ }; do python3 "$HERE/mutate.py" effect "$TSV" "$part"; done | paste -sd'|' | sed 's/|/ AND /g')"
    for part in ${id//+/ }; do python3 "$HERE/mutate.py" apply "$TSV" "$part" "$WT" | sed 's/^/  /'; done
    if [ -z "$(git -C "$WT" diff --name-only -- "$HDR")" ]; then echo "  NOT APPLIED"; continue; fi
    git -C "$WT" diff -U0 -- "$HDR" | grep -E '^[+-] ' | sed 's/^/    /'
    echo "  changed files: $(git -C "$WT" status --porcelain | tr '\n' ' ')"
    t0=$(date +%s)
    if build "$id"; then
      echo "  build: ok in $(( $(date +%s) - t0 )) s; sha256 of the binary $(sha256sum "$WT/gen/t_amx_dispatch_dtype" | cut -c1-16)"
      if runtest "$id"; then echo "  RESULT: NOT CAUGHT (the test passes with the fault)"; survived=$((survived + 1))
      else echo "  RESULT: caught"; caught=$((caught + 1)); fi
    else
      echo "  build: FAILED in $(( $(date +%s) - t0 )) s. This fault does not compile, so it does not count."
      grep -E 'error:' "$LOGDIR/$NAME-mutation-$OPT$SUFFIX-$id-ninja.log" | sed -n 1,3p | sed "s|$WT/||g" | cut -c1-300 | sed 's/^/    /'
      nocompile=$((nocompile + 1))
    fi
    git -C "$WT" checkout -- "$HDR"
    [ -z "$(dirty_of "$WT")" ] || { echo "restore of $HDR failed"; exit 1; }
  done
  echo
  echo "part 1 totals: caught $caught, not caught $survived, did not compile $nocompile"
  echo
  [ "$PART2" = 1 ] && echo "== part 2: the define of the test registration in $CML"
  for st in $([ "$PART2" = 1 ] && echo "S2 S1"); do
    id=m-define-$st
    echo "== $id: 'DEFINES TRON_AMX_DISPATCH' removed from the registration line, at state $st"
    sha=$(sha_of $st)
    [ "$(git -C "$WT" rev-parse HEAD)" = "$sha" ] || git -C "$WT" checkout --detach "$sha" >>"$LOG" 2>&1
    echo "  tree at $(git -C "$WT" rev-parse HEAD)"
    n=$(grep -c 'add_catch_test(NAME t_amx_dispatch_dtype DEFINES TRON_AMX_DISPATCH LIBRARIES' "$WT/$CML")
    [ "$n" = 1 ] || { echo "  the registration line was found $n times, wanted 1"; exit 1; }
    sed -i 's|add_catch_test(NAME t_amx_dispatch_dtype DEFINES TRON_AMX_DISPATCH LIBRARIES|add_catch_test(NAME t_amx_dispatch_dtype LIBRARIES|' "$WT/$CML"
    git -C "$WT" diff -U0 -- "$CML" | grep -E '^[+-][^+-]' | sed 's/^/    /'
    echo "  changed files: $(git -C "$WT" status --porcelain | tr '\n' ' ')"
    t0=$(date +%s)
    if build "$id"; then
      echo "  build: ok in $(( $(date +%s) - t0 )) s; sha256 of the binary $(sha256sum "$WT/gen/t_amx_dispatch_dtype" | cut -c1-16)"
      echo "  compile command now: $(define_count)"
      if runtest "$id"; then echo "  RESULT: the test PASSES without the define"; else echo "  RESULT: the test fails without the define"; fi
    else
      echo "  build: FAILED in $(( $(date +%s) - t0 )) s"
      grep -E 'error:|undefined reference|undefined symbol' "$LOGDIR/$NAME-mutation-$OPT$SUFFIX-$id-ninja.log" | sed -n 1,5p | sed "s|$WT/||g" | cut -c1-300 | sed 's/^/    /'
    fi
    git -C "$WT" checkout -- "$CML"
    [ -z "$(dirty_of "$WT")" ] || { echo "restore of $CML failed"; exit 1; }
  done
  echo
  echo "== restore"
  trap - EXIT
  restore
  echo "restored: HEAD $(git -C "$WT" rev-parse HEAD) ($([ "$(git -C "$WT" rev-parse HEAD)" = "$S2" ] && echo "is S2" || echo "is NOT S2")); git tree hash $(git -C "$WT" rev-parse 'HEAD^{tree}')"
  echo "git status --porcelain: $(dirty_of "$WT" | wc -l) lines"
  SHA_AFTER=$(sha256sum "$WT/gen/t_amx_dispatch_dtype" | cut -c1-64)
  echo "sha256 of gen/t_amx_dispatch_dtype after: $SHA_AFTER ($([ "$SHA_AFTER" = "$SHA_BEFORE" ] && echo "same binary as before" || echo "binary DIFFERS from before"))"
  echo "compile command now: $(define_count)"
  for tg in $ALL_TARGETS; do echo "sha256 after the restore: $(sha256sum "$WT/gen/$tg" | cut -c1-64)  gen/$tg"; done
  runtest restored
  echo "# finished $(ts)"
} >"$OUT" 2>&1
cat "$OUT"
grep -q '^# finished' "$OUT" && echo ok >"$DONE" || echo failed >"$DONE"
