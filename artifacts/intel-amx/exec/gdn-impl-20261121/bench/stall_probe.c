// gdn-impl-20261121: does work on other CPUs stall this CPU?
// The program pins itself to one CPU and reads the time-stamp counter in a tight loop for some seconds. A gap
// between two readings that is far longer than the loop time means that the CPU did not run this thread for
// that time: the hardware paused the core, or the kernel ran something else there.
// It prints the number of gaps above 20 us, 100 us and 1 ms, the longest gap and the total time lost in gaps
// above 20 us.
// Build: clang-19 -O2 -o stall_probe stall_probe.c      Run: ./stall_probe CPU SECONDS
#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <x86intrin.h>

int main(int argc, char **argv) {
  int cpu = argc > 1 ? atoi(argv[1]) : -1;
  double seconds = argc > 2 ? atof(argv[2]) : 4.0;
  if (cpu >= 0) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    sched_setaffinity(0, sizeof(set), &set);
  }
  // TSC rate from the monotonic clock
  struct timespec a, b;
  clock_gettime(CLOCK_MONOTONIC_RAW, &a);
  uint64_t t0 = __rdtsc();
  do clock_gettime(CLOCK_MONOTONIC_RAW, &b); while ((b.tv_sec - a.tv_sec) * 1e9 + (b.tv_nsec - a.tv_nsec) < 2e8);
  uint64_t t1 = __rdtsc();
  double hz = (t1 - t0) / (((b.tv_sec - a.tv_sec) * 1e9 + (b.tv_nsec - a.tv_nsec)) * 1e-9);
  uint64_t end = __rdtsc() + (uint64_t)(seconds * hz);
  uint64_t prev = __rdtsc(), now, max_gap = 0, n20 = 0, n100 = 0, n1000 = 0, lost = 0, iters = 0;
  const uint64_t g20 = (uint64_t)(20e-6 * hz), g100 = (uint64_t)(100e-6 * hz), g1000 = (uint64_t)(1e-3 * hz);
  while ((now = __rdtsc()) < end) {
    uint64_t gap = now - prev;
    prev = now;
    iters++;
    if (gap > g20) {
      n20++;
      lost += gap;
      if (gap > g100) n100++;
      if (gap > g1000) n1000++;
    }
    if (gap > max_gap) max_gap = gap;
  }
  printf("stall_probe cpu %d seconds %.1f iterations %llu gaps_over_20us %llu over_100us %llu over_1ms %llu longest_us %.1f lost_ms %.2f\n",
         cpu, seconds, (unsigned long long)iters, (unsigned long long)n20, (unsigned long long)n100,
         (unsigned long long)n1000, max_gap / hz * 1e6, lost / hz * 1e3);
  return 0;
}
