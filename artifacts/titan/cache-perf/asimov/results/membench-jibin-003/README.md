# cache-mem-perf on the Asimov emulator: run membench-jibin-003 (control for round two)

Jibin Han's round-two `cache-mem-perf` (commit `8ae533c916fb729a18058660e0a288443ecb1dfa`) ran a second time on the GA13 Palladium, from 2026-11-02 to 2026-11-03, on round one's firmware, as a control for round two (`../membench-jibin-002/`). His whole results directory is `results/19700101T000000Z/`, byte for byte as his script wrote it; `SHA256SUMS` lists each file's sha256. The run's evidence is `evidence/runs/membench-jibin-003/` in the emuMemBenchBox sandbox. Round two's README has the platform facts and the notes for reading his numbers; this one covers what the control shows.

## Result: the firmware made round two's writes faster

On round one's firmware, his round-two code hits round one's write limit again, within 0.4%. So round two's faster multi-core DRAM writes came from the newer firmware, not from his code changes or the kernel.

## What this run is

- **The same program and platform as round two, on round one's firmware.** The same binaries (`latency` 78b5b55a…, `bandwidth` e850315a…, `cmncount` bb0d30be…), kernel (Linux 6.18.36 with transparent huge pages, hugetlbfs and debugfs), init, `/dev/ocm` module, 256 huge pages and CPU layout as round two. Only the firmware differs: round one's SCP `scp-v0.34.0` (`45b053c`, release) and TF-A `tfa-v0.24.0` (`cc13f8c`, debug), in place of round two's SCP 0.48.0 (this box's build with PCIe0 held, debug) and TF-A 0.35.0 (debug). The SAM profiles (`bootloader-no-sam`, `cold-boot-ocm-w4`) are the same in both.
- **Linux saw the same platform.** This run's `sysinfo.txt` equals round two's apart from the free memory and five kernel-log timestamps: the same CPUs, caches, kernel config, memory map, mesh PMU and events, and mesh map.

## The run

- Queue request 4519 on ga13pd01 (boards 12-15), granted 23:19:41 UTC on 2026-11-02. The init started at 23:43:56 UTC, between 0.43 and 0.44 s of chip time after the swap-in (the kernel's own clock read 0.210 s). His script ran from 23:44:22 to 00:59:07 UTC, and the emulator was released at 00:59:52 UTC on 2026-11-03.
- It exited 0 after 1.610 s of chip time (`MB RUN end status=exit:0 ns=1610013380`). All 63 of his commands exited 0, and all 57 of his files came back intact (`MB WIN ok ... files=60 trunc=0`, with this box's `init.log`, `out.txt` and `dmesg.txt`).
- The run's checker passed every criterion, the same criteria as round two's (`JIBIN_CHECK PASS`, `evidence/runs/membench-jibin-003/judge-jibin.txt`).
- The emulator ran 2,785 wall seconds per chip second.

## Writes on the two firmware sets

The four `--kernel all` write rows (best of three) and his writer-placement rows (16 MiB per writer, best of two), in GB/s:

| Command | Round one (old firmware, his round-one code) | This run (old firmware) | Round two (new firmware) |
|---|---|---|---|
| 4 threads on CPUs 2,4,6,8, 2 MiB each | 88.80 | 88.78 | 127.93 |
| 8 threads on CPUs 2-9, 2 MiB each | 88.25 | 88.61 | 155.39 |
| 4 threads on CPUs 2,4,6,8, 16 MiB each | 86.78 | 86.81 | 127.98 |
| 8 threads on CPUs 2-9, 16 MiB each | 86.75 | 86.66 | 151.69 |
| writers on CPUs 2+4 | - | 63.98 | 63.98 |
| writers on CPUs 2+8 | - | 63.98 | 63.98 |
| writers on CPUs 2+3 (one cluster) | - | 40.94 | 40.92 |
| writers on CPUs 2+4+6+8 (one per cluster) | - | 86.60 | 127.97 |
| writers on CPUs 2+3+4+5 (two clusters) | - | 85.86 | 85.84 |
| writers on CPUs 2+3+8+9 (two clusters) | - | 84.16 | 84.11 |

- **On the old firmware the limit is shared across the hemisphere,** about 87-89 GB/s. Four writers, one per cluster, get 21.6-22.4 GB/s each, and eight writers 10.8-11.2 GB/s each, well under one core's 32.0 GB/s.
- **On both firmware sets, two writers that share a cluster get about 41-43 GB/s between them.** Two writers on different clusters each write at the full 32.0 GB/s. Only the placements that need more than about 87 GB/s and spread over all four clusters (2+4+6+8, and the 4- and 8-thread rows) differ between the firmware sets. The other placement rows agree within 0.1%.
- **What this run does not separate.** Of the newer firmware's changes, the route overrides from the home nodes to the memory controllers are the likely cause. The other mesh change, the POCQ cap, applies to traffic the cores don't send. This run changes the whole firmware set at once, so it cannot rule out the rest of the newer SCP, TF-A 0.35.0, or the debug build round two loaded.

## Mesh counts on the limited row

- **On the old firmware, the 2+4+6+8 row put about 829,000 extra requests on one home node.** Node 344, OCM4's home at crosspoint (5,3), received 2,105,333 requests, against 1,275,875-1,277,589 at each of the other four. On round two's firmware all five read 1,276,581-1,278,473. No other write row shows this on either firmware: each spreads evenly, within 0.2%.
- **The extra requests brought no extra memory requests or misses.** `hns_mc_reqs_local_all` read 5,621,097 against round two's 5,625,931, and `hns_cache_miss_all` 5,604,936 against 5,608,583. So they look like the same writes received more than once, as retried requests would be. This PMU's `hns_pocq_retry_all`, counted per node, would show whether they are.

## Everything else repeats

- **Against round two (same code, other firmware):** apart from the multi-core write rows above, every best row of the 63 commands agrees within 1.9%, except the per-region OCM latency rows. The all-five OCM rows agree within 0.14 ns, and the 2 MiB DRAM (SLC) rows within 0.35 ns.
- **The per-region OCM rows move by up to 3.05 ns (12.4%)** between the two runs, as their two passes already did within round two. The pattern by mesh distance repeats: they average 19.24, 22.86 and 25.26 ns at 1, 3 and 5 crosspoints (round two: 19.64, 21.82 and 24.58), and each CPU's fastest region is again one at 1 crosspoint. Their passes again count 1.11-1.42 L2 refills and 0.77-0.96 L3 read refills per load.
- **Against round one (same firmware, his code and the kernel changed):** the 69 best rows of the 22 commands both ran with the same arguments agree within 1.44%. The one exception is the 4 MiB fresh chain: 29.76 ns in round one, 28.40 here and 28.70 in round two. That is the one size just over the 3.75 MiB of SLC that caches DRAM.
