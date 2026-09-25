import json, math
P = json.load(open("/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/pairs.json"))
def sd(x):
    n=len(x); m=sum(x)/n
    return math.sqrt(sum((v-m)**2 for v in x)/(n-1)) if n>1 else None
def welch(a,b):
    na,nb=len(a),len(b)
    if na<2 or nb<2: return None,None
    ma,mb=sum(a)/na,sum(b)/nb
    va,vb=sd(a)**2/na, sd(b)**2/nb
    t=(ma-mb)/math.sqrt(va+vb)
    df=(va+vb)**2/((va**2/(na-1))+(vb**2/(nb-1)))
    return t,df
# two-sided p from t distribution via regularized incomplete beta (simple numeric)
def betainc(a,b,x, N=20000):
    # numeric integration of the regularized incomplete beta
    import math
    if x<=0: return 0.0
    if x>=1: return 1.0
    f=lambda u: u**(a-1)*(1-u)**(b-1)
    h=x/N; s=0.0
    for i in range(N):
        u0=i*h; u1=(i+1)*h; um=(u0+u1)/2
        # avoid u=0 singularity when a<1: a>=0.5 here
        s+= (f(max(u0,1e-12))+4*f(um)+f(u1))*h/6
    B=math.gamma(a)*math.gamma(b)/math.gamma(a+b)
    return s/B
def p_two(t,df):
    x=df/(df+t*t)
    return betainc(df/2,0.5,x)
print(f'{"grp":3s} {"kern":6s} {"setup":58s} {"cpu":>8s} n {"fpga":>8s} n {"d ms":>7s} {"pct":>6s} {"t_page":>7s} {"t_mine":>7s} {"df":>5s} {"p2":>6s}')
for p in P:
    a=p["fpga_reps"]; b=p["cpu_reps"]
    t,df=welch(a,b)
    d=sum(a)/len(a)-sum(b)/len(b)
    pct=100*d/(sum(b)/len(b))
    ts = f"{t:+.1f}" if t is not None else "-"
    dfs = f"{df:.1f}" if df is not None else "-"
    pp = f"{p_two(t,df):.3f}" if t is not None else "-"
    tp = f"{p['t']:+.1f}" if p['t'] is not None else "-"
    print(f'{p["group"]:3s} {p["kernel"]:6s} {p["setup"][:58]:58s} {sum(b)/len(b):8.1f} {len(b)} {sum(a)/len(a):8.1f} {len(a)} {d:+7.1f} {pct:+6.1f} {tp:>7s} {ts:>7s} {dfs:>5s} {pp:>6s}  sd_cpu={sd(b)} sd_fpga={sd(a)}')
print()
print("count by kernel:", {k: sum(1 for p in P if p["kernel"]==k) for k in ("avx","canon","vnnik")})
print("count rt vnnik:", sum(1 for p in P if p["kernel"]=="vnnik" and p["group"]=="rt"))
canon=[p for p in P if p["kernel"]=="canon"]
print("canon pcts (all):", [(round(p["pct"],1), p["setup"][:30]) for p in canon])
canon_lfl=[p for p in canon if "two builds" not in p["setup"] and "c7844ca2ce" not in p["setup"]]
print("canon like-for-like min/max:", min(p["pct"] for p in canon_lfl), max(p["pct"] for p in canon_lfl))
vn=[p for p in P if p["kernel"]=="vnnik"]
print("vnnik pcts:", [round(p["pct"],1) for p in vn], "min/max", min(p["pct"] for p in vn), max(p["pct"] for p in vn))
av=[p for p in P if p["kernel"]=="avx"]
print("avx pcts:", [round(p["pct"],1) for p in av], "min/max", min(p["pct"] for p in av), max(p["pct"] for p in av))
