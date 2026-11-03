/*
 * latency.c - single-thread dependent-load pointer chase.
 *
 * The buffer holds one 8-byte pointer per 64-byte line. The pointers form
 * one random cycle through all lines, built with Sattolo's algorithm (a
 * Fisher-Yates shuffle that swaps element i only with an element j < i, which
 * yields a single n-cycle). Each load depends on the previous one, so the
 * hardware prefetcher cannot run ahead and elapsed / loads is the load-to-use
 * latency of one dependent load at that footprint.
 */
#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>

#define LINE_BYTES 64
#define HUGE_BYTES (2UL << 20)
#define MAX_SIZES 64
#define MIN_CHUNK_LOADS (1UL << 20)

static void *volatile sink; /* the pointer object is volatile, so the store survives */
static uint64_t rng_state;

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

static uint64_t xorshift64(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}

/* Accepts "4096", "16K", "1.5M", "2G" (K/M/G are powers of 1024). */
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

/* Maps round_up(bytes, 2 MiB) at a 2 MiB-aligned address. The mapping is returned in raw and raw_len
 * receive the mapping to pass to munmap. */
static uint8_t *alloc_buf(uint64_t bytes, int use_thp, void **raw, size_t *raw_len)
{
    size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);
    *raw_len = len + HUGE_BYTES;
    *raw = mmap(NULL, *raw_len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (*raw == MAP_FAILED) {
        perror("mmap");
        exit(2);
    }
    uint8_t *p = (uint8_t *)(((uintptr_t)*raw + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));
    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp
     * would still get 2 MiB pages. */
    if (madvise(p, len, use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)
        perror("madvise (continuing)");
    return p;
}

static long anon_huge_kb(void)
{
    FILE *f = fopen("/proc/self/smaps_rollup", "r");
    if (!f)
        return -1;
    char line[256];
    long kb = -1;
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "AnonHugePages: %ld kB", &kb) == 1)
            break;
    fclose(f);
    return kb;
}

/* First touch, then Sattolo shuffle of line indices, then index -> pointer.
 * slot selects which 8-byte word of each line carries this chain; the stored
 * pointer targets the same slot of the next line, so chase() needs no offset. */
static void build_cycle(uint8_t *buf, uint64_t n, int slot, uint64_t seed)
{
#define AT(i) (*(uint64_t *)(buf + (i) * LINE_BYTES + (slot) * 8))
    rng_state = seed;
    for (uint64_t i = 0; i < n; i++)
        AT(i) = i;
    for (uint64_t i = n - 1; i > 0; i--) {
        uint64_t j = xorshift64() % i;
        uint64_t tmp = AT(i);
        AT(i) = AT(j);
        AT(j) = tmp;
    }
    for (uint64_t i = 0; i < n; i++)
        AT(i) = (uint64_t)(uintptr_t)(buf + AT(i) * LINE_BYTES + slot * 8);
#undef AT
}

__attribute__((noinline)) static void *chase(void *p, uint64_t loads)
{
    for (uint64_t i = 0; i < loads; i += 8) {
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
    }
    return p;
}

static int build_cpu = -1, chase_cpu = -1; /* --build-cpu: build and first-touch the chain there, then chase on --cpu */

static void run_size(uint64_t bytes, int reps, double min_s, int min_cycles, int use_thp, int fresh)
{
    if (build_cpu >= 0)
        pin_cpu(build_cpu);
    if (bytes % (8 * LINE_BYTES) != 0) {
        fprintf(stderr, "size %lu is not a multiple of 512 bytes\n", (unsigned long)bytes);
        exit(2);
    }
    uint64_t n = bytes / LINE_BYTES;
    void *raw;
    size_t raw_len;
    uint8_t *buf = alloc_buf(bytes, use_thp, &raw, &raw_len);
    build_cycle(buf, n, 0, 0x9E3779B97F4A7C15ULL);
    for (int c = 1; c < fresh; c++)
        build_cycle(buf, n, c, 0x9E3779B97F4A7C15ULL * (uint64_t)(c + 1) + 12345);
    if (build_cpu >= 0) {
        chase(buf, n); /* the builder walks it once so its chiplet holds every line */
        pin_cpu(chase_cpu);
    }
    printf("# size_bytes=%lu AnonHugePages_kB=%ld build_cpu=%d\n", (unsigned long)bytes, anon_huge_kb(), build_cpu);

    double best = 1e30;
    uint64_t best_loads = 0;
    void *p = buf;
    if (fresh) {
        /* Fresh mode: chain 0 is walked twice (data resident, prefetcher trained on
         * chain 0 only); then each rep is exactly one pass over a chain that has
         * never been walked. A temporal prefetcher that replays a learned miss
         * sequence cannot help here. */
        if (build_cpu < 0) { /* with --build-cpu the builder's walk is the only warm-up */
            p = chase(p, n);
            p = chase(p, n);
        }
        sink = p;
        for (int c = 1; c < fresh; c++) {
            void *q = buf + c * 8;
            double t0 = now_s();
            q = chase(q, n);
            double t1 = now_s();
            sink = q;
            double ns = (t1 - t0) * 1e9 / (double)n;
            printf("%lu,fresh%d,%lu,%.3f\n", (unsigned long)bytes, c, (unsigned long)n, ns);
            if (ns < best) {
                best = ns;
                best_loads = n;
            }
        }
    } else {
        /* Chunk = whole cycles, at least MIN_CHUNK_LOADS loads, so the clock
         * read between chunks is negligible. */
        uint64_t chunk = n * (n >= MIN_CHUNK_LOADS ? 1 : MIN_CHUNK_LOADS / n);
        p = chase(p, n); /* warm-up: one full cycle */
        for (int rep = 0; rep < reps; rep++) {
            uint64_t loads = 0;
            double t0 = now_s(), t1;
            do {
                p = chase(p, chunk);
                loads += chunk;
                t1 = now_s();
            } while (t1 - t0 < min_s || loads < (uint64_t)min_cycles * n);
            double ns = (t1 - t0) * 1e9 / (double)loads;
            printf("%lu,%d,%lu,%.3f\n", (unsigned long)bytes, rep, (unsigned long)loads, ns);
            if (ns < best) {
                best = ns;
                best_loads = loads;
            }
        }
        sink = p;
    }
    printf("%lu,best,%lu,%.3f\n", (unsigned long)bytes, (unsigned long)best_loads, best);
    fflush(stdout);
    munmap(raw, raw_len);
}

static void usage(void)
{
    fprintf(stderr,
            "usage: latency [--cpu N] [--build-cpu N] [--min S] [--max S] [--sizes a,b,c] "
            "[--min-ms MS] [--min-cycles C] [--reps R] [--no-thp] [--fresh K]\n"
            "  sizes accept K/M/G suffixes; --min..--max doubles\n"
            "  --fresh K (2..8): K chains per line; warm up on chain 0, then time one\n"
            "    single pass over each of chains 1..K-1 (defeats temporal prefetchers;\n"
            "    one pass of a small size is too short to time: use it for >= 256K)\n");
    exit(2);
}

int main(int argc, char **argv)
{
    int cpu = -1, reps = 3, min_cycles = 2, use_thp = 1, fresh = 0;
    double min_s = 0.3;
    uint64_t min = 0, max = 0, sizes[MAX_SIZES];
    int nsizes = 0;

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        int more = i + 1 < argc;
        if (!strcmp(a, "--no-thp")) {
            use_thp = 0;
        } else if (!strcmp(a, "--cpu") && more) {
            cpu = atoi(argv[++i]);
        } else if (!strcmp(a, "--build-cpu") && more) {
            build_cpu = atoi(argv[++i]);
        } else if (!strcmp(a, "--min") && more) {
            min = parse_bytes(argv[++i]);
        } else if (!strcmp(a, "--max") && more) {
            max = parse_bytes(argv[++i]);
        } else if (!strcmp(a, "--min-ms") && more) {
            min_s = atof(argv[++i]) / 1000.0;
        } else if (!strcmp(a, "--min-cycles") && more) {
            min_cycles = atoi(argv[++i]);
        } else if (!strcmp(a, "--reps") && more) {
            reps = atoi(argv[++i]);
        } else if (!strcmp(a, "--fresh") && more) {
            fresh = atoi(argv[++i]);
            if (fresh < 2 || fresh > 8)
                usage();
        } else if (!strcmp(a, "--sizes") && more) {
            char *list = argv[++i];
            for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
                if (nsizes == MAX_SIZES)
                    usage();
                sizes[nsizes++] = parse_bytes(tok);
            }
        } else {
            usage();
        }
    }
    if (max == 0)
        max = min;
    for (uint64_t s = min; s && s <= max; s *= 2) {
        if (nsizes == MAX_SIZES)
            usage();
        sizes[nsizes++] = s;
    }
    if (nsizes == 0 || reps < 1 || min_cycles < 1)
        usage();
    if (build_cpu >= 0 && cpu < 0)
        usage();
    chase_cpu = cpu;
    if (cpu >= 0)
        pin_cpu(cpu);

    printf("# latency pointer chase: ns_per_load = elapsed_ns / loads; cpu=%d thp=%s min_ms=%.0f min_cycles=%d reps=%d fresh=%d\n",
           cpu, use_thp ? "madvise" : "nohugepage", min_s * 1000.0, min_cycles, reps, fresh);
    printf("size_bytes,rep,loads,ns_per_load\n");
    for (int i = 0; i < nsizes; i++)
        run_size(sizes[i], reps, min_s, min_cycles, use_thp, fresh);
    return 0;
}
