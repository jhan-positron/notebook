// pfbench: one AMX attention visit (QK over a 64x128 bf16 K plane, a 16x64
// softmax epilogue, PV over the packed V plane, the v*/s*/m* update) repeated
// over blocks streamed from a buffer larger than L3, with and without a
// software prefetch of the next block. Mirrors apply_dense_amx_page +
// qk_rowmajor_128x4<16> + weights_times_v_128x4<16> of tron branch
// jhan-amx-kvmul16 (5061623a34). Usage:
//   pfbench <mode> <nblocks> <visits> [order]
//   mode: none | full | lines8 | hot | fullk | interleave
//   order: seq (default) | rand
#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <x86intrin.h>
#include <algorithm>
#include <random>
#include <vector>

#define ARCH_REQ_XCOMP_PERM 0x1023
#define XFEATURE_XTILEDATA 18
struct __attribute__((packed)) tilecfg {
  uint8_t palette; uint8_t start_row; uint8_t res[14]; uint16_t colsb[16]; uint8_t rows[16];
};

constexpr size_t PAGE = 64, HEAD = 128, G = 16;
constexpr size_t PLANE_BYTES = PAGE * HEAD * 2;  // 16 KB
constexpr size_t BLOCK_BYTES = 2 * PLANE_BYTES;  // K + packed V = 32 KB

static inline __m512 exp512(__m512 x) {
  // cheap exp: 2^(x*log2e) via polynomial, enough to cost like a real one
  const __m512 log2e = _mm512_set1_ps(1.44269504f);
  __m512 t = _mm512_mul_ps(x, log2e);
  t = _mm512_max_ps(t, _mm512_set1_ps(-126.f));
  __m512 fl = _mm512_floor_ps(t);
  __m512 f = _mm512_sub_ps(t, fl);
  __m512 p = _mm512_set1_ps(0.05924f);
  p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(0.2402f));
  p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(0.6931f));
  p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(1.0f));
  return _mm512_scalef_ps(p, fl);
}

template <int lane>
static inline void store_transposed_rows(const __m512 (&u)[4][4], float* s_block, size_t s_stride) {
  constexpr int pair_sel = (lane & 1) ? 0xdd : 0x88;
  constexpr int quad_sel = (lane & 2) ? 0xdd : 0x88;
  float* const s_rows = s_block + lane * 4 * s_stride;
  for (size_t k = 0; k < 4; k++) {
    __m512 p = _mm512_shuffle_f32x4(u[0][k], u[1][k], pair_sel);
    __m512 q2 = _mm512_shuffle_f32x4(u[2][k], u[3][k], pair_sel);
    _mm512_storeu_ps(s_rows + k * s_stride, _mm512_shuffle_f32x4(p, q2, quad_sel));
  }
}

static int g_hint = 0;  // 0 none, 1 T1, 2 T0
static const uint8_t* g_pf = nullptr;
static size_t g_pf_off = 0;
static int g_lines = 16;
static inline void pf16() {
  if (!g_hint || g_pf_off >= BLOCK_BYTES) return;
  const char* b = (const char*)g_pf + g_pf_off;
  if (g_hint == 1) for (int l = 0; l < g_lines; l++) _mm_prefetch(b + l * 64, _MM_HINT_T1);
  else for (int l = 0; l < g_lines; l++) _mm_prefetch(b + l * 64, _MM_HINT_T0);
  g_pf_off += g_lines * 64;
}
static void qk(const uint16_t* k_rows, const uint16_t* q_packed, float* s) {
  alignas(64) float st[PAGE * 16];
  _tile_zero(0); _tile_zero(1); _tile_zero(2); _tile_zero(3);
  for (size_t step = 0; step < 4; step++) {
    _tile_loadd(6, q_packed + step * 16 * 32, 64);
    _tile_loadd(4, k_rows + 0 * 16 * HEAD + step * 32, 256); pf16();
    _tile_dpbf16ps(0, 4, 6);
    _tile_loadd(5, k_rows + 1 * 16 * HEAD + step * 32, 256); pf16();
    _tile_dpbf16ps(1, 5, 6);
    _tile_loadd(4, k_rows + 2 * 16 * HEAD + step * 32, 256); pf16();
    _tile_dpbf16ps(2, 4, 6);
    _tile_loadd(5, k_rows + 3 * 16 * HEAD + step * 32, 256); pf16();
    _tile_dpbf16ps(3, 5, 6);
  }
  _tile_stored(0, st + 0 * 256, 64);
  _tile_stored(1, st + 1 * 256, 64);
  _tile_stored(2, st + 2 * 256, 64);
  _tile_stored(3, st + 3 * 256, 64);
  for (int r = 0; r < 4; r++) {
    const float* src = st + r * 256;
    __m512 u[4][4];
    for (int rg = 0; rg < 4; rg++) {
      __m512 r0 = _mm512_loadu_ps(src + (4 * rg + 0) * 16);
      __m512 r1 = _mm512_loadu_ps(src + (4 * rg + 1) * 16);
      __m512 r2 = _mm512_loadu_ps(src + (4 * rg + 2) * 16);
      __m512 r3 = _mm512_loadu_ps(src + (4 * rg + 3) * 16);
      __m512 t0 = _mm512_unpacklo_ps(r0, r1), t1 = _mm512_unpackhi_ps(r0, r1);
      __m512 t2 = _mm512_unpacklo_ps(r2, r3), t3 = _mm512_unpackhi_ps(r2, r3);
      u[rg][0] = _mm512_castpd_ps(_mm512_unpacklo_pd(_mm512_castps_pd(t0), _mm512_castps_pd(t2)));
      u[rg][1] = _mm512_castpd_ps(_mm512_unpackhi_pd(_mm512_castps_pd(t0), _mm512_castps_pd(t2)));
      u[rg][2] = _mm512_castpd_ps(_mm512_unpacklo_pd(_mm512_castps_pd(t1), _mm512_castps_pd(t3)));
      u[rg][3] = _mm512_castpd_ps(_mm512_unpackhi_pd(_mm512_castps_pd(t1), _mm512_castps_pd(t3)));
    }
    float* const sb = s + r * 16;
    store_transposed_rows<0>(u, sb, PAGE);
    store_transposed_rows<1>(u, sb, PAGE);
    store_transposed_rows<2>(u, sb, PAGE);
    store_transposed_rows<3>(u, sb, PAGE);
  }
}

static void pv(const uint16_t* v_pairs, const float* exp_rows, float* o) {
  alignas(64) static thread_local uint16_t P[16][PAGE];
  for (size_t q = 0; q < G; q++)
    for (size_t c = 0; c < PAGE; c += 32) {
      __m512 lo = _mm512_loadu_ps(exp_rows + q * PAGE + c);
      __m512 hi = _mm512_loadu_ps(exp_rows + q * PAGE + c + 16);
      _mm512_storeu_si512(P[q] + c, (__m512i)_mm512_cvtne2ps_pbh(hi, lo));
    }
  for (int half = 0; half < 2; half++) {
    _tile_zero(0); _tile_zero(1); _tile_zero(2); _tile_zero(3);
    for (int s = 0; s < 2; s++) {
      _tile_loadd(4, &P[0][s * 32], PAGE * 2);
      const uint16_t* base = v_pairs + s * 16 * HEAD * 2;
      _tile_loadd(5, base + (half * 4 + 0) * 32, 512); pf16();
      _tile_dpbf16ps(0, 4, 5);
      _tile_loadd(6, base + (half * 4 + 1) * 32, 512); pf16();
      _tile_dpbf16ps(1, 4, 6);
      _tile_loadd(5, base + (half * 4 + 2) * 32, 512); pf16();
      _tile_dpbf16ps(2, 4, 5);
      _tile_loadd(6, base + (half * 4 + 3) * 32, 512); pf16();
      _tile_dpbf16ps(3, 4, 6);
    }
    _tile_stored(0, o + half * 64 + 0, HEAD * 4);
    _tile_stored(1, o + half * 64 + 16, HEAD * 4);
    _tile_stored(2, o + half * 64 + 32, HEAD * 4);
    _tile_stored(3, o + half * 64 + 48, HEAD * 4);
  }
}

struct state { alignas(64) float v_star[G][HEAD]; float s_star[G]; float m_star[G]; };

static inline void visit(const uint8_t* block, const uint16_t* qp, state& st, bool was_valid) {
  alignas(64) float s[G][PAGE];
  qk((const uint16_t*)block, qp, &s[0][0]);
  float corr[G], m_new[G], sum[G];
  const __m512 scale = _mm512_set1_ps(0.088388f);
  for (size_t h = 0; h < G; h++) {
    __m512 mx = _mm512_set1_ps(-1e30f);
    for (size_t c = 0; c < PAGE; c += 16) {
      __m512 x = _mm512_mul_ps(_mm512_loadu_ps(&s[h][c]), scale);
      _mm512_storeu_ps(&s[h][c], x);
      mx = _mm512_max_ps(mx, x);
    }
    float m_page = _mm512_reduce_max_ps(mx);
    if (was_valid) m_page = std::max(st.m_star[h], m_page);
    __m512 mv = _mm512_set1_ps(m_page), acc = _mm512_setzero_ps();
    for (size_t c = 0; c < PAGE; c += 16) {
      __m512 e = exp512(_mm512_sub_ps(_mm512_loadu_ps(&s[h][c]), mv));
      _mm512_storeu_ps(&s[h][c], e);
      acc = _mm512_add_ps(acc, e);
    }
    m_new[h] = m_page;
    sum[h] = _mm512_reduce_add_ps(acc);
    corr[h] = was_valid ? __builtin_expf(st.m_star[h] - m_page) : 0.f;
  }
  alignas(64) float o[16 * HEAD];
  pv((const uint16_t*)(block + PLANE_BYTES), &s[0][0], o);
  for (size_t h = 0; h < G; h++) {
    __m512 c = _mm512_set1_ps(corr[h]);
    for (size_t d = 0; d < HEAD; d += 16) {
      __m512 sc = _mm512_loadu_ps(o + h * HEAD + d);
      __m512 vs = _mm512_loadu_ps(&st.v_star[h][d]);
      _mm512_storeu_ps(&st.v_star[h][d], was_valid ? _mm512_fmadd_ps(vs, c, sc) : sc);
    }
    st.s_star[h] = was_valid ? st.s_star[h] * corr[h] + sum[h] : sum[h];
    st.m_star[h] = m_new[h];
  }
}

static inline void prefetch_block(const uint8_t* b, int lines_per_4k) {
  // 8 x 4 KB regions per block; lines_per_4k = 64 prefetches every line
  for (size_t r = 0; r < BLOCK_BYTES; r += 4096)
    for (int l = 0; l < lines_per_4k; l++) _mm_prefetch((const char*)b + r + l * 64, _MM_HINT_T1);
}

int main(int argc, char** argv) {
  if (argc < 4) { fprintf(stderr, "usage: pfbench mode nblocks visits [seq|rand]\n"); return 1; }
  const char* mode = argv[1];
  size_t nblocks = atol(argv[2]);
  size_t visits = atol(argv[3]);
  bool rand_order = argc > 4 && strcmp(argv[4], "rand") == 0;
  if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) != 0) { perror("arch_prctl"); return 2; }
  tilecfg cfg; memset(&cfg, 0, sizeof cfg); cfg.palette = 1;
  for (int t = 0; t < 8; t++) { cfg.colsb[t] = 64; cfg.rows[t] = 16; }
  _tile_loadconfig(&cfg);

  size_t bytes = nblocks * BLOCK_BYTES;
  uint8_t* buf = (uint8_t*)mmap(nullptr, bytes + (2u << 20), PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (buf == MAP_FAILED) { perror("mmap"); return 3; }
  buf = (uint8_t*)(((uintptr_t)buf + (2u << 20) - 1) & ~((uintptr_t)(2u << 20) - 1));
  madvise(buf, bytes, MADV_HUGEPAGE);
  // bf16 values in [-0.5, 0.5): fill with a simple LCG
  uint32_t x = 12345;
  for (size_t i = 0; i < bytes / 2; i++) {
    x = x * 1664525u + 1013904223u;
    float f = ((x >> 8) & 0xffff) / 65536.f - 0.5f;
    uint32_t bits; memcpy(&bits, &f, 4);
    ((uint16_t*)buf)[i] = (uint16_t)(bits >> 16);
  }
  alignas(64) uint16_t qp[4 * 16 * 32];
  for (size_t i = 0; i < sizeof(qp) / 2; i++) { x = x * 1664525u + 1013904223u; float f = ((x >> 8) & 0xffff) / 65536.f - 0.5f; uint32_t bits; memcpy(&bits, &f, 4); qp[i] = (uint16_t)(bits >> 16); }
  std::vector<uint32_t> order(nblocks);
  for (size_t i = 0; i < nblocks; i++) order[i] = i;
  if (rand_order) { std::mt19937 rng(7); std::shuffle(order.begin(), order.end(), rng); }

  state st; memset(&st, 0, sizeof st);
  bool hot = strcmp(mode, "hot") == 0;
  int pf_lines = 0;  // lines per 4 KB region of the NEXT block, prefetched at the top of the visit
  if (strcmp(mode, "full") == 0) pf_lines = 64;
  else if (strcmp(mode, "lines8") == 0) pf_lines = 1;
  else if (strcmp(mode, "lines16") == 0) pf_lines = 16;
  bool fullk = strcmp(mode, "fullk") == 0;  // prefetch only the next K plane + current V plane
  if (strcmp(mode, "il1") == 0) g_hint = 1;
  if (strcmp(mode, "il0") == 0) g_hint = 2;
  int dist = 1;
  if (strcmp(mode, "il1d2") == 0) { g_hint = 1; dist = 2; }
  if (strcmp(mode, "il1x2") == 0) { g_hint = 1; g_lines = 32; }
  if (strcmp(mode, "il1x2d2") == 0) { g_hint = 1; g_lines = 32; dist = 2; }
  bool stream = strncmp(mode, "stream", 6) == 0;  // pure reads, no compute
  bool stream_pf = strcmp(mode, "streampf") == 0;
  __m512i acc_stream = _mm512_setzero_si512();
  // warm up
  for (size_t i = 0; i < 64; i++) visit(buf + order[i % nblocks] * BLOCK_BYTES, qp, st, i > 0);
  uint64_t t0 = __rdtsc();
  for (size_t i = 0; i < visits; i++) {
    size_t cur = hot ? 0 : order[i % nblocks];
    size_t nxt = hot ? 0 : order[(i + dist) % nblocks];
    const uint8_t* b = buf + cur * BLOCK_BYTES;
    if (pf_lines) prefetch_block(buf + nxt * BLOCK_BYTES, pf_lines);
    g_pf = buf + nxt * BLOCK_BYTES; g_pf_off = 0;
    if (fullk) {
      for (size_t r = 0; r < PLANE_BYTES; r += 64) _mm_prefetch((const char*)b + PLANE_BYTES + r, _MM_HINT_T0);
      for (size_t r = 0; r < PLANE_BYTES; r += 64) _mm_prefetch((const char*)buf + nxt * BLOCK_BYTES + r, _MM_HINT_T1);
    }
    if (stream) {
      if (stream_pf) prefetch_block(buf + nxt * BLOCK_BYTES, 64);
      for (size_t r = 0; r < BLOCK_BYTES; r += 64) acc_stream = _mm512_xor_si512(acc_stream, _mm512_load_si512((const void*)(b + r)));
      continue;
    }
    visit(b, qp, st, (i % 32) != 0);
  }
  st.s_star[5] += (float)_mm512_reduce_add_epi32(acc_stream);
  { FILE* f = fopen("/proc/self/smaps_rollup", "r"); char line[256]; while (f && fgets(line, sizeof line, f)) if (strstr(line, "AnonHugePages")) fputs(line, stdout); if (f) fclose(f); }
  uint64_t t1 = __rdtsc();
  _tile_release();
  double per = (double)(t1 - t0) / visits;
  printf("mode=%s order=%s nblocks=%zu bytes=%.0fMB visits=%zu cycles/visit=%.0f (check %g)\n", mode,
      rand_order ? "rand" : "seq", nblocks, bytes / 1048576.0, visits, per, st.v_star[3][7] + st.s_star[5]);
  return 0;
}
