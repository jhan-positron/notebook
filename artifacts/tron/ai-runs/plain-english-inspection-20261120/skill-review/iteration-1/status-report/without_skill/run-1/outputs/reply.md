# Status report: jf2 allocator test on kestrel, 2026-11-20

## Short version

We tested whether jf2 (our fork of the jemalloc memory allocator) removes the p99 latency spikes in kestrel (our key-value store). On the one workload tested, p99 latency (99% of requests finish within this time) fell from 2140 us to 870 us (59% lower), and throughput did not change measurably. Two items are open: jf2 uses 5.7 GB (9.3%) more memory, and the write-heavy workload is not tested yet.

## Words used here

- **jemalloc**: an open-source memory allocator, the library that hands out and frees memory for a program.
- **p50 / p99 / p99.9 latency**: the time within which 50% / 99% / 99.9% of requests finish.
- **Latency spike**: a short period in which request latency is much higher than normal.
- **YCSB**: Yahoo! Cloud Serving Benchmark, a standard load generator for key-value stores.
  - ycsb-b is 95% reads and 5% updates.
  - ycsb-a is 50% reads and 50% updates.
- **kops/s**: thousand operations per second.
- **RSS**: resident set size, the physical memory the process holds.
- **Decay purge**: the jemalloc step that returns unused memory to the operating system after a delay. `je_arena_decay` is a jemalloc function in that step.
- **perf**: the Linux sampling profiler.
- **NUMA pinning**: binding threads and memory to one CPU socket on a multi-socket machine.

## Setup

- **Host**: bench-07 (2 x 32-core Xeon, 512 GB RAM), Linux kernel 6.8.
- **Load before the runs**: load average 0.4 on 64 cores, so the machine was almost idle.
- **Build A**: main@4f1c2aa with jemalloc 5.3.
- **Build B**: the same commit with jf2. The allocator is the only difference.
- **Workload**: ycsb-b, 64 client threads, 10 minutes per run.
- **Runs**: 5 per build, in alternating order (A, B, A, B, ...).

## Results

```
Median of 5 runs. 1 block = 200 us (rounded). Lower is better.

p99    A  ███████████ 2140 us
       B  ████ 870 us                    59% lower
p99.9  A  █████████████████████████████████████████████████ 9800 us
       B  ████████████████ 3100 us       68% lower
```

Only p99 and p99.9 moved. Throughput and p50 changed by less than 1%.

| Metric | A: jemalloc 5.3 | B: jf2 | Change, B vs A | Min..max ranges overlap? |
|---|---|---|---|---|
| Throughput (kops/s) | 412 (405..418) | 409 (401..415) | -3 (-0.7%) | Yes |
| p50 latency (us) | 118 (116..121) | 119 (117..121) | +1 (+0.8%) | Yes |
| p99 latency (us) | 2140 (1890..2610) | 870 (820..940) | -1270 (-59.3%) | No |
| p99.9 latency (us) | 9800 (7200..14100) | 3100 (2700..3900) | -6700 (-68.4%) | No |
| RSS at end (GB) | 61.2 | 66.9 | +5.7 (+9.3%) | Range not recorded |

Values are the median of 5 runs, with min..max in parentheses.

- **p99 and p99.9**: the slowest B run was faster than the fastest A run on both metrics.
- **Throughput and p50**: the ranges of the two builds overlap, so this test shows no difference.

## Cause of the spikes

- **Observation**: in build A, the spikes occur at the same times as the jemalloc decay purge.
- **Evidence**: perf puts 31% of the samples from the spike windows in `je_arena_decay`.
- **Difference in B**: jf2 runs the purge in a background thread.
- **Hypothesis**: moving the purge off the request threads is the reason p99 fell. A perf profile of build B during its slowest windows would confirm or reject this.

## Discarded run

- Run 3 of build B had a 40 s stall at minute 7.
- We traced the stall to the nightly logrotate job (log file rotation, started by the cron scheduler). The allocator was not the cause.
- We reran that run. The results above use the rerun.

## Not tested

- ycsb-a (write-heavy).
- More than 64 client threads.
- NUMA pinning.

The result above holds only for ycsb-b at 64 threads without NUMA pinning.

## Open decision

Is an RSS increase of 5.7 GB (9.3%) acceptable? The capacity team must approve it.

## Next steps

1. Run ycsb-a tomorrow (2026-11-21).
2. Ask the capacity team about the RSS increase.
3. If the capacity team approves, enable jf2 in staging, controlled by a feature flag.

---

Notes from me, outside the report:

- **Added facts**: the YCSB read/update mixes are the standard YCSB definitions, not from your notes. Check that they match your configuration.
- **Derived numbers**: I computed the percent changes for throughput, p50, p99, and p99.9 from your medians.
- **Hypothesis label**: your notes state the purge link as an observation. I labeled the causal step as a hypothesis, and I added the confirming measurement myself.
- **Possible control run**: stock jemalloc 5.3 has a `background_thread:true` option that also purges in a background thread. Your notes do not say whether build A had it enabled. A run of build A with that option would separate the background-purge effect from the other jf2 changes.