**Short version.** Correct the slice-bandwidth attribution, the one-port write claim, and the mixed-repetition read result before sharing this brief. Several shortened explanations also turn aggregate measurements into claims about individual cache lines or unmeasured hardware. The existing counter-analysis checks pass, but they do not validate those interpretations.

Reviewed on 2026-11-10. Line numbers refer to `crb-memory-hierarchy-brief.html`, SHA-256 `5ad0feb997a4cf1025dde2c3cb98ca46797a89fb40f37a3648ba1263ba7a0b24`. These are review comments and suggested replacements. The HTML was not edited. [Ref1]

Terms used below:

- A **mesh** connects cores, caches, and memory interfaces. A **slice** stores part of the shared mesh cache.
- A **home node** handles an address on its assigned mesh. A **proxy** handles that address on the other mesh.
- **L1/L2** are private core caches. **SLC** means system-level cache, the mesh cache in this brief. **DRAM** means main memory.
- Bandwidth uses decimal GB/s and TB/s. Buffer sizes use binary KiB, MiB, and GiB.

**1. “≥ 0.62 TB/s served by slices” counts accesses that missed.**

Location: line 32.

The matching 40-thread run measured 1,384.77 GB/s of application reads. Its counters recorded 9,718,737,781 slice accesses and 280,083,112 slice misses. The brief attributes bytes to every access, including misses. A slice miss does not establish that the slice supplied the data. [Ref2]

Under the report's approximation of one 64-byte line per event:

```text
All slice accesses     minus slice misses     gives slice hits
621.91 GB/s, est.       17.92 GB/s, est.       603.99 GB/s, est.
```

Counting misses adds 17.92 GB/s, est., to the claimed slice service.

| Quantity | Recomputed result |
|---|---:|
| Application read bandwidth | 1,384.77 GB/s, measured |
| Slice accesses per application line | 0.449109 events/line |
| Slice misses per slice access | 2.8819% |
| Bandwidth represented by all accesses | 621.91 GB/s, est. |
| Bandwidth represented by accesses minus misses | 603.99 GB/s, est. |

The last two rows are estimates derived from counters. They are not direct byte-transfer measurements. The counter file also reports 49–50% event running time, so these counters were scheduled for only part of the run. That limitation should accompany this estimate. The later tables' 100% running-time statement does not apply to this earlier run. [Ref2]

Suggested replacement:

> About 0.60 TB/s from slice hits, est., within 1.38 TB/s of measured application reads at 40 threads. The estimate uses slice accesses minus misses and counters active for 49–50% of the run.

Remove the asserted lower-bound sign unless a separate measurement establishes that bound.

**2. The 229 GB/s write result used four ports, not one.**

Location: line 40, “the same port carries 82 GB/s with the partner core, 229 GB/s with 4 writers.”

The source run uses these placements. The full report correctly distinguishes their port counts. [Ref3]

| Writers | Ports used | Approximate aggregate bandwidth |
|---|---:|---:|
| CPU 2 | 1 port | 71 GB/s |
| CPUs 2 and 3 | 1 port | 82 GB/s |
| CPUs 2, 4, 6, and 8 | 4 ports | 229 GB/s |

This matters because the sentence uses the result to locate the single-writer limit. Four-port aggregate bandwidth cannot establish one-port capacity.

The same sentence also overstates the counters as exact zeros. The analysis reports approximately 0.001 L2 write-backs per application line and 21,130 east-link stall cycles per second. These are small rates, but they are not zero. [Ref3]

Suggested replacement:

> The partner pair reaches about 82 GB/s through one port. Four writers on four ports reach about 229 GB/s. The single-writer run has near-zero cache allocation and little measured link stalling. These observations are consistent with a limit on writes issued by one core, but they do not identify the limiting resource.

**Insufficient data:** the specific core resource setting the rate was not measured. The full report proposes a per-core write sweep to test whether bandwidth changes with distance to the slices. Keep that explanation labelled as a hypothesis. [Ref3]

**3. The concurrent-read finding combines different repetitions.**

Location: line 46.

The 869 GB/s mesh-0 sum and the 58–60 GB/s per-thread range on mesh 1 come from repetition 0. The 1,372 GB/s total comes from repetition 2. The generator selects repetition 0 for thread records and independently selects the best aggregate. [Ref4]

| Recorded repetition | Mesh-0 thread-rate sum | Mesh-1 rate per thread | Application aggregate |
|---|---:|---:|---:|
| 0 | 868.52 GB/s | 58.22–60.42 GB/s | 1,341.56 GB/s |
| 2 | 890.11 GB/s | 58.76–61.56 GB/s | 1,371.64 GB/s |

Use one repetition throughout. For example:

> In repetition 2, the 32 threads on mesh 0 total about 890 GB/s. The eight threads on mesh 1 each read 58.8–61.6 GB/s. Aggregate application bandwidth is 1,372 GB/s.

Call these **application read rates**. The mesh-cache working-set test includes private-cache hits, so the per-thread rates do not isolate bytes supplied by slices. Retain the buffer size and core placement in the caption. [Ref2, Ref4]

**4. Missing measurements are drawn as absent cores.**

Locations: line 42 and the mesh-1 “no cores” labels at lines 197, 218, 239, and 260.

The position dataset covers CPUs 0–119. The generator prints “no cores” whenever it finds no matching measured position. CPUs 120–127 exist but were excluded from these tests. The full report identifies the last column of mesh 1 as their expected location. [Ref5]

Change the mapping claim to:

> Positions of tested CPUs 0–119 were inferred from their latency gradients.

Use “not measured” in the affected cells. Add a caption saying that CPUs 120–127 were not mapped by this experiment. If their expected positions are drawn, distinguish those inferred positions from the measured fits. An empty measurement set does not prove that a hardware position is empty.

**5. The counter-rate formula omits the conversion to 64-byte lines.**

Location: line 487, “counts over the byte difference.”

That formula produces events per byte. The table reports events per 64-byte application line. The analysis script divides the byte difference by 64 before normalizing the counts. [Ref6]

Use:

```text
events per line =
  64 × (long count − short count − idle rate × interval difference)
  / (long bytes − short bytes)
```

Here, idle rate is measured in events per second, and the interval difference is in seconds. “Divide by the difference in 64-byte lines streamed” is a shorter correct description. The recorded table values use the correct normalization. This is an error in the method description.

**6. The caption extends the single-reader result to writes.**

Location: line 487, “The other mesh sees nothing for an 8 MiB working set.”

The write row immediately above reports 0.38 other-mesh accesses per application line. Recalculation gives 0.382 events/line. Only the single-reader case rounds to zero in this column. [Ref7]

The preceding explanation also describes every read as removing a line from a slice and every later L2 eviction as restoring it. The recorded 0.827 accesses/line and 0.828 fills/line are aggregate rates from separate event groups. They do not track individual lines through those transitions. [Ref7]

Suggested replacement:

> For the single-reader 8 MiB case, other-mesh accesses round to zero events per line. Similar access and fill rates are consistent with predominantly exclusive caching, where data moves between private caches and slices. These counters do not record each line's movements. The 8 MiB write stream records 0.38 other-mesh accesses per line.

**7. Cross-mesh averages do not establish each line's supplying cache.**

Locations: line 43, “A line held only on the other mesh costs about 85 ns on its first access, then it is kept locally,” and line 502.

The cross-mesh test measures complete 16 MiB pointer-chain traversals. It does not identify the supplying cache or record individual line residency. The later caveat about the builder's L2 does not repair the stronger claim near the top of the brief. [Ref8]

Suggested replacement:

> After warming a 16 MiB chain on another mesh, the first reader walk averaged 85.0–88.5 ns/load. The second averaged 31.7–33.2 ns/load. The supplying caches and individual line states were not measured.

**Insufficient data:** distinguishing remote-slice hits from transfers out of the builder's private cache requires a test that controls private-cache residency and records cache-source evidence. The timing averages alone do not separate those paths. [Ref8]

**Smaller corrections and presentation comments.**

| Location | Original text or issue | Suggested correction |
|---|---|---|
| Line 32 | “29 avg (85)” | At 2.8 GHz, 29 ns is 81.2 cycles. Use approximately 81 cycles, or use the latency measurement that supports 85 cycles. Include “cycles” in the L2 and DRAM cells too. |
| Lines 32, 280 | “1 MiB” per slice without qualification | Restore “1 MiB per slice, est.” The full report derives it from 128 MiB divided by 128 nodes. [Ref9] |
| Lines 32, 43 | “64 MiB seen by one core” and “one buffer sees 64 MiB” | Prefer “single-buffer capacity transition around 64 MiB.” The report already records misses at that working-set size. It does not establish 64 MiB of simultaneous slice residency or the configured occupancy limits. [Ref9] |
| Line 32 | Whole-chip writes: “not cached” | Use “streaming writes mostly bypass the SLC.” The brief itself reports nonzero slice fills for this workload. [Ref7] |
| Line 41 | “Repeat spread 3%” | Say “Median spread across seven repeats: 3%.” The computed median is 2.8700%. This is not a bound on every case. One recorded case ranges from 20.47 to 37.08 ns around a 22.39 ns median. [Ref10] |
| Line 483 | “285” GB/s without a statistic | This rounds the best short run, 284.92 GB/s. The long runs span 281.79–283.23 GB/s. Label the statistic or report the long-run range consistently. [Ref7] |
| Lines 25, 40 | Evidence references are plain text | Link the full report and the source data. The CSV reference also needs its `results/` prefix. The HTML contains no links. [Ref1] |
| Lines 25–43 | Undefined CMN, SLC, crosspoint, home, proxy, and address hash | Add a compact glossary before the findings. Reuse the full report's definitions where they remain supported. Add a short opening takeaway so the reader encounters the conclusions before the dense table. [Ref1, Ref9] |
| Lines 72–74 and similar map cells | Small white labels on pale blue | This color combination has a calculated contrast ratio of 2.55:1. Select text color from background brightness. At the declared 186 mm content width, the map's core labels are about 5.09 pt. Enlarge the labels or the map. These are calculations from the HTML, not a rendered print check. [Ref1, Ref5] |

The brief is generated by `make-brief.py`. Apply accepted corrections there as well as in the generated file so regeneration preserves them. [Ref5]

**Verification and limits.**

- Ran `subtract.py` against the recorded `writebw.csv` and `crossmesh.csv` files. Both exited successfully with `checks failed: 0`. [Ref6, Ref7, Ref11]
- Ran `analyze_writepath.py` against `writepath.csv`. It exited successfully with `checks failed: 0`. [Ref3]
- Recomputed the access-minus-miss bandwidth estimate, per-repetition read totals, cross-mesh traversal ranges, and repeat-spread statistic from local records. [Ref2, Ref4, Ref8, Ref10]
- Reviewed the HTML and generator without regenerating or changing the brief. No new hardware benchmarks were run.
- **Insufficient data:** rendered pagination and clipping remain unverified. The available PDF renderer could not start because its Pango dependency is missing. A browser print preview or working PDF renderer would resolve this.

**References.**

- **Ref1:** [Reviewed brief](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy-brief.html:25).
- **Ref2:** Matching [40-thread application bandwidth](/home/jhan/workspace/titan/cache-perf/crb/results/uncore2-20261030T203752Z/bw-asmread-3M-40T-even.csv:3) and [slice counters](/home/jhan/workspace/titan/cache-perf/crb/results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv:3). Sum accesses from both meshes, subtract their misses, multiply by 64 bytes, and divide by total application bytes to obtain the estimated slice-hit fraction.
- **Ref3:** [Write-path measurements](/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T211150Z/writepath.csv:57), [analysis script](/home/jhan/workspace/titan/cache-perf/bench/analyze_writepath.py:1), and [full report's port-count table and hypothesis](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html:268). Relevant cases: `w8M-c2`, `w8M-c2c3`, and `w8M-c2c4c6c8`.
- **Ref4:** [Per-thread read records](/home/jhan/workspace/titan/cache-perf/crb/results/followup3-20261102T031936Z/perthread-asmread-3M-40.csv:3) and [generator's repetition selection](/home/jhan/workspace/titan/cache-perf/crb/make-brief.py:45). Per-mesh sums add each thread's reported rate. The application aggregate uses total bytes divided by the longest thread duration, so the two calculations need not match exactly.
- **Ref5:** [Generator's missing-position fallback](/home/jhan/workspace/titan/cache-perf/crb/make-brief.py:87), [CPU availability record](/home/jhan/workspace/titan/cache-perf/crb/inspection-record-2026-10-30.md:140), and [full report's unmeasured-column caveat](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html:694).
- **Ref6:** [Counter normalization and checks](/home/jhan/workspace/titan/cache-perf/bench/subtract.py:46).
- **Ref7:** [Read/write counter records](/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/writebw.csv:1). Relevant cases: `asmread-8M-1`, `asmread-8M-14`, `asmwrite-8M-1`, and `asmwrite-1G-14`.
- **Ref8:** [Cross-mesh traversal records](/home/jhan/workspace/titan/cache-perf/crb/results/followup2-20261031T073513Z/cross.csv:15) and [benchmark's chain construction and timed walks](/home/jhan/workspace/titan/cache-perf/bench/latency.c:154). The four cross-mesh 16 MiB first walks span 84.953–88.462 ns/load. Their second walks span 31.740–33.228 ns/load.
- **Ref9:** [Full report's glossary](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html:75), [derived slice size](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html:191), and [reported capacity transition](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html:238).
- **Ref10:** [Generator's repeat-spread calculation](/home/jhan/workspace/titan/cache-perf/crb/make-brief.py:22) and [seven-repeat measurements](/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/full/latency.csv:6). The generator takes the median of `(maximum − minimum) / median` across the 15,360 individual-slice cases.
- **Ref11:** [Cross-mesh counter records](/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/crossmesh.csv:1).
