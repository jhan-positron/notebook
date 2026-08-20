// membw: memory-bandwidth antagonist for the perf-fluctuation deep dive.
// Streams reads over a buffer far larger than LLC, pinned to one CPU,
// with a duty cycle to dial the load. Run one instance per antagonist CPU.
// Usage: membw CPU BUF_MB DUTY_PCT DURATION_S
#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static double now(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + t.tv_nsec * 1e-9;
}

int main(int argc, char **argv) {
  if (argc != 5) { fprintf(stderr, "usage: %s CPU BUF_MB DUTY_PCT DURATION_S\n", argv[0]); return 1; }
  int cpu = atoi(argv[1]);
  size_t mb = atol(argv[2]);
  int duty = atoi(argv[3]);
  double dur = atof(argv[4]);

  cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu, &set);
  if (sched_setaffinity(0, sizeof set, &set)) { perror("setaffinity"); return 1; }

  size_t n = mb * 1024 * 1024;
  uint64_t *buf = malloc(n);
  if (!buf) { perror("malloc"); return 1; }
  memset(buf, 1, n);

  size_t words = n / 8;
  volatile uint64_t sink = 0;
  double t_end = now() + dur, bytes = 0;
  // 10 ms work/sleep periods at the requested duty cycle
  const double period = 0.010;
  while (now() < t_end) {
    double t0 = now(), t_work = t0 + period * duty / 100.0;
    while (now() < t_work) {
      uint64_t acc = 0;
      for (size_t i = 0; i < words; i += 8) acc += buf[i];   // one load per cache line
      sink += acc;
      bytes += (double)(words / 8) * 64;
    }
    if (duty < 100) {
      struct timespec ts = {0, (long)(period * (100 - duty) / 100.0 * 1e9)};
      nanosleep(&ts, NULL);
    }
  }
  fprintf(stderr, "membw cpu%d: %.1f GB read, %.2f GB/s avg\n", cpu, bytes / 1e9, bytes / 1e9 / dur);
  return (int)(sink & 1);
}
