/*
 * inspect_pages.c -- sanity check for CPU pinning, memory policy, and
 *                    actual page placement of a test allocation.
 *
 * Purpose:
 *   Before we trust ptr_chase / bw_avx512 numbers, prove the test process
 *   is really pinned where we asked and the memory really lives on the
 *   NUMA node we asked. This program does ONLY that.
 *
 * Build:
 *   gcc -O2 -std=c11 -Wall -o inspect_pages inspect_pages.c -lnuma
 *
 * Run (no sudo needed for basic checks; root recommended for mlock):
 *   ./inspect_pages --cpu 0 --mem-node 0 --size 1G --hugepage 1g
 *
 * What it prints:
 *   - Current CPU (sched_getcpu) before and after pinning
 *   - Effective cpu affinity mask
 *   - get_mempolicy result
 *   - For each page in the allocation: which NUMA node it actually
 *     landed on (via move_pages with NULL nodes -> query mode)
 *   - Hugepage backing: by inspecting /proc/self/smaps for the mapping
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
#include <sys/sysinfo.h>
#include <linux/mempolicy.h>
#include <numa.h>
#include <numaif.h>
#include <getopt.h>
#include <ctype.h>

/* MAP_HUGE_* helpers: define if missing */
#ifndef MAP_HUGE_SHIFT
#define MAP_HUGE_SHIFT 26
#endif
#ifndef MAP_HUGE_2MB
#define MAP_HUGE_2MB (21 << MAP_HUGE_SHIFT)
#endif
#ifndef MAP_HUGE_1GB
#define MAP_HUGE_1GB (30 << MAP_HUGE_SHIFT)
#endif

/* move_pages syscall wrapper (libnuma has it, but use direct syscall
 * to avoid version-dependent signatures). */
static long sys_move_pages(int pid, unsigned long count, void **pages,
                           const int *nodes, int *status, int flags) {
    return syscall(SYS_move_pages, pid, count, pages, nodes, status, flags);
}

static size_t parse_size(const char *s) {
    char *end;
    double v = strtod(s, &end);
    while (*end && isspace((unsigned char)*end)) end++;
    size_t mul = 1;
    if (*end == 'k' || *end == 'K') mul = 1024UL;
    else if (*end == 'm' || *end == 'M') mul = 1024UL * 1024;
    else if (*end == 'g' || *end == 'G') mul = 1024UL * 1024 * 1024;
    else if (*end == 't' || *end == 'T') mul = 1024UL * 1024 * 1024 * 1024;
    return (size_t)(v * mul);
}

static void print_affinity(const char *label) {
    cpu_set_t set;
    CPU_ZERO(&set);
    if (sched_getaffinity(0, sizeof(set), &set) < 0) {
        perror("sched_getaffinity");
        return;
    }
    printf("  %s affinity:", label);
    int first = -1, last = -1, total = 0;
    int ncpus = get_nprocs_conf();
    for (int i = 0; i < ncpus; i++) {
        if (CPU_ISSET(i, &set)) {
            total++;
            if (first < 0) first = i;
            last = i;
        }
    }
    printf(" %d CPU(s) allowed [first=%d last=%d]\n", total, first, last);
}

static void print_mempolicy(void) {
    int mode = -1;
    unsigned long nodemask = 0;
    if (get_mempolicy(&mode, &nodemask, sizeof(nodemask) * 8, NULL, 0) < 0) {
        perror("get_mempolicy");
        return;
    }
    const char *mname = "UNKNOWN";
    switch (mode) {
        case MPOL_DEFAULT:   mname = "DEFAULT"; break;
        case MPOL_PREFERRED: mname = "PREFERRED"; break;
        case MPOL_BIND:      mname = "BIND"; break;
        case MPOL_INTERLEAVE:mname = "INTERLEAVE"; break;
        case MPOL_LOCAL:     mname = "LOCAL"; break;
        default: break;
    }
    printf("  mempolicy mode=%s nodemask=0x%lx\n", mname, nodemask);
}

static void print_smaps_for(void *addr) {
    /* find the line in /proc/self/smaps that covers `addr` and print
     * the AnonHugePages / FilePmdMapped / HugePages fields beneath it. */
    FILE *f = fopen("/proc/self/smaps", "r");
    if (!f) { perror("smaps"); return; }
    char line[512];
    uintptr_t want = (uintptr_t)addr;
    int in_block = 0;
    int printed_header = 0;
    while (fgets(line, sizeof(line), f)) {
        uintptr_t s, e;
        if (sscanf(line, "%lx-%lx", &s, &e) == 2) {
            in_block = (want >= s && want < e);
            if (in_block) {
                if (!printed_header) {
                    printf("  smaps for buffer:\n");
                    printed_header = 1;
                }
                printf("    %s", line);
            }
        } else if (in_block) {
            /* indent and print key/value lines we care about */
            if (strncmp(line, "Size:", 5) == 0 ||
                strncmp(line, "Rss:", 4) == 0 ||
                strncmp(line, "AnonHugePages:", 14) == 0 ||
                strncmp(line, "FilePmdMapped:", 14) == 0 ||
                strncmp(line, "HugePages_", 10) == 0 ||
                strncmp(line, "Hugetlb:", 8) == 0 ||
                strncmp(line, "VmFlags:", 8) == 0 ||
                strncmp(line, "KernelPageSize:", 15) == 0 ||
                strncmp(line, "MMUPageSize:", 12) == 0) {
                printf("    %s", line);
            }
        }
    }
    fclose(f);
}

static void usage(const char *p) {
    fprintf(stderr,
        "usage: %s --cpu N --mem-node N [--size BYTES] [--hugepage 1g|2m|none]\n"
        "       sizes accept K/M/G/T suffix, default 256M\n"
        "       hugepage default = 1g\n", p);
    exit(2);
}

int main(int argc, char **argv) {
    int cpu = -1, mem_node = -1;
    size_t size = 256UL * 1024 * 1024;
    const char *hp = "1g";

    static struct option opts[] = {
        {"cpu", required_argument, 0, 'c'},
        {"mem-node", required_argument, 0, 'm'},
        {"size", required_argument, 0, 's'},
        {"hugepage", required_argument, 0, 'h'},
        {0, 0, 0, 0}
    };
    int oi;
    int c;
    while ((c = getopt_long(argc, argv, "c:m:s:h:", opts, &oi)) != -1) {
        switch (c) {
            case 'c': cpu = atoi(optarg); break;
            case 'm': mem_node = atoi(optarg); break;
            case 's': size = parse_size(optarg); break;
            case 'h': hp = optarg; break;
            default: usage(argv[0]);
        }
    }
    if (cpu < 0 || mem_node < 0) usage(argv[0]);

    printf("== inspect_pages: cpu=%d mem-node=%d size=%zu hugepage=%s ==\n",
           cpu, mem_node, size, hp);

    /* numa availability check */
    if (numa_available() < 0) {
        fprintf(stderr, "ERROR: NUMA not available on this system\n");
        return 1;
    }
    printf("  numa_max_node=%d numa_num_configured_nodes=%d\n",
           numa_max_node(), numa_num_configured_nodes());

    /* before pinning */
    printf("Before pinning:\n");
    printf("  sched_getcpu() = %d\n", sched_getcpu());
    print_affinity("current");
    print_mempolicy();

    /* pin CPU */
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof(set), &set) < 0) {
        perror("sched_setaffinity");
        return 1;
    }
    /* let scheduler migrate us */
    sched_yield();

    printf("After pinning to cpu %d:\n", cpu);
    printf("  sched_getcpu() = %d\n", sched_getcpu());
    print_affinity("current");

    /* allocate */
    int flags = MAP_PRIVATE | MAP_ANONYMOUS;
    size_t pagesize = 4096;
    if (strcmp(hp, "1g") == 0) {
        flags |= MAP_HUGETLB | MAP_HUGE_1GB;
        pagesize = 1UL * 1024 * 1024 * 1024;
    } else if (strcmp(hp, "2m") == 0) {
        flags |= MAP_HUGETLB | MAP_HUGE_2MB;
        pagesize = 2UL * 1024 * 1024;
    } else if (strcmp(hp, "none") == 0) {
        /* default 4K pages, THP may promote */
    } else {
        fprintf(stderr, "unknown --hugepage value: %s\n", hp);
        return 2;
    }

    /* align size up to pagesize */
    if (size < pagesize) {
        fprintf(stderr,
            "ERROR: --size (%zu bytes = %.1f MiB) is smaller than one "
            "%s page (%zu bytes = %.0f MiB).\n"
            "       Either pick a larger --size or use --hugepage 2m / none.\n",
            size, size / (1024.0 * 1024.0),
            hp, pagesize, pagesize / (1024.0 * 1024.0));
        return 2;
    }
    if (size % pagesize) {
        size = ((size + pagesize - 1) / pagesize) * pagesize;
        printf("  rounded size up to %zu bytes\n", size);
    }

    void *buf = mmap(NULL, size, PROT_READ | PROT_WRITE, flags, -1, 0);
    if (buf == MAP_FAILED) {
        fprintf(stderr, "mmap(size=%zu, flags=0x%x) failed: %s\n",
                size, flags, strerror(errno));
        fprintf(stderr, "  hint: for --hugepage 1g, /proc/meminfo "
                "HugePages_Free must be >= %zu\n",
                size / (1UL << 30));
        return 1;
    }

    /* bind to requested node BEFORE touching pages */
    unsigned long nodemask = 1UL << mem_node;
    if (mbind(buf, size, MPOL_BIND, &nodemask,
              sizeof(nodemask) * 8, MPOL_MF_STRICT | MPOL_MF_MOVE) < 0) {
        /* MOVE may fail if pages haven't been faulted yet; try without */
        if (mbind(buf, size, MPOL_BIND, &nodemask,
                  sizeof(nodemask) * 8, 0) < 0) {
            perror("mbind");
            return 1;
        }
    }

    /* fault every page */
    volatile char *p = (volatile char *)buf;
    for (size_t off = 0; off < size; off += pagesize) {
        p[off] = (char)off;
    }

    printf("Allocation:\n");
    printf("  base=%p size=%zu pagesize=%zu npages=%zu\n",
           buf, size, pagesize, size / pagesize);
    print_smaps_for(buf);

    /* query actual placement of each page via move_pages */
    size_t npages = size / pagesize;
    void **addrs = calloc(npages, sizeof(void *));
    int *status = calloc(npages, sizeof(int));
    if (!addrs || !status) {
        perror("calloc"); return 1;
    }
    for (size_t i = 0; i < npages; i++) {
        addrs[i] = (char *)buf + i * pagesize;
    }
    if (sys_move_pages(0, npages, addrs, NULL, status, 0) < 0) {
        perror("move_pages(query)");
        /* keep going; maybe partial info */
    }

    /* tabulate */
    int max_node = numa_max_node();
    long *count_by_node = calloc(max_node + 2, sizeof(long));
    long error_count = 0;
    for (size_t i = 0; i < npages; i++) {
        if (status[i] < 0) error_count++;
        else if (status[i] <= max_node) count_by_node[status[i]]++;
        else count_by_node[max_node + 1]++;
    }
    printf("  page placement (move_pages query):\n");
    for (int n = 0; n <= max_node; n++) {
        if (count_by_node[n] > 0) {
            printf("    node %d: %ld pages (%.1f%%)\n",
                   n, count_by_node[n],
                   100.0 * count_by_node[n] / npages);
        }
    }
    if (count_by_node[max_node + 1] > 0)
        printf("    unknown/high: %ld pages\n", count_by_node[max_node + 1]);
    if (error_count > 0)
        printf("    error: %ld pages\n", error_count);

    /* verdict */
    long good = count_by_node[mem_node];
    printf("Verdict:\n");
    if (sched_getcpu() == cpu && good == (long)npages) {
        printf("  OK: pinned to cpu %d, all %zu pages on node %d\n",
               cpu, npages, mem_node);
    } else {
        printf("  WARN: cpu=%d (wanted %d), %ld/%zu pages on node %d "
               "(wanted all)\n",
               sched_getcpu(), cpu, good, npages, mem_node);
    }

    free(addrs); free(status); free(count_by_node);
    munmap(buf, size);
    return 0;
}
