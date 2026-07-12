/*
 * bw_multi.c -- multi-thread AVX-512 bandwidth aggregator.
 *
 * Purpose:
 *   Measure how aggregate bandwidth scales as we add threads.
 *   Each thread runs the same kernel on its OWN private buffer,
 *   so threads don't share cache lines or compete for the same
 *   bytes.
 *
 * Why this is informative:
 *   - 1 thread:  per-core memory subsystem limit (already known
 *     from bw_avx512.c)
 *   - few threads:  scaling factor — does the next core add the
 *     same BW, or does shared structure (L3 ring/mesh, IOD) start
 *     to throttle?
 *   - many threads:  aggregate saturation — the system-wide
 *     bandwidth ceiling for the chosen access pattern.
 *
 * Example questions answered:
 *   - Where does Intel's monolithic L3 saturate (mesh BW ceiling)?
 *   - At how many threads does AMD's IOD become the bottleneck?
 *   - Does aggregate DRAM BW approach the channel-theoretical limit?
 *     (Intel: 12ch × DDR5-6400 ≈ 614 GB/s per socket)
 *     (AMD:   12ch × DDR5-4800 ≈ 461 GB/s per socket)
 *
 * Method:
 *   - Spawn --threads N worker threads.
 *   - Each thread is pinned (sched_setaffinity) to its own logical
 *     CPU, taken from --cpus LIST.
 *   - Each thread mmaps and binds its own buffer on --mem-node.
 *   - Threads synchronize on a start barrier, then each runs the
 *     kernel for --min-walk-secs. Per-thread bytes/elapsed is the
 *     per-thread BW; sum is the aggregate.
 *
 * Build:
 *   gcc -O3 -mavx512f -std=c11 -Wall -Wextra -pthread \
 *       -o bw_multi bw_multi.c -lnuma -lm
 *
 * Examples:
 *   # 8 threads on cores 0-7, each with a 4 MB buffer, read from L3
 *   ./bw_multi --cpus 0-7 --mem-node 0 --size-per-thread 4M \
 *              --pattern read --hugepage 2m --iters 5
 *
 *   # 32 threads, 256 MB each, DRAM read
 *   ./bw_multi --cpus 0-31 --mem-node 0 --size-per-thread 256M \
 *              --pattern read --hugepage 2m --iters 5
 *
 *   # 64 threads, 64 MB each → 4 GB total → forces DRAM
 *   ./bw_multi --cpus 0-63 --mem-node 0 --size-per-thread 64M \
 *              --pattern read --hugepage 2m --iters 5
 *
 * Output: per-thread GB/s + aggregate (median over iters), plus
 *         optional CSV row.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <sched.h>
#include <pthread.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <math.h>
#include <ctype.h>
#include <getopt.h>
#include <numa.h>
#include <numaif.h>
#include <immintrin.h>

#ifndef MAP_HUGE_SHIFT
#define MAP_HUGE_SHIFT 26
#endif
#ifndef MAP_HUGE_2MB
#define MAP_HUGE_2MB (21 << MAP_HUGE_SHIFT)
#endif
#ifndef MAP_HUGE_1GB
#define MAP_HUGE_1GB (30 << MAP_HUGE_SHIFT)
#endif

#define CHUNK 256

/* ---------- helpers ---------- */

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

/* parse "0-7,16-23,40" into a sorted array of ints, return count.
 * caller must free the returned array. */
static int *parse_cpulist(const char *s, int *out_n) {
    int cap = 16, n = 0;
    int *arr = malloc(cap * sizeof(int));
    if (!arr) return NULL;
    const char *p = s;
    while (*p) {
        while (*p == ',' || isspace((unsigned char)*p)) p++;
        if (!*p) break;
        char *end;
        long a = strtol(p, &end, 10);
        long b = a;
        p = end;
        if (*p == '-') { p++; b = strtol(p, &end, 10); p = end; }
        for (long v = a; v <= b; v++) {
            if (n == cap) { cap *= 2; arr = realloc(arr, cap * sizeof(int)); }
            arr[n++] = (int)v;
        }
    }
    *out_n = n;
    return arr;
}

static int cmp_double(const void *a, const void *b) {
    double da = *(const double *)a, db = *(const double *)b;
    return (da > db) - (da < db);
}

/* ---------- kernels (identical to bw_avx512.c) ---------- */

static volatile uint64_t SINK;

static inline uint64_t kernel_read(const char *buf, size_t bytes) {
    const __m512i *p = (const __m512i *)buf;
    const __m512i *end = (const __m512i *)(buf + bytes);
    __m512i a0 = _mm512_setzero_si512();
    __m512i a1 = _mm512_setzero_si512();
    __m512i a2 = _mm512_setzero_si512();
    __m512i a3 = _mm512_setzero_si512();
    while (p < end) {
        a0 = _mm512_xor_si512(a0, _mm512_load_si512(p + 0));
        a1 = _mm512_xor_si512(a1, _mm512_load_si512(p + 1));
        a2 = _mm512_xor_si512(a2, _mm512_load_si512(p + 2));
        a3 = _mm512_xor_si512(a3, _mm512_load_si512(p + 3));
        p += 4;
    }
    __m512i tot = _mm512_xor_si512(_mm512_xor_si512(a0, a1),
                                   _mm512_xor_si512(a2, a3));
    uint64_t out[8];
    _mm512_storeu_si512((__m512i *)out, tot);
    uint64_t r = 0;
    for (int i = 0; i < 8; i++) r ^= out[i];
    return r;
}

static inline uint64_t kernel_rmw(char *buf, size_t bytes) {
    __m512i *p = (__m512i *)buf;
    __m512i *end = (__m512i *)(buf + bytes);
    __m512i one = _mm512_set1_epi64(1);
    while (p < end) {
        __m512i v0 = _mm512_load_si512(p + 0);
        __m512i v1 = _mm512_load_si512(p + 1);
        __m512i v2 = _mm512_load_si512(p + 2);
        __m512i v3 = _mm512_load_si512(p + 3);
        v0 = _mm512_add_epi64(v0, one);
        v1 = _mm512_add_epi64(v1, one);
        v2 = _mm512_add_epi64(v2, one);
        v3 = _mm512_add_epi64(v3, one);
        _mm512_store_si512(p + 0, v0);
        _mm512_store_si512(p + 1, v1);
        _mm512_store_si512(p + 2, v2);
        _mm512_store_si512(p + 3, v3);
        p += 4;
    }
    return (uint64_t)_mm_cvtsi128_si64(_mm512_castsi512_si128(one));
}

/* ---------- thread plumbing ---------- */

typedef struct {
    int tid;
    int cpu;
    int mem_node;
    int local;        /* --local: first-touch on the pinned thread's local node (no mbind) */
    size_t size;
    const char *hp;
    const char *pattern;
    double min_walk_secs;

    /* barriers (start, stop) */
    pthread_barrier_t *start;
    pthread_barrier_t *stop;

    /* outputs */
    double elapsed;
    double bytes_workload;   /* bytes the kernel really moved */
    double bytes_traffic;    /* bus traffic (rmw counts ×2) */
    int err;
} worker_t;

static void *worker_fn(void *arg) {
    worker_t *w = (worker_t *)arg;
    w->err = 0;

    /* pin */
    cpu_set_t cs; CPU_ZERO(&cs); CPU_SET(w->cpu, &cs);
    if (sched_setaffinity(0, sizeof(cs), &cs) < 0) {
        fprintf(stderr, "tid=%d sched_setaffinity(cpu=%d): %s\n",
                w->tid, w->cpu, strerror(errno));
        w->err = 1;
        pthread_barrier_wait(w->start); pthread_barrier_wait(w->stop);
        return NULL;
    }

    /* alloc */
    int flags = MAP_PRIVATE | MAP_ANONYMOUS;
    size_t pagesize = 4096;
    if (strcmp(w->hp, "1g") == 0)      { flags |= MAP_HUGETLB | MAP_HUGE_1GB; pagesize = 1UL << 30; }
    else if (strcmp(w->hp, "2m") == 0) { flags |= MAP_HUGETLB | MAP_HUGE_2MB; pagesize = 2UL << 20; }

    size_t sz = w->size;
    if (sz < pagesize) {
        fprintf(stderr, "tid=%d size %zu < pagesize %zu\n",
                w->tid, sz, pagesize);
        w->err = 1;
        pthread_barrier_wait(w->start); pthread_barrier_wait(w->stop);
        return NULL;
    }
    if (sz % pagesize) sz = ((sz + pagesize - 1) / pagesize) * pagesize;
    if (sz % CHUNK) sz -= sz % CHUNK;

    void *buf = mmap(NULL, sz, PROT_READ | PROT_WRITE, flags, -1, 0);
    if (buf == MAP_FAILED) {
        fprintf(stderr, "tid=%d mmap(sz=%zu hp=%s): %s\n",
                w->tid, sz, w->hp, strerror(errno));
        w->err = 1;
        pthread_barrier_wait(w->start); pthread_barrier_wait(w->stop);
        return NULL;
    }

    if (!w->local) {
        unsigned long nodemask = 1UL << w->mem_node;
        if (mbind(buf, sz, MPOL_BIND, &nodemask, sizeof(nodemask) * 8, 0) < 0) {
            fprintf(stderr, "tid=%d mbind: %s\n", w->tid, strerror(errno));
        }
    }
    /* --local: no mbind. The fault loop below first-touches each page while the
       thread is pinned (MPOL_DEFAULT), so pages land on the thread's LOCAL NUMA
       node -> each thread streams local memory and all dies' channels engage. */
    /* fault */
    volatile char *vb = (volatile char *)buf;
    for (size_t off = 0; off < sz; off += pagesize) vb[off] = (char)off;

    /* warm */
    if (strcmp(w->pattern, "read") == 0) {
        SINK ^= kernel_read((const char *)buf, sz);
    } else {
        SINK ^= kernel_rmw((char *)buf, sz);
    }

    /* wait for everyone */
    pthread_barrier_wait(w->start);

    /* run */
    size_t passes = 1;
    double elapsed = 0;
    for (;;) {
        double t0 = now_sec();
        for (size_t k = 0; k < passes; k++) {
            if (strcmp(w->pattern, "read") == 0) {
                SINK ^= kernel_read((const char *)buf, sz);
            } else {
                SINK ^= kernel_rmw((char *)buf, sz);
            }
        }
        double t1 = now_sec();
        elapsed = t1 - t0;
        if (elapsed >= w->min_walk_secs) break;
        if (passes > (size_t)1e9) break;
        double factor = (w->min_walk_secs / elapsed) * 1.1;
        if (factor < 2) factor = 2;
        passes = (size_t)(passes * factor) + 1;
    }

    w->elapsed = elapsed;
    w->bytes_workload = (double)sz * (double)passes;
    w->bytes_traffic = w->bytes_workload;
    if (strcmp(w->pattern, "rmw") == 0) w->bytes_traffic *= 2.0;

    pthread_barrier_wait(w->stop);
    munmap(buf, sz);
    return NULL;
}

/* ---------- driver ---------- */

static void usage(const char *p) {
    fprintf(stderr,
        "usage: %s --cpus LIST (--mem-node N | --local) --pattern read|rmw\n"
        "          [--size-per-thread BYTES] [--hugepage 1g|2m|none]\n"
        "          [--iters N] [--min-walk-secs SEC] [--csv]\n"
        "  --cpus LIST     comma-separated list with ranges, e.g. 0-7,16-23\n"
        "  --local         each thread first-touches its buffer on its OWN local\n"
        "                  NUMA node (no mbind); use for whole-socket BW. Mutually\n"
        "                  exclusive with --mem-node.\n"
        "  size suffix K/M/G   default 4M\n"
        "  hugepage default 2m\n"
        "  iters default 5\n"
        "  min-walk-secs default 0.5\n", p);
    exit(2);
}

int main(int argc, char **argv) {
    const char *cpus_str = NULL;
    int mem_node = -1;
    size_t size_per = 4UL * 1024 * 1024;
    const char *hp = "2m";
    const char *pattern = NULL;
    int iters = 5;
    double min_walk_secs = 0.5;
    int csv = 0;
    int local = 0;

    static struct option opts[] = {
        {"cpus", required_argument, 0, 'C'},
        {"mem-node", required_argument, 0, 'm'},
        {"size-per-thread", required_argument, 0, 's'},
        {"hugepage", required_argument, 0, 'h'},
        {"pattern", required_argument, 0, 'p'},
        {"iters", required_argument, 0, 'i'},
        {"min-walk-secs", required_argument, 0, 'w'},
        {"csv", no_argument, 0, 'V'},
        {"local", no_argument, 0, 'L'},
        {0,0,0,0}
    };
    int oi, c;
    while ((c = getopt_long(argc, argv, "C:m:s:h:p:i:w:VL", opts, &oi)) != -1) {
        switch (c) {
            case 'C': cpus_str = optarg; break;
            case 'm': mem_node = atoi(optarg); break;
            case 's': size_per = parse_size(optarg); break;
            case 'h': hp = optarg; break;
            case 'p': pattern = optarg; break;
            case 'i': iters = atoi(optarg); break;
            case 'w': min_walk_secs = atof(optarg); break;
            case 'V': csv = 1; break;
            case 'L': local = 1; break;
            default: usage(argv[0]);
        }
    }
    if (!cpus_str || !pattern || (!local && mem_node < 0)) usage(argv[0]);
    if (strcmp(pattern,"read")!=0 && strcmp(pattern,"rmw")!=0) {
        fprintf(stderr, "bad --pattern (use read|rmw)\n"); return 2;
    }

    int nthreads = 0;
    int *cpus = parse_cpulist(cpus_str, &nthreads);
    if (!cpus || nthreads <= 0) {
        fprintf(stderr, "bad --cpus: %s\n", cpus_str); return 2;
    }

    fprintf(stderr, "== bw_multi threads=%d mem-node=%d size/thread=%zu "
            "pattern=%s hugepage=%s iters=%d ==\n",
            nthreads, mem_node, size_per, pattern, hp, iters);

    double *agg_results = malloc(iters * sizeof(double));

    for (int it = 0; it < iters; it++) {
        pthread_barrier_t b_start, b_stop;
        pthread_barrier_init(&b_start, NULL, nthreads + 1);
        pthread_barrier_init(&b_stop,  NULL, nthreads + 1);

        worker_t *W = calloc(nthreads, sizeof(worker_t));
        pthread_t *T = calloc(nthreads, sizeof(pthread_t));
        if (!W || !T) { perror("calloc"); return 1; }

        for (int t = 0; t < nthreads; t++) {
            W[t].tid = t;
            W[t].cpu = cpus[t];
            W[t].mem_node = mem_node;
            W[t].local = local;
            W[t].size = size_per;
            W[t].hp = hp;
            W[t].pattern = pattern;
            W[t].min_walk_secs = min_walk_secs;
            W[t].start = &b_start;
            W[t].stop = &b_stop;
            if (pthread_create(&T[t], NULL, worker_fn, &W[t]) != 0) {
                fprintf(stderr, "pthread_create %d\n", t); return 1;
            }
        }

        /* release all at once */
        pthread_barrier_wait(&b_start);
        /* wait for all to finish */
        pthread_barrier_wait(&b_stop);

        for (int t = 0; t < nthreads; t++) pthread_join(T[t], NULL);

        double agg = 0;
        double sum_workload = 0;
        double max_elapsed = 0;
        int errs = 0;
        for (int t = 0; t < nthreads; t++) {
            if (W[t].err) errs++;
            else {
                agg += W[t].bytes_traffic / W[t].elapsed / 1e9;
                sum_workload += W[t].bytes_workload;
                if (W[t].elapsed > max_elapsed) max_elapsed = W[t].elapsed;
            }
        }
        agg_results[it] = agg;
        fprintf(stderr, "  iter=%d errs=%d agg=%.2f GB/s "
                "(workload sum=%.2f GB over %.3fs)\n",
                it, errs, agg, sum_workload / 1e9, max_elapsed);

        pthread_barrier_destroy(&b_start);
        pthread_barrier_destroy(&b_stop);
        free(W); free(T);
        if (errs) return 1;
    }

    /* stats */
    double *sorted = malloc(iters * sizeof(double));
    memcpy(sorted, agg_results, iters * sizeof(double));
    qsort(sorted, iters, sizeof(double), cmp_double);
    double median = (iters % 2) ? sorted[iters/2]
                                 : 0.5 * (sorted[iters/2 - 1] + sorted[iters/2]);
    double mn = sorted[0], mx = sorted[iters - 1];
    double sum = 0, sum2 = 0;
    for (int i = 0; i < iters; i++) { sum += agg_results[i]; sum2 += agg_results[i]*agg_results[i]; }
    double mean = sum / iters;
    double var = (sum2 / iters) - mean*mean;
    double sd = var > 0 ? sqrt(var) : 0;

    fprintf(stderr, "SUMMARY: aggregate median=%.2f min=%.2f max=%.2f mean=%.2f stddev=%.2f GB/s\n",
            median, mn, mx, mean, sd);

    if (csv) {
        /* CSV: test,nthreads,mem_node,size_per_thread,hugepage,pattern,iters,
                median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps */
        printf("bw_multi,%d,%d,%zu,%s,%s,%d,%.3f,%.3f,%.3f,%.3f,%.3f\n",
               nthreads, mem_node, size_per, hp, pattern, iters,
               median, mn, mx, mean, sd);
    }

    free(sorted); free(agg_results); free(cpus);
    return 0;
}
