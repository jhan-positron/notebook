# ---------------------------------------------------------------- boots C, D and E (membench-jibin-007, 008, 010): the OCM in 64 KiB translations, and the L3 turned on
import l1_reader   # the run 5c reader for the G8 rows (bandwidth-l1-passes.csv, bandwidth-l1-asmpasses.csv)
BOOT_RUNS = dict(C=("007", "bootC"), D=("008", "bootD"), E=("010", "bootE"))
BT = {"A": {k: globals()[k] for k in B}, "B": B}   # every boot as one dict with load_boot's names; boot A's are also the module's globals
for _x, (_run, _boot) in BOOT_RUNS.items(): BT[_x] = load_boot(A + f"/results/membench-jibin-{_run}/", _boot)
BOOT_ORDER = ("A", "B", "C", "D", "E")
BOOT_RUN_ID = dict(A="005", B="006", C="007", D="008", E="010")

def bw_perf(path):
    """bw_rows plus e = {counter name: value per line} from the file's own column header (the G7 and G8 files carry seven perf columns)"""
    rows = bw_rows(path); cols = None; i = 0
    for line in open(path):
        if line.startswith("mem,"): cols = line.rstrip("\n").split(","); continue
        if line.startswith("#"): continue
        f = dict(zip(cols, line.rstrip("\n").split(",")))
        rows[i]["e"] = {k.replace("_per_line", ""): float(v) for k, v in f.items() if k.endswith("_per_line")}; i += 1
    assert i == len(rows)
    return rows

def extras(X):
    """the rows and records boot A lacks, each None when the boot has no such file: the box's power readings, the firmware, the L3 hit set, the read variants, the walk rows, the G8 rows"""
    RX = X["RA"]; ex = {}
    ex["pwrstat"] = [v for _, v in re.findall(r"# box clusterpwrstat (before|after) l3: (0x[0-9a-f]+)", X["LOG"])]
    ex["commit"] = re.search(r"cache-mem-perf-([0-9a-f]{7})", X["LOG"]).group(1)
    ex["scp"] = re.search(r"SCP (0\.48\.0-nopcie(?:-l3)?\.\d+)", X["README"]).group(1)
    ex["tfa"] = re.search(r"TF-A (0\.35\.0(?:-pfoff\.\d+)?)", X["README"]).group(1)
    ex["cont"] = bool(X["MAPS"][0]["cont"]) and all(m["cont"] == (64, 64) for m in X["MAPS"])   # every OCM mapping in 64 KiB contiguous translations
    ex["pf_on"] = X["SEQ"]["emean"]["l1d_refill_hwprf"] > 0.9   # the plan's boot check: the sequential chain's L1 prefetch refills per load
    if os.path.exists(RX + "latency-dram-small-l3.csv"):
        rows = [d for d in lat(RX + "latency-dram-small-l3.csv") if d["mode"] == "repeat"]
        sizes = sorted(set(d["size"] for d in rows))
        ex["l3"] = dict(sizes=sizes, n=len(rows), best={s: min((d for d in rows if d["size"] == s), key=lambda d: d["ns"]) for s in sizes},
                        hit_max=max(d["e"]["l3d_hit_rd"] for d in rows), hit_rng={s: rng_e([d for d in rows if d["size"] == s], "l3d_hit_rd") for s in sizes},
                        acc_minus_refill_minus_hit=max(abs(d["e"]["l3d_access_rd"] - d["e"]["l3d_refill_rd"] - d["e"]["l3d_hit_rd"]) for d in rows))   # 0xA0 = 0xA2 + 0x81C6 on every row
    else: ex["l3"] = None
    if os.path.exists(RX + "bandwidth-read-prefetch.csv"):
        rp = bw_perf(RX + "bandwidth-read-prefetch.csv")
        ex["rp"] = {(k, s): dict(agg=best(rp, kernel=k, bpt=s)["agg"], reps=[d for d in rp if d["kernel"] == k and d["bpt"] == s and d["rep"] != "best"]) for k, _ in RP_KERNELS for s in RP_SIZES}
        for v in ex["rp"].values():
            bestrep = max(v["reps"], key=lambda d: d["agg"]); v["e"] = bestrep["e"]
    else: ex["rp"] = None
    if os.path.exists(RX + "latency-dram-walk-cpu2.csv"):
        st = lat(RX + "latency-dram-walk-cpu2.csv"); stp = timed(st, 33554432)
        wk = {}
        for r in range(5):
            rows = lat(RX + f"latency-ocm-region{r}-walk-cpu2.csv"); ps = timed(rows, 262144)
            wk[r] = dict(best=best(rows, size=262144)["ns"], n=len(ps), passes=[dict(ns=p["ns"], e=p["e"]) for p in ps], emean={k: mean_e(ps, k) for k in ps[0]["e"]}, erng={k: rng_e(ps, k) for k in ps[0]["e"]})
        ex["walk"] = dict(stim=dict(best=best(st)["ns"], n=len(stp), emean={k: mean_e(stp, k) for k in stp[0]["e"]}, erng={k: rng_e(stp, k) for k in stp[0]["e"]}), ocm=wk)
    else: ex["walk"] = None
    if os.path.exists(RX + "bandwidth-l1-passes.csv"):
        g8 = {}
        for form, f in (("per-pass", "bandwidth-l1-passes.csv"), ("asm", "bandwidth-l1-asmpasses.csv")):
            rows = l1_reader.read_l1(RX + f); bests = l1_reader.best_reps(rows)
            assert all(d["asm_passes"] == (form == "asm") for d in rows)
            for kernel in ("read", "write"):
                pts = sorted((d["size"], d["t_pass_ns"]) for (k, _), d in bests.items() if k == kernel)
                a, b, resid = l1_reader.fit(pts); t_min = min(t for _, t in pts)
                g8[(form, kernel)] = dict(a_ns=a, rate=1 / b, resid=resid, resid_pct=100 * resid / t_min, ok=resid < l1_reader.RESID_MAX * t_min, n_reps=len(rows) // 8,
                                          rows={s: dict(agg=bests[(kernel, s)]["agg"], t_pass=t, cyc=bests[(kernel, s)]["cycles_per_line"], l1=bests[(kernel, s)]["l1d_refill_per_line"],
                                                        above_ideal=t - s / 64.0,   # ns per pass above the core's 64 B per cycle read path at 2 GHz (64 GB/s): t_pass - bytes / 64
                                                        reps=sorted(r["agg"] for r in rows if r["kernel"] == kernel and r["size"] == s)) for s, t in pts})
        ex["g8"] = g8
    else: ex["g8"] = None
    return ex
EX = {x: extras(BT[x]) for x in BOOT_ORDER}
assert EX["A"]["pwrstat"] == [] and all(EX[x]["pwrstat"] == ["0x0", "0x0"] for x in "BCD") and EX["E"]["pwrstat"] == ["0x70", "0x70"]
assert EX["C"]["cont"] and EX["D"]["cont"] and not EX["E"]["cont"] and not EX["A"]["cont"] and not EX["B"]["cont"]
assert EX["A"]["pf_on"] and EX["C"]["pf_on"] and EX["E"]["pf_on"] and not EX["B"]["pf_on"] and not EX["D"]["pf_on"]

# ---- the 69 core OCM rows on every boot, and the ratios of the pairs the plan names
def core_rows(X):
    """the 69 core OCM rows of a boot: label -> best ns (30 shape cells, 4 all-five rows, 15 TLB-set rows, 20 route rows); the walk rows are not among them"""
    out = {}
    for c in (2, 8):
        for r in range(5):
            for s in SHAPES: out[f"CPU {c} OCM{r} {s}"] = X["OCM"][c][r][s]["best"]
        for s in ("dense", "sparse"): out[f"CPU {c} all five {s}"] = X["ALL5"][c][s]["best"]
    for r in range(5):
        for s in SHAPES: out[f"CPU 2 OCM{r} {s}, TLB set"] = X["TLB"][r][s]["best"]
    for (c, r), v in X["ROUTE"].items(): out[f"CPU {c} OCM{r} route"] = v["best"]
    assert len(out) == 69
    return out
CORE_ROWS = {x: core_rows(BT[x]) for x in BOOT_ORDER}
def ratio_stats(num, den):
    rs = {k: CORE_ROWS[num][k] / CORE_ROWS[den][k] for k in CORE_ROWS[num]}
    return dict(n=len(rs), faster=sum(1 for r in rs.values() if r < 1), lo=min(rs.values()), hi=max(rs.values()), gm=math.exp(sum(math.log(r) for r in rs.values()) / len(rs)), rows=rs)
PAIRS = [("D", "B", "the hint alone (prefetchers off on both)"), ("C", "A", "the hint with the prefetchers on (two commits; A's one placement draw)"), ("C", "D", "the prefetchers (both with the hint)"),
         ("E", "A", "the L3 on (with another SCP, commit, build and placement draw)"), ("E", "C", "the L3 on against the hint (same commit and build)")]
RATIOS = {(a, b): ratio_stats(a, b) for a, b, _ in PAIRS}

# ---- H4 (boots C and D): the L1 data TLB refills per pass on CPU 2's 15 TLB-set chains, and the sparse-minus-dense gap
def tlb_per_pass(X, r, s):
    lo, hi = X["TLB"][r][s]["erng"]["l1d_tlb_refill"]; hops = X["TLB"][r][s]["hops"]
    return (lo * hops, hi * hops)
TLB_PASS = {x: {(r, s): tlb_per_pass(BT[x], r, s) for r in range(5) for s in SHAPES} for x in BOOT_ORDER}
TLB_PASS_RNG = {x: (min(v[0] for v in TLB_PASS[x].values()), max(v[1] for v in TLB_PASS[x].values())) for x in BOOT_ORDER}
TLB_PASS_RNG_SPARSE = {x: (min(v[0] for (r, s), v in TLB_PASS[x].items() if s != "dense"), max(v[1] for (r, s), v in TLB_PASS[x].items() if s != "dense")) for x in BOOT_ORDER}
TLB_PASS_RNG_DENSE = {x: (min(v[0] for (r, s), v in TLB_PASS[x].items() if s == "dense"), max(v[1] for (r, s), v in TLB_PASS[x].items() if s == "dense")) for x in BOOT_ORDER}
GAP = {x: BT[x]["SPARSE_MINUS_DENSE"][2] for x in BOOT_ORDER}   # sparse minus dense, best pass, CPU 2, per region
GAP_MEAN = {x: statistics.mean(GAP[x]) for x in BOOT_ORDER}
H4_TLB_FELL = max(TLB_PASS_RNG["C"][1], TLB_PASS_RNG["D"][1]) < min(TLB_PASS_RNG["A"][0], TLB_PASS_RNG["B"][0])
H4_GAP_CLOSED = dict(CA=sum(1 for a, c in zip(GAP["A"], GAP["C"]) if c < a), DB=sum(1 for b, d in zip(GAP["B"], GAP["D"]) if d < b))
H4_SUPPORTED = H4_TLB_FELL and GAP_MEAN["C"] < GAP_MEAN["A"] and GAP_MEAN["D"] < GAP_MEAN["B"]
# the 32 MiB stimulus on 4 KiB pages, which the hint does not reach
STIM = {x: dict(best=BT[x]["TLB_STIM_BEST"], l1=BT[x]["STIM_E"]["l1d_tlb_refill"], walk=BT[x]["STIM_E"]["dtlb_walk"]) for x in BOOT_ORDER}
# the walk rows (boots C, D, E): 0x34 walks, 0x8188 block walks, 0x818A page walks, per load
WALK_STIM = {x: EX[x]["walk"]["stim"] for x in "CDE"}
WALK_OCM_34 = {x: (min(EX[x]["walk"]["ocm"][r]["erng"]["dtlb_walk"][0] for r in range(5)), max(EX[x]["walk"]["ocm"][r]["erng"]["dtlb_walk"][1] for r in range(5))) for x in "CDE"}
WALK_OCM_BLOCK_MAX = {x: max(EX[x]["walk"]["ocm"][r]["erng"]["dtlb_walk_block"][1] for r in range(5)) for x in "CDE"}
WALK_OCM_PAGE_MAX = {x: max(EX[x]["walk"]["ocm"][r]["erng"]["dtlb_walk_page"][1] for r in range(5)) for x in "CDE"}
WALK_STIM_PAGE_EQ = all(abs(WALK_STIM[x]["emean"]["dtlb_walk"] - WALK_STIM[x]["emean"]["dtlb_walk_page"]) < 1e-3 and WALK_STIM[x]["emean"]["dtlb_walk_block"] == 0.0 for x in "CDE")
WALK_OCM_PASSES = {x: sum(EX[x]["walk"]["ocm"][r]["n"] for r in range(5)) for x in "CDE"}
WALK_OCM_NONZERO = {x: sum(1 for r in range(5) for p in EX[x]["walk"]["ocm"][r]["passes"] if p["e"]["dtlb_walk"] > 0) for x in "CDE"}

# ---- boot E: the L3 turned on, against boot C (same commit, build, TF-A, kernel; only the SCP differs, and the OCM mapping)
E_L3, C_L3 = EX["E"]["l3"], EX["C"]["l3"]
assert E_L3["sizes"] == C_L3["sizes"] == L3_SIZES
L3_HIT_SIZES = [s for s in L3_SIZES if E_L3["hit_rng"][s][0] > 0.1]   # the sizes whose every rep hits in the L3 on boot E
EC_LV = [(d["size"], d["kind"], c["ns"], d["ns"]) for d in BT["E"]["LV"] for c in BT["C"]["LV"] if c["size"] == d["size"] and c["kind"] == d["kind"]]
EC_RATIO = {(s, k): e / c for s, k, c, e in EC_LV}
EC_SMALL_RATIO = [e / c for s, k, c, e in EC_LV if k == "repeat" and s <= 131072]
E_L2_NS = E_L3["best"][131072]["ns"]   # the 128 KiB hit-set row on E: an L2 hit on nearly every load
C_MESH_NS = C_L3["best"][393216]["ns"]   # the 384 KiB hit-set row on C: a read from the mesh on nearly every load
def l3_hit_est(s):
    """est. ns of one L3 hit from E's hit-set row at size s: the row's time less its L2 hits at the L2 hop and its outside refills at C's mesh hop, over its L3 hits"""
    d = E_L3["best"][s]["e"]
    return (E_L3["best"][s]["ns"] - d["l2d_hit_rd"] * E_L2_NS - d["l3d_refill_rd"] * C_MESH_NS) / d["l3d_hit_rd"]
L3_HIT_EST = {s: l3_hit_est(s) for s in (262144, 393216)}
E_SEQ, C_SEQ = BT["E"]["SEQ"], BT["C"]["SEQ"]
E_ABOVE_16_32 = {s: BT["E"]["LV"][[i for i, d in enumerate(BT["E"]["LV"]) if d["size"] == s and d["kind"] == "fresh"][0]]["ns"] - max(BT[x]["LV"][[i for i, d in enumerate(BT[x]["LV"]) if d["size"] == s and d["kind"] == "fresh"][0]]["ns"] for x in "ABCD") for s in (16777216, 33554432)}
# E's OCM rows: the sparse per-region rows partly hit in the L3 (0xA2 below one per hop); the dense all-five row keeps one outside refill per hop
E_SPARSE_L3 = [BT["E"]["SPLIT"][(c, r, "sparse")]["l3"] for c in (2, 8) for r in range(5)]
AC_SPARSE_L3 = [BT[x]["SPLIT"][(c, r, "sparse")]["l3"] for x in "AC" for c in (2, 8) for r in range(5)]
E_ALL5_DENSE_L3 = {c: BT["E"]["SPLIT_ALL5"][(c, "dense")]["l3"] for c in (2, 8)}
ALL5_DENSE_BEST = {x: BT[x]["ALL5"][2]["dense"]["best"] for x in BOOT_ORDER}
# the read variants on the boots that ran them (G7)
RP_BOOTS = [x for x in BOOT_ORDER if EX[x]["rp"]]
RP_CYC = {x: {s: EX[x]["rp"][("read", s)]["e"]["cycles_per_line"] for s in RP_SIZES} for x in RP_BOOTS}
# the CME on E against C: the small chases with inner and outer refills
EC_CLV = [(d["size"], c, d) for d in BT["E"]["CLV"] for c in BT["C"]["CLV"] if c["size"] == d["size"] and c["kind"] == d["kind"] == "repeat"]
EC_CLV_RATIO = {s: d["ns"] / c["ns"] for s, c, d in EC_CLV}
CME_INNER_SHARE = {x: {d["size"]: d["emean"]["cme_l1d_refill_inner"] / max(1e-9, d["emean"]["cme_l1d_refill_inner"] + d["emean"]["cme_l1d_refill_outer"]) for d in BT[x]["CLV"] if d["kind"] == "repeat" and d["size"] >= 8192} for x in "ACE"}
# the G8 rows (boots C and E)
G8 = {x: EX[x]["g8"] for x in BOOT_ORDER if EX[x]["g8"]}
G8_SIZES = (4096, 8192, 16384, 24576)
G8_READ_OK = all(G8[x][(f, "read")]["ok"] for x in G8 for f in ("per-pass", "asm")); G8_WRITE_OK = all(G8[x][(f, "write")]["ok"] for x in G8 for f in ("per-pass", "asm"))
G8_L1_MAX = max(v["l1"] for x in G8 for g in G8[x].values() for v in g["rows"].values())
G8_MARGINAL = {(x, f): 1 / ((G8[x][(f, "read")]["rows"][16384]["t_pass"] - G8[x][(f, "read")]["rows"][8192]["t_pass"]) / 8192) for x in G8 for f in ("per-pass", "asm")}   # GB/s between the 8 and 16 KiB rows
# the five boots side by side
def lv_ns(x, size, kind="repeat"): return next(d["ns"] for d in BT[x]["LV"] if d["size"] == size and d["kind"] == kind)
FIVE = [("Commit", {x: EX[x]["commit"] for x in BOOT_ORDER}), ("SCP", {x: EX[x]["scp"] for x in BOOT_ORDER}), ("TF-A", {x: EX[x]["tfa"] for x in BOOT_ORDER}),
        ("Data prefetchers", {x: "on" if EX[x]["pf_on"] else "off" for x in BOOT_ORDER}), ("OCM mapping", {x: "64 KiB contiguous" if EX[x]["cont"] else "4 KiB pages" for x in BOOT_ORDER}),
        ("IMP_CLUSTERPWRSTAT_EL1 of CPU 2's cluster", {x: ", ".join(EX[x]["pwrstat"]) or "not read" for x in BOOT_ORDER}),
        ("L3 read hits per load at 256 KiB", {x: f"{EX[x]['l3']['hit_rng'][262144][0]:.4f} to {EX[x]['l3']['hit_rng'][262144][1]:.4f}" if EX[x]["l3"] else "no such row" for x in BOOT_ORDER}),
        ("Chase, 256 KiB, ns", {x: f"{lv_ns(x, 262144):.3f}" for x in BOOT_ORDER}), ("Chase, 2 MiB, ns", {x: f"{lv_ns(x, 2097152, 'fresh'):.3f}" for x in BOOT_ORDER}), ("Chase, 32 MiB, ns", {x: f"{lv_ns(x, 33554432, 'fresh'):.3f}" for x in BOOT_ORDER}),
        ("Sequential chain, 8 MiB, ns", {x: f"{BT[x]['SEQ']['ns']:.3f}" for x in BOOT_ORDER}), ("Plain one-core read of 32 MiB, GB/s", {x: f"{EX[x]['rp'][('read', 33554432)]['agg']:.3f}" if EX[x]["rp"] else "no such row" for x in BOOT_ORDER}),
        ("Chip time, s; commands", {x: f"{BT[x]['CHIP_S']:.3f}; {len(BT[x]['CMDS'])}" for x in BOOT_ORDER})]
for x in "CDE":
    FACTS["boot" + x] = dict(run=f"membench-jibin-{BOOT_RUN_ID[x]} boot {x} (commit {EX[x]['commit']}, prefetchers {'on' if EX[x]['pf_on'] else 'off'}, OCM {'in 64 KiB contiguous translations' if EX[x]['cont'] else 'in 4 KiB pages'}, SCP {EX[x]['scp']})",
                             chip_s=BT[x]["CHIP_S"], commands=len(BT[x]["CMDS"]), ctrl_4k=BT[x]["P4K"]["ns"], rt=BT[x]["RT_NS"], pwrstat=EX[x]["pwrstat"], seq_ns=BT[x]["SEQ"]["ns"], flushed_ns=BT[x]["FLUSHED"]["ns"],
                             l3rows={s: dict(ns=EX[x]["l3"]["best"][s]["ns"], l2hit=EX[x]["l3"]["best"][s]["e"]["l2d_hit_rd"], l3hit=EX[x]["l3"]["best"][s]["e"]["l3d_hit_rd"], l3refill=EX[x]["l3"]["best"][s]["e"]["l3d_refill_rd"]) for s in L3_SIZES},
                             chase={s: lv_ns(x, s) for s in (196608, 262144, 393216)}, chase_fresh={s: lv_ns(x, s, "fresh") for s in (524288, 1048576, 2097152, 33554432)},
                             read_variants={f"{k}@{s}": EX[x]["rp"][(k, s)]["agg"] for k, _ in RP_KERNELS for s in RP_SIZES},
                             ocm_all5_dense=ALL5_DENSE_BEST[x], tlb_per_pass=TLB_PASS_RNG[x], gap=GAP[x], cme=dict(k8=next(d["ns"] for d in BT[x]["CLV"] if d["kind"] == "repeat" and d["size"] == 8192), k64=next(d["ns"] for d in BT[x]["CLV"] if d["kind"] == "repeat" and d["size"] == 65536),
                             ocm_sparse_best=(min(BT[x]["COCM"][r]["sparse"]["best"] for r in range(5)), max(BT[x]["COCM"][r]["sparse"]["best"] for r in range(5))), ocm_all5_dense=BT[x]["CALL5"]["dense"]["best"]))
FACTS["bootE"].update(l3_hit_est=L3_HIT_EST, sparse_l3=(min(E_SPARSE_L3), max(E_SPARSE_L3)), all5_dense_l3=E_ALL5_DENSE_L3)
FACTS["ratios"] = {f"{a}/{b}": {k: v for k, v in RATIOS[(a, b)].items() if k != "rows"} for a, b, _ in PAIRS}
FACTS["h4"] = dict(supported=H4_SUPPORTED, tlb_fell=H4_TLB_FELL, gap_mean=GAP_MEAN, closed=H4_GAP_CLOSED)
FACTS["g8"] = {x: {f"{f} {k}": dict(a_ns=v["a_ns"], rate=v["rate"], resid_pct=v["resid_pct"], ok=v["ok"], best={s: r["agg"] for s, r in v["rows"].items()}) for (f, k), v in G8[x].items()} for x in G8}

