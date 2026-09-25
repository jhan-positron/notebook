# i4587-20260924 summary (base = main 996f58ec82, head = PR #4557, new = draft PR #4587; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | baseoff | 4 | 14.59 | 0.01 | 122.189 | 0.096 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headoff | 4 | 14.63 | 0.01 | 123.388 | 0.098 | 0 | 0.0 | c73e7fb2f9 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | newoff | 4 | 14.59 | 0.02 | 122.199 | 0.094 | 0 | 0.0 | 633cb88896 |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | altoff | 4 | 14.58 | 0.03 | 122.408 | 0.125 | 0 | 0.0 | c73e7fb2f9 |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p8192 | cpu | headoff vs baseoff | +0.3 | +1.0 | +1198 | +0.04 (0.02, 4, +4.9) | +1198 (88, 4, +27.3) |
| q3-4b-tp2-8u-p8192 | cpu | altoff vs newoff | -0.0 | +0.2 | +210 | -0.00 (0.02, 4, -0.2) | +210 (142, 4, +3.0) |
| q3-4b-tp2-8u-p8192 | cpu | newoff vs baseoff | +0.0 | +0.0 | +9 | +0.00 (0.01, 4, +0.1) | +9 (110, 4, +0.2) |
| q3-4b-tp2-8u-p8192 | cpu | altoff vs headoff | -0.3 | -0.8 | -979 | -0.04 (0.04, 4, -2.4) | -979 (172, 4, -11.4) |

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

