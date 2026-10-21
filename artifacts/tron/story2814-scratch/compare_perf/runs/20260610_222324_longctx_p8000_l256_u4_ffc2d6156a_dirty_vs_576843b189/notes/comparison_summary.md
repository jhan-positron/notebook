# Story 2814 Long-Context Perf Compare

Date: 2026-06-10T22:23:25Z

Run directory: `/scratch/jhan/workspace/story2814/compare_perf/runs/20260610_222324_longctx_p8000_l256_u4_ffc2d6156a_dirty_vs_576843b189`

## Setup

- Parent baseline: `576843b189e9803f0fc48fc4483ff7a62012a461`
- Candidate: `ffc2d6156a87f42ca8f5354007247cd6b1f125e1` plus tracked dirty diff, if any.
- Tracked dirty diff: `notes/candidate_tracked_diff.patch`; source status: `notes/source_status.txt`.
- Untracked source files are recorded in source status but intentionally not applied to the candidate clone.
- Workload: `USE_HW_ATTN=1 SYSTEM_CONFIG="--instance 0,4" ./perfetto/tronperf --gen -m llama-3.1-8b-instruct-good-tp2 --prompt-length 8000 -l 256 --instance 0,4 --shared-system-prompt-length 64 -u 4`
- Smoke passed before full comparisons. `TRON_TRACE_FROM_TOKEN`: `unset`.

Validation checks from full comparison logs:

- iterations parent: OK (hw_attention_enabled=True, system_config_instance=True, fuse_instance=True, two_devices=True)
- iterations candidate: OK (hw_attention_enabled=True, system_config_instance=True, fuse_instance=True, two_devices=True)
- isolated parent: OK (hw_attention_enabled=True, system_config_instance=True, fuse_instance=True, two_devices=True)
- isolated candidate: OK (hw_attention_enabled=True, system_config_instance=True, fuse_instance=True, two_devices=True)

## `--iterations 3` Log Metrics

| Metric | Parent | Candidate | Candidate delta |
| --- | ---: | ---: | ---: |
| New-token throughput | 500.981 tok/s | 501.927 tok/s | +0.946 tok/s (+0.189%) |
| All-token throughput | 1483.990 tok/s | 1491.083 tok/s | +7.093 tok/s (+0.478%) |
| Avg prompt parse / TTFT | 15.570445 s | 15.530431 s | -0.040014 s (-0.257% better) |
| Avg generation time | 6.796473 s | 6.729968 s | -0.066505 s (-0.979% better) |
| Avg generation throughput | 37.226 tok/s | 37.594 tok/s | +0.368 tok/s (+0.988%) |
| Avg ms/token | 26.864 ms | 26.601 ms | -0.263 ms (-0.979% better) |
| Avg TTLT | 22.397291 s | 22.290186 s | -0.107105 s (-0.478% better) |
| Memory allocations | 5,947,664 | 6,033,896 | +86232 (+1.450% worse) |

### `--iterations 3` Per-Iteration Trend

| Occurrence | Parent new tok/s | Candidate new tok/s | Throughput delta | Parent TTLT s | Candidate TTLT s | TTLT delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 639.787 | 641.914 | +2.127 tok/s (+0.332%) | 51.683669 | 51.512728 | -0.170941 s (-0.331% better) |
| 2 | 39.706 | 34.283 | -5.423 tok/s (-13.658%) | 7.754139 | 7.673230 | -0.080909 s (-1.043% better) |
| 3 | 39.579 | 33.195 | -6.384 tok/s (-16.130%) | 7.754066 | 7.684600 | -0.069466 s (-0.896% better) |

- Parent new-token throughput trend: monotonic down; last vs first -600.208 (-93.814%), worse.
- Candidate new-token throughput trend: monotonic down; last vs first -608.719 (-94.829%), worse.
- Parent TTLT trend: monotonic down; last vs first -43.930 (-84.997%), better.
- Candidate TTLT trend: mixed; last vs first -43.828 (-85.082%), better.
- Candidate overall new-token throughput delta: +0.946 tok/s (+0.189%); candidate is faster in 0/2 later occurrence(s).

### `--iterations 3` Trace Slices

Trace totals are summed slice durations, not additive wall time; slices can overlap or be nested.

| Slice | Parent count / total / avg | Candidate count / total / avg | Total delta |
| --- | ---: | ---: | ---: |
| `Attn residual and RMS norm` | 114,048 / 697.145 ms / 0.006113 ms | 114,048 / 740.899 ms / 0.006496 ms | +43.754 ms (+6.276% worse) |
| `Post attn prepare` | 57,024 / 49.181 ms / 0.000862 ms | 57,024 / 50.801 ms / 0.000891 ms | +1.620 ms (+3.294% worse) |
| `gof_populate` | no rows | 12,032 / 167.628 ms / 0.013932 ms | candidate-only |
| `gof_rodeo` | no rows | 10,944 / 348.335 ms / 0.031829 ms | candidate-only |
| `launch_hw_attn` | 57,022 / 26.077 ms / 0.000457 ms | 57,024 / 25.445 ms / 0.000446 ms | -0.632 ms (-2.424% better) |
| `prep_hw_attn` | 57,022 / 15.517 ms / 0.000272 ms | 57,024 / 16.119 ms / 0.000283 ms | +0.602 ms (+3.880% worse) |
| `xfer_gof` | 12,032 / 180.691 ms / 0.015018 ms | 12,032 / 175.858 ms / 0.014616 ms | -4.833 ms (-2.675% better) |

## `--isolated-iterations 3` Log Metrics

| Metric | Parent | Candidate | Candidate delta |
| --- | ---: | ---: | ---: |
| New-token throughput | 638.235 tok/s | 639.881 tok/s | +1.646 tok/s (+0.258%) |
| All-token throughput | 641.939 tok/s | 643.595 tok/s | +1.655 tok/s (+0.258%) |
| Avg prompt parse / TTFT | 45.085020 s | 44.949028 s | -0.135992 s (-0.302% better) |
| Avg generation time | 6.689632 s | 6.693538 s | +0.003906 s (+0.058% worse) |
| Avg generation throughput | 37.820 tok/s | 37.797 tok/s | -0.022 tok/s (-0.059%) |
| Avg ms/token | 26.441 ms | 26.457 ms | +0.015 ms (+0.058% worse) |
| Avg TTLT | 51.811415 s | 51.678907 s | -0.132509 s (-0.256% better) |
| Memory allocations | 11,921,596 | 12,000,624 | +79028 (+0.663% worse) |

### `--isolated-iterations 3` Per-Isolated-Run Trend

Each isolated run logs as `[Iteration 1/1]`; the table uses occurrence order 1-3.

| Occurrence | Parent new tok/s | Candidate new tok/s | Throughput delta | Parent TTLT s | Candidate TTLT s | TTLT delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 643.671 | 647.008 | +3.337 tok/s (+0.518%) | 51.371511 | 51.106878 | -0.264633 s (-0.515% better) |
| 2 | 634.596 | 635.861 | +1.265 tok/s (+0.199%) | 52.107079 | 52.003345 | -0.103733 s (-0.199% better) |
| 3 | 636.446 | 636.803 | +0.357 tok/s (+0.056%) | 51.955657 | 51.926497 | -0.029160 s (-0.056% better) |

- Parent new-token throughput trend: mixed; last vs first -7.225 (-1.122%), worse.
- Candidate new-token throughput trend: mixed; last vs first -10.205 (-1.577%), worse.
- Parent TTLT trend: mixed; last vs first +0.584 (+1.137%), worse.
- Candidate TTLT trend: mixed; last vs first +0.820 (+1.604%), worse.
- Candidate overall new-token throughput delta: +1.646 tok/s (+0.258%); candidate is faster in 2/2 later occurrence(s).

### `--isolated-iterations 3` Trace Slices

Trace totals are summed slice durations, not additive wall time; slices can overlap or be nested.

| Slice | Parent count / total / avg | Candidate count / total / avg | Total delta |
| --- | ---: | ---: | ---: |
| `Attn residual and RMS norm` | 386,774 / 1880.108 ms / 0.004861 ms | 386,148 / 1938.130 ms / 0.005019 ms | +58.022 ms (+3.086% worse) |
| `Post attn prepare` | 16,320 / 12.921 ms / 0.000792 ms | 16,320 / 14.408 ms / 0.000883 ms | +1.487 ms (+11.508% worse) |
| `gof_populate` | no rows | 524,928 / 4561.419 ms / 0.008690 ms | candidate-only |
| `gof_rodeo` | no rows | 524,928 / 10956.727 ms / 0.020873 ms | candidate-only |
| `launch_hw_attn` | 16,320 / 7.017 ms / 0.000430 ms | 16,320 / 7.406 ms / 0.000454 ms | +0.389 ms (+5.544% worse) |
| `prep_hw_attn` | 16,320 / 4.384 ms / 0.000269 ms | 16,320 / 4.498 ms / 0.000276 ms | +0.114 ms (+2.600% worse) |
| `xfer_gof` | 528,000 / 5868.463 ms / 0.011115 ms | 528,000 / 5853.512 ms / 0.011086 ms | -14.951 ms (-0.255% better) |

## Artifacts

- isolated candidate log: `captures/isolated3_candidate/candidate_ffc2d6156a_dirty_p8000_l256_s64_u4_isolated3_instance_0_4.log`
- isolated parent log: `captures/isolated3_parent/base_576843b189_p8000_l256_s64_u4_isolated3_instance_0_4.log`
- iterations candidate log: `captures/iterations3_candidate/candidate_ffc2d6156a_dirty_p8000_l256_s64_u4_iter3_instance_0_4.log`
- iterations parent log: `captures/iterations3_parent/base_576843b189_p8000_l256_s64_u4_iter3_instance_0_4.log`
- Trace: `captures/isolated3_candidate/candidate_ffc2d6156a_dirty_p8000_l256_s64_u4_isolated3_instance_0_4.trace`
- Trace: `captures/isolated3_parent/base_576843b189_p8000_l256_s64_u4_isolated3_instance_0_4.trace`
- Trace: `captures/iterations3_candidate/candidate_ffc2d6156a_dirty_p8000_l256_s64_u4_iter3_instance_0_4.trace`
- Trace: `captures/iterations3_parent/base_576843b189_p8000_l256_s64_u4_iter3_instance_0_4.trace`
- Trace: `captures/smoke_candidate/candidate_ffc2d6156a_smoke_p8000_l256_s64_u4_instance_0_4.trace`
- Per-iteration metrics CSV: `notes/per_iteration_log_metrics.csv`
- Overall metrics CSV: `notes/overall_log_metrics.csv`
- Trace slice CSVs: `queries/trace_slices_iterations3_parent.csv`, `queries/trace_slices_iterations3_candidate.csv`, `queries/trace_slices_isolated3_parent.csv`, `queries/trace_slices_isolated3_candidate.csv`
