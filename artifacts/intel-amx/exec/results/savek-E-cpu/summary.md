# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 83.39 | 0.42 | 3.139 | 0.007 | 0 | 0.0 | 30c4ac82cb |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 83.83 | 0.51 | 3.136 | 0.002 | 0 | 0.0 | 19ae84d95a |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 18.90 | 0.03 | 52.738 | 0.116 | 0 | 0.0 | 30c4ac82cb |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 18.80 | 0.01 | 55.937 | 4.834 | 0 | 0.0 | 19ae84d95a |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | new vs head | +0.5 | -0.1 | -3 | +0.45 (0.11, 3, +7.0) | -3 (5, 3, -1.1) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | -0.5 | +6.1 | +3199 | -0.10 (0.03, 3, -6.4) | +3199 (4719, 3, +1.2) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

