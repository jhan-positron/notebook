# pr4lazy-20261013 summary (base = main 72308ec90c, head = PR #4898 dfafd13dce, new = PR #4901 ea94e95a4e, lazy = the lazy-dotter probe ca6456b7dc; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 72.83 | 0.01 | 3.945 | 0.004 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 75.83 | 0.11 | 3.862 | 0.002 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 73.36 | 0.30 | 3.866 | 0.001 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | lazyoff | 3 | 74.81 | 0.24 | 3.866 | 0.002 | 0 | 0.0 | ca6456b7dc |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 3 | 14.57 | 0.02 | 122.841 | 0.220 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 15.37 | 0.03 | 117.274 | 0.067 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 14.96 | 0.02 | 117.861 | 0.101 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | lazyoff | 3 | 15.10 | 0.03 | 117.882 | 0.164 | 0 | 0.0 | ca6456b7dc |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | baseoff | 3 | 111.67 | 0.92 | 2.471 | 0.003 | 0 | 0.0 | 72308ec90c |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | headoff | 3 | 111.63 | 0.40 | 2.387 | 0.003 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | newoff | 3 | 111.07 | 0.08 | 2.403 | 0.007 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | lazyoff | 3 | 111.24 | 0.78 | 2.398 | 0.003 | 0 | 0.0 | ca6456b7dc |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | newoff vs baseoff | +0.7 | -2.0 | -79 | +0.52 (0.31, 3, +2.9) | -79 (4, 3, -37.4) |
| q3-4b-tp2-8u-p1024 | cpu | lazyoff vs baseoff | +2.7 | -2.0 | -78 | +1.98 (0.24, 3, +14.4) | -78 (5, 3, -26.1) |
| q3-4b-tp2-8u-p1024 | cpu | headoff vs baseoff | +4.1 | -2.1 | -83 | +2.99 (0.12, 3, +42.6) | -83 (5, 3, -28.1) |
| q3-4b-tp2-8u-p1024 | cpu | lazyoff vs newoff | +2.0 | +0.0 | +0 | +1.45 (0.49, 3, +5.2) | +0 (3, 3, +0.1) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs headoff | -3.3 | +0.1 | +4 | -2.47 (0.19, 3, -22.7) | +4 (2, 3, +4.3) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs baseoff | +2.7 | -4.1 | -4980 | +0.39 (0.03, 3, +20.1) | -4980 (227, 3, -38.1) |
| q3-4b-tp2-8u-p8192 | cpu | lazyoff vs baseoff | +3.6 | -4.0 | -4959 | +0.53 (0.03, 3, +35.0) | -4959 (127, 3, -67.5) |
| q3-4b-tp2-8u-p8192 | cpu | headoff vs baseoff | +5.5 | -4.5 | -5567 | +0.80 (0.03, 3, +42.8) | -5567 (253, 3, -38.1) |
| q3-4b-tp2-8u-p8192 | cpu | lazyoff vs newoff | +0.9 | +0.0 | +21 | +0.14 (0.05, 3, +4.4) | +21 (119, 3, +0.3) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs headoff | -2.7 | +0.5 | +587 | -0.41 (0.02, 3, -39.4) | +587 (56, 3, +18.1) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs baseoff | -0.5 | -2.7 | -68 | -0.60 (0.85, 3, -1.2) | -68 (10, 3, -12.0) |
| q3-4b-tp4-8u-p1024 | cpu | lazyoff vs baseoff | -0.4 | -2.9 | -73 | -0.43 (1.64, 3, -0.5) | -73 (1, 3, -96.4) |
| q3-4b-tp4-8u-p1024 | cpu | headoff vs baseoff | -0.0 | -3.4 | -83 | -0.04 (0.83, 3, -0.1) | -83 (6, 3, -24.2) |
| q3-4b-tp4-8u-p1024 | cpu | lazyoff vs newoff | +0.2 | -0.2 | -5 | +0.18 (0.86, 3, +0.4) | -5 (9, 3, -0.9) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs headoff | -0.5 | +0.6 | +15 | -0.56 (0.39, 3, -2.5) | +15 (5, 3, +5.5) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

