#!/usr/bin/env python3
"""Check every dot, band and row label of Figure 2 (2 panels) against the raw files."""
import os, re, sys, html, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rawp import *

HERE = os.path.dirname(os.path.abspath(__file__))
_bw, _bx = {}, {}
bad = 0


def err(*a):
    global bad
    bad += 1
    print('  MISMATCH:', *a)


def raw_value(rel, line):
    path = os.path.join(R, rel)
    first = open(path).readline()
    if first.startswith('-- '):
        if path not in _bw:
            ps = bw_procs(path)
            _bw[path] = {i['line']: (i['v'], p, n + 1, i) for n, p in enumerate(ps) for i in p['iv']}
        v, p, idx, i = _bw[path][line]
        return v, dict(kind='bw', binary=p['binary'], kernel=p['kernel'], round=p['round'], proc=idx, tag=p['tag'], rep=i['rep'], minms=p['minms'])
    if path not in _bx:
        _bx[path] = {e['Iline']: e for e in bwx_ivs(path)}
    e = _bx[path][line]
    assert e['ok'], (rel, line)
    return e['total'], dict(kind='bwx', kernel=e['kernel'], round=e['round'], pos=e['pos'], prev=e['prev'])


def check(fn, panel):
    s = open(os.path.join(HERE, fn)).read()
    print('=====', fn, panel)
    ticks = {}
    for m in re.finditer(r'<line x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)" y2="[\d.]+" stroke="#e4e3df"/>\s*<text x="([\d.]+)"[^>]*>(\d+)</text>', s):
        ticks[float(m.group(4))] = float(m.group(1))
    ks = sorted(ticks)
    # exact scale: the axis starts at x = 190 (left end of the row guide lines) with the value named in the
    # text 'The axis starts at N GB/s'; the last tick sits at x = 450.0
    a = float(re.search(r'The axis starts at (\d+) GB/s', s).group(1))
    b = ks[-1]
    assert ticks[b] == 450.0
    ppu = (450.0 - 190.0) / (b - a)
    X = lambda v: 190.0 + (v - a) * ppu
    V = lambda x: a + (x - 190.0) / ppu
    print('  ticks', ticks, 'px per GB/s %.4f ; 0.1 px = %.4f GB/s ; x=190 -> %.2f GB/s' % (ppu, 0.1 / ppu, V(190.0)))
    for k in ks:
        if abs(ticks[k] - X(k)) > 0.06:
            err('tick', k, ticks[k], X(k))
    start = re.findall(r'The axis starts at (\d+) GB/s', s)
    print('  axis start texts', start)
    # elements in order
    els = list(re.finditer(r'<g class="pt"><title>(.*?)</title>(.*?)</g>|<g><title>(Grey band.*?)</title><rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"[^>]*/>|<text x="([\d.]+)" y="([\d.]+)"([^>]*)>([^<]*)</text>|<rect x="0" y="([\d.]+)" width="466" height="([\d.]+)" fill="#f1f0ec"/>', s, flags=re.S))
    rows = []      # dicts: name, range text, n, y, dots
    bands = []
    cur = None
    pending_name = None
    for m in els:
        if m.group(1) is not None:
            t = html.unescape(m.group(1))
            mk = re.search(r'<circle class="mk (ho|fi)" cx="([\d.]+)" cy="([\d.]+)"[^>]*?(#2a78d6|#eb6834)', m.group(2))
            cur['dots'].append(dict(title=t, cx=float(mk.group(2)), cy=float(mk.group(3)), filled=mk.group(1) == 'fi', col=mk.group(4)))
        elif m.group(3) is not None:
            bands.append(dict(title=html.unescape(m.group(3)), x=float(m.group(4)), y=float(m.group(5)), w=float(m.group(6)), h=float(m.group(7))))
        elif m.group(8) is not None:
            x, y, txt = float(m.group(8)), float(m.group(9)), html.unescape(m.group(11))
            if x == 18.0 and 'font-size="12"' in m.group(10):
                pending_name = (txt, y)
            elif x == 18.0 and re.match(r'^[\d.]+ to [\d.]+ \(\d+\)$', txt):
                cur = dict(name=pending_name[0], y=pending_name[1], rng=txt, notes=[], dots=[])
                rows.append(cur)
            elif x == 18.0 and cur is not None:
                cur['notes'].append(txt)
    print('  rows', len(rows), 'dots', sum(len(r['dots']) for r in rows), 'bands', len(bands))
    # bands
    for bd in bands:
        m = re.search(r'([\d.]+) to ([\d.]+) GB/s, n = (\d+) intervals / (\d+) processes / 1 boot', bd['title'])
        lo, hi = float(m.group(1)), float(m.group(2))
        inside = [r for r in rows if bd['y'] <= r['y'] <= bd['y'] + bd['h']]
        raw8000 = []
        procs = set()
        for r in inside:
            for d in r['dots']:
                if not d['filled']:
                    sm = re.search(r'Source: R/(\S+?),? (?:interval row in )?line (\d+)\.', d['title'])
                    v, inf = raw_value(sm.group(1), int(sm.group(2)))
                    raw8000.append(v)
                    procs.add((sm.group(1), inf.get('proc')))
        print('  band y %.0f-%.0f rows %s' % (bd['y'], bd['y'] + bd['h'], [r['name'] for r in inside]))
        print('     title %.2f to %.2f n=%s/%s ; raw hollow dots in it: %.4f to %.4f n=%d procs=%d ; rect x %.1f..%.1f expected %.2f..%.2f' % (
            lo, hi, m.group(3), m.group(4), min(raw8000), max(raw8000), len(raw8000), len(procs), bd['x'], bd['x'] + bd['w'], X(min(raw8000)), X(max(raw8000))))
        if '%.2f' % min(raw8000) != m.group(1) or '%.2f' % max(raw8000) != m.group(2):
            err('band range', bd['title'][:80])
        if int(m.group(3)) != len(raw8000) or int(m.group(4)) != len(procs):
            err('band n', m.group(3), m.group(4), len(raw8000), len(procs))
        if abs(bd['x'] - X(min(raw8000))) > 0.06 or abs(bd['x'] + bd['w'] - X(max(raw8000))) > 0.11:
            err('band rect', bd['x'], bd['x'] + bd['w'], X(min(raw8000)), X(max(raw8000)))
        bd['raw'] = raw8000
    allvals = []
    for r in rows:
        rv = []
        procs = set()
        for d in r['dots']:
            t = d['title']
            sm = re.search(r'Source: R/(\S+?),? (?:interval row in )?line (\d+)\.', t)
            v, inf = raw_value(sm.group(1), int(sm.group(2)))
            rv.append(v)
            vm = re.search(r': ([\d.]+) GB/s\. Row: ([\d.]+) to ([\d.]+) GB/s, n = (\d+) intervals? / (\d+) process', t)
            if vm.group(1) != '%.2f' % v:
                err(r['name'], 'dot tooltip value', vm.group(1), 'raw %.4f' % v, sm.group(0))
            if abs(d['cx'] - X(v)) > 0.06:
                err(r['name'], 'cx %.1f expected %.2f (value at cx %.2f raw %.2f)' % (d['cx'], X(v), V(d['cx']), v))
            d['row_rng'] = (vm.group(2), vm.group(3), int(vm.group(4)), int(vm.group(5)))
            # identity
            km = re.search(r': (oldread|asmread|read|bw_old read|bw_new read) \(([^)]*)\), process ([^,]+?)(?: \(tag ([^)]+)\))?,(?: round (\d+),)? (?:position (\d+), (.*?)|interval (\d+)): [\d.]+ GB/s', t)
            assert km, t
            kern = km.group(1)
            if inf['kind'] == 'bwx':
                procs.add(sm.group(1))
                if inf['kernel'] != kern:
                    err(r['name'], 'kernel', kern, inf)
                if int(km.group(5)) != inf['round'] or int(km.group(6)) != inf['pos']:
                    err(r['name'], 'round/pos', km.group(5), km.group(6), inf)
                prev = km.group(7)
                want = 'no kernel ran before it' if inf['prev'] is None else 'directly after ' + inf['prev']
                if not prev.startswith(want):
                    err(r['name'], 'prev', prev, inf)
                # process name against file / folder
                pn = km.group(3)
                if not (pn in sm.group(1)):
                    err(r['name'], 'process name', pn, sm.group(1))
            else:
                procs.add((sm.group(1), inf['proc']))
                if '%s %s' % (inf['binary'], inf['kernel']) != kern:
                    err(r['name'], 'kernel', kern, inf)
                if km.group(3) != '%d of the file' % inf['proc']:
                    err(r['name'], 'process index', km.group(3), inf)
                if km.group(5) is not None and int(km.group(5)) != inf['round']:
                    err(r['name'], 'round', km.group(5), inf)
                if km.group(4) is not None and km.group(4) != inf['tag']:
                    err(r['name'], 'tag', km.group(4), inf)
                if int(km.group(8)) != inf['rep'] + 1:
                    err(r['name'], 'interval index', km.group(8), inf)
                if inf['minms'] != 500:
                    err(r['name'], 'min-ms', inf)
            is_old = kern in ('oldread', 'bw_old read')
            if (d['col'] == '#2a78d6') != is_old or (panel == 'old') != is_old:
                err(r['name'], 'colour/panel', d['col'], kern)
        lo, hi, n = '%.2f' % min(rv), '%.2f' % max(rv), len(rv)
        want = '%s to %s (%d)' % (lo, hi, n)
        if r['rng'] != want:
            err(r['name'], 'row label', r['rng'], 'raw', want)
        for d in r['dots']:
            if d['row_rng'] != (lo, hi, n, len(procs)):
                err(r['name'], 'row range in tooltip', d['row_rng'], (lo, hi, n, len(procs)))
        fills = set(d['filled'] for d in r['dots'])
        r['raw'] = rv
        r['filled'] = fills
        allvals += rv
        print('   row %-24s y %6.1f %-22s procs %d fill %s notes %s' % (r['name'], r['y'], r['rng'], len(procs), sorted(fills), r['notes']))
    # distance notes
    for r in rows:
        bd = [b for b in bands if b['y'] <= r['y'] <= b['y'] + b['h']]
        if not bd or r['filled'] != {True}:
            continue
        b = bd[0]
        lo8, hi8 = min(b['raw']), max(b['raw'])
        lo, hi = min(r['raw']), max(r['raw'])
        note = ' '.join(r['notes'])
        if lo > hi8:
            want = '%.2f GB/s higher (right of the band)' % (lo - hi8)
        elif hi < lo8:
            want = '%.2f GB/s lower (left of the band)' % (lo8 - hi)
        else:
            want = 'overlap'
        print('   position of %-24s raw: %s | notes: %s' % (r['name'], want, note))
        if 'medians' in note:
            print('       medians raw: %.4f' % (med(b['raw']) - med(r['raw'])))
    print('  total dots', len(allvals))
    return rows, bands


r1, b1 = check('svg14.txt', 'old')
r2, b2 = check('svg15.txt', 'lo')
print('dots total', sum(len(r['dots']) for r in r1) + sum(len(r['dots']) for r in r2))
print('MISMATCHES:', bad)
