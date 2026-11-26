#!/usr/bin/env bash
# pr5022-optb-20261124 build. Runs ON delphi-3b35 (shared machine: other users hold the first half of the FPGA cards).
# Uses our CPUs only (96-143, low priority), local disk, no FPGA card, no huge page.
#
# What it builds: runtron (tron's command-line tool) and three unit tests from the head of tron PR 5022 after the
# rebase (commit 187da02163), with the plugins of two models: Muse Glimmer 30B and llama-3.1-8b-instruct-good.
#   TAG=a  the commit unchanged ("without the change").
#   TAG=b  the commit plus ONE changed declaration in h/tron/models/self_attention.hpp ("with the change", option B):
#            tensor<operation_kv_mul, page::page_size> s_pages{uninitialized};
#          becomes
#            auto s_pages =
#                make_array_of<tensor<page::page_size>, operation_kv_mul>(uninitialized);
# Both trees use one recipe, so a difference between the two binaries comes from that declaration.
# Recipe = exec/gdn-20261120/build-3b35.sh (plain shell, host clang 19.1.7, ccache, a registry file that selects the
# models), with the Glimmer trace copied from /var/tmp/jhan/seed-traces/b47f as exec/glimext-20261018/build.sh did.
# Words: tron = the inference program; AMX = Intel tile-matrix instructions; TRON_AMX_DISPATCH = the build option
# that compiles the AMX kernels; trace = the torch export of a model that the ingest step turns into C++.
# Usage (on 3b35): TAG=a|b bash build-3b35.sh   [JOBS=22]
# Log: exec/logs/pr5022-optb-20261124-build-$TAG.log (+ -ninja.log). Marker: exec/results/pr5022-optb-20261124/build-$TAG.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
TAG=${TAG:?TAG=a|b is required}
SHA=187da02163fe97db837dca6443983986f20c0ef8
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5022-optb-20261124
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-build-$TAG.log
NLOG=$EXEC/logs/$NAME-build-$TAG-ninja.log
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/b35-optb-$TAG
REG=$EXEC/$NAME/models.optb.yaml
TRACE=ingested-meta-models-Muse-Glimmer-30B
TRACE_SRC=/var/tmp/jhan/seed-traces/b47f/$TRACE
F=h/tron/models/self_attention.hpp
OUR_CPUS=96-143
JOBS=${JOBS:-22}
CONF="--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DDEV_MODEL_CONFIG=$WT/models.optb.yaml"
TARGETS=${TARGETS:-'runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit'}
# The build runs each new test binary once to list its cases, so the build needs this value too.
export SYSTEM_CONFIG="--instance 1,2"
mkdir -p "$RES" "$EXEC/logs" /var/tmp/jhan
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
PIN="nice -n10 taskset -c $OUR_CPUS"
mark() { echo "$1" >"$RES/build-$TAG.done"; echo "=== build $TAG finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
case $TAG in a|b) ;; *) echo "TAG must be a or b"; exit 1 ;; esac
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
cp "$REG" "$WT/models.optb.yaml" || fail "copy of $REG failed"
if [ ! -d "$WT/ingest/traces/$TRACE" ]; then
  mkdir -p "$WT/ingest/traces" && cp -r "$TRACE_SRC" "$WT/ingest/traces/" || fail "cp -r $TRACE_SRC failed"
  echo "$(ts) trace copied from $TRACE_SRC"
fi
[ -e "$WT/ingest/traces/$TRACE/torch-export.stamp" ] || fail "no Glimmer trace stamp under $WT/ingest/traces/$TRACE"
cd "$WT" || fail "cd $WT"
if [ "$TAG" = b ]; then
  python3 - "$F" <<'EOF' || fail "the option B edit did not apply"
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
old = "      tensor<operation_kv_mul, page::page_size> s_pages{uninitialized};\n"
new = ("      auto s_pages =\n"
       "          make_array_of<tensor<page::page_size>, operation_kv_mul>(uninitialized);\n")
if s.count(new) == 1 and s.count(old) == 0:
    print("the option B edit is already in the file")
elif s.count(old) == 1 and s.count(new) == 0:
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    print("the option B edit is applied")
else:
    sys.exit(f"unexpected file state: old x{s.count(old)}, new x{s.count(new)}")
EOF
fi
git diff -- . ':(exclude)models.optb.yaml' >"$RES/build-$TAG.diff"
n_diff=$(grep -c -E '^[+-][^+-]' "$RES/build-$TAG.diff")
echo "$(ts) source changes against $SHA: $n_diff changed lines (see $RES/build-$TAG.diff)"
if [ "$TAG" = a ]; then [ "$n_diff" -eq 0 ] || fail "tree a has source changes"; else [ "$n_diff" -eq 3 ] || fail "tree b has $n_diff changed lines, expected 3"; fi
t0=$(date +%s)
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
$PIN bash -c '
  set -o pipefail
  make TOKENIZER_PYTHON_VERSION=3.12.7 ingest-deps 2>&1 | tail -4 || exit 2
  [ -x ingest/export/.venv/bin/python3 ] || { echo "ingest/export/.venv missing after make ingest-deps"; exit 2; }
  make TOKENIZER_PYTHON_VERSION=3.12.7 gen/tokenize_py 2>&1 | tail -2 || exit 2
  [ -x gen/tokenize_py ] || { echo "gen/tokenize_py missing"; exit 2; }
  cmake '"$CONF"' -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache 2>&1 | tail -6 || exit 2
  echo "configure ok $(date -u +%T): $(grep -E "^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|DEV_MODEL_CONFIG|CMAKE_CXX_COMPILER):" gen/CMakeCache.txt | tr "\n" " ")"
  cmake --build gen --target '"$TARGETS"' -j'"$JOBS"' >"'"$NLOG"'" 2>&1'
rc=$?
echo "$(ts) build rc=$rc wall=$(( $(date +%s) - t0 ))s"
[ $rc -eq 2 ] && fail "configure or dependency step failed"
if [ $rc -ne 0 ]; then grep -E "error|Error|FAILED|ninja: build stopped|Traceback|Exception" "$NLOG" | sed -n 1,40p | cut -c1-400; fail "build failed rc=$rc"; fi
for tg in $TARGETS; do [ -x "gen/$tg" ] || fail "gen/$tg missing after the build"; done
n_amx=$($PIN objdump -d --no-show-raw-insn gen/runtron 2>/dev/null | grep -c -w tdpbf16ps || true)
n_glm=$($PIN grep -a -o 'ingested-meta-models--Muse-Glimmer-30B' gen/runtron | wc -l)
n_l8b=$($PIN grep -a -o 'llama-3\.1-8b-instruct-good' gen/runtron | wc -l)
{
  echo "tag $TAG worktree $WT on $(hostname)"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s' | cut -c1-120)); changed source lines: $n_diff"
  echo "configure: cmake $CONF -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
  echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|DEV_MODEL_CONFIG|CMAKE_CXX_COMPILER):' gen/CMakeCache.txt | tr '\n' ' ')"
  echo "compiler: $(clang++-19 --version | head -1)"
  echo "targets: $TARGETS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS with -j$JOBS"
  for tg in $TARGETS; do sha256sum "gen/$tg"; done
  echo "ninja steps: $(grep -c -E '^\[[0-9]+/[0-9]+\]' "$NLOG" || true); compiler warnings: $(grep -c 'warning:' "$NLOG" || true); trace exports in this build: $(grep -c -i 'exporting' "$NLOG" || true)"
  echo "checks: tdpbf16ps instructions in runtron = $n_amx (need > 0); Glimmer slug literals = $n_glm (need > 0); llama slug literals = $n_l8b (need > 0)"
} >"$RES/build-$TAG.txt"
cat "$RES/build-$TAG.txt"
[ "${n_amx:-0}" -gt 0 ] || fail "no tdpbf16ps in gen/runtron (the AMX kernel is not compiled in)"
[ "${n_glm:-0}" -gt 0 ] || fail "the Glimmer model slug is missing from gen/runtron"
[ "${n_l8b:-0}" -gt 0 ] || fail "the llama model slug is missing from gen/runtron"
mark ok
