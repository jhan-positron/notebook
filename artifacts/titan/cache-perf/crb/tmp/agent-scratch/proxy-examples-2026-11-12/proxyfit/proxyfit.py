#!/usr/bin/env python3
"""proxyfit.py - place the latency minimum of each home node on the reader's mesh.

For each reader mesh A (the cores whose fitted crosspoint in core-positions.json is on mesh A) and
each of the 128 home nodes, fit
    latency(reader crosspoint) = intercept + slope * manhattan(candidate, reader crosspoint)
with one point per reader crosspoint (the smaller ns_median of the cores fitted to that crosspoint,
the same "min" reduction fitpos.py uses on the slice side). Candidates are the 32 crosspoints that
carry home nodes (nodes.csv). Keep slope > 0 only. The best candidate is the smallest RMS residual.
Fits are done per node (dev 0 and dev 1 separately) and per crosspoint (min of the two devs).
Nodes on the reader's own mesh are the control: their true crosspoint is in nodes.csv.

Inputs (read only): <R>/full/latency.csv, <R>/full/nodes.csv, <R>/core-positions.json
Output: proxy-positions.json beside this script, and a text report on stdout.
Usage: proxyfit.py <R>
"""
import csv, json, sys, os, collections, statistics as st
R = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
AMBIG = 0.3      # ns RMS: runner-up closer than this = ambiguous
TIE = 1e-9

pos = {int(c): (p['mesh'], p['x'], p['y']) for c, p in json.load(open(f'{R}/core-positions.json'))['pos'].items()}
nodes = [(int(r['mesh']), r['node_id_hex'], int(r['x']), int(r['y']), int(r['dev'])) for r in csv.DictReader(open(f'{R}/full/nodes.csv'))]
HNXP = {m: sorted({(x, y) for mm, _, x, y, _ in nodes if mm == m}) for m in (0, 1)}
assert HNXP[0] == HNXP[1]
CAND = HNXP[0]
# lat[(mesh,node)][core] = ns_median
lat = collections.defaultdict(dict)
for r in csv.DictReader(open(f'{R}/full/latency.csv')):
    if r['node_id_hex'] == 'mixed': continue
    lat[(int(r['mesh']), r['node_id_hex'])][int(r['core'])] = float(r['ns_median'])
readers = {m: collections.defaultdict(list) for m in (0, 1)}
for c, (m, x, y) in pos.items(): readers[m][(x, y)].append(c)

def linfit(pts):
    n = len(pts); mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts); sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    if sxx == 0: return None
    b = sxy / sxx; a = my - b * mx
    return a, b, (sum((v - (a + b * d)) ** 2 for d, v in pts) / n) ** 0.5

def place(vals, cands=CAND):
    """vals: {(x,y) reader crosspoint: ns}. Returns ranked list of (rms, cand, intercept, slope)."""
    out = []
    for (cx, cy) in cands:
        f = linfit([(abs(x - cx) + abs(y - cy), v) for (x, y), v in vals.items()])
        if f is None or f[1] <= 0: continue
        out.append((f[2], (cx, cy), f[0], f[1]))
    out.sort()
    return out

def summarize(vals, cands=CAND):
    rk = place(vals, cands)
    best = rk[0]
    ties = [c for r, c, _, _ in rk if r - best[0] < TIE]
    rest = [t for t in rk if t[0] - best[0] >= TIE]
    ru = rest[0] if rest else None
    mean = sum(vals.values()) / len(vals)
    flat = (sum((v - mean) ** 2 for v in vals.values()) / len(vals)) ** 0.5
    return dict(best=list(best[1]), ties=[list(c) for c in ties], rms=round(best[0], 4), slope=round(best[3], 4),
                intercept=round(best[2], 4), flat_rms=round(flat, 4),
                runner_up=list(ru[1]) if ru else None, runner_up_rms=round(ru[0], 4) if ru else None,
                gap=round(ru[0] - best[0], 4) if ru else None,
                ambiguous=bool(len(ties) > 1 or (ru and ru[0] - best[0] < AMBIG)),
                min_ns=round(min(vals.values()), 2), max_ns=round(max(vals.values()), 2))

def xpvals(A, keys, per_core=False):
    """latency per reader crosspoint of mesh A for the given node keys (min over cores and nodes)."""
    v = {}
    for xp, cores in readers[A].items():
        xs = [lat[k][c] for k in keys for c in cores if c in lat[k]]
        if xs: v[xp] = min(xs)
    return v

res = dict(method=__doc__, inputs=[f'{R}/full/latency.csv', f'{R}/full/nodes.csv', f'{R}/core-positions.json'],
           candidates=[list(c) for c in CAND], ambiguous_threshold_ns=AMBIG,
           reader_crosspoints={str(m): sorted(list(k) for k in readers[m]) for m in (0, 1)},
           reader_cores={str(m): sum(len(v) for v in readers[m].values()) for m in (0, 1)}, per_node=[], per_xp=[])
for A in (0, 1):
    for m, nid, x, y, dev in nodes:
        s = summarize(xpvals(A, [(m, nid)]))
        s.update(reader_mesh=A, home_mesh=m, node=nid, home_xp=[x, y], dev=dev, kind='local' if m == A else 'remote')
        res['per_node'].append(s)
    for m in (0, 1):
        for xp in CAND:
            keys = [(m, nid) for mm, nid, x, y, _ in nodes if mm == m and (x, y) == xp]
            s = summarize(xpvals(A, keys))
            s.update(reader_mesh=A, home_mesh=m, home_xp=list(xp), kind='local' if m == A else 'remote')
            res['per_xp'].append(s)
json.dump(res, open(f'{HERE}/proxy-positions.json', 'w'), indent=1)

P = print
def med(x): return st.median(x)
P('reader crosspoints: mesh0 %d (%d cores), mesh1 %d (%d cores)' % (len(readers[0]), res['reader_cores']['0'], len(readers[1]), res['reader_cores']['1']))
P('candidate crosspoints (home-node XPs):', len(CAND))
P('core XPs absent on mesh 1 but present on mesh 0:', sorted(set(readers[0]) - set(readers[1])))
P('home-node XPs with no reader XP: mesh0', sorted(set(CAND) - set(readers[0])), 'mesh1', sorted(set(CAND) - set(readers[1])))
P('reader XPs with no home node: mesh0', sorted(set(readers[0]) - set(CAND)), 'mesh1', sorted(set(readers[1]) - set(CAND)))

P('\n== (a) fit quality ==')
for level in ('per_node', 'per_xp'):
    for A in (0, 1):
        for kind in ('local', 'remote'):
            rows = [s for s in res[level] if s['reader_mesh'] == A and s['kind'] == kind]
            line = '%-8s reader mesh %d %-6s n=%2d rms med %.3f worst %.3f | flat-model rms med %.3f | slope med %.3f min %.3f max %.3f | ambiguous %d (exact ties %d)' % (
                level, A, kind, len(rows), med(s['rms'] for s in rows), max(s['rms'] for s in rows), med(s['flat_rms'] for s in rows),
                med(s['slope'] for s in rows), min(s['slope'] for s in rows), max(s['slope'] for s in rows),
                sum(s['ambiguous'] for s in rows), sum(len(s['ties']) > 1 for s in rows))
            if kind == 'local':
                ok = sum(s['best'] == s['home_xp'] and len(s['ties']) == 1 for s in rows)
                intie = sum(s['home_xp'] in s['ties'] for s in rows)
                ok_un = sum(s['best'] == s['home_xp'] and not s['ambiguous'] for s in rows)
                line += ' | true XP recovered uniquely %d, true XP in tie set %d, recovered and unambiguous %d' % (ok, intie, ok_un)
            P(line)
P('local misses (per_node):')
for s in res['per_node']:
    if s['kind'] == 'local' and not (s['best'] == s['home_xp'] and len(s['ties']) == 1):
        P('  reader %d node %s true %s best %s ties %s rms %.3f runner-up %s %.3f' % (s['reader_mesh'], s['node'], s['home_xp'], s['best'], s['ties'], s['rms'], s['runner_up'], s['runner_up_rms']))
P('local misses (per_xp):')
for s in res['per_xp']:
    if s['kind'] == 'local' and not (s['best'] == s['home_xp'] and len(s['ties']) == 1):
        P('  reader %d true %s best %s ties %s rms %.3f runner-up %s %.3f' % (s['reader_mesh'], s['home_xp'], s['best'], s['ties'], s['rms'], s['runner_up'], s['runner_up_rms']))
P('local hop error of best vs true (per_node), histogram of manhattan error:')
for A in (0, 1):
    P('  reader', A, sorted(collections.Counter(min(abs(t[0] - s['home_xp'][0]) + abs(t[1] - s['home_xp'][1]) for t in s['ties']) for s in res['per_node'] if s['kind'] == 'local' and s['reader_mesh'] == A).items()))

P('\n== (b) table: home XP on mesh B -> proxy XP on mesh A (per_xp fit, min of dev 0/1) ==')
P('reader home  home_xp -> proxy   rms  slope  flat | runner-up  rms   gap  amb ties | dev0   dev1')
pn = {(s['reader_mesh'], s['home_mesh'], tuple(s['home_xp']), s['dev']): s for s in res['per_node']}
for s in res['per_xp']:
    if s['kind'] != 'remote': continue
    d0 = pn[(s['reader_mesh'], s['home_mesh'], tuple(s['home_xp']), 0)]; d1 = pn[(s['reader_mesh'], s['home_mesh'], tuple(s['home_xp']), 1)]
    P('  %d     %d   (%d,%d) -> (%d,%d) %6.3f %5.2f %5.2f | (%d,%d) %6.3f %5.3f %s %s | (%d,%d)%s (%d,%d)%s' % (
        s['reader_mesh'], s['home_mesh'], *s['home_xp'], *s['best'], s['rms'], s['slope'], s['flat_rms'], *s['runner_up'], s['runner_up_rms'], s['gap'],
        'AMB' if s['ambiguous'] else '   ', s['ties'] if len(s['ties']) > 1 else '', *d0['best'], '*' if d0['ambiguous'] else ' ', *d1['best'], '*' if d1['ambiguous'] else ' '))

P('\n== (c) do dev 0 and dev 1 of one home XP map to the same proxy XP? ==')
for A in (0, 1):
    same = both = same_un = diff_un = tieov = 0; diffs = []
    for xp in CAND:
        d0 = pn[(A, 1 - A, xp, 0)]; d1 = pn[(A, 1 - A, xp, 1)]
        same += d0['best'] == d1['best']
        tieov += bool({tuple(t) for t in d0['ties']} & {tuple(t) for t in d1['ties']})
        if not d0['ambiguous'] and not d1['ambiguous']:
            both += 1; same_un += d0['best'] == d1['best']; diff_un += d0['best'] != d1['best']
        if d0['best'] != d1['best']: diffs.append((xp, d0['best'], d0['rms'], d0['gap'], d1['best'], d1['rms'], d1['gap']))
    P('reader mesh %d: same best %d of 32; tie sets overlap %d of 32; both unambiguous %d, of those same %d, different %d' % (A, same, tieov, both, same_un, diff_un))
    for d in diffs: P('   differ: home', d[0], 'dev0 ->', d[1], 'rms %.3f gap %.3f' % d[2:4], 'dev1 ->', d[4], 'rms %.3f gap %.3f' % d[5:7])
P('control, local nodes: dev0 and dev1 same best:', [sum(pn[(A, A, xp, 0)]['best'] == pn[(A, A, xp, 1)]['best'] for xp in CAND) for A in (0, 1)], 'of 32 each')

P('\n== (d) mapping properties (per_xp fit) ==')
mp = {A: {tuple(s['home_xp']): s for s in res['per_xp'] if s['reader_mesh'] == A and s['kind'] == 'remote'} for A in (0, 1)}
RULES = {'identity': lambda x, y: (x, y), 'mirror_x (8-x,y)': lambda x, y: (8 - x, y), 'mirror_y (x,6-y)': lambda x, y: (x, 6 - y),
         'rot180 (8-x,6-y)': lambda x, y: (8 - x, 6 - y), 'transpose (y,x)': lambda x, y: (y, x)}
for A in (0, 1):
    m = mp[A]
    img = collections.Counter(tuple(s['best']) for s in m.values())
    un = {k: s for k, s in m.items() if not s['ambiguous']}
    imgu = collections.Counter(tuple(s['best']) for s in un.values())
    P('reader mesh %d: 32 home XPs -> %d distinct proxy XPs (one-to-one: %s); max homes on one proxy %d; unambiguous entries %d -> %d distinct' % (
        A, len(img), len(img) == 32, max(img.values()), len(un), len(imgu)))
    P('   proxies used more than once:', {k: v for k, v in img.items() if v > 1})
    P('   home-node XPs never chosen as proxy:', sorted(set(CAND) - set(img)))
    for name, f in RULES.items():
        P('   rule %-18s matches all %2d/32, unambiguous %2d/%d, rule target is a home-node XP for %d/32, in tie set %d/32' % (
            name, sum(tuple(s['best']) == f(*k) for k, s in m.items()), sum(tuple(s['best']) == f(*k) for k, s in un.items()), len(un),
            sum(f(*k) in CAND for k in m), sum(list(f(*k)) in s['ties'] for k, s in m.items())))
    # exhaustive: proxy = (sx*x+ax, sy*y+ay) and transposed forms
    best = []
    for tr in (0, 1):
        for sx in (1, -1):
            for sy in (1, -1):
                for ax in range(-8, 17):
                    for ay in range(-8, 17):
                        def f(x, y):
                            if tr: x, y = y, x
                            return (sx * x + ax, sy * y + ay)
                        best.append((sum(tuple(s['best']) == f(*k) for k, s in m.items()), tr, sx, ax, sy, ay))
    best.sort(reverse=True)
    P('   best of all sign/offset/transpose rules (matches, transpose, sx, ax, sy, ay):', best[:4])
    # per-axis: correlation of proxy x with home x etc.
    def corr(a, b):
        ma = sum(a) / len(a); mb = sum(b) / len(b)
        den = (sum((i - ma) ** 2 for i in a) * sum((j - mb) ** 2 for j in b)) ** 0.5
        return sum((i - ma) * (j - mb) for i, j in zip(a, b)) / den if den else float('nan')
    ks = list(m)
    P('   Pearson r over 32: proxy x vs home x %.3f, proxy y vs home y %.3f, proxy x vs home y %.3f, proxy y vs home x %.3f' % (
        corr([m[k]['best'][0] for k in ks], [k[0] for k in ks]), corr([m[k]['best'][1] for k in ks], [k[1] for k in ks]),
        corr([m[k]['best'][0] for k in ks], [k[1] for k in ks]), corr([m[k]['best'][1] for k in ks], [k[0] for k in ks])))
    P('   grid (rows y=5..1, cols x=1..7): proxy XP chosen for the home XP at that place, * = ambiguous')
    for y in range(5, 0, -1):
        P('     ' + ' '.join(('(%d,%d)%s' % (*m[(x, y)]['best'], '*' if m[(x, y)]['ambiguous'] else ' ')) if (x, y) in m else '  .   ' for x in range(1, 8)))
both_un = [k for k in CAND if not mp[0][k]['ambiguous'] and not mp[1][k]['ambiguous']]
P('same proxy XP for reader mesh 0 and reader mesh 1: all %d/32; where both unambiguous %d/%d' % (
    sum(mp[0][k]['best'] == mp[1][k]['best'] for k in CAND), sum(mp[0][k]['best'] == mp[1][k]['best'] for k in both_un), len(both_un)))
P('   tie sets overlap between reader meshes: %d/32' % sum(bool({tuple(t) for t in mp[0][k]['ties']} & {tuple(t) for t in mp[1][k]['ties']}) for k in CAND))
P('   differing (home XP: reader0 proxy, reader1 proxy):', [(k, tuple(mp[0][k]['best']), tuple(mp[1][k]['best'])) for k in both_un if mp[0][k]['best'] != mp[1][k]['best']])
# inverse check: is mapping for reader 1 the inverse of mapping for reader 0?
inv = sum(tuple(mp[1].get(tuple(mp[0][k]['best']), {'best': None})['best'] or ()) == k for k in CAND)
P('   involution check: proxy_reader1(proxy_reader0(h)) == h for %d/32' % inv)

P('\n== (e) ambiguous entries (runner-up within %.1f ns RMS or exact tie), per_xp remote ==' % AMBIG)
for A in (0, 1):
    for k, s in mp[A].items():
        if s['ambiguous']:
            P('  reader %d home %s best %s rms %.3f runner-up %s rms %.3f gap %.4f ties %s slope %.2f' % (A, k, s['best'], s['rms'], s['runner_up'], s['runner_up_rms'], s['gap'], s['ties'], s['slope']))
P('counts per_node remote ambiguous: reader0 %d/64, reader1 %d/64' % tuple(sum(s['ambiguous'] for s in res['per_node'] if s['kind'] == 'remote' and s['reader_mesh'] == A) for A in (0, 1)))
P('counts per_node remote ambiguous by cause: exact tie %s, near (gap<0.3, no tie) %s' % (
    [sum(len(s['ties']) > 1 for s in res['per_node'] if s['kind'] == 'remote' and s['reader_mesh'] == A) for A in (0, 1)],
    [sum(len(s['ties']) == 1 and s['ambiguous'] for s in res['per_node'] if s['kind'] == 'remote' and s['reader_mesh'] == A) for A in (0, 1)]))

P('\n== (d2) is the reader-mesh-1 map the inverse of the reader-mesh-0 map? ==')
# reader 0: home h on mesh 1 -> proxy p on mesh 0. Inverse prediction for reader 1: home p on mesh 0 -> proxy h on mesh 1.
invpred = {tuple(mp[0][h]['best']): h for h in CAND}
P('inverse prediction equals reader-1 best: %d/32; lies in reader-1 tie set: %d/32; equals best among the %d unambiguous reader-1 entries: %d' % (
    sum(tuple(mp[1][p]['best']) == invpred[p] for p in CAND), sum(list(invpred[p]) in mp[1][p]['ties'] for p in CAND),
    sum(not mp[1][p]['ambiguous'] for p in CAND), sum(tuple(mp[1][p]['best']) == invpred[p] for p in CAND if not mp[1][p]['ambiguous'])))
for p in CAND:
    if mp[1][p]['ambiguous']: P('   reader 1 home', p, 'tie set', mp[1][p]['ties'], 'inverse of reader-0 map says', invpred[p])
P('reader-0 map applied twice returns to start (self-inverse on coordinates) for %d/32' % sum(tuple(mp[0][tuple(mp[0][h]['best'])]['best']) == h for h in CAND))
for s in res['per_xp']:
    if s['reader_mesh'] == 1 and s['kind'] == 'remote': s['inverse_of_reader0_map'] = list(invpred[tuple(s['home_xp'])])
json.dump(res, open(f'{HERE}/proxy-positions.json', 'w'), indent=1)

P('\n== sensitivity ==')
ALL72 = [(x, y) for x in range(9) for y in range(8)]
C35 = [(x, y) for y in range(1, 6) for x in range(1, 8)]
for A in (0, 1):
    for name, cands in (('35 core-port candidates (fitpos.py set)', C35), ('all 72 crosspoints', ALL72)):
        same = tie = 0; tiesz = []
        for h in CAND:
            keys = [(1 - A, nid) for mm, nid, x, y, _ in nodes if mm == 1 - A and (x, y) == h]
            s = summarize(xpvals(A, keys), cands)
            same += mp[A][h]['best'] in s['ties']; tie += len(s['ties']) > 1; tiesz.append(len(s['ties']))
        P('reader %d remote, %s: 32-candidate best is in the best tie set for %d/32; entries with exact ties %d (max tie size %d)' % (A, name, same, tie, max(tiesz)))
    # one point per core instead of min per crosspoint
    same = 0; rms = []
    for h in CAND:
        keys = [(1 - A, nid) for mm, nid, x, y, _ in nodes if mm == 1 - A and (x, y) == h]
        pts = {}
        for c, (m, x, y) in pos.items():
            if m != A: continue
            pts[c] = ((x, y), min(lat[k][c] for k in keys))
        rk = []
        for (cx, cy) in CAND:
            f = linfit([(abs(x - cx) + abs(y - cy), v) for (x, y), v in pts.values()])
            if f and f[1] > 0: rk.append((f[2], (cx, cy)))
        rk.sort(); t = [list(c) for r, c in rk if r - rk[0][0] < TIE]
        same += mp[A][h]['best'] in t; rms.append(rk[0][0])
    P('reader %d remote, one point per core (%d points): same best (within tie set) %d/32, rms med %.3f worst %.3f' % (A, len(pts), same, med(rms), max(rms)))
P('latency at the best-fit proxy XP vs at the true XP for local nodes (per_node min_ns): remote med %.2f, local med %.2f (reader 0); remote med %.2f, local med %.2f (reader 1)' % tuple(
    med(s['min_ns'] for s in res['per_node'] if s['reader_mesh'] == A and s['kind'] == k) for A in (0, 1) for k in ('remote', 'local')))
P('fitted intercept (ns at 0 hops): ' + '; '.join('reader %d %s med %.2f' % (A, k, med(s['intercept'] for s in res['per_node'] if s['reader_mesh'] == A and s['kind'] == k)) for A in (0, 1) for k in ('local', 'remote')))
