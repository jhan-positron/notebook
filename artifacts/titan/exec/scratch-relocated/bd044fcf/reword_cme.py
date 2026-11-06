"""Reword gen_perf_cme.py: no 'chase', 'register control', or bare 'fresh/flushed/sparse/dense/sequential/vary' labels.
Every (old, new) pair must match exactly once. Run from the project folder."""
import sys
p = "gen_perf_cme.py"
s = open(p).read()
R = [
 # ---- module level: the kind labels and the glossary
 ('R3_LABEL = "run 3 (the L3 off), not repeated with the L3 on"\n',
  'R3_LABEL = "run 3 (the L3 off), not repeated with the L3 on"\n'
  'KIND = {"repeat": "walked many times", "fresh": "walked once", "flushed": "every line flushed first", "seq": "address order"}   # the chain kinds of the latency files, in words\n'
  'ONE_PER_PAGE = "one line per page"   # the OCM chain shape with one member line per 4 KiB page (the files call it sparse)\n'),
 ('    ("dense, sparse, vary (chain shapes)", "The OCM chain shapes of run 4. Dense: every line of the 256 KiB region, 4,096 loads per pass. Sparse: one line per 4 KiB page at one offset, 64 loads per pass. Vary: one line per page at a different offset per page, 64 loads per pass. "\n'
  '                                            "The all-five chains cover the five regions: 20,480 loads dense, 320 sparse."),\n',
  '    ("round-trip baseline", "The cme-roundtrip row: the latency test\'s loop with the load replaced by a register move (DUP then LASTB), so it measures one core-to-CME-to-core round trip with no memory access."),\n'
  '    ("chain, chain load", "The latency test walks a chain of dependent loads: each load reads the address of the next, so the loads cannot overlap. A chain load is one load of that chain, and its time is the load-to-use latency. "\n'
  '                          "A chain is walked many times (later walks hit whatever cache holds it), walked once, or walked with every line flushed from the caches first. The OCM chains have one line per 4 KiB page (64 loads per pass, at one offset or at a different offset per page) or every line of the region (4,096 loads per pass)."),\n'),
 ('WORDS_RUN = [w for w in p.WORDS_NEW if w[0] in ("run, boot", "sequential chain")]\n',
  'WORDS_RUN = [w for w in p.WORDS_NEW if w[0] == "run, boot"]\n'
  'GLOSS_DROP = ("chase", "repeated chase, fresh chain, flushed", "sparse chain")   # shared entries the chain entry above replaces\n'
  'BEST_PASS = "A command walks its chain several times (passes, or reps); best is the fastest. A per-region OCM row has 7 passes, an all-five row over every line 2, a chain walked many times 3 reps."\n'),
 ('{words(WORDS_CME_E + WORDS_RUN + [w for w in p.words_core() if w[0] not in [n for n, _ in p.WORDS_NEW + WORDS_CME_E]])}',
  '{words(WORDS_CME_E + WORDS_RUN + [(k, BEST_PASS if k == "best, pass, rep" else v) for k, v in p.words_core() if k not in [n for n, _ in p.WORDS_NEW + WORDS_CME_E] + list(GLOSS_DROP)])}'),
 # ---- table 4.1
 ('    t1 = table(["Footprint", "Chase", "Core ns (E)",', '    t1 = table(["Footprint", "Chain", "Core ns (E)",'),
 ('               [[kib(d["size"]), d["kind"], fmt(d["core"], 3),', '               [[kib(d["size"]), KIND[d["kind"]], fmt(d["core"], 3),'),
 ('f"Run 3 had no sequential row. Controls on boot E:', 'f"Run 3 had no address-order row. Controls on boot E:'),
 # ---- table 4.2
 ('    t2 = table(["Region", "Distance from DSU 1", "Core sparse best ns (E)", "Core L3 refills per load (E)", "CME sparse best ns (E)", "CME sparse median (E)", "CME dense best (E)", "CME vary best (E)", "CME outer / demand / prefetch per load (E, sparse)", "CME sparse best, run 3", "CME sparse best, boot C", "CME read GB/s (run 3, L3 off)", "Core read GB/s (run 3, L3 off)"],',
  '    t2 = table(["Region", "Distance from DSU 1", f"Core best ns, {ONE_PER_PAGE} (E)", "Core L3 refills per load (E)", f"CME best ns, {ONE_PER_PAGE} (E)", f"CME median, {ONE_PER_PAGE} (E)", "CME best, every line (E)", f"CME best, {ONE_PER_PAGE} at varied offsets (E)", f"CME outer / demand / prefetch per load (E, {ONE_PER_PAGE})", f"CME best, {ONE_PER_PAGE}, run 3", f"CME best, {ONE_PER_PAGE}, boot C", "CME read GB/s (run 3, L3 off)", "Core read GB/s (run 3, L3 off)"],'),
 ('               + [["All five, sparse (320 loads)", "",', '               + [[f"All five, {ONE_PER_PAGE} (320 loads)", "",'),
 ('                  ["All five, dense (20,480 loads)", "",', '                  ["All five, every line (20,480 loads)", "",'),
 ('f"Boot E, CPU 2 and its CME, OCM mapped in 4 KiB pages, best of 7 sparse passes (2 dense, 7 vary), with the counters as pass means per load',
  'f"Boot E, CPU 2 and its CME, OCM mapped in 4 KiB pages. Chain shapes: {ONE_PER_PAGE} at one offset (64 loads per pass), {ONE_PER_PAGE} at a different offset per page (varied offsets, 64 loads), every line of the region (4,096 loads). Best of 7 passes (2 for the every-line chains), with the counters as pass means per load'),
 ('of the loads in the core\'s sparse rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so these values are below the true OCM latency. The core\'s OCM number to quote is the dense all-five row,',
  'of the loads in the core\'s {ONE_PER_PAGE} rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so these values are below the true OCM latency. The core\'s OCM number to quote is the all-five row over every line,'),
 ('f"The CME\'s sparse rows count {E_INNER_RNG[0]:.2f}', 'f"The CME\'s {ONE_PER_PAGE} rows count {E_INNER_RNG[0]:.2f}'),
 # ---- table 4.6
 ('               [[f"OCM{r} sparse chase", f"{g.ATTR_CME[r][\'own\']:,}"', '               [[f"OCM{r} chain, {ONE_PER_PAGE}", f"{g.ATTR_CME[r][\'own\']:,}"'),
 ('f"The flushed 8 MiB CME command put {g.FLUSH_SPREAD[0]:,}', 'f"The 8 MiB CME command with every line flushed first put {g.FLUSH_SPREAD[0]:,}'),
 # ---- figures
 ('f"{c4[\'ns\']:.1f} ns at 4 KiB; register control {RT_E[0]:.1f} ns", K["cme"]),', 'f"{c4[\'ns\']:.1f} ns at 4 KiB; round-trip baseline {RT_E[0]:.1f} ns", K["cme"]),'),
 ('f"{cfl[\'ns\']:.1f} ns at 8 MiB flushed; core {cfl[\'core\']:.1f}", "#f1f1ee")],', 'f"{cfl[\'ns\']:.1f} ns at 8 MiB, every line flushed first; core {cfl[\'core\']:.1f}", "#f1f1ee")],'),
 ('f"CME boot E {kib(d[\'size\'])} {d[\'kind\']}: {d[\'ns\']:.3f} ns, inner', 'f"CME boot E {kib(d[\'size\'])} {KIND[d[\'kind\']]}: {d[\'ns\']:.3f} ns, inner'),
 ('f"CME boot C {kib(d[\'size\'])} {d[\'kind\']}: {d[\'nsC\']:.3f} ns"', 'f"CME boot C {kib(d[\'size\'])} {KIND[d[\'kind\']]}: {d[\'nsC\']:.3f} ns"'),
 ('f"CME run 3 {kib(d[\'size\'])} {d[\'kind\']}: {d[\'ns3\']:.3f} ns"', 'f"CME run 3 {kib(d[\'size\'])} {KIND[d[\'kind\']]}: {d[\'ns3\']:.3f} ns"'),
 ('f"CME boot B {kib(d[\'size\'])} {d[\'kind\']}: {d[\'nsB\']:.3f} ns"', 'f"CME boot B {kib(d[\'size\'])} {KIND[d[\'kind\']]}: {d[\'nsB\']:.3f} ns"'),
 ('hline=(RT_E[0], f"DUP/LASTB register control {RT_E[0]:.1f} ns, no memory access"))', 'hline=(RT_E[0], f"round-trip baseline {RT_E[0]:.1f} ns (DUP/LASTB, no memory access)", 98304))'),
 ('    orows = [dict(label=f"OCM{o[\'region\']} ({o[\'dist\']} xp) sparse best",', '    orows = [dict(label=f"OCM{o[\'region\']} ({o[\'dist\']} xp), {ONE_PER_PAGE}, best",'),
 ('    orows += [dict(label="all five, sparse, best", a=p.ALL5[2]["E"]["sparse"], b=CALL5_E["sparse"]["best"]), dict(label="all five, dense, best", a=p.ALL5[2]["E"]["dense"], b=CALL5_E["dense"]["best"])]',
  '    orows += [dict(label=f"all five, {ONE_PER_PAGE}, best", a=p.ALL5[2]["E"]["sparse"], b=CALL5_E["sparse"]["best"]), dict(label="all five, every line, best", a=p.ALL5[2]["E"]["dense"], b=CALL5_E["dense"]["best"])]'),
 ('    rrows = [dict(label=f"OCM{o[\'region\']} ({o[\'dist\']} xp) sparse best",', '    rrows = [dict(label=f"OCM{o[\'region\']} ({o[\'dist\']} xp), {ONE_PER_PAGE}, best",'),
 ('    rrows += [dict(label="all five, sparse, best", a=CALL5_3["sparse"]["best"], b=CALL5_E["sparse"]["best"]), dict(label="all five, dense, best", a=CALL5_3["dense"]["best"], b=CALL5_E["dense"]["best"])]',
  '    rrows += [dict(label=f"all five, {ONE_PER_PAGE}, best", a=CALL5_3["sparse"]["best"], b=CALL5_E["sparse"]["best"]), dict(label="all five, every line, best", a=CALL5_3["dense"]["best"], b=CALL5_E["dense"]["best"])]'),
 ('    srows += [dict(label="CME all five, sparse, boot E",', '    srows += [dict(label=f"CME all five, {ONE_PER_PAGE}, boot E",'),
 ('        ("Register control, DUP then LASTB: the core-to-CME link both ways, no memory access",', '        ("Round-trip baseline, DUP then LASTB: the core-to-CME link both ways, no memory access",'),
 ('        ("Chase at 4 KiB, fits the CME L1D', '        ("Chain load at 4 KiB, fits the CME L1D'),
 ('        ("Chase at 256 KiB, fits the DSU L3', '        ("Chain load at 256 KiB, fits the DSU L3'),
 ('        ("Fresh chain of 2 MiB, fits the SLC (core at 2 MiB)"', '        ("2 MiB chain walked once, fits the SLC (core at 2 MiB)"'),
 ('        ("Sparse chase of one OCM region, best of five regions (core, same rows)"', '        (f"Chain with {ONE_PER_PAGE} over one OCM region, best of five regions (core, same rows)"'),
 # ---- short version and the first list
 ('against a {RT_E[0]:.1f} ns register round trip with no memory access. From 8 KiB on the chase climbs', 'against a {RT_E[0]:.1f} ns round-trip baseline (a register move with no memory access). From 8 KiB on the chain load climbs'),
 ('{c4[\'ns\']:.1f} ns at 4 KiB (chase minus DUP/LASTB control {c4[\'ns\'] - RT_E[0]:.2f} ns, a derived number', '{c4[\'ns\']:.1f} ns at 4 KiB (chain load minus round-trip baseline {c4[\'ns\'] - RT_E[0]:.2f} ns, a derived number'),
 ('on boot B, with that prefetcher off, the chase reads {B_L1[0][1]:.1f}', 'on boot B, with that prefetcher off, the chain load reads {B_L1[0][1]:.1f}'),
 ('ns per region through the CME (sparse best) against {CORE_SP_RNG[0]:.1f} to {CORE_SP_RNG[1]:.1f} ns for the core\'s own sparse loads.', 'ns per region through the CME (best of the chains with {ONE_PER_PAGE}) against {CORE_SP_RNG[0]:.1f} to {CORE_SP_RNG[1]:.1f} ns for the core\'s own loads of the same chains.'),
 ('(section 7). The all-five dense chain reads {CALL5_E[\'dense\'][\'best\']:.1f} ns', '(section 7). The all-five chain over every line reads {CALL5_E[\'dense\'][\'best\']:.1f} ns'),
 # ---- section 2
 ('cycles per ns on the {len(CLOCK_E)} chase rows of boot E', 'cycles per ns on the {len(CLOCK_E)} chain rows of boot E'),
 ('CME cycles per core cycle on its DRAM chase rows.', 'CME cycles per core cycle on its DRAM chain rows.'),
 ('(the 64 KiB to 512 KiB chases run with the L2 and L3 hit events)', '(the 64 KiB to 512 KiB chains run with the L2 and L3 hit events)'),
 ('<li><b>Rows added.</b> The sequential 8 MiB chain through the CME, and the dense and vary shapes of each OCM region beside the sparse one (table 4.2).</li>',
  '<li><b>Rows added.</b> The 8 MiB chain in address order through the CME, and two more chain shapes of each OCM region (every line, and {ONE_PER_PAGE} at varied offsets) beside the {ONE_PER_PAGE} chain (table 4.2).</li>'),
 ('Of the {len(REP3)} CME chase rows run 3 also ran,', 'Of the {len(REP3)} CME chain rows run 3 also ran,'),
 ('at {kib(REP3_MAX[0][\'size\'])} ({REP3_MAX[0][\'kind\']}), a row where', 'at {kib(REP3_MAX[0][\'size\'])} ({KIND[REP3_MAX[0][\'kind\']]}), a row where'),
 # ---- section 3
 ('The chase times written in the boxes are measured at a footprint.', 'The chain-load times written in the boxes are measured at a footprint.'),
 ('The label under each home node is the CME\'s best sparse chase of that region beside CPU 2\'s own, both from boot E.', 'The label under each home node is the CME\'s best chain with {ONE_PER_PAGE} over that region beside CPU 2\'s own, both from boot E.'),
 ('at 2 MiB (fresh chain), {cfl[\'ns\']:.1f} against', 'at 2 MiB (chain walked once), {cfl[\'ns\']:.1f} against'),
 ('f"The register control (DUP then LASTB, no memory access) reads {RT_E[0]:.1f} ns per load', 'f"The round-trip baseline (DUP then LASTB, no memory access) reads {RT_E[0]:.1f} ns per load'),
 ('The chase replaces DUP with LD1D, a different dependency chain, so chase minus control ({c4', 'The latency test replaces DUP with LD1D, a different dependency chain, so chain load minus baseline ({c4'),
 ('<p>The example is one load of the chase kernel:', '<p>The example is one load of the latency test\'s kernel:'),
 ('The register control that does only that reads {RT_E[0]:.1f} ns. The 4 KiB chase reads {c4', 'The round-trip baseline that does only that reads {RT_E[0]:.1f} ns. The 4 KiB chain load reads {c4'),
 ('From 4 KiB to the flushed 8 MiB row they climb', 'From 4 KiB to the 8 MiB row with every line flushed first they climb'),
 ('The chase minus the control ({c4[\'ns\'] - RT_E[0]:.2f} ns at 4 KiB) is a derived number: the two rows', 'The chain load minus the baseline ({c4[\'ns\'] - RT_E[0]:.2f} ns at 4 KiB) is a derived number: the two rows'),
 ('The measured control is {RT_CYC_E[0]:.0f} CME cycles per load', 'The measured baseline is {RT_CYC_E[0]:.0f} CME cycles per load'),
 # ---- section 5
 ('With the CME prefetcher off (boot B) the chase stays at {B_L1[0][1]:.2f}', 'With the CME prefetcher off (boot B) the chain load stays at {B_L1[0][1]:.2f}'),
 ('The CME\'s fresh chains of 512 KiB to 1 MiB ({c512', 'The CME\'s chains walked once, 512 KiB to 1 MiB ({c512'),
 ('and its flushed 8 MiB row ({cfl[\'ns\']:.1f} ns) reads below its unflushed one', 'and its 8 MiB row with every line flushed first ({cfl[\'ns\']:.1f} ns) reads below its unflushed one'),
 ('The CME minus the register round trip at 4 KiB is', 'The chain load minus the round-trip baseline at 4 KiB is'),
 ('The sequential 8 MiB chain through the CME reads {cseq', 'The 8 MiB chain in address order through the CME reads {cseq'),
 ('On the sparse OCM passes (every line flushed from the caches before the pass)', 'On the OCM passes with {ONE_PER_PAGE} (every line flushed from the caches before the pass)'),
 ('The chase is not faster: E reads', 'The chain load is not faster: E reads'),
 ('the prefetcher\'s fills set the chase time on both boots, and no CME event', 'the prefetcher\'s fills set the chain-load time on both boots, and no CME event'),
 # ---- section 6
 ('while run 3\'s chase latency rises', 'while run 3\'s chain-load latency rises'),
 # ---- section 7
 ('ns more per load through the CME than from the core on the sparse rows, and {CALL5_E[\'dense\'][\'best\'] - p.ALL5[2][\'E\'][\'dense\']:.1f} ns more on the all-five dense chain."',
  'ns more per load through the CME than from the core on the rows with {ONE_PER_PAGE}, and {CALL5_E[\'dense\'][\'best\'] - p.ALL5[2][\'E\'][\'dense\']:.1f} ns more on the all-five chain over every line."'),
 ('of the loads in the core\'s sparse rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so the core\'s values are below the true OCM latency. The CME\'s rows count',
  'of the loads in the core\'s {ONE_PER_PAGE} rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so the core\'s values are below the true OCM latency. The CME\'s rows count'),
 ('The dense all-five chase reads {CALL5_E[\'dense\'][\'best\'] - CALL5_E[\'sparse\'][\'best\']:+.1f} ns against the sparse one through the CME,', 'The all-five chain over every line reads {CALL5_E[\'dense\'][\'best\'] - CALL5_E[\'sparse\'][\'best\']:+.1f} ns against the {ONE_PER_PAGE} one through the CME,'),
 ('On the core the dense row reads {p.ALL5[2][\'E\'][\'dense\'] - p.ALL5[2][\'E\'][\'sparse\']:+.1f} ns against the sparse one [table 4.2]. The per-region dense rows through the CME read {E_DN_RNG[0]:.1f} to {E_DN_RNG[1]:.1f} ns, below the sparse best of',
  'On the core the every-line row reads {p.ALL5[2][\'E\'][\'dense\'] - p.ALL5[2][\'E\'][\'sparse\']:+.1f} ns against the {ONE_PER_PAGE} one [table 4.2]. The per-region every-line rows through the CME read {E_DN_RNG[0]:.1f} to {E_DN_RNG[1]:.1f} ns, below the {ONE_PER_PAGE} best of'),
 ('f"Against run 3, boot E\'s sparse CME rows read {min(E3_RATIO):.2f} to {max(E3_RATIO):.2f} times run 3\'s by region, the all-five sparse chain {CALL5_E[\'sparse\'][\'best\'] / CALL5_3[\'sparse\'][\'best\']:.2f} times and the dense one',
  'f"Against run 3, boot E\'s {ONE_PER_PAGE} CME rows read {min(E3_RATIO):.2f} to {max(E3_RATIO):.2f} times run 3\'s by region, the all-five {ONE_PER_PAGE} chain {CALL5_E[\'sparse\'][\'best\'] / CALL5_3[\'sparse\'][\'best\']:.2f} times and the every-line one'),
 ('f"Best of 7 sparse passes (2 dense) on each run [cme-latency-ocm-*.csv of 004 and 010].', 'f"Best of 7 passes (2 for the every-line chains) on each run [cme-latency-ocm-*.csv of 004 and 010].'),
 ('ns on the same sparse rows and {p.CME_ALL5[\'C\'][\'dense\']:.2f} ns dense all five, so', 'ns on the same {ONE_PER_PAGE} rows and {p.CME_ALL5[\'C\'][\'dense\']:.2f} ns on all five over every line, so'),
 ('and in one flushed pass against warm passes, so the data', 'and in one pass with every line flushed first against warm passes, so the data'),
 # ---- section 8
 ('The sparse chases, whose counts are dominated by the core-side chain build and the 7 flushes,', 'The {ONE_PER_PAGE} chains, whose counts are dominated by the core-side chain build and the 7 flushes,'),
 ('prefetch refills per sparse-chain load on boot E (table 4.2)', 'prefetch refills per load of the {ONE_PER_PAGE} chains on boot E (table 4.2)'),
 ('The flushed 8 MiB CME command spread its', 'The 8 MiB CME command with every line flushed first spread its'),
 # ---- section 9
 ('<li>CME L1 chase: {c4[\'ns\']:.2f} ns on boot E', '<li>CME L1 chain load: {c4[\'ns\']:.2f} ns on boot E'),
 ('The DUP/LASTB control, which asimov-bench did not run, reads {RT_E[0]:.1f} ns. Chase minus control is', 'The round-trip baseline (DUP then LASTB), which asimov-bench did not run, reads {RT_E[0]:.1f} ns. Chain load minus baseline is'),
 ('ns of its {p.CONTROLS[\'B\'][\'rt\'][0]:.2f} ns control: the CME L1 load', 'ns of its {p.CONTROLS[\'B\'][\'rt\'][0]:.2f} ns baseline: the CME L1 load'),
 ('On boot E the prefetcher\'s fills set the chase time (section 5), and the two chases differ in chain construction and footprint.', 'On boot E the prefetcher\'s fills set the chain-load time (section 5), and the two tests differ in chain construction and footprint.'),
 ('ns per region on boot E (sparse best, run 3 {R3_SP_RNG[0]:.1f}', 'ns per region on boot E (best of the {ONE_PER_PAGE} chains, run 3 {R3_SP_RNG[0]:.1f}'),
 # ---- section 10
 ('on boot E the sparse medians run {min(E_MED_ABOVE):.1f}', 'on boot E the {ONE_PER_PAGE} medians run {min(E_MED_ABOVE):.1f}'),
 ('(the 2 MiB fresh chain at {c2m[\'ns\']:.1f} ns and the flushed 8 MiB row at {cfl[\'ns\']:.1f} ns,', '(the 2 MiB chain walked once at {c2m[\'ns\']:.1f} ns and the 8 MiB row with every line flushed first at {cfl[\'ns\']:.1f} ns,'),
 ('The memory model\'s configured delay behind the flushed rows (asked of Jesse, unanswered).', 'The memory model\'s configured delay behind the rows with every line flushed first (asked of Jesse, unanswered).'),
 # ---- sources (the shared list says "the dense OCM chains")
 ('{"".join(f"<li><a href=\'{s}\'>{s}</a>: {t}.</li>" for s, t in p.SOURCES)}', '{"".join(f"<li><a href=\'{s}\'>{s}</a>: {t.replace("the dense OCM chains", "the OCM chains over every line")}.</li>" for s, t in p.SOURCES)}'),
]
bad = [(s.count(a), a[:70]) for a, b in R if s.count(a) != 1]
if bad:
    for n, a in bad: print("count", n, ":", a)
    sys.exit(1)
for a, b in R: s = s.replace(a, b)
open(p, "w").write(s)
print("edits", len(R))
