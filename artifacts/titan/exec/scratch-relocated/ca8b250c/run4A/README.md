# cache-mem-perf on the Asimov emulator: run membench-jibin-005 (round four, boot A)

Jibin Han's `cache-mem-perf` (github.com/jhan-positron/asimov, folder `cache-mem-perf`, commit `e8e4580e8472c3902f5f9cbbec0031574500c6f0`) ran his follow-up script once, as boot A of his round four (the run 3 platform), on one emulated Asimov hemisphere on the GA13 Palladium on 2026-11-04 (UTC). His whole results directory is `results/bootA/`, byte for byte as his script wrote it. `dmesg.txt` beside it is the kernel log from the same boot, which carries one `/dev/ocm` line per mapping. `SHA256SUMS` lists each file's sha256. The run's evidence is `evidence/runs/membench-jibin-005/` in the emuMemBenchBox sandbox.

## Read first

- **The platform is run 3's.** Same image copy, firmware (SCP 0.48.0-nopcie.1, TF-A 0.35.0 debug), kernel, CPU layout and huge pages. This boot's snapshot differs from run 3's only in his programs, this box's init (it names the results folder `bootA`) and the `/dev/ocm` module, which now writes one kernel-log line per mapping at debug level, never to the console; its mapping code is unchanged (`evidence/bundle/membench-jibin-e8e4580-fw19-checks.txt`).
- **Both controls repeat run 3** (his criterion G-e: within 0.5% of 2.0 and 21.00 ns). The 4 KiB repeated chase in `latency-dram-small.csv` reads 2.002 ns best (reps 2.002-2.003; run 3: 2.002). The `cme-roundtrip` best reads 21.004-21.005 ns in all 21 files that carry it (run 3: 21.004-21.006).
- **His script ran whole:** 2.830 s of chip time against his 3.0 s estimate, 105 commands, all exit 0 (`# run_followup.sh done ...: 0 measurement command(s) failed`), all 103 files back.
- **His program flagged no counter row:** no `# perf:` line in any file. As in run 3, this kernel opens any raw event number but CHAIN (0x1E), so an event opening does not show that it counts; only its counts do.
- **Nothing was added to his script on this boot.** It ran from his commit as sent.

## The run

- Queue request 4666 on ga13pd01, granted 18:58:40 UTC. The init started at 19:35:46 UTC, his script ran from 19:36:09 to 21:46:55 UTC, and the emulator was released at 21:48:11 UTC. The emulator ran 2,778 wall seconds per chip second by its own 10 ms ticks (run 3: 2,776).
- This box's init (PID 1) ran `/bin/sh /opt/membench/cache-mem-perf-e8e4580/run_followup.sh --out /opt/membench/cache-mem-perf-e8e4580/results/bootA` as root, pinned to CPU 2 under SCHED_FIFO priority 10, with RT throttling off, as in run 3. It exited 0 after 2.830 s (`MB RUN end status=exit:0 ns=2829791989`). The 12 s hang guard did not fire.
- His script took CPU 3 offline before G1 and brought it back at the end (`cpu3 online=0`, `cpu3 online=1` in `log.txt`).
- Build: his Makefile with the asimov-os `v0.0.17` SDK's GCC (Arm GNU Toolchain 14.2.Rel1, 14.2.1) and his default flags, all static. `latency` sha256 `ce19c59594b1fc8bc86a58820c500540e1a58714f3485f08fd97365ea953f3e3`, `bandwidth` `1c25ab2ac309c4b1d8ee5d3e40a25e8936a0afa99325ca3a5be172024439f0a5`, `bandwidth_r2` `2570e5ba9f604fc3a14550341c48ad34857458787345090e18e969d7d7dfa6c6`, `cmncount` `bb0d30be9499053cbe4a78f0fab49018b6abeda9de0d7c6574ba8575f3a53d41` (run 3's). `bandwidth` has run 3's machine code and `bandwidth_r2` run 2's (`objdump -d` identical); `latency` is new.
- The run's checker passed every criterion (`JIBIN_CHECK PASS`, `evidence/runs/membench-jibin-005/judge-jibin.txt`): firmware banners, kernel, CPU layout, huge pages and `/dev/ocm` as qualified; `ocm=1 sme2=1 hugepages_free=256`; all 103 expected files; CPU 3 offline and back; no `# perf:` line; the mesh map in `sysinfo.txt`; `cmn-counts.csv` with 20 counted commands of 8 events each; one mapping line for each of the 110 OCM mappings; nothing on stderr.

## OCM mappings

`dmesg.txt` has one line per `/dev/ocm` mapping, 110 in all, in the form `membench_ocm: map pid=194 va=0xffffafd09000 pa=0xe0000000 len=0x40000 prot=0x68000000000fc3`. Each line carries the kernel-log time and the mapping process's pid.

- Every mapping is one whole 256 KiB region at its base: 22 each at 0xE0000000, 0xE0100000, 0xE0200000, 0xE0300000 and 0xE0400000.
- Every mapping has the same attributes, `prot=0x68000000000fc3`: Normal write-back memory (attribute index 0), inner shareable, user read-write, never executable, 4 KiB pages, no contiguous bit.
- The user address is placed by the kernel per mapping, so its offset from the physical address varies: `va - pa` is a multiple of 16 KiB on 23 of the 110 mappings, of 32 KiB on 8 and of 64 KiB on 5. A TLB entry that merges neighbouring 4 KiB pages can only form where the two addresses share that alignment.

## Platform facts

These equal run 3's (its README, Platform facts); this boot's `sysinfo.txt` and `dmesg.txt` read the same.

- **Emulator image:** GA13 release `a10280100`, build `hemi_rtws_tlm`, RTL `0d9e214eb43b` (main, 2026-10-28), from this box's private copy. Real C1-Nano cores and clusters with their CMEs, the CMN-S3 mesh with its SLC and OCM; the matmul array is cut to one column.
- **Firmware:** SCP 0.48.0-nopcie.1 (`e361a83`, debug build) and TF-A 0.35.0 (`3b3df18`, debug).
- **Kernel:** Linux 6.18.36 built from asimov-os `v0.0.17`'s config and patches plus transparent huge pages (madvise), hugetlbfs and debugfs; command line in `sysinfo.txt`.
- **CPU placement:** ten C1-Nano cores, all online at boot; CPUs 2-9 isolated from the scheduler and `nohz_full`, device interrupts on CPUs 0-1. Each pair {2,3}, {4,5}, {6,7}, {8,9} shares an L2, an L3, a CME and one mesh port.
- **Clock:** core 2.000 GHz against the 1 GHz generic timer: 4.01 cycles per 2.002 ns load on the 4 KiB control.
- **Caches:** L1 data and instruction 32 KiB per core, L2 128 KiB and L3 256 KiB per two-core cluster, 64-byte lines. The SLC is five home nodes of 1 MiB; the firmware locks 4 of 16 ways of each as OCM.
- **OCM:** five regions of 256 KiB at 0xE0000000 + n MiB, mapped by this box's `/dev/ocm` module as above.
- **PMU:** `armv9_c1_nano`, 21 counters (20 plus the cycle counter; `dmesg.txt`); mesh PMU `arm_cmn_0`.
- **Huge pages:** 256 pages of 2 MiB reserved at boot; MemTotal 1,833,848 kB.
- **DRAM caveat:** AP DRAM on this image is an embedded emulator memory, not LPDDR5X, so no DRAM latency or bandwidth number here is silicon-like.
- No real-time clock: every time his script read shows 1970.
