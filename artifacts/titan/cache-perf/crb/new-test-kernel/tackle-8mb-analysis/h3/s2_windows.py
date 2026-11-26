#!/usr/bin/env python3
"""s2_windows.py <S2.csv> [size_bytes]: for each S2 process of one size, print every window rate (prefix and target)
in time order with the window start time since process start. Shows whether level switches sit at fixed process times."""
import sys
size = sys.argv[2] if len(sys.argv) > 2 else '8388608'
cur = None; out = []
for line in open(sys.argv[1]):
    line = line.rstrip('\n')
    if line.startswith('-- step'):
        f = line.split(); cur = {'tag': f[f.index('tag')+1], 'utc': f[f.index('utc')+1], 'W': [], 'M': {}}; out.append(cur)
    elif cur is None: continue
    elif line.startswith('M,'):
        p = line.split(',', 2); cur['M'][p[1]] = p[2]
    elif line.startswith('W,'):
        p = line.split(','); cur['W'].append((int(p[1]), p[2], int(p[3]), int(p[6]), int(p[7]), int(p[8])))
for c in out:
    if c['M'].get('plan.size') != size or c['M'].get('plan.kernel') == 'oldread': continue
    s = ' '.join('%s%.1f@%.1f' % ('|' if (ph == 'prefix' and w == 0) else '', b/(e-st), st/1e9) for t, ph, w, b, st, e in c['W'])
    print('%-22s %s cpu%s %s' % (c['tag'], c['utc'], c['M'].get('cpu'), s))
