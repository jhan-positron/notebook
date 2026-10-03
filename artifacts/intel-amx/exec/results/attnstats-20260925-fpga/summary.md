# attnstats-20260924 summary (attention path stats: base/base2 = main binary 66c7bb8db1 with the switch unset (same-binary control pair), head = branch binary with TRON_ATTN_STATS unset (off-state cost), headon = branch binary with TRON_ATTN_STATS=1 (on-state cost), headkill = headon + TRON_AMX_DISABLE=1 (kill-switch cross-check); attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headon2 | 1 | 124.34 | 0.00 | 3.264 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headkill2 | 1 | 124.49 | 0.00 | 3.248 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-1u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 1 | headon2 | 1 | 226.65 | 0.00 | 0.409 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-1u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 1 | headkill2 | 1 | 225.04 | 0.00 | 0.408 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-8u-p64 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headon2 | 1 | 131.05 | 0.00 | 0.183 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-8u-p64 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headkill2 | 1 | 130.97 | 0.00 | 0.179 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-8u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headon2 | 1 | 61.20 | 0.00 | 29.266 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-8u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headkill2 | 1 | 61.04 | 0.00 | 29.415 | 0.000 | 0 | 0.0 | cbf1bb6c0c |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

