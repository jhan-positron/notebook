# Story 2814 Perf Compare: corrected TP2 instance 0,4

Date: 2026-06-10 UTC

Run directory: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260610_tp2_instance_0_4_ffc2d615_dirty_vs_parent`

## Setup

- Parent baseline: `576843b189e9803f0fc48fc4483ff7a62012a461`
- Candidate: `ffc2d6156a87f42ca8f5354007247cd6b1f125e1` plus tracked dirty diff
- Tracked dirty diff: `.gitignore` only; saved at `notes/candidate_tracked_diff.patch`
- Untracked workspace files were ignored.
- Corrected workload: `USE_HW_ATTN=1 SYSTEM_CONFIG="--instance 0,4" ./perfetto/tronperf --gen -m llama-3.1-8b-instruct-good-tp2 --prompt-length 256 -l 256 --instance 0,4 --shared-system-prompt-length 64 -u 8`
- Both successful captures show `FUSE mount point scoped for instance 0,4`, `INIT: environment system config: --instance 0,4`, `Found 2 Positron devices`, `HW attention: ENABLED`, and `hw_attn configured: max_layers=32`.

Note: one parent attempt in this run is invalid and excluded. It hit Perfetto startup race / zero-byte trace and also exposed the inherited `SYSTEM_CONFIG=--instance 0,2`. It was preserved as `captures/base_parent/invalid_attempt_env_system_config_0_2.log`.

## Log Metrics

All request averages are across the 8 requests in the run.

| Metric | Parent | Candidate | Delta | Percent |
| --- | ---: | ---: | ---: | ---: |
| New-token throughput | 1111.871 tok/s | 1110.266 tok/s | -1.605 tok/s | -0.144% |
| All-token throughput | 1231.841 tok/s | 1230.063 tok/s | -1.778 tok/s | -0.144% |
| Avg prompt parse / TTFT | 1.225485 s | 1.224447 s | -1.038 ms | -0.085% |
| Avg generation time | 2.484658 s | 2.490673 s | +6.014 ms | +0.242% |
| Avg generation throughput | 101.825 tok/s | 101.579 tok/s | -0.246 tok/s | -0.242% |
| Avg ms/token | 9.821 ms | 9.845 ms | +0.024 ms | +0.244% |
| Avg TTLT | 3.725193 s | 3.730657 s | +5.464 ms | +0.147% |
| Memory allocations | 1,571,198 | 1,578,435 | +7,237 | +0.461% |

## Trace Slices

Trace totals are summed slice durations, not additive wall time; some slices can overlap or be nested. Parent has no `gof_populate` or `gof_rodeo` rows, while candidate does, so those candidate-only rows demonstrate the updated GOF path/instrumentation was exercised but are not directly comparable by name.

| Slice | Parent count / total / avg | Candidate count / total / avg | Total delta |
| --- | ---: | ---: | ---: |
| `Attn residual and RMS norm` | 65,280 / 450.210 ms / 0.006897 ms | 65,236 / 439.700 ms / 0.006740 ms | -10.510 ms (-2.334%) |
| `Post attn prepare` | 16,320 / 26.270 ms / 0.001610 ms | 16,309 / 26.762 ms / 0.001641 ms | +0.492 ms (+1.873%) |
| `launch_hw_attn` | 16,320 / 7.024 ms / 0.000430 ms | 16,308 / 8.776 ms / 0.000538 ms | +1.752 ms (+24.943%) |
| `prep_hw_attn` | 16,320 / 4.199 ms / 0.000257 ms | 16,307 / 5.319 ms / 0.000326 ms | +1.120 ms (+26.673%) |
| `xfer_gof` | 16,128 / 179.835 ms / 0.011150 ms | 16,128 / 177.839 ms / 0.011027 ms | -1.996 ms (-1.110%) |
| `gof_populate` | no rows | 16,128 / 175.765 ms / 0.010898 ms | candidate-only |
| `gof_rodeo` | no rows | 16,128 / 372.973 ms / 0.023126 ms | candidate-only |

## Summary

This corrected run is apple-to-apple for the TP2 model placement: both parent and candidate used `--instance 0,4` through both the forwarded argument and `SYSTEM_CONFIG`, both ran on 2 Positron devices, and both had HW attention enabled.

For this single capture, candidate is slightly slower at the top level: -0.144% new-token throughput and +0.147% average TTLT. The directly comparable `xfer_gof` slice improved slightly at -1.110% total time. `prep_hw_attn` and `launch_hw_attn` increased in percentage terms, but by small absolute totals (+1.120 ms and +1.752 ms over the full trace).

I do not see a large perf regression in this corrected one-run comparison. The deltas are small enough that repeated captures would be useful if we need a firmer statistical guardrail.

## Artifacts

- Parent log: `captures/base_parent/base_576843b18_hwattn_p256_g256_s64_u8_instance_0_4.log`
- Parent trace: `captures/base_parent/base_576843b18_hwattn_p256_g256_s64_u8_instance_0_4.trace`
- Candidate log: `captures/candidate/candidate_ffc2d615_dirty_hwattn_p256_g256_s64_u8_instance_0_4.log`
- Candidate trace: `captures/candidate/candidate_ffc2d615_dirty_hwattn_p256_g256_s64_u8_instance_0_4.trace`
- Parent trace slices CSV: `queries/trace_slices_parent.csv`
- Candidate trace slices CSV: `queries/trace_slices_candidate.csv`
- Invalid excluded attempt: `captures/base_parent/invalid_attempt_env_system_config_0_2.log`
