#!/usr/bin/env bash
# Light compile check of one commit of the jhan-amx-vnniK branch on delphi-3bda
# during the nightly CI window (4 cores, nice 19, no full build): fresh worktree
# on local disk, cmake configure, the fuse3 header dependency, then a
# syntax-only compile (-fsyntax-only) of the translation units that instantiate
# the K storage code, in TWO configurations: TRON_K_VNNI=ON (the VNNI layout)
# and OFF (the row-major layout must still compile).
# Usage: syn-check-vnni.sh <commit> <label>     (run on delphi-3bda)
set -u
COMMIT=$1; TAG=vnni-syn-$2
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
TUS="t/t_k_vnni_layout.cpp t/t_amx_dispatch_dtype.cpp t/t_amx_numerics.cpp t/t_llama_unit.cpp src/tron/gof.cpp t/t_gof_dma.cpp t/t_phase1_integration.cpp t/t_gof_staging_leaks.cpp src/tron/kernels/amx_attn.cpp"
for CFG in ON OFF; do
  nice -n19 taskset -c 72-75 nix develop --command bash -c '
    set -u
    CFG=$1; shift
    rm -rf gen
    cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=$CFG -DCMAKE_CXX_FLAGS= > cfg-$CFG.log 2>&1 || { echo "[$CFG] configure FAILED rc=$?"; tail -20 cfg-$CFG.log; exit 2; }
    echo "[$CFG] configure ok"
    if cmake --build gen --target libfuse3_external -j4 > dep-$CFG.log 2>&1; then echo "[$CFG] dep libfuse3_external ok"; else echo "[$CFG] dep build FAILED rc=$?"; tail -5 dep-$CFG.log; fi
    # the production TU that instantiates model.hpp / self_attention.hpp for a real plugin
    PROD=$(grep -l "self_attention.hpp\|models/model.hpp" src/tron/*.cpp src/tron/*/*.cpp 2>/dev/null | head -1)
    echo "[$CFG] production TU: ${PROD:-none}"
    for TU in "$@" $PROD; do
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
      bash syn_cmd.sh 2>&1 | grep -E "error:|warning:|note: " | grep -v "unused-command-line-argument" | head -40
      echo "[$CFG] syntax $TU rc=${PIPESTATUS[0]} in $(( $(date +%s) - t1 )) s"
    done
  ' _ "$CFG" $TUS
  echo "[$CFG] nix-develop rc=$?"
done
if command -v nix >/dev/null; then
  nix develop --command bash -c 'clang-format --version; for f in h/tron/kernels/k_vnni.hpp h/tron/kernels/amx_attn_iface.hpp h/tron/models/kv_cache.hpp h/tron/models/model.hpp h/tron/models/self_attention.hpp h/tron/scheduler/full.hpp h/tron/gof.hpp src/tron/gof.cpp src/tron/kernels/amx_attn.cpp t/t_k_vnni_layout.cpp t/t_amx_numerics.cpp t/t_amx_dispatch_dtype.cpp t/t_llama_unit.cpp t/t_gof_dma.cpp t/t_gof_staging_leaks.cpp t/t_phase1_integration.cpp; do if clang-format --dry-run --Werror "$f" >/dev/null 2>&1; then echo "clang-format clean: $f"; else echo "clang-format DIFF: $f"; clang-format --dry-run "$f" 2>&1 | grep -c "warning:" | sed "s/^/  warnings: /"; fi; done'
fi
echo "total $(( $(date +%s) - t0 )) s"
cd ~/workspace/tron-amx && git worktree remove --force "$WT" && echo "worktree removed"
echo "=== end $(date -u +%FT%TZ)"
touch "$DONE"
