// Ground truth for the window struct layout: a replica of batch::k_store_window_t
// (h/tron/models/common.hpp, head 04ffeedccb) with the generated plugins'
// max_minibatch_size = 1024 (ingest/src/TronCpp.hs:263) and cache_line_size = 64.
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdio>
constexpr size_t cache_line_size = 64;
constexpr size_t max_minibatch_size = 1024;
struct k_store_window_t {
  static constexpr size_t MAX_SHARED_WORKERS_128 = 128;
  alignas(cache_line_size) std::atomic<uint32_t> next_unit{0};
  alignas(cache_line_size) std::atomic<uint32_t> opened{0};
  std::atomic<uint32_t> finished{0};
  uint32_t n_units = 0;
  std::array<uint32_t, max_minibatch_size + 1> unit_start{};
  std::array<uint32_t, MAX_SHARED_WORKERS_128> helper_windows{};
};
int main() {
  printf("{\"sizeof\":%zu,\"next_unit\":%zu,\"opened\":%zu,\"finished\":%zu,\"n_units\":%zu,\"unit_start\":%zu,\"unit_start_end\":%zu,\"helper_windows\":%zu,\"helper_windows_end\":%zu,\"lines\":%zu}\n",
    sizeof(k_store_window_t), offsetof(k_store_window_t, next_unit), offsetof(k_store_window_t, opened),
    offsetof(k_store_window_t, finished), offsetof(k_store_window_t, n_units), offsetof(k_store_window_t, unit_start),
    offsetof(k_store_window_t, unit_start) + sizeof(k_store_window_t::unit_start),
    offsetof(k_store_window_t, helper_windows), offsetof(k_store_window_t, helper_windows) + sizeof(k_store_window_t::helper_windows),
    sizeof(k_store_window_t) / 64);
  return 0;
}
