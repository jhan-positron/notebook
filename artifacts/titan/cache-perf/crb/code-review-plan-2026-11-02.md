# Fourth review of plan-2026-11-02.md

**Short version:** The final result set is complete, and the main implementation fixes from the third review are verified. Remaining issues concern bypassed validation, incomplete counter summaries, and unsupported conclusions retained in the brief. The saved final run passes the current checks; the validation findings below concern future runs and regeneration.

The plan changed during monitoring. This review uses **“State at 06:30 UTC”**, with plan SHA-256 `6105ba4275d40024bb3ee28132c51a95357d38e36a56785b6cd4c9427b82325c`. The final result set is [sudo-20261102T054936Z](results/sudo-20261102T054936Z/), completed at 06:04:26 UTC. The brief is included because the plan identifies it as an output of this result set. All checks were local. No hardware workload was launched.

Terms: **L2** is a core's private cache. **SLC** is the mesh cache. A **home node** owns an address. A **proxy** can serve a remote-owned address locally. **Pass A** measures the selected home's counters and L2 refills. **Pass B** measures both meshes' counters and L2 refills in a separate execution. Rates below are events per timed load or per application cache line of 64 bytes, as labelled. **P2** means correct the affected validation or conclusion.

**1. P2 — The full-run option bypasses required checks, not just uncertain diagnostics.**

The full run always passes `--verify-lenient`. This suppresses termination for every failure in the cache-state predicate, including multiplexed counters, excessive local-home misses, and latency outside the accepted range. Whole-mesh miss totals have already been removed from that predicate. The bypass is therefore broader than the stated reason for relaxing the check. [run_sudo.sh:67](/home/jhan/workspace/titan/cache-perf/bench/run_sudo.sh:67), [homelat.c:895](/home/jhan/workspace/titan/cache-perf/bench/homelat.c:895)

The earlier self-test uses a different allocation and core. Its success cannot validate a later failure in the full run. A local evaluation with 148 ns latency and one local-home miss per load reaches the failure branch, then continues when this option is enabled.

```mermaid
flowchart LR
    A[Full allocation] --> B[Required check fails]
    B --> C[Lenient mode continues]
    C --> D[Matrix available to reporting]
```

**Correction:** keep invalid counter scheduling and failed local-home residency checks fatal. Record uncertain whole-mesh totals separately. If invalid measurements must be retained, save an explicit validity status and require downstream analysis to reject them.

All eight rows in the final saved check pass the current predicate. This finding does **not** establish a failure in that matrix. [final verify.csv](results/sudo-20261102T054936Z/full/verify.csv), [run.log:79](/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/run.log:79)

**2. P2 — The brief generator discards the strict counter checker's failure status.**

`make-brief.py` reads the checker's standard output without checking its exit status. Its default input is still the superseded 04:06 result set. A local test of the extracted `rates()` function returned 48 numeric rates from that set's cross-mesh file, although the checker exited 1 with 48 missing-idle failures. The resulting caption would still claim measured background subtraction. [make-brief.py:8](/home/jhan/workspace/titan/cache-perf/crb/make-brief.py:8), [rates:51](/home/jhan/workspace/titan/cache-perf/crb/make-brief.py:51), [caption:196](/home/jhan/workspace/titan/cache-perf/crb/make-brief.py:196)

**Correction:** require successful checker completion before parsing rates or writing the brief. Require an explicit result directory, or update and clearly record the selected default. Check that required rates exist instead of substituting missing values.

Both final counter files pass the checker. The issue is that an ordinary regeneration can silently select and publish an invalid older input.

**3. P2 — The brief's memory-request column omits two counters and retains an unsupported utilization claim.**

The split-writer row displays mesh-0 local requests and mesh-1 remote requests only. Its heading says “local / remote,” and the caption says the counts cover both meshes. The omitted counters are substantial when both meshes have writers. [make-brief.py:202](/home/jhan/workspace/titan/cache-perf/crb/make-brief.py:202), [brief:490](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy-brief.html:490)

For 32 writers on each mesh, the final analysis gives:

| Memory-request category | Mesh 0, events/line | Mesh 1, events/line | Both meshes, events/line |
|---|---:|---:|---:|
| Local | 0.771 | 0.645 | 1.416 |
| Remote | 0.253 | 0.268 | 0.521 |
| Combined | 1.024 | 0.913 | 1.937 |

The brief prints approximately **0.77 / 0.27**, omitting **0.898 events per line**. The combined total increases from approximately 1.654 to 1.937 events per line between the two writer placements. These remain event totals from separate counter runs, not unique writes. [final crossmesh.csv](results/sudo-20261102T054936Z/crossmesh.csv), [subtract.py](/home/jhan/workspace/titan/cache-perf/bench/subtract.py)

The caption also says the home nodes are “less busy.” Lower retry and throttle counts do not establish overall home-node utilization. The plan correctly withdrew that inference, but the brief retains it. Its claim that streaming writes are “not kept” also loses the plan's qualification that they *largely* bypass allocation. [plan:145](/home/jhan/workspace/titan/cache-perf/crb/plan-2026-11-02.md:145), [brief:43](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy-brief.html:43), [brief:495](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy-brief.html:495)

**Correction:** display all four counters or explicitly sum each category across both meshes. Carry the plan's narrower conclusions into the generator and regenerate the brief.

**4. P2 — The final verification summary omits the second pass's larger excess.**

The reported L2 range uses only Pass A. The reported whole-mesh maxima use only mesh 0. The final verification file contains these ranges:

| Metric | Range, events per timed load |
|---|---:|
| L2 refills, Pass A | 1.038–1.232 |
| L2 refills, Pass B | 1.024–2.048 |
| SLC accesses, both meshes summed | 1.011–2.126 |
| SLC misses, both meshes summed | −0.006–0.346 |

For remote home `0x218`, Pass A reports 1.204 L2 refills per load, while Pass B reports 2.048. The difference is hidden by the summary's unqualified range of 1.04–1.23. The main report repeats that range. [plan:159](/home/jhan/workspace/titan/cache-perf/crb/plan-2026-11-02.md:159), [verify.csv:8](/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/full/verify.csv:8), [report:204](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html:204)

**Correction:** identify the pass when quoting a range, and sum both meshes when reporting combined totals. Preserve the excess and negative background-adjusted result as unresolved measurement diagnostics. The source comment still assigns whole-mesh misses to traffic triggered by the load. The retained counts do not separate that explanation from residual measurement overhead or unrelated traffic. [homelat.c:892](/home/jhan/workspace/titan/cache-perf/bench/homelat.c:892)

**Insufficient data:** raw per-counter control and measurement deltas, with repeat variation, that would explain the remaining excess. The selected local-home counts still support low miss rates for those sampled local slices.

**5. P2 — The 15% proxy-miss claim reads whole-mesh totals as selected-home counts.**

The 05:00 self-test records `home_acc = 0.000` and `home_miss = 0.000` for **all four remote homes**. The approximately 0.15 values are mesh-wide totals from Pass B. They are not accesses or misses measured at those particular homes. [05:00 verify.csv:6](/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T050043Z/selftest/verify.csv:6)

The plan's description of that run misreads these columns. The interpretation persists in the current source rationale and the final brief's statement about a 15% proxy-miss rate. The brief also calls the sample “eight remote homes,” although it contained four local and four remote homes. [plan:150](/home/jhan/workspace/titan/cache-perf/crb/plan-2026-11-02.md:150), [homelat.c:887](/home/jhan/workspace/titan/cache-perf/bench/homelat.c:887), [brief:500](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy-brief.html:500)

**Correction:** remove the measured 15% forwarding claim from the plan, source rationale, and brief generator. Whole-mesh misses were observed, but their attribution remains unresolved. **Insufficient data:** counters at the serving proxy and selected home over comparable intervals that establish forwarding for those address groups.

**Smaller corrections**

- The latest plan calls the 04:06 mixed baseline “duplicate-affected” and attributes its lower latency to the defect from the third review. That review explicitly said the saved run preceded the defective sampler. The plan's own response says the same. Keep the measured difference, but remove the causal attribution unless a saved source version establishes it. [plan:142](/home/jhan/workspace/titan/cache-perf/crb/plan-2026-11-02.md:142), [plan:160](/home/jhan/workspace/titan/cache-perf/crb/plan-2026-11-02.md:160), [third review:22](/home/jhan/workspace/titan/cache-perf/crb/codex-review-plan-2026-11-02.md:22)
- An empty or idle-only input still makes `subtract.py` report zero failures and exit 0. Reject files without measurement pairs. This does not affect the complete final files. [subtract.py:35](/home/jhan/workspace/titan/cache-perf/bench/subtract.py:35)
- The brief attaches 141 GB/s to all split-writer counter results. The final long runs range from 141.28 to 160.65 GB/s across event sets. Identify the selected run or report that range. The bandwidth collapse remains present. [final crossmesh.csv](results/sudo-20261102T054936Z/crossmesh.csv), [brief:492](/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy-brief.html:492)

**Resolved findings and verification**

| Third-review concern | Verified status |
|---|---|
| Duplicate mixed-chain addresses | Fixed. Local reproductions at 2, 16, and 32 MiB produced 2,048 distinct addresses and seven complete cycles each. Construction rejects duplicates. |
| Four incorrect inferred core positions | Fixed. Re-running `fitpos.py` in temporary directories reproduced both saved JSON files exactly. All 120 positions agree between runs. |
| Missing counters, ignored failures, absent idle controls | Fixed in the checker for nonempty measurement inputs. Invalid-counter, missing-idle, multiplexing, missing-run, and invalid-byte fixtures fail. Both final files pass. Finding 2 concerns the consumer ignoring that result. |
| Unmatched empty control | Fixed. The control now includes filling, eviction, and timing calls. Hardware results exist at the full 2,048-line size. Remaining unexplained counts are finding 4. |
| Unsupported write and bottleneck wording | Corrected in the plan. The brief still needs the changes in findings 3 and 5. |

The final matrix contains **15,360 per-node rows and 120 mixed rows**. Recalculation confirms median repeat spread **2.870%**, with **5.124%** at the 90th percentile. The absolute change from the earlier per-node matrix is **0.21 ns median**, **0.48 ns at the 90th percentile**, and **3.65 ns maximum**. These support the latest plan's rounded values. Repeat spread means `(maximum − minimum) / median` across the seven chains.

The final counter files contain all expected measurement blocks and report 100% counter running time. The cross-mesh file now has measured idle controls for all 16 events. The older cross-mesh file correctly fails with 48 missing-idle errors. These checks establish file completeness and parser behavior; they do not resolve the counter-attribution questions above.
