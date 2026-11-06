#!/usr/bin/env python3
"""The data layer for the four performance pages, and main() that writes them:

  asimov-c1nano-perf.html        gen_perf_core.core_page()   the C1-Nano core: latency, bandwidth, OCM, mesh
  asimov-cme-perf.html           gen_perf_cme.cme_page()     the CME (the cluster's C1-SME2 unit)
  asimov-c1nano-perf-brief.html  gen_brief.core_brief()      the two-page brief of the core page
  asimov-cme-perf-brief.html     gen_brief.cme_brief()       the two-page brief of the CME page

"Latest" is run 4 boot E (results/membench-jibin-010/results/bootE/, 2026-11-05, the DSU L3 on). Run 3
(membench-jibin-004, the L3 off) is beside it where boot E repeated the row, boot C (007, same commit as E,
L3 off) where a comparison isolates the L3, and boot A (005, the configuration closest to run 3) where the OCM
rows need an L3-off reference. Every number is read from the CSV files through gen_run3 (run 2 and run 3) and
gen_run4 (the five boots of run 4); this module only selects and joins. Nothing is typed in except the
platform facts quoted from Jesse's README files (cited where used) and gen_run3.BENCH (asimov-bench values).

Exported names (source in brackets: g = gen_run3, r4 = gen_run4):

  Boots and platform
    E, C, A, B, D       the boot tables, r4.BT[x]: dicts with load_boot()'s names (LV, CLV, OCM, ALL5, TLB, ROUTE,
                        FIT, COCM, CALL5, W, REPEAT_SAME, REPEAT_SORTED, N_WITHIN, CTRL, RT_NS, P4K, CHIP_S, CMDS,
                        README, LOG, SPLIT, SPLIT_ALL5, SEQ, FLUSHED, CSEQ, CFLUSHED, XFIRST_DSU, XFIRST_NODE, ...)
    BOOTS               ("A", "B", "C", "D", "E") [r4.BOOT_ORDER]
    BOOT_RUN_ID, BOOT_NAME, BOOT_COL   run directory number, long name and chart colour per boot [r4]
    BOOT_SHORT          a short name per boot for table heads ("boot E (L3 on)")
    PLATFORM            {boot: dict(run_id, dir, commit, scp, tfa, pwrstat, date, chip_s, commands, pf_on, cont, l3_on)}
                        [r4.EX, r4.BT, the README of each run: date, chip seconds]
    RUN3                dict(run_id, dir, commit, scp, tfa, date, chip_s, commands, files) for run 3 [README 004, g.CMD4]
    FIVE                the five-boot table rows (label, {boot: text}) [r4.FIVE]
    CONTROLS            {boot or "run3": dict(p4k, rt=(lo, hi), ctrl={2:, 8:})}: the 4 KiB repeated chase, the CME
                        round trip and the two uncounted 4 KiB controls [r4.BT[x]["P4K"], ["RT_NS"], ["CTRL"]; g.LV4, g.RT_NS, g.CTRL]

  The core level map (section 4.1 / 5)
    LEVELS              one row per boot E chase (repeat, fresh, flushed, seq): dict(size, kind, ns, ns3, nsC, ns_boot={x: ns},
                        ratio (E over C), level (level_name_e), e (best-pass refills per load), emean, n, ns_rng,
                        hit (the HITSET row of that size on E, or None; the hit set is a repeated chase, so at 512 KiB its ns differs
                        from the fresh level row's)) [r4.BT["E"]["LV"], g.LV4, r4.BT["C"]["LV"], r4.E_L3]
    SEQ_ROW             the sequential 8 MiB chain: dict(size, kind, ns={boot: ns}, l1pf={boot: L1 prefetch refills per load}, l1_refill={boot: all L1 refills per load}) [r4.BT[x]["SEQ"]]
    HITSET              the L3 hit set on E, one row per size 64 KiB to 512 KiB: dict(size, ns, nsC, l1_refill, l2_refill, l2_hit,
                        l3_acc, l3_hit, l3_refill, hit_rng, hitC) [r4.E_L3, r4.C_L3: latency-dram-small-l3.csv]
    L3_HIT_SIZES        the sizes whose every rep counts over 0.1 L3 hits per load on E (192, 256, 384, 512 KiB) [r4.L3_HIT_SIZES]
    L3_HIT_EST          {256 KiB: ns, 384 KiB: ns}: est. cost of one L3 hit [r4.L3_HIT_EST]; L3_HIT_EST_HOW says how it is derived
    EC_RATIO            {(size, kind): E ns over C ns} [r4.EC_RATIO]
    EC_DELTA            {16 MiB: E minus C ns, 32 MiB: ...} on the fresh chains [r4.BT]
    L32M                {boot or "run3": 32 MiB fresh chase ns}
    DRAM_MODEL          dict(seq_B, random_B, home_hop, flushed_E, flushed_C, rest_est): boot B's address-order and random 8 MiB
                        chains, E's 2 MiB SLC chase (the home-node round trip) and the remainder (est.) [r4.BT["B"], r4.BT["E"]]

  OCM and the mesh (sections 4.2 / 6 / 10)
    CELLS               the 20 (cpu, region) cells in gen_run4's order [r4.CELLS]
    ROUTES              one row per cell: dict(cpu, region, node, dist, dx, dy, E=dict(best, median, l3, l2, pf, dom_dsu, exp_dsu,
                        share_dsu, dom_node, exp_node, share_node, d_dsu, d_node), A=same, C=same, run3_sparse, run2_dense,
                        E_dense (G2 dense on CPUs 2 and 8, else None)) [r4.BT[x]["ROUTE"], g.OCM, g.OCM2]
    ROUTE_FIT           {boot: dict(a, bx, by, rms, n)}: the distance fit of the 20 route cells [r4.BT[x]["FIT"]["route"]]
    ROUTE_L3_RNG        {boot: (min, max) L3 read refills per load over the 20 route cells}
    XFIRST              {boot: (cells where the DSU's dominant direction is X-first, same at the node)} [r4.BT[x]["XFIRST_DSU"], ["XFIRST_NODE"]]
    OCM_SPARSE          one row per (cpu in 2, 8; region): dict(cpu, region, dist, E=dict(best, median, l3, pf), A, C, B, D (same), run3=dict(best, median))
                        [r4.BT[x]["OCM"][c][r]["sparse"], r4.BT[x]["SPLIT"], g.OCM]
    SPARSE_L3_RNG       {boot: (min, max) L3 read refills per load (pass mean) over the 10 sparse rows of CPUs 2 and 8} for A, C, E
    SPARSE_L3_RNG_CPU2  the same over CPU 2's 5 sparse rows
    ALL5                {cpu: {boot or "run3" or "run2": dict(dense, sparse)}} the all-five chains, CPUs 2 and 8
                        [r4.BT[x]["ALL5"], g.ALL5D, g.ALL5S, g.ALL5_2]
    ALL5_DENSE_BEST     {boot: CPU 2 dense all-five best ns} [r4.ALL5_DENSE_BEST]; ALL5_DENSE_L3 {cpu: E's L3 refills per load}
    RATIOS, PAIRS       the 69-row ratio statistics of the boot pairs and their descriptions [r4.RATIOS, r4.PAIRS]
    TLB_PASS, TLB_PASS_RNG   L1 data TLB refills per pass on the 15 TLB-set rows, per boot [r4]
    GAP, GAP_MEAN       sparse minus dense ns per region on CPU 2, per boot, and its mean [r4]
    STIM, WALK_STIM     the 32 MiB TLB stimulus (best, l1, walk per load) per boot; the walk-counted stimulus on C, D, E [r4]
    WALK_RATES          {boot: dict(tlb_set, walk_row)}: walks per load of the two 32 MiB processes of one boot [r4.STIM, r4.WALK_STIM]

  Bandwidth (sections 4.3 / 7)
    READ_VARIANTS       one row per (kernel, size): dict(kernel, name, size, agg={boot: GB/s}, run3 (plain loop only)) [r4.EX[x]["rp"], g.ONE]
    RP_KERNELS, RP_SIZES   [r4]
    G8, G8_SIZES, G8_MARGINAL, G8_FITS   the L1 rows of boots C and E; G8_FITS = {(boot, form, kernel): dict(a_ns, rate, resid_pct, ok)} [r4.G8]
    G8_ROWS             one row per (form, kernel, size): dict(form, kernel, size, agg={boot: GB/s}, t_pass={boot: ns}, run3 (16 KiB only)) [r4.G8, g.ONE]
    WRITE_SMALL         one row per size: dict(size, agg={boot: run 3 program GB/s}, agg_r2={boot: run 2 program}, run3, run2, ns_pass={boot:}, delta={boot:})
                        for boots A and E [r4.BT[x]["W"], g.ONE]

  The CME (the CME page's sections 4, 5, 7, 9)
    CME_LEVELS          one row per boot E CME chase: dict(size, kind, ns, ns3, nsC, nsB, ns_boot, ratio (E over C), core (E's core chase),
                        e, emean, eC, emeanC, inner_share, outer3 (run 3 best-pass outer refills)) [r4.BT[x]["CLV"], g.CLV]
    CME_SEQ, CME_FLUSHED   {boot: ns} the sequential and the flushed 8 MiB chain through the CME [r4.BT[x]["CSEQ"], ["CFLUSHED"]]
    CME_B               [(size, ns)] boot B's repeated CME chases (CME prefetcher off) [r4.BT["B"]["CLV"]]
    EC_CLV_RATIO, CME_INNER_SHARE   [r4]
    CME_OCM             one row per region: dict(region, dist, E=dict(sparse, dense, vary, median, outer, rd, pf), C, A, B (best per shape),
                        run3=dict(best, median)) [r4.BT[x]["COCM"], g.COCM]
    CME_ALL5            {boot or "run3": dict(dense, sparse)} [r4.BT[x]["CALL5"], g.CALL5D, g.CALL5S]

  Repeat checks (section 4.8)
    REPEAT_E3, N_WITHIN_E3   boot E against run 3: the rows sorted by |change| and the counts within 1, 3, 5 % [r4.BT["E"]]
    REPEAT_A3, N_WITHIN_A3   boot A against run 3 (the same configuration: the repeatability pair) [r4.BT["A"]]

  Text
    META, SOURCES       the pages' subtitle and the sources list
    WORDS_FIRST, WORDS_NEW, L3_WORD, words_core()   the terms defined first (PMU, TLB), the new terms, the reworded L3 entry, and gen_run3.WORDS_COMMON with all applied
    BW_COV_ROWS_E       the bandwidth rows of boot E that carry perf_cov (all 1.0000); RUN3_CTRL2_BEST the best rows in run 3's latency-control-cpu2.csv
    L3_HIT_EST_192, L3_HIT_192_SHARE   the same L3-hit derivation on the 192 KiB row (not in r4.L3_HIT_EST) and that row's L3 hits per load
    level_name_e(size, kind), bw_level_e(size)   level names for the L3-on reading
    BENCH               asimov-bench reference values [g.BENCH]
  Helpers re-exported from gen_run3 and gen_run4: kib, fmt, tr, table, pct, esc, C, SVG, legend, line_chart, dumbbell, strip,
    bars_h, mesh_map, cme_path_fig, page, fig, words, dist, NODES, DSUS, NODE_OF_REGION, CPU_DSU, SLC_BYTES, dotplot, stacked_h,
    hyp, ok, no, gap, rng, mono, cell_label.
"""
import os, re, sys, statistics

A_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, A_DIR)
import gen_run3 as g
import gen_run4 as r4
from gen_run3 import (kib, fmt, tr, table, pct, esc, C, SVG, legend, line_chart, dumbbell, strip, bars_h, mesh_map, cme_path_fig, page, fig, words,
                      dist, NODES, DSUS, NODE_OF_REGION, CPU_DSU, SLC_BYTES, BENCH)
from gen_run4 import (dotplot, stacked_h, hyp, ok, no, gap, rng, mono, cell_label, CELLS, BOOT_RUN_ID, BOOT_NAME, BOOT_COL, FIVE, RATIOS, PAIRS,
                      TLB_PASS, TLB_PASS_RNG, GAP, GAP_MEAN, STIM, WALK_STIM, EC_RATIO, EC_CLV_RATIO, CME_INNER_SHARE, L3_HIT_EST, L3_HIT_SIZES,
                      ALL5_DENSE_BEST, G8, G8_SIZES, G8_MARGINAL, RP_KERNELS, RP_SIZES, SHAPES)

OUT = dict(core=A_DIR + "/asimov-c1nano-perf.html", cme=A_DIR + "/asimov-cme-perf.html",
           core_brief=A_DIR + "/asimov-c1nano-perf-brief.html", cme_brief=A_DIR + "/asimov-cme-perf-brief.html")

# ---------------------------------------------------------------- boots and platform
BOOTS = r4.BOOT_ORDER
BT = r4.BT
E, C, A, B, D = (BT[x] for x in "ECABD")
BOOT_SHORT = dict(A="boot A (L3 off, 4 KiB pages)", B="boot B (L3 off, prefetchers off)", C="boot C (L3 off, 64 KiB hint)", D="boot D (L3 off, hint, prefetchers off)", E="boot E (L3 on)")

def _readme_date(text):
    m = re.search(r"on (2026-\d\d-\d\d(?: and \d\d)?) \(UTC\)", text)
    return m.group(1) if m else None
PLATFORM = {x: dict(run_id=BOOT_RUN_ID[x], dir=f"results/membench-jibin-{BOOT_RUN_ID[x]}/results/boot{x}/", commit=r4.EX[x]["commit"], scp=r4.EX[x]["scp"], tfa=r4.EX[x]["tfa"],
                    pwrstat=r4.EX[x]["pwrstat"], date=_readme_date(BT[x]["README"]), chip_s=BT[x]["CHIP_S"], commands=len(BT[x]["CMDS"]),
                    pf_on=r4.EX[x]["pf_on"], cont=r4.EX[x]["cont"], l3_on=r4.EX[x]["pwrstat"] == ["0x70", "0x70"]) for x in BOOTS}
_r3_readme = open(A_DIR + "/results/membench-jibin-004/README.md").read()
RUN3 = dict(run_id="004", dir="results/membench-jibin-004/results/", commit=re.search(r"commit `([0-9a-f]{7})", _r3_readme).group(1),
            scp=re.search(r"SCP (0\.48\.0-nopcie(?:-l3)?\.\d+)", _r3_readme).group(1), tfa=re.search(r"TF-A (0\.35\.0(?:-pfoff\.\d+)?)", _r3_readme).group(1),
            date=_readme_date(_r3_readme), chip_s=float(re.search(r"ns=(\d+)", _r3_readme).group(1)) / 1e9, commands=len(g.CMD4), files=g.FILES4)
CONTROLS = {x: dict(p4k=BT[x]["P4K"]["ns"], p4k_cyc=BT[x]["P4K"]["cyc"], rt=BT[x]["RT_NS"], ctrl=dict(BT[x]["CTRL"])) for x in BOOTS}
CONTROLS["run3"] = dict(p4k=g.LV4[0]["ns"], p4k_cyc=None, rt=g.RT_NS, ctrl={c: g.CTRL[c]["best"] for c in g.CTRL})
def _bw_cov_rows(x):
    """the bandwidth rows of boot x that carry a perf_cov column (the timed reps; the best rows carry '-'): count and the set of values"""
    import csv, glob
    vals, n = set(), 0
    for f in sorted(glob.glob(A_DIR + "/" + PLATFORM[x]["dir"] + "bandwidth-*.csv")):
        for d in csv.DictReader(l for l in open(f) if not l.startswith("#")):
            if d.get("perf_cov") not in (None, "-", "perf_cov"): n += 1; vals.add(d["perf_cov"])
    return n, vals
BW_COV_ROWS_E, _bw_cov_vals = _bw_cov_rows("E")
assert _bw_cov_vals == {"1.0000"}, _bw_cov_vals
RUN3_CTRL2_BEST = sum(1 for d in r4.lat_rows(g.R4 + "latency-control-cpu2.csv") if d["mode"].endswith("best"))   # run 3's file holds one best row per command (two commands)

# ---------------------------------------------------------------- the core level map
def level_name_e(size, kind):
    """the level name of a boot E chase (the L3 on): never gen_run3's "held no data" wording"""
    if kind == "flushed": return "DRAM (emulator memory model, fixed delay), 8 MiB random chain, every line flushed"
    if kind == "seq": return "DRAM (emulator memory model, fixed delay), 8 MiB sequential chain in address order"
    if size <= 24576: return "L1"
    if size <= 32768: return "L1 and L2"
    if size <= 131072: return "L2"
    if size <= 393216: return "L2 and L3 (mixed)"
    if size <= 524288: return "L3 and SLC (mixed)"
    if size <= SLC_BYTES: return "SLC (mesh cache)"
    if size < 16777216: return "SLC and DRAM (mixed)"
    return "DRAM"

def bw_level_e(size):
    """a capacity reading of where a streamed buffer of this size fits with the L3 on (hypothesis: the bandwidth rows carry no level counters)"""
    return "L1" if size <= 32768 else "L2" if size <= 131072 else "L2 and L3" if size <= 262144 else "L3 and SLC" if size <= 524288 else "SLC" if size <= SLC_BYTES else "DRAM"

_LV = {x: {(d["size"], d["kind"]): d for d in BT[x]["LV"]} for x in BOOTS}
_hit = lambda s: dict(size=s, ns=r4.E_L3["best"][s]["ns"], nsC=r4.C_L3["best"][s]["ns"], l1_refill=r4.E_L3["best"][s]["e"]["l1d_refill"], l2_refill=r4.E_L3["best"][s]["e"]["l2d_refill"],
                      l2_hit=r4.E_L3["best"][s]["e"]["l2d_hit_rd"], l3_acc=r4.E_L3["best"][s]["e"]["l3d_access_rd"], l3_hit=r4.E_L3["best"][s]["e"]["l3d_hit_rd"],
                      l3_refill=r4.E_L3["best"][s]["e"]["l3d_refill_rd"], hit_rng=r4.E_L3["hit_rng"][s], hitC=r4.C_L3["best"][s]["e"]["l3d_hit_rd"])
HITSET = [_hit(s) for s in r4.E_L3["sizes"]]
_HIT = {h["size"]: h for h in HITSET}
LEVELS = [dict(size=d["size"], kind=d["kind"], ns=d["ns"], ns3=d["ns3"], nsC=_LV["C"][(d["size"], d["kind"])]["ns"], ns_boot={x: _LV[x][(d["size"], d["kind"])]["ns"] for x in BOOTS},
               ratio=EC_RATIO[(d["size"], d["kind"])], level=level_name_e(d["size"], d["kind"]), e=d["e"], emean=d["emean"], n=d["n"], ns_rng=d["ns_rng"],
               hit=_HIT.get(d["size"]) if d["kind"] in ("repeat", "fresh") else None) for d in E["LV"]]
SEQ_ROW = dict(size=8388608, kind="seq", ns={x: BT[x]["SEQ"]["ns"] for x in BOOTS}, l1pf={x: BT[x]["SEQ"]["e"]["l1d_refill_hwprf"] for x in BOOTS},
               l1_refill={x: BT[x]["SEQ"]["e"]["l1d_refill"] for x in BOOTS})
L3_HIT_EST_HOW = ("the hit-set row's ns per load, less its L2 read hits per load at the 128 KiB row's time (an L2 hit) and its L3 read refills per load at boot C's "
                  "384 KiB time (a read from the mesh), divided by its L3 read hits per load")
L3_HIT_EST_192 = r4.l3_hit_est(196608)   # the same derivation on the 192 KiB row, where under half the loads hit the L3 (not in r4.L3_HIT_EST)
L3_HIT_192_SHARE = _HIT[196608]["l3_hit"]
EC_DELTA = {s: _LV["E"][(s, "fresh")]["ns"] - _LV["C"][(s, "fresh")]["ns"] for s in (16777216, 33554432)}
L32M = {x: _LV[x][(33554432, "fresh")]["ns"] for x in BOOTS}; L32M["run3"] = next(d["ns"] for d in g.LV4 if d["size"] == 33554432)
DRAM_MODEL = dict(seq_B=B["SEQ"]["ns"], random_B=B["FLUSHED"]["ns"], home_hop=_LV["E"][(2097152, "fresh")]["ns"], flushed_E=E["FLUSHED"]["ns"], flushed_C=C["FLUSHED"]["ns"])
DRAM_MODEL["rest_est"] = DRAM_MODEL["flushed_E"] - DRAM_MODEL["home_hop"]

# ---------------------------------------------------------------- OCM and the mesh
def _route(x, c, r):
    v = BT[x]["ROUTE"][(c, r)]
    return dict(best=v["best"], median=v["median"], l3=v["emean"]["l3d_refill_rd"], l2=v["emean"]["l2d_refill"], pf=v["emean"]["l2d_refill_hwprf"],
                dom_dsu=v["dom_dsu"], exp_dsu=v["exp_dsu"], share_dsu=v["share_dsu"], dom_node=v["dom_node"], exp_node=v["exp_node"], share_node=v["share_node"],
                d_dsu=v["d_dsu"], d_node=v["d_node"], passes=v["passes"])
ROUTES = [dict(cpu=c, region=r, node=NODE_OF_REGION[r], dist=dist(c, NODE_OF_REGION[r]), dx=E["ROUTE"][(c, r)]["dx"], dy=E["ROUTE"][(c, r)]["dy"],
               E=_route("E", c, r), A=_route("A", c, r), C=_route("C", c, r), B=_route("B", c, r), D=_route("D", c, r),
               run3_sparse=g.OCM[c][r]["best"], run2_dense=g.OCM2[c][r]["best"], E_dense=E["OCM"][c][r]["dense"]["best"] if c in E["OCM"] else None) for c, r in CELLS]
ROUTE_FIT = {x: BT[x]["FIT"]["route"] for x in BOOTS}
ROUTE_L3_RNG = {x: (min(BT[x]["ROUTE"][k]["emean"]["l3d_refill_rd"] for k in CELLS), max(BT[x]["ROUTE"][k]["emean"]["l3d_refill_rd"] for k in CELLS)) for x in BOOTS}
XFIRST = {x: (BT[x]["XFIRST_DSU"], BT[x]["XFIRST_NODE"]) for x in BOOTS}
def _sparse(x, c, r):
    o = BT[x]["OCM"][c][r]["sparse"]; s = BT[x]["SPLIT"][(c, r, "sparse")]
    return dict(best=o["best"], median=o["median"], l3=s["l3"], pf=s["pf"], dense=BT[x]["OCM"][c][r]["dense"]["best"])
OCM_SPARSE = [dict(cpu=c, region=r, dist=dist(c, NODE_OF_REGION[r]), **{x: _sparse(x, c, r) for x in BOOTS}, run3=dict(best=g.OCM[c][r]["best"], median=g.OCM[c][r]["median"]))
              for c in (2, 8) for r in sorted(range(5), key=lambda r: (dist(c, NODE_OF_REGION[r]), r))]
SPARSE_L3_RNG = {x: (min(BT[x]["SPLIT"][(c, r, "sparse")]["l3"] for c in (2, 8) for r in range(5)), max(BT[x]["SPLIT"][(c, r, "sparse")]["l3"] for c in (2, 8) for r in range(5))) for x in "ACE"}
SPARSE_L3_RNG_CPU2 = {x: (min(BT[x]["SPLIT"][(2, r, "sparse")]["l3"] for r in range(5)), max(BT[x]["SPLIT"][(2, r, "sparse")]["l3"] for r in range(5))) for x in "ACE"}
ALL5 = {c: {**{x: dict(dense=BT[x]["ALL5"][c]["dense"]["best"], sparse=BT[x]["ALL5"][c]["sparse"]["best"]) for x in BOOTS},
            "run3": dict(dense=g.ALL5D[c]["best"], sparse=g.ALL5S[c]["best"]), "run2": dict(dense=g.ALL5_2[c]["best"], sparse=None)} for c in (2, 8)}
ALL5_RUN3_ALL = {c: dict(dense=g.ALL5D[c]["best"], sparse=g.ALL5S[c]["best"]) for c in (2, 4, 6, 8)}   # run 3 ran the all-five chains from four CPUs
ALL5_DENSE_L3 = r4.E_ALL5_DENSE_L3
WALK_RATES = {x: dict(tlb_set=STIM[x]["walk"], walk_row=WALK_STIM[x]["emean"]["dtlb_walk"] if x in WALK_STIM else None) for x in BOOTS}

# ---------------------------------------------------------------- bandwidth
_RP_BOOTS = r4.RP_BOOTS
_ONE = {d["size"]: d for d in g.ONE}
READ_VARIANTS = [dict(kernel=k, name=name, size=s, agg={x: r4.EX[x]["rp"][(k, s)]["agg"] for x in _RP_BOOTS}, e={x: r4.EX[x]["rp"][(k, s)]["e"] for x in _RP_BOOTS}, run3=_ONE[s]["read"] if k == "read" else None)
                 for s in RP_SIZES for k, name in RP_KERNELS]
G8_FITS = {(x, f, k): dict(a_ns=v["a_ns"], rate=v["rate"], resid_pct=v["resid_pct"], ok=v["ok"]) for x in G8 for (f, k), v in G8[x].items()}
G8_ROWS = [dict(form=f, kernel=k, size=s, agg={x: G8[x][(f, k)]["rows"][s]["agg"] for x in G8}, t_pass={x: G8[x][(f, k)]["rows"][s]["t_pass"] for x in G8},
                run3=_ONE[s][k] if s in _ONE else None) for f in ("per-pass", "asm") for k in ("read", "write") for s in G8_SIZES]
_W = {x: {d["size"]: d for d in BT[x]["W"]} for x in "AE"}
WRITE_SMALL = [dict(size=s, agg={x: _W[x][s]["r3prog"] for x in "AE"}, agg_r2={x: _W[x][s]["r2prog"] for x in "AE"}, run3=_W["E"][s]["run3"], run2=_W["E"][s]["run2"],
                    ns_pass={x: _W[x][s]["ns3"] for x in "AE"}, delta={x: _W[x][s]["delta"] for x in "AE"}, delta_orig=_W["E"][s]["delta_orig"]) for s in sorted(_W["E"])]

# ---------------------------------------------------------------- the CME
_CLV = {x: {(d["size"], d["kind"]): d for d in BT[x]["CLV"]} for x in BOOTS}
_CLV3 = {(d["size"], d["kind"]): d for d in g.CLV}
CME_LEVELS = [dict(size=d["size"], kind=d["kind"], ns=d["ns"], ns3=d["ns3"], nsC=_CLV["C"][(d["size"], d["kind"])]["ns"], nsB=_CLV["B"][(d["size"], d["kind"])]["ns"],
                   ns_boot={x: _CLV[x][(d["size"], d["kind"])]["ns"] for x in BOOTS}, ratio=d["ns"] / _CLV["C"][(d["size"], d["kind"])]["ns"],
                   core=_LV["E"][(d["size"], d["kind"])]["ns"], e=d["e"], emean=d["emean"], eC=_CLV["C"][(d["size"], d["kind"])]["e"], emeanC=_CLV["C"][(d["size"], d["kind"])]["emean"],
                   inner_share=CME_INNER_SHARE["E"].get(d["size"]) if d["kind"] == "repeat" else None,
                   outer3=_CLV3[(d["size"], d["kind"])]["outer_best"] if (d["size"], d["kind"]) in _CLV3 else None) for d in E["CLV"]]
CME_SEQ = {x: BT[x]["CSEQ"]["ns"] for x in BOOTS}; CME_FLUSHED = {x: BT[x]["CFLUSHED"]["ns"] for x in BOOTS}; CME_FLUSHED["run3"] = _CLV3[(8388608, "flushed")]["ns"]
CME_B = [(d["size"], d["ns"]) for d in B["CLV"] if d["kind"] == "repeat"]
def _cocm(x, r):
    o = BT[x]["COCM"][r]
    return dict(sparse=o["sparse"]["best"], dense=o["dense"]["best"], vary=o["vary"]["best"], median=o["sparse"]["median"],
                outer=o["sparse"]["emean"]["cme_l1d_refill_outer"], inner=o["sparse"]["emean"]["cme_l1d_refill_inner"], rd=o["sparse"]["emean"]["cme_l1d_refill_rd"], pf=o["sparse"]["emean"]["cme_l1d_refill_hwprf"])
CME_OCM = [dict(region=r, dist=dist(2, NODE_OF_REGION[r]), **{x: _cocm(x, r) for x in BOOTS}, run3=dict(best=g.COCM[r]["best"], median=g.COCM[r]["median"], outer=g.COCM[r]["outer"]))
           for r in sorted(range(5), key=lambda r: (dist(2, NODE_OF_REGION[r]), r))]
CME_ALL5 = {**{x: dict(dense=BT[x]["CALL5"]["dense"]["best"], sparse=BT[x]["CALL5"]["sparse"]["best"]) for x in BOOTS}, "run3": dict(dense=g.CALL5D["best"], sparse=g.CALL5S["best"])}

# ---------------------------------------------------------------- repeat checks
REPEAT_E3, N_WITHIN_E3 = E["REPEAT_SORTED"], E["N_WITHIN"]
REPEAT_A3, N_WITHIN_A3 = A["REPEAT_SORTED"], A["N_WITHIN"]

# ---------------------------------------------------------------- text
META = (f"Latest: run 4 boot E (membench-jibin-{BOOT_RUN_ID['E']}, {PLATFORM['E']['date']}, commit {PLATFORM['E']['commit']}, the DSU L3 on: IMP_CLUSTERPWRSTAT_EL1 {PLATFORM['E']['pwrstat'][0]}). "
        f"Beside it: run 3 (membench-jibin-004, {RUN3['date']}, the L3 off), boot C ({BOOT_RUN_ID['C']}, same commit, the L3 off) and boot A ({BOOT_RUN_ID['A']}, run 3's configuration). "
        f"Runs 1 to 3 and boots A to D measured with the L3 of CPUs 2 to 9 holding no data. Every number is read from the CSV files by gen_perf.py.")
SOURCES = [
    (f"results/membench-jibin-010/", "run 4 boot E (2026-11-05): results/bootE/*.csv, log.txt, sysinfo.txt, dmesg.txt and Jesse's README (the SCP rebuild, the L3 power reading)"),
    (f"results/membench-jibin-007/", "run 4 boot C (2026-11-05): the same commit as E with the L3 off and the OCM in 64 KiB contiguous translations"),
    (f"results/membench-jibin-005/", "run 4 boot A (2026-11-04): run 3's configuration with the prefetch and TLB counters"),
    (f"results/membench-jibin-006/", "run 4 boot B (2026-11-04 and 05): the data prefetchers off"),
    (f"results/membench-jibin-008/", "run 4 boot D (2026-11-05): the hint with the prefetchers off"),
    (f"results/membench-jibin-004/", "run 3 (2026-11-03): the bandwidth set, the CPU 4 and 6 rows, the mesh-counter attribution"),
    (f"results/membench-jibin-002/", "run 2 (2026-11-02): the dense OCM chains"),
    ("gen_perf.py, gen_perf_core.py, gen_perf_cme.py, gen_brief.py", "the generators of these four pages (data layer, core page, CME page, briefs)"),
    ("gen_run3.py, gen_run4.py", "the readers of run 2, run 3 and the five boots of run 4 (imported, not edited)"),
    ("asimov-c1nano-run4.html, asimov-cme-run4.html", "the run 4 pages: the hypotheses, the per-boot checks and the five-boot comparisons"),
]
L3_WORD = ("L1, L2, L3", f"32 KiB data cache per core, 128 KiB per DSU, 256 KiB per DSU, 64-byte lines [sysinfo.txt]. On runs 1 to 3 and run 4 boots A to D the L3 of CPUs 2 to 9 was in snoop-filter-only mode "
           f"and held no data (the stock SCP stages the full L3 for cluster 0 only; register 0x0, 0 L3 hits per load). Boot E's rebuilt SCP turns it on: the register reads {PLATFORM['E']['pwrstat'][0]} and the "
           f"hit set counts {_HIT[262144]['l3_hit']:.2f} L3 read hits per load at 256 KiB [Jesse's boot E README, L3 power; latency-dram-small-l3.csv].")
WORDS_FIRST = [
    ("PMU, TRM, SOG", "PMU: the performance monitoring unit, the counters of a core, of the CME or of the mesh. TRM: Arm's Technical Reference Manual of a unit. SOG: Arm's Software Optimization Guide of a core."),
    ("TLB, table walk", "TLB: the translation lookaside buffer, the core's cache of address translations. A table walk is the read of the page tables when the TLB misses. The counted events are L1 data TLB refills (0x05) and data TLB walks (0x34)."),
]
WORDS_NEW = [
    ("run, boot", "A run is one job on the emulator (run 3 = membench-jibin-004). Run 4 is five boots, A to E, each a job with one firmware and program configuration (section 2). Boot E is the latest."),
    ("L3 hit set", "Run 4's repeated chases from 64 KiB to 512 KiB with the hit events 0x81C5 (L2 read hits), 0xA0 (L3 read accesses) and 0x81C6 (L3 read hits) per load beside the refill events [latency-dram-small-l3.csv]."),
    ("sequential chain", "A chain whose members are the lines in address order, 8 MiB, every line flushed first: the stimulus a hardware prefetcher is built for [latency-dram-seq.csv]."),
    ("route row", "The dense chase of one CPU-to-region cell run under the mesh's crosspoint counters (data flits sent per direction on the DSU's and the home node's crosspoint); 20 cells, CPUs 2, 4, 6, 8 by OCM0 to OCM4 [latency-ocm-region*-route-cpu*.csv, cmn-counts.csv]."),
    ("contiguous hint", "The contiguous bit of a translation entry, which marks 16 neighbouring 4 KiB entries as one 64 KiB block. Boots C and D map the OCM with it (cont=64/64 on every mapping line in dmesg.txt)."),
    ("G2 rows", "Run 4's dense, sparse and vary chases of each OCM region from CPUs 2 and 8 without the mesh counters, and the all-five chains [latency-ocm-region&lt;r&gt;-dense-cpu&lt;c&gt;.csv, latency-ocm-region&lt;r&gt;-cpu&lt;c&gt;.csv]."),
    ("rms", "Root mean square of the residuals: the fit's typical miss per cell, in ns."),
    ("G8 rows, per-pass and single-call forms", "One-core L1 reads and writes of 4, 8, 16 and 24 KiB over many passes on boots C and E, timed with one call per pass (looped form, bandwidth-l1-passes.csv) or with every pass inside one assembly call (single-call form, bandwidth-l1-asmpasses.csv). A kernel is the program's inner loop function for one pass of reads or writes. A fit is a straight line, time per pass = fixed cost + bytes / rate, through a form's four rows, and its fixed cost is that form's per-pass cost."),
    ("read variants, PRFM", "The plain one-core read loop and four variants (PRFM, the Arm prefetch-hint instruction, issued 4, 8 or 16 lines ahead, or two streams) at 2 MiB and 32 MiB [bandwidth-read-prefetch.csv]."),
]
def dehop(items):
    """the shared glossary entries of gen_run3 with 'hop' (one load of a chain) written as 'load'; gen_run3 itself is not changed"""
    out = []
    for k, v in items:
        if k == "chase, hop": k, v = "chase", v.replace(" One load of the chain is one hop.", "")
        v = v.replace("one such hop per call", "one such round trip per call").replace("the hops of the timed span", "the loads of the timed span")
        v = re.sub(r"\bhops per pass\b", "loads per pass", v); v = re.sub(r"(\d[\d,]*) hops\b", r"\1 loads", v)
        out.append((k, v))
    return out

def words_core():
    """gen_run3.WORDS_COMMON with the L3 entry reworded for the L3-on data and the new terms appended (WORDS_COMMON itself is not changed)"""
    return WORDS_FIRST + dehop([L3_WORD if k == "L1, L2, L3" else (k, v) for k, v in g.WORDS_COMMON]) + WORDS_NEW

# ---------------------------------------------------------------- sanity: a wrong data wiring fails here
assert all(abs(CONTROLS[x]["p4k"] - 2.002) <= 0.001 for x in BOOTS), CONTROLS
assert all(abs(CONTROLS[x]["rt"][0] - 21.00) < 0.01 and abs(CONTROLS[x]["rt"][1] - 21.00) < 0.01 for x in BOOTS), CONTROLS
assert PLATFORM["E"]["pwrstat"] == ["0x70", "0x70"] and PLATFORM["C"]["pwrstat"] == ["0x0", "0x0"], (PLATFORM["E"], PLATFORM["C"])
assert _HIT[262144]["l3_hit"] > 0.7 and _HIT[262144]["hitC"] == 0.0, _HIT[262144]
assert next(d for d in LEVELS if d["size"] == 4096)["ns"] == 2.002 and len(REPEAT_E3) == 70
assert RUN3["commit"] == "ba834c0" and PLATFORM["E"]["commit"] == PLATFORM["C"]["commit"] == "b79dffa"

def main():
    import importlib, traceback
    for mod, func, out in (("gen_perf_core", "core_page", OUT["core"]), ("gen_perf_cme", "cme_page", OUT["cme"]), ("gen_brief", "core_brief", OUT["core_brief"]), ("gen_brief", "cme_brief", OUT["cme_brief"])):
        try:
            m = importlib.import_module(mod)
            html = getattr(m, func)()
            open(out, "w").write(html)
            print(f"wrote {os.path.basename(out)} ({len(html):,} bytes) from {mod}.{func}()")
        except ModuleNotFoundError as ex:
            print(f"SKIPPED {os.path.basename(out)}: {mod}.{func}: {ex} (the page module is not written yet)")
        except Exception as ex:
            print(f"FAILED {os.path.basename(out)}: {mod}.{func}: {type(ex).__name__}: {ex}")
            traceback.print_exc(limit=3)

if __name__ == "__main__":
    main()
