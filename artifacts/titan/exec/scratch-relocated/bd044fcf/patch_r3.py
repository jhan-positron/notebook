p = "/home/jhan/workspace/titan/cache-perf/asimov/gen_run3.py"; s = open(p).read()
def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (n, s.count(a), a[:80]); s = s.replace(a, b)
# ---- R5: SLC capacity constant
rep('''NODE_OF_REGION = {r: n for n, (x, y, r) in NODES.items()}''', '''NODE_OF_REGION = {r: n for n, (x, y, r) in NODES.items()}
SLC_BYTES = 5 * (1 << 20) * 12 // 16   # 3.75 MiB: five 1 MiB home nodes, 4 of 16 ways locked as OCM''')
rep('''    if size <= 3145728: return "SLC (mesh cache)"''', '''    if size <= SLC_BYTES: return "SLC (mesh cache)"''')
rep('''(3145728, "SLC 3.75 MiB")), ylim=(0, 60), ticks_y=[0, 10, 20, 30, 40, 50, 60])''', '''(SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 60), ticks_y=[0, 10, 20, 30, 40, 50, 60])''')
rep('''marks=((32768, "L1"), (131072, "L2"), (3145728, "SLC")), ylim=(0, 65)''', '''marks=((32768, "L1"), (131072, "L2"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 65)''')
rep('''(262144, "L3 256 KiB"), (3145728, "SLC 3.75 MiB")), ylim=(0, 75)''', '''(262144, "L3 256 KiB"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 75)''')
rep('''marks=((65536, "CME L1 64 KiB"), (262144, "L3"), (3145728, "SLC")), ylim=(0, 135)''', '''marks=((65536, "CME L1 64 KiB"), (262144, "L3 256 KiB"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 135)''')
# ---- R3: bandwidth capacity reading per kernel, copy's two buffers; R10 counts
rep('''# ---------------------------------------------------------------- html helpers''', '''def bw_level(size):
    """a capacity reading of where a streamed buffer of this size fits (hypothesis: the bandwidth rows carry no counters)"""
    return "L1" if size <= 32768 else "L2" if size <= 131072 else "L3 and mesh" if size <= 262144 else "SLC" if size <= SLC_BYTES else "DRAM"
CME_INNER_ZERO = 0; CME_TIMED = 0
for f in sorted(glob.glob(R4 + "cme-latency-*.csv")):
    for d in lat_rows(f):
        if d["mode"].endswith("best") or "roundtrip" in d["mode"] or "call" in d["mode"]: continue
        CME_TIMED += 1; CME_INNER_ZERO += d["c2"] == 0.0
        assert d["c3"] > 0
CALL_OUT = max(CALL, key=lambda d: d["ns"]); CALL_OUT_RATIO = CALL_OUT["c1"] / CALL_OUT["cyc"]

# ---------------------------------------------------------------- html helpers''')
rep('''    t3 = table(["Buffer", "Read GB/s", "Write GB/s", "Copy GB/s", "Run 2 read", "Run 2 write", "Run 2 copy", "Write, run 3 vs run 2", "Buffer sits in"],
               [[kib(d["size"]), fmt(d["read"]), fmt(d["write"]), fmt(d["copy"]), fmt(d["read2"]), fmt(d["write2"]), fmt(d["copy2"]), pct(d["write"], d["write2"]),
                 ("L1" if d["size"] <= 32768 else "L2" if d["size"] <= 131072 else "L3 and mesh" if d["size"] <= 262144 else "SLC" if d["size"] <= 3145728 else "DRAM")] for d in ONE],
               "One thread on CPU 2, best of 3 reps, GB = 1e9 bytes [bandwidth-dram-1core.csv]. Copy counts bytes read plus written.")''',
'''    t3 = table(["Buffer (read, write)", "Copy's two buffers", "Read GB/s", "Write GB/s", "Copy GB/s", "Run 2 read", "Run 2 write", "Run 2 copy", "Write, run 3 vs run 2", "Capacity reading: read and write; copy"],
               [[kib(d["size"]), kib(2 * d["size"]), fmt(d["read"]), fmt(d["write"]), fmt(d["copy"]), fmt(d["read2"]), fmt(d["write2"]), fmt(d["copy2"]), pct(d["write"], d["write2"]),
                 f"{bw_level(d['size'])}; {bw_level(2 * d['size'])}"] for d in ONE],
               "One thread on CPU 2, best of 3 reps, GB = 1e9 bytes [bandwidth-dram-1core.csv]. Copy reads one buffer and writes another of the same size, so its working set is twice the displayed size, and it counts bytes read plus written. The last column is a reading from the capacities (hypothesis): these rows carry no counters, so which level served a stream is not measured.")''')
rep('''    t3 = table(["Buffer", "Core read", "CME read", "Core write", "CME write", "Core copy", "CME copy", "Buffer sits in (core)"],
               [[kib(d["size"]), fmt(d["core_read"]), fmt(d["read"]), fmt(d["core_write"]), fmt(d["write"]), fmt(d["core_copy"]), fmt(d["copy"]),
                 ("L1" if d["size"] <= 32768 else "L2" if d["size"] <= 131072 else "L3 and mesh" if d["size"] <= 262144 else "SLC" if d["size"] <= 3145728 else "DRAM")] for d in CBW],
               "GB/s, one thread on CPU 2 (CPU 3 offline for the CME rows), best of 3 reps, GB = 1e9 bytes [cme-bandwidth-dram-1core.csv, bandwidth-dram-1core.csv]. The 160 KiB and 1 MiB rows have no core twin. Copy counts bytes read plus written.")''',
'''    t3 = table(["Buffer (read, write)", "Copy's two buffers", "Core read", "CME read", "Core write", "CME write", "Core copy", "CME copy", "Core capacity reading: read and write; copy"],
               [[kib(d["size"]), kib(2 * d["size"]), fmt(d["core_read"]), fmt(d["read"]), fmt(d["core_write"]), fmt(d["write"]), fmt(d["core_copy"]), fmt(d["copy"]),
                 f"{bw_level(d['size'])}; {bw_level(2 * d['size'])}"] for d in CBW],
               "GB/s, one thread on CPU 2 (CPU 3 offline for the CME rows), best of 3 reps, GB = 1e9 bytes [cme-bandwidth-dram-1core.csv, bandwidth-dram-1core.csv]. The 160 KiB and 1 MiB rows have no core twin. Copy reads one buffer and writes another of the same size, so its working set is twice the displayed size, and it counts bytes read plus written. The last column reads the core's capacities (hypothesis); the CME's 64 KiB L1 is smaller than the core's L1 plus L2, and no bandwidth row carries counters, so the level that served a stream is not measured for either.")''')
# ---- R4: refill chart from the fastest rep
rep('''        CLV.append(dict(size=d["size"], kind=kind, ns=d["ns"], core=CORE_BEST[(d["size"], kind)]["ns"],
                        outer=(min(p["c3"] for p in ps), max(p["c3"] for p in ps)), inner=(min(p["c2"] for p in ps), max(p["c2"] for p in ps)),''',
'''        bp = best_pass(rows, d["size"])
        CLV.append(dict(size=d["size"], kind=kind, ns=d["ns"], core=CORE_BEST[(d["size"], kind)]["ns"], outer_best=bp["c3"], inner_best=bp["c2"],
                        outer=(min(p["c3"] for p in ps), max(p["c3"] for p in ps)), inner=(min(p["c2"] for p in ps), max(p["c2"] for p in ps)),''')
rep('''    f_ref = line_chart([dict(name="outer refills per load (0x327E, from outside the cluster)", color=C["s2"], pts=[(d["size"], d["outer"][0], f"{kib(d['size'])}: outer {d['outer'][0]:.2f} to {d['outer'][1]:.2f}") for d in CLV if d["kind"] != "flushed"], short="outer"),
                        dict(name="inner refills per load (0x327D, from inside the cluster)", color=C["s7"], pts=[(d["size"], d["inner"][0], f"{kib(d['size'])}: inner {d['inner'][0]:.2f} to {d['inner'][1]:.2f}") for d in CLV if d["kind"] != "flushed"], short="inner", dy=14)],
                       ylabel="CME L1 refills per load (best rep)",''',
'''    f_ref = line_chart([dict(name="outer refills per load (0x327E, from outside the cluster)", color=C["s2"], pts=[(d["size"], d["outer_best"], f"{kib(d['size'])}: outer {d['outer_best']:.2f} in the fastest rep (reps {d['outer'][0]:.2f} to {d['outer'][1]:.2f})") for d in CLV if d["kind"] != "flushed"], short="outer"),
                        dict(name="inner refills per load (0x327D, from inside the cluster)", color=C["s7"], pts=[(d["size"], d["inner_best"], f"{kib(d['size'])}: inner {d['inner_best']:.2f} in the fastest rep (reps {d['inner'][0]:.2f} to {d['inner'][1]:.2f})") for d in CLV if d["kind"] != "flushed"], short="inner", dy=14)],
                       ylabel="CME L1 refills per load, counted in the fastest rep of each footprint (hover for the range over reps)",''')
rep('''{fig(f_ref, f"Outer refills per load are {c8['outer'][0]:.2f} at 8 KiB and {c16['outer'][0]:.2f} at 16 KiB, footprints a 64 KiB L1 should hold, and reach {max(d['outer'][1] for d in CLV):.1f} per load near 128 to 256 KiB.", f"On the sparse OCM passes, where every hop is one demand miss to a flushed line, the same event reads''',
'''{fig(f_ref, f"Outer refills per load are {c8['outer_best']:.2f} at 8 KiB and {c16['outer_best']:.2f} at 16 KiB in the fastest reps, footprints a 64 KiB L1 should hold, and reach {max(d['outer'][1] for d in CLV):.1f} per load near 128 to 256 KiB.", f"On the sparse OCM passes (every line flushed from the core caches before the pass), the same event reads''')
# ---- R1: the register control is a control, not a component or a floor
rep('''<div class="short"><p><b>Short version.</b> Through the CME, a dependent load costs {c4['ns']:.1f} ns at 4 KiB, of which {RT_NS[0]:.1f} ns is the register round trip that every CME instruction pays, and it climbs from 8 KiB on with no clear step at the CME L1's 64 KiB.''',
'''<div class="short"><p><b>Short version.</b> Through the CME, a dependent load costs {c4['ns']:.1f} ns at 4 KiB, beside a {RT_NS[0]:.1f} ns register round trip control that makes no memory access, and it climbs from 8 KiB on with no clear step at the CME L1's 64 KiB.''')
rep('''<li><b>Latency.</b> {c4['ns']:.1f} ns at 4 KiB,''', '''<li><b>Latency.</b> {c4['ns']:.1f} ns at 4 KiB (chase minus DUP/LASTB control {c4['ns'] - RT_NS[0]:.2f} ns, a derived number, not the memory latency),''')
rep('''f"The {RT_NS[0]:.1f} ns register round trip is the floor of every CME row: a value moved into a vector register and back takes {RT_CYC[0]:.0f} CME cycles, and a dependent chase cannot go faster than that per hop [table 4.1].")}''',
'''f"The register control (DUP then LASTB, no memory access) reads {RT_NS[0]:.1f} ns per hop, {RT_CYC[0]:.0f} CME cycles, in all {len(RT)} reps. The chase replaces DUP with LD1D, a different dependency chain, so chase minus control ({c4['ns'] - RT_NS[0]:.2f} ns at 4 KiB) is a derived number, not the memory latency and not a proven floor [table 4.1; CME-plan.md section 2.2].")}''')
rep('''<li>CME L1 chase: {c4['ns']:.2f} ns here at 4 KiB against {BENCH['cme_l1']} ns (asimov-bench run 3969, as quoted in est_chip_time.py); the register round trip, which asimov-bench did not separate, is {RT_NS[0]:.1f} ns of it.</li>''',
'''<li>CME L1 chase: {c4['ns']:.2f} ns here at 4 KiB against {BENCH['cme_l1']} ns (asimov-bench run 3969, as quoted in est_chip_time.py). The DUP/LASTB control, which asimov-bench did not run, reads {RT_NS[0]:.1f} ns; chase minus control is {c4['ns'] - RT_NS[0]:.2f} ns (derived).</li>''')
rep('''<li><span class="ok">settled</span> The floor of a CME dependent load is the {RT_NS[0]:.1f} ns register round trip ({RT_CYC[0]:.0f} CME cycles); a 4 KiB chase adds {c4['ns'] - RT_NS[0]:.2f} ns.</li>''',
'''<li><span class="ok">settled</span> The DUP/LASTB register control reads {RT_NS[0]:.1f} ns per hop ({RT_CYC[0]:.0f} CME cycles) in all {len(RT)} reps, and the 4 KiB chase {c4['ns']:.1f} ns. Their difference is "chase minus control", a derived number; what part of a chase hop is memory latency is Insufficient data.</li>''')
# ---- R2: fills are not demand misses
rep('''("refills per load", "PMU events 0x03 (L1D refill), 0x17 (L2D refill), 0xA2 (L3D read refill) divided by the loads of the timed walk. 1.00 means every load missed that level and filled one line."),''',
'''("refills per load", "PMU events 0x03 (L1D refill), 0x17 (L2D refill), 0xA2 (L3D read refill) divided by the loads of the timed walk. 1.00 means one fill of that level per load. A fill can be a demand miss or a prefetch, so the count does not say which loads missed, and a useful prefetch can replace a later demand fill and leave the count near one."),''')
rep('''f"The dense controls count {min(min(ALL5D[c]['l2']) for c in ALL5D):.4f} to {max(max(ALL5D[c]['l2']) for c in ALL5D):.4f} L2 and {min(min(ALL5D[c]['l3']) for c in ALL5D):.4f} to {max(max(ALL5D[c]['l3']) for c in ALL5D):.4f} L3 refills per load: one line per load, no prefetched members. The sparse all-five rows count''',
'''f"The dense controls count {min(min(ALL5D[c]['l2']) for c in ALL5D):.4f} to {max(max(ALL5D[c]['l2']) for c in ALL5D):.4f} L2 and {min(min(ALL5D[c]['l3']) for c in ALL5D):.4f} to {max(max(ALL5D[c]['l3']) for c in ALL5D):.4f} L3 refills per load: one fill per load at each level. The counters cannot tell a demand fill from a prefetch fill, so whether every load was a demand miss is Insufficient data. The sparse all-five rows count''')
rep('''So the sparse best is a bound from above on the demand latency, not a tighter measurement than the dense one [latency-ocm-region*-cpu*.csv].")}''',
'''So a sparse pass time is the complete-call elapsed time divided by 64 hops, and how much of it is demand-only OCM latency is Insufficient data [latency-ocm-region*-cpu*.csv].")}''')
rep('''<p><span class="gap">Insufficient data</span> How much of the sparse excess is the clock bracket, how much the L1 TLB misses and how much the extra L2 refills cannot be separated from these rows. A sparse chain with 16 KiB or 64 KiB pages, or a dense chain with the prefetcher disabled, would separate them.</p>''',
'''<p><span class="gap">Insufficient data</span> How much of the sparse excess is the clock bracket, how much the L1 TLB misses and how much the extra L2 refills cannot be separated from these rows, and neither the dense nor the sparse rows give a demand-only OCM latency. A boot with the prefetchers disabled would remove the prefetch term, and larger OCM pages the translation term; each addresses one factor, and only both together would give a demand-only number.</p>''')
rep('''<li><span class="ok">settled</span> The dense all-five OCM chase is clean (1.00 refills per load at L1, L2 and L3) and repeats within {max(abs(x) for x in dense_vs_run2):.2f} ns; it is the OCM latency row to quote: {min(ALL5D[c]['best'] for c in ALL5D):.1f} to {max(ALL5D[c]['best'] for c in ALL5D):.1f} ns from the four DSUs.</li>''',
'''<li><span class="ok">settled</span> The dense all-five OCM chase repeats run 2 within {max(abs(x) for x in dense_vs_run2):.2f} ns and counts 1.00 fills per load at L1, L2 and L3; it is the OCM chase row to quote: {min(ALL5D[c]['best'] for c in ALL5D):.1f} to {max(ALL5D[c]['best'] for c in ALL5D):.1f} ns from the four DSUs. Whether every fill was a demand miss is Insufficient data (section 6).</li>''')
rep('''<li><span class="gap">open</span> Per-region OCM latency free of prefetch and TLB effects needs either a prefetcher-off boot or larger OCM pages.</li>''',
'''<li><span class="gap">open</span> A demand-only OCM latency needs both a prefetcher-off boot (the prefetch term) and larger OCM pages (the translation term); either alone removes one factor.</li>''')
rep('''The one fix in this run, sparse OCM chains, did not give cleaner per-region OCM latencies, so the dense all-five control row is the OCM latency to quote.''',
'''The one fix in this run, sparse OCM chains, did not give tighter per-region OCM latencies, so the dense all-five control row is the OCM chase row to quote.''')
# ---- R9: the core prefetch events
rep('''A per-pass count of prefetch requests (the core's 0x2000-range prefetch events, not opened here) would test it.</p>''',
'''A per-pass count of prefetch refills would test it: the C1-Nano's L2D_CACHE_REFILL_HWPRF (0x81BD, L2 refills made by hardware prefetchers) and its per-prefetcher refill events (0x00D9 correlating, 0x00DA spatial, 0x00DB offset, 0x010F stride, 0x0110 TLB prefetcher) [Arm C1-Nano TRM, event list]. Whether each counts on this image has to be checked by its counts, since the kernel opens any event number.</p>''')
# ---- R6: CPU placement
rep('''    ("C1-Nano, DSU", "The Arm core and its two-core cluster (DynamIQ Shared Unit). The hemisphere has 5 DSUs, CPUs 0 to 9. CPUs 2 to 9 are reserved for the tests: the scheduler places no task there unless pinned (isolcpus=2-9), their timer tick stops while one task runs (nohz_full=2-9) and device interrupts go elsewhere (irqaffinity=0-1). CPUs 0 and 1 (DSU 0) are the housekeeping CPUs, where the scheduler runs everything else, the interrupts arrive and the tick work of the other cores is done. Every core still runs its own page faults and system calls."),''',
'''    ("C1-Nano, DSU", "The Arm core and its two-core cluster (DynamIQ Shared Unit). The hemisphere has 5 DSUs, CPUs 0 to 9. Device interrupts are routed to CPUs 0 and 1 (irqaffinity=0-1); the scheduler places no unpinned task on CPUs 2 to 9 (isolcpus=2-9) and their periodic tick stops while one task runs (nohz_full=2-9). The init started run_all.sh pinned to CPU 2, so the scripts, the shell and the counter helper ran on CPU 2 (cmncount sets no affinity of its own) and each measured program pinned itself to its --cpu. Every core takes its own timer and per-CPU interrupts, and a program's page faults and system calls run on its own core [Jesse's run 3 README, The run and CPU placement]."),''')
rep('''"DSU 0 port at (1,2), CPUs 0 and 1: the housekeeping CPUs. The scheduler may place any task here (isolcpus=2-9 keeps it off the test cores), device interrupts are routed here (irqaffinity=0-1) and the timer-tick work of the nohz_full cores is done here. Every core still runs its own page faults and system calls."''',
'''"DSU 0 port at (1,2), CPUs 0 and 1: where device interrupts are routed (irqaffinity=0-1) and where the scheduler may place unpinned tasks. The scripts and the counter helper ran pinned to CPU 2; each measured program pinned itself to its --cpu; every core runs its own timer interrupts, page faults and system calls."''')
rep('''"CPU 0, 1 (housekeeping)"''', '''"CPU 0, 1 (device interrupts)"''')
# ---- R7: command-wide mesh counts
rep('''f"Requests received at the region's home node over the whole command [cmn-counts.csv]. The flushed 8 MiB CME chase put {FLUSH_SPREAD[0]:,} to {FLUSH_SPREAD[-1]:,} requests on each of the five nodes (within {100 * (FLUSH_SPREAD[-1] / FLUSH_SPREAD[0] - 1):.1f} %), so the CME's traffic leaves the cluster and spreads evenly.")''',
'''f"Requests received at the region's home node over the whole command (buffer fill, chain build, warm-up, flushes, controls and timed walks together) [cmn-counts.csv]. The flushed 8 MiB CME command put {FLUSH_SPREAD[0]:,} to {FLUSH_SPREAD[-1]:,} requests on each of the five nodes (within {100 * (FLUSH_SPREAD[-1] / FLUSH_SPREAD[0] - 1):.1f} %): the command's traffic as a whole is spread evenly by the address hash. The two timed walks are 262,144 hops of it, so these counts do not measure the CME's own traffic.")''')
rep('''<span class="hyp">hypothesis</span> The extra requests are the CME's refills above one per load (prefetches), seen at the home node. The flushed 8 MiB CME chase spread its {sum(FLUSH_SPREAD):,} requests evenly over the five nodes, so the CME's traffic does leave the cluster and is hashed like the core's.</p>''',
'''<span class="hyp">hypothesis</span> The extra requests are the CME's refills above one per load (prefetches), seen at the home node; the CME outer-refill event is the direct evidence that CME refills come from outside the cluster, with the demand-against-prefetch limit of section 5. The flushed 8 MiB CME command spread its {sum(FLUSH_SPREAD):,} requests evenly over the five nodes, which fits the address hash; the counts cover the whole command, not the CME's timed loads alone.</p>''')
# ---- R10: three overgeneralisations
rep('''the proof that the events are real is their counts: both refill events read 0.0000 in the no-memory control rows and nonzero wherever the CME loads memory [cme-latency-*.csv].</li>''',
'''the proof that the events are real is their counts: both refill events read 0.0000 in every no-memory control rep; the outer event is nonzero in all {CME_TIMED} timed load rows, and the inner event in {CME_TIMED - CME_INNER_ZERO} of them (zero on {CME_INNER_ZERO} OCM passes, which service from outside the cluster fits) [cme-latency-*.csv].</li>''')
rep('''<li><b>Clock.</b> The CME ran on the core's 2 GHz clock: CME cycles per core cycle read {min(CME_RATIO):.4f} to {max(CME_RATIO):.4f} on the CME latency rows [cme-latency-dram-*.csv].</li>''',
'''<li><b>Clock.</b> The CME ran on the core's 2 GHz clock: CME cycles per core cycle read {min(CME_RATIO):.4f} to {max(CME_RATIO):.4f} on the DRAM chase rows of 65,536 loads or more [cme-latency-dram-*.csv]. A short span reads lower, because the core's cycle count includes work outside the streaming span: the one slow cme-call rep ({CALL_OUT['ns']:.1f} ns per call) counted {CALL_OUT['c1']:.1f} CME cycles against {CALL_OUT['cyc']:.1f} core cycles per call, a ratio of {CALL_OUT_RATIO:.2f}.</li>''')
rep('''{fig(f_spread, f"The 7 CME passes of a region spread {min(cme_region_spread):.1f} to {max(cme_region_spread):.1f} ns, more than the core's {min(spread[:5]):.1f} to {max(spread[:5]):.1f} ns from CPU 2.",''',
'''{fig(f_spread, f"The 7 CME passes of a region spread {min(cme_region_spread):.1f} to {max(cme_region_spread):.1f} ns; the core's 7 passes from CPU 2 spread {min(spread[:5]):.1f} to {max(spread[:5]):.1f} ns. By region the CME spread is smaller for OCM0 and OCM1 and larger for OCM2 to OCM4.",''')
# ---- R3 (CME map and text) and R8 (left column order)
rep('''    f_map = mesh_map(left=[("CME L1, 64 KiB per DSU (4-way)", f"{CLV[0]['ns']:.1f} ns at 4 KiB (register round trip {RT_NS[0]:.1f} ns)", C["cme"]),
                           ("DSU L3, 256 KiB (core L1 and L2 not on this path)", f"{[d for d in CLV if d['size'] == 131072][0]['ns']:.1f} ns at 128 KiB; no clear step at 64 KiB", "#e9f1fb"),
                           ("SLC, 3.75 MiB over five home nodes", f"{[d for d in CLV if d['size'] == 2097152][0]['ns']:.1f} ns (2 MiB fresh chain); core {SLC[2]['best']:.1f}", "#fdeee6"),
                           ("DRAM (emulator memory)", f"{[d for d in CLV if d['kind'] == 'flushed'][0]['ns']:.1f} ns (8 MiB flushed); core {[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f}", "#f1f1ee")],''',
'''    f_map = mesh_map(left=[("CME L1, 64 KiB per DSU (4-way)", f"{CLV[0]['ns']:.1f} ns at 4 KiB; register control {RT_NS[0]:.1f} ns", C["cme"]),
                           ("DSU L3, 256 KiB (core L1, L2 bypassed)", f"{[d for d in CLV if d['size'] == 131072][0]['ns']:.1f} ns at 128 KiB (serving level not measured)", "#e9f1fb"),
                           ("mesh: to the home node that owns the line", "the grid on the right; one hop per crosspoint", "#f9f9f7"),
                           ("Home node: SLC (3.75 MiB) or OCM", f"{[d for d in CLV if d['size'] == 2097152][0]['ns']:.1f} ns at 2 MiB (level not measured); core {SLC[2]['best']:.1f}", "#fdeee6"),
                           ("DRAM behind the home node (emulator memory)", f"{[d for d in CLV if d['kind'] == 'flushed'][0]['ns']:.1f} ns at 8 MiB flushed; core {[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f}", "#f1f1ee")],''')
rep('''    f_map = mesh_map(left=[("L1, 32 KiB per core", f"{LV4[0]['ns']:.1f} ns (4 KiB chase)", "#e9f1fb"),
                           ("L2, 128 KiB per DSU", f"{[d for d in LV4 if d['size'] == 131072][0]['ns']:.1f} ns (128 KiB chase)", "#e9f1fb"),
                           ("L3, 256 KiB per DSU", f"{[d for d in LV4 if d['size'] == 196608][0]['ns']:.1f} ns at 192 KiB (mixed L2, L3 and mesh)", "#e9f1fb"),
                           ("SLC, 3.75 MiB over five home nodes", f"{SLC[2]['best']:.1f} ns (2 MiB fresh chain)", "#fdeee6"),
                           ("DRAM (emulator memory)", f"{[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f} ns (8 MiB flushed)", "#f1f1ee")],''',
'''    f_map = mesh_map(left=[("L1, 32 KiB per core", f"{LV4[0]['ns']:.1f} ns (4 KiB chase)", "#e9f1fb"),
                           ("L2, 128 KiB per DSU", f"{[d for d in LV4 if d['size'] == 131072][0]['ns']:.1f} ns (128 KiB chase)", "#e9f1fb"),
                           ("L3, 256 KiB per DSU", f"{[d for d in LV4 if d['size'] == 196608][0]['ns']:.1f} ns at 192 KiB (mixed L2, L3 and mesh)", "#e9f1fb"),
                           ("mesh: to the home node that owns the line", "the grid on the right; one hop per crosspoint", "#f9f9f7"),
                           ("Home node: SLC (3.75 MiB) or OCM", f"{SLC[2]['best']:.1f} ns (2 MiB fresh chain, in the SLC)", "#fdeee6"),
                           ("DRAM behind the home node (emulator memory)", f"{[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f} ns (8 MiB flushed)", "#f1f1ee")],''')
rep('''        svg.text(20, y + 8, "then the mesh (right): the home node that owns the line", 10, "start", C["muted"])''', '''        pass''')
rep('''    for Y in range(6): svg.text(cx(5) + 28, cy(Y) + 4, f"y={Y}", 10, "start", C["muted"])''', '''    for Y in range(6): svg.text(cx(5) + 46, cy(Y) + 4, f"y={Y}", 10, "start", C["muted"])''')
rep('''<p>The left column is the CME's path outward: its own L1, then the DSU's L3, then the mesh. The core's L1 and L2 are not on it. The label under each home node is the CME's best sparse chase of that region beside CPU 2's own.</p>''',
'''<p>The left column is the CME's path outward: its own L1, then the DSU's L3, then the mesh to the home node (SLC or OCM), with DRAM behind the home node. The core's L1 and L2 are not on it. The chase times written in the boxes are measured at a footprint; which level served them is not measured, because the two CME refill events cannot tell demand from prefetch (section 5). The label under each home node is the CME's best sparse chase of that region beside CPU 2's own.</p>''')
rep('''<p>The left column is the path one load takes from CPU 2 outward, with this run's time at each level.''', '''<p>The left column is the path one load takes from CPU 2 outward (cluster caches, then the mesh to the home node, with DRAM behind it), with this run's chase time at the footprint that reads from each level.''')
rep('''then holds through the L3, the SLC and DRAM while the chase latency rises''', '''then holds at every larger footprint while the chase latency rises''')
rep('''<li><span class="ok">settled</span> One core moves {min(d['read'] for d in big):.0f} to {max(d['read'] for d in big):.0f} GB/s of reads and {min(d['write'] for d in big):.0f} to {max(d['write'] for d in big):.0f} GB/s of writes through the CME from the L3 outward,''',
'''<li><span class="ok">settled</span> One core moves {min(d['read'] for d in big):.0f} to {max(d['read'] for d in big):.0f} GB/s of reads and {min(d['write'] for d in big):.0f} to {max(d['write'] for d in big):.0f} GB/s of writes through the CME at every footprint from 160 KiB to 32 MiB,''')
# ---- small 1: match the two CPU 2 controls by position
rep('''        for d in a:
            if d["mode"] != "best": continue
            m = [e for e in b if e["mode"] == "best" and e["size"] == d["size"]]
            if m and d["lines"] == [e for e in a if e["size"] == d["size"]][0]["lines"]:
                same_chain = ("sparse" not in open(R4 + f).readline()) or "sparse=0" in open(R4 + f).readline()
                COMPARE.append(dict(file=f, what=f"{kib(d['size'])} chase" if "size" in d else "", run3=d["ns"], run2=m[0]["ns"], unit="ns", same=same_chain))''',
'''        seen = collections.Counter()
        for d in a:
            if d["mode"] != "best": continue
            k = seen[d["size"]]; seen[d["size"]] += 1   # the k-th best row of this size matches the k-th in run 2 (the two CPU 2 controls share one file)
            m = [e for e in b if e["mode"] == "best" and e["size"] == d["size"]]
            if len(m) > k:
                same_chain = ("sparse" not in open(R4 + f).readline()) or "sparse=0" in open(R4 + f).readline()
                what = f"{kib(d['size'])} chase" + (" (counted)" if "control" in f and k == 0 else " (uncounted)" if "control" in f else "")
                COMPARE.append(dict(file=f, what=what, run3=d["ns"], run2=m[k]["ns"], unit="ns", same=same_chain))''')
# ---- small 2: links in the sources
rep('''<li>results/membench-jibin-004/ (run 3, commit ba834c0, 2026-11-03) and results/membench-jibin-002/ (run 2, commit 8ae533c, 2026-11-02): every number on this page is read from their CSV files by gen_run3.py.</li>
<li>Jesse's README files in those directories: platform facts, chip time, firmware, the hang guard, the disassembly estimate for the bandwidth program's pass loop.</li>
<li>asimov-memory-hierarchy.html: the run 2 report, whose format this page follows.</li>
<li>The companion page asimov-cme-perf.html: the same loads and stores through the CME.</li>''',
'''<li><a href="results/membench-jibin-004/results/19700101T000000Z/">results/membench-jibin-004/</a> (run 3, commit ba834c0, 2026-11-03) and <a href="results/membench-jibin-002/results/19700101T000000Z/">results/membench-jibin-002/</a> (run 2, commit 8ae533c, 2026-11-02): every number on this page is read from their CSV files by <a href="gen_run3.py">gen_run3.py</a>.</li>
<li>Jesse's README files, <a href="results/membench-jibin-004/README.md">run 3</a> and <a href="results/membench-jibin-002/README.md">run 2</a>: platform facts, chip time, firmware, the hang guard, the disassembly estimate for the bandwidth program's pass loop.</li>
<li><a href="asimov-memory-hierarchy.html">asimov-memory-hierarchy.html</a>: the run 2 report, whose format this page follows.</li>
<li>The companion page <a href="asimov-cme-perf.html">asimov-cme-perf.html</a>: the same loads and stores through the CME.</li>''')
rep('''<li>results/membench-jibin-004/ (run 3, commit ba834c0, 2026-11-03): every number on this page is read from its CSV files by gen_run3.py; the core twins are the same run's core rows.</li>
<li>Jesse's run 3 README: platform facts, the SCP's CME lines, the kernel's SME lines, the chip time, the CME power analysis and the pass-loop disassembly estimate.</li>
<li>CME-plan.md and codex-review-CME-plan.md: the test design, the counter events and their caveats, the asimov-bench reference values (runs 3969 and 4045 as quoted in est_chip_time.py).</li>
<li>asimov-c1nano-perf.html: the companion page for the core; asimov-memory-hierarchy.html: the run 2 report whose format both pages follow.</li>''',
'''<li><a href="results/membench-jibin-004/results/19700101T000000Z/">results/membench-jibin-004/</a> (run 3, commit ba834c0, 2026-11-03): every number on this page is read from its CSV files by <a href="gen_run3.py">gen_run3.py</a>; the core twins are the same run's core rows.</li>
<li><a href="results/membench-jibin-004/README.md">Jesse's run 3 README</a>: platform facts, the SCP's CME lines, the kernel's SME lines, the chip time, the CME power analysis and the pass-loop disassembly estimate.</li>
<li><a href="CME-plan.md">CME-plan.md</a> and <a href="codex-review-CME-plan.md">codex-review-CME-plan.md</a>: the test design, the counter events and their caveats, the asimov-bench reference values (runs 3969 and 4045 as quoted in <a href="est_chip_time.py">est_chip_time.py</a>); <a href="cme_kern.S">cme_kern.S</a>: the kernels.</li>
<li><a href="asimov-c1nano-perf.html">asimov-c1nano-perf.html</a>: the companion page for the core; <a href="asimov-memory-hierarchy.html">asimov-memory-hierarchy.html</a>: the run 2 report whose format both pages follow.</li>''')
rep('''Those core rows repeat run 2 within 2.56 % (asimov-c1nano-perf.html, section 2.1 and table 4.8).''', '''Those core rows repeat run 2 within 2.56 % (<a href="asimov-c1nano-perf.html">asimov-c1nano-perf.html</a>, section 2.1 and table 4.8).''')
open(p, "w").write(s); print("patched")
