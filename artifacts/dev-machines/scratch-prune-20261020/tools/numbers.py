# Classify every file on /scratch/jhan and total on-disk bytes per top-level entry and class.
import sys, os, re, json, collections
SP=sys.argv[1]; OUT=sys.argv[2]
KiB=1024; GiB=1024**3; MiB=1024**2
scratch={}   # rel -> [apparent, date, ondisk]
for l in open(f"{SP}/3bda-scratch-files.tsv", encoding="utf-8", errors="replace"):
    p=l.rstrip("\n").split("\t",2)
    if len(p)==3: scratch[p[2][len("/scratch/jhan/"):]]=[int(p[0]),p[1],None]
for l in open(f"{SP}/3bda-ondisk.tsv", encoding="utf-8", errors="replace"):
    p=l.rstrip("\n").split("\t",1)
    if len(p)==2:
        rel=p[1][len("/scratch/jhan/"):]
        if rel in scratch: scratch[rel][2]=int(p[0])*KiB
        else: scratch[rel]=[None,"",int(p[0])*KiB]
missing=[r for r,v in scratch.items() if v[2] is None]
print("files without on-disk size:", len(missing))
# archived-by-content set
repo_md5=collections.defaultdict(list)
for l in open(f"{SP}/repo-md5.txt", encoding="utf-8", errors="replace"):
    h,p=l.rstrip("\n").split("  ",1); repo_md5[h].append(p)
archived={}
for f in ["remote-md5.clean.txt","doccheck-md5.txt","fullcheck-md5.txt"]:
    try:
        for l in open(f"{SP}/{f}"):
            h,p=l.rstrip("\n").split("  ",1)
            if h in repo_md5: archived[p]=repo_md5[h][0]
    except FileNotFoundError: pass
checked=set()
for f in ["remote-md5.clean.txt","doccheck-md5.txt","fullcheck-md5.txt"]:
    try:
        for l in open(f"{SP}/{f}"): checked.add(l.rstrip("\n").split("  ",1)[1])
    except FileNotFoundError: pass
REGEN=re.compile(r"^(pr3244|workspace/story2814/compare_perf/runs/[^/]+/worktrees|tron-pr3070|pdjn-wt|tron-src|systest-b2|frozen|symbols|tron-perfetto-install-20260809|tron-perfetto-vanilla-install-20260806)/|^(pdjn/install-|pdjn/runtron-|perf-fluctuation/deep-dive/install-)|/(\.venv|venv|\.rustup|\.cargo|site-packages|node_modules)/|^\.venv-pdfconv/")
PERSONAL=re.compile(r"^(laptop-bkup|claude-dev-migrate|codex-home-andoria-11|tmp)/")
def cls(rel):
    if rel.endswith(".pftrace"): return "pftrace"
    if PERSONAL.search(rel): return "personal"
    if REGEN.search(rel): return "regen"
    return "raw"
CLS=["pftrace","regen","raw","personal"]
top=collections.defaultdict(lambda: {"ondisk":0,"apparent":0,"files":0,"newest":"","by":{c:0 for c in CLS},"byn":{c:0 for c in CLS},"archived_n":0,"archived_b":0,"checked_n":0})
tot={"ondisk":0,"apparent":0,"files":0,"by":{c:0 for c in CLS},"byn":{c:0 for c in CLS},"archived_n":0,"archived_b":0,"checked_n":0}
for rel,(ap,dt,od) in scratch.items():
    t=rel.split("/",1)[0] if "/" in rel else "(top-level files)"
    c=cls(rel); od=od or 0; ap=ap or 0
    v=top[t]; v["ondisk"]+=od; v["apparent"]+=ap; v["files"]+=1; v["by"][c]+=od; v["byn"][c]+=1
    if dt>v["newest"]: v["newest"]=dt
    tot["ondisk"]+=od; tot["apparent"]+=ap; tot["files"]+=1; tot["by"][c]+=od; tot["byn"][c]+=1
    if rel in archived: v["archived_n"]+=1; v["archived_b"]+=ap; tot["archived_n"]+=1; tot["archived_b"]+=ap
    if rel in checked: v["checked_n"]+=1; tot["checked_n"]+=1
# du cross-check
du={}
for l in open(f"{SP}/du-top.tsv"):
    k,p=l.rstrip("\n").split("\t",1); du[p]=int(k)*KiB
for t,v in top.items():
    v["du"]=du.get(t)
print(f"TOTAL on-disk {tot['ondisk']/GiB:.1f} GiB (du sum {sum(du.values())/GiB:.1f}), apparent {tot['apparent']/GiB:.1f} GiB, files {tot['files']}")
for c in CLS: print(f"  {c:9s} {tot['by'][c]/GiB:7.1f} GiB  {tot['byn'][c]:7d} files")
print(f"  archived (content-identical copy in notebook): {tot['archived_n']} files, {tot['archived_b']/MiB:.1f} MiB apparent; files hash-checked: {tot['checked_n']}")
rows=sorted(top.items(), key=lambda kv:-kv[1]["ondisk"])
print("\nentry | on-disk | du | pftrace | regen | raw | personal | archived files | newest")
for t,v in rows[:40]:
    print(f"{t:50s} {v['ondisk']/GiB:7.2f} {((v['du'] or 0)/GiB):7.2f} | {v['by']['pftrace']/GiB:6.2f} {v['by']['regen']/GiB:6.2f} {v['by']['raw']/GiB:6.2f} {v['by']['personal']/GiB:6.2f} | {v['archived_n']:4d}/{v['checked_n']:<5d} | {v['newest']}")
# archived files by entry (list) for the page
arch_by=collections.defaultdict(list)
for p,rp in archived.items(): arch_by[p.split("/",1)[0] if "/" in p else "(top-level files)"].append([p,rp])
json.dump({"total":tot,"entries":{t:v for t,v in top.items()},"archived":arch_by,"classes":CLS}, open(OUT,"w"))
print("wrote", OUT)
