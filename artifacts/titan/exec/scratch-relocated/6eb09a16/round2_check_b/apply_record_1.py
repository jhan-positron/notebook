#!/usr/bin/env python3
"""Record edits after the second internal check, part 1: Short version to section 6.
Every old text must occur exactly once."""
import sys
P = "/home/jhan/tmp/update-crb-memory-hierarchy.md"
s = open(P, encoding="utf-8").read()
n_edits = 0

def rep(old, new):
    global s, n_edits
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new); n_edits += 1

def block(start, end, new, keep_end=True):
    """Replace from the start marker up to (and, if keep_end is False, including) the end marker."""
    global s, n_edits
    assert s.count(start) == 1, (s.count(start), start[:60])
    i = s.index(start); j = s.index(end, i + len(start))
    assert s.count(end, i + len(start)) >= 1
    s = s[:i] + new + (s[j:] if keep_end else s[j + len(end):]); n_edits += 1

# ---------------------------------------------------------------- Short version
block("## Short version\n", "## Words used here\n", r'''## Short version

The first figure of the report now has two aligned rows of boxes, "Measured" and "Spec", and every text change in the request is made.
Three questions of the request led to corrections that go beyond the listed text, and the next section names them.
The term "mesh cache" is not an Arm term, and the report still uses it (see Q4).

## The three corrections

- The clock of the mesh (the on-chip interconnect) is 2.0 GHz. The measurement of 2026-11-02 already contained this value. The report said that the value was not known.
- The report said that the core has five pipelines for loads and stores. Arm's guide shows four that start loads and stores, and two more that carry store data.
- The machine code of the read loop compiled from C was read on CRB (the server that the report measures). The report had a hypothesis in two parts for the low rate of this loop. The first part is confirmed: the loop does one vector add per 16 B load. The second part is a limit of two vector adds per cycle. It does not fit the measured rate: it allows 89.6 GB/s, and the loop reaches 66.8 GB/s.

''')

# ---------------------------------------------------------------- Words used here
block("- **Report**: `crb-memory-hierarchy.html`", "## 1. Files\n", r'''- **Report**: `crb-memory-hierarchy.html`, the file that this update changes.
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

''')

# ---------------------------------------------------------------- section 2, side effects
rep("Its longest cell grew from 231 to 661 characters (line 118). The cells at lines 104 (603 characters) and 113 (568 characters) are also long.",
    "Its longest cell grew from 231 to 706 characters (line 118). The cells at lines 113 (642 characters) and 104 (603 characters) are also long.")

# ---------------------------------------------------------------- Q1
rep('''"The counters were read in one run of this test, at 40 threads. A separate series of runs of the same day used 8, 16, 24, 32 and 40 threads without counters.''',
    '''"The counters were read in that one run. It used 40 threads of 3 MiB each [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv]. A separate series of runs of the same day used 8, 16, 24, 32 and 40 threads without counters.''')
rep('''| C (shortest) | "The test stopped at 40 threads by its own rule, and the total was still increasing." |''',
    '''| C (shortest) | "A separate series of runs stopped at 40 threads by its own rule, and its total was still increasing." |''')
rep("- Two runs are involved. The totals are from one series of runs",
    "- One series of runs and one separate run are involved. The totals are from one series of runs")
rep("Mesh 1 had 3.47 × 10^9 of 9.72 × 10^9 accesses (36 %) with 8 of the 40 threads.",
    "Mesh 1 had 3.47 × 10^9 of 9.72 × 10^9 accesses (36 %, est.). Both counters ran for 49 % of that run, and perf scaled the counts to the whole run. The two files of this run hold no CPU list. Their name (`40T-even`) says 40 threads on even CPUs. If the run used the CPU list of the series (`0-118:2`), 8 of its 40 threads ran on mesh 1. The per-thread values of the run fit this. The slowest thread read 26.9 GB/s, the fastest 61.9 GB/s, and the average was 34.6 GB/s. 32 threads at the slowest value and 8 at the fastest would average 33.9 GB/s.")
rep("These sums differ from 450 GB/s, because they are from another run.",
    "These sums are not the 450 GB/s. They are from another run. They are also another quantity. The 450 GB/s is the difference of two totals. So it also includes any change in the rate of the 32 threads on mesh 0.")

# ---------------------------------------------------------------- Q2, firmware row
rep('''| The image holds the 64-bit value 2,000,000,000 at offset 0x4e80a91, directly after 2,800,000,000. The nearest text before it is "PhoenixCfg1" (offset 0x4e80428). A list of names in another part of the image holds INTPLL_MAIN (offset 0x4fbf12). The same list holds CCSM_MESH and MESH_DVFS | Read from the 0.9.0 image with `strings` and a hex dump. The two offsets are 73.5 MiB apart. The bytes alone do not link the value to the name. A research agent linked them by decoding machine code by hand. I did not repeat that step. That INTPLL_MAIN clocks the mesh is an inference from its name. This row is consistent with 2.0 GHz. It does not establish the value |''',
    '''| The image holds the 64-bit value 2,000,000,000 at offset 0x4e80a91, directly after the value 2,800,000,000. Read as Hz, the two values are 2.0 GHz and 2.8 GHz. The nearest text before them is "PhoenixCfg1" (offset 0x4e80428). Another part of the image holds a list of names. In this list the name INTPLL_MAIN (offset 0x4fbf12) follows 70 names from `CPU_PLL0_MAIN` to `CPU_PLL34_FALLBK`. Three later names of the list contain the word MESH: CCSM_MESH, MESH_THERMAL_MANAGEMENT and MESH_DVFS. The image gives no description next to these names | Read from the 0.9.0 image with `strings` and a hex dump. The value at 0x4e80a91 and the name at 0x4fbf12 are 73.5 MiB apart. The image holds this 8-byte value at 46 offsets. The bytes alone do not link the value to the name. A research agent linked them by decoding machine code by hand. I did not repeat that step. That INTPLL_MAIN is the PLL of the mesh is an inference. This row is consistent with 2.0 GHz. It does not establish the value |''')

# ---------------------------------------------------------------- Q4
rep('''The AWS page lists CMN as the interconnect of Graviton2 to Graviton5 (CMN-600 to CMN-S3; CMN S3 is also the model of CRB's mesh).''',
    '''The AWS page lists CMN as the interconnect of Graviton2 to Graviton5. It names the models CMN-600 to CMN S3 (the page writes "CMN-S3"). CMN S3 is also the model of CRB's mesh.''')
rep('''For a future product (AmpereOne Aurora) it names a mesh that Ampere designed.''',
    '''For one more product, AmpereOne Aurora, the page says "Ampere designed cores, mesh, and chiplet interconnect". The heading above that product is "Future of AI Compute".''')
rep("Size of the rename in the report after this update: 91 literal occurrences (86 before this update).",
    "Size of the rename in the report after this update: 92 literal occurrences (86 before this update).")
rep("About 26 more places use the bare word \"mesh\" for the cache level and need a manual check. Not done. I will do it when you confirm the term.",
    "About 26 more places use the bare word \"mesh\" for the cache level and need a manual check. Not done. The request asked only for an investigation of the term. I will do it when you confirm the term.")

# ---------------------------------------------------------------- Q7
rep('''- **Dispatch limits checked.** Arm's guide limits how many operations enter the pipelines in one cycle (section 4.1, "Dispatch constraints") [Ref2]. The section lists eight limits. Among them: at most 10 decoded instructions, at most 6 operations for the load pipelines, and at most 2 for each of the two vector pipelines. On average the loop runs 3.0 instructions, 1.5 loads of 16 B and 1.5 vector adds per cycle. The four other limits are for all operations together (20 per cycle) and for three groups of integer and branch pipelines (4, 4 and 2 per cycle). The loop is below them too on average (est.). One pass has about 20 operations, which is 3.7 per cycle. At most 4 of them are integer or branch operations, which is 0.75 per cycle.''',
    '''- **Dispatch limits checked.** Arm's guide limits how many operations the core dispatches in one cycle (section 4.1, "Dispatch constraints") [Ref2]. The section lists eight limits. Four of them, each per cycle: at most 10 decoded instructions, at most 6 operations for the load pipelines, and at most 2 for each of the two vector pipelines. On average the loop runs 3.0 instructions, 1.5 loads of 16 B and 1.5 vector adds per cycle. The four other limits are for all operations together (20 per cycle) and for three groups of integer and branch pipelines (4, 4 and 2 per cycle). The loop is below them too on average (est.). One pass has about 20 operations, which is 3.7 per cycle. The guide gives no count for the instruction LDP q, and the 20 counts one LDP q as two operations (est.). At most 4 of the 20 are integer or branch operations, which is at most 0.75 per cycle.''')
rep("holds the same `k_read`, `k_write` and `k_copy` [Ref22], and gcc on CRB was the same package on both days. The log of the follow-up run",
    "holds the same `k_read`, `k_write` and `k_copy` [Ref22]. The gcc package on CRB was the same on 2026-10-30 and on 2026-11-11 [Ref8][Ref22]. No saved file records it for the build day, 2026-11-02. The log of the follow-up run")
rep("Its stores are STP q instructions, not `st1d`.",
    "Its stores are STP q instructions, not `st1d` [Ref21]. One STP q stores two 16 B registers.")

# ---------------------------------------------------------------- D1
block("The proposal is the first of three separate statements. The report keeps them apart (lines 420 to 422):\n",
      "The alternative figure is rendered at", r'''The proposal is the first of three separate statements. The report keeps them apart (lines 420 to 422):

- **Hypothesis 1, capacity.** The pair port passes at most one data flit of 32 B per mesh cycle in each direction. That is 64 GB/s each way. Only this statement would go into the Spec box.
- **Hypothesis 2, saturation.** Four kinds of run fill this capacity, and the full port is what limits them. They are the runs of two partner cores that read 8 MiB each, of two partner cores that write 8 MiB each, of one core that writes 1 GiB, and of two partner cores that write 1 GiB each. The report calls them the tests of hypothesis 2. Hypothesis 1 can hold while a test leaves the port partly idle.
- **Conversion, two assumptions.** The measured rates count the bytes that the loops moved. The hypotheses are about the bytes that cross the port. The first assumption: one bus read or bus write of a core is one data flit of 32 B at the port. The second assumption: a count per line that was measured on one core alone also holds for two partner cores. The counts and most pair rates are also from different runs. Most counts are from CPU 2 with the asm loops in part 5 (2026-11-02). One share is from CPU 0 in part 3 of the same day [Ref29]. One more value of that share, the 0.81, is from a counter run of 2026-10-30 [Ref28]. Its file does not record the CPU. Most pair rates are from CPUs 0 to 5 on 2026-10-30, and three of them are from the read loop compiled from C.

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
| Two partner readers at 8 MiB | With 0.83, 64 GB/s on the port allows 77 GB/s. Measured 77.5 to 78.5 GB/s. Converted with 0.83, that is 64.1 to 64.9 GB/s on the port (est.), which is 1.00 to 1.01 flits per mesh cycle. With the scaled 0.81 the allowed rate is 79 GB/s, and the converted rates are 62.9 to 63.7 GB/s (est.) | Hypotheses 1 and 2 together, through the conversion (est.) | [Ref10] for the pair rates |
| Two partner writers at 8 MiB | 64 GB/s on the port allows 84 GB/s (1.52 bus writes per line, each taken as 32 B). Measured 82.34 GB/s on 2026-10-30 and 81.41 to 82.05 GB/s in the nine 2 s runs of part 5. In one pair of runs of part 5, CPU 2 sent 1.52 bus writes per line that it wrote itself, the same count as alone | Hypotheses 1 and 2 together, through the conversion (est.) | [Ref5][Ref10][Ref24] |
| Writers at 1 GiB | One writer 63.0 GB/s. Two partner writers together 63.2 GB/s. Four writers on two pairs 113 GB/s | Hypotheses 1 and 2 together, through the conversion (2.00 bus writes per line, measured on one writer alone). With both assumptions the two rates through one port are 0.98 and 0.99 of 64 GB/s (est.) | [Ref5][Ref10][Ref24] |

What is missing. The first three points follow the three statements (report lines 431 to 436). The last two points are at report lines 420 and 429:

- Capacity. The number of data channels at the port was not read. A run can reject hypothesis 1 only by a rate above 64 GB/s through one port in one direction. A low rate cannot reject it.
  - For writes one comparison exists. Two partner writers reach 63.2 GB/s together at 1 GiB, which is below 64 GB/s. At 1 GiB one writer alone sends 2.00 bus writes per line. If both assumptions of the conversion hold, the rate of the write loop is also the rate through the port (est.). No run counted the bus writes of two partner writers at 1 GiB. No counter of part 5 covers the data flits from the port to the crosspoint.
  - For reads, the converted rate of two partner readers at 8 MiB is 64.1 to 64.9 GB/s on the port with the share of 0.83 (est.). It is 62.9 to 63.7 GB/s with the scaled share of 0.81 (est.). No run counted the share for two partner cores. So the conversion cannot say whether the rate is below or above 64 GB/s.
  - A run with more bus reads than mesh cycles could not separate a wrong hypothesis 1 from a wrong first assumption. A read of the register field dat_vc_num_p can separate them. This field holds the number of data channels at the port (TRM page 1656) [Ref3]. The manual gives no numbering for the field. The report assumes the numbering of the design parameter on TRM page 1678.
- Saturation. No run counted the data flits at the port while two partner cores read. The report gives no threshold for "full". Only one value of this counter exists for a reader. This counter cannot be used for writes. It counts only the data flits that the crosspoint sends to the port, toward the core. Write data goes the other way. For writes, the bus writes of both partner cores must be counted.
- Conversion. The two factors (0.83 of the lines read cross the port, and 1.52 bus writes per line written) were measured on one core alone. No run counted the bus reads or the bus writes of both partner cores. One count exists for one core of a writing pair: CPU 2 sent 1.52 bus writes per line that it wrote itself.
- The limit of one flit per clock cycle on one channel follows from the signals of the CHI protocol [Ref23]. None of the Arm documents that were read states it in one sentence.
- The copy runs of two partner cores were not checked against the hypotheses. No bus count exists for a copy run. One more count is not explained: the four mesh links of CPU 2's crosspoint carried 1.09 times as many data flits as the core made bus writes (report line 429).

The measured ~80 GB/s in the box above (77.5 to 78.5 GB/s) is higher than 64 GB/s. The 80 GB/s counts every byte that the two cores read. One core alone takes 17 % of its lines from its own L2. If two partner cores do the same, 64.1 to 64.9 GB/s cross the port (est.). That is at or just above 64 GB/s. No run counted this share for two partner cores. A share of 0.81 would put all four pair rates below 64 GB/s (est.). So the estimate does not decide whether the measured rate conflicts with 64 GB/s on the port.

''')

# ---------------------------------------------------------------- D2
rep('''The evidence there is a read test. For writes at 1 GiB, two partner cores write 63.2 GB/s together, the same as one core (63.0 GB/s) [Ref10]. So both statements are wrong for write streams, whether hypotheses 1 and 2 hold or not.''',
    '''The evidence there is a read test. For writes at 1 GiB, two partner cores write 63.2 GB/s together, one core alone writes 63.0 GB/s, and four writers on two pairs write 113 GB/s [Ref10]. So two partner writers share one limit at 1 GiB. This follows from the measured rates, and it holds whether hypotheses 1 and 2 hold or not. The read test behind both statements does not cover write streams. That the full port is the shared limit is part of hypothesis 2.''')
rep('''At 1 GiB one writer sends 0.98 bus writes of 32 B per mesh cycle [Ref5]. If hypothesis 1 of D1 holds and one bus write is one flit at the port, that is 98 % of the capacity of the port (est.).''',
    '''At 1 GiB one writer sends 0.98 bus writes per mesh cycle [Ref5]. If hypothesis 1 of D1 and the first assumption of the conversion hold, that is 98 % of the capacity of the port (est.).''')

# ---------------------------------------------------------------- D9
rep("With 12 channels at 8000 MT/s the DRAM box would read 768 GB/s. The report says this at lines 120 and 467.",
    "With 12 channels at 8000 MT/s the DRAM box would read 768 GB/s. The report gives the 768 GB/s at line 120. It gives the 3.2 GHz and the 7200 MT/s at line 467. It does not give the 153.6 GB/s and the 102.4 GB/s.")

# ---------------------------------------------------------------- section 5
rep("the explanation of Q1 (wording B). It keeps the counter run and the series of runs apart | Q1 | 113 |",
    "the explanation of Q1 (wording B). It keeps the counter run and the series of runs apart, and it cites the file of each | Q1 | 113 |")
rep("The pair-port row names hypothesis 1 and gives the estimate of 63 to 65 GB/s on the port",
    "The pair-port row names hypothesis 1 and gives the estimate of 64 to 65 GB/s on the port")
rep("| C11 | Compiled-loop paragraphs with the disassembly result, the limits of Arm's guide that were checked, and two hypotheses with their test.",
    "| C11 | Compiled-loop paragraphs with the disassembly result, the limits of Arm's guide that were checked, and two hypotheses with their test. Line 132 holds three paragraphs on one source line.")
rep("It keeps two hypotheses (capacity, saturation) and one assumption (conversion) apart, and it names one missing test for each",
    "It keeps two hypotheses (capacity, saturation) and the conversion with its two assumptions apart, and it names the missing test for each. Four of its items hold a nested list on one source line (lines 422, 425, 433 and 434)")

# ---------------------------------------------------------------- section 6
rep('''Line 302: "In a separate series of runs without counters the total was still rising at 40 threads (899 GB/s at 32 threads, 1,349 GB/s at 40). The last 8 of the 40 threads were the first threads on chiplet 1. The series stopped at 40 threads by its own rule (all buffers together stay below 128 MiB). So 0.62 TB/s is a lower bound." Line 343: "... and the total of the series was still rising at 40 ...". Label: "total still rising: the test stops at 40 threads" |''',
    '''Line 302: "In a separate series of runs without counters the total was still rising at 40 threads (899 GB/s at 32 threads, 1,349 GB/s at 40). The last 8 of the 40 threads were the first threads on chiplet 1. The series stopped at 40 threads by its own rule: all buffers together stay below 128 MiB, and the next step of 48 threads would be 144 MiB. The 0.62 TB/s is what the mesh cache delivered in one run, so the cache can deliver at least that." Line 343, in place of the last sentence: "So 40 is the largest count tested that fits. The 0.62 TB/s is what the mesh cache delivered in this one run, so the cache can deliver at least that. A separate series of runs with 8 to 40 threads measured only the total, and the total was still rising at 40 threads." Label: "total still rising: the test stops at 40 threads" |''')
rep('''| F4 | Line 214 | "about 28 B per core cycle (est. from 78 GB/s at 2.8 GHz)". The port runs on the mesh clock |''',
    '''| F4 | Line 214 | "about 28 B per core cycle (est. from 78 GB/s at 2.8 GHz)". The crosspoint is part of the mesh, and hypothesis 1 of D1 counts its port in mesh cycles (2.0 GHz). Arm's event list says that the core's own bus interface runs at the core clock [Ref26]. The 78 GB/s also counts the L2 hits |''')
rep("What sets it was not tested (see Q7). The read loops give 67.0 and 66.9 GB/s at 8 MiB, and 28.2 and 30.5 GB/s at 1 GiB. Equal rates",
    "What sets it was not tested (see Q7). The read loop compiled from C and the asm read loop give 67.0 and 66.9 GB/s at 8 MiB. They give 28.2 and 30.5 GB/s at 1 GiB. Equal rates")
rep("From DRAM they differ by 8 % (28.2 and 30.5 GB/s). The write loops do not agree.",
    "From DRAM they differ by 8 % (28.2 GB/s compiled from C, 30.5 GB/s asm). The write loops do not agree.")
rep('''The new text says 17 to 19 % for one core alone (lines 118 and 425). No run counted this share with only two partner cores busy | Line 110: "two partner cores together read 78 GB/s at the mesh-cache footprint" (the rest of that sentence stays). After the sentence that ends with "78 rounded." add: "The 78 GB/s counts every byte that the loops read. One core alone takes 17 to 19 % of its lines from its own L2. No run counted this share with only two partner cores busy." |''',
    '''The new text says 17 % for one core alone, from three counters that ran for the whole run (lines 118 and 425). The 19 % of line 266 is from a scaled count (see F21). No run counted this share with only two partner cores busy | Line 110: "two partner cores together read 78 GB/s at the mesh-cache footprint" (the rest of that sentence stays). After the sentence that ends with "78 rounded." add: "The 78 GB/s counts every byte that the loops read. One core alone takes 17 % of its lines from its own L2. No run counted this share with only two partner cores busy." |''')
rep('''Name the three PDFs at line 215 |
''', '''Name the three PDFs at line 215 |
| F21 | Lines 52, 86, 97, 113, 266, 302, 320, 330, 336, 343, 396, 959 and 969 | These lines give values from the counter files of `crb/results/uncore2-20261030T203752Z/`: 0.62 TB/s and 0.45 accesses per line (40 threads), 2.9 % misses, 81 % and 19 % (one reader at 8 MiB), and the 54 GB/s of line 266. In all 8 counter files of that folder every counter ran for 49 or 50 % of the run, and perf scaled the counts to the whole run [Ref11][Ref28]. The report gives the values with no "est.". For one reader at 8 MiB a count over the whole run exists. It gives 0.83, and the report has it at lines 232 and 268 [Ref29]. No count over the whole run exists for the 40-thread test | Mark the values of these lines "est." and add at line 113: "Each counter ran for about half of this run, and perf (the Linux counter tool) scaled the counts to the whole run." At lines 266, 330 and 959 use the 83 % and 17 % of the root run of 2026-11-02. A new counter run of the 40-thread test with fewer events at a time would give counts over the whole run. Not run |
''')

open(P, "w", encoding="utf-8").write(s) if "--write" in sys.argv else None
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits")
