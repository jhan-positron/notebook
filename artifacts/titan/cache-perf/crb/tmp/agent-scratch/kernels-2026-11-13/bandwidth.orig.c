/*
 * bandwidth.c - multi-thread streaming bandwidth: read, write, copy.
 *
 * Every thread owns its buffers (allocated and first-touched by that thread),
 * so timing contains no page faults. All threads start on a barrier, run
 * whole passes over their buffer until --min-ms has elapsed, and record
 * bytes moved and their own elapsed time. GB means 1e9 bytes throughout.
 */
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define HUGE_BYTES (2UL << 20)
#define MAX_CPUS 1024
#define MAX_REPS 32
#define CHECK_BYTES (8UL << 20) /* clock is read after at least this many bytes */

enum kernel { K_READ, K_WRITE, K_COPY, K_ASMREAD, K_ASMWRITE, K_ASMCOPY, K_COUNT };
static const char *kernel_name[K_COUNT] = { "read", "write", "copy", "asmread", "asmwrite", "asmcopy" };

static struct {
    int threads;
    int ncpus;
    int cpus[MAX_CPUS];
    uint64_t bytes;
    int run[K_COUNT];
    double min_s;
    int reps;
    int use_thp;
    int per_thread; /* --per-thread: one line per thread with its CPU and best GB/s */
} cfg = { .threads = 1, .min_s = 0.5, .reps = 3, .use_thp = 1 };

struct result {
    uint64_t bytes;
    double elapsed_s;
};

struct thread {
    int idx;
    int cpu;
    uint64_t *a, *b;
    struct result res[K_COUNT][MAX_REPS];
    pthread_t tid;
};

static pthread_barrier_t bar;

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
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
    if (end == s || *end != '\0' || v <= 0) {
        fprintf(stderr, "bad size: %s\n", s);
        exit(2);
    }
    return (uint64_t)(v * mul);
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
        if (e == tok || *e != '\0' || lo < 0 || hi < lo || hi >= CPU_SETSIZE || step < 1) {
            fprintf(stderr, "bad cpu list: %s\n", tok);
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

static uint64_t *alloc_buf(uint64_t bytes)
{
    size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);
    uint8_t *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED) {
        perror("mmap");
        exit(2);
    }
    uint8_t *p = (uint8_t *)(((uintptr_t)raw + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));
    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp
     * would still get 2 MiB pages. */
    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)
        perror("madvise (continuing)");
    return (uint64_t *)p;
}

/* 16 independent accumulators keep the loop load-bound: on 128-bit NEON gcc
 * folds them into 8 vector chains, enough to hide a 2-cycle add latency;
 * on AVX-512 they become 2 zmm chains. */
__attribute__((noinline)) static uint64_t k_read(const uint64_t *a, size_t n)
{
    uint64_t s[16] = { 0 };
    for (size_t i = 0; i < n; i += 16)
        for (int j = 0; j < 16; j++)
            s[j] += a[i + j];
    uint64_t sum = 0;
    for (int j = 0; j < 16; j++)
        sum += s[j];
    return sum;
}

__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)
{
    for (size_t i = 0; i < n; i++)
        a[i] = v;
}

__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    for (size_t i = 0; i < n; i++)
        d[i] = s[i];
}

/*
 * asm kernels: the whole hot loop is one inline-asm block, so the compiler
 * cannot add arithmetic, reorder, or drop anything. Each iteration moves
 * 256 B with 8 ldp/stp of q registers (16 B each). The loop body is:
 * 8 x ldp or stp, add, cmp, b.lo. Callers guarantee n * 8 is a multiple of
 * 256 and non-zero. v8-v15 are callee-saved in AAPCS64: naming them as
 * clobbers makes gcc save d8-d15 once per call, which is outside the loop.
 */
#if defined(__aarch64__)
#define HAVE_ASM_KERNELS 1

__attribute__((noinline)) static void k_asmread(const uint64_t *a, size_t n)
{
    const uint64_t *p = a;
    const uint64_t *end = a + n;
    __asm__ volatile(
        "1:\n\t"
        "ldp q0, q1, [%[p]]\n\t"
        "ldp q2, q3, [%[p], #32]\n\t"
        "ldp q4, q5, [%[p], #64]\n\t"
        "ldp q6, q7, [%[p], #96]\n\t"
        "ldp q8, q9, [%[p], #128]\n\t"
        "ldp q10, q11, [%[p], #160]\n\t"
        "ldp q12, q13, [%[p], #192]\n\t"
        "ldp q14, q15, [%[p], #224]\n\t"
        "add %[p], %[p], #256\n\t"
        "cmp %[p], %[end]\n\t"
        "b.lo 1b\n\t"
        : [p] "+r"(p)
        : [end] "r"(end)
        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
          "memory", "cc");
}

__attribute__((noinline)) static void k_asmwrite(uint64_t *a, size_t n, uint64_t v)
{
    uint64_t *p = a;
    const uint64_t *end = a + n;
    __asm__ volatile(
        "dup v0.2d, %[v]\n\t"
        "1:\n\t"
        "stp q0, q0, [%[p]]\n\t"
        "stp q0, q0, [%[p], #32]\n\t"
        "stp q0, q0, [%[p], #64]\n\t"
        "stp q0, q0, [%[p], #96]\n\t"
        "stp q0, q0, [%[p], #128]\n\t"
        "stp q0, q0, [%[p], #160]\n\t"
        "stp q0, q0, [%[p], #192]\n\t"
        "stp q0, q0, [%[p], #224]\n\t"
        "add %[p], %[p], #256\n\t"
        "cmp %[p], %[end]\n\t"
        "b.lo 1b\n\t"
        : [p] "+r"(p)
        : [end] "r"(end), [v] "r"(v)
        : "v0", "memory", "cc");
}

__attribute__((noinline)) static void k_asmcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    uint64_t *dp = d;
    const uint64_t *sp = s;
    const uint64_t *end = s + n;
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
        "stp q0, q1, [%[d]]\n\t"
        "stp q2, q3, [%[d], #32]\n\t"
        "stp q4, q5, [%[d], #64]\n\t"
        "stp q6, q7, [%[d], #96]\n\t"
        "stp q8, q9, [%[d], #128]\n\t"
        "stp q10, q11, [%[d], #160]\n\t"
        "stp q12, q13, [%[d], #192]\n\t"
        "stp q14, q15, [%[d], #224]\n\t"
        "add %[s], %[s], #256\n\t"
        "add %[d], %[d], #256\n\t"
        "cmp %[s], %[end]\n\t"
        "b.lo 1b\n\t"
        : [s] "+r"(sp), [d] "+r"(dp)
        : [end] "r"(end)
        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
          "memory", "cc");
}
#else
#define HAVE_ASM_KERNELS 0
#endif

/* One pass over the thread's buffer; returns bytes moved. The sink is per
 * thread (on its stack) so the read kernels of 120 threads do not all store
 * to one shared cache line. */
static uint64_t pass(enum kernel k, struct thread *t, size_t n, uint64_t v, volatile uint64_t *sink)
{
    switch (k) {
    case K_READ:
        *sink = k_read(t->a, n);
        return cfg.bytes;
    case K_WRITE:
        k_write(t->a, n, v);
        return cfg.bytes;
    case K_COPY:
        k_copy(t->b, t->a, n);
        return 2 * cfg.bytes;
#if HAVE_ASM_KERNELS
    case K_ASMREAD:
        k_asmread(t->a, n);
        return cfg.bytes;
    case K_ASMWRITE:
        k_asmwrite(t->a, n, v);
        return cfg.bytes;
    case K_ASMCOPY:
        k_asmcopy(t->b, t->a, n);
        return 2 * cfg.bytes;
#endif
    default:
        return 0;
    }
}

static void *worker(void *arg)
{
    struct thread *t = arg;
    size_t n = cfg.bytes / 8;
    volatile uint64_t sink;
    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */
    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;
    uint64_t passes_per_check = CHECK_BYTES / cfg.bytes;
    if (passes_per_check == 0)
        passes_per_check = 1;

    if (cfg.ncpus)
        pin_cpu(t->cpu);
    t->a = alloc_buf(cfg.bytes);
    k_write(t->a, n, v); /* first touch by this thread */
    if (cfg.run[K_COPY] || cfg.run[K_ASMCOPY]) {
        t->b = alloc_buf(cfg.bytes);
        k_write(t->b, n, v);
    }

    for (int k = 0; k < K_COUNT; k++) {
        if (!cfg.run[k])
            continue;
        for (int rep = 0; rep < cfg.reps; rep++) {
            pass(k, t, n, v, &sink); /* warm-up */
            pthread_barrier_wait(&bar);
            double t0 = now_s(), t1;
            uint64_t bytes = 0, p = 0;
            do {
                for (uint64_t c = 0; c < passes_per_check; c++, p++)
                    bytes += pass(k, t, n, v + p, &sink);
                t1 = now_s();
            } while (t1 - t0 < cfg.min_s);
            t->res[k][rep].bytes = bytes;
            t->res[k][rep].elapsed_s = t1 - t0;
            pthread_barrier_wait(&bar);
        }
    }
    return NULL;
}

static void usage(void)
{
    fprintf(stderr,
            "usage: bandwidth [--threads T --cpus LIST] [--bytes B] "
            "[--kernel read|write|copy|all|asmread|asmwrite|asmcopy|asmall] "
            "[--min-ms MS] [--reps R] [--no-thp] [--per-thread]\n"
            "  asm* kernels: aarch64 only, loads/stores only, bytes must be a multiple of 256\n");
    exit(2);
}

int main(int argc, char **argv)
{
    int threads_given = 0;
    cfg.bytes = 1UL << 20;
    cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        int more = i + 1 < argc;
        if (!strcmp(a, "--no-thp")) {
            cfg.use_thp = 0;
        } else if (!strcmp(a, "--per-thread")) {
            cfg.per_thread = 1;
        } else if (!strcmp(a, "--threads") && more) {
            cfg.threads = atoi(argv[++i]);
            threads_given = 1;
        } else if (!strcmp(a, "--cpus") && more) {
            parse_cpus(argv[++i]);
        } else if (!strcmp(a, "--bytes") && more) {
            cfg.bytes = parse_bytes(argv[++i]);
        } else if (!strcmp(a, "--min-ms") && more) {
            cfg.min_s = atof(argv[++i]) / 1000.0;
        } else if (!strcmp(a, "--reps") && more) {
            cfg.reps = atoi(argv[++i]);
        } else if (!strcmp(a, "--kernel") && more) {
            const char *k = argv[++i];
            memset(cfg.run, 0, sizeof cfg.run);
            if (!strcmp(k, "all"))
                cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;
            else if (!strcmp(k, "read"))
                cfg.run[K_READ] = 1;
            else if (!strcmp(k, "write"))
                cfg.run[K_WRITE] = 1;
            else if (!strcmp(k, "copy"))
                cfg.run[K_COPY] = 1;
            else if (!strcmp(k, "asmall"))
                cfg.run[K_ASMREAD] = cfg.run[K_ASMWRITE] = cfg.run[K_ASMCOPY] = 1;
            else if (!strcmp(k, "asmread"))
                cfg.run[K_ASMREAD] = 1;
            else if (!strcmp(k, "asmwrite"))
                cfg.run[K_ASMWRITE] = 1;
            else if (!strcmp(k, "asmcopy"))
                cfg.run[K_ASMCOPY] = 1;
            else
                usage();
        } else {
            usage();
        }
    }
    if (threads_given && cfg.ncpus == 0) {
        fprintf(stderr, "--threads requires --cpus\n");
        usage();
    }
    if (cfg.threads < 1 || cfg.reps < 1 || cfg.reps > MAX_REPS || cfg.bytes == 0 || cfg.bytes % 256 != 0)
        usage();
    if (!HAVE_ASM_KERNELS && (cfg.run[K_ASMREAD] || cfg.run[K_ASMWRITE] || cfg.run[K_ASMCOPY])) {
        fprintf(stderr, "asm kernels need aarch64\n");
        return 2;
    }
    if (cfg.ncpus && cfg.threads > cfg.ncpus)
        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);

    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);
    if (!th || pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {
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
    printf("kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,"
           "per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps\n");
    for (int k = 0; k < K_COUNT; k++) {
        if (!cfg.run[k])
            continue;
        double best = -1;
        for (int rep = 0; rep < cfg.reps; rep++) {
            pthread_barrier_wait(&bar); /* release the workers */
            pthread_barrier_wait(&bar); /* all workers finished this rep */
            uint64_t total = 0;
            double max_el = 0, mn = 1e30, mx = 0, sum = 0;
            for (int i = 0; i < cfg.threads; i++) {
                struct result *r = &th[i].res[k][rep];
                double g = (double)r->bytes / r->elapsed_s / 1e9;
                total += r->bytes;
                if (r->elapsed_s > max_el)
                    max_el = r->elapsed_s;
                if (g < mn)
                    mn = g;
                if (g > mx)
                    mx = g;
                sum += g;
            }
            double agg = (double)total / max_el / 1e9;
            if (agg > best)
                best = agg;
            printf("%s,%d,%lu,%d,%lu,%.4f,%.2f,%.2f,%.2f,%.2f\n", kernel_name[k], cfg.threads,
                   (unsigned long)cfg.bytes, rep, (unsigned long)total, max_el, agg, mn, mx,
                   sum / cfg.threads);
        }
        printf("%s,%d,%lu,best,,,%.2f,,,\n", kernel_name[k], cfg.threads, (unsigned long)cfg.bytes, best);
        if (cfg.per_thread) {
            /* thread,<index>,<cpu>,<kernel>,<rep>,<GB/s>: one line per thread and repetition, so that
             * concurrent per-group totals can be formed from one repetition (reviewer's request) */
            for (int i = 0; i < cfg.threads; i++)
                for (int rep = 0; rep < cfg.reps; rep++) {
                    struct result *r = &th[i].res[k][rep];
                    printf("thread,%d,%d,%s,%d,%.2f\n", i, th[i].cpu, kernel_name[k], rep, (double)r->bytes / r->elapsed_s / 1e9);
                }
        }
        fflush(stdout);
    }
    for (int i = 0; i < cfg.threads; i++)
        pthread_join(th[i].tid, NULL);
    return 0;
}
