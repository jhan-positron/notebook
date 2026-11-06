"""G8 fits per form per boot, and OCM best-ratio comparisons between boots."""
import csv, glob, math, os, sys
sys.path.insert(0, "/home/jhan/workspace/titan/cache-perf/asimov")
import l1_reader as L
R = "/home/jhan/workspace/titan/cache-perf/asimov/results"
BOOTS = {"A": "membench-jibin-005/results/bootA", "B": "membench-jibin-006/results/bootB",
         "C": "membench-jibin-007/results/bootC", "D": "membench-jibin-008/results/bootD",
         "E": "membench-jibin-010/results/bootE"}
print("== G8 fits: t_pass = a + bytes/rate, best rep per size")
for b in "CE":
    for form in ("passes", "asmpasses"):
        rows = L.read_l1(os.path.join(R, BOOTS[b], f"bandwidth-l1-{form}.csv"))
        br = L.best_reps(rows)
        for k in ("read", "write"):
            pts = [(s, br[(k, s)]["t_pass_ns"]) for s in (4096, 8192, 16384, 24576)]
            a, bb, res = L.fit(pts)
            tmin = min(t for _, t in pts)
            print(f"{b} {form:9s} {k:5s} a={a:6.2f} ns ({a*2:5.1f} cycles)  rate={1/bb:6.2f} GB/s ({1/bb/2:5.2f} B/cycle)  max|resid|={res:5.2f} ns ({res/tmin*100:4.1f} % of {tmin:.1f})  t_pass: " + " ".join(f"{t:.1f}" for _, t in pts))
print()

def rows(boot, name):
    p = os.path.join(R, BOOTS[boot], name)
    if not os.path.exists(p): return []
    lines = [l for l in open(p) if not l.startswith("#")]
    hdr = [l for l in lines if l.startswith("mem,")][0]
    return list(csv.DictReader([hdr] + [l for l in lines if not l.startswith("mem,")]))

def ocm_best(boot):
    out = {}
    for p in sorted(glob.glob(os.path.join(R, BOOTS[boot], "latency-ocm-*.csv"))):
        n = os.path.basename(p)
        rs = [r for r in rows(boot, n) if r["mode"] != "best"]
        if rs: out[n] = min(float(r["ns_per_load"]) for r in rs)
    return out

def cmp(x, y):
    bx, by = ocm_best(x), ocm_best(y)
    common = sorted(set(bx) & set(by))
    ratios = [bx[n] / by[n] for n in common]
    faster = sum(1 for r in ratios if r < 1)
    gm = math.exp(sum(math.log(r) for r in ratios) / len(ratios))
    print(f"{x} vs {y}: {len(common)} rows, {faster} faster, ratio {min(ratios):.3f}-{max(ratios):.3f}, geometric mean {gm:.3f}")
    return bx, by, common

print("== core OCM rows, best of each file, ratio of bests")
cmp("D", "B"); cmp("C", "A"); cmp("C", "D"); bx, by, common = cmp("E", "A"); cmp("E", "C")
print("E vs A per file:", " ".join(f"{n[12:-4]}:{bx[n]/by[n]:.2f}" for n in common if "cpu2" in n and "tlb" not in n and "walk" not in n))

print("\n== TLB-set rows CPU 2: l1d_tlb_refill per pass (loads per pass * refill per load), by boot")
for n in ["latency-dram-tlb-cpu2.csv"] + [f"latency-ocm-region{i}-{v}tlb-cpu2.csv" for i in range(5) for v in ("", "dense-", "vary-")]:
    out = []
    for b in "ABCDE":
        rs = [r for r in rows(b, n) if r["mode"] != "best"]
        if not rs: out.append(f"{b}: -"); continue
        v = [float(r["l1d_tlb_refill_per_load"]) * int(r["loads"]) for r in rs]
        out.append(f"{b}: {min(v):.0f}-{max(v):.0f}")
    print(f"{n[8:-4]:28s} " + "  ".join(out))

print("\n== sparse-dense gap, CPU 2, best ns (sparse - dense) per region")
for b in "ABCDE":
    g = []
    for i in range(5):
        s = [float(r["ns_per_load"]) for r in rows(b, f"latency-ocm-region{i}-cpu2.csv") if r["mode"] != "best"]
        d = [float(r["ns_per_load"]) for r in rows(b, f"latency-ocm-region{i}-dense-cpu2.csv") if r["mode"] != "best"]
        if s and d: g.append(min(s) - min(d))
    print(b, " ".join(f"{x:+.2f}" for x in g))
