#!/usr/bin/env python3
"""Section 2.3 follow-ups asked by Jibin 2026-11-08: impact column, read/write in the group names, the L3 mode words."""
path = "/home/jhan/workspace/titan/cache-perf/asimov/gen_perf_core.py"
s = open(path).read()
def sub(old, new):
    global s
    assert s.count(old) == 1, ("sub", old[:70], s.count(old)); s = s.replace(old, new)

# group names: every latency row is a read (a chain of dependent loads); the placement rows are writes
for old, new in [
    ('("Chains 4 to 128 KiB (L1, L2)",', '("Chains 4 to 128 KiB (L1, L2): read",'),
    ('("Chains 192 to 384 KiB (the L3\'s sizes)",', '("Chains 192 to 384 KiB (the L3\'s sizes): read",'),
    ('("Fresh chains 512 KiB to 1 MiB",', '("Fresh chains 512 KiB to 1 MiB: read",'),
    ('("Fresh chains 1.5 to 4 MiB (the SLC)",', '("Fresh chains 1.5 to 4 MiB (the SLC): read",'),
    ('("Fresh chains 6 to 32 MiB (DRAM)",', '("Fresh chains 6 to 32 MiB (DRAM): read",'),
    ('("Flushed 8 MiB chain",', '("Flushed 8 MiB chain: read",'),
    ('("4 KiB controls, CPUs 2, 4, 6, 8",', '("4 KiB controls, CPUs 2, 4, 6, 8: read",'),
    ('("OCM, one line per page, per region, CPUs 2 to 8 (20 rows)",', '("OCM, one line per page, per region, CPUs 2 to 8: read (20 rows)",'),
    ('("OCM, one line per page, all five regions, CPUs 2 to 8",', '("OCM, one line per page, all five regions, CPUs 2 to 8: read",'),
    ('("OCM, every line, all five regions, CPUs 2 to 8",', '("OCM, every line, all five regions, CPUs 2 to 8: read",'),
    ('("2 MiB SLC chains, CPUs 4, 6, 8",', '("2 MiB SLC chains, CPUs 4, 6, 8: read",'),
    ('("Writer placement, six rows",', '("Writer placement, six rows: write",'),
    ('''ratio("Fresh chains 1.5 to 4 MiB (the SLC)") + ratio("Fresh chains 6 to 32 MiB (DRAM)")''', '''ratio("Fresh chains 1.5 to 4 MiB (the SLC): read") + ratio("Fresh chains 6 to 32 MiB (DRAM): read")'''),
]: sub(old, new)
# wider label column for the longer names
sub('unit="ratio", xlim=(0.5, 3.0), rh=19, L=400)', 'unit="ratio", xlim=(0.5, 3.0), rh=19, L=430)')
sub('''<li><b>What moved.</b> The figure puts every row of the two boots into {len(groups)} groups and shows each group's lowest and highest speed ratio. A dot at 1.0 is a row that repeated run 3.</li>''',
    '''<li><b>What moved.</b> The figure puts every row of the two boots into {len(groups)} groups and shows each group's lowest and highest speed ratio. A dot at 1.0 is a row that repeated run 3. Each group name ends with the kind of access: every latency row (the chains, the controls, the OCM and SLC chains) is a read, one dependent load at a time, and the bandwidth rows are read, write or copy streams; the writer-placement rows are writes.</li>''')

# the setup table: a fifth column, the impact rating
sub('''{table(["Item", "Run 3 (membench-jibin-004)", "Boot F1 (membench-jibin-011)", "Can it move a core row?"], [''',
    '''{table(["Item", "Run 3 (membench-jibin-004)", "Boot F1 (membench-jibin-011)", "Can it move a core row?", "Suspected impact"], [''')
for old, rating in [
    ('''which section 4.8 (boot A against run 3) bounds"],''', "low"),
    ('''the L3 mode is known from the SCP's staging lines alone"],''', "high"),
    ('''differs in the initial ramdisk's end address only)", "No"],''', "low"),
    ('''Boot E against boot C, one build, shows the read rise on its own"],''', "mid (the 16 KiB rows only)"),
    ('''run 3's 67 command lines in the same order", "No"],''', "low"),
    ('''"No (perf_cov 1.0000 on every row)"],''', "low"),
    ('''"OCM rows only, through page placement (this page's reading)"],''', "low"),
    ('''between passes of one row on run 3 and {max(sp_1) * 100:.0f} % on F1"],''', "mid (the OCM rows only)"),
    ('''with RT throttling (the kernel's cap on real-time CPU time) off"],''', "low"),
    ('''"No: they ran after phases A to E"],''', "low"),
]:
    assert old.endswith('"],'); sub(old, old[:-2] + f', "{rating}"],')
sub('''note="Columns 2 and 3 are quoted from Jesse's two README files (Core rows against round three; Platform facts). Column 4 is this page's reading. Not listed: the snapshot's build id and the OCM map lines, which touch no row.")}''',
    '''note="Columns 2 and 3 are quoted from Jesse's two README files (Core rows against round three; Platform facts). Columns 4 and 5 are this page's reading. Suspected impact: high = can explain the moves in the figure below on its own; mid = can move the named rows by a few percent; low = no row, by the evidence in column 4. Not listed: the snapshot's build id and the OCM map lines, which touch no row.")}''')

# the words of the SCP row and the register value, as their own bullet right after the table
sub('''<ul>
<li><b>How the commands ran.</b>''', '''<ul>
<li><b>Words in the SCP row.</b> Snoop filter: the DSU's record of which lines each core's L1 and L2 hold, used to answer the mesh's coherence requests without asking the cores. L3 lookup: on an L2 miss, the check whether the L3 RAM holds the line. L3 allocation: placing a line into the L3 RAM so that a later lookup can hit it. In snoop-filter-only mode the L3 RAM keeps only the snoop filter, there is no lookup and no allocation, and every L2 miss goes to the mesh. The three words are general cache terms, used for every vendor's caches; the mode names are the DSU's own. IMP_CLUSTERPWRSTAT_EL1: the DSU's cluster power status register (IMP: implementation defined, an Arm register that is not part of the architecture; EL1: readable from exception level 1 up). By the DSU RTL's field names, 0x70 is bits [7:6] = 01 (all slices on; this DSU has one L3 slice), bits [5:4] = 11 (the L3 RAM fully on) and bits [3:0] = 0 (no core asking for retention or power-down): the full L3 operating mode, with lookup and allocation open. The L3-off boots B, C and D read 0x0 (one slice, snoop filter only); run 3 did not read the register, so its mode rests on the SCP's staging lines. Arm's TRM was not consulted for the decode [Jesse's F1 README, The L3 and the prefetchers, lines 66 to 70].</li>
<li><b>How the commands ran.</b>''')
open(path, "w").write(s); print("patch_sec23b ok")
