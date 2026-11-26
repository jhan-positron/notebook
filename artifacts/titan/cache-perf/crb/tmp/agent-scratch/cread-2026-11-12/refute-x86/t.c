#include <emmintrin.h>
#include <stddef.h>
#include <stdint.h>
void plain(const uint64_t *a, size_t n){ for(size_t i=0;i<n;i+=2){ __m128i v=_mm_loadu_si128((const __m128i*)(a+i)); (void)v; } }
void one(const uint64_t *a, size_t n){ for(size_t i=0;i<n;i+=2){ __m128i v=_mm_loadu_si128((const __m128i*)(a+i)); __asm__ volatile("" : : "x"(v)); } }
void four(const uint64_t *a, size_t n){ const uint64_t*p=a,*e=a+n; do{ __m128i v0=_mm_loadu_si128((const __m128i*)(p)),v1=_mm_loadu_si128((const __m128i*)(p+2)),v2=_mm_loadu_si128((const __m128i*)(p+4)),v3=_mm_loadu_si128((const __m128i*)(p+6));
 __asm__ volatile("" : : "x"(v0),"x"(v1),"x"(v2),"x"(v3)); p+=8;}while(p<e);}
void same(const uint64_t *a){ __m128i v0=_mm_loadu_si128((const __m128i*)a), v1=_mm_loadu_si128((const __m128i*)a); __asm__ volatile("" : : "x"(v0),"x"(v1)); }
void vol(const uint64_t *a, size_t n){ const volatile uint64_t*p=a; for(size_t i=0;i<n;i+=4) for(int j=0;j<4;j++) (void)p[i+j]; }
