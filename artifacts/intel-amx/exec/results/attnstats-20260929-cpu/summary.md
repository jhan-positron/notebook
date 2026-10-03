# attnstats-20260924 summary (attention path stats: base/base2 = main binary 66c7bb8db1 with the switch unset (same-binary control pair), head = branch binary with TRON_ATTN_STATS unset (off-state cost), headon = branch binary with TRON_ATTN_STATS=1 (on-state cost), headkill = headon + TRON_AMX_DISABLE=1 (kill-switch cross-check); attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

