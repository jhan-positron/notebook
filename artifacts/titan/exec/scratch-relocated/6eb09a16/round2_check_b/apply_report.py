#!/usr/bin/env python3
"""Apply the corrections of the second internal check to the report.
Every sub-line edit must match exactly once. Every whole-line edit names its line and a prefix.
No line is added or removed, so the line numbers that the record cites stay valid."""
import sys
P = "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
src = open(P, encoding="utf-8").read()
L = src.split("\n")
assert len(L) == 979 and L[-1] == "", len(L)   # 978 lines plus the final newline

def sub(n, old, new):
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:60])
    assert src.count(old) == 1, (n, "not unique in file", src.count(old), old[:60])
    L[n - 1] = line.replace(old, new)

def whole(n, prefix, new):
    assert L[n - 1].startswith(prefix), (n, L[n - 1][:80])
    assert "\n" not in new
    L[n - 1] = new

# ---- line 113: name the counter run and cite its file
sub(113, "The counters were read in one run of this test, at 40 threads. A separate series",
    "The counters were read in that one run. It used 40 threads of 3 MiB each [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv]. A separate series")

# ---- line 118: the share of one core alone is 0.83 by three full-run counters
sub(118, "The measured ~80 GB/s (77.5 to 78.5 GB/s) counts every byte that the two partner cores read. One core alone takes 17 to 19 % of its lines from its own L2. If two partner cores do the same, 63 to 65 GB/s cross the port (est.). This estimate is not exact enough to say whether the rate on the port is below or above 64 GB/s.",
    "The measured ~80 GB/s (77.5 to 78.5 GB/s, two read loops) counts every byte that the two partner cores read. One core alone takes 17 % of its lines from its own L2. If two partner cores do the same, 64 to 65 GB/s cross the port (est.). No run counted this share for two partner cores. So the estimate cannot say whether the rate on the port is below or above 64 GB/s.")

# ---- line 131: the two days for which the compiler version is recorded
sub(131, "The compiler on CRB was the same package on both days. So the three loops",
    "The compiler package on CRB was the same on 2026-10-30 and on 2026-11-11 [results/20261030T193108Z/sysinfo.txt; results/probe-20261111T210017Z.txt]. The build of 2026-11-02 lies between these two days. So the three loops")

# ---- line 132: dispatch is not entry into a pipeline; three paragraphs on one source line
sub(132, " The measured 66.8 GB/s is 25 % below that. Arm's guide also limits how many operations enter the pipelines in one cycle [SOG, section 4.1 \"Dispatch constraints\", page 55]. This report calls them dispatch limits. The section lists eight of them. At most 10 instructions enter per cycle (the guide counts them after decoding and calls them MOPs). At most 6 operations per cycle go to the load pipelines (the guide calls operations µOPs, and one LDP q is taken as two of them). At most 2 operations per cycle go to each of the two vector pipelines. On average",
    " The measured 66.8 GB/s is 25 % below that.</p><p>Arm's guide also limits how many operations the core dispatches in one cycle [SOG, section 4.1 \"Dispatch constraints\", page 55]. Dispatch is the step before the pipelines. A dispatched operation waits for its inputs and then goes to a pipeline [SOG, section 2.1 page 11]. So a dispatch limit can be higher than the number of operations that the pipelines accept in one cycle. This report calls these limits dispatch limits. The section lists eight of them. The dispatch step handles at most 10 instructions per cycle. The guide counts instructions after decoding and calls them MOPs (macro-operations). At most 6 operations per cycle are dispatched for the load pipelines. The guide calls operations µOPs (micro-operations). It gives no count for LDP q. This report counts one LDP q as two operations, one for each 16 B load (est.). At most 2 operations per cycle are dispatched for FP/ASIMD 0, and at most 2 for FP/ASIMD 1. On average")
sub(132, "One pass has about 20 operations: 8 loads, 8 vector adds, 2 integer adds, one compare and one branch. That is 3.7 operations per cycle, and at most 0.75 of them are integer or branch operations. So the loop stays below",
    "One pass of the loop (128 B) has about 20 operations: 8 loads, 8 vector adds, 2 integer adds, one compare and one branch. One pass takes 5.37 cycles at 32 KiB (see \"Observation\" below). That is 3.7 operations per cycle. At most 0.75 of them are integer or branch operations.</p><p>So the loop stays below")

# ---- line 420: one long sentence becomes five
sub(420, "The limit of one flit per clock cycle follows from the signals of Arm's CHI link protocol (CHI = Coherent Hub Interface, the protocol of the mesh ports and links): one channel has one flit bus (the wires for one flit) and one valid signal (it marks a cycle that carries a flit) [AMBA CHI specification, IHI 0050 issue H, Figure B13.14 and Table B13.5, pages 469 to 470].",
    "The limit of one flit per clock cycle follows from the signals of Arm's CHI link protocol. CHI is the Coherent Hub Interface, the protocol of the mesh ports and links. One channel has one flit bus and one valid signal [AMBA CHI specification, IHI 0050 issue H, Figure B13.14 and Table B13.5, pages 469 to 470]. The flit bus is the set of wires for one flit. The valid signal marks a cycle that carries a flit.")

# ---- line 421: name the tests of hypothesis 2 one by one
sub(421, "The pair tests fill this capacity, and the full port is what limits them. These tests are the runs of two partner cores that read or write 8 MiB each, and the runs of one or two cores of a pair that write 1 GiB each. Hypothesis 2 is a separate statement.",
    "Four kinds of run fill this capacity, and the full port is what limits them. They are the runs of two partner cores that read 8 MiB each, of two partner cores that write 8 MiB each, of one core that writes 1 GiB, and of two partner cores that write 1 GiB each. This report calls them the tests of hypothesis 2. Hypothesis 2 is a separate statement.")

# ---- line 422: "first assumption" and "second assumption"; sub-items; six runs behind three counts
whole(422, "<li><b>Assumption, conversion.</b>",
    "<li><b>Conversion, two assumptions.</b> The measured rates count the bytes that the loops read or wrote. Both hypotheses are about the bytes that cross the port. The conversion between the two makes two assumptions.<ul>"
    "<li>The first assumption: one bus read or bus write of a core is one data flit of 32 B at the port (see \"bus access\" in \"Words used here\").</li>"
    "<li>The second assumption: a count per line that was measured on one core alone also holds for two partner cores.</li>"
    "<li>Most counts are from part 5 (2026-11-02). Most of the pair rates are from runs of 2026-10-30. Each item below names its sources.</li>"
    "<li>For one core alone the counts of part 5 fit the first assumption. One writer at 1 GiB sends 2.00 bus writes per 64 B line [writepath.csv, case w1G-c2]. A case name gives the loop (r for asm read, w for asm write), the buffer size and the CPUs. One reader at 8 MiB makes 3.306 bus accesses per line, and 1.653 of them are bus writes. Part 5 did not count the bus reads, so the other 1.653 bus accesses per line are taken as bus reads (est.). The port of that reader carries 1.653 data flits per line toward the core. Each of these three counts is from its own pair of runs of case r8M-c2 (the 2 s run minus the 0.2 s run).</li>"
    "</ul></li>")

# ---- line 423: the range, its two ends, the run that is not a test, and no margin
sub(423, "The rows below compare measured rates with the rate that 64 GB/s on the port allows. In the first three rows the measured rates are 0.97 to 1.02 of the allowed rates (est.). A row that fits supports hypotheses 1 and 2 together. It does not support hypothesis 1 alone. The rows that use a count per line also depend on the conversion. A measured rate clearly above the allowed rate would mean that hypothesis 1 or the conversion is wrong. A measured rate clearly below it would mean that hypothesis 2 or the conversion is wrong. It would not test hypothesis 1.",
    "The items below compare measured rates with the rate that 64 GB/s on the port allows. In the first three items the measured rates of the tests of hypothesis 2 are 0.97 to 1.01 of the allowed rates (est.). The lowest value is the slowest of the nine 2 s runs of the writes at 8 MiB. The highest is the fastest run of the reads at 8 MiB. The third item also holds one run with two busy pairs, at 0.88 of the allowed rate. It is not a test of hypothesis 2. An item that fits supports hypotheses 1 and 2 together. It does not support hypothesis 1 alone. The items that use a count per line also depend on the conversion. A measured rate clearly above the allowed rate would mean that hypothesis 1 or the conversion is wrong. A measured rate clearly below it would mean that hypothesis 2 or the conversion is wrong. It would not test hypothesis 1. No margin is set for \"clearly\". The variation of the counts per line from run to run was not measured.")

# ---- line 425: three full-run counters give 0.83; the 0.81 is a scaled count
whole(425, "<li>Reads at 8 MiB. One reader gets 1.653 data flits per line",
    "<li>Reads at 8 MiB.<ul>"
    "<li>One reader gets 1.653 data flits per line from its port, not 2. So 0.83 of its lines cross the port, and the rest are L2 hits [writepath.csv, case r8M-c2]. Two more counters of 2026-11-02 give the same share. The first is 0.83 L2 refills per line (lines that the L2 loads from outside the core) [same case]. The second is 0.83 accesses to the mesh cache per line, counted at the home nodes [results/sudo-20261102T054936Z/writebw.csv, case asmread-8M-1]. A run of 2026-10-30 gave 0.81 for the second counter (est.). Each counter of that run ran for about half of the run, and perf (the Linux counter tool) scaled the counts to the whole run [results/uncore2-20261030T203752Z/cmn-asmread-8M-1T.csv].</li>"
    "<li>With the share of 0.83, 64 GB/s on the port allows 77 GB/s for two partner cores. Measured: 77.5 GB/s with the asm loop [results/followup-20261030T194205Z/asm.csv] and 77.9 to 78.5 GB/s with the read loop compiled from C [pair.csv in the same folder]. All four shares were counted with the asm loop, on one core alone.</li>"
    "<li>Converted with the share of 0.83, the measured rates are 64.1 to 64.9 GB/s on the port (est.). That is 1.00 to 1.01 flits per mesh cycle. With the scaled share of 0.81 they are 62.9 to 63.7 GB/s (est.). No run counted the share for two partner cores. So the conversion cannot say whether the rate on the port is below or above 64 GB/s.</li>"
    "</ul></li>")

# ---- line 426: the size of a bus write is assumed; both measured values; one pair of runs
sub(426, "One writer sends 1.52 bus writes of 32 B per line, not 2, for a reason that is not known [writepath.csv, case w8M-c2]. With that count, 64 GB/s on the port allows 84 GB/s for two partner cores. Measured: 82 GB/s [asm.csv; writepath.csv, case w8M-c2c3]. In the run of part 5 (case w8M-c2c3) CPU 2 sent 0.50 bus writes per mesh cycle while its partner also wrote. With the first part of the conversion, that is half of the capacity of hypothesis 1 (est.). In that run CPU 2 sent 1.52 bus writes per line that it wrote itself, the same as alone.",
    "One writer sends 1.52 bus writes per line, not 2, for a reason that is not known [writepath.csv, case w8M-c2]. With that count and both assumptions of the conversion, 64 GB/s on the port allows 84 GB/s for two partner cores (est.). Measured: 82.3 GB/s on 2026-10-30 [asm.csv], and 81.4 to 82.1 GB/s in the nine 2 s runs of part 5 [writepath.csv, case w8M-c2c3]. In one pair of runs of that case CPU 2 sent 0.50 bus writes per mesh cycle while its partner also wrote. With the first assumption of the conversion, that is half of the capacity of hypothesis 1 (est.). In the same runs CPU 2 sent 1.52 bus writes per line that it wrote itself, the same count as alone.")

# ---- line 427: the step from bus writes to flits is the first assumption
sub(427, "One writer sends 2.00 bus writes of 32 B per line, so every line crosses the port as 2 flits [writepath.csv, case w1G-c2]. One writer reaches 63.0 GB/s, and two partner writers together reach 63.2 GB/s. That is 0.98 and 0.99 of 64 GB/s. Four writers on two pairs reach 113 GB/s [asm.csv]. That is 56.6 GB/s per pair, which is 0.88 of 64 GB/s. This run has two busy pairs, so it is not one of the pair tests of hypothesis 2.",
    "One writer sends 2.00 bus writes per line [writepath.csv, case w1G-c2]. With the first assumption of the conversion, every line crosses the port as 2 flits of 32 B (est.). One writer reaches 63.0 GB/s, and two partner writers together reach 63.2 GB/s [asm.csv]. That is 0.98 and 0.99 of 64 GB/s (est.). The value for two partner writers also uses the second assumption. Four writers on two pairs reach 113 GB/s [asm.csv]. That is 56.6 GB/s per pair, which is 0.88 of 64 GB/s. This run has two busy pairs. It is not a test of hypothesis 2.")

# ---- line 428: source for "one data channel"; mesh cycle
sub(428, "This row shows how full the port was with one reader. It cannot test hypothesis 1. The counter covers one data channel, so it cannot count more than one flit per cycle.",
    "This item shows how full the data channel toward the core was with one reader. It cannot test hypothesis 1. The counter covers one data channel [CMN S3 TRM, pages 1678 to 1679]. So it cannot count more than one flit per mesh cycle.")

# ---- line 431: first results exist for writes
sub(431, "Each of the three statements needs its own test. None was run.",
    "Hypothesis 1, hypothesis 2 and the conversion each need their own test. None of these tests was run in full. Existing runs give first results for writes. The items below name them.")

# ---- line 433: capacity, in six sub-items
whole(433, "<li>Capacity. Read the number of data channels at the port",
    "<li>Capacity.<ul>"
    "<li>Read the number of data channels at the port (field dat_vc_num_p above). The manual gives no numbering for this field [CMN S3 TRM, page 1656]. For the design parameter POR_DAT_VC_NUM_PARAM, 1 means one data channel, and a value above 1 means two sub-channels [CMN S3 TRM, page 1678]. This report assumes the same numbering for the field. Then a value of 1 supports hypothesis 1, and a value of 2 or more rejects it.</li>"
    "<li>A run can reject hypothesis 1 only by a rate above 64 GB/s through one pair port in one direction. A lower rate cannot reject it. A test can leave the port partly idle.</li>"
    "<li>For writes an existing run can be compared with 64 GB/s. Two partner cores that write 1 GiB each reach 63.2 GB/s together [asm.csv]. That is below 64 GB/s. The comparison uses both assumptions of the conversion. One writer alone sends 2.00 bus writes per 64 B line at 1 GiB [writepath.csv, case w1G-c2]. No run counted the bus writes of two partner writers at 1 GiB. No counter of part 5 covers the data flits that go from the port to the crosspoint. If both assumptions hold, 63.2 GB/s is also the rate through the port (est.). Then this run does not reject hypothesis 1.</li>"
    "<li>For reads the run is missing. Let two partner cores read 8 MiB each. Count the bus reads of both cores (Arm event BUS_ACCESS_RD) and the mesh cycles (perf event dtc_cycles) in the same run. If both cores together make more bus reads than the mesh has cycles, the port carried more than one flit per mesh cycle.</li>"
    "<li>This step uses the first assumption of the conversion. So such a result rejects hypothesis 1 or the first assumption, and the run alone does not show which. The flit counter of the port cannot show which of the two is wrong. It covers one data channel. So it cannot count more than one flit per mesh cycle. A read of the register field can show it.</li>"
    "<li>The expected count is close to one bus read per mesh cycle. With the share of 0.83, the existing rates give 2.00 to 2.03 × 10<sup>9</sup> bus reads per second for two partner readers (est.). With the scaled share of 0.81 they give 1.97 to 1.99 × 10<sup>9</sup> (est.). The mesh has 2.00 × 10<sup>9</sup> cycles per second. No margin is set here. Repeated runs must give the variation of the count first.</li>"
    "</ul></li>")

# ---- line 434: saturation, in three sub-items
whole(434, "<li>Saturation. Let two partner cores read 8 MiB each.",
    "<li>Saturation.<ul>"
    "<li>Let two partner cores read 8 MiB each. Count the data flits that the crosspoint sends to the port (perf event mxp_p1_dat_txflit_valid) and the mesh cycles. A rate near 1.0 flit per mesh cycle supports hypothesis 2. A rate clearly below 1.0 means that this data channel had idle cycles. Then the full data channel did not limit the pair. That result rejects hypothesis 2 for reads and leaves hypothesis 1 open.</li>"
    "<li>No threshold is set here. Only one value of this counter exists for a reader. It is 0.92 flits per mesh cycle for one reader alone (case r8M-c2, the count of the 2 s run minus the count of the 0.2 s run). So its variation from run to run is not known. Repeated counts must give that variation before a threshold is set.</li>"
    "<li>This counter covers reads only. It counts the flits that the crosspoint sends to the port, and write data goes the other way. For writes, count the bus writes of both partner cores and the mesh cycles. A total near 1.0 bus write per mesh cycle supports hypothesis 2 for writes, through the first assumption of the conversion. Part 5 holds two such counts, each of one core only: 0.98 bus writes per mesh cycle for one writer alone at 1 GiB, and 0.50 for CPU 2 at 8 MiB while its partner also wrote.</li>"
    "</ul></li>")

# ---- line 435: one run for both counts; "items", not "rows"
whole(435, "<li>Conversion. In the read run above, compare the bus reads",
    "<li>Conversion. Let the read test above count the bus reads of both cores and the data flits at the port in one run. As many bus reads as flits supports the first assumption. For the second assumption, compare the flits per line of the pair with the 1.653 of one core. Suppose that one of these two comparisons fails, and the bus reads stay at or below the mesh cycles. Then the converted numbers in the items above are wrong. That result does not test hypothesis 1. More bus reads than mesh cycles is the case of the capacity item above. For writes, compare the bus writes per line of both partner cores with the 1.52 (8 MiB) and the 2.00 (1 GiB) of one core. Part 5 gives a first value for one of the two cores: the 1.52 of CPU 2 in the item \"Writes at 8 MiB\".</li>")

# ---- line 437: what the rates show (a shared limit) against what is hypothesis 2 (the port)
whole(437, "<li><b>Older statements that need a correction.</b>",
    "<li><b>Older statements that need a correction.</b> \"For DRAM streams the port is not the limit\" (section \"Is the pair port how the mesh cache is reached?\") and \"For DRAM traffic the port is not the limit\" (section \"The pair finding\") rest on a read test. The measured rates above do not support them for write streams. Two partner cores together wrote 63.2 GB/s at 1 GiB. One core alone wrote 63.0 GB/s. So the second core added 0.2 GB/s (0.3 %). Four writers on two pairs wrote 113 GB/s. So two partner writers share one limit at 1 GiB. This follows from the measured rates, and it does not depend on the hypotheses. The rates do not show what the shared limit is. That the full port is this limit is part of hypothesis 2. \"The single-writer limit is inside the core\" (section \"Where one writer's 73 GB/s limit sits\") was written for 8 MiB writes. For 1 GiB writes it is in doubt. One writer sends 0.98 bus writes per mesh cycle there [writepath.csv, case w1G-c2]. If hypothesis 1 and the first assumption of the conversion hold, that is 98 % of the capacity of the port (est.). If hypothesis 2 also holds for this case, the port limits one writer at 1 GiB, and the core does not. These sections are unchanged for now.</li>")

# ---- line 452: what Arm's list says, what this report assumes, and the snoop part
whole(452, "<dt>bus access, bus read, bus write</dt>",
    "<dt>bus access, bus read, bus write</dt><dd>One data transfer between a core and the mesh, as the core's own counters count it (Arm events BUS_ACCESS and BUS_ACCESS_WR). A bus write goes from the core to the mesh, and a bus read goes to the core. Arm's event list for this core says that each beat of data is counted individually [Linux source in Arm's kit, tools/perf/pmu-events/arch/arm64/arm/neoverse-v3/bus.json]. The table mapfile.csv of the same source assigns part 0xd83 to this folder. A beat is one transfer on the bus. This report takes one transfer as 32 B. That belongs to the first assumption of the conversion in \"Open items\". One count of part 5 fits it: one writer sent 2.00 bus writes per 64 B line at 1 GiB. Part 5 counted all bus accesses and the bus writes. It did not count the bus reads. This report takes them as all bus accesses minus bus writes (est.). Arm's list also says that the count of all bus accesses includes snoop requests and snoop responses. A snoop is a request from the mesh to a core about a line that the core may hold. So the difference can hold more than bus reads. The port counts of case r8M-c2 (the 2 s run minus the 0.2 s run) hold 4,182 snoop flits and 3.3 × 10<sup>9</sup> data flits from the crosspoint to the port in 1.8 s. So snoops were a small part of the traffic at that port.</dd>")

out = "\n".join(L)
assert out.count("\n") == src.count("\n")
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write(out)
    print("written")
else:
    print("dry run ok")
