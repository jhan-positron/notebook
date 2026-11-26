#!/usr/bin/env python3
"""Independent raw parser for the reviewer (lens NUMBERS). Reads only raw files under R."""
import os, re, statistics, json
R = '/home/jhan/workspace/titan/cache-perf/crb/results'

def parse_bw(path):
    """bandwidth.c csv: returns list of processes: dict(header fields, line, intervals=[(agg, total_bytes, elapsed, bpt, line)])"""
    procs = []
    cur = None
    with open(path) as fh:
        for ln, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if line.startswith('-- '):
                cur = {'hdr': line, 'line': ln, 'iv': []}
                procs.append(cur)
                continue
            if line.startswith('#') or line.startswith('kernel,') or line.startswith('thread,'):
                continue
            p = line.split(',')
            if len(p) >= 7 and p[3].isdigit():
                cur['iv'].append({'agg': float(p[6]), 'bytes': int(p[4]), 'el': float(p[5]), 'bpt': int(p[2]),
                                  'kernel': p[0], 'threads': int(p[1]), 'rep': int(p[3]), 'line': ln,
                                  'passes': int(p[4]) / int(p[2])})
    return procs

def hdr_new(h):
    m = re.match(r'-- binary (\S+) kernel (\S+) threads (\S+) cpus (\S+) bytes (\S+) round (\S+) load (\S+) utc (\S+)$', h)
    assert m, h
    return dict(binary=m.group(1), kernel=m.group(2), round=int(m.group(6)), load=float(m.group(7)), utc=m.group(8))

def hdr_step(h):
    m = re.match(r'-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) logins (\S+) utc (\S+) args (.*)$', h)
    assert m, h
    args = m.group(11)
    k = re.search(r'--kernel (\S+)', args).group(1)
    return dict(step=m.group(1), tag=m.group(2), binary=m.group(3), load=float(m.group(5)), utc=m.group(10), kernel=k, args=args)

def parse_bwx(path):
    """returns ordered list of intervals: dict(round,pos,kernel,total,n,h0,h1,line_I,I_agg,first_T,last_T,t_start,t_end)"""
    ivs = {}
    order = []
    with open(path) as fh:
        for ln, line in enumerate(fh, 1):
            if line.startswith('#'):
                continue
            p = line.rstrip('\n').split(',')
            if p[0] == 'I':
                key = (int(p[1]), int(p[2]), p[3])
                d = ivs.setdefault(key, {'round': key[0], 'pos': key[1], 'kernel': key[2], 'total': 0.0, 'n': 0, 'h0': 0.0, 'h1': 0.0, 'cpus': [], 'tstart': [], 'tend': []})
                if key not in order: order.append(key)
                d['line_I'] = ln; d['I_agg'] = float(p[8]); d['I_threads'] = int(p[5])
            elif p[0] == 'T':
                key = (int(p[1]), int(p[2]), p[3])
                d = ivs.setdefault(key, {'round': key[0], 'pos': key[1], 'kernel': key[2], 'total': 0.0, 'n': 0, 'h0': 0.0, 'h1': 0.0, 'cpus': [], 'tstart': [], 'tend': []})
                if key not in order: order.append(key)
                r = float(p[6]) / float(p[7]) / 1e9
                cpu = int(p[5])
                d['total'] += r; d['n'] += 1
                d['h0' if cpu < 64 else 'h1'] += r
                d['cpus'].append(cpu)
                d['tstart'].append(float(p[9])); d['tend'].append(float(p[10]))
                d.setdefault('first_T', ln); d['last_T'] = ln
                d.setdefault('flags', []).append(p[-1])
    out = [ivs[k] for k in order]
    return out

def launches(path):
    out = []
    for ln, line in enumerate(open(path), 1):
        out.append((ln, line.rstrip('\n')))
    return out

def med(v): return statistics.median(v)
