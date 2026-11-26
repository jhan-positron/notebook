import re,datetime as dt
R="/home/jhan/workspace/titan/cache-perf/crb/results"
J=R+"/dimm-check-20261117/h-5.txt"
recs=[]  # (time, line, text)
sev=[]
lines=open(J,errors="replace").read().split("\n")
print("journal lines:",len(lines), "first:",lines[0][:80])
for i,l in enumerate(lines,1):
    if "Hardware error from APEI" in l:
        t=dt.datetime.fromisoformat(l.split(" ")[0]).replace(tzinfo=None)
        recs.append((t,i,l))
    if "event severity" in l:
        t=dt.datetime.fromisoformat(l.split(" ")[0]).replace(tzinfo=None)
        sev.append((t,i,l.split("event severity:")[1].strip()))
print("records total:",len(recs),"severity lines:",len(sev))
from collections import Counter
print(Counter(s[2] for s in sev))
def sev_of(line):
    # the severity line following record line
    for t,i,s in sev:
        if i>line: return (i,s)
def win(day,a,b):
    A=dt.datetime.fromisoformat(day+"T"+a); B=dt.datetime.fromisoformat(day+"T"+b)
    return A,B
def parse_launch(folder,day):
    out={}
    for i,l in enumerate(open(R+"/"+folder+"/launches.txt"),1):
        p=l.split()
        if p[0]=="launch": out.setdefault(p[1],{})["launch"]=(p[3],i)
        if p[0]=="rc": out.setdefault(p[2],{})["rc"]=(p[4],i)
    return out
rows=[("L-1","w120-R8-20261117T020549Z","2026-11-17",["a6456"]),
      ("L-2","w120-R1-20261115T185140Z","2026-11-15",["p1nop","p2add"]),
      ("L-3","w120-R5-20261115T203152Z","2026-11-15",["thp"]),
      ("L-4","w120-R6-20261115T203438Z","2026-11-15",["st1","st2","st3"]),
      ("R0","w120-R0-20261115T165608Z","2026-11-15",["p1","p2"]),
      ("R0b","w120-R0b-20261115T170342Z","2026-11-15",["cA","cB","cC"])]
def intervals(path):
    iv=[]; cur=None
    for i,l in enumerate(open(path),1):
        if l.startswith("I,"):
            p=l.split(","); cur={"round":int(p[1]),"pos":int(p[2]),"k":p[3],"iline":i,"ts":[],"te":[],"tl":[],"sum":0.0}; iv.append(cur)
        elif l.startswith("T,"):
            p=l.rstrip().split(",")
            cur["ts"].append(float(p[9])); cur["te"].append(float(p[10])); cur["tl"].append(i); cur["sum"]+=float(p[6])/float(p[7])/1e9
    return iv
tot=0
for row,folder,day,procs in rows:
    L=parse_launch(folder,day)
    for pr in procs:
        A,B=win(day,L[pr]["launch"][0],L[pr]["rc"][0])
        hits=[(t,i) for t,i,l in recs if A<=t<=B]
        tot+=len(hits)
        iv=intervals(R+"/"+folder+"/"+pr+".csv")
        print(row,pr,"launch",A,"rc",B,"records",len(hits))
        for t,i in hits:
            d=(t-A).total_seconds()
            s=sev_of(i)
            # which intervals contain d (with +-1 s)
            inside=[(x["k"],x["round"],x["pos"],x["iline"],round(min(x["ts"]),2),round(max(x["te"]),2),round(x["sum"],2),x["tl"][0],x["tl"][-1]) for x in iv if min(x["ts"])-1<=d<=max(x["te"])+1]
            print("    rec line",i,"time",t,"dt",d,"sev",s,"| intervals within +-1s:",inside)
        used=[(x["k"],x["round"],x["pos"],x["iline"],round(min(x["ts"]),2),round(max(x["te"]),2),round(x["sum"],2)) for x in iv if (x["k"]=="oldread" and x["pos"]==0) or (x["k"]=="asmread" and x["pos"]==1)]
        print("    used intervals:",used)
print("total records in windows:",tot)
# no record between 2026-11-15T20:30 and 20:59?
print([ (str(t),i) for t,i,l in recs if dt.datetime(2026,11,15,20,30)<=t<=dt.datetime(2026,11,15,21,0)])
