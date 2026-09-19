#include <immintrin.h>
#include <cstddef>
#include <cstdio>
constexpr size_t LANES_16 = 16;
void transpose_16x16_epi32(__m512i (&r)[LANES_16]) noexcept {
  // Selectors of _mm512_shuffle_i32x4: the even 128-bit quarters of both
  // inputs (0x88) or the odd quarters (0xdd).
  constexpr int EVEN_QUARTERS_0X88 = 0x88;
  constexpr int ODD_QUARTERS_0XDD = 0xdd;
  __m512i t[LANES_16];
  for (size_t i = 0; i < LANES_16 / 2; ++i) {
    t[2 * i] = _mm512_unpacklo_epi32(r[2 * i], r[2 * i + 1]);
    t[2 * i + 1] = _mm512_unpackhi_epi32(r[2 * i], r[2 * i + 1]);
  }
  for (size_t i = 0; i < LANES_16 / 4; ++i) {
    r[4 * i] = _mm512_unpacklo_epi64(t[4 * i], t[4 * i + 2]);
    r[4 * i + 1] = _mm512_unpackhi_epi64(t[4 * i], t[4 * i + 2]);
    r[4 * i + 2] = _mm512_unpacklo_epi64(t[4 * i + 1], t[4 * i + 3]);
    r[4 * i + 3] = _mm512_unpackhi_epi64(t[4 * i + 1], t[4 * i + 3]);
  }
  for (size_t i = 0; i < LANES_16 / 4; ++i) {
    t[i] = _mm512_shuffle_i32x4(r[i], r[i + 4], EVEN_QUARTERS_0X88);
    t[i + 4] = _mm512_shuffle_i32x4(r[i], r[i + 4], ODD_QUARTERS_0XDD);
    t[i + 8] = _mm512_shuffle_i32x4(r[i + 8], r[i + 12], EVEN_QUARTERS_0X88);
    t[i + 12] = _mm512_shuffle_i32x4(r[i + 8], r[i + 12], ODD_QUARTERS_0XDD);
  }
  for (size_t i = 0; i < LANES_16 / 2; ++i) {
    r[i] = _mm512_shuffle_i32x4(t[i], t[i + 8], EVEN_QUARTERS_0X88);
    r[i + 8] = _mm512_shuffle_i32x4(t[i], t[i + 8], ODD_QUARTERS_0XDD);
  }
}
int main() {
  alignas(64) unsigned rows[LANES_16][LANES_16];
  __m512i regs[LANES_16];
  for (size_t r = 0; r < LANES_16; ++r) {
    for (size_t c = 0; c < LANES_16; ++c) {
      rows[r][c] = r * LANES_16 + c;
    }
    regs[r] = _mm512_loadu_si512(rows[r]);
  }
  transpose_16x16_epi32(regs);
  for (size_t r = 0; r < LANES_16; ++r) {
    _mm512_storeu_si512(rows[r], regs[r]);
    for (size_t c = 0; c < LANES_16; ++c) {
      if (rows[r][c] != c * LANES_16 + r) {
        std::printf("FAIL at row %zu column %zu\n", r, c);
        return 1;
      }
    }
  }
  std::puts("PASS: extracted production transpose, all 256 dword positions");
}
