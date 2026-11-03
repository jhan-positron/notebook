# Review comments for RUN2-PLAN.md

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
