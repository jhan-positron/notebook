# check_fig1.py - Figure 1, all three layouts: dot x against the median in its tooltip, whisker ends against lowest/highest interval,
# value label text against the median, drop label against the pairs recomputed from the tooltip intervals, label placement on the row.
import re,html,statistics
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
t=open(P).read()
for cls in ('f1w','f1m','f1n'):
    svg=re.search(r'<svg class="%s".*?</svg>'%cls,t,re.S).group(0)
    # scale from tick labels: text '0' and '500' at top
    ticks={}
    for m in re.finditer(r'<text x="([\d.]+)" y="17\.0"[^>]*>(\d+)</text>',svg): ticks[int(m.group(2))]=float(m.group(1))
    x0=ticks[0]; k=(ticks[500]-ticks[0])/500
    print('==',cls,'x(0)=',x0,'px per GB/s',round(k,4),'ticks',sorted(ticks))
    items=re.findall(r'(<g(?: class="pt")?><title>.*?</title>.*?</g>)\s*(?:<text([^>]*)>([^<]*)</text>)?',svg,re.S)
    bad=0; rows={}
    seq=re.findall(r'<g(?: class="pt")?><title>(.*?)</title>(.*?)</g>|<text ([^>]*)>([^<]*)</text>',svg,re.S)
    last=None; cur=None
    for title,body,tattr,ttext in seq:
        if title:
            title=html.unescape(title)
            if 'drop of the load-only loop' in title:
                name=title.split(': drop of')[0]
                ln=re.search(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)"',body)
                lab=re.search(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]*)</text>',body)
                rows[name]=dict(line=(float(ln.group(1)),float(ln.group(3)),float(ln.group(2))),drop=lab.group(3),dropxy=(float(lab.group(1)),float(lab.group(2))),dots=[])
                cur=rows[name]; last=None
            else:
                name=title.split(': ')[0]
                # name may contain ': ' inside? use the known row
                med=float(re.search(r'Median ([\d.]+) GB/s',title).group(1))
                iv=[float(v) for v in re.search(r'Intervals: ([\d., ]+) GB/s',title).group(1).split(', ')]
                mk=re.search(r'<circle class="mk (ho|fi)" cx="([\d.]+)" cy="([\d.]+)"',body)
                wh=re.search(r'<path d="M([\d.]+) [\d.]+V[\d.]+M([\d.]+) ',body)
                cx=float(mk.group(2)); cy=float(mk.group(3))
                d=dict(med=med,iv=iv,cx=cx,cy=cy,kind=mk.group(1),wh=(float(wh.group(1)),float(wh.group(2))),old=('old read kernel' in title),label=None)
                cur['dots'].append(d); last=d
                if abs(x0+k*med-cx)>0.15: bad+=1; print('  DOT X',name,med,cx,round(x0+k*med,1))
                if abs(x0+k*min(iv)-d['wh'][0])>0.15 or abs(x0+k*max(iv)-d['wh'][1])>0.15: bad+=1; print('  WHISKER',name,iv,d['wh'],round(x0+k*min(iv),1),round(x0+k*max(iv),1))
        elif last is not None and re.fullmatch(r'\d+\.\d\d',ttext or ''):
            last['label']=ttext; a=dict(re.findall(r'([\w-]+)="([^"]*)"',tattr)); last['lxy']=(float(a['x']),float(a['y']),a['text-anchor'])
            if abs(float(ttext)-last['med'])>0.005: bad+=1; print('  VALUE LABEL',ttext,last['med'])
            if abs(float(a['y'])-last['cy']-4.2)>0.6: bad+=1; print('  LABEL NOT ON ROW',ttext,a['y'],last['cy'])
            last=None
    n=0
    for name,r in rows.items():
        n+=1
        if len(r['dots'])!=2: bad+=1; print('  ROW WITHOUT 2 DOTS',name,len(r['dots'])); continue
        o=[d for d in r['dots'] if d['old']][0]; nw=[d for d in r['dots'] if not d['old']][0]
        if any(d['label'] is None for d in r['dots']): bad+=1; print('  DOT WITHOUT VALUE LABEL',name)
        if 'round' in name and ('Part A' in name or name.startswith('A-')):
            dr=[100*(1-nw['med']/o['med'])]
        else:
            dr=[100*(1-b/a) for a,b in zip(o['iv'],nw['iv'])]
        lo,hi='%.1f'%min(dr),'%.1f'%max(dr)
        exp=(lo+' %') if lo==hi else (lo+' % to '+hi+' %')
        if exp!=r['drop']: print('  DROP LABEL differs (recomputed from the 2-decimal tooltip values):',name,'page',r['drop'],'recomputed',exp,[round(x,3) for x in dr])
        # drop label is centred on the line and sits above it
        mid=(r['line'][0]+r['line'][1])/2
        if abs(mid-r['dropxy'][0])>0.2 or not (5<r['line'][2]-r['dropxy'][1]<9): bad+=1; print('  DROP LABEL POSITION',name,r['line'],r['dropxy'])
        if abs(r['line'][0]-nw['cx'])>0.15 or abs(r['line'][1]-o['cx'])>0.15 or abs(r['line'][2]-o['cy'])>0.05: bad+=1; print('  LINE ENDS',name)
        if not nw['cx']<o['cx']: print('  orange not left of blue',name)
    print('   rows',n,'problems',bad)
