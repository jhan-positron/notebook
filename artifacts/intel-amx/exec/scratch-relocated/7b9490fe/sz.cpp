#include <atomic>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstddef>
inline constexpr size_t cache_line_size = 64;
template <size_t N> struct W {
  static constexpr size_t max_shared_workers = 128;
  alignas(cache_line_size) std::atomic<uint32_t> next_unit{0};
  alignas(cache_line_size) std::atomic<uint32_t> opened{0};
  std::atomic<uint32_t> finished{0};
  uint32_t n_units = 0;
  std::array<uint32_t, N + 1> unit_start{};
  std::array<uint32_t, max_shared_workers> helper_windows{};
};
int main(){
  printf("N=1024 sizeof=%zu unit_table=%zu rest=%zu off_hw=%zu\n", sizeof(W<1024>), sizeof(W<1024>::unit_start), sizeof(W<1024>)-sizeof(W<1024>::unit_start), offsetof(W<1024>, helper_windows));
  printf("N=128 sizeof=%zu unit_table=%zu rest=%zu off_hw=%zu\n", sizeof(W<128>), sizeof(W<128>::unit_start), sizeof(W<128>)-sizeof(W<128>::unit_start), offsetof(W<128>, helper_windows));
}
