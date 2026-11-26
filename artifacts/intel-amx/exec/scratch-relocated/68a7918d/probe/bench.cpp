#include <chrono>
#include <cstddef>
#include <cstdio>
#include <algorithm>
float fill_default(); float fill_tag(); float fill_visible();
void rows_copy(float* __restrict, const float* __restrict, float);
void rows_view(float* __restrict, const float* __restrict, float);
static float g = 1.0f;
void kernel(float* s) noexcept { for (size_t i = 0; i < 16 * 64; i++) s[i] = g; }
float consume(const float* s) noexcept { return s[0] + s[1023]; }
template <class F> static double ns_per_call(F f) {
  double best = 1e30;
  for (int rep = 0; rep < 25; rep++) {
    const int n = 200000;
    auto t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < n; i++) f();
    auto t1 = std::chrono::steady_clock::now();
    best = std::min(best, std::chrono::duration<double, std::nano>(t1 - t0).count() / n);
  }
  return best;
}
int main() {
  alignas(64) static float v[16 * 128], o[16 * 128];
  for (size_t i = 0; i < 16 * 128; i++) { v[i] = 0.5f; o[i] = 0.25f; }
  volatile float sink = 0;
  double a = ns_per_call([&] { sink = sink + fill_default(); });
  double b = ns_per_call([&] { sink = sink + fill_tag(); });
  double c = ns_per_call([&] { sink = sink + fill_visible(); });
  double d = ns_per_call([&] { rows_copy(v, o, 0.999f); });
  double e = ns_per_call([&] { rows_view(v, o, 0.999f); });
  std::printf("fill_default %.1f ns  fill_tag %.1f ns  fill_visible %.1f ns\n", a, b, c);
  std::printf("rows_copy %.1f ns  rows_view %.1f ns\n", d, e);
}
