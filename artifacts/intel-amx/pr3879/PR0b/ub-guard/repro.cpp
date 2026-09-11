// Minimal copy of the log_kv_footprint throttle. ORDER is the memory order of the load.
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#ifndef ORDER
#define ORDER std::memory_order_release
#endif
static std::atomic_int64_t last_print_bytes = 0;
__attribute__((noinline)) bool throttled(int64_t new_bytes, int64_t granularity) {
  if (std::abs(new_bytes - last_print_bytes.load(ORDER)) < granularity) return true;
  last_print_bytes.store(new_bytes, std::memory_order_release);
  return false;
}
int main(int argc, char**) { std::printf("throttled=%d\n", (int)throttled(argc * 100, 10)); return 0; }
