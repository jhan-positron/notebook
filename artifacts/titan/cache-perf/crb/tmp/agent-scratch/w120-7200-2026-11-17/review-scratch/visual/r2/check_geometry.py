# check_geometry.py - compare the drawn positions in the SVG charts of the report with the values in their <title> texts.
import re, html, sys
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
h=open(P).read()
svgs=re.findall(r'<svg (class="f1[wmn]" )?viewBox="0 0 (\d+) (\d+)"[^>]*role="img"[^>]*>(.*?)</svg>',h,re.S)
print('chart svgs:',len(svgs))
bad=0
def axis(body):
    # tick texts: tabular-nums, text-anchor middle, integer content -> map x to value (least squares on distinct ticks)
    t=re.findall(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*text-anchor="middle"[^>]*tabular-nums">(\d+)</text>',body)
    pts=sorted(set((float(x),float(v)) for x,y,v in t))
    (x0,v0),(x1,v1)=pts[0],pts[-1]
    k=(x1-x0)/(v1-v0)
    for x,v in pts:
        assert abs(x-(x0+(v-v0)*k))<0.11,(x,v)
    return (lambda v: x0+(v-v0)*k), pts
for cls,W,H,body in svgs:
    name=cls.strip() or f'fig2 {W}x{H}'
    fx,pts=axis(body)
    print(f'== {name}: ticks {[(x,int(v)) for x,v in pts]}')
    n=0; maxd=0
    if 'f1' in name:
        for m in re.finditer(r'<g class="pt"><title>(.*?)</title>(.*?)</g>',body,re.S):
            t=html.unescape(m.group(1)); g=m.group(2)
            med=float(re.search(r'Median ([\d.]+) GB/s',t).group(1))
            iv=[float(a) for a in re.search(r'Intervals?: ([\d., ]+) GB/s',t).group(1).split(', ')]
            cx=float(re.search(r'class="mk[^"]*" cx="([\d.]+)"',g).group(1))
            d=abs(cx-fx(med)); maxd=max(maxd,d); n+=1
            if d>0.11: bad+=1; print('  DOT off',t[:60],cx,fx(med))
            pm=re.search(r'<path d="M([\d.]+) [\d.]+V[\d.]+M([\d.]+) ',g)
            if not pm: bad+=1; print('  no whisker',t[:60]); continue
            a,b=float(pm.group(1)),float(pm.group(2))
            if abs(a-fx(min(iv)))>0.11 or abs(b-fx(max(iv)))>0.11: bad+=1; print('  WHISKER off',t[:70],a,b,fx(min(iv)),fx(max(iv)))
            # median check
            s=sorted(iv); md=(s[len(s)//2] if len(s)%2 else (s[len(s)//2-1]+s[len(s)//2])/2)
            if abs(md-med)>0.0051: bad+=1; print('  MEDIAN text off',t[:70],md,med)
            # value label next to the dot
        print(f'  dots checked {n}, largest x error {maxd:.3f} px')
        # drop lines: line from load-only dot to old dot, label text
        k=0
        for m in re.finditer(r'<g><title>(.*?)</title><line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)"[^>]*/>.*?<text x="([\d.]+)" y="([\d.]+)"[^>]*>(.*?)</text></g>',body,re.S):
            t=html.unescape(m.group(1)); x1,y1,x2,tx,ty,lab=float(m.group(2)),float(m.group(3)),float(m.group(4)),float(m.group(5)),float(m.group(6)),m.group(7)
            k+=1
            if abs(tx-(x1+x2)/2)>0.11: bad+=1; print('  drop label not centred',lab,tx,(x1+x2)/2)
            if not (0<y1-ty<=9): bad+=1; print('  drop label not on its row',lab,y1,ty)
            if lab not in t: bad+=1; print('  drop label differs from its title',lab,'|',t[:120])
        print(f'  drop lines checked {k}')
    else:
        for m in re.finditer(r'<g class="pt"><title>(.*?)</title>(.*?)</g>',body,re.S):
            t=html.unescape(m.group(1)); g=m.group(2)
            v=float(re.search(r': ([\d.]+) GB/s\. Row',t).group(1))
            cx=float(re.search(r'class="mk[^"]*" cx="([\d.]+)"',g).group(1))
            d=abs(cx-fx(v)); maxd=max(maxd,d); n+=1
            if d>0.11: bad+=1; print('  DOT off',t[:70],cx,fx(v))
            lo,hi=[float(a) for a in re.search(r'Row: ([\d.]+) to ([\d.]+) GB/s',t).groups()]
            if not (lo-0.005<=v<=hi+0.005): bad+=1; print('  value outside its row range',t[:80])
        print(f'  dots checked {n}, largest x error {maxd:.3f} px')
        for m in re.finditer(r'<g><title>(Grey band.*?)</title><rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"',body,re.S):
            t=html.unescape(m.group(1)); x,y,w,hh=[float(a) for a in m.groups()[1:]]
            lo,hi=[float(a) for a in re.search(r'([\d.]+) to ([\d.]+) GB/s',t).groups()]
            ok=abs(x-fx(lo))<0.11 and abs(x+w-fx(hi))<0.11
            print(f'  band {lo} to {hi}: rect x {x} to {x+w:.1f}, expected {fx(lo):.1f} to {fx(hi):.1f}, y {y} to {y+hh} ->','ok' if ok else 'OFF')
            if not ok: bad+=1
print('defects:',bad)
