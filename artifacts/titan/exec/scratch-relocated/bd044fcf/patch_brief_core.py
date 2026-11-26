#!/usr/bin/env python3
"""Additions to gen_brief.py's core_brief() from run 6 boot F1, highlighted (class r6); no existing number or sentence of the core brief changes."""
path = "/home/jhan/workspace/titan/cache-perf/asimov/gen_brief.py"
s = open(path).read()
def sub(old, new):
    global s
    assert s.count(old) == 1, ("sub", old[:70], s.count(old)); s = s.replace(old, new)

sub('''.gap { font-size:9px; padding:0 5px; border-radius:8px; background:#eef0f3; color:#3b3f46; margin-right:4px; }''',
    '''.gap { font-size:9px; padding:0 5px; border-radius:8px; background:#eef0f3; color:#3b3f46; margin-right:4px; }
.r6 { background:#fff1c2; }   /* the core brief's additions from run 6 boot F1 (2026-11-06), so a reader can tell them from the earlier text */
.r6tag { font-size:9px; padding:0 5px; border-radius:8px; background:#f2c14e; color:#3b2f00; margin-right:4px; font-weight:600; }''')
# the bars: run 6 boot F1's rows beside the run 3 rows they repeat (purple, labelled run 6)
sub('''    f2 = bars_compact(bw, w=1150, xlim=170, rh=BAR_RH)
    read_x = rv[("read", 33554432)]["agg"]["E"] / one[33554432]["read"]''',
    '''    K1 = p.F1["core"]; one1 = {d["size"]: d for d in K1["ONE"]}; m1 = {(d["kernel"], d["size"], d["threads"]): d["agg"] for d in K1["PAIR"] + K1["PERDSU"] + K1["ALL8"]}   # run 6 boot F1, the L3 on
    R6 = C["s7"]
    bw += [dict(label="1 core read 48 KiB (L2) (run 6 boot F1, L3 on)", v=one1[49152]["read"], color=R6), dict(label="1 core read 48 KiB (L2) (run 3, L3 off)", v=one[49152]["read"]),
           dict(label="4 cores, one per DSU, read 16 MiB each (run 6 boot F1, L3 on)", v=m1[("read", 16777216, 4)], color=R6), dict(label="4 cores, one per DSU, read 16 MiB each (run 3, L3 off)", v=PD[("read", 16777216)]),
           dict(label="8 cores read 16 MiB each (run 6 boot F1, L3 on)", v=m1[("read", 16777216, 8)], color=R6), dict(label="8 cores write 16 MiB each (run 6 boot F1, L3 on)", v=m1[("write", 16777216, 8)], color=R6),
           dict(label="1 core reads one OCM region (run 6 boot F1, L3 on)", v=max(K1["OCMBW"]["region"]), color=R6), dict(label="4 cores read four OCM regions (run 6 boot F1, L3 on)", v=K1["OCMBW"]["four"], color=R6)]
    f2 = bars_compact(bw, w=1150, xlim=170, rh=BAR_RH)
    read_x = rv[("read", 33554432)]["agg"]["E"] / one[33554432]["read"]
    r6_read_x = {s: one1[s]["read"] / one[s]["read"] for s in one1 if s >= 49152}''')
# section 3: one highlighted bullet
sub('''<h2>3. What else the runs showed</h2>
<ul>
''', '''<h2>3. What else the runs showed</h2>
<ul>
<li class="r6"><span class="r6tag">run 6</span><b>Boot F1 ran run 3's whole command set with the L3 on (membench-jibin-011, 2026-11-06, commit 0c190a1, boot E's firmware).</b> Every read stream that misses the L3 runs faster: one core reads {min(r6_read_x.values()):.2f} to {max(r6_read_x.values()):.2f} times run 3's rate from 48 KiB to 32 MiB ({one1[33554432]['read']:.1f} GB/s at 32 MiB, as boot E), four cores on four DSUs read {m1[('read', 16777216, 4)]:.1f} GB/s together against {PD[('read', 16777216)]:.1f}, eight cores {m1[('read', 16777216, 8)]:.1f} against {A8[('read', 16777216)]:.1f}, and one core reads an OCM region at {min(K1['OCMBW']['region']):.1f} to {max(K1['OCMBW']['region']):.1f} GB/s against {min(g.OCMBW['region']):.1f} to {max(g.OCMBW['region']):.1f}. No write stream moves: one core {min(one1[s]['write'] for s in one1):.1f} to {max(one1[s]['write'] for s in one1):.1f} GB/s, eight cores {m1[('write', 16777216, 8)]:.0f}, the six writer-placement rows within {max(abs(q['agg'] / r['run3'] - 1) * 100 for q, r in zip(K1['PLACE'], g.PLACE)):.1f} % of run 3, the OCM write {K1['OCMBW']['write']:.1f}. The dependent chains do not move either (CPU 2's L3 rows repeat boot E within 0.2 ns). Why the L3 raises a read stream that misses it is open [bandwidth-*.csv of 011; asimov-c1nano-perf.html, sections 7, 9, 10 and 12].</li>
''')
# section 4: the two caveats that run 6 answers get a highlighted follow-up line each; the earlier lines stay as they were
sub('''<li>DRAM on this emulator image is a memory model, not LPDDR5X, so the DRAM latency and multi-core bandwidth rows are not silicon numbers. Its configured delay is an open question to Jesse.</li>
<li>The bandwidth set (one-core sweep, multi-core, writer placement, OCM bandwidth) has not run with the L3 on.</li>''',
    '''<li>DRAM on this emulator image is a memory model, not LPDDR5X, so the DRAM latency and multi-core bandwidth rows are not silicon numbers. Its configured delay is an open question to Jesse.</li>
<li class="r6"><span class="r6tag">run 6</span>Answered: the memory model has no configured delay (every delay control zero, a 3 ns native response); the rest of the DRAM leg is RTL pipeline by Jesse's stage count, an inference [Jesse's F1 README, The memory model behind the home node].</li>
<li>The bandwidth set (one-core sweep, multi-core, writer placement, OCM bandwidth) has not run with the L3 on.</li>
<li class="r6"><span class="r6tag">run 6</span>Done on boot F1 (section 3 above and the highlighted bars in section 2).</li>''')
sub('''    return page("Asimov C1-Nano memory performance: brief", META, body)''',
    '''    return page("Asimov C1-Nano memory performance: brief", META + ' <span class="r6"><span class="r6tag">run 6</span>Boot F1 (membench-jibin-011, 2026-11-06, commit 0c190a1, boot E\\'s firmware, the L3 on) repeated run 3\\'s command set; its additions on this page are highlighted like this.</span>', body)''')
open(path, "w").write(s); print("core brief additions ok")
