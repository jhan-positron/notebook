# wedperf-20260916 summary (the nightly CI perf models; base = main before PR #3879, target = PR #4424 head)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gptoss-tp4-8u | cpu | ingested-gpt-oss-120b-tp4 | 4 | 8 | base | 2 | 80.01 | 2.31 | 2.663 | 0.033 | 0 | eb2de0265a |
| gptoss-tp4-8u | cpu | ingested-gpt-oss-120b-tp4 | 4 | 8 | mid | 2 | 80.69 | 4.14 | 2.826 | 0.011 | 0 | c7844ca2ce |
| gptoss-tp4-8u | cpu | ingested-gpt-oss-120b-tp4 | 4 | 8 | target | 2 | 80.16 | 0.42 | 2.854 | 0.032 | 0 | ff680c8020 |
| g2-9b-tp2-8u | cpu | gemma-2-9b-it-fast-tp2 | 2 | 8 | base | 2 | 65.08 | 0.52 | 4.945 | 0.007 | 0 | eb2de0265a |
| g2-9b-tp2-8u | cpu | gemma-2-9b-it-fast-tp2 | 2 | 8 | mid | 2 | 65.54 | 0.07 | 4.952 | 0.007 | 0 | c7844ca2ce |
| g2-9b-tp2-8u | cpu | gemma-2-9b-it-fast-tp2 | 2 | 8 | target | 2 | 65.42 | 0.30 | 5.009 | 0.089 | 0 | ff680c8020 |
| q3-4b-tp2-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 2 | 71.25 | 0.27 | 3.943 | 0.004 | 0 | eb2de0265a |
| q3-4b-tp2-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | mid | 2 | 79.94 | 0.23 | 3.157 | 0.002 | 0 | c7844ca2ce |
| q3-4b-tp2-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | target | 2 | 83.52 | 0.48 | 3.091 | 0.003 | 0 | ff680c8020 |
| l8b-tp2-8u | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | base | 2 | 110.29 | 0.21 | 3.620 | 0.006 | 0 | eb2de0265a |
| l8b-tp2-8u | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | mid | 2 | 113.59 | 0.20 | 3.406 | 0.000 | 0 | c7844ca2ce |
| l8b-tp2-8u | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | target | 2 | 112.36 | 0.85 | 3.434 | 0.004 | 0 | ff680c8020 |
| gptoss-tp4-8u | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | base | 6 | 86.88 | 2.53 | 2.689 | 0.025 | 0 | eb2de0265a |
| gptoss-tp4-8u | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | mid | 6 | 90.24 | 2.77 | 2.835 | 0.042 | 0 | c7844ca2ce |
| gptoss-tp4-8u | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | target | 6 | 85.73 | 2.98 | 2.865 | 0.067 | 0 | ff680c8020 |
| q3-4b-tp4-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | base | 6 | 132.30 | 8.17 | 2.253 | 0.017 | 0 | eb2de0265a |
| q3-4b-tp4-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | mid | 6 | 129.65 | 9.02 | 2.288 | 0.016 | 0 | c7844ca2ce |
| q3-4b-tp4-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | target | 6 | 117.12 | 2.54 | 2.231 | 0.024 | 0 | ff680c8020 |
| q3-4b-tp2-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 6 | 124.80 | 0.82 | 3.214 | 0.023 | 0 | eb2de0265a |
| q3-4b-tp2-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | mid | 6 | 125.41 | 0.85 | 3.195 | 0.011 | 0 | c7844ca2ce |
| q3-4b-tp2-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | target | 6 | 122.61 | 0.40 | 3.161 | 0.015 | 0 | ff680c8020 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| gptoss-tp4-8u | cpu | mid vs base | +0.9 | +6.1 | +162 | +0.68 (1.83, 2, +0.5) | +162 (44, 2, +5.2) |
| gptoss-tp4-8u | cpu | target vs mid | -0.7 | +1.0 | +28 | -0.54 (4.56, 2, -0.2) | +28 (21, 2, +1.9) |
| gptoss-tp4-8u | cpu | target vs base | +0.2 | +7.1 | +190 | +0.15 (2.73, 2, +0.1) | +190 (65, 2, +4.2) |
| g2-9b-tp2-8u | cpu | mid vs base | +0.7 | +0.1 | +7 | +0.47 (0.59, 2, +1.1) | +7 (0, 2, +311.0) |
| g2-9b-tp2-8u | cpu | target vs mid | -0.2 | +1.2 | +57 | -0.12 (0.23, 2, -0.8) | +57 (96, 2, +0.8) |
| g2-9b-tp2-8u | cpu | target vs base | +0.5 | +1.3 | +64 | +0.34 (0.82, 2, +0.6) | +64 (96, 2, +0.9) |
| q3-4b-tp2-8u | cpu | mid vs base | +12.2 | -19.9 | -786 | +8.70 (0.04, 2, +334.5) | -786 (2, 2, -705.5) |
| q3-4b-tp2-8u | cpu | target vs mid | +4.5 | -2.1 | -65 | +3.58 (0.71, 2, +7.1) | -65 (6, 2, -16.5) |
| q3-4b-tp2-8u | cpu | target vs base | +17.2 | -21.6 | -852 | +12.28 (0.75, 2, +23.1) | -852 (7, 2, -168.6) |
| l8b-tp2-8u | cpu | mid vs base | +3.0 | -5.9 | -214 | +3.29 (0.42, 2, +11.2) | -214 (7, 2, -44.5) |
| l8b-tp2-8u | cpu | target vs mid | -1.1 | +0.8 | +29 | -1.23 (1.05, 2, -1.7) | +29 (3, 2, +12.1) |
| l8b-tp2-8u | cpu | target vs base | +1.9 | -5.1 | -186 | +2.06 (0.63, 2, +4.6) | -186 (10, 2, -25.8) |
| gptoss-tp4-8u | fpga | mid vs base | +3.9 | +5.4 | +146 | +3.36 (4.42, 6, +1.9) | +146 (57, 6, +6.3) |
| gptoss-tp4-8u | fpga | target vs mid | -5.0 | +1.1 | +30 | -4.51 (4.71, 6, -2.3) | +30 (67, 6, +1.1) |
| gptoss-tp4-8u | fpga | target vs base | -1.3 | +6.5 | +176 | -1.15 (2.08, 6, -1.4) | +176 (58, 6, +7.4) |
| q3-4b-tp4-8u | fpga | mid vs base | -2.0 | +1.6 | +35 | -2.65 (8.74, 6, -0.7) | +35 (30, 6, +2.8) |
| q3-4b-tp4-8u | fpga | target vs mid | -9.7 | -2.5 | -58 | -12.52 (10.58, 6, -2.9) | -58 (23, 6, -6.2) |
| q3-4b-tp4-8u | fpga | target vs base | -11.5 | -1.0 | -23 | -15.18 (8.50, 6, -4.4) | -23 (26, 6, -2.1) |
| q3-4b-tp2-8u | fpga | mid vs base | +0.5 | -0.6 | -19 | +0.61 (1.20, 6, +1.3) | -19 (32, 6, -1.5) |
| q3-4b-tp2-8u | fpga | target vs mid | -2.2 | -1.1 | -34 | -2.81 (1.06, 6, -6.5) | -34 (14, 6, -5.9) |
| q3-4b-tp2-8u | fpga | target vs base | -1.8 | -1.7 | -53 | -2.19 (0.86, 6, -6.2) | -53 (27, 6, -4.8) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

