#!/bin/bash
# Rebuild the PR-1 branch jhan-vnnik-1-layout (create-PR1-handoff.md steps 1-3) from the
# merge base: six topical commits from the tree 76a0160b72 (the kernels commit carries the
# 88-column rewrap of the amx_attn_iface diagram line), the PR-1-only commit (D2 and the
# comment rewrites), then the merge of origin/main. Deterministic. Re-run after any fix.
# usage: bash build-branch.sh   (MAIN=<ref> overrides origin/main)
set -euo pipefail
W=/home/jhan/workspace/ai-runs/tron-split-pr1; T=76a0160b72; BASE=be0d5565b3; MAIN=${MAIN:-origin/main}
D=$(cd "$(dirname "$0")" && pwd)
G="git -C $W -c core.hooksPath=/dev/null"
[ -z "$(git -C $W status --porcelain)" ] || { echo "worktree not clean"; exit 1; }
$G checkout -q -B jhan-vnnik-1-layout $BASE
take() { $G checkout -q $T -- "$@"; }
commit() { $G commit -q --no-verify -F $D/msgs/$1.txt; echo "$1 $($G rev-parse --short=10 HEAD)"; }
edit() {  # edit <file> <python literal old> <python literal new>: exact replacement, exactly one match
  python3 - "$W/$1" "$2" "$3" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); old = sys.argv[2].encode().decode('unicode_escape'); new = sys.argv[3].encode().decode('unicode_escape')
s = p.read_text(); n = s.count(old)
if n != 1: print(f"FAIL {p}: {n} matches for {old[:70]!r}"); sys.exit(1)
p.write_text(s.replace(old, new))
PY
}
take h/tron/tensor/k_vnni.hpp h/tron/tensor/kv_cache_fwd.hpp; commit a
take h/tron/models/kv_cache.hpp h/tron/models/model.hpp CMakeLists.txt src/tron/CMakeLists.txt; commit b
take h/tron/kernels/k_vnni.hpp h/tron/models/self_attention.hpp h/tron/models/attn_stats.hpp h/tron/kernels/amx_attn_iface.hpp
# The diagram line of 76a0160b72 is 100 columns (limit 88): two lines, the separators aligned.
edit h/tron/kernels/amx_attn_iface.hpp \
  '//      |                 (VNNI K: k_vnni::qk_group)  |      (VNNI K: not taken, see apply_page_tok)\n' \
  '//      |                 (VNNI K: k_vnni::qk_group)  |      (VNNI K: not taken until\n//      |                                              |      the VNNI AMX kernel lands)\n'
$G add -A .; commit c
take h/tron/gof.hpp src/tron/gof.cpp h/tron/scheduler/full.hpp t/t_gof_dma.cpp t/t_gof_staging_leaks.cpp t/t_phase1_integration.cpp; commit d
take t/t_k_vnni_layout.cpp t/t_llama_unit.cpp t/t_amx_dispatch_dtype.cpp t/CMakeLists.txt config/test-benchmarks.json; commit e
take .github/workflows/cmake-single-platform.yml README.ci.md; commit f
# The six commits reproduce the tree of 76a0160b72 except the rewrapped diagram line.
if [ "$($G diff $T --stat | wc -l)" != 2 ] || ! $G diff $T --stat | grep -q 'amx_attn_iface.hpp'; then echo "tree differs from $T beyond the diagram line:"; $G diff $T --stat; exit 1; fi
# Step 2: the PR-1-only commit (D2 and the comment rewrites of create-PR1-handoff.md step 2).
edit src/tron/CMakeLists.txt \
  '# The AMX (Intel Advanced Matrix Extensions) QK kernel (QK, the query-key\n# product) that reads the layout is in the dispatch translation unit above. The\n# option therefore requires TRON_AMX_DISPATCH.\nif(TRON_K_VNNI)\n  if(NOT TRON_AMX_DISPATCH)\n    message(FATAL_ERROR "TRON_K_VNNI requires TRON_AMX_DISPATCH=ON")\n  endif()\n  target_compile_definitions(tron PUBLIC TRON_K_VNNI)\nendif()\n' \
  'if(TRON_K_VNNI)\n  target_compile_definitions(tron PUBLIC TRON_K_VNNI)\nendif()\n'
edit CMakeLists.txt \
  '(requires TRON_AMX_DISPATCH; see Note [K VNNI storage] in h/tron/models/kv_cache.hpp)' \
  '(see Note [K VNNI storage] in h/tron/models/kv_cache.hpp)'
edit h/tron/kernels/k_vnni.hpp \
  '// K VNNI layout (h/tron/tensor/k_vnni.hpp). It serves partial pages, hosts\n// without AMX (Advanced Matrix Extensions, the tile instruction set) and the\n' \
  '// K VNNI layout (h/tron/tensor/k_vnni.hpp). Until the VNNI AMX kernel is\n// merged it serves every page of a VNNI slot; after that, partial pages, hosts\n// without AMX (Advanced Matrix Extensions, the tile instruction set) and the\n'
edit h/tron/kernels/k_vnni.hpp \
  "// reader is one of the two layout-specific readers allowed to take the plane\n// address. q points at kv_mul rows of 128 values (the group's heads, row\n// stride 128). kv_mul is any group size: a group of more than 16 heads is\n" \
  "// reader is the layout-specific reader allowed to take the plane address. q\n// points at kv_mul rows of 128 values (the group's heads, row stride 128).\n// kv_mul is any group size: a group of more than 16 heads is\n"
edit h/tron/tensor/k_vnni.hpp \
  '// 64-byte alignment: every pair row is one 64-byte line, and the AMX QK kernel\n// reads the plane in 64-byte tile rows.\n' \
  '// 64-byte alignment: every pair row is one 64-byte line.\n'
edit t/t_llama_unit.cpp \
  '  // The 64-byte pair rows and the AMX tile rows need a 64-byte-aligned plane.\n' \
  '  // The 64-byte pair rows need a 64-byte-aligned plane.\n'
edit h/tron/models/kv_cache.hpp \
  '// With TRON_K_VNNI (CMake option, default OFF, requires TRON_AMX_DISPATCH) the\n// K plane of every 128-dimension head holds the VNNI pair-interleaved layout of\n' \
  '// With TRON_K_VNNI (CMake option, default OFF) the K plane of every\n// 128-dimension head holds the VNNI pair-interleaved layout of\n'
edit h/tron/models/kv_cache.hpp \
  '// the numerics contract in Note [AMX attention dispatch]).\n\n// A kv_block holds two planes' \
  '// the numerics contract in Note [AMX attention dispatch]). Until the VNNI AMX\n// kernel is merged, TRON_AMX_DISABLE=1 changes no score and no visit path for\n// 128-dimension heads. No AMX visit can occur for a VNNI slot.\n\n// A kv_block holds two planes'
$G add -A .; commit g
# Step 3: merge main (a merge, not a rebase: the repo convention for reviewed branches).
if ! $G merge --no-ff --no-commit $MAIN > /dev/null; then echo "MERGE CONFLICTS:"; $G diff --name-only --diff-filter=U; exit 1; fi
$G commit -q --no-verify -F $D/msgs/merge.txt; echo "merge $($G rev-parse --short=10 HEAD) ($MAIN = $($G rev-parse --short=10 $MAIN))"
echo "branch: $($G branch --show-current); status lines: $($G status --porcelain | wc -l)"
$G log --oneline $BASE..HEAD
