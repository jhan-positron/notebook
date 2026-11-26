import datetime as dt
R="/home/jhan/workspace/titan/cache-perf/crb/results"
recs=[]
for i,l in enumerate(open(R+"/dimm-check-20261117/h-5.txt",errors="replace"),1):
    if "Hardware error from APEI" in l:
        recs.append((dt.datetime.fromisoformat(l.split(" ")[0]).replace(tzinfo=None),i))
def ivs(path):
    out=[];cur=None
    for i,l in enumerate(open(path),1):
        if l.startswith("I,"):
            p=l.split(","); cur=dict(r=int(p[1]),pos=int(p[2]),k=p[3],line=i,ts=1e9,te=0,s=0.0); out.append(cur)
        elif l.startswith("T,"):
            p=l.rstrip().split(","); cur["ts"]=min(cur["ts"],float(p[9])); cur["te"]=max(cur["te"],float(p[10])); cur["s"]+=float(p[6])/float(p[7])/1e9
    return out
rows=[("L-1","w120-R8-20261117T020549Z","2026-11-17","a6456","02:05:54","02:06:56"),
("L-2","w120-R1-20261115T185140Z","2026-11-15","p1nop","18:51:45","18:53:40"),
("L-2","w120-R1-20261115T185140Z","2026-11-15","p2add","18:53:45","18:55:50"),
("R0","w120-R0-20261115T165608Z","2026-11-15","p1","16:56:08","16:58:36")]
for row,folder,day,pr,a,b in rows:
    A=dt.datetime.fromisoformat(day+"T"+a); B=dt.datetime.fromisoformat(day+"T"+b)
    iv=ivs(R+"/"+folder+"/"+pr+".csv")
    hit={}
    for t,i in recs:
        if A<=t<=B:
            d=(t-A).total_seconds()
            for x in iv:
                if x["ts"]<=d-1 and d+1<=x["te"]: hit.setdefault((x["r"],x["pos"]),[]).append((i,d,"inside"))
                elif x["ts"]<=d+1 and d-1<=x["te"]: hit.setdefault((x["r"],x["pos"]),[]).append((i,d,"possible"))
    print("==",row,pr)
    for (r,pos),h in sorted(hit.items()):
        x=[y for y in iv if y["r"]==r and y["pos"]==pos][0]
        sib=[y for y in iv if y["pos"]==pos and y["r"]!=r]
        sibhit=[(y["r"],y["pos"]) in hit for y in sib]
        print("  round",r,"pos",pos,x["k"],"%.2f GB/s"%x["s"],"t %.2f-%.2f"%(x["ts"],x["te"]),"records",[(a_,b_,c_) for a_,b_,c_ in h],"| other round same position:",[("%.2f"%y["s"],"has records" if (y["r"],y["pos"]) in hit else "no records") for y in sib])
