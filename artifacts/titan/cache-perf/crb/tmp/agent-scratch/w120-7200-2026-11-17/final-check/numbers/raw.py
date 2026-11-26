#!/usr/bin/env python3
"""Own parser of the raw csv files (lens NUMBERS). No import of facts.json / build_facts.py / make_report.py."""
import os, re, statistics

R = '/home/jhan/workspace/titan/cache-perf/crb/results'


def parse_bandwidth(path):
    """bandwidth.c files (threads120.csv, A1.csv, A3.csv). Returns list of processes."""
    procs = []
    cur = None
    with open(path) as fh:
        for ln, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if line.startswith('-- '):
                cur = {'path': path, 'line': ln, 'hdr': line, 'iv': []}
                m = re.match(r'-- binary (\S+) kernel (\S+) threads (\d+) cpus (\S+) bytes (\S+) round (\d+) load (\S+)(?: utc (\S+))?', line)
                if m:
                    cur.update(binary=m[1], kernel=m[2], round=int(m[6]), load=float(m[7]), utc=m[8], tag=None, minms=500)
                else:
                    m = re.match(r'-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) logins (\S+) utc (\S+) args (.*)$', line)
                    assert m, line
                    args = m[11]
                    k = re.search(r'--kernel (\S+)', args)[1]
                    mm = re.search(r'--min-ms (\d+)', args)[1]
                    rm = re.search(r'-r(\d)$', m[2])
                    cur.update(binary=m[3], kernel=k, round=int(rm[1]) if rm else None, load=float(m[5]), utc=m[10], tag=m[2], minms=int(mm), args=args)
                procs.append(cur)
                continue
            p = line.split(',')
            if len(p) >= 10 and p[3].isdigit() and p[0] != 'thread':
                # kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,min,max,avg
                cur['iv'].append({'kernel': p[0], 'rep': int(p[3]), 'agg': float(p[6]), 'total_bytes': int(p[4]),
                                  'bpt': int(p[2]), 'passes': int(p[4]) / int(p[2]), 'line': ln, 'elapsed': float(p[5])})
    return procs


def parse_bwx(path):
    """bwx / bwx12 csv. Returns list of processes; each has intervals in file order.
    A file without '-- step' lines is one process."""
    procs = []
    cur = None
    def newproc(hdr, ln):
        return {'path': path, 'line': ln, 'hdr': hdr, 'iv': [], 'meta': {}}
    with open(path) as fh:
        for ln, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if line.startswith('-- '):
                cur = newproc(line, ln)
                m = re.match(r'-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) logins (\S+) utc (\S+) args (.*)$', line)
                assert m, line
                cur.update(tag=m[2], binary=m[3], load=float(m[5]), utc=m[10], args=m[11])
                procs.append(cur)
                continue
            if cur is None:
                cur = newproc(None, 0)
                cur.update(tag=None, binary=None, load=None, utc=None, args=None)
                procs.append(cur)
            if line.startswith('#'):
                for key in ('seq', 'rounds', 'stop', 'start', 'count', 'min_ms', 'thp'):
                    m = re.search(r'\b%s=(\S+)' % key, line)
                    if m and key not in cur['meta']:
                        cur['meta'][key] = m[1].rstrip(';')
                continue
            p = line.split(',')
            if p[0] == 'I':
                cur['iv'].append({'round': int(p[1]), 'pos': int(p[2]), 'kernel': p[3], 'I_agg': float(p[8]), 'line': ln,
                                  'T': [], 'max_elapsed': float(p[7]), 'total_bytes': int(p[6])})
            elif p[0] == 'T':
                key = (int(p[1]), int(p[2]), p[3])
                iv = cur['iv'][-1] if cur['iv'] else None
                if iv is None or (iv['round'], iv['pos'], iv['kernel']) != key:
                    # T rows before their I row?  find or create
                    iv = next((x for x in cur['iv'] if (x['round'], x['pos'], x['kernel']) == key), None)
                    if iv is None:
                        iv = {'round': key[0], 'pos': key[1], 'kernel': key[2], 'I_agg': None, 'line': None, 'T': []}
                        cur['iv'].append(iv)
                iv['T'].append({'tid': int(p[4]), 'cpu': int(p[5]), 'bytes': int(p[6]), 'el': float(p[7]),
                                't_start': float(p[9]), 't_end': float(p[10]), 'flags': p[-1], 'line': ln})
    for pr in procs:
        for iv in pr['iv']:
            iv['n'] = len(iv['T'])
            iv['rate'] = sum(t['bytes'] / t['el'] / 1e9 for t in iv['T'])
            cpus = [t['cpu'] for t in iv['T']]
            iv['ok6456'] = (len(cpus) == 120 and len(set(cpus)) == 120 and sum(c < 64 for c in cpus) == 64 and max(cpus) <= 119)
    return procs


def r2(x):
    return float('%.2f' % x)


def med(v):
    return statistics.median(v)
