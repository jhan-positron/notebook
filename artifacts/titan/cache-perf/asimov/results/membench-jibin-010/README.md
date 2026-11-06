# cache-mem-perf on the Asimov emulator: run membench-jibin-010 (round four, boot E)

Jibin Han's `cache-mem-perf` (github.com/jhan-positron/asimov, folder `cache-mem-perf`, commit `b79dffa3fb169255bf985bbddae33b86ee05c27f`) ran his follow-up script once, as boot E, the last boot of his round four: boot A's platform (TF-A 0.35.0 and the same kernel, the data prefetchers on, the OCM in 4 KiB translations) with the SCP rebuilt to stage the full-L3 operating mode for the clusters of CPUs 2-9 before they power on (SCP 0.48.0-nopcie-l3.1), on one emulated Asimov hemisphere on the GA13 Palladium on 2026-11-05 (UTC). He asked for this boot on 2026-11-04 at 18:57 PST (`docs/REQUEST.md`). His whole results directory is `results/bootE/`, byte for byte as his script wrote it. `dmesg.txt` beside it is the kernel log from the same boot, which carries one `/dev/ocm` line per mapping. `SHA256SUMS` lists the sha256 of his 113 files and `dmesg.txt`. The run's evidence is `evidence/runs/membench-jibin-010/` in the emuMemBenchBox sandbox.

## Read first

- **The L3 of CPU 2's cluster was in use as a cache.** IMP_CLUSTERPWRSTAT_EL1 read 0x70 just before and just after his hit-counter command: by the DSU RTL's field names all slices (ALL_SLICE) with the whole L3 RAM open to lookup and allocation (FULL_ON), the full-RAM encoding he expected; boots B, C and D read 0x0 there. In `latency-dram-small-l3.csv`, `l3d_hit_rd_per_load` reads 0.4651-0.4708 at 192 KiB, 0.7508-0.7712 at 256 KiB and 0.9152-0.9236 at 384 KiB (C: 0.0000 at every size), and `l3d_access_rd_per_load` minus `l3d_refill_rd_per_load` equals it to within 0.0001 in every row. The reading and the hit counter cover CPU 2's cluster only; the clusters of CPUs 4-9 rest on the SCP's staging lines (L3 power below).
- **E is boot C's program, module file and box lines with boot A's TF-A, kernel and 4 KiB OCM mapping; only the SCP is new.** His commit `b79dffa` with C's program build (the same binaries once stripped), C's `/dev/ocm` module file and the box's two lines as on C; TF-A 0.35.0 (`3b3df18`, debug) and the kernel byte for byte boot A's, the data prefetchers on, and A's 4 KiB OCM mapping (the module loaded with no parameters, `cont=0`). The SCP is SCP 0.48.0-nopcie-l3.1 (`28663ab` on `e361a83`, debug), which stages the full-L3 operating mode for the clusters of CPUs 2-9 before they power on, as SCP 0.48.0-nopcie.1 does for the cluster of CPUs 0-1 only (The SCP below).
- **Against boot C, the L3 alone:** the hit-set chases at 192, 256 and 384 KiB read 7.811, 9.489 and 10.906 ns against C's 14.101, 19.690 and 22.669 (0.481-0.554 over both of G1's files at these sizes), and the 512 KiB rows 0.760-0.779 times C's. In the small-footprint rows the core's 4-128 KiB chases read 0.986-1.002 times C's, and through the CME the L1 refills from outside the cluster at 8 and 16 KiB fall to 0.0114-0.0315 and 1.2234-1.2680 per load (C: 3.2778-3.3558 and 6.4963-6.6071), with as many refills in all or more, while the CME's latency there reads 1.019 and 1.120 times C's. The SLC row at 2 MiB reads 24.177 ns against C's 24.053 (A 24.091), 1.005 times C's, about the 0.5% between E's own two passes. The DRAM row at 32 MiB reads 52.875 ns against C's 52.238 (A 52.181), 0.626-0.694 ns above all four earlier boots, whose own values span 0.068 ns, and 16 MiB 0.481 ns above C's; but the 8 MiB chase did not move (45.077 against 45.130), and the flushed 8 MiB row, every load refilled from outside the cluster, read C's best in one pass (52.659 against 52.657) and 53.330 in the other, so these files do not show a fixed cost of an L3 lookup on every DRAM read. The sequential 8 MiB row reads 2.492 ns against 6.917, with both of its prefetch refill columns at 0.9997 per load, and G7's one-core reads run 1.577-2.684 times C's GB/s; these files do not show why (Against boot C below).
- **The other comparisons:** against boot A, which differs in the SCP, his commit, the builds and each row's placement draw, 57 of E's 69 core OCM rows read faster (geometric mean 0.865) and the CME's OCM rows 0.836-1.055 times A's (Against boot A below); G8 repeats C's L1 rows within 0.972-1.013 apart from the 4 KiB per-pass read, 0.886 times C's (The G8 rows below); and 0x8188 read 0 in every walk pass again, though on E no walk row's buffer had a contiguous or block entry for it to count (The walk rows below).
- **His script ran whole:** 3.250 s of chip time against his estimator's 3.773 s (C: 3.461 s), 138 commands, all exit 0 (`# run_followup.sh done ...: 0 measurement command(s) failed`), all 113 files back, no `# perf:` line, and `perf_cov` 1.0000 in all 809 counted rows. His two controls repeat run 3 and boot A: the 4 KiB repeated chase reads 2.002 ns, and `cme-roundtrip` 21.004-21.005 ns in all 21 files that carry it.
- **This box added two lines to his script and rebuilt the SCP** (The run and The SCP below). The lines, one just before and one just after his hit-counter command, write the power status of CPU 2's cluster into his `log.txt` and stdout as comment lines that look like his own; they read it from a read-only file in this box's `/dev/ocm` module. The lines and the module file are boot C's, and the module is boots B's and D's too.
- **The live console stopped echoing his stdout at line 147 of 158, so this README quotes the window's `out.txt` and his `log.txt`.** The init echoes at most 16,384 bytes of the script's stdout to the console and then prints `MB OUT cap=16384 rest-in-window`; the results window holds everything (`MB WIN ok ... files=116 trunc=0`), and its `out.txt` equals his `log.txt`.
- **E is the last boot of round four.** The round ran A, B, D, C and then E; the A repeat did not run, since C met his two conditions for dropping it (boot C's README). No further run follows this one.

## The SCP: staging the full-L3 mode

- **The rebuild:** SCP 0.48.0-nopcie.1 (`e361a83`, scp-v0.48.0 with PCIe0 held) plus one local commit, `28663ab`, under the local tag `scp-v0.48.0-nopcie-l3.1`, never pushed, kept as `evidence/firmware/0002-asimov_system-stage-the-full-L3-operating-mode-for-c.patch` (sha256 `9c6db588d1789772fa0c5422c627c047b64c6aaae302ea5bc93f43dc5a860cfc`; build record `evidence/firmware/scp-v0.48.0-nopcie-l3.1.txt`; package `asimov-scp-fw.tar.gz`, sha256 `a8cca78ab5c4198ebf33f28cfb88ac0133d6ca640488f147e86e78d8a5c35a30`). No qualification boot ran for it: E was its first boot, and E's check (L3 power below) served as its check.
- **What it changes:** the stock SCP sets cluster operating mode 7 (all slices, full L3 RAM) only for cluster 0, the cluster of CPUs 0-1, before it powers on the primary core. Clusters 1-4 power on later, when Linux starts CPUs 2-9, through the SCP's PPU driver, which writes only the power policy, so on boots A to D they came up in the reset mode 0. The commit changes one function, `asimov_system_init_primary_core` in `mod_asimov_system.c`: right after cluster 0's unchanged staging and before the primary core's power-on, a read-modify-write puts operating mode 7 into the PWPR of clusters 1-4 with their power policy left OFF, which the PPU takes as a status-only update, and BL2 then logs each cluster's PWSR after at most 1,000 reads waiting for OP_STATUS 7. The driver's cluster power-on keeps the operating-mode field, so by its code each of those clusters requests mode 7 with ON at Linux's CPU_ON, the request cluster 0 makes (`docs/PLAN.md` section 2).
- **The banners** (`evidence/runs/membench-jibin-010/a01/evidence/run-evidence/uartout/uart_0.log`, the SCP console): BL1 at line 2 and BL2 at line 13 (0.092990 s of the SCP's clock) both print `version: 28663ab (0.48.0-nopcie-l3.1)  (debug)`, the debug build. Boot A's and C's consoles print `version: e361a83 (0.48.0-nopcie.1)  (debug)` on the same lines.
- **The staging lines,** `uart_0.log` lines 181-187 (SCP cluster N is the cluster of CPUs 2N and 2N+1: the SCP's `scp_mmap.h` places cluster 1 at mesh node 152, the crosspoint his G6 rows give for CPU 2, and its `Pinned CLUS1CORE1` line comes back when CPU 3 does):

| Line | SCP time, s | Text | Bits [19:16] | Bits [3:0] |
|---|---|---|---|---|
| 181 | 0.295551 | `[ASIMOV SYSTEM] Powering on primary core (CLUS0CORE0)...` | | |
| 182 | 0.297071 | `[ASIMOV SYSTEM] Staged cluster 0 PPU PWPR=0x00070008 (ON)` | OP_POLICY 7 (the written constant) | PWR_POLICY 8, ON (the written constant) |
| 183 | 0.298613 | `[ASIMOV SYSTEM] Staged cluster 1 PPU PWSR=0x00070000 (OFF)` | OP_STATUS 7 | PWR_STATUS 0, OFF |
| 184 | 0.300174 | `[ASIMOV SYSTEM] Staged cluster 2 PPU PWSR=0x00070000 (OFF)` | OP_STATUS 7 | PWR_STATUS 0, OFF |
| 185 | 0.301736 | `[ASIMOV SYSTEM] Staged cluster 3 PPU PWSR=0x00070000 (OFF)` | OP_STATUS 7 | PWR_STATUS 0, OFF |
| 186 | 0.303298 | `[ASIMOV SYSTEM] Staged cluster 4 PPU PWSR=0x00070000 (OFF)` | OP_STATUS 7 | PWR_STATUS 0, OFF |
| 187 | 0.304861 | `[ASIMOV SYSTEM] Primary core power-on initiated` | | |

- **What is read and what is fixed text:** cluster 0's `PWPR=0x00070008` is the constant the SCP writes, printed from that same constant by the unchanged stock code, and the words `(ON)` and `(OFF)` are fixed text in the two format strings. Only the four PWSR values are reads, each taken after the bounded wait. Each decodes to OP_STATUS [19:16] = 7, the staged mode, and PWR_STATUS [3:0] = 0, OFF (the SCP's PPU driver: 0 is OFF, 8 is ON), so each of clusters 1-4 reported mode 7 while still powered off.
- **Their order:** all five lie between `Powering on primary core` (line 181) and `Primary core power-on initiated` (line 187), and so before every `Pinned CLUS<N>CORE<m>` line: the first is `Pinned CLUS0CORE0` at line 190 (0.309214 s), and the cores of clusters 1-4 follow at lines 195-213 (0.480774-0.509570 s). So each of those clusters had its mode staged before it powered on. CPU 3's return at the end of his script is line 215 (`Pinned CLUS1CORE1`, 3.961348 s).
- **What it cost:** 9.310 ms of the SCP's clock from line 181 to line 187, against boot A's 3.062 ms (0.295317 to 0.298379 s, its lines 181-183): 6.248 ms more, with the four new lines 1.542-1.562 ms apart. That is about what four more lines take on this console (A's lines 181-183 are 1.520 and 1.542 ms apart), so this figure does not separate the staging's register writes and waits from its printing.

## L3 power

- **The samples:** IMP_CLUSTERPWRSTAT_EL1 (S3_0_C15_C3_7) reads 0x70 in his `log.txt` on CPU 2's cluster just before and just after his hit-counter command, both with CPU 3 offline (lines 7 and 9: `# box clusterpwrstat before l3: 0x70`, `# box clusterpwrstat after l3: 0x70`; both reads returned a value, not an error). He asked for it printed the same way as before ("it should read the full-RAM encoding this time", 18:57 PST). Boots B, C and D read 0x0 at the same two places. TF-A 0.35.0 (`3b3df18`), which this boot runs (its banner, line 2 of the AP console, `uart_1.log` beside `uart_0.log`: `NOTICE:  version: 3b3df18 (0.35.0)  (debug)`), has no hook, and the AP console carries no `pfoff` line, so unlike boots B and D this boot has no power-on readback of the register.
- **The reading,** by the DSU RTL's field names (Arm's TRM was not consulted; `evidence/jibin/l3-power-rtl.md` parts 2, 3, 4 and 6): the register copies the cluster power sequencer's committed state, the slice field in bits [7:6] and the L3 RAM field in bits [5:4], and bits [1:0] are the ORs of the cores' retention and power-down requests. 0x70 is [7:6] = 01, ALL_SLICE, and [5:4] = 11, FULL_ON, with bits [3:0] at 0. ALL_SLICE with FULL_ON is cluster operating mode 7, the mode the SCP staged, and a power-on from OFF with mode 7 already staged goes out as one mode-7 request, which reads 0x70. With FULL_ON the sequencer gives the L3 slice lookup and allocate permission in both of its halves. This DSU has one slice, and with one slice ALL_SLICE and ONE_SLICE give the same internal slice status, so 01 does not mean a second slice. The 0x0 of boots B, C and D is ONE_SLICE with SFONLY, the snoop-filter-only state in which the slice neither looks up nor allocates.
- **E's check** (`docs/PLAN.md` section 8): the run's checker reports the staging values and the box readings without judging them, so this check decides whether E answers his question. `python3 -I evidence/jibin/echeck.py evidence/runs/membench-jibin-010` printed `staging=PASS box=PASS l3_hits=PASS l2_rest=PASS prefetchers_on=PASS` (`evidence/runs/membench-jibin-010/echeck.txt`). Its thresholds are its own (a hit count above 0.01 per load and access minus refill within 25% of it, the L2 refills not accounted for above 0.01 per load, and both prefetch refill columns above 0.9 per load), and the values below, recomputed for this README by separate code, clear them by wide margins. Part by part:
  - **The staging lines:** the five lines in order, between line 181 and line 187 and before every `Pinned CLUS<N>CORE<m>` line, with OP_STATUS 7 and PWR_STATUS 0 in all four PWSR values (The SCP above).
  - **The box readings:** 0x70 before and after, bits [7:6] 01 and [5:4] 11; boots B and D read 0x0.
  - **The L3 hits:** in `latency-dram-small-l3.csv` at 192, 256 and 384 KiB, `l3d_hit_rd_per_load` (0x81C6) is far above 0, and `l3d_access_rd_per_load` (0xA0) minus `l3d_refill_rd_per_load` (0xA2) equals it to within 0.0001 in all nine rows (the table below; in all 21 rows of the file too). On C, 0x81C6 reads 0.0000 in all 21 rows and 0xA0 equals 0xA2 to within 0.0001, as on boots B and D. 0x81C6, which had read nonzero on no earlier boot, counts here.
  - **The L2 refills:** in `latency-dram-small.csv`, another process at the same sizes, `l2d_refill_per_load` minus `l2d_refill_hwprf_per_load`, `l2d_refill_l1dhwprf_per_load` and `l3d_refill_rd_per_load`, the L2 refills that neither prefetch event nor 0xA2 accounts for, is 0.4614-0.9132 per load, where boot A's is about 0 (-0.0002 to 0.0000; C's -0.0001 to 0.0000). For example, at 192 KiB, rep 0: E 0.5801 - 0.1176 - 0.0000 - 0.0011 = 0.4614; A 0.5844 - 0.1241 - 0.0000 - 0.4604 = -0.0001.
  - **The prefetchers,** on as on C: the 8 MiB rows of `latency-dram-seq.csv` read `l1d_refill_hwprf_per_load` and `l2d_refill_l1dhwprf_per_load` 0.9997 in both reps (boot A: 0.9999; C: 1.0000 and 0.9999; B and D: 0.0000). The row's latency, 2.501 and 2.492 ns per rep against C's 6.927 and 6.917, was not part of this check (Against boot C below).

| Size, rep (`latency-dram-small-l3.csv`) | 0x81C6 hits | 0xA0 accesses | 0xA2 refills | 0xA0 - 0xA2 | L2 refills not accounted for, E (`latency-dram-small.csv`, same rep, another process) | The same, A |
|---|---|---|---|---|---|---|
| 192 KiB, 0 | 0.4651 | 0.4653 | 0.0002 | 0.4651 | 0.4614 | -0.0001 |
| 192 KiB, 1 | 0.4708 | 0.4708 | 0.0000 | 0.4708 | 0.4663 | -0.0002 |
| 192 KiB, 2 | 0.4707 | 0.4707 | 0.0000 | 0.4707 | 0.4706 | 0.0000 |
| 256 KiB, 0 | 0.7658 | 0.7659 | 0.0002 | 0.7657 | 0.7542 | -0.0001 |
| 256 KiB, 1 | 0.7508 | 0.7508 | 0.0000 | 0.7508 | 0.7680 | -0.0001 |
| 256 KiB, 2 | 0.7712 | 0.7713 | 0.0001 | 0.7712 | 0.7607 | -0.0001 |
| 384 KiB, 0 | 0.9236 | 0.9433 | 0.0198 | 0.9235 | 0.8899 | -0.0002 |
| 384 KiB, 1 | 0.9222 | 0.9537 | 0.0315 | 0.9222 | 0.9072 | -0.0001 |
| 384 KiB, 2 | 0.9152 | 0.9461 | 0.0309 | 0.9152 | 0.9132 | 0.0000 |

- **Every part holds, so E's rows have the L3 of CPU 2's cluster in full mode.**
- **Coverage:** the runtime reading and the hit counter cover CPU 2's cluster only (SCP cluster 1). E's TF-A 0.35.0 (`3b3df18`) has no hook, so no power-on readback of the register exists for any cluster. The clusters of CPUs 4-9 (SCP clusters 2-4) rest on their PWSR, read at boot while they were OFF (OP_STATUS 7, `uart_0.log` lines 184-186), and on the same power-on path as CPU 2's cluster, so CPU 8's G2 rows and the G6 route rows from CPUs 4, 6 and 8 carry that caveat; all ten CPUs came online (`dmesg.txt` line 116: `smp: Brought up 1 node, 10 CPUs`), so no cluster refused the mode-7 power-on (`docs/PLAN.md` section 2). A reading, not a check: by the same L2 arithmetic over every pass of the core OCM rows that carry the prefetch counters, E's rows from CPUs 4, 6 and 8 count up to 0.4419, 0.4249 and 0.4431 L2 refills per load that neither prefetch event nor 0xA2 accounts for, and CPU 2's up to 0.4843, while on boots A to D every pass of the same rows, from every CPU, reads at most 0.0157. Read that way, the L3s of those clusters served reads too.
- **Linux runs at EL2:** `dmesg.txt` line 47 reads `CPU features: detected: Virtualization Host Extensions` and line 118 `CPU: All CPU(s) started at EL2`, as on every boot of this kernel. That is the state the proof that the `clusterpwrstat` read cannot trap assumes (`evidence/jibin/pwrstat-read-verdict.txt`).
- **Boots A to D:** the L3 note sent to him on 2026-11-04 at 18:51 PST (`docs/REQUEST.md`) covers them; it is not repeated here.
- **No read on CPU 0 or 1:** this boot reads the register on CPU 2 only. A read on CPU 1 is proven unable to trap too but, as on CPU 2, not proven always to complete, and a hang there could lose the whole boot: if the init, pinned to CPUs 0 and 1, was on CPU 1, it would stop, and the kernel's lockup detector, which watches CPU 1, would panic the kernel (`evidence/jibin/pwrstat-read-cpu1-addendum.txt`). E's 0x70 on CPU 2, beside its L3 hits, is itself a positive control for the encoding: the full-RAM value on a cluster whose L3 is in use (`docs/PLAN.md` section 8).

## Against boot C: the L3 alone

E and C ran the same commit, `b79dffa`: the same 138 command lines in the same order (E's `log.txt` equals C's apart from his uptime stamps, the results folder's name and the two box readings), the same program build (`latency`, `bandwidth` and `bandwidth_r3` are C's once stripped, 6 bytes of the assembler's temporary object name apart; `bandwidth_r2` and `cmncount` byte for byte), the same TF-A 0.35.0 (`3b3df18`), kernel, module file and box lines, and the data prefetchers on. By `evidence/bundle/r4-build/snapshots-l3-checks.txt` (E's snapshot against C's: `UNEXPECTED: none`), the two snapshots differ only in the SCP, the settings `FWSET`, `MB_OCM_CONT` and `MB_OUT`, the init (it loads the module with `cont=0` on E and `cont=1` on C, and names the results folder), the asimov-os commit they were built at, those object names, and the records and files built from these. C's `cont=1` touches only the OCM mappings, and the rows below use DRAM buffers, on huge pages or on 4 KiB pages. So on these rows, all run on CPU 2 or its CME apart from CPU 8's 4 KiB control, E against C is the L3 alone, except that each command is its own process on each boot, whose buffers need not sit on the same physical pages. E's OCM rows are compared with boot A's below, both without the hint. The figures are E's over C's: each latency row's best ns per load, where below 1 means faster on E, and for the bandwidth rows each row's best aggregate GB/s, where above 1 means faster on E. The spread is the largest (max - min) / min of one row's reps or passes inside one boot, so a ratio well beyond both boots' spreads is a move.

| Rows | Rows compared | E/C, best | Spread inside one row: C; E |
|---|---|---|---|
| G1 chase, 4-128 KiB (`latency-dram-small.csv`) | 9 | 0.986-1.002 | 1.2%; 0.4% |
| G1 hit-set rows, 64-128 KiB (`latency-dram-small-l3.csv`) | 3 | 0.988-0.999 | 1.3%; 0.4% |
| G1 192, 256 and 384 KiB, both files | 6 | 0.481-0.554 | 2.7%; 2.2% |
| G1 512 KiB, both files | 2 | 0.760-0.779 | 2.7%; 2.8% |
| G1 768 KiB and 1 MiB (`latency-dram-large.csv`) | 2 | 0.934, 0.974 | 2.4%; 1.6% |
| G1 2 MiB, the SLC row (`latency-dram-large.csv`) | 1 | 1.005 | 0.2%; 0.5% |
| G1 1.5 and 3-8 MiB | 5 | 0.969-1.016 | 1.8%; 1.2% |
| G1 16 and 32 MiB | 2 | 1.009, 1.012 | 0.2%; 0.1% |
| G1 flushed 8 MiB (`latency-dram-flushed.csv`) | 1 | 1.000 | 0.2%; 1.3% |
| G1 sequential 8 MiB (`latency-dram-seq.csv`) | 1 | 0.360 | 0.1%; 0.4% |
| G2's 4 KiB controls, CPUs 2 and 8 (one rep each) | 2 | 1.001-1.002 | - |
| 32 MiB stimulus on 4 KiB pages: TLB set, walk set | 1, 1 | 0.975, 1.035 | 0.2%; 0.1% |
| CME chase, 4 KiB (`cme-latency-dram-small.csv`) | 1 | 0.995 | 0.0%; 0.0% |
| CME chase, 8-32 KiB | 4 | 1.012-1.120 | 1.1%; 4.4% |
| CME chase, 48-384 KiB | 7 | 0.940-0.977 | 8.4%; 1.3% |
| CME chase, 512 KiB-4 MiB (`cme-latency-dram-large.csv`) | 7 | 0.964-0.992 | 0.9%; 0.7% |
| CME chase, 6-32 MiB | 4 | 0.998-1.002 | 0.2%; 0.1% |
| CME flushed 8 MiB, sequential 8 MiB | 1, 1 | 0.992, 1.000 | 0.2%; 0.1% |
| `cme-roundtrip` best, `cme-call` best | 21, 21 | 1.000, 0.976-1.025 | 1.4%; 1.2% |
| Write rows, G5 (GB/s) | 8 | 1.000-1.001 | 0.4%; 0.4% |
| Read rows, G7, 2 MiB (`bandwidth-read-prefetch.csv`, GB/s) | 5 | 1.577-2.684 | 13.3%; 5.9% |
| Read rows, G7, 32 MiB (GB/s) | 5 | 1.977-2.669 | 0.2%; 0.4% |
| G8 apart from the 4 KiB per-pass read (GB/s; The G8 rows below) | 15 | 0.972-1.013 | 11.0%; 5.7% |
| G8 4 KiB per-pass read (GB/s) | 1 | 0.886 | 0.5%; 0.2% |

| Hit-set row (`latency-dram-small-l3.csv`) | B, D best ns (prefetchers off) | C best ns | E best ns | E/C | E per load: L2 hits; L3 hits; 0xA2 refills | C per load: L2 hits; 0xA2 refills |
|---|---|---|---|---|---|---|
| 64 KiB | 5.130, 5.132 | 5.131 | 5.126 | 0.999 | 0.8241-0.8265; 0.0001-0.0002; under 0.0001 | 0.8247-0.8253; 0.0002 |
| 96 KiB | 5.826, 5.821 | 5.829 | 5.819 | 0.998 | 0.9528-0.9534; 0.0007-0.0015; under 0.0001 | 0.9522-0.9539; 0.0006-0.0018 |
| 128 KiB | 6.062, 6.053 | 6.091 | 6.019 | 0.988 | 0.9754-0.9817; 0.0054-0.0114; 0.0000-0.0001 | 0.9765-0.9813; 0.0055-0.0100 |
| 192 KiB | 14.506, 14.466 | 14.101 | 7.811 | 0.554 | 0.5280-0.5336; 0.4651-0.4708; 0.0000-0.0002 | 0.5264-0.5360; 0.4629-0.4727 |
| 256 KiB | 20.171, 20.204 | 19.690 | 9.489 | 0.482 | 0.2288-0.2492; 0.7508-0.7712; 0.0000-0.0002 | 0.2265-0.2315; 0.7686-0.7735 |
| 384 KiB | 23.682, 23.674 | 22.669 | 10.906 | 0.481 | 0.0466-0.0569; 0.9152-0.9236; 0.0198-0.0315 | 0.0592-0.0676; 0.9326-0.9410 |
| 512 KiB | 23.728, 23.917 | 23.722 | 18.481 | 0.779 | 0.0022-0.0072; 0.4031-0.4118; 0.5813-0.5921 | 0.0021-0.0115; 0.9888-0.9982 |

- **The hit-set rows** (his G1 64-512 KiB chases, the first rows he named): at 64 and 96 KiB nothing moved (0.999 and 0.998), and at 128 KiB little (0.988), though E's three reps sit below every rep of B, C and D, with 0.0054-0.0114 L3 hits per load where C counts 0.0055-0.0100 outside refills; the L2 serves 0.82-0.98 reads per load at 64-128 KiB on both boots. At 192, 256 and 384 KiB, E's L2 hits per load stay within about 0.02 of C's, and where C counts 0.4629-0.9410 reads per load refilled from outside the cluster (0xA2), E counts about as many L3 hits (0x81C6, 0.4651-0.9236) and at most 0.0315 outside refills; the latency reads 0.481-0.554 times C's. At 512 KiB E counts 0.4031-0.4118 L3 hits and 0.5813-0.5921 outside refills per load, against C's 0.9888-0.9982 outside, and reads 0.779 times C's. The same sizes in `latency-dram-small.csv`, another process on each boot, agree with these rows to 0.1-0.9% on E (7.821, 9.527 and 11.004 ns) and to 0.1-2.4% on C (14.206, 19.228 and 22.683 ns). Boots B and D, with the prefetchers off, read 14.466-14.506, 20.171-20.204 and 23.674-23.682 ns at 192, 256 and 384 KiB, with 0.0000 L3 hits at every size. Which lines the L3 held, these files do not show.
- **Against asimov-bench's pre-silicon figure:** its chase of a 192 KiB set on DSU1, on an older RTL of the same build kind (`hemi_rtws_tlm`, RTL `6da3026`), read 15.16 ns per load, which it takes as a lower bound on an L3 hit (`references/asimov-bench/presilicon-perf/asimov-latency/OPS.md:154`). E's 192 KiB rows, with 0.4651-0.4708 L3 hits per load, read 7.811 and 7.821 ns, about half of it, and B's, C's and D's hit-set rows, with none, 14.101-14.506 ns.
- **The small-footprint rows:** the core's chases at 4-128 KiB read 0.986-1.002 times C's (2.002-6.023 ns on E). Through the CME (`cme-latency-dram-small.csv`), whose two refill events split its L1 refills into those served from inside the cluster (inner, 0x327D: on Asimov the DSU's L3 or the other core's caches, the event does not say which) and from outside it (outer, 0x327E: SLC, OCM or DRAM), far more of E's refills come from inside than C's at every size, most of them up to 32 KiB and a third at 64 KiB: at 8 KiB 3.9520-4.0239 inner and 0.0114-0.0315 outer per load (C: 0.5875-0.5986 and 3.2778-3.3558), at 16 KiB 9.0452-9.2349 and 1.2234-1.2680 (C: 1.2810-1.3874 and 6.4963-6.6071), at 64 KiB 5.0083-5.2198 and 10.1060-10.1689 (C: 1.8847-2.0538 and 15.0115-15.0782). Its refills in all (inner plus outer) stay about as many at 8 KiB (3.9677-4.0353 against C's 3.8653-3.9544) and rise at 16 KiB (10.2686-10.4881 against 7.7773-7.9945), nearly all of them its prefetcher's on both boots (`cme_l1d_refill_hwprf_per_load` 3.7922-3.8522 and 9.8067-10.0261; C: 3.6957-3.7791 and 7.3534-7.5599). The CME's latency reads 24.932 against 24.466 ns at 8 KiB (1.019), 35.065 against 31.303 at 16 KiB (1.120) and 45.639 against 48.115 at 64 KiB (0.949), and 0.940-1.034 times C's at 24-384 KiB.
- **His 24 ns, the SLC row at 2 MiB** (`latency-dram-large.csv`): 24.177 ns best (passes 24.299 and 24.177) against C's 24.053 (24.053, 24.102) and A's 24.091 (24.091, 24.149), 1.005 times C's and 1.004 times A's: 0.124 ns above C's best, about the 0.122 ns between E's own two passes, so by this README's rule not a move, though both of E's passes lie above every pass of the four earlier boots (23.888-24.149 ns). E's 0xA2 reads 0.9790 and 0.9810 per load there, C's 0.9984 and 0.9982. Around it, 1.5 MiB reads 23.784 against 23.793 ns (1.000), 3 MiB 25.507 against 25.111 (1.016) and 4 MiB 28.321 against 29.216 (0.969; C's two passes 1.8% apart, both of E's below both of C's and both of A's).
- **His 52 ns, the DRAM row at 32 MiB:** 52.875 ns best (passes 52.875 and 52.881) against C's 52.238 (52.326, 52.238) and A's 52.181 (52.181, 52.321): 1.012 times C's, 0.637 ns more, and 0.626-0.694 ns above all four earlier boots (B 52.248, D 52.249), which span 0.068 ns. 0xA2 reads 0.9999 and 0.9998 per load (C: 1.0000 in both passes). At 16 MiB E reads 51.167 against 50.686 ns (1.009) and at 8 MiB 45.077 against 45.130 (0.999). The flushed 8 MiB row (`latency-dram-flushed.csv`) reads 52.659 ns best against C's 52.657 (1.000); E's other pass read 53.330, C's 52.739. So E's 16 and 32 MiB passes sit 0.380-0.700 ns above every pass of the four earlier boots, while its 8 MiB passes sit among theirs and its 6 MiB passes below theirs; these files do not show what raised the 16 and 32 MiB rows.
- **From 512 KiB to 1 MiB** (`latency-dram-large.csv`): 17.395 against 22.903 ns at 512 KiB (0.760), 22.072 against 23.634 at 768 KiB (0.934) and 23.216 against 23.830 at 1 MiB (0.974), with 0xA2 at 0.5237-0.5437, 0.8375-0.8560 and 0.9130-0.9212 per load on E against 0.9543-0.9559, 0.9814-0.9862 and 0.9899-0.9928 on C.
- **The sequential 8 MiB row** (`latency-dram-seq.csv`): 2.501 and 2.492 ns per rep (best 2.492) against C's 6.927 and 6.917 (best 6.917; A 6.917), with `l1d_refill_hwprf_per_load` and `l2d_refill_l1dhwprf_per_load` 0.9997 in both reps (C: 1.0000 and 0.9999; A: 0.9999) and `l2d_refill_hwprf_per_load` 0.0001 and 4.578e-05. B and D read 52.762 and 52.763 ns with 0.0000 in all three columns. These files do not show why its latency fell. The CME's sequential row reads 21.417 ns on both E and C, `cme_l1d_refill_hwprf_per_load` 1.0000.
- **G7, the one-core read rows** (`bandwidth-read-prefetch.csv`): the plain read reaches 24.945 GB/s at 2 MiB and 24.546 at 32 MiB, against C's 9.294 and 9.196 (2.684 and 2.669 times; B and D, with the prefetchers off and another `bandwidth` build, 5.031 and 5.007 at 2 MiB, 2.377 at 32 MiB). The rows with a software prefetch 4, 8 and 16 lines ahead read 18.285-20.353 GB/s (C: 9.249-9.862) and the two-stream rows 17.982 and 18.911 (C: 11.400 and 8.681), so on E the plain read is the fastest of the five kernels at both sizes. The plain reads take 5.13-5.22 cycles per line against C's 13.78-13.93, with `l1d_refill_hwprf_per_line` 0.9927-0.9994 (C: 0.9921-0.9994); on the software-prefetch rows that column reads 0.2814-0.4650 (C: 0.8524-0.9103), and `l3d_refill_rd_per_line` is at most 0.0032 in every E rep (C: up to 0.3122). Per line, the plain read's L1, L2 and prefetch refill counts are about C's, so these files do not show why it got faster.
- **The CME's DRAM rows past its small footprints:** 0.964-0.992 times C's at 512 KiB-4 MiB and 0.998-1.002 at 6-32 MiB; the flushed 8 MiB row 0.992.
- **The 32 MiB stimulus on 4 KiB pages:** the TLB-set row reads 57.611 against 59.081 ns (0.975) and the walk row 58.705 against 56.726 (1.035); the walk rate on this chain differs from process to process (The walk rows below).
- **His controls and the write rows:** the 4 KiB repeated chase reads 2.002 ns best (reps 2.002, 2.002, 2.002; C and A 2.002), and `cme-roundtrip` 21.004-21.005 ns in all 21 files (C and A the same); G2's 4 KiB controls read 1.001-1.002 times C's and G5's write rows 1.000-1.001.
- **The boots side by side:**

| Row | A | B | C | D | E |
|---|---|---|---|---|---|
| IMP_CLUSTERPWRSTAT_EL1 of CPU 2's cluster (the box lines) | not read | 0x0 | 0x0 | 0x0 | 0x70 |
| `l3d_hit_rd_per_load` at 256 KiB (`latency-dram-small-l3.csv`) | no such row | 0.0000 | 0.0000 | 0.0000 | 0.7508-0.7712 |
| G1 256 KiB chase (`latency-dram-small.csv`), best ns | 19.470 | 20.172 | 19.228 | 20.170 | 9.527 |
| G1 2 MiB chase (`latency-dram-large.csv`), best ns | 24.091 | 23.902 | 24.053 | 23.888 | 24.177 |
| G1 32 MiB chase, best ns | 52.181 | 52.248 | 52.238 | 52.249 | 52.875 |
| G1 sequential 8 MiB (`latency-dram-seq.csv`), best ns | 6.917 | 52.762 | 6.917 | 52.763 | 2.492 |
| G7 one-core plain read of 32 MiB, best GB/s | no such row | 2.377 | 9.196 | 2.377 | 24.546 |

Each row is the same command on every boot that has it. What differs: the commit (A `e8e4580`, B `7921962`, D `ed6056a`, C and E `b79dffa`); the data prefetchers (off on B and D through TF-A 0.35.0-pfoff.1, `5a9e2a8`; on elsewhere, with TF-A 0.35.0, `3b3df18`); the SCP (SCP 0.48.0-nopcie.1, `e361a83`, on A to D, which leaves the L3 of CPUs 2-9 in the snoop-filter-only mode; SCP 0.48.0-nopcie-l3.1, `28663ab`, on E); the OCM mapping (the 64 KiB hint on C and D), which these DRAM rows do not use; and G7's `bandwidth` build (B's and D's differ from C's and E's). `latency`'s `chase` is the same instructions at the same offsets in their 64 B lines in all five builds (boot C's README for A, B and D; E's `latency` is C's once stripped).

## Against boot A: the OCM rows

E's OCM rows pair with boot A's by command: on both boots the kernel places each mapping and fills it with single 4 KiB entries (E's module loaded with `cont=0`; boot C's README compares this module with A's function by function: they differ only by the contiguous hint, with its longer mapping line, and the `clusterpwrstat` file). What differs: the SCP (on E the L3 of CPU 2's cluster in full mode and the others staged, L3 power above); his commit and builds (A ran `e8e4580`, its `latency` sha256 `ce19c59594b1fc8bc86a58820c500540e1a58714f3485f08fd97365ea953f3e3`, and its module, `e9f83e6d...` from asimov-os `a434694`, printed the short map line; by `evidence/jibin/latency-e8e4580-b79dffa.txt`, A's `latency` against C's build, which E's equals once stripped, `chase`, `timed_walk` and the CME kernels are the same instructions 256 B higher, at the same offsets in their 64 B lines apart from the low bits of global addresses); the box's two lines around command 2 on E; each command's own placement draw on each boot (only 5 of the 110 paired mappings share their `va - pa` modulo 64 KiB, OCM mappings below); and the rows C and E add, so positions shift: A's command 1 is E's 1, A's 2-38 are E's 3-39 and A's 39-105 are E's 46-112. By his uptime stamps E's commands 3-39 started 0.00-0.08 s earlier than their A twins and E's 46-112 0.18-0.23 s later, after the walk rows. The figures are E's best ns per load over A's, below 1 meaning faster on E; the table in OCM mappings below lists every file.

| Rows | Rows compared | E/A, best | Faster on E | Largest pass spread inside one row, ns: A; E |
|---|---|---|---|---|
| Core OCM sparse per region, CPUs 2 and 8 | 10 | 0.691-1.096 | 9 | 12.218; 9.828 |
| Core OCM vary per region, CPUs 2 and 8 | 10 | 0.896-1.412 | 6 | 9.672; 11.172 |
| Core OCM dense per region, CPUs 2 and 8 | 10 | 0.683-0.942 | 10 | 2.297; 3.967 |
| Core OCM all five regions, dense and sparse, CPUs 2 and 8 | 4 | 0.914-1.005 | 2 | 1.178; 1.812 |
| Core OCM with the TLB set, CPU 2: dense | 5 | 0.685-0.979 | 5 | 1.822; 2.976 |
| Core OCM with the TLB set, CPU 2: sparse | 5 | 0.780-0.860 | 5 | 9.766; 9.187 |
| Core OCM with the TLB set, CPU 2: vary | 5 | 0.962-1.112 | 1 | 9.969; 9.516 |
| Core OCM route rows, G6, from CPU 2 | 5 | 0.833-0.943 | 5 | 0.808; 4.469 |
| Core OCM route rows, G6, from CPUs 4, 6 and 8 | 15 | 0.669-1.011 | 14 | 3.518; 7.563 |
| CME OCM chases: dense | 5 | 0.850-0.929 | 5 | 0.329; 0.296 |
| CME OCM chases: sparse | 5 | 0.836-1.055 | 1 | 10.140; 13.547 |
| CME OCM chases: vary | 5 | 0.966-1.010 | 4 | 3.156; 2.907 |
| CME OCM chases: all five | 2 | 0.962-0.967 | 2 | 3.472; 2.319 |

- **Core OCM:** 57 of the 69 rows got faster (geometric mean 0.865; 0.890 by the median of each row's passes); 3 are within 1% of A and 45 differ by more than 10%. All 15 dense per-region rows of G2 got faster (0.683-0.979), and 19 of the 20 route rows, also dense chains (0.669-1.011), while the two all-five dense rows read 1.003 and 1.005, and the vary rows 0.896-1.412 and with the TLB set 0.962-1.112. Single rows are noisy on both boots: within one row the passes spread up to 12.218 ns on A and 11.172 ns on E, and the same chain's best differs between two processes of one boot (CPU 2's G2 and TLB-set rows, and on E the walk rows for the sparse chains) by up to 12.5% on the sparse, 5.4% on the dense and 22.9% on the vary chains on A, and by up to 13.1%, 27.8% and 8.5% on E.
- **The counts:** by the L2 arithmetic of E's check, the passes of E's core OCM rows with the prefetch counters count up to 0.48 L2 refills per load that neither prefetch event nor 0xA2 accounts for, where A's read at most 0.0157 (L3 power above, Coverage).
- **CME:** the CME's dense OCM chases read 0.850-0.929 times A's, the sparse 0.836-1.055, the vary 0.966-1.010 and the all-five rows 0.962-0.967.
- **Mesh counts (G6, `cmn-counts.csv`):** per cell, the sum of its eight data-flit counts reads 0.685-0.731 times A's from CPU 2 and 0.360-0.565 times from CPUs 4, 6 and 8, and `child_elapsed_ns` 0.938-0.967 and 0.857-0.922 times. These counters run for the whole command, chain build, flushes and unmap included.

## The G8 rows

- **The rows:** commands 123-138 (`log.txt` lines 140-155, after G7, with CPU 3 still offline), all on CPU 2, the same sixteen one-core L1 read and write rows as on boot C: for 4, 8, 16 and 24 KiB (1,024, 512, 256 and 176 passes, 5 reps, `--perf`), a read and a write row in the program's usual form, one kernel call per pass (`bandwidth-l1-passes.csv`), each followed by the same row with `--asm-passes`, all passes of a rep in one assembly call (`bandwidth-l1-asmpasses.csv`). They stay in the L1 (L1 data refills at most 0.0195 per line on E, 0.0199 on C), so on E they are a repeat check of C's rows, not an L3 result.
- **Their data rows,** counted here since the run's checker does not count a CSV's rows: `bash evidence/jibin/g8rows.sh` on the window's copy printed, for both files, `blocks=8 wrong_asm=0 backing=8 headers=8 counted_reps=40 best=8 perf_lines=0 bytes_4194304=30 bytes_4325376=10` (`evidence/runs/membench-jibin-010/g8rows.txt`), C's line, and run on the delivered files it prints the same. A separate count agrees: each file is 72 lines, 8 blocks of one command each (`asm_passes=0` in all 8 blocks of the passes file and `asm_passes=1` in all 8 of the asmpasses file), 40 rep rows with every counter column filled and `perf_cov` 1.0000, 8 best rows, `total_bytes` 4,194,304 per rep in 30 rows (4-16 KiB) and 4,325,376 in 10 (24 KiB), and no `# perf:` line. So neither file is empty or short, and the two are not swapped.
- **The best rows,** aggregate GB/s (1 GB = 1e9 bytes), the best of 5 reps, E with C in parentheses:

| Size, passes | Read, per-pass form | Read, `--asm-passes` | Write, per-pass form | Write, `--asm-passes` |
|---|---|---|---|---|
| 4 KiB, 1,024 | 40.910 (46.180) | 53.096 (53.103) | 26.589 (26.588) | 29.034 (29.873) |
| 8 KiB, 512 | 50.426 (50.234) | 57.890 (57.898) | 29.139 (29.543) | 30.434 (30.893) |
| 16 KiB, 256 | 56.004 (56.586) | 60.331 (60.249) | 30.494 (30.488) | 31.191 (31.428) |
| 24 KiB, 176 | 57.258 (57.962) | 60.586 (59.812) | 30.972 (30.973) | 31.558 (31.612) |

- **Against C:** 15 of the 16 rows read 0.972-1.013 times C's. The exception is the 4 KiB per-pass read, 40.910 against 46.180 GB/s (0.886), with its reps spreading 0.2% on E and 0.5% on C (E 40.844-40.910, C 45.936-46.180), 3.13-3.14 cycles per line against 2.78-2.79, and L1 data refills at most 0.0008 per line on both. So on that row E did not repeat C, and these files do not show why. The reps of one row spread up to 1.8% in E's per-pass rows and 5.7% in E's `--asm-passes` rows (C: 1.9% and 11.0%).

## The walk rows

- **The rows:** six files from CPU 2 with CPU 3 offline, commands 40-45 of 138 as on boots C and D (`log.txt` lines 50-55), right after CPU 2's TLB-set rows and before CPU 8's G2 rows. Each is the TLB-set row of the same chain with `--events walk`, which keeps cycles, 0x03, 0x17, 0xA2 and 0x34 DTLB_WALK and replaces the TLB set's 0x05 and 0x2D with 0x8188 DTLB_WALK_BLOCK and 0x818A DTLB_WALK_PAGE (columns `dtlb_walk_per_load`, `dtlb_walk_block_per_load`, `dtlb_walk_page_per_load`). Every pass row reads `perf_cov` 1.0000. By his uptime stamps they took 0.31 s (1.51 to 1.82 s), as on C.
- **Their data rows,** counted here since the run's checker passes an empty file: `latency-dram-walk-cpu2.csv`, the random 32 MiB chain on 4 KiB pages (`backing=4k`), has 2 pass rows (`fresh1` and `fresh2`, 524,288 loads each) and its best row; each `latency-ocm-region<r>-walk-cpu2.csv` (r = 0-4), the sparse chain over one 256 KiB region (`backing=ocm sparse=1`), has 7 pass rows (`fresh1` to `fresh7`, 64 loads each) and its best row. That is 37 pass rows and 6 best rows, as on C and D.
- **Beside C's and D's,** the walk columns per load over each file's passes:

| File | E: 0x34 | E: 0x8188; 0x818A | E best, ns | C: 0x34 | C best, ns | D best, ns |
|---|---|---|---|---|---|---|
| `latency-dram-walk-cpu2.csv` | 0.5113, 0.5118 | 0.0000; as 0x34 | 58.705 | 0.1849, 0.1850 | 56.726 | 58.725 |
| `latency-ocm-region0-walk-cpu2.csv` | 0.1562-1.9062 (nonzero in 7 of 7) | 0.0000; 0.0000 | 18.922 | 0-2.5781 (6 of 7) | 22.438 | 23.641 |
| `latency-ocm-region1-walk-cpu2.csv` | 0-0.9688 (5 of 7) | 0.0000; 0.0000 | 19.047 | 0.1562-2.6094 (7 of 7) | 20.938 | 23.109 |
| `latency-ocm-region2-walk-cpu2.csv` | 0-1.7969 (6 of 7) | 0.0000; 0.0000 | 17.937 | 0.5312-2.1719 (7 of 7) | 24.328 | 23.609 |
| `latency-ocm-region3-walk-cpu2.csv` | 0.1719-2.7969 (7 of 7) | 0.0000; 0.0000 | 23.016 | 0-1.3125 (6 of 7) | 24.391 | 26.734 |
| `latency-ocm-region4-walk-cpu2.csv` | 0.3125-1.9219 (7 of 7) | 0.0000; 0.0000 | 20.984 | 0.2344-2.3906 (7 of 7) | 24.656 | 27.641 |

- **On the 32 MiB stimulus:** 0x34 reads 0.5113 and 0.5118 walks per load, 0x818A the same and 0x8188 0.0000, so every walk ended in a page descriptor, as on 4 KiB pages it must (C: 0.1849 and 0.1850; D: 0.4381 and 0.4371, with 0x8188 0.0000 on both). E's TLB-set row of the same chain (command 24) walked 0.3655-0.3662 times per load (C: 0.3655-0.3669).
- **On the five OCM rows** (no contiguous entries on E: every map line reads `cont=0/64`): 0x34 counted walks in 32 of the 35 passes, 0.1562-2.7969 per load where nonzero (10-179 in a 64-load pass), while 0x8188 and 0x818A read 0.0000 in all 35. By the RTL's counting rules (boot C's README, The walk rows), 0x34 counts a walk when it starts, and 0x8188 and 0x818A count one only when it returns a translation to the core without a fault, so no walk 0x34 counted here returned one. On C, with the contiguous hint, 0x34 counted in 33 of 35 and 0x818A one walk in each of two passes (0.0156 per load in region 1's `fresh5` and region 2's `fresh7`); on D, with the prefetchers off, all three read 0 in every pass. The rows read 17.937-23.016 ns best (C: 20.938-24.656; D: 23.109-27.641).
- **0x8188 stays unvalidated:** it read 0 in every pass of the six walk files, and it has read nonzero on no boot. On E none of the walk rows' buffers had a contiguous or block entry (every map line `cont=0/64`, the 32 MiB stimulus on 4 KiB pages), so these zeros were expected and do not test it.

## OCM mappings

`dmesg.txt` has one line per `/dev/ocm` mapping, 115 in all (lines 204-318), in the form `membench_ocm: map pid=206 comm=latency va=0xffff8f223000 pa=0xe0000000 len=0x40000 prot=0x68000000000fc3 pte=0x1680000e0000fc3 cont=0/64 same=64/64`: the process, the user and physical addresses, the length, the protection, the first page-table entry as read back, how many of the mapping's entries carry the contiguous bit and how many share the first entry's attributes. These lines exist only in this file. The module's load line, `membench_ocm: /dev/ocm ready, pmu=1 cont=0` (line 202), shows the default mode, in which the kernel places each mapping and fills it with single 4 KiB entries, as boot A's module does. Each line carries the kernel-log time, and the lines tie to his OCM commands in `log.txt` by the order of their `pid` groups, one process per command.

- Every mapping is one whole 256 KiB region at its base: 23 each at 0xE0000000, 0xE0100000, 0xE0200000, 0xE0300000 and 0xE0400000, over 91 OCM commands (85 of one region, 6 of all five), all by `latency`, pids 206 to 983.
- Every mapping has `prot=0x68000000000fc3` (Normal write-back memory, inner shareable, user read-write, never executable) and is made of single 4 KiB page entries. Its `pte` (`0x1680000e0n00fc3` for region n) has bit 52, the contiguous bit, clear; C's `0x1780000e0n00fc3` differs from it only by that bit, and boot A's shorter line has no `pte` field.
- Every line of every command reads `cont=0/64 same=64/64`.
- Per line, `va - pa` modulo 16, 32 and 64 KiB is in the table below. It is 0 modulo 16 KiB on 23 of the 115 lines, modulo 32 KiB on 11 and modulo 64 KiB on 4 (boot A: 23, 8 and 5 of its 110), each the kernel's own placement for that process.
- By command: map lines 1-25 are G2 from CPU 2 (17 commands), 26-40 its TLB set (15), 41-45 the walk rows (5), 46-70 G2 from CPU 8 (17), 71-95 G4, the CME rows (17), and 96-115 G6, the route rows (20); map line k is `dmesg.txt` line 203 + k on this boot and on boot A.
- **Paired with boot A's 110 by command, not by line number:** A's 86 OCM commands are E's other 86 in the same order, so A's line k is E's line k up to 40 and E's line k+5 from 41 on, E's lines 41-45 being the walk rows; all 110 pairs name the same command line and region (derived for this README from both boots' `log.txt` and `dmesg.txt`). Only 5 pairs share their `va - pa` modulo 64 KiB; both lines of a pair are multiples of 16 KiB in 5 pairs, of 32 KiB in 2 and of 64 KiB in none.
- **The table:** one row per command (the five lines of an all-five command share one value on both boots), with E's and A's `va - pa` modulo 16, 32 and 64 KiB, in KiB, and the file's best over A's (the CME rows: the CME's best).

| E map line(s) | A map line(s) | File | E: `va - pa` mod 16, 32, 64 KiB | A: the same | E/A, best |
|---|---|---|---|---|---|
| 1 | 1 | `latency-ocm-region0-dense-cpu2.csv` | 12, 12, 12 | 4, 4, 36 | 0.942 |
| 2 | 2 | `latency-ocm-region0-cpu2.csv` | 4, 4, 36 | 0, 16, 48 | 0.892 |
| 3 | 3 | `latency-ocm-region0-vary-cpu2.csv` | 0, 0, 0 | 12, 28, 28 | 0.976 |
| 4 | 4 | `latency-ocm-region1-dense-cpu2.csv` | 8, 8, 8 | 0, 16, 16 | 0.772 |
| 5 | 5 | `latency-ocm-region1-cpu2.csv` | 0, 0, 32 | 4, 4, 36 | 0.833 |
| 6 | 6 | `latency-ocm-region1-vary-cpu2.csv` | 0, 16, 16 | 0, 16, 48 | 0.973 |
| 7 | 7 | `latency-ocm-region2-dense-cpu2.csv` | 12, 12, 12 | 12, 28, 60 | 0.768 |
| 8 | 8 | `latency-ocm-region2-cpu2.csv` | 12, 28, 28 | 4, 20, 52 | 0.800 |
| 9 | 9 | `latency-ocm-region2-vary-cpu2.csv` | 12, 28, 60 | 12, 28, 60 | 1.198 |
| 10 | 10 | `latency-ocm-region3-dense-cpu2.csv` | 12, 28, 28 | 4, 4, 4 | 0.915 |
| 11 | 11 | `latency-ocm-region3-cpu2.csv` | 8, 8, 40 | 12, 12, 44 | 0.771 |
| 12 | 12 | `latency-ocm-region3-vary-cpu2.csv` | 0, 0, 32 | 12, 12, 44 | 0.919 |
| 13 | 13 | `latency-ocm-region4-dense-cpu2.csv` | 0, 0, 32 | 0, 0, 32 | 0.683 |
| 14 | 14 | `latency-ocm-region4-cpu2.csv` | 12, 28, 28 | 0, 16, 16 | 0.691 |
| 15 | 15 | `latency-ocm-region4-vary-cpu2.csv` | 12, 12, 44 | 12, 12, 12 | 0.912 |
| 16-20 | 16-20 | `latency-ocm-all5-dense-cpu2.csv` | 8, 8, 40 | 8, 8, 8 | 1.003 |
| 21-25 | 21-25 | `latency-ocm-all5-cpu2.csv` | 4, 20, 20 | 12, 28, 60 | 0.965 |
| 26 | 26 | `latency-ocm-region0-dense-tlb-cpu2.csv` | 4, 4, 4 | 12, 12, 44 | 0.915 |
| 27 | 27 | `latency-ocm-region0-tlb-cpu2.csv` | 12, 12, 44 | 8, 24, 24 | 0.857 |
| 28 | 28 | `latency-ocm-region0-vary-tlb-cpu2.csv` | 0, 16, 16 | 12, 12, 12 | 0.962 |
| 29 | 29 | `latency-ocm-region1-dense-tlb-cpu2.csv` | 12, 28, 60 | 8, 24, 24 | 0.822 |
| 30 | 30 | `latency-ocm-region1-tlb-cpu2.csv` | 4, 4, 4 | 12, 28, 28 | 0.791 |
| 31 | 31 | `latency-ocm-region1-vary-tlb-cpu2.csv` | 0, 0, 32 | 8, 8, 8 | 1.101 |
| 32 | 32 | `latency-ocm-region2-dense-tlb-cpu2.csv` | 4, 20, 52 | 4, 20, 52 | 0.979 |
| 33 | 33 | `latency-ocm-region2-tlb-cpu2.csv` | 0, 0, 0 | 12, 12, 12 | 0.780 |
| 34 | 34 | `latency-ocm-region2-vary-tlb-cpu2.csv` | 8, 8, 40 | 12, 28, 28 | 1.112 |
| 35 | 35 | `latency-ocm-region3-dense-tlb-cpu2.csv` | 4, 4, 4 | 8, 24, 56 | 0.746 |
| 36 | 36 | `latency-ocm-region3-tlb-cpu2.csv` | 12, 12, 12 | 8, 24, 56 | 0.860 |
| 37 | 37 | `latency-ocm-region3-vary-tlb-cpu2.csv` | 12, 12, 44 | 0, 16, 16 | 1.072 |
| 38 | 38 | `latency-ocm-region4-dense-tlb-cpu2.csv` | 8, 24, 56 | 0, 0, 0 | 0.685 |
| 39 | 39 | `latency-ocm-region4-tlb-cpu2.csv` | 12, 28, 60 | 8, 24, 56 | 0.854 |
| 40 | 40 | `latency-ocm-region4-vary-tlb-cpu2.csv` | 4, 20, 20 | 8, 24, 56 | 1.005 |
| 41 | - | `latency-ocm-region0-walk-cpu2.csv` | 4, 4, 4 | - | - |
| 42 | - | `latency-ocm-region1-walk-cpu2.csv` | 0, 16, 16 | - | - |
| 43 | - | `latency-ocm-region2-walk-cpu2.csv` | 0, 16, 48 | - | - |
| 44 | - | `latency-ocm-region3-walk-cpu2.csv` | 12, 28, 28 | - | - |
| 45 | - | `latency-ocm-region4-walk-cpu2.csv` | 0, 0, 32 | - | - |
| 46 | 41 | `latency-ocm-region0-dense-cpu8.csv` | 8, 24, 24 | 0, 0, 0 | 0.761 |
| 47 | 42 | `latency-ocm-region0-cpu8.csv` | 4, 4, 36 | 8, 24, 56 | 0.831 |
| 48 | 43 | `latency-ocm-region0-vary-cpu8.csv` | 4, 20, 52 | 0, 0, 32 | 0.969 |
| 49 | 44 | `latency-ocm-region1-dense-cpu8.csv` | 12, 12, 44 | 12, 28, 28 | 0.710 |
| 50 | 45 | `latency-ocm-region1-cpu8.csv` | 0, 16, 48 | 4, 4, 36 | 0.937 |
| 51 | 46 | `latency-ocm-region1-vary-cpu8.csv` | 8, 8, 8 | 8, 8, 40 | 1.118 |
| 52 | 47 | `latency-ocm-region2-dense-cpu8.csv` | 4, 4, 4 | 8, 24, 24 | 0.685 |
| 53 | 48 | `latency-ocm-region2-cpu8.csv` | 12, 28, 28 | 0, 0, 0 | 0.816 |
| 54 | 49 | `latency-ocm-region2-vary-cpu8.csv` | 12, 12, 12 | 0, 16, 16 | 1.015 |
| 55 | 50 | `latency-ocm-region3-dense-cpu8.csv` | 8, 24, 24 | 12, 12, 12 | 0.751 |
| 56 | 51 | `latency-ocm-region3-cpu8.csv` | 4, 20, 52 | 12, 28, 28 | 0.870 |
| 57 | 52 | `latency-ocm-region3-vary-cpu8.csv` | 0, 0, 32 | 0, 16, 16 | 0.896 |
| 58 | 53 | `latency-ocm-region4-dense-cpu8.csv` | 12, 28, 60 | 4, 20, 20 | 0.884 |
| 59 | 54 | `latency-ocm-region4-cpu8.csv` | 12, 28, 28 | 12, 28, 28 | 1.096 |
| 60 | 55 | `latency-ocm-region4-vary-cpu8.csv` | 12, 12, 12 | 0, 0, 32 | 1.412 |
| 61-65 | 56-60 | `latency-ocm-all5-dense-cpu8.csv` | 4, 4, 4 | 0, 16, 16 | 1.005 |
| 66-70 | 61-65 | `latency-ocm-all5-cpu8.csv` | 12, 28, 28 | 8, 8, 40 | 0.914 |
| 71 | 66 | `cme-latency-ocm-region0-dense.csv` | 4, 4, 4 | 0, 16, 48 | 0.929 |
| 72 | 67 | `cme-latency-ocm-region0.csv` | 12, 28, 28 | 12, 12, 12 | 1.047 |
| 73 | 68 | `cme-latency-ocm-region0-vary.csv` | 0, 0, 0 | 8, 8, 40 | 0.966 |
| 74 | 69 | `cme-latency-ocm-region1-dense.csv` | 8, 8, 40 | 8, 24, 56 | 0.920 |
| 75 | 70 | `cme-latency-ocm-region1.csv` | 0, 0, 32 | 0, 0, 0 | 0.836 |
| 76 | 71 | `cme-latency-ocm-region1-vary.csv` | 12, 28, 60 | 4, 20, 52 | 0.973 |
| 77 | 72 | `cme-latency-ocm-region2-dense.csv` | 4, 4, 36 | 8, 24, 24 | 0.886 |
| 78 | 73 | `cme-latency-ocm-region2.csv` | 8, 8, 8 | 12, 12, 12 | 1.039 |
| 79 | 74 | `cme-latency-ocm-region2-vary.csv` | 0, 16, 48 | 0, 16, 16 | 0.987 |
| 80 | 75 | `cme-latency-ocm-region3-dense.csv` | 8, 8, 40 | 4, 20, 20 | 0.850 |
| 81 | 76 | `cme-latency-ocm-region3.csv` | 8, 24, 24 | 12, 28, 60 | 1.055 |
| 82 | 77 | `cme-latency-ocm-region3-vary.csv` | 4, 4, 4 | 4, 20, 20 | 1.010 |
| 83 | 78 | `cme-latency-ocm-region4-dense.csv` | 12, 12, 44 | 8, 8, 40 | 0.877 |
| 84 | 79 | `cme-latency-ocm-region4.csv` | 4, 4, 36 | 12, 28, 60 | 1.034 |
| 85 | 80 | `cme-latency-ocm-region4-vary.csv` | 0, 16, 16 | 12, 12, 44 | 0.999 |
| 86-90 | 81-85 | `cme-latency-ocm-all5-dense.csv` | 4, 4, 4 | 12, 28, 60 | 0.967 |
| 91-95 | 86-90 | `cme-latency-ocm-all5.csv` | 12, 12, 44 | 4, 4, 4 | 0.962 |
| 96 | 91 | `latency-ocm-region0-route-cpu2.csv` | 12, 12, 44 | 4, 4, 36 | 0.943 |
| 97 | 92 | `latency-ocm-region1-route-cpu2.csv` | 0, 16, 16 | 8, 24, 24 | 0.914 |
| 98 | 93 | `latency-ocm-region2-route-cpu2.csv` | 0, 16, 48 | 8, 8, 8 | 0.938 |
| 99 | 94 | `latency-ocm-region3-route-cpu2.csv` | 12, 28, 28 | 4, 20, 52 | 0.833 |
| 100 | 95 | `latency-ocm-region4-route-cpu2.csv` | 12, 12, 44 | 12, 12, 44 | 0.901 |
| 101 | 96 | `latency-ocm-region0-route-cpu4.csv` | 0, 16, 16 | 4, 20, 20 | 0.693 |
| 102 | 97 | `latency-ocm-region1-route-cpu4.csv` | 4, 4, 36 | 12, 28, 28 | 0.721 |
| 103 | 98 | `latency-ocm-region2-route-cpu4.csv` | 4, 20, 52 | 12, 28, 28 | 0.749 |
| 104 | 99 | `latency-ocm-region3-route-cpu4.csv` | 12, 12, 44 | 4, 4, 4 | 0.790 |
| 105 | 100 | `latency-ocm-region4-route-cpu4.csv` | 0, 16, 16 | 8, 24, 56 | 0.798 |
| 106 | 101 | `latency-ocm-region0-route-cpu6.csv` | 4, 4, 36 | 12, 12, 44 | 1.011 |
| 107 | 102 | `latency-ocm-region1-route-cpu6.csv` | 12, 28, 60 | 0, 16, 48 | 0.716 |
| 108 | 103 | `latency-ocm-region2-route-cpu6.csv` | 0, 16, 16 | 4, 4, 4 | 0.708 |
| 109 | 104 | `latency-ocm-region3-route-cpu6.csv` | 12, 28, 28 | 4, 20, 52 | 0.857 |
| 110 | 105 | `latency-ocm-region4-route-cpu6.csv` | 8, 8, 8 | 4, 20, 52 | 0.669 |
| 111 | 106 | `latency-ocm-region0-route-cpu8.csv` | 0, 0, 0 | 12, 28, 28 | 0.750 |
| 112 | 107 | `latency-ocm-region1-route-cpu8.csv` | 4, 20, 52 | 4, 20, 20 | 0.855 |
| 113 | 108 | `latency-ocm-region2-route-cpu8.csv` | 8, 8, 40 | 0, 0, 0 | 0.828 |
| 114 | 109 | `latency-ocm-region3-route-cpu8.csv` | 8, 8, 40 | 4, 20, 20 | 0.703 |
| 115 | 110 | `latency-ocm-region4-route-cpu8.csv` | 12, 12, 12 | 8, 8, 8 | 0.775 |

## The run

- Queue request 4746, submitted on ga13pd01 at 10:09:26 UTC on 2026-11-05 and granted at 10:09:54 UTC (02:09:54 PST), ran on ga13pd01. The init started at 10:47:27 UTC, his script ran from 10:47:51 to 13:18:12 UTC, and the emulator was released at 13:19:26 UTC. The emulator ran 2,780 wall seconds per chip second by its own 10 ms ticks (boot C: 2,776; boot A: 2,778). E launched once boot C had passed its checker and his prefetchers-on check, with C's 3.461 s well inside the 12 s guard (`docs/PLAN.md` section 8, E's launch check).
- This box's init (PID 1) loaded the module with no parameters and ran `/bin/sh /opt/membench/cache-mem-perf-b79dffa/run_followup.sh --out /opt/membench/cache-mem-perf-b79dffa/results/bootE` as root, pinned to CPU 2 under SCHED_FIFO priority 10, with RT throttling off, as on boots A and C. It exited 0 after 3.250 s (`MB RUN end status=exit:0 ns=3249645413`), against his estimator's 3.773 s, of which G8 is 0.247 s (`evidence/jibin/prequeue-b79dffa.txt`), boot C's 3.461 s and boot A's 2.830 s. By his uptime stamps E's commands started 0.01-0.21 s earlier than C's: G7's between 3.19 and 3.33 s (C: 3.28 and 3.51 s), and G8's between 3.36 and 3.44 s (C: 3.56 and 3.64 s). The 12 s hang guard did not fire. The results window came back whole (`MB WIN ok ... files=116 trunc=0`: his 113 files, `init.log`, `out.txt` and `dmesg.txt`).
- His script took CPU 3 offline before G1 and brought it back at the end (`cpu3 online=0`, `cpu3 online=1`, `log.txt` lines 4 and 156).
- **The console cap:** his stdout is 158 lines, 21,089 bytes (`MB RUN end ... bytes=21089`). The init echoes at most 16,384 bytes of it to the console, counting each line at most 120 characters plus its newline (`MB_ECHO_MAX` and `MB_LINE_MAX` in this box's `membench-init.c`), so lines 1-147 reached the console, 124 of them cut short (ending in `~`), and at 13:14:28 UTC the init printed `MB OUT cap=16384 rest-in-window`. Lines 148-158, G8's last eight commands, `cpu3 online=1` and his two closing lines, reached only the window, which keeps everything: its `out.txt` equals his `log.txt` (`cmp`), and this README quotes them.
- **The two added lines:** this box's patch `cache-mem-perf-b79dffa-clusterpwrstat.patch`, which the snapshot's `MANIFEST.md` lists with sha256 `350080a766462a3748bdfaf08750837ebdf8bd63c5528cc5bd1ba6ffa8f464e4`, "applied to the copy with `patch -p1 -N`, no fuzz or offset allowed", adds lines 114 and 117 of the installed `run_followup.sh` (sha256 `0dfbe227a11f1788e4a43ff0dfcfd5b7641d3a7f52f5298679eb39a8b72e60a3`): `say "# box clusterpwrstat before l3: $(cat /sys/module/membench_ocm/parameters/clusterpwrstat 2>&1)"` and the same with `after`, so an error from `cat` would replace the value. These are boot C's patch and lines. The snapshot's `membench/README.md` names only the `7921962` patch (its lines 10 and 31), while its `MANIFEST.md` names this one.
- **The file they read:** a read-only parameter of this box's `/dev/ocm` module (asimov-os `89cfd32`, module sha256 `937077c761e5227b9799f2b2fd4a609705737d71b9bebe96b0320fa2f548e577`, boots B's, C's and D's file), which by the snapshot's `MANIFEST.md` "returns IMP_CLUSTERPWRSTAT_EL1 (S3_0_C15_C3_7) of CPU 2's cluster as `0x<hex>`, read on CPU 2 at EL2 each time the file is read (its only MRS of an IMPLEMENTATION DEFINED register, and no MSR of one)". The read cannot trap (`evidence/jibin/pwrstat-read-verdict.txt`), given the kernel at EL2 that `dmesg.txt` shows.
- **The SCP rebuild:** SCP 0.48.0-nopcie-l3.1, commit `28663ab` on `e361a83` under the local tag `scp-v0.48.0-nopcie-l3.1`, never pushed (patch `evidence/firmware/0002-asimov_system-stage-the-full-L3-operating-mode-for-c.patch`, sha256 `9c6db588d1789772fa0c5422c627c047b64c6aaae302ea5bc93f43dc5a860cfc`; package sha256 `a8cca78ab5c4198ebf33f28cfb88ac0133d6ca640488f147e86e78d8a5c35a30`, which the snapshot's `MANIFEST.md` names; The SCP above).
- Snapshot `membench-jibin-b79dffa-l3`, built at asimov-os `02074d7` (`MANIFEST.md` sha256 `8ccebc1d5bdbeb0b2a62d2935a2ad60b46b7dc87aeb0bff12d558e61fd8e87a8`, which the run's launch plan, `evidence/runs/membench-jibin-010/plan.json`, pins with the debug SCP drop; AP boot image `palladium/ap_composite.bin`, which holds BL31, the kernel, the device tree and the root file system, sha256 `40d01472fe0265f153bbe5d7c8a44f6e292359b8d357c7ae19af67032560c8fe`). `evidence/bundle/r4-build/snapshots-l3-checks.txt` finds nothing unexpected against boot C's snapshot (Against boot C above) or boot A's: against A, `tfa/`, `kernel/`, `os/` and `sam/` are byte-identical, and the SCP, his folder, the box patch, the module and the init differ.
- The run's checker passed all 36 of its rows (`JIBIN_CHECK PASS`, `evidence/runs/membench-jibin-010/judge-jibin.txt`): firmware banners (SCP `28663ab (0.48.0-nopcie-l3.1)`, TF-A `3b3df18 (0.35.0)`), kernel, CPU layout, huge pages and `/dev/ocm` as on boot A; `ocm=1 sme2=1 hugepages_free=256`; the program `cache-mem-perf-b79dffa/run_followup.sh` with `out=.../results/bootE`; all 113 expected files; CPU 3 offline and back; no `# perf:` line; the mesh map in `sysinfo.txt`; `cmn-counts.csv` with 20 counted commands of 8 events each; one mapping line for each of the 115 OCM mappings, each `cont=0/64`; both clusterpwrstat lines; nothing on stderr; and a row new on this boot (C had 35), `scp_l3_staging`: the five staging lines once each and in order, their values reported, not judged. What it does not check is checked in this README: whether E's L3 was on (E's check, L3 power), where the staging lines sit in the SCP's sequence (The SCP), the commit, which the launched `MANIFEST.md`, the checker's program row and the 113 files name, the map lines command by command (OCM mappings), and a CSV's data rows (the walk and G8 files).

## Platform facts

These equal boot A's except the SCP, the `/dev/ocm` module (boots B's, C's and D's file, loaded with no parameters) and his commit's programs. This boot's `sysinfo.txt` differs from A's only in times, memory counts, the initrd's size and the module's load line (`pmu=1 cont=0` against `pmu=1`), and from C's only in times, memory counts and that load line (`cont=1` on C). Its `dmesg.txt` differs from A's the same way, apart from the map lines and two of the kernel's buddy-audit entry counts (74 and 81 against 75 and 82).

- **Emulator image:** GA13 release `a10280100`, build `hemi_rtws_tlm`, RTL `0d9e214eb43b` (main, 2026-10-28), from this box's private copy. Real C1-Nano cores and clusters with their CMEs, the CMN-S3 mesh with its SLC and OCM; the matmul array is cut to one column.
- **Firmware:** SCP 0.48.0-nopcie-l3.1 (`28663ab` on `e361a83`, debug build; this box's local build of scp-v0.48.0 with PCIe0 held and the full-L3 operating mode staged for the clusters of CPUs 2-9, never pushed) and TF-A 0.35.0 (`3b3df18`, debug; BL31 debug sha256 `c650bd0e928ff880527f7f7aea982b7ceb34efd7df04480b589bd3df04b60b08`), boot A's TF-A file.
- **Kernel:** Linux 6.18.36 built from asimov-os `v0.0.17`'s config and patches plus transparent huge pages (madvise), hugetlbfs and debugfs, its `Image` (sha256 `e298e0e0f21437b05dcea58c40a9d69bcac1efd3c26721d5bcea8628391531f8`) boot A's file; command line in `sysinfo.txt`.
- **CPU placement:** ten C1-Nano cores, all online at boot; CPUs 2-9 isolated from the scheduler and `nohz_full`, device interrupts on CPUs 0-1. Each pair {2,3}, {4,5}, {6,7}, {8,9} shares an L2, an L3, a CME and one mesh port.
- **Clock:** core 2.000 GHz against the 1 GHz generic timer: 4.01 cycles per 2.002 ns load on the 4 KiB control.
- **Caches:** as `sysinfo.txt` lists them for CPU 2 (lines 100-103): L1 data and L1 instruction 32K each (`shared_cpu_list=2`), L2 128K and L3 256K (`shared_cpu_list=2-3`), 64-byte lines. On this boot the SCP staged the full-L3 operating mode for clusters 1-4 (CPUs 2-9) before they powered on, and the L3 of CPU 2's cluster was in use as a cache (L3 power above). The SLC is five home nodes of 1 MiB; the firmware locks 4 of 16 ways of each as OCM.
- **OCM:** five regions of 256 KiB at 0xE0000000 + n MiB, mapped by this box's `/dev/ocm` module (sha256 `937077c761e5227b9799f2b2fd4a609705737d71b9bebe96b0320fa2f548e577`) loaded with no parameters (`cont=0`): the kernel places each mapping and fills it with single 4 KiB entries, as on boot A.
- **PMU:** `armv9_c1_nano`, 21 counters (20 plus the cycle counter; `dmesg.txt` line 189); mesh PMU `arm_cmn_0`.
- **Huge pages:** 256 pages of 2 MiB reserved at boot; MemTotal 1,833,848 kB.
- **Programs:** his Makefile with the asimov-os `v0.0.17` SDK's GCC (Arm GNU Toolchain 14.2.Rel1, 14.2.1) and his default flags, all static. From the snapshot's `MANIFEST.md`: `latency` sha256 `cf176f67f3973a49fa28fa135ff999a639896e3c64ad94775455bcbdc7b77735`, `bandwidth` `f21ade7aa62756b27e0757384f75f773f694d7602e43beb7e46e3a14cd153a57`, `bandwidth_r2` `2570e5ba9f604fc3a14550341c48ad34857458787345090e18e969d7d7dfa6c6`, `bandwidth_r3` `aface7f76e8cceb38364c40cbff120740f64c37891f753879334c7eb5d5d8a99`, `cmncount` `bb0d30be9499053cbe4a78f0fab49018b6abeda9de0d7c6574ba8575f3a53d41`. `latency`, `bandwidth` and `bandwidth_r3` are boot C's once stripped (6 bytes of the assembler's temporary object name differ; `evidence/bundle/r4-build/snapshots-l3-checks.txt`), and `bandwidth_r2` and `cmncount` are C's byte for byte (and A's, B's and D's).
- **DRAM caveat:** AP DRAM on this image is an embedded emulator memory, not LPDDR5X, so no DRAM latency or bandwidth number here is silicon-like.
- No real-time clock: every time his script read shows 1970.
