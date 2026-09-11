// Standalone local feasibility proof, not a production Tron implementation.
// Layout and canonical dotter arithmetic transcribed from PR3879 head
// 60d66d9c04428d907069ced375b93265add02db7. No Tron headers required:
// the installed GCC 11 does not support Tron's scalar __bf16 type.
#include <immintrin.h>
#include <sys/mman.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <numeric>
#include <random>

#define AVX512 __attribute__((target("avx512f,avx512dq,avx512bw,avx512vl,fma")))
#define BF16 __attribute__((target("avx512f,avx512dq,avx512bw,avx512vl,avx512bf16,fma")))
#define NOINLINE __attribute__((noinline))

constexpr size_t P = 64, D = 128;
using Page = std::array<uint16_t, P * D>;
using Q16 = std::array<uint16_t, D>;
using Q32 = std::array<float, D>;
using Scores = std::array<float, P>;

float fp32(uint16_t b) { return std::bit_cast<float>(uint32_t(b) << 16); }
uint16_t bf16_rne(float x) {
  uint32_t u = std::bit_cast<uint32_t>(x);
  return uint16_t((u + 0x7fff + ((u >> 16) & 1)) >> 16);
}

// Exact scatter_k_mirror<P,D> index from kv_cache.hpp:652.
size_t mirror_index(size_t token, size_t dim) {
  const size_t s = dim / 32, c = token / 16;
  const size_t dp = (dim % 32) / 2, t = token % 16, j = dim % 2;
  return (((s * (P / 16) + c) * 16 + dp) * 16 + t) * 2 + j;
}

uint16_t block_mask(uint64_t live, size_t block) {
  return uint16_t(live >> (block * 16));
}

AVX512 NOINLINE __m512i masked_pairs(const void* ptr, __mmask16 live) {
  // One 32-bit mask lane covers BOTH BF16 dimensions of one token.
  // Masked-off lanes do not access memory; no page zero-fill is required.
  return _mm512_maskz_loadu_epi32(live, ptr);
}

BF16 NOINLINE void swizzled_bf16(
    const uint16_t* k, const uint16_t* q, uint64_t live, float* out) {
  const __m512 neginf = _mm512_set1_ps(-INFINITY);
  for (size_t c = 0; c < P / 16; ++c) {
    const __mmask16 mask = block_mask(live, c);
    if (!mask) {
      _mm512_storeu_ps(out + c * 16, neginf);
      continue;
    }
    __m512 acc[4] = {_mm512_setzero_ps(), _mm512_setzero_ps(),
        _mm512_setzero_ps(), _mm512_setzero_ps()};
    for (size_t dp = 0; dp < 16; ++dp) {
      for (size_t s = 0; s < 4; ++s) {
        const size_t d = s * 32 + dp * 2;
        uint32_t qp;
        std::memcpy(&qp, q + d, sizeof(qp));
        const __m512bh qb = (__m512bh)_mm512_set1_epi32(qp);
        const uint16_t* row = k + ((s * 4 + c) * 16 + dp) * 32;
        // Inline the same masked load exercised by the guard-page test.
        const __m512bh kb = (__m512bh)_mm512_maskz_loadu_epi32(mask, row);
        acc[s] = _mm512_dpbf16_ps(acc[s], qb, kb);
      }
    }
    __m512 sum = _mm512_add_ps(_mm512_add_ps(acc[0], acc[2]),
        _mm512_add_ps(acc[1], acc[3]));
    _mm512_storeu_ps(out + c * 16, _mm512_mask_mov_ps(neginf, mask, sum));
  }
}

AVX512 NOINLINE void swizzled_fp32(
    const uint16_t* k, const float* q, uint64_t live, float* out) {
  const __m512 neginf = _mm512_set1_ps(-INFINITY);
  for (size_t c = 0; c < P / 16; ++c) {
    const __mmask16 mask = block_mask(live, c);
    if (!mask) {
      _mm512_storeu_ps(out + c * 16, neginf);
      continue;
    }
    __m512 acc[4] = {_mm512_setzero_ps(), _mm512_setzero_ps(),
        _mm512_setzero_ps(), _mm512_setzero_ps()};
    for (size_t dp = 0; dp < 16; ++dp) {
      for (size_t s = 0; s < 4; ++s) {
        const size_t d = s * 32 + dp * 2;
        const uint16_t* row = k + ((s * 4 + c) * 16 + dp) * 32;
        const __m512i bits = _mm512_maskz_loadu_epi32(mask, row);
        const __m512 even = _mm512_castsi512_ps(_mm512_slli_epi32(bits, 16));
        const __m512 odd = _mm512_castsi512_ps(
            _mm512_and_si512(bits, _mm512_set1_epi32(0xffff0000)));
        acc[s] = _mm512_fmadd_ps(_mm512_set1_ps(q[d]), even, acc[s]);
        acc[s] = _mm512_fmadd_ps(_mm512_set1_ps(q[d + 1]), odd, acc[s]);
      }
    }
    __m512 sum = _mm512_add_ps(_mm512_add_ps(acc[0], acc[2]),
        _mm512_add_ps(acc[1], acc[3]));
    _mm512_storeu_ps(out + c * 16, _mm512_mask_mov_ps(neginf, mask, sum));
  }
}

NOINLINE void swizzled_avx2(
    const uint16_t* k, const float* q, uint64_t live, float* out) {
  const __m256 neginf = _mm256_set1_ps(-INFINITY);
  for (size_t block = 0; block < P / 8; ++block) {
    const uint8_t live8 = uint8_t(live >> (block * 8));
    if (!live8) {
      _mm256_storeu_ps(out + block * 8, neginf);
      continue;
    }
    alignas(32) int32_t lanes[8];
    for (size_t i = 0; i < 8; ++i) lanes[i] = (live8 >> i) & 1 ? -1 : 0;
    const __m256i mask = _mm256_load_si256((const __m256i*)lanes);
    __m256 acc[4] = {_mm256_setzero_ps(), _mm256_setzero_ps(),
        _mm256_setzero_ps(), _mm256_setzero_ps()};
    for (size_t dp = 0; dp < 16; ++dp) {
      for (size_t s = 0; s < 4; ++s) {
        const size_t d = s * 32 + dp * 2;
        const uint16_t* row = k + ((s * 4 + block / 2) * 16 + dp) * 32
            + (block % 2) * 16;
        const __m256i bits = _mm256_maskload_epi32((const int*)row, mask);
        const __m256 even = _mm256_castsi256_ps(_mm256_slli_epi32(bits, 16));
        const __m256 odd = _mm256_castsi256_ps(
            _mm256_and_si256(bits, _mm256_set1_epi32(0xffff0000)));
        acc[s] = _mm256_fmadd_ps(_mm256_set1_ps(q[d]), even, acc[s]);
        acc[s] = _mm256_fmadd_ps(_mm256_set1_ps(q[d + 1]), odd, acc[s]);
      }
    }
    const __m256 sum = _mm256_add_ps(_mm256_add_ps(acc[0], acc[2]),
        _mm256_add_ps(acc[1], acc[3]));
    _mm256_storeu_ps(out + block * 8,
        _mm256_blendv_ps(neginf, sum, _mm256_castsi256_ps(mask)));
  }
}

// Intrinsic-level reproductions of dotter<bf16,128> and dotter<float,128>.
// They use its accumulation and _mm512_reduce_add_ps order, but are not linked
// Tron kernels and omit tensor/view wrappers. Q is prepared once per page.
BF16 NOINLINE void canonical_bf16(
    const uint16_t* k, const uint16_t* q, uint64_t live, float* out) {
  const __m512bh q0 = (__m512bh)_mm512_loadu_si512(q);
  const __m512bh q1 = (__m512bh)_mm512_loadu_si512(q + 32);
  const __m512bh q2 = (__m512bh)_mm512_loadu_si512(q + 64);
  const __m512bh q3 = (__m512bh)_mm512_loadu_si512(q + 96);
  for (size_t t = 0; t < P; ++t) {
    out[t] = -INFINITY;
    if (!((live >> t) & 1)) continue;
    const uint16_t* row = k + t * D;
    __m512 a = _mm512_dpbf16_ps(_mm512_setzero_ps(), q0,
        (__m512bh)_mm512_loadu_si512(row));
    __m512 b = _mm512_dpbf16_ps(_mm512_setzero_ps(), q1,
        (__m512bh)_mm512_loadu_si512(row + 32));
    a = _mm512_dpbf16_ps(a, q2, (__m512bh)_mm512_loadu_si512(row + 64));
    b = _mm512_dpbf16_ps(b, q3, (__m512bh)_mm512_loadu_si512(row + 96));
    out[t] = _mm512_reduce_add_ps(_mm512_add_ps(a, b));
  }
}

AVX512 __m512 load_bf16x16(const uint16_t* p) {
  return _mm512_castsi512_ps(_mm512_slli_epi32(
      _mm512_cvtepu16_epi32(_mm256_loadu_si256((const __m256i*)p)), 16));
}

AVX512 NOINLINE void canonical_fp32(
    const uint16_t* k, const float* q, uint64_t live, float* out) {
  __m512 qs[8];
  for (size_t i = 0; i < 8; ++i) qs[i] = _mm512_loadu_ps(q + i * 16);
  for (size_t t = 0; t < P; ++t) {
    out[t] = -INFINITY;
    if (!((live >> t) & 1)) continue;
    const uint16_t* row = k + t * D;
    __m512 a = _mm512_mul_ps(qs[0], load_bf16x16(row));
    __m512 b = _mm512_mul_ps(qs[1], load_bf16x16(row + 16));
    for (size_t i = 2; i < 8; i += 2) {
      a = _mm512_fmadd_ps(qs[i], load_bf16x16(row + i * 16), a);
      b = _mm512_fmadd_ps(qs[i + 1], load_bf16x16(row + (i + 1) * 16), b);
    }
    out[t] = _mm512_reduce_add_ps(_mm512_add_ps(a, b));
  }
}

struct Stats {
  const char* name;
  size_t checked = 0, bitwise_different = 0;
  double max_abs = 0, max_scaled = 0, max_vs_dotter = 0;
  void check(double ref, double scale, float got, float dotter) {
    if (!std::isfinite(got) || std::abs(ref - got) > 1e-6 + 8e-6 * scale) {
      std::fprintf(stderr, "FAIL %s ref=%.12g got=%.12g scale=%.12g\n",
          name, ref, double(got), scale);
      std::exit(1);
    }
    ++checked;
    bitwise_different += std::bit_cast<uint32_t>(got) !=
        std::bit_cast<uint32_t>(dotter);
    max_abs = std::max(max_abs, std::abs(ref - got));
    max_scaled = std::max(max_scaled, std::abs(ref - got) / std::max(1.0, scale));
    max_vs_dotter = std::max(max_vs_dotter, double(std::abs(got - dotter)));
  }
  void print() const {
    std::printf("%s checked=%zu max_abs_vs_fp64=%.9g "
                "max_abs/sum_abs=%.9g max_abs_vs_dotter=%.9g "
                "different_bits_vs_dotter=%zu\n",
        name, checked, max_abs, max_scaled, max_vs_dotter, bitwise_different);
  }
};

void require(bool ok, const char* msg) {
  if (!ok) { std::fprintf(stderr, "FAIL %s\n", msg); std::exit(1); }
}

AVX512 void guard_test() {
  const size_t bytes = size_t(sysconf(_SC_PAGESIZE));
  void* p = mmap(nullptr, bytes * 2, PROT_READ | PROT_WRITE,
      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  require(p != MAP_FAILED, "mmap");
  require(mprotect((char*)p + bytes, bytes, PROT_NONE) == 0, "mprotect");
  for (unsigned n = 0; n <= 16; ++n) {
    uint32_t* row = (uint32_t*)((char*)p + bytes) - n;
    for (unsigned i = 0; i < n; ++i) row[i] = 0x3f803f80;
    const __mmask16 mask = n == 16 ? 0xffff : ((1u << n) - 1);
    alignas(64) uint32_t result[16];
    _mm512_store_si512(result, masked_pairs(row, mask));
    for (unsigned i = 0; i < 16; ++i)
      require(result[i] == (i < n ? 0x3f803f80u : 0u), "guard mask result");
  }
  munmap(p, bytes * 2);
  std::puts("guard_page: all 17 prefix masks PASS; masked lanes cross PROT_NONE");
}

volatile float sink;
template <typename Fn, typename Q>
double ns_per_page(Fn fn, const Page& page, const Q& query, uint64_t live) {
  Scores scores;
  constexpr size_t iterations = 6000, repeats = 7;
  std::array<double, repeats> times;
  for (size_t repeat = 0; repeat < repeats; ++repeat) {
    auto start = std::chrono::steady_clock::now();
    for (size_t i = 0; i < iterations; ++i) {
      fn(page.data(), query.data(), live, scores.data());
      asm volatile("" : : "m"(scores) : "memory");
    }
    auto stop = std::chrono::steady_clock::now();
    sink = scores[0];
    times[repeat] = std::chrono::duration<double, std::nano>(stop - start).count()
        / iterations;
  }
  std::sort(times.begin(), times.end());
  return times[repeats / 2];
}

int main(int argc, char**) {
  require(__builtin_cpu_supports("avx512bf16"), "CPU requires AVX512_BF16");
  std::printf("Standalone QK proof: P=%zu D=%zu MXCSR=0x%x seed=3879\n",
      P, D, _mm_getcsr());
  Page canonical, swizzled;
  Q16 q16;
  Q32 q32, q16_as32;
  std::mt19937 rng(3879);
  std::normal_distribution<float> normal(0.0f, 1.0f);
  Stats b{"AVX512_BF16"}, f{"AVX512_FP32_Q"}, a{"AVX2_FP32_Q"};
  size_t mask_cases = 0;
  for (size_t trial = 0; trial < 24; ++trial) {
    for (size_t d = 0; d < D; ++d) {
      q32[d] = std::ldexp(normal(rng), int(rng() % 7) - 3);
      q16[d] = bf16_rne(q32[d]);
      q16_as32[d] = fp32(q16[d]);
    }
    for (auto& x : canonical) x = bf16_rne(
        std::ldexp(normal(rng), int(rng() % 7) - 3));
    // All 65 page prefixes plus 64 arbitrary masks; inactive token storage
    // is NaN poison. A shuffled scatter also tests token write independence.
    for (size_t mc = 0; mc < 129; ++mc) {
      const uint64_t live = mc < 64 ? ((uint64_t(1) << mc) - 1)
          : mc == 64 ? ~uint64_t(0) : ((uint64_t(rng()) << 32) | rng());
      swizzled.fill(0x7fc1);
      std::array<size_t, P> order;
      std::iota(order.begin(), order.end(), 0);
      std::shuffle(order.begin(), order.end(), rng);
      for (size_t t : order) {
        if (!((live >> t) & 1)) continue;
        for (size_t d = 0; d < D; ++d)
          swizzled[mirror_index(t, d)] = canonical[t * D + d];
      }
      Scores bs, fs, as, bc, fc;
      swizzled_bf16(swizzled.data(), q16.data(), live, bs.data());
      swizzled_fp32(swizzled.data(), q32.data(), live, fs.data());
      swizzled_avx2(swizzled.data(), q32.data(), live, as.data());
      canonical_bf16(canonical.data(), q16.data(), live, bc.data());
      canonical_fp32(canonical.data(), q32.data(), live, fc.data());
      for (size_t t = 0; t < P; ++t) {
        if (!((live >> t) & 1)) {
          require(bs[t] == -INFINITY && fs[t] == -INFINITY && as[t] == -INFINITY,
              "inactive score must remain negative infinity");
          continue;
        }
        double rb = 0, rf = 0, sb = 0, sf = 0;
        for (size_t d = 0; d < D; ++d) {
          const double kval = fp32(canonical[t * D + d]);
          const double pb = double(q16_as32[d]) * kval;
          const double pf = double(q32[d]) * kval;
          rb += pb; rf += pf; sb += std::abs(pb); sf += std::abs(pf);
        }
        b.check(rb, sb, bs[t], bc[t]);
        f.check(rf, sf, fs[t], fc[t]);
        a.check(rf, sf, as[t], fc[t]);
      }
      ++mask_cases;
    }
  }
  std::printf("correctness: %zu page-mask cases PASS (finite normal inputs)\n",
      mask_cases);
  b.print(); f.print(); a.print();
  guard_test();

  // ISA behavior probe: BF16 dot instructions treat BF16 subnormals as zero;
  // FP32 FMA behavior depends on MXCSR. This is intentionally not equality.
  canonical.fill(0); swizzled.fill(0); q16.fill(0); q32.fill(0);
  canonical[0] = swizzled[mirror_index(0, 0)] = 0x0001;
  q16[0] = 0x3f80; q32[0] = 1.0f;
  Scores bs, fs;
  swizzled_bf16(swizzled.data(), q16.data(), 1, bs.data());
  swizzled_fp32(swizzled.data(), q32.data(), 1, fs.data());
  std::printf("subnormal probe: bf16_dp=%.9g fp32_fma=%.9g scalar=%.9g\n",
      double(bs[0]), double(fs[0]), double(fp32(0x0001)));

  if (argc > 1) return 0;  // --correctness-only
  for (size_t d = 0; d < D; ++d) {
    q32[d] = normal(rng); q16[d] = bf16_rne(q32[d]);
  }
  for (size_t t = 0; t < P; ++t)
    for (size_t d = 0; d < D; ++d)
      swizzled[mirror_index(t, d)] = canonical[t * D + d] = bf16_rne(normal(rng));
  std::puts("hot-page single-query microbench: median of 7 x 6000 calls, ns/page");
  std::puts("visible,canonical_bf16,swizzled_bf16,canonical_fp32,swizzled_fp32,avx2_fp32");
  for (unsigned visible : {1, 3, 8, 15, 16, 17, 32, 63, 64}) {
    const uint64_t live = visible == 64 ? ~uint64_t(0)
        : ((uint64_t(1) << visible) - 1);
    std::printf("%u,%.2f,%.2f,%.2f,%.2f,%.2f\n", visible,
        ns_per_page(canonical_bf16, canonical, q16, live),
        ns_per_page(swizzled_bf16, swizzled, q16, live),
        ns_per_page(canonical_fp32, canonical, q32, live),
        ns_per_page(swizzled_fp32, swizzled, q32, live),
        ns_per_page(swizzled_avx2, swizzled, q32, live));
  }
  return 0;
}
