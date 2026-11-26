import re,statistics,glob,os,hashlib
R="/home/jhan/workspace/titan/cache-perf/crb/results"
def parse(path):
    procs=[]; cur=None
    for i,l in enumerate(open(path),1):
        l=l.rstrip("\n")
        if l.startswith("-- "):
            cur={"hdr":l,"line":i,"iv":[],"hash":None}; procs.append(cur)
        elif l.startswith("#"):
            if cur is not None: cur["hash"]=l
        elif cur is not None:
            p=l.split(",")
            if len(p)>6 and p[3] in ("0","1","2"):
                cur["iv"].append((float(p[6]),i,int(p[4])//int(p[2])//int(p[1]) if False else int(p[4])//int(p[2])))
    return procs
def hd(h):
    m=re.match(r"-- binary (\S+) kernel (\S+) threads (\S+) cpus (\S+) bytes (\S+) round (\S+) load (\S+) utc (\S+)",h)
    return m.groups()
files={"A-1":R+"/kernels-20261113T181222Z/threads120.csv"}
for g in sorted(glob.glob(R+"/k120-T72A*")):
    files[os.path.basename(g).split("-")[1]]=g+"/threads120.csv"
P={}
for k,f in files.items():
    P[k]=parse(f)
    print(k,f,len(P[k]),"procs")
# check 27
ref=[hd(p["hdr"])[:6] for p in P["A-1"]]
tot=0;eq=0
for k in ("T72A1","T72A2","T72A3"):
    for a,b in zip(ref,[hd(p["hdr"])[:6] for p in P[k]]):
        tot+=1; eq+=(a==b)
print("header lines equal in binary,kernel,threads,cpus,bytes,round:",eq,"of",tot)
print("distinct (threads,cpus,bytes):",set(hd(p["hdr"])[2:5] for k in P for p in P[k]))
ends=set(); n=0
for k in P:
    for p in P[k]:
        n+=1; ends.add(p["hash"].split("; ")[-1])
print("hash line endings over",n,"processes:",ends)
# ra.sh vs run_kernels.sh
S="/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
ra=open(S+"/ra.sh").read().split("\n"); rk=open("/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh").read().split("\n")
print("ra.sh 39-43:"); print("\n".join(ra[38:43])); print("run_kernels 60-64:"); print("\n".join(rk[59:64]))
print("equal:", ra[38:43]==rk[59:64])
print("sha256 run_kernels.sh:", hashlib.sha256(open("/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh","rb").read()).hexdigest())
pl=open(R+"/kernels-20261113T181222Z/probe.txt").read().split("\n")
print("probe.txt line 18:", pl[17])
# PA-2/PA-3
def get(k,binary,kern,rnd):
    for p in P[k]:
        h=hd(p["hdr"])
        if h[0]==binary and h[1]==kern and h[5]==str(rnd): return p
allold=[]
for s,k in enumerate(("T72A1","T72A2","T72A3"),1):
    for r in (1,2):
        o=get(k,"bw_old","read",r); nw=get(k,"bw_new","read",r)
        ov=[x[0] for x in o["iv"]]; nv=[x[0] for x in nw["iv"]]
        allold+=ov
        mo=statistics.median(ov); mn=statistics.median(nv)
        print("session",s,"round",r,"old",ov,"lines",[x[1] for x in o["iv"]],"new",nv,"lines",[x[1] for x in nw["iv"]],
              "ratio med %.3f below %.1f%%"%(mn/mo,(1-mn/mo)*100),"lo %.3f hi %.3f"%(min(nv)/max(ov),max(nv)/min(ov)),
              "same-number", ["%.3f"%(a/b) for a,b in zip(nv,ov)], "hdr utc old",hd(o["hdr"])[7],"new",hd(nw["hdr"])[7])
        ao=get(k,"bw_old","asmread",r); an=get(k,"bw_new","asmread",r)
        print("    asm ratios: %.3f %.3f"%(statistics.median([x[0] for x in ao["iv"]])/mo, statistics.median([x[0] for x in an["iv"]])/mo))
print("7200 old read: min %.2f max %.2f width %.2f n %d"%(min(allold),max(allold),max(allold)-min(allold),len(allold)))
lo,hi=463.58,469.03
print("below:",[v for v in allold if v<lo],"above:",[v for v in allold if v>hi], "width8000 %.2f pct %.3f"%(hi-lo,(hi-lo)/lo*100))
# PA-4 medians
a1=[x[0] for r in (1,2) for x in get("A-1","bw_new","read",r)["iv"]]
print("A-1 bw_new read 6 iv:",a1,"median",statistics.median(a1))
s1=[x[0] for r in (1,2) for x in get("T72A1","bw_new","read",r)["iv"]]
print("session1 bw_new read 6 iv:",s1,"median",statistics.median(s1))
