## Short version

A TLB (translation lookaside buffer) is a small cache in each CPU core that stores recent virtual-to-physical address translations. With 4 KiB pages, the TLB of a big-memory server covers only a few MiB, and most accesses outside that range need a slow page-table lookup. Huge pages (2 MiB or 1 GiB) make each TLB entry cover 512 or 262,144 times more memory, but they can cause long allocation pauses, higher memory use, and run-to-run performance differences.

## Words used here

- **Page**: the unit of memory mapping. The default size on x86-64 is 4 KiB.
- **Page table**: the in-memory tree, 4 levels deep on x86-64, that maps each virtual page to a physical page.
- **Page walk**: the CPU reading the page table level by level after a TLB miss.
- **TLB reach**: entry count times page size, the amount of memory the TLB can translate without a miss.
- **THP** (transparent huge pages): the Linux feature that gives a process 2 MiB pages automatically.
- **Reserved pool** (hugetlbfs): huge pages that the administrator sets aside in advance and that a program must request explicitly.
- **Compaction**: the kernel moving pages to create a contiguous free block.
- **khugepaged**: the kernel background thread that merges 4 KiB pages into huge pages.
- **NUMA**: a server layout where each CPU socket has its own local memory.
- **madvise**: the system call a program uses to give the kernel hints about a memory range.

## 1. What a TLB is

- A program uses virtual addresses, and the CPU must translate each one to a physical address before it can access memory.
- The TLB stores recent translations. One entry covers one page.
- A first-level TLB hit adds no visible delay. A second-level hit adds a few CPU cycles (est.).
- A miss starts a page walk.

```
virtual address --> [ TLB ] --hit--> physical address
                       |
                      miss
                       v
          [L4] -> [L3] -> [L2] -> [L1] --> physical address
          page walk: one memory read per level

  4 KiB page: walk ends at L1 (4 reads)
  2 MiB page: walk ends at L2 (3 reads)
  1 GiB page: walk ends at L3 (2 reads)
```

## 2. Why misses are expensive on a big-memory server

The example is a server with 512 GiB of memory and a core with 2,048 second-level TLB entries [Ref1].

- **The reach is small.** 2,048 entries times 4 KiB is 8 MiB, which is 0.0015% of 512 GiB. A workload that accesses memory at random misses on almost every access.
- **The page table does not fit in the CPU cache.** Mapping 512 GiB with 4 KiB pages needs 134,217,728 last-level entries of 8 bytes each, which is 1 GiB of tables.
- **The last read of the walk often goes to main memory.** The CPU caches the upper levels of the walk, but not the last level. One main-memory read costs est. 100 ns (about 300 CPU cycles at 3 GHz).
- **Virtual machines (VMs) multiply the cost.** A walk inside a VM can need up to 24 memory reads [Ref3].
- **NUMA adds delay.** The tables can be located on another socket, and each walk read is then slower.
- **Measured size of the problem.** One study measured about 5% to 51% of execution cycles spent on TLB misses across five big-memory workloads with 4 KiB pages [Ref2].

## 3. How huge pages help

| Page size | Example entries | TLB reach | Share of 512 GiB | Walk reads | Last-level tables for 512 GiB |
|---|---|---|---|---|---|
| 4 KiB | 2,048 | 8 MiB | 0.0015% | 4 | 1 GiB |
| 2 MiB | 2,048 | 4 GiB | 0.78% | 3 | 2 MiB |
| 1 GiB | 1,024 | 1,024 GiB | 100% | 2 | 4 KiB |

- **Fewer misses.** Each entry covers more memory.
- **Cheaper misses.** The walk is one or two reads shorter. The tables shrink from 1 GiB to 2 MiB, and they then fit in the CPU cache.
- **Fewer page faults.** One fault maps 2 MiB instead of 4 KiB, so the first access to new memory causes 512 times fewer faults.

Linux offers two ways to turn huge pages on:

| | THP | Reserved pool |
|---|---|---|
| Who asks | The kernel decides. Modes are `always`, `madvise`, `never`. | The program asks with `mmap(MAP_HUGETLB)`. |
| Sizes | 2 MiB | 2 MiB and 1 GiB |
| Guarantee | None. The kernel may use 4 KiB pages instead. | Yes, after the reservation succeeds. |
| Cost | Kernel work at run time | Reserved memory is unusable for anything else. |

## 4. What can go wrong

| Problem | Applies to | What happens | How to limit it |
|---|---|---|---|
| Allocation pauses | THP | The kernel runs compaction inside a page fault. The thread waits for milliseconds or longer (est.). | Set `defrag` to `madvise` or `defer`. Allocate and write all memory at startup. |
| Memory use grows | THP | A 1-byte write takes 2 MiB. By default khugepaged merges a 2 MiB range that has only 1 of 512 small pages in use [Ref4]. The kernel may then terminate processes for lack of memory. | Set `enabled` to `madvise`. Lower `max_ptes_none`. |
| Huge pages lost without an error | THP | On fragmented memory the kernel uses 4 KiB pages. A partial `munmap` or `mprotect` splits a huge page. Performance then differs between runs. | Record `thp_fault_fallback` and `AnonHugePages` with every performance run. |
| Wrong pool size | Pool | A pool that is too large leaves too little memory for everything else. A pool that is too small makes `mmap` fail, or the process gets SIGBUS (a fatal signal) at first access [Ref5]. | Size the pool from the measured peak. Monitor `HugePages_Free`. |
| Late reservation fails | Pool | After long uptime the kernel often cannot find contiguous memory, especially for 1 GiB pages. | Reserve on the kernel command line at boot. |
| NUMA imbalance | Both | The pool is split per socket. A process bound to one socket can run out while another socket has free pages. | Reserve per node under `/sys/devices/system/node/`. |
| Slow `fork` users | Both | After `fork`, the first write to a shared huge page copies 2 MiB instead of 4 KiB. Redis documents latency and memory problems from this [Ref6]. | Exclude such processes with `madvise` mode. |
| Few 1 GiB TLB entries | 1 GiB | Older cores have as few as 16 second-level entries for 1 GiB pages [Ref1]. In [Ref2], one workload spent 1.4% of cycles on misses with 2 MiB pages and 7.1% with 1 GiB pages. | Read the entry counts with `cpuid` before choosing 1 GiB. |
| Zeroing at first access | Both | The kernel clears the whole page. That takes est. 0.1 ms to 0.2 ms for 2 MiB and est. 50 ms to 100 ms for 1 GiB, at an assumed 10 GiB/s to 20 GiB/s. | Write all memory once at startup. |
| VMs | Both | The TLB entry uses the smaller of the guest and host page sizes. | Turn huge pages on in both guest and host. |

My recommendation for the lowest-risk start:

- Set THP `enabled=madvise` and `defrag=madvise`.
- Have the application call `madvise(MADV_HUGEPAGE)` only on its large, long-lived buffers.
- Use a reserved pool instead when repeatable performance matters more than flexible memory use.

## 5. What to measure before and after

```bash
# TLB entry counts of this CPU
cpuid -1 | grep -i tlb

# Share of cycles spent in page walks (Intel event names)
perf stat -e cycles,dtlb_load_misses.walk_active,\
dtlb_store_misses.walk_active,itlb_misses.walk_active -- <command>

# Did the process really get huge pages?
grep -E 'AnonHugePages|HugePages_' /proc/meminfo
grep AnonHugePages /proc/<pid>/smaps_rollup
grep -E 'thp_fault_alloc|thp_fault_fallback' /proc/vmstat
grep -E 'thp_split_page|compact_stall' /proc/vmstat

# Current THP settings
cat /sys/kernel/mm/transparent_hugepage/{enabled,defrag}
```

Insufficient data: the gain for your workload is unknown. The `perf stat` line above (`perf` is the Linux profiling tool) gives it: the sum of the three `walk_active` counts divided by `cycles` is the largest share of time that huge pages can remove.

## References

I quoted the numbers from Ref1 and Ref2 from memory. Check them against the sources before you present them.

- [Ref1] Intel 64 and IA-32 Architectures Optimization Reference Manual, TLB parameter tables. Golden Cove (the Sapphire Rapids core): 2,048 second-level entries shared by 4 KiB and 2 MiB pages, 1,024 entries for 1 GiB pages. Skylake Server: 1,536 shared entries, 16 entries for 1 GiB pages.
- [Ref2] Basu, Gandhi, Chang, Hill, Swift. "Efficient Virtual Memory for Big Memory Servers." ISCA 2013.
- [Ref3] Bhargava, Serebrin, Spadini, Manne. "Accelerating Two-Dimensional Page Walks for Virtualized Systems." ASPLOS 2008.
- [Ref4] Linux kernel documentation, `Documentation/admin-guide/mm/transhuge.rst`.
- [Ref5] Linux kernel documentation, `Documentation/admin-guide/mm/hugetlbpage.rst`.
- [Ref6] Redis documentation, "Diagnosing latency issues", section on transparent huge pages.