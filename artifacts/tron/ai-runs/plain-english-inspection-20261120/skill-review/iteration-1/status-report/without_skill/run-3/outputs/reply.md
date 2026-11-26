# Status report: jf2 allocator test on kestrel (2026-11-20)

## Short version

jf2 (our fork of the jemalloc memory allocator) made the slowest 1% of requests in kestrel (our key-value store) faster: p99 latency fell from 2140 microseconds (us) to 870 us, 59% lower, on a read-mostly workload. Throughput and median latency stayed inside the range seen between repeated runs. jf2 used 5.7 GB (9.3%) more memory, and the capacity team must approve this cost before we enable jf2 in staging.

## Words used here

- **jemalloc**: the memory allocator kestrel uses today, version 5.3.
- **Purge**: the allocator returns unused memory to the operating system after a delay. jemalloc 5.3 calls this "decay purge".
- **Latency spike**: a short period when requests take much longer than usual.
- **p50, p99, p99.9**: latency percentiles. For example, 99% of requests finish faster than the p99 value.
- **YCSB-B**: workload B of the Yahoo! Cloud Serving Benchmark, which is read-mostly (95% reads, 5% updates).
- **YCSB-A**: the write-heavy workload of the same benchmark (50% reads, 50% updates).
- **RSS**: resident set size, the physical memory the process holds.
- **kops/s**: thousand operations per second.

## Goal

Check whether replacing jemalloc 5.3 with jf2 removes the p99 latency spikes in kestrel.

## Test setup

- **Host**: bench-07 (2 x 32-core Xeon, 512 GB memory, Linux kernel 6.8).
- **System load**: the load average (average number of runnable tasks) was 0.4 before the runs. The host has 64 physical cores, so it was nearly idle.
- **Build A**: main@4f1c2aa with jemalloc 5.3.
- **Build B**: the same commit with jf2. The allocator is the only difference.
- **Workload**: YCSB-B, 64 client threads, 10 minutes per run.
- **Runs**: 5 per build, in alternating order (A, B, A, B, ...).

## Results

```
Median of 5 runs. 1 block = 200 us. Lower is better.

p99    A ███████████ 2140 us
       B ████ 870 us                    (-59%)

p99.9  A █████████████████████████████████████████████████ 9800 us
       B ████████████████ 3100 us       (-68%)
```

Only the p99 and p99.9 latencies changed. Throughput and p50 did not.

| Metric | A (jemalloc 5.3) | B (jf2) | Change, B vs A |
|---|---|---|---|
| Throughput, kops/s | 412 (405..418) | 409 (401..415) | -0.7%, ranges overlap |
| p50 latency, us | 118 (116..121) | 119 (117..121) | +0.8%, ranges overlap |
| p99 latency, us | 2140 (1890..2610) | 870 (820..940) | -59%, ranges do not overlap |
| p99.9 latency, us | 9800 (7200..14100) | 3100 (2700..3900) | -68%, ranges do not overlap |
| RSS at end of run, GB | 61.2 | 66.9 | +5.7 GB (+9.3%) |

Values are the median of 5 runs, with min..max in parentheses. The notes hold one RSS value per build, with no range.

## What the data shows

- **jf2 lowers p99 and p99.9 latency.** The slowest B run had a p99 of 940 us, and the fastest A run had 1890 us. For p99.9, the slowest B run had 3900 us, and the fastest A run had 7200 us.
- **jf2 does not change throughput or p50 latency by a measurable amount.** The medians differ by 0.7% and 0.8%, and the min..max ranges of A and B overlap for both metrics.
- **The spikes in build A occur at the same time as the jemalloc purge.** We profiled A with perf (the Linux sampling profiler). During the spike windows, 31% of the samples were in `je_arena_decay` (the jemalloc function that does the purge).
- **Hypothesis: jf2 removes the spikes by moving the purge off the request threads.** jf2 runs the purge in a background thread. The notes contain no profile of build B, so this cause is not confirmed. A perf profile of B during its slowest windows would confirm or reject it.

## Data handling

- Run 3 of build B had a 40-second stall at minute 7.
- We traced the stall to logrotate (the log-file rotation tool), which a nightly cron job started. The allocator did not cause it.
- We repeated run 3. The B results above use the repeat, not the original run.

## Not tested

- YCSB-A (write-heavy).
- More than 64 client threads.
- NUMA pinning (binding threads and memory to fixed CPU sockets).

The results above apply only to a read-mostly workload at 64 client threads without pinning.

## Open question

- Is the RSS increase of 5.7 GB (9.3%) acceptable? The capacity team must decide.

## Next steps

1. Run YCSB-A on 2026-11-21.
2. Ask the capacity team to approve the RSS increase.
3. If the capacity team approves, enable jf2 in staging, controlled by a feature flag.

---

Two things to check before you send this:

- The YCSB read/update mixes (95/5 for B, 50/50 for A) are the standard YCSB defaults, not from your notes. Confirm that your configuration uses them.
- I labeled the cause as a hypothesis, since your notes do not say how the background purge in B was observed. Remove the label if you have a profile of B.