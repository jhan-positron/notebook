# check_hit.py - hover hit targets and mark sizes of both figures (static reading of the SVG source)
import re,html,math,collections
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
t=open(P).read()
def pts(svg):
    out=[]
    for m in re.finditer(r'<g class="pt"><title>(.*?)</title>(.*?)</g>',svg,re.S):
        title=html.unescape(m.group(1)); body=m.group(2)
        cs=re.findall(r'<circle([^>]*)/>',body)
        d=[]
        for c in cs:
            a=dict(re.findall(r'([\w-]+)="([^"]*)"',c)); d.append(a)
        out.append((title,d,body))
    return out
f1=re.search(r'<svg class="f1w".*?</svg>',t,re.S).group(0)
f2=re.findall(r'<svg viewBox="0 0 466 \d+".*?</svg>',t,re.S)
for name,svg in (('fig1 f1w',f1),('fig2 left',f2[0]),('fig2 right',f2[1])):
    P_=pts(svg)
    hit=[];mk=[];ring=[]
    rows=[]
    for title,d,body in P_:
        h=[c for c in d if c.get('fill-opacity')=='0']; m=[c for c in d if 'mk' in c.get('class','')]
        halo=[c for c in d if c.get('fill')=='#fcfcfb' and c.get('fill-opacity') is None and 'class' not in c]
        assert len(m)==1, (title[:60],d)
        mm=m[0]; r=float(mm['r']); sw=float(mm.get('stroke-width',0)); outer=r+sw/2
        hr=float(h[0]['r']) if h else None
        rows.append((float(mm['cx']),float(mm['cy']),outer,hr,float(halo[0]['r']) if halo else None,mm['class'],title))
    print('==',name,'points',len(rows))
    print('   mark outer radius:',collections.Counter(round(r[2],2) for r in rows))
    print('   mark class:',collections.Counter(r[5] for r in rows))
    print('   halo (surface ring) radius:',collections.Counter(r[4] for r in rows))
    print('   hit radius:',sorted(collections.Counter(r[3] for r in rows).items()))
    small=0; could=0
    for i,a in enumerate(rows):
        nn=min((math.hypot(a[0]-b[0],a[1]-b[1]) for j,b in enumerate(rows) if j!=i),default=999)
        eff=max(a[3] or 0,a[2])
        if eff<12:
            small+=1
            if nn/2>eff+0.5:
                could+=1
                if could<=12: print('     small target although free space: eff r=%.1f, nearest other dot %.1f px away | %s'%(eff,nn,a[6][:90]))
    print('   targets with effective radius < 12 px:',small,'of',len(rows),'; of these not limited by a neighbour at half distance:',could)
    # overlap of marks
    ov=0;full=0
    for i,a in enumerate(rows):
        for j,b in enumerate(rows):
            if j<=i: continue
            dd=math.hypot(a[0]-b[0],a[1]-b[1])
            if dd<a[2]+b[2]: ov+=1
            if dd<2.0: full+=1; print('     nearly coincident marks (centre distance %.2f px): %s || %s'%(dd,a[6][:70],b[6][:70]))
    print('   overlapping mark pairs:',ov,'nearly coincident (<2 px):',full)
