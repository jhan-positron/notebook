# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 80.99 | 0.29 | 3.178 | 0.006 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 85.15 | 0.22 | 3.120 | 0.004 | 0 | 0.0 | 80bce9a08d |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 75.72 | 0.11 | 3.888 | 0.003 | 0 | 0.0 | 80bce9a08d |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 84.94 | 0.44 | 3.273 | 0.003 | 0 | 0.0 | 0ee8671d35 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 75.82 | 0.38 | 3.937 | 0.003 | 0 | 0.0 | 0ee8671d35 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 17.30 | 0.03 | 52.607 | 0.117 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 18.88 | 0.01 | 51.780 | 0.147 | 0 | 0.0 | 80bce9a08d |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 15.49 | 0.04 | 117.464 | 0.111 | 0 | 0.0 | 80bce9a08d |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 18.98 | 0.01 | 51.952 | 0.091 | 0 | 0.0 | 0ee8671d35 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 15.51 | 0.08 | 116.865 | 0.106 | 0 | 0.0 | 0ee8671d35 |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | base | 3 | 117.38 | 0.48 | 2.211 | 0.007 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | new | 3 | 121.36 | 0.12 | 2.135 | 0.010 | 0 | 0.0 | 80bce9a08d |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | newoff | 3 | 111.74 | 0.36 | 2.403 | 0.004 | 0 | 0.0 | 80bce9a08d |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | head | 3 | 120.28 | 0.63 | 2.378 | 0.003 | 0 | 0.0 | 0ee8671d35 |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | headoff | 3 | 111.08 | 0.67 | 2.535 | 0.011 | 0 | 0.0 | 0ee8671d35 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | new vs base | +5.1 | -1.8 | -57 | +4.16 (0.49, 3, +14.6) | -57 (4, 3, -22.5) |
| q3-4b-tp2-8u-p1024 | cpu | new vs head | +0.3 | -4.7 | -153 | +0.22 (0.61, 3, +0.6) | -153 (7, 3, -35.6) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs new | -11.1 | +24.6 | +768 | -9.43 (0.24, 3, -69.1) | +768 (7, 3, +198.9) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs headoff | -0.1 | -1.3 | -50 | -0.10 (0.28, 3, -0.6) | -50 (1, 3, -150.3) |
| q3-4b-tp2-8u-p1024 | cpu | head vs base | +4.9 | +3.0 | +95 | +3.95 (0.19, 3, +36.2) | +95 (8, 3, +20.3) |
| q3-4b-tp2-8u-p8192 | cpu | new vs base | +9.1 | -1.6 | -827 | +1.57 (0.03, 3, +108.4) | -827 (166, 3, -8.6) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | -0.6 | -0.3 | -172 | -0.10 (0.02, 3, -8.7) | -172 (131, 3, -2.3) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs new | -18.0 | +126.9 | +65684 | -3.39 (0.04, 3, -132.4) | +65684 (164, 3, +695.4) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs headoff | -0.1 | +0.5 | +599 | -0.02 (0.09, 3, -0.4) | +599 (217, 3, +4.8) |
| q3-4b-tp2-8u-p8192 | cpu | head vs base | +9.7 | -1.2 | -655 | +1.68 (0.03, 3, +94.8) | -655 (195, 3, -5.8) |
| q3-4b-tp4-8u-p1024 | cpu | new vs base | +3.4 | -3.4 | -75 | +3.98 (0.45, 3, +15.3) | -75 (9, 3, -13.9) |
| q3-4b-tp4-8u-p1024 | cpu | new vs head | +0.9 | -10.2 | -243 | +1.08 (0.73, 3, +2.6) | -243 (9, 3, -45.2) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs new | -7.9 | +12.5 | +268 | -9.63 (0.37, 3, -44.5) | +268 (6, 3, +77.0) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs headoff | +0.6 | -5.2 | -132 | +0.66 (0.42, 3, +2.7) | -132 (8, 3, -28.7) |
| q3-4b-tp4-8u-p1024 | cpu | head vs base | +2.5 | +7.6 | +167 | +2.90 (1.04, 3, +4.8) | +167 (4, 3, +80.0) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

