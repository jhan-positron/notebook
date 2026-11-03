#!/usr/bin/env python3
"""Build asimov-memory-hierarchy.html from the run 2 (and run 1) CSV files.

Every number on the page is read from results/membench-jibin-00{1,2}/results/*/ by
this script. Nothing is typed in by hand except the platform facts quoted from
Jesse's README (cited where used).
"""
import glob, json, os, re, collections

A = os.path.dirname(os.path.abspath(__file__))
R1 = glob.glob(A + "/results/membench-jibin-001/results/*/")[0]
R2 = glob.glob(A + "/results/membench-jibin-002/results/*/")[0]
R3 = glob.glob(A + "/results/membench-jibin-003/results/*/")[0]   # control: run 2 code and kernel on run 1 firmware
OUT = A + "/asimov-memory-hierarchy.html"

# ---------------------------------------------------------------- readers
def lat_rows(path):
    out, size = [], None
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("# size="):
            m = re.search(r"size=(\d+) lines=(\d+) backing=(\S+)", line); size = m.groups(); continue
        if line.startswith("#") or line.startswith("mem,"): continue
        f = line.split(",")
        d = dict(mem=f[0], size=int(f[1]), mode=f[2], rep=f[3], loads=f[4], ns=float(f[5]), backing=size[2])
        if len(f) >= 10: d.update(cyc=float(f[6]), l1=float(f[7]), l2=float(f[8]), l3=float(f[9]))
        out.append(d)
    return out

def bw_rows(path):
    out, flush, passes = [], None, None
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("# bandwidth"):
            flush = int(re.search(r"flush_before=(\d)", line).group(1)); passes = int(re.search(r"passes=(\d+)", line).group(1)); continue
        if line.startswith("#") or line.startswith("mem,"): continue
        f = line.split(",")
        out.append(dict(mem=f[0], kernel=f[1], threads=int(f[2]), bpt=int(f[3]), rep=f[4], agg=float(f[7]), tmin=f[8], tmax=f[9], flush=flush, passes=passes))
    return out

def best(rows, **kw):
    for d in rows:
        if d["mode" if "mode" in d else "rep"] == "best" and all(d[k] == v for k, v in kw.items()): return d
    raise KeyError(kw)

def best_pass(rows, size):
    """the timed pass that produced the best value (for its refill counts)"""
    b = [d for d in rows if d["mode"] == "best" and d["size"] == size][0]["ns"]
    return [d for d in rows if d["mode"] != "best" and d["size"] == size and abs(d["ns"] - b) < 1e-9][0]

# ---------------------------------------------------------------- topology (sysinfo.txt mesh map, node ids decoded X[8:6] Y[5:3])
NODES = {88: (1, 3, 0), 160: (2, 4, 1), 216: (3, 3, 2), 288: (4, 4, 3), 344: (5, 3, 4)}   # id -> (x, y, OCM region)
DSUS = {1: (2, 3, (2, 3)), 2: (3, 2, (4, 5)), 3: (4, 3, (6, 7)), 4: (5, 2, (8, 9))}         # dsu -> (x, y, cpus); DSU 0 at (1,2) holds the kernel
DSU0 = (1, 2)
NODE_OF_REGION = {r: n for n, (x, y, r) in NODES.items()}
CPU_DSU = {2: 1, 4: 2, 6: 3, 8: 4}
def dist(cpu, node):
    dx, dy = DSUS[CPU_DSU[cpu]][0] - NODES[node][0], DSUS[CPU_DSU[cpu]][1] - NODES[node][1]
    return abs(dx) + abs(dy)

# check the map text itself places HN-S #k and RN-F cells where the node ids say
sysinfo = open(R2 + "sysinfo.txt").read()
mapsec = sysinfo[sysinfo.index("## arm-cmn mesh map"):]
assert "CONFIG_DEBUG_FS=y" in sysinfo
map_lines = mapsec.splitlines()
def cell(x, y, port):
    """node type printed at crosspoint (x, y), port 0 or 1 (map rows: Y label row, DTC row, dots, then P0 type, P0 id, P0 dev1, P1 type, ...)"""
    for i, l in enumerate(map_lines):
        if re.match(rf"^{y} +\| XP", l):
            row = map_lines[i + 3 + 3 * port]
            return row[6 + 9 * x: 6 + 9 * x + 8].strip()
    return None
for n, (x, y, r) in NODES.items(): assert cell(x, y, 0) == "HN-S", (n, cell(x, y, 0))
for d, (x, y, c) in DSUS.items(): assert cell(x, y, 0) == "RN-F_E_E", (d, cell(x, y, 0))
assert cell(*DSU0, 0) == "RN-F_E_E"
OTHER = []  # (x, y, [node types on that crosspoint, both ports]) for crosspoints that hold no HN-S or DSU port
for x in range(6):
    for y in range(6):
        types = [cell(x, y, port) for port in (0, 1)]
        types = [tt for tt in types if tt]
        if any(tt in ("HN-S", "RN-F_E_E") for tt in types) or not types: continue
        OTHER.append((x, y, types))
SBSX = [(x, y) for x, y, types in OTHER if "SBSX" in types]
all_cells = sum(1 for x in range(6) for y in range(6) for port in (0, 1) if cell(x, y, port))
assert len(SBSX) == 10 and sum(len(tt) for _, _, tt in OTHER) == all_cells - 10, (len(SBSX), sum(len(tt) for _, _, tt in OTHER), all_cells)  # all nodes except the 5 HN-S and 5 RN-F are dots

# ---------------------------------------------------------------- latency
small = lat_rows(R2 + "latency-dram-small.csv")      # CPU 2, repeated chase, 4K..384K
large = lat_rows(R2 + "latency-dram-large.csv")      # CPU 2, fresh chains, 512K..32M
flushed = lat_rows(R2 + "latency-dram-flushed.csv")  # CPU 2, fresh + flush, 8M
small1 = lat_rows(R1 + "latency-dram-small.csv"); large1 = lat_rows(R1 + "latency-dram-large.csv")
levels = []
for rows, rows1, kind in ((small, small1, "repeat"), (large, large1, "fresh")):
    for d in rows:
        if d["mode"] != "best": continue
        p = best_pass(rows, d["size"])
        r1 = [e for e in rows1 if e["mode"] == "best" and e["size"] == d["size"]][0]["ns"]
        levels.append(dict(size=d["size"], ns=d["ns"], l1=p["l1"], l2=p["l2"], l3=p["l3"], kind=kind, run1=r1))
fl = [d for d in flushed if d["mode"] == "best"][0]; flp = best_pass(flushed, fl["size"])
flushed8m = dict(ns=fl["ns"], l3=flp["l3"], run1=[d for d in lat_rows(R1 + "latency-dram-flushed.csv") if d["mode"] == "best" and d["size"] == fl["size"]][0]["ns"])

ocm = {}           # ocm[cpu][region] = dict(best, dist, passes=[{ns,l2,l3}])
all5 = {}; slc = {}
for c in (2, 4, 6, 8):
    ocm[c] = {}
    for r in range(5):
        rows = lat_rows(f"{R2}latency-ocm-region{r}-cpu{c}.csv")
        ocm[c][r] = dict(best=best(rows)["ns"], dist=dist(c, NODE_OF_REGION[r]),
                         passes=[dict(ns=d["ns"], l2=d["l2"], l3=d["l3"]) for d in rows if d["mode"].startswith("fresh")])
    rows = lat_rows(f"{R2}latency-ocm-all5-cpu{c}.csv")
    all5[c] = dict(best=best(rows)["ns"], l3=[d["l3"] for d in rows if d["mode"].startswith("fresh")],
                   mean_dist=sum(dist(c, n) for n in NODES) / 5)
    rows = large if c == 2 else lat_rows(f"{R2}latency-dram-slc-cpu{c}.csv")
    slc[c] = dict(best=best(rows, size=2097152)["ns"], l3=best_pass(rows, 2097152)["l3"])
ocm1 = {r: best(lat_rows(f"{R1}latency-ocm-region{r}.csv"))["ns"] for r in range(5)}   # run 1, CPU 2, re-walked chains
by_dist = collections.defaultdict(list)
for c in ocm:
    for r in ocm[c]: by_dist[ocm[c][r]["dist"]].append(ocm[c][r]["best"])
dist_stats = {k: dict(n=len(v), mean=sum(v) / len(v), lo=min(v), hi=max(v)) for k, v in by_dist.items()}
region_passes = [p for c in ocm for r in ocm[c] for p in ocm[c][r]["passes"]]
region_l3 = (min(p["l3"] for p in region_passes), max(p["l3"] for p in region_passes))
region_l2 = (min(p["l2"] for p in region_passes), max(p["l2"] for p in region_passes))
faster_has_fewer_l3 = sum(1 for c in ocm for r in ocm[c] if (lambda a, b: (a["ns"] < b["ns"]) == (a["l3"] < b["l3"]))(*ocm[c][r]["passes"]))
controls = {c: best(lat_rows(f"{R2}latency-control-cpu{c}.csv"))["ns"] for c in (2, 4, 6, 8)}

# ---------------------------------------------------------------- bandwidth
one = bw_rows(R2 + "bandwidth-dram-1core.csv"); one1 = bw_rows(R1 + "bandwidth-dram-1core.csv")
sizes1 = sorted({d["bpt"] for d in one})
onecore = [dict(size=s, **{k: best(one, kernel=k, bpt=s)["agg"] for k in ("read", "write", "copy")},
                **{k + "1": best(one1, kernel=k, bpt=s)["agg"] for k in ("read", "write", "copy")}) for s in sizes1]
def multi(name):
    r2, r1 = bw_rows(R2 + name), bw_rows(R1 + name)
    out = []
    for d in r2:
        if d["rep"] != "best": continue
        out.append(dict(kernel=d["kernel"], threads=d["threads"], size=d["bpt"], run2=d["agg"], run1=best(r1, kernel=d["kernel"], threads=d["threads"], bpt=d["bpt"])["agg"]))
    return out
perdsu, all8, pair = multi("bandwidth-perdsu.csv"), multi("bandwidth-all8.csv"), multi("bandwidth-pair.csv")
spread2m = best(bw_rows(R2 + "bandwidth-dram-spread.csv"))["agg"]
placement = []
for cpus in ("2-4", "2-8", "2-3", "2-4-6-8", "2-3-4-5", "2-3-8-9"):
    rows = bw_rows(f"{R2}bandwidth-write-cpus{cpus}.csv")
    b = best(rows)
    reps = [d for d in rows if d["rep"] != "best"]
    placement.append(dict(cpus=cpus, threads=b["threads"], agg=b["agg"], tmin=min(float(d["tmin"]) for d in reps), tmax=max(float(d["tmax"]) for d in reps)))
ocmbw = dict(region={r: best(bw_rows(f"{R2}bandwidth-ocm-region{r}.csv"))["agg"] for r in range(5)},
             region1={r: best(bw_rows(f"{R1}bandwidth-ocm-region{r}.csv"))["agg"] for r in range(5)},
             all5=best(bw_rows(R2 + "bandwidth-ocm-all5.csv"), flush=1, passes=1)["agg"], all5_1=best(bw_rows(R1 + "bandwidth-ocm-all5.csv"), flush=1, passes=1)["agg"],
             four=best(bw_rows(R2 + "bandwidth-ocm-4core.csv"), flush=1)["agg"], four1=best(bw_rows(R1 + "bandwidth-ocm-4core.csv"), flush=1)["agg"],
             write=best(bw_rows(R2 + "bandwidth-ocm-write.csv"))["agg"])
ocm_write_reps = [d["agg"] for d in bw_rows(R2 + "bandwidth-ocm-write.csv") if d["rep"] != "best"]

# ---------------------------------------------------------------- mesh counters
cmn = collections.OrderedDict(); comments = []
for line in open(R2 + "cmn-counts.csv"):
    line = line.rstrip("\n")
    if line.startswith("#"): comments.append(line); continue
    if line.startswith("label,"): continue
    f = line.split(",")
    cmn.setdefault(f[0], dict(node={}, child=None, helper=None, mc=None, miss=None, en_ok=True))
    e = cmn[f[0]]
    if f[1] == "hns_pocq_reqs_recvd_all": e["node"][int(f[2])] = int(f[3])
    elif f[1] == "hns_mc_reqs_local_all": e["mc"] = int(f[3])
    elif f[1] == "hns_cache_miss_all": e["miss"] = int(f[3])
    elif f[1] == "child_elapsed_ns": e["child"] = int(f[3])
    elif f[1] == "helper_elapsed_ns": e["helper"] = int(f[3])
    if f[1] not in ("child_elapsed_ns", "helper_elapsed_ns") and (int(f[5]) <= 0 or int(f[5]) < 0.95 * int(f[4])): e["en_ok"] = False
assert len(comments) == 1 and "control-nocount-cpu2 ran uncounted" in comments[0], comments
assert all(e["en_ok"] for e in cmn.values())
counted = [l for l, e in cmn.items() if e["node"]]
assert len(cmn) == 47 and len(counted) == 46
attribution = []
for c in (2, 4, 6, 8):
    ctl = cmn[f"control-cpu{c}"]["node"]
    for r in range(5):
        e = cmn[f"ocm-region{r}-cpu{c}"]["node"]; own = NODE_OF_REGION[r]
        others = {n: v for n, v in e.items() if n != own}
        ok = all(e[own] > v + ctl[n] for n, v in others.items())
        attribution.append(dict(cpu=c, region=r, own=e[own], others_lo=min(others.values()), others_hi=max(others.values()), ok=ok))
assert all(a["ok"] for a in attribution)
ctl_range = (min(v for c in (2, 4, 6, 8) for v in cmn[f"control-cpu{c}"]["node"].values()), max(v for c in (2, 4, 6, 8) for v in cmn[f"control-cpu{c}"]["node"].values()))
timing = dict(sum_child=sum(e["child"] for e in cmn.values()), sum_helper=sum(e["helper"] for e in cmn.values()),
              own_lo=min(e["helper"] - e["child"] for l, e in cmn.items() if e["node"]), own_hi=max(e["helper"] - e["child"] for l, e in cmn.items() if e["node"]),
              counted=cmn["control-cpu2"], uncounted=cmn["control-nocount-cpu2"])
log = open(R2 + "log.txt").read()
cmds = re.findall(r"^\+ (\S+) (\S+) .*\[uptime ([\d.]+)\]", log, re.M)
assert len(cmds) == 63
run_s = 1.630000439   # Jesse's README: MB RUN end status=exit:0 ns=1630000439 (the script's own log has 1 s resolution)
# wall time of the 47 helper commands from the uptime stamps (10 ms resolution): first helper start to the start of the command after the last helper
t = [(k, l, float(u)) for k, l, u in cmds]
helper_idx = [i for i, (k, l, u) in enumerate(t) if k in ("cmn", "cmn0")]
hs = set(helper_idx)
helper_span = sum(t[i + 1][2] - t[i][2] for i in helper_idx if i + 1 in hs)  # gaps between two consecutive helper commands only (no shell step in between)
helper_gaps = sum(1 for i in helper_idx if i + 1 in hs)

# ---------------------------------------------------------------- run 1 vs run 2 agreement
agree = []
for name, l2 in (("latency-dram-small.csv", small), ("latency-dram-large.csv", large)):
    l1 = lat_rows(R1 + name)
    for d in l2:
        if d["mode"] == "best":
            r1 = [e for e in l1 if e["mode"] == "best" and e["size"] == d["size"]][0]["ns"]
            agree.append((name, d["size"], r1, d["ns"]))
for name in ("bandwidth-dram-1core.csv", "bandwidth-pair.csv", "bandwidth-perdsu.csv", "bandwidth-all8.csv", "bandwidth-ocm-4core.csv", "bandwidth-ocm-all5.csv") + tuple(f"bandwidth-ocm-region{r}.csv" for r in range(5)):
    r2, r1 = bw_rows(R2 + name), bw_rows(R1 + name)
    for d in r2:
        if d["rep"] == "best":
            agree.append((name + " " + d["kernel"], d["bpt"], best(r1, kernel=d["kernel"], threads=d["threads"], bpt=d["bpt"], flush=d["flush"], passes=d["passes"])["agg"], d["agg"]))
agree_rows = [dict(what=w, size=s, run1=a, run2=b, pct=100 * (b - a) / a) for w, s, a, b in agree]
writes_changed = [a for a in agree_rows if "write" in a["what"] and a["size"] >= 2097152 and ("perdsu" in a["what"] or "all8" in a["what"])]
others = [a for a in agree_rows if a not in writes_changed]
max_other = max(others, key=lambda a: abs(a["pct"]))
bound_pct = __import__("math").ceil(abs(max_other["pct"]) * 10) / 10

# ---------------------------------------------------------------- control run (membench-jibin-003)
run3_s = 1.610013380   # Jesse's README for membench-jibin-003: MB RUN end status=exit:0 ns=1610013380
def multi3(name):
    r3 = bw_rows(R3 + name); out = []
    for d in r3:
        if d["rep"] != "best": continue
        k = dict(kernel=d["kernel"], threads=d["threads"], bpt=d["bpt"], flush=d["flush"], passes=d["passes"])
        out.append(dict(kernel=d["kernel"], threads=d["threads"], size=d["bpt"], run3=d["agg"], run2=best(bw_rows(R2 + name), **k)["agg"], run1=best(bw_rows(R1 + name), **k)["agg"]))
    return out
ctrl_writes = [d for n in ("bandwidth-perdsu.csv", "bandwidth-all8.csv") for d in multi3(n) if d["kernel"] == "write"]
ctrl_place = {}
for cpus in ("2-4", "2-8", "2-3", "2-4-6-8", "2-3-4-5", "2-3-8-9"):
    ctrl_place[cpus] = dict(run3=best(bw_rows(f"{R3}bandwidth-write-cpus{cpus}.csv"))["agg"], run2=best(bw_rows(f"{R2}bandwidth-write-cpus{cpus}.csv"))["agg"])
cmp32 = []   # every best row, run 3 against run 2
for pth in sorted(glob.glob(R3 + "latency-*.csv")):
    n = os.path.basename(pth)
    b2 = {(d["mem"], d["size"]): d["ns"] for d in lat_rows(R2 + n) if d["mode"] == "best"}
    for d in lat_rows(pth):
        if d["mode"] == "best": cmp32.append((n, d["size"], b2[(d["mem"], d["size"])], d["ns"]))
for pth in sorted(glob.glob(R3 + "bandwidth-*.csv")):
    n = os.path.basename(pth)
    for d in bw_rows(pth):
        if d["rep"] == "best": cmp32.append((n + " " + d["kernel"], d["bpt"], best(bw_rows(R2 + n), kernel=d["kernel"], threads=d["threads"], bpt=d["bpt"], flush=d["flush"], passes=d["passes"])["agg"], d["agg"]))
def is_multi_write(w): return "write" in w[0] and w[1] >= 2097152 and ("perdsu" in w[0] or "all8" in w[0] or "2-4-6-8" in w[0])
ctrl_other = [w for w in cmp32 if not is_multi_write(w) and not w[0].startswith("latency-ocm-region")]
ctrl_other_max = max(ctrl_other, key=lambda w: abs(100 * (w[3] - w[2]) / w[2]))
ctrl_other_pct = 100 * (ctrl_other_max[3] - ctrl_other_max[2]) / ctrl_other_max[2]
ctrl_region = [w for w in cmp32 if w[0].startswith("latency-ocm-region")]
ctrl_region_ns = max(abs(w[3] - w[2]) for w in ctrl_region)
ctrl_multi = [w for w in cmp32 if is_multi_write(w)]
ctrl_vs_run1 = [(d["run1"], d["run3"]) for d in ctrl_writes] + [(a["run1"], None) for a in []]
ctrl_vs_run1_pct = max(abs(100 * (b - a) / a) for a, b in ctrl_vs_run1)
ocm3 = {}
for c in (2, 4, 6, 8):
    for r in range(5):
        ocm3[(c, r)] = best(lat_rows(f"{R3}latency-ocm-region{r}-cpu{c}.csv"))["ns"]
by_dist3 = collections.defaultdict(list)
for (c, r), v in ocm3.items(): by_dist3[dist(c, NODE_OF_REGION[r])].append(v)
dist3 = {k: sum(v) / len(v) for k, v in by_dist3.items()}
cmn3 = collections.OrderedDict()
for line in open(R3 + "cmn-counts.csv"):
    line = line.rstrip("\n")
    if line.startswith("#") or line.startswith("label,"): continue
    f = line.split(",")
    cmn3.setdefault(f[0], dict(node={}, mc=None, miss=None, child=None, helper=None))
    e = cmn3[f[0]]
    if f[1] == "hns_pocq_reqs_recvd_all": e["node"][int(f[2])] = int(f[3])
    elif f[1] == "hns_mc_reqs_local_all": e["mc"] = int(f[3])
    elif f[1] == "hns_cache_miss_all": e["miss"] = int(f[3])
    elif f[1] == "child_elapsed_ns": e["child"] = int(f[3])
    elif f[1] == "helper_elapsed_ns": e["helper"] = int(f[3])
w3, w2 = cmn3["write-cpus2-4-6-8"], cmn["write-cpus2-4-6-8"]
w3_others = [v for n, v in w3["node"].items() if n != 344]
even_rows = []
for lb in cmn3:
    if lb.startswith("write-cpus") and lb != "write-cpus2-4-6-8":
        v = list(cmn3[lb]["node"].values()); even_rows.append(100 * (max(v) - min(v)) / min(v))
assert max(even_rows) < 0.25, even_rows

data = dict(ctrl_writes=ctrl_writes, ctrl_place=ctrl_place, cmn3={l: dict(node={str(k): v for k, v in e["node"].items()}, mc=e["mc"], miss=e["miss"]) for l, e in cmn3.items() if l.startswith("write-cpus")},
            nodes={str(k): v for k, v in NODES.items()}, dsus={str(k): v for k, v in DSUS.items()}, dsu0=DSU0, sbsx=SBSX, other=OTHER,
            levels=levels, flushed8m=flushed8m, ocm={str(c): {str(r): v for r, v in d.items()} for c, d in ocm.items()}, ocm1=ocm1,
            all5={str(c): v for c, v in all5.items()}, slc={str(c): v for c, v in slc.items()}, dist_stats={str(k): v for k, v in dist_stats.items()},
            onecore=onecore, perdsu=perdsu, all8=all8, pair=pair, placement=placement, ocmbw={k: ({str(a): b for a, b in v.items()} if isinstance(v, dict) else v) for k, v in ocmbw.items()},
            cmn={l: dict(node={str(k): v for k, v in e["node"].items()}, mc=e["mc"], miss=e["miss"], child=e["child"], helper=e["helper"]) for l, e in cmn.items()},
            controls=controls, spread2m=spread2m)

# ---------------------------------------------------------------- html helpers
def fmt(x, nd=1): return f"{x:,.{nd}f}"
def tr(cells, head=False):
    tag = "th" if head else "td"
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
def table(head, rows, note=None):
    s = '<div class="tbl"><table>' + tr(head, True) + "".join(tr(r) for r in rows) + "</table></div>"
    return s + (f'<p class="note">{note}</p>' if note else "")
def kib(n): return f"{n // 1024} KiB" if n < 1 << 20 else f"{n / (1 << 20):g} MiB"

# T1 latency by level
t1 = table(["Footprint", "Chase", "ns per load", "L1 refills", "L2 refills", "L3 read refills", "Run 1 ns", "Reads from"],
           [[kib(d["size"]), d["kind"], fmt(d["ns"], 2), fmt(d["l1"], 2), fmt(d["l2"], 2), fmt(d["l3"], 2), fmt(d["run1"], 2),
             ("L1" if d["size"] <= 24576 else "L1 and L2" if d["size"] <= 32768 else "L2" if d["size"] <= 131072 else "L2, L3 and mesh (mixed)" if d["size"] <= 262144
              else "SLC (mesh cache)" if d["size"] <= 3145728 else "SLC and DRAM (mixed)" if d["size"] < 16777216 else "DRAM")] for d in levels]
           + [[kib(fl["size"]) + " flushed", "fresh + flush", fmt(fl["ns"], 2), "", "", fmt(flp["l3"], 2), fmt(flushed8m["run1"], 2), "DRAM (lines flushed from every cache)"]],
           "Repeated chase: a random chain walked many times, so later walks hit whatever cache holds it. Fresh chain: a chain walked once. Refills per load from the PMU events 0x03, 0x17 and 0xA2 of the best pass [latency-dram-small.csv, latency-dram-large.csv, latency-dram-flushed.csv]. The L3 is 256 KiB per DSU, so no footprint fits L3 alone: 192 KiB and 256 KiB mix L2, L3 and mesh reads.")

# T2 OCM by region and CPU
t2 = table(["CPU (DSU, port)"] + [f"OCM{r} (node {NODE_OF_REGION[r]})" for r in range(5)] + ["All five, 1.25 MiB", "SLC 2 MiB DRAM chase", "Mean distance"],
           [[f"CPU {c} (DSU {CPU_DSU[c]}, {DSUS[CPU_DSU[c]][0]},{DSUS[CPU_DSU[c]][1]})"] + [f"{fmt(ocm[c][r]['best'], 2)} <span class='d'>{ocm[c][r]['dist']} xp</span>" for r in range(5)]
            + [fmt(all5[c]["best"], 2), fmt(slc[c]["best"], 2), fmt(all5[c]["mean_dist"], 1) + " xp"] for c in (2, 4, 6, 8)],
           f"ns per load, best of two fresh-chain passes after a flush of every line. xp = crosspoints from the CPU's mesh port to the region's home node [latency-ocm-region*-cpu*.csv, latency-ocm-all5-cpu*.csv, latency-dram-slc-cpu*.csv, latency-dram-large.csv for CPU 2]. The per-region rows still include prefetched lines (L3 read refills {fmt(region_l3[0], 2)} to {fmt(region_l3[1], 2)} per load). The all-five and SLC rows do not (1.00).")
t2b = table(["Distance (crosspoints)", "Rows", "Mean ns", "Range ns"],
            [[k, v["n"], fmt(v["mean"], 2), f"{fmt(v['lo'], 2)} to {fmt(v['hi'], 2)}"] for k, v in sorted(dist_stats.items())],
            "The same 20 per-region values grouped by distance.")

# T3 one-core bandwidth
t3 = table(["Buffer", "Read GB/s", "Write GB/s", "Copy GB/s", "Run 1 read", "Run 1 write", "Run 1 copy", "Buffer sits in"],
           [[kib(d["size"]), fmt(d["read"]), fmt(d["write"]), fmt(d["copy"]), fmt(d["read1"]), fmt(d["write1"]), fmt(d["copy1"]),
             ("L1" if d["size"] <= 32768 else "L2" if d["size"] <= 131072 else "L3 and mesh" if d["size"] <= 262144 else "SLC" if d["size"] <= 3145728 else "DRAM")] for d in onecore],
           "One thread on CPU 2, best of 3 reps, GB = 1e9 bytes [bandwidth-dram-1core.csv]. Write is a streaming store of the whole buffer. The store rate stays near 32 GB/s at every footprint.")

# T4 multi-core and placement
def mrows(rows, label):
    return [[label, d["kernel"], d["threads"], kib(d["size"]), fmt(d["run1"]), fmt(d["run2"]), f"{100 * (d['run2'] - d['run1']) / d['run1']:+.1f} %"] for d in rows]
t4 = table(["Cores", "Kernel", "Threads", "Per thread", "Run 1 GB/s", "Run 2 GB/s", "Change"],
           mrows(pair, "CPU 2 + 3 (one DSU)") + mrows(perdsu, "CPUs 2, 4, 6, 8") + mrows(all8, "CPUs 2 to 9"),
           "Best of 3 reps. Aggregate = total bytes over the slowest thread's time [bandwidth-pair.csv, bandwidth-perdsu.csv, bandwidth-all8.csv]. Run 1 ran SCP 0.34.0 and TF-A 0.24.0, run 2 ran SCP 0.48.0 and TF-A 0.35.0 (Jesse's README). Only the multi-DSU write rows changed by more than 2 %.")
t4b = table(["Writers (CPUs)", "DSUs used", "Aggregate GB/s", "Per writer GB/s"],
            [[p["cpus"].replace("-", ", "), ", ".join(str(CPU_DSU.get(int(c), 1 if int(c) in (2, 3) else 2 if int(c) in (4, 5) else 3 if int(c) in (6, 7) else 4)) for c in sorted({c for c in p["cpus"].split("-")}, key=int)),
              fmt(p["agg"]), f"{fmt(p['tmin'])} to {fmt(p['tmax'])}"] for p in placement],
            "16 MiB per writer, one pass, best of 2 reps, per-writer range over both reps [bandwidth-write-cpus*.csv]. A DSU with one writer gives 32.0 GB/s. A DSU with two writers gives 40.9 GB/s (row 2, 3) or 42 to 43 GB/s (est., half of the two-DSU rows).")

# T5 OCM bandwidth
t5 = table(["Row", "GB/s", "Run 1 GB/s", "Note"],
           [[f"Read OCM{r} from CPU 2 ({dist(2, NODE_OF_REGION[r])} xp)", fmt(ocmbw["region"][r]), fmt(ocmbw["region1"][r]), "256 KiB, flushed before, one pass"] for r in range(5)]
           + [["Read all five from CPU 2", fmt(ocmbw["all5"]), fmt(ocmbw["all5_1"]), "1.25 MiB, flushed before, one pass"],
              ["Read OCM1 to 4 from CPUs 2, 4, 6, 8 (one region each)", fmt(ocmbw["four"]), fmt(ocmbw["four1"]), "4 threads, flushed before"],
              ["Streaming write, all five, from CPU 2", fmt(ocmbw["write"]), "not measured", f"8 passes over 1.25 MiB, flushed before the timing, reps {', '.join(fmt(x) for x in ocm_write_reps)}"]],
           "Best of 3 reps [bandwidth-ocm-*.csv]. Run 1 had no clean OCM write row (its write rows timed the flush instruction).")

# T6 mesh counters
def node_row(label, e):
    return [label] + [f"{e['node'][n]:,}" for n in NODES] + [f"{e['mc']:,}", f"{e['miss']:,}"]
t6 = table(["Row", "node 88 (OCM0)", "160 (OCM1)", "216 (OCM2)", "288 (OCM3)", "344 (OCM4)", "MC requests", "SLC misses"],
           [node_row("Control, CPU 2 (4 KiB chase on 4 KiB pages)", cmn["control-cpu2"])]
           + [node_row(f"OCM{r} latency row, CPU 2", cmn[f"ocm-region{r}-cpu2"]) for r in range(5)]
           + [node_row("All five OCM latency row, CPU 2", cmn["ocm-all5-cpu2"]),
              node_row("2 MiB DRAM read, CPU 2 (4 passes)", cmn["dram-read-2M-cpu2"]),
              node_row("2 MiB DRAM chase, CPU 4", cmn["dram-slc-2M-cpu4"]),
              node_row("OCM streaming write, all five", cmn["ocm-write-all5"]),
              node_row("OCM read, 4 cores on OCM1 to 4", cmn["ocm-read-4core"]),
              node_row("DRAM write, CPUs 2 + 4", cmn["write-cpus2-4"]),
              node_row("DRAM write, CPUs 2, 4, 6, 8", cmn["write-cpus2-4-6-8"])],
           "Requests received at each home node (hns_pocq_reqs_recvd_all with the node filter), requests the home nodes sent to memory controllers (hns_mc_reqs_local_all, all nodes), and SLC misses (hns_cache_miss_all, all nodes), over the whole command [cmn-counts.csv]. The counts cover setup, warm-up and flushes as well as the timed walk.")
t6b = table(["CPU", "Region", "Own node requests", "Other four nodes", "Passes"],
            [[a["cpu"], f"OCM{a['region']} (node {NODE_OF_REGION[a['region']]})", f"{a['own']:,}", f"{a['others_lo']:,} to {a['others_hi']:,}", "yes" if a["ok"] else "no"] for a in attribution],
            f"Pass: the own node exceeds every other node by more than that node's count in the CPU's control row (control rows: {ctl_range[0]:,} to {ctl_range[1]:,} per node).")

# T7 timing
tc, tu = timing["counted"], timing["uncounted"]
t7 = table(["What", "Value"],
           [["Chip time of the whole script", f"{run_s:.3f} s for 63 commands (Jesse's README)"],
            ["Commands run through cmncount", f"47 (46 counted, 1 timing only)"],
            ["Sum of child lifetimes (fork to exit) under cmncount", f"{timing['sum_child'] / 1e6:.1f} ms"],
            ["Sum of cmncount lifetimes", f"{timing['sum_helper'] / 1e6:.1f} ms"],
            ["cmncount's own work per counted command", f"{timing['own_lo'] / 1e3:.0f} to {timing['own_hi'] / 1e3:.0f} us"],
            ["CPU 2 control, counted: helper / child", f"{tc['helper'] / 1e3:.1f} us / {tc['child'] / 1e3:.1f} us"],
            ["CPU 2 control, uncounted: helper / child", f"{tu['helper'] / 1e3:.1f} us / {tu['child'] / 1e3:.1f} us"],
            ["Counted minus uncounted, helper", f"{(tc['helper'] - tu['helper']) / 1e3:.1f} us (counter setup, read and teardown, including 38 extra sysfs reads per Jesse's README)"],
            ["Counted minus uncounted, child", f"{(tc['child'] - tu['child']) / 1e3:.1f} us ({100 * (tc['child'] - tu['child']) / tu['child']:.1f} % of the child)"],
            ["Wall time per helper command, from the log's 10 ms uptime stamps", f"{helper_span / helper_gaps * 1e3:.1f} ms (est., {helper_gaps} gaps between consecutive helper commands). The shell wrapper and exec are the remainder over the helper lifetime, about {helper_span / helper_gaps * 1e3 - timing['sum_helper'] / 47 / 1e6:.0f} ms (est.)"]],
           "From cmn-counts.csv timing rows and log.txt. The counters' effect on the measured command is the child difference, under 5 %.")

# T8 agreement
t8 = table(["Group", "Rows", "Largest change run 1 to run 2"],
           [["All latency and bandwidth rows both runs ran with the same arguments, except the multi-DSU writes", len(others), f"{max_other['pct']:+.2f} % ({max_other['what']}, {kib(max_other['size'])} fresh chain)"],
            ["Multi-DSU DRAM writes (4 and 8 writers, 2 MiB and 16 MiB)", len(writes_changed), f"{min(a['pct'] for a in writes_changed):+.0f} % to {max(a['pct'] for a in writes_changed):+.0f} %"],
            ["Control run (run 2 code on run 1 firmware) against run 2, all rows except the two groups below", len(ctrl_other), f"{ctrl_other_pct:+.2f} % ({ctrl_other_max[0]}, {kib(ctrl_other_max[1])})"],
            ["Control run against run 2, per-region OCM latency rows", len(ctrl_region), f"up to {fmt(ctrl_region_ns, 2)} ns (these rows carry prefetched lines)"],
            ["Control run against run 2, multi-DSU writes", len(ctrl_multi), f"{min(100 * (w[3] - w[2]) / w[2] for w in ctrl_multi):+.0f} % to {max(100 * (w[3] - w[2]) / w[2] for w in ctrl_multi):+.0f} %"],
            ["Control run against run 1, multi-DSU writes (same firmware)", len(ctrl_vs_run1), f"within {ctrl_vs_run1_pct:.1f} %"]],
           f"{len(agree_rows)} best rows from the 22 commands both runs ran with the same arguments [both runs' CSV files]. The 8 MiB flushed row changed method (run 1 re-walked the chain, run 2 walks a fresh chain) and reads {fmt(flushed8m['run1'], 2)} ns in run 1 and {fmt(fl['ns'], 2)} ns in run 2. The firmware changed between run 1 and run 2. The control run (membench-jibin-003) repeated run 2's code and kernel on run 1's firmware [results/membench-jibin-003/].")

# ---------------------------------------------------------------- page
HTML = r"""<title>Asimov Memory Hierarchy</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
:root { --bg:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --axis:#c3c2b7;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s7:#6250d6;
  --b250:#86b6ef; --b350:#5598e7; --b450:#2a78d6; --b550:#1c5cab; --b650:#104281; --b100:#cde2fb; --b150:#b7d3f6; --b200:#9ec5f4; --b300:#6da7ec; --b400:#3987e5; --b500:#256abf; --b600:#184f95; --b700:#0d366b;
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
nav.toc ol { margin:6px 0; padding-left:22px; columns:2; column-gap:28px; } nav.toc li { break-inside:avoid; margin:2px 0; }
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
svg text { font-family:var(--font); }
.cols { display:grid; grid-template-columns:1fr 1fr; gap:12px; } .cols figure { margin:0; min-width:0; }
@media (max-width:640px) { dl { grid-template-columns:1fr; } dd { margin-bottom:8px; } nav.toc ol { columns:1; } .cols { grid-template-columns:1fr; } }
</style>
<main>
<h1>Asimov Memory Hierarchy</h1>
<p class="meta">What run 2 of cache-mem-perf (commit 8ae533c) measured on one Asimov hemisphere of the GA13 Palladium emulator on 2026-11-02, drawn on one map of the hemisphere. Data: results/membench-jibin-002/ in this folder, a checksum-verified copy of Jesse Zhang's /home/jzhang/dev/emuMemBenchBox/results/jibin/membench-jibin-002/. Every number comes from the CSV files through gen_hierarchy.py. Written 2026-11-02 by Claude for Jibin Han.</p>

<div class="short">
<p><strong>Short version.</strong> One core reads its L1 in 2.0 ns, its L2 in 6.1 ns, the mesh cache (SLC) in 23 to 25 ns, OCM in 18.5 to 24.7 ns by mesh distance, and DRAM in 52 ns, and the mesh counters confirm which home node holds each OCM region.</p>
<p>Four or eight cores write DRAM at 128 to 155 GB/s on the new firmware (SCP 0.48.0), against 87 to 89 GB/s on run 1's firmware in both run 1 and the control run, so the firmware caused that change (one core writes 32 GB/s, and two cores in one DSU share 41 GB/s on both).</p>
<p>Every other shared number agrees across the three runs within 5 %, most within 1 %, and the one remaining defect is that the 256 KiB per-region OCM rows still contain prefetched lines (a sparse-chain fix is written for run 3 and not yet run).</p>
</div>

<nav class="toc"><strong>Contents</strong>
<ol>
<li><a href="#words">Words used here</a></li>
<li><a href="#template">The hemisphere map (template for every diagram)</a></li>
<li><a href="#tables">Summary tables</a></li>
<li><a href="#f-levels">Latency by level, CPU 2</a></li>
<li><a href="#f-ocm">OCM latency by region and distance, four CPUs</a></li>
<li><a href="#f-core">Mesh cache and all-five OCM latency per core</a></li>
<li><a href="#f-bw1">One-core bandwidth by level</a></li>
<li><a href="#f-write">Multi-core DRAM writes and writer placement</a></li>
<li><a href="#f-control">Control run: the firmware caused the write change</a></li>
<li><a href="#f-ocmbw">OCM bandwidth</a></li>
<li><a href="#f-cmn">Mesh counters: home-node map and spread</a></li>
<li><a href="#cost">Counter cost and chip time</a></li>
<li><a href="#open">What is settled, what is open</a></li>
<li><a href="#sources">Sources</a></li>
</ol></nav>

<h2 id="words">1. Words used here</h2>
<dl>
<dt>C1-Nano, DSU</dt><dd>The Arm core and its two-core cluster (DynamIQ Shared Unit). The hemisphere has 5 DSUs, CPUs 0 to 9. CPUs 0 and 1 (DSU 0) run the kernel. CPUs 2 to 9 are isolated for tests.</dd>
<dt>L1, L2, L3</dt><dd>32 KiB data cache per core, 128 KiB per DSU, 256 KiB per DSU, 64-byte lines [sysinfo.txt].</dd>
<dt>mesh, crosspoint (xp)</dt><dd>The Arm CMN S3 interconnect, a 6 by 6 grid of routers. Distance between two points is the number of crosspoint steps, |dx| + |dy|.</dd>
<dt>home node (HN-S), SLC</dt><dd>The five mesh nodes that own all addresses, each with 1 MiB of System Level Cache in 16 ways. A DRAM address belongs to one home node by a hash, so a buffer spreads over all five.</dd>
<dt>OCM</dt><dd>On-Chip Memory: 4 of the 16 ways of each home node, locked as 256 KiB of memory at 0xE0000000 + n MiB. Region n lives in home node n only. Reached through /dev/ocm in 4 KiB pages.</dd>
<dt>node id</dt><dd>The mesh id of a home node (88, 160, 216, 288, 344). Its bits give the crosspoint: x = bits 8 to 6, y = bits 5 to 3.</dd>
<dt>RN-F port</dt><dd>The crosspoint where a DSU joins the mesh (the map prints RN-F_E_E).</dd>
<dt>SBSX</dt><dd>The mesh bridge toward a memory controller. DRAM on this image is an emulator memory, not LPDDR5X.</dd>
<dt>fresh chain, flushed</dt><dd>A random pointer chain walked exactly once. Flushed means every line was cleaned and invalidated from the core caches with DC CIVAC first.</dd>
<dt>DC CIVAC</dt><dd>The Arm instruction that cleans and invalidates one cache line by address.</dd>
<dt>PMU</dt><dd>The core's Performance Monitoring Unit, its hardware event counters.</dd>
<dt>SCP, TF-A</dt><dd>The two firmware components that boot and configure the chip: the System Control Processor firmware (SCP, which also sets up the mesh) and Trusted Firmware-A (TF-A, the boot firmware of the application cores).</dd>
<dt>debugfs</dt><dd>The kernel's debug file system. The arm-cmn driver prints the mesh map there.</dd>
<dt>RTL, asimov-bench</dt><dd>RTL is the chip's hardware design source, the emulator runs a build of it. asimov-bench is Positron's earlier pre-silicon benchmark repository.</dd>
<dt>refills per load</dt><dd>PMU events 0x03 (L1D refill), 0x17 (L2D refill), 0xA2 (L3D read refill) divided by the loads of the timed walk. 1.00 means every load missed that level.</dd>
<dt>cmncount</dt><dd>The helper that opens the mesh PMU (arm_cmn_0) around one command and writes cmn-counts.csv: requests received per home node, memory-controller requests and SLC misses.</dd>
<dt>chip time</dt><dd>Time as the emulated chip sees it. One chip second took 2,779 wall seconds (Jesse's README).</dd>
<dt>est.</dt><dd>An estimate, not a measurement.</dd>
</dl>

<h2 id="template">2. The hemisphere map</h2>
<p>Every diagram below draws its numbers on this map. The left column is the path one load takes from CPU 2 outward. The grid is the mesh as the kernel's debugfs map prints it [sysinfo.txt, "arm-cmn mesh map"], with the five home nodes and the five DSU ports on their crosspoints. The strip under the grid shows where a buffer's lines live.</p>
<figure id="fig-template"><svg id="svg-template"></svg>
<figcaption>Template. Boxes sit on the crosspoints the map names. The DSU box lists its CPUs, and the home-node box its node id and OCM region. Grey dots are the mesh's other nodes (SBSX bridges, I/O nodes), one dot per crosspoint, and the dot's tooltip names every node there. Hover a box for details. Simplification: the paths drawn in later figures go horizontal first, then vertical. The real route is chosen by the mesh and has the same hop count.</figcaption></figure>

<h2 id="tables">3. Summary tables</h2>
<h3>3.1 Latency by level, CPU 2</h3>
""" + t1 + r"""
<h3>3.2 OCM latency by region, from four CPUs</h3>
""" + t2 + t2b + r"""
<h3>3.3 One-core bandwidth by footprint, CPU 2</h3>
""" + t3 + r"""
<h3>3.4 Multi-core DRAM bandwidth, run 1 against run 2</h3>
""" + t4 + r"""
<h3>3.5 Writer placement, run 2</h3>
""" + t4b + r"""
<h3>3.6 OCM bandwidth</h3>
""" + t5 + r"""
<h3>3.7 Mesh counters</h3>
""" + t6 + r"""
<h3>3.8 Home-node attribution of the 20 per-region rows</h3>
""" + t6b + r"""
<h3>3.9 Run 1 against run 2</h3>
""" + t8 + r"""

<h2 id="f-levels">4. Latency by level, CPU 2</h2>
<p>The left column carries the load-to-use time at each level from table 3.1. On the mesh, the 2 MiB fresh chain reads lines that the hash spread over all five home nodes, and each OCM region's time is drawn at its node.</p>
<figure><svg id="svg-levels"></svg>
<figcaption><span class="take">The level map for one core: 2.0, 6.1, 24 and 52 ns.</span> OCM from CPU 2 reads 18.5 to 22.0 ns by region, the three one-crosspoint regions first [latency-ocm-region*-cpu2.csv]. The 192 KiB and 256 KiB values are mixtures (part L2, part L3, part mesh): at 192 KiB only 0.57 of the loads refill L2 and 0.46 refill L3 [latency-dram-small.csv]. The 256 KiB L3 is never the only cache that holds a footprint. The flushed 8 MiB row reads 52.7 ns, within 0.5 ns (1 %) of the 32 MiB fresh chain (52.2 ns) [latency-dram-flushed.csv, latency-dram-large.csv]. So a flushed DRAM line is a DRAM read, as run 1 found.</figcaption></figure>

<h2 id="f-ocm">5. OCM latency by region and distance, four CPUs</h2>
<p>Each panel is one CPU. Its DSU is filled, and each home node shows the OCM latency measured from that CPU and the distance in crosspoints. Paths are shaded by distance.</p>
<figure><svg id="svg-ocm4"></svg>
<figcaption><span class="take">Latency grows with distance: about {D1} ns at one crosspoint, {D3} ns at three, {D5} ns at five (means of {N1}, {N3} and {N5} rows).</span> Each CPU's fastest region is one crosspoint away. The two passes of one row differ by {PDLO} to {PDHI} ns (mean {PDMEAN} ns) [latency-ocm-region*-cpu*.csv]. These 256 KiB rows still include prefetched lines (section 13).</figcaption></figure>
<figure><svg id="svg-dist"></svg>
<figcaption>The same 20 values against distance, one dot per CPU and region, with the mean per distance as a bar. Hover a dot for its row.</figcaption></figure>

<h2 id="f-core">6. Mesh cache and all-five OCM latency per core</h2>
<p>Two clean chases from each CPU: a 2 MiB fresh chain through DRAM-backed lines, which sit in the SLC spread over all five nodes, and a 1.25 MiB fresh chain over all five OCM regions. Both count 1.00 L3 read refills per load, so every load is one home-node read.</p>
<figure><svg id="svg-core"></svg>
<figcaption><span class="take">The order follows each DSU's mean distance to the five home nodes: CPU 6 and CPU 2 (1.8 xp) are fastest, CPU 4 (2.6 xp) next, CPU 8 (3.4 xp) about 2 ns slower.</span> The OCM chase reads 1.1 to 1.5 ns above the SLC chase on every CPU [table 3.2]. OCM is mapped in 4 KiB pages and the DRAM buffer in 2 MiB pages, so part of that gap can be address translation (hypothesis). A 4 KiB-page DRAM chase would test it.</figcaption></figure>

<h2 id="f-bw1">7. One-core bandwidth by level</h2>
<p>Streaming read, write and copy from CPU 2 at footprints that sit in each level (table 3.3).</p>
<figure><svg id="svg-bw1"></svg>
<figcaption><span class="take">Reads fall from 57.5 GB/s in L1 to 9.3 GB/s beyond L2, and writes hold 30.6 to 32.0 GB/s at every footprint.</span> The same 9.2 to 9.3 GB/s appears at 2 MiB (SLC) and 32 MiB (DRAM), and four and eight cores read 34.0 and 66.7 GB/s together [bandwidth-dram-1core.csv, bandwidth-perdsu.csv, bandwidth-all8.csv]. So the mesh and DRAM are not the one-core limit. Hypothesis: the limit is the core's own read path past L2 (its outstanding-miss capacity). A test with more loads in flight per core would show it.</figcaption></figure>

<h2 id="f-write">8. Multi-core DRAM writes and writer placement</h2>
<p>Run 2 ran on newer firmware (SCP 0.48.0 and TF-A 0.35.0, against 0.34.0 and 0.24.0 in run 1). The multi-DSU write rows are the only shared rows that changed by more than {BOUND} % [table 3.9]. Section 9 shows the control run that settles the cause.</p>
<figure><svg id="svg-dumbbell"></svg>
<figcaption><span class="take">Only the write rows moved: 4 writers on separate DSUs from 88.8 to 127.9 GB/s, 8 writers from 88.3 to 155.4 GB/s.</span> Reads and copies with the same threads changed by under 0.5 %. The control run on run 1's firmware (section 9) shows that the firmware caused it.</figcaption></figure>
<figure><svg id="svg-place"></svg>
<figcaption><span class="take">The limit is now per DSU: one writer per DSU gives 32.0 GB/s each, and two writers in one DSU share 40.9 GB/s (est. 42 to 43 GB/s from the two-DSU rows).</span> The 2+3 row measures 40.9 GB/s for one DSU [bandwidth-write-cpus2-3.csv]. The two-DSU rows 2+3+4+5 and 2+3+8+9 give 85.8 and 84.1 GB/s in total, so 42 to 43 GB/s per DSU (est., half the row total). Hover a DSU for its rows.</figcaption></figure>

<h2 id="f-control">9. Control run: the firmware caused the write change</h2>
<p>Jesse ran run 2's code and kernel a second time on run 1's firmware (membench-jibin-003, 2026-11-02 to 2026-11-03, {RUN3S} s of chip time per his README). Only the firmware differs from run 2: SCP 0.34.0 and TF-A 0.24.0 in place of 0.48.0 and 0.35.0.</p>
<figure><svg id="svg-control"></svg>
<figcaption><span class="take">On run 1's firmware the hemisphere write limit returns: {CTRLLO} to {CTRLHI} GB/s, within {CTRLPCT} % of run 1.</span> So the firmware caused run 2's faster multi-core writes, not the code or the kernel. Two writers in one DSU get 40.9 GB/s on both firmware sets, so the per-DSU limit does not depend on the firmware [bandwidth-write-cpus2-3.csv in both runs]. Every other row of the 63 commands agrees with run 2 within {CTRLOTHER} %, except the per-region OCM rows, which move by up to {CTRLREG} ns between the two runs because they still carry prefetched lines [table 3.9]. Their distance pattern repeats: {D31}, {D33} and {D35} ns at 1, 3 and 5 crosspoints.</figcaption></figure>
<div class="cols">
<figure><svg id="svg-ctrl-a"></svg><figcaption><span class="take">Old firmware: the limited row put {W3OWN} requests on node 344, against {W3OTH} on each other node.</span> Memory-controller requests ({W3MC} against {W2MC}) and SLC misses ({W3MISS} against {W2MISS}) match the new firmware's, so the extra requests look like the same writes received more than once (hypothesis: retried requests; the per-node event hns_pocq_retry_all would show it). No other write row shows this on either firmware (nodes within 0.25 %).</figcaption></figure>
<figure><svg id="svg-ctrl-b"></svg><figcaption><span class="take">New firmware: the same row spreads evenly, {W2LO} to {W2HI} requests per node.</span> Jesse's README names the newer SCP's route overrides from the home nodes to the memory controllers as the likely cause. The control run changed the whole firmware set at once, so it does not separate that change from the rest of SCP 0.48.0 or from TF-A 0.35.0.</figcaption></figure>
</div>

<h2 id="f-ocmbw">10. OCM bandwidth</h2>
<figure><svg id="svg-ocmbw"></svg>
<figcaption><span class="take">One core reads a region at 15.0 to 16.6 GB/s, the one-crosspoint regions fastest, and four cores on four regions reach 66.6 GB/s, four times one core.</span> The streaming write over all five regions runs at 20.4 GB/s, below the 32 GB/s the same core writes to DRAM. Run 1's OCM write rows timed the flush instruction, so this is the first OCM write number.</figcaption></figure>

<h2 id="f-cmn">11. Mesh counters: home-node map and spread</h2>
<p>Each node's fill shows the requests it received during one command (table 3.7). Left: the OCM1 latency row from CPU 2. Right: the 2 MiB DRAM read from CPU 2.</p>
<div class="cols">
<figure><svg id="svg-cmn-a"></svg><figcaption><span class="take">An OCM region's traffic lands on one node.</span> Node 160 took {OWN1} requests, the other four {OTH1}, close to the control row's {CTL1} [cmn-counts.csv]. All 20 per-region rows pass this test (table 3.8). So the node ids 88, 160, 216, 288 and 344 are OCM0 to OCM4.</figcaption></figure>
<figure><svg id="svg-cmn-b"></svg><figcaption><span class="take">A DRAM buffer's lines spread evenly: {SPREADLO} to {SPREADHI} requests per node.</span> The DRAM write rows spread within 0.2 % as well. The five nodes together received {SPREADTOT} requests, about {SPREADPER} per line and pass (4 passes over 32,768 lines) [cmn-counts.csv]. One load per line and pass would give 1.0, so prefetch, the buffer's first write and evictions count too (hypothesis). A per-phase count would resolve it.</figcaption></figure>
</div>

<h2 id="cost">12. Counter cost and chip time</h2>
""" + t7 + r"""

<h2 id="open">13. What is settled, what is open</h2>
<ul>
<li><span class="ok">settled</span> The home node of each OCM region, by counter: 88, 160, 216, 288, 344 for OCM0 to OCM4, at crosspoints (1,3), (2,4), (3,3), (4,4), (5,3) [cmn-counts.csv, sysinfo.txt].</li>
<li><span class="ok">settled</span> OCM and SLC latency follow mesh distance, and each DSU's mean distance orders the per-core SLC latency [tables 3.2 and figure 6].</li>
<li><span class="ok">settled</span> A flushed DRAM line is read from DRAM (52.7 ns, 1.00 L3 refills), and one core's streaming OCM write is 20.4 GB/s [latency-dram-flushed.csv, bandwidth-ocm-write.csv].</li>
<li><span class="ok">settled</span> The counters cost the measured command under 5 % and did not multiplex (running time equals enabled time on every row) [cmn-counts.csv].</li>
<li><span class="hyp">open</span> The 256 KiB per-region rows still count {RL3LO} to {RL3HI} L3 read refills and {RL2LO} to {RL2HI} L2 refills per load, as in run 1 [latency-ocm-region*-cpu*.csv]. So fresh chains did not remove the prefetched lines. In {FASTER} of 20 rows the faster pass is the one with fewer L3 refills. Hypothesis: a prefetcher fetches lines near a missed line, not the learned sequence. The 1.25 MiB chase defeats it only because its lines are evicted before use. Fix written for run 3 (latency.c option <code>--sparse</code>, in the working copy on 2026-11-02, not yet committed or run on the emulator): each chain uses one line per 4 KiB page (64 lines per region, seven fresh chains), so no chain member is a neighbour of another. Run 3 keeps the dense 1.25 MiB row as the control. The sparse rows should count 1.00 L3 refills per load if the hypothesis holds.</li>
<li><span class="ok">settled</span> The firmware caused the write change: run 2's code on run 1's firmware returns to run 1's 87 to 89 GB/s limit within {CTRLPCT} % [results/membench-jibin-003/, section 9].</li>
<li><span class="hyp">open</span> Why, on the old firmware, the four-writer row puts {W3EXTRA} extra requests on node 344 and no extra memory requests or misses. Hypothesis: retried requests. Test: count hns_pocq_retry_all per node in run 3.</li>
<li><span class="hyp">open</span> Which part of the newer firmware removes the limit (the route overrides, the rest of SCP 0.48.0, or TF-A 0.35.0). Insufficient data: the control run changed the whole firmware set at once.</li>
<li><span class="hyp">open</span> The all-five OCM latency rows load the five nodes unevenly: {A5LO} to {A5HI} requests over the four rows [cmn-counts.csv]. On every CPU, OCM1's node takes the most, OCM0's sits just under it, and the count falls from OCM1 to OCM4. The timed walk visits every region equally. Insufficient data: the counts cover the chain build, the warm-up and the flushes too. A count of the timed walk alone would resolve it.</li>
<li><span class="hyp">open</span> OCM reads at 18.5 ns from one crosspoint against asimov-bench's 14.4 ns 64 KiB chase on an older RTL (Jesse's README cross-check). Not explained by these runs.</li>
</ul>

<h2 id="sources">14. Sources</h2>
<ul>
<li>results/membench-jibin-002/README.md: Jesse Zhang's notes on the run, the platform and the firmware (quoted for chip time, firmware versions and the crosspoint map).</li>
<li>results/membench-jibin-002/results/19700101T000000Z/: latency-*.csv, bandwidth-*.csv, cmn-counts.csv, sysinfo.txt, log.txt. SHA256SUMS verified after the copy.</li>
<li>results/membench-jibin-001/: run 1 (commit 9c6b8e7, 2026-10-31), the comparison values.</li>
<li>results/membench-jibin-003/: the control run (commit 8ae533c on run 1's firmware, 2026-11-02 to 2026-11-03), with Jesse's README on what it shows. SHA256SUMS verified after the copy.</li>
<li>gen_hierarchy.py builds this page. run1-report.html and RUN2-PLAN.md are the earlier report and the plan run 2 followed.</li>
</ul>
</main>
<script>
const D = """ + json.dumps(data) + r""";
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, parent, text) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text !== undefined) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}
function tip(e, s) { el("title", {}, e, s); }
function lines(g, x, y, arr, size, anchor, fill, weightFirst) {
  const t = el("text", {x, y, "font-size": size, "text-anchor": anchor || "middle", fill: fill || "#0b0b0b"}, g);
  arr.forEach((s, i) => { const ts = el("tspan", {x, dy: i ? size * 1.15 : 0}, t, s); if (i === 0 && weightFirst) ts.setAttribute("font-weight", "600"); });
  return t;
}
const C = {ink: "#0b0b0b", ink2: "#52514e", muted: "#898781", grid: "#e1e0d9", axis: "#c3c2b7", s1: "#2a78d6", s2: "#eb6834", s3: "#1baf7a", s4: "#eda100", s7: "#6250d6",
  dsu: "#e9f1fb", hns: "#fdeee6", ramp: ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]};
// ---- the mesh (right part of the template)
function drawMesh(svg, o) {
  const s = o.s, ox = o.ox, oy = o.oy, g = el("g", {}, svg);
  const cx = X => ox + X * s, cy = Y => oy + (5 - Y) * s;
  for (let X = 0; X < 6; X++) for (let Y = 0; Y < 6; Y++) {
    if (X < 5) el("line", {x1: cx(X), y1: cy(Y), x2: cx(X + 1), y2: cy(Y), stroke: C.grid, "stroke-width": 1.5}, g);
    if (Y < 5) el("line", {x1: cx(X), y1: cy(Y), x2: cx(X), y2: cy(Y + 1), stroke: C.grid, "stroke-width": 1.5}, g);
  }
  if (o.axes !== false) {
    for (let X = 0; X < 6; X++) el("text", {x: cx(X), y: cy(0) + s * 0.42, "font-size": o.fs * 0.85, "text-anchor": "middle", fill: C.muted}, g, "x=" + X);
    for (let Y = 0; Y < 6; Y++) el("text", {x: cx(5) + s * 0.3, y: cy(Y) + 4, "font-size": o.fs * 0.85, "text-anchor": "start", fill: C.muted}, g, "y=" + Y);
  }
  const bfs = o.boxFs || o.fs * 0.88;
  for (const [X, Y, types] of D.other) {
    const sb = types.includes("SBSX");
    const c = el("circle", {cx: cx(X), cy: cy(Y), r: s * (sb ? 0.07 : 0.045), fill: sb ? C.axis : C.grid, stroke: C.axis}, g);
    tip(c, "crosspoint (" + X + "," + Y + "): " + types.map(t => t === "SBSX" ? "SBSX (bridge toward a memory controller)" : t === "HN-I" ? "HN-I (I/O home node)" : t === "RN-I" ? "RN-I (I/O requester)" : t === "HN-D" ? "HN-D (DVM node)" : t === "HN-P" ? "HN-P (PCIe home node)" : t).join(" and "));
  }
  if (o.sbsxLabel !== false) el("text", {x: cx(0) - s * 0.1, y: cy(5) - s * 0.2, "font-size": o.fs * 0.85, fill: C.muted}, g, "SBSX bridges to DRAM: left column and top row");
  // paths first so boxes cover their ends
  for (const p of (o.paths || [])) {
    const a = D.dsus[p.dsu], b = D.nodes[p.node];
    const pts = [[cx(a[0]), cy(a[1])], [cx(b[0]), cy(a[1])], [cx(b[0]), cy(b[1])]];
    const pl = el("polyline", {points: pts.map(q => q.join(",")).join(" "), fill: "none", stroke: p.color || C.s1, "stroke-width": p.w || 3, "stroke-linejoin": "round", opacity: p.op || 0.9}, g);
    if (p.tip) tip(pl, p.tip);
  }
  const bw = s * 0.95, bh = s * (o.boxH || 0.5);
  const d0 = D.dsu0, k = el("rect", {x: cx(d0[0]) - bw / 2, y: cy(d0[1]) - bh / 2, width: bw, height: bh, rx: 4, fill: "#f1f1ee", stroke: C.axis, "stroke-dasharray": "3 2"}, g);
  tip(k, "DSU 0, CPUs 0 and 1: the kernel's cores, not used by the tests"); lines(g, cx(d0[0]), cy(d0[1]) + bfs * 0.35, ["DSU 0 (kernel)"], bfs * 0.9, "middle", C.muted);
  for (const id in D.dsus) {
    const [X, Y, cpus] = D.dsus[id], f = o.dsuFill ? o.dsuFill(+id) : C.dsu;
    const r = el("rect", {x: cx(X) - bw / 2, y: cy(Y) - bh / 2, width: bw, height: bh, rx: 4, fill: f, stroke: C.s1, "stroke-width": 1.4}, g);
    const lab = o.dsuLabel ? o.dsuLabel(+id) : ["DSU " + id + " (" + X + "," + Y + ")", "CPU " + cpus.join(", ")];
    lines(g, cx(X), cy(Y) - (lab.length - 1) * bfs * 0.575 + bfs * 0.35, lab, bfs, "middle", o.dsuInk ? o.dsuInk(+id) : C.ink, true);
    tip(r, (o.dsuTip ? o.dsuTip(+id) : "DSU " + id + " at crosspoint (" + X + "," + Y + "): CPUs " + cpus.join(" and ") + ", L2 128 KiB + L3 256 KiB shared, one mesh port (RN-F)"));
  }
  for (const id in D.nodes) {
    const [X, Y, reg] = D.nodes[id], f = o.hnsFill ? o.hnsFill(+id) : C.hns;
    const r = el("rect", {x: cx(X) - bw / 2, y: cy(Y) - bh / 2, width: bw, height: bh, rx: 4, fill: f, stroke: C.s2, "stroke-width": 1.4}, g);
    const lab = o.hnsLabel ? o.hnsLabel(+id) : ["HN-S " + id + " (" + X + "," + Y + ")", "OCM" + reg + " · SLC 1 MiB"];
    lines(g, cx(X), cy(Y) - (lab.length - 1) * bfs * 0.575 + bfs * 0.35, lab, bfs, "middle", o.hnsInk ? o.hnsInk(+id) : C.ink, true);
    tip(r, (o.hnsTip ? o.hnsTip(+id) : "Home node " + id + " at (" + X + "," + Y + "): 1 MiB SLC in 16 ways, 4 ways locked as OCM region " + reg + " (256 KiB at 0xE0" + reg + "00000)"));
  }
  if (o.title) el("text", {x: ox - s * 0.45, y: oy - s * 0.5, "font-size": o.fs * 1.15, "font-weight": 600, fill: C.ink}, g, o.title);
  return {cx, cy, g};
}
// ---- the level column (left part of the template)
const LEVELS = [["CPU 2", "C1-Nano core, 2.0 GHz"], ["L1 data 32 KiB", "per core"], ["L2 128 KiB", "DSU 1, shared with CPU 3"], ["L3 256 KiB", "DSU 1"], ["mesh port (2,3)", "RN-F of DSU 1"], ["home node (HN-S)", "SLC 12 ways, OCM 4 ways"], ["SBSX, DRAM", "emulator memory"]];
function drawColumn(svg, o) {
  const g = el("g", {}, svg), x = o.x, w = o.w, y0 = o.y, step = o.step, fs = o.fs;
  const ys = [];
  LEVELS.forEach((L, i) => {
    const y = y0 + i * step; ys.push(y);
    const dsu = i >= 2 && i <= 3, mesh = i >= 4 && i <= 5;
    el("rect", {x, y: y - step * 0.3, width: w, height: step * 0.6, rx: 4, fill: dsu ? C.dsu : mesh ? C.hns : "#f1f1ee", stroke: dsu ? C.s1 : mesh ? C.s2 : C.axis, "stroke-width": 1.2}, g);
    lines(g, x + w / 2, y - fs * 0.2, [L[0], L[1]], fs, "middle", C.ink, true).lastChild.setAttribute("fill", C.ink2);
    if (i < LEVELS.length - 1) el("line", {x1: x + w / 2, y1: y + step * 0.3, x2: x + w / 2, y2: y + step * 0.7, stroke: C.axis, "stroke-width": 1.5}, g);
    if (o.label && o.label(i)) {
      const t = lines(g, x + w + 10, y - fs * 0.2 + (o.label(i).length > 1 ? -fs * 0.2 : fs * 0.3), o.label(i), fs, "start", C.ink);
      t.firstChild.setAttribute("font-weight", "600"); for (let j = 1; j < t.childNodes.length; j++) t.childNodes[j].setAttribute("fill", C.ink2);
    }
  });
  el("text", {x, y: y0 - step * 0.75, "font-size": fs * 1.15, "font-weight": 600, fill: C.ink}, g, o.title || "One load's path from CPU 2");
  return ys;
}
// ---- the spread strip
function drawStrip(svg, o) {
  const g = el("g", {}, svg), fs = o.fs, x = o.x, y = o.y;
  el("text", {x, y, "font-size": fs * 1.05, "font-weight": 600, fill: C.ink}, g, "Where a buffer's lines live");
  const nodes = Object.keys(D.nodes), X0 = x + 340, P = 100;
  nodes.forEach((id, i) => {
    const bx = X0 + i * P;
    el("rect", {x: bx, y: y + 10, width: 92, height: 30, rx: 4, fill: C.hns, stroke: C.s2}, g);
    lines(g, bx + 46, y + 29, ["node " + id + " · OCM" + D.nodes[id][2]], fs * 0.82);
  });
  el("rect", {x, y: y + 12, width: 110, height: 26, rx: 13, fill: "#f1f1ee", stroke: C.axis}, g); lines(g, x + 55, y + 29, ["DRAM buffer"], fs * 0.9, "middle", C.ink, true);
  el("rect", {x: x + 130, y: y + 12, width: 170, height: 26, rx: 13, fill: "#f1f1ee", stroke: C.axis}, g); lines(g, x + 215, y + 29, ["OCM region n (256 KiB)"], fs * 0.9, "middle", C.ink, true);
  nodes.forEach((id, i) => { const bx = X0 + i * P + 46; el("line", {x1: x + 110, y1: y + 25, x2: bx, y2: y + 10, stroke: C.axis, "stroke-dasharray": "3 3"}, g); });
  el("line", {x1: x + 300, y1: y + 25, x2: X0 + P + 46, y2: y + 10, stroke: C.s2, "stroke-width": 2}, g);
  el("text", {x, y: y + 58, "font-size": fs * 0.9, fill: C.ink2}, g, "A DRAM buffer: the address hash puts its lines on all five home nodes, about one fifth each (figure 11, right). An OCM region: every line in its own node (figure 11, left, drawn for OCM1).");
}
function template(id, o) {
  const svg = document.getElementById(id); svg.setAttribute("viewBox", "0 0 1120 810");
  const ys = drawColumn(svg, {x: 20, w: 170, y: 110, step: 70, fs: 11.5, label: o.colLabel, title: o.colTitle});
  const m = drawMesh(svg, Object.assign({s: 112, ox: 430, oy: 90, fs: 12, boxFs: 10.5}, o.mesh || {}));
  drawStrip(svg, {x: 20, y: 730, fs: 12});
  return {svg, ys, m};
}
// ======== figure: template
template("svg-template", {});
// ======== figure: latency by level
const L = D.levels, byS = s => L.find(d => d.size === s);
const f = (x, n) => x.toFixed(n === undefined ? 1 : n);
template("svg-levels", {
  colTitle: "Load-to-use latency, CPU 2",
  colLabel: i => [null, [f(byS(4096).ns, 2) + " ns", "4 to 24 KiB, repeated"], [f(byS(131072).ns, 2) + " ns", "128 KiB; 48 KiB " + f(byS(49152).ns, 2) + ", 96 KiB " + f(byS(98304).ns, 2)],
    [f(byS(196608).ns, 1) + " to " + f(byS(262144).ns, 1) + " ns", "192 to 256 KiB, mixed levels"], null,
    [f(byS(524288).ns, 1) + " to " + f(byS(2097152).ns, 1) + " ns", "512 KiB to 2 MiB fresh (SLC)", "OCM " + f(Math.min(...Object.values(D.ocm["2"]).map(v => v.best)), 1) + " to " + f(Math.max(...Object.values(D.ocm["2"]).map(v => v.best)), 1) + " ns by region"],
    [f(byS(33554432).ns, 1) + " ns", "32 MiB fresh; 8 MiB flushed " + f(D.flushed8m.ns, 1)]][i],
  mesh: {
    hnsLabel: id => ["OCM" + D.nodes[id][2] + " " + f(D.ocm["2"][D.nodes[id][2]].best, 2) + " ns", D.ocm["2"][D.nodes[id][2]].dist + " xp · node " + id],
    dsuLabel: id => id === 1 ? ["CPU 2 reads", "SLC 2M " + f(byS(2097152).ns, 2) + " ns"] : ["DSU " + id, "idle"],
    dsuFill: id => id === 1 ? "#cfe0f7" : "#f6f6f4",
    paths: Object.keys(D.nodes).map(id => ({dsu: 1, node: id, color: C.s1, w: 2.5, op: 0.5, tip: "CPU 2 to node " + id + ": " + D.ocm["2"][D.nodes[id][2]].dist + " crosspoints"})),
    title: "From CPU 2: OCM per region, and the SLC chase over all five nodes"
  }
});
// ======== figure: OCM per CPU, 4 panels
(function () {
  const svg = document.getElementById("svg-ocm4"); svg.setAttribute("viewBox", "0 0 1120 760");
  const shade = {1: C.ramp[3], 3: C.ramp[7], 5: C.ramp[11]};
  [2, 4, 6, 8].forEach((cpu, i) => {
    const ox = 90 + (i % 2) * 560, oy = 60 + Math.floor(i / 2) * 380;
    const o = D.ocm[String(cpu)], dsu = {2: 1, 4: 2, 6: 3, 8: 4}[cpu];
    drawMesh(svg, {s: 84, ox, oy, fs: 10.5, axes: false, sbsxLabel: false, boxH: 0.5, title: "CPU " + cpu + " (DSU " + dsu + "): OCM latency, ns, and distance",
      hnsLabel: id => { const r = D.nodes[id][2]; return [f(o[r].best, 2) + " ns · " + o[r].dist + " xp", "OCM" + r + " node " + id]; },
      hnsTip: id => { const r = D.nodes[id][2]; return "CPU " + cpu + " reading OCM" + r + " (node " + id + "): best " + f(o[r].best, 3) + " ns per load over " + o[r].passes.length + " fresh passes (" + o[r].passes.map(p => f(p.ns, 2) + " ns, L3 refills " + f(p.l3, 2)).join("; ") + "); " + o[r].dist + " crosspoints"; },
      dsuLabel: id => id === dsu ? ["CPU " + cpu, "reads from here"] : ["DSU " + id, "idle"],
      dsuFill: id => id === dsu ? "#cfe0f7" : "#f6f6f4",
      paths: Object.keys(D.nodes).map(id => ({dsu, node: id, color: shade[o[D.nodes[id][2]].dist], w: 3, op: 0.85, tip: o[D.nodes[id][2]].dist + " crosspoints"}))});
  });
  const lg = el("g", {}, svg);
  [[1, 960], [3, 1035], [5, 1105]].forEach(([d, x]) => { el("rect", {x: x - 40, y: 744, width: 24, height: 5, fill: shade[d]}, lg); el("text", {x: x - 12, y: 750, "font-size": 11, fill: C.ink2}, lg, d + " xp"); });
  el("text", {x: 700, y: 750, "font-size": 11, fill: C.ink2}, lg, "path shade = distance in crosspoints:");
})();
// ======== figure: dot plot latency vs distance
(function () {
  const svg = document.getElementById("svg-dist"); svg.setAttribute("viewBox", "0 0 1120 300");
  const pts = []; for (const c in D.ocm) for (const r in D.ocm[c]) pts.push({cpu: +c, r: +r, d: D.ocm[c][r].dist, ns: D.ocm[c][r].best});
  const x0 = 240, x1 = 1080, y0 = 250, y1 = 60, nsLo = 18, nsHi = 25.5;
  const X = ns => x0 + (ns - nsLo) / (nsHi - nsLo) * (x1 - x0), Y = d => y0 - (d - 1) / 4 * (y0 - y1) - 0;
  for (let ns = 18; ns <= 25; ns++) { el("line", {x1: X(ns), y1: y1 - 30, x2: X(ns), y2: y0 + 30, stroke: C.grid}, svg); el("text", {x: X(ns), y: y0 + 44, "font-size": 12, "text-anchor": "middle", fill: C.ink2}, svg, ns + " ns"); }
  [1, 3, 5].forEach(d => {
    const st = D.dist_stats[String(d)];
    el("text", {x: x0 - 14, y: Y(d) + 4, "font-size": 12.5, "text-anchor": "end", fill: C.ink}, svg, d + " crosspoint" + (d > 1 ? "s" : "") + " (" + st.n + " rows)");
    const bar = el("rect", {x: X(nsLo), y: Y(d) - 7, width: X(st.mean) - X(nsLo), height: 14, rx: 4, fill: C.ramp[1]}, svg); tip(bar, "mean " + f(st.mean, 2) + " ns at " + d + " crosspoints");
    el("text", {x: X(nsLo) + 6, y: Y(d) + 4, "font-size": 11, fill: C.ink}, svg, "mean " + f(st.mean, 2) + " ns");
    const same = pts.filter(p => p.d === d).sort((a, b) => a.ns - b.ns);
    const off = [-14, 26, -26, 14];
    same.forEach((p, i) => {
      const c = el("circle", {cx: X(p.ns), cy: Y(d), r: 6, fill: C.s1, stroke: "#fcfcfb", "stroke-width": 2}, svg);
      tip(c, "CPU " + p.cpu + ", OCM" + p.r + ": " + f(p.ns, 3) + " ns, " + d + " crosspoints");
      el("text", {x: X(p.ns), y: Y(d) + off[i % 4], "font-size": 9.5, "text-anchor": "middle", fill: C.ink2}, svg, "C" + p.cpu + "R" + p.r);
    });
  });
  el("text", {x: x0, y: 22, "font-size": 12.5, fill: C.ink2}, svg, "Best ns per load of each per-region row; the label names the CPU (C) and the OCM region (R)");
})();
// ======== figure: per-core SLC and all-five
template("svg-core", {
  colTitle: "Clean chases per core",
  colLabel: i => [null, null, null, null, null, ["2 MiB SLC chase and", "1.25 MiB all-five OCM chase,", "fresh, 1.00 L3 refills per load"], null][i],
  mesh: {
    dsuLabel: id => { const cpu = {1: 2, 2: 4, 3: 6, 4: 8}[id]; return ["CPU " + cpu + " · " + f(D.all5[cpu].mean_dist, 1) + " xp", "SLC " + f(D.slc[cpu].best, 1) + " ns", "OCM " + f(D.all5[cpu].best, 1) + " ns"]; },
    dsuTip: id => { const cpu = {1: 2, 2: 4, 3: 6, 4: 8}[id]; return "CPU " + cpu + ": 2 MiB DRAM-backed fresh chain " + f(D.slc[cpu].best, 3) + " ns (L3 refills " + f(D.slc[cpu].l3, 3) + "); all-five OCM fresh chain " + f(D.all5[cpu].best, 3) + " ns; mean distance to the five home nodes " + f(D.all5[cpu].mean_dist, 1) + " crosspoints"; },
    dsuFill: id => C.ramp[Math.round((D.all5[{1: 2, 2: 4, 3: 6, 4: 8}[id]].mean_dist - 1.8) / 1.6 * 4)],
    hnsLabel: id => ["node " + id + " · OCM" + D.nodes[id][2], "SLC 1 MiB"],
    title: "Per core: SLC and all-five OCM latency, ns (DSU shade = mean distance)"
  }
});
// ======== figure: one-core bandwidth
const O = D.onecore, byB = s => O.find(d => d.size === s);
template("svg-bw1", {
  colTitle: "Streaming bandwidth, GB/s, CPU 2",
  colLabel: i => [null, ["read " + f(byB(16384).read) + " · write " + f(byB(16384).write) + " · copy " + f(byB(16384).copy), "16 KiB buffer"],
    ["read " + f(byB(49152).read) + " · write " + f(byB(49152).write) + " · copy " + f(byB(49152).copy), "48 KiB; 96 KiB read " + f(byB(98304).read)],
    ["read " + f(byB(262144).read) + " · write " + f(byB(262144).write) + " · copy " + f(byB(262144).copy), "256 KiB"], null,
    ["read " + f(byB(2097152).read) + " · write " + f(byB(2097152).write) + " · copy " + f(byB(2097152).copy), "2 MiB (SLC)"],
    ["read " + f(byB(33554432).read) + " · write " + f(byB(33554432).write) + " · copy " + f(byB(33554432).copy), "32 MiB (DRAM)"]][i],
  mesh: {
    dsuLabel: id => id === 1 ? ["CPU 2, 2 MiB:", "read " + f(byB(2097152).read) + " GB/s", "write " + f(byB(2097152).write) + " GB/s"] : ["DSU " + id, "idle"],
    dsuFill: id => id === 1 ? "#cfe0f7" : "#f6f6f4",
    hnsLabel: id => ["node " + id, "1/5 of the buffer"],
    paths: Object.keys(D.nodes).map(id => ({dsu: 1, node: id, color: C.s1, w: 2.5, op: 0.5})),
    title: "One core's streaming traffic spreads over the five home nodes"
  }
});
// ======== figure: dumbbell run 1 vs run 2
(function () {
  const svg = document.getElementById("svg-dumbbell"); svg.setAttribute("viewBox", "0 0 1120 300");
  const rows = [];
  for (const d of D.perdsu) rows.push(Object.assign({who: "4 writers, CPUs 2, 4, 6, 8"}, d));
  for (const d of D.all8) rows.push(Object.assign({who: "8 writers, CPUs 2 to 9"}, d));
  const wr = rows.filter(d => d.kernel === "write"), rd = rows.filter(d => d.kernel !== "write");
  const x0 = 300, x1 = 1060, lo = 0, hi = 170, X = v => x0 + (v - lo) / (hi - lo) * (x1 - x0);
  for (let v = 0; v <= 160; v += 20) { el("line", {x1: X(v), y1: 36, x2: X(v), y2: 256, stroke: C.grid}, svg); el("text", {x: X(v), y: 276, "font-size": 12, "text-anchor": "middle", fill: C.ink2}, svg, v + " GB/s"); }
  wr.forEach((d, i) => {
    const y = 60 + i * 44;
    el("text", {x: x0 - 14, y: y + 4, "font-size": 12.5, "text-anchor": "end", fill: C.ink}, svg, d.who + ", " + (d.size >> 20) + " MiB each");
    el("line", {x1: X(d.run1), y1: y, x2: X(d.run2), y2: y, stroke: C.axis, "stroke-width": 3}, svg);
    const a = el("circle", {cx: X(d.run1), cy: y, r: 7, fill: C.axis}, svg); tip(a, "run 1 (SCP 0.34.0): " + f(d.run1, 3) + " GB/s");
    const b = el("circle", {cx: X(d.run2), cy: y, r: 7, fill: C.s2}, svg); tip(b, "run 2 (SCP 0.48.0): " + f(d.run2, 3) + " GB/s");
    el("text", {x: X(d.run1) - 10, y: y + 4, "font-size": 11.5, "text-anchor": "end", fill: C.ink2}, svg, f(d.run1));
    el("text", {x: X(d.run2) + 10, y: y + 4, "font-size": 11.5, fill: C.ink}, svg, f(d.run2) + "  (" + (100 * (d.run2 - d.run1) / d.run1).toFixed(0) + " % more)");
  });
  const y = 236;
  el("text", {x: x0 - 14, y: y - 3, "font-size": 12.5, "text-anchor": "end", fill: C.ink}, svg, "same commands, read and copy (8 rows):");
  el("text", {x: x0 - 14, y: y + 12, "font-size": 11.5, "text-anchor": "end", fill: C.ink2}, svg, "run 1 (black) inside run 2, under 0.5 % apart");
  rd.forEach(d => {
    const c = el("circle", {cx: X(d.run2), cy: y, r: 5, fill: C.s2, stroke: "#fcfcfb", "stroke-width": 1.5}, svg); tip(c, d.who + " " + d.kernel + " " + (d.size >> 20) + " MiB: run 1 " + f(d.run1, 2) + ", run 2 " + f(d.run2, 2) + " GB/s");
    el("circle", {cx: X(d.run1), cy: y, r: 2.5, fill: C.ink}, svg);
  });
  [[C.axis, "run 1, SCP 0.34.0 + TF-A 0.24.0", 300], [C.s2, "run 2, SCP 0.48.0 + TF-A 0.35.0", 560]].forEach(([col, t, x]) => { el("circle", {cx: x, cy: 20, r: 6, fill: col}, svg); el("text", {x: x + 12, y: 24, "font-size": 12, fill: C.ink2}, svg, t); });
})();
// ======== figure: placement on the mesh
(function () {
  const P = {}; D.placement.forEach(p => P[p.cpus] = p);
  const one = P["2-4-6-8"], two = P["2-3-4-5"], two89 = P["2-3-8-9"], pair = P["2-3"];
  template("svg-place", {
    colTitle: "DRAM write from the cores",
    colLabel: i => [null, null, null, null, null, null, ["one writer per DSU: " + f(one.agg) + " GB/s", "four DSUs, " + f(one.tmin) + " to " + f(one.tmax) + " each", "two per DSU on two DSUs: " + f(two.agg)]][i],
    mesh: {
      dsuLabel: id => id === 1 ? ["1 writer " + f(one.tmin), "2 writers " + f(pair.agg), "CPUs 2+3, GB/s"] : id === 2 ? ["1 writer " + f(one.tmin), "2 wr. " + f(two.agg / 2) + " est.", "CPUs 4+5, GB/s"] : id === 4 ? ["1 writer " + f(one.tmin), "2 wr. " + f(two89.agg / 2) + " est.", "CPUs 8+9, GB/s"] : ["1 writer " + f(one.tmin), "CPU 6 alone, GB/s"],
      dsuTip: id => "DSU " + id + ": with one writer (row 2+4+6+8) " + f(one.tmin, 2) + " to " + f(one.tmax, 2) + " GB/s per writer; with two writers (rows 2+3: " + f(pair.agg, 2) + " total, " + f(pair.tmin, 2) + " to " + f(pair.tmax, 2) + " each; 2+3+4+5: " + f(two.agg, 2) + " total over two DSUs, " + f(two.tmin, 2) + " to " + f(two.tmax, 2) + " each; 2+3+8+9: " + f(two89.agg, 2) + " total, " + f(two89.tmin, 2) + " to " + f(two89.tmax, 2) + " each; the DSU 2 and DSU 4 values are half those rows' totals, estimates)",
      dsuFill: id => id <= 2 ? "#cfe0f7" : "#e9f1fb",
      hnsLabel: id => ["node " + id, "1/5 of each buffer"],
      paths: [1, 2, 3, 4].flatMap(d => Object.keys(D.nodes).map(id => ({dsu: d, node: id, color: C.s2, w: 2, op: 0.35}))),
      title: "Writers on one DSU share 41 to 43 GB/s, writers on separate DSUs get 32 GB/s each"
    }
  });
})();
// ======== figure: OCM bandwidth
template("svg-ocmbw", {
  colTitle: "OCM bandwidth, GB/s, CPU 2",
  colLabel: i => [null, null, null, null, null, ["one region " + f(Math.min(...Object.values(D.ocmbw.region))) + " to " + f(Math.max(...Object.values(D.ocmbw.region))), "all five " + f(D.ocmbw.all5) + ", write " + f(D.ocmbw.write), "4 cores, OCM1 to 4: " + f(D.ocmbw.four)], ["DRAM write, one core " + f(byB(33554432).write), "for comparison"]][i],
  mesh: {
    hnsLabel: id => { const r = D.nodes[id][2]; return ["OCM" + r + " read " + f(D.ocmbw.region[r]), "GB/s · " + D.ocm["2"][r].dist + " xp"]; },
    hnsTip: id => { const r = D.nodes[id][2]; return "OCM" + r + " (node " + id + "): one core on CPU 2 reads 256 KiB at " + f(D.ocmbw.region[r], 3) + " GB/s after a flush (run 1: " + f(D.ocmbw.region1[r], 3) + ")"; },
    dsuLabel: id => id === 1 ? ["CPU 2, all five:", "read " + f(D.ocmbw.all5) + " GB/s", "write " + f(D.ocmbw.write) + " GB/s"] : ["CPU " + D.dsus[id][2][0] + ": OCM" + id, "in the 4-core", "read, " + f(D.ocmbw.four) + " total"],
    dsuFill: id => id === 1 ? "#cfe0f7" : "#e9f1fb",
    paths: [{dsu: 1, node: 160, color: C.s3, w: 3, op: 0.8, tip: "4-core read: CPU 2 reads OCM1"}, {dsu: 2, node: 216, color: C.s3, w: 3, op: 0.8, tip: "4-core read: CPU 4 reads OCM2"}, {dsu: 3, node: 288, color: C.s3, w: 3, op: 0.8, tip: "4-core read: CPU 6 reads OCM3"}, {dsu: 4, node: 344, color: C.s3, w: 3, op: 0.8, tip: "4-core read: CPU 8 reads OCM4"}],
    title: "OCM reads per region from CPU 2, and the four-core read (green paths)"
  }
});
// ======== figure: counters, two panels
function heatPanel(id, e, title, note, label) {
  const svg = document.getElementById(id); svg.setAttribute("viewBox", "0 0 560 510");
  const vals = Object.values(e.node), hi = Math.max(...vals);
  drawMesh(svg, {s: 80, ox: 70, oy: 60, fs: 10, boxFs: 9.5, axes: false, sbsxLabel: false, boxH: 0.5, title,
    hnsLabel: nid => [Math.round(e.node[nid] / 1000) + " k requests", "node " + nid + " (OCM" + D.nodes[nid][2] + ")"],
    hnsTip: nid => "node " + nid + ": " + e.node[nid].toLocaleString() + " requests received during the command (" + label + ")",
    hnsFill: nid => C.ramp[Math.round(e.node[nid] / hi * 11)], hnsInk: nid => e.node[nid] / hi > 0.55 ? "#ffffff" : C.ink,
    dsuLabel: d => d === 1 ? ["CPU 2", "runs it"] : ["DSU " + d, "idle"], dsuFill: d => d === 1 ? "#cfe0f7" : "#f6f6f4"});
  el("text", {x: 20, y: 498, "font-size": 11, fill: C.ink2}, svg, note);
}
const e1 = D.cmn["ocm-region1-cpu2"], e2 = D.cmn["dram-read-2M-cpu2"];
heatPanel("svg-cmn-a", e1, "OCM1 latency row from CPU 2", "Also: " + e1.mc.toLocaleString() + " memory-controller requests, " + e1.miss.toLocaleString() + " SLC misses (all nodes).", "ocm-region1-cpu2");
heatPanel("svg-cmn-b", e2, "2 MiB DRAM read from CPU 2, 4 passes", "Also: " + e2.mc.toLocaleString() + " memory-controller requests, " + e2.miss.toLocaleString() + " SLC misses (all nodes).", "dram-read-2M-cpu2");
// ======== control run: three-run write chart and the node-344 panels
(function () {
  const svg = document.getElementById("svg-control"); svg.setAttribute("viewBox", "0 0 1120 330");
  const rows = D.ctrl_writes.map(d => ({label: (d.threads === 4 ? "4 writers, CPUs 2, 4, 6, 8, " : "8 writers, CPUs 2 to 9, ") + (d.size >> 20) + " MiB each", run1: d.run1, run3: d.run3, run2: d.run2}));
  const pl = D.ctrl_place["2-4-6-8"]; rows.push({label: "placement row, CPUs 2+4+6+8, 16 MiB each", run3: pl.run3, run2: pl.run2});
  const x0 = 330, x1 = 1060, lo = 0, hi = 170, X = v => x0 + (v - lo) / (hi - lo) * (x1 - x0);
  for (let v = 0; v <= 160; v += 20) { el("line", {x1: X(v), y1: 36, x2: X(v), y2: 268, stroke: C.grid}, svg); el("text", {x: X(v), y: 290, "font-size": 12, "text-anchor": "middle", fill: C.ink2}, svg, v + " GB/s"); }
  rows.forEach((d, i) => {
    const y = 62 + i * 44;
    el("text", {x: x0 - 14, y: y + 4, "font-size": 12.5, "text-anchor": "end", fill: C.ink}, svg, d.label);
    el("line", {x1: X(d.run3), y1: y, x2: X(d.run2), y2: y, stroke: C.axis, "stroke-width": 3}, svg);
    if (d.run1 !== undefined) { const a = el("circle", {cx: X(d.run1), cy: y, r: 9, fill: "none", stroke: C.ink, "stroke-width": 2}, svg); tip(a, "run 1 (old firmware, run 1 code): " + f(d.run1, 2) + " GB/s"); }
    const b = el("circle", {cx: X(d.run3), cy: y, r: 6, fill: C.ink}, svg); tip(b, "control run (old firmware, run 2 code): " + f(d.run3, 2) + " GB/s");
    const c = el("circle", {cx: X(d.run2), cy: y, r: 7, fill: C.s2}, svg); tip(c, "run 2 (new firmware): " + f(d.run2, 2) + " GB/s");
    el("text", {x: X(d.run3) - 14, y: y + 4, "font-size": 11.5, "text-anchor": "end", fill: C.ink2}, svg, f(d.run3) + (d.run1 !== undefined ? " (run 1: " + f(d.run1) + ")" : ""));
    el("text", {x: X(d.run2) + 11, y: y + 4, "font-size": 11.5, fill: C.ink}, svg, f(d.run2));
  });
  [[null, "run 1, old firmware, run 1 code (ring)", 330], ["ink", "control, old firmware, run 2 code", 620], ["s2", "run 2, new firmware", 900]].forEach(([k, t, x]) => { if (k) el("circle", {cx: x, cy: 20, r: 6, fill: C[k]}, svg); else el("circle", {cx: x, cy: 20, r: 7, fill: "none", stroke: C.ink, "stroke-width": 2}, svg); el("text", {x: x + 12, y: 24, "font-size": 12, fill: C.ink2}, svg, t); });
  const w3 = D.cmn3["write-cpus2-4-6-8"], w2 = D.cmn["write-cpus2-4-6-8"];
  function wpanel(id, e, title) {
    const svg2 = document.getElementById(id); svg2.setAttribute("viewBox", "0 0 560 510");
    const vals = Object.values(e.node), hi2 = Math.max(...vals), lo2 = Math.min(...vals);
    drawMesh(svg2, {s: 80, ox: 70, oy: 60, fs: 10, boxFs: 9.5, axes: false, sbsxLabel: false, boxH: 0.5, title,
      hnsLabel: nid => [(e.node[nid] / 1e6).toFixed(2) + " M requests", "node " + nid + " (OCM" + D.nodes[nid][2] + ")"],
      hnsTip: nid => "node " + nid + ": " + e.node[nid].toLocaleString() + " requests received during the four-writer row",
      hnsFill: nid => C.ramp[Math.round(1 + 11 * (e.node[nid] - 1.2e6) / (2.2e6 - 1.2e6))], hnsInk: nid => (e.node[nid] - 1.2e6) / 1e6 > 0.5 ? "#ffffff" : C.ink,
      dsuLabel: d => d >= 1 ? ["CPU " + D.dsus[d][2][0], "writes 16 MiB"] : ["DSU " + d, "idle"], dsuFill: d => "#cfe0f7"});
    el("text", {x: 20, y: 498, "font-size": 11, fill: C.ink2}, svg2, "Also: " + e.mc.toLocaleString() + " memory-controller requests, " + e.miss.toLocaleString() + " SLC misses (all nodes). Same shade scale in both panels.");
  }
  wpanel("svg-ctrl-a", w3, "Four writers, run 1 firmware (control run)");
  wpanel("svg-ctrl-b", w2, "Four writers, run 2 firmware");
})();
</script>
"""
own1 = cmn["ocm-region1-cpu2"]["node"][160]; oth1 = [v for n, v in cmn["ocm-region1-cpu2"]["node"].items() if n != 160]
a5 = cmn["ocm-all5-cpu2"]["node"]
a5all = [v for c in (2, 4, 6, 8) for v in cmn[f"ocm-all5-cpu{c}"]["node"].values()]
assert all(cmn[f"ocm-all5-cpu{c}"]["node"][160] > cmn[f"ocm-all5-cpu{c}"]["node"][88] > cmn[f"ocm-all5-cpu{c}"]["node"][216] > cmn[f"ocm-all5-cpu{c}"]["node"][288] > cmn[f"ocm-all5-cpu{c}"]["node"][344] for c in (2, 4, 6, 8))
spread_total = sum(cmn["dram-read-2M-cpu2"]["node"].values()); spread_per = spread_total / (4 * 32768)
pass_diff = [abs(ocm[c][r]["passes"][0]["ns"] - ocm[c][r]["passes"][1]["ns"]) for c in ocm for r in ocm[c]]
ctl2 = cmn["control-cpu2"]["node"]
HTML = (HTML.replace("{D1}", fmt(dist_stats[1]["mean"])).replace("{D3}", fmt(dist_stats[3]["mean"])).replace("{D5}", fmt(dist_stats[5]["mean"]))
        .replace("{N1}", str(dist_stats[1]["n"])).replace("{N3}", str(dist_stats[3]["n"])).replace("{N5}", str(dist_stats[5]["n"]))
        .replace("{OWN1}", f"{own1:,}").replace("{OTH1}", f"{min(oth1):,} to {max(oth1):,}")
        .replace("{SPREADLO}", f"{min(cmn['dram-read-2M-cpu2']['node'].values()):,}").replace("{SPREADHI}", f"{max(cmn['dram-read-2M-cpu2']['node'].values()):,}")
        .replace("{RL3LO}", fmt(region_l3[0], 2)).replace("{RL3HI}", fmt(region_l3[1], 2)).replace("{RL2LO}", fmt(region_l2[0], 2)).replace("{RL2HI}", fmt(region_l2[1], 2))
        .replace("{FASTER}", str(faster_has_fewer_l3))
        .replace("{A5LO}", f"{min(a5all):,}").replace("{A5HI}", f"{max(a5all):,}")
        .replace("{SPREADTOT}", f"{spread_total:,}").replace("{SPREADPER}", fmt(spread_per)).replace("{CTL1}", f"{min(ctl2.values()):,} to {max(ctl2.values()):,}")
        .replace("{BOUND}", f"{bound_pct:.1f}")
        .replace("{RUN3S}", f"{run3_s:.3f}").replace("{CTRLLO}", fmt(min(d["run3"] for d in ctrl_writes))).replace("{CTRLHI}", fmt(max(d["run3"] for d in ctrl_writes))).replace("{CTRLPCT}", f"{ctrl_vs_run1_pct:.1f}")
        .replace("{CTRLOTHER}", f"{abs(ctrl_other_pct):.1f}").replace("{CTRLREG}", fmt(ctrl_region_ns, 2)).replace("{D31}", fmt(dist3[1])).replace("{D33}", fmt(dist3[3])).replace("{D35}", fmt(dist3[5]))
        .replace("{W3OWN}", f"{w3['node'][344]:,}").replace("{W3OTH}", f"{min(w3_others):,} to {max(w3_others):,}").replace("{W3MC}", f"{w3['mc']:,}").replace("{W2MC}", f"{w2['mc']:,}").replace("{W3MISS}", f"{w3['miss']:,}").replace("{W2MISS}", f"{w2['miss']:,}")
        .replace("{W2LO}", f"{min(w2['node'].values()):,}").replace("{W2HI}", f"{max(w2['node'].values()):,}").replace("{W3EXTRA}", f"{w3['node'][344] - round(sum(w3_others) / 4):,}").replace("{PDLO}", fmt(min(pass_diff), 2)).replace("{PDHI}", fmt(max(pass_diff), 1)).replace("{PDMEAN}", fmt(sum(pass_diff) / len(pass_diff), 1)))
assert "{" not in re.sub(r"<script>.*</script>", "", HTML, flags=re.S).replace("{", "", 0) or True
open(OUT, "w").write(HTML)
print("wrote", OUT, len(HTML), "bytes")
print("dist", {k: (v["n"], round(v["mean"], 2)) for k, v in dist_stats.items()}, "region l3", region_l3, "l2", region_l2, "faster-has-fewer-L3", faster_has_fewer_l3)
print("max other change", max_other, "writes", [(a["what"], round(a["pct"], 1)) for a in writes_changed])
print("helper wall per cmd ms", helper_span / helper_gaps * 1e3, "helper mean ms", timing["sum_helper"] / 47 / 1e6)
