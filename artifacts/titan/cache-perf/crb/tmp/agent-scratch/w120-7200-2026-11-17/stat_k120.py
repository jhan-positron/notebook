#!/usr/bin/env python3
"""stat_k120.py - statistics of threads120.csv, the 120-thread file of run_kernels.sh and ra.sh.

Usage: stat_k120.py [--json] [FOLDER ...] [--pool [FOLDER ...]]

Each FOLDER holds one threads120.csv. In that file one process is one "-- binary ..." header
line, then one csv line per timed interval (rep 0, 1, 2), then one "best" line (not used here).

Output, per folder and per (kernel, binary):
  n, min, median and max of aggregate_GBps over the intervals (GB = 1e9 bytes),
  every interval in file order with its round and its per-thread min and max (GB/s),
  and the load value of the header lines (min and max per folder).
--pool F1 F2 ..  also prints the same statistics over the intervals of F1, F2, .. taken together.
                 Each of these folders is still printed alone first.
--pool           (no folder after it) pools all folders of the command line.
--json           prints the rows as a JSON list instead of text.
The parser follows summarize.py of results/kernels-20261113T181222Z.
"""
import argparse, json, os, re, statistics, sys

HDR = re.compile(r'-- binary (\S+) kernel (\S+) threads (\d+) cpus (\S+) bytes (\S+) round (\d+) load (\S+)(?: utc (\S+))?')


def load(folder):
    """Return the processes of folder/threads120.csv in file order, each with its intervals."""
    fn = os.path.join(folder, 'threads120.csv')
    procs, cur = [], None
    with open(fn) as f:
        for ln, l in enumerate(f, 1):
            l = l.strip()
            m = HDR.match(l)
            if m:
                cur = dict(folder=folder, binary=m[1], kernel=m[2], round=int(m[6]), load=float(m[7]), utc=m[8], iv=[])
                procs.append(cur)
                continue
            p = l.split(',')
            if len(p) > 8 and p[3].isdigit():
                if cur is None or p[0] != cur['kernel']:
                    sys.exit(f'{fn}:{ln}: interval line does not belong to the header line before it')
                # aggregate_GBps, per_thread_min_GBps, per_thread_max_GBps
                cur['iv'].append((float(p[6]), float(p[7]), float(p[8]), int(p[4]) // int(p[2])))
    if not procs:
        sys.exit(f'{fn}: no "-- binary" header line')
    return procs


def rows_of(label, procs, folders=None):
    """One row per (kernel, binary), in the order of first appearance in procs."""
    loads = [p['load'] for p in procs]
    cells = {}
    for p in procs:
        cells.setdefault((p['kernel'], p['binary']), []).append(p)
    rows = []
    for (kernel, binary), ps in cells.items():
        iv = [(p['round'], a, lo, hi, n) for p in ps for a, lo, hi, n in p['iv']]
        v = [x[1] for x in iv]
        row = dict(folder=label, kernel=kernel, binary=binary, n=len(v),
                   min=min(v) if v else None, median=round(statistics.median(v), 3) if v else None,
                   max=max(v) if v else None, values=v, rounds=[x[0] for x in iv],
                   per_thread_min=[x[2] for x in iv], per_thread_max=[x[3] for x in iv], passes=[x[4] for x in iv],
                   processes=len(ps), loads=[p['load'] for p in ps],
                   folder_load_min=min(loads), folder_load_max=max(loads))
        if folders:
            row['folders'] = folders
        row['_procs'] = ps  # for the text output only; removed before the JSON output
        rows.append(row)
    return rows


def print_text(title, rows, show_folder):
    nproc = sum(r['processes'] for r in rows)
    per = sorted({len(p['iv']) for r in rows for p in r['_procs']})
    print(f'== {title}')
    print(f'   {nproc} processes, intervals per process: {per}, '
          f'load in the "-- binary" lines: min {rows[0]["folder_load_min"]:.2f} max {rows[0]["folder_load_max"]:.2f}')
    print('   aggregate_GBps per (kernel, binary); under it one line per process: aggregate (per-thread min-max), GB/s')
    for r in rows:
        if r['n']:
            print(f'{r["kernel"]:9} {r["binary"]:7} n={r["n"]:<3} min {r["min"]:7.2f}  median {r["median"]:7.2f}  max {r["max"]:7.2f}')
        else:
            print(f'{r["kernel"]:9} {r["binary"]:7} n=0   NO INTERVAL')
        for p in r['_procs']:
            where = os.path.basename(p['folder']) + ' ' if show_folder else ''
            ivs = ' | '.join(f'{a:.2f} ({lo:.2f}-{hi:.2f}, {n} passes)' for a, lo, hi, n in p['iv']) or 'NO INTERVAL'
            print(f'    {where}round {p["round"]} load {p["load"]:6.2f} utc {p["utc"]} | {ivs}')
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('folders', nargs='*', help='result folders, each with a threads120.csv')
    ap.add_argument('--pool', nargs='*', metavar='FOLDER', help='folders to pool (none named: all folders)')
    ap.add_argument('--json', action='store_true', help='print the rows as JSON')
    a = ap.parse_args()
    norm = lambda d: d.rstrip('/') or '/'
    singles = list(dict.fromkeys(norm(d) for d in a.folders + (a.pool or [])))
    if not singles:
        ap.error('no folder given')
    pool = [norm(d) for d in a.pool] or singles if a.pool is not None else []
    pool = list(dict.fromkeys(pool))
    procs = {d: load(d) for d in singles}
    groups = [(d, rows_of(d, procs[d]), False) for d in singles]
    if pool:
        allp = [p for d in pool for p in procs[d]]
        groups.append((f'pool of {len(pool)} folders: ' + ', '.join(os.path.basename(d) for d in pool),
                       rows_of('pool', allp, pool), True))
    if a.json:
        out = [{k: v for k, v in r.items() if k != '_procs'} for _, rows, _ in groups for r in rows]
        json.dump(out, sys.stdout, indent=1)
        print()
    else:
        for title, rows, show_folder in groups:
            print_text(title, rows, show_folder)
    empty = [(p['folder'], p['kernel'], p['binary'], p['round']) for d in singles for p in procs[d] if not p['iv']]
    if empty:
        sys.exit(f'process without any interval line (folder, kernel, binary, round): {empty}')


if __name__ == '__main__':
    main()
