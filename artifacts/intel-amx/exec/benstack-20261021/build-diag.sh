#!/usr/bin/env bash
# benstack-20261021 DIAGNOSTIC build (runs ON delphi-3bda, detached, our cpus only, production serving left alone): build
# t_llama_unit ONLY of ONE commit with ONE value of the CMake option TRON_K_VNNI, as a 3bda-local worktree of the shared
# repo. Copy of build.sh for instrumented test commits (local, unpushed branches are fine: the shared repo is on NFS). Tags: bp2/bp2v = branch jhan-vnnik-2-amx-5047 (PR 4957 re-expressed on PR 5047) option OFF/ON; bp3/bp3v =
# jhan-vnnik-3-shared-save-5047; bp4/bp4v = jhan-vnnik-4-tail-block-5047. Fork of exec/pr5047-20261020/build2.sh; new:
# t_k_vnni_layout and t_heterogeneous_scheduler are gating targets (PR 5047's own head fails to compile the latter).
# Words: tron = the inference program, runtron = its command-line tool; AMX = Intel tile-matrix instructions; the option =
# TRON_K_VNNI (K cache of 128-dim heads in the VNNI pair-interleaved layout); the worktree = /var/tmp/jhan/tron-$TAG.
# Usage (on 3bda): TAG=bp2|bp2v|bp3|bp3v|bp4|bp4v SHA=<full 40-hex sha> VNNI=ON|OFF bash build.sh   [JOBS=18]
# Log: exec/logs/benstack-20261021-build-$TAG.log. Marker: exec/results/benstack-20261021/build-$TAG.done = "ok" or "failed: <why>".
# Outputs: /var/tmp/jhan/tron-$TAG/gen/{runtron.$TAG,t_amx_numerics,t_amx_dispatch_dtype,t_llama_unit,t_k_vnni_layout,t_heterogeneous_scheduler},
#          exec/results/benstack-20261021/{build-$TAG.txt,build-symbols-$TAG.txt}.
# Never edit this file while a copy of it runs on 3bda (NFS: bash reads the script incrementally; fixes go into a new file name).
set -u
TAG=${TAG:?TAG=<lowercase tag, e.g. bp4d> is required}
SHA=${SHA:?SHA=<full 40-hex commit sha> is required}
VNNI=${VNNI:?VNNI=ON|OFF is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=benstack-20261021
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-build-$TAG.log
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/tron-$TAG
TRACES_SRC=/var/tmp/jhan/tron-pr4/ingest/traces
OUR_CPUS=72-143,216-287
JOBS=${JOBS:-18}
CONF="--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=$VNNI"
TARGETS='t_llama_unit'
KSYM_RE='amx_attn_h128g4'
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
PIN="nice -n10 taskset -c $OUR_CPUS"
mark() { echo "$1" >"$RES/build-$TAG.done"; echo "=== build $TAG finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
exec {BUILD_LOCK_FD}>"/var/tmp/jhan/$NAME.build-$TAG.lock"
flock -n "$BUILD_LOCK_FD" || { echo "$(ts) another build.sh $TAG holds /var/tmp/jhan/$NAME.build-$TAG.lock; this copy exits"; exit 1; }
rm -f "$RES/build-$TAG.done"
echo "=== build $TAG started $(ts) pid $$ on $(hostname) sha=$SHA vnni=$VNNI conf=[$CONF] targets=[$TARGETS] jobs=$JOBS ==="
case $TAG in *[!a-z0-9]*|'') fail "TAG '$TAG' is not lowercase alphanumerics" ;; esac
case $SHA in *[!0-9a-f]*|'') fail "SHA '$SHA' is not a hex sha" ;; esac
[ ${#SHA} -eq 40 ] || fail "SHA must be the full 40-hex sha (got ${#SHA} chars)"
case $VNNI in ON|OFF) ;; *) fail "VNNI '$VNNI' is not ON or OFF" ;; esac
for try in 1 2 3 4 5 6 7 8 9 10; do
  git -C "$REPO" cat-file -e "$SHA^{commit}" 2>/dev/null && break
  [ "$try" = 10 ] && fail "$SHA not visible in $REPO after 5 min"
  [ "$try" = 1 ] && echo "$(ts) waiting: $SHA not yet visible in $REPO"
  sleep 30
done
if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$SHA" || fail "git worktree add $WT failed"
  echo "$(ts) worktree $WT added at $SHA"
fi
[ "$(git -C "$WT" rev-parse HEAD 2>/dev/null)" = "$SHA" ] || fail "$WT exists but is not at $SHA (HEAD $(git -C "$WT" rev-parse HEAD 2>/dev/null)); remove it by hand on 3bda (git -C $REPO worktree remove $WT) and relaunch"
echo "$(ts) worktree $WT at $(git -C "$WT" rev-parse HEAD) ($(git -C "$WT" log -1 --format='%ci %s' | cut -c1-120))"
if [ ! -d "$WT/ingest/traces" ]; then
  mkdir -p "$WT/ingest" && cp -r "$TRACES_SRC" "$WT/ingest/" || fail "cp -r $TRACES_SRC failed"
  echo "$(ts) ingest/traces copied from $TRACES_SRC"
fi
cd "$WT" || fail "cd $WT"
t0=$(date +%s)
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
$PIN bash -c '
  set -o pipefail
  make TOKENIZER_PYTHON_VERSION=3.12.7 ingest-deps 2>&1 | tail -2 || exit 2
  [ -x ingest/export/.venv/bin/python3 ] || { echo "ingest/export/.venv missing after make ingest-deps"; exit 2; }
  make TOKENIZER_PYTHON_VERSION=3.12.7 gen/tokenize_py 2>&1 | tail -2 || exit 2
  [ -x gen/tokenize_py ] || { echo "gen/tokenize_py missing"; exit 2; }
  cmake '"$CONF"' -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache 2>&1 | tail -3 || exit 2
  echo "configure ok $(date -u +%T): $(grep -E "^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|TRON_K_VNNI|BUILD_INGEST_MODELS|CMAKE_CXX_COMPILER):" gen/CMakeCache.txt | tr "\n" " ")"
  cmake --build gen --target '"$TARGETS"' -j'"$JOBS"' 2>&1 | grep -E "error|FAILED|warning:" | sed -n 1,120p
  exit ${PIPESTATUS[0]}'
rc=$?
echo "$(ts) build rc=$rc wall=$(( $(date +%s) - t0 ))s"
[ $rc -eq 2 ] && fail "configure failed"
[ $rc -ne 0 ] && fail "build failed rc=$rc"
for tg in $TARGETS; do [ -x "gen/$tg" ] || fail "gen/$tg missing after the build"; done
# the option must have taken: the cache value and the compile definition (src/tron/CMakeLists.txt adds -DTRON_K_VNNI)
cache_vnni=$(grep -E '^TRON_K_VNNI:BOOL=' gen/CMakeCache.txt | cut -d= -f2)
def_vnni=$(grep -c -- '-DTRON_K_VNNI' gen/compile_commands.json 2>/dev/null); def_vnni=${def_vnni:-0}
{
  echo "tag $TAG worktree $WT option TRON_K_VNNI=$VNNI (diagnostic build: t_llama_unit only)"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s' | cut -c1-120))"
  echo "configure: cmake $CONF -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
  echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|TRON_K_VNNI|BUILD_INGEST_MODELS|CMAKE_CXX_COMPILER):' gen/CMakeCache.txt | tr '\n' ' ')"
  echo "compiler: $(clang++-19 --version | head -1)"
  echo "targets: $TARGETS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS with -j$JOBS"
  for tg in $TARGETS; do sha256sum "gen/$tg"; done
  echo "checks: cache_vnni=$cache_vnni (need $VNNI) define_count=$def_vnni"
} >"$RES/build-$TAG.txt"
cat "$RES/build-$TAG.txt"
[ "$cache_vnni" = "$VNNI" ] || fail "TRON_K_VNNI in the CMake cache is '$cache_vnni', wanted $VNNI"
if [ "$VNNI" = ON ]; then [ "${def_vnni:-0}" -gt 0 ] || fail "no -DTRON_K_VNNI in compile_commands.json although the option is ON"; else [ "${def_vnni:-0}" -eq 0 ] || fail "-DTRON_K_VNNI present in compile_commands.json although the option is OFF"; fi
mark ok
