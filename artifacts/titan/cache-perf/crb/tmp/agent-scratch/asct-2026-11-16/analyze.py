#!/usr/bin/env python3
"""analyze.py OUT.json FOLDER...: read ASCT result folders (asct-single-*, asct-chip-*, asct-mesh-*, asct-prep-*)
and write every number the report uses. GB = 1e9 bytes. A line = 64 bytes.

Rates come from the lines the ASCT binary prints for its measured phase:
  'tid = T, repetitions = R, tickdiff = D, time = S'  ->  thread rate = R * buflen / S
  'Total Bandwidth (MB/sec) = X'                       ->  process total (sum of the thread rates)
Counter files are written by ASCT's capture code (dietperf): one file <cpu>_<tid> per thread, one line per
event: code,count,time_enabled_ns,time_running_ns. Counts are divided by the lines of the measured phase.
"""
import glob
import json
import os
import re
import statistics as st
import sys

LINE = 64
MESH0 = range(0, 64)


def parse_out(path):
    """One process output -> dict or None when the process printed no total."""
    tid_cpu, buflen, nops = {}, None, None
    threads = {}
    total = reps = None
    for line in open(path, errors='replace'):
        m = re.match(r'CPU(\d+) BWTHREAD(\d+): buflen = (\d+), .*inner_nops = (\d+), .*tid = (\d+)', line)
        if m:
            tid_cpu[int(m.group(5))] = int(m.group(1))
            buflen, nops = int(m.group(3)), int(m.group(4))
            continue
        m = re.match(r'tid = (\d+), repetitions = (\d+), tickdiff = (\d+), time = ([0-9.]+)', line)
        if m:
            tid, r, sec = int(m.group(1)), int(m.group(2)), float(m.group(4))
            threads[tid] = {'reps': r, 'sec': sec}
            continue
        m = re.match(r'Total Bandwidth \(MB/sec\) = ([0-9.]+)', line)
        if m:
            total = float(m.group(1)) / 1e3
            continue
        m = re.match(r'Bandwidth Repetitions = (\d+)', line)
        if m:
            reps = int(m.group(1))
    if total is None or not threads or buflen is None:
        return None
    per = {}
    for tid, t in threads.items():
        cpu = tid_cpu[tid]
        per[cpu] = {'tid': tid, 'reps': t['reps'], 'sec': t['sec'], 'gbps': t['reps'] * buflen / t['sec'] / 1e9,
                    'lines': t['reps'] * buflen / LINE}
    return {'total': total, 'reps': reps, 'buflen': buflen, 'nops': nops, 'threads': per,
            'sum_threads': sum(t['gbps'] for t in per.values())}


def parse_counters(folder, proc, names):
    """Counter folder of one process -> {cpu: {name: per-line count}}, plus the checks."""
    out, bad = {}, []
    for f in glob.glob(os.path.join(folder, '*')):
        cpu, tid = (int(x) for x in os.path.basename(f).split('_'))
        th = proc['threads'].get(cpu)
        if th is None or th['tid'] != tid:
            bad.append(f'no thread for {os.path.basename(f)}')
            continue
        row = {}
        for line in open(f):
            p = line.strip().split(',')
            if len(p) != 4:
                continue
            code, cnt, en, run = int(p[0], 16), int(p[1]), int(p[2]), int(p[3])
            name = names.get(code, hex(code))
            if run != en:
                bad.append(f'{name} cpu {cpu}: running {run} of enabled {en} ns')
            ratio = en / 1e9 / th['sec'] if th['sec'] else 0
            if not 0.98 <= ratio <= 1.02:
                bad.append(f'{name} cpu {cpu}: enabled time is {ratio:.3f} of the measured time')
            row[name] = cnt / th['lines']
        out[cpu] = row
    return out, bad


def med(v):
    return st.median(v) if v else None


def load_codes(folder):
    names, sets = {}, {}
    p = os.path.join(folder, 'events.codes')
    if os.path.exists(p):
        for line in open(p):
            if '|' not in line:
                continue
            s, evs = line.strip().split('|')
            sets[s] = []
            for e in evs.split(','):
                if '=' in e:
                    n, c = e.split('=')
                    names[int(c, 16)] = n
                    sets[s].append(n)
    return names, sets


def launches(folder):
    loads, rcs = [], []
    p = os.path.join(folder, 'launches.txt')
    if not os.path.exists(p):
        return {'n': 0}
    for line in open(p):
        m = re.match(r'launch (\S+) epoch ([0-9.]+) load ([0-9.]+) [0-9.]+ [0-9.]+ (\d+)/', line)
        if m:
            loads.append((float(m.group(3)), int(m.group(4))))
        m = re.match(r'rc (-?\d+) (\S+)', line)
        if m:
            rcs.append(int(m.group(1)))
    return {'n': len(loads), 'load1_min': min(l[0] for l in loads) if loads else None,
            'load1_max': max(l[0] for l in loads) if loads else None,
            'runnable_max': max(l[1] for l in loads) if loads else None,
            'rc_nonzero': sum(1 for r in rcs if r != 0), 'rc_count': len(rcs)}


def do_single(folder):
    names, sets = load_codes(folder)
    res = {'folder': os.path.basename(folder), 'launches': launches(folder), 'cells': {}, 'counted': {}, 'nops': {}, 'nops_counted': {}, 'problems': []}
    for f in sorted(glob.glob(os.path.join(folder, 'u.*.out'))):
        _, cpu, size, rep = os.path.basename(f)[:-4].split('.')
        p = parse_out(f)
        if p is None:
            res['problems'].append(f'no result in {os.path.basename(f)}')
            continue
        res['cells'].setdefault(f'{cpu}.{size}', []).append(p['total'])
    for f in sorted(glob.glob(os.path.join(folder, 'n.*.out'))):      # part N: injected NOPs
        _, nn, cpu, size, rep = os.path.basename(f)[:-4].split('.')
        p = parse_out(f)
        if p is None:
            res['problems'].append(f'no result in {os.path.basename(f)}')
            continue
        if p['nops'] != int(nn):
            res['problems'].append(f'{os.path.basename(f)}: the binary reports {p["nops"]} NOPs')
        res['nops'].setdefault(f'{nn}.{cpu}.{size}', []).append(p['total'])
    for f in sorted(glob.glob(os.path.join(folder, 'nc.*.out'))):     # part NC: injected NOPs with counters
        _, s, nn, cpu, size, rep = os.path.basename(f)[:-4].split('.')
        p = parse_out(f)
        if p is None:
            res['problems'].append(f'no result in {os.path.basename(f)}')
            continue
        if p['nops'] != int(nn):
            res['problems'].append(f'{os.path.basename(f)}: the binary reports {p["nops"]} NOPs')
        cnt, bad = parse_counters(f[:-4] + '.d', p, names)
        res['problems'] += [f'{os.path.basename(f)}: {b}' for b in bad]
        cell = res['nops_counted'].setdefault(f'{nn}.{cpu}.{size}', {'rate': [], 'ev': {}})
        cell['rate'].append(p['total'])
        for name, v in cnt.get(int(cpu), {}).items():
            cell['ev'].setdefault(name, []).append(v)
    for f in sorted(glob.glob(os.path.join(folder, 'c.*.out'))):
        _, s, cpu, size, rep = os.path.basename(f)[:-4].split('.')
        p = parse_out(f)
        if p is None:
            res['problems'].append(f'no result in {os.path.basename(f)}')
            continue
        cnt, bad = parse_counters(f[:-4] + '.d', p, names)
        res['problems'] += [f'{os.path.basename(f)}: {b}' for b in bad]
        cell = res['counted'].setdefault(f'{cpu}.{size}', {'rate': [], 'ev': {}})
        cell['rate'].append(p['total'])
        for name, v in cnt.get(int(cpu), {}).items():
            cell['ev'].setdefault(name, []).append(v)
    return res


def mesh_split(proc):
    m0 = [t['gbps'] for c, t in proc['threads'].items() if c in MESH0]
    m1 = [t['gbps'] for c, t in proc['threads'].items() if c not in MESH0]
    return {'total': proc['total'], 'mesh0': sum(m0), 'mesh1': sum(m1), 'n0': len(m0), 'n1': len(m1),
            'thr0': [min(m0), med(m0), max(m0)] if m0 else None, 'thr1': [min(m1), med(m1), max(m1)] if m1 else None,
            'sec': [min(t['sec'] for t in proc['threads'].values()), max(t['sec'] for t in proc['threads'].values())],
            # lower bound of the simultaneous rate: all bytes of the process over the time of its slowest thread
            'floor': sum(t['lines'] for t in proc['threads'].values()) * LINE / max(t['sec'] for t in proc['threads'].values()) / 1e9,
            'reps': proc['reps']}


def do_chip(folder):
    names, sets = load_codes(folder)
    res = {'folder': os.path.basename(folder), 'launches': launches(folder), 'runs': {}, 'counted': {}, 'mix': {}, 'problems': []}
    for f in sorted(glob.glob(os.path.join(folder, 'w.*.out'))):
        m = re.match(r'w\.(\d+)\.n(\d+)\.d([0-9.]+)\.(\d+)\.out', os.path.basename(f))
        p = parse_out(f)
        if p is None:
            res['problems'].append(f'no result in {os.path.basename(f)}')
            continue
        if p['nops'] != int(m.group(2)):
            res['problems'].append(f'{os.path.basename(f)}: the binary reports {p["nops"]} NOPs')
        if len(p['threads']) != {'6456': 120, '6400': 64, '0056': 56, '5656': 112}.get(m.group(1), len(p['threads'])):
            res['problems'].append(f'{os.path.basename(f)}: {len(p["threads"])} threads reported')
        res['runs'].setdefault(f'{m.group(1)}.n{m.group(2)}.d{m.group(3)}', []).append(mesh_split(p))
    for f in sorted(glob.glob(os.path.join(folder, 'x.*.out'))):      # step MIX: read-write traffic types
        m = re.match(r'x\.(\d+)\.t(\d)\.d([0-9.]+)\.(\d+)\.out', os.path.basename(f))
        p = parse_out(f)
        if p is None:
            res['problems'].append(f'no result in {os.path.basename(f)}')
            continue
        res['mix'].setdefault(m.group(2), []).append(p['total'])
    for f in sorted(glob.glob(os.path.join(folder, 'c.*.out'))):
        m = re.match(r'c\.(\w+)\.(\d+)\.n(\d+)\.out', os.path.basename(f))
        p = parse_out(f)
        if p is None:
            res['problems'].append(f'no result in {os.path.basename(f)}')
            continue
        cnt, bad = parse_counters(f[:-4] + '.d', p, names)
        if bad:
            res['problems'].append(f'{os.path.basename(f)}: {len(bad)} counter rows fail a check, first: {bad[0]}')
        cell = res['counted'].setdefault(f'{m.group(2)}.n{m.group(3)}', {'sets': {}, 'ev': {}})
        cell['sets'][m.group(1)] = mesh_split(p)
        evnames = sorted({n for row in cnt.values() for n in row})
        for name in evnames:
            v0 = [row[name] for c, row in cnt.items() if c in MESH0 and name in row]
            v1 = [row[name] for c, row in cnt.items() if c not in MESH0 and name in row]
            cell['ev'].setdefault(name, {})[m.group(1)] = {
                'mesh0': [min(v0), med(v0), max(v0)] if v0 else None,
                'mesh1': [min(v1), med(v1), max(v1)] if v1 else None, 'threads': len(v0) + len(v1)}
    return res


def do_mesh(folder):
    res = {'folder': os.path.basename(folder), 'launches': launches(folder), 'tags': {}, 'problems': [], 'order': []}
    spec = {}
    for line in open(os.path.join(folder, 'launches.txt')):
        m = re.match(r'launch (\S+) .* layout (\S+) bytes (\d+) nops (\d+) duration (\S+)', line)
        if m:
            spec[m.group(1)] = {'layout': m.group(2), 'bytes': int(m.group(3)), 'nops': int(m.group(4)), 'duration': m.group(5)}
            res['order'].append(m.group(1))
    # every counting window must lie inside the measured phase of its process: the phase ends at the 'rc' line
    # and lasts as long as the slowest thread reports
    t_launch, t_rc, wins = {}, {}, {}
    for line in open(os.path.join(folder, 'launches.txt')):
        m = re.match(r'launch (\S+) epoch ([0-9.]+)', line)
        if m:
            t_launch[m.group(1)] = float(m.group(2))
        m = re.match(r'rc -?\d+ (\S+) epoch ([0-9.]+)', line)
        if m:
            t_rc[m.group(1)] = float(m.group(2))
        m = re.match(r'win (\S+) (\S+) (start|end) ([0-9.]+)', line)
        if m:
            wins.setdefault(m.group(1), {}).setdefault(m.group(2), {})[m.group(3)] = float(m.group(4))
    for tag, sp in spec.items():
        rate = None
        phase = None
        if sp['layout'] != 'idle':
            p = parse_out(os.path.join(folder, tag + '.out')) if os.path.exists(os.path.join(folder, tag + '.out')) else None
            if p is None:
                res['problems'].append(f'no result for {tag}')
                continue
            rate = p['total']
            if tag in t_rc:
                longest = max(t['sec'] for t in p['threads'].values())
                phase = {'start': t_rc[tag] - longest, 'end': t_rc[tag], 'startup': t_rc[tag] - longest - t_launch[tag]}
                for sn, w in wins.get(tag, {}).items():
                    if 'end' not in w or w['start'] < phase['start'] or w['end'] > phase['end']:
                        res['problems'].append(f'{tag} {sn}: window {w.get("start", 0) - phase["start"]:.1f} to '
                                               f'{w.get("end", 0) - phase["start"]:.1f} s is not inside the measured phase of {longest:.1f} s')
        res.setdefault('phase', {})[tag] = phase
        ev = {}
        for f in sorted(glob.glob(os.path.join(folder, f'{tag}.*.perf'))):
            sn = os.path.basename(f).split('.')[-2]
            for line in open(f):
                p = line.strip().split(',')
                if len(p) < 5 or line.startswith('#'):
                    continue
                m = re.match(r'arm_cmn_(\d)/(.*)/', p[2])
                if not m or p[0].startswith('<'):
                    if m:
                        res['problems'].append(f'{tag} {sn} {p[2]}: {p[0]}')
                    continue
                mesh, name = int(m.group(1)), m.group(2)
                cnt, sec, pct = float(p[0]), float(p[3]) / 1e9, float(p[4])
                if pct < 99.9:
                    res['problems'].append(f'{tag} {sn} {name} mesh {mesh}: counted {pct} % of the window')
                ev.setdefault(name, {})[f'mesh{mesh}'] = {'count': cnt, 'sec': sec, 'per_s': cnt / sec, 'set': sn}
        res['tags'][tag] = {'spec': sp, 'rate': rate, 'ev': ev}
    return res


def main():
    out = {'single': [], 'chip': [], 'mesh': [], 'prep': []}
    for folder in sys.argv[2:]:
        b = os.path.basename(folder.rstrip('/'))
        if b.startswith('asct-single-'):
            out['single'].append(do_single(folder))
        elif b.startswith('asct-chip-'):
            out['chip'].append(do_chip(folder))
        elif b.startswith('asct-mesh-'):
            out['mesh'].append(do_mesh(folder))
        elif b.startswith('asct-prep-'):
            out['prep'].append({'folder': b, 'env': open(os.path.join(folder, 'env.txt')).read(),
                                'sha': open(os.path.join(folder, 'sha.txt')).read(),
                                'resolve': open(os.path.join(folder, 'resolve.txt')).read()})
        else:
            sys.exit(f'unknown folder kind: {b}')
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    for kind in ('single', 'chip', 'mesh'):
        for r in out[kind]:
            print(kind, r['folder'], 'launches', r['launches'], 'problems', len(r['problems']))
            for p in r['problems'][:8]:
                print('   ', p)


if __name__ == '__main__':
    main()
