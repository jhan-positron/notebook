#!/usr/bin/env python3
"""refute.py - independent check of the 'proxy crosspoint' claim. Reads only
full/latency.csv, full/nodes.csv, core-positions.json. Usage: refute.py <results dir>"""
import csv, json, sys, collections, itertools
import numpy as np
R = sys.argv[1]
rng = np.random.default_rng(12345)
pos = {int(c): (p['mesh'], p['x'], p['y']) for c, p in json.load(open(f'{R}/core-positions.json'))['pos'].items()}
nodes = [(int(r['mesh']), int(r['x']), int(r['y']), int(r['dev'])) for r in csv.DictReader(open(f'{R}/full/nodes.csv'))]
HXP = sorted({(x, y) for m, x, y, d in nodes if m == 0})
assert HXP == sorted({(x, y) for m, x, y, d in nodes if m == 1}) and len(HXP) == 32
lat = {}
for r in csv.DictReader(open(f'{R}/full/latency.csv')):
    if r['node_id_hex'] == 'mixed': continue
    lat[(int(r['core']), int(r['mesh']), int(r['x']), int(r['y']), int(r['dev']))] = float(r['ns_median'])
cores = sorted(pos)
print('cores', len(cores), 'core mesh != (cpu<64 ? 0 : 1):', [c for c in cores if (c < 64) != (pos[c][0] == 0)])
RC = {m: [c for c in cores if pos[c][0] == m] for m in (0, 1)}
for m in (0, 1): print('reader mesh', m, 'cores', len(RC[m]), 'distinct XPs', len({pos[c][1:] for c in RC[m]}),
                       'home XPs with no reader:', [h for h in HXP if h not in {pos[c][1:] for c in RC[m]}])
def vec(rm, hm, h):  # latency per reader core, min of two devs
    return np.array([min(lat[(c, hm, h[0], h[1], 0)], lat[(c, hm, h[0], h[1], 1)]) for c in RC[rm]])
def vecd(rm, hm, h, d): return np.array([lat[(c, hm, h[0], h[1], d)] for c in RC[rm]])
def dist(metric, cand, P):
    dx = np.abs(P[:, 0] - cand[0]); dy = np.abs(P[:, 1] - cand[1])
    return {'man': dx + dy, 'euc': np.sqrt(dx * dx + dy * dy), 'cheb': np.maximum(dx, dy)}[metric].astype(float)
def fitone(d, v):
    dm = d - d.mean(); sxx = (dm * dm).sum()
    if sxx == 0: return None
    b = (dm * (v - v.mean())).sum() / sxx; a = v.mean() - b * d.mean()
    return a, b, float(np.sqrt(((v - a - b * d) ** 2).mean()))
def best(v, P, cands=HXP, metric='man'):
    out = []
    for c in cands:
        f = fitone(dist(metric, c, P), v)
        if f and f[1] > 0: out.append((f[2], c, f[0], f[1]))
    out.sort()
    if not out: return (float(v.std()), None, float(v.mean()), 0.0), [], None  # no candidate with slope > 0: constant model
    ties = [o[1] for o in out if o[0] - out[0][0] < 1e-9]
    ru = next((o for o in out if o[0] - out[0][0] >= 1e-9), None)
    return out[0], sorted(ties), ru
PP = {m: np.array([pos[c][1:] for c in RC[m]]) for m in (0, 1)}
fs = lambda t: '|'.join('(%d,%d)' % x for x in t)

print('\n== A. my fit, one point per core, 32 candidates, Manhattan ==')
MAP = {}
for rm in (0, 1):
    for kind, hm in (('local', rm), ('remote', 1 - rm)):
        rms, flat, slope, icpt, gaps, nt = [], [], [], [], [], 0
        for h in HXP:
            v = vec(rm, hm, h); b, ties, ru = best(v, PP[rm])
            MAP[(rm, kind, h)] = (ties, b, ru)
            rms.append(b[0]); flat.append(v.std()); slope.append(b[3]); icpt.append(b[2]); gaps.append(ru[0] - b[0]); nt += len(ties) > 1
        print('reader %d %-6s: RMS med %.3f max %.3f | constant-model RMS med %.3f min %.3f | slope med %.3f (%.3f..%.3f) | intercept med %.2f | tied %d/32 | min gap to non-tied runner-up %.3f | min ratio flat/fit %.2f'
              % (rm, kind, np.median(rms), max(rms), np.median(flat), min(flat), np.median(slope), min(slope), max(slope), np.median(icpt), nt, min(gaps), min(np.array(flat) / np.array(rms))))
    ok = sum(1 for h in HXP if h in MAP[(rm, 'local', h)][0]); uq = sum(1 for h in HXP if MAP[(rm, 'local', h)][0] == [h])
    print('  local control: true XP in tie set %d/32, unique %d/32' % (ok, uq))
for rm in (0, 1):
    print('reader mesh %d remote map (home XP on mesh %d -> XP on mesh %d, RMS, slope, runner-up RMS):' % (rm, 1 - rm, rm))
    for h in HXP:
        t, b, ru = MAP[(rm, 'remote', h)]
        print('  (%d,%d)->%s %.3f %.2f | %s %.3f%s' % (h[0], h[1], fs(t), b[0], b[3], fs([ru[1]]), ru[0], ' TIE' if len(t) > 1 else ''))

print('\n== B. compare with the claimed table ==')
CL0 = "(1,1)->(5,4) (1,2)->(5,5) (1,3)->(6,3) (1,4)->(5,1) (2,1)->(6,4) (2,2)->(6,5) (2,3)->(5,3) (2,4)->(6,1) (2,5)->(5,2) (3,1)->(7,4) (3,2)->(7,3) (3,3)->(7,2) (3,4)->(7,1) (3,5)->(6,2) (4,1)->(2,3) (4,2)->(4,4) (4,3)->(4,3) (4,4)->(4,2) (5,1)->(1,4) (5,2)->(2,5) (5,3)->(4,1) (5,4)->(1,1) (5,5)->(1,2) (6,1)->(2,4) (6,2)->(3,5) (6,3)->(3,2) (6,4)->(2,1) (6,5)->(2,2) (7,1)->(3,4) (7,2)->(1,3) (7,3)->(3,3) (7,4)->(3,1)"
CL1 = "(1,1)->(5,4) (1,2)->(5,5) (1,3)->(7,2)|(6,2) (1,4)->(5,1) (2,1)->(7,4)|(6,4) (2,2)->(6,5) (2,3)->(4,1) (2,4)->(7,1)|(6,1) (2,5)->(5,2) (3,1)->(7,4)|(6,4) (3,2)->(6,3)|(7,3) (3,3)->(6,3)|(7,3) (3,4)->(6,1)|(7,1) (3,5)->(6,2)|(7,2) (4,1)->(5,3) (4,2)->(4,4) (4,3)->(4,3) (4,4)->(4,2) (5,1)->(1,4) (5,2)->(2,5) (5,3)->(2,3) (5,4)->(1,1) (5,5)->(1,2) (6,1)->(2,4) (6,2)->(3,5) (6,3)->(1,3) (6,4)->(2,1) (6,5)->(2,2) (7,1)->(3,4) (7,2)->(3,3) (7,3)->(3,2) (7,4)->(3,1)"
def parse(s):
    d = {}
    for e in s.split():
        a, b = e.split('->'); d[eval(a)] = sorted(eval(x) for x in b.split('|'))
    return d
CLM = {0: parse(CL0), 1: parse(CL1)}
for rm in (0, 1):
    bad = [(h, MAP[(rm, 'remote', h)][0], CLM[rm][h]) for h in HXP if MAP[(rm, 'remote', h)][0] != CLM[rm][h]]
    print('reader %d: entries equal to claim %d/32; differing: %s' % (rm, 32 - len(bad), bad))
m0 = {h: MAP[(0, 'remote', h)][0] for h in HXP}; m1 = {h: MAP[(1, 'remote', h)][0] for h in HXP}
print('reader0 map bijection onto 32 home XPs:', sorted(t[0] for t in m0.values()) == HXP and all(len(t) == 1 for t in m0.values()))
inv = {m0[h][0]: h for h in HXP}
print('reader1 = inverse(reader0): unique match %d of %d unique; inverse inside tie set %d of %d tied' % (
    sum(1 for h in HXP if len(m1[h]) == 1 and m1[h][0] == inv[h]), sum(1 for h in HXP if len(m1[h]) == 1),
    sum(1 for h in HXP if len(m1[h]) > 1 and inv[h] in m1[h]), sum(1 for h in HXP if len(m1[h]) > 1)))
both = [h for h in HXP if len(m1[h]) == 1]
print('same coordinates r0 and r1 on unique entries: %d of %d; differ: %s' % (sum(m0[h] == m1[h] for h in both), len(both), [(h, m0[h][0], m1[h][0]) for h in both if m0[h] != m1[h]]))
print('r0 applied twice returns to start: %d/32' % sum(m0[m0[h][0]][0] == h for h in HXP))
for name, f in (('identity', lambda x, y: (x, y)), ('mirror-x', lambda x, y: (8 - x, y)), ('mirror-y', lambda x, y: (x, 6 - y)), ('rot180', lambda x, y: (8 - x, 6 - y)), ('transpose', lambda x, y: (y, x))):
    print('  rule %-9s matches r0 %d/32, r1 (in tie set) %d/32' % (name, sum(f(*h) == m0[h][0] for h in HXP), sum(f(*h) in m1[h] for h in HXP)))
bestaff = {}
for rm, mp in ((0, m0), (1, m1)):
    bb = (0, None)
    for tr in (0, 1):
        for sx, sy in itertools.product((1, -1), repeat=2):
            for ax in range(-8, 17):
                for ay in range(-8, 17):
                    n = sum(((sx * (h[1] if tr else h[0]) + ax, sy * (h[0] if tr else h[1]) + ay) in mp[h]) for h in HXP)
                    if n > bb[0]: bb = (n, (tr, sx, ax, sy, ay))
    print('  best affine rule reader %d: %d/32 (transpose,sx,ax,sy,ay)=%s' % (rm, bb[0], bb[1]))
hx = np.array([h[0] for h in HXP]); hy = np.array([h[1] for h in HXP]); px = np.array([m0[h][0][0] for h in HXP]); py = np.array([m0[h][0][1] for h in HXP])
print('  reader0 Pearson: proxy x vs home x %.3f, proxy y vs home y %.3f, px-hy %.3f, py-hx %.3f' % (np.corrcoef(hx, px)[0, 1], np.corrcoef(hy, py)[0, 1], np.corrcoef(hy, px)[0, 1], np.corrcoef(hx, py)[0, 1]))

print('\n== C. dev 0 vs dev 1 fitted alone (remote) ==')
for rm in (0, 1):
    same = uniq = tsame = 0
    for h in HXP:
        t0 = best(vecd(rm, 1 - rm, h, 0), PP[rm])[1]; t1 = best(vecd(rm, 1 - rm, h, 1), PP[rm])[1]
        tsame += t0 == t1
        if len(t0) == 1 and len(t1) == 1: uniq += 1; same += t0 == t1
    print('reader %d: both unique %d/32, same XP %d of those; tie sets identical %d/32' % (rm, uniq, same, tsame))

print('\n== D. attack 1: constant model and permutation tests (remote, per-core points) ==')
NP = 1000
for rm in (0, 1):
    worst_p = 0; worst_p2 = 0; ratio = []; pmin = []
    xps = sorted({tuple(p) for p in PP[rm]}); idx = {x: [i for i, p in enumerate(PP[rm]) if tuple(p) == x] for x in xps}
    for h in HXP:
        v = vec(rm, 1 - rm, h); act = best(v, PP[rm])[0][0]
        # (i) shuffle latency among cores
        def shuf():
            # keep the cores of one reader XP together: permute which XP block gets which block of values
            o = rng.permutation(len(xps)); w = np.empty_like(v)
            for i, x in enumerate(xps):
                src = idx[xps[o[i]]]; dst = idx[x]; w[dst] = v[src][:len(dst)] if len(src) >= len(dst) else np.resize(v[src], len(dst))
            return w
        null = np.array([best(shuf(), PP[rm])[0][0] for _ in range(NP if h in HXP[:4] else 100)])
        worst_p = max(worst_p, (null <= act).mean()); ratio.append(null.min() / act); pmin.append(null.min())
    print('reader %d: shuffle reader-XP blocks, cores of one XP kept together (1000 perms for 4 home XPs, 100 for 28): largest fraction of shuffles with best-of-32 RMS <= actual = %.4f; smallest shuffled best-RMS %.3f ns (actual max %.3f); min ratio shuffled/actual %.2f'
          % (rm, worst_p, min(pmin), max(MAP[(rm, 'remote', h)][1][0] for h in HXP), min(ratio)))
# (ii) F-like: variance explained
for rm in (0, 1):
    r2 = [1 - (MAP[(rm, 'remote', h)][1][0] / vec(rm, 1 - rm, h).std()) ** 2 for h in HXP]
    print('reader %d remote R^2 of single-XP model: min %.3f med %.3f' % (rm, min(r2), np.median(r2)))
# (iii) two-source alternative: fixed gateway (one XP for all homes)? RMS if every home is forced to the same single XP
for rm in (0, 1):
    tot = {c: np.sqrt(np.mean([fitone(dist('man', c, PP[rm]), vec(rm, 1 - rm, h))[2] ** 2 for h in HXP])) for c in HXP}
    cb = min(tot, key=tot.get)
    print('reader %d: one common XP for all 32 remote homes: best common XP %s pooled RMS %.3f ns; per-home best pooled RMS %.3f ns'
          % (rm, cb, tot[cb], np.sqrt(np.mean([MAP[(rm, 'remote', h)][1][0] ** 2 for h in HXP]))))

print('\n== E. attack 2: hold-out ==')
for rm in (0, 1):
    ev = [i for i, c in enumerate(RC[rm]) if c % 2 == 0]; od = [i for i, c in enumerate(RC[rm]) if c % 2 == 1]
    agree = intie = 0; oos = []; oosflat = []
    for h in HXP:
        v = vec(rm, 1 - rm, h); be, te, _ = best(v[ev], PP[rm][ev]); bo, to, _ = best(v[od], PP[rm][od])
        agree += te == to; intie += bool(set(te) & set(MAP[(rm, 'remote', h)][0])) and bool(set(to) & set(MAP[(rm, 'remote', h)][0]))
        pred = be[2] + be[3] * dist('man', be[1], PP[rm][od]); oos.append(np.sqrt(((v[od] - pred) ** 2).mean())); oosflat.append(np.sqrt(((v[od] - v[ev].mean()) ** 2).mean()))
    print('reader %d even-CPU vs odd-CPU fits: same tie set %d/32; both overlap full-data answer %d/32; odd-core RMS predicted from even-core fit med %.3f max %.3f (constant from even: med %.3f)'
          % (rm, agree, intie, np.median(oos), max(oos), np.median(oosflat)))
    # random half of reader XPs (stronger: unseen positions)
    xps = sorted({tuple(p) for p in PP[rm]}); nsp = 200; hit = tot = amb = 0; oos = []; oosf = []; fails = collections.Counter()
    for s in range(nsp):
        tr = set(map(tuple, rng.permutation(xps)[:len(xps) // 2])); a = np.array([tuple(p) in tr for p in PP[rm]])
        for h in HXP:
            v = vec(rm, 1 - rm, h); b, t, _ = best(v[a], PP[rm][a]); full = MAP[(rm, 'remote', h)][0]
            tot += 1; ok = bool(set(t) & set(full)); hit += ok; amb += len(t) > 1
            if not ok: fails[h] += 1
            pred = b[2] + b[3] * dist('man', b[1], PP[rm][~a]); oos.append(np.sqrt(((v[~a] - pred) ** 2).mean())); oosf.append(np.sqrt(((v[~a] - v[a].mean()) ** 2).mean()))
    print('reader %d random half of reader XPs (200 splits x 32 homes): train winner tie set contains full-data answer %d/%d (%.2f%%); train ties %d; held-out XP RMS med %.3f p95 %.3f max %.3f; constant model held-out med %.3f; homes with misses: %s'
          % (rm, hit, tot, 100 * hit / tot, amb, np.median(oos), np.percentile(oos, 95), max(oos), np.median(oosf), dict(fails)))

print('\n== F. attack 3: other distance metrics (remote, per-core points) ==')
for rm in (0, 1):
    for met in ('euc', 'cheb'):
        same = 0; rm_m = []; rm_e = []; diff = []
        for h in HXP:
            b, t, _ = best(vec(rm, 1 - rm, h), PP[rm], metric=met); full = MAP[(rm, 'remote', h)]
            ok = bool(set(t) & set(full[0])); same += ok; rm_m.append(full[1][0]); rm_e.append(b[0])
            if not ok: diff.append((h, full[0], t))
        print('reader %d %s: winner inside Manhattan tie set %d/32; RMS med %.3f (Manhattan %.3f); homes where Manhattan RMS is smaller %d/32; differing %s'
              % (rm, met, same, np.median(rm_e), np.median(rm_m), sum(a < b for a, b in zip(rm_m, rm_e)), diff))

print('\n== G. attack 4: position-free test (no core-positions.json). Match latency vector over reader cores of a remote home XP to the vectors of the 32 LOCAL home XPs ==')
for rm, crs in ((0, [c for c in cores if c < 64]), (1, [c for c in cores if c >= 64])):
    V = lambda hm, h: np.array([min(lat[(c, hm, h[0], h[1], 0)], lat[(c, hm, h[0], h[1], 1)]) for c in crs])
    loc = {q: V(rm, q) for q in HXP}
    agree_c = agree_r = 0; rows = []; gapc = []; rawbest = []; cen = []; mm = []
    for h in HXP:
        v = V(1 - rm, h)
        c_sc = sorted((float(np.sqrt((((v - v.mean()) - (u - u.mean())) ** 2).mean())), q) for q, u in loc.items())
        r_sc = sorted((float(np.sqrt(((v - u) ** 2).mean())), q) for q, u in loc.items())
        full = MAP[(rm, 'remote', h)][0]
        agree_c += c_sc[0][1] in full; agree_r += r_sc[0][1] in full; gapc.append(c_sc[1][0] - c_sc[0][0]); rawbest.append(r_sc[0][0]); cen.append(c_sc[0][0])
        mm.append(float((v - loc[r_sc[0][1]]).mean()))
        rows.append((h, c_sc[0][1], c_sc[0][0], c_sc[1][1], c_sc[1][0], r_sc[0][1], r_sc[0][0], r_sc[1][1], r_sc[1][0]))
    print('reader %d: closest local XP (mean removed) is in fit tie set %d/32; closest raw (no offset) in tie set %d/32; mean-removed RMS diff to best med %.3f max %.3f; raw med %.3f max %.3f; mean (remote - matched local) med %+.3f min %+.3f max %+.3f ns'
          % (rm, agree_c, agree_r, np.median(cen), max(cen), np.median(rawbest), max(rawbest), np.median(mm), min(mm), max(mm)))
    # local-vs-local scale: RMS diff between dev0 and dev1 vectors of same local XP
    dd = [float(np.sqrt(((np.array([lat[(c, rm, q[0], q[1], 0)] for c in crs]) - np.array([lat[(c, rm, q[0], q[1], 1)] for c in crs])) ** 2).mean())) for q in HXP]
    print('   scale: RMS diff between dev0 and dev1 vectors of one local XP: med %.3f max %.3f' % (np.median(dd), max(dd)))
    for r in rows:
        full = MAP[(rm, 'remote', r[0])][0]
        if len(full) > 1 or r[1] not in full or r[5] not in full:
            print('   home (%d,%d) fit %s | mean-removed best (%d,%d) %.3f next (%d,%d) %.3f | raw best (%d,%d) %.3f next (%d,%d) %.3f' % (r[0][0], r[0][1], fs(full), *r[1], r[2], *r[3], r[4], *r[5], r[6], *r[7], r[8]))
    if rm == 1:
        print('   raw-match answer for tied homes vs inverse-of-reader0 prediction:', [(r[0], r[5], inv[r[0]], r[5] == inv[r[0]]) for r in rows if len(MAP[(1, 'remote', r[0])][0]) > 1])
        # control: does raw matching separate local col 6 from col 7? leave-one-dev: match local dev0 vector of XP q against dev1 vectors
        ok = 0; l67 = []
        for q in HXP:
            v0 = np.array([lat[(c, rm, q[0], q[1], 0)] for c in crs])
            sc = sorted((float(np.sqrt(((v0 - np.array([lat[(c, rm, u[0], u[1], 1)] for c in crs])) ** 2).mean())), u) for u in HXP)
            ok += sc[0][1] == q
            if q[0] >= 6 and q[1] <= 4: l67.append((q, sc[0][1], round(sc[0][0], 3), sc[1][1], round(sc[1][0], 3)))
        print('   control: raw match of local dev0 vector to local dev1 vectors finds its own XP %d/32; columns 6,7:' % ok, l67)

print('\n== H. sensitivity: all 72 XPs (x 0..8, y 0..7) as candidates ==')
ALL = [(x, y) for x in range(9) for y in range(8)]
for rm in (0, 1):
    k = t = 0
    for h in HXP:
        b, ties, _ = best(vec(rm, 1 - rm, h), PP[rm], cands=ALL); k += bool(set(ties) & set(MAP[(rm, 'remote', h)][0])); t += len(ties) > 1
    print('reader %d: 32-candidate answer in 72-candidate tie set %d/32; tied entries %d' % (rm, k, t))
