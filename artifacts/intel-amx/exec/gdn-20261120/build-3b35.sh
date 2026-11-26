#!/usr/bin/env bash
# gdn-20261120 build. Runs ON delphi-3b35 (shared machine: other users hold the first half of the FPGA cards).
# Uses our CPUs only (96-143, low priority), local disk, no FPGA card, no huge page.
#
# What it builds: runtron (tron's command-line tool) with the generated plugin of ONE model, Qwen3.5 4B
# (tron slug ingested-qwen-3.5-4b). That model is not on tron main yet. It is registered by tron PR #3696, whose
# branch holds the whole open GatedDeltaNet (GDN) stack. SHA below = the head of that PR.
# The build selects the model with a one-model registry file (models.gdn.yaml in this folder, DEV_MODEL_CONFIG).
#
# Recipe = exec/glimext-20261018/build.sh (plain shell, host clang 19.1.7, ccache, uv venv for the export step),
# with two changes: the worktree lives under a 3b35 name, and no trace folder is copied (the model is exported here).
# Words: tron = the inference program; AMX = Intel tile-matrix instructions; TRON_AMX_DISPATCH = the build option
# that compiles the AMX kernels; trace = the torch export of the model that the ingest step turns into C++.
# Usage (on 3b35): bash build-3b35.sh   [TAG=base] [SHA=<40-hex>] [JOBS=40]
# Log: exec/logs/gdn-20261120-build-$TAG.log. Marker: exec/results/gdn-20261120/build-$TAG.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
TAG=${TAG:-base}
SHA=${SHA:-72e1191804ecb7591b23230439786a6a1ca784b8}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=gdn-20261120
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-build-$TAG.log
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/b35-gdn-$TAG
REG=$EXEC/$NAME/models.gdn.yaml
OUR_CPUS=96-143
JOBS=${JOBS:-40}
CONF="--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DDEV_MODEL_CONFIG=$WT/models.gdn.yaml"
TARGETS=${TARGETS:-'runtron t_gated_delta_net'}
mkdir -p "$RES" "$EXEC/logs" /var/tmp/jhan
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
PIN="nice -n10 taskset -c $OUR_CPUS"
mark() { echo "$1" >"$RES/build-$TAG.done"; echo "=== build $TAG finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
case $TAG in *[!a-z0-9]*|'') echo "TAG must be lowercase alphanumerics"; exit 1 ;; esac
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only (here: $(hostname))"; exit 1; }
exec {BUILD_LOCK_FD}>"/var/tmp/jhan/$NAME.build-$TAG.lock"
flock -n "$BUILD_LOCK_FD" || { echo "$(ts) another build-3b35.sh $TAG runs; this copy exits"; exit 1; }
rm -f "$RES/build-$TAG.done"
echo "=== build $TAG started $(ts) pid $$ on $(hostname) sha=$SHA conf=[$CONF] targets=[$TARGETS] jobs=$JOBS cpus=$OUR_CPUS ==="
echo "uptime: $(uptime)"
git -C "$REPO" cat-file -e "$SHA^{commit}" 2>/dev/null || fail "$SHA not visible in $REPO"
if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$SHA" || fail "git worktree add $WT failed"
  echo "$(ts) worktree $WT added at $SHA"
fi
[ "$(git -C "$WT" rev-parse HEAD 2>/dev/null)" = "$SHA" ] || fail "$WT is not at $SHA"
cp "$REG" "$WT/models.gdn.yaml" || fail "copy of $REG failed"
cd "$WT" || fail "cd $WT"
t0=$(date +%s)
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
$PIN bash -c '
  set -o pipefail
  make TOKENIZER_PYTHON_VERSION=3.12.7 ingest-deps 2>&1 | tail -4 || exit 2
  [ -x ingest/export/.venv/bin/python3 ] || { echo "ingest/export/.venv missing after make ingest-deps"; exit 2; }
  echo "ingest-deps ok $(date -u +%T): $(ingest/export/.venv/bin/python3 -c "import torch, transformers; print(\"torch\", torch.__version__, \"transformers\", transformers.__version__)" 2>&1 | tail -1)"
  make TOKENIZER_PYTHON_VERSION=3.12.7 gen/tokenize_py 2>&1 | tail -2 || exit 2
  [ -x gen/tokenize_py ] || { echo "gen/tokenize_py missing"; exit 2; }
  cmake '"$CONF"' -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache 2>&1 | tail -6 || exit 2
  echo "configure ok $(date -u +%T): $(grep -E "^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|DEV_MODEL_CONFIG|CMAKE_CXX_COMPILER):" gen/CMakeCache.txt | tr "\n" " ")"
  cmake --build gen --target '"$TARGETS"' -j'"$JOBS"' 2>&1 | grep -E "error|Error|FAILED|warning:|ninja: build stopped|Traceback|Exporting|Exception" | sed -n 1,200p
  exit ${PIPESTATUS[0]}'
rc=$?
echo "$(ts) build rc=$rc wall=$(( $(date +%s) - t0 ))s"
[ $rc -eq 2 ] && fail "configure or dependency step failed"
[ $rc -ne 0 ] && fail "build failed rc=$rc"
for tg in $TARGETS; do [ -x "gen/$tg" ] || fail "gen/$tg missing after the build"; done
n_amx=$($PIN objdump -d --no-show-raw-insn gen/runtron 2>/dev/null | grep -c -w tdpbf16ps || true)
n_stats=$($PIN grep -a -o TRON_ATTN_STATS gen/runtron | wc -l)
n_model=$($PIN grep -a -o 'ingested-qwen-3\.5-4b' gen/runtron | wc -l)
{
  echo "tag $TAG worktree $WT on $(hostname)"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s' | cut -c1-120))"
  echo "configure: cmake $CONF -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
  echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|DEV_MODEL_CONFIG|CMAKE_CXX_COMPILER):' gen/CMakeCache.txt | tr '\n' ' ')"
  echo "compiler: $(clang++-19 --version | head -1)"
  echo "targets: $TARGETS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS with -j$JOBS"
  for tg in $TARGETS; do sha256sum "gen/$tg"; done
  echo "checks: tdpbf16ps instructions in runtron = $n_amx (need > 0); TRON_ATTN_STATS literals = $n_stats (need > 0); model slug literals = $n_model (need > 0)"
} >"$RES/build-$TAG.txt"
cat "$RES/build-$TAG.txt"
[ "${n_amx:-0}" -gt 0 ] || fail "no tdpbf16ps in gen/runtron (the AMX kernel is not compiled in)"
[ "${n_stats:-0}" -gt 0 ] || fail "TRON_ATTN_STATS literal missing from gen/runtron"
[ "${n_model:-0}" -gt 0 ] || fail "model slug ingested-qwen-3.5-4b missing from gen/runtron"
mark ok
