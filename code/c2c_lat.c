/*
 * c2c_lat.c -- core-to-core latency via CAS ping-pong.
 *
 * Purpose:
 *   Measure how long it takes for a cache line to bounce between two
 *   specific cores. This exposes the coherency / interconnect topology:
 *     - same-CCD / same-mesh-cluster pairs: fast
 *     - cross-CCD / cross-mesh-region pairs: slower
 *     - cross-socket pairs: slowest
 *
 * Method (the classic CAS ping-pong):
 *   Two threads, each pinned to a specific CPU.
 *   They share a single 64-byte cache line containing one atomic counter.
 *   Thread A waits until counter is EVEN, then atomically increments it.
 *   Thread B waits until counter is ODD, then atomically increments it.
 *   Each increment is a full coherency round trip: the line must be
 *   evicted from one core's L1 (in Modified state) and re-fetched into
 *   the other core's L1 (transitioning Modified -> Modified again
 *   via the cache coherency protocol).
 *
 * Measured number = ns per ROUND TRIP (one A increment + one B increment).
 * Reported also = ns one-way = round trip / 2.
 *
 * Important: the memory holding the shared counter is allocated on a
 * specific NUMA node. For symmetric tests we use the node home of the
 * caller (cpu A). The home node DOES affect c2c latency because the
 * line's coherency directory may live there.
 *
 * Build:
 *   gcc -O2 -std=c11 -Wall -Wextra -pthread \
 *       -o c2c_lat c2c_lat.c -lnuma -lm
 *
 * Examples:
 *   # cores 0 and 1 (likely same CCD/cluster)
 *   ./c2c_lat --cpu-a 0 --cpu-b 1 --mem-node 0 --iters 5
 *
 *   # cores 0 and 8 (likely cross-CCD on AMD)
 *   ./c2c_lat --cpu-a 0 --cpu-b 8 --mem-node 0 --iters 5
 *
 *   # cross-socket
 *   ./c2c_lat --cpu-a 0 --cpu-b 72 --mem-node 0 --iters 5
 *
 * Output: ns/round-trip + ns/one-way, median over iters.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdatomic.h>
#include <unistd.h>
#include <errno.h>
#include <sched.h>
#include <pthread.h>
#include <sys/mman.h>
#include <time.h>
#include <math.h>
#include <getopt.h>
#include <numa.h>
#include <numaif.h>

#define LINE_BYTES 64

/* Shared state, aligned to a cache line and padded so neighbors
 * don't end up in adjacent lines. */
typedef struct __attribute__((aligned(LINE_BYTES))) {
    _Atomic uint64_t counter;
    char pad[LINE_BYTES - sizeof(_Atomic uint64_t)];
} shared_t;

typedef struct {
    int tid;            /* 0 or 1 */
    int cpu;
    int parity;         /* 0 expects even, 1 expects odd */
    shared_t *shared;
    _Atomic int *go;    /* start barrier flag */
    _Atomic int *done;  /* stop flag */
    uint64_t target;    /* stop when counter >= target */
    int err;
} worker_t;

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static int cmp_double(const void *a, const void *b) {
    double da = *(const double *)a, db = *(const double *)b;
    return (da > db) - (da < db);
}

static void *worker_fn(void *arg) {
    worker_t *w = (worker_t *)arg;
    w->err = 0;

    cpu_set_t cs; CPU_ZERO(&cs); CPU_SET(w->cpu, &cs);
    if (sched_setaffinity(0, sizeof(cs), &cs) < 0) {
        fprintf(stderr, "tid=%d sched_setaffinity(cpu=%d): %s\n",
                w->tid, w->cpu, strerror(errno));
        w->err = 1;
        /* signal peer so it doesn't spin forever */
        atomic_store_explicit(w->done, 1, memory_order_release);
        return NULL;
    }

    /* spin until start or abort */
    while (!atomic_load_explicit(w->go, memory_order_acquire)) {
        if (atomic_load_explicit(w->done, memory_order_acquire)) return NULL;
        __builtin_ia32_pause();
    }

    _Atomic uint64_t *c = &w->shared->counter;
    uint64_t target = w->target;
    int parity = w->parity;

    /* hot loop */
    for (;;) {
        if (atomic_load_explicit(w->done, memory_order_acquire)) break;
        uint64_t v = atomic_load_explicit(c, memory_order_acquire);
        if (v >= target) break;
        if ((v & 1) == (uint64_t)parity) {
            uint64_t want = v + 1;
            if (atomic_compare_exchange_strong_explicit(
                    c, &v, want,
                    memory_order_acq_rel, memory_order_acquire)) {
            }
        } else {
            __builtin_ia32_pause();
        }
    }
    return NULL;
}

static void usage(const char *p) {
    fprintf(stderr,
        "usage: %s --cpu-a A --cpu-b B --mem-node N [--iters N] "
        "[--rounds N] [--csv]\n"
        "  --rounds  number of round trips per iter (default 1000000)\n"
        "  --iters   number of repetitions (default 5)\n", p);
    exit(2);
}

int main(int argc, char **argv) {
    int cpu_a = -1, cpu_b = -1, mem_node = -1;
    int iters = 5;
    uint64_t rounds = 1000000;
    int csv = 0;

    static struct option opts[] = {
        {"cpu-a", required_argument, 0, 'a'},
        {"cpu-b", required_argument, 0, 'b'},
        {"mem-node", required_argument, 0, 'm'},
        {"iters", required_argument, 0, 'i'},
        {"rounds", required_argument, 0, 'r'},
        {"csv", no_argument, 0, 'V'},
        {0,0,0,0}
    };
    int oi, c;
    while ((c = getopt_long(argc, argv, "a:b:m:i:r:V", opts, &oi)) != -1) {
        switch (c) {
            case 'a': cpu_a = atoi(optarg); break;
            case 'b': cpu_b = atoi(optarg); break;
            case 'm': mem_node = atoi(optarg); break;
            case 'i': iters = atoi(optarg); break;
            case 'r': rounds = (uint64_t)atoll(optarg); break;
            case 'V': csv = 1; break;
            default: usage(argv[0]);
        }
    }
    if (cpu_a < 0 || cpu_b < 0 || mem_node < 0) usage(argv[0]);
    if (cpu_a == cpu_b) {
        fprintf(stderr, "ERROR: cpu-a and cpu-b must differ\n");
        return 2;
    }

    if (numa_available() < 0) {
        fprintf(stderr, "NUMA not available\n"); return 1;
    }

    /* allocate one cache line, bound to mem_node, 2M page for clean
     * TLB but 64B is all we need.
     * Simpler: anonymous, then mbind. */
    size_t pagesize = 4096;
    void *raw = mmap(NULL, pagesize, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED) { perror("mmap"); return 1; }
    unsigned long nodemask = 1UL << mem_node;
    if (mbind(raw, pagesize, MPOL_BIND, &nodemask, sizeof(nodemask)*8, 0) < 0) {
        perror("mbind"); return 1;
    }
    memset(raw, 0, pagesize);  /* fault */

    shared_t *sh = (shared_t *)raw;
    if ((uintptr_t)sh % LINE_BYTES != 0) {
        fprintf(stderr, "ERROR: shared not line-aligned\n"); return 1;
    }

    double *results = malloc(iters * sizeof(double));

    fprintf(stderr, "== c2c_lat cpu-a=%d cpu-b=%d mem-node=%d "
            "iters=%d rounds=%lu ==\n",
            cpu_a, cpu_b, mem_node, iters, (unsigned long)rounds);

    for (int it = 0; it < iters; it++) {
        atomic_store_explicit(&sh->counter, 0, memory_order_release);
        _Atomic int go = 0;
        _Atomic int done = 0;
        worker_t WA = { 0, cpu_a, 0, sh, &go, &done, rounds * 2, 0 };
        worker_t WB = { 1, cpu_b, 1, sh, &go, &done, rounds * 2, 0 };
        pthread_t TA, TB;

        if (pthread_create(&TA, NULL, worker_fn, &WA) != 0 ||
            pthread_create(&TB, NULL, worker_fn, &WB) != 0) {
            fprintf(stderr, "pthread_create\n"); return 1;
        }
        /* small settle */
        usleep(50000);

        double t0 = now_sec();
        atomic_store_explicit(&go, 1, memory_order_release);

        pthread_join(TA, NULL);
        pthread_join(TB, NULL);
        double t1 = now_sec();

        if (WA.err || WB.err) {
            fprintf(stderr, "  iter=%d ERROR (a.err=%d b.err=%d)\n",
                    it, WA.err, WB.err);
            return 1;
        }

        double elapsed = t1 - t0;
        uint64_t final = atomic_load(&sh->counter);
        if (final < rounds * 2) {
            fprintf(stderr, "  iter=%d under-shot counter=%lu (wanted %lu)\n",
                    it, (unsigned long)final, (unsigned long)(rounds*2));
        }
        /* counter incremented 2*rounds times = `rounds` round trips */
        double ns_per_rt = (elapsed * 1e9) / (double)rounds;
        results[it] = ns_per_rt;
        fprintf(stderr, "  iter=%d rt=%lu elapsed=%.3fs  ns/rt=%.2f  "
                "ns/1-way=%.2f\n",
                it, (unsigned long)rounds, elapsed,
                ns_per_rt, ns_per_rt / 2.0);
    }

    /* stats */
    double *sorted = malloc(iters * sizeof(double));
    memcpy(sorted, results, iters * sizeof(double));
    qsort(sorted, iters, sizeof(double), cmp_double);
    double median = (iters % 2)
        ? sorted[iters/2]
        : 0.5 * (sorted[iters/2-1] + sorted[iters/2]);
    double mn = sorted[0], mx = sorted[iters-1];
    double sum = 0, sum2 = 0;
    for (int i = 0; i < iters; i++) { sum += results[i]; sum2 += results[i]*results[i]; }
    double mean = sum / iters;
    double var = (sum2 / iters) - mean*mean;
    double sd = var > 0 ? sqrt(var) : 0;

    fprintf(stderr, "SUMMARY: median rt=%.2f one-way=%.2f  "
            "min=%.2f max=%.2f mean=%.2f stddev=%.2f ns/rt\n",
            median, median/2.0, mn, mx, mean, sd);

    if (csv) {
        /* CSV: test,cpu_a,cpu_b,mem_node,iters,rounds,
                median_ns_rt,min_ns_rt,max_ns_rt,mean_ns_rt,stddev_ns_rt */
        printf("c2c_lat,%d,%d,%d,%d,%lu,%.3f,%.3f,%.3f,%.3f,%.3f\n",
               cpu_a, cpu_b, mem_node, iters, (unsigned long)rounds,
               median, mn, mx, mean, sd);
    }

    free(sorted); free(results);
    munmap(raw, pagesize);
    return 0;
}
