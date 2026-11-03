#!/usr/bin/env python3
"""Parse run 2 (membench-jibin-002) per RUN2-PLAN.md section 4 and compare with run 1."""
import csv, glob, os, re, sys, collections
A = "/home/jhan/workspace/titan/cache-perf/asimov/results"
R1 = glob.glob(A + "/membench-jibin-001/results/*/")[0]
R2 = glob.glob(A + "/membench-jibin-002/results/*/")[0]

def lat_rows(path):
    """yield dicts for every data row of a latency csv (several sweeps per file possible)"""
    out = []
    size = None
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("# size="):
            m = re.search(r"size=(\d+) lines=(\d+) backing=(\S+)", line); size = m.groups()
            continue
        if line.startswith("#") or line.startswith("mem,"): continue
        f = line.split(",")
        d = dict(mem=f[0], size=int(f[1]), mode=f[2], rep=f[3], loads=f[4], ns=float(f[5]), backing=size[2] if size else "?")
        if len(f) >= 10:
            d.update(cyc=float(f[6]), l1=float(f[7]), l2=float(f[8]), l3=float(f[9]))
        out.append(d)
    return out

def bw_rows(path):
    out = []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("#") or line.startswith("mem,"): continue
        f = line.split(",")
        out.append(dict(mem=f[0], kernel=f[1], threads=int(f[2]), bpt=int(f[3]), rep=f[4], agg=float(f[7]),
                        tmin=f[8], tmax=f[9]))
    return out

print("=" * 70); print("A. latency best rows, run 2 (and run 1 where the same file/size exists)")
r1best = {}
for p in sorted(glob.glob(R1 + "latency-*.csv")):
    for d in lat_rows(p):
        if d["mode"] == "best": r1best[(os.path.basename(p), d["mem"], d["size"])] = d["ns"]
for p in sorted(glob.glob(R2 + "latency-*.csv")):
    name = os.path.basename(p)
    rows = lat_rows(p)
    for d in rows:
        if d["mode"] != "best": continue
        k = (name, d["mem"], d["size"])
        r1 = r1best.get(k)
        delta = f"  run1 {r1:7.3f}  {100*(d['ns']-r1)/r1:+5.1f}%" if r1 else ""
        print(f"{name:32s} {d['mem']:4s} {d['size']:>9d} {d['ns']:8.3f} ns{delta}")

print("=" * 70); print("B. per-region OCM rows: refills per load per pass (defect 1 check), and the hop table")
hop = {}
for c in (2, 4, 6, 8):
    for r in range(5):
        rows = lat_rows(f"{R2}latency-ocm-region{r}-cpu{c}.csv")
        passes = [d for d in rows if d["mode"].startswith("fresh")]
        best = [d for d in rows if d["mode"] == "best"][0]["ns"]
        hop[(c, r)] = best
        print(f"cpu{c} region{r}: best {best:6.2f}  passes " + "  ".join(f"{d['ns']:6.2f}(L2 {d['l2']:.2f} L3 {d['l3']:.2f})" for d in passes))
print("hop table (best ns): rows=cpu, cols=region0..4, all5, slc2M")
for c in (2, 4, 6, 8):
    a5 = [d for d in lat_rows(f"{R2}latency-ocm-all5-cpu{c}.csv") if d["mode"] == "best"][0]
    slcf = f"{R2}latency-dram-slc-cpu{c}.csv" if c != 2 else f"{R2}latency-dram-large.csv"
    slc = [d for d in lat_rows(slcf) if d["mode"] == "best" and d["size"] == 2097152][0]["ns"]
    a5rows = [d for d in lat_rows(f"{R2}latency-ocm-all5-cpu{c}.csv") if d["mode"].startswith("fresh")]
    print(f"cpu{c}: " + " ".join(f"{hop[(c,r)]:6.2f}" for r in range(5)) + f"  all5 {a5['ns']:6.2f} (L3 {min(d['l3'] for d in a5rows):.3f}-{max(d['l3'] for d in a5rows):.3f})  slc2M {slc:6.2f}")

print("=" * 70); print("C. 8 MiB flushed vs 32 MiB fresh, and the DRAM sweep")
fl = [d for d in lat_rows(R2 + "latency-dram-flushed.csv") if d["mode"] == "best"][0]["ns"]
lg = {d["size"]: d["ns"] for d in lat_rows(R2 + "latency-dram-large.csv") if d["mode"] == "best"}
print(f"8M flushed {fl:.3f}  32M fresh {lg.get(33554432)}  16M fresh {lg.get(16777216)}  8M fresh {lg.get(8388608)}")

print("=" * 70); print("D. cmn-counts.csv: structure, success criteria, node attribution")
rows = collections.defaultdict(list); comments = []
for line in open(R2 + "cmn-counts.csv"):
    line = line.rstrip("\n")
    if line.startswith("#"): comments.append(line); continue
    if line.startswith("label,"): continue
    f = line.split(",")
    rows[f[0]].append(dict(event=f[1], node=f[2], count=int(f[3]), en=int(f[4]), run=int(f[5])))
print("comment lines:", comments)
labels = list(rows)
print("labels:", len(labels))
bad = 0
for lb in labels:
    ev = [r for r in rows[lb] if r["event"] not in ("child_elapsed_ns", "helper_elapsed_ns")]
    t = {r["event"]: r for r in rows[lb] if r["event"] in ("child_elapsed_ns", "helper_elapsed_ns")}
    if lb == "control-nocount-cpu2":
        assert not ev and len(t) == 2; continue
    if len(ev) != 7 or len(t) != 2: print("STRUCTURE", lb, len(ev), len(t)); bad += 1
    for r in ev:
        if r["run"] <= 0 or r["run"] < 0.95 * r["en"]: print("RUNNING", lb, r); bad += 1
print("structure/running problems:", bad)
ctl = {}
for c in (2, 4, 6, 8):
    ctl[c] = {r["node"]: r["count"] for r in rows[f"control-cpu{c}"] if r["event"] == "hns_pocq_reqs_recvd_all"}
    print(f"control cpu{c}:", ctl[c])
nodes = ["88", "160", "216", "288", "344"]
print("per-region rows: own node vs others (criterion: own > each other + that node's control count)")
fails = 0
for c in (2, 4, 6, 8):
    for r in range(5):
        lb = f"ocm-region{r}-cpu{c}"
        cnt = {x["node"]: x["count"] for x in rows[lb] if x["event"] == "hns_pocq_reqs_recvd_all"}
        own = nodes[r]
        ok = all(cnt[own] > cnt[o] + ctl[c][o] for o in nodes if o != own)
        others = [cnt[o] for o in nodes if o != own]
        if not ok: fails += 1
        print(f"{lb:20s} own {own:>3s}={cnt[own]:7d} others {min(others)}-{max(others)}  ok={ok}")
print("attribution failures:", fails)
print("other counted rows (pocq per node, mc_local, cache_miss):")
for lb in labels:
    if lb.startswith("ocm-region") or lb.startswith("control"): continue
    cnt = {x["node"]: x["count"] for x in rows[lb] if x["event"] == "hns_pocq_reqs_recvd_all"}
    mc = [x["count"] for x in rows[lb] if x["event"] == "hns_mc_reqs_local_all"][0]
    cm = [x["count"] for x in rows[lb] if x["event"] == "hns_cache_miss_all"][0]
    print(f"{lb:20s} " + " ".join(f"{cnt[n]:8d}" for n in nodes) + f"  mc {mc:8d} miss {cm:8d}")

print("=" * 70); print("E. timing rows")
tot_helper = 0; tot_child = 0
for lb in labels:
    t = {r["event"]: r["count"] for r in rows[lb] if r["event"] in ("child_elapsed_ns", "helper_elapsed_ns")}
    tot_helper += t["helper_elapsed_ns"]; tot_child += t["child_elapsed_ns"]
    print(f"{lb:22s} child {t['child_elapsed_ns']/1e6:8.3f} ms  helper {t['helper_elapsed_ns']/1e6:8.3f} ms  own {(t['helper_elapsed_ns']-t['child_elapsed_ns'])/1e6:6.3f} ms")
print(f"sum child {tot_child/1e6:.1f} ms, sum helper {tot_helper/1e6:.1f} ms over {len(labels)} helper runs")
c2 = {r["event"]: r["count"] for r in rows["control-cpu2"] if r["event"].endswith("elapsed_ns")}
n2 = {r["event"]: r["count"] for r in rows["control-nocount-cpu2"] if r["event"].endswith("elapsed_ns")}
print(f"counted control: helper {c2['helper_elapsed_ns']} child {c2['child_elapsed_ns']}; uncounted: helper {n2['helper_elapsed_ns']} child {n2['child_elapsed_ns']}; helper diff {c2['helper_elapsed_ns']-n2['helper_elapsed_ns']} ns, child diff {c2['child_elapsed_ns']-n2['child_elapsed_ns']} ns")

print("=" * 70); print("F. bandwidth best rows, run 2 vs run 1 (same file, kernel, threads, bytes)")
r1bw = {}
for p in sorted(glob.glob(R1 + "bandwidth-*.csv")):
    for d in bw_rows(p):
        if d["rep"] == "best": r1bw[(os.path.basename(p), d["kernel"], d["threads"], d["bpt"], d["mem"])] = d["agg"]
for p in sorted(glob.glob(R2 + "bandwidth-*.csv")):
    name = os.path.basename(p)
    for d in bw_rows(p):
        if d["rep"] != "best": continue
        k = (name, d["kernel"], d["threads"], d["bpt"], d["mem"])
        r1 = r1bw.get(k)
        delta = f"  run1 {r1:8.3f}  {100*(d['agg']-r1)/r1:+6.1f}%" if r1 else ""
        print(f"{name:32s} {d['mem']:4s} {d['kernel']:5s} t{d['threads']} {d['bpt']:>9d} {d['agg']:8.3f} GB/s{delta}")
print("placement rows, per-thread min/max of each rep:")
for p in sorted(glob.glob(R2 + "bandwidth-write-cpus*.csv")):
    for d in bw_rows(p):
        if d["rep"] != "best": print(f"{os.path.basename(p):32s} rep{d['rep']} agg {d['agg']:7.3f} per-thread {d['tmin']}-{d['tmax']}")
