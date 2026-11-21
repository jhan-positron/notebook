#!/usr/bin/env python3
"""Fixes after the check of the second step of 2026-11-12 (check3: four checkers, each
followed by a second checker). Every edit stays on its physical line, so the report keeps
978 lines. Each edit names the finding that it answers.
sub(): the old text must occur exactly once in its line.
Usage: apply_report_p_fixes.py <report.html> [--write]"""
import sys

P = sys.argv[1]
L = open(P, encoding="utf-8").read().split("\n")
assert len(L) == 979 and L[-1] == "", len(L)
n_edits = 0
ASM = "results/followup-20261030T194205Z/asm.csv"
BW = "results/20261030T193108Z/bandwidth.csv"
WP = "results/sudo-20261102T211150Z/writepath.csv"


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


# ---- line 49 (language-render-11): the name in quotes is a section, and the section has four tables
sub(49, 'and the estimate is explained under the table "Where each number in the figure comes from".',
    'and the estimate is explained in the section "Where each number in the figure comes from", under its first table.')

# claims-X1: the change note named three replaced statements and none of the other corrections
sub(49, "DRAM traffic on a pair, and the limit of one writer.</div>",
    "DRAM traffic on a pair, and the limit of one writer. The same change corrected more statements. Two cores of different pairs read 125 to 134 GB/s "
    "(before: 134 GB/s). The pair chart shows the read loop compiled from C (its caption said \"asm read\"), and it has two more bars. "
    "The sentence \"From the SLC and DRAM the two loops agree, so there the limit is outside the core\" in \"Bandwidth per core\" is withdrawn. "
    "\"Words used here\" has new entries for credit stall, data stall, back-pressure, write in flight and partner cores.</div>")

# ---- line 52 (claims-8): the pair test ran on three pairs
sub(52, "the two cores of a pair (cores 2k and 2k+1) together read only about 78 GB/s, against",
    "the two cores of a pair (cores 2k and 2k+1, three pairs tested) together read only about 78 GB/s, against")

# ---- line 110 (claims-7, numbers-reads-7): one basis for the inference in every place
sub(110, "That two cores sit on one crosspoint port (Arm's CAL2) is inferred from the CMN S3 manual and the map's port count.",
    "That two cores sit on one crosspoint port is inferred from two timing tests and from the map's port count "
    "(see \"The SLC (L3) and the pair port\"). Arm's manual describes the block that allows it (CAL2).")

# ---- line 118 (numbers-reads-X3): 32 B is the data that a data flit holds, not the size of the flit
sub(118, "The flit size is from Arm's manual [CMN S3 TRM, Table A-2 page 2120].",
    "The 32 B are from Arm's manual [CMN S3 TRM, Table A-2 page 2120].")

# ---- line 121
sub(121, "<tr><td>Size of one data flit</td>", "<tr><td>Data that one data flit holds</td>")                      # numbers-reads-X3
sub(121, "<tr><td>Write, 1 GiB each</td>", "<tr><td>Write, 1 GiB each, asm loop</td>")                            # claims-1 and three others
sub(121, f"The write rates at 8 MiB are from nine runs of 2026-11-02 and one run of 2026-10-30 [{WP}, case w8M-c2c3; {ASM}].",
    f"The write rates at 8 MiB are from the nine runs of 2 s of part 5 on CPUs 2 and 3 (2026-11-02, 81.4 to 82.1 GB/s) and from one run of 2026-10-30 "
    f"on CPUs 0 and 1 (82.3 GB/s) [{WP}, case w8M-c2c3; {ASM}]. Both are converted with the count of CPU 2.")  # numbers-reads-X2, numbers-writes-X3
sub(121, f"The write rate at 1 GiB is from one run with each write loop on 2026-10-30 [{ASM}; {BW}].",
    f"The write rate at 1 GiB is from one run with the asm loop on 2026-10-30 [{ASM}].")
sub(121, "if something else limits the pair to that rate.</li>",
    "if something else limits the pair to that rate.</li><li>Other runs with two partner cores were not converted. No bus count exists for them. "
    f"They are the write runs of the loop compiled from C (75.6 GB/s at 8 MiB and 63.2 GB/s at 1 GiB) [{BW}] and the copy runs of the asm loop "
    f"(80.9 GB/s at 8 MiB and 72.5 GB/s at 1 GiB, counted as bytes read plus bytes written) [{ASM}]. So these runs were not compared with the estimate.</li>")
sub(121, "For the writes at 8 MiB one writer alone sends 1.52 bus writes per 64 B line, not 2. For the writes at 1 GiB one writer alone sends 2.00 bus writes per line.",
    "For the writes at 8 MiB one asm writer alone sends 1.52 bus writes per 64 B line, not 2. For the writes at 1 GiB one asm writer alone sends 2.00 bus writes per line.")
sub(121, "No run counted both cores of a pair.", "No run counted the bus accesses of both cores of a pair.")     # numbers-reads-1, claims-3
sub(121, "One run counted one core of a writing pair. In that run CPU 2 sent 1.52 bus writes per line that it wrote itself.",   # numbers-writes-X4
    "One pair of runs (0.2 s and 2 s) counted one core of a writing pair. In these runs CPU 2 sent 1.52 bus writes per line that it wrote itself.")
sub(121, "That is the same count as alone.</li>",                                                                # claims-4, numbers-reads-X1
    "That is the same count as alone.</li><li>The read row has one more limit. The share of 83 % was counted with the asm loop on 2026-11-02. "
    "Four of the five read rates are from the read loop compiled from C on 2026-10-30. No run counted the share for that loop with one or two busy cores. "
    "Only the lowest rate, 77.5 GB/s, is from the asm loop. Converted, it is 64.1 GB/s at the port (est.).</li>")

# ---- line 179 (claims-X3): the sentence spoke for every claim of the section
sub(179, "Each claim that neither confirms is marked as an inference or as a hypothesis.",
    "The CAL2 and the two hypotheses on the pair port are marked as an inference or as hypotheses.")

# ---- line 206 (claims-8, numbers-reads-4, text of the second checker): the pair test ran partner cores on three pairs
sub(206, 'Latency fit, and the pair test (cores 2k and 2k+1 running together read 77.5 to 78.5 GB/s with a buffer of 8 MiB each, and two cores of different pairs '
         'read 125 to 134 GB/s, see "The pair finding"). The pair test fits two cores on one port. It does not show what limits the pair. Not read from hardware',
    'Latency fit (all 120 CPUs that were measured), and the pair test. The pair test ran partner cores on three pairs (CPUs 0 and 1, 2 and 3, 4 and 5). '
    'Each pair together read 77.5 to 78.5 GB/s with a buffer of 8 MiB for each core. Two cores of different pairs read 125 to 134 GB/s (see "The pair finding"). '
    'For these three pairs the pair test fits two cores on one port. It does not show what limits the pair. Not read from hardware')

# ---- line 213 (numbers-reads-2): the rate of a core with an idle partner, from the per-thread columns
sub(213, "A core with an idle partner reads the full 67 GB/s of one core alone.",
    "With one more busy core on another pair, a core with an idle partner read 62.4 to 67.1 GB/s (seven runs). "
    "A core with a busy partner read 37.8 to 40.3 GB/s (five runs).")

sub(213, "[CMN S3 TRM, section 2.1.1.15 page 63]. The measurement in \"The pair finding\" ran two cores at the same time.",
    "[CMN S3 TRM, section 2.1.1.15 page 63].</p><p>The measurement in \"The pair finding\" ran two cores at the same time.")
sub(213, "A core with a busy partner read 37.8 to 40.3 GB/s (five runs). What is confirmed by the document is that the mechanism exists. "
         "What is measured is that CRB's cores are limited in pairs.",
    "A core with a busy partner read 37.8 to 40.3 GB/s (five runs).</p><p>What is confirmed by the document is that the mechanism exists. "
    "What is measured is that the two cores of a pair slow each other on the three pairs that were tested (CPUs 0 to 5).")

# ---- line 266 (language-render-3 and -12): what "shared limit" meant, and the long paragraph as a list
old266 = ("<p class=\"take\"><b>The asm loop doubles the L1 numbers and is the real per-core ceiling.</b> 133 GB/s read is 3 loads of 16 B per cycle, "
          "89.5 GB/s write is 2 stores of 16 B per cycle. From the SLC the two read loops give almost the same rate (67.0 and 67.5 GB/s). "
          "This does not show a shared limit. The loop compiled from C reads 66.8 to 67.1 GB/s at 32 KiB, 1 MiB and 8 MiB alike. "
          "From DRAM the two read loops differ by 8 % (28.2 GB/s compiled from C, 30.5 GB/s asm). The write loops do not agree. "
          "The loop compiled from C writes 44.8 GB/s at 8 MiB and at 1 GiB. The asm loop writes 73.2 GB/s at 8 MiB and 63.0 GB/s at 1 GiB. "
          "These rates do not show where the limit of one core is. Mesh counters for the 8 MiB run show 81 % of lines coming from the SLC and 19 % from L2, "
          "so the SLC delivers about 54 GB/s to one core.</p>")
new266 = ("<p class=\"take\"><b>The asm loop doubles the L1 numbers and is the real per-core ceiling.</b> 133 GB/s read is 3 loads of 16 B per cycle, "
          "89.5 GB/s write is 2 stores of 16 B per cycle.</p><ul>"
          "<li><b>Reads from the SLC.</b> The two read loops give almost the same rate (67.0 and 67.5 GB/s). This does not show that the two loops have the same limit. "
          "The loop compiled from C reads 66.8 to 67.1 GB/s at 32 KiB, 1 MiB and 8 MiB alike. So its rate at 8 MiB can be the limit of the loop itself (section \"The read loop compiled from C: 1.5 loads per cycle\").</li>"
          "<li><b>Reads from DRAM.</b> The two read loops differ by 8 % (28.2 GB/s compiled from C, 30.5 GB/s asm).</li>"
          "<li><b>Writes.</b> The write loops do not agree. The loop compiled from C writes 44.8 GB/s at 8 MiB and at 1 GiB. "
          "The asm loop writes 73.2 GB/s at 8 MiB and 63.0 GB/s at 1 GiB.</li>"
          "<li>These rates do not show where the limit of one core is.</li>"
          "<li>Mesh counters for the 8 MiB run show 81 % of lines coming from the SLC and 19 % from L2, so the SLC delivers about 54 GB/s to one core.</li></ul>")
assert L[265] == old266, L[265][:120]
L[265] = new266; n_edits += 1

# ---- line 278 (numbers-writes-8): the table gives the value for 1 GiB in brackets where it differs
sub(278, "<td>2 × 10<sup>4</sup> per second against 1.85 × 10<sup>9</sup> flits per second</td>",
    "<td>2 × 10<sup>4</sup> [3 × 10<sup>4</sup>] per second against 1.85 × 10<sup>9</sup> [2.14 × 10<sup>9</sup>] flits per second</td>")

# ---- line 289
# numbers-writes-X1: the sentence named a behaviour of Arm and cited no Arm document
sub(289, "The lines are not allocated in L1 or L2 (zero refills for writes, zero write-backs), so Arm's write-streaming behaviour is confirmed by measurement.</p>",
    "The lines are not allocated in L1 or L2. Part 5 counted 0.000 refills for writes per line and at most 0.001 write-backs per line (table above). "
    "This report calls such writes streaming writes.</p>")
# claims-2: the loop of the rates
sub(289, "<ul><li><b>One writer alone writes 70.4 to 73.2 GB/s with a buffer of 8 MiB.</b>",
    "<ul><li>All rates in this list are from the asm write loop. With the write loop compiled from C one writer alone writes 44.8 GB/s at 8 MiB and at 1 GiB.</li>"
    "<li><b>One writer alone writes 70.4 to 73.2 GB/s with a buffer of 8 MiB.</b>")
# numbers-writes-2, claims-6: the runs of the range
sub(289, f"The runs are from 2026-10-30 and 2026-11-02, on CPUs 0 and 2 [{ASM}; {WP}].</li>",
    f"On 2026-10-30 CPU 0 wrote 73.2 GB/s (best of three repetitions of 0.5 s) [{ASM}]. In part 5 on 2026-11-02 CPU 2 wrote 70.4 to 71.3 GB/s "
    f"in the nine runs of 2 s [{WP}]. All rates of part 5 in this list are from the runs of 2 s. The nine runs of 0.2 s of one writer gave 68.9 to 70.7 GB/s.</li>")
# language-render-8, numbers-writes-3, claims-6: which parts, and which pair
sub(289, "<li><b>Other runs sent more through the same parts.</b>", "<li><b>Other runs sent more data through the same port or through the same mesh.</b>")
sub(289, "With the partner core also writing, the pair writes 81.4 to 82.3 GB/s. Four writers on four ports write 228 to 230 GB/s.</li>",
    f"With its partner CPU 3 also writing, the pair wrote 81.4 to 82.1 GB/s. The pair of CPUs 0 and 1 wrote 82.3 GB/s on 2026-10-30 [{ASM}]. "
    "Four writers on four ports (CPUs 2, 4, 6 and 8) wrote 228 to 230 GB/s.</li>")
sub(289, "This estimate uses the count of CPU 2. CPU 3 was not counted.</li>",
    "This estimate uses the count of CPU 2. CPU 3 was not counted. CPUs 0 and 1 were not counted either.</li>")
# language-render-9, claims-5, numbers-writes-7: which path, which CPUs, and the counters of these runs
sub(289, "<li><b>The runs do not rule out a limit that depends on the shared path.</b> With a second busy port each writer falls from 71 GB/s to between 60 and 61 GB/s. "
         "With four busy ports the writers fall to 57 GB/s on average (55 to 59 GB/s by writer).",
    "<li><b>The runs do not exclude a limit in the path that writers share outside the core.</b> CPU 2 alone writes 71 GB/s. "
    "With a second busy port (CPUs 2 and 4) each of the two writers writes between 60 and 61 GB/s. With four busy ports (CPUs 2, 4, 6 and 8) the writers write "
    "57 GB/s on average (55 to 59 GB/s by writer). No run measured CPU 4, 6 or 8 alone. So the fall is measured for CPU 2 only. "
    "The back-pressure counters rise in these runs. The home nodes of mesh 0 show 1.7 × 10<sup>6</sup> data stalls per second with two busy ports "
    "and 2.0 × 10<sup>7</sup> per second with four busy ports. The links out of the crosspoint of CPU 2 show 7 × 10<sup>5</sup> credit-stall cycles per second with four busy ports. "
    "These counts stay small: with four busy ports the home nodes show 0.005 data stalls per line written.")
# numbers-writes-4: the loop of the rates at 1 GiB
sub(289, "One writer alone writes 63.0 GB/s (CPU 0, 2026-10-30) and 62.9 GB/s (CPU 2, part 5). Two partner writers together write 63.2 GB/s (CPUs 0 and 1, 2026-10-30). "
         "So one writer alone already reaches the rate of the pair.",
    "With the asm loop one writer alone writes 63.0 GB/s (CPU 0, 2026-10-30) and 62.9 GB/s (CPU 2, part 5). Two partner writers together write 63.2 GB/s "
    "with the same loop (CPUs 0 and 1, 2026-10-30). So one asm writer alone already reaches the rate of the pair. With the loop compiled from C one writer alone "
    "writes 44.8 GB/s, and the pair writes 63.2 GB/s (table in \"The pair finding\").")

# ---- line 380 (language-render-6 and -7): two words of the approved text that are not literal
sub(380, "<b>Two heavy threads on two pairs read 1.6 to 1.7 times", "<b>Two threads on two pairs read 1.6 to 1.7 times")
sub(380, "So two partner readers are not held to the rate of one reader.", "So two partner readers are not limited to the rate of one reader.")

# ---- line 437 (claims-2, numbers-writes-5, claims-9)
sub(437, "At 1 GiB one writer alone already reaches the rate of the pair.</li>",
    "At 1 GiB one writer alone already reaches the rate of the pair with the asm loop (63.0 against 63.2 GB/s). With the loop compiled from C one writer alone writes 44.8 GB/s.</li>")
sub(437, "Still open: what limits a pair, and what limits one writer at 8 MiB. The tests are the missing tests of the item above and the per-core asm write sweep.",
    "Still open: what limits a pair, whether the pair port limits reads at 1 GiB, and what limits one writer at 8 MiB. The tests are the missing tests of the item above, "
    "the per-core asm write sweep, and a read run at 1 GiB with two cores of different pairs on one mesh (for example CPUs 0 and 2).")

# ---- line 451 (language-render-2 and -10, numbers-reads-6): no undefined abbreviation, and the name that the table uses
sub(451, "A data stall is one count of a home-node event. Arm describes it as \"Counts number of times HN-F has a pending TXDAT flit but no credits to upload\" [CMN S3 TRM, page 391].",
    "A data stall is one count of the home-node event for a home node that has a data flit to send and no credit for it "
    "[CMN S3 TRM, page 391, event PMU_HN_TXDAT_STALL_EVENT]. The table of part 5 calls it a \"data-send stall\".")

sub(451, "<dt>credit stall, data stall, back-pressure</dt>", "<dt>credit stall, data stall</dt>")
sub(451, " Back-pressure is this report's word for such waits.</dd>",
    "</dd><dt>back-pressure</dt><dd>This report's word for the waits of a sender that has no credit. Credit-stall cycles and data stalls count such waits.</dd>")

# ---- line 462 (claims-7): an inference, as lines 110 and 213 say
sub(462, "The sharing follows from two timing tests", "The sharing is inferred from two timing tests")

assert len(L) == 979 and L[-1] == "", len(L)
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, {len(L) - 1} lines")
