import re, json, statistics
from datetime import datetime
def ts(l):
    m = re.match(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)', l); return datetime.strptime(m.group(1), '%Y-%m-%dT%H:%M:%S') if m else None
def pct(vals,q):
    s=sorted(vals); n=len(s); pos=(n-1)*q/100; lo=int(pos); hi=min(lo+1,n-1); return s[lo]+(s[hi]-s[lo])*(pos-lo)
runs = {'35178969541': ('2026-09-17','2026.09.17-31b80a18','ac52a591f026015fecee7a816e3a736045827498'),
        '35052594106': ('2026-09-16','2026.09.16-f46e48ba','6b20db065a1907b25ab3adad7f4e5425d7c1e7fc')}
out = {}
for rid,(day,deb,sha) in runs.items():
    lines = open(f'nightly-{rid}.clean.log', errors='replace').read().splitlines()
    def first(pat, after=0):
        return next((l for i,l in enumerate(lines) if i>=after and re.search(pat,l)), None)
    t_apt_install = ts(first(r'Setting up tron \('))
    t_func_start = ts(first(r'== Running functional tests =='))
    t_perf_start = ts(first(r'== Running performance tests =='))
    t_perf_end = ts(first(r'== Performance tests completed in'))
    t_mmlu_start = ts(first(r'== Running MMLU Pro ==')); t_mmlu_end = ts(first(r'== MMLU Pro completed in'))
    t_soak_start = ts(first(r'== Running soak')); t_soak_end = ts(first(r'Soak exiting: Max duration'))
    t_last = ts(lines[-1]) or ts([l for l in lines if ts(l)][-1])
    si = lines.index(first(r'== Running performance tests ==')); ei = lines.index(first(r'== Running MMLU Pro =='))
    perf = lines[si:ei]
    idx = [i for i,l in enumerate(perf) if '== Benchmarking' in l] + [len(perf)]
    cfgs=[]
    for k in range(len(idx)-1):
        seg = perf[idx[k]:idx[k+1]]
        comp = next(l for l in seg if 'completed in' in l); m = re.search(r'Perf test for (\S+) completed in ([\d.]+)mins', comp)
        prov = next((l for l in seg if 'Provisioning models via legacy posadm path' in l), None)
        caddy = next((l for l in seg if 'Caddy upstreams are healthy' in l), None)
        eng = re.search(r'All (\d+) inference engines', next(l for l in seg if 'inference engines are running' in l)).group(1)
        round1 = next((l for l in seg if 'Running round (1/10)' in l), None)
        tps=[];ttft=[]
        for l in seg:
            mm = re.search(r'Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)', l)
            if mm: ttft.append(int(mm.group(1))); tps.append(float(mm.group(2)))
        users=len(tps)//10
        avg_lines=[l for l in seg if 'Running averages' in l]
        per_round=[]
        ai=[i for i,l in enumerate(seg) if 'Running averages' in l]
        prev=0
        for i in ai:
            blk=seg[prev:i+1]; prev=i+1
            v=[float(re.search(r', ([\d.]+) / ',l).group(1)) for l in blk if 'Done (TTFT=' in l]
            per_round.append({'n':len(v),'mean':round(statistics.mean(v),2),'min':min(v),'max':max(v)} if v else None)
        cfgs.append({'order':k+1,'config':m.group(1),'users':users,'engines':int(eng),
            't_bench_start':str(ts(seg[0])),'t_provision_cmd':str(ts(prov)) if prov else None,'t_caddy_healthy':str(ts(caddy)) if caddy else None,
            'provision_secs':(ts(caddy)-ts(prov)).total_seconds() if prov and caddy else None,
            't_round1':str(ts(round1)) if round1 else None,'t_completed':str(ts(comp)),
            'completed_mins_harness':float(m.group(2)),'wall_mins_incl_provision':round((ts(comp)-ts(seg[0])).total_seconds()/60,2),
            'n_samples':len(tps),'tps_mean':round(statistics.mean(tps),2),'tps_p05':round(pct(tps,5),2),'tps_min_slowest_user':min(tps),'tps_max':max(tps),'tps_median':round(statistics.median(tps),2),
            'ttft_mean_ms':round(statistics.mean(ttft),1),'ttft_p95_ms':round(pct(ttft,95),0),'ttft_min_ms':min(ttft),'ttft_max_ms':max(ttft),
            'final_running_avg_line':re.sub(r'.*\] ','',avg_lines[-1]),'per_round_tps':per_round})
    out[rid]={'date':day,'run_id':rid,'systems_test_sha':sha,'tron_deb':deb,
      't_apt_setting_up_tron':str(t_apt_install),'t_functional_start':str(t_func_start),'t_perf_start':str(t_perf_start),'t_perf_end':str(t_perf_end),
      'perf_phase_mins':round((t_perf_end-t_perf_start).total_seconds()/60,2),'t_mmlu_start':str(t_mmlu_start),'t_mmlu_end':str(t_mmlu_end),
      't_soak_start':str(t_soak_start),'t_soak_end':str(t_soak_end),'t_log_last_line':str(t_last),'configs':cfgs}
json.dump(out, open('nightly-reference-final.json','w'), indent=1)
for rid,d in out.items():
    print('=====',rid,d['date'],d['tron_deb'],'apt',d['t_apt_setting_up_tron'],'func',d['t_functional_start'],'perf',d['t_perf_start'],'->',d['t_perf_end'],d['perf_phase_mins'],'min; mmlu',d['t_mmlu_start'],'->',d['t_mmlu_end'],'; soak',d['t_soak_start'],'->',d['t_soak_end'],'; last',d['t_log_last_line'])
    for c in d['configs']:
        print(f"{c['order']:2d} {c['config']:38s} u={c['users']:2d} eng={c['engines']} prov={c['provision_secs']} s | bench {c['t_bench_start'][11:]}->{c['t_completed'][11:]} harness={c['completed_mins_harness']} wall={c['wall_mins_incl_provision']} | TPS mean={c['tps_mean']} p05={c['tps_p05']} min={c['tps_min_slowest_user']} max={c['tps_max']} | TTFT mean={c['ttft_mean_ms']} p95={c['ttft_p95_ms']} | rounds mean: {[r['mean'] for r in c['per_round_tps']]}")
