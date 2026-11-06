"""verify.py - check Jesse's round-four claims (boots C, D, E) against the CSV files."""
import csv, glob, os, sys, statistics
R = "/home/jhan/workspace/titan/cache-perf/asimov/results"
BOOTS = {"A": "membench-jibin-005/results/bootA", "B": "membench-jibin-006/results/bootB",
         "C": "membench-jibin-007/results/bootC", "D": "membench-jibin-008/results/bootD",
         "E": "membench-jibin-010/results/bootE"}

def rows(boot, name):
    p = os.path.join(R, BOOTS[boot], name)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        lines = [l for l in f if not l.startswith("#")]
    hdr = [l for l in lines if l.startswith("mem,")][0]
    return list(csv.DictReader([hdr] + [l for l in lines if not l.startswith("mem,")]))

def best(boot, name, size=None, mode_not=("best",), key="ns_per_load"):
    rs = [r for r in rows(boot, name) if r["mode"] not in mode_not and (size is None or int(r["size_bytes"]) == size)]
    if not rs:
        return None
    return min(float(r[key]) for r in rs)

def fmt(x, d=3):
    return "-" if x is None else f"{x:.{d}f}"

print("== commit / commands / exit / perf lines / controls")
for b in "ABCDE":
    log = open(os.path.join(R, BOOTS[b], "log.txt")).read().splitlines()
    start = [l for l in log if "start" in l and "out=" in l][0]
    commit = start.split("cache-mem-perf-")[1].split("/")[0]
    done = [l for l in log if "done" in l][-1]
    ncmd = len([l for l in log if l.startswith("+ ")])
    nfiles = len(glob.glob(os.path.join(R, BOOTS[b], "*")))
    perf = sum(1 for f in glob.glob(os.path.join(R, BOOTS[b], "*.csv")) for l in open(f) if l.startswith("# perf:"))
    pw = [l.split(":")[-1].strip() for l in log if "clusterpwrstat" in l]
    ctl = best(b, "latency-dram-small.csv", 4096)
    rt = [float(r["ns_per_load"]) for f in glob.glob(os.path.join(R, BOOTS[b], "cme-*.csv")) for r in rows(b, os.path.basename(f)) if r["mode"] == "cme-roundtrip"]
    print(f"{b}: commit {commit} cmds {ncmd} files {nfiles} perf-lines {perf} pwrstat {pw} 4K {fmt(ctl)} roundtrip {fmt(min(rt))}-{fmt(max(rt))} | {done.split('Z:')[1].strip()}")

print("\n== hit set (latency-dram-small-l3.csv): best ns, l3 hit per load, 0xA0-0xA2 (best rep)")
for sz in (65536, 131072, 196608, 262144, 393216, 524288):
    out = []
    for b in "BCDE":
        rs = [r for r in rows(b, "latency-dram-small-l3.csv") if int(r["size_bytes"]) == sz and r["mode"] != "best"]
        if not rs:
            out.append(f"{b}: -"); continue
        r = min(rs, key=lambda r: float(r["ns_per_load"]))
        d = max(abs(float(x["l3d_access_rd_per_load"]) - float(x["l3d_refill_rd_per_load"]) - float(x["l3d_hit_rd_per_load"])) for x in rs)
        out.append(f"{b}: {float(r['ns_per_load']):.3f} hit {float(r['l3d_hit_rd_per_load']):.4f} l2hit {float(r['l2d_hit_rd_per_load']):.4f} |A0-A2-hit|max {d:.4f}")
    print(f"{sz>>10:4d} KiB  " + "   ".join(out))
print("E/C ratio of best:", ", ".join(f"{sz>>10}K {best('E','latency-dram-small-l3.csv',sz)/best('C','latency-dram-small-l3.csv',sz):.3f}" for sz in (196608, 262144, 393216, 524288)))

print("\n== core chases (latency-dram-small/large/flushed/seq), best ns")
for name, sizes in (("latency-dram-small.csv", None), ("latency-dram-large.csv", None), ("latency-dram-flushed.csv", None), ("latency-dram-seq.csv", None)):
    szs = sorted({int(r["size_bytes"]) for b in "ABCDE" for r in rows(b, name)})
    for sz in szs:
        vals = {b: best(b, name, sz) for b in "ABCDE"}
        line = f"{name:26s} {sz>>10:6d} KiB  " + "  ".join(f"{b} {fmt(vals[b])}" for b in "ABCDE")
        if vals["C"] and vals["E"]:
            line += f"   E/C {vals['E']/vals['C']:.3f}"
        print(line)
print("E's two passes at 2 MiB (large):", [r["ns_per_load"] for r in rows("E", "latency-dram-large.csv") if int(r["size_bytes"]) == 2 << 20])
print("32 MiB best by boot:", {b: best(b, "latency-dram-large.csv", 32 << 20) for b in "ABCDE"})
print("seq 8 MiB prefetch refills per load, C:", [r["l1d_refill_hwprf_per_load"] for r in rows("C", "latency-dram-seq.csv") if r["mode"] != "best"],
      "E:", [r["l1d_refill_hwprf_per_load"] for r in rows("E", "latency-dram-seq.csv") if r["mode"] != "best"])

print("\n== CME chases (cme-latency-dram-small.csv), best ns and L1 refills (best rep)")
for sz in sorted({int(r["size_bytes"]) for r in rows("C", "cme-latency-dram-small.csv")}):
    out = []
    for b in "ACE":
        rs = [r for r in rows(b, "cme-latency-dram-small.csv") if int(r["size_bytes"]) == sz and r["mode"] != "best"]
        if not rs: out.append(f"{b}: -"); continue
        r = min(rs, key=lambda r: float(r["ns_per_load"]))
        out.append(f"{b}: {float(r['ns_per_load']):.3f} in {float(r['cme_l1d_refill_inner_per_load']):.2f} out {float(r['cme_l1d_refill_outer_per_load']):.2f}")
    e, c = best("E", "cme-latency-dram-small.csv", sz), best("C", "cme-latency-dram-small.csv", sz)
    print(f"{sz>>10:5d} KiB  " + "   ".join(out) + (f"   E/C {e/c:.3f}" if e and c else ""))
for name in ("cme-latency-dram-large.csv", "cme-latency-dram-flushed.csv", "cme-latency-dram-seq.csv"):
    for sz in sorted({int(r["size_bytes"]) for r in rows("C", name)}):
        print(f"{name:30s} {sz>>10:6d} KiB  " + "  ".join(f"{b} {fmt(best(b, name, sz))}" for b in "ABCE"))

print("\n== G7 read variants (bandwidth-read-prefetch.csv), best GB/s")
for b in "BCDE":
    rs = rows(b, "bandwidth-read-prefetch.csv")
    keys = sorted({(r["kernel"], int(r["bytes_per_thread"])) for r in rs}, key=lambda k: (k[1], k[0]))
    print(b, "  ".join(f"{k}@{s>>20}M {max(float(r['aggregate_GBps']) for r in rs if r['kernel']==k and int(r['bytes_per_thread'])==s):.3f}" for k, s in keys))

print("\n== G8 (bandwidth-l1-passes / asmpasses), best GB/s and all reps")
for b in "CDE":
    for name in ("bandwidth-l1-passes.csv", "bandwidth-l1-asmpasses.csv"):
        rs = rows(b, name)
        if not rs: print(b, name, "absent"); continue
        for k in ("read", "write"):
            for s in (4096, 8192, 16384, 24576):
                v = sorted(float(r["aggregate_GBps"]) for r in rs if r["kernel"] == k and int(r["bytes_per_thread"]) == s)
                rf = max(float(r["l1d_refill_per_line"]) for r in rs if r["l1d_refill_per_line"] != "-" and r["kernel"] == k and int(r["bytes_per_thread"]) == s)
                print(f"{b} {name[13:-4]:9s} {k:5s} {s>>10:2d}K best {v[-1]:7.3f} reps {' '.join(f'{x:.3f}' for x in v)} max-refill/line {rf:.4f}")

print("\n== walk rows (D, C): dtlb walk per load, block, page")
for b in "CDE":
    for name in ["latency-dram-walk-cpu2.csv"] + [f"latency-ocm-region{i}-walk-cpu2.csv" for i in range(5)]:
        rs = [r for r in rows(b, name) if r["mode"] != "best"]
        if not rs: continue
        print(b, name, " ".join(f"{r['mode']} {float(r['ns_per_load']):.2f}ns walk {float(r['dtlb_walk_per_load']):.4f} blk {float(r['dtlb_walk_block_per_load']):.4f} pg {float(r['dtlb_walk_page_per_load']):.4f}" for r in rs))

print("\n== TLB-set rows CPU 2 (latency-dram-tlb-cpu2.csv and ocm tlb rows): columns")
print(open(os.path.join(R, BOOTS["C"], "latency-dram-tlb-cpu2.csv")).read().splitlines()[0:1])
