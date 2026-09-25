# i4525-20260922 summary (issue #4525 typed KV-cache tensors: base = main binary, head = branch binary, baseoff/headoff = the same binaries with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 79.02 | 0.28 | 3.159 | 0.002 | 0 | 0.0 | 0a51385e95 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 79.18 | 0.31 | 3.154 | 0.004 | 0 | 0.0 | 682064f8fb |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 71.60 | 0.35 | 3.962 | 0.004 | 0 | 0.0 | 0a51385e95 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 71.29 | 0.08 | 3.956 | 0.009 | 0 | 0.0 | 682064f8fb |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 52.12 | 0.12 | 7.261 | 0.004 | 0 | 0.0 | 0a51385e95 |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 52.46 | 0.18 | 7.242 | 0.007 | 0 | 0.0 | 682064f8fb |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 44.97 | 0.09 | 11.205 | 0.018 | 0 | 0.0 | 0a51385e95 |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 45.29 | 0.08 | 11.177 | 0.007 | 0 | 0.0 | 682064f8fb |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 17.04 | 0.02 | 53.071 | 0.229 | 0 | 0.0 | 0a51385e95 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 17.06 | 0.01 | 52.684 | 0.172 | 0 | 0.0 | 682064f8fb |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 14.61 | 0.02 | 123.200 | 0.125 | 0 | 0.0 | 0a51385e95 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 14.63 | 0.01 | 123.071 | 0.170 | 0 | 0.0 | 682064f8fb |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | head vs base | +0.2 | -0.2 | -6 | +0.16 (0.37, 3, +0.8) | -6 (2, 3, -4.3) |
| q3-4b-tp2-8u-p1024 | cpu | headoff vs baseoff | -0.4 | -0.1 | -6 | -0.31 (0.37, 3, -1.5) | -6 (7, 3, -1.4) |
| q3-4b-tp2-8u-p2048 | cpu | head vs base | +0.7 | -0.3 | -19 | +0.34 (0.21, 3, +2.8) | -19 (5, 3, -7.1) |
| q3-4b-tp2-8u-p2048 | cpu | headoff vs baseoff | +0.7 | -0.3 | -29 | +0.32 (0.15, 3, +3.8) | -29 (15, 3, -3.2) |
| q3-4b-tp2-8u-p8192 | cpu | head vs base | +0.1 | -0.7 | -387 | +0.02 (0.01, 3, +3.5) | -387 (293, 3, -2.3) |
| q3-4b-tp2-8u-p8192 | cpu | headoff vs baseoff | +0.2 | -0.1 | -129 | +0.03 (0.02, 3, +1.8) | -129 (61, 3, -3.7) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

