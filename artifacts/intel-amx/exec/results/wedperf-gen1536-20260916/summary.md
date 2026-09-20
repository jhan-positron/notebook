# wedperf-20260916 summary (the nightly CI perf models; base = main before PR #3879, target = PR #4424 head)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| l3b-tp2-32u | cpu | llama-3.2-3b-instruct-fast-tp2 | 2 | 32 | base | 2 | 28.57 | 0.08 | 6.797 | 0.003 | 0 | eb2de0265a |
| l3b-tp2-32u | cpu | llama-3.2-3b-instruct-fast-tp2 | 2 | 32 | target | 2 | 29.72 | 0.10 | 6.855 | 0.032 | 0 | ff680c8020 |
| l8b-tp2-8u | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | base | 2 | 83.30 | 0.20 | 3.573 | 0.066 | 0 | eb2de0265a |
| l8b-tp2-8u | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | target | 2 | 97.49 | 0.55 | 3.434 | 0.003 | 0 | ff680c8020 |
| l70b-tp2-8u | cpu | llama-3.3-70b-instruct-good-tp2 | 2 | 8 | base | 2 | 15.35 | 0.00 | 38.327 | 0.002 | 0 | eb2de0265a |
| l70b-tp2-8u | cpu | llama-3.3-70b-instruct-good-tp2 | 2 | 8 | target | 2 | 15.35 | 0.00 | 38.326 | 0.002 | 0 | ff680c8020 |
| l70b-tp2-4u | cpu | llama-3.3-70b-instruct-good-tp2 | 2 | 4 | base | 2 | 16.38 | 0.01 | 19.193 | 0.000 | 0 | eb2de0265a |
| l70b-tp2-4u | cpu | llama-3.3-70b-instruct-good-tp2 | 2 | 4 | target | 2 | 16.38 | 0.00 | 19.191 | 0.002 | 0 | ff680c8020 |
| l70b-tp4-4u | cpu | llama-3.3-70b-instruct-good-tp4 | 4 | 4 | base | 2 | 29.33 | 0.06 | 9.820 | 0.002 | 0 | eb2de0265a |
| l70b-tp4-4u | cpu | llama-3.3-70b-instruct-good-tp4 | 4 | 4 | target | 2 | 29.27 | 0.16 | 9.822 | 0.009 | 0 | ff680c8020 |
| mixtral-tp2-8u | cpu | mixtral-8x7b-instruct-v0.1-tp2 | 2 | 8 | base | 2 | 34.42 | 0.07 | 6.577 | 0.008 | 0 | eb2de0265a |
| mixtral-tp2-8u | cpu | mixtral-8x7b-instruct-v0.1-tp2 | 2 | 8 | target | 2 | 34.33 | 0.01 | 6.577 | 0.008 | 0 | ff680c8020 |
| q25-32b-tp2-8u | cpu | qwen-2.5-32b-it-fast-tp2 | 2 | 8 | base | 2 | 30.74 | 0.02 | 18.258 | 0.001 | 0 | eb2de0265a |
| q25-32b-tp2-8u | cpu | qwen-2.5-32b-it-fast-tp2 | 2 | 8 | target | 2 | 31.09 | 0.01 | 18.270 | 0.003 | 0 | ff680c8020 |
| q3-4b-tp2-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 2 | 52.70 | 0.03 | 3.944 | 0.005 | 0 | eb2de0265a |
| q3-4b-tp2-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | target | 2 | 64.19 | 0.23 | 3.084 | 0.005 | 0 | ff680c8020 |
| q3-4b-tp4-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | base | 2 | 80.94 | 0.42 | 2.463 | 0.008 | 0 | eb2de0265a |
| q3-4b-tp4-8u | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | target | 2 | 88.09 | 2.94 | 2.127 | 0.015 | 0 | ff680c8020 |
| g2-9b-tp2-8u | cpu | gemma-2-9b-it-fast-tp2 | 2 | 8 | base | 2 | 45.16 | 0.08 | 4.947 | 0.000 | 0 | eb2de0265a |
| g2-9b-tp2-8u | cpu | gemma-2-9b-it-fast-tp2 | 2 | 8 | target | 2 | 45.20 | 0.09 | 4.946 | 0.004 | 0 | ff680c8020 |
| gptoss-tp4-8u | cpu | ingested-gpt-oss-120b-tp4 | 4 | 8 | base | 2 | 73.87 | 0.14 | 2.647 | 0.013 | 0 | eb2de0265a |
| gptoss-tp4-8u | cpu | ingested-gpt-oss-120b-tp4 | 4 | 8 | target | 2 | 73.68 | 0.81 | 2.853 | 0.036 | 0 | ff680c8020 |
| g4-31b-tp2-8u | cpu | ingested-gemma-4-31b-it-tp2 | 2 | 8 | base | 2 | 14.56 | 0.04 | 23.628 | 0.019 | 0 | eb2de0265a |
| g4-31b-tp2-8u | cpu | ingested-gemma-4-31b-it-tp2 | 2 | 8 | target | 2 | 14.57 | 0.00 | 23.667 | 0.000 | 0 | ff680c8020 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| l3b-tp2-32u | cpu | target vs base | +4.0 | +0.8 | +57 | +1.15 (0.02, 2, +69.9) | +57 (36, 2, +2.3) |
| l8b-tp2-8u | cpu | target vs base | +17.0 | -3.9 | -139 | +14.20 (0.74, 2, +27.1) | -139 (63, 2, -3.1) |
| l70b-tp2-8u | cpu | target vs base | +0.0 | -0.0 | -2 | +0.00 (0.00, 2, +1.0) | -2 (4, 2, -0.6) |
| l70b-tp2-4u | cpu | target vs base | -0.0 | -0.0 | -2 | -0.00 (0.00, 2, -0.5) | -2 (2, 2, -1.4) |
| l70b-tp4-4u | cpu | target vs base | -0.2 | +0.0 | +2 | -0.06 (0.10, 2, -0.8) | +2 (11, 2, +0.3) |
| mixtral-tp2-8u | cpu | target vs base | -0.3 | +0.0 | +0 | -0.09 (0.06, 2, -2.1) | +0 (0, 2, +2.4) |
| q25-32b-tp2-8u | cpu | target vs base | +1.1 | +0.1 | +12 | +0.34 (0.01, 2, +32.5) | +12 (2, 2, +7.2) |
| q3-4b-tp2-8u | cpu | target vs base | +21.8 | -21.8 | -859 | +11.49 (0.20, 2, +82.9) | -859 (0, 2, -5724.5) |
| q3-4b-tp4-8u | cpu | target vs base | +8.8 | -13.7 | -336 | +7.14 (2.52, 2, +4.0) | -336 (7, 2, -69.2) |
| g2-9b-tp2-8u | cpu | target vs base | +0.1 | -0.0 | -1 | +0.04 (0.17, 2, +0.3) | -1 (5, 2, -0.4) |
| gptoss-tp4-8u | cpu | target vs base | -0.3 | +7.8 | +206 | -0.19 (0.95, 2, -0.3) | +206 (23, 2, +12.6) |
| g4-31b-tp2-8u | cpu | target vs base | +0.0 | +0.2 | +39 | +0.00 (0.04, 2, +0.2) | +39 (19, 2, +2.9) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

