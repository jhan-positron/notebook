#!/bin/bash
# Rebuild the PR-2 branch jhan-vnnik-2-amx (PR2-handoff.md steps 1-3) from the PR-1 head
# jhan-vnnik-1-layout: apply the patch ref/PR2-diff-76a0..4d3a.patch with --3way (one known
# conflict, the dispatch diagram line of amx_attn_iface.hpp, resolved by exact text), revert the
# five PR-1-only comment edits by exact text (step 2), then two commits (step 3). Deterministic.
# Re-run after any fix (from a clean worktree). usage: bash build-branch.sh   (BASE=<ref> overrides jhan-vnnik-1-layout)
set -euo pipefail
W=/home/jhan/workspace/ai-runs/tron-split-pr2; BASE=${BASE:-jhan-vnnik-1-layout}
PATCH=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material/ref/PR2-diff-76a0..4d3a.patch
D=$(cd "$(dirname "$0")" && pwd)
G="git -C $W -c core.hooksPath=/dev/null"
[ -z "$(git -C $W status --porcelain)" ] || { echo "worktree not clean"; exit 1; }
$G checkout -q -B jhan-vnnik-2-amx $BASE
echo "base: $($G rev-parse --short=10 HEAD) ($BASE)"
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
# Step 1: the patch. Expected: rc 1, 8 files applied cleanly, UU h/tron/kernels/amx_attn_iface.hpp only.
set +e; $G apply --3way "$PATCH"; rc=$?; set -e
[ "$rc" = 1 ] || { echo "git apply rc=$rc (expected 1: the one diagram conflict)"; exit 1; }
[ "$($G status --porcelain | grep -c '^UU ')" = 1 ] && $G status --porcelain | grep -q '^UU h/tron/kernels/amx_attn_iface.hpp$' || { echo "unexpected conflict set:"; $G status --porcelain; exit 1; }
IFACE=h/tron/kernels/amx_attn_iface.hpp
LINE='//      |                 (VNNI K: k_vnni::qk_group)  |      (VNNI K: qk_vnni_128x4)\n'
if grep -q '^<<<<<<< ours$' "$W/$IFACE"; then
  edit $IFACE \
    '<<<<<<< ours\n//      |                 (VNNI K: k_vnni::qk_group)  |      (VNNI K: not taken until\n//      |                                              |      the VNNI AMX kernel lands)\n=======\n'"$LINE"'>>>>>>> theirs\n' \
    "$LINE"
else
  echo "no conflict markers: rerere resolved the file on its own; checking the result"
fi
grep -q 'VNNI K: qk_vnni_128x4' "$W/$IFACE" || { echo "restored diagram line missing"; exit 1; }
grep -q 'not taken until' "$W/$IFACE" && { echo "PR-1 diagram line still present"; exit 1; }
[ "$(grep -c -E '^(<<<<<<<|=======|>>>>>>>)' "$W/$IFACE")" = 0 ] || { echo "conflict markers left"; exit 1; }
[ "$(awk 'NR==61 {print length($0)}' "$W/$IFACE")" = 84 ] || { echo "diagram line 61 is not 84 columns"; exit 1; }
$G add $IFACE
# Step 2: the five PR-1-only comment edits reverted (old text at 82d05e94be -> the wording of 4d3a042225).
edit h/tron/models/kv_cache.hpp \
  '// the numerics contract in Note [AMX attention dispatch]). Until the VNNI AMX\n// kernel is merged, TRON_AMX_DISABLE=1 changes no score and no visit path for\n// 128-dimension heads. No AMX visit can occur for a VNNI slot.\n' \
  '// the numerics contract in Note [AMX attention dispatch]).\n'
edit h/tron/kernels/k_vnni.hpp \
  '// K VNNI layout (h/tron/tensor/k_vnni.hpp). Until the VNNI AMX kernel is\n// merged it serves every page of a VNNI slot; after that, partial pages, hosts\n// without AMX (Advanced Matrix Extensions, the tile instruction set) and the\n' \
  '// K VNNI layout (h/tron/tensor/k_vnni.hpp). It serves partial pages, hosts\n// without AMX (Advanced Matrix Extensions, the tile instruction set) and the\n'
edit h/tron/kernels/k_vnni.hpp \
  "// reader is the layout-specific reader allowed to take the plane address. q\n// points at kv_mul rows of 128 values (the group's heads, row stride 128).\n// kv_mul is any group size: a group of more than 16 heads is\n" \
  "// reader is one of the two layout-specific readers allowed to take the plane\n// address. q points at kv_mul rows of 128 values (the group's heads, row\n// stride 128). kv_mul is any group size: a group of more than 16 heads is\n"
edit h/tron/tensor/k_vnni.hpp \
  '// 64-byte alignment: every pair row is one 64-byte line.\n' \
  '// 64-byte alignment: every pair row is one 64-byte line, and the AMX QK kernel\n// reads the plane in 64-byte tile rows.\n'
edit t/t_llama_unit.cpp \
  '  // The 64-byte pair rows need a 64-byte-aligned plane.\n' \
  '  // The 64-byte pair rows and the AMX tile rows need a 64-byte-aligned plane.\n'
# Step 5: the pre-review fixes (PR2-handoff.md step 5.3; findings of workflow wf_f2fd0e23-1dd, recorded in split-status.md).
# (1) t_amx_dispatch_dtype.cpp: a per-packer count, so the test checks that the dispatch picks the packer of the build's layout.
edit t/t_amx_dispatch_dtype.cpp \
  '// the dispatch calls. The layouts are row-major, or under TRON_K_VNNI the VNNI\n// (Vector Neural Network Instructions) plane (Note [K VNNI storage] in\n// kv_cache.hpp). The fakes of both pairs count into the same probe. So the\n// expectations below hold for either layout.\n//   host_bf16, full page: the Q pack runs exactly once and sees the query\n//   values; the dense QK and PV kernels run once each.\n' \
  '// the dispatch calls. The layout is row-major, or under TRON_K_VNNI the VNNI\n// (Vector Neural Network Instructions) layout (Note [K VNNI storage] in\n// kv_cache.hpp). The fakes of both packers and both QK kernels count into the\n// same probe, and the fake of the VNNI packer counts a second time. So the\n// expectations below hold for either layout, and the VNNI packer count checks\n// that the dispatch picks the packer of the build'"'"'s layout (the two packers\n// share one signature; the kernel is pinned by its view type).\n//   host_bf16, full page: the Q pack runs exactly once and sees the query\n//   values. The dense QK and PV kernels run once each.\n'
edit t/t_amx_dispatch_dtype.cpp \
  'struct amx_probe {\n  size_t pack_calls = 0;\n' \
  'struct amx_probe {\n  size_t pack_calls = 0;\n  size_t rows_pack_calls = 0;  // pack_q_rows_128x4 only: the packers share a signature\n'
edit t/t_amx_dispatch_dtype.cpp \
  'void pack_q_rows_128x4(const bf16* input, bf16* output) noexcept {\n  ++probe.pack_calls;\n' \
  'void pack_q_rows_128x4(const bf16* input, bf16* output) noexcept {\n  ++probe.pack_calls;\n  ++probe.rows_pack_calls;\n'
edit t/t_amx_dispatch_dtype.cpp \
  '    REQUIRE(probe.pack_calls == (packs ? 1 : 0));\n' \
  '    REQUIRE(probe.pack_calls == (packs ? 1 : 0));\n    // The packer of the build'"'"'s K layout ran, never the other one.\n    REQUIRE(probe.rows_pack_calls == (packs && k_vnni::layout_on<head_size> ? 1 : 0));\n'
# (2) t_amx_numerics.cpp: the identity case'"'"'s comment (A/B defined, one claim per sentence, no one-word line), distinct fill
#     patterns for the two score arrays, a packer section for pack_q_rows_128x4, and the file header'"'"'s mention of the new case.
edit t/t_amx_numerics.cpp \
  "  // qk_vnni_128x4 reads K as the B operand and Q as the A operand.\n  // qk_rowmajor_128x4 reads K as the A operand and Q as the B operand\n  // (Note [QK orientation]). Both add the same four 32-dimension partial dots in\n  // the same order inside the tile multiply (the TDPBF16PS instruction, Note\n  // [QK orientation]). So the scores must agree to the bit. This is the check\n  // that the K store (store_row into a k_vnni_tensor) plus the kernel's panel\n  // addressing (a panel is one 16-token x 32-dimension block of the K plane,\n  // h/tron/tensor/k_vnni.hpp)\n  // reproduce the row-major kernel's scores. A wrong panel or dimension pair (two\n  // adjacent dimensions stored as one dword) would not reproduce them.\n" \
  "  // A and B are the left and right matrices of the AMX tile multiply (Note [QK\n  // orientation] in amx_attn_iface.hpp). qk_vnni_128x4 reads K as the B operand\n  // and Q as the A operand. qk_rowmajor_128x4 reads K as the A operand and Q as\n  // the B operand. Both add the same four 32-dimension partial dot products in\n  // the same order (steps 0 to 3 into one zeroed accumulator), and inside one\n  // tile multiply (TDPBF16PS) each score element is the same dot product of 16\n  // dimension pairs whichever operand holds K. So the scores must match bit for\n  // bit. This case checks that the K store (store_row into a k_vnni_tensor) and\n  // the kernel's panel addressing reproduce the row-major kernel's scores. A\n  // panel is one 16-token x 32-dimension block of the K plane\n  // (h/tron/tensor/k_vnni.hpp). A wrong panel or a wrong dimension pair (two\n  // adjacent dimensions stored as one 32-bit dword) would not reproduce them.\n"
edit t/t_amx_numerics.cpp \
  '    alignas(64) float s_row[GROUP_HEADS_4][PAGE_TOKENS_64];\n    alignas(64) float s_vnni[GROUP_HEADS_4][PAGE_TOKENS_64];\n' \
  '    // Different fill patterns: an element a kernel fails to write cannot match.\n    alignas(64) float s_row[GROUP_HEADS_4][PAGE_TOKENS_64] = {};\n    alignas(64) float s_vnni[GROUP_HEADS_4][PAGE_TOKENS_64];\n    std::memset(s_vnni, 0xff, sizeof(s_vnni));\n'
edit t/t_amx_numerics.cpp \
  '  // Layout contract of pack_q_group_128x4 (amx_attn_iface.hpp): a scalar\n  // copy, no AMX instruction runs, so this runs on every host. Distinct bit\n' \
  '  // Layout contracts of pack_q_group_128x4 and pack_q_rows_128x4\n  // (amx_attn_iface.hpp): scalar copies, no AMX instruction runs, so this runs\n  // on every host. Distinct bit\n'
edit t/t_amx_numerics.cpp \
  '              REQUIRE(got == 0);  // padding columns stay untouched\n            }\n          }\n        }\n      }\n    }\n  }\n}\n' \
  '              REQUIRE(got == 0);  // padding columns stay untouched\n            }\n          }\n        }\n      }\n    }\n  }\n  SECTION("A operand rows, pack_q_rows_128x4") {\n    // The contract is rows 0..3 only, so the padding rows hold a poison pattern,\n    // not zero: a packer that wrote them would be caught.\n    alignas(64) tron::bf16 padded[tron::amx_attn_h128g4::Q_PACK_ELEMS_2048];\n    constexpr uint16_t POISON_0X7F7F = 0x7f7fu;\n    for (auto& x : padded) {\n      x = tron::bf16::from_bits(POISON_0X7F7F);\n    }\n    tron::amx_attn_h128g4::pack_q_rows_128x4(q, padded);\n    for (size_t row = 0; row < TILE_ROWS_16; ++row) {\n      for (size_t dim = 0; dim < HEAD_SIZE_128; ++dim) {\n        const uint16_t got = padded[row * HEAD_SIZE_128 + dim].to_bits();\n        if (row < GROUP_HEADS_4) {\n          REQUIRE(got == q[row * HEAD_SIZE_128 + dim].to_bits());\n        } else {\n          REQUIRE(got == POISON_0X7F7F);  // padding rows stay untouched\n        }\n      }\n    }\n  }\n}\n'
edit t/t_amx_numerics.cpp \
  '// dropped token or dim block, a changed accumulation precision - fails.\n' \
  '// dropped token or dim block, a changed accumulation precision - fails.\n// The VNNI QK case pins qk_vnni_128x4 to qk_rowmajor_128x4 bit for bit\n// instead: the two kernels add the same products in the same order.\n'
# (3) amx_attn_iface.hpp: the Notes and declaration comments name both kernels and both packers where they apply.
edit h/tron/kernels/amx_attn_iface.hpp \
  $'// qk_rowmajor_128x4 stores its result tiles into a buffer inside the kernel\\n// (s_transposed), and the transpose that reads that buffer writes only the 4\\n// query rows into the caller\'s `s`, so `s` needs only 4 rows\\n// (s[4][s_stride_floats]).\\n' \
  $'// Both QK kernels store their result tiles into a buffer inside the kernel\\n// (s_transposed in qk_rowmajor_128x4, s16 in qk_vnni_128x4). The transpose\\n// that reads s_transposed, and the row copy that reads s16, write only the\\n// 4 query rows into the caller\'s `s`, so `s` needs only 4 rows\\n// (s[4][s_stride_floats]).\\n'
edit h/tron/kernels/amx_attn_iface.hpp \
  "// That is the same buffer size as pack_q_group_128x4's output. One slot\n// therefore serves either layout.\n" \
  "// That is the same buffer size as pack_q_group_128x4's output. One query-pack\n// slot (amx_qpack_slot in self_attention.hpp) therefore serves either layout.\n// The build's K layout picks one packer and one kernel (k_vnni::layout_on).\n"
edit h/tron/kernels/amx_attn_iface.hpp \
  "// mistake. q_rows = the pack_q_rows_128x4 output.\n" \
  "// mistake. q_rows = the pack_q_rows_128x4 output. For the same K and Q the\n// scores are bit-identical to qk_rowmajor_128x4's: both kernels add the same\n// four 32-dimension partial dot products in the same order inside TDPBF16PS\n// (t_amx_numerics checks the identity).\n"
edit h/tron/kernels/amx_attn_iface.hpp \
  '// takes the 4 query rows, padded to 16 rows, as the A operand. The 16 K panels\n// of the page are the B operand. The tiles come out as S[query][token]. No\n// transpose is needed. The price moves to the K store (a scatter of 64\n// dimension pairs per token, in save_k) and to the software reader\n// k_vnni::qk_group for partial pages.\n' \
  '// takes the 4 query rows, padded to 16 rows, as the A operand. The 16 K panels\n// of the page (a panel is 16 dimension-pair rows x 16 tokens, one B tile;\n// h/tron/tensor/k_vnni.hpp) are the B operand. The tiles come out as\n// S[query][token]. No transpose is needed. The extra work moves to the K store\n// (a scatter of 64 dimension pairs per token, in save_k) and to the software\n// reader k_vnni::qk_group for partial pages.\n'
edit h/tron/kernels/amx_attn_iface.hpp \
  '// The scalar half of the gate: pack_q_group_128x4 takes `const bf16*` and\n// copies the values without conversion, so the executor'"'"'s activation scalar\n' \
  '// The scalar half of the gate: both query packers (pack_q_group_128x4 and\n// pack_q_rows_128x4) take `const bf16*` and copy the values without\n// conversion, so the executor'"'"'s activation scalar\n'
edit h/tron/kernels/amx_attn_iface.hpp \
  '// One packed Q group (the pack_q_group_128x4 output buffer): 4 panels x 16\n// dim-pair rows x 16 columns x 2 = 2048 bf16 = 4096 bytes, padding included.\n' \
  '// One packed Q group, the output buffer of either packer, padding included:\n// pack_q_group_128x4 fills 4 panels x 16 dim-pair rows x 16 columns x 2, and\n// pack_q_rows_128x4 fills 16 rows x 128 dims. Both are 2048 bf16 = 4096 bytes.\n'
edit h/tron/kernels/amx_attn_iface.hpp \
  '// completely (64 tokens = 4 tiles of 16 rows). Everything else, incomplete\n// or partially visible pages, pages outside the sliding window, other\n' \
  '// completely (64 tokens = 4 tiles of 16 rows). With TRON_K_VNNI the roles\n// swap: Q is the A operand (16 rows, 4 of them live) and the stored K plane\n// is the B operand (Note [QK orientation]). Everything else, incomplete\n// or partially visible pages, pages outside the sliding window, other\n'
# (4) kv_cache.hpp: Note [K VNNI storage] item 3 lists every visit the reader serves; two wording fixes.
edit h/tron/models/kv_cache.hpp \
  '//   3. the software path for partial pages, the kill switch\n//      (TRON_AMX_DISABLE=1) and hosts without AMX use k_vnni::qk_group with\n//      the same view. That reader is AVX-512 code with one token per vector\n//      lane. It needs no per-token gather and no horizontal reduction. The\n' \
  '//   3. every other visit of a VNNI slot uses k_vnni::qk_group with the same\n//      view: partial or partly visible pages, the kill switch\n//      (TRON_AMX_DISABLE=1), hosts without AMX, builds without\n//      TRON_AMX_DISPATCH, and the shapes and query types outside the AMX\n//      gate (Note [AMX attention dispatch]). That reader is AVX-512 code\n//      with one token per vector lane. It needs no per-token gather and no\n//      horizontal reduction. The\n'
edit h/tron/models/kv_cache.hpp \
  '  // qk_vnni_128x4 reads it in place as its B operand, the AVX-512 reader\n  // k_vnni::qk_group one token per lane). VNNI slots only (Note [K VNNI\n' \
  '  // qk_vnni_128x4 reads it in place as its B operand, and the AVX-512 reader\n  // k_vnni::qk_group reads it one token per lane). VNNI slots only (Note [K VNNI\n'
edit h/tron/models/kv_cache.hpp \
  '// Why: the AMX QK kernel reads the VNNI plane directly as its B operand. It\n// computes the scores S = Q . K^T in the orientation the softmax wants\n// (qk_vnni_128x4). So the transposing store of the row-major kernel\n' \
  '// Why: the AMX QK kernel (qk_vnni_128x4) reads the VNNI plane directly as its\n// B operand. It computes the scores S = Q . K^T in the orientation the softmax\n// wants. So the transposing store of the row-major kernel\n'
# (5) kernels/k_vnni.hpp: the header lists every page the reader serves; the reader names the other score kernel.
edit h/tron/kernels/k_vnni.hpp \
  '// K VNNI layout (h/tron/tensor/k_vnni.hpp). It serves partial pages, hosts\n// without AMX (Advanced Matrix Extensions, the tile instruction set) and the\n// AMX kill switch (TRON_AMX_DISABLE=1). No AMX instruction runs here. So any\n' \
  '// K VNNI layout (h/tron/tensor/k_vnni.hpp). It serves every page the AMX\n// (Advanced Matrix Extensions, the tile instruction set) kernel qk_vnni_128x4\n// does not take: partial or partly visible pages, hosts without AMX, the AMX\n// kill switch (TRON_AMX_DISABLE=1), builds without TRON_AMX_DISPATCH, and the\n// shapes and query types outside the AMX gate (Note [AMX attention dispatch]\n// in amx_attn_iface.hpp). No AMX instruction runs here. So any\n'
edit h/tron/kernels/k_vnni.hpp \
  "// reader is one of the two layout-specific readers allowed to take the plane\n// address. q points at kv_mul rows of 128 values (the group's heads, row\n// stride 128). kv_mul is any group size: a group of more than 16 heads is\n" \
  "// reader is one of the two layout-specific score kernels allowed to take the\n// plane address (the other is amx_attn_h128g4::qk_vnni_128x4). q points at\n// kv_mul rows of 128 values (the group's heads, row stride 128). kv_mul is\n// any group size: a group of more than 16 heads is\n"
# (6) tensor/k_vnni.hpp: the header names the AMX kernel's file beside the reader's.
edit h/tron/tensor/k_vnni.hpp \
  '// rows in and out (store_row, load_row, copy_token). The AVX-512\n// score reader of this layout is in h/tron/kernels/k_vnni.hpp. Who writes and\n' \
  '// rows in and out (store_row, load_row, copy_token). The AVX-512 score reader\n// of this layout is in h/tron/kernels/k_vnni.hpp and the AMX QK kernel in\n// h/tron/kernels/amx_attn_iface.hpp. Who writes and\n'
# (7) self_attention.hpp: the slot comment names both packers'"'"' contract and the Note; A and B defined before use; plain wording.
edit h/tron/models/self_attention.hpp \
  "    // pack_q_group_128x4 for row-major K, or of pack_q_rows_128x4 for VNNI K):\n    // 4096 bytes. alignas(64) meets the packer's 64-byte\n    // alignment contract; std::vector routes over-aligned elements through\n    // the aligned operator new.\n" \
  "    // pack_q_group_128x4 for row-major K, or of pack_q_rows_128x4 for VNNI K,\n    // Note [K VNNI storage] in kv_cache.hpp): 4096 bytes. alignas(64) meets\n    // both packers' 64-byte alignment contract; std::vector routes\n    // over-aligned elements through the aligned operator new.\n"
edit h/tron/models/self_attention.hpp \
  '        // kv_cache.hpp). The VNNI plane (K in the Vector Neural Network\n        // Instructions layout, pair-interleaved) is the B operand of\n        // qk_vnni_128x4. A and B are the left and right matrices of the AMX\n        // (Advanced Matrix Extensions) tile multiply. So Q is packed as its A\n        // operand (rows). The row-major K page is the A operand of\n        // qk_rowmajor_128x4. So Q is packed as its B operand.\n' \
  '        // kv_cache.hpp). A and B are the left and right matrices of the AMX\n        // (Advanced Matrix Extensions) tile multiply. The VNNI plane (K in the\n        // Vector Neural Network Instructions layout, pair-interleaved) is the B\n        // operand of qk_vnni_128x4. So Q is packed as its A operand (rows). The\n        // row-major K page is the A operand of qk_rowmajor_128x4. So Q is\n        // packed as its B operand (pair-interleaved columns).\n'
edit h/tron/models/self_attention.hpp \
  "      // loop fills. It reads K straight from storage, in the slot's layout\n" \
  "      // loop fills. It reads K directly from storage, in the slot's layout\n"
# (8) amx_attn.cpp: the accumulator comment names real identifiers; two more static_asserts tie the panel to the B tile.
edit src/tron/kernels/amx_attn.cpp \
  '  // used in turn. Token block b accumulates its scores in ACCUMULATOR_TILE_b.\n' \
  '  // used in turn. Token block b (0..3) accumulates its scores in accumulator\n  // tile b (ACCUMULATOR_TILE_0 .. ACCUMULATOR_TILE_3).\n'
edit src/tron/kernels/amx_attn.cpp \
  '      "the 16 dim-pair rows of one K panel are the 16 rows of one B tile");\n' \
  '      "the 16 dim-pair rows of one K panel are the 16 rows of one B tile");\n  static_assert(k_vnni::LINE_BYTES_64 == TILE_ROW_BYTES_64,\n      "one pair row of the plane is one B tile row: the panel load stride");\n  static_assert(k_vnni::PANEL_BYTES_1024 == TILE_ROWS_16 * TILE_ROW_BYTES_64,\n      "one K panel is exactly one B tile");\n'
# (9) t_llama_unit.cpp: the typed-boundary comment says what the kernel accepts.
edit t/t_llama_unit.cpp \
  '  // QK kernel takes its view and nothing else. The other two kernels reject it.\n' \
  '  // QK kernel accepts the view, and no other type, as its K argument. The other\n  // two kernels reject it.\n'
# (10) README.ci.md: the kernel case exercises the store and the kernel, in every dispatch build.
edit README.ci.md \
  '`t_k_vnni_layout`, the `save_k` case of `t_llama_unit` and the VNNI kernel\ncase of `t_amx_numerics` exercise the VNNI store, the reader and the page copy.\nThe kernel case executes AMX only on a Granite Rapids runner, as above. The\n' \
  '`t_k_vnni_layout` and the `save_k` case of `t_llama_unit` exercise the VNNI\nstore, the reader and the page copy. The VNNI kernel case of `t_amx_numerics`\nexercises the store and the AMX kernel `qk_vnni_128x4`. That case compiles in\nevery `TRON_AMX_DISPATCH=ON` build, with or without this option, and executes\nAMX only on a Granite Rapids runner, as above. The\n'
# Step 3: two commits. (a) the kernel, its callers, the comment updates and the dispatch fakes; (b) the tests and README.
$G reset -q
$G add src/tron/kernels/amx_attn.cpp h/tron/kernels/amx_attn_iface.hpp h/tron/models/self_attention.hpp h/tron/models/kv_cache.hpp h/tron/kernels/k_vnni.hpp h/tron/tensor/k_vnni.hpp t/t_amx_dispatch_dtype.cpp
commit a
$G add t/t_amx_numerics.cpp t/t_llama_unit.cpp README.ci.md
commit b
echo "branch: $($G branch --show-current); status lines: $($G status --porcelain | wc -l)"
$G log --oneline $BASE..HEAD
$G diff --numstat $BASE HEAD | awk '{a+=$1; r+=$2; n++} END {print "files " n " +" a "/-" r}'
