// This file tests the VNNI (Vector Neural Network Instructions) K storage layout
// (Note [K VNNI storage] in kv_cache.hpp) through its typed owner and views
// (h/tron/tensor/k_vnni.hpp). The index map matches hand-computed anchors. The
// per-token store / load operations are exact. The in-place conversion of a
// 16-token block between its row-major and its VNNI form (Note [Row-major tail
// block] in h/tron/tensor/k_vnni.hpp) is exact. The AVX-512 (the
// 512-bit Advanced Vector Extensions) reader of that layout does not differ
// from the row-major dotter. The layout-agnostic page accessors and page copies
// move tokens correctly, and the page's per-block layout state follows the
// saved rows.
// No AMX (Advanced Matrix Extensions, the tile instruction set) instruction runs
// here. So every case runs on every host. The cases that need a VNNI slot (the
// book-level ones under TRON_K_VNNI) exercise the row-major layout in the other
// build. There they check the same contract.
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <memory>
#include <random>
#include <utility>
#include <vector>

#include <catch2/catch_test_macros.hpp>

#include "common/numerics/bf16.hpp"
#include "common/numerics/fp16.hpp"
#include "tron/kernels/dotter.hpp"
#include "tron/kernels/k_vnni.hpp"  // qk_group
#include "tron/models/kv_cache.hpp"
#include "tron/tensor/k_vnni.hpp"

namespace {

using tron::k_vnni::BF16_BITS_16;
using tron::k_vnni::BLOCK_TOKENS_16;
using tron::k_vnni::FULL_BLOCK_0XFFFF;
using tron::k_vnni::HEAD_SIZE_128;
using tron::k_vnni::LINE_BYTES_64;
using tron::k_vnni::PAGE_TOKENS_64;
using tron::k_vnni::TOKEN_BLOCKS_4;

// The bytes of one fp32 (the 32-bit IEEE single format). The bf16 (the 16-bit
// brain floating-point format) helpers move bit patterns through memcpy.
constexpr size_t F32_BYTES_4 = 4;
// Round-to-nearest-even (the nearest bf16 is chosen, a tie goes to the even one)
// bias added before the fp32 -> bf16 truncation.
constexpr uint32_t RNE_BIAS_0X7FFF = 0x7fffu;
// The largest bf16 bit pattern: the random-bits distributions cover all of them.
constexpr uint16_t BITS_MAX_0XFFFF = 0xffff;
// Poison for the plane slots no store may touch.
constexpr uint16_t POISON_0XA5A5 = 0xa5a5;

uint16_t bf16_rne(float f) {
  uint32_t bits;
  std::memcpy(&bits, &f, F32_BYTES_4);
  bits += RNE_BIAS_0X7FFF + ((bits >> BF16_BITS_16) & 1u);
  return static_cast<uint16_t>(bits >> BF16_BITS_16);
}

float bf16_to_float(uint16_t b) {
  uint32_t bits = static_cast<uint32_t>(b) << BF16_BITS_16;
  float f;
  std::memcpy(&f, &bits, F32_BYTES_4);
  return f;
}

using k_plane_t = tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>;
// The plane's bytes copied out for the physical-layout checks. The owner is
// trivially copyable, so a memcpy of the owner is the plane's bytes.
using plane_bytes_t = std::array<tron::bf16, PAGE_TOKENS_64 * HEAD_SIZE_128>;
static_assert(sizeof(k_plane_t) == sizeof(plane_bytes_t),
    "the owner holds the plane and nothing else");

struct alignas(64) plane_and_rows {
  k_plane_t plane;  // the packed K plane, written through the typed operations
  tron::bf16 rows[PAGE_TOKENS_64 * HEAD_SIZE_128];  // the same K, one row per token
};

// One token's native row of `rows`, as the read-only typed source row.
tron::const_k_row_view<HEAD_SIZE_128> row_of(const plane_and_rows& buf, size_t tok) {
  return tron::k_source_row<HEAD_SIZE_128>(buf.rows + tok * HEAD_SIZE_128);
}

// Every token's slots filled with one poison pattern, through 64 typed row
// stores (the owner has no raw access).
void poison_plane(k_plane_t& plane, uint16_t pattern) {
  alignas(64) tron::bf16 poison_row[HEAD_SIZE_128];
  for (auto& x : poison_row) {
    x = tron::bf16::from_bits(pattern);
  }
  for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
    tron::store_row(
        plane.as_view(), tok, tron::k_source_row<HEAD_SIZE_128>(poison_row));
  }
}

plane_bytes_t bytes_of(const k_plane_t& plane) {
  plane_bytes_t bytes;
  std::memcpy(bytes.data(), &plane, sizeof(plane));
  return bytes;
}

}  // namespace

TEST_CASE("VNNI K index map matches hand-computed anchors", "[kv_data][k_vnni]") {
  // Positions derived by hand from the layout definition (Note [K VNNI
  // storage]). One panel = 512 elements = 1024 bytes (16 dimension-pair rows x 16
  // tokens x 2). One dimension step = 4 panels. One dimension-pair row = 32
  // elements. One token = 2 elements inside a row. The (17, 34) anchor is the
  // worked example of the 2026-09-04 single-K feasibility study (bf16 offset 2594).
  using tron::k_vnni::index;
  STATIC_REQUIRE(index(0, 0) == 0);
  STATIC_REQUIRE(index(0, 1) == 1);      // second value of the pair
  STATIC_REQUIRE(index(1, 0) == 2);      // next token: next 32-bit lane
  STATIC_REQUIRE(index(15, 0) == 30);    // last token of block 0
  STATIC_REQUIRE(index(16, 0) == 512);   // token block 1: next panel
  STATIC_REQUIRE(index(0, 2) == 32);     // dimension pair 1: next 64-byte row
  STATIC_REQUIRE(index(0, 31) == 481);   // last pair of step 0, second value
  STATIC_REQUIRE(index(0, 32) == 2048);  // dimension step 1: 4 panels later
  STATIC_REQUIRE(index(17, 34) == 2594);
  STATIC_REQUIRE(index(63, 127) == 8191);  // the last element of the plane
}

TEST_CASE(
    "VNNI K store and load are exact and token-independent", "[kv_data][k_vnni]") {
  constexpr uint32_t SEED_7 = 7;
  // The scrambled store order: token (i * 37 + 11) mod 64 for i = 0..63.
  constexpr size_t SCRAMBLE_STRIDE_37 = 37;
  constexpr size_t SCRAMBLE_OFFSET_11 = 11;
  auto buf = std::make_unique<plane_and_rows>();
  std::mt19937 gen(SEED_7);
  std::uniform_int_distribution<uint16_t> bits(0, BITS_MAX_0XFFFF);
  for (auto& x : buf->rows) {
    x = tron::bf16::from_bits(bits(gen));
  }
  // Poison: a wrong index would leave poison where a value belongs, or put
  // a value where poison belongs.
  poison_plane(buf->plane, POISON_0XA5A5);
  // Store every token in a scrambled order (tokens own disjoint slots).
  for (size_t i = 0; i < PAGE_TOKENS_64; ++i) {
    const size_t tok = (i * SCRAMBLE_STRIDE_37 + SCRAMBLE_OFFSET_11) % PAGE_TOKENS_64;
    tron::store_row(buf->plane.as_view(), tok, row_of(*buf, tok));
  }
  SECTION("the plane holds every value at the documented position") {
    const plane_bytes_t bytes = bytes_of(buf->plane);
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
        // store_row addresses the plane through its own pair-row offsets, not
        // through index(). Agreement here ties the store to the index map.
        const size_t at = tron::k_vnni::index(tok, d);
        REQUIRE(bytes[at].to_bits() == buf->rows[tok * HEAD_SIZE_128 + d].to_bits());
      }
    }
  }
  SECTION("at() reads the plane by (token, dim)") {
    auto const plane = std::as_const(buf->plane).as_view();
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
        REQUIRE(
            plane.at(tok, d).to_bits() == buf->rows[tok * HEAD_SIZE_128 + d].to_bits());
      }
    }
  }
  SECTION("load_row inverts store_row for every token") {
    alignas(64) tron::bf16 row[HEAD_SIZE_128];
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      tron::load_row(std::as_const(buf->plane).as_view(), tok,
          tron::k_destination_row<HEAD_SIZE_128>(row));
      REQUIRE(std::memcmp(row, buf->rows + tok * HEAD_SIZE_128, sizeof(row)) == 0);
    }
  }
  SECTION("rewriting one token changes no other token's slots") {
    constexpr size_t REWRITTEN_TOKEN_29 = 29;
    for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
      buf->rows[REWRITTEN_TOKEN_29 * HEAD_SIZE_128 + d] =
          tron::bf16::from_bits(bits(gen));
    }
    tron::store_row(
        buf->plane.as_view(), REWRITTEN_TOKEN_29, row_of(*buf, REWRITTEN_TOKEN_29));
    const plane_bytes_t bytes = bytes_of(buf->plane);
    for (size_t t = 0; t < PAGE_TOKENS_64; ++t) {
      for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
        REQUIRE(bytes[tron::k_vnni::index(t, d)].to_bits() ==
                buf->rows[t * HEAD_SIZE_128 + d].to_bits());
      }
    }
  }
  SECTION("copy_token moves one token between planes, other tokens untouched") {
    constexpr size_t SOURCE_TOKEN_5 = 5;
    constexpr size_t DESTINATION_TOKEN_42 = 42;
    auto other = std::make_unique<plane_and_rows>();
    poison_plane(other->plane, POISON_0XA5A5);
    tron::copy_token(other->plane.as_view(), DESTINATION_TOKEN_42,
        std::as_const(buf->plane).as_view(), SOURCE_TOKEN_5);
    const plane_bytes_t bytes = bytes_of(other->plane);
    for (size_t t = 0; t < PAGE_TOKENS_64; ++t) {
      for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
        const uint16_t expected =
            t == DESTINATION_TOKEN_42
                ? buf->rows[SOURCE_TOKEN_5 * HEAD_SIZE_128 + d].to_bits()
                : POISON_0XA5A5;
        REQUIRE(bytes[tron::k_vnni::index(t, d)].to_bits() == expected);
      }
    }
  }
}

TEST_CASE("VNNI K block save equals the per-token row store, bit for bit",
    "[kv_data][k_vnni]") {
  // store_block (16 tokens transposed in registers, whole-line stores) is
  // the prefill store of save_k (Note [Shared block save] in model.hpp). It
  // must leave the plane exactly as store_row per present token does. It
  // must not touch the slots of absent tokens (poison stays poison). The
  // masks cover: full block, single tokens, halves, alternating lanes, the
  // empty block, and random subsets.
  constexpr uint32_t SEED_19 = 19;
  constexpr unsigned TOKEN_0_0X0001 = 0x0001;
  constexpr unsigned TOKEN_15_0X8000 = 0x8000;
  constexpr unsigned LOW_HALF_0X00FF = 0x00ff;
  constexpr unsigned HIGH_HALF_0XFF00 = 0xff00;
  constexpr unsigned EVEN_TOKENS_0X5555 = 0x5555;
  constexpr unsigned ODD_TOKENS_0XAAAA = 0xaaaa;
  constexpr unsigned EMPTY_BLOCK_0X0000 = 0x0000;
  constexpr unsigned MIXED_0X1234 = 0x1234;
  constexpr unsigned ALL_BUT_TOKEN_0_0XFFFE = 0xfffe;
  constexpr unsigned ALL_BUT_TOKEN_15_0X7FFF = 0x7fff;
  constexpr unsigned NIBBLES_0X0F0F = 0x0f0f;
  constexpr unsigned TOKEN_1_0X0002 = 0x0002;
  constexpr unsigned TOKEN_14_0X4000 = 0x4000;
  constexpr int N_RANDOM_MASKS_24 = 24;
  auto ref = std::make_unique<plane_and_rows>();
  auto blk = std::make_unique<plane_and_rows>();
  std::mt19937 gen(SEED_19);
  std::uniform_int_distribution<uint16_t> bits(0, BITS_MAX_0XFFFF);
  for (auto& x : ref->rows) {
    x = tron::bf16::from_bits(bits(gen));
  }
  std::vector<unsigned> masks = {FULL_BLOCK_0XFFFF, TOKEN_0_0X0001, TOKEN_15_0X8000,
      LOW_HALF_0X00FF, HIGH_HALF_0XFF00, EVEN_TOKENS_0X5555, ODD_TOKENS_0XAAAA,
      EMPTY_BLOCK_0X0000, MIXED_0X1234, ALL_BUT_TOKEN_0_0XFFFE, ALL_BUT_TOKEN_15_0X7FFF,
      NIBBLES_0X0F0F, TOKEN_1_0X0002, TOKEN_14_0X4000};
  for (int i = 0; i < N_RANDOM_MASKS_24; ++i) {
    masks.push_back(bits(gen));
  }
  size_t checked = 0;
  for (size_t c = 0; c < TOKEN_BLOCKS_4; ++c) {
    for (unsigned m : masks) {
      poison_plane(ref->plane, POISON_0XA5A5);
      blk->plane = ref->plane;  // the owner copy: same bytes
      const tron::bf16* rows[BLOCK_TOKENS_16] = {};
      for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
        if (!((m >> t) & 1u)) continue;
        const size_t tok = c * BLOCK_TOKENS_16 + t;
        rows[t] = ref->rows + tok * HEAD_SIZE_128;
        tron::store_row(ref->plane.as_view(), tok, row_of(*ref, tok));
      }
      tron::store_block(blk->plane.as_view(), c, __mmask16(m), rows);
      REQUIRE(std::memcmp(&blk->plane, &ref->plane, sizeof(ref->plane)) == 0);
      ++checked;
    }
  }
  REQUIRE(checked == TOKEN_BLOCKS_4 * masks.size());
  SECTION("a block save on top of other blocks changes only its own block") {
    constexpr size_t NEW_BLOCK_2 = 2;
    constexpr size_t NEW_FIRST_TOKEN_32 = NEW_BLOCK_2 * BLOCK_TOKENS_16;
    constexpr size_t NEW_END_TOKEN_48 = NEW_FIRST_TOKEN_32 + BLOCK_TOKENS_16;
    static_assert(NEW_FIRST_TOKEN_32 == 32 && NEW_END_TOKEN_48 == 48,
        "every constant's name states its value");
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      tron::store_row(ref->plane.as_view(), tok, row_of(*ref, tok));
    }
    blk->plane = ref->plane;
    // New rows for block 2 only.
    for (size_t tok = NEW_FIRST_TOKEN_32; tok < NEW_END_TOKEN_48; ++tok) {
      for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
        ref->rows[tok * HEAD_SIZE_128 + d] = tron::bf16::from_bits(bits(gen));
      }
    }
    const tron::bf16* rows[BLOCK_TOKENS_16];
    for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
      rows[t] = ref->rows + (NEW_FIRST_TOKEN_32 + t) * HEAD_SIZE_128;
      tron::store_row(ref->plane.as_view(), NEW_FIRST_TOKEN_32 + t,
          row_of(*ref, NEW_FIRST_TOKEN_32 + t));
    }
    tron::store_block(blk->plane.as_view(), NEW_BLOCK_2, FULL_BLOCK_0XFFFF, rows);
    REQUIRE(std::memcmp(&blk->plane, &ref->plane, sizeof(ref->plane)) == 0);
    alignas(64) tron::bf16 row[HEAD_SIZE_128];
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      tron::load_row(std::as_const(blk->plane).as_view(), tok,
          tron::k_destination_row<HEAD_SIZE_128>(row));
      REQUIRE(std::memcmp(row, ref->rows + tok * HEAD_SIZE_128, sizeof(row)) == 0);
    }
  }
}
TEST_CASE("row-major tail block converts to the VNNI layout and back, bit for bit",
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

namespace {

// The reader against the row-major dotter for one query-group size (KV_MUL
// query heads sharing the K/V head). qk_group scores groups wider than 16 heads
// in passes of 16. 20 heads is an uneven split (16 + 4). 32 heads is an even
// split (16 + 16).
template <size_t KV_MUL>
void check_reader_against_dotter() {
  // Same numerics contract as the AMX kernels (Note [AMX attention dispatch]).
  // For the bf16 query both readers add the same exact bf16 x bf16 products in
  // fp32. For the fp32 query both widen K to fp32 and use FMA (fused
  // multiply-add). So only the add order may differ. An fp16 (16-bit IEEE
  // half) query is widened to fp32 once by the reader. So it is checked
  // against the dotter on the widened query. Envelope: 1e-4 of the
  // absolute-product mass plus 1e-6. Tokens outside the live mask keep their
  // preset value. Their storage holds NaN (not a number) poison. A stray load
  // would spread it into the scores.
  constexpr uint32_t SEED_31 = 31;
  // Queries and keys are drawn from [-1, 1).
  constexpr float VALUE_RANGE_1 = 1.f;
  // Masks with holes: two mt19937 outputs (32 bits each) make one 64-token mask.
  constexpr int N_HOLE_MASKS_24 = 24;
  constexpr int GEN_WORD_BITS_32 = 32;
  // Single live tokens: the last token, the first token of token block 1.
  constexpr size_t LAST_TOKEN_63 = 63;
  constexpr size_t BLOCK_1_FIRST_TOKEN_16 = 16;
  // A quiet NaN (the NaN kind that raises no exception): the storage of dead tokens.
  constexpr uint16_t NAN_POISON_0X7FC1 = 0x7fc1;
  // Dead tokens keep this preset. A stray load would overwrite it.
  constexpr float PRESET_NEG_INF = -std::numeric_limits<float>::infinity();
  constexpr double REL_TOL_1E_MINUS_4 = 1e-4;
  constexpr double ABS_TOL_1E_MINUS_6 = 1e-6;
  auto buf = std::make_unique<plane_and_rows>();
  std::mt19937 gen(SEED_31);
  std::uniform_real_distribution<float> u(-VALUE_RANGE_1, VALUE_RANGE_1);
  alignas(64) tron::bf16 q_bf16[KV_MUL * HEAD_SIZE_128];
  alignas(64) float q_f32[KV_MUL * HEAD_SIZE_128];
  alignas(64) tron::fp16 q_f16[KV_MUL * HEAD_SIZE_128];
  alignas(64) float q_f16_widened[KV_MUL * HEAD_SIZE_128];  // the fp16 values as fp32
  for (size_t i = 0; i < KV_MUL * HEAD_SIZE_128; ++i) {
    q_bf16[i] = tron::bf16::from_bits(bf16_rne(u(gen)));
    q_f32[i] = u(gen);
    q_f16[i] = tron::fp16(u(gen));
    q_f16_widened[i] = float(q_f16[i]);
  }
  for (auto& x : buf->rows) {
    x = tron::bf16::from_bits(bf16_rne(u(gen)));
  }
  std::vector<uint64_t> masks;
  for (size_t n = 0; n <= PAGE_TOKENS_64; ++n) {  // every prefix, 0 and 64 included
    masks.push_back(n == PAGE_TOKENS_64 ? ~uint64_t{0} : ((uint64_t{1} << n) - 1));
  }
  for (int i = 0; i < N_HOLE_MASKS_24; ++i) {  // holes
    masks.push_back((uint64_t(gen()) << GEN_WORD_BITS_32) | uint64_t(gen()));
  }
  masks.push_back(uint64_t{1} << LAST_TOKEN_63);
  masks.push_back(uint64_t{1} << BLOCK_1_FIRST_TOKEN_16);

  for (uint64_t live : masks) {
    // Only live tokens are stored. The rest of the plane is NaN poison.
    poison_plane(buf->plane, NAN_POISON_0X7FC1);
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      if ((live >> tok) & 1) {
        tron::store_row(buf->plane.as_view(), tok, row_of(*buf, tok));
      }
    }
    alignas(64) float s_bf16[KV_MUL][PAGE_TOKENS_64];
    alignas(64) float s_f32[KV_MUL][PAGE_TOKENS_64];
    alignas(64) float s_f16[KV_MUL][PAGE_TOKENS_64];
    for (auto* scores : {&s_bf16, &s_f32, &s_f16}) {
      for (auto& row : *scores) {
        for (auto& x : row) {
          x = PRESET_NEG_INF;
        }
      }
    }
    auto const plane = std::as_const(buf->plane).as_view();
    tron::k_vnni::qk_group<KV_MUL>(plane, q_bf16, live, &s_bf16[0][0], PAGE_TOKENS_64);
    tron::k_vnni::qk_group<KV_MUL>(plane, q_f32, live, &s_f32[0][0], PAGE_TOKENS_64);
    tron::k_vnni::qk_group<KV_MUL>(plane, q_f16, live, &s_f16[0][0], PAGE_TOKENS_64);
    for (size_t h = 0; h < KV_MUL; ++h) {
      tron::const_view<tron::bf16, tron::VIEW_ALIGNED_TRUE, tron::VIEW_DMA_FALSE,
          tron::seq<HEAD_SIZE_128>>
          qv_bf16{q_bf16 + h * HEAD_SIZE_128};
      tron::const_view<float, tron::VIEW_ALIGNED_TRUE, tron::VIEW_DMA_FALSE,
          tron::seq<HEAD_SIZE_128>>
          qv_f32{q_f32 + h * HEAD_SIZE_128};
      tron::const_view<float, tron::VIEW_ALIGNED_TRUE, tron::VIEW_DMA_FALSE,
          tron::seq<HEAD_SIZE_128>>
          qv_f16_widened{q_f16_widened + h * HEAD_SIZE_128};
      tron::dotter<tron::bf16, HEAD_SIZE_128> dot_bf16(qv_bf16);
      tron::dotter<float, HEAD_SIZE_128> dot_f32(qv_f32);
      tron::dotter<float, HEAD_SIZE_128> dot_f16_widened(qv_f16_widened);
      for (size_t t = 0; t < PAGE_TOKENS_64; ++t) {
        CAPTURE(live, h, t);
        if (!((live >> t) & 1)) {
          REQUIRE(s_bf16[h][t] == PRESET_NEG_INF);
          REQUIRE(s_f32[h][t] == PRESET_NEG_INF);
          REQUIRE(s_f16[h][t] == PRESET_NEG_INF);
          continue;
        }
        tron::const_view<tron::bf16, tron::VIEW_ALIGNED_TRUE, tron::VIEW_DMA_FALSE,
            tron::seq<HEAD_SIZE_128>>
            kv{buf->rows + t * HEAD_SIZE_128};
        double mass_bf16 = 0, mass_f32 = 0, mass_f16 = 0;
        for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
          const double k = bf16_to_float(buf->rows[t * HEAD_SIZE_128 + d].to_bits());
          mass_bf16 += std::fabs(
              double(bf16_to_float(q_bf16[h * HEAD_SIZE_128 + d].to_bits())) * k);
          mass_f32 += std::fabs(double(q_f32[h * HEAD_SIZE_128 + d]) * k);
          mass_f16 += std::fabs(double(q_f16_widened[h * HEAD_SIZE_128 + d]) * k);
        }
        REQUIRE(std::fabs(double(s_bf16[h][t]) - double(dot_bf16(kv))) <=
                REL_TOL_1E_MINUS_4 * mass_bf16 + ABS_TOL_1E_MINUS_6);
        REQUIRE(std::fabs(double(s_f32[h][t]) - double(dot_f32(kv))) <=
                REL_TOL_1E_MINUS_4 * mass_f32 + ABS_TOL_1E_MINUS_6);
        REQUIRE(std::fabs(double(s_f16[h][t]) - double(dot_f16_widened(kv))) <=
                REL_TOL_1E_MINUS_4 * mass_f16 + ABS_TOL_1E_MINUS_6);
      }
    }
  }
}

}  // namespace

TEST_CASE(
    "VNNI K reader does not digress from the row-major dotter", "[kv_data][k_vnni]") {
  constexpr size_t KV_MUL_4 = 4;
  constexpr size_t KV_MUL_20 = 20;
  constexpr size_t KV_MUL_32 = 32;
  SECTION("4 query heads (one pass)") {
    check_reader_against_dotter<KV_MUL_4>();
  }
  SECTION("20 query heads (passes of 16 and 4)") {
    check_reader_against_dotter<KV_MUL_20>();
  }
  SECTION("32 query heads (two passes of 16)") {
    check_reader_against_dotter<KV_MUL_32>();
  }
}

namespace {

// One slot, one KV head of 128 dimensions: a VNNI slot under TRON_K_VNNI, a
// row-major slot otherwise. The accessors and the append path below are
// layout-agnostic. So the same checks hold in both builds.
constexpr size_t N_SLOTS_1 = 1;
constexpr size_t N_KV_HEADS_1 = 1;
using book_t = tron::
    uniform_kv_cache<N_SLOTS_1, tron::kv_geometry{N_KV_HEADS_1, HEAD_SIZE_128}, 0>;
using page_t = book_t::page_t;
constexpr tron::kv_slot_id SLOT_0(0);
// Every book below has one page.
constexpr size_t N_PAGES_1 = 1;

// Distinct finite bf16 bit patterns per (salt, token, dimension). The salt selects
// one of four ranges of 16 Ki (0x4000) bit patterns. token * 128 + d (< 0x2000)
// selects the position inside it. Every pattern is shifted up by 0x0800
// (PATTERN_BASE_0X0800). So every (token, dimension) of one salt is distinct.
// No pattern reaches the inf (infinity) / NaN range 0x7f80..0x7fff or
// 0xff80..0xffff. NaN is unequal to itself. That would hide a correct copy.
void fill_row(std::array<tron::bf16, HEAD_SIZE_128>& row, size_t token, size_t salt) {
  constexpr size_t N_SALT_RANGES_4 = 4;
  constexpr size_t SALT_RANGE_0X4000 = 0x4000;
  constexpr size_t PATTERN_BASE_0X0800 = 0x0800;
  for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
    row[d] = tron::bf16::from_bits(static_cast<uint16_t>(
        PATTERN_BASE_0X0800 + (salt % N_SALT_RANGES_4) * SALT_RANGE_0X4000 +
        token * HEAD_SIZE_128 + d));
  }
}

// Bit-exact comparison of two rows. bf16 operator== compares values. The test
// must see every stored bit.
bool same_bits(const std::array<tron::bf16, HEAD_SIZE_128>& a,
    const std::array<tron::bf16, HEAD_SIZE_128>& b) {
  for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
    if (a[d].to_bits() != b[d].to_bits()) return false;
  }
  return true;
}

}  // namespace

TEST_CASE(
    "page K rows survive the store, the load and an append", "[kv_data][k_vnni]") {
  static_assert(book_t::page_size == PAGE_TOKENS_64);
#ifdef TRON_K_VNNI
  STATIC_REQUIRE(tron::k_vnni::layout_on<HEAD_SIZE_128>);
#else
  STATIC_REQUIRE_FALSE(tron::k_vnni::layout_on<HEAD_SIZE_128>);
#endif
  alignas(64) std::array<tron::bf16, HEAD_SIZE_128> row{}, got{};
  SECTION("store and load, every token of a page") {
    constexpr size_t STORED_SALT_1 = 1;
    book_t cache(/*n_pages=*/N_PAGES_1);
    cache.increment_tokens_used(PAGE_TOKENS_64);
    page_t* page = cache.page_of(0);
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      fill_row(row, tok, STORED_SALT_1);
      page->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    }
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      fill_row(row, tok, STORED_SALT_1);
      page->get_k_row(
          SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
  }
  SECTION("append into a partly filled page moves tokens to new offsets") {
    // Destination holds 5 tokens. The source's 20 tokens are copied to offsets
    // 5..24 of the destination's first page. This is the token-by-token copy
    // path.
    constexpr size_t OLD_TOKENS_5 = 5;
    constexpr size_t NEW_TOKENS_20 = 20;
    constexpr size_t OLD_SALT_2 = 2;
    constexpr size_t NEW_SALT_3 = 3;
    book_t destination(/*n_pages=*/N_PAGES_1);
    book_t source(/*n_pages=*/N_PAGES_1);
    destination.increment_tokens_used(OLD_TOKENS_5);
    source.increment_tokens_used(NEW_TOKENS_20);
    for (size_t tok = 0; tok < OLD_TOKENS_5; ++tok) {
      fill_row(row, tok, OLD_SALT_2);
      destination.page_of(tok)->set_k_row(
          SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    }
    for (size_t tok = 0; tok < NEW_TOKENS_20; ++tok) {
      fill_row(row, tok, NEW_SALT_3);
      source.page_of(tok)->set_k_row(
          SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    }
    destination.append(source);
    REQUIRE(destination.size() == OLD_TOKENS_5 + NEW_TOKENS_20);
    for (size_t tok = 0; tok < OLD_TOKENS_5; ++tok) {  // the old tokens are untouched
      fill_row(row, tok, OLD_SALT_2);
      destination.page_of(tok)->get_k_row(
          SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
    for (size_t tok = 0; tok < NEW_TOKENS_20; ++tok) {
      fill_row(row, tok, NEW_SALT_3);
      destination.page_of(OLD_TOKENS_5 + tok)
          ->get_k_row(SLOT_0, 0, OLD_TOKENS_5 + tok,
              tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
  }
  SECTION("append of a full page into an empty book copies the whole page") {
    constexpr size_t FULL_PAGE_SALT_4 = 4;
    book_t destination(/*n_pages=*/N_PAGES_1);
    book_t source(/*n_pages=*/N_PAGES_1);
    source.increment_tokens_used(PAGE_TOKENS_64);
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      fill_row(row, tok, FULL_PAGE_SALT_4);
      source.page_of(tok)->set_k_row(
          SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    }
    destination.append(source);
    REQUIRE(destination.size() == PAGE_TOKENS_64);
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      fill_row(row, tok, FULL_PAGE_SALT_4);
      destination.page_of(tok)->get_k_row(
          SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
  }
}

namespace {

[[maybe_unused]] constexpr tron::kv_geometry GEOMETRY_1X128{
    N_KV_HEADS_1, HEAD_SIZE_128};
// No block of the page holds the VNNI layout.
constexpr uint8_t NO_BLOCK_0X0 = 0x0;
// The rows 0 .. tok are tok + NEXT_ROW_1 rows.
constexpr size_t NEXT_ROW_1 = 1;
// A book that carries the EAGLE storage slot.
constexpr bool SUPPORT_EAGLE_TRUE = true;
// A second slot for the multi-slot case below.
constexpr size_t N_SLOTS_2 = 2;
using book2_t = tron::uniform_kv_cache<N_SLOTS_2, GEOMETRY_1X128, 0>;
using page2_t = book2_t::page_t;
constexpr tron::kv_slot_id SLOT_1(1);

// What save_k plus the forward end do per row (Note [K VNNI storage]): record
// the row; when it completes its 16-token block, convert the block to the VNNI
// layout. Returns whether the block was completed by this row (always false in
// the row-major build: a row-major slot keeps no bits).
template <typename P>
bool save_row_state(P* page, tron::kv_slot_id slot, size_t tok) {
  const bool completed = page->note_k_row_saved(slot, tok);
  if (completed) page->k_block_to_vnni(slot, tok / BLOCK_TOKENS_16);
  return completed;
}

// The page's VNNI blocks; 0 in the row-major build (no block is ever VNNI).
template <typename P>
uint8_t vnni_blocks(const P* page, tron::kv_slot_id slot) {
#ifdef TRON_K_VNNI
  return page->template k_vnni_blocks<GEOMETRY_1X128>(slot);
#else
  (void)page;
  (void)slot;
  return NO_BLOCK_0X0;
#endif
}

}  // namespace

TEST_CASE("page K blocks turn VNNI at the 16th saved row and back when a row is "
          "forgotten",
    "[kv_data][k_vnni]") {
  // Note [K VNNI storage]: a block holds the VNNI layout exactly when its 16
  // rows are saved. Every row stays readable through get_k_row across the
  // transitions, and the raw plane holds the documented bytes on both sides.
  constexpr size_t SALT_5 = 5;
  constexpr size_t SAVED_TOKENS_21 = 21;  // block 0 complete, block 1 with 5 rows
  constexpr size_t LAST_OF_BLOCK_0_15 = 15;
  constexpr size_t FORGOTTEN_TOKEN_3 = 3;
  constexpr size_t FORGOTTEN_TOKEN_18 = 18;  // a row of the row-major block 1
  constexpr size_t FORGOTTEN_TOKEN_16 = 16;  // the first row of block 1
  constexpr size_t LAST_OF_BLOCK_1_31 = 31;
  constexpr size_t SAVED_TOKENS_32 = 32;
  constexpr uint8_t BLOCK_0_ONLY_0X1 = 0x1;
  constexpr uint8_t BLOCKS_0_AND_1_0X3 = 0x3;
  static_assert(SAVED_TOKENS_21 == 21 && LAST_OF_BLOCK_0_15 == 15,
      "every constant's name states its value");
  const bool vnni_build = tron::k_vnni::layout_on<HEAD_SIZE_128>;
  alignas(LINE_BYTES_64) std::array<tron::bf16, HEAD_SIZE_128> row{}, got{};
  book_t cache(/*n_pages=*/N_PAGES_1);
  cache.increment_tokens_used(PAGE_TOKENS_64);
  page_t* page = cache.page_of(0);
  auto check_rows = [&](size_t n, size_t skip) {
    for (size_t tok = 0; tok < n; ++tok) {
      if (tok == skip) continue;
      fill_row(row, tok, SALT_5);
      page->get_k_row(
          SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
  };
  for (size_t tok = 0; tok < SAVED_TOKENS_21; ++tok) {
    fill_row(row, tok, SALT_5);
    page->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    CAPTURE(tok);
    REQUIRE(
        save_row_state(page, SLOT_0, tok) == (vnni_build && tok == LAST_OF_BLOCK_0_15));
    REQUIRE(
        vnni_blocks(page, SLOT_0) ==
        (vnni_build && tok >= LAST_OF_BLOCK_0_15 ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
    check_rows(tok + NEXT_ROW_1, PAGE_TOKENS_64);
  }
#ifdef TRON_K_VNNI
  {
    // The plane: block 0 holds the VNNI columns of rows 0..15 (the elements
    // store_row wrote, read back through at()); block 1 holds rows 16..20
    // row-major (row_major_row).
    const auto plane = page->template k_packed<GEOMETRY_1X128>(SLOT_0, 0);
    for (size_t tok = 0; tok < SAVED_TOKENS_21; ++tok) {
      fill_row(row, tok, SALT_5);
      CAPTURE(tok);
      if (tok < BLOCK_TOKENS_16) {
        for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
          REQUIRE(plane.at(tok, d).to_bits() == row[d].to_bits());
        }
      } else {
        REQUIRE(std::memcmp(tron::row_major_row(plane, tok).data, row.data(),
                    sizeof(row)) == 0);
      }
    }
  }
#endif
  // A new token takes offset 3: the rows at and above 3 are forgotten, the
  // block goes back to row-major, and rows 0..2 stay readable.
  page->clear_kv_complete_at(FORGOTTEN_TOKEN_3);
  REQUIRE(vnni_blocks(page, SLOT_0) == NO_BLOCK_0X0);
  check_rows(FORGOTTEN_TOKEN_3, PAGE_TOKENS_64);
  // Saving rows 3..20 again completes block 0 at row 15 again.
  for (size_t tok = FORGOTTEN_TOKEN_3; tok < SAVED_TOKENS_21; ++tok) {
    fill_row(row, tok, SALT_5);
    page->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    CAPTURE(tok);
    REQUIRE(
        save_row_state(page, SLOT_0, tok) == (vnni_build && tok == LAST_OF_BLOCK_0_15));
  }
  REQUIRE(vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
  check_rows(SAVED_TOKENS_21, PAGE_TOKENS_64);
  // A row saved again into a converted block keeps the block VNNI.
  fill_row(row, LAST_OF_BLOCK_0_15, SALT_5);
  page->set_k_row(
      SLOT_0, 0, LAST_OF_BLOCK_0_15, tron::k_source_row<HEAD_SIZE_128>(row.data()));
  REQUIRE_FALSE(save_row_state(page, SLOT_0, LAST_OF_BLOCK_0_15));
  REQUIRE(vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
  check_rows(SAVED_TOKENS_21, PAGE_TOKENS_64);
  // A new token takes offset 18, a row of the row-major block 1: block 0 stays
  // VNNI, rows 0..17 stay readable, and block 1 completes only once rows
  // 18..31 are saved.
  page->clear_kv_complete_at(FORGOTTEN_TOKEN_18);
  REQUIRE(vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
  check_rows(FORGOTTEN_TOKEN_18, PAGE_TOKENS_64);
  for (size_t tok = FORGOTTEN_TOKEN_18; tok < SAVED_TOKENS_32; ++tok) {
    fill_row(row, tok, SALT_5);
    page->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    CAPTURE(tok);
    REQUIRE(
        save_row_state(page, SLOT_0, tok) == (vnni_build && tok == LAST_OF_BLOCK_1_31));
  }
  REQUIRE(
      vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCKS_0_AND_1_0X3 : NO_BLOCK_0X0));
  check_rows(SAVED_TOKENS_32, PAGE_TOKENS_64);
  // A new token takes offset 16, the first row of the converted block 1: no
  // row of that block survives, so only its bits drop; block 0 stays VNNI.
  page->clear_kv_complete_at(FORGOTTEN_TOKEN_16);
  REQUIRE(vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
  check_rows(FORGOTTEN_TOKEN_16, PAGE_TOKENS_64);
  // Rows 16..31 again (blocks 0 and 1 converted), then a new token at offset
  // 3: block 0 goes back to row-major for rows 0..2, block 1 above it only
  // drops its bits and its bytes stay as they are.
  for (size_t tok = FORGOTTEN_TOKEN_16; tok < SAVED_TOKENS_32; ++tok) {
    fill_row(row, tok, SALT_5);
    page->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    save_row_state(page, SLOT_0, tok);
  }
  REQUIRE(
      vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCKS_0_AND_1_0X3 : NO_BLOCK_0X0));
#ifdef TRON_K_VNNI
  // Block 1's bytes: its 4 panels are exactly the elements at(tok, d) of the
  // tokens 16..31 (Note [K VNNI storage]: token i owns column i % 16 of block
  // i / 16 in every panel).
  auto block_1_bytes = [&] {
    std::array<uint16_t, BLOCK_TOKENS_16 * HEAD_SIZE_128> bytes{};
    const auto plane = page->template k_packed<GEOMETRY_1X128>(SLOT_0, 0);
    for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
      for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
        bytes[t * HEAD_SIZE_128 + d] = plane.at(BLOCK_TOKENS_16 + t, d).to_bits();
      }
    }
    return bytes;
  };
  const auto snap = block_1_bytes();
#endif
  page->clear_kv_complete_at(FORGOTTEN_TOKEN_3);
  REQUIRE(vnni_blocks(page, SLOT_0) == NO_BLOCK_0X0);
  check_rows(FORGOTTEN_TOKEN_3, PAGE_TOKENS_64);
#ifdef TRON_K_VNNI
  // Block 1's 4 panels are byte-identical to the snapshot.
  REQUIRE(block_1_bytes() == snap);
#endif
}

TEST_CASE("the EAGLE storage view keeps its own K layout state", "[kv_data][k_vnni]") {
  // Note [K VNNI storage]: while the EAGLE view is active, logical slot 0
  // addresses the extra storage slot and the extra state entry. Rows recorded
  // and converted under the view must not show up in the primary slot's
  // state, and each view reads its own rows.
  constexpr size_t PRIMARY_SALT_9 = 9;
  constexpr size_t EAGLE_SALT_10 = 10;
  constexpr size_t FORGOTTEN_TOKEN_5 = 5;
  constexpr size_t LAST_OF_BLOCK_0_15 = 15;
  constexpr uint8_t BLOCK_0_ONLY_0X1 = 0x1;
  const bool vnni_build = tron::k_vnni::layout_on<HEAD_SIZE_128>;
  alignas(LINE_BYTES_64) std::array<tron::bf16, HEAD_SIZE_128> row{}, got{};
  // An EAGLE-capable book carries x storage (the hidden state per token, 16
  // bytes here); the layout book without it cannot allocate the EAGLE slot.
  constexpr size_t X_BYTES_16 = 16;
  using eagle_book_t = tron::uniform_kv_cache<N_SLOTS_1, GEOMETRY_1X128, X_BYTES_16>;
  constexpr size_t STORAGE_SLOTS_2 = eagle_book_t::storage_slot_count_for_layers(
      /*max_model_layers=*/N_SLOTS_1, SUPPORT_EAGLE_TRUE);
  static_assert(STORAGE_SLOTS_2 == 2, "one logical slot plus the EAGLE storage");
  eagle_book_t cache(/*n_pages=*/N_PAGES_1, STORAGE_SLOTS_2, SUPPORT_EAGLE_TRUE);
  cache.increment_tokens_used(PAGE_TOKENS_64);
  eagle_book_t::page_t* page = cache.page_of(0);
  // Primary view: 16 rows saved and converted.
  for (size_t tok = 0; tok < BLOCK_TOKENS_16; ++tok) {
    fill_row(row, tok, PRIMARY_SALT_9);
    page->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    save_row_state(page, SLOT_0, tok);
  }
  REQUIRE(vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
  // EAGLE view: its own 16 rows, converted separately.
  cache.set_storage_view(cache.eagle_storage_offset());
  REQUIRE(vnni_blocks(page, SLOT_0) == NO_BLOCK_0X0);
  for (size_t tok = 0; tok < BLOCK_TOKENS_16; ++tok) {
    fill_row(row, tok, EAGLE_SALT_10);
    page->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    CAPTURE(tok);
    REQUIRE(
        save_row_state(page, SLOT_0, tok) == (vnni_build && tok == LAST_OF_BLOCK_0_15));
  }
  REQUIRE(vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
  for (size_t tok = 0; tok < BLOCK_TOKENS_16; ++tok) {
    fill_row(row, tok, EAGLE_SALT_10);
    page->get_k_row(SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
    CAPTURE(tok);
    REQUIRE(same_bits(got, row));
  }
  // Back to the primary view: its state and rows are untouched.
  cache.reset_storage_view();
  REQUIRE(vnni_blocks(page, SLOT_0) == (vnni_build ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
  for (size_t tok = 0; tok < BLOCK_TOKENS_16; ++tok) {
    fill_row(row, tok, PRIMARY_SALT_9);
    page->get_k_row(SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
    CAPTURE(tok);
    REQUIRE(same_bits(got, row));
  }
  // A new token at offset 5 forgets rows 5.. in both storages; rows 0..4 of
  // both stay readable (each storage converted back on its own).
  page->clear_kv_complete_at(FORGOTTEN_TOKEN_5);
  REQUIRE(vnni_blocks(page, SLOT_0) == NO_BLOCK_0X0);
  for (size_t tok = 0; tok < FORGOTTEN_TOKEN_5; ++tok) {
    fill_row(row, tok, PRIMARY_SALT_9);
    page->get_k_row(SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
    CAPTURE(tok);
    REQUIRE(same_bits(got, row));
  }
  cache.set_storage_view(cache.eagle_storage_offset());
  REQUIRE(vnni_blocks(page, SLOT_0) == NO_BLOCK_0X0);
  for (size_t tok = 0; tok < FORGOTTEN_TOKEN_5; ++tok) {
    fill_row(row, tok, EAGLE_SALT_10);
    page->get_k_row(SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
    CAPTURE(tok);
    REQUIRE(same_bits(got, row));
  }
  cache.reset_storage_view();
}

TEST_CASE("forgetting a row acts on every slot's own block", "[kv_data][k_vnni]") {
  // Note [K VNNI storage]: clear_kv_complete_at drops the bits of the offset
  // in every storage slot and converts back only the slots whose block was
  // converted. Two slots, converted in one of them only.
  constexpr size_t SALT_8 = 8;
  constexpr size_t FORGOTTEN_TOKEN_3 = 3;
  constexpr uint8_t BLOCK_0_ONLY_0X1 = 0x1;
  const bool vnni_build = tron::k_vnni::layout_on<HEAD_SIZE_128>;
  alignas(LINE_BYTES_64) std::array<tron::bf16, HEAD_SIZE_128> row{}, got{};
  book2_t cache(/*n_pages=*/N_PAGES_1);
  cache.increment_tokens_used(PAGE_TOKENS_64);
  page2_t* page = cache.page_of(0);
  for (size_t tok = 0; tok < BLOCK_TOKENS_16; ++tok) {
    fill_row(row, tok, SALT_8);
    page->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    page->set_k_row(SLOT_1, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
    // Slot 1 records its rows (and converts at row 15); slot 0 does not.
    save_row_state(page, SLOT_1, tok);
  }
  REQUIRE(vnni_blocks(page, SLOT_0) == NO_BLOCK_0X0);
  REQUIRE(vnni_blocks(page, SLOT_1) == (vnni_build ? BLOCK_0_ONLY_0X1 : NO_BLOCK_0X0));
  page->clear_kv_complete_at(FORGOTTEN_TOKEN_3);
  REQUIRE(vnni_blocks(page, SLOT_0) == NO_BLOCK_0X0);
  REQUIRE(vnni_blocks(page, SLOT_1) == NO_BLOCK_0X0);
  for (size_t tok = 0; tok < BLOCK_TOKENS_16; ++tok) {
    if (tok == FORGOTTEN_TOKEN_3) continue;  // forgotten in every slot
    fill_row(row, tok, SALT_8);
    CAPTURE(tok);
    page->get_k_row(SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
    REQUIRE(same_bits(got, row));
    if (tok < FORGOTTEN_TOKEN_3) {  // the rows slot 1 keeps
      page->get_k_row(
          SLOT_1, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      REQUIRE(same_bits(got, row));
    }
  }
}

TEST_CASE("page append carries the K layout state with the rows", "[kv_data][k_vnni]") {
  // Note [K VNNI storage] item 5: the token-by-token copy moves rows between
  // blocks of both layouts. Afterwards the destination's blocks are VNNI
  // exactly where its 16 rows are saved.
  constexpr size_t OLD_TOKENS_5 = 5;
  constexpr size_t NEW_TOKENS_40 =
      40;  // source: blocks 0 and 1 VNNI, block 2 with 8 rows
  constexpr size_t OLD_SALT_6 = 6;
  constexpr size_t NEW_SALT_7 = 7;
  constexpr uint8_t BLOCKS_0_AND_1_0X3 = 0x3;
  constexpr uint8_t BLOCKS_PER_PAGE_MASK_0XF = tron::k_vnni::BLOCKS_PER_PAGE_MASK_0XF;
  constexpr size_t TOTAL_TOKENS_45 = OLD_TOKENS_5 + NEW_TOKENS_40;
  static_assert(TOTAL_TOKENS_45 == 45, "blocks 0 and 1 complete, block 2 with 13 rows");
  const bool vnni_build = tron::k_vnni::layout_on<HEAD_SIZE_128>;
  alignas(LINE_BYTES_64) std::array<tron::bf16, HEAD_SIZE_128> row{}, got{};
  SECTION("token-by-token append into a partly filled page") {
    book_t destination(/*n_pages=*/N_PAGES_1);
    book_t source(/*n_pages=*/N_PAGES_1);
    destination.increment_tokens_used(OLD_TOKENS_5);
    source.increment_tokens_used(NEW_TOKENS_40);
    for (size_t tok = 0; tok < OLD_TOKENS_5; ++tok) {
      fill_row(row, tok, OLD_SALT_6);
      destination.page_of(tok)->set_k_row(
          SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
      REQUIRE_FALSE(save_row_state(destination.page_of(tok), SLOT_0, tok));
    }
    for (size_t tok = 0; tok < NEW_TOKENS_40; ++tok) {
      fill_row(row, tok, NEW_SALT_7);
      source.page_of(tok)->set_k_row(
          SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
      save_row_state(source.page_of(tok), SLOT_0, tok);
    }
    REQUIRE(vnni_blocks(source.page_of(0), SLOT_0) ==
            (vnni_build ? BLOCKS_0_AND_1_0X3 : NO_BLOCK_0X0));
    destination.append(source);
    REQUIRE(destination.size() == TOTAL_TOKENS_45);
    REQUIRE(vnni_blocks(destination.page_of(0), SLOT_0) ==
            (vnni_build ? BLOCKS_0_AND_1_0X3 : NO_BLOCK_0X0));
    for (size_t tok = 0; tok < OLD_TOKENS_5; ++tok) {
      fill_row(row, tok, OLD_SALT_6);
      destination.page_of(tok)->get_k_row(
          SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
    for (size_t tok = 0; tok < NEW_TOKENS_40; ++tok) {
      fill_row(row, tok, NEW_SALT_7);
      destination.page_of(OLD_TOKENS_5 + tok)
          ->get_k_row(SLOT_0, 0, OLD_TOKENS_5 + tok,
              tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
  }
  SECTION("append into a converted destination block converts it back and forth") {
    // The destination page has 64 recorded rows (every block converted) but a
    // size of 20; the source's 10 rows land at offsets 20..29 inside block 1.
    // Block 1 must go back to row-major for the copy, keep rows 16..19 and
    // 30..31, and come back as VNNI (its 16 rows are saved after the copy).
    constexpr size_t DST_SIZE_20 = 20;
    constexpr size_t SRC_TOKENS_10 = 10;
    constexpr size_t COPIED_END_30 = DST_SIZE_20 + SRC_TOKENS_10;
    static_assert(COPIED_END_30 == 30, "the constant's name states its value");
    book_t destination(/*n_pages=*/N_PAGES_1);
    book_t source(/*n_pages=*/N_PAGES_1);
    destination.increment_tokens_used(DST_SIZE_20);
    source.increment_tokens_used(SRC_TOKENS_10);
    page_t* dst = destination.page_of(0);
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      fill_row(row, tok, OLD_SALT_6);
      dst->set_k_row(SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
      save_row_state(dst, SLOT_0, tok);
    }
    REQUIRE(vnni_blocks(dst, SLOT_0) ==
            (vnni_build ? BLOCKS_PER_PAGE_MASK_0XF : NO_BLOCK_0X0));
    for (size_t tok = 0; tok < SRC_TOKENS_10; ++tok) {
      fill_row(row, tok, NEW_SALT_7);
      source.page_of(tok)->set_k_row(
          SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
      save_row_state(source.page_of(tok), SLOT_0, tok);
    }
    destination.append(source);
    REQUIRE(destination.size() == COPIED_END_30);
    REQUIRE(vnni_blocks(dst, SLOT_0) ==
            (vnni_build ? BLOCKS_PER_PAGE_MASK_0XF : NO_BLOCK_0X0));
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      const bool copied = tok >= DST_SIZE_20 && tok < COPIED_END_30;
      if (copied) {
        fill_row(row, tok - DST_SIZE_20, NEW_SALT_7);
      } else {
        fill_row(row, tok, OLD_SALT_6);
      }
      dst->get_k_row(
          SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
  }
  SECTION("whole-page append copies the state of a fully VNNI page") {
    book_t destination(/*n_pages=*/N_PAGES_1);
    book_t source(/*n_pages=*/N_PAGES_1);
    source.increment_tokens_used(PAGE_TOKENS_64);
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      fill_row(row, tok, NEW_SALT_7);
      source.page_of(tok)->set_k_row(
          SLOT_0, 0, tok, tron::k_source_row<HEAD_SIZE_128>(row.data()));
      save_row_state(source.page_of(tok), SLOT_0, tok);
    }
    REQUIRE(vnni_blocks(source.page_of(0), SLOT_0) ==
            (vnni_build ? BLOCKS_PER_PAGE_MASK_0XF : NO_BLOCK_0X0));
    destination.append(source);
    REQUIRE(vnni_blocks(destination.page_of(0), SLOT_0) ==
            (vnni_build ? BLOCKS_PER_PAGE_MASK_0XF : NO_BLOCK_0X0));
    for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
      fill_row(row, tok, NEW_SALT_7);
      destination.page_of(tok)->get_k_row(
          SLOT_0, 0, tok, tron::k_destination_row<HEAD_SIZE_128>(got.data()));
      CAPTURE(tok);
      REQUIRE(same_bits(got, row));
    }
  }
}
