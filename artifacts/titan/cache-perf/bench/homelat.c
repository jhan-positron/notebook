/*
 * homelat.c - mesh-cache latency from each core to each home-node slice.
 *
 * Needs root for the mesh counters (perf_event_paranoid is 2 on CRB) and for
 * /proc/self/pagemap. Three steps:
 *
 * 1. Discover the home nodes (HN-S) of each mesh PMU (arm_cmn_0, arm_cmn_1):
 *    perf_event_open with bynodeid=1 fails with EINVAL for a node id that does
 *    not exist, so every id from 0 to 0xffff is tried once.
 * 2. Classify every 64 B line of a buffer by home node: flush the line (dc
 *    civac), read the per-node "home-bound requests received" counters, flush and
 *    load the line 256 times, read the counters again. The one node whose count
 *    rose by about 256 is the home of that line. The probes run on the PMU's
 *    own CPU and read 8 counters per syscall, to keep the kernel's traffic low. At most 8 nodes per DTC domain can be counted
 *    at once (hardware limit), so classification runs in passes.
 * 3. For each core and each home node: build a pointer chase over lines of
 *    that node only, load each line once to fill, push the lines out of L1 and L2
 *    with 8 MiB of random-order loads (they stay in the slice, 1 MiB per node;
 *    a sequential evictor read was found not to replace L2 lines), then time
 *    one pass over a never-walked chain through the same lines. Every timed
 *    chain is used exactly once, because the cores learn a repeated chain
 *    (temporal prefetcher) and the latency then drops to L2 level.
 *
 * Output (CSV files in --out DIR): nodes.csv, chunks.csv, homes.csv, latency.csv.
 * --no-perf assigns fake homes (line index modulo 128) so the chase code can be
 * tested without root; its latency numbers mean nothing.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/perf_event.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define LINE 64
#define HUGE_BYTES (2UL << 20)
#define NMESH 2
#define MAX_NODES 256 /* both meshes together */
#define MESH_X 9
#define MESH_Y 8
static uint64_t evict_bytes = 8UL << 20; /* --evict-bytes */
static int evict_reshuffle = 1;            /* --evict-fixed keeps one order; a repeated order gets learned and replayed */
#define DTC_LIMIT 8  /* counters per DTC domain, CMN_DT_NUM_COUNTERS in drivers/perf/arm-cmn.c */
#define MAX_CORES 1024

struct node {
    int mesh;
    uint16_t id;
    int x, y, port, dev, dtc;
    int fd;         /* open counter, or -1 */
    int done;       /* already used in a classification pass */
    uint64_t before;
    uint32_t *lines; /* line indices homed here */
    int nlines, cap;
};

static struct node nodes[MAX_NODES];
static int nnodes;
static int pmu_type[NMESH], pmu_cpu[NMESH];
static uint64_t event_cfg[NMESH];
static void *volatile sink;
static uint64_t rng_state = 0x9E3779B97F4A7C15ULL;

static void die(const char *what)
{
    fprintf(stderr, "homelat: %s: %s\n", what, strerror(errno));
    exit(2);
}

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

static uint64_t parse_bytes(const char *s)
{
    char *end;
    double v = strtod(s, &end), mul = 1;
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

/* "0-119", "0-118:2", "3,64,119" */
static int parse_list(char *list, int *out, int max)
{
    int n = 0;
    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
        char *e, *e2;
        long lo = strtol(tok, &e, 10), hi = lo, step = 1;
        if (e != tok && *e == '-') {
            hi = strtol(e + 1, &e2, 10);
            e = e2;
            if (*e == ':') {
                step = strtol(e + 1, &e2, 10);
                e = e2;
            }
        }
        if (e == tok || *e != '\0' || lo < 0 || hi < lo || step < 1) {
            fprintf(stderr, "bad list: %s\n", tok);
            exit(2);
        }
        for (long c = lo; c <= hi; c += step) {
            if (n == max) {
                fprintf(stderr, "list too long\n");
                exit(2);
            }
            out[n++] = (int)c;
        }
    }
    return n;
}

static void pin_cpu(int cpu)
{
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof set, &set) != 0)
        die("sched_setaffinity");
}

static uint8_t *alloc_buf(uint64_t bytes)
{
    size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);
    void *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED)
        die("mmap");
    uint8_t *p = (uint8_t *)(((uintptr_t)raw + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));
    if (madvise(p, len, MADV_HUGEPAGE) != 0)
        perror("madvise (continuing)");
    memset(p, 0, len);
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

static uint64_t pfn_of(int pagemap_fd, const void *addr)
{
    uint64_t entry = 0;
    off_t off = (off_t)((uintptr_t)addr / 4096) * 8;
    if (pread(pagemap_fd, &entry, 8, off) != 8)
        return 0;
    return (entry >> 63) ? (entry & ((1ULL << 55) - 1)) : 0;
}

/* ---- perf ---- */

static int read_sysfs_int(const char *path)
{
    FILE *f = fopen(path, "r");
    int v = -1;
    if (!f || fscanf(f, "%d", &v) != 1) {
        fprintf(stderr, "homelat: cannot read %s\n", path);
        exit(2);
    }
    fclose(f);
    return v;
}

/* Builds the config word from the sysfs event description "type=0x200,eventid=0x5,filter=0x1"
 * using the arm_cmn format: type bits 0-15, eventid 16-26, filter 27-30, bynodeid 31, nodeid 32-47. */
static uint64_t event_config(int mesh, const char *event)
{
    char path[256], text[256];
    snprintf(path, sizeof path, "/sys/bus/event_source/devices/arm_cmn_%d/events/%s", mesh, event);
    FILE *f = fopen(path, "r");
    if (!f || !fgets(text, sizeof text, f)) {
        fprintf(stderr, "homelat: cannot read %s\n", path);
        exit(2);
    }
    fclose(f);
    uint64_t cfg = 0;
    unsigned v;
    for (char *tok = strtok(text, ",\n"); tok; tok = strtok(NULL, ",\n")) {
        if (sscanf(tok, "type=0x%x", &v) == 1) cfg |= (uint64_t)v;
        else if (sscanf(tok, "eventid=0x%x", &v) == 1) cfg |= (uint64_t)v << 16;
        else if (sscanf(tok, "filter=0x%x", &v) == 1) cfg |= (uint64_t)v << 27;
        else {
            fprintf(stderr, "homelat: unknown field in %s: %s\n", path, tok);
            exit(2);
        }
    }
    return cfg;
}

static int perf_open(int mesh, uint16_t nodeid, int group_fd)
{
    struct perf_event_attr a;
    memset(&a, 0, sizeof a);
    a.type = (uint32_t)pmu_type[mesh];
    a.size = sizeof a;
    a.config = event_cfg[mesh] | (1ULL << 31) | ((uint64_t)nodeid << 32);
    a.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
    return (int)syscall(SYS_perf_event_open, &a, -1, pmu_cpu[mesh], group_fd, 0);
}

/* One group per (mesh, DTC quadrant): up to DTC_LIMIT counters read with one syscall.
 * Fewer syscalls matter: each read on a CPU other than the PMU's CPU is an interrupt to
 * that CPU, and the kernel's memory traffic from 128 such reads per probe (measured
 * 2026-11-02) buried the one load being classified under hundreds of requests. */
struct group {
    int leader_fd, n;
    int node_idx[DTC_LIMIT];
    uint64_t before[DTC_LIMIT];
};
static struct group groups[NMESH * 4];
static int ngroups;

/* reads a group: values[0..n-1], and enabled/running of the leader */
static void group_read(struct group *g, uint64_t *values, uint64_t *enabled, uint64_t *running)
{
    uint64_t r[3 + DTC_LIMIT];
    ssize_t want = (ssize_t)((3 + (size_t)g->n) * sizeof(uint64_t));
    if (read(g->leader_fd, r, sizeof r) != want)
        die("perf group read");
    if ((int)r[0] != g->n) {
        fprintf(stderr, "homelat: group read returned %d counters, expected %d\n", (int)r[0], g->n);
        exit(2);
    }
    *enabled = r[1]; *running = r[2];
    for (int i = 0; i < g->n; i++)
        values[i] = r[3 + i];
}

/* DTC domain of a crosspoint, from crb/results/cmn-map.txt (both meshes identical):
 * rows 4-7: columns 0-4 are DTC 1, columns 5-8 DTC 0; rows 0-3: columns 0-4 DTC 2, columns 5-8 DTC 3. */
static int dtc_of(int x, int y)
{
    if (y >= 4)
        return x <= 4 ? 1 : 0;
    return x <= 4 ? 2 : 3;
}

static void discover(int mesh)
{
    int found = 0, first_errno = 0;
    for (unsigned id = 0; id < 0x10000; id++) {
        int fd = perf_open(mesh, (uint16_t)id, -1);
        if (fd < 0) {
            if (!first_errno)
                first_errno = errno;
            if (errno == EACCES || errno == EPERM)
                die("perf_event_open (run as root)");
            continue;
        }
        close(fd);
        if (nnodes == MAX_NODES) {
            fprintf(stderr, "homelat: more than %d nodes\n", MAX_NODES);
            exit(2);
        }
        nodes[nnodes].mesh = mesh;
        nodes[nnodes].id = (uint16_t)id;
        nodes[nnodes].fd = -1;
        nnodes++;
        found++;
    }
    fprintf(stderr, "mesh %d: %d home nodes found (first error on a bad id: %s)\n", mesh, found, strerror(first_errno));
    if (found == 0) {
        fprintf(stderr, "homelat: no home node answered on mesh %d\n", mesh);
        exit(2);
    }
}

/* The node id packs x, y, port and device. Two layouts occur in the driver: port 3 bits +
 * device 2 bits, or port 2 bits + device 1 bit; x and y use 4 bits each on a 9 x 8 mesh. The
 * layout under which every id lands on a crosspoint of the map (x 1..7, y 1..5) is kept. */
static void decode_ids(void)
{
    const int layouts[2][2] = { { 3, 2 }, { 2, 1 } };
    for (int l = 0; l < 2; l++) {
        int pb = layouts[l][0], db = layouts[l][1], ok = 1;
        for (int i = 0; i < nnodes && ok; i++) {
            unsigned id = nodes[i].id;
            int dev = id & ((1 << db) - 1), port = (id >> db) & ((1 << pb) - 1);
            unsigned xy = id >> (pb + db);
            int x = (int)(xy >> 4), y = (int)(xy & 15);
            if (x < 0 || x >= MESH_X || y < 0 || y >= MESH_Y)
                ok = 0;
            nodes[i].x = x; nodes[i].y = y; nodes[i].port = port; nodes[i].dev = dev;
            nodes[i].dtc = dtc_of(x, y);
        }
        if (ok) {
            fprintf(stderr, "node id layout: x 4 bits, y 4 bits, port %d bits, device %d bits\n", pb, db);
            return;
        }
    }
    fprintf(stderr, "homelat: node ids do not decode onto a %d x %d mesh:", MESH_X, MESH_Y);
    for (int i = 0; i < nnodes; i++)
        fprintf(stderr, " %d:0x%x", nodes[i].mesh, nodes[i].id);
    fprintf(stderr, "\n");
    exit(2);
}

/* ---- classification ---- */

static inline void flush_line(const void *p)
{
    __asm__ volatile("dc civac, %0\n\tdsb sy" : : "r"(p) : "memory");
}

static inline uint64_t load_line(const void *p)
{
    uint64_t v;
    __asm__ volatile("ldr %0, [%1]\n\tdsb sy" : "=r"(v) : "r"(p) : "memory");
    return v;
}

static const char *marker_path = "/tmp/positron-perf.RUNNING"; /* --marker PATH: stop if it appears */
static double marker_checked;

/* Checked at least once per second inside every long loop: the shared-host rule. */
static void check_marker(void)
{
    double now = now_s();
    if (now - marker_checked < 1.0)
        return;
    marker_checked = now;
    if (access(marker_path, F_OK) == 0) {
        fprintf(stderr, "homelat: %s exists: stopping\n", marker_path);
        exit(3);
    }
}

static int probe_loads = 256; /* --probe-loads: flush+load repeats inside one counter window */
static int probe_verbose = 3;  /* raw deltas of the first probes go to stderr */

/* Returns the index in nodes[] of the home node of line i: the open node whose counter rose by
 * at least 3/4 of probe_loads while every other open node rose by at most 1/4 of it. Returns -1
 * if no node rose that much (the home is not among the open nodes) and -2 if the rule fails
 * otherwise (noise; the caller retries). */
static int probe(uint8_t *buf, uint64_t nlines, uint64_t i)
{
    uint8_t *p = buf + i * LINE;
    uint64_t vals[DTC_LIMIT], en, run;
    /* make the neighbours resident so a next-line prefetch adds no mesh request */
    if (i > 0) sink = (void *)(uintptr_t)load_line(p - LINE);
    if (i + 1 < nlines) sink = (void *)(uintptr_t)load_line(p + LINE);
    flush_line(p);
    for (int g = 0; g < ngroups; g++) {
        group_read(&groups[g], vals, &en, &run);
        for (int k = 0; k < groups[g].n; k++)
            groups[g].before[k] = vals[k];
    }
    for (int r = 0; r < probe_loads; r++) {
        sink = (void *)(uintptr_t)load_line(p);
        flush_line(p);
    }
    int hit = -1, over_high = 0, over_low = 0;
    uint64_t best = 0, second = 0;
    int best_node = -1, second_node = -1;
    for (int g = 0; g < ngroups; g++) {
        group_read(&groups[g], vals, &en, &run);
        for (int k = 0; k < groups[g].n; k++) {
            uint64_t d = vals[k] - groups[g].before[k];
            int node = groups[g].node_idx[k];
            if (d >= (uint64_t)probe_loads * 3 / 4) { over_high++; hit = node; }
            else if (d > (uint64_t)probe_loads / 4) over_low++;
            if (d > best) { second = best; second_node = best_node; best = d; best_node = node; }
            else if (d > second) { second = d; second_node = node; }
        }
    }
    if (probe_verbose > 0) {
        fprintf(stderr, "  probe line %lu: best mesh %d node 0x%x +%lu, second mesh %d node 0x%x +%lu, %d node(s) >= %d, %d node(s) in between\n",
                (unsigned long)i, best_node >= 0 ? nodes[best_node].mesh : -1, best_node >= 0 ? nodes[best_node].id : 0, (unsigned long)best,
                second_node >= 0 ? nodes[second_node].mesh : -1, second_node >= 0 ? nodes[second_node].id : 0, (unsigned long)second,
                over_high, probe_loads * 3 / 4, over_low);
        probe_verbose--;
    }
    if (over_high == 1 && over_low == 0)
        return hit;
    return over_high == 0 && over_low == 0 ? -1 : -2;
}

static void node_add_line(struct node *n, uint32_t line)
{
    if (n->nlines == n->cap) {
        n->cap = n->cap ? n->cap * 2 : 1024;
        n->lines = realloc(n->lines, (size_t)n->cap * sizeof *n->lines);
        if (!n->lines)
            die("realloc");
    }
    n->lines[n->nlines++] = line;
}

/* home[i] = node index, -1 = not found by any node, -2 = ambiguous after retries */
static void classify(uint8_t *buf, uint64_t nlines, int16_t *home, int retries)
{
    for (uint64_t i = 0; i < nlines; i++)
        home[i] = -1;
    int pass = 0, left;
    for (;;) {
        /* open the next batch: one group per (mesh, dtc) with at most DTC_LIMIT nodes */
        int opened = 0;
        ngroups = 0;
        for (int m = 0; m < NMESH; m++)
            for (int d = 0; d < 4; d++) {
                struct group *g = &groups[ngroups];
                g->n = 0; g->leader_fd = -1;
                for (int k = 0; k < nnodes && g->n < DTC_LIMIT; k++) {
                    struct node *n = &nodes[k];
                    if (n->done || n->mesh != m || n->dtc != d)
                        continue;
                    n->fd = perf_open(m, n->id, g->leader_fd);
                    if (n->fd < 0) {
                        if (g->n == 0)
                            die("perf_event_open for a discovered node");
                        fprintf(stderr, "mesh %d node 0x%x: cannot join its group (%s), left for a later pass\n", m, n->id, strerror(errno));
                        break;
                    }
                    if (g->n == 0)
                        g->leader_fd = n->fd;
                    g->node_idx[g->n++] = k;
                    opened++;
                }
                if (g->n)
                    ngroups++;
            }
        if (!opened)
            break;
        pass++;
        double t0 = now_s();
        long classified = 0, ambiguous = 0, none = 0;
        for (uint64_t i = 0; i < nlines; i++) {
            if (home[i] != -1)
                continue;
            if ((i & 1023) == 0)
                check_marker();
            int r = probe(buf, nlines, i);
            for (int t = 0; t < retries && r == -2; t++)
                r = probe(buf, nlines, i);
            if (r >= 0) {
                home[i] = (int16_t)r;
                node_add_line(&nodes[r], (uint32_t)i);
                classified++;
            } else if (r == -2) {
                ambiguous++;
            } else {
                none++;
            }
            /* half of the nodes are open in pass 1, so about half of the first lines must classify */
            if (pass == 1 && i == 255 && classified == 0) {
                fprintf(stderr, "homelat: none of the first 256 lines was classified (%ld ambiguous, the rest raised no counter). "
                        "If the probes above show one node far ahead, raise --probe-loads; if none stands out, the event does not count these loads: "
                        "try --event hns_pocq_reqs_recvd_all or hns_slc_sf_cache_access_all\n", ambiguous);
                exit(2);
            }
        }
        /* a group that was not running the whole time was multiplexed: results unusable */
        for (int g = 0; g < ngroups; g++) {
            uint64_t vals[DTC_LIMIT], en, run;
            group_read(&groups[g], vals, &en, &run);
            if (en != run) {
                fprintf(stderr, "homelat: a counter group (mesh %d node 0x%x) ran %.1f%% of the time: multiplexed, too many counters per DTC\n",
                        nodes[groups[g].node_idx[0]].mesh, nodes[groups[g].node_idx[0]].id, 100.0 * (double)run / (double)en);
                exit(2);
            }
            for (int k = 0; k < groups[g].n; k++) {
                struct node *n = &nodes[groups[g].node_idx[k]];
                close(n->fd);
                n->fd = -1;
                n->done = 1;
            }
        }
        ngroups = 0;
        left = 0;
        for (uint64_t i = 0; i < nlines; i++)
            left += home[i] == -1;
        fprintf(stderr, "pass %d: %d counters, %ld lines classified, %ld ambiguous after retries, %ld raised no open node, %d left, %.1f s\n",
                pass, opened, classified, ambiguous, none, left, now_s() - t0);
        if (!left)
            break;
    }
    long unknown = 0;
    for (uint64_t i = 0; i < nlines; i++)
        unknown += home[i] < 0;
    fprintf(stderr, "classification: %lu lines, %ld without a home (%.2f%%)\n", (unsigned long)nlines, unknown,
            100.0 * (double)unknown / (double)nlines);
}

/* Verification (reviewer's request): a sample of classified lines is probed again with only the
 * assigned node's counter open (plus one control node that is not the home). The assigned node
 * must rise by >= 3/4 of the loads and the control by <= 1/4. Returns the agreement rate. */
static double verify_classification(uint8_t *buf, uint64_t nlines, const int16_t *home, int sample, long *control_false)
{
    long agree = 0, tested = 0;
    *control_false = 0;
    for (int s = 0; s < sample; s++) {
        uint64_t i = xorshift64() % nlines;
        if (home[i] < 0)
            continue;
        int k = home[i], c = (k + 1 + (int)(xorshift64() % (uint64_t)(nnodes - 1))) % nnodes; /* a different node */
        struct node *n = &nodes[k], *cn = &nodes[c];
        struct group *g = &groups[0], *cg = &groups[1];
        n->fd = perf_open(n->mesh, n->id, -1);
        cn->fd = perf_open(cn->mesh, cn->id, -1);
        if (n->fd < 0 || cn->fd < 0)
            die("perf_event_open in verification");
        g->leader_fd = n->fd; g->n = 1; g->node_idx[0] = k;
        cg->leader_fd = cn->fd; cg->n = 1; cg->node_idx[0] = c;
        ngroups = 2;
        int saved = probe_verbose;
        probe_verbose = 0;
        uint64_t vals[DTC_LIMIT], en, run, c0;
        group_read(cg, vals, &en, &run);
        c0 = vals[0];
        int r = probe(buf, nlines, i);
        probe_verbose = saved;
        group_read(cg, vals, &en, &run);
        tested++;
        if (r == k)
            agree++;
        if (vals[0] - c0 > (uint64_t)probe_loads / 4) /* the control rose, whatever the verdict (reviewer's request) */
            (*control_false)++;
        close(n->fd); close(cn->fd);
        n->fd = cn->fd = -1;
        ngroups = 0;
        check_marker();
    }
    fprintf(stderr, "verification: %ld of %ld sampled lines confirmed by a lone counter (%.2f%%), the control node rose in %ld probes\n",
            agree, tested, tested ? 100.0 * (double)agree / (double)tested : 0.0, *control_false);
    return tested ? (double)agree / (double)tested : 0.0;
}

/* --no-perf: fake homes so the chase code can be exercised without root */
static void classify_fake(uint64_t nlines, int16_t *home)
{
    nnodes = 128;
    for (int k = 0; k < nnodes; k++) {
        nodes[k].mesh = k / 64;
        nodes[k].id = (uint16_t)k;
        nodes[k].x = 1 + (k % 64) / 10; nodes[k].y = 1 + (k % 64) % 5; nodes[k].dev = k & 1;
        nodes[k].fd = -1;
    }
    for (uint64_t i = 0; i < nlines; i++) {
        home[i] = (int16_t)(i % 128);
        node_add_line(&nodes[i % 128], (uint32_t)i);
    }
}

/* ---- latency ---- */

static int cmp_u32(const void *a, const void *b)
{
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return x < y ? -1 : x > y;
}

/* Sattolo cycle over the given lines, stored in 8-byte slot s of each line. The lines must be
 * distinct: a duplicate would overwrite a successor and close a shorter cycle, so the timed pass
 * would repeat lines (reviewer's catch, 2026-11-02). Sattolo's shuffle yields one n-cycle over the
 * indices, so with distinct lines every line is visited exactly once before the start recurs. */
static void build_chain(uint8_t *buf, const uint32_t *lines, int n, int slot)
{
    uint32_t *perm = malloc((size_t)n * sizeof *perm), *sorted = malloc((size_t)n * sizeof *sorted);
    if (!perm || !sorted)
        die("malloc");
    memcpy(sorted, lines, (size_t)n * sizeof *sorted);
    qsort(sorted, (size_t)n, sizeof *sorted, cmp_u32);
    for (int i = 1; i < n; i++)
        if (sorted[i] == sorted[i - 1]) {
            fprintf(stderr, "homelat: duplicate line %u in a chain of %d lines\n", sorted[i], n);
            exit(2);
        }
    free(sorted);
    for (int i = 0; i < n; i++)
        perm[i] = (uint32_t)i;
    for (int i = n - 1; i > 0; i--) {
        int j = (int)(xorshift64() % (uint64_t)i);
        uint32_t t = perm[i]; perm[i] = perm[j]; perm[j] = t;
    }
    /* perm is a single cycle: line lines[perm[i]] points to line lines[perm[(i+1) % n]] */
    for (int i = 0; i < n; i++) {
        uint8_t *from = buf + (uint64_t)lines[perm[i]] * LINE + slot * 8;
        uint8_t *to = buf + (uint64_t)lines[perm[(i + 1) % n]] * LINE + slot * 8;
        *(uint64_t *)from = (uint64_t)(uintptr_t)to;
    }
    free(perm);
}

__attribute__((noinline)) static void *chase(void *p, int loads)
{
    for (int i = 0; i < loads; i += 8) {
        p = *(void **)p; p = *(void **)p; p = *(void **)p; p = *(void **)p;
        p = *(void **)p; p = *(void **)p; p = *(void **)p; p = *(void **)p;
    }
    return p;
}

static uint32_t *evict_order; /* random permutation of the evictor's lines */

static void evict_init(void)
{
    uint32_t n = (uint32_t)(evict_bytes / LINE);
    if (!evict_order) {
        evict_order = malloc((n ? n : 1) * sizeof *evict_order);
        if (!evict_order)
            die("malloc");
    }
    for (uint32_t i = 0; i < n; i++)
        evict_order[i] = i;
    for (uint32_t i = n - 1; i > 0; i--) {
        uint32_t j = (uint32_t)(xorshift64() % (i + 1)), t = evict_order[i];
        evict_order[i] = evict_order[j]; evict_order[j] = t;
    }
}

/* Independent loads in random order, a new order every call: no stream for a prefetcher to
 * detect, and no repeated sequence for the temporal prefetcher to learn. Measured 2026-11-02:
 * with one fixed order the timed passes fell from 30 ns to 7 ns from the second repeat on. */
static void evict(const uint8_t *ev)
{
    uint64_t s = 0;
    uint32_t n = (uint32_t)(evict_bytes / LINE);
    if (evict_reshuffle)
        evict_init();
    for (uint32_t i = 0; i < n; i++)
        s += *(const uint64_t *)(ev + (uint64_t)evict_order[i] * LINE);
    sink = (void *)(uintptr_t)s;
}

static int cmp_double(const void *a, const void *b)
{
    double x = *(const double *)a, y = *(const double *)b;
    return x < y ? -1 : x > y;
}

/* Loads every line of the set once, independent loads in a new random order each call. A
 * dependent fill chain walked every repeat was learned by the temporal prefetcher, which then
 * replayed it during the timed pass and pulled the whole set into L2. */
static void fill_random(const uint8_t *buf, const uint32_t *lines, int n)
{
    uint64_t s = 0, start = xorshift64() % (uint64_t)n, step = (xorshift64() % (uint64_t)(n - 1)) | 1;
    for (;;) { /* step must be coprime with n to visit every line once (reviewer's catch, 2026-11-02) */
        uint64_t a = (uint64_t)n, b = step % (uint64_t)n;
        while (b) { uint64_t r = a % b; a = b; b = r; }
        if (a == 1)
            break;
        step = (step + 2) % (uint64_t)n;
        if (step < 2)
            step = 3;
    }
    for (int i = 0; i < n; i++)
        s += *(const uint64_t *)(buf + (uint64_t)lines[(start + (uint64_t)i * step) % (uint64_t)n] * LINE);
    sink = (void *)(uintptr_t)s;
}

/* Fresh-chain latency over the given lines. Chains 0..reps-1 (one 8-byte slot of each line per
 * chain) are each timed exactly once: fill the set with random independent loads, evict L1/L2,
 * time one pass of chain r. Returns median, min and max in ns per load. reps is at most 8. */
#define NCSTATE 5
static int cstate_fds[NCSTATE] = { -1, -1, -1, -1, -1 }; /* --verify-slices counters, see verify_slices() */
static uint64_t cstate_delta[NCSTATE];
static int cstate_multiplexed;
static int verify_lenient; /* --verify-lenient: a failed cache-state check is recorded (valid=0 in verify.csv) and the run continues; off in run_sudo.sh */

/* Reads a group through its leader and returns its n values in open order. A read through a member
 * descriptor also returns the whole group with the leader first, which is why an earlier version
 * reported the leader's count under the member's name (reviewer's catch, 2026-11-02). */
static void group_values(int leader_fd, int n, uint64_t *out)
{
    uint64_t r[3 + DTC_LIMIT];
    ssize_t want = (ssize_t)((3 + (size_t)n) * sizeof(uint64_t)), got = read(leader_fd, r, sizeof r);
    if (got != want) {
        fprintf(stderr, "homelat: cache-state group read returned %zd bytes, expected %zd for %d counters\n", got, want, n);
        exit(2);
    }
    if ((int)r[0] != n) {
        fprintf(stderr, "homelat: group read returned %d counters, expected %d\n", (int)r[0], n);
        exit(2);
    }
    if (r[1] != r[2])
        cstate_multiplexed = 1;
    for (int i = 0; i < n; i++)
        out[i] = r[3 + i];
}

/* cstate counters are organised as groups: cstate_group[j] is the leader index for value j */
static int cstate_leader[NCSTATE] = { -1, -1, -1, -1, -1 }, cstate_pos[NCSTATE];

static void cstate_read(uint64_t *vals)
{
    for (int j = 0; j < NCSTATE; j++) {
        if (cstate_fds[j] < 0) { vals[j] = 0; continue; }
        if (cstate_leader[j] != j)
            continue; /* a member: filled when its leader is read */
        uint64_t v[DTC_LIMIT];
        int n = 0;
        for (int k = j; k < NCSTATE; k++) n += cstate_fds[k] >= 0 && cstate_leader[k] == j;
        group_values(cstate_fds[j], n, v);
        for (int k = j; k < NCSTATE; k++)
            if (cstate_fds[k] >= 0 && cstate_leader[k] == j)
                vals[k] = v[cstate_pos[k]];
    }
}

/* ns_all receives every repeat in run order (reviewer's request: keep each repeat). */
static void measure(uint8_t *buf, const uint8_t *ev, const uint32_t *lines, int n, int reps,
                    double *med, double *mn, double *mx, double *ns_all)
{
    for (int s = 0; s < reps; s++)
        build_chain(buf, lines, n, s);
    double ns[8];
    uint8_t *p0 = buf + (uint64_t)lines[0] * LINE;
    for (int r = 0; r < reps; r++) {
        fill_random(buf, lines, n);
        evict(ev);
        uint64_t before[NCSTATE], after[NCSTATE];
        if (cstate_fds[0] >= 0)
            cstate_read(before);
        double t0 = now_s();
        sink = chase(p0 + 8 * r, n);
        double t1 = now_s();
        if (cstate_fds[0] >= 0) {
            cstate_read(after);
            for (int j = 0; j < NCSTATE; j++) cstate_delta[j] += after[j] - before[j];
        }
        ns[r] = (t1 - t0) * 1e9 / (double)n;
        ns_all[r] = ns[r];
    }
    qsort(ns, (size_t)reps, sizeof ns[0], cmp_double);
    *mn = ns[0]; *mx = ns[reps - 1]; *med = ns[reps / 2];
}

/* Cache-state check (reviewer's request): for a few real slices, half on each mesh, count during the
 * timed chains only: SLC accesses summed over every node of mesh 0 and of mesh 1 (bynodeid=0), the
 * home node's own accesses and misses, and this core's L2 refills (raw event 0x17). Expected per timed
 * load: about one SLC access somewhere, no miss at the home, about one L2 refill. A line homed on the
 * other mesh is served by the local proxy's cache partition (the LCC of a local HN-S, CMN S3 TRM page
 * 1216), so for a remote slice the home itself may see no access while the local mesh's total shows one
 * (measured 2026-11-02: 0.00 to 0.04 accesses at four remote homes, 1.3 L2 refills, 11 to 29 ns). */
static int open_counter(uint32_t type, uint64_t config, int cpu, int pid, int group_fd)
{
    struct perf_event_attr a;
    memset(&a, 0, sizeof a);
    a.type = type; a.size = sizeof a; a.config = config;
    a.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
    return (int)syscall(SYS_perf_event_open, &a, pid, cpu, group_fd, 0);
}

static void cstate_open_group(int j, uint32_t type, uint64_t config, int cpu, int pid, int leader)
{
    cstate_leader[j] = leader < 0 ? j : leader;
    cstate_pos[j] = 0;
    if (leader >= 0)
        for (int k = leader; k < j; k++) cstate_pos[j] += cstate_leader[k] == leader;
    cstate_fds[j] = open_counter(type, config, cpu, pid, leader < 0 ? -1 : cstate_fds[leader]);
    if (cstate_fds[j] < 0)
        die("perf_event_open for the cache-state check");
}

static void cstate_close(void)
{
    for (int j = 0; j < NCSTATE; j++) {
        if (cstate_fds[j] >= 0) close(cstate_fds[j]);
        cstate_fds[j] = -1;
        cstate_leader[j] = -1; /* a stale leader entry made the next pass count a closed member (2026-11-02) */
    }
}

/* An empty counter window with the same cache state as the timed one: fill the set and read the
 * evictor exactly as measure() does, then take the two counter snapshots and the two clock reads
 * with no chase between them, reps times. What the window counts is the overhead of the reads
 * themselves under the post-eviction cache state (reviewer's request, 2026-11-02). */
static void cstate_baseline(uint8_t *buf, const uint8_t *ev, const uint32_t *lines, int n, int reps, uint64_t *base)
{
    uint64_t b[NCSTATE], a[NCSTATE];
    memset(base, 0, NCSTATE * sizeof *base);
    for (int r = 0; r < reps; r++) {
        fill_random(buf, lines, n);
        evict(ev);
        cstate_read(b);
        double t0 = now_s();
        sink = (void *)(uintptr_t)t0;
        double t1 = now_s();
        sink = (void *)(uintptr_t)t1;
        cstate_read(a);
        for (int j = 0; j < NCSTATE; j++) base[j] += a[j] - b[j];
    }
}

static void verify_slices(uint8_t *buf, const uint8_t *ev, int core, int count, int lines_per_node, int reps, const char *out)
{
    char path[512];
    snprintf(path, sizeof path, "%s/verify.csv", out);
    FILE *f = fopen(path, "w");
    if (!f)
        die("verify.csv");
    fprintf(f, "core,mesh,node_id_hex,x,y,dev,lines,timed_loads,home_acc,home_miss,l2_refills_a,ns_median_a,"
               "acc_mesh0,miss_mesh0,acc_mesh1,miss_mesh1,l2_refills_b,ns_median_b,baseline_slc_accesses_per_window,baseline_l2_refills_per_window,multiplexed,valid\n");
    uint64_t acc_cfg[NMESH], miss_cfg[NMESH];
    for (int m = 0; m < NMESH; m++) {
        acc_cfg[m] = event_config(m, "hns_slc_sf_cache_access_all");
        miss_cfg[m] = event_config(m, "hns_cache_miss_all");
    }
    pin_cpu(core);
    int bad = 0;
    for (int s = 0; s < count; s++) {
        int k = (int)(((uint64_t)s * (uint64_t)nnodes + xorshift64() % (uint64_t)(nnodes / count)) / (uint64_t)count) % nnodes;
        struct node *n = &nodes[k];
        int cn = n->nlines < lines_per_node ? n->nlines & ~7 : lines_per_node;
        if (cn < 64)
            continue;
        uint64_t nid = (1ULL << 31) | ((uint64_t)n->id << 32);
        double loads = (double)cn * (double)reps, med_a, med_b, mn, mx, all[8];
        uint64_t base_a[NCSTATE], base_b[NCSTATE];
        int mux = 0;
        /* pass A: the home node's own accesses and misses, and this core's L2 refills */
        cstate_multiplexed = 0;
        cstate_open_group(0, (uint32_t)pmu_type[n->mesh], acc_cfg[n->mesh] | nid, pmu_cpu[n->mesh], -1, -1);
        cstate_open_group(1, (uint32_t)pmu_type[n->mesh], miss_cfg[n->mesh] | nid, pmu_cpu[n->mesh], -1, 0);
        cstate_open_group(2, PERF_TYPE_RAW, 0x17, -1, 0, -1);
        cstate_baseline(buf, ev, n->lines, cn, reps, base_a);
        memset(cstate_delta, 0, sizeof cstate_delta);
        measure(buf, ev, n->lines, cn, reps, &med_a, &mn, &mx, all);
        double ha = ((double)cstate_delta[0] - (double)base_a[0]) / loads, hm = ((double)cstate_delta[1] - (double)base_a[1]) / loads,
               rfa = ((double)cstate_delta[2] - (double)base_a[2]) / loads;
        mux |= cstate_multiplexed;
        cstate_close();
        /* pass B: accesses and misses summed over every home node of each mesh (two groups), and L2 refills.
         * Four events per crosspoint is the DTM limit, so the home's own counters cannot join this pass. */
        cstate_multiplexed = 0;
        cstate_open_group(0, (uint32_t)pmu_type[0], acc_cfg[0], pmu_cpu[0], -1, -1);
        cstate_open_group(1, (uint32_t)pmu_type[0], miss_cfg[0], pmu_cpu[0], -1, 0);
        cstate_open_group(2, (uint32_t)pmu_type[1], acc_cfg[1], pmu_cpu[1], -1, -1);
        cstate_open_group(3, (uint32_t)pmu_type[1], miss_cfg[1], pmu_cpu[1], -1, 2);
        cstate_open_group(4, PERF_TYPE_RAW, 0x17, -1, 0, -1);
        cstate_baseline(buf, ev, n->lines, cn, reps, base_b);
        memset(cstate_delta, 0, sizeof cstate_delta);
        measure(buf, ev, n->lines, cn, reps, &med_b, &mn, &mx, all);
        double a0 = ((double)cstate_delta[0] - (double)base_b[0]) / loads, m0 = ((double)cstate_delta[1] - (double)base_b[1]) / loads,
               a1 = ((double)cstate_delta[2] - (double)base_b[2]) / loads, m1 = ((double)cstate_delta[3] - (double)base_b[3]) / loads,
               rfb = ((double)cstate_delta[4] - (double)base_b[4]) / loads;
        mux |= cstate_multiplexed;
        cstate_close();
        /* The decisive test for a local slice is its home's own counters: about 1 access and under 0.1 misses
         * per timed load (measured 0.000 to 0.027 misses in every run). Whole-mesh misses (0.03 to 0.35 per load
         * summed over both meshes, 2026-11-02) are recorded with no attribution. */
        int local = n->mesh == 0; /* the probing core (CPU 0 or 3) is on arm_cmn_0 */
        int ok = 1;
        if (rfa < 0.8 || rfb < 0.8 || med_a < 8.0 || med_a > 100.0 || a0 + a1 < 0.8 || mux ||
            (local && (ha < 0.8 || hm > 0.1)))
        { ok = 0; bad++; }
        double base_acc = ((double)base_b[0] + (double)base_b[2]) / (double)reps, base_rf = (double)base_b[4] / (double)reps;
        fprintf(f, "%d,%d,0x%x,%d,%d,%d,%d,%.0f,%.3f,%.3f,%.3f,%.2f,%.3f,%.3f,%.3f,%.3f,%.3f,%.2f,%.1f,%.1f,%d,%d\n", core, n->mesh, n->id, n->x, n->y, n->dev, cn, loads,
                ha, hm, rfa, med_a, a0, m0, a1, m1, rfb, med_b, base_acc, base_rf, mux, ok);
        fprintf(stderr, "cache state, mesh %d node 0x%x from core %d, per timed load: home acc %.2f miss %.3f, L2 refills %.2f, %.1f ns | "
                        "mesh0 acc %.2f miss %.3f, mesh1 acc %.2f miss %.3f, L2 refills %.2f, %.1f ns%s\n",
                n->mesh, n->id, core, ha, hm, rfa, med_a, a0, m0, a1, m1, rfb, med_b, mux ? " (multiplexed!)" : "");
        /* Acceptance: the loads must miss L2 (refills about 1), reach the mesh (accesses on the two meshes
         * about 1 or more), hit in the serving cache (misses on the two meshes under 0.1 per load), and take
         * mesh latency (8 to 100 ns). For a local slice the home itself must see about 1 access per load. */
        /* Measured 2026-11-02 04:33 UTC on CRB: local slices show 1.06 to 1.08 accesses and 0.005 to 0.030 misses
         * per load at the home; the whole-mesh totals add 0.6 to 0.8 accesses and 0.05 to 0.14 misses per load from
         * the other traffic a load triggers, so the whole-mesh miss limit is 0.2 and the decisive test for a local
         * slice is the home's own miss rate. */
        /* A local slice (the probing core's own mesh) must serve its loads itself: about 1 access and under 0.1
         * misses at the home. A remote slice is served elsewhere and its home sees about 0 accesses; the remote
         * rows are "latency by home group" and carry no slice-distance claim. Whole-mesh accesses and misses
         * (pass B) exceed the timed loads by amounts that are recorded but not attributed (reviewer, 2026-11-02). */

        check_marker();
    }
    fclose(f);
    if (bad) {
        fprintf(stderr, "homelat: cache-state check failed for %d of %d slices (per timed load: about 1 L2 refill, about 1 mesh access, "
                        "8 to 100 ns, no multiplexing, and for a local slice about 1 access and under 0.1 misses at the home)%s\n",
                bad, count, verify_lenient ? "; --verify-lenient: recorded, continuing" : "");
        if (!verify_lenient)
            exit(2);
        return;
    }
    fprintf(stderr, "cache-state check passed for %d slices\n", count);
}

static void usage(void)
{
    fprintf(stderr,
            "usage: homelat [--bytes B] [--cores LIST] [--lines-per-node N] [--reps R] [--retries K]\n"
            "               [--event NAME] [--out DIR] [--no-perf] [--evict-bytes B] [--evict-fixed] [--probe-loads K]\n"
            "               [--expect-nodes N] [--verify-sample N] [--verify-slices K] [--verify-lenient] [--marker PATH]\n"
            "  defaults: 16M, cores 0-119, 2048 lines per node, 7 reps, 3 retries, event hns_pocq_reqs_recvd_hbt,\n"
            "            out ., 64 home nodes per mesh expected, 512 lines re-verified, 8 slices cache-state checked\n");
    exit(2);
}

int main(int argc, char **argv)
{
    uint64_t bytes = 16UL << 20;
    int cores[MAX_CORES], ncores = 0, lines_per_node = 2048, reps = 7, retries = 3, use_perf = 1;
    /* hbt = home-bound traffic. With the plain "read" filter a load of a line homed on the other
     * mesh counted at two nodes: the local proxy (the LCN role of a local HN-S) and the true home
     * (measured 2026-11-02: +255 at mesh 0 node 0x288 and +255 at mesh 1 node 0xa0 for one line
     * probed from CPU 0). The proxy's share is LCN-bound traffic, which hbt excludes. */
    const char *event = "hns_pocq_reqs_recvd_hbt", *out = ".";
    int expect_nodes = 64, verify_sample = 512, verify_count = 8;
    char default_cores[] = "0-119";
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        int more = i + 1 < argc;
        if (!strcmp(a, "--bytes") && more) bytes = parse_bytes(argv[++i]);
        else if (!strcmp(a, "--cores") && more) ncores = parse_list(argv[++i], cores, MAX_CORES);
        else if (!strcmp(a, "--lines-per-node") && more) lines_per_node = atoi(argv[++i]);
        else if (!strcmp(a, "--reps") && more) reps = atoi(argv[++i]);
        else if (!strcmp(a, "--retries") && more) retries = atoi(argv[++i]);
        else if (!strcmp(a, "--event") && more) event = argv[++i];
        else if (!strcmp(a, "--out") && more) out = argv[++i];
        else if (!strcmp(a, "--no-perf")) use_perf = 0;
        else if (!strcmp(a, "--evict-bytes") && more) evict_bytes = parse_bytes(argv[++i]);
        else if (!strcmp(a, "--evict-fixed")) evict_reshuffle = 0;
        else if (!strcmp(a, "--probe-loads") && more) probe_loads = atoi(argv[++i]);
        else if (!strcmp(a, "--expect-nodes") && more) expect_nodes = atoi(argv[++i]);
        else if (!strcmp(a, "--verify-sample") && more) verify_sample = atoi(argv[++i]);
        else if (!strcmp(a, "--verify-slices") && more) verify_count = atoi(argv[++i]);
        else if (!strcmp(a, "--marker") && more) marker_path = argv[++i];
        else if (!strcmp(a, "--verify-lenient")) verify_lenient = 1;
        else usage();
    }
    if (!ncores)
        ncores = parse_list(default_cores, cores, MAX_CORES);
    if (reps < 1 || reps > 8 || lines_per_node < 64 || bytes % HUGE_BYTES || probe_loads < 2)
        usage();
    lines_per_node &= ~7;

    char path[512];
    snprintf(path, sizeof path, "%s/nodes.csv", out);
    FILE *fnodes = fopen(path, "w");
    snprintf(path, sizeof path, "%s/chunks.csv", out);
    FILE *fchunks = fopen(path, "w");
    snprintf(path, sizeof path, "%s/homes.csv", out);
    FILE *fhomes = fopen(path, "w");
    snprintf(path, sizeof path, "%s/latency.csv", out);
    FILE *flat = fopen(path, "w");
    if (!fnodes || !fchunks || !fhomes || !flat)
        die("cannot create output files in --out");

    pin_cpu(cores[0]);
    uint64_t nlines = bytes / LINE;
    uint8_t *buf = alloc_buf(bytes);
    uint8_t *ev = alloc_buf(evict_bytes ? evict_bytes : HUGE_BYTES);
    evict_init();
    long huge_kb = anon_huge_kb();
    fprintf(stderr, "buffer %lu MiB, %lu lines, AnonHugePages %ld kB\n", (unsigned long)(bytes >> 20),
            (unsigned long)nlines, huge_kb);
    if (huge_kb < (long)(bytes >> 10))
        fprintf(stderr, "warning: not all of the buffer is on 2 MiB pages; physical bits 12-20 are then unknown\n");

    int16_t *home = malloc(nlines * sizeof *home);
    if (!home)
        die("malloc");

    if (use_perf) {
        for (int m = 0; m < NMESH; m++) {
            snprintf(path, sizeof path, "/sys/bus/event_source/devices/arm_cmn_%d/type", m);
            pmu_type[m] = read_sysfs_int(path);
            snprintf(path, sizeof path, "/sys/bus/event_source/devices/arm_cmn_%d/cpumask", m);
            pmu_cpu[m] = read_sysfs_int(path);
            event_cfg[m] = event_config(m, event);
            fprintf(stderr, "arm_cmn_%d: perf type %d, cpu %d, %s config 0x%llx\n", m, pmu_type[m], pmu_cpu[m], event,
                    (unsigned long long)event_cfg[m]);
            discover(m);
        }
        for (int m = 0; m < NMESH; m++) {
            int found = 0;
            for (int k = 0; k < nnodes; k++)
                found += nodes[k].mesh == m;
            if (found != expect_nodes) {
                fprintf(stderr, "homelat: mesh %d has %d home nodes, expected %d (--expect-nodes)\n", m, found, expect_nodes);
                exit(2);
            }
        }
        decode_ids();
        /* probe on the PMU's own CPU: a counter read from any other CPU is an interrupt to it */
        if (pmu_cpu[0] != pmu_cpu[1])
            fprintf(stderr, "warning: the two mesh PMUs use different CPUs (%d, %d); probing on %d\n", pmu_cpu[0], pmu_cpu[1], pmu_cpu[0]);
        pin_cpu(pmu_cpu[0]);
        fprintf(stderr, "classification runs on CPU %d, %d loads per probe\n", pmu_cpu[0], probe_loads);
        double t0 = now_s();
        classify(buf, nlines, home, retries);
        fprintf(stderr, "classification took %.1f s\n", now_s() - t0);
        long unknown = 0;
        for (uint64_t i = 0; i < nlines; i++)
            unknown += home[i] < 0;
        if ((uint64_t)unknown > nlines / 20) {
            fprintf(stderr, "homelat: %.1f%% of the lines have no home: classification rejected (limit 5%%)\n", 100.0 * (double)unknown / (double)nlines);
            exit(2);
        }
        long control_false;
        double agree = verify_classification(buf, nlines, home, verify_sample, &control_false);
        if (agree < 0.98 || control_false > verify_sample / 100) {
            fprintf(stderr, "homelat: classification rejected (%.1f%% agreement, %ld control hits; limits 98%% and 1%%)\n", 100.0 * agree, control_false);
            exit(2);
        }
    } else {
        classify_fake(nlines, home);
    }

    fprintf(fnodes, "mesh,node_id_hex,x,y,port,dev,dtc,lines\n");
    for (int k = 0; k < nnodes; k++)
        fprintf(fnodes, "%d,0x%x,%d,%d,%d,%d,%d,%d\n", nodes[k].mesh, nodes[k].id, nodes[k].x, nodes[k].y, nodes[k].port,
                nodes[k].dev, nodes[k].dtc, nodes[k].nlines);
    fclose(fnodes);

    /* per 2 MiB chunk: physical frame and how its lines split over the two meshes */
    int pagemap = open("/proc/self/pagemap", O_RDONLY);
    fprintf(fchunks, "chunk,virt_hex,pfn_hex,contiguous,lines_mesh0,lines_mesh1,lines_unknown\n");
    for (uint64_t c = 0; c < bytes / HUGE_BYTES; c++) {
        long m0 = 0, m1 = 0, un = 0;
        for (uint64_t i = c * (HUGE_BYTES / LINE); i < (c + 1) * (HUGE_BYTES / LINE); i++) {
            if (home[i] < 0) un++;
            else if (nodes[home[i]].mesh == 0) m0++;
            else m1++;
        }
        uint64_t pfn = pagemap >= 0 ? pfn_of(pagemap, buf + c * HUGE_BYTES) : 0;
        int contiguous = pfn != 0;
        uint64_t pfn_last = pfn;
        for (uint64_t pg = 1; contiguous && pg < HUGE_BYTES / 4096; pg++) { /* every page (reviewer's request) */
            pfn_last = pfn_of(pagemap, buf + c * HUGE_BYTES + pg * 4096);
            contiguous = pfn_last == pfn + pg;
        }
        fprintf(fchunks, "%lu,0x%lx,0x%lx,%d,%ld,%ld,%ld\n", (unsigned long)c, (unsigned long)(uintptr_t)(buf + c * HUGE_BYTES),
                (unsigned long)pfn, contiguous, m0, m1, un);
        if (!contiguous)
            fprintf(stderr, "warning: chunk %lu is not one physically contiguous 2 MiB page (first pfn 0x%lx, last 0x%lx)\n",
                    (unsigned long)c, (unsigned long)pfn, (unsigned long)pfn_last);
    }
    fclose(fchunks);
    fprintf(fhomes, "line,mesh,node_id_hex\n");
    for (uint64_t i = 0; i < nlines; i++) {
        if (home[i] < 0)
            fprintf(fhomes, "%lu,-1,%d\n", (unsigned long)i, home[i]);
        else
            fprintf(fhomes, "%lu,%d,0x%x\n", (unsigned long)i, nodes[home[i]].mesh, nodes[home[i]].id);
    }
    fclose(fhomes);

    /* latency: from each core to each node, plus a mixed chain over all classified lines */
    uint32_t *mixed = malloc((size_t)lines_per_node * sizeof *mixed);
    if (!mixed)
        die("malloc");
    int nmixed = 0, per = lines_per_node / nnodes; /* the same number of lines from every node, without replacement */
    if (per < 1) per = 1;
    for (int k = 0; k < nnodes && nmixed < lines_per_node; k++) {
        /* partial Fisher-Yates over this node's line list: the first `take` entries are distinct */
        int take = per < nodes[k].nlines ? per : nodes[k].nlines;
        for (int j = 0; j < take; j++) {
            int r = j + (int)(xorshift64() % (uint64_t)(nodes[k].nlines - j));
            uint32_t tmp = nodes[k].lines[j]; nodes[k].lines[j] = nodes[k].lines[r]; nodes[k].lines[r] = tmp;
        }
        for (int j = 0; j < take && nmixed < lines_per_node; j++)
            mixed[nmixed++] = nodes[k].lines[j];
    }
    nmixed &= ~7;
    int short_nodes = 0;
    for (int k = 0; k < nnodes; k++)
        if (nodes[k].nlines < lines_per_node) {
            if (!short_nodes)
                fprintf(stderr, "coverage: nodes with fewer than %d lines:", lines_per_node);
            fprintf(stderr, " mesh%d/0x%x=%d", nodes[k].mesh, nodes[k].id, nodes[k].nlines);
            short_nodes++;
        }
    if (short_nodes)
        fprintf(stderr, "\ncoverage: %d of %d nodes are short; their rows use fewer lines or are missing (under 64)\n", short_nodes, nnodes);
    else
        fprintf(stderr, "coverage: every node has at least %d lines\n", lines_per_node);
    if (use_perf && verify_count > 0)
        verify_slices(buf, ev, cores[0], verify_count, lines_per_node, reps, out);
    fprintf(flat, "core,mesh,node_id_hex,x,y,dev,lines,ns_median,ns_min,ns_max");
    for (int r = 0; r < reps; r++)
        fprintf(flat, ",ns_rep%d", r + 1);
    fprintf(flat, "\n");
    double t0 = now_s();
    for (int ci = 0; ci < ncores; ci++) {
        int core = cores[ci];
        pin_cpu(core);
        double med, mn, mx, all[8];
        if (nmixed >= 64) {
            measure(buf, ev, mixed, nmixed, reps, &med, &mn, &mx, all);
            fprintf(flat, "%d,-1,mixed,-1,-1,-1,%d,%.2f,%.2f,%.2f", core, nmixed, med, mn, mx);
            for (int r = 0; r < reps; r++) fprintf(flat, ",%.2f", all[r]);
            fprintf(flat, "\n");
        }
        for (int k = 0; k < nnodes; k++) {
            int n = nodes[k].nlines < lines_per_node ? nodes[k].nlines & ~7 : lines_per_node;
            if (n < 64)
                continue;
            check_marker();
            measure(buf, ev, nodes[k].lines, n, reps, &med, &mn, &mx, all);
            fprintf(flat, "%d,%d,0x%x,%d,%d,%d,%d,%.2f,%.2f,%.2f", core, nodes[k].mesh, nodes[k].id, nodes[k].x, nodes[k].y,
                    nodes[k].dev, n, med, mn, mx);
            for (int r = 0; r < reps; r++) fprintf(flat, ",%.2f", all[r]);
            fprintf(flat, "\n");
        }
        fflush(flat);
        fprintf(stderr, "core %d done (%.0f s)\n", core, now_s() - t0);
    }
    fclose(flat);
    return 0;
}
