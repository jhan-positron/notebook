#include <cstddef>
#include <cstdio>
#include <immintrin.h>
#include <vector>
constexpr size_t TILE_ROWS_16 = 16, TILE_FP32S = 256, GROUP_HEADS_16 = 16;
constexpr int LANES_EVEN_0X88 = 0x88;
constexpr int LANES_ODD_0XDD = 0xdd;
// A 128-bit lane holds 4 fp32 values: lane `lane` of u[.][0..3] holds tile
// columns 4 * lane .. 4 * lane + 3, which become 4 consecutive output rows.
constexpr size_t ROWS_PER_LANE_4 = 4;

template <int lane>
inline void store_transposed_rows(
    const __m512 (&u)[TILE_ROWS_16 / ROWS_PER_LANE_4][ROWS_PER_LANE_4],
    float* s_block,
    size_t s_stride_floats) {
  constexpr int pair_sel = (lane & 1) ? LANES_ODD_0XDD : LANES_EVEN_0X88;
  constexpr int quad_sel = (lane & 2) ? LANES_ODD_0XDD : LANES_EVEN_0X88;
  float* const s_rows = s_block + lane * ROWS_PER_LANE_4 * s_stride_floats;
  for (size_t k = 0; k < ROWS_PER_LANE_4; k++) {
    __m512 p = _mm512_shuffle_f32x4(u[0][k], u[1][k], pair_sel);
    __m512 q2 = _mm512_shuffle_f32x4(u[2][k], u[3][k], pair_sel);
    _mm512_storeu_ps(
        s_rows + k * s_stride_floats, _mm512_shuffle_f32x4(p, q2, quad_sel));
  }
}

template<size_t group_heads>
void transpose(const float* s_transposed, float* s, size_t s_stride_floats) {
  for (int r = 0; r < 4; r++) {
    const float* src = s_transposed + r * TILE_FP32S;
    __m512 u[4][4];
    // row_group: which 4-row group of the 16x16 tile this pass interleaves
    // (rows 4*row_group .. 4*row_group+3).
    for (int row_group = 0; row_group < 4; row_group++) {
      __m512 r0 = _mm512_loadu_ps(src + (4 * row_group + 0) * 16);
      __m512 r1 = _mm512_loadu_ps(src + (4 * row_group + 1) * 16);
      __m512 r2 = _mm512_loadu_ps(src + (4 * row_group + 2) * 16);
      __m512 r3 = _mm512_loadu_ps(src + (4 * row_group + 3) * 16);
      __m512 t0 = _mm512_unpacklo_ps(r0, r1);
      __m512 t1 = _mm512_unpackhi_ps(r0, r1);
      __m512 t2 = _mm512_unpacklo_ps(r2, r3);
      __m512 t3 = _mm512_unpackhi_ps(r2, r3);
      u[row_group][0] = _mm512_castpd_ps(
          _mm512_unpacklo_pd(_mm512_castps_pd(t0), _mm512_castps_pd(t2)));
      u[row_group][1] = _mm512_castpd_ps(
          _mm512_unpackhi_pd(_mm512_castps_pd(t0), _mm512_castps_pd(t2)));
      u[row_group][2] = _mm512_castpd_ps(
          _mm512_unpacklo_pd(_mm512_castps_pd(t1), _mm512_castps_pd(t3)));
      u[row_group][3] = _mm512_castpd_ps(
          _mm512_unpackhi_pd(_mm512_castps_pd(t1), _mm512_castps_pd(t3)));
    }
    float* const s_block = s + r * 16;
    store_transposed_rows<0>(u, s_block, s_stride_floats);
    if constexpr (group_heads == GROUP_HEADS_16) {
      store_transposed_rows<1>(u, s_block, s_stride_floats);
      store_transposed_rows<2>(u, s_block, s_stride_floats);
      store_transposed_rows<3>(u, s_block, s_stride_floats);
    }
  }
}
int main() {
  constexpr float SENTINEL = -12345;
  alignas(64) float source[64 * 16];
  for(size_t t=0; t<64; ++t) for(size_t h=0; h<16; ++h) source[t*16+h]=float(1000*t+h);
  size_t checked=0;
  for(size_t stride : {size_t(64), size_t(80)}) {
    for(size_t heads : {size_t(4), size_t(16)}) {
      std::vector<float> out(18*stride,SENTINEL);
      float* target = out.data()+stride;
      if(heads==4) transpose<4>(source,target,stride); else transpose<16>(source,target,stride);
      for(size_t row=0; row<18; ++row) for(size_t col=0; col<stride; ++col) {
        float expected = (row>=1 && row<=heads && col<64) ? float(1000*col+(row-1)) : SENTINEL;
        if(out[row*stride+col]!=expected) {std::printf("FAIL heads=%zu stride=%zu row=%zu col=%zu got=%f expected=%f\n",heads,stride,row,col,out[row*stride+col],expected);return 1;}
        ++checked;
      }
    }
  }
  std::printf("PASS: %zu positions across 4/16 heads and 64/80 float row strides; all source coordinates and guard cells match.\n",checked);
}
