#!/bin/bash
# Build the rebased PR1 head (jhan-amx-p0 rebased onto main 68378c3b48, 2026-09-15)
# on delphi-3bda and run the tests that touch the merged regions.
# Both options ON: TRON_AMX_DISPATCH (this PR) and TRON_PAGE_SHARE_COUNTERS
# (PR0 #4267, on main), so the merged self_attention.hpp region compiles with
# both blocks active. CI compiles them in separate lanes.
# Copy of exec/pr1-rebase-20260911/build-test.sh with the tip, the log path
# and an object-visibility wait (NFS attribute cache) changed.
set -u
TIP=${TIP:-f4c7c7af74}
WT=/var/tmp/jhan/tron-pr1-rebase
OUR_CPUS=72-143,216-287          # jhan's half of 3bda (socket 1)
NIX=$(command -v nix || echo /home/jhan/.nix-profile/bin/nix)
LOG=${LOG:-/home/jhan/workspace/intel-AMX/exec/pr1-rebase-20260915/build-test.log}
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "$(ts) start TIP=$TIP"
cd /home/jhan/workspace/tron-amx || exit 1
for i in 1 2 3 4 5 6; do
  git cat-file -e "$TIP^{commit}" 2>/dev/null && break
  echo "$(ts) commit $TIP not visible yet (NFS cache), retry $i"; sleep 20
done
git cat-file -e "$TIP^{commit}" || { echo "$(ts) commit $TIP not found"; exit 1; }
[ -d "$WT" ] || git worktree add --detach "$WT" "$TIP" || { echo "$(ts) worktree add failed"; exit 1; }
cd "$WT" || exit 1
[ "$(git rev-parse HEAD)" = "$(git rev-parse $TIP)" ] || git checkout -q --detach "$TIP" || exit 1
echo "$(ts) tree at $(git rev-parse --short HEAD): $(git log -1 --format=%s)"
echo "$(ts) status: $(git status --short | head -5 | tr '\n' ' ')"
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c '
  set -o pipefail
  clang-format --dry-run t/t_llama_unit.cpp 2>&1 | grep -E "t_llama_unit.cpp:(19[89][0-9]|20[01][0-9]):" | head -5; echo "clang-format dry-run of t_llama_unit.cpp lines 1980-2019 checked"
  cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_PAGE_SHARE_COUNTERS=ON -DCMAKE_CXX_FLAGS= 2>&1 | tail -3 &&
  cmake --build gen --target runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit t_page_share_counters -j96 2>&1 | grep -E "error|FAILED|warning: unused" | sed -n 1,60p
  exit ${PIPESTATUS[0]}'
rc=$?
echo "$(ts) build rc=$rc in $(( $(date +%s) - t0 )) s"
[ $rc -eq 0 ] || { echo "$(ts) BUILD FAILED"; exit 1; }
for t in t_page_share_counters t_amx_numerics t_amx_dispatch_dtype t_llama_unit; do
  echo "$(ts) === run $t"
  env -u SYSTEM_CONFIG nice -n10 taskset -c $OUR_CPUS timeout 1800 ./gen/$t 2>&1 | tail -6
  echo "$(ts) $t exit=${PIPESTATUS[0]}"
done
echo "$(ts) done"
