import re, sys, json, statistics
def pct(vals, q):
    # numpy default 'linear' interpolation
    s = sorted(vals); n = len(s)
    if n == 1: return s[0]
    pos = (n-1)*q/100.0; lo = int(pos); hi = min(lo+1, n-1); f = pos-lo
    return s[lo] + (s[hi]-s[lo])*f
granite = {  # thresholds at run sha ac52a591 (09-17); 09-16 gpt-oss differs (filled below)
 ('llama-3.2-3b-instruct-fast-tp2',32):(190.54,169.29), ('llama-3.1-8b-instruct-good-tp2',8):(188.64,166.26),
 ('llama-3.3-70b-instruct-good-tp2',8):(27.47,24.25), ('llama-3.3-70b-instruct-good-tp2',4):(42.00,37.12),
 ('llama-3.3-70b-instruct-good-tp4',4):(45.97,40.72), ('mixtral-8x7b-instruct-v0.1-tp2',8):(76.83,76.03),
 ('qwen-2.5-32b-it-fast-tp2',8):(33.99,33.81), ('ingested-qwen-3-4b-instruct-2507-tp2',8):(178.75,168.84),
 ('ingested-qwen-3-4b-instruct-2507-tp4',8):(137.59,129.56), ('gemma-2-9b-it-fast-tp2',8):(97.87,95.90),
 ('ingested-gpt-oss-120b-tp4',8):(94.68,87.93), ('ingested-gemma-4-31b-it-tp2',8):(None,None)}
out = {}
for path in sys.argv[1:]:
    lines = open(path, errors='replace').read().splitlines()
    start = next(i for i,l in enumerate(lines) if '== Running performance tests ==' in l)
    end = next(i for i,l in enumerate(lines) if i > start and '== Running MMLU Pro ==' in l)
    perf = lines[start:end]
    idx = [i for i,l in enumerate(perf) if '== Benchmarking' in l] + [len(perf)]
    rows = []
    for k in range(len(idx)-1):
        seg = perf[idx[k]:idx[k+1]]
        m = next(re.search(r'Perf test for (\S+) completed', l) for l in seg if 'completed in' in l)
        cfg = m.group(1)
        tps=[]; ttft=[]
        for l in seg:
            mm = re.search(r'Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)', l)
            if mm: ttft.append(int(mm.group(1))); tps.append(float(mm.group(2)))
        users = len(tps)//10
        thr = granite.get((cfg,users),(None,None))
        mean = round(statistics.mean(tps),2); p05 = round(pct(tps,5),2)
        rows.append({'config':cfg,'users':users,'n':len(tps),'tps_mean':mean,'tps_p05':p05,'tps_min':min(tps),'tps_max':max(tps),
                     'ttft_mean_ms':round(statistics.mean(ttft),1),'ttft_p95_ms':round(pct(ttft,95),0),'ttft_min_ms':min(ttft),'ttft_max_ms':max(ttft),
                     'thr_avg':thr[0],'thr_p05':thr[1],
                     'avg_ok':(mean>=thr[0]) if thr[0] else None,'p05_ok':(p05>=thr[1]) if thr[1] else None,'tps_all':tps,'ttft_all':ttft})
    out[path]=rows
    print('=====',path)
    for r in rows:
        print(f"{r['config']:40s} u={r['users']:2d} n={r['n']:3d} mean={r['tps_mean']:7.2f} p05={r['tps_p05']:7.2f} min={r['tps_min']:7.2f} max={r['tps_max']:7.2f} | ttft mean={r['ttft_mean_ms']:7.1f} p95={r['ttft_p95_ms']:6.0f} | thr avg={r['thr_avg']} p05={r['thr_p05']} -> avg_ok={r['avg_ok']} p05_ok={r['p05_ok']}")
json.dump(out, open('perf_tps_lists.json','w'))
