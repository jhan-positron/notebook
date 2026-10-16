# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 81.07 | 0.20 | 3.175 | 0.001 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 76.01 | 0.44 | 4.003 | 0.010 | 0 | 0.0 | a711aeee83 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 75.58 | 0.25 | 3.942 | 0.007 | 0 | 0.0 | a711aeee83 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 72.40 | 0.18 | 3.986 | 0.005 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 17.29 | 0.02 | 52.637 | 0.044 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 15.39 | 0.01 | 117.261 | 0.190 | 0 | 0.0 | a711aeee83 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 15.44 | 0.04 | 116.592 | 0.048 | 0 | 0.0 | a711aeee83 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 14.65 | 0.03 | 122.851 | 0.058 | 0 | 0.0 | 72308ec90c |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | new vs base | -6.2 | +26.1 | +828 | -5.06 (0.60, 3, -14.6) | +828 (11, 3, +133.6) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs baseoff | +4.4 | -1.1 | -44 | +3.18 (0.25, 3, +22.4) | -44 (11, 3, -6.9) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs new | -0.6 | -1.5 | -61 | -0.43 (0.68, 3, -1.1) | -61 (13, 3, -8.0) |
| q3-4b-tp2-8u-p1024 | cpu | baseoff vs base | -10.7 | +25.5 | +811 | -8.67 (0.14, 3, -105.1) | +811 (6, 3, +220.1) |
| q3-4b-tp2-8u-p8192 | cpu | new vs base | -11.0 | +122.8 | +64624 | -1.90 (0.01, 3, -411.8) | +64624 (190, 3, +589.0) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs baseoff | +5.3 | -5.1 | -6259 | +0.78 (0.04, 3, +32.8) | -6259 (102, 3, -106.0) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs new | +0.3 | -0.6 | -669 | +0.04 (0.04, 3, +1.9) | -669 (199, 3, -5.8) |
| q3-4b-tp2-8u-p8192 | cpu | baseoff vs base | -15.3 | +133.4 | +70214 | -2.64 (0.05, 3, -89.8) | +70214 (101, 3, +1208.8) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

