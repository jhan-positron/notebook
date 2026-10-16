# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 83.38 | 0.12 | 3.121 | 0.005 | 0 | 0.0 | c6ec38813d |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 83.67 | 0.22 | 3.121 | 0.002 | 0 | 0.0 | 37064d72b2 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 18.89 | 0.01 | 51.618 | 0.067 | 0 | 0.0 | c6ec38813d |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 18.91 | 0.03 | 51.787 | 0.107 | 0 | 0.0 | 37064d72b2 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | new vs head | +0.4 | -0.0 | -0 | +0.29 (0.34, 3, +1.5) | -0 (5, 3, -0.0) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | +0.1 | +0.3 | +169 | +0.01 (0.04, 3, +0.7) | +169 (69, 3, +4.2) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

