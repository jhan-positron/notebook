/*
 * bwx.c - scratch copy of bench/bandwidth.c for Parts B and C of
 * crb/new-test-kernel/plan.md. It follows "specification v1" of
 * crb/new-test-kernel/handoff.md, sections B.1 to B.8. Every difference from
 * that specification is listed in DEVIATIONS-bwx.md.
 *
 * Every thread owns its buffers (allocated and first-touched by that thread),
 * so timing contains no page faults. One process times a sequence of kernels
 * (--seq), one interval per entry. All threads start an interval on a
 * barrier. GB means 1e9 bytes throughout.
 *
 * On AArch64 the kernels are the real ones. On any other machine every NEON
 * and asm kernel is replaced by a plain C stand-in, so that the harness (rows,
 * barriers, page state, self-test) can be run on the development machine.
 * Rates of a stand-in build mean nothing.
 */
#define _GNU_SOURCE
#ifdef __aarch64__
#include <arm_neon.h>
#endif
#include <errno.h>
#include <linux/perf_event.h>
#include <pthread.h>
#include <sched.h>
#include <setjmp.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define HUGE_BYTES (2UL << 20)
#define MAX_CPUS 1024
#define MAX_SEQ 64
#define MAX_EV 8
#define CHECK_BYTES (8UL << 20) /* --stop pass: clock is read after at least this many bytes */
#define CHUNK_BYTES HUGE_BYTES  /* --stop common: clock is read after each chunk of this size */
#define LEAD_NS 2000000L        /* --stop common: the common start is this long after the barrier */
#define LATE_NS 100000L         /* --stop common: flag "late" if a thread starts later than this */
/* Highest CPU that the process may use. Rule of the test machine: CPUs 0 to
 * 119 only, never 126 or 127. main() removes every higher CPU from the
 * allowed set of the process, and --cpus rejects one. Another machine can
 * build with -DMAX_USE_CPU=N. */
#ifndef MAX_USE_CPU
#define MAX_USE_CPU 119
#endif

/*
 * Loop placement (handoff B.7). PLACE(name) stands directly before kernel
 * k_<name>. It pads .text to a 64 B boundary and then adds PAD_<name> zero bytes,
 * so the function starts at PAD_<name> modulo 64. This needs the gcc flags
 * -fno-toplevel-reorder -falign-functions=4, and PAD must be a multiple of 4.
 *
 * For a kernel with a planned loop offset, PAD = (LOOP - HEAD) mod 64. LOOP
 * is the planned offset of the loop start modulo 64. HEAD is the number of
 * bytes between the function start and the loop start: 4 or 20 in the
 * listings of bw_new (results/kernels-20261113T181222Z/probe.txt). HEAD is a
 * guess until the objdump listing of the CRB build confirms it: override it
 * with -DHEAD_<name>=N, or the whole pad with -DPAD_<name>=N.
 * -DB3_OFFSET=0|36|52 puts the loops of copy, asmcopy and asmcopy2 at that
 * offset (step B3).
 *
 * For the other kernels the default PAD is the start offset modulo 64 that
 * the function has in bw_new (new C and asm kernels) or in bw_old (old
 * kernels). An A/A copy takes the PAD of its original.
 */
#define STR2(x) #x
#define STR(x) STR2(x)
#define PLACE(name) __asm__(".pushsection .text\n.p2align 6\n.fill " STR(PAD_##name) ", 1, 0\n.popsection\n")
#define PADOF(loop, head) (((loop) - (head)) & 63)

#ifdef B3_OFFSET
#define LOOP_copy B3_OFFSET
#define LOOP_asmcopy B3_OFFSET
#else
#define LOOP_copy 36
#define LOOP_asmcopy 52
#endif
#define LOOP_asmcopy_c 52
#ifndef HEAD_copy
#define HEAD_copy 4
#endif
#ifndef HEAD_asmcopy
#define HEAD_asmcopy 20
#endif
#ifndef HEAD_asmcopy_c
#define HEAD_asmcopy_c 4
#endif
#ifndef HEAD_asmcopy_c_add
#define HEAD_asmcopy_c_add 4
#endif
#ifndef HEAD_asmcopy_c_reg
#define HEAD_asmcopy_c_reg 20
#endif
#ifndef PAD_copy
#define PAD_copy PADOF(LOOP_copy, HEAD_copy)
#endif
#ifndef PAD_asmcopy
#define PAD_asmcopy PADOF(LOOP_asmcopy, HEAD_asmcopy)
#endif
#ifndef PAD_asmcopy2
#define PAD_asmcopy2 PAD_asmcopy
#endif
#ifndef PAD_asmcopy_c
#define PAD_asmcopy_c PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c)
#endif
#ifndef PAD_asmcopy_c_add
#define PAD_asmcopy_c_add PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_add)
#endif
#ifndef PAD_asmcopy_c_reg
#define PAD_asmcopy_c_reg PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_reg)
#endif
#ifndef PAD_read
#define PAD_read 32
#endif
#ifndef PAD_write
#define PAD_write 0
#endif
#ifndef PAD_asmread
#define PAD_asmread 0
#endif
#ifndef PAD_asmread2
#define PAD_asmread2 PAD_asmread
#endif
#ifndef PAD_asmwrite
#define PAD_asmwrite 32
#endif
#ifndef PAD_asmwrite2
#define PAD_asmwrite2 PAD_asmwrite
#endif
#ifndef PAD_oldread
#define PAD_oldread 0
#endif
#ifndef PAD_oldread2
#define PAD_oldread2 PAD_oldread
#endif
#ifndef PAD_oldwrite
#define PAD_oldwrite 32
#endif
#ifndef PAD_oldcopy
#define PAD_oldcopy 32
#endif
#ifndef PAD_read_nop4
#define PAD_read_nop4 PAD_asmread
#endif
#ifndef PAD_read_nop8
#define PAD_read_nop8 PAD_asmread
#endif
#ifndef PAD_read_nop16
#define PAD_read_nop16 PAD_asmread
#endif
#ifndef PAD_read_nop32
#define PAD_read_nop32 PAD_asmread
#endif
#ifndef PAD_read_sparse
#define PAD_read_sparse PAD_asmread
#endif

enum ktype { T_READ, T_WRITE, T_COPY, T_OLDREAD };
typedef void (*read_fn)(const uint64_t *, size_t);
typedef uint64_t (*oldread_fn)(const uint64_t *, size_t);
typedef void (*write_fn)(uint64_t *, size_t, uint64_t);
typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);

struct entry {
    int k;          /* index into kernels[] */
    uint64_t bytes; /* 0 until main() replaces it by --bytes */
};

static struct {
    int threads;
    int ncpus;
    int cpus[MAX_CPUS];
    uint64_t bytes;
    double min_s;
    int use_thp;
    struct entry seq[MAX_SEQ];
    int nseq;
    int rounds;
    int stop_common;  /* --stop common */
    int start_offset; /* --start offset */
    int two_buffers;  /* buffer b exists: --two-buffers, or a copy kernel in the sequence */
    int count;        /* --count */
    long pmu_type;    /* --pmu-type: the "type" field of perf_event_attr */
    int nev;
    char ev_name[MAX_EV][32];
    uint64_t ev_code[MAX_EV];
} cfg = { .threads = 1, .min_s = 0.5, .use_thp = 1, .rounds = 1, .pmu_type = -1 };

struct page {
    long kb_total, kb_huge; /* -1: no exact entry in /proc/self/smaps */
};

struct counts {
    uint64_t cpu_ns;              /* CLOCK_THREAD_CPUTIME_ID */
    uint64_t enabled, running;    /* of the counter group */
    uint64_t val[MAX_EV];
};

/* One thread, one interval. Written by the worker between the start barrier
 * and the end barrier of the interval; read by main() after the end barrier. */
struct result {
    uint64_t bytes;
    int64_t t_sched, t_start, t_end; /* CLOCK_MONOTONIC, ns */
    int late;
    struct page pg[2]; /* one-thread process only: read by the worker before the interval */
    long long vm[4];
    struct counts c0, c1;
};

struct thread {
    int idx;
    int cpu;
    uint64_t *a, *b;
    int group_fd;      /* leader of the counter group, -1 if no event opened */
    int ev_pos[MAX_EV]; /* position of the event in the group read, -1 if it did not open */
    int nopen;
    struct result res;
    pthread_t tid;
};

static pthread_barrier_t bar;
static int64_t t_base_ns; /* clock at process start: printed times are relative to it */
static long page_bytes;

/* --stop common (handoff B.4). gen only grows. main() stores the two times
 * before it increments gen, so a worker that sees the new gen reads the new
 * times. */
static _Atomic uint64_t gen;
static _Atomic int64_t t_sched_ns;
static _Atomic int64_t deadline_ns;

static int64_t now_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000000L + ts.tv_nsec;
}

static uint64_t parse_bytes(const char *s)
{
    char *end;
    double v = strtod(s, &end);
    double mul = 1;
    switch (*end) {
    case 'k': case 'K': mul = 1UL << 10; end++; break;
    case 'm': case 'M': mul = 1UL << 20; end++; break;
    case 'g': case 'G': mul = 1UL << 30; end++; break;
    }
    if (end == s || *end != '\0' || v <= 0 || (uint64_t)(v * mul) == 0) { /* 0 bytes after rounding is no size */
        fprintf(stderr, "bad size: %s\n", s);
        exit(2);
    }
    return (uint64_t)(v * mul);
}

/* A whole number in [lo, hi], with nothing after it. Anything else ends the
 * program: a malformed value must not run as 0. */
static long parse_long(const char *s, const char *what, long lo, long hi)
{
    char *end;
    errno = 0;
    long v = strtol(s, &end, 10);
    if (end == s || *end != '\0' || errno != 0 || v < lo || v > hi) {
        fprintf(stderr, "bad %s: '%s' (a whole number from %ld to %ld is needed)\n", what, s, lo, hi);
        exit(2);
    }
    return v;
}

/* Removes every CPU above MAX_USE_CPU from the allowed set of the calling
 * thread. main() calls it before it starts a thread, so the main thread and
 * every worker (also one without --cpus) stay on the permitted CPUs. */
static void restrict_cpus(void)
{
    cpu_set_t set;
    int changed = 0;
    if (sched_getaffinity(0, sizeof set, &set) != 0) {
        perror("sched_getaffinity");
        exit(2);
    }
    for (int c = MAX_USE_CPU + 1; c < CPU_SETSIZE; c++)
        if (CPU_ISSET(c, &set)) {
            CPU_CLR(c, &set);
            changed = 1;
        }
    if (changed && (CPU_COUNT(&set) == 0 || sched_setaffinity(0, sizeof set, &set) != 0)) {
        fprintf(stderr, "cannot keep the process on CPUs 0-%d\n", MAX_USE_CPU);
        exit(2);
    }
}

/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */
static void parse_cpus(char *list)
{
    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
        char *e, *e2;
        long lo = strtol(tok, &e, 10), hi = lo, step = 1;
        if (e != tok && *e == '-') {
            hi = strtol(e + 1, &e2, 10);
            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */
            if (e != tok && *e == ':') {
                step = strtol(e + 1, &e2, 10);
                e = e2 == e + 1 ? tok : e2;
            }
        }
        if (e == tok || *e != '\0' || lo < 0 || hi < lo || hi > MAX_USE_CPU || step < 1) {
            fprintf(stderr, "bad cpu list: %s (CPUs 0-%d only)\n", tok, MAX_USE_CPU);
            exit(2);
        }
        for (long c = lo; c <= hi; c += step) {
            if (cfg.ncpus == MAX_CPUS) {
                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);
                exit(2);
            }
            cfg.cpus[cfg.ncpus++] = (int)c;
        }
    }
}

static void pin_cpu(int cpu)
{
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof set, &set) != 0) {
        perror("sched_setaffinity");
        exit(2);
    }
}

static size_t buf_len(void)
{
    return (cfg.bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);
}

/* The buffer starts at a 2 MiB boundary, at least one page above the start
 * of the mapping. The unused parts before and after it are PROT_NONE, so the
 * buffer is one entry of its own in /proc/self/smaps (handoff B.6). */
static uint64_t *alloc_buf(void)
{
    size_t len = buf_len(), maplen = len + 2 * HUGE_BYTES;
    uint8_t *raw = mmap(NULL, maplen, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED) {
        perror("mmap");
        exit(2);
    }
    uint8_t *p = (uint8_t *)(((uintptr_t)raw + (size_t)page_bytes + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));
    if (mprotect(raw, (size_t)(p - raw), PROT_NONE) != 0 ||
        mprotect(p + len, (size_t)(raw + maplen - (p + len)), PROT_NONE) != 0)
        perror("mprotect of the guard ranges (continuing; page state will be NA)");
    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp
     * would still get 2 MiB pages. */
    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)
        perror("madvise (continuing)");
    return (uint64_t *)p;
}

/*
 * Old kernels: k_read, k_write and k_copy of bandwidth.orig.c (the benchmark
 * until 2026-11-13), renamed. The old comment of k_read was: "16 independent
 * accumulators keep the loop load-bound: on 128-bit NEON gcc folds them into
 * 8 vector chains, enough to hide a 2-cycle add latency; on AVX-512 they
 * become 2 zmm chains." oldread2 is the A/A copy: the same source under a
 * second name (the build uses -fno-ipa-icf, so gcc keeps both).
 */
#define DEF_OLDREAD(name) \
    PLACE(name); \
    __attribute__((noinline)) static uint64_t k_##name(const uint64_t *a, size_t n) \
    { \
        uint64_t s[16] = { 0 }; \
        for (size_t i = 0; i < n; i += 16) \
            for (int j = 0; j < 16; j++) \
                s[j] += a[i + j]; \
        uint64_t sum = 0; \
        for (int j = 0; j < 16; j++) \
            sum += s[j]; \
        return sum; \
    }
DEF_OLDREAD(oldread)
DEF_OLDREAD(oldread2)

PLACE(oldwrite);
__attribute__((noinline)) static void k_oldwrite(uint64_t *a, size_t n, uint64_t v)
{
    for (size_t i = 0; i < n; i++)
        a[i] = v;
}

PLACE(oldcopy);
__attribute__((noinline)) static void k_oldcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    for (size_t i = 0; i < n; i++)
        d[i] = s[i];
}

#if defined(__aarch64__)
#define STANDIN 0
/*
 * C kernels: unchanged from bench/bandwidth.c. Each iteration moves 256 B as
 * 16 vectors of 16 B and does no arithmetic on the data. Callers guarantee
 * n * 8 is a multiple of 256 and non-zero. The empty asm statement of k_read
 * and k_copy takes the 16 loaded vectors as inputs in NEON registers ("w"):
 * see the comment in bench/bandwidth.c.
 */
PLACE(read);
__attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)
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

PLACE(write);
__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)
{
    uint64_t *p = a;
    const uint64_t *end = a + n;
    uint64x2_t q = vdupq_n_u64(v);
    do {
        vst1q_u64(p + 0, q);
        vst1q_u64(p + 2, q);
        vst1q_u64(p + 4, q);
        vst1q_u64(p + 6, q);
        vst1q_u64(p + 8, q);
        vst1q_u64(p + 10, q);
        vst1q_u64(p + 12, q);
        vst1q_u64(p + 14, q);
        vst1q_u64(p + 16, q);
        vst1q_u64(p + 18, q);
        vst1q_u64(p + 20, q);
        vst1q_u64(p + 22, q);
        vst1q_u64(p + 24, q);
        vst1q_u64(p + 26, q);
        vst1q_u64(p + 28, q);
        vst1q_u64(p + 30, q);
        p += 32;
    } while (p < end);
}

PLACE(copy);
__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    uint64_t *dp = d;
    const uint64_t *sp = s;
    const uint64_t *end = s + n;
    do {
        uint64x2_t v0 = vld1q_u64(sp + 0);
        uint64x2_t v1 = vld1q_u64(sp + 2);
        uint64x2_t v2 = vld1q_u64(sp + 4);
        uint64x2_t v3 = vld1q_u64(sp + 6);
        uint64x2_t v4 = vld1q_u64(sp + 8);
        uint64x2_t v5 = vld1q_u64(sp + 10);
        uint64x2_t v6 = vld1q_u64(sp + 12);
        uint64x2_t v7 = vld1q_u64(sp + 14);
        uint64x2_t v8 = vld1q_u64(sp + 16);
        uint64x2_t v9 = vld1q_u64(sp + 18);
        uint64x2_t v10 = vld1q_u64(sp + 20);
        uint64x2_t v11 = vld1q_u64(sp + 22);
        uint64x2_t v12 = vld1q_u64(sp + 24);
        uint64x2_t v13 = vld1q_u64(sp + 26);
        uint64x2_t v14 = vld1q_u64(sp + 28);
        uint64x2_t v15 = vld1q_u64(sp + 30);
        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),
                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),
                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),
                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));
        vst1q_u64(dp + 0, v0);
        vst1q_u64(dp + 2, v1);
        vst1q_u64(dp + 4, v2);
        vst1q_u64(dp + 6, v3);
        vst1q_u64(dp + 8, v4);
        vst1q_u64(dp + 10, v5);
        vst1q_u64(dp + 12, v6);
        vst1q_u64(dp + 14, v7);
        vst1q_u64(dp + 16, v8);
        vst1q_u64(dp + 18, v9);
        vst1q_u64(dp + 20, v10);
        vst1q_u64(dp + 22, v11);
        vst1q_u64(dp + 24, v12);
        vst1q_u64(dp + 26, v13);
        vst1q_u64(dp + 28, v14);
        vst1q_u64(dp + 30, v15);
        sp += 32;
        dp += 32;
    } while (sp < end);
}

/*
 * asm kernels: the asm text of bench/bandwidth.c, inside macros so that an
 * A/A copy is the same source under a second name. Each iteration moves
 * 256 B with 8 ldp/stp of q registers (16 B each). Callers guarantee n * 8
 * is a multiple of 256 and non-zero. v8-v15 are callee-saved in AAPCS64:
 * naming them as clobbers makes gcc save d8-d15 once per call, which is
 * outside the loop.
 *
 * DEF_ASMREAD(name, nops) puts "nops" nop instructions after the 8 ldp and
 * before the add (step B5). asmread and asmread2 have 0 of them.
 */
#define DEF_ASMREAD(name, nops) \
    PLACE(name); \
    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \
    { \
        const uint64_t *p = a; \
        const uint64_t *end = a + n; \
        __asm__ volatile( \
            "1:\n\t" \
            "ldp q0, q1, [%[p]]\n\t" \
            "ldp q2, q3, [%[p], #32]\n\t" \
            "ldp q4, q5, [%[p], #64]\n\t" \
            "ldp q6, q7, [%[p], #96]\n\t" \
            "ldp q8, q9, [%[p], #128]\n\t" \
            "ldp q10, q11, [%[p], #160]\n\t" \
            "ldp q12, q13, [%[p], #192]\n\t" \
            "ldp q14, q15, [%[p], #224]\n\t" \
            ".rept " #nops "\n\tnop\n\t.endr\n\t" \
            "add %[p], %[p], #256\n\t" \
            "cmp %[p], %[end]\n\t" \
            "b.lo 1b\n\t" \
            : [p] "+r"(p) \
            : [end] "r"(end) \
            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \
              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \
              "memory", "cc"); \
    }
DEF_ASMREAD(asmread, 0)
DEF_ASMREAD(asmread2, 0)
DEF_ASMREAD(read_nop4, 4)
DEF_ASMREAD(read_nop8, 8)
DEF_ASMREAD(read_nop16, 16)
DEF_ASMREAD(read_nop32, 32)

/* Step B5. Per 128 B: 4 ldp, 9 nop, add, cmp, b.lo. That is 16 instructions
 * per 128 B, as the old read loop has, and no vector add. */
PLACE(read_sparse);
__attribute__((noinline)) static void k_read_sparse(const uint64_t *a, size_t n)
{
    const uint64_t *p = a;
    const uint64_t *end = a + n;
    __asm__ volatile(
        "1:\n\t"
        "ldp q0, q1, [%[p]]\n\t"
        "ldp q2, q3, [%[p], #32]\n\t"
        "ldp q4, q5, [%[p], #64]\n\t"
        "ldp q6, q7, [%[p], #96]\n\t"
        ".rept 9\n\tnop\n\t.endr\n\t"
        "add %[p], %[p], #128\n\t"
        "cmp %[p], %[end]\n\t"
        "b.lo 1b\n\t"
        : [p] "+r"(p)
        : [end] "r"(end)
        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc");
}

#define DEF_ASMWRITE(name) \
    PLACE(name); \
    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \
    { \
        uint64_t *p = a; \
        const uint64_t *end = a + n; \
        __asm__ volatile( \
            "dup v0.2d, %[v]\n\t" \
            "1:\n\t" \
            "stp q0, q0, [%[p]]\n\t" \
            "stp q0, q0, [%[p], #32]\n\t" \
            "stp q0, q0, [%[p], #64]\n\t" \
            "stp q0, q0, [%[p], #96]\n\t" \
            "stp q0, q0, [%[p], #128]\n\t" \
            "stp q0, q0, [%[p], #160]\n\t" \
            "stp q0, q0, [%[p], #192]\n\t" \
            "stp q0, q0, [%[p], #224]\n\t" \
            "add %[p], %[p], #256\n\t" \
            "cmp %[p], %[end]\n\t" \
            "b.lo 1b\n\t" \
            : [p] "+r"(p) \
            : [end] "r"(end), [v] "r"(v) \
            : "v0", "memory", "cc"); \
    }
DEF_ASMWRITE(asmwrite)
DEF_ASMWRITE(asmwrite2)

#define DEF_ASMCOPY(name) \
    PLACE(name); \
    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \
    { \
        uint64_t *dp = d; \
        const uint64_t *sp = s; \
        const uint64_t *end = s + n; \
        __asm__ volatile( \
            "1:\n\t" \
            "ldp q0, q1, [%[s]]\n\t" \
            "ldp q2, q3, [%[s], #32]\n\t" \
            "ldp q4, q5, [%[s], #64]\n\t" \
            "ldp q6, q7, [%[s], #96]\n\t" \
            "ldp q8, q9, [%[s], #128]\n\t" \
            "ldp q10, q11, [%[s], #160]\n\t" \
            "ldp q12, q13, [%[s], #192]\n\t" \
            "ldp q14, q15, [%[s], #224]\n\t" \
            "stp q0, q1, [%[d]]\n\t" \
            "stp q2, q3, [%[d], #32]\n\t" \
            "stp q4, q5, [%[d], #64]\n\t" \
            "stp q6, q7, [%[d], #96]\n\t" \
            "stp q8, q9, [%[d], #128]\n\t" \
            "stp q10, q11, [%[d], #160]\n\t" \
            "stp q12, q13, [%[d], #192]\n\t" \
            "stp q14, q15, [%[d], #224]\n\t" \
            "add %[s], %[s], #256\n\t" \
            "add %[d], %[d], #256\n\t" \
            "cmp %[s], %[end]\n\t" \
            "b.lo 1b\n\t" \
            : [s] "+r"(sp), [d] "+r"(dp) \
            : [end] "r"(end) \
            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \
              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \
              "memory", "cc"); \
    }
DEF_ASMCOPY(asmcopy)
DEF_ASMCOPY(asmcopy2)

/*
 * Step B2. asmcopy_c: the loop is the machine code of the C copy loop, from
 * the listing "bw_new k_copy" of probe.txt: same instruction order, same
 * offsets, registers q16 to q31, and "cmp end, s; b.hi" as its loop end. The
 * three pointers are bound to x0, x1 and x2, the registers of that listing.
 */
PLACE(asmcopy_c);
__attribute__((noinline)) static void k_asmcopy_c(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    register uint64_t *dp __asm__("x0") = d;
    register const uint64_t *sp __asm__("x1") = s;
    register const uint64_t *end __asm__("x2") = s + n;
    __asm__ volatile(
        "1:\n\t"
        "ldp q31, q30, [%[s]]\n\t"
        "ldp q29, q28, [%[s], #32]\n\t"
        "ldp q27, q26, [%[s], #64]\n\t"
        "ldp q25, q24, [%[s], #96]\n\t"
        "ldp q23, q22, [%[s], #128]\n\t"
        "ldp q21, q20, [%[s], #160]\n\t"
        "ldp q19, q18, [%[s], #192]\n\t"
        "ldp q17, q16, [%[s], #224]\n\t"
        "add %[s], %[s], #256\n\t"
        "stp q31, q30, [%[d]]\n\t"
        "add %[d], %[d], #256\n\t"
        "stp q29, q28, [%[d], #-224]\n\t"
        "stp q27, q26, [%[d], #-192]\n\t"
        "stp q25, q24, [%[d], #-160]\n\t"
        "stp q23, q22, [%[d], #-128]\n\t"
        "stp q21, q20, [%[d], #-96]\n\t"
        "stp q19, q18, [%[d], #-64]\n\t"
        "stp q17, q16, [%[d], #-32]\n\t"
        "cmp %[end], %[s]\n\t"
        "b.hi 1b\n\t"
        : [s] "+r"(sp), [d] "+r"(dp)
        : [end] "r"(end)
        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",
          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",
          "memory", "cc");
}

/* As asmcopy_c, but the two add stand after the 8 stp, and the 8 stp use the
 * offsets 0 to 224, as in asmcopy. Registers stay q16 to q31. */
PLACE(asmcopy_c_add);
__attribute__((noinline)) static void k_asmcopy_c_add(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    register uint64_t *dp __asm__("x0") = d;
    register const uint64_t *sp __asm__("x1") = s;
    register const uint64_t *end __asm__("x2") = s + n;
    __asm__ volatile(
        "1:\n\t"
        "ldp q31, q30, [%[s]]\n\t"
        "ldp q29, q28, [%[s], #32]\n\t"
        "ldp q27, q26, [%[s], #64]\n\t"
        "ldp q25, q24, [%[s], #96]\n\t"
        "ldp q23, q22, [%[s], #128]\n\t"
        "ldp q21, q20, [%[s], #160]\n\t"
        "ldp q19, q18, [%[s], #192]\n\t"
        "ldp q17, q16, [%[s], #224]\n\t"
        "stp q31, q30, [%[d]]\n\t"
        "stp q29, q28, [%[d], #32]\n\t"
        "stp q27, q26, [%[d], #64]\n\t"
        "stp q25, q24, [%[d], #96]\n\t"
        "stp q23, q22, [%[d], #128]\n\t"
        "stp q21, q20, [%[d], #160]\n\t"
        "stp q19, q18, [%[d], #192]\n\t"
        "stp q17, q16, [%[d], #224]\n\t"
        "add %[s], %[s], #256\n\t"
        "add %[d], %[d], #256\n\t"
        "cmp %[end], %[s]\n\t"
        "b.hi 1b\n\t"
        : [s] "+r"(sp), [d] "+r"(dp)
        : [end] "r"(end)
        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",
          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",
          "memory", "cc");
}

/* As asmcopy_c, but with the registers q0 to q15 (q31 becomes q0, q30
 * becomes q1, and so on), and d8 to d15 named as clobbered, as in asmcopy. */
PLACE(asmcopy_c_reg);
__attribute__((noinline)) static void k_asmcopy_c_reg(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    register uint64_t *dp __asm__("x0") = d;
    register const uint64_t *sp __asm__("x1") = s;
    register const uint64_t *end __asm__("x2") = s + n;
    __asm__ volatile(
        "1:\n\t"
        "ldp q0, q1, [%[s]]\n\t"
        "ldp q2, q3, [%[s], #32]\n\t"
        "ldp q4, q5, [%[s], #64]\n\t"
        "ldp q6, q7, [%[s], #96]\n\t"
        "ldp q8, q9, [%[s], #128]\n\t"
        "ldp q10, q11, [%[s], #160]\n\t"
        "ldp q12, q13, [%[s], #192]\n\t"
        "ldp q14, q15, [%[s], #224]\n\t"
        "add %[s], %[s], #256\n\t"
        "stp q0, q1, [%[d]]\n\t"
        "add %[d], %[d], #256\n\t"
        "stp q2, q3, [%[d], #-224]\n\t"
        "stp q4, q5, [%[d], #-192]\n\t"
        "stp q6, q7, [%[d], #-160]\n\t"
        "stp q8, q9, [%[d], #-128]\n\t"
        "stp q10, q11, [%[d], #-96]\n\t"
        "stp q12, q13, [%[d], #-64]\n\t"
        "stp q14, q15, [%[d], #-32]\n\t"
        "cmp %[end], %[s]\n\t"
        "b.hi 1b\n\t"
        : [s] "+r"(sp), [d] "+r"(dp)
        : [end] "r"(end)
        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
          "memory", "cc");
}

#else
/*
 * Stand-ins for a machine that is not AArch64: plain C loops that touch
 * exactly the same bytes as the real kernels. They exist only so that the
 * harness can be compiled and run on the development machine.
 */
#define STANDIN 1
#define DEF_ASMREAD(name, nops) \
    PLACE(name); \
    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \
    { \
        const volatile uint64_t *p = a; \
        for (size_t i = 0; i < n; i++) \
            (void)p[i]; \
    }
#define DEF_ASMWRITE(name) \
    PLACE(name); \
    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \
    { \
        for (size_t i = 0; i < n; i++) \
            a[i] = v; \
    }
#define DEF_ASMCOPY(name) \
    PLACE(name); \
    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \
    { \
        for (size_t i = 0; i < n; i++) \
            d[i] = s[i]; \
    }
DEF_ASMREAD(read, 0)
DEF_ASMWRITE(write)
DEF_ASMCOPY(copy)
DEF_ASMREAD(asmread, 0)
DEF_ASMREAD(asmread2, 0)
DEF_ASMREAD(read_nop4, 4)
DEF_ASMREAD(read_nop8, 8)
DEF_ASMREAD(read_nop16, 16)
DEF_ASMREAD(read_nop32, 32)
DEF_ASMREAD(read_sparse, 9)
DEF_ASMWRITE(asmwrite)
DEF_ASMWRITE(asmwrite2)
DEF_ASMCOPY(asmcopy)
DEF_ASMCOPY(asmcopy2)
DEF_ASMCOPY(asmcopy_c)
DEF_ASMCOPY(asmcopy_c_add)
DEF_ASMCOPY(asmcopy_c_reg)
#endif

/* The function is named k_<name>. The cast to void (*)(void) is undone by
 * call() according to the type. */
static const struct kdef {
    const char *name;
    enum ktype type;
    void (*fn)(void);
} kernels[] = {
#define K(name, type) { #name, type, (void (*)(void))k_##name }
    K(read, T_READ), K(write, T_WRITE), K(copy, T_COPY),
    K(asmread, T_READ), K(asmwrite, T_WRITE), K(asmcopy, T_COPY),
    K(oldread, T_OLDREAD), K(oldwrite, T_WRITE), K(oldcopy, T_COPY),
    K(asmread2, T_READ), K(asmwrite2, T_WRITE), K(asmcopy2, T_COPY), K(oldread2, T_OLDREAD),
    K(asmcopy_c, T_COPY), K(asmcopy_c_add, T_COPY), K(asmcopy_c_reg, T_COPY),
    K(read_nop4, T_READ), K(read_nop8, T_READ), K(read_nop16, T_READ), K(read_nop32, T_READ),
    K(read_sparse, T_READ),
#undef K
};
#define K_COUNT ((int)(sizeof kernels / sizeof kernels[0]))

/* Runs kernel kd on len bytes at byte offset off of the thread's buffers. A
 * read or write kernel uses buffer a. A copy kernel reads a and writes b. The
 * sink of the old read kernel is on the stack of the thread, as it was in the
 * old pass(), so the threads do not all store to one shared cache line. */
static void call(const struct kdef *kd, struct thread *t, size_t off, size_t len, uint64_t v, volatile uint64_t *sink)
{
    uint64_t *a = t->a + off / 8;
    size_t n = len / 8;
    switch (kd->type) {
    case T_READ:
        ((read_fn)kd->fn)(a, n);
        break;
    case T_OLDREAD:
        *sink = ((oldread_fn)kd->fn)(a, n);
        break;
    case T_WRITE:
        ((write_fn)kd->fn)(a, n, v);
        break;
    case T_COPY:
        ((copy_fn)kd->fn)(t->b + off / 8, a, n);
        break;
    }
}

/* Page state (handoff B.6). For each of the n buffers (a NULL entry is
 * skipped): the entry of /proc/self/smaps whose start is the buffer and whose
 * end is the buffer plus buf_len(). Without such an entry both values stay -1
 * and are printed as NA. */
static void read_smaps(struct page *pg, uint64_t *const *buf, int n)
{
    char line[256];
    int cur = -1;
    size_t len = buf_len();
    for (int i = 0; i < n; i++)
        pg[i].kb_total = pg[i].kb_huge = -1;
    FILE *f = fopen("/proc/self/smaps", "r");
    if (!f)
        return;
    while (fgets(line, sizeof line, f)) {
        unsigned long s, e;
        char perms[8];
        if (sscanf(line, "%lx-%lx %7s", &s, &e, perms) == 3) {
            cur = -1;
            for (int i = 0; i < n; i++)
                if (buf[i] && (unsigned long)(uintptr_t)buf[i] == s && e == s + len)
                    cur = i;
        } else if (cur >= 0) {
            sscanf(line, "Size: %ld kB", &pg[cur].kb_total);
            sscanf(line, "AnonHugePages: %ld kB", &pg[cur].kb_huge);
        }
    }
    fclose(f);
    for (int i = 0; i < n; i++)
        if (pg[i].kb_total < 0 || pg[i].kb_huge < 0)
            pg[i].kb_total = pg[i].kb_huge = -1;
}

/* Four counters of /proc/vmstat. They count for the whole system. -1: not found. */
static void read_vmstat(long long vm[4])
{
    static const char *name[4] = { "thp_fault_alloc", "thp_fault_fallback", "thp_collapse_alloc", "pgmigrate_success" };
    char key[64];
    long long val;
    for (int i = 0; i < 4; i++)
        vm[i] = -1;
    FILE *f = fopen("/proc/vmstat", "r");
    if (!f)
        return;
    while (fscanf(f, "%63s %lld", key, &val) == 2)
        for (int i = 0; i < 4; i++)
            if (!strcmp(key, name[i]))
                vm[i] = val;
    fclose(f);
}

static void print_na(long long v)
{
    if (v < 0)
        printf(",NA");
    else
        printf(",%lld", v);
}

static void print_p(int round, int pos, int tid, char buffer, const struct page *pg, const long long vm[4])
{
    printf("P,%d,%d,%d,%c", round, pos, tid, buffer);
    print_na(pg->kb_total);
    print_na(pg->kb_huge);
    for (int i = 0; i < 4; i++)
        print_na(vm[i]);
    printf("\n");
}

/* Counters (handoff B.8): one group per thread, user mode only, opened by the
 * pinned thread for itself. An event that does not open is printed as NA. */
static void open_counters(struct thread *t)
{
    t->group_fd = -1;
    t->nopen = 0;
    for (int e = 0; e < cfg.nev; e++) {
        struct perf_event_attr a;
        memset(&a, 0, sizeof a);
        a.type = (uint32_t)cfg.pmu_type;
        a.size = sizeof a;
        a.config = cfg.ev_code[e];
        a.exclude_kernel = 1;
        a.exclude_hv = 1;
        a.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, t->group_fd, 0);
        if (fd < 0) {
            if (t->idx == 0)
                fprintf(stderr, "perf_event_open %s (type %ld code 0x%llx): %s (printed as NA)\n", cfg.ev_name[e],
                        cfg.pmu_type, (unsigned long long)cfg.ev_code[e], strerror(errno));
            t->ev_pos[e] = -1;
            continue;
        }
        t->ev_pos[e] = t->nopen++;
        if (t->group_fd < 0)
            t->group_fd = fd;
    }
}

static uint64_t cpu_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);
    return (uint64_t)ts.tv_sec * 1000000000UL + (uint64_t)ts.tv_nsec;
}

/* Group read: nr, time_enabled, time_running, then one value per open event. */
static void read_group(const struct thread *t, struct counts *c)
{
    uint64_t buf[3 + MAX_EV];
    if (t->group_fd < 0)
        return;
    if (read(t->group_fd, buf, sizeof buf) < (ssize_t)(3 * sizeof buf[0]) || buf[0] != (uint64_t)t->nopen) {
        perror("read of the counter group");
        exit(2);
    }
    c->enabled = buf[1];
    c->running = buf[2];
    for (int i = 0; i < t->nopen; i++)
        c->val[i] = buf[3 + i];
}

static void *worker(void *arg)
{
    struct thread *t = arg;
    volatile uint64_t sink;
    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */
    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;
    uint64_t k = 0; /* intervals this thread has run (--stop common) */
    int64_t min_ns = (int64_t)(cfg.min_s * 1e9);

    if (cfg.ncpus)
        pin_cpu(t->cpu);
    if (cfg.count)
        open_counters(t);
    t->a = alloc_buf();
    k_write(t->a, cfg.bytes / 8, v); /* first touch by this thread */
    if (cfg.two_buffers) {
        t->b = alloc_buf();
        k_write(t->b, cfg.bytes / 8, v);
    }
    if (cfg.threads > 1) {
        pthread_barrier_wait(&bar); /* the buffers exist: main() reads the first page state */
        pthread_barrier_wait(&bar); /* main() has read it */
    }

    for (int round = 0; round < cfg.rounds; round++) {
        for (int pos = 0; pos < cfg.nseq; pos++) {
            const struct kdef *kd = &kernels[cfg.seq[pos].k];
            size_t size = cfg.seq[pos].bytes;
            size_t nchunk = size / HUGE_BYTES;
            /* --start offset (handoff B.5): thread i starts at (i * 37 mod n) * 2 MiB */
            size_t off = cfg.start_offset && nchunk ? ((size_t)t->idx * 37 % nchunk) * HUGE_BYTES : 0;
            uint64_t per_byte = kd->type == T_COPY ? 2 : 1; /* copy counts read+write bytes */
            uint64_t bytes = 0, p = 0;
            int64_t sched = 0, deadline = 0, t0, t1;
            struct result r;
            memset(&r, 0, sizeof r);

            call(kd, t, 0, size, v, &sink); /* warm-up */
            if (cfg.threads == 1) {
                uint64_t *buf[2] = { t->a, t->b };
                read_smaps(r.pg, buf, 2);
                read_vmstat(r.vm);
            }
            pthread_barrier_wait(&bar);
            if (cfg.stop_common) {
                while (atomic_load(&gen) != k + 1)
                    ;
                sched = atomic_load(&t_sched_ns);
                deadline = atomic_load(&deadline_ns);
                while (now_ns() < sched)
                    ;
            }
            if (cfg.count) {
                read_group(t, &r.c0);
                r.c0.cpu_ns = cpu_ns();
            }
            t0 = now_ns();
            k++;
            if (cfg.stop_common) {
                /* chunks of 2 MiB (or the whole entry if it is smaller); the
                 * position continues from chunk to chunk and wraps */
                size_t chunk = size < CHUNK_BYTES ? size : CHUNK_BYTES, at = off;
                do {
                    call(kd, t, at, chunk, v + p++, &sink);
                    bytes += per_byte * chunk;
                    at += chunk;
                    if (at == size)
                        at = 0;
                    t1 = now_ns();
                } while (t1 < deadline);
            } else {
                /* whole passes; with an offset a pass is [off, size) then [0, off) */
                uint64_t passes_per_check = CHECK_BYTES / size;
                if (passes_per_check == 0)
                    passes_per_check = 1;
                do {
                    for (uint64_t c = 0; c < passes_per_check; c++, p++) {
                        call(kd, t, off, size - off, v + p, &sink);
                        if (off)
                            call(kd, t, 0, off, v + p, &sink);
                        bytes += per_byte * size;
                    }
                    t1 = now_ns();
                } while (t1 - t0 < min_ns);
            }
            if (cfg.count) {
                r.c1.cpu_ns = cpu_ns();
                read_group(t, &r.c1);
            }
            r.bytes = bytes;
            r.t_start = t0;
            r.t_end = t1;
            r.t_sched = cfg.stop_common ? sched : t0;
            r.late = cfg.stop_common && t0 - sched > LATE_NS;
            t->res = r;
            pthread_barrier_wait(&bar);
            /* main() reads the page state of all buffers. The warm-up pass of
             * the next interval starts only after that reading (handoff B.6). */
            if (cfg.threads > 1)
                pthread_barrier_wait(&bar);
        }
    }
    return NULL;
}

static void usage(void)
{
    fprintf(stderr,
            "usage: bwx --seq LIST [--threads T --cpus LIST] [--bytes B] [--min-ms MS] [--no-thp]\n"
            "           [--rounds N] [--stop pass|common] [--start common|offset] [--two-buffers]\n"
            "           [--count --pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"
            "       bwx --selftest | --list\n"
            "  --seq: comma-separated entries KERNEL or KERNEL@SIZE; --list prints the kernel names\n"
            "  sizes must be multiples of 256; with --stop common: multiples of 2M, or below 2M\n"
            "  --pmu-type and CODE: the perf_event_attr fields type and config of the core PMU (CODE may be 0x..)\n");
    exit(2);
}

static void parse_seq(char *list)
{
    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
        char *at = strchr(tok, '@');
        int k = 0;
        if (at)
            *at = '\0';
        while (k < K_COUNT && strcmp(tok, kernels[k].name))
            k++;
        if (k == K_COUNT || cfg.nseq == MAX_SEQ) {
            fprintf(stderr, "bad --seq entry: %s\n", tok);
            exit(2);
        }
        cfg.seq[cfg.nseq].k = k;
        cfg.seq[cfg.nseq].bytes = at ? parse_bytes(at + 1) : 0;
        cfg.nseq++;
    }
}

/* "NAME=CODE,..." or "CODE,...". A code without a name gets the name of its
 * position in the list of handoff B.8. */
static void parse_events(char *list)
{
    static const char *by_pos[5] = { "cycles", "instructions", "l1d_refill", "l2d_refill", "ll_miss_rd" };
    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
        char *eq = strchr(tok, '='), *code = eq ? eq + 1 : tok, *end;
        if (eq == tok || cfg.nev == MAX_EV || (eq && (size_t)(eq - tok) >= sizeof cfg.ev_name[0])) {
            fprintf(stderr, "bad --events entry: %s\n", tok);
            exit(2);
        }
        if (eq)
            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "%.*s", (int)(eq - tok), tok);
        else if (cfg.nev < 5)
            strcpy(cfg.ev_name[cfg.nev], by_pos[cfg.nev]);
        else
            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "ev%d", cfg.nev);
        cfg.ev_code[cfg.nev] = strtoull(code, &end, 0);
        if (end == code || *end != '\0') {
            fprintf(stderr, "bad --events code: %s\n", code);
            exit(2);
        }
        cfg.nev++;
    }
}

#include "bwx_selftest.c"

int main(int argc, char **argv)
{
    int threads_given = 0;
    char seq_text[1024] = "";
    t_base_ns = now_ns();
    page_bytes = sysconf(_SC_PAGESIZE);
    cfg.bytes = 1UL << 20;
    restrict_cpus();

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        int more = i + 1 < argc;
        if (!strcmp(a, "--selftest")) {
            return selftest();
        } else if (!strcmp(a, "--list")) {
            for (int k = 0; k < K_COUNT; k++)
                printf("%s\n", kernels[k].name);
            return 0;
        } else if (!strcmp(a, "--no-thp")) {
            cfg.use_thp = 0;
        } else if (!strcmp(a, "--two-buffers")) {
            cfg.two_buffers = 1;
        } else if (!strcmp(a, "--count")) {
            cfg.count = 1;
        } else if (!strcmp(a, "--threads") && more) {
            cfg.threads = (int)parse_long(argv[++i], "--threads", 1, 4096);
            threads_given = 1;
        } else if (!strcmp(a, "--cpus") && more) {
            parse_cpus(argv[++i]);
        } else if (!strcmp(a, "--bytes") && more) {
            cfg.bytes = parse_bytes(argv[++i]);
        } else if (!strcmp(a, "--min-ms") && more) {
            char *end;
            double ms = strtod(argv[++i], &end);
            if (end == argv[i] || *end != '\0' || !(ms > 0) || ms > 3.6e6) {
                fprintf(stderr, "bad --min-ms: '%s' (a number of milliseconds above 0 is needed)\n", argv[i]);
                exit(2);
            }
            cfg.min_s = ms / 1000.0;
        } else if (!strcmp(a, "--rounds") && more) {
            cfg.rounds = (int)parse_long(argv[++i], "--rounds", 1, 1000000);
        } else if (!strcmp(a, "--seq") && more) {
            snprintf(seq_text, sizeof seq_text, "%s", argv[++i]);
            parse_seq(argv[i]);
        } else if (!strcmp(a, "--stop") && more) {
            const char *s = argv[++i];
            if (strcmp(s, "pass") && strcmp(s, "common"))
                usage();
            cfg.stop_common = !strcmp(s, "common");
        } else if (!strcmp(a, "--start") && more) {
            const char *s = argv[++i];
            if (strcmp(s, "common") && strcmp(s, "offset"))
                usage();
            cfg.start_offset = !strcmp(s, "offset");
        } else if (!strcmp(a, "--pmu-type") && more) {
            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);
        } else if (!strcmp(a, "--events") && more) {
            parse_events(argv[++i]);
        } else {
            usage();
        }
    }
    if (threads_given && cfg.ncpus == 0) {
        fprintf(stderr, "--threads requires --cpus\n");
        usage();
    }
    if (cfg.threads < 1 || cfg.rounds < 1 || cfg.nseq < 1 || cfg.bytes == 0 || cfg.bytes % 256 != 0)
        usage();
    /* run_bwx.sh passes the counter settings in the environment */
    if (cfg.count && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))
        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);
    if (cfg.count && cfg.nev == 0 && getenv("BWX_EVENTS")) {
        char *copy = strdup(getenv("BWX_EVENTS"));
        parse_events(copy);
        free(copy);
    }
    if (cfg.count && (cfg.pmu_type < 0 || cfg.nev == 0)) {
        fprintf(stderr, "--count requires --pmu-type and --events (or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");
        usage();
    }
    for (int s = 0; s < cfg.nseq; s++) {
        struct entry *e = &cfg.seq[s];
        if (e->bytes == 0)
            e->bytes = cfg.bytes;
        if (e->bytes > cfg.bytes || e->bytes % 256 != 0 ||
            (cfg.stop_common && e->bytes > CHUNK_BYTES && e->bytes % CHUNK_BYTES != 0)) {
            fprintf(stderr, "bad size of --seq entry %d (%s): %lu\n", s, kernels[e->k].name, (unsigned long)e->bytes);
            usage();
        }
        if (kernels[e->k].type == T_COPY)
            cfg.two_buffers = 1;
    }
    if (cfg.ncpus && cfg.threads > cfg.ncpus)
        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);

    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);
    uint64_t **bufs = calloc((size_t)cfg.threads * 2, sizeof *bufs);
    struct page *pg = calloc((size_t)cfg.threads * 2, sizeof *pg);
    if (!th || !bufs || !pg || pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {
        perror("setup");
        return 2;
    }
    for (int i = 0; i < cfg.threads; i++) {
        th[i].idx = i;
        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;
        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {
            perror("pthread_create");
            return 2;
        }
    }

    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "
           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",
           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");
    printf("# bwx: seq=%s rounds=%d stop=%s start=%s two_buffers=%d count=%d kernels=%s; "
           "round and pos count from 0; times are seconds since process start\n",
           seq_text, cfg.rounds, cfg.stop_common ? "common" : "pass", cfg.start_offset ? "offset" : "common",
           cfg.two_buffers, cfg.count, STANDIN ? "STAND-IN (not AArch64: rates mean nothing)" : "aarch64");
    printf("# I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps\n"
           "# T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags\n"
           "# P,round,pos,tid,buffer,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n");
    if (cfg.count) {
        printf("# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns");
        for (int e = 0; e < cfg.nev; e++)
            printf(",%s", cfg.ev_name[e]);
        printf("; pmu_type=%ld codes=", cfg.pmu_type);
        for (int e = 0; e < cfg.nev; e++)
            printf("%s0x%llx", e ? "," : "", (unsigned long long)cfg.ev_code[e]);
        printf("\n");
    }
    fflush(stdout);

    for (int round = 0; round < cfg.rounds; round++) {
        for (int pos = -1; pos < cfg.nseq; pos++) {
            if (pos < 0 && (round > 0 || cfg.threads == 1))
                continue;
            if (pos < 0) {
                /* the workers have allocated and first touched their buffers */
                pthread_barrier_wait(&bar);
                for (int i = 0; i < cfg.threads; i++) {
                    bufs[2 * i] = th[i].a;
                    bufs[2 * i + 1] = th[i].b;
                }
            } else {
                const struct entry *e = &cfg.seq[pos];
                const char *name = kernels[e->k].name;
                double per_pass = (double)e->bytes * (kernels[e->k].type == T_COPY ? 2 : 1);
                uint64_t total = 0;
                int64_t max_el = 0;

                pthread_barrier_wait(&bar); /* release the workers */
                if (cfg.stop_common) {
                    int64_t sched = now_ns() + LEAD_NS;
                    atomic_store(&t_sched_ns, sched);
                    atomic_store(&deadline_ns, sched + (int64_t)(cfg.min_s * 1e9));
                    atomic_fetch_add(&gen, 1);
                }
                pthread_barrier_wait(&bar); /* all workers finished this interval */

                for (int i = 0; i < cfg.threads; i++) {
                    struct result *r = &th[i].res;
                    total += r->bytes;
                    if (r->t_end - r->t_start > max_el)
                        max_el = r->t_end - r->t_start;
                }
                if (cfg.threads == 1) { /* read by the worker before the interval */
                    print_p(round, pos, 0, 'a', &th[0].res.pg[0], th[0].res.vm);
                    if (th[0].b)
                        print_p(round, pos, 0, 'b', &th[0].res.pg[1], th[0].res.vm);
                }
                printf("I,%d,%d,%s,%lu,%d,%lu,%.6f,%.2f\n", round, pos, name, (unsigned long)e->bytes, cfg.threads,
                       (unsigned long)total, (double)max_el * 1e-9, (double)total / (double)max_el);
                for (int i = 0; i < cfg.threads; i++) {
                    struct result *r = &th[i].res;
                    printf("T,%d,%d,%s,%d,%d,%lu,%.6f,%.6f,%.6f,%.6f,%.3f,%s\n", round, pos, name, i, th[i].cpu,
                           (unsigned long)r->bytes, (double)(r->t_end - r->t_start) * 1e-9,
                           (double)(r->t_sched - t_base_ns) * 1e-9, (double)(r->t_start - t_base_ns) * 1e-9,
                           (double)(r->t_end - t_base_ns) * 1e-9, (double)r->bytes / per_pass, r->late ? "late" : "-");
                }
                for (int i = 0; cfg.count && i < cfg.threads; i++) {
                    struct result *r = &th[i].res;
                    printf("C,%d,%d,%s,%d,%d", round, pos, name, i, th[i].cpu);
                    if (th[i].group_fd < 0)
                        printf(",NA,NA");
                    else
                        printf(",%llu,%llu", (unsigned long long)(r->c1.enabled - r->c0.enabled),
                               (unsigned long long)(r->c1.running - r->c0.running));
                    printf(",%llu", (unsigned long long)(r->c1.cpu_ns - r->c0.cpu_ns));
                    for (int ev = 0; ev < cfg.nev; ev++) {
                        int at = th[i].ev_pos[ev];
                        if (at < 0)
                            printf(",NA");
                        else
                            printf(",%llu", (unsigned long long)(r->c1.val[at] - r->c0.val[at]));
                    }
                    printf("\n");
                }
            }
            if (cfg.threads > 1) {
                /* Page state of all buffers, read between two intervals. It is
                 * the state after interval pos (pos -1: before the first). The
                 * workers wait on the barrier below until it is read. */
                long long vm[4];
                int64_t r0 = now_ns();
                read_smaps(pg, bufs, 2 * cfg.threads);
                read_vmstat(vm);
                double ms = (double)(now_ns() - r0) * 1e-6;
                pthread_barrier_wait(&bar); /* the reading is done: the workers go on */
                for (int i = 0; i < 2 * cfg.threads; i++)
                    if (bufs[i])
                        print_p(round, pos, i / 2, i % 2 ? 'b' : 'a', &pg[i], vm);
                printf("# page_read,%d,%d,%.3f ms\n", round, pos, ms);
            }
            fflush(stdout);
        }
    }
    for (int i = 0; i < cfg.threads; i++)
        pthread_join(th[i].tid, NULL);
    return 0;
}
