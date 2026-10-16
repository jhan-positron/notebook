#!/usr/bin/env python3
"""Resolve the merge of origin/jhan-amx-vnniK (typed K owner/view, save_k worker fold)
into jhan-amx-vnniK-i4500 (issue #4500 row-major tail block + policy).

Every conflict block is replaced by index (1-based per file). Non-conflict edits are
exact-string replacements that assert their occurrence count. Run once."""
import re
import sys

W = "/home/jhan/workspace/ai-runs/tron-vnnik-i4500m/"
OURS = "<<<<<<< HEAD\n"
SEP = "=======\n"
THEIRS = ">>>>>>> origin/jhan-amx-vnniK\n"


def read(p):
    with open(W + p) as f:
        return f.read()


def write(p, s):
    with open(W + p, "w") as f:
        f.write(s)


def conflicts(s):
    """list of (start, end, ours, theirs) for every conflict block, in file order"""
    out = []
    pos = 0
    while True:
        a = s.find(OURS, pos)
        if a < 0:
            break
        m = s.find(SEP, a)
        e = s.find(THEIRS, m)
        assert m > a and e > m, "conflict markers out of order"
        e2 = e + len(THEIRS)
        out.append((a, e2, s[a + len(OURS):m], s[m + len(SEP):e]))
        pos = e2
    return out


def resolve(path, resolutions):
    """resolutions: dict index(1-based) -> text | 'ours' | 'theirs' | callable(ours, theirs)"""
    s = read(path)
    cs = conflicts(s)
    assert len(cs) == len(resolutions), f"{path}: {len(cs)} conflicts, {len(resolutions)} resolutions"
    out = []
    last = 0
    for i, (a, e, ours, theirs) in enumerate(cs, 1):
        r = resolutions[i]
        if r == "ours":
            t = ours
        elif r == "theirs":
            t = theirs
        elif callable(r):
            t = r(ours, theirs)
        else:
            t = r
        out.append(s[last:a])
        out.append(t)
        last = e
    out.append(s[last:])
    s = "".join(out)
    assert OURS not in s and THEIRS not in s, f"{path}: markers left"
    write(path, s)


def sub(path, old, new, count=1):
    s = read(path)
    n = s.count(old)
    assert n == count, f"{path}: expected {count} of {old[:60]!r}, found {n}"
    write(path, s.replace(old, new))


def sub_in(text, old, new, count=1):
    n = text.count(old)
    assert n == count, f"hunk: expected {count} of {old[:60]!r}, found {n}"
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# 1. h/tron/tensor/k_vnni.hpp: constants + the typed row-major tail-block operations
# ---------------------------------------------------------------------------
P = "h/tron/tensor/k_vnni.hpp"
sub(P, "// rows in and out (store_row, load_row, store_block, copy_token). The AVX-512\n"
       "// score reader of this layout is in h/tron/kernels/k_vnni.hpp. Who writes and\n"
       "// reads the layout is described in Note [K VNNI storage] (kv_cache.hpp).\n",
       "// rows in and out (store_row, load_row, store_block, copy_token), and the\n"
       "// in-place conversion of one 16-token block between its row-major and its VNNI\n"
       "// form (block_to_vnni, block_to_rows, Note [Row-major tail block] below). The\n"
       "// AVX-512 score reader of this layout is in h/tron/kernels/k_vnni.hpp. Who\n"
       "// writes and reads the layout is described in Note [K VNNI storage]\n"
       "// (kv_cache.hpp).\n")
sub(P, "#include <cstdint>\n#include <immintrin.h>\n", "#include <cstdint>\n#include <cstring>\n#include <immintrin.h>\n")
sub(P, "inline constexpr uint32_t HIGH_HALF_0XFFFF0000 = 0xffff0000u;\n",
       "inline constexpr uint32_t HIGH_HALF_0XFFFF0000 = 0xffff0000u;\n"
       "// A row-major block (Note [Row-major tail block] below) keeps 4 token rows of\n"
       "// 256 bytes in each of its 4 panels.\n"
       "inline constexpr size_t PANEL_ROWS_4 = PANEL_ELEMS_512 / HEAD_SIZE_128;\n"
       "// The 4 token blocks of a page, one bit each (page::k_vnni_blocks). A block\n"
       "// mask equal to it has every block of the page set.\n"
       "inline constexpr uint8_t BLOCKS_PER_PAGE_MASK_0XF = 0xfu;\n"
       "// Bit c of a block mask (page::k_vnni_blocks): token block c of the page.\n"
       "constexpr uint8_t block_bit(size_t c) noexcept {\n"
       "  return uint8_t(1u << c);\n"
       "}\n"
       "// Bit `offset` of a page-offset mask (the saved rows of a page): the row at\n"
       "// that page offset.\n"
       "constexpr uint64_t offset_bit(size_t offset) noexcept {\n"
       "  return uint64_t{1} << offset;\n"
       "}\n")
sub(P, "                  PANEL_DWORDS_256 == 256 && N_PANELS_16 == 16 && LANES_16 == 16,\n"
       "    \"every constant's name states its value\");\n",
       "                  PANEL_DWORDS_256 == 256 && N_PANELS_16 == 16 && LANES_16 == 16 &&\n"
       "                  PANEL_ROWS_4 == 4,\n"
       "    \"every constant's name states its value\");\n"
       "static_assert(BLOCKS_PER_PAGE_MASK_0XF == block_bit(TOKEN_BLOCKS_4) - 1,\n"
       "    \"one bit per token block\");\n")
TAIL_OPS = r'''
// Note [Row-major tail block]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~
// A 16-token block of the plane holds the VNNI layout above only once all 16
// of its K rows are saved. Until then the block holds its rows row-major:
// token t of block c owns 256 contiguous bytes (its 128 bf16 values in
// dimension order) at row_major_row(). Those bytes are the block's own 4
// panels: panel (t / 4, c) holds the rows of tokens 4 (t / 4) .. 4 (t / 4) + 3,
// 256 bytes each. So a row-major block and a VNNI block occupy the same 4 KiB,
// and no other block is touched by either layout.
// Why: in decode every step saves one token per user. The VNNI scatter of one
// row writes 4 bytes into each of 64 lines; the row-major store writes 4 whole
// lines. The readers of an incomplete block (the AVX-512 tail scoring through
// the row-major dotter, and the FPGA staging gather) read 4 lines per token
// instead of 64 as well. At the forward end of the pass that saved the 16th
// row (or at once, when a whole-block save wrote the block), block_to_vnni()
// transposes the block in place (4 KiB read, 4 KiB written), and the AMX
// kernel reads the page as its B operand once every block of the page is
// VNNI. Which layout a block holds is recorded per (page, slot) by the page
// (its converted-block bit, Note [K VNNI storage] in kv_cache.hpp). The
// operations here take the layout from the caller.

// The token's row inside a row-major block, as a typed row view: Cols
// contiguous bf16 in dimension order, on a 64-byte line, not DMA memory. The
// caller knows from the page's state (page::k_vnni_blocks) that the block is
// row-major; the view does not say so.
template <typename T, size_t Rows, size_t Cols>
TRON(nodiscard, inline, pure)
auto row_major_row(k_vnni_view<T, Rows, Cols> plane, size_t token) noexcept {
  using row_t = std::conditional_t<std::is_const_v<T>, const_k_row_view<Cols>,
      k_row_view<Cols>>;
  const size_t c = token / k_vnni::BLOCK_TOKENS_16, t = token % k_vnni::BLOCK_TOKENS_16;
  return row_t{detail::k_vnni_access::plane(plane) +
               ((t / k_vnni::PANEL_ROWS_4) * k_vnni::TOKEN_BLOCKS_4 + c) *
                   k_vnni::PANEL_ELEMS_512 +
               (t % k_vnni::PANEL_ROWS_4) * Cols};
}

// Store one token's row into its row-major block: 4 whole 64-byte lines, the
// same lines the row-major layout's store writes.
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void store_row_major(k_vnni_view<bf16, Rows, Cols> dst,
    size_t token,
    const_k_row_view<Cols, Aligned, Dma> src) noexcept {
  std::memcpy(row_major_row(dst, token).data, src.data, Cols * sizeof(bf16));
}

// Load one token's row out of its row-major block (the inverse of
// store_row_major).
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void load_row_major(k_vnni_view<const bf16, Rows, Cols> src,
    size_t token,
    k_row_view<Cols, Aligned, Dma> dst) noexcept {
  std::memcpy(dst.data, row_major_row(src, token).data, Cols * sizeof(bf16));
}

// Convert block c from row-major (Note [Row-major tail block]) to the VNNI
// layout, in place. The 16 rows are copied to the stack first: store_block
// writes panel (s, c) while the rows of tokens 4 s .. 4 s + 3 still live there.
template <size_t Rows, size_t Cols>
TRON(inline)
void block_to_vnni(k_vnni_view<bf16, Rows, Cols> plane, size_t c) noexcept {
  alignas(k_vnni::LINE_BYTES_64) bf16 rows[k_vnni::BLOCK_TOKENS_16][Cols];
  const bf16* row_ptrs[k_vnni::BLOCK_TOKENS_16];
  const k_vnni_view<const bf16, Rows, Cols> source = plane;
  for (size_t t = 0; t < k_vnni::BLOCK_TOKENS_16; ++t) {
    load_row_major(
        source, c * k_vnni::BLOCK_TOKENS_16 + t, k_destination_row<Cols>(rows[t]));
    row_ptrs[t] = rows[t];
  }
  store_block(plane, c, k_vnni::FULL_BLOCK_0XFFFF, row_ptrs);
}

// The inverse: block c from the VNNI layout back to row-major, in place.
template <size_t Rows, size_t Cols>
TRON(inline)
void block_to_rows(k_vnni_view<bf16, Rows, Cols> plane, size_t c) noexcept {
  alignas(k_vnni::LINE_BYTES_64) bf16 rows[k_vnni::BLOCK_TOKENS_16][Cols];
  const k_vnni_view<const bf16, Rows, Cols> source = plane;
  for (size_t t = 0; t < k_vnni::BLOCK_TOKENS_16; ++t) {
    load_row(source, c * k_vnni::BLOCK_TOKENS_16 + t, k_destination_row<Cols>(rows[t]));
  }
  for (size_t t = 0; t < k_vnni::BLOCK_TOKENS_16; ++t) {
    store_row_major(plane, c * k_vnni::BLOCK_TOKENS_16 + t, k_source_row<Cols>(rows[t]));
  }
}

}  // namespace tron
'''
s = read(P)
end = "\n}  // namespace tron\n"
assert s.endswith(end), "tensor/k_vnni.hpp tail"
write(P, s[: -len(end)] + "\n" + TAIL_OPS.lstrip("\n"))

# ---------------------------------------------------------------------------
# 2. h/tron/kernels/k_vnni.hpp: the reader keeps the typed-view form of 4424
# ---------------------------------------------------------------------------
resolve("h/tron/kernels/k_vnni.hpp", {
    1: "theirs",
    2: "theirs",
    3: "// change the result. Every token block with a live bit must hold the VNNI\n"
       "// layout (Note [Row-major tail block] in h/tron/tensor/k_vnni.hpp): the\n"
       "// caller scores the tokens of a row-major block with the row-major dotter\n"
       "// and keeps their bits clear here. Token lanes: one 64-byte load supplies\n"
       "// one dimension pair of 16 tokens. The query's dimension pair is broadcast.\n"
       "// VDPBF16PS accumulates 16 scores at once. So there is no horizontal\n"
       "// reduction and no per-token gather. k_page is the page's packed K plane as\n"
       "// its typed view (page::k_packed). This reader is one of the two\n"
       "// layout-specific readers allowed to take the plane address. q points at\n"
       "// kv_mul rows of 128 values (the group's heads, row stride 128). kv_mul is\n"
       "// any group size: a group of more than 16 heads is scored 16 heads at a\n"
       "// time. Every head's scores are its own accumulation. So the split changes\n"
       "// no head's add order.\n",
})

# ---------------------------------------------------------------------------
# 3. h/tron/models/kv_cache.hpp
# ---------------------------------------------------------------------------
P = "h/tron/models/kv_cache.hpp"


def kv_h4(ours, theirs):
    t = ours
    t = sub_in(t,
        "          k_vnni::block_to_vnni(\n"
        "              reinterpret_cast<bf16*>(\n"
        "                  kv_block_at_storage<geometry>(storage_offset, kv_head).k),\n"
        "              c);\n",
        "          block_to_vnni(\n"
        "              kv_block_at_storage<geometry>(storage_offset, kv_head).k.as_view(), c);\n")
    t = sub_in(t, "// layout in place (Note [Row-major tail block] in k_vnni.hpp) when its 16\n",
                  "// layout in place (Note [Row-major tail block] in h/tron/tensor/k_vnni.hpp)\n  // when its 16\n")
    t = sub_in(t,
        "  // Layout-agnostic K row store: writes the token's head_size bf16 values\n"
        "  // (contiguous in `row`) into whichever layout the slot, and for a VNNI slot\n"
        "  // the token's block, uses (Note [K VNNI storage]). The row's saved bit is\n"
        "  // the caller's (note_k_row_saved).\n"
        "  template <kv_geometry geometry>\n",
        "  // Layout-agnostic K row store: writes the token's head_size bf16 values (one\n"
        "  // contiguous row, as a read-only typed view) into whichever layout the slot,\n"
        "  // and for a VNNI slot the token's block, uses (Note [K VNNI storage]). The\n"
        "  // row's `aligned` and `dma` flags are the caller's. The packed store reads\n"
        "  // the row with unaligned loads. The row's saved bit is the caller's\n"
        "  // (note_k_row_saved).\n"
        "  template <kv_geometry geometry, bool Aligned, bool Dma>\n")
    return t


resolve(P, {
    1: "//      pass's tokens fills one whole 16-token block of a page. The 16 rows are\n"
       "//      transposed in registers. Every 64-byte pair row of the four panels (a\n"
       "//      panel: the 16 pair rows of one 32-dimension step for one 16-token\n"
       "//      block, 1 KiB) is written whole (store_block). Any shorter run\n"
       "//      (decode: one token per user per step; the last block of a prompt) is\n"
       "//      stored row by row with page::set_k_row: 4 whole 64-byte lines per\n"
       "//      token into the row-major tail block (store_row_major), the same store\n"
       "//      the row-major layout makes. When a pass holds more than 16 tokens the\n"
       "//      store may be shared with the idle main helpers (Note [Shared block\n"
       "//      save] in model.hpp). TRON_AMX_DISABLE leaves both store paths\n"
       "//      untouched.\n"
       "//   2. the dense AMX page path (self_attention.hpp) passes page::k_packed, the\n"
       "//      read-only view of the plane, to qk_vnni_128x4 when page::k_vnni_blocks\n"
       "//      says every block of the page is converted. A page whose last block\n"
       "//      waits for the forward end, a page with a block that stays row-major\n"
       "//      under hardware attention, or a page filled by another writer than\n"
       "//      save_k, takes the software loop.\n"
       "//   3. the software path for partial pages, the kill switch\n"
       "//      (TRON_AMX_DISABLE=1) and hosts without AMX read the VNNI blocks with\n"
       "//      k_vnni::qk_group, with the same view. That reader is AVX-512 code with\n"
       "//      one token per vector lane. It needs no per-token gather and no\n"
       "//      horizontal reduction. The tokens of the row-major tail block are\n"
       "//      scored with the row-major dotter (the per-token dot-product loop of\n"
       "//      self_attention.hpp) through their typed row (row_major_row), 4 lines\n"
       "//      per token.\n",
    2: "//      as one owner assignment (dst_block.k = src_block.k) when the range\n"
       "//      covers the page, bits included. A token's position inside the page\n"
       "//      decides its column. So every other range moves token by token: the\n"
       "//      converted destination blocks the range touches are made row-major\n"
       "//      first (block_to_rows), the rows are copied row-major, and a block\n"
       "//      whose 16 rows are saved after the copy is converted to VNNI\n"
       "//      (block_to_vnni).\n"
       "//   6. the row view page::k() does not exist for VNNI slots. A token's values\n"
       "//      are not contiguous there. The layout-agnostic set_k_row / get_k_row\n"
       "//      accessors exist for every slot. They take one token's row as a typed\n"
       "//      view (const_k_row_view / k_row_view) and follow the block's recorded\n"
       "//      layout.\n",
    3: "  // This page's packed K plane for one KV head of one slot, read-only: the\n"
       "  // argument type of the layout-specific score kernels (the AMX QK kernel\n"
       "  // qk_vnni_128x4 reads it in place as its B operand, the AVX-512 reader\n"
       "  // k_vnni::qk_group one token per lane). VNNI slots only (Note [K VNNI\n"
       "  // storage]). Internal cache writes take writable views from the block owner\n"
       "  // instead. Only the blocks named by k_vnni_blocks hold the VNNI layout; the\n"
       "  // others hold row-major rows (Note [Row-major tail block] in\n"
       "  // h/tron/tensor/k_vnni.hpp, read through row_major_row).\n",
    4: kv_h4,
    5: "      auto plane = kv_block<geometry>(slot, kv_head).k.as_view();\n"
       "      if (k_block_is_vnni(k_state_ix(slot), i_page)) {\n"
       "        store_row(plane, i_page, row);\n"
       "      } else {\n"
       "        store_row_major(plane, i_page, row);\n"
       "      }\n",
    6: "  // K rows of the 16 tokens of one 16-token block of this page, stored at\n"
       "  // once in the VNNI layout (VNNI slots only, Note [K VNNI storage] item 1).\n"
       "  // Block c holds the page offsets c * 16 .. c * 16 + 15; rows[t] (128 bf16)\n"
       "  // is the row of offset c * 16 + t. The result is bit-identical to set_k_row\n"
       "  // per token of a complete block (store_block). The difference is the write\n"
       "  // pattern. The 16 row pointers are native source rows in dimension order,\n"
       "  // not packed storage. The caller records the block with note_k_block_saved\n"
       "  // after the last KV head.\n",
    7: "    store_block(kv_block<geometry>(slot, kv_head).k.as_view(), c,\n"
       "        k_vnni::FULL_BLOCK_0XFFFF, rows);\n",
    8: "      const auto plane = kv_block<geometry>(slot, kv_head).k.as_view();\n"
       "      if (k_block_is_vnni(k_state_ix(slot), i_page)) {\n"
       "        load_row(plane, i_page, row);\n"
       "      } else {\n"
       "        load_row_major(plane, i_page, row);\n"
       "      }\n",
    9: "  // The token's K row in place when its block is row-major (Note [Row-major\n"
       "  // blocks under hardware attention]): a typed row view of head_size\n"
       "  // contiguous bf16 inside the block's own panels, valid as long as no writer\n"
       "  // touches the block (the same rule as get_k_row's read). An invalid view\n"
       "  // for a converted block: the caller gathers that one with get_k_row.\n"
       "  template <kv_geometry geometry>\n"
       "    requires(book_t::template declares_geometry<geometry>() &&\n"
       "             k_vnni::layout_on<geometry.head_size>)\n"
       "  TRON(nodiscard, inline)\n"
       "  k_row_view<geometry.head_size> k_row_if_row_major(\n"
       "      kv_slot_id slot, size_t kv_head, size_t i_page) noexcept TRON(this_lifetimebound)\n"
       "  {\n"
       "    TRON_ASSERT_LT(i_page, page_size);\n"
       "    if (k_block_is_vnni(k_state_ix(slot), i_page)) {\n"
       "      return k_row_view<geometry.head_size>{};\n"
       "    }\n"
       "    return row_major_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page);\n"
       "  }\n\n",
    10: "        // VNNI plane (Note [K VNNI storage] item 5): a token's column depends\n"
        "        // on its offset in the page. So a whole-page copy copies the owner\n"
        "        // (the defaulted assignment of the trivially copyable k_vnni_tensor),\n"
        "        // bits included. Every other range moves token by token, through\n"
        "        // row-major rows: the destination blocks the range touches are made\n"
        "        // row-major first, and those complete after the copy are converted to\n"
        "        // VNNI at the end (block_to_rows / block_to_vnni in\n"
        "        // h/tron/tensor/k_vnni.hpp).\n"
        "        auto const& src_block =\n"
        "            src_page->template kv_block_at_storage<geometry>(storage_offset, kv_head);\n"
        "        auto& dst_block = kv_block_at_storage<geometry>(storage_offset, kv_head);\n"
        "        if (whole_page) {\n"
        "          dst_block.k = src_block.k;\n"
        "          new_blocks = src_blocks;\n"
        "        } else {\n"
        "          const auto src_plane = src_block.k.as_view();\n"
        "          auto dst_plane = dst_block.k.as_view();\n"
        "          // The blocks the range [dst_begin, dst_begin + count) touches.\n"
        "          const size_t c_begin = dst_begin / k_vnni::BLOCK_TOKENS_16;\n"
        "          const size_t dst_end = dst_begin + count;\n"
        "          for (size_t c = c_begin; c * k_vnni::BLOCK_TOKENS_16 < dst_end; ++c) {\n"
        "            if ((dst_blocks & k_vnni::block_bit(c)) != 0) {\n"
        "              block_to_rows(dst_plane, c);\n"
        "              new_blocks &= uint8_t(~k_vnni::block_bit(c));\n"
        "            }\n"
        "          }\n"
        "          for (size_t i = 0; i < count; ++i) {\n"
        "            const size_t src_c = (src_begin + i) / k_vnni::BLOCK_TOKENS_16;\n"
        "            if ((src_blocks & k_vnni::block_bit(src_c)) != 0) {\n"
        "              load_row(src_plane, src_begin + i, row_major_row(dst_plane, dst_begin + i));\n"
        "            } else {\n"
        "              store_row_major(\n"
        "                  dst_plane, dst_begin + i, row_major_row(src_plane, src_begin + i));\n"
        "            }\n"
        "          }\n"
        "          for (size_t c = c_begin; c * k_vnni::BLOCK_TOKENS_16 < dst_end; ++c) {\n"
        "            if ((new_saved & k_block_bits(c)) == k_block_bits(c)) {\n"
        "              block_to_vnni(dst_plane, c);\n"
        "              new_blocks |= k_vnni::block_bit(c);\n"
        "            }\n",
})
# non-conflict regions of kv_cache.hpp that still call the raw helpers
sub(P, "              k_vnni::block_to_rows(\n"
       "                  reinterpret_cast<bf16*>(\n"
       "                      kv_block_at_storage<geometry>(storage_offset, kv_head).k),\n"
       "                  c);\n",
       "              block_to_rows(\n"
       "                  kv_block_at_storage<geometry>(storage_offset, kv_head).k.as_view(),\n"
       "                  c);\n")
sub(P, "// row-major inside the same 4 KiB (Note [Row-major tail block] in k_vnni.hpp)\n",
       "// row-major inside the same 4 KiB (Note [Row-major tail block] in\n// h/tron/tensor/k_vnni.hpp)\n")

# ---------------------------------------------------------------------------
# 4. h/tron/models/model.hpp
# ---------------------------------------------------------------------------
P = "h/tron/models/model.hpp"
resolve(P, {
    1: "    //   1. Block save (store_block in h/tron/tensor/k_vnni.hpp, page::set_k_block):\n"
       "    //      a run of the pass's tokens that fills one whole 16-token block of a\n"
       "    //      page is transposed in registers. It is then written as whole 64-byte\n",
    2: "    static constexpr size_t k_store_block = k_vnni::BLOCK_TOKENS_16;\n"
       "\n"
       "    // Note [K VNNI storage]: the 16-token blocks that this forward pass\n"
       "    // completed through runs shorter than a block, for the operations the\n"
       "    // hardware attention does not score (Note [Row-major blocks under\n"
       "    // hardware attention] in kv_cache.hpp). save_k queues them (main\n"
       "    // thread) and convert_pending_k_blocks converts them at the forward end,\n"
       "    // after wait_for_coop_gof: the cooperative GOF staging gather of an\n"
       "    // earlier minibatch is the reader that can still hold the block's rows\n"
       "    // row-major. The storage reference is taken at the save, so a storage\n"
       "    // view change cannot redirect the conversion.\n"
       "    struct pending_k_block {\n"
       "      page* pg;\n"
       "      typename page::k_storage_ref storage;\n"
       "      uint32_t block;\n"
       "    };\n"
       "    std::vector<pending_k_block> pending_k_blocks_;\n"
       "\n"
       "    // Convert the queued blocks (Note [K VNNI storage]). Main thread, after\n"
       "    // the plugin's run() returned and the cooperative GOF staging drained.\n"
       "    void convert_pending_k_blocks() noexcept {\n"
       "      if (pending_k_blocks_.empty()) return;\n"
       "      TRACE_EVENT(\"model\", \"convert_k_blocks\", \"blocks\", pending_k_blocks_.size());\n"
       "      for (pending_k_block const& b : pending_k_blocks_) {\n"
       "        b.pg->k_block_to_vnni_at(b.storage, b.block);\n"
       "      }\n"
       "      pending_k_blocks_.clear();\n"
       "    }\n",
    3: "    // that fill one whole 16-token block of one page are stored as one VNNI\n"
       "    // block (set_k_block). A shorter run is stored row by row (set_k_row)\n"
       "    // into the block's row-major form. Row-major slots: one row store per\n"
       "    // token and KV head (page::k(...).set). Marks, saved-row bits of partial\n"
       "    // runs and credits are not touched here. save_k_impl does them after\n"
       "    // every store is done.\n",
    4: "          if (n < k_store_block) {\n"
       "            // An incomplete block: row-major rows (Note [Row-major tail block]\n"
       "            // in h/tron/tensor/k_vnni.hpp), or the VNNI column when the block\n"
       "            // is complete already (a row saved again). set_k_row decides.\n",
})
sub(P, "                  static_cast<uint32_t>(j / K_STORE_BLOCK_16)});\n",
       "                  static_cast<uint32_t>(j / k_store_block)});\n")
sub(P, "    //      in k_vnni.hpp), also whole lines. A block completed that way is\n",
       "    //      in h/tron/tensor/k_vnni.hpp), also whole lines. A block completed that\n    //      way is\n")

# ---------------------------------------------------------------------------
# 5. h/tron/models/self_attention.hpp
# ---------------------------------------------------------------------------
P = "h/tron/models/self_attention.hpp"
resolve(P, {
    1: "        // relevant tokens of its VNNI blocks in `live`. It scores them after\n"
       "        // the loop with the AVX-512 (Advanced Vector Extensions, 512-bit\n"
       "        // vectors) reader k_vnni::qk_group, in passes of up to 16 heads over\n"
       "        // the plane. The tokens of a row-major tail block (Note [Row-major\n"
       "        // tail block] in h/tron/tensor/k_vnni.hpp) are scored with the\n"
       "        // dotters, through their typed row (row_major_row).\n",
    2: "          if (live != 0) {\n"
       "            k_vnni::qk_group<operation_kv_mul>(*plane,\n",
})
sub(P, "        // The VNNI slot: the blocks of the page that hold the VNNI layout, and\n"
       "        // the plane whose row-major tail rows the dotters read. Both are\n"
       "        // fetched at the first relevant token, like the row view below: a\n"
       "        // page nothing is relevant for is never asked (a book may have no\n"
       "        // active KV slot).\n"
       "        [[maybe_unused]] uint8_t vnni_blocks = 0;\n"
       "        [[maybe_unused]] const bf16* plane = nullptr;\n",
       "        // The VNNI slot: the blocks of the page that hold the VNNI layout, and\n"
       "        // the packed plane (page::k_packed) whose row-major tail rows the\n"
       "        // dotters read. Both are fetched at the first relevant token, like the\n"
       "        // row view below: a page nothing is relevant for is never asked (a\n"
       "        // book may have no active KV slot). A row-major slot has no packed\n"
       "        // plane, so `plane` is a placeholder there.\n"
       "        [[maybe_unused]] uint8_t vnni_blocks = 0;\n"
       "        [[maybe_unused]] auto plane = [&] {\n"
       "          if constexpr (k_vnni_on) {\n"
       "            return std::optional<decltype(page.template k_packed<geometry.kv>(\n"
       "                slot, kv_head))>{};\n"
       "          } else {\n"
       "            return 0;  // no packed plane: the row-major slot keeps rows\n"
       "          }\n"
       "        }();\n")
sub(P, "            if (plane == nullptr) {\n"
       "              vnni_blocks = page.template k_vnni_blocks<geometry.kv>(slot);\n"
       "              plane = page.template k_vnni_plane<geometry.kv>(slot, kv_head);\n"
       "            }\n",
       "            if (!plane) {\n"
       "              vnni_blocks = page.template k_vnni_blocks<geometry.kv>(slot);\n"
       "              plane = page.template k_packed<geometry.kv>(slot, kv_head);\n"
       "            }\n")
sub(P, "              const const_view<bf16, k_vnni::ROW_ALIGNED_TRUE, k_vnni::ROW_DMA_FALSE,\n"
       "                  seq<operation_head_size>>\n"
       "                  k{k_vnni::row_ptr(plane, i)};\n",
       "              const auto k = row_major_row(*plane, i);\n")

# ---------------------------------------------------------------------------
# 6. h/tron/scheduler/full.hpp
# ---------------------------------------------------------------------------
resolve("h/tron/scheduler/full.hpp", {
    1: "                        // kv_cache.hpp describes the layout. A row of a row-major\n"
       "                        // block (the usual case under hardware attention, Note\n"
       "                        // [Row-major blocks under hardware attention] there) is\n"
       "                        // read in place; a row of a converted block is gathered\n"
       "                        // into the caller's scratch buffer (dest: page_info's\n"
       "                        // 64-byte-aligned scratch, 256 bytes per head). The V\n"
       "                        // callback below always unpacks into the scratch.\n"
       "                        const auto row = pg_ptr->template k_row_if_row_major<hw_kv>(\n"
       "                            slot, kv_head, off);\n"
       "                        if (row.valid()) return row.data;\n"
       "                        pg_ptr->template get_k_row<hw_kv>(slot, kv_head, off,\n"
       "                            k_destination_row<hw_kv.head_size>(dest));\n",
})

# ---------------------------------------------------------------------------
# 7. h/tron/kernels/amx_attn_iface.hpp (comment reference only)
# ---------------------------------------------------------------------------
P = "h/tron/kernels/amx_attn_iface.hpp"
s = read(P)
m = re.search(r"^(// .*\(Note \[Row-major tail block\] in )k_vnni\.hpp\)(.*)$", s, re.M)
assert m, "amx_attn_iface reference"
sub(P, m.group(0), m.group(1) + "h/tron/tensor/k_vnni.hpp)" + m.group(2))

# ---------------------------------------------------------------------------
# 8. t/t_amx_dispatch_dtype.cpp
# ---------------------------------------------------------------------------
P = "t/t_amx_dispatch_dtype.cpp"
resolve(P, {
    1: "// `repeat` the call is made a second time with different query values.\n"
       "// `amx_available` is what the fake available() answers during the call. With\n"
       "// `record_rows` the stored rows are recorded like save_k records them, so the\n"
       "// page's blocks hold the VNNI layout under TRON_K_VNNI; without it a full page\n"
       "// keeps row-major blocks and the dense gate must refuse the AMX path.\n"
       "template <typename executor_t>\n"
       "void exercise_page(size_t n_tokens,\n"
       "    bool repeat = REPEAT_FALSE,\n"
       "    bool amx_available = AMX_AVAILABLE_TRUE,\n"
       "    bool record_rows = RECORD_ROWS_TRUE) {\n",
    2: "    page->set_k_row(slot, 0, token, k_source_row<head_size>(zero.data()));\n"
       "    // What save_k and the forward end do after a row store: record the row,\n"
       "    // and convert the block to the VNNI layout when it is complete (Note [K\n"
       "    // VNNI storage]). The dense AMX path runs only for a page whose 4 blocks\n"
       "    // are VNNI.\n"
       "    if (record_rows && page->note_k_row_saved(slot, token)) {\n"
       "      page->k_block_to_vnni(slot, token / k_vnni::BLOCK_TOKENS_16);\n"
       "    }\n"
       "    page->template set_v<geometry.kv>(\n"
       "        slot, 0, token, v_source_row<head_size>(zero.data()));\n",
    3: "  // converts nothing. With available() false nothing is packed either.\n"
       "  const bool packs = std::is_same_v<query_scalar, bf16> && amx_available;\n"
       "  // The dense predicate: the kernels run only for a full page whose blocks\n"
       "  // hold the VNNI layout (a VNNI slot with unrecorded rows keeps them row-major).\n"
       "  const bool dense = packs && n_tokens == book_t::page_size &&\n"
       "                     (record_rows || !k_vnni::layout_on<head_size>);\n"
       "  fake_amx_available = amx_available;\n",
    4: "  SECTION(\"host_bf16, full page with unrecorded rows: one pack, and under \"\n"
       "          \"TRON_K_VNNI no kernel call (the blocks are row-major)\") {\n"
       "    exercise_page<host_bf16>(\n"
       "        page_size, REPEAT_FALSE, AMX_AVAILABLE_TRUE, RECORD_ROWS_FALSE);\n"
       "  }\n"
       "  SECTION(\"host_bf16, full page, available() false: no pack, no kernel call, one \"\n"
       "          \"AVX visit that scored the whole page\") {\n"
       "    // The kill-switch arm of the attention path stats: the visit lands on the\n"
       "    // AVX path with the page's every token, and avx_full_page_visits counts it\n"
       "    // as AMX-eligible volume that did not take AMX.\n"
       "    exercise_page<host_bf16>(page_size, REPEAT_FALSE, AMX_AVAILABLE_FALSE);\n",
})
sub(P, "// exercise_page arguments: whether a second call is made, and whether the\n"
       "// stored rows are recorded like save_k records them.\n"
       "constexpr bool REPEAT_FALSE = false;\n"
       "constexpr bool RECORD_ROWS_TRUE = true;\n"
       "constexpr bool RECORD_ROWS_FALSE = false;\n",
       "// exercise_page arguments: whether a second call is made, what the fake\n"
       "// available() answers, and whether the stored rows are recorded like save_k\n"
       "// records them.\n"
       "constexpr bool REPEAT_FALSE = false;\n"
       "constexpr bool AMX_AVAILABLE_TRUE = true;\n"
       "constexpr bool AMX_AVAILABLE_FALSE = false;\n"
       "constexpr bool RECORD_ROWS_TRUE = true;\n"
       "constexpr bool RECORD_ROWS_FALSE = false;\n")

# ---------------------------------------------------------------------------
# 9. t/t_k_vnni_layout.cpp
# ---------------------------------------------------------------------------
P = "t/t_k_vnni_layout.cpp"
TAIL_TEST = r'''TEST_CASE("row-major tail block converts to the VNNI layout and back, bit for bit",
    "[kv_data][k_vnni]") {
  // Note [Row-major tail block] in h/tron/tensor/k_vnni.hpp: before its 16th
  // row is saved a block holds contiguous 256-byte rows (row_major_row) inside
  // its own 4 panels. block_to_vnni must produce the same bytes as store_row
  // per token, touch no other block, and block_to_rows must invert it.
  constexpr uint32_t SEED_23 = 23;
  constexpr size_t ROW_BYTES_256 = HEAD_SIZE_128 * sizeof(tron::bf16);
  constexpr size_t PANEL_BYTES_1024 = tron::k_vnni::PANEL_BYTES_1024;
  static_assert(ROW_BYTES_256 == 256, "the constant's name states its value");
  auto ref = std::make_unique<plane_and_rows>();
  auto blk = std::make_unique<plane_and_rows>();
  std::mt19937 gen(SEED_23);
  std::uniform_int_distribution<uint16_t> bits(0, BITS_MAX_0XFFFF);
  for (auto& x : ref->rows) {
    x = tron::bf16::from_bits(bits(gen));
  }
  SECTION("row_major_row rows are distinct, 64-byte aligned, and inside the block's "
          "panels") {
    // The owner is the plane (static_assert above): offsets are taken from it.
    const char* base = reinterpret_cast<const char*>(&blk->plane);
    const auto plane = std::as_const(blk->plane).as_view();
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      const size_t c = tok / BLOCK_TOKENS_16;
      const char* row =
          reinterpret_cast<const char*>(tron::row_major_row(plane, tok).data);
      const size_t off = static_cast<size_t>(row - base);
      CAPTURE(tok, off);
      REQUIRE(off % tron::k_vnni::LINE_BYTES_64 == 0);
      // Inside panel (s, c) for some dimension step s: those are the block's bytes.
      const size_t panel = off / PANEL_BYTES_1024;
      REQUIRE(panel % TOKEN_BLOCKS_4 == c);
      REQUIRE(off + ROW_BYTES_256 <= panel * PANEL_BYTES_1024 + PANEL_BYTES_1024);
      for (size_t other = 0; other < tok; ++other) {
        const char* orow =
            reinterpret_cast<const char*>(tron::row_major_row(plane, other).data);
        REQUIRE(static_cast<size_t>(std::abs(orow - row)) >= ROW_BYTES_256);
      }
    }
  }
  SECTION("block_to_vnni equals store_row per token and touches no other block") {
    for (size_t c = 0; c < TOKEN_BLOCKS_4; ++c) {
      poison_plane(ref->plane, POISON_0XA5A5);
      blk->plane = ref->plane;
      for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
        const size_t tok = c * BLOCK_TOKENS_16 + t;
        tron::store_row(ref->plane.as_view(), tok, row_of(*ref, tok));
        tron::store_row_major(blk->plane.as_view(), tok, row_of(*ref, tok));
      }
      tron::block_to_vnni(blk->plane.as_view(), c);
      CAPTURE(c);
      REQUIRE(std::memcmp(&blk->plane, &ref->plane, sizeof(ref->plane)) == 0);
      tron::block_to_rows(blk->plane.as_view(), c);
      const auto plane = std::as_const(blk->plane).as_view();
      for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
        const size_t tok = c * BLOCK_TOKENS_16 + t;
        CAPTURE(tok);
        REQUIRE(std::memcmp(tron::row_major_row(plane, tok).data,
                    ref->rows + tok * HEAD_SIZE_128, ROW_BYTES_256) == 0);
      }
      // The other blocks' bytes are still poison after both conversions.
      for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
        if (tok / BLOCK_TOKENS_16 == c) continue;
        alignas(tron::k_vnni::LINE_BYTES_64) tron::bf16 row[HEAD_SIZE_128];
        tron::load_row(plane, tok, tron::k_destination_row<HEAD_SIZE_128>(row));
        for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
          REQUIRE(row[d].to_bits() == POISON_0XA5A5);
        }
      }
    }
  }
}

'''


def layout_h2(ours, theirs):
    # 4737's tail-block test (typed port) followed by 4424's reader helper
    return TAIL_TEST + theirs


def layout_h3(ours, theirs):
    t = ours
    # typed accessors
    t = re.sub(r"set_k_row\((SLOT_[01]), 0, ([A-Za-z_0-9 +]+), row\.data\(\)\)",
               r"set_k_row(\1, 0, \2, tron::k_source_row<HEAD_SIZE_128>(row.data()))", t)
    t = re.sub(r"get_k_row\((SLOT_[01]), 0, ([A-Za-z_0-9 +]+), got\.data\(\)\)",
               r"get_k_row(\1, 0, \2, tron::k_destination_row<HEAD_SIZE_128>(got.data()))", t)
    assert "row.data())" not in t.replace("k_source_row<HEAD_SIZE_128>(row.data())", "") , "raw set_k_row left"
    assert "got.data())" not in t.replace("k_destination_row<HEAD_SIZE_128>(got.data())", ""), "raw get_k_row left"
    # the raw plane check after 21 saved rows
    t = re.sub(
        r"#ifdef TRON_K_VNNI\n  \{\n    // The raw plane: block 0 as scatter_row would write it, block 1's rows at row_ptr\.\n.*?\n#endif\n",
        "#ifdef TRON_K_VNNI\n"
        "  {\n"
        "    // The plane: block 0 holds the VNNI columns of rows 0..15 (the elements\n"
        "    // store_row wrote, read back through at()); block 1 holds rows 16..20\n"
        "    // row-major (row_major_row).\n"
        "    const auto plane = page->template k_packed<GEOMETRY_1X128>(SLOT_0, 0);\n"
        "    for (size_t tok = 0; tok < SAVED_TOKENS_21; ++tok) {\n"
        "      fill_row(row, tok, SALT_5);\n"
        "      CAPTURE(tok);\n"
        "      if (tok < BLOCK_TOKENS_16) {\n"
        "        for (size_t d = 0; d < HEAD_SIZE_128; ++d) {\n"
        "          REQUIRE(plane.at(tok, d).to_bits() == row[d].to_bits());\n"
        "        }\n"
        "      } else {\n"
        "        REQUIRE(std::memcmp(\n"
        "                    tron::row_major_row(plane, tok).data, row.data(), sizeof(row)) == 0);\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "#endif\n", t, count=1, flags=re.S)
    assert "scatter_row" not in t.split("TEST_CASE(\"the EAGLE")[0], "raw plane check left"
    # the snapshot of block 1 before the clear, and its check after
    t = sub_in(t,
        "#ifdef TRON_K_VNNI\n"
        "  auto snap = std::make_unique<plane_and_rows>();\n"
        "  std::memcpy(snap->plane, page->template k_vnni_plane<GEOMETRY_1X128>(SLOT_0, 0),\n"
        "      sizeof(snap->plane));\n"
        "#endif\n",
        "#ifdef TRON_K_VNNI\n"
        "  // Block 1's bytes: its 4 panels are exactly the elements at(tok, d) of the\n"
        "  // tokens 16..31 (Note [K VNNI storage]: token i owns column i % 16 of block\n"
        "  // i / 16 in every panel).\n"
        "  auto block_1_bytes = [&] {\n"
        "    std::array<uint16_t, BLOCK_TOKENS_16 * HEAD_SIZE_128> bytes{};\n"
        "    const auto plane = page->template k_packed<GEOMETRY_1X128>(SLOT_0, 0);\n"
        "    for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {\n"
        "      for (size_t d = 0; d < HEAD_SIZE_128; ++d) {\n"
        "        bytes[t * HEAD_SIZE_128 + d] = plane.at(BLOCK_TOKENS_16 + t, d).to_bits();\n"
        "      }\n"
        "    }\n"
        "    return bytes;\n"
        "  };\n"
        "  const auto snap = block_1_bytes();\n"
        "#endif\n")
    t = re.sub(
        r"#ifdef TRON_K_VNNI\n  \{\n    // Block 1's 4 panels \(s, 1\) are byte-identical to the snapshot\.\n.*?\n#endif\n",
        "#ifdef TRON_K_VNNI\n"
        "  // Block 1's 4 panels are byte-identical to the snapshot.\n"
        "  REQUIRE(block_1_bytes() == snap);\n"
        "#endif\n", t, count=1, flags=re.S)
    assert "k_vnni_plane" not in t and "row_ptr" not in t, "raw plane access left in the state tests"
    # the chunk-size guard tail that 4424 removed
    t = re.sub(r"\n#else  // TRON_CHUNK_SIZE != 16\n.*?\n#endif\n$", "\n", t, count=1, flags=re.S)
    assert "TRON_CHUNK_SIZE" not in t, "chunk guard left"
    return t


resolve(P, {
    1: "// (Note [K VNNI storage] in kv_cache.hpp) through its typed owner and views\n"
       "// (h/tron/tensor/k_vnni.hpp). The index map matches hand-computed anchors. The\n"
       "// per-token store / load operations are exact. The in-place conversion of a\n"
       "// 16-token block between its row-major and its VNNI form (Note [Row-major tail\n"
       "// block] in h/tron/tensor/k_vnni.hpp) is exact. The AVX-512 (the\n",
    2: layout_h2,
    3: layout_h3,
})
sub(P, "#include <cstdint>\n#include <cstring>\n", "#include <cstdint>\n#include <cstdlib>\n#include <cstring>\n")

# ---------------------------------------------------------------------------
# 10. t/t_llama_unit.cpp
# ---------------------------------------------------------------------------
P = "t/t_llama_unit.cpp"
resolve(P, {
    1: "    check_blocks(/*converted=*/false);\n"
       "    state.convert_pending_k_blocks();\n"
       "    check_blocks(/*converted=*/true);\n"
       "    check(before);\n"
       "    if constexpr (k_vnni::layout_on<head_size>) {\n",
})
# the raw-plane setup of "apply and join page ranges": typed, same K instance as the row-major build
sub(P, "  // Give the VNNI build the K instance of the row-major build: the raw bytes\n"
       "  // fill_random wrote, read as consecutive 128-value rows (row i at element\n"
       "  // i * 128 of the plane), stored through set_k_row. Then record the rows of\n",
       "  // Give the VNNI build the K instance of the row-major build: the raw bytes\n"
       "  // fill_random wrote, read as consecutive 128-value rows (row i at element\n"
       "  // i * 128 of the plane; the packed view reaches element e through the\n"
       "  // inverse of the index map of Note [K VNNI storage]), stored through\n"
       "  // set_k_row. Then record the rows of\n")
sub(P, "    constexpr size_t PAGE_1_RECORDED_ROWS_41 = 41;\n"
       "    static_assert(\n"
       "        PAGE_1_RECORDED_ROWS_41 == 41, \"the constant's name states its value\");\n",
       "    constexpr size_t page_1_recorded_rows = 41;\n"
       "    // Element e of the plane as (token, dim) of the packed view.\n"
       "    auto element = [](auto const& plane, size_t e) {\n"
       "      using namespace k_vnni;\n"
       "      const size_t j = e % PAIR_2;\n"
       "      const size_t t = (e / PAIR_2) % BLOCK_TOKENS_16;\n"
       "      const size_t dp = (e / (PAIR_2 * BLOCK_TOKENS_16)) % STEP_PAIRS_16;\n"
       "      const size_t c = (e / PANEL_ELEMS_512) % TOKEN_BLOCKS_4;\n"
       "      const size_t s = e / (PANEL_ELEMS_512 * TOKEN_BLOCKS_4);\n"
       "      return plane.at(c * BLOCK_TOKENS_16 + t, s * STEP_DIMS_32 + PAIR_2 * dp + j);\n"
       "    };\n")
sub(P, "        const bf16* plane = page->template k_vnni_plane<geometry.kv>(slot_0, kv_head);\n"
       "        for (size_t tok = 0; tok < page_t::page_size; ++tok) {\n"
       "          std::memcpy(\n"
       "              (*rows)[tok].data(), plane + tok * head_size, head_size * sizeof(bf16));\n"
       "        }\n"
       "        for (size_t tok = 0; tok < page_t::page_size; ++tok) {\n"
       "          page->set_k_row(slot_0, kv_head, tok, (*rows)[tok].data());\n"
       "        }\n",
       "        const auto plane = page->template k_packed<geometry.kv>(slot_0, kv_head);\n"
       "        for (size_t tok = 0; tok < page_t::page_size; ++tok) {\n"
       "          for (size_t d = 0; d < head_size; ++d) {\n"
       "            (*rows)[tok][d] = element(plane, tok * head_size + d);\n"
       "          }\n"
       "        }\n"
       "        for (size_t tok = 0; tok < page_t::page_size; ++tok) {\n"
       "          page->set_k_row(\n"
       "              slot_0, kv_head, tok, k_source_row<head_size>((*rows)[tok].data()));\n"
       "        }\n")
sub(P, "      const size_t recorded = pg == 0 ? page_t::page_size : PAGE_1_RECORDED_ROWS_41;\n",
       "      const size_t recorded = pg == 0 ? page_t::page_size : page_1_recorded_rows;\n")
# local spelling for 4737's constants in this shared test file
sub(P, "  constexpr size_t PRE_SAVED_ROWS_5 = 5;\n"
       "  // check_blocks argument: whether the forward end converted the queued block.\n"
       "  constexpr bool CONVERTED_FALSE = false;\n"
       "  constexpr bool CONVERTED_TRUE = true;\n",
       "  constexpr size_t pre_saved_rows = 5;\n")
sub(P, "      if (tok >= PRE_SAVED_ROWS_5 && tok != NO_KV_TOKEN_8) continue;\n",
       "      if (tok >= pre_saved_rows && tok != no_kv_token) continue;\n")
sub(P, "    constexpr uint8_t BLOCKS_0_AND_3_0X9 = 0x9;\n"
       "    constexpr uint8_t BLOCK_3_ONLY_0X8 = 0x8;\n"
       "    constexpr uint8_t NO_BLOCK_0X0 = 0x0;\n"
       "    constexpr size_t PAGE_1 = 1;  // the pages the pass does not complete a block of\n"
       "    constexpr size_t PAGE_2 = 2;\n"
       "    const uint8_t page0 = converted ? BLOCKS_0_AND_3_0X9 : BLOCK_3_ONLY_0X8;\n"
       "    REQUIRE(pages[0]->template k_vnni_blocks<geometry.kv>(slot) == page0);\n"
       "    REQUIRE(pages[PAGE_1]->template k_vnni_blocks<geometry.kv>(slot) == NO_BLOCK_0X0);\n"
       "    REQUIRE(pages[PAGE_2]->template k_vnni_blocks<geometry.kv>(slot) == NO_BLOCK_0X0);\n",
       "    constexpr uint8_t blocks_0_and_3 = 0x9;\n"
       "    constexpr uint8_t block_3_only = 0x8;\n"
       "    constexpr uint8_t no_block = 0x0;\n"
       "    const uint8_t page0 = converted ? blocks_0_and_3 : block_3_only;\n"
       "    REQUIRE(pages[0]->template k_vnni_blocks<geometry.kv>(slot) == page0);\n"
       "    // The pages the pass does not complete a block of.\n"
       "    REQUIRE(pages[1]->template k_vnni_blocks<geometry.kv>(slot) == no_block);\n"
       "    REQUIRE(pages[2]->template k_vnni_blocks<geometry.kv>(slot) == no_block);\n")
s = read(P)
n1 = s.count("check_blocks(CONVERTED_FALSE);"); n2 = s.count("check_blocks(CONVERTED_TRUE);")
assert (n1, n2) == (4, 2), (n1, n2)
s = s.replace("check_blocks(CONVERTED_FALSE);", "check_blocks(/*converted=*/false);")
s = s.replace("check_blocks(CONVERTED_TRUE);", "check_blocks(/*converted=*/true);")
assert s.count("OPERATION_USES_HW_1") == 3, s.count("OPERATION_USES_HW_1")
s = s.replace("  constexpr uint8_t OPERATION_USES_HW_1 = 1;\n", "  constexpr uint8_t operation_uses_hw = 1;\n")
s = s.replace("OPERATION_USES_HW_1", "operation_uses_hw")
assert s.count("OTHER_OPERATION_1") == 2
s = s.replace("    constexpr size_t OTHER_OPERATION_1 = 1;\n", "    constexpr size_t other_operation = 1;\n")
s = s.replace("OTHER_OPERATION_1", "other_operation")
write(P, s)

# ---------------------------------------------------------------------------
# final sanity: no conflict markers, no raw helpers, no dropped names
# ---------------------------------------------------------------------------
bad = []
for p in ["h/tron/tensor/k_vnni.hpp", "h/tron/kernels/k_vnni.hpp", "h/tron/models/kv_cache.hpp",
          "h/tron/models/model.hpp", "h/tron/models/self_attention.hpp", "h/tron/scheduler/full.hpp",
          "h/tron/kernels/amx_attn_iface.hpp", "t/t_amx_dispatch_dtype.cpp", "t/t_k_vnni_layout.cpp",
          "t/t_llama_unit.cpp"]:
    s = read(p)
    for pat in ["<<<<<<<", ">>>>>>>", "k_vnni::row_ptr", "k_vnni::block_to_vnni", "k_vnni::block_to_rows",
                "k_vnni::scatter_row", "k_vnni::gather_row", "k_vnni::store_block", "k_vnni_plane",
                "ROW_ALIGNED_TRUE", "ROW_DMA_FALSE", "K_STORE_BLOCK_16", "k_scatter_run_len",
                "Row-major tail block] in k_vnni.hpp", "save_k_helper"]:
        if pat in s:
            bad.append((p, pat, s.count(pat)))
print("leftovers:", bad)
sys.exit(1 if bad else 0)
