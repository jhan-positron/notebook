#!/usr/bin/env python3
"""Apply the 24 accepted review proposals of PR #4887 (review 5528392683, 2026-10-15) by exact
line-range replacement. Each edit names new-file line numbers at head 0ee8671d35, the text the first
and last old line must contain (a guard against a shifted file), and the replacement lines.
Edits within a file are applied bottom-up so the earlier line numbers stay valid.
usage: apply.py <worktree> [--dry]"""
import sys, pathlib
W = pathlib.Path(sys.argv[1]); dry = '--dry' in sys.argv
E = []  # (file, first, last, first_contains, last_contains, new_lines)
def e(f, a, b, fc, lc, new): E.append((f, a, b, fc, lc, new))

f = 'h/tron/kernels/amx_attn_iface.hpp'
e(f, 145, 147, 'One packed Q group, the output buffer', 'Both are 2048 bf16 = 4096 bytes.', [
"// Element count of either query packer's output buffer (4096 bytes), padding included."])
e(f, 242, 249, 'Pack one query group as the A operand', 'picks one packer and one kernel (k_vnni::layout_on).', [
"// Pack one query group as the A operand of qk_vnni_128x4: the 4 heads' 128-dim",
"// bf16 rows copied as stored into rows 0..3 of `padded`. Rows 4..15 are zero",
"// padding the caller keeps zero: this call writes rows 0..3 only. `padded`",
"// holds Q_PACK_ELEMS_2048 bf16 (4096 bytes), aligned to 64 bytes."])
e(f, 252, 264, 'Dense QK for one page whose K is stored in the VNNI layout', '(t_amx_numerics checks the identity).', [
"// Dense QK for one page whose K is stored in the VNNI layout: computes",
"// S = Q . K^T with no transpose (Note [QK orientation]); writes",
"// s[4][s_stride_floats] fp32, all 64 token columns, UNSCALED. k_page = the",
"// page's packed K plane (layout in h/tron/tensor/k_vnni.hpp); q_rows = the",
"// pack_q_rows_128x4 output. The scores are bit-identical to qk_rowmajor_128x4's",
"// (the same four 32-dim partial sums in the same order; t_amx_numerics checks)."])

f = 'h/tron/kernels/k_vnni.hpp'
e(f, 2, 10, "The AVX-512 (the CPU's 512-bit vector instruction set) QK score reader", 'reads it are described in Note [K VNNI storage] (in kv_cache.hpp).', [
"// The AVX-512 QK score reader of the K VNNI layout (h/tron/tensor/k_vnni.hpp).",
"// It serves every page the AMX kernel qk_vnni_128x4",
"// does not take (Note [AMX attention dispatch] in amx_attn_iface.hpp). No AMX",
"// instruction runs here. So any translation unit may include it. The layout",
"// itself, who writes it and who reads it are described in Note [K VNNI storage]",
"// (in kv_cache.hpp)."])
e(f, 46, 50, "k_page is the page's packed K plane as its typed view (page::k_packed). This", 'any group size: a group of more than 16 heads is', [
"// k_page is the page's packed K plane as its typed view (page::k_packed). This",
"// reader is allowed to take the plane address (detail::k_vnni_access). q points",
"// at kv_mul rows of 128 values (the group's heads, row stride 128). kv_mul is",
"// any group size: a group of more than 16 heads is"])

f = 'h/tron/models/kv_cache.hpp'
e(f, 1987, 1992, "This page's packed K plane for one KV head of one slot, read-only: the", '// instead.', [
"  // This page's packed K plane for one KV head of one slot, read-only. VNNI",
"  // slots only (Note [K VNNI storage]). Internal cache writes take writable views",
"  // from the block owner instead."])

f = 'h/tron/models/self_attention.hpp'
e(f, 256, 260, 'One packed query group for the AMX attention path (the output of', 'over-aligned elements through the aligned operator new.', [
"    // One packed query group for the AMX attention path (the output of",
"    // pack_q_group_128x4 or of pack_q_rows_128x4): 4096 bytes. alignas(64) meets",
"    // both packers' 64-byte alignment contract; std::vector routes over-aligned",
"    // elements through the aligned operator new."])
e(f, 1553, 1556, 'resize() zero-fills new slots. The packer writes only the 4 live', 'packers rely on stays zero (the pack contracts in amx_attn_iface.hpp).', [
"        // resize() zero-fills new slots. Both packers rely on the padding they",
"        // do not write staying zero (the pack contracts in amx_attn_iface.hpp)."])
e(f, 1700, 1706, "The pack matches the slot's K layout (Note [K VNNI storage] in", 'packed as its B operand (pair-interleaved columns).', [
"        // The K layout picks the packer. Each QK kernel takes Q as a different",
"        // tile operand (Note [QK orientation] in amx_attn_iface.hpp)."])
e(f, 1763, 1773, 'QK for the whole page in one kernel call. The kernel writes the raw', 'consecutive rows. The view types state the layout at the call.', [
"      // QK for the whole page in one kernel call. The kernel writes the raw",
"      // scores, not yet multiplied by the attention scale, into",
"      // s_pages[head][token]. That is the same array and layout the software",
"      // loop fills. It reads K directly from storage, in the slot's layout",
"      // (Note [K VNNI storage] in kv_cache.hpp). In the row-major layout the",
"      // argument is this (slot, kv_head)'s whole K plane, a const_native_k_view",
"      // of 64 consecutive 128-dim rows. That call is the only place where the",
"      // AMX path depends on K being stored as consecutive rows. The view types",
"      // state the layout at the call."])

f = 'h/tron/tensor/k_vnni.hpp'
e(f, 119, 122, 'The one route from a packed K view to its plane address, for the typed', 'documented exception (Note [K VNNI storage] in kv_cache.hpp).', [
"// The one route from a packed K view to its plane address. Who may use it is",
"// listed at the top of this file (Who may compute a packed address)."])
e(f, 180, 181, '64-byte alignment: every pair row is one 64-byte line, and the AMX QK kernel', 'reads the plane in 64-byte tile rows.', [
"// 64-byte alignment: every pair row is one 64-byte line."])

f = 'src/tron/kernels/amx_attn.cpp'
e(f, 58, 60, 'qk_vnni_128x4: the padded Q rows load into tile 4. In each dimension step,', 'blocks 1 and 3 into tile 6.', [
"// qk_vnni_128x4: the K panels of token blocks 0 and 2 load into tile 5, those of",
"// blocks 1 and 3 into tile 6."])
e(f, 231, 236, 'S[16 q][64 tok] = Q . K^T. K is read from the VNNI (Vector Neural Network', '0..3 = the four 16-token blocks.', [
"// S[16 q][64 tok] = Q . K^T in tiles (A = the padded Q rows, B = the K panels as",
"// stored), then rows 0..3 copied into the caller's s buffer (UNSCALED). See the",
"// declaration and Note [K VNNI storage] in kv_cache.hpp."])
e(f, 241, 243, "The plane's first element: panel (step 0, block 0), pair row 0. This kernel", '(the other is k_vnni::qk_group).', [
"  // This kernel is one of the two layout-specific readers allowed to take the",
"  // plane address."])
e(f, 250, 253, 'One K panel = 16 dimension-pair rows x 16 tokens x 2 paired values (1 KiB).', '// tile row.', [])
e(f, 269, 272, 'Tile registers: the padded Q rows are the A operand in Q_ROWS_TILE_4. The', 'tile b (ACCUMULATOR_TILE_0 .. ACCUMULATOR_TILE_3).', [])

f = 't/t_amx_dispatch_dtype.cpp'
e(f, 8, 15, 'present. The K layout of the build selects which packer and which QK kernel', 'share one signature; the kernel is pinned by its view type).', [
"// present. Under TRON_K_VNNI the K plane holds the VNNI (Vector Neural Network",
"// Instructions) layout (Note [K VNNI storage] in kv_cache.hpp) and the dispatch",
"// calls the VNNI packer and QK kernel. The expectations below hold for either",
"// layout. The QK kernels differ in their K view type and the packers do not, so",
"// only the packer choice needs its own count (rows_pack_calls)."])
e(f, 170, 170, 'The dense predicate: the kernels run only for a full page.', 'The dense predicate: the kernels run only for a full page.', [])

f = 't/t_amx_numerics.cpp'
e(f, 122, 126, 'Layout contracts of pack_q_group_128x4 and pack_q_rows_128x4', 'comparison is on the bit patterns, not on float equality.', [
"  // Both packers are scalar copies, no AMX instruction runs, so this runs on",
"  // every host. Distinct bit patterns per element, so a wrong index cannot pass",
"  // by coincidence; the comparison is on the bit patterns, not on float equality."])

f = 't/t_llama_unit.cpp'
e(f, 101, 102, '', 'The VNNI K kernel takes the packed K plane (page::k_packed) the same way.', [])
e(f, 416, 420, 'The packed K plane (Note [K VNNI storage]) follows the same rules. The VNNI', '// only.', [
"  // The packed K plane (Note [K VNNI storage]) follows the same rules."])
e(f, 429, 430, 'STATIC_REQUIRE(', 'amx_qk_vnni_accepts<k_packed_mut_t>);  // writable converts to read-only', [
"  STATIC_REQUIRE(amx_qk_vnni_accepts<k_packed_mut_t>);"])
e(f, 433, 433, 'STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<k_plane_t>);  // the native K view', 'the native K view', [
"  STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<k_plane_t>);"])

byfile = {}
for ed in E: byfile.setdefault(ed[0], []).append(ed)
n_ok = 0
for fname, eds in byfile.items():
    p = W / fname; lines = p.read_text().split('\n')
    for (_, a, b, fc, lc, new) in sorted(eds, key=lambda x: -x[1]):
        old = lines[a-1:b]
        assert fc in old[0], (fname, a, old[0]); assert lc in old[-1], (fname, b, old[-1])
        assert len(old) == b - a + 1
        print(f"== {fname}:{a}-{b}  -{len(old)} +{len(new)}")
        for l in old: print('   -', l)
        for l in new: print('   +', l)
        lines[a-1:b] = new; n_ok += 1
    if not dry: p.write_text('\n'.join(lines))
print(f"{n_ok} edits {'checked (dry)' if dry else 'applied'}")
