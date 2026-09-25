import re, json, math
R="/home/jhan/workspace/intel-AMX/exec/results"
def parse(path):
    out=[]
    cur=None
    for line in open(path, errors="replace"):
        if line.startswith("### runtron kind=rt"):
            m=re.search(r"cell=(\S+) .*attn=(\S+) .*arm=(\S+) rep=(\d+).*?(2026-09-\d\dT\d\d:\d\d:\d\d)", line)
            cur=dict(cell=m.group(1), attn=m.group(2), arm=m.group(3), rep=int(m.group(4)), ts=m.group(5), ttft=None) if m else None
            if cur: out.append(cur)
        elif cur and cur["ttft"] is None and "Parsing the prompt took" in line:
            cur["ttft"]=float(re.search(r"took ([0-9.]+) s", line).group(1))*1000
    return out
for name in ("wedperf-attr-20260916","wedperf-20260916"):
    print("==",name)
    rows=[r for r in parse(f"{R}/{name}/rt-results.txt") if r["cell"].startswith("q3-4b")]
    groups={}
    for r in rows: groups.setdefault((r["cell"],r["attn"],r["arm"]),[]).append(r)
    for k,v in sorted(groups.items()):
        v=sorted(v,key=lambda r:r["rep"])
        print(k, [round(r["ttft"],1) for r in v], "ts", v[0]["ts"], "..", v[-1]["ts"])
d=json.load(open(f"{R}/issue4500-20260918/m6/summary.json"))
print("== m6 per-rep ttft"); 
for k,v in d.items(): print(k, [v[r]["ttft"] for r in sorted(v)])
# section 3 stats
def sd(x):
    n=len(x); m=sum(x)/n; return math.sqrt(sum((v-m)**2 for v in x)/(n-1))
def welch(a,b):
    na,nb=len(a),len(b); ma,mb=sum(a)/na,sum(b)/nb
    va,vb=sd(a)**2/na, sd(b)**2/nb
    t=(ma-mb)/math.sqrt(va+vb) if va+vb>0 else float('inf')
    df=(va+vb)**2/((va**2/(na-1))+(vb**2/(nb-1))) if va+vb>0 else float('nan')
    return ma,mb,100*(ma-mb)/mb,t,df
print("== section 3: build effect under FPGA attention (a = AMX build, b = AVX build), t of a-b")
attr_tp4={"avx":[2245.0,2278.7,2243.6,2235.1,2269.0,2247.4],"canon":[2281.1,2279.3,2290.7,2316.9,2271.4,2290.8],"vnnik":[2220.8,2262.5,2214.1,2260.0,2216.3,2209.5]}
attr_tp2={"avx":[3202.6,3238.8,3179.9,3218.6,3205.2,3240.1],"canon":[3203.0,3181.3,3197.5,3194.0,3209.9,3185.0],"vnnik":[3182.1,3143.8,3143.2,3166.7,3164.6,3166.0]}
for nm,g in (("attr tp4",attr_tp4),("attr tp2",attr_tp2)):
    for k in ("canon","vnnik"):
        print(nm, k, "vs avx: mean %.1f vs %.1f  %+.1f %%  t %+.1f df %.1f" % welch(g[k],g["avx"]))
m6t2={"avx":[763,761],"vnnik":[698,701],"kill":[761,764]}
m6t4={"avx":[847,850],"vnnik":[809,809],"kill":[815,814]}
for nm,g in (("m6 tp2",m6t2),("m6 tp4",m6t4)):
    for k in ("vnnik","kill"):
        print(nm, k, "vs avx: mean %.1f vs %.1f  %+.1f %%  t %+.1f df %.1f" % welch(g[k],g["avx"]))
    print(nm, "vnnik vs kill: mean %.1f vs %.1f  %+.1f %%  t %+.1f df %.1f" % welch(g["vnnik"],g["kill"]))
print("whole tp2 canon 516 vs nightly 528: %+.1f %%; vs 13-night mean 509.5: %+.1f %%  z of 528 in 13 nights: %.1f" % (100*(516-528)/528, 100*(516-509.5)/509.5, (528-509.5)/7.2))
print("whole tp4 canon 646 vs nightly 636: %+.1f %%; vnnik 629 vs 636: %+.1f %%; 13-night 635.2 sd 10.1" % (100*(646-636)/636, 100*(629-636)/636))
print("whole tp2 vnnik 504 vs 528: %+.1f %%" % (100*(504-528)/528))
# p sanity
def betainc(a,b,x,N=40000):
    if x<=0: return 0.0
    if x>=1: return 1.0
    f=lambda u: u**(a-1)*(1-u)**(b-1)
    h=x/N; s=0.0
    for i in range(N):
        u0=i*h; u1=(i+1)*h; um=(u0+u1)/2
        s+=(f(max(u0,1e-12))+4*f(um)+f(u1))*h/6
    return s/(math.gamma(a)*math.gamma(b)/math.gamma(a+b))
def p2(t,df): return betainc(df/2,0.5,df/(df+t*t))
print("p sanity: t=2 df=10 ->",round(p2(2,10),4),"(expect 0.0734); t=12.706 df=1 ->",round(p2(12.706,1),4),"(expect 0.05); t=4.303 df=2 ->", round(p2(4.303,2),4), "(expect 0.05)")
