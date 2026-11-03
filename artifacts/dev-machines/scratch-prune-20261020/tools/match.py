# Build the notebook<->scratch mapping and classify every scratch file.
import sys, os, re, json, collections
SP=sys.argv[1]; GiB=1024**3
scratch={}  # rel -> (size,date)
for l in open(f"{SP}/3bda-scratch-files.tsv", encoding="utf-8", errors="replace"):
    p=l.rstrip("\n").split("\t",2)
    if len(p)==3: scratch[p[2][len("/scratch/jhan/"):]]=(int(p[0]),p[1])
repo={}  # repo path -> size
for l in open(f"{SP}/repo-files.tsv", encoding="utf-8", errors="replace"):
    s,p=l.rstrip("\n").split("\t",1); repo[p]=int(s)
mapped={}  # scratch rel -> set(repo paths) via explicit records
how=collections.Counter()
def add(rel, rp, src):
    rel=rel.strip("/"); 
    if rel in scratch and rp in repo:
        mapped.setdefault(rel,set()).add(rp); how[src]+=1
# 1. path-mapped mirror: artifacts/tron-perf-fluctuation/{3bda-scratch,alpha-scratch}/<rel>
for rp in repo:
    m=re.match(r"artifacts/tron-perf-fluctuation/(?:3bda|alpha)-scratch/(.+)$", rp)
    if m: add(m.group(1), rp, "scratch-mirror-path")
# 2. README "- `repo` — canonical `host:/scratch/jhan/rel`" lines (tron-perf-fluctuation README) and
#    "Canonical: delphi-3bda:/scratch/jhan/rel" lines that follow a "## name" or "- `name`" (delphi-flat-freq README)
def scan_readme(path, topdir):
    cur=None
    for line in open(path, encoding="utf-8", errors="replace"):
        m=re.match(r"^- `([^`]+)` — canonical `[a-z0-9-]+:/scratch/jhan/([^`]+)`", line)
        if m: add(m.group(2), f"{topdir}/{m.group(1)}", f"readme:{os.path.basename(topdir)}"); continue
        m=re.match(r"^## (\S+)", line)
        if m: cur=m.group(1)
        m=re.match(r"^- `([^`]+)`\s*$", line)
        if m: cur=m.group(1)
        for c in re.findall(r"(?:Canonical|canonical|Canonicals|mirror):?\s*[a-z0-9-]+:/scratch/jhan/([A-Za-z0-9_./-]+)", line):
            if cur:
                cands=[f"{topdir}/{cur}", f"{topdir}/test-scripts/{cur}", f"{topdir}/docs/{cur}", f"{topdir}/{os.path.basename(c)}", f"{topdir}/test-scripts/{os.path.basename(c)}", f"{topdir}/docs/{os.path.basename(c)}"]
                for rp in cands:
                    if rp in repo: add(c, rp, f"readme:{os.path.basename(topdir)}"); break
scan_readme("artifacts/tron-perf-fluctuation/README.md","artifacts/tron-perf-fluctuation")
scan_readme("artifacts/delphi-flat-freq/README.md","artifacts/delphi-flat-freq")
# 3. lineage tables: | ... | `host:/scratch/jhan/rel` | `repo path`; ... |
for root,_,files in os.walk("artifacts"):
    for f in files:
        if f.endswith(".lineage.md"):
            for line in open(os.path.join(root,f), encoding="utf-8", errors="replace"):
                m=re.search(r"`[a-z0-9-]+:/scratch/jhan/([^`]+)`\s*\|\s*`(artifacts/[^`]+)`", line)
                if m: add(m.group(1), m.group(2), "lineage")
# 4. codex sidecar json: look for any dict with a /scratch/jhan source and a repo path
def walk(o, bag):
    if isinstance(o,dict):
        vals=[v for v in o.values() if isinstance(v,str)]
        src=[v for v in vals if "/scratch/jhan/" in v]
        dst=[v for v in vals if v.startswith("artifacts/") or v.startswith("handoffs/")]
        if src and dst: bag.append((src,dst))
        for v in o.values(): walk(v,bag)
    elif isinstance(o,list):
        for v in o: walk(v,bag)
for f in sorted(os.listdir("logs")):
    if f.endswith(".json"):
        bag=[]; walk(json.load(open(os.path.join("logs",f))), bag)
        for src,dst in bag:
            for s in src:
                m=re.search(r"/scratch/jhan/([A-Za-z0-9_./@+=-]+)", s)
                if not m: continue
                for d in dst:
                    d=d.split("`")[0].strip()
                    add(m.group(1), d, "codex-json")
# 5. basename+size fallback (not an explicit record): report separately
by_bs=collections.defaultdict(list)
for rp,s in repo.items(): by_bs[(os.path.basename(rp),s)].append(rp)
fallback={}
for rel,(s,d) in scratch.items():
    if rel in mapped or rel.endswith(".pftrace"): continue
    k=(os.path.basename(rel),s)
    if k in by_bs and s>=64: fallback[rel]=by_bs[k]
# size agreement for mapped
same=diff=0; diffs=[]
for rel,rps in mapped.items():
    if any(repo[rp]==scratch[rel][0] for rp in rps): same+=1
    else: diff+=1; diffs.append((rel, scratch[rel][0], [ (rp,repo[rp]) for rp in rps]))
print("explicit mapping sources:", dict(how))
print(f"scratch files with an explicit notebook mirror: {len(mapped)} (size identical: {same}, size differs: {diff})")
print(f"scratch files matched only by basename+size (no explicit record): {len(fallback)}")
json.dump({"mapped":{k:sorted(v) for k,v in mapped.items()}, "fallback":fallback, "diffs":diffs}, open(f"{SP}/mapping.json","w"), indent=0)
# per top dir summary
top=collections.defaultdict(lambda: dict(n=0,b=0,pf_n=0,pf_b=0,m_n=0,m_b=0,f_n=0,f_b=0))
for rel,(s,d) in scratch.items():
    t=rel.split("/",1)[0] if "/" in rel else "(top-level files)"; v=top[t]; v["n"]+=1; v["b"]+=s
    if rel.endswith(".pftrace"): v["pf_n"]+=1; v["pf_b"]+=s
    elif rel in mapped: v["m_n"]+=1; v["m_b"]+=s
    elif rel in fallback: v["f_n"]+=1; v["f_b"]+=s
print("\ntop dir | files | mirrored(explicit) | basename+size only | other non-trace files not in notebook")
for t,v in sorted(top.items(), key=lambda kv:-kv[1]["b"]):
    other_n=v["n"]-v["pf_n"]-v["m_n"]-v["f_n"]; other_b=v["b"]-v["pf_b"]-v["m_b"]-v["f_b"]
    if v["m_n"] or v["f_n"] or v["b"]>GiB/10:
        print(f"{t:58s} {v['n']:7d} | mirrored {v['m_n']:5d} ({v['m_b']/1048576:8.1f} MiB) | bs-only {v['f_n']:6d} ({v['f_b']/1048576:8.1f} MiB) | not-in-notebook {other_n:7d} files {other_b/GiB:7.2f} GiB")
print("\nsize-differs samples:")
for d in diffs[:15]: print("  ",d)
