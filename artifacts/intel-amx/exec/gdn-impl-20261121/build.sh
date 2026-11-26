#!/usr/bin/env bash
# gdn-impl-20261121 build. Runs ON delphi-3b35 (a shared machine: other users hold the first half of the FPGA cards).
# Uses our CPUs only (low priority), local disk, no FPGA card, no huge page, no root.
#
# What it builds: tron targets (runtron = tron's command-line tool, and unit-test binaries) at one commit of the
# GDN/AMX work, with the generated plugin of ONE model, Qwen3.5 4B (tron slug ingested-qwen-3.5-4b).
# Words: tron = the inference program; GDN = GatedDeltaNet, the recurrent layer type of that model; AMX = Intel
# tile-matrix instructions; TRON_AMX_DISPATCH = the build option that compiles the AMX kernels.
# Recipe = exec/gdn-20261120/build-3b35.sh with two changes:
#   - an existing build tree of the same TAG is moved to the new commit and rebuilt incrementally;
#   - the CPUs of the build are a parameter, so that CPUs 136-143 stay free for stand-alone benchmarks.
# Usage (on 3b35): TAG=<tag> SHA=<40-hex> [TARGETS='runtron t_gated_delta_net'] [JOBS=36] [CPUS=96-135] bash build.sh
# Log: exec/logs/gdn-impl-20261121-build-$TAG.log (appended). Marker: exec/results/gdn-impl-20261121/build-$TAG.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
TAG=${TAG:?TAG=<tag> is required}
SHA=${SHA:?SHA=<commit> is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=gdn-impl-20261121
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-build-$TAG.log
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/b35-gdn-$TAG
# REG = the model list of the build. The default holds Qwen3.5 4B only. REG=<file> selects another list.
REG=${REG:-$EXEC/gdn-20261120/models.gdn.yaml}
CPUS=${CPUS:-96-135}
JOBS=${JOBS:-36}
# CONF_FLAGS replaces the default options, for example CONF_FLAGS="-DCMAKE_BUILD_TYPE=Debug" for a build without AMX
# dispatch and without optimization (the configuration of the asan, tsan and coverage presets).
CONF="--preset native -DBUILD_INGEST_MODELS=ON ${CONF_FLAGS:--DTRON_AMX_DISPATCH=ON} -DDEV_MODEL_CONFIG=$WT/models.gdn.yaml"
TARGETS=${TARGETS:-'runtron t_gated_delta_net'}
mkdir -p "$RES" "$EXEC/logs" /var/tmp/jhan
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
PIN="nice -n10 taskset -c $CPUS"
mark() { echo "$1" >"$RES/build-$TAG.done"; echo "=== build $TAG finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
case $TAG in *[!a-z0-9]*|'') echo "TAG must be lowercase alphanumerics"; exit 1 ;; esac
[ "$TAG" = base ] && { echo "TAG=base is the baseline tree of 2026-11-20; this script does not touch it"; exit 1; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only (here: $(hostname))"; exit 1; }
exec {BUILD_LOCK_FD}>"/var/tmp/jhan/$NAME.build-$TAG.lock"
flock -n "$BUILD_LOCK_FD" || { echo "$(ts) another build.sh $TAG runs; this copy exits"; exit 1; }
rm -f "$RES/build-$TAG.done"
SHA=$(git -C "$REPO" rev-parse --verify "$SHA^{commit}" 2>/dev/null) || fail "commit not visible in $REPO"
echo "=== build $TAG started $(ts) pid $$ on $(hostname) sha=$SHA conf=[$CONF] targets=[$TARGETS] jobs=$JOBS cpus=$CPUS ==="
if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$SHA" || fail "git worktree add $WT failed"
  echo "$(ts) worktree $WT added at $SHA"
else
  [ -z "$(git -C "$WT" status --porcelain --untracked-files=no)" ] || fail "$WT has local changes"
  git -C "$WT" checkout --detach "$SHA" 2>&1 | tail -1 || fail "checkout of $SHA in $WT failed"
fi
[ "$(git -C "$WT" rev-parse HEAD 2>/dev/null)" = "$SHA" ] || fail "$WT is not at $SHA"
cp "$REG" "$WT/models.gdn.yaml" || fail "copy of $REG failed"
cd "$WT" || fail "cd $WT"
t0=$(date +%s)
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
$PIN bash -c '
  set -o pipefail
  if [ ! -f gen/CMakeCache.txt ]; then
    make TOKENIZER_PYTHON_VERSION=3.12.7 ingest-deps 2>&1 | tail -4 || exit 2
    [ -x ingest/export/.venv/bin/python3 ] || { echo "ingest/export/.venv missing after make ingest-deps"; exit 2; }
    make TOKENIZER_PYTHON_VERSION=3.12.7 gen/tokenize_py 2>&1 | tail -2 || exit 2
    [ -x gen/tokenize_py ] || { echo "gen/tokenize_py missing"; exit 2; }
    cmake '"$CONF"' -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache 2>&1 | tail -6 || exit 2
    echo "configure ok $(date -u +%T): $(grep -E "^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|DEV_MODEL_CONFIG|CMAKE_CXX_COMPILER):" gen/CMakeCache.txt | tr "\n" " ")"
  fi
  cmake --build gen --target '"$TARGETS"' -j'"$JOBS"' 2>&1 | grep -E "error|Error|FAILED|warning:|ninja: build stopped|Traceback|Exporting|Exception|note:" | sed -n 1,300p
  exit ${PIPESTATUS[0]}'
rc=$?
echo "$(ts) build rc=$rc wall=$(( $(date +%s) - t0 ))s"
[ $rc -eq 2 ] && fail "configure or dependency step failed"
[ $rc -ne 0 ] && fail "build failed rc=$rc"
for tg in $TARGETS; do [ -x "gen/$tg" ] || fail "gen/$tg missing after the build"; done
{
  echo "tag $TAG worktree $WT on $(hostname)"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s' | cut -c1-120))"
  echo "configure: cmake $CONF -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
  echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|DEV_MODEL_CONFIG|CMAKE_CXX_COMPILER):' gen/CMakeCache.txt | tr '\n' ' ')"
  echo "compiler: $(clang++-19 --version | head -1)"
  echo "targets: $TARGETS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $CPUS with -j$JOBS"
  for tg in $TARGETS; do sha256sum "gen/$tg"; done
  if [ -x gen/runtron ]; then
    echo "checks: tdpbf16ps instructions in runtron = $($PIN objdump -d --no-show-raw-insn gen/runtron 2>/dev/null | grep -c -w tdpbf16ps || true); TRON_ATTN_STATS literals = $($PIN grep -a -o TRON_ATTN_STATS gen/runtron | wc -l); TRON_GDN_STATS literals = $($PIN grep -a -o TRON_GDN_STATS gen/runtron | wc -l); model slug literals = $($PIN grep -a -o 'ingested-qwen-3\.5-4b' gen/runtron | wc -l)"
  fi
} >"$RES/build-$TAG.txt"
cat "$RES/build-$TAG.txt"
mark ok
