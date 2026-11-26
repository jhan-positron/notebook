#!/usr/bin/env python3
"""Check Figure 2 panels against raw: every dot (value, tooltip metadata, cx), row range labels, bands."""
import re, sys, html
import data3 as d, raw3
from data3 import BW, sel, med, R
N = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/numbers/r3'
bad = 0
def chk(c, msg):
    global bad
    if not c: bad += 1; print('  MISMATCH:', msg)
def f2(x): return '%.2f' % x
# ---- index raw intervals by (path, line)
IDX = {}
PROCNAME = {'L-1': 'a6456', 'L-2a': 'p1nop', 'L-2b': 'p2add', 'L-3': 'thp', 'L-4a': 'st1', 'L-4b': 'st2', 'L-4c': 'st3', 'F72d12': 'a6456'}
for k, ivs in BW.items():
    for n, i in enumerate(ivs):
        prev = ivs[n - 1]['kernel'] if n > 0 else None
        IDX[(i['path'].replace(R, 'R'), i['I_line'])] = dict(v=i['total'], kernel=i['kernel'], round=i['round'], pos=i['pos'], prev=prev, proc=PROCNAME.get(k, k), key=k)
def add_bw(procs, hdrfn, nm):
    # ordinal of process in the file
    for n, p in enumerate(procs, 1):
        for j, i in enumerate(p['iv'], 1):
            IDX[(p['path'].replace(R, 'R'), i['line'])] = dict(v=i['agg'], kernel=p['kernel'], binary=p['binary'], round=p.get('round'), ordinal=n, interval=j, tag=p.get('tag'), key=nm, min_ms=p.get('min_ms'))
for s in (1, 2, 3): add_bw(d.A72[s], None, 'A72-%d' % s)
add_bw(d.A1, None, 'A-1')
for p in d.A2: p['round'] = int(p['tag'][-1])
add_bw(d.A2, None, 'A-2'); add_bw(d.A3, None, 'A-3')

def keys_bw(procs, kern, pos=None, rnd=None):
    return [(i['path'].replace(R, 'R'), i['I_line']) for k in procs for i in sel(BW[k], kern, pos, rnd)]
def keys_a(procs, binary, rnd):
    p = [x for x in procs if x['binary'] == binary and x['kernel'] == 'read' and x['round'] == rnd and x.get('min_ms', '500') == '500' and (x.get('tag') is None or not x['tag'].startswith('twobuf'))]
    assert len(p) == 1, (binary, rnd, len(p))
    return [(p[0]['path'].replace(R, 'R'), i['line']) for i in p[0]['iv']]
def keys_a3():
    return [(d.a3(n)['path'].replace(R, 'R'), i['line']) for n in (1, 2, 3) for i in d.a3(n)['iv']]
LP = ('L-1', 'L-2a', 'L-2b', 'L-3', 'L-4a', 'L-4b', 'L-4c')
OLD = [  # (row title prefix regex, expected keys, nproc, band-id)
 ('L-1:', keys_bw(['L-1'], 'oldread', 0), 1), ('L-2:', keys_bw(['L-2a', 'L-2b'], 'oldread', 0), 2), ('L-3:', keys_bw(['L-3'], 'oldread', 0), 1),
 ('L-4:', keys_bw(['L-4a', 'L-4b', 'L-4c'], 'oldread', 0), 3), ('F72d12,', keys_bw(['F72d12'], 'oldread', 0), 1),
 ('Part L,', keys_bw(['T72L1', 'T72L2', 'T72L3'], 'oldread', 0), 3), ('Part C,', keys_bw(['T72C1', 'T72C2', 'T72C3', 'T72C4'], 'oldread'), 4),
 ('Control I,', keys_bw(['T72I1', 'T72I2'], 'oldread', 0), 2),
 ('A-1:', keys_a(d.A1, 'bw_old', 1) + keys_a(d.A1, 'bw_old', 2), 2), ('A-2:', keys_a(d.A2, 'bw_old', 1) + keys_a(d.A2, 'bw_old', 2), 2), ('A-3:', keys_a3(), 3),
] + [('Part A, session %d,' % s, keys_a(d.A72[s], 'bw_old', 1) + keys_a(d.A72[s], 'bw_old', 2), 2) for s in (1, 2, 3)]
LO = [
 ('L-1:', keys_bw(['L-1'], 'asmread', 1), 1), ('L-2:', keys_bw(['L-2a', 'L-2b'], 'asmread', 1), 2), ('L-3:', keys_bw(['L-3'], 'asmread', 1), 1),
 ('L-4:', keys_bw(['L-4a', 'L-4b', 'L-4c'], 'asmread', 1), 3), ('F72d12,', keys_bw(['F72d12'], 'asmread', 1), 1),
 ('Part L,', keys_bw(['T72L1', 'T72L2', 'T72L3'], 'asmread', 1), 3),
 ('Part C, asmread directly after oldread', keys_bw(['T72C2', 'T72C4'], 'asmread', 0, 1), 2),
 ('Control I,', keys_bw(['T72I1', 'T72I2'], 'asmread', 1), 2),
 ('Part C, read directly after oldread', keys_bw(['T72C1', 'T72C3'], 'read', 1), 2),
 ('Part C, read directly after asmread', keys_bw(['T72C2', 'T72C4'], 'read', 1), 2),
 ('Part C, asmread directly after read', keys_bw(['T72C1', 'T72C3'], 'asmread', 2), 2),
 ('Part C, asmread as first interval', keys_bw(['T72C2', 'T72C4'], 'asmread', 0, 0), 2),
]
for r in (1, 2):
    LO += [('A-1, round %d:' % r, keys_a(d.A1, 'bw_new', r), 1), ('A-2, round %d:' % r, keys_a(d.A2, 'bw_new', r), 1)]
    LO += [('Part A, session %d, round %d,' % (s, r), keys_a(d.A72[s], 'bw_new', r), 1) for s in (1, 2, 3)]

def run(fn, ROWS, axis_start):
    global bad
    s = open(N + '/' + fn).read()
    ticks = {}
    for m in re.finditer(r'<text x="([\d.]+)" y="[\d.]+" font-size="11.5" fill="#52514e" text-anchor="middle"[^>]*>(\d+)</text>', s):
        ticks[int(m.group(2))] = float(m.group(1))
    lo, hi = min(ticks), max(ticks)
    k = (ticks[hi] - ticks[lo]) / (hi - lo); X = lambda v: ticks[lo] + (v - lo) * k
    print(fn, 'ticks', sorted(ticks.items()), 'px per GB/s %.4f' % k, 'x at axis start %s: %.2f' % (axis_start, X(axis_start)))
    for t in ticks: chk(abs(ticks[t] - X(t)) < 0.06, 'tick %s' % t)
    chk(('The axis starts at %d GB/s, not at 0.' % axis_start) in s, 'axis start note')
    # leftmost grid line = axis start?
    gl = sorted(set(float(x) for x in re.findall(r'<line x1="([\d.]+)" y1="94"', s)))
    print('  grid lines x', gl[:3], '...', gl[-1], '-> values', ['%.2f' % (lo + (g - ticks[lo]) / k) for g in gl])
    seen = {}
    ndots = 0
    for body in re.findall(r'<g class="pt">(.*?)</g>', s, flags=re.S):
        title = html.unescape(re.search(r'<title>(.*?)</title>', body, flags=re.S).group(1))
        ndots += 1
        row = [r for r in ROWS if title.startswith(r[0])]
        chk(len(row) == 1, 'row match %d for %s' % (len(row), title[:90]))
        if len(row) != 1: continue
        row = row[0]
        m = re.search(r'Source: (\S+?),? (?:interval row in )?line (\d+)\.', title)
        chk(m is not None, 'no source in ' + title[-120:])
        key = (m.group(1), int(m.group(2)))
        chk(key in row[1], '%s: source %s not in expected row set' % (row[0], key))
        e = IDX.get(key)
        chk(e is not None, 'source %s not an interval row' % (key,))
        if e is None: continue
        chk(key not in seen, 'duplicate dot %s' % (key,)); seen[key] = row[0]
        vm = re.search(r': ([\d.]+) GB/s\. Row: ([\d.]+) to ([\d.]+) GB/s, n = (\d+) intervals? / (\d+) process', title)
        chk(vm is not None, 'no value in ' + title[:200])
        v, rlo, rhi, n, npr = vm.groups()
        chk(v == f2(e['v']), '%s %s value %s raw %s' % (row[0], key, v, f2(e['v'])))
        rv = [IDX[kk]['v'] for kk in row[1]]
        chk(rlo == f2(min(rv)) and rhi == f2(max(rv)), '%s row range %s-%s raw %s-%s' % (row[0], rlo, rhi, f2(min(rv)), f2(max(rv))))
        chk(int(n) == len(rv) and int(npr) == row[2], '%s n %s/%s raw %d/%d' % (row[0], n, npr, len(rv), row[2]))
        cx = [float(x) for x in re.findall(r'<circle[^>]*cx="([\d.]+)"', body)]
        chk(len(set(cx)) == 1 and abs(cx[0] - X(e['v'])) < 0.06, '%s %s cx %s exp %.2f (v %s)' % (row[0], key, cx, X(e['v']), f2(e['v'])))
        if 'pos' in e:
            pm = re.search(r': (\w+) \(([^)]*)\), process (\S+), round (\d), position (\d), (no kernel ran before it|directly after (\w+)(?: \(another test loop of bwx12\))?):', title)
            chk(pm is not None, 'bwx title form: ' + title[:200])
            if pm:
                chk(pm.group(1) == e['kernel'], '%s kernel %s raw %s' % (key, pm.group(1), e['kernel']))
                chk(pm.group(3) == e['proc'], '%s process %s raw %s' % (key, pm.group(3), e['proc']))
                chk(int(pm.group(4)) == e['round'] and int(pm.group(5)) == e['pos'], '%s round/pos %s/%s raw %s/%s' % (key, pm.group(4), pm.group(5), e['round'], e['pos']))
                prev = pm.group(7)
                chk((prev or None) == e['prev'], '%s prev %s raw %s' % (key, prev, e['prev']))
        else:
            pm = re.search(r': (bw_\w+) read \(([^)]*)\), process (\d+) of the file(?: \(tag ([\w-]+)\))?,(?: round (\d),)? interval (\d):', title)
            chk(pm is not None, 'part A title form: ' + title[:200])
            if pm:
                chk(pm.group(1) == e['binary'], '%s binary' % (key,))
                chk(int(pm.group(3)) == e['ordinal'], '%s ordinal %s raw %s' % (key, pm.group(3), e['ordinal']))
                if pm.group(4): chk(pm.group(4) == e['tag'], '%s tag %s raw %s' % (key, pm.group(4), e['tag']))
                if pm.group(5): chk(int(pm.group(5)) == e['round'], '%s round %s raw %s' % (key, pm.group(5), e['round']))
                chk(int(pm.group(6)) == e['interval'], '%s interval %s raw %s' % (key, pm.group(6), e['interval']))
        is8000 = row[0].startswith('L-') or row[0].startswith('A-')
        chk(('class="mk ho"' in body) == is8000, '%s hollow' % row[0])
    exp = set(kk for r in ROWS for kk in r[1])
    chk(set(seen) == exp, 'dot set differs: missing %s extra %s' % (sorted(exp - set(seen))[:5], sorted(set(seen) - exp)[:5]))
    print('  dots', ndots, 'expected', len(exp))
    # bands
    for body in re.findall(r'<g>(.*?)</g>', s, flags=re.S):
        tm = re.search(r'<title>(.*?)</title>', body, flags=re.S)
        if not tm or not tm.group(1).startswith('Grey band'): continue
        t = html.unescape(tm.group(1))
        bm = re.search(r'([\d.]+) to ([\d.]+) GB/s, n = (\d+) intervals / (\d+) processes / 1 boot', t)
        rect = re.search(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)"', body)
        x, w = float(rect.group(1)), float(rect.group(2))
        print('  band:', t[:110], '| rect', x, x + w, '-> %.2f to %.2f' % (lo + (x - ticks[lo]) / k, lo + (x + w - ticks[lo]) / k))
        yield_band.append((fn, t, bm.groups(), x, w, X))
    return X
yield_band = []
run('svg14.txt', OLD, 458)
run('svg15.txt', LO, 276)
# band expectations
def rngk(keys): v = [IDX[k]['v'] for k in keys]; return min(v), max(v), len(v)
bands = {
 ('svg14.txt', 'L-1 to L-4'): (keys_bw(LP, 'oldread', 0), 7), ('svg14.txt', 'A-1 to A-3'): (keys_a(d.A1, 'bw_old', 1) + keys_a(d.A1, 'bw_old', 2) + keys_a(d.A2, 'bw_old', 1) + keys_a(d.A2, 'bw_old', 2) + keys_a3(), 7),
 ('svg15.txt', 'L-1 to L-4'): (keys_bw(LP, 'asmread', 1), 7),
 ('svg15.txt', 'round 1'): (keys_a(d.A1, 'bw_new', 1) + keys_a(d.A2, 'bw_new', 1), 2), ('svg15.txt', 'round 2'): (keys_a(d.A1, 'bw_new', 2) + keys_a(d.A2, 'bw_new', 2), 2),
}
for fn, t, g, x, w, X in yield_band:
    kk = [b for b in bands if b[0] == fn and b[1] in t]
    chk(len(kk) == 1, 'band id ' + t[:80])
    keys, npr = bands[kk[0]]
    a, b, n = rngk(keys)
    chk(g[0] == f2(a) and g[1] == f2(b) and int(g[2]) == n and int(g[3]) == npr, 'band %s text %s raw %s %s %d %d' % (kk[0], g, f2(a), f2(b), n, npr))
    chk(abs(x - X(a)) < 0.06 and abs(x + w - X(b)) < 0.11, 'band %s rect %.1f..%.1f exp %.2f..%.2f' % (kk[0], x, x + w, X(a), X(b)))
print('TOTAL MISMATCHES', bad)
