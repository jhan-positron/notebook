# Story 2814 Perf Comparison: Parent vs Tracing Commit

Run directory:

`/scratch/jhan/workspace/story2814/compare_perf/runs/20260608_parent_vs_tracing`

Compared:

- Base parent: `576843b18`
- Candidate: `1c6d3fc8e`
- Workload: `USE_HW_ATTN=1`, `p256/g256/s64/u8`, `--instance 0,2`
- Both logs show `HW attention: ENABLED` and `hw_attn configured: max_layers=32`

## Corrected Result

| Metric | Parent `576843b18` | Candidate `1c6d3fc8e` | Delta |
|---|---:|---:|---:|
| new tok/s | `1163.784` | `1156.240` | `-0.648%` |
| all tok/s | `1289.356` | `1280.998` | `-0.648%` |
| gen ms/tok | `9.658` | `9.746` | `+0.911%` |
| TTFT | `1.098851s` | `1.098959s` | `+0.010%` |
| TTLT | `3.558652s` | `3.581303s` | `+0.637%` |

## Trace Evidence

- Parent has existing HW/GOF slices, e.g. `xfer_gof`: `16128` slices, `209.060 ms` total.
- Candidate has `xfer_gof`: `16128` slices, `208.738 ms` total.
- Candidate additionally has the new trace events from the commit, e.g. `gof_populate` and `gof_rodeo`, which parent cannot have because those are the instrumentation being added.

## Summary

The corrected parent-vs-candidate comparison is apples-to-apples: both runs used HW attention and the same workload. The tracing commit does not show a material perf regression in this single A/B run. The observed candidate slowdown is about `0.65%` throughput, with essentially unchanged TTFT.

Artifacts:

- Parent: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260608_parent_vs_tracing/captures/base_parent`
- Candidate: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260608_parent_vs_tracing/captures/candidate`
