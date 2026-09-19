#!/usr/bin/env bash
# Light functional pre-test of one commit of jhan-amx-vnniK during the CI window on
# delphi-3bda: 4 cores at nice 19, fresh worktree on local disk, TRON_K_VNNI=ON build of the
# three cheap unit tests (no runtron, no t_llama_unit), then run them. AMX is live on this
# host, so t_amx_numerics executes the kernels. Usage: pretest-light.sh <commit> <label>
set -u
COMMIT=$1; TAG=vnni-pretest-$2
WT=/var/tmp/jhan/tron-$TAG
OUT=/var/tmp/jhan/$TAG.out; DONE=/var/tmp/jhan/$TAG.done
rm -f "$OUT" "$DONE"
exec >>"$OUT" 2>&1
echo "=== $TAG commit=$COMMIT start $(date -u +%FT%TZ) load=$(cut -d' ' -f1-3 /proc/loadavg)"
cd ~/workspace/tron-amx || { echo no-checkout; touch "$DONE"; exit 1; }
git worktree remove --force "$WT" 2>/dev/null
git worktree add --detach "$WT" "$COMMIT" || { echo worktree-failed; touch "$DONE"; exit 1; }
cd "$WT" || exit 1
nice -n19 taskset -c 72-75 nix develop --command bash -c '
  set -u
  cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= > cfg.log 2>&1 || { echo "configure FAILED rc=$?"; tail -20 cfg.log; exit 2; }
  echo "configure ok (DISPATCH=ON K_VNNI=ON, ingest models OFF)"
  t0=$(date +%s)
  cmake --build gen --target t_k_vnni_layout t_amx_numerics t_amx_dispatch_dtype -j4 2>&1 | grep -E "error|FAILED|warning:" | grep -v "unused-command-line-argument" | head -60
  echo "build rc=${PIPESTATUS[0]} in $(( $(date +%s) - t0 )) s"
  for t in t_k_vnni_layout t_amx_numerics t_amx_dispatch_dtype; do
    [ -x gen/$t ] || { echo "$t: not built"; continue; }
    SYSTEM_CONFIG="--instance 1,2" timeout -k 30 1200 ./gen/$t > $t.out 2>&1
    echo "$t rc=$? $(grep -E "test cases:|All tests passed|FAILED|AMX unavailable|assertions" $t.out | tr "\n" " " | cut -c1-300)"
  done
' 2>&1 | grep -v "^warning: ignoring untrusted\|^Pass '--accept-flake-config'"
echo "=== end $(date -u +%FT%TZ)"
touch "$DONE"
