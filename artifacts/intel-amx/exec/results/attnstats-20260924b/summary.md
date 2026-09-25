# attnstats-20260924 summary (attention path stats: base/base2 = main binary 66c7bb8db1 with the switch unset (same-binary control pair), head = branch binary with TRON_ATTN_STATS unset (off-state cost), headon = branch binary with TRON_ATTN_STATS=1 (on-state cost), headkill = headon + TRON_AMX_DISABLE=1 (kill-switch cross-check); attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base3 | 3 | 79.78 | 0.41 | 3.139 | 0.008 | 0 | 0.0 | 66c7bb8db1 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head2 | 3 | 79.81 | 0.38 | 3.151 | 0.003 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headon2 | 3 | 80.10 | 0.17 | 3.156 | 0.006 | 0 | 0.0 | cbf1bb6c0c |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

