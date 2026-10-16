# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 128.72 | 0.38 | 3.184 | 0.007 | 0 | 0.0 | be0d5565b3 |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 125.47 | 0.16 | 3.193 | 0.027 | 0 | 0.0 | 30c4ac82cb |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 125.97 | 0.44 | 3.142 | 0.014 | 0 | 0.0 | 37064d72b2 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | new vs head | +0.4 | -1.6 | -51 | +0.50 (0.58, 3, +1.5) | -51 (28, 3, -3.1) |
| q3-4b-tp2-8u-p1024 | fpga | new vs base | -2.1 | -1.3 | -42 | -2.75 (0.65, 3, -7.3) | -42 (19, 3, -3.7) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

