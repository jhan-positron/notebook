# i4587-20260924 summary (base = main 996f58ec82, head = PR #4557, new = draft PR #4587; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 79.50 | 0.22 | 3.148 | 0.002 | 0 | 0.0 | 996f58ec82 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 79.81 | 0.20 | 3.150 | 0.005 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 79.83 | 0.14 | 3.142 | 0.001 | 0 | 0.0 | c73e7fb2f9 |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 52.35 | 0.09 | 7.260 | 0.016 | 0 | 0.0 | 996f58ec82 |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 52.45 | 0.15 | 7.210 | 0.012 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 52.61 | 0.10 | 7.215 | 0.007 | 0 | 0.0 | c73e7fb2f9 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 17.12 | 0.01 | 52.971 | 0.338 | 0 | 0.0 | 996f58ec82 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 17.06 | 0.01 | 52.553 | 0.224 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 17.04 | 0.00 | 52.651 | 0.127 | 0 | 0.0 | c73e7fb2f9 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | head vs base | +0.4 | +0.1 | +2 | +0.31 (0.18, 3, +3.0) | +2 (5, 3, +0.8) |
| q3-4b-tp2-8u-p1024 | cpu | new vs base | +0.4 | -0.2 | -6 | +0.33 (0.36, 3, +1.6) | -6 (3, 3, -3.7) |
| q3-4b-tp2-8u-p1024 | cpu | new vs head | +0.0 | -0.3 | -8 | +0.02 (0.31, 3, +0.1) | -8 (5, 3, -2.7) |
| q3-4b-tp2-8u-p2048 | cpu | head vs base | +0.2 | -0.7 | -50 | +0.10 (0.09, 3, +2.0) | -50 (11, 3, -8.0) |
| q3-4b-tp2-8u-p2048 | cpu | new vs base | +0.5 | -0.6 | -45 | +0.26 (0.19, 3, +2.3) | -45 (18, 3, -4.4) |
| q3-4b-tp2-8u-p2048 | cpu | new vs head | +0.3 | +0.1 | +5 | +0.16 (0.24, 3, +1.1) | +5 (18, 3, +0.5) |
| q3-4b-tp2-8u-p8192 | cpu | head vs base | -0.3 | -0.8 | -418 | -0.06 (0.01, 3, -6.7) | -418 (119, 3, -6.1) |
| q3-4b-tp2-8u-p8192 | cpu | new vs base | -0.5 | -0.6 | -321 | -0.08 (0.01, 3, -12.7) | -321 (416, 3, -1.3) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | -0.1 | +0.2 | +98 | -0.02 (0.02, 3, -2.3) | +98 (297, 3, +0.6) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

