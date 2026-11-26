#!/usr/bin/env python3
"""Builds the easy-read page of the whole-chip read drop report.
All numbers are copied from FINDINGS.md (the facts sheet) in this folder."""
import math, html

OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop-easy-read.html"
R = "/home/jhan/workspace/titan/cache-perf/crb/results"
W = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15"

BLUE, ORANGE, GREY, INK, MUTED, GRID = "#1f6fc9", "#c2500a", "#6b6a66", "#0b0b0b", "#52514e", "#e4e3df"

# ---------------------------------------------------------------- figure 1
# Original run, 120 threads, benchmark bandwidth.c, whole-pass stop, 0.5 s, n = 6 per loop.
F1 = [  # label, lo, hi, median or None, colour
    ("Read, old loop", 464.4, 466.7, None, GREY),
    ("Read, new loop", 279.7, 304.1, None, BLUE),
    ("Write, old loop", 140.9, 186.9, 144.6, GREY),
    ("Write, new loop", 123.5, 147.8, 131.9, BLUE),
    ("Copy, old loop", 155.0, 158.6, None, GREY),
    ("Copy, new loop", 153.9, 162.4, None, BLUE),
]


def fig1():
    w, h = 920, 318
    x0, x1 = 150, 700
    sx = lambda v: x0 + (x1 - x0) * v / 500.0
    o = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Range of the 120-thread total for the old and the new loop: read, write and copy">']
    for t in range(0, 501, 100):
        o.append(f'<line x1="{sx(t):.1f}" y1="28" x2="{sx(t):.1f}" y2="268" stroke="{GRID}"/>')
        o.append(f'<text x="{sx(t):.1f}" y="286" font-size="12.5" fill="{MUTED}" text-anchor="middle">{t}</text>')
    o.append(f'<text x="{(x0+x1)/2:.1f}" y="308" font-size="13" fill="{MUTED}" text-anchor="middle">Total of 120 threads, GB/s (the bar spans the lowest and the highest of 6 intervals)</text>')
    notes = ["Looks like a large drop", "Looks like a drop", "No drop"]
    for i, (lab, lo, hi, med, col) in enumerate(F1):
        y = 48 + i * 36 + (i // 2) * 14
        o.append(f'<text x="{x0-10}" y="{y+4.5}" font-size="13.5" fill="{INK}" text-anchor="end">{lab}</text>')
        o.append(f'<line x1="{sx(0):.1f}" y1="{y}" x2="{sx(lo):.1f}" y2="{y}" stroke="{col}" stroke-width="2" opacity="0.35"/>')
        o.append(f'<rect x="{sx(lo):.1f}" y="{y-8}" width="{max(sx(hi)-sx(lo),4):.1f}" height="16" rx="3" fill="{col}"/>')
        txt = f"{lo} to {hi}"
        if med is not None:
            o.append(f'<line x1="{sx(med):.1f}" y1="{y-11}" x2="{sx(med):.1f}" y2="{y+11}" stroke="{INK}" stroke-width="2"/>')
            txt += f" (median {med})"
        o.append(f'<text x="{sx(hi)+8:.1f}" y="{y+4.5}" font-size="13" fill="{INK}">{txt}</text>')
        if i % 2 == 1:
            o.append(f'<text x="{w-12}" y="{y-13.5}" font-size="13.5" font-weight="600" fill="{INK}" text-anchor="end">{notes[i//2]}</text>')
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- figure 2
# name, window lo, window hi (lines), total min, total max (GB/s), state
P = [
    ("read_1pl", 156, 164, 230.2, 235.0, "slow"),
    ("read_sparse", 38, 42, 294.6, 301.5, "slow"),
    ("asmread", 36, 40, 288.5, 309.8, "slow"),
    ("read_pf2048", 36, 40, 290.5, 306.8, "slow"),
    ("read_nop32", 36, 40, 284.8, 302.7, "slow"),
    ("read_nop48", 32, 36, 305.4, 307.2, "slow"),
    ("read_dadd2", 32, 36, 290.1, 296.4, "slow"),
    ("read_sp24", 32, 34, 280.9, 283.2, "slow"),
    ("read_nop56", 28, 32, 308.6, 309.1, "slow"),
    ("read_dadd4", 28, 32, 280.1, 283.2, "slow"),
    ("read_nop64", 28, 32, 325.5, 333.9, "between"),
    ("read_sp32", 26, 30, 366.3, 366.6, "between"),
    ("read_nop72", 24, 28, 459.0, 459.3, "fast"),
    ("read_dadd8", 24, 28, 462.4, 462.6, "fast"),
    ("read_1pl_nop96", 24, 28, 460.8, 460.9, "fast"),
    ("read_nop80", 24, 28, 459.7, 459.8, "fast"),
    ("read_sp40", 22, 24, 466.8, 466.9, "fast"),
    ("read_nop88", 20, 24, 462.8, 462.9, "fast"),
    ("read_nop96", 20, 24, 465.5, 470.6, "fast"),
    ("read_sp48", 20, 22, 470.0, 470.1, "fast"),
    ("oldread", 18, 22, 465.5, 470.1, "fast"),
    ("read_sp56", 18, 20, 473.6, 473.7, "fast"),
    ("read_dadd16", 16, 20, 466.7, 469.8, "fast"),
    ("read_iadd16", 16, 20, 469.2, 469.7, "fast"),
    ("read_nop112", 16, 20, 471.1, 471.2, "fast"),
    ("read_nop128", 16, 20, 473.8, 476.4, "fast"),
    ("read_nop160", 12, 16, 477.9, 478.2, "fast"),
    ("read_nop192", 12, 16, 479.6, 479.8, "fast"),
    ("read_nop256", 8, 12, 543.9, 549.0, "fast"),
]
assert len(P) == 29
NSLOW = sum(1 for p in P if p[5] == "slow")
NBETW = sum(1 for p in P if p[5] == "between")
NFAST = sum(1 for p in P if p[5] == "fast" and p[0] != "read_nop256")
COL = {"slow": ORANGE, "between": GREY, "fast": BLUE}


def fig2():
    w, h = 920, 470
    x0, x1, yt, yb = 70, 896, 26, 400
    lx = lambda v: x0 + (x1 - x0) * (math.log(v) - math.log(7)) / (math.log(200) - math.log(7))
    sy = lambda v: yb - (yb - yt) * v / 600.0
    o = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Total read rate of 120 threads against the window depth of the loop, 29 loop variants">']
    # band where the total falls
    o.append(f'<rect x="{lx(28):.1f}" y="{yt}" width="{lx(32)-lx(28):.1f}" height="{yb-yt}" fill="#f3e9c9"/>')
    for t in range(0, 601, 100):
        o.append(f'<line x1="{x0}" y1="{sy(t):.1f}" x2="{x1}" y2="{sy(t):.1f}" stroke="{GRID}"/>')
        o.append(f'<text x="{x0-8}" y="{sy(t)+4:.1f}" font-size="12.5" fill="{MUTED}" text-anchor="end">{t}</text>')
    for t in (8, 10, 12, 16, 20, 24, 28, 32, 40, 60, 80, 120, 160):
        o.append(f'<line x1="{lx(t):.1f}" y1="{yb}" x2="{lx(t):.1f}" y2="{yb+5}" stroke="{MUTED}"/>')
        o.append(f'<text x="{lx(t):.1f}" y="{yb+19}" font-size="12.5" fill="{MUTED}" text-anchor="middle">{t}</text>')
    o.append(f'<line x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}" stroke="{MUTED}"/>')
    o.append(f'<text x="{(x0+x1)/2:.1f}" y="{yb+42}" font-size="13" fill="{MUTED}" text-anchor="middle">Window depth of the loop, cache lines (measured range, one thread). The axis is logarithmic.</text>')
    o.append(f'<text transform="translate(18,{(yt+yb)/2:.1f}) rotate(-90)" font-size="13" fill="{MUTED}" text-anchor="middle">Total of 120 threads, GB/s</text>')
    for name, lo, hi, a, b, st in P:
        y = sy((a + b) / 2)
        c = COL[st]
        o.append(f'<line x1="{lx(lo):.1f}" y1="{y:.1f}" x2="{lx(hi):.1f}" y2="{y:.1f}" stroke="{c}" stroke-width="2.2" opacity="0.55"/>')
        key = name in ("oldread", "asmread")
        o.append(f'<circle cx="{lx(math.sqrt(lo*hi)):.1f}" cy="{y:.1f}" r="{6.5 if key else 4.2}" fill="{c}" stroke="{INK if key else "#fcfcfb"}" stroke-width="{2 if key else 1}"/>')

    def lab(x, y, lines, anchor="start", bold=True):
        for i, t in enumerate(lines):
            fw = ' font-weight="600"' if bold and i == 0 else ""
            o.append(f'<text x="{x:.1f}" y="{y+i*17:.1f}" font-size="13.5" fill="{INK}" text-anchor="{anchor}"{fw}>{html.escape(t)}</text>')

    def lead(xa, ya, xb, yb_):
        o.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb_:.1f}" stroke="{INK}" stroke-width="1"/>')

    # old loop
    xo, yo = lx(math.sqrt(18 * 22)), sy(467.8)
    lead(xo - 5, yo + 6, lx(8.2) + 96, sy(400) - 14)
    lab(lx(8.2), sy(400), ["Old read loop", "18 to 22 lines", "465.5 to 470.1 GB/s"])
    # new loop
    xn, yn = lx(math.sqrt(36 * 40)), sy(299.15)
    lead(xn + 5, yn + 6, xn + 44, sy(215) - 14)
    lab(xn + 30, sy(215), ["New load-only loop", "36 to 40 lines", "288.5 to 309.8 GB/s", "about 36 % below the old loop"])
    # 256 nop
    lab(lx(12) + 10, sy(546.45) + 4.5, ["Load-only loop + 256 nop: 8 to 12 lines, 543.9 to 549.0 GB/s"])
    # one load per line
    lab(lx(156) - 8, sy(232.6) - 34, ["One load per line", "156 to 164 lines", "230.2 to 235.0 GB/s"], "end")
    # groups
    lab(lx(32) + 12, sy(470) + 4.5, [f"Fast: {NFAST} loops, 459 to 480 GB/s"], "start", False)
    lab(lx(60), sy(345), [f"Slow: {NSLOW} loops, 230 to 310 GB/s"], "start", False)
    lead(lx(32), sy(110) - 4, lx(32) + 14, sy(110) - 4)
    lab(lx(32) + 18, sy(110), ["The total falls here:", "at about 30 lines"])
    lab(lx(24.5), sy(366.45) + 4.5, [f"Between: {NBETW} loops"], "end", False)
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- text
REFS = [
    f"Facts sheet with every number of this page: {W}/FINDINGS.md",
    "Full report: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop.html",
    f"Original run: {R}/kernels-20261113T181222Z/threads120.csv (benchmark bandwidth.c)",
    f"Copy and write runs with a common stop: {R}/w120-R1-20261115T185140Z/ (files p4copy.csv, p3write.csv)",
    f"Write under two stop rules at two interval lengths (earlier runs with 64 processes): {R}/B10a-* and {R}/B10b-*",
    f"Read runs at 64+56: {R}/w120-R0-20261115T165608Z/, w120-R0b-20261115T170342Z/, w120-R1-20261115T185140Z/, w120-R5-20261115T203152Z/, w120-R6-20261115T203438Z/",
    f"Window test: {W}/robsize/ (program robsize.c, results in results/rob-k1-*.csv, rob-k2-*.csv, rob-k3-*.csv)",
    f"Thread layouts: {R}/w120-R0b-20261115T170342Z/ and {R}/w120-R1-20261115T185140Z/p5r5656.csv",
    f"Different loops on the two meshes: {R}/w120-R3-20261115T193922Z/",
    f"Latency probe: {R}/w120-R4-20261115T200016Z/",
    f"Mesh counters: {R}/w120-RC1-20261115T190208Z/. Memory-port counters: {R}/w120-RC2-20261115T192222Z/",
    f"Scrambled-order run: {R}/w120-R7-20261115T205946Z/",
    f"Test programs: {W}/../bwx12-2026-11-15/bwx12.c and {W}/../bwx13-2026-11-15/bwx13.c",
    f"Load and login records of all runs: {R}/w120-*/env.txt and launches.txt",
    f"Generator of this page: {W}/easy_read.py",
]


def ref(*n):
    return '<span class="ref">' + "".join(f"[Ref{i}]" for i in n) + "</span>"


WORDS = [
    ("CRB", "The Arm server under test. It has 128 cores of type Neoverse V3AE. The tests use CPUs 0 to 119."),
    ("loop", "One timed loop of the benchmark. The benchmark calls it a kernel. It is not the Linux kernel."),
    ("old read loop", "The read loop of the old benchmark. Per 128 B it holds 4 load instructions and 8 vector adds."),
    ("new read loop, load-only loop", "The read loop of the new benchmark. Per 256 B it holds 8 load instructions and nothing else. A C version and an assembly version exist. This page shows the assembly version where both were measured."),
    ("nop", "An instruction that does nothing. It still uses one place in the window."),
    ("padded loop", "The load-only loop with nop instructions added."),
    ("filler", "Extra instructions in a loop that are not needed to read the data: nop or adds."),
    ("line", "One cache line. It is 64 B."),
    ("address order", "The loop reads its buffer from the lowest address to the highest, one block after the next."),
    ("scrambled order", "The loop reads the same bytes, but it jumps between the 256 B blocks."),
    ("slow state, fast state", "Slow state: the 120 threads at 64+56 run the new read loop (about 300 GB/s). Fast state: the same threads run the old loop or a padded loop (459 GB/s or more)."),
    ("window", "The instructions that a core holds between fetch and retirement. The core can start the loads of all instructions in the window before the first one finishes."),
    ("window depth", "The number of 64 B lines that the loads inside one full window touch. It was measured for each loop with one thread. The result is a range, for example 36 to 40 lines."),
    ("mesh 0, mesh 1", "The chip has two meshes (grids of links that connect cores, cache and memory ports). CPUs 0 to 63 are on mesh 0. CPUs 64 to 119 are on mesh 1."),
    ("64+56", "64 threads on mesh 0 and 56 threads on mesh 1. Each thread reads its own 256 MiB buffer. Other layouts use the same form, for example 64+0."),
    ("DRAM", "The main memory of the machine. A 256 MiB buffer does not fit in the caches, so the data comes from DRAM."),
    ("total", "The sum of the rates of all threads, in GB/s. 1 GB is 1e9 bytes."),
    ("whole-pass stop", "The stop rule of the benchmark. A thread stops only at the end of a whole pass over its buffer. The threads stop at different times."),
    ("common stop", "All threads stop at the same time."),
    ("lines in flight", "The lines that one core has requested from memory and has not yet received."),
    ("prefetcher", "The part of a core that requests data before the loop asks for it."),
    ("n", "The number of timed intervals behind a value."),
    ("est.", "Estimate. The value is computed with an assumption. It is not measured directly."),
]

FLOW = [
    ("1", "Did all three drop?", "Only read", "held"),
    ("2", "What in the loop decides it?", "Enough filler of any kind. The adds are not needed.", "held"),
    ("3", "Why does filler help?", "It makes the window cover fewer lines", "held"),
    ("4", "Same in other thread layouts?", "Yes. The drop appears only with many threads on both meshes.", "held"),
    ("5", "Do deep-window cores take from the others?", "Yes", "held"),
    ("6", "Is the chip congested when slow?", "No", "rej"),
    ("7", "Is the deep window alone enough?", "No. It also needs address order.", "held"),
]


def step(num, title, tag, tagtxt, q, idea, test, result):
    def ul(items):
        return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"
    return f"""<section class="step" id="s{num}">
<h3><span class="num">{num}</span>{title}<span class="tag {tag}">{tagtxt}</span></h3>
<div class="qitr">
<div class="k">Question</div><div class="v">{ul(q)}</div>
<div class="k">Idea</div><div class="v">{ul(idea)}</div>
<div class="k">Test</div><div class="v">{ul(test)}</div>
<div class="k res">Result</div><div class="v res">{ul(result)}</div>
</div></section>"""


STEPS = [
    step(1, "Did read, write and copy all drop?", "held", "Idea held",
         ["Read and write looked lower. Copy did not. Is each of these three results real?"],
         ["The benchmark uses the whole-pass stop.",
          "With this rule the threads stop at different times.",
          "This can move a total without any change in the chip."],
         ["Run old and new loops with a common stop at 64+56 " + ref(4) + ".",
          "Compare write under two stop rules (whole-pass stop, common stop), each with intervals of 0.5 s and 15 s. These are earlier runs with 64 processes. Each case has 64 intervals " + ref(5) + "."],
         ["Copy: 152.4 to 153.6 GB/s for all loops. No drop.",
          "Write, earlier runs, whole-pass stop at 0.5 s: old is 21.5 % above new (medians 144.1 and 118.6 GB/s).",
          "Write, earlier runs, common stop: old is 3.7 % above new at 0.5 s (medians 126.4 and 122.0 GB/s) and 3.1 % above new at 15 s (126.6 and 122.8 GB/s). The percentages are copied from the facts sheet.",
          "Write at 64+56 with a common stop: old 126.1 to 126.8 GB/s, new 121.3 to 129.3 GB/s (2 intervals per loop) " + ref(4) + ".",
          "Read: 465.5 to 470.1 GB/s (old) against 288.5 to 309.8 GB/s (new). This drop stays " + ref(6) + ".",
          "<b>So only read dropped by a large amount. Copy did not drop. Write keeps a small difference of 3 to 4 %.</b>"]),
    step(2, "What in the loop decides fast or slow?", "held", "Idea A rejected, idea B held",
         ["The old loop has 8 vector adds per 128 B. The new loop has none. Do the adds matter?"],
         ["Idea A: the adds must wait for the loaded data, and this slows the loads down in a useful way.",
          "Idea B: enough extra instructions of any kind help, also instructions that do nothing."],
         ["Build 26 new loop variants in a copy of the test program " + ref(13) + ".",
          "Add vector adds that use the loaded data. Add vector adds that do not use it. Add nop instructions.",
          "Measure each variant at 64+56 " + ref(6) + "."],
         ["16 adds per 256 B that use the data: 466.7 to 469.8 GB/s.",
          "16 adds per 256 B that do not use the data: 469.2 to 469.7 GB/s. This is the same.",
          "72 to 192 nop per 256 B: 459 to 480 GB/s. 256 nop per 256 B: 543.9 to 549.0 GB/s.",
          "32 to 56 nop per 256 B: 284.8 to 309.1 GB/s. This is too little filler.",
          "Software prefetch instructions: 289 to 316 GB/s. They do not help.",
          "<b>Idea A is rejected. Idea B held: the kind of filler does not matter, the amount does.</b>"]),
    step(3, "Why does filler help?", "held", "Idea held",
         ["What does a nop change, when it does no work?"],
         ["The window of a core holds a fixed number of instructions.",
          "Filler takes places in the window. Then fewer loads fit in the window.",
          "So the window covers fewer lines."],
         ["Measure the window with one thread " + ref(7) + ".",
          "Measure, for each loop, how many lines one full window covers."],
         ["The window holds 684 nop, or 159 instructions that write a vector register.",
          "Old loop: 18 to 22 lines. New loop: 36 to 40 lines.",
          "All loops with a range at or above 32 to 34 lines are slow. All loops with a range at or below 24 to 28 lines are fast.",
          "Four loops lie between these (26 to 32 lines). Two are slow and two are in between (325.5 to 366.6 GB/s).",
          "The adds of the old loop use up the vector-register places of the window (159 places). The old loop is fast for this reason, not because the adds wait for data.",
          "<b>This is the chart of section 2.</b>"]),
    step(4, "Is it the same in other thread layouts?", "held", "Idea held",
         ["Does a padded loop behave like the old loop everywhere?"],
         ["If the window depth is the cause, a padded loop with a similar depth follows the old loop in every layout."],
         ["Run the old loop, the new loop and two padded loops in 7 layouts " + ref(8) + ".",
          "Each pair of loop and layout has one interval."],
         ["Both padded loops (96 nop and 128 nop) are within 2.3 % of the old loop in all 7 layouts.",
          "64+0 (mesh 0 only): old 348.0 GB/s, new 348.4 GB/s. No drop.",
          "56+56: old 534.8 GB/s, new 300.1 GB/s.",
          "<b>The drop exists only with many threads on both meshes.</b>"]),
    step(5, "Do deep-window cores take from the others?", "held", "Idea held",
         ["Does the rate of a thread depend on the loop of the other threads?"],
         ["A core with a deep window requests more lines ahead. It may take a larger share of the memory traffic."],
         ["Run two processes at the same time, one per mesh, with different loops " + ref(9) + "."],
         ["New loop on mesh 0, 256-nop loop on mesh 1: mesh 0 reads 349.8 GB/s, mesh 1 reads 108.2 GB/s.",
          "Mesh 0 alone with the new loop reads 348 GB/s. So mesh 0 reads as if mesh 1 were idle.",
          "256-nop loop on both: 327.4 and 221.8 GB/s (total 549.1 GB/s).",
          "New loop on both: 175.7 and 127.2 GB/s (total 302.9 GB/s).",
          "<b>The deeper window takes the larger share. When all cores have a deep window, all are slow.</b>"]),
    step(6, "Is the chip congested in the slow state?", "rej", "Idea rejected",
         ["Are the mesh or DRAM overloaded in the slow state?"],
         ["Too many requests fill the queues of the mesh. Requests are retried. DRAM does wasted reads."],
         ["Read the counters of the mesh and of the 24 memory ports with root rights " + ref(11) + ".",
          "Measure the time of one memory request on one core per mesh, while the other 118 cores read " + ref(10) + "."],
         ["DRAM gets 1.00 read request per line in the slow state and 1.00 in the fast state with 96 nop. The 256-nop loop has 1.08. So the slow state wastes no read.",
          "Request retries per line: 0.047 (slow) against 0.072 (fast). The slow state has fewer.",
          "One exception: data-link stalls to the north and south are higher in the slow state (north: 0.119 against 0.069 per line).",
          "One memory request takes 203 to 211 ns with the new loop on all cores (slow) against 238 to 287 ns with a padded loop on all cores (fast). The slow state is quicker.",
          "Lines in flight per core: 6.5 to 9.2 (slow, est.) against 14.9 to 25.3 (fast, est.).",
          "<b>No queue and no memory port is congested. In the slow state the cores keep fewer requests outstanding.</b>"]),
    step(7, "Is the deep window alone enough?", "held", "Idea held",
         ["Is the cause the number of lines in the window, or the way a core treats a stream in address order?"],
         ["A core treats a stream in address order in a special way (the prefetcher follows it).",
          "If this is part of the cause, the same loads in a scrambled order do not show the drop."],
         ["Read the same bytes with the same loads, but visit the 256 B blocks in a scrambled order " + ref(12) + ".",
          "One interval of 10 s per loop and order at 64+56. One scrambled order was tested."],
         ["Address order, load-only loop: 297.8 GB/s.",
          "Scrambled order, same loads: 489.6 GB/s.",
          "In scrambled order the deep window is the faster one (489.6 against 382.5 GB/s with 256 nop).",
          "<b>In this run the drop needed a deep window and address order together.</b>",
          "Hypothesis: a core limits its own requests for a stream in address order (section 4). Steps 6 and 7 fit this. They do not prove it."]),
]

CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#fcfcfb;color:#0b0b0b;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:28px;line-height:1.25;margin:0 0 6px}
h2{font-size:21px;margin:40px 0 10px;padding-top:14px;border-top:1px solid #e4e3df}
h3{font-size:17px;margin:0 0 8px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
p{margin:8px 0}
ul{margin:4px 0 8px;padding-left:22px}
li{margin:3px 0}
.sub{color:#52514e;font-size:14px;margin:0 0 18px}
.short{background:#f1f0ec;border-left:4px solid #1f6fc9;padding:12px 16px;margin:14px 0}
.short p{margin:4px 0}
dl.words{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:4px 14px;margin:8px 0;font-size:15px}
dl.words dt{font-weight:600}
dl.words dd{margin:0}
@media (max-width:600px){dl.words{grid-template-columns:1fr;gap:0}dl.words dd{margin:0 0 8px}}
.tw{overflow-x:auto;margin:10px 0}
table{border-collapse:collapse;font-size:14px;line-height:1.35}
th,td{border-bottom:1px solid #e4e3df;padding:4px 10px;text-align:left;vertical-align:top}
th{background:#f1f0ec;font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
figure{margin:16px 0}
.fig{overflow-x:auto;border:1px solid #e4e3df;border-radius:6px;background:#fcfcfb}
.fig svg{display:block;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
figcaption{font-size:14.5px;margin-top:6px}
.take{font-weight:600}
.ref{color:#52514e;font-size:0.85em;white-space:nowrap}
.note{color:#52514e;font-size:14px}
ol.refs{font-size:14px;padding-left:0;list-style:none}
ol.refs li{margin:5px 0;overflow-wrap:anywhere}
details{margin:8px 0}
summary{cursor:pointer;font-weight:600}
.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:6px 0;margin:14px 0}
.flow a{flex:1 1 108px;max-width:150px;border:1px solid #c9c7c0;border-radius:6px;padding:8px 8px 9px;background:#fff;color:inherit;text-decoration:none;font-size:13px;line-height:1.35;display:flex;flex-direction:column;gap:5px}
.flow a .q{font-weight:600}
.flow a .a{margin-top:auto;border-top:3px solid #1f6fc9;padding-top:5px}
.flow a.rej .a{border-top-color:#c2500a}
.flow .arr{flex:0 0 18px;display:flex;align-items:center;justify-content:center;color:#52514e;font-size:16px}
.num{display:inline-flex;width:26px;height:26px;border-radius:50%;background:#0b0b0b;color:#fff;align-items:center;justify-content:center;font-size:14px;font-weight:600;flex:none}
.flow .num{width:21px;height:21px;font-size:12px}
.tag{font-size:12.5px;font-weight:600;padding:1px 8px;border-radius:10px;border:1px solid #1f6fc9;color:#17559b;background:#eaf2fc}
.tag.rej{border-color:#c2500a;color:#99400a;background:#fdf0e6}
.step{border:1px solid #e4e3df;border-radius:8px;padding:14px 16px 8px;margin:14px 0;background:#fff}
.qitr{display:grid;grid-template-columns:92px 1fr;gap:2px 12px}
.qitr .k{font-weight:600;color:#52514e;padding-top:4px}
.qitr .k.res{color:#0b0b0b}
.qitr .v.res{background:#f6f5f1;border-radius:6px;padding:2px 6px}
@media (max-width:600px){.qitr{grid-template-columns:1fr}}
"""


def build():
    flow = []
    for i, (n, q, a, cls) in enumerate(FLOW):
        if i:
            flow.append('<span class="arr" aria-hidden="true">&rarr;</span>')
        flow.append(f'<a class="{cls}" href="#s{n}"><span class="num">{n}</span><span class="q">{q}</span><span class="a">{a}</span></a>')
    words = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in WORDS)
    refs = "".join(f"<li>[Ref{i+1}] {html.escape(t)}</li>" for i, t in enumerate(REFS))
    page = f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Whole-chip read drop: easy read</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Why the whole-chip read rate fell with the new test loop: easy read</h1>
<p class="sub">CRB, 120 threads. The investigation ran on 2026-11-15. The original run is from 2026-11-13. This page is the simple version of the full report {ref(2)}. All numbers come from the facts sheet {ref(1)}.</p>

<h2 id="short">Short version</h2>
<div class="short">
<p>The benchmark has read, write and copy loops, and with 120 threads only the read total dropped by a large amount: about 300 GB/s with the new loop against about 468 GB/s with the old loop (36 % lower).</p>
<p>The new read loop holds only loads, and each core then works on 36 to 40 cache lines at one time instead of 18 to 22.</p>
<p>The total is 230 to 310 GB/s above about 30 lines, 459 to 480 GB/s at 12 to 28 lines, and 543.9 to 549.0 GB/s (the highest measured) at 8 to 12 lines, and the rule inside the core that causes this is not established.</p>
</div>

<details><summary>Words used here</summary>
<dl class="words">{words}</dl>
</details>

<h2 id="goal">1. The goal</h2>
<h3>The problem</h3>
<ul>
<li>The benchmark got new test loops for read, write and copy.</li>
<li>The new loops were made to do less work per byte. For example, the new read loop has no adds.</li>
<li>An earlier test run used old and new loops with 120 threads on CRB {ref(3)}.</li>
<li>The read total and the write total were lower with the new loops. The copy total was not lower in that file.</li>
</ul>
<figure>
<div class="fig">{fig1()}</div>
<figcaption><span class="take">Figure 1. The original run: read and write look lower with the new loop, copy does not.</span> 120 threads, stop rule of the benchmark (whole-pass stop), 0.5 s intervals, 6 intervals per loop. The new loop here is the C version. The black mark on a write bar is the median {ref(3)}.</figcaption>
</figure>
<h3>Why it is a mystery</h3>
<ul>
<li><b>Less work gave a lower rate.</b> The new read loop does only loads. It was expected to be at least as fast as the old loop.</li>
<li><b>With threads on one mesh there is no drop.</b> 64 threads on mesh 0 read 348.0 GB/s with the old loop and 348.4 GB/s with the new loop {ref(8)}.</li>
<li><b>More threads gave a lower total.</b> The new loop reads 445.0 GB/s with 64+32 threads and 300.1 GB/s with 56+56 threads {ref(8)}.</li>
<li><b>The goal:</b> find which drops are real, and find the cause.</li>
</ul>

<h2 id="answer">2. The answer in one chart</h2>
<ul>
<li>Each point is one read loop, run with 120 threads (64+56).</li>
<li>The horizontal position is the window depth: how many cache lines the core works on at one time.</li>
<li>The vertical position is the total read rate.</li>
</ul>
<figure>
<div class="fig">{fig2()}</div>
<figcaption><span class="take">Figure 2. The total depends on the window depth. Loops with a range at or above 32 to 34 lines are slow. Loops with a range at or below 24 to 28 lines are fast.</span> 29 loop variants at 64+56, common stop. Each point is the middle of the lowest and the highest interval (2 to 22 intervals per loop). The horizontal bar is the measured range of the window depth {ref(6, 7)}.</figcaption>
</figure>
<ul>
<li><b>The old loop is fast for a reason that nobody intended.</b> Its 8 vector adds per 128 B fill the window. So its window covers only 18 to 22 lines.</li>
<li><b>The new loop removed the adds.</b> Its window covers 36 to 40 lines. This is above the limit of about 30 lines.</li>
<li><b>The remedy is verified.</b> 72 to 192 nop per 256 B give 459 to 480 GB/s. 256 nop give 543.9 to 549.0 GB/s. This is 17 % above the old loop.</li>
<li><b>The best point is not known.</b> The loop with 8 to 12 lines gave the highest total. No loop with fewer than 8 lines was tested.</li>
<li><b>Write and copy are not part of this.</b> Copy did not drop. Most of the write drop comes from the stop rule of the benchmark (step 1).</li>
</ul>
<h3>How to read the table</h3>
<ul>
<li><b>Window.</b> A window is not one pass of the loop. It is a part of the core: the list of instructions that the core has fetched and has not yet finished. On CRB it holds up to 684 nop. Several passes of a loop fit in it at one time.</li>
<li><b>Window depth.</b> The number of 64 B cache lines that the loads inside one full window touch. The core can request all these lines from memory at one time. Example: about 9 to 10 passes of the new loop fit in the window, and each pass reads 4 lines, so the depth is 36 to 40 lines.</li>
<li><b>Sum of the read rates.</b> 120 threads run at the same time: 64 threads on CPUs 0 to 63 and 56 threads on CPUs 64 to 119 (written 64+56). The value is the sum of the rates of all 120 threads.</li>
<li><b>Timed intervals (n).</b> The number of timed measurements behind the row. The rate column shows the lowest and the highest of these n measurements.</li>
</ul>
<div class="tw"><table>
<tr><th>Loop</th><th class="n">Cache lines in one full window (window depth)</th><th class="n">Sum of the read rates of all 120 threads, GB/s</th><th class="n">Timed intervals (n)</th></tr>
<tr><td>One load per line</td><td class="n">156 to 164</td><td class="n">230.2 to 235.0</td><td class="n">16</td></tr>
<tr><td>New load-only loop</td><td class="n">36 to 40</td><td class="n">288.5 to 309.8</td><td class="n">22</td></tr>
<tr><td>Load-only loop + 64 nop</td><td class="n">28 to 32</td><td class="n">325.5 to 333.9</td><td class="n">13</td></tr>
<tr><td>Load-only loop + 72 nop</td><td class="n">24 to 28</td><td class="n">459.0 to 459.3</td><td class="n">2</td></tr>
<tr><td>Old read loop</td><td class="n">18 to 22</td><td class="n">465.5 to 470.1</td><td class="n">22</td></tr>
<tr><td>Load-only loop + 256 nop</td><td class="n">8 to 12</td><td class="n">543.9 to 549.0</td><td class="n">9</td></tr>
</table></div>
<p class="note">The full report has all 29 rows {ref(2)}.</p>

<h2 id="path">3. How we got there</h2>
<p>Seven steps. Each step has a question, an idea, a test and a result. Select a box to go to the step.</p>
<div class="flow">{''.join(flow)}</div>
<p class="note">Blue line: the idea of the step held. Orange line: the idea of the step was rejected.</p>
{''.join(STEPS)}

<h2 id="open">4. What is still open</h2>
<ul>
<li><b>The exact rule inside the core.</b> Insufficient data. Hypothesis: the core lowers its limit of outstanding requests, or its prefetcher asks for less, for a stream in address order. The manual of an older core type (Neoverse V2) documents such controls. Three things can resolve it. First: read two control registers of the core on CRB. This needs a kernel module or firmware access. The approval for this task did not cover either. Second: read the prefetch section of the manual of this core type (Neoverse V3AE). Third: ask Arm, with the data of steps 5 and 6.</li>
<li><b>The write total with writers on both meshes.</b> Write falls from 455 GB/s on one mesh to 120 to 129 GB/s at 64+56. This is the same for old and new loops. Insufficient data on the cause.</li>
<li><b>The 3 to 4 % by which old write stays above new write with a common stop.</b> Insufficient data on the cause.</li>
</ul>

<h2 id="limits">5. Limits of the data</h2>
<ul>
<li>One machine. All new runs are from one evening: 2026-11-15, 16:56 to 21:03 UTC. Figure 1 is the original run of 2026-11-13. The write comparison under two stop rules (step 1) uses earlier runs with 64 processes.</li>
<li>System load: the 1-minute load average was 0.00 to 71.24 at the start of the scripts, and up to 109.60 at a process launch (101 launches). The high values follow the scripts' own earlier 120-thread processes (hypothesis, not checked further). At every launch 1 task was runnable and 0 users were logged in {ref(14)}.</li>
<li>Steps 4 and 7 have one interval per measured case.</li>
<li>Step 7 tested one scrambled order. The window depth of the scrambled loops was assumed equal to the address-order loops. It was not measured.</li>
<li>Lines in flight (step 6) are estimates: lines per second of a thread times the time of one probe request.</li>
<li>The benchmark source <code>bench/bandwidth.c</code> was not changed. The new loop variants are in two copies of the test program {ref(13)}.</li>
</ul>

<h2 id="refs">References</h2>
<ol class="refs">{refs}</ol>
</main>
</body>
</html>
"""
    open(OUT, "w").write(page)
    print("wrote", OUT, len(page), "bytes")


build()
