import json, math, statistics as st
R=json.load(open('/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/fpga-campaign-rows.json'))
def mean(x): return sum(x)/len(x)
def sd(x): return st.stdev(x) if len(x)>1 else 0.0
def welch(a,b):
    if len(a)<2 or len(b)<2: return float('nan')
    va,vb=st.variance(a),st.variance(b)
    return (mean(a)-mean(b))/math.sqrt(va/len(a)+vb/len(b))
P=[1024,1536,2048,3000,4096,5120,6144,7168,8192]
def sel(**k):
    out=[]
    for r in R:
        ok=True
        for kk,v in k.items():
            if callable(v):
                if not v(r.get(kk)): ok=False;break
            elif r.get(kk)!=v: ok=False;break
        if ok: out.append(r)
    return out
arms={
 'avxcpu':  lambda r: r['campaign']=='q4b-swattn-20260919' and r['arm']=='base',
 'canoncpu':lambda r: r['arm']=='canon' and r['tag'].startswith('canon-pass'),
 'fpgabase':lambda r: r['arm']=='fpgabase' and r['tag'].startswith('fpgabase-pass'),
 'fpgacanon':lambda r: r['arm']=='fpgacanon' and r['tag'].startswith('fpgacanon-pass'),
}
F='ttft_harness_ms'
agg={}
print("== Section 5 warm/1024 means (harness ms) ==")
for a,f in arms.items():
    for p in P:
        xs=[r for r in R if f(r) and r['prompt_length']==p]
        xs.sort(key=lambda r:(r['started']))
        v=[r[F] for r in xs]; t=[r['tps_mean'] for r in xs]; h=[r['cache_hit_pct'] for r in xs]
        agg[(a,p)]=dict(v=v,t=t,h=h,tags=[r['tag'] for r in xs])
        print(f"{a:9s} {p:5d} n={len(v)} mean={mean(v):8.1f} sd={sd(v):6.1f} vals={v} tps={mean(t):6.1f} hits={[round(x,1) for x in h]}")
print("\n== cold cells ==")
cold={}
for a in ['fpgabase','fpgacanon']:
    for p in [4096,8192]:
        xs=sorted([r for r in R if r['arm']==a and 'cold' in r['tag'] and r['prompt_length']==p],key=lambda r:r['tag'])
        v=[r[F] for r in xs]; t=[r['tps_mean'] for r in xs]
        cold[(a,p)]=dict(v=v,t=t,h=[r['cache_hit_pct'] for r in xs],tags=[r['tag'] for r in xs])
        print(f"{a:9s} cold {p} n={len(v)} mean={mean(v):.1f} sd={sd(v):.1f} vals={v} spread={max(v)-min(v)} tps={mean(t):.1f} {[round(x,2) for x in t]}")
chk=[r for r in R if r['tag']=='check-8u-p8192'][0]
print("check-8u-p8192", chk[F], chk['tps_mean'], chk['cache_hit_pct'], chk['started'])
print("\n== FPGA vs CPU (warm), canon and nightly ==")
for p in P:
    c=agg[('fpgacanon',p)]['v']; k=agg[('canoncpu',p)]['v']; b=agg[('fpgabase',p)]['v']; a=agg[('avxcpu',p)]['v']
    print(f"{p:5d} canon: {mean(c):.1f} vs {mean(k):.1f} = {100*(mean(c)/mean(k)-1):+.1f}%  t={welch(c,k):+.1f} | nightly: {mean(b):.1f} vs {mean(a):.1f} = {100*(mean(b)/mean(a)-1):+.1f}% ratio={mean(a)/mean(b):.2f}x t={welch(b,a):+.1f}")
# canon 3000 without the two uneven cells
c3=agg[('canoncpu',3000)]
print("canon 3000 vals",c3['v'],c3['tags'])
rest=[v for v,t in zip(c3['v'],c3['tags']) if v not in (2056,2296)]
print("canon 3000 without 2056/2296:",rest, mean(rest), "FPGA vs CPU:", 100*(mean(agg[('fpgacanon',3000)]['v'])/mean(rest)-1), "with:",100*(mean(agg[('fpgacanon',3000)]['v'])/mean(c3['v'])-1))
print("\n== ratios ==")
cc=mean(cold[('fpgacanon',8192)]['v']); cb=mean(cold[('fpgabase',8192)]['v'])
print("cold 8192: canon-cpu check 12743 / fpgacanon", cc, "=", 12743/cc, " / fpgabase", cb, "=", 12743/cb, " pct", 100*(cc/12743-1), " build effect", 100*(cc/cb-1))
print("cold 4096:", cold[('fpgacanon',4096)]['v'], cold[('fpgabase',4096)]['v'], 100*(mean(cold[('fpgacanon',4096)]['v'])/mean(cold[('fpgabase',4096)]['v'])-1))
w=lambda a,p: mean(agg[(a,p)]['v'])
print("warm 8192: avxcpu",w('avxcpu',8192),"canoncpu",w('canoncpu',8192),"ratio",w('avxcpu',8192)/w('canoncpu',8192),"fpgacanon",w('fpgacanon',8192),"ratio canoncpu/fpgacanon",w('canoncpu',8192)/w('fpgacanon',8192),"avxcpu/fpgacanon",w('avxcpu',8192)/w('fpgacanon',8192),"fpgabase",w('fpgabase',8192))
print("nightly 1024 ratio", w('avxcpu',1024)/w('fpgabase',1024), "7168", w('avxcpu',7168)/w('fpgabase',7168), "history 674/509.5", w('avxcpu',1024)/509.5, "554 above 528/509.5:", w('fpgabase',1024)-528, w('fpgabase',1024)-509.5)
print("fpgabase 1024 vals", agg[('fpgabase',1024)]['v'], "spread", max(agg[('fpgabase',1024)]['v'])-min(agg[('fpgabase',1024)]['v']))
print("canoncpu 1024 vals", agg[('canoncpu',1024)]['v'])
print("decode 8192: fpgacanon warm tps", agg[('fpgacanon',8192)]['t'], mean(agg[('fpgacanon',8192)]['t']), " canoncpu warm", agg[('canoncpu',8192)]['t'], mean(agg[('canoncpu',8192)]['t']), " check cold", chk['tps_mean'], " fpgacanon cold", cold[('fpgacanon',8192)]['t'])
print("sd ranges below 4096 / from 4096 (FPGA arms):")
for a in ['fpgabase','fpgacanon']:
    lo=[sd(agg[(a,p)]['v']) for p in P if 1024<p<4096]; hi=[sd(agg[(a,p)]['v']) for p in P if p>=4096]
    print(a, [round(x) for x in lo], [round(x) for x in hi])
print("cache hits warm range (all 4 arms, p>1024):", min(min(agg[(a,p)]['h']) for a in arms for p in P if p>1024), max(max(agg[(a,p)]['h']) for a in arms for p in P if p>1024))
print("cache hits warm range (FPGA arms only):", min(min(agg[(a,p)]['h']) for a in ['fpgabase','fpgacanon'] for p in P if p>1024), max(max(agg[(a,p)]['h']) for a in ['fpgabase','fpgacanon'] for p in P if p>1024))
print("canon cpu 4096 hits", agg[('canoncpu',4096)]['h'])

print("\n== Section 6: paired AMX vs AVX, FPGA attention ==")
def paired(vb,vc):
    d=[100*(c/b-1) for b,c in zip(vb,vc)]
    return d, mean(d)
allTTFT=[]
for p in P:
    b=agg[('fpgabase',p)]; c=agg[('fpgacanon',p)]
    d,m=paired(b['v'],c['v']); dt,mt=paired(b['t'],c['t'])
    if p>=4096: allTTFT+=d
    print(f"{p:5d} warm/1024: TTFT {mean(b['v']):.0f}+/-{sd(b['v']):.0f} vs {mean(c['v']):.0f}+/-{sd(c['v']):.0f} d={[round(x,1) for x in d]} mean={m:+.1f} (means-based {100*(mean(c['v'])/mean(b['v'])-1):+.1f}) t={welch(c['v'],b['v']):+.1f} | TPS {mean(b['t']):.1f} vs {mean(c['t']):.1f} d={[round(x,1) for x in dt]} mean={mt:+.1f} t={welch(c['t'],b['t']):+.1f} | hits {mean(b['h']):.1f}/{mean(c['h']):.1f}")
print("15 paired passes range", min(allTTFT), max(allTTFT))
for p in [4096,8192]:
    b=cold[('fpgabase',p)]; c=cold[('fpgacanon',p)]
    d,m=paired(b['v'],c['v']); dt,mt=paired(b['t'],c['t'])
    print(f"{p:5d} cold: TTFT {mean(b['v']):.0f}+/-{sd(b['v']):.0f} vs {mean(c['v']):.0f}+/-{sd(c['v']):.0f} d={[round(x,1) for x in d]} mean={m:+.1f} t={welch(c['v'],b['v']):+.1f} | TPS {mean(b['t']):.1f} vs {mean(c['t']):.1f} d={[round(x,1) for x in dt]} mean={mt:+.1f} t={welch(c['t'],b['t']):+.1f} | hits {mean(b['h']):.1f}/{mean(c['h']):.1f} tags {b['tags']} {c['tags']}")
print("warm TPS below cold TPS at same prompt:")
for p in [4096,8192]:
    for a in ['fpgabase','fpgacanon']:
        print(a,p, 100*(mean(agg[(a,p)]['t'])/mean(cold[(a,p)]['t'])-1))
