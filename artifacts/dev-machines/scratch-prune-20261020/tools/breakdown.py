import sys, os, collections
tsv = sys.argv[1]
GiB = 1024**3
by_ext = collections.defaultdict(lambda: [0,0])
by_top = collections.defaultdict(lambda: {"n":0,"b":0,"pf_n":0,"pf_b":0,"newest":""})
tot_n = tot_b = pf_n = pf_b = 0
for line in open(tsv, encoding="utf-8", errors="replace"):
    parts = line.rstrip("\n").split("\t", 2)
    if len(parts) != 3: continue
    size, date, path = int(parts[0]), parts[1], parts[2]
    rel = path[len("/scratch/jhan/"):]
    top = rel.split("/",1)[0] if "/" in rel else "(top-level files)"
    base = os.path.basename(path)
    ext = base.rsplit(".",1)[1].lower() if "." in base[1:] else "(none)"
    if len(ext) > 10 or any(c.isspace() for c in ext): ext = "(none)"
    is_pf = ext == "pftrace"
    by_ext[ext][0] += 1; by_ext[ext][1] += size
    t = by_top[top]; t["n"] += 1; t["b"] += size
    if date > t["newest"]: t["newest"] = date
    if is_pf: t["pf_n"] += 1; t["pf_b"] += size; pf_n += 1; pf_b += size
    tot_n += 1; tot_b += size
print(f"TOTAL files={tot_n} bytes={tot_b/GiB:.1f} GiB ; pftrace files={pf_n} {pf_b/GiB:.1f} GiB ; other={tot_n-pf_n} files {(tot_b-pf_b)/GiB:.1f} GiB")
print("\n== by extension (top 30 by bytes) ==")
for ext,(n,b) in sorted(by_ext.items(), key=lambda kv:-kv[1][1])[:30]:
    print(f"{b/GiB:9.2f} GiB {n:8d}  .{ext}")
print("\n== by top dir (sorted by bytes) : total | pftrace | other | files | newest mtime ==")
for top,t in sorted(by_top.items(), key=lambda kv:-kv[1]["b"]):
    print(f"{t['b']/GiB:8.2f} GiB | pf {t['pf_b']/GiB:7.2f} GiB ({t['pf_n']:4d}) | other {(t['b']-t['pf_b'])/GiB:7.2f} GiB ({t['n']-t['pf_n']:7d} files) | newest {t['newest']} | {top}")
