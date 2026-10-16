# i4934-E-fpga summary (head = PR #4898 dfafd13dce, new = PR #4901 ea94e95a4e, fix = issue #4934 branch c30a86f252195d8be2a8b0edfa93bf2a97f44470; attn = fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 130.37 | 0.35 | 3.118 | 0.009 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 133.12 | 0.45 | 3.142 | 0.013 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fix | 3 | 133.15 | 0.07 | 3.102 | 0.003 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | head | 3 | 147.39 | 0.71 | 2.159 | 0.017 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | new | 3 | 166.32 | 0.31 | 2.159 | 0.003 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | fix | 3 | 164.25 | 0.19 | 2.155 | 0.008 | 0 | 0.0 | c30a86f252 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | fix vs new | +0.0 | -1.3 | -40 | +0.03 (0.39, 3, +0.1) | -40 (10, 3, -7.1) |
| q3-4b-tp2-8u-p1024 | fpga | fix vs head | +2.1 | -0.5 | -15 | +2.78 (0.30, 3, +16.1) | -15 (10, 3, -2.6) |
| q3-4b-tp2-8u-p1024 | fpga | new vs head | +2.1 | +0.8 | +25 | +2.75 (0.10, 3, +49.1) | +25 (14, 3, +2.9) |
| q3-4b-tp4-8u-p1024 | fpga | fix vs new | -1.2 | -0.1 | -3 | -2.08 (0.21, 3, -17.0) | -3 (6, 3, -0.9) |
| q3-4b-tp4-8u-p1024 | fpga | fix vs head | +11.4 | -0.2 | -3 | +16.85 (0.57, 3, +51.5) | -3 (15, 3, -0.4) |
| q3-4b-tp4-8u-p1024 | fpga | new vs head | +12.8 | -0.0 | -0 | +18.93 (0.40, 3, +81.5) | -0 (18, 3, -0.0) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

