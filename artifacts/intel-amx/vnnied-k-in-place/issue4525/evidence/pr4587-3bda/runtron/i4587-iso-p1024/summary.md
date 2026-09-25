# i4587-20260924 summary (base = main 996f58ec82, head = PR #4557, new = draft PR #4587; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 72.53 | 0.11 | 3.942 | 0.006 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 71.70 | 0.02 | 3.949 | 0.009 | 0 | 0.0 | 39a6899446 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 71.87 | 0.17 | 3.959 | 0.014 | 0 | 0.0 | c73e7fb2f9 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | headoff vs baseoff | -1.2 | +0.2 | +8 | -0.84 (0.12, 3, -11.7) | +8 (15, 3, +0.9) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs baseoff | -0.9 | +0.4 | +17 | -0.67 (0.14, 3, -8.2) | +17 (8, 3, +3.6) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs headoff | +0.2 | +0.2 | +10 | +0.17 (0.19, 3, +1.5) | +10 (22, 3, +0.8) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

