# wedperf-20260916 summary (the nightly CI perf models; base = main before PR #3879, target = PR #4424 head)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| l3b-tp2-32u | cpu | llama-3.2-3b-instruct-fast-tp2 | 2 | 32 | base | 3 | 40.67 | 0.09 | 6.847 | 0.058 | 0 | eb2de0265a |
| l3b-tp2-32u | cpu | llama-3.2-3b-instruct-fast-tp2 | 2 | 32 | target | 3 | 42.14 | 0.17 | 6.885 | 0.002 | 0 | ff680c8020 |
| l8b-tp2-8u | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | base | 3 | 110.13 | 0.14 | 3.582 | 0.038 | 0 | eb2de0265a |
| l8b-tp2-8u | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | target | 3 | 112.32 | 0.28 | 3.436 | 0.003 | 0 | ff680c8020 |
| l70b-tp2-8u | cpu | llama-3.3-70b-instruct-good-tp2 | 2 | 8 | base | 3 | 15.39 | 0.01 | 38.323 | 0.002 | 0 | eb2de0265a |
| l70b-tp2-8u | cpu | llama-3.3-70b-instruct-good-tp2 | 2 | 8 | target | 3 | 15.38 | 0.01 | 38.327 | 0.003 | 0 | ff680c8020 |
| l70b-tp2-4u | cpu | llama-3.3-70b-instruct-good-tp2 | 2 | 4 | base | 3 | 16.40 | 0.00 | 19.192 | 0.001 | 0 | eb2de0265a |
| l70b-tp2-4u | cpu | llama-3.3-70b-instruct-good-tp2 | 2 | 4 | target | 3 | 16.40 | 0.00 | 19.191 | 0.000 | 0 | ff680c8020 |
| l70b-tp4-4u | cpu | llama-3.3-70b-instruct-good-tp4 | 4 | 4 | base | 3 | 29.60 | 0.14 | 9.831 | 0.006 | 0 | eb2de0265a |
| l70b-tp4-4u | cpu | llama-3.3-70b-instruct-good-tp4 | 4 | 4 | target | 3 | 29.41 | 0.12 | 9.827 | 0.008 | 0 | ff680c8020 |
| mixtral-tp2-8u | cpu | mixtral-8x7b-instruct-v0.1-tp2 | 2 | 8 | base | 3 | 34.60 | 0.13 | 6.575 | 0.003 | 0 | eb2de0265a |
| mixtral-tp2-8u | cpu | mixtral-8x7b-instruct-v0.1-tp2 | 2 | 8 | target | 3 | 34.65 | 0.16 | 6.574 | 0.002 | 0 | ff680c8020 |
| q25-32b-tp2-8u | cpu | qwen-2.5-32b-it-fast-tp2 | 2 | 8 | base | 3 | 31.29 | 0.01 | 18.258 | 0.003 | 0 | eb2de0265a |
| q25-32b-tp2-8u | cpu | qwen-2.5-32b-it-fast-tp2 | 2 | 8 | target | 3 | 31.30 | 0.03 | 18.268 | 0.001 | 0 | ff680c8020 |
| q3-4b-tp2-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 71.59 | 0.32 | 3.945 | 0.003 | 0 | eb2de0265a |
| q3-4b-tp2-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | target | 3 | 83.16 | 0.28 | 3.087 | 0.004 | 0 | ff680c8020 |
| q3-4b-tp4-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | base | 3 | 98.35 | 1.03 | 2.464 | 0.005 | 0 | eb2de0265a |
| q3-4b-tp4-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | target | 3 | 105.83 | 2.39 | 2.121 | 0.007 | 0 | ff680c8020 |
| g2-9b-tp2-8u | cpu | gemma-2-9b-it-fast-tp2 | 2 | 8 | base | 3 | 64.76 | 0.07 | 4.992 | 0.073 | 0 | eb2de0265a |
| g2-9b-tp2-8u | cpu | gemma-2-9b-it-fast-tp2 | 2 | 8 | target | 3 | 65.50 | 0.05 | 4.994 | 0.071 | 0 | ff680c8020 |
| gptoss-tp4-8u | cpu | ingested-gpt-oss-120b-tp4 | 4 | 8 | base | 3 | 80.07 | 3.36 | 2.650 | 0.007 | 0 | eb2de0265a |
| gptoss-tp4-8u | cpu | ingested-gpt-oss-120b-tp4 | 4 | 8 | target | 3 | 79.68 | 1.74 | 2.846 | 0.031 | 0 | ff680c8020 |
| g4-31b-tp2-8u | cpu | ingested-gemma-4-31b-it-tp2 | 2 | 8 | base | 3 | 15.37 | 0.01 | 23.631 | 0.003 | 0 | eb2de0265a |
| g4-31b-tp2-8u | cpu | ingested-gemma-4-31b-it-tp2 | 2 | 8 | target | 3 | 15.38 | 0.01 | 23.656 | 0.025 | 0 | ff680c8020 |
| q3-4b-tp2-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 2 | 125.62 | 0.35 | 3.191 | 0.020 | 0 | eb2de0265a |
| q3-4b-tp2-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | target | 2 | 122.25 | 0.12 | 3.150 | 0.013 | 0 | ff680c8020 |
| q3-4b-tp4-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | base | 2 | 123.67 | 11.97 | 2.273 | 0.024 | 0 | eb2de0265a |
| q3-4b-tp4-8u | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | target | 2 | 119.80 | 0.76 | 2.252 | 0.048 | 0 | ff680c8020 |
| gptoss-tp4-8u | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | base | 2 | 89.04 | 1.04 | 2.651 | 0.008 | 0 | eb2de0265a |
| gptoss-tp4-8u | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | target | 2 | 86.45 | 0.70 | 2.856 | 0.067 | 0 | ff680c8020 |
| g4-31b-tp2-8u | fpga | ingested-gemma-4-31b-it-tp2 | 2 | 8 | base | 2 | 15.36 | 0.00 | 23.641 | 0.031 | 0 | eb2de0265a |
| g4-31b-tp2-8u | fpga | ingested-gemma-4-31b-it-tp2 | 2 | 8 | target | 2 | 15.41 | 0.01 | 23.679 | 0.059 | 0 | ff680c8020 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| l3b-tp2-32u | cpu | target vs base | +3.6 | +0.6 | +38 | +1.47 (0.25, 3, +10.2) | +38 (60, 3, +1.1) |
| l8b-tp2-8u | cpu | target vs base | +2.0 | -4.1 | -146 | +2.19 (0.20, 3, +19.0) | -146 (39, 3, -6.5) |
| l70b-tp2-8u | cpu | target vs base | -0.1 | +0.0 | +4 | -0.01 (0.01, 3, -1.8) | +4 (5, 3, +1.5) |
| l70b-tp2-4u | cpu | target vs base | -0.0 | -0.0 | -1 | -0.00 (0.01, 3, -0.9) | -1 (1, 3, -3.1) |
| l70b-tp4-4u | cpu | target vs base | -0.6 | -0.0 | -4 | -0.19 (0.24, 3, -1.3) | -4 (7, 3, -1.0) |
| mixtral-tp2-8u | cpu | target vs base | +0.1 | -0.0 | -0 | +0.05 (0.27, 3, +0.3) | -0 (2, 3, -0.3) |
| q25-32b-tp2-8u | cpu | target vs base | +0.0 | +0.1 | +10 | +0.01 (0.01, 3, +1.4) | +10 (2, 3, +7.8) |
| q3-4b-tp2-8u | cpu | target vs base | +16.2 | -21.7 | -858 | +11.57 (0.43, 3, +46.8) | -858 (5, 3, -273.7) |
| q3-4b-tp4-8u | cpu | target vs base | +7.6 | -13.9 | -342 | +7.48 (3.42, 3, +3.8) | -342 (9, 3, -64.6) |
| g2-9b-tp2-8u | cpu | target vs base | +1.1 | +0.0 | +2 | +0.74 (0.03, 3, +43.0) | +2 (6, 3, +0.7) |
| gptoss-tp4-8u | cpu | target vs base | -0.5 | +7.4 | +196 | -0.39 (1.84, 3, -0.4) | +196 (36, 3, +9.4) |
| g4-31b-tp2-8u | cpu | target vs base | +0.0 | +0.1 | +25 | +0.00 (0.03, 3, +0.2) | +25 (25, 3, +1.7) |
| q3-4b-tp2-8u | fpga | target vs base | -2.7 | -1.3 | -41 | -3.37 (0.47, 2, -10.2) | -41 (7, 2, -8.3) |
| q3-4b-tp4-8u | fpga | target vs base | -3.1 | -0.9 | -21 | -3.87 (12.73, 2, -0.4) | -21 (72, 2, -0.4) |
| gptoss-tp4-8u | fpga | target vs base | -2.9 | +7.7 | +205 | -2.59 (0.34, 2, -10.9) | +205 (76, 2, +3.8) |
| g4-31b-tp2-8u | fpga | target vs base | +0.3 | +0.2 | +38 | +0.05 (0.01, 2, +7.1) | +38 (89, 2, +0.6) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

