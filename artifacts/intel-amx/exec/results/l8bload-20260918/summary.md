# l8bload-20260918: AMX gain on llama-3.1-8b against the load per engine

Cells: 2 engines placed like the nightly's socket-1 engines, U users per engine each (CI harness, prompt 1024, generate 1536, 10 rounds, capture 896-1024). off = TRON_AMX_DISABLE=1, on = unset. TPS = tokens per second per user, pooled over both engines. Gain = mean over repetitions of (on - off) / off, paired by repetition.

| users per engine | reps | off TPS | on TPS | gain | paired t | off TTFT ms | on TTFT ms | AMX-busy cycles off / on (20 s) |
|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 141.57 | 141.81 | +0.2 % | +0.5 | 834 | 792 | 0.0 G / 40.3 G |
| 4 | 3 | 122.93 | 127.69 | +3.9 % | +5.8 | 1472 | 1424 | 0.0 G / 67.8 G |
| 8 | 3 | 70.08 | 79.14 | +12.9 % | +38.7 | 2768 | 2693 | 0.0 G / 92.0 G |

Per cell (started UTC, TPS mean +/- sd over all samples, slowest sample, per-engine means, TTFT, AMX-busy cycles, machine line at start):
- 2u off rep1 (2026-09-18T19:55:06Z): TPS 140.93 +/- 0.73 (min 138.1; engines 140.8 / 141.1), TTFT 834 ms, amx_busy 0, 2.0 min; load=93.44 118.99 126.62 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 2u off rep2 (2026-09-18T20:20:02Z): TPS 141.57 +/- 0.18 (min 141.3; engines 141.6 / 141.6), TTFT 836 ms, amx_busy 0, 2.0 min; load=45.39 52.08 66.65 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 2u off rep3 (2026-09-18T20:39:10Z): TPS 141.50 +/- 0.29 (min 140.9; engines 141.5 / 141.5), TTFT 833 ms, amx_busy 0, 2.0 min; load=49.87 55.05 57.33 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 2u off rep4 (2026-09-18T21:05:01Z): TPS 142.22 +/- 0.24 (min 141.8; engines 142.0 / 142.4), TTFT 833 ms, amx_busy 0, 2.0 min; load=47.30 49.99 52.06 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 2u on rep1 (2026-09-18T19:58:03Z): TPS 142.14 +/- 0.48 (min 140.7; engines 142.0 / 142.2), TTFT 793 ms, amx_busy 40,542,524,652, 2.0 min; load=49.10 87.10 112.75 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 2u on rep2 (2026-09-18T20:17:07Z): TPS 141.59 +/- 0.25 (min 140.8; engines 141.4 / 141.7), TTFT 792 ms, amx_busy 40,083,952,524, 2.0 min; load=48.37 55.17 70.56 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 2u on rep3 EXCLUDED (Both engines slowed identically in rounds 1 to 8 (119 to 135 TPS per round, engine a and engine b within 0.3 TPS of each other). Both returned to 141 TPS in rounds 9 and 10.
TTFT was normal (807 ms).
The other 2-user cells (five before the 21:01 UTC summary of the first launch, seven with repetition 4) have per-engine means of 140.8 to 142.4 TPS and per-engine sd of 0.11 to 1.0 TPS.
The system journal for 20:41:30 to 20:45:30 UTC is saved as journal-2042-2045.txt in this cell's result directory (section 5). It shows no other user, no cron job and no kernel event. The only sudo commands are the campaign's own perf and prlimit calls.
The window also holds routine lines from the campaign itself throughout: Caddy health-check failures against the four stopped production ports every 10 s, a systemd warning about the rinzler@.service file every 10 s, and the deactivation of the two campaign fuse mounts. The only other event is a reconfiguration of tailscaled (the VPN daemon) with a DNS cache flush at 20:44:36 UTC, 10 s after round 9 began. Its relation to the slowdown is unknown.
The cause is unknown. The cell is treated as a short disturbance from outside the campaign and is replaced by repetition 4.) (2026-09-18T20:42:04Z): TPS 130.08 +/- 7.44 (min 119.0; engines 130.1 / 130.1), TTFT 807 ms, amx_busy 41,187,384,036, 2.1 min; load=47.48 52.56 55.89 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 2u on rep4 (2026-09-18T21:02:06Z): TPS 141.71 +/- 0.36 (min 141.1; engines 141.5 / 142.0), TTFT 791 ms, amx_busy 40,231,045,764, 2.0 min; load=34.57 50.05 52.61 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 4u off rep1 (2026-09-18T20:00:57Z): TPS 123.58 +/- 4.14 (min 121.4; engines 123.4 / 123.8), TTFT 1473 ms, amx_busy 0, 2.4 min; load=45.22 69.74 101.55 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 4u off rep2 (2026-09-18T20:26:14Z): TPS 122.18 +/- 3.54 (min 119.8; engines 122.9 / 121.5), TTFT 1469 ms, amx_busy 0, 2.4 min; load=48.13 50.88 61.08 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 4u off rep3 (2026-09-18T20:45:09Z): TPS 123.02 +/- 3.56 (min 121.3; engines 122.8 / 123.2), TTFT 1474 ms, amx_busy 0, 2.4 min; load=47.69 51.45 54.77 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 4u on rep1 (2026-09-18T20:04:20Z): TPS 126.79 +/- 4.31 (min 125.5; engines 126.8 / 126.8), TTFT 1426 ms, amx_busy 66,821,194,180, 2.3 min; load=48.61 60.82 91.74 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 4u on rep2 (2026-09-18T20:22:57Z): TPS 128.12 +/- 3.82 (min 126.7; engines 128.0 / 128.3), TTFT 1420 ms, amx_busy 68,380,367,324, 2.3 min; load=45.31 50.35 63.41 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 4u on rep3 (2026-09-18T20:48:31Z): TPS 128.16 +/- 4.35 (min 126.6; engines 128.5 / 127.8), TTFT 1426 ms, amx_busy 68,314,008,920, 2.3 min; load=48.52 51.51 54.07 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 8u off rep1 (2026-09-18T20:07:36Z): TPS 70.35 +/- 0.40 (min 69.6; engines 70.6 / 70.1), TTFT 2770 ms, amx_busy 0, 4.0 min; load=50.27 56.56 84.07 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 8u off rep2 (2026-09-18T20:34:11Z): TPS 69.67 +/- 0.25 (min 69.1; engines 69.8 / 69.6), TTFT 2768 ms, amx_busy 0, 4.0 min; load=49.79 53.41 57.93 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 8u off rep3 (2026-09-18T20:51:48Z): TPS 70.22 +/- 0.22 (min 69.8; engines 70.3 / 70.1), TTFT 2767 ms, amx_busy 0, 4.0 min; load=46.73 51.15 53.38 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 8u on rep1 (2026-09-18T20:12:33Z): TPS 79.53 +/- 0.37 (min 78.4; engines 79.7 / 79.3), TTFT 2693 ms, amx_busy 92,184,838,032, 3.6 min; load=48.30 55.78 76.07 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 8u on rep2 (2026-09-18T20:29:36Z): TPS 79.04 +/- 0.28 (min 78.5; engines 79.0 / 79.0), TTFT 2692 ms, amx_busy 91,902,871,156, 3.6 min; load=48.28 51.01 59.06 hugepages_free=512 bill_procs=0 bill_cpu_pct=0
- 8u on rep3 (2026-09-18T20:56:45Z): TPS 78.86 +/- 0.32 (min 78.0; engines 79.0 / 78.7), TTFT 2695 ms, amx_busy 91,900,417,164, 3.6 min; load=49.79 54.01 53.93 hugepages_free=512 bill_procs=0 bill_cpu_pct=0

Reference points (same kernel, same 28-CPU engine placement, CPU attention): runtron 2026-09-16, 8 users on one engine, 1536 generated tokens: 83.3 -> 97.5 TPS (+17 %); ci-mimic 2026-09-18, nightly layout 2 users per engine: 139.40 -> 140.53 TPS (+0.8 %, paired t 2.96 over 10 rounds).
