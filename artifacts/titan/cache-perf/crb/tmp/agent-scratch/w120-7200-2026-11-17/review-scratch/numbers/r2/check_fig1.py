#!/usr/bin/env python3
"""Check every mark of Figure 1 (3 variants) against the raw files: tooltip numbers, direct labels, positions."""
import os, re, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rawp import *

HERE = os.path.dirname(os.path.abspath(__file__))
_bw, _bx = {}, {}


def raw_value(rel, line):
    path = os.path.join(R, rel)
    first = open(path).readline()
    if first.startswith('-- '):
        if path not in _bw:
            _bw[path] = {i['line']: (i['v'], p) for p in bw_procs(path) for i in p['iv']}
        v, p = _bw[path][line]
        return v, ('bw', p['binary'], p['kernel'], p['round'], p['hline'])
    if path not in _bx:
        _bx[path] = {e['Iline']: e for e in bwx_ivs(path)}
    e = _bx[path][line]
    assert e['ok'], (rel, line)
    return e['total'], ('bwx', e['kernel'], e['round'], e['pos'], e['prev'])


bad = 0


def err(*a):
    global bad
    bad += 1
    print('  MISMATCH:', *a)


def check(fn):
    global bad
    s = re.sub(r'>\s*\n\s*<', '><', open(os.path.join(HERE, fn)).read())
    print('=====', fn, re.match(r'<svg[^>]*>', s).group(0)[:60])
    # axis: tick lines followed by text labels
    ticks = {}
    for m in re.finditer(r'<line x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)" y2="[\d.]+" stroke="#e4e3df"/><text x="([\d.]+)"[^>]*>(\d+)</text>', s):
        if m.group(1) == m.group(2) == m.group(3):
            ticks.setdefault(float(m.group(4)), set()).add(float(m.group(1)))
    print('  ticks', {k: sorted(v) for k, v in sorted(ticks.items())})
    # may be several axes (narrow variant can be stacked); build list of (x0, x500)
    scales = sorted(set((min(ticks[0.0]), min(ticks[500.0])) for _ in [0])) if all(len(v) == 1 for v in ticks.values()) else None
    assert scales, 'several axes: handle by hand'
    x0, x500 = scales[0]
    X = lambda v: x0 + (x500 - x0) * v / 500.0
    V = lambda x: (x - x0) * 500.0 / (x500 - x0)
    ppu = (x500 - x0) / 500.0
    print('  scale: %.4f px per GB/s, 0.1 px = %.3f GB/s' % (ppu, 0.1 / ppu))
    tol_px = 0.06  # coordinates have 1 decimal
    # tokens in order
    toks = list(re.finditer(r'<g class="pt">(.*?)</g>|<g>(.*?)</g>|<text ([^>]*)>([^<]*)</text>', s, flags=re.S))
    rows = []
    n_pt = n_drop = 0
    i = 0
    last_drop = None
    while i < len(toks):
        m = toks[i]
        if m.group(2) is not None:  # drop group
            g = m.group(2)
            t = html.unescape(re.search(r'<title>(.*?)</title>', g, flags=re.S).group(1))
            ln = re.search(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)"', g)
            lab = re.search(r'<text [^>]*>([^<]*)</text>', g).group(1)
            last_drop = dict(title=t, x1=float(ln.group(1)), x2=float(ln.group(3)), label=html.unescape(lab), pts=[])
            rows.append(last_drop)
            n_drop += 1
        elif m.group(1) is not None:  # point group
            g = m.group(1)
            t = html.unescape(re.search(r'<title>(.*?)</title>', g, flags=re.S).group(1))
            cs = re.findall(r'<circle([^>]*)/>', g)
            mk = [c for c in cs if 'class="mk' in c][0]
            cx = float(re.search(r'cx="([\d.]+)"', mk).group(1))
            filled = 'mk fi' in mk
            col = re.search(r'(?:fill|stroke)="(#2a78d6|#eb6834)"', mk).group(1)
            pth = re.search(r'<path d="M([\d.]+) [\d.]+V[\d.]+M([\d.]+) ', g)
            w1, w2 = float(pth.group(1)), float(pth.group(2))
            # the direct label is the next text token
            nxt = toks[i + 1]
            assert nxt.group(3) is not None, 'no label after point'
            label = nxt.group(4)
            lx = float(re.search(r'x="([\d.]+)"', nxt.group(3)).group(1))
            last_drop['pts'].append(dict(title=t, cx=cx, filled=filled, col=col, w1=w1, w2=w2, label=label, lx=lx))
            n_pt += 1
            i += 1
        i += 1
    print('  rows', len(rows), 'points', n_pt)
    for r in rows:
        t = r['title']
        name = t.split(': drop of the load-only loop')[0]
        assert len(r['pts']) == 2, name
        dm = re.search(r'kernel: ([\d.]+) %(?: to ([\d.]+) %)? \((.*?), n = (\d+) pairs?\)\. Source: (R/\S+?)(?:,)? (?:interval rows in )?lines ([\d, ]+)\.', t)
        assert dm, t
        rel = dm.group(5)[2:]
        vals = {}
        for p in r['pts']:
            pt = p['title']
            assert pt.startswith(name + ': '), (name, pt)
            pm = re.search(r': (oldread|asmread|read|bw_old read|bw_new read) \(([^)]*)\)\. Median ([\d.]+) GB/s\. Intervals: ([\d., ]+) GB/s\. n = (\d+) intervals / 1 process\. Source: (R/\S+?)(?:,)? (?:interval rows in )?lines ([\d, ]+)\.', pt)
            assert pm, pt
            kern = pm.group(1)
            lines = [int(x) for x in pm.group(7).split(',')]
            assert pm.group(6)[2:] == rel
            raws = [raw_value(rel, l) for l in lines]
            rv = [x[0] for x in raws]
            infos = [x[1] for x in raws]
            # kernel identity
            for inf in infos:
                if inf[0] == 'bwx':
                    if inf[1] != kern:
                        err(name, 'tooltip kernel', kern, 'raw', inf)
                else:
                    if '%s %s' % (inf[1], inf[2]) != kern:
                        err(name, 'tooltip kernel', kern, 'raw', inf)
            if int(pm.group(5)) != len(rv):
                err(name, kern, 'n', pm.group(5), len(rv))
            tv = [float(x) for x in pm.group(4).split(',')]
            for a, b in zip(tv, rv):
                if '%.2f' % b != '%.2f' % a:
                    err(name, kern, 'interval tooltip', a, 'raw %.4f' % b)
            mraw = med(rv)
            if '%.2f' % mraw != pm.group(3):
                err(name, kern, 'median tooltip', pm.group(3), 'raw %.4f' % mraw)
            if p['label'] != '%.2f' % mraw:
                err(name, kern, 'direct label', p['label'], 'raw %.4f' % mraw)
            if abs(p['cx'] - X(mraw)) > tol_px:
                err(name, kern, 'cx %.1f expected %.2f (value at cx %.2f, raw %.2f)' % (p['cx'], X(mraw), V(p['cx']), mraw))
            if abs(p['w1'] - X(min(rv))) > tol_px or abs(p['w2'] - X(max(rv))) > tol_px:
                err(name, kern, 'whisker %.1f-%.1f expected %.2f-%.2f' % (p['w1'], p['w2'], X(min(rv)), X(max(rv))))
            is_old = kern in ('oldread', 'bw_old read')
            if (p['col'] == '#2a78d6') != is_old:
                err(name, kern, 'colour', p['col'])
            want_filled = not (name.startswith('L-1') or name.startswith('A-1') or name.startswith('A-2'))
            if p['filled'] != want_filled:
                err(name, kern, 'fill', p['filled'])
            # label side
            if is_old and not p['lx'] > p['cx']:
                err(name, 'old label not right of dot')
            if not is_old and not p['lx'] < p['cx']:
                err(name, 'lo label not left of dot')
            vals['old' if is_old else 'lo'] = (rv, infos, lines)
        # drop
        o, oi, ol = vals['old']
        l, li, ll = vals['lo']
        if oi[0][0] == 'bwx':
            # pair by round
            d = []
            for (lv, linf) in zip(l, li):
                ov = [x for x, inf in zip(o, oi) if inf[2] == linf[2]]
                assert len(ov) == 1
                d.append((1 - lv / ov[0]) * 100)
                if linf[3] != 1:
                    err(name, 'load-only interval not at position 1', linf)
            npairs = len(d)
        else:
            d = [(1 - med(l) / med(o)) * 100]
            npairs = 1
        lo_s, hi_s = '%.1f' % min(d), '%.1f' % max(d)
        want = (lo_s + ' %') if lo_s == hi_s else '%s %% to %s %%' % (lo_s, hi_s)
        if r['label'] != want:
            err(name, 'drop label', r['label'], 'raw', want, d)
        got = dm.group(1) + ' %' if not dm.group(2) else '%s %% to %s %%' % (dm.group(1), dm.group(2))
        if got != want:
            err(name, 'drop tooltip', got, 'raw', want)
        if int(dm.group(4)) != npairs:
            err(name, 'pairs n', dm.group(4), npairs)
        dl = sorted(int(x) for x in dm.group(6).split(','))
        if dl != sorted(ol + ll):
            err(name, 'drop source lines', dl, sorted(ol + ll))
        # connecting line ends = the two dots
        xs = sorted([r['pts'][0]['cx'], r['pts'][1]['cx']])
        if abs(r['x1'] - xs[0]) > 0.01 or abs(r['x2'] - xs[1]) > 0.01:
            err(name, 'connector', r['x1'], r['x2'], xs)
        print('   ok-row %-62s old %.2f lo %.2f drop %s' % (name[:62], med(o), med(l), want))
    return rows


allrows = {}
for fn in ('svg06.txt', 'svg07.txt', 'svg08.txt'):
    allrows[fn] = check(fn)
names = [[r['title'].split(': drop')[0] for r in rows] for rows in allrows.values()]
print('same row order in the 3 variants:', names[0] == names[1] == names[2], len(names[0]))
print('MISMATCHES:', bad)
