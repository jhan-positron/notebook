# sync4424-20261002 summary (base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746); <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 80.61 | 0.16 | 3.185 | 0.010 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 75.45 | 0.11 | 4.005 | 0.002 | 0 | 0.0 | 82d05e94be |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 75.07 | 0.14 | 3.941 | 0.000 | 0 | 0.0 | 82d05e94be |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 72.62 | 0.19 | 3.981 | 0.007 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 17.26 | 0.01 | 53.510 | 1.634 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 15.26 | 0.03 | 117.516 | 0.160 | 0 | 0.0 | 82d05e94be |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 15.30 | 0.05 | 117.090 | 0.301 | 0 | 0.0 | 82d05e94be |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 14.64 | 0.03 | 122.938 | 0.126 | 0 | 0.0 | 72308ec90c |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | new vs base | -6.4 | +25.8 | +820 | -5.16 (0.24, 3, -36.5) | +820 (9, 3, +158.8) |
| q3-4b-tp2-8u-p1024 | cpu | new vs head | +3.9 | +0.6 | +24 | +2.83 (0.23, 3, +21.7) | +24 (5, 3, +8.3) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs new | -0.5 | -1.6 | -65 | -0.37 (0.12, 3, -5.4) | -65 (2, 3, -65.2) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs head | +3.4 | -1.0 | -41 | +2.45 (0.12, 3, +36.3) | -41 (7, 3, -10.5) |
| q3-4b-tp2-8u-p8192 | cpu | new vs base | -11.6 | +119.6 | +64006 | -2.00 (0.02, 3, -174.6) | +64006 (1594, 3, +69.6) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | +4.3 | -4.4 | -5422 | +0.63 (0.03, 3, +32.8) | -5422 (164, 3, -57.2) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs new | +0.3 | -0.4 | -425 | +0.04 (0.08, 3, +0.9) | -425 (414, 3, -1.8) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs head | +4.5 | -4.8 | -5847 | +0.66 (0.09, 3, +13.4) | -5847 (424, 3, -23.9) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

