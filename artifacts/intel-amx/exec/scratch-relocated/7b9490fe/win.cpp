#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <new>
inline constexpr size_t cache_line_size = 64;
template <size_t max_minibatch_size>
struct k_store_window_t {
  static constexpr size_t max_shared_workers = 128;
  alignas(cache_line_size) std::atomic<uint32_t> next_unit{0};
  alignas(cache_line_size) std::atomic<uint32_t> opened{0};
  std::atomic<uint32_t> finished{0};
  uint32_t n_units = 0;
  std::array<uint32_t, max_minibatch_size + 1> unit_start{};
  std::array<uint32_t, max_shared_workers> helper_windows{};
};
template <size_t M> void dump(const char* name) {
  using W = k_store_window_t<M>;
  printf("%s: cache_line_size=%zu sizeof=%zu off(next_unit)=%zu off(opened)=%zu off(finished)=%zu off(n_units)=%zu off(unit_start)=%zu sizeof(unit_start)=%zu off(helper_windows)=%zu sizeof(helper_windows)=%zu fixed_without_unit_table=%zu\n",
    name, cache_line_size, sizeof(W), offsetof(W, next_unit), offsetof(W, opened), offsetof(W, finished), offsetof(W, n_units), offsetof(W, unit_start), sizeof(W::unit_start), offsetof(W, helper_windows), sizeof(W::helper_windows), sizeof(W) - sizeof(W::unit_start));
}
int main() { dump<1024>("generated(1024)"); dump<128>("llama(128)"); return 0; }
