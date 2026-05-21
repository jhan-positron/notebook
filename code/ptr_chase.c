/*
 * ptr_chase.c -- single-thread random pointer chase, NUMA-pinned,
 *                hugepage-backed. Measures load latency in ns.
 *
 * Method:
 *   - Allocate a buffer on requested NUMA node.
 *   - Treat it as an array of pointer-sized cells.
 *   - Build a single random Hamiltonian cycle through the cells.
 *     (Every cell is visited exactly once; chain returns to start.)
 *   - Use 64-byte stride between linked cells so each load misses
 *     the line of the previous one (no spatial prefetch hits).
 *   - Walk the chain N times, time the walk, divide by hops.
 *
 * Why a single random cycle:
 *   - Defeats stride and stream prefetchers
 *   - One outstanding load at a time (data dependency on the load result)
 *   - Reports true load-use latency, not bandwidth-amortized number
 *
 * Build:
 *   gcc -O2 -std=c11 -Wall -o ptr_chase ptr_chase.c -lnuma
 *
 * Run:
 *   ./ptr_chase --cpu 0 --mem-node 0 --size 256M --hugepage 1g --iters 5
 *
 * Output (one line per repetition, plus a summary):
 *   size=...  iter=N  ns/load=...
 *   SUMMARY: median=...  min=...  max=...  stddev=...
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/time.h>
#include <time.h>
#include <math.h>
#include <ctype.h>
#include <getopt.h>
#include <numa.h>
#include <numaif.h>

#ifndef MAP_HUGE_SHIFT
#define MAP_HUGE_SHIFT 26
#endif
#ifndef MAP_HUGE_2MB
#define MAP_HUGE_2MB (21 << MAP_HUGE_SHIFT)
#endif
#ifndef MAP_HUGE_1GB
#define MAP_HUGE_1GB (30 << MAP_HUGE_SHIFT)
#endif

#define STRIDE 64   /* one cache line */

static size_t parse_size(const char *s) {
    char *end;
    double v = strtod(s, &end);
    while (*end && isspace((unsigned char)*end)) end++;
    size_t mul = 1;
    if (*end == 'k' || *end == 'K') mul = 1024UL;
    else if (*end == 'm' || *end == 'M') mul = 1024UL * 1024;
    else if (*end == 'g' || *end == 'G') mul = 1024UL * 1024 * 1024;
    return (size_t)(v * mul);
}

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* xorshift64 PRNG, deterministic */
static uint64_t xs_state = 0x123456789abcdef0ULL;
static inline uint64_t xs_next(void) {
    uint64_t x = xs_state;
    x ^= x << 13; x ^= x >> 7; x ^= x << 17;
    xs_state = x;
    return x;
}

static void usage(const char *p) {
    fprintf(stderr,
        "usage: %s --cpu N --mem-node N [--size BYTES] "
        "[--hugepage 1g|2m|none] [--iters N] [--min-walk-secs SEC] [--csv]\n"
        "  size suffix: K/M/G   default 256M\n"
        "  hugepage  default 1g\n"
        "  iters     default 5  (repetitions for statistics)\n"
        "  min-walk-secs   each iter walks at least this many seconds\n"
        "                  default 0.5\n"
        "  --csv     emit one CSV summary line to stdout (in addition\n"
        "            to per-iter human-readable lines on stderr)\n",
        p);
    exit(2);
}

static int cmp_double(const void *a, const void *b) {
    double da = *(const double *)a, db = *(const double *)b;
    return (da > db) - (da < db);
}

int main(int argc, char **argv) {
    int cpu = -1, mem_node = -1;
    size_t size = 256UL * 1024 * 1024;
    const char *hp = "1g";
    int iters = 5;
    double min_walk_secs = 0.5;
    int csv = 0;

    static struct option opts[] = {
        {"cpu", required_argument, 0, 'c'},
        {"mem-node", required_argument, 0, 'm'},
        {"size", required_argument, 0, 's'},
        {"hugepage", required_argument, 0, 'h'},
        {"iters", required_argument, 0, 'i'},
        {"min-walk-secs", required_argument, 0, 'w'},
        {"csv", no_argument, 0, 'V'},
        {0, 0, 0, 0}
    };
    int oi;
    int c;
    while ((c = getopt_long(argc, argv, "c:m:s:h:i:w:V", opts, &oi)) != -1) {
        switch (c) {
            case 'c': cpu = atoi(optarg); break;
            case 'm': mem_node = atoi(optarg); break;
            case 's': size = parse_size(optarg); break;
            case 'h': hp = optarg; break;
            case 'i': iters = atoi(optarg); break;
            case 'w': min_walk_secs = atof(optarg); break;
            case 'V': csv = 1; break;
            default: usage(argv[0]);
        }
    }
    if (cpu < 0 || mem_node < 0) usage(argv[0]);

    if (numa_available() < 0) {
        fprintf(stderr, "ERROR: NUMA not available\n");
        return 1;
    }

    /* pin */
    cpu_set_t cs; CPU_ZERO(&cs); CPU_SET(cpu, &cs);
    if (sched_setaffinity(0, sizeof(cs), &cs) < 0) {
        perror("sched_setaffinity"); return 1;
    }
    sched_yield();
    if (sched_getcpu() != cpu) {
        fprintf(stderr, "WARN: requested cpu %d but on cpu %d\n",
                cpu, sched_getcpu());
    }

    /* allocate */
    int flags = MAP_PRIVATE | MAP_ANONYMOUS;
    size_t pagesize = 4096;
    if (strcmp(hp, "1g") == 0)      { flags |= MAP_HUGETLB | MAP_HUGE_1GB; pagesize = 1UL << 30; }
    else if (strcmp(hp, "2m") == 0) { flags |= MAP_HUGETLB | MAP_HUGE_2MB; pagesize = 2UL << 20; }
    else if (strcmp(hp, "none") != 0) { fprintf(stderr,"bad --hugepage\n"); return 2; }

    if (size < pagesize) {
        fprintf(stderr,
            "ERROR: --size (%zu bytes = %.1f MiB) is smaller than one "
            "%s page (%zu bytes = %.0f MiB).\n"
            "       Either pick a larger --size or use --hugepage 2m / none.\n",
            size, size / (1024.0 * 1024.0),
            hp, pagesize, pagesize / (1024.0 * 1024.0));
        return 2;
    }
    if (size % pagesize) size = ((size + pagesize - 1) / pagesize) * pagesize;

    void *buf = mmap(NULL, size, PROT_READ | PROT_WRITE, flags, -1, 0);
    if (buf == MAP_FAILED) {
        fprintf(stderr, "mmap failed (size=%zu hugepage=%s): %s\n",
                size, hp, strerror(errno));
        if (strcmp(hp, "1g") == 0)
            fprintf(stderr, "  1G hugepages required: %zu; check /proc/meminfo\n",
                    size / (1UL << 30));
        return 1;
    }

    /* bind to node */
    unsigned long nodemask = 1UL << mem_node;
    if (mbind(buf, size, MPOL_BIND, &nodemask, sizeof(nodemask)*8, 0) < 0) {
        perror("mbind"); return 1;
    }
    /* touch all pages to fault them in on the target node */
    {
        volatile char *p = (volatile char *)buf;
        for (size_t off = 0; off < size; off += pagesize) p[off] = (char)off;
    }
    /* try to lock so pages don't migrate during the test */
    if (mlock(buf, size) < 0) {
        /* not fatal -- print and continue */
        if (errno != EPERM)
            fprintf(stderr, "WARN: mlock failed: %s\n", strerror(errno));
    }

    /* build the chain.
     * Treat buffer as N cells of STRIDE bytes each.
     * Each cell stores a pointer to the next cell.
     * We want a single cycle visiting all N cells exactly once.
     * Method: indices 0..N-1; Fisher-Yates shuffle, then link
     *   shuffled[i] -> shuffled[i+1], wrap last -> first. */
    size_t ncells = size / STRIDE;
    if (ncells < 2) { fprintf(stderr, "buffer too small\n"); return 1; }

    /* index array */
    uint32_t *idx = malloc(ncells * sizeof(uint32_t));
    if (!idx) { perror("malloc"); return 1; }
    for (size_t i = 0; i < ncells; i++) idx[i] = (uint32_t)i;
    /* shuffle */
    for (size_t i = ncells - 1; i > 0; i--) {
        size_t j = xs_next() % (i + 1);
        uint32_t t = idx[i]; idx[i] = idx[j]; idx[j] = t;
    }
    /* link */
    char *base = (char *)buf;
    for (size_t i = 0; i < ncells; i++) {
        size_t from = idx[i];
        size_t to   = idx[(i + 1) % ncells];
        void **slot = (void **)(base + from * STRIDE);
        *slot = (void *)(base + to * STRIDE);
    }
    /* starting point */
    void **start = (void **)(base + idx[0] * STRIDE);
    free(idx);

    /* warm walk: one full pass to populate cache state predictably */
    {
        void **p = start;
        size_t steps = ncells;
        while (steps--) p = (void **)*p;
        /* prevent dead code elim */
        if (p == NULL) fprintf(stderr, "impossible\n");
    }

    /* timed walks */
    fprintf(stderr, "== ptr_chase cpu=%d mem-node=%d size=%zu cells=%zu "
            "hugepage=%s iters=%d ==\n",
            cpu, mem_node, size, ncells, hp, iters);

    double *results = malloc(iters * sizeof(double));
    if (!results) { perror("malloc"); return 1; }

    for (int it = 0; it < iters; it++) {
        /* compute how many hops we need to reach min-walk-secs */
        /* start with one pass; if too fast, double until enough */
        size_t hops = ncells;
        double elapsed;
        void **p;

        for (;;) {
            p = start;
            double t0 = now_sec();
            size_t k = hops;
            while (k--) {
                p = (void **)*p;
            }
            double t1 = now_sec();
            elapsed = t1 - t0;
            /* prevent DCE */
            if (p == (void *)0x1) fprintf(stderr, "impossible2\n");
            if (elapsed >= min_walk_secs) break;
            if (hops > (size_t)1e10) break;  /* hard cap */
            hops *= 2;
        }
        double ns_per_load = (elapsed * 1e9) / (double)hops;
        results[it] = ns_per_load;
        fprintf(stderr, "  iter=%d hops=%zu elapsed=%.3fs  ns/load=%.3f\n",
                it, hops, elapsed, ns_per_load);
    }

    /* stats */
    double *sorted = malloc(iters * sizeof(double));
    memcpy(sorted, results, iters * sizeof(double));
    qsort(sorted, iters, sizeof(double), cmp_double);
    double median = (iters % 2)
        ? sorted[iters / 2]
        : 0.5 * (sorted[iters/2 - 1] + sorted[iters/2]);
    double mn = sorted[0], mx = sorted[iters - 1];
    double sum = 0, sum2 = 0;
    for (int i = 0; i < iters; i++) { sum += results[i]; sum2 += results[i]*results[i]; }
    double mean = sum / iters;
    double var = (sum2 / iters) - mean*mean;
    double sd = var > 0 ? sqrt(var) : 0;

    fprintf(stderr, "SUMMARY: median=%.3f min=%.3f max=%.3f mean=%.3f stddev=%.3f ns/load\n",
            median, mn, mx, mean, sd);

    if (csv) {
        /* CSV columns:
           test,cpu,mem_node,size_bytes,hugepage,iters,median_ns,min_ns,max_ns,mean_ns,stddev_ns */
        printf("ptr_chase,%d,%d,%zu,%s,%d,%.3f,%.3f,%.3f,%.3f,%.3f\n",
               cpu, mem_node, size, hp, iters, median, mn, mx, mean, sd);
    }

    free(sorted); free(results);
    munmap(buf, size);
    return 0;
}
