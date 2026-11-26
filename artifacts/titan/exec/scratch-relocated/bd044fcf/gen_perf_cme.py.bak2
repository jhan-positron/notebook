#!/usr/bin/env python3
"""asimov-cme-perf.html: the CME page, with run 4 boot E (the DSU L3 on) as the latest data.

cme_page() -> HTML string. Every number comes from gen_perf (p: the joined data of run 3 and run 4's five boots),
gen_run3 (p.g: run 3's own rows, used for the bandwidth and mesh-counter sections that run 4 did not repeat) and
gen_run4 (p.r4: the boot tables). Nothing is typed in except the platform facts quoted from Jesse's README files
(cited where used) and gen_run3.BENCH (asimov-bench values). The sections keep the subjects and order of the run 3 page.
"""
import glob, statistics, os
import gen_perf as p
from gen_perf import (kib, fmt, table, pct, line_chart, dumbbell, strip, mesh_map, cme_path_fig, page, fig, words, dist, NODE_OF_REGION, SLC_BYTES, dotplot, stacked_h, rng)

g, r4 = p.g, p.r4
E, BC, BA, BB = p.E, p.C, p.A, p.B          # the boot tables (p.C is boot C's table, not the colour dict)
K = g.C                                      # the colour dict
RT_E = p.CONTROLS["E"]["rt"]; RT_3 = p.CONTROLS["run3"]["rt"]
RT_CYC_E = (min(d["c1"] for d in E["RT"]), max(d["c1"] for d in E["RT"]))
E_DIR = p.A_DIR + "/" + p.PLATFORM["E"]["dir"]
CALLS_E = [d for f in sorted(glob.glob(E_DIR + "cme-latency-*.csv")) for d in r4.lat(f) if d["mode"] == "cme-call"]
CALL_NS_E = sorted(d["ns"] for d in CALLS_E)
REFILL_KEYS = ("cme_l1d_refill_inner", "cme_l1d_refill_outer", "cme_l1d_refill_rd", "cme_l1d_refill_hwprf", "cme_l1d_refill_wr")
CTRL_ZERO = all(d["e"][k] == 0.0 for d in E["RT"] + CALLS_E for k in REFILL_KEYS)   # the two no-memory controls count no refill
CME_TIMED_E = [d for f in sorted(glob.glob(E_DIR + "cme-latency-*.csv")) for d in r4.lat(f) if d["mode"] not in ("cme-roundtrip", "cme-call") and d["mode"].endswith("best") is False and d["mode"].startswith("cme")]
N_TIMED_E = len(CME_TIMED_E); N_OUTER_NZ = sum(1 for d in CME_TIMED_E if d["e"]["cme_l1d_refill_outer"] > 0); N_RD_NZ = sum(1 for d in CME_TIMED_E if d["e"]["cme_l1d_refill_rd"] > 0)
N_CME_CMDS = sum(1 for c in E["CMDS"] if "--cme" in c); N_SME2 = E["SYSINFO"].count("sme2")
N_FILES_E = len(glob.glob(E_DIR + "*"))
CLOCK_E = [d["e"]["cme_cycles"] / d["ns"] for d in p.CME_LEVELS if d["kind"] in ("repeat", "fresh")]   # CME cycles per ns on the chase rows, best pass

CL = p.CME_LEVELS
def cl(size, kind="repeat"): return next(d for d in CL if d["size"] == size and d["kind"] == kind)
c4, c8, c16, c24, c32, c48, c64, c96, c128, c192, c256, c384 = (cl(s) for s in (4096, 8192, 16384, 24576, 32768, 49152, 65536, 98304, 131072, 196608, 262144, 393216))
c512, c1m, c2m, c8m, c32m = (cl(s, "fresh") for s in (524288, 1048576, 2097152, 8388608, 33554432))
cfl = next(d for d in CL if d["kind"] == "flushed"); cseq = next(d for d in CL if d["kind"] == "seq")
CHASE = [d for d in CL if d["kind"] in ("repeat", "fresh")]
EM = lambda d, k: d["emean"]["cme_l1d_refill_" + k]
EMC = lambda d, k: d["emeanC"]["cme_l1d_refill_" + k]
ratio_from48 = [p.EC_CLV_RATIO[s] for s in p.EC_CLV_RATIO if s >= 49152]
far_agree = max(abs(d["ratio"] - 1) for d in CHASE if d["kind"] == "fresh" and d["size"] >= 6291456)
B_L1 = [(s, ns) for s, ns in p.CME_B if s <= 65536]; B_96 = next(ns for s, ns in p.CME_B if s == 98304)
# boot E against run 3 on the CME chase rows
REP3 = [(d, 100 * (d["ns"] - d["ns3"]) / d["ns3"]) for d in CL if d["ns3"]]
N_REP3 = {t: sum(1 for _, c in REP3 if abs(c) <= t) for t in (1, 3, 5)}
REP3_MAX = max(REP3, key=lambda t: abs(t[1]))

# OCM through the CME on boot E, with the core's sparse rows from CPU 2 and the dense all-five rows
CO = p.CME_OCM                       # five regions sorted by distance
CORE_SP = {o["region"]: o for o in p.OCM_SPARSE if o["cpu"] == 2}
CALL5_E = E["CALL5"]; CALL5_3 = dict(sparse=g.CALL5S, dense=g.CALL5D)
E_SP_RNG = (min(o["E"]["sparse"] for o in CO), max(o["E"]["sparse"] for o in CO))
E_DN_RNG = (min(o["E"]["dense"] for o in CO), max(o["E"]["dense"] for o in CO))
R3_SP_RNG = (min(o["run3"]["best"] for o in CO), max(o["run3"]["best"] for o in CO))
CORE_SP_RNG = (min(CORE_SP[r]["E"]["best"] for r in CORE_SP), max(CORE_SP[r]["E"]["best"] for r in CORE_SP))
CORE_L3_RNG = p.SPARSE_L3_RNG_CPU2["E"]
E_RD_RNG = (min(o["E"]["rd"] for o in CO), max(o["E"]["rd"] for o in CO)); E_PF_RNG = (min(o["E"]["pf"] for o in CO), max(o["E"]["pf"] for o in CO))
E_OUTER_RNG = (min(o["E"]["outer"] for o in CO), max(o["E"]["outer"] for o in CO)); E_INNER_RNG = (min(o["E"]["inner"] for o in CO), max(o["E"]["inner"] for o in CO))
E_MED_ABOVE = [o["E"]["median"] - o["E"]["sparse"] for o in CO]
E_PASS_SPREAD = [max(q["ns"] for q in E["COCM"][o["region"]]["sparse"]["passes"]) - min(q["ns"] for q in E["COCM"][o["region"]]["sparse"]["passes"]) for o in CO]
CORE_PASS_SPREAD = [max(q["ns"] for q in E["OCM"][2][o["region"]]["sparse"]["passes"]) - min(q["ns"] for q in E["OCM"][2][o["region"]]["sparse"]["passes"]) for o in CO]
E3_RATIO = [o["E"]["sparse"] / o["run3"]["best"] for o in CO]
E_FASTEST = min(CO, key=lambda o: o["E"]["sparse"])
DN_BELOW = [o["region"] for o in CO if o["E"]["dense"] < o["E"]["sparse"]]; DN_ABOVE = [o["region"] for o in CO if o["E"]["dense"] >= o["E"]["sparse"]]
_regs = lambda rs: "OCM" + ", ".join(str(r) for r in sorted(rs))
WAKE_US = (0.1, 0.3)   # Jesse's run 3 README bounds on a fixed cost per timed span (CME power), us: not a measured row
L3HIT = {h["size"]: h for h in p.HITSET}
RV2M = next(v for v in p.READ_VARIANTS if v["kernel"] == "read" and v["size"] == 2097152)   # the core's plain one-core read at 2 MiB

# run 3's bandwidth and mesh-counter rows (not repeated with the L3 on)
CBW, NARROW, CALLB, PASS16, COCMBW, OCMBW = g.CBW, g.NARROW, g.CALLB, g.PASS16, g.COCMBW, g.OCMBW
b48 = next(d for d in CBW if d["size"] == 49152); b96 = next(d for d in CBW if d["size"] == 98304); b160 = next(d for d in CBW if d["size"] == 163840)
b32m = next(d for d in CBW if d["size"] == 33554432); b16 = next(d for d in CBW if d["size"] == 16384); big = [d for d in CBW if d["size"] >= 163840]
# per-call cost of the CME kernels (run 3 rows): a line through the 16 and 48 KiB rows, time per pass against bytes (two points, est.)
def _fit2(kernel):
    a, b = (next(d for d in CBW if d["size"] == s) for s in (16384, 49152))
    ta, tb = 16384 / a[kernel], 49152 / b[kernel]   # ns per pass: bytes / (GB/s) with GB = 1e9
    slope = (tb - ta) / (49152 - 16384)
    return dict(t16=ta, t48=tb, icpt=ta - slope * 16384, rate=1 / slope)
CALLFIT = {k: _fit2(k) for k in ("read", "write")}
CALL_1K_STORE_NS = 1024 / CALLFIT["write"]["rate"]                      # the 1 KiB of stores of one write call at the fitted rate
CALL_SWITCH_NS = statistics.mean(CALL_NS_E) - statistics.mean(d["ns"] for d in E["RT"])   # cme-call minus cme-roundtrip on boot E: register save, SMSTART, SMSTOP, restore
R3_LABEL = "run 3 (the L3 off), not repeated with the L3 on"
KIND = {"repeat": "walked many times", "fresh": "walked once", "flushed": "every line flushed first", "seq": "address order"}   # the chain kinds of the latency files, in words
_src = lambda t: t.replace("the dense OCM chains", "the OCM chains over every line")   # the shared sources list in this page's words
ONE_PER_PAGE = "one line per page"   # the OCM chain shape with one member line per 4 KiB page (the files call it sparse)
L3_ON_BOX = "DSU L3, 256 KiB (on, boot E)"

WORDS_CME_E = p.WORDS_FIRST + [
    ("CME", "The Compute Matrix Engine: Arm's C1-SME2 unit (code name Griffin). One per DSU, shared by the DSU's two cores. It executes the cores' streaming-mode (SME) instructions, with its own 64 KiB 4-way L1 data cache, its own TLB and its own hardware prefetcher. "
            "Its path to memory is CME L1, then the DSU's L3 (on and holding data on boot E, empty on runs 1 to 3 and boots A to D), then the mesh. The core's L1 and L2 are not on it [Jesse's run 3 README, CME; CME-plan.md section 1]."),
] + p.dehop([w for w in g.WORDS_CME if w[0] != "CME"]) + [
    ("CME refill events by cause", "Run 4 adds three CME events to the two of run 3: 0x3280 CME L1D refills for demand reads (the chain's own loads), 0x32B2 refills requested by the CME's hardware prefetcher, 0x3281 refills for writes. "
                                   "Inner plus outer equals demand read plus prefetch plus write on every row [asimov-cme-run4.html, section 3.1]."),
    ("round-trip baseline", "The cme-roundtrip row: the latency test's loop with the load replaced by a register move (DUP then LASTB), so it measures one core-to-CME-to-core round trip with no memory access."),
    ("chain, chain load", "The latency test walks a chain of dependent loads: each load reads the address of the next, so the loads cannot overlap. A chain load is one load of that chain, and its time is the load-to-use latency. "
                          "A chain is walked many times (later walks hit whatever cache holds it), walked once, or walked with every line flushed from the caches first. The OCM chains have one line per 4 KiB page (64 loads per pass, at one offset or at a different offset per page) or every line of the region (4,096 loads per pass)."),
    ("pass mean", "A counter value averaged over the timed passes (reps) of a row, written \"per load\". Run 3's page quoted the fastest pass. This page quotes the pass mean and says so where it differs."),
    ("E / C", "Boot E's ns per load divided by boot C's on the same row. The two boots ran the same commit, build and kernel, and only the SCP differs, so the ratio isolates the L3 [Jesse's boot E README, Against boot C]."),
]
WORDS_RUN = [w for w in p.WORDS_NEW if w[0] == "run, boot"]
GLOSS_DROP = ("chase", "repeated chase, fresh chain, flushed", "sparse chain")   # shared entries the chain entry above replaces
BEST_PASS = "A command walks its chain several times (passes, or reps); best is the fastest. A per-region OCM row has 7 passes, an all-five row over every line 2, a chain walked many times 3 reps."


def boots_table():
    cols = ["Boot", "Run", "Date", "Commit", "SCP", "TF-A", "Data prefetchers", "OCM pages", "L3 of CPU 2's cluster", "Chip time", "Commands"]
    rows = []
    for x in p.BOOTS:
        q = p.PLATFORM[x]
        rows.append([f"boot {x}", f"membench-jibin-{q['run_id']}", q["date"], q["commit"], q["scp"], q["tfa"], "on" if q["pf_on"] else "off", "64 KiB hint" if q["cont"] else "4 KiB",
                     f"on ({q['pwrstat'][0]})" if q["l3_on"] else (f"off ({q['pwrstat'][0]})" if q["pwrstat"] else "off (not read)"), f"{q['chip_s']:.3f} s", str(q["commands"])])
    q = p.RUN3
    rows.append(["run 3", f"membench-jibin-{q['run_id']}", q["date"], q["commit"], q["scp"], q["tfa"], "on", "4 KiB", "off (not read)", f"{q['chip_s']:.3f} s", str(q["commands"])])
    return table(cols, rows, "The five boots of run 4 and run 3, from gen_run4.EX and each run's README [results/membench-jibin-*/README.md]. "
                 "The L3 column is IMP_CLUSTERPWRSTAT_EL1 read on CPU 2 by the box lines of the script: 0x70 is the full-L3 mode, 0x0 the snoop-filter-only mode. Boot A and run 3 did not read it. "
                 "Every boot ran the CME test on CPU 2 with CPU 3 offline.")


def cme_page():
    # ------------------------------------------------------------------ tables
    t1 = table(["Footprint", "Chain", "Core ns (E)", "CME ns (E)", "CME minus core", "CME run 3 ns", "CME boot C ns", "E / C", "Inner (0x327D)", "Outer (0x327E)", "Demand read (0x3280)", "Prefetch (0x32B2)", "Core reads from (E)"],
               [[kib(d["size"]), KIND[d["kind"]], fmt(d["core"], 3), fmt(d["ns"], 3), fmt(d["ns"] - d["core"], 1), fmt(d["ns3"], 3), fmt(d["nsC"], 3), f"{d['ratio']:.3f}",
                 fmt(EM(d, "inner"), 2), fmt(EM(d, "outer"), 2), fmt(EM(d, "rd"), 2), fmt(EM(d, "hwprf"), 2), p.level_name_e(d["size"], d["kind"]).replace("8 MiB sequential chain", "8 MiB chain")] for d in CL],
               f"Boot E, CPU 2 with CPU 3 offline, ns per load of the best rep, refills per load as the pass mean over the timed reps [cme-latency-dram-small.csv, -large.csv, -flushed.csv, -seq.csv and the core's latency-dram-*.csv of membench-jibin-010; run 3's cme-latency-*.csv of 004; boot C's of 007]. "
               f"Run 3 had no address-order row. Controls on boot E: cme-roundtrip {RT_E[0]:.3f} to {RT_E[1]:.3f} ns per load ({RT_CYC_E[0]:.1f} to {RT_CYC_E[1]:.1f} CME cycles) in all {len(E['RT'])} reps, the same {RT_3[0]:.3f} to {RT_3[1]:.3f} ns on run 3. "
               f"cme-call {CALL_NS_E[0]:.1f} to {CALL_NS_E[-1]:.1f} ns per call in {len(CALLS_E)} reps (run 3: {g.CALL_NS[0]:.1f} to {g.CALL_NS[-2]:.1f} in {len(g.CALL) - 1} of {len(g.CALL)} reps, one rep {g.CALL_NS[-1]:.1f}).")
    t2 = table(["Region", "Distance from DSU 1", f"Core best ns, {ONE_PER_PAGE} (E)", "Core L3 refills per load (E)", f"CME best ns, {ONE_PER_PAGE} (E)", f"CME median, {ONE_PER_PAGE} (E)", "CME best, every line (E)", f"CME best, {ONE_PER_PAGE} at varied offsets (E)", f"CME outer / demand / prefetch per load (E, {ONE_PER_PAGE})", f"CME best, {ONE_PER_PAGE}, run 3", f"CME best, {ONE_PER_PAGE}, boot C", "CME read GB/s (run 3, L3 off)", "Core read GB/s (run 3, L3 off)"],
               [[f"OCM{o['region']} (node {NODE_OF_REGION[o['region']]})", f"{o['dist']} xp", fmt(CORE_SP[o["region"]]["E"]["best"], 3), fmt(CORE_SP[o["region"]]["E"]["l3"], 2), fmt(o["E"]["sparse"], 3), fmt(o["E"]["median"], 2), fmt(o["E"]["dense"], 3), fmt(o["E"]["vary"], 3),
                 f"{o['E']['outer']:.2f} / {o['E']['rd']:.2f} / {o['E']['pf']:.2f}", fmt(o["run3"]["best"], 3), fmt(o["C"]["sparse"], 3), fmt(COCMBW["region"][o["region"]]), fmt(OCMBW["region"][o["region"]])] for o in CO]
               + [[f"All five, {ONE_PER_PAGE} (320 loads)", "", fmt(p.ALL5[2]["E"]["sparse"], 3), fmt(E["SPLIT_ALL5"][(2, "sparse")]["l3"], 2), fmt(CALL5_E["sparse"]["best"], 3), fmt(CALL5_E["sparse"]["median"], 2), "", "",
                   f"{CALL5_E['sparse']['emean']['cme_l1d_refill_outer']:.2f} / {CALL5_E['sparse']['emean']['cme_l1d_refill_rd']:.2f} / {CALL5_E['sparse']['emean']['cme_l1d_refill_hwprf']:.2f}", fmt(CALL5_3["sparse"]["best"], 3), fmt(p.CME_ALL5["C"]["sparse"], 3), fmt(COCMBW["all5"]), fmt(OCMBW["all5"])],
                  ["All five, every line (20,480 loads)", "", fmt(p.ALL5[2]["E"]["dense"], 3), fmt(E["SPLIT_ALL5"][(2, "dense")]["l3"], 2), fmt(CALL5_E["dense"]["best"], 3), fmt(CALL5_E["dense"]["median"], 2), "", "",
                   f"{CALL5_E['dense']['emean']['cme_l1d_refill_outer']:.2f} / {CALL5_E['dense']['emean']['cme_l1d_refill_rd']:.2f} / {CALL5_E['dense']['emean']['cme_l1d_refill_hwprf']:.2f}", fmt(CALL5_3["dense"]["best"], 3), fmt(p.CME_ALL5["C"]["dense"], 3), "", ""],
                  ["Streaming write, all five", "", "", "", "", "", "", "", "", "", "", fmt(COCMBW["write"]), fmt(OCMBW["write"])]],
               f"Boot E, CPU 2 and its CME, OCM mapped in 4 KiB pages. Chain shapes: {ONE_PER_PAGE} at one offset (64 loads per pass), {ONE_PER_PAGE} at a different offset per page (varied offsets, 64 loads), every line of the region (4,096 loads). Best of 7 passes (2 for the every-line chains), with the counters as pass means per load [cme-latency-ocm-region*.csv, -dense.csv, -vary.csv, cme-latency-ocm-all5*.csv and the core's rows of the same footprints of 010; run 3's cme-latency-ocm-*.csv of 004; boot C's of 007]. "
               f"On boot E only {CORE_L3_RNG[0]:.2f} to {CORE_L3_RNG[1]:.2f} of the loads in the core's {ONE_PER_PAGE} rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so these values are below the true OCM latency. The core's OCM number to quote is the all-five row over every line, {p.ALL5[2]['E']['dense']:.3f} ns [latency-ocm-all5-dense-cpu2.csv]. "
               f"The CME's {ONE_PER_PAGE} rows count {E_INNER_RNG[0]:.2f} to {E_INNER_RNG[1]:.2f} inner refills per load, so through the CME the OCM rows are not served by the L3. The two bandwidth columns are {R3_LABEL} [cme-bandwidth-ocm-*.csv, bandwidth-ocm-*.csv of 004].")
    t3 = table(["Buffer", "Core read", "CME read", "Core write", "CME write", "Core copy", "CME copy", "Core capacity reading: read and write; copy"],
               [[kib(d["size"]), fmt(d["core_read"]), fmt(d["read"]), fmt(d["core_write"]), fmt(d["write"]), fmt(d["core_copy"]), fmt(d["copy"]), f"{g.bw_level(d['size'])}; {g.bw_level(2 * d['size'])}"] for d in CBW],
               f"GB/s, {R3_LABEL}. One thread on CPU 2 (CPU 3 offline for the CME rows), best of 3 reps, GB = 1e9 bytes [cme-bandwidth-dram-1core.csv, bandwidth-dram-1core.csv of 004]. The 160 KiB and 1 MiB rows have no core row at that size. "
               "Copy reads one buffer and writes another of the same size, so its working set is twice the buffer size, and it counts bytes read plus written. The last column reads the core's capacities with the L3 off (hypothesis), for read and write at the buffer size and for copy at twice it. "
               "The CME's 64 KiB L1 is smaller than the core's L1 plus L2, and no bandwidth row carries counters, so the level that served a stream is not measured for either.")
    t3b = table(["Buffer", "read (256 B per instruction)", "ldr16 (64 B)", "ldr16 / read", "write (256 B)", "str16 (64 B)", "str16 / write"],
                [[kib(d["size"]), fmt(d["read"]), fmt(d["ldr16"]), fmt(d["ldr16"] / d["read"], 3), fmt(d["write"]), fmt(d["str16"]), fmt(d["str16"] / d["write"], 3)] for d in NARROW],
                f"GB/s, {R3_LABEL} [cme-bandwidth-dram-1core.csv of 004]. The 64-byte forms issue one vector per instruction and fold (sum) into 8 accumulators. The 256 B forms issue four vectors and fold into 16 accumulators.")
    t4 = table(["Control", "Bound on ns per call", "What it includes"],
               [["read, 1 KiB per call, 4,096 calls", fmt(CALLB["read"], 1), "SMSTART, register save, 1 KiB of loads and the fold, SMSTOP"], ["write, 1 KiB per call, 4,096 calls", fmt(CALLB["write"], 1), "the same with 1 KiB of stores"]],
               f"Elapsed time over calls, best rep, {R3_LABEL} [cme-bandwidth-call-cost.csv of 004]. A 16 KiB read pass takes {PASS16:.0f} ns, so up to {100 * CALLB['read'] / PASS16:.0f} % of the 16 KiB read row is call cost (Jesse's fit for the write rows: 0.01 ns per pass plus a fixed cost per rep).")
    t5 = table(["Row", "Own node, CME", "Own node, core", "CME / core", "Other four (CME), mean"],
               [[f"OCM{r} chain, {ONE_PER_PAGE}", f"{g.ATTR_CME[r]['own']:,}", f"{g.ATTR[(2, r)]['own']:,}", fmt(g.CME_OCM_OWN_RATIO[r], 2), f"{g.ATTR_CME[r]['others_mean']:,.0f}"] for r in range(5)]
               + [[f"OCM{r} read", f"{g.ATTR_READ_CME[r]['own']:,}", f"{g.ATTR_READ[r]['own']:,}", fmt(g.CME_READ_OWN_RATIO[r], 2), f"{g.ATTR_READ_CME[r]['others_mean']:,.0f}"] for r in range(5)],
               f"Requests received at the region's home node over the whole command (buffer fill, chain build, warm-up, flushes, controls and timed walks together), {R3_LABEL}: run 4 ran no mesh counters around a CME command [cmn-counts.csv of 004]. "
               f"The 8 MiB CME command with every line flushed first put {g.FLUSH_SPREAD[0]:,} to {g.FLUSH_SPREAD[-1]:,} requests on each of the five nodes (within {100 * (g.FLUSH_SPREAD[-1] / g.FLUSH_SPREAD[0] - 1):.1f} %), so the command's traffic as a whole is spread evenly by the address hash. "
               "The two timed walks are 262,144 loads of it, so these counts do not measure the CME's own traffic.")

    # ------------------------------------------------------------------ figures
    f_map = mesh_map(left=[("CME L1, 64 KiB per DSU (4-way)", f"{c4['ns']:.1f} ns at 4 KiB; round-trip baseline {RT_E[0]:.1f} ns", K["cme"]),
                           ([L3_ON_BOX, f"core L3 hit about {min(p.L3_HIT_EST.values()):.1f} to {max(p.L3_HIT_EST.values()):.1f} ns est."], f"CME {c8['ns']:.1f} ns at 8 KiB; {100 * c8['inner_share']:.1f} % of refills from in-cluster", "#e9f1fb"),
                           ("mesh: to the home node that owns the line", "the grid on the right; one step per crosspoint", "#f9f9f7"),
                           (["5 home nodes (HN-S)", "SLC 768 KiB each (12 ways), \"L4\" cache", "OCM 256 KiB each (4 ways)", "addressable SRAM"], f"{c2m['ns']:.1f} ns at 2 MiB (level not measured); core {c2m['core']:.1f}", "#fdeee6"),
                           ("DRAM, behind the home node (emulator)", f"{cfl['ns']:.1f} ns at 8 MiB, every line flushed first; core {cfl['core']:.1f}", "#f1f1ee")],
                     node_labels={NODE_OF_REGION[o["region"]]: [f"CME {o['E']['sparse']:.1f} ns", f"core {CORE_SP[o['region']]['E']['best']:.1f} ns"] for o in CO},
                     paths=[(1, NODE_OF_REGION[r], K["s2"], "") for r in range(5)], title_dsu="DSU 1: CPU 2 in streaming mode, CPU 3 offline")
    f_lat = line_chart([dict(name="C1-Nano core, CPU 2, boot E", color=K["s1"], pts=[(d["size"], d["core"]) for d in CHASE], short="core", dy=14),
                        dict(name="CME, boot E (L3 on)", color=K["s2"], pts=[(d["size"], d["ns"], f"CME boot E {kib(d['size'])} {KIND[d['kind']]}: {d['ns']:.3f} ns, inner {EM(d, 'inner'):.2f}, outer {EM(d, 'outer'):.2f} per load") for d in CHASE], short="CME E"),
                        dict(name="CME, boot C (L3 off, same commit)", color=K["s3"], pts=[(d["size"], d["nsC"], f"CME boot C {kib(d['size'])} {KIND[d['kind']]}: {d['nsC']:.3f} ns") for d in CHASE], dash="5 4", short="CME C", dy=-8),
                        dict(name="CME, run 3 (L3 off)", color=K["muted"], pts=[(d["size"], d["ns3"], f"CME run 3 {kib(d['size'])} {KIND[d['kind']]}: {d['ns3']:.3f} ns") for d in CHASE], dash="2 3", short="run 3", dy=14),
                        dict(name="CME, boot B (CME prefetcher off)", color=K["s7"], pts=[(d["size"], d["nsB"], f"CME boot B {kib(d['size'])} {KIND[d['kind']]}: {d['nsB']:.3f} ns") for d in CHASE], dash="7 3", short="CME B", dy=-8)],
                       marks=((32768, "core L1 32 KiB"), (65536, "CME L1 64 KiB"), (262144, "L3 256 KiB (on)"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 75), ticks_y=[0, 15, 30, 45, 60, 75], hline=(RT_E[0], f"round-trip baseline {RT_E[0]:.1f} ns", 98304))
    f_ref = line_chart([dict(name="hardware prefetch refills (0x32B2)", color=K["s2"], pts=[(d["size"], EM(d, "hwprf"), f"{kib(d['size'])}: prefetch {EM(d, 'hwprf'):.2f} per load") for d in CHASE], short="prefetch"),
                        dict(name="demand read refills (0x3280)", color=K["s1"], pts=[(d["size"], EM(d, "rd"), f"{kib(d['size'])}: demand read {EM(d, 'rd'):.2f} per load") for d in CHASE], short="demand", dy=14),
                        dict(name="inner refills (0x327D, from inside the cluster)", color=K["s7"], pts=[(d["size"], EM(d, "inner"), f"{kib(d['size'])}: inner {EM(d, 'inner'):.2f} per load") for d in CHASE], dash="5 4", short="inner", dy=-8),
                        dict(name="outer refills (0x327E, from outside the cluster)", color=K["s3"], pts=[(d["size"], EM(d, "outer"), f"{kib(d['size'])}: outer {EM(d, 'outer'):.2f} per load") for d in CHASE], dash="5 4", short="outer", dy=14)],
                       ylabel="CME L1 refills per load on boot E, pass mean over the timed reps", marks=((65536, "CME L1 64 KiB"), (262144, "L3 256 KiB (on)")), ylim=(0, 18), ticks_y=[0, 3, 6, 9, 12, 15, 18])
    f_io = stacked_h([dict(label=f"{kib(d['size'])}, boot {x}", parts=[(EM(d, "inner") if x == "E" else EMC(d, "inner"), K["s1"], "inner (0x327D)"), (EM(d, "outer") if x == "E" else EMC(d, "outer"), K["s3"], "outer (0x327E)")])
                      for d in (c8, c16, c32, c64, c128, c256) for x in ("C", "E")], unit="refills per load")
    f_bw = line_chart([dict(name="core read", color=K["s1"], pts=[(d["size"], d["core_read"]) for d in CBW if d["core_read"]], dash="5 4", short="core read", dy=14),
                       dict(name="CME read", color=K["s1"], pts=[(d["size"], d["read"]) for d in CBW], short="CME read"),
                       dict(name="core write", color=K["s2"], pts=[(d["size"], d["core_write"]) for d in CBW if d["core_write"]], dash="5 4", short="core write", dy=14),
                       dict(name="CME write", color=K["s2"], pts=[(d["size"], d["write"]) for d in CBW], short="CME write"),
                       dict(name="core copy", color=K["s3"], pts=[(d["size"], d["core_copy"]) for d in CBW if d["core_copy"]], dash="5 4", short="core copy", dy=14),
                       dict(name="CME copy", color=K["s3"], pts=[(d["size"], d["copy"]) for d in CBW], short="CME copy")],
                      ylabel="GB/s, one thread on CPU 2, run 3 with the L3 off (dashed: core, solid: CME)", marks=((65536, "CME L1 64 KiB"), (262144, "L3 256 KiB (no data on run 3)"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 135), ticks_y=[0, 25, 50, 75, 100, 125])
    orows = [dict(label=f"OCM{o['region']} ({o['dist']} xp), {ONE_PER_PAGE}", a=CORE_SP[o["region"]]["E"]["best"], b=o["E"]["sparse"]) for o in CO]
    orows += [dict(label=f"all five, {ONE_PER_PAGE}", a=p.ALL5[2]["E"]["sparse"], b=CALL5_E["sparse"]["best"]), dict(label="all five, every line", a=p.ALL5[2]["E"]["dense"], b=CALL5_E["dense"]["best"])]
    f_ocm = dumbbell(orows, names=("core (CPU 2), boot E, best pass", "CME, boot E, best pass"), colors=(K["s1"], K["s2"]), xlim=(16, 48))
    rrows = [dict(label=f"OCM{o['region']} ({o['dist']} xp), {ONE_PER_PAGE}", a=o["run3"]["best"], b=o["E"]["sparse"]) for o in CO]
    rrows += [dict(label=f"all five, {ONE_PER_PAGE}", a=CALL5_3["sparse"]["best"], b=CALL5_E["sparse"]["best"]), dict(label="all five, every line", a=CALL5_3["dense"]["best"], b=CALL5_E["dense"]["best"])]
    f_ocm3 = dumbbell(rrows, names=("CME, run 3 (L3 off), best pass", "CME, boot E (L3 on), best pass"), colors=(K["muted"], K["s2"]), xlim=(26, 48))
    srows = [dict(label=f"CME OCM{o['region']} ({o['dist']} xp), boot E", vals=[q["ns"] for q in E["COCM"][o["region"]]["sparse"]["passes"]], best=o["E"]["sparse"], extra=[(CORE_SP[o["region"]]["E"]["best"], K["s1"], "core best")]) for o in CO]
    srows += [dict(label=f"CME all five, {ONE_PER_PAGE}", vals=[q["ns"] for q in CALL5_E["sparse"]["passes"]], best=CALL5_E["sparse"]["best"], extra=[(p.ALL5[2]["E"]["sparse"], K["s1"], "core best")])]
    f_spread = strip(srows, color=K["s2"], markers=((K["s1"], "core best (square)"),), xlim=(16, 48))
    bwrows = [dict(label=f"OCM{r} read from CPU 2 ({dist(2, NODE_OF_REGION[r])} xp)", a=OCMBW["region"][r], b=COCMBW["region"][r]) for r in range(5)] + [dict(label="all five read", a=OCMBW["all5"], b=COCMBW["all5"]), dict(label="all five streaming write", a=OCMBW["write"], b=COCMBW["write"])]
    f_ocmbw = dumbbell(bwrows, unit="GB/s", names=("core (CPU 2), run 3", "CME, run 3"), colors=(K["s1"], K["s2"]), xlim=(10, 26))
    f_path = cme_path_fig(meas=[
        ("Round-trip baseline, DUP then LASTB: the core-to-CME link both ways, no memory access", f"{RT_E[0]:.1f} ns ({RT_CYC_E[0]:.0f} CME cycles)"),
        ("Chain load at 4 KiB, fits the CME L1D (core's own loads at 4 KiB, from its L1)", f"{c4['ns']:.1f} ns (core {c4['core']:.1f})"),
        ("Chain load at 256 KiB, fits the DSU L3, on for boot E (core at 256 KiB: an L2 and L3 mix)", f"{c256['ns']:.1f} ns (core {c256['core']:.1f})"),
        ("2 MiB chain walked once, fits the SLC (core at 2 MiB)", f"{c2m['ns']:.1f} ns (core {c2m['core']:.1f})"),
        (f"Chain with {ONE_PER_PAGE} over one OCM region, best of five regions (core, same rows)", f"{E_SP_RNG[0]:.1f} to {E_SP_RNG[1]:.1f} ns (core {CORE_SP_RNG[0]:.1f} to {CORE_SP_RNG[1]:.1f})"),
        ("8 MiB with every line flushed first, served beyond the SLC (core, same row)", f"{cfl['ns']:.1f} ns (core {cfl['core']:.1f})"),
    ])
    # gen_run3's path figure writes run 3's L3 state into two labels; boot E's L3 is on
    f_path = f_path.replace("L3 cache 256 KiB: no data on this run", "L3 cache 256 KiB: on (boot E)").replace("the line returns the same way into the CME L1D (0x327E outer refill); the L3 held no data on this run", "the line returns the same way: into the L3, then the CME L1D (0x327E outer refill)")
    f_path = f_path.replace("Run 3 measurements along this path", "Boot E measurements along this path")
    assert "held no data" not in f_path and "no data on this run" not in f_path and "Run 3 measurements" not in f_path

    plat = p.PLATFORM["E"]
    body = f"""
<div class="short"><p><b>Short version.</b> Through the CME on boot E (the DSU L3 on) a dependent load costs {c4['ns']:.1f} ns at 4 KiB, against a {RT_E[0]:.1f} ns round-trip baseline (a register move with no memory access). From 8 KiB on the chain load climbs as the CME's prefetcher fills its L1, and the L3 on does not lower it ({p.EC_CLV_RATIO[8192]:.3f} times boot C's at 8 KiB, {min(ratio_from48):.3f} to {max(ratio_from48):.3f} from 48 to 384 KiB). The bandwidth rows are run 3's with the L3 off, not repeated: {min(d['read'] for d in big):.1f} to {max(d['read'] for d in big):.1f} GB/s of reads and {min(d['write'] for d in big):.1f} to {max(d['write'] for d in big):.1f} GB/s of writes through the CME from 160 KiB to 32 MiB.</p></div>
<ul>
<li><b>Latency (boot E).</b> {c4['ns']:.1f} ns at 4 KiB (chain load minus round-trip baseline {c4['ns'] - RT_E[0]:.2f} ns, a derived number, not the memory latency), {c8['ns']:.1f} at 8 KiB, {c16['ns']:.1f} at 16 KiB, {c64['ns']:.1f} at 64 KiB, {c256['ns']:.1f} at 256 KiB, {c32m['ns']:.1f} at 32 MiB. The core's same rows read {c4['core']:.1f}, {c8['core']:.1f}, {c16['core']:.1f}, {c64['core']:.1f}, {c256['core']:.1f} and {c32m['core']:.1f} ns (section 5). Run 3 read {c4['ns3']:.1f}, {c8['ns3']:.1f}, {c16['ns3']:.1f}, {c64['ns3']:.1f}, {c256['ns3']:.1f} and {c32m['ns3']:.1f} ns on the same CME rows. The climb from 8 KiB is the CME prefetcher's: on boot B, with that prefetcher off, the chain load reads {B_L1[0][1]:.1f} to {B_L1[-1][1]:.1f} ns up to 64 KiB. With the L3 on, {100 * c8['inner_share']:.1f} % of the CME's refills at 8 KiB come from inside the cluster (boot C, the L3 off: {100 * p.CME_INNER_SHARE['C'][8192]:.1f} %). No row gives an L3 hit time through the CME.</li>
<li><b>Bandwidth (run 3, the L3 off).</b> Reads peak at {b48['read']:.1f} GB/s at 48 KiB. Writes hold {min(d['write'] for d in CBW):.1f} to {max(d['write'] for d in CBW):.1f} GB/s at every footprint, 32 bytes per cycle (section 6).</li>
<li><b>OCM (boot E).</b> {E_SP_RNG[0]:.1f} to {E_SP_RNG[1]:.1f} ns per region through the CME (best of the chains with {ONE_PER_PAGE}) against {CORE_SP_RNG[0]:.1f} to {CORE_SP_RNG[1]:.1f} ns for the core's own loads of the same chains. Part of those loads are served by the L3 on this boot, so the core's values are below the true OCM latency (section 7). The all-five chain over every line reads {CALL5_E['dense']['best']:.1f} ns through the CME against the core's {p.ALL5[2]['E']['dense']:.1f} ns (section 7). The OCM bandwidth rows are run 3's: {COCMBW['all5']:.1f} GB/s read through the CME against the core's {OCMBW['all5']:.1f}.</li>
<li><b>Open.</b> No CME bandwidth row has run with the L3 on. No CME event names the level that served a load, so the L3 hit time through the CME is unmeasured (section 10).</li>
</ul>

<h2 id="words">1. Words used here</h2>
{words(WORDS_CME_E + WORDS_RUN + [(k, BEST_PASS if k == "best, pass, rep" else v) for k, v in p.words_core() if k not in [n for n, _ in p.WORDS_NEW + WORDS_CME_E] + list(GLOSS_DROP)])}

<h2 id="run">2. The run and the platform</h2>
<ul>
<li><b>Where and when.</b> One emulated Asimov hemisphere on the GA13 Palladium (image hemi_rtws_tlm), {plat['date']} UTC, as one job (run_followup.sh). {plat['chip_s']:.3f} s of chip time. All {plat['commands']} commands exited 0 and all {N_FILES_E} files came back. No file carries a "# perf:" line [Jesse's boot E README, the run; log.txt of 010 checked here].</li>
<li><b>Platform.</b> SCP {plat['scp']} (a rebuild of the stock SCP that stages the full-L3 mode for every cluster) and TF-A {plat['tfa']}, the data prefetchers on, /dev/ocm in 4 KiB pages. IMP_CLUSTERPWRSTAT_EL1 read {plat['pwrstat'][0]} on CPU 2's cluster before and after the hit-set command: the L3 of CPUs 2 and 3 was in full mode. The clusters of CPUs 4 to 9 were not read. Core 2.000 GHz against a 1 GHz timer. DRAM is an emulator memory, not LPDDR5X, so no DRAM number is silicon-like [Jesse's boot E README, Platform and L3 power].</li>
<li><b>Code.</b> cache-mem-perf commit {plat['commit']}, the same commit, binaries and kernel as boot C (membench-jibin-{p.BOOT_RUN_ID['C']}, the L3 off), so the E against C comparison isolates the L3 [Jesse's boot E README, Against boot C]. Run 3 ran commit {p.RUN3['commit']}.</li>
</ul>
{boots_table()}
<ul>
<li><b>CME conditions.</b> The kernel found SME2 with a 64-byte vector length, and /proc/cpuinfo lists sme2 on all {N_SME2} CPUs [sysinfo.txt and dmesg.txt of 010, checked by this script]. CPU 3 was offline for the whole CME test ({N_CME_CMDS} commands with --cme), so the CME served one core [log.txt of 010].</li>
<li><b>Clock.</b> The CME ran on the core's 2 GHz clock: the CME cycle count per load divided by the ns per load reads {min(CLOCK_E):.3f} to {max(CLOCK_E):.3f} cycles per ns on the {len(CLOCK_E)} chain rows of boot E [cme-latency-dram-small.csv, -large.csv of 010]. Run 3's reading was {min(g.CME_RATIO):.4f} to {max(g.CME_RATIO):.4f} CME cycles per core cycle on its DRAM chain rows.</li>
<li><b>Counter validity.</b> perf_cov reads 1.0000 on every counted row of boot E ({len(E['COV_ROWS'])} rows) and no file carries a "# perf:" line, so no event was refused. Both no-memory controls ({len(E['RT'])} cme-roundtrip and {len(CALLS_E)} cme-call reps) count {"0.0000 in every refill event" if CTRL_ZERO else "a nonzero refill in at least one rep"}. The outer event is nonzero in {N_OUTER_NZ} of the {N_TIMED_E} timed CME load reps and the demand-read event in {N_RD_NZ} [cme-latency-*.csv of 010].</li>
</ul>

<h3 id="changes">2.1 What changed from run 3 to run 4 boot E for the CME</h3>
<ul>
<li><b>The L3 holds data.</b> On run 3 (and on boots A to D) the L3 of CPUs 2 to 9 was in snoop-filter-only mode: the stock SCP stages the full L3 for cluster 0 only, and the hit counters read 0 L3 hits per load. Boot E's rebuilt SCP turns it on. The core's hit set (the 64 KiB to 512 KiB chains run with the L2 and L3 hit events) counts {L3HIT[196608]['l3_hit']:.2f}, {L3HIT[262144]['l3_hit']:.2f} and {L3HIT[393216]['l3_hit']:.2f} L3 read hits per load at 192, 256 and 384 KiB. The data read fell from boot C's {L3HIT[196608]['nsC']:.3f}, {L3HIT[262144]['nsC']:.3f} and {L3HIT[393216]['nsC']:.3f} ns to {L3HIT[196608]['ns']:.3f}, {L3HIT[262144]['ns']:.3f} and {L3HIT[393216]['ns']:.3f} ns [latency-dram-small-l3.csv of 010 and 007; Jesse's boot E README, L3 power].</li>
<li><b>Three more CME events.</b> Run 4 counts 0x3280 (demand read refills), 0x32B2 (hardware prefetch refills) and 0x3281 (write refills) beside run 3's 0x3246, 0x327D and 0x327E, so the CME's refills split by cause (table 4.1, section 5).</li>
<li><b>Rows added.</b> The 8 MiB chain in address order through the CME, and two more chain shapes of each OCM region (every line, and {ONE_PER_PAGE} at varied offsets) beside the {ONE_PER_PAGE} chain (table 4.2).</li>
<li><b>Rows not repeated.</b> Every CME bandwidth row (the one-core sweep, the 64-byte forms, the call-cost rows, the OCM bandwidth) and the mesh counters around CME commands. Sections 4.3 to 4.6, 6 and 8 keep run 3's values, labelled {R3_LABEL}.</li>
<li><b>The core rows are from boot E.</b> Every core number beside a CME number on this page is boot E's own cache-test row of the same footprint, so the comparison carries no firmware or image difference. The core page is <a href="asimov-c1nano-perf.html">asimov-c1nano-perf.html</a>.</li>
<li><b>Repeat check against run 3.</b> Of the {len(REP3)} CME chain rows run 3 also ran, {N_REP3[1]} read within 1 %, {N_REP3[3]} within 3 % and {N_REP3[5]} within 5 %. The largest change is {REP3_MAX[1]:+.1f} % at {kib(REP3_MAX[0]['size'])} ({KIND[REP3_MAX[0]['kind']]}), a row where the L3 on changes where the prefetcher's fills come from (section 5). The CME rows of boot A, run 3's configuration, are the repeatability reference [asimov-cme-run4.html, section 3.3].</li>
<li><b>The other boots on this page.</b> Boot C (the same commit as E, the L3 off) is the boot that isolates the L3. Boot B (the CME and core prefetchers off through a TF-A hook) gives the demand-only reading. Boot A (run 3's configuration) is the reference of the run 4 pages.</li>
</ul>

<h2 id="map">3. The hemisphere map, CME path</h2>
<p>The left column is the CME's path outward: its own L1, then the DSU's L3 (on and holding data on boot E), then the mesh to the home node (SLC or OCM), with DRAM behind the home node. The core's L1 and L2 are not on it. The chain-load times written in the boxes are measured at a footprint. Which level served them is not measured, because no CME event names the source of a refill (section 5). The label under each home node is the CME's best chain with {ONE_PER_PAGE} over that region beside CPU 2's own, both from boot E.</p>
{fig(f_map, f"Through the CME every footprint costs more: {c4['ns']:.1f} ns against the core's {c4['core']:.1f} at 4 KiB, {c2m['ns']:.1f} against {c2m['core']:.1f} at 2 MiB (chain walked once), {cfl['ns']:.1f} against {cfl['core']:.1f} at 8 MiB with every line flushed.", f"The round-trip baseline (DUP then LASTB, no memory access) reads {RT_E[0]:.1f} ns per load, {RT_CYC_E[0]:.0f} CME cycles, in all {len(E['RT'])} reps of boot E. The latency test replaces DUP with LD1D, a different dependency chain, so chain load minus baseline ({c4['ns'] - RT_E[0]:.2f} ns at 4 KiB) is a derived number, not the memory latency and not a proven floor [table 4.1; CME-plan.md section 2.2].")}

<h3 id="path">3.1 The data path of one CME load</h3>
<p>The example is one load of the latency test's kernel: <code>LD1D {{z0.d}}, p0/z, [x0]</code> then <code>LASTB x0, p0, z0.d</code> in streaming mode [cme_kern.S]. Words used here: MMU (the core's memory management unit, which translates a virtual address to a physical one), GPR (a general-purpose register such as x0), PIPT (a cache indexed and tagged by physical address), SCU (the DSU's snoop control unit, which keeps the cluster's caches coherent), CHI (the Arm bus protocol between the DSU and the mesh), SBSX (the mesh bridge toward a memory controller).</p>
<ol>
<li><b>Core.</b> CPU 2 is in streaming mode. It decodes the LD1D, but does not execute it: SME instructions are decoded on the core and issued to the CME, up to three per cycle, loads and stores two per cycle [C1-Nano SOG 109590, section 2.33]. The core's MMU translates the address in x0 first, so the CME receives a physical address and never asks for a translation of its own for a load or a store [C1-SME2 TRM 107831, chapter 5]. The core's L1 data cache and L2 are not on the path.</li>
<li><b>Bridges.</b> The instruction and its physical address cross the DSU on the streaming request channel (CMEREQ). A second channel (CMETLB) carries the translation requests of the CME's prefetcher back to the core [TRM 107831, chapter 1]. There is one SME2 unit bridge between each CME and the DSU [TRM 107831, section 2.1].</li>
<li><b>CME.</b> The CME decodes, renames and issues the load to its L1 data memory system: a 64 KiB, 4-way, 16-bank, physically indexed and tagged cache with 64-byte lines and two 512-bit read paths into the vector registers, so one line fills Z0 in one transfer. A hardware prefetcher with 128 streams, indexed by instruction address, fills this L1D and the DSU L3. It works in virtual addresses and keeps its own TLB [TRM 107831, table 6-1 and sections 5 and 6.3]. LASTB then moves the last active element of Z0 into x0, and that GPR update travels back to the core, where the next LD1D waits for it (the core's event 0x3205 counts the waiting cycles) [C1-Nano TRM 107753, PMU events 0x3204 and 0x3205].</li>
<li><b>DSU L3.</b> A CME L1D miss goes to the DSU's L3 memory system: the SCU's snoop filter, which tracks the CME's L1D beside the cores' caches, and the 256 KiB L3. On a simultaneous hit in both, the L3 supplies the line [C1-DSU TRM 107804, chapter 2]. A line that comes from inside the cluster counts as an inner refill (event 0x327D). On boot E the L3 holds data: at 8 KiB the CME counts {EM(c8, 'inner'):.2f} inner and {EM(c8, 'outer'):.2f} outer refills per load, where boot C (the L3 off) counts {EMC(c8, 'inner'):.2f} and {EMC(c8, 'outer'):.2f} [cme-latency-dram-small.csv of 010 and 007]. On runs 1 to 3 and boots A to D the L3 held no data (register 0x0, 0 L3 hits per load), so the inner refills counted there were not L3 hits. Which lines that event counted, those files do not show.</li>
<li><b>Mesh, home node, DRAM.</b> An L3 miss leaves the cluster on the DSU's 256-bit CHI memory interface [DSU TRM 107804, chapter 2] and crosses the mesh from crosspoint (2,3) to the home node that owns the address, 1 crosspoint away for three of the five nodes and 3 for the other two (table 4.2). There the line is in the SLC, or in the OCM ways when the address is an OCM region, or is fetched from DRAM through the SBSX bridge. The line returning from outside the cluster fills the L3 and the CME L1D and counts as an outer refill (event 0x327E). The counter cannot say which of SLC, OCM or DRAM supplied it (section 5).</li>
</ol>
{fig(f_path, f"Every CME load crosses the core-to-CME link twice: the address goes out, the result comes back. The round-trip baseline that does only that reads {RT_E[0]:.1f} ns. The 4 KiB chain load reads {c4['ns']:.1f} ns, against {c4['core']:.1f} ns for the core's own L1 load.", f"From 4 KiB to 256 KiB the CME rows climb {c256['ns'] - c4['ns']:.1f} ns and the core's own rows {c256['core'] - c4['core']:.1f} ns. From 4 KiB to the 8 MiB row with every line flushed first they climb {cfl['ns'] - c4['ns']:.1f} ns against {cfl['core'] - c4['core']:.1f} ns. The chain load minus the baseline ({c4['ns'] - RT_E[0]:.2f} ns at 4 KiB) is a derived number: the two rows run different instruction chains, so it is not the L1D hit latency [CME-plan.md section 2.2]. The public LLVM model of the C1-Nano puts a CLASTB result (a close relative of LASTB) into a GPR at 12 cycles in streaming mode. The measured baseline is {RT_CYC_E[0]:.0f} CME cycles per load, so most of a load's time is spent outside that one instruction [refs/C1Nano-streaming-cme-instructions.s].")}

<h2 id="tables">4. Summary tables</h2>
<h3 id="t41">4.1 Latency by footprint, core against CME</h3>{t1}
<h3 id="t42">4.2 OCM through the CME</h3>{t2}
<h3 id="t43">4.3 One-core bandwidth, core against CME</h3>{t3}
<h3 id="t44">4.4 The 64-byte forms</h3>{t3b}
<h3 id="t45">4.5 Call cost</h3>{t4}
<h3 id="t46">4.6 Home-node counts, CME rows against core rows</h3>{t5}

<h2 id="f-lat">5. Latency by footprint</h2>
{fig(f_lat, f"The CME has no step at its 64 KiB L1 and none at the L3: on boot E the climb starts at 8 KiB ({c8['ns'] - c4['ns']:+.1f} ns), continues at 16 KiB ({c16['ns'] - c8['ns']:+.1f}), and the 64 to 96 KiB step is {c96['ns'] - c64['ns']:+.1f} ns. With the CME prefetcher off (boot B) the chain load stays at {B_L1[0][1]:.2f} to {B_L1[-1][1]:.2f} ns up to 64 KiB and reads {B_96:.2f} ns at 96 KiB, so the climb from 8 KiB is the prefetcher's.", f"The core steps at 48 KiB (L1), 192 KiB (the L2 and L3 mix) and 4 to 16 MiB (SLC). Against boot C (the L3 off) the CME reads {p.EC_CLV_RATIO[8192]:.3f} times at 8 KiB, {p.EC_CLV_RATIO[16384]:.3f} at 16 KiB and {min(ratio_from48):.3f} to {max(ratio_from48):.3f} from 48 to 384 KiB. Past the SLC the two boots agree within {100 * far_agree:.1f} %. Run 3's CME rows (dotted) sit within {max(abs(c) for _, c in REP3 if _['size'] >= 524288):.1f} % of boot E's from 512 KiB on. The CME's chains walked once, 512 KiB to 1 MiB ({c512['ns']:.1f} ns at 512 KiB) read below its repeated walks of 96 to 384 KiB ({c96['ns']:.1f} to {c384['ns']:.1f}), and its 8 MiB row with every line flushed first ({cfl['ns']:.1f} ns) reads below its unflushed one ({c8m['ns']:.1f}), the reverse of the core [table 4.1]. The chain load minus the round-trip baseline at 4 KiB is {c4['ns'] - RT_E[0]:.2f} ns. The 8 MiB chain in address order through the CME reads {cseq['ns']:.3f} ns on boots A, C and E alike ({p.CME_SEQ['A']:.3f}, {p.CME_SEQ['C']:.3f}, {p.CME_SEQ['E']:.3f}), with every refill a prefetch ({EM(cseq, 'hwprf'):.2f} per load) and {EM(cseq, 'rd'):.2f} demand refills: a load that hits in the CME's L1 with the prefetcher ahead of the chain (the core's same chain, and how its reads in flight overlap, is in asimov-c1nano-perf.html, section 8) [cme-latency-dram-seq.csv].")}
{fig(f_ref, f"On boot E the CME's prefetcher fills {EM(c8, 'hwprf'):.1f} lines per load at 8 KiB and {EM(c16, 'hwprf'):.1f} at 16 KiB, footprints a 64 KiB L1 should hold, and {max(EM(d, 'hwprf') for d in CHASE):.1f} per load near 96 to 384 KiB. The chain's own demand refills stay below 1 per load.", f"Pass means over the timed reps [cme-latency-dram-small.csv, -large.csv of 010]. Demand read plus prefetch equals inner plus outer within {max(abs(EM(d, 'rd') + EM(d, 'hwprf') + EM(d, 'wr') - EM(d, 'inner') - EM(d, 'outer')) for d in CHASE):.2f} per load on every row. On the OCM passes with {ONE_PER_PAGE} (every line flushed from the caches before the pass) the outer event reads {E_OUTER_RNG[0]:.2f} to {E_OUTER_RNG[1]:.2f} per load, split {E_RD_RNG[0]:.2f} to {E_RD_RNG[1]:.2f} demand and {E_PF_RNG[0]:.2f} to {E_PF_RNG[1]:.2f} prefetch: the prefetcher finds part of each load's line before the chain asks for it. Run 3's page read the counts above 1 per load as the prefetcher's traffic (a hypothesis then). Boot A's split events and boot B's prefetcher-off rows settled it [asimov-cme-run4.html, sections 4 and 8].")}
{fig(f_io, f"With the L3 on, the lines the CME's prefetcher evicts from its 64 KiB L1 come back from inside the cluster: {100 * c8['inner_share']:.1f} % of the refills at 8 KiB, {100 * c16['inner_share']:.1f} % at 16 KiB, {100 * c32['inner_share']:.1f} % at 32 KiB and {100 * c64['inner_share']:.1f} % at 64 KiB on boot E, against {100 * min(p.CME_INNER_SHARE['C'][s] for s in (8192, 16384, 32768, 65536)):.1f} to {100 * max(p.CME_INNER_SHARE['C'][s] for s in (8192, 16384, 32768, 65536)):.1f} % on boot C.", f"Pass means per load, boots C and E [cme-latency-dram-small.csv of 007 and 010]. The chain load is not faster: E reads {p.EC_CLV_RATIO[8192]:.3f} times C at 8 KiB and {p.EC_CLV_RATIO[16384]:.3f} at 16 KiB, with {EM(c16, 'inner') + EM(c16, 'outer'):.1f} refills per load in all against C's {EMC(c16, 'inner') + EMC(c16, 'outer'):.1f}, nearly all the prefetcher's on both boots. From 48 KiB on E reads {min(ratio_from48):.3f} to {max(ratio_from48):.3f} times C. No row gives the cost of one L3 hit through the CME: the prefetcher's fills set the chain-load time on both boots, and no CME event names the level that served a refill.")}

<h2 id="f-bw">6. Bandwidth by footprint</h2>
<p>This section is {R3_LABEL}. Run 4 ran no CME bandwidth row, so these numbers describe the CME with the DSU L3 holding no data [cme-bandwidth-dram-1core.csv of 004].</p>
{fig(f_bw, f"The CME reads {b48['read']:.0f} GB/s at 48 KiB and {min(d['read'] for d in big):.0f} to {max(d['read'] for d in big):.0f} GB/s from 160 KiB on. It writes {min(d['write'] for d in CBW):.0f} to {max(d['write'] for d in CBW):.0f} GB/s at every footprint, 32 bytes per cycle (run 3, the L3 off).", f"Read falls {100 * (1 - b96['read'] / b48['read']):.0f} % from 48 to 96 KiB and {100 * (1 - b160['read'] / b96['read']):.0f} % more by 160 KiB, then holds at every larger footprint while run 3's chain-load latency rises {100 * (c32m['ns3'] / c1m['ns3'] - 1):.0f} % from 1 to 32 MiB. Copy holds {min(b16['copy'], b48['copy']):.1f} to {max(b16['copy'], b48['copy']):.1f} GB/s at 16 and 48 KiB and {min(d['copy'] for d in big):.1f} to {max(d['copy'] for d in big):.1f} GB/s from 160 KiB. These rows carry no counters, so which level serves a footprint is read from the footprint [table 4.3]. Up to {100 * CALLB['read'] / PASS16:.0f} % of the 16 KiB read row is call cost [table 4.5]. Whether the L3 on changes these rates is Insufficient data: the one-core sweep through the CME has not run on boot E.")}
<p><b>Writes beside the cluster's two cores (run 3, the L3 off).</b> One CME writes a 32 MiB buffer at {g.W32:.1f} GB/s through CPU 2-3's cluster, {g.W32 / g.PAIR_W:.2f} times the {g.PAIR_W:.1f} GB/s CPUs 2 and 3 write together. <span class="hyp">hypothesis</span> If the CME's stores leave through the same cluster port, the two-core write limit is on the cores' side, not the port's. A two-core write with one of them in streaming mode would test it.</p>

<h2 id="f-ocm">7. OCM through the CME</h2>
{fig(f_ocm, f"On boot E, OCM costs {min(o['E']['sparse'] - CORE_SP[o['region']]['E']['best'] for o in CO):.1f} to {max(o['E']['sparse'] - CORE_SP[o['region']]['E']['best'] for o in CO):.1f} ns more per load through the CME than from the core on the rows with {ONE_PER_PAGE}, and {CALL5_E['dense']['best'] - p.ALL5[2]['E']['dense']:.1f} ns more on the all-five chain over every line.", f"Through the CME the per-region bests do not order by mesh distance (OCM{E_FASTEST['region']}, {E_FASTEST['dist']} crosspoint{'s' if E_FASTEST['dist'] != 1 else ''} away, is fastest at {E_FASTEST['E']['sparse']:.2f} ns). On boot E only {CORE_L3_RNG[0]:.2f} to {CORE_L3_RNG[1]:.2f} of the loads in the core's {ONE_PER_PAGE} rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so the core's values are below the true OCM latency. The CME's rows count {E_INNER_RNG[0]:.2f} to {E_INNER_RNG[1]:.2f} inner refills per load, so through the CME the OCM rows are served from outside the cluster. The all-five chain over every line reads {CALL5_E['dense']['best'] - CALL5_E['sparse']['best']:+.1f} ns against the {ONE_PER_PAGE} one through the CME, with {CALL5_E['dense']['emean']['cme_l1d_refill_outer']:.2f} outer refills per load ({CALL5_E['dense']['emean']['cme_l1d_refill_hwprf']:.2f} of them prefetches) against {CALL5_E['sparse']['emean']['cme_l1d_refill_outer']:.2f}. On the core the every-line row reads {p.ALL5[2]['E']['dense'] - p.ALL5[2]['E']['sparse']:+.1f} ns against the {ONE_PER_PAGE} one [table 4.2]. The per-region every-line rows through the CME read {E_DN_RNG[0]:.1f} to {E_DN_RNG[1]:.1f} ns, below the {ONE_PER_PAGE} best of {len(DN_BELOW)} region{'s' if len(DN_BELOW) != 1 else ''} ({_regs(DN_BELOW)}) and above it for {len(DN_ABOVE)} ({_regs(DN_ABOVE)}).")}
{fig(f_ocm3, f"Against run 3, boot E's {ONE_PER_PAGE} CME rows read {min(E3_RATIO):.2f} to {max(E3_RATIO):.2f} times run 3's by region, the all-five {ONE_PER_PAGE} chain {CALL5_E['sparse']['best'] / CALL5_3['sparse']['best']:.2f} times and the every-line one {CALL5_E['dense']['best'] / CALL5_3['dense']['best']:.2f} times.", f"Best of 7 passes (2 for the every-line chains) on each run [cme-latency-ocm-*.csv of 004 and 010]. Boot C (the L3 off, E's commit) reads {min(o['C']['sparse'] for o in CO):.2f} to {max(o['C']['sparse'] for o in CO):.2f} ns on the same {ONE_PER_PAGE} rows and {p.CME_ALL5['C']['dense']:.2f} ns on all five over every line, so the run-to-run spread of these rows is of the size of the E against run 3 change. Which part of a change is the L3's is Insufficient data without a repeat of boot E.")}
{fig(f_spread, f"The 7 CME passes of a region spread {min(E_PASS_SPREAD):.1f} to {max(E_PASS_SPREAD):.1f} ns on boot E. The core's 7 passes from CPU 2 spread {min(CORE_PASS_SPREAD):.1f} to {max(CORE_PASS_SPREAD):.1f} ns.", f"The CME rows' medians run {min(E_MED_ABOVE):.1f} to {max(E_MED_ABOVE):.1f} ns above their bests [table 4.2]. <span class='hyp'>hypothesis</span> Part of a 64-load CME pass is a fixed cost per timed span of about {WAKE_US[0]:.1f} to {WAKE_US[1]:.1f} us est. (the CME waking from dynamic power-down, or its first instructions after SMSTART). Spread over a pass that would be up to about {1000 * WAKE_US[1] / 64:.0f} ns est. per load here and under {1000 * WAKE_US[1] / 320:.1f} ns est. on the 320-load passes. Jesse's run 3 README bounds it from three views, but no row measures it directly. A row that times the first and the later passes of one span separately would decide it [Jesse's run 3 README, CME power].")}
{fig(f_ocmbw, f"The CME reads an OCM region at {min(COCMBW['region']):.1f} to {max(COCMBW['region']):.1f} GB/s, {min(COCMBW['region'][r] / OCMBW['region'][r] for r in range(5)):.2f} to {max(COCMBW['region'][r] / OCMBW['region'][r] for r in range(5)):.2f} times the core, with no step by distance. Its streaming write to OCM ({COCMBW['write']:.1f} GB/s) matches the core's ({OCMBW['write']:.1f}). These are {R3_LABEL}.", f"The CME's OCM read reps spread {min(g.cme_rep_spread):.1f} to {max(g.cme_rep_spread):.1f} % (the core's {min(g.core_rep_spread):.1f} to {max(g.core_rep_spread):.1f} %) [cme-bandwidth-ocm-*.csv, bandwidth-ocm-*.csv of 004]. Through the CME, OCM reads at {COCMBW['all5'] / b32m['read']:.2f} times its warm DRAM-buffer rate, the reverse of the core ({OCMBW['all5'] / b32m['core_read']:.2f}). These rows also differ in page size (4 KiB against 2 MiB) and in one pass with every line flushed first against warm passes, so the data do not say which costs the CME [table 4.2].")}

<h2 id="f-cmn">8. Mesh counters</h2>
<p>This section is {R3_LABEL}: run 4 ran no mesh counters around a CME command, so boot E has no CME row here [cmn-counts.csv of 004]. Where the CME's loads make most of a command's traffic, its rows put more requests on the home nodes than the core's same rows: the OCM reads {min(g.CME_READ_OWN_RATIO):.2f} to {max(g.CME_READ_OWN_RATIO):.2f} times on the region's node. The {ONE_PER_PAGE} chains, whose counts are dominated by the core-side chain build and the 7 flushes, {min(g.CME_OCM_OWN_RATIO):.2f} to {max(g.CME_OCM_OWN_RATIO):.2f} times [table 4.6]. <span class="hyp">hypothesis</span> The extra requests are the CME's refills above one per load (prefetches), seen at the home node. Boot A's split events count {E_PF_RNG[0]:.2f} to {E_PF_RNG[1]:.2f} prefetch refills per load of the {ONE_PER_PAGE} chains on boot E (table 4.2), which fits, but no run has counted the mesh around a CME command with the split events on. The 8 MiB CME command with every line flushed first spread its {sum(g.FLUSH_SPREAD):,} requests evenly over the five nodes, which fits the address hash. The counts cover the whole command, not the CME's timed loads alone.</p>

<h2 id="bench">9. Against asimov-bench's earlier CME numbers</h2>
<ul>
<li>CME L1 chain load: {c4['ns']:.2f} ns on boot E at 4 KiB (run 3 {c4['ns3']:.2f}) against {p.BENCH['cme_l1']} ns (asimov-bench run 3969, as quoted in est_chip_time.py). The round-trip baseline (DUP then LASTB), which asimov-bench did not run, reads {RT_E[0]:.1f} ns. Chain load minus baseline is {c4['ns'] - RT_E[0]:.2f} ns (derived). Boot B, with the CME prefetcher off, reads {B_L1[0][1]:.2f} to {B_L1[-1][1]:.2f} ns from 4 to 64 KiB, within {max(ns for _, ns in B_L1) - p.CONTROLS['B']['rt'][0]:.2f} ns of its {p.CONTROLS['B']['rt'][0]:.2f} ns baseline: the CME L1 load [cme-latency-dram-small.csv of 006].</li>
<li>DSU L3 through the CME: nothing on boot E levels off near asimov-bench's {p.BENCH['dsu_l3']} ns. The rows between 8 KiB and 256 KiB read {c8['ns']:.1f} to {c256['ns']:.1f} ns and climb throughout, with the L3 on. On run 3 there was no L3 level to find (the L3 held no data). On boot E the prefetcher's fills set the chain-load time (section 5), and the two tests differ in chain construction and footprint. Which difference matters is Insufficient data. A boot with the L3 on and the CME prefetcher off (boot B's TF-A with boot E's SCP) would give a load served by the L3 through the CME.</li>
<li>OCM through the CME: {E_SP_RNG[0]:.1f} to {E_SP_RNG[1]:.1f} ns per region on boot E (best of the {ONE_PER_PAGE} chains, run 3 {R3_SP_RNG[0]:.1f} to {R3_SP_RNG[1]:.1f}) against {p.BENCH['ocm']} ns. DRAM read: {b32m['read']:.1f} GB/s at 32 MiB on run 3 (the L3 off) against {p.BENCH['read_gbps']} GB/s. The core's {c4['core']:.3f} ns at 4 KiB and {c128['core']:.3f} ns at 128 KiB on boot E match asimov-bench's {p.BENCH['core_l1']} and {p.BENCH['core_l2']}.</li>
</ul>

<h2 id="open">10. Open items</h2>
<ul>
<li><span class="hyp">hypothesis</span> A fixed cost of {WAKE_US[0]:.1f} to {WAKE_US[1]:.1f} us est. per timed span (CME wake-up from dynamic power-down, Jesse's run 3 README bounds) inflates the 64-load OCM passes: on boot E the {ONE_PER_PAGE} medians run {min(E_MED_ABOVE):.1f} to {max(E_MED_ABOVE):.1f} ns above the bests (section 7). A row that times the first and the later passes of one span separately would decide it.</li>
<li><span class="gap">open</span> The bandwidth set (the one-core sweep, the 64-byte forms, the call cost, the OCM bandwidth) has not run through the CME with the L3 on. Sections 4.3 to 4.6 and 6 are run 3's. The core's plain one-core read rose from {RV2M['run3']:.1f} GB/s (run 3) to {RV2M['agg']['E']:.1f} GB/s at 2 MiB with the L3 on [bandwidth-read-prefetch.csv of 010], so the CME's rates may have moved too (why the core's rate rose is an open item of asimov-c1nano-perf.html, section 12). The measurement: the CME test script's bandwidth rows (run_cme.sh) on a boot with E's SCP. Planned: run 6 boot F1, the L3 on with the prefetchers on, not yet run [follow-up-run-plan.md, section 13].</li>
<li><span class="gap">Insufficient data</span> Which level served a CME load: no CME event names it, so SLC against DRAM through the CME (the 2 MiB chain walked once at {c2m['ns']:.1f} ns and the 8 MiB row with every line flushed first at {cfl['ns']:.1f} ns, {cfl['ns'] - c2m['ns']:.1f} ns apart, both with about one demand refill per load: {EM(c2m, 'rd'):.2f} and {EM(cfl, 'rd'):.2f}) and a load served by the L3 through the CME stay unmeasured. The measurement: a boot with the L3 on and the CME prefetcher off (boot B's TF-A with boot E's SCP), which would make every refill a demand refill. Planned: run 6 boot F2, not yet run [follow-up-run-plan.md, section 13].</li>
<li><span class="gap">open</span> The memory model's configured delay behind the rows with every line flushed first (asked of Jesse, unanswered). The L3 state of the clusters of CPUs 4 to 9 on boot E was not read (the README's reading covers CPU 2's cluster), so the CME rows of other DSUs are untested with the L3 on. No mesh counter has run around a CME command since run 3.</li>
<li><span class="gap">open</span> Two cores of one DSU in streaming mode at once (the CME is shared), and the CME with operands in OCM for a matmul.</li>
<li><span class="gap">open</span> <b>A CME write call carries no fixed cost. A CME read call carries about {CALLFIT['read']['icpt']:.0f} ns.</b>
<ul>
<li><b>What the rows show.</b> Each bandwidth pass is one call of the kernel (the test loop in cme_kern.S). A call enters streaming mode with SMSTART, moves its bytes and leaves with SMSTOP. A straight line through the 16 and 48 KiB rows, time per pass against bytes, gives the fixed cost per call as its intercept (two points, est.). For cme-write the intercept is {CALLFIT['write']['icpt']:.1f} ns per call at a fitted rate of {CALLFIT['write']['rate']:.0f} GB/s. For cme-read it is {CALLFIT['read']['icpt']:.0f} ns per call at {CALLFIT['read']['rate']:.0f} GB/s [cme-bandwidth-dram-1core.csv, run 3].</li>
<li><b>A short write call does show a cost.</b> The 1 KiB write call takes {CALLB['write']:.0f} ns. Its stores take {CALL_1K_STORE_NS:.0f} ns at {CALLFIT['write']['rate']:.0f} GB/s. The rest, {CALLB['write'] - CALL_1K_STORE_NS:.0f} ns est., is the call's own cost [cme-bandwidth-call-cost.csv, run 3].</li>
<li><b>What every call pays.</b> The register save, SMSTART, SMSTOP and the restore cost {CALL_SWITCH_NS:.0f} ns est. together (cme-call minus cme-roundtrip on boot E). The read kernel also adds up the 16 running totals it kept while loading and returns the result. The write kernel returns nothing.</li>
<li><span class="hyp">hypothesis</span> <b>Why the write rows hide the cost.</b> Stores are posted: the core counts a store as done before the data reaches memory. So the last stores of one call are still draining while the kernel leaves streaming mode and the next call enters. From 16 KiB up, the mode switch overlaps with those stores. The read kernel's final sum waits for its loads, so nothing overlaps there.</li>
<li><b>Three tests would settle it.</b> All three are in run 6, phase F2 of run_cme.sh, requested for boot F1 and not yet run [follow-up-run-plan.md, section 13].
<ul>
<li>A single-call form for the CME (all passes of a rep in one streaming span, cme_kern.S) for read and write at 4, 8, 16 and 24 KiB, beside the looped form (one call per pass). Read the two forms as the core's L1 rows are read (asimov-c1nano-perf.html, section 7.1). The difference of the two intercepts is the cost per call. A difference near zero for writes confirms the overlap.</li>
<li>A write variant with DSB ST (a barrier that waits for all earlier stores to complete) before SMSTOP. If about {CALL_SWITCH_NS:.0f} ns per call then appears, the overlap is confirmed.</li>
<li>Per-call writes at 1, 2, 4 and 8 KiB, to find the size at which the {CALLB['write'] - CALL_1K_STORE_NS:.0f} ns disappears.</li>
</ul>
</li>
</ul>
</li>
</ul>

<h2 id="sources">11. Sources</h2>
<ul>
{"".join(f"<li><a href='{s}'>{s}</a>: {_src(t)}.</li>" for s, t in p.SOURCES)}
<li><a href="results/membench-jibin-010/README.md">Jesse's boot E README</a>: the SCP rebuild, the L3 power reading, the E against C comparison.</li>
<li><a href="results/membench-jibin-004/README.md">Jesse's run 3 README</a>: the CME power analysis and the pass-loop disassembly estimate.</li>
<li><a href="CME-plan.md">CME-plan.md</a> and <a href="codex-review-CME-plan.md">codex-review-CME-plan.md</a>: the test design, the counter events and their caveats, the asimov-bench reference values (runs 3969 and 4045 as quoted in <a href="est_chip_time.py">est_chip_time.py</a>). <a href="cme_kern.S">cme_kern.S</a>: the kernels.</li>
<li><a href="asimov-c1nano-perf.html">asimov-c1nano-perf.html</a>: the companion page for the core. <a href="asimov-cme-run4.html">asimov-cme-run4.html</a>: the run 4 CME page with the per-boot checks.</li>
</ul>
"""
    toc = [("words", "1. Words used here"), ("run", "2. The run and the platform", [("changes", "2.1 What changed from run 3 to run 4 boot E for the CME")]), ("map", "3. The hemisphere map, CME path", [("path", "3.1 The data path of one CME load")]),
           ("tables", "4. Summary tables", [("t41", "4.1 Latency by footprint"), ("t42", "4.2 OCM through the CME"), ("t43", "4.3 One-core bandwidth, core against CME"), ("t44", "4.4 The 64-byte forms"), ("t45", "4.5 Call cost"), ("t46", "4.6 Home-node counts")]),
           ("f-lat", "5. Latency by footprint"), ("f-bw", "6. Bandwidth by footprint"),
           ("f-ocm", "7. OCM through the CME"), ("f-cmn", "8. Mesh counters"), ("bench", "9. Against asimov-bench"), ("open", "10. Open items"), ("sources", "11. Sources")]
    return page("Asimov CME Memory Performance", f"The C1-SME2 unit of DSU 1 driven from CPU 2 in streaming mode, beside the same core's rows. {p.META} The bandwidth and mesh-counter sections are run 3's (the L3 off). Generated by gen_perf_cme.py.", toc, body)


if __name__ == "__main__":
    html = cme_page()
    open(p.OUT["cme"], "w").write(html)
    print("wrote", p.OUT["cme"], len(html), "bytes")
