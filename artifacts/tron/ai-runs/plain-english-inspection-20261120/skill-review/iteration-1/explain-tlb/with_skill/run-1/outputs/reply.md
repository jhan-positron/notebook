## Short version

A TLB (translation lookaside buffer) is a small cache in the CPU that stores recent address translations. On a big-memory server the TLB covers a tiny share of memory, so many memory accesses need a slow lookup. Huge pages make each TLB entry cover 512 times more memory, but they can add latency and waste memory.

## Words used here

| Term | Meaning |
|---|---|
| Virtual address | The address that a program uses. |
| Physical address | The real location of the data in RAM. |
| Page | The unit of address translation. The default size is 4 KiB on x86-64 (64-bit Intel and AMD CPUs). |
| Page table | The structure in RAM that maps virtual pages to physical pages. It is a tree with 4 levels, or 5 on some recent servers. |
| Page walk | The lookup through the page table levels that the CPU runs after a TLB miss. |
| TLB reach | The amount of memory that all TLB entries cover together. It equals the entry count times the page size. |
| Huge page | A page of 2 MiB or 1 GiB instead of 4 KiB. |
| THP | Transparent huge pages. The Linux kernel picks 2 MiB pages automatically. |
| hugetlbfs | The Linux interface to a pool of huge pages that the administrator reserves in advance. |
| Compaction | The kernel moves pages in RAM to create one free contiguous block. |
| NUMA | Non-uniform memory access. Each CPU socket has its own local RAM, and RAM of another socket is slower to reach. |
| KiB, MiB, GiB, TiB | 2^10, 2^20, 2^30 and 2^40 bytes. |

## 1. What a TLB is

- A program uses virtual addresses, and RAM uses physical addresses. The CPU translates the address on every memory access.
- The page table holds the mapping. A read of the page table on every access would be too slow.
- The TLB stores the results of recent translations, one entry per page.
- A hit returns the physical address with no extra memory read. A miss starts a page walk.

```
virtual        +-----+   hit: no extra memory read       physical
address  ----> | TLB | --------------------------------> address
               +-----+                                      ^
                  | miss                                    |
                  v                                         |
               +---------------------------------+          |
               | page walk: up to 4 memory reads | ---------+
               | level 4 -> 3 -> 2 -> 1          |
               +---------------------------------+
```

After the walk, the CPU stores the result in the TLB. The next access to the same page is a hit.

## 2. Why TLB misses are expensive on a big-memory server

- The TLB is small. A recent Intel server core holds 1,536 to 2,048 entries in its largest TLB level [Ref1].
- The reach is tiny compared with the data. 2,048 entries of 4 KiB pages cover 8 MiB. That is 0.0015% of a 512 GiB data set, so a random access almost always misses.
- A miss costs up to 4 memory reads in sequence. Each read needs the result of the previous one, so they cannot run in parallel. The CPU caches the upper levels, so the last 1 or 2 reads cause most of the cost.
- The page table is too large for the CPU cache. A 512 GiB mapping with 4 KiB pages needs 1 GiB of final-level tables. So the last read often goes to RAM, at about 100 ns est. (about 300 CPU cycles at 3 GHz).
- Page table entries also occupy CPU cache space. They remove program data from the cache.
- A virtual machine raises the cost. With nested paging (the hardware scheme for guest page tables), one walk can need up to 24 memory reads [Ref2].

Basu and others measured big-memory workloads with 4 KiB pages. A graph workload spent about 51% of its CPU cycles on TLB misses [Ref3]. With 2 MiB pages the share fell to about 10%.

You can measure the same share on your own workload:

```
perf stat -p <pid> \
  -e cycles \
  -e dtlb_load_misses.walk_active \
  -e dtlb_store_misses.walk_active \
  -- sleep 30
```

Each `walk_active` event counts the CPU cycles during which a page walk runs. Divide their sum by `cycles` to get the approximate share. These are Intel event names, and `perf list` shows the names on the target CPU.

## 3. How huge pages help

```
Share of a 512 GiB data set that 2,048 TLB entries cover
(40 characters = 100%)

4 KiB pages |                                          0.0015%
2 MiB pages |                                          0.78%
1 GiB pages |########################################  100%
```

The first two bars are shorter than one character. Only 1 GiB pages cover the whole data set.

| Page size | TLB reach (2,048 entries) | Memory reads per walk | Final-level tables for 512 GiB |
|---|---|---|---|
| 4 KiB | 8 MiB | up to 4 | 1 GiB |
| 2 MiB | 4 GiB | up to 3 | 2 MiB |
| 1 GiB | 2 TiB | up to 2 | 4 KiB |

The chart and table assume 2,048 entries for every page size and a 4-level page table.

- A 2 MiB page makes one TLB entry cover 512 times more memory. A 1 GiB page covers 262,144 times more.
- The walk becomes shorter. It stops 1 level earlier for 2 MiB pages and 2 levels earlier for 1 GiB pages.
- The page tables shrink from 1 GiB to 2 MiB in the example. They then fit in the CPU cache, so a walk rarely reads RAM.
- 2 MiB pages still cover under 1% of 512 GiB. For random access over the full data set, they make each miss faster but do not remove the misses.
- The first touch of memory needs fewer page faults. One fault maps 2 MiB instead of 4 KiB.

Linux offers two ways to turn huge pages on. The kernel documents both [Ref4] [Ref5].

| | THP | Reserved pool (hugetlbfs) |
|---|---|---|
| Who chooses the pages | the kernel, automatically | the administrator and the program |
| Page sizes | 2 MiB | 2 MiB and 1 GiB |
| Program change | none, or one `madvise` call | the program must request huge pages |
| Guarantee | none, the kernel only tries | yes, after the pool is reserved |

## 4. What can go wrong

**With THP**

- A page fault can stall. When no free 2 MiB block exists, the kernel can run compaction inside the fault, and the thread waits [Ref4].
- A program that touches 1 byte of a 2 MiB range can receive the full 2 MiB. The background kernel thread khugepaged can also merge ranges that the program mostly never touched [Ref4]. Both raise memory use.
- A partial `munmap`, `mprotect` or `madvise` call on a huge page splits it into 4 KiB pages. Memory allocators do this when they return memory. The program still runs, but the speed gain is lost without any error.
- The Redis documentation reports high latency and memory growth after a process copy (`fork`) when THP is on [Ref6]. It recommends turning THP off.
- RAM becomes fragmented while the server runs. Free memory is then split into small pieces, and the kernel finds fewer free 2 MiB blocks. A benchmark then gives different results right after boot and after long uptime.

**With a reserved pool**

- Reserved memory is not available for any other use, even while the pool is idle. An oversized pool can make the rest of the system run out of memory. On a shared server, the pool also takes memory from the other users.
- The reservation can fail after boot. The kernel needs free contiguous RAM for each huge page, and fragmented RAM has little. 1 GiB pages are normally reserved on the kernel command line at boot [Ref5].
- When the pool is empty, the memory request fails or the process receives SIGBUS at first touch. SIGBUS is a signal that kills the process by default. So the program needs a fallback path to 4 KiB pages.
- The pool is divided among the NUMA nodes. A thread can receive a huge page from a remote node when its local node has none left. Access to that page is then slower.

**With both**

- The first touch of a huge page is slow. The kernel fills the whole page with zeros first. For a 1 GiB page this takes 0.1 to 0.3 s est.
- Some CPUs hold few TLB entries for 1 GiB pages. On such a CPU, 1 GiB pages can be slower than 2 MiB pages. Read the entry counts of the target CPU with the `cpuid` tool before choosing a size.
- In a virtual machine, the guest and the host must both use huge pages. Otherwise the CPU stores the translation at the smaller page size, and most of the gain is lost.

## 5. Checks to run before turning huge pages on

1. Measure the share of CPU cycles in page walks on the current setup. A small share means huge pages can give only a small gain.
2. Start with the THP `madvise` mode. Then only the memory ranges that the program marks get huge pages.
3. Confirm that huge pages are in use. `AnonHugePages` in `/proc/<pid>/smaps_rollup` shows THP use, and `HugePages_Free` in `/proc/meminfo` shows the pool.
4. Compare throughput and tail latency (the slowest 1% of requests) with huge pages on and off. Repeat the comparison after long uptime.

## References

- [Ref1] Intel 64 and IA-32 Architectures Optimization Reference Manual. It lists the TLB entry counts of each core type.
- [Ref2] Bhargava, Serebrin, Spadini, Manne. "Accelerating Two-Dimensional Page Walks for Virtualized Systems." ASPLOS 2008.
- [Ref3] Basu, Gandhi, Chang, Hill, Swift. "Efficient Virtual Memory for Big Memory Servers." ISCA 2013.
- [Ref4] Linux kernel documentation, "Transparent Hugepage Support." https://docs.kernel.org/admin-guide/mm/transhuge.html
- [Ref5] Linux kernel documentation, "HugeTLB Pages." https://docs.kernel.org/admin-guide/mm/hugetlbpage.html
- [Ref6] Redis documentation, "Diagnosing latency issues," section on transparent huge pages.

I wrote the figures from [Ref1], [Ref2] and [Ref3] from memory. This session had no lookup tool, so check them before they go on a slide. The `perf` command is also untested here.