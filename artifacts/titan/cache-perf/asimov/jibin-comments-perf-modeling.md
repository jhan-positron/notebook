# Jibin's comments on the perf-modeling reports and tests

Collected 2026-11-04 from the Claude Code transcripts of four sessions and from Bill's Slack direct messages. Every entry is the message as typed, in time order, Pacific time. Operational messages (Slack relays, push, status checks, pasted run logs, review-loop bookkeeping) are left out.

## Jibin's inputs

### 1. 2026-10-30 18:37 (S1) - ocm-interpretation.html; re-wording

> Please update the html at https://claude.ai/artifact/5DxNVPjVhhVPT1jaPDar2T:
> - "is backed" means "is cached", right? If so, please change 

### 2. 2026-10-30 18:56 (S1) - ocm-interpretation.html; term

> `A line's physical address`: what is "a line" ?

### 3. 2026-10-30 22:23 (S1) - CRB report; re-run

> Back to CRB perf, you updated our doc after reviewing Bill's doc, but you did not verify the numbers. Should you re-run the tests to confirm the updates to our doc are indeed correct?

### 4. 2026-11-01 12:21 (S1) - crb-memory-hierarchy.html; broken characters

> There are quite some messed up char, such as ` Ã`

### 5. 2026-11-01 12:59 (S1) - crb-memory-hierarchy.html; re-wording

> Please update the paragraph, `What each field does`:
> - make bullet points formet, each field is one bullet
> - at tag field, indicate the 14 bit right shift

### 6. 2026-11-01 20:39 (S1) - crb-memory-hierarchy.html; measured or spec

> The diagrams at `The hierarchy at a glance` state some metrics:
> - pair port, 80 GB/s per 2 cores
> - 1.43 ns L1 data
> - and many other metrics
>
> Are all these data measured, or from Arm spec?

### 7. 2026-11-01 22:11 (S1) - crb-memory-hierarchy-brief.html; new page for Bill

> The run is going. After it finishes, please:
> - update plan-2026-11-02.md again with the latest data, and monitor codex-review-plan-2026-11-02.md updates. If codex points out new problems, please respond
> - generate crb-memory-hierarchy-brief.html:
> -- this file is to give to Bill who is an expert in system engineering, he just wants to see test results. There is no need to explain tech terms
> -- the whole file can fit no more than 2 A4 pages.
> -- present data intuitively, e.g. data on top of CMN map, data in table, etc.

### 8. 2026-11-02 08:02 (S1) - CRB; re-run after codex review

> Do we need to rerun the test because of the changes from codex review?

### 9. 2026-11-02 09:38 (S1) - crb-memory-hierarchy.html; write throughput question

> L1 and L2 have same write throughput at 89.5 GB/s, why? Is it because the write is write-back not write-through? If so, how come mesh cache perf is lower at 73 GB/s?

### 10. 2026-11-02 09:40 (S1) - crb-memory-hierarchy.html; whole chip wording

> What does "read, whole chip" mean in the sense of who are readers and who are providers? Same question to "write, whole chip"

### 11. 2026-11-02 09:57 (S1) - crb-memory-hierarchy.html; collect counters; re-run

> ```
> Why the mesh row is 73 GB/s. At 8 MiB the buffer no longer fits in L2, so every written line leaves the core through its single mesh port. The counters show the mesh cache keeps almost none of them (0.013 fills per line) and sends about one memory request per line. So the number is a single core writing to DRAM through the mesh. The limit is how many writes one core can keep in flight across the mesh and memory, not the mesh cache's write bandwidth. The exact in-flight limit is Insufficient data. It would need the core's outstanding-write count from the CMN request-queue occupancy counters, which were not collected.
> ```
> - please collect them
> - "line" is 64B cache line? Basically you are saying, all cache lines just flow through L1, L2 and mesh cache (fill and immediately evicted), correct? What we do not have measurement is, we do not know if the bound is at L2 cache to mesh, the mesh or the mesh to DRAM, correct?

### 12. 2026-11-02 11:22 (S1b) - perf-measurement-tech.html; new page

> Please digest the perf measurement code at bench/run_sudo.sh (top level) and bench/bandwidth.c, and generate perf-measurement-tech.html:
> - illustrate the distilled techniques of cache/dram perf measurement, quote relevant code snippets 
> - use top down fashion: start with architecture overview, data paths, potential bounds along the data paths
> - highlight implementation techniques: choose data set sizes, load/write instructions, read/write patterns, avoid/cause cache hits/misses, core/cache/mesh/dram spread/shape consideration, etc.
> - end the doc with a summary: key take aways of which readers are best to internalize
> - the goals are: assume the reader is an experienced software engineer who likes to learn the techniques and be able to implement it manually
> - use diagrams
> - avoid lengthy verbose, best to apply succinct verbose on top of diagrams; or use bullet pointing format

### 13. 2026-11-02 11:59 (S1) - crb-memory-hierarchy.html; whole chip table; new data-path section

> Back to "Whole chip" table:
> - "Mesh read" row is not clear: the 40 threads are at 40 different cores and 1 thread each core? If so, why 40 thread/core instead of 120 thread/core?
> - "DRAM read" row: "over both chiplets": what is the chiplet, DRAM chiplet? 
> - please write a new section at crb-memory-hierarchy.html, it has hierarch diagrams to illustrate mesh, processor cores, SLC, DDR channels; and use the diagrams as templates to illustrate the reader/writer and provider/destination and data paths of each measurement(read/write 1 core, read/write while chip)

### 14. 2026-11-02 12:04 (S1) - crb-memory-hierarchy-brief.html; term

> As of crb-memory-hierarchy-brief.html: "slices" is used multi times, they all indicate mesh cache slices, correct?

### 15. 2026-11-02 12:12 (S1) - crb-memory-hierarchy.html; interleave paragraph re-wording

> As of:
> ```
> Every 2 MiB chunk is interleaved line by line, half on each mesh. Lines homed on the other mesh are served by a proxy on the core's own mesh at the same 19 to 44 ns, so a core's working set lives on its own mesh: one buffer sees 64 MiB.
> ```
> Is my paraphrasing right:
> ```
> Every 2 MiB mesh cache chunk is interleaved cache line by cache line, half on each mesh. E.g. line 0, 2, 4, etc. at own mesh, line 1, 3, 5, etc. at the other mesh. Lines homed on the other mesh are served by a proxy on the core's own mesh, and the read latency between issuing the load instruction and reaching the mesh cache at the other mesh is between 19 to 44 ns, this latency spread is same for all the cores.
> ```
> ?
> I do not know how to adapt ` so a core's working set lives on its own mesh: one buffer sees 64 MiB`

### 16. 2026-11-02 12:24 (S1) - crb-memory-hierarchy.html; interleave paragraph

> `The 19 to 44 ns is the time from the load to that slice on the core's own mesh, whether the slice is the line's home or a proxy.`: this does not make sense since that slice is always on the core's own mesh as you said

### 17. 2026-11-02 12:26 (S1) - crb-memory-hierarchy.html; interleave paragraph

> But if the target address is at the remote mesh, it would take extra time between the proxy slice and the target slice at remote mesh, right? If so, how come ` the second case is not slower than the first` ?

### 18. 2026-11-02 12:31 (S1) - crb-memory-hierarchy.html; interleave paragraph

> YOu did not cover 1 case: the proxy slice at home mesh is miss and it is hit at slice at remote mesh

### 19. 2026-11-02 12:33 (S1) - crb-memory-hierarchy.html; interleave paragraph

> 2 to 7 ns reads too quick to me: proxy slice to C2C and to target slice at remote mesh should be longer than all-local mesh which is 19 to 44 ns

### 20. 2026-11-03 10:47 (S2) - asimov-memory-hierarchy.html; Linux on DSUs

> The 5 DSU run 5 individual Linux OS, or they run 1 Linux on all, or 1 DSU runs Linux and the rest special sw?

### 21. 2026-11-03 10:52 (S2) - asimov-memory-hierarchy.html; kernel on all cores

> The kernel code run on all 5 DSU / 10 cores?

### 22. 2026-11-03 11:04 (S3) - asimov-c1nano-perf.html; term

> ```
> L3, 256 KiB per DSU
> 14.0 ns at 192 KiB (mixed L2, L3 and mesh)
> ```
> - what does it mean "mixed L2, L3 and mesh" ?

### 23. 2026-11-03 11:11 (S3) - asimov-c1nano-perf.html; L1 miss question

> how can 100% miss in L1 be? L1 size is 32 KB, does this mean the step size is larger than 32 KB so that every data load is beyond L1?

### 24. 2026-11-03 12:04 (S3) - asimov-c1nano-perf.html; define repeat/fresh/flushed

> What do repeat, fresh and flushed mean? How are the test code implementing the scenarios?

### 25. 2026-11-03 13:04 (S3) - asimov-c1nano-perf-brief.html; asimov-cme-perf-brief.html; new pages

> Please generate asimov-c1nano-perf-brief.html and asimov-cme-perf-brief.html:
> - they are simplified versions of   asimov-c1nano-perf.html and asimov-cme-perf.html
> - the audiance is Bill who knows technical context, and he is just curious of the profiling results
> - each file should be no more than 2 A4 pages

### 26. 2026-11-03 15:47 (S3) - asimov-c1nano-perf.html; section 3 diagram re-wording

> The home node box at the left diagram of section 3, "The hemisphere map", please change `Home node: SLC (3.75 MiB) or OCM` to :
> ```
> 5 home nodes (HN-S)SLC 768 KiB each (12 ways)OCM 256 KiB each (4 ways)
> ```

### 27. 2026-11-03 15:52 (S3) - asimov-c1nano-perf.html; OCM range; open item; add dense range

> ```
>
>
> Distance (crosspoints)    Rows    Run 3 sparse, mean ns    Range ns    Run 2 dense, mean ns
> 1    8    21.58    20.14 to 22.97    19.64
> 3    10    24.25    22.39 to 26.52    21.82
> 5    2    27.73    27.00 to 28.45    24.58
>
> ```
> How come the ranges are that large, 10% at each distance? Is this logged as open item?
>
> And please add Range for dense runs

### 28. 2026-11-03 15:58 (S3) - asimov-c1nano-perf.html; sparse vs dense

> The difference between sparse and dense does not make sense. E.g. for distance 1, the difference is only 2ns. My understanding is, dense has larger chance to hit OCM while sparse pretty much each load is OCM miss, if so, the differences should be much larger.

### 29. 2026-11-03 16:03 (S3) - asimov-c1nano-perf.html; refill meaning

> Refill means cache miss, right? Then Dense should have lower refill than sparse, how come otherwise?

### 30. 2026-11-03 16:09 (S3) - asimov-c1nano-perf.html; add to run 4; proof request

> `In the sparse chain the prefetcher fetched about twice as many lines per load, and a larger share of them were members`: do you have proof of this statement? Or this is how ARM64 is desiged?

### 31. 2026-11-03 16:36 (S3) - asimov-c1nano-perf.html; table 4.3 write bandwidth question

> At table `4.3 One-core bandwidth by footprint, CPU 2`, why Write bandwidth shows larger buffer writes are higher throughput than smaller?

### 32. 2026-11-03 16:48 (S3) - asimov-c1nano-perf.html; table 4.3 note

> And please please add a note under the table saying write overhead of the test code at smaller buffers caused them not reaching full write potential

### 33. 2026-11-03 16:55 (S3) - asimov-c1nano-perf.html; table 4.4 add ratio column

> Please add 1 column to table `4.4 Multi-core DRAM bandwidth`, ratio of Run 3 to one-core bandwidth

### 34. 2026-11-03 17:04 (S3) - asimov-c1nano-perf.html; table 4.4 add potential column

> Add another column to table 4.4, the ratio to single core full potential. E.g. `CPU 2 + 3 (one DSU)    read` is 100% because 116.4 of run 3 divided by 2 is 58.2 GB/s which equals to 58.1 GB/s of 1 core

### 35. 2026-11-03 18:01 (S3) - asimov-c1nano-perf.html; tables 4.3 and 4.6 L3 vs OCM

> Table 4.3 shows 256 KB buffer's read throughput is 10.2 GB/s and the data providers are L3 and SLC; table 4.6 shows 16 GB/s from OCM. Does this make sense? L3 should be faster than OCM

### 36. 2026-11-03 18:29 (S3) - asimov-c1nano-perf.html; diagrams 5 and 7 add L3 and sizes

> The diagrams at section 5 and 7 do not have L3 line, any reason for the missing? And please add sizes to L1, L2 (and L3 if you are to add) at diagram 7

### 37. 2026-11-04 09:07 (S3) - asimov-cme-perf.html; data path diagram

> As of asimov-cme-perf.html, please draw a data path diagram using CME data load instruction as example, starting with c1nano core


### Bill, 2026-11-04 09:19 PST - Bill 2; asimov-c1nano-perf-brief.html; wording

> There's some of AI extraneous verbiage and terminology.  "chase"?

### Bill, 2026-11-04 09:19 PST - Bill 4; asimov-c1nano-perf-brief.html; L3

> L3 is confusing.  42% L2 hit rate?

### Bill, 2026-11-04 09:21 PST - Bill 5; asimov-c1nano-perf-brief.html; compare with CRB

> L1,2,3,SLC,DRAM compared vs the CRB.  I remember the CRB's L1 is also 4 cycles.  Don't spend too much time on DRAM. That's going to look very different between the two platforms.

### Bill, 2026-11-04 09:26 PST - Bill 6; asimov-c1nano-perf-brief.html; DRAM read bandwidth

> The read throughput from DRAM is too slow.  I doubt that's reality. It's probably a software mechanism issue. Write speeds are great, though.   155 GB/s is around max theoretical.

### Bill, 2026-11-04 09:28 PST - Bill 7; asimov-c1nano-perf-brief.html; L1 read bandwidth

> The 1 core read from L1 is only 58GB/s.  That's WAY too slow.

### Wade, 2026-11-05 12:24 PST

> SMSTART and SMSTOP of SME are costly operations
- so I should prompt claude when writing test code, such setup calls and all such overhead should be one time call, or should be excluded from time measurement
- well, the purpose is perf modeling, not raw perf potential. So we also need to measure the perf of typical sw calling. Use CME as example, if SMSTART and SMSTOP are required at
  each call, then I still need to have them inside each call. So I need to measure both raw perf and typical perf
