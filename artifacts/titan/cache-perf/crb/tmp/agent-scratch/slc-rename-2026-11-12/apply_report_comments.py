#!/usr/bin/env python3
"""The author's comments of 2026-11-12 on crb-memory-hierarchy.html:
1. source table: "The cycle number is derived: ns x 2.8 GHz." -> "Cycles derived."
2. source table: row label "30 ns (85 cycles)" -> "SLC latency avg: 30 ns (85 cycles)"
3. source table: row label ">=0.62 TB/s whole chip" -> "SLC throughput >=0.62 TB/s whole chip"
4. every "3 loads + 2 stores" -> "3 loads / 2 stores"
5. the passage on the read loop compiled from C (lines 131 to 133): better format, with the C code.

No line is added or removed. A code listing keeps its line breaks as the character reference &#10;
so that the three source lines 131 to 133 stay three lines.
The listings are read from the source files by this script, so they are verbatim.
Usage: apply_report_comments.py <report.html> [--write]"""
import html
import sys

P = sys.argv[1]
BENCH = "/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c"
PROBE = "/home/jhan/workspace/titan/cache-perf/crb/results/probe-20261111T210017Z.txt"
L = open(P, encoding="utf-8").read().split("\n")
N0 = len(L)
n_edits = 0


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


def whole(n, prefix, new):
    global n_edits
    assert L[n - 1].startswith(prefix), (n, L[n - 1][:80])
    assert "\n" not in new
    L[n - 1] = new
    n_edits += 1


def listing(lines):
    """A <pre> block on one source line: escaped text, line breaks as &#10;."""
    return "<pre><code>" + "&#10;".join(html.escape(x, quote=False) for x in lines) + "</code></pre>"


src = open(BENCH, encoding="utf-8").read().split("\n")
k_read = src[138 - 1:148]
k_asmread = src[173 - 1:195]
assert k_read[0].startswith("__attribute__((noinline)) static uint64_t k_read(") and k_read[-1] == "}", k_read
assert k_asmread[0].startswith("__attribute__((noinline)) static void k_asmread(") and k_asmread[-1] == "}", k_asmread
assert all("\t" not in x for x in k_read + k_asmread)

probe = open(PROBE, encoding="utf-8").read().split("\n")
loop = probe[44 - 1:59]          # addresses 1b68 to 1ba4, the loop of k_read
assert len(loop) == 16 and loop[0].strip().startswith("1b68:") and loop[-1].strip().startswith("1ba4:"), loop
mc = []
for x in loop:
    f = x.strip().split("\t")    # address, mnemonic, operands
    assert len(f) == 3, f
    mc.append(f"{f[0]:<7}{f[1]:<6}{f[2]}".rstrip())

# ---- 0. style for the listings (appended to the line of the rule for "code")
sub(35, "code, .mono { font-family: var(--mono); font-size: 0.92em; }",
    "code, .mono { font-family: var(--mono); font-size: 0.92em; } pre { font-family: var(--mono); font-size: 13px; line-height: 1.45; background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; padding: 10px 14px; margin: 8px 0; overflow-x: auto; } pre code { font-size: inherit; }")

# ---- 1 to 3. source table
sub(107, "Measured (pointer chase; asm read loop, one thread). The cycle number is derived: ns × 2.8 GHz.</td>",
    "Measured (pointer chase; asm read loop, one thread). Cycles derived.</td>")
sub(112, "<tr><td>30 ns (85 cycles)</td>", "<tr><td>SLC latency avg: 30 ns (85 cycles)</td>")
sub(113, "<tr><td>≥0.62 TB/s whole chip</td>", "<tr><td>SLC throughput ≥0.62 TB/s whole chip</td>")

# ---- 4. the label
sub(58, ">What \"3 loads + 2 stores of 16 B per cycle\" means</a></li>",
    ">What \"3 loads / 2 stores of 16 B per cycle\" means</a><ol><li><a href=\"#the-read-loop-compiled-from-c\">The read loop compiled from C: 1.5 loads per cycle</a></li></ol></li>")
sub(82, ">3 loads + 2 stores</text>", ">3 loads / 2 stores</text>")
sub(105, "<tr><td>3 loads + 2 stores of 16 B per cycle</td>", "<tr><td>3 loads / 2 stores of 16 B per cycle</td>")
sub(116, "(row \"3 loads + 2 stores of 16 B per cycle\" above)", "(row \"3 loads / 2 stores of 16 B per cycle\" above)")
sub(122, ">What \"3 loads + 2 stores of 16 B per cycle\" means</h2>", ">What \"3 loads / 2 stores of 16 B per cycle\" means</h2>")
sub(124, "So the label \"3 loads + 2 stores\" gives two separate limits.", "So the label \"3 loads / 2 stores\" gives two separate limits.")

# ---- 5. the passage on the read loop compiled from C
l131 = "".join([
    "<h3 id=\"the-read-loop-compiled-from-c\">The read loop compiled from C: 1.5 loads per cycle</h3>",
    "<p><b>The read loop compiled from C reaches 66.8 GB/s, which is 1.5 loads of 16 B per cycle.</b> The asm read loop measured 132.7 GB/s, which is 99 % of 3 loads per cycle. The limit of two vector adds per cycle can explain at most part of this gap. The cause of the rest is not established. This section gives the source code, the machine code, the limits that were checked, and the test that is missing.</p>",
    "<p><b>Source code.</b> This loop is the C function <code>k_read</code> in <code>bench/bandwidth.c</code> [lines 138 to 148]. It adds every 8 B word of the buffer into one of 16 running sums, and gcc 14.2 chooses the instructions.</p>",
    listing(k_read),
    "<p>The asm loop is written by hand and only loads. It is the function <code>k_asmread</code> in the same file [lines 173 to 195]. One pass of its loop runs 8 LDP q instructions (16 loads of 16 B, which is 256 B), one add, one compare and one branch.</p>",
    listing(k_asmread),
    "<p><b>Machine code.</b> The machine code of <code>k_read</code> on CRB was read with <code>objdump -d</code> on 2026-11-11, with no test run [results/probe-20261111T210017Z.txt]. For each 128 B the loop runs these 16 instructions:</p>",
    listing(mc),
    "<ul><li>4 LDP q (8 loads of 16 B)</li><li>8 vector adds</li><li>2 integer adds</li><li>one compare and one branch</li></ul>",
    "<p>So the compiled loop does issue one vector add per 16 B load.</p>",
    "<p><b>Which build was read.</b></p>",
    "<ul><li>The binary that was read is the build of 2026-11-02 from the current source file.</li>",
    "<li>The 66.8 GB/s was measured on 2026-10-30 with an earlier build, and no copy of that binary was kept.</li>",
    "<li>A copy of the source file of 2026-10-30 holds the same <code>k_read</code>, and the same write and copy functions (<code>k_write</code> and <code>k_copy</code>) [~/workspace/titan/exec/scratch-relocated/ed41c79f/bandwidth.c.orig].</li>",
    "<li>The compiler package on CRB was the same on 2026-10-30 and on 2026-11-11 [results/20261030T193108Z/sysinfo.txt; results/probe-20261111T210017Z.txt]. The build of 2026-11-02 lies between these two days.</li>",
    "<li>So the three loops compiled from C were very probably the same.</li></ul>",
])
whole(131, "<p>The read loop compiled from C reaches 66.8 GB/s, which is 1.5 loads of 16 B per cycle. This loop is the C function", l131)

l132 = "".join([
    "<p><b>The limits that were checked.</b> The limit of two vector adds per cycle can explain at most part of the gap between 66.8 GB/s and the 134.4 GB/s of the load pipelines. The core has two vector pipelines (FP/ASIMD 0 and 1), and Arm's table gives 2 vector adds per cycle [SOG, Table 2-1 page 13 and Table 3-15 page 26]. Two adds per cycle allow 2 loads per cycle, which is 89.6 GB/s. The measured 66.8 GB/s is 25 % below that.</p>",
    "<p>Arm's guide also limits how many operations the core dispatches in one cycle [SOG, section 4.1 \"Dispatch constraints\", page 55]. Dispatch is the step before the pipelines. A dispatched operation waits for its inputs and then goes to a pipeline [SOG, section 2.1 page 11]. So a dispatch limit can be higher than the number of operations that the pipelines accept in one cycle. This report calls these limits dispatch limits. The section lists eight of them. The table below compares each limit with the average rate of the loop.</p>",
    "<p>How the loop is counted:</p>",
    "<ul><li>The dispatch step handles at most 10 instructions per cycle. The guide counts instructions after decoding and calls them MOPs (macro-operations).</li>",
    "<li>The guide calls operations µOPs (micro-operations). It gives no count for LDP q. This report counts one LDP q as two operations, one for each 16 B load (est.).</li>",
    "<li>One pass of the loop (128 B) has about 20 operations: 8 loads, 8 vector adds, 2 integer adds, one compare and one branch. At most 4 of the 20 operations are integer or branch operations.</li>",
    "<li>One pass takes 5.37 cycles at 32 KiB (see \"Observation\" below).</li></ul>",
    "<div class=\"tw\"><table>",
    "<tr><th>Limit in Arm's guide</th><th>Allowed per cycle</th><th>This loop, average per cycle</th></tr>",
    "<tr><td>Loads of 16 B on the three load pipelines</td><td>3</td><td>1.5</td></tr>",
    "<tr><td>Vector adds on the two vector pipelines</td><td>2</td><td>1.5</td></tr>",
    "<tr><td>Dispatch: instructions (MOPs)</td><td>10</td><td>3.0</td></tr>",
    "<tr><td>Dispatch: operations for the load pipelines</td><td>6</td><td>1.5 loads of 16 B</td></tr>",
    "<tr><td>Dispatch: operations for FP/ASIMD 0, and for FP/ASIMD 1 (2 limits)</td><td>2 and 2</td><td>1.5 vector adds on both together</td></tr>",
    "<tr><td>Dispatch: operations in total</td><td>20</td><td>3.7 (est.)</td></tr>",
    "<tr><td>Dispatch: three groups of integer and branch pipelines (3 limits)</td><td>4, 4 and 2</td><td>at most 0.75 in total (est.)</td></tr>",
    "</table></div>",
    "<p>So the loop stays below every limit that was checked: 3 loads per cycle, 2 vector adds per cycle, and the eight dispatch limits. For the last two rows of the table this holds on average (est.). The check compares average rates only. It covers only these limits. It does not exclude any other limit, whether the guide lists it or not. The cause of the remaining gap is not established.</p>",
])
whole(132, "<p>The limit of two vector adds per cycle can explain at most part of the gap", l132)

l133 = "".join([
    "<p><b>Observation.</b> One pass of the loop (128 B, 8 loads and 8 adds) takes 5.37 cycles at 32 KiB and 5.34 cycles at 1 MiB. Each load and each add writes one vector register. So the loop writes 2.98 to 3.00 vector registers per cycle, half of them by loads and half by adds.</p>",
    "<p>Two readings fit this number.</p>",
    "<ul><li>Hypothesis A: loads and adds that write vector registers share a limit of 3 per cycle.</li>",
    "<li>Hypothesis B: the adds reach only 1.5 per cycle for a reason that is not known, and the loads follow the adds.</li></ul>",
    "<p>The loop also runs 3 instructions per cycle. A general limit of 3 instructions per cycle does not fit. The write and copy loops compiled from C have 4 and 5 instructions per pass, and they run about 4 and about 5 instructions per cycle at 32 KiB and 1 MiB [results/probe-20261111T210017Z.txt; results/20261030T193108Z/bandwidth.csv].</p>",
    "<p><b>The test that is missing.</b> The test that separates A and B is a loop with loads and adds in a 3:2 ratio. Not run.</p>",
    "<div class=\"tw\"><table>",
    "<tr><th>Result of the 3:2 loop</th><th>Meaning</th></tr>",
    "<tr><td>80.6 GB/s</td><td>Hypothesis A predicts it</td></tr>",
    "<tr><td>100.8 GB/s</td><td>Hypothesis B predicts it</td></tr>",
    "<tr><td>134.4 GB/s, the limit of the load pipelines</td><td>It would reject both</td></tr>",
    "</table></div>",
])
whole(133, "<p>Observation: one pass of the loop (128 B, 8 loads and 8 adds) takes 5.37 cycles", l133)

assert len(L) == N0
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, lines 131/132/133 now {len(L[130])}/{len(L[131])}/{len(L[132])} chars")
