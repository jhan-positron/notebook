# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 80.98 | 0.10 | 3.181 | 0.004 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 84.75 | 0.12 | 3.125 | 0.006 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 73.19 | 0.14 | 3.905 | 0.007 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 85.36 | 0.33 | 3.116 | 0.003 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 75.80 | 0.23 | 3.894 | 0.003 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 17.31 | 0.02 | 52.549 | 0.091 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 18.95 | 0.03 | 51.852 | 0.148 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 15.05 | 0.07 | 117.812 | 0.103 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 18.90 | 0.02 | 51.622 | 0.141 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 15.49 | 0.06 | 117.359 | 0.047 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | base | 3 | 117.36 | 0.49 | 2.215 | 0.004 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | new | 3 | 120.22 | 0.39 | 2.142 | 0.004 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | newoff | 3 | 109.03 | 0.39 | 2.417 | 0.009 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | head | 3 | 120.78 | 0.77 | 2.137 | 0.011 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | headoff | 3 | 111.27 | 0.50 | 2.402 | 0.003 | 0 | 0.0 | dfafd13dce |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | new vs base | +4.7 | -1.8 | -56 | +3.77 (0.10, 3, +65.8) | -56 (10, 3, -9.8) |
| q3-4b-tp2-8u-p1024 | cpu | new vs head | -0.7 | +0.3 | +9 | -0.61 (0.43, 3, -2.4) | +9 (8, 3, +1.9) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs new | -13.6 | +24.9 | +780 | -11.56 (0.13, 3, -150.9) | +780 (12, 3, +109.8) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs headoff | -3.4 | +0.3 | +10 | -2.61 (0.37, 3, -12.4) | +10 (7, 3, +2.4) |
| q3-4b-tp2-8u-p1024 | cpu | head vs base | +5.4 | -2.0 | -65 | +4.38 (0.36, 3, +21.3) | -65 (2, 3, -47.4) |
| q3-4b-tp2-8u-p8192 | cpu | new vs base | +9.4 | -1.3 | -697 | +1.63 (0.04, 3, +76.5) | -697 (239, 3, -5.1) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | +0.2 | +0.4 | +231 | +0.04 (0.05, 3, +1.5) | +231 (280, 3, +1.4) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs new | -20.6 | +127.2 | +65960 | -3.90 (0.10, 3, -69.7) | +65960 (190, 3, +600.1) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs headoff | -2.9 | +0.4 | +453 | -0.45 (0.02, 3, -45.2) | +453 (88, 3, +8.9) |
| q3-4b-tp2-8u-p8192 | cpu | head vs base | +9.2 | -1.8 | -928 | +1.59 (0.02, 3, +122.2) | -928 (78, 3, -20.5) |
| q3-4b-tp4-8u-p1024 | cpu | new vs base | +2.4 | -3.3 | -73 | +2.86 (0.80, 3, +6.2) | -73 (1, 3, -85.4) |
| q3-4b-tp4-8u-p1024 | cpu | new vs head | -0.5 | +0.2 | +5 | -0.56 (1.14, 3, -0.9) | +5 (7, 3, +1.4) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs new | -9.3 | +12.8 | +275 | -11.18 (0.69, 3, -28.2) | +275 (7, 3, +72.5) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs headoff | -2.0 | +0.6 | +15 | -2.24 (0.87, 3, -4.4) | +15 (11, 3, +2.5) |
| q3-4b-tp4-8u-p1024 | cpu | head vs base | +2.9 | -3.5 | -78 | +3.42 (0.75, 3, +7.9) | -78 (8, 3, -17.5) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

