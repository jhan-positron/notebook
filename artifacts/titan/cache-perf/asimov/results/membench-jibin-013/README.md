# cache-mem-perf on the Asimov emulator: run membench-jibin-013 (the rehearsal for run 8, the mesh latency map)

Jibin Han's `cache-mem-perf` (github.com/jhan-positron/asimov, folder `cache-mem-perf`, commit `3b12e4f8a8c7414d14fb06b356c5a79e3e6c0a1e`) ran the rehearsal he asked for before run 8's full run: his one `meshmap` command on CPU 2, on one emulated Asimov hemisphere on the GA13 Palladium, on 2026-11-12 (UTC). His three files are in `results/bootM0/`, byte for byte as his program wrote them, with the kernel log as `dmesg.txt` and `SHA256SUMS` over all of them. This box checked that the files are whole. It did not analyse the numbers.

## Read first

- **His command ran whole.** Exit status 0, `# meshmap: done cells=20/20`, `# mesh counters: level=1`, `# classify: probed=320 ambiguous=1 unused=0 per_node=64,64,64,64,64 lines=64`, `# one_2mib_page: yes (backing=hugetlb)`, `# pagemap: pfn=0xc004800 page_bytes=4096 covers=buffer`, `# read_floor: 7 6 5 12 10`, and the first 32 `# probe` lines.
- **How it was run.** The init can run only `/bin/sh <script> --out <folder>`, so the box's wrapper `box_map_rehearsal.sh` changed into `results/bootM0`, waited 20 ms and ran `/opt/membench/cache-mem-perf-3b12e4f/meshmap --cpus 2 --lines 64 --reps 1 --out map-rehearsal.csv --homes map-rehearsal-homes.txt > map-rehearsal-log.txt 2>&1`, as root on CPU 2 under SCHED_FIFO 10, as every earlier run. The wrapper printed nothing until both of its commands had ended, so no console output of the box's falls into his counter windows.
- **The box ran a second command after his, its own.** The same command with `--last-cpus 0`, which is what his `--kernel-cpus` adds to the full run, to try CPU 0 where a failure costs least. Its files are `map-rehearsal-cpu0.csv`, `map-rehearsal-cpu0-homes.txt` and `map-rehearsal-cpu0-log.txt`. It ran whole too: exit status 0, `# meshmap: done cells=40/40`, level 1. His three files were complete before it started. The wrapper's one line of output: `# box rehearsal: his command exit 0; with --last-cpus 0 exit 0`.
- **CPU 0's rows are not in the cache state of the CPU 2 rows.** CPU 0's cluster has its L3 in use and its data prefetchers on: the SCP stages the full-L3 mode for the cluster of CPUs 0-1 on every build, and the hook of TF-A 0.35.0-pfoff.1 that turns the prefetchers off covers CPUs 2-9 only. The second file shows it: `l1d_refill_hwprf` or `l2d_refill_hwprf` is nonzero in all 20 of its CPU 0 cell rows and both read 0.0000 in all 40 CPU 2 cell rows of the two files, and `l3d_refill_rd` reads 0.27 to 0.47 in the five CPU 0 `ocm-flush` rows where the CPU 2 rows read 1.00 to 1.05. This holds with all three firmware pairs of the full run, so CPU 0's cells match the other CPUs' state only on his boot 3 (L3 on, prefetchers on). No register readback stands behind CPU 0's state: the hook prints for CPUs 2-9 only.
- **More on CPU 0.** Its cluster's mesh port (node 80, crosspoint (1,2)) is 1, 3, 3, 5 and 5 steps from home nodes 88, 160, 216, 288 and 344, the mirror image of the port of CPUs 8-9 (node 336, crosspoint (5,2): 5, 5, 3, 3 and 1). CPU 0 is the kernel's CPU: it is not isolated, keeps the 100 Hz timer tick, shares the device interrupts with CPU 1 (`irqaffinity=0-1`), and executes every mesh counter read (the mesh PMU's CPU is 0). So a read made from CPU 0 is local, while the read floor was measured from CPU 2. With `--last-cpus 0` the program also pins itself to CPU 0 once at its start, for its pin test, before any row is written.
- **The mesh counters on this kernel.** A read of an event group stops the whole mesh PMU, reads every event and restarts it (Linux 6.18.36, `kernel/events/core.c` and `drivers/perf/arm-cmn.c`: his levels 1 and 2). A read of an event opened alone (level 3) does not stop it. The mesh events count per home node, so the mesh columns of every row also hold the requests of the kernel's CPUs 0-1.
- **CPU 3 was online and idle during every row.** His earlier OCM rows from CPU 2 (the G2 rows of `run_followup.sh`, for example) were taken with CPU 3 offline.
- **The full run follows without waiting for his look at these files** (the user's decision): `sh run_map.sh --kernel-cpus` on the same commit, his boots 1, 2 and 3 back to back, each checked by the box before the next is queued. At this rehearsal's probe time (`# classify: probe_ns=11545`) his `lines_for_budget` keeps 2,048 lines per cell in the full run: with the 1 s budget its limit is 78,125 ns per probe.

## Platform

- **Image:** GA13 release `a10280100`, build `hemi_rtws_tlm` (RTL `0d9e214eb43b`), from this box's own copy. The DRAM is the emulator's embedded memory model, not LPDDR5X, so no DRAM number here is silicon-like.
- **Firmware:** SCP 0.48.0-nopcie.1 (`e361a83`, debug; its banner is `uart_0.log` lines 2 and 13) with TF-A 0.35.0-pfoff.1 (`5a9e2a8`, debug; `uart_1.log` line 2), the firmware of his round four boot B. The clusters of CPUs 2-9 have their L3 out of use as a cache, and the data prefetchers of CPUs 2-9 and their CMEs are off.
- **BL31's readbacks** (the AP console `uart_1.log`, lines 104-111, one line per CPU 2-9 at its power-on; nothing took a CPU offline, so there is no later line):
  - CPU 2: `pfoff cpu2 ectlr 0x900000->0x1000000900000 cmpx 0x340000009400 cmecfg 0x2a9f11115->0x2b9f11115 clusterpwrctlr 0xb40170 clusterpwrstat 0x0`
  - CPU 8: `pfoff cpu8 ectlr 0x900000->0x1000000900000 cmpx 0x340000009400 cmecfg 0x2a9f11115->0x2b9f11115 clusterpwrctlr 0xb40170 clusterpwrstat 0x0`
  - IMP_CPUECTLR_EL1 bit 48 went from 0 to 1 on all eight CPUs. IMP_CMECFG_EL1 bit 28 was set at each cluster's first core (CPUs 2, 4, 6, 8) and read already set at its second (CPUs 3, 5, 7, 9: `0x2b9f11115->0x2b9f11115`). IMP_CLUSTERPWRSTAT_EL1 read 0x0 in all eight lines.
- **Kernel:** this box's Linux 6.18.36 (transparent huge pages, hugetlbfs, debugfs, `CONFIG_PROC_PAGE_MONITOR=y`), command line `earlycon=pl011,0x2a400000 quiet nohz_full=2-9 isolcpus=domain,managed_irq,2-9 irqaffinity=0-1 earlycon=pl011,0x2a400000 console=ttyAMA0,480000 panic=0 loglevel=7 rdinit=/sbin/membench-init`. The kernel runs on CPUs 0-1; CPUs 2-9 are online and isolated. 256 huge pages of 2 MiB were reserved. `/dev/ocm` maps the OCM in 4 KiB pages: `dmesg.txt` has 10 map lines, five regions for each of the two `meshmap` processes.
- **The run:** queue request 5292 on ga13pd01. The wrapper took 0.211 chip seconds in all (`MB RUN end status=exit:0 ns=211320072`); his command reports `cells 20/20 in 0.0961 s` and the second `cells 40/40 in 0.0853 s`. The hang guard of 12 chip seconds did not fire. The emulator ran 2,781 wall seconds per chip second.
- **Evidence in the box:** `evidence/runs/membench-jibin-013/` (console logs, the launcher's events, the results window).

## Files

| File | Bytes | What |
|---|---|---|
| `results/bootM0/map-rehearsal.csv` | 5,441 | his command's rows and `#` lines |
| `results/bootM0/map-rehearsal-homes.txt` | 422 | his command's classification record |
| `results/bootM0/map-rehearsal-log.txt` | 402 | his command's stdout and stderr |
| `results/bootM0/map-rehearsal-cpu0.csv` | 8,474 | the box's second command: the same with `--last-cpus 0` |
| `results/bootM0/map-rehearsal-cpu0-homes.txt` | 422 | its classification record (equal to his command's: the same physical page) |
| `results/bootM0/map-rehearsal-cpu0-log.txt` | 440 | its stdout and stderr |
| `dmesg.txt` | 16,655 | the kernel log, read after the wrapper ended |
| `SHA256SUMS` | 705 | sha256 of the seven files above |
