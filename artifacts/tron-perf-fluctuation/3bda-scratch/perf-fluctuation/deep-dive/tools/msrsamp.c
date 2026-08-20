// msrsamp: fixed-cadence MSR sampler for the perf-fluctuation deep dive.
// Samples, every PERIOD_US microseconds, on two target cpus:
//   APERF (0xE8), MPERF (0xE7), IA32_THERM_STATUS (0x19C)
// plus package: PKG_ENERGY_STATUS (0x611) and PACKAGE_THERM_STATUS (0x1B1),
// each record TSC-stamped so it joins the kvwait probe's timestamps offline.
// Record layout (little-endian, 56 bytes):
//   u64 tsc; u64 aperf0; u64 mperf0; u32 therm0;
//            u64 aperf1; u64 mperf1; u32 therm1;
//   u32 pkg_energy; u32 pkg_therm;
// Usage: msrsamp OUT PERIOD_US DURATION_S CPU_A CPU_B PIN_CPU
#define _GNU_SOURCE
#include <fcntl.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <x86intrin.h>

static int open_msr(int cpu) {
  char p[64];
  snprintf(p, sizeof p, "/dev/cpu/%d/msr", cpu);
  int fd = open(p, O_RDONLY);
  if (fd < 0) { perror(p); exit(1); }
  return fd;
}
static uint64_t rd(int fd, uint32_t reg) {
  uint64_t v = 0;
  if (pread(fd, &v, 8, reg) != 8) { perror("pread msr"); exit(1); }
  return v;
}

#pragma pack(push, 1)
typedef struct {
  uint64_t tsc, aperf0, mperf0;
  uint32_t therm0;
  uint64_t aperf1, mperf1;
  uint32_t therm1, pkg_energy, pkg_therm;
} rec_t;
#pragma pack(pop)

int main(int argc, char **argv) {
  if (argc != 7) { fprintf(stderr, "usage: %s OUT PERIOD_US DURATION_S CPU_A CPU_B PIN_CPU\n", argv[0]); return 1; }
  const char *out = argv[1];
  long period_us = atol(argv[2]), duration_s = atol(argv[3]);
  int cpu_a = atoi(argv[4]), cpu_b = atoi(argv[5]), pin = atoi(argv[6]);

  cpu_set_t set; CPU_ZERO(&set); CPU_SET(pin, &set);
  if (sched_setaffinity(0, sizeof set, &set)) { perror("setaffinity"); return 1; }

  int fa = open_msr(cpu_a), fb = open_msr(cpu_b), f0 = open_msr(0);
  long n_max = duration_s * 1000000L / period_us + 16;
  rec_t *buf = calloc(n_max, sizeof(rec_t));
  if (!buf) { perror("calloc"); return 1; }

  struct timespec next;
  clock_gettime(CLOCK_MONOTONIC, &next);
  long n = 0;
  for (; n < n_max; n++) {
    rec_t *r = &buf[n];
    r->tsc = __rdtsc();
    r->aperf0 = rd(fa, 0xE8); r->mperf0 = rd(fa, 0xE7);
    r->therm0 = (uint32_t)rd(fa, 0x19C);
    r->aperf1 = rd(fb, 0xE8); r->mperf1 = rd(fb, 0xE7);
    r->therm1 = (uint32_t)rd(fb, 0x19C);
    r->pkg_energy = (uint32_t)rd(f0, 0x611);
    r->pkg_therm  = (uint32_t)rd(f0, 0x1B1);
    next.tv_nsec += period_us * 1000L;
    while (next.tv_nsec >= 1000000000L) { next.tv_nsec -= 1000000000L; next.tv_sec++; }
    clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL);
  }
  FILE *fp = fopen(out, "wb");
  if (!fp) { perror(out); return 1; }
  fwrite(buf, sizeof(rec_t), n, fp);
  fclose(fp);
  fprintf(stderr, "msrsamp: wrote %ld records to %s\n", n, out);
  return 0;
}
