// bench_k_vnni: per-row costs of the three K-path operations that PR #4424 (TRON_K_VNNI) changes on the
// FPGA-attention decode path, against their row-major counterparts, in the cache states a decode step
// produces. Stand-alone copies of h/tron/kernels/k_vnni.hpp (index formula, scatter_row, gather_row,
// qk_group<4,bf16>) and of dotter<bf16,128> (dotter.hpp:176-226); AVX-512 only (no AMX).
//
// Words used here: plane = the K storage of one (page, KV head): 64 tokens x 128 dims x bf16 = 16 KiB;
// row = one token's 128 bf16 values (256 B); line = 64-byte cache line; VNNI = the pair-interleaved
// layout (a row lives in 64 lines, 4 bytes each); row-major = the row is 4 consecutive lines;
// step = one decode step: the main thread stores one row per (user, KV head, layer) = ROWS planes;
// worker = the attention worker that reads the newest rows (tail scoring) and stages GOFs (gather).
//
// Protocol (two threads, pinned): thread M ("main") stores token t into every plane (ROWS planes,
// the whole step's K rows), then thread W ("worker") reads the newest token of every plane like the
// tail scoring does (qk_group on the VNNI plane / dotter on the row-major plane), and every 4th step
// W also stages the 4 newest tokens like gof::populate does (gather_row / memcpy of 4 rows). M and W
// alternate on a barrier so their access pattern to the same lines (M writes, W reads, M writes ...)
// is the pattern of decode. Times are per row on the thread that does the work.
// Cases: --rows N (planes per step; 2304 = 8 users x 8 heads x 36 layers, 576 = 2 users x 8 x 36)
//        --steps S (timed steps; 8 warm-up steps extra), --main CPU --worker CPU, --no-worker.
// Output: one line per quantity: ns per row (mean over steps) for vnni and rowmajor variants.
#include <immintrin.h>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sched.h>
#include <thread>
#include <vector>
#include <string>

using bf16 = uint16_t;
static constexpr size_t PAGE_TOKENS_64 = 64, HEAD_SIZE_128 = 128, PAIR_2 = 2, DWORD_BYTES_4 = 4, LINE_BYTES_64 = 64;
static constexpr size_t BLOCK_TOKENS_16 = 16, TOKEN_BLOCKS_4 = 4, STEP_DIMS_32 = 32, STEP_PAIRS_16 = 16, DIM_STEPS_4 = 4;
static constexpr size_t ROW_ELEMS_32 = 32, ROW_DWORDS_16 = 16, PANEL_DWORDS_256 = 256, PANEL_ELEMS_512 = 512;
static constexpr size_t PLANE_ELEMS = PAGE_TOKENS_64 * HEAD_SIZE_128;   // 8192 bf16 = 16 KiB
static constexpr size_t KV_MUL = 4;

static inline char* pair_base(bf16* plane, size_t s, size_t token) {
  const size_t c = token / BLOCK_TOKENS_16, t = token % BLOCK_TOKENS_16;
  return reinterpret_cast<char*>(plane) + ((s * TOKEN_BLOCKS_4 + c) * PANEL_DWORDS_256 + t) * DWORD_BYTES_4;
}
static inline const char* pair_base(const bf16* plane, size_t s, size_t token) {
  const size_t c = token / BLOCK_TOKENS_16, t = token % BLOCK_TOKENS_16;
  return reinterpret_cast<const char*>(plane) + ((s * TOKEN_BLOCKS_4 + c) * PANEL_DWORDS_256 + t) * DWORD_BYTES_4;
}
static inline __m512i pair_row_offsets() {
  constexpr int R = int(ROW_DWORDS_16);
  return _mm512_set_epi32(15 * R, 14 * R, 13 * R, 12 * R, 11 * R, 10 * R, 9 * R, 8 * R, 7 * R, 6 * R, 5 * R, 4 * R, 3 * R, 2 * R, 1 * R, 0);
}
static inline void scatter_row(bf16* plane, size_t token, const bf16* row) {
  const __m512i offsets = pair_row_offsets();
  for (size_t s = 0; s < DIM_STEPS_4; ++s) {
    const __m512i pairs = _mm512_loadu_si512(row + s * STEP_DIMS_32);
    _mm512_i32scatter_epi32(pair_base(plane, s, token), offsets, pairs, DWORD_BYTES_4);
  }
}
static inline void gather_row(const bf16* plane, size_t token, bf16* row) {
  const __m512i offsets = pair_row_offsets();
  for (size_t s = 0; s < DIM_STEPS_4; ++s) {
    const __m512i pairs = _mm512_i32gather_epi32(offsets, pair_base(plane, s, token), DWORD_BYTES_4);
    _mm512_storeu_si512(row + s * STEP_DIMS_32, pairs);
  }
}
// qk_group<4, bf16>: scores of 4 query heads against the live tokens of the plane (masked loads per pair row)
static inline void qk_group4(const bf16* plane, const bf16* q, uint64_t live, float* s, size_t s_stride) {
  for (size_t c = 0; c < TOKEN_BLOCKS_4; ++c) {
    const __mmask16 mask = __mmask16(live >> (c * BLOCK_TOKENS_16));
    if (mask == 0) continue;
    __m512 acc[KV_MUL];
    for (size_t h = 0; h < KV_MUL; ++h) acc[h] = _mm512_setzero_ps();
    for (size_t step = 0; step < DIM_STEPS_4; ++step) {
      const bf16* panel = plane + (step * TOKEN_BLOCKS_4 + c) * PANEL_ELEMS_512;
      for (size_t dp = 0; dp < STEP_PAIRS_16; ++dp) {
        const __m512i k_pairs = _mm512_maskz_loadu_epi32(mask, panel + dp * ROW_ELEMS_32);
        const size_t d = step * STEP_DIMS_32 + PAIR_2 * dp;
        for (size_t h = 0; h < KV_MUL; ++h) {
          uint32_t q_pair; std::memcpy(&q_pair, q + h * HEAD_SIZE_128 + d, sizeof(q_pair));
          acc[h] = _mm512_dpbf16_ps(acc[h], (__m512bh)_mm512_set1_epi32(int(q_pair)), (__m512bh)k_pairs);
        }
      }
    }
    for (size_t h = 0; h < KV_MUL; ++h) _mm512_mask_storeu_ps(s + h * s_stride + c * BLOCK_TOKENS_16, mask, acc[h]);
  }
}
// dotter<bf16,128>: q (4 x 64 B) held in registers, one token row: 4 loads + 4 VDPBF16PS (2 chains) + reduce
static inline float reduce_sum(__m512 v) { return _mm512_reduce_add_ps(v); }
struct dotter_bf16_128 {
  __m512i x01, x23, x45, x67;
  explicit dotter_bf16_128(const bf16* q) : x01(_mm512_loadu_si512(q)), x23(_mm512_loadu_si512(q + 32)), x45(_mm512_loadu_si512(q + 64)), x67(_mm512_loadu_si512(q + 96)) {}
  inline float dot(const bf16* y) const {
    __m512i y01 = _mm512_loadu_si512(y), y23 = _mm512_loadu_si512(y + 32), y45 = _mm512_loadu_si512(y + 64), y67 = _mm512_loadu_si512(y + 96);
    __m512 s1 = _mm512_dpbf16_ps(_mm512_setzero_ps(), (__m512bh)x01, (__m512bh)y01);
    __m512 s2 = _mm512_dpbf16_ps(_mm512_setzero_ps(), (__m512bh)x23, (__m512bh)y23);
    s1 = _mm512_dpbf16_ps(s1, (__m512bh)x45, (__m512bh)y45);
    s2 = _mm512_dpbf16_ps(s2, (__m512bh)x67, (__m512bh)y67);
    return reduce_sum(_mm512_add_ps(s1, s2));
  }
};

static void pin(int cpu) {
  if (cpu < 0) return;
  cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu, &set);
  if (sched_setaffinity(0, sizeof(set), &set) != 0) perror("sched_setaffinity");
}
static inline double now_ns() { return std::chrono::duration<double, std::nano>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

struct Barrier {  // two-party turn-taking: M runs when turn==0, W when turn==1
  std::atomic<int> turn{0};
  void wait_for(int who) { while (turn.load(std::memory_order_acquire) != who) _mm_pause(); }
  void hand_to(int who) { turn.store(who, std::memory_order_release); }
};

int main(int argc, char** argv) {
  size_t rows = 2304, steps = 64; int cpu_m = -1, cpu_w = -1; bool worker = true, vnni = true;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if (a == "--rows") rows = std::strtoul(argv[++i], nullptr, 10);
    else if (a == "--steps") steps = std::strtoul(argv[++i], nullptr, 10);
    else if (a == "--main") cpu_m = std::atoi(argv[++i]);
    else if (a == "--worker") cpu_w = std::atoi(argv[++i]);
    else if (a == "--no-worker") worker = false;
    else if (a == "--rowmajor") vnni = false;
    else { std::fprintf(stderr, "unknown arg %s\n", a.c_str()); return 2; }
  }
  const size_t warm = 8, total = warm + steps;
  // planes: 16 KiB each, 64-byte aligned; rows_in: the new K rows of one step (one per plane)
  bf16* planes = static_cast<bf16*>(std::aligned_alloc(4096, rows * PLANE_ELEMS * sizeof(bf16)));
  bf16* rows_in = static_cast<bf16*>(std::aligned_alloc(64, rows * HEAD_SIZE_128 * sizeof(bf16)));
  bf16* q = static_cast<bf16*>(std::aligned_alloc(64, rows * KV_MUL * HEAD_SIZE_128 * sizeof(bf16)));
  std::vector<float> scores(rows * KV_MUL * PAGE_TOKENS_64, 0.f);
  alignas(64) bf16 scratch[HEAD_SIZE_128 * 4];
  for (size_t i = 0; i < rows * PLANE_ELEMS; ++i) planes[i] = bf16(0x3f80 + (i & 0x7f));   // ~1.0 .. 1.99
  for (size_t i = 0; i < rows * HEAD_SIZE_128; ++i) rows_in[i] = bf16(0x3f00 + (i & 0x3f));
  for (size_t i = 0; i < rows * KV_MUL * HEAD_SIZE_128; ++i) q[i] = bf16(0x3f80 + (i & 0x1f));
  Barrier bar; std::atomic<bool> done{false};
  std::vector<double> t_store(total, 0.0), t_tail(total, 0.0), t_stage(total, 0.0);
  std::vector<size_t> n_stage(total, 0);
  volatile float sink = 0.f;
  std::thread wt;
  if (worker) wt = std::thread([&] {
    pin(cpu_w);
    float acc = 0.f;
    for (size_t st = 0; st < total; ++st) {
      bar.wait_for(1);
      const size_t token = st % PAGE_TOKENS_64;
      double t0 = now_ns();
      if (vnni) {
        const uint64_t live = uint64_t(1) << token;   // the newest token only (the tail)
        for (size_t r = 0; r < rows; ++r) qk_group4(planes + r * PLANE_ELEMS, q + r * KV_MUL * HEAD_SIZE_128, live, scores.data() + r * KV_MUL * PAGE_TOKENS_64, PAGE_TOKENS_64);
      } else {
        for (size_t r = 0; r < rows; ++r) {
          const bf16* qq = q + r * KV_MUL * HEAD_SIZE_128;
          const bf16* krow = planes + r * PLANE_ELEMS + token * HEAD_SIZE_128;
          for (size_t h = 0; h < KV_MUL; ++h) { dotter_bf16_128 d(qq + h * HEAD_SIZE_128); acc += d.dot(krow); }
        }
      }
      double t1 = now_ns();
      t_tail[st] = (t1 - t0) / rows;
      if (token % 4 == 3) {   // a GOF completed: stage its 4 tokens of every plane (populate)
        double t2 = now_ns();
        if (vnni) {
          for (size_t r = 0; r < rows; ++r) for (size_t k = 0; k < 4; ++k) gather_row(planes + r * PLANE_ELEMS, token - 3 + k, scratch + k * HEAD_SIZE_128);
        } else {
          for (size_t r = 0; r < rows; ++r) for (size_t k = 0; k < 4; ++k) std::memcpy(scratch + k * HEAD_SIZE_128, planes + r * PLANE_ELEMS + (token - 3 + k) * HEAD_SIZE_128, HEAD_SIZE_128 * sizeof(bf16));
        }
        acc += float(scratch[5]);
        double t3 = now_ns();
        t_stage[st] = (t3 - t2) / (rows * 4); n_stage[st] = rows * 4;
      }
      bar.hand_to(0);
    }
    sink = acc;
  });
  pin(cpu_m);
  for (size_t st = 0; st < total; ++st) {
    bar.wait_for(0);
    const size_t token = st % PAGE_TOKENS_64;
    double t0 = now_ns();
    if (vnni) { for (size_t r = 0; r < rows; ++r) scatter_row(planes + r * PLANE_ELEMS, token, rows_in + r * HEAD_SIZE_128); }
    else { for (size_t r = 0; r < rows; ++r) std::memcpy(planes + r * PLANE_ELEMS + token * HEAD_SIZE_128, rows_in + r * HEAD_SIZE_128, HEAD_SIZE_128 * sizeof(bf16)); }
    double t1 = now_ns();
    t_store[st] = (t1 - t0) / rows;
    if (worker) bar.hand_to(1); else { /* no worker: keep going */ }
    if (!worker) { /* emulate the worker turn without reading */ bar.hand_to(0); }
  }
  if (worker) wt.join();
  auto mean_from = [&](std::vector<double>& v, size_t from, bool only_stage) {
    double s = 0; size_t n = 0;
    for (size_t i = from; i < v.size(); ++i) { if (only_stage && n_stage[i] == 0) continue; s += v[i]; ++n; }
    return n ? s / n : 0.0;
  };
  std::printf("layout=%s rows=%zu steps=%zu worker=%d main_cpu=%d worker_cpu=%d\n", vnni ? "vnni" : "rowmajor", rows, steps, int(worker), cpu_m, cpu_w);
  std::printf("store_ns_per_row=%.1f\n", mean_from(t_store, warm, false));
  if (worker) {
    std::printf("tail_score_ns_per_row=%.1f   (one query group of 4 heads against the newest token of every plane)\n", mean_from(t_tail, warm, false));
    std::printf("stage_ns_per_row=%.1f   (populate of a 4-token GOF, per row; every 4th step)\n", mean_from(t_stage, warm, true));
  }
  std::printf("sink=%g\n", double(sink));
  std::free(planes); std::free(rows_in); std::free(q);
  return 0;
}
