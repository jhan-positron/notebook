## Short version

A TLB (translation lookaside buffer) is a small CPU cache that stores recent virtual-to-physical address translations. On a big-memory server it covers a tiny share of memory, and each miss costs up to 4 extra memory reads. Huge pages make each TLB entry cover at least 512 times more memory, but they can add latency spikes, memory growth, and allocation failures.

## Words used here

- **Page**: a fixed-size block of memory, 4 KB by default on x86-64.
- **Page table**: the in-memory tree that records which physical page backs each virtual page. It has 4 levels on x86-64, named L4 (root) to L1 here.
- **Page walk**: the CPU reads the page table level by level to find one translation.
- **TLB reach**: entry count times page size. This is the memory the TLB can translate without a walk.
- **Huge page**: a 2 MB or 1 GB page on x86-64.
- **THP (Transparent Huge Pages)**: the Linux feature that gives 2 MB pages to a process automatically.
- **hugetlbfs**: the Linux feature where the administrator reserves a fixed pool of huge pages, and the application requests them explicitly.
- **NUMA (non-uniform memory access)**: a server layout where each CPU socket has its own memory, and memory on another socket is slower to reach.

## 1. What a TLB is

- Programs use virtual addresses, and memory chips use physical addresses.
- The CPU translates on every memory access.
- The TLB stores the results of recent page walks.

```
                   hit: no extra memory read
virtual --> [TLB] --------------------------> physical
address       |                                address
              | miss                              ^
              v                                   |
        [page walk: L4 -> L3 -> L2 -> L1] --------+
         up to 4 memory reads, result saved in TLB
```

## 2. Why misses are expensive on a big-memory server

Example: 512 GB of mapped memory and a TLB with 2,048 entries (est. for a recent Intel server core).

| Page size | TLB reach | Share of 512 GB | Last-level page tables |
|---|---|---|---|
| 4 KB | 8 MB | 0.0015% | 1 GB |
| 2 MB | 4 GB | 0.78% | 2 MB |
| 1 GB | 1 GB per entry, count varies by CPU | varies | 4 KB |

- **Small reach.** With 4 KB pages, the TLB covers 8 MB of 512 GB. Random access over a large heap then misses on almost every access.
- **Up to 4 reads per miss** [Ref1]. The CPU also caches the upper tree levels. The L1 read is then the main cost.
- **Page tables do not fit in the CPU cache.** They take 1 GB in this example. The L1 read then goes to main memory, which costs about 100 ns (est., about 300 cycles on a 3 GHz core).
- **Virtual machines make it worse.** A walk inside a virtual machine can take up to 24 memory reads [Ref2].
- **NUMA adds latency.** The page table can sit on the other socket.
- **Published measurement.** Big-memory workloads spent up to 10% of execution cycles on TLB misses, even with large pages [Ref3]. The same paper reports larger shares with 4 KB pages.

## 3. How huge pages help

```
4 KB page:  L4 -> L3 -> L2 -> L1 -> data    4 reads
2 MB page:  L4 -> L3 -> L2 -------> data    3 reads
1 GB page:  L4 -> L3 -------------> data    2 reads
```

- **More reach per entry.** One 2 MB entry covers 512 times more memory than a 4 KB entry, and one 1 GB entry covers 262,144 times more.
- **Shorter walk.** It takes 3 reads for 2 MB pages and 2 reads for 1 GB pages.
- **Smaller page tables.** They take 2 MB instead of 1 GB in the example. The walk reads then hit the CPU cache.
- **Fewer page faults.** One fault maps 2 MB instead of 4 KB.
- **Limit.** 2 MB pages reach only 4 GB in the example. Random access over all 512 GB still misses often, but each miss is cheaper.

Linux offers two ways to get huge pages [Ref4][Ref5]:

| | THP | hugetlbfs |
|---|---|---|
| Page sizes | 2 MB | 2 MB, 1 GB |
| Who requests | Kernel, automatic | Application, explicit |
| Memory reserved in advance | No | Yes |
| When no huge page is free | Silent fallback to 4 KB | Request fails |

## 4. What can go wrong

| # | Problem | What you see | Usual control |
|---|---|---|---|
| 1 | Compaction during a page fault: the kernel moves pages to build a free 2 MB block while the thread waits | Latency spikes of milliseconds or more (est.) | Set THP `defrag` to `madvise` or `defer`, or use a hugetlbfs pool |
| 2 | Sparse use: a process touches a few bytes and gets a full 2 MB page | Physical memory use grows with no code change | Set THP `enabled` to `madvise` and opt in only for large, dense regions |
| 3 | Silent fallback: memory is fragmented after long uptime | Speed differs between runs and drops with uptime | Reserve the pool at boot and check the counters after each run |
| 4 | hugetlbfs pool size: reserved pages are unavailable to everything else | Too large: out-of-memory kills while the pool is free. Too small: `mmap` fails or the process gets SIGBUS | Size the pool from measured need |
| 5 | NUMA placement: the pool is split per socket | Pages come from the far socket | Reserve per node under `/sys/devices/system/node/node*/hugepages/` |
| 6 | Copy after fork: the first write copies 2 MB instead of 4 KB | Stalls in processes that fork to take snapshots [Ref6] | Disable THP for those processes |
| 7 | Few 1 GB TLB entries on older CPUs | 1 GB pages give less gain than expected | Check the entry counts with `cpuid` |

- 1 GB pages normally need reservation on the kernel command line at boot [Ref5].
- THP may already be on, so check the current setting before the review.

## Checks on the target server

```bash
# Current THP mode
cat /sys/kernel/mm/transparent_hugepage/enabled
# TLB entry counts per page size
cpuid -1 | grep -i tlb
# Cycles spent in page walks (Intel event name), for a running workload
perf stat -e cycles,dtlb_load_misses.walk_active -p <pid> -- sleep 30
# Did huge pages get used, and did fallback or compaction stalls occur
grep -E 'AnonHugePages|HugePages_' /proc/meminfo
grep -E 'thp_fault_alloc|thp_fault_fallback|compact_stall' /proc/vmstat
```

If `walk_active / cycles` is only a few percent, huge pages cannot gain more than that share.

## Insufficient data

- I ran nothing on your server. All numbers above come from memory of the sources, not from a measurement.
- The TLB entry counts for your CPU are unknown. The `cpuid` command above gives them.
- The share of cycles your workload spends in page walks is unknown. The `perf stat` command above gives it.

## References

- [Ref1] Intel 64 and IA-32 Architectures Software Developer's Manual, Volume 3A, chapter "Paging".
- [Ref2] Bhargava et al., "Accelerating Two-Dimensional Page Walks for Virtualized Systems", ASPLOS 2008.
- [Ref3] Basu et al., "Efficient Virtual Memory for Big Memory Servers", ISCA 2013.
- [Ref4] Linux kernel documentation, "Transparent Hugepage Support", https://docs.kernel.org/admin-guide/mm/transhuge.html
- [Ref5] Linux kernel documentation, "HugeTLB Pages", https://docs.kernel.org/admin-guide/mm/hugetlbpage.html
- [Ref6] Redis documentation, "Diagnosing latency issues", section on transparent huge pages.