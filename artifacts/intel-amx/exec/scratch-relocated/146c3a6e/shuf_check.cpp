#include <immintrin.h>
__m512 f(__m512 a, __m512 b) { return _mm512_shuffle_f32x4(a, b, 0x88); }
__m512 g(__m512 a, __m512 b) { return _mm512_shuffle_ps(a, b, 0x88); }
