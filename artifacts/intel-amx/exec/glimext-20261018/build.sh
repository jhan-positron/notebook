#!/usr/bin/env bash
# glimext-20261018 build (runs ON delphi-3bda, detached, our half only): build runtron and the three AMX test binaries of
# ONE commit as a 3bda-local worktree of the shared repo. The chain launches it twice: TAG=g16b for the PR's merge base
# (main 6198824246, "without PR #5015") and TAG=g16h for the PR head (5061623a34, "with PR #5015"). Both builds use the
# same recipe (plain shell, host clang 19.1.7, ccache), so a throughput difference between the two binaries comes from
# the commit, not from the toolchain. Fork of exec/glimpl-20261017/build.sh (itself a fork of exec/td-20261016/build-variant.sh
# with the checks of exec/attnstats-20261002/chain.sh step A); the tag, worktree, symbol regex and marker name are parameters.
# Words: tron = the inference program, runtron = its command-line tool; AMX = Intel tile-matrix instructions;
# kv_mul = query heads per KV head; the worktree = /var/tmp/jhan/tron-$TAG (local disk, object store shared over NFS).
# Usage (on 3bda): TAG=g16b|g16h SHA=<full 40-hex sha> KSYM_RE=<regex> KSYM_N=<count> bash build.sh   [JOBS=20]
#   KSYM_RE/KSYM_N: the kernel symbols the binary must contain (mangled names, `nm` without -C: the host nm cannot demangle
#   the requires-clause templates). Base: 'amx_attn_h128g4(17qk_rowmajor_128x4|18pack_q_group_128x4|21weights_times_v_128x4)E'
#   with 4 lines (3 plain kernels + 1 thread-local guard); head: '...ILm(4|16)E' with 8 lines (6 instantiations + 2 guards).
# Log: exec/logs/glimext-20261018-build-$TAG.log. Marker: exec/results/glimext-20261018/build-$TAG.done = "ok" or "failed: <why>".
# Outputs: /var/tmp/jhan/tron-$TAG/gen/{runtron.$TAG,t_amx_numerics,t_amx_dispatch_dtype,t_llama_unit},
#          exec/results/glimext-20261018/{build-$TAG.txt,build-symbols-$TAG.txt}.
# Never edit this file while a copy of it runs on 3bda (NFS: bash reads the script incrementally; fixes go into a new file name).
set -u
TAG=${TAG:?TAG=g16b|g16h is required}
SHA=${SHA:?SHA=<full 40-hex commit sha> is required}
KSYM_RE=${KSYM_RE:?KSYM_RE (mangled kernel symbol regex) is required}
KSYM_N=${KSYM_N:?KSYM_N (expected symbol line count) is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=glimext-20261018
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-build-$TAG.log
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/tron-$TAG
TRACES_SRC=/var/tmp/jhan/tron-pr4/ingest/traces
GLIMMER_TRACE=ingested-meta-models-Muse-Glimmer-30B
OUR_CPUS=72-143,216-287
JOBS=${JOBS:-20}
CONF='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON'
TARGETS='runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit'
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
PIN="nice -n10 taskset -c $OUR_CPUS"
mark() { echo "$1" >"$RES/build-$TAG.done"; echo "=== build $TAG finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
# one build per tag at a time (the chain may be relaunched while a build still runs); a second copy exits without touching the marker
exec {BUILD_LOCK_FD}>"/var/tmp/jhan/$NAME.build-$TAG.lock"
flock -n "$BUILD_LOCK_FD" || { echo "$(ts) another build.sh $TAG holds /var/tmp/jhan/$NAME.build-$TAG.lock; this copy exits"; exit 1; }
rm -f "$RES/build-$TAG.done"
echo "=== build $TAG started $(ts) pid $$ on $(hostname) sha=$SHA conf=[$CONF] targets=[$TARGETS] jobs=$JOBS ksym_re=[$KSYM_RE] ksym_n=$KSYM_N ==="
case $TAG in *[!a-z0-9]*|'') fail "TAG '$TAG' is not lowercase alphanumerics" ;; esac
case $SHA in *[!0-9a-f]*|'') fail "SHA '$SHA' is not a hex sha" ;; esac
[ ${#SHA} -eq 40 ] || fail "SHA must be the full 40-hex sha (got ${#SHA} chars)"
case $KSYM_N in ''|*[!0-9]*) fail "KSYM_N '$KSYM_N' is not a number" ;; esac
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
# the ingest traces (torch export of every ingested model) are copied whole; the copied stamp is newer than its inputs, so the export step is skipped
if [ ! -d "$WT/ingest/traces" ]; then
  mkdir -p "$WT/ingest" && cp -r "$TRACES_SRC" "$WT/ingest/" || fail "cp -r $TRACES_SRC failed"
  echo "$(ts) ingest/traces copied from $TRACES_SRC"
fi
[ -e "$WT/ingest/traces/$GLIMMER_TRACE/torch-export.stamp" ] || fail "no Glimmer trace stamp under $WT/ingest/traces/$GLIMMER_TRACE"
cd "$WT" || fail "cd $WT"
t0=$(date +%s)
# 2026-10-17: the nix dev shell can no longer be built on 3bda, so the build runs in a plain shell with the host's clang 19.1.7
# and ccache, the way `make deb` does. gen/tokenize_py comes from the GNUmakefile target (uv from /tools/uv/0.9.5).
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
cp gen/runtron "gen/runtron.$TAG" || fail "cp gen/runtron"
BIN=$WT/gen/runtron.$TAG
# check 1: the AMX tile multiply instruction is in the binary (TRON_AMX_DISPATCH took)
n_amx=$($PIN objdump -d --no-show-raw-insn "$BIN" 2>/dev/null | grep -c -w tdpbf16ps || true)
# check 2: the attention path stats switch is compiled in (PR #4596)
n_stats=$($PIN grep -a -o TRON_ATTN_STATS "$BIN" | wc -l)
# check 3: the kernel symbols (mangled; the host nm cannot demangle the requires-clause templates of the head)
$PIN nm "$BIN" 2>/dev/null | grep -E "$KSYM_RE" | cut -c1-200 >"$RES/build-symbols-$TAG.txt" || true
n_sym=$(wc -l <"$RES/build-symbols-$TAG.txt")
{
  echo "tag $TAG worktree $WT"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s' | cut -c1-120))"
  echo "configure: cmake $CONF -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
  echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|TRON_K_VNNI|BUILD_INGEST_MODELS|CMAKE_CXX_COMPILER):' gen/CMakeCache.txt | tr '\n' ' ')"
  echo "compiler: $(clang++-19 --version | head -1)"
  echo "targets: $TARGETS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS with -j$JOBS"
  for tg in $TARGETS; do sha256sum "gen/$tg"; done
  sha256sum "$BIN"; echo "version: $("$BIN" --version 2>&1 | head -1)"
  echo "checks: tdpbf16ps=$n_amx (need > 0) TRON_ATTN_STATS=$n_stats (need > 0) kernel_symbols=$n_sym (need $KSYM_N, regex $KSYM_RE)"
} >"$RES/build-$TAG.txt"
cat "$RES/build-$TAG.txt"
[ "${n_amx:-0}" -gt 0 ] || fail "no tdpbf16ps in runtron.$TAG (the AMX kernel is not compiled in)"
[ "${n_stats:-0}" -gt 0 ] || fail "TRON_ATTN_STATS literal missing from runtron.$TAG"
[ "$n_sym" -eq "$KSYM_N" ] || fail "kernel symbol count $n_sym, expected $KSYM_N (see $RES/build-symbols-$TAG.txt)"
mark ok
