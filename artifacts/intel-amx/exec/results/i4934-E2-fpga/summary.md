# i4934-E2-fpga summary (head = PR #4898 dfafd13dce, new = PR #4901 ea94e95a4e, fix = issue #4934 branch b87d20dd81d5d7b562e5b9eea6656de7a6c6df84; attn = fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 130.00 | 0.38 | 3.117 | 0.018 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 133.55 | 0.25 | 3.123 | 0.011 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fix | 3 | 133.14 | 0.53 | 3.106 | 0.004 | 0 | 0.0 | b87d20dd81 |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | head | 3 | 147.23 | 1.13 | 2.160 | 0.016 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | new | 3 | 165.17 | 0.32 | 2.164 | 0.010 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | fix | 3 | 165.21 | 0.89 | 2.170 | 0.011 | 0 | 0.0 | b87d20dd81 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | fix vs new | -0.3 | -0.5 | -17 | -0.41 (0.70, 3, -1.0) | -17 (15, 3, -2.0) |
| q3-4b-tp2-8u-p1024 | fpga | fix vs head | +2.4 | -0.3 | -11 | +3.14 (0.34, 3, +16.0) | -11 (16, 3, -1.1) |
| q3-4b-tp2-8u-p1024 | fpga | new vs head | +2.7 | +0.2 | +6 | +3.55 (0.63, 3, +9.8) | +6 (27, 3, +0.4) |
| q3-4b-tp4-8u-p1024 | fpga | fix vs new | +0.0 | +0.3 | +6 | +0.04 (1.18, 3, +0.1) | +6 (20, 3, +0.5) |
| q3-4b-tp4-8u-p1024 | fpga | fix vs head | +12.2 | +0.5 | +10 | +17.98 (1.81, 3, +17.2) | +10 (19, 3, +0.9) |
| q3-4b-tp4-8u-p1024 | fpga | new vs head | +12.2 | +0.2 | +4 | +17.93 (1.14, 3, +27.2) | +4 (12, 3, +0.6) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

