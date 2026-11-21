/* probe.c - compile-only candidates for k_copy. */
#include <arm_neon.h>
#include <stddef.h>
#include <stdint.h>
#define LOADS(P) \
    uint64x2_t v0 = vld1q_u64(P + 0), v1 = vld1q_u64(P + 2), v2 = vld1q_u64(P + 4), v3 = vld1q_u64(P + 6), \
               v4 = vld1q_u64(P + 8), v5 = vld1q_u64(P + 10), v6 = vld1q_u64(P + 12), v7 = vld1q_u64(P + 14), \
               v8 = vld1q_u64(P + 16), v9 = vld1q_u64(P + 18), v10 = vld1q_u64(P + 20), v11 = vld1q_u64(P + 22), \
               v12 = vld1q_u64(P + 24), v13 = vld1q_u64(P + 26), v14 = vld1q_u64(P + 28), v15 = vld1q_u64(P + 30)
#define BARRIER \
    __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3), "w"(v4), "w"(v5), "w"(v6), "w"(v7), \
                     "w"(v8), "w"(v9), "w"(v10), "w"(v11), "w"(v12), "w"(v13), "w"(v14), "w"(v15))
#define STORES(P) \
    vst1q_u64(P + 0, v0); vst1q_u64(P + 2, v1); vst1q_u64(P + 4, v2); vst1q_u64(P + 6, v3); \
    vst1q_u64(P + 8, v4); vst1q_u64(P + 10, v5); vst1q_u64(P + 12, v6); vst1q_u64(P + 14, v7); \
    vst1q_u64(P + 16, v8); vst1q_u64(P + 18, v9); vst1q_u64(P + 20, v10); vst1q_u64(P + 22, v11); \
    vst1q_u64(P + 24, v12); vst1q_u64(P + 26, v13); vst1q_u64(P + 28, v14); vst1q_u64(P + 30, v15)

/* candidate 1: copy with the barrier between the loads and the stores */
void copy_barrier(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    uint64_t *dp = d; const uint64_t *sp = s; const uint64_t *end = s + n;
    do { LOADS(sp); BARRIER; STORES(dp); sp += 32; dp += 32; } while (sp < end);
}
/* candidate 2: copy without the barrier */
void copy_plain(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    uint64_t *dp = d; const uint64_t *sp = s; const uint64_t *end = s + n;
    do { LOADS(sp); STORES(dp); sp += 32; dp += 32; } while (sp < end);
}
/* candidate 3: copy without the barrier and without restrict */
void copy_plain_norestrict(uint64_t *d, const uint64_t *s, size_t n)
{
    uint64_t *dp = d; const uint64_t *sp = s; const uint64_t *end = s + n;
    do { LOADS(sp); STORES(dp); sp += 32; dp += 32; } while (sp < end);
}
