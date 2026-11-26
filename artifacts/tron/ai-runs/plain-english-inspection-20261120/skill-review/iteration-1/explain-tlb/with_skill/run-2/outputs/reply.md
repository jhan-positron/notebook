## Short version

The TLB (translation lookaside buffer) is a small CPU cache of address translations. A big-memory server misses it often, and each miss can cost a slow read from main memory. Huge pages reduce the misses, but they can cause stalls, memory growth and failed allocations.

## Words used here

- A **page** is the fixed-size block that one translation covers. The default size on x86-64 is 4 KiB.
- The **page table** is the per-process tree that holds all translations. It has 4 levels on x86-64, or 5 on some newer CPUs.
- A **page fault** is the kernel call that gives a page its physical memory on first use.
- A **huge page** is a page of 2 MiB or 1 GiB.
- **THP** (Transparent Huge Pages) is the Linux feature that gives a process 2 MiB pages automatically.
- **hugetlbfs** is the Linux feature that reserves a fixed pool of huge pages.
- **Compaction** is the kernel moving pages to build one large free block.
- **RSS** (resident set size) is the physical memory that a process holds.
- **NUMA** (non-uniform memory access) means each CPU socket has its own memory, called a node.
- **est.** marks an estimate. No value below was measured on your server.

## 1. What a TLB is

- A program uses virtual addresses. The CPU must translate each one to a physical address (a location in main memory).
- The page table holds the translations. A page walk (the CPU reading the table levels) finds one translation [Ref1].
- The TLB stores recent results. So a repeated access to the same page skips the walk.
- One TLB entry covers one page, and the entry count is fixed in hardware. Recent Intel server cores hold 2,048 entries in the second-level TLB [Ref2].

```
virtual      +-----+  hit
address ---> | TLB | -------------------------> physical address
             +-----+
                | miss
                v
             page walk: level 4 -> 3 -> 2 -> 1 --> physical address
```

The walk takes up to 4 memory reads. The TLB then stores the result.

## 2. Why misses are expensive on a big-memory server

The example uses 2,048 TLB entries and 256 GiB of mapped memory. The TLB reach is the memory that all its entries cover together.

```
mapped memory      256 GiB  ################################  100%
reach, 2 MiB pages   4 GiB  #                                 1.6%
reach, 4 KiB pages   8 MiB                                    0.003%
```

One character is 8 GiB. The 4 GiB bar is rounded up to one character. The 8 MiB bar is too small to draw.

- With 4 KiB pages, 2,048 entries cover 8 MiB, which is 0.003% of 256 GiB. So a workload that reads addresses across the whole 256 GiB misses on almost every read.
- The page table does not fit in the CPU cache. Its last level alone is 512 MiB for 256 GiB of 4 KiB pages.
- So a walk often reads from main memory. That read takes est. 100 ns, against est. 1 to 2 ns for a cache hit.
- The data read itself follows the walk. So one access can need two slow reads instead of one.
- The CPU also caches the upper table levels, so many walks need fewer than 4 reads. The last-level read is the one that most often goes to main memory.
- Table entries loaded by walks take CPU cache space away from program data.
- In a virtual machine, one miss can need up to 24 memory reads instead of 4 [Ref3].
- One study measured big-memory workloads that spent up to 10% of execution cycles on TLB misses, even with large pages [Ref4].

## 3. How huge pages help

| Page size | Reach of 2,048 entries | Last table level for 256 GiB | Memory reads per walk (max) |
|---|---|---|---|
| 4 KiB | 8 MiB | 512 MiB | 4 |
| 2 MiB | 4 GiB | 1 MiB | 3 |
| 1 GiB | depends on the CPU | 2 KiB | 2 |

Add 1 read per walk on a CPU that uses 5-level paging.

- One 2 MiB entry covers 512 times more memory than one 4 KiB entry. The same 2,048 entries then reach 4 GiB.
- The walk is shorter by one read for 2 MiB pages, and by two for 1 GiB pages [Ref1].
- The last table level shrinks from 512 MiB to 1 MiB, so it fits in the CPU cache. The misses that remain then cost less.
- Page faults on first use drop by a factor of 512. One fault maps 2 MiB instead of 4 KiB.
- Misses do not disappear. A reach of 4 GiB is still only 1.6% of 256 GiB. The study above measured its 10% with large pages in use [Ref4].

Linux offers two ways to get huge pages [Ref5] [Ref6].

| | THP | hugetlbfs pool |
|---|---|---|
| Page sizes | 2 MiB | 2 MiB and 1 GiB |
| Who allocates | the kernel, automatically | an administrator reserves the pool |
| Change to the program | none, or one `madvise` system call | an `mmap` call with the `MAP_HUGETLB` flag |
| When no huge page is free | uses 4 KiB pages, with no error | the request fails |
| Unused huge-page memory | stays available to the system | stays reserved |

## 4. What can go wrong

With THP:

- A page fault can stall while the kernel runs compaction to build a free 2 MiB block. The thread that caused the fault waits during that work. The THP `defrag` setting controls when this happens [Ref5].
- Memory use can grow. A process that touches one byte of a 2 MiB range receives the full 2 MiB. So RSS rises, and a container can reach its memory limit sooner.
- When memory is fragmented, the kernel gives 4 KiB pages instead and reports no error. So the same test can run slower after long uptime than after a reboot.
- A program that calls `fork()` shares its huge pages with the child process. The first write to each one forces a 2 MiB copy or a split into 4 KiB pages. Redis documents large latency increases from this pattern [Ref7].
- The first use of a huge page clears 2 MiB in one fault. That fault takes longer than a 4 KiB fault, although the total fault time falls.

THP has three modes: `always`, `madvise` and `never` [Ref5]. In `madvise` mode, only memory ranges that the program requests get huge pages. This confines the risks above to those ranges.

With a hugetlbfs pool:

- The pool is removed from general use, even when no program uses it. The file cache and other processes cannot take that memory. On a shared server, that memory is taken from every other user.
- A pool that is too small makes `mmap` fail. A pool that is too large leaves too little memory for the rest of the system.
- Growing the pool at run time can fail on a fragmented system. The kernel then gives fewer pages than requested and reports no error. So read the pool size back, or reserve the pool at boot [Ref6].
- The kernel spreads the pool evenly across NUMA nodes by default [Ref6]. A process bound to one node can use only that node's share. It receives SIGBUS (a fatal signal) at first use when that share is empty.
- 1 GiB pages are not always faster than 2 MiB pages. Some CPUs hold few TLB entries for 1 GiB pages. An older Intel core (Skylake) holds 16 in its second level, which reach only 16 GiB [Ref2].

## 5. Checks to run before the decision

Insufficient data: this answer holds no measurement from your server or workload. The gain depends on how the workload accesses memory. These checks give the missing data.

1. Measure the share of cycles that page walks take today (Intel event names):

   ```
   perf stat -p <pid> \
     -e cycles \
     -e dtlb_load_misses.walk_active \
     -e dtlb_store_misses.walk_active \
     -- sleep 30
   ```

   The two walk counts divided by `cycles` give that share. It is the approximate upper limit of the direct gain.
2. Confirm that huge pages are in use during each test run. Read `AnonHugePages` in `/proc/meminfo` for THP, or `HugePages_Free` for a pool.
3. Read `thp_fault_fallback` in `/proc/vmstat` before and after each run. It rises each time THP used 4 KiB pages instead [Ref5].
4. Compare the slowest requests before and after, not only the average. Compaction stalls change the slowest requests more than the average.

## References

- [Ref1] Intel 64 and IA-32 Architectures Software Developer's Manual, Volume 3A, chapter 4 "Paging".
- [Ref2] Intel 64 and IA-32 Architectures Optimization Reference Manual, TLB parameters per core generation.
- [Ref3] Bhargava et al., "Accelerating Two-Dimensional Page Walks for Virtualized Systems", ASPLOS 2008.
- [Ref4] Basu et al., "Efficient Virtual Memory for Big Memory Servers", ISCA 2013.
- [Ref5] Linux kernel documentation, "Transparent Hugepage Support", docs.kernel.org/admin-guide/mm/transhuge.html
- [Ref6] Linux kernel documentation, "HugeTLB Pages", docs.kernel.org/admin-guide/mm/hugetlbpage.html
- [Ref7] Redis documentation, "Diagnosing latency issues", section on transparent huge pages.

I wrote these references from memory and did not open them in this session. Confirm the TLB entry counts for your CPU with the `cpuid` tool before you quote them.