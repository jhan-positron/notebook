// amxspin: run AMX tile multiplies (tdpbf16ps) in a loop for N iterations, or a scalar loop
// when called with "scalar". Used only to validate a perf counter encoding: the AMX run must
// count, the scalar run must not.
#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/syscall.h>
#define ARCH_REQ_XCOMP_PERM 0x1023
#define XFEATURE_XTILEDATA 18
struct __attribute__((packed)) tilecfg { uint8_t palette; uint8_t start_row; uint8_t res[14]; uint16_t colsb[16]; uint8_t rows[16]; };
int main(int argc, char** argv) {
  long iters = argc > 2 ? atol(argv[2]) : 20000000L;
  if (argc > 1 && strcmp(argv[1], "scalar") == 0) {
    volatile double acc = 0; for (long i = 0; i < iters * 16; i++) acc += (double)i * 1e-9;
    printf("scalar done acc=%f\n", acc); return 0;
  }
  if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) != 0) { perror("arch_prctl"); return 2; }
  struct tilecfg cfg; memset(&cfg, 0, sizeof cfg); cfg.palette = 1;
  for (int t = 0; t < 3; t++) { cfg.colsb[t] = 64; cfg.rows[t] = 16; }
  _tile_loadconfig(&cfg);
  static uint16_t a[16 * 32], b[16 * 32]; static float c[16 * 16];
  for (int i = 0; i < 16 * 32; i++) { a[i] = 0x3f80; b[i] = 0x3f80; }  // bf16 1.0
  _tile_zero(0); _tile_loadd(1, a, 64); _tile_loadd(2, b, 64);
  for (long i = 0; i < iters; i++) { _tile_dpbf16ps(0, 1, 2); }
  _tile_stored(0, c, 64); _tile_release();
  printf("amx done c[0]=%f (expect %ld)\n", c[0], iters * 32L); return 0;
}
