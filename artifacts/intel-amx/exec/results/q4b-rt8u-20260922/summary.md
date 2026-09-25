# q4b-rt8u-20260922 summary (qwen3-4b tp2, one engine, 8 or 2 users, prompt 1024..8192; base = AVX build, canon = canonical AMX build; attn = cpu or fpga)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 71.45 | 0.18 | 3.949 | 0.008 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-8u-p1024 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | canon | 3 | 79.89 | 0.20 | 3.143 | 0.013 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 124.20 | 0.62 | 3.211 | 0.026 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-8u-p1024 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | canon | 3 | 124.93 | 0.83 | 3.200 | 0.003 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 45.08 | 0.10 | 11.141 | 0.004 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-8u-p2048 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | canon | 3 | 52.73 | 0.11 | 7.259 | 0.004 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-8u-p2048 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 119.05 | 0.91 | 6.603 | 0.027 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-8u-p2048 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | canon | 3 | 120.08 | 0.54 | 6.479 | 0.013 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-8u-p4096 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 26.43 | 0.04 | 35.384 | 0.015 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-8u-p4096 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | canon | 3 | 31.31 | 0.06 | 18.599 | 0.043 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-8u-p4096 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 84.14 | 0.21 | 13.086 | 0.016 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-8u-p4096 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | canon | 3 | 85.03 | 0.53 | 12.944 | 0.013 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 14.52 | 0.03 | 123.112 | 0.106 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-8u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | canon | 3 | 17.09 | 0.02 | 53.501 | 0.229 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-8u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | base | 3 | 61.51 | 0.37 | 29.707 | 0.079 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-8u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | canon | 3 | 61.50 | 0.31 | 29.118 | 0.101 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-2u-p4096 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 2 | base | 3 | 101.57 | 0.62 | 8.944 | 0.015 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-2u-p4096 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 2 | canon | 3 | 114.16 | 0.34 | 4.692 | 0.027 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-2u-p4096 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 2 | base | 3 | 162.27 | 0.43 | 3.170 | 0.010 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-2u-p4096 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 2 | canon | 3 | 161.44 | 0.32 | 3.181 | 0.001 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-2u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 2 | base | 3 | 62.52 | 0.03 | 30.945 | 0.058 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-2u-p8192 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 2 | canon | 3 | 71.75 | 0.20 | 13.415 | 0.054 | 0 | 0.0 | c7844ca2ce |
| q3-4b-tp2-2u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 2 | base | 3 | 135.41 | 0.66 | 7.345 | 0.029 | 0 | 0.0 | eb2de0265a |
| q3-4b-tp2-2u-p8192 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 2 | canon | 3 | 136.60 | 0.50 | 7.248 | 0.017 | 0 | 0.0 | c7844ca2ce |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|
| q3-4b-tp2-8u-p1024 | cpu | canon vs base | +11.8 | -20.4 | -806 | +8.45 (0.29, 3, +49.8) | -806 (20, 3, -68.2) |
| q3-4b-tp2-8u-p1024 | fpga | canon vs base | +0.6 | -0.3 | -10 | +0.72 (0.52, 3, +2.4) | -10 (27, 3, -0.7) |
| q3-4b-tp2-8u-p2048 | cpu | canon vs base | +17.0 | -34.8 | -3882 | +7.65 (0.10, 3, +136.6) | -3882 (5, 3, -1372.8) |
| q3-4b-tp2-8u-p2048 | fpga | canon vs base | +0.9 | -1.9 | -125 | +1.04 (1.41, 3, +1.3) | -125 (16, 3, -13.3) |
| q3-4b-tp2-8u-p4096 | cpu | canon vs base | +18.5 | -47.4 | -16785 | +4.88 (0.05, 3, +165.3) | -16785 (54, 3, -534.6) |
| q3-4b-tp2-8u-p4096 | fpga | canon vs base | +1.1 | -1.1 | -141 | +0.89 (0.49, 3, +3.2) | -141 (14, 3, -17.0) |
| q3-4b-tp2-8u-p8192 | cpu | canon vs base | +17.7 | -56.5 | -69611 | +2.57 (0.05, 3, +90.9) | -69611 (129, 3, -936.0) |
| q3-4b-tp2-8u-p8192 | fpga | canon vs base | -0.0 | -2.0 | -589 | -0.01 (0.59, 3, -0.0) | -589 (129, 3, -7.9) |
| q3-4b-tp2-2u-p4096 | cpu | canon vs base | +12.4 | -47.5 | -4251 | +12.60 (0.93, 3, +23.5) | -4251 (13, 3, -567.3) |
| q3-4b-tp2-2u-p4096 | fpga | canon vs base | -0.5 | +0.3 | +11 | -0.83 (0.32, 3, -4.5) | +11 (10, 3, +1.8) |
| q3-4b-tp2-2u-p8192 | cpu | canon vs base | +14.8 | -56.6 | -17530 | +9.23 (0.22, 3, +71.8) | -17530 (66, 3, -462.9) |
| q3-4b-tp2-2u-p8192 | fpga | canon vs base | +0.9 | -1.3 | -96 | +1.19 (0.77, 3, +2.7) | -96 (12, 3, -13.4) |

Excluded rt attempts (failed or stopped): 1
- ### runtron kind=rt cell=q3-4b-tp2-8u-p1024 model=ingested-qwen-3-4b-instruct-2507-tp2 tp=2 users=8 attn=cpu prompt=1024 len=256 arm=base rep=1 attempt=1 bin=/var/tmp/jhan/tron-pre3879/gen/runtron.pre3879 tip=eb2de0265a 2026-09-22T16:36:26Z load=100.43 122.50 122.40 hugepages_free=512 bill_procs=0 bill_cpu_pct=0 marker=present

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 0

Duplicate complete records of one repetition (second and later ignored): 0

