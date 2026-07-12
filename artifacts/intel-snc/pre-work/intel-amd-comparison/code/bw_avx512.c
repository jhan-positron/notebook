/*
 * bw_avx512.c -- single-thread streaming bandwidth with AVX-512.
 *
 * Measures how fast a single thread can move data through the cache
 * hierarchy, as a function of buffer size and access pattern.
 *
 * Access patterns:
 *   read  -- pure load:           sum  += buf[i..i+63]    (8 AVX-512 loads)
 *   write -- non-temporal store:  buf[i..i+63] = vec       (bypasses cache)
 *   rmw   -- read-modify-write:   buf[i..i+63] += vec      (load + store)
 *
 * Notes on what the patterns mean:
 *   - "read" tests pure pull bandwidth from a cache level. With a small
 *     buffer (< L3) we get cache-level BW. With a large buffer (> L3)
 *     we get DRAM read BW.
 *   - "rmw" hits both the read AND write port of the cache port budget
 *     on most architectures. The Chips and Cheese article notes that
 *     L3 bandwidth ROUGHLY DOUBLES under RMW vs read-only on Xeon 6
 *     because Intel's L3 has separate read and write paths that can
 *     run concurrently. We expect to see the same effect.
 *   - "write" uses non-temporal stores (MOVNTPS) so it bypasses cache.
 *     Useful only for pure DRAM write bandwidth.
 *
 * Method:
 *   - Allocate buffer (NUMA-pinned, hugepage-backed).
 *   - Touch every page so all faults complete before timing.
 *   - Inner loop runs in 256-byte chunks (4 AVX-512 vectors = 1 KiB
 *     unrolled to ~16 vectors actually loaded). Each chunk is fully
 *     independent so the load/store pipelines can saturate.
 *   - Time at least --min-walk-secs of work to amortize timer noise.
 *   - Report GB/s.
 *
 * Build (requires AVX-512 support; both Xeon 6 and Genoa have it):
 *   gcc -O3 -mavx512f -std=c11 -Wall -o bw_avx512 bw_avx512.c -lnuma
 *
 * Examples:
 *   ./bw_avx512 --cpu 0 --mem-node 0 --size 32M --pattern read --hugepage 2m
 *   ./bw_avx512 --cpu 0 --mem-node 0 --size 4G  --pattern read --hugepage 1g
 *   ./bw_avx512 --cpu 0 --mem-node 0 --size 32M --pattern rmw  --hugepage 2m
 *
 * Output: ns/iter, GB/s, plus median/min/max/stddev across --iters runs.
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

#define CHUNK 256   /* bytes processed per inner iteration */

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

static int cmp_double(const void *a, const void *b) {
    double da = *(const double *)a, db = *(const double *)b;
    return (da > db) - (da < db);
}

/* ============================================================
 * KERNELS
 *
 * Each kernel processes the buffer once, in CHUNK-byte strides.
 * Buffer size MUST be a multiple of CHUNK.
 *
 * Return: an "accumulator" value to prevent the compiler from
 * eliminating the entire loop as dead code. Caller stores it
 * into a volatile sink.
 *
 * Vector ABI: __m512 = 16 single-precision floats = 64 bytes.
 * One CHUNK (256 B) = 4 vectors.
 * ============================================================
 */

static inline uint64_t kernel_read(const char *buf, size_t bytes) {
    /* Pure load. We use integer XOR to accumulate so the compiler
       cannot pretend the loads are unused. */
    const __m512i *p = (const __m512i *)buf;
    const __m512i *end = (const __m512i *)(buf + bytes);
    __m512i acc0 = _mm512_setzero_si512();
    __m512i acc1 = _mm512_setzero_si512();
    __m512i acc2 = _mm512_setzero_si512();
    __m512i acc3 = _mm512_setzero_si512();
    while (p < end) {
        __m512i v0 = _mm512_load_si512(p + 0);
        __m512i v1 = _mm512_load_si512(p + 1);
        __m512i v2 = _mm512_load_si512(p + 2);
        __m512i v3 = _mm512_load_si512(p + 3);
        acc0 = _mm512_xor_si512(acc0, v0);
        acc1 = _mm512_xor_si512(acc1, v1);
        acc2 = _mm512_xor_si512(acc2, v2);
        acc3 = _mm512_xor_si512(acc3, v3);
        p += 4;  /* CHUNK / 64 = 4 vectors */
    }
    __m512i tot = _mm512_xor_si512(_mm512_xor_si512(acc0, acc1),
                                   _mm512_xor_si512(acc2, acc3));
    /* reduce to scalar so we can return */
    uint64_t out[8];
    _mm512_storeu_si512((__m512i *)out, tot);
    uint64_t r = 0;
    for (int i = 0; i < 8; i++) r ^= out[i];
    return r;
}

static inline void kernel_write_nt(char *buf, size_t bytes, uint64_t seed) {
    /* Non-temporal stores: data goes straight to memory, bypasses
       cache pollution. */
    __m512i v0 = _mm512_set1_epi64((long long)(seed +  0));
    __m512i v1 = _mm512_set1_epi64((long long)(seed +  1));
    __m512i v2 = _mm512_set1_epi64((long long)(seed +  2));
    __m512i v3 = _mm512_set1_epi64((long long)(seed +  3));
    __m512i *p = (__m512i *)buf;
    __m512i *end = (__m512i *)(buf + bytes);
    while (p < end) {
        _mm512_stream_si512(p + 0, v0);
        _mm512_stream_si512(p + 1, v1);
        _mm512_stream_si512(p + 2, v2);
        _mm512_stream_si512(p + 3, v3);
        p += 4;
    }
    _mm_sfence();  /* drain WC buffers */
}

static inline uint64_t kernel_rmw(char *buf, size_t bytes) {
    /* Load, modify, store back. Hits read AND write paths of cache.
       Use regular stores (not NT) so values stay in cache. */
    __m512i *p = (__m512i *)buf;
    __m512i *end = (__m512i *)(buf + bytes);
    __m512i one = _mm512_set1_epi64(1);
    uint64_t acc = 0;
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
    /* sink */
    acc ^= _mm_cvtsi128_si64(_mm512_castsi512_si128(one));
    return acc;
}

static volatile uint64_t SINK;

static void usage(const char *p) {
    fprintf(stderr,
        "usage: %s --cpu N --mem-node N --pattern read|write|rmw\n"
        "          [--size BYTES] [--hugepage 1g|2m|none] [--iters N]\n"
        "          [--min-walk-secs SEC] [--csv]\n"
        "  size suffix: K/M/G   default 32M\n"
        "  hugepage  default 2m\n"
        "  iters     default 5\n"
        "  min-walk-secs   each iter does enough passes to take this long\n"
        "                  default 0.5\n",
        p);
    exit(2);
}

int main(int argc, char **argv) {
    int cpu = -1, mem_node = -1;
    size_t size = 32UL * 1024 * 1024;
    const char *hp = "2m";
    const char *pattern = NULL;
    int iters = 5;
    double min_walk_secs = 0.5;
    int csv = 0;

    static struct option opts[] = {
        {"cpu", required_argument, 0, 'c'},
        {"mem-node", required_argument, 0, 'm'},
        {"size", required_argument, 0, 's'},
        {"hugepage", required_argument, 0, 'h'},
        {"pattern", required_argument, 0, 'p'},
        {"iters", required_argument, 0, 'i'},
        {"min-walk-secs", required_argument, 0, 'w'},
        {"csv", no_argument, 0, 'V'},
        {0, 0, 0, 0}
    };
    int oi, c;
    while ((c = getopt_long(argc, argv, "c:m:s:h:p:i:w:V", opts, &oi)) != -1) {
        switch (c) {
            case 'c': cpu = atoi(optarg); break;
            case 'm': mem_node = atoi(optarg); break;
            case 's': size = parse_size(optarg); break;
            case 'h': hp = optarg; break;
            case 'p': pattern = optarg; break;
            case 'i': iters = atoi(optarg); break;
            case 'w': min_walk_secs = atof(optarg); break;
            case 'V': csv = 1; break;
            default: usage(argv[0]);
        }
    }
    if (cpu < 0 || mem_node < 0 || !pattern) usage(argv[0]);
    if (strcmp(pattern,"read")!=0 && strcmp(pattern,"write")!=0 && strcmp(pattern,"rmw")!=0) {
        fprintf(stderr, "bad --pattern: %s (use read|write|rmw)\n", pattern);
        return 2;
    }

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

    /* size must be both >= pagesize and a multiple of CHUNK */
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
    if (size % CHUNK) size -= size % CHUNK;

    void *buf = mmap(NULL, size, PROT_READ | PROT_WRITE, flags, -1, 0);
    if (buf == MAP_FAILED) {
        fprintf(stderr, "mmap failed (size=%zu hugepage=%s): %s\n",
                size, hp, strerror(errno));
        return 1;
    }

    /* alignment guarantee: mmap returns page-aligned; AVX-512 needs 64 */
    if ((uintptr_t)buf % 64 != 0) {
        fprintf(stderr, "ERROR: buffer not 64-byte aligned (%p)\n", buf);
        return 1;
    }

    /* bind */
    unsigned long nodemask = 1UL << mem_node;
    if (mbind(buf, size, MPOL_BIND, &nodemask, sizeof(nodemask)*8, 0) < 0) {
        perror("mbind"); return 1;
    }
    /* fault in all pages */
    {
        volatile char *p = (volatile char *)buf;
        for (size_t off = 0; off < size; off += pagesize) p[off] = (char)off;
    }
    if (mlock(buf, size) < 0 && errno != EPERM) {
        fprintf(stderr, "WARN: mlock failed: %s\n", strerror(errno));
    }

    /* warm: one full pass with the chosen kernel */
    if (strcmp(pattern, "read") == 0) {
        SINK ^= kernel_read((const char *)buf, size);
    } else if (strcmp(pattern, "rmw") == 0) {
        SINK ^= kernel_rmw((char *)buf, size);
    } else {
        kernel_write_nt((char *)buf, size, 0xdeadbeef);
    }

    fprintf(stderr, "== bw_avx512 cpu=%d mem-node=%d size=%zu pattern=%s "
            "hugepage=%s iters=%d ==\n",
            cpu, mem_node, size, pattern, hp, iters);

    double *results = malloc(iters * sizeof(double));
    if (!results) { perror("malloc"); return 1; }

    for (int it = 0; it < iters; it++) {
        /* find passes count s.t. total time >= min_walk_secs */
        size_t passes = 1;
        double elapsed = 0;
        for (;;) {
            double t0 = now_sec();
            for (size_t k = 0; k < passes; k++) {
                if (strcmp(pattern, "read") == 0) {
                    SINK ^= kernel_read((const char *)buf, size);
                } else if (strcmp(pattern, "rmw") == 0) {
                    SINK ^= kernel_rmw((char *)buf, size);
                } else {
                    kernel_write_nt((char *)buf, size, 0xdeadbeef + k);
                }
            }
            double t1 = now_sec();
            elapsed = t1 - t0;
            if (elapsed >= min_walk_secs) break;
            if (passes > (size_t)1e9) break;
            /* extrapolate: target = current * factor */
            double factor = (min_walk_secs / elapsed) * 1.1;
            if (factor < 2) factor = 2;
            passes = (size_t)(passes * factor) + 1;
        }
        double total_bytes = (double)size * (double)passes;
        /* For RMW, both read AND write traffic count toward the
           bus bandwidth. We report two numbers:
             - bytes_traffic     = data moved on the cache/memory bus
             - bytes_workload    = useful data of pattern */
        double bytes_traffic = total_bytes;
        if (strcmp(pattern, "rmw") == 0) bytes_traffic *= 2.0;

        double gbps_workload = total_bytes / elapsed / 1e9;
        double gbps_traffic  = bytes_traffic / elapsed / 1e9;
        results[it] = gbps_traffic;   /* primary metric */
        fprintf(stderr, "  iter=%d passes=%zu elapsed=%.3fs  "
                "workload=%.2f GB/s  bus=%.2f GB/s\n",
                it, passes, elapsed, gbps_workload, gbps_traffic);
    }

    /* stats on the primary metric (bus bandwidth) */
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

    fprintf(stderr, "SUMMARY: median=%.2f min=%.2f max=%.2f mean=%.2f stddev=%.2f GB/s "
            "(bus traffic; for RMW this counts both load+store)\n",
            median, mn, mx, mean, sd);

    if (csv) {
        /* CSV columns:
           test,cpu,mem_node,size_bytes,hugepage,pattern,iters,
           median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps */
        printf("bw_avx512,%d,%d,%zu,%s,%s,%d,%.3f,%.3f,%.3f,%.3f,%.3f\n",
               cpu, mem_node, size, hp, pattern, iters,
               median, mn, mx, mean, sd);
    }

    free(sorted); free(results);
    munmap(buf, size);
    return 0;
}
