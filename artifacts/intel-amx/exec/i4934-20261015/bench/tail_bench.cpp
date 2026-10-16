// tail_bench: micro-benchmark of the ways to score the row-major tail rows of
// one K block (Note [Row-major tail block] in h/tron/tensor/k_vnni.hpp) against
// one query group, on one core.
//
// Arms (what scores block 3 of a 64-token page, n live tokens, kv_mul heads):
//   dotter  the fix's path (self_attention.hpp): kv_mul dotters built per visit,
//           one row at a time through row_major_row.
//   reader  PR #4898's path: the block holds the VNNI layout, k_vnni::qk_group
//           scores the live tokens with masked 64-byte loads.
//   rowbat  candidate: one 256-byte row loaded once, VDPBF16PS into kv_mul
//           accumulators, one horizontal reduce per (row, head).
//   xpose   candidate: the live rows transposed in registers (the 16x16 dword
//           transpose of store_block) and scored like the reader, no memory
//           write, one lane per token.
//   tmpblk  candidate: store_block into a thread-local plane, then qk_group.
// Scenarios (where the block's lines are when the visit starts):
//   hot      in this core's L1 (the same visit repeated).
//   step     one decode step: another core writes the newest token (row-major
//            store for the row arms, the per-token scatter store_row for the
//            reader arm), this core's L1/L2 copies of the rest are evicted
//            by a 4 MiB walk, so they come from L3.
//   alldirty another core writes all n live tokens right before the visit.
//   flush    the block's 64 lines are flushed to memory (clflushopt) first.
// Output: CSV lines "scenario,arm,kv_mul,n,iters,median_ns,p10_ns,p90_ns,mean_ns"
// after one block of correctness lines "check,arm,kv_mul,n,max_rel_err".
// Usage: tail_bench <reader_cpu> <writer_cpu> [iters_hot] [iters_cold]

#include <immintrin.h>
#include <sched.h>
#include <x86intrin.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <thread>
#include <utility>
#include <vector>

#include "tron/kernels/dotter.hpp"
#include "tron/kernels/k_vnni.hpp"
#include "tron/tensor/k_vnni.hpp"

namespace {

using tron::bf16;
using tron::k_vnni::BLOCK_TOKENS_16;
using tron::k_vnni::HEAD_SIZE_128;
using tron::k_vnni::PAGE_TOKENS_64;
using plane_t = tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>;
using cview_t = tron::k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>;
using view_t = tron::k_vnni_view<bf16, PAGE_TOKENS_64, HEAD_SIZE_128>;

constexpr size_t BLOCK_C = 3;  // the page's last block: the tail block in decode
constexpr size_t FIRST_TOKEN = BLOCK_C * BLOCK_TOKENS_16;
constexpr size_t S_STRIDE = PAGE_TOKENS_64;
constexpr size_t EVICT_BYTES = 4u << 20;  // > the 2 MiB L2 of one Granite Rapids core

struct alignas(64) rows_t {
  bf16 row[BLOCK_TOKENS_16][HEAD_SIZE_128];
};

// ---------------------------------------------------------------- the arms

template <size_t KV_MUL>
struct arms {
  // The fix's path: dotters per visit, one row at a time.
  static void dotter_path(cview_t plane, const bf16* q, uint64_t live, float* s) {
    auto dots = [&]<size_t... I>(std::index_sequence<I...>) {
      return std::array{tron::dotter<bf16, HEAD_SIZE_128>(
          tron::k_source_row<HEAD_SIZE_128>(q + I * HEAD_SIZE_128))...};
    }(std::make_index_sequence<KV_MUL>{});
    for (uint64_t rows = live; rows != 0; rows &= rows - 1) {
      const size_t i = static_cast<size_t>(std::countr_zero(rows));
      const auto k = tron::row_major_row(plane, i);
      for (size_t h = 0; h < KV_MUL; ++h) {
        s[h * S_STRIDE + i] = dots[h](k);
      }
    }
  }

  // PR #4898's path: the block is VNNI, the AVX-512 reader scores it.
  static void reader_path(cview_t plane, const bf16* q, uint64_t live, float* s) {
    tron::k_vnni::qk_group<KV_MUL>(plane, q, live, s, S_STRIDE);
  }

  // Candidate: load a row once, VDPBF16PS into KV_MUL accumulator pairs.
  static void rowbat_path(cview_t plane, const bf16* q, uint64_t live, float* s) {
    __m512i xq[KV_MUL][4];
    for (size_t h = 0; h < KV_MUL; ++h) {
      for (size_t j = 0; j < 4; ++j) {
        xq[h][j] = _mm512_load_si512(q + h * HEAD_SIZE_128 + j * 32);
      }
    }
    for (uint64_t rows = live; rows != 0; rows &= rows - 1) {
      const size_t i = static_cast<size_t>(std::countr_zero(rows));
      const bf16* const k = tron::row_major_row(plane, i).data;
      const __m512i y0 = _mm512_load_si512(k + 0);
      const __m512i y1 = _mm512_load_si512(k + 32);
      const __m512i y2 = _mm512_load_si512(k + 64);
      const __m512i y3 = _mm512_load_si512(k + 96);
      for (size_t h = 0; h < KV_MUL; ++h) {
        __m512 sum1 = _mm512_dpbf16_ps(_mm512_setzero_ps(), (__m512bh)xq[h][0], (__m512bh)y0);
        __m512 sum2 = _mm512_dpbf16_ps(_mm512_setzero_ps(), (__m512bh)xq[h][1], (__m512bh)y1);
        sum1 = _mm512_dpbf16_ps(sum1, (__m512bh)xq[h][2], (__m512bh)y2);
        sum2 = _mm512_dpbf16_ps(sum2, (__m512bh)xq[h][3], (__m512bh)y3);
        s[h * S_STRIDE + i] = _mm512_reduce_add_ps(_mm512_add_ps(sum1, sum2));
      }
    }
  }

  // Candidate: transpose the live rows in registers, then score one lane per
  // token like the reader. Nothing is written to memory but the scores.
  static void xpose_path(cview_t plane, const bf16* q, uint64_t live, float* s) {
    const __mmask16 mask = __mmask16(live >> FIRST_TOKEN);
    const bf16* rowp[BLOCK_TOKENS_16];
    for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
      rowp[t] = ((mask >> t) & 1u) ? tron::row_major_row(plane, FIRST_TOKEN + t).data
                                   : nullptr;
    }
    __m512 acc[KV_MUL];
    for (size_t h = 0; h < KV_MUL; ++h) acc[h] = _mm512_setzero_ps();
    for (size_t step = 0; step < tron::k_vnni::DIM_STEPS_4; ++step) {
      __m512i r[BLOCK_TOKENS_16];
      for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
        r[t] = rowp[t] ? _mm512_load_si512(rowp[t] + step * tron::k_vnni::STEP_DIMS_32)
                       : _mm512_setzero_si512();
      }
      tron::k_vnni::detail::transpose_16x16_epi32(r);
      for (size_t dp = 0; dp < tron::k_vnni::STEP_PAIRS_16; ++dp) {
        const size_t d = step * tron::k_vnni::STEP_DIMS_32 + 2 * dp;
        for (size_t h = 0; h < KV_MUL; ++h) {
          uint32_t q_pair;
          std::memcpy(&q_pair, q + h * HEAD_SIZE_128 + d, sizeof(q_pair));
          acc[h] = _mm512_dpbf16_ps(
              acc[h], (__m512bh)_mm512_set1_epi32(int(q_pair)), (__m512bh)r[dp]);
        }
      }
    }
    for (size_t h = 0; h < KV_MUL; ++h) {
      _mm512_mask_storeu_ps(s + h * S_STRIDE + FIRST_TOKEN, mask, acc[h]);
    }
  }

  // Candidate: pack the live rows into a thread-local VNNI block, then the reader.
  static void tmpblk_path(cview_t plane, const bf16* q, uint64_t live, float* s) {
    thread_local plane_t tmp;
    const __mmask16 mask = __mmask16(live >> FIRST_TOKEN);
    const bf16* rowp[BLOCK_TOKENS_16];
    for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
      rowp[t] = ((mask >> t) & 1u) ? tron::row_major_row(plane, FIRST_TOKEN + t).data
                                   : nullptr;
    }
    tron::store_block(tmp.as_view(), BLOCK_C, mask, rowp);
    tron::k_vnni::qk_group<KV_MUL>(std::as_const(tmp).as_view(), q, live, s, S_STRIDE);
  }
};

using path_fn = void (*)(cview_t, const bf16*, uint64_t, float*);

struct arm_t {
  const char* name;
  bool vnni_layout;  // the block holds the VNNI layout (reader) or row-major rows
  path_fn fn4, fn8;
};

const arm_t ARMS[] = {
    {"dotter", false, &arms<4>::dotter_path, &arms<8>::dotter_path},
    {"reader", true, &arms<4>::reader_path, &arms<8>::reader_path},
    {"rowbat", false, &arms<4>::rowbat_path, &arms<8>::rowbat_path},
    {"xpose", false, &arms<4>::xpose_path, &arms<8>::xpose_path},
    {"tmpblk", false, &arms<4>::tmpblk_path, &arms<8>::tmpblk_path},
};

// ---------------------------------------------------------------- the writer

// The other core: writes tokens on request, as the main thread's Save K does.
struct writer_t {
  std::atomic<int> phase{0};  // 0 idle, 1 requested, 2 done, -1 stop
  std::atomic<uint64_t> tokens{0};
  std::atomic<bool> vnni{false};
  plane_t* plane = nullptr;
  const rows_t* rows = nullptr;

  void run(int cpu) {
    pin(cpu);
    for (;;) {
      int p;
      while ((p = phase.load(std::memory_order_acquire)) == 0 || p == 2) _mm_pause();
      if (p < 0) return;
      const uint64_t toks = tokens.load(std::memory_order_relaxed);
      const bool v = vnni.load(std::memory_order_relaxed);
      for (uint64_t m = toks; m != 0; m &= m - 1) {
        const size_t tok = static_cast<size_t>(std::countr_zero(m));
        const auto src = tron::k_source_row<HEAD_SIZE_128>(rows->row[tok - FIRST_TOKEN]);
        if (v) {
          tron::store_row(plane->as_view(), tok, src);
        } else {
          tron::store_row_major(plane->as_view(), tok, src);
        }
      }
      _mm_sfence();
      phase.store(2, std::memory_order_release);
    }
  }

  void write(uint64_t toks, bool v) {
    tokens.store(toks, std::memory_order_relaxed);
    vnni.store(v, std::memory_order_relaxed);
    phase.store(1, std::memory_order_release);
    while (phase.load(std::memory_order_acquire) != 2) _mm_pause();
    phase.store(0, std::memory_order_relaxed);
  }

  static void pin(int cpu) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) {
      std::perror("sched_setaffinity");
      std::exit(2);
    }
  }
};

// ---------------------------------------------------------------- helpers

inline uint64_t tsc_begin() {
  _mm_lfence();
  const uint64_t t = __rdtsc();
  _mm_lfence();
  return t;
}
inline uint64_t tsc_end() {
  unsigned aux;
  const uint64_t t = __rdtscp(&aux);
  _mm_lfence();
  return t;
}

double tsc_ghz() {
  const auto c0 = std::chrono::steady_clock::now();
  const uint64_t t0 = __rdtsc();
  while (std::chrono::steady_clock::now() - c0 < std::chrono::milliseconds(200)) {}
  const uint64_t t1 = __rdtsc();
  const auto c1 = std::chrono::steady_clock::now();
  const double ns = std::chrono::duration<double, std::nano>(c1 - c0).count();
  return double(t1 - t0) / ns;
}

void fill_rows(rows_t& rows, std::mt19937& rng) {
  std::normal_distribution<float> dist(0.0f, 1.0f);
  for (auto& r : rows.row) {
    for (auto& v : r) v = bf16(dist(rng));
  }
}

// Write the block in the layout the arm reads (all 16 rows: absent tokens hold
// stale values, which masked loads and the row loop never touch).
void lay_out_block(plane_t& plane, const rows_t& rows, bool vnni) {
  for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
    const auto src = tron::k_source_row<HEAD_SIZE_128>(rows.row[t]);
    if (vnni) {
      tron::store_row(plane.as_view(), FIRST_TOKEN + t, src);
    } else {
      tron::store_row_major(plane.as_view(), FIRST_TOKEN + t, src);
    }
  }
}

// The block's 4 KiB: its 4 panels (s, BLOCK_C), 1 KiB each.
void flush_block(const plane_t& plane) {
  const char* base = reinterpret_cast<const char*>(&plane);
  for (size_t s = 0; s < tron::k_vnni::DIM_STEPS_4; ++s) {
    const char* panel = base + (s * tron::k_vnni::TOKEN_BLOCKS_4 + BLOCK_C) *
                                   tron::k_vnni::PANEL_BYTES_1024;
    for (size_t off = 0; off < tron::k_vnni::PANEL_BYTES_1024; off += 64) {
      _mm_clflushopt(const_cast<char*>(panel + off));
    }
  }
  _mm_sfence();
}

uint64_t evict_l2(std::vector<uint64_t>& buf) {
  uint64_t acc = 0;
  for (size_t i = 0; i < buf.size(); i += 8) {
    acc += buf[i];
    buf[i] = acc;
  }
  return acc;
}

double reference(const rows_t& rows, const bf16* q, size_t h, size_t t) {
  double acc = 0;
  for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
    acc += double(float(q[h * HEAD_SIZE_128 + d])) * double(float(rows.row[t][d]));
  }
  return acc;
}

struct stats_t {
  double median, p10, p90, mean;
};

stats_t stats(std::vector<uint64_t>& v, double ghz) {
  std::sort(v.begin(), v.end());
  auto at = [&](double f) { return double(v[size_t(f * double(v.size() - 1))]) / ghz; };
  double sum = 0;
  for (auto x : v) sum += double(x);
  return {at(0.5), at(0.1), at(0.9), sum / double(v.size()) / ghz};
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) {
    std::fprintf(stderr, "usage: %s <reader_cpu> <writer_cpu> [iters_hot] [iters_cold]\n",
        argv[0]);
    return 2;
  }
  const int reader_cpu = std::atoi(argv[1]);
  const int writer_cpu = std::atoi(argv[2]);
  const size_t iters_hot = argc > 3 ? std::strtoul(argv[3], nullptr, 10) : 20000;
  const size_t iters_cold = argc > 4 ? std::strtoul(argv[4], nullptr, 10) : 3000;

  writer_t::pin(reader_cpu);
  const double ghz = tsc_ghz();
  std::printf("# tail_bench reader_cpu=%d writer_cpu=%d tsc_ghz=%.4f iters_hot=%zu "
              "iters_cold=%zu\n",
      reader_cpu, writer_cpu, ghz, iters_hot, iters_cold);

  auto* plane = new plane_t;
  std::memset(plane, 0, sizeof(*plane));
  auto* rows = new rows_t;
  std::mt19937 rng(4934);
  fill_rows(*rows, rng);
  alignas(64) bf16 q[8 * HEAD_SIZE_128];
  {
    std::normal_distribution<float> dist(0.0f, 1.0f);
    for (auto& v : q) v = bf16(dist(rng));
  }
  alignas(64) float s[8 * S_STRIDE];
  std::vector<uint64_t> evict(EVICT_BYTES / sizeof(uint64_t), 1);
  volatile float sink = 0;

  writer_t writer;
  writer.plane = plane;
  writer.rows = rows;
  std::thread writer_thread([&] { writer.run(writer_cpu); });

  // Correctness: every arm against a double reference, every n, both kv_mul.
  for (const auto& arm : ARMS) {
    for (size_t kv_mul : {size_t(4), size_t(8)}) {
      const path_fn fn = kv_mul == 4 ? arm.fn4 : arm.fn8;
      double worst = 0;
      for (size_t n = 1; n <= 15; ++n) {
        const uint64_t live = ((uint64_t(1) << n) - 1) << FIRST_TOKEN;
        lay_out_block(*plane, *rows, arm.vnni_layout);
        for (auto& x : s) x = -1.0f / 0.0f;
        fn(std::as_const(*plane).as_view(), q, live, s);
        for (size_t h = 0; h < kv_mul; ++h) {
          for (size_t t = 0; t < n; ++t) {
            const double ref = reference(*rows, q, h, t);
            const double got = s[h * S_STRIDE + FIRST_TOKEN + t];
            const double err = std::fabs(got - ref) / std::max(1.0, std::fabs(ref));
            worst = std::max(worst, err);
          }
          for (size_t t = n; t < BLOCK_TOKENS_16; ++t) {
            if (std::isfinite(s[h * S_STRIDE + FIRST_TOKEN + t])) {
              std::printf("check,%s,%zu,%zu,WROTE_DEAD_LANE_%zu\n", arm.name, kv_mul, n, t);
              worst = 1.0;
            }
          }
        }
      }
      std::printf("check,%s,%zu,all,%.3e\n", arm.name, kv_mul, worst);
    }
  }

  const char* SCENARIOS[] = {"hot", "step", "alldirty", "flush"};
  std::vector<uint64_t> samples;
  for (const char* scenario : SCENARIOS) {
    const bool hot = std::strcmp(scenario, "hot") == 0;
    const bool step = std::strcmp(scenario, "step") == 0;
    const bool alldirty = std::strcmp(scenario, "alldirty") == 0;
    const bool flush = std::strcmp(scenario, "flush") == 0;
    const size_t iters = hot ? iters_hot : iters_cold;
    for (const auto& arm : ARMS) {
      for (size_t kv_mul : {size_t(4), size_t(8)}) {
        const path_fn fn = kv_mul == 4 ? arm.fn4 : arm.fn8;
        for (size_t n = 1; n <= 15; ++n) {
          const uint64_t live = ((uint64_t(1) << n) - 1) << FIRST_TOKEN;
          const uint64_t newest = uint64_t(1) << (FIRST_TOKEN + n - 1);
          lay_out_block(*plane, *rows, arm.vnni_layout);
          samples.clear();
          samples.reserve(iters);
          const cview_t view = std::as_const(*plane).as_view();
          for (size_t it = 0; it < iters + iters / 10; ++it) {
            if (step) {
              writer.write(newest, arm.vnni_layout);
              sink = float(evict_l2(evict));
              // q is the worker's own fresh data: hot again before the visit.
              for (size_t i = 0; i < kv_mul * HEAD_SIZE_128; i += 32) sink = float(q[i]);
            } else if (alldirty) {
              writer.write(live, arm.vnni_layout);
            } else if (flush) {
              flush_block(*plane);
            }
            const uint64_t t0 = tsc_begin();
            fn(view, q, live, s);
            const uint64_t t1 = tsc_end();
            sink = s[FIRST_TOKEN];
            if (it >= iters / 10) samples.push_back(t1 - t0);  // the first tenth warms up
          }
          const stats_t st = stats(samples, ghz);
          std::printf("%s,%s,%zu,%zu,%zu,%.1f,%.1f,%.1f,%.1f\n", scenario, arm.name, kv_mul,
              n, samples.size(), st.median, st.p10, st.p90, st.mean);
          std::fflush(stdout);
        }
      }
    }
  }
  writer.phase.store(-1, std::memory_order_release);
  writer_thread.join();
  (void)sink;
  delete plane;
  delete rows;
  return 0;
}
