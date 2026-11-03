// H6 test: does the head's two-pass loop expose more K latency than the base's one-pass loop
// when the K page comes from L2 / L3 instead of L1?
// Arms copied from ../bench/kloop.cpp (base one-pass, head two-pass inline).
// Modes: "cycle N" = every visit reads the next page of a ring of N pages (N pages x 16.3 KB working set),
//        "prefill N" = each page of a ring of N pages is visited by 128 queries in a row, then the next page
//        (the real prefill pattern: pages outer, queries inner).
#include <immintrin.h>
#include <algorithm>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

constexpr int PAGE = 64, DIMS = 128, KV_MUL = 4;
struct alignas(64) Page {
  uint16_t k[PAGE][DIMS];
  uint32_t token_id[PAGE];
};
struct Dotter {
  __m512bh x0, x1, x2, x3;
  explicit Dotter(const uint16_t* q) noexcept
  : x0((__m512bh)_mm512_load_si512(q)), x1((__m512bh)_mm512_load_si512(q + 32)),
    x2((__m512bh)_mm512_load_si512(q + 64)), x3((__m512bh)_mm512_load_si512(q + 96)) {}
  inline __attribute__((always_inline)) float dot(const uint16_t* y) const noexcept {
    __m512bh y0 = (__m512bh)_mm512_load_si512(y), y1 = (__m512bh)_mm512_load_si512(y + 32);
    __m512bh y2 = (__m512bh)_mm512_load_si512(y + 64), y3 = (__m512bh)_mm512_load_si512(y + 96);
    __m512 s1 = _mm512_dpbf16_ps(_mm512_setzero_ps(), x0, y0);
    __m512 s2 = _mm512_dpbf16_ps(_mm512_setzero_ps(), x1, y1);
    s1 = _mm512_dpbf16_ps(s1, x2, y2);
    s2 = _mm512_dpbf16_ps(s2, x3, y3);
    return _mm512_reduce_add_ps(_mm512_add_ps(s1, s2));
  }
};
struct Visit {
  const Page* page; const uint16_t* q; uint32_t tok_hi; uint32_t q_position; uint32_t k_position; int window;
};
static inline __attribute__((always_inline)) float consume(const float (*s)[PAGE]) {
  __m512 m = _mm512_set1_ps(-1e30f);
  for (int h = 0; h < KV_MUL; ++h)
    for (int i = 0; i < PAGE; i += 16) m = _mm512_max_ps(m, _mm512_loadu_ps(&s[h][i]));
  return _mm512_reduce_max_ps(m);
}
static inline __attribute__((always_inline)) void fill_neg_inf(float (*s)[PAGE]) {
  for (int h = 0; h < KV_MUL; ++h)
    for (int i = 0; i < PAGE; i += 16) _mm512_storeu_ps(&s[h][i], _mm512_set1_ps(-1.0f / 0.0f));
}
__attribute__((noinline)) float visit_base(const Visit& v) {
  alignas(64) float s_pages[KV_MUL][PAGE];
  fill_neg_inf(s_pages);
  const Dotter dot_q[KV_MUL] = {Dotter(v.q), Dotter(v.q + DIMS), Dotter(v.q + 2 * DIMS), Dotter(v.q + 3 * DIMS)};
  int relevant = 0;
  for (int i = 0; i < PAGE; ++i) {
    uint32_t kv_idx = v.page->token_id[i];
    if (kv_idx >= v.tok_hi) break;
    if ((int)v.q_position - (int)(v.k_position + i) >= v.window) continue;
    relevant++;
    const uint16_t* k = v.page->k[i];
    for (int h = 0; h < KV_MUL; ++h) s_pages[h][i] = dot_q[h].dot(k);
  }
  if (relevant == 0) return 0.f;
  return consume(s_pages);
}
static inline __attribute__((always_inline)) void score_k(const Page* page, const uint16_t* q, uint64_t live, float* scores, size_t stride) {
  if (live == 0) return;
  const Dotter dot_q[KV_MUL] = {Dotter(q), Dotter(q + DIMS), Dotter(q + 2 * DIMS), Dotter(q + 3 * DIMS)};
  for (uint64_t remaining = live; remaining != 0; remaining &= remaining - 1) {
    const size_t i = std::countr_zero(remaining);
    const uint16_t* k = page->k[i];
    for (int h = 0; h < KV_MUL; ++h) scores[h * stride + i] = dot_q[h].dot(k);
  }
}
__attribute__((noinline)) float visit_head(const Visit& v) {
  alignas(64) float s_pages[KV_MUL][PAGE];
  fill_neg_inf(s_pages);
  int relevant = 0;
  uint64_t live = 0;
  for (int i = 0; i < PAGE; ++i) {
    uint32_t kv_idx = v.page->token_id[i];
    if (kv_idx >= v.tok_hi) break;
    if ((int)v.q_position - (int)(v.k_position + i) >= v.window) continue;
    relevant++;
    live |= uint64_t{1} << i;
  }
  score_k(v.page, v.q, live, &s_pages[0][0], PAGE);
  if (relevant == 0) return 0.f;
  return consume(s_pages);
}
static long parse(const char* s) { long v = 0; for (; *s >= 48 && *s <= 57; ++s) v = v * 10 + (*s - 48); return v; }
static uint16_t f2bf(float f) { uint32_t u; std::memcpy(&u, &f, 4); return uint16_t(u >> 16); }

int main(int argc, char** argv) {
  const long n_visits = argc > 1 ? parse(argv[1]) : 1000000;
  const int reps = argc > 2 ? int(parse(argv[2])) : 5;
  const long n_pages_max = 65536;
  std::vector<Page> pages(n_pages_max);
  for (long p = 0; p < n_pages_max; ++p)
    for (int i = 0; i < PAGE; ++i) {
      pages[p].token_id[i] = uint32_t(p * PAGE + i);
      for (int d = 0; d < DIMS; ++d) pages[p].k[i][d] = f2bf(float(((i * 7 + d * 3 + p) % 17) - 8) / 8.0f);
    }
  alignas(64) uint16_t q[KV_MUL * DIMS];
  for (int j = 0; j < KV_MUL * DIMS; ++j) q[j] = f2bf(float((j % 13) - 6) / 8.0f);
  struct Arm { const char* name; float (*fn)(const Visit&); };
  const Arm arms[] = {{"base", visit_base}, {"head", visit_head}};
  const long sets[] = {1, 2, 4, 16, 48, 128, 1024, 4096, 65536};
  printf("visits per arm %ld, reps %d (min reported), page = %zu bytes\n", n_visits, reps, sizeof(Page));
  for (int mode = 0; mode < 2; ++mode) {
    printf("-- mode %s --\n", mode == 0 ? "cycle: each visit = next page of a ring of N pages" : "prefill: 128 visits per page, then the next page of the ring");
    printf("%8s %10s %10s %10s %10s %8s\n", "N pages", "KB", "base ns", "head ns", "delta ns", "delta %");
    for (long N : sets) {
      double best[2] = {1e30, 1e30};
      for (int rep = 0; rep < reps; ++rep)
        for (int a = 0; a < 2; ++a) {
          float acc = 0;
          auto t0 = std::chrono::steady_clock::now();
          for (long n = 0; n < n_visits; ++n) {
            long p = mode == 0 ? (n % N) : ((n / 128) % N);
            Visit v{&pages[p], q, 0xffffffffu, uint32_t(PAGE * p + 200000), uint32_t(PAGE * p), 1 << 30};
            acc += arms[a].fn(v);
          }
          auto t1 = std::chrono::steady_clock::now();
          double ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / n_visits;
          if (acc == 12345.f) printf("x");
          best[a] = std::min(best[a], ns);
        }
      printf("%8ld %10.0f %10.1f %10.1f %+10.1f %+7.1f%%\n", N, N * sizeof(Page) / 1024.0, best[0], best[1], best[1] - best[0], 100.0 * (best[1] - best[0]) / best[0]);
    }
  }
}
