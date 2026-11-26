#!/usr/bin/env bash
# pr5606-check-20261123 build. Runs ON delphi-3b35. Uses our CPUs only (96-143, low priority), no FPGA card,
# no huge page. Adapted from exec/pr5022-final-20261119/build-3b35.sh; the build recipe is the same.
#
# What it does: moves one build tree to one source state and builds the named test targets.
#   OPT=off  tree /var/tmp/jhan/b35-pr5606-off, configured with -DTRON_AMX_DISPATCH=OFF
#   OPT=on   tree /var/tmp/jhan/b35-pr5606-on,  configured with -DTRON_AMX_DISPATCH=ON
#   STATE=S0|S1|S2  the commit to build (see common.sh)
# The tree is a git worktree of /home/jhan/workspace/tron. It is created on the first call. The preset builds into
# the folder gen inside the tree, so each option value has its own tree.
# cmake is configured once per tree. A later call only runs the build; ninja (the build tool) runs cmake again by
# itself when a CMakeLists.txt changed.
# After the build, a copy of gen/t_amx_dispatch_dtype is kept as gen/t_amx_dispatch_dtype.<STATE>. The copy stays
# in gen, because the binary finds two shared libraries relative to its own folder (rpath $ORIGIN).
# Usage (on 3b35): OPT=off STATE=S0 [TARGETS="..."] bash build-3b35.sh
# Logs: exec/logs/pr5606-check-20261123-build-<opt>-<state>{,-configure,-ninja}.log
# Record: exec/results/pr5606-check-20261123/build-<opt>-<state>.txt. Marker: build-<opt>-<state>.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
OPT=${OPT:?OPT=off|on is required}
STATE=${STATE:?STATE=S0|S1|S2 is required}
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
TARGETS=${TARGETS:-'t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_page_share_counters'}
TAG=$OPT-$STATE
LOG=$LOGDIR/$NAME-build-$TAG.log
CLOG=$LOGDIR/$NAME-build-$TAG-configure.log
NLOG=$LOGDIR/$NAME-build-$TAG-ninja.log
WT=$(wt_of "$OPT") || { echo "OPT must be off or on"; exit 1; }
SHA=$(sha_of "$STATE") || { echo "STATE must be S0, S1 or S2"; exit 1; }
ONOFF=$(echo "$OPT" | tr a-z A-Z)
CONF="--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=$ONOFF"
mkdir -p "$RES" "$LOGDIR" /var/tmp/jhan
exec >>"$LOG" 2>&1
mark() { echo "$1" >"$RES/build-$TAG.done"; echo "=== build $TAG finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
only_3b35
rm -f "$RES/build-$TAG.done"
echo "=== build $TAG started $(ts) pid $$ on $(hostname) sha=$SHA conf=[$CONF] targets=[$TARGETS] jobs=$JOBS cpus=$OUR_CPUS ==="
echo "uptime: $(uptime)"
git -C "$REPO" cat-file -e "$SHA^{commit}" 2>/dev/null || fail "$SHA not visible in $REPO"
if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$SHA" || fail "git worktree add $WT failed"
  echo "$(ts) worktree $WT added at $SHA"
fi
mkdir -p "$WT/gen/keep"
exec {BUILD_LOCK_FD}>"$WT/gen/keep/build.lock"
flock -n "$BUILD_LOCK_FD" || { echo "$(ts) another build-3b35.sh runs in $WT; this copy exits"; exit 1; }
[ -z "$(dirty_of "$WT")" ] || fail "$WT has changes: $(dirty_of "$WT" | head -3 | tr '\n' ' ')"
if [ "$(git -C "$WT" rev-parse HEAD)" != "$SHA" ]; then
  git -C "$WT" checkout --detach "$SHA" || fail "git checkout $SHA in $WT"
fi
[ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || fail "$WT is not at $SHA"
GOT_TREE=$(git -C "$WT" rev-parse 'HEAD^{tree}')
echo "$(ts) $WT is at $SHA, git tree hash $GOT_TREE"
if [ "$STATE" = S2 ]; then
  [ "$GOT_TREE" = "$S2_TREE" ] || fail "tree hash $GOT_TREE differs from the expected $S2_TREE"
fi
cd "$WT" >/dev/null 2>&1 || fail "cd $WT"
t0=$(date +%s)
if [ ! -e gen/CMakeCache.txt ]; then
  # shellcheck disable=SC2086
  $PIN cmake $CONF -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache >"$CLOG" 2>&1 \
    || { tail -20 "$CLOG"; fail "configure failed"; }
  echo "$(ts) configured (first configure of this tree), $(wc -l <"$CLOG") lines in $CLOG"
else
  echo "$(ts) gen/CMakeCache.txt exists: no explicit configure; ninja runs cmake again when a CMakeLists.txt changed"
  echo "no explicit configure at this state" >"$CLOG"
fi
# shellcheck disable=SC2086
$PIN cmake --build gen --target $TARGETS -j"$JOBS" >"$NLOG" 2>&1
rc=$?
wall=$(( $(date +%s) - t0 ))
echo "$(ts) build rc=$rc wall=${wall}s, $(wc -l <"$NLOG") lines in $NLOG"
if [ $rc -ne 0 ]; then grep -E "error|FAILED|ninja: build stopped" "$NLOG" | sed -n 1,40p; fail "build failed rc=$rc"; fi
for tg in $TARGETS; do [ -x "gen/$tg" ] || fail "gen/$tg missing after the build"; done
cp -p gen/t_amx_dispatch_dtype "gen/t_amx_dispatch_dtype.$STATE" || fail "copy of the test binary"
CACHE=$(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|CMAKE_CXX_COMPILER|CMAKE_CXX_COMPILER_LAUNCHER):' gen/CMakeCache.txt | tr '\n' ' ')
case "$CACHE" in *"TRON_AMX_DISPATCH:BOOL=$ONOFF"*) ;; *) fail "the cache does not say TRON_AMX_DISPATCH=$ONOFF: $CACHE" ;; esac
n_warn=$(grep -c "warning:" "$NLOG" || true)
n_cwarn=$(grep -c -i "warning" "$CLOG" || true)
{
  echo "build $TAG: tree $WT on $(hostname), state $STATE = commit $SHA"
  echo "git tree hash: $GOT_TREE; changes outside gen: $(dirty_of "$WT" | wc -l) lines"
  echo "configure: cmake $CONF -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
  echo "cache: $CACHE"
  echo "compiler: $(clang++-19 --version | head -1)"
  echo "targets: $TARGETS; built $(ts) in $wall s on cpus $OUR_CPUS with -j$JOBS"
  echo "ninja steps in this build: $(grep -c -E '^\[[0-9]+/[0-9]+\]' "$NLOG" || true); cmake ran again inside ninja: $(grep -c 'Re-running CMake' "$NLOG" || true) time(s)"
  for tg in $TARGETS; do sha256sum "gen/$tg"; done
  echo "compiler warnings (lines with 'warning:' in the ninja log): $n_warn; lines with 'warning' in the configure log: $n_cwarn"
} >"$RES/build-$TAG.txt"
cat "$RES/build-$TAG.txt"
mark ok
