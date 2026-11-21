/* Candidates for a read loop written in C that only loads, like k_asmread.
 * Compile check only. Not part of bench/bandwidth.c. */
#include <arm_neon.h>
#include <stddef.h>
#include <stdint.h>

/* v1: 16 loads of 16 B, then one empty asm statement that names all 16
 * values as inputs. The statement emits no instruction. */
__attribute__((noinline)) void k_cread(const uint64_t *a, size_t n)
{
    const uint64_t *p = a;
    const uint64_t *end = a + n;
    do {
        uint64x2_t v0 = vld1q_u64(p + 0);
        uint64x2_t v1 = vld1q_u64(p + 2);
        uint64x2_t v2 = vld1q_u64(p + 4);
        uint64x2_t v3 = vld1q_u64(p + 6);
        uint64x2_t v4 = vld1q_u64(p + 8);
        uint64x2_t v5 = vld1q_u64(p + 10);
        uint64x2_t v6 = vld1q_u64(p + 12);
        uint64x2_t v7 = vld1q_u64(p + 14);
        uint64x2_t v8 = vld1q_u64(p + 16);
        uint64x2_t v9 = vld1q_u64(p + 18);
        uint64x2_t v10 = vld1q_u64(p + 20);
        uint64x2_t v11 = vld1q_u64(p + 22);
        uint64x2_t v12 = vld1q_u64(p + 24);
        uint64x2_t v13 = vld1q_u64(p + 26);
        uint64x2_t v14 = vld1q_u64(p + 28);
        uint64x2_t v15 = vld1q_u64(p + 30);
        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),
                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),
                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),
                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));
        p += 32;
    } while (p < end);
}

/* v2: same, written as two loops. One empty asm statement per load. */
__attribute__((noinline)) void k_cread_loop(const uint64_t *a, size_t n)
{
    for (size_t i = 0; i < n; i += 32)
        for (int j = 0; j < 32; j += 2) {
            uint64x2_t v = vld1q_u64(a + i + j);
            __asm__ volatile("" : : "w"(v));
        }
}

/* v3: no asm statement at all. Expected: gcc deletes the loads. */
__attribute__((noinline)) void k_cread_plain(const uint64_t *a, size_t n)
{
    for (size_t i = 0; i < n; i += 32)
        for (int j = 0; j < 32; j += 2) {
            uint64x2_t v = vld1q_u64(a + i + j);
            (void)v;
        }
}

/* v4: ISO C only, volatile access. Expected: 8 B loads, no 16 B loads. */
__attribute__((noinline)) void k_cread_volatile(const uint64_t *a, size_t n)
{
    const volatile uint64_t *p = a;
    for (size_t i = 0; i < n; i += 16)
        for (int j = 0; j < 16; j++)
            (void)p[i + j];
}
