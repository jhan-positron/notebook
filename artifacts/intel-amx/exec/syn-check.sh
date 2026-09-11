#!/usr/bin/env bash
# Light check of one commit: fresh worktree on local disk, cmake configure only,
# then a syntax-only compile of the TUs that instantiate the AMX dispatch.
# Usage: syn-check.sh <commit> <label>   (run on delphi-3bda, nice 19, few cores)
set -u
COMMIT=$1; TAG=syn-$2
WT=/var/tmp/jhan/tron-$TAG
OUT=/var/tmp/jhan/$TAG.out; DONE=/var/tmp/jhan/$TAG.done
rm -f "$OUT" "$DONE"
exec >>"$OUT" 2>&1
echo "=== $TAG commit=$COMMIT start $(date -u +%FT%TZ)"
cd ~/workspace/tron-amx || { echo no-checkout; touch "$DONE"; exit 1; }
git worktree remove --force "$WT" 2>/dev/null
git worktree add --detach "$WT" "$COMMIT" || { echo worktree-failed; touch "$DONE"; exit 1; }
cd "$WT" || exit 1
t0=$(date +%s)
nix develop --command bash -c '
  set -u
  cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS= > cfg.log 2>&1 || { echo "configure FAILED rc=$?"; tail -20 cfg.log; exit 2; }
  echo "configure ok"
  # Header-producing dependency (fuse3 is built by an ExternalProject step, so a
  # configure-only tree has no fuse3/*.h). Build just that target, few cores.
  if cmake --build gen --target libfuse3_external -j4 > dep.log 2>&1; then echo "dep libfuse3_external ok"; else echo "dep build FAILED rc=$?"; tail -5 dep.log; ninja -C gen -t targets all 2>/dev/null | grep -i fuse | head -5; fi
  if command -v clang-format >/dev/null 2>&1; then
    clang-format --version
    if clang-format --dry-run --Werror h/tron/models/self_attention.hpp >/dev/null 2>&1; then echo "clang-format: clean"; else echo "clang-format: DIFF"; clang-format --dry-run h/tron/models/self_attention.hpp 2>&1 | head -20; fi
  else echo "clang-format: not in nix shell"; fi
  PROD=$(grep -l "self_attention.hpp\|models/model.hpp" src/tron/*.cpp src/tron/*/*.cpp 2>/dev/null | head -1)
  echo "production TU: ${PROD:-none}"
  for TU in t/t_amx_dispatch_dtype.cpp $PROD; do
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
    t1=$(date +%s)
    bash syn_cmd.sh 2>&1 | grep -E "error:|warning:" | grep -v "unused-command-line-argument" | head -30
    echo "syntax $TU rc=${PIPESTATUS[0]} in $(( $(date +%s) - t1 )) s"
  done
'
echo "nix-develop rc=$? total $(( $(date +%s) - t0 )) s"
cd ~/workspace/tron-amx && git worktree remove --force "$WT" && echo "worktree removed"
echo "=== end $(date -u +%FT%TZ)"
touch "$DONE"
