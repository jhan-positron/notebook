# glimext-20261018 summary (base = PR #5015 merge base, main 6198824246; head = PR #5015 head 5061623a34; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| l8b-tp2-8u-p1024-cpu | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | base | 4 | 119.22 | 0.11 | 3.405 | 0.002 | 0 | 0.0 | 6198824246 |
| l8b-tp2-8u-p1024-cpu | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | head | 4 | 119.35 | 0.14 | 3.408 | 0.002 | 0 | 0.0 | 5061623a34 |
| q4b-tp2-8u-p1024-fpga | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 4 | 133.61 | 0.16 | 3.056 | 0.002 | 0 | 0.0 | 6198824246 |
| q4b-tp2-8u-p1024-fpga | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 4 | 134.17 | 0.15 | 3.057 | 0.003 | 0 | 0.0 | 5061623a34 |
| gptoss-tp4-8u-p1024-fpga | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | base | 4 | 96.77 | 1.47 | 2.706 | 0.005 | 0 | 0.0 | 6198824246 |
| gptoss-tp4-8u-p1024-fpga | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | head | 4 | 97.05 | 0.35 | 2.701 | 0.002 | 0 | 0.0 | 5061623a34 |
| l8b-tp2-8u-p8192-cpu | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | base | 8 | 25.31 | 0.06 | 35.293 | 0.072 | 0 | 0.0 | 6198824246 |
| l8b-tp2-8u-p8192-cpu | cpu | llama-3.1-8b-instruct-good-tp2 | 2 | 8 | head | 8 | 25.24 | 0.03 | 34.818 | 0.055 | 0 | 0.0 | 5061623a34 |
| q4b-tp2-8u-p8192-fpga | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 4 | 61.74 | 0.06 | 26.396 | 0.024 | 0 | 0.0 | 6198824246 |
| q4b-tp2-8u-p8192-fpga | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 4 | 61.81 | 0.07 | 26.384 | 0.013 | 0 | 0.0 | 5061623a34 |
| gptoss-tp4-8u-p2048-fpga | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | base | 4 | 95.05 | 0.63 | 5.090 | 0.007 | 0 | 0.0 | 6198824246 |
| gptoss-tp4-8u-p2048-fpga | fpga | ingested-gpt-oss-120b-tp4 | 4 | 8 | head | 4 | 94.85 | 1.67 | 5.093 | 0.011 | 0 | 0.0 | 5061623a34 |
| glm-tp2-8u-p1024-fpga | fpga | ingested-meta-models--Muse-Glimmer-30B-tp2 | 2 | 8 | base | 4 | 38.34 | 0.02 | 15.275 | 0.035 | 0 | 0.0 | 6198824246 |
| glm-tp2-8u-p1024-fpga | fpga | ingested-meta-models--Muse-Glimmer-30B-tp2 | 2 | 8 | head | 4 | 41.92 | 0.05 | 14.840 | 0.013 | 0 | 0.0 | 5061623a34 |
| glm-tp2-8u-p2048-fpga | fpga | ingested-meta-models--Muse-Glimmer-30B-tp2 | 2 | 8 | base | 4 | 33.01 | 0.02 | 33.941 | 0.032 | 0 | 0.0 | 6198824246 |
| glm-tp2-8u-p2048-fpga | fpga | ingested-meta-models--Muse-Glimmer-30B-tp2 | 2 | 8 | head | 4 | 38.17 | 0.05 | 30.922 | 0.006 | 0 | 0.0 | 5061623a34 |
| glm-tp4-8u-p1024-fpga | fpga | ingested-meta-models--Muse-Glimmer-30B-tp4 | 4 | 8 | base | 4 | 60.46 | 0.07 | 8.338 | 0.021 | 0 | 0.0 | 6198824246 |
| glm-tp4-8u-p1024-fpga | fpga | ingested-meta-models--Muse-Glimmer-30B-tp4 | 4 | 8 | head | 4 | 63.07 | 0.09 | 8.296 | 0.008 | 0 | 0.0 | 5061623a34 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| l8b-tp2-8u-p1024-cpu | cpu | head vs base | +0.1 | +0.1 | +3 | +0.13 (0.18, 4, +1.4) | +3 (4, 4, +1.5) |
| q4b-tp2-8u-p1024-fpga | fpga | head vs base | +0.4 | +0.0 | +1 | +0.56 (0.21, 4, +5.4) | +1 (2, 4, +0.7) |
| gptoss-tp4-8u-p1024-fpga | fpga | head vs base | +0.3 | -0.2 | -5 | +0.28 (1.18, 4, +0.5) | -5 (4, 4, -2.1) |
| l8b-tp2-8u-p8192-cpu | cpu | head vs base | -0.3 | -1.3 | -475 | -0.07 (0.05, 8, -3.7) | -475 (87, 8, -15.5) |
| q4b-tp2-8u-p8192-fpga | fpga | head vs base | +0.1 | -0.0 | -12 | +0.07 (0.13, 4, +1.0) | -12 (13, 4, -1.9) |
| gptoss-tp4-8u-p2048-fpga | fpga | head vs base | -0.2 | +0.1 | +3 | -0.19 (1.71, 4, -0.2) | +3 (18, 4, +0.4) |
| glm-tp2-8u-p1024-fpga | fpga | head vs base | +9.3 | -2.8 | -435 | +3.58 (0.07, 4, +99.7) | -435 (25, 4, -34.8) |
| glm-tp2-8u-p2048-fpga | fpga | head vs base | +15.6 | -8.9 | -3019 | +5.16 (0.05, 4, +202.1) | -3019 (29, 4, -210.0) |
| glm-tp4-8u-p1024-fpga | fpga | head vs base | +4.3 | -0.5 | -42 | +2.61 (0.11, 4, +48.6) | -42 (21, 4, -4.0) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

