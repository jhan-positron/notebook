# Status report: jf2 allocator test on kestrel (2026-11-20)

## Short version

We tested jf2 (our fork of the jemalloc memory allocator) in kestrel (our key-value store) under a read-heavy workload. The p99 latency (99% of requests finish within it) fell by 59%, and throughput changed by less than 1%. Memory use rose by 5.7 GB (9.3%), and the capacity team must approve that increase.

## Words used here

- **ycsb-b** is workload B of YCSB (the Yahoo! Cloud Serving Benchmark). It is read-heavy, with 95% reads and 5% updates.
- **ycsb-a** is workload A of YCSB. It is write-heavy, with 50% reads and 50% updates.
- **kops/s** means thousand operations per second.
- **us** means microseconds.
- **p50 and p99.9 latency** use the same definition as p99, for 50% and 99.9% of requests. p50 is the median latency.
- **RSS** (resident set size) is the physical memory that the kestrel process holds.
- **Decay purge** is a jemalloc step that returns unused memory to the operating system after a delay.
- **perf** is the Linux profiler. It samples which function each CPU is running.
- **NUMA pinning** binds threads to the CPUs and memory of one processor socket. NUMA means non-uniform memory access.

## Test setup

The goal was to check whether jf2 removes the latency spikes (short periods of high latency) in kestrel. These spikes raise the p99 latency.

- The host was bench-07, a benchmark server with two 32-core Xeon processors and 512 GB of memory. It runs Linux kernel 6.8.
- The load average before the runs was 0.4 on 64 cores, so the host was almost idle.
- Build A is the main branch at commit 4f1c2aa with jemalloc 5.3, the allocator in use today.
- Build B is the same commit with jf2 in place of jemalloc 5.3.
- The workload was ycsb-b with 64 client threads.
- Each build ran 5 times, for 10 minutes per run. The runs alternated between the builds: A, B, A, B, and so on.

## Results

```
p99 latency in us (lower is better)
  A  █████████ 2140
  B  ███ 870                  59% lower

p99.9 latency in us (lower is better)
  A  ███████████████████████████████████████ 9800
  B  ████████████ 3100        68% lower

One block is 250 us. Bars show the median of 5 runs.
```

Only the p99 and p99.9 latencies changed. Throughput and p50 latency stayed the same.

| Metric | Build A | Build B | Change of median |
|---|---|---|---|
| Throughput, kops/s | 412 (405 to 418) | 409 (401 to 415) | -0.7% |
| p50 latency, us | 118 (116 to 121) | 119 (117 to 121) | +0.8% |
| p99 latency, us | 2140 (1890 to 2610) | 870 (820 to 940) | -59% |
| p99.9 latency, us | 9800 (7200 to 14100) | 3100 (2700 to 3900) | -68% |
| RSS at end of run, GB | 61.2 | 66.9 | +5.7 GB (+9.3%) |

Each cell shows the median of 5 runs, then the lowest and highest run in parentheses. No range was recorded for RSS.

- The p99 and p99.9 gains exceed the run-to-run variation. For both metrics, the highest build B run is below the lowest build A run.
- Throughput and p50 latency show no measurable change. The medians differ by less than 1%, and the run ranges of the two builds overlap.
- RSS at the end of the run is 5.7 GB higher with jf2, a 9.3% increase.

## Why build A has spikes

- In build A, the latency spikes occur at the same times as the decay purge.
- During the spikes, 31% of the perf samples are in je_arena_decay (the jemalloc purge function).
- Build B runs the purge in a background thread. We think this is the reason for the gain.
- That reason is a hypothesis, because build B has no recorded perf profile. A profile of build B during purges would confirm or reject it.

## One build B run was replaced

- Run 3 of build B stalled for 40 s at minute 7.
- We traced the stall to logrotate (the log rotation tool). The system scheduler cron starts it every night. The allocator was not involved.
- We ran run 3 again. The build B results use the rerun, not the stalled run.

## Not tested

These cases were not tested, so the results do not cover them:

- ycsb-a, the write-heavy workload
- more than 64 client threads
- NUMA pinning

## Open question

The RSS increase of 5.7 GB (9.3%) needs a decision from the capacity team. We do not know yet whether it is acceptable.

## Next steps

1. Run ycsb-a tomorrow (2026-11-21).
2. Ask the capacity team whether the RSS increase is acceptable.
3. If it is, enable jf2 in staging (the pre-production environment). A feature flag (an on/off configuration switch) will control it.

---

Four things in the report are not in your notes, so check them before you send it:

- The 95%/5% and 50%/50% read/update mixes come from the standard YCSB definitions. Correct them if your configuration differs.
- The percent changes for throughput, p50, p99 and p99.9 are computed from your medians.
- The hypothesis bullet assumes that build B was not profiled. Remove it if you have a perf profile of build B.
- "Tomorrow" became 2026-11-21, which is a Saturday.