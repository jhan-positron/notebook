#include <array>
#include <cstddef>
#include <cstring>
#include <memory>

struct uninitialized_t {};
inline constexpr uninitialized_t uninitialized{};

// Same shape as tron's tensor<N>: the default constructor value-initializes.
template <size_t N>
struct row_t {
  alignas(64) std::array<float, N> data;
  row_t() : data() {}
  row_t(uninitialized_t) noexcept {}
};
// Same shape as tron's tensor<d0, d1>: construct_at value-initializes each row.
template <size_t R, size_t N>
struct mat_t {
  union { alignas(64) std::array<row_t<N>, R> data; };
  mat_t() noexcept { std::construct_at(&data); }
  mat_t(uninitialized_t) noexcept {}
};

void kernel(float* s) noexcept;          // other file: writes all 16 x 64 floats
float consume(const float* s) noexcept;  // other file

// Pattern 1: default-constructed buffer, then a writer the compiler cannot see.
float fill_default() {
  mat_t<16, 64> s;
  kernel(&s.data[0].data[0]);
  return consume(&s.data[0].data[0]);
}
float fill_tag() {
  mat_t<16, 64> s{uninitialized};
  kernel(&s.data[0].data[0]);
  return consume(&s.data[0].data[0]);
}
// Same buffer, but the overwrite is visible inside this function.
float fill_visible() {
  mat_t<16, 64> s;
  for (size_t r = 0; r < 16; r++)
    for (size_t i = 0; i < 64; i++) s.data[r].data[i] = -1.0f;
  return consume(&s.data[0].data[0]);
}

// Pattern 2: copy each row into a stack temporary before use.
void rows_copy(float* __restrict v_star, const float* __restrict amx_o, float c) {
  for (size_t h = 0; h < 16; h++) {
    row_t<128> scratch;
    std::memcpy(&scratch.data[0], amx_o + h * 128, 128 * sizeof(float));
    for (size_t i = 0; i < 128; i++)
      v_star[h * 128 + i] = v_star[h * 128 + i] * c + scratch.data[i];
  }
}
void rows_view(float* __restrict v_star, const float* __restrict amx_o, float c) {
  for (size_t h = 0; h < 16; h++) {
    const float* row = amx_o + h * 128;
    for (size_t i = 0; i < 128; i++)
      v_star[h * 128 + i] = v_star[h * 128 + i] * c + row[i];
  }
}
