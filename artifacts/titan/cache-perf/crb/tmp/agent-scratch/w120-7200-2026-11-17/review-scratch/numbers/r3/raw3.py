#!/usr/bin/env python3
"""Round-3 reviewer's own raw parser. Reads only the raw files under R. No facts.json, no build_facts, no make_report."""
import os, re, statistics, collections
R = '/home/jhan/workspace/titan/cache-perf/crb/results'

def parse_bandwidth(path):
    """bandwidth.c csv with '-- ...' headers. Returns list of processes:
    dict(header=line text, line=header line no, kv=dict, iv=[(lineno, rep, total_bytes, elapsed, agg, passes)])"""
    procs = []
    cur = None
    with open(path) as fh:
        for no, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if line.startswith('-- '):
                cur = {'header': line, 'line': no, 'iv': [], 'path': path}
                procs.append(cur)
                continue
            if cur is None or line.startswith('#') or line.startswith('kernel,') or line.startswith('thread'):
                continue
            p = line.split(',')
            if len(p) >= 10 and p[3] not in ('best',) and p[3].isdigit():
                tb = int(p[4]); bpt = int(p[2])
                cur['iv'].append({'line': no, 'kernel': p[0], 'rep': int(p[3]), 'total_bytes': tb,
                                  'elapsed': float(p[5]), 'agg': float(p[6]), 'passes': tb / bpt,
                                  'tmin': float(p[7]), 'tmax': float(p[8])})
    return procs

def hdr_ra(h):
    m = re.match(r'-- binary (\S+) kernel (\S+) threads (\S+) cpus (\S+) bytes (\S+) round (\S+) load (\S+) utc (\S+)', h)
    return dict(binary=m.group(1), kernel=m.group(2), round=int(m.group(6)), load=m.group(7), utc=m.group(8))

def hdr_step(h):
    m = re.match(r'-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) logins (\S+) utc (\S+) args (.*)$', h)
    args = m.group(11)
    k = re.search(r'--kernel (\S+)', args).group(1)
    ms = re.search(r'--min-ms (\S+)', args).group(1)
    return dict(step=m.group(1), tag=m.group(2), binary=m.group(3), load=m.group(5), utc=m.group(10), kernel=k, min_ms=ms, args=args)

def parse_bwx(path):
    """bwx / bwx12 csv. Returns ordered list of intervals:
    dict(round,pos,kernel, I_line, I_agg, total (sum of T rows bytes/elapsed/1e9), n_thr, m0, m1, t_start_min, t_end_max, tag)"""
    out = []
    cur = None
    tag = None
    with open(path) as fh:
        for no, line in enumerate(fh, 1):
            if line.startswith('-- '):
                tag = line.rstrip('\n'); continue
            if line.startswith('#'):
                continue
            p = line.rstrip('\n').split(',')
            if p[0] == 'I':
                cur = {'round': int(p[1]), 'pos': int(p[2]), 'kernel': p[3], 'I_line': no, 'I_agg': float(p[8]),
                       'total': 0.0, 'n_thr': 0, 'm0': 0.0, 'm1': 0.0, 'n0': 0, 'n1': 0, 'cpus': set(),
                       't_start': [], 't_end': [], 'path': path, 'hdr': tag, 'flags': 0, 'T_first': None, 'T_last': None}
                out.append(cur)
            elif p[0] == 'T':
                key = (int(p[1]), int(p[2]), p[3])
                # T rows may come before or after the I row: find the interval
                tgt = cur if (cur is not None and (cur['round'], cur['pos'], cur['kernel']) == key) else None
                if tgt is None:
                    # look up by key among intervals with same hdr, else create a placeholder
                    for c in reversed(out):
                        if (c['round'], c['pos'], c['kernel']) == key and c['hdr'] == tag:
                            tgt = c; break
                if tgt is None:
                    tgt = {'round': key[0], 'pos': key[1], 'kernel': key[2], 'I_line': None, 'I_agg': None,
                           'total': 0.0, 'n_thr': 0, 'm0': 0.0, 'm1': 0.0, 'n0': 0, 'n1': 0, 'cpus': set(),
                           't_start': [], 't_end': [], 'path': path, 'hdr': tag, 'flags': 0, 'T_first': None, 'T_last': None}
                    out.append(tgt); cur = tgt
                cpu = int(p[5]); rate = float(p[6]) / float(p[7]) / 1e9
                tgt['total'] += rate; tgt['n_thr'] += 1
                if cpu < 64: tgt['m0'] += rate; tgt['n0'] += 1
                else: tgt['m1'] += rate; tgt['n1'] += 1
                tgt['cpus'].add(cpu)
                tgt['t_start'].append(float(p[9])); tgt['t_end'].append(float(p[10]))
                if p[-1] != '-': tgt['flags'] += 1
                if tgt['T_first'] is None: tgt['T_first'] = no
                tgt['T_last'] = no
    return out

def med(v):
    return statistics.median(v)
