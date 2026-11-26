# check_fig2_dots.py - Figure 2: dots per row against the n in the row label; dots that hide each other; dots against the plot edges.
import re, html, collections, math
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
h=open(P).read()
svgs=re.findall(r'<svg viewBox="0 0 (\d+) (\d+)"[^>]*role="img"[^>]*>(.*?)</svg>',h,re.S)
for W,H,body in svgs:
    print(f'== fig2 {W}x{H}')
    rows=collections.OrderedDict()
    for m in re.finditer(r'<g class="pt"><title>(.*?)</title>(.*?)</g>',body,re.S):
        t=html.unescape(m.group(1)); g=m.group(2)
        mk=re.search(r'class="mk (\w+)" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"',g)
        cx,cy=float(mk.group(2)),float(mk.group(3))
        n=int(re.search(r'n = (\d+) interval',t).group(1))
        rng=re.search(r'Row: ([\d.]+ to [\d.]+) GB/s',t).group(1)
        name=t.split(':')[0]
        key=(name,rng,round(cy/40))
        rows.setdefault((name,rng),[]).append((cx,cy,mk.group(1),n,float(re.search(r': ([\d.]+) GB/s\. Row',t).group(1))))
    # labels: "lo to hi (n)"
    labs=re.findall(r'>([\d.]+ to [\d.]+) \((\d+)\)</text>',body)
    labd=collections.Counter((a,int(b)) for a,b in labs)
    print('  row labels with (n):',len(labs),' dot rows:',len(rows))
    for (name,rng),pts in rows.items():
        n=pts[0][3]
        flag=''
        if len(pts)!=n: flag+=f' COUNT {len(pts)} dots but n={n}'
        if (rng,n) not in labd: flag+=' NO LABEL with this range and n'
        lo,hi=[float(a) for a in rng.split(' to ')]
        vs=[p[4] for p in pts]
        if abs(min(vs)-lo)>0.005 or abs(max(vs)-hi)>0.005: flag+=f' RANGE label {rng} but dots {min(vs)} to {max(vs)}'
        close=[]
        for i in range(len(pts)):
            for j in range(i+1,len(pts)):
                d=math.hypot(pts[i][0]-pts[j][0],pts[i][1]-pts[j][1])
                if d<5.0: close.append((round(d,1),pts[i][4],pts[j][4]))
        ys=sorted(set(p[1] for p in pts))
        kinds=set(p[2] for p in pts)
        print(f'  {name[:38]:38s} {rng:18s} n={n} dots={len(pts)} y={ys} {kinds}{flag}' + (f'  close pairs (<5 px): {close}' if close else ''))
    xs=[float(a) for a in re.findall(r'class="mk \w+" cx="([\d.]+)"',body)]
    print('  dot x range',min(xs),max(xs),'; plot from the row lines:',set(re.findall(r'<line x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)" y2="[\d.]+" stroke="#e4e3df" stroke-opacity="0.6"/>',body)))
