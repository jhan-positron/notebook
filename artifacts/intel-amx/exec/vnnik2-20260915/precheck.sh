#!/usr/bin/env bash
# Light pre-check of a commit on delphi-3bda socket 0 (cpus 0-3, 8-11) while a campaign
# runs on socket 1: fresh worktree /var/tmp/jhan/tron-vnnik3, configure, syntax-only
# compile of t_llama_unit.cpp and t_k_vnni_layout.cpp, then the Haskell emitter tests.
# Usage: precheck.sh <commit>
set -u
COMMIT=$1
SRC_WT=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K
WT=/var/tmp/jhan/tron-vnnik3
OUT=/home/jhan/workspace/intel-AMX/exec/results/vnnik2-20260915/precheck-$COMMIT.txt
NIX=/home/jhan/.nix-profile/bin/nix
CPUS=0-3,8-11
exec >"$OUT" 2>&1
echo "=== precheck $COMMIT $(date -u +%FT%TZ)"
if [ ! -e "$WT/.git" ]; then
  ( cd /home/jhan/workspace/tron-amx && git fetch -q "$SRC_WT" "$COMMIT" && git worktree add --detach "$WT" "$COMMIT" ) || { echo worktree-failed; exit 1; }
else
  ( cd "$WT" && git fetch -q "$SRC_WT" "$COMMIT" && git checkout -q --detach "$COMMIT" ) || { echo checkout-failed; exit 1; }
fi
cd "$WT" || exit 1
echo "at $(git rev-parse HEAD)"
nice -n15 taskset -c $CPUS "$NIX" develop --command bash -c '
  set -o pipefail
  cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= 2>&1 | tail -2 || exit 2
  cmake --build gen --target libfuse3_external -j4 >/dev/null 2>&1 && echo "dep ok"
  for TU in t/t_k_vnni_layout.cpp t/t_llama_unit.cpp; do
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
  cd ingest && cabal test 2>&1 | tail -6; echo "cabal test rc=${PIPESTATUS[0]}"'
echo "=== end $(date -u +%FT%TZ)"
