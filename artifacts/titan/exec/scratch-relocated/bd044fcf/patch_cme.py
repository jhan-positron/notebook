#!/usr/bin/env python3
"""Patch gen_perf_cme.py for run 6 (boots F1 and F2): data lookups, glossary, tables, figures, sections 2.2, 5.2, 6.1, open items."""
import sys
path = "/home/jhan/workspace/titan/cache-perf/asimov/gen_perf_cme.py"
s = open(path).read()

def rep(start, end, new, keep_end=True):
    """replace from the unique line that starts with `start` up to (not including) the unique `end` anchor"""
    global s
    assert s.count(start) == 1, ("start", start[:60], s.count(start))
    assert s.count(end) == 1, ("end", end[:60], s.count(end))
    i, j = s.index(start), s.index(end)
    assert i < j, (start[:40], end[:40])
    s = s[:i] + new + s[j:]

def sub(old, new):
    global s
    assert s.count(old) == 1, ("sub", old[:70], s.count(old))
    s = s.replace(old, new)

# ---------------------------------------------------------------- module docstring and lookups
sub('(cited where used) and gen_run3.BENCH (asimov-bench values). The sections keep the subjects and order of the run 3 page.\n"""',
    '(cited where used) and gen_run3.BENCH (asimov-bench values). The sections keep the subjects and order of the run 3 page.\n'
    'Run 6 (gen_run6: boot F1, the L3 on with the prefetchers on and the whole CME set; boot F2, the L3 on with the prefetchers off) is\n'
    'joined in: the bandwidth sections now show F1 with run 3 beside it, section 5.2 the L3-served load on F2, section 6.1 the cost per call.\n"""')
sub("# per-call cost of the CME kernels (run 3 rows): a line through the 16 and 48 KiB rows, time per pass against bytes (two points, est.)\n",
    '''# run 6: boots F1 (the L3 on, prefetchers on, the whole CME set) and F2 (the L3 on, prefetchers off) [gen_run6]
F1, F2 = p.F1, p.F2; C1, C2, K1 = F1["cme"], F2["cme"], F1["core"]
CLV1 = {(d["size"], d["kind"]): d for d in C1["CLV"]}; CLV2 = {(d["size"], d["kind"]): d for d in C2["CLV"]}
CL3_1 = {(d["size"], d["kind"]): d for d in C1["CL3"]}; CL3_2 = {(d["size"], d["kind"]): d for d in C2["CL3"]}
CBW1 = {d["size"]: d for d in C1["CBW"]}; CBW2 = {d["size"]: d for d in C2["CBW"]}; ASM1 = {d["size"]: d for d in C1["CBW_ASM"]}; ASM2 = {d["size"]: d for d in C2["CBW_ASM"]}
NAR1 = {d["size"]: d for d in C1["NARROW"]}; NAR2 = {d["size"]: d for d in C2["NARROW"]}
ONE1 = {d["size"]: d for d in K1["ONE"]}
COCM1, COCM2 = C1["COCM"], C2["COCM"]; FORM1, FORM2 = C1["FORM"], C2["FORM"]; CC1, CC2 = C1["CALLCOST"], C2["CALLCOST"]
L3FIT = F2["L3FIT"]; OCMBW1, COCMBW1, COCMBW2 = K1["OCMBW"], C1["COCMBW"], C2["COCMBW"]
L3_SIZES = (98304, 131072, 196608, 262144, 393216)
F2_L3 = [CLV2[(s, "repeat")] for s in L3_SIZES]            # F2's chains that outgrow the CME L1 and fit the L3: every refill a demand refill
L3_SERVED = (min(d["ns"] for d in F2_L3[2:]), max(d["ns"] for d in F2_L3[2:]))   # 192 to 384 KiB, where most refills are L3 hits by the exploratory events
RT_6 = C2["RT_NS"][0]
L1S = (4096, 8192, 16384, 24576)
BCLV = {(d["size"], d["kind"]): d for d in BB["CLV"]}; ECLV = {(d["size"], d["kind"]): d for d in CL}
_refills = lambda e: f"{e['cme_l1d_refill_outer']:.2f} / {e['cme_l1d_refill_rd']:.2f} / {e['cme_l1d_refill_hwprf']:.2f}"
F2_OCM_RNG = (min(COCM2[r]["best"] for r in range(5)), max(COCM2[r]["best"] for r in range(5)))
F1_OCM_RNG = (min(COCM1[r]["best"] for r in range(5)), max(COCM1[r]["best"] for r in range(5)))
F2_OCM_OUTER = (min(COCM2[r]["emean"]["cme_l1d_refill_outer"] for r in range(5)), max(COCM2[r]["emean"]["cme_l1d_refill_outer"] for r in range(5)))
SINGLE_RD = [FORM1[("single", "read")]["rows"][s]["agg"] for s in L1S] + [ASM1[49152]["read"]["agg"]]   # the single-call read at 4 to 48 KiB, F1
SINGLE_WR = [FORM1[("single", "write")]["rows"][s]["agg"] for s in L1S] + [ASM1[49152]["write"]["agg"]]
BPC6 = 0.5   # bytes per CME cycle per GB/s at 2 GHz
F1_PAIR_W = max(d["agg"] for d in K1["PAIR"] if d["kernel"] == "write")
# per-call cost of the CME kernels (run 3 rows): a line through the 16 and 48 KiB rows, time per pass against bytes (two points, est.)
''')
sub('R3_LABEL = "run 3 (the L3 off), not repeated with the L3 on"', 'R3_LABEL = "run 3 (the L3 off)"')

# ---------------------------------------------------------------- glossary and the boots table
sub('''    ("E / C", "Boot E's ns per load divided by boot C's on the same row. The two boots ran the same commit, build and kernel, and only the SCP differs, so the ratio isolates the L3 [Jesse's boot E README, Against boot C]."),
]''', '''    ("E / C", "Boot E's ns per load divided by boot C's on the same row. The two boots ran the same commit, build and kernel, and only the SCP differs, so the ratio isolates the L3 [Jesse's boot E README, Against boot C]."),
    ("boot F1, boot F2 (run 6)", "Run 6 ran commit 0c190a1 as two boots on boot E's SCP. F1: TF-A 0.35.0, the prefetchers on, the whole run_all.sh (the core rows and every CME row with the L3 on, 137 commands). F2: boot B's TF-A 0.35.0-pfoff.1, the data prefetchers of the cores and of the CMEs off, run_cme.sh (the CME rows, 70 commands) [Jesse's F1 and F2 READMEs]."),
    ("bracket, in span", "Two times per --cme row from run 6 on. The bracket is the clock read before and after the call, as before. In span is the clock read inside the streaming span (after SMSTART, before SMSTOP). Bracket minus span is the call's cost outside the span: the register save and restore, SMSTART, SMSTOP, the call and the return."),
    ("looped form, single-call form", "The bandwidth test's two forms of an L1 row: one call of the kernel per pass (looped, cme-bandwidth-l1-passes.csv) or every pass of a rep inside one call and one streaming span (single-call, --asm-passes, cme-bandwidth-l1-asmpasses.csv). The no-fold read drops the looped read's end-of-call sum. The DSB ST write adds a store barrier before SMSTOP."),
    ("L3-event rows, snoop", "Run 6's exploratory CME events 0x328E (CME L3 hits), 0x328F (misses) and 0x3290 (refills) on the chain rows [cme-latency-dram-small-l3.csv, -large-l3.csv]. By Jesse's reading of the RTL, 0x3290 equals the outer refill event and 0x328E counts the refills the DSU's L3 supplied, so miss minus refill is the refills a core's cache in the cluster supplied (called a snoop here, a derived number). No independent control validates that reading yet."),
]''')
sub("    q = p.RUN3\n", '''    for x in ("F1", "F2"):
        q = p.PLATFORM[x]
        rows.append([f"boot {x} (run 6)", f"membench-jibin-{q['run_id']}", q["date"], q["commit"], q["scp"], q["tfa"], "on" if q["pf_on"] else "off", "4 KiB", f"on ({q['pwrstat'][0]})", f"{q['chip_s']:.3f} s", str(q["commands"])])
    q = p.RUN3
''')

# ---------------------------------------------------------------- tables
rep("    t1 = table(", "    t2 = table(", '''    t1 = table(["Footprint", "Chain", "Core ns (E)", "CME ns (E)", "CME minus core", "CME F1 ns (run 6, L3 on)", "CME F2 ns (prefetchers off)", "F2 inner / outer refills", "CME run 3 ns", "CME boot C ns", "E / C", "Inner (0x327D)", "Outer (0x327E)", "Demand read (0x3280)", "Prefetch (0x32B2)", "Core reads from (E)"],
               [[kib(d["size"]), KIND[d["kind"]], fmt(d["core"], 3), fmt(d["ns"], 3), fmt(d["ns"] - d["core"], 1), fmt(CLV1[(d["size"], d["kind"])]["ns"], 3) if (d["size"], d["kind"]) in CLV1 else "-", fmt(CLV2[(d["size"], d["kind"])]["ns"], 3) if (d["size"], d["kind"]) in CLV2 else "-",
                 f"{CLV2[(d['size'], d['kind'])]['emean']['cme_l1d_refill_inner']:.2f} / {CLV2[(d['size'], d['kind'])]['emean']['cme_l1d_refill_outer']:.2f}" if (d["size"], d["kind"]) in CLV2 else "-",
                 fmt(d["ns3"], 3), fmt(d["nsC"], 3), f"{d['ratio']:.3f}", fmt(EM(d, "inner"), 2), fmt(EM(d, "outer"), 2), fmt(EM(d, "rd"), 2), fmt(EM(d, "hwprf"), 2), p.level_name_e(d["size"], d["kind"]).replace("8 MiB sequential chain", "8 MiB chain")] for d in CL],
               f"Boot E, CPU 2 with CPU 3 offline, ns per load of the best rep, refills per load as the pass mean over the timed reps [cme-latency-dram-small.csv, -large.csv, -flushed.csv, -seq.csv and the core's latency-dram-*.csv of membench-jibin-010; run 3's cme-latency-*.csv of 004; boot C's of 007]. "
               f"Run 6: F1 (the L3 on, prefetchers on) and F2 (the L3 on, prefetchers off) ran the same command lines [cme-latency-*.csv of 011 and 012]; neither run 6 nor run 3 ran the address-order row. On F2 every refill is a demand refill (prefetch refills {C2['PF_RNG'][1]:.4f} per load on all {C2['N_CHAIN_ROWS']} chain rows), so its inner and outer columns say where each load's line came from. "
               f"Controls on boot E: cme-roundtrip {RT_E[0]:.3f} to {RT_E[1]:.3f} ns per load ({RT_CYC_E[0]:.1f} to {RT_CYC_E[1]:.1f} CME cycles) in all {len(E['RT'])} reps, the same {RT_3[0]:.3f} to {RT_3[1]:.3f} ns on run 3 and {C1['RT_NS'][0]:.3f} to {C2['RT_NS'][1]:.3f} ns on F1 and F2 ({C1['RT_SPAN'][0]:.3f} in span). "
               f"cme-call {CALL_NS_E[0]:.1f} to {CALL_NS_E[-1]:.1f} ns per call in {len(CALLS_E)} reps (run 3: {g.CALL_NS[0]:.1f} to {g.CALL_NS[-2]:.1f} in {len(g.CALL) - 1} of {len(g.CALL)} reps, one rep {g.CALL_NS[-1]:.1f}). On F1 and F2 the same call reads {C1['CALL_NS'][0]:.1f} to {C2['CALL_NS'][1]:.1f} ns by the bracket and {C1['CALL_SPAN'][0]:.1f} to {C2['CALL_SPAN'][1]:.2f} ns in span: run 6's two clock reads inside the span add about {C1['CALL_NS'][0] - CALL_NS_E[0]:.0f} ns to this one-instruction call (section 6.1).")
''')
rep("    t2 = table(", "    t3 = table(", '''    t2 = table(["Region", "Distance from DSU 1", f"Core best ns, {ONE_PER_PAGE} (E)", "Core L3 refills per load (E)", f"CME best ns, {ONE_PER_PAGE} (E)", f"CME median, {ONE_PER_PAGE} (E)", "CME best, every line (E)", f"CME best, {ONE_PER_PAGE} at varied offsets (E)", f"CME outer / demand / prefetch per load (E, {ONE_PER_PAGE})",
                "CME best, F1 (run 6, L3 on)", "CME best, F2 (prefetchers off)", "F2 outer / demand / prefetch per load", f"CME best, {ONE_PER_PAGE}, run 3", f"CME best, {ONE_PER_PAGE}, boot C", "CME read GB/s (F1, L3 on)", "Core read GB/s (F1)", "CME read GB/s (run 3, L3 off)", "Core read GB/s (run 3, L3 off)"],
               [[f"OCM{o['region']} (node {NODE_OF_REGION[o['region']]})", f"{o['dist']} xp", fmt(CORE_SP[o["region"]]["E"]["best"], 3), fmt(CORE_SP[o["region"]]["E"]["l3"], 2), fmt(o["E"]["sparse"], 3), fmt(o["E"]["median"], 2), fmt(o["E"]["dense"], 3), fmt(o["E"]["vary"], 3),
                 f"{o['E']['outer']:.2f} / {o['E']['rd']:.2f} / {o['E']['pf']:.2f}", fmt(COCM1[o["region"]]["best"], 3), fmt(COCM2[o["region"]]["best"], 3), _refills(COCM2[o["region"]]["emean"]), fmt(o["run3"]["best"], 3), fmt(o["C"]["sparse"], 3),
                 fmt(COCMBW1["region"][o["region"]]), fmt(OCMBW1["region"][o["region"]]), fmt(COCMBW["region"][o["region"]]), fmt(OCMBW["region"][o["region"]])] for o in CO]
               + [[f"All five, {ONE_PER_PAGE} (320 loads)", "", fmt(p.ALL5[2]["E"]["sparse"], 3), fmt(E["SPLIT_ALL5"][(2, "sparse")]["l3"], 2), fmt(CALL5_E["sparse"]["best"], 3), fmt(CALL5_E["sparse"]["median"], 2), "", "",
                   _refills(CALL5_E["sparse"]["emean"]), fmt(C1["CALL5S"]["best"], 3), fmt(C2["CALL5S"]["best"], 3), _refills(C2["CALL5S"]["emean"]), fmt(CALL5_3["sparse"]["best"], 3), fmt(p.CME_ALL5["C"]["sparse"], 3), fmt(COCMBW1["all5"]), fmt(OCMBW1["all5"]), fmt(COCMBW["all5"]), fmt(OCMBW["all5"])],
                  ["All five, every line (20,480 loads)", "", fmt(p.ALL5[2]["E"]["dense"], 3), fmt(E["SPLIT_ALL5"][(2, "dense")]["l3"], 2), fmt(CALL5_E["dense"]["best"], 3), fmt(CALL5_E["dense"]["median"], 2), "", "",
                   _refills(CALL5_E["dense"]["emean"]), fmt(C1["CALL5D"]["best"], 3), fmt(C2["CALL5D"]["best"], 3), _refills(C2["CALL5D"]["emean"]), fmt(CALL5_3["dense"]["best"], 3), fmt(p.CME_ALL5["C"]["dense"], 3), "", "", "", ""],
                  ["Streaming write, all five", "", "", "", "", "", "", "", "", "", "", "", "", "", fmt(COCMBW1["write"]), fmt(OCMBW1["write"]), fmt(COCMBW["write"]), fmt(OCMBW["write"])]],
               f"Boot E, CPU 2 and its CME, OCM mapped in 4 KiB pages. Chain shapes: {ONE_PER_PAGE} at one offset (64 loads per pass), {ONE_PER_PAGE} at a different offset per page (varied offsets, 64 loads), every line of the region (4,096 loads). Best of 7 passes (2 for the every-line chains), with the counters as pass means per load [cme-latency-ocm-region*.csv, -dense.csv, -vary.csv, cme-latency-ocm-all5*.csv and the core's rows of the same footprints of 010; run 3's cme-latency-ocm-*.csv of 004; boot C's of 007]. "
               f"Run 6: F1 and F2 ran the same {ONE_PER_PAGE} and every-line rows and the OCM bandwidth rows [cme-latency-ocm-*.csv, cme-bandwidth-ocm-*.csv, bandwidth-ocm-*.csv of 011 and 012]. On F2 every refill is a demand refill from outside the cluster ({F2_OCM_OUTER[0]:.2f} to {F2_OCM_OUTER[1]:.2f} outer per load on the per-region rows), so the F2 column is the demand-only OCM latency through the CME. "
               f"On boot E only {CORE_L3_RNG[0]:.2f} to {CORE_L3_RNG[1]:.2f} of the loads in the core's {ONE_PER_PAGE} rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so these values are below the true OCM latency. The core's OCM number to quote is the all-five row over every line, {p.ALL5[2]['E']['dense']:.3f} ns [latency-ocm-all5-dense-cpu2.csv]. "
               f"The CME's {ONE_PER_PAGE} rows count {E_INNER_RNG[0]:.2f} to {E_INNER_RNG[1]:.2f} inner refills per load, so through the CME the OCM rows are not served by the L3. The run 3 bandwidth columns are {R3_LABEL} [cme-bandwidth-ocm-*.csv, bandwidth-ocm-*.csv of 004].")
''')
rep("    t3 = table(", "    t5 = table(", '''    def _c(size, k, boot):   # a run 6 CME sweep cell: the bracket GB/s with the in-span rate in brackets
        d = (CBW1 if boot == "F1" else CBW2)[size][k]; return f"{d['agg']:.1f} ({d['span']:.1f})"
    t3 = table(["Buffer", "Core read (F1)", "CME read (F1, in span)", "CME read (F2, prefetchers off)", "CME read (run 3, L3 off)", "Core write (F1)", "CME write (F1, in span)", "CME write (run 3)", "Core copy (F1)", "CME copy (F1, in span)", "CME copy (run 3)", "Capacity reading, L3 on (hypothesis): read and write; copy"],
               [[kib(d["size"]), fmt(ONE1[d["size"]]["read"]) if d["size"] in ONE1 else "-", _c(d["size"], "read", "F1"), _c(d["size"], "read", "F2"), fmt(d["read"]), fmt(ONE1[d["size"]]["write"]) if d["size"] in ONE1 else "-", _c(d["size"], "write", "F1"), fmt(d["write"]),
                 fmt(ONE1[d["size"]]["copy"]) if d["size"] in ONE1 else "-", _c(d["size"], "copy", "F1"), fmt(d["copy"]), f"{p.bw_level_e(d['size'])}; {p.bw_level_e(2 * d['size'])}"] for d in CBW],
               f"GB/s, one thread on CPU 2 (CPU 3 offline for the CME rows), best of 3 reps, GB = 1e9 bytes. Run 6 boot F1 (the L3 on, prefetchers on) and F2 (the L3 on, prefetchers off) [cme-bandwidth-dram-1core.csv and bandwidth-dram-1core.csv of 011; cme-bandwidth-dram-1core.csv of 012], run 3 (the L3 off) beside them [cme-bandwidth-dram-1core.csv of 004]. The 160 KiB and 1 MiB rows have no core row at that size. "
               "A run 6 CME cell gives the bracket rate and, in brackets, the rate inside the streaming span. The bracket counts each call's save, SMSTART, SMSTOP and restore and run 6's two in-span clock reads, so at 16 and 48 KiB it reads below run 3's bracket while the in-span rate matches run 3 within 1 % (section 6.1). "
               "Copy reads one buffer and writes another of the same size, so its working set is twice the buffer size, and it counts bytes read plus written. The last column reads the capacities with the L3 on, a hypothesis: no bandwidth row carries a level counter.")
    t3b = table(["Buffer", "read, 256 B per instruction (F1)", "ldr16, 64 B (F1)", "ldr16 / read (F1)", "ldr16 (F2, prefetchers off)", "write, 256 B (F1)", "str16, 64 B (F1)", "str16 / write (F1)", "read (run 3)", "ldr16 (run 3)", "write (run 3)", "str16 (run 3)"],
                [[kib(d["size"]), fmt(NAR1[d["size"]]["read"]["agg"]), fmt(NAR1[d["size"]]["ldr16"]["agg"]), fmt(NAR1[d["size"]]["ldr16"]["agg"] / NAR1[d["size"]]["read"]["agg"], 3), fmt(NAR2[d["size"]]["ldr16"]["agg"]), fmt(NAR1[d["size"]]["write"]["agg"]), fmt(NAR1[d["size"]]["str16"]["agg"]), fmt(NAR1[d["size"]]["str16"]["agg"] / NAR1[d["size"]]["write"]["agg"], 3),
                  fmt(d["read"]), fmt(d["ldr16"]), fmt(d["write"]), fmt(d["str16"])] for d in NARROW],
                f"GB/s by the bracket, best rep. Run 6 boots F1 and F2 [cme-bandwidth-dram-1core.csv of 011 and 012], run 3 (the L3 off) beside them [004]. The 64-byte forms issue one vector per instruction and fold (sum) into 8 accumulators. The 256 B forms issue four vectors and fold into 16 accumulators.")
    def _frow(form, k, label):
        v1, v2 = FORM1[(form, k)], FORM2[(form, k)]
        return [label] + [f"{v1['rows'][s]['agg']:.1f} ({v1['rows'][s]['span']:.1f})" for s in L1S] + [f"{v1['fit']['a_ns']:.1f} ({v1['fit_span']['a_ns']:.1f})", f"{v1['fit']['rate']:.1f} ({v1['fit_span']['rate']:.1f})", f"{v1['fit']['resid']:.1f} ns, {'met' if v1['ok'] else 'not met'}", f"{v2['fit']['a_ns']:.1f} ({v2['fit_span']['a_ns']:.1f}); {v2['fit']['rate']:.1f}"]
    t4 = table(["Form, kernel (boot F1)"] + [f"{kib(s)} GB/s (in span)" for s in L1S] + ["Fitted cost per pass, ns (in span)", "Fitted rate GB/s (in span)", "Largest residual; the 2 % rule", "F2: cost per pass (in span); rate"],
               [_frow("looped", "read", "looped read (one call per pass)"), _frow("nofold", "read", "looped read without the fold"), _frow("single", "read", "single-call read (every pass in one call)"),
                _frow("looped", "write", "looped write"), _frow("dsb", "write", "looped write with DSB ST before SMSTOP"), _frow("single", "write", "single-call write")],
               f"Run 6's L1 rows through the CME, 5 reps, best rep, GB = 1e9 bytes; boot F1 in the size columns, F2 in the last [cme-bandwidth-l1-*.csv of 011 and 012]. The fit is the line ns per pass = a + bytes / rate through the four sizes (least squares, l1_reader.fit), by the bracket and, in brackets, in span. The 2 % rule is the core page's: the largest residual under 2 % of the smallest pass time. "
               f"The looped write's four points are not a line (residual {FORM1[('looped', 'write')]['fit']['resid']:.0f} ns), so its intercept is not a cost per call. The call-cost rows: a 1 KiB read call takes {CC1[('read', 1024)]['ns']:.1f} ns ({CC1[('read', 1024)]['span_ns']:.1f} in span) against run 3's {CALLB['read']:.1f}, a 1 KiB write call {CC1[('write', 1024)]['ns']:.1f} ns ({CC1[('write', 1024)]['span_ns']:.1f} in span) against {CALLB['write']:.1f}; writes of 2, 4 and 8 KiB per call {CC1[('write', 2048)]['ns']:.1f}, {CC1[('write', 4096)]['ns']:.1f} and {CC1[('write', 8192)]['ns']:.1f} ns per call ({CC1[('write', 2048)]['span_ns']:.1f}, {CC1[('write', 4096)]['span_ns']:.1f}, {CC1[('write', 8192)]['span_ns']:.1f} in span) [cme-bandwidth-call-cost.csv of 011].")
''')
rep("    t5 = table(", "\n    # ------------------------------------------------------------------ figures", '''    t5 = table(["Row", "Own node, CME (run 3)", "Own node, core (run 3)", "CME / core (run 3)", "Other four (CME), mean (run 3)", "Own node, CME (F1, L3 on)", "Own node, core (F1)", "CME / core (F1)"],
               [[f"OCM{r} chain, {ONE_PER_PAGE}", f"{g.ATTR_CME[r]['own']:,}", f"{g.ATTR[(2, r)]['own']:,}", fmt(g.CME_OCM_OWN_RATIO[r], 2), f"{g.ATTR_CME[r]['others_mean']:,.0f}", f"{K1['ATTR_CME'][r]['own']:,}", f"{K1['ATTR'][(2, r)]['own']:,}", fmt(K1['CME_OCM_OWN_RATIO'][r], 2)] for r in range(5)]
               + [[f"OCM{r} read", f"{g.ATTR_READ_CME[r]['own']:,}", f"{g.ATTR_READ[r]['own']:,}", fmt(g.CME_READ_OWN_RATIO[r], 2), f"{g.ATTR_READ_CME[r]['others_mean']:,.0f}", f"{K1['ATTR_READ_CME'][r]['own']:,}", f"{K1['ATTR_READ'][r]['own']:,}", fmt(K1['CME_READ_OWN_RATIO'][r], 2)] for r in range(5)],
               f"Requests received at the region's home node over the whole command (buffer fill, chain build, warm-up, flushes, controls and timed walks together): run 3, the L3 off [cmn-counts.csv of 004], and run 6 boot F1, the L3 on [cmn-counts.csv of 011]. Run 4 ran no mesh counters around a CME command. "
               f"The 8 MiB CME command with every line flushed first put {g.FLUSH_SPREAD[0]:,} to {g.FLUSH_SPREAD[-1]:,} requests on each of the five nodes on run 3 (within {100 * (g.FLUSH_SPREAD[-1] / g.FLUSH_SPREAD[0] - 1):.1f} %) and {K1['FLUSH_SPREAD'][0]:,} to {K1['FLUSH_SPREAD'][-1]:,} on F1, so the command's traffic as a whole is spread evenly by the address hash. "
               "The two timed walks are 262,144 loads of it, so these counts do not measure the CME's own traffic.")
    def _l3row(s):
        a, b = CL3_2[(s, "repeat")], CL3_1[(s, "repeat")]
        return [kib(s), fmt(a["ns"], 3), fmt(a["ns"] - RT_6, 2), fmt(a["e"]["cme_l1d_refill_inner"], 3), fmt(a["e"]["cme_l1d_refill_outer"], 3), fmt(a["hit"], 3), fmt(a["snoop"], 3), fmt(a["refill"], 3), fmt(b["ns"], 3), fmt(b["hit"], 2), fmt(b["snoop"], 2), fmt(b["refill"], 2)]
    t6 = table(["Footprint", "F2 ns per load", "minus the round-trip baseline", "F2 inner refills (0x327D)", "F2 outer refills (0x327E)", "F2 L3 hits (0x328E)", "F2 snoops (miss minus refill, derived)", "F2 L3 refills (0x3290)", "F1 ns", "F1 L3 hits", "F1 snoops", "F1 L3 refills"],
               [_l3row(s) for s in (65536,) + L3_SIZES],
               f"The chains walked many times with the exploratory L3 events, best rep, counts per load of that rep [cme-latency-dram-small-l3.csv of 012 and 011]. On F2 (the prefetchers off) every refill is a demand refill; on F1 the prefetcher's fills dominate every count. "
               f"Hit plus miss equals inner plus outer and refill equals outer in every row of both boots, so the events agree with Jesse's reading of the RTL by construction and validate nothing on their own [Jesse's F2 README, The CME L3 events]. "
               f"Least squares over F2's {L3FIT['n']} reps from 96 to 384 KiB, ns per load = a + hits x h + snoops x s + outer x o: a {L3FIT['const']:.1f}, h {L3FIT['hit']:.1f}, s {L3FIT['snoop']:.1f}, o {L3FIT['outer']:.1f} ns est. (rms {L3FIT['rms']:.2f} ns). The three columns are near-collinear (each row's counts sum to about one), so the split is a hypothesis; what the rows show without a fit is that the time falls as the L3-hit share rises.")
''')

# ---------------------------------------------------------------- figures
rep("    f_lat = line_chart(", "    f_ref = line_chart(", '''    f_lat = line_chart([dict(name="C1-Nano core, CPU 2, boot E", color=K["s1"], pts=[(d["size"], d["core"]) for d in CHASE], short="core", dy=14),
                        dict(name="CME, boot E (L3 on)", color=K["s2"], pts=[(d["size"], d["ns"], f"CME boot E {kib(d['size'])} {KIND[d['kind']]}: {d['ns']:.3f} ns, inner {EM(d, 'inner'):.2f}, outer {EM(d, 'outer'):.2f} per load") for d in CHASE], short="CME E"),
                        dict(name="CME, boot F1 (L3 on, run 6)", color=K["s4"], pts=[(d["size"], CLV1[(d["size"], d["kind"])]["ns"], f"CME boot F1 {kib(d['size'])} {KIND[d['kind']]}: {CLV1[(d['size'], d['kind'])]['ns']:.3f} ns") for d in CHASE], dash="5 4", short="CME F1", dy=-8),
                        dict(name="CME, boot F2 (L3 on, prefetchers off)", color=K["s3"], pts=[(d["size"], CLV2[(d["size"], d["kind"])]["ns"], f"CME boot F2 {kib(d['size'])} {KIND[d['kind']]}: {CLV2[(d['size'], d['kind'])]['ns']:.3f} ns, inner {CLV2[(d['size'], d['kind'])]['emean']['cme_l1d_refill_inner']:.2f}, outer {CLV2[(d['size'], d['kind'])]['emean']['cme_l1d_refill_outer']:.2f} per load") for d in CHASE], short="CME F2", dy=14),
                        dict(name="CME, run 3 (L3 off)", color=K["muted"], pts=[(d["size"], d["ns3"], f"CME run 3 {kib(d['size'])} {KIND[d['kind']]}: {d['ns3']:.3f} ns") for d in CHASE], dash="2 3", short="run 3", dy=14),
                        dict(name="CME, boot B (L3 off, prefetchers off)", color=K["s7"], pts=[(d["size"], d["nsB"], f"CME boot B {kib(d['size'])} {KIND[d['kind']]}: {d['nsB']:.3f} ns") for d in CHASE], dash="7 3", short="CME B", dy=-8)],
                       marks=((32768, "core L1 32 KiB"), (65536, "CME L1 64 KiB"), (262144, "L3 256 KiB (on)"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 75), ticks_y=[0, 15, 30, 45, 60, 75], hline=(RT_E[0], f"round-trip baseline {RT_E[0]:.1f} ns", 98304))
''')
rep("    f_bw = line_chart(", "    orows = [", '''    f_bw = line_chart([dict(name="core read, F1 (L3 on)", color=K["s1"], pts=[(s, ONE1[s]["read"]) for s in sorted(ONE1)], dash="5 4", short="core read", dy=14),
                       dict(name="CME read, F1 (L3 on)", color=K["s1"], pts=[(d["size"], d["read"]["agg"], f"CME read F1 {kib(d['size'])}: {d['read']['agg']:.2f} GB/s by the bracket, {d['read']['span']:.2f} in span") for d in C1["CBW"]], short="CME read F1"),
                       dict(name="CME read, F2 (L3 on, prefetchers off)", color=K["s1"], pts=[(d["size"], d["read"]["agg"], f"CME read F2 {kib(d['size'])}: {d['read']['agg']:.2f} GB/s") for d in C2["CBW"]], dash="2 3", short="CME read F2", dy=14),
                       dict(name="CME read, run 3 (L3 off)", color=K["muted"], pts=[(d["size"], d["read"], f"CME read run 3 {kib(d['size'])}: {d['read']:.2f} GB/s") for d in CBW], dash="2 3", short="run 3 read", dy=-8),
                       dict(name="core write, F1", color=K["s2"], pts=[(s, ONE1[s]["write"]) for s in sorted(ONE1)], dash="5 4", short="core write", dy=14),
                       dict(name="CME write, F1 (L3 on)", color=K["s2"], pts=[(d["size"], d["write"]["agg"], f"CME write F1 {kib(d['size'])}: {d['write']['agg']:.2f} GB/s by the bracket, {d['write']['span']:.2f} in span") for d in C1["CBW"]], short="CME write F1"),
                       dict(name="CME write, run 3 (L3 off)", color=K["s2"], pts=[(d["size"], d["write"], f"CME write run 3 {kib(d['size'])}: {d['write']:.2f} GB/s") for d in CBW], dash="2 3", short="run 3 write", dy=-8),
                       dict(name="CME copy, F1 (L3 on)", color=K["s3"], pts=[(d["size"], d["copy"]["agg"], f"CME copy F1 {kib(d['size'])}: {d['copy']['agg']:.2f} GB/s") for d in C1["CBW"]], short="CME copy F1"),
                       dict(name="CME copy, run 3 (L3 off)", color=K["s3"], pts=[(d["size"], d["copy"], f"CME copy run 3 {kib(d['size'])}: {d['copy']:.2f} GB/s") for d in CBW], dash="2 3", short="run 3 copy", dy=14)],
                      ylabel="GB/s by the bracket, one thread on CPU 2 (solid: run 6 boot F1, the L3 on; dotted: run 3, the L3 off, and F2; dashed: the core on F1)", marks=((65536, "CME L1 64 KiB"), (262144, "L3 256 KiB (on)"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 135), ticks_y=[0, 25, 50, 75, 100, 125])
    f_forms = dotplot([dict(label=f"read {kib(s)}", vals=[FORM1[("looped", "read")]["rows"][s]["agg"], FORM1[("nofold", "read")]["rows"][s]["agg"], FORM1[("single", "read")]["rows"][s]["agg"]]) for s in L1S]
                      + [dict(label=f"write {kib(s)}", vals=[FORM1[("looped", "write")]["rows"][s]["agg"], FORM1[("dsb", "write")]["rows"][s]["agg"], FORM1[("single", "write")]["rows"][s]["agg"]]) for s in L1S],
                      ["looped form (one call per pass)", "looped read without the fold / looped write with DSB ST", "single-call form (every pass in one call)"], [K["s2"], K["s4"], K["s1"]], unit="GB/s", xlim=(0, 140))
    _l3s = (65536, 98304, 131072, 196608, 262144, 393216, 524288, 1048576, 2097152)
    _nsk = lambda t, s: t[(s, "repeat" if s <= 393216 else "fresh")]["ns"]
    f_l3 = dotplot([dict(label=f"{kib(s)}, {KIND['repeat' if s <= 393216 else 'fresh']}", vals=[_nsk(BCLV, s), _nsk(CLV2, s), _nsk(CLV1, s), _nsk(ECLV, s)]) for s in _l3s],
                   ["boot B (L3 off, prefetchers off)", "boot F2 (L3 on, prefetchers off)", "boot F1 (L3 on, prefetchers on)", "boot E (L3 on, prefetchers on, run 4)"], [K["s7"], K["s3"], K["s4"], K["s2"]], unit="ns", xlim=(20, 60))
''')
rep("    rrows = [", "    srows = [", '''    f_ocm3 = dotplot([dict(label=f"OCM{o['region']} ({o['dist']} xp), {ONE_PER_PAGE}", vals=[o["run3"]["best"], o["B"]["sparse"], o["E"]["sparse"], COCM1[o["region"]]["best"], COCM2[o["region"]]["best"]]) for o in CO]
                     + [dict(label=f"all five, {ONE_PER_PAGE}", vals=[CALL5_3["sparse"]["best"], p.CME_ALL5["B"]["sparse"], CALL5_E["sparse"]["best"], C1["CALL5S"]["best"], C2["CALL5S"]["best"]]),
                        dict(label="all five, every line", vals=[CALL5_3["dense"]["best"], p.CME_ALL5["B"]["dense"], CALL5_E["dense"]["best"], C1["CALL5D"]["best"], C2["CALL5D"]["best"]])],
                     ["run 3 (L3 off)", "boot B (L3 off, prefetchers off)", "boot E (L3 on)", "boot F1 (L3 on, run 6)", "boot F2 (L3 on, prefetchers off)"], [K["muted"], K["s7"], K["s2"], K["s4"], K["s3"]], unit="ns", xlim=(26, 54))
''')
rep("    bwrows = [", "    f_path = cme_path_fig(", '''    bwrows = [dict(label=f"OCM{r} read from CPU 2 ({dist(2, NODE_OF_REGION[r])} xp)", a=OCMBW1["region"][r], b=COCMBW1["region"][r]) for r in range(5)] + [dict(label="all five read", a=OCMBW1["all5"], b=COCMBW1["all5"]), dict(label="all five streaming write", a=OCMBW1["write"], b=COCMBW1["write"])]
    f_ocmbw = dumbbell(bwrows, unit="GB/s", names=("core (CPU 2), boot F1 (L3 on)", "CME, boot F1 (L3 on)"), colors=(K["s1"], K["s2"]), xlim=(10, 45))
''')
# the L1 table of section 5.1: the single-call rows replace the two-point estimate
rep('''                  ["L1 read / write bandwidth, 48 KiB buffer", f"{b48['core_read']:.1f} / {b48['core_write']:.1f} GB/s (L2 for the core)"''',
    '''                  ["CME pipeline widths (hardware)"''',
    '''                  ["L1 read / write bandwidth, single-call form, 4 to 48 KiB", f"{next(d for d in p.G8_ROWS if d['form'] == 'asm' and d['kernel'] == 'read' and d['size'] == 24576)['agg']['E']:.1f} / {next(d for d in p.G8_ROWS if d['form'] == 'asm' and d['kernel'] == 'write' and d['size'] == 24576)['agg']['E']:.1f} GB/s at 24 KiB (boot E)", f"{min(SINGLE_RD):.1f} to {max(SINGLE_RD):.1f} / {min(SINGLE_WR):.1f} to {max(SINGLE_WR):.1f} GB/s", "boot F1 (run 6)", f"{BPC6 * min(SINGLE_RD):.0f} to {BPC6 * max(SINGLE_RD):.0f} / {BPC6 * min(SINGLE_WR):.0f} bytes per CME cycle: one 64-byte load per cycle, {BPC6 * max(SINGLE_WR) / 64:.2f} of a store per cycle, measured with every pass of a rep inside one call. The looped form of the same rows reads {FORM1[('looped', 'read')]['rows'][24576]['agg']:.1f} / {FORM1[('looped', 'write')]['rows'][24576]['agg']:.1f} GB/s at 24 KiB: its cost per call ({FORM1[('looped', 'read')]['fit']['a_ns']:.0f} ns for a read call) hides the rate (section 6.1). Run 3's looped rows with the L3 off: {b48['read']:.1f} / {b48['write']:.1f} GB/s at 48 KiB, {BPC * b48['write']:.0f} bytes of stores per cycle; with the L3 on the CME's stores run at {BPC6 * max(SINGLE_WR):.0f} bytes per cycle in every form (section 6)"],
''')
sub('''Measured: about 1 load and half a store per cycle. Why stores stop at half is Insufficient data: no source on disk gives the store path width"]],''',
    '''Measured (F1, single-call form): about 1 load and {BPC6 * max(SINGLE_WR) / 64:.1f} of a store per cycle with the L3 on (run 3, the L3 off: half a store). Why stores stop there is Insufficient data: no source on disk gives the store path width"]],''')
sub('''                 f"The CME L1 on its own. Boot B turns the CME prefetcher off, so its chain loads are served by the L1 without eviction. The bandwidth rows are {R3_LABEL} [cme-bandwidth-dram-1core.csv of 004]; the latency rows are boot B's [cme-latency-dram-small.csv of 006].")''',
    '''                 f"The CME L1 on its own. Boot B turns the CME prefetcher off, so its chain loads are served by the L1 without eviction (boot F2, the L3 on, reads the same {CLV2[(4096, 'repeat')]['ns']:.2f} to {CLV2[(65536, 'repeat')]['ns']:.2f} ns on these rows). The bandwidth rows are run 6 boot F1's single-call form [cme-bandwidth-l1-asmpasses.csv, cme-bandwidth-dram-1core-asmpasses.csv of 011] with run 3's looped rows beside them [cme-bandwidth-dram-1core.csv of 004]; the latency rows are boot B's [cme-latency-dram-small.csv of 006].")''')

open(path, "w").write(s); print("part 1 ok")
