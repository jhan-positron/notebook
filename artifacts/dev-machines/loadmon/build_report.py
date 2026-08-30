import json, html
from datetime import datetime, timezone, timedelta
PDT=timezone(timedelta(hours=-7))
d=json.load(open('summary.json'))
A=d['alpha']; S=d['sw-dev-01']
BLUE='#2a78d6'; ORANGE='#eb6834'; RED='#d03b3b'; INK='#0b0b0b'; INK2='#52514e'; MUTED='#898781'; GRID='#e1e0d9'; AXIS='#c3c2b7'; SURF='#fcfcfb'

# ---------- common x scale ----------
e0=min(A['series'][0]['e'],S['series'][0]['e']); e1=max(A['series'][-1]['e'],S['series'][-1]['e'])
W=960; ML=44; MR=110; PW=W-ML-MR
def X(e): return ML+(e-e0)/(e1-e0)*PW
def fmt_t(e): return datetime.fromtimestamp(e,PDT).strftime('%H:%M')
# hour ticks every 3h on PDT clock
ticks=[]
t=datetime.fromtimestamp(e0,PDT).replace(minute=0,second=0)
while t.timestamp()<=e1:
    if t.hour%3==0 and t.timestamp()>=e0: ticks.append(t)
    t+=timedelta(hours=1)
work0=datetime(2026,8,25,8,0,tzinfo=PDT).timestamp(); work1=datetime(2026,8,25,18,0,tzinfo=PDT).timestamp()
def xaxis(y):
    out=[f'<line x1="{ML}" x2="{ML+PW}" y1="{y}" y2="{y}" stroke="{AXIS}" stroke-width="1"/>']
    for tk in ticks:
        x=X(tk.timestamp()); lab=tk.strftime('%H:%M')
        if tk.hour==0: lab='Tue 00:00'
        out.append(f'<text x="{x:.1f}" y="{y+16}" font-size="11" fill="{MUTED}" text-anchor="middle">{lab}</text>')
    return ''.join(out)
def workband(y0,y1):
    return (f'<rect x="{X(work0):.1f}" y="{y0}" width="{X(work1)-X(work0):.1f}" height="{y1-y0}" fill="rgba(11,11,11,0.045)"/>'
            f'<text x="{(X(work0)+X(work1))/2:.1f}" y="{y0+13}" font-size="11" fill="{MUTED}" text-anchor="middle">work hours Tue 08:00–18:00 PDT</text>')
def path(series,key,Y,gap=400):
    segs=[];cur=[];prev=None
    for r in series:
        v=r[key]
        if v is None: continue
        if prev is not None and r['e']-prev>gap:
            segs.append(cur);cur=[]
        cur.append(f"{X(r['e']):.1f},{Y(v):.1f}"); prev=r['e']
    if cur: segs.append(cur)
    return ''.join(f'<path d="M{" L".join(s)}" fill="none" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' for s in segs if len(s)>1)
def gaps_rects(y0,y1):
    out=[]
    for i in range(1,len(A['series'])):
        p=A['series'][i-1]; r=A['series'][i]
        if r['e']-p['e']>400:
            x0=X(p['e']); x1=X(r['e']); mins=round((r['e']-p['e'])/60)
            out.append(f'<rect x="{x0:.1f}" y="{y0}" width="{x1-x0:.1f}" height="{y1-y0}" fill="{RED}" fill-opacity="0.10"/>')
            out.append(f'<line x1="{x0:.1f}" x2="{x0:.1f}" y1="{y0}" y2="{y1}" stroke="{RED}" stroke-width="1"/>')
            out.append(f'<line x1="{x1:.1f}" x2="{x1:.1f}" y1="{y0}" y2="{y1}" stroke="{RED}" stroke-width="1"/>')
            out.append((x0,x1,mins,fmt_t(p['e'])))
    return out

# ---------- Chart 1: idle cores over time ----------
H1=250; T1=28; B1=H1-34; PH=B1-T1
def Y1(v): return B1-(v/32)*PH
c1=[f'<svg viewBox="0 0 {W} {H1}" width="100%" role="img" aria-label="Idle CPU cores over 24 hours, alpha versus sw-dev-01" class="chart" data-chart="idle">']
c1.append(workband(T1,B1))
for v in (0,8,16,24,32):
    c1.append(f'<line x1="{ML}" x2="{ML+PW}" y1="{Y1(v):.1f}" y2="{Y1(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
    c1.append(f'<text x="{ML-8}" y="{Y1(v)+4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{v}</text>')
c1.append(f'<text x="{ML-8}" y="{T1-10}" font-size="11" fill="{MUTED}" text-anchor="end">cores</text>')
gr=gaps_rects(T1,B1)
for g in gr:
    if isinstance(g,str): c1.append(g)
for g in gr:
    if isinstance(g,tuple):
        x0,x1,mins,t0=g
        c1.append(f'<text x="{(x0+x1)/2:.1f}" y="{T1+28}" font-size="11" fill="{RED}" text-anchor="middle" font-weight="600">⚠ NFS stall {mins} min</text>')
# idle cores = ncpu*(1-busy/100)
for r in A['series']: r['idle']=None if r['busy'] is None else 32*(1-r['busy']/100)
for r in S['series']: r['idle']=None if r['busy'] is None else 16*(1-r['busy']/100)
c1.append(f'<g stroke="{BLUE}">{path(A["series"],"idle",Y1)}</g>')
c1.append(f'<g stroke="{ORANGE}">{path(S["series"],"idle",Y1)}</g>')
# end labels
la=A['series'][-1]; ls=S['series'][-1]
c1.append(f'<circle cx="{X(la["e"]):.1f}" cy="{Y1(la["idle"]):.1f}" r="4" fill="{BLUE}" stroke="{SURF}" stroke-width="2"/>')
c1.append(f'<circle cx="{X(ls["e"]):.1f}" cy="{Y1(ls["idle"]):.1f}" r="4" fill="{ORANGE}" stroke="{SURF}" stroke-width="2"/>')
c1.append(f'<text x="{ML+PW+10}" y="{Y1(la["idle"])+4:.1f}" font-size="12" fill="{INK}" font-weight="600">alpha <tspan fill="{INK2}" font-weight="400">32 cores</tspan></text>')
c1.append(f'<text x="{ML+PW+10}" y="{Y1(ls["idle"])+4:.1f}" font-size="12" fill="{INK}" font-weight="600">sw-dev-01 <tspan fill="{INK2}" font-weight="400">16 cores</tspan></text>')
# annotate lowest point of sw-dev-01
mn=min((r for r in S['series'] if r['idle'] is not None),key=lambda r:r['idle'])
c1.append(f'<circle cx="{X(mn["e"]):.1f}" cy="{Y1(mn["idle"]):.1f}" r="4" fill="{ORANGE}" stroke="{SURF}" stroke-width="2"/>')
c1.append(f'<text x="{X(mn["e"])+8:.1f}" y="{Y1(mn["idle"])+22:.1f}" font-size="11" fill="{INK2}">0 idle cores, {fmt_t(mn["e"])} (3 users building)</text>')
c1.append(xaxis(B1))
c1.append(f'<g class="hover"><line class="cross" x1="0" x2="0" y1="{T1}" y2="{B1}" stroke="{INK2}" stroke-width="1" visibility="hidden"/></g>')
c1.append('</svg>')
chart1=''.join(c1)

# ---------- Chart 2: CPU busy % small multiples ----------
LH=130; GAP=40; H2=LH*2+GAP+30
def lane(series,color,name,top,ncpu):
    B=top+LH-8; T=top+18; ph=B-T
    Y=lambda v:B-(v/100)*ph
    o=[workband(T,B)]
    for v in (0,50,100):
        o.append(f'<line x1="{ML}" x2="{ML+PW}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{ML-8}" y="{Y(v)+4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{v}%</text>')
    o.append(f'<line x1="{ML}" x2="{ML+PW}" y1="{Y(80):.1f}" y2="{Y(80):.1f}" stroke="{RED}" stroke-width="1" stroke-dasharray="4 4"/>')
    o.append(f'<text x="{ML+PW+6}" y="{Y(80)+4:.1f}" font-size="11" fill="{RED}">80% = saturated</text>')
    if name=='alpha':
        for g in gaps_rects(T,B):
            if isinstance(g,str): o.append(g)
    # area wash
    pts=[];prev=None;segs=[]
    for r in series:
        if r['busy'] is None: continue
        if prev is not None and r['e']-prev>400: segs.append(pts);pts=[]
        pts.append((X(r['e']),Y(r['busy']))); prev=r['e']
    segs.append(pts)
    for s in segs:
        if len(s)>1:
            o.append(f'<path d="M{s[0][0]:.1f},{B} L'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in s)+f' L{s[-1][0]:.1f},{B} Z" fill="{color}" fill-opacity="0.10"/>')
    o.append(f'<g stroke="{color}">{path(series,"busy",Y)}</g>')
    o.append(f'<text x="{ML}" y="{top+8}" font-size="12" fill="{INK}" font-weight="600">{name} <tspan fill="{INK2}" font-weight="400">· {ncpu} cores · CPU busy % (5-min average)</tspan></text>')
    return ''.join(o),Y,T,B
c2=[f'<svg viewBox="0 0 {W} {H2}" width="100%" role="img" aria-label="CPU busy percent over 24 hours, one lane per host" class="chart" data-chart="busy">']
la_,YA,TA,BA=lane(A['series'],BLUE,'alpha',0,32); c2.append(la_)
ls_,YS,TS,BS=lane(S['series'],ORANGE,'sw-dev-01',LH+GAP,16); c2.append(ls_)
# annotate sw-dev-01 episodes
eps=[('09:43','bcraig clang++',75.0,datetime(2026,8,25,9,50,tzinfo=PDT).timestamp()),
     ('10:33','airani + bcraig',89.3,datetime(2026,8,25,10,40,tzinfo=PDT).timestamp()),
     ('11:28','bcraig + wmiller + jzhang',100.0,datetime(2026,8,25,11,45,tzinfo=PDT).timestamp()),
     ('12:43','airani ingest',83.0,datetime(2026,8,25,12,50,tzinfo=PDT).timestamp()),
     ('16:53','jzhang',92.3,datetime(2026,8,25,17,0,tzinfo=PDT).timestamp())]
for i,(t0,who,mx,e) in enumerate(eps):
    x=X(e); y=YS(mx)-6
    anchor='middle'
    c2.append(f'<text x="{x:.1f}" y="{y-2 if i%2==0 else y-14:.1f}" font-size="10.5" fill="{INK2}" text-anchor="{anchor}">{html.escape(who)}</text>')
c2.append(f'<text x="{X(A["series"][100]["e"]) if False else ML+PW/2:.1f}" y="{YA(50)-4:.1f}" font-size="11" fill="{INK2}" text-anchor="middle">alpha never exceeded 33 % — the two red bands are stalls, not CPU load</text>')
c2.append(xaxis(BS))
c2.append(f'<g class="hover"><line class="cross" x1="0" x2="0" y1="{TA}" y2="{BS}" stroke="{INK2}" stroke-width="1" visibility="hidden"/></g>')
c2.append('</svg>')
chart2=''.join(c2)

# ---------- Chart 3: dumbbell off-hours -> work-hours ----------
def dumbbell(title,unit,rows,maxv,note):
    W3=960; ML3=130; MR3=40; PW3=W3-ML3-MR3; RH=54; H3=40+RH*len(rows)+30
    Xd=lambda v:ML3+v/maxv*PW3
    o=[f'<svg viewBox="0 0 {W3} {H3}" width="100%" role="img" aria-label="{html.escape(title)}" class="chart">']
    for v in range(0,maxv+1,10 if maxv<=50 else 20):
        o.append(f'<line x1="{Xd(v):.1f}" x2="{Xd(v):.1f}" y1="34" y2="{34+RH*len(rows)}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{Xd(v):.1f}" y="{34+RH*len(rows)+16}" font-size="11" fill="{MUTED}" text-anchor="middle">{v}{unit}</text>')
    for i,(name,color,off,work) in enumerate(rows):
        y=34+RH*i+RH/2
        o.append(f'<text x="{ML3-14}" y="{y+4}" font-size="13" fill="{INK}" font-weight="600" text-anchor="end">{name}</text>')
        o.append(f'<line x1="{Xd(off):.1f}" x2="{Xd(work):.1f}" y1="{y}" y2="{y}" stroke="{color}" stroke-width="2"/>')
        o.append(f'<circle cx="{Xd(off):.1f}" cy="{y}" r="6" fill="{SURF}" stroke="{color}" stroke-width="2"/>')
        o.append(f'<circle cx="{Xd(work):.1f}" cy="{y}" r="6" fill="{color}" stroke="{SURF}" stroke-width="2"/>')
        o.append(f'<text x="{Xd(off):.1f}" y="{y-12}" font-size="11" fill="{INK2}" text-anchor="middle">off-hours {off}{unit}</text>')
        o.append(f'<text x="{Xd(work):.1f}" y="{y+24}" font-size="11" fill="{INK}" text-anchor="middle" font-weight="600">work {work}{unit}</text>')
        if work-off>3:
            o.append(f'<text x="{(Xd(off)+Xd(work))/2:.1f}" y="{y-12}" font-size="11" fill="{INK2}" text-anchor="middle">{"+" if work>off else ""}{round(work-off,1)}{unit}</text>')
    o.append(f'<text x="{ML3}" y="18" font-size="12" fill="{INK}" font-weight="600">{html.escape(title)} <tspan fill="{INK2}" font-weight="400">{html.escape(note)}</tspan></text>')
    o.append('</svg>')
    return ''.join(o)
chart3a=dumbbell('CPU busy, mean','%',[('alpha',BLUE,A['off']['busy_mean'],A['work']['busy_mean']),('sw-dev-01',ORANGE,S['off']['busy_mean'],S['work']['busy_mean'])],100,'— hollow dot = off-hours, filled dot = work hours')
chart3b=dumbbell('CPU busy, 95th percentile','%',[('alpha',BLUE,A['off']['busy_p95'],A['work']['busy_p95']),('sw-dev-01',ORANGE,S['off']['busy_p95'],S['work']['busy_p95'])],100,'— the busiest 5 % of 5-minute windows')

# ---------- Chart 4: minutes bars ----------
def bars(rows,maxv,title,unit='min'):
    W4=960; ML4=250; MR4=90; PW4=W4-ML4-MR4; RH=26; GAPG=18
    n=sum(len(r[1]) for r in rows); H4=40+n*RH+(len(rows)-1)*GAPG+10
    Xb=lambda v:ML4+v/maxv*PW4
    o=[f'<svg viewBox="0 0 {W4} {H4}" width="100%" role="img" aria-label="{html.escape(title)}" class="chart">']
    o.append(f'<text x="{ML4}" y="18" font-size="12" fill="{INK}" font-weight="600">{html.escape(title)}</text>')
    y=34
    for label,items in rows:
        o.append(f'<text x="{ML4-14}" y="{y+RH*len(items)/2+4}" font-size="12.5" fill="{INK}" text-anchor="end">{html.escape(label)}</text>')
        for name,color,v in items:
            bw=max(0,Xb(v)-ML4)
            if v>0:
                o.append(f'<rect x="{ML4}" y="{y+4}" width="{bw:.1f}" height="{RH-8}" fill="{color}" rx="4" ry="4"/>')
                o.append(f'<rect x="{ML4}" y="{y+4}" width="{min(4,bw):.1f}" height="{RH-8}" fill="{color}"/>')
            o.append(f'<text x="{ML4+bw+8:.1f}" y="{y+RH/2+4}" font-size="12" fill="{INK}" font-weight="600">{v} {unit}</text>')
            o.append(f'<circle cx="{ML4-6}" cy="{y+RH/2}" r="3.5" fill="{color}"/>') if False else None
            y+=RH
        y+=GAPG
    o.append(f'<line x1="{ML4}" x2="{ML4}" y1="30" y2="{y-GAPG+2}" stroke="{AXIS}" stroke-width="1"/>')
    o.append('</svg>')
    return ''.join(o)
stall_min=round(sum(g for _,g in A['gaps'])/60)
chart4=bars([('CPU busy > 80 % (saturated)',[('alpha',BLUE,A['all']['min_over80']),('sw-dev-01',ORANGE,S['all']['min_over80'])]),
             ('CPU busy > 50 %',[('alpha',BLUE,A['all']['min_over50']),('sw-dev-01',ORANGE,S['all']['min_over50'])]),
             ('I/O stalled (NFS, sampler blocked)',[('alpha',BLUE,stall_min),('sw-dev-01',ORANGE,0)])],
            150,'Minutes in a bad state during the 24 h window')

# ---------- tables ----------
def trow(label,fa,fs,unit=''):
    return f'<tr><th scope="row">{label}</th><td>{fa}{unit}</td><td>{fs}{unit}</td></tr>'
def stat_table(key,title):
    a=A[key]; s=S[key]
    return f'''<table class="num"><caption>{title}</caption><thead><tr><th></th><th><span class="sw sw-a"></span>alpha (32 c)</th><th><span class="sw sw-s"></span>sw-dev-01 (16 c)</th></tr></thead><tbody>
{trow('samples (5-min)',a['n'],s['n'])}
{trow('CPU busy, mean',a['busy_mean'],s['busy_mean'],' %')}
{trow('CPU busy, median',a['busy_p50'],s['busy_p50'],' %')}
{trow('CPU busy, p90',a['busy_p90'],s['busy_p90'],' %')}
{trow('CPU busy, p95',a['busy_p95'],s['busy_p95'],' %')}
{trow('CPU busy, max',a['busy_max'],s['busy_max'],' %')}
{trow('idle cores, mean',a['idle_cores_mean'],s['idle_cores_mean'])}
{trow('idle cores, p90 (worst 10 % of time)',a['idle_cores_p90'],s['idle_cores_p90'])}
{trow('load1, mean',a['load1_mean'],s['load1_mean'])}
{trow('load1, p95',a['load1_p95'],s['load1_p95'])}
{trow('load1, max',a['load1_max'],s['load1_max'])}
{trow('memory used, mean / max',f"{a['mem_used_mean']} / {a['mem_used_max']}",f"{s['mem_used_mean']} / {s['mem_used_max']}",' GB')}
{trow('memory available, min',a['mem_avail_min'],s['mem_avail_min'],' GB')}
{trow('logged-in users, mean / max',f"{a['users_mean']} / {a['users_max']}",f"{s['users_mean']} / {s['users_max']}")}
</tbody></table>'''

events=f'''<table class="events"><caption>Events observed (PDT, Tue 2026-08-25)</caption>
<thead><tr><th>Host</th><th>Time</th><th>What the samples show</th><th>Who / what</th></tr></thead><tbody>
<tr><td><span class="sw sw-a"></span>alpha</td><td>09:57 → 10:23</td><td><b class="crit">I/O stall, 25 min.</b> load1 150 with CPU busy 6 % (processes blocked in I/O wait). Sampler blocked writing to NFS home; load15 still 92 at 10:23.</td><td>root <code>192.168.1.174-manager</code> (NFSv4 client state-manager kthread) was the top process</td></tr>
<tr><td><span class="sw sw-a"></span>alpha</td><td>11:28 → 12:17</td><td><b class="crit">I/O stall, 50 min.</b> Same signature; load15 reached 99. 13 samples lost in the two stalls.</td><td>same NFS kthread on top</td></tr>
<tr><td><span class="sw sw-s"></span>sw-dev-01</td><td>09:43 → 09:58</td><td>CPU 60–75 %, load1 15</td><td>bcraig <code>clang++</code></td></tr>
<tr><td><span class="sw sw-s"></span>sw-dev-01</td><td>10:33 → 10:48</td><td>CPU up to 89 %, load1 22</td><td>airani <code>clang++</code>, bcraig <code>trace_processor</code></td></tr>
<tr><td><span class="sw sw-s"></span>sw-dev-01</td><td>11:28 → 12:13</td><td><b class="crit">Saturated, 35 min at 98–100 %.</b> load1 43 (2.7× oversubscribed), memory used 41 → 90 GB</td><td>bcraig <code>clang++</code>/<code>ld</code>, wmiller <code>isim_system</code>, jzhang <code>python</code></td></tr>
<tr><td><span class="sw sw-s"></span>sw-dev-01</td><td>12:43 → 12:58</td><td>CPU 79–83 %, load1 28, memory used peaked at 122 GB of 168</td><td>airani <code>ingest</code>/<code>nix</code>/<code>python3.12</code>/<code>ld</code></td></tr>
<tr><td><span class="sw sw-s"></span>sw-dev-01</td><td>16:53 → 17:13</td><td>CPU 81–92 %, load1 25</td><td>jzhang <code>MainThread</code> (5–8 cores)</td></tr>
</tbody></table>'''

# ---------- JSON for hover ----------
hover=json.dumps({'e0':e0,'e1':e1,'ML':ML,'PW':PW,
  'alpha':[[r['e'],r['busy'],r['idle'],r['l1'],r['tu'],r['tc']] for r in A['series']],
  'sw':[[r['e'],r['busy'],r['idle'],r['l1'],r['tu'],r['tc']] for r in S['series']]})

page=f'''<title>alpha vs sw-dev-01</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{color-scheme:light;--page:#f6f6f2;--surf:{SURF};--ink:{INK};--ink2:{INK2};--muted:{MUTED};--grid:{GRID};--axis:{AXIS};--a:{BLUE};--s:{ORANGE};--crit:{RED};--border:rgba(11,11,11,0.10)}}
body{{background:var(--page);color:var(--ink);font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.5;margin:0;padding:32px 20px 64px}}
main{{max-width:1000px;margin:0 auto;display:grid;gap:28px}}
h1{{font-size:28px;font-weight:600;margin:0 0 6px;text-wrap:balance;letter-spacing:-0.01em}}
h2{{font-size:17px;font-weight:600;margin:0 0 10px}}
p{{margin:0 0 10px;max-width:72ch}}
.eyebrow{{font-size:12px;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink2);font-weight:500}}
.card{{background:var(--surf);border:1px solid var(--border);border-radius:6px;padding:20px 22px}}
.verdict{{border-left:4px solid var(--ink);}}
.verdict p{{max-width:80ch}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}}
.kpi{{background:var(--surf);border:1px solid var(--border);border-radius:6px;padding:14px 16px}}
.kpi .l{{font-size:12.5px;color:var(--ink2)}}
.kpi .v{{font-size:30px;font-weight:600;line-height:1.15;margin:4px 0 2px}}
.kpi .v small{{font-size:14px;font-weight:400;color:var(--ink2)}}
.kpi .d{{font-size:12.5px;color:var(--ink2)}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}}
.sw-a{{background:var(--a)}} .sw-s{{background:var(--s)}}
.chart{{display:block;overflow:visible}}
.chartwrap{{overflow-x:auto}}
.take{{font-size:13.5px;color:var(--ink2);margin-top:8px;max-width:90ch}}
.legend{{font-size:12.5px;color:var(--ink2);display:flex;gap:18px;flex-wrap:wrap;margin-bottom:6px}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}}
caption{{text-align:left;font-weight:600;font-size:14px;padding:0 0 8px;color:var(--ink)}}
th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid var(--grid);vertical-align:top}}
thead th{{color:var(--ink2);font-weight:500;font-size:12.5px}}
table.num td{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}}
table.num thead th:not(:first-child){{text-align:right}}
table.num th[scope=row]{{font-weight:400;color:var(--ink2)}}
code{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12.5px;background:rgba(11,11,11,0.05);padding:0 4px;border-radius:3px}}
.crit{{color:var(--crit)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media (max-width:820px){{.two{{grid-template-columns:1fr}}}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;margin:0;font-size:13.5px}}
dt{{font-weight:500}} dd{{margin:0;color:var(--ink2)}}
ul{{margin:0;padding-left:20px}} li{{margin-bottom:4px}}
#tip{{position:fixed;pointer-events:none;background:var(--surf);border:1px solid var(--border);border-radius:4px;padding:8px 10px;font-size:12.5px;box-shadow:0 2px 8px rgba(0,0,0,0.08);display:none;z-index:9;font-family:"IBM Plex Mono",ui-monospace,monospace;white-space:nowrap}}
</style>
<main>
<header>
<div class="eyebrow">Load comparison · 24 h · Mon 2026-08-24 18:11 → Tue 2026-08-25 18:08 PDT · 5-minute samples</div>
<h1>alpha vs sw-dev-01</h1>
<p>Question: is moving your development work from <b>alpha</b> (32 cores, 157 GB, Ubuntu 22.04) to <b>sw-dev-01</b> (16 cores, 168 GB, Ubuntu 24.04) worthwhile, judged by machine load?</p>
</header>

<section class="card verdict">
<h2>Answer: not on load alone</h2>
<p><b>sw-dev-01 is the busier machine.</b> During work hours it averaged <b>34 % CPU busy</b> against alpha's <b>8 %</b>, and it ran at 80–100 % (all 16 cores) for <b>85 minutes</b> spread over five build/simulation bursts from four different users. alpha never went above 33 % and had <b>29 idle cores on average</b>, versus <b>13</b> on sw-dev-01 (and only <b>2.6</b> in sw-dev-01's worst work-hour decile).</p>
<p><b>alpha's problem is not CPU, it is I/O.</b> It froze twice on NFS (09:57 and 11:28 PDT, 25 + 50 minutes) — load1 hit 150 while the CPUs were 94 % idle, and every process touching the home filesystem stalled, including the sampler. sw-dev-01 mounts the same filer but did not stall in this window (it did have an NFS livelock on 2026-08-18 per #hardware-systems, so the risk is shared, not alpha-specific).</p>
<p><b>Recommendation.</b> If your work is CPU-bound (builds, simulation), alpha gives you about 3× more spare cores during the day on average and 10× in the worst decile; stay. Move to sw-dev-01 only for reasons this data cannot show — Ubuntu 24.04 toolchain, podman, its status as the validated LSF submission host — and if so, expect contention around 09:45, 10:30, 11:30–12:15, 12:45 and 17:00 PDT when the other developers build. Off-hours, both machines are idle.</p>
</section>

<section class="kpis">
<div class="kpi"><div class="l">Work-hours CPU busy, mean</div><div class="v"><span class="sw sw-a"></span>8.4 % <small>vs</small> <span class="sw sw-s"></span>34.2 %</div><div class="d">Tue 08:00–18:00 PDT; sw-dev-01 4.1× busier</div></div>
<div class="kpi"><div class="l">Idle cores, work-hours mean</div><div class="v"><span class="sw sw-a"></span>29.3 <small>vs</small> <span class="sw sw-s"></span>10.5</div><div class="d">worst 10 % of the time: 26.9 vs 2.6</div></div>
<div class="kpi"><div class="l">Minutes at ≥ 80 % CPU</div><div class="v"><span class="sw sw-a"></span>0 <small>vs</small> <span class="sw sw-s"></span>85</div><div class="d">five saturation bursts on sw-dev-01</div></div>
<div class="kpi"><div class="l">Minutes stalled on NFS</div><div class="v"><span class="sw sw-a"></span>{stall_min} <small>vs</small> <span class="sw sw-s"></span>0</div><div class="d">two stalls on alpha; CPUs idle, processes blocked</div></div>
</section>

<section class="card">
<h2>Idle CPU cores over the 24 hours</h2>
<div class="legend"><span><span class="sw sw-a"></span>alpha (32 cores)</span><span><span class="sw sw-s"></span>sw-dev-01 (16 cores)</span><span><span class="sw" style="background:{RED};opacity:.35"></span>alpha NFS stall (no samples)</span><span><span class="sw" style="background:rgba(11,11,11,0.09)"></span>work hours</span></div>
<div class="chartwrap">{chart1}</div>
<p class="take">Idle cores = cores × (1 − CPU busy). Higher is more headroom for you. alpha stayed above 21 idle cores at every sample; sw-dev-01 dropped to 0 at 11:43 PDT and below 4 idle cores in 19 work-hour samples (95 min). Hover for values.</p>
</section>

<section class="card">
<h2>CPU busy %, one lane per host</h2>
<div class="chartwrap">{chart2}</div>
<p class="take">Same data as above, as a percentage of each machine's own cores, so 100 % means saturated regardless of core count. Labels on the sw-dev-01 lane name the users whose processes topped <code>ps</code> during each burst. The 16–20 % floor on sw-dev-01 all day is one long-running <code>jzhang MainThread</code> process (0.6–0.7 of a core) plus agent sessions.</p>
</section>

<section class="card">
<h2>Off-hours → work-hours</h2>
<div class="chartwrap">{chart3a}</div>
<div class="chartwrap">{chart3b}</div>
<p class="take">Off-hours: Mon 18:11–Tue 08:00 and Tue 18:00–18:08 PDT (168 samples each). Work hours: Tue 08:00–18:00 (107 alpha / 120 sw-dev-01 samples; alpha lost 13 to the stalls). Only the orange dots moved: sw-dev-01's work day is a different machine from its night; alpha barely changes.</p>
</section>

<section class="card">
<h2>Time in a bad state</h2>
<div class="chartwrap">{chart4}</div>
<p class="take">Each 5-minute sample above the threshold counts as 5 minutes. Stall minutes are the gaps between consecutive samples minus the normal 5-minute cadence (1511 s + 2970 s). The two failure modes are different: on sw-dev-01 your build slows down; on alpha every command that touches <code>/home</code> hangs.</p>
</section>

<section class="card">
{events}
</section>

<section class="two">
<div class="card">{stat_table('all','24-hour totals')}</div>
<div class="card">{stat_table('work','Work hours only (Tue 08:00–18:00 PDT)')}</div>
</section>

<section class="card">
<h2>Method and caveats</h2>
<ul>
<li><b>One weekday.</b> This is a single Tuesday. The build bursts on sw-dev-01 come from four people (bcraig, airani, wmiller, jzhang) whose schedules will vary; a second day would show whether 34 % / 85 saturated minutes is typical. The NFS stalls on alpha match a pattern Mitchell Stokes reported for agentsrv (2026-07-23) and sw-dev-01 (2026-08-18) in #hardware-systems, so they are recurring but not daily-predictable.</li>
<li><b>Sampler.</b> <code>sample.sh</code> ran on each host (not through SSH), every 300 s, writing to <code>~/workspace/random/loadmon/&lt;host&gt;.csv</code>. CPU busy = 1 − (idle + iowait) / total from the <code>/proc/stat</code> delta between samples, so it is a true 5-minute average; I/O wait counts as idle, which is why alpha's stalls show as low CPU busy. load1/5/15 from <code>/proc/loadavg</code>; memory from <code>free -g</code>; users = distinct names in <code>who</code>; top process = first row of <code>ps --sort=-pcpu</code>.</li>
<li><b>Top-process attribution is a snapshot</b>, not a share of CPU over the interval. In 13 sw-dev-01 samples the top process was the sampler's own <code>ps</code> (jhan) under heavy contention; those are excluded from the "who" column.</li>
<li><b>alpha was read from the host</b>, not from the claude-box container; the container's <code>/proc/loadavg</code> was checked to match the host before starting.</li>
<li><b>Not measured:</b> NFS latency or client statistics (<code>mountstats</code>), disk I/O, network, GPU/FPGA. Whether the 11:28 PDT coincidence (alpha stall start = sw-dev-01 saturation start) shares a cause needs the filer logs.</li>
</ul>
</section>

<section class="card">
<h2>Glossary</h2>
<dl>
<dt>CPU busy %</dt><dd>Share of all CPU time in the 5-minute window not spent idle or waiting for I/O. 100 % = every core fully used.</dd>
<dt>Idle cores</dt><dd>cores × (1 − CPU busy). The number of cores nobody was using, on average over the window.</dd>
<dt>load1 / load15</dt><dd>Linux load average over 1 / 15 minutes: the number of processes running or waiting (for CPU <i>or</i> uninterruptible I/O). A load far above the core count with low CPU busy means processes are blocked on I/O, not competing for CPU.</dd>
<dt>p90 / p95</dt><dd>The value that 90 % / 95 % of samples stay below — the "bad but not rare" level.</dd>
<dt>NFS stall / livelock</dt><dd>The network filesystem (home directories on <code>filer.positron.internal</code>) stops answering for minutes; every process that reads or writes it blocks. Seen here as a gap in the samples plus a huge load average with idle CPUs.</dd>
<dt>alpha</dt><dd>General Linux dev server, 32 cores, 157 GB RAM, Ubuntu 22.04; ~10 users logged in.</dd>
<dt>sw-dev-01</dt><dd>SW-team dev server set up May 2026, 16 cores, 168 GB RAM, Ubuntu 24.04, podman, validated LSF submission host; ~3 users logged in.</dd>
</dl>
</section>
</main>
<div id="tip"></div>
<script>
const D={hover};
const tip=document.getElementById('tip');
function fmt(e){{const d=new Date(e*1000);return d.toLocaleString('en-US',{{timeZone:'America/Los_Angeles',weekday:'short',hour:'2-digit',minute:'2-digit',hour12:false}})}}
function nearest(arr,e){{let best=null,bd=1e12;for(const r of arr){{const dd=Math.abs(r[0]-e);if(dd<bd){{bd=dd;best=r}}}}return bd<=600?best:null}}
document.querySelectorAll('svg[data-chart]').forEach(svg=>{{
  const kind=svg.dataset.chart; const cross=svg.querySelector('.cross');
  svg.addEventListener('mousemove',ev=>{{
    const pt=svg.createSVGPoint();pt.x=ev.clientX;pt.y=ev.clientY;const p=pt.matrixTransform(svg.getScreenCTM().inverse());
    if(p.x<D.ML||p.x>D.ML+D.PW){{cross.setAttribute('visibility','hidden');tip.style.display='none';return}}
    const e=D.e0+(p.x-D.ML)/D.PW*(D.e1-D.e0);
    cross.setAttribute('x1',p.x);cross.setAttribute('x2',p.x);cross.setAttribute('visibility','visible');
    const a=nearest(D.alpha,e),s=nearest(D.sw,e);
    const line=(name,r,col)=>r?`<div><span style="display:inline-block;width:9px;height:9px;background:${{col}};border-radius:2px;margin-right:6px"></span>${{name}}: ${{kind==='idle'?(r[2]==null?'—':r[2].toFixed(1)+' idle cores'):(r[1]==null?'—':r[1].toFixed(1)+' % busy')}} · load1 ${{r[3]}} · top ${{r[4]}} ${{r[5]}}</div>`:`<div><span style="display:inline-block;width:9px;height:9px;background:${{col}};border-radius:2px;margin-right:6px"></span>${{name}}: no sample (stalled)</div>`;
    tip.innerHTML=`<div style="color:{INK2};margin-bottom:4px">${{fmt(e)}} PDT</div>`+line('alpha',a,'{BLUE}')+line('sw-dev-01',s,'{ORANGE}');
    tip.style.display='block';
    const tw=tip.offsetWidth;let x=ev.clientX+14;if(x+tw>window.innerWidth-8)x=ev.clientX-tw-14;
    tip.style.left=x+'px';tip.style.top=(ev.clientY+14)+'px';
  }});
  svg.addEventListener('mouseleave',()=>{{cross.setAttribute('visibility','hidden');tip.style.display='none'}});
}});
</script>
'''
out='/tmp/claude-0/-home-jhan-workspace-random/9252de4a-118d-4f09-b740-8545c92a1732/scratchpad/alpha-vs-sw-dev-01.html'
open(out,'w').write(page); open('report.html','w').write(page)
print(out, len(page))
