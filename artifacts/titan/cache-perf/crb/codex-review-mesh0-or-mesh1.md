**Short version.** I agree with the revised architectural explanation. Most earlier corrections are incorporated, but several statements still turn aggregate measurements into claims about individual cache lines or slices. There is also an error in the address-bit explanation, and the bandwidth calculations and software advice need the qualifications below.

Second review, 2026-11-09, of the regenerated [mesh0-or-mesh1.md](mesh0-or-mesh1.md). This replaces the first review. Line numbers refer to the revision whose file fingerprint begins `c74d8ac18e42`.

The earlier corrections that now stand are:

- Home and proxy lines share storage under separate occupancy limits. There is no established fixed half-and-half division.
- The chip's distinct-data capacity and persistent duplication of shared lines are unmeasured.
- Small buffers need not have equal numbers of lines on both meshes.
- The whole-chip read combines both meshes, and not every node has been shown to serve proxy lines.

Here, a **home node** owns an address. A **proxy** handles that address on the other mesh. A **slice** is a home node's cache storage. **L1/L2** are private core caches, **SLC** is the mesh cache, and **DRAM** is main memory.

**1. The cross-mesh test still does not establish every line's location.**

Affected text: Question 6, lines 163–168; Question 9, lines 252–254.

These statements remain too strong:

- “lines that only the other mesh's slices hold”
- “no usable copy was found on the reader's mesh”
- “About one eighth of the lines were also still in core 3's L2”

The test records mean time per load. It does not record which cache supplied each line or the fraction of local hits. The builder's private cache may still hold some lines, but that fraction was not measured. The original report describes this as a possibility. [Recorded [cross.csv](results/followup2-20261031T073513Z/cross.csv); [full report, cross-mesh caveat](crb-memory-hierarchy.html#a-first-read-of-lines-cached-on-the-other-chiplet-costs-85-ns).]

The two proposed paths—remote home supplying a local proxy miss, or remote proxy supplying a local home miss—are explanations consistent with the design. They are not separately measured categories in this run. The benchmark also writes the chain during construction, so it does not isolate clean shared-data behavior. [Benchmark [latency.c](../bench/latency.c), `build_cycle` and `run_size`.]

Line 252 introduces a separate recording error. The same-core times and cross-mesh times came from separate program invocations with separate allocations. They were not four consecutive timed walks over the same buffer:

```text
Control run:  build/warm on 3 --> time on 3 --> time on 3
Cross run:    build/warm on 3 --> time on 67 --> time on 67
```

The builder's warmup in the cross run was untimed. [Recorded [cross.csv](results/followup2-20261031T073513Z/cross.csv), first two invocation blocks; [launch script](../../exec/scratch-relocated/ed41c79f/crb-followup2.sh), pair loop; [latency.c](../bench/latency.c), `run_size`.]

Suggested replacement:

> A separate same-core control measured 29.277 and 29.034 ns/load. The cross-mesh case measured 86.053 and 32.134 ns/load after an untimed builder-side warmup. These averages establish a first-walk penalty. They do not establish every line's supplying cache, hit/miss state, or coherence state.

The other placements support the same timing observation. Their first-walk range is 84.953–88.462 ns/load, which rounds to **85.0–88.5 ns/load**, rather than 84.9–88.5 ns/load.

**2. Global address balance does not establish half-full slices or half-capacity lower bounds.**

Affected text: Question 5, line 133; Question 9, lines 237–241.

Removing the fixed 50/50 partition was correct. The replacement still claims that a globally balanced buffer fills each slice half with home lines and half with proxy lines. It then concludes that neither occupancy limit was below approximately half.

That inference needs assumptions the tests have not established:

- The local proxy mapping and distribution across individual slices remain unknown, as Question 8 acknowledges.
- The 64 MiB working set already has the reported 11% misses. It is not a demonstration that all 64 MiB simultaneously occupy the slices.
- Some data can reside in private caches. The working-set size is not a direct measurement of mesh-cache occupancy.

These limitations prevent the reported capacity transition from establishing a lower bound for every slice's two occupancy limits. “Whatever the limits allow” is also incorrect: a limit can prevent a balanced offered workload from producing balanced resident contents. [Discussion, lines 225, 236 and 241; [capacity results](crb-memory-hierarchy.html#effective-capacity-is-64-mib-for-one-buffer).]

Suggested replacement:

> The measured capacity transition is compatible with approximately balanced home/proxy occupancy. It does not measure either occupancy limit or the resident mix in individual slices. Uniform distribution and sufficient occupancy limits remain assumptions of that explanation.

Prefer “capacity transition around 64 MiB” to “one core sees 64 MiB, and that is measured.” The former describes what the miss curve actually establishes.

**3. Counters can show capacity-limit pressure and active proxy service.**

Affected text: Question 2, lines 91–93.

“Performance counters cannot show either” is too broad. Register reads reveal configured values. Counters can reveal whether those limits affect a workload.

Arm defines two relevant events:

| Event | What it counts |
|---|---|
| `PMU_HN_LBT_REQ_OVER_HARDLIM_EVENT`, `0x35` | Proxy-class write allocations rejected because that class exceeds its capacity limit |
| `PMU_HN_HBT_REQ_OVER_HARDLIM_EVENT`, `0x36` | Home-class write allocations rejected because that class exceeds its capacity limit |

These are documented on page 1219. Home/proxy event filters can also test whether an individual node processes both classes. They do not read the exact mode bits. [Arm CMN S3 Technical Reference Manual, [local PDF](refs/arm-cmn-s3-r2p3-trm-107858.pdf#page=1219), pages 1214, 1216 and 1219.]

Conversely, reading a configured limit does not by itself show that the workload reached it.

Suggested replacement:

> Register reads provide the configured limits and mode bits. Additional counters can test whether either limit blocks allocations and whether each node handles both classes. The recorded runs did not make those measurements.

**4. Three participating bit flips do not cancel.**

Affected text: Question 4, line 121.

The explanation says a carry that flips bit 6 plus “bit 8 and bit 10” leaves the home unchanged. Those are three participating flips, so the parity changes. Parity means whether the number of participating set bits is odd or even.

```text
Participating bits flipped     Count     Home
6 and 8                         2       unchanged
6, 8 and 10                     3       changes
```

The recorded transition from line 15 to line 16 is a direct counterexample. Byte offsets `0x3C0` and `0x400` have homes 0 and 1. [Recorded [homes.csv](results/sudo-20261102T054936Z/full/homes.csv), line indices 15 and 16.]

Suggested replacement:

> Neighbors have the same home when the increment flips an even number of participating hash bits. They have different homes when it flips an odd number.

**5. Matching fill and access rates are consistent with exclusivity, not proof of each transition.**

Affected text: Question 7, lines 200–201.

The values reproduce: 0.828 fills and 0.827 accesses per application line. But they are aggregate rates from different event-group runs. They do not establish that **each** slice read removed a line and that its next L2 eviction restored it. [Recorded [writebw.csv](results/sudo-20261102T054936Z/writebw.csv), case `asmread-8M-1`, fill and access groups; analysis [subtract.py](../bench/subtract.py).]

The manual supports a generally exclusive data-cache policy: a data copy need not remain in the slice while held privately. There are exceptions for sharing. That makes the proposed mechanism reasonable. It does not make the aggregate rates a record of individual line transitions. [Arm manual, [page 55](refs/arm-cmn-s3-r2p3-trm-107858.pdf#page=55).]

Suggested replacement:

> The similar fill and access rates are consistent with predominantly exclusive read-and-evict behavior. These counters do not track individual lines through those transitions. Local slice residency was verified under the benchmark's warmed conditions, rather than guaranteed after any L2 eviction.

The diagram at lines 195–196 also labels line 1 as the proxy line without fixing its home. Label it as an example where line 0 homes on mesh 0 and line 1 homes on mesh 1. The roles reverse when the homes reverse.

**6. The read-bandwidth attribution mixes runs and counts misses as slice-served bytes.**

Affected text: Question 6, lines 154–155.

The cited per-thread follow-up peaks at **1,371.64 GB/s**, or 1.37 TB/s. The **1,384.77 GB/s**, or 1.38 TB/s, result comes from the earlier bandwidth run. Use that earlier run with its matching counters for the attribution. [Recorded [per-thread follow-up](results/followup3-20261102T031936Z/perthread-asmread-3M-40.csv), [earlier bandwidth run](results/uncore2-20261030T203752Z/bw-asmread-3M-40T-even.csv), and [matching counters](results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv).]

Recomputing the earlier run gives:

| Quantity | Result |
|---|---:|
| Slice accesses | 9,718,737,781 events |
| Slice misses | 280,083,112 events |
| Accesses per application line | 0.449109 events/line |
| Misses per slice access | 2.88189% |
| Bandwidth represented by all slice accesses | 621.91 GB/s, est. |
| Bandwidth represented by accesses minus misses | 603.99 GB/s, est. |

The two bandwidth estimates use the document's model: multiply total application bandwidth by the corresponding event count per application line. The 0.62 TB/s figure includes accesses that missed. Under that same model, the slice-hit contribution is approximately **0.60 TB/s, est.** A slice miss can obtain data elsewhere, so the remainder cannot all be assigned to L2.

Suggested replacement:

> The earlier 40-core run measured 1.38477 TB/s of total reads across both meshes. Its counters recorded 0.449 slice accesses per application line, with 2.882% of those accesses missing. Under the same counter-to-bytes approximation, slice hits account for about 0.60 TB/s, est. The remaining traffic includes private-cache hits and service for slice misses.

Similarly, the 17% L2 share is inferred from `1 − 0.827` slice accesses per application line. It was not directly measured as L2 hits. The corresponding long counter run reports 70.89 GB/s, rather than the separately measured 67 GB/s. Say “the counter run's access rate is consistent with roughly 17% private-cache hits, est., assuming one slice access per line that misses the private caches.” [Recorded [writebw.csv](results/sudo-20261102T054936Z/writebw.csv), access group for `asmread-8M-1`.]

**7. The software recommendation must name the writer placement.**

Affected text: Question 9, line 256.

“Writers spread over both meshes halve the DRAM write bandwidth” is not a general result. The same test file shows opposite effects at different writer counts:

```text
Bandwidth, GB/s; each # represents about 10 GB/s

32 writers, one mesh | ############################  280.18
32 writers, split   | ################################### 346.49
64 writers, one mesh | ####################################### 394.15
64 writers, split   | ################# 172.81
```

Bars start at zero and are rounded for drawing. Splitting 32 writers helped; splitting 64 writers hurt.

| Total writers | All on mesh 0 | Equal split across meshes | Change |
|---|---:|---:|---:|
| 32 | 280.18 GB/s | 346.49 GB/s | +23.67% |
| 64 | 394.15 GB/s | 172.81 GB/s | −56.16% |

These are the best recorded results for the four placements, with 256 MiB per writer. [Recorded [writegrid.csv](results/followup3-20261102T031936Z/writegrid.csv), placements 32+0, 16+16, 64+0 and 32+32.]

Suggested replacement:

> Keep a thread's repeatedly used data associated with a stable reader placement to avoid the measured cross-mesh first-access penalty. For this streaming-write workload, placing 64 writers on mesh 0 outperformed a 32+32 split. Placement effects depend on writer count, so benchmark the intended concurrency.

“Keep data on its own mesh” should describe reuse and thread placement. It must not imply that ordinary buffer allocation changes the per-line address-home hash.

**Smaller corrections and test clarification.**

- **Line 106:** exact balance is still overstated for “a large buffer.” A 1 MiB sub-buffer starting at recorded offset `0xC0` has 8,191 mesh-0 lines and 8,193 mesh-1 lines. Say “the measured 32 MiB buffer,” or “approximately half of a large buffer.” [Recorded [homes.csv](results/sudo-20261102T054936Z/full/homes.csv), line indices 3–16,386.]
- **Line 148:** specify the latency statistic. The median signed difference, other-mesh minus own-mesh, is −0.008672 ns, rounding to −0.01 ns. The median absolute difference is 0.019141 ns, rounding to 0.02 ns. The stated maximum difference of 0.44 ns is correct. [Recorded [latency.csv](results/sudo-20261102T054936Z/full/latency.csv), per-core means of the 64 node medians on each mesh.]
- **Line 247:** specify how private-cache copies will be removed. The residency test must preserve the mesh-cache state it is trying to inspect. Reuse a validated private-cache eviction procedure, rather than leaving “flushed” ambiguous. The existing benchmark uses an 8 MiB randomized eviction buffer and checks the resulting cache state. [Benchmark [homelat.c](../bench/homelat.c), `evict`, `measure` and `verify_slices`.]

**Verification.** I rechecked the address counts, the new latency comparisons, the write-placement results, and the whole-chip access-versus-hit calculation. The reported correlation median of −0.74 and range −0.83 to +0.20 reproduce. The 19.18 ns and 22.39 ns slice medians also reproduce. Both existing counter-analysis runs completed with `checks failed: 0`. No new hardware benchmarks were run.
