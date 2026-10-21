# Story 2814 Perf Compare: f5ea3148 dirty vs parent

Date: 2026-06-09 UTC

Run directory: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent`

## Setup

- Parent baseline: `576843b189e9803f0fc48fc4483ff7a62012a461`
- Candidate: `f5ea3148ee475c4e0975a685dcf30001d6b72f5e` plus tracked dirty diff
- Dirty patch saved at: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/notes/candidate_tracked_diff.patch`
- Untracked workspace files were ignored.
- Workload: `USE_HW_ATTN=1 ./perfetto/tronperf --gen -m llama-3.1-8b-instruct-good-tp2 --prompt-length 256 -l 256 --instance 0,2 --shared-system-prompt-length 64 -u 8`
- Both successful captures show `HW attention: ENABLED` and `hw_attn configured: max_layers=32`.

Note: the first candidate attempt aborted before the workload with `fusermount3: could not determine username` while creating the FUSE mount directory. A second candidate run with the same command succeeded after the mount directory existed; the final candidate log/trace below are from the successful run.

## Log Metrics

All request averages are across the 8 requests in the run.

| Metric | Parent | Candidate | Delta | Percent |
| --- | ---: | ---: | ---: | ---: |
| New-token throughput | 1160.834 tok/s | 1158.218 tok/s | -2.616 tok/s | -0.225% |
| All-token throughput | 1286.088 tok/s | 1283.189 tok/s | -2.899 tok/s | -0.225% |
| Avg prompt parse / TTFT | 1.099184 s | 1.100411 s | +1.227 ms | +0.112% |
| Avg generation time | 2.452043 s | 2.458178 s | +6.135 ms | +0.250% |
| Avg generation throughput | 103.179 tok/s | 102.922 tok/s | -0.257 tok/s | -0.249% |
| Avg ms/token | 9.692 ms | 9.716 ms | +0.024 ms | +0.248% |
| Avg TTLT | 3.567657 s | 3.575787 s | +8.130 ms | +0.228% |
| Memory allocations | 2,051,031 | 2,058,214 | +7,183 | +0.350% |

## Trace Slices

Trace totals are summed slice durations, not additive wall time; some slices can overlap or be nested. Parent has no `gof_populate` or `gof_rodeo` rows, while candidate does, so those rows show that the updated GOF path/instrumentation was exercised but cannot be directly delta-compared against parent by name.

| Slice | Parent count / total / avg | Candidate count / total / avg | Total delta |
| --- | ---: | ---: | ---: |
| `Attn residual and RMS norm` | 65,280 / 494.778 ms / 0.007579 ms | 65,216 / 509.305 ms / 0.007810 ms | +14.527 ms (+2.936%) |
| `Post attn prepare` | 16,320 / 29.531 ms / 0.001810 ms | 16,304 / 26.574 ms / 0.001630 ms | -2.957 ms (-10.013%) |
| `launch_hw_attn` | 16,320 / 8.249 ms / 0.000505 ms | 16,303 / 7.106 ms / 0.000436 ms | -1.143 ms (-13.856%) |
| `prep_hw_attn` | 16,320 / 5.217 ms / 0.000320 ms | 16,302 / 4.196 ms / 0.000257 ms | -1.021 ms (-19.571%) |
| `xfer_gof` | 16,128 / 208.486 ms / 0.012927 ms | 16,128 / 210.896 ms / 0.013076 ms | +2.410 ms (+1.156%) |
| `gof_populate` | no rows | 16,128 / 168.150 ms / 0.010426 ms | candidate-only |
| `gof_rodeo` | no rows | 16,128 / 401.730 ms / 0.024909 ms | candidate-only |

## Summary

The successful rerun is now apple-to-apple for HW attention: both parent and candidate enabled HW attention and both emitted GOF/HW-attention trace slices.

For this single capture, candidate is slightly slower at the top level: about -0.225% new-token throughput and +0.228% average TTLT. The directly comparable GOF transfer slice, `xfer_gof`, increased by +1.156% total slice time, while `prep_hw_attn` and `launch_hw_attn` decreased. I do not see a large perf regression in this one-run comparison, but the observed deltas are small enough that repeated runs would be the better guard if Wade wants a firmer statistical answer.

## Artifacts

- Parent log: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/captures/base_parent/base_576843b18_hwattn_p256_g256_s64_u8.log`
- Parent trace: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/captures/base_parent/base_576843b18_hwattn_p256_g256_s64_u8.trace`
- Candidate log: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/captures/candidate/candidate_f5ea3148_dirty_hwattn_p256_g256_s64_u8.log`
- Candidate trace: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/captures/candidate/candidate_f5ea3148_dirty_hwattn_p256_g256_s64_u8.trace`
