# Status report: jf2 allocator test in kestrel (2026-11-20)

## Short version

We tested whether jf2 (our fork of the jemalloc memory allocator) reduces latency spikes in kestrel (our key-value store). On a read-mostly workload, p99 latency (the time 99% of requests finish within) fell from 2140 to 870 microseconds. Memory use rose by 5.7 GB (9.3%), and the capacity team must approve that increase.

## Words used here

- **Build A** is the main branch at commit 4f1c2aa with jemalloc 5.3. **Build B** is the same commit with jf2.
- **YCSB** (Yahoo! Cloud Serving Benchmark) is a standard load test for key-value stores. **YCSB-B** is its read-mostly workload, and **YCSB-A** is its write-heavy workload.
- **p50 and p99.9 latency** are defined like p99, for 50% and 99.9% of requests.
- **us** means microseconds. **kops/s** means thousand operations per second.
- **RSS** (resident set size) is the physical memory that the process holds.
- **Decay purge** is the step where jemalloc returns unused memory to the operating system.

## Test setup

- The host was bench-07: two 32-core Xeon processors, 512 GB of memory, Linux kernel 6.8.
- The load average was 0.4 before the runs. That is the average number of runnable tasks, so the 64 cores were nearly idle.
- The workload was YCSB-B with 64 client threads.
- Each build ran 5 times, for 10 minutes per run. The runs alternated A, B, A, B, so slow changes on the host affect both builds equally.

### One replaced run

Run 3 of build B had a 40-second stall at minute 7. We traced the stall to logrotate (a nightly log-archiving job), not to the allocator. We reran run 3, and the results below use the rerun.

## Results

```
Latency, median of 5 runs (one █ = 250 us, rounded)

p99    A █████████ 2140 us
       B ███ 870 us  (-59%)

p99.9  A ███████████████████████████████████████ 9800 us
       B ████████████ 3100 us  (-68%)
```

Both latency values for build B are less than half of the build A values.

| Metric | Build A (jemalloc 5.3) | Build B (jf2) | Change |
|---|---|---|---|
| Throughput, kops/s | 412 (405 to 418) | 409 (401 to 415) | -0.7% |
| p50 latency, us | 118 (116 to 121) | 119 (117 to 121) | +0.8% |
| p99 latency, us | 2140 (1890 to 2610) | 870 (820 to 940) | -59% |
| p99.9 latency, us | 9800 (7200 to 14100) | 3100 (2700 to 3900) | -68% |
| RSS at end of run, GB | 61.2 | 66.9 | +5.7 GB (+9.3%) |

Each cell shows the median of 5 runs. The lowest and highest runs follow in parentheses.

## What the results show

- p99 latency fell by 59%, from 2140 us to 870 us. The highest build B run (940 us) is below the lowest build A run (1890 us). So the drop is larger than the variation between runs.
- p99.9 latency fell by 68%, from 9800 us to 3100 us. The highest build B run (3900 us) is below the lowest build A run (7200 us).
- Throughput and p50 latency did not change measurably. The medians differ by 0.7% for throughput and by 0.8% for p50 latency. For both metrics, the build A and build B ranges overlap.
- RSS at the end of the run rose by 5.7 GB (9.3%), from 61.2 GB to 66.9 GB.

## Likely cause of the spikes

- In build A, the spikes occur at the same times as the decay purge.
- A profile of build A from perf (the Linux profiler) supports this. In the time windows of the spikes, 31% of the samples were in je_arena_decay (the jemalloc purge function).
- Build B does the purge in a background thread.
- The hypothesis is that the purge delays requests in build A, and build B avoids that delay. A perf profile of build B during its slowest periods would confirm or reject this.

## Not tested

- YCSB-A, the write-heavy workload
- more than 64 client threads
- NUMA pinning (binding threads and memory to one processor socket)

So these results apply only to a read-mostly workload with 64 client threads.

`Insufficient data`: the variation of RSS between runs. The notes give one RSS value per build. The per-run RSS values would resolve this.

## Open item

The capacity team must decide whether the RSS increase of 5.7 GB (9.3%) is acceptable.

## Next steps

1. Run YCSB-A tomorrow (2026-11-21).
2. Ask the capacity team to approve the RSS increase.
3. If they approve, enable jf2 in staging (the pre-production environment). A feature flag (a configuration switch) will control it.

---

Notes for you, not part of the report:

- I read "if ok" as "if the capacity team approves". The YCSB-A result is not a condition in step 3. Change step 3 if you meant both.
- "Read-mostly" for YCSB-B comes from the standard YCSB definition, not from your notes.
- I computed the percent changes for throughput, p50, p99 and p99.9 from your medians. I computed them by hand, since this session has no shell tool.
- jemalloc 5.3 has an option named `background_thread`. It moves the purge to a background thread without a fork. Build A may not have set it. In that case, one build A run with the option set would show how much of the gain needs jf2.