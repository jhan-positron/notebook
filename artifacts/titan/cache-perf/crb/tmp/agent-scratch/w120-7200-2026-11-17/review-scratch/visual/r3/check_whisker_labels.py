# check_whisker_labels.py - Figure 1: does a whisker (lowest to highest interval) run into a value label or the drop label? viewBox units.
import json,re,html
V='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual/r3/work/'
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
t=open(P).read()
for w,cls in ((1280,'f1w'),(900,'f1m'),(420,'f1n')):
    m=json.load(open(V+f'measure-{w}.json'))
    s=[x for x in m['svgs'] if x['cls']==cls][0]
    T=s['texts']
    def tb(t_):
        x=float(t_['x']); y=float(t_['y']); fs=float(t_['fs']); cl=t_['cl']; a=t_['anchor'] or 'start'
        x0 = x if a=='start' else (x-cl if a=='end' else x-cl/2)
        return (x0, y-0.74*fs, x0+cl, y+0.05*fs)
    svg=re.search(r'<svg class="%s".*?</svg>'%cls,t,re.S).group(0)
    n=0;mind=99
    for mm in re.finditer(r'<g class="pt"><title>(.*?)</title>.*?<path d="M([\d.]+) ([\d.]+)V([\d.]+)M([\d.]+) ',svg,re.S):
        xa,ya,yb,xb=float(mm.group(2)),float(mm.group(3)),float(mm.group(4)),float(mm.group(5))
        wb=(xa-0.55,ya,xb+0.55,yb)
        for t_ in T:
            b=tb(t_)
            if min(b[2],wb[2])-max(b[0],wb[0])>0 and min(b[3],wb[3])-max(b[1],wb[1])>0:
                n+=1; print('  ',cls,'whisker',[round(v,1) for v in wb],'touches text',repr(t_['s']),[round(v,1) for v in b],'|',html.unescape(mm.group(1))[:60])
            # horizontal clearance to value labels on the same row
            if re.fullmatch(r'\d+\.\d\d',t_['s']) and abs((b[1]+b[3])/2-(ya+yb)/2)<4:
                d=min(abs(b[0]-wb[2]),abs(wb[0]-b[2])) if not (min(b[2],wb[2])-max(b[0],wb[0])>0) else 0
                mind=min(mind,d)
    print(cls,'whisker/text contacts:',n,'smallest horizontal clearance whisker to value label: %.1f'%mind)
