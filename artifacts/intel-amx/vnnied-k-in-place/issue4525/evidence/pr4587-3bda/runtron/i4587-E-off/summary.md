# i4587-20260924 summary (base = main 996f58ec82, head = PR #4557, new = draft PR #4587; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 71.80 | 0.21 | 3.943 | 0.005 | 0 | 0.0 | 996f58ec82 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 72.31 | 0.12 | 3.939 | 0.009 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 71.67 | 0.27 | 3.956 | 0.007 | 0 | 0.0 | c73e7fb2f9 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 14.55 | 0.02 | 122.582 | 0.041 | 0 | 0.0 | 996f58ec82 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 14.57 | 0.02 | 122.335 | 0.057 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 14.60 | 0.01 | 123.582 | 0.088 | 0 | 0.0 | c73e7fb2f9 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | headoff vs baseoff | +0.7 | -0.1 | -3 | +0.51 (0.18, 3, +4.8) | -3 (7, 3, -0.8) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs baseoff | -0.2 | +0.4 | +14 | -0.13 (0.44, 3, -0.5) | +14 (11, 3, +2.1) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs headoff | -0.9 | +0.4 | +17 | -0.64 (0.38, 3, -2.9) | +17 (17, 3, +1.8) |
| q3-4b-tp2-8u-p8192 | cpu | headoff vs baseoff | +0.2 | -0.2 | -247 | +0.02 (0.02, 3, +1.7) | -247 (88, 3, -4.9) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs baseoff | +0.3 | +0.8 | +1000 | +0.05 (0.03, 3, +3.2) | +1000 (55, 3, +31.3) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs headoff | +0.2 | +1.0 | +1247 | +0.03 (0.02, 3, +2.6) | +1247 (111, 3, +19.5) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

