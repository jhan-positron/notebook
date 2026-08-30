// Isolated cost of generating the mirrored (transposed) K: one token-row
// scatter into a mirror plane. Copy of tron::detail::scatter_k_mirror
// (kv_cache.hpp) with page_size=64, head_size=128.
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
using bf16 = uint16_t;
static inline void scatter(bf16* plane, size_t i_page, const bf16* k_row) {
  const size_t c = i_page / 16, t = i_page % 16;
  for (size_t s = 0; s < 128 / 32; ++s)
    for (size_t dp = 0; dp < 16; ++dp) {
      bf16* dst = plane + (((s * (64 / 16) + c) * 16 + dp) * 16 + t) * 2;
      dst[0] = k_row[s * 32 + 2 * dp];
      dst[1] = k_row[s * 32 + 2 * dp + 1];
    }
}
int main() {
  // Model the real access pattern: many (kv_head) planes cycling (L2-resident
  // working set like save_k's), fresh K rows.
  constexpr int PLANES = 8;                       // 8 kv_heads/layer
  std::vector<bf16> planes(PLANES * 64 * 128, 0);
  std::vector<bf16> rows(64 * 128);
  for (auto& x : rows) x = 0x3f80;
  volatile bf16 sink = 0;
  // warmup
  for (int r = 0; r < 1000; ++r) scatter(&planes[(r % PLANES) * 64 * 128], r % 64, &rows[(r % 64) * 128]);
  const long N = 3000000;
  auto t0 = std::chrono::steady_clock::now();
  for (long r = 0; r < N; ++r)
    scatter(&planes[(r % PLANES) * 64 * 128], r % 64, &rows[(r % 64) * 128]);
  auto t1 = std::chrono::steady_clock::now();
  sink = planes[12345];
  double ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / N;
  printf("scatter_k_mirror: %.1f ns per token-row (head 128)\n", ns);
  // Per prefill token: 36 layers x 8 kv_heads scatters
  printf("per prefill token (36 layers x 8 heads): %.2f us\n", ns * 36 * 8 / 1000.0);
  (void)sink;
  return 0;
}
