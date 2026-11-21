/*
 * meshmap.c - latency map of the Asimov mesh: the time of one load from each
 * CPU to each home node, for lines of the node's mesh cache and of its OCM.
 *
 * Words used here:
 *   home node   the mesh node that owns a line's address. Asimov has five. Each
 *               holds one slice of the mesh cache (SLC) and one on-chip memory
 *               (OCM) region. An OCM address selects its node by address range.
 *               A DRAM address selects its node by a hash of the line address.
 *   cell        one (kind, cpu, node): --reps timed passes of `lines` dependent
 *               loads, each pass over a different chain on the same lines.
 *   chain       the lines of a cell linked into one random cycle, as in
 *               latency.c. Chain r keeps its pointers in 8-byte slot r of each
 *               line, so a line carries up to seven chains (slots 0 to 6). Slot
 *               7 is the store target of the preload.
 *   probe       P times {DC CIVAC on one line, load it}, then one read of the
 *               mesh counters. The node whose request counter rose by about 2 P
 *               is the line's home node.
 *   classification  the probe of the buffer's lines in address order, until
 *               every node has `lines` lines.
 *   evictor     one load of every line of the buffer that is not in the cell's
 *               DRAM chain. The loads push the chain lines out of the cluster's
 *               caches, to the SLC slice of their home node.
 *   read floor  the counts that one read of the mesh counters adds by itself.
 *
 * Kinds of cell:
 *   ocm-flush   OCM lines of the node. Per pass: DC CIVAC on every chain line,
 *               DSB SY, timed chase. Needs no mesh counter.
 *   slc         DRAM-backed lines whose home node was found by classification.
 *               Per pass: store-preload, evictor, timed chase. The store makes
 *               the measuring cluster the only holder of the line and makes the
 *               line dirty, so the eviction writes it to the SLC slice.
 *   dram-flush  the same lines as slc, with the ocm-flush recipe: the load goes
 *               to the home node, misses, and is fetched from DRAM.
 *   ocm-evict   OCM lines of the node with the slc recipe (the control of the
 *               recipe on the other kind of line).
 *   idle        one bracket with zero loads per CPU: the background of the counters.
 * With --no-perf the DRAM kinds are named slc-fake and dram-flush-fake: the
 * homes are then line index mod number of nodes, not measured.
 *
 * Order of work: the parts most certain to work run first. The program runs
 * once per boot on an emulator, and a guard there can kill it without notice.
 * So every row is appended to --out and flushed immediately. No failure after
 * the command line is read ends the process: a failing part prints a '#' line
 * and the rest still runs.
 *   A  preflight: test-pin every CPU, one 2 MiB buffer, map the OCM regions,
 *      whether the buffer is one physical 2 MiB page, page frame number, core
 *      counters, bracket overhead
 *   B  ocm-flush cells (no mesh counter is open: the mesh columns print "-")
 *   C  mesh counters: one group with the per-node event and three sums, else
 *      one group with the per-node events, else each per-node event alone
 *   D  read floor, then the classification of the DRAM lines
 *   E  idle rows and slc cells, then dram-flush cells, then ocm-evict cells
 *   F  the --last-cpus block (meant for CPU 0, the kernel's CPU)
 *   G  "# meshmap: done cells=<printed>/<requested>"; exit 0 when the two are
 *      equal and no write to the row file or to the --homes file failed, else 1
 *
 * Requested cells: per CPU and node the two DRAM kinds, and the two OCM kinds
 * when the node has an OCM region. OCM region i belongs to one fixed node id
 * (regions 0..4 = nodes 88, 160, 216, 288, 344). A node id of --nodes outside
 * these five has no OCM cells, and none is counted as requested for it.
 *
 * A failed write, flush or close of the row file or of the --homes file is
 * reported once per file on stderr. The measurement still runs to its end.
 *
 * Output: one CSV row per timed pass. Core counter columns are per load as in
 * latency.c. Mesh columns are counts per load of the timed bracket ("-" when
 * the counter is not open or did not run for the whole bracket). The node's
 * read floor is subtracted from the req_<id> columns only. The three sums
 * (mc_reqs, cache_miss, snp_sent) carry no floor. An idle row has lines = 0
 * and raw counts with no floor in any column. The program applies no reading
 * rule and drops no row.
 */
#include "common.h"
#include <dirent.h>
#include <stdarg.h>
#include <sys/stat.h>

/* 32,768 lines: 2 MiB of virtual addresses. Never more. The bound "at most 8 lines of one node share an
 * SLC set (12 DRAM ways)" holds only when the buffer is one physical 2 MiB page. The row file says so
 * in its "# one_2mib_page:" line (see check_one_page). Without "yes" there, the bound is not known. */
#define NBUF ((uint32_t)(HUGE_BYTES / LINE_BYTES))
#define MAX_NODES 8
#define MAX_LINES 4096
#define MAX_CPUS 64
#define N_SUMS 3
#define MESH_MAX (MAX_NODES + N_SUMS) /* event i < MAX_NODES: the per-node event on node i; MAX_NODES + j: sum j */
#define STORE_SLOT 7                  /* the preload stores here; the chains use slots 0 to 6 */
#define NAME_LEN 64

static struct {
    long cpus[MAX_CPUS], last[MAX_CPUS], nodes[MAX_NODES];
    int ncpus, nlast, nnodes;
    const char *cpus_arg, *last_arg, *nodes_arg;
    const char *pmu, *sysfs, *event, *out_path, *homes_path;
    uint64_t lines;
    int reps, warm, probe_loads, no_perf, no_ocm;
    double max_classify_s;
} cfg = {
    .cpus_arg = "2,4,6,8,3,5,7,9", .last_arg = "", .nodes_arg = "88,160,216,288,344",
    .pmu = "arm_cmn_0", .sysfs = "/sys/bus/event_source/devices", .event = "hns_pocq_reqs_recvd_all",
    .lines = 2048, .reps = 7, .warm = 2, .probe_loads = 64, .max_classify_s = 1.0,
};

static FILE *out;     /* rows and '#' lines: --out FILE (appended) or stdout */
static int quiet;     /* the self-test runs without the '#' lines and without the stderr line of a failed write */
static double t_main; /* set at the entry of main */
static int out_failed;   /* an open, write, flush or close of the row file failed */
static int homes_failed; /* the same for the --homes file */

/* Records a failure of one output file; the caller's errno says why. Only the first failure of a file
 * is reported on stderr. The measurement goes on, and main exits nonzero at its end. */
static void write_failed(int *failed, const char *path)
{
    int err = errno;
    if (!*failed && !quiet)
        fprintf(stderr, "meshmap: write to %s failed (%s)\n", path, strerror(err));
    *failed = 1;
    errno = err;
}

/* Flushes the row file. Records a failure of the flush or of a write to the file before it. */
static void out_flush(void)
{
    if (fflush(out) != 0 || ferror(out))
        write_failed(&out_failed, out == stdout ? "stdout" : cfg.out_path);
}

/* Flushes and closes f. Records a failure of either, or of a write to f before them. */
static void close_checked(FILE *f, int *failed, const char *path)
{
    if (fflush(f) != 0 || ferror(f))
        write_failed(failed, path);
    if (fclose(f) != 0)
        write_failed(failed, path);
}

/* The exit status of main: 0 only when every requested cell was printed and no output file failed. */
static int exit_status(int printed, int requested)
{
    return printed == requested && !out_failed && !homes_failed ? 0 : 1;
}

/* One '#' line to the row file, flushed immediately: a line still in the stdio buffer is lost when
 * the guard kills the process. */
__attribute__((format(printf, 1, 2))) static void note(const char *fmt, ...)
{
    va_list ap;
    if (quiet)
        return;
    va_start(ap, fmt);
    vfprintf(out, fmt, ap);
    va_end(ap);
    fputc('\n', out);
    out_flush();
}

/* One progress or summary line to stdout, flushed immediately. */
__attribute__((format(printf, 1, 2))) static void say(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    putchar('\n');
    fflush(stdout);
}

static void progress(const char *what)
{
    say("# progress: t=%.4fs %s", now_s() - t_main, what);
}

/* "3 2 4" or "3,2,4" in buf. */
static const char *list_text(char *buf, size_t size, const int64_t *v, int n, char sep)
{
    const char s[2] = { sep, '\0' };
    size_t len = 0;
    buf[0] = '\0';
    for (int i = 0; i < n && len < size; i++)
        len += (size_t)snprintf(buf + len, size - len, "%s%lld", i ? s : "", (long long)v[i]);
    return buf;
}

/* As common.h pin_cpu, but returns the failure (errno set) instead of ending the process. */
static int try_pin(long cpu)
{
    cpu_set_t set;
    CPU_ZERO(&set);
    if (cpu >= 0 && cpu < CPU_SETSIZE)
        CPU_SET((int)cpu, &set);
    return sched_setaffinity(0, sizeof set, &set);
}

static void *volatile sink;
static uint64_t rng_state;

static uint64_t xorshift64(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}

static void shuffle16(uint16_t *p, uint32_t n)
{
    for (uint32_t i = n; i > 1; i--) {
        uint32_t j = (uint32_t)(xorshift64() % i);
        uint16_t tmp = p[i - 1];
        p[i - 1] = p[j];
        p[j] = tmp;
    }
}

/* A new visiting order of n elements without a new shuffle: index (a + i * s) mod n for i = 0..n-1,
 * with a random start a and a random step s that shares no factor with n, so every index comes up
 * exactly once. The caller reads one fixed random permutation through it. */
struct order {
    uint32_t n, j, s;
};

static uint32_t gcd32(uint32_t a, uint32_t b)
{
    while (b) {
        uint32_t t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static struct order new_order(uint32_t n)
{
    struct order o = { n, 0, 0 };
    if (n < 2)
        return o;
    o.j = (uint32_t)(xorshift64() % n);
    do
        o.s = 1 + (uint32_t)(xorshift64() % (n - 1));
    while (gcd32(o.s, n) != 1);
    return o;
}

static inline uint32_t order_next(struct order *o)
{
    uint32_t j = o->j;
    o->j += o->s;
    if (o->j >= o->n)
        o->j -= o->n;
    return j;
}

/* Chain `slot` over the n lines of line[]: one random cycle by Sattolo's algorithm, the method of
 * latency.c build_cycle. First the identity, then the shuffle of the indices, then index -> address.
 * The pointer in slot `slot` of a line targets the same slot of the next line. */
static void build_chain(uint8_t *const *line, uint64_t n, int slot, uint64_t seed)
{
#define AT(i) (*(uint64_t *)(line[i] + (slot) * 8))
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
        AT(i) = (uint64_t)(uintptr_t)(line[AT(i)] + slot * 8);
#undef AT
}

/* A different nonzero seed per (kind, node, cpu, rep); each field stays below 16 bits. */
static uint64_t chain_seed(int kind, int node, long cpu, int rep)
{
    return (((uint64_t)(kind + 1) << 48) ^ ((uint64_t)(node + 1) << 32) ^ ((uint64_t)(cpu + 1) << 16) ^ (uint64_t)(rep + 1)) *
           0x9E3779B97F4A7C15ULL;
}

/* The same routine as latency.c chase (8 dependent loads per loop iteration, then a tail), without
 * the CME branch. */
__attribute__((noinline)) static void *chase(void *p, uint64_t loads)
{
    if (loads == 0)
        return p;
    uint64_t i = 0;
    for (; i + 8 <= loads; i += 8) {
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
        p = *(void **)p;
    }
    for (; i < loads; i++)
        p = *(void **)p;
    return p;
}

/* DC CIVAC: clean and invalidate one line from every core cache. DSB SY: wait until it is done.
 * Both are AArch64 instructions; a host build does nothing here, as common.h flush_buf. */
static inline void civac(const uint8_t *p)
{
#if defined(__aarch64__)
    __asm__ volatile("dc civac, %0" : : "r"(p) : "memory");
#else
    (void)p;
#endif
}

static inline void dsb_sy(void)
{
#if defined(__aarch64__)
    __asm__ volatile("dsb sy" : : : "memory");
#endif
}

/* ---- mesh counters (the arm_cmn PMU) ---- */

static struct {
    int level;        /* 0: none open. 1: one group, the per-node events and the sums. 2: one group, the
                         per-node events only. 3: the per-node events, each opened and read alone. */
    int fd[MESH_MAX]; /* -1 when not open */
    int pos[MESH_MAX]; /* position of the event in the group read (the open events in open order), or -1 */
    int n;            /* events open */
    unsigned type;    /* the PMU's perf type number */
    int cpu;          /* the PMU's own CPU (sysfs cpumask) */
    uint64_t config[MESH_MAX][3];
    int built[MESH_MAX];             /* the event's config was built from sysfs */
    char sum_name[N_SUMS][NAME_LEN]; /* the sysfs names of the sums */
    int64_t floor[MAX_NODES];        /* read floor per node: subtracted from a probe's changes and from the req columns of a measured row */
} mesh;

static char pmu_dir[512]; /* <--sysfs>/<--pmu> */
static char why[512];     /* the reason of the last mesh counter failure */

/* The next three functions are a copy of the sysfs config builder of cmncount.c (read_text, set_field,
 * build_event). Two changes: a failure writes its reason to `why` instead of stderr, and the config
 * words and the node id are arguments. cmncount.c stays as it is, since the counted rows of ten boots
 * come from it. The two copies are to be merged later. */
static int read_text(const char *path, char *buf, size_t n)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0)
        return -1;
    ssize_t r = read(fd, buf, n - 1);
    close(fd);
    if (r < 0)
        return -1;
    buf[r] = '\0';
    while (r > 0 && (buf[r - 1] == '\n' || buf[r - 1] == ' '))
        buf[--r] = '\0';
    return (int)r;
}

/* format/<field> holds "config:16-26", "config1:0-63" or "config:31". */
static int set_field(uint64_t config[3], const char *field, uint64_t val)
{
    char path[1024], spec[64];
    snprintf(path, sizeof path, "%s/format/%.63s", pmu_dir, field);
    if (read_text(path, spec, sizeof spec) < 0) {
        snprintf(why, sizeof why, "no format/%.63s in %.300s", field, pmu_dir);
        return -1;
    }
    int which;
    if (!strncmp(spec, "config2:", 8)) which = 2;
    else if (!strncmp(spec, "config1:", 8)) which = 1;
    else if (!strncmp(spec, "config:", 7)) which = 0;
    else {
        snprintf(why, sizeof why, "bad format %.63s: %s", field, spec);
        return -1;
    }
    const char *bits = strchr(spec, ':') + 1;
    char *end;
    long lo = strtol(bits, &end, 10), hi = lo;
    if (*end == '-')
        hi = strtol(end + 1, &end, 10);
    if (*end != '\0' || lo < 0 || hi < lo || hi > 63) {
        snprintf(why, sizeof why, "bad bit range %.63s: %s", field, spec);
        return -1;
    }
    uint64_t width = (uint64_t)(hi - lo + 1);
    uint64_t mask = width == 64 ? ~0ULL : ((1ULL << width) - 1);
    if (val & ~mask) {
        snprintf(why, sizeof why, "value 0x%llx does not fit %.63s (%s)", (unsigned long long)val, field, spec);
        return -1;
    }
    config[which] |= (val & mask) << lo;
    return 0;
}

/* events/<name> holds "type=0x200,eventid=0x5,occupid=0x0". nodeid >= 0 counts on that node only
 * (bynodeid=1, nodeid=id); nodeid -1 sums over every node of the event's type. */
static int build_event(uint64_t config[3], const char *name, long nodeid)
{
    char path[1024], desc[256];
    config[0] = config[1] = config[2] = 0;
    snprintf(path, sizeof path, "%s/events/%.63s", pmu_dir, name);
    if (read_text(path, desc, sizeof desc) < 0) {
        snprintf(why, sizeof why, "unknown event %.63s (no %.400s)", name, path);
        return -1;
    }
    for (char *tok = strtok(desc, ","); tok; tok = strtok(NULL, ",")) {
        char *eq = strchr(tok, '=');
        if (!eq) {
            snprintf(why, sizeof why, "bad event text %.63s: %s", name, tok);
            return -1;
        }
        *eq = '\0';
        if (set_field(config, tok, strtoull(eq + 1, NULL, 0)) < 0)
            return -1;
    }
    if (nodeid >= 0) {
        if (set_field(config, "bynodeid", 1) < 0 || set_field(config, "nodeid", (uint64_t)nodeid) < 0)
            return -1;
    }
    return 0;
}

/* The sysfs name of a sum: `want` itself when events/<want> exists, else the first event whose name
 * starts with `want`, else "". */
static void find_event(const char *want, char name[NAME_LEN])
{
    char path[1024];
    name[0] = '\0';
    snprintf(path, sizeof path, "%s/events/%.63s", pmu_dir, want);
    if (access(path, R_OK) == 0) {
        snprintf(name, NAME_LEN, "%.63s", want);
        return;
    }
    snprintf(path, sizeof path, "%s/events", pmu_dir);
    DIR *d = opendir(path);
    if (!d)
        return;
    for (struct dirent *e = readdir(d); e; e = readdir(d))
        if (!strncmp(e->d_name, want, strlen(want)) && strlen(e->d_name) < NAME_LEN) {
            snprintf(name, NAME_LEN, "%.63s", e->d_name);
            break;
        }
    closedir(d);
}

/* Reads the PMU's type and CPU and builds every event's config. Returns -1 with `why` set when the
 * PMU or the per-node event is missing. A missing sum is dropped (its column prints "-"). */
static int mesh_configs(void)
{
    static const char *want[N_SUMS] = { "hns_mc_reqs_local_all", "hns_cache_miss_all", "hns_snp_sent" };
    char text[64], path[1024];
    snprintf(pmu_dir, sizeof pmu_dir, "%s/%s", cfg.sysfs, cfg.pmu);
    snprintf(path, sizeof path, "%s/type", pmu_dir);
    if (read_text(path, text, sizeof text) < 0) {
        snprintf(why, sizeof why, "%.63s absent (no %.400s)", cfg.pmu, path);
        return -1;
    }
    mesh.type = (unsigned)strtoul(text, NULL, 0);
    snprintf(path, sizeof path, "%s/cpumask", pmu_dir);
    mesh.cpu = 0;
    if (read_text(path, text, sizeof text) >= 0)
        mesh.cpu = (int)strtol(text, NULL, 10); /* first cpu of "0" or "0-1" */
    for (int i = 0; i < cfg.nnodes; i++) {
        if (build_event(mesh.config[i], cfg.event, cfg.nodes[i]) < 0)
            return -1;
        mesh.built[i] = 1;
    }
    for (int j = 0; j < N_SUMS; j++) {
        find_event(want[j], mesh.sum_name[j]);
        if (!mesh.sum_name[j][0])
            snprintf(why, sizeof why, "no event named %s* in %.300s", want[j], pmu_dir);
        mesh.built[MAX_NODES + j] = mesh.sum_name[j][0] && build_event(mesh.config[MAX_NODES + j], mesh.sum_name[j], -1) == 0;
        if (!mesh.built[MAX_NODES + j])
            note("# meshmap: optional mesh event %s dropped (%s)", want[j], why);
    }
    return 0;
}

static void mesh_close(void)
{
    for (int i = 0; i < MESH_MAX; i++) {
        if (mesh.level && mesh.fd[i] >= 0)
            close(mesh.fd[i]);
        mesh.fd[i] = mesh.pos[i] = -1;
    }
    mesh.n = 0;
    mesh.level = 0;
}

/* Rules of the arm-cmn driver, as cmncount.c: system-wide (pid -1) on the PMU's own CPU, no exclude
 * bit. A group leader or a lone event starts disabled and is enabled once every event is open. A
 * lone event is opened exactly as cmncount.c opens it (the form that ran on every boot so far). */
static int mesh_open_one(const uint64_t config[3], int group_fd, int grouped)
{
    struct perf_event_attr a;
    memset(&a, 0, sizeof a);
    a.size = sizeof a;
    a.type = mesh.type;
    a.config = config[0];
    a.config1 = config[1];
    a.config2 = config[2];
    a.disabled = group_fd < 0;
    a.read_format = PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING | (grouped ? PERF_FORMAT_GROUP : 0);
    return (int)syscall(__NR_perf_event_open, &a, -1, mesh.cpu, group_fd, PERF_FLAG_FD_CLOEXEC);
}

/* One read of every open mesh event. v[i] is the lifetime count of event i; en and run are the
 * enabled and running times in ns (summed over the events at level 3). ok = 0 when a read failed. */
struct msample {
    uint64_t v[MESH_MAX], en, run;
    int ok;
};

static void mesh_read(struct msample *s)
{
    memset(s, 0, sizeof *s);
    if (mesh.level == 0)
        return;
    if (mesh.level < 3) {
        uint64_t b[3 + MESH_MAX]; /* nr, time_enabled, time_running, then one value per open event in open order */
        size_t want = sizeof(uint64_t) * (3 + (size_t)mesh.n);
        if (read(mesh.fd[0], b, want) != (ssize_t)want || b[0] != (uint64_t)mesh.n)
            return;
        s->en = b[1];
        s->run = b[2];
        for (int i = 0; i < MESH_MAX; i++)
            if (mesh.pos[i] >= 0)
                s->v[i] = b[3 + mesh.pos[i]];
    } else {
        for (int i = 0; i < cfg.nnodes; i++) {
            uint64_t b[3]; /* value, time_enabled, time_running */
            if (read(mesh.fd[i], b, sizeof b) != (ssize_t)sizeof b)
                return;
            s->v[i] = b[0];
            s->en += b[1];
            s->run += b[2];
        }
    }
    s->ok = 1;
}

/* The change between two reads, as signed 64-bit counts. Returns 1 when the window is valid: both
 * reads worked and the events ran for the whole time they were enabled (no multiplexing, and the
 * driver gave every event a counter). */
static int mesh_delta(const struct msample *a, const struct msample *b, int64_t d[MESH_MAX])
{
    for (int i = 0; i < MESH_MAX; i++)
        d[i] = (int64_t)(b->v[i] - a->v[i]);
    uint64_t en = b->en - a->en, run = b->run - a->run;
    return a->ok && b->ok && run > 0 && run == en;
}

/* Opens the events of one level, enables them and checks one idle window (read, read). Returns -1
 * with `why` set and everything closed when the level does not work. */
static int mesh_open(int level)
{
    int grouped = level < 3;
    mesh_close();
    mesh.level = level; /* from here mesh_close closes what is open */
    for (int i = 0; i < cfg.nnodes; i++) {
        mesh.fd[i] = mesh_open_one(mesh.config[i], grouped && i ? mesh.fd[0] : -1, grouped);
        if (mesh.fd[i] < 0) {
            snprintf(why, sizeof why, "level %d: open %.63s on node %ld: %s", level, cfg.event, cfg.nodes[i], strerror(errno));
            mesh_close();
            return -1;
        }
        mesh.pos[i] = mesh.n++;
    }
    for (int j = 0; level == 1 && j < N_SUMS; j++) {
        int i = MAX_NODES + j;
        if (!mesh.built[i])
            continue;
        mesh.fd[i] = mesh_open_one(mesh.config[i], mesh.fd[0], 1);
        if (mesh.fd[i] < 0) {
            note("# meshmap: optional mesh event %s not opened (%s)", mesh.sum_name[j], strerror(errno));
            continue;
        }
        mesh.pos[i] = mesh.n++;
    }
    int err = 0;
    if (grouped) {
        if (ioctl(mesh.fd[0], PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP) != 0)
            err = errno;
    } else {
        for (int i = 0; i < cfg.nnodes; i++)
            if (ioctl(mesh.fd[i], PERF_EVENT_IOC_ENABLE, 0) != 0)
                err = errno;
    }
    if (err) {
        snprintf(why, sizeof why, "level %d: enable: %s", level, strerror(err));
        mesh_close();
        return -1;
    }
    struct msample a, b;
    int64_t d[MESH_MAX];
    mesh_read(&a);
    mesh_read(&b);
    if (!mesh_delta(&a, &b, d)) {
        snprintf(why, sizeof why, "level %d: idle window read_ok=%d,%d enabled_ns=%llu running_ns=%llu", level, a.ok, b.ok,
                 (unsigned long long)(b.en - a.en), (unsigned long long)(b.run - a.run));
        mesh_close();
        return -1;
    }
    return 0;
}

/* The read floor: 64 empty windows (read, read). The per-node median is what one read adds to the
 * node's counter when the program does nothing else. */
static void mesh_floor(void)
{
    static int64_t w[MAX_NODES][64];
    struct msample a, b;
    int64_t d[MESH_MAX];
    char text[256];
    int n = 0;
    mesh_read(&a);
    for (int i = 0; i < 64; i++) {
        mesh_read(&b);
        if (mesh_delta(&a, &b, d)) {
            for (int k = 0; k < cfg.nnodes; k++)
                w[k][n] = d[k];
            n++;
        }
        a = b;
    }
    for (int k = 0; k < cfg.nnodes; k++) {
        for (int i = 1; i < n; i++) /* insertion sort, 64 values */
            for (int j = i; j > 0 && w[k][j - 1] > w[k][j]; j--) { int64_t x = w[k][j]; w[k][j] = w[k][j - 1]; w[k][j - 1] = x; }
        mesh.floor[k] = n ? w[k][n / 2] : 0;
    }
    note("# read_floor: %s", list_text(text, sizeof text, mesh.floor, cfg.nnodes, ' '));
    if (n < 64)
        note("# meshmap: read floor from %d of 64 windows (in the others the counters did not run the whole time)", n);
}

/* Section C of the order of work: configs, then level 1, 2, 3. Returns 1 when counters are open. */
static int mesh_start(void)
{
    char names[512];
    mesh_close();
    if (mesh_configs() < 0) {
        note("# meshmap: no mesh counters (%s)", why);
        return 0;
    }
    for (int level = 1; level <= 3; level++) {
        if (mesh_open(level) == 0)
            break;
        note("# meshmap: mesh counters %s", why);
    }
    if (!mesh.level) {
        note("# meshmap: no mesh counters (%s)", why);
        return 0;
    }
    size_t len = (size_t)snprintf(names, sizeof names, "%.63s", cfg.event);
    for (int j = 0; j < N_SUMS; j++)
        if (mesh.pos[MAX_NODES + j] >= 0)
            len += (size_t)snprintf(names + len, sizeof names - len, ",%s", mesh.sum_name[j]);
    note("# mesh counters: level=%d events=%s pmu_cpu=%d", mesh.level, names, mesh.cpu);
    return 1;
}

/* ---- core counters and the timed bracket ---- */

static struct perfgrp pg;
static struct buf dram;
static uint8_t *ocm_base[MAX_NODES];

struct bracket {
    double ns;        /* between the two clock reads around the chase */
    double window_ns; /* between the two mesh reads */
    uint64_t c[PERF_N];
    int cvalid;       /* the core counters ran for the whole chase */
    const char *cwhy;
    double cov;       /* core counters: time running / time enabled */
    int64_t d[MESH_MAX];
    int mvalid;       /* the mesh counters ran for the whole window */
};

/* Mesh read, core counters start, clock, chase, clock, core counters stop, mesh read. */
static void bracket(void *start, uint64_t loads, struct bracket *b)
{
    struct msample m0, m1;
    mesh_read(&m0);
    double w0 = now_s();
    perf_start(&pg);
    double t0 = now_s();
    void *q = chase(start, loads);
    double t1 = now_s();
    perf_stop(&pg);
    mesh_read(&m1);
    double w1 = now_s();
    sink = q;
    b->ns = (t1 - t0) * 1e9;
    b->window_ns = (w1 - w0) * 1e9;
    b->cvalid = perf_read(&pg, b->c, &b->cwhy);
    b->cov = b->cvalid ? (double)pg.t_running / (double)pg.t_enabled : 0;
    b->mvalid = mesh_delta(&m0, &m1, b->d);
}

/* One per-load counter value as a CSV field, by the rule of common.h print_rate (which prints to
 * stdout only): "%.4f", or "%.3e" for a nonzero count that "%.4f" would print as 0.0000. */
static void put_rate(uint64_t count, uint64_t per)
{
    double v = (double)count / (double)per;
    if (count != 0 && v < 0.00005)
        fprintf(out, ",%.3e", v);
    else
        fprintf(out, ",%.4f", v);
}

/* One CSV row, flushed immediately. k is the node's index, or -1 for an idle row. */
static void print_row(const char *kind, long cpu, int k, uint64_t lines, int rep, const struct bracket *b)
{
    uint64_t per = lines ? lines : 1; /* an idle row has no loads: its counts are printed raw */
    fprintf(out, "%s,%ld,", kind, cpu);
    if (k >= 0) fprintf(out, "%ld", cfg.nodes[k]);
    else fprintf(out, "-");
    fprintf(out, ",%llu,%d", (unsigned long long)lines, rep);
    if (lines) fprintf(out, ",%.3f", b->ns / (double)lines);
    else fprintf(out, ",-");
    if (b->cvalid) {
        fprintf(out, ",%.2f", (double)b->c[0] / (double)per);
        for (int i = 1; i < PERF_N; i++) {
            if (perf_have(&pg, i)) put_rate(b->c[i], per);
            else fprintf(out, ",-"); /* an optional event this kernel refused to open */
        }
        fprintf(out, ",%.4f", b->cov);
    } else {
        for (int i = 0; i <= PERF_N; i++)
            fprintf(out, ",-");
    }
    for (int i = 0; i < cfg.nnodes; i++) { /* req_<id>: less the node's read floor, except in an idle row */
        if (b->mvalid) fprintf(out, ",%.4f", (double)(b->d[i] - (lines ? mesh.floor[i] : 0)) / (double)per);
        else fprintf(out, ",-");
    }
    for (int i = MAX_NODES; i < MESH_MAX; i++) { /* the three sums: no floor */
        if (b->mvalid && mesh.pos[i] >= 0) fprintf(out, ",%.4f", (double)b->d[i] / (double)per);
        else fprintf(out, ",-");
    }
    fprintf(out, ",%.0f\n", b->window_ns);
    if (pg.ok && !b->cvalid)
        fprintf(out, "# perf: counters of the row above are invalid: %s\n", b->cwhy);
    out_flush();
}

/* The fixed cost of one bracket with no loads, as latency.c prints it. Median of 32. */
static void print_bracket_overhead(void)
{
    double t[32];
    struct bracket b;
    for (int i = 0; i < 32; i++) {
        bracket(NULL, 0, &b);
        t[i] = b.ns;
    }
    for (int i = 1; i < 32; i++) /* insertion sort, 32 values */
        for (int j = i; j > 0 && t[j - 1] > t[j]; j--) { double x = t[j]; t[j] = t[j - 1]; t[j - 1] = x; }
    note("# bracket_overhead_ns=%.1f (median of 32 empty brackets: the two clock reads and a chase call with zero loads)", t[16]);
}

/* ---- classification of the DRAM lines ---- */

#define HOME_NONE (-1)   /* not probed */
#define HOME_UNUSED (-2) /* ambiguous three times: left out of every chain */
static int8_t home[NBUF]; /* per buffer line: the index of its home node, or one of the two values above */
static uint16_t dline[MAX_NODES][MAX_LINES]; /* per node: its first `lines` buffer lines in address order (the DRAM chain lines) */
static struct {
    uint32_t probed;    /* lines walked, from line 0 */
    uint32_t ambiguous; /* probes without a clear home (a line is probed up to 3 times) */
    uint32_t unused;    /* lines left unused */
    uint32_t count[MAX_NODES];
    uint64_t lines;     /* lines per node: first the target of the walk, at the end the result (0: failed) */
    int loads;          /* flush-and-load pairs per probe, after any doubling */
} cls;

/* The decision rule on the changes d[] of one probe of `loads` flush-and-load pairs, less the read
 * floor fl[]: the winner w is the largest. It is the home when w >= 3/4 of loads and no other node
 * has more than w / 4. Returns the winner's index, or -1 (ambiguous; a tie is ambiguous). */
static int decide(const int64_t *d, const int64_t *fl, int n, int64_t loads)
{
    int wi = 0;
    for (int i = 1; i < n; i++)
        if (d[i] - fl[i] > d[wi] - fl[wi])
            wi = i;
    int64_t w = d[wi] - fl[wi];
    if (4 * w < 3 * loads)
        return -1;
    for (int i = 0; i < n; i++)
        if (i != wi && 4 * (d[i] - fl[i]) > w)
            return -1;
    return wi;
}

/* The largest of {requested, 1024, 512, 256}, not above the request, whose projected classification
 * time fits the budget. Projected time = mean probe time x probes needed (5/4 x nodes x lines). When
 * none fits, the smallest of them. */
static uint64_t lines_for_budget(uint64_t requested, double probe_ns, int nnodes, double budget_s)
{
    const uint64_t cand[4] = { requested, 1024, 512, 256 };
    uint64_t pick = requested;
    for (int i = 0; i < 4; i++) {
        if (cand[i] > requested)
            continue;
        pick = cand[i];
        if (probe_ns * 1e-9 * 1.25 * nnodes * (double)pick <= budget_s)
            break;
    }
    return pick;
}

/* The lines per node that every node reaches: `lines` itself when the smallest count reaches it,
 * else the largest of {2048, 1024, 512, 256, 64} below `lines` that the smallest count reaches,
 * else 0 (a node has fewer than 64 lines: the classification failed). */
static uint64_t lines_for_counts(const uint32_t *count, int nnodes, uint64_t lines)
{
    static const uint64_t step[5] = { 2048, 1024, 512, 256, 64 };
    uint64_t min = count[0];
    for (int k = 1; k < nnodes; k++)
        if (count[k] < min)
            min = count[k];
    if (min >= lines)
        return lines;
    for (int i = 0; i < 5; i++)
        if (step[i] < lines && step[i] <= min)
            return step[i];
    return 0;
}

/* A probe fills the raw changes d[] of the mesh counters, sets *valid and returns its time in ns. */
typedef double (*probe_fn)(uint32_t line, int loads, int64_t d[MESH_MAX], int *valid);

static struct msample probe_prev; /* the read that ended the previous probe */

/* Loads both neighbour lines first (when inside the buffer): they are then resident, so a next-line
 * prefetch started by the probe's loads adds no mesh request. Then `loads` times {DC CIVAC, DSB SY,
 * load}, then ONE counter read. The change is this read minus the previous probe's read. */
static double probe_real(uint32_t line, int loads, int64_t d[MESH_MAX], int *valid)
{
    double t0 = now_s();
    const uint8_t *p = line_addr(&dram, line);
    uint64_t sum = 0;
    struct msample s;
    if (line > 0)
        sum += *(const volatile uint64_t *)(p - LINE_BYTES);
    if (line + 1 < NBUF)
        sum += *(const volatile uint64_t *)(p + LINE_BYTES);
    for (int i = 0; i < loads; i++) {
        civac(p);
        dsb_sy();
        sum += *(const volatile uint64_t *)p;
    }
    sink = (void *)(uintptr_t)sum;
    mesh_read(&s);
    *valid = mesh_delta(&probe_prev, &s, d);
    probe_prev = s;
    return (now_s() - t0) * 1e9;
}

/* --no-perf: no counter is read. The fake home of a line is its index mod the number of nodes. */
static double probe_fake(uint32_t line, int loads, int64_t d[MESH_MAX], int *valid)
{
    memset(d, 0, sizeof(int64_t) * MESH_MAX);
    d[line % (uint32_t)cfg.nnodes] = 2 * (int64_t)loads;
    *valid = 1;
    return 0;
}

/* One walk of the buffer at `loads` pairs per probe. Returns 1 when more than 1/4 of its first 256
 * probes were ambiguous and the pairs can still be doubled (the caller restarts), else 0. */
static int classify_round(probe_fn probe, int loads, double t0)
{
    uint32_t nprobe = 0;
    int bad = 0; /* counter windows in a row that were not valid */
    double ns32 = 0;
    char text[256];
    memset(home, HOME_NONE, sizeof home);
    memset(&cls, 0, sizeof cls);
    cls.loads = loads;
    cls.lines = cfg.lines;
    if (probe == probe_real)
        mesh_read(&probe_prev); /* the read before the first probe: the first touch of home[] and a restart's '#' line stay out of its window */
    for (uint32_t line = 0; line < NBUF; line++) {
        uint32_t min = cls.count[0];
        for (int k = 1; k < cfg.nnodes; k++)
            if (cls.count[k] < min)
                min = cls.count[k];
        if (min >= cls.lines)
            break; /* every node has its lines */
        if (now_s() - t0 > 2 * cfg.max_classify_s) { /* a hard stop, so a slow or failing classification cannot use up the boot */
            note("# classify: stopped at line=%u: twice --max-classify-s used", line);
            break;
        }
        int h = -1;
        for (int try = 0; try < 3 && h < 0; try++) {
            int64_t d[MESH_MAX];
            int valid;
            double ns = probe(line, loads, d, &valid);
            h = valid ? decide(d, mesh.floor, cfg.nnodes, loads) : -1;
            bad = valid ? 0 : bad + 1;
            nprobe++;
            cls.ambiguous += h < 0;
            int printed = nprobe <= 32 || (h < 0 && cls.ambiguous <= 32); /* the record that explains a failed classification */
            if (printed)
                note("# probe line=%u ns=%.0f d=%s home=%c%s", line, ns, list_text(text, sizeof text, d, cfg.nnodes, ','),
                     h < 0 ? '?' : '0' + h, valid ? "" : " (counters did not run the whole window)");
            if (nprobe <= 32)
                ns32 += ns;
            if (nprobe == 32) {
                cls.lines = lines_for_budget(cfg.lines, ns32 / 32, cfg.nnodes, cfg.max_classify_s);
                note("# classify: probe_ns=%.0f lines=%llu projected_s=%.4f", ns32 / 32, (unsigned long long)cls.lines,
                     ns32 / 32 * 1e-9 * 1.25 * cfg.nnodes * (double)cls.lines);
            }
            if (printed && probe == probe_real)
                mesh_read(&probe_prev); /* a printed line is a write call: its mesh requests stay out of the next probe */
            if (nprobe == 256 && cls.ambiguous > 64 && loads < 256)
                return 1;
            if (bad == 64 || (nprobe == 256 && cls.ambiguous == 256)) { /* this classification cannot work: do not walk the whole buffer */
                note("# classify: stopped at line=%u: %s", line,
                     bad == 64 ? "64 counter windows in a row were not valid" : "none of the first 256 probes gave a clear home");
                return 0;
            }
        }
        home[line] = (int8_t)(h < 0 ? HOME_UNUSED : h);
        if (h < 0) cls.unused++;
        else cls.count[h]++;
        cls.probed = line + 1;
    }
    return 0;
}

/* Section D of the order of work. Fills home[], cls and dline[]. Returns the lines per node, or 0
 * when a node has fewer than 64 lines. */
static uint64_t classify(probe_fn probe)
{
    double t0 = now_s();
    int loads = cfg.probe_loads;
    int64_t c[MAX_NODES];
    uint32_t have[MAX_NODES] = { 0 };
    char text[256];
    while (classify_round(probe, loads, t0)) {
        loads *= 2;
        note("# classify: %u of the first 256 probes were ambiguous: probe_loads doubled to %d, restart from line 0", cls.ambiguous, loads);
    }
    cls.lines = lines_for_counts(cls.count, cfg.nnodes, cls.lines);
    for (int k = 0; k < cfg.nnodes; k++)
        c[k] = cls.count[k];
    list_text(text, sizeof text, c, cfg.nnodes, ',');
    note("# classify: probed=%u ambiguous=%u unused=%u per_node=%s lines=%llu probe_loads=%d elapsed_s=%.4f", cls.probed,
         cls.ambiguous, cls.unused, text, (unsigned long long)cls.lines, cls.loads, now_s() - t0);
    if (!cls.lines)
        note("# meshmap: classification failed (%s lines per node, 64 needed)", text);
    for (uint32_t line = 0; line < cls.probed; line++) {
        int h = home[line];
        if (h >= 0 && have[h] < cls.lines)
            dline[h][have[h]++] = (uint16_t)line;
    }
    return cls.lines;
}

static uint64_t buf_pfn; /* page frame number of the buffer's first page, 0 when not known */
static int one_page;     /* the buffer is established as one physical 2 MiB page (check_one_page) */

/* Decides whether the buffer is established as one physical 2 MiB page, and prints the result. The set
 * bound at NBUF and the rebuild of a line's physical address from buf_pfn hold only for "yes".
 *   hugetlb  yes: such a mapping exists only as huge pages.
 *   thp      the kernel accepted the hint for transparent huge pages (common.h alloc_dram). That does
 *            not prove the page size. /proc/self/smaps (the kernel's memory report per mapping)
 *            decides: one mapping must be exactly the buffer, and its AnonHugePages value (the memory
 *            that huge pages map) must be 2 MiB. Anything else: not established.
 *   4k       no.
 * Called after the buffer's first stores: a page exists only once it is touched. */
static void check_one_page(void)
{
    uintptr_t base = (uintptr_t)dram.seg[0].base;
    unsigned long lo, hi, kb = 0;
    char line[256];
    int in = 0, found = 0;
    one_page = !strcmp(dram.backing, "hugetlb");
    if (one_page || !strcmp(dram.backing, "4k")) {
        note("# one_2mib_page: %s (backing=%s)", one_page ? "yes" : "no", dram.backing);
        return;
    }
    FILE *f = fopen("/proc/self/smaps", "re");
    if (!f) {
        note("# one_2mib_page: not established (backing=%s; /proc/self/smaps: %s)", dram.backing, strerror(errno));
        return;
    }
    while (!found && fgets(line, sizeof line, f)) {
        if (sscanf(line, "%lx-%lx ", &lo, &hi) == 2) /* the first line of a mapping: its address range */
            in = lo == base && hi == base + HUGE_BYTES;
        else if (in)
            found = sscanf(line, "AnonHugePages: %lu kB", &kb) == 1;
    }
    fclose(f);
    one_page = found && kb * 1024 == HUGE_BYTES;
    if (found)
        note("# one_2mib_page: %s (backing=%s; smaps: AnonHugePages=%lu kB of the buffer's 2048 kB)", one_page ? "yes" : "not established",
             dram.backing, kb);
    else
        note("# one_2mib_page: not established (backing=%s; smaps: no mapping is exactly the buffer)", dram.backing);
}

/* /proc/self/pagemap holds one 64-bit entry per page of the address space: bit 63 says the page is
 * present, bits 0 to 54 are the page frame number (zero without CAP_SYS_ADMIN). The entry read here
 * is that of the buffer's first page. It gives the address of every line only when the buffer is one
 * physical 2 MiB page (one_page), and the line printed says which case holds. */
static void read_pagemap(void)
{
    uint64_t e = 0;
    long page = sysconf(_SC_PAGESIZE);
    int fd = open("/proc/self/pagemap", O_RDONLY);
    ssize_t r = fd < 0 ? -1 : pread(fd, &e, sizeof e, (off_t)((uintptr_t)dram.seg[0].base / (uintptr_t)page * sizeof e));
    int err = errno;
    if (fd >= 0)
        close(fd);
    if (r != (ssize_t)sizeof e) {
        note("# pagemap: unreadable (%s)", r < 0 ? strerror(err) : "short read");
        return;
    }
    buf_pfn = (e >> 63) ? e & ((1ULL << 55) - 1) : 0;
    if (!buf_pfn) {
        note("# pagemap: unreadable (entry 0x%llx: page not present, or the kernel hides the frame number)", (unsigned long long)e);
        return;
    }
    if (one_page)
        note("# pagemap: pfn=0x%llx page_bytes=%ld covers=buffer (the buffer is one physical 2 MiB page that starts at this frame)",
             (unsigned long long)buf_pfn, page);
    else
        note("# pagemap: pfn=0x%llx page_bytes=%ld covers=first-page (one 2 MiB page is not established: the frame number covers only "
             "the first %ld KiB page of the buffer, and the addresses of the other lines are not known)",
             (unsigned long long)buf_pfn, page, page / 1024);
}

/* The compact record of the classification: one header line, then one character per probed line in
 * address order, 64 per text row: the index of the line's home node in --nodes, or '?' (unused).
 * The header says what the frame number covers: the whole buffer only when the buffer is one physical
 * 2 MiB page. Otherwise a reader cannot rebuild the lines' addresses, so it cannot check a hash. */
static void write_homes(FILE *f)
{
    fprintf(f, "# meshmap homes: first_line=0 count=%u nodes=%s pfn=", cls.probed, cfg.nodes_arg);
    if (!buf_pfn)
        fprintf(f, "- pfn_covers=-\n");
    else if (one_page)
        fprintf(f, "0x%llx pfn_covers=buffer\n", (unsigned long long)buf_pfn);
    else
        fprintf(f, "0x%llx pfn_covers=first-page (one 2 MiB page is not established: the frame number covers only the first %ld KiB page)\n",
                (unsigned long long)buf_pfn, sysconf(_SC_PAGESIZE) / 1024);
    for (uint32_t i = 0; i < cls.probed; i++) {
        fputc(home[i] >= 0 ? '0' + home[i] : '?', f);
        if (i % 64 == 63 || i + 1 == cls.probed)
            fputc('\n', f);
    }
}

/* ---- cells ---- */

enum { K_OCM_FLUSH, K_SLC, K_DRAM_FLUSH, K_OCM_EVICT, K_N };

static const char *kind_name(int kind)
{
    static const char *name[K_N] = { "ocm-flush", "slc", "dram-flush", "ocm-evict" };
    if (cfg.no_perf && kind == K_SLC) return "slc-fake";
    if (cfg.no_perf && kind == K_DRAM_FLUSH) return "dram-flush-fake";
    return name[kind];
}

static uint64_t map_lines;           /* lines per cell of the kinds slc, dram-flush and ocm-evict */
static uint16_t evict[MAX_NODES][NBUF]; /* per node: the evictor's lines, in one fixed random order */
static uint32_t evict_n[MAX_NODES];
static uint8_t *cell_line[MAX_LINES];   /* the lines of the cell being measured */
static uint16_t cell_perm[MAX_LINES];   /* one fixed random order of them, for the preload */
static int warmed[K_N][MAX_NODES];      /* a CPU has measured this kind on this node (the first one warms up twice as long) */

/* The evictor's list: every line 0..nbuf-1 that is not in chain[], shuffled once. Returns its length. */
static uint32_t build_evictor(uint16_t *list, uint32_t nbuf, const uint16_t *chain, uint32_t nchain, uint64_t seed)
{
    static uint8_t in_chain[NBUF];
    uint32_t n = 0;
    memset(in_chain, 0, nbuf);
    for (uint32_t i = 0; i < nchain; i++)
        in_chain[chain[i]] = 1;
    for (uint32_t l = 0; l < nbuf; l++)
        if (!in_chain[l])
            list[n++] = (uint16_t)l;
    rng_state = seed;
    shuffle16(list, n);
    return n;
}

/* The store-preload: one 8-byte store into slot 7 of every chain line, in a new order. A store
 * needs the line in the unique state, so the home node invalidates every copy in another cluster. */
static void preload(uint64_t n)
{
    struct order o = new_order((uint32_t)n);
    for (uint64_t i = 0; i < n; i++)
        *(volatile uint64_t *)(cell_line[cell_perm[order_next(&o)]] + STORE_SLOT * 8) = i;
}

/* The evictor of node k: one independent load of every line of its list, in a new order. */
static void evictor(int k)
{
    struct order o = new_order(evict_n[k]);
    const uint8_t *base = dram.seg[0].base;
    uint64_t sum = 0;
    for (uint32_t i = 0; i < evict_n[k]; i++)
        sum += *(const volatile uint64_t *)(base + (uint64_t)evict[k][order_next(&o)] * LINE_BYTES);
    sink = (void *)(uintptr_t)sum;
}

/* One cell: pin, build the chains, warm up (slc and ocm-evict), then one row per timed pass.
 * Returns 1 when the rows were printed, 0 when the CPU could not be pinned or the cell cannot exist. */
static int run_cell(int kind, long cpu, int k)
{
    int ocm = kind == K_OCM_FLUSH || kind == K_OCM_EVICT;
    int evicting = kind == K_SLC || kind == K_OCM_EVICT;
    uint64_t n = kind == K_OCM_FLUSH ? cfg.lines : map_lines;
    if (ocm && !ocm_base[k])
        return 0; /* the node has no OCM region: the cell is not requested (requested_cells) */
    if (try_pin(cpu) != 0) {
        note("# meshmap: cell %s cpu %ld node %ld skipped (sched_setaffinity: %s)", kind_name(kind), cpu, cfg.nodes[k], strerror(errno));
        return 0;
    }
    for (uint64_t i = 0; i < n; i++)
        cell_line[i] = ocm ? ocm_base[k] + i * LINE_BYTES : line_addr(&dram, dline[k][i]);
    for (int r = 0; r < cfg.reps; r++)
        build_chain(cell_line, n, r, chain_seed(kind, k, cpu, r));
    for (uint64_t i = 0; i < n; i++)
        cell_perm[i] = (uint16_t)i;
    shuffle16(cell_perm, (uint32_t)n);
    int warm = evicting ? cfg.warm * (warmed[kind][k] ? 1 : 2) : 0;
    warmed[kind][k] = 1;
    for (int r = -warm; r < cfg.reps; r++) { /* r < 0: an untimed warm-up cycle on chain 0 */
        struct bracket b;
        if (evicting) {
            preload(n);
            evictor(k);
        } else {
            for (uint64_t i = 0; i < n; i++)
                civac(cell_line[i]);
            dsb_sy();
        }
        bracket(cell_line[0] + (r < 0 ? 0 : r) * 8, n, &b);
        if (r >= 0)
            print_row(kind_name(kind), cpu, k, n, r, &b);
    }
    if (kind == K_DRAM_FLUSH) /* dirty again: every slc line is stored after its last DC CIVAC */
        preload(n);
    return 1;
}

static void idle_row(long cpu)
{
    struct bracket b;
    if (try_pin(cpu) != 0) {
        note("# meshmap: idle row of cpu %ld skipped (sched_setaffinity: %s)", cpu, strerror(errno));
        return;
    }
    bracket(NULL, 0, &b);
    print_row("idle", cpu, -1, 0, 0, &b);
}

/* OCM region i belongs to the home node ocm_node[i] (asimov-address-map profiles/sam_map.yaml: the ids
 * of HNS in lib_run.sh). The region of a node follows from its id, not from its place in --nodes. */
#define OCM_REGIONS 5
static const long ocm_node[OCM_REGIONS] = { 88, 160, 216, 288, 344 };

/* The OCM region of a node id, or -1 when the node has none. */
static int ocm_region(long node)
{
    for (int r = 0; r < OCM_REGIONS; r++)
        if (ocm_node[r] == node)
            return r;
    return -1;
}

/* The cells that the command line requests for `ncpus` CPUs: per CPU and node the two DRAM kinds, and
 * the two OCM kinds when the node has an OCM region and --no-ocm is not given. A node without a
 * region cannot have OCM cells, so none is counted for it. */
static int requested_cells(int ncpus)
{
    int per_cpu = 0;
    for (int k = 0; k < cfg.nnodes; k++)
        per_cpu += 2 + (!cfg.no_ocm && ocm_region(cfg.nodes[k]) >= 0 ? 2 : 0);
    return ncpus * per_cpu;
}

/* Maps the OCM region of every node of --nodes that has one, and stores one word in every line a cell
 * can use: OCM must be written before it is read. ocm_base[k] stays NULL for a node without a region.
 * Own code in place of common.h map_dev, which ends the process on a failure. Returns 1 when every
 * such region is mapped, 0 when a region failed to map or no node has one. */
static int map_ocm(void)
{
    int nocm = 0;
    for (int k = 0; k < cfg.nnodes; k++) {
        if (ocm_region(cfg.nodes[k]) >= 0)
            nocm++;
        else
            note("# meshmap: node %ld has no OCM region (regions 0..4 belong to nodes 88,160,216,288,344): no OCM cells for it", cfg.nodes[k]);
    }
    if (!nocm)
        return 0;
    int fd = open(memcfg.ocm_dev, O_RDWR);
    if (fd < 0) {
        note("# meshmap: OCM kinds skipped (open %s: %s)", memcfg.ocm_dev, strerror(errno));
        return 0;
    }
    for (int k = 0; k < cfg.nnodes; k++) {
        int r = ocm_region(cfg.nodes[k]);
        if (r < 0)
            continue;
        uint64_t off = memcfg.ocm_base + (uint64_t)r * memcfg.ocm_stride;
        void *p = mmap(NULL, memcfg.ocm_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, (off_t)off);
        if (p == MAP_FAILED) {
            note("# meshmap: OCM kinds skipped (mmap %s offset 0x%llx: %s)", memcfg.ocm_dev, (unsigned long long)off, strerror(errno));
            close(fd);
            return 0;
        }
        ocm_base[k] = p;
        for (uint64_t l = 0; l < cfg.lines; l++)
            *(volatile uint64_t *)(ocm_base[k] + l * LINE_BYTES) = l;
    }
    close(fd);
    return 1;
}

/* Keeps the CPUs the thread can be pinned to; a failing CPU gets a '#' line. Returns how many stay. */
static int keep_pinnable(long *cpu, int n)
{
    int kept = 0;
    for (int i = 0; i < n; i++) {
        if (try_pin(cpu[i]) != 0) {
            note("# meshmap: cpu %ld dropped (sched_setaffinity: %s)", cpu[i], strerror(errno));
            continue;
        }
        cpu[kept++] = cpu[i];
    }
    return kept;
}

/* ---- self-test (--selftest): no PMU, no device ---- */

static int st_failed;
#define CHECK(name, cond) do { int ok_ = (cond); printf("%s %s\n", ok_ ? "ok  " : "FAIL", name); st_failed += !ok_; } while (0)

static int sim_mode, sim_calls;

/* A simulated probe: the home of a line is its index mod 5, with one fault per mode. */
static double probe_sim(uint32_t line, int loads, int64_t d[MESH_MAX], int *valid)
{
    int k = (int)(line % 5);
    memset(d, 0, sizeof(int64_t) * MESH_MAX);
    *valid = 1;
    if (sim_mode == 1)
        d[(k + 1) % 5] = 40; /* a second node with 40 counts: too many beside 2 x 64, few enough beside 2 x 128 */
    if ((sim_mode == 2 && line % 20 == 3) || sim_mode == 6) {
        d[k] = loads / 2; /* never a clear winner */
        return 0;
    }
    if (sim_mode == 5 || (sim_mode == 7 && sim_calls++ % 8 == 7))
        *valid = 0; /* mode 5: the counters never cover a window. Mode 7: not in every 8th window */
    if (sim_mode == 3 && k == 4 && line >= 1500)
        k = 0; /* node 4 owns only 300 lines */
    if (sim_mode == 4 && line == 7 && sim_calls++ == 0)
        *valid = 0; /* one window that the counters did not cover */
    d[k] += 2 * (int64_t)loads;
    return 0;
}

static void st_file(const char *dir, const char *rel, const char *text)
{
    char path[1024];
    snprintf(path, sizeof path, "%s/%s", dir, rel);
    if (!text) { /* remove */
        if (unlink(path) != 0)
            rmdir(path);
        return;
    }
    FILE *f = fopen(path, "w");
    if (f) {
        fputs(text, f);
        fclose(f);
    }
}

static int selftest(void)
{
    static const long ids[5] = { 88, 160, 216, 288, 344 };
    static const int64_t fl0[5] = { 0, 0, 0, 0, 0 };
    out = stdout;
    quiet = 1;
    cfg.nnodes = 5;
    cfg.nodes_arg = "88,160,216,288,344";
    memcpy(cfg.nodes, ids, sizeof ids);
    cfg.probe_loads = 64;
    cfg.max_classify_s = 1.0;

    /* decision rule, 64 pairs: the bounds are 48 for the winner and winner / 4 for any other node */
    {
        const int64_t clear[5] = { 3, 130, 2, 4, 1 }, low[5] = { 47, 0, 0, 0, 0 }, edge[5] = { 0, 0, 48, 12, 12 };
        const int64_t second[5] = { 100, 26, 0, 0, 0 }, tie[5] = { 100, 0, 0, 100, 0 }, neg[5] = { -3, -1, 60, -2, 0 };
        const int64_t f1[5] = { 60, 40, 0, 0, 0 }, fl1[5] = { 0, 30, 0, 0, 0 }, f2[5] = { 50, 0, 0, 0, 0 }, fl2[5] = { 10, 0, 0, 0, 0 };
        CHECK("decide: clear winner accepted", decide(clear, fl0, 5, 64) == 1);
        CHECK("decide: winner below 3/4 of the pairs rejected", decide(low, fl0, 5, 64) == -1);
        CHECK("decide: winner at 3/4 with others at winner/4 accepted", decide(edge, fl0, 5, 64) == 2);
        CHECK("decide: another node above winner/4 rejected", decide(second, fl0, 5, 64) == -1);
        CHECK("decide: tie rejected", decide(tie, fl0, 5, 64) == -1);
        CHECK("decide: negative changes of other nodes accepted", decide(neg, fl0, 5, 64) == 2);
        CHECK("decide: floor subtracted before the rule (accept)", decide(f1, fl1, 5, 64) == 0 && decide(f1, fl0, 5, 64) == -1);
        CHECK("decide: floor subtracted before the rule (reject)", decide(f2, fl2, 5, 64) == -1 && decide(f2, fl0, 5, 64) == 0);
    }

    /* chain builder: the cell is the odd lines of a small buffer; chains in slots 0 and 1 */
    {
        enum { N = 200 };
        const uint64_t pat = 0xA5A5A5A5A5A5A5A5ULL;
        uint64_t *mem = aligned_alloc(LINE_BYTES, 2 * N * LINE_BYTES);
        uint8_t *line[N];
        int next[2][N], one_cycle = 1, own_slot = 1, back = 1, differ = 0;
        if (!mem) {
            printf("FAIL selftest: no memory\n");
            return 1;
        }
        for (int i = 0; i < 2 * N * 8; i++)
            mem[i] = pat;
        for (int i = 0; i < N; i++)
            line[i] = (uint8_t *)mem + (2 * i + 1) * LINE_BYTES;
        for (int r = 0; r < 2; r++) {
            int seen[N] = { 0 }, at = 0;
            build_chain(line, N, r, chain_seed(K_SLC, 1, 2, r));
            for (int i = 0; i < N; i++) { /* walk N loads from line 0 */
                uint8_t *p = *(uint8_t **)(line[at] + r * 8);
                long off = p - (uint8_t *)mem;
                long l = off / LINE_BYTES;
                if (off < 0 || l >= 2 * N || l % 2 != 1 || off % LINE_BYTES != r * 8 || seen[l / 2]++) {
                    one_cycle = 0;
                    break;
                }
                next[r][at] = (int)(l / 2);
                at = (int)(l / 2);
            }
            one_cycle = one_cycle && at == 0; /* N loads visit N different lines and end at the start */
            back = back && chase(line[0] + r * 8, N) == (void *)(line[0] + r * 8);
        }
        for (int i = 0; i < 2 * N * 8; i++)
            if (mem[i] == pat ? (i / 8) % 2 == 1 && i % 8 < 2 : !((i / 8) % 2 == 1 && i % 8 < 2))
                own_slot = 0; /* a chain word still holds the pattern, or another word was changed */
        for (int i = 0; i < N && one_cycle; i++)
            differ += next[0][i] != next[1][i];
        CHECK("chain: one cycle over exactly the cell's lines", one_cycle);
        CHECK("chain: only its own slot of the cell's lines is written", own_slot);
        CHECK("chain: the chase of `lines` loads returns to the start", back);
        CHECK("chain: two reps differ in order", one_cycle && differ > N / 2);
        free(mem);
    }

    /* evictor list and visiting order: 1,000 lines, 100 chain lines, so 900 = 2^2 x 3^2 x 5^2 elements */
    {
        enum { NB = 1000, NC = 100 };
        static uint16_t list[NB], chain[NC];
        int seen[NB] = { 0 }, list_ok = 1, order_ok = 1, differ = 0;
        uint32_t first[2][8];
        for (int i = 0; i < NC; i++)
            chain[i] = (uint16_t)(i * 7 + 3);
        uint32_t n = build_evictor(list, NB, chain, NC, 12345);
        for (uint32_t i = 0; i < n; i++)
            seen[list[i]]++;
        for (int l = 0; l < NB; l++)
            if (seen[l] != (l % 7 == 3 && l / 7 < NC ? 0 : 1))
                list_ok = 0;
        CHECK("evictor: no chain line, every other line once", n == NB - NC && list_ok);
        for (int t = 0; t < 50; t++) {
            int hit[NB - NC] = { 0 };
            struct order o = new_order(n);
            for (uint32_t i = 0; i < n; i++) {
                uint32_t j = order_next(&o);
                if (j >= n || hit[j]++)
                    order_ok = 0;
                if (t < 2 && i < 8)
                    first[t][i] = j;
            }
        }
        for (int i = 0; i < 8; i++)
            differ += first[0][i] != first[1][i];
        CHECK("evictor: each of 50 visiting orders reaches every element once", order_ok);
        CHECK("evictor: two visiting orders differ", differ > 0);
    }

    /* lines step-down */
    {
        const uint32_t even[5] = { 6560, 6552, 6552, 6552, 6552 }, c1500[5] = { 2048, 1500, 3000, 2048, 2048 };
        const uint32_t c300[5] = { 300, 2048, 2048, 2048, 2048 }, c100[5] = { 2048, 2048, 100, 2048, 2048 }, c63[5] = { 2048, 2048, 2048, 2048, 63 };
        const uint32_t c512[5] = { 512, 2048, 2048, 2048, 2048 }, c64[5] = { 2048, 64, 2048, 2048, 2048 };
        CHECK("lines for counts: every node reaches the target", lines_for_counts(even, 5, 2048) == 2048 && lines_for_counts(even, 5, 4096) == 4096);
        CHECK("lines for counts: 1,500 -> 1024, 300 -> 256, 100 -> 64", lines_for_counts(c1500, 5, 2048) == 1024 &&
              lines_for_counts(c300, 5, 2048) == 256 && lines_for_counts(c100, 5, 2048) == 64);
        CHECK("lines for counts: never above the target", lines_for_counts(c1500, 5, 512) == 512 && lines_for_counts(c300, 5, 512) == 256);
        CHECK("lines for counts: a count equal to a step reaches it", lines_for_counts(c512, 5, 2048) == 512 && lines_for_counts(c64, 5, 2048) == 64);
        CHECK("lines for counts: below 64 fails", lines_for_counts(c63, 5, 2048) == 0 && lines_for_counts(c63, 5, 64) == 0);
        /* 5 nodes: 2048 lines need 12,800 probes, 1024 need 6,400, 512 need 3,200, 256 need 1,600 */
        CHECK("lines for budget: 11 us probes fit 2048 in 1 s", lines_for_budget(2048, 11e3, 5, 1.0) == 2048);
        CHECK("lines for budget: 100 us probes -> 1024, 200 us -> 512, 500 us -> 256", lines_for_budget(2048, 100e3, 5, 1.0) == 1024 &&
              lines_for_budget(2048, 200e3, 5, 1.0) == 512 && lines_for_budget(2048, 500e3, 5, 1.0) == 256);
        CHECK("lines for budget: nothing fits -> the smallest", lines_for_budget(2048, 5e6, 5, 1.0) == 256 && lines_for_budget(64, 5e6, 5, 1.0) == 64);
        CHECK("lines for budget: never above the request", lines_for_budget(512, 11e3, 5, 1.0) == 512 && lines_for_budget(320, 300e3, 5, 1.0) == 320 &&
              lines_for_budget(320, 600e3, 5, 1.0) == 256);
    }

    /* the walk of the classification on simulated probes */
    {
        cfg.lines = 2048;
        sim_mode = 0;
        CHECK("classify: clean probes give every node its lines in address order", classify(probe_sim) == 2048 && cls.probed == 10240 &&
              cls.ambiguous == 0 && cls.unused == 0 && cls.loads == 64 && dline[3][5] == 28);
        sim_mode = 1;
        CHECK("classify: over 1/4 ambiguous in 256 probes doubles the pairs and restarts", classify(probe_sim) == 2048 && cls.loads == 128 &&
              cls.probed == 10240 && cls.ambiguous == 0);
        sim_mode = 2; /* node 3 loses lines 3, 23, 43, ..: its 2,048th line is line 13,653, after 683 lost lines */
        CHECK("classify: a line ambiguous three times is left unused", classify(probe_sim) == 2048 && cls.loads == 64 && cls.probed == 13654 &&
              cls.unused == 683 && cls.ambiguous == 3 * 683 && home[23] == HOME_UNUSED && home[8] == 3 && dline[3][0] == 8);
        sim_mode = 3;
        CHECK("classify: a short node lowers the lines after the whole buffer", classify(probe_sim) == 256 && cls.probed == NBUF &&
              cls.count[4] == 300 && dline[4][255] == 1279);
        sim_mode = 4;
        sim_calls = 0;
        CHECK("classify: an invalid window is retried", classify(probe_sim) == 2048 && cls.ambiguous == 1 && cls.unused == 0 && home[7] == 2);
        sim_mode = 5; /* 21 lines of 3 probes, then the 64th probe on line 21 */
        CHECK("classify: 64 invalid windows in a row stop the walk", classify(probe_sim) == 0 && cls.loads == 64 && cls.ambiguous == 64 &&
              cls.probed == 21 && cls.unused == 21);
        sim_mode = 6; /* two doublings, then 85 lines of 3 probes and the 256th probe on line 85 */
        CHECK("classify: no clear home in 256 probes at 256 pairs stops the walk", classify(probe_sim) == 0 && cls.loads == 256 &&
              cls.ambiguous == 256 && cls.probed == 85 && cls.unused == 85);
        sim_mode = 7; /* 10,240 lines need 11,702 probes, of which 1,462 are not valid */
        sim_calls = 0;
        CHECK("classify: invalid windows that are not in a row do not stop the walk", classify(probe_sim) == 2048 && cls.probed == 10240 &&
              cls.ambiguous == 1462 && cls.unused == 0);
    }

    /* homes file text, read back */
    {
        const char *head = "# meshmap homes: first_line=0 count=150 nodes=88,160,216,288,344 pfn=- pfn_covers=-\n";
        char text[1024];
        FILE *f = fmemopen(text, sizeof text, "w");
        int same = f != NULL, rows = 0;
        memset(&cls, 0, sizeof cls);
        cls.probed = 150;
        buf_pfn = 0;
        for (int i = 0; i < 150; i++)
            home[i] = (int8_t)(i % 11 == 4 ? HOME_UNUSED : i % 5);
        if (f) {
            write_homes(f);
            fclose(f);
            const char *p = text + strlen(head);
            same = !strncmp(text, head, strlen(head));
            for (int i = 0; i < 150 && same; i++, p++) {
                if (*p == '\n' && i % 64 == 0 && i > 0) {
                    p++;
                    rows++;
                }
                same = *p == (i % 11 == 4 ? '?' : '0' + i % 5);
            }
            same = same && rows == 2 && !strcmp(p, "\n");
        }
        CHECK("homes: header and one character per line, 64 per row, read back the same", same);
        /* the header with a frame number: it covers the buffer only when one 2 MiB page is established */
        int covers = 1;
        buf_pfn = 0x1234;
        for (one_page = 0; one_page < 2; one_page++) {
            memset(text, 0, sizeof text);
            f = fmemopen(text, sizeof text, "w");
            if (f) {
                write_homes(f);
                fclose(f);
            }
            covers = covers && f && !strncmp(text, head, strlen(head) - strlen("- pfn_covers=-\n")) &&
                     (strstr(text, " pfn=0x1234 pfn_covers=buffer\n") != NULL) == one_page &&
                     (strstr(text, " pfn=0x1234 pfn_covers=first-page (") != NULL) == !one_page;
        }
        buf_pfn = 0;
        one_page = 0;
        CHECK("homes: the frame number covers the buffer only when one 2 MiB page is established", covers);
    }

    /* a failed write: /dev/full accepts the open and refuses every write (no space left on device).
     * The row and the homes record go through the functions that main uses. */
    {
        struct bracket b;
        char text[1024];
        FILE *mem = fmemopen(text, sizeof text, "w"), *full = fopen("/dev/full", "we"), *hfull = fopen("/dev/full", "we");
        memset(&b, 0, sizeof b);
        if (mem) {
            out = mem;
            print_row("idle", 0, -1, 0, 0, &b);
            out = stdout;
            fclose(mem);
        }
        CHECK("write failure: a row that is written sets no flag, and all cells printed is then exit 0", mem && !out_failed &&
              exit_status(10, 10) == 0 && exit_status(9, 10) == 1);
        if (!full || !hfull) {
            printf("ok   (skipped: no /dev/full) write failure: a row and a homes record to /dev/full\n");
        } else {
            out = full;
            print_row("idle", 0, -1, 0, 0, &b);
            out = stdout;
            CHECK("write failure: a row to /dev/full sets the flag, and all cells printed is then exit 1", out_failed == 1 &&
                  !homes_failed && exit_status(10, 10) == 1);
            out_failed = 0;
            write_homes(hfull);
            close_checked(hfull, &homes_failed, "/dev/full");
            hfull = NULL;
            CHECK("write failure: a homes record to /dev/full sets its flag, and all cells printed is then exit 1", homes_failed == 1 &&
                  !out_failed && exit_status(10, 10) == 1);
            homes_failed = 0;
        }
        if (full)
            fclose(full);
        if (hfull)
            fclose(hfull);
    }

    /* sysfs config builder against a directory that holds the image's strings (boot F1 sysinfo.txt: type,
     * cpumask, the two request events; the format ranges are the driver's; the two snoop events carry
     * made-up event ids, and hns_cache_miss_all is left out to check that an absent sum is dropped) */
    {
        static const char *fix[][2] = {
            { "arm_cmn_0/type", "8\n" },
            { "arm_cmn_0/cpumask", "0\n" },
            { "arm_cmn_0/events/hns_pocq_reqs_recvd_all", "type=0x200,eventid=0x5,occupid=0x0\n" },
            { "arm_cmn_0/events/hns_mc_reqs_local_all", "type=0x200,eventid=0xd,occupid=0x0\n" },
            { "arm_cmn_0/events/hns_snp_sent_cluster", "type=0x200,eventid=0x1f\n" },
            { "arm_cmn_0/events/hns_snp_sent", "type=0x200,eventid=0x1e\n" },
            { "arm_cmn_0/format/type", "config:0-15\n" },
            { "arm_cmn_0/format/eventid", "config:16-26\n" },
            { "arm_cmn_0/format/occupid", "config:27-30\n" },
            { "arm_cmn_0/format/bynodeid", "config:31\n" },
            { "arm_cmn_0/format/nodeid", "config:32-47\n" },
        };
        const int nfix = (int)(sizeof fix / sizeof fix[0]);
        char dir[512];
        uint64_t c[3];
        const char *tmp = getenv("TMPDIR");
        snprintf(dir, sizeof dir, "%.480s/meshmap-selftest-XXXXXX", tmp && *tmp ? tmp : "/tmp");
        if (!mkdtemp(dir)) {
            CHECK("sysfs: temporary directory", 0);
        } else {
            char sub[1024];
            snprintf(sub, sizeof sub, "%s/arm_cmn_0", dir);
            mkdir(sub, 0700);
            snprintf(sub, sizeof sub, "%s/arm_cmn_0/events", dir);
            mkdir(sub, 0700);
            snprintf(sub, sizeof sub, "%s/arm_cmn_0/format", dir);
            mkdir(sub, 0700);
            for (int i = 0; i < nfix; i++)
                st_file(dir, fix[i][0], fix[i][1]);
            cfg.sysfs = dir;
            cfg.pmu = "arm_cmn_0";
            cfg.event = "hns_pocq_reqs_recvd_all";
            mesh_close();
            CHECK("sysfs: PMU type 8 on CPU 0, per-node event found", mesh_configs() == 0 && mesh.type == 8 && mesh.cpu == 0);
            CHECK("sysfs: config of node 160 = 0x200 | 0x5<<16 | 1<<31 | 160<<32",
                  mesh.config[1][0] == (0x200ULL | 0x5ULL << 16 | 1ULL << 31 | 160ULL << 32) && mesh.config[1][1] == 0 && mesh.config[1][2] == 0);
            CHECK("sysfs: a sum sets no node field", mesh.built[MAX_NODES] && mesh.config[MAX_NODES][0] == (0x200ULL | 0xdULL << 16));
            CHECK("sysfs: an absent sum is dropped, the exact name hns_snp_sent wins", !mesh.built[MAX_NODES + 1] && mesh.built[MAX_NODES + 2] &&
                  !strcmp(mesh.sum_name[2], "hns_snp_sent") && mesh.config[MAX_NODES + 2][0] == (0x200ULL | 0x1eULL << 16));
            CHECK("sysfs: an unknown event and a node id above 16 bits fail", build_event(c, "no_such_event", -1) < 0 &&
                  build_event(c, "hns_pocq_reqs_recvd_all", 70000) < 0);
            for (int i = nfix - 1; i >= 0; i--)
                st_file(dir, fix[i][0], NULL);
            st_file(dir, "arm_cmn_0/format", NULL);
            st_file(dir, "arm_cmn_0/events", NULL);
            st_file(dir, "arm_cmn_0", NULL);
            rmdir(dir);
        }
    }

    /* OCM regions by node id. A file stands in for the device, with region r at offset r x stride. Each
     * mapped node stores its id in the first word of its region. The file must then hold the id of
     * ocm_node[r] in region r, whatever the order of --nodes, and a region of no listed node is untouched. */
    {
        static const long lists[3][5] = { { 88, 160, 216, 288, 344 }, { 344, 288, 216, 160, 88 }, { 88, 999, 216, 288, 344 } };
        static const char *name[3] = { "ocm: the default list maps node i to region i",
                                       "ocm: the list 344,288,216,160,88 maps node 344 to region 4 and node 88 to region 0",
                                       "ocm: an unknown node id gets no region and no requested OCM cell" };
        const uint64_t untouched = 7;
        const char *tmp = getenv("TMPDIR");
        char path[512];
        snprintf(path, sizeof path, "%.480s/meshmap-selftest-ocm-XXXXXX", tmp && *tmp ? tmp : "/tmp");
        int fd = mkstemp(path);
        if (fd < 0 || ftruncate(fd, (off_t)(4 * memcfg.ocm_stride + memcfg.ocm_size)) != 0) {
            CHECK("ocm: temporary file", 0);
        } else {
            memcfg.ocm_dev = path;
            memcfg.ocm_base = 0;
            cfg.lines = 64;
            cfg.no_ocm = 0;
            CHECK("ocm: region of a node id", ocm_region(88) == 0 && ocm_region(216) == 2 && ocm_region(344) == 4 && ocm_region(999) == -1 &&
                  ocm_region(0) == -1);
            for (int t = 0; t < 3; t++) {
                int ok = 1;
                memcpy(cfg.nodes, lists[t], sizeof lists[t]);
                memset(ocm_base, 0, sizeof ocm_base);
                for (int r = 0; r < OCM_REGIONS; r++)
                    ok = ok && pwrite(fd, &untouched, 8, (off_t)(r * memcfg.ocm_stride)) == 8;
                ok = ok && map_ocm() == 1;
                for (int k = 0; k < 5; k++) {
                    ok = ok && (ocm_base[k] != NULL) == (lists[t][k] != 999);
                    if (ocm_base[k]) {
                        *(uint64_t *)ocm_base[k] = (uint64_t)lists[t][k];
                        munmap(ocm_base[k], memcfg.ocm_size);
                    }
                }
                for (int r = 0; r < OCM_REGIONS; r++) {
                    uint64_t w = 0, want = t == 2 && r == 1 ? untouched : (uint64_t)ocm_node[r];
                    ok = ok && pread(fd, &w, 8, (off_t)(r * memcfg.ocm_stride)) == 8 && w == want;
                }
                ok = ok && requested_cells(8) == (t == 2 ? 8 * (5 * 2 + 4 * 2) : 160);
                CHECK(name[t], ok);
            }
            cfg.no_ocm = 1;
            CHECK("ocm: --no-ocm requests the two DRAM kinds only", requested_cells(8) == 8 * 5 * 2);
            memset(ocm_base, 0, sizeof ocm_base);
        }
        if (fd >= 0) {
            close(fd);
            unlink(path);
        }
    }

    printf("meshmap selftest: %s\n", st_failed ? "FAILED" : "all checks passed");
    return st_failed ? 1 : 0;
}

static void usage(void)
{
    fprintf(stderr,
            "usage: meshmap [--cpus LIST] [--last-cpus LIST] [--nodes ID,..] [--pmu NAME] [--sysfs DIR]\n"
            "               [--event NAME] [--lines N] [--reps R] [--warm W] [--probe-loads P]\n"
            "               [--max-classify-s S] [--out FILE] [--homes FILE] [--no-perf] [--no-ocm] [--selftest]\n"
            "               [--ocm-dev PATH] [--no-hugetlb] [--no-thp]\n"
            "  --cpus: CPUs in measuring order (default 2,4,6,8,3,5,7,9). --last-cpus: CPUs measured in a\n"
            "    last block, after every other row is written (meant for CPU 0, the kernel's CPU).\n"
            "  --nodes: home node ids, at most 8 (default 88,160,216,288,344 = OCM regions 0..4). The OCM\n"
            "    region of a node follows from its id, not from its place in the list. Another id has no OCM\n"
            "    region: it gets the DRAM kinds only, and no OCM cell is counted as requested for it.\n"
            "  --pmu, --sysfs, --event: the mesh PMU (arm_cmn_0), the directory that holds it\n"
            "    (/sys/bus/event_source/devices) and the per-node request event (hns_pocq_reqs_recvd_all).\n"
            "  --lines: loads per pass, a multiple of 8 from 64 to 4096 (default 2048). --reps: timed passes\n"
            "    per cell, 1..7 (default 7). --warm: untimed cycles before them (default 2).\n"
            "  --probe-loads: flush-and-load pairs per probed line (default 64; doubles when too many\n"
            "    probes are ambiguous). --max-classify-s: time budget of the classification (default 1.0);\n"
            "    the program lowers the lines per node to fit.\n"
            "  --out FILE: append rows and '#' lines to FILE, each flushed immediately (default stdout).\n"
            "  --homes FILE: the compact record of the classification, one character per probed line.\n"
            "  --no-perf: no mesh counters; fake homes (line index mod number of nodes); for a host check.\n"
            "  --no-ocm: skip the OCM kinds. --selftest: run the unit checks and exit 0 or 1.\n"
            "  Exit status: 0 when every requested cell was printed and no write to the rows or to the\n"
            "    --homes file failed, else 1. A failed write is reported once per file on stderr.\n");
    exit(2);
}

/* "2,4,6": non-negative numbers separated by commas. An empty text is an empty list. */
static int parse_ints(const char *s, long *v, int max)
{
    int n = 0;
    while (*s) {
        char *end;
        long x = strtol(s, &end, 10);
        if (end == s || x < 0 || n == max || (*end != ',' && *end != '\0'))
            usage();
        v[n++] = x;
        s = *end ? end + 1 : end;
    }
    return n;
}

int main(int argc, char **argv)
{
    int run_selftest = 0;
    t_main = now_s();
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        int more = i + 1 < argc;
        if (!strcmp(a, "--no-perf")) cfg.no_perf = 1;
        else if (!strcmp(a, "--no-ocm")) cfg.no_ocm = 1;
        else if (!strcmp(a, "--selftest")) run_selftest = 1;
        else if (!strcmp(a, "--no-hugetlb")) memcfg.no_hugetlb = 1;
        else if (!strcmp(a, "--no-thp")) memcfg.no_hugetlb = memcfg.no_thp = 1;
        else if (!more) usage();
        else if (!strcmp(a, "--cpus")) cfg.cpus_arg = argv[++i];
        else if (!strcmp(a, "--last-cpus")) cfg.last_arg = argv[++i];
        else if (!strcmp(a, "--nodes")) cfg.nodes_arg = argv[++i];
        else if (!strcmp(a, "--pmu")) cfg.pmu = argv[++i];
        else if (!strcmp(a, "--sysfs")) cfg.sysfs = argv[++i];
        else if (!strcmp(a, "--event")) cfg.event = argv[++i];
        else if (!strcmp(a, "--lines")) cfg.lines = strtoull(argv[++i], NULL, 10);
        else if (!strcmp(a, "--reps")) cfg.reps = atoi(argv[++i]);
        else if (!strcmp(a, "--warm")) cfg.warm = atoi(argv[++i]);
        else if (!strcmp(a, "--probe-loads")) cfg.probe_loads = atoi(argv[++i]);
        else if (!strcmp(a, "--max-classify-s")) cfg.max_classify_s = atof(argv[++i]);
        else if (!strcmp(a, "--out")) cfg.out_path = argv[++i];
        else if (!strcmp(a, "--homes")) cfg.homes_path = argv[++i];
        else if (!strcmp(a, "--ocm-dev")) memcfg.ocm_dev = argv[++i];
        else usage();
    }
    if (run_selftest)
        return selftest();
    cfg.ncpus = parse_ints(cfg.cpus_arg, cfg.cpus, MAX_CPUS);
    cfg.nlast = parse_ints(cfg.last_arg, cfg.last, MAX_CPUS);
    cfg.nnodes = parse_ints(cfg.nodes_arg, cfg.nodes, MAX_NODES);
    if (cfg.nnodes < 1 || cfg.lines < 64 || cfg.lines > MAX_LINES || cfg.lines % 8 || cfg.reps < 1 || cfg.reps > STORE_SLOT ||
        cfg.warm < 0 || cfg.warm > 64 || cfg.probe_loads < 1 || cfg.probe_loads > 4096 || !(cfg.max_classify_s > 0))
        usage();
    for (int k = 0; k < cfg.nnodes; k++)
        if (cfg.nodes[k] > 0xFFFF)
            usage();

    /* A. preflight. From here on nothing ends the process but a failed allocation of the buffer. */
    out = stdout;
    if (cfg.out_path && !(out = fopen(cfg.out_path, "ae"))) {
        out = stdout;
        write_failed(&out_failed, cfg.out_path); /* the requested file gets no row: the exit status is 1 */
        note("# meshmap: cannot append to %s (%s): rows go to stdout", cfg.out_path, strerror(errno));
    }
    int requested = requested_cells(cfg.ncpus + cfg.nlast), printed = 0;
    /* --last-cpus first: the test leaves the thread on the last CPU it pinned, and the rest of the
     * preflight must not run on a CPU of the last block. The test comes before the buffer, so the
     * buffer's first stores run on a measuring CPU. */
    cfg.nlast = keep_pinnable(cfg.last, cfg.nlast);
    cfg.ncpus = keep_pinnable(cfg.cpus, cfg.ncpus);
    alloc_dram(&dram, HUGE_BYTES);
    fill_buf(&dram, 0x9E3779B97F4A7C15ULL);
    note("# meshmap: ns_per_load = elapsed_ns / lines; one row per timed pass. cpus=%s last_cpus=%s nodes=%s lines=%llu reps=%d warm=%d probe_loads=%d event=%s backing=%s cntfrq_hz=%llu",
         cfg.cpus_arg, *cfg.last_arg ? cfg.last_arg : "-", cfg.nodes_arg, (unsigned long long)cfg.lines, cfg.reps, cfg.warm,
         cfg.probe_loads, cfg.event, dram.backing, (unsigned long long)read_cntfrq());
    fprintf(out, "kind,cpu,node,lines,rep,ns_per_load,cycles_per_load");
    for (int i = 1; i < PERF_N; i++)
        fprintf(out, ",%s", perf_name_map[i]);
    fprintf(out, ",perf_cov");
    for (int k = 0; k < cfg.nnodes; k++)
        fprintf(out, ",req_%ld", cfg.nodes[k]);
    fprintf(out, ",mc_reqs,cache_miss,snp_sent,window_ns\n");
    out_flush();

    int have_ocm = !cfg.no_ocm && map_ocm();
    check_one_page();
    read_pagemap();
    /* The group is opened on the calling thread for any CPU (common.h perf_open_one: pid 0, cpu -1),
     * so it follows the thread from cell to cell and is not opened again per CPU. */
    perf_open_map(&pg);
    fflush(stdout);
    mesh_close(); /* no mesh counter is open yet: every descriptor and position is -1 */
    print_bracket_overhead();

    /* B. ocm-flush cells: they need no mesh counter and no classification. */
    if (have_ocm)
        progress("ocm-flush cells");
    for (int c = 0; have_ocm && c < cfg.ncpus; c++)
        for (int k = 0; k < cfg.nnodes; k++)
            printed += run_cell(K_OCM_FLUSH, cfg.cpus[c], k);

    /* C and D. mesh counters, read floor, classification; all on the first measuring CPU. */
    int have_dram = 0, have_cpu = cfg.ncpus + cfg.nlast > 0;
    map_lines = cfg.lines;
    if (!have_cpu)
        note("# meshmap: no usable CPU in --cpus and --last-cpus");
    else if (try_pin(cfg.ncpus ? cfg.cpus[0] : cfg.last[0]) != 0)
        note("# meshmap: classification not pinned (sched_setaffinity: %s)", strerror(errno));
    if (have_cpu && cfg.no_perf) {
        progress("classification (fake homes)");
        have_dram = classify(probe_fake) != 0;
    } else if (have_cpu) {
        progress("mesh counters");
        if (mesh_start()) {
            mesh_floor();
            progress("classification");
            have_dram = classify(probe_real) != 0;
        }
    }
    if (have_dram)
        map_lines = cls.lines;
    if (cfg.homes_path && cls.probed) {
        FILE *f = fopen(cfg.homes_path, "we");
        if (f) {
            write_homes(f);
            close_checked(f, &homes_failed, cfg.homes_path);
        } else {
            write_failed(&homes_failed, cfg.homes_path);
            note("# meshmap: homes file %s not written (%s)", cfg.homes_path, strerror(errno));
        }
    } else if (cfg.homes_path)
        note("# meshmap: homes file %s not written (no classification)", cfg.homes_path);
    for (int k = 0; k < cfg.nnodes; k++) /* without DRAM chains the evictor is the whole buffer */
        evict_n[k] = build_evictor(evict[k], NBUF, dline[k], have_dram ? (uint32_t)map_lines : 0, 0xD1B54A32D192ED03ULL * (uint64_t)(k + 1));

    /* E. per kind, every CPU of --cpus and every node. */
    progress(have_dram ? "idle rows and slc cells" : "idle rows (DRAM kinds skipped)");
    for (int c = 0; c < cfg.ncpus; c++) {
        idle_row(cfg.cpus[c]);
        for (int k = 0; have_dram && k < cfg.nnodes; k++)
            printed += run_cell(K_SLC, cfg.cpus[c], k);
    }
    if (have_dram)
        progress("dram-flush cells");
    for (int c = 0; have_dram && c < cfg.ncpus; c++)
        for (int k = 0; k < cfg.nnodes; k++)
            printed += run_cell(K_DRAM_FLUSH, cfg.cpus[c], k);
    if (have_ocm)
        progress("ocm-evict cells");
    for (int c = 0; have_ocm && c < cfg.ncpus; c++)
        for (int k = 0; k < cfg.nnodes; k++)
            printed += run_cell(K_OCM_EVICT, cfg.cpus[c], k);

    /* F. the --last-cpus block: per CPU every kind. */
    if (cfg.nlast)
        progress("last-cpus block");
    for (int c = 0; c < cfg.nlast; c++) {
        for (int k = 0; have_ocm && k < cfg.nnodes; k++)
            printed += run_cell(K_OCM_FLUSH, cfg.last[c], k);
        idle_row(cfg.last[c]);
        for (int k = 0; have_dram && k < cfg.nnodes; k++)
            printed += run_cell(K_SLC, cfg.last[c], k);
        for (int k = 0; have_dram && k < cfg.nnodes; k++)
            printed += run_cell(K_DRAM_FLUSH, cfg.last[c], k);
        for (int k = 0; have_ocm && k < cfg.nnodes; k++)
            printed += run_cell(K_OCM_EVICT, cfg.last[c], k);
    }

    /* G. The row file is closed before the summary, so the summary and the exit status know of a
     * failure that only the close shows. */
    note("# meshmap: done cells=%d/%d", printed, requested);
    if (out != stdout) {
        close_checked(out, &out_failed, cfg.out_path);
        out = stdout;
    }
    char text[256], line[512];
    int64_t c[MAX_NODES];
    for (int k = 0; k < cfg.nnodes; k++)
        c[k] = cls.count[k];
    snprintf(line, sizeof line, "# summary: classify lines=%llu probed=%u ambiguous=%u unused=%u probe_loads=%d per_node=%s",
             (unsigned long long)cls.lines, cls.probed, cls.ambiguous, cls.unused, cls.loads, list_text(text, sizeof text, c, cfg.nnodes, ','));
    say("%.120s", line);
    say("# summary: mesh counters level=%d%s", mesh.level, cfg.no_perf ? " (--no-perf: fake homes)" : "");
    say("# summary: cells %d/%d in %.4f s%s", printed, requested, now_s() - t_main,
        out_failed || homes_failed ? "; a write to an output file failed (see stderr)" : "");
    if (!cfg.out_path)
        out_flush(); /* the rows went to stdout: a failed write there counts too */
    return exit_status(printed, requested);
}
