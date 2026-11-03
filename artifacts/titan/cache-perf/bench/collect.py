#!/usr/bin/env python3
"""collect.py - merge CRB result directories into one JSON for the report.

usage: collect.py MAIN_DIR [FOLLOWUP_DIR] [UNCORE_DIR] > data.json
"""
import csv, glob, json, os, re, sys

def parse_bytes(s):
    m = re.fullmatch(r'([0-9.]+)([KMG]?)', s)
    v = float(m.group(1)); mul = {'': 1, 'K': 1 << 10, 'M': 1 << 20, 'G': 1 << 30}[m.group(2)]
    return int(v * mul)

def latency_rows(path):
    """rows: size_bytes, rep (int, 'freshN' or 'best'), loads, ns; plus AnonHugePages per size"""
    rows, huge = [], {}
    for line in open(path):
        line = line.strip()
        m = re.match(r'# size_bytes=(\d+) AnonHugePages_kB=(-?\d+)', line)
        if m:
            huge[int(m.group(1))] = int(m.group(2)); continue
        if not line or line.startswith('#') or line.startswith('size_bytes'):
            continue
        s, rep, loads, ns = line.split(',')
        rows.append({'size': int(s), 'rep': rep, 'loads': int(loads), 'ns': float(ns)})
    return rows, huge

def best_by_size(rows, key=lambda r: r['rep'] == 'best'):
    out = {}
    for r in rows:
        if key(r):
            out[r['size']] = r['ns']
    return out

def bandwidth_rows(path):
    """rows from bandwidth.c CSV, keeping the '-- ...' context lines as 'ctx'"""
    rows, ctx = [], ''
    for line in open(path):
        line = line.strip()
        if line.startswith('--'):
            ctx = line[2:].strip(); continue
        if not line or line.startswith('#') or line.startswith('kernel,'):
            continue
        f = line.split(',')
        if f[3] != 'best':
            continue
        rows.append({'ctx': ctx, 'kernel': f[0], 'threads': int(f[1]), 'bytes': int(f[2]), 'gbps': float(f[6])})
    return rows

def perf_counts(path):
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path):
        f = line.strip().split(',')
        if len(f) < 3 or line.startswith('#'):
            continue
        try:
            out[f[2].split(':')[0]] = float(f[0])
        except ValueError:
            out[f[2].split(':')[0]] = None
    return out

def refills_per_load(d, sizes_csv, prefix):
    """(long - short) / (loads_long - loads_short), per event, per size"""
    res = {}
    short, _ = latency_rows(os.path.join(d, f'{prefix}-short.csv')) if os.path.exists(os.path.join(d, f'{prefix}-short.csv')) else ([], {})
    long_, _ = latency_rows(os.path.join(d, f'{prefix}-long.csv')) if os.path.exists(os.path.join(d, f'{prefix}-long.csv')) else ([], {})
    ls = {r['size']: r['loads'] for r in short if r['rep'] == 'best'}
    ll = {r['size']: r['loads'] for r in long_ if r['rep'] == 'best'}
    for tok in sizes_csv.split(','):
        size = parse_bytes(tok)
        cs = perf_counts(os.path.join(d, f'{sizes_csv_prefix(prefix)}-{tok}-short.csv'))
        cl = perf_counts(os.path.join(d, f'{sizes_csv_prefix(prefix)}-{tok}-long.csv'))
        if size in ls and size in ll and cs and cl and ll[size] > ls[size]:
            per = {}
            for ev in cl:
                if cl.get(ev) is not None and cs.get(ev) is not None:
                    per[ev] = (cl[ev] - cs[ev]) / (ll[size] - ls[size])
            res[size] = per
    return res

def sizes_csv_prefix(prefix):
    return {'latency-perfrun': 'latency-perf', 'chase': 'cmn'}[prefix]

LAT_SIZES = '4K,8K,16K,32K,48K,64K,96K,128K,256K,512K,1M,1.5M,2M,3M,4M,8M,16M,32M,64M,96M,128M,192M,256M,512M,1G,2G'
UNCORE_SIZES = '1M,8M,16M,32M,48M,64M,96M,128M,192M,256M,512M,1G'

def main():
    main_dir = sys.argv[1]
    fu = sys.argv[2] if len(sys.argv) > 2 else None
    un = sys.argv[3] if len(sys.argv) > 3 else None
    out = {'main_dir': main_dir, 'followup_dir': fu, 'uncore_dir': un}
    rows, huge = latency_rows(os.path.join(main_dir, 'latency.csv'))
    out['latency_repeated'] = best_by_size(rows)
    out['latency_repeated_reps'] = [r for r in rows if r['rep'] != 'best']
    out['anon_huge_kb'] = huge
    out['core_refills_per_load'] = refills_per_load(main_dir, LAT_SIZES, 'latency-perfrun')
    out['bandwidth_main'] = bandwidth_rows(os.path.join(main_dir, 'bandwidth.csv'))
    if fu:
        rows, _ = latency_rows(os.path.join(fu, 'latency-fresh.csv'))
        out['latency_fresh'] = best_by_size(rows)
        out['latency_fresh_reps'] = [r for r in rows if r['rep'] != 'best']
        out['pair'] = bandwidth_rows(os.path.join(fu, 'pair.csv'))
        out['asm'] = bandwidth_rows(os.path.join(fu, 'asm.csv'))
        out['dram'] = bandwidth_rows(os.path.join(fu, 'dram.csv'))
        bycpu, cur = {}, None
        for line in open(os.path.join(fu, 'latency-bycpu.csv')):
            line = line.strip()
            m = re.match(r'-- cpu (\d+) (repeated|fresh)', line)
            if m:
                cur = f'cpu{m.group(1)}-{m.group(2)}'; bycpu[cur] = {}; continue
            f = line.split(',')
            if len(f) == 4 and f[1] == 'best':
                bycpu[cur][int(f[0])] = float(f[3])
        out['latency_bycpu'] = bycpu
    if un:
        out['cmn_per_load'] = refills_per_load(un, UNCORE_SIZES, 'chase')
        for tag in ('bw-8M-14T', 'bw-256M-64T'):
            out['cmn_' + tag] = {'counts': perf_counts(os.path.join(un, f'cmn-{tag}.csv')),
                                 'bw': bandwidth_rows(os.path.join(un, f'{tag}.csv'))}
    json.dump(out, sys.stdout, indent=1, sort_keys=True)

main()
