# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 132.07 | 0.24 | 3.192 | 0.021 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 132.84 | 0.48 | 3.171 | 0.012 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 129.60 | 0.10 | 3.157 | 0.011 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | base | 3 | 163.49 | 1.06 | 2.232 | 0.002 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | new | 3 | 163.07 | 0.83 | 2.192 | 0.010 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | head | 3 | 145.44 | 0.48 | 2.170 | 0.013 | 0 | 0.0 | dfafd13dce |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | fpga | new vs base | +0.6 | -0.6 | -21 | +0.77 (0.59, 3, +2.3) | -21 (32, 3, -1.1) |
| q3-4b-tp2-8u-p1024 | fpga | new vs head | +2.5 | +0.5 | +14 | +3.24 (0.46, 3, +12.1) | +14 (22, 3, +1.1) |
| q3-4b-tp2-8u-p1024 | fpga | head vs base | -1.9 | -1.1 | -35 | -2.47 (0.16, 3, -26.1) | -35 (11, 3, -5.6) |
| q3-4b-tp4-8u-p1024 | fpga | new vs base | -0.3 | -1.8 | -40 | -0.42 (1.26, 3, -0.6) | -40 (8, 3, -8.5) |
| q3-4b-tp4-8u-p1024 | fpga | new vs head | +12.1 | +1.0 | +22 | +17.63 (1.25, 3, +24.4) | +22 (23, 3, +1.6) |
| q3-4b-tp4-8u-p1024 | fpga | head vs base | -11.0 | -2.8 | -62 | -18.05 (0.94, 3, -33.2) | -62 (15, 3, -7.2) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

