#!/usr/bin/env python3
"""Fixes to gen_brief.py from the peer review of 2026-11-07 (findings 38 to 46)."""
path = "/home/jhan/workspace/titan/cache-perf/asimov/gen_brief.py"
s = open(path).read()
def sub(old, new):
    global s
    assert s.count(old) == 1, ("sub", old[:70], s.count(old)); s = s.replace(old, new)

# derived numbers
sub('''    F1_PAIR_W = next(q["agg"] for q in K1["PLACE"] if q["cpus"] == "2-3")
''', '''    F1_PAIR_W = next(q["agg"] for q in K1["PLACE"] if q["cpus"] == "2-3")
    STAMP = C1["CALL_NS"][0] - g.CALL_NS[0] if False else C1["CALL_NS"][0] - min(d["ns"] for d in p.E["RT"]) - (min(d["ns"] for d in p.E["RT"]) * 0)   # placeholder, replaced below
    STAMP = C1["CALL_NS"][0] - min(d["ns"] for f in __import__("glob").glob(p.A_DIR + "/" + p.PLATFORM["E"]["dir"] + "cme-latency-*.csv") for d in p.r4.lat(f) if d["mode"] == "cme-call")   # ns est.: cme-call on F1 against boot E
    CW1 = dict(small=(min(d["write"]["agg"] for d in C1["CBW"] if d["size"] <= 262144), max(d["write"]["agg"] for d in C1["CBW"] if d["size"] <= 262144)), big=(min(d["write"]["agg"] for d in C1["CBW"] if d["size"] >= 1048576), max(d["write"]["agg"] for d in C1["CBW"] if d["size"] >= 1048576)))
    W3_TXT = f"{max(d['write'] for d in CBW if d['size'] <= 2097152):.0f} GB/s at 16 KiB to 2 MiB and {next(d['write'] for d in CBW if d['size'] == 33554432):.0f} at 32 MiB"
    f2_in_best = (min(d["e"]["cme_l1d_refill_inner"] for d in f2_l3.values()), max(d["e"]["cme_l1d_refill_inner"] for d in f2_l3.values()))
''')
sub('''    STAMP = C1["CALL_NS"][0] - g.CALL_NS[0] if False else C1["CALL_NS"][0] - min(d["ns"] for d in p.E["RT"]) - (min(d["ns"] for d in p.E["RT"]) * 0)   # placeholder, replaced below
''', '')
# [38] the cost row
sub('''["Cost per call (the four L1 forms, 4 to 24 KiB)", "", f"read call about {FORM1[('looped', 'read')]['fit']['a_ns'] - FORM1[('single', 'read')]['fit']['a_ns']:.0f} ns, {FORM1[('looped', 'read')]['fit']['a_ns'] - FORM1[('nofold', 'read')]['fit']['a_ns']:.0f} of it the fold", "boot F1 (run 6)", f"the looped read's line (ns per pass against bytes) gives {FORM1[('looped', 'read')]['fit']['a_ns']:.0f} ns per pass, the single-call read's {FORM1[('single', 'read')]['fit']['a_ns']:.1f}. A write call hides its cost behind its posted stores; DSB ST before SMSTOP exposes''',
    '''["Cost per call (the four L1 forms, 4 to 24 KiB)", "", f"read call about {FORM1[('looped', 'read')]['fit']['a_ns']:.0f} ns by run 6's bracket, of which about {STAMP:.0f} ns is run 6's own clock stamps and {FORM1[('looped', 'read')]['fit']['a_ns'] - FORM1[('nofold', 'read')]['fit']['a_ns']:.0f} the fold", "boot F1 (run 6)", f"the looped read's line (ns per pass against bytes) gives {FORM1[('looped', 'read')]['fit']['a_ns']:.0f} ns per pass; cme-call, a one-instruction call, reads {C1['CALL_NS'][0]:.0f} ns on run 6 against boot E's {C1['CALL_NS'][0] - STAMP:.0f}, so net of the stamps the call costs about {FORM1[('looped', 'read')]['fit']['a_ns'] - STAMP:.0f} ns est. (run 3's 1 KiB read call: {CALLB['read']:.0f} ns); no run 6 row isolates the stamps. A write call's cost overlaps with its posted stores; DSB ST before SMSTOP exposes''')
# [39] [40] the write numbers (bullet, caption, row)
sub('''On boots F1 and F2 alike the CME writes {CBW1[262144]['write']['agg']:.0f} GB/s to 256 KiB and {CBW1[33554432]['write']['agg']:.0f} from 1 MiB, in span too, where run 3 wrote {b32m['write']:.0f} at every footprint with the L3 off;''',
    '''On boots F1 and F2 alike the CME writes {CW1['small'][0]:.0f} to {CW1['small'][1]:.0f} GB/s by the bracket from 16 to 256 KiB and {CW1['big'][0]:.0f} to {CW1['big'][1]:.0f} GB/s from 1 MiB (in span 53 to 55 from 96 KiB on, {CBW1[16384]['write']['span']:.0f} and {CBW1[49152]['write']['span']:.0f} at 16 and 48 KiB), where run 3 wrote {W3_TXT} with the L3 off;''')
sub('''It writes {CBW1[262144]['write']['agg']:.0f} GB/s to 256 KiB and {CBW1[33554432]['write']['agg']:.0f} from 1 MiB, against run 3's {b32m['write']:.0f} with the L3 off; the core writes {ONE1[33554432]['write']:.0f}."''',
    '''It writes {CW1['small'][0]:.0f} to {CW1['small'][1]:.0f} GB/s from 16 to 256 KiB and {CW1['big'][0]:.0f} to {CW1['big'][1]:.0f} from 1 MiB, against run 3's {W3_TXT} with the L3 off; the core writes {ONE1[33554432]['write']:.0f}."''')
sub('''f"{CBW1[262144]['write']['agg']:.0f} GB/s to 256 KiB and {CBW1[33554432]['write']['agg']:.0f} from 1 MiB, in span too, on F1 and F2 alike; run 3 wrote {min(d['write'] for d in CBW):.0f} to {max(d['write'] for d in CBW):.0f} with the L3 off (open, full page section 10)"''',
    '''f"{CW1['small'][0]:.0f} to {CW1['small'][1]:.0f} GB/s from 16 to 256 KiB and {CW1['big'][0]:.0f} to {CW1['big'][1]:.0f} from 1 MiB by the bracket, in span too from 96 KiB on, on F1 and F2 alike; run 3 wrote {W3_TXT} with the L3 off (open, full page section 10)"''')
# [41] best-rep inner refills, [42] the caption, [43] the core cell
sub('''f"one demand refill per load, {f2_in[0]:.2f} to {f2_in[1]:.2f} of it from inside the cluster. Minus the baseline: "''', '''f"one demand refill per load, {f2_in_best[0]:.2f} to {f2_in_best[1]:.2f} of it from inside the cluster (best rep; the three reps' mean {f2_in[0]:.2f} to {f2_in[1]:.2f}). Minus the baseline: "''')
sub('''repeats boot B to 64 KiB and reads {min(d['ns'] for d in f2_l3.values()):.1f} to {max(d['ns'] for d in f2_l3.values()):.1f} ns at 192 to 384 KiB, where the L3 serves it. The core steps at 48 KiB,''',
    '''repeats boot B to 64 KiB and reads {min(d['ns'] for d in f2_l3.values()):.1f} to {max(d['ns'] for d in f2_l3.values()):.1f} ns at 192 to 384 KiB, where every load is served inside the cluster ({CL3_2[(196608, 'repeat')]['hit']:.2f} to {CL3_2[(393216, 'repeat')]['hit']:.2f} per load by the exploratory L3-hit event; the rest is a hypothesis, section 4). The core steps at 48 KiB,''')
sub('''["L1 hit, dependent load, 4 to 64 KiB, CME prefetcher off", f"{c[(4096, 'repeat')]['core']:.1f} ns (4 KiB)", f"{min(b_l1):.1f} to {max(b_l1):.1f} ns", "boots B, F2",''',
    '''["L1 hit, dependent load, 4 to 64 KiB, CME prefetcher off", f"{c[(4096, 'repeat')]['core']:.1f} ns (4 KiB, boot E)", f"{min(b_l1):.1f} to {max(b_l1):.1f} ns", "boots B, F2",''')
# [44] the words
sub('''<dt>round-trip baseline</dt><dd>The latency test's loop with the load replaced by a register move (DUP then LASTB), so it measures one core-to-CME-to-core round trip with no memory access.</dd>
</dl>
<h2>1. Latency: core against CME</h2>''',
    '''<dt>round-trip baseline</dt><dd>The latency test's loop with the load replaced by a register move (DUP then LASTB), so it measures one core-to-CME-to-core round trip with no memory access.</dd>
<dt>OCM, SLC, crosspoint, TLB</dt><dd>OCM: the on-chip SRAM, five regions, each behind one home node of the mesh. SLC: the system level cache on the mesh, 3.75 MiB over five home nodes. Crosspoint: one switch of the mesh; a region's home node is 1 or 3 crosspoints from the DSU. TLB: the translation buffer.</dd>
<dt>fold, DSB ST, SOG, TRM, LLVM model, GA13 Palladium</dt><dd>Fold: the read kernel's end-of-call sum of its 16 running totals. DSB ST: the Arm barrier that waits for every earlier store. SOG, TRM: Arm's Software Optimization Guide and Technical Reference Manual. LLVM model: the public C1-Nano timing table in the LLVM compiler. GA13 Palladium: the emulator that runs the Asimov hardware design.</dd>
</dl>
<h2>1. Latency: core against CME</h2>''')
# [45] [46] the core brief's highlighted items
sub('''The dependent chains do not move either (CPU 2's L3 rows repeat boot E within 0.2 ns).''', '''The dependent chains repeat boot E (CPU 2's 192 to 384 KiB rows within {max(abs(next(d['ns'] for d in K1['LV'] if d['size'] == sz and d['kind'] == 'repeat') - lv(sz)) for sz in (196608, 262144, 393216)):.2f} ns of E), so against run 3 they keep boot E's change: {min(next(d['ns'] for d in K1['LV'] if d['size'] == sz and d['kind'] == 'repeat') / lv3(sz) for sz in (196608, 262144, 393216)):.2f} to {max(next(d['ns'] for d in K1['LV'] if d['size'] == sz and d['kind'] == 'repeat') / lv3(sz) for sz in (196608, 262144, 393216)):.2f} times at 192 to 384 KiB.''')
sub('''Answered: the memory model has no configured delay (every delay control zero, a 3 ns native response); the rest of the DRAM leg is RTL pipeline by Jesse's stage count, an inference [Jesse's F1 README, The memory model behind the home node].''',
    '''Answered: the memory model has no configured delay (every delay control zero, a 3 ns native response in the repo's Xcelium test). By Jesse's count of the RTL stages (RTL: the chip's hardware source; an inference) about 20 ns of the DRAM leg is fixed pipeline between the mesh's memory-side nodes and the memory; the rest of the about 29 ns is inside the mesh, not configured anywhere in the tree and not determined [Jesse's F1 README, The memory model behind the home node].''')
open(path, "w").write(s); print("fix_brief ok")
