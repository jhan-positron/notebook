import csv, sys
def load(fn):
    rows=[]; hdr=None; passes=None
    for line in open(fn):
        line=line.strip()
        if line.startswith('# bandwidth'):
            passes=int(line.split('passes=')[1].split()[0]); continue
        if line.startswith('#'): continue
        if line.startswith('mem,'): hdr=line.split(','); continue
        d=dict(zip(hdr,line.split(','))); d['passes']=passes; rows.append(d)
    return rows
def summarize(fn, label):
    rows=load(fn)
    print(f"== {label}: {len(rows)} rows ({sum(r['rep']=='best' for r in rows)} best rows)")
    best={}
    for r in rows:
        if r['rep']=='best':
            dash=[k for k in r if r[k]=='-']
            print(f"  best {r['kernel']:5s} {int(r['bytes_per_thread']):6d}: {len(dash)} '-' columns, agg={r['aggregate_GBps']}")
            continue
        b=int(r['bytes_per_thread']); p=r['passes']; k=r['kernel']
        el=float(r['elapsed_s']); tb=int(r['total_bytes']); agg=float(r['aggregate_GBps'])
        tpp_el=el/p*1e9; tpp_agg=tb/(agg*1e9)/p*1e9
        refill=float(r['l1d_refill_per_line'])
        print(f"  {k:5s} {b:6d} rep{r['rep']} passes={p} elapsed={el*1e6:.0f}us tpp(elapsed)={tpp_el:7.2f}ns tpp(agg)={tpp_agg:7.2f}ns agg={agg:.3f}GB/s cyc/line={r['cycles_per_line']} l1refill={refill}")
        key=(k,b)
        if key not in best or agg>best[key][0]: best[key]=(agg,tpp_agg,tpp_el,refill,p)
    return best
def fit(pts):
    n=len(pts); sx=sum(x for x,y in pts); sy=sum(y for x,y in pts)
    sxx=sum(x*x for x,y in pts); sxy=sum(x*y for x,y in pts)
    m=(n*sxy-sx*sy)/(n*sxx-sx*sx); c=(sy-m*sx)/n
    res=[(x,y,y-(m*x+c)) for x,y in pts]
    return m,c,res
bp=summarize(sys.argv[1],'per-pass'); ba=summarize(sys.argv[2],'asm')
for k in ('read','write'):
    for name,src in (('tpp(agg)',1),('tpp(elapsed)',2)):
        pts=[(b,v[src]) for (kk,b),v in sorted(bp.items()) if kk==k]
        m,c,res=fit(pts)
        ymin=min(y for x,y in pts)
        print(f"fit {k} per-pass best reps using {name}: intercept={c:.2f} ns ({c*2.8:.0f} cyc @2.8GHz), slope={1/m:.2f} GB/s ({1/m/2.8:.1f} B/cyc); residuals ns: "+", ".join(f"{x//1024}K:{r:+.2f}({abs(r)/ymin*100:.1f}%)" for x,y,r in res)+f"; max |res|/min tpp = {max(abs(r) for _,_,r in res)/ymin*100:.2f}%")
    print(f"  asm {k} best: "+", ".join(f"{b//1024}K {v[0]:.1f}GB/s ({v[0]/2.8:.1f}B/cyc, tpp {v[1]:.2f}ns)" for (kk,b),v in sorted(ba.items()) if kk==k))
    print(f"  per-pass {k} best: "+", ".join(f"{b//1024}K {v[0]:.1f}GB/s" for (kk,b),v in sorted(bp.items()) if kk==k))
