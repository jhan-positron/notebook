#!/usr/bin/env bash
# pr5022-final-20261119 build. Runs ON delphi-3b35 (shared machine: Brian Hamon and John Pruitt use the
# first half of the FPGA cards). Uses our CPUs only (96-143, low priority), local disk, no FPGA card, no huge page.
#
# What it builds: the prepared final tree of tron PR 5022 (reviewed head 4c4b7b8864 merged with main 3bea58b788,
# plus the review edits), which is NOT committed. So the build tree is made in two steps:
#   1. a worktree of main at BASE_SHA on 3b35-local disk (/var/tmp/jhan/b35-<tag>), and
#   2. the files that differ from main (exec/results/pr5022-final-20261119/overlay-files.txt), copied over it
#      from the prepared tree on the shared home.
# The git tree hash of the result must equal exec/results/pr5022-final-20261119/tree.txt before anything is built.
# With TAG=main the worktree is plain main (no copy): the reference build for the linked-binary kernel compare.
#
# Recipe = exec/pr5047-20261020/build.sh (plain shell, host clang 19.1.7, ccache), with BUILD_INGEST_MODELS=OFF:
# the three unit tests and runtron need no ingested model, and OFF avoids the model export steps.
# Words: tron = the inference program; runtron = its command-line tool; AMX = Intel tile-matrix instructions;
# TRON_AMX_DISPATCH = the build option that compiles the AMX kernels.
# Usage (on 3b35): TAG=final|main bash build-3b35.sh   [JOBS=40]
# Log: exec/logs/pr5022-final-20261119-build-$TAG.log. Marker: exec/results/pr5022-final-20261119/build-$TAG.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
TAG=${TAG:?TAG=final|main is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5022-final-20261119
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-build-$TAG.log
REPO=/home/jhan/workspace/tron
SRC=/home/jhan/workspace/ai-runs/pr5022-final/tron
BASE_SHA=3bea58b78867dd7567c86237aeefdc29a1617d87
WT=/var/tmp/jhan/b35-pr5022-$TAG
OUR_CPUS=96-143
JOBS=${JOBS:-40}
CONF="--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON"
TARGETS='runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit'
mkdir -p "$RES" "$EXEC/logs" /var/tmp/jhan
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
PIN="nice -n10 taskset -c $OUR_CPUS"
mark() { echo "$1" >"$RES/build-$TAG.done"; echo "=== build $TAG finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
case $TAG in final|main) ;; *) echo "TAG must be final or main"; exit 1 ;; esac
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only (here: $(hostname))"; exit 1; }
exec {BUILD_LOCK_FD}>"/var/tmp/jhan/$NAME.build-$TAG.lock"
flock -n "$BUILD_LOCK_FD" || { echo "$(ts) another build-3b35.sh $TAG runs; this copy exits"; exit 1; }
rm -f "$RES/build-$TAG.done"
echo "=== build $TAG started $(ts) pid $$ on $(hostname) base=$BASE_SHA conf=[$CONF] targets=[$TARGETS] jobs=$JOBS cpus=$OUR_CPUS ==="
echo "uptime: $(uptime)"
git -C "$REPO" cat-file -e "$BASE_SHA^{commit}" 2>/dev/null || fail "$BASE_SHA not visible in $REPO"
if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$BASE_SHA" || fail "git worktree add $WT failed"
  echo "$(ts) worktree $WT added at $BASE_SHA"
fi
[ "$(git -C "$WT" rev-parse HEAD 2>/dev/null)" = "$BASE_SHA" ] || fail "$WT is not at $BASE_SHA"
if [ "$TAG" = final ]; then
  WANT_TREE=$(cat "$RES/tree.txt") || fail "no $RES/tree.txt"
  while read -r f; do
    [ -n "$f" ] || continue
    [ -f "$SRC/$f" ] || fail "prepared file missing: $SRC/$f"
    mkdir -p "$WT/$(dirname "$f")" && cp -p "$SRC/$f" "$WT/$f" || fail "copy of $f failed"
  done <"$RES/overlay-files.txt"
  git -C "$WT" add -A || fail "git add in $WT"
  GOT_TREE=$(git -C "$WT" write-tree) || fail "git write-tree in $WT"
  echo "$(ts) tree hash of the build tree: $GOT_TREE (wanted $WANT_TREE)"
  [ "$GOT_TREE" = "$WANT_TREE" ] || fail "build tree hash $GOT_TREE differs from the prepared tree $WANT_TREE (stale NFS read or a changed file)"
else
  [ -z "$(git -C "$WT" status --porcelain | grep -v '^?? gen' | head -1)" ] || fail "$WT is not a clean checkout of main"
  GOT_TREE=$(git -C "$WT" rev-parse 'HEAD^{tree}')
fi
cd "$WT" || fail "cd $WT"
t0=$(date +%s)
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
$PIN bash -c '
  set -o pipefail
  cmake '"$CONF"' -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache 2>&1 | tail -4 || exit 2
  echo "configure ok $(date -u +%T): $(grep -E "^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|CMAKE_CXX_COMPILER):" gen/CMakeCache.txt | tr "\n" " ")"
  cmake --build gen --target '"$TARGETS"' -j'"$JOBS"' 2>&1 | grep -E "error|FAILED|warning:|ninja: build stopped" | sed -n 1,160p
  exit ${PIPESTATUS[0]}'
rc=$?
echo "$(ts) build rc=$rc wall=$(( $(date +%s) - t0 ))s"
[ $rc -eq 2 ] && fail "configure failed"
[ $rc -ne 0 ] && fail "build failed rc=$rc"
for tg in $TARGETS; do [ -x "gen/$tg" ] || fail "gen/$tg missing after the build"; done
n_amx=$($PIN objdump -d --no-show-raw-insn gen/runtron 2>/dev/null | grep -c -w tdpbf16ps || true)
n_warn=$(grep -c "warning:" "$LOG" || true)
{
  echo "tag $TAG worktree $WT on $(hostname)"
  echo "source: main $BASE_SHA$([ "$TAG" = final ] && echo " + the $(grep -c . "$RES/overlay-files.txt") prepared files of $SRC")"
  echo "git tree hash of the build tree: $GOT_TREE"
  echo "configure: cmake $CONF -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
  echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|CMAKE_CXX_COMPILER):' gen/CMakeCache.txt | tr '\n' ' ')"
  echo "compiler: $(clang++-19 --version | head -1)"
  echo "targets: $TARGETS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS with -j$JOBS"
  for tg in $TARGETS; do sha256sum "gen/$tg"; done
  echo "checks: tdpbf16ps instructions in runtron = $n_amx (need > 0); compiler warnings in the build log = $n_warn"
} >"$RES/build-$TAG.txt"
cat "$RES/build-$TAG.txt"
[ "${n_amx:-0}" -gt 0 ] || fail "no tdpbf16ps in gen/runtron (the AMX kernel is not compiled in)"
mark ok
