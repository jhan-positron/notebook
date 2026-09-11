#!/usr/bin/env bash
# Rebuild PR 1's history as four topical commits from a finished stage-2 tip.
# Usage: make_topical.sh <stage2-tip> <new-branch>   (run inside the worktree
#        ~/workspace/ai-runs/tron-split; the stage-2 tip is a branch or SHA)
set -euo pipefail
TIP=${1:?stage-2 tip}; BR=${2:?new branch}
GA=(-c user.name="Jibin Han" -c user.email="jhan@positron.ai")
# Base = the PR's own base (the merge base of the tip with origin/main, i.e.
# main a80b102c18 for the 2026-09 split), not the moving origin/main: taking
# the tip's files onto a newer main would silently undo main's later changes
# to those files. Override with BASE=<commit> to rebase on purpose.
BASE=${BASE:-$(git merge-base origin/main "$TIP")}
echo "base: $(git rev-parse --short=10 "$BASE")"
git checkout -q -B "$BR" "$BASE"
take() { git checkout -q "$TIP" -- "$@"; }
# 1. kernel unit + interface (+ the doc that states the kernels' contracts)
take src/tron/kernels/amx_attn.cpp h/tron/kernels/amx_attn_iface.hpp doc/amx_software_attention.md
git "${GA[@]}" commit -q -F - <<'MSG'
attention: add row-major AMX kernels for the head-128, kv_mul-4 shape

Add the query packer, the row-major QK kernel qk_rowmajor_128x4 and the
weights-times-values kernel weights_times_v_128x4 in tron::amx_attn_h128g4,
plus their intrinsics-free interface header. AMX (Intel Advanced Matrix
Extensions) is the tile-matrix instruction set of Sapphire Rapids and later
Xeons; the test hosts are Granite Rapids. The kernels serve one attention
shape, head size 128 with 4 query heads per KV head, on bf16 (bfloat16)
inputs with fp32 accumulation.

The kernels read K exactly as it is stored (row-major, one 128-value row
per token): K is the A operand of the tile multiply, the packed Q group the
B operand, and the transposed result is transposed back on the way out
(Note [QK orientation]). No second copy of K or V is introduced.

Only src/tron/kernels/amx_attn.cpp is compiled with the AMX flags; nothing
calls the kernels yet (the dispatch and the build option follow). The
interface takes tron::bf16 pointers. available() probes CPUID, the OS tile
state and the Linux arch_prctl permission once per process, and honours
TRON_AMX_DISABLE=1; doc/amx_software_attention.md states that switch's
contract ("AMX off, same layout, same AVX dotter, clean-binary numerics"),
the numerical differences between the two paths, and how to verify.
MSG
# 2. dispatch integration
take h/tron/models/self_attention.hpp h/tron/models/kv_cache.hpp
git "${GA[@]}" commit -q -F - <<'MSG'
attention: dispatch dense bf16 pages of the AMX shape to the AMX kernels

Behind TRON_AMX_DISPATCH (not yet defined by any build; next commit), the
software attention loop takes the AMX path for one (query, page) pair when
the page is dense: all 64 tokens active, visible to the query in one range,
inside the sliding window (is_dense_amx_page). try_apply_dense_amx_page
does the whole step for such a page (QK, the same scale/max/exp math as the
AVX epilogue, PV, the v*/s*/m* update) and returns whether it ran; every
other page runs the existing AVX-512 dotter loop, which is unchanged.

Each token's Q group is packed once per apply_page_range call, at its first
page, into a thread-local 4096-byte slot (packed_amx_query; a std::bitset
records which tokens are done). The tile configuration is held for the
whole call. The model gate is amx_attn_h128g4::eligible: the shape and a
bf16 activation scalar; float and fp16 executors compile no AMX code.

kv_cache.hpp gains the raw V accessors page::v_data and kv_block::v_base
(the pair-interleaved V storage the PV kernel reads as its B operand) and a
named kv_block_planes constant; storage layout and constructors are
unchanged.
MSG
# 3. build option + CI flag
take CMakeLists.txt src/tron/CMakeLists.txt .github/workflows/cmake-single-platform.yml README.ci.md
git "${GA[@]}" commit -q -F - <<'MSG'
build: TRON_AMX_DISPATCH option (default OFF) and compile it in the CMake CI lane

option(TRON_AMX_DISPATCH) in the top-level CMakeLists.txt, next to the other
feature options. When ON, src/tron/CMakeLists.txt adds the kernel
translation unit with the AMX compiler flags (that one file only) and the
public TRON_AMX_DISPATCH definition that enables the dispatch. A default
build contains none of the AMX code.

The CMake CI workflow configures with -DTRON_AMX_DISPATCH=ON, so the
kernels and the dispatch compile in every run; the kernel tests execute
AMX when the test job lands on one of the three Granite Rapids runners and
skip with a warning elsewhere (issue #3997, option 1). A green run is not
by itself proof that AMX executed; doc/amx_software_attention.md says what
to record.
MSG
# 4. tests
take t/CMakeLists.txt t/t_amx_numerics.cpp t/t_amx_dispatch_dtype.cpp t/t_llama_unit.cpp
# cost data for the new tests (config/test-benchmarks.json) rides with the tests
# when the stage-2 tip has it; a no-op otherwise.
git checkout -q "$TIP" -- config/test-benchmarks.json 2>/dev/null || true
git "${GA[@]}" commit -q -F - <<'MSG'
test: AMX kernel numerics, dispatch eligibility and the dense-page predicate

t_amx_numerics: the compile-time eligibility gate (query_scalar_ok and
eligible over the executors' activation scalars and over the shape), the
query packer's layout (bit patterns compared), QK
against the AVX dotter within the fp32 add-order envelope, and PV within
the envelope of round-to-nearest (AMX) versus truncation (AVX) of the
softmax weights, both computed from the inputs; the two kernel checks skip
with a warning when AMX is unavailable.

t_amx_dispatch_dtype: drives the production apply_page_range with CPU fakes
for every amx_attn_h128g4 entry point (no AMX instruction linked). A bf16
executor packs once and calls QK and PV once for a full page; a 63-token
page packs but calls neither kernel (the dense predicate); float and fp16
executors never reach the fakes (the activation-scalar gate).

t_llama_unit: the bytes-per-page expression of the fixed-KV-layout case
uses the new named constant kv_block_planes instead of the literal 2; the
eligibility case the original PR added here was dropped because the first
case of t_amx_numerics checks the same predicate.
MSG
git log --oneline origin/main..HEAD
echo "tree identical to tip: $(git diff --quiet "$TIP" HEAD && echo yes || echo NO)"
