# check_fig2.py - Figure 2: every dot against the value in its own tooltip, against the axis, and against facts.json (own grouping).
import re,json,html,collections,statistics
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/'
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
t=open(P).read()
svgs=re.findall(r'<svg viewBox="0 0 466 \d+".*?</svg>',t,re.S)
assert len(svgs)==2
F=json.load(open(S+'facts.json'))['intervals']
def sel(**kw):
    out=[]
    for r in F:
        ok=True
        for k,v in kw.items():
            if callable(v):
                if not v(r.get(k)): ok=False;break
            elif r.get(k)!=v: ok=False;break
        if ok: out.append(r)
    return out
def rng(rs): 
    v=[r['GBps'] for r in rs]; return (round(min(v),2),round(max(v),2),len(v))
scales=[(458.0,260/18.0),(276.0,260/64.0)]
tot=0
for pi,(svg,(x0,k)) in enumerate(zip(svgs,scales)):
    print('== panel',pi)
    rows=collections.OrderedDict()
    bad=0
    for m in re.finditer(r'<g class="pt"><title>(.*?)</title>(.*?)</g>',svg,re.S):
        title=html.unescape(m.group(1)); body=m.group(2)
        mk=re.search(r'<circle class="mk (ho|fi)" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="(#[0-9a-f]+)"(?: stroke="(#[0-9a-f]+)")?',body)
        assert mk, body[:200]
        val=float(re.search(r': ([\d.]+) GB/s\. Row',title).group(1))
        cx=float(mk.group(2)); cy=float(mk.group(3))
        ex=190+(val-x0)*k
        if abs(ex-cx)>0.15: bad+=1; print('  X MISMATCH',title[:80],val,cx,round(ex,1))
        if cx<190-0.1 or cx>450+0.1: bad+=1; print('  OUT OF AXIS',title[:80],val,cx)
        name=title.split(':')[0]
        col=mk.group(6) if mk.group(1)=='ho' else mk.group(5)
        rows.setdefault(name,[]).append((val,cx,cy,mk.group(1),col,title))
        tot+=1
    print('  dots',sum(len(v) for v in rows.values()),'x mismatches',bad)
    for name,v in rows.items():
        vals=[a[0] for a in v]; ys=sorted(set(a[2] for a in v)); kinds=set((a[3],a[4]) for a in v)
        print('   %-70s n=%d %.2f..%.2f y=%s %s'%(name[:70],len(v),min(vals),max(vals),ys,kinds))
print('total dots',tot)
# expected groups from facts.json (own grouping)
print('-- facts.json, own grouping')
def show(lbl,rs): print('   %-58s %s'%(lbl,rng(rs)))
for d in ('L-1','L-2','L-3','L-4'):
    show(d+' oldread pos0',sel(dataset=d,kernel='oldread',pos=0)); show(d+' asmread pos1',sel(dataset=d,kernel='asmread',pos=1))
show('pool L oldread pos0',[r for d in ('L-1','L-2','L-3','L-4') for r in sel(dataset=d,kernel='oldread',pos=0)])
show('pool L asmread pos1',[r for d in ('L-1','L-2','L-3','L-4') for r in sel(dataset=d,kernel='asmread',pos=1)])
for d in ('F72d12','rerun-L','control-I'):
    show(d+' oldread pos0',sel(dataset=d,kernel='oldread',pos=0)); show(d+' asmread pos1',sel(dataset=d,kernel='asmread',pos=1))
show('rerun-C oldread',sel(dataset='rerun-C',kernel='oldread'))
show('rerun-C read after oldread',sel(dataset='rerun-C',kernel='read',kernel_before='oldread'))
show('rerun-C read after asmread',sel(dataset='rerun-C',kernel='read',kernel_before='asmread'))
show('rerun-C asmread after oldread',sel(dataset='rerun-C',kernel='asmread',kernel_before='oldread'))
show('rerun-C asmread after read',sel(dataset='rerun-C',kernel='asmread',kernel_before='read'))
show('rerun-C asmread first',sel(dataset='rerun-C',kernel='asmread',kernel_before=lambda s: s and s.startswith('none')))
for d in ('A-1','A-2','A-3'):
    show(d+' bw_old read',sel(dataset=d,kernel='read',binary='bw_old'))
    for rd in (1,2):
        rs=sel(dataset=d,kernel='read',binary='bw_new',round=rd)
        if rs: show(d+' bw_new read round %d'%rd,rs)
show('pool A bw_old read',[r for d in ('A-1','A-2','A-3') for r in sel(dataset=d,kernel='read',binary='bw_old')])
for rd in (1,2): show('pool A bw_new read round %d'%rd,[r for d in ('A-1','A-2') for r in sel(dataset=d,kernel='read',binary='bw_new',round=rd)])
for tg in ('T72A1','T72A2','T72A3'):
    show(tg+' bw_old read',sel(dataset='rerun-A',tag=tg,kernel='read',binary='bw_old'))
    for rd in (1,2): show(tg+' bw_new read round %d'%rd,sel(dataset='rerun-A',tag=tg,kernel='read',binary='bw_new',round=rd))
