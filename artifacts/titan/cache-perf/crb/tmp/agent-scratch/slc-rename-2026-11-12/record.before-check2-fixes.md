# Update record: crb-memory-hierarchy.html, 2026-11-11

## Short version

The first figure of the report now has two aligned rows of boxes, "Measured" and "Spec", and every text change in the request is made.
Three questions of the request led to corrections that go beyond the listed text, and the next section names them.
After the review loop the author's decisions and comments of 2026-11-12 were applied, among them Arm's name "SLC" in place of "mesh cache" (section 10).

## The three corrections

- The clock of the mesh (the on-chip interconnect) is 2.0 GHz. The measurement of 2026-11-02 already contained this value. The report said that the value was not known.
- The report said that the core has five pipelines for loads and stores. Arm's guide shows four that start loads and stores, and two more that carry store data.
- The machine code of the read loop compiled from C was read on CRB (the server that the report measures). The report had a hypothesis in two parts for the low rate of this loop. The first part is confirmed: the loop does one vector add per 16 B load. The second part is a limit of two vector adds per cycle. It does not fit the measured rate: it allows 89.6 GB/s, and the loop reaches 66.8 GB/s.

## Words used here

- **Report**: `crb-memory-hierarchy.html`, the file that this update changes.
- **Request**: the Notion page "Scratch", last edited on 2026-11-11 at 19:48 UTC and read a few minutes later [Ref1].
- **CRB**: the Arm Phoenix reference server that the report measures.
- **Kit**: Arm's welcome kit for CRB, a folder of documents, firmware and tools at `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit`.
- **SOG**: Arm's Software Optimization Guide for the Neoverse V3AE core [Ref2].
- **TRM**: Arm's Technical Reference Manual for CMN S3 [Ref3].
- **SVK user guide**: Arm's user guide for the CRB System Validation Kit, revision 3.0, written for firmware 0.9.0 [Ref4].
- **Mesh, CMN**: Arm's Coherent Mesh Network, the on-chip interconnect of CRB (model CMN S3). CRB has two meshes, mesh 0 and mesh 1. A crosspoint is one router of the mesh grid.
- **Mesh clock**: the clock of that interconnect. One mesh cycle is one period of it.
- **perf**: the Linux tool that reads the hardware counters. When a counter runs for only a part of a run, perf scales its count to the whole run. This record marks such a count "est.".
- **dtc_cycles**: the perf event that reads the cycle counter of the mesh.
- **Flit, data channel**: a flit is one transfer unit on a mesh link or port. A data flit holds 32 B. A data channel is the part of a link or port that carries data flits.
- **Pair port**: the report's name for the one mesh port that two neighbouring cores share. The two cores are called partner cores.
- **Part 5**: the last part of the script `run_sudo.sh`, run with root rights on 2026-11-02. Its raw file is `writepath.csv` [Ref5]. Its test cases have names such as r8M-c2 (read, 8 MiB, CPU 2) and w1G-c2 (write, 1 GiB, CPU 2). **Part 3** of the same script ran earlier on that day. Its raw file is `writebw.csv` [Ref29].
- **Long run minus short run**: each test ran once for 2 s and once for 0.2 s. The difference of the two counts removes the start-up part.
- **Idle control**: a 2 s count with no test running.
- **Bus access, bus write, bus read**: one data transfer between a core and the mesh, as the core's own counters count it. Part 5 counted all bus accesses (Arm event BUS_ACCESS) and the bus writes (Arm event BUS_ACCESS_WR) in separate runs. It did not count the bus reads. This record takes them as all bus accesses minus bus writes (est.). Arm's description says that BUS_ACCESS also counts snoop requests and snoop responses [Ref26]. So the difference can hold more than the bus reads. The record takes one transfer as 32 B. That belongs to the first assumption of the conversion in D1. The count of 2.00 bus writes per 64 B line at 1 GiB fits it.
- **Snoop**: a request from the mesh to a core about a line that the core may hold.
- **L2 refill**: one line that the L2 cache loads from outside the core.
- **CHI**: Coherent Hub Interface, Arm's protocol for the ports and links of the mesh [Ref23].
- **Loop pass**: one run of the loop body, from its first instruction to the branch back. The read loop compiled from C moves 128 B per pass. The write loop compiled from C moves 16 B per pass.
- **Dispatch limits**: this record's name for the limits in section 4.1 of the SOG ("Dispatch constraints"). They limit how many operations the core dispatches in one cycle. Dispatch is the step before the pipelines. A dispatched operation waits for its inputs and then goes to a pipeline.
- **Series of runs**: several runs of one test, one after the other, each with a different thread count.
- **SLC**: System Level Cache, Arm's name for the 128 MiB cache inside the mesh. The report calls it the mesh cache. Linux shows it as L3. **LLC**: last-level cache, another name for it.
- **ASCT**: Arm System Characterization Tool, a benchmark tool whose results are in the kit.
- **asm loop**: a benchmark loop written by hand in assembly. **Loop compiled from C**: the same job written in C and compiled by gcc.
- **SVE**: Scalable Vector Extension, Arm's second vector instruction set. Its vectors are 16 B long on CRB.
- **RUNNING marker**: the file `/tmp/positron-perf.RUNNING` on CRB. It is present while another user's timed run is active.
- **MT/s**: million transfers per second, the speed unit of a memory module. One transfer moves 8 B on one channel.
- **PLL**: phase-locked loop, the circuit that makes a clock.
- **Hunk**: one block of changed lines in a comparison of two files.
- **viewBox**: the coordinate range of an SVG figure. Its numbers are called units here.
- **est.**: estimate.

## 1. Files

| File | Role |
|---|---|
| `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html` | The report. 978 lines. The reviewed state of sections 2 to 9 has the sha256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3`. The state after section 10 has the sha256 `REPORT_SHA256` |
| `/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-spec-row.html` | The report before this update. 931 lines. sha256 `ae33da24ceb2230706e42553076084275003124ef3f89a1371208175ba73138f` |
| `/home/jhan/workspace/titan/cache-perf/crb/results/probe-20261111T210017Z.txt` | New raw file: the output of the one read-only login to CRB (disassembly, versions, mesh event names) |
| `/home/jhan/workspace/titan/cache-perf/crb/results/probe-20261111T210017Z.cmd.txt` | New file: the commands of that login |
| `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/` | Check scripts (`check_geometry.py`, `render.py`, `mesh_clock.py`, `port_counts.py`), the page font, renders of the figure before and after, the variant figure of D1, the screenshot from the request, a copy of the probe output, and the folder `web-2026-11-12/` with the four downloaded web sources of [Ref13] and [Ref20] |
| `/home/jhan/tmp/update-crb-memory-hierarchy.md` | This record |
| `/home/jhan/tmp/update-crb-memory-hierarchy.md.review.md` | The shared file of the review loop |

No other project file was changed in the work of sections 2 to 9. Section 10 also changed the brief and its generator, and it lists its own backup files. The directory has no git history. The backup files are the only record of the older states.

## 2. Changes that the request listed

All line numbers are lines of the report after the update.

| Id | Request | What was done | Lines |
|---|---|---|---|
| R1 | Add a row of boxes under the existing row, aligned box by box | New row of six boxes. Each has the same x position and width as the box above it. The viewBox grew from 880 x 150 to 924 x 234 units | 77 to 96 |
| R2 | Core box: read and write throughput with the calculation | "read: 3 loads × 2.8 GHz × 16 B = 134.4 GB/s" and "write: 2 stores × 2.8 GHz × 16 B = 89.6 GB/s". Each calculation is split over two lines to fit the box | 89 |
| R3 | L1 and L2: "measured above" if there is no way to calculate | "measured above" in both boxes | 90, 91 |
| R4 | Mesh cache and pair port: "unknown" | "unknown" in both boxes. See D1: the reason in the request no longer holds | 92, 93 |
| R5 | DRAM box: "640 GB/s theoretical peak" | "10 channels × 8000 MT/s × 8 B per transfer = 640 GB/s theoretical peak" on three lines. See D4 | 94 |
| R6 | Remove "1 core" from the L1 and L2 boxes | "133 GB/s read" and "85 GB/s read". The caption now says "L1 and L2 bandwidth = one core, one thread, asm loop" | 83, 84, 97 |
| R7 | Remove "640 GB/s theoretical peak" from the first-row DRAM box | Removed | 87 |
| R8 | Row captions at the left: "Measured" and "Spec" | Two captions at x = 6 units, left of the first box | 80, 81 |
| R9 | Replace the bullet about the 8 reserved cores | Replaced with the requested sentence, character by character | 410 |
| R10 | Replace the source text of "30 ns (85 cycles)" | "Measured (averaged over all slices). Range: 19 to 44 ns by slice." I added the final full stop | 112 |
| R11 | "compiled read loop" becomes "read loop compiled from C" | Done. The text around it was rewritten with the disassembly result (answer Q7) | 131 |

Side effects that the request did not name:

- The box widths changed to make room for the row captions and for the core calculation: Core 118 to 150 units, L1 142 to 118, L2 142 to 134, mesh cache 148 to 146, DRAM 188 to 170. The pair port keeps 76 units.
- The page column is 880 px wide and the figure is now 924 units wide. The text of this figure therefore renders 4.8 % smaller than before: 12.5 px becomes 11.9 px.
- In the L1 and L2 boxes the bandwidth line lost its smaller font size (12 units). The shorter text fits at the normal size (12.5 units).
- The Source column of the table under the figure is right-aligned by the page style. Its longest cell grew from 231 to 832 characters (line 113). The cells at lines 118 (706 characters) and 104 (603 characters) are also long.

## 3. Answers to the questions

### Q1. What does "it was still rising at the footprint limit" mean?

- The whole-chip test of the mesh cache gives each thread a 3 MiB buffer. Its rule is that all buffers together stay below the 128 MiB cache size. That rule is the "footprint limit".
- The test ran 8, 16, 24, 32 and 40 threads. The next step is 48 threads, which is 144 MiB. The test stopped at 40.
- The total at 40 threads (1,349 GB/s) was higher than at 32 threads (899 GB/s) [Ref11]. That is "still rising".
- The meaning that the old text intended: the test stopped by its own rule (40 threads × 3 MiB = 120 MiB, below 128 MiB), not at a measured maximum. The total was still increasing at the last step. The old text concluded that the measured value is a lower bound.

Simpler alternatives:

| | Wording |
|---|---|
| A (now in the caption, line 97) | "A separate series of runs with 8 to 40 threads stopped at 40 threads, and its total was still increasing there." |
| B (now in the source table, line 113) | "The counters were read in that one run. The value comes from two counters, one for each mesh. Each ran for 49 % of the run, and perf scaled its count to the whole run [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv]. The run used 40 threads of 3 MiB each [bw-asmread-3M-40T-even.csv in the same folder]. A separate series of runs of the same day used 8, 16, 24, 32 and 40 threads without counters. It stopped at 40 threads by its own rule: all buffers together stay below the 128 MiB cache size, and 48 threads of 3 MiB each would be 144 MiB. The total of that series (mesh cache plus L2 hits) was still increasing there: 899 GB/s at 32 threads and 1,349 GB/s at 40 [results/slc-20261030T194835Z/slc.csv]." |
| C (shortest) | "A separate series of runs stopped at 40 threads by its own rule, and its total was still increasing." |

Three facts in the raw data limit what the old phrase can claim [Ref11]:

- One series of runs and one separate run are involved. The totals are from one series of runs with 8 to 40 threads (19:48 UTC, no counters). The mesh-served part (0.62 TB/s, est.) comes from the counters of one separate 40-thread run of the same day (20:37 UTC, total 1,384.8 GB/s). Each of the two counters ran for 49 % of that run, and perf scaled the counts. The 1.38 TB/s of the caption is the total of that separate run. The 1,349 GB/s above is the 40-thread total of the series.
- The last increase of the series is the first one with threads on the second mesh. By the command line and the source, the runs with 8 to 32 threads had every thread on a CPU below 64, which is mesh 0. Their gain per 8 threads fell from 249 to 90 GB/s. The 40-thread run added 8 threads on CPUs 64 to 78, which is mesh 1, and the total rose by 450 GB/s (898.8 to 1,348.8 GB/s).
- The file of this series holds the total, the slowest thread, the fastest thread and the average. It holds no total per mesh. So it does not show which threads delivered the 450 GB/s. It shows one related fact: the fastest thread read 58.7 GB/s in the 40-thread run and 31.0 GB/s in the 32-thread run.

Interpretation, not a measurement of the series of 2026-10-30: most of the last increase came from the 8 threads on mesh 1. Two other runs support this [Ref11].

- The counter run of the same day (20:37 UTC) counted the accesses to the mesh cache on each mesh. Mesh 1 had 3.47 × 10^9 of 9.72 × 10^9 accesses (36 %, est.). Both counters ran for 49 % of that run, and perf scaled the counts to the whole run. The two files of this run hold no CPU list. Their name (`40T-even`) says 40 threads on even CPUs. If the run used the CPU list of the series (`0-118:2`, which is every second CPU from 0 to 118), its 40 threads ran on the even CPUs from 0 to 78. Then 8 of them ran on mesh 1 (CPUs 64 to 78). The slowest thread of the run read 26.9 GB/s, the fastest 61.9 GB/s, and the average was 34.6 GB/s. The run of 2026-11-02 has a recorded placement, with 32 threads on mesh 0 and 8 on mesh 1. Its fastest repetition gave nearly the same three values: 26.2, 61.6 and 34.3 GB/s. The three values do not show how many threads were fast.
- The run of 2026-11-02 repeated the 40-thread case and recorded every thread. In its three repetitions the 32 threads on mesh 0 read 868.5, 885.9 and 890.1 GB/s together. The 8 threads on mesh 1 read 473.3, 474.3 and 481.7 GB/s. These sums are not the 450 GB/s. They are from another run. They are also another quantity. The 450 GB/s is the difference of two totals. So it also includes any change in the rate of the 32 threads on mesh 0.

The same wording is in three more places. I did not change them: lines 302 and 343 ("the mesh-served part was still rising") and the chart label at line 559 ("still rising: footprint rule stops the test here"). See F1.

### Q2. What is the clock frequency of the CMN mesh, and how can it be checked?

**The mesh clock is 2.0 GHz.** A measurement on CRB gives this value, and Arm's user guide states it. Two more sources are consistent with it:

| Source | Value | Kind |
|---|---|---|
| Part 5 of 2026-11-02: 78 raw rows of `dtc_cycles`, count divided by counting time [Ref5][Ref6] | 1.9995 to 2.0000 GHz on both meshes, with the machine idle and with 1 to 4 busy cores on mesh 0 | Measured on CRB, firmware 0.7.2 |
| SVK user guide, page 10, list of the tested platform configuration [Ref4] | "Interconnect clocked at 2.0 GHz." | Arm document, firmware 0.9.0 |
| Firmware image in the kit [Ref17] | The image holds the 64-bit value 2,000,000,000 at offset 0x4e80a91, directly after the value 2,800,000,000. Read as Hz, the two values are 2.0 GHz and 2.8 GHz. The nearest text before them is "PhoenixCfg1" (offset 0x4e80428). Another part of the image holds a list of names. In this list the name INTPLL_MAIN (offset 0x4fbf12) follows 70 names from `CPU_PLL0_MAIN` to `CPU_PLL34_FALLBK`. Three later names of the list contain the word MESH: CCSM_MESH, MESH_THERMAL_MANAGEMENT and MESH_DVFS. The image gives no description next to these names | Read from the 0.9.0 image with `strings` and a hex dump. The value at 0x4e80a91 and the name at 0x4fbf12 are 73.5 MiB apart. The image holds this 8-byte value at 46 offsets. The bytes alone do not link the value to the name. A research agent linked them by decoding machine code by hand. I did not repeat that step. That INTPLL_MAIN is the PLL of the mesh is an inference. This row is consistent with 2.0 GHz. It does not establish the value |
| TRM: the reset value of one timeout register is 50,000 cycles per 25 us [Ref3] | 2.0 GHz | Design default only |

Why the report said the opposite. The report said that `dtc_cycles` "counted only about 6,500 per second". The raw rows hold about 4.0 x 10^9 counts per 2.0 s run. The analysis script `bench/analyze_writepath.py` subtracts the count of the idle control from every counter [Ref7]. It does this also for the two cycle counters, which run all the time. For a clock, the subtraction leaves only a small remainder.

How to check it on the system (root needed, no test load needed):

```
sudo perf stat -a -x, -e arm_cmn_0/dtc_cycles/,arm_cmn_1/dtc_cycles/ -- sleep 10
# GHz = field 1 (count) / field 4 (counting time in ns)
```

On existing files, with no access to CRB:

```
python3 /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/mesh_clock.py
```

Other ways, not tried:

- The firmware reports a telemetry value "CMN FREQUENCY_PRESENT" in Hz (data event 0x0520). The kit tool `stlm` reads it [Ref18]. The devices `/dev/scmi/tlm_0` and `tlm_1` exist on CRB [Ref8]. Whether firmware 0.7.2 serves this event is not known.
- Arm support can confirm the value. The Slack channel ext-arm-positron reaches Arm's engineers [Ref15].

Limits of the 2.0 GHz statement:

- CRB still runs firmware 0.7.2 (read on 2026-11-11) [Ref8]. Firmware 0.9.0 adds frequency scaling for the mesh ("Added CMN mesh DVFS and thermal tuning", SVK user guide page 7) [Ref4]. The clock must be measured again after a firmware update.
- The clock was not measured with the whole chip busy.
- The perf event reads the cycle counter of one debug controller. Each mesh has four. That the whole mesh runs on one clock is an assumption. Arm's manual requires the same frequency in all clock domains of a mesh [Ref3].

### Q3. "Consistent with the measured cycles: 1.43 ns × 2.8 GHz = 4.0." Is it a proof of the clock?

No. You are right.

- What the sentence tried to say: the L1 latency of 1.43 ns is a whole number of cycles at 2.8 GHz, and Arm documents 4 cycles for a load that hits L1 [Ref2].
- Why it proves nothing as written: it named no source for the "4". The "(4 cycles)" in the figure is itself computed as ns × 2.8 GHz.
- What replaces it (line 104): a direct measurement. The cycle counter of CPU 2 advanced 2.800 x 10^9 cycles per second while the core ran the benchmark. The six cases of part 5 give 2.7998 to 2.8001 x 10^9 cycles per second [Ref5][Ref6]. Example, case w8M-c2: 5,039,939,572 cycles in 1.799979528 s, long run minus short run.
- Other evidence that exists and is not in the report: the kernel's measured average frequency `cpuinfo_avg_freq` was 2,797,265 kHz in the inspection of 2026-10-30 [Ref12]. The perf counter gives 4.0000 cycles per L1 load, so "4 cycles" is also a measured number [Ref16].

### Q4. Is "mesh cache" the term of the Arm documents?

No. "Mesh cache" is the report's own name.

| Source | Term | Count |
|---|---|---|
| CMN S3 TRM, 2,184 pages [Ref3] | "System Level Cache (SLC)". Definition on page 54: "The System Level Cache (SLC) is a last-level cache." | "SLC" 445 times, "mesh cache" 0 times |
| CMN-700 TRM, 1,316 pages [Ref19] | "System Level Cache (SLC)" | "SLC" 396 times, "mesh cache" 0 times |
| SOG, 67 pages [Ref2] | It names no shared cache | "SLC" 0 times, "mesh cache" 0 times |
| Arm's public product brief for the Arm AGI CPU [Ref13] | "System-Level Cache 128MB" | |
| Linux on CRB (lscpu, sysfs) [Ref12] | "L3" | |
| Linux mesh driver events [Ref5] | `hns_slc_...`, for example `hns_slc_sf_cache_access_all` | |
| Kit: SPEC benchmark reports and ASCT results [Ref14] | "L3 cache" and "LLC" | "SLC" 0 times as a cache name, "mesh cache" 0 times |
| Other Arm server CPUs: Ampere, AWS Graviton, NVIDIA Grace [Ref20] | Ampere: "System Level Cache". AWS: "LLC (shared)". NVIDIA: "L3" | Read from the text of the three pages on 2026-11-12 UTC. The row compares the words only. It makes no statement about the interconnect of these chips (see the note below the table) |

Note on the last row. The three pages differ in what they say about the interconnect. The AWS page lists CMN as the interconnect of Graviton2 to Graviton5. It names the models CMN-600 to CMN S3 (the page writes "CMN-S3"). CMN S3 is also the model of CRB's mesh. The NVIDIA page names an interconnect that NVIDIA designed (its name is Scalable Coherency Fabric). The Ampere page names no interconnect for the three products that it lists with the words "System Level Cache". For one more product, AmpereOne Aurora, the page says "Ampere designed cores, mesh, and chiplet interconnect". The heading above that product is "Future of AI Compute".

Recommendation: rename "mesh cache" to "SLC". Write "SLC (L3)" where the term is introduced and in the first figure. A reader who knows Linux then finds the L3. Define it once: "SLC: system level cache, Arm's name for the cache in the mesh. Linux shows it as L3."

Size of the rename in the report after this update: 93 literal occurrences (86 before this update). 5 are element ids with 5 matching links, 8 are chart labels in JavaScript, 1 is a JavaScript comment, 1 is the screen-reader label of the first figure, and the rest is visible text. 7 of the 20 figures draw the phrase. About 26 more places use the bare word "mesh" for the cache level and need a manual check. This was not done in the update of 2026-11-11, because the request asked only for an investigation of the term. It was done on 2026-11-12 after the author confirmed the term (section 10.1).

### Q5. Can the pipelines be configured as 4 read plus 1 write?

No.

- The core has four pipelines that start loads and stores: Load/Store 0, Load 1, Load 2 and Store 1 [Ref2].
- Only three of them accept loads. Four loads in one cycle are not possible.
- Each pipeline accepts one operation per cycle. The core can therefore start at most 3 loads + 1 store, or 2 loads + 2 stores, in one cycle.
- The guide gives these roles as part of the design. It describes no setting that changes them.
- The report said "five pipelines" and named four. The count is corrected to four (line 123). A new paragraph gives the possible mixes (line 124).
- The asm copy loop is a measured case of the second mix: 178.4 GB/s against 179.2 GB/s for 2 loads + 2 stores of 16 B per cycle (line 125) [Ref10].

### Q6. What is the difference between "compiled read loop" and "asm loop"?

Both are in `bench/bandwidth.c` [Ref21].

- The compiled read loop is the C function `k_read`. It adds every 8 B word of the buffer into one of 16 running sums. gcc 14.2 chooses the instructions. It is compiled from C, and the report now says "read loop compiled from C".
- The asm loop is the function `k_asmread`. Its loop body is written by hand: 8 `ldp` instructions of two 16 B registers each, one add, one compare and one branch. It loads and does nothing else.

### Q7. Can the disassembly replace the test run?

Partly. I read the machine code on CRB with `objdump -d` in one read-only login on 2026-11-11 at 21:00 UTC. No benchmark ran [Ref8].

- **Confirmed without a test run.** For each 128 B the compiled read loop runs 16 instructions: 4 `ldp` of q registers (8 loads of 16 B), 8 vector adds into 8 separate registers, 2 integer adds, one compare and one branch. The first half of the old hypothesis holds: one vector add per 16 B load.
- **The old explanation does not fit.** Arm's table gives 2 vector adds per cycle on the two vector pipelines [Ref2]. That allows 2 loads per cycle, which is 89.6 GB/s. The measured 66.8 GB/s is 25 % below that.
- **Dispatch limits checked.** Arm's guide limits how many operations the core dispatches in one cycle (section 4.1, "Dispatch constraints") [Ref2]. The section lists eight limits. Four of them, each per cycle: at most 10 decoded instructions, at most 6 operations for the load pipelines, and at most 2 for each of the two vector pipelines. On average the loop runs 3.0 instructions, 1.5 loads of 16 B and 1.5 vector adds per cycle. The four other limits are for all operations together (20 per cycle) and for three groups of integer and branch pipelines (4, 4 and 2 per cycle). The loop is below them too on average (est.). One pass has about 20 operations, which is 3.7 per cycle. The guide gives no count for the instruction LDP q, and the 20 counts one LDP q as two operations (est.). At most 4 of the 20 are integer or branch operations, which is at most 0.75 per cycle. So the loop stays below every limit that was checked: 3 loads per cycle, 2 vector adds per cycle, and the eight dispatch limits. The check compares average rates only. It covers only these limits. It does not exclude any other limit, whether the guide lists it or not. The cause of the remaining gap is not established.
- **New observation.** One pass of the loop takes 5.37 cycles at 32 KiB and 5.34 cycles at 1 MiB, and it writes 16 vector registers (8 by loads, 8 by adds). That is 2.98 to 3.00 per cycle.
- **Two readings fit.** Hypothesis A: loads and adds that write vector registers share a limit of 3 per cycle. Hypothesis B: the adds reach only 1.5 per cycle for a reason that is not known, and the loads follow the adds.
- **A test run is still needed for that last part.** The 3:2 loop that the report already proposed separates the two. Hypothesis A predicts 80.6 GB/s. Hypothesis B predicts 100.8 GB/s. A result of 134.4 GB/s would reject both.
- The report text is at lines 131 to 133.

One caveat. The binary that I read was built on 2026-11-02 from the current source file. The source on CRB and the local source have the same sha256 [Ref8]. The 66.8 GB/s was measured on 2026-10-30 with an earlier build, and no copy of that binary exists. Evidence that the loop did not change: a copy of the source of 2026-10-30 holds the same `k_read`, `k_write` and `k_copy` [Ref22]. The gcc package on CRB was the same on 2026-10-30 and on 2026-11-11 [Ref8][Ref22]. No saved file records it for the build day, 2026-11-02. The log of the follow-up run of 2026-10-30 shows a second build at 19:42 UTC with the compile flags of today's Makefile [Ref25]. That build gave the same rate for the read loop as the first build: 67.10 to 67.13 GB/s per thread at 1 MiB against 67.09 GB/s. The log of the first run holds no compile command. A 2 s run of `./bandwidth --kernel read --bytes 32K --threads 1 --cpus 3` on CRB would show whether the binary that was read gives the same 66.8 GB/s. I did not run it.

A second result of the same disassembly: the write and copy loops compiled from C are SVE loops that move one 16 B vector per pass [Ref8]. Each uses the SVE store instruction `st1d` in a loop that the SVE instruction `whilelo` controls. The write loop has 4 instructions per pass, and the copy loop has 5. Their observed rates with one thread [Ref16]:

- Write: 0.98 to 1.00 loop passes per cycle at all four buffer sizes (44.0 to 44.8 GB/s from 32 KiB to 1 GiB).
- Copy: 0.98 to 0.99 loop passes per cycle at 32 KiB and 1 MiB (88.0 and 88.8 GB/s, counted as bytes read plus bytes written). At 8 MiB and 1 GiB the copy loop is slower (50.0 and 42.2 GB/s).

These are observed rates. No run tested what sets them.

- A bound follows from Arm's guide. It is derived, not measured. Each pass adds to the index register, and the add of the next pass needs the result. The guide gives a latency of 1 cycle for an integer add [Ref2]. Latency is the number of cycles before a dependent operation can start. So by the guide's numbers these loops run at most one pass per cycle.
- The guide gives 2 per cycle for `st1d` and 2 per cycle for `whilelo` [Ref2]. So by the guide's numbers these two instructions allow two passes per cycle.
- Hypothesis: a limit of one pass per cycle sets the rate of the write loop, and the stores do not.
- Test: write a loop by hand with two `st1d` stores of 16 B per pass and still one index add per pass. The hypothesis predicts more than 44.8 GB/s, up to 89.6 GB/s (one pass per cycle, which is also 2 stores per cycle). A result of 44.8 GB/s again would reject it. Not run.
- A measured fact that fits the hypothesis and does not replace the test: the asm write loop has 16 stores of 16 B per pass and reaches 89.5 GB/s, which is 2 stores per cycle [Ref10]. Its stores are STP q instructions, not `st1d` [Ref21]. One STP q stores two 16 B registers.

For these two loops the report gives the bytes per pass ("Words used here", line 461) and the instructions per cycle ("about 4 and about 5", line 133). It does not give the passes per cycle, and it states no limit of one pass per cycle. See F14.

## 4. Points to discuss

### D1. The pair-port Spec box says "unknown", but a calculation now exists

The request says "unknown" for the pair port and the mesh cache "because we do not know mesh clock". The mesh clock is now known. I kept "unknown" in both boxes, because the request asks to discuss before I differ.

My proposal for the pair-port box: "hypothesis: 1 flit × 32 B × 2.0 GHz = 64 GB/s each way".

The proposal is the first of three separate statements. The report keeps them apart (lines 420 to 422):

- **Hypothesis 1, capacity.** The pair port passes at most one data flit of 32 B per mesh cycle in each direction. That is 64 GB/s each way. Only this statement would go into the Spec box.
- **Hypothesis 2, saturation.** Four kinds of run fill this capacity, and the full port is what limits them. They are the runs of two partner cores that read 8 MiB each, of two partner cores that write 8 MiB each, of one core that writes 1 GiB, and of two partner cores that write 1 GiB each. The report calls them the runs of hypothesis 2. Hypothesis 1 can hold while a run leaves the port partly idle.
- **Conversion, two assumptions.** The measured rates count the bytes that the loops moved. The hypotheses are about the bytes that cross the port. The first assumption: one bus read or bus write of a core is one data flit of 32 B at the port. The second assumption: a count per line that was measured on one core alone also holds for two partner cores. The counts and most pair rates are also from different runs. Most counts are from CPU 2 with the asm loops in part 5 (2026-11-02). One share is from CPU 0 in part 3 of the same day [Ref29]. One more value of that share, the 0.81, is from a counter run of 2026-10-30 [Ref28]. Its file does not record the CPU. The loop read 67.1 GB/s in that run. It read 70.7 to 71.0 GB/s in the runs of the three counts of 0.83 [Ref5][Ref29]. On 2026-10-30 one asm reader alone read 66.9 GB/s in the file of the asm pair rate [Ref10]. Most pair rates are from CPUs 0 to 5 on 2026-10-30, and three of them are from the read loop compiled from C.

| Evidence | Value | Statement that it concerns | Source |
|---|---|---|---|
| Mesh clock | 2.0 GHz, measured | Hypothesis 1 | [Ref5] |
| Size of a data flit | 32 B, fixed by design ("Data_Width ... Fixed to 256") | Hypothesis 1 | TRM page 2120 [Ref3] |
| Data channels at the pair port | Not read from CRB. Arm's manual draws one data channel in each direction at a device port (Figure 2-25, page 89). For the links between crosspoints there is a hint: the mesh driver on CRB lists events for a second response channel (`rsp2`) and none for a second data channel (`dat2`) | Hypothesis 1 | [Ref3][Ref8][Ref9] |
| Arm's description of the bus events of this core | "Each beat of data is counted individually." A beat is one transfer on the bus. The same description says that BUS_ACCESS includes "snoop requests and snoop responses". The port counts of case r8M-c2 hold 4,182 snoop flits against 3.3 × 10^9 data flits | Conversion, first assumption | [Ref26][Ref5] |
| One writer at 1 GiB, bus count | 2.00 bus writes per 64 B line | Conversion, first assumption | case w1G-c2 [Ref5][Ref24] |
| One reader at 8 MiB, bus count and port count | 3.306 bus accesses per line, of which 1.653 are bus writes. The other 1.653 are taken as bus reads (est.). The port carries 1.653 data flits per line toward the core. Each of the three counts is from its own pair of runs of the case (2 s minus 0.2 s) | Conversion, first assumption | case r8M-c2 [Ref5][Ref24] |
| One reader, counted at its port | 0.92 data flits per mesh cycle = 58.7 GB/s on the port, while the loop reads 71 GB/s. This counter covers one data channel and cannot show more than 1.0 flit per mesh cycle (TRM pages 1678 to 1679) | It shows how full this data channel was with one reader. It cannot test hypothesis 1 | case r8M-c2 [Ref5][Ref3] |
| Share of the lines of one reader at 8 MiB that cross the port | 0.83 by three counters of 2026-11-02 that ran for the whole run: 1.653 port flits per line, 0.83 L2 refills per line, and 0.83 accesses to the mesh cache per line. A scaled count of 2026-10-30 gives 0.81 (est.) | Conversion. The second assumption carries this share over to two partner cores | [Ref5][Ref24] for the port flits and the L2 refills, [Ref29] for the accesses to the mesh cache, [Ref28] for 0.81 |
| Two partner readers at 8 MiB | With 0.83, 64 GB/s on the port allows 77 GB/s (est.). Measured 77.5 GB/s with the asm loop and 77.9 to 78.5 GB/s with the read loop compiled from C. Converted with 0.83, these rates are 64.1 to 64.9 GB/s on the port (est.), which is 1.00 to 1.01 flits per mesh cycle. With the scaled 0.81 the allowed rate is 79 GB/s, and the converted rates are 62.9 to 63.7 GB/s (est.) | Hypotheses 1 and 2 together, through the conversion (est.) | [Ref10] for the pair rates |
| Two partner writers at 8 MiB | 64 GB/s on the port allows 84 GB/s (1.52 bus writes per line, each taken as 32 B). Measured 82.34 GB/s on 2026-10-30 and 81.41 to 82.05 GB/s in the nine 2 s runs of part 5. In one pair of runs of part 5, CPU 2 sent 1.52 bus writes per line that it wrote itself, the same count as alone | Hypotheses 1 and 2 together, through the conversion (est.) | [Ref5][Ref10][Ref24] |
| Writers at 1 GiB | One writer 63.0 GB/s. Two partner writers together 63.2 GB/s. Four writers on two pairs 113 GB/s, which is 56.6 GB/s per pair | The first two rates: hypotheses 1 and 2 together, through the conversion (2.00 bus writes per line, measured on one writer alone). With the first assumption the rate of one writer through the port is 0.98 of 64 GB/s (est.). With both assumptions the rate of two partner writers through the port is 0.99 of 64 GB/s (est.). The run of four writers is not one of the runs of hypothesis 2. It has two busy pairs, and its rate per pair is 0.88 of 64 GB/s (est.). D2 uses this run | [Ref5][Ref10][Ref24] |

What is missing. The first three points follow the three statements (report lines 431 to 436). The last two points are at report lines 420 and 429:

- Capacity. The number of data channels at the port was not read. A run can reject hypothesis 1 only by a rate above 64 GB/s through one port in one direction. A low rate cannot reject it.
  - For writes one comparison exists. Two partner writers reach 63.2 GB/s together at 1 GiB, which is below 64 GB/s. At 1 GiB one writer alone sends 2.00 bus writes per line. If both assumptions of the conversion hold, the rate of the write loop is also the rate through the port (est.). No run counted the bus writes of two partner writers at 1 GiB. No counter of part 5 covers the data flits from the port to the crosspoint.
  - For reads, the converted rate of two partner readers at 8 MiB is 64.1 to 64.9 GB/s on the port with the share of 0.83 (est.). It is 62.9 to 63.7 GB/s with the scaled share of 0.81 (est.). No run counted the share for two partner cores. So the conversion cannot say whether the rate is below or above 64 GB/s.
  - A run with more bus reads than mesh cycles could not separate a wrong hypothesis 1 from a wrong first assumption. A read of the register field dat_vc_num_p can separate them. This field holds the number of data channels at the port (TRM page 1656) [Ref3]. The manual does not say which value of the field stands for which number of channels. The report assumes that the field counts the channels in the same way as the design parameter on TRM page 1678.
- Saturation. No run counted the data flits at the port while two partner cores read. The report gives no threshold for "full". Only one value of this counter exists for a reader. This counter cannot be used for writes. It counts only the data flits that the crosspoint sends to the port, toward the core. Write data goes the other way. For writes, the bus writes of both partner cores must be counted. A reader also sends data the other way (1.653 bus writes per line for one reader). So the read test counts the bus writes of both cores too.
- Conversion. The two factors (0.83 of the lines read cross the port, and 1.52 bus writes per line written) were measured on one core alone. No run counted the bus reads or the bus writes of both partner cores. One count exists for one core of a writing pair: CPU 2 sent 1.52 bus writes per line that it wrote itself. A count of more bus reads than port flits would have two readings. Either the first assumption is wrong, or a second data channel carries flits that the counter does not cover.
- The limit of one flit per clock cycle on one channel follows from the signals of the CHI protocol [Ref23]. None of the Arm documents that were read states it in one sentence.
- The copy runs of two partner cores were not checked against the hypotheses. No bus count exists for a copy run. One more count is not explained: the four mesh links of CPU 2's crosspoint carried 1.09 times as many data flits as the core made bus writes (report line 429).

The measured ~80 GB/s in the box above (77.5 GB/s with the asm loop, 77.9 to 78.5 GB/s with the read loop compiled from C) is higher than 64 GB/s. The 80 GB/s counts every byte that the two cores read. One core alone takes 17 % of its lines from its own L2. If two partner cores do the same, 64.1 to 64.9 GB/s cross the port (est.). That is at or just above 64 GB/s. No run counted this share for two partner cores. A share of 0.81 would put all four pair rates of the read loops (77.5, 77.9, 78.3 and 78.5 GB/s) below 64 GB/s (est.). So the estimate does not decide whether the measured rate conflicts with 64 GB/s on the port.

The alternative figure is rendered at `crb/tmp/agent-scratch/spec-row-2026-11-11/figure-variant-pair-port-64.png`. Its box starts with the word "hypothesis". If you choose it, I will add one sentence to the caption.

For the mesh cache I agree with "unknown". Arm's manual gives no throughput. It gives only the timing of the data array of one slice (TRM page 280) [Ref3].

### D2. Older statements of the report that the new facts put in doubt

- "For DRAM streams the port is not the limit" (line 214) and "For DRAM traffic the port is not the limit" (line 380). The evidence there is a read test. For writes at 1 GiB, two partner cores write 63.2 GB/s together, one core alone writes 63.0 GB/s, and four writers on two pairs write 113 GB/s [Ref10]. So two partner writers share one limit at 1 GiB. This follows from the measured rates, and it holds whether hypotheses 1 and 2 hold or not. The read test behind both statements does not cover write streams. That the full port is the shared limit is part of hypothesis 2.
- "The single-writer limit is inside the core" (line 289) was written for 8 MiB writes. At 1 GiB one writer sends 1.96 × 10^9 bus writes per second [Ref5]. At the mesh clock of 2.0 GHz that is 0.98 bus writes per mesh cycle (est.). If hypothesis 1 of D1 and the first assumption of the conversion hold, that is 98 % of the capacity of the port (est.). Whether the port then limits the writer is hypothesis 2.
- "For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2" (line 214). The rates show that two partner readers share one limit of about 78 GB/s. That the full port is this limit is part of hypothesis 2. The 78 GB/s also counts the lines that the two cores take from their own L2.

I did not change these sections. The new open item names them (line 437). They need your decision, and possibly the tests of D1.

### D3. The row caption "Measured" stands over values that are not measured

The first row also holds values read from the machine (sizes, ways, 2.8 GHz, DDR5 channels) and one value from Arm's guide ("3 loads + 2 stores of 16 B per cycle"). I kept the caption. At line 101 I rewrote the first sentence and added the kind "Arm document". An option: move "3 loads + 2 stores of 16 B per cycle *" from the first-row Core box to the Spec row.

### D4. The DRAM Spec box holds two more lines than the request

The request says "640 GB/s theoretical peak". I added the calculation above it, "10 channels × 8000 MT/s × 8 B per transfer", to match the style of the Core box. Say so if you want only the one line.

### D5. "between Jeremy and me" in the reserved-cores sentence

The sentence is in the report exactly as requested. Elsewhere the report says "Jibin" in the third person. Say so if "me" should become "Jibin".

### D6. The label "3 loads + 2 stores of 16 B per cycle" reads as five operations in one cycle

The two numbers are separate limits. The label is the text of the Core box, of a table row, and of a section title with its anchor. I did not change it. I added "The two numbers are separate limits" to the table row (line 105), and line 124 says that the label gives two separate limits. An exact label would be "3 loads or 2 stores of 16 B per cycle". Decided by the author on 2026-11-12: the label is now "3 loads / 2 stores" in all six places (section 10.2).

### D7. Arm's own reference results for L1 and L2 exist in the kit

The kit holds two sets of results that Arm measured with its tool ASCT, both with firmware 0.9.0 [Ref14]. CRB reports product version EVT0 [Ref12]. It has 10 memory modules of part number MTC20F2085S1RC80BH1 NCKK at 8000 MT/s [Ref27]. The first set has the same product version and the same core count (128). The second set has the same module part number and speed. Its machine is EVT1 and has 136 cores. Both sets ran firmware 0.9.0 with 12 memory channels. CRB ran firmware 0.7.2 with 10 memory modules.

| Level | ASCT, EVT0 machine, 7200 MT/s | ASCT, EVT1 machine, 8000 MT/s | This report (CRB) |
|---|---|---|---|
| L1 bandwidth | 324.5 GB/s | 370.6 GB/s | 132.7 GB/s (pipeline limit 134.4 GB/s) |
| L2 bandwidth | 84.7 GB/s | 112.3 GB/s | 85.2 GB/s |
| LLC bandwidth | 55.4 GB/s | 45.9 GB/s | 67 GB/s |
| DRAM bandwidth | 36.2 GB/s | 36.3 GB/s | 30.5 GB/s |

The L2 value of the EVT0 set agrees with this report. The L2 value of the EVT1 set is 32 % higher. The L1 values of ASCT are 2.4 and 2.8 times the 134.4 GB/s pipeline limit of CRB. Hypothesis: the tool counts bytes that it does not load. The kit does not say how the tool counts. A run of the tool on CRB, with the core's counter of L1 accesses read at the same time, would test it. If the counted accesses account for fewer bytes than the tool reports, the hypothesis holds. If they account for all reported bytes, it is rejected. Not run. I did not put these numbers into the report. They could become a new open item.

### D8. A sentence from a document that Arm marks Confidential

The SVK user guide is marked Confidential. The report cites it (pages 6, 7 and 10) and gives its facts in my own words. It does not quote it. This record quotes two short sentences of it in Q2.

### D9. The Spec row uses the values of CRB as it ran, not the highest values that Arm states

The Core box uses 2.8 GHz. That is the highest clock that CRB offers with firmware 0.7.2. Arm's user guide for firmware 0.9.0 gives a core clock of up to 3.2 GHz and a default memory speed of 7200 MT/s (SVK user guide, pages 6 and 10) [Ref4]. The platform has 12 memory channels, and CRB has 10 memory modules. With 3.2 GHz the Core box would read 153.6 GB/s for read and 102.4 GB/s for write. With 12 channels at 8000 MT/s the DRAM box would read 768 GB/s. The report gives the 768 GB/s at line 120. It gives the 3.2 GHz and the 7200 MT/s at line 467. It does not give the 153.6 GB/s and the 102.4 GB/s.

Arm's public product brief states higher values for the product [Ref13]. Its table on page 3 gives "Max Frequency" as 3.5GHz for the 136-core and the 128-core model, and memory as "12x DDR5 up to 8800MT/s". Page 2 says "up to 3.2GHz, all-core clock speed with boost speeds up to 3.7GHz". With 3.5 GHz the Core box would read 168.0 GB/s for read and 112.0 GB/s for write. With 12 channels at 8800 MT/s the DRAM box would read 844.8 GB/s. The report does not give these values.

## 5. Changes that the request did not list

Each one follows from a requested change or answers one of the questions.

| Id | Change | Reason | Lines |
|---|---|---|---|
| C1 | Sub-header: two sentences that name the additions and the corrections of 2026-11-11 | The page keeps a change log in this line | 49 |
| C2 | New screen-reader label (`aria-label`) of the figure | The figure has two rows now | 77 |
| C3 | Caption: explains the two rows, "measured above" and "unknown". The phrase of Q1 is replaced by wording A, which names the separate series of runs. The caption marks the 0.62 TB/s as an estimate from scaled counts (section 9) | Follows from R1 to R8 and from Q1 | 97 |
| C4 | Paragraph under the figure: the first sentence is rewritten, the kind "Arm document" is named, and one sentence says that the Spec row holds derived numbers only | The row caption "Measured" would contradict the old definition | 101 |
| C5 | Source table, row "Core, 2.8 GHz fixed": the first sentences now give the values that the machine reports and their source. The sentence of Q3 is replaced by a measurement | Q3 | 104 |
| C6 | Source table, row "3 loads + 2 stores": two sentences that the two numbers are separate limits | Q5, D6 | 105 |
| C7 | Source table, row "≥0.62 TB/s whole chip": the explanation of Q1 (wording B). It keeps the counter run and the series of runs apart, and it cites the file of each. It marks the value as an estimate from scaled counts (section 9) | Q1 | 113 |
| C8 | Source table: five new rows for the Spec boxes. The old row "640 GB/s theoretical peak" became the DRAM row. The pair-port row names hypothesis 1 and gives the estimate of 64 to 65 GB/s on the port | Each new box needs a source | 116 to 120 |
| C9 | Pipeline section: "five" becomes "four". New paragraphs on the possible mixes, on the copy loop (a measured case of 2 loads + 2 stores) and on the store data pipelines. The citation of SOG Table 3-14 changes from "page 25" to "pages 24 to 25" | Q5 | 123 to 127 |
| C10 | Caption of the pipeline figure: "carry 16 B" becomes "each start a 16 B store" | It agrees with the new paragraph at line 127 | 129 |
| C11 | Compiled-loop paragraphs with the disassembly result, the limits of Arm's guide that were checked, and two hypotheses with their test. Line 132 holds five paragraphs on one source line. In line 130 the citation of `bench/bandwidth.c` changes from "176 to 210" to "179 to 186 and 204 to 211" | Q6, Q7 | 130 to 133 |
| C12 | Table of part 5: "2.48" cycles per line becomes "2.52 [2.85]", and 72 GB/s becomes 71 GB/s | The old value came from the same idle subtraction as the wrong mesh clock. The new line 104 uses the raw count | 276 |
| C13 | Table of part 5: "occupancy cannot be turned into a queue time" becomes "was not converted" | The corrected note no longer gives a reason why it cannot | 279 |
| C14 | Note under the part 5 table: the statement about `dtc_cycles` is corrected. The other caveats are now a second note | Q2 | 290, 291 |
| C15 | New open item on the Spec throughput of the pair port and the mesh cache. It keeps two hypotheses (capacity, saturation) and the conversion with its two assumptions apart, and it names the missing test for each. Six of its items hold a nested list on one source line (lines 422, 425, 433, 434, 435 and 437). Line 429 holds two items | The two "unknown" boxes need the reason and the missing tests | 416 to 439 |
| C16 | "Words used here": new entries "mesh clock, mesh cycle", "flit, data flit, data channel" and "bus access, bus read, bus write". Line 452 also holds a second entry, "bus reads in part 5". The entry "compiled loop, asm loop" says what "compiled" means and what the three compiled loops are. The SVK user guide is added to the cited documents, with the values that differ under firmware 0.9.0 | New terms, Q6, D9 | 450, 451, 452, 461, 467 |
| C17 | "When the runs happened": one paragraph for part 5 and for the login of 2026-11-11 | The new text cites both | 471 |

## 6. Found and not changed

These are outside the request. Each has a proposed correction. Say "apply" with the ids. F1 to F21 are from the update of 2026-11-11. F22 to F34 were found by the check of 2026-11-12 (section 10.8). The rows quote the report with the name "SLC", as the report has it since 2026-11-12. The rename of 2026-11-12 edited report lines that hold nine of the older items (F1, F3, F4, F5, F10, F14, F15, F20 and F21). It replaced only the name there, and these items are still open.

| Id | Where | Problem | Proposed text |
|---|---|---|---|
| F1 | Lines 302, 343, chart label 559 | "The SLC-served part was still rising" was not measured. The SLC-served part was counted in one run at 40 threads. Only the total was measured at each thread count, in a separate series of runs without counters. The chart label keeps the phrase "footprint rule" | Line 302: "In a separate series of runs without counters the total was still rising at 40 threads (899 GB/s at 32 threads, 1,349 GB/s at 40). The last 8 of the 40 threads were the first threads on chiplet 1. The series stopped at 40 threads by its own rule: all buffers together stay below 128 MiB, and the next step of 48 threads would be 144 MiB. The 0.62 TB/s is what the SLC delivered in one run (est.). Each counter ran for about half of that run, and the counts were scaled to the whole run. So the cache can deliver about 0.62 TB/s or more (est.)." Line 343, in place of the last sentence: "So 40 is the largest count tested that fits. The 0.62 TB/s is what the SLC delivered in this one run (est., from counters that ran for about half of the run). So the cache can deliver about 0.62 TB/s or more (est.). A separate series of runs with 8 to 40 threads measured only the total, and the total was still rising at 40 threads." Label: "total still rising: the test stops at 40 threads" |
| F2 | Line 379, caption of the pair chart | It says "asm read". The data are from the read loop compiled from C (`--kernel read`). The asm value for CPUs 0 and 1 is 77.5 GB/s | "Read loop compiled from C, 2 threads, 8 MiB each, best of 2 reps." |
| F3 | Lines 110, 213 and 377 | "two non-partners 134 GB/s". CPUs 0 and 2 read 126.6 GB/s (compiled) and 129.7 GB/s (asm). CPUs 0 and 3 read 124.8 GB/s. 134 GB/s is CPUs 0 and 64, on different meshes | "two non-partners 125 to 134 GB/s" |
| F4 | Line 214 | "about 28 B per core cycle (est. from 78 GB/s at 2.8 GHz)". The crosspoint is part of the mesh, and hypothesis 1 of D1 counts its port in mesh cycles (2.0 GHz). Arm's event list says that the core's own bus interface runs at the core clock [Ref26]. The 78 GB/s also counts the L2 hits | "39 B per mesh cycle at the readers, about 32 B per mesh cycle on the port (est., with the share of one core alone)" |
| F5 | Lines 214, 289, 380 | The statements of D2 | See D2 |
| F6 | Line 301 | "40 threads is the most that fits". 42 threads (126 MiB) would fit | "40 threads is the largest count tested" |
| F7 | Line 181 | Citation "[SOG, section 1.1 page 9]". The feature list is in chapter 2 on page 10 | "[SOG, chapter 2 page 10]" |
| F8 | Line 107 | "Cycles derived." (the author's wording of 2026-11-12, before that "The cycle number is derived: ns × 2.8 GHz."). The perf counter also measured 4.0000 cycles per L1 load | Add: "The core cycle counter gives the same 4.0 cycles per load." |
| F9 | The figure drawn by script with id "pipes" | The write panel draws "16 B" on Load/Store 0 and Store 1. Those two pipelines start the stores. The 16 B of data go through FP/ASIMD 0 and 1 | Redraw the right panel, or keep it as a simplification |
| F10 | Lines 52, 266 and 428 | Three values for one reader at the SLC: 67 GB/s (line 52), 54 GB/s from the SLC (line 266, run of 2026-10-30, est. from scaled counts, see F21) and 71 GB/s with 58.7 GB/s on the port (line 428, part 5). The report does not link them | Line 52: "about 67 GB/s (66 to 72 GB/s by core and by run)" |
| F11 | `bench/analyze_writepath.py` lines 55 to 57 | The script subtracts the idle control from the two cycle counters. Its "per cycle" column (line 58) is wrong | Skip the subtraction for events that end in `/dtc_cycles/` or `/cycles/` |
| F12 | `bench/run_sudo.sh` line 15 and `crb/plan-2026-11-02.md` line 207 | Both still say that `dtc_cycles` is not usable as a mesh clock | Correct both notes |
| F13 | `crb/crb-memory-hierarchy-brief.html` and `crb/perf-measurement-tech.html` | Not checked against the new facts. The technique page repeats the old explanation of the compiled read loop | Check both |
| F14 | Line 266 | "From the SLC and DRAM the two loops agree, so there the limit is outside the core." This is wrong for the write rows. The write loop compiled from C stays at 44.8 GB/s from 1 MiB to 1 GiB. The asm write loop reaches 73.2 GB/s at 8 MiB and 63.0 GB/s at 1 GiB. The loop compiled from C stores one 16 B vector per loop pass, and it ran 1.00 loop passes per cycle in these runs. This is an observed rate. What sets it was not tested (see Q7). The read loop compiled from C and the asm read loop give 67.0 and 66.9 GB/s at 8 MiB. They give 28.2 and 30.5 GB/s at 1 GiB. Equal rates at 8 MiB do not show a shared limit: the read loop compiled from C gives 66.8 to 67.1 GB/s at 32 KiB, 1 MiB and 8 MiB alike [Ref10][Ref16] | "From the SLC the two read loops give the same rate (67.0 and 66.9 GB/s). This does not show a shared limit: the loop compiled from C reads 66.8 to 67.1 GB/s at 32 KiB, 1 MiB and 8 MiB alike. From DRAM they differ by 8 % (28.2 GB/s compiled from C, 30.5 GB/s asm). The write loops do not agree. The loop compiled from C stays at 44.8 GB/s. The asm loop reaches 73.2 GB/s at 8 MiB and 63.0 GB/s at 1 GiB. The loop compiled from C stores one 16 B vector per loop pass, and it ran one loop pass per cycle in these runs. What sets that rate was not tested." |
| F15 | Lines 110, 266, 408 | The share of L2 hits at the SLC footprint has three values: none (line 110, "read 78 GB/s from the SLC"), 19 % (line 266) and "a few percent" (line 408). The new text says 17 % for one core alone, from three counters that ran for the whole run (lines 118 and 425). The 19 % of line 266 is from a scaled count (see F21). No run counted this share with only two partner cores busy | Line 110: "two partner cores together read 78 GB/s at the SLC footprint" (the rest of that sentence stays). After the sentence that ends with "78 rounded." add: "The 78 GB/s counts every byte that the loops read. One core alone takes 17 % of its lines from its own L2. No run counted this share with only two partner cores busy." |
| F16 | Line 275 | "every line leaves the core as a write". At 8 MiB the core sends 1.52 bus writes per line, which is 0.76 of the lines | "at 1 GiB every line leaves the core as two bus writes of 32 B; at 8 MiB 0.76 of the lines leave, for a reason not measured" |
| F17 | Line 290 | The report cites `crb/tmp/agent-scratch/spec-row-2026-11-11/mesh_clock.py`. The folder is a scratch folder | Move the script to `bench/mesh_clock.py` and change the citation |
| F18 | `bench/bandwidth.c` lines 135 to 137 | The comment says that the 16 sums keep the read loop load-bound. On CRB the loop runs at 1.5 of 3 possible loads per cycle | Correct the comment |
| F19 | Line 116 | The write limit of 89.6 GB/s is for stores of register data. Arm's guide recommends another instruction for zero fill (DC ZVA) | Add one sentence that zero fill is a separate path and was not measured |
| F20 | Lines 215 and 230 | "The three documents above" now reads as SOG, TRM and SVK user guide. The third PDF in `crb/refs/` is the CMN-700 TRM. Line 230 says "29 to 30 ns" and the figure says 30 ns | Name the three PDFs at line 215 |
| F21 | Lines 52, 86, 266, 302, 320, 330, 336, 343, 396, 534, 959 and 969. Also lines 245 and 251 | These lines give values from the counter files of `crb/results/uncore2-20261030T203752Z/`: 0.62 TB/s and 0.45 accesses per line (40 threads), 2.9 % misses, 81 % and 19 % (one reader at 8 MiB), and the 54 GB/s of line 266. In all 8 counter files of that folder every counter ran for 49 or 50 % of the run, and perf scaled the counts to the whole run [Ref11][Ref28]. The report gives the values with no "est.". For one reader at 8 MiB a count over the whole run exists. It gives 0.83, and the report has it at lines 232, 268, 308 and 312 [Ref29]. No count over the whole run exists for the 40-thread test. The first counter pass of the same day (`crb/results/uncore-20261030T203537Z/`) has the same property: 352 of its 354 counter rows ran for less than the whole run, most of them for 28 %. Report lines 245 and 251 give values of that pass with no "est.". Lines 97 and 113 held the 0.62 TB/s in the same way. They are corrected (section 9) | Mark the values of these lines "est.", as lines 97 and 113 now do. At lines 266, 330 and 959 use the 83 % and 17 % of the root run of 2026-11-02. A new counter run of the 40-thread test with fewer events at a time would give counts over the whole run. Not run |
| F22 | Line 296, caption of the whole-chip chart | "DRAM uses 32 to 60 threads, one per pair, 256 MiB each." This fits the copy bar only (48 threads, one per pair). The read bar is from 30 threads, and the write bar is from 16 threads [`results/followup2-20261031T073513Z/spread.csv` lines 20 and 5, `results/followup-20261030T194205Z/dram.csv` line 75]. Line 397 has the right values | "DRAM uses 256 MiB per thread: 30 threads spread 4 cores apart for read, 16 threads spread 8 cores apart for write, and 48 threads, one per pair, for copy." |
| F23 | Lines 230, 259 and 778 | "2.6 ns" for one crosspoint hop. The table at line 227 gives a median of 2.67 ns. The file of the final run gives 2.668 ns [`results/sudo-20261102T054936Z/core-positions.json`], and the brief says 2.7 ns. The figure label at line 778 gives 19.0 ns, 2.6 ns and 42 ns. A checker reports that the cells of that figure show 20.8 and 43.2 ns. I did not recompute those two cells | Lines 230 and 259: "2.7 ns". Line 778: take its three numbers from the final run |
| F24 | Lines 268, 316 and 964 | Memory requests per line of one writer at 8 MiB. Line 268 says 0.76. Lines 316 and 964 say "about 1". A checker reports that 0.76 is the count of mesh 0 and that mesh 1 counted 0.38 more. I did not recompute the 0.38 | Give one value and name its mesh at lines 316 and 964, for example "0.76 memory requests per line on mesh 0" |
| F25 | Lines 265 and 385 | "Footprints: ... per thread" and "Level (footprint)". The sizes are buffer sizes. A copy thread has two buffers of that size, so its footprint is two times the value [Ref33] | Line 265: "Buffer sizes: L1 = 32 KiB, L2 = 1 MiB, SLC = 8 MiB, DRAM = 1 GiB per thread. A copy thread has two buffers of that size." Line 385: "Level (buffer size)" |
| F26 | Line 63, and references at lines 125, 183, 199, 251, 259, 316, 437, 454 and 464 | The contents entry says "(part 5)", and its heading at line 269 says "(part 5, 2026-11-02)". The nine references quote only the first part of a heading. Each short form fits one heading only, so none is ambiguous | Use the full heading text |
| F27 | Latency figure, script lines 492 and 505 | Two labels are drawn over each other: the band label "DRAM" and the label "DRAM: 148 ns (415 cycles)". A checker saw this in a browser render of the report before and after the rename. I did not render that figure | Move one of the two labels |
| F28 | Brief line 46, `crb/make-brief.py` lines 47 and 48 | The values per thread are from repetition 0 (869 GB/s on one mesh, 25 to 30 GB/s each, 58 to 60 GB/s each on the other mesh). The total is from the best repetition (1372 GB/s). The parts of repetition 0 add up to 1342 GB/s [`results/followup3-20261102T031936Z/perthread-asmread-3M-40.csv`] | Take all values from repetition 2: 890 GB/s on one mesh (26 to 30 GB/s each), 59 to 62 GB/s each on the other mesh, 1372 GB/s total |
| F29 | Brief line 32, `crb/make-brief.py` line 173 | "29 avg (85)". 29 ns is 81 cycles at 2.8 GHz. The report gives 30 ns and 85 cycles. A checker reports a mean of 29.41 ns over the rows of the root run, which is 82 cycles. I did not recompute that mean | Make the two numbers agree: "29 avg (82)" or "30 avg (85)" |
| F30 | Brief line 40, `crb/make-brief.py` line 181 | "the same port carries 82 GB/s with the partner core, 229 GB/s with 4 writers". The four writers ran on four ports (CPUs 2, 4, 6 and 8, report line 287). The line also repeats "inside the core" with no limit to 8 MiB | The text for the brief under P3 in section 10.6 |
| F31 | Line 278 | "1.8 × 10^9 flits per second". The raw counts give 1.85 × 10^9 [Ref5, lines 98 to 101 and 108 to 111: 3,338,638,175 data flits in 1.7999 s] | "1.85 × 10^9 flits per second" |
| F32 | Line 289 | "the number of write transactions the core's L2 interface keeps outstanding, times the round trip to the home node, sets the rate" and "the limit is latency times in-flight count". The relation is the other way round. With a fixed number of writes in flight, a longer round trip gives a lower rate. So the rate is the number in flight divided by the round-trip time | P3 in section 10.6 holds the corrected wording |
| F33 | Line 343 | "two partner cores share one port and together get no more than one". At 8 MiB two partner cores together read 1.15 to 1.17 times as much as one core alone (77.5 to 78.5 GB/s against 66.9 to 67.5 GB/s). That the port is the limit is hypothesis 2 | "one thread per pair. At 8 MiB two partner cores together read only 1.15 to 1.17 times as much as one core alone (section "The pair finding")." |
| F34 | Style rule at line 32, tables with text columns (for example lines 102 to 121) | One rule aligns every table cell but the first to the right. A browser render shows the long texts of the column "Source" set flush right, which is hard to read. The rule is older than this update | Add a class for tables with text columns that aligns their cells to the left |

## 7. Verification

| Check | Result |
|---|---|
| Figure geometry: `python3 crb/tmp/agent-scratch/spec-row-2026-11-11/check_geometry.py crb/crb-memory-hierarchy.html 6` | PASS. Every label fits its box with at least 8.3 units of padding. The two rows share x and width in all six columns. The gaps are 10 units |
| Figure render with the page font (`render.py`, cairosvg) | Viewed before and after. No overlap and no clipping. The text of the first row differs from the old figure only by the removed words ("1 core" twice and "640 GB/s theoretical peak" once). Positions and widths changed as listed in section 2. The render draws normal text with the Medium weight of the font, which is 1 to 2 % wider than the page's Regular weight. The fit result is therefore on the safe side |
| Fallback fonts | Every label still fits with a font 5 % wider and with Helvetica or Arial widths. This is a reviewer computation. With DejaVu Sans (14 % wider) four labels overflow. Segoe UI was not measured |
| HTML structure, by script | 0 tag mismatches. Both script blocks and the style block are byte-identical to the backup. All 58 ids and all 38 href attributes (37 links in the page and the link to the font stylesheet) are unchanged. Checked again after the changes of sections 8 and 9. The open item now nests lists 4 levels deep. The backup had 1 level |
| Diff against the backup | 19 hunks with `diff -U0` (7 with the default context of three lines), all listed in sections 2 and 5. Still 19 after the changes of sections 8 and 9. Against the report of round 2 the diff has 2 hunks, lines 97 and 113 (section 9). Against the round-1 state of the report the diff has 9 hunks: lines 97, 113, 118, 125, 131 to 133, 420 to 423, 425 to 429, 431 to 437 and 452. Section 8 names each of them |
| Mesh clock, core clock, flit rates: `mesh_clock.py` on the raw file | 78 rows at 1.999465 to 1.999994 GHz. Core 2.79977 to 2.80011 GHz. Port 0.9169 data flits per mesh cycle for one reader |
| Bus and port counts: `port_counts.py` on the raw file [Ref24] | One reader at 8 MiB: 3.3059 bus accesses, 1.6529 bus writes and 0.8264 L2 refills per line, and 1.6530 data flits per line at the port. One writer: 1.5241 bus writes per line at 8 MiB and 1.9982 at 1 GiB, which is 0.982 per mesh cycle. CPU 2 with its partner also writing: 0.495 bus writes per mesh cycle and 1.5236 bus writes per line that it wrote itself. Each value per mesh cycle is the bus writes per second divided by 2.0 × 10^9 (est.). The runs that counted the bus writes did not count the mesh cycles. The nine 2 s runs of one case differ by 0.0 to 2.2 % in loop rate. Every counter row of part 5 ran for 100 % of its run (598 rows, column 5 of the raw file) |
| Share of the lines of one reader at 8 MiB that cross the port, recomputed from the raw rows | Port flits: 1.6530 per line, which is 0.8265 of the lines [Ref5]. L2 refills: 0.8264 per line [Ref5]. Accesses to the mesh cache in part 3: 1,650,550,050 for 1,994,522,624 lines, which is 0.8275 per line, with both counters at 100 % of the run [Ref29]. Scaled count of 2026-10-30: 850,985,083 for 1,047,920,640 lines, which is 0.8121 per line, with the counters at 49 % of the run [Ref28] |
| Arm documents | Each cited page was opened and the cited words were found: SOG pages 10, 11, 12, 13, 14, 15, 19, 23, 24, 25, 26, 38, 52, 55. TRM pages 54, 101 to 102, 280, 386, 671 to 672, 1016, 1656, 1678 to 1679, 2120. SVK user guide pages 3, 6, 7, 10. CHI specification pages 469 to 470. TRM page 89 (Figure 2-25) was read as an image by review agents, not by me |
| Firmware image of Q2 [Ref17] | Read again as bytes on 2026-11-12: the two values, the text "PhoenixCfg1", the names before and after INTPLL_MAIN, and the 46 offsets of the 8-byte value 2,000,000,000 |
| Web sources of Q4 and D9 | Arm's product brief and the pages of Ampere, AWS and NVIDIA were downloaded on 2026-11-12 UTC and searched as text [Ref13][Ref20]. Copies are in `crb/tmp/agent-scratch/spec-row-2026-11-11/web-2026-11-12/` |
| Arithmetic | 3 × 2.8 GHz × 16 B = 134.4 GB/s. 2 × 2.8 GHz × 16 B = 89.6 GB/s. 10 × 8000 MT/s × 8 B = 640 GB/s. 32 B × 2.0 GHz = 64 GB/s. 128 B × 2.8 GHz / 66.76 GB/s = 5.37 cycles. 16 / 5.37 = 2.98 per cycle. 20 / 5.37 = 3.7 per cycle. 4 / 5.37 = 0.745 and 4 / 5.34 = 0.749, so at most 0.75 per cycle. 1 − 66.76 / 89.6 = 25 %. 3 × 3/5 × 16 B × 2.8 GHz = 80.6 GB/s. 1.5 × 3/2 × 16 B × 2.8 GHz = 100.8 GB/s. 44.04 / 44.8 = 0.98 and 44.78 / 44.8 = 1.00 loop passes per cycle. 88.01 / 89.6 = 0.98 and 88.78 / 89.6 = 0.99. 64 / 0.8265 = 77.4 GB/s and 64 / 0.8121 = 78.8 GB/s. 77.51 × 0.8264 = 64.05 GB/s and 78.45 × 0.8275 = 64.92 GB/s. 77.51 × 0.81207 = 62.94 GB/s and 78.45 × 0.81207 = 63.71 GB/s. 64.05 / 64 = 1.00 and 64.92 / 64 = 1.01 flits per mesh cycle. 64.05 GB/s / 32 B = 2.00 × 10^9 and 64.92 GB/s / 32 B = 2.03 × 10^9 bus reads per second. 62.94 / 32 = 1.97 × 10^9 and 63.71 / 32 = 1.99 × 10^9. 78.45 × 0.81 = 63.5 GB/s. 1 − 0.8265 = 17 %. 64 × 2 / 1.5241 = 83.98 GB/s. 81.41 / 83.98 = 0.97 and 82.34 / 83.98 = 0.98. 64 / 0.8275 = 77.34 GB/s, and 78.45 / 77.34 = 1.01. 62.99 / 64 = 0.98 and 63.18 / 64 = 0.99. 113.24 / 2 = 56.6 GB/s, and 56.6 / 64 = 0.88. 63.18 − 62.99 = 0.19 GB/s, which is 0.3 % of 62.99. 1,348.80 − 898.80 = 450.00 GB/s. 3.47 / 9.72 = 36 %. 3,553,584,520 bus writes in 1.8094 s = 1.96 × 10^9 per second, and 1.96 / 2.0 = 0.98. 1,782,823,128 bus writes in 1.8000 s = 0.99 × 10^9 per second, and 0.99 / 2.0 = 0.50 |
| Internal review, round 1: six independent agents on the first version of the edit | 19 major, 42 minor and 39 note findings. All 19 major findings are applied or listed in section 4 or 6 |
| Internal review, round 2: four independent agents on the corrected report and on the first version of this record | 4 blocker, 8 major, 47 minor and 13 note findings. The 4 blockers named two false statements in the first version of this record: the claim that every finding was applied or listed, and a file-table row for a review file that did not exist yet. Both are corrected. The 8 major findings are applied or listed in section 4 or 6 |
| Login to CRB | One login at 21:00 UTC on 2026-11-11. The first command checks the RUNNING marker and stops the script when it is present [Ref8]. The saved output records a load of 0.00 and no other login. Read-only commands. The channel #phoenix-crb was read before the login. Its newest message was dated 2026-11-10, and no message announced a block for 2026-11-11 [Ref15]. No login after that |
| External review, round 1 of the review loop (reviewer agent, 2026-11-12 00:41 UTC) | 4 findings, CRB-R1 to CRB-R4. All 4 are accepted and applied. Section 8 lists them |
| External review, round 2 of the review loop (reviewer agent, 2026-11-12 04:24 UTC) | The reviewer's entry says that CRB-R1 to CRB-R4 are resolved. It holds 1 new finding, CRB-R5. It is accepted and applied. Section 9 lists it. The same entry confirms the two submitted hashes, the hunk counts (9 and 19) and the counts of `port_counts.py` |
| Internal check of the changes of section 8: five independent agents, one for each reviewer finding or pair of findings, one for plain English, and one that acted as the reviewer. A second agent then tried to refute each finding | 77 findings: 9 major, 38 minor and 30 note. The second agents confirmed all 47 major and minor findings. They lowered 3 of them from major to minor and 7 from minor to note. All 47 are applied. Of the 30 notes, 26 are applied, 2 are applied in part and 2 are not applied. The 2 notes that are not applied: a second counter (stall cycles) for the saturation test, and a sentence on the placement of the threads in report line 113 (report line 344 has it). The open part of one other note is not applied either: a quotation from the CHI specification about resource planes (a flow-control feature of CHI links). The open part of the last note, the split of three long list items, was applied after the second check |
| Second internal check, after the findings of the first check were applied: four independent agents (data and logic of the report, claims of this record, a reading as the reviewer, plain English). A second agent then tried to refute each major and minor finding | 78 findings: 5 major, 55 minor and 18 note. The second agents judged the 60 major and minor findings. They confirmed 59 and rejected 1. They kept 3 as major, lowered 2 from major to minor and 7 from minor to note. Several findings name the same defect. The 3 findings that stayed major name these defects. First, the share 0.81 was a scaled count, and the text gave it as a count. Second, the write comparison of the capacity item used the conversion and did not say so. Third, the item on the older statements called them wrong for write streams and said that this does not depend on the hypotheses. But "the port limits" is hypothesis 2. All 59 confirmed findings are applied. Before I applied a finding that cites data or a source, I checked that evidence in the raw file or on the cited page. One confirmed finding had an optional part that is not applied: the caption at report line 97 keeps wording A. Of the 18 notes, 16 are applied and 2 in part. Their open parts: the 60-thread run in the file of the series is named in [Ref11] and not in the report, and report line 118 says "two read loops" and does not give the rate of each loop |
| Third internal check, on the text that changed after the second check: three independent agents (numbers and logic, this record against the report and the sources, a reading as the reviewer with plain English). A second agent then tried to refute each minor finding | 43 findings: 0 major, 25 minor and 18 note. The second agents judged the 25 minor findings. They confirmed 24 and rejected 1, and they lowered 3 of the 24 to note. All 24 are applied. The main ones are these. First, the conversion item said that one failed comparison makes all converted numbers wrong. Second, the report called the four kinds of run "the tests of hypothesis 2" and also said that the test of hypothesis 2 was not run. Third, three values of bus writes per mesh cycle came from runs that did not count the mesh cycles. Fourth, the runs behind the shares 0.81 and 0.83 also differ in loop rate (67.1 against 70.7 to 71.0 GB/s). All 18 notes are applied too. The rejected finding asked that each sub-item can be read alone, and no change was made for it. The corrections of this third check were not read by another agent. I checked them by script: the numbers, the quotations of report text in this record, the report line numbers, and the HTML structure |

Not done:

- No browser render. This machine has no browser, and the reviewer could not start one either. The first figure was rendered with cairosvg. The charts that the page draws by script, the long table cells and the nested lists in "Open items" (4 levels) were not rendered. Line 452 of the report holds two entries of the word list on one source line, and line 132 holds five paragraphs. These were not rendered either.
- Minor and note findings of the two internal rounds before the review loop were applied where they concerned new text. I did not check each of those 141 findings one by one after the last edit.
- No benchmark was run on CRB. The tests named in Q7 and D1 are open.
- A local cross-build of `bandwidth.c` was not possible. The permission system declined to run the downloaded compiler. The disassembly from CRB made it unnecessary.
- The brief and the technique page were not checked (F13).

## 8. Changes after the external review, round 1

The reviewer agent of the review loop read the report and this record. It wrote four findings on 2026-11-12 at 00:41 UTC. All four are accepted. No benchmark was needed for any of them.

| Finding | What the reviewer asked | What changed | Where |
|---|---|---|---|
| CRB-R1 | Keep the capacity of the port apart from the question whether a test fills it. Remove the rejection threshold of 0.95 flits per mesh cycle or justify it | The open item now holds two hypotheses (capacity, saturation) and the conversion with its two assumptions. Each has its own missing test. A low rate no longer rejects the capacity. A count mismatch tests the conversion. One kind of mismatch, more bus reads than port flits, can also mean a second data channel, and the text says so. The threshold is removed, and the text says why none is set | Report lines 118 and 420 to 437. Record D1 and D2 |
| CRB-R2 | Do not present an observed loop rate as an established limit. Limit "No other limit in Arm's guide is reached" to the limits that were checked | The sentence is replaced by the list of the limits that were checked, and the paragraph ends with "The cause of the remaining gap is not established". In this record, one loop pass per cycle is an observed rate. A bound from Arm's guide, a hypothesis and its test are labelled as such. Q7 no longer says that the "Words used here" entry states a limit. The proposed text of F14 states no cause | Report lines 132 and 133. Record Q7 and F14, Ref2, Ref16 |
| CRB-R3 | Do not assign the increase of 450 GB/s of 2026-10-30 to the threads on mesh 1, because only the run of 2026-11-02 recorded each thread | Q1 keeps the totals of the series of 2026-10-30 apart from the totals per mesh of other runs. The attribution is labelled as an interpretation | Record Q1, Ref11 |
| CRB-R4 | The row "Other vendors of CMN-based chips" claims an interconnect that the NVIDIA page does not support | The row is now "Other Arm server CPUs" and compares the words only. A note says what each page states about its interconnect | Record Q4, Ref13, Ref20 |

Two internal checks then read the corrected texts (section 7). They found more places with the same four kinds of defect. The table lists them by kind. "Round 1" marks a defect that was in the text that the reviewer read. "Draft" marks a defect that was only in a corrected version of this round, which the reviewer did not see.

| Kind | Place | Correction |
|---|---|---|
| Capacity against saturation (CRB-R1) | Round 1. Report line 118: "the hypothesis does not conflict with the measured ~80 GB/s (est.)" | The converted rate on the port is 64 to 65 GB/s (est.), at or just above 64 GB/s. The text says that the estimate cannot decide |
| Capacity against saturation (CRB-R1) | Round 1. Report line 430 (now 437): "If the hypothesis holds, "The single-writer limit is inside the core" also does not hold at 1 GiB" | The step from 98 % of the capacity to "the port limits the writer" now needs hypothesis 2 |
| Capacity against saturation (CRB-R1) | Round 1. Report line 430 (now 437) and record D2: the two older statements "are wrong for write streams", and this "does not depend on the hypothesis" | The measured rates show that two partner writers share one limit at 1 GiB. That the full port is this limit is now part of hypothesis 2 |
| Capacity against saturation (CRB-R1) | Draft. Report lines 433 to 435: the test for the capacity and the test for the conversion read one result in two ways | For reads, more bus reads than mesh cycles cannot separate a wrong hypothesis 1 from a wrong first assumption. The text says so. Tests for writes are added |
| Capacity against saturation (CRB-R1) | Round 1 and draft. Round 1: report line 425 (now 427) said "so every line crosses the port as 2 flits", and the D1 table of the record said "Writers at 1 GiB, where every line crosses the port". Draft: report line 433 said "Every line of a 1 GiB buffer leaves the core, so this rate is the rate through the port" | Line 427 names the first assumption and marks the step "est.". The row of D1 names both assumptions and marks its ratios "est.". The write comparison at line 433 names both assumptions of the conversion and the two counts that are missing |
| Capacity against saturation (CRB-R1) | Draft. Report line 435: one failed comparison made "the converted numbers in the items above" wrong, and the text said that this result does not test hypothesis 1 | The item now says which comparison tests which assumption. It says that more bus reads than port flits can also mean a second data channel |
| Capacity against saturation (CRB-R1) | Draft. Report lines 421, 423 and 427 called the four kinds of run "the tests of hypothesis 2". Line 431 said that the test of hypothesis 2 was not run | The runs are now called "the runs of hypothesis 2" |
| Observed rate against limit (CRB-R2) | Round 1. Report line 132: "The vector adds explain only part of the gap". The dispatch limits: round 1 named three of the eight, and a draft named four | The first sentence states a bound. All eight dispatch limits are named and compared |
| Observed rate against limit (CRB-R2) | Round 1 and draft. Report line 132: operations "enter the pipelines". This read as a conflict with "Each pipeline accepts one operation per cycle" (line 123) | The text now says that these are limits of dispatch, the step before the pipelines |
| Runs kept apart (CRB-R3) | Round 1. Report lines 97 and 113: the 1.38 TB/s counter run and the series of runs with 8 to 40 threads read as one test | Both texts now name the separate series of runs. Line 113 cites the file of each |
| Runs kept apart (CRB-R3) | Round 1. Report line 423 (now 425) and record D1: pair rates of two loops in one range, and the share 0.81 with only a pointer to another section | The item and D1 name the loop of each rate. They also name the counter and the source of each share |
| Runs kept apart (CRB-R3) | Round 1 and draft. Report lines 118, 425 and 433, record D1 and F15: the share 0.81 was given as a count. Its counters ran for 49 or 50 % of the run, and perf scaled the counts. The run of the 0.81 also had another loop rate (67.1 GB/s) than the runs of the 0.83 (70.7 to 71.0 GB/s) | The share is 0.83 by three counters that ran for the whole run. The 0.81 is marked as a scaled count (est.), and the item gives the loop rate of each run. With 0.83 the converted pair rates are 64.1 to 64.9 GB/s on the port (est.). The earlier text said 63 to 65 GB/s |
| Runs kept apart (CRB-R3) | Round 1 and draft. Report lines 424 and 430 (now 426 and 437) and, in the draft, line 434 gave bus writes "per mesh cycle" for runs that did not count the mesh cycles | The text gives the bus writes per second first. It marks the value per mesh cycle "est." and names the mesh clock of 2.0 GHz |
| Runs kept apart (CRB-R3) | Draft. Record Q1: "8 of the 40 threads" stated for the counter run, whose files hold no CPU list. Also: "These sums differ from 450 GB/s, because they are from another run" | The placement of the counter run is now a condition ("If the run used the CPU list of the series"). The sums and the 450 GB/s are named as two different quantities |
| Runs kept apart (CRB-R3) | Draft. Report line 422: "three separate runs" for three counts that come from six runs | "Each of these three counts is from its own pair of runs" |
| Source against claim (CRB-R4) | Round 1. Record Q2: "2,000,000,000 Hz next to the PLL name INTPLL_MAIN" | The value and the name are 73.5 MiB apart. The row now says that it is consistent with 2.0 GHz and does not establish it |
| Source against claim (CRB-R4) | Round 1. Record D7 and D9: statements about CRB and about Arm's highest values with no source | D7 cites the inspection record and the module inventory. D9 adds the values of Arm's product brief and says which values the report gives |
| Source against claim (CRB-R4) | Round 1. Report line 131 and record Q7: "the same package on both days", with no record for the build day | Both texts name the two days that have a record (2026-10-30 and 2026-11-11) |
| Source against claim (CRB-R4) | Round 1 and draft. Round 1: report lines 424, 425 and 430 (now 426, 427 and 437) and record D1 and D2 said "bus writes of 32 B". The record's entry "Bus write, bus read" said "one data transfer of 32 B". Draft: report line 452 said "One transfer moved 32 B in part 5". All of them stated a part of the first assumption as a fact. The draft also left out Arm's sentence on snoops | Report lines 426, 427 and 437 and record D1 and D2 no longer say "bus writes of 32 B". Line 427 gives the 32 B under the first assumption and marks it "est.". Both word lists say that the text takes one transfer as 32 B. The entry at line 452 also says what Arm's list says and how many snoop flits the port counted |
| Source against claim (CRB-R4) | Round 1 and draft. Round 1: the row "One reader, counted at its port" of record D1 said "This counter covers one data channel" and cited only the raw file. Draft: report line 428 said "The counter covers one data channel", and report line 433 gave the values of the register field. Neither had a source | Report line 428 and the row of D1 cite TRM pages 1678 to 1679. Line 433 says that the manual does not say which value of the field stands for which number of channels, and it names the assumption |
| Source against claim (CRB-R4) | Draft. Report line 113: the sentence on 40 threads of 3 MiB cited the counter file, which holds neither value | Each of the two sentences cites the file that holds its fact |
| Source against claim (CRB-R4) | Draft. Record Q4, note: "a future product" | The note quotes the page |

Other changes of this round:

- Evidence for the conversion from the existing raw files: the new script `port_counts.py` [Ref24], Arm's description of the bus events [Ref26], the count of part 3 [Ref29], report line 422 and the new "Words used here" entry at report line 452.
- The three vendor pages and Arm's product brief were downloaded and read as text. The earlier reading came through a tool that summarises pages.
- Report line 125: "confirms the second mix" became "is a measured case of the second mix". Q5 of this record already used these words.
- Report line 131: the sentence on the source copy of 2026-10-30 now names `k_write` and `k_copy` next to `k_read` [Ref22]. Its conclusion now covers the three loops compiled from C. Line 133 uses the instruction counts of the write and copy loops.
- Report line 133: the sentence on the write and copy loops is now two sentences. It says "A general limit", gives the instructions per pass (4 and 5) and names the buffer sizes (32 KiB and 1 MiB).
- Report lines 421, 423, 426 to 429 and 431: wording and added numbers. The four kinds of run of hypothesis 2 are named one by one and are called "the runs of hypothesis 2". The list items are called "items", not "rows". The "first part" of the conversion became the "first assumption". Line 423 gives the measured rates of these runs as 0.97 to 1.01 of the allowed rates (est.). It also gives the 0.88 of the run with two busy pairs. Line 426 gives both measured values of the pair write rate. It says that the bus writes of CPU 2 are half of the capacity of hypothesis 1 (est.). It adds that CPU 2 sent 1.52 bus writes per line that it wrote itself. Line 427 gives the ratios 0.98, 0.99 and 0.88 against 64 GB/s. Line 428 gives the loop rates of the 18 runs of case r8M-c2: 67.3 and 69.6 GB/s in the first two runs, and 70.8 to 71.2 GB/s in the 16 later runs [Ref5]. Line 429 adds the count on the four mesh links that is not explained. Line 431 says that first results exist for writes.
- Report line 437: the heading changed from "Older statements that need a correction" to "Older statements that the new rates put in doubt". The item names one more older statement: "For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2" (D2).
- Plain English in the report. The long sentence of line 420 is split. Line 132 holds five paragraphs. The items at lines 422, 425, 433, 434, 435 and 437 hold sub-items. The reading rules of line 423 moved to a new last item, "How to read these items", on line 429. The entry at line 452 is split into two entries. Each of these stays on its source line.
- Between round 1 and this round the report grew from 970 to 978 lines. Lines after 420 moved down by up to 8 lines. The line numbers in this record are updated.
- Section 6 has one new item, F21: older text of the report gives values from scaled counts with no "est.".
- This record also changed outside the places named in this section: the Short version and the new section "The three corrections", "Words used here", sections 1, 2, 5, 6 and 7, and the references. These edits are not listed one by one.

## 9. Changes after the external review, round 2

The reviewer's entry of 2026-11-12 at 04:24 UTC says that CRB-R1 to CRB-R4 are resolved. It holds one new finding. It is accepted. No benchmark was needed.

| Finding | What the reviewer asked | What changed | Where |
|---|---|---|---|
| CRB-R5 | This change revised the caption and the source row of the first figure. Both still gave the 0.62 TB/s with no "est.", and F21 listed both as text outside this change. Mark the value and its reading as a lower bound as estimated in both places. Say that each cache-access counter ran for about half of the run and that perf scaled its count. Do not list the two places as uncorrected in F21 | The caption now says "an estimated lower bound" and "0.62 TB/s (est.)". It adds: "Each of these counters ran for about half of that run, and perf (the Linux counter tool) scaled its count to the whole run." The source row now starts with "From the mesh counters (est.)" and says "An estimated lower bound". It adds: "The value comes from two counters, one for each mesh. Each ran for 49 % of the run, and perf scaled its count to the whole run", with the counter file as its source. F21 no longer lists lines 97 and 113 | Report lines 97 and 113. Record: wording B of Q1, section 2 (cell lengths), C3 and C7 of section 5, F10 and F21 of section 6, section 7 |

How it was checked:

- The two counters are lines 3 and 7 of the counter file of that run. Column 5 of both lines is 49.00 [Ref11].
- The mechanical checks of section 7 were run again after the change. The geometry check prints PASS. The HTML has 0 tag mismatches. The diff has 19 hunks against the backup, 9 against the round-1 report and 2 against the report of round 2 (lines 97 and 113).
- A script confirmed that wording B of Q1 is in report line 113 word for word.
- I searched the text that this change wrote or revised for other values of the scaled counts. Report lines 425 and 433 and this record already mark each such value "est.". One place had no label: F10 of this record named the 54 GB/s of report line 266. It now says that the value is from scaled counts.

Not changed:

- The label "≥0.62 TB/s whole chip" in the figure (line 86), and the first cell of the source row (line 113), which repeats that label. The caption and the second cell of the row now carry the qualification. Line 86 stays in F21.
- The other lines of F21. The reviewer's finding leaves them deferred.

## 10. Changes after the review loop (2026-11-12)

The review loop ended on 2026-11-12 at 04:30 UTC. Its last entry names the digest `81bef21aae0ea4628c114234a2f40f6b0644f5d62fcb1d71b5a1bfa09e5ba864` of this record and the report with the sha256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3` (section 9). After that the author decided two open points and sent five comments on the report. This section lists what changed since then. The reviewer agent has not read these changes.

| File | State after this section |
|---|---|
| `crb/crb-memory-hierarchy.html` | 978 lines, as before. 93 lines differ from the reviewed state. sha256 `REPORT_SHA256` |
| `crb/tmp/crb-memory-hierarchy.before-slc-rename.html` | Copy of the reviewed state of the report |
| `crb/make-brief.py` | The script that builds the brief. 10 lines differ from its copy `crb/tmp/make-brief.before-slc-rename.py` |
| `crb/crb-memory-hierarchy-brief.html` | The brief, built again with `python3 crb/make-brief.py crb/results/sudo-20261102T054936Z`. 11 lines differ from its copy `crb/tmp/crb-memory-hierarchy-brief.before-slc-rename.html` |

No line was added to the report or removed from it. So the report line numbers in sections 1 to 9 still fit.

### 10.1 The name "SLC" replaces "mesh cache"

The author confirmed the recommendation of Q4 and asked for the same change in the brief.

- **Rule.** "SLC (L3)" stands where the term is introduced and in main labels. "SLC" stands elsewhere. The word "mesh" stays where it means the interconnect, for example in "mesh counters", "mesh clock" and "own mesh".
- **Report.** 101 replacements on 77 lines. They include the places where the bare word "mesh" named the cache level, for example the chart rows "mesh read", "mesh write" and "mesh copy". These rows are now "SLC read", "SLC write" and "SLC copy".
- **Places with "SLC (L3)".** The sub-header (line 49), the first figure and its screen-reader label (lines 86 and 77), two rows of the source table (lines 111 and 119), the size table (line 144), the heading "The SLC (L3) and the pair port" and its contents entry (lines 178 and 60), the word list (line 454) and one chart label (line 492).
- **Sentences that were rewritten.** Line 49: the change log names the new term. Line 52: the Short version defines the SLC as "the shared cache in the on-chip mesh interconnect, which Linux lists as L3". Line 139. Line 179. Line 183: it says that versions before 2026-11-12 used the old name, and why. Line 454: the entry of the word list.
- **Heading.** The heading 'Why "mesh cache"' is now 'The mesh, and why older versions said "mesh cache"' (lines 182 and 60). The section under it describes the mesh.
- **Old name kept on purpose.** Six lines name the old term as a history note: lines 49, 60, 179, 182, 183 and 454.
- **Not changed.** The element ids and the link targets still contain "mesh-cache". No other file links to them. The identifiers in the page script are not changed.
- **Brief.** The generator got 8 replacements. One sentence was added to the caption of the first table: "SLC: Arm's system level cache, in the mesh. Linux lists it as L3." The label of the table row is now "SLC (L3), 128 slices of 1 MiB, 16-way".
- **Side effect in the brief, corrected.** The shorter label made the first column of that table narrower. A print with the local browser then broke two labels at a hyphen ("4-" and "way", "DDR5-" and "8000"). Four labels now keep their short parts on one line (generator lines 171 to 174). A new print has 2 pages and no such break [Ref35].
- **Other files.** These still say "mesh cache", and they were not changed: `crb/perf-measurement-tech.html` (9 places), `crb/crb-cross-check-bill.html` (12), `crb/mesh0-or-mesh1.md` (11), `crb/plan-2026-11-02.md` (16), four review records in `crb/` (9 in total), `crb/crb-memory-hierarchy-edited.html` (40, an older copy of the report) and three files in `bench/` (5 in total).

### 10.2 The author's comments of 2026-11-12 on the report

| Comment | Change | Lines |
|---|---|---|
| Source table: "The cycle number is derived: ns × 2.8 GHz." becomes "Cycles derived" | Done. The cell now ends with "Cycles derived." | 107 |
| Source table: the label "30 ns (85 cycles)" becomes "SLC latency avg: 30 ns (85 cycles)" | Done | 112 |
| Source table: the label "≥0.62 TB/s whole chip" becomes "SLC throughput ≥0.62 TB/s whole chip" | Done | 113 |
| Every "3 loads + 2 stores" becomes "3 loads / 2 stores" | Done in all six places: the Core box of the first figure, the row label of the source table, a reference to that row, the section heading, its contents entry and one sentence. The mixes "3 loads + 1 store" and "2 loads + 2 stores" keep the plus sign, because each names the operations of one cycle. This decides D6 | 82, 105, 116, 122, 58, 124 |
| The long paragraph on the read loop compiled from C: a better format, and a listing of the C code | Done. The list below gives the details | 131 to 133, 58, 35 |

The passage on the read loop compiled from C:

- It has its own sub-heading now: "The read loop compiled from C: 1.5 loads per cycle". The heading has the new id `the-read-loop-compiled-from-c` and a new contents entry at line 58.
- Three listings were added. The first is the C function `k_read` [Ref21]. The second is the function `k_asmread` with the hand-written loop [Ref21]. The third is the 16 machine instructions of the compiled loop, which are lines 44 to 59 of the saved output from CRB [Ref8].
- The script that wrote the passage copied the listings from these files. A check after the edit found each listing equal to its source.
- The limits that were checked are now one table. Its columns are "Limit in Arm's guide", "Allowed per cycle" and "This loop, average per cycle".
- The two hypotheses are a list. The predictions of the missing test are a small table.
- No statement and no number was changed. A script compared the sentences. Of the 60 sentences of the old text, 47 are in the new text word for word. The other 13 became list items, table cells or table rows.
- New sentences: a lead of four sentences under the sub-heading, two sentences that introduce `k_asmread`, the line "How the loop is counted:", and the sentence "The table below compares each limit with the average rate of the loop."
- The three source lines 131 to 133 are still three lines. A listing keeps its line breaks as the character reference `&#10;`.
- One style rule for the listings was added at line 35.

### 10.3 What "at 1 GiB" means

The author asked what "1 GiB" means in "Two partner cores together wrote 63.2 GB/s at 1 GiB".

- It is the size of the buffer of each thread. Each thread reads or writes its own buffer again and again [Ref33].
- The report now says so in three places: line 421 (the first place in "Open items" that uses the sizes), line 437 (the sentence that the author quoted) and line 457 (word list, entry "GB/s, TB/s").
- Line 457 also says that a copy thread has two buffers of that size. It names the sizes of the tests: 8 MiB and 1 GiB per thread for the bandwidth tests with one, two or four threads, and 3 MiB and 256 MiB per thread for the whole-chip tests [Ref33].

### 10.4 Corrections in "Open items" that the check found

The check of 2026-11-12 (section 10.7) found three places in the open item of this update that said more than the data show. They are corrected.

| Line | Before | Now | Evidence |
|---|---|---|---|
| 421 | The runs of hypothesis 2 included "two partner cores that write 8 MiB each" and "one core that writes 1 GiB" | Both are limited to the asm loop | With the write loop compiled from C one core writes 44.8 GB/s at 1 GiB. That is far below 64 GB/s [Ref31] |
| 425 and 118 | "No run counted the share for two partner cores." | "No run counted the share with only two partner cores busy." Line 425 adds the count of two runs with four busy cores on two pairs: 0.82 accesses to the SLC per line. In those runs each pair read 62.9 to 63.7 GB/s at the loops | [Ref32] |
| 429 | The list of runs that were not checked against the hypotheses named the copy runs only | It also names the write runs of the loop compiled from C: 75.6 GB/s for two partner cores at 8 MiB, and 44.8 GB/s for one core at 8 MiB and at 1 GiB | [Ref31] |

Seven smaller corrections of text that this section wrote were also applied: the first use of "SLC" at line 49, a citation at line 139 (pages 31 to 32), quotation marks at line 179, the heading at lines 182 and 60, one plural at line 297 ("The SLC bar is a lower bound"), the order of two sentences at line 454, and the pronoun "them" at line 421.

### 10.5 Answers to the author's questions of 2026-11-12

**What is a "flit"? Is it a known term?**

- Yes. "Flit" is short for "flow control unit". It is the smallest unit that the flow control of a network link handles.
- Arm's CHI specification defines it: "FLow control unIT (Flit) is the smallest flow control unit. A packet can be made up of one or more flits." and "A flit is the basic unit of transfer in the Link layer." [Ref30]. CHI (Coherent Hub Interface) is the protocol of CRB's mesh [Ref3, pages 12, 17 and 51].
- In CRB's mesh one data flit carries 32 B of data. So a 64 B line needs two data flits [Ref3, page 2120].
- The term is also used outside CHI. The mesh manual names flit formats of 68 B and 256 B for CXL (Compute Express Link) links [Ref3, pages 250 and 621]. A web search result says that PCIe 6.0 has a flit mode too [Ref36].

**"We measured 80 GB/s, but the hypothesis is 64 GB/s."**

- The two numbers are counted at two different places. The 80 GB/s (78 rounded) is every byte that the two loops read. The 64 GB/s is a calculation for the bytes that cross the shared port in one direction: one data flit of 32 B in each mesh cycle, at a mesh clock of 2.0 GHz.
- With a buffer of 8 MiB a part of the lines never crosses the port. The core's own L2 serves them. For one core alone this was measured: the loop read 71 GB/s while its port carried 58.7 GB/s toward the core [Ref5][Ref24]. Three counters give 0.83 for the share of the lines that cross the port.
- If two partner cores have the same share, 77.5 to 78.5 GB/s at the loops is 64.1 to 64.9 GB/s at the port (est.). No run counted the share with only two partner cores busy.
- Where every line must cross the port, the pair rate at the loops is itself close to 64 GB/s. Two partner writers with 1 GiB each write 63.2 GB/s together [Ref10]. With the loop compiled from C one writer alone writes 44.8 GB/s, and two partner writers reach the same 63.2 GB/s together [Ref31].
- At the loops the pair rate differs from test to test: 63 GB/s (writes at 1 GiB), 78 GB/s (reads at 8 MiB) and 82 GB/s (writes at 8 MiB with the asm loop). Converted to the port, the three are 62.0 to 64.9 GB/s (est.). That is 0.97 to 1.01 of 64 GB/s.
- So the rates fit the hypothesis. They do not prove it. A rate close to 64 GB/s also fits a port with a higher maximum that something else holds near that rate. The number of data channels at the port was not read from CRB. "Open items" in the report names the tests.

**Where are F1 to F21?** They are in section 6 of this record. They are not in the report. Entry 6 of the contents list of the report is "Latency".

### 10.6 Replacement texts for the older statements (proposed, not applied)

The author asked what the new statements would be. For the cause of each limit there is no definitive statement. The measured part can be stated definitively. Each text below gives the measured rates first and names the hypotheses as not confirmed. Two checkers compared every number with the raw files (section 10.7). None of the three texts is in the report.

**P1. For the second sentence of report line 380 ("For DRAM traffic the port is not the limit") and the last sentence of line 214 ("For DRAM streams the port is not the limit").**

> With a buffer of 1 GiB for each core, reads and writes behave differently on a pair. All rates are from 2026-10-30. The pair is CPUs 0 and 1. Reads. One core alone reads 28.2 GB/s with the read loop compiled from C and 30.5 GB/s with the asm loop. Two partner cores together read 52.6 GB/s with the compiled loop and 56.7 GB/s with the asm loop. So the second reader on the pair adds 24.5 GB/s or 26.2 GB/s. That is 87 % or 86 % of the rate of one core alone. So two partner readers are not held to the rate of one reader. Two cores on different meshes (CPUs 0 and 64) together read 54.9 GB/s with the compiled loop. That is 2.3 GB/s (4 %) more than the partner pair. CPUs 0 and 64 share neither a pair port nor a mesh. No run has two cores of different pairs on one mesh at 1 GiB. So the cause of this difference was not measured. Whether the pair port limits DRAM reads was not measured. Writes. One core alone writes 63.0 GB/s with the asm loop and 44.8 GB/s with the compiled loop. Two partner cores together write 63.2 GB/s with each loop. So the second asm writer adds 0.2 GB/s (0.3 %). Four writers on two pairs (CPUs 0 to 3) write 113 GB/s. So a second pair adds 50 GB/s. So two partner writers share one limit of about 63 GB/s. What this limit is was not measured. Hypothesis 2 of "Open items" says that the full pair port is this limit. Hypothesis 1 says that the port passes at most 64 GB/s in each direction. Neither is confirmed. The earlier reason, that DRAM latency limits each core first, is withdrawn. No run tested it.

The full text would go to line 380. At line 214 the last sentence would become: "With a buffer of 1 GiB for each core, reads and writes behave differently on a pair (section "The pair finding")." Sources: [Ref10], [Ref31], [Ref34].

**P2. For sentences 1 to 3 of report line 214 ("For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2").**

> For software. The rates below are for a buffer of 8 MiB for each thread, measured on 2026-10-30. Two threads on partner cores together read 77.5 to 78.5 GB/s (five runs on the pairs of CPUs 0 to 5, four with the read loop compiled from C and one with the asm loop). One thread alone read 66.9 to 67.5 GB/s on CPU 0. Two threads on cores of different pairs together read 125 to 134 GB/s (seven runs, best repetition of each). That is 125 to 132 GB/s on mesh 0 and 134 GB/s on two meshes. So two threads on two pairs read 1.6 to 1.7 times as much as two threads on one pair. These rates were measured with no other busy core. With two busy pairs (CPUs 0 to 3) four threads together read 127.6 GB/s with the asm loop and 129.1 GB/s with the compiled loop. That is 0.82 to 0.83 of two times the rate of one pair. In the root runs of 2026-11-02 one thread alone read 69.6 to 71.2 GB/s (CPUs 0 and 2, runs of 2 s). The cause of that difference is not known. All these rates count the bytes that the loops read. They include the lines that a core takes from its own L2. For one core alone that is 0.17 of the lines. No run counted it with only two partner cores busy. What limits the pair was not measured. Hypothesis 2 of "Open items" says that the full pair port is this limit. Hypothesis 1 says that the port passes at most 64 GB/s in each direction. The 78 GB/s and the 64 GB/s are counted at two different places. If 0.83 of the lines cross the port, as counted for one core alone, 77.5 to 78.5 GB/s at the loops is about 64 to 65 GB/s at the port (est.).

The first sentence of line 380 would become: "Two heavy threads on two pairs read 1.6 to 1.7 times as much as two threads on one pair (buffer of 8 MiB for each thread)." The old sentence "about 28 B per core cycle" is dropped. The port belongs to the mesh, and the mesh clock is 2.0 GHz, not 2.8 GHz. Sources: [Ref10], [Ref31], [Ref5], [Ref29], [Ref34].

**P3. For the whole paragraph of report line 289 ("The single-writer limit is inside the core").**

> What limits one writer at 8 MiB was not measured. The lines are not allocated in L1 or L2 (zero refills for writes, zero write-backs), so Arm's write-streaming behaviour is confirmed by measurement. One writer alone writes 70.4 to 73.2 GB/s with a buffer of 8 MiB (CPUs 0 and 2, runs of 2026-10-30 and 2026-11-02). With one writer the counters show almost no back-pressure. The links out of the crosspoint show 2 × 10^4 credit-stall cycles per second against 1.85 × 10^9 data flits per second. The home nodes of mesh 0 show 1 × 10^4 data stalls per second. Other runs sent more through the same parts. CPU 2 sent 1.68 × 10^9 bus writes per second at 8 MiB and 1.96 × 10^9 per second at 1 GiB. With the partner core also writing, the pair writes 81.4 to 82.3 GB/s. Four writers on four ports write 228 to 230 GB/s. These rates count the bytes that the loops wrote. At 8 MiB a line needs 1.52 bus writes, not 2, for a reason that is not known. So 82 GB/s at the loops is about 62 to 63 GB/s at the port (est.). This estimate uses the count of CPU 2. CPU 3 was not counted. The runs do not rule out a limit that depends on the shared path. With a second busy port each writer falls from 71 to 61 GB/s. With four busy ports each writer falls to 57 GB/s. No counter of part 5 covers the write data from the port to the crosspoint. Hypothesis, not tested: the core keeps at most a fixed number of writes in flight. Then the rate of one writer is that number divided by the round-trip time to the home node. The test is a per-core asm write sweep, like the per-core read sweep. It was not run. At 1 GiB the comparison with the partner gives another result. One writer alone writes 63.0 GB/s (CPU 0, 2026-10-30) and 62.9 GB/s (CPU 2, part 5). Two partner writers together write 63.2 GB/s (CPUs 0 and 1, 2026-10-30). So one writer alone already reaches the rate of the pair. What limits the pair was not measured. Hypothesis 2 of "Open items" says that the full pair port is this limit. One count fits it. The 1.96 × 10^9 bus writes per second of CPU 2 are 0.98 bus writes per mesh cycle at the mesh clock of 2.0 GHz (est.). If one bus write is one data flit at the port, that is 98 % of the capacity of hypothesis 1 (est.).

Sources: [Ref5], [Ref10], [Ref24].

If these texts are applied, other places change with them:

- Report line 437 lists the three old statements as current text and says "These sections are unchanged for now." It would then say that the sections were changed.
- Report lines 110, 213 and 377 give 134 GB/s for two cores of different pairs (F3), line 343 repeats the pair statement (F33), and line 379 names the wrong loop (F2).
- The brief repeats two of the statements at its lines 39 and 40 (F30). Proposed texts for the generator, line 180: "Pair port: cores 2k and 2k+1 share one crosspoint port. Two partner cores together read 78 GB/s with a buffer of 8 MiB each. That rate counts the lines from their own L2 too. Two cores of different pairs read 125 to 134 GB/s." Line 181: "What limits one writer at 8 MiB (70 to 73 GB/s) was not measured. The lines are not allocated in L1 or L2 (0 refills, 0 write-backs). The links out of its crosspoint show 2 × 10^4 credit-stall cycles per second against 1.85 × 10^9 data flits per second. With the partner core on the same port the pair writes 82 GB/s. Four writers on four ports write 229 GB/s. Hypothesis, not tested: a limit on the writes that the core keeps in flight. At 1 GiB one writer alone (63.0 GB/s) already reaches the rate of the pair (63.2 GB/s)."

### 10.7 Checks of this section

| Check | Result |
|---|---|
| Structure of the report, by script | 978 lines before and after. 0 tag mismatches. 59 ids (one new, none removed, none twice) and 39 link targets, all present. The two script blocks changed only inside 14 text strings and 2 comments, all by the rename. The style block has one new rule (line 35) |
| Figure geometry: `check_geometry.py crb/crb-memory-hierarchy.html 6` | PASS |
| Old names left in the report | "3 loads + 2 stores": 0 places. "mesh cache" outside ids and link targets: the 6 history notes of section 10.1 |
| Listings | Each of the three listings equals its source: `bench/bandwidth.c` lines 138 to 148 and 173 to 195, and lines 44 to 59 of the saved output from CRB (white space normalised for the third) |
| Brief | An unchanged copy of the generator rebuilt the old brief byte for byte, apart from the date. After the edits the brief differs from the old one in 11 lines: the date, the four label rows of the first table, its caption, three findings, one screen-reader label and one figure caption |
| Render with the local headless browser, with the network blocked [Ref35] | The report loads with no script error, and all 19 figures that the script draws hold elements. The changed section was rendered and viewed: the source table, the new sub-heading, the three listings, the limits table and the test table. The brief was printed: 2 pages, and page 2 starts at the page break. The first figure was also rendered with cairosvg and viewed. The browser had no copy of the page's monospace font, so the listings were viewed in the fallback font DejaVu Sans Mono |
| Check of 2026-11-12, first run: four checkers (rename in the report, brief and language, facts of the answers, replacement texts), each followed by a second checker that tried to refute every finding | 73 findings: 12 major, 36 minor and 25 notes. The second checkers confirmed 60, confirmed 13 in part and rejected none. They added 22 findings of their own. Applied: every finding about text that this section wrote. Not applied: the findings about older text. They are items F22 to F34 of section 6. The findings about the draft answers and the draft replacement texts are worked into sections 10.5 and 10.6 |
| What the first run changed in my own work | Three statements of the open item said more than the data show (section 10.4). The first draft of P1 to P3 called the limit of one writer "by elimination ... in the core" and gave the pair rate with no conversion to the port. Both are corrected in section 10.6. One new sentence at line 457 was wrong for the whole-chip tests and is corrected |

Not done:

- The reviewer agent of the review loop has not read the changes of this section.
- No benchmark ran, and no login to CRB was made.
- The page was not viewed in a normal browser with its web fonts. The listings were not viewed in IBM Plex Mono.
- The other files that still say "mesh cache" were not changed (section 10.1).
- P1 to P3 and F1 to F34 are not applied. They wait for the author's decision.

## References

- [Ref1] Notion page "Scratch", https://app.notion.com/p/3c3d132d3cfd80b38c47cc0f424f0511, last edited 2026-11-11 19:48 UTC.
- [Ref2] `crb/refs/arm-neoverse-v3ae-r0p2-software-optimization-guide-110075.pdf`. Page 11: instructions are "decoded into internal Macro-OPerations (MOPs)", and "A MOP can be split into two Micro-OPerations (µOPs)". This record calls a µOP an operation. Page 11 also: "Once dispatched, µOPs wait for their operands and issue out-of-order to one of 21 issue pipelines. Each issue pipeline can accept one µOP per cycle." Pages 12 and 13: Figure 2-1 and Table 2-1. Page 14, Table 3-1: the symbols V0 and V1 stand for the pipelines FP/ASIMD 0 and FP/ASIMD 1. Page 14 also: "Exec Latency is defined as the minimum latency seen by an operation dependent on an instruction in the described group." Page 15, Table 3-3: integer ADD ("ALU, basic"), latency 1 cycle. Page 19, Table 3-7: LDR, latency 4 cycles, 3 per cycle. Pages 23 to 25, Tables 3-13 and 3-14. Page 23: LDP of two q registers with an immediate offset, latency 6 cycles, 3/2 per cycle, load pipelines. The table gives no count of µOPs. Page 26, Table 3-15: vector ADD, latency 2 cycles, 2 per cycle. Page 38, Table 3-23: WHILELO, latency 2 cycles, 2 per cycle. Page 52, Table 3-28: ST1D with a scalar + scalar address, latency 2 cycles, 2 per cycle. Page 55, section 4.1 "Dispatch constraints": "Dispatch of µOPs from the in-order portion to the out-of-order portion of the microarchitecture includes several constraints.", "The dispatch stage can process up to 10 MOPs per cycle and dispatch up to 20 µOPs per cycle", "Up to 4 µOPs utilizing the S or B pipelines", "Up to 4 µOPs utilizing the M pipelines", "Up to 2 µOPs utilizing the M0 pipelines", "Up to 2 µOPs utilizing the V0 pipeline", "Up to 2 µOPs utilizing the V1 pipeline", "Up to 6 µOPs utilizing the L pipelines".
- [Ref3] `crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf`. Page 54: SLC definition. Page 89, Figure 2-25: channels at a device port. Pages 101 to 102: clock domains at one frequency. Page 280: "Supports two-cycle or three-cycle non-pipelined data array". Page 386, section 7.2.1: "The global clock signal or signals, clock the cycle counter." Pages 671 to 672: timeout register with reset value 0xC350. Page 1016: field data_ram_latency. Page 1656: field dat_vc_num_p, "Number of replicated channels on DAT VC at this port", with no table of values. Page 1678: the port event DAT, "DAT channel when POR_DAT_VC_NUM_PARAM = 1 ; DAT Sub-channel 1: when POR_DAT_VC_NUM_PARAM > 1", and the port event DAT2, "DAT Sub-channel 2: Applicable when POR_DAT_VC_NUM_PARAM > 1". Page 1679: "TX flit valid; signaled when a flit is successfully transmitted". Page 2120, Table A-2: "Data_Width N Fixed to 256".
- [Ref4] `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf`. Page 3: revision 3.0, based on firmware 0.9.0. Page 6: default memory speed 7200 MT/s. Page 7: mesh DVFS. Page 10: interconnect clock, core clock, twelve memory interfaces.
- [Ref5] `crb/results/sudo-20261102T211150Z/writepath.csv`. Lines 5 and 6: idle rows of `dtc_cycles`. Lines 226 and 237: core cycles of case w8M-c2. Lines 204 and 215: bus writes of case w8M-c2. Lines 386 and 397: bus writes of case w1G-c2. Lines 568 and 579: bus writes of CPU 2 in case w8M-c2c3. Lines 1051 and 1061: port data flits of case r8M-c2. Lines 1132 and 1143: all bus accesses of case r8M-c2. Lines 1114 and 1125: bus writes of case r8M-c2. Lines 1092 and 1103: L2 refills of case r8M-c2. Lines 1050 and 1060: snoop flits to the port in case r8M-c2. Lines 433, 451, 470, 490, 510, 530, 551, 573 and 595: the loop rates of the nine 2 s runs of case w8M-c2c3. Lines 970 and 979: the loop rates of the first two runs of case r8M-c2 (67.31 and 69.63 GB/s). The rows that start with `asmread,1,8388608,0,` from line 988 to line 1141: the loop rates of its 16 later runs (70.75 to 71.17 GB/s). Among them lines 1046 and 1056 are the runs with the port flits (70.79 and 70.98 GB/s), and lines 1086 and 1097 are the runs with the L2 refills (70.86 and 70.86 GB/s). Every counter row of the file ran for 100.00 % of its run (column 5). Event names such as `hns_slc_sf_cache_access_all` are in `crb/results/uncore2-20261030T203752Z/`.
- [Ref6] Output of `crb/tmp/agent-scratch/spec-row-2026-11-11/mesh_clock.py`.
- [Ref7] `bench/analyze_writepath.py` lines 55 to 57 (the subtraction) and line 58 (the per-cycle column uses the result).
- [Ref8] `crb/results/probe-20261111T210017Z.txt`: host state, firmware and kernel version, gcc version, the `-march=native` string, sha256 of the source and the binary, `/dev/scmi` devices, event names of `arm_cmn_0`, and the disassembly of `k_read`, `k_write`, `k_copy` and `k_asmread`. The commands are in `crb/results/probe-20261111T210017Z.cmd.txt`.
- [Ref9] Linux `drivers/perf/arm-cmn.c` in the kit's kernel source archive, lines 855 to 858 and 2537 to 2552. The archive is the source for firmware 0.9.0. CRB runs the kernel build for firmware 0.7.2, whose source is not in the kit.
- [Ref10] `crb/results/followup-20261030T194205Z/asm.csv` lines 11, 15, 67, 74, 102, 109, 144, 165, 169, 184, 188, 199, lines 166 to 168 and 181 to 183 (the three repetitions of one writer and of two partner writers at 1 GiB) and `pair.csv` lines 6, 12, 18, 30, 36, 48. The rows of `pair.csv` are from the read loop compiled from C. The rows of `asm.csv` are from the asm loops.
- [Ref11] `crb/results/slc-20261030T194835Z/slc.csv` lines 7, 14, 21, 28, 35 (best total of each thread count), lines 1, 8, 15, 22, 29 (the command of each run: CPU list `0-118:2`) and lines 27 and 34 (slowest, fastest and average thread of the best repetition with 32 and with 40 threads). The same file holds other runs that are not part of this series: write and copy runs, read runs with 40 and with 60 threads on CPU list `0-119` (lines 78 and 85), and three read runs of 120 MiB with other buffer sizes (lines 92, 99 and 106). The 60 buffers of the run at line 85 are 180 MiB together. `bench/bandwidth.c` line 408 (current source): thread i runs on the i-th CPU of the list. The source copy of 2026-10-30 [Ref22] has the same statement at line 281. Report, entry "chiplet" in "Words used here": CPUs 0 to 63 are on mesh 0. `crb/results/followup3-20261102T031936Z/perthread-asmread-3M-40.csv`, run of 2026-11-02: rows `thread,<index>,<CPU>,<kernel>,<repetition>,<GB/s>`. The 32 rows with a CPU below 64 sum to 868.52, 885.94 and 890.11 GB/s in repetitions 0, 1 and 2. The 8 rows with CPUs 64 to 78 sum to 473.26, 474.29 and 481.74 GB/s. Line 5 of the same file: slowest, fastest and average thread of repetition 2 (26.23, 61.56 and 34.30 GB/s). `crb/results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv`: mesh counters of a separate 40-thread run on 2026-10-30 at 20:37 UTC, with 6,247,492,962 accesses to the mesh cache on mesh 0 (line 3) and 3,471,244,819 on mesh 1 (line 7). Both are scaled counts (est.): each of the two counters ran for 49 % of the run (column 5). `bw-asmread-3M-40T-even.csv` in the same folder: the total of that run, 1,384.77 GB/s in one repetition of 1.0 s, and its slowest, fastest and average thread (26.86, 61.90 and 34.62 GB/s, line 3). Neither file of this run holds a CPU list.
- [Ref12] `crb/inspection-record-2026-10-30.md` lines 15 (product version EVT0), 17, 21 (128 CPUs), 22, 23, 38 to 40, 113.
- [Ref13] https://www.arm.com/static/az/pdf/product-brief/arm-agi-cpu-product-brief.pdf, page 3: "System-Level Cache 128MB", "Max Frequency" 3.5GHz, 3.5GHz and 3.7GHz for the 136-core, the 128-core and the 64-core model, and "RDIMM Memory 12x DDR5 up to 8800MT/s". Page 2: "operating at up to 3.2GHz, all-core clock speed with boost speeds up to 3.7GHz". Downloaded on 2026-11-12 UTC and read as text. Copy: `crb/tmp/agent-scratch/spec-row-2026-11-11/web-2026-11-12/armbrief/brief.pdf`.
- [Ref14] Kit, `tools/asct/reports/asct_run_output_a0_numa2_ddr_7200.txt` and `asct_run_output_a1_numa2_ddr_8000.txt`, lines 17 (number of CPUs), 41 to 56 and 166 to 172 of each. SPEC reports: `tools/spec2017-toolkit/reports/` and `tools/spec2026-toolkit/reports/`.
- [Ref15] Slack channel #phoenix-crb, read on 2026-11-11 before the login. A message of 2026-11-10 names the Arm support site and the channel ext-arm-positron.
- [Ref16] `crb/data-all.json` line 1223 (4.0000 cycles per load). `crb/results/20261030T193108Z/bandwidth.csv`, loops compiled from C with one thread, best of each case in the order read, write, copy. Lines 6, 10 and 14 (32 KiB): 66.76, 44.04 and 88.01 GB/s. Lines 62, 66 and 70 (1 MiB): 67.09, 44.75 and 88.78 GB/s. Lines 118, 154 and 190 (8 MiB): 66.99, 44.76 and 50.00 GB/s. Lines 214, 218 and 222 (1 GiB): 28.15, 44.78 and 42.19 GB/s. One loop pass per cycle is 44.8 GB/s for write (16 B per pass) and 89.6 GB/s for copy (32 B counted per pass).
- [Ref17] Kit, `svk-release/SoC_Flash/phoenix_flash.bin`, offsets 0x4e80a89 (64-bit value 2,800,000,000), 0x4e80a91 (64-bit value 2,000,000,000), 0x4e80428 (text PhoenixCfg1) and 0x4fbf12 (text INTPLL_MAIN). The names before INTPLL_MAIN are DBGSYSPLL, APSYSPLL, LCPPLL, DDRPLL0 to DDRPLL5 and 70 names from CPU_PLL0_MAIN to CPU_PLL34_FALLBK. The names after it are INTPLL_FALLBK, CCSM_MESH, MESH_THERMAL_MANAGEMENT and MESH_DVFS. The 8-byte value 2,000,000,000 occurs at 46 offsets of the image.
- [Ref18] Kit, `tools/arm-telemetrix/lib/config/scmi/public/phoenix/scp.json` lines 197 to 216 (component CMN, metric FREQUENCY_PRESENT, unit Hz, id 0x00000520) and the tool `svk-release/phx-soc-utils/scripts/power_management/stlm`.
- [Ref19] `crb/refs/arm-cmn-700-trm-102308-issue08.pdf`.
- [Ref20] Three public pages, downloaded on 2026-11-12 UTC and searched as text. https://amperecomputing.com/products/processors : "64MB System Level Cache" (AmpereOne and AmpereOne M), "16-32MB System Level Cache" (Ampere Altra) and "Ampere designed cores, mesh, and chiplet interconnect" (AmpereOne Aurora). https://github.com/aws/aws-graviton-getting-started , file README.md, table "Building for Graviton": row "Interconnect" with CMN-600, CMN-650, CMN-700 and CMN-S3 for Graviton2, Graviton3(E), Graviton4 and Graviton5 (line 60), and row "LLC (shared)" (line 73). https://developer.nvidia.com/blog/nvidia-grace-cpu-superchip-architecture-in-depth : "An NVIDIA Grace CPU Superchip has 234 MB of distributed L3 cache across the two chips." and "Designed by NVIDIA, Scalable Coherency Fabric (SCF) is a mesh fabric and distributed cache architecture". Copies of the three pages: `crb/tmp/agent-scratch/spec-row-2026-11-11/web-2026-11-12/`.
- [Ref21] `bench/bandwidth.c` lines 138 to 148 (`k_read`), 150 to 160 (`k_write` and `k_copy`), 173 to 195 (`k_asmread`) and 197 to 218 (`k_asmwrite`, with 8 `stp` instructions of two q registers at lines 204 to 211).
- [Ref22] `~/workspace/titan/exec/scratch-relocated/ed41c79f/bandwidth.c.orig`, dated 2026-10-30, lines 133 to 155 (`k_read`, `k_write` and `k_copy`, identical to lines 138 to 160 of the current source) and line 281 (placement of the threads). `crb/results/20261030T193108Z/sysinfo.txt` line 8 (gcc package).
- [Ref23] `~/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf`, AMBA CHI specification issue H, Figure B13.14 and Table B13.5, pages 469 to 470.
- [Ref24] Output of `crb/tmp/agent-scratch/spec-row-2026-11-11/port_counts.py`. It recomputes, from the raw rows of [Ref5], the bus accesses, bus writes, L2 refills and port data flits per line, the bus writes of CPU 2 per line that it wrote itself, the bus writes per mesh cycle, and the loop rates of the nine long runs of each case.
- [Ref25] `crb/results/followup-20261030T194205Z/log.txt` line 4 (compile command of the build at 19:42 UTC) and `pair.csv` lines 58 and 59 (read loop compiled from C, 1 MiB, 67.10 to 67.13 GB/s per thread). `bench/Makefile` line 9 (the same flags). `crb/results/20261030T193108Z/log.txt` (the first run: no compile command).
- [Ref26] Kit, Linux source archive `svk-release/linux/arm-agi-cpu-linux-7.1.3-v0.9.0-source.tar.gz`, file `tools/perf/pmu-events/arch/arm64/arm/neoverse-v3/bus.json` (descriptions of BUS_ACCESS, BUS_ACCESS_RD, BUS_ACCESS_WR and BUS_CYCLES). BUS_ACCESS: "Counts memory transactions issued by the CPU to the external bus, including snoop requests and snoop responses. Each beat of data is counted individually." BUS_CYCLES: "Since that interface is driven at the same clock speed as the CPU, this event is a duplicate of CPU_CYCLES." Also file `tools/perf/pmu-events/arch/arm64/mapfile.csv` line 39 (part 0xd83, the part number of CRB's cores, uses this folder). The archive is the source for firmware 0.9.0.
- [Ref27] `crb/results/dmidecode-t17-2026-10-30.txt`: 10 memory devices, each with Part Number MTC20F2085S1RC80BH1 NCKK and Speed 8000 MT/s.
- [Ref28] `crb/results/uncore2-20261030T203752Z/cmn-asmread-8M-1T.csv` lines 3 and 7 and `bw-asmread-8M-1T.csv` line 3 (loop rate 67.07 GB/s): one asm reader at 8 MiB on 2026-10-30. Each counter of this file ran for 49 or 50 % of the run (column 5 of each row), and perf scaled the counts to the whole run. The scaled counts of the two meshes sum to 850,985,083 accesses to the mesh cache. The loop read 1,047,920,640 lines. That is 0.81 accesses per line (est.). The file does not record the CPU. All 8 counter files of this folder have every counter at 49 or 50 %.
- [Ref29] `crb/results/sudo-20261102T054936Z/writebw.csv`, written by part 3 of `run_sudo.sh` (`bench/run_sudo.sh` lines 91 to 103). The script run started on 2026-11-02 at 05:49 UTC, and part 3 ran from 05:54 to 06:02 UTC (`log.txt` of the same folder, line 2 and lines 208 to 211). Case asmread-8M-1 is one asm reader at 8 MiB with the CPU list `0-119`, which puts the thread on CPU 0. Lines 511 and 520: the bytes read in the 0.2 s run and in the 2 s run, at 70.71 and 70.89 GB/s. Lines 515 and 524: the accesses to the mesh cache on mesh 0, both counters at 100.00 % of the run. The 2 s run minus the 0.2 s run gives 1,650,550,050 accesses for 1,994,522,624 lines, which is 0.83 per line.
- [Ref30] `~/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf`, AMBA CHI specification issue H. Page 32: "FLow control unIT (Flit) is the smallest flow control unit. A packet can be made up of one or more flits." and "For CHI, all packets consist of a single flit." The same page: "PHysical layer transfer unIT (Phit) is one transfer between two adjacent network devices." and "For CHI, all flits consist of a single phit." Page 455, section B13.3: "A flit is the basic unit of transfer in the Link layer." Page 518: "Each transfer of a flit from the Transmitter to the Receiver consumes one L-Credit."
- [Ref31] `crb/results/20261030T193108Z/bandwidth.csv`, the main sweep of 2026-10-30 with the loops compiled from C. The sweep used the CPU list 0-119 (`bench/run_crb.sh` lines 30 and 149, and line 9 of the `log.txt` of the run), so two threads are CPUs 0 and 1 and four threads are CPUs 0 to 3 [Ref33]. Lines 118, 124 and 130: one, two and four readers at 8 MiB, 66.99, 78.12 and 129.07 GB/s. Lines 154 and 160: one and two writers at 8 MiB, 44.76 and 75.57 GB/s. Lines 214 and 228: one and two readers at 1 GiB, 28.15 and 52.60 GB/s. Lines 218, 232 and 246: one, two and four writers at 1 GiB, 44.78, 63.19 and 113.25 GB/s.
- [Ref32] `crb/results/sudo-20261102T054936Z/writebw.csv` and `crb/results/sudo-20261102T040631Z/writebw.csv`, case asmread-8M-4 (four asm readers on CPUs 0 to 3, 8 MiB each). Lines 601 and 610: bytes of the 0.2 s run and of the 2 s run. Lines 605 and 614: accesses to the SLC on mesh 0 in the same two runs, both rows at 100 % in column 5. The difference of the counts divided by the difference of the lines gives 0.8217 and 0.8188 accesses per line. Lines 574, 592, 610, 628 and 646: the five 2 s runs of the case, 125.79 to 127.47 GB/s in the first file and 125.83 to 126.39 GB/s in the second.
- [Ref33] `bench/bandwidth.c` lines 4 to 6 (every thread owns its buffers and runs whole passes over them), 301 to 306 (a second buffer of the same size when a copy loop runs), 408 (thread i runs on entry i of the CPU list) and 416 to 418 (the column bytes_per_thread). `bench/run_crb.sh` lines 83 to 89: 8 MiB per thread for the SLC tests, 1 GiB per thread for the DRAM tests with 1 to 8 threads, 256 MiB per thread with 16 or more threads.
- [Ref34] `crb/results/followup-20261030T194205Z/pair.csv` lines 12, 18, 24, 36, 42 and 54 (two readers on cores of different pairs at 8 MiB: 126.59, 124.78, 132.02, 134.11, 134.02 and 132.37 GB/s) and lines 66 and 72 (two readers at 1 GiB with the loop compiled from C: 52.62 GB/s on CPUs 0 and 1, 54.91 GB/s on CPUs 0 and 64). `asm.csv` of the same folder, lines 81 (four asm readers at 8 MiB, 127.60 GB/s), 165 and 180 (one and two asm readers at 1 GiB, 30.47 and 56.66 GB/s), 300 and 307 (one asm reader and two asm readers on CPUs 0 and 2 at 8 MiB, 67.53 and 129.71 GB/s).
- [Ref35] The local headless browser `~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell` (Chrome for Testing 153.0.8010.12). It ran with every host name blocked and with the page font IBM Plex Sans from `crb/tmp/agent-scratch/spec-row-2026-11-11/fonts/`. A checker of the first run found this browser. The memory notes of the project had said that this machine has no browser.
- [Ref36] Rambus glossary entry "FLIT (Flow Control Unit)", https://www.rambus.com/?p=65936, a web search result of 2026-11-12. The page was not opened.
