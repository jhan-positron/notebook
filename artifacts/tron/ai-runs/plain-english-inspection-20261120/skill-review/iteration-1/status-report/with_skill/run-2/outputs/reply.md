# Status report: jf2 allocator test in kestrel (2026-11-20)

## Short version

We tested jf2 (our fork of the jemalloc memory allocator) in kestrel (our key-value store) on a read-heavy workload. The p99 latency (99% of requests finish faster) fell from 2140 to 870 microseconds, and throughput changed by under 1%. Memory use rose by 5.7 GB (9.3%), and the capacity team must approve that before we enable jf2 in staging.

## Words used here

- Build A: commit 4f1c2aa of the main branch with jemalloc 5.3.
- Build B: the same commit with jf2.
- ycsb-b: the read-heavy workload of YCSB (a standard key-value benchmark). Its standard mix is 95% reads and 5% updates [Ref1].
- ycsb-a: the write-heavy YCSB workload. Its standard mix is 50% reads and 50% updates [Ref1].
- us: microseconds.
- kops/s: thousands of operations per second.
- p50 and p99.9 latency: 50% and 99.9% of requests finish faster. The p50 is the median.
- RSS (resident set size): the physical memory that the kestrel process holds.
- Decay purge: jemalloc returns unused memory to the operating system after a delay. This step is the decay purge.
- Staging: the pre-production environment.

## Test setup

- The host was bench-07. It has two 32-core Xeon processors, 512 GB of memory and Linux kernel 6.8.
- The load average (average number of runnable tasks) before the runs was 0.4. That is nearly idle for 64 cores.
- Builds A and B are the same commit. Only the allocator differs.
- The workload was ycsb-b with 64 client threads.
- Each build ran 5 times, 10 minutes per run. The runs alternated A, B, A, B.

## Results

Each value is the median of 5 runs, with the lowest and highest run in parentheses.

```
|--o--| = lowest run, median, highest run. Lower is better.

p99 latency in us (1 character = 50 us)
  0                   1000                2000                3000
  +-------------------+-------------------+-------------------+
A                                       |----o--------|  2140 us
B                 |o-|  870 us
  B median is 59% lower. The ranges do not overlap.

p99.9 latency in us (1 character = 250 us)
  0                   5000                10000               15000
  +-------------------+-------------------+-------------------+
A                              |---------o----------------|  9800 us
B            |o---|  3100 us
  B median is 68% lower. The ranges do not overlap.
```

The two charts use different scales.

| Metric | Build A (jemalloc 5.3) | Build B (jf2) | Change in median |
|---|---|---|---|
| Throughput, kops/s | 412 (405..418) | 409 (401..415) | -3 (-0.7%) |
| p50 latency, us | 118 (116..121) | 119 (117..121) | +1 (+0.8%) |
| p99 latency, us | 2140 (1890..2610) | 870 (820..940) | -1270 (-59%) |
| p99.9 latency, us | 9800 (7200..14100) | 3100 (2700..3900) | -6700 (-68%) |
| RSS at end of run, GB | 61.2 | 66.9 | +5.7 (+9.3%) |

- p99 latency fell by 1270 us (59%). The highest B run (940 us) is below the lowest A run (1890 us). So the two ranges do not overlap.
- p99.9 latency fell by 6700 us (68%). Again the highest B run (3900 us) is below the lowest A run (7200 us).
- Throughput fell by 3 kops/s (0.7%), and p50 latency rose by 1 us (0.8%). Runs of one build differ by more than that: 13 to 14 kops/s and 4 to 5 us. So this test does not show a change in either metric.
- RSS at the end of the run rose by 5.7 GB (9.3%). RSS has one value per build here, with no lowest and highest run.

## What the profile of build A shows

- Build A has latency spikes (short periods of high latency). They occur at the same times as the decay purge.
- We profiled build A during the spikes with perf (the Linux sampling profiler). Of those samples, 31% were in je_arena_decay (the jemalloc purge function).
- Build B runs the purge in a background thread.

Hypothesis: the background-thread purge is the reason for the smaller spikes in build B. A perf profile of build B during its slowest requests would confirm or reject this.

## One build B run was replaced

- Run 3 of build B stalled for 40 s at minute 7.
- The cause was logrotate (a log rotation tool). Cron (the system job scheduler) started it during the run. The allocator did not cause the stall.
- We repeated the run. The build B results use the repeat, not the original run 3.

## Not tested

- ycsb-a, the write-heavy workload
- more than 64 client threads
- NUMA pinning. NUMA means non-uniform memory access: each processor has its own memory. Pinning binds kestrel threads to chosen processors and their memory.

So the results hold only for ycsb-b at 64 threads without pinning.

## Open question

Is the extra 5.7 GB of RSS (9.3%) acceptable? We need an answer from the capacity team.

## Next steps

1. Run ycsb-a tomorrow (2026-11-21).
2. Ask the capacity team whether the extra 5.7 GB is acceptable.
3. If the capacity team approves, enable jf2 in staging. A feature flag (an on/off setting) will control it.

## References

- [Ref1] YCSB core workloads: https://github.com/brianfrankcooper/YCSB/wiki/Core-Workloads

---

Notes for you, not part of the report:

- Your notes give no lowest and highest run for RSS. I treated 61.2 GB and 66.9 GB as medians.
- I wrote "tomorrow" as 2026-11-21. That date is a Saturday.
- The YCSB read and update percentages come from the public YCSB definition, not from your notes. Remove them if kestrel uses a custom mix.
- I labeled the cause of the improvement as a hypothesis. Your notes hold a profile of build A only.