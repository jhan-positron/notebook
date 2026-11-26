#!/usr/bin/env python3
"""Print or compare the conflict regions of a file with git conflict markers.
usage: regions.py list <file>            -> one line per region: start, ours-lines, theirs-lines
       regions.py dump <file> <outdir>   -> writes region-N.ours / region-N.theirs
       regions.py same <fileA> <fileB>   -> says per region whether both sides are identical in A and B
"""
import sys, os

def regions(path):
    out = []; cur = None; side = None
    for i, line in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
        if line.startswith('<<<<<<< '):
            cur = {'start': i, 'ours': [], 'theirs': []}; side = 'ours'
        elif line.startswith('=======') and cur is not None and side == 'ours':
            cur['mid'] = i; side = 'theirs'
        elif line.startswith('>>>>>>> ') and cur is not None:
            cur['end'] = i; out.append(cur); cur = None; side = None
        elif cur is not None:
            cur[side].append(line)
    return out

cmd = sys.argv[1]
if cmd == 'list':
    for n, r in enumerate(regions(sys.argv[2]), 1):
        print(f"region {n}: lines {r['start']}-{r['end']}  ours={len(r['ours'])} lines  theirs={len(r['theirs'])} lines")
elif cmd == 'dump':
    os.makedirs(sys.argv[3], exist_ok=True)
    for n, r in enumerate(regions(sys.argv[2]), 1):
        open(os.path.join(sys.argv[3], f'region-{n}.ours'), 'w').writelines(r['ours'])
        open(os.path.join(sys.argv[3], f'region-{n}.theirs'), 'w').writelines(r['theirs'])
elif cmd == 'same':
    a = regions(sys.argv[2]); b = regions(sys.argv[3])
    print(f"regions: A={len(a)} B={len(b)}")
    for n, (x, y) in enumerate(zip(a, b), 1):
        print(f"region {n}: ours-identical={x['ours']==y['ours']}  theirs-identical={x['theirs']==y['theirs']}  (A ours={len(x['ours'])} theirs={len(x['theirs'])}; B ours={len(y['ours'])} theirs={len(y['theirs'])})")
