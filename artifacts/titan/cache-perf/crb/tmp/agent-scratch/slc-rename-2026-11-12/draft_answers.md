# Draft answers to the author's five questions (2026-11-12)

These are drafts. Every number must be checked against the raw file that is named for it.
Paths: `C` = `/home/jhan/workspace/titan/cache-perf/crb`, `B` = `/home/jhan/workspace/titan/cache-perf/bench`.

## A1. What is a "flit"? Is it a known technical term?

Claim A1.1. Yes. "Flit" is short for "flow control unit". It is the unit that a link of an on-chip network moves in one step.

Claim A1.2. Arm's CHI specification defines it. CHI (Coherent Hub Interface) is the protocol of CRB's mesh ports and links. Page 32: "FLow control unIT (Flit) is the smallest flow control unit. A packet can be made up of one or more flits." and "For CHI, all packets consist of a single flit." Page 455, section B13.3: "A flit is the basic unit of transfer in the Link layer." Source: AMBA CHI specification, IHI 0050 issue H, local copy `/home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf` (text copy: `/home/jhan/workspace/vendor-resources/ARM/md/IHI0050H_amba_chi_architecture_spec.md`, lines 1385 to 1391 and 21119).

Claim A1.3. In CRB's mesh one data flit carries 32 B of data (256 bits). So one 64 B cache line needs two data flits. Source: CMN S3 TRM, Table A-2 page 2120 ("Data_Width ... Fixed to 256"), local copy `C/refs/arm-cmn-s3-r2p3-trm-107858.pdf`.

Claim A1.4. The term is also used outside Arm. PCIe 6.0 and CXL have a "flit mode". Source: Rambus glossary entry "FLIT (Flow Control Unit)", https://www.rambus.com/?p=65936 (web search result of 2026-11-12, not opened as a page).

## A2. "We measured 80 GB/s, but the hypothesis is 64 GB/s. That does not look right."

Claim A2.1. The two numbers are counted at two different places. The 80 GB/s (78 rounded) is counted at the loops. It is every byte that the two partner cores read. The 64 GB/s is a hypothesis about the bytes that cross the shared port in one direction.

Claim A2.2. Measured pair read rates at 8 MiB per core: 77.51 GB/s with the asm loop on CPUs 0 and 1 (`C/results/followup-20261030T194205Z/asm.csv` line 74) and 78.26, 77.87 and 78.45 GB/s with the read loop compiled from C on CPUs 0,1 and 2,3 and 4,5 (`pair.csv` lines 6, 30 and 48 in the same folder).

Claim A2.3. With a buffer of 8 MiB a part of the lines never crosses the port. The core's own L2 serves them. For one core alone this was measured in one case (r8M-c2, part 5, 2026-11-02, file `C/results/sudo-20261102T211150Z/writepath.csv`): the loop read 71 GB/s (69.63 to 71.17 GB/s in the nine 2 s runs), and the port carried 58.7 GB/s toward the core (0.92 data flits of 32 B per mesh cycle of 2.0 GHz). The port count and the loop rate are from the same pair of runs. The script `C/tmp/agent-scratch/spec-row-2026-11-11/port_counts.py` recomputes the counts.

Claim A2.4. Three counters that ran for the whole run give the same share for one core alone: 1.653 data flits per line at the port (2 would mean every line), 0.826 L2 refills per line, and 0.83 accesses to the SLC per line (`C/results/sudo-20261102T054936Z/writebw.csv`, case asmread-8M-1). So 0.83 of the lines cross the port and 0.17 are L2 hits.

Claim A2.5. If two partner cores have the same share of 0.83, the 77.5 to 78.5 GB/s at the loops is 64.1 to 64.9 GB/s at the port (est.). That is at or just above 64 GB/s. No run counted the share for two partner cores. So the 80 GB/s does not contradict the 64 GB/s, and it does not confirm it.

Claim A2.6. A run in which every line must cross the port gives the cleanest comparison. With a buffer of 1 GiB one writer sends 2.00 bus writes of 32 B per 64 B line (1.9982, case w1G-c2). Two partner writers together write 63.18 GB/s and one writer alone writes 62.99 GB/s (asm loop, `asm.csv` lines 184 and 169). Both are just below 64 GB/s.

Claim A2.7. The loop compiled from C stops at the same pair total. At 1 GiB one compiled writer writes 44.78 GB/s, two partner writers write 63.19 GB/s together, and four writers on two pairs write 113.25 GB/s (`C/results/20261030T193108Z/bandwidth.csv` lines 218, 232 and 246; the sweep used `--cpus 0-119`, so two threads are CPUs 0 and 1, `B/bandwidth.c` line 408). Two times 44.78 would be 89.6 GB/s. So the pair total of 63.2 GB/s is a limit of the pair, not of one loop.

Claim A2.8. Writes at 8 MiB. Two partner writers write 81.41 to 82.34 GB/s at the loops (`asm.csv` line 109 and the nine 2 s runs of case w8M-c2c3). One writer alone sends 1.5241 bus writes per line, not 2 (case w8M-c2). With that count the pair rate is 62.0 to 62.7 GB/s at the port (est.).

Claim A2.9. Summary. At the loops the pair limit is a different number in each test: 63 GB/s (writes at 1 GiB), 78 GB/s (reads at 8 MiB) and 82 GB/s (writes at 8 MiB). Converted to bytes at the port, all three are 62 to 65 GB/s (est.). That is the reason for the hypothesis of 64 GB/s. The conversion for two partner cores uses counts of one core alone. That is why it stays a hypothesis.

Text diagram for the reply:

```
two partner cores read 8 MiB each

loops: 78 GB/s --+-- 17 % from each core's own L2 : 13 GB/s (est.)
(measured)       +-- 83 % through the pair port   : 64 to 65 GB/s (est.)
                                       hypothesis for the port: at most 64
```

## A3. Replacement statements for the older statements (proposals, not applied)

For the cause there is no definitive replacement. The measured part can be replaced definitively. Each proposal below has a measured part and a hypothesis part.

### A3.1 Report line 214 and line 380: "For DRAM streams the port is not the limit, because DRAM latency limits each core first (2 threads at 1 GiB get 53 GB/s paired or not)" and "For DRAM traffic the port is not the limit: 2 threads at 1 GiB get 53 GB/s whether paired or not."

Proposed text:

"DRAM reads and DRAM writes differ. Reads: two partner cores read 52.6 GB/s together at 1 GiB, and two cores on different meshes read 54.9 GB/s (read loop compiled from C). One core alone reads 28.2 GB/s. So a second reader on the same pair adds 24.4 GB/s. Writes: two partner cores write 63.2 GB/s together at 1 GiB, and one core alone writes 63.0 GB/s (asm loop). So a second writer on the same pair adds 0.2 GB/s. Four writers on two pairs write 113 GB/s. So two partner writers share one limit at 1 GiB. What this limit is was not measured. Hypothesis: it is the pair port at 64 GB/s in each direction (see "Open items")."

Sources: `pair.csv` lines 66 and 72; `C/results/20261030T193108Z/bandwidth.csv` line 214; `asm.csv` lines 169, 184 and 199.

### A3.2 Report line 214: "For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2. That is about 28 B per core cycle (est. from 78 GB/s at 2.8 GHz). It is the reason one thread per pair gets 1.6 to 1.7 times more SLC bandwidth than two threads on a pair."

Proposed text:

"For software: two threads on partner cores that both read from the SLC get about 78 GB/s together (77.5 to 78.5 GB/s in four runs with 8 MiB each). One thread alone gets 67 GB/s. Two threads on cores of different pairs get 125 to 134 GB/s. So one thread per pair gets 1.6 to 1.7 times the SLC read bandwidth of two threads on one pair. The 78 GB/s is counted at the loops. It includes the lines that each core takes from its own L2. Where the shared limit sits was not measured. Hypothesis: the pair port passes at most 64 GB/s in each direction (see "Open items")."

Sources: `asm.csv` lines 67, 74 and 307; `pair.csv` lines 6, 12, 18, 24, 30, 36, 42, 48 and 54. The sentence "about 28 B per core cycle" is dropped: the port belongs to the mesh, and the mesh clock is 2.0 GHz, not 2.8 GHz.

### A3.3 Report line 289: "The single-writer limit is inside the core."

Proposed text:

"At 8 MiB the limit of one writer is not on the shared path. One writer reaches 71 to 73 GB/s. The same port passes more when the partner core also writes: 82 GB/s at the loops. Four writers on four ports reach 229 GB/s. The links out of the crosspoint show no credit stalls, and the home nodes show no data stalls. So by elimination the limit is in the core (hypothesis and test as before). At 1 GiB this does not hold. One writer reaches 63.0 GB/s, and two partner writers together reach 63.2 GB/s. So at 1 GiB one writer already uses the whole limit that the pair shares. Where that limit sits was not measured. Hypothesis: it is the pair port (one writer sends 1.96 × 10^9 bus writes per second, which is 0.98 per mesh cycle (est.))."

Sources: `asm.csv` lines 102, 109, 169 and 184; the nine 2 s runs of cases w8M-c2, w8M-c2c3 and w8M-c2c4c6c8 in `writepath.csv` (70.37 to 71.34, 81.41 to 82.05 and 228.21 to 229.83 GB/s); case w1G-c2 for the bus writes.

## A4. What does "1 GiB" mean in "Two partner cores together wrote 63.2 GB/s at 1 GiB"?

Claim A4.1. It is the buffer size of each thread. Each thread reads or writes its own buffer of that size again and again. Sources: `B/bandwidth.c` line 4 ("Every thread owns its buffers (allocated and first-touched by that thread)"), option `--bytes`, and the column `bytes_per_thread` of the result files (`asm.csv` line 175: `threads=2 bytes_per_thread=1073741824`).

Claim A4.2. Two partner cores "at 1 GiB" therefore use 2 GiB in total. A buffer of 1 GiB is far larger than the 128 MiB SLC. The report uses 8 MiB as the buffer size for the SLC tests and 1 GiB for the DRAM tests (caption at report line 265: "Footprints: L1 = 32 KiB, L2 = 1 MiB, SLC = 8 MiB, DRAM = 1 GiB per thread").

Claim A4.3. The report now says this in three places: line 421 (open item, where the sizes are first used), line 437 (the sentence that the author quoted) and line 457 ("Words used here", entry "GB/s, TB/s").

## A5. Where are F1 to F21?

Claim A5.1. They are not in the report. They are in the record file `/home/jhan/tmp/update-crb-memory-hierarchy.md`, section "6. Found and not changed", lines 350 to 376. Section 6 of the report is "Latency", which is a different document.
