// Precision regression tests for the AMX attention kernels: the AMX QK and
// PV outputs must not digress from the AVX path beyond the documented
// numerics contract (see Note [AMX attention dispatch]): both engines are
// bf16-in/fp32-accumulate, so admissible A/B deltas are ONLY
//   (a) fp32 accumulation order, and
//   (b) for PV, the weight rounding mode - AVX scaled_v truncates
//       fp32->bf16, AMX rounds to nearest even.
// Each check pins a kernel to the AVX side (the real dotter for QK, an
// exactly-rounded weight reference for PV) within an envelope computed from
// the inputs, so any regression outside (a)/(b) - wrong element indexing, a
// dropped token or dim block, a changed accumulation precision - fails.
// The VNNI QK case pins qk_vnni_128x4 to qk_rowmajor_128x4 bit for bit
// instead: the two kernels add the same products in the same order.
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <memory>
#include <random>
#include <utility>
#include <vector>

#include <catch2/catch_test_macros.hpp>

#ifdef TRON_AMX_DISPATCH

#include "common/numerics/bf16.hpp"
#include "common/numerics/fp16.hpp"
#include "tron/kernels/amx_attn_iface.hpp"
#include "tron/kernels/dotter.hpp"
#include "tron/models/common.hpp"
#include "tron/tensor/k_vnni.hpp"
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/seq.hpp"
#include "tron/tensor/v_vnni.hpp"
#include "tron/tensor/view.hpp"

namespace {

// The kernel shape, by the names the interface header gives it.
using tron::amx_attn_h128g4::GROUP_HEADS_4;  // query heads per KV head
using tron::amx_attn_h128g4::HEAD_SIZE_128;
using tron::amx_attn_h128g4::PAGE_TOKENS_64;
using tron::amx_attn_h128g4::TILE_ROWS_16;

// float -> bf16 with RNE, round to nearest even: the closest bf16 value, and
// when the float sits exactly halfway between two bf16 values, the one whose
// last kept bit is 0. This is the rounding the AMX PV kernel applies to the
// weights (VCVTNE2PS2BF16); bf16_trunc below is the AVX path's rounding.
uint16_t bf16_rne(float f) {
  uint32_t bits;
  std::memcpy(&bits, &f, 4);
  bits += 0x7fffu + ((bits >> 16) & 1u);
  return static_cast<uint16_t>(bits >> 16);
}

uint16_t bf16_trunc(float f) {
  uint32_t bits;
  std::memcpy(&bits, &f, 4);
  return static_cast<uint16_t>(bits >> 16);
}

float bf16_to_float(uint16_t b) {
  uint32_t bits = static_cast<uint32_t>(b) << 16;
  float f;
  std::memcpy(&f, &bits, 4);
  return f;
}

// The independent rounding helpers above work on bit patterns; the kernels
// take tron::bf16 objects. from_bits/to_bits move between the two without
// numeric conversion.
struct alignas(64) qk_inputs {
  tron::bf16 k[PAGE_TOKENS_64 * HEAD_SIZE_128];  // row-major, the kv_block K layout
  tron::bf16 q[GROUP_HEADS_4 * HEAD_SIZE_128];   // one GQA group
};

void fill_qk(qk_inputs& in, uint32_t seed) {
  std::mt19937 gen(seed);
  std::uniform_real_distribution<float> u(-1.f, 1.f);
  for (auto& x : in.k) {
    x = tron::bf16::from_bits(bf16_rne(u(gen)));
  }
  for (auto& x : in.q) {
    x = tron::bf16::from_bits(bf16_rne(u(gen)));
  }
}

}  // namespace

TEST_CASE("AMX dispatch is limited to executors that store activations as bf16",
    "[amx_numerics][q_pack]") {
  // The packer copies bf16 values without conversion (pack contract in
  // amx_attn_iface.hpp), so the gate must reject executors whose activations
  // are float (host) or fp16 (host_fp16).
  using tron::amx_attn_h128g4::eligible;
  using tron::amx_attn_h128g4::query_scalar_ok;
  STATIC_REQUIRE(query_scalar_ok<tron::bf16>);
  STATIC_REQUIRE_FALSE(query_scalar_ok<float>);
  STATIC_REQUIRE_FALSE(query_scalar_ok<tron::fp16>);
  // Through the executor aliases the models are built with (common.hpp):
  // hardware::btensor (tp*, host_bf16) holds bf16, tensor (host) holds float,
  // hardware::htensor (host_fp16) holds fp16.
  STATIC_REQUIRE(
      query_scalar_ok<typename tron::tp1::btensor_t<HEAD_SIZE_128>::element>);
  STATIC_REQUIRE(
      query_scalar_ok<typename tron::host_bf16::btensor_t<HEAD_SIZE_128>::element>);
  STATIC_REQUIRE_FALSE(
      query_scalar_ok<typename tron::host::btensor_t<HEAD_SIZE_128>::element>);
  STATIC_REQUIRE_FALSE(
      query_scalar_ok<typename tron::host_fp16::btensor_t<HEAD_SIZE_128>::element>);
  // The whole gate: shape and scalar must both hold.
  STATIC_REQUIRE(eligible<tron::bf16>(HEAD_SIZE_128, GROUP_HEADS_4));
  STATIC_REQUIRE_FALSE(eligible<float>(HEAD_SIZE_128, GROUP_HEADS_4));
  STATIC_REQUIRE_FALSE(eligible<tron::fp16>(HEAD_SIZE_128, GROUP_HEADS_4));
  STATIC_REQUIRE_FALSE(eligible<tron::bf16>(HEAD_SIZE_128, 2));
  STATIC_REQUIRE_FALSE(eligible<tron::bf16>(64, GROUP_HEADS_4));
}

TEST_CASE("AMX Q packer moves bf16 values to the documented positions",
    "[amx_numerics][q_pack]") {
  // Layout contracts of pack_q_group_128x4 and pack_q_rows_128x4
  // (amx_attn_iface.hpp): scalar copies, no AMX instruction runs, so this runs
  // on every host. Distinct bit
  // patterns per element, so a wrong index cannot pass by coincidence; the
  // comparison is on the bit patterns, not on float equality.
  alignas(64) tron::bf16 q[GROUP_HEADS_4 * HEAD_SIZE_128];
  for (size_t i = 0; i < GROUP_HEADS_4 * HEAD_SIZE_128; ++i) {
    q[i] = tron::bf16::from_bits(static_cast<uint16_t>(0x3f80u + i));
  }
  SECTION("VNNI B operand, pack_q_group_128x4") {
    alignas(64) tron::bf16 packed[tron::amx_attn_h128g4::Q_PACK_ELEMS_2048] = {};
    tron::amx_attn_h128g4::pack_q_group_128x4(q, packed);
    for (size_t step = 0; step < HEAD_SIZE_128 / 32; ++step) {
      for (size_t dim_pair = 0; dim_pair < 16; ++dim_pair) {
        for (size_t col = 0; col < 16; ++col) {
          for (size_t j = 0; j < 2; ++j) {
            const uint16_t got =
                packed[((step * 16 + dim_pair) * 16 + col) * 2 + j].to_bits();
            if (col < GROUP_HEADS_4) {
              REQUIRE(got ==
                      q[col * HEAD_SIZE_128 + step * 32 + 2 * dim_pair + j].to_bits());
            } else {
              REQUIRE(got == 0);  // padding columns stay untouched
            }
          }
        }
      }
    }
  }
  SECTION("A operand rows, pack_q_rows_128x4") {
    // The contract is rows 0..3 only, so the padding rows hold a poison pattern,
    // not zero: a packer that wrote them would be caught.
    alignas(64) tron::bf16 padded[tron::amx_attn_h128g4::Q_PACK_ELEMS_2048];
    constexpr uint16_t POISON_0X7F7F = 0x7f7fu;
    for (auto& x : padded) {
      x = tron::bf16::from_bits(POISON_0X7F7F);
    }
    tron::amx_attn_h128g4::pack_q_rows_128x4(q, padded);
    for (size_t row = 0; row < TILE_ROWS_16; ++row) {
      for (size_t dim = 0; dim < HEAD_SIZE_128; ++dim) {
        const uint16_t got = padded[row * HEAD_SIZE_128 + dim].to_bits();
        if (row < GROUP_HEADS_4) {
          REQUIRE(got == q[row * HEAD_SIZE_128 + dim].to_bits());
        } else {
          REQUIRE(got == POISON_0X7F7F);  // padding rows stay untouched
        }
      }
    }
  }
}

TEST_CASE("AMX QK does not digress from the AVX dotter", "[amx_numerics][kv_data]") {
  if (!tron::amx_attn_h128g4::available()) {
    WARN("AMX unavailable on this host - QK precision check skipped");
    return;
  }
  auto in = std::make_unique<qk_inputs>();

  for (uint32_t seed : {11u, 12u, 13u, 14u}) {
    fill_qk(*in, seed);

    alignas(64) tron::bf16 q_packed[tron::amx_attn_h128g4::Q_PACK_ELEMS_2048] = {};
    tron::amx_attn_h128g4::pack_q_group_128x4(in->q, q_packed);
    alignas(64) float s_amx[GROUP_HEADS_4][PAGE_TOKENS_64];
    tron::amx_attn_h128g4::begin_region();
    // The fixture's aligned row-major K block, wrapped explicitly as the whole
    // native K plane the kernel takes.
    tron::amx_attn_h128g4::qk_rowmajor_128x4(
        tron::const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>{in->k}, q_packed,
        &s_amx[0][0], PAGE_TOKENS_64);
    tron::amx_attn_h128g4::end_region();

    for (size_t qi = 0; qi < GROUP_HEADS_4; ++qi) {
      tron::const_view<tron::bf16, true, false, tron::seq<HEAD_SIZE_128>> qv{
          in->q + qi * HEAD_SIZE_128};
      tron::dotter<tron::bf16, HEAD_SIZE_128> dot_q(qv);
      for (size_t t = 0; t < PAGE_TOKENS_64; ++t) {
        tron::const_view<tron::bf16, true, false, tron::seq<HEAD_SIZE_128>> kv{
            in->k + t * HEAD_SIZE_128};
        const float s_avx = dot_q(kv);
        // Both engines sum the same 128 exact bf16xbf16 products in fp32;
        // only the accumulation order differs. Envelope: 1e-4 of the
        // absolute-product mass (about 840 times fp32 epsilon, 1.2e-7) plus
        // 1e-6, a fixed relative bound with room for any summation order.
        double abs_mass = 0;
        for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
          abs_mass +=
              std::fabs(double(bf16_to_float(in->q[qi * HEAD_SIZE_128 + d].to_bits())) *
                        double(bf16_to_float(in->k[t * HEAD_SIZE_128 + d].to_bits())));
        }
        const double tol = 1e-4 * abs_mass + 1e-6;
        REQUIRE(std::fabs(double(s_amx[qi][t]) - double(s_avx)) <= tol);
      }
    }
  }
}

TEST_CASE("AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K",
    "[amx_numerics][kv_data]") {
  // A and B are the left and right matrices of the AMX tile multiply (Note [QK
  // orientation] in amx_attn_iface.hpp). qk_vnni_128x4 reads K as the B operand
  // and Q as the A operand. qk_rowmajor_128x4 reads K as the A operand and Q as
  // the B operand. Both add the same four 32-dimension partial dot products in
  // the same order (steps 0 to 3 into one zeroed accumulator), and inside one
  // tile multiply (TDPBF16PS) each score element is the same dot product of 16
  // dimension pairs whichever operand holds K. So the scores must match bit for
  // bit. This case checks that the K store (store_row into a k_vnni_tensor) and
  // the kernel's panel addressing reproduce the row-major kernel's scores. A
  // panel is one 16-token x 32-dimension block of the K plane
  // (h/tron/tensor/k_vnni.hpp). A wrong panel or a wrong dimension pair (two
  // adjacent dimensions stored as one 32-bit dword) would not reproduce them.
  if (!tron::amx_attn_h128g4::available()) {
    WARN("AMX unavailable on this host - VNNI QK identity check skipped");
    return;
  }
  constexpr uint32_t SEED_A_21 = 21u;
  constexpr uint32_t SEED_B_22 = 22u;
  // Scrambled store order: tok = (i * stride + offset) % 64 visits every token
  // exactly once. The stride is odd. So it is coprime with 64 (no common
  // factor with 64 other than 1).
  constexpr size_t SCRAMBLE_STRIDE_37 = 37;
  constexpr size_t SCRAMBLE_OFFSET_11 = 11;
  auto in = std::make_unique<qk_inputs>();
  // The packed K owner, filled through the typed store like the cache does.
  auto k_owner = std::make_unique<tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>();
  for (uint32_t seed : {SEED_A_21, SEED_B_22}) {
    fill_qk(*in, seed);
    for (size_t i = 0; i < PAGE_TOKENS_64; ++i) {  // scrambled store order
      const size_t tok = (i * SCRAMBLE_STRIDE_37 + SCRAMBLE_OFFSET_11) % PAGE_TOKENS_64;
      tron::store_row(k_owner->as_view(), tok,
          tron::k_source_row<HEAD_SIZE_128>(in->k + tok * HEAD_SIZE_128));
    }
    alignas(64) tron::bf16 q_packed[tron::amx_attn_h128g4::Q_PACK_ELEMS_2048] = {};
    alignas(64) tron::bf16 q_rows[tron::amx_attn_h128g4::Q_PACK_ELEMS_2048] = {};
    tron::amx_attn_h128g4::pack_q_group_128x4(in->q, q_packed);
    tron::amx_attn_h128g4::pack_q_rows_128x4(in->q, q_rows);
    // Different fill patterns: an element a kernel fails to write cannot match.
    alignas(64) float s_row[GROUP_HEADS_4][PAGE_TOKENS_64] = {};
    alignas(64) float s_vnni[GROUP_HEADS_4][PAGE_TOKENS_64];
    std::memset(s_vnni, 0xff, sizeof(s_vnni));
    tron::amx_attn_h128g4::begin_region();
    tron::amx_attn_h128g4::qk_rowmajor_128x4(
        tron::const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>{in->k}, q_packed,
        &s_row[0][0], PAGE_TOKENS_64);
    tron::amx_attn_h128g4::qk_vnni_128x4(
        std::as_const(*k_owner).as_view(), q_rows, &s_vnni[0][0], PAGE_TOKENS_64);
    tron::amx_attn_h128g4::end_region();
    for (size_t qi = 0; qi < GROUP_HEADS_4; ++qi) {
      for (size_t t = 0; t < PAGE_TOKENS_64; ++t) {
        uint32_t a, b;
        std::memcpy(&a, &s_row[qi][t], sizeof(a));
        std::memcpy(&b, &s_vnni[qi][t], sizeof(b));
        CAPTURE(seed, qi, t, s_row[qi][t], s_vnni[qi][t]);
        REQUIRE(a == b);
      }
    }
  }
}

TEST_CASE(
    "AMX PV stays inside the AVX weight-rounding envelope", "[amx_numerics][kv_data]") {
  if (!tron::amx_attn_h128g4::available()) {
    WARN("AMX unavailable on this host - PV precision check skipped");
    return;
  }
  std::mt19937 gen(31);
  std::uniform_real_distribution<float> uv(-1.f, 1.f);
  std::uniform_real_distribution<float> ue(-10.f, 0.f);

  // Logical V[token][dim], and the pair-interleaved storage the kernel
  // consumes as-is, by the independent formula
  //   storage[(pair * HEAD_SIZE_128 + d) * 2 + j] = V[2*pair + j][d].
  // v_page is the reference for both the physical layout and the numerics.
  std::vector<float> v(PAGE_TOKENS_64 * HEAD_SIZE_128);
  for (auto& x : v) {
    x = uv(gen);
  }
  std::vector<tron::bf16> v_page(PAGE_TOKENS_64 * HEAD_SIZE_128);
  for (size_t pair = 0; pair < PAGE_TOKENS_64 / 2; ++pair) {
    for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
      for (size_t j = 0; j < 2; ++j) {
        v_page[(pair * HEAD_SIZE_128 + d) * 2 + j] =
            tron::bf16::from_bits(bf16_rne(v[(2 * pair + j) * HEAD_SIZE_128 + d]));
      }
    }
  }
  // The kernel input is a real packed V owner (v_vnni_tensor), filled through
  // the public typed write path: one aligned bf16 row per token, appended in
  // order (append_v_row). The owner is 16 KiB with 64-byte alignment, so it
  // lives on the heap (the aligned operator new honors alignas(64)). The
  // layout formula itself is checked in t_llama_unit ("append_v_row matches
  // the independent packed-V formula"), which needs no AMX.
  auto v_owner = std::make_unique<tron::v_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>();
  for (size_t t = 0; t < PAGE_TOKENS_64; ++t) {
    alignas(tron::chunk_alignment) tron::bf16 row[HEAD_SIZE_128];
    for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
      row[d] = tron::bf16::from_bits(bf16_rne(v[t * HEAD_SIZE_128 + d]));
    }
    tron::append_v_row(v_owner->as_view(), t, tron::v_source_row<HEAD_SIZE_128>(row));
  }
  // Weight rows shaped like the per-page softmax update's exp() output:
  // positives in (0,1] spanning ~4 decades, so RNE-vs-truncation deltas
  // are actually exercised.
  alignas(64) float exp_rows[GROUP_HEADS_4][PAGE_TOKENS_64];
  for (auto& row : exp_rows) {
    for (auto& x : row) {
      x = std::exp(ue(gen));
    }
  }

  alignas(64) float
      o_amx[TILE_ROWS_16 * HEAD_SIZE_128];  // See Note [Tile stores write 16 rows]
  tron::amx_attn_h128g4::begin_region();
  tron::amx_attn_h128g4::weights_times_v_128x4(
      v_owner->as_view(), &exp_rows[0][0], PAGE_TOKENS_64, o_amx);
  tron::amx_attn_h128g4::end_region();

  double total_rounding_gap = 0;
  for (size_t qi = 0; qi < GROUP_HEADS_4; ++qi) {
    for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
      double ref_rne = 0, ref_avx = 0, abs_mass = 0, envelope = 0;
      for (size_t t = 0; t < PAGE_TOKENS_64; ++t) {
        const double p = exp_rows[qi][t];
        const double p_rne = bf16_to_float(bf16_rne(float(p)));
        const double p_avx = bf16_to_float(bf16_trunc(float(p)));
        const double vv =
            bf16_to_float(v_page[((t / 2) * HEAD_SIZE_128 + d) * 2 + t % 2].to_bits());
        ref_rne += p_rne * vv;
        ref_avx += p_avx * vv;
        abs_mass += std::fabs(p_rne * vv);
        envelope += std::fabs(p_rne - p_avx) * std::fabs(vv);
      }
      const double acc_slack = 1e-4 * abs_mass + 1e-6;
      const double got = o_amx[qi * HEAD_SIZE_128 + d];
      // (1) Kernel correctness: matches its own (RNE-weight) exact reference
      //     up to fp32 accumulation order.
      REQUIRE(std::fabs(got - ref_rne) <= acc_slack);
      // (2) Non-digression from AVX: within the exact per-element
      //     RNE-vs-truncation envelope of the AVX-weight reference.
      REQUIRE(std::fabs(got - ref_avx) <= envelope + acc_slack);
      total_rounding_gap += envelope;
    }
  }
  // The envelope must be non-trivial, or (2) would be vacuously equal to (1).
  REQUIRE(total_rounding_gap > 0.0);
}

#else  // !TRON_AMX_DISPATCH

TEST_CASE("AMX numerics tests skipped (dispatch not compiled)", "[amx_numerics]") {
  SUCCEED("build without TRON_AMX_DISPATCH - nothing to test");
}

#endif
