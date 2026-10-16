# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 79.37 | 0.27 | 3.178 | 0.003 | 0 | 0.0 | be0d5565b3 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 83.32 | 0.17 | 3.147 | 0.006 | 0 | 0.0 | 30c4ac82cb |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 83.60 | 0.12 | 3.121 | 0.005 | 0 | 0.0 | 37064d72b2 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 17.13 | 0.02 | 52.542 | 0.058 | 0 | 0.0 | be0d5565b3 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 18.93 | 0.02 | 52.849 | 0.162 | 0 | 0.0 | 30c4ac82cb |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 18.90 | 0.03 | 51.745 | 0.143 | 0 | 0.0 | 37064d72b2 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | new vs head | +0.3 | -0.8 | -26 | +0.28 (0.14, 3, +3.6) | -26 (2, 3, -22.8) |
| q3-4b-tp2-8u-p1024 | cpu | new vs base | +5.3 | -1.8 | -57 | +4.23 (0.19, 3, +39.4) | -57 (3, 3, -33.8) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | -0.1 | -2.1 | -1103 | -0.02 (0.05, 3, -0.9) | -1103 (99, 3, -19.2) |
| q3-4b-tp2-8u-p8192 | cpu | new vs base | +10.4 | -1.5 | -797 | +1.77 (0.04, 3, +68.9) | -797 (196, 3, -7.0) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

