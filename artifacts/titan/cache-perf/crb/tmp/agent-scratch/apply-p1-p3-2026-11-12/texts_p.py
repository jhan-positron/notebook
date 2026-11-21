#!/usr/bin/env python3
"""New report texts of the second step of 2026-11-12:
  - Spec box of the pair port: "estimated 64 GB/s", with its explanation
  - P1, P2 and P3 of record section 10.6, as structured HTML
Each text is one physical line of the report. J() joins a draft that is broken at tag
boundaries only, so no white space is lost or added inside a sentence."""


def J(s):
    out = "".join(part.strip() for part in s.strip().split("\n"))
    assert "\n" not in out
    return out


PAIR = "results/followup-20261030T194205Z/pair.csv"
ASM = "results/followup-20261030T194205Z/asm.csv"
BW = "results/20261030T193108Z/bandwidth.csv"
WP = "results/sudo-20261102T211150Z/writepath.csv"
WB = "results/sudo-20261102T054936Z/writebw.csv"

# ---------------------------------------------------------------- line 92, Spec box of the pair port
L92 = J("""
<g><rect x="504" y="156" width="76" height="48" rx="6" fill="#ffffff" stroke="#eb6834"/>
<text x="542" y="175" text-anchor="middle" fill="#5b6470">estimated</text>
<text x="542" y="192" text-anchor="middle">64 GB/s</text></g>
""")

# ---------------------------------------------------------------- line 118, row of the source table
L118 = J("""
<tr><td>Spec row, pair port: estimated 64 GB/s</td>
<td>Derived, and an estimate (est.). Not measured. One data flit holds 32 B (a flit is one transfer unit on a mesh port, see "flit" in "Words used here"). One data flit per mesh cycle is 32 B × 2.0 GHz = 64 GB/s in each direction (est.). The flit size is from Arm's manual [CMN S3 TRM, Table A-2 page 2120]. The mesh clock is measured (see "mesh clock" in "Words used here"). That the port passes at most one data flit per mesh cycle in each direction is hypothesis 1 (capacity) in "Open items". It is not confirmed. The estimate counts only the bytes that cross the port. The measured ~80 GB/s counts every byte that the two partner cores read. The text under this table explains both points.</td></tr>
""")

# ---------------------------------------------------------------- line 121, explanation under the source table
L121 = J(f"""
</table></div>
<p><b>The estimate for the pair port.</b> The Spec box of the pair port says "estimated 64 GB/s". The estimate is the product of three factors.</p>
<div class="tw"><table>
<tr><th>Factor</th><th>Value</th><th>How it is known</th></tr>
<tr><td>Size of one data flit</td><td>32 B</td><td>Arm document</td></tr>
<tr><td>Mesh clock</td><td>2.0 GHz</td><td>Measured</td></tr>
<tr><td>Data flits that the port passes in one direction in one mesh cycle</td><td>at most 1</td><td>Hypothesis 1, not confirmed</td></tr>
<tr><td>Product: bytes that cross the port in one direction</td><td>64 GB/s</td><td>Derived (est.)</td></tr>
</table></div>
<ul>
<li>The third factor is the uncertain one. It is hypothesis 1 in "Open items": the port has one data channel in each direction, and a channel passes at most one data flit per mesh cycle.</li>
<li>The number of data channels at the port was not read from CRB. Arm's manual draws one data channel in each direction at a device port [CMN S3 TRM, Figure 2-25 page 89].</li>
<li>The estimate is a maximum for one direction. It does not say that a run reaches it.</li>
</ul>
<p><b>Why the estimate is lower than the measured ~80 GB/s.</b> The two numbers are counted at two different places. The measured rate counts every byte that the two loops read. The estimate counts only the bytes that cross the port in one direction. The table is for two partner cores that each read their own buffer of 8 MiB.</p>
<div class="tw"><table>
<tr><th>Where the bytes are counted</th><th>Rate</th><th>Kind</th></tr>
<tr><td>At the loops: every byte that the two cores read</td><td>77.5 to 78.5 GB/s</td><td>Measured</td></tr>
<tr><td>Part that the cores take from their own L2 (17 % of the lines)</td><td>about 13.5 GB/s</td><td>est.</td></tr>
<tr><td>Part that crosses the pair port toward the cores (83 % of the lines)</td><td>64.1 to 64.9 GB/s</td><td>est.</td></tr>
</table></div>
<ul>
<li>The measured rates are from five runs of 2026-10-30: four with the read loop compiled from C and one with the asm loop [{PAIR}, {ASM} and {BW}].</li>
<li>The split of 83 % and 17 % was counted on 2026-11-02 with the asm loop and with one busy core. Three counters gave it [{WP}, case r8M-c2; {WB}, case asmread-8M-1]. No run counted it with only two partner cores busy.</li>
<li>An older count gives 81 % (est., from scaled counts of 2026-10-30). With that share 62.9 to 63.7 GB/s cross the port (est.).</li>
<li>So this conversion cannot say whether the rate on the port is below or above 64 GB/s.</li>
<li>For one core alone the two places of counting were measured in one run. The loop read 71 GB/s, and its port carried 58.7 GB/s toward the core [{WP}, case r8M-c2].</li>
</ul>
<p>Three kinds of run with two partner cores can be converted to the port. Each converted rate is close to 64 GB/s.</p>
<div class="tw"><table>
<tr><th>Run with two partner cores</th><th>At the loops, measured</th><th>At the port (est.)</th><th>Share of the estimate (est.)</th></tr>
<tr><td>Read, 8 MiB each</td><td>77.5 to 78.5 GB/s</td><td>64.1 to 64.9 GB/s</td><td>1.00 to 1.01</td></tr>
<tr><td>Write, 8 MiB each, asm loop</td><td>81.4 to 82.3 GB/s</td><td>62.0 to 62.7 GB/s</td><td>0.97 to 0.98</td></tr>
<tr><td>Write, 1 GiB each</td><td>63.2 GB/s</td><td>63.2 GB/s</td><td>0.99</td></tr>
</table></div>
<ul>
<li>The read rates are from the five runs of the table above. The write rates at 8 MiB are from nine runs of 2026-11-02 and one run of 2026-10-30 [{WP}, case w8M-c2c3; {ASM}]. The write rate at 1 GiB is from one run with each write loop on 2026-10-30 [{ASM}; {BW}].</li>
<li>The conversion differs by run. For the reads it is the share of 83 %. For the writes at 8 MiB one writer alone sends 1.52 bus writes per 64 B line, not 2. For the writes at 1 GiB one writer alone sends 2.00 bus writes per line. A bus write is one data transfer from a core to the mesh (see "bus access" in "Words used here").</li>
<li>The conversion makes two assumptions. One bus write is one data flit of 32 B at the port. A count that was measured on one core alone also holds for two partner cores. No run counted both cores of a pair. One run counted one core of a writing pair. In that run CPU 2 sent 1.52 bus writes per line that it wrote itself. That is the same count as alone.</li>
<li>The rates fit the estimate. They do not prove it. A rate close to 64 GB/s also fits a port with a higher maximum, if something else limits the pair to that rate.</li>
<li>Two tests are missing. The first reads the number of data channels at the port from CRB (register field dat_vc_num_p). The second counts the bus reads of both partner cores and the mesh cycles in one run. "Open items" describes both tests and gives the source of each rate and count.</li>
</ul>
""")

# ---------------------------------------------------------------- line 214, P2 (reads at 8 MiB) and the pointer of P1
L214 = J(f"""
<p class="take"><b>For software: with a buffer of 8 MiB for each thread, two threads on two pairs read 1.6 to 1.7 times as much as two threads on one pair.</b> What limits a pair was not measured.</p>
<p>The rates in the table are for a buffer of 8 MiB for each thread. They were measured on 2026-10-30 with no other busy core [{PAIR}, {ASM} and {BW}]. Each rate is the best repetition of its run.</p>
<div class="tw"><table>
<tr><th>Threads and runs</th><th>Read rate of all threads together</th></tr>
<tr><td>One thread alone on CPU 0 (three runs: two with the asm loop, one with the read loop compiled from C)</td><td>66.9 to 67.5 GB/s</td></tr>
<tr><td>Two threads on partner cores (five runs on the pairs of CPUs 0 to 5: four with the read loop compiled from C, one with the asm loop)</td><td>77.5 to 78.5 GB/s</td></tr>
<tr><td>Two threads on cores of different pairs, both on mesh 0 (five runs)</td><td>125 to 132 GB/s</td></tr>
<tr><td>Two threads on cores of different meshes (two runs)</td><td>134 GB/s</td></tr>
<tr><td>Four threads on two pairs, CPUs 0 to 3 (one run with the asm loop, one with the read loop compiled from C)</td><td>127.6 and 129.1 GB/s</td></tr>
</table></div>
<ul>
<li>With two busy pairs (CPUs 0 to 3) the four threads together read 0.82 to 0.83 of two times the rate of one pair.</li>
<li>In the root runs of 2026-11-02 one thread alone read 69.6 to 71.2 GB/s (CPUs 0 and 2, runs of 2 s) [{WB}; {WP}]. The cause of the difference from the 66.9 to 67.5 GB/s of 2026-10-30 is not known.</li>
<li>All these rates count the bytes that the loops read. They include the lines that a core takes from its own L2. For one core alone that is 0.17 of the lines. No run counted it with only two partner cores busy.</li>
<li>What limits the pair was not measured. Hypothesis 2 of "Open items" says that the full pair port is this limit. Hypothesis 1 says that the port passes at most 64 GB/s in each direction.</li>
<li>The 78 GB/s and the 64 GB/s are counted at two different places. If 0.83 of the lines cross the port, as counted for one core alone, 77.5 to 78.5 GB/s at the loops is about 64 to 65 GB/s at the port (est.).</li>
<li>With a buffer of 1 GiB for each core, reads and writes behave differently on a pair (section "The pair finding").</li>
</ul>
""")

# ---------------------------------------------------------------- line 289, P3 (one writer)
L289 = J(f"""
<p class="take"><b>What limits one writer at 8 MiB was not measured.</b> The lines are not allocated in L1 or L2 (zero refills for writes, zero write-backs), so Arm's write-streaming behaviour is confirmed by measurement.</p>
<ul>
<li><b>One writer alone writes 70.4 to 73.2 GB/s with a buffer of 8 MiB.</b> The runs are from 2026-10-30 and 2026-11-02, on CPUs 0 and 2 [{ASM}; {WP}].</li>
<li><b>With one writer the counters show almost no back-pressure.</b> The links out of the crosspoint show 2 × 10<sup>4</sup> credit-stall cycles per second against 1.85 × 10<sup>9</sup> data flits per second. The home nodes of mesh 0 show 1 × 10<sup>4</sup> data stalls per second.</li>
<li><b>Other runs sent more through the same parts.</b> CPU 2 sent 1.68 × 10<sup>9</sup> bus writes per second at 8 MiB and 1.96 × 10<sup>9</sup> per second at 1 GiB. With the partner core also writing, the pair writes 81.4 to 82.3 GB/s. Four writers on four ports write 228 to 230 GB/s.</li>
<li><b>These rates count the bytes that the loops wrote.</b> At 8 MiB a line needs 1.52 bus writes, not 2, for a reason that is not known. So 82 GB/s at the loops is about 62 to 63 GB/s at the port (est.). This estimate uses the count of CPU 2. CPU 3 was not counted.</li>
<li><b>The runs do not rule out a limit that depends on the shared path.</b> With a second busy port each writer falls from 71 GB/s to between 60 and 61 GB/s. With four busy ports the writers fall to 57 GB/s on average (55 to 59 GB/s by writer). No counter of part 5 covers the write data from the port to the crosspoint.</li>
<li><b>Hypothesis, not tested.</b> The core keeps at most a fixed number of writes in flight. Then the rate of one writer is that number divided by the round-trip time to the home node. The test is a per-core asm write sweep, like the per-core read sweep. It was not run.</li>
<li><b>At 1 GiB the comparison with the partner gives another result.</b> One writer alone writes 63.0 GB/s (CPU 0, 2026-10-30) and 62.9 GB/s (CPU 2, part 5). Two partner writers together write 63.2 GB/s (CPUs 0 and 1, 2026-10-30). So one writer alone already reaches the rate of the pair. What limits the pair was not measured. Hypothesis 2 of "Open items" says that the full pair port is this limit. One count fits it. The 1.96 × 10<sup>9</sup> bus writes per second of CPU 2 are 0.98 bus writes per mesh cycle at the mesh clock of 2.0 GHz (est.). If one bus write is one data flit at the port, that is 98 % of the capacity of hypothesis 1 (est.).</li>
</ul>
""")

# ---------------------------------------------------------------- line 380, P1 (1 GiB on a pair) and the 8 MiB sentence of P2
L380 = J(f"""
<p class="take"><b>Two heavy threads on two pairs read 1.6 to 1.7 times as much as two threads on one pair (buffer of 8 MiB for each thread).</b> With a buffer of 1 GiB for each core, reads and writes behave differently on a pair.</p>
<p>The table is for a buffer of 1 GiB for each core. All its rates are from 2026-10-30. The pair is CPUs 0 and 1 [{ASM}; {BW}].</p>
<div class="tw"><table>
<tr><th>Test</th><th>One core alone</th><th>Two partner cores together</th><th>The second core adds</th></tr>
<tr><td>Read, loop compiled from C</td><td>28.2 GB/s</td><td>52.6 GB/s</td><td>24.5 GB/s (87 %)</td></tr>
<tr><td>Read, asm loop</td><td>30.5 GB/s</td><td>56.7 GB/s</td><td>26.2 GB/s (86 %)</td></tr>
<tr><td>Write, asm loop</td><td>63.0 GB/s</td><td>63.2 GB/s</td><td>0.2 GB/s (0.3 %)</td></tr>
<tr><td>Write, loop compiled from C</td><td>44.8 GB/s</td><td>63.2 GB/s</td><td>18.4 GB/s (41 %)</td></tr>
</table></div>
<ul>
<li>The percentage in the last column is the share of the rate of one core alone.</li>
<li><b>Reads.</b> The second reader on the pair adds 86 to 87 % of the rate of one core alone. So two partner readers are not held to the rate of one reader. Two cores on different meshes (CPUs 0 and 64) together read 54.9 GB/s with the compiled loop [{PAIR}]. That is 2.3 GB/s (4 %) more than the partner pair. CPUs 0 and 64 share neither a pair port nor a mesh. No run has two cores of different pairs on one mesh at 1 GiB. So the cause of this difference was not measured. Whether the pair port limits DRAM reads was not measured.</li>
<li><b>Writes.</b> Two partner cores together write 63.2 GB/s with each loop. The second asm writer adds 0.2 GB/s (0.3 %). Four writers on two pairs (CPUs 0 to 3) write 113 GB/s. So a second pair adds 50 GB/s. So two partner writers share one limit of about 63 GB/s. What this limit is was not measured.</li>
<li><b>Hypotheses.</b> Hypothesis 2 of "Open items" says that the full pair port is this limit. Hypothesis 1 says that the port passes at most 64 GB/s in each direction. Neither is confirmed.</li>
<li><b>Withdrawn.</b> Earlier versions of this report said that DRAM latency limits each core first. No run tested it. That reason is withdrawn.</li>
</ul>
""")

# ---------------------------------------------------------------- line 437, open item on the replaced statements
L437 = J("""
<li><b>Three older statements were replaced on 2026-11-12.</b> The measured rates are now in the sections named below. The cause of each limit is still open.
<ul>
<li>"For DRAM streams the port is not the limit" and "For DRAM traffic the port is not the limit" rested on a read test. The new text is in section "The pair finding". At 1 GiB two partner writers share one limit of about 63 GB/s. What this limit is was not measured. Whether the pair port limits reads at 1 GiB was not measured. The earlier reason, that DRAM latency limits each core first, is withdrawn.</li>
<li>"For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2" stated more than the rates show. The new text is in section "Is the pair port how the SLC is reached?". Two partner readers together read 77.5 to 78.5 GB/s at 8 MiB. That rate also counts the lines that the two cores take from their own L2. That the full port is the limit is part of hypothesis 2.</li>
<li>"The single-writer limit is inside the core" is replaced in section "Where one writer's 73 GB/s limit sits (part 5, 2026-11-02)". What limits one writer at 8 MiB was not measured. At 1 GiB one writer alone already reaches the rate of the pair.</li>
<li>Still open: what limits a pair, and what limits one writer at 8 MiB. The tests are the missing tests of the item above and the per-core asm write sweep.</li>
</ul></li>
""")

if __name__ == "__main__":
    for name in ("L92", "L118", "L121", "L214", "L289", "L380", "L437"):
        print(name, len(globals()[name]), "chars")
