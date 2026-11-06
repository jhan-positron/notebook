# Review comments for RUN2-PLAN.md — second review

**Short version:** Two measurement issues remain in commit `94572c5`. The earlier high-priority write-protocol finding is resolved. One stale scope sentence also needs correction.

Reviewed the updated plan and the changes from `f81eb51` to `94572c5`. All seven local source, build, and README files match `94572c5`. The first review is retained below as history.

OCM means on-chip memory held in locked cache ways. DRAM is the memory behind the shared system-level cache, or SLC. A home node is the mesh component that owns an address. `cmncount` is the helper that counts mesh requests around a command. KiB means 1,024 bytes and MiB means 1,048,576 bytes. P2 marks a normal-priority issue. P3 marks a minor documentation issue.

1. **[P2] The new background control includes a 2 MiB allocation that the OCM rows do not perform.**

   **Locations:** [RUN2-PLAN.md:123](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:123), [RUN2-PLAN.md:242](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:242), [run_asimov.sh:163](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:163).

   The new control requests 4 KiB, but `alloc_dram` rounds the mapping to 2 MiB and requests a reserved huge page. Run 1 confirms that the 4 KiB row used this allocation path. [common.h:104](/home/jhan/workspace/titan/cache-perf/asimov/common.h:104), [latency-dram-small.csv:3](/home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-001/results/19700101T000000Z/latency-dram-small.csv:3).

   ```text
   Requested: 4 KiB → allocated and cleared: 2 MiB
   ```

   | Quantity implied by the allocation code | Bytes |
   |---|---:|
   | Requested buffer | 4,096 |
   | Huge-page allocation | 2,097,152 |

   The allocation is 512 times the requested buffer size. Linux clears the entire huge page when it is first accessed. That work occurs while the process-wide counters are running. The OCM path maps existing device memory instead of allocating this DRAM buffer. [Linux v6.18 huge-page fault handler](https://github.com/torvalds/linux/blob/v6.18/mm/hugetlb.c#L6073-L6094), [cmncount.c:288](/home/jhan/workspace/titan/cache-perf/asimov/cmncount.c:288), [common.h:145](/home/jhan/workspace/titan/cache-perf/asimov/common.h:145).

   The control therefore includes additional memory traffic, beyond the background it is meant to estimate. Subtracting it from OCM counts or using it as an acceptance threshold is not justified without accounting for that traffic. [README.md:130](/home/jhan/workspace/titan/cache-perf/asimov/README.md:130).

   **Requested change:** Use an ordinary-page control with both reserved and transparent huge pages disabled, or a control that performs matching OCM setup without the measured workload. Adding `--no-hugetlb` alone does not solve this: the fallback explicitly requests transparent huge pages. [common.h:117](/home/jhan/workspace/titan/cache-perf/asimov/common.h:117). **Insufficient data:** the effect on each node's request count needs a corrected control measurement on the emulator.

2. **[P2] The new uptime stamps do not directly measure command duration or launch cost.**

   **Locations:** [RUN2-PLAN.md:233](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:233), [RUN2-PLAN.md:295](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:295), [run_asimov.sh:79](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:79).

   Linux prints `/proc/uptime` with two decimal places, giving 10 ms steps. That is too coarse to resolve the plan's estimated 2–10 ms of added work per small OCM command. [Linux v6.18 uptime implementation](https://github.com/torvalds/linux/blob/v6.18/fs/proc/uptime.c#L31-L35), [RUN2-PLAN.md:250](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:250).

   The script records only command-start stamps. Differences between starts also include output copying, cleanup, and any intervening phase setup. The final command has no following uptime stamp. These intervals cannot isolate process-launch cost. The script also lacks a pair of identical commands run with and without the counter helper. [run_asimov.sh:77](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:77), [run_asimov.sh:232](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:232).

   **Requested change:** If precise command costs are required, record monotonic start and end times immediately around each command, with resolution below 1 ms. Compare the same workload with and without counters to measure the helper's added cost. Otherwise describe the existing stamps as coarse intervals between command starts and retain launch cost as an estimate. **Insufficient data:** the current logging does not provide the claimed direct launch-cost measurement.

3. **[P3] Remove the remaining claim that all handoff measurements are covered.**

   **Location:** [RUN2-PLAN.md:81](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:81).

   “Run 2 covers all five” conflicts with the explicit deferral of per-home-node DRAM-backed latency in section 2.3. The added per-core SLC average resolves that part of the earlier finding. The deferred comparison is still outside this run. [RUN2-PLAN.md:139](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:139), [run_asimov.sh:170](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:170).

   **Requested change:** Say that run 2 covers the listed work except the deferred per-home-node DRAM-backed comparison. No further implementation is requested for this comment.

**Status of the first review**

| Earlier finding | Current status |
|---|---|
| 1. Infer write protocol from total requests | Resolved: the claim is withdrawn in the plan, script, and README. |
| 2. Use 88 GB/s as a placement threshold | Resolved: the comparison uses the same-run control with identical options. |
| 3. Accept counters that never ran | Resolved: failed enables and zero running time produce comments; the plan requires positive running time and at least 95% coverage. |
| 4. Require exactly one node to rise | Partly resolved: background traffic is acknowledged; the new control needs correction in comment 1 above. |
| 5. Omit helper launches from the budget | Launch count corrected; the claimed timing measurement needs correction in comment 2 above. |
| 6. Omit or misstate SLC scope | Per-core measurements added and per-home-node comparison deferred; only the stale sentence in comment 3 remains. |

**Verification performed for this review**

- All three programs compiled locally without warnings using `-O2 -Wall -Wextra -std=gnu11 -pthread -fno-tree-loop-distribute-patterns`. Shell syntax validation passed.
- Safe expansion of the measurement phases confirmed 62 benchmark commands, 46 counted commands, and 108 benchmark/helper executable launches. These counts exclude shell utilities and system-information collection. The quick configuration expands to 15 benchmark commands.
- Temporary simulated counter tests covered an enable error, zero running time, and a successful counter. The first two produced comments instead of numeric rows. The successful case produced the expected count and timing fields. All three preserved the child command's exit status of 7. The absent-counter-device test also preserved that status.
- The added per-core SLC rows use the same 2 MiB footprint and unflushed fresh-chain timing mode as the existing core-2 row. [run_asimov.sh:151](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:151), [run_asimov.sh:170](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:170).

No emulator or Arm hardware measurements were run. The simulated counter tests verify error handling, not hardware event behavior.

<details>
<summary>First review of f81eb51 — historical findings, superseded by the status above</summary>

## First review

**Short version:** Six findings need changes to the measurement claims or acceptance criteria. The fresh-chain and flush implementation matches the plan, but the proposed counters cannot establish the claimed write protocol or bottleneck location.

Reviewed the plan against commit `f81eb51`, its changes from `9c6b8e7`, the handoff, and the run 1 results. All seven local source, build, and README files match `f81eb51` byte for byte.

P1 marks a high-priority issue. P2 marks a normal-priority issue.

Terms used below: OCM is on-chip memory held in locked cache ways. SLC is the shared system-level cache. DRAM is the memory behind that cache. A home node is the mesh component that owns an address. `cmncount` is the helper that counts mesh events around a benchmark command. Chip time is elapsed time inside the emulated chip.

1. **[P1] Remove the write-protocol conclusion from the total request count.**

   **Location:** [RUN2-PLAN.md:97](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:97).

   The plan treats roughly twice the expected request count as evidence of fetching a line before writing it back. The selected `hns_pocq_reqs_recvd_all` event counts all received requests. It does not distinguish a data fetch from a request to acquire write ownership. Arm identifies `MakeUnique`, an ownership request, as dataless. Ownership acquisition followed by writeback can therefore produce two requests without fetching the old data. [Arm CMN S3 Technical Reference Manual, document 107858_0203_05_en, PDF pages 239, 391 and 1216](/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf).

   The count also includes buffer initialization, warm-up writes, and cache flushes. The formula counts the warm-up and eight timed passes, but does not account for all those other operations. This conflicts with the statement that absolute counts are not used. [bandwidth.c:226](/home/jhan/workspace/titan/cache-perf/asimov/bandwidth.c:226), [bandwidth.c:243](/home/jhan/workspace/titan/cache-perf/asimov/bandwidth.c:243), [RUN2-PLAN.md:119](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:119).

   **Requested change:** Limit this row's conclusion to throughput and traffic distribution. To identify the write protocol, separate setup traffic from timed stores and collect events that distinguish data-returning reads from ownership and writeback requests. **Insufficient data:** the selected total-request event cannot resolve that distinction.

2. **[P2] Use the matching placement control instead of an 88 GB/s threshold.**

   **Location:** [RUN2-PLAN.md:98](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:98).

   Run 1 already measured below 88 GB/s with the reference placement, cores 2, 4, 6 and 8. Its best result at the proposed 16 MiB per writer was 86.779 GB/s. The 88.799 GB/s result used 2 MiB per writer. Here, MiB means 1,048,576 bytes and GB/s means billion bytes per second. [bandwidth-perdsu.csv:11](/home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-001/results/19700101T000000Z/bandwidth-perdsu.csv:11), [bandwidth-perdsu.csv:26](/home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-001/results/19700101T000000Z/bandwidth-perdsu.csv:26).

   ```text
   Same core placement, run 1 best write rates (GB/s)
   16 MiB/writer  86.779 ●──────────● 88.799  2 MiB/writer
                          2.020 GB/s gap
   ```

   | Run 1 footprint per writer | Timed passes per repetition | Best rate |
   |---|---:|---:|
   | 2 MiB | 4 | 88.799 GB/s |
   | 16 MiB | 2 | 86.779 GB/s |

   The new placement rows use one timed pass per repetition. A literal “below 88 GB/s” rule would classify the existing reference result as a new bottleneck. [run_asimov.sh:209](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:209).

   **Requested change:** Compare each four-writer placement with the new `2,4,6,8` control using identical options. Define an acceptance tolerance from the repetitions. Report a placement effect if supported. **Insufficient data:** locating the limit before the home nodes requires a measurement of contention at the relevant cluster or mesh link.

3. **[P2] Require counters to have run, not merely to produce numeric records.**

   **Location:** [RUN2-PLAN.md:223](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:223).

   Seven numeric lines do not prove that seven counters measured the command. The helper ignores errors when enabling counters. It also prints an ordinary numeric row with a scaled count of zero when `running_ns` is zero. That row can be mistaken for a valid observation of no traffic. [cmncount.c:285](/home/jhan/workspace/titan/cache-perf/asimov/cmncount.c:285), [cmncount.c:325](/home/jhan/workspace/titan/cache-perf/asimov/cmncount.c:325).

   **Requested change:** Check counter-enable results and mark counters that never ran as unavailable. Require positive `running_ns` for every expected event and node. This field records actual counting time. Also define acceptable coverage relative to `enabled_ns`, the time counting was requested. Reject insufficient coverage before comparing node totals.

4. **[P2] Replace “exactly one node rises” with a criterion that accounts for background traffic.**

   **Locations:** [RUN2-PLAN.md:92](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:92), [RUN2-PLAN.md:224](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:224).

   Counting starts before the child process is created and ends after it exits. This includes executable loading, stack accesses, allocation, output, and kernel activity. Those addresses are not restricted to the selected OCM region. The plan only discusses background kernel traffic, and provides no control measurement for the whole process. [cmncount.c:285](/home/jhan/workspace/titan/cache-perf/asimov/cmncount.c:285), [RUN2-PLAN.md:258](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:258).

   ```text
   Start counts → process setup → benchmark work → exit → stop
   ```

   **Requested change:** Measure background traffic and define the required excess at the selected home node. Alternatively, report the dominant node without requiring the other four counts to stay flat. **Insufficient data:** a comparable control interval is needed to set a numerical background tolerance.

5. **[P2] Include the counter helpers in the chip-time budget.**

   **Location:** [RUN2-PLAN.md:227](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:227).

   Expanding the script's phases with command execution replaced by logging confirms 55 benchmark commands. Of these, 39 invoke `cmncount`. A counted command launches the helper and then the benchmark executable. This gives 94 executable launches before counting shell utilities or system-information collection. The helper also attempts seven counter opens per counted command, for 273 opens across the run. [run_asimov.sh:86](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:86), [cmncount.c:270](/home/jhan/workspace/titan/cache-perf/asimov/cmncount.c:270), [cmncount.c:289](/home/jhan/workspace/titan/cache-perf/asimov/cmncount.c:289).

   ```text
   55 benchmark launches + 39 helper launches = 94 launches
   ```

   The 1.5 s estimate uses the benchmark-command count and the old process-start estimate. It does not identify an allowance for the new helper launches or counter setup.

   **Requested change:** Include these costs explicitly. Measure one representative counted command against the same uncounted command on the emulator before treating the under-2-s criterion as supported. **Insufficient data:** the additional chip time is unmeasured. The launch count alone does not prove that the run will exceed 2 s.

6. **[P2] State the omitted SLC latency measurements as deferred scope.**

   **Locations:** [RUN2-PLAN.md:78](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:78), [RUN2-PLAN.md:135](/home/jhan/workspace/titan/cache-perf/asimov/RUN2-PLAN.md:135).

   The handoff asks for per-home-node DRAM-backed latency compared with OCM. It separately asks for the existing SLC-regime chase from each free core. Run 2 measures OCM latency on cores 4, 6 and 8, but the DRAM-backed latency rows still run only on core 2. The counted 2 MiB streaming read measures request distribution, not latency. The claim that all five handoff requests are covered is therefore too broad. [HANDOFF-2026-11-02.md:40](/home/jhan/workspace/titan/cache-perf/asimov/HANDOFF-2026-11-02.md:40), [handoff:41](/home/jhan/workspace/titan/cache-perf/asimov/HANDOFF-2026-11-02.md:41), [run_asimov.sh:149](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:149), [run_asimov.sh:157](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:157), [run_asimov.sh:173](/home/jhan/workspace/titan/cache-perf/asimov/run_asimov.sh:173).

   **Requested change:** Explicitly defer the per-home-node SLC comparison. For the per-core SLC average, add the existing unflushed `--fresh 3 --sizes 2M` chase on cores 4, 6 and 8, or explicitly defer that measurement too. Remove the statement that buffer distribution was the handoff's only DRAM question.

**Verification performed**

- Compared the seven local source, build, and README files with commit `f81eb51`; all matched.
- Built `latency`, `bandwidth`, and `cmncount` locally with `-O2 -Wall -Wextra -std=gnu11 -pthread -fno-tree-loop-distribute-patterns`; all compiled without warnings.
- Ran `sh -n run_asimov.sh`; syntax check passed.
- Tested the absent-counter-device path: the child command ran and its exit status of 7 was preserved.
- Expanded the script's measurement phases without executing benchmarks or changing host state. The full configuration has 55 benchmark commands and 39 counted commands. The quick configuration has 15 benchmark commands.
- Checked the fresh-chain path: chain zero is warmed, chains one and two are each timed once, and each timed walk starts with a flush. [latency.c:87](/home/jhan/workspace/titan/cache-perf/asimov/latency.c:87), [latency.c:116](/home/jhan/workspace/titan/cache-perf/asimov/latency.c:116).

No emulator or Arm hardware measurements were run for this review. Local compilation and control-flow checks do not validate hardware counter behavior or the chip-time estimate.

</details>
