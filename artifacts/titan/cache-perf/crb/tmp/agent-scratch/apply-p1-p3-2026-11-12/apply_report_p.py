#!/usr/bin/env python3
"""Second step of 2026-11-12, on the author's three requests:
  1. "flit" in "Words used here" (the entry existed; it now says what the word stands for)
  2. Spec box of the pair port: "estimated 64 GB/s", explained in the section
     "Where each number in the figure comes from"
  3. P1, P2 and P3 of record section 10.6 applied, with the places that change with them
     (rows F2, F3, F4, F5, F14, F15 (line 110), F16, F31, F32 and F33 of record section 6)
  4. the places that the sweep of this step found: sentences that still stated one of the
     replaced statements, or that the new texts contradict (each is marked "sweep" below)
Every edit stays on its physical line, so the report keeps 978 lines.
sub(): the old text must occur exactly once in its line.
whole(): the old line must start and end with the given texts.
Usage: apply_report_p.py <report.html> [--write]"""
import sys
import texts_p as T

P = sys.argv[1]
L = open(P, encoding="utf-8").read().split("\n")
assert len(L) == 979 and L[-1] == "", len(L)
n_edits = 0


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


def whole(n, start, end, new):
    global n_edits
    line = L[n - 1]
    assert line.startswith(start) and line.endswith(end), (n, line[:60], line[-40:])
    assert "\n" not in new
    L[n - 1] = new
    n_edits += 1


# ---- line 49, sub-header: name the changes of this step
sub(49, "and the write runs of the loop compiled from C.</div>",
    "and the write runs of the loop compiled from C. Changed later on 2026-11-12 after Jibin's review: "
    "the Spec box of the pair port now says \"estimated 64 GB/s\" (before: \"unknown\"), and the estimate is explained "
    "under the table \"Where each number in the figure comes from\". Three older statements were replaced by measured "
    "rates and named hypotheses: the pair port as a 78 GB/s limit, DRAM traffic on a pair, and the limit of one writer.</div>")

# ---- line 52, Short version (sweep): the old sentence gave about 80 GB/s as a property of a shared path
sub(52, "each pair of neighbouring cores shares one path to the mesh of about 80 GB/s, and the core's prefetcher",
    "with a buffer of 8 MiB each, the two cores of a pair (cores 2k and 2k+1) together read only about 78 GB/s, "
    "against 125 to 134 GB/s for two cores of different pairs, and the core's prefetcher")

# ---- first figure: label for screen readers, Spec box of the pair port, caption
sub(77, "Spec row: throughput calculated from the specification, for core and DRAM only.",
    "Spec row: throughput calculated from the specification for core and DRAM, and an estimate of 64 GB/s for the pair port.")
whole(92, '<g><rect x="504" y="156" width="76" height="48"', '>unknown</text></g>', T.L92)
sub(97, '"unknown" means that this row gives no number yet.',
    '"estimated 64 GB/s" at the pair port is a calculation that rests on a hypothesis. The hypothesis is not confirmed. '
    'The estimate counts only the bytes that cross the port in one direction. The measured ~80 GB/s above it counts every '
    'byte that two partner cores read, also the bytes from their own L2. "unknown" means that this row gives no number.')

# ---- section "Where each number in the figure comes from"
sub(101, "The Spec row holds derived numbers only.",
    "The Spec row holds derived numbers only. The 64 GB/s of the pair port is an estimate (est.). One of its three factors is a hypothesis.")
# rows F3 and F15 of the record: the rate of two cores of different pairs, and what the 78 GB/s counts
sub(110, 'Measured: two partner cores together read 78 GB/s from the SLC, two non-partners 134 GB/s; "~80" is 78 rounded.',
    'Measured: two partner cores together read 78 GB/s with a buffer of 8 MiB each (77.5 to 78.5 GB/s in five runs). '
    'Two cores of different pairs together read 125 to 134 GB/s. "~80" is 78 rounded. The 78 GB/s counts every byte that '
    'the loops read. One core alone takes 17 % of its lines from its own L2. No run counted this share with only two partner cores busy.')
sub(110, "The mechanism (two cores on one crosspoint port, Arm's CAL2) is from the CMN S3 manual and the map's port count.",
    "That two cores sit on one crosspoint port (Arm's CAL2) is inferred from the CMN S3 manual and the map's port count. It was not read from hardware. "
    "What limits the pair was not measured. That the full port is the limit is hypothesis 2 in \"Open items\".")
whole(118, "<tr><td>Spec row, pair port: unknown</td>", "</td></tr>", T.L118)
whole(121, "</table></div>", "</table></div>", T.L121)

# ---- section "Is the pair port how the SLC is reached?": row F3, then P2
# line 179: the section now names more than one claim that is not confirmed
sub(179, "Each answer is tied to an Arm document or to a measurement, and the one claim that neither confirms is marked.",
    "Each answer is tied to an Arm document or to a measurement. Each claim that neither confirms is marked as an inference or as a hypothesis.")
# line 206: the cell gave "one 78 GB/s limit" as a fact
sub(206, 'Latency fit, and the pair test (cores 2k and 2k+1 running together share one 78 GB/s limit, see "The pair finding"). Not read from hardware',
    'Latency fit, and the pair test (cores 2k and 2k+1 running together read 77.5 to 78.5 GB/s with a buffer of 8 MiB each, and two cores of different pairs '
    'read 125 to 134 GB/s, see "The pair finding"). The pair test fits two cores on one port. It does not show what limits the pair. Not read from hardware')
# line 213: what the buffers are, the rate of two cores of different pairs (row F3), and the rate of one core with an idle partner
sub(213, 'The measurement in "The pair finding" ran two cores at the same time, each streaming its own buffer from the SLC, and added their bandwidths.',
    'The measurement in "The pair finding" ran two cores at the same time. Each core read its own buffer of 8 MiB, which does not fit in its L2. The rates of the two cores were added.')
sub(213, "When the two busy cores come from different pairs (for example 0 and 2), the total is 134 GB/s, which is two times the single-core value.",
    "When the two busy cores come from different pairs, the total is 125 to 134 GB/s. That is 1.9 to 2.0 times the rate of one core alone. "
    "For example, CPUs 0 and 2 together read 126.6 GB/s with the read loop compiled from C and 129.7 GB/s with the asm loop. "
    "Only cores on different meshes (CPUs 0 and 64, CPUs 0 and 119) reached 134 GB/s.")
sub(213, "It depends on which cores are busy at the same time: a port serving one busy core and one idle core gives the busy core its full 67 GB/s.",
    "It depends on which cores are busy at the same time. A core with an idle partner reads the full 67 GB/s of one core alone.")
whole(214, '<p class="take"><b>For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2.</b>', "paired or not).</p>", T.L214)

# ---- section "Bandwidth per core", line 266 (sweep, row F14 of the record): the sentence put the limit outside the core
sub(266, "From the SLC and DRAM the two loops agree, so there the limit is outside the core.",
    "From the SLC the two read loops give almost the same rate (67.0 and 67.5 GB/s). This does not show a shared limit. "
    "The loop compiled from C reads 66.8 to 67.1 GB/s at 32 KiB, 1 MiB and 8 MiB alike. From DRAM the two read loops differ by 8 % "
    "(28.2 GB/s compiled from C, 30.5 GB/s asm). The write loops do not agree. The loop compiled from C writes 44.8 GB/s at 8 MiB and at 1 GiB. "
    "The asm loop writes 73.2 GB/s at 8 MiB and 63.0 GB/s at 1 GiB. These rates do not show where the limit of one core is.")

# ---- section "Where one writer's 73 GB/s limit sits": the table of part 5 (sweep, rows F16 and F31), then P3 (which holds row F32)
sub(275, "<td>every line leaves the core as a write; the 8 MiB bus count below 2 is unexplained</td>",
    "<td>At 1 GiB the core sends 2.00 bus writes per line. At 8 MiB it sends 1.52, for a reason that is not known</td>")
sub(276, "<td>2.8 GHz / 2.52 = 1.11 G lines/s = 71 GB/s; the stall counter does not see the wait</td>",
    "<td>2.8 GHz / 2.52 = 1.11 G lines/s = 71 GB/s. The stall counter shows 0.000 stall cycles per line</td>")
sub(278, "1.8 × 10<sup>9</sup> flits per second", "1.85 × 10<sup>9</sup> flits per second")
sub(278, "<td>no back-pressure at the first hop</td>", "<td>almost no back-pressure on these four links</td>")
whole(289, '<p class="take"><b>The single-writer limit is inside the core.</b>', "Not run.</p>", T.L289)

# ---- row F33, with the two rates and the section that holds them (sweep)
sub(343, 'one thread per pair, because two partner cores share one port and together get no more than one (section "The pair finding").',
    'one thread per pair. At 8 MiB two partner cores together read only 1.15 to 1.17 times as much as one core alone: '
    '77.5 to 78.5 GB/s against 66.9 to 67.5 GB/s (section "Is the pair port how the SLC is reached?").')

# ---- section "The pair finding": rows F3 and F2, the second sentence and the caption (sweep), then P1
sub(377, "get 134 GB/s together when they sit on any two cores from different pairs, and 78 GB/s when they share a pair.",
    "get 125 to 134 GB/s together when they sit on two cores from different pairs, and 78 GB/s when they share a pair.")
sub(377, "The same two cores with 1 MiB each (inside L2) get 134 GB/s, so the L2 is private and the shared part is the path to the mesh.",
    "CPUs 0 and 1, the two cores of one pair, get 134 GB/s together with 1 MiB each (inside L2). So the L2 is private, and what the two "
    "partner cores share lies beyond L2. What it is was not measured. Hypothesis 2 in \"Open items\" says that it is the full pair port.")
sub(379, "<figcaption>asm read, 2 threads, 8 MiB each, best of 2 reps. Pairs are CPUs (0,1), (2,3), (4,5); the others mix pairs.</figcaption>",
    "<figcaption>Read loop compiled from C, 2 threads, 8 MiB each, best of 2 reps. Pairs are CPUs (0,1), (2,3), (4,5). The others mix pairs. "
    "CPUs 64 and 119 are on mesh 1. All other CPUs of the chart are on mesh 0.</figcaption>")
whole(380, '<p class="take"><b>Placing one heavy thread per pair is worth 1.6 to 1.7 times the SLC bandwidth of a pair.</b>', "whether paired or not.</p>", T.L380)

# ---- "Open items"
sub(416, 'The Spec row of the hierarchy figure says "unknown" for both.',
    'The Spec row of the hierarchy figure says "estimated 64 GB/s" for the pair port and "unknown" for the SLC. The 64 GB/s is hypothesis 1 below. It is not confirmed.')
# line 425 (sweep): the new texts count five runs of two partner readers, and this item listed four
sub(425, "with the read loop compiled from C on three pairs of partner cores [pair.csv in the same folder].",
    "with the read loop compiled from C on three pairs of partner cores [pair.csv in the same folder]. The main sweep of the same day holds a fifth run. "
    "Two threads on CPUs 0 and 1 read 78.1 GB/s with the read loop compiled from C [results/20261030T193108Z/bandwidth.csv].")
sub(425, "would put all four measured rates below 64 GB/s on the port (est.).", "would put all five measured rates below 64 GB/s on the port (est.).")
whole(437, "<li><b>Older statements that the new rates put in doubt.</b>", "<li>These sections are unchanged for now.</li></ul></li>", T.L437)

# ---- "Words used here": what "flit" stands for
whole(451, "<dt>flit, data flit, data channel</dt>", "carries data flits.</dd>",
      '<dt>flit, data flit, data channel</dt><dd>"Flit" is short for "flow control unit". It is a known term of link protocols. '
      'Arm\'s CHI specification defines it: "FLow control unIT (Flit) is the smallest flow control unit" [AMBA CHI specification, '
      'IHI 0050 issue H, page 32]. CHI (Coherent Hub Interface) is the protocol of the mesh ports and links. In this report a flit is '
      'one transfer unit on a mesh link or port. A data flit carries data and holds 32 B [CMN S3 TRM, Table A-2 page 2120]. '
      'A 64 B line needs two data flits. A data channel is the part of a link or port that carries data flits.</dd>'
      # the applied texts use these terms, and the list did not hold them
      '<dt>credit stall, data stall, back-pressure</dt><dd>A sender on a mesh link needs one credit from the receiver for each flit '
      '[AMBA CHI specification, IHI 0050 issue H, page 518]. A credit-stall cycle is one count of the link event "TX flit stall". '
      'Arm describes it as "signaled when flit transmission is stalled and waiting on credits" [CMN S3 TRM, page 1679]. '
      'A data stall is one count of a home-node event. Arm describes it as "Counts number of times HN-F has a pending TXDAT flit but no credits to upload" '
      "[CMN S3 TRM, page 391]. Back-pressure is this report's word for such waits.</dd>"
      '<dt>write in flight</dt><dd>A write that the core has sent and that is not yet complete.</dd>')

# ---- "Words used here" (sweep): the applied texts say "partner cores", and the entry called the shared path "Measured"
sub(462, "<dt>pair port</dt><dd>Cores 2k and 2k+1 share one path to the mesh. Measured, not read from documentation.</dd>",
    "<dt>pair port, partner cores</dt><dd>The crosspoint port that cores 2k and 2k+1 share. The two cores of one pair are called partner cores, or partners. "
    "The sharing follows from two timing tests (the latency fit and the pair test) and from the port count of the mesh map. "
    "It was not read from hardware or from documentation. What limits the rate of a pair was not measured (see \"Open items\").</dd>")

# ---- pair chart (sweep): the text gives 125 to 134 GB/s, and the chart drew seven of the nine runs of pair.csv at 8 MiB
sub(587, "['CPUs 0,2', 126.6, false], ['CPUs 1,2', 132.0, false], ['CPUs 0,64', 134.1, false]",
    "['CPUs 0,2', 126.6, false], ['CPUs 0,3', 124.8, false], ['CPUs 1,2', 132.0, false], ['CPUs 4,6', 132.4, false], ['CPUs 0,64', 134.1, false]")

assert len(L) == 979 and L[-1] == "", len(L)
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, {len(L) - 1} lines")
