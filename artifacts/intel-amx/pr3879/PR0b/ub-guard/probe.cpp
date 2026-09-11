// Calls the real tron::log_kv_footprint (h/tron/models/kv_cache.hpp) twice:
// once above the 1 GiB print granularity (prints the footprint line), once below it (throttled).
#include <tron/models/kv_cache.hpp>
#include <cstdio>
int main() {
  tron::log_kv_footprint(int64_t{2} << 30, 1);
  tron::log_kv_footprint(1, 0);
  std::puts("probe: both calls returned");
  return 0;
}
