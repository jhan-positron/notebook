#!/usr/bin/env python3
"""Build the run 4 pages from boot A (membench-jibin-005) with run 3 (004) and run 2 (002) beside it:

  asimov-c1nano-run4.html   the C1-Nano core: prefetch-refill and TLB counters on the chase rows, the
                            per-region routes under the crosspoint counters, the write-cost check
  asimov-cme-run4.html      the CME: its L1 refills by cause (demand read, hardware prefetch, write)

Every number on both pages is read from results/membench-jibin-005/results/bootA/ (and dmesg.txt beside it)
by this script, or from run 3 and run 2 through gen_run3.py. The typed-in numbers are platform facts quoted
from Jesse's README files (cited where used). Boots B to E (006, 007, 008, 010) are read through the same load_boot
under results/membench-jibin-00N/results/boot<X>/; until then every cross-boot comparison is Insufficient data.
"""
import os, re, glob, statistics, collections, sys, math

A = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, A)
import gen_run3 as g   # readers, chart helpers, page shell, and the run 2 / run 3 numbers (computed at import)
from gen_run3 import (lat_rows, bw_rows, kib, best, passes, best_pass, fmt, tr, table, pct, esc, C, SVG, legend, legend_rows,
                      line_chart, bars_h, page, fig, words, NODES, DSUS, NODE_OF_REGION, CPU_DSU, dist)

R5 = A + "/results/membench-jibin-005/"
RA = R5 + "results/bootA/"
OUT_CORE = A + "/asimov-c1nano-run4.html"
OUT_CME = A + "/asimov-cme-run4.html"

# ---------------------------------------------------------------- readers on top of gen_run3's
def counter_names(path):
    """the counter column names of a latency CSV, without the _per_load suffix: c1..cN in order"""
    for line in open(path):
        if line.startswith("mem,"):
            cols = line.rstrip("\n").split(",")
            return [c.replace("_per_load", "") for c in cols[7:-1]]
    raise KeyError(path)

def lat(path):
    """lat_rows plus, on each measured row, e = {counter name: value} (None for a refused or invalid counter)"""
    names = counter_names(path); rows = lat_rows(path)
    for d in rows:
        if "c1" in d: d["e"] = {n: d[f"c{i + 1}"] for i, n in enumerate(names)}
    return rows

def timed(rows, size):
    """the timed passes of a size: run 3's passes() without the CME controls"""
    return passes(rows, size)

def mean_e(ps, key): return statistics.mean(p["e"][key] for p in ps)
def corr0(xs, ys):
    """g.corr, or nan when a series is constant (every prefetch count is 0 on a prefetcher-off boot)"""
    return g.corr(xs, ys) if max(xs) > min(xs) and max(ys) > min(ys) else float("nan")
def rng_e(ps, key): return (min(p["e"][key] for p in ps), max(p["e"][key] for p in ps))

def route_rows(path):
    """cmn-counts.csv of G6: label -> dict(dirs={(node id, dir): count}, child=, helper=); every row must be unmultiplexed"""
    out = collections.defaultdict(lambda: dict(dirs={}))
    for line in open(path):
        if line.startswith("#") or line.startswith("label,"): continue
        lab, ev, node, cnt, en, run, sc = line.rstrip("\n").split(",")
        assert en == run, (lab, ev)
        e = out[lab]
        m = re.match(r"mxp_([ewns])_dat_txflit_valid$", ev)
        if m: e["dirs"][(int(node), m.group(1))] = int(cnt)
        elif ev == "child_elapsed_ns": e["child"] = int(cnt)
        elif ev == "helper_elapsed_ns": e["helper"] = int(cnt)
    return out

def load_boot(R, boot):
    """read one boot (results/<boot>/ under the run directory R) into a dict of every table this module computes for a boot"""
    RA = R + f"results/{boot}/"
    # ---------------------------------------------------------------- the boot's record
    README = open(R + "README.md").read()
    LOG = open(RA + "log.txt").read()
    SYSINFO = open(RA + "sysinfo.txt").read()
    PMU_COUNTERS = int(re.search(r"armv9_c1_nano PMU driver, (\d+) \(", SYSINFO).group(1))
    CHIP_S = float(re.search(r"ns=(\d+)", README).group(1)) / 1e9 if re.search(r"ns=(\d+)", README) else None
    CMDS = [re.sub(r"\s*\[uptime.*$", "", re.sub(r"/opt/membench/[^ ]*/", "", l[2:].rstrip("\n"))) for l in LOG.splitlines() if l.startswith("+ ")]
    FAILED = int(re.search(r"(\d+) measurement command\(s\) failed", LOG).group(1))
    N_PERF_FLAG = sum(1 for f in glob.glob(RA + "*.csv") for l in open(f) if l.startswith("# perf:"))
    assert FAILED == 0 and N_PERF_FLAG == 0
    assert "cpu3 online=0" in LOG and "cpu3 online=1" in LOG

    def cmd_key(c):
        """(cpu, cme, events, regions tuple, shape, route label) of an OCM latency command line, or None"""
        if "--mem ocm" not in c: return None
        cpu = int(re.search(r"--cpu (\d+)", c).group(1)); cme = "--cme" in c
        ev = re.search(r"--events (\w+)", c); ev = ev.group(1) if ev else "prefetch"
        regions = tuple(int(x) for x in re.search(r"--ocm-regions ([\d,]+)", c).group(1).split(","))
        shape = "vary" if "--sparse-vary" in c else "sparse" if "--sparse" in c else "dense"
        route = re.match(r"xp (\S+) ", c); route = route.group(1) if route else None
        return (cpu, cme, ev, regions, shape, route)
    OCM_CMDS = [cmd_key(c) for c in CMDS if cmd_key(c)]

    # the kernel log's /dev/ocm mapping lines, one per mapped region, grouped by the mapping process and matched to the
    # OCM commands in the log's order (checked: one group per command and each group's regions are the command's regions)
    MAPS = []
    for l in open(R + "dmesg.txt"):
        # boot A's module line: pid, va, pa, len, prot; from boot B the module adds comm= and the page-table fields pte=, cont=<n>/64, same=<n>/64
        m = re.search(r"membench_ocm: map pid=(\d+)(?: comm=\S+)? va=0x([0-9a-f]+) pa=0x([0-9a-f]+) len=0x([0-9a-f]+) prot=0x([0-9a-f]+)", l)
        if not m: continue
        pid, va, pa, ln, prot = int(m.group(1)), int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16), m.group(5)
        assert ln == 262144 and (pa - 0xE0000000) % (1 << 20) == 0 and prot == "68000000000fc3", l
        d = va - pa
        cont = re.search(r" cont=(\d+)/(\d+)", l)   # entries with the contiguous hint, over the mapping's entries (None on boot A)
        MAPS.append(dict(pid=pid, region=(pa - 0xE0000000) >> 20, align=64 if d % 65536 == 0 else 32 if d % 32768 == 0 else 16 if d % 16384 == 0 else 4,
                         cont=(int(cont.group(1)), int(cont.group(2))) if cont else None))
    groups = [list(v) for k, v in __import__("itertools").groupby(MAPS, key=lambda m: m["pid"])]
    assert len(MAPS) == sum(len(k[3]) for k in OCM_CMDS) and len(groups) == len(OCM_CMDS), (len(MAPS), len(groups), len(OCM_CMDS))   # 110 on boots A and B, 115 with the five walk rows
    assert all(gr[0]["pid"] < gr2[0]["pid"] for gr, gr2 in zip(groups, groups[1:]))
    ALIGN = {}   # command key -> alignment of its mapping(s) in KiB (4 = none)
    for key, gr in zip(OCM_CMDS, groups):
        assert tuple(m["region"] for m in gr) == key[3], (key, gr)
        ALIGN[key] = [m["align"] for m in gr]
    ALIGN_COUNT = collections.Counter(m["align"] for m in MAPS)

    # ---------------------------------------------------------------- controls (G-e, G-f)
    CTRL = {c: best(lat(f"{RA}latency-control-cpu{c}.csv"))["ns"] for c in (2, 8)}
    P4K = best_pass(lat(RA + "latency-dram-small.csv"), 4096)
    RT = [d for f in sorted(glob.glob(RA + "cme-latency-*.csv")) for d in lat(f) if d["mode"] == "cme-roundtrip"]
    RT_NS = (min(d["ns"] for d in RT), max(d["ns"] for d in RT))
    COV_ROWS = [d for f in sorted(glob.glob(RA + "latency-*.csv")) + sorted(glob.glob(RA + "cme-latency-*.csv")) for d in lat(f) if "cov" in d]
    assert all(d["cov"] == 1.0 for d in COV_ROWS)
    CTRL_OK = abs(P4K["ns"] - 2.0) / 2.0 < 0.005 and RT_NS[1] <= 21.0 * 1.005 and RT_NS[0] >= 21.0 * 0.995

    # ---------------------------------------------------------------- G1: the core sweep with the prefetch columns
    def sweep(prefix):
        small, large, flushed, seq = (lat(RA + prefix + f) for f in ("latency-dram-small.csv", "latency-dram-large.csv", "latency-dram-flushed.csv", "latency-dram-seq.csv"))
        out = []
        for rows, kind in ((small, "repeat"), (large, "fresh"), (flushed, "flushed"), (seq, "seq")):
            for d in rows:
                if not d["mode"].endswith("best") or "roundtrip" in d["mode"] or "call" in d["mode"]: continue
                ps = timed(rows, d["size"]); bp = best_pass(rows, d["size"])
                out.append(dict(size=d["size"], kind=kind, ns=d["ns"], e=bp["e"], emean={k: mean_e(ps, k) for k in bp["e"]}, erng={k: rng_e(ps, k) for k in bp["e"]}, n=len(ps),
                                ns_rng=(min(p["ns"] for p in ps), max(p["ns"] for p in ps))))
        return out
    LV = sweep("")
    RUN3_LV = {(d["size"], d["kind"]): d["ns"] for d in g.LV4}
    for d in LV: d["ns3"] = RUN3_LV.get((d["size"], d["kind"]))
    SEQ = [d for d in LV if d["kind"] == "seq"][0]; FLUSHED = [d for d in LV if d["kind"] == "flushed"][0]
    L2HIT_NS = [d for d in LV if d["size"] == 131072][0]["ns"]

    # event validation (G-a): the sequential chain is the stimulus
    EV_CORE = [
        ("0x81BC", "l1d_refill_hwprf", "L1D refills requested by a hardware prefetcher"),
        ("0x81BD", "l2d_refill_hwprf", "L2 refills for accesses generated by hardware prefetchers targeting the L2"),
        ("0x0111", "l2d_refill_l1dhwprf", "L2 refills for accesses from L1D hardware prefetches"),
    ]

    # ---------------------------------------------------------------- G2: the OCM rows (dense, sparse, vary; CPUs 2 and 8), the TLB set (CPU 2)
    SHAPES = ("dense", "sparse", "vary")
    def ocm_file(c, r, shape, ev="prefetch", cme=False):
        base = "cme-latency-ocm-" if cme else "latency-ocm-"
        name = base + (f"region{r}" if r is not None else "all5") + ("-dense" if shape == "dense" and r is None else "" if shape == "sparse" else f"-{shape}" if shape != "dense" else "-dense") + ("-tlb" if ev == "tlb" else "")
        if r is None and shape == "dense": name = base + "all5-dense"
        if r is None and shape == "sparse": name = base + "all5"
        return name + ("" if cme else f"-cpu{c}") + ".csv"
    def ocm_row(c, r, shape, ev="prefetch", cme=False):
        f = ocm_file(c, r, shape, ev, cme); rows = lat(RA + f); size = 262144 if r is not None else 1310720
        ps = timed(rows, size); bp = best_pass(rows, size)
        key = (c, cme, ev, (r,) if r is not None else (0, 1, 2, 3, 4), shape, None)
        return dict(file=f, cpu=c, region=r, shape=shape, best=best(rows, size=size)["ns"], median=statistics.median(p["ns"] for p in ps), n=len(ps),
                    ns_rng=(min(p["ns"] for p in ps), max(p["ns"] for p in ps)), hops=int(bp["loads"]), align=ALIGN[key],
                    passes=[dict(ns=p["ns"], e=p["e"]) for p in ps], e=bp["e"], emean={k: mean_e(ps, k) for k in bp["e"]}, erng={k: rng_e(ps, k) for k in bp["e"]},
                    dist=dist(c, NODE_OF_REGION[r]) if r is not None else None)
    OCM = {c: {r: {s: ocm_row(c, r, s) for s in SHAPES} for r in range(5)} for c in (2, 8)}
    ALL5 = {c: {s: ocm_row(c, None, s) for s in ("dense", "sparse")} for c in (2, 8)}
    TLB = {r: {s: ocm_row(2, r, s, "tlb") for s in SHAPES} for r in range(5)}
    TLB_STIM = lat(RA + "latency-dram-tlb-cpu2.csv"); TLB_STIM_P = timed(TLB_STIM, 33554432); TLB_STIM_BEST = best(TLB_STIM)["ns"]
    assert all(TLB[r][s]["e"]["l2d_tlb_refill"] == 0.0 for r in TLB for s in SHAPES)   # read below as a measured zero

    # L2 refills split by cause on every OCM row (H1): "demand" here means not counted by 0x81BD, a labelled difference
    def split(row):
        l2 = row["emean"]["l2d_refill"]; pf = row["emean"]["l2d_refill_hwprf"]
        return dict(l2=l2, pf=pf, rest=l2 - pf, l3=row["emean"]["l3d_refill_rd"], l1=row["emean"]["l1d_refill"], l1pf=row["emean"]["l1d_refill_hwprf"], l1dpf=row["emean"]["l2d_refill_l1dhwprf"])
    SPLIT = {(c, r, s): split(OCM[c][r][s]) for c in OCM for r in range(5) for s in SHAPES}
    SPLIT_ALL5 = {(c, s): split(ALL5[c][s]) for c in ALL5 for s in ("dense", "sparse")}
    PF_DENSE = [SPLIT[(c, r, "dense")]["pf"] for c in OCM for r in range(5)]; PF_PAGE = [SPLIT[(c, r, s)]["pf"] for c in OCM for r in range(5) for s in ("sparse", "vary")]
    REST_MINUS_L3 = [v["rest"] - v["l3"] for v in SPLIT.values()]   # L2 refills not by the L2 prefetcher, minus L3 read refills
    L1PF_MAX = max(max(v["l1pf"], v["l1dpf"]) for v in SPLIT.values())
    def shape_stat(c, s, key): return [SPLIT[(c, r, s)][key] for r in range(5)]
    # within-row correlation of pass time with the L2 prefetch refills (pooled, each row's mean removed), sparse and vary rows
    def within(shape_list, key):
        xs, ys = [], []
        for c in OCM:
            for r in range(5):
                for s in shape_list:
                    ps = OCM[c][r][s]["passes"]; mn, mk = statistics.mean(p["ns"] for p in ps), statistics.mean(p["e"][key] for p in ps)
                    xs += [p["ns"] - mn for p in ps]; ys += [p["e"][key] - mk for p in ps]
        return corr0(xs, ys)
    CORR_PF = within(("sparse", "vary"), "l2d_refill_hwprf"); CORR_L3 = within(("sparse", "vary"), "l3d_refill_rd"); CORR_L2 = within(("sparse", "vary"), "l2d_refill")
    # H2: vary against sparse, per cell
    H2_CELLS = [(c, r, SPLIT[(c, r, "vary")]["l3"] - SPLIT[(c, r, "sparse")]["l3"], OCM[c][r]["vary"]["median"] - OCM[c][r]["sparse"]["median"], OCM[c][r]["vary"]["best"] - OCM[c][r]["sparse"]["best"]) for c in OCM for r in range(5)]
    H2_MORE_L3 = sum(1 for x in H2_CELLS if x[2] > 0)
    VARY_FASTER_MED = sum(1 for x in H2_CELLS if x[3] < 0); VARY_FASTER_BEST = sum(1 for x in H2_CELLS if x[4] < 0)
    SPARSE_MINUS_DENSE = {c: [OCM[c][r]["sparse"]["best"] - OCM[c][r]["dense"]["best"] for r in range(5)] for c in OCM}
    # TLB (H3): the sparse rows' L1 TLB refills per hop and walks per hop; the dense rows' by alignment
    H3_L1 = [TLB[r]["sparse"]["emean"]["l1d_tlb_refill"] for r in range(5)]; H3_WALK = [TLB[r]["sparse"]["emean"]["dtlb_walk"] for r in range(5)]
    VARY_L1 = [TLB[r]["vary"]["emean"]["l1d_tlb_refill"] for r in range(5)]; VARY_WALK = [TLB[r]["vary"]["emean"]["dtlb_walk"] for r in range(5)]
    DENSE_L1 = [TLB[r]["dense"]["emean"]["l1d_tlb_refill"] for r in range(5)]; DENSE_WALK = [TLB[r]["dense"]["emean"]["dtlb_walk"] for r in range(5)]
    STIM_E = {k: mean_e(TLB_STIM_P, k) for k in TLB_STIM_P[0]["e"]}

    # run 3 (sparse) and run 2 (dense) per cell, from gen_run3
    R3_SPARSE = {(c, r): g.OCM[c][r]["best"] for c in (2, 4, 6, 8) for r in range(5)}
    R2_DENSE = {(c, r): g.OCM2[c][r]["best"] for c in (2, 4, 6, 8) for r in range(5)}

    # ---------------------------------------------------------------- G6: the route rows and the crosspoint counters
    CMN = route_rows(RA + "cmn-counts.csv")
    XP_ID = lambda x, y: 64 * x + 8 * y
    def first_dir(a, b):
        """the outgoing direction from crosspoint a to crosspoint b if the route takes its X steps first ('e','w'), else its Y step ('n','s')"""
        (x1, y1), (x2, y2) = a, b
        if x2 != x1: return "e" if x2 > x1 else "w"
        return "n" if y2 > y1 else "s"
    ROUTE = {}
    for c in (2, 4, 6, 8):
        for r in range(5):
            lab = f"route-ocm{r}-cpu{c}"; e = CMN[lab]
            dsu_xy = DSUS[CPU_DSU[c]][:2]; node = NODE_OF_REGION[r]; node_xy = NODES[node][:2]
            dsu_id = XP_ID(*dsu_xy); assert dsu_id in {152, 208, 280, 336} and node == XP_ID(*node_xy)
            assert c in (2, 4, 6, 8) and re.search(rf"xp {lab} {dsu_id},{node} ", LOG)   # the helper counted the DSU's and the node's crosspoint
            d_dsu = {k[1]: v for k, v in e["dirs"].items() if k[0] == dsu_id}; d_node = {k[1]: v for k, v in e["dirs"].items() if k[0] == node}
            assert len(d_dsu) == 4 and len(d_node) == 4
            dom_dsu = max(d_dsu, key=d_dsu.get); dom_node = max(d_node, key=d_node.get)
            rows = lat(RA + f"latency-ocm-region{r}-route-cpu{c}.csv"); ps = timed(rows, 262144)
            ROUTE[(c, r)] = dict(dsu=dsu_id, node=node, dsu_xy=dsu_xy, node_xy=node_xy, d_dsu=d_dsu, d_node=d_node, dom_dsu=dom_dsu, dom_node=dom_node,
                                 exp_dsu=first_dir(dsu_xy, node_xy), exp_node=first_dir(node_xy, dsu_xy),
                                 share_dsu=d_dsu[dom_dsu] / sum(d_dsu.values()), share_node=d_node[dom_node] / sum(d_node.values()),
                                 best=best(rows, size=262144)["ns"], median=statistics.median(p["ns"] for p in ps), dist=dist(c, node),
                                 dx=abs(dsu_xy[0] - node_xy[0]), dy=abs(dsu_xy[1] - node_xy[1]), child=e["child"], helper=e["helper"],
                                 e=best_pass(rows, 262144)["e"], emean={k: mean_e(ps, k) for k in ps[0]["e"]}, passes=[p["ns"] for p in ps])
    XFIRST_DSU = sum(1 for v in ROUTE.values() if v["dom_dsu"] == v["exp_dsu"]); XFIRST_NODE = sum(1 for v in ROUTE.values() if v["dom_node"] == v["exp_node"])
    SHARE_MIN = min(min(v["share_dsu"], v["share_node"]) for v in ROUTE.values())
    FLITS_DOM = [v["d_dsu"][v["dom_dsu"]] for v in ROUTE.values()] + [v["d_node"][v["dom_node"]] for v in ROUTE.values()]
    HELPER_COST = [v["helper"] - v["child"] for v in ROUTE.values()]

    def fit_xy(cells):
        """least squares of ns = a + bx * |dx| + by * |dy| over cells [(dx, dy, ns)]; returns a, bx, by, rms residual"""
        n = len(cells); S = lambda f: sum(f(*c) for c in cells)
        M = [[n, S(lambda x, y, z: x), S(lambda x, y, z: y)], [S(lambda x, y, z: x), S(lambda x, y, z: x * x), S(lambda x, y, z: x * y)], [S(lambda x, y, z: y), S(lambda x, y, z: x * y), S(lambda x, y, z: y * y)]]
        v = [S(lambda x, y, z: z), S(lambda x, y, z: x * z), S(lambda x, y, z: y * z)]
        det = lambda m: (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
        D = det(M); sol = []
        for i in range(3):
            Mi = [row[:] for row in M]
            for j in range(3): Mi[j][i] = v[j]
            sol.append(det(Mi) / D)
        a, bx, by = sol
        rms = (sum((z - a - bx * x - by * y) ** 2 for x, y, z in cells) / n) ** 0.5
        return dict(a=a, bx=bx, by=by, rms=rms, n=n)
    def dxdy(c, r):
        dsu_xy = DSUS[CPU_DSU[c]][:2]; node_xy = NODES[NODE_OF_REGION[r]][:2]
        return abs(dsu_xy[0] - node_xy[0]), abs(dsu_xy[1] - node_xy[1])
    FIT = dict(route=fit_xy([(*dxdy(c, r), v["best"]) for (c, r), v in ROUTE.items()]),
               route_med=fit_xy([(*dxdy(c, r), v["median"]) for (c, r), v in ROUTE.items()]),
               dense_g2=fit_xy([(*dxdy(c, r), OCM[c][r]["dense"]["best"]) for c in (2, 8) for r in range(5)]),
               run2=fit_xy([(*dxdy(c, r), R2_DENSE[(c, r)]) for c in (2, 4, 6, 8) for r in range(5)]),
               run3=fit_xy([(*dxdy(c, r), R3_SPARSE[(c, r)]) for c in (2, 4, 6, 8) for r in range(5)]))
    H5_XY_DIFF = FIT["route"]["bx"] - FIT["route"]["by"]
    H5_SUPPORTED = abs(H5_XY_DIFF) > FIT["route"]["rms"] and (H5_XY_DIFF > 0) == (FIT["run2"]["bx"] - FIT["run2"]["by"] > 0) == (FIT["run3"]["bx"] - FIT["run3"]["by"] > 0)
    ROUTE_VS_DENSE = [(c, r, ROUTE[(c, r)]["best"] - OCM[c][r]["dense"]["best"]) for c in (2, 8) for r in range(5)]   # the same command, counted and uncounted
    ROUTE_VS_RUN2 = [ROUTE[k]["best"] - R2_DENSE[k] for k in ROUTE]

    # ---------------------------------------------------------------- G5: the write-cost check (H6)
    W = []
    for size in (16384, 49152, 98304, 262144):
        r3 = best(bw_rows(RA + "bandwidth-write-small.csv"), bpt=size)["agg"]; r2 = best(bw_rows(RA + "bandwidth-write-small-r2prog.csv"), bpt=size)["agg"]
        o3 = [d for d in g.ONE if d["size"] == size][0]
        W.append(dict(size=size, r3prog=r3, r2prog=r2, run3=o3["write"], run2=o3["write2"],
                      ns3=size / r3, ns2=size / r2, ns3_orig=size / o3["write"], ns2_orig=size / o3["write2"]))   # ns per pass: bytes / (GB/s) with GB = 1e9
    for d in W: d["delta"] = d["ns3"] - d["ns2"]; d["delta_orig"] = d["ns3_orig"] - d["ns2_orig"]
    H6_SUPPORTED = all(d["delta"] > 0 for d in W)

    # ---------------------------------------------------------------- G3, G4: the CME rows
    CLV = sweep("cme-")
    RUN3_CLV = {(d["size"], d["kind"]): d["ns"] for d in g.CLV}
    for d in CLV: d["ns3"] = RUN3_CLV.get((d["size"], d["kind"]))
    CSEQ = [d for d in CLV if d["kind"] == "seq"][0]; CFLUSHED = [d for d in CLV if d["kind"] == "flushed"][0]
    COCM = {r: {s: ocm_row(2, r, s, cme=True) for s in SHAPES} for r in range(5)}
    CALL5 = {s: ocm_row(2, None, s, cme=True) for s in ("dense", "sparse")}
    CME_ROWS = [d for f in sorted(glob.glob(RA + "cme-latency-*.csv")) for d in lat(f) if "e" in d and "roundtrip" not in d["mode"] and "call" not in d["mode"]]
    CME_WR_MAX = max(d["e"]["cme_l1d_refill_wr"] for d in CME_ROWS)
    CME_CONSIST = [d["e"]["cme_l1d_refill_rd"] + d["e"]["cme_l1d_refill_hwprf"] - d["e"]["cme_l1d_refill_inner"] - d["e"]["cme_l1d_refill_outer"] for d in CME_ROWS]
    CME_CONSIST_REL = [abs(x) / max(1e-9, d["e"]["cme_l1d_refill_inner"] + d["e"]["cme_l1d_refill_outer"]) for x, d in zip(CME_CONSIST, CME_ROWS) if d["e"]["cme_l1d_refill_inner"] + d["e"]["cme_l1d_refill_outer"] > 0.1]
    CME_HWPRF_MAX = max(d["emean"]["cme_l1d_refill_hwprf"] for d in CLV)
    CME_HWPRF_AT = {d["size"]: d["emean"]["cme_l1d_refill_hwprf"] for d in CLV if d["kind"] == "repeat"}
    CME_RD_AT = {d["size"]: d["emean"]["cme_l1d_refill_rd"] for d in CLV if d["kind"] == "repeat"}
    CME_PF_CORR = corr0([d["ns"] for d in CLV if d["kind"] == "repeat"], [d["emean"]["cme_l1d_refill_hwprf"] for d in CLV if d["kind"] == "repeat"])
    CME_L1_FITS = [d for d in CLV if d["kind"] == "repeat" and d["size"] <= 65536]   # footprints within the CME's 64 KiB L1
    CME_SPARSE_RD = [COCM[r]["sparse"]["emean"]["cme_l1d_refill_rd"] for r in range(5)]; CME_SPARSE_PF = [COCM[r]["sparse"]["emean"]["cme_l1d_refill_hwprf"] for r in range(5)]
    CME_VARY_MINUS_SPARSE = [COCM[r]["vary"]["best"] - COCM[r]["sparse"]["best"] for r in range(5)]
    CME_DENSE_MINUS_SPARSE = [COCM[r]["dense"]["best"] - COCM[r]["sparse"]["best"] for r in range(5)]
    R3_COCM = {r: g.COCM[r]["best"] for r in range(5)}

    # ---------------------------------------------------------------- the rows run 3 also ran (drift check)
    R4 = g.R4
    REPEAT = []
    for f in sorted(os.listdir(RA)):
        if not f.endswith(".csv") or f == "cmn-counts.csv" or not os.path.exists(R4 + f): continue
        if f.startswith("bandwidth"): continue   # G5's files share no name with run 3
        a, b = lat_rows(RA + f), lat_rows(R4 + f)
        for d in a:
            if not d["mode"].endswith("best") or "call" in d["mode"]: continue
            m = [e for e in b if e["mode"] == d["mode"] and e["size"] == d["size"]]
            if len(m) == 1: REPEAT.append(dict(file=f, mode=d["mode"], size=d["size"], run4=d["ns"], run3=m[0]["ns"], pct=100 * (d["ns"] - m[0]["ns"]) / m[0]["ns"]))
    REPEAT_SAME = [d for d in REPEAT if "roundtrip" not in d["mode"]]
    REPEAT_SORTED = sorted(REPEAT_SAME, key=lambda d: -abs(d["pct"]))
    N_WITHIN = {t: sum(1 for d in REPEAT_SAME if abs(d["pct"]) <= t) for t in (1, 3, 5)}
    SPARSE_REPEAT = [d for d in REPEAT_SAME if re.match(r"latency-ocm-region\d-cpu\d", d["file"])]

    return {k: v for k, v in locals().items() if k not in ("R", "boot")}

globals().update(load_boot(R5, "bootA"))   # boot A is the module's namespace: the page code below reads it by name

# ---------------------------------------------------------------- facts for the run 3 pages (gen_run3.py, gen_brief.py read run4-bootA-facts.json when it exists)
def resid_corr(pairs):
    """correlation of two samples of the same cells after removing each sample's mean at each distance; pairs: [(dist, a, b)]"""
    by = collections.defaultdict(list)
    for d, a, b in pairs: by[d].append((a, b))
    ma = {d: statistics.mean(a for a, b in v) for d, v in by.items()}; mb = {d: statistics.mean(b for a, b in v) for d, v in by.items()}
    return g.corr([a - ma[d] for d, a, b in pairs], [b - mb[d] for d, a, b in pairs])
RESID = dict(g6_vs_run2=resid_corr([(ROUTE[k]["dist"], ROUTE[k]["best"], R2_DENSE[k]) for k in ROUTE]),
             g2_vs_run2=resid_corr([(OCM[c][r]["dense"]["dist"], OCM[c][r]["dense"]["best"], R2_DENSE[(c, r)]) for c in OCM for r in range(5)]),
             sparse_vs_run3=resid_corr([(OCM[c][r]["sparse"]["dist"], OCM[c][r]["sparse"]["best"], R3_SPARSE[(c, r)]) for c in OCM for r in range(5)]),
             g6_vs_g2_same_boot=resid_corr([(OCM[c][r]["dense"]["dist"], ROUTE[(c, r)]["best"], OCM[c][r]["dense"]["best"]) for c in OCM for r in range(5)]))
_l192 = [d for d in LV if d["size"] == 196608 and d["kind"] == "repeat"][0]; _l32m = [d for d in LV if d["size"] == 33554432][0]
_sp_l1 = [p["e"]["l1d_tlb_refill"] for r in range(5) for p in TLB[r]["sparse"]["passes"]]; _sp_walk = [p["e"]["dtlb_walk"] for r in range(5) for p in TLB[r]["sparse"]["passes"]]
_sp_pf = [p["e"]["l2d_refill_hwprf"] for c in OCM for r in range(5) for p in OCM[c][r]["sparse"]["passes"]]; _de_pf = [p["e"]["l2d_refill_hwprf"] for c in OCM for r in range(5) for p in OCM[c][r]["dense"]["passes"]]
# the CME facts the run 3 CME pages quote (run4-bootA-facts.json); counts are pass means, times the best pass
def _clv(size, kind): return [d for d in CLV if d["size"] == size and d["kind"] == kind][0]
def _rdpf(d): return dict(ns=d["ns"], rd=d["emean"]["cme_l1d_refill_rd"], pf=d["emean"]["cme_l1d_refill_hwprf"])
_csp = [p["e"] for r in COCM for p in COCM[r]["sparse"]["passes"]]   # every sparse pass of the five region rows
CME_FACTS = dict(
    consist_rel=max(CME_CONSIST_REL), wr_max=CME_WR_MAX, pf8k=CME_HWPRF_AT[8192], rd8k=CME_RD_AT[8192], pf32k=CME_HWPRF_AT[32768], pf64k=CME_HWPRF_AT[65536], rd32k=CME_RD_AT[32768], rd64k=CME_RD_AT[65536], pf_max=CME_HWPRF_MAX,
    seq_ns=CSEQ["ns"], seq_pf=CSEQ["e"]["cme_l1d_refill_hwprf"], seq_rd=CSEQ["e"]["cme_l1d_refill_rd"],
    k4=_rdpf(_clv(4096, "repeat")),
    rd_from8k=(min(v for s, v in CME_RD_AT.items() if s >= 8192), max(v for s, v in CME_RD_AT.items() if s >= 8192)),
    pf_from8k=(min(v for s, v in CME_HWPRF_AT.items() if s >= 8192), max(v for s, v in CME_HWPRF_AT.items() if s >= 8192)),
    dram2m=_rdpf(_clv(2097152, "fresh")), flushed=_rdpf(CFLUSHED), l32m=_rdpf(_clv(33554432, "fresh")),
    ocm_sparse_best=(min(COCM[r]["sparse"]["best"] for r in COCM), max(COCM[r]["sparse"]["best"] for r in COCM)),
    ocm_dense_best=(min(COCM[r]["dense"]["best"] for r in COCM), max(COCM[r]["dense"]["best"] for r in COCM)),
    ocm_all5_dense=CALL5["dense"]["best"], ocm_all5_sparse=CALL5["sparse"]["best"],
    ocm_sparse_tot=(min(e["cme_l1d_refill_inner"] + e["cme_l1d_refill_outer"] for e in _csp), max(e["cme_l1d_refill_inner"] + e["cme_l1d_refill_outer"] for e in _csp)),
    ocm_sparse_rd=(min(e["cme_l1d_refill_rd"] for e in _csp), max(e["cme_l1d_refill_rd"] for e in _csp)),
    ocm_dense_rd=(min(COCM[r]["dense"]["emean"]["cme_l1d_refill_rd"] for r in COCM), max(COCM[r]["dense"]["emean"]["cme_l1d_refill_rd"] for r in COCM)),
    ocm_dense_pf=(min(COCM[r]["dense"]["emean"]["cme_l1d_refill_hwprf"] for r in COCM), max(COCM[r]["dense"]["emean"]["cme_l1d_refill_hwprf"] for r in COCM)),
)
FACTS = dict(
    run="membench-jibin-005 boot A (commit e8e4580, 2026-11-04)", chip_s=CHIP_S, commands=len(CMDS), ctrl_4k=P4K["ns"], rt=RT_NS, shared_rows=len(REPEAT_SAME), within3=N_WITHIN[3],
    write=[dict(size=d["size"], delta=d["delta"], delta_orig=d["delta_orig"], r3prog=d["r3prog"], r2prog=d["r2prog"]) for d in W], h6=H6_SUPPORTED,
    rest_minus_l3_max=max(abs(x) for x in REST_MINUS_L3),
    l192=dict(ns=_l192["ns"], l2=_l192["emean"]["l2d_refill"], pf=_l192["emean"]["l2d_refill_hwprf"], l3=_l192["emean"]["l3d_refill_rd"], l1=_l192["emean"]["l1d_refill"]),
    l32m=dict(ns=_l32m["ns"], pf=_l32m["e"]["l2d_refill_hwprf"], l1pf=_l32m["e"]["l1d_refill_hwprf"], l3=_l32m["e"]["l3d_refill_rd"]),
    flushed=dict(ns=FLUSHED["ns"], pf=FLUSHED["e"]["l2d_refill_hwprf"], l1pf=FLUSHED["e"]["l1d_refill_hwprf"], l3=FLUSHED["e"]["l3d_refill_rd"]),
    seq=dict(ns=SEQ["ns"], l1pf=SEQ["e"]["l1d_refill_hwprf"]),
    same_boot_repeat=(min(x[2] for x in ROUTE_VS_DENSE), max(x[2] for x in ROUTE_VS_DENSE)), resid=RESID,
    sparse_l1tlb=(min(_sp_l1), max(_sp_l1)), sparse_l1tlb_mean=(min(H3_L1), max(H3_L1)), sparse_walk=(min(_sp_walk), max(_sp_walk)), sparse_walk_mean=(min(H3_WALK), max(H3_WALK)),
    sparse_pf=(min(_sp_pf), max(_sp_pf)), dense_pf=(min(_de_pf), max(_de_pf)), sparse_pf_mean=(min(shape_stat(2, "sparse", "pf") + shape_stat(8, "sparse", "pf")), max(shape_stat(2, "sparse", "pf") + shape_stat(8, "sparse", "pf"))),
    dense_pf_mean=(min(shape_stat(2, "dense", "pf") + shape_stat(8, "dense", "pf")), max(shape_stat(2, "dense", "pf") + shape_stat(8, "dense", "pf"))),
    vary_minus_sparse_med=(min(x[3] for x in H2_CELLS), max(x[3] for x in H2_CELLS)), vary_faster_med=VARY_FASTER_MED, h2_more_l3=H2_MORE_L3,
    sparse_minus_dense=(min(SPARSE_MINUS_DENSE[2] + SPARSE_MINUS_DENSE[8]), max(SPARSE_MINUS_DENSE[2] + SPARSE_MINUS_DENSE[8])),
    xfirst=(XFIRST_DSU, XFIRST_NODE), fit=dict(bx=FIT["route"]["bx"], by=FIT["route"]["by"], rms=FIT["route"]["rms"]),
    cme=CME_FACTS,
)

# ---------------------------------------------------------------- boot B (membench-jibin-006, commit 7921962): the data prefetchers off
R6 = A + "/results/membench-jibin-006/"
B = load_boot(R6, "bootB"); RB = R6 + "results/bootB/"
B_PWRSTAT = re.findall(r"# box clusterpwrstat (before|after) l3: (0x[0-9a-f]+)", B["LOG"]); assert len(B_PWRSTAT) == 2
B_TFA = re.search(r"TF-A (0\.35\.0-pfoff\.\d+) \(`([0-9a-f]+)`", B["README"])
B_PF_ROWS = [d for f in sorted(glob.glob(RB + "latency-*.csv")) + sorted(glob.glob(RB + "cme-latency-*.csv")) for d in lat(f) if "e" in d and any("hwprf" in k for k in d["e"])]
B_PF_MAX = max(v for d in B_PF_ROWS for k, v in d["e"].items() if "hwprf" in k)   # every prefetch refill counter on the boot
L3ROWS = [d for d in lat(RB + "latency-dram-small-l3.csv") if d["mode"] == "repeat"]   # the hit set: 0x81C5 L2 read hits, 0xA0 L3 read accesses, 0x81C6 L3 read hits
L3_SIZES = sorted(set(d["size"] for d in L3ROWS))
L3_BEST = {s: min((d for d in L3ROWS if d["size"] == s), key=lambda d: d["ns"]) for s in L3_SIZES}
L3_HIT_MAX = max(d["e"]["l3d_hit_rd"] for d in L3ROWS)
L3_ACC_VS_REFILL = max(abs(d["e"]["l3d_access_rd"] - d["e"]["l3d_refill_rd"]) for d in L3ROWS)
RP = bw_rows(RB + "bandwidth-read-prefetch.csv")   # the run 5 read variants, one core, 2 MiB and 32 MiB
RP_KERNELS = [("read", "plain loop"), ("read-pf4", "PRFM 4 lines ahead"), ("read-pf8", "PRFM 8 lines ahead"), ("read-pf16", "PRFM 16 lines ahead"), ("read-2s", "two streams")]
RP_SIZES = (2097152, 33554432)
RP_BEST = {(k, s): best(RP, kernel=k, bpt=s)["agg"] for k, _ in RP_KERNELS for s in RP_SIZES}
RP_RUN3 = {s: next(d["read"] for d in g.ONE if d["size"] == s) for s in RP_SIZES}   # run 3's plain one-core read, prefetchers on
AB_LV = [(d["size"], d["kind"], d["ns"], e["ns"]) for d in LV for e in B["LV"] if e["size"] == d["size"] and e["kind"] == d["kind"]]
AB_CLV = [(d["size"], d["kind"], d["ns"], e["ns"]) for d in CLV for e in B["CLV"] if e["size"] == d["size"] and e["kind"] == d["kind"]]
AB_LV_RANDOM_PCT = [100 * (b - a) / a for s, k, a, b in AB_LV if k != "seq"]
B_CELLS = [dict(c=c, r=r, s=s, a=OCM[c][r][s]["median"], b=B["OCM"][c][r][s]["median"], a_best=OCM[c][r][s]["best"], b_best=B["OCM"][c][r][s]["best"]) for c in (2, 8) for r in range(5) for s in SHAPES]
B_SHAPE_PCT = {s: [100 * (d["b"] - d["a"]) / d["a"] for d in B_CELLS if d["s"] == s] for s in SHAPES}
B_SPARSE_L2 = [B["SPLIT"][(c, r, "sparse")]["l2"] for c in (2, 8) for r in range(5)]; B_SPARSE_L3 = [B["SPLIT"][(c, r, "sparse")]["l3"] for c in (2, 8) for r in range(5)]
A_SPARSE_L2 = [SPLIT[(c, r, "sparse")]["l2"] for c in (2, 8) for r in range(5)]
B_COCM_PCT = {s: [100 * (B["COCM"][r][s]["best"] - COCM[r][s]["best"]) / COCM[r][s]["best"] for r in range(5)] for s in SHAPES}
B_COCM_1XP = [B["COCM"][r]["sparse"]["best"] for r in range(5) if dist(2, NODE_OF_REGION[r]) == 1]; B_COCM_3XP = [B["COCM"][r]["sparse"]["best"] for r in range(5) if dist(2, NODE_OF_REGION[r]) == 3]
B_COCM_ORDERED = max(B_COCM_1XP) < min(B_COCM_3XP)
B_CLV_REPEAT = {d["size"]: d for d in B["CLV"] if d["kind"] == "repeat"}
B_CME_L1 = [d for d in B["CLV"] if d["kind"] == "repeat" and d["size"] <= 65536]; B_CME_PAST = [d for d in B["CLV"] if d["kind"] == "repeat" and d["size"] >= 98304]
B_RD_L1_MAX = max(d["emean"]["cme_l1d_refill_rd"] for d in B_CME_L1); B_RD_PAST_MIN = min(d["emean"]["cme_l1d_refill_rd"] for d in B_CME_PAST)
# verdicts on the pair of boots
HB1 = B_PF_MAX < 1e-4 and max(B_SPARSE_L2) < 1.02 and min(A_SPARSE_L2) > 1.02
HB3_NO_WALK = max(B["H3_WALK"]) == 0.0
HB5 = B["H5_SUPPORTED"] and B["FIT"]["route"]["rms"] < FIT["route"]["rms"]
HB7 = all(RP_BEST[("read-pf4", s)] > 2 * RP_BEST[("read", s)] for s in RP_SIZES)
FACTS["bootB"] = dict(
    run="membench-jibin-006 boot B (commit 7921962, 2026-11-04, prefetchers off)", chip_s=B["CHIP_S"], commands=len(B["CMDS"]), ctrl_4k=B["P4K"]["ns"], rt=B["RT_NS"],
    pf_max=B_PF_MAX, seq_ns=B["SEQ"]["ns"], flushed_ns=B["FLUSHED"]["ns"], l3_hit_max=L3_HIT_MAX, l3_acc_vs_refill=L3_ACC_VS_REFILL, pwrstat=[v for _, v in B_PWRSTAT],
    l3rows={s: dict(ns=L3_BEST[s]["ns"], l2hit=L3_BEST[s]["e"]["l2d_hit_rd"], l3acc=L3_BEST[s]["e"]["l3d_access_rd"], l3hit=L3_BEST[s]["e"]["l3d_hit_rd"], l3refill=L3_BEST[s]["e"]["l3d_refill_rd"]) for s in L3_SIZES},
    random_pct=(min(AB_LV_RANDOM_PCT), max(AB_LV_RANDOM_PCT)), shape_pct={s: (min(v), max(v)) for s, v in B_SHAPE_PCT.items()},
    walk_max=max(B["H3_WALK"]), fit=dict(bx=B["FIT"]["route"]["bx"], by=B["FIT"]["route"]["by"], rms=B["FIT"]["route"]["rms"]), write=[dict(size=w["size"], delta=w["delta"]) for w in B["W"]],
    read_variants={f"{k}@{s}": RP_BEST[(k, s)] for k, _ in RP_KERNELS for s in RP_SIZES}, read_run3=RP_RUN3,
    cme=dict(k4=B_CLV_REPEAT[4096]["ns"], k64=B_CLV_REPEAT[65536]["ns"], k96=B_CLV_REPEAT[98304]["ns"], rd_l1_max=B_RD_L1_MAX, rd_past_min=B_RD_PAST_MIN, seq_ns=B["CSEQ"]["ns"], flushed_ns=B["CFLUSHED"]["ns"],
             ocm_sparse_best=(min(B["COCM"][r]["sparse"]["best"] for r in range(5)), max(B["COCM"][r]["sparse"]["best"] for r in range(5))), ocm_all5_dense=B["CALL5"]["dense"]["best"], ocm_ordered=B_COCM_ORDERED),
)

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
        rows[i]["e"] = {k.replace("_per_line", ""): float(v) for k, v in f.items() if k.endswith("_per_line") and v != "-"}; i += 1   # the "best" rows carry "-" in the perf columns
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
RP_CYC = {x: {s: EX[x]["rp"][("read", s)]["e"]["cycles"] for s in RP_SIZES} for x in RP_BOOTS}   # cycles per line of the best rep
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

# ---------------------------------------------------------------- figures
def dotplot(rows, names, colors, w=900, unit="ns", xlim=None, rh=24, L=250):
    """rows: dict(label, vals=[v or None per series], title?)  one row of dots per label, one colour per series"""
    Rr, T, B = 60, 30, 44 + 16 * (legend_rows(list(zip(names, colors)), L, w) - 1); h = T + B + rh * len(rows)
    svg = SVG(w, h)
    vals = [v for r in rows for v in r["vals"] if v is not None]
    x0, x1 = xlim or (min(vals) * 0.95, max(vals) * 1.03)
    fx = lambda v: L + (v - x0) / (x1 - x0) * (w - L - Rr)
    for t in [x0 + i * (x1 - x0) / 5 for i in range(6)]:
        svg.line(fx(t), T - 6, fx(t), h - B, C["grid"]); svg.text(fx(t), T - 10, f"{t:.1f}", 10, "middle", C["muted"])
    svg.text(w - Rr + 24, T - 10, unit, 10, "start", C["ink2"])
    for i, r in enumerate(rows):
        y = T + rh * i + rh / 2
        svg.text(L - 10, y + 4, r["label"], 12, "end")
        present = [v for v in r["vals"] if v is not None]
        if len(present) > 1: svg.line(fx(min(present)), y, fx(max(present)), y, C["axis"], 1)
        for v, name, col in zip(r["vals"], names, colors):
            if v is not None: svg.circle(fx(v), y, 4.5, col, f"{name}, {r['label']}: {v:.3f} {unit}")
    legend(svg, L, h - 10 - 16 * (legend_rows(list(zip(names, colors)), L, w) - 1), list(zip(names, colors)), w)
    return svg.out()

def stacked_h(rows, w=900, unit="per load", xlim=None, rh=26, L=300, marker_name=None):
    """rows: dict(label, parts=[(value, color, name)], marker=(value, color, name) or None): one horizontal stacked bar per row"""
    names = []
    for r in rows:
        for v, col, name in r["parts"]:
            if (name, col) not in names: names.append((name, col))
    if marker_name: names.append(marker_name)
    Rr, T, B = 70, 26, 36 + 16 * (legend_rows(names, L, w) - 1); h = T + B + rh * len(rows)
    svg = SVG(w, h); x1 = xlim or max(sum(v for v, *_ in r["parts"]) for r in rows) * 1.08
    fx = lambda v: L + v / x1 * (w - L - Rr)
    for t in [i * x1 / 5 for i in range(6)]:
        svg.line(fx(t), T - 6, fx(t), h - B, C["grid"]); svg.text(fx(t), T - 10, f"{t:.1f}", 10, "middle", C["muted"])
    svg.text(w - Rr + 24, T - 10, unit, 10, "start", C["ink2"])
    for i, r in enumerate(rows):
        y = T + rh * i + 3; x = 0
        svg.text(L - 10, y + 14, r["label"], 12, "end")
        for v, col, name in r["parts"]:
            if v > 0: svg.rect(fx(x) + (1 if x else 0), y, max(0, fx(x + v) - fx(x) - (1 if x else 0)), rh - 8, col, f"{name}, {r['label']}: {v:.2f} {unit}", rx=2); x += v
        svg.text(fx(x) + 6, y + 13, f"{x:.2f}", 11, "start", C["ink2"])
        if r.get("marker"):
            v, col, name = r["marker"]; svg.line(fx(v), y - 2, fx(v), y + rh - 6, col, 2.5); svg.add(f'<title>{esc(name)}</title>')
    legend(svg, L, h - 10 - 16 * (legend_rows(names, L, w) - 1), names, w)
    return svg.out()

CELLS = [(c, r) for c in (2, 4, 6, 8) for r in sorted(range(5), key=lambda r: (dist(c, NODE_OF_REGION[r]), r))]
def cell_label(c, r): return f"CPU {c} to OCM{r} ({dist(c, NODE_OF_REGION[r])} xp)"
f_dense = dotplot([dict(label=cell_label(c, r), vals=[R2_DENSE[(c, r)], OCM[c][r]["dense"]["best"] if c in OCM else None, ROUTE[(c, r)]["best"]]) for c, r in CELLS],
                  ["run 2 dense", "boot A dense (G2, CPUs 2 and 8)", "boot A dense under the crosspoint counters (G6)"], [C["muted"], C["s1"], C["s3"]])
f_sparse = dotplot([dict(label=cell_label(c, r), vals=[R3_SPARSE[(c, r)], OCM[c][r]["sparse"]["best"], OCM[c][r]["vary"]["best"]]) for c, r in CELLS if c in OCM],
                   ["run 3 sparse", "boot A sparse", "boot A vary"], [C["muted"], C["s1"], C["s2"]])
f_sparse_med = dotplot([dict(label=cell_label(c, r), vals=[OCM[c][r]["dense"]["median"], OCM[c][r]["sparse"]["median"], OCM[c][r]["vary"]["median"]]) for c, r in CELLS if c in OCM],
                       ["boot A dense, median of 2 passes", "boot A sparse, median of 7", "boot A vary, median of 7"], [C["s3"], C["s1"], C["s2"]])
_split_rows = []
for c in (2, 8):
    for s in SHAPES:
        v = {k: statistics.mean(shape_stat(c, s, k)) for k in ("pf", "rest", "l3")}
        _split_rows.append(dict(label=f"CPU {c}, {s} (mean of 5 regions)", parts=[(v["rest"], C["s1"], "L2 refills not counted by 0x81BD"), (v["pf"], C["s2"], "L2 refills by hardware prefetchers (0x81BD)")],
                                marker=(v["l3"], C["ink"], f"L3 read refills {v['l3']:.2f}")))
    for s in ("dense", "sparse"):
        v = SPLIT_ALL5[(c, s)]
        _split_rows.append(dict(label=f"CPU {c}, all five {s}", parts=[(v["rest"], C["s1"], "L2 refills not counted by 0x81BD"), (v["pf"], C["s2"], "L2 refills by hardware prefetchers (0x81BD)")],
                                marker=(v["l3"], C["ink"], f"L3 read refills {v['l3']:.2f}")))
f_split = stacked_h(_split_rows, marker_name=("L3 read refills per load (0xA2), black mark", C["ink"]))
DENSE_ALIGNED = [(r, TLB[r]["dense"]["align"][0], TLB[r]["dense"]["emean"]["l1d_tlb_refill"]) for r in range(5) if TLB[r]["dense"]["align"][0] > 4]
DENSE_PLAIN = [TLB[r]["dense"]["emean"]["l1d_tlb_refill"] for r in range(5) if TLB[r]["dense"]["align"][0] == 4]
f_levels = line_chart([dict(name="run 3", color=C["muted"], pts=[(d["size"], d["ns3"], f"run 3 {kib(d['size'])} {d['kind']}: {d['ns3']:.3f} ns") for d in LV if d["kind"] in ("repeat", "fresh")], short="run 3", dy=14),
                       dict(name="boot A (run 4)", color=C["s1"], pts=[(d["size"], d["ns"], f"boot A {kib(d['size'])} {d['kind']}: {d['ns']:.3f} ns") for d in LV if d["kind"] in ("repeat", "fresh")], short="boot A")],
                      marks=[(49152, "48 KiB: past L1"), (196608, "192 KiB: past L2"), (4194304, "4 MiB: past the SLC")])
_pf = [d for d in LV if d["kind"] in ("repeat", "fresh") and d["size"] >= 65536]
f_fills = line_chart([dict(name="L2 refills (0x17)", color=C["s1"], pts=[(d["size"], d["emean"]["l2d_refill"], f"{kib(d['size'])}: {d['emean']['l2d_refill']:.3f} L2 refills per load") for d in _pf], short="L2 refills", dy=16),
                      dict(name="L2 refills by hardware prefetchers (0x81BD)", color=C["s2"], pts=[(d["size"], d["emean"]["l2d_refill_hwprf"], f"{kib(d['size'])}: {d['emean']['l2d_refill_hwprf']:.3f} prefetch refills per load") for d in _pf], short="by prefetchers", dy=14),
                      dict(name="L3 read refills (0xA2)", color=C["s3"], pts=[(d["size"], d["emean"]["l3d_refill_rd"], f"{kib(d['size'])}: {d['emean']['l3d_refill_rd']:.3f} L3 read refills per load") for d in _pf], short="L3 read refills", dy=-10, dash="5 4")],
                     ylabel="refills per load", ylim=(0, 1.25), marks=[(196608, "192 KiB"), (262144, "256 KiB")])
f_seq = bars_h([dict(label=f"core, random chain, every line flushed, 8 MiB", v=FLUSHED["ns"], color=C["s1"]), dict(label="core, sequential chain, every line flushed, 8 MiB", v=SEQ["ns"], color=C["s1"]),
                dict(label="CME, random chain, every line flushed, 8 MiB", v=CFLUSHED["ns"], color=C["s2"]), dict(label="CME, sequential chain, every line flushed, 8 MiB", v=CSEQ["ns"], color=C["s2"])], unit="ns per load")
f_tlb = dotplot([dict(label=f"OCM{r}, {s}" + (f" ({TLB[r][s]['align'][0]} KiB aligned)" if TLB[r][s]["align"][0] > 4 else ""), vals=[TLB[r][s]["emean"]["l1d_tlb_refill"], TLB[r][s]["emean"]["dtlb_walk"], TLB[r][s]["emean"]["l2d_tlb_refill"]])
                 for r in range(5) for s in SHAPES], ["L1 data TLB refills (0x05)", "translation table walks (0x34)", "L2 data TLB refills (0x2D)"], [C["s1"], C["s2"], C["s3"]], unit="per load", xlim=(0, 1.3))
f_cme_lat = line_chart([dict(name="run 3", color=C["muted"], pts=[(d["size"], d["ns3"], f"run 3 {kib(d['size'])} {d['kind']}: {d['ns3']:.3f} ns") for d in CLV if d["kind"] in ("repeat", "fresh")], short="run 3", dy=14),
                        dict(name="boot A (run 4)", color=C["s2"], pts=[(d["size"], d["ns"], f"boot A {kib(d['size'])} {d['kind']}: {d['ns']:.3f} ns") for d in CLV if d["kind"] in ("repeat", "fresh")], short="boot A")],
                       marks=[(65536, "64 KiB: the CME L1"), (393216, "384 KiB: last repeated row"), (524288, "512 KiB: first fresh chain")])
_cp = [d for d in CLV if d["kind"] in ("repeat", "fresh")]
f_cme_pf = line_chart([dict(name="hardware prefetch refills (0x32B2)", color=C["s2"], pts=[(d["size"], d["emean"]["cme_l1d_refill_hwprf"], f"{kib(d['size'])} {d['kind']}: {d['emean']['cme_l1d_refill_hwprf']:.2f} prefetch refills per load") for d in _cp], short="prefetch", dy=16),
                       dict(name="demand read refills (0x3280)", color=C["s1"], pts=[(d["size"], d["emean"]["cme_l1d_refill_rd"], f"{kib(d['size'])} {d['kind']}: {d['emean']['cme_l1d_refill_rd']:.3f} read refills per load") for d in _cp], short="demand read", dy=16),
                       dict(name="refills from outside the cluster (0x327E)", color=C["s3"], pts=[(d["size"], d["emean"]["cme_l1d_refill_outer"], f"{kib(d['size'])} {d['kind']}: {d['emean']['cme_l1d_refill_outer']:.2f} outer refills per load") for d in _cp], short="outer", dash="5 4", dy=-8)],
                      ylabel="CME L1 refills per load", marks=[(65536, "64 KiB: the CME L1"), (524288, "512 KiB: first fresh chain")])
f_cme_ocm = dotplot([dict(label=f"CPU 2 to OCM{r} through the CME ({dist(2, NODE_OF_REGION[r])} xp)", vals=[R3_COCM[r], COCM[r]["sparse"]["best"], COCM[r]["dense"]["best"], COCM[r]["vary"]["best"]]) for r in range(5)]
                    + [dict(label="all five, through the CME", vals=[g.CALL5S["best"], CALL5["sparse"]["best"], CALL5["dense"]["best"], None])],
                    ["run 3 sparse", "boot A sparse", "boot A dense", "boot A vary"], [C["muted"], C["s2"], C["s3"], C["s7"]], L=300)
_cme_split = [dict(label=f"{s}, mean of 5 regions", parts=[(statistics.mean(COCM[r][s]["emean"]["cme_l1d_refill_rd"] for r in range(5)), C["s1"], "demand read refills (0x3280)"), (statistics.mean(COCM[r][s]["emean"]["cme_l1d_refill_hwprf"] for r in range(5)), C["s2"], "hardware prefetch refills (0x32B2)")]) for s in SHAPES]
_cme_split += [dict(label=f"all five, {s}", parts=[(CALL5[s]["emean"]["cme_l1d_refill_rd"], C["s1"], "demand read refills (0x3280)"), (CALL5[s]["emean"]["cme_l1d_refill_hwprf"], C["s2"], "hardware prefetch refills (0x32B2)")]) for s in ("dense", "sparse")]
f_cme_split = stacked_h(_cme_split, L=240)

# boot B figures
f_b_cme = line_chart([dict(name="boot A, CME prefetcher on", color=C["muted"], pts=[(s, a, f"boot A {kib(s)} {k}: {a:.3f} ns") for s, k, a, b in AB_CLV if k in ("repeat", "fresh")], short="boot A", dy=14),
                      dict(name="boot B, CME prefetcher off", color=C["s2"], pts=[(s, b, f"boot B {kib(s)} {k}: {b:.3f} ns") for s, k, a, b in AB_CLV if k in ("repeat", "fresh")], short="boot B")],
                     marks=[(65536, "64 KiB: the CME L1"), (4194304, "4 MiB: past the SLC")], hline=(RT_NS[0], "register control 21.0 ns"))
f_b_dense = dotplot([dict(label=cell_label(c, r), vals=[OCM[c][r]["dense"]["median"], B["OCM"][c][r]["dense"]["median"]]) for c in (2, 8) for r in range(5)],
                    ["boot A, median of passes", "boot B, median of passes"], [C["muted"], C["s2"]])
f_b_cocm = dotplot([dict(label=f"CPU 2 to OCM{r} through the CME ({dist(2, NODE_OF_REGION[r])} xp)", vals=[COCM[r]["sparse"]["best"], B["COCM"][r]["sparse"]["best"]]) for r in range(5)]
                   + [dict(label="all five, sparse", vals=[CALL5["sparse"]["best"], B["CALL5"]["sparse"]["best"]])],
                   ["boot A, best pass", "boot B, best pass"], [C["muted"], C["s2"]])

# boots C, D and E figures
BOOT_COL = dict(A=C["muted"], B=C["s2"], C=C["s3"], D=C["s4"], E=C["s1"])
BOOT_NAME = dict(A="boot A (prefetchers on, 4 KiB pages)", B="boot B (prefetchers off)", C="boot C (hint, prefetchers on)", D="boot D (hint, prefetchers off)", E="boot E (L3 on, prefetchers on)")
f_cd_tlb = dotplot([dict(label=f"OCM{r}, {s}", vals=[statistics.mean(TLB_PASS[x][(r, s)]) for x in "ABCD"]) for s in SHAPES for r in range(5)],
                   [BOOT_NAME[x] for x in "ABCD"], [BOOT_COL[x] for x in "ABCD"], unit="per pass", xlim=(0, 620))
f_cd_gap = dotplot([dict(label=f"OCM{r} ({dist(2, NODE_OF_REGION[r])} xp)", vals=[GAP[x][r] for x in "ABCD"]) for r in range(5)],
                   [BOOT_NAME[x] for x in "ABCD"], [BOOT_COL[x] for x in "ABCD"], unit="ns", xlim=(0, 5.5))
_hit_rows = []
for s in (196608, 262144, 393216, 524288):
    for x in "CE":
        e = EX[x]["l3"]["best"][s]["e"]
        _hit_rows.append(dict(label=f"boot {x}, {kib(s)} ({EX[x]['l3']['best'][s]['ns']:.1f} ns)", parts=[(e["l2d_hit_rd"], C["s1"], "L2 read hits (0x81C5)"), (e["l3d_hit_rd"], C["s3"], "L3 read hits (0x81C6)"), (e["l3d_refill_rd"], C["s2"], "L3 read refills from outside the cluster (0xA2)")]))
f_e_hits = stacked_h(_hit_rows, L=260, xlim=1.15)
f_e_levels = line_chart([dict(name="boot C: L3 in snoop-filter-only mode (prefetchers on)", color=C["s3"], pts=[(s, c, f"boot C {kib(s)} {k}: {c:.3f} ns") for s, k, c, e in EC_LV if k in ("repeat", "fresh")], short="boot C", dy=14),
                         dict(name="boot E: L3 on (prefetchers on)", color=C["s1"], pts=[(s, e, f"boot E {kib(s)} {k}: {e:.3f} ns") for s, k, c, e in EC_LV if k in ("repeat", "fresh")], short="boot E", dy=-8)],
                        marks=[(131072, "128 KiB: the L2"), (262144, "256 KiB: the L3"), (4194304, "4 MiB: past the SLC")])
f_e_read = dotplot([dict(label=f"{name}, {kib(s)}", vals=[EX[x]["rp"][(k, s)]["agg"] for x in RP_BOOTS]) for s in RP_SIZES for k, name in RP_KERNELS],
                   [BOOT_NAME[x] for x in RP_BOOTS], [BOOT_COL[x] for x in RP_BOOTS], unit="GB/s", xlim=(0, 27))
G8_FORM = {"per-pass": "looped", "asm": "single-call"}   # the two forms' names on the pages (the data keys stay)
_g8_names = [f"boot {x}, {G8_FORM[f]}" for x in G8 for f in ("per-pass", "asm")]; _g8_cols = [C["s3"], C["s7"], C["s1"], C["s2"]]
f_g8 = dotplot([dict(label=f"{kernel}, {kib(s)}", vals=[G8[x][(f, kernel)]["rows"][s]["agg"] for x in G8 for f in ("per-pass", "asm")]) for kernel in ("read", "write") for s in G8_SIZES],
               _g8_names, _g8_cols[:len(_g8_names)], unit="GB/s", xlim=(20, 66))
f_e_cme = line_chart([dict(name="boot C: L3 in snoop-filter-only mode", color=C["s3"], pts=[(d["size"], c["ns"], f"boot C {kib(d['size'])}: {c['ns']:.3f} ns") for d in BT["E"]["CLV"] for c in BT["C"]["CLV"] if c["size"] == d["size"] and c["kind"] == d["kind"] and d["kind"] in ("repeat", "fresh")], short="boot C", dy=14),
                      dict(name="boot E: L3 on", color=C["s1"], pts=[(d["size"], d["ns"], f"boot E {kib(d['size'])}: {d['ns']:.3f} ns") for d in BT["E"]["CLV"] if d["kind"] in ("repeat", "fresh")], short="boot E", dy=-8)],
                     marks=[(65536, "64 KiB: the CME L1"), (262144, "256 KiB: the L3"), (4194304, "4 MiB: past the SLC")], hline=(RT_NS[0], "register control 21.0 ns"))
_cme_io = []
for s in (8192, 16384, 32768, 65536, 131072):
    for x in "CE":
        d = next(d for d in BT[x]["CLV"] if d["kind"] == "repeat" and d["size"] == s)
        _cme_io.append(dict(label=f"boot {x}, {kib(s)} ({d['ns']:.1f} ns)", parts=[(d["emean"]["cme_l1d_refill_inner"], C["s3"], "refills from inside the cluster (0x327D)"), (d["emean"]["cme_l1d_refill_outer"], C["s2"], "refills from outside the cluster (0x327E)")]))
f_e_cme_io = stacked_h(_cme_io, L=240)
f_e_cocm = dotplot([dict(label=f"CPU 2 to OCM{r} through the CME ({dist(2, NODE_OF_REGION[r])} xp)", vals=[BT[x]["COCM"][r]["sparse"]["best"] for x in BOOT_ORDER]) for r in range(5)]
                   + [dict(label="all five, sparse", vals=[BT[x]["CALL5"]["sparse"]["best"] for x in BOOT_ORDER])],
                   [BOOT_NAME[x] for x in BOOT_ORDER], [BOOT_COL[x] for x in BOOT_ORDER], L=300)
E_COCM_OUTER = {s: [BT["E"]["COCM"][r][s]["emean"]["cme_l1d_refill_outer"] for r in range(5)] for s in SHAPES}
C_COCM_OUTER = {s: [BT["C"]["COCM"][r][s]["emean"]["cme_l1d_refill_outer"] for r in range(5)] for s in SHAPES}
COCM_RATIO = {(a, b): {s: [BT[a]["COCM"][r][s]["best"] / BT[b]["COCM"][r][s]["best"] for r in range(5)] for s in SHAPES} for a, b in (("D", "B"), ("C", "A"), ("E", "A"), ("E", "C"))}

# ---------------------------------------------------------------- page text helpers
def hyp(s): return f'<span class="hyp">hypothesis</span>{s}'
def ok(s): return f'<span class="ok">supported</span>{s}'
def no(s): return f'<span class="hyp">not supported</span>{s}'
def gap(s): return f'<span class="gap">Insufficient data</span>{s}'
def mono(s): return f"<code>{esc(s)}</code>"
def rng(a, b, nd=2): return f"{a:.{nd}f} to {b:.{nd}f}"

WORDS_RUN4 = [
    ("boot A to E", "The five boots of run 4 (round four). A is the run 3 platform (sections 1 to 10); B has the data prefetchers of CPUs 2 to 9 and their CMEs turned off (section 11); C maps the OCM in 64 KiB contiguous translations with the prefetchers on, and D with them off (section 13); E is boot C's program and platform with the OCM back in 4 KiB pages and a rebuilt SCP that turns the L3 on (sections 14 and 15). The CME page gives the CME side (its sections 8 and 9)."),
    ("contiguous hint", "The contiguous bit of a translation entry, which marks 16 neighbouring 4 KiB entries as one 64 KiB block; the TLB then holds the block as one entry (two 32 KiB entries in the core's L1 data TLB). Boots C and D load /dev/ocm with cont=1 and every mapping line reads cont=64/64 [dmesg.txt of 007 and 008; Jesse's boot C README, OCM mappings]."),
    ("walk events", "0x34 translation table walks (data side), 0x8188 walks that ended in a block entry and 0x818A walks that ended in a page entry [C1-Nano TRM, event list], run on the TLB-set chains of boots C, D and E (the -walk-cpu2.csv files)."),
    ("L3 full mode (operating mode 7)", "The DSU cluster operating mode with all L3 slices and the whole L3 RAM open to lookup and allocation; IMP_CLUSTERPWRSTAT_EL1 reads 0x70 in it. Boot E's SCP (0.48.0-nopcie-l3.1) stages it for the clusters of CPUs 2 to 9; the stock SCP stages it for cluster 0 only."),
    ("G8 rows, looped and single-call forms", "Run 5c's one-core L1 rows on boots C and E: a read and a write of 4, 8, 16 and 24 KiB over many passes, timed in two forms: the looped form, one call of the kernel per pass (bandwidth-l1-passes.csv), and the single-call form, all passes of a rep inside one assembly call (bandwidth-l1-asmpasses.csv, header asm_passes=1). Read with l1_reader.py."),
    ("geometric mean", "The n-th root of the product of n ratios: the average ratio when rows are compared as ratios, so one row at half the time and one at twice the time average to 1."),
    ("prefetch-refill events", "Three core PMU events added in run 4 beside run 3's three refill events: 0x81BC (L1 data cache refills a hardware prefetcher requested), 0x81BD (L2 refills for accesses generated by hardware prefetchers targeting the L2) and 0x0111 (L2 refills for accesses from the L1 data prefetcher) [C1-Nano TRM, event list]. Each is reported per load of the timed pass, beside 0x03 (L1 refills), 0x17 (L2 refills) and 0xA2 (L3 read refills)."),
    ("TLB events", "0x05 L1 data TLB refills (counts refills that hardware prefetches caused too), 0x2D L2 data TLB refills (excludes hardware prefetches) and 0x34 translation table walks (walks caused by a miss in the L2 TLB driven by a memory access) [C1-Nano TRM, event list]. Run on the CPU 2 OCM rows with run 3's three refill events."),
    ("CME refill events", "0x3280 CME L1 refills caused by load instructions (demand reads), 0x32B2 refills by the CME's hardware prefetcher, 0x3281 refills caused by stores [C1-SME2 TRM, event list], beside run 3's 0x327D (refills from inside the cluster, inner) and 0x327E (from outside, outer)."),
    ("dense, sparse, vary", "Three chain shapes over one 256 KiB OCM region. Dense: every line of the region, 4,096 hops per pass (run 2's chain). Sparse: one line per 4 KiB page at one fixed line offset, 64 hops per pass (run 3's chain). Vary: one line per page at a line offset that changes from page to page, 64 hops per pass (new in run 4)."),
    ("sequential chain", "New in run 4: a chain whose members are the lines in address order, 8 MiB, every line flushed first. It is the stimulus a hardware prefetcher is built for, so it shows whether the prefetch events count at all."),
    ("route rows", "Phase G6: the dense chase of each of the 20 CPU-to-region cells run again under the mesh's crosspoint counters (mxp_<dir>_dat_txflit_valid, dir = e, w, n, s) on the crosspoint of the CPU's DSU and on the crosspoint of the region's home node. The events count transmitted data-channel flits over the whole command."),
    ("data flit", "One unit of the mesh's data channel. Read requests travel on a different channel (the request channel), which G6 does not count."),
    ("X-first", "A route that takes its horizontal (X) crosspoint steps before its vertical (Y) steps. Used here as the direction a route's first link would have if the mesh routed that way."),
    ("mapping alignment", "Each /dev/ocm mapping places a 256 KiB region at a user address the kernel chooses. The difference between the user and the physical address is a multiple of 16, 32 or 64 KiB on some mappings and of 4 KiB only on the others [dmesg.txt, membench_ocm lines]. A TLB entry that merges neighbouring 4 KiB pages needs the two addresses to share that alignment [Jesse's run 4 README, OCM mappings]."),
    ("snoop-filter-only mode (SFONLY)", "A DSU L3 state in which the L3 RAM holds no data and the L3 only keeps the snoop filter (the record of which lines the cores hold). The cluster power status register IMP_CLUSTERPWRSTAT_EL1 reads 0x0 in it. In this state every L2 miss goes to the mesh (SLC, OCM or DRAM)."),
    ("L2 and L3 hit events", "Run 5's hit set on the 64 KiB to 512 KiB chases: 0x81C5 L2 read hits, 0xA0 L3 read accesses and 0x81C6 L3 read hits per load, beside the three refill events [latency-dram-small-l3.csv]."),
    ("PRFM", "The AArch64 prefetch-memory instruction (PRFM PLDL1KEEP): a software hint that fetches a line into the L1 without using it. The read variants issue it 4, 8 or 16 lines ahead of the load."),
    ("H1 to H7", "The hypotheses of follow-up-run-plan.md section 5 and 10, each with the row that decides it. H1: the fills above one per hop are prefetches. H2: the sparse chain's fixed line offset is what a prefetcher reacts to. H3: a sparse pass takes one L1 TLB refill per hop. H4: the page size separates sparse from dense (boot C). H5: an X hop costs more than a Y hop. H6: the 7.7 to 8.0 ns per pass added to the small write rows in run 3 is the program. H7: the plain read loop keeps too few lines in flight (the run 5 rows, not in boot A)."),
]

PLATFORM_A = f"""<ul>
<li><b>Where and when.</b> One emulated Asimov hemisphere on the GA13 Palladium (image hemi_rtws_tlm, RTL 0d9e214, release a10280100), 2026-11-04 UTC, as one job: run_followup.sh at commit e8e4580. {CHIP_S:.3f} s of chip time against the 3.0 s estimate; {len(CMDS)} commands, all exit 0 ({FAILED} failed); 103 files back with matching checksums [Jesse's run 4 README, The run; SHA256SUMS checked here].</li>
<li><b>Platform.</b> Run 3's: the same image copy, SCP 0.48.0-nopcie.1 and TF-A 0.35.0, Linux 6.18.36, 256 huge pages of 2 MiB, CPUs 2 to 9 isolated, CPU 3 offline for the whole script. /dev/ocm maps the regions in 4 KiB pages as before and now logs each mapping [Jesse's run 4 README, Read first]. The PMU driver reports {PMU_COUNTERS} counters (20 event counters and the cycle counter), so no group of six events was multiplexed: every row reads perf_cov 1.0000 ({len(COV_ROWS)} counted rows) and no row carries a "# perf:" flag.</li>
<li><b>Controls (criterion G-e).</b> The 4 KiB repeated chase reads {P4K['ns']:.3f} ns ({P4K['cyc']:.2f} cycles) against run 3's {RUN3_LV[(4096, 'repeat')]:.3f}; the CME round trip reads {RT_NS[0]:.3f} to {RT_NS[1]:.3f} ns in its {len(RT)} reps against 21.00. Both are within 0.5 %, so the boot is run 3's as far as these two numbers can tell. The two uncounted 4 KiB controls read {CTRL[2]:.3f} ns (CPU 2) and {CTRL[8]:.3f} ns (CPU 8).</li>
<li><b>What this boot alone cannot answer.</b> Every comparison across boots (prefetchers off, 64 KiB translations, the L3 on) needs boots B to E, which sections 11 to 15 carry. Run 5's additions (the L2 and L3 hit set, the one-core read variants, the walk rows, the G8 rows) came after e8e4580 and are not in boot A's data.</li>
</ul>"""

# ======================================================================= page 1: the C1-Nano core
def core_page():
    # T1 the sweep with the prefetch columns
    t1 = table(["Footprint", "Chase", "Boot A ns", "Run 3 ns", "Boot A vs run 3", "L1 refills", "L1 refills by prefetch (0x81BC)", "L2 refills", "L2 refills by prefetch (0x81BD)", "L2 refills by the L1 prefetcher (0x0111)", "L3 read refills"],
               [[kib(d["size"]), d["kind"], fmt(d["ns"], 3), fmt(d["ns3"], 3), pct(d["ns"], d["ns3"]) if d["ns3"] else "-", fmt(d["e"]["l1d_refill"], 3), fmt(d["e"]["l1d_refill_hwprf"], 3), fmt(d["e"]["l2d_refill"], 3), fmt(d["e"]["l2d_refill_hwprf"], 3), fmt(d["e"]["l2d_refill_l1dhwprf"], 3), fmt(d["e"]["l3d_refill_rd"], 3)] for d in LV],
               "CPU 2, ns per load of the best pass with that pass's counters per load [latency-dram-small.csv, latency-dram-large.csv, latency-dram-flushed.csv, latency-dram-seq.csv]. The sequential row has no run 3 twin. Boot A vs run 3 is (boot A minus run 3) over run 3.")
    # T2 event validation
    ev_rows = []
    for code, key, what in EV_CORE:
        on_seq = SEQ["e"][key]; peak = max((d["emean"][key], d["file"]) for c in OCM for r in range(5) for d in [OCM[c][r][s] for s in SHAPES])
        status = "validated on the sequential row" if on_seq > 0.5 else f"validated on the OCM rows (up to {peak[0]:.2f} per load on {peak[1]}); reads {on_seq:.4f} on the sequential row"
        ev_rows.append([code, what, fmt(on_seq, 4), fmt(SEQ["e"]["l1d_refill"], 3) if key == "l1d_refill_hwprf" else fmt(SEQ["e"]["l2d_refill"], 3), status])
    for code, key, what in (("0x05", "l1d_tlb_refill", "L1 data TLB refills"), ("0x2D", "l2d_tlb_refill", "L2 data TLB refills"), ("0x34", "dtlb_walk", "translation table walks")):
        ev_rows.append([code, what, fmt(STIM_E[key], 4), "1.0 (one page per hop)", "validated on the 32 MiB chain on 4 KiB pages" if STIM_E[key] > 0.1 else "unvalidated"])
    t2 = table(["Event", "Counts", "Per load on its stimulus", "Reference column on that row", "Status"], ev_rows,
               f"Criterion G-a and G-c: an event is validated where the activity it counts is established. The sequential 8 MiB chain is the prefetch stimulus (every line flushed, members in address order); the 32 MiB random chain on 4 KiB pages (8,192 pages) is the TLB stimulus, {TLB_STIM_BEST:.1f} ns per load [latency-dram-seq.csv, latency-dram-tlb-cpu2.csv].")
    # T3 OCM by cell and shape, CPUs 2 and 8
    def cellrow(c, r):
        o = OCM[c][r]
        return [cell_label(c, r)] + [f"{fmt(o[s]['best'], 2)} <span class='d'>(med {fmt(o[s]['median'], 2)}, {o[s]['n']} passes)</span>" for s in SHAPES] + [fmt(R2_DENSE[(c, r)], 2), fmt(R3_SPARSE[(c, r)], 2), fmt(ROUTE[(c, r)]["best"], 2)]
    t3 = table(["Cell", "Dense", "Sparse", "Vary", "Run 2 dense", "Run 3 sparse", "Dense under counters (G6)"], [cellrow(c, r) for c in (2, 8) for r in sorted(range(5), key=lambda r: (dist(c, NODE_OF_REGION[r]), r))]
               + [[f"CPU {c}, all five regions", fmt(ALL5[c]["dense"]["best"], 2), fmt(ALL5[c]["sparse"]["best"], 2), "-", fmt(g.ALL5_2[c]["best"], 2), fmt(g.ALL5S[c]["best"], 2), "-"] for c in (2, 8)],
               "ns per load, best pass, with the median and the number of timed passes. Dense: 4,096 hops, 2 timed passes; sparse and vary: 64 hops, 7 timed passes; all five: 20,480 or 320 hops. Run 2 and run 3 from their own files [latency-ocm-region*-{dense,vary,}-cpu*.csv, latency-ocm-all5*-cpu*.csv].")
    # T4 the refill split per shape
    t4 = table(["CPU, shape", "L1 refills", "L1 refills by prefetch", "L2 refills", "by hardware prefetchers (0x81BD)", "not counted by 0x81BD", "L3 read refills", "(not by 0x81BD) minus L3 read refills"],
               [[f"CPU {c}, {s}" + (f", OCM{r}" if r is not None else ", all five")] + [fmt(v[k], 3) for k in ("l1", "l1pf", "l2", "pf", "rest", "l3")] + [f"{v['rest'] - v['l3']:+.3f}"]
                for c in (2, 8) for s in SHAPES for r in range(5) for v in [SPLIT[(c, r, s)]]]
               + [[f"CPU {c}, {s}, all five"] + [fmt(v[k], 3) for k in ("l1", "l1pf", "l2", "pf", "rest", "l3")] + [f"{v['rest'] - v['l3']:+.3f}"] for c in (2, 8) for s in ("dense", "sparse") for v in [SPLIT_ALL5[(c, s)]]],
               "Per load, mean over the timed passes. 'Not counted by 0x81BD' is L2 refills minus 0x81BD, a labelled difference: 0x17 also counts instruction misses, translation walks and L1 write-backs [C1-Nano TRM, 0x0017], so it is not a demand count. 0x0111 (L2 refills from the L1 prefetcher) reads 0 on every OCM row and is not shown.")
    # T5 TLB rows
    t5 = table(["Row", "Mapping alignment", "L1 TLB refills (0x05)", "L2 TLB refills (0x2D)", "Walks (0x34)", "L2 refills", "L3 read refills", "ns best"],
               [[f"OCM{r}, {s}, CPU 2", f"{TLB[r][s]['align'][0]} KiB" if TLB[r][s]["align"][0] > 4 else "4 KiB (none)", fmt(TLB[r][s]["emean"]["l1d_tlb_refill"], 3), fmt(TLB[r][s]["emean"]["l2d_tlb_refill"], 3), fmt(TLB[r][s]["emean"]["dtlb_walk"], 3), fmt(TLB[r][s]["emean"]["l2d_refill"], 3), fmt(TLB[r][s]["emean"]["l3d_refill_rd"], 3), fmt(TLB[r][s]["best"], 2)]
                for s in SHAPES for r in range(5)]
               + [["32 MiB random chain, 4 KiB pages, DRAM (the stimulus)", "-", fmt(STIM_E["l1d_tlb_refill"], 3), fmt(STIM_E["l2d_tlb_refill"], 3), fmt(STIM_E["dtlb_walk"], 3), fmt(STIM_E["l2d_refill"], 3), fmt(STIM_E["l3d_refill_rd"], 3), fmt(TLB_STIM_BEST, 2)]],
               "Per load, mean over the timed passes, CPU 2 [latency-ocm-region*-{dense-,vary-,}tlb-cpu2.csv, latency-dram-tlb-cpu2.csv]. The mapping alignment is the user-to-physical offset of that command's /dev/ocm mapping, matched to the command by the order of the kernel-log lines (110 lines, one group per OCM command, each group's regions equal to the command's; checked by this script).")
    # T6 route table
    t6 = table(["Cell", "DSU crosspoint", "Outgoing data flits at the DSU's crosspoint (e / w / n / s)", "Most at", "X-first would be", "Node crosspoint", "Outgoing data flits at the node's crosspoint (e / w / n / s)", "Most at", "X-first would be", "ns best (G6)", "ns best (G2 dense)"],
               [[cell_label(c, r), f"{v['dsu']} ({v['dsu_xy'][0]},{v['dsu_xy'][1]})", " / ".join(f"{v['d_dsu'][d]:,}" for d in "ewns"), f"{v['dom_dsu']} ({100 * v['share_dsu']:.0f} %)", v["exp_dsu"],
                 f"{v['node']} ({v['node_xy'][0]},{v['node_xy'][1]})", " / ".join(f"{v['d_node'][d]:,}" for d in "ewns"), f"{v['dom_node']} ({100 * v['share_node']:.0f} %)", v["exp_node"], fmt(v["best"], 2), fmt(OCM[c][r]["dense"]["best"], 2) if c in OCM else "-"]
                for c, r in CELLS for v in [ROUTE[(c, r)]]],
               f"Data flits transmitted in each direction over the whole command (the chain build, the flush, 3 fresh passes and anything else on that crosspoint) [cmn-counts.csv, labels route-ocm*-cpu*]. 'Most at' is the direction with the most flits and its share of the four. 'X-first would be' is the first link of a route that takes its X steps before its Y steps, from the two crosspoints' coordinates. The helper's own cost around each command is {min(HELPER_COST) / 1e6:.2f} to {max(HELPER_COST) / 1e6:.2f} ms of chip time (helper minus child elapsed).")
    # T7 fit
    t7 = table(["Rows", "n", "Intercept a (ns)", "Per X step bx (ns)", "Per Y step by (ns)", "bx minus by (ns)", "Residual, rms (ns)"],
               [[name, f["n"], fmt(f["a"], 2), fmt(f["bx"], 2), fmt(f["by"], 2), f"{f['bx'] - f['by']:+.2f}", fmt(f["rms"], 2)]
                for name, f in (("boot A, G6 dense under counters, best of 2", FIT["route"]), ("boot A, G6, median of 2", FIT["route_med"]), ("boot A, G2 dense, CPUs 2 and 8, best", FIT["dense_g2"]), ("run 2 dense, best", FIT["run2"]), ("run 3 sparse, best", FIT["run3"]))],
               "Least squares of ns per load = a + bx |dx| + by |dy| over the cells, with |dx| and |dy| the coordinate differences between the DSU's and the node's crosspoints (the assumed hop counts, not a measured route). The residual is the root mean square of the cells' distances from the fit.")
    # T8 write cost
    t8 = table(["Footprint", "Run 3 program on boot A, GB/s", "Run 2 program on boot A, GB/s", "ns per pass, run 3 program", "ns per pass, run 2 program", "Difference on one boot (ns per pass)", "Run 3's own row, GB/s", "Run 2's own row, GB/s", "Difference across runs (ns per pass)"],
               [[kib(d["size"]), fmt(d["r3prog"], 3), fmt(d["r2prog"], 3), fmt(d["ns3"], 1), fmt(d["ns2"], 1), f"{d['delta']:+.1f}", fmt(d["run3"], 3), fmt(d["run2"], 3), f"{d['delta_orig']:+.1f}"] for d in W],
               "One core (CPU 2), the write kernel, best of 3 reps, run 3's pass counts (256, 128, 64, 32). ns per pass is bytes over GB/s with GB = 1e9 [bandwidth-write-small.csv (bandwidth, run 3's machine code per Jesse's README), bandwidth-write-small-r2prog.csv (bandwidth_r2, run 2's); run 3's and run 2's rows from bandwidth-dram-1core.csv of 004 and 002].")
    # boot B tables (section 11)
    tb1 = table(["Footprint", "Chase", "Boot A ns", "Boot B ns", "Boot B against A"], [[kib(s), k, fmt(a, 3), fmt(b, 3), pct(b, a)] for s, k, a, b in AB_LV],
                "CPU 2, best rep or best pass of each row on each boot [latency-dram-small.csv, -large.csv, -flushed.csv, -seq.csv of 005 and 006]. The sequential row is the prefetch stimulus; the others are random chases.")
    tb2 = table(["Footprint", "ns per load", "L1 refills", "L2 refills", "L2 read hits (0x81C5)", "L3 read accesses (0xA0)", "L3 read hits (0x81C6)", "L3 read refills (0xA2)"],
                [[kib(s), fmt(L3_BEST[s]["ns"], 3)] + [f"{L3_BEST[s]['e'][k]:.4f}" for k in ("l1d_refill", "l2d_refill", "l2d_hit_rd", "l3d_access_rd", "l3d_hit_rd", "l3d_refill_rd")] for s in L3_SIZES],
                f"CPU 2 with CPU 3 offline, the repeated chase, best of 3 reps with that rep's counters per load; the hits read 0.0000 in all {len(L3ROWS)} reps [latency-dram-small-l3.csv]. IMP_CLUSTERPWRSTAT_EL1 read {B_PWRSTAT[0][1]} before and {B_PWRSTAT[1][1]} after the command [log.txt].")
    tb3 = table(["Cell", "Dense A", "Dense B", "Sparse A", "Sparse B", "Vary A", "Vary B"],
                [[cell_label(c, r)] + [f"{fmt(OCM[c][r][s]['median'], 1)} <span class='d'>({fmt(OCM[c][r][s]['best'], 1)})</span>" if boot == "A" else f"{fmt(B['OCM'][c][r][s]['median'], 1)} <span class='d'>({fmt(B['OCM'][c][r][s]['best'], 1)})</span>" for s in SHAPES for boot in ("A", "B")] for c in (2, 8) for r in range(5)],
                "ns per hop: median of the passes, the best pass in brackets; dense 2 passes of 4,096 hops, sparse and vary 7 passes of 64 hops [latency-ocm-region&lt;r&gt;[-dense|-vary]-cpu&lt;c&gt;.csv of 005 and 006].")
    tb4 = table(["Read variant", "2 MiB, GB/s", "32 MiB, GB/s", "2 MiB against the plain loop", "32 MiB against the plain loop"],
                [[name, fmt(RP_BEST[(k, 2097152)], 2), fmt(RP_BEST[(k, 33554432)], 2), pct(RP_BEST[(k, 2097152)], RP_BEST[("read", 2097152)]), pct(RP_BEST[(k, 33554432)], RP_BEST[("read", 33554432)])] for k, name in RP_KERNELS]
                + [["run 3's plain loop, prefetchers on", fmt(RP_RUN3[2097152], 2), fmt(RP_RUN3[33554432], 2), pct(RP_RUN3[2097152], RP_BEST[("read", 2097152)]), pct(RP_RUN3[33554432], RP_BEST[("read", 33554432)])]],
                "One core (CPU 2), best of 3 reps, 4 passes at 2 MiB and 2 at 32 MiB, huge pages [bandwidth-read-prefetch.csv of 006; run 3's row from bandwidth-dram-1core.csv of 004]. GB = 1e9 bytes.")
    # T9 repeat rows
    t9 = table(["File", "Row", "Boot A ns", "Run 3 ns", "Boot A vs run 3"], [[d["file"], f"{kib(d['size'])} {d['mode'].replace('-best', '').replace('best', 'best')}", fmt(d["run4"], 3), fmt(d["run3"], 3), f"{d['pct']:+.2f} %"] for d in REPEAT_SORTED[:12]],
               f"The 12 rows that moved most among the {len(REPEAT_SAME)} best rows boot A and run 3 share by file name and footprint (core and CME; the round-trip controls set aside). {N_WITHIN[1]} are within 1 %, {N_WITHIN[3]} within 3 %, {N_WITHIN[5]} within 5 %.")
    # T10 alignment counts
    t10 = table(["Alignment of user to physical address", "Mappings (of 110)"], [[f"multiple of {a} KiB" if a > 4 else "4 KiB only (no larger alignment)", ALIGN_COUNT[a]] for a in (64, 32, 16, 4)],
                "From the 110 membench_ocm lines of dmesg.txt, matched to the 86 OCM commands of the log in order. Jesse's README counts 23 mappings aligned to 16 KiB or better (5 at 64 KiB, 8 at 32 KiB, 15 at 16 KiB in his breakdown; the 64 and 32 KiB ones are also 16 KiB multiples), which this count reproduces.")

    sparse_med_cpu2 = [OCM[2][r]["sparse"]["median"] for r in range(5)]; dense_med_cpu2 = [OCM[2][r]["dense"]["median"] for r in range(5)]
    t12 = table(["Row"] + [f"Boot {x}" for x in BOOT_ORDER], [[lab] + [d[x] for x in BOOT_ORDER] for lab, d in FIVE],
                "Each row is the same command on every boot that has it [log.txt, latency-dram-small.csv, latency-dram-small-l3.csv, latency-dram-large.csv, latency-dram-seq.csv, bandwidth-read-prefetch.csv of 005 to 010]. The power status is the box's two reads around the hit-set command.")
    t13a = table(["Chain (CPU 2, TLB set)", "Hops per pass"] + [f"Boot {x}" for x in BOOT_ORDER],
                 [[f"OCM{r}, {s}", f"{BT['A']['TLB'][r][s]['hops']:,}"] + [f"{TLB_PASS[x][(r, s)][0]:.0f} to {TLB_PASS[x][(r, s)][1]:.0f}" for x in BOOT_ORDER] for s in SHAPES for r in range(5)],
                 "L1 data TLB refills (0x05) per pass, lowest to highest pass of the row [latency-ocm-region&lt;r&gt;-&lt;shape&gt;-tlb-cpu2.csv of 005 to 010]. Boots C and D map the OCM in 64 KiB contiguous translations; A, B and E in 4 KiB pages.")
    t13b = table(["Pair", "What the pair compares", "Rows", "Faster on the first", "Ratio, lowest to highest", "Geometric mean"],
                 [[f"{a} against {b}", what, RATIOS[(a, b)]["n"], RATIOS[(a, b)]["faster"], f"{RATIOS[(a, b)]['lo']:.3f} to {RATIOS[(a, b)]['hi']:.3f}", f"{RATIOS[(a, b)]['gm']:.3f}"] for a, b, what in PAIRS],
                 "The 69 core OCM rows of each boot (30 shape cells on CPUs 2 and 8, 4 all-five rows, 15 TLB-set rows, 20 route rows), ratio of best passes; below 1 is faster on the first boot. The walk rows are not among them.")
    t13c = table(["Walk event, row"] + [f"Boot {x}" for x in "CDE"],
                 [["32 MiB stimulus: 0x34 walks per hop"] + [f"{WALK_STIM[x]['emean']['dtlb_walk']:.4f}" for x in "CDE"],
                  ["32 MiB stimulus: 0x818A page walks per hop"] + [f"{WALK_STIM[x]['emean']['dtlb_walk_page']:.4f}" for x in "CDE"],
                  ["32 MiB stimulus: 0x8188 block walks per hop"] + [f"{WALK_STIM[x]['emean']['dtlb_walk_block']:.4f}" for x in "CDE"],
                  ["32 MiB stimulus: ns per hop, best"] + [f"{WALK_STIM[x]['best']:.2f}" for x in "CDE"],
                  ["5 OCM sparse rows: 0x34 per hop, lowest to highest pass"] + [f"{WALK_OCM_34[x][0]:.4f} to {WALK_OCM_34[x][1]:.4f}" for x in "CDE"],
                  ["5 OCM sparse rows: passes with a walk, of 35"] + [f"{WALK_OCM_NONZERO[x]}" for x in "CDE"],
                  ["5 OCM sparse rows: 0x818A per hop, highest pass"] + [f"{WALK_OCM_PAGE_MAX[x]:.4f}" for x in "CDE"],
                  ["5 OCM sparse rows: 0x8188 per hop, highest pass"] + [f"{WALK_OCM_BLOCK_MAX[x]:.4f}" for x in "CDE"]],
                 "The walk rows: the TLB-set chains run again with 0x34, 0x8188 and 0x818A [latency-dram-walk-cpu2.csv, latency-ocm-region&lt;r&gt;-walk-cpu2.csv of 007, 008 and 010]. The stimulus is the random 32 MiB chain on 4 KiB DRAM pages (2 passes); each OCM row is the sparse chain of one region (7 passes of 64 hops).")
    t14a = table(["Footprint", "Boot C ns", "Boot E ns", "E / C", "E: L2 hits", "E: L3 hits", "E: outside refills", "C: L2 hits", "C: L3 hits", "C: outside refills"],
                 [[kib(s), fmt(C_L3["best"][s]["ns"], 3), fmt(E_L3["best"][s]["ns"], 3), f"{E_L3['best'][s]['ns'] / C_L3['best'][s]['ns']:.3f}",
                   fmt(E_L3["best"][s]["e"]["l2d_hit_rd"], 4), fmt(E_L3["best"][s]["e"]["l3d_hit_rd"], 4), fmt(E_L3["best"][s]["e"]["l3d_refill_rd"], 4),
                   fmt(C_L3["best"][s]["e"]["l2d_hit_rd"], 4), fmt(C_L3["best"][s]["e"]["l3d_hit_rd"], 4), fmt(C_L3["best"][s]["e"]["l3d_refill_rd"], 4)] for s in L3_SIZES],
                 "The hit set, CPU 2 with CPU 3 offline, best of 3 reps, counts per load of that rep [latency-dram-small-l3.csv of 007 and 010]: 0x81C5 L2 read hits, 0x81C6 L3 read hits, 0xA2 L3 read refills (filled from outside the cluster).")
    t14b = table(["Footprint", "Chase", "Boot C ns", "Boot E ns", "E / C"], [[kib(s), k, fmt(c, 3), fmt(e, 3), f"{e / c:.3f}"] for s, k, c, e in EC_LV],
                 "CPU 2, best rep or best pass [latency-dram-small.csv, -large.csv, -flushed.csv, -seq.csv of 007 and 010].")
    t14c = table(["Read variant", "Footprint"] + [f"Boot {x}, GB/s" for x in RP_BOOTS] + ["E / C"],
                 [[name, kib(s)] + [fmt(EX[x]["rp"][(k, s)]["agg"], 3) for x in RP_BOOTS] + [f"{EX['E']['rp'][(k, s)]['agg'] / EX['C']['rp'][(k, s)]['agg']:.3f}"] for s in RP_SIZES for k, name in RP_KERNELS],
                 "One thread on CPU 2, best of 3 reps, GB = 1e9 bytes [bandwidth-read-prefetch.csv of 006 to 010]. Prefetchers off on B and D, on with the L3 in snoop-filter-only mode on C, on with the L3 on on E.")
    t15 = table(["Boot, form, kernel"] + [f"{kib(s)}, GB/s" for s in G8_SIZES] + ["Fixed cost per pass, ns", "Rate, GB/s", "Largest residual", "Rule (under 2 %)"],
                [[f"{x}, {G8_FORM[f]}, {k}"] + [fmt(v["rows"][s]["agg"], 3) for s in G8_SIZES] + [fmt(v["a_ns"], 1), fmt(v["rate"], 1), f"{v['resid_pct']:.1f} %", "met" if v["ok"] else "not met"] for x in G8 for (f, k), v in G8[x].items()],
                "Best of 5 reps per size; the fit t_pass = a + bytes / rate through the four best reps [bandwidth-l1-passes.csv, bandwidth-l1-asmpasses.csv of 007 and 010; l1_reader.py]. looped = one call of the kernel per pass; single-call = all passes of a rep inside one assembly call.")
    t15b = table(["Boot, form (read)"] + [f"{kib(s)}: ns per pass above 64 GB/s" for s in G8_SIZES] + ["8 to 16 KiB: added bytes, GB/s"],
                 [[f"{x}, {G8_FORM[f]}"] + [fmt(G8[x][(f, 'read')]["rows"][s]["above_ideal"], 1) for s in G8_SIZES] + [fmt(G8_MARGINAL[(x, f)], 1)] for x in G8 for f in ("per-pass", "asm")],
                 "The read rows without a fit: each best rep's pass time minus bytes / 64 GB/s (the dual 128-bit read path at 2 GHz), and the rate of the bytes added between the 8 and 16 KiB rows.")
    body = f"""
<div class="short"><p><b>Short version.</b> Boot A repeats run 3 and its counters show that the fills above one per hop on the sparse OCM chains are hardware prefetches, which boot B confirms with the prefetchers off while its hit counters show that the DSU L3 of CPUs 2 to 9 held no data on runs 1 to 4 (sections 4 to 11). Boots C and D map the OCM in 64 KiB translations: the L1 TLB refills fall from {TLB_PASS_RNG['A'][0]:.0f} to {TLB_PASS_RNG['B'][1]:.0f} per pass to {TLB_PASS_RNG['C'][0]:.0f} to {max(TLB_PASS_RNG['C'][1], TLB_PASS_RNG['D'][1]):.0f}, and the OCM rows gain {100 * (1 - RATIOS[('D', 'B')]['gm']):.1f} % by geometric mean with the prefetchers off (section 13). Boot E turns the L3 on through a rebuilt SCP: the 192 to 384 KiB chases fall to {E_L3['best'][196608]['ns']:.1f} to {E_L3['best'][393216]['ns']:.1f} ns (an L3 hit costs about {statistics.mean(L3_HIT_EST.values()):.1f} ns est.), the plain one-core read of 32 MiB rises from {EX['C']['rp'][('read', 33554432)]['agg']:.1f} to {EX['E']['rp'][('read', 33554432)]['agg']:.1f} GB/s, and the dense all-five OCM row stays at {ALL5_DENSE_BEST['E']:.1f} ns (sections 14 and 15).</p></div>

<h2 id="words">1. Words used here</h2>
{words(g.WORDS_COMMON[:8] + WORDS_RUN4 + g.WORDS_COMMON[9:])}

<h2 id="run">2. The run and the platform</h2>
{PLATFORM_A}

<h2 id="tables">3. Summary tables</h2>
<h3 id="t31">3.1 Do the new events count? (criteria G-a, G-c)</h3>{t2}
<ul>
<li><b>The prefetch events count.</b> On the sequential chain every L1 refill was requested by a hardware prefetcher (0x81BC {SEQ['e']['l1d_refill_hwprf']:.4f} per load beside {SEQ['e']['l1d_refill']:.4f} L1 refills) and every L2 refill came from the L1 prefetcher's requests (0x0111 {SEQ['e']['l2d_refill_l1dhwprf']:.4f} beside {SEQ['e']['l2d_refill']:.4f} L2 refills). 0x81BD (prefetchers targeting the L2) reads {SEQ['e']['l2d_refill_hwprf']:.4f} there and up to {max(shape_stat(2, 'vary', 'pf') + shape_stat(8, 'vary', 'pf')):.2f} per load on the OCM rows, so it counts; the sequential chain is served by the L1 prefetcher, not by one targeting the L2.</li>
<li><b>The TLB events count.</b> On the 32 MiB chain on 4 KiB pages: {STIM_E['l1d_tlb_refill']:.3f} L1 TLB refills, {STIM_E['l2d_tlb_refill']:.3f} L2 TLB refills and {STIM_E['dtlb_walk']:.3f} walks per load, at {TLB_STIM_BEST:.1f} ns per load against {[d for d in LV if d['size'] == 33554432][0]['ns']:.1f} ns for the same footprint on 2 MiB huge pages. {hyp(f" The L2 TLB refill and the walk count agree to the fourth digit on that row, so on this chain every L2 TLB miss walked and every walk refilled the L2 TLB; the {100 - 100 * STIM_E['l2d_tlb_refill']:.0f} % of loads with an L1 TLB refill but no L2 TLB refill hit in the L2 TLB.")}</li>
<li><b>The L3 read refill event does not count prefetch fills.</b> On the sequential chain the L2 refills are {SEQ['e']['l2d_refill']:.4f} per load but the L3 read refills {SEQ['e']['l3d_refill_rd']:.4f}, although every line came from outside the DSU (it was flushed). {hyp(" Either the L1 prefetcher's fills do not allocate in the L3, or 0xA2 counts demand reads only; the TRM text ('level 3 accesses that receive data from outside the L3 cache due to a memory-read operation') does not say which. On the random chains 0xA2 therefore counts the loads that missed the L3, not every line that entered the DSU.")}</li>
</ul>
<h3 id="t32">3.2 Latency by footprint, CPU 2, with the prefetch columns</h3>{t1}
<h3 id="t33">3.3 OCM latency by cell and chain shape</h3>{t3}
<h3 id="t34">3.4 L2 refills by cause on the OCM rows (H1)</h3>{t4}
<h3 id="t35">3.5 Translation activity by chain shape (H3)</h3>{t5}{t10}
<h3 id="t36">3.6 The route rows: outgoing data directions at both ends (G-g, H5)</h3>{t6}
<h3 id="t37">3.7 Latency against the assumed hop counts</h3>{t7}
<h3 id="t38">3.8 The write-cost check (H6)</h3>{t8}
<h3 id="t39">3.9 Boot A against run 3 on the rows both ran</h3>{t9}

<h2 id="f-levels">4. Latency by footprint, CPU 2</h2>
{fig(f_levels, f"Boot A lies on run 3 at every footprint: the largest change among the {len(REPEAT_SAME)} shared rows is {REPEAT_SORTED[0]['pct']:+.2f} % ({REPEAT_SORTED[0]['file']}, {kib(REPEAT_SORTED[0]['size'])}).", "Steps at 48 KiB (past L1), 192 KiB (past L2) and 4 to 16 MiB (past the SLC) [table 3.2]. Hover a dot for the value.")}
{fig(f_fills, f"At 192 and 256 KiB, {100 * [d for d in LV if d['size'] == 196608][0]['emean']['l2d_refill_hwprf'] / [d for d in LV if d['size'] == 196608][0]['emean']['l2d_refill']:.0f} % and {100 * [d for d in LV if d['size'] == 262144][0]['emean']['l2d_refill_hwprf'] / [d for d in LV if d['size'] == 262144][0]['emean']['l2d_refill']:.0f} % of the L2 refills are prefetches (0x81BD); from 768 KiB on none are.", f"L2 refills, the share of them made by hardware prefetchers, and L3 read refills per load on the repeated and fresh rows from 64 KiB [table 3.2]. The 192 KiB row reads {[d for d in LV if d['size'] == 196608][0]['e']['l2d_refill']:.2f} L2 refills and {[d for d in LV if d['size'] == 196608][0]['e']['l3d_refill_rd']:.2f} L3 read refills per load: the rest of its loads hit the L2 or the L3, which run 5's hit set will count directly.")}

<h2 id="f-seq">5. The sequential chain against the random one</h2>
{fig(f_seq, f"The core's sequential chain runs at {SEQ['ns']:.1f} ns per load, {FLUSHED['ns'] / SEQ['ns']:.1f} times faster than the random chain of the same size with every line flushed; the CME's at {CSEQ['ns']:.1f} ns, its L1 hit time.", f"Both chains are 8 MiB and both are flushed from every cache before each pass. Core: every L1 refill on the sequential row was a prefetch (table 3.1), and {SEQ['ns']:.1f} ns is close to the L2 hit time of the 128 KiB row ({L2HIT_NS:.1f} ns). {hyp(' The L1 prefetcher runs ahead by about one L2 hit, not far enough to make the load an L1 hit; a longer chain or a wider stride would say how far it runs.')} CME: see the CME page.")}

<h2 id="f-ocm">6. OCM latency by cell: three chain shapes, three runs</h2>
{fig(f_dense, f"The dense chains of boot A sit {min(ROUTE_VS_RUN2):+.2f} to {max(ROUTE_VS_RUN2):+.2f} ns from run 2's at the 20 cells; the counted and uncounted dense rows of the same cell differ by {min(x[2] for x in ROUTE_VS_DENSE):+.2f} to {max(x[2] for x in ROUTE_VS_DENSE):+.2f} ns.", "Best pass per cell, ns per load. The G6 rows are the same command as the G2 dense rows, run under the crosspoint counters [tables 3.3 and 3.6]. CPUs 4 and 6 ran only in G6 and in run 2.")}
{fig(f_sparse, f"Boot A's sparse rows read {min(d['pct'] for d in SPARSE_REPEAT):+.1f} to {max(d['pct'] for d in SPARSE_REPEAT):+.1f} % of run 3's; the vary chain's best pass is faster than the sparse chain's in {VARY_FASTER_BEST} of 10 cells.", f"Best of 7 timed passes of 64 hops, CPUs 2 and 8 [table 3.3]. The 7 passes of one row spread by up to {max(o[s]['ns_rng'][1] - o[s]['ns_rng'][0] for c in OCM for r in range(5) for o in [OCM[c][r]] for s in ('sparse', 'vary')):.1f} ns, so the next figure shows medians.")}
{fig(f_sparse_med, f"By medians the vary chain is faster than the sparse one in {VARY_FASTER_MED} of 10 cells, and the dense chain is faster than both in every cell.", f"Median pass per cell, ns per load. Sparse minus dense, best passes: {min(SPARSE_MINUS_DENSE[2]):+.1f} to {max(SPARSE_MINUS_DENSE[2]):+.1f} ns on CPU 2, {min(SPARSE_MINUS_DENSE[8]):+.1f} to {max(SPARSE_MINUS_DENSE[8]):+.1f} ns on CPU 8.")}
{fig(f_split, f"On the one-line-per-page chains the L2 prefetcher adds {min(shape_stat(2, 'sparse', 'pf') + shape_stat(8, 'sparse', 'pf') + shape_stat(2, 'vary', 'pf') + shape_stat(8, 'vary', 'pf')):.1f} to {max(shape_stat(2, 'sparse', 'pf') + shape_stat(8, 'sparse', 'pf') + shape_stat(2, 'vary', 'pf') + shape_stat(8, 'vary', 'pf')):.1f} L2 refills per hop; the refills it does not account for equal the L3 read refills (black mark) within {max(abs(x) for x in REST_MINUS_L3):.2f}.", f"L2 refills per load split into those 0x81BD counts (made by a hardware prefetcher targeting the L2) and the rest, with the L3 read refills as a mark [table 3.4]. The dense chains carry {min(PF_DENSE):.2f} to {max(PF_DENSE):.2f} prefetch refills per hop, the one-line-per-page chains {min(PF_PAGE):.2f} to {max(PF_PAGE):.2f}.")}
<ul>
<li><b>What the split says (H1).</b> {ok(f" On every OCM row the L2 refills that 0x81BD does not count equal the L3 read refills within {max(abs(x) for x in REST_MINUS_L3):.2f} per load (table 3.4, last column). So the fills above one per hop that run 3 saw are refills a hardware prefetcher targeting the L2 made, and the L1 prefetcher made none (0x81BC and 0x0111 read at most {L1PF_MAX:.4f} on these rows). This is agreement between two counts on boot A; whether removing the prefetcher changes the chase time is boot B's question.")}</li>
<li><b>The prefetched lines are partly used.</b> The L3 read refills are {min(shape_stat(2, 'sparse', 'l3') + shape_stat(8, 'sparse', 'l3')):.2f} to {max(shape_stat(2, 'sparse', 'l3') + shape_stat(8, 'sparse', 'l3')):.2f} per load on the sparse rows and {min(shape_stat(2, 'dense', 'l3') + shape_stat(8, 'dense', 'l3')):.2f} to {max(shape_stat(2, 'dense', 'l3') + shape_stat(8, 'dense', 'l3')):.2f} on the dense ones, while every hop misses the L1 ({min(shape_stat(2, 'sparse', 'l1') + shape_stat(8, 'sparse', 'l1')):.2f} L1 refills per load or more). {hyp(" The loads that did not refill the L3 hit a line the prefetcher had already brought into the L2 or L3: about a quarter of the sparse hops and a tenth of the dense ones. A prefetch that lands before the load shortens that hop, so the per-hop time of these rows is below the OCM service time of an unprefetched load; boot B measures that time.")}</li>
<li><b>Pass-to-pass.</b> Within a row, a pass's time correlates only weakly with its counts: {CORR_PF:+.2f} with the prefetch refills (0x81BD), {CORR_L2:+.2f} with the L2 refills and {CORR_L3:+.2f} with the L3 read refills (each row's mean removed, pooled over the sparse and vary rows of CPUs 2 and 8). Run 3's sparse rows showed {g.CORR_L2:+.2f} with the L2 refills. So on this boot the spread between the passes of one row is not explained by how many lines the prefetcher fetched.</li>
<li><b>Vary against sparse (H2).</b> {no(f" The vary chain counts more L3 read refills than the sparse chain in {H2_MORE_L3} of 10 cells, not in all, and its prefetch refills are {min(shape_stat(2, 'vary', 'pf')):.2f} to {max(shape_stat(2, 'vary', 'pf')):.2f} per load on CPU 2 against the sparse chain's {min(shape_stat(2, 'sparse', 'pf')):.2f} to {max(shape_stat(2, 'sparse', 'pf')):.2f} (CPU 8: {min(shape_stat(8, 'vary', 'pf')):.2f} to {max(shape_stat(8, 'vary', 'pf')):.2f} against {min(shape_stat(8, 'sparse', 'pf')):.2f} to {max(shape_stat(8, 'sparse', 'pf')):.2f}). The prefetcher reacts to both one-line-per-page chains, at rates that differ more between the two CPUs than between the two shapes, so the fixed line offset is not what it reacts to.")} {hyp(" What it reacts to is the page stride itself (one member per 4 KiB page): a stride or spatial prefetcher that sees a load every 4 KiB fetches the next page's candidate lines whatever their offset. The per-prefetcher refill events (0x00D9 to 0x00DB, 0x010F, 0x0110) would name it.")} The vary chain is nevertheless faster than the sparse chain in {VARY_FASTER_MED} of 10 cells by median, by {-statistics.mean(x[3] for x in H2_CELLS):.1f} ns on average; {gap(' its cause: the two chains differ in offset pattern, in which prefetched lines are useful, and in their walks (table 3.5), and no row here separates those.')}</li>
</ul>

<h2 id="f-tlb">7. Translation activity by chain shape (H3)</h2>
{fig(f_tlb, f"A sparse hop takes {min(H3_L1):.2f} to {max(H3_L1):.2f} L1 TLB refills and {min(H3_WALK):.2f} to {max(H3_WALK):.2f} table walks; a dense hop {min(DENSE_L1):.3f} to {max(DENSE_L1):.3f} refills and {max(DENSE_WALK):.3f} walks or fewer; the L2 TLB refills read 0.000 on all 15 rows.", "Per load, mean over the timed passes, CPU 2 [table 3.5]. Rows whose /dev/ocm mapping was 16, 32 or 64 KiB aligned are marked.")}
<ul>
<li><b>H3 as stated is not supported.</b> {no(f" A sparse pass takes {min(H3_L1):.2f} to {max(H3_L1):.2f} L1 TLB refills per hop, not 1.0, on 64 pages per pass. The dense rows, 4,096 hops over the same 64 pages, take {min(DENSE_L1):.3f} to {max(DENSE_L1):.3f} per hop, which is {min(DENSE_L1) * 4096:.0f} to {max(DENSE_L1) * 4096:.0f} refills per pass of 64 pages.")}</li>
<li><b>Walks without L2 TLB refills.</b> The sparse and vary rows count {min(H3_WALK + VARY_WALK):.2f} to {max(H3_WALK + VARY_WALK):.2f} walks per hop and 0.000 L2 TLB refills. On the TLB stimulus the two were equal. {hyp(" 0x2D excludes refills that hardware prefetches caused and 0x34 counts any walk driven by a memory access [C1-Nano TRM, 0x002D and 0x0034], so these walks are translations for the prefetcher's requests into other pages, which are not installed in the L2 TLB as demand refills; the dense rows, whose prefetches stay within pages the chain has touched, walk 0.015 times per hop or fewer. The demand-only walk event 0x813C DTLB_WALK_RW would separate the two.")}</li>
<li><b>Alignment.</b> {ALIGN_COUNT[16] + ALIGN_COUNT[32] + ALIGN_COUNT[64]} of the 110 mappings are 16 KiB aligned or better (table 3.5, second table). Among the 15 TLB rows, {sum(1 for r in range(5) for s in SHAPES if TLB[r][s]['align'][0] > 4)} had such a mapping: {"; ".join(f"OCM{r} {s} ({TLB[r][s]['align'][0]} KiB)" for r in range(5) for s in SHAPES if TLB[r][s]['align'][0] > 4)}. The one dense row with an aligned mapping ({", ".join(f"OCM{r}, {a} KiB" for r, a, v in DENSE_ALIGNED)}) reads {", ".join(f"{v:.3f}" for r, a, v in DENSE_ALIGNED)} L1 TLB refills per hop; the four with 4 KiB-only mappings read {min(DENSE_PLAIN):.3f} to {max(DENSE_PLAIN):.3f}. {hyp(" On the aligned mapping the L1 TLB merged neighbouring pages into fewer entries, so the 64 pages of a region stayed resident. One row is a reading of the table, not a test: the kernel sets the alignment per mapping and the four unaligned rows differ among themselves by a factor of three. Boot C, which asks for larger entries by design, is the test.")} {gap(" H4 (boot C): not run.")}</li>
<li><b>What the TLB rows cost in time.</b> The sparse rows under the TLB set read {min(TLB[r]['sparse']['best'] for r in range(5)):.1f} to {max(TLB[r]['sparse']['best'] for r in range(5)):.1f} ns best against {min(OCM[2][r]['sparse']['best'] for r in range(5)):.1f} to {max(OCM[2][r]['sparse']['best'] for r in range(5)):.1f} under the prefetch set, the same chains on the same CPU, so the counter set does not change the row.</li>
</ul>

<h2 id="f-route">8. The route rows: where the data flits leave (G-g, H5)</h2>
<ul>
<li><b>Both ends send along X first.</b> At the DSU's crosspoint the direction with the most outgoing data flits is the X-first direction toward the node in {XFIRST_DSU} of 20 cells, and at the node's crosspoint the X-first direction toward the DSU in {XFIRST_NODE} of 20 (table 3.6); the dominant direction carries {100 * SHARE_MIN:.0f} % or more of that crosspoint's outgoing data flits in every cell, {min(FLITS_DOM):,} to {max(FLITS_DOM):,} flits per command. Where the two crosspoints share a column (CPU 4 to OCM2, CPU 6 to OCM3) the dominant direction is the Y direction, as it must be.</li>
<li><b>What that does and does not show.</b> The data channel carries the read responses, the chain build's writes and the flush write-backs; the request channel, on which the read requests travel, is not counted. So the counts show the first link of the data leaving each end, over the whole command, and nothing about the links between. {hyp(" The mesh routes X-first in both directions (dimension-order routing). Under that routing every CPU-to-node pair has one route and |dx| + |dy| hops, which is what the fits assume.")}</li>
<li><b>H5, an X hop against a Y hop.</b> {(ok if H5_SUPPORTED else no)(f" The fit over the 20 counted dense cells gives {FIT['route']['bx']:.2f} ns per X step and {FIT['route']['by']:.2f} ns per Y step (difference {H5_XY_DIFF:+.2f} ns) with a residual of {FIT['route']['rms']:.2f} ns rms; run 2's dense cells gave {FIT['run2']['bx']:.2f} and {FIT['run2']['by']:.2f}, run 3's sparse {FIT['run3']['bx']:.2f} and {FIT['run3']['by']:.2f} (table 3.7).")} {'The difference exceeds the residual and has the same sign as in runs 2 and 3.' if H5_SUPPORTED else 'The difference does not exceed the residual on these 20 cells, or its sign does not repeat, so the two costs are not separated here.'} The cells offer only |dy| of 0 or 1 and |dx| of 0 to 4, so the Y coefficient rests on 10 cells.</li>
<li><b>A second sample of every cell.</b> The G6 rows repeat the G2 dense command on CPUs 2 and 8 with the counters attached: the two differ by {min(x[2] for x in ROUTE_VS_DENSE):+.2f} to {max(x[2] for x in ROUTE_VS_DENSE):+.2f} ns per cell (best of 2 passes each). Against run 2's dense cells, boot A's counted cells read {min(ROUTE_VS_RUN2):+.2f} to {max(ROUTE_VS_RUN2):+.2f} ns.</li>
</ul>

<h2 id="f-write">9. The write-cost check (H6)</h2>
<ul>
<li>{ok(f" On one boot, run 3's program takes {min(d['delta'] for d in W):.1f} to {max(d['delta'] for d in W):.1f} ns more per pass than run 2's on the four rows (table 3.8); across the two runs the difference was {min(d['delta_orig'] for d in W):.1f} to {max(d['delta_orig'] for d in W):.1f} ns. The per-pass cost is the program's, as run 3's page said; the firmware did not change between those runs and the platform did not change here.") if H6_SUPPORTED else no(" The two programs read the same on one boot, so the per-pass difference between runs 2 and 3 was not the program.")}</li>
<li>Both programs read run 3's and run 2's own numbers back within {max(abs(100 * (d['r3prog'] - d['run3']) / d['run3']) for d in W):.2f} % and {max(abs(100 * (d['r2prog'] - d['run2']) / d['run2']) for d in W):.2f} %.</li>
</ul>

<h2 id="hyp">10. Hypotheses, one line each</h2>
<p>Boot A alone. Section 11.5 gives each verdict on the pair of boots A and B.</p>
<ul>
<li>{ok(" H1 (the fills above one per hop are prefetches): the L2 refills not counted by 0x81BD equal the L3 read refills on every OCM row; a prefetcher targeting the L2 made the rest. Boot B decides whether the chase time changes without them.")}</li>
<li>{no(" H2 (the fixed line offset is what the prefetcher reacts to): the vary chain draws prefetches as the sparse chain does.")}</li>
<li>{no(f" H3 (one L1 TLB refill per sparse hop): {min(H3_L1):.2f} to {max(H3_L1):.2f} per hop, with {min(H3_WALK):.2f} to {max(H3_WALK):.2f} walks.")}</li>
<li>{(ok if H4_SUPPORTED else no)(f" H4 (page size separates sparse from dense): with the OCM in 64 KiB translations the L1 TLB refills fall to {TLB_PASS_RNG['C'][0]:.0f} to {max(TLB_PASS_RNG['C'][1], TLB_PASS_RNG['D'][1]):.0f} per pass and the sparse-minus-dense gap narrows by mean on both pairs (section 13.2).")}</li>
<li>{(ok if H5_SUPPORTED else no)(f" H5 (an X hop costs more than a Y hop): {FIT['route']['bx']:.2f} against {FIT['route']['by']:.2f} ns per step, residual {FIT['route']['rms']:.2f} ns; both ends send X-first in 20 of 20 cells.")}</li>
<li>{ok(" H6 (the per-pass write cost is the program): run 3's program is slower per pass than run 2's on one boot.") if H6_SUPPORTED else no(" H6: no difference on one boot.")}</li>
<li>{gap(" H7 (the read loop keeps too few lines in flight): the run 5 rows are not in boot A.")}</li>
<li>Boots B to E have run: sections 11 (B), 13 (C and D), 14 (E) and 15 (the G8 rows of C and E) carry the cross-boot comparisons of follow-up-run-plan.md section 5.</li>
</ul>

<h2 id="bootb">11. Boot B: the prefetchers off, and the L3 that held no data</h2>
<p><b>The boot.</b> Boot B is boot A's platform with the data prefetchers of CPUs 2 to 9 and of their CMEs turned off: TF-A {B_TFA.group(1)} ({B_TFA.group(2)}) sets IMP_CPUECTLR_EL1 bit 48 and IMP_CMECFG_EL1 bit 28 at every core power-on and prints the readbacks [Jesse's boot B README, The prefetchers]. The script ran at commit 7921962, which adds the run 5 rows: {B['CHIP_S']:.3f} s of chip time, {len(B['CMDS'])} commands, {B['FAILED']} failed, no "# perf:" flag, perf_cov 1.0000 on all {len(B['COV_ROWS'])} counted rows. The controls repeat: {B['P4K']['ns']:.3f} ns at 4 KiB and {B['RT_NS'][0]:.3f} to {B['RT_NS'][1]:.3f} ns for the CME round trip. The prefetchers were off: every prefetch refill counter reads {B_PF_MAX:.4f} per load in all {len(B_PF_ROWS)} counted rows that carry one, and the sequential 8 MiB chain, which boot A's prefetcher ran at {SEQ['ns']:.3f} ns per load, reads {B['SEQ']['ns']:.3f} ns, the flushed random chain's {B['FLUSHED']['ns']:.3f} [latency-dram-seq.csv, latency-dram-flushed.csv].</p>
<h3 id="t111">11.1 The L3 of CPUs 2 to 9 holds no data</h3>
{tb2}
<ul>
<li><b>What the hit set counts.</b> L3 read hits (0x81C6) are {L3_HIT_MAX:.4f} per load in every row from 64 KiB to 512 KiB, and L3 read accesses (0xA0) equal L3 read refills (0xA2) within {L3_ACC_VS_REFILL:.4f} per load: every read that reached the L3 was filled from outside the cluster. The 192 KiB row is {100 * L3_BEST[196608]['e']['l2d_hit_rd']:.0f} % L2 hits and {100 * L3_BEST[196608]['e']['l3d_refill_rd']:.0f} % reads from the mesh, with no level between the L2's {L3_BEST[131072]['ns']:.2f} ns and the mesh's {L3_BEST[393216]['ns']:.2f} ns.</li>
<li><b>Why.</b> IMP_CLUSTERPWRSTAT_EL1 read {B_PWRSTAT[0][1]} just before and {B_PWRSTAT[1][1]} just after the hit-set command [log.txt lines 7 and 9]: one L3 slice in snoop-filter-only mode. The SCP firmware (0.48.0-nopcie.1) stages the full-L3 operating mode (PWPR = 0x00070008, all slices and full RAM) for cluster 0 only, at boot; the clusters of CPUs 2 to 9 are powered on later by Linux through the standard driver and stay in operating mode 0, and the firmware comment marks the other clusters as a follow-up [asimov-scp-firmware mod_asimov_system.c at 9ef7952, asimov_system_stage_cluster_op_policy and its one call with cluster 0; Jesse's boot B README, L3 power].</li>
<li><b>What it changes.</b> On every run so far (runs 1 to 3, boots A and B) the measured cores had no L3 data cache: the "L3" rows of the run 3 pages (14.0 ns at 192 KiB) are L2 hits mixed with SLC reads, and boot A's H1 reading (L2 refills not made by a prefetcher equal L3 read refills) is the same fact seen from the L2. Boot E, with the L3 staged on by a rebuilt SCP, shows the level (section 14), and the run 3 pages now carry the relabel; sections 1 to 10 of this page keep run 3's level names as boot A's record.</li>
</ul>
<h3 id="t112">11.2 The core's chases with the prefetchers off</h3>
{tb1}
<ul>
<li><b>The random chases did not move.</b> Over the {len(AB_LV_RANDOM_PCT)} random rows from 4 KiB to 32 MiB, boot B is {min(AB_LV_RANDOM_PCT):+.1f} % to {max(AB_LV_RANDOM_PCT):+.1f} % of boot A. A dependent random chase gives a prefetcher nothing to follow, so its latencies are the levels' own.</li>
<li><b>The OCM chains did move.</b> By the median of each cell's passes, the dense chains read {min(B_SHAPE_PCT['dense']):+.0f} % to {max(B_SHAPE_PCT['dense']):+.0f} % against boot A, the vary chains {min(B_SHAPE_PCT['vary']):+.0f} % to {max(B_SHAPE_PCT['vary']):+.0f} %, the sparse chains {min(B_SHAPE_PCT['sparse']):+.0f} % to {max(B_SHAPE_PCT['sparse']):+.0f} % (table 11.3). On boot A the L2 prefetcher brought part of the dense chain's next lines in early; on boot B every hop is a demand read from the region.</li>
</ul>
{fig(f_b_dense, f"With the prefetchers off, the dense OCM cells read {min(B_SHAPE_PCT['dense']):+.0f} % to {max(B_SHAPE_PCT['dense']):+.0f} % slower by median, and the fit of the 20 route cells to distance tightens from {FIT['route']['rms']:.2f} ns to {B['FIT']['route']['rms']:.2f} ns rms.", f"Dense chains, 4,096 hops per pass, median of the passes on each boot [latency-ocm-region&lt;r&gt;-dense-cpu&lt;c&gt;.csv of 005 and 006].")}
<h3 id="t113">11.3 OCM cells, boot A against boot B</h3>
{tb3}
<h3 id="t114">11.4 The one-core read with lines in flight (H7)</h3>
{tb4}
<p>With the hardware prefetcher off, the plain read loop moves {RP_BEST[('read', 2097152)]:.2f} GB/s at 2 MiB and {RP_BEST[('read', 33554432)]:.2f} GB/s at 32 MiB, against run 3's {RP_RUN3[2097152]:.2f} and {RP_RUN3[33554432]:.2f} with it on. A PRFM hint 4 lines ahead raises the two rows to {RP_BEST[('read-pf4', 2097152)]:.2f} and {RP_BEST[('read-pf4', 33554432)]:.2f} GB/s, more than twice the plain loop; 8 and 16 lines ahead give less than 4, and a second stream gives nothing. So on this boot the number of lines in flight sets the read rate (H7 supported for the prefetcher-off case). Whether the hint adds to the hardware prefetcher's rate is boot C's question, where these rows run with the prefetcher on.</p>
<h3 id="t115">11.5 The hypotheses on the pair of boots</h3>
<ul>
<li>{(ok if HB1 else no)(f" H1 (the fills above one per hop are prefetches): on boot B the sparse rows count {min(B_SPARSE_L2):.3f} to {max(B_SPARSE_L2):.3f} L2 refills and {min(B_SPARSE_L3):.3f} to {max(B_SPARSE_L3):.3f} L3 read refills per hop, one line per hop, where boot A counted {min(A_SPARSE_L2):.2f} to {max(A_SPARSE_L2):.2f} L2 refills; the extra fills vanish with the prefetchers.")}</li>
<li>{no(f" H2 (the fixed line offset is what the prefetcher reacts to): on boot B the vary chain is faster than the sparse one by median in {B['VARY_FASTER_MED']} of 10 cells ({min(x[3] for x in B['H2_CELLS']):+.2f} to {max(x[3] for x in B['H2_CELLS']):+.2f} ns), against 10 of 10 on boot A: boot A's vary advantage came from the prefetcher, whose fills were more often useful on the vary chain, not from more prefetches on the sparse chain (boot A counted the same number on both).")}</li>
<li>{no(f" H3 (one L1 TLB refill per sparse hop): {min(B['H3_L1']):.2f} to {max(B['H3_L1']):.2f} L1 TLB refills per hop on boot B, and the page-table walks fall from boot A's {min(H3_WALK):.2f} to {max(H3_WALK):.2f} per hop to {max(B['H3_WALK']):.2f}: the walks on boot A were the prefetchers' translations, not the chain's.")}</li>
<li>{(ok if H4_SUPPORTED else no)(f" H4 (page size separates sparse from dense): with the OCM in 64 KiB translations the L1 TLB refills fall to {TLB_PASS_RNG['C'][0]:.0f} to {max(TLB_PASS_RNG['C'][1], TLB_PASS_RNG['D'][1]):.0f} per pass and the sparse-minus-dense gap narrows by mean on both pairs (section 13.2).")}</li>
<li>{(ok if HB5 else no)(f" H5 (an X hop costs more than a Y hop): with the prefetchers off the 20 route cells fit {B['FIT']['route']['a']:.2f} + {B['FIT']['route']['bx']:.2f} ns per X step + {B['FIT']['route']['by']:.2f} ns per Y step with {B['FIT']['route']['rms']:.2f} ns rms, against {FIT['route']['rms']:.2f} ns rms on boot A; the cells now order by distance.")}</li>
<li>{(ok if B['H6_SUPPORTED'] else no)(f" H6 (the per-pass write cost is the program): run 3's program is again slower per pass than run 2's on one boot, by {min(w['delta'] for w in B['W']):.1f} to {max(w['delta'] for w in B['W']):.1f} ns.")}</li>
<li>{(ok if HB7 else no)(f" H7 (the plain read loop keeps too few lines in flight): PRFM 4 lines ahead more than doubles the plain loop's rate at both sizes on the prefetcher-off boot (11.4).")}</li>
</ul>

<h2 id="five">12. Boots C, D and E: the five boots side by side</h2>
<p>Round four ran five boots. Each row of table 12 is the same command on every boot that has it. What differs between the boots: the commit of cache-mem-perf, the data prefetchers (off on B and D through a TF-A hook), the SCP firmware (E's stages the full L3 for the clusters of CPUs 2 to 9) and the OCM mapping (C and D map each region in 64 KiB contiguous translations). The controls repeat on all five: {min(BT[x]['P4K']['ns'] for x in BOOT_ORDER):.3f} to {max(BT[x]['P4K']['ns'] for x in BOOT_ORDER):.3f} ns at 4 KiB and {min(BT[x]['RT_NS'][0] for x in BOOT_ORDER):.3f} to {max(BT[x]['RT_NS'][1] for x in BOOT_ORDER):.3f} ns for the CME round trip. Every command exited 0 and every file's checksum matched [log.txt and SHA256SUMS of 007, 008 and 010, checked here].</p>
{t12}
<ul>
<li><b>Boot C</b> (membench-jibin-007, commit b79dffa) is boot A's platform with the OCM mapped in 64 KiB contiguous translations: each of its {len(BT['C']['MAPS'])} mappings reads cont=64/64 in the kernel log [dmesg.txt of 007]. A's repeat did not run: C's sequential chain reads {BT['C']['SEQ']['ns']:.3f} ns with {BT['C']['SEQ']['emean']['l1d_refill_hwprf']:.4f} L1 prefetch refills per load, boot A's {SEQ['ns']:.3f} ns with {SEQ['emean']['l1d_refill_hwprf']:.4f}, which was the condition for dropping it [Jesse's boot C README, Read first].</li>
<li><b>Boot D</b> (membench-jibin-008, commit ed6056a: the emulator was granted before b79dffa was sent) is boot B's platform with the same mapping. D against B is the hint alone, with the prefetchers off on both.</li>
<li><b>Boot E</b> (membench-jibin-010, commit b79dffa) is boot C's program, build, TF-A and kernel with a rebuilt SCP, 0.48.0-nopcie-l3.1 (commit 28663ab on e361a83), that stages cluster operating mode 7 (all slices, the full L3 RAM) for the clusters of CPUs 2 to 9 before the primary core powers on, and with the OCM back in 4 KiB pages. IMP_CLUSTERPWRSTAT_EL1 read {EX['E']['pwrstat'][0]} just before and {EX['E']['pwrstat'][1]} just after the hit-set command [log.txt of 010, lines 7 and 9; Jesse's boot E README, The SCP and L3 power]. E against C is the L3 alone on every DRAM row.</li>
</ul>

<h2 id="hint">13. Boots C and D: the OCM in 64 KiB translations (H4)</h2>
<h3 id="t131">13.1 The TLB rates fell</h3>
{t13a}
{fig(f_cd_tlb, f"With the OCM in 64 KiB translations the L1 data TLB refills {TLB_PASS_RNG['C'][0]:.0f} to {max(TLB_PASS_RNG['C'][1], TLB_PASS_RNG['D'][1]):.0f} times per pass on every chain, against {TLB_PASS_RNG['A'][0]:.0f} to {TLB_PASS_RNG['A'][1]:.0f} on boot A and {TLB_PASS_RNG['B'][0]:.0f} to {TLB_PASS_RNG['B'][1]:.0f} on boot B.", "CPU 2's 15 TLB-set chains, mean over the passes of the L1 data TLB refills (0x05) per pass [latency-ocm-region&lt;r&gt;-&lt;shape&gt;-tlb-cpu2.csv of 005 to 008]. A sparse or vary pass is 64 hops over 64 pages; a dense pass is 4,096 hops over the whole region.")}
<ul>
<li><b>The sparse and vary chains</b> went from {TLB_PASS_RNG_SPARSE['A'][0]:.0f} to {TLB_PASS_RNG_SPARSE['A'][1]:.0f} refills per pass (boots A and B alike) to {min(TLB_PASS_RNG_SPARSE['C'][0], TLB_PASS_RNG_SPARSE['D'][0]):.0f} to {max(TLB_PASS_RNG_SPARSE['C'][1], TLB_PASS_RNG_SPARSE['D'][1]):.0f}; the dense chains from {min(TLB_PASS_RNG_DENSE['A'][0], TLB_PASS_RNG_DENSE['B'][0]):.0f} to {max(TLB_PASS_RNG_DENSE['A'][1], TLB_PASS_RNG_DENSE['B'][1]):.0f} to {min(TLB_PASS_RNG_DENSE['C'][0], TLB_PASS_RNG_DENSE['D'][0]):.0f} to {max(TLB_PASS_RNG_DENSE['C'][1], TLB_PASS_RNG_DENSE['D'][1]):.0f}. The core holds a 64 KiB block as two 32 KiB entries in its L1 data TLB, so a region needs 8 entries [Jesse's boot C README, OCM mappings]; which entries the remaining 11 to 15 refills per pass are, these files do not show.</li>
<li><b>The 32 MiB stimulus on 4 KiB DRAM pages,</b> which the hint does not reach, kept its {min(STIM[x]['l1'] for x in BOOT_ORDER):.3f} to {max(STIM[x]['l1'] for x in BOOT_ORDER):.3f} refills per hop on every boot. Its walks per hop (0x34) read {STIM['A']['walk']:.3f} on A, {STIM['B']['walk']:.3f} on B, {STIM['C']['walk']:.3f} on C, {STIM['D']['walk']:.3f} on D and {STIM['E']['walk']:.3f} on E, and its time {STIM['A']['best']:.2f}, {STIM['B']['best']:.2f}, {STIM['C']['best']:.2f}, {STIM['D']['best']:.2f} and {STIM['E']['best']:.2f} ns: the walk rate on this chain differs from process to process, and the process that walked least ran fastest [latency-dram-tlb-cpu2.csv]. The walk rows ran the same stimulus in another process on each boot and counted {WALK_STIM['C']['emean']['dtlb_walk']:.3f}, {WALK_STIM['D']['emean']['dtlb_walk']:.3f} and {WALK_STIM['E']['emean']['dtlb_walk']:.3f} walks per hop on C, D and E, {WALK_STIM['C']['emean']['dtlb_walk'] / STIM['C']['walk']:.1f}, {WALK_STIM['D']['emean']['dtlb_walk'] / STIM['D']['walk']:.0f} and {WALK_STIM['E']['emean']['dtlb_walk'] / STIM['E']['walk']:.1f} times the TLB-set rows' [latency-dram-walk-cpu2.csv of 007, 008 and 010]. So a walk rate on this chain is the process's, not the boot's: D's {STIM['D']['walk']:.3f} is not the hint's effect (the hint does not reach DRAM pages), and why the rate differs between two processes of one boot is Insufficient data.</li>
</ul>
<h3 id="t132">13.2 The OCM cells, and H4</h3>
{t13b}
{fig(f_cd_gap, f"The sparse chain's cost above the dense one fell from a mean of {GAP_MEAN['A']:.1f} ns (boot A) to {GAP_MEAN['C']:.1f} ns (boot C) with the prefetchers on, and from {GAP_MEAN['B']:.1f} ns (boot B) to {GAP_MEAN['D']:.1f} ns (boot D) with them off.", f"Best pass of the sparse chain minus best pass of the dense chain, CPU 2, per region [latency-ocm-region&lt;r&gt;-cpu2.csv and -dense-cpu2.csv of 005 to 008]. The 64 KiB translations narrowed the gap in {H4_GAP_CLOSED['CA']} of 5 regions on C and {H4_GAP_CLOSED['DB']} of 5 on D.")}
<ul>
<li>{(ok if H4_SUPPORTED else no)(f" H4 (the page size separates sparse from dense): the TLB refills fell on all 15 chains, and the sparse-minus-dense gap narrowed by mean on both pairs, in {H4_GAP_CLOSED['CA']} of 5 regions on C against A and {H4_GAP_CLOSED['DB']} of 5 on D against B. On D the gap is {min(GAP['D']):.1f} to {max(GAP['D']):.1f} ns, so the page size is part of what separates the two shapes, not all of it.")}</li>
<li><b>D against B, the hint alone:</b> {RATIOS[('D', 'B')]['faster']} of {RATIOS[('D', 'B')]['n']} core OCM rows faster, {RATIOS[('D', 'B')]['lo']:.3f} to {RATIOS[('D', 'B')]['hi']:.3f} times B, geometric mean {RATIOS[('D', 'B')]['gm']:.3f}: the hint buys about {100 * (1 - RATIOS[('D', 'B')]['gm']):.1f} % on these rows, most on the chains that touch one line per page. The route fit on D, {BT['D']['FIT']['route']['a']:.2f} + {BT['D']['FIT']['route']['bx']:.2f} ns per X step + {BT['D']['FIT']['route']['by']:.2f} ns per Y step with {BT['D']['FIT']['route']['rms']:.2f} ns rms, repeats B's ({BT['B']['FIT']['route']['bx']:.2f}, {BT['B']['FIT']['route']['by']:.2f}, {BT['B']['FIT']['route']['rms']:.2f} ns rms): H5 holds on D too.</li>
<li><b>C against A:</b> {RATIOS[('C', 'A')]['faster']} of {RATIOS[('C', 'A')]['n']} rows faster, {RATIOS[('C', 'A')]['lo']:.3f} to {RATIOS[('C', 'A')]['hi']:.3f} times A, geometric mean {RATIOS[('C', 'A')]['gm']:.3f}. This pair spans two commits and rests on A's one placement draw, so it is a weaker test than D against B. C against D, the prefetchers with the hint on both: {RATIOS[('C', 'D')]['faster']} of {RATIOS[('C', 'D')]['n']} rows faster on C, geometric mean {RATIOS[('C', 'D')]['gm']:.3f}.</li>
<li><b>H6 on the b79dffa build.</b> On boots C and E the 16 KiB write row no longer shows the per-pass cost: run 3's program reads {-BT['C']['W'][0]['delta']:.2f} and {-BT['E']['W'][0]['delta']:.2f} ns per pass faster than run 2's at 16 KiB, and {min(w['delta'] for x in 'CE' for w in BT[x]['W'][1:]):.1f} to {max(w['delta'] for x in 'CE' for w in BT[x]['W'][1:]):.1f} ns slower at 48 to 256 KiB. C's and E's bandwidth build is b79dffa's, whose default form of each row is the same program for what the rows measure but not byte for byte [Jesse's boot C README, The G8 rows]. So H6 holds on the builds of boots A, B and D (16 KiB: {W[0]['delta']:.1f}, {BT['B']['W'][0]['delta']:.1f} and {BT['D']['W'][0]['delta']:.1f} ns) and not at 16 KiB on b79dffa's.</li>
</ul>
<h3 id="t133">13.3 The walk rows</h3>
{t13c}
<ul>
<li><b>Three walk events</b> ran on the TLB-set chains of boots C, D and E: 0x34 (translation table walks), 0x8188 (walks that ended in a block entry) and 0x818A (walks that ended in a page entry). On the 32 MiB stimulus, on 4 KiB pages, 0x818A equals 0x34 and 0x8188 reads 0 on all three boots: every walk ended in a page entry, as it must there, so 0x818A counts on this image.</li>
<li><b>On boot D's five OCM walk rows</b> all three events read 0 in every one of the {WALK_OCM_PASSES['D']} passes: with the hint and no prefetcher, a timed pass walks no table. On C and E, prefetchers on, 0x34 counts up to {WALK_OCM_34['C'][1]:.2f} and {WALK_OCM_34['E'][1]:.2f} walks per hop, in {WALK_OCM_NONZERO['C']} and {WALK_OCM_NONZERO['E']} of 35 passes, while 0x8188 reads 0 everywhere and 0x818A at most {max(WALK_OCM_PAGE_MAX['C'], WALK_OCM_PAGE_MAX['E']):.4f} per hop: walks that 0x34 counts and neither of the other two does. 0x8188 has read nonzero on no boot, so it stays unvalidated.</li>
<li><b>The walks are the prefetchers'.</b> Boot B's TLB-set rows (prefetchers off, 4 KiB pages) counted 0 walks per hop (11.5), D's 0 with the hint, and A's, C's and E's, prefetchers on, {min(H3_WALK):.2f} to {max(H3_WALK):.2f}, {min(BT['C']['H3_WALK']):.2f} to {max(BT['C']['H3_WALK']):.2f} and {min(BT['E']['H3_WALK']):.2f} to {max(BT['E']['H3_WALK']):.2f} per hop on the sparse chains.</li>
</ul>

<h2 id="boote">14. Boot E: the L3 turned on</h2>
<h3 id="t141">14.1 The hit set: where each read is served</h3>
{t14a}
{fig(f_e_hits, f"With the L3 on, the 192 to 384 KiB chases are served {100 * min(E_L3['best'][s]['e']['l3d_hit_rd'] for s in (196608, 262144, 393216)):.0f} % to {100 * max(E_L3['best'][s]['e']['l3d_hit_rd'] for s in (196608, 262144, 393216)):.0f} % from the L3 and read {E_L3['best'][196608]['ns']:.1f} to {E_L3['best'][393216]['ns']:.1f} ns, against {C_L3['best'][196608]['ns']:.1f} to {C_L3['best'][393216]['ns']:.1f} ns on boot C, where the same reads came from the mesh.", f"Per load of the best rep, boots C and E [latency-dram-small-l3.csv of 007 and 010]. L3 read accesses (0xA0) equal L3 read refills (0xA2) plus L3 read hits (0x81C6) within {max(E_L3['acc_minus_refill_minus_hit'], C_L3['acc_minus_refill_minus_hit']):.4f} per load on every row of both boots. On C, as on B and D, the hits are {C_L3['hit_max']:.4f} in every row.")}
<ul>
<li><b>An L3 hit costs about {statistics.mean(L3_HIT_EST.values()):.1f} ns (est.).</b> E's 256 KiB row reads {E_L3['best'][262144]['ns']:.3f} ns with {E_L3['best'][262144]['e']['l2d_hit_rd']:.3f} L2 hits, {E_L3['best'][262144]['e']['l3d_hit_rd']:.3f} L3 hits and {E_L3['best'][262144]['e']['l3d_refill_rd']:.4f} outside refills per load. Taking the L2 hop at E's 128 KiB row ({E_L2_NS:.3f} ns) and the outside hop at C's 384 KiB row ({C_MESH_NS:.3f} ns) leaves {L3_HIT_EST[262144]:.1f} ns per L3 hit, and the 384 KiB row gives {L3_HIT_EST[393216]:.1f} ns. asimov-bench's chase of a 192 KiB set on an older RTL read 15.16 ns per load and took it as a lower bound on an L3 hit; E's 192 KiB row reads {E_L3['best'][196608]['ns']:.3f} ns with {100 * E_L3['best'][196608]['e']['l3d_hit_rd']:.0f} % L3 hits [Jesse's boot E README, Against boot C].</li>
<li><b>At 512 KiB the L3 holds part of the set:</b> {100 * E_L3['best'][524288]['e']['l3d_hit_rd']:.0f} % L3 hits and {100 * E_L3['best'][524288]['e']['l3d_refill_rd']:.0f} % outside refills per load, {E_L3['best'][524288]['ns']:.2f} ns against C's {C_L3['best'][524288]['ns']:.2f}. The random 768 KiB and 1 MiB chains read {lv_ns('E', 786432, 'fresh'):.2f} and {lv_ns('E', 1048576, 'fresh'):.2f} ns against C's {lv_ns('C', 786432, 'fresh'):.2f} and {lv_ns('C', 1048576, 'fresh'):.2f}: from there the row is the SLC's.</li>
<li><b>Nothing below 128 KiB moved.</b> The 4 to 128 KiB chases read {min(EC_SMALL_RATIO):.3f} to {max(EC_SMALL_RATIO):.3f} times C's; the L2 serves {min(E_L3['best'][s]['e']['l2d_hit_rd'] for s in (65536, 98304, 131072)):.2f} to {max(E_L3['best'][s]['e']['l2d_hit_rd'] for s in (65536, 98304, 131072)):.2f} of the reads at 64 to 128 KiB on both boots.</li>
</ul>
<h3 id="t142">14.2 Latency by footprint, boot C against boot E</h3>
{fig(f_e_levels, f"The L3 step appears: from 192 KiB to 512 KiB boot E reads {min(EC_RATIO[(s, k)] for s, k in EC_RATIO if 196608 <= s <= 524288):.2f} to {max(EC_RATIO[(s, k)] for s, k in EC_RATIO if 196608 <= s <= 524288):.2f} times boot C, and from 1.5 MiB on {min(EC_RATIO[(s, k)] for s, k in EC_RATIO if s >= 1572864 and k == 'fresh'):.3f} to {max(EC_RATIO[(s, k)] for s, k in EC_RATIO if s >= 1572864 and k == 'fresh'):.3f} times.", "CPU 2, best rep or best pass [latency-dram-small.csv and latency-dram-large.csv of 007 and 010]. Up to 384 KiB the same list is walked repeatedly; from 512 KiB a random list is walked once. Hover a dot for the value.")}
{t14b}
<ul>
<li><b>The SLC and DRAM rows stayed.</b> 2 MiB reads {lv_ns('E', 2097152, 'fresh'):.3f} against {lv_ns('C', 2097152, 'fresh'):.3f} ns ({EC_RATIO[(2097152, 'fresh')]:.3f}), and 3 to 8 MiB {min(EC_RATIO[(s, 'fresh')] for s in (3145728, 4194304, 6291456, 8388608)):.3f} to {max(EC_RATIO[(s, 'fresh')] for s in (3145728, 4194304, 6291456, 8388608)):.3f} times C. At 16 and 32 MiB E reads {lv_ns('E', 16777216, 'fresh'):.3f} and {lv_ns('E', 33554432, 'fresh'):.3f} ns, {E_ABOVE_16_32[16777216]:.2f} and {E_ABOVE_16_32[33554432]:.2f} ns above the highest of boots A to D, with one outside refill per load as before. What raised these two rows is Insufficient data: the counters of these files are the same on both boots.</li>
<li><b>The sequential chain fell to {E_SEQ['ns']:.3f} ns</b> against {C_SEQ['ns']:.3f} on C, with the same {E_SEQ['emean']['l1d_refill_hwprf']:.4f} L1 prefetch refills per load on both. {hyp(" With the L3 holding data the prefetcher's stream drains into the L3 and the L2 refills complete sooner; the sequential row with the prefetchers off and the L3 on (not run) would show how much of the 2.49 ns is the prefetcher's.")}</li>
</ul>
<h3 id="t143">14.3 The one-core read (G7) on boots B, C, D and E</h3>
{t14c}
{fig(f_e_read, f"With the L3 on the plain read loop reaches {EX['E']['rp'][('read', 2097152)]['agg']:.1f} GB/s at 2 MiB and {EX['E']['rp'][('read', 33554432)]['agg']:.1f} at 32 MiB, {EX['E']['rp'][('read', 2097152)]['agg'] / EX['C']['rp'][('read', 2097152)]['agg']:.2f} and {EX['E']['rp'][('read', 33554432)]['agg'] / EX['C']['rp'][('read', 33554432)]['agg']:.2f} times boot C's; the software hint, which more than doubled the prefetcher-off rate, is now below the plain loop.", "One thread on CPU 2, best of 3 reps, GB = 1e9 bytes [bandwidth-read-prefetch.csv of 006 to 010]. The plain loop reads one line per iteration; the pf4, pf8 and pf16 rows issue PRFM 4, 8 or 16 lines ahead; the 2s row reads two streams.")}
<ul>
<li><b>Cycles per line.</b> E's plain read takes {RP_CYC['E'][2097152]:.2f} to {RP_CYC['E'][33554432]:.2f} cycles per line against C's {RP_CYC['C'][2097152]:.2f} to {RP_CYC['C'][33554432]:.2f}, with {EX['E']['rp'][('read', 33554432)]['e']['l1d_refill_hwprf']:.4f} L1 prefetch refills per line on both. {hyp(f" The hardware prefetcher runs ahead of the loop on both boots; on E its lines wait in the L3, about {statistics.mean(L3_HIT_EST.values()):.0f} ns from the core (est.), instead of in the SLC across the mesh, so the loop stalls less per line. The same rows with the prefetchers off and the L3 on would test it.")}</li>
<li><b>The software hint adds little with the hardware prefetcher on.</b> On C, PRFM 4 lines ahead reads {EX['C']['rp'][('read-pf4', 2097152)]['agg']:.2f} against the plain loop's {EX['C']['rp'][('read', 2097152)]['agg']:.2f} GB/s at 2 MiB and {EX['C']['rp'][('read-pf4', 33554432)]['agg']:.2f} against {EX['C']['rp'][('read', 33554432)]['agg']:.2f} at 32 MiB (section 11.4's question). On B and D, prefetchers off, the five rows repeat within {100 * max(abs(EX['D']['rp'][k]['agg'] / EX['B']['rp'][k]['agg'] - 1) for k in EX['B']['rp']):.1f} %: the OCM hint changes nothing on these DRAM rows.</li>
</ul>
<h3 id="t144">14.4 The OCM rows on boot E</h3>
<ul>
<li><b>The sparse per-region rows partly hit in the L3.</b> They count {min(E_SPARSE_L3):.2f} to {max(E_SPARSE_L3):.2f} outside refills (0xA2) per hop on E ({sum(1 for v in E_SPARSE_L3 if v < 0.8)} of the 10 cells below 0.8) against {min(AC_SPARSE_L3):.2f} to {max(AC_SPARSE_L3):.2f} on A and C: part of each pass's lines were still in the L3 from the pass before, so on E these rows are not pure mesh rows. Their best passes read {min(RATIOS[('E', 'A')]['rows'][k] for k in RATIOS[('E', 'A')]['rows'] if k.endswith('sparse')):.2f} to {max(RATIOS[('E', 'A')]['rows'][k] for k in RATIOS[('E', 'A')]['rows'] if k.endswith('sparse')):.2f} times A's.</li>
<li><b>The dense all-five row keeps one outside refill per hop</b> ({E_ALL5_DENSE_L3[2]:.4f} and {E_ALL5_DENSE_L3[8]:.4f} per hop on CPUs 2 and 8) and reads {ALL5_DENSE_BEST['E']:.2f} ns on E against {ALL5_DENSE_BEST['A']:.2f} on A and {ALL5_DENSE_BEST['C']:.2f} on C: the OCM number of the run 3 pages stands on the L3-on boot.</li>
<li><b>The route fit is not usable on E:</b> {BT['E']['FIT']['route']['a']:.2f} + {BT['E']['FIT']['route']['bx']:.2f} ns per X step {BT['E']['FIT']['route']['by']:+.2f} ns per Y step with {BT['E']['FIT']['route']['rms']:.2f} ns rms, since the route rows' lines are partly L3 hits. Over the 69 core OCM rows E reads {RATIOS[('E', 'A')]['lo']:.3f} to {RATIOS[('E', 'A')]['hi']:.3f} times A ({RATIOS[('E', 'A')]['faster']} faster, geometric mean {RATIOS[('E', 'A')]['gm']:.3f}); the pair differs in the SCP, the commit, the build and each row's placement draw, so it is not the L3 alone.</li>
</ul>

<h2 id="g8">15. The L1 bandwidth rows (G8) on boots C and E</h2>
<p>Run 5c added sixteen one-core rows on CPU 2: a read and a write of 4, 8, 16 and 24 KiB (1,024, 512, 256 and 176 passes, 5 reps, the perf columns) in two forms: the looped form, one call of the kernel per pass, and the single-call form, all passes of a rep inside one assembly call. The reading rule of follow-up-run-plan.md section 12: a straight line t_pass = a + bytes / rate through the four best reps gives the fixed cost per pass (a) and the L1 rate; the fit counts only when its largest residual is under 2 % of the smallest pass time, and a row is an L1 row when its L1 refills are under 0.01 per line. The core's read path is dual 128-bit, 32 B per cycle, 64 GB/s at 2 GHz; its write path is 128-bit, 32 GB/s [C1-Nano TRM].</p>
{t15}
{fig(f_g8, f"In the single-call form the core reads {min(G8[x][('asm', 'read')]['rows'][s]['agg'] for x in G8 for s in (16384, 24576)):.1f} to {max(G8[x][('asm', 'read')]['rows'][s]['agg'] for x in G8 for s in (16384, 24576)):.1f} GB/s at 16 and 24 KiB, {100 * max(G8[x][('asm', 'read')]['rows'][s]['agg'] for x in G8 for s in (16384, 24576)) / 64:.0f} % of the 64 GB/s read path, and writes {min(G8[x][(f, 'write')]['rows'][24576]['agg'] for x in G8 for f in ('per-pass', 'asm')):.1f} to {max(G8[x][(f, 'write')]['rows'][24576]['agg'] for x in G8 for f in ('per-pass', 'asm')):.1f} GB/s at 24 KiB, the 32 GB/s write path.", f"Best of 5 reps, GB = 1e9 bytes [bandwidth-l1-passes.csv and bandwidth-l1-asmpasses.csv of 007 and 010, read by l1_reader.py]. L1 refills are at most {G8_L1_MAX:.4f} per line on every row, so every row is an L1 row.")}
{t15b}
<ul>
<li><b>The write fits hold</b> on both boots and both forms: rate {min(G8[x][(f, 'write')]['rate'] for x in G8 for f in ('per-pass', 'asm')):.1f} to {max(G8[x][(f, 'write')]['rate'] for x in G8 for f in ('per-pass', 'asm')):.1f} GB/s (16 B per cycle, the write path), fixed cost {G8['C'][('per-pass', 'write')]['a_ns']:.1f} and {G8['E'][('per-pass', 'write')]['a_ns']:.1f} ns per pass in the looped form and {G8['C'][('asm', 'write')]['a_ns']:.1f} and {G8['E'][('asm', 'write')]['a_ns']:.1f} ns in the single-call form, residuals {min(G8[x][(f, 'write')]['resid_pct'] for x in G8 for f in ('per-pass', 'asm')):.1f} to {max(G8[x][(f, 'write')]['resid_pct'] for x in G8 for f in ('per-pass', 'asm')):.1f} %.</li>
<li><b>The read fits fail the rule</b> on both boots and both forms (residuals {min(G8[x][(f, 'read')]['resid_pct'] for x in G8 for f in ('per-pass', 'asm')):.1f} to {max(G8[x][(f, 'read')]['resid_pct'] for x in G8 for f in ('per-pass', 'asm')):.1f} %), so the read's fixed cost per pass is Insufficient data as a single number. Without a fit the rows still show: between the 8 and 16 KiB rows the added bytes move at {min(G8_MARGINAL.values()):.1f} to {max(G8_MARGINAL.values()):.1f} GB/s on every form, the path's rate; and each read row's time above the 64 GB/s ideal is {min(G8[x][('asm', 'read')]['rows'][s]['above_ideal'] for x in G8 for s in G8_SIZES):.0f} to {max(G8[x][('asm', 'read')]['rows'][s]['above_ideal'] for x in G8 for s in G8_SIZES):.0f} ns per pass in the single-call form and {min(G8[x][('per-pass', 'read')]['rows'][s]['above_ideal'] for x in G8 for s in G8_SIZES):.0f} to {max(G8[x][('per-pass', 'read')]['rows'][s]['above_ideal'] for x in G8 for s in G8_SIZES):.0f} ns in the looped form (table 15b).</li>
<li><b>So the run 3 open item is answered in part.</b> Run 3's {next(d['read'] for d in g.ONE if d['size'] == 16384):.1f} GB/s at 16 KiB, {100 * next(d['read'] for d in g.ONE if d['size'] == 16384) / 64:.0f} % of the read path, was the loop's cost per pass, not the L1's rate: once a pass is long enough the added bytes move at the path's rate, and in the single-call form the 16 and 24 KiB rows reach {100 * min(G8[x][('asm', 'read')]['rows'][s]['agg'] for x in G8 for s in (16384, 24576)) / 64:.0f} % of it. What the remaining {min(G8[x][('asm', 'read')]['rows'][s]['above_ideal'] for x in G8 for s in (16384, 24576)):.0f} to {max(G8[x][('asm', 'read')]['rows'][s]['above_ideal'] for x in G8 for s in (16384, 24576)):.0f} ns per pass is, these rows do not show.</li>
<li><b>Unexplained:</b> E's 4 KiB looped-form read reads {G8['E'][('per-pass', 'read')]['rows'][4096]['agg']:.2f} GB/s against C's {G8['C'][('per-pass', 'read')]['rows'][4096]['agg']:.2f}, with reps within {100 * (G8['E'][('per-pass', 'read')]['rows'][4096]['reps'][-1] - G8['E'][('per-pass', 'read')]['rows'][4096]['reps'][0]) / G8['E'][('per-pass', 'read')]['rows'][4096]['reps'][-1]:.1f} % on E and {100 * (G8['C'][('per-pass', 'read')]['rows'][4096]['reps'][-1] - G8['C'][('per-pass', 'read')]['rows'][4096]['reps'][0]) / G8['C'][('per-pass', 'read')]['rows'][4096]['reps'][-1]:.1f} % on C; the other 15 rows read {min(G8['E'][k]['rows'][s]['agg'] / G8['C'][k]['rows'][s]['agg'] for k in G8['E'] for s in G8_SIZES if (k, s) != (('per-pass', 'read'), 4096)):.3f} to {max(G8['E'][k]['rows'][s]['agg'] / G8['C'][k]['rows'][s]['agg'] for k in G8['E'] for s in G8_SIZES if (k, s) != (('per-pass', 'read'), 4096)):.3f} times C's. Insufficient data.</li>
</ul>

<h2 id="sources">16. Sources</h2>
<ul>
<li><a href="results/membench-jibin-007/results/bootC/">results/membench-jibin-007/results/bootC/</a> (boot C, commit b79dffa, 2026-11-05), <a href="results/membench-jibin-008/results/bootD/">008/results/bootD/</a> (boot D, commit ed6056a) and <a href="results/membench-jibin-010/results/bootE/">010/results/bootE/</a> (boot E, commit b79dffa, SCP 0.48.0-nopcie-l3.1): sections 12 to 15, read by the same code; the mapping lines from each run's dmesg.txt; <a href="results/membench-jibin-007/README.md">Jesse's boot C</a>, <a href="results/membench-jibin-008/README.md">boot D</a> and <a href="results/membench-jibin-010/README.md">boot E</a> READMEs: the platforms, the SCP rebuild, the L3 power readings, the contiguous mappings.</li>
<li><a href="results/round4-checks/">results/round4-checks/</a>: the independent check of boots A to E (verify.py, fits_ocm.py and their outputs), whose numbers this page's code reproduces.</li>
<li><a href="l1_reader.py">l1_reader.py</a>: the reader and fit for the G8 rows (follow-up-run-plan.md section 12).</li>
<li><a href="results/membench-jibin-006/results/bootB/">results/membench-jibin-006/results/bootB/</a> (run 4 boot B, commit 7921962, 2026-11-04): section 11's numbers, read by the same code; <a href="results/membench-jibin-006/README.md">Jesse's boot B README</a>: the prefetcher hook and its readbacks, the L3 power reading, boot B against boot A.</li>
<li>asimov-scp-firmware, product/asimov/module/asimov_system/src/mod_asimov_system.c at 9ef7952: the cluster operating-mode staging for cluster 0 and its follow-up note (read from GitHub on 2026-11-04).</li>
<li><a href="results/membench-jibin-005/results/bootA/">results/membench-jibin-005/results/bootA/</a> (run 4 boot A, commit e8e4580, 2026-11-04): every number on this page is read from its CSV files, log.txt and sysinfo.txt by <a href="gen_run4.py">gen_run4.py</a>; the mapping alignments from <a href="results/membench-jibin-005/dmesg.txt">dmesg.txt</a>.</li>
<li><a href="results/membench-jibin-005/README.md">Jesse's run 4 README</a>: the run, the platform, the mapping attributes, the chip time.</li>
<li><a href="results/membench-jibin-004/">results/membench-jibin-004/</a> and <a href="results/membench-jibin-002/">002</a> through <a href="gen_run3.py">gen_run3.py</a>: the run 3 and run 2 rows beside boot A's.</li>
<li><a href="follow-up-run-plan.md">follow-up-run-plan.md</a>: the goals, criteria and hypotheses (sections 2, 5 and 10); <a href="asimov-c1nano-perf.html">asimov-c1nano-perf.html</a> and <a href="asimov-cme-perf.html">asimov-cme-perf.html</a>: the full core and CME pages (run 4 boot E, with run 3 beside it), which this page follows.</li>
<li>Arm C1-Nano TRM (107753) and C1-SME2 TRM (107831), event lists: the scope of each counter event quoted above.</li>
</ul>
"""
    toc = [("words", "1. Words used here"), ("run", "2. The run and the platform"),
           ("tables", "3. Summary tables", [("t31", "3.1 Do the new events count?"), ("t32", "3.2 Latency by footprint with the prefetch columns"), ("t33", "3.3 OCM latency by cell and shape"), ("t34", "3.4 L2 refills by cause"), ("t35", "3.5 Translation activity"), ("t36", "3.6 The route rows"), ("t37", "3.7 Latency against hop counts"), ("t38", "3.8 The write-cost check"), ("t39", "3.9 Boot A against run 3")]),
           ("f-levels", "4. Latency by footprint"), ("f-seq", "5. Sequential against random"), ("f-ocm", "6. OCM latency by cell and shape"), ("f-tlb", "7. Translation activity"), ("f-route", "8. The route rows"), ("f-write", "9. The write-cost check"), ("hyp", "10. Hypotheses"), ("bootb", "11. Boot B", [("t111", "11.1 The L3 holds no data"), ("t112", "11.2 Chases with the prefetchers off"), ("t113", "11.3 OCM cells A against B"), ("t114", "11.4 Lines in flight (H7)"), ("t115", "11.5 Hypotheses on the pair")]), ("five", "12. The five boots side by side"), ("hint", "13. Boots C and D: 64 KiB translations", [("t131", "13.1 The TLB rates fell"), ("t132", "13.2 The OCM cells, and H4"), ("t133", "13.3 The walk rows")]), ("boote", "14. Boot E: the L3 turned on", [("t141", "14.1 The hit set"), ("t142", "14.2 Latency by footprint, C against E"), ("t143", "14.3 The one-core read (G7)"), ("t144", "14.4 The OCM rows on boot E")]), ("g8", "15. The L1 bandwidth rows (G8)"), ("sources", "16. Sources")]
    return page("Asimov C1-Nano Memory Performance, run 4 boots A to E", f"Prefetch, TLB and crosspoint counters on the chase rows of run 3: run membench-jibin-005 (cache-mem-perf e8e4580) on the GA13 Palladium, 2026-11-04, beside run 3 (004) and run 2 (002); boot B (006, the data prefetchers off) in section 11; boots C and D (007, 008, the OCM in 64 KiB translations) in section 13; boot E (010, the L3 on) in sections 14 and 15. Generated by gen_run4.py from the CSV files.", toc, body)

# ======================================================================= page 2: the CME
def cme_page():
    t1 = table(["Footprint", "Chase", "Boot A ns", "Run 3 ns", "Boot A vs run 3", "CME cycles", "Inner (0x327D)", "Outer (0x327E)", "Demand read (0x3280)", "Hardware prefetch (0x32B2)", "Write (0x3281)", "(rd + hwprf) minus (inner + outer)"],
               [[kib(d["size"]), d["kind"], fmt(d["ns"], 3), fmt(d["ns3"], 3), pct(d["ns"], d["ns3"]) if d["ns3"] else "-", fmt(d["e"]["cme_cycles"], 2), fmt(d["e"]["cme_l1d_refill_inner"], 3), fmt(d["e"]["cme_l1d_refill_outer"], 3), fmt(d["e"]["cme_l1d_refill_rd"], 3), fmt(d["e"]["cme_l1d_refill_hwprf"], 3), fmt(d["e"]["cme_l1d_refill_wr"], 3),
                 f"{d['e']['cme_l1d_refill_rd'] + d['e']['cme_l1d_refill_hwprf'] - d['e']['cme_l1d_refill_inner'] - d['e']['cme_l1d_refill_outer']:+.3f}"] for d in CLV],
               "CPU 2 in streaming mode, ns per load of the best pass with that pass's counters per load [cme-latency-dram-small.csv, cme-latency-dram-large.csv, cme-latency-dram-flushed.csv, cme-latency-dram-seq.csv]. The last column is the consistency check of criterion G-b for this load-only kernel.")
    t2 = table(["Region", "Sparse", "Dense", "Vary", "Run 3 sparse", "Sparse: demand read / prefetch", "Dense: demand read / prefetch", "Vary: demand read / prefetch"],
               [[f"OCM{r} ({dist(2, NODE_OF_REGION[r])} xp)"] + [f"{fmt(COCM[r][s]['best'], 2)} <span class='d'>(med {fmt(COCM[r][s]['median'], 2)})</span>" for s in ("sparse", "dense", "vary")] + [fmt(R3_COCM[r], 2)]
                + [f"{COCM[r][s]['emean']['cme_l1d_refill_rd']:.2f} / {COCM[r][s]['emean']['cme_l1d_refill_hwprf']:.2f}" for s in ("sparse", "dense", "vary")] for r in range(5)]
               + [["all five"] + [f"{fmt(CALL5[s]['best'], 2)} <span class='d'>(med {fmt(CALL5[s]['median'], 2)})</span>" for s in ("sparse", "dense")] + ["-", fmt(g.CALL5S["best"], 2)] + [f"{CALL5[s]['emean']['cme_l1d_refill_rd']:.2f} / {CALL5[s]['emean']['cme_l1d_refill_hwprf']:.2f}" for s in ("sparse", "dense")] + ["-"]],
               "ns per load, best pass (median in brackets), CPU 2 through the CME; refills per load are means over the timed passes [cme-latency-ocm-region*{,-dense,-vary}.csv, cme-latency-ocm-all5{,-dense}.csv].")
    t9 = table(["File", "Row", "Boot A ns", "Run 3 ns", "Boot A vs run 3"], [[d["file"], f"{kib(d['size'])} {d['mode'].replace('-best', '')}", fmt(d["run4"], 3), fmt(d["run3"], 3), f"{d['pct']:+.2f} %"] for d in sorted([d for d in REPEAT_SAME if d["file"].startswith("cme-")], key=lambda d: -abs(d["pct"]))[:8]],
               f"The 8 CME rows that moved most between boot A and run 3 among the {sum(1 for d in REPEAT_SAME if d['file'].startswith('cme-'))} shared by file name and footprint.")
    # boot B tables (section 8)
    tc1 = table(["Footprint", "Chase", "Boot A ns", "Boot B ns", "Boot B against A", "Boot B demand-read refills per load"],
                [[kib(s), k, fmt(a, 3), fmt(b, 3), pct(b, a), f"{next(d['emean']['cme_l1d_refill_rd'] for d in B['CLV'] if d['size'] == s and d['kind'] == k):.3f}"] for s, k, a, b in AB_CLV],
                "CPU 2 in streaming mode, best rep or best pass of each row on each boot; the refills are the mean over that row's reps or passes [cme-latency-dram-*.csv of 005 and 006].")
    tc2 = table(["Region", "Sparse A", "Sparse B", "Dense A", "Dense B", "Vary A", "Vary B"],
                [[f"OCM{r} ({dist(2, NODE_OF_REGION[r])} xp)"] + [fmt(COCM[r][s]["best"], 2) if boot == "A" else fmt(B["COCM"][r][s]["best"], 2) for s in ("sparse", "dense", "vary") for boot in ("A", "B")] for r in range(5)]
                + [["all five"] + [fmt(CALL5[s]["best"], 2) if boot == "A" else fmt(B["CALL5"][s]["best"], 2) for s in ("sparse", "dense") for boot in ("A", "B")] + ["-", "-"]],
                "ns per hop, best pass of each row on each boot [cme-latency-ocm-*.csv of 005 and 006].")
    at8 = [d for d in CLV if d["size"] == 8192 and d["kind"] == "repeat"][0]["emean"]; at64 = [d for d in CLV if d["size"] == 65536 and d["kind"] == "repeat"][0]["emean"]; at32 = [d for d in CLV if d["size"] == 32768 and d["kind"] == "repeat"][0]["emean"]
    at4_ns = [d for d in CLV if d["size"] == 4096 and d["kind"] == "repeat"][0]["ns"]
    pf_big = [d["emean"]["cme_l1d_refill_hwprf"] for d in CLV if d["kind"] == "repeat" and d["size"] >= 24576]
    cme_dense_pf = [COCM[r]["dense"]["emean"]["cme_l1d_refill_hwprf"] for r in range(5)]; cme_vary_pf = [COCM[r]["vary"]["emean"]["cme_l1d_refill_hwprf"] for r in range(5)]
    cme_dense_rd = [COCM[r]["dense"]["emean"]["cme_l1d_refill_rd"] for r in range(5)]; cme_vary_rd = [COCM[r]["vary"]["emean"]["cme_l1d_refill_rd"] for r in range(5)]
    tc3 = table(["Footprint", "Boot C ns", "Boot E ns", "E / C", "C: inner", "C: outer", "E: inner", "E: outer"],
                [[kib(s), fmt(c["ns"], 3), fmt(d["ns"], 3), f"{d['ns'] / c['ns']:.3f}", fmt(c["emean"]["cme_l1d_refill_inner"], 2), fmt(c["emean"]["cme_l1d_refill_outer"], 2), fmt(d["emean"]["cme_l1d_refill_inner"], 2), fmt(d["emean"]["cme_l1d_refill_outer"], 2)] for s, c, d in EC_CLV],
                "CPU 2 in streaming mode, best of 3 reps, CME L1 refills per load as the mean over the reps: inner 0x327D, outer 0x327E [cme-latency-dram-small.csv of 007 and 010].")
    tc4 = table(["Row through the CME"] + [f"Boot {x} ns" for x in BOOT_ORDER],
                [[f"OCM{r}, {s}"] + [fmt(BT[x]["COCM"][r][s]["best"], 2) for x in BOOT_ORDER] for s in SHAPES for r in range(5)]
                + [[f"all five, {s}"] + [fmt(BT[x]["CALL5"][s]["best"], 2) for x in BOOT_ORDER] for s in ("dense", "sparse")],
                "Best pass [cme-latency-ocm-*.csv of 005 to 010]. Dense: 4,096 hops a pass; sparse and vary: 64 hops; all five: the five regions as one chain.")
    body = f"""
<div class="short"><p><b>Short version.</b> The CME's refills now have a cause: the demand-read and hardware-prefetch refills add up to the inner plus outer refills within {max(CME_CONSIST_REL) * 100:.1f} % on every chase row, and boot B, with the CME prefetcher off, shows that the climb from 8 KiB on boot A was the prefetcher's: the chase reads {min(d['ns'] for d in B_CME_L1):.2f} to {max(d['ns'] for d in B_CME_L1):.2f} ns from 4 to 64 KiB and steps to {B_CLV_REPEAT[98304]['ns']:.2f} ns at 96 KiB, past the 64 KiB L1 (section 8). With the prefetcher off the CME's sparse OCM chases read {min(B_COCM_PCT['sparse']):+.0f} % to {max(B_COCM_PCT['sparse']):+.0f} % slower and order by mesh distance, and its flushed DRAM chase reads {B['CFLUSHED']['ns']:.1f} ns, {B['CFLUSHED']['ns'] - B['FLUSHED']['ns']:.1f} ns more than the core's on the same boot. Boot E, with the L3 on, moves the CME's refills inside the cluster ({100 * CME_INNER_SHARE['E'][8192]:.0f} % inner at 8 KiB against {100 * CME_INNER_SHARE['C'][8192]:.0f} % on boot C) without a faster chase below 32 KiB, reads {min(EC_CLV_RATIO[s] for s in EC_CLV_RATIO if s >= 49152):.2f} to {max(EC_CLV_RATIO[s] for s in EC_CLV_RATIO if s >= 49152):.2f} times boot C from 48 to 384 KiB, and reads the dense OCM rows at {min(COCM_RATIO[('E', 'A')]['dense']):.2f} to {max(COCM_RATIO[('E', 'A')]['dense']):.2f} times boot A (section 9).</p></div>

<h2 id="words">1. Words used here</h2>
{words(g.WORDS_COMMON[:8] + [w for w in WORDS_RUN4 if w[0] in ("boot A to E", "prefetch-refill events", "TLB events", "CME refill events", "dense, sparse, vary", "sequential chain", "L3 full mode (operating mode 7)", "contiguous hint")] + g.WORDS_CME + g.WORDS_COMMON[9:])}

<h2 id="run">2. The run and the platform</h2>
{PLATFORM_A}
<p>The CME rows ran in phases G3 and G4 from CPU 2 with CPU 3 offline, as in run 3, under the CME event set (table 1 of the words) [log.txt].</p>

<h2 id="tables">3. Summary tables</h2>
<h3 id="t31">3.1 Latency by footprint through the CME, with refills by cause</h3>{t1}
<h3 id="t32">3.2 OCM through the CME by chain shape</h3>{t2}
<h3 id="t33">3.3 Boot A against run 3 on the CME rows</h3>{t9}
<ul>
<li><b>Do the events count? (criterion G-b).</b> 0x3280 (demand read) reads {min(d['e']['cme_l1d_refill_rd'] for d in CME_ROWS):.3f} to {max(d['e']['cme_l1d_refill_rd'] for d in CME_ROWS):.3f} per load across the {len(CME_ROWS)} counted CME rows and rises to {CME_RD_AT[393216]:.3f} on the 384 KiB row, where nearly every load misses the L1. 0x32B2 (hardware prefetch) reads up to {CME_HWPRF_MAX:.1f} per load. 0x3281 (write) reads {CME_WR_MAX:.4f} at most: the kernel has no stores. The consistency check (rd + hwprf against inner + outer) holds within {max(abs(x) for x in CME_CONSIST):.3f} per load on every row ({max(CME_CONSIST_REL) * 100:.1f} % at most where the sum exceeds 0.1).</li>
</ul>

<h2 id="f-lat">4. Latency and refills by footprint</h2>
{fig(f_cme_lat, f"Boot A repeats run 3's CME sweep within {max(abs(d['pct']) for d in REPEAT_SAME if d['file'].startswith('cme-latency-dram')):.2f} % at every footprint.", "ns per load, CPU 2 in streaming mode, repeated rows to 384 KiB, fresh chains from 512 KiB [table 3.1].")}
{fig(f_cme_pf, f"The prefetcher makes {CME_HWPRF_AT[8192]:.1f} refills per load at 8 KiB and {max(CME_HWPRF_AT.values()):.1f} at {kib(max(CME_HWPRF_AT, key=CME_HWPRF_AT.get))}; the demand reads reach {CME_RD_AT[32768]:.2f} per load at 32 KiB, half the L1.", f"CME L1 refills per load by cause, mean over the reps [table 3.1]. The outer refills (from outside the cluster) follow the prefetch count: at 32 KiB, {at32['cme_l1d_refill_outer']:.1f} of the {at32['cme_l1d_refill_rd'] + at32['cme_l1d_refill_hwprf']:.1f} refills per load came from outside the cluster and {at32['cme_l1d_refill_inner']:.1f} from inside it (the DSU's L3). Correlation of the repeated rows' latency with their prefetch refills: {CME_PF_CORR:+.2f}.")}
<ul>
<li><b>Why the CME has no L1 step at 64 KiB.</b> Run 3 saw the CME latency climb from 8 KiB with no step at its 64 KiB L1, and more than one refill per load from 8 KiB, and offered the prefetcher as the hypothesis. Boot A counts it: at 8 KiB the prefetcher fills {at8['cme_l1d_refill_hwprf']:.1f} lines per load, at 32 KiB {at32['cme_l1d_refill_hwprf']:.1f}, at 64 KiB {at64['cme_l1d_refill_hwprf']:.1f} (means over the reps), and the demand reads, which should be near 0 while a chain fits the L1, are {at8['cme_l1d_refill_rd']:.2f}, {at32['cme_l1d_refill_rd']:.2f} and {at64['cme_l1d_refill_rd']:.2f} per load. {hyp(f" The prefetcher's fills evict the chain's own lines from the 64 KiB 4-way L1, so a random chain of 8 KiB and above never stays resident: the latency is set by how many loads miss the L1 (the demand-read count) and by the {min(pf_big):.0f} to {max(pf_big):.0f} prefetch requests per load that queue behind each demand miss from 24 KiB on. With the prefetcher off (boot B) the repeated rows to 64 KiB should read near the 4 KiB time ({at4_ns:.1f} ns) and the demand reads near 0 there.")}</li>
<li><b>On the fresh chains the prefetcher does less.</b> From 512 KiB the prefetch refills fall from {[d for d in CLV if d['size'] == 524288][0]['emean']['cme_l1d_refill_hwprf']:.1f} per load to {[d for d in CLV if d['size'] == 33554432][0]['emean']['cme_l1d_refill_hwprf']:.1f} at 32 MiB while the demand reads sit at {[d for d in CLV if d['size'] == 524288][0]['emean']['cme_l1d_refill_rd']:.2f} to {[d for d in CLV if d['size'] == 33554432][0]['emean']['cme_l1d_refill_rd']:.2f}. {hyp(" A chain walked once gives the prefetcher no repeated pattern to train on, and the larger footprints spread the loads over more pages; what it still fetches is the neighbourhood of each miss.")}</li>
</ul>

<h2 id="f-seq">5. The sequential chain</h2>
{fig(f_seq, f"The CME's sequential chain runs at {CSEQ['ns']:.1f} ns per load, the 4 KiB hit time, against {CFLUSHED['ns']:.1f} ns for the random chain; the core's runs at {SEQ['ns']:.1f} ns.", f"Both chains are 8 MiB and both are flushed before each pass. On the CME's sequential row every refill is a prefetch ({CSEQ['e']['cme_l1d_refill_hwprf']:.3f} per load) and the demand-read refills are {CSEQ['e']['cme_l1d_refill_rd']:.3f}: each line was in the L1 before its load arrived. The core's L1 prefetcher also fetched every line but the load still waited about an L2 hit (core page, section 5).")}

<h2 id="f-ocm">6. OCM through the CME by chain shape</h2>
{fig(f_cme_ocm, f"Through the CME the sparse chain is the fastest of the three ({min(COCM[r]['sparse']['best'] for r in range(5)):.1f} to {max(COCM[r]['sparse']['best'] for r in range(5)):.1f} ns), the dense chain {min(CME_DENSE_MINUS_SPARSE):+.1f} to {max(CME_DENSE_MINUS_SPARSE):+.1f} ns slower and the vary chain {min(CME_VARY_MINUS_SPARSE):+.1f} to {max(CME_VARY_MINUS_SPARSE):+.1f} ns slower, the reverse of the core's order.", "Best pass per region, ns per load, CPU 2 through the CME [table 3.2]; run 3's sparse rows beside them.")}
{fig(f_cme_split, f"On the sparse chain the CME takes {min(CME_SPARSE_RD):.2f} to {max(CME_SPARSE_RD):.2f} demand-read refills per hop (so {100 - 100 * max(CME_SPARSE_RD):.0f} % or more of the hops hit the L1) and {min(CME_SPARSE_PF):.2f} to {max(CME_SPARSE_PF):.2f} prefetch refills; the dense chain {min(COCM[r]['dense']['emean']['cme_l1d_refill_hwprf'] for r in range(5)):.2f} to {max(COCM[r]['dense']['emean']['cme_l1d_refill_hwprf'] for r in range(5)):.2f} prefetch refills.", "CME L1 refills per load by cause, mean over the timed passes and the five regions [table 3.2].")}
<ul>
<li><b>The order of the three shapes.</b> On the core the dense chain is fastest and the sparse slowest (core page, section 6); through the CME the sparse chain is fastest. {hyp(f" Through the CME a sparse hop's prefetches ({min(CME_SPARSE_PF):.2f} to {max(CME_SPARSE_PF):.2f} lines per hop) land on the next member often enough to make {100 - 100 * max(CME_SPARSE_RD):.0f} to {100 - 100 * min(CME_SPARSE_RD):.0f} % of the hops L1 hits, while the dense chain's {min(cme_dense_pf):.1f} to {max(cme_dense_pf):.1f} prefetches per hop are mostly neighbours the random walk does not visit next ({100 - 100 * max(cme_dense_rd):.0f} to {100 - 100 * min(cme_dense_rd):.0f} % hits); the vary chain draws {min(cme_vary_pf):.1f} to {max(cme_vary_pf):.1f} prefetches per hop and hits on {100 - 100 * max(cme_vary_rd):.0f} to {100 - 100 * min(cme_vary_rd):.0f} % of them. Which prefetcher does this, and why the core's L2 prefetcher helps the sparse chain less, is not counted here.")} {gap(" A per-hop hit count (the CME's hit events, if the TRM lists them) would decide it.")}</li>
<li><b>Against run 3.</b> Boot A's sparse rows read {min(100 * (COCM[r]['sparse']['best'] - R3_COCM[r]) / R3_COCM[r] for r in range(5)):+.1f} to {max(100 * (COCM[r]['sparse']['best'] - R3_COCM[r]) / R3_COCM[r] for r in range(5)):+.1f} % of run 3's by best pass (7 passes each; the passes of one row spread by up to {max(COCM[r]['sparse']['ns_rng'][1] - COCM[r]['sparse']['ns_rng'][0] for r in range(5)):.1f} ns).</li>
</ul>

<h2 id="open">7. What is settled, what is open</h2>
<p>Boot A alone. Section 8 says what boot B settles.</p>
<ul>
<li>{ok(" The three CME refill-cause events count and are consistent with run 3's two (criterion G-b).")}</li>
<li>{hyp(" The CME prefetcher's fills evict a random chain from the 64 KiB L1 from 8 KiB on, which is why the CME has no L1 step; boot B (prefetcher off) decides it. The TRM's PF_DISABLE bit (IMP_CMECFG_EL1 bit 28) is the switch.")}</li>
<li>{gap(" The CME L1 hit latency and the DSU L3 latency through the CME as separate numbers: no row on this boot gives a flat region above 4 KiB.")}</li>
<li>Boots B to E have run: section 8 (B) and section 9 (C, D and E).</li>
</ul>

<h2 id="bootb">8. Boot B: the CME prefetcher off</h2>
<p>Boot B turns off the CME's hardware prefetcher (IMP_CMECFG_EL1 bit 28) with the cores' (section 11 of the core page): the prefetch refill event 0x32B2 reads {B['CME_HWPRF_MAX']:.4f} per load on every CME row, the round trip repeats at {B['RT_NS'][0]:.3f} to {B['RT_NS'][1]:.3f} ns, and the demand-read plus prefetch refills still equal inner plus outer within {100 * max(B['CME_CONSIST_REL']):.2f} %.</p>
{fig(f_b_cme, f"With its prefetcher off the CME's chase reads {min(d['ns'] for d in B_CME_L1):.2f} to {max(d['ns'] for d in B_CME_L1):.2f} ns per load from 4 to 64 KiB, within {max(d['ns'] for d in B_CME_L1) - B['RT_NS'][0]:.2f} ns of the register round trip, and steps to {B_CLV_REPEAT[98304]['ns']:.2f} ns at 96 KiB: the 64 KiB L1 that boot A's climb from 8 KiB hid.", f"CPU 2 in streaming mode, best rep or best pass, both boots [cme-latency-dram-small.csv, -large.csv of 005 and 006]. The demand-read refills per load are at most {B_RD_L1_MAX:.3f} up to 64 KiB and at least {B_RD_PAST_MIN:.3f} from 96 KiB on. Hover a dot for the value.")}
{tc1}
<ul>
<li><b>The CME L1 hit hop is the round trip.</b> Up to 64 KiB a chase hop costs {min(d['ns'] for d in B_CME_L1) - B['RT_NS'][0]:.2f} to {max(d['ns'] for d in B_CME_L1) - B['RT_NS'][0]:.2f} ns more than the DUP/LASTB control, a derived number: the load itself adds almost nothing to the core-to-CME-to-core trip when the CME L1 holds the line.</li>
<li><b>Past the CME L1 the next level is the mesh.</b> From 96 KiB the chase reads {B_CLV_REPEAT[98304]['ns']:.2f} to {max(d['ns'] for d in B_CME_PAST):.2f} ns with about one demand refill per load, and the DSU's L3 held no data on any boot (core page, 11.1), so these loads come from the SLC through the mesh; the random 512 KiB to 4 MiB chains read {min(b for s, k, a, b in AB_CLV if k == 'fresh' and s <= 4194304):.1f} to {max(b for s, k, a, b in AB_CLV if k == 'fresh' and s <= 4194304):.1f} ns on boot B against {min(a for s, k, a, b in AB_CLV if k == 'fresh' and s <= 4194304):.1f} to {max(a for s, k, a, b in AB_CLV if k == 'fresh' and s <= 4194304):.1f} on boot A, where the prefetcher's 5 to 7 fills per load slowed the chase.</li>
<li><b>DRAM through the CME.</b> The flushed 8 MiB chain reads {B['CFLUSHED']['ns']:.2f} ns on boot B against {CFLUSHED['ns']:.2f} on boot A, and the sequential one {B['CSEQ']['ns']:.2f} against {CSEQ['ns']:.2f}: on boot A the prefetcher's {CFLUSHED['emean']['cme_l1d_refill_hwprf']:.1f} fills per load on the random flushed chain cut the hop time by {100 * (B['CFLUSHED']['ns'] - CFLUSHED['ns']) / B['CFLUSHED']['ns']:.0f} %, and on boot B every load of both chains is a demand miss to DRAM. The core's flushed chain reads {B['FLUSHED']['ns']:.2f} ns on the same boot, so the CME path adds {B['CFLUSHED']['ns'] - B['FLUSHED']['ns']:.1f} ns to a DRAM load.</li>
</ul>
{fig(f_b_cocm, f"Through the CME, the sparse OCM chases read {min(B_COCM_PCT['sparse']):+.0f} % to {max(B_COCM_PCT['sparse']):+.0f} % slower with the prefetcher off, and {'now order by mesh distance' if B_COCM_ORDERED else 'still do not order by mesh distance'}: {min(B_COCM_1XP):.1f} to {max(B_COCM_1XP):.1f} ns one crosspoint away, {min(B_COCM_3XP):.1f} to {max(B_COCM_3XP):.1f} ns three away.", "Sparse chains (one line per 4 KiB page, 64 hops a pass), best of 7 passes on each boot [cme-latency-ocm-region&lt;r&gt;.csv, cme-latency-ocm-all5.csv of 005 and 006]. On boot A the prefetcher found 0.23 to 0.70 of each hop's lines early (section 6).")}
{tc2}
<p><b>What boot B settles for section 7.</b> The CME L1 side of "CME L1 against DSU L3 hit latency" is answered: an L1 hit hop costs the round trip plus {min(d['ns'] for d in B_CME_L1) - B['RT_NS'][0]:.2f} to {max(d['ns'] for d in B_CME_L1) - B['RT_NS'][0]:.2f} ns, and the climb from 8 KiB on boot A was the prefetcher's (the prefetcher hypothesis of section 7 is supported). On boots A to D the level after the CME L1 is the mesh; boot E, with the L3 on, is section 9.</p>

<h2 id="cde">9. Boots C, D and E through the CME</h2>
<p>Boots C and D (the OCM in 64 KiB contiguous translations) and boot E (the L3 on through a rebuilt SCP) are described in sections 12 to 15 of the core page. Through the CME, C and D change little; E changes where the CME's refills come from.</p>
<h3 id="t91">9.1 Boot E: the CME's refills come from inside the cluster</h3>
{fig(f_e_cme, f"With the L3 on the CME's chase reads {EC_CLV_RATIO[8192]:.3f} times boot C's at 8 KiB and {EC_CLV_RATIO[16384]:.3f} at 16 KiB, then {min(EC_CLV_RATIO[s] for s in EC_CLV_RATIO if s >= 49152):.3f} to {max(EC_CLV_RATIO[s] for s in EC_CLV_RATIO if s >= 49152):.3f} from 48 to 384 KiB; past the SLC the two boots agree within {100 * max(abs(d['ns'] / c['ns'] - 1) for d in BT['E']['CLV'] for c in BT['C']['CLV'] if c['size'] == d['size'] and c['kind'] == d['kind'] == 'fresh' and d['size'] >= 6291456):.1f} %.", "CPU 2 in streaming mode, best rep or best pass, boots C and E [cme-latency-dram-small.csv, -large.csv of 007 and 010]. E and C ran the same commit, build, TF-A and kernel; only the SCP differs on these DRAM rows. Hover a dot for the value.")}
{fig(f_e_cme_io, f"On boot C {100 * min(CME_INNER_SHARE['C'][s] for s in (8192, 16384, 24576, 32768, 49152)):.0f} % to {100 * max(CME_INNER_SHARE['C'][s] for s in (8192, 16384, 24576, 32768, 49152)):.0f} % of the CME's L1 refills at 8 to 48 KiB come from inside the cluster; on boot E {100 * CME_INNER_SHARE['E'][8192]:.0f} % at 8 KiB, {100 * CME_INNER_SHARE['E'][16384]:.0f} % at 16 KiB, {100 * CME_INNER_SHARE['E'][32768]:.0f} % at 32 KiB and {100 * CME_INNER_SHARE['E'][65536]:.0f} % at 64 KiB.", "CME L1 refills per load, mean over the reps, split by the two run 3 events: 0x327D (inner, from the DSU's L3 or the other core's caches) and 0x327E (outer, from the SLC, OCM or DRAM) [cme-latency-dram-small.csv of 007 and 010].")}
{tc3}
<ul>
<li><b>Inner refills.</b> With the L3 holding data, the lines the CME's prefetcher evicts from the 64 KiB L1 come back from the L3 instead of from the SLC across the mesh: at 8 KiB E counts {next(d['emean']['cme_l1d_refill_inner'] for d in BT['E']['CLV'] if d['kind'] == 'repeat' and d['size'] == 8192):.2f} inner and {next(d['emean']['cme_l1d_refill_outer'] for d in BT['E']['CLV'] if d['kind'] == 'repeat' and d['size'] == 8192):.2f} outer refills per load, C {next(d['emean']['cme_l1d_refill_inner'] for d in BT['C']['CLV'] if d['kind'] == 'repeat' and d['size'] == 8192):.2f} and {next(d['emean']['cme_l1d_refill_outer'] for d in BT['C']['CLV'] if d['kind'] == 'repeat' and d['size'] == 8192):.2f}. On boot A, inner refills were read as the other core's caches or nothing (section 4); on E they are L3 hits.</li>
<li><b>The chase is not faster below 32 KiB.</b> E reads {EC_CLV_RATIO[8192]:.3f} times C at 8 KiB and {EC_CLV_RATIO[16384]:.3f} at 16 KiB, with more refills in all ({sum(next(d['emean'][k] for d in BT['E']['CLV'] if d['kind'] == 'repeat' and d['size'] == 16384) for k in ('cme_l1d_refill_inner', 'cme_l1d_refill_outer')):.1f} against {sum(next(d['emean'][k] for d in BT['C']['CLV'] if d['kind'] == 'repeat' and d['size'] == 16384) for k in ('cme_l1d_refill_inner', 'cme_l1d_refill_outer')):.1f} per load at 16 KiB, nearly all the prefetcher's on both boots); from 48 KiB on it reads {min(EC_CLV_RATIO[s] for s in EC_CLV_RATIO if s >= 49152):.3f} to {max(EC_CLV_RATIO[s] for s in EC_CLV_RATIO if s >= 49152):.3f} times C. The CME prefetcher's fills set the chase time at these footprints on both boots, so the L3 hit latency through the CME as a single number is Insufficient data; a boot with the CME prefetcher off and the L3 on (not run) would give it.</li>
<li><b>Past the SLC nothing moved:</b> the flushed 8 MiB chain reads {BT['E']['CFLUSHED']['ns']:.2f} ns on E against {BT['C']['CFLUSHED']['ns']:.2f} on C, and the sequential chain {BT['E']['CSEQ']['ns']:.3f} ns on A, C and E alike.</li>
</ul>
<h3 id="t92">9.2 OCM through the CME on the five boots</h3>
{fig(f_e_cocm, f"Through the CME the sparse OCM chases read {min(COCM_RATIO[('D', 'B')]['sparse']):.3f} to {max(COCM_RATIO[('D', 'B')]['sparse']):.3f} times boot B's on boot D (the 64 KiB translations alone) and {min(COCM_RATIO[('E', 'A')]['sparse']):.2f} to {max(COCM_RATIO[('E', 'A')]['sparse']):.2f} times boot A's on boot E (the L3 on).", "Sparse chains (one line per 4 KiB page, 64 hops a pass), best of 7 passes, every boot [cme-latency-ocm-region&lt;r&gt;.csv, cme-latency-ocm-all5.csv of 005 to 010]. On the prefetcher-off boots (B, D) every hop is a demand read; on the others the CME prefetcher finds part of each hop's lines early.")}
{tc4}
<ul>
<li><b>The 64 KiB translations change little through the CME:</b> D against B reads {min(COCM_RATIO[('D', 'B')]['sparse']):.3f} to {max(COCM_RATIO[('D', 'B')]['sparse']):.3f} on the sparse rows, {min(COCM_RATIO[('D', 'B')]['vary']):.3f} to {max(COCM_RATIO[('D', 'B')]['vary']):.3f} on the vary rows and {min(COCM_RATIO[('D', 'B')]['dense']):.3f} to {max(COCM_RATIO[('D', 'B')]['dense']):.3f} on the dense rows; C against A {min(COCM_RATIO[('C', 'A')]['sparse']):.3f} to {max(COCM_RATIO[('C', 'A')]['sparse']):.3f} sparse and {min(COCM_RATIO[('C', 'A')]['dense']):.3f} to {max(COCM_RATIO[('C', 'A')]['dense']):.3f} dense. The CME keeps its own TLB [C1-SME2 TRM 107831].</li>
<li><b>The L3 on, E against A:</b> dense {min(COCM_RATIO[('E', 'A')]['dense']):.2f} to {max(COCM_RATIO[('E', 'A')]['dense']):.2f}, sparse {min(COCM_RATIO[('E', 'A')]['sparse']):.2f} to {max(COCM_RATIO[('E', 'A')]['sparse']):.2f}, vary {min(COCM_RATIO[('E', 'A')]['vary']):.2f} to {max(COCM_RATIO[('E', 'A')]['vary']):.2f}. E's dense rows count {min(E_COCM_OUTER['dense']):.2f} to {max(E_COCM_OUTER['dense']):.2f} outer refills per hop against C's {min(C_COCM_OUTER['dense']):.2f} to {max(C_COCM_OUTER['dense']):.2f}: part of the prefetcher's fills now come from the L3. The all-five dense row reads {BT['E']['CALL5']['dense']['best']:.2f} ns on E against {CALL5['dense']['best']:.2f} on A and {BT['C']['CALL5']['dense']['best']:.2f} on C, with {BT['E']['CALL5']['dense']['emean']['cme_l1d_refill_outer']:.2f} outer refills per hop (A {CALL5['dense']['emean']['cme_l1d_refill_outer']:.2f}).</li>
</ul>

<h2 id="sources">10. Sources</h2>
<ul>
<li><a href="results/membench-jibin-007/results/bootC/">results/membench-jibin-007/results/bootC/</a>, <a href="results/membench-jibin-008/results/bootD/">008/results/bootD/</a> and <a href="results/membench-jibin-010/results/bootE/">010/results/bootE/</a> (boots C, D and E, 2026-11-05): section 9's numbers; <a href="results/membench-jibin-010/README.md">Jesse's boot E README</a>: the SCP rebuild and the L3 power reading.</li>
<li><a href="results/membench-jibin-006/results/bootB/">results/membench-jibin-006/results/bootB/</a> (run 4 boot B, commit 7921962, 2026-11-04, the prefetchers off): section 8's numbers; <a href="results/membench-jibin-006/README.md">Jesse's boot B README</a>: the readbacks, the L3 power reading, boot B against boot A.</li>
<li><a href="results/membench-jibin-005/results/bootA/">results/membench-jibin-005/results/bootA/</a> (run 4 boot A, commit e8e4580, 2026-11-04): every number on this page is read from its cme-latency-*.csv files by <a href="gen_run4.py">gen_run4.py</a>; the core rows quoted are the same boot's.</li>
<li><a href="results/membench-jibin-005/README.md">Jesse's run 4 README</a>: the run and the platform.</li>
<li><a href="results/membench-jibin-004/">results/membench-jibin-004/</a> through <a href="gen_run3.py">gen_run3.py</a>: the run 3 rows beside boot A's; <a href="asimov-cme-perf.html">asimov-cme-perf.html</a>: the full CME page (run 4 boot E, with run 3 beside it).</li>
<li><a href="follow-up-run-plan.md">follow-up-run-plan.md</a> sections 2 and 5: criterion G-b and the consistency check; <a href="asimov-c1nano-run4.html">asimov-c1nano-run4.html</a>: the companion page for the core.</li>
<li>Arm C1-SME2 TRM (107831), event list: 0x3280, 0x32B2, 0x3281 as quoted in the words.</li>
</ul>
"""
    toc = [("words", "1. Words used here"), ("run", "2. The run and the platform"), ("tables", "3. Summary tables", [("t31", "3.1 Latency with refills by cause"), ("t32", "3.2 OCM by chain shape"), ("t33", "3.3 Boot A against run 3")]),
           ("f-lat", "4. Latency and refills by footprint"), ("f-seq", "5. The sequential chain"), ("f-ocm", "6. OCM by chain shape"), ("open", "7. Settled and open"), ("bootb", "8. Boot B: the CME prefetcher off"), ("cde", "9. Boots C, D and E", [("t91", "9.1 Boot E: refills from inside the cluster"), ("t92", "9.2 OCM through the CME on the five boots")]), ("sources", "10. Sources")]
    return page("Asimov CME Memory Performance, run 4 boots A to E", "The CME's L1 refills by cause (demand read, hardware prefetch, write) on the chase rows of run 3: run membench-jibin-005 (cache-mem-perf e8e4580) on the GA13 Palladium, 2026-11-04, beside run 3 (004); boot B (006, the CME prefetcher off) in section 8; boots C, D (007, 008, the OCM in 64 KiB translations) and E (010, the L3 on) in section 9. Generated by gen_run4.py from the CSV files.", toc, body)

def dehop(html):
    """the pages without the word "hop" (Jibin, 2026-11-05): a load of a chain is a load, a crosspoint-to-crosspoint
    move on the mesh is a step; applied to the finished page so the shared gen_run3 glossary is covered too"""
    for a, b in (("Latency against hop counts", "Latency against step counts"), ("the assumed hop counts", "the assumed step counts"),
                 ("|dx| + |dy| hops", "|dx| + |dy| steps"), ("an X hop costs more than a Y hop", "an X step costs more than a Y step"),
                 ("an X hop against a Y hop", "an X step against a Y step"), ("Taking the L2 hop at", "Taking the L2 time at"),
                 ("the outside hop at", "the outside time at"), ("The CME L1 hit hop is the round trip", "The CME L1 hit load is the round trip"),
                 ("an L1 hit hop costs the round trip", "an L1 hit load costs the round trip"), ("one such hop per call", "one such round trip per call"),
                 ("chase, hop", "chase"), (" One load of the chain is one hop.", ""), ("per-hop", "per-load"),
                 ("sparse hop's", "sparse-chain load's"), ("A sparse hop takes", "A sparse-chain load takes"), ("a dense hop", "a dense-chain load"),
                 ("the sparse hops", "the sparse-chain loads"), ("per sparse hop", "per sparse-chain load"), ("each hop's", "each load's"),
                 ("a chase hop", "a chase load"), ("the hop time", "the load time")):
        html = html.replace(a, b)
    html = re.sub(r"\bhops\b", "loads", html); html = re.sub(r"\bhop\b", "load", html)
    assert not re.search(r"\bhops?\b", html)
    return html

if __name__ == "__main__":
    __import__("json").dump(FACTS, open(A + "/run4-bootA-facts.json", "w"), indent=1)
    open(OUT_CORE, "w").write(dehop(core_page()))
    open(OUT_CME, "w").write(dehop(cme_page()))
    print("wrote", OUT_CORE, OUT_CME, "and run4-bootA-facts.json (with bootB to bootE blocks)")
