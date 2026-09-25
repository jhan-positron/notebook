# attnstats-20260924 summary (attention path stats: base/base2 = main binary 66c7bb8db1 with the switch unset (same-binary control pair), head = branch binary with TRON_ATTN_STATS unset (off-state cost), headon = branch binary with TRON_ATTN_STATS=1 (on-state cost), headkill = headon + TRON_AMX_DISABLE=1 (kill-switch cross-check); attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 79.95 | 0.29 | 3.146 | 0.006 | 0 | 0.0 | 66c7bb8db1 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 79.81 | 0.17 | 3.153 | 0.008 | 0 | 0.0 | 9b3832eb4b |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headon | 3 | 79.91 | 0.24 | 3.161 | 0.012 | 0 | 0.0 | 9b3832eb4b |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base2 | 3 | 79.67 | 0.29 | 3.147 | 0.006 | 0 | 0.0 | 66c7bb8db1 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headkill | 1 | 71.56 | 0.00 | 3.991 | 0.000 | 0 | 0.0 | 9b3832eb4b |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 17.12 | 0.00 | 52.648 | 0.121 | 0 | 0.0 | 66c7bb8db1 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 17.25 | 0.04 | 52.778 | 0.407 | 0 | 0.0 | 9b3832eb4b |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headon | 3 | 17.24 | 0.02 | 53.007 | 0.099 | 0 | 0.0 | 9b3832eb4b |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base2 | 3 | 17.11 | 0.02 | 52.676 | 0.046 | 0 | 0.0 | 66c7bb8db1 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | head vs base | -0.2 | +0.2 | +8 | -0.13 (0.32, 3, -0.7) | +8 (12, 3, +1.1) |
| q3-4b-tp2-8u-p8192 | cpu | head vs base | +0.8 | +0.2 | +131 | +0.13 (0.04, 3, +5.4) | +131 (323, 3, +0.7) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

