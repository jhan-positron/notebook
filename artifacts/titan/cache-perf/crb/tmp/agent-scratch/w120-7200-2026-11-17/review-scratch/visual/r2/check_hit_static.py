# check_hit_static.py - Figure 2: dots whose centre lies under the transparent hit circle (r = 7.5) of a dot drawn later.
import re, html, math
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
h=open(P).read()
lines=h.split('\n')
svgs=re.findall(r'<svg viewBox="0 0 (\d+) (\d+)"[^>]*role="img"[^>]*>(.*?)</svg>',h,re.S)
tot=0
for W,H,body in svgs:
    pts=[]
    for m in re.finditer(r'<g class="pt"><title>(.*?)</title><circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="#fcfcfb" fill-opacity="0"/><circle class="mk \w+" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"',body,re.S):
        t=html.unescape(m.group(1)); pts.append((float(m.group(2)),float(m.group(3)),float(m.group(4)),t))
    bad=[]
    for i,a in enumerate(pts):
        for b in pts[i+1:]:
            d=math.hypot(a[0]-b[0],a[1]-b[1])
            if d<b[2]: bad.append((round(d,2),a[3],b[3])); break
    tot+=len(bad)
    print(f'fig2 {W}x{H}: dots {len(pts)}, hit radius {set(p[2] for p in pts)}, centres covered by a later hit circle: {len(bad)}')
    for d,a,b in bad[:3]:
        va=re.search(r': ([\d.]+) GB/s\. Row',a).group(1); vb=re.search(r': ([\d.]+) GB/s\. Row',b).group(1)
        print(f'   distance {d} px: dot {va} GB/s ({a.split(":")[0][:30]}) is answered by the dot {vb} GB/s')
print('total',tot)
