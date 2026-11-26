#!/usr/bin/env python3
"""Apply the corrections of the third internal check to the report.
Every sub-line edit must match exactly once. No line is added or removed."""
import sys
P = "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
src = open(P, encoding="utf-8").read()
L = src.split("\n")
assert len(L) == 979 and L[-1] == "", len(L)

def sub(n, old, new):
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:60])
    L[n - 1] = line.replace(old, new)

def whole(n, prefix, new):
    assert L[n - 1].startswith(prefix), (n, L[n - 1][:80])
    assert "\n" not in new
    L[n - 1] = new

def append(n, suffix_old, new_tail):
    assert L[n - 1].endswith(suffix_old), (n, L[n - 1][-80:])
    L[n - 1] = L[n - 1] + new_tail

# ---- line 113: each fact gets the file that holds it
sub(113, "The counters were read in that one run. It used 40 threads of 3 MiB each [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv].",
    "The counters were read in that one run [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv]. It used 40 threads of 3 MiB each [bw-asmread-3M-40T-even.csv in the same folder].")

# ---- line 132: five paragraphs; 0.75 gets its unit
sub(132, "This report calls these limits dispatch limits. The section lists eight of them. The dispatch step handles",
    "This report calls these limits dispatch limits. The section lists eight of them.</p><p>The dispatch step handles")
sub(132, "1.5 loads of 16 B and 1.5 vector adds per cycle. The four other limits",
    "1.5 loads of 16 B and 1.5 vector adds per cycle.</p><p>The four other limits")
sub(132, "That is 3.7 operations per cycle. At most 0.75 of them are integer or branch operations.",
    "That is 3.7 operations per cycle. At most 4 of the 20 operations are integer or branch operations. That is at most 0.75 operations per cycle.")

# ---- line 421: "runs of hypothesis 2", so that "test" keeps one meaning
sub(421, "This report calls them the tests of hypothesis 2. Hypothesis 2 is a separate statement. Hypothesis 1 can hold while a test leaves the port partly idle.",
    "This report calls them the runs of hypothesis 2. Hypothesis 2 is a separate statement. Hypothesis 1 can hold while a run leaves the port partly idle.")

# ---- line 422: say what is converted
sub(422, "The conversion between the two makes two assumptions.",
    "The conversion between the bytes of the loops and the bytes that cross the port makes two assumptions.")

# ---- line 423: short introduction; the reading rules move to a last item on line 429
whole(423, "<li><b>What fits.</b>",
    "<li><b>What fits.</b> The items below compare measured rates with the rate that 64 GB/s on the port allows. In the first three items the measured rates of the runs of hypothesis 2 are 0.97 to 1.01 of the allowed rates (est.). The lowest value is the slowest of the nine 2 s runs of the writes at 8 MiB. The highest is the fastest run of the reads at 8 MiB. The third item also holds one run with two busy pairs, at 0.88 of the allowed rate (est.). It is not one of the runs of hypothesis 2. The last item says how to read a fit.")
append(429, "Other senders that use these links were not counted.</li>",
    "<li>How to read these items. An item that fits supports hypotheses 1 and 2 together. It does not support hypothesis 1 alone. The items that use a count per line also depend on the conversion. A measured rate clearly above the allowed rate would mean that hypothesis 1 or the conversion is wrong. A measured rate clearly below it would mean that hypothesis 2 or the conversion is wrong. It would not test hypothesis 1. No margin is set for \"clearly\". The variation of the counts per line from run to run was not measured.</li>")

# ---- line 425: the loop rate of each run behind a share; the four pair rates; est.
whole(425, "<li>Reads at 8 MiB.<ul>",
    "<li>Reads at 8 MiB.<ul>"
    "<li>One reader gets 1.653 data flits per line from its port, not 2. So 0.83 of its lines cross the port, and the rest are L2 hits [writepath.csv, case r8M-c2]. Two more counters of 2026-11-02 give the same share. The first is 0.83 L2 refills per line (lines that the L2 loads from outside the core) [same case]. The second is 0.83 accesses to the mesh cache per line, counted at the home nodes [results/sudo-20261102T054936Z/writebw.csv, case asmread-8M-1]. A run of 2026-10-30 gave 0.81 for the second counter (est.). Each counter of that run ran for about half of the run, and perf (the Linux counter tool) scaled the counts to the whole run [results/uncore2-20261030T203752Z/cmn-asmread-8M-1T.csv]. The loop read 67.1 GB/s in that run [bw-asmread-8M-1T.csv in the same folder]. In the runs of the three counts of 0.83 it read 70.7 to 71.0 GB/s. So the scaled count is not the only difference between the 0.81 and the 0.83. The cause of the lower share is not known.</li>"
    "<li>With the share of 0.83 and the second assumption of the conversion, 64 GB/s on the port allows 77 GB/s for two partner cores (est.). Measured: 77.5 GB/s with the asm loop [results/followup-20261030T194205Z/asm.csv] and 77.9, 78.3 and 78.5 GB/s with the read loop compiled from C on three pairs of partner cores [pair.csv in the same folder]. One reader alone read 66.9 GB/s in the same asm.csv. That is close to the 67.1 GB/s of the run that gave 0.81. All four shares were counted with the asm loop and with one busy core. The core was CPU 2 for the two counters of part 5 and CPU 0 for the count in writebw.csv. The file of 2026-10-30 does not record the CPU.</li>"
    "<li>Converted with the share of 0.83, the measured rates are 64.1 to 64.9 GB/s on the port (est.). That is 1.00 to 1.01 flits per mesh cycle, at or just above the 64 GB/s of hypothesis 1. With the scaled share of 0.81 they are 62.9 to 63.7 GB/s (est.). No run counted the share for two partner cores. A share of 0.81 for two partner cores would put all four measured rates below 64 GB/s on the port (est.). So the conversion cannot say whether the rate on the port is below or above 64 GB/s.</li>"
    "</ul></li>")

# ---- line 426: the value per mesh cycle is a rate divided by the mesh clock
sub(426, "In one pair of runs of that case CPU 2 sent 0.50 bus writes per mesh cycle while its partner also wrote. With the first assumption",
    "In one pair of runs of that case CPU 2 sent 0.99 × 10<sup>9</sup> bus writes per second while its partner also wrote. At the mesh clock of 2.0 GHz that is 0.50 bus writes per mesh cycle (est.). With the first assumption")

# ---- line 427
sub(427, "That is 56.6 GB/s per pair, which is 0.88 of 64 GB/s. This run has two busy pairs. It is not a test of hypothesis 2.",
    "That is 56.6 GB/s per pair, which is 0.88 of 64 GB/s (est.). This run has two busy pairs. It is not one of the runs of hypothesis 2.")

# ---- line 428: the premise behind "at most one flit per mesh cycle"
sub(428, "The counter covers one data channel [CMN S3 TRM, pages 1678 to 1679]. So it cannot count more than one flit per mesh cycle.",
    "The counter covers one data channel. Its event is one signal, and the signal is set in a cycle that sends a flit [CMN S3 TRM, pages 1678 to 1679]. So it cannot count more than one flit per mesh cycle.")

# ---- line 433
sub(433, "The manual gives no numbering for this field [CMN S3 TRM, page 1656]. For the design parameter POR_DAT_VC_NUM_PARAM, 1 means one data channel, and a value above 1 means two sub-channels [CMN S3 TRM, page 1678]. This report assumes the same numbering for the field. Then a value of 1 supports hypothesis 1, and a value of 2 or more rejects it.",
    "The manual does not say which value of this field stands for which number of channels [CMN S3 TRM, page 1656]. For the design parameter POR_DAT_VC_NUM_PARAM, 1 means one data channel. A value above 1 means that the data channel is split into sub-channels, and the page names sub-channel 1 and sub-channel 2 [CMN S3 TRM, page 1678]. This report assumes that the field counts the channels in the same way. Then a value of 1 supports hypothesis 1, and a value of 2 or more rejects it. A value of 0 would show that the field counts in another way. Then this rule does not apply.")
sub(433, "A test can leave the port partly idle.", "A run can leave the port partly idle.")
sub(433, "It covers one data channel. So it cannot count more than one flit per mesh cycle. A read of the register field can show it.",
    "It covers one data channel, and its event is one signal. So it cannot count more than one flit per mesh cycle. A read of the register field can show it.")
sub(433, "With the scaled share of 0.81 they give 1.97 to 1.99 × 10<sup>9</sup> (est.).",
    "With the scaled share of 0.81 they give 1.97 to 1.99 × 10<sup>9</sup> bus reads per second (est.).")

# ---- line 434: both directions; the two values are rates divided by the mesh clock
sub(434, "A rate clearly below 1.0 means that this data channel had idle cycles. Then the full data channel did not limit the pair. That result rejects hypothesis 2 for reads and leaves hypothesis 1 open.",
    "A rate clearly below 1.0 means that this data channel had idle cycles. Then a full channel toward the cores did not limit the pair. A reader also sends data the other way, 1.653 bus writes per line for one reader. So count the bus writes of both cores in the same run. If both directions had idle cycles, the result rejects hypothesis 2 for reads. It leaves hypothesis 1 open.")
sub(434, "Part 5 holds two such counts, each of one core only: 0.98 bus writes per mesh cycle for one writer alone at 1 GiB, and 0.50 for CPU 2 at 8 MiB while its partner also wrote.",
    "Part 5 holds two first values, each of one core only: 0.98 bus writes per mesh cycle for one writer alone at 1 GiB, and 0.50 for CPU 2 at 8 MiB while its partner also wrote (est.). The runs that counted these bus writes did not count the mesh cycles. Each value is the bus writes per second divided by the mesh clock of 2.0 GHz.")

# ---- line 435: which comparison tests which statement; sub-items
whole(435, "<li>Conversion. Let the read test above count",
    "<li>Conversion.<ul>"
    "<li>Let the read test above count the bus reads of both cores and the data flits at the port in one run. As many bus reads as flits supports the first assumption. For the second assumption, compare the flits per line of the pair with the 1.653 of one core.</li>"
    "<li>Suppose that the bus reads stay at or below the mesh cycles. If the flits per line of the pair differ from the 1.653 of one core, the second assumption fails for reads. Then the converted rates in the item \"Reads at 8 MiB\" are wrong. That result does not test hypothesis 1.</li>"
    "<li>If the bus reads differ from the flits, the first assumption is in doubt. Then every converted number that uses a bus count is in doubt too, for example the 84 GB/s in the item \"Writes at 8 MiB\". More bus reads than flits can also mean a second data channel. The flit counter covers one data channel. It would not count the flits of a second one. So that result rejects the first assumption or hypothesis 1, and the run alone does not show which. A read of the register field can show it.</li>"
    "<li>More bus reads than mesh cycles is the case of the capacity item above.</li>"
    "<li>For writes, compare the bus writes per line of both partner cores with the 1.52 (8 MiB) and the 2.00 (1 GiB) of one core. Part 5 gives a first value for one of the two cores: the 1.52 of CPU 2 in the item \"Writes at 8 MiB\".</li>"
    "</ul></li>")

# ---- line 437: heading matches the body; sub-items; the third older statement; rate before ratio
whole(437, "<li><b>Older statements that need a correction.</b>",
    "<li><b>Older statements that the new rates put in doubt.</b><ul>"
    "<li>\"For DRAM streams the port is not the limit\" (section \"Is the pair port how the mesh cache is reached?\") and \"For DRAM traffic the port is not the limit\" (section \"The pair finding\") rest on a read test. The measured rates above do not support them for write streams. Two partner cores together wrote 63.2 GB/s at 1 GiB. One core alone wrote 63.0 GB/s. So the second core added 0.2 GB/s (0.3 %). Four writers on two pairs wrote 113 GB/s. So two partner writers share one limit at 1 GiB. This follows from the measured rates, and it does not depend on the hypotheses. The rates do not show what the shared limit is. That the full port is this limit is part of hypothesis 2.</li>"
    "<li>\"For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2\" (section \"Is the pair port how the mesh cache is reached?\") states more than the rates show. The rates show that two partner readers share one limit of about 78 GB/s. That the full port is this limit is part of hypothesis 2. The 78 GB/s also counts the lines that the two cores take from their own L2.</li>"
    "<li>\"The single-writer limit is inside the core\" (section \"Where one writer's 73 GB/s limit sits\") was written for 8 MiB writes. For 1 GiB writes it is in doubt. One writer sends 1.96 × 10<sup>9</sup> bus writes per second there [writepath.csv, case w1G-c2]. At the mesh clock of 2.0 GHz that is 0.98 bus writes per mesh cycle (est.). If hypothesis 1 and the first assumption of the conversion hold, that is 98 % of the capacity of the port (est.). If hypothesis 2 also holds for this case, the port limits one writer at 1 GiB, and the core does not.</li>"
    "<li>These sections are unchanged for now.</li>"
    "</ul></li>")

# ---- line 452: two entries on one source line; the folder is named
whole(452, "<dt>bus access, bus read, bus write</dt>",
    "<dt>bus access, bus read, bus write</dt><dd>One data transfer between a core and the mesh, as the core's own counters count it (Arm events BUS_ACCESS and BUS_ACCESS_WR). A bus write goes from the core to the mesh, and a bus read goes to the core. Arm's event list for this core says that each beat of data is counted individually [Linux source in Arm's kit, tools/perf/pmu-events/arch/arm64/arm/neoverse-v3/bus.json]. The file is in the folder neoverse-v3 of that source. The table mapfile.csv of the same source assigns part 0xd83, the part number of CRB's cores, to that folder. A beat is one transfer on the bus. This report takes one transfer as 32 B. That belongs to the first assumption of the conversion in \"Open items\". One count of part 5 fits it: one writer sent 2.00 bus writes per 64 B line at 1 GiB.</dd>"
    "<dt>bus reads in part 5</dt><dd>Part 5 counted all bus accesses and the bus writes. It did not count the bus reads. This report takes them as all bus accesses minus bus writes (est.). Arm's list also says that the count of all bus accesses includes snoop requests and snoop responses. A snoop is a request from the mesh to a core about a line that the core may hold. So the difference can hold more than bus reads. The port counts of case r8M-c2 (the 2 s run minus the 0.2 s run) hold 4,182 snoop flits and 3.3 × 10<sup>9</sup> data flits from the crosspoint to the port in 1.8 s. So snoops were a small part of the traffic at that port.</dd>")

out = "\n".join(L)
assert out.count("\n") == src.count("\n")
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write(out); print("written")
else:
    print("dry run ok")
