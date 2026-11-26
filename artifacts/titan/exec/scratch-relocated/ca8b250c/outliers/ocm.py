import re, glob, os, sys
def lat_rows(path):
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
        d = dict(mem=f[0], size=int(f[1]), mode=f[2], rep=f[3], loads=f[4], ns=float(f[5]), meta=meta, lines=int((size or {}).get("lines",0)))
        ncol = header.count(",") + 1 if header else 6
        base = 7 if "ns_per_load_span" in header else 6
        if f[3] != "-":
            num = lambda v: None if v == "-" else float(v)
            if ncol > base:
                has_cov = "perf_cov" in header; ctr = f[base+1:-1] if has_cov else f[base+1:]
                d.update(cyc=num(f[base]), **{f"c{i+1}": num(v) for i, v in enumerate(ctr)})
        out.append(d)
    return out
base="/home/jhan/workspace/titan/cache-perf/asimov/results"
dist={2:{0:1,1:1,2:1,3:3,4:3},4:{0:3,1:3,2:1,3:3,4:3},6:{0:3,1:3,2:1,3:1,4:1},8:{0:5,1:5,2:3,3:3,4:1}}
for run,sub in [("002","19700101T000000Z"),("004","19700101T000000Z"),("011","bootF1")]:
    print("=== run", run)
    bydist={}
    for f in sorted(glob.glob(f"{base}/membench-jibin-{run}/results/{sub}/latency-ocm-*.csv")):
        rows=lat_rows(f); meas=[r for r in rows if r["rep"]!="-"]; best=[r for r in rows if r["rep"]=="-"]
        mn=min(meas,key=lambda r:r["ns"])
        print(os.path.basename(f), "meta:", {k:rows[0]["meta"].get(k) for k in ("cpu","reps","fresh","flush","sparse","stride","loads")}, "size", mn["size"], "lines", mn["lines"], "n_meas", len(meas), "best_row", [b["ns"] for b in best], "min_meas", mn["ns"], "mode", mn["mode"], "c1..c3", mn.get("c1"), mn.get("c2"), mn.get("c3"), "all ns:", [r["ns"] for r in meas])
        m=re.search(r"region(\d)-cpu(\d)", f)
        if m and "dense" not in f:
            d=dist[int(m.group(2))][int(m.group(1))]; bydist.setdefault(d,[]).append(min(b["ns"] for b in best) if best else mn["ns"])
    for d in sorted(bydist):
        v=bydist[d]; print(f"dist {d}: n={len(v)} mean={sum(v)/len(v):.2f} min={min(v)} max={max(v)}")
