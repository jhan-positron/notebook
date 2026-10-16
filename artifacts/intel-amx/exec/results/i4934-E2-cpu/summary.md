# i4934-E2-cpu summary (head = PR #4898 dfafd13dce, new = PR #4901 ea94e95a4e, fix = issue #4934 branch b87d20dd81d5d7b562e5b9eea6656de7a6c6df84; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 85.47 | 0.22 | 3.078 | 0.006 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 75.84 | 0.15 | 3.856 | 0.005 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 85.16 | 0.12 | 3.092 | 0.005 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 73.43 | 0.13 | 3.863 | 0.002 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fix | 3 | 86.12 | 0.21 | 3.077 | 0.006 | 0 | 0.0 | b87d20dd81 |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fixoff | 3 | 75.00 | 0.09 | 3.861 | 0.002 | 0 | 0.0 | b87d20dd81 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | head | 3 | 18.89 | 0.02 | 51.464 | 0.087 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 3 | 15.42 | 0.01 | 117.381 | 0.139 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | new | 3 | 18.95 | 0.04 | 51.619 | 0.094 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 3 | 14.94 | 0.03 | 117.769 | 0.160 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fix | 3 | 19.02 | 0.02 | 51.547 | 0.057 | 0 | 0.0 | b87d20dd81 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | fixoff | 3 | 15.30 | 0.08 | 117.609 | 0.292 | 0 | 0.0 | b87d20dd81 |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | head | 3 | 122.19 | 0.18 | 2.127 | 0.003 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | headoff | 3 | 111.18 | 1.14 | 2.396 | 0.013 | 0 | 0.0 | dfafd13dce |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | new | 3 | 120.83 | 0.74 | 2.133 | 0.002 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | newoff | 3 | 110.95 | 0.29 | 2.414 | 0.018 | 0 | 0.0 | ea94e95a4e |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | fix | 3 | 122.36 | 0.60 | 2.119 | 0.005 | 0 | 0.0 | b87d20dd81 |
| q3-4b-tp4-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp4 | 4 | 8 | fixoff | 3 | 111.64 | 0.08 | 2.404 | 0.003 | 0 | 0.0 | b87d20dd81 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | fixoff vs headoff | -1.1 | +0.1 | +5 | -0.84 (0.18, 3, -8.0) | +5 (5, 3, +1.8) |
| q3-4b-tp2-8u-p1024 | cpu | fixoff vs newoff | +2.1 | -0.0 | -2 | +1.56 (0.05, 3, +59.2) | -2 (3, 3, -1.1) |
| q3-4b-tp2-8u-p1024 | cpu | fix vs new | +1.1 | -0.5 | -14 | +0.96 (0.22, 3, +7.6) | -14 (3, 3, -8.9) |
| q3-4b-tp2-8u-p1024 | cpu | fix vs head | +0.8 | -0.0 | -1 | +0.65 (0.14, 3, +8.0) | -1 (5, 3, -0.3) |
| q3-4b-tp2-8u-p1024 | cpu | newoff vs headoff | -3.2 | +0.2 | +7 | -2.40 (0.19, 3, -21.4) | +7 (2, 3, +4.9) |
| q3-4b-tp2-8u-p1024 | cpu | new vs head | -0.4 | +0.4 | +13 | -0.31 (0.29, 3, -1.9) | +13 (2, 3, +10.4) |
| q3-4b-tp2-8u-p8192 | cpu | fixoff vs headoff | -0.8 | +0.2 | +228 | -0.12 (0.08, 3, -2.7) | +228 (155, 3, +2.5) |
| q3-4b-tp2-8u-p8192 | cpu | fixoff vs newoff | +2.4 | -0.1 | -160 | +0.36 (0.05, 3, +12.3) | -160 (205, 3, -1.4) |
| q3-4b-tp2-8u-p8192 | cpu | fix vs new | +0.3 | -0.1 | -72 | +0.06 (0.03, 3, +3.2) | -72 (37, 3, -3.4) |
| q3-4b-tp2-8u-p8192 | cpu | fix vs head | +0.7 | +0.2 | +83 | +0.13 (0.01, 3, +21.5) | +83 (134, 3, +1.1) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs headoff | -3.1 | +0.3 | +388 | -0.48 (0.03, 3, -32.9) | +388 (129, 3, +5.2) |
| q3-4b-tp2-8u-p8192 | cpu | new vs head | +0.3 | +0.3 | +155 | +0.06 (0.02, 3, +4.4) | +155 (167, 3, +1.6) |
| q3-4b-tp4-8u-p1024 | cpu | fixoff vs headoff | +0.4 | +0.3 | +8 | +0.46 (1.13, 3, +0.7) | +8 (12, 3, +1.1) |
| q3-4b-tp4-8u-p1024 | cpu | fixoff vs newoff | +0.6 | -0.4 | -10 | +0.68 (0.22, 3, +5.5) | -10 (20, 3, -0.8) |
| q3-4b-tp4-8u-p1024 | cpu | fix vs new | +1.3 | -0.7 | -14 | +1.53 (1.25, 3, +2.1) | -14 (7, 3, -3.7) |
| q3-4b-tp4-8u-p1024 | cpu | fix vs head | +0.1 | -0.3 | -7 | +0.17 (0.74, 3, +0.4) | -7 (2, 3, -6.2) |
| q3-4b-tp4-8u-p1024 | cpu | newoff vs headoff | -0.2 | +0.7 | +18 | -0.22 (1.26, 3, -0.3) | +18 (29, 3, +1.1) |
| q3-4b-tp4-8u-p1024 | cpu | new vs head | -1.1 | +0.3 | +7 | -1.37 (0.76, 3, -3.1) | +7 (5, 3, +2.4) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

