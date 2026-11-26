/* bwx11+ */
/*
 * bwx11.c - bwx10.c plus the additions of round 4 (2026-11-15). Every
 * addition stands between a line "bwx11+" and a line "bwx11-" (both are
 * comments). Without these blocks this file is bwx10.c byte for byte:
 * test_runner11.py checks it. So the 26 kernels of bwx10, call(),
 * timed_sequence(), timed_sequence_hot() and the interval mode are the text
 * of bwx10.c.
 *
 * Additions:
 *   kernels read_nop64, read_nop96, read_nop128: the asmread loop with 64, 96
 *     and 128 nop instructions after the 8 ldp. They stand after the last
 *     kernel of bwx10 in the source and in kernels[], so the kernels of bwx10
 *     keep their machine code and their loop offsets.
 *   A second pad after these kernels, so that call() and the code up to the
 *     end of timed_sequence_hot() keep their placement modulo 64.
 *   --evict-mb N  (trial mode) before the first trial the worker writes N MiB
 *     of other memory twice. This pushes the benchmark buffer out of the
 *     caches, so its lines are read back from memory.
 *   M rows evict_mb and evict_ns. With --trace and N above 0 also the rows
 *     TR,-1,0,evict_start,<t_ns> and TR,-1,1,evict_end,<t_ns>.
 * The line that includes the self-test file is changed by additions only: the
 * old line stands inside "#if 0".
 * The plan file format is unchanged ("# bwx8-plan v1").
 */
/* bwx11- */
/* bwx10+ */
/*
 * bwx10.c - bwx8.c plus the additions of round 3 (2026-11-15). Every addition
 * stands between a line "bwx10+" and a line "bwx10-" (both are comments).
 * Without these blocks, and with the name of the included self-test file set
 * back, this file is bwx8.c byte for byte: test_runner10.py checks it. So the
 * 21 kernels of bwx8, call(), timed_sequence() and the interval mode are the
 * text of bwx8.c.
 *
 * Additions:
 *   kernels read_pf256, read_pf512, read_pf1024, read_pf2048, read_1pl. They
 *     stand after the last kernel of bwx8 in the source and in kernels[], so
 *     the kernels of bwx8 keep their machine code and their loop offsets.
 *   --rec-pad BYTES  (trial mode) unused bytes before the win[] array of the
 *     record block.
 *   --hot-copy       (trial mode) timed_sequence_hot() runs the windows: it
 *     does not read or write win[i] between the first and the last pass of a
 *     window.
 *   M rows rec_pad, hot_copy, rec_addr, win_addr, win_size, stack_addr,
 *     buf_addr, tw_addr.
 *   A pad after the new kernels, so that call() and the code up to the end
 *     of timed_sequence() keep their placement modulo 64.
 * The plan file format is unchanged ("# bwx8-plan v1").
 */
/* bwx10- */
/*
 * bwx8.c - scratch copy of bwx.c (crb/tmp/agent-scratch/bwx-2026-11-13) for
 * the design crb/new-test-kernel/tackle-8mb.md. The contract with the other
 * parts is DECISIONS-bwx8.md in this folder.
 *
 * Two modes:
 *   --seq ...    the interval mode of bwx.c. Its code is the text of bwx.c.
 *   --trial ...  one pinned worker runs the trials of a plan file. A trial is
 *                previous activity, prefix, predecessor and target windows
 *                with nothing but clock reads between them.
 *
 * Everything from "#define _GNU_SOURCE" to the end of parse_events() is the
 * text of bwx.c, so the kernels, PLACE, call() and alloc_buf() are unchanged.
 * All code of the trial mode stands after it. The build uses
 * -fno-toplevel-reorder, so the kernels keep their place in the binary.
 *
 * On AArch64 the kernels are the real ones. On any other machine every NEON
 * and asm kernel is replaced by a plain C stand-in, so that the harness can
 * be run on the development machine. Rates of a stand-in build mean nothing.
 * GB means 1e9 bytes throughout.
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
/* bwx10+ */

/*
 * Kernels of round 3. They stand after every kernel of bwx8, so those keep
 * their place. Each one is a read kernel (T_READ) with the loop start at 20
 * modulo 64, the loop offset of asmread in the accepted build.
 *
 * read_pf256, read_pf512, read_pf1024, read_pf2048 have the frame of asmread
 * (d8-d15 are saved), so HEAD is 20 and the pad is the pad of asmread.
 * read_1pl names v0-v3 only, so gcc saves nothing: HEAD is 4, as read_sparse
 * has it. HEAD_read_1pl is a guess until the listing of the CRB build
 * confirms it (check_listing10.py checks the loop offset).
 */
#ifndef PAD_read_pf256
#define PAD_read_pf256 PAD_asmread
#endif
#ifndef PAD_read_pf512
#define PAD_read_pf512 PAD_asmread
#endif
#ifndef PAD_read_pf1024
#define PAD_read_pf1024 PAD_asmread
#endif
#ifndef PAD_read_pf2048
#define PAD_read_pf2048 PAD_asmread
#endif
#define LOOP_read_1pl 20
#ifndef HEAD_read_1pl
#define HEAD_read_1pl 4
#endif
#ifndef PAD_read_1pl
#define PAD_read_1pl PADOF(LOOP_read_1pl, HEAD_read_1pl)
#endif

#if defined(__aarch64__)
/*
 * DEF_READ_PF(name, d0, d1, d2, d3): the loop of asmread (8 ldp of q
 * registers per 256 B, same registers, same clobbers) plus four software
 * prefetches per iteration, one per 64 B line, after the 8 ldp and before the
 * add. d0 is the prefetch distance D in bytes ahead of the block that the
 * iteration loads. d1, d2, d3 are D + 64, D + 128, D + 192.
 *
 * prfm pldl1keep asks for the line in the first-level data cache (PLD: for a
 * load, L1: first level, KEEP: normal, not streaming). The form
 * [base, #offset] needs an offset that is a multiple of 8 from 0 to 32760.
 * In the last iterations of a pass the prefetch address lies past the end of
 * the range, and for the last range of the buffer past the end of the
 * buffer. That is allowed: prfm never faults, not even on an address that is
 * not mapped. It reads no data, so the kernel touches the same bytes as
 * asmread.
 */
#define DEF_READ_PF(name, d0, d1, d2, d3) \
    _Static_assert((d0) % 8 == 0 && (d0) >= 0 && (d1) == (d0) + 64 && (d2) == (d0) + 128 && (d3) == (d0) + 192 && \
                   (d3) <= 32760, "prfm offsets: multiples of 8 from 0 to 32760, one per 64 B line"); \
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
            "prfm pldl1keep, [%[p], #" #d0 "]\n\t" \
            "prfm pldl1keep, [%[p], #" #d1 "]\n\t" \
            "prfm pldl1keep, [%[p], #" #d2 "]\n\t" \
            "prfm pldl1keep, [%[p], #" #d3 "]\n\t" \
            "add %[p], %[p], #256\n\t" \
            "cmp %[p], %[end]\n\t" \
            "b.lo 1b\n\t" \
            : [p] "+r"(p) \
            : [end] "r"(end) \
            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \
              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \
              "memory", "cc"); \
    }
DEF_READ_PF(read_pf256, 256, 320, 384, 448)
DEF_READ_PF(read_pf512, 512, 576, 640, 704)
DEF_READ_PF(read_pf1024, 1024, 1088, 1152, 1216)
DEF_READ_PF(read_pf2048, 2048, 2112, 2176, 2240)

/* read_1pl, "one load per line". Per 256 B: four loads of 16 B, one at the
 * start of each 64 B line, then add, cmp, b.lo. It reads bytes 0 to 15 of
 * every line and no other byte. */
PLACE(read_1pl);
__attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)
{
    const uint64_t *p = a;
    const uint64_t *end = a + n;
    __asm__ volatile(
        "1:\n\t"
        "ldr q0, [%[p]]\n\t"
        "ldr q1, [%[p], #64]\n\t"
        "ldr q2, [%[p], #128]\n\t"
        "ldr q3, [%[p], #192]\n\t"
        "add %[p], %[p], #256\n\t"
        "cmp %[p], %[end]\n\t"
        "b.lo 1b\n\t"
        : [p] "+r"(p)
        : [end] "r"(end)
        : "v0", "v1", "v2", "v3", "memory", "cc");
}
#else
/* Stand-ins. A prefetch touches no byte, so the stand-in of a read_pf kernel
 * is the stand-in of asmread. The stand-in of read_1pl reads the first two
 * words (16 B) of every 64 B line, as the real kernel does. */
DEF_ASMREAD(read_pf256, 0)
DEF_ASMREAD(read_pf512, 0)
DEF_ASMREAD(read_pf1024, 0)
DEF_ASMREAD(read_pf2048, 0)
PLACE(read_1pl);
__attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)
{
    const volatile uint64_t *p = a;
    for (size_t i = 0; i < n; i += 8) {
        (void)p[i];
        (void)p[i + 1];
    }
}
#endif

/*
 * Placement of the code after the kernels. In the accepted build of bwx8 the
 * last kernel ends at 0x4a14 (ref-bwx8/listing.txt), so the function after
 * the kernels starts at 0x4a18: 24 modulo 64. That function is call(), or
 * read_smaps() if gcc inlines every call of call(). The pad below gives it
 * the same start modulo 64 in bwx10. No code is added between call() and the
 * end of timed_sequence(), so that code keeps the placement modulo 64 that it
 * has in bwx8. build10.sh prints the placement of both binaries.
 * The value 24 holds for the AArch64 build with the accepted compiler. On
 * another machine it is only a pad: test_runner10.py builds one copy with the
 * local value to check the method.
 */
#ifndef PAD_after_kernels
#define PAD_after_kernels 24
#endif
PLACE(after_kernels);
/* bwx10- */
/* bwx11+ */

/*
 * Kernels of round 4. They stand after every kernel of bwx10, so those keep
 * their place. Each one is the asmread loop with more nop instructions
 * between the 8 ldp and the add: 64, 96 and 128. The frame is the frame of
 * asmread (d8-d15 are saved), so the pad is the pad of asmread and the loop
 * starts at 20 modulo 64 (check_listing11.py checks it). DEF_ASMREAD is the
 * macro of the kernels of bwx8: the asm text on AArch64, the stand-in loop on
 * another machine. A nop touches no byte, so the stand-in is the stand-in of
 * asmread.
 */
#ifndef PAD_read_nop64
#define PAD_read_nop64 PAD_asmread
#endif
#ifndef PAD_read_nop96
#define PAD_read_nop96 PAD_asmread
#endif
#ifndef PAD_read_nop128
#define PAD_read_nop128 PAD_asmread
#endif
DEF_ASMREAD(read_nop64, 64)
DEF_ASMREAD(read_nop96, 96)
DEF_ASMREAD(read_nop128, 128)

/*
 * The pad after the kernels, once more. The pad of bwx10 above now stands
 * before the kernels of round 4, so it no longer places call(). This pad has
 * the same value, and the function after the kernels starts at that value
 * modulo 64, as in bwx10 and in bwx8. build11.sh prints the placement.
 */
#ifndef PAD_after_kernels11
#define PAD_after_kernels11 PAD_after_kernels
#endif
PLACE(after_kernels11);
/* bwx11- */

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
/* bwx10+ */
    K(read_pf256, T_READ), K(read_pf512, T_READ), K(read_pf1024, T_READ), K(read_pf2048, T_READ),
    K(read_1pl, T_READ),
/* bwx10- */
/* bwx11+ */
    K(read_nop64, T_READ), K(read_nop96, T_READ), K(read_nop128, T_READ),
/* bwx11- */
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

/*
 * Trial mode (--trial). Design: crb/new-test-kernel/tackle-8mb.md, "Runner
 * design". Formats: DECISIONS-bwx8.md.
 *
 * The plan file gives the trials of the process. The whole plan is read and
 * checked before the process pins, allocates or opens a counter. A defect
 * ends the process with status 2.
 *
 * One trial is a list of windows: previous activity (1), prefix (4),
 * predecessor (1), target (nwin). timed_sequence() runs them. It calls only
 * the kernels and the clock. With count "read" it also reads the counter
 * group and the thread CPU clock at the boundaries of the target windows.
 * Page state, context switches, counter open and close, and all output lie
 * outside the timed sequence.
 */
#include <stdarg.h>
#include <sys/resource.h>

#define BIN_NS 10000000L     /* requested width of a bin: 10 ms */
#define TRACE_CAP (1L << 20) /* --trace: events kept per trial */
#define PLAN_LINE1 "# bwx8-plan v1"
#define PLAN_LINE3 "# trial cond rep prev pfx pred tgt nwin win_ms count bins"
#define PLAN_FIELDS 11
#define MAX_PAIRS 64
#define MAX_NWIN 4096
#define MAX_MS 3600000L
#define MAX_REC_BYTES (256UL << 20) /* bound of the record storage of one plan */

enum { PH_PREV, PH_PREFIX, PH_PRED, PH_TARGET };
enum { CS_CLOSED, CS_OPEN, CS_READ, CS_FAIL };
enum { EV_CLOCK, EV_KERNEL_FIRST, EV_COUNT_READ, EV_CPU_CLOCK, EV_PAGE_READ, EV_RUSAGE, EV_OUTPUT, EV_COUNT_OPEN, EV_COUNT_CLOSE };
static const char *const phase_name[] = { "prev", "prefix", "pred", "target" };
static const char *const count_name[] = { "closed", "open", "read", "fail" };
static const char *const event_name[] = { "clock", "kernel_first", "count_read", "cpu_clock", "page_read",
                                          "rusage", "output", "count_open", "count_close" };

/* One kernel on a range for a time. k < 0: this part is absent ("-"). */
struct part {
    int k;
    uint64_t size;
    long ms;
};

/* One line of the plan. */
struct trial {
    char *f[PLAN_FIELDS]; /* the fields as text, for the S row */
    int nwin, count, bins;
    long win_ms;
    struct part prev, pfx, pred, tgt;
};

struct bin {
    int64_t t_end;  /* a clock read of the window loop */
    uint64_t bytes; /* bytes since the start of the window */
};

/* One window. set_windows() fills the first group of fields before the first
 * trial. timed_sequence() fills the second group. */
struct win {
    int k, phase, widx;
    uint64_t size;
    uint64_t passes; /* passes between two clock reads */
    int64_t dur_ns;
    struct bin *bin; /* NULL: no bins */
    int bin_cap;

    int nbin;
    uint64_t bytes;
    int64_t t_start, t_end; /* CLOCK_MONOTONIC, ns */
};

/* The record of one trial. */
struct trec {
    struct win *win;
    int nw;
    struct counts *cnt; /* count "read": nwin + 1 readings, one per target boundary */
    struct page pg[2];  /* before and after the timed sequence */
    long long vm[2][4];
    uint64_t cpu[2];
    long nvcsw[2], nivcsw[2];
    long minflt[2]; /* minor page faults of the thread, for the --trace check */
    int state;   /* CS_* */
    int sink_ok; /* 1, 0, or -1 if the trial ran no old read */
    int read_fail, close_fail;
};

struct tev {
    int64_t t;
    int widx;
    uint8_t ev, phase;
};

/* The worker of the trial mode. */
struct tw {
    struct thread t; /* a, group_fd, ev_pos, nopen: used as in the interval mode */
    uint64_t v;      /* every word of the buffer holds v */
    int fd[MAX_EV], nfd;
    int group_open; /* an open was tried and no close followed */
    int open_fail;  /* events that did not open */
    int close_fail, read_fail;
    char open_err[160];
    /* --trace */
    struct tev *log;
    long nlog, ndrop;
    int64_t last_t;
    int cur_phase, cur_widx;
};

static struct {
    const char *path;
    uint64_t hash;
    char *pair[MAX_PAIRS];
    int npair;
    struct trial *tr;
    int n;
    int ctl_cpu, trace;
/* bwx10+ */
    size_t rec_pad; /* --rec-pad: unused bytes before win[] in the record block */
    int hot_copy;   /* --hot-copy: timed_sequence_hot() runs the windows */
/* bwx10- */
} plan;

static struct trec *rec;
static struct {
    size_t windows, bins, counts, trace, bytes;
} recsz;

/* --trace. An event that is not a clock read carries the time of the latest
 * clock read: the trace adds no clock read of its own. */
static inline void tev_add(struct tw *w, int ev, int phase, int widx)
{
    if (!w->log)
        return;
    if (w->nlog == TRACE_CAP) {
        w->ndrop++;
        return;
    }
    w->log[w->nlog++] = (struct tev){ .t = w->last_t, .widx = widx, .ev = (uint8_t)ev, .phase = (uint8_t)phase };
}

static inline int64_t tclock(struct tw *w)
{
    int64_t t = now_ns();
    if (w->log) {
        w->last_t = t;
        tev_add(w, EV_CLOCK, 0, 0);
    }
    return t;
}

static uint64_t tcpu(struct tw *w)
{
    uint64_t c = cpu_ns();
    tev_add(w, EV_CPU_CLOCK, 0, 0);
    return c;
}

/* Every kernel call of a trial goes through here, and from here through the
 * unchanged call(). The trace gets the first call of each window. */
static inline void tcall(struct tw *w, const struct win *r, volatile uint64_t *sink)
{
    if (w->log && (r->phase != w->cur_phase || r->widx != w->cur_widx)) {
        w->cur_phase = r->phase;
        w->cur_widx = r->widx;
        tev_add(w, EV_KERNEL_FIRST, r->phase, r->widx);
    }
    call(&kernels[r->k], &w->t, 0, r->size, 0, sink);
}

/* Group read and thread CPU clock, at a boundary of a target window. Not
 * inlined: build8.sh lists the branch targets of timed_sequence(), and this
 * function must be one name there. */
__attribute__((noinline)) static void tcount(struct tw *w, struct counts *c)
{
    uint64_t buf[3 + MAX_EV];
    if (w->t.group_fd >= 0) {
        ssize_t want = (ssize_t)((3 + (size_t)w->t.nopen) * sizeof buf[0]);
        if (read(w->t.group_fd, buf, sizeof buf) != want || buf[0] != (uint64_t)w->t.nopen) {
            w->read_fail++;
        } else {
            c->enabled = buf[1];
            c->running = buf[2];
            for (int i = 0; i < w->t.nopen; i++)
                c->val[i] = buf[3 + i];
        }
        tev_add(w, EV_COUNT_READ, 0, 0);
    }
    c->cpu_ns = tcpu(w);
}

/*
 * The timed sequence of one trial. Each window runs whole passes over
 * [0, size) and reads the clock after every "passes" passes. It ends at the
 * first clock read at or after its duration. At a boundary the clock is read
 * for the end of the window and again for the start of the next one, so the
 * gap is measured. No output, allocation, page read, sleep or warm-up pass
 * is in here. Not inlined: build8.sh and test_runner8.py read the branch
 * targets of this function from the machine code. Only clock_gettime, the
 * kernel call of call() and tcount() are allowed there.
 */
__attribute__((noinline)) static void timed_sequence(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)
{
    for (int i = 0; i < r->nw; i++) {
        struct win *x = &r->win[i];
        uint64_t bytes = 0;
        int64_t t0, t1, next_bin;
        int nbin = 0;

        if (count_read && x->phase == PH_TARGET)
            tcount(w, &r->cnt[x->widx]);
        t0 = tclock(w);
        next_bin = t0 + BIN_NS;
        do {
            for (uint64_t c = 0; c < x->passes; c++) {
                tcall(w, x, sink);
                bytes += x->size;
            }
            t1 = tclock(w);
            /* A bin closes on this clock read if its requested end has
             * passed. The last clock read of the window closes the last bin. */
            if (x->bin && (t1 >= next_bin || t1 - t0 >= x->dur_ns) && nbin < x->bin_cap) {
                x->bin[nbin].t_end = t1;
                x->bin[nbin].bytes = bytes;
                nbin++;
                while (next_bin <= t1)
                    next_bin += BIN_NS;
            }
        } while (t1 - t0 < x->dur_ns);
        x->bytes = bytes;
        x->t_start = t0;
        x->t_end = t1;
        x->nbin = nbin;
    }
    if (count_read)
        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);
}

/* bwx10+ */
/* tcall() for timed_sequence_hot(): the kernel index, the phase, the window
 * index and the size come by value, so no field of win[i] is read here. */
static inline void tcall_hot(struct tw *w, int k, int phase, int widx, uint64_t size, volatile uint64_t *sink)
{
    if (w->log && (phase != w->cur_phase || widx != w->cur_widx)) {
        w->cur_phase = phase;
        w->cur_widx = widx;
        tev_add(w, EV_KERNEL_FIRST, phase, widx);
    }
    call(&kernels[k], &w->t, 0, size, 0, sink);
}

/*
 * --hot-copy: timed_sequence() with one difference. Before the start clock
 * read of a window it copies the fields of win[i] that the window loop needs
 * into local variables. After the end clock read it stores bytes, t_start,
 * t_end and nbin. Between the first pass and the last pass of a window it
 * does not read or write win[i]. The compiler cannot read a field again
 * inside the loop in place of the local copy: the loop calls a kernel
 * through a pointer, and such a call may change any memory. The self-test
 * checks it on the machine code (test_hot_touch). The same rules as for
 * timed_sequence() hold for the calls made here.
 */
__attribute__((noinline)) static void timed_sequence_hot(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)
{
    for (int i = 0; i < r->nw; i++) {
        struct win *x = &r->win[i];
        const int k = x->k, phase = x->phase, widx = x->widx, bin_cap = x->bin_cap;
        const uint64_t size = x->size, passes = x->passes;
        const int64_t dur_ns = x->dur_ns;
        struct bin *const bin = x->bin;
        uint64_t bytes = 0;
        int64_t t0, t1, next_bin;
        int nbin = 0;

        if (count_read && phase == PH_TARGET)
            tcount(w, &r->cnt[widx]);
        t0 = tclock(w);
        next_bin = t0 + BIN_NS;
        do {
            for (uint64_t c = 0; c < passes; c++) {
                tcall_hot(w, k, phase, widx, size, sink);
                bytes += size;
            }
            t1 = tclock(w);
            if (bin && (t1 >= next_bin || t1 - t0 >= dur_ns) && nbin < bin_cap) {
                bin[nbin].t_end = t1;
                bin[nbin].bytes = bytes;
                nbin++;
                while (next_bin <= t1)
                    next_bin += BIN_NS;
            }
        } while (t1 - t0 < dur_ns);
        x->bytes = bytes;
        x->t_start = t0;
        x->t_end = t1;
        x->nbin = nbin;
    }
    if (count_read)
        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);
}

/* bwx10- */
static void count_close(struct tw *w)
{
    for (int i = 0; i < w->nfd; i++)
        if (close(w->fd[i]) != 0)
            w->close_fail++;
    w->nfd = 0;
    w->t.group_fd = -1;
    w->t.nopen = 0;
    w->group_open = 0;
    w->open_fail = 0;
    tev_add(w, EV_COUNT_CLOSE, 0, 0);
}

/* One group, user mode only, opened by the pinned worker for itself. The
 * events count from the open on. An event that does not open is counted in
 * open_fail and is printed as NA. */
static void count_open(struct tw *w)
{
    w->t.group_fd = -1;
    w->t.nopen = 0;
    w->nfd = 0;
    w->open_fail = 0;
    for (int e = 0; e < cfg.nev; e++) {
        struct perf_event_attr a;
        memset(&a, 0, sizeof a);
        a.type = (uint32_t)cfg.pmu_type;
        a.size = sizeof a;
        a.config = cfg.ev_code[e];
        a.exclude_kernel = 1;
        a.exclude_hv = 1;
        a.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, w->t.group_fd, 0);
        if (fd < 0) {
            if (w->open_fail++ == 0)
                snprintf(w->open_err, sizeof w->open_err, "%s type %ld code 0x%llx: %s", cfg.ev_name[e], cfg.pmu_type,
                         (unsigned long long)cfg.ev_code[e], strerror(errno));
            w->t.ev_pos[e] = -1;
            continue;
        }
        w->t.ev_pos[e] = w->t.nopen++;
        w->fd[w->nfd++] = fd;
        if (w->t.group_fd < 0)
            w->t.group_fd = fd;
    }
    w->group_open = 1;
    tev_add(w, EV_COUNT_OPEN, 0, 0);
}

static void page_read(struct tw *w, struct trec *r, int at)
{
    uint64_t *buf[1] = { w->t.a };
    read_smaps(&r->pg[at], buf, 1);
    read_vmstat(r->vm[at]);
    tev_add(w, EV_PAGE_READ, 0, 0);
}

/* Context-switch counts of the calling thread. -1: not readable. */
static void switches(struct tw *w, struct trec *r, int at)
{
    struct rusage ru;
    int ok = getrusage(RUSAGE_THREAD, &ru) == 0;
    r->nvcsw[at] = ok ? ru.ru_nvcsw : -1;
    r->nivcsw[at] = ok ? ru.ru_nivcsw : -1;
    r->minflt[at] = ok ? ru.ru_minflt : -1;
    tev_add(w, EV_RUSAGE, 0, 0);
}

/* The index of the first target window whose counters ran for less time
 * than they were enabled, or -1. cnt holds nwin + 1 readings. */
static int first_multiplexed(const struct counts *cnt, int nwin)
{
    for (int i = 0; i < nwin; i++)
        if (cnt[i + 1].running - cnt[i].running < cnt[i + 1].enabled - cnt[i].enabled)
            return i;
    return -1;
}

/* One trial: the work before the timed sequence, the timed sequence, the
 * work after it. Prints nothing. */
static void run_trial(struct tw *w, const struct trial *p, struct trec *r, volatile uint64_t *sink)
{
    uint64_t expect = 0;
    int old = -1;

    if (p->count == CS_CLOSED && w->group_open)
        count_close(w);
    else if (p->count != CS_CLOSED && !w->group_open)
        count_open(w);
    r->state = p->count != CS_CLOSED && w->open_fail ? CS_FAIL : p->count;
    r->close_fail = w->close_fail;
    w->close_fail = 0;
    w->read_fail = 0;

    /* The last old read of the trial must leave the sum of its range in the
     * sink. The sink starts with another value, so an old value cannot pass. */
    for (int i = 0; i < r->nw; i++)
        if (kernels[r->win[i].k].type == T_OLDREAD)
            old = i;
    if (old >= 0) {
        expect = w->v * (r->win[old].size / 8);
        *sink = expect + 1;
    }

    page_read(w, r, 0);
    switches(w, r, 0);
    r->cpu[0] = tcpu(w);
/* bwx10+ */
    /* --hot-copy selects the other function. The statement after this block
     * is the else branch. */
    if (plan.hot_copy)
        timed_sequence_hot(w, r, p->count == CS_READ, sink);
    else
/* bwx10- */
    timed_sequence(w, r, p->count == CS_READ, sink);
    r->cpu[1] = tcpu(w);
    switches(w, r, 1);
    page_read(w, r, 1);
    r->sink_ok = old < 0 ? -1 : *sink == expect;
    r->read_fail = w->read_fail;
}

static int trial_windows(const struct trial *p)
{
    return (p->prev.k >= 0) + 4 * (p->pfx.k >= 0) + (p->pred.k >= 0) + p->nwin;
}

/* Bins that one target window can close: one per 10 ms that ends inside the
 * window, one at the end of the window, and one spare. */
static int window_bins(const struct trial *p)
{
    return p->bins ? (int)(p->win_ms / 10) + 2 : 0;
}

/* Fills the plan part of the windows of one trial. bin: storage for
 * nwin * window_bins(p) bins. */
static void set_windows(const struct trial *p, struct win *win, struct bin *bin)
{
    const struct {
        const struct part *part;
        int phase, n;
    } ph[4] = { { &p->prev, PH_PREV, 1 }, { &p->pfx, PH_PREFIX, 4 }, { &p->pred, PH_PRED, 1 }, { &p->tgt, PH_TARGET, p->nwin } };
    struct win *x = win;
    for (int i = 0; i < 4; i++) {
        const struct part *part = ph[i].part;
        if (part->k < 0)
            continue;
        for (int j = 0; j < ph[i].n; j++, x++) {
            memset(x, 0, sizeof *x);
            x->k = part->k;
            x->phase = ph[i].phase;
            x->widx = j;
            x->size = part->size;
            x->passes = CHECK_BYTES / part->size ? CHECK_BYTES / part->size : 1;
            x->dur_ns = (ph[i].phase == PH_TARGET ? p->win_ms : part->ms / ph[i].n) * 1000000L;
            if (ph[i].phase == PH_TARGET && p->bins) {
                x->bin_cap = window_bins(p);
                x->bin = bin + (size_t)j * (size_t)x->bin_cap;
            }
        }
    }
}

/* The record storage of all trials: one block, sized from the plan, written
 * once here so that no page of it is first touched during a trial.
 * plan_trial() has filled recsz and has checked its bound. */
static void alloc_records(struct tw *w)
{
    char *mem = malloc(recsz.bytes);
    if (!mem) {
        fprintf(stderr, "no memory for %zu bytes of records\n", recsz.bytes);
        exit(2);
    }
    memset(mem, 0, recsz.bytes);
    /* gcc joins malloc and memset into calloc, and calloc does not write a
     * fresh block. One volatile store per page is the first touch. */
    for (size_t at = 0; at < recsz.bytes; at += (size_t)page_bytes)
        ((volatile char *)mem)[at] = 0;
    ((volatile char *)mem)[recsz.bytes - 1] = 0;
    rec = (struct trec *)mem;
    struct win *win = (struct win *)(rec + plan.n);
/* bwx10+ */
    /* --rec-pad: win[] starts this many bytes later. With 0 nothing moves. */
    win = (struct win *)((char *)win + plan.rec_pad);
/* bwx10- */
    struct counts *cnt = (struct counts *)(win + recsz.windows);
    struct bin *bin = (struct bin *)(cnt + recsz.counts);
    if (plan.trace)
        w->log = (struct tev *)(bin + recsz.bins);
    for (int i = 0; i < plan.n; i++) {
        const struct trial *p = &plan.tr[i];
        rec[i].win = win;
        rec[i].nw = trial_windows(p);
        rec[i].cnt = p->count == CS_READ ? cnt : NULL;
        set_windows(p, win, bin);
        win += rec[i].nw;
        bin += (size_t)p->nwin * (size_t)window_bins(p);
        if (p->count == CS_READ)
            cnt += p->nwin + 1;
    }
}

static void print_s(int i)
{
    const struct trial *p = &plan.tr[i];
    printf("S");
    for (int f = 0; f < PLAN_FIELDS; f++)
        printf(",%s", p->f[f]);
    printf(",%s,%s\n", i ? plan.tr[i - 1].f[1] : "none", i ? plan.tr[i - 1].f[6] : "none");
}

static void print_p8(int i, const char *when, const struct page *pg, const long long vm[4])
{
    printf("P,%d,%s", i, when);
    print_na(pg->kb_total);
    print_na(pg->kb_huge);
    for (int k = 0; k < 4; k++)
        print_na(vm[k]);
    printf("\n");
}

/* All rows of one trial after its S row. */
static void emit_trial(struct tw *w, int i)
{
    const struct trial *p = &plan.tr[i];
    const struct trec *r = &rec[i];
    int g = r->nw - p->nwin; /* index of target window 0 */
    int64_t max_gap = -1;

    tev_add(w, EV_OUTPUT, 0, 0);
    print_p8(i, "pre", &r->pg[0], r->vm[0]);
    for (int k = 0; k < r->nw; k++) {
        const struct win *x = &r->win[k];
        printf("W,%d,%s,%d,%s,%lu,%lu,%lld,%lld\n", i, phase_name[x->phase], x->widx, kernels[x->k].name,
               (unsigned long)x->size, (unsigned long)x->bytes, (long long)(x->t_start - t_base_ns),
               (long long)(x->t_end - t_base_ns));
        if (k && x->t_start - r->win[k - 1].t_end > max_gap)
            max_gap = x->t_start - r->win[k - 1].t_end;
    }
    for (int k = g; k < r->nw; k++)
        for (int b = 0; b < r->win[k].nbin; b++)
            printf("B,%d,%d,%d,%lld,%lu\n", i, r->win[k].widx, b, (long long)(r->win[k].bin[b].t_end - t_base_ns),
                   (unsigned long)r->win[k].bin[b].bytes);
    for (int k = 0; r->cnt && k < p->nwin; k++) {
        const struct counts *c0 = &r->cnt[k], *c1 = &r->cnt[k + 1];
        int group = w->t.group_fd >= 0 && !r->read_fail;
        printf("C,%d,%d", i, k);
        if (group)
            printf(",%llu,%llu", (unsigned long long)(c1->enabled - c0->enabled),
                   (unsigned long long)(c1->running - c0->running));
        else
            printf(",NA,NA");
        printf(",%llu", (unsigned long long)(c1->cpu_ns - c0->cpu_ns));
        for (int e = 0; e < cfg.nev; e++) {
            int at = w->t.ev_pos[e];
            if (!group || at < 0)
                printf(",NA");
            else
                printf(",%llu", (unsigned long long)(c1->val[at] - c0->val[at]));
        }
        printf("\n");
    }
    print_p8(i, "post", &r->pg[1], r->vm[1]);

    if (r->pg[0].kb_huge < 0 || r->pg[1].kb_huge < 0)
        printf("X,%d,coverage_na,the buffer has no exact entry in /proc/self/smaps\n", i);
    if (r->close_fail)
        printf("X,%d,count_close,%d counter descriptors did not close\n", i, r->close_fail);
    if (r->state == CS_FAIL)
        printf("X,%d,count_open,%d of %d events did not open; first: %s\n", i, w->open_fail, cfg.nev, w->open_err);
    if (r->read_fail)
        printf("X,%d,count_read,%d reads of the counter group failed\n", i, r->read_fail);
    if (r->cnt && w->t.group_fd >= 0 && !r->read_fail) {
        int m = first_multiplexed(r->cnt, p->nwin);
        if (m >= 0)
            printf("X,%d,count_multiplexed,target window %d: running_ns %llu below enabled_ns %llu\n", i, m,
                   (unsigned long long)(r->cnt[m + 1].running - r->cnt[m].running),
                   (unsigned long long)(r->cnt[m + 1].enabled - r->cnt[m].enabled));
    }
    if (r->sink_ok == 0)
        printf("X,%d,sink,the last old read did not leave the sum of its range in the sink\n", i);

    printf("E,%d,%lld,%llu", i, (long long)(r->win[r->nw - 1].t_end - r->win[0].t_start),
           (unsigned long long)(r->cpu[1] - r->cpu[0]));
    if (r->nvcsw[0] < 0 || r->nvcsw[1] < 0)
        printf(",NA,NA");
    else
        printf(",%ld,%ld", r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]);
    print_na(g ? r->win[g].t_start - r->win[g - 1].t_end : -1);
    print_na(max_gap);
    if (r->sink_ok < 0)
        printf(",NA");
    else
        printf(",%d", r->sink_ok);
    printf(",%s\n", count_name[r->state]);

    for (long n = 0; n < w->nlog; n++) {
        const struct tev *e = &w->log[n];
        if (e->ev == EV_KERNEL_FIRST)
            printf("TR,%d,%ld,%s:%s:%d,%lld\n", i, n, event_name[e->ev], phase_name[e->phase], e->widx,
                   (long long)(e->t - t_base_ns));
        else
            printf("TR,%d,%ld,%s,%lld\n", i, n, event_name[e->ev], (long long)(e->t - t_base_ns));
    }
    if (w->ndrop)
        printf("# trace_dropped,%d,%ld\n", i, w->ndrop);
    /* --trace: minor page faults of the worker between the two rusage reads.
     * Above 0: a page was first touched inside the timed sequence. */
    if (w->log)
        printf("# minflt,%d,%ld\n", i, r->minflt[0] < 0 || r->minflt[1] < 0 ? -1 : r->minflt[1] - r->minflt[0]);
    fflush(stdout);
}

/* bwx11+ */
/*
 * --evict-mb N. evict_step() maps N MiB of anonymous private memory (plain
 * mmap, no madvise), stores one 8-byte word to every 64 B line in ascending
 * order, in two passes, and unmaps the range. The stores go through a
 * volatile pointer, so gcc keeps every one of them and does not call memset.
 * Purpose: the lines of the benchmark buffer leave the caches. The first
 * touch wrote them, so they were dirty. The next read brings them back from
 * memory, clean.
 * trial_worker() calls it once, after the first touch of the buffer and of
 * the record block and before the first trial. No timed sequence holds it.
 * evict_t holds one clock read before the mmap and one after the munmap.
 * Returns 0, or -1 with the text of the error in evict_err.
 * These definitions stand after timed_sequence_hot() and after every other
 * variable of the trial mode, so nothing before them moves.
 */
static long evict_mb;      /* --evict-mb: 0 = no evict step */
static int64_t evict_t[2]; /* CLOCK_MONOTONIC, ns */
static char evict_err[160];

__attribute__((noinline)) static int evict_step(void)
{
    size_t len = (size_t)evict_mb << 20;
    evict_t[0] = now_ns();
    volatile uint64_t *m = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (m == MAP_FAILED) {
        snprintf(evict_err, sizeof evict_err, "mmap of %ld MiB failed: %s", evict_mb, strerror(errno));
        return -1;
    }
    for (int pass = 0; pass < 2; pass++)
        for (size_t i = 0; i < len / 8; i += 8)
            m[i] = (uint64_t)i + (uint64_t)pass + 1;
    if (munmap((void *)m, len) != 0) {
        snprintf(evict_err, sizeof evict_err, "munmap of %ld MiB failed: %s", evict_mb, strerror(errno));
        return -1;
    }
    evict_t[1] = now_ns();
    return 0;
}

/* bwx11- */
static void *trial_worker(void *arg)
{
    struct tw *w = arg;
    volatile uint64_t sink = 0;
    int madvise_ok;

    pin_cpu(cfg.cpus[0]);
    if (sched_getcpu() != cfg.cpus[0]) {
        fprintf(stderr, "the worker runs on CPU %d, not on CPU %d\n", sched_getcpu(), cfg.cpus[0]);
        exit(2);
    }
    w->v = ((uint64_t)getpid() + 1) * 0x9E3779B97F4A7C15ULL;
    w->t.group_fd = -1;
    w->t.a = alloc_buf();
    /* alloc_buf() does not return the result of its madvise. The same request
     * again gives it. */
    madvise_ok = madvise(w->t.a, buf_len(), cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) == 0;
    k_write(w->t.a, cfg.bytes / 8, w->v); /* first touch by the pinned worker */
    alloc_records(w);
    w->last_t = t_base_ns;

    printf("# bwx8 trial mode: GB = 1e9 bytes; times are whole ns since process start on CLOCK_MONOTONIC\n"
           "# S,trial,cond,rep,prev,pfx,pred,tgt,nwin,win_ms,count,bins,prev_cond,prev_tgt\n"
           "# P,trial,when,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n"
           "# W,trial,phase,widx,kernel,pass_bytes,bytes,t_start_ns,t_end_ns\n"
           "# B,trial,widx,bin,t_end_ns,bytes_since_window_start\n"
           "# C,trial,widx,enabled_ns,running_ns,cputime_ns");
    for (int e = 0; e < cfg.nev; e++)
        printf(",%s", cfg.ev_name[e]);
    printf("\n# E,trial,wall_ns,cpu_ns,nvcsw,nivcsw,gap_ns,max_boundary_gap_ns,sink_ok,count_state\n"
           "# X,trial,code,text\n"
           "# TR,trial,n,event,t_ns; t_ns of an event that is not a clock read is the time of the clock read before it\n");
    printf("M,mode,trial\nM,cpu,%d\nM,ctl_cpu,%d\nM,bytes,%lu\nM,thp,%s\nM,madvise_ok,%d\nM,check_bytes,%lu\nM,kernels,%s\n",
           cfg.cpus[0], plan.ctl_cpu, (unsigned long)cfg.bytes, cfg.use_thp ? "madvise" : "nohugepage", madvise_ok,
           (unsigned long)CHECK_BYTES, STANDIN ? "STAND-IN" : "aarch64");
    printf("M,plan_fnv1a64,%016llx\nM,ntrials,%d\nM,rec_windows,%zu\nM,rec_bins,%zu\nM,rec_counts,%zu\nM,rec_trace,%zu\n"
           "M,rec_bytes,%zu\nM,trace,%d\n",
           (unsigned long long)plan.hash, plan.n, recsz.windows, recsz.bins, recsz.counts, recsz.trace, recsz.bytes,
           plan.trace);
/* bwx10+ */
    /* Addresses in hex without "0x", as in the K rows. rec_addr: the record
     * block. win_addr: win[0] of trial 0. stack_addr: the sink of the worker. */
    printf("M,rec_pad,%zu\nM,hot_copy,%d\nM,rec_addr,%lx\nM,win_addr,%lx\nM,win_size,%zu\nM,stack_addr,%lx\nM,buf_addr,%lx\n"
           "M,tw_addr,%lx\n",
           plan.rec_pad, plan.hot_copy, (unsigned long)(uintptr_t)rec, (unsigned long)(uintptr_t)rec[0].win,
           sizeof(struct win), (unsigned long)(uintptr_t)&sink, (unsigned long)(uintptr_t)w->t.a,
           (unsigned long)(uintptr_t)w);
/* bwx10- */
/* bwx11+ */
    /* The evict step. The buffer and the record block are first touched, and
     * no trial has started. With --evict-mb 0 no call is made. A failure
     * ends the process here: the X row is the last row. */
    printf("M,evict_mb,%ld\n", evict_mb);
    if (evict_mb > 0 && evict_step() != 0) {
        printf("X,-1,evict,%s\n", evict_err);
        fflush(stdout);
        exit(2);
    }
    printf("M,evict_ns,%lld\n", (long long)(evict_t[1] - evict_t[0]));
    if (evict_mb > 0 && plan.trace)
        printf("TR,-1,0,evict_start,%lld\nTR,-1,1,evict_end,%lld\n", (long long)(evict_t[0] - t_base_ns),
               (long long)(evict_t[1] - t_base_ns));
/* bwx11- */
    if (cfg.pmu_type < 0)
        printf("M,pmu_type,none\n");
    else
        printf("M,pmu_type,%ld\n", cfg.pmu_type);
    printf("M,events,%s", cfg.nev ? "" : "none");
    for (int e = 0; e < cfg.nev; e++)
        printf("%s%s=0x%llx", e ? ";" : "", cfg.ev_name[e], (unsigned long long)cfg.ev_code[e]);
    printf("\n");
    for (int i = 0; i < plan.npair; i++) {
        char *eq = strchr(plan.pair[i], '=');
        printf("M,plan.%.*s,%s\n", (int)(eq - plan.pair[i]), plan.pair[i], eq + 1);
    }
    for (int k = 0; k < K_COUNT; k++) {
        int used = 0;
        for (int i = 0; i < plan.n && !used; i++) {
            const struct trial *p = &plan.tr[i];
            used = p->prev.k == k || p->pfx.k == k || p->pred.k == k || p->tgt.k == k;
        }
        if (used)
            printf("K,%s,%lx,%lu\n", kernels[k].name, (unsigned long)(uintptr_t)kernels[k].fn,
                   (unsigned long)((uintptr_t)kernels[k].fn % 64));
    }
    if (!madvise_ok)
        printf("X,-1,madvise,the page policy request failed\n");

    for (int i = 0; i < plan.n; i++) {
        w->nlog = w->ndrop = 0;
        w->cur_phase = -1;
        tev_add(w, EV_OUTPUT, 0, 0);
        print_s(i);
        fflush(stdout);
        run_trial(w, &plan.tr[i], &rec[i], &sink);
        emit_trial(w, i);
    }
    if (w->group_open)
        count_close(w);
    if (w->close_fail)
        printf("X,-1,count_close,%d counter descriptors did not close\n", w->close_fail);
    fflush(stdout);
    return NULL;
}

static void plan_bad(int line, const char *fmt, ...)
{
    va_list ap;
    fprintf(stderr, "bad plan %s, line %d: ", plan.path, line);
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fprintf(stderr, "\n");
    exit(2);
}

/* A whole number in [lo, hi] made of digits only. */
static int plan_long(const char *s, long lo, long hi, long *out)
{
    char *end;
    if (*s < '0' || *s > '9')
        return 0;
    errno = 0;
    long v = strtol(s, &end, 10);
    if (*end != '\0' || errno != 0 || v < lo || v > hi)
        return 0;
    *out = v;
    return 1;
}

/* A whole number above 0 with an optional K, M or G. */
static int plan_size(const char *s, uint64_t *out)
{
    char *end;
    int shift = 0;
    if (*s < '0' || *s > '9')
        return 0;
    errno = 0;
    unsigned long long v = strtoull(s, &end, 10);
    switch (*end) {
    case 'K': shift = 10; end++; break;
    case 'M': shift = 20; end++; break;
    case 'G': shift = 30; end++; break;
    }
    if (*end != '\0' || errno != 0 || v == 0 || v > (UINT64_MAX >> shift))
        return 0;
    *out = (uint64_t)v << shift;
    return 1;
}

/* "KERNEL@SIZE:MS" (with_ms, where "-" is also allowed) or "KERNEL@SIZE". */
static void plan_part(int line, const char *what, const char *s, int with_ms, struct part *p)
{
    char buf[96];
    p->k = -1;
    p->size = 0;
    p->ms = 0;
    if (with_ms && !strcmp(s, "-"))
        return;
    if (strlen(s) >= sizeof buf)
        plan_bad(line, "%s is too long", what);
    strcpy(buf, s);
    char *at = strchr(buf, '@'), *colon = at ? strchr(at, ':') : NULL;
    if (!at || with_ms != (colon != NULL))
        plan_bad(line, "%s '%s' is not %s", what, s, with_ms ? "'-' or KERNEL@SIZE:MS" : "KERNEL@SIZE");
    *at = '\0';
    if (colon)
        *colon = '\0';
    int k = 0;
    while (k < K_COUNT && strcmp(buf, kernels[k].name))
        k++;
    if (k == K_COUNT)
        plan_bad(line, "%s: unknown kernel '%s'", what, buf);
    if (kernels[k].type != T_READ && kernels[k].type != T_OLDREAD)
        plan_bad(line, "%s: '%s' is not a read kernel", what, buf);
    if (!plan_size(at + 1, &p->size) || p->size % 256 != 0 || p->size > cfg.bytes)
        plan_bad(line, "%s: size '%s' must be a multiple of 256, above 0 and at most --bytes (%lu)", what, at + 1,
                 (unsigned long)cfg.bytes);
    if (colon && !plan_long(colon + 1, 1, MAX_MS, &p->ms))
        plan_bad(line, "%s: bad duration '%s' (whole ms from 1 to %ld)", what, colon + 1, MAX_MS);
    p->k = k;
}

/* Line 2: "# key=value key=value ...". bytes and cpu must equal the options. */
static void plan_pairs(char *s)
{
    int have_bytes = 0, have_cpu = 0;
    if (strncmp(s, "# ", 2))
        plan_bad(2, "the line must start with '# '");
    for (char *tok = s + 2, *sp; tok; tok = sp ? sp + 1 : NULL) {
        sp = strchr(tok, ' ');
        if (sp)
            *sp = '\0';
        char *eq = strchr(tok, '=');
        if (!eq || eq == tok || strchr(tok, ',') || plan.npair == MAX_PAIRS)
            plan_bad(2, "bad key=value pair '%s'", tok);
        plan.pair[plan.npair++] = tok;
        if (!strncmp(tok, "bytes=", 6)) {
            uint64_t b;
            if (!plan_size(eq + 1, &b) || b != cfg.bytes)
                plan_bad(2, "%s differs from --bytes %lu", tok, (unsigned long)cfg.bytes);
            have_bytes = 1;
        }
        if (!strncmp(tok, "cpu=", 4)) {
            long c;
            if (!plan_long(eq + 1, 0, MAX_USE_CPU, &c) || c != cfg.cpus[0])
                plan_bad(2, "%s differs from --cpus %d", tok, cfg.cpus[0]);
            have_cpu = 1;
        }
    }
    if (!have_bytes || !have_cpu)
        plan_bad(2, "bytes= and cpu= are needed");
}

static void plan_trial(int line, char *s)
{
    char *f[PLAN_FIELDS];
    int nf = 0;
    long v;
    for (char *tok = s, *sp; tok; tok = sp ? sp + 1 : NULL) {
        sp = strchr(tok, ' ');
        if (sp)
            *sp = '\0';
        if (nf == PLAN_FIELDS || *tok == '\0')
            plan_bad(line, "%d fields separated by single spaces are needed", PLAN_FIELDS);
        f[nf++] = tok;
    }
    if (nf != PLAN_FIELDS)
        plan_bad(line, "%d fields separated by single spaces are needed, %d found", PLAN_FIELDS, nf);
    plan.tr = realloc(plan.tr, ((size_t)plan.n + 1) * sizeof *plan.tr);
    if (!plan.tr)
        plan_bad(line, "no memory");
    struct trial *p = &plan.tr[plan.n];
    memcpy(p->f, f, sizeof f);
    if (!plan_long(f[0], 0, 1000000, &v) || v != plan.n)
        plan_bad(line, "trial '%s': the trial numbers must be 0, 1, 2, ... (%d expected)", f[0], plan.n);
    if (strchr(f[1], ','))
        plan_bad(line, "cond '%s' holds a comma", f[1]);
    if (!plan_long(f[2], 1, 4, &v))
        plan_bad(line, "rep '%s' is not 1 to 4", f[2]);
    plan_part(line, "prev", f[3], 1, &p->prev);
    plan_part(line, "pfx", f[4], 1, &p->pfx);
    plan_part(line, "pred", f[5], 1, &p->pred);
    plan_part(line, "tgt", f[6], 0, &p->tgt);
    if (p->pfx.k >= 0 && p->pfx.ms % 4 != 0)
        plan_bad(line, "pfx duration %ld ms is not a multiple of 4", p->pfx.ms);
    if (!plan_long(f[7], 1, MAX_NWIN, &v))
        plan_bad(line, "nwin '%s' is not 1 to %d", f[7], MAX_NWIN);
    p->nwin = (int)v;
    if (!plan_long(f[8], 1, MAX_MS, &p->win_ms))
        plan_bad(line, "win_ms '%s' is not 1 to %ld", f[8], MAX_MS);
    p->count = !strcmp(f[9], "closed") ? CS_CLOSED : !strcmp(f[9], "open") ? CS_OPEN : !strcmp(f[9], "read") ? CS_READ : -1;
    if (p->count < 0)
        plan_bad(line, "count '%s' is not closed, open or read", f[9]);
    if (strcmp(f[10], "0") && strcmp(f[10], "1"))
        plan_bad(line, "bins '%s' is not 0 or 1", f[10]);
    p->bins = f[10][0] == '1';
    plan.n++;
    /* The record storage is bounded here, before the process pins or
     * allocates. */
    recsz.windows += (size_t)trial_windows(p);
    recsz.bins += (size_t)p->nwin * (size_t)window_bins(p);
    if (p->count == CS_READ)
        recsz.counts += (size_t)p->nwin + 1;
    recsz.trace = plan.trace ? TRACE_CAP : 0;
    recsz.bytes = (size_t)plan.n * sizeof(struct trec) + recsz.windows * sizeof(struct win) +
                  recsz.counts * sizeof(struct counts) + recsz.bins * sizeof(struct bin) + recsz.trace * sizeof(struct tev);
/* bwx10+ */
    recsz.bytes += plan.rec_pad;
/* bwx10- */
    if (recsz.bytes > MAX_REC_BYTES)
        plan_bad(line, "the records of the plan up to this line need %zu bytes, the bound is %lu bytes", recsz.bytes,
                 MAX_REC_BYTES);
}

/* Reads and checks the whole plan. Returns only if it can run. */
static void read_plan(void)
{
    size_t cap = 1 << 16, len = 0, got;
    FILE *f = fopen(plan.path, "rb");
    char *text = malloc(cap + 1);
    int line = 0;
    if (!f || !text) {
        fprintf(stderr, "cannot read the plan %s: %s\n", plan.path, strerror(errno));
        exit(2);
    }
    while ((got = fread(text + len, 1, cap - len, f)) > 0) {
        len += got;
        if (len == cap && !(text = realloc(text, (cap *= 2) + 1))) {
            fprintf(stderr, "no memory for the plan\n");
            exit(2);
        }
    }
    if (ferror(f)) {
        fprintf(stderr, "cannot read the plan %s\n", plan.path);
        exit(2);
    }
    fclose(f);
    text[len] = '\0';
    plan.hash = 14695981039346656037ULL; /* FNV-1a, 64 bit, over the bytes of the file */
    for (size_t i = 0; i < len; i++)
        plan.hash = (plan.hash ^ (uint8_t)text[i]) * 1099511628211ULL;
    if (strlen(text) != len)
        plan_bad(0, "the file holds a zero byte");
    for (char *s = text, *next; *s; s = next) {
        char *nl = strchr(s, '\n');
        next = nl ? nl + 1 : s + strlen(s);
        if (nl)
            *nl = '\0';
        line++;
        if (line == 1) {
            if (strcmp(s, PLAN_LINE1))
                plan_bad(1, "the line must be '%s'", PLAN_LINE1);
        } else if (line == 2) {
            plan_pairs(s);
        } else if (line == 3) {
            if (strcmp(s, PLAN_LINE3))
                plan_bad(3, "the line must be '%s'", PLAN_LINE3);
        } else {
            plan_trial(line, s);
        }
    }
    if (line < 3)
        plan_bad(line + 1, "the three header lines are needed");
    if (plan.n == 0)
        plan_bad(line + 1, "no trial");
}

static void trial_usage(void)
{
    fprintf(stderr,
            "usage: bwx8 --trial --cpus C --bytes B --plan FILE [--ctl-cpu N] [--no-thp] [--trace]\n"
            "            [--pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"
            "  --cpus: exactly one CPU. --ctl-cpu: CPU of the controlling thread (default 0), another CPU.\n"
            "  the counter settings are required if a trial of the plan has count open or read\n");
/* bwx10+ */
    fprintf(stderr,
            "  bwx10 adds: [--rec-pad BYTES] [--hot-copy]\n"
            "  --rec-pad: unused bytes before the window records, a multiple of %zu from 0 to 65536 (default 0)\n"
            "  --hot-copy: the window loop works on a local copy of its window record\n",
            _Alignof(struct win));
/* bwx10- */
/* bwx11+ */
    fprintf(stderr,
            "  bwx11 adds: [--evict-mb N]\n"
            "  --evict-mb: before the first trial the worker writes N MiB of other memory twice, a whole number\n"
            "              from 0 to 4096 (default 0: no such step)\n");
/* bwx11- */
    exit(2);
}

static int trial_main(int argc, char **argv)
{
    struct tw w;
    pthread_t tid;
    cpu_set_t set;
    int bytes_given = 0, counting = 0;

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        int more = i + 1 < argc;
        if (!strcmp(a, "--trial")) {
        } else if (!strcmp(a, "--no-thp")) {
            cfg.use_thp = 0;
        } else if (!strcmp(a, "--trace")) {
            plan.trace = 1;
/* bwx10+ */
        } else if (!strcmp(a, "--hot-copy")) {
            plan.hot_copy = 1;
        } else if (!strcmp(a, "--rec-pad") && more) {
            long pad = parse_long(argv[++i], "--rec-pad", 0, 65536);
            if (pad % (long)_Alignof(struct win) != 0) {
                fprintf(stderr, "bad --rec-pad: '%s' (a multiple of %zu is needed: the window records stay aligned)\n",
                        argv[i], _Alignof(struct win));
                exit(2);
            }
            plan.rec_pad = (size_t)pad;
/* bwx10- */
/* bwx11+ */
        } else if (!strcmp(a, "--evict-mb") && more) {
            evict_mb = parse_long(argv[++i], "--evict-mb", 0, 4096);
/* bwx11- */
        } else if (!strcmp(a, "--cpus") && more) {
            parse_cpus(argv[++i]);
        } else if (!strcmp(a, "--bytes") && more) {
            cfg.bytes = parse_bytes(argv[++i]);
            bytes_given = 1;
        } else if (!strcmp(a, "--plan") && more) {
            plan.path = argv[++i];
        } else if (!strcmp(a, "--ctl-cpu") && more) {
            plan.ctl_cpu = (int)parse_long(argv[++i], "--ctl-cpu", 0, MAX_USE_CPU);
        } else if (!strcmp(a, "--pmu-type") && more) {
            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);
        } else if (!strcmp(a, "--events") && more) {
            parse_events(argv[++i]);
        } else {
            trial_usage();
        }
    }
    if (cfg.ncpus != 1 || !bytes_given || !plan.path || cfg.bytes % 256 != 0) {
        fprintf(stderr, "--trial needs --cpus with exactly one CPU, --bytes (a multiple of 256) and --plan\n");
        trial_usage();
    }
    if (plan.ctl_cpu == cfg.cpus[0]) {
        fprintf(stderr, "the controlling thread and the worker must not share CPU %d\n", plan.ctl_cpu);
        exit(2);
    }
    if (sched_getaffinity(0, sizeof set, &set) != 0 || !CPU_ISSET(cfg.cpus[0], &set) || !CPU_ISSET(plan.ctl_cpu, &set)) {
        fprintf(stderr, "CPU %d or CPU %d is not in the allowed set of the process\n", cfg.cpus[0], plan.ctl_cpu);
        exit(2);
    }
    read_plan();
    for (int i = 0; i < plan.n; i++)
        counting |= plan.tr[i].count != CS_CLOSED;
    if (counting && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))
        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);
    if (counting && cfg.nev == 0 && getenv("BWX_EVENTS")) {
        char *copy = strdup(getenv("BWX_EVENTS"));
        parse_events(copy);
        free(copy);
    }
    if (counting && (cfg.pmu_type < 0 || cfg.nev == 0)) {
        fprintf(stderr, "the plan has a trial with count open or read: --pmu-type and --events are needed "
                        "(or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");
        exit(2);
    }

    /* The plan can run. The controlling thread pins itself, starts the
     * worker and waits. It never touches the buffer. */
    pin_cpu(plan.ctl_cpu);
    memset(&w, 0, sizeof w);
    if (pthread_create(&tid, NULL, trial_worker, &w) != 0) {
        perror("pthread_create");
        return 2;
    }
    pthread_join(tid, NULL);
    return 0;
}

/* bwx11+ */
#if 0
/* bwx11- */
#include "bwx10_selftest.c"
/* bwx11+ */
#endif
#include "bwx11_selftest.c"
/* bwx11- */

int main(int argc, char **argv)
{
    int threads_given = 0;
    char seq_text[1024] = "";
    t_base_ns = now_ns();
    page_bytes = sysconf(_SC_PAGESIZE);
    cfg.bytes = 1UL << 20;
    restrict_cpus();
    for (int i = 1; i < argc; i++)
        if (!strcmp(argv[i], "--trial"))
            return trial_main(argc, argv);

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
