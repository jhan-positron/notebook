// Verifier: does the blocked working-copy layout cost anything through 4K aliasing?
// Layout [value block][key row][16 columns] puts the 4 chunks of one key row exactly
// 8,192 bytes apart (same address bits 0..11). Loop 2 stores chunk c and then loads
// chunk c+1 when it keeps the statement order of gated_delta_net.hpp:288-293.
// Variants: block stride 128 lines (as specified) and 129 lines (no aliasing).
// Host: design host (Zen 5 guest), NOT the Xeon 6962P.
#define _GNU_SOURCE
#include <immintrin.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define KD 128
static inline uint64_t now_ns(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC_RAW,&ts);return (uint64_t)ts.tv_sec*1000000000ull+ts.tv_nsec;}
// loop 2 only, statement order of the tron kernel: per chunk load, fma, store, fma
__attribute__((noinline)) static void loop2_tron_order(float *Sl, size_t block_lines, const float *k, const float *qs,
                                                       const __m512 *d, __m512 dv, float *o) {
  __m512 res[4] = {_mm512_setzero_ps(), _mm512_setzero_ps(), _mm512_setzero_ps(), _mm512_setzero_ps()};
  for (int i = 0; i < KD; i++) {
    __m512 kv = _mm512_set1_ps(k[i]), qv = _mm512_set1_ps(qs[i]);
    for (int c = 0; c < 4; c++) {
      float *p = Sl + ((size_t)c * block_lines + i) * 16;
      __m512 ns = _mm512_fmadd_ps(kv, d[c], _mm512_mul_ps(_mm512_load_ps(p), dv));
      _mm512_store_ps(p, ns);
      __asm__ volatile("" ::: "memory");  // keep the store before the next chunk's load
      res[c] = _mm512_fmadd_ps(qv, ns, res[c]);
    }
  }
  for (int c = 0; c < 4; c++) _mm512_storeu_ps(o + c * 16, res[c]);
}
int main(int argc, char **argv) {
  int cpu = argc > 1 ? atoi(argv[1]) : -1;
  if (cpu >= 0) { cpu_set_t s; CPU_ZERO(&s); CPU_SET(cpu, &s); sched_setaffinity(0, sizeof s, &s); }
  float *S = aligned_alloc(4096, 1 << 20);
  for (int i = 0; i < (1 << 18); i++) S[i] = 0.01f * (float)((i * 2654435761u) >> 20) / 4096.0f;
  float k[KD], qs[KD], o[64];
  for (int i = 0; i < KD; i++) { k[i] = 0.05f + 0.001f * i; qs[i] = 0.01f; }
  __m512 d[4] = {_mm512_set1_ps(1e-3f), _mm512_set1_ps(2e-3f), _mm512_set1_ps(3e-3f), _mm512_set1_ps(4e-3f)};
  __m512 dv = _mm512_set1_ps(0.95f);
  size_t strides[2] = {128, 129};
  double best[2] = {1e30, 1e30};
  for (int round = 0; round < 400; round++)
    for (int v = 0; v < 2; v++) {
      uint64_t t0 = now_ns();
      for (int rep = 0; rep < 64; rep++) loop2_tron_order(S, strides[v], k, qs, d, dv, o);
      uint64_t t1 = now_ns();
      double ns = (double)(t1 - t0) / 64;
      if (ns < best[v]) best[v] = ns;
    }
  printf("loop 2 on one 32 KiB slice, tron statement order (store chunk c, then load chunk c+1), lowest of 400 rounds:\n");
  printf("  block stride 128 lines (chunks 8,192 B apart, 4K-aliased): %.1f ns per slice-token\n", best[0]);
  printf("  block stride 129 lines (chunks 8,256 B apart, not aliased): %.1f ns per slice-token\n", best[1]);
  printf("  ratio aliased / not aliased = %.2fx  (1,536 zmm operations per slice-token)\n", best[0] / best[1]);
  return (int)o[0] & 0;
}
