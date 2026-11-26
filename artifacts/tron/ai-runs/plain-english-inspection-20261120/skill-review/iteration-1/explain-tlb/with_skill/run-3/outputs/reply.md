## Short version

A TLB (translation lookaside buffer) is a small CPU cache of recent address translations. On a big-memory server it covers a tiny share of memory, so many accesses need a slow table lookup. Huge pages (2 MiB or 1 GiB) raise that coverage 512 times or more, but risk pauses and wasted memory.

## 1. What a TLB is

- A program uses virtual addresses. The CPU translates each one to a physical address in RAM before the access.
- Memory is divided into pages, and the default page size on x86-64 is 4 KiB.
- The page table stores the translation for every page. On x86-64 it is a tree with 4 levels, or 5 on some newer servers [Ref1].
- The TLB keeps the most recently used translations inside the CPU core. A hit (the translation is in the TLB) adds almost no time.
- A miss (the translation is absent) starts a page walk. The CPU then reads one table per tree level. With 4 levels, that is up to 4 memory reads.

```
                       hit: no extra memory read
 virtual  --> [ TLB ] --------------------------> physical
 address         |                                address
                 | miss                              ^
                 v                                   |
              [ page walk: up to 4 table reads ] ----+
```

The result of a walk is stored in the TLB for the next access.

## 2. Why misses cost a lot on a big-memory server

| Page size | Covered by 2,048 TLB entries | Table reads per walk | Last-level tables to map 512 GiB |
|---|---|---|---|
| 4 KiB | 8 MiB | up to 4 | 1 GiB |
| 2 MiB | 4 GiB | up to 3 | 2 MiB |
| 1 GiB | depends on CPU model | up to 2 | 4 KiB |

The count of 2,048 entries is an example size. The real count differs by CPU model.

- The TLB covers a tiny share of memory. With 4 KiB pages, 2,048 entries cover 8 MiB. That is 0.0015% of a 512 GiB server.
- The page tables do not fit in the CPU cache. Mapping 512 GiB needs 1 GiB of last-level tables. So the last read of a walk often goes to RAM.
- A read from RAM takes about 100 ns (est.). A read from the CPU cache takes 1 to 20 ns (est.).
- Programs that access a large memory range in random order miss most often. Examples are in-memory databases, large hash tables and graph searches.
- Inside a virtual machine, one walk can need up to 24 memory reads [Ref3]. Each table address inside the virtual machine also needs a translation by the host's tables.

## 3. How huge pages help

A huge page is one page of 2 MiB or 1 GiB, where a normal page is 4 KiB.

- One TLB entry covers 512 times more memory with 2 MiB pages. With 1 GiB pages it covers 262,144 times more.
- The walk is one level shorter for 2 MiB pages and two levels shorter for 1 GiB pages.
- The page tables shrink by the same factor, so they fit in the CPU cache. The remaining misses then cost less.
- There are fewer page faults. A page fault is the kernel step that supplies memory on first use. One fault now supplies 2 MiB, not 4 KiB.

One study measured the effect on graph500 (a graph search benchmark) [Ref2]:

```
Share of CPU cycles spent on TLB misses, graph500

 4 KiB pages |##########################  51.1%
 2 MiB pages |#####                        9.9%
 1 GiB pages |#                            1.5%
```

One `#` is 2 percentage points.

- The study used 2013 hardware with smaller TLBs than today's servers.
- I quote these three values from memory. Check them against the paper before they go on a slide.
- Insufficient data for your own workload. Section 5 names the measurement.

Linux offers two ways to get huge pages [Ref4] [Ref6]:

| | Reserved huge pages (hugetlbfs interface) | Transparent huge pages (THP) |
|---|---|---|
| Who asks for them | the application, explicitly | the kernel, automatically |
| Sizes on x86-64 | 2 MiB and 1 GiB | 2 MiB |
| Source of the memory | reserved in advance | free memory at the time of use |
| When no huge page is free | the request fails | the kernel uses 4 KiB pages, without any message |
| Can be swapped to disk | no | yes |

THP has three modes: `always`, `madvise` (only regions that the application marks) and `never` [Ref4].

## 4. What can go wrong

**Transparent huge pages**

- A page fault can stall. The kernel may first move other pages to free a contiguous 2 MiB block. The THP setting named `defrag` controls whether the fault waits for that [Ref4].
- Memory use can grow. A program that writes 1 byte into an empty 2 MiB region receives the full 2 MiB. A kernel thread named khugepaged also merges partly empty regions into huge pages [Ref4].
- A write after `fork()` (the call that duplicates a process) costs more. The copy and the original share pages until one of them writes. The kernel then copies or splits a 2 MiB page instead of copying 4 KiB [Ref5].
- The speedup can end without an error message. When no contiguous 2 MiB block is free, the kernel uses 4 KiB pages. The counters `AnonHugePages` (huge pages in use) and `thp_fault_fallback` (fallbacks to 4 KiB) show this [Ref4].

**Reserved huge pages**

- The reserved memory is unavailable to everything else. The file cache and other programs cannot use it, even when it is unused [Ref6].
- The reservation size must be right. A reservation that is too large leaves too little memory for everything else. A reservation that is too small makes the application's request fail.
- A reservation after boot can return fewer pages than requested. The kernel needs contiguous free memory for each page [Ref6]. So read the count back, and reserve 1 GiB pages at boot.
- The reservation is split across NUMA nodes (CPU groups with their own local memory). A process bound to one node can find that node's share empty. Other nodes may still have free huge pages [Ref6].
- Memory monitors can miss this memory. Reserved huge pages are not counted in RSS (resident set size, the usual per-process figure). Container memory limits do not cover them by default [Ref7].

**Both kinds**

- The first write to a huge page takes longer. The kernel fills the whole 2 MiB or 1 GiB with zeros in one fault.
- Some workloads gain nothing. A program that reads memory in order already causes few TLB misses.
- 1 GiB pages are not always faster than 2 MiB pages. Some CPUs have far fewer TLB entries for 1 GiB pages.

## 5. The measurement that answers "how much do we gain"

Run this before and after the change, under the same load. It uses `perf` (the Linux profiling tool).

```
# CPU cycles with a page walk in progress (recent Intel CPUs)
perf stat -e cycles \
          -e dtlb_load_misses.walk_active \
          -e dtlb_store_misses.walk_active \
          -p <pid> -- sleep 30

# current huge page state
grep -i huge /proc/meminfo
cat /sys/kernel/mm/transparent_hugepage/enabled
cat /sys/kernel/mm/transparent_hugepage/defrag
```

- Add the two `walk_active` counts and divide by `cycles`. The result is the share of CPU time with a page walk in progress.
- A small share before the change means huge pages cannot gain much.
- The event names differ on other CPUs. `perf list | grep -i tlb` shows the names there.

## References

- [Ref1] Intel 64 and IA-32 Architectures Software Developer's Manual, Volume 3A, chapter 4, "Paging".
- [Ref2] Basu, Gandhi, Chang, Hill, Swift, "Efficient Virtual Memory for Big Memory Servers", ISCA 2013.
- [Ref3] Bhargava, Serebrin, Spadini, Manne, "Accelerating Two-Dimensional Page Walks for Virtualized Systems", ASPLOS 2008.
- [Ref4] Linux kernel documentation, "Transparent Hugepage Support", https://docs.kernel.org/admin-guide/mm/transhuge.html
- [Ref5] Redis documentation, "Diagnosing latency issues", section "Latency induced by transparent huge pages".
- [Ref6] Linux kernel documentation, "HugeTLB Pages", https://docs.kernel.org/admin-guide/mm/hugetlbpage.html
- [Ref7] Linux kernel documentation, "Control Group v2", HugeTLB sections, https://docs.kernel.org/admin-guide/cgroup-v2.html