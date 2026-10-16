# pr4lazy-20261013 summary (base = main 72308ec90c, head = PR #4898 dfafd13dce, new = PR #4901 ea94e95a4e, lazy = the lazy-dotter probe ca6456b7dc; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 84.89 | 0.21 | 3.125 | 0.005 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 72.98 | 0.26 | 3.901 | 0.002 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 85.17 | 0.25 | 3.117 | 0.003 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 75.80 | 0.47 | 3.890 | 0.005 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | lazy | 3 | 84.83 | 0.10 | 3.125 | 0.006 | 0 | 0.0 | ca6456b7dc |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | lazyoff | 3 | 74.65 | 0.08 | 3.905 | 0.005 | 0 | 0.0 | ca6456b7dc |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 18.96 | 0.03 | 51.858 | 0.146 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 14.99 | 0.02 | 117.919 | 0.087 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 18.90 | 0.01 | 51.681 | 0.190 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 15.47 | 0.01 | 117.398 | 0.092 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | lazy | 3 | 18.98 | 0.01 | 51.855 | 0.070 | 0 | 0.0 | ca6456b7dc |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | lazyoff | 3 | 15.23 | 0.03 | 118.019 | 0.088 | 0 | 0.0 | ca6456b7dc |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | new | 3 | 119.76 | 0.50 | 2.148 | 0.003 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | newoff | 3 | 109.97 | 0.58 | 2.430 | 0.036 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | head | 3 | 121.32 | 0.30 | 2.136 | 0.002 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | headoff | 3 | 111.32 | 0.03 | 2.399 | 0.009 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | lazy | 3 | 120.17 | 0.69 | 2.144 | 0.009 | 0 | 0.0 | ca6456b7dc |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | lazyoff | 3 | 110.17 | 0.74 | 2.411 | 0.013 | 0 | 0.0 | ca6456b7dc |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | lazyoff vs newoff | +2.3 | +0.1 | +4 | +1.66 (0.34, 3, +8.5) | +4 (3, 3, +2.0) |
| q3-4b-tp2-8u-p1024 | cpu | lazyoff vs headoff | -1.5 | +0.4 | +14 | -1.16 (0.53, 3, -3.8) | +14 (3, 3, +8.1) |
| q3-4b-tp2-8u-p1024 | cpu | lazy vs new | -0.1 | +0.0 | +0 | -0.06 (0.29, 3, -0.4) | +0 (1, 3, +0.0) |
| q3-4b-tp2-8u-p1024 | cpu | lazy vs head | -0.4 | +0.2 | +7 | -0.34 (0.31, 3, -1.9) | +7 (3, 3, +4.3) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs headoff | -3.7 | +0.3 | +10 | -2.82 (0.30, 3, -16.5) | +10 (5, 3, +3.7) |
| q3-4b-tp2-8u-p8192 | cpu | lazyoff vs newoff | +1.6 | +0.1 | +100 | +0.24 (0.02, 3, +19.2) | +100 (81, 3, +2.1) |
| q3-4b-tp2-8u-p8192 | cpu | lazyoff vs headoff | -1.5 | +0.5 | +621 | -0.24 (0.02, 3, -19.5) | +621 (143, 3, +7.5) |
| q3-4b-tp2-8u-p8192 | cpu | lazy vs new | +0.1 | -0.0 | -3 | +0.02 (0.03, 3, +1.1) | -3 (141, 3, -0.0) |
| q3-4b-tp2-8u-p8192 | cpu | lazy vs head | +0.4 | +0.3 | +174 | +0.08 (0.01, 3, +9.5) | +174 (246, 3, +1.2) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs headoff | -3.1 | +0.4 | +521 | -0.48 (0.02, 3, -45.2) | +521 (176, 3, +5.1) |
| q3-4b-tp4-8u-p1024 | cpu | lazyoff vs newoff | +0.2 | -0.8 | -19 | +0.20 (0.23, 3, +1.5) | -19 (23, 3, -1.4) |
| q3-4b-tp4-8u-p1024 | cpu | lazyoff vs headoff | -1.0 | +0.5 | +11 | -1.15 (0.71, 3, -2.8) | +11 (17, 3, +1.1) |
| q3-4b-tp4-8u-p1024 | cpu | lazy vs new | +0.3 | -0.2 | -3 | +0.41 (0.39, 3, +1.8) | -3 (9, 3, -0.7) |
| q3-4b-tp4-8u-p1024 | cpu | lazy vs head | -1.0 | +0.4 | +8 | -1.15 (0.98, 3, -2.0) | +8 (8, 3, +1.9) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs headoff | -1.2 | +1.3 | +31 | -1.35 (0.55, 3, -4.2) | +31 (38, 3, +1.4) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

