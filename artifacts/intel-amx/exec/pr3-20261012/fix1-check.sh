#!/usr/bin/env bash
# fix1-check (runs ON delphi-3bda, our half, detached): the review-round-1 test fix of PR-3 (the three-thread section of the
# save_k case reads the finished count as the main call returns, with a late helper). Steps, all in the existing worktrees:
#   A1. /var/tmp/jhan/tron-pr3 (option on): checkout COMMIT, rebuild t_llama_unit only, run the save_k case alone, then the
#       whole binary (must pass; the counts are recorded).
#   M3. mutation check of the production join: `while (w.finished.load(std::memory_order_acquire) < n_helpers) {` ->
#       `while (false) {` in h/tron/models/model.hpp (main no longer waits for the helpers); rebuild t_llama_unit; the save_k
#       case must fail at `REQUIRE( finished_at_return == n_workers - 1 )`; restore; rebuild; the whole binary passes again.
#   B1. /var/tmp/jhan/tron-pr3rm (option off): checkout COMMIT, rebuild t_llama_unit, run the save_k case and the whole binary.
#   A3b. /var/tmp/jhan/tron-pr3nd (option on, dispatch off): the same.
#   F1. clang-format on the changed file and git diff --check against PR2_COMMIT (nix shell).
# Light-ish work next to serving: every build waits for the CI lease (600 s grace) and for other people.
# Usage (on 3bda): COMMIT=<full sha of the fix head> PR2_COMMIT=<full sha> bash fix1-check.sh
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
export NAME=pr3-20261012
RES=$EXEC/results/$NAME/fix1
LOG=$EXEC/logs/$NAME-fix1.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?}; PR2_COMMIT=${PR2_COMMIT:?}
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
SAVEK_CASE="save_k stores every token's K row once\, grouped by page block\, alone or with helper threads"
mkdir -p "$RES"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 210 ] && [ "$hm" -lt 345 ]; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do [ $w = 0 ] && echo "$(ts) waiting before $1"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
summary_of() { grep -E 'test cases:|assertions|All tests passed|FAILED' "$1" | tr '\n' ' ' | cut -c1-400; }
passed_line() { grep -oE 'All tests passed \([0-9]+ assertions? in [0-9]+ test cases?\)' "$1"; }
build_llama() {  # build_llama <worktree> <label>
  ( cd "$1" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'cmake --build gen --target t_llama_unit -j48 2>&1 | grep -E "error|FAILED|warning:" | head -10; echo "'"$2"' build rc=${PIPESTATUS[0]}"' )
}
run_llama() {  # run_llama <worktree> [spec]
  ( cd "$1" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 3600 ./gen/t_llama_unit --skip-benchmarks "${2-}" )
}
checkout() {  # checkout <worktree>: the fix head (the worktrees are detached at 80bce9a08d; the fix is a child commit)
  git -C "$REPO" cat-file -e "$COMMIT^{commit}" || { echo "$(ts) $COMMIT not in the shared store"; return 1; }
  git -C "$1" status --porcelain | grep -q . && { echo "$(ts) $1 is dirty:"; git -C "$1" status --porcelain; return 1; }
  git -C "$1" checkout -q --detach "$COMMIT" && echo "$(ts) $1 at $(git -C "$1" rev-parse HEAD)"
}
exec >>"$LOG" 2>&1
rm -f "$RES/fix1.done"
echo "=== $NAME fix1-check started $(ts) pid $$ COMMIT=$COMMIT PR2_COMMIT=$PR2_COMMIT ==="
ok=1
# ---- A1. option on ----
wait_slot A1
WT=/var/tmp/jhan/tron-pr3
checkout $WT || { step_done A1 "checkout failed"; echo failed-checkout >"$RES/fix1.done"; exit 1; }
t0=$(date +%s); build_llama $WT A1 >"$RES/build-A1.txt" 2>&1; echo "A1 build $(( $(date +%s) - t0 )) s" >>"$RES/build-A1.txt"
grep -q 'A1 build rc=0' "$RES/build-A1.txt" || { step_done A1 "build failed: $(cat "$RES/build-A1.txt" | tr '\n' ' ' | cut -c1-300)"; echo failed-build-A1 >"$RES/fix1.done"; exit 1; }
run_llama $WT "$SAVEK_CASE" >"$RES/A1-case.out" 2>&1; rc1=$?
run_llama $WT >"$RES/A1-all.out" 2>&1; rc2=$?
step_done A1 "case rc=$rc1 $(summary_of "$RES/A1-case.out"); whole rc=$rc2 $(passed_line "$RES/A1-all.out"); $(grep -E 'build rc|build [0-9]+ s' "$RES/build-A1.txt" | tr '\n' ' ')"
[ $rc1 -eq 0 ] && [ $rc2 -eq 0 ] || ok=0
# ---- M3. the production join removed ----
K=h/tron/models/model.hpp
OLD3='while (w.finished.load(std::memory_order_acquire) < n_helpers) {'
NEW3='while (false) {'
python3 - "$WT/$K" "$OLD3" "$NEW3" >"$RES/mutation3-applied.txt" 2>&1 <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); old, new = sys.argv[2], sys.argv[3]; s = p.read_text(); n = s.count(old)
print(f"before={n}", end=" ")
if n != 1: print("FAIL"); sys.exit(1)
s = s.replace(old, new); p.write_text(s); print(f"after-old={s.count(old)} after-new={s.count(new)}")
PY
m3=failed
if [ "$(cat "$RES/mutation3-applied.txt")" = "before=1 after-old=0 after-new=1" ]; then
  t0=$(date +%s); build_llama $WT mutant >"$RES/mutation3-build.txt" 2>&1; echo "mutant build $(( $(date +%s) - t0 )) s" >>"$RES/mutation3-build.txt"
  run_llama $WT "$SAVEK_CASE" >"$RES/mutation3-run.out" 2>&1; mrc=$?
  echo "mutant t_llama_unit rc=$mrc $(grep -E 'test cases:|assertions:|FAILED:|No tests ran|All tests passed' "$RES/mutation3-run.out" | tr '\n' ' ' | cut -c1-300) captured: $(grep -oE '^ *(finished_at_return|n_windows|worker_ix) := [0-9]+' "$RES/mutation3-run.out" | head -3 | tr -s ' ' | tr '\n' ' ') require: $(grep -A1 'FAILED:' "$RES/mutation3-run.out" | grep -m1 REQUIRE | tr -s ' ')" | tee "$RES/mutation3-result.txt"
  ( cd "$WT" && git checkout -- $K && git status --porcelain -- $K | wc -l ) >"$RES/mutation3-reverted.txt" 2>&1
  t0=$(date +%s); build_llama $WT restore >>"$RES/mutation3-build.txt" 2>&1; echo "restore build $(( $(date +%s) - t0 )) s" >>"$RES/mutation3-build.txt"
  run_llama $WT >"$RES/A1-restored.out" 2>&1; rrc=$?
  echo "restored t_llama_unit rc=$rrc $(summary_of "$RES/A1-restored.out")" | tee -a "$RES/mutation3-result.txt"
  reverted=$([ "$(cat "$RES/mutation3-reverted.txt")" = 0 ] && echo clean || echo DIRTY)
  same=$([ "$(passed_line "$RES/A1-all.out")" = "$(passed_line "$RES/A1-restored.out")" ] && echo same-counts || echo COUNTS-DIFFER)
  if [ $mrc -ne 0 ] && [ $rrc -eq 0 ] && [ "$reverted" = clean ] && [ "$same" = same-counts ] && grep -q 'FAILED:' "$RES/mutation3-run.out" && grep -q 'finished_at_return == n_workers - 1' "$RES/mutation3-run.out" && grep -E '^test cases:' "$RES/mutation3-run.out" | grep -q '1 failed'; then m3=ok; fi
  step_done M3 "$m3; mutant rc=$mrc: $(grep -E 'test cases:|assertions:' "$RES/mutation3-run.out" | tr '\n' ';') $(grep -m1 'FAILED:' "$RES/mutation3-run.out" | cut -c1-60); model.hpp reverted=$reverted; restored rc=$rrc $same"
else
  ( cd "$WT" && git checkout -- $K ); step_done M3 "mutation not applied ($(cat "$RES/mutation3-applied.txt")): failed"
fi
[ "$m3" = ok ] || ok=0
# ---- B1. option off; A3b. dispatch off ----
for spec in "B1 /var/tmp/jhan/tron-pr3rm" "A3b /var/tmp/jhan/tron-pr3nd"; do
  set -- $spec; lab=$1; wt=$2
  wait_slot $lab
  checkout $wt || { step_done $lab "checkout failed"; ok=0; continue; }
  t0=$(date +%s); build_llama $wt $lab >"$RES/build-$lab.txt" 2>&1; echo "$lab build $(( $(date +%s) - t0 )) s" >>"$RES/build-$lab.txt"
  grep -q "$lab build rc=0" "$RES/build-$lab.txt" || { step_done $lab "build failed: $(tr '\n' ' ' <"$RES/build-$lab.txt" | cut -c1-300)"; ok=0; continue; }
  run_llama $wt "$SAVEK_CASE" >"$RES/$lab-case.out" 2>&1; rc1=$?
  run_llama $wt >"$RES/$lab-all.out" 2>&1; rc2=$?
  step_done $lab "case rc=$rc1 $(summary_of "$RES/$lab-case.out"); whole rc=$rc2 $(passed_line "$RES/$lab-all.out"); $(grep -E 'build rc|build [0-9]+ s' "$RES/build-$lab.txt" | tr '\n' ' ')"
  [ $rc1 -eq 0 ] && [ $rc2 -eq 0 ] || ok=0
done
# ---- F1. format ----
( cd /var/tmp/jhan/tron-pr3 && "$NIX" develop --accept-flake-config --command bash -c '
  files=$(git diff --name-only '"$PR2_COMMIT"' HEAD -- "*.hpp" "*.cpp"); echo "files: $(echo $files | wc -w)"
  clang-format --dry-run --Werror $files; echo "clang-format rc=$?"
  git diff --check '"$PR2_COMMIT"' HEAD -- ":!lib/**"; echo "diff-check rc=$?"' ) >"$RES/format-fix1.txt" 2>&1
step_done F1 "$(grep -E ' rc=|files:' "$RES/format-fix1.txt" | tr '\n' ' ')"
grep -q '^clang-format rc=0' "$RES/format-fix1.txt" && grep -q '^diff-check rc=0' "$RES/format-fix1.txt" || ok=0
echo "$([ $ok = 1 ] && echo ok || echo failed)" >"$RES/fix1.done"
step_done end "$(cat "$RES/fix1.done")"
echo "=== $NAME fix1-check finished $(ts): $(cat "$RES/fix1.done") ==="
