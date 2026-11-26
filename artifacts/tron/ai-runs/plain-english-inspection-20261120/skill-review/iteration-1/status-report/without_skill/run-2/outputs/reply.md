# Status report: jf2 allocator test on kestrel (2026-11-20)

## Short version

- On the read-heavy benchmark, the jf2 memory allocator (our fork of jemalloc) cut the 99th-percentile request latency of kestrel (our key-value store) from 2140 us to 870 us, which is 59% lower.
- Throughput and median latency did not change measurably, and memory use rose by 5.7 GB (9.3%).
- Next, we will run the write-heavy benchmark, and the capacity team must approve the memory increase before we enable jf2 in staging (the pre-production environment).

## Words used here

- **jemalloc**: the memory allocator library that kestrel uses today, at version 5.3.
- **YCSB-B / YCSB-A**: two workloads of the Yahoo Cloud Serving Benchmark. B is read-heavy (95% reads, 5% updates in the standard mix). A is write-heavy (50% reads, 50% updates in the standard mix).
- **p50, p99, p99.9**: latency percentiles. For example, 99% of requests finished faster than the p99 value.
- **us**: microseconds.
- **kops/s**: thousand operations per second.
- **RSS**: resident set size, the physical memory that the process holds.
- **Decay purge**: the step in which jemalloc returns unused memory to the operating system after a delay.
- **perf**: the Linux sampling profiler.
- **je_arena_decay**: the jemalloc function that performs the decay purge.
- **NUMA pinning**: binding a process to the CPUs and memory of one processor socket.
- **logrotate**: a system job that rotates log files. Here cron (the Linux job scheduler) starts it every night.

## Test setup

- **Goal**: check whether jf2 removes the p99 latency spikes (short periods of high latency) in kestrel.
- **Host**: bench-07 (the test host), 2 x 32-core Xeon, 512 GB memory, Linux kernel 6.8.
- **System load**: the load average was 0.4 before the runs, so the 64-core host was almost idle.
- **Build A**: main@4f1c2aa with jemalloc 5.3.
- **Build B**: the same commit with jf2.
- **Workload**: YCSB-B with 64 client threads.
- **Runs**: 5 runs per build, 10 minutes each, in alternating order (A, B, A, B, ...).

## Results

High-percentile latency, median of 5 runs (1 block = 250 us):

```
p99    A  █████████ 2140 us
       B  ███ 870 us                  59% lower
p99.9  A  ███████████████████████████████████████ 9800 us
       B  ████████████ 3100 us        68% lower
```

Only the high percentiles changed. Throughput and median latency stayed inside the run-to-run spread.

| Metric | Build A (jemalloc 5.3) | Build B (jf2) | Change |
|---|---|---|---|
| Throughput (kops/s) | 412 (405..418) | 409 (401..415) | -0.7%, ranges overlap |
| p50 latency (us) | 118 (116..121) | 119 (117..121) | +0.8%, ranges overlap |
| p99 latency (us) | 2140 (1890..2610) | 870 (820..940) | -59%, ranges do not overlap |
| p99.9 latency (us) | 9800 (7200..14100) | 3100 (2700..3900) | -68%, ranges do not overlap |
| RSS at end of run (GB) | 61.2 | 66.9 | +5.7 GB (+9.3%), range not recorded |

Values are the median of 5 runs, with min..max in parentheses.

## Findings

1. **jf2 lowered the high-percentile latency.**
   - Median p99 fell from 2140 us to 870 us.
   - Median p99.9 fell from 9800 us to 3100 us.
   - The slowest B run (940 us p99) was faster than the fastest A run (1890 us p99).

2. **Throughput and median latency did not change measurably.**
   - Median throughput differed by 3 kops/s. The spread inside each build was 13 to 14 kops/s.
   - Median p50 differed by 1 us. The spread inside each build was 4 to 5 us.

3. **The decay purge is the likely cause of the spikes in build A.**
   - The spikes in build A occur at the same times as the decay purge.
   - perf attributed 31% of the samples in the spike windows to je_arena_decay.
   - jf2 runs the purge in a background thread, and build B has the lower p99 and p99.9.

4. **jf2 uses more memory.**
   - RSS at the end of the run was 61.2 GB for build A and 66.9 GB for build B.

## Caveats

- **Run 3 of build B was replaced.**
  - The original run had a 40 s stall at minute 7.
  - We traced the stall to logrotate, not to the allocator.
  - We reran the run, and the build B figures use the rerun.
- **Three cases are not tested.** Insufficient data for each one until we run it:
  - YCSB-A (write-heavy).
  - More than 64 client threads.
  - NUMA pinning.

## Open question

- Is the RSS increase of 5.7 GB (9.3%) acceptable? The capacity team must approve it.

## Next steps

1. Run YCSB-A tomorrow.
2. Ask the capacity team about the RSS increase.
3. If the capacity team approves, enable jf2 in staging behind a feature flag (a configuration switch that turns it on or off).

---

Two points to check before you send this:

- **YCSB mixes**: I added the read/update ratios (95/5 for B, 50/50 for A) from the standard YCSB definitions. Your notes do not state them, so remove them if kestrel's runs use a custom mix.
- **RSS values**: your notes give one RSS value per build with no range. I do not know whether each is a median or a single run, so the table says "range not recorded".