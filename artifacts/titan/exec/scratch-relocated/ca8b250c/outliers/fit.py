import sys, glob, csv, collections
port = {2:(2,3), 4:(3,2), 6:(4,3), 8:(5,2)}
home = [(1,3),(2,4),(3,3),(4,4),(5,3)]
def best(path):
    b=None
    for line in open(path):
        if line.startswith("#") or line.startswith("mem,"): continue
        f=line.split(",")
        if f[3]=="-": continue
        v=float(f[5]); b=v if b is None or v<b else b
    return b
for run in sys.argv[1:]:
    D=glob.glob(f"/home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-{run}/results/*/")[0]
    rows=[]
    for c in port:
        for r in range(5):
            y=best(f"{D}/latency-ocm-region{r}-route-cpu{c}.csv")
            dx=abs(port[c][0]-home[r][0]); dy=abs(port[c][1]-home[r][1])
            rows.append((y,dx,dy))
    # least squares y = a + b*dx + c*dy
    import itertools
    n=len(rows)
    X=[[1,dx,dy] for _,dx,dy in rows]; Y=[y for y,_,_ in rows]
    # normal equations 3x3
    XtX=[[sum(X[i][p]*X[i][q] for i in range(n)) for q in range(3)] for p in range(3)]
    XtY=[sum(X[i][p]*Y[i] for i in range(n)) for p in range(3)]
    # solve via Gaussian elimination
    M=[XtX[p]+[XtY[p]] for p in range(3)]
    for p in range(3):
        piv=M[p][p]
        M[p]=[v/piv for v in M[p]]
        for q in range(3):
            if q!=p:
                f=M[q][p]; M[q]=[a-f*b for a,b in zip(M[q],M[p])]
    a,b,c=[M[p][3] for p in range(3)]
    rms=(sum((y-(a+b*dx+c*dy))**2 for y,dx,dy in rows)/n)**0.5
    print(f"run {run}: fit {a:.2f} + {b:.2f}/X + {c:.2f}/Y, rms {rms:.2f} ns, n={n}")
    # G6 direction check from cmn-counts.csv
    cnt=collections.defaultdict(dict)
    for row in csv.DictReader(open(f"{D}/cmn-counts.csv")):
        if row["label"].startswith("route-ocm") and row["event"].startswith("mxp_") and row["event"].endswith("dat_txflit_valid"):
            cnt[(row["label"],int(row["nodeid"]))][row["event"][4]]=int(row["count"])
    ok_dsu=ok_node=tot=0; minshare=1.0
    for c in port:
        for r in range(5):
            lab=f"route-ocm{r}-cpu{c}"; dsu={2:152,4:208,6:280,8:336}[c]; node=[88,160,216,288,344][r]
            px,py=port[c]; hx,hy=home[r]
            def xfirst(fx,fy,tx,ty):
                if tx!=fx: return "e" if tx>fx else "w"
                return "n" if ty>fy else "s"
            for nid,exp,which in ((dsu,xfirst(px,py,hx,hy),"dsu"),(node,xfirst(hx,hy,px,py),"node")):
                d=cnt.get((lab,nid))
                if not d: print("missing",lab,nid); continue
                top=max(d,key=d.get); share=d[top]/sum(d.values()); minshare=min(minshare,share)
                if which=="dsu": tot+=1; ok_dsu+= top==exp
                else: ok_node+= top==exp
    print(f"  G6: DSU end X-first {ok_dsu}/{tot}, node end X-first {ok_node}/{tot}, min dominant share {minshare:.2f}")
