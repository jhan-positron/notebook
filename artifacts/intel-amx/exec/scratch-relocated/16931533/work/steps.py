import json,statistics as st
S=json.load(open('summary.json'))
pk=json.load(open('packages.json'))
runs=json.load(open('runs.json'))
pkg_by={(r['machine'],r['date']):r['package'] for r in runs if r['date']}
out=[]
for s in S:
    dates=s['pre_dates']+s['post_dates']
    for metric in ('tps','prefill'):
        vals=s[metric+'_pre']+s[metric+'_post']
        # a step at night i: median of next 3 nights vs median of previous 3 nights, and the night itself outside prev range
        for i in range(3,len(vals)-1):
            prev=vals[i-3:i]; nxt=vals[i:i+3]
            if min(prev)<=0: continue
            d=100*(st.median(nxt)/st.median(prev)-1)
            lo,hi=min(prev),max(prev)
            outside=all(v>hi for v in nxt) or all(v<lo for v in nxt)
            if abs(d)>=1.0 and outside:
                out.append({'machine':s['machine'],'model':s['model'],'users':s['users'],'metric':metric,'night':'2026-'+dates[i],
                            'package':pkg_by.get((s['machine'],'2026-'+dates[i])),'prev3':prev,'next3':nxt,'delta_pct':round(d,1)})
json.dump(out,open('steps.json','w'),indent=1)
for o in sorted(out,key=lambda o:(o['machine'],o['night'],o['model'])):
    print(f"{o['machine']:5} {o['night']} {o['package'] or '':22} {o['model']:40} {o['users']:>2} {o['metric']:7} {o['delta_pct']:+6.1f}%  prev {o['prev3']} -> next {o['next3']}")
