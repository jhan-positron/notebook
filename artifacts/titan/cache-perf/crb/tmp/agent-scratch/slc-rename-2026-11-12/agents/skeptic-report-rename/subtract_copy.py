#!/usr/bin/env python3
"""subtract.py - rates per cache line from the short/long counter runs of run_sudo.sh parts 3 and 4.
Reads writebw.csv or crossmesh.csv. For each case (tag) and declared event set: rate =
(long count - short count) / (long lines - short lines), lines = total_bytes / 64 from the
bandwidth tool's rep-0 row, minus the idle background rate scaled by the interval difference.
Checks (each failure is listed and makes the exit status 1): every declared event present as a
numeric count on both meshes in both runs; every counter ran 100 % of its interval; the long run
moved more bytes than the short one; a numeric idle control exists for every event (a rate without
one is printed with bg=none and counts as a failure)."""
import sys, re, collections
f = sys.argv[1]
blocks = []
cur = None
for L in open(f):
    L = L.rstrip('\n')
    m = re.match(r'-- (\S+) (short|long) events (\S+) args', L)
    if m:
        cur = dict(tag=m.group(1), len=m.group(2), events=m.group(3).split(','), bytes=None, counts={}, bad=[]); blocks.append(cur); continue
    if L.startswith('-- background'):
        cur = dict(tag='idle', len='idle', events=[], counts={}, bad=[]); blocks.append(cur); continue
    p = L.split(',')
    if cur is None: continue
    if len(p) >= 7 and p[3] == '0' and p[0] in ('asmwrite', 'asmread', 'read', 'write', 'copy', 'asmcopy'):
        cur['bytes'] = int(p[4]); cur['gbps'] = float(p[6])
    elif len(p) >= 5 and '/' in p[2]:
        if p[0].isdigit() and p[3].isdigit():
            cur['counts'][p[2]] = (int(p[0]), float(p[3]) / 1e9, float(p[4]))
        else:
            cur['bad'].append(p[2] + ':' + p[0])
idle = {}
for b in blocks:
    if b['tag'] == 'idle':
        for ev, (c, t, pct) in b['counts'].items():
            if pct >= 99.9: idle[ev] = c / t
by = collections.defaultdict(dict)
for b in blocks:
    if b['tag'] != 'idle': by[(b['tag'], tuple(b['events']))][b['len']] = b
fail = []
print(f"{'case':28} {'event':44} {'per line':>9} {'bg/line':>8} {'GB/s long':>9}")
for (tag, events), d in sorted(by.items()):
    if 'short' not in d or 'long' not in d: fail.append(f'{tag} {events}: missing short or long run'); continue
    s, l = d['short'], d['long']
    for blk in (s, l):
        for bad in blk['bad']: fail.append(f"{tag} {blk['len']}: uncounted row {bad}")
    if not s.get('bytes') or not l.get('bytes') or l['bytes'] <= s['bytes']: fail.append(f'{tag}: bad byte totals'); continue
    dlines = (l['bytes'] - s['bytes']) / 64
    for e in events:
        for mesh in (0, 1):
            ev = f'arm_cmn_{mesh}/{e}/'
            if ev not in l['counts'] or ev not in s['counts']: fail.append(f'{tag} {ev}: counter missing in short or long run'); continue
            (cl, tl, pl), (cs, ts, ps) = l['counts'][ev], s['counts'][ev]
            if pl < 99.9 or ps < 99.9: fail.append(f'{tag} {ev}: multiplexed ({ps:.0f} % / {pl:.0f} %)')
            if ev in idle:
                bg = idle[ev] * (tl - ts) / dlines; bgs = f'{bg:8.4f}'
            else:
                bg = 0.0; bgs = '    none'; fail.append(f'{tag} {ev}: no idle control measured')
            print(f"{tag:28} {ev:44} {(cl - cs) / dlines - bg:9.3f} {bgs} {l['gbps']:9.1f}")
if not by: fail.append('no measurement pairs in the file')
print('checks failed:', len(fail))
for x in sorted(set(fail))[:40]: print('  ', x)
if len(set(fail)) > 40: print('   ...')
sys.exit(1 if fail else 0)
