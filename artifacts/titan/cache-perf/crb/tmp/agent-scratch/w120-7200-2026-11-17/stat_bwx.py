#!/usr/bin/env python3
"""stat_bwx.py [--json] [--pool] FOLDER...

Reads the bwx csv files (*.csv) of each result folder.

Part 1, one row per interval (round, pos, kernel) of each csv file:
  thr      number of T rows (threads)
  total    sum over threads of bytes / elapsed_s / 1e9, in GB/s (GB = 1e9 bytes; the method of an.py)
  h0, h1   the same sum for the threads on CPUs 0-63 (h0) and on CPUs 64-127 (h1),
           with the thread count and the lowest and highest per-thread rate
  I_agg    aggregate_GBps of the I row with the same round, pos and kernel
           (the runner computes it as sum(bytes) / max(per-thread elapsed_s))
  64+56    "yes" when the interval has 64 threads on 64 different CPUs of 0-63
           and 56 threads on 56 different CPUs of 64-119, and no other thread
  flg      number of T rows whose flags field is not "-" (bwx writes "late" for a thread that
           started more than 100 us after the common start); these rows are counted, not removed

Part 2, per folder and kernel, over the "64+56" intervals only: n, min, median, max of total,
and the totals in file order (csv files sorted by name, rows in the order of the file).

--pool  adds Part 2 once more over all folders together (folder name "POOLED").
--json  prints {"intervals": [...], "summary": [...]} instead of text.
A copy kernel counts read plus written bytes. No kernel is treated specially.
"""
import collections
import glob
import json
import os
import re
import statistics
import sys


def half(cpu):
    return 0 if cpu < 64 else 1


def read_csv(path):
    """Return (header info, {(round, pos, kernel): [(cpu, GB/s, flags)]}, {(round, pos, kernel): aggregate_GBps})."""
    info = {}
    threads = collections.OrderedDict()
    agg = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith('#'):
                for key in ('min_ms', 'stop', 'thp'):
                    m = re.search(r'\b%s=(\S+)' % key, line)
                    if m and key not in info:
                        info[key] = m.group(1).rstrip(';')
                continue
            p = line.rstrip('\n').split(',')
            if p[0] == 'T':
                # T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags
                threads.setdefault((p[1], p[2], p[3]), []).append((int(p[5]), float(p[6]) / float(p[7]) / 1e9, p[-1]))
            elif p[0] == 'I':
                # I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps
                agg[(p[1], p[2], p[3])] = float(p[8])
    return info, threads, agg


def interval_rows(folder):
    rows = []
    name = os.path.basename(os.path.normpath(folder))
    for path in sorted(glob.glob(os.path.join(folder, '*.csv'))):
        info, threads, agg = read_csv(path)
        for (rnd, pos, kernel), tl in threads.items():
            row = {'folder': name, 'file': os.path.basename(path), 'round': int(rnd), 'pos': int(pos),
                   'kernel': kernel, 'threads': len(tl), 'total': sum(t[1] for t in tl),
                   'I_agg': agg.get((rnd, pos, kernel)), 'flagged': sum(t[2] != '-' for t in tl),
                   'min_ms': info.get('min_ms'), 'stop': info.get('stop'), 'thp': info.get('thp')}
            for h in (0, 1):
                rates = [t[1] for t in tl if half(t[0]) == h]
                row['h%d_n' % h] = len(rates)
                row['h%d_sum' % h] = sum(rates)
                row['h%d_min' % h] = min(rates) if rates else None
                row['h%d_max' % h] = max(rates) if rates else None
            cpus = [t[0] for t in tl]
            row['is_64_56'] = (row['h0_n'] == 64 and row['h1_n'] == 56 and max(cpus) <= 119
                               and len(set(cpus)) == 120)
            rows.append(row)
    return rows


def summarize(rows, folder_name):
    """Per kernel over the 64+56 intervals of rows: n, min, median, max and the totals in file order."""
    by_kernel = collections.OrderedDict()
    for r in rows:
        if r['is_64_56']:
            by_kernel.setdefault(r['kernel'], []).append(r)
    out = []
    for kernel, rs in by_kernel.items():
        v = [r['total'] for r in rs]
        out.append({'folder': folder_name, 'kernel': kernel, 'n': len(v), 'min': min(v),
                    'median': statistics.median(v), 'max': max(v), 'values': v,
                    'files': sorted(set(r['file'] for r in rs)), 'flagged': sum(r['flagged'] for r in rs),
                    'min_ms': sorted(set(str(r['min_ms']) for r in rs)),
                    'stop': sorted(set(str(r['stop']) for r in rs)),
                    'thp': sorted(set(str(r['thp']) for r in rs))})
    return out


def rounded(obj):
    if isinstance(obj, float):
        return round(obj, 3)
    if isinstance(obj, dict):
        return {k: rounded(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rounded(v) for v in obj]
    return obj


def fmt_half(row, h):
    if not row['h%d_n' % h]:
        return '%32s' % '-'
    return '%7.1f n=%3d (%5.2f-%5.2f)' % (row['h%d_sum' % h], row['h%d_n' % h], row['h%d_min' % h], row['h%d_max' % h]) + ' ' * 4


def print_summary(summary):
    print('   %-16s %3s %8s %8s %8s  %-12s %3s %s' % ('kernel', 'n', 'min', 'median', 'max', 'min_ms', 'flg', 'totals in file order (GB/s)'))
    for s in summary:
        print('   %-16s %3d %8.2f %8.2f %8.2f  %-12s %3d %s' % (s['kernel'], s['n'], s['min'], s['median'], s['max'],
              '/'.join(s['min_ms']), s['flagged'], ' '.join('%.2f' % x for x in s['values'])))


def main(argv):
    flags = [a for a in argv if a.startswith('--')]
    folders = [a for a in argv if not a.startswith('--')]
    if not folders or set(flags) - {'--json', '--pool'}:
        sys.exit(__doc__)
    all_rows, all_summary = [], []
    per_folder = []
    for folder in folders:
        rows = interval_rows(folder)
        if not rows:
            sys.exit('no T rows in the csv files of ' + folder)
        summary = summarize(rows, rows[0]['folder'])
        per_folder.append((rows, summary))
        all_rows += rows
        all_summary += summary
    pooled = summarize(all_rows, 'POOLED') if '--pool' in flags else []
    if '--json' in flags:
        json.dump(rounded({'intervals': all_rows, 'summary': all_summary + pooled}), sys.stdout, indent=1)
        print()
        return
    for rows, summary in per_folder:
        print('== ' + rows[0]['folder'])
        last_file = None
        for r in rows:
            if r['file'] != last_file:
                last_file = r['file']
                print('-- %s  (header: stop=%s min_ms=%s thp=%s)' % (r['file'], r['stop'], r['min_ms'], r['thp']))
                print('   %2s %3s %-16s %4s %8s  %-32s %-32s %8s %-5s %s' % ('rd', 'pos', 'kernel', 'thr', 'total',
                      'h0: CPUs 0-63, GB/s n (min-max)', 'h1: CPUs 64-127', 'I_agg', '64+56', 'flg'))
            print('   %2d %3d %-16s %4d %8.2f  %s %s %8s %-5s %d' % (r['round'], r['pos'], r['kernel'], r['threads'], r['total'],
                  fmt_half(r, 0), fmt_half(r, 1), '-' if r['I_agg'] is None else '%.2f' % r['I_agg'],
                  'yes' if r['is_64_56'] else 'no', r['flagged']))
        print('-- 64+56 intervals of %s, total GB/s per kernel' % rows[0]['folder'])
        print_summary(summary)
        print()
    if pooled:
        print('== POOLED over %d folders, 64+56 intervals, total GB/s per kernel' % len(folders))
        print_summary(pooled)


if __name__ == '__main__':
    main(sys.argv[1:])
