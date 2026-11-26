import pickle,os
D=pickle.load(open(os.path.dirname(os.path.abspath(__file__))+"/bwx.pkl","rb"))
f2=lambda v:"%.2f"%(int(v*100+0.5)/100)
def sel(rows,cond):
    return [x for r in rows for folder,n,p in D[r] for x in p["iv"] if cond(n,x)]
def show(name,L):
    print(name,len(L),"m0",f2(min(x["m0"] for x in L)),"to",f2(max(x["m0"] for x in L)),"m1",f2(min(x["m1"] for x in L)),"to",f2(max(x["m1"] for x in L)))
show("part L asmread",sel(["L"],lambda n,x:x["k"]=="asmread" and x["pos"]==1))
show("C read after oldread",sel(["C"],lambda n,x:x["k"]=="read" and x["before"]=="oldread"))
show("C read after asmread",sel(["C"],lambda n,x:x["k"]=="read" and x["before"]=="asmread"))
show("C asmread after read",sel(["C"],lambda n,x:x["k"]=="asmread" and x["before"]=="read"))
show("C asmread first",sel(["C"],lambda n,x:x["k"]=="asmread" and x["before"] is None))
show("C asmread after oldread",sel(["C"],lambda n,x:x["k"]=="asmread" and x["before"]=="oldread"))
show("I asmread",sel(["I"],lambda n,x:x["k"]=="asmread" and x["pos"]==1))
show("F asmread",sel(["F"],lambda n,x:x["k"]=="asmread" and x["pos"]==1))
show("pool asmread",sel(["L-1","L-2","L-3","L-4"],lambda n,x:x["k"]=="asmread" and x["pos"]==1))
show("R0,R0b asmread",sel(["R0","R0b"],lambda n,x:x["k"]=="asmread" and x["pos"]==1))
# who sets extremes in 7200 no C oldread
L=[(r,folder.split("-")[1],x) for r in ("L","I","F") for folder,n,p in D[r] for x in p["iv"] if x["k"]=="oldread" and x["pos"]==0]
for key,fn in (("m1 min",min),("m1 max",max)):
    v=fn(L,key=lambda t:t[2]["m1"]); print(key,v[0],v[1],"round",v[2]["round"],f2(v[2]["m1"]))
v=max(L,key=lambda t:t[2]["m0"]); print("m0 max",v[0],v[1],"round",v[2]["round"],f2(v[2]["m0"]))
v=min(L,key=lambda t:t[2]["m0"]); print("m0 min",v[0],v[1],"round",v[2]["round"],f2(v[2]["m0"]))
# without control I too
L2=[t for t in L if t[0]!="I"]
print("no C no I: m0",f2(min(t[2]["m0"] for t in L2)),f2(max(t[2]["m0"] for t in L2)),"m1",f2(min(t[2]["m1"] for t in L2)),f2(max(t[2]["m1"] for t in L2)))
