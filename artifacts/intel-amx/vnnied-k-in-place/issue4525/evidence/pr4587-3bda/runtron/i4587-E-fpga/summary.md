# i4587-20260924 summary (base = main 996f58ec82, head = PR #4557, new = draft PR #4587; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 125.08 | 0.19 | 3.147 | 0.004 | 0 | 0.0 | 996f58ec82 |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 125.07 | 0.10 | 3.157 | 0.001 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 125.63 | 0.20 | 3.149 | 0.001 | 0 | 0.0 | c73e7fb2f9 |
| q3-4b-tp2-8u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 61.25 | 0.12 | 28.348 | 0.014 | 0 | 0.0 | 996f58ec82 |
| q3-4b-tp2-8u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 61.26 | 0.02 | 28.240 | 0.012 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 61.22 | 0.10 | 28.318 | 0.015 | 0 | 0.0 | c73e7fb2f9 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | head vs base | -0.0 | +0.3 | +11 | -0.01 (0.23, 3, -0.1) | +11 (4, 3, +4.3) |
| q3-4b-tp2-8u-p1024 | fpga | new vs base | +0.4 | +0.1 | +2 | +0.55 (0.36, 3, +2.6) | +2 (4, 3, +0.9) |
| q3-4b-tp2-8u-p1024 | fpga | new vs head | +0.4 | -0.3 | -9 | +0.56 (0.27, 3, +3.6) | -9 (1, 3, -15.4) |
| q3-4b-tp2-8u-p8192 | fpga | head vs base | +0.0 | -0.4 | -108 | +0.01 (0.14, 3, +0.1) | -108 (6, 3, -31.0) |
| q3-4b-tp2-8u-p8192 | fpga | new vs base | -0.1 | -0.1 | -30 | -0.03 (0.03, 3, -1.7) | -30 (18, 3, -2.9) |
| q3-4b-tp2-8u-p8192 | fpga | new vs head | -0.1 | +0.3 | +78 | -0.04 (0.11, 3, -0.6) | +78 (21, 3, +6.4) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

