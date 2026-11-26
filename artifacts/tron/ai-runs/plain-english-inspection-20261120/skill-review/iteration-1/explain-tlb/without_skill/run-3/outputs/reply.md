## Short version

A TLB (translation lookaside buffer) is a small cache inside the CPU that stores recent translations from virtual to physical memory addresses. With 4 KiB pages it covers about 8 MiB of a server that holds hundreds of GiB, and each miss costs up to 4 extra memory reads. Huge pages (2 MiB or 1 GiB) make each entry cover 512 or 262,144 times more memory, and the risks are memory growth, long pauses, and allocation failures.

## Words used here

- **Page**: the block of memory that the operating system maps as one unit. The default size on x86-64 is 4 KiB.
- **Page table**: the tree in memory that records which physical address backs each page. x86-64 uses 4 levels [Ref1].
- **Page walk**: the CPU reads the page table level by level to find one translation.
- **THP (transparent huge pages)**: the Linux feature that gives 2 MiB pages to a program automatically [Ref5].
- **hugetlbfs**: the Linux feature that reserves a fixed pool of huge pages, which a program requests explicitly [Ref6].
- **NUMA (non-uniform memory access)**: a server layout where each CPU socket has its own local memory.

## 1. What a TLB is

Every memory access uses a virtual address. The CPU must translate it to a physical address first.

```
virtual addr --> TLB --hit--> physical addr   (almost free)
                  |
                 miss
                  v
        page walk: L4 -> L3 -> L2 -> L1 --> physical addr
                   (up to 4 memory reads)
```

## 2. Why misses are expensive on a big-memory server

- **Small reach.** A recent Intel server core has about 2,048 second-level TLB entries [Ref2]. 2,048 entries x 4 KiB = 8 MiB, which is about 0.0015% of a 512 GiB memory.
- **The page table does not fit in the CPU caches.** Mapping 512 GiB with 4 KiB pages needs 1 GiB of last-level table entries. The last read of a walk therefore often goes to DRAM (est. 60 to 100 ns).
- **Virtual machines multiply the cost.** The guest table and the host table are both walked. One miss can need up to 24 memory reads [Ref3].
- **Table entries take cache space.** That space is then not available for program data.

One published study measured about 10% of execution cycles for memcached and about 51% for graph500 (a graph benchmark) spent on TLB misses with 4 KiB pages [Ref4].

## 3. How huge pages help

```
4 KiB page:  L4 -> L3 -> L2 -> L1 -> page    4 reads
2 MiB page:  L4 -> L3 -> L2 -------> page    3 reads
1 GiB page:  L4 -> L3 -------------> page    2 reads
```

| Page size | TLB reach (example core) | Last-level table for 512 GiB |
|---|---|---|
| 4 KiB | 8 MiB (2,048 entries) | 1 GiB |
| 2 MiB | 4 GiB (2,048 entries) | 2 MiB |
| 1 GiB | 1 TiB (1,024 entries) | 4 KiB |

- Each entry covers more memory, so more accesses hit.
- Each walk is shorter.
- The table becomes small enough to stay in the CPU cache, so the remaining misses are cheap.
- The program takes 1 page fault per 2 MiB instead of 512.

## 4. What can go wrong

1. **Memory growth (THP).** A program touches 1 byte and receives 2 MiB. Programs with sparse heaps use much more physical memory. Avoid it with the `madvise` THP mode, which gives huge pages only to regions the program marks [Ref5].
2. **Long pauses (THP).** The first touch must zero 2 MiB (est. 50 to 200 us) instead of 4 KiB. If free memory is fragmented, the kernel may move pages inside the page fault to build a 2 MiB block. The `defrag` setting controls this [Ref5].
3. **Fallback without an error (THP).** When no free 2 MiB block exists, the kernel uses 4 KiB pages and reports nothing. Performance then differs between runs and often drops with uptime. Check `AnonHugePages` in `/proc/<pid>/smaps` and `thp_fault_fallback` in `/proc/vmstat`.
4. **Wrong pool size (hugetlbfs).** Reserved memory is unavailable to every other program, even when unused.
   - If the pool is too small, `mmap` fails or the program is killed with SIGBUS (the bus-error signal) [Ref6].
   - 1 GiB pages usually must be reserved at boot.
   - On a shared server the pool is system-wide, so agree the size with the other users.
5. **Wrong NUMA node.** Each node has its own pool. If the pages are on the other socket, every access is slower. Check `/sys/devices/system/node/node*/hugepages/`.
6. **`fork` and copy-on-write (copy a shared page at first write).** The kernel either copies 2 MiB or splits the huge page into 4 KiB pages. The first adds latency. The second removes the benefit. Redis documents this problem [Ref7].
7. **Splitting.** `mprotect`, `munmap`, or swap on part of a THP page splits it into 4 KiB pages. The benefit is lost without a message. hugetlbfs pages cannot be swapped at all.
8. **Few TLB entries for 1 GiB pages.** Some older cores have only 4. Check before choosing 1 GiB.

## Insufficient data

- **TLB sizes of your CPU.** The entry counts above are examples from one Intel core. `cpuid -1 | grep -i tlb` on the target server gives the real values.
- **Miss cost for your workload.** On Intel cores, this measures it:

```
perf stat -e dtlb_load_misses.walk_active,\
dtlb_store_misses.walk_active,itlb_misses.walk_active,cycles \
  -p <pid> -- sleep 10
```

The sum of the three `walk_active` counts divided by `cycles` is the fraction of time spent in page walks.

Not covered: virtual-machine live migration, hardware memory-error handling, and same-page merging. Each interacts with huge pages.

## References

I cite these from memory and did not open them in this session.

- [Ref1] Intel 64 and IA-32 Architectures Software Developer's Manual, Volume 3A, Chapter 4 "Paging".
- [Ref2] Intel 64 and IA-32 Architectures Optimization Reference Manual, TLB parameters of the Golden Cove core.
- [Ref3] Bhargava et al., "Accelerating Two-Dimensional Page Walks for Virtualized Systems", ASPLOS 2008.
- [Ref4] Basu et al., "Efficient Virtual Memory for Big Memory Servers", ISCA 2013.
- [Ref5] Linux kernel documentation, "Transparent Hugepage Support", https://docs.kernel.org/admin-guide/mm/transhuge.html
- [Ref6] Linux kernel documentation, "HugeTLB Pages", https://docs.kernel.org/admin-guide/mm/hugetlbpage.html
- [Ref7] Redis documentation, "Diagnosing latency issues", section on transparent huge pages.