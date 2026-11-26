#!/usr/bin/env python3
"""Check the 5 large SVGs of the report against the raw csv files (own parser)."""
import sys, os, re, html, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *

HTML = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
src = open(HTML).read()
svgs = [m for m in re.finditer(r'<svg[^>]*role="img"[^>]*>.*?</svg>', src, re.S)]
print('large svgs:', len(svgs))
problems = []
def bad(msg):
    problems.append(msg); print('  !!', msg)

_cache = {}
def bwx_file(rel):
    if rel not in _cache:
        ps = parse_bwx(R + '/' + rel)
        d = {}
        for pi, p in enumerate(ps):
            for k, iv in enumerate(p['iv']):
                iv['_proc'] = p; iv['_idx'] = k; iv['_pi'] = pi
                d[iv['line']] = iv
        _cache[rel] = d
    return _cache[rel]
def band_file(rel):
    if rel not in _cache:
        ps = parse_bandwidth(R + '/' + rel)
        d = {}
        for pi, p in enumerate(ps):
            for k, iv in enumerate(p['iv']):
                iv['_proc'] = p; iv['_idx'] = k; iv['_pi'] = pi
                d[iv['line']] = iv
        _cache[rel] = d
    return _cache[rel]
def is_bwx(rel):
    return not (rel.endswith('threads120.csv') or '/A1.csv' in rel or '/A3.csv' in rel)
def rate_at(rel, line):
    if is_bwx(rel):
        iv = bwx_file(rel)[line]
        return iv['rate'], iv
    iv = band_file(rel)[line]
    return iv['agg'], iv
def is8000(rel):
    return not ('T72' in rel or 'F72d12' in rel)

def scale_of(svg):
    ticks = {}
    for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*text-anchor="middle"[^>]*>(\d+)</text>', svg):
        ticks.setdefault(float(m[3]), set()).add(float(m[1]))
    pts = sorted((v, min(xs)) for v, xs in ticks.items() if len(xs) == 1)
    st = re.search(r'The axis starts at (\d+) GB/s', svg)
    if st:
        v0 = float(st[1]); x0 = 190.0; v1, x1 = pts[-1]
    else:
        (v0, x0), (v1, x1) = pts[0], pts[-1]
    b = (x1 - x0) / (v1 - v0); a = x0 - b * v0
    for v, x in pts:
        if abs(a + b * v - x) > 0.06:
            bad('tick %s at x=%s not on the linear scale (expected %.2f)' % (v, x, a + b * v))
    return a, b, pts

def near(x, y, tol=0.056):
    return abs(x - y) <= tol

def fmt2(x):
    return '%.2f' % x

for si, m in enumerate(svgs):
    svg = m.group(0)
    label = re.search(r'aria-label="([^"]*)"', svg)[1]
    a, b, pts = scale_of(svg)
    print('== SVG %d: %s | scale: x = %.3f + %.4f * v ; ticks %s ; px per GB/s %.4f' % (si, label[:60], a, b, [p[0] for p in pts], b))
    X = lambda v: a + b * v
    is_fig1 = label.startswith('Dumbbell')
    # ----- point groups
    groups = list(re.finditer(r'<g class="pt"><title>(.*?)</title>(.*?)</g>(?:</g>)?\s*(<text[^>]*>[^<]*</text>)?', svg, re.S))
    print('   pt groups:', len(groups))
    dots = {}
    nint = 0
    for g in groups:
        title = html.unescape(g[1]); body = g[2]
        mk = re.search(r'<circle class="mk (ho|fi)" cx="([\d.]+)" cy="([\d.]+)"', body)
        if not mk:
            bad('no marker in group: ' + title[:80]); continue
        cx = float(mk[2]); kind = mk[1]
        if is_fig1:
            t = re.match(r'^(.*?): (\S+(?: \S+)?) \((old read kernel|new read kernel|in place of the new read kernel)\)\. Median ([\d.]+) GB/s\. Intervals: ([\d., ]+) GB/s\. n = (\d+) intervals / (\d+) process\. Source: (\S+?),? (?:interval rows in )?lines ([\d, ]+)\.', title)
            if not t:
                bad('title not parsed: ' + title[:200]); continue
            row, kname, kdesc, med_s, ivs_s, n_s, np_s, rel, lines_s = t.groups()
            rel = rel[2:] if rel.startswith('R/') else rel
            lines = [int(x) for x in lines_s.split(',')]
            vals = []; kerns = set(); procs = set()
            for ln in lines:
                v, iv = rate_at(rel, ln); vals.append(v)
                kerns.add((iv['_proc'].get('binary') or '') + ' ' + iv['kernel'] if not is_bwx(rel) else iv['kernel'])
                procs.add(iv['_pi'])
            want_k = kname if is_bwx(rel) else kname
            if kerns != {want_k}:
                bad('%s: title kernel "%s" but raw lines hold %s' % (row, kname, kerns))
            if len(procs) != int(np_s): bad('%s: process count %s vs raw %d' % (row, np_s, len(procs)))
            if int(n_s) != len(lines): bad('%s: n %s vs %d lines' % (row, n_s, len(lines)))
            if [fmt2(v) for v in vals] != [x.strip() for x in ivs_s.split(',')]:
                bad('%s %s: intervals in title %s, raw %s' % (row, kname, ivs_s, [fmt2(v) for v in vals]))
            med = statistics.median(vals)
            if fmt2(med) != med_s and abs(med - float(med_s)) > 0.0051:
                bad('%s %s: median in title %s, raw %.4f' % (row, kname, med_s, med))
            if not near(cx, X(med)):
                bad('%s %s: dot cx %.1f but scale(median %.3f) = %.2f (dot shows %.2f GB/s)' % (row, kname, cx, med, X(med), (cx - a) / b))
            pm = re.search(r'<path d="M([\d.]+) [\d.]+V[\d.]+M([\d.]+) ', body)
            if pm:
                x1, x2 = float(pm[1]), float(pm[2])
                if not (near(x1, X(min(vals))) and near(x2, X(max(vals)))):
                    bad('%s %s: range mark %.1f..%.1f but scale(min,max) = %.2f..%.2f' % (row, kname, x1, x2, X(min(vals)), X(max(vals))))
            else:
                bad('%s %s: no range mark' % (row, kname))
            lab = g[3]
            if lab:
                lv = re.search(r'>([^<]*)<', lab)[1]
                if lv != med_s: bad('%s %s: value label "%s" vs median %s' % (row, kname, lv, med_s))
            else:
                bad('%s %s: no value label after the dot' % (row, kname))
            if (kind == 'ho') != is8000(rel):
                bad('%s %s: marker kind %s but file %s' % (row, kname, kind, rel))
            dots[(row, 'old' if kdesc == 'old read kernel' else 'lo')] = (cx, vals, rel, lines, med)
            nint += len(lines)
        else:
            t = re.match(r'^(.*?): (\S+(?: \S+)?) \((old read kernel|new read kernel|in place of the new read kernel)\), process (.+?),(?: round (\d+),)? (?:position (\d+), (.+?)|interval (\d+)): ([\d.]+) GB/s\. Row: ([\d.]+) to ([\d.]+) GB/s, n = (\d+) intervals? / (\d+) process(?:es)?\. Source: (\S+?),? (?:interval row in )?line (\d+)\.', title)
            if not t:
                bad('title not parsed: ' + title[:260]); continue
            row, kname, kdesc, proc, rnd, pos, before, ivno, val_s, lo_s, hi_s, n_s, np_s, rel, line = t.groups()
            rel = rel[2:] if rel.startswith('R/') else rel
            v, iv = rate_at(rel, int(line))
            if fmt2(v) != val_s: bad('%s: value in title %s, raw %.4f (%s line %s)' % (row, val_s, v, rel, line))
            if not near(cx, X(v)): bad('%s: dot cx %.1f but scale(%.3f) = %.2f (dot shows %.2f GB/s) [%s line %s]' % (row, cx, v, X(v), (cx - a) / b, rel, line))
            if (kind == 'ho') != is8000(rel): bad('%s: marker kind %s but file %s' % (row, kind, rel))
            if is_bwx(rel):
                if iv['kernel'] != kname: bad('%s: kernel %s vs raw %s' % (row, kname, iv['kernel']))
                if int(rnd) != iv['round'] or int(pos) != iv['pos']: bad('%s: round/pos %s/%s vs raw %d/%d' % (row, rnd, pos, iv['round'], iv['pos']))
                k = iv['_idx']; prev = iv['_proc']['iv'][k - 1]['kernel'] if k > 0 else None
                if prev is None:
                    if before != 'no kernel ran before it': bad('%s: "%s" but first interval of the process' % (row, before))
                else:
                    bm = re.match(r'directly after (\S+)', before)
                    if not bm or bm[1] != prev: bad('%s: "%s" but raw previous kernel is %s (%s line %s)' % (row, before, prev, rel, line))
                # process name check
                base = os.path.basename(rel)[:-4]
                folder = rel.split('/')[0]
                tm = re.search(r'(T72[A-Z]\d)', folder)
                expect = tm[1] if tm else base
                if proc != expect: bad('%s: process "%s" vs expected "%s" (%s)' % (row, proc, expect, rel))
            else:
                want = kname.split()
                if iv['_proc']['binary'] != want[0] or iv['kernel'] != want[1]: bad('%s: %s vs raw %s %s' % (row, kname, iv['_proc']['binary'], iv['kernel']))
                if iv['_proc']['round'] is not None and (rnd is None or int(rnd) != iv['_proc']['round']): bad('%s: round %s vs raw %s' % (row, rnd, iv['_proc']['round']))
                if int(ivno) != iv['rep'] + 1: bad('%s: interval %s vs raw rep %d' % (row, ivno, iv['rep']))
                pm_ = re.match(r'(\d+) of the file(?: \(tag (\S+)\))?$', proc)
                if pm_ and pm_[2] and pm_[2] != iv['_proc'].get('tag'): bad('%s: tag %s vs raw %s' % (row, pm_[2], iv['_proc'].get('tag')))
                if pm_ and int(pm_[1]) != iv['_pi'] + 1: bad('%s: process %s vs raw process index %d (%s line %s)' % (row, proc, iv['_pi'] + 1, rel, line))
                if not pm_: print('     note: process label "%s" (%s line %s, raw tag %s, index %d)' % (proc, rel, line, iv['_proc'].get('tag'), iv['_pi'] + 1))
            dots.setdefault((si, row.split(',')[0] + '|' + kname + '|' + lo_s + '|' + hi_s + '|' + n_s + '|' + np_s), []).append((v, rel, iv['_pi']))
            nint += 1
    print('   intervals shown:', nint)
    if is_fig1:
        # drop groups
        dg = list(re.finditer(r'<g><title>(.*?)</title><line x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)"[^>]*/><line[^>]*/><text[^>]*>([^<]*)</text></g>', svg, re.S))
        print('   drop groups:', len(dg))
        for g in dg:
            title = html.unescape(g[1]); x1, x2 = float(g[2]), float(g[3]); txt = html.unescape(g[4])
            t = re.match(r'^(.*?): drop of the load-only loop below the old read kernel: ([\d.]+) %(?: to ([\d.]+) %)? \((.*?), n = (\d+) pairs?\)\. Source: (\S+?),? (?:interval rows in )?lines ([\d, ]+)\.', title)
            if not t: bad('drop title not parsed: ' + title[:200]); continue
            row, p1, p2, how, npair, rel, lines_s = t.groups()
            rel = rel[2:]
            o = dots.get((row, 'old')); l = dots.get((row, 'lo'))
            if not o or not l: bad('drop row without dots: ' + row); continue
            if is_bwx(rel):
                # pairs: same round
                fo = bwx_file(rel)
                op = {fo[ln]['round']: fo[ln]['rate'] for ln in o[3]}; lp = {fo[ln]['round']: fo[ln]['rate'] for ln in l[3]}
                drops = [(1 - lp[r] / op[r]) * 100 for r in sorted(op)]
                if int(npair) != len(drops): bad('%s: n pairs %s vs %d' % (row, npair, len(drops)))
            else:
                drops = [(1 - l[4] / o[4]) * 100]
                if int(npair) != 1: bad('%s: n pairs %s vs 1' % (row, npair))
            lo, hi = '%.1f' % min(drops), '%.1f' % max(drops)
            want = (lo, None) if lo == hi else (lo, hi)
            if (p1, p2) != want: bad('%s: drop in title %s..%s, raw %s (%.3f..%.3f)' % (row, p1, p2, want, min(drops), max(drops)))
            wt = '%s %%' % lo if lo == hi else '%s %% to %s %%' % (lo, hi)
            if txt != wt: bad('%s: drop label "%s" vs "%s"' % (row, txt, wt))
            if not (near(x1, l[0]) and near(x2, o[0])): bad('%s: connecting line %.1f..%.1f vs dots %.1f..%.1f' % (row, x1, x2, l[0], o[0]))
            if set(int(x) for x in lines_s.split(',')) != set(o[3]) | set(l[3]): bad('%s: drop source lines %s vs dots lines %s' % (row, lines_s, sorted(set(o[3]) | set(l[3]))))
        rows = sorted({k[0] for k in dots})
        print('   rows:', len(rows))
        for (row, which), (cx, vals, rel, lines, med) in dots.items():
            if which == 'old':
                l = dots[(row, 'lo')]
                if not l[0] < cx: bad('%s: orange dot not left of blue' % row)
    else:
        # row checks
        for (s_, key), lst in dots.items():
            rowname, kname, lo_s, hi_s, n_s, np_s = key.split('|')
            vals = [x[0] for x in lst]
            if fmt2(min(vals)) != lo_s or fmt2(max(vals)) != hi_s: bad('row %s: title range %s to %s, raw dots %.2f to %.2f' % (rowname, lo_s, hi_s, min(vals), max(vals)))
            if int(n_s) != len(vals): bad('row %s: n %s but %d dots' % (rowname, n_s, len(vals)))
            if int(np_s) != len({(x[1], x[2]) for x in lst}): bad('row %s: processes %s but raw %d' % (rowname, np_s, len({(x[1], x[2]) for x in lst})))
            print('     row %-70s %-12s %s to %s n=%s proc=%s  OK-checked' % (rowname[:70], kname, lo_s, hi_s, n_s, np_s))
        # bands
        for bm in re.finditer(r'<g><title>(Grey band:.*?)</title><rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg, re.S):
            title = html.unescape(bm[1]); x = float(bm[2]); w = float(bm[4]); y = float(bm[3]); h = float(bm[5])
            t = re.search(r'([\d.]+) to ([\d.]+) GB/s, n = (\d+) intervals / (\d+) processes / 1 boot', title)
            lo, hi = float(t[1]), float(t[2])
            print('     band %s to %s n=%s/%s : rect x %.1f..%.1f (y %g..%g) ; scale gives %.2f..%.2f ; shows %.2f..%.2f' % (t[1], t[2], t[3], t[4], x, x + w, y, y + h, X(lo), X(hi), (x - a) / b, (x + w - a) / b))
            if not (near(x, X(lo), 0.12) and near(x + w, X(hi), 0.12)): bad('band %s..%s drawn at %.1f..%.1f, expected %.2f..%.2f' % (t[1], t[2], x, x + w, X(lo), X(hi)))
print()
print('PROBLEMS: %d' % len(problems))
for p in problems: print(' -', p)
