# i4587-20260924 summary (base = main 996f58ec82, head = PR #4557, new = draft PR #4587; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 4 | 14.52 | 0.03 | 122.570 | 0.244 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 4 | 14.58 | 0.03 | 123.841 | 0.369 | 0 | 0.0 | 39a6899446 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 4 | 14.56 | 0.04 | 123.820 | 0.322 | 0 | 0.0 | c73e7fb2f9 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p8192 | cpu | headoff vs baseoff | +0.4 | +1.0 | +1271 | +0.06 (0.00, 4, +26.8) | +1271 (136, 4, +18.7) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs baseoff | +0.3 | +1.0 | +1250 | +0.04 (0.03, 4, +2.4) | +1250 (104, 4, +24.0) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs headoff | -0.2 | -0.0 | -21 | -0.02 (0.04, 4, -1.3) | -21 (152, 4, -0.3) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

