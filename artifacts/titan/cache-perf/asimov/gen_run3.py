#!/usr/bin/env python3
"""Build two pages from run 3 (membench-jibin-004) with run 2 (membench-jibin-002) beside it:

  asimov-c1nano-perf.html   the C1-Nano core: cache, mesh, OCM and DRAM latency and bandwidth
  asimov-cme-perf.html      the CME (the cluster's C1-SME2 unit): the same loads and stores in streaming mode

Every number on both pages is read from results/membench-jibin-00{2,4}/results/*/ by this script.
The only typed-in numbers are platform facts quoted from Jesse's README files (cited where used)
and the asimov-bench reference values quoted in est_chip_time.py and CME-plan.md (cited as such).
"""
import glob, os, re, json, statistics, collections

A = os.path.dirname(os.path.abspath(__file__))
R2 = glob.glob(A + "/results/membench-jibin-002/results/*/")[0]
R4 = glob.glob(A + "/results/membench-jibin-004/results/*/")[0]
OUT_CORE = A + "/asimov-c1nano-perf.html"
OUT_CME = A + "/asimov-cme-perf.html"
try: R4A = json.load(open(A + "/run4-bootA-facts.json"))   # run 4 boot A facts written by gen_run4.py; None until that run is read, and the pages then regenerate as before
except FileNotFoundError: R4A = None
R4B = R4A.get("bootB") if R4A else None   # run 4 boot B (prefetchers off): its hit counters show the DSU L3 of CPUs 2 to 9 held no data on this platform
R4E = R4A.get("bootE") if R4A else None   # run 4 boot E: the L3 turned on by a rebuilt SCP
L3_SF = bool(R4B and R4B["l3_hit_max"] < 1e-4)   # the L3 was in snoop-filter-only mode on runs 1 to 3: there is no L3 level in these pages
L3_TAG = " (no data)" if L3_SF else ""   # the L3 mark on the charts

# ---------------------------------------------------------------- readers
def lat_rows(path):
    """rows of a latency CSV. Core rows: c1,c2,c3 = L1D, L2D, L3D-read refills per load.
    CME rows (cme=1 in the header): c1 = CME cycles per load, c2 = inner refills, c3 = outer refills."""
    out, meta, size, header = [], {}, None, ""
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("# latency:"):
            meta = dict(re.findall(r"(\w+)=(\S+)", line)); continue
        if line.startswith("# size="):
            size = dict(re.findall(r"(\w+)=(\S+)", line)); continue
        if line.startswith("mem,"): header = line; continue
        if line.startswith("#"): continue
        f = line.split(",")
        d = dict(mem=f[0], size=int(f[1]), mode=f[2], rep=f[3], loads=f[4], ns=float(f[5]), cme=meta.get("cme") == "1",
                 backing=(size or {}).get("backing"), lines=int((size or {}).get("lines", 0)))
        ncol = header.count(",") + 1 if header else 6
        base = 7 if "ns_per_load_span" in header else 6   # run 6: a --cme row carries the in-span ns per load as column 7, before the counters
        if f[3] == "-":        # a best row: timing only (mem,size,mode,-,-,ns)
            assert len(f) == 6, f"{path}: best row has {len(f)} fields: {line}"
        else:                  # a measured row has every header column; a counter is a number or "-" (refused or invalid)
            assert len(f) == ncol, f"{path}: row has {len(f)} fields, header {ncol}: {line}"
            num = lambda v: None if v == "-" else float(v)
            if base == 7: d["span"] = num(f[6])
            if ncol > base:   # run 2: cyc + 3 counters; run 3: + perf_cov; run 4: cyc + 6 counters + perf_cov
                has_cov = "perf_cov" in header; ctr = f[base + 1:-1] if has_cov else f[base + 1:]
                d.update(cyc=num(f[base]), cov=num(f[-1]) if has_cov else None, **{f"c{i + 1}": num(v) for i, v in enumerate(ctr)})
        out.append(d)
    return out

def bw_rows(path):
    out, meta = [], {}
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("# bandwidth"):
            meta = dict(re.findall(r"(\w+)=(\S+)", line)); continue
        if line.startswith("#") or line.startswith("mem,"): continue
        f = line.split(",")
        out.append(dict(mem=f[0], kernel=f[1], threads=int(f[2]), bpt=int(f[3]), rep=f[4],
                        elapsed=None if f[6] == "-" else float(f[6]), agg=float(f[7]), tmin=f[8], tmax=f[9],
                        passes=int(meta["passes"]), flush=int(meta["flush_before"]), cme=meta.get("cme") == "1"))
    return out

def cmn_rows(path):
    """label -> dict(node={id: requests}, mc=, miss=, child=, helper=)"""
    out = collections.defaultdict(lambda: dict(node={}))
    for line in open(path):
        if line.startswith("#") or line.startswith("label,"): continue
        lab, ev, node, cnt, en, run, sc = line.rstrip("\n").split(",")
        assert en == run, (lab, ev)   # never multiplexed
        e = out[lab]
        if ev == "hns_pocq_reqs_recvd_all": e["node"][int(node)] = int(cnt)
        elif ev == "hns_mc_reqs_local_all": e["mc"] = int(cnt)
        elif ev == "hns_cache_miss_all": e["miss"] = int(cnt)
        elif ev == "child_elapsed_ns": e["child"] = int(cnt)
        elif ev == "helper_elapsed_ns": e["helper"] = int(cnt)
    return out

def kib(n): return f"{n // 1024} KiB" if n < 1 << 20 else f"{n / (1 << 20):g} MiB"

def best(rows, **kw):
    for d in rows:
        key = "mode" if "mode" in d else "rep"
        if d[key].endswith("best") and all(d[k] == v for k, v in kw.items()): return d
    raise KeyError((kw, rows[0]))

def passes(rows, size):
    return [d for d in rows if d["size"] == size and not d["mode"].endswith("best") and "roundtrip" not in d["mode"] and "call" not in d["mode"]]

def best_pass(rows, size):
    b = best(rows, size=size)["ns"]
    return [d for d in passes(rows, size) if abs(d["ns"] - b) < 1e-9][0]

# ---------------------------------------------------------------- topology (node ids decoded X[8:6] Y[5:3]; checked against the debugfs map)
NODES = {88: (1, 3, 0), 160: (2, 4, 1), 216: (3, 3, 2), 288: (4, 4, 3), 344: (5, 3, 4)}   # id -> (x, y, OCM region)
DSUS = {1: (2, 3, (2, 3)), 2: (3, 2, (4, 5)), 3: (4, 3, (6, 7)), 4: (5, 2, (8, 9))}         # dsu -> (x, y, cpus)
DSU0 = (1, 2)
NODE_OF_REGION = {r: n for n, (x, y, r) in NODES.items()}
SLC_BYTES = 5 * (1 << 20) * 12 // 16   # 3.75 MiB: five 1 MiB home nodes, 4 of 16 ways locked as OCM
CPU_DSU = {2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 4, 9: 4}
def dist(cpu, node):
    dx, dy = DSUS[CPU_DSU[cpu]][0] - NODES[node][0], DSUS[CPU_DSU[cpu]][1] - NODES[node][1]
    return abs(dx) + abs(dy)
sysinfo = open(R4 + "sysinfo.txt").read()
mapsec = sysinfo[sysinfo.index("## arm-cmn mesh map"):]
map_lines = mapsec.splitlines()
def cell(x, y, port):
    for i, l in enumerate(map_lines):
        if re.match(rf"^{y} +\| XP", l):
            row = map_lines[i + 3 + 3 * port]
            return row[6 + 9 * x: 6 + 9 * x + 8].strip()
    return None
for n, (x, y, r) in NODES.items(): assert cell(x, y, 0) == "HN-S", (n, cell(x, y, 0))
for d, (x, y, c) in DSUS.items(): assert cell(x, y, 0) == "RN-F_E_E", (d, cell(x, y, 0))
assert cell(*DSU0, 0) == "RN-F_E_E"
SBSX = [(x, y) for x in range(6) for y in range(6) if "SBSX" in [cell(x, y, p) for p in (0, 1)]]
assert len(SBSX) == 10
assert sysinfo.count("sme2") == 10   # every CPU lists SME2

# ---------------------------------------------------------------- core latency, run 3 against run 2
def levels_of(R):
    small, large, flushed = (lat_rows(R + f) for f in ("latency-dram-small.csv", "latency-dram-large.csv", "latency-dram-flushed.csv"))
    out = []
    for rows, kind in ((small, "repeat"), (large, "fresh")):
        for d in rows:
            if d["mode"] != "best": continue
            p = best_pass(rows, d["size"])
            out.append(dict(size=d["size"], kind=kind, ns=d["ns"], l1=p["c1"], l2=p["c2"], l3=p["c3"], cov=p["cov"]))
    fb = best(flushed); fp = best_pass(flushed, fb["size"])
    out.append(dict(size=fb["size"], kind="flushed", ns=fb["ns"], l1=fp["c1"], l2=fp["c2"], l3=fp["c3"], cov=fp["cov"]))
    return out
LV4, LV2 = levels_of(R4), levels_of(R2)
for a, b in zip(LV4, LV2): assert (a["size"], a["kind"]) == (b["size"], b["kind"]); a["ns2"] = b["ns"]
def level_name(size, kind):
    if kind == "flushed": return "DRAM (every line flushed)"
    if size <= 24576: return "L1"
    if size <= 32768: return "L1 and L2"
    if size <= 131072: return "L2"
    if size <= 262144: return "L2 and SLC through the mesh (mixed; the L3 held no data)" if L3_SF else "L2, L3 and mesh (mixed)"
    if size <= SLC_BYTES: return "SLC (mesh cache)"
    if size < 16777216: return "SLC and DRAM (mixed)"
    return "DRAM"

# OCM chases: run 3 sparse per region (7 passes of 64 hops), run 3 dense all-five control, run 3 sparse all-five, run 2 dense
OCM, ALL5S, ALL5D, ALL5_2, OCM2, SLC, CTRL = {}, {}, {}, {}, {}, {}, {}
for c in (2, 4, 6, 8):
    OCM[c], OCM2[c] = {}, {}
    for r in range(5):
        rows = lat_rows(f"{R4}latency-ocm-region{r}-cpu{c}.csv")
        assert rows[0]["lines"] == 64 and rows[0]["loads"] == "64"
        ps = passes(rows, 262144)
        OCM[c][r] = dict(best=best(rows)["ns"], median=statistics.median(p["ns"] for p in ps), dist=dist(c, NODE_OF_REGION[r]),
                         passes=[dict(ns=p["ns"], l1=p["c1"], l2=p["c2"], l3=p["c3"], cyc=p["cyc"]) for p in ps])
        rows2 = lat_rows(f"{R2}latency-ocm-region{r}-cpu{c}.csv")
        OCM2[c][r] = dict(best=best(rows2)["ns"], passes=[dict(ns=p["ns"], l2=p["c2"], l3=p["c3"]) for p in passes(rows2, 262144)])
    rows = lat_rows(f"{R4}latency-ocm-all5-cpu{c}.csv"); ps = passes(rows, 1310720)
    ALL5S[c] = dict(best=best(rows)["ns"], median=statistics.median(p["ns"] for p in ps), passes=[p["ns"] for p in ps], l3=[p["c3"] for p in ps], l2=[p["c2"] for p in ps])
    rows = lat_rows(f"{R4}latency-ocm-all5-dense-cpu{c}.csv"); ps = passes(rows, 1310720)
    ALL5D[c] = dict(best=best(rows)["ns"], passes=[p["ns"] for p in ps], l1=[p["c1"] for p in ps], l2=[p["c2"] for p in ps], l3=[p["c3"] for p in ps])
    rows = lat_rows(f"{R2}latency-ocm-all5-cpu{c}.csv"); ps = passes(rows, 1310720)
    ALL5_2[c] = dict(best=best(rows)["ns"], l3=[p["c3"] for p in ps])
    f = "latency-dram-large.csv" if c == 2 else f"latency-dram-slc-cpu{c}.csv"
    SLC[c] = dict(best=best(lat_rows(R4 + f), size=2097152)["ns"], best2=best(lat_rows(R2 + f), size=2097152)["ns"])
    CTRL[c] = dict(best=best(lat_rows(f"{R4}latency-control-cpu{c}.csv"))["ns"], best2=best(lat_rows(f"{R2}latency-control-cpu{c}.csv"))["ns"])
by_dist = collections.defaultdict(list); by_dist2 = collections.defaultdict(list)
for c in OCM:
    for r in OCM[c]:
        by_dist[OCM[c][r]["dist"]].append(OCM[c][r]["best"]); by_dist2[OCM[c][r]["dist"]].append(OCM2[c][r]["best"])
DIST = {k: dict(n=len(v), mean=statistics.mean(v), lo=min(v), hi=max(v), mean2=statistics.mean(by_dist2[k]), lo2=min(by_dist2[k]), hi2=max(by_dist2[k])) for k, v in by_dist.items()}
DIST_PCT = {k: dict(run3=100 * (v["hi"] / v["lo"] - 1), run2=100 * (v["hi2"] / v["lo2"] - 1)) for k, v in DIST.items()}   # widest over narrowest cell at that distance
sparse_cells = [(c, r) for c in OCM for r in OCM[c]]
DIST_CORR = statistics.correlation([OCM[c][r]["best"] for c, r in sparse_cells], [OCM2[c][r]["best"] for c, r in sparse_cells])   # all 20 cells, distance effect included
_dm3 = {k: v["mean"] for k, v in DIST.items()}; _dm2 = {k: v["mean2"] for k, v in DIST.items()}
DIST_RESID_CORR = statistics.correlation([OCM[c][r]["best"] - _dm3[OCM[c][r]["dist"]] for c, r in sparse_cells],
                                         [OCM2[c][r]["best"] - _dm2[OCM[c][r]["dist"]] for c, r in sparse_cells])   # after removing each run's mean at each distance
sparse_minus_dense = [OCM[c][r]["best"] - OCM2[c][r]["best"] for c, r in sparse_cells]
spread = [max(p["ns"] for p in OCM[c][r]["passes"]) - min(p["ns"] for p in OCM[c][r]["passes"]) for c, r in sparse_cells]
best_below_median = [OCM[c][r]["median"] - OCM[c][r]["best"] for c, r in sparse_cells]
_p4k = best_pass(lat_rows(R4 + "latency-dram-small.csv"), 4096)
CORE_GHZ = _p4k["cyc"] / _p4k["ns"]   # core cycles per ns from the 4 KiB repeated row (cycles_per_load / ns_per_load)
ordered_within_cpu = all(all(OCM[c][a]["best"] <= OCM[c][b]["best"] for a in range(5) for b in range(5) if OCM[c][a]["dist"] < OCM[c][b]["dist"]) for c in OCM)
sp_l2 = [p["l2"] for c, r in sparse_cells for p in OCM[c][r]["passes"]]; sp_l3 = [p["l3"] for c, r in sparse_cells for p in OCM[c][r]["passes"]]
d2_l2 = [p["l2"] for c, r in sparse_cells for p in OCM2[c][r]["passes"]]; d2_l3 = [p["l3"] for c, r in sparse_cells for p in OCM2[c][r]["passes"]]
def corr(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5; sy = sum((y - my) ** 2 for y in ys) ** 0.5
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)
# within-row correlation of pass time with L2 and L3 refills (pooled after removing each row's mean)
def within(key):
    xs, ys = [], []
    for c, r in sparse_cells:
        ps = OCM[c][r]["passes"]; mn, mk = statistics.mean(p["ns"] for p in ps), statistics.mean(p[key] for p in ps)
        xs += [p["ns"] - mn for p in ps]; ys += [p[key] - mk for p in ps]
    return corr(xs, ys)
CORR_L2, CORR_L3 = within("l2"), within("l3")
dense_vs_run2 = [ALL5D[c]["best"] - ALL5_2[c]["best"] for c in ALL5D]
sparse_vs_dense_all5 = [ALL5S[c]["best"] - ALL5D[c]["best"] for c in ALL5D]

# ---------------------------------------------------------------- core bandwidth, run 3 against run 2
def bw_best(R, f, **kw): return best(bw_rows(R + f), **kw)["agg"]
def _passes_one(size):   # the pass count of the one-core row of that size, from its header line
    for line in open(R4 + "bandwidth-dram-1core.csv"):
        if line.startswith("# bandwidth") and f"bytes_per_thread={size} " in line: return int(re.search(r"passes=(\d+)", line).group(1))
    raise KeyError(size)
ONE = [dict(size=s, **{k: bw_best(R4, "bandwidth-dram-1core.csv", kernel=k, bpt=s) for k in ("read", "write", "copy")},
            **{k + "2": bw_best(R2, "bandwidth-dram-1core.csv", kernel=k, bpt=s) for k in ("read", "write", "copy")})
       for s in sorted({d["bpt"] for d in bw_rows(R4 + "bandwidth-dram-1core.csv")})]
def multi(f):
    rows4, rows2 = bw_rows(R4 + f), bw_rows(R2 + f)
    def best_rep(d):   # the rep whose aggregate the best row carries, for its per-thread range
        return [r for r in rows4 if r["rep"] != "best" and r["kernel"] == d["kernel"] and r["bpt"] == d["bpt"] and abs(r["agg"] - d["agg"]) < 1e-9][0]
    return [dict(kernel=d["kernel"], threads=d["threads"], size=d["bpt"], run3=d["agg"], run2=best(rows2, kernel=d["kernel"], bpt=d["bpt"])["agg"],
                 tmin=float(best_rep(d)["tmin"]), tmax=float(best_rep(d)["tmax"]))
            for d in rows4 if d["rep"] == "best"]
PAIR, PERDSU, ALL8 = multi("bandwidth-pair.csv"), multi("bandwidth-perdsu.csv"), multi("bandwidth-all8.csv")
PLACE = []
for cpus in ("2-3", "2-4", "2-8", "2-3-4-5", "2-3-8-9", "2-4-6-8"):
    r4, r2 = bw_rows(f"{R4}bandwidth-write-cpus{cpus}.csv"), bw_rows(f"{R2}bandwidth-write-cpus{cpus}.csv")
    b = best(r4); reps = [d for d in r4 if d["rep"] != "best"]
    PLACE.append(dict(cpus=cpus, run3=b["agg"], run2=best(r2)["agg"], dsus=sorted({CPU_DSU[int(c)] for c in cpus.split("-")}),
                      tmin=min(float(d["tmin"]) for d in reps), tmax=max(float(d["tmax"]) for d in reps)))
OCMBW = dict(region=[bw_best(R4, f"bandwidth-ocm-region{r}.csv") for r in range(5)], region2=[bw_best(R2, f"bandwidth-ocm-region{r}.csv") for r in range(5)],
             all5=bw_best(R4, "bandwidth-ocm-all5.csv"), all5_2=bw_best(R2, "bandwidth-ocm-all5.csv"),
             four=bw_best(R4, "bandwidth-ocm-4core.csv"), four2=bw_best(R2, "bandwidth-ocm-4core.csv"),
             write=bw_best(R4, "bandwidth-ocm-write.csv"), write2=bw_best(R2, "bandwidth-ocm-write.csv"))
SPREAD1 = dict(run3=bw_best(R4, "bandwidth-dram-spread.csv"), run2=bw_best(R2, "bandwidth-dram-spread.csv"))

# every best row both runs share, for the run 3 against run 2 table
COMPARE = []
for f in sorted(os.listdir(R4)):
    if not f.endswith(".csv") or f.startswith("cme-") or f == "cmn-counts.csv" or not os.path.exists(R2 + f): continue
    if f.startswith("latency"):
        a, b = lat_rows(R4 + f), lat_rows(R2 + f)
        seen = collections.Counter()
        for d in a:
            if d["mode"] != "best": continue
            k = seen[d["size"]]; seen[d["size"]] += 1   # the k-th best row of this size matches the k-th in run 2 (the two CPU 2 controls share one file)
            m = [e for e in b if e["mode"] == "best" and e["size"] == d["size"]]
            if len(m) > k:
                same_chain = ("sparse" not in open(R4 + f).readline()) or "sparse=0" in open(R4 + f).readline()
                what = f"{kib(d['size'])} chase" + (" (counted)" if "control" in f and k == 0 else " (uncounted)" if "control" in f else "")
                COMPARE.append(dict(file=f, what=what, run3=d["ns"], run2=m[k]["ns"], unit="ns", same=same_chain))
    else:
        a, b = bw_rows(R4 + f), bw_rows(R2 + f)
        for d in a:
            if d["rep"] != "best": continue
            m = [e for e in b if e["rep"] == "best" and e["kernel"] == d["kernel"] and e["bpt"] == d["bpt"] and e["threads"] == d["threads"]]
            if m: COMPARE.append(dict(file=f, what=f"{d['kernel']} {d['threads']}t {kib(d['bpt'])}", run3=d["agg"], run2=m[0]["agg"], unit="GB/s", same=True))
for c in (2, 4, 6, 8):
    COMPARE.append(dict(file=f"latency-ocm-all5-dense-cpu{c}.csv (run 2: latency-ocm-all5-cpu{c}.csv)", what="1.25 MiB dense chase", run3=ALL5D[c]["best"], run2=ALL5_2[c]["best"], unit="ns", same=True))
for d in COMPARE: d["pct"] = 100 * (d["run3"] - d["run2"]) / d["run2"]
LAT_SAME = [d for d in COMPARE if d["unit"] == "ns" and d["same"]]
BW_SAME = [d for d in COMPARE if d["unit"] == "GB/s"]

# ---------------------------------------------------------------- mesh counters
CMN4, CMN2 = cmn_rows(R4 + "cmn-counts.csv"), cmn_rows(R2 + "cmn-counts.csv")
def attribution(cmn, label, region):
    e = cmn[label]; own = e["node"][NODE_OF_REGION[region]]
    others = [v for n, v in e["node"].items() if n != NODE_OF_REGION[region]]
    return dict(own=own, others_mean=statistics.mean(others), others_lo=min(others), others_hi=max(others), ratio=own / statistics.mean(others))
ATTR = {(c, r): attribution(CMN4, f"ocm-region{r}-cpu{c}", r) for c in (2, 4, 6, 8) for r in range(5)}
ATTR2 = {(c, r): attribution(CMN2, f"ocm-region{r}-cpu{c}", r) for c in (2, 4, 6, 8) for r in range(5)}
ATTR_READ = {r: attribution(CMN4, f"ocm-read-region{r}", r) for r in range(5)}
ATTR_READ_CME = {r: attribution(CMN4, f"cme-ocm-read-region{r}", r) for r in range(5)}
ATTR_CME = {r: attribution(CMN4, f"cme-ocm-region{r}-cpu2", r) for r in range(5)}
own_ratio_vs_run2 = [ATTR[k]["own"] / ATTR2[k]["own"] for k in ATTR]
oth_ratio_vs_run2 = [ATTR[k]["others_mean"] / ATTR2[k]["others_mean"] for k in ATTR]
dense_nodes_vs_run2 = [CMN4[f"ocm-all5-dense-cpu{c}"]["node"][n] / CMN2[f"ocm-all5-cpu{c}"]["node"][n] - 1 for c in (2, 4, 6, 8) for n in NODES]
COST = dict(counted=CMN4["control-cpu2"]["helper"], uncounted=CMN4["control-nocount-cpu2"]["helper"],
            child_c=CMN4["control-cpu2"]["child"], child_u=CMN4["control-nocount-cpu2"]["child"],
            counted2=CMN2["control-cpu2"]["helper"], uncounted2=CMN2["control-nocount-cpu2"]["helper"])
BG = [v for c in (2, 4, 6, 8) for v in CMN4[f"control-cpu{c}"]["node"].values()]
FLUSH_SPREAD = sorted(CMN4["cme-dram-flushed-8M-cpu2"]["node"].values())

# ---------------------------------------------------------------- CME rows (CPU 2, CPU 3 offline)
CSMALL, CLARGE, CFLUSH = (lat_rows(R4 + f) for f in ("cme-latency-dram-small.csv", "cme-latency-dram-large.csv", "cme-latency-dram-flushed.csv"))
CORE_BEST = {(d["size"], d["kind"]): d for d in LV4}
CLV = []
for rows, kind in ((CSMALL, "repeat"), (CLARGE, "fresh"), (CFLUSH, "flushed")):
    for d in rows:
        if d["mode"] != "cme-best": continue
        ps = passes(rows, d["size"])
        bp = best_pass(rows, d["size"])
        CLV.append(dict(size=d["size"], kind=kind, ns=d["ns"], core=CORE_BEST[(d["size"], kind)]["ns"], outer_best=bp["c3"], inner_best=bp["c2"],
                        outer=(min(p["c3"] for p in ps), max(p["c3"] for p in ps)), inner=(min(p["c2"] for p in ps), max(p["c2"] for p in ps)),
                        reps=[(p["ns"], p["c3"]) for p in ps], ratio=[p["c1"] / p["cyc"] for p in ps]))
RT = []; CALL = []   # every roundtrip and call rep across the 10 CME latency files
for f in sorted(glob.glob(R4 + "cme-latency-*.csv")):
    for d in lat_rows(f):
        if d["mode"] == "cme-roundtrip": RT.append(d)
        if d["mode"] == "cme-call": CALL.append(d)
RT_NS = (min(d["ns"] for d in RT), max(d["ns"] for d in RT)); RT_CYC = (min(d["c1"] for d in RT), max(d["c1"] for d in RT))
CALL_NS = sorted(d["ns"] for d in CALL)
CME_RATIO = [r for d in CLV for r in d["ratio"]]
assert all(d["cov"] == 1.0 for rows in (CSMALL, CLARGE, CFLUSH) for d in rows if d.get("cov") is not None)
slowest_has_most_outer = sum(1 for d in CLV if d["kind"] == "repeat" and d["size"] <= 131072 and max(d["reps"])[1] == max(r[1] for r in d["reps"]))
n_small = sum(1 for d in CLV if d["kind"] == "repeat" and d["size"] <= 131072)
COCM = {}
for r in range(5):
    rows = lat_rows(f"{R4}cme-latency-ocm-region{r}.csv"); ps = passes(rows, 262144)
    COCM[r] = dict(best=best(rows, size=262144)["ns"], median=statistics.median(p["ns"] for p in ps), passes=[(p["ns"], p["c3"]) for p in ps],
                   outer=(min(p["c3"] for p in ps), max(p["c3"] for p in ps)), dist=dist(2, NODE_OF_REGION[r]))
rows = lat_rows(R4 + "cme-latency-ocm-all5.csv"); ps = passes(rows, 1310720)
CALL5S = dict(best=best(rows, size=1310720)["ns"], median=statistics.median(p["ns"] for p in ps), passes=[(p["ns"], p["c3"]) for p in ps], outer=(min(p["c3"] for p in ps), max(p["c3"] for p in ps)))
rows = lat_rows(R4 + "cme-latency-ocm-all5-dense.csv"); ps = passes(rows, 1310720)
CALL5D = dict(best=best(rows, size=1310720)["ns"], passes=[(p["ns"], p["c3"]) for p in ps], outer=(min(p["c3"] for p in ps), max(p["c3"] for p in ps)))
cme_region_spread = [max(p[0] for p in COCM[r]["passes"]) - min(p[0] for p in COCM[r]["passes"]) for r in COCM]
CBW_ROWS = bw_rows(R4 + "cme-bandwidth-dram-1core.csv")
CBW = [dict(size=s, **{k: best(CBW_ROWS, kernel="cme-" + k, bpt=s)["agg"] for k in ("read", "write", "copy")},
            **{"core_" + k: (bw_best(R4, "bandwidth-dram-1core.csv", kernel=k, bpt=s) if any(d["bpt"] == s for d in bw_rows(R4 + "bandwidth-dram-1core.csv")) else None) for k in ("read", "write", "copy")})
       for s in sorted({d["bpt"] for d in CBW_ROWS if d["kernel"] in ("cme-read", "cme-write", "cme-copy")})]
NARROW = [dict(size=s, ldr16=best(CBW_ROWS, kernel="cme-ldr16", bpt=s)["agg"], str16=best(CBW_ROWS, kernel="cme-str16", bpt=s)["agg"],
               read=best(CBW_ROWS, kernel="cme-read", bpt=s)["agg"], write=best(CBW_ROWS, kernel="cme-write", bpt=s)["agg"])
          for s in sorted({d["bpt"] for d in CBW_ROWS if d["kernel"] == "cme-ldr16"})]
CC = bw_rows(R4 + "cme-bandwidth-call-cost.csv")
def call_bound(kernel):
    reps = [d for d in CC if d["kernel"] == kernel and d["rep"] != "best"]
    return min(d["elapsed"] / d["passes"] * 1e9 for d in reps)   # ns per call, 1 KiB of data and the loop included
CALLB = dict(read=call_bound("cme-read"), write=call_bound("cme-write"))
r16 = [d for d in CBW_ROWS if d["kernel"] == "cme-read" and d["bpt"] == 16384 and d["rep"] != "best"]
PASS16 = min(d["elapsed"] / d["passes"] * 1e9 for d in r16)   # ns per 16 KiB read pass
COCMBW = dict(region=[bw_best(R4, f"cme-bandwidth-ocm-region{r}.csv") for r in range(5)], all5=bw_best(R4, "cme-bandwidth-ocm-all5.csv"), write=bw_best(R4, "cme-bandwidth-ocm-write.csv"),
              region_reps=[[d["agg"] for d in bw_rows(f"{R4}cme-bandwidth-ocm-region{r}.csv") if d["rep"] != "best"] for r in range(5)],
              core_region_reps=[[d["agg"] for d in bw_rows(f"{R4}bandwidth-ocm-region{r}.csv") if d["rep"] != "best"] for r in range(5)])
cme_rep_spread = [100 * (max(v) - min(v)) / max(v) for v in COCMBW["region_reps"]]
core_rep_spread = [100 * (max(v) - min(v)) / max(v) for v in COCMBW["core_region_reps"]]
W32 = best(CBW_ROWS, kernel="cme-write", bpt=33554432)["agg"]
PAIR_W = [p for p in PLACE if p["cpus"] == "2-3"][0]["run3"]
CME_OCM_OWN_RATIO = [ATTR_CME[r]["own"] / ATTR[(2, r)]["own"] for r in range(5)]
CME_READ_OWN_RATIO = [ATTR_READ_CME[r]["own"] / ATTR_READ[r]["own"] for r in range(5)]
# asimov-bench reference values, as quoted in est_chip_time.py and CME-plan.md (not re-measured here)
BENCH = dict(cme_l1=21.56, dsu_l3=26.6, ocm=34.8, read_gbps=34.5, core_l1=2.0, core_l2=6.1)

# ---------------------------------------------------------------- the two runs' command lists
def commands(R):
    out = []
    for line in open(R + "log.txt"):
        if not line.startswith("+ "): continue
        c = re.sub(r"\s*\[uptime.*$", "", line[2:].rstrip("\n"))
        c = re.sub(r"/opt/membench/[^ ]*/", "", c)
        out.append(c)
    return out
CMD2, CMD4 = commands(R2), commands(R4)
CMD4_CACHE = [c for c in CMD4 if "--cme" not in c]
def strip_label(c): return re.sub(r"^cmn0? \S+ ", "", c)
REPEATED = sum(1 for c in CMD4_CACHE if c in CMD2)                       # identical command lines, labels included
REPEATED_NOLABEL = sum(1 for c in CMD4_CACHE if strip_label(c) in {strip_label(x) for x in CMD2})
FILES2 = sum(1 for f in os.listdir(R2) if f.endswith(".csv")); FILES4 = sum(1 for f in os.listdir(R4) if f.endswith(".csv"))
SPARSE_CMDS = sum(1 for c in CMD4_CACHE if "--sparse" in c)
NEW_DENSE = sum(1 for c in CMD4_CACHE if "all5-dense" in c)
FRESH2 = re.search(r"fresh=(\d+)", open(R2 + "latency-ocm-region0-cpu2.csv").readline()).group(1)
FRESH4 = re.search(r"fresh=(\d+)", open(R4 + "latency-ocm-region0-cpu2.csv").readline()).group(1)

def bw_level(size):
    """a capacity reading of where a streamed buffer of this size fits (hypothesis: the bandwidth rows carry no counters)"""
    return "L1" if size <= 32768 else "L2" if size <= 131072 else ("mesh, no L3 data" if L3_SF else "L3 and mesh") if size <= 262144 else "SLC" if size <= SLC_BYTES else "DRAM"
CME_INNER_ZERO = 0; CME_TIMED = 0
for f in sorted(glob.glob(R4 + "cme-latency-*.csv")):
    for d in lat_rows(f):
        if d["mode"].endswith("best") or "roundtrip" in d["mode"] or "call" in d["mode"]: continue
        CME_TIMED += 1; CME_INNER_ZERO += d["c2"] == 0.0
        assert d["c3"] > 0
CALL_OUT = max(CALL, key=lambda d: d["ns"]); CALL_OUT_RATIO = CALL_OUT["c1"] / CALL_OUT["cyc"]

# ---------------------------------------------------------------- html helpers
def fmt(x, nd=1): return "-" if x is None else f"{x:,.{nd}f}"
def tr(cells, head=False):
    tag = "th" if head else "td"
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
def table(head, rows, note=None):
    s = '<div class="tbl"><table>' + tr(head, True) + "".join(tr(r) for r in rows) + "</table></div>"
    return s + (f'<p class="note">{note}</p>' if note else "")
def pct(a, b): return f"{100 * (a - b) / b:+.2f} %"
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;")

C = dict(ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9", axis="#c3c2b7", s1="#2a78d6", s2="#eb6834", s3="#1baf7a", s4="#eda100", s7="#6250d6",
         dsu="#e9f1fb", hns="#fdeee6", cme="#fdeee6")

class SVG:
    def __init__(self, w, h): self.w, self.h, self.parts = w, h, []
    def add(self, s): self.parts.append(s)
    def text(self, x, y, s, size=12, anchor="start", fill=None, weight=None, title=None):
        extra = f' font-weight="{weight}"' if weight else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill or C["ink"]}"{extra}>{esc(s)}</text>')
    def line(self, x1, y1, x2, y2, stroke, width=1, dash=None, title=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"{d}/>')
    def circle(self, x, y, r, fill, title=None, stroke="#fcfcfb"):
        t = f"<title>{esc(title)}</title>" if title else ""
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2">{t}</circle>')
    def rect(self, x, y, w, h, fill, title=None, stroke=None, rx=3):
        t = f"<title>{esc(title)}</title>" if title else ""
        s = f' stroke="{stroke}"' if stroke else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{s}>{t}</rect>')
    def path(self, d, stroke, width=2, fill="none", dash=None):
        dd = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" stroke="{stroke}" stroke-width="{width}" fill="{fill}" stroke-linejoin="round" stroke-linecap="round"{dd}/>')
    def out(self):
        return f'<svg viewBox="0 0 {self.w} {self.h}" xmlns="http://www.w3.org/2000/svg" role="img">' + "".join(self.parts) + "</svg>"

def legend(svg, x, y, items, w=900):
    cx, cy = x, y
    for label, color in items:
        adv = 24 + len(label) * 6.4
        if cx + adv > w - 10 and cx > x: cx, cy = x, cy + 16
        svg.rect(cx, cy - 9, 12, 12, color, rx=2); svg.text(cx + 18, cy + 1, label, 12, fill=C["ink2"]); cx += adv
def legend_rows(items, x, w=900):
    cx, rows = x, 1
    for label, color in items:
        adv = 24 + len(label) * 6.4
        if cx + adv > w - 10 and cx > x: cx, rows = x, rows + 1
        cx += adv
    return rows

import math
def line_chart(series, w=900, h=360, ylabel="ns per load", xlog=True, ylim=None, marks=(), hline=None, ticks_y=None):
    """series: list of dict(name, color, pts=[(x, y, title)], dash=None). x in bytes on a log axis."""
    items = [(s["name"], s["color"]) for s in series]; L = 70
    B = 54 + 16 * (legend_rows(items, L, w) - 1); h = h + 16 * (legend_rows(items, L, w) - 1)
    svg = SVG(w, h); Rr, T = 20, 24
    xs = [p[0] for s in series for p in s["pts"]]; ys = [p[1] for s in series for p in s["pts"]]
    x0, x1 = min(xs), max(xs); y0, y1 = (0, max(ys) * 1.08) if ylim is None else ylim
    fx = lambda x: L + (math.log2(x) - math.log2(x0)) / (math.log2(x1) - math.log2(x0)) * (w - L - Rr) if xlog else L + (x - x0) / (x1 - x0) * (w - L - Rr)
    fy = lambda y: T + (y1 - y) / (y1 - y0) * (h - T - B)
    yt = ticks_y or [round(y0 + i * (y1 - y0) / 5, 1) for i in range(6)]
    for t in yt:
        svg.line(L, fy(t), w - Rr, fy(t), C["grid"]); svg.text(L - 8, fy(t) + 4, f"{t:g}", 11, "end", C["muted"])
    svg.text(L, T - 10, ylabel, 11, "start", C["ink2"])
    xt = sorted({p[0] for s in series for p in s["pts"]}); lastx, row = -1e9, 0
    for t in xt:
        row = 1 - row if fx(t) - lastx < 30 else 0; lastx = fx(t)
        svg.text(fx(t), h - B + 16 + 11 * row, kib(t).replace(" KiB", "K").replace(" MiB", "M"), 10, "middle", C["muted"])
    svg.text(w - Rr, h - B + 38, "footprint (log scale)", 10, "end", C["ink2"])
    if hline:   # (y, label) puts the label at the right end; (y, label, x) starts it at footprint x, for a chart whose series cross the line at the right
        svg.line(L, fy(hline[0]), w - Rr, fy(hline[0]), C["muted"], 1, "4 4")
        if len(hline) > 2: svg.text(fx(hline[2]) + 4, fy(hline[0]) - 5, hline[1], 11, "start", C["ink2"])
        else: svg.text(w - Rr, fy(hline[0]) - 5, hline[1], 11, "end", C["ink2"])
    for i, m in enumerate(marks):   # (x, label), labels staggered so neighbours do not collide
        svg.line(fx(m[0]), T, fx(m[0]), h - B, C["axis"], 1, "2 4"); svg.text(fx(m[0]) + 4, T + 12 + 12 * (i % 2), m[1], 10, "start", C["muted"])
    for s in series:
        d = "M" + " L".join(f"{fx(x):.1f},{fy(y):.1f}" for x, y, *_ in s["pts"])
        svg.path(d, s["color"], 2, dash=s.get("dash"))
        for x, y, *t in s["pts"]: svg.circle(fx(x), fy(y), 4, s["color"], t[0] if t else f"{s['name']} {kib(x)}: {y:g}")
        lx, ly = s["pts"][-1][0], s["pts"][-1][1]
        svg.text(fx(lx) - 6, min(fy(ly) + s.get("dy", -8), h - B - 6), s.get("short", s["name"]), 11, "end", C["ink2"])
    legend(svg, L, h - B + 52, items, w)
    return svg.out()

def dumbbell(rows, w=900, unit="ns", colors=(C["muted"], C["s1"]), names=("run 2", "run 3"), xlim=None, note_delta=True):
    """rows: list of dict(label, a, b, title?)"""
    rh = 26; L, Rr, T, B = 230, 80, 30, 40; h = T + B + rh * len(rows)
    svg = SVG(w, h)
    vals = [v for r in rows for v in (r["a"], r["b"]) if v is not None]
    x0, x1 = xlim or (min(vals) * 0.9, max(vals) * 1.05)
    fx = lambda v: L + (v - x0) / (x1 - x0) * (w - L - Rr)
    for t in [x0 + i * (x1 - x0) / 5 for i in range(6)]:
        svg.line(fx(t), T - 6, fx(t), h - B, C["grid"]); svg.text(fx(t), T - 10, f"{t:.1f}", 10, "middle", C["muted"])
    svg.text(w - Rr + 24, T - 10, unit, 10, "start", C["ink2"])
    for i, r in enumerate(rows):
        y = T + rh * i + rh / 2
        svg.text(L - 10, y + 4, r["label"], 12, "end")
        if r["a"] is not None and r["b"] is not None:
            svg.line(fx(r["a"]), y, fx(r["b"]), y, C["axis"], 2)
        if r["a"] is not None: svg.circle(fx(r["a"]), y, 5, colors[0], f"{names[0]} {r['label']}: {r['a']:.3f} {unit}")
        if r["b"] is not None: svg.circle(fx(r["b"]), y, 5, colors[1], f"{names[1]} {r['label']}: {r['b']:.3f} {unit}")
        if note_delta and r["a"] is not None and r["b"] is not None:
            svg.text(fx(max(r["a"], r["b"])) + 9, y + 4, f"{r['b'] - r['a']:+.2f}", 10, "start", C["ink2"])
    legend(svg, L, h - 10, list(zip(names, colors)), w)
    return svg.out()

def strip(rows, w=900, unit="ns", color=C["s1"], markers=(), xlim=None):
    """rows: dict(label, vals=[...], best, extra=[(value, color, name)])  one row of dots per label"""
    rh = 24; L, Rr, T, B = 230, 60, 30, 40; h = T + B + rh * len(rows)
    svg = SVG(w, h)
    vals = [v for r in rows for v in r["vals"]] + [e[0] for r in rows for e in r.get("extra", [])]
    x0, x1 = xlim or (min(vals) * 0.95, max(vals) * 1.03)
    fx = lambda v: L + (v - x0) / (x1 - x0) * (w - L - Rr)
    for t in [x0 + i * (x1 - x0) / 5 for i in range(6)]:
        svg.line(fx(t), T - 6, fx(t), h - B, C["grid"]); svg.text(fx(t), T - 10, f"{t:.0f}", 10, "middle", C["muted"])
    svg.text(w - Rr + 24, T - 10, unit, 10, "start", C["ink2"])
    for i, r in enumerate(rows):
        y = T + rh * i + rh / 2
        svg.text(L - 10, y + 4, r["label"], 12, "end")
        for v in r["vals"]: svg.circle(fx(v), y, 4, color if v != r["best"] else C["ink"], f"{r['label']}: {v:.3f} {unit}" + (" (best)" if v == r["best"] else ""))
        for v, col, name in r.get("extra", []):
            svg.rect(fx(v) - 4, y - 6, 8, 12, col, f"{name} {r['label']}: {v:.3f} {unit}", rx=1)
    legend(svg, L, h - 10, [("one pass (best in black)", color)] + [(m[1], m[0]) for m in markers], w)
    return svg.out()

def mesh_map(w=900, left=None, node_labels=None, dsu_labels=None, paths=(), title_dsu="DSU 1: CPUs 2, 3"):
    """the hemisphere map: a left column of levels and the 6 by 6 mesh with the five home nodes and five DSU ports"""
    s = 92; ox, oy = 350, 40; h = oy + 6 * s + 10
    svg = SVG(w, h)
    cx = lambda X: ox + X * s; cy = lambda Y: oy + (5 - Y) * s
    for X in range(6):
        for Y in range(6):
            if X < 5: svg.line(cx(X), cy(Y), cx(X + 1), cy(Y), C["grid"], 1.5)
            if Y < 5: svg.line(cx(X), cy(Y), cx(X), cy(Y + 1), C["grid"], 1.5)
    for X in range(6): svg.text(cx(X), cy(0) + 30, f"x={X}", 10, "middle", C["muted"])
    for Y in range(6): svg.text(cx(5) + 46, cy(Y) + 4, f"y={Y}", 10, "start", C["muted"])
    for (X, Y) in SBSX: svg.circle(cx(X), cy(Y), 5, C["axis"], f"crosspoint ({X},{Y}): SBSX bridge toward a memory controller", stroke=C["axis"])
    svg.text(cx(0) - 10, cy(5) - 18, "grey dots: SBSX bridges to DRAM", 10, "start", C["muted"])
    for p in paths:   # (dsu, node, color, label)
        d, n, col, lab = p; ax, ay = DSUS[d][0], DSUS[d][1]; bx, by = NODES[n][0], NODES[n][1]
        svg.path(f"M{cx(ax)},{cy(ay)} L{cx(bx)},{cy(ay)} L{cx(bx)},{cy(by)}", col, 3, dash="6 4")
    for n, (X, Y, r) in NODES.items():
        lab = (node_labels or {}).get(n, [])
        hh = 44 + 11 * len(lab)
        svg.rect(cx(X) - 36, cy(Y) - hh / 2, 72, hh, C["hns"], f"home node {n} at ({X},{Y}), OCM region {r}", stroke="#e8b9a2")
        svg.text(cx(X), cy(Y) - hh / 2 + 15, f"HN-S {n}", 11, "middle", weight=600); svg.text(cx(X), cy(Y) - hh / 2 + 27, f"OCM{r}", 10, "middle", C["ink2"])
        for i, t in enumerate(lab): svg.text(cx(X), cy(Y) - hh / 2 + 39 + 11 * i, t, 9.5, "middle", C["s2"], 600)
    for d, (X, Y, cpus) in DSUS.items():
        svg.rect(cx(X) - 34, cy(Y) - 22, 68, 44, C["dsu"], f"DSU {d} port at ({X},{Y}), CPUs {cpus[0]} and {cpus[1]}", stroke="#b7d3f6")
        svg.text(cx(X), cy(Y) - 6, f"DSU {d}", 11, "middle", weight=600); svg.text(cx(X), cy(Y) + 7, f"CPU {cpus[0]}, {cpus[1]}", 10, "middle", C["ink2"])
        if dsu_labels and d in dsu_labels: svg.text(cx(X), cy(Y) + 18, dsu_labels[d], 10, "middle", C["s1"], 600)
    X, Y = DSU0
    svg.rect(cx(X) - 34, cy(Y) - 22, 68, 44, "#f1f1ee", "DSU 0 port at (1,2), CPUs 0 and 1: where device interrupts are routed (irqaffinity=0-1) and where the scheduler may place unpinned tasks. The scripts and the counter helper ran pinned to CPU 2; each measured program pinned itself to its --cpu; every core runs its own timer interrupts, page faults and system calls.", stroke=C["axis"])
    svg.text(cx(X), cy(Y) - 6, "DSU 0", 11, "middle", weight=600); svg.text(cx(X), cy(Y) + 7, "CPU 0, 1 (device interrupts)", 9, "middle", C["ink2"])
    # left column: the path of one load outward
    if left:
        y = oy + 10; svg.text(20, y, title_dsu, 11, "start", weight=600); y += 14
        for name, val, fill in left:
            lines = name if isinstance(name, list) else [name]   # a name may take several lines
            hh = 40 + 13 * (len(lines) - 1)
            svg.rect(20, y, 300, hh, fill, stroke=C["axis"])
            for i, t in enumerate(lines): svg.text(30, y + 17 + 13 * i, t, 11.5, "start", weight=600)
            svg.text(30, y + hh - 8, val, 10.5, "start", C["ink2"])
            svg.line(170, y + hh, 170, y + hh + 12, C["axis"], 1.5); y += hh + 12
        pass
    return svg.out()


def cme_path_fig(w=960, meas=None):
    """the data path of one CME load (LD1D in streaming mode, as the chase kernel issues it), from the C1-Nano core outward.
    Boxes and their text are from the Arm manuals (C1-Nano SOG 109590 2.33, C1-SME2 TRM 107831 chapters 1, 2, 5, 6, C1-DSU TRM 107804 chapter 2);
    the coloured numbers are run 3 measurements, passed in as meas."""
    svg = SVG(w, 462)
    def box(x, y, bw, bh, title, lines, fill, stroke):
        svg.rect(x, y, bw, bh, fill, stroke=stroke)
        svg.text(x + 8, y + 15, title, 11, "start", None, 600)
        for i, t in enumerate(lines): svg.text(x + 8, y + 30 + 12 * i, t, 9.5, "start", C["ink2"])
    def head(x, y, dx, dy, col):   # a triangle pointing along the unit vector (dx, dy)
        px, py = -dy, dx
        svg.path(f"M{x:.1f},{y:.1f} L{x - 7 * dx + 3.5 * px:.1f},{y - 7 * dy + 3.5 * py:.1f} L{x - 7 * dx - 3.5 * px:.1f},{y - 7 * dy - 3.5 * py:.1f} Z", col, 1, fill=col)
    def arrow(x1, y1, x2, y2, col, dash=None):
        svg.line(x1, y1, x2, y2, col, 2, dash=dash)
        dx, dy = x2 - x1, y2 - y1; n = (dx * dx + dy * dy) ** 0.5; head(x2, y2, dx / n, dy / n, col)
    req, ret = C["s1"], C["s2"]
    y1, h1 = 58, 96
    svg.rect(10, 20, 940, y1 + h1 + 18 - 20, "#f6f8fc", stroke="#b7d3f6"); svg.text(18, 34, "DSU 1: the cluster of CPUs 2 and 3 (CPU 3 offline during the CME test)", 10, "start", C["ink2"], 600)
    box(20, y1, 215, h1, "1. C1-Nano core, CPU 2",
        ["streaming mode (SMSTART) [SOG 2.33]", "LD1D decoded here, issued to the CME", "3 SME instr. per cycle, loads/stores 2", "MMU: x0 (virtual) -> physical address", "core L1D 32 KiB, L2 128 KiB: not used"], C["dsu"], "#b7d3f6")
    box(250, y1, 150, h1, "2. DSU bridges", ["CPU and SME2 unit bridges", "CMEREQ: the request channel", "(LD1D + physical address)", "CMETLB: the TLB channel", "(prefetcher translations)"], "#f1f1ee", C["axis"])
    box(415, y1, 270, h1, "3. CME (C1-SME2 unit)",
        ["decode, rename, issue queues", "L1D 64 KiB, 4-way, 16 banks, PIPT, 64 B lines", "2 x 512-bit read paths: one line fills Z0", "prefetcher: 128 streams, own TLB, fills L1D + L3", "LASTB: last element of Z0 -> x0, sent to the core"], C["cme"], "#e8b9a2")
    box(700, y1, 240, h1, "4. DSU L3 memory system",
        ["SCU + snoop filter (tracks the CME L1D too)", "L3 cache 256 KiB" + (": no data on this run" if L3_SF else ""), "memory interface: CHI, 256-bit wide"], C["dsu"], "#b7d3f6")
    y2, h2 = y1 + h1 + 56, 80
    box(300, y2, 180, h2, "5. CMN mesh", ["DSU 1 enters at crosspoint (2,3)", "1 or 3 crosspoints to the home", "node that owns the address"], "#f9f9f7", C["axis"])
    box(500, y2, 230, h2, "6. Home node (HN-S)", ["one of five; a 1 MiB array of 16 ways:", "SLC 768 KiB (12 ways), DRAM lines", "OCM 256 KiB (4 ways), 0xE0000000 + n MiB"], C["hns"], "#e8b9a2")
    box(750, y2, 190, h2, "7. DRAM (on an SLC miss)", ["emulator memory, behind the", "SBSX bridge and the", "memory controller"], "#f1f1ee", C["axis"])
    # row 1: the request (solid) and the returns (dashed)
    arrow(235, y1 + 30, 250, y1 + 30, req); arrow(400, y1 + 30, 415, y1 + 30, req)
    svg.text(325, y1 - 8, "LD1D + physical address", 9, "middle", req, 600)
    arrow(415, y1 + 72, 400, y1 + 72, ret, dash="5 3"); arrow(250, y1 + 72, 235, y1 + 72, ret, dash="5 3")
    svg.text(325, y1 + h1 + 13, "x0 back to the core (GPR update)", 9, "middle", ret, 600)
    arrow(685, y1 + 44, 700, y1 + 44, req); svg.text(692, y1 - 8, "L1D miss", 9, "middle", req, 600)
    arrow(700, y1 + 72, 685, y1 + 72, ret, dash="5 3"); svg.text(740, y1 + h1 + 13, "line fill: 0x327D inner, 0x327E outer", 9, "end", ret, 600)
    # L3 miss: down and left into the mesh; the line returns up into the L3 memory system
    svg.path(f"M760,{y1 + h1} L760,{y2 - 24} L390,{y2 - 24} L390,{y2 - 2}", req, 2); head(390, y2, 0, 1, req)
    svg.text(575, y2 - 29, "L3 miss: out of the cluster on CHI", 9, "middle", req, 600)
    svg.path(f"M440,{y2} L440,{y2 - 12} L820,{y2 - 12} L820,{y1 + h1 + 2}", ret, 2, dash="5 3"); head(820, y1 + h1, 0, -1, ret)
    # row 2
    arrow(480, y2 + 30, 500, y2 + 30, req); arrow(730, y2 + 30, 750, y2 + 30, req)
    arrow(500, y2 + 62, 480, y2 + 62, ret, dash="5 3"); arrow(750, y2 + 62, 730, y2 + 62, ret, dash="5 3")
    svg.text(300, y2 + h2 + 13, ("the line returns the same way into the CME L1D (0x327E outer refill); the L3 held no data on this run" if L3_SF else "the line returns the same way: into the L3, then the CME L1D (0x327E outer refill)"), 9, "start", ret, 600)
    # the measured strip
    ys = y2 + h2 + 40
    svg.text(20, ys, "Run 3 measurements along this path (ns per load, best rep, CPU 2):", 10.5, "start", C["ink"], 600)
    for i, (lab, val) in enumerate(meas or []):
        yy = ys + 16 + 13 * i
        svg.text(28, yy, lab, 10, "start", C["ink2"]); svg.text(600, yy, val, 10, "start", ret, 600)
    svg.text(20, 440, "Solid blue: the request. Dashed orange: what comes back. Box text from the Arm manuals: C1-Nano SOG 109590 section 2.33, C1-SME2 TRM 107831 chapters 1, 2, 5 and 6, C1-DSU TRM 107804 chapter 2.", 9, "start", C["muted"])
    svg.text(20, 453, "Which level served a CME load is not measured: the two refill events count fills by source side of the cluster, not by level (section 5).", 9, "start", C["muted"])
    return svg.out()

def bars_h(rows, w=900, unit="GB/s", color=C["s1"], xlim=None):
    rh = 24; L, Rr, T, B = 300, 95, 26, 10; h = T + B + rh * len(rows)
    svg = SVG(w, h); x1 = xlim or max(r["v"] for r in rows) * 1.05
    fx = lambda v: L + v / x1 * (w - L - Rr)
    for t in [i * x1 / 5 for i in range(6)]:
        svg.line(fx(t), T - 6, fx(t), h - B, C["grid"]); svg.text(fx(t), T - 10, f"{t:.0f}", 10, "middle", C["muted"])
    svg.text(w - Rr + 30, T - 10, unit, 10, "start", C["ink2"])
    for i, r in enumerate(rows):
        y = T + rh * i + 3
        svg.text(L - 10, y + 14, r["label"], 12, "end")
        svg.rect(L, y, fx(r["v"]) - L, rh - 6, r.get("color", color), f"{r['label']}: {r['v']:,.1f} {unit}", rx=2)
        svg.text(fx(r["v"]) + 6, y + 14, f"{r['v']:,.1f}", 11, "start", C["ink2"])
    return svg.out()

CSS = r"""
:root { --bg:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --axis:#c3c2b7;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s7:#6250d6;
  --font:system-ui,-apple-system,"Segoe UI",sans-serif; --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color-scheme:light; }
body { background:var(--bg); color:var(--ink); font-family:var(--font); font-size:15px; line-height:1.5; margin:0;
  padding-block:24px 48px; padding-left:max(16px,env(safe-area-inset-left,0px)); padding-right:max(16px,env(safe-area-inset-right,0px)); }
main { max-width:980px; margin:0 auto; }
h1 { font-size:28px; line-height:1.2; margin:0 0 6px; text-wrap:balance; }
h2 { font-size:21px; margin:44px 0 10px; text-wrap:balance; border-top:1px solid var(--grid); padding-top:18px; }
h3 { font-size:16px; margin:22px 0 6px; }
p, li, dd { max-width:72ch; }
.short { background:var(--surface); border-left:4px solid var(--s1); padding:12px 16px; margin:16px 0 24px; }
.short p { margin:0 0 8px; } .short p:last-child { margin:0; }
.meta, .note { color:var(--ink2); font-size:14px; }
.note { max-width:none; margin:4px 0 0; }
nav.toc { background:var(--surface); border:1px solid var(--grid); border-radius:6px; padding:10px 18px; margin:0 0 8px; }
nav.toc ol { margin:6px 0; padding-left:4px; list-style:none; columns:2; column-gap:28px; } nav.toc li { break-inside:avoid; margin:2px 0; }
nav.toc ol ol { columns:1; margin:1px 0 3px; padding-left:22px; font-size:14px; }
nav.toc a { color:var(--s1); text-decoration:none; } nav.toc a:hover { text-decoration:underline; }
figure { margin:18px 0 6px; background:var(--surface); border:1px solid var(--grid); border-radius:6px; padding:10px 10px 6px; }
figure svg { width:100%; height:auto; display:block; }
figcaption { font-size:14px; color:var(--ink2); margin:8px 4px 2px; max-width:none; }
.take { font-weight:600; color:var(--ink); }
.tbl { overflow-x:auto; margin:8px 0 4px; }
table { border-collapse:collapse; font-size:13px; font-variant-numeric:tabular-nums; min-width:520px; }
th, td { text-align:left; padding:5px 10px; border-bottom:1px solid var(--grid); vertical-align:top; }
th { color:var(--ink2); font-weight:600; }
td:nth-child(n+2), th:nth-child(n+2) { text-align:right; }
td:last-child, th:last-child { text-align:left; }
td .d { color:var(--muted); font-size:11px; }
code { font-family:var(--mono); font-size:13px; background:#efeee9; padding:1px 4px; border-radius:3px; }
dl { display:grid; grid-template-columns:max-content 1fr; gap:4px 14px; }
dt { font-weight:600; } dd { margin:0; }
.hyp { display:inline-block; font-size:12px; padding:1px 7px; border-radius:10px; background:#fbe9e2; color:#8a3a1c; margin-right:6px; }
.ok { display:inline-block; font-size:12px; padding:1px 7px; border-radius:10px; background:#e3f3e3; color:#1d5a1d; margin-right:6px; }
.gap { display:inline-block; font-size:12px; padding:1px 7px; border-radius:10px; background:#efeee9; color:#52514e; margin-right:6px; }
.plan { display:inline-block; font-size:12px; padding:1px 7px; border-radius:10px; background:#e4edf9; color:#1f4f8f; margin-right:6px; }
svg text { font-family:var(--font); }
@media (max-width:640px) { dl { grid-template-columns:1fr; } dd { margin-bottom:8px; } nav.toc ol { columns:1; } }
"""

def page(title, subtitle, toc, body):
    def item(e):   # (id, title) or (id, title, [sub-entries])
        subs = e[2] if len(e) > 2 else []
        return f'<li><a href="#{e[0]}">{e[1]}</a>' + (f'<ol>{"".join(item(x) for x in subs)}</ol>' if subs else "") + "</li>"
    nav = "".join(item(e) for e in toc)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body><main>
<h1>{title}</h1>
<p class="meta">{subtitle}</p>
<nav class="toc"><b>Contents</b><ol>{nav}</ol></nav>
{body}
</main></body></html>"""

def fig(svg, take, rest=""):
    return f'<figure>{svg}<figcaption><span class="take">{take}</span> {rest}</figcaption></figure>'

WORDS_COMMON = [
    ("C1-Nano, DSU", "The Arm core and its two-core cluster (DynamIQ Shared Unit). The hemisphere has 5 DSUs, CPUs 0 to 9. Device interrupts are routed to CPUs 0 and 1 (irqaffinity=0-1); the scheduler places no unpinned task on CPUs 2 to 9 (isolcpus=2-9) and their periodic tick stops while one task runs (nohz_full=2-9). The init started run_all.sh pinned to CPU 2, so the scripts, the shell and the counter helper ran on CPU 2 (cmncount sets no affinity of its own) and each measured program pinned itself to its --cpu. Every core takes its own timer and per-CPU interrupts, and a program's page faults and system calls run on its own core [Jesse's run 3 README, The run and CPU placement]."),
    ("L1, L2, L3", "32 KiB data cache per core, 128 KiB per DSU, 256 KiB per DSU, 64-byte lines [sysinfo.txt]." + (" On this run, as on runs 1 and 2 and run 4 boots A to D, the L3 of CPUs 2 to 9 was in snoop-filter-only mode and held no data: the stock SCP firmware stages the full L3 for cluster 0 only, and run 4 boot B's hit counters read 0 L3 hits per load. There is no L3 level in these numbers; run 4 boot E turned the L3 on [asimov-c1nano-run4.html, sections 11.1 and 14]." if L3_SF else "")),
    ("mesh, crosspoint (xp)", "The Arm CMN S3 interconnect, a 6 by 6 grid of routers. Distance between two points is the number of crosspoint steps, |dx| + |dy|."),
    ("home node (HN-S), SLC", "The five mesh nodes that own all addresses, each with 1 MiB of System Level Cache in 16 ways. A DRAM address belongs to one home node by a hash, so a buffer spreads over all five."),
    ("OCM", "On-Chip Memory: 4 of the 16 ways of each home node, locked as 256 KiB of memory at 0xE0000000 + n MiB. Region n lives in home node n only. Reached through /dev/ocm in 4 KiB pages."),
    ("node id", "The mesh id of a home node (88, 160, 216, 288, 344). Its bits give the crosspoint: x = bits 8 to 6, y = bits 5 to 3."),
    ("chase, hop", "A pointer chase: each load reads the address of the next load, so the loads cannot overlap and the time per load is the load-to-use latency. One load of the chain is one hop."),
    ("repeated chase, fresh chain, flushed", "Repeated: a random chain walked many times, so later walks hit whatever cache holds it. Fresh: a chain walked once. Flushed: every line was cleaned and invalidated from the caches with DC CIVAC first."),
    ("sparse chain", "New in run 3: a chain with one member line per 4 KiB page, at a different line offset per chain, so a line the hardware prefetcher fetches beside a member is never itself a member. A 256 KiB region gives 64 hops per pass; all five regions give 320. The run 2 chains were dense (every line of the region, 4,096 hops)."),
    ("best, pass, rep", "A command walks its chain several times (passes, or reps); best is the fastest. A sparse per-region row has 7 fresh passes, a dense all-five control 2, a repeated chase 3 reps."),
    ("refills per load", "PMU events 0x03 (L1D refill), 0x17 (L2D refill), 0xA2 (L3D read refill) divided by the loads of the timed walk. 1.00 means one fill of that level per load. A fill can be a demand miss or a prefetch, so the count does not say which loads missed, and a useful prefetch can replace a later demand fill and leave the count near one."),
    ("perf_cov", "New in run 3: the counter group's running time over its enabled time for the row. 1.0000 means the counters were never multiplexed; every row of this run reads 1.0000."),
    ("cmncount", "The helper that opens the mesh PMU (arm_cmn_0) around one command and writes cmn-counts.csv: requests received per home node, memory-controller requests and SLC misses."),
    ("SCP, TF-A", "The System Control Processor firmware (which also sets up the mesh) and Trusted Firmware-A (the boot firmware of the application cores). Run 3 ran SCP 0.48.0-nopcie.1 and TF-A 0.35.0, the same as run 2 [Jesse's run 3 README]."),
    ("chip time", "Time as the emulated chip sees it. One chip second took 2,776 wall seconds in run 3 [Jesse's run 3 README]."),
    ("est.", "An estimate, not a measurement."),
]
WORDS_CME = [
    ("CME", "The Compute Matrix Engine: Arm's C1-SME2 unit (code name Griffin). One per DSU, shared by the DSU's two cores. It executes the cores' streaming-mode (SME) instructions, with its own 64 KiB 4-way L1 data cache, its own TLB and its own hardware prefetcher. Its path to memory is CME L1, then the DSU's L3" + (" (which held no data on this run)" if L3_SF else "") + ", then the mesh; the core's L1 and L2 are not on it [Jesse's run 3 README, CME; CME-plan.md section 1]."),
    ("streaming mode, SMSTART, SMSTOP", "The CPU state in which SVE instructions run on the CME. SMSTART enters it and SMSTOP leaves it; both zero the vector registers. The test kernels enter it once per timed call and leave at the end."),
    ("SVL", "The streaming vector length: 64 bytes on this chip, one cache line [dmesg: SME default vector length 64 bytes]."),
    ("cme-roundtrip, cme-call", "Two controls with no memory access. cme-roundtrip moves a value into a vector register and back out (DUP then LASTB) 65,536 times inside one streaming span. cme-call does one such hop per call, 64 calls, so it carries the SMSTART, register save and SMSTOP of a whole call."),
    ("CME counters", "The CME's own PMU events read through the core PMU: 0x3246 CME cycles, 0x327D CME L1D refills from inside the cluster (inner), 0x327E refills from outside the cluster (outer). Per load means divided by the hops of the timed span. These events count prefetch refills too [CME-plan.md section 2.1]."),
    ("CME power (dynamic mode)", "The firmware arms each CME's power controller in dynamic mode, so the CME switches itself off when idle and back on at the next streaming instruction. Whether it was off at the start of a timed span is not recorded [Jesse's run 3 README, CME power]."),
    ("ldr16, str16", "The 64-byte forms of the read and write kernels (one vector per instruction) beside the 256 B forms (four vectors per instruction)."),
]
def words(items): return "<dl>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items) + "</dl>"

PLATFORM = """<ul>
<li><b>Where and when.</b> One emulated Asimov hemisphere on the GA13 Palladium (image hemi_rtws_tlm, RTL 0d9e214, release a10280100), 2026-11-03 UTC, as one job: run_asimov.sh then run_cme.sh. 2.918 s of chip time (about 1.62 s for the cache test and 1.28 s for the CME test). All 100 commands exited 0 and all 80 files came back with matching checksums [Jesse's run 3 README, The run; SHA256SUMS checked here].</li>
<li><b>Platform.</b> Run 2's: SCP 0.48.0-nopcie.1 and TF-A 0.35.0, Linux 6.18.36, 256 huge pages of 2 MiB, /dev/ocm in 4 KiB pages, CPUs 2 to 9 isolated. Core 2.000 GHz against a 1 GHz timer. DRAM is an emulator memory, not LPDDR5X, so no DRAM number is silicon-like [Jesse's run 3 README, Platform facts].</li>
<li><b>Code.</b> cache-mem-perf commit ba834c0. Against run 2 (8ae533c): sparse OCM chains, the dense all-five control rows, the perf_cov column, the CME test. The program flags of the repeated rows are unchanged.</li>
</ul>"""

# ======================================================================= page 1: the C1-Nano core
def core_page():
    read_note = (f" Boot C ran them: with the hardware prefetcher on, PRFM 4 lines ahead reads {R4A['bootC']['read_variants']['read-pf4@33554432']:.2f} GB/s against the plain loop's {R4A['bootC']['read_variants']['read@33554432']:.2f} at 32 MiB, so the hint adds little; with the L3 on (boot E) the plain loop reads {R4E['read_variants']['read@33554432']:.2f} GB/s [asimov-c1nano-run4.html, section 14.3]." if R4E else "")
    g8_note = ((lambda b: f" <span class='ok'>boots C, E</span> Run 5c's G8 rows separate them in part: in one assembly call the 16 and 24 KiB reads reach {min(b):.1f} to {max(b):.1f} GB/s, {100 * max(b) / 64:.0f} % of the 64 GB/s path, and the added bytes between the 8 and 16 KiB rows move at the path's rate, so the shortfall is a cost per pass of the loop, not the L1's rate [asimov-c1nano-run4.html, section 15].")([R4A['g8'][x]['asm read']['best'][sz] for x in R4A['g8'] for sz in ('16384', '24576')]) if R4A and R4A.get('g8') else "")
    route_note = (f" Boot B gave it: with the prefetchers off the 20 route cells fit distance within {R4B['fit']['rms']:.2f} ns rms, so most of the spread was the prefetchers' [asimov-c1nano-run4.html, section 11]." if R4B else "")
    parts_note = (f" Boots B to D answered it: the sparse chain's cost above the dense one on CPU 2 falls from a mean of {R4A['h4']['gap_mean']['A']:.1f} ns on boot A to {R4A['h4']['gap_mean']['B']:.1f} ns with the prefetchers off (boot B), {R4A['h4']['gap_mean']['C']:.1f} ns with the OCM in 64 KiB translations (boot C) and {R4A['h4']['gap_mean']['D']:.1f} ns with both (boot D), while the L1 TLB refills fall to {R4A['bootC']['tlb_per_pass'][0]:.0f} to {R4A['bootD']['tlb_per_pass'][1]:.0f} per pass [asimov-c1nano-run4.html, section 13]." if R4A and R4A.get('h4') else "")
    hit_note = (f"boots B to E counted the hits directly: 0 L3 read hits per load with the stock SCP, and with the L3 on (boot E) the 192 KiB row reads {R4E['chase']['196608']:.1f} ns with {100 * R4E['l3rows']['196608']['l3hit']:.0f} % L3 hits [asimov-c1nano-run4.html, sections 11.1 and 14.1]." if R4E else "a direct hit count waits on boot C's latency-dram-small-l3.csv (the run 5 hit set).")
    # T1 levels
    t1 = table(["Footprint", "Chase", "Run 3 ns", "Run 2 ns", "Run 3 vs run 2", "L1 refills", "L2 refills", "L3 read refills", "Reads from"],
               [[kib(d["size"]), d["kind"], fmt(d["ns"], 3), fmt(d["ns2"], 3), pct(d["ns"], d["ns2"]), fmt(d["l1"], 2), fmt(d["l2"], 2), fmt(d["l3"], 2), level_name(d["size"], d["kind"])] for d in LV4],
               "CPU 2, ns per load of the best pass, with that pass's refills per load [latency-dram-small.csv, latency-dram-large.csv, latency-dram-flushed.csv, run 3 and run 2]. Run 3 vs run 2 is (run 3 minus run 2) over run 2; a negative value means run 3 was faster. " + ("The L3 of this DSU held no data on this run (snoop-filter-only mode: run 4 boot B's hit counters read 0 L3 hits per load), so the 192 to 384 KiB rows are L2 hits mixed with reads from the SLC across the mesh." if L3_SF else "The L3 is 256 KiB per DSU, so no footprint fits L3 alone."))
    # T2 OCM per region
    t2 = table(["CPU (DSU, port)"] + [f"OCM{r} (node {NODE_OF_REGION[r]})" for r in range(5)] + ["All five, sparse", "All five, dense control", "All five, run 2 (dense)", "2 MiB DRAM chase (SLC)"],
               [[f"CPU {c} (DSU {CPU_DSU[c]}, {DSUS[CPU_DSU[c]][0]},{DSUS[CPU_DSU[c]][1]})"]
                + [f"{fmt(OCM[c][r]['best'], 3)} <span class='d'>({OCM[c][r]['dist']} xp; run 2 {fmt(OCM2[c][r]['best'], 2)})</span>" for r in range(5)]
                + [fmt(ALL5S[c]["best"], 3), fmt(ALL5D[c]["best"], 3), fmt(ALL5_2[c]["best"], 3), fmt(SLC[c]["best"], 3)] for c in (2, 4, 6, 8)],
               "ns per load. Per region: best of 7 sparse passes of 64 hops after a flush of every line, with the distance in crosspoints and run 2's dense best in brackets. All five sparse: best of 7 passes of 320 hops. Dense control: best of 2 passes of 20,480 hops, run 2's chain [latency-ocm-region*-cpu*.csv, latency-ocm-all5*-cpu*.csv, latency-dram-slc-cpu*.csv].")
    t2b = table(["Distance (crosspoints)", "Rows", "Run 3 sparse, mean ns", "Run 3 range ns", "Run 2 dense, mean ns", "Run 2 range ns"],
                [[k, v["n"], fmt(v["mean"], 2), f"{fmt(v['lo'], 2)} to {fmt(v['hi'], 2)} ({DIST_PCT[k]['run3']:.0f} %)", fmt(v["mean2"], 2), f"{fmt(v['lo2'], 2)} to {fmt(v['hi2'], 2)} ({DIST_PCT[k]['run2']:.0f} %)"] for k, v in sorted(DIST.items())],
                f"The same 20 per-region bests grouped by distance; a range is the lowest and highest cell (CPU, region pair) at that distance, with the spread as a percentage of the lowest. Each range spans different cells, not repeats of one cell: run 2's dense rows spread as widely at 1 and 3 crosspoints as run 3's sparse rows. Across all 20 cells the two runs correlate {DIST_CORR:.2f}, but that includes the distance effect; after removing each run's mean at each distance the remaining cell differences correlate {DIST_RESID_CORR:.2f}, so whether a given cell is fast or slow in both runs is unresolved. The 2 cells at 5 crosspoints are both from CPU 8.")
    # T3 one core bandwidth
    t3 = table(["Buffer", "Read GB/s", "Write GB/s", "Copy GB/s", "Run 2 read", "Run 2 write", "Run 2 copy", "Write, run 3 vs run 2", "Capacity reading: read and write; copy"],
               [[kib(d["size"]), fmt(d["read"]), fmt(d["write"]), fmt(d["copy"]), fmt(d["read2"]), fmt(d["write2"]), fmt(d["copy2"]), pct(d["write"], d["write2"]),
                 f"{bw_level(d['size'])}; {bw_level(2 * d['size'])}"] for d in ONE],
               "One thread on CPU 2, best of 3 reps, GB = 1e9 bytes [bandwidth-dram-1core.csv]. Copy reads one buffer and writes another of the same size, so its working set is twice the buffer size, and it counts bytes read plus written. The last column is a reading from the capacities (hypothesis), given for read and write at the buffer size and for copy at twice it: these rows carry no counters, so which level served a stream is not measured.")
    # T4 multi-core
    def one_ref(kernel, size):
        """the run 3 one-core row of the same kernel at the same per-thread buffer, else at the nearest larger one-core footprint"""
        exact = [d for d in ONE if d["size"] == size]
        d = exact[0] if exact else min((d for d in ONE if d["size"] > size), key=lambda d: d["size"])
        return d[kernel], d["size"]
    def ratio_cell(d):
        v, ref = one_ref(d["kernel"], d["size"])
        return f"{d['run3'] / v:.2f}x" + ("" if ref == d["size"] else f" <span class='d'>(one core at {kib(ref)})</span>")
    def per_core_cell(d):
        v, ref = one_ref(d["kernel"], d["size"])
        return f"{100 * d['run3'] / d['threads'] / v:.0f} %"
    def mrows(rows, label): return [[label, d["kernel"], d["threads"], kib(d["size"]), fmt(d["run2"]), fmt(d["run3"]), pct(d["run3"], d["run2"]), ratio_cell(d), per_core_cell(d)] for d in rows]
    t4 = table(["Cores", "Kernel", "Threads", "Per thread", "Run 2 GB/s", "Run 3 GB/s", "Run 3 vs run 2", "Run 3 / one core", "Per core, of one-core rate"], mrows(PAIR, "CPU 2 + 3 (one DSU)") + mrows(PERDSU, "CPUs 2, 4, 6, 8") + mrows(ALL8, "CPUs 2 to 9"),
               "Best of 3 reps. Aggregate = total bytes over the slowest thread's time [bandwidth-pair.csv, bandwidth-perdsu.csv, bandwidth-all8.csv]. Both runs on the same firmware. \"Run 3 / one core\" divides the run 3 aggregate by the run 3 one-core bandwidth of the same kernel at the same per-thread buffer (table 4.3); where no one-core row has that size (160 KiB, 16 MiB) the nearest larger one-core footprint is used and named, which serves from the same level. \"Per core, of one-core rate\" is the same ratio divided by the thread count: the share of its one-core rate each core kept (116.4 GB/s over 2 threads is 58.2 GB/s per core, 100 % of the one-core 58.1). 100 % means the cores add up without interfering; less means they share a limit.")
    _r4 = [d for d in PERDSU if d["kernel"] == "read" and d["size"] == 2097152][0]; _w4 = [d for d in PERDSU if d["kernel"] == "write" and d["size"] == 2097152][0]
    _r8 = [d for d in ALL8 if d["kernel"] == "read" and d["size"] == 2097152][0]; _one2m = [d for d in ONE if d["size"] == 2097152][0]
    t4_note = f"""<ul>
<li><b>Why the four-DSU rows keep 100 % on write but 93 % on read.</b> The two streams hit different limits. A store stream is pinned at the core's own write path, 32.0 GB/s, whatever is behind it: the four writers read {_w4['tmin']:.3f} to {_w4['tmax']:.3f} GB/s each, and 4 times 32 is below the DRAM write ceiling that eight writers reach (table 4.4, 155 GB/s), so nothing shared is saturated. A read stream beyond L2 is bound by latency (a fixed number of lines in flight per core), and the aggregate is defined by the slowest thread: the four readers read {_r4['tmin']:.2f} to {_r4['tmax']:.2f} GB/s each against {_one2m['read']:.2f} for one core alone, so the fastest reader kept {100 * _r4['tmax'] / _one2m['read']:.1f} % of the one-core rate and the slowest {100 * _r4['tmin'] / _one2m['read']:.0f} %. The spread is a per-core property, not interference: with eight readers the per-thread range is {_r8['tmin']:.2f} to {_r8['tmax']:.2f} GB/s, nearly the same, and the aggregate doubles. <span class="hyp">hypothesis</span> The slowest reader is the core farthest from the home nodes: the 2 MiB chase reads {SLC[2]['best']:.1f}, {SLC[4]['best']:.1f}, {SLC[6]['best']:.1f} and {SLC[8]['best']:.1f} ns from CPUs 2, 4, 6 and 8 (table 4.2), an {100 * (SLC[8]['best'] / SLC[2]['best'] - 1):.0f} % spread that matches the {100 * (_r4['tmax'] / _r4['tmin'] - 1):.0f} % spread in read rate; the program does not record which thread was slowest.</li>
<li><b>Where write loses instead.</b> In two groups of rows write keeps less than read: two writers in one DSU at 160 KiB, and eight writers at any size. There the writers share one path. For the pair it is the DSU's one mesh port. For the eight it is the DRAM write ceiling (section 8). A write stream is 32 GB/s per core and a read stream beyond L2 is 9 to 12 GB/s. So writers fill a shared path about three times sooner than readers do.</li>
</ul>"""
    t4b = table(["Writers (CPUs)", "DSUs used", "Run 2 GB/s", "Run 3 GB/s", "Run 3 vs run 2", "Per writer, run 3"],
                [[p["cpus"].replace("-", ", "), ", ".join(str(d) for d in p["dsus"]), fmt(p["run2"]), fmt(p["run3"]), pct(p["run3"], p["run2"]), f"{fmt(p['tmin'])} to {fmt(p['tmax'])}"] for p in PLACE],
                "16 MiB per writer, one pass, best of 2 reps [bandwidth-write-cpus*.csv].")
    t5 = table(["Row", "Run 3 GB/s", "Run 2 GB/s", "Run 3 vs run 2", "Note"],
               [[f"Read OCM{r} from CPU 2 ({dist(2, NODE_OF_REGION[r])} xp)", fmt(OCMBW["region"][r]), fmt(OCMBW["region2"][r]), pct(OCMBW["region"][r], OCMBW["region2"][r]), "256 KiB, flushed before, one pass"] for r in range(5)]
               + [["Read all five from CPU 2", fmt(OCMBW["all5"]), fmt(OCMBW["all5_2"]), pct(OCMBW["all5"], OCMBW["all5_2"]), "1.25 MiB, flushed before, one pass"],
                  ["Read OCM1 to 4 from CPUs 2, 4, 6, 8", fmt(OCMBW["four"]), fmt(OCMBW["four2"]), pct(OCMBW["four"], OCMBW["four2"]), "4 threads, one region each"],
                  ["Streaming write, all five, from CPU 2", fmt(OCMBW["write"]), fmt(OCMBW["write2"]), pct(OCMBW["write"], OCMBW["write2"]), "8 passes over 1.25 MiB"]],
               "Best of 3 reps [bandwidth-ocm-*.csv].")
    # T5b one core by level: the DRAM-address rows of table 4.3 and the OCM rows of table 4.6, run 3 only
    _one = {d["size"]: d for d in ONE}
    def _lv(size): return [bw_level(size), f"{kib(size)} DRAM-address buffer, warm, {_passes_one(size)} passes", fmt(_one[size]["read"]), fmt(_one[size]["write"])]
    t5b = table(["Level (capacity reading, hypothesis)", "Row (one core, CPU 2)", "Read GB/s", "Write GB/s"],
                [["Core, its own load and store paths", f"not a measured row: the TRM's dual 128-bit read path and single 128-bit write path at the {CORE_GHZ:.1f} GHz the latency rows show", f"{32 * CORE_GHZ:.1f}", f"{16 * CORE_GHZ:.1f}"],
                 _lv(16384), _lv(49152), _lv(98304), _lv(262144), _lv(2097152),
                 ["OCM, one home node", "256 KiB, one region, flushed before, one pass; the five regions", f"{min(OCMBW['region']):.1f} to {max(OCMBW['region']):.1f}", "-"],
                 ["OCM, the five home nodes", "1.25 MiB, all five regions, flushed before; read one pass, write 8 passes", fmt(OCMBW["all5"]), fmt(OCMBW["write"])],
                 _lv(33554432)],
                f"Run 3 only, best of 3 reps, GB = 1e9 bytes. The first row is the core's own limit, computed from the Arm C1-Nano TRM's path widths (\"Read path: dual 128-bit\", \"Write path: 128-bit\") and the measured clock, not a bandwidth row; the L1 row reaches {100 * [d for d in ONE if d['size'] == 16384][0]['read'] / (32 * CORE_GHZ):.0f} % of the read limit and every row from 2 MiB up sits on the write limit. The level is read from the capacities, a hypothesis: no bandwidth row carries counters that say which level served it. The DRAM-address rows are table 4.3's (many warm passes over one buffer); the OCM rows are table 4.6's (the buffer flushed from the core caches before the timed passes), so the two methods differ. Read is set by the serving level; write is the core's 128-bit write path ({16 * CORE_GHZ:.1f} GB/s) at every DRAM-address footprint and {OCMBW['write']:.1f} GB/s to OCM. The 256 KiB chase counts {[d for d in LV4 if d['size'] == 262144][0]['l3']:.2f} L3 read refills per load (table 4.1), so that row is mostly mesh service.")
    # T6 attribution
    t6 = table(["Row", "Own node, run 3", "Other four, mean", "Own / others", "Own node, run 2 (dense)", "Run 3 / run 2 own"],
               [[f"OCM{r} chase, CPU {c}", f"{ATTR[(c, r)]['own']:,}", f"{ATTR[(c, r)]['others_mean']:,.0f}", fmt(ATTR[(c, r)]["ratio"], 1), f"{ATTR2[(c, r)]['own']:,}", fmt(ATTR[(c, r)]["own"] / ATTR2[(c, r)]["own"], 2)] for c in (2, 4, 6, 8) for r in range(5)],
               "Requests received per home node (hns_pocq_reqs_recvd_all) over the whole command [cmn-counts.csv]. A sparse row builds 8 chains, fills the region and flushes 7 times, so most of its requests are not the 448 timed loads.")
    # T7 run 3 vs run 2 summary
    lat_within = sorted(abs(d["pct"]) for d in LAT_SAME); bw_within = sorted(abs(d["pct"]) for d in BW_SAME)
    t7 = table(["File", "Row", "Run 2", "Run 3", "Run 3 vs run 2"],
               [[d["file"], d["what"], fmt(d["run2"], 3 if d["unit"] == "ns" else 1), fmt(d["run3"], 3 if d["unit"] == "ns" else 1), f"{d['pct']:+.2f} %"] for d in COMPARE if abs(d["pct"]) >= 1.0 and d["same"]],
               f"Only the rows that moved 1 % or more are listed. {len(LAT_SAME)} latency rows with the same chain in both runs: {sum(1 for p in lat_within if p < 1)} within 1 %, the largest change {lat_within[-1]:.2f} %. {len(BW_SAME)} bandwidth rows: {sum(1 for p in bw_within if p < 1)} within 1 %, the largest {bw_within[-1]:.2f} %. The 20 sparse per-region rows and the 4 sparse all-five rows are not in this table or count; their chains differ from run 2's (table 4.2 has them).")

    # figures
    f_levels = line_chart([dict(name="run 2 (8ae533c)", color=C["muted"], pts=[(d["size"], d["ns2"]) for d in LV4 if d["kind"] != "flushed"], short="run 2", dy=14),
                           dict(name="run 3 (ba834c0)", color=C["s1"], pts=[(d["size"], d["ns"], f"run 3 {kib(d['size'])} {d['kind']}: {d['ns']:.3f} ns") for d in LV4 if d["kind"] != "flushed"], short="run 3")],
                          marks=((32768, "L1 32 KiB"), (131072, "L2 128 KiB"), (262144, "L3 256 KiB" + L3_TAG), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 60), ticks_y=[0, 10, 20, 30, 40, 50, 60])
    f_map = mesh_map(left=[("L1, 32 KiB per core", f"{LV4[0]['ns']:.1f} ns (4 KiB chase)", "#e9f1fb"),
                           ("L2, 128 KiB per DSU", f"{[d for d in LV4 if d['size'] == 131072][0]['ns']:.1f} ns (128 KiB chase)", "#e9f1fb"),
                           ("L3, 256 KiB per DSU" + (": no data on this run" if L3_SF else ""), f"{[d for d in LV4 if d['size'] == 196608][0]['ns']:.1f} ns at 192 KiB " + ("(L2 hits mixed with SLC reads)" if L3_SF else "(mixed L2, L3 and mesh)"), "#e9f1fb"),
                           ("mesh: to the home node that owns the line", "the grid on the right; one hop per crosspoint", "#f9f9f7"),
                           (["5 home nodes (HN-S)", "SLC 768 KiB each (12 ways), \"L4\" cache", "OCM 256 KiB each (4 ways), addressable SRAM"], f"{SLC[2]['best']:.1f} ns (2 MiB fresh chain, in the SLC)", "#fdeee6"),
                           ("DRAM, behind the home node (emulator)", f"{[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f} ns (8 MiB flushed)", "#f1f1ee")],
                     node_labels={NODE_OF_REGION[r]: [f"CPU 2: {OCM[2][r]['best']:.1f} ns"] for r in range(5)},
                     paths=[(1, NODE_OF_REGION[r], C["s2"], "") for r in range(5)])
    rows = []
    for c in (2, 4, 6, 8):
        for r in sorted(range(5), key=lambda r: (OCM[c][r]["dist"], r)):
            rows.append(dict(label=f"CPU {c}, OCM{r} ({OCM[c][r]['dist']} xp)", a=OCM2[c][r]["best"], b=OCM[c][r]["best"]))
    f_ocm = dumbbell(rows, names=("run 2 dense best", "run 3 sparse best"), xlim=(18, 30))
    srows = []
    for c in (2, 4, 6, 8):
        for r in sorted(range(5), key=lambda r: (OCM[c][r]["dist"], r)):
            srows.append(dict(label=f"CPU {c}, OCM{r} ({OCM[c][r]['dist']} xp)", vals=[p["ns"] for p in OCM[c][r]["passes"]], best=OCM[c][r]["best"], extra=[(OCM2[c][r]["best"], C["muted"], "run 2 dense best")]))
    f_spread = strip(srows, markers=((C["muted"], "run 2 dense best (square)"),), xlim=(18, 40))
    arows = [dict(label=f"CPU {c}: all five, sparse (320 hops)", vals=ALL5S[c]["passes"], best=ALL5S[c]["best"], extra=[(ALL5D[c]["best"], C["s2"], "dense control best"), (ALL5_2[c]["best"], C["muted"], "run 2 dense best")]) for c in (2, 4, 6, 8)]
    f_all5 = strip(arows, markers=((C["s2"], "dense control, run 3 (square)"), (C["muted"], "run 2 dense (square)")), xlim=(24, 30))
    f_bw1 = line_chart([dict(name="read", color=C["s1"], pts=[(d["size"], d["read"]) for d in ONE]), dict(name="write", color=C["s2"], pts=[(d["size"], d["write"]) for d in ONE]),
                        dict(name="copy (read + write bytes)", color=C["s3"], pts=[(d["size"], d["copy"]) for d in ONE], short="copy")],
                       ylabel="GB/s, one thread on CPU 2", marks=((32768, "L1 32 KiB"), (131072, "L2 128 KiB"), (262144, "L3 256 KiB" + L3_TAG), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 65), ticks_y=[0, 10, 20, 30, 40, 50, 60])
    wrows = [dict(label=f"{'CPU 2+3' if d['threads'] == 2 else 'CPUs 2,4,6,8' if d['threads'] == 4 else 'CPUs 2 to 9'} write {kib(d['size'])}", a=d["run2"], b=d["run3"]) for d in PAIR + PERDSU + ALL8 if d["kernel"] == "write"]
    wrows += [dict(label=f"writers {p['cpus'].replace('-', ',')} (DSUs {','.join(map(str, p['dsus']))})", a=p["run2"], b=p["run3"]) for p in PLACE]
    f_write = dumbbell(wrows, unit="GB/s", names=("run 2", "run 3"))
    brows = [dict(label=f"OCM{r} from CPU 2 ({dist(2, NODE_OF_REGION[r])} xp)", v=OCMBW["region"][r]) for r in range(5)] + [dict(label="all five from CPU 2", v=OCMBW["all5"]), dict(label="OCM1 to 4 from four CPUs", v=OCMBW["four"], color=C["s3"]), dict(label="streaming write, all five", v=OCMBW["write"], color=C["s2"])]
    f_ocmbw = bars_h(brows, xlim=70)
    crow = CMN4["ocm-region1-cpu2"]
    f_cmn = bars_h([dict(label=f"node {n} (OCM{NODES[n][2]})", v=crow["node"][n], color=C["s2"] if n == 160 else C["s1"]) for n in NODES], unit="requests")

    ratio_lo, ratio_hi = min(a["ratio"] for a in ATTR.values()), max(a["ratio"] for a in ATTR.values())
    wr = [d for d in ONE]; w16 = [d for d in ONE if d["size"] == 16384][0]
    write_ns_more = [(1 / d["write"] - 1 / d["write2"]) * d["size"] for d in ONE if d["size"] <= 262144]   # ns more per pass
    extra_open = (f"""<li><span class='ok'>boot A</span> The DRAM chase time of about 52 ns (the 8 MiB flushed row and the 32 MiB chain walked once) is a demand miss on every load: on boot A those rows count {R4A['flushed']['pf']:.3f} and {R4A['l32m']['pf']:.3f} L2 prefetch refills, {R4A['flushed']['l1pf']:.3f} and {R4A['l32m']['l1pf']:.3f} L1 prefetch refills, and {R4A['flushed']['l3']:.3f} and {R4A['l32m']['l3']:.3f} L3 read refills per load, at {R4A['flushed']['ns']:.1f} and {R4A['l32m']['ns']:.1f} ns [latency-dram-flushed.csv, latency-dram-large.csv of membench-jibin-005]. Whether the emulator's memory model sets that time, and what the silicon's DRAM would give, is Insufficient data (Jesse's README: the AP DRAM on this image is an embedded emulator memory, not LPDDR5X).</li>
<li><span class='plan'>planned</span> The one-core DRAM read of {[d for d in ONE if d['size'] == 33554432][0]['read']:.1f} GB/s (table 4.3) against {[d for d in ONE if d['size'] == 16384][0]['read']:.1f} GB/s from L1: whether the plain read loop keeps too few lines in flight is run 5's question (bandwidth read variants with software prefetch and two streams, phase G7), which boot A did not carry (it ran commit e8e4580) and which runs on boot C, the first boot with the prefetchers on and the run 5 script.{read_note}</li>
<li><span class='gap'>open</span> The L1 read rate of {[d for d in ONE if d['size'] == 16384][0]['read']:.1f} GB/s, {100 * [d for d in ONE if d['size'] == 16384][0]['read'] / (32 * CORE_GHZ):.0f} % of the dual 128-bit read path, has no scheduled test; the shortfall is a property of the test loop or the core, and no row separates the two.{g8_note}</li>""") if R4A else ""
    w_deltas = ", ".join(f"{d['delta']:.1f}" for d in R4A["write"]) if R4A else ""
    body = f"""
<div class="short"><p><b>Short version.</b> Run 3 repeats run 2 on the same firmware, and the C1-Nano cache, SLC, DRAM and multi-core numbers hold within 2.6 %. The one fix in this run, sparse OCM chains, did not give tighter per-region OCM latencies, so the dense all-five control row is the OCM chase row to quote. The level map for one core is unchanged: L1 {LV4[0]['ns']:.1f} ns, L2 {[d for d in LV4 if d['size'] == 131072][0]['ns']:.1f} ns, SLC {SLC[2]['best']:.1f} ns, DRAM {[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f} ns flushed.</p></div>
<ul>
<li><b>Repeatability.</b> Of {len(LAT_SAME)} latency rows with the same chain in both runs, {sum(1 for p in lat_within if p < 1)} agree within 1 % and the largest change is {lat_within[-1]:.2f} %. Of {len(BW_SAME)} bandwidth rows, {sum(1 for p in bw_within if p < 1)} agree within 1 % and the largest change is {bw_within[-1]:.2f} % (section 4.8).</li>
<li><b>Sparse OCM chains.</b> The 20 sparse per-region bests read {statistics.mean(sparse_minus_dense):+.2f} ns on average against run 2's dense rows, and their 7 passes spread {min(spread):.1f} to {max(spread):.1f} ns. The distance order still holds: {DIST[1]['mean']:.2f}, {DIST[3]['mean']:.2f} and {DIST[5]['mean']:.2f} ns at 1, 3 and 5 crosspoints (section 6).</li>
<li><b>Dense control.</b> The dense all-five OCM chase repeats run 2 within {max(abs(x) for x in dense_vs_run2):.2f} ns, with 1.00 refills per load at every level: {min(ALL5D[c]['best'] for c in ALL5D):.1f} to {max(ALL5D[c]['best'] for c in ALL5D):.1f} ns from the four DSUs.</li>
<li><b>Bandwidth.</b> One core reads {[d for d in ONE if d['size'] == 33554432][0]['read']:.1f} GB/s and writes {[d for d in ONE if d['size'] == 33554432][0]['write']:.1f} GB/s from DRAM, eight cores write {max(d['run3'] for d in ALL8 if d['kernel'] == 'write'):.0f} GB/s, one core reads OCM at {min(OCMBW['region']):.1f} to {max(OCMBW['region']):.1f} GB/s per region (sections 7 to 9).</li>
</ul>

<h2 id="words">1. Words used here</h2>
{words(WORDS_COMMON)}

<h2 id="run">2. The run and the platform</h2>
{PLATFORM}

<h3 id="changes">2.1 What changed from run 2 to run 3</h3>
<p><b>The platform did not change.</b> Run 3 ran on run 2's image copy, firmware (SCP 0.48.0-nopcie.1, TF-A 0.35.0), kernel, OCM module, huge pages and CPU layout. Two changes in Jesse's init do not touch the measurements: a hang guard that would have killed the scripts after 12 chip seconds (it did not fire) and room for 256 files in the results window [Jesse's run 3 README, Read first]. So a difference between the two runs comes from the code or from run-to-run noise, not from the firmware, unlike the run 1 to run 2 comparison.</p>
<p><b>The code changed from commit 8ae533c to ba834c0.</b> In the cache test:</p>
<ul>
<li><b>Sparse chains on the OCM rows.</b> The 20 per-region rows walk a sparse chain (one member line per 4 KiB page, 64 hops per pass) for {FRESH4} fresh passes ({int(FRESH4) - 1} timed) instead of run 2's dense chain (4,096 hops) for {FRESH2} fresh passes ({int(FRESH2) - 1} timed). The purpose was to keep prefetched neighbours out of the chain. The four all-five rows are sparse too, 320 hops per pass, <b>under the same file names as run 2's dense all-five rows</b> (latency-ocm-all5-cpuN.csv), so those files are not comparable by name.</li>
<li><b>Four new dense all-five control rows</b> (latency-ocm-all5-dense-cpuN.csv) run run 2's all-five arguments unchanged. These are the rows that compare with run 2's all-five rows (table 4.8 pairs them).</li>
<li><b>Counter validity.</b> Every counter row carries a perf_cov column (running time over enabled time of the counter group), a failed counter call marks the row "-" with a "# perf:" reason, and the chase loop handles any hop count (a 64-hop pass needs that). Each latency command also prints its clock-bracket overhead (32 empty timed brackets) as a comment line.</li>
<li><b>The bandwidth program</b> gained a switch in its pass loop to call the CME kernels. It is the likely cause of the 7.7 to 8.0 ns more per pass on the one-core 16 to 256 KiB write rows (section 7); the flags of every repeated bandwidth row are unchanged.</li>
<li><b>Scripts.</b> run_all.sh runs run_asimov.sh and then the new run_cme.sh into one directory; the shared lib_run.sh counts failed commands and returns a non-zero exit code when any failed (run 2's script returned the last rm's status).</li>
</ul>
<p><b>What that means for the rows.</b> Run 2 ran {len(CMD2)} commands and wrote {FILES2} CSV files; run 3 ran {len(CMD4)} commands ({len(CMD4_CACHE)} in the cache test, {len(CMD4) - len(CMD4_CACHE)} in the CME test) and wrote {FILES4}. Of the cache test's {len(CMD4_CACHE)} commands, {REPEATED} have the same command line as a run 2 command ({REPEATED_NOLABEL} with the counter labels set aside, the four dense controls among them), {SPARSE_CMDS} use the new sparse chains and {NEW_DENSE} are the new dense controls. Chip time rose from 1.630 s to 2.918 s, of which the CME test is about 1.28 s [Jesse's READMEs of runs 2 and 3].</p>

<h2 id="map">3. The hemisphere map</h2>
<p>The left column is the path one load takes from CPU 2 outward (cluster caches, then the mesh to the home node, with DRAM behind it), with this run's chase time at the footprint that reads from each level. The grid is the mesh as the kernel's debugfs map prints it [sysinfo.txt, "arm-cmn mesh map"], with the five home nodes and the five DSU ports on their crosspoints. The dashed paths run from CPU 2's port to each OCM home node, horizontal first (a simplification: the real route is the mesh's choice). The label under each home node is CPU 2's best sparse chase of that region.</p>
{fig(f_map, f"From CPU 2, OCM reads {min(OCM[2][r]['best'] for r in range(5)):.1f} to {max(OCM[2][r]['best'] for r in range(5)):.1f} ns by region, the SLC {SLC[2]['best']:.1f} ns and flushed DRAM {[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f} ns.", "Hover a box or a dot for its details. The crosspoint of each box comes from the node ids and was checked against the map text by this script [sysinfo.txt].")}

<h2 id="tables">4. Summary tables</h2>
<h3 id="t41">4.1 Latency by level, CPU 2, run 3 against run 2</h3>{t1}
<h3 id="t42">4.2 OCM latency by region, from four CPUs</h3>{t2}{t2b}
<h3 id="t43">4.3 One-core bandwidth by footprint, CPU 2</h3>{t3}
<ul>
<li><b>The write rows are the full width of the core's write path.</b> The C1-Nano has one 128-bit write path from the core to its L1 memory system [Arm C1-Nano TRM, "Write path"], which is 16 bytes per cycle. The latency rows put the core at {CORE_GHZ:.1f} GHz ({_p4k['cyc']:.2f} cycles per {_p4k['ns']:.3f} ns at 4 KiB), so the path carries {16 * CORE_GHZ:.1f} GB/s. Every write row from 2 MiB to 32 MiB reads {min(d['write'] for d in ONE if d['size'] >= 2097152):.2f} to {max(d['write'] for d in ONE):.2f} GB/s, so the store stream runs at the path's width at every footprint, including DRAM; the memory behind it is not the limit for one core.</li>
<li><b>Note: the rows below 2 MiB fall short of the path's width because of the test program, not the core.</b> Each pass of the store kernel carries a fixed cost of about 30 ns est. (the call into the kernel, the loop around it and the drain of its last stores; derived from these rows as the time per pass above the 32.0 GB/s time). A 16 KiB pass lasts 512 ns, so that cost is 6 % of it and the row reads {[d for d in ONE if d['size'] == 16384][0]['write']:.1f} GB/s; a 2 MiB pass lasts 65 us and the cost is below 0.05 %. The same per-pass cost shapes the copy rows.</li>
<li><b>The read rows are not.</b> The read path is dual 128-bit, 32 bytes per cycle or {32 * CORE_GHZ:.1f} GB/s. The 16 KiB row, in L1, reads {[d for d in ONE if d['size'] == 16384][0]['read']:.1f} GB/s ({100 * [d for d in ONE if d['size'] == 16384][0]['read'] / (32 * CORE_GHZ):.0f} % of the path); every larger row is set by the level that serves it, down to {[d for d in ONE if d['size'] == 33554432][0]['read']:.1f} GB/s from DRAM.</li>
</ul>
<h3 id="t44">4.4 Multi-core DRAM bandwidth</h3>{t4}{t4_note}
<h3 id="t45">4.5 Writer placement</h3>{t4b}
<h3 id="t46">4.6 OCM bandwidth</h3>{t5}
<h3 id="t461">4.6.1 One core, read and write by level (tables 4.3 and 4.6 combined)</h3>{t5b}
<h3 id="t47">4.7 Home-node attribution of the 20 sparse per-region rows</h3>{t6}
<h3 id="t48">4.8 Every row that moved 1 % or more between run 2 and run 3</h3>{t7}

<h2 id="f-levels">5. Latency by level, CPU 2</h2>
{fig(f_levels, f"Run 3 lies on run 2 at every footprint: the largest change among the {len(LAT_SAME)} same-chain rows is {lat_within[-1]:.2f} %.", f"Steps at 48 KiB (past L1), 192 KiB (past L2) and 4 to 16 MiB (past the SLC) [table 4.1]. The 8 MiB flushed row, not drawn, reads {[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f} ns, the DRAM load-to-use time with every cache missed.")}

<h2 id="f-ocm">6. OCM latency by region: sparse chains against run 2's dense ones</h2>
<p>Run 2's per-region rows carried prefetched lines (0.76 to 0.95 L3 read refills per load). Run 3 walks a sparse chain instead: one member line per 4 KiB page, so a prefetched neighbour is never a member. The rows are grouped by CPU and ordered by distance within each CPU.</p>
{fig(f_ocm, f"The sparse bests read higher than the dense ones in {sum(1 for x in sparse_minus_dense if x > 0)} of 20 cells, by {statistics.mean(sparse_minus_dense):+.2f} ns on average ({min(sparse_minus_dense):+.2f} to {max(sparse_minus_dense):+.2f}).", f"Within each CPU the order by distance {'holds' if ordered_within_cpu else 'does not hold'} in run 3. By distance the sparse means are {DIST[1]['mean']:.2f}, {DIST[3]['mean']:.2f} and {DIST[5]['mean']:.2f} ns at 1, 3 and 5 crosspoints (run 2 dense: {DIST[1]['mean2']:.2f}, {DIST[3]['mean2']:.2f}, {DIST[5]['mean2']:.2f}), about {(DIST[5]['mean'] - DIST[1]['mean']) / 4:.1f} ns per extra crosspoint [table 4.2].")}
{fig(f_spread, f"The 7 passes of a sparse row spread {min(spread):.1f} to {max(spread):.1f} ns, and the best sits {min(best_below_median):.1f} to {max(best_below_median):.1f} ns below the row's median.", f"A 64-hop pass reads in steps of 1/64 ns and carries the clock bracket (39 to 41 ns a pass, 0.6 ns a hop) and the L1 data TLB misses a sparse chain makes (a pass never revisits a page; the 16-entry L1 TLB covers 64 KiB). So a sparse pass time is the complete-call elapsed time divided by 64 hops, and how much of it is demand-only OCM latency is Insufficient data [latency-ocm-region*-cpu*.csv].")}
{fig(f_all5, f"The all-five pair is the cleaner test: the sparse all-five bests read {min(sparse_vs_dense_all5):+.2f} to {max(sparse_vs_dense_all5):+.2f} ns against the dense controls, and the dense controls repeat run 2 within {max(abs(x) for x in dense_vs_run2):.2f} ns.", f"The dense controls count {min(min(ALL5D[c]['l2']) for c in ALL5D):.4f} to {max(max(ALL5D[c]['l2']) for c in ALL5D):.4f} L2 and {min(min(ALL5D[c]['l3']) for c in ALL5D):.4f} to {max(max(ALL5D[c]['l3']) for c in ALL5D):.4f} L3 refills per load: one fill per load at each level. The counters cannot tell a demand fill from a prefetch fill, so whether every load was a demand miss is Insufficient data. The sparse all-five rows count {min(min(ALL5S[c]['l2']) for c in ALL5S):.2f} to {max(max(ALL5S[c]['l2']) for c in ALL5S):.2f} L2 refills per load [latency-ocm-all5*-cpu*.csv].")}
<p><b>What the sparse passes' refill counts show.</b> The sparse per-region passes count {min(sp_l2):.2f} to {max(sp_l2):.2f} L2 refills and {min(sp_l3):.2f} to {max(sp_l3):.2f} L3 read refills per load (run 2's dense rows: {min(d2_l2):.2f} to {max(d2_l2):.2f} and {min(d2_l3):.2f} to {max(d2_l3):.2f}). Within a row, a slower pass carries more L2 refills (correlation {CORR_L2:+.2f}) and fewer L3 refills ({CORR_L3:+.2f}). <span class="hyp">hypothesis</span> The extra L2 refills are neighbouring lines the prefetcher fetches and the chain never uses; the L3 count below 1 does not behave like prefetched hits, which would make a pass faster. A per-pass count of prefetch refills would test it: the C1-Nano's L2D_CACHE_REFILL_HWPRF (0x81BD, L2 refills made by hardware prefetchers) and its per-prefetcher refill events (0x00D9 correlating, 0x00DA spatial, 0x00DB offset, 0x010F stride, 0x0110 TLB prefetcher) [Arm C1-Nano TRM, event list]. Whether each counts on this image has to be checked by its counts, since the kernel opens any event number.</p>
<p><span class="gap">Insufficient data</span> How much of the sparse excess is the clock bracket, how much the L1 TLB misses and how much the extra L2 refills cannot be separated from these rows, and neither the dense nor the sparse rows give a demand-only OCM latency. A boot with the prefetchers disabled would remove the prefetch term, and larger OCM pages the translation term; each addresses one factor, and only both together would give a demand-only number.</p>

<h2 id="f-bw1">7. One-core bandwidth by level</h2>
{fig(f_bw1, f"Read falls from {[d for d in ONE if d['size'] == 16384][0]['read']:.1f} GB/s in L1 to {[d for d in ONE if d['size'] == 33554432][0]['read']:.1f} GB/s from DRAM; write holds {min(d['write'] for d in ONE):.1f} to {max(d['write'] for d in ONE):.1f} GB/s at every footprint.", f"The one-core write rows of 16 to 256 KiB each take {min(write_ns_more):.1f} to {max(write_ns_more):.1f} ns more per pass than in run 2 ({pct(w16['write'], w16['write2'])} at 16 KiB), about 16 core cycles. <span class='hyp'>hypothesis</span> The rebuilt bandwidth program's new CME switch in its pass loop costs that; Jesse's pre-run disassembly estimate was 4 to 15 cycles [Jesse's run 3 README, Cache test against round two]. The 48 KiB and larger reads and copies agree with run 2 within 1.3 % [table 4.3].")}

<h2 id="f-write">8. Multi-core DRAM writes and writer placement</h2>
{fig(f_write, f"Every multi-core write row repeats run 2 within {max(abs(d['pct']) for d in BW_SAME if 'write' in d['what'] and d['run3'] > 40):.2f} %, on the same firmware.", f"One DSU with two writers still gives {PAIR_W:.1f} GB/s, four DSUs {max(d['run3'] for d in PERDSU if d['kernel'] == 'write'):.1f} GB/s and eight cores {max(d['run3'] for d in ALL8 if d['kernel'] == 'write'):.1f} GB/s [tables 4.4 and 4.5]. The firmware dependence of these rows was shown by run 2's control run (SCP 0.34.0 gave 87 to 89 GB/s for the multi-DSU rows); run 3 adds no firmware change.")}

<h2 id="f-ocmbw">9. OCM bandwidth</h2>
{fig(f_ocmbw, f"One core reads an OCM region at {min(OCMBW['region']):.1f} to {max(OCMBW['region']):.1f} GB/s and writes all five at {OCMBW['write']:.1f} GB/s; four cores on four regions read {OCMBW['four']:.1f} GB/s together.", f"The three-crosspoint regions (OCM3, OCM4) read lowest from CPU 2. All rows within {max(abs(d['pct']) for d in BW_SAME if 'ocm' in d['file']):.2f} % of run 2 [table 4.6].")}

<h2 id="f-cmn">10. Mesh counters</h2>
{fig(f_cmn, f"A sparse region row still lands on one home node: OCM1's row from CPU 2 put {ATTR[(2, 1)]['own']:,} requests on node 160 and {ATTR[(2, 1)]['others_mean']:,.0f} on average on each other node.", f"All 20 sparse rows pass this test (own node {ratio_lo:.1f} to {ratio_hi:.1f} times the others) [table 4.7]. The own-node counts are {min(own_ratio_vs_run2):.2f} to {max(own_ratio_vs_run2):.2f} times run 2's dense rows and the other nodes {min(oth_ratio_vs_run2):.2f} to {max(oth_ratio_vs_run2):.2f} times, so the sparse rows' counts are not comparable with run 2's under the same labels: a sparse row fills its 4,096 lines once but flushes them 7 times for 448 timed loads. The dense all-five controls repeat run 2's all-five counts node for node within {100 * min(dense_nodes_vs_run2):+.1f} % to {100 * max(dense_nodes_vs_run2):+.1f} %.")}
<p><b>Background and the counters' cost.</b> Each control row (a 4 KiB chase on 4 KiB pages) put {min(BG):,} to {max(BG):,} requests on each node, the run's background traffic. CPU 2's counted and uncounted control commands' helper times differ by {COST['counted'] - COST['uncounted']:,} ns (run 2: {COST['counted2'] - COST['uncounted2']:,} ns), which is the cost of the counter helper, mostly its own sysfs work; the counted command itself lived {COST['child_c'] - COST['child_u']:,} ns longer [cmn-counts.csv].</p>

<h2 id="open">11. Open items</h2>
<p class="note">Labels: <span class="plan">planned</span> run 4 (follow-up-run-plan.md) measures it; <span class="gap">open</span> no test scheduled yet{('; <span class="ok">boot A</span> run 4 boot A (membench-jibin-005, 2026-11-04) answered it or part of it, read from its files by gen_run4.py and quoted here from run4-bootA-facts.json') if R4A else ""}.</p>
<ul>
<li><span class="plan">planned</span> Cells at the same crosspoint count differ by up to {max(DIST_PCT[k]['run2'] for k in (1, 3)):.0f} % in both runs (run 2 dense, {DIST[1]['lo2']:.2f} to {DIST[1]['hi2']:.2f} ns at 1 crosspoint; table 4.2). So the hop count alone does not set the latency of a route, and the per-crosspoint figure in section 6 is a mean over routes. Whether the same cell is fast or slow in both runs is unresolved: within a distance the two runs' cell differences correlate only {DIST_RESID_CORR:.2f}. What else in a route costs time, or whether the spread is run-to-run variation of each cell, is Insufficient data; a chase from every CPU to every node on one boot, with each cell repeated, would separate the two. Run 4's phase G6 runs all 20 cells again on one boot under the mesh's crosspoint counters, which record the outgoing data-flit directions at the DSU's and the node's crosspoint over the whole command (the chain build, the flushes and unrelated traffic included); they do not identify the read-request route or the response's last link, so the hop counts stay coordinate assumptions, and a second sample of every cell is what the phase gives for the spread question; a fit of the 20 cells already attributes none of the spread to the node or the CPU, and puts an X hop at 1.3 to 1.7 ns against 0.8 to 0.9 for a Y hop, a reading to be tested on that data.{(f" <span class='ok'>boot A</span> That second sample exists: the same ten cells (CPUs 2 and 8, dense chain) measured twice on one boot, in phase G2 and again in G6 under the counters, differ by {R4A['same_boot_repeat'][0]:+.2f} to {R4A['same_boot_repeat'][1]:+.2f} ns, and within a distance the two samples' cell residuals correlate only {R4A['resid']['g6_vs_g2_same_boot']:.2f} with each other, {R4A['resid']['g2_vs_run2']:.2f} and {R4A['resid']['g6_vs_run2']:.2f} with run 2's cells, and {R4A['resid']['sparse_vs_run3']:.2f} between boot A's and run 3's sparse rows. So most of the within-distance spread is pass-to-pass variation of a cell rather than a fixed cost of its route; boot B gives a third sample.{route_note} The fit over the 20 counted cells gives {R4A['fit']['bx']:.2f} ns per X hop against {R4A['fit']['by']:.2f} per Y hop with a residual of {R4A['fit']['rms']:.2f} ns rms, so the two costs are not separated there, and the data flits leave each end along the X direction first in {R4A['xfirst'][0]} of 20 cells at the DSU and {R4A['xfirst'][1]} of 20 at the node [asimov-c1nano-run4.html, sections 6 and 8].") if R4A else ""}</li>
<li><span class="plan">planned</span> The per-region excess of the sparse rows over the dense ones is the clock bracket plus L1 TLB misses plus prefetcher traffic; which dominates is Insufficient data (section 6).{(f" <span class='ok'>boot A</span> The parts are now counted: a sparse hop takes {R4A['sparse_l1tlb_mean'][0]:.2f} to {R4A['sparse_l1tlb_mean'][1]:.2f} L1 TLB refills ({R4A['sparse_l1tlb'][0]:.2f} to {R4A['sparse_l1tlb'][1]:.2f} by pass) and {R4A['sparse_walk_mean'][0]:.2f} to {R4A['sparse_walk_mean'][1]:.2f} table walks (up to {R4A['sparse_walk'][1]:.1f} in one pass), and draws {R4A['sparse_pf_mean'][0]:.1f} to {R4A['sparse_pf_mean'][1]:.1f} L2 prefetch refills (0x81BD) against {R4A['dense_pf_mean'][0]:.2f} to {R4A['dense_pf_mean'][1]:.2f} for a dense hop; the sparse rows read {R4A['sparse_minus_dense'][0]:.1f} to {R4A['sparse_minus_dense'][1]:.1f} ns above the dense ones on that boot. The vary chain (one line per page at a changing offset) draws prefetches like the sparse one yet runs {-R4A['vary_minus_sparse_med'][1]:.1f} to {-R4A['vary_minus_sparse_med'][0]:.1f} ns faster by median in {R4A['vary_faster_med']} of 10 cells, so the fixed line offset is not what the prefetcher reacts to [asimov-c1nano-run4.html, sections 6 and 7]. What each part costs in ns waits on boot B (prefetchers off) and boot C (larger translation entries).{parts_note}") if R4A else ""}</li>
<li>{'<span class="ok">boot A</span>' if R4A else '<span class="plan">planned</span>'} The 7.7 to 8.0 ns per pass added to the small one-core write rows is the new CME switch in the bandwidth program's pass loop. Run 4 tests it: phase G5 runs the same rows with run 3's program and with run 2's program (bandwidth_r2, no CME path) on one boot (follow-up-run-plan.md).{(f" Answered: on one boot run 3's program takes {w_deltas} ns more per pass than run 2's at {', '.join(kib(d['size']) for d in R4A['write'])} (derived from the GB/s columns of bandwidth-write-small.csv and bandwidth-write-small-r2prog.csv; the elapsed_s column is printed at 1 us resolution). The cost is the program's, as this item said.") if R4A else ""}</li>
<li><span class="plan">planned</span> The OCM latency of a single load, with nothing helping or hurting it, is not yet measured. Two things in the per-region rows are not the memory's own cost. First, the hardware prefetcher fetches some lines before the chase asks for them, so those loads finish early. Second, the OCM is mapped to the program in 4 KiB pages, so a sparse pass touches a new page at every hop and pays for address translation; "larger pages" means mapping the same 256 KiB regions through 2 MiB or 64 KiB translation entries, so one entry covers a region, not a larger OCM. Run 4 addresses both: boot A counts the prefetched fills and the translation refills, boot B turns the prefetchers off, boot C maps the OCM in larger translation entries if the /dev/ocm driver can, and boot D does both (follow-up-run-plan.md, section 4).{(f" <span class='ok'>boot A</span> The counting part is done: the fills above one per hop on the OCM rows are refills a hardware prefetcher made into the L2 (0x81BD), and on every OCM row the L2 refills it does not count equal the L3 read refills within {R4A['rest_minus_l3_max']:.2f} per load. At 192 KiB (table 4.1) the L2 refills not made by prefetch, {R4A['l192']['l2'] - R4A['l192']['pf']:.3f} per load, equal the L3 read refills, {R4A['l192']['l3']:.3f}, so the reading that 42 % of those loads hit the L2 stands as a difference of counts; {hit_note} The OCM latency with nothing helping or hurting the load waits on boots B, C and D, none of which has run [asimov-c1nano-run4.html, section 6].") if R4A else ""}</li>
{extra_open}<li><span class="gap">open</span> The scratchpad memory (SPM) phase is still postponed (no /dev/asimov-spm on this image).</li>
</ul>

<h2 id="sources">12. Sources</h2>
<ul>
<li><a href="results/membench-jibin-004/results/19700101T000000Z/">results/membench-jibin-004/</a> (run 3, commit ba834c0, 2026-11-03) and <a href="results/membench-jibin-002/results/19700101T000000Z/">results/membench-jibin-002/</a> (run 2, commit 8ae533c, 2026-11-02): every number on this page is read from their CSV files by <a href="gen_run3.py">gen_run3.py</a>.</li>
<li>Jesse's README files, <a href="results/membench-jibin-004/README.md">run 3</a> and <a href="results/membench-jibin-002/README.md">run 2</a>: platform facts, chip time, firmware, the hang guard, the disassembly estimate for the bandwidth program's pass loop.</li>
<li>The companion page <a href="asimov-cme-perf.html">asimov-cme-perf.html</a>: the same loads and stores through the CME.</li>
</ul>
"""
    toc = [("words", "1. Words used here"), ("run", "2. The run and the platform", [("changes", "2.1 What changed from run 2 to run 3")]), ("map", "3. The hemisphere map"),
           ("tables", "4. Summary tables", [("t41", "4.1 Latency by level"), ("t42", "4.2 OCM latency by region"), ("t43", "4.3 One-core bandwidth by footprint"), ("t44", "4.4 Multi-core DRAM bandwidth"),
                                             ("t45", "4.5 Writer placement"), ("t46", "4.6 OCM bandwidth"), ("t461", "4.6.1 One core, read and write by level"), ("t47", "4.7 Home-node attribution"), ("t48", "4.8 Rows that moved 1 % or more")]),
           ("f-levels", "5. Latency by level, CPU 2"), ("f-ocm", "6. OCM latency by region: sparse against dense"),
           ("f-bw1", "7. One-core bandwidth by level"), ("f-write", "8. Multi-core DRAM writes and writer placement"), ("f-ocmbw", "9. OCM bandwidth"), ("f-cmn", "10. Mesh counters"), ("open", "11. Open items"), ("sources", "12. Sources")]
    return page("Asimov C1-Nano Memory Performance, run 3", "Run membench-jibin-004 (cache-mem-perf ba834c0) on the GA13 Palladium, 2026-11-03, against run 2. Generated by gen_run3.py from the CSV files; nothing typed in by hand except the cited platform facts.", toc, body)

# ======================================================================= page 2: the CME
def cme_page():
    b_evict = (f" <span class='ok'>boot B</span> Supported: with the CME prefetcher off the chase reads {R4B['cme']['k4']:.2f} to {R4B['cme']['k64']:.2f} ns from 4 to 64 KiB and {R4B['cme']['k96']:.2f} ns at 96 KiB [asimov-cme-run4.html, section 8]." if R4B else "")
    b_l3 = (f" <span class='ok'>boots B, E</span> Boot B gives the CME L1 side: the chase reads {R4B['cme']['k4']:.2f} to {R4B['cme']['k64']:.2f} ns up to 64 KiB, within {R4B['cme']['k64'] - R4B['rt'][0]:.2f} ns of the {R4B['rt'][0]:.2f} ns register round trip. Boot E, with the L3 on, gives no L3 hit number through the CME: the prefetcher's fills set the chase time from 8 KiB on both boots ({R4E['cme']['k8']:.1f} ns at 8 KiB against {R4A['bootC']['cme']['k8']:.1f} ns with the L3 off) [asimov-cme-run4.html, sections 8 and 9]." if R4E and R4B else "")
    t1 = table(["Footprint", "Chase", "Core ns", "CME ns", "CME minus core", "CME outer refills (0x327E)", "CME inner refills (0x327D)", "Reads from (core)"],
               [[kib(d["size"]), d["kind"], fmt(d["core"], 3), fmt(d["ns"], 3), fmt(d["ns"] - d["core"], 1), f"{d['outer'][0]:.2f} to {d['outer'][1]:.2f}", f"{d['inner'][0]:.2f} to {d['inner'][1]:.2f}", level_name(d["size"], d["kind"])] for d in CLV],
               f"CPU 2 with CPU 3 offline, ns per load of the best rep, refills per load as the range over the timed reps [cme-latency-dram-*.csv, latency-dram-*.csv]. Controls: cme-roundtrip {RT_NS[0]:.3f} to {RT_NS[1]:.3f} ns per hop ({RT_CYC[0]:.1f} to {RT_CYC[1]:.1f} CME cycles) in all {len(RT)} reps; cme-call {CALL_NS[0]:.1f} to {CALL_NS[-2]:.1f} ns per call in {len(CALL) - 1} of {len(CALL)} reps, one rep {CALL_NS[-1]:.1f}.")
    t2 = table(["Region", "Distance from DSU 1", "Core best ns", "Core median", "CME best ns", "CME median", "CME outer refills", "CME read GB/s", "Core read GB/s"],
               [[f"OCM{r} (node {NODE_OF_REGION[r]})", f"{COCM[r]['dist']} xp", fmt(OCM[2][r]["best"], 3), fmt(OCM[2][r]["median"], 2), fmt(COCM[r]["best"], 3), fmt(COCM[r]["median"], 2), f"{COCM[r]['outer'][0]:.2f} to {COCM[r]['outer'][1]:.2f}", fmt(COCMBW["region"][r]), fmt(OCMBW["region"][r])] for r in range(5)]
               + [["All five, sparse (320 hops)", "", fmt(ALL5S[2]["best"], 3), fmt(ALL5S[2]["median"], 2), fmt(CALL5S["best"], 3), fmt(CALL5S["median"], 2), f"{CALL5S['outer'][0]:.2f} to {CALL5S['outer'][1]:.2f}", fmt(COCMBW["all5"]), fmt(OCMBW["all5"])],
                  ["All five, dense (20,480 hops)", "", fmt(ALL5D[2]["best"], 3), "", fmt(CALL5D["best"], 3), "", f"{CALL5D['outer'][0]:.2f} to {CALL5D['outer'][1]:.2f}", "", ""],
                  ["Streaming write, all five", "", "", "", "", "", "", fmt(COCMBW["write"]), fmt(OCMBW["write"])]],
               "CPU 2 and its CME, OCM mapped in 4 KiB pages. Latency: best and median of 7 sparse passes (2 dense). Bandwidth: best of 3 reps, one flushed pass [cme-latency-ocm-*.csv, cme-bandwidth-ocm-*.csv, and the core twins].")
    t3 = table(["Buffer", "Core read", "CME read", "Core write", "CME write", "Core copy", "CME copy", "Core capacity reading: read and write; copy"],
               [[kib(d["size"]), fmt(d["core_read"]), fmt(d["read"]), fmt(d["core_write"]), fmt(d["write"]), fmt(d["core_copy"]), fmt(d["copy"]),
                 f"{bw_level(d['size'])}; {bw_level(2 * d['size'])}"] for d in CBW],
               "GB/s, one thread on CPU 2 (CPU 3 offline for the CME rows), best of 3 reps, GB = 1e9 bytes [cme-bandwidth-dram-1core.csv, bandwidth-dram-1core.csv]. The 160 KiB and 1 MiB rows have no core twin. Copy reads one buffer and writes another of the same size, so its working set is twice the buffer size, and it counts bytes read plus written. The last column reads the core's capacities (hypothesis), for read and write at the buffer size and for copy at twice it; the CME's 64 KiB L1 is smaller than the core's L1 plus L2, and no bandwidth row carries counters, so the level that served a stream is not measured for either.")
    t3b = table(["Buffer", "read (256 B per instruction)", "ldr16 (64 B)", "ldr16 / read", "write (256 B)", "str16 (64 B)", "str16 / write"],
                [[kib(d["size"]), fmt(d["read"]), fmt(d["ldr16"]), fmt(d["ldr16"] / d["read"], 3), fmt(d["write"]), fmt(d["str16"]), fmt(d["str16"] / d["write"], 3)] for d in NARROW],
                "The 64-byte forms issue one vector per instruction and fold into 8 accumulators; the 256 B forms four vectors and 16 accumulators.")
    t4 = table(["Control", "Bound on ns per call", "What it includes"],
               [["read, 1 KiB per call, 4,096 calls", fmt(CALLB["read"], 1), "SMSTART, register save, 1 KiB of loads and the fold, SMSTOP"], ["write, 1 KiB per call, 4,096 calls", fmt(CALLB["write"], 1), "the same with 1 KiB of stores"]],
               f"elapsed time over calls, best rep [cme-bandwidth-call-cost.csv]. A 16 KiB read pass takes {PASS16:.0f} ns, so up to {100 * CALLB['read'] / PASS16:.0f} % of the 16 KiB read row is call cost; the write rows show no cost per pass (Jesse's fit: 0.01 ns per pass plus a fixed cost per rep).")
    t5 = table(["Row", "Own node, CME", "Own node, core", "CME / core", "Other four (CME), mean"],
               [[f"OCM{r} sparse chase", f"{ATTR_CME[r]['own']:,}", f"{ATTR[(2, r)]['own']:,}", fmt(CME_OCM_OWN_RATIO[r], 2), f"{ATTR_CME[r]['others_mean']:,.0f}"] for r in range(5)]
               + [[f"OCM{r} read", f"{ATTR_READ_CME[r]['own']:,}", f"{ATTR_READ[r]['own']:,}", fmt(CME_READ_OWN_RATIO[r], 2), f"{ATTR_READ_CME[r]['others_mean']:,.0f}"] for r in range(5)],
               f"Requests received at the region's home node over the whole command (buffer fill, chain build, warm-up, flushes, controls and timed walks together) [cmn-counts.csv]. The flushed 8 MiB CME command put {FLUSH_SPREAD[0]:,} to {FLUSH_SPREAD[-1]:,} requests on each of the five nodes (within {100 * (FLUSH_SPREAD[-1] / FLUSH_SPREAD[0] - 1):.1f} %): the command's traffic as a whole is spread evenly by the address hash. The two timed walks are 262,144 hops of it, so these counts do not measure the CME's own traffic.")

    f_map = mesh_map(left=[("CME L1, 64 KiB per DSU (4-way)", f"{CLV[0]['ns']:.1f} ns at 4 KiB; register control {RT_NS[0]:.1f} ns", C["cme"]),
                           ("DSU L3, 256 KiB" + (": no data on this run" if L3_SF else " (core L1, L2 bypassed)"), f"{[d for d in CLV if d['size'] == 131072][0]['ns']:.1f} ns at 128 KiB" + (", from the SLC; core L1, L2 bypassed" if L3_SF else " (serving level not measured)"), "#e9f1fb"),
                           ("mesh: to the home node that owns the line", "the grid on the right; one hop per crosspoint", "#f9f9f7"),
                           (["5 home nodes (HN-S)", "SLC 768 KiB each (12 ways), \"L4\" cache", "OCM 256 KiB each (4 ways), addressable SRAM"], f"{[d for d in CLV if d['size'] == 2097152][0]['ns']:.1f} ns at 2 MiB (level not measured); core {SLC[2]['best']:.1f}", "#fdeee6"),
                           ("DRAM, behind the home node (emulator)", f"{[d for d in CLV if d['kind'] == 'flushed'][0]['ns']:.1f} ns at 8 MiB flushed; core {[d for d in LV4 if d['kind'] == 'flushed'][0]['ns']:.1f}", "#f1f1ee")],
                     node_labels={NODE_OF_REGION[r]: [f"CME {COCM[r]['best']:.1f} ns", f"core {OCM[2][r]['best']:.1f} ns"] for r in range(5)},
                     paths=[(1, NODE_OF_REGION[r], C["s2"], "") for r in range(5)], title_dsu="DSU 1: CPU 2 in streaming mode, CPU 3 offline")
    f_lat = line_chart([dict(name="C1-Nano core, CPU 2", color=C["s1"], pts=[(d["size"], d["core"]) for d in CLV if d["kind"] != "flushed"], short="core", dy=14),
                        dict(name="CME (streaming mode)", color=C["s2"], pts=[(d["size"], d["ns"], f"CME {kib(d['size'])} {d['kind']}: {d['ns']:.3f} ns, outer refills {d['outer'][0]:.2f} to {d['outer'][1]:.2f} per load") for d in CLV if d["kind"] != "flushed"], short="CME")],
                       marks=((32768, "core L1 32 KiB"), (65536, "CME L1 64 KiB"), (262144, "L3 256 KiB" + L3_TAG), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 75), ticks_y=[0, 15, 30, 45, 60, 75], hline=(RT_NS[0], f"DUP/LASTB register control {RT_NS[0]:.1f} ns, no memory access"))
    f_ref = line_chart([dict(name="outer refills per load (0x327E, from outside the cluster)", color=C["s2"], pts=[(d["size"], d["outer_best"], f"{kib(d['size'])}: outer {d['outer_best']:.2f} in the fastest rep (reps {d['outer'][0]:.2f} to {d['outer'][1]:.2f})") for d in CLV if d["kind"] != "flushed"], short="outer"),
                        dict(name="inner refills per load (0x327D, from inside the cluster)", color=C["s7"], pts=[(d["size"], d["inner_best"], f"{kib(d['size'])}: inner {d['inner_best']:.2f} in the fastest rep (reps {d['inner'][0]:.2f} to {d['inner'][1]:.2f})") for d in CLV if d["kind"] != "flushed"], short="inner", dy=14)],
                       ylabel="CME L1 refills per load, counted in the fastest rep of each footprint (hover for the range over reps)", marks=((65536, "CME L1 64 KiB"),), ylim=(0, 18), ticks_y=[0, 3, 6, 9, 12, 15, 18])
    f_bw = line_chart([dict(name="core read", color=C["s1"], pts=[(d["size"], d["core_read"]) for d in CBW if d["core_read"]], dash="5 4", short="core read", dy=14),
                       dict(name="CME read", color=C["s1"], pts=[(d["size"], d["read"]) for d in CBW], short="CME read"),
                       dict(name="core write", color=C["s2"], pts=[(d["size"], d["core_write"]) for d in CBW if d["core_write"]], dash="5 4", short="core write", dy=14),
                       dict(name="CME write", color=C["s2"], pts=[(d["size"], d["write"]) for d in CBW], short="CME write"),
                       dict(name="core copy", color=C["s3"], pts=[(d["size"], d["core_copy"]) for d in CBW if d["core_copy"]], dash="5 4", short="core copy", dy=14),
                       dict(name="CME copy", color=C["s3"], pts=[(d["size"], d["copy"]) for d in CBW], short="CME copy")],
                      ylabel="GB/s, one thread on CPU 2 (dashed: core; solid: CME)", marks=((65536, "CME L1 64 KiB"), (262144, "L3 256 KiB" + L3_TAG), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 135), ticks_y=[0, 25, 50, 75, 100, 125])
    orows = [dict(label=f"OCM{r} ({COCM[r]['dist']} xp) best", a=OCM[2][r]["best"], b=COCM[r]["best"]) for r in sorted(range(5), key=lambda r: (COCM[r]["dist"], r))]
    orows += [dict(label="all five, sparse, best", a=ALL5S[2]["best"], b=CALL5S["best"]), dict(label="all five, dense, best", a=ALL5D[2]["best"], b=CALL5D["best"])]
    f_ocm = dumbbell(orows, names=("core (CPU 2)", "CME"), colors=(C["s1"], C["s2"]), xlim=(18, 48))
    srows = [dict(label=f"CME OCM{r} ({COCM[r]['dist']} xp)", vals=[p[0] for p in COCM[r]["passes"]], best=COCM[r]["best"], extra=[(OCM[2][r]["best"], C["s1"], "core best")]) for r in sorted(range(5), key=lambda r: (COCM[r]["dist"], r))]
    srows += [dict(label="CME all five, sparse", vals=[p[0] for p in CALL5S["passes"]], best=CALL5S["best"], extra=[(ALL5S[2]["best"], C["s1"], "core best")])]
    f_spread = strip(srows, color=C["s2"], markers=((C["s1"], "core best (square)"),), xlim=(20, 48))
    bwrows = [dict(label=f"OCM{r} read from CPU 2 ({COCM[r]['dist']} xp)", a=OCMBW["region"][r], b=COCMBW["region"][r]) for r in range(5)] + [dict(label="all five read", a=OCMBW["all5"], b=COCMBW["all5"]), dict(label="all five streaming write", a=OCMBW["write"], b=COCMBW["write"])]
    f_ocmbw = dumbbell(bwrows, unit="GB/s", names=("core (CPU 2)", "CME"), colors=(C["s1"], C["s2"]), xlim=(10, 26))

    c4 = CLV[0]; c8 = [d for d in CLV if d["size"] == 8192][0]; c16 = [d for d in CLV if d["size"] == 16384][0]; c64 = [d for d in CLV if d["size"] == 65536][0]; c96 = [d for d in CLV if d["size"] == 98304][0]
    c256 = [d for d in CLV if d["size"] == 262144][0]; c32m = [d for d in CLV if d["size"] == 33554432][0]; cfl = [d for d in CLV if d["kind"] == "flushed"][0]; c8m = [d for d in CLV if d["size"] == 8388608 and d["kind"] == "fresh"][0]
    c512 = [d for d in CLV if d["size"] == 524288][0]; c384 = [d for d in CLV if d["size"] == 393216][0]
    b48 = [d for d in CBW if d["size"] == 49152][0]; b96 = [d for d in CBW if d["size"] == 98304][0]; b160 = [d for d in CBW if d["size"] == 163840][0]; b32m = [d for d in CBW if d["size"] == 33554432][0]; b16 = [d for d in CBW if d["size"] == 16384][0]
    big = [d for d in CBW if d["size"] >= 163840]
    f_path = cme_path_fig(meas=[
        ("Register control, DUP then LASTB: the core-to-CME link both ways, no memory access", f"{RT_NS[0]:.1f} ns ({RT_CYC[0]:.0f} CME cycles)"),
        ("Chase at 4 KiB, fits the CME L1D (core's own loads at 4 KiB, from its L1)", f"{c4['ns']:.1f} ns (core {c4['core']:.1f})"),
        ("Chase at 256 KiB" + (", the DSU L3 held no data on this run" if L3_SF else ", fits the DSU L3") + " (core at 256 KiB)", f"{c256['ns']:.1f} ns (core {c256['core']:.1f})"),
        ("Fresh chain of 2 MiB, fits the SLC (core at 2 MiB)", f"{[d for d in CLV if d['size'] == 2097152][0]['ns']:.1f} ns (core {SLC[2]['best']:.1f})"),
        ("Sparse chase of one OCM region, best of five regions (core, same rows)", f"{min(COCM[r]['best'] for r in COCM):.1f} to {max(COCM[r]['best'] for r in COCM):.1f} ns (core {min(OCM[2][r]['best'] for r in range(5)):.1f} to {max(OCM[2][r]['best'] for r in range(5)):.1f})"),
        ("8 MiB with every line flushed first, served beyond the SLC (core, same row)", f"{cfl['ns']:.1f} ns (core {cfl['core']:.1f})"),
    ])
    body = f"""
<div class="short"><p><b>Short version.</b> Through the CME, a dependent load costs {c4['ns']:.1f} ns at 4 KiB, beside a {RT_NS[0]:.1f} ns register round trip control that makes no memory access, and it climbs from 8 KiB on with no clear step at the CME L1's 64 KiB. One core streams {min(d['read'] for d in big):.0f} to {max(d['read'] for d in big):.0f} GB/s of reads and {min(d['write'] for d in big):.0f} to {max(d['write'] for d in big):.0f} GB/s of writes through the CME from 160 KiB to 32 MiB, about {b32m['read'] / b32m['core_read']:.1f} and {b32m['write'] / b32m['core_write']:.1f} times its own rates. All three CME counters count and every row is valid, but the data cannot say why the CME refills from outside the cluster at footprints its 64 KiB L1 should hold.</p></div>
<ul>
<li><b>Latency.</b> {c4['ns']:.1f} ns at 4 KiB (chase minus DUP/LASTB control {c4['ns'] - RT_NS[0]:.2f} ns, a derived number, not the memory latency), {c8['ns']:.1f} at 8 KiB, {c16['ns']:.1f} at 16 KiB, {c64['ns']:.1f} at 64 KiB, {c256['ns']:.1f} at 256 KiB, {c32m['ns']:.1f} at 32 MiB; the core's same rows read {c4['core']:.1f}, {c8['core']:.1f}, {c16['core']:.1f}, {c64['core']:.1f}, {c256['core']:.1f} and {c32m['core']:.1f} ns (section 5).</li>
<li><b>Bandwidth.</b> Reads peak at {b48['read']:.1f} GB/s at 48 KiB; writes hold {min(d['write'] for d in CBW):.1f} to {max(d['write'] for d in CBW):.1f} GB/s at every footprint, 32 bytes per cycle (section 6).</li>
<li><b>OCM.</b> {min(COCM[r]['best'] for r in COCM):.1f} to {max(COCM[r]['best'] for r in COCM):.1f} ns per region through the CME against {min(OCM[2][r]['best'] for r in range(5)):.1f} to {max(OCM[2][r]['best'] for r in range(5)):.1f} ns for the core's own loads; {COCMBW['all5']:.1f} GB/s read against the core's {OCMBW['all5']:.1f} (section 7).</li>
<li><b>Open.</b> The CME's refill counter from outside the cluster is above 1 per load from 8 KiB on; whether the CME was powered down at the start of a timed span is not recorded (section 10).</li>
</ul>

<h2 id="words">1. Words used here</h2>
{words(WORDS_CME + WORDS_COMMON)}

<h2 id="run">2. The run and the platform</h2>
{PLATFORM}
<ul>
<li><b>CME conditions.</b> The kernel found SME2 with a 64-byte vector length; /proc/cpuinfo lists sme2 on all ten CPUs [sysinfo.txt, checked by this script]. The SCP armed every cluster's CME power controller in dynamic mode at boot and re-armed CPU 2-3's each time CPU 3 came back online [Jesse's run 3 README, quoting the SCP log; the log itself is not in the results directory]. CPU 3 was offline for the whole CME test, so the CME served one core.</li>
<li><b>Clock.</b> The CME ran on the core's 2 GHz clock: CME cycles per core cycle read {min(CME_RATIO):.4f} to {max(CME_RATIO):.4f} on the DRAM chase rows of 65,536 loads or more [cme-latency-dram-*.csv]. A short span reads lower, because the core's cycle count includes work outside the streaming span: the one slow cme-call rep ({CALL_OUT['ns']:.1f} ns per call) counted {CALL_OUT['c1']:.1f} CME cycles against {CALL_OUT['cyc']:.1f} core cycles per call, a ratio of {CALL_OUT_RATIO:.2f}.</li>
<li><b>Counter validity.</b> perf_cov reads 1.0000 on every CME row; no "# perf:" line in any file, so no event was refused. This kernel opens any raw event number, so the proof that the events are real is their counts: both refill events read 0.0000 in every no-memory control rep; the outer event is nonzero in all {CME_TIMED} timed load rows, and the inner event in {CME_TIMED - CME_INNER_ZERO} of them (zero on {CME_INNER_ZERO} OCM passes, which service from outside the cluster fits) [cme-latency-*.csv].</li>
</ul>

<h3 id="changes">2.1 What is new in run 3 for the CME</h3>
<ul>
<li><b>The CME test itself is new.</b> run_cme.sh ({len(CMD4) - len(CMD4_CACHE)} commands) runs the latency and bandwidth programs with --cme, which routes every load and store through the CME kernels in cme_kern.S (streaming mode, 64-byte vectors) on CPU 2 with CPU 3 offline. Its rows copy the cache test's footprints and flags, with the sparse OCM chains and the 7 fresh passes of the cache test, plus the two no-memory controls (cme-roundtrip, cme-call), the 1 KiB call-cost rows and the 64-byte kernel forms. The design and its review are in CME-plan.md and codex-review-CME-plan.md.</li>
<li><b>The core twins are from the same boot.</b> Every core number on this page is run 3's own cache-test row (run_asimov.sh ran first, in the same job), so the comparison carries no firmware or image difference. Those core rows repeat run 2 within 2.56 % (<a href="asimov-c1nano-perf.html">asimov-c1nano-perf.html</a>, section 2.1 and table 4.8).</li>
<li><b>No earlier run here read the CME.</b> asimov-bench measured the CME on an older RTL with its own chase; section 9 compares with the numbers it reported.</li>
</ul>

<h2 id="map">3. The hemisphere map, CME path</h2>
<p>The left column is the CME's path outward: its own L1, then the DSU's L3{' (which held no data on this run)' if L3_SF else ''}, then the mesh to the home node (SLC or OCM), with DRAM behind the home node. The core's L1 and L2 are not on it. The chase times written in the boxes are measured at a footprint; which level served them is not measured, because the two CME refill events cannot tell demand from prefetch (section 5). The label under each home node is the CME's best sparse chase of that region beside CPU 2's own.</p>
{fig(f_map, f"Through the CME every footprint costs more: {c4['ns']:.1f} ns against the core's {c4['core']:.1f} at 4 KiB, {[d for d in CLV if d['size'] == 2097152][0]['ns']:.1f} against {SLC[2]['best']:.1f} at 2 MiB (fresh chain), {cfl['ns']:.1f} against {cfl['core']:.1f} at 8 MiB with every line flushed.", f"The register control (DUP then LASTB, no memory access) reads {RT_NS[0]:.1f} ns per hop, {RT_CYC[0]:.0f} CME cycles, in all {len(RT)} reps. The chase replaces DUP with LD1D, a different dependency chain, so chase minus control ({c4['ns'] - RT_NS[0]:.2f} ns at 4 KiB) is a derived number, not the memory latency and not a proven floor [table 4.1; CME-plan.md section 2.2].")}

<h3 id="path">3.1 The data path of one CME load</h3>
<p>The example is one hop of the chase kernel: <code>LD1D {{z0.d}}, p0/z, [x0]</code> then <code>LASTB x0, p0, z0.d</code> in streaming mode [cme_kern.S]. Words used here: MMU (the core's memory management unit, which translates a virtual address to a physical one), GPR (a general-purpose register such as x0), PIPT (a cache indexed and tagged by physical address), SCU (the DSU's snoop control unit, which keeps the cluster's caches coherent), CHI (the Arm bus protocol between the DSU and the mesh), SBSX (the mesh bridge toward a memory controller).</p>
<ol>
<li><b>Core.</b> CPU 2 is in streaming mode. It decodes the LD1D, but does not execute it: SME instructions are decoded on the core and issued to the CME, up to three per cycle, loads and stores two per cycle [C1-Nano SOG 109590, section 2.33]. The core's MMU translates the address in x0 first, so the CME receives a physical address and never asks for a translation of its own for a load or a store [C1-SME2 TRM 107831, chapter 5]. The core's L1 data cache and L2 are not on the path.</li>
<li><b>Bridges.</b> The instruction and its physical address cross the DSU on the streaming request channel (CMEREQ); a second channel (CMETLB) carries the translation requests of the CME's prefetcher back to the core [TRM 107831, chapter 1]. There is one SME2 unit bridge between each CME and the DSU [TRM 107831, section 2.1].</li>
<li><b>CME.</b> The CME decodes, renames and issues the load to its L1 data memory system: a 64 KiB, 4-way, 16-bank, physically indexed and tagged cache with 64-byte lines and two 512-bit read paths into the vector registers, so one line fills Z0 in one transfer. A hardware prefetcher with 128 streams, indexed by instruction address, fills this L1D and the DSU L3; it works in virtual addresses and keeps its own TLB [TRM 107831, table 6-1 and sections 5 and 6.3]. LASTB then moves the last active element of Z0 into x0, and that GPR update travels back to the core, where the next LD1D waits for it (the core's event 0x3205 counts the waiting cycles) [C1-Nano TRM 107753, PMU events 0x3204 and 0x3205].</li>
<li><b>DSU L3.</b> A CME L1D miss goes to the DSU's L3 memory system: the SCU's snoop filter, which tracks the CME's L1D beside the cores' caches, and the 256 KiB L3; on a simultaneous hit in both, the L3 supplies the line [C1-DSU TRM 107804, chapter 2]. A line that comes from inside the cluster counts as an inner refill (event 0x327D).{" On this run the L3 of CPUs 2 to 9 was in snoop-filter-only mode and held no data (run 4 boot B's hit counters read 0 L3 hits per load), so the inner refills counted here were not L3 hits; which lines the event counted, these files do not show. Run 4 boot E turned the L3 on, and there the CME's refills at 8 KiB come from inside the cluster [asimov-cme-run4.html, section 9]." if L3_SF else ""}</li>
<li><b>Mesh, home node, DRAM.</b> An L3 miss leaves the cluster on the DSU's 256-bit CHI memory interface [DSU TRM 107804, chapter 2] and crosses the mesh from crosspoint (2,3) to the home node that owns the address, 1 crosspoint away for three of the five nodes and 3 for the other two (table 4.2). There the line is in the SLC, or in the OCM ways when the address is an OCM region, or is fetched from DRAM through the SBSX bridge. The line returning from outside the cluster fills the L3 and the CME L1D and counts as an outer refill (event 0x327E). The counter cannot say which of SLC, OCM or DRAM supplied it (section 5).</li>
</ol>
{fig(f_path, f"Every CME hop crosses the core-to-CME link twice: the address goes out, the result comes back. The register control that does only that reads {RT_NS[0]:.1f} ns; the 4 KiB chase reads {c4['ns']:.1f} ns, against {c4['core']:.1f} ns for the core's own L1 load.", f"From 4 KiB to 256 KiB the CME rows climb {c256['ns'] - c4['ns']:.1f} ns and the core's own rows {c256['core'] - c4['core']:.1f} ns; from 4 KiB to the flushed 8 MiB row, {cfl['ns'] - c4['ns']:.1f} ns against {cfl['core'] - c4['core']:.1f} ns. The chase minus the control ({c4['ns'] - RT_NS[0]:.2f} ns at 4 KiB) is a derived number: the two rows run different instruction chains, so it is not the L1D hit latency [CME-plan.md section 2.2]. The public LLVM model of the C1-Nano puts a CLASTB result (a close relative of LASTB) into a GPR at 12 cycles in streaming mode; the measured control is {RT_CYC[0]:.0f} CME cycles per hop, so most of a hop is spent outside that one instruction [refs/C1Nano-streaming-cme-instructions.s].")}

<h2 id="tables">4. Summary tables</h2>
<h3 id="t41">4.1 Latency by footprint, core against CME</h3>{t1}
<h3 id="t42">4.2 OCM through the CME</h3>{t2}
<h3 id="t43">4.3 One-core bandwidth, core against CME</h3>{t3}
<h3 id="t44">4.4 The 64-byte forms</h3>{t3b}
<h3 id="t45">4.5 Call cost</h3>{t4}
<h3 id="t46">4.6 Home-node counts, CME rows against core rows</h3>{t5}

<h2 id="f-lat">5. Latency by footprint</h2>
{fig(f_lat, f"The CME has no clear step at its 64 KiB L1: the climb starts at 8 KiB ({c8['ns'] - c4['ns']:+.1f} ns), continues at 16 KiB ({c16['ns'] - c8['ns']:+.1f}), and the 64 to 96 KiB step is only {c96['ns'] - c64['ns']:+.1f} ns.", f"The core steps at 48 KiB (L1), 192 KiB (L2) and 4 to 16 MiB (SLC). The CME's fresh chains of 512 KiB to 1 MiB ({c512['ns']:.1f} ns at 512 KiB) read below its repeated walks of 96 to 384 KiB ({c96['ns']:.1f} to {c384['ns']:.1f}), and its flushed 8 MiB row ({cfl['ns']:.1f} ns) reads below its unflushed one ({c8m['ns']:.1f}), the reverse of the core [table 4.1]. The CME minus the register round trip at 4 KiB is {c4['ns'] - RT_NS[0]:.2f} ns.")}
{fig(f_ref, f"Outer refills per load are {c8['outer_best']:.2f} at 8 KiB and {c16['outer_best']:.2f} at 16 KiB in the fastest reps, footprints a 64 KiB L1 should hold, and reach {max(d['outer'][1] for d in CLV):.1f} per load near 128 to 256 KiB.", f"On the sparse OCM passes (every line flushed from the core caches before the pass), the same event reads {min(COCM[r]['outer'][0] for r in COCM):.2f} to {max(COCM[r]['outer'][1] for r in COCM):.2f} per load, so it counts about one per line fill there. The slowest rep carries the most outer refills in {slowest_has_most_outer} of the {n_small} repeated rows up to 128 KiB. <span class='hyp'>hypothesis</span> The counts above 1 per load are the CME's hardware prefetcher fetching lines the chain does not use, which these two events include; a run with 0x3280 (read refills) and 0x32B2 (prefetcher refills) beside them would separate demand from prefetch [CME-plan.md section 2.1; Jesse's run 3 README, CME latency]." + (f" <span class='ok'>boot A</span> Run 4 boot A ran them: at 8 KiB the prefetcher fills {R4A['cme']['pf8k']:.1f} lines per load and the chain's own loads {R4A['cme']['rd8k']:.2f}, so the counts above 1 are prefetches (section 10) [asimov-cme-run4.html]." if R4A else ""))}

<h2 id="f-bw">6. Bandwidth by footprint</h2>
{fig(f_bw, f"The CME reads {b48['read']:.0f} GB/s at 48 KiB and {min(d['read'] for d in big):.0f} to {max(d['read'] for d in big):.0f} GB/s from 160 KiB on; it writes {min(d['write'] for d in CBW):.0f} to {max(d['write'] for d in CBW):.0f} GB/s at every footprint, 32 bytes per cycle.", f"Read falls {100 * (1 - b96['read'] / b48['read']):.0f} % from 48 to 96 KiB and {100 * (1 - b160['read'] / b96['read']):.0f} % more by 160 KiB, then holds at every larger footprint while the chase latency rises {100 * (c32m['ns'] / [d for d in CLV if d['size'] == 1048576][0]['ns'] - 1):.0f} % from 1 to 32 MiB. Copy holds {b16['copy']:.0f} GB/s at 16 and 48 KiB and {min(d['copy'] for d in big):.0f} to {max(d['copy'] for d in big):.0f} from 160 KiB. These rows carry no counters, so which level serves a footprint is read from the footprint [table 4.3]. Up to {100 * CALLB['read'] / PASS16:.0f} % of the 16 KiB read row is call cost [table 4.5].")}
<p><b>Writes beside the cluster's two cores.</b> One CME writes a 32 MiB buffer at {W32:.1f} GB/s through CPU 2-3's cluster, {W32 / PAIR_W:.2f} times the {PAIR_W:.1f} GB/s CPUs 2 and 3 write together. <span class="hyp">hypothesis</span> If the CME's stores leave through the same cluster port, the two-core write limit is on the cores' side, not the port's. A two-core write with one of them in streaming mode would test it.</p>

<h2 id="f-ocm">7. OCM through the CME</h2>
{fig(f_ocm, f"OCM costs {min(COCM[r]['best'] - OCM[2][r]['best'] for r in COCM):.1f} to {max(COCM[r]['best'] - OCM[2][r]['best'] for r in COCM):.1f} ns more per load through the CME than from the core, by region best.", f"Through the CME the per-region bests do not order by mesh distance (OCM{min(COCM, key=lambda r: COCM[r]['best'])}, {COCM[min(COCM, key=lambda r: COCM[r]['best'])]['dist']} crosspoints away, is fastest), where the core's do. The dense all-five chase reads {CALL5D['best'] - CALL5S['best']:+.1f} ns against the sparse one through the CME, with {CALL5D['outer'][0]:.2f} to {CALL5D['outer'][1]:.2f} outer refills per load against {CALL5S['outer'][0]:.2f} to {CALL5S['outer'][1]:.2f}; on the core the dense row reads {ALL5D[2]['best'] - ALL5S[2]['best']:+.1f} ns [table 4.2].")}
{fig(f_spread, f"The 7 CME passes of a region spread {min(cme_region_spread):.1f} to {max(cme_region_spread):.1f} ns; the core's 7 passes from CPU 2 spread {min(spread[:5]):.1f} to {max(spread[:5]):.1f} ns. By region the CME spread is smaller for OCM0 and OCM1 and larger for OCM2 to OCM4.", f"The CME rows' medians run {min(COCM[r]['median'] - COCM[r]['best'] for r in COCM):.1f} to {max(COCM[r]['median'] - COCM[r]['best'] for r in COCM):.1f} ns above their bests [table 4.2]. <span class='hyp'>hypothesis</span> Part of a 64-hop CME pass is a fixed cost per timed span of about 0.1 to 0.3 us (the CME waking from dynamic power-down, or its first instructions after SMSTART), which would be up to about 5 ns a hop here and under 1 ns on the 320-hop passes; Jesse's README bounds it from three views but no row measures it directly [Jesse's run 3 README, CME power].")}
{fig(f_ocmbw, f"The CME reads an OCM region at {min(COCMBW['region']):.1f} to {max(COCMBW['region']):.1f} GB/s, {min(COCMBW['region'][r] / OCMBW['region'][r] for r in range(5)):.2f} to {max(COCMBW['region'][r] / OCMBW['region'][r] for r in range(5)):.2f} times the core, with no step by distance; its streaming write to OCM ({COCMBW['write']:.1f} GB/s) matches the core's ({OCMBW['write']:.1f}).", f"The CME's OCM read reps spread {min(cme_rep_spread):.1f} to {max(cme_rep_spread):.1f} % (the core's {min(core_rep_spread):.1f} to {max(core_rep_spread):.1f} %). Through the CME, OCM reads at {COCMBW['all5'] / b32m['read']:.2f} times its warm DRAM-buffer rate, the reverse of the core ({OCMBW['all5'] / b32m['core_read']:.2f}); these rows also differ in page size (4 KiB against 2 MiB) and in one flushed pass against warm passes, so the data do not say which costs the CME [table 4.2].")}

<h2 id="f-cmn">8. Mesh counters</h2>
<p>Where the CME's loads make most of a command's traffic, its rows put more requests on the home nodes than the core's same rows: the OCM reads {min(CME_READ_OWN_RATIO):.2f} to {max(CME_READ_OWN_RATIO):.2f} times on the region's node; the sparse chases, whose counts are dominated by the core-side chain build and the 7 flushes, {min(CME_OCM_OWN_RATIO):.2f} to {max(CME_OCM_OWN_RATIO):.2f} times [table 4.6]. <span class="hyp">hypothesis</span> The extra requests are the CME's refills above one per load (prefetches), seen at the home node; the CME outer-refill event is the direct evidence that CME refills come from outside the cluster, with the demand-against-prefetch limit of section 5. The flushed 8 MiB CME command spread its {sum(FLUSH_SPREAD):,} requests evenly over the five nodes, which fits the address hash; the counts cover the whole command, not the CME's timed loads alone.</p>

<h2 id="bench">9. Against asimov-bench's earlier CME numbers</h2>
<ul>
<li>CME L1 chase: {c4['ns']:.2f} ns here at 4 KiB against {BENCH['cme_l1']} ns (asimov-bench run 3969, as quoted in est_chip_time.py). The DUP/LASTB control, which asimov-bench did not run, reads {RT_NS[0]:.1f} ns; chase minus control is {c4['ns'] - RT_NS[0]:.2f} ns (derived).</li>
<li>DSU L3 through the CME: nothing here levels off near asimov-bench's {BENCH['dsu_l3']} ns; the rows between 8 KiB and 256 KiB read {c8['ns']:.1f} to {c256['ns']:.1f} ns and climb throughout. The two chases differ in chain construction and footprint; which difference matters is Insufficient data.{(f" <span class='ok'>boots B, E</span> There was no L3 level to find: the L3 held no data on this run. With the L3 on (run 4 boot E) the CME's chase at 8 KiB reads {R4E['cme']['k8']:.1f} ns against {R4A['bootC']['cme']['k8']:.1f} ns with it off, and the climb stays the prefetcher's [asimov-cme-run4.html, section 9]." if R4E else "")}</li>
<li>OCM through the CME: {min(COCM[r]['best'] for r in COCM):.1f} to {max(COCM[r]['best'] for r in COCM):.1f} ns per region against {BENCH['ocm']} ns. DRAM read: {b32m['read']:.1f} GB/s at 32 MiB against {BENCH['read_gbps']} GB/s. The core's {c4['core']:.3f} ns at 4 KiB and {[d for d in LV4 if d['size'] == 131072][0]['ns']:.2f} ns at 128 KiB match asimov-bench's {BENCH['core_l1']} and {BENCH['core_l2']}.</li>
</ul>

<h2 id="open">10. What is settled, what is open</h2>
<ul>
<li><span class="ok">settled</span> The CME test runs on this platform: SME2 present, the CME PPU armed, all three CME PMU events open and count, every row valid, no hang (the 12 s guard did not fire).</li>
<li><span class="ok">settled</span> The DUP/LASTB register control reads {RT_NS[0]:.1f} ns per hop ({RT_CYC[0]:.0f} CME cycles) in all {len(RT)} reps, and the 4 KiB chase {c4['ns']:.1f} ns. Their difference is "chase minus control", a derived number; what part of a chase hop is memory latency is Insufficient data.</li>
<li><span class="ok">settled</span> One core moves {min(d['read'] for d in big):.0f} to {max(d['read'] for d in big):.0f} GB/s of reads and {min(d['write'] for d in big):.0f} to {max(d['write'] for d in big):.0f} GB/s of writes through the CME at every footprint from 160 KiB to 32 MiB, {b32m['read'] / b32m['core_read']:.1f} and {b32m['write'] / b32m['core_write']:.1f} times its own DRAM rates.</li>
<li><span class="ok">settled</span> OCM through the CME: {min(COCM[r]['best'] for r in COCM):.1f} to {max(COCM[r]['best'] for r in COCM):.1f} ns per load (sparse best), {CALL5D['best']:.1f} ns dense; {COCMBW['all5']:.1f} GB/s read, {COCMBW['write']:.1f} GB/s write.{(f" <span class='ok'>boot A</span> Run 4 boot A repeated the chases: sparse best {R4A['cme']['ocm_sparse_best'][0]:.1f} to {R4A['cme']['ocm_sparse_best'][1]:.1f} ns, all five dense {R4A['cme']['ocm_all5_dense']:.1f} ns. Each sparse hop fills {R4A['cme']['ocm_sparse_tot'][0]:.2f} to {R4A['cme']['ocm_sparse_tot'][1]:.2f} lines, of which {R4A['cme']['ocm_sparse_rd'][0]:.2f} to {R4A['cme']['ocm_sparse_rd'][1]:.2f} are the chain's own loads and the rest prefetches; each dense hop fills {R4A['cme']['ocm_dense_rd'][0]:.2f} to {R4A['cme']['ocm_dense_rd'][1]:.2f} on its own loads plus {R4A['cme']['ocm_dense_pf'][0]:.1f} to {R4A['cme']['ocm_dense_pf'][1]:.1f} prefetches [asimov-cme-run4.html].") if R4A else ""}</li>
<li><span class="hyp">hypothesis</span> The climb from 8 KiB and the refills above 1 per load are the CME prefetcher's traffic; 0x3280 and 0x32B2 beside the present events would show it (section 5).{(f" <span class='ok'>boot A</span> Counted: 0x32B2 reads {R4A['cme']['pf8k']:.1f} prefetch refills per load at 8 KiB, {R4A['cme']['pf32k']:.1f} at 32 KiB and {R4A['cme']['pf64k']:.1f} at 64 KiB, while the demand-read refills (0x3280) reach {R4A['cme']['rd32k']:.2f} per load at 32 KiB and {R4A['cme']['rd64k']:.2f} at 64 KiB; the two new events add up to inner plus outer within {100 * R4A['cme']['consist_rel']:.1f} % on every row, and the sequential 8 MiB chain through the CME runs at {R4A['cme']['seq_ns']:.1f} ns per load with every refill a prefetch [asimov-cme-run4.html]. That the prefetcher's fills evict the chain from the L1 stays a hypothesis until boot B (prefetcher off).{b_evict}") if R4A else ""}</li>
<li><span class="hyp">hypothesis</span> A fixed cost of 0.1 to 0.3 us per timed span (CME wake-up from dynamic power-down) inflates the 64-hop OCM passes (section 7).</li>
<li><span class="gap">Insufficient data</span> CME L1 against DSU L3 hit latency as two separate numbers: no footprint here gives a flat region, and the two refill events cannot tell demand from prefetch.{(f" <span class='ok'>boot A</span> Partly answered: 0x3280 and 0x32B2 now tell them apart. The 4 KiB chase ({R4A['cme']['k4']['ns']:.1f} ns) carries {R4A['cme']['k4']['rd']:.2f} demand and {R4A['cme']['k4']['pf']:.2f} prefetch refills per load, so it is the L1 hit hop. From 8 KiB to 384 KiB the demand refills run {R4A['cme']['rd_from8k'][0]:.2f} to {R4A['cme']['rd_from8k'][1]:.2f} per load with {R4A['cme']['pf_from8k'][0]:.1f} to {R4A['cme']['pf_from8k'][1]:.1f} prefetch refills beside them, so no row isolates an L3 hit; boot B (prefetcher off) is the test [asimov-cme-run4.html].{b_l3}") if R4A else ""}</li>
<li><span class="gap">Insufficient data</span> SLC against DRAM through the CME: the 2 MiB fresh chain ({[d for d in CLV if d['size'] == 2097152][0]['ns']:.1f} ns) and the flushed 8 MiB row ({cfl['ns']:.1f} ns) are {cfl['ns'] - [d for d in CLV if d['size'] == 2097152][0]['ns']:.1f} ns apart, but no counter here names the level that served a CME load.{(f" <span class='ok'>boot A</span> Both rows read about one demand refill per load ({R4A['cme']['dram2m']['rd']:.2f} and {R4A['cme']['flushed']['rd']:.2f}) and the prefetcher adds {R4A['cme']['dram2m']['pf']:.1f} and {R4A['cme']['flushed']['pf']:.1f} refills per load; the 32 MiB chain reads {R4A['cme']['l32m']['ns']:.1f} ns with {R4A['cme']['l32m']['pf']:.1f} prefetch refills per load. The level stays unnamed: no CME event in run 4 counts where a line came from [asimov-cme-run4.html].") if R4A else ""}</li>
<li><span class="gap">open</span> Two cores of one DSU in streaming mode at once (the CME is shared); the CME with operands in OCM for a matmul; a prefetcher-off boot{" (boot B ran: asimov-cme-run4.html, section 8)" if R4B else ""}.</li>
</ul>

<h2 id="sources">11. Sources</h2>
<ul>
<li><a href="results/membench-jibin-004/results/19700101T000000Z/">results/membench-jibin-004/</a> (run 3, commit ba834c0, 2026-11-03): every number on this page is read from its CSV files by <a href="gen_run3.py">gen_run3.py</a>; the core twins are the same run's core rows.</li>
<li><a href="results/membench-jibin-004/README.md">Jesse's run 3 README</a>: platform facts, the SCP's CME lines, the kernel's SME lines, the chip time, the CME power analysis and the pass-loop disassembly estimate.</li>
<li><a href="CME-plan.md">CME-plan.md</a> and <a href="codex-review-CME-plan.md">codex-review-CME-plan.md</a>: the test design, the counter events and their caveats, the asimov-bench reference values (runs 3969 and 4045 as quoted in <a href="est_chip_time.py">est_chip_time.py</a>); <a href="cme_kern.S">cme_kern.S</a>: the kernels.</li>
<li><a href="asimov-c1nano-perf.html">asimov-c1nano-perf.html</a>: the companion page for the core.</li>
</ul>
"""
    toc = [("words", "1. Words used here"), ("run", "2. The run and the platform", [("changes", "2.1 What is new in run 3 for the CME")]), ("map", "3. The hemisphere map, CME path", [("path", "3.1 The data path of one CME load")]),
           ("tables", "4. Summary tables", [("t41", "4.1 Latency by footprint"), ("t42", "4.2 OCM through the CME"), ("t43", "4.3 One-core bandwidth, core against CME"), ("t44", "4.4 The 64-byte forms"), ("t45", "4.5 Call cost"), ("t46", "4.6 Home-node counts")]),
           ("f-lat", "5. Latency by footprint"), ("f-bw", "6. Bandwidth by footprint"),
           ("f-ocm", "7. OCM through the CME"), ("f-cmn", "8. Mesh counters"), ("bench", "9. Against asimov-bench"), ("open", "10. What is settled, what is open"), ("sources", "11. Sources")]
    return page("Asimov CME Memory Performance, run 3", "The C1-SME2 unit of DSU 1 driven from CPU 2 in streaming mode, run membench-jibin-004 (cache-mem-perf ba834c0) on the GA13 Palladium, 2026-11-03, beside the same core's rows. Generated by gen_run3.py from the CSV files.", toc, body)

if __name__ == "__main__":
    # The two pages are written by gen_perf.py since 2026-11-05 (run 4 boot E with run 3 beside it); this
    # module is their run 3 data layer and the shared helpers, imported by gen_perf.py and gen_run4.py.
    print("gen_run3.py no longer writes", OUT_CORE, "and", OUT_CME + "; run gen_perf.py instead")
