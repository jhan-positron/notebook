#!/usr/bin/env python3
"""Second half of the resolution (resolve.py applied steps 1-8): the raw helper block
4737 added to the kernel header outside the conflict hunks, the two test files, and
the final leftover check."""
import re
import sys

sys.argv = ["resolve2"]
exec(open(__file__.replace("resolve2.py", "resolve.py")).read().split(
    "# ---------------------------------------------------------------------------\n# 1. h/tron/tensor/k_vnni.hpp")[0])
# (the helpers read/write/conflicts/resolve/sub/sub_in come from resolve.py's header)

# ---------------------------------------------------------------------------
# 2b. h/tron/kernels/k_vnni.hpp: drop the auto-merged raw block (Note + row_ptr +
#     block_to_vnni + block_to_rows) that now lives typed in h/tron/tensor/k_vnni.hpp
# ---------------------------------------------------------------------------
P = "h/tron/kernels/k_vnni.hpp"
s = read(P)
a = s.find("// Note [Row-major tail block]\n")
b = s.find("// Scores of one query group against the live tokens of one page, read from\n")
assert 0 < a < b, (a, b)
s = s[:a] + s[b:]
assert "row_ptr" not in s and "block_to_vnni" not in s and "<cstring>" in s
# <cstring> came with 4737's memcpy helpers; the reader does not need it
s = s.replace("#include <cstdint>\n#include <cstring>\n#include <immintrin.h>\n",
              "#include <cstdint>\n#include <immintrin.h>\n")
write(P, s)

# ---------------------------------------------------------------------------
# 9. t/t_k_vnni_layout.cpp
# ---------------------------------------------------------------------------
P = "t/t_k_vnni_layout.cpp"
TAIL_TEST = open(__file__.replace("resolve2.py", "tail_test.cpp")).read()


def layout_h2(ours, theirs):
    return TAIL_TEST + theirs


def layout_h3(ours, theirs):
    t = ours
    # the raw plane check after 21 saved rows (replace before the typed-accessor pass:
    # it carries a scatter_row(..., row.data()) call of its own)
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
    assert "scatter_row" not in t, "raw plane check left"
    # typed accessors
    t = re.sub(r"set_k_row\((SLOT_[01]), 0, ([A-Za-z_0-9 +]+), row\.data\(\)\)",
               r"set_k_row(\1, 0, \2, tron::k_source_row<HEAD_SIZE_128>(row.data()))", t)
    t = re.sub(r"get_k_row\((SLOT_[01]), 0, ([A-Za-z_0-9 +]+), got\.data\(\)\)",
               r"get_k_row(\1, 0, \2, tron::k_destination_row<HEAD_SIZE_128>(got.data()))", t)
    assert "row.data())" not in t.replace("k_source_row<HEAD_SIZE_128>(row.data())", "").replace("row.data(), sizeof(row)) == 0", ""), "raw set_k_row left"
    assert "got.data())" not in t.replace("k_destination_row<HEAD_SIZE_128>(got.data())", ""), "raw get_k_row left"
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
                "Row-major tail block] in k_vnni.hpp", "save_k_helper", "NO_KV_TOKEN_8", "CONVERTED_"]:
        if pat in s:
            bad.append((p, pat, s.count(pat)))
print("leftovers:", bad)
sys.exit(1 if bad else 0)
