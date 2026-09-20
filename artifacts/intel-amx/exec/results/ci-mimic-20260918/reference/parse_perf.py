import re, sys, json, statistics
from datetime import datetime
def ts(line):
    m = re.match(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)', line)
    return datetime.strptime(m.group(1), '%Y-%m-%dT%H:%M:%S') if m else None
out = {}
for path in sys.argv[1:]:
    lines = open(path, errors='replace').read().splitlines()
    # perf phase bounds
    start = next(i for i,l in enumerate(lines) if '== Running performance tests ==' in l)
    end = next((i for i,l in enumerate(lines) if i > start and re.search(r'_run_test_phases:\d+\] == Running', l)), len(lines))
    perf = lines[start:end]
    phase_end_line = None
    # split by Benchmarking markers
    idx = [i for i,l in enumerate(perf) if '== Benchmarking' in l]
    idx.append(len(perf))
    configs = []
    for k in range(len(idx)-1):
        seg = perf[idx[k]:idx[k+1]]
        name = re.search(r'== Benchmarking (\S+) ==', seg[0]).group(1)
        t0 = ts(seg[0])
        done = [l for l in seg if re.search(r'\bDone \(TTFT=', l)]
        tps, ttft, goal = [], [], set()
        for l in done:
            m = re.search(r'Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)', l)
            if m:
                ttft.append(int(m.group(1))); tps.append(float(m.group(2))); goal.add(m.group(3))
        comp = [l for l in seg if 'Perf test for' in l and 'completed in' in l]
        avg = [l for l in seg if 'Running averages' in l]
        m = re.search(r'Perf test for (\S+) completed in ([\d.]+)mins', comp[-1]) if comp else None
        ma = re.search(r'TTFT=(\d+), TPS=([\d.]+)', avg[-1]) if avg else None
        # two-group split: sort tps, find largest gap
        groups = None
        if len(tps) >= 4:
            s = sorted(tps)
            gaps = [(s[i+1]-s[i], i) for i in range(len(s)-1)]
            g, i = max(gaps)
            lo, hi = s[:i+1], s[i+1:]
            groups = {'gap': round(g,2), 'low_n': len(lo), 'low_mean': round(statistics.mean(lo),2), 'low_max': lo[-1], 'high_n': len(hi), 'high_mean': round(statistics.mean(hi),2), 'high_min': hi[0]}
        # per-iteration Done counts (users per iteration)
        # iterations = number of Running averages lines
        provision = [l for l in seg if 'Provisioning models via legacy posadm path' in l]
        engines = [re.search(r'All (\d+) inference engines are running', l).group(1) for l in seg if 'inference engines are running' in l]
        caddy = [re.search(r'All (\d+) Caddy upstreams are healthy', l).group(1) for l in seg if 'Caddy upstreams are healthy' in l]
        configs.append({
            'order': k+1, 'bench_label': name, 'config': m.group(1) if m else None,
            'start': str(t0), 'end': str(ts(comp[-1])) if comp else None,
            'completed_mins': float(m.group(2)) if m else None,
            'wall_mins_start_to_completed': round((ts(comp[-1])-t0).total_seconds()/60,2) if comp else None,
            'final_avg_TTFT_ms': int(ma.group(1)) if ma else None, 'final_avg_TPS': float(ma.group(2)) if ma else None,
            'n_running_avg_lines': len(avg),
            'done_n': len(done), 'done_per_iter': (len(done)/len(avg)) if avg else None,
            'tps_min': min(tps) if tps else None, 'tps_max': max(tps) if tps else None, 'tps_mean': round(statistics.mean(tps),2) if tps else None, 'tps_median': round(statistics.median(tps),2) if tps else None,
            'ttft_min': min(ttft) if ttft else None, 'ttft_max': max(ttft) if ttft else None, 'ttft_mean': round(statistics.mean(ttft),1) if ttft else None,
            'goal_tps': sorted(goal), 'two_group_split': groups,
            'provision_lines': [re.sub(r'.*path: ', '', l) for l in provision], 'engines_running': engines, 'caddy_healthy': caddy,
        })
    phase_start = ts(perf[0]); last_comp = max(ts(l) for l in perf if 'completed in' in l)
    out[path] = {'perf_phase_start': str(phase_start), 'perf_phase_last_completed': str(last_comp), 'perf_phase_total_mins': round((last_comp-phase_start).total_seconds()/60,2), 'next_phase_marker': lines[end] if end < len(lines) else None, 'configs': configs}
json.dump(out, open('perf_parsed.json','w'), indent=1)
for p, d in out.items():
    print('=====', p, 'phase', d['perf_phase_start'], '->', d['perf_phase_last_completed'], d['perf_phase_total_mins'], 'min; next phase:', (d['next_phase_marker'] or '')[:160])
    for c in d['configs']:
        print(json.dumps({k:v for k,v in c.items() if k not in ('provision_lines',)}))
