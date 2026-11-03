#!/usr/bin/env bash
# glimpl-20261017 build (runs ON delphi-3bda, detached by jhan, our half only): build runtron and the three AMX test
# binaries of branch jhan-amx-kvmul16 (the AMX attention kernels generalised to kv_mul 16 for Muse Glimmer) as a
# 3bda-local worktree of the shared repo at commit SHA. Fork of exec/td-20261016/build-variant.sh (worktree recipe,
# nix develop, our-half pinning) with the checks of exec/attnstats-20261002/chain.sh step A (AMX tile instructions,
# TRON_ATTN_STATS literal) and a new symbol check (the kernel template instantiations <4> and <16>).
# Words: tron = the inference program, runtron = its command-line tool; AMX = Intel tile-matrix instructions;
# kv_mul = query heads per KV head; the worktree = /var/tmp/jhan/tron-g16q (local disk, object store shared over NFS).
# Usage (on 3bda): SHA=<full 40-hex commit sha> bash build.sh         [JOBS=20] [KSYM_RE=<regex>] [KSYM_N=6]
# Log: exec/logs/glimpl-20261017-build.log. Marker: exec/results/glimpl-20261017/build.done = "ok" or "failed: <why>".
# Outputs: /var/tmp/jhan/tron-g16q/gen/{runtron.g16q,t_amx_numerics,t_amx_dispatch_dtype,t_llama_unit},
#          exec/results/glimpl-20261017/{build.txt,build-symbols.txt}.
# Never edit this file while a copy of it runs on 3bda (NFS: bash reads the script incrementally; fixes go into a new file name).
set -u
SHA=${SHA:?SHA=<full 40-hex commit sha of jhan-amx-kvmul16> is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=glimpl-20261017
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-build.log
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/tron-g16q
TAG=g16q
TRACES_SRC=/var/tmp/jhan/tron-pr4/ingest/traces
GLIMMER_TRACE=ingested-meta-models-Muse-Glimmer-30B
OUR_CPUS=72-143,216-287
JOBS=${JOBS:-20}
NIX=/home/jhan/.nix-profile/bin/nix
CONF='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON'
TARGETS='runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit'
# the kernel template instantiations the branch must produce: three kernels x two kv_mul values (4 = the llama shape, 16 = Glimmer)
KSYM_RE=${KSYM_RE:-'amx_attn_h128g4::(pack_q_group_128x4|qk_rowmajor_128x4|weights_times_v_128x4)<(4|16)'}
KSYM_N=${KSYM_N:-6}
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
PIN="nice -n10 taskset -c $OUR_CPUS"
mark() { echo "$1" >"$RES/build.done"; echo "=== build $TAG finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
rm -f "$RES/build.done"
echo "=== build $TAG started $(ts) pid $$ on $(hostname) sha=$SHA conf=[$CONF] targets=[$TARGETS] jobs=$JOBS ==="
case $SHA in *[!0-9a-f]*|'') fail "SHA '$SHA' is not a hex sha" ;; esac
[ ${#SHA} -eq 40 ] || fail "SHA must be the full 40-hex sha (got ${#SHA} chars)"
# the commit is made on claude-box into the shared object store; 3bda sees it after the NFS attribute cache refreshes (up to a minute)
for try in 1 2 3 4 5 6 7 8 9 10; do
  git -C "$REPO" cat-file -e "$SHA^{commit}" 2>/dev/null && break
  [ "$try" = 10 ] && fail "$SHA not visible in $REPO after 5 min (commit not made, or made elsewhere)"
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
# 2026-10-17: the nix dev shell can no longer be built on 3bda (its closure is gone from the local cache and the host has no
# mirror access), so the build runs in a plain shell with the host's clang 19.1.7 and ccache, the way `make deb` does
# (exec/glimci-20261017/build-deb.sh built the deb the same way at 17:58 UTC). gen/tokenize_py comes from the GNUmakefile
# target (uv from /tools/uv/0.9.5, as make deb uses it).
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
# check 3: the kernel template instantiations for kv_mul 4 and 16
$PIN nm -C "$BIN" 2>/dev/null | grep -E "$KSYM_RE" | cut -c1-200 >"$RES/build-symbols.txt" || true
n_sym=$(wc -l <"$RES/build-symbols.txt")
{
  echo "tag $TAG worktree $WT"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s' | cut -c1-120))"
  echo "configure: cmake $CONF"
  echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|TRON_K_VNNI|BUILD_INGEST_MODELS|CMAKE_CXX_COMPILER):' gen/CMakeCache.txt | tr '\n' ' ')"
  echo "targets: $TARGETS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS with -j$JOBS"
  for tg in $TARGETS; do sha256sum "gen/$tg"; done
  sha256sum "$BIN"; echo "version: $("$BIN" --version 2>&1 | head -1)"
  echo "checks: tdpbf16ps=$n_amx (need > 0) TRON_ATTN_STATS=$n_stats (need > 0) kernel_symbols=$n_sym (need $KSYM_N, regex $KSYM_RE)"
} >"$RES/build.txt"
cat "$RES/build.txt"
[ "${n_amx:-0}" -gt 0 ] || fail "no tdpbf16ps in runtron.$TAG (the AMX kernel is not compiled in)"
[ "${n_stats:-0}" -gt 0 ] || fail "TRON_ATTN_STATS literal missing from runtron.$TAG"
[ "$n_sym" -eq "$KSYM_N" ] || fail "kernel symbol count $n_sym, expected $KSYM_N (see $RES/build-symbols.txt; relaunch with KSYM_RE/KSYM_N if the branch names them differently)"
mark ok
