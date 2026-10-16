// This file tests the VNNI (Vector Neural Network Instructions) K storage layout
// (Note [K VNNI storage] in kv_cache.hpp) through its typed owner and views
// (h/tron/tensor/k_vnni.hpp). The index map matches hand-computed anchors. The
// per-token store / load operations are exact. The AVX-512 (the
// 512-bit Advanced Vector Extensions) reader of that layout does not differ
// from the row-major dotter. The layout-agnostic page accessors and page copies
// move tokens correctly.
// No AMX (Advanced Matrix Extensions, the tile instruction set) instruction runs
// here. So every case runs on every host. The cases that need a VNNI slot (the
// book-level ones under TRON_K_VNNI) exercise the row-major layout in the other
// build. There they check the same contract.
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
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
  // preset value. Their storage holds NaN (not a number) poison. The check is
  // that dead-token values do not reach live scores.
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
  // Dead-token score slots must retain this preset.
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
