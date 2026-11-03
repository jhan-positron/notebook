#!/usr/bin/env python3
"""analyze_writepath.py - rates from run_sudo.sh part 5 (writepath.csv): per 64 B line, per second,
and per mesh cycle where a cycle counter was in the same set.
Each case (tag) and set (label) has a short and a long run; rate = (long - short) counts over
(long - short) lines, minus the idle rate times the interval difference, as in subtract.py.
Event names may contain commas (bynodeid=1,nodeid=0x98), so perf rows are parsed from both ends.
Checks: every counter ran 100 %, both runs present, long moved more bytes, idle control present.
Exit 1 if any check fails. Usage: analyze_writepath.py <results dir>/writepath.csv"""
import sys, re, collections
f = sys.argv[1]
blocks, cur = [], None
for L in open(f):
    L = L.rstrip('\n')
    m = re.match(r'-- (\S+) (short|long) set (\S+) events', L)
    if m:
        cur = dict(tag=m.group(1), len=m.group(2), label=m.group(3), bytes=None, counts={}, bad=[]); blocks.append(cur); continue
    m = re.match(r'-- idle set (\S+) events', L)
    if m:
        cur = dict(tag='idle', len='idle', label=m.group(1), counts={}, bad=[]); blocks.append(cur); continue
    if L.startswith('-- background'): cur = None; continue
    if cur is None: continue
    p = L.split(',')
    if len(p) >= 7 and p[3] == '0' and p[0] in ('asmwrite', 'asmread', 'read', 'write', 'copy', 'asmcopy'):
        cur['bytes'] = int(p[4]); cur['gbps'] = float(p[6]); continue
    if len(p) >= 7 and p[-1] == '' and p[-2] == '' and '/' in L:
        name = ','.join(p[2:-4]); cnt, rt, pct = p[0], p[-4], p[-3]
        if cnt.isdigit() and rt.isdigit(): cur['counts'][name] = (int(cnt), int(rt) / 1e9, float(pct))
        else: cur['bad'].append(name + ':' + cnt)
idle = {}
for b in blocks:
    if b['tag'] == 'idle':
        for ev, (c, t, pct) in b['counts'].items():
            if pct >= 99.9: idle[ev] = c / t
by = collections.defaultdict(dict)
for b in blocks:
    if b['tag'] != 'idle': by[(b['tag'], b['label'])][b['len']] = b
fail, out = [], collections.defaultdict(dict)
def short(ev):
    ev = ev.replace(',bynodeid=1,nodeid=0x98', '@xp98')
    return ev.replace('armv8_pmuv3_0/', 'core/').replace('arm_cmn_', 'mesh')
print(f"{'case':14} {'set':8} {'event':46} {'per line':>9} {'per s':>12} {'per cycle':>10} {'GB/s':>6}")
for (tag, label), d in sorted(by.items()):
    if 'short' not in d or 'long' not in d: fail.append(f'{tag} {label}: missing short or long run'); continue
    s, l = d['short'], d['long']
    for blk in (s, l):
        for bad in blk['bad']: fail.append(f"{tag} {label} {blk['len']}: uncounted row {bad}")
    if not s.get('bytes') or not l.get('bytes') or l['bytes'] <= s['bytes']: fail.append(f'{tag} {label}: bad byte totals'); continue
    dlines = (l['bytes'] - s['bytes']) / 64
    rates = {}
    for ev in l['counts']:
        if ev not in s['counts']: fail.append(f'{tag} {label} {ev}: missing in short run'); continue
        (cl, tl, pl), (cs, ts, ps) = l['counts'][ev], s['counts'][ev]
        if pl < 99.9 or ps < 99.9: fail.append(f'{tag} {label} {ev}: multiplexed ({ps:.0f} % / {pl:.0f} %)')
        if ev not in idle: fail.append(f'{tag} {label} {ev}: no idle control'); bg = 0.0
        else: bg = idle[ev] * (tl - ts)
        dt = tl - ts
        rates[ev] = ((cl - cs - bg) / dlines, (cl - cs - bg) / dt if dt > 0 else float('nan'), cl - cs - bg)
    cyc = next((rates[e][2] for e in rates if e.endswith('/dtc_cycles/') or e.endswith('/cycles/')), None)
    for ev, (pl_, ps_, raw) in rates.items():
        pc = f'{raw / cyc:10.4f}' if cyc and not (ev.endswith('/dtc_cycles/') or ev.endswith('/cycles/')) else ' ' * 10
        print(f"{tag:14} {label:8} {short(ev):46} {pl_:9.3f} {ps_:12.4g} {pc} {l['gbps']:6.1f}")
        out[tag][short(ev)] = (pl_, ps_, raw / cyc if cyc else None)
if not by: fail.append('no measurement pairs in the file')
print('checks failed:', len(set(fail)))
for x in sorted(set(fail))[:40]: print('  ', x)
sys.exit(1 if fail else 0)
