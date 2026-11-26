import re,glob,os,statistics,json,pickle
R="/home/jhan/workspace/titan/cache-perf/crb/results"
def parse(path):
    """returns list of processes; each: hdr (or None), hdr_line, intervals[]"""
    procs=[]; cur=None; iv=None
    for i,l in enumerate(open(path),1):
        if l.startswith("-- "):
            cur={"hdr":l.rstrip(),"line":i,"iv":[]}; procs.append(cur)
        elif l.startswith("I,"):
            if cur is None:
                cur={"hdr":None,"line":0,"iv":[]}; procs.append(cur)
            p=l.rstrip().split(",")
            iv={"round":int(p[1]),"pos":int(p[2]),"k":p[3],"iline":i,"agg":float(p[8]),"m0":0.0,"m1":0.0,"n":0,"ts":1e9,"te":0}
            cur["iv"].append(iv)
        elif l.startswith("T,"):
            p=l.rstrip().split(",")
            cpu=int(p[5]); r=float(p[6])/float(p[7])/1e9
            if cpu<=63: iv["m0"]+=r
            else: iv["m1"]+=r
            iv["n"]+=1; iv["ts"]=min(iv["ts"],float(p[9])); iv["te"]=max(iv["te"],float(p[10]))
    for pr in procs:
        for x in pr["iv"]:
            x["sum"]=x["m0"]+x["m1"]
            # kernel before
        for a,b in zip([None]+pr["iv"][:-1],pr["iv"]):
            b["before"]=a["k"] if a else None
    return procs
def one(folder,name):
    return parse(R+"/"+folder+"/"+name+".csv")[0]
D={}
def add(row,folder,names):
    for n in names:
        p=one(folder,n); assert all(x["n"]==120 for x in p["iv"]),(folder,n)
        D.setdefault(row,[]).append((folder,n,p))
add("L",*("w120-T72L1-20261117T221329Z",["a6456"])); add("L","w120-T72L2-20261117T221638Z",["a6456"]); add("L","w120-T72L3-20261117T221947Z",["a6456"])
add("C","w120-T72C1-20261117T221436Z",["cfwd"]); add("C","w120-T72C2-20261117T221745Z",["crev"]); add("C","w120-T72C3-20261117T222054Z",["cfwd"]); add("C","w120-T72C4-20261117T222136Z",["crev"])
add("I","w120-T72I1-20261117T222700Z",["a6456"]); add("I","w120-T72I2-20261117T223227Z",["a6456"])
add("F","w120-w120-F72d12-20261117T200231Z",["a6456"])
add("L-1","w120-R8-20261117T020549Z",["a6456"]); add("L-2","w120-R1-20261115T185140Z",["p1nop","p2add"]); add("L-3","w120-R5-20261115T203152Z",["thp"]); add("L-4","w120-R6-20261115T203438Z",["st1","st2","st3"])
add("R0","w120-R0-20261115T165608Z",["p1","p2"]); add("R0b","w120-R0b-20261115T170342Z",["cA","cB","cC"])
pickle.dump(D,open(os.path.dirname(os.path.abspath(__file__))+"/bwx.pkl","wb"))
f2=lambda v:"%.2f"%(int(v*100+0.5)/100)
print("=== part C table: m0 + m1")
for folder,n,p in D["C"]:
    tag=folder.split("-")[1]
    for rnd in (0,1):
        cells=[]
        for k in ("oldread","read","asmread"):
            x=[y for y in p["iv"] if y["round"]==rnd and y["k"]==k][0]
            cells.append("%s %s (pos %d, after %s, I line %d) %s + %s"%(k,f2(x["sum"]),x["pos"],x["before"],x["iline"],f2(x["m0"]),f2(x["m1"])))
        print(tag,n,rnd," | ".join(cells))
def used(rows,k,pos=None,cond=None):
    out=[]
    for r in rows:
        for folder,n,p in D[r]:
            for x in p["iv"]:
                if x["k"]==k and (pos is None or x["pos"]==pos) and (cond is None or cond(r,folder,n,x)):
                    out.append((r,folder.split("-")[1],n,x))
    return out
def rng(lst,key):
    v=[x[3][key] for x in lst]; return "%s to %s (n=%d)"%(f2(min(v)),f2(max(v)),len(v)), min(v), max(v)
print("=== mesh sums oldread")
for name,rows,pos in (("part L",["L"],0),("part C",["C"],None),("control I",["I"],0),("F72d12",["F"],0),("pool L-1..L-4",["L-1","L-2","L-3","L-4"],0),("R0,R0b",["R0","R0b"],0),("7200 all",["L","C","I","F"],None),("7200 no C",["L","I","F"],0),("8000 bwx12+bwx11",["L-1","L-2","L-3","L-4","R0","R0b"],0)):
    u=used(rows,"oldread",pos if name!="part C" and name!="7200 all" else None)
    if name=="7200 all": u=used(["L","I","F"],"oldread",0)+used(["C"],"oldread")
    print(name,"sum",rng(u,"sum")[0],"m0",rng(u,"m0")[0],"m1",rng(u,"m1")[0])
u=used(["L","I","F"],"oldread",0); m0max=max(x[3]["m0"] for x in u)
print("7200 no C mesh0 max unrounded",m0max)
print("=== asmread pool")
u=used(["L-1","L-2","L-3","L-4"],"asmread",1)
for r,t,n,x in u: print("  ",r,t,n,"round",x["round"],"I line",x["iline"],f2(x["sum"]),x["sum"])
v=sorted(x[3]["sum"] for x in u)
print("pool:",f2(v[0]),f2(v[-1]),"n",len(v)); 
w=v[1:]; print("without lowest:",f2(w[0]),f2(w[-1]),"width",f2(w[-1]-w[0]),"pct %.2f"%((w[-1]-w[0])/w[0]*100),"n",len(w))
pc=[x for x in used(["C"],"asmread") if x[3]["before"]=="oldread"]
print("part C asmread after oldread:",[(t,n,x["round"],x["pos"],x["iline"],f2(x["sum"])) for r,t,n,x in pc]," distance to pool max:",f2(min(x[3]["sum"] for x in pc)-v[-1]))
for nm,rows in (("L",["L"]),("I",["I"]),("F",["F"])):
    u2=used(rows,"asmread",1); print(nm,"asmread",rng(u2,"sum")[0], "dist to pool max %s ; to new lower end"%f2(min(x[3]["sum"] for x in u2)-v[-1]))
print("=== bwx11 after 120-thread work, oldread pos 0")
for r in ("R0","R0b"):
    for folder,n,p in D[r]:
        print(r,n,[(x["round"],x["iline"],f2(x["sum"])) for x in p["iv"] if x["k"]=="oldread" and x["pos"]==0])
print("part C oldread:",rng(used(["C"],"oldread"),"sum")[0], "part L oldread:",rng(used(["L"],"oldread",0),"sum")[0])
print("part C cfwd pos0:",rng([x for x in used(["C"],"oldread",0)],"sum")[0])
# runner bwx
print("=== runner bwx common-6000")
allold=[]; loads=[]; nproc=0; m0=[];m1=[]
for f in ("B7-20261113T232859Z/B7.csv","B7-20261114T024352Z/B7.csv","C3-20261114T022708Z/C3.csv","C3-20261114T054116Z/C3.csv"):
    ps=parse(R+"/"+f)
    for i,p in enumerate(ps):
        m=re.search(r"tag (\S+) binary (\S+) .*loadavg (\S+) .* utc (\S+) args (.*)",p["hdr"])
        tag=m.group(1)
        if tag.startswith("common-6000-"):
            nproc+=1; loads.append(float(m.group(3)))
            prev=ps[i-1]["hdr"] if i>0 else None
            pm=re.search(r"tag (\S+) binary (\S+) .* utc (\S+) args --threads (\S+)",prev) if prev else None
            o0=[x for x in p["iv"] if x["k"]=="oldread" and x["pos"]==0]
            o7=[x for x in p["iv"] if x["k"]=="oldread" and x["pos"]==7]
            allold+= [x["sum"] for x in o0]
            m0+=[x["m0"] for x in o0+o7]; m1+=[x["m1"] for x in o0+o7]
            print(f.split("/")[0],tag,"load",m.group(3),"utc",m.group(4),"prev:",(pm.group(1),pm.group(2),pm.group(3),"threads",pm.group(4)) if pm else None,"pos0:",[f2(x["sum"]) for x in o0])
print("runner bwx pos 0: n",len(allold),"procs",nproc,f2(min(allold)),"to",f2(max(allold)),"load",min(loads),"to",max(loads))
print("runner bwx pos 0+7 mesh0",f2(min(m0)),f2(max(m0)),"mesh1",f2(min(m1)),f2(max(m1)),"n",len(m0), "min m0 unrounded",min(m0))
print("gap: runner m0 min - 7200noC m0 max = %.4f"%(min(m0)-m0max))
