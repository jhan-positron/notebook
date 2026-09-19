#!/usr/bin/env bash
# vnnik4-20260915 light pre-check of a commit on delphi-3bda socket 0 (cpus 0-3, 8-11,
# nice 15) while CI or a campaign owns the rest of the machine: fetch the commit from the
# NFS worktree into /var/tmp/jhan/tron-vnnik4 (the same configure the full build uses
# later), clang-format-19 check of every C++ file the branch changed against
# origin/jhan-amx-p0, syntax-only compile of the translation units that instantiate the
# VNNI K code, and (optionally, CABAL=1) the Haskell emitter tests.
# Usage (on delphi-3bda): precheck.sh <commit>   [TUS="..."] [CABAL=1]
set -u
COMMIT=$1
SRC_WT=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K
WT=${WT:-/var/tmp/jhan/tron-vnnik4}
OUT=${OUT:-/home/jhan/workspace/intel-AMX/exec/results/vnnik4-20260915/precheck-$COMMIT.txt}
NIX=/home/jhan/.nix-profile/bin/nix
CPUS=${CPUS:-0-3,8-11}
TUS=${TUS:-"t/t_k_vnni_layout.cpp t/t_llama_unit.cpp t/t_amx_numerics.cpp t/t_amx_dispatch_dtype.cpp src/tron/kernels/amx_attn.cpp src/tron/gof.cpp"}
mkdir -p "$(dirname "$OUT")"
exec >"$OUT" 2>&1
echo "=== precheck $COMMIT $(date -u +%FT%TZ)"
fetch_ok=0
for i in 1 2 3 4 5 6; do   # the NFS attribute cache can hide a fresh object for a while
  if [ ! -e "$WT/.git" ]; then
    ( cd /home/jhan/workspace/tron-amx && git fetch -q "$SRC_WT" "$COMMIT" && git worktree add --detach "$WT" "$COMMIT" ) && fetch_ok=1 && break
  else
    ( cd "$WT" && git fetch -q "$SRC_WT" "$COMMIT" && git checkout -q --detach "$COMMIT" ) && fetch_ok=1 && break
  fi
  echo "fetch attempt $i failed; retry in 20 s"; sleep 20
done
[ $fetch_ok = 1 ] || { echo "fetch-failed"; echo "=== end $(date -u +%FT%TZ)"; exit 1; }
cd "$WT" || exit 1
echo "at $(git rev-parse HEAD) ($(git log -1 --format='%s'))"
git fetch -q origin jhan-amx-p0 2>/dev/null || true
FILES=$(git diff --name-only origin/jhan-amx-p0 -- 'h/*.hpp' 'src/*.cpp' 't/*.cpp' | tr '\n' ' ')
echo "C++ files changed vs origin/jhan-amx-p0: $FILES"
nice -n15 taskset -c $CPUS "$NIX" develop --command bash -c '
  set -o pipefail
  echo "--- clang-format-19 --dry-run -Werror"
  clang-format-19 --dry-run -Werror '"$FILES"' 2>&1 | head -60; echo "clang-format rc=${PIPESTATUS[0]}"
  echo "--- configure"
  cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= 2>&1 | tail -2 || exit 2
  cmake --build gen --target libfuse3_external -j4 >/dev/null 2>&1 && echo "dep libfuse3_external ok"
  for TU in '"$TUS"'; do
    python3 - "$TU" <<PY > syn_cmd.sh
import json,sys,shlex
tu=sys.argv[1]; d=json.load(open("gen/compile_commands.json"))
e=next((e for e in d if e["file"].endswith("/"+tu)), None)
if e is None: print("echo no-compile-entry-for "+tu+"; exit 3"); sys.exit()
args=shlex.split(e["command"]); out=[]; skip=False
for a in args:
    if skip: skip=False; continue
    if a=="-o": skip=True; continue
    if a=="-c": continue
    out.append(a)
out.append("-fsyntax-only")
print("cd "+shlex.quote(e["directory"])+" && "+" ".join(shlex.quote(a) for a in out))
PY
    bash syn_cmd.sh 2>&1 | grep -E "error|warning:" | grep -v unused-command-line-argument | head -40
    echo "syntax $TU rc=${PIPESTATUS[0]} $(date -u +%T)"
  done
  if [ "'"${CABAL:-0}"'" = 1 ]; then cd ingest && cabal test 2>&1 | tail -6; echo "cabal test rc=${PIPESTATUS[0]}"; fi'
echo "=== end $(date -u +%FT%TZ)"
