# i4934-E-cpu summary (head = PR #4898 dfafd13dce, new = PR #4901 ea94e95a4e, fix = issue #4934 branch c30a86f252195d8be2a8b0edfa93bf2a97f44470; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 85.09 | 0.43 | 3.080 | 0.005 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 75.78 | 0.42 | 3.858 | 0.003 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 85.23 | 0.17 | 3.090 | 0.001 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 73.37 | 0.15 | 3.867 | 0.002 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fix | 3 | 85.72 | 0.20 | 3.079 | 0.003 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fixoff | 3 | 74.49 | 0.17 | 3.858 | 0.003 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 18.91 | 0.02 | 51.341 | 0.155 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 15.38 | 0.02 | 117.223 | 0.151 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 18.99 | 0.01 | 51.451 | 0.126 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 14.93 | 0.04 | 117.699 | 0.098 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fix | 3 | 18.98 | 0.03 | 51.463 | 0.326 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fixoff | 3 | 15.15 | 0.03 | 117.314 | 0.088 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | head | 3 | 122.12 | 0.44 | 2.124 | 0.004 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | headoff | 3 | 111.97 | 0.10 | 2.392 | 0.003 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | new | 3 | 120.36 | 0.36 | 2.136 | 0.003 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | newoff | 3 | 110.97 | 0.07 | 2.407 | 0.003 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | fix | 3 | 121.88 | 0.95 | 2.126 | 0.005 | 0 | 0.0 | c30a86f252 |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | fixoff | 3 | 111.54 | 0.50 | 2.404 | 0.005 | 0 | 0.0 | c30a86f252 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | fixoff vs headoff | -1.7 | -0.0 | -0 | -1.29 (0.40, 3, -5.5) | -0 (4, 3, -0.0) |
| q3-4b-tp2-8u-p1024 | cpu | fixoff vs newoff | +1.5 | -0.2 | -9 | +1.13 (0.13, 3, +14.7) | -9 (2, 3, -9.4) |
| q3-4b-tp2-8u-p1024 | cpu | fix vs new | +0.6 | -0.4 | -11 | +0.49 (0.07, 3, +12.5) | -11 (4, 3, -4.5) |
| q3-4b-tp2-8u-p1024 | cpu | fix vs head | +0.7 | -0.0 | -1 | +0.63 (0.51, 3, +2.1) | -1 (4, 3, -0.3) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs headoff | -3.2 | +0.2 | +9 | -2.41 (0.29, 3, -14.5) | +9 (5, 3, +3.1) |
| q3-4b-tp2-8u-p1024 | cpu | new vs head | +0.2 | +0.3 | +11 | +0.14 (0.45, 3, +0.5) | +11 (5, 3, +3.7) |
| q3-4b-tp2-8u-p8192 | cpu | fixoff vs headoff | -1.5 | +0.1 | +92 | -0.23 (0.05, 3, -8.0) | +92 (219, 3, +0.7) |
| q3-4b-tp2-8u-p8192 | cpu | fixoff vs newoff | +1.5 | -0.3 | -385 | +0.22 (0.03, 3, +13.0) | -385 (186, 3, -3.6) |
| q3-4b-tp2-8u-p8192 | cpu | fix vs new | -0.1 | +0.0 | +12 | -0.02 (0.02, 3, -1.3) | +12 (362, 3, +0.1) |
| q3-4b-tp2-8u-p8192 | cpu | fix vs head | +0.3 | +0.2 | +122 | +0.06 (0.04, 3, +2.6) | +122 (296, 3, +0.7) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs headoff | -2.9 | +0.4 | +477 | -0.45 (0.06, 3, -12.7) | +477 (136, 3, +6.1) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | +0.4 | +0.2 | +110 | +0.08 (0.02, 3, +5.9) | +110 (81, 3, +2.4) |
| q3-4b-tp4-8u-p1024 | cpu | fixoff vs headoff | -0.4 | +0.5 | +12 | -0.43 (0.40, 3, -1.9) | +12 (4, 3, +5.2) |
| q3-4b-tp4-8u-p1024 | cpu | fixoff vs newoff | +0.5 | -0.1 | -3 | +0.57 (0.53, 3, +1.9) | -3 (6, 3, -0.8) |
| q3-4b-tp4-8u-p1024 | cpu | fix vs new | +1.3 | -0.5 | -10 | +1.52 (0.74, 3, +3.5) | -10 (7, 3, -2.5) |
| q3-4b-tp4-8u-p1024 | cpu | fix vs head | -0.2 | +0.1 | +2 | -0.24 (1.21, 3, -0.3) | +2 (5, 3, +0.6) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs headoff | -0.9 | +0.6 | +15 | -1.00 (0.14, 3, -12.1) | +15 (6, 3, +4.2) |
| q3-4b-tp4-8u-p1024 | cpu | new vs head | -1.4 | +0.5 | +12 | -1.76 (0.79, 3, -3.9) | +12 (3, 3, +6.4) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

