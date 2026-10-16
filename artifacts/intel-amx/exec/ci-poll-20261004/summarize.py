import csv, statistics as st, json, collections
rows=[r for r in csv.DictReader(open('rows.csv')) if r['usable']=='True']
for r in rows:
    for k in ('tps_mean','prefill_tps','ttft_mean_ms','tps_sd','tps_p05'):
        r[k]=float(r[k]) if r[k] not in ('','None') else None
PRE=lambda d: d<='2026-09-22'
by=collections.defaultdict(dict)
for r in rows: by[(r['machine'],r['model'],r['users'])][r['date']]=r
out=[]
def med(x): return st.median(x) if x else None
def cv(x): return 100*st.pstdev(x)/st.mean(x) if len(x)>1 else None
for (m,model,users),d in sorted(by.items()):
    pre=[d[k] for k in sorted(d) if PRE(k)]; post=[d[k] for k in sorted(d) if not PRE(k)]
    pt=[r['tps_mean'] for r in pre]; qt=[r['tps_mean'] for r in post]
    pp=[r['prefill_tps'] for r in pre]; qp=[r['prefill_tps'] for r in post]
    rec={'machine':m,'model':model,'users':users,'n_pre':len(pre),'n_post':len(post),
         'pre_dates':[r['date'][5:] for r in pre],'post_dates':[r['date'][5:] for r in post],
         'tps_pre':[round(x,2) for x in pt],'tps_post':[round(x,2) for x in qt],
         'prefill_pre':[round(x,1) for x in pp],'prefill_post':[round(x,1) for x in qp],
         'tps_pre_med':med(pt),'tps_post_med':med(qt),'tps_pre_cv':cv(pt),'tps_post_cv':cv(qt),
         'prefill_pre_med':med(pp),'prefill_post_med':med(qp),
         'tps_pre_min':min(pt) if pt else None,'tps_pre_max':max(pt) if pt else None,
         'tps_post_min':min(qt) if qt else None,'tps_post_max':max(qt) if qt else None}
    if pt and qt:
        rec['tps_delta_pct']=100*(rec['tps_post_med']/rec['tps_pre_med']-1)
        rec['prefill_delta_pct']=100*(rec['prefill_post_med']/rec['prefill_pre_med']-1)
        # separation: do post values all exceed pre max?
        rec['post_all_above_pre_max']=all(x>max(pt) for x in qt)
        rec['first_post_vs_pre_max_pct']=100*(qt[0]/max(pt)-1)
    out.append(rec)
json.dump(out,open('summary.json','w'),indent=1)
print(f"{'machine':6} {'model':40} {'u':>3} {'nPre':>4} {'nPost':>5} {'preMed':>8} {'postMed':>8} {'dTPS%':>7} {'preCV%':>6} {'postCV%':>7} {'allAbove':>8} | {'prefPre':>8} {'prefPost':>8} {'dPref%':>7}")
for r in out:
    if 'tps_delta_pct' not in r: print(r['machine'],r['model'],r['users'],'pre',r['n_pre'],'post',r['n_post']); continue
    print(f"{r['machine']:6} {r['model']:40} {r['users']:>3} {r['n_pre']:>4} {r['n_post']:>5} {r['tps_pre_med']:8.2f} {r['tps_post_med']:8.2f} {r['tps_delta_pct']:+7.1f} {r['tps_pre_cv']:6.2f} {r['tps_post_cv']:7.2f} {str(r['post_all_above_pre_max']):>8} | {r['prefill_pre_med']:8.1f} {r['prefill_post_med']:8.1f} {r['prefill_delta_pct']:+7.1f}")
