/*
 * robsize.c - measure how many filler instructions fit in the out-of-order
 * window of one AArch64 core.
 *
 * Method (Henry Wong, "Measuring Reorder Buffer Capacity", 2013):
 * each loop iteration does two independent cache-missing loads. N filler
 * instructions follow EACH load. While the fillers fit in the window, the
 * two misses run at the same time and one iteration costs about one miss.
 * When the fillers no longer fit, the second load cannot enter the window
 * before the first load retires. The misses then run one after the other,
 * and one iteration costs about two misses. The N at that step is the
 * capacity for that filler kind.
 *
 * Generated loop (x0 = chain A pointer, x1 = chain B pointer,
 * x2 = iteration count, x3 = hot 256 B scratch buffer):
 *
 *     stp d8..d15 to the stack, x4 = x5 = x6 = 0   (7 instructions, once)
 *   loop:
 *     ldr  x0, [x0]                   load A: cache miss, chain A
 *     <N filler units>
 *     ldr  x1, [x1]                   load B: cache miss, chain B
 *     <N filler units>
 *     sub  x2, x2, #1
 *     cbnz x2, loop
 *     ldp d8..d15 from the stack, ret (5 instructions, once)
 *
 * No instruction word is encoded by hand. Every instruction is assembled
 * by the assembler in the "templates" block below, and the code generator
 * copies the 4-byte words. The only PC-relative copied instruction is the
 * "b.lo" of the k_* kinds, which branches to the instruction after itself,
 * so a copy is valid at any address. The only word changed at run time is
 * the offset field (bits 23:5) of the "cbnz" loop branch. main() checks
 * that patch against an assembler-encoded "cbnz" before any measurement.
 *
 * To review the encodings on the target:  objdump -d robsize | less
 * and search for the labels t_nop, t_vadd, ... (all in .text.robtmpl).
 *
 * Build: gcc -O2 -o robsize robsize.c        (AArch64 Linux only)
 */
#define _GNU_SOURCE
#include <errno.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#if !defined(__aarch64__) && !defined(ROBSIZE_SYNTAX_CHECK)
#error "robsize.c runs on AArch64 only"
#endif

#define MAX_CPU 119 /* CPUs above this number are refused */

/* ------------------------------------------------------------------ */
/* Templates: the assembler encodes every instruction used at run time. */
/* ------------------------------------------------------------------ */
#ifdef __aarch64__
__asm__(
"    .pushsection .text.robtmpl,\"ax\",%progbits\n"
"    .balign 4\n"
/* skeleton */
"t_prologue:\n" /* v8..v15 low halves are callee-saved (AAPCS64) */
"    stp d8, d9, [sp, #-64]!\n"
"    stp d10, d11, [sp, #16]\n"
"    stp d12, d13, [sp, #32]\n"
"    stp d14, d15, [sp, #48]\n"
/* x4, x5, x6 = 0 for the kernel-body kinds (k_*): "cmp x4, x5" then always
 * gives "not lower", so their "b.lo" is never taken */
"    mov x4, #0\n"
"    mov x5, #0\n"
"    mov x6, #0\n"
"t_prologue_end:\n"
"t_load_a:\n"
"    ldr x0, [x0]\n"
"t_load_a_end:\n"
"t_load_b:\n"
"    ldr x1, [x1]\n"
"t_load_b_end:\n"
"t_dec:\n"
"    sub x2, x2, #1\n"
"t_dec_end:\n"
"t_cbnz0:\n" /* offset field = 0; patched at run time */
"    cbnz x2, t_cbnz0\n"
"t_cbnz0_end:\n"
"t_epilogue:\n"
"    ldp d10, d11, [sp, #16]\n"
"    ldp d12, d13, [sp, #32]\n"
"    ldp d14, d15, [sp, #48]\n"
"    ldp d8, d9, [sp], #64\n"
"    ret\n"
"t_epilogue_end:\n"
/* reference for the cbnz patch check: branch back by 300 instructions */
"t_chk_target:\n"
"    .rept 300\n"
"    nop\n"
"    .endr\n"
"t_chk_cbnz:\n"
"    cbnz x2, t_chk_target\n"
"t_chk_cbnz_end:\n"
/* filler kind: nop */
"t_nop:\n"
"    nop\n"
"t_nop_end:\n"
/* filler kind: vadd - NEON add, 16 accumulators v16..v31, source v0 */
"t_vadd:\n"
"    add v16.2d, v16.2d, v0.2d\n"
"    add v17.2d, v17.2d, v0.2d\n"
"    add v18.2d, v18.2d, v0.2d\n"
"    add v19.2d, v19.2d, v0.2d\n"
"    add v20.2d, v20.2d, v0.2d\n"
"    add v21.2d, v21.2d, v0.2d\n"
"    add v22.2d, v22.2d, v0.2d\n"
"    add v23.2d, v23.2d, v0.2d\n"
"    add v24.2d, v24.2d, v0.2d\n"
"    add v25.2d, v25.2d, v0.2d\n"
"    add v26.2d, v26.2d, v0.2d\n"
"    add v27.2d, v27.2d, v0.2d\n"
"    add v28.2d, v28.2d, v0.2d\n"
"    add v29.2d, v29.2d, v0.2d\n"
"    add v30.2d, v30.2d, v0.2d\n"
"    add v31.2d, v31.2d, v0.2d\n"
"t_vadd_end:\n"
/* filler kind: vadd_nd - NEON add with no dependency between fillers:
 * destinations v16..v31, sources v0 and v1 are never written */
"t_vadd_nd:\n"
"    add v16.2d, v0.2d, v1.2d\n"
"    add v17.2d, v0.2d, v1.2d\n"
"    add v18.2d, v0.2d, v1.2d\n"
"    add v19.2d, v0.2d, v1.2d\n"
"    add v20.2d, v0.2d, v1.2d\n"
"    add v21.2d, v0.2d, v1.2d\n"
"    add v22.2d, v0.2d, v1.2d\n"
"    add v23.2d, v0.2d, v1.2d\n"
"    add v24.2d, v0.2d, v1.2d\n"
"    add v25.2d, v0.2d, v1.2d\n"
"    add v26.2d, v0.2d, v1.2d\n"
"    add v27.2d, v0.2d, v1.2d\n"
"    add v28.2d, v0.2d, v1.2d\n"
"    add v29.2d, v0.2d, v1.2d\n"
"    add v30.2d, v0.2d, v1.2d\n"
"    add v31.2d, v0.2d, v1.2d\n"
"t_vadd_nd_end:\n"
/* filler kind: iadd - integer add, 14 accumulators x4..x17, source x3 */
"t_iadd:\n"
"    add x4, x4, x3\n"
"    add x5, x5, x3\n"
"    add x6, x6, x3\n"
"    add x7, x7, x3\n"
"    add x8, x8, x3\n"
"    add x9, x9, x3\n"
"    add x10, x10, x3\n"
"    add x11, x11, x3\n"
"    add x12, x12, x3\n"
"    add x13, x13, x3\n"
"    add x14, x14, x3\n"
"    add x15, x15, x3\n"
"    add x16, x16, x3\n"
"    add x17, x17, x3\n"
"t_iadd_end:\n"
/* filler kind: iadd_nd - integer add with no dependency between fillers:
 * destinations x4..x17, source x3 is never written */
"t_iadd_nd:\n"
"    add x4, x3, x3\n"
"    add x5, x3, x3\n"
"    add x6, x3, x3\n"
"    add x7, x3, x3\n"
"    add x8, x3, x3\n"
"    add x9, x3, x3\n"
"    add x10, x3, x3\n"
"    add x11, x3, x3\n"
"    add x12, x3, x3\n"
"    add x13, x3, x3\n"
"    add x14, x3, x3\n"
"    add x15, x3, x3\n"
"    add x16, x3, x3\n"
"    add x17, x3, x3\n"
"t_iadd_nd_end:\n"
/* filler kind: ldrq - one 16-byte load of the hot scratch buffer */
"t_ldrq:\n"
"    ldr q16, [x3]\n"
"t_ldrq_end:\n"
/* filler kind: ldpq - one 32-byte pair load of the hot scratch buffer */
"t_ldpq:\n"
"    ldp q16, q17, [x3]\n"
"t_ldpq_end:\n"
/* filler kind: iter256 - the benchmark body, 8 pair loads = 256 bytes */
"t_iter256:\n"
"    ldp q0, q1, [x3]\n"
"    ldp q2, q3, [x3, #32]\n"
"    ldp q4, q5, [x3, #64]\n"
"    ldp q6, q7, [x3, #96]\n"
"    ldp q8, q9, [x3, #128]\n"
"    ldp q10, q11, [x3, #160]\n"
"    ldp q12, q13, [x3, #192]\n"
"    ldp q14, q15, [x3, #224]\n"
"t_iter256_end:\n"
"    .popsection\n"
);

/*
 * Kernel-body kinds (k_*): ONE unit is one loop body of a benchmark kernel
 * of bwx12.c, in the instruction order of that kernel. Differences from the
 * kernel, all needed by this harness:
 *   - the loads and prefetches read the hot scratch buffer [x3], not [x4],
 *     so they all hit L1 and do not depend on the pointer add;
 *   - the loop end "add x4,x4,#B; cmp x4,x5; b.lo" is kept, but the branch
 *     goes to the next instruction and is never taken (x5 = 0);
 *   - the accumulators v16-v31 are not initialized (integer adds, so the
 *     values do not change the timing).
 * "b.lo 1f" is PC-relative with offset +4, so a copy is valid anywhere.
 */
#define KT(name, body) "t_" #name ":\n" body "t_" #name "_end:\n"
#define LDP4 \
    "ldp q0, q1, [x3]\n" \
    "ldp q2, q3, [x3, #32]\n" \
    "ldp q4, q5, [x3, #64]\n" \
    "ldp q6, q7, [x3, #96]\n"
#define LDP8 LDP4 \
    "ldp q8, q9, [x3, #128]\n" \
    "ldp q10, q11, [x3, #160]\n" \
    "ldp q12, q13, [x3, #192]\n" \
    "ldp q14, q15, [x3, #224]\n"
#define LDR4 \
    "ldr q0, [x3]\n" \
    "ldr q1, [x3, #64]\n" \
    "ldr q2, [x3, #128]\n" \
    "ldr q3, [x3, #192]\n"
#define NOPS(n) ".rept " #n "\nnop\n.endr\n"
#define TAIL(bytes) "add x4, x4, #" #bytes "\ncmp x4, x5\nb.lo 1f\n1:\n"
#define VADD(a, b) "add v" #a ".2d, v" #a ".2d, v" #b ".2d\n"
#define K_NOP(n) KT(k_nop##n, LDP8 NOPS(n) TAIL(256))
#define K_SP(n) KT(k_sp##n, LDP4 NOPS(n) TAIL(128))
__asm__(
"    .pushsection .text.robtmpl,\"ax\",%progbits\n"
"    .balign 4\n"
/* read_nopN: 8 ldp, N nop, add, cmp, b.lo */
K_NOP(32) K_NOP(48) K_NOP(56) K_NOP(64) K_NOP(72) K_NOP(80) K_NOP(88)
K_NOP(96) K_NOP(112) K_NOP(128) K_NOP(160) K_NOP(192) K_NOP(256)
/* read_daddK: 8 ldp, K adds that take loaded registers */
KT(k_dadd2, LDP8 VADD(16, 0) VADD(17, 8) TAIL(256))
KT(k_dadd4, LDP8 VADD(16, 0) VADD(17, 4) VADD(18, 8) VADD(19, 12) TAIL(256))
KT(k_dadd8, LDP8
   VADD(16, 0) VADD(17, 2) VADD(18, 4) VADD(19, 6)
   VADD(20, 8) VADD(21, 10) VADD(22, 12) VADD(23, 14) TAIL(256))
KT(k_dadd16, LDP8
   VADD(16, 0) VADD(17, 1) VADD(18, 2) VADD(19, 3)
   VADD(20, 4) VADD(21, 5) VADD(22, 6) VADD(23, 7)
   VADD(16, 8) VADD(17, 9) VADD(18, 10) VADD(19, 11)
   VADD(20, 12) VADD(21, 13) VADD(22, 14) VADD(23, 15) TAIL(256))
/* read_iadd16: 8 ldp, 16 adds that take no loaded register */
KT(k_iadd16, LDP8
   VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27)
   VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31)
   VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27)
   VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31) TAIL(256))
/* oldread, 128 B per unit, order of the compiler listing: ldp, counter add,
 * 3 ldp, pointer add, 8 adds (one loaded register each), cmp, branch.
 * 16 instructions, as the listing has. */
KT(k_old,
   "ldp q0, q1, [x3]\n"
   "add x6, x6, #1\n"
   "ldp q2, q3, [x3, #32]\n"
   "ldp q4, q5, [x3, #64]\n"
   "ldp q6, q7, [x3, #96]\n"
   "add x4, x4, #128\n"
   VADD(16, 0) VADD(17, 1) VADD(18, 2) VADD(19, 3)
   VADD(20, 4) VADD(21, 5) VADD(22, 6) VADD(23, 7)
   "cmp x4, x5\nb.lo 1f\n1:\n")
/* read_sparse and read_spN: 4 ldp, N nop, add, cmp, b.lo per 128 B */
K_SP(9) K_SP(24) K_SP(32) K_SP(40) K_SP(48) K_SP(56)
/* read_1pl: one 16 B load per 64 B line, 256 B per unit */
KT(k_1pl, LDR4 TAIL(256))
KT(k_1pl_nop96, LDR4 NOPS(96) TAIL(256))
/* read_pf2048: 8 ldp, 4 prefetches. Here the prefetches name the hot
 * scratch lines, so they take a slot and do not miss. */
KT(k_pf2048, LDP8
   "prfm pldl1keep, [x3]\n"
   "prfm pldl1keep, [x3, #64]\n"
   "prfm pldl1keep, [x3, #128]\n"
   "prfm pldl1keep, [x3, #192]\n" TAIL(256))
"    .popsection\n"
);
#endif

#define TMPL(name)                                                         \
    extern const uint32_t name[] __attribute__((visibility("hidden")));    \
    extern const uint32_t name##_end[] __attribute__((visibility("hidden")))

TMPL(t_prologue);
TMPL(t_load_a);
TMPL(t_load_b);
TMPL(t_dec);
TMPL(t_cbnz0);
TMPL(t_epilogue);
TMPL(t_chk_cbnz);
TMPL(t_nop);
TMPL(t_vadd);
TMPL(t_vadd_nd);
TMPL(t_iadd);
TMPL(t_iadd_nd);
TMPL(t_ldrq);
TMPL(t_ldpq);
TMPL(t_iter256);
#define KERNEL_KINDS(X) \
    X(k_nop32, 16) X(k_nop48, 16) X(k_nop56, 16) X(k_nop64, 16) \
    X(k_nop72, 16) X(k_nop80, 16) X(k_nop88, 16) X(k_nop96, 16) \
    X(k_nop112, 16) X(k_nop128, 16) X(k_nop160, 12) X(k_nop192, 12) \
    X(k_nop256, 12) \
    X(k_dadd2, 16) X(k_dadd4, 16) X(k_dadd8, 16) X(k_dadd16, 16) \
    X(k_iadd16, 16) X(k_old, 24) \
    X(k_sp9, 30) X(k_sp24, 30) X(k_sp32, 30) X(k_sp40, 30) X(k_sp48, 30) \
    X(k_sp56, 30) \
    X(k_1pl, 60) X(k_1pl_nop96, 16) X(k_pf2048, 16)
#define X(name, nmax) TMPL(t_##name);
KERNEL_KINDS(X)
#undef X

/*
 * One filler kind.
 * unit: instructions emitted per count of N. 0 means the whole template
 * (see kunit()).
 * The i-th emitted instruction is tmpl[i % period].
 */
struct kind {
    const char *name;
    const uint32_t *tmpl, *tmpl_end;
    long unit;
    long nmin, nmax, nstep; /* default list of N */
    const char *what;
};

static const struct kind kinds[] = {
    { "nop",     t_nop,     t_nop_end,     1, 0, 1200, 10,
      "nop (reorder-buffer entries)" },
    { "vadd",    t_vadd,    t_vadd_end,    1, 0, 600, 5,
      "add vA.2d,vA.2d,v0.2d, 16 accumulators (free vector registers)" },
    { "iadd",    t_iadd,    t_iadd_end,    1, 0, 1200, 10,
      "add xA,xA,x3, 14 accumulators (free integer registers)" },
    { "ldrq",    t_ldrq,    t_ldrq_end,    1, 0, 600, 5,
      "ldr q16,[x3] (load-queue entries or vector registers)" },
    { "ldpq",    t_ldpq,    t_ldpq_end,    1, 0, 300, 2,
      "ldp q16,q17,[x3] (2 vector register writes each)" },
    { "iter256", t_iter256, t_iter256_end, 8, 0, 60, 1,
      "8 x ldp q0..q15 = one 256 B benchmark iteration per N" },
    { "vadd_nd", t_vadd_nd, t_vadd_nd_end, 1, 0, 600, 5,
      "add vA.2d,v0.2d,v1.2d, no dependency chain (control for vadd)" },
    { "iadd_nd", t_iadd_nd, t_iadd_nd_end, 1, 0, 1200, 10,
      "add xA,x3,x3, no dependency chain (control for iadd)" },
#define X(name, nmax) \
    { #name, t_##name, t_##name##_end, 0, 0, nmax, 1, \
      "one loop body of the benchmark kernel per N, loads from hot scratch" },
    KERNEL_KINDS(X)
#undef X
};
#define NKINDS ((int)(sizeof kinds / sizeof kinds[0]))

/* Instructions per count of N. */
static long kunit(const struct kind *k)
{
    return k->unit ? k->unit : (long)(k->tmpl_end - k->tmpl);
}

/* Is `name` "all" or one entry of the comma-separated list `list`? */
static int kind_selected(const char *list, const char *name)
{
    size_t len = strlen(name);
    if (!strcmp(list, "all"))
        return 1;
    for (const char *p = list; *p;) {
        const char *e = strchr(p, ',');
        size_t l = e ? (size_t)(e - p) : strlen(p);
        if (l == len && !strncmp(p, name, len))
            return 1;
        p += l + (e != NULL);
    }
    return 0;
}

/* ------------------------------------------------------------------ */

static void die(const char *msg)
{
    fprintf(stderr, "robsize: %s: %s\n", msg, strerror(errno));
    exit(1);
}

static void fail(const char *msg)
{
    fprintf(stderr, "robsize: %s\n", msg);
    exit(1);
}

static double now_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e9 + (double)ts.tv_nsec;
}

static uint64_t rng_state;

static uint64_t rng(void) /* xorshift64* */
{
    rng_state ^= rng_state >> 12;
    rng_state ^= rng_state << 25;
    rng_state ^= rng_state >> 27;
    return rng_state * 0x2545F4914F6CDD1DULL;
}

/*
 * Build one pointer chain: `bytes` of memory, one 8-byte pointer every
 * `stride` bytes. The pointers form ONE random cycle through all nodes
 * (Sattolo's shuffle), so a chase never repeats a node before it has
 * visited all of them. Returns the address of node 0.
 */
static uint64_t build_chain(size_t bytes, size_t stride, uint64_t seed)
{
    const size_t huge = 2UL << 20;
    char *raw = mmap(NULL, bytes + huge, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED)
        die("mmap chain");
    char *p = (char *)(((uintptr_t)raw + huge - 1) & ~(huge - 1));
    if (madvise(p, bytes, MADV_HUGEPAGE) != 0)
        fprintf(stderr, "robsize: warning: madvise(MADV_HUGEPAGE): %s\n",
                strerror(errno));

    size_t n = bytes / stride;
    if (n < 2)
        fail("chain needs at least 2 nodes");
#define NODE(i) (*(uint64_t *)(p + (size_t)(i) * stride))
    for (size_t i = 0; i < n; i++)
        NODE(i) = i;
    rng_state = seed;
    for (size_t i = n - 1; i >= 1; i--) { /* Sattolo: j in [0, i) */
        size_t j = (size_t)(((__uint128_t)rng() * i) >> 64);
        uint64_t t = NODE(i);
        NODE(i) = NODE(j);
        NODE(j) = t;
    }
    for (size_t i = 0; i < n; i++)
        NODE(i) = (uint64_t)(uintptr_t)(p + NODE(i) * stride);
#undef NODE
    return (uint64_t)(uintptr_t)p;
}

/* Sum of AnonHugePages over the process, in kB; -1 when unreadable. */
static long anon_huge_kb(void)
{
    FILE *f = fopen("/proc/self/smaps_rollup", "r");
    char line[256];
    long kb = -1;
    if (!f)
        return -1;
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "AnonHugePages: %ld kB", &kb) == 1)
            break;
    fclose(f);
    return kb;
}

/* ------------------------------------------------------------------ */
/* Code generation                                                     */
/* ------------------------------------------------------------------ */

typedef struct {
    uint64_t a, b;
} pair_t; /* returned in x0, x1 (AAPCS64) */

typedef pair_t (*loop_fn)(uint64_t a, uint64_t b, uint64_t iters,
                          void *scratch);

/* Put a branch offset, counted in instructions, into bits 23:5 (imm19). */
static uint32_t patch_cbnz(uint32_t word, long off_words)
{
    if (off_words < -(1L << 18) || off_words >= (1L << 18))
        fail("loop body too long for cbnz (limit 1 MiB)");
    return (word & ~(0x7FFFFu << 5)) |
           (((uint32_t)off_words & 0x7FFFFu) << 5);
}

static uint32_t *copy_words(uint32_t *p, const uint32_t *from,
                            const uint32_t *end)
{
    while (from < end)
        *p++ = *from++;
    return p;
}

static uint32_t *emit_fillers(uint32_t *p, const struct kind *k, long n)
{
    long period = k->tmpl_end - k->tmpl;
    for (long i = 0; i < n * kunit(k); i++)
        *p++ = k->tmpl[i % period];
    return p;
}

#define CODE_BYTES (4UL << 20)

/* Write the loop for (kind, n) into code[]. code[] must be writable. */
static void emit_loop(uint32_t *code, const struct kind *k, long n)
{
    if ((unsigned long)(n * kunit(k)) * 8 + 256 > CODE_BYTES)
        fail("N too large for the code buffer");
    uint32_t *p = copy_words(code, t_prologue, t_prologue_end);
    uint32_t *loop = p;
    p = copy_words(p, t_load_a, t_load_a_end);
    p = emit_fillers(p, k, n);
    p = copy_words(p, t_load_b, t_load_b_end);
    p = emit_fillers(p, k, n);
    p = copy_words(p, t_dec, t_dec_end);
    *p = patch_cbnz(t_cbnz0[0], loop - p);
    p++;
    p = copy_words(p, t_epilogue, t_epilogue_end);
}

/* ------------------------------------------------------------------ */
/* Measurement                                                         */
/* ------------------------------------------------------------------ */

static int cmp_double(const void *x, const void *y)
{
    double a = *(const double *)x, b = *(const double *)y;
    return (a > b) - (a < b);
}

/*
 * Run `reps` repetitions of `iters` iterations. The chase position is
 * carried from one repetition to the next, so no repetition re-reads
 * lines that an earlier one left in the cache.
 */
static void measure(loop_fn fn, pair_t *pos, void *scratch, uint64_t iters,
                    int reps, double *median, double *min)
{
    double t[64];
    for (int r = 0; r < reps; r++) {
        double t0 = now_ns();
        *pos = fn(pos->a, pos->b, iters, scratch);
        t[r] = (now_ns() - t0) / (double)iters;
    }
    qsort(t, reps, sizeof t[0], cmp_double);
    *min = t[0];
    *median = (reps & 1) ? t[reps / 2]
                         : 0.5 * (t[reps / 2 - 1] + t[reps / 2]);
}

/*
 * Find the step in one series t[] over n[].
 * The series is cut at the first point where the fillers alone (hot[])
 * cost more than half of the low plateau of the miss run (miss_lo).
 * Beyond that point the time grows with the filler cost, not with the
 * window, so those points must not define the high plateau.
 * Low plateau = mean of the first 3 points, high plateau = mean of the
 * last 3 points before the cut. The step position is the N where t first crosses the
 * midpoint, with linear interpolation between the two neighbours.
 * The largest rise between two neighbours is printed as a second
 * estimate that does not depend on the plateaus.
 */
static void report_step(const char *kind, const char *series, const long *n,
                        const double *t, const double *hot, double miss_lo,
                        int cnt)
{
    int full = cnt;
    for (int i = 0; i < full; i++)
        if (hot[i] > 0.5 * miss_lo) {
            cnt = i;
            break;
        }
    if (cnt < full)
        printf("# cut,%s,%s,series cut at N=%ld: filler cost %.2f ns > "
               "0.5 x low plateau %.2f ns\n", kind, series, n[cnt], hot[cnt],
               miss_lo);
    if (cnt < 8) {
        printf("# step,%s,%s,too few points (%d, need 8)\n", kind, series,
               cnt);
        return;
    }
    double lo = (t[0] + t[1] + t[2]) / 3.0;
    double hi = (t[cnt - 1] + t[cnt - 2] + t[cnt - 3]) / 3.0;
    double mid = 0.5 * (lo + hi);
    int jump = 1;
    for (int i = 2; i < cnt; i++)
        if (t[i] - t[i - 1] > t[jump] - t[jump - 1])
            jump = i;
    double cross = -1.0;
    for (int i = 1; i < cnt; i++)
        if (t[i - 1] < mid && t[i] >= mid) {
            cross = (double)n[i - 1] + (double)(n[i] - n[i - 1]) *
                                           (mid - t[i - 1]) /
                                           (t[i] - t[i - 1]);
            break;
        }
    printf("# step,%s,%s,low_ns=%.2f,high_ns=%.2f,midpoint_ns=%.2f,", kind,
           series, lo, hi, mid);
    if (cross < 0.0)
        printf("N_at_midpoint=none%s,",
               cnt < full ? " (no step before filler cost dominates)" : "");
    else
        printf("N_at_midpoint=%.1f,", cross);
    printf("largest_rise=N %ld to %ld (+%.2f ns)", n[jump - 1], n[jump],
           t[jump] - t[jump - 1]);
    if (hi < 1.4 * lo)
        printf(",WARNING high plateau < 1.4 x low plateau: "
               "no clear step in this N range");
    printf("\n");
}

static void usage(void);

/* Parse a whole decimal number; any other text is a usage error. */
static long num(const char *v)
{
    char *end;
    errno = 0;
    long x = strtol(v, &end, 10);
    if (end == v || *end != '\0' || errno != 0) {
        fprintf(stderr, "robsize: not a number: %s\n", v);
        usage();
    }
    return x;
}

static void usage(void)
{
    fprintf(stderr,
        "usage: robsize --cpu C [--kind NAME[,NAME...]|all] [--nmin N] [--nmax N]\n"
        "               [--nstep N] [--reps R] [--iters I] [--mb M]\n"
        "               [--stride S]\n"
        "  --cpu C     CPU to pin to (required, 0..%d)\n"
        "  --kind K    filler kind, or all (default all). Kinds:\n",
        MAX_CPU);
    for (int i = 0; i < NKINDS; i++)
        fprintf(stderr, "                %-11s N=%ld..%ld step %ld  %s\n",
                kinds[i].name, kinds[i].nmin, kinds[i].nmax, kinds[i].nstep,
                kinds[i].what);
    fprintf(stderr,
        "  --nmin/--nmax/--nstep  replace the default N list of every\n"
        "              selected kind\n"
        "  --reps R    repetitions per point, 5..64 (default 5)\n"
        "  --iters I   iterations per repetition, >= 200000 (default 200000)\n"
        "  --mb M      size of each pointer chain in MiB (default 1024)\n"
        "  --stride S  bytes between pointers, multiple of 64 (default 64)\n");
    exit(2);
}

int main(int argc, char **argv)
{
    long cpu = -1, nmin = -1, nmax = -1, nstep = -1;
    long reps = 5, iters = 200000, mb = 1024, stride = 64;
    const char *kind_arg = "all";

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (i + 1 >= argc)
            usage();
        const char *v = argv[++i];
        if (!strcmp(a, "--cpu")) cpu = num(v);
        else if (!strcmp(a, "--kind")) kind_arg = v;
        else if (!strcmp(a, "--nmin")) nmin = num(v);
        else if (!strcmp(a, "--nmax")) nmax = num(v);
        else if (!strcmp(a, "--nstep")) nstep = num(v);
        else if (!strcmp(a, "--reps")) reps = num(v);
        else if (!strcmp(a, "--iters")) iters = num(v);
        else if (!strcmp(a, "--mb")) mb = num(v);
        else if (!strcmp(a, "--stride")) stride = num(v);
        else usage();
    }
    if (cpu < 0) {
        fprintf(stderr, "robsize: --cpu is required\n");
        usage();
    }
    if (cpu > MAX_CPU) {
        fprintf(stderr, "robsize: refusing CPU %ld (limit is %d)\n", cpu,
                MAX_CPU);
        return 1;
    }
    if (reps < 5 || reps > 64)
        fail("--reps must be 5..64");
    if (iters < 200000)
        fail("--iters must be >= 200000");
    if (mb < 1 || stride < 64 || stride % 64 != 0)
        fail("--mb must be >= 1 and --stride a multiple of 64");
    if (nstep == 0 || (nmin >= 0 && nmax >= 0 && nmax < nmin))
        fail("bad --nmin/--nmax/--nstep");
    /* every name of the --kind list must be a kind */
    for (const char *q = kind_arg; *q && strcmp(kind_arg, "all");) {
        const char *e = strchr(q, ',');
        size_t l = e ? (size_t)(e - q) : strlen(q);
        int found = 0;
        for (int i = 0; i < NKINDS; i++)
            found |= strlen(kinds[i].name) == l &&
                     !strncmp(q, kinds[i].name, l);
        if (!found)
            fail("unknown --kind");
        q += l + (e != NULL);
    }

    /* Check the only run-time patch against the assembler. */
    if (patch_cbnz(t_cbnz0[0], -300) != t_chk_cbnz[0]) {
        fprintf(stderr,
                "robsize: cbnz patch check failed: got %08x, assembler %08x\n",
                patch_cbnz(t_cbnz0[0], -300), t_chk_cbnz[0]);
        return 1;
    }

    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET((int)cpu, &set);
    if (sched_setaffinity(0, sizeof set, &set) != 0)
        die("sched_setaffinity");
    if (sched_getcpu() != (int)cpu)
        fail("not running on the requested CPU after sched_setaffinity");

    /* Chains are built after pinning: pages land on this CPU's node. */
    size_t bytes = (size_t)mb << 20;
    pair_t miss_pos;
    miss_pos.a = build_chain(bytes, (size_t)stride, 0x9E3779B97F4A7C15ULL);
    miss_pos.b = build_chain(bytes, (size_t)stride, 0xD1B54A32D192ED03ULL);
    long huge_kb = anon_huge_kb();

    /* Hot scratch: 256 B for the load fillers, then two self-pointing
     * cells (one cache line each) for the no-miss baseline. */
    uint64_t *scratch;
    if (posix_memalign((void **)&scratch, 64, 512) != 0)
        fail("posix_memalign");
    memset(scratch, 0, 512);
    scratch[32] = (uint64_t)(uintptr_t)&scratch[32];
    scratch[40] = (uint64_t)(uintptr_t)&scratch[40];
    pair_t hot_pos = { scratch[32], scratch[40] };

    uint32_t *code = mmap(NULL, CODE_BYTES, PROT_READ | PROT_WRITE,
                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (code == MAP_FAILED)
        die("mmap code");

    printf("# robsize: cpu=%ld chain=%ld MiB x 2, stride=%ld B, reps=%ld, "
           "iters=%ld\n", cpu, mb, stride, reps, iters);
    printf("# AnonHugePages=%ld kB (expected about %ld kB)%s\n", huge_kb,
           2 * mb * 1024,
           huge_kb < mb * 1024 ? " WARNING: chains are mostly NOT on huge "
                                 "pages; TLB walks add to every miss" : "");
    printf("# columns: median_ns, min_ns = ns per iteration with two "
           "cache-missing loads; hot_ns = same code, loads hit L1 "
           "(cost of the fillers alone, min of 3 repetitions)\n");
    printf("kind,N,filler_instrs_per_block,median_ns,min_ns,hot_ns\n");

    for (int ki = 0; ki < NKINDS; ki++) {
        const struct kind *k = &kinds[ki];
        if (!kind_selected(kind_arg, k->name))
            continue;
        long lo = nmin >= 0 ? nmin : k->nmin;
        long hi = nmax >= 0 ? nmax : k->nmax;
        long st = nstep > 0 ? nstep : k->nstep;
        if (hi < lo)
            fail("N range is empty");
        int cnt = (int)((hi - lo) / st) + 1;
        long *ns = malloc(cnt * sizeof *ns);
        double *med = malloc(cnt * sizeof *med);
        double *exc = malloc(cnt * sizeof *exc);
        double *hot = malloc(cnt * sizeof *hot);
        if (!ns || !med || !exc || !hot)
            fail("out of memory");

        printf("# kind %s: %s\n", k->name, k->what);
        for (int i = 0; i < cnt; i++) {
            long n = lo + i * st;
            double mn, hot_med, hot_min;

            if (mprotect(code, CODE_BYTES, PROT_READ | PROT_WRITE) != 0)
                die("mprotect RW");
            emit_loop(code, k, n);
            if (mprotect(code, CODE_BYTES, PROT_READ | PROT_EXEC) != 0)
                die("mprotect RX");
            __builtin___clear_cache((char *)code, (char *)code + CODE_BYTES);
            loop_fn fn = (loop_fn)(uintptr_t)code;

            /* warm-up: code pages, branch predictor */
            hot_pos = fn(hot_pos.a, hot_pos.b, 20000, scratch);
            measure(fn, &hot_pos, scratch, (uint64_t)iters, 3, &hot_med,
                    &hot_min);
            miss_pos = fn(miss_pos.a, miss_pos.b, 20000, scratch);
            measure(fn, &miss_pos, scratch, (uint64_t)iters, (int)reps,
                    &med[i], &mn);

            ns[i] = n;
            exc[i] = med[i] - hot_min;
            hot[i] = hot_min;
            printf("%s,%ld,%ld,%.3f,%.3f,%.3f\n", k->name, n, n * kunit(k),
                   med[i], mn, hot_min);
            fflush(stdout);
        }
        double miss_lo = cnt >= 3 ? (med[0] + med[1] + med[2]) / 3.0
                                  : med[0];
        report_step(k->name, "median_ns", ns, med, hot, miss_lo, cnt);
        report_step(k->name, "median_minus_hot_ns", ns, exc, hot, miss_lo,
                    cnt);
        fflush(stdout);
        free(ns);
        free(med);
        free(exc);
        free(hot);
    }
    return 0;
}
