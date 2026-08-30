import csv, json, statistics as st
from datetime import datetime, timezone, timedelta
PDT = timezone(timedelta(hours=-7))
def load(h):
    rows=[]
    with open(f"{h}.csv") as f:
        for r in csv.DictReader(f):
            if r['ts']=='ts': continue
            e=int(r['epoch']); t=datetime.fromtimestamp(e,PDT)
            rows.append(dict(t=t,e=e,ncpu=int(r['ncpu']),l1=float(r['load1']),l5=float(r['load5']),l15=float(r['load15']),
                busy=float(r['cpu_busy_pct']) if r['cpu_busy_pct'] else None,mu=int(r['mem_used_gb']),ma=int(r['mem_avail_gb']),
                users=int(r['users']),tu=r['top_user'],tp=float(r['top_pcpu']) if r['top_pcpu'] else 0,tc=r['top_cmd']))
    return rows
def pct(v,p):
    v=sorted(v); k=(len(v)-1)*p/100; f=int(k); c=min(f+1,len(v)-1); return v[f]+(v[c]-v[f])*(k-f)
def summarize(rows,label):
    b=[r['busy'] for r in rows if r['busy'] is not None]; l1=[r['l1'] for r in rows]; n=rows[0]['ncpu']
    return dict(label=label,n=len(rows),ncpu=n,busy_mean=round(st.mean(b),1),busy_p50=round(pct(b,50),1),busy_p90=round(pct(b,90),1),busy_p95=round(pct(b,95),1),busy_max=max(b),
        idle_cores_mean=round(n*(1-st.mean(b)/100),1),idle_cores_p90=round(n*(1-pct(b,90)/100),1),
        load1_mean=round(st.mean(l1),2),load1_p95=round(pct(l1,95),2),load1_max=max(l1),loadpercore_mean=round(st.mean(l1)/n,3),
        min_over50=sum(5 for x in b if x>50),min_over80=sum(5 for x in b if x>80),
        mem_used_mean=round(st.mean(r['mu'] for r in rows)),mem_used_max=max(r['mu'] for r in rows),mem_avail_min=min(r['ma'] for r in rows),
        users_mean=round(st.mean(r['users'] for r in rows),1),users_max=max(r['users'] for r in rows))
out={}
for h in ['alpha','sw-dev-01']:
    rows=load(h)
    work=[r for r in rows if 8<=r['t'].hour<18 and r['t'].weekday()<5]
    off=[r for r in rows if r not in work]
    gaps=[(rows[i]['t'].isoformat(),rows[i]['e']-rows[i-1]['e']) for i in range(1,len(rows)) if rows[i]['e']-rows[i-1]['e']>400]
    # stall signature: load1 > 2*ncpu and busy < 20
    stalls=[dict(t=r['t'].strftime('%H:%M'),l1=r['l1'],busy=r['busy'],top=f"{r['tu']} {r['tc']}") for r in rows if r['l1']>2*r['ncpu'] and (r['busy'] or 0)<20]
    # top users by count of being top process
    from collections import Counter
    tu=Counter(r['tu'] for r in rows); tuw=Counter(r['tu'] for r in work)
    out[h]=dict(all=summarize(rows,'24h'),work=summarize(work,'work 08-18 PDT'),off=summarize(off,'off-hours'),
        gaps=gaps,stalls=stalls,top_users=tu.most_common(6),top_users_work=tuw.most_common(6),
        series=[dict(t=r['t'].strftime('%Y-%m-%dT%H:%M'),e=r['e'],l1=r['l1'],busy=r['busy'],mu=r['mu'],users=r['users'],tu=r['tu'],tc=r['tc'],tp=r['tp']) for r in rows])
json.dump(out,open('summary.json','w'),default=str)
for h in out:
    print("=====",h)
    for k in ['all','work','off']:
        s=out[h][k]; print(f"{s['label']:16s} n={s['n']:3d} busy mean={s['busy_mean']:5.1f} p50={s['busy_p50']:5.1f} p90={s['busy_p90']:5.1f} p95={s['busy_p95']:5.1f} max={s['busy_max']:5.1f} | idle cores mean={s['idle_cores_mean']} p90={s['idle_cores_p90']} | load1 mean={s['load1_mean']} p95={s['load1_p95']} max={s['load1_max']} | min>50%={s['min_over50']} min>80%={s['min_over80']} | mem used mean={s['mem_used_mean']} max={s['mem_used_max']} avail min={s['mem_avail_min']} | users mean={s['users_mean']} max={s['users_max']}")
    print("gaps:",out[h]['gaps']); print("stalls:",out[h]['stalls']); print("top users:",out[h]['top_users']); print("top users work:",out[h]['top_users_work'])
