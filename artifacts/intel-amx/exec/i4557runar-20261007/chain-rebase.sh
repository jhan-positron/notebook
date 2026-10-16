#!/usr/bin/env bash
# i4557runar-20261007 chain-rebase (runs ON delphi-3bda): compile and unit-test the PR #4557 branch after its rebase onto
# main 2e7752a0db (2026-10-07). Steps: rsync the NFS worktree into /var/tmp/jhan/tron-issue4525, lint-notes, gen (all
# targets) and gen-amxoff (4 tests), unit tests in both trees. Our half of the machine only; serving is left alone.
EXEC=/home/jhan/workspace/intel-AMX/exec
export NAME=i4557runar-20261007
RES=$EXEC/results/$NAME/rebase
LOG=$EXEC/logs/$NAME-rebase.log
SRCWT=/home/jhan/workspace/ai-runs/tron-issue4525
UT=/var/tmp/jhan/tron-issue4525
T=/var/tmp/jhan/tron-issue4525-tests/runar-rebase-20261007
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command bash -c"
PIN="taskset -c 72-143,216-287 nice -n 10"
PROGRESS='^\[[0-9]+/[0-9]+\] '
TESTS="t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler"
mkdir -p "$RES" "$T"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
HEAD_SHA=$(git -C "$SRCWT" rev-parse HEAD)
echo "=== $NAME rebase check started $(ts) pid $$ head=$HEAD_SHA ==="
rsync -rlc --exclude .git --exclude 'gen*' --exclude init.txt --exclude compile_commands.json "$SRCWT/" "$UT/" && echo "$(ts) rsync ok" || { echo "rsync failed" >"$RES/done"; exit 1; }
builtin cd "$UT" || exit 1
git add -A . >/dev/null 2>&1; git rm -r -q --cached gen-amxoff gen-avx2 gen-debug >/dev/null 2>&1
$PIN $NIX "make lint-notes >$T/lint-notes.log 2>&1; echo LINT-NOTES EXIT \$?"
run_tests() {
  local g=$1 p=$2 t
  for t in $TESTS; do
    $PIN "$g/$t" --skip-benchmarks >"$T/$p.$t.log" 2>&1
    echo "$p $t EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/$p.$t.log" | tail -1))"
  done
}
t0=$(date +%s)
$PIN $NIX "cmake --build gen -j 48 -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -80; echo BUILD-AMXON EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen build took $(( $(date +%s) - t0 )) s"
run_tests gen amxon
TRON_AMX_DISABLE=1 $PIN gen/t_amx_numerics --skip-benchmarks >"$T/amxon.t_amx_numerics.disabled.log" 2>&1
echo "amxon t_amx_numerics kill-switch EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/amxon.t_amx_numerics.disabled.log" | tail -1))"
t0=$(date +%s)
$PIN $NIX "cmake --build gen-amxoff -j 48 --target $TESTS -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -80; echo BUILD-AMXOFF EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen-amxoff build took $(( $(date +%s) - t0 )) s"
run_tests gen-amxoff amxoff
cp "$T"/*.log "$RES/" 2>/dev/null
echo finished >"$RES/done"
echo "=== $NAME rebase check finished $(ts) ==="
