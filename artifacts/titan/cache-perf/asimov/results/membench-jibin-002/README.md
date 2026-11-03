# cache-mem-perf on the Asimov emulator: run membench-jibin-002 (round two)

Jibin Han's `cache-mem-perf` (github.com/jhan-positron/asimov, folder `cache-mem-perf`, commit `8ae533c916fb729a18058660e0a288443ecb1dfa`) ran on one emulated Asimov hemisphere on the GA13 Palladium on 2026-11-02. His whole results directory is `results/19700101T000000Z/`, byte for byte as his script wrote it; `SHA256SUMS` lists each file's sha256. The run's evidence is `evidence/runs/membench-jibin-002/` in the emuMemBenchBox sandbox. Round one is `../membench-jibin-001/`.

## Read first: what else changed since round one

- **The firmware is newer.** Round two ran on the latest SCP and TF-A releases, SCP 0.48.0 and TF-A 0.35.0, where round one ran SCP 0.34.0 and TF-A 0.24.0 (details under Platform facts). This was a decision on our side, not something he asked for. The newer SCP adds mesh setup that 0.34.0 lacks, so a difference from round one can come from the firmware as well as from his changes.
- **The kernel adds debugfs,** as he asked, for the mesh map. Nothing else in the kernel changed.
- **One difference showed up: multi-core DRAM writes are 44-76% faster,** and round one's hemisphere write limit is gone (next section). Every other best row both rounds ran with the same arguments agrees within 3.6%.
- **A control run is under way:** `membench-jibin-003` runs this same program and kernel on round one's firmware, so it tells whether the firmware caused the write change. It will be delivered as `../membench-jibin-003/`.

## The run

- Queue request 4507 on ga13pd01 (boards 12-15), granted 21:21:34 UTC. The init started at 21:58:31 UTC, about 0.70 s of chip time after the swap-in (the kernel's own clock, which starts partway into the boot, read 0.244 s), his script ran from 21:58:57 to 23:14:27 UTC, and the emulator was released at 23:15:21 UTC.
- His script ran as he asked: `sh run_asimov.sh` as root, with `latency`, `bandwidth` and `cmncount` beside it. This box's init (PID 1) started it as `/bin/sh /opt/membench/cache-mem-perf-8ae533c/run_asimov.sh`, pinned to CPU 2 under SCHED_FIFO priority 10, with RT throttling off and no time limit, as in round one.
- It exited 0 after 1.630 s of chip time (`MB RUN end status=exit:0 ns=1630000439`; his estimate was about 2 s). All 63 of his commands exited 0, 47 of them under `cmncount`. All 57 of his files came back intact through the results window, which held 60 files with this box's `init.log`, his script's console output (`out.txt`) and the kernel log (`MB WIN ok ... files=60 trunc=0`); the window's checksum matched the init's.
- Build: his Makefile with the asimov-os `v0.0.17` SDK's GCC (Arm GNU Toolchain 14.2.Rel1, 14.2.1) and his default flags, as round one: `-O2 -mcpu=cortex-a520 -static -Wall -Wextra -std=gnu11 -pthread -fno-tree-loop-distribute-patterns`, plus the SDK wrapper's sysroot, `-mabi=lp64`, `-fstack-protector-strong` and link flags. `latency` sha256 `78b5b55aeb84a30cbffd4accadb4ee5eb19232c9880e27af83b9e90aa82fe318`, `bandwidth` `e850315a2070c3f26ffd62bd7b926f9b8aa55e77939f229c2e6514d7545dd92d`, `cmncount` `bb0d30be9499053cbe4a78f0fab49018b6abeda9de0d7c6574ba8575f3a53d41`, all static. His timed code compiles to round one's instructions (only string and constant addresses moved); the one new code path is `--no-thp`.
- The run's checker passed every criterion (`JIBIN_CHECK PASS`, `evidence/runs/membench-jibin-002/judge-jibin.txt`): the firmware, kernel, CPU layout, huge pages and `/dev/ocm` as qualified; his script's exit 0; all 57 expected files; no nonzero exit among his commands; CPU 3 offline and back; perf counters open in every latency file; the mesh map in `sysinfo.txt`; `cmn-counts.csv` with all seven events and both timing rows for each of the 46 counted commands, plus the uncounted control's comment and timing rows; every backing his programs print is `hugetlb` or `ocm`, and the control rows' is `4k`, as `--no-thp` asks (latency prints each buffer's, bandwidth only its first thread's first buffer; the others had room, with 256 pages reserved and at most 128 needed at once); nothing on stderr.
- The emulator ran 2,779 wall seconds per chip second, as in round one.

## Platform facts

These were read on round two's qualification boot `membench-boot-003` (GA13 request 4502, 2026-11-02), which ran the same image copy, firmware, kernel and OCM module (this run's snapshot differs from its only in the init and his program), and from the RTL and address map, except where this run's files are cited. The sources are in `results/platform-facts.md` in the sandbox. Apart from the firmware, the kernel's debugfs and 64 kB of memory, everything below equals round one's platform.

- **Emulator image:** GA13 release `a10280100`, build `hemi_rtws_tlm`, RTL `0d9e214eb43b` (main, 2026-10-28), from this box's private copy. Real C1-Nano cores and clusters, the CMN-S3 mesh with its SLC and OCM, the SCP and the scratchpad; the matmul array is cut to one column. The CMN's HRA leg (0x8000_0000-0xBFFF_FFFF: PCIe and the control registers of SMS, XMS, the scratchpad and others) is tied off on this image, so nothing there answers.
- **Firmware:** SCP `scp-v0.48.0` rebuilt by this box with PCIe0 held (version `0.48.0-nopcie.1`, commit `e361a83`; loaded as the debug build) and TF-A `tfa-v0.35.0` (`3b3df18`) debug, the firmware asimov-os `v0.0.19` pins. Every SCP since 0.43.0 starts PCIe0 at boot and would stall on this image's dead HRA leg, so the box rebuilt 0.48.0 with that one flag changed; the rest of its code is 0.48.0's. Over round one's 0.34.0, the SCP adds mesh setup: 15 HN-S-to-SMS route overrides (vertical first, the same hop count) and a POCQ class-3 cap for QoS 0-7 traffic (the C1 cores send QoS 14, so not theirs), and a setup step for the scratchpad's DMA engines. The SAM profiles (`bootloader-no-sam`, `cold-boot-ocm-w4`), the SAM tables, the OCM programming and the AP reset vector are 0.34.0's. TF-A 0.35.0 adds a DSU driver, which at every CPU power-on writes the cluster power-control fields with their reset values and opens the cluster PMU and cluster power registers to Linux, and it lets Linux use the trace registers and trace buffer (nothing here uses either).
- **Kernel:** Linux 6.18.36 built from asimov-os `v0.0.17`'s config and patches plus transparent huge pages (madvise), hugetlbfs and debugfs (`CONFIG_DEBUG_FS=y`, `CONFIG_DEBUG_FS_ALLOW_ALL=y`); `v0.0.17`'s userspace (busybox 1.37.0, glibc 2.40). This run's banner and command line are in its `dmesg.txt`.
- **CPU placement:** ten C1-Nano cores, all online at boot. Device interrupts default to CPUs 0-1; CPUs 2-9 are isolated from the scheduler and `nohz_full`, with their RCU callbacks offloaded (this run's `init.log`: `MB LAYOUT ok online=0-9 iso=2-9 nohz=2-9`). Each CPU still takes its own timer and per-CPU interrupts, and his programs' system calls and page faults run on their own CPU. His script ran on CPU 2; CPU 3 was offline for phases A to D and back online for phase E. Each pair {2,3}, {4,5}, {6,7}, {8,9} shares an L2 and an L3 and one mesh port.
- **Clock:** core 2.000 GHz against the 1 GHz generic timer (one timer tick is one chip nanosecond); his own rows agree, at 4.01 cycles per 2.002 ns L1 load, and his CSV headers read `cntfrq_hz=1000000000`.
- **Caches:** L1 data 32 KiB and L1 instruction 32 KiB per core, L2 128 KiB and L3 256 KiB (one slice) per two-core cluster, 64-byte lines (this run's `sysinfo.txt`); these equal the RTL's configuration. The SLC is five home nodes (HN-S) of 1 MiB in 16 ways each; the firmware locks 4 ways of each as OCM, so 3.75 MiB of SLC caches DRAM.
- **Mesh placement:** a 6 by 6 grid of crosspoints. By the address map's node ids and the RTL's mesh, the home nodes of OCM0-4 (node ids 88, 160, 216, 288, 344) sit at crosspoints (x, y) (1,3), (2,4), (3,3), (4,4) and (5,3), and the mesh ports of the clusters of CPUs 2-3, 4-5, 6-7 and 8-9 (the address map's `c1_1` to `c1_4`, node ids 152, 208, 280, 336) at (2,3), (3,2), (4,3) and (5,2). The distance from a port to a home node, in crosspoints, is |dx| + |dy|. For CPU 2 this was checked on round one's qualification boot; this run's OCM rows bear it out for CPUs 4, 6 and 8 (below).
- **OCM:** five regions of 256 KiB at 0xE0000000 + n MiB, each in a different home node. `/dev/ocm` is this box's own module (`membench_ocm.ko`; no driver in this kernel serves OCM), which maps a region as Normal write-back in 4 KiB pages; a future asimov-os driver may map it differently. Nothing initialises OCM; a line never written reads as zeros (no ECC error).
- **Huge pages and memory:** 256 pages of 2 MiB reserved at boot (this run's `init.log`: `huge=256/256`); MemTotal 1,833,848 kB including that pool (this run's `sysinfo.txt`), 64 kB less than round one's for the larger kernel.
- **Core PMU:** `armv9_c1_nano`, 20 event counters plus the cycle counter. His group (cycles and raw 0x03, 0x17, 0xA2) counts user space only. 0xA2 (L3 read refill) counts on this core; 0x2A is not implemented here.
- **Mesh PMU:** `arm_cmn_0`, 280 events (this run's `sysinfo.txt`), one DTC for the whole mesh and one DTM per crosspoint. His seven counters fit at once (3 of the 4 counters on each home node's crosspoint, 7 of the 8 on the DTC), and no counter was multiplexed: `running_ns` equals `enabled_ns` on every row of `cmn-counts.csv`.
- **DRAM caveat:** AP DRAM on this image is an embedded emulator memory, not LPDDR5X, so no DRAM latency or bandwidth number here is silicon-like.

## Writes: round one's hemisphere limit is gone

The same four `--kernel all` commands, write rows, best of three:

| Command | Round one | Round two |
|---|---|---|
| 4 threads on CPUs 2,4,6,8, 2 MiB each | 88.8 GB/s | 127.9 GB/s (+44%) |
| 8 threads on CPUs 2-9, 2 MiB each | 88.3 GB/s | 155.4 GB/s (+76%) |
| 4 threads on CPUs 2,4,6,8, 16 MiB each | 86.8 GB/s | 128.0 GB/s (+47%) |
| 8 threads on CPUs 2-9, 16 MiB each | 86.7 GB/s | 151.7 GB/s (+75%) |

- The same commands' read and copy rows moved by under 0.5%, and one core still writes DRAM at 32.0 GB/s in both rounds.
- His writer-placement rows (16 MiB per writer, best of two) now show a limit per cluster, not per hemisphere: CPUs 2+4 and 2+8 write 64.0 GB/s (32.0 each); 2+3, one cluster, 40.9 GB/s (20.5-21.7 each); 2+4+6+8 128.0 GB/s (32.0 each); 2+3+4+5 and 2+3+8+9, two clusters, 85.8 and 84.1 GB/s (21.0-23.0 each). His aggregate is total bytes over the slowest writer's time.
- The firmware is the likely cause: its new mesh setup reroutes traffic from the home nodes to the memory controllers, and its other mesh change, the POCQ cap, applies to traffic the cores don't send. The control run `membench-jibin-003` (round one's firmware) settles it, and also gives his writer-placement rows on round one's firmware, the setup they were designed against.

## OCM and SLC latency by mesh distance

Best of the two fresh-chain passes, ns per load; the distance in crosspoints from the CPU's cluster port to the region's home node in brackets:

| CPU | OCM0 | OCM1 | OCM2 | OCM3 | OCM4 | all five | 2 MiB DRAM (SLC) |
|---|---|---|---|---|---|---|---|
| 2 | 19.77 (1) | 18.46 (1) | 21.36 (1) | 21.54 (3) | 22.00 (3) | 25.51 | 24.38 |
| 4 | 21.23 (3) | 21.27 (3) | 19.11 (1) | 20.49 (3) | 22.86 (3) | 26.11 | 24.64 |
| 6 | 23.44 (3) | 21.28 (3) | 19.98 (1) | 20.63 (1) | 18.96 (1) | 25.37 | 24.05 |
| 8 | 24.68 (5) | 24.48 (5) | 21.12 (3) | 22.94 (3) | 18.89 (1) | 27.70 | 26.26 |

- By distance, the per-region rows average 19.64 ns at 1 crosspoint (18.46-21.36, 8 rows), 21.82 ns at 3 (20.49-23.44, 10 rows) and 24.58 ns at 5 (24.48-24.68, 2 rows), about 1.1-1.4 ns per extra crosspoint. Each CPU's fastest region is one at 1 crosspoint. That places CPU 4's port but would fit CPUs 6 and 8 either way round; CPU 8 reading 1.1-3.2 ns slower than CPU 6 from OCM0-3 and level with it from OCM4 (18.89 against 18.96), and the all-five order below, tell those two apart.
- The all-five and 2 MiB rows count 1.00 refills per load at L1, L2 and L3 (0.998-1.001), so each load is one home-node read. They order the CPUs as their mean distance to the five home nodes does: CPU 6 and CPU 2 (1.8 crosspoints) fastest, CPU 4 (2.6) next, CPU 8 (3.4) about 2 ns behind CPU 2. On every CPU the all-five OCM row reads 1.1-1.5 ns above the 2 MiB DRAM row, which is in the SLC; OCM is mapped with 4 KiB pages and the DRAM buffer with 2 MiB pages.
- The per-region rows are rougher. The fresh chain did not change them much: their 40 timed passes count 1.11-1.45 L2 refills and 0.76-0.95 L3 read refills per load, as round one's re-walked rows did (1.14-1.31 and 0.77-0.91), so some lines still reach the cluster before their load, and the 256 KiB buffer fits in L2 plus L3 (384 KiB). The two passes of a row differ by up to 3.4 ns, and in 19 of the 20 rows the faster pass is the one with fewer L3 read refills (in the 20th the two counts differ by 0.001). The all-five rows, at 1.25 MiB, count 1.00 of each. So a per-region best understates a single home-node read, by an amount that varies from pass to pass.

## Mesh counts

- **His node ids are right.** In each of the 20 per-region latency rows, the region's own home node received 111,468-123,460 requests, against 9,042-10,576 at each other node, so 88, 160, 216, 288 and 344 are OCM0-4. The five OCM read rows show the same (71,550-76,496 against 9,485-9,909).
- **Background:** each core's control row (a 4 KiB chase on 4 KiB pages) puts 8,372-10,859 requests on each node.
- **The 2 MiB DRAM read row** (CPU 2) put 87,386-88,013 requests on each node: spread evenly, and about twice his estimate of 40,000.
- **The DRAM write rows** spread their requests evenly over the five nodes, within 0.2% on every row.
- **The counters' cost:** CPU 2's counted and uncounted control rows read `helper_elapsed_ns` 1,163,263 and 540,889, so 622,374 ns apart; the counted helper also makes 38 more sysfs reads than the uncounted one to set its events up (each event's file and its format files; 40 against 2), so that gap is not the counters alone. Their `child_elapsed_ns` read 504,243 and 481,627.

## Reading the numbers

- No real-time clock: the folder name and every time the run read show 1970 (the clock starts at zero at boot; the 2026 date in the `uname` line is the kernel's build stamp). The run took place on 2026-11-02.
- The scratchpad is postponed to a next phase. This snapshot has no `/dev/asimov-spm`, so phase C skipped itself (`sysinfo.txt` shows `ls: /dev/asimov-spm: No such file or directory`).
- The mesh map in `sysinfo.txt` prints crosspoint numbers and each node's logical id within its type, not node ids: HN-S #0-#4 are nodes 88, 216, 344, 160 and 288, that is OCM0, OCM2, OCM4, OCM1 and OCM3.
- A wrong node id would fail to open (the driver rejects it), so five nodes that look like the control under a region row would not by themselves mean wrong ids.
- The kernel's arm-cmn driver places the HN-S filter fields one bit off this RTL's; that does not affect the `_all` events he uses.
- `hns_cache_miss_all` counts every qualified lookup that misses, fills and flushes included, not only his loads.
- By round one's console timing, less a model of each command's own work, each command in his script cost about 3 to 5 ms of chip time, not 14; the console's 10 ms polling bounds it no closer. That is an estimate, and it covers the shell's whole wrapper around a command (the `+` line through `tee`, fork and exec, `cat`, `cat` and `rm`), not process start alone: here the uncounted control ran 0.48 ms from fork to exit (`child_elapsed_ns` 481,627).
- A partial `munmap` of a hugetlb buffer fails, so a latency sweep holds up to 22 huge pages until it exits; 256 were reserved and none ran short.
- The OCM streaming write over all five regions ran at 20.3-20.4 GB/s, below one core's 32.0 GB/s store rate to DRAM.
- The bandwidth program's main thread shares CPU 2 with its first worker; the threads start a rep within microseconds of one another.
- SLC and DRAM numbers carry the newer firmware's mesh setup; round one's carry 0.34.0's.

## Against round one

- 22 commands ran with the same arguments in both rounds. Every best row agrees within 3.6% (most within 1%), except the four multi-core DRAM write rows above. The latency rows agree within 1.7% except the 4 MiB fresh chain (29.76 ns in round one, 28.70 here); the new route overrides keep the same hop count, and the latencies did not move.
- Rows whose method changed: his per-region OCM rows from CPU 2 read 18.46-22.00 ns with fresh chains, against 18.78-23.17 ns re-walked in round one; the all-five OCM row 25.51 ns (round one 25.2 fresh, 25.5 flushed); the 8 MiB flushed DRAM row 52.71 ns with fresh chains (round one's flushed 1 to 8 MiB rows: 52.7 ns).

## Cross-check against earlier pre-silicon measurements

Round one's README compares his numbers with the load latencies asimov-bench measured on an older RTL of the same build kind (`hemi_rtws_tlm`, RTL `6da3026`). Round two's numbers agree with round one's, so the same comparison holds: L2 5.83 ns at 96 KiB against 5.60; the SLC 22.9-24.4 ns (512 KiB to 2 MiB fresh chains from CPU 2) against its 23.32 ns SLC-hit model; OCM 18.46-22.00 ns per region from CPU 2 against its 14.42 ns 64 KiB chase, a large gap still not explained (asimov-bench notes its chase reads below its own 20.0 ns waveform read of an SLC line, so it counts some lines already fetched; and that chase spans 16 pages, which fit the core's 16-entry L1 data TLB, where each of his regions spans 64); cold DRAM 52.2 ns at 32 MiB against its 53.3 ns on RTL bc5596aa (`hemi_tlm`, host-model DRAM). asimov-bench's boots ran an SCP with the route overrides and queue caps, closer to round two's firmware than to round one's. His numbers are unchanged; the gaps are noted, not corrected.
