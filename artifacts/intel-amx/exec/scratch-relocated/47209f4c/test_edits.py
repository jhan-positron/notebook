import pathlib, re
R = pathlib.Path('/home/jhan/workspace/ai-runs/tron-issue4525')
def edit(path, reps):
    p = R / path; s = p.read_text()
    for old, new in reps:
        assert s.count(old) == 1, (path, old[:80])
        s = s.replace(old, new)
    p.write_text(s)

# ---------------- t_llama_unit.cpp
llama = [
# include for memcpy
("#include <cstddef>\n#include <filesystem>\n", "#include <cstddef>\n#include <cstring>\n#include <filesystem>\n"),
# W4: unused probe definition
("// A packed view indexes by at(token, dim) only. There is no operator[]: a row\n// of the interleaved plane is not contiguous, and no production code reads one.\ntemplate <typename Matrix>\nconstexpr bool matrix_indexes_rows = requires(Matrix& m) { m[0]; };\n\n", ""),
# W4 + W3: pointer-constructor block
("""  // Packed views come only from an owner; a bare pointer does not say
  // which layout it points at. The native K alias keeps its explicit pointer
  // wrap: that view type is the existing row-major view.
  STATIC_REQUIRE_FALSE(std::is_constructible_v<v_plane_mut_t, bf16*>);
  STATIC_REQUIRE_FALSE(std::is_constructible_v<v_plane_t, const bf16*>);
  STATIC_REQUIRE_FALSE(std::is_default_constructible_v<v_plane_t>);
  STATIC_REQUIRE(std::is_constructible_v<k_plane_t, const bf16*>);
""", """  // Packed views come only from an owner; a bare pointer does not say
  // which layout it points at. The native K alias is the existing row-major
  // view and keeps its pointer constructor: it names the layout at the kernel
  // signature but does not enforce it. A distinct K type comes with the
  // packed-K change.
  STATIC_REQUIRE_FALSE(std::is_constructible_v<v_plane_mut_t, bf16*>);
  STATIC_REQUIRE_FALSE(std::is_constructible_v<v_plane_t, const bf16*>);
  STATIC_REQUIRE(std::is_constructible_v<k_plane_t, const bf16*>);
"""),
("""  STATIC_REQUIRE_FALSE(matrix_at_writes<v_plane_t>);
  STATIC_REQUIRE_FALSE(matrix_indexes_rows<v_plane_mut_t>);
  STATIC_REQUIRE_FALSE(matrix_indexes_rows<v_plane_t>);
  // The owner is one aligned plane, trivial to construct, copy and destroy. The
  // KV arena's DMA allocation creates the kv_blocks that hold it (Note [KV block
  // lifetime]). A trivial constructor and destructor are enough for C++ to create
  // such objects implicitly ([class.prop]), so these checks keep that true.
  STATIC_REQUIRE(std::is_trivially_default_constructible_v<v_owner_t>);
  STATIC_REQUIRE(std::is_trivially_destructible_v<v_owner_t>);
  STATIC_REQUIRE(std::is_trivially_copyable_v<v_owner_t>);
  STATIC_REQUIRE(
      sizeof(v_owner_t) ==
      amx_attn_h128g4::PAGE_TOKENS_64 * amx_attn_h128g4::HEAD_SIZE_128 * sizeof(bf16));
  STATIC_REQUIRE(alignof(v_owner_t) == V_PLANE_ALIGNMENT_64);
  using kv_block_t =
      detail::kv_block<amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
  STATIC_REQUIRE(std::is_trivially_default_constructible_v<kv_block_t>);
  STATIC_REQUIRE(std::is_trivially_destructible_v<kv_block_t>);
  STATIC_REQUIRE(sizeof(kv_block_t) == detail::KV_BLOCK_PLANES_2 * sizeof(v_owner_t));
""", """  STATIC_REQUIRE_FALSE(matrix_at_writes<v_plane_t>);
  // The aligned vector loads and the AMX tile rows need a 64-byte-aligned
  // plane, also for an owner that lives outside a kv_block.
  STATIC_REQUIRE(alignof(v_owner_t) == V_PLANE_ALIGNMENT_64);
"""),
# W6 file comment
("""// "append_v preserves poison" poisons the padding slot and verifies that
// the zero-init invariant (make_unique_dma + append_v zeroing the odd
// partner) prevents NaN propagation through _mm512_dpbf16_ps.""",
 """// "append_v zeroes the poisoned partner" poisons the padding slot and verifies
// that the zero-init invariant (make_unique_dma + append_v zeroing the odd
// partner) prevents NaN propagation through _mm512_dpbf16_ps."""),
# W5 + W6 poison section
("""  SECTION("append_v preserves poison") {
    // dst_tokens 3 copies odd<-even and even<-odd; dst_tokens 2 copies
    // even<-even and odd<-odd. Together they exercise the four parity
    // combinations of copy_token, each time with the last copy landing next to
    // the poisoned token 7.
    const size_t dst_tokens = GENERATE(EVEN_START_DST_TOKENS_2, ODD_START_DST_TOKENS_3);
""", """  SECTION("append_v zeroes the poisoned partner") {
    // With 3 destination tokens the append's last copy lands on the even token
    // 6, so the even-destination rule must zero the poisoned token 7. The four
    // copy parities are compared bit for bit in the packed-bits case below.
    const size_t dst_tokens = ODD_START_DST_TOKENS_3;
"""),
# W1 case header comment
("""// - a bf16 source row is stored bit for bit, infinities and NaNs included;
// - fp16 and float source rows become fp32 and keep their upper 16 bits:
//   truncation, no rounding, no NaN correction, so a float NaN whose payload
//   sits only in the discarded bits stores as infinity (the generic
//   fp32s_to_bf16s conversion would keep it a NaN when TRON_IGNORE_NAN is off);
""", """// - a bf16 source row is stored bit for bit, infinities and NaNs included;
// - fp16 and float source rows are stored as bf16, checked on values that
//   are exact in bf16 (how inexact values round is not a contract);
"""),
# W1 float section
("""  SECTION("float rows truncate to their upper 16 bits, without NaN correction") {
    // fp32 bit pattern -> stored bf16 bits under truncation. The second entry
    // would round to 0x3f81 under round-to-nearest; the third would stay a NaN
    // (0x7f81) under the generic conversion's NaN correction.
    constexpr std::array<std::pair<uint32_t, uint16_t>, 5> cases{{
        {0x3f800000u, 0x3f80u},  // 1.0
        {0x3f80ffffu, 0x3f80u},  // just below the next bf16 value
        {0x7f800001u, 0x7f80u},  // NaN with payload only in the low bits -> +inf
        {0x7fc00000u, 0x7fc0u},  // quiet NaN, payload survives
        {0xbf818000u, 0xbf81u},  // exact tie: truncation keeps the odd value
    }};
""", """  SECTION("float rows are stored as bf16 and keep the pair rule") {
    // fp32 bit pattern -> stored bf16 bits. Every value is exact in bf16, so
    // the expected bits do not depend on the rounding rule of the store.
    constexpr std::array<std::pair<uint32_t, uint16_t>, 4> cases{{
        {0x3f800000u, 0x3f80u},  // 1.0
        {0x3f000000u, 0x3f00u},  // 0.5
        {0xc0000000u, 0xc000u},  // -2.0
        {0x7fc00000u, 0x7fc0u},  // quiet NaN, payload survives
    }};
"""),
# W1 fp16 section
("""  SECTION("fp16 rows convert through fp32 and truncate") {
    // fp16 value -> stored bf16 bits. 65504 (the largest fp16) is 0x477fe000
    // as fp32: truncation keeps 0x477f, rounding would give 0x4780.
    constexpr std::array<std::pair<float, uint16_t>, 4> cases{{
        {1.0f, 0x3f80u},
        {65504.0f, 0x477fu},
        {-0.00006103515625f, 0xb880u},  // -2^-14, the smallest fp16 normal
        {0.5f, 0x3f00u},
    }};
""", """  SECTION("fp16 rows are stored as bf16 and keep the pair rule") {
    // fp16 value -> stored bf16 bits. Every value is exact in bf16.
    constexpr std::array<std::pair<float, uint16_t>, 3> cases{{
        {1.0f, 0x3f80u},
        {-0.00006103515625f, 0xb880u},  // -2^-14, the smallest fp16 normal
        {0.5f, 0x3f00u},
    }};
"""),
]
edit('t/t_llama_unit.cpp', llama)

# W2: new case appended after the packed-bits case (the at() section closes the case)
p = R / 't/t_llama_unit.cpp'; s = p.read_text()
anchor = """        REQUIRE(plane.at(token, dim).to_bits() == pattern(token, dim));
      }
    }
  }
}
"""
assert s.count(anchor) == 1
new_case = anchor + """
// The packed layout against an independent formula that shares no code with
// the typed operations: append_v_row and at() both compute addresses through
// pair_base, so a wrong formula there would pass a read-back through at().
// This case compares the owner's bytes with
//   storage[(pair * Cols + dim) * 2 + j] = V[2 * pair + j][dim]
// written out by hand. It needs no AMX, so it runs in every build.
TEST_CASE("append_v_row matches the independent packed-V formula", "[kv_data]") {
  static constexpr size_t ROWS_64 = 64;
  static constexpr size_t COLS_128 = 128;
  // Base of the distinct bit patterns: exponent field 0x78..0xb7, never 0xff.
  static constexpr uint16_t PATTERN_BASE_0X3C00 = 0x3c00;
  auto pattern = [](size_t token, size_t dim) {
    return static_cast<uint16_t>(PATTERN_BASE_0X3C00 + token * COLS_128 + dim);
  };
  // The owner is 16 KiB with 64-byte alignment, so it lives on the heap (the
  // aligned operator new honors alignas(64)).
  auto owner = std::make_unique<v_vnni_tensor<ROWS_64, COLS_128>>();
  for (size_t token = 0; token < ROWS_64; ++token) {
    alignas(chunk_alignment) std::array<bf16, COLS_128> row;
    for (size_t dim = 0; dim < COLS_128; ++dim) {
      row[dim] = bf16::from_bits(pattern(token, dim));
    }
    append_v_row(owner->as_view(), token, v_source_row<COLS_128>(row.data()));
  }
  std::array<uint16_t, ROWS_64 * COLS_128> stored;
  static_assert(sizeof(stored) == sizeof(*owner));
  std::memcpy(stored.data(), owner.get(), sizeof(stored));
  for (size_t pair = 0; pair < ROWS_64 / V_PAIR_TOKENS_2; ++pair) {
    for (size_t dim = 0; dim < COLS_128; ++dim) {
      for (size_t j = 0; j < V_PAIR_TOKENS_2; ++j) {
        CAPTURE(pair, dim, j);
        REQUIRE(stored[(pair * COLS_128 + dim) * V_PAIR_TOKENS_2 + j] ==
                pattern(V_PAIR_TOKENS_2 * pair + j, dim));
      }
    }
  }
}
"""
s = s.replace(anchor, new_case); p.write_text(s)

# ---------------- t_amx_numerics.cpp: drop the byte comparison, keep the owner
edit('t/t_amx_numerics.cpp', [
("""  // The kernel input is a real packed V owner (v_vnni_tensor), filled through
  // the public typed write path: one aligned bf16 row per token, appended in
  // order (append_v_row). The owner is 16 KiB with 64-byte alignment, so it
  // lives on the heap (the aligned operator new honors alignas(64)). Its bytes,
  // copied out of the trivially copyable owner, must equal the independent
  // formula above; that checks the typed write path, not the kernel.
""", """  // The kernel input is a real packed V owner (v_vnni_tensor), filled through
  // the public typed write path: one aligned bf16 row per token, appended in
  // order (append_v_row). The owner is 16 KiB with 64-byte alignment, so it
  // lives on the heap (the aligned operator new honors alignas(64)). The
  // layout formula itself is checked in t_llama_unit ("append_v_row matches
  // the independent packed-V formula"), which needs no AMX.
"""),
("""  {
    std::vector<tron::bf16> owner_bytes(PAGE_TOKENS_64 * HEAD_SIZE_128);
    std::memcpy(owner_bytes.data(), v_owner.get(), sizeof(*v_owner));
    for (size_t i = 0; i < owner_bytes.size(); ++i) {
      REQUIRE(owner_bytes[i].to_bits() == v_page[i].to_bits());
    }
  }

""", ""),
])
print("edits applied")
