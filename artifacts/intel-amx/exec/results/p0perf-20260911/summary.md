| test | tp | metric | AMX-off | AMX-on | on vs off |
|---|---|---|---|---|---|
| runtron | 2 | decode TPS per user | 71.07 ± 0.13 (n=5) | 79.53 ± 0.15 (n=6) | 11.9% (per rep: +12.1%, +12.1%, +11.8%, +11.5%, +11.9%) |
| runtron | 2 | TTFT (prompt parse, s) | 3.934 ± 0.010 (n=5) | 3.128 ± 0.010 (n=6) | -20.5% |
| runtron | 4 | decode TPS per user | 95.15 ± 3.43 (n=6) | 101.63 ± 2.27 (n=6) | 6.8% (per rep: +9.5%, +6.0%, +6.0%, +9.0%, +5.3%, +5.2%) |
| runtron | 4 | TTFT (prompt parse, s) | 2.458 ± 0.008 (n=6) | 2.188 ± 0.008 (n=6) | -11.0% |
| CI harness | 2 | decode TPS per user | 48.81 ± 0.03 (n=2) | 55.61 ± 0.10 (n=2) | 13.9% (per rep: +14.1%, +13.7%) |
| CI harness | 2 | TTFT (ms) | 3052 ± 1 (n=2) | 2460 ± 6 (n=2) | -19.4% |
| CI harness | 4 | decode TPS per user | 72.76 ± 0.33 (n=2) | 82.38 ± 2.24 (n=2) | 13.2% (per rep: +15.8%, +10.7%) |
| CI harness | 4 | TTFT (ms) | 1738 ± 1 (n=2) | 1578 ± 5 (n=2) | -9.2% |

Per-run values (runtron: per-user TPS / TTFT s; CI: per-user TPS ± sd over 80 samples / TTFT ms). Runtron runs marked EARLY-STOP (one user hit a stop token early, so part of the decode ran with fewer users) are excluded from the means and the paired deltas above:
- runtron tp2 off rep1: TPS 71.049 (x8 requests, aggregate 568.4), TTFT 3.937 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T11:51:03Z load=95.99 132.62 137.05 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 off rep2: TPS 75.828 (x8 requests, aggregate 606.6), TTFT 3.928 s, generated 73-253 tokens EARLY-STOP; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T11:54:51Z load=10.09 65.92 108.82 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 off rep3: TPS 71.086 (x8 requests, aggregate 568.7), TTFT 3.944 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T11:58:40Z load=7.41 33.91 86.28 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 off rep4: TPS 71.079 (x8 requests, aggregate 568.6), TTFT 3.917 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T12:53:05Z load=0.17 12.77 28.68 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 off rep5: TPS 71.264 (x8 requests, aggregate 570.1), TTFT 3.935 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T12:56:54Z load=12.03 10.68 24.19 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 off rep6: TPS 70.894 (x8 requests, aggregate 567.2), TTFT 3.937 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T13:00:41Z load=8.33 9.05 20.52 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 on rep1: TPS 79.659 (x8 requests, aggregate 637.3), TTFT 3.122 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T11:51:48Z load=49.92 115.22 130.95 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 on rep2: TPS 79.583 (x8 requests, aggregate 636.7), TTFT 3.140 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T11:55:36Z load=7.53 57.42 103.91 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 on rep3: TPS 79.722 (x8 requests, aggregate 637.8), TTFT 3.140 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T11:59:25Z load=7.90 30.33 82.59 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 on rep4: TPS 79.439 (x8 requests, aggregate 635.5), TTFT 3.120 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T12:53:51Z load=2.52 11.44 27.39 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 on rep5: TPS 79.424 (x8 requests, aggregate 635.4), TTFT 3.119 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T12:57:39Z load=10.28 10.34 23.43 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp2 on rep6: TPS 79.328 (x8 requests, aggregate 634.6), TTFT 3.125 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T13:01:26Z load=6.35 8.41 19.76 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 off rep1: TPS 88.902 (x8 requests, aggregate 711.2), TTFT 2.469 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T11:52:32Z load=28.82 100.48 125.22 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 off rep2: TPS 97.821 (x8 requests, aggregate 782.6), TTFT 2.463 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T11:56:21Z load=7.39 50.35 99.31 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 off rep3: TPS 95.256 (x8 requests, aggregate 762.0), TTFT 2.447 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T12:00:08Z load=8.59 27.66 79.48 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 off rep4: TPS 93.917 (x8 requests, aggregate 751.3), TTFT 2.459 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T12:54:35Z load=4.14 10.70 26.46 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 off rep5: TPS 97.740 (x8 requests, aggregate 781.9), TTFT 2.460 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T12:58:25Z load=7.76 9.61 22.56 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 off rep6: TPS 97.248 (x8 requests, aggregate 778.0), TTFT 2.453 s, generated 253-253 tokens; env=TRON_AMX_DISABLE=1 prompt=1024 len=256 users=8 2026-09-11T13:02:10Z load=5.92 8.00 19.14 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 on rep1: TPS 97.380 (x8 requests, aggregate 779.0), TTFT 2.183 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T11:53:40Z load=17.59 81.80 116.90 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 on rep2: TPS 103.724 (x8 requests, aggregate 829.8), TTFT 2.195 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T11:57:32Z load=7.10 41.12 92.53 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 on rep3: TPS 100.992 (x8 requests, aggregate 807.9), TTFT 2.181 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T12:01:17Z load=7.67 23.22 74.16 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 on rep4: TPS 102.404 (x8 requests, aggregate 819.2), TTFT 2.189 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T12:55:44Z load=10.22 10.71 25.29 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 on rep5: TPS 102.946 (x8 requests, aggregate 823.6), TTFT 2.182 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T12:59:34Z load=11.35 9.83 21.66 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- runtron tp4 on rep6: TPS 102.353 (x8 requests, aggregate 818.8), TTFT 2.199 s, generated 253-253 tokens; env=TRON_AMX_DISABLE unset prompt=1024 len=256 users=8 2026-09-11T13:03:19Z load=10.63 8.54 18.49 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- CI tp2 off rep1: TPS 48.78 ± 0.31 (min 48.16, 80 samples), TTFT 3051 ms, 5.5 min, status done; load=11.05 20.70 69.56 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- CI tp2 off rep2: TPS 48.83 ± 0.30 (min 48.30, 80 samples), TTFT 3053 ms, 5.5 min, status done; load=45.64 47.66 48.85 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- CI tp2 on rep1: TPS 55.68 ± 0.29 (min 55.23, 80 samples), TTFT 2456 ms, 4.9 min, status done; load=27.49 27.60 56.30 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- CI tp2 on rep2: TPS 55.54 ± 0.36 (min 54.78, 80 samples), TTFT 2465 ms, 4.9 min, status done; load=25.70 34.64 42.38 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- CI tp4 off rep1: TPS 72.53 ± 1.36 (min 69.84, 80 samples), TTFT 1737 ms, 3.8 min, status done; load=25.23 28.42 47.71 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- CI tp4 off rep2: TPS 73.00 ± 1.24 (min 71.03, 80 samples), TTFT 1739 ms, 3.8 min, status done; load=25.78 30.81 38.17 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- CI tp4 on rep1: TPS 83.96 ± 0.94 (min 82.66, 80 samples), TTFT 1574 ms, 3.3 min, status done; load=49.65 44.30 48.91 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- CI tp4 on rep2: TPS 80.80 ± 0.81 (min 79.27, 80 samples), TTFT 1581 ms, 3.4 min, status done; load=50.00 45.18 42.03 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
