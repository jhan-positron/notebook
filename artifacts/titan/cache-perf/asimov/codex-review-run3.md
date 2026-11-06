# Review of the run 3 C1-Nano and CME reports

**Short version.** The supplied results pass their checksums, and the main timing and bandwidth values reproduce. The reports need the ten corrections below before their causal conclusions can be relied on. The two highest-priority issues are the claimed CME latency decomposition and the claim that refill counts establish prefetch-free OCM latency.

Reviewed on 2026-11-03. Comments are open. This review does not modify the reports or request another hardware run merely to correct their wording.

## Scope and verified results

Reviewed both HTML reports, `gen_run3.py`, the referenced run 3 and run 2 CSVs, their supplied READMEs, and relevant benchmark code. Run 3 is `results/membench-jibin-004/results/19700101T000000Z/`; run 2 is the corresponding directory under `membench-jibin-002`. CSV references below are relative to run 3 unless stated otherwise.

Words used here: CME is the Compute Matrix Engine; DSU is the two-core cluster; OCM is On-Chip Memory; SLC is the mesh's System Level Cache; PMU is the hardware performance counter unit; TLB is a cache of address translations. A demand load is a load issued by the measured program. A prefetch fetches data before such a load needs it.

Checks that passed:

- All **80 run 3 files** and **57 run 2 files** match their supplied `SHA256SUMS`. Both HTML files exactly match the output of the current generator.
- The run log contains **100 measurement commands** and reports zero failed commands from both suites. All **247 core** and **164 CME** timed latency/control rows report `perf_cov=1.0000`. No CSV contains a `# perf:` failure. All mesh-counter rows have equal enabled and running times. These checks establish measurement coverage, not the causal meaning of each count.
- The core report's repeatability summary reproduces: **33/36 latency comparisons** and **49/54 bandwidth comparisons** are within 1%. The largest changes are **2.5572%** and **2.2942%**, respectively. All eight displayed changes of at least 1% reproduce. [Run 2/run 3 matching latency and bandwidth CSVs; core report table 4.8]
- Sparse per-region bests are higher than run 2's dense bests in **18/20 comparisons**, with a mean difference of **+2.3059 ns/hop**. The observed best-pass ordering by mesh distance holds within every CPU. This verifies the ordering, not an isolated cost of another mesh step. [Both runs' `latency-ocm-region*-cpu*.csv`]
- CME reads peak at **104.865 GB/s at 48 KiB** and span **36.564–37.218 GB/s from 160 KiB onward**. CME writes span **61.971–63.865 GB/s**. At 32 MiB, the CME/core throughput ratios reproduce as **3.986 for reads** and **1.937 for writes**. [Both one-core bandwidth CSVs]
- All **16 SVG figures** were rendered for inspection. All table-of-contents targets resolve. This was a static SVG/HTML review, not a browser interaction test.

Firmware, RTL configuration and power-controller facts were checked against the supplied README descriptions. The underlying external RTL and execution evidence cited there was not independently revalidated. No hardware benchmark was run for this review.

## R1 — P1: The register control is neither a proven latency component nor a universal floor

**Locations:** CME report short version, section 3 map caption, section 9, and section 10's second “settled” item. [`asimov-cme-perf.html:46,71,99,107`]

The report says that 21.0 ns is part of the 21.4 ns chase, that every CME instruction pays it, and that it is the minimum possible dependent-load latency. The measurement does not establish any of those claims. The chase executes `LD1D` then `LASTB`; the control substitutes `DUP` for `LD1D`. No calibration establishes an equal non-memory cost for these different dependency chains. [cme_kern.S:73,88; CME-plan.md section 2.2 item 4]

The measured values are **21.376 ns/hop for the 4 KiB chase** and **21.004 ns/hop for the register control**. Their **0.372 ns/hop difference** is valid arithmetic. It does not isolate memory latency or prove a lower bound. The supplied run README explicitly preserves this distinction. [cme-latency-dram-small.csv:4,13; results/membench-jibin-004/README.md:62]

**Requested change:** retain both raw measurements. Name the difference “chase minus DUP/LASTB control.” Remove “of which,” “floor,” “every CME instruction pays,” and the corresponding “settled” conclusion. This is the caveat already accepted in the plan review's R2.

## R2 — P1: Refill counts do not prove prefetch-free or demand-only latency

**Locations:** both glossaries; core sections 6 and 11; CME section 5's refill-chart caption. [gen_run3.py:542,681–683,702; asimov-cme-perf.html:83]

The core report calls the dense control “clean” and says approximately one refill per load means “no prefetched members.” Both glossaries say 1.00 means every demand load missed. These are stronger conclusions than the counters support. A useful prefetch can replace a later demand refill, leaving total fills per hop near one. The CME source events also include prefetch fills. [CME-plan.md sections 2.1 and 11; Arm C1-SME2 TRM, local text at /scratch/jhan/arm-txt/c1-sme2-trm.txt:4302–4312]

The core report also calls the sparse best an upper bound on demand latency. Positive timer or TLB overhead does not establish that bound while the number of hops receiving faster cached/prefetched service remains unresolved. The CME caption likewise assumes each flushed sparse hop is known to be a demand miss.

**Requested change:** describe the dense control as repeatable and report its measured chase latency. Describe sparse timings as complete-call elapsed time divided by hop count. Remove the demand-only guarantee and upper-bound claim. Use **Insufficient data for demand-only OCM latency** where that distinction matters. A prefetch-disabled run and larger pages address different factors; neither alone establishes freedom from both prefetch and translation effects. Preserve that distinction in the proposed follow-ups. This is the limitation already accepted in the plan review's R10/R11.

## R3 — P2: Cache-service labels ignore copy's second buffer and exceed the available evidence

**Locations:** both reports' table 4.3; CME section 3 diagram, section 6, and section 10's throughput conclusion. [gen_run3.py:582–585,733–736,747–750]

The bandwidth tables assign one “Buffer sits in” label to read, write and copy. Copy touches two buffers, so the displayed per-buffer size is insufficient:

| Displayed size | Copy's combined working set | Current label | Capacity conflict |
|---|---:|---|---|
| 96 KiB | 192 KiB | L2 | Exceeds the 128 KiB L2 |
| 2 MiB | 4 MiB | SLC | Exceeds the 3.75 MiB unlocked SLC |

These sizes follow directly from allocating both `src` and `dst`. The bandwidth rows contain no per-kernel service counters. A shared footprint also does not transfer a chase's service attribution to a stream. [bandwidth.c:200–221; results/membench-jibin-004/README.md, cache capacity and bandwidth sections]

The CME map puts the **52.3 ns result at 128 KiB inside the DSU L3 box** and the **57.6 ns result at 2 MiB inside the SLC box**. Section 10 correctly says those service levels cannot be isolated by these data. The diagram should preserve that uncertainty.

**Requested change:** show per-buffer and combined copy sizes. Label capacity-based regimes as hypotheses, separately by kernel where needed. Report the measured bandwidth by footprint. Do not present the CME's “L3 outward” throughput or its diagram's level-specific latency as established service attribution. This also restores the plan review's R6 caveat.

## R4 — P2: The CME refill chart does not plot the repetition named by its axis

**Location:** CME section 5, “CME L1 refills per load (best rep).” [asimov-cme-perf.html:83; gen_run3.py:249–255,757–759]

The generator plots the minimum inner count and minimum outer count independently. They need not belong to the fastest repetition, or even to the same repetition. The 96 KiB rows demonstrate the mismatch:

| Repetition | Time, ns/hop | Inner refills/hop | Outer refills/hop |
|---|---:|---:|---:|
| 0 | 50.993 | 1.4946 | **15.7932** |
| 1, fastest | **50.966** | **1.4761** | **16.2497** |
| 2 | 51.140 | **1.4001** | 15.9629 |

The chart uses 1.4001 and 15.7932, which combine repetitions 2 and 0. The fastest repetition has 1.4761 and 16.2497. [cme-latency-dram-small.csv:48–50]

**Requested change:** select both counters from the fastest repetition, matching the time plot. Alternatively, label the plot as independent minima and show the ranges. Do not call it “best rep” in that case.

## R5 — P2: Four charts put the SLC capacity marker at the wrong footprint

**Locations:** core latency and bandwidth charts; CME latency and bandwidth charts. [gen_run3.py:612,634,756,767]

The marker uses **3,145,728 bytes**, which is **3 MiB**. The latency charts label it “SLC 3.75 MiB,” whose correct position is **3,932,160 bytes**. The bandwidth charts reuse the same incorrect position. The marker therefore appears 20% below the stated capacity on the footprint axis.

**Requested change:** use the correct byte coordinate and a shared capacity constant. Keep copy's different combined footprint explicit as requested in R3.

## R6 — P2: The reports place the counter helper and all kernel work on the wrong CPUs

**Location:** “C1-Nano, DSU” in both glossaries. [gen_run3.py:532]

The text says the kernel, interrupts and counter helper run on CPUs 0 and 1. The run README says `run_all.sh` was launched pinned to **CPU 2**. `cmncount` does not change its process affinity, so it inherits that placement. Choosing the PMU's control CPU in `perf_event_open` does not pin the helper process to that CPU. [results/membench-jibin-004/README.md, The run and CPU placement; cmncount.c:313–353]

CPU isolation also does not move a benchmark's system calls, page faults, timer interrupts and per-CPU interrupts to CPUs 0 and 1. The supplied README explicitly distinguishes those from default device-interrupt routing.

**Requested change:** state the actual runner/helper placement and default interrupt routing separately. Remove the guarantee that all kernel activity is confined to DSU 0. This matters when explaining counter setup, short timing windows and background traffic.

## R7 — P2: Command-wide mesh counts are described as isolated CME traffic

**Locations:** CME table 4.6's note and section 8. [asimov-cme-perf.html:79,95]

The **7,280,163 requests** for the flushed 8 MiB command are spread evenly across the five home nodes. Those counts span allocation/fill, chain construction, warm-ups, core-side flushes, controls and timed walks. They are not a per-node measurement of CME demand traffic. [cmn-counts.csv:456–460; latency.c:run_size, timed_walk; cmncount.c:run_child]

For scale, the two timed walks contain **262,144 hops**. The total request count cannot be assigned to those hops, or to the CME alone, without separating the rest of the command.

**Requested change:** say that the command's traffic is evenly distributed and that this corroborates the memory layout. Use the CME outer-refill event as evidence of outside-cluster CME refills, with R2's demand/prefetch limit. Remove the claim that this mesh measurement itself proves the distribution of CME-only traffic. The existing plan already makes this distinction.

## R8 — P2: Both hierarchy diagrams put the mesh after DRAM

**Location:** section 3 in both reports. [gen_run3.py:454–461]

The left column is described as the path of a load. It connects the cluster caches, SLC and DRAM, then ends with “then the mesh (right).” The SLC/OCM home nodes are on the mesh, and DRAM-backed misses reach memory through it. The displayed sequence reverses that relationship.

**Requested change:** place the mesh transition after the cluster caches and before the home node. For example:

```mermaid
flowchart LR
    C[Cluster caches] --> M[Mesh] --> H[Home node: SLC or OCM]
    H -->|DRAM-backed miss| D[DRAM]
```

Keep measured chase results separate from unproven service assignments, as requested in R3.

## R9 — P2: The proposed core prefetch measurement names the wrong event range

**Location:** core section 6, “What the sparse passes' refill counts show.” [gen_run3.py:683]

The suggested follow-up names the core's “0x2000-range prefetch events.” The supplied C1-Nano manual instead identifies **0x81BD, `L2D_CACHE_REFILL_HWPRF`**, for L2 refills generated by hardware prefetchers. It also lists specific prefetcher refill events such as **0x00D9** and **0x00DA**. [Arm C1-Nano TRM, local text at /scratch/jhan/arm-txt/c1-nano-trm.txt:7490,7953,7961]

**Requested change:** name the intended event and its verified encoding. Distinguish prefetch requests from prefetch refills. Treat support and counting behavior on this image as something to validate; an event opening successfully is insufficient on the reported kernel.

## R10 — P2: Correct three CME statements that overgeneralize their supporting rows

| Location | Current statement | Correction supported by the data |
|---|---|---|
| Section 2, counter validity | Both refill events are nonzero wherever the CME loads memory | Outer refills are nonzero throughout the timed load rows. **19 of 104 timed load rows have zero inner refills**, including OCM0 passes 2, 4 and 7. This is consistent with outside-cluster service; it does not make those rows invalid. [cme-latency-ocm-region0.csv:14,16,19] |
| Section 2, clock | The 0.9989–1.0000 CME/core-cycle ratio applies to “the CME latency rows” | That range is calculated from the long DRAM chase rows. Qualify the scope. Short control/OCM rows differ; the 82.641 ns/call outlier has 87.5938 CME cycles versus 168.52 core cycles per call, a ratio of about **0.520**. [cme-latency-ocm-all5.csv, first cme-call row; gen_run3.py:263] |
| Section 7, spread caption | CME spreads of 6.1–10.7 ns are “more than” core spreads of 5.9–14.5 ns | The comparison is mixed. CME spreads are smaller for OCM0/1 and larger for OCM2/3/4. For OCM1, the spreads are **6.109 ns CME versus 14.547 ns core**. Report the two ranges without ranking them, or compare each paired region. [cme-latency-ocm-region*.csv; latency-ocm-region*-cpu2.csv] |

## Smaller corrections

- **Match the two CPU 2 controls separately.** The comparison generator matches best rows by size alone. Both CPU 2 controls therefore match run 2's counted control. The uncounted comparison should be **2.015 → 2.014 ns/hop**, rather than using 2.017 ns/hop as its baseline. This does not change the displayed outlier list or headline repeatability totals. Match the command/control identity as well as size. [gen_run3.py:203–213; both runs' latency-control-cpu2.csv]
- **Make sources usable as links.** Every source and companion-report reference is plain text. The only links in either HTML file are table-of-contents anchors. Link the result READMEs, cited CSVs, generator and companion report so readers can inspect the evidence directly.
- **Fix map label overlap.** In the rendered CME map, the DSU L3 label extends beyond its box into the mesh. In both maps, the rightmost node boxes cover part of the `y=2` and `y=3` labels. Wrap the long label and move the coordinate labels outside the boxes. [gen_run3.py:435,458]

## Reviewed versions

The files were unchanged between the start and final verification of this review:

- `asimov-c1nano-perf.html`: SHA-256 `d255d70a6f5f2115775a84a5f564c4c1fc647265a062e1b6ff1a5d42da18707c`
- `asimov-cme-perf.html`: SHA-256 `206db9b5aca58a608220a8627dd36e0e7b5adbe6e1263c78d6e2ec02bf00ffc3`
- `gen_run3.py`: SHA-256 `8382be78734f9417204a6e436c6bb309f81e8633f17322584b8bad8e2f08de5b`

Please make report corrections in the generator and regenerate both pages so the source and rendered reports remain consistent.

## Responses (asimov-be, 2026-11-03)

Every comment was checked against the CSVs, the code or the Arm manual text before the change was made. All thirteen are accepted; the fixes are in gen_run3.py and both pages were regenerated from it.

| Comment | Verified how | Disposition |
|---|---|---|
| R1 register control | cme_kern.S:73 (LD1D then LASTB) against :88 (DUP then LASTB); CME-plan.md section 2.2 | Fixed. "Of which", "floor", "every CME instruction pays" removed from the short version, the map caption, section 9 and the settled item. Both raw numbers stay; their difference is named "chase minus DUP/LASTB control, a derived number". The settled item now says what part of a hop is memory latency is Insufficient data. |
| R2 refill counts | CME-plan.md sections 2.1 and 11 | Fixed. "refills per load" now says a fill can be a demand miss or a prefetch and a useful prefetch can replace a later demand fill. "Clean" and "no prefetched members" removed; the dense control is described as repeatable with 1.00 fills per load at each level, demand-only status Insufficient data. The "bound from above" claim removed; a sparse pass is complete-call elapsed time over 64 hops. The follow-ups now say a prefetcher-off boot removes the prefetch term and larger pages the translation term, and only both together give a demand-only number (section 6, section 11, and the open item). |
| R3 copy's two buffers, service labels | bandwidth.c allocates src and dst for copy | Fixed. Both tables 4.3 show the displayed size and copy's combined size, and the last column is "capacity reading (hypothesis)" given separately for read/write and for copy. The CME map's L3 and SLC boxes now say "serving level not measured"; section 6 and the section 10 throughput item say "at every footprint from 160 KiB on" instead of naming levels. |
| R4 refill chart | cme-latency-dram-small.csv:48-50 (rep 1 fastest: 1.4761 / 16.2497; the chart had 1.4001 and 15.7932 from reps 2 and 0) | Fixed. Both series are taken from the fastest rep of each footprint (best_pass); the axis label says so and the hover text gives the range over reps. The caption quotes the fastest-rep values. |
| R5 SLC marker | 3.75 MiB = 3,932,160 bytes; the code had 3,145,728 | Fixed. One constant SLC_BYTES (5 x 1 MiB x 12/16) used for the four markers and the level labels. |
| R6 CPU placement | cmncount.c has no affinity call; Jesse's README, The run (run_all.sh pinned to CPU 2) and CPU placement | Fixed. The glossary and the DSU 0 box now say: device interrupts to CPUs 0-1, no unpinned task on 2-9, the scripts and the counter helper pinned to CPU 2 by the init, each measured program pinned to its --cpu, every core taking its own timer and per-CPU interrupts, page faults and system calls. The earlier "housekeeping" wording is gone. |
| R7 command-wide mesh counts | cmncount wraps the whole command; latency.c run_size fills, builds, warms up and flushes inside it | Fixed. Table 4.6's note and section 8 say the counts cover the whole command (fill, chain build, warm-up, flushes, controls, walks), that the even spread fits the address hash, and that the 262,144 timed hops cannot be separated from it; the CME outer-refill event is named as the direct evidence of outside-cluster refills, with R2's limit. |
| R8 diagram order | the left column ended with "then the mesh" after DRAM | Fixed. Both left columns now read cluster caches, then "mesh: to the home node that owns the line", then "Home node: SLC or OCM", then "DRAM, behind the home node". The section 3 text says the same. |
| R9 prefetch events | /scratch/jhan/arm-txt/c1-nano-trm.txt:7490 (0x81BD L2D_CACHE_REFILL_HWPRF), :7953 (0x00D9), :7961 (0x00DA), plus 0x00DB, 0x010F, 0x0110 | Fixed. Section 6 names 0x81BD and the per-prefetcher refill events, calls them refills (not requests), and says each must be validated by its counts because the kernel opens any event number. |
| R10a inner refills | 19 of 104 timed CME load rows have inner = 0 (counted by the generator); outer > 0 in all 104 (asserted) | Fixed. Section 2 now gives those counts and says zero inner on an OCM pass fits outside-cluster service. |
| R10b clock ratio scope | CME_RATIO is computed from the DRAM chase rows only; cme-latency-ocm-all5.csv first cme-call rep: 82.641 ns, 87.59 CME against 168.52 core cycles, ratio 0.520 | Fixed. The clock bullet scopes the 0.9989-1.0000 range to the DRAM chase rows of 65,536 loads or more and quotes the slow call rep's 0.52 with the reason (core cycles include work outside the streaming span). |
| R10c spreads | per region, CME against core from CPU 2: 7.0/7.8, 6.1/14.5, 8.5/6.7, 10.7/6.1, 9.6/5.9 ns | Fixed. The caption gives both ranges without ranking and says the CME spread is smaller for OCM0 and OCM1 and larger for OCM2 to OCM4. |
| Smaller: the two CPU 2 controls | latency-control-cpu2.csv holds two best rows in each run (run 3: 2.012 counted, 2.014 uncounted; run 2: 2.017, 2.015) | Fixed. The comparison matches the k-th best row of a size with the k-th in run 2 and labels the controls counted and uncounted. Neither control moved 1 %, so table 4.8 and the totals are unchanged (36 latency rows, 33 within 1 %, largest 2.56 %). |
| Smaller: links | the sources were plain text | Fixed. The sources and the companion-page references on both pages are relative links to the results directories, the READMEs, the generator, the plan, the review, the kernels and the companion page. |
| Smaller: map overlap | rendered with headless Chromium before and after | Fixed. The L3 box title is shortened to "DSU L3, 256 KiB (core L1, L2 bypassed)", the DRAM title to "DRAM, behind the home node (emulator)", and the y labels moved outside the rightmost boxes. Re-rendered and checked. |

Not changed: the chase, control and bandwidth numbers themselves, the repeatability totals, and the sparse-against-dense comparison, all of which the review reproduced.

Regenerated versions:

- `asimov-c1nano-perf.html`: SHA-256 `99e93cf6ce26ac1dcf5cdf936753b7a7199243f1075ae6c0e6b499a9769340d9`
- `asimov-cme-perf.html`: SHA-256 `205453cf91fe8983556bbe2736d911efc5e4b65f04cd958685aace62491b1af3`
- `gen_run3.py`: SHA-256 `b315a06d30d82349a66415363921a9da9ddb147cbfb04e52fe51eca3f24aa11a`
