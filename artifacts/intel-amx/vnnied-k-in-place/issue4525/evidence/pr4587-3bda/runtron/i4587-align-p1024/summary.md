# i4587-20260924 summary (base = main 996f58ec82, head = PR #4557, new = draft PR #4587; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 72.43 | 0.23 | 3.941 | 0.001 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 71.80 | 0.07 | 3.955 | 0.003 | 0 | 0.0 | c73e7fb2f9 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 72.36 | 0.16 | 3.938 | 0.003 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | altoff | 3 | 72.47 | 0.19 | 3.939 | 0.004 | 0 | 0.0 | c73e7fb2f9 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | headoff vs baseoff | -0.9 | +0.4 | +14 | -0.63 (0.28, 3, -3.9) | +14 (4, 3, +5.9) |
| q3-4b-tp2-8u-p1024 | cpu | altoff vs newoff | +0.2 | +0.0 | +0 | +0.11 (0.27, 3, +0.7) | +0 (5, 3, +0.1) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs baseoff | -0.1 | -0.1 | -3 | -0.07 (0.12, 3, -1.1) | -3 (3, 3, -1.3) |
| q3-4b-tp2-8u-p1024 | cpu | altoff vs headoff | +0.9 | -0.4 | -16 | +0.66 (0.21, 3, +5.6) | -16 (2, 3, -11.9) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

