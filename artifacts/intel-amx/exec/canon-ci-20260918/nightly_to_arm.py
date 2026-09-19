#!/usr/bin/env python3
"""Turn a nightly System CI run log (gh run view <id> --log, ANSI stripped or not) into the same
"arm record" shape that st_ci_perf.py writes, so gen_report.py treats the nightly and our arms alike.

usage: nightly_to_arm.py <run.log> <out.json> [--date YYYY-MM-DD] [--label text]

Per config the log carries one Rich "Done (TTFT=<ms>, <tps> / <goal> TPS)" row per user per round
(rendered in user order) and one "Running averages: TTFT=, TPS=" line per round, then
"Perf test for <model> completed in <min>mins". The per-round grouping below uses the Running
averages lines as round separators (verified on the 2026-09-16/17 logs by the research workflow).
"""
import json
import re
import statistics
import sys
from datetime import datetime

ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')


def ts(line):
    m = re.search(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)', line)
    return datetime.strptime(m.group(1), '%Y-%m-%dT%H:%M:%S') if m else None


def main():
    path, out = sys.argv[1], sys.argv[2]
    date = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else None
    label = sys.argv[sys.argv.index('--label') + 1] if '--label' in sys.argv else 'nightly'
    lines = [ANSI.sub('', l) for l in open(path, errors='replace').read().splitlines()]
    deb = next((re.search(r'Setting up tron \(([^)]+)\)', l).group(1) for l in lines if 'Setting up tron (' in l), None)
    si = next(i for i, l in enumerate(lines) if '== Running performance tests ==' in l)
    ei = next((i for i, l in enumerate(lines) if i > si and re.search(r'== Running (MMLU Pro|soak)', l)), len(lines))
    perf = lines[si:ei]
    idx = [i for i, l in enumerate(perf) if '== Benchmarking' in l] + [len(perf)]
    results, raw = [], []
    for k in range(len(idx) - 1):
        seg = perf[idx[k]:idx[k + 1]]
        comp = next((l for l in seg if 'Perf test for' in l and 'completed in' in l), None)
        if not comp:
            continue
        m = re.search(r'Perf test for (\S+) completed in ([\d.]+)mins', comp)
        model = m.group(1)
        tps, ttft, rounds, cur_t, cur_f = [], [], [], [], []
        for l in seg:
            mm = re.search(r'Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)', l)
            if mm:
                cur_f.append(int(mm.group(1))); cur_t.append(float(mm.group(2)))
            if 'Running averages' in l:
                rounds.append({'tps': cur_t, 'ttft_ms': cur_f}); tps += cur_t; ttft += cur_f; cur_t, cur_f = [], []
        if cur_t:
            rounds.append({'tps': cur_t, 'ttft_ms': cur_f}); tps += cur_t; ttft += cur_f
        users = max((len(r['tps']) for r in rounds), default=0)
        prov = next((l for l in seg if 'Provisioning models via legacy posadm path' in l), None)
        caddy = next((l for l in seg if 'Caddy upstreams are healthy' in l), None)
        eng = next((int(re.search(r'All (\d+) inference engines', l).group(1)) for l in seg if 'inference engines are running' in l), None)
        s = sorted(tps)
        p05 = None
        if s:
            pos = (len(s) - 1) * 0.05; lo = int(pos); hi = min(lo + 1, len(s) - 1); p05 = s[lo] + (s[hi] - s[lo]) * (pos - lo)
        results.append({
            'use_case': f'{model} @ {users} users {{}}',
            'tps_mean': statistics.mean(tps) if tps else 0, 'tps_std_dev': statistics.pstdev(tps) if tps else 0,
            'p05_tps': p05, 'min_tps': min(tps) if tps else 0, 'ttft_mean': round(statistics.mean(ttft)) if ttft else 0,
            'prefill_mean': None, 'prompt_tokens': None, 'cache_hit_pct': None,
            'context': {'model': model, 'nominal_users': users, 'prompt_length': 200 if 'llama-3.2-3b' in model else 1024},
            'tps_results': tps, 'minutes': float(m.group(2)),
            'engines': eng, 'provision_seconds': (ts(caddy) - ts(prov)).total_seconds() if prov and caddy else None,
            'started': str(ts(seg[0])), 'completed': str(ts(comp)),
        })
        raw.append({'model': model, 'n_users': users, 'n_rounds': len(rounds), 'ttfts_ms': [float(x) for x in ttft],
                    'tpss': tps, 'rounds': rounds})
    rec = {'arm': label, 'source': path, 'date': date, 'tron_version': deb,
           'perf_phase_start': str(ts(perf[0])), 'perf_phase_end': str(ts(lines[ei - 1])) if ei < len(lines) else None,
           'results': results, 'raw': raw}
    json.dump(rec, open(out, 'w'), indent=1)
    print(f'{label}: {len(results)} configs, deb {deb}, perf phase {rec["perf_phase_start"]} -> {rec["perf_phase_end"]}')
    for r in results:
        print(f'  {r["context"]["model"]:42s} @{r["context"]["nominal_users"]:3d}u  TPS {r["tps_mean"]:7.2f} min {r["min_tps"]:7.2f}  TTFT {r["ttft_mean"]:5d} ms  n={len(r["tps_results"])}')


if __name__ == '__main__':
    main()
