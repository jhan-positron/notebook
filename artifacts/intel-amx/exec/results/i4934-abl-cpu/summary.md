# i4934-abl-cpu summary (4 arms): headoff = PR #4898 dfafd13dce; fixoff = the fix c30a86f252; lazyoff = ablation a1 (tail rows through the reader, per-page mask read kept); baseoff = ablation a2 (constant block mask, no per-page read, tail rows through the reader); all TRON_AMX_DISABLE=1, CPU attention

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 75.98 | 0.09 | 3.857 | 0.007 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fixoff | 3 | 74.60 | 0.10 | 3.858 | 0.002 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | lazyoff | 3 | 75.53 | 0.04 | 3.881 | 0.002 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 75.95 | 0.22 | 3.860 | 0.006 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 15.40 | 0.02 | 117.165 | 0.093 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fixoff | 3 | 15.16 | 0.02 | 117.352 | 0.088 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | lazyoff | 3 | 15.16 | 0.00 | 119.231 | 0.097 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 15.31 | 0.02 | 117.757 | 0.055 | 0 | 0.0 | c30a86f252 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | fixoff vs headoff | -1.8 | +0.0 | +1 | -1.38 (0.18, 3, -13.1) | +1 (9, 3, +0.3) |
| q3-4b-tp2-8u-p1024 | cpu | lazyoff vs headoff | -0.6 | +0.6 | +24 | -0.45 (0.09, 3, -8.4) | +24 (9, 3, +4.7) |
| q3-4b-tp2-8u-p1024 | cpu | baseoff vs headoff | -0.0 | +0.1 | +3 | -0.03 (0.28, 3, -0.2) | +3 (10, 3, +0.5) |
| q3-4b-tp2-8u-p1024 | cpu | fixoff vs lazyoff | -1.2 | -0.6 | -23 | -0.92 (0.13, 3, -12.6) | -23 (2, 3, -20.5) |
| q3-4b-tp2-8u-p1024 | cpu | lazyoff vs baseoff | -0.6 | +0.6 | +22 | -0.43 (0.26, 3, -2.8) | +22 (7, 3, +5.3) |
| q3-4b-tp2-8u-p8192 | cpu | fixoff vs headoff | -1.6 | +0.2 | +187 | -0.24 (0.01, 3, -62.8) | +187 (169, 3, +1.9) |
| q3-4b-tp2-8u-p8192 | cpu | lazyoff vs headoff | -1.5 | +1.8 | +2066 | -0.24 (0.02, 3, -19.6) | +2066 (148, 3, +24.2) |
| q3-4b-tp2-8u-p8192 | cpu | baseoff vs headoff | -0.6 | +0.5 | +592 | -0.09 (0.02, 3, -10.3) | +592 (59, 3, +17.5) |
| q3-4b-tp2-8u-p8192 | cpu | fixoff vs lazyoff | -0.0 | -1.6 | -1879 | -0.00 (0.02, 3, -0.3) | -1879 (55, 3, -59.4) |
| q3-4b-tp2-8u-p8192 | cpu | lazyoff vs baseoff | -1.0 | +1.3 | +1474 | -0.15 (0.02, 3, -15.7) | +1474 (90, 3, +28.3) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

