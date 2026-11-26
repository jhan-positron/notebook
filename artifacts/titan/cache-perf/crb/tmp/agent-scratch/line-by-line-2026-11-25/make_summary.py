#!/usr/bin/env python3
"""make_summary.py - write the summary page of the line-by-line job (main session).

    python3 make_summary.py            write S/code-pages-summary.html
    python3 make_summary.py --numbers  print the numbers that the page uses

The numbers come from manifest.json, from the annotation files and from the table of REVIEW-RESULTS.md.
The texts of the sections are written here by hand (file facts.py holds the facts that are not computed).
"""
import collections
import html
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbl  # noqa: E402
import summary_facts as F  # noqa: E402

OUT = lbl.S + '/code-pages-summary.html'
E = html.escape

REVIEW_LABEL = {
    'R1': 'Kernel sources of 2026-11-13 (4 C files)',
    'R2': 'Run scripts of the whole-chip test, 14 small files',
    'R3a': 'Runner bwx12.c, lines 1 to 1561',
    'R3b': 'Runner bwx12.c, lines 1562 to 3126',
    'R4': 'Build, self-test, listing check, kernel test of version 12',
    'R5': 'Hardware record, folder hwwatch-2026-11-24 (4 files)',
    'SR1': 'facts_text.py, facts_text4.py',
    'SR2': 'facts_data.py, build_facts.py, make_report.py part 1',
    'SR3': 'make_report.py part 2',
    'SR4': 'Folder bench (13 files)',
    'SR5': 'Folder w120-2026-11-15 (38 files)',
    'SR6': 'report_w120.py, robsize.c, ASCT scripts (15 files)',
    'SR7': 'Round 4 scripts and tests, cread files (11 files)',
    'SR8': 'Analysis of parts B and C (7 files)',
    'SR9': 'ASCT analysis (6 files)',
    'SR10': 'Part A scripts and analysis (8 files)',
    'SR11': 'Runner versions 13 and 11 (8 files)',
    'SR12': 'Analysis of the first runner, two tests (5 files)',
    'SR13': 'Runner sources of versions 10, 8, first (3 C files)',
    'SR14': 'Round 3 scripts and tests (6 files)',
    'SR15': 'Build, self-test, listing check of versions 10, 8, first',
    'SR16': 'Round 2 scripts and test (4 files)',
    'SR17': 'Round 1 run script, visit scripts, schedule (4 files)',
    'SR18': 'Round 1 schedule test (1 file)',
    'SR19': 'Run scripts of step H2 and of the first runner (2 files)',
}


def review_rows():
    rows = []
    for l in lbl.read_text(os.path.join(lbl.HERE, 'REVIEW-RESULTS.md')).split('\n'):
        if not l.startswith('| ') or l.startswith('| Review') or l.startswith('|---'):
            continue
        c = [x.strip() for x in l.strip().strip('|').split(' | ')]
        name, kind, checked, corrected = c[0], c[2], c[3], c[4]
        n = int(re.match(r'\D*(\d+)', checked).group(1))
        k = int(re.match(r'\D*(\d+)', corrected).group(1))
        mo = re.search(r'and (\d+)(?: more)? outside', corrected)
        kd = 'full' if kind.startswith('full') else ('mixed' if kind.startswith('every row') else 'sample')
        rows.append({'name': name, 'kind': kd, 'full': kd == 'full', 'n': n, 'k': k, 'out': int(mo.group(1)) if mo else 0,
                     'label': REVIEW_LABEL[name]})

    def order(r):
        m = re.match(r'(S?R)(\d+)(\w*)', r['name'])
        return (('full', 'mixed', 'sample').index(r['kind']), m.group(1) == 'SR', int(m.group(2)), m.group(3))
    rows.sort(key=order)
    return rows


def numbers():
    m = lbl.manifest()
    n = {}
    n['files'] = len(m)
    n['lines'] = sum(e['lines'] for e in m.values())
    n['rows'] = sum(e['nonblank'] for e in m.values())
    by = collections.OrderedDict((k, [0, 0]) for k in ('python', 'c', 'bash', 'text', 'make'))
    for e in m.values():
        by[e['lang']][0] += 1
        by[e['lang']][1] += e['nonblank']
    n['by'] = by
    n['mode'] = collections.Counter(e['mode'] for e in m.values())
    n['equal'] = sum('same_as' in e for e in m.values())
    own = seed = left = built = 0
    for key, e in m.items():
        built += os.path.isfile(e['page'])
        if 'same_as' in e:
            continue
        errs = []
        o, s, _ = lbl.load_ann(key, errs)
        src = lbl.source_lines(e['src'])[0]
        need = {i for i in range(1, len(src) + 1) if src[i - 1].strip()}
        own += len(need & set(o))
        seed += len((need & set(s)) - set(o))
        left += len(need - set(o) - set(s))
    n['own'], n['seed'], n['left'], n['built'] = own, seed, left, built
    n['equal_rows'] = sum(e['nonblank'] for e in m.values() if 'same_as' in e)
    r = review_rows()
    n['reviews'] = r
    full = [x for x in r if x['full']]
    samp = [x for x in r if not x['full']]
    n['full_n'], n['full_k'] = sum(x['n'] for x in full), sum(x['k'] for x in full)
    n['samp_n'], n['samp_k'] = sum(x['n'] for x in samp), sum(x['k'] for x in samp)
    n['out'] = sum(x['out'] for x in r)
    n['unsampled'] = n['rows'] - n['full_n'] - n['samp_n']
    n['share'] = n['samp_k'] / n['samp_n']
    n['est_left'] = n['share'] * n['unsampled']
    return n


def fmt(i):
    return '{:,}'.format(i)


def pct(k, n):
    return '%.1f %%' % (100.0 * k / n) if n else 'n/a'


def chart(rows):
    """Horizontal bars: share of the checked rows that a review corrected. One hue. Light surface."""
    W, LEFT, RIGHT, ROW, BAR = 940, 452, 150, 26, 12
    import math
    xmax = float(max(3, math.ceil(max(100.0 * r['k'] / r['n'] for r in rows) + 0.2)))
    ticks = list(range(0, int(xmax) + 1))
    plot = W - LEFT - RIGHT

    def X(v):
        return LEFT + plot * v / xmax
    groups = [('Full review: the reviewer checked every row', [r for r in rows if r['kind'] == 'full']),
              ('Mixed review: every row of a part of the files, and a random sample of the rest', [r for r in rows if r['kind'] == 'mixed']),
              ('Sampled review: the reviewer checked a random sample of the rows', [r for r in rows if r['kind'] == 'sample'])]
    groups = [g for g in groups if g[1]]
    y = 34
    out = []
    body = []
    for title, rs in groups:
        body.append('<text x="0" y="%d" class="grp">%s</text>' % (y, E(title)))
        y += 12
        top = y
        for r in rs:
            v = 100.0 * r['k'] / r['n']
            cy = y + ROW / 2
            tip = '%d of %s checked rows corrected (%s). Review %s: %s.' % (r['k'], fmt(r['n']), pct(r['k'], r['n']), r['name'], r['label'])
            if r['out']:
                tip += ' %d more rows corrected outside the sample.' % r['out']
            body.append('<g class="row" tabindex="0" data-tip="%s">' % E(tip, quote=True))
            body.append('<title>%s</title>' % E(tip))
            body.append('<rect class="hit" x="0" y="%d" width="%d" height="%d"/>' % (y, W, ROW))
            body.append('<text x="0" y="%.1f" class="name"><tspan class="rid">%s</tspan> %s</text>' % (cy + 4, E(r['name']), E(r['label'])))
            if r['k']:
                x1 = X(min(v, xmax))
                rr = min(4, max(0.5, (x1 - LEFT) / 2))
                body.append('<path class="bar" d="M%.1f %.1f H%.1f a%.1f %.1f 0 0 1 %.1f %.1f V%.1f a%.1f %.1f 0 0 1 %.1f %.1f H%.1f Z"/>' % (
                    LEFT, cy - BAR / 2, x1 - rr, rr, rr, rr, rr, cy + BAR / 2 - rr, rr, rr, -rr, rr, LEFT))
            else:
                x1 = LEFT
            body.append('<text x="%.1f" y="%.1f" class="val">%d of %s (%s)</text>' % (x1 + 7, cy + 4, r['k'], fmt(r['n']), pct(r['k'], r['n'])))
            body.append('</g>')
            y += ROW
        # grid and baseline of this group
        g = []
        for t in ticks[1:]:
            g.append('<line class="grid" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>' % (X(t), top, X(t), y))
        g.append('<line class="base" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>' % (LEFT, top, LEFT, y))
        for t in ticks:
            g.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%d %%</text>' % (X(t), y + 15, t))
        out.append(''.join(g))
        y += 44
    H = y - 14
    svg = ['<svg class="viz-root" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-labelledby="ct cd">' % (W, H, W, H),
           '<title id="ct">Share of the checked rows that each review corrected</title>',
           '<desc id="cd">Horizontal bars, one per review. The table below the chart holds the same numbers.</desc>',
           '<text x="%d" y="14" class="axt">Corrected rows as a share of the checked rows (percent)</text>' % LEFT]
    svg += out + body + ['</svg>']
    return '\n'.join(svg)


def table(rows, n):
    o = ['<table class="num"><thead><tr><th>Review</th><th>Files</th><th>Kind</th><th>Rows checked</th><th>Rows corrected</th>'
         '<th>Share</th><th>More rows corrected outside the sample</th></tr></thead><tbody>']
    for r in rows:
        o.append('<tr><td>%s</td><td>%s</td><td>%s</td><td class="r">%s</td><td class="r">%d</td><td class="r">%s</td><td class="r">%s</td></tr>' % (
            E(r['name']), E(r['label']), r['kind'], fmt(r['n']), r['k'], pct(r['k'], r['n']), r['out'] if not r['full'] else 'n/a'))
    o.append('<tr class="sum"><td colspan="3">All full reviews</td><td class="r">%s</td><td class="r">%d</td><td class="r">%s</td><td class="r">n/a</td></tr>' % (
        fmt(n['full_n']), n['full_k'], pct(n['full_k'], n['full_n'])))
    o.append('<tr class="sum"><td colspan="3">All mixed and sampled reviews</td><td class="r">%s</td><td class="r">%d</td><td class="r">%s</td><td class="r">%d</td></tr>' % (
        fmt(n['samp_n']), n['samp_k'], pct(n['samp_k'], n['samp_n']), n['out']))
    o.append('</tbody></table>')
    return '\n'.join(o)


CSS = '''
:root { color-scheme: light; }
body { margin: 0; background: #ffffff; color: #191919; font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 28px 16px 60px; }
h1 { font-size: 28px; line-height: 1.2; margin: 0 0 6px; }
h2 { font-size: 20px; margin: 34px 0 8px; padding-top: 12px; border-top: 1px solid #e7e7e7; }
h3 { font-size: 16px; margin: 20px 0 6px; }
p, li { max-width: 78ch; }
.sub { color: #666666; margin: 0 0 18px; }
code { font: 14px/1.4 ui-monospace, "DejaVu Sans Mono", Menlo, Consolas, monospace; background: #f4f4f4; padding: 1px 4px; border-radius: 3px; overflow-wrap: anywhere; }
.short { background: #f4f8fe; border-left: 4px solid #257de0; padding: 10px 16px; margin: 14px 0; }
.short p { margin: 6px 0; }
.flow { display: flex; flex-wrap: wrap; align-items: stretch; gap: 8px; margin: 14px 0; }
.flow .box { flex: 1 1 200px; border: 1px solid #c2c2c2; border-radius: 6px; padding: 10px 12px; background: #ffffff; }
.flow .box b { display: block; margin-bottom: 4px; }
.flow .arrow { align-self: center; color: #666666; font-size: 22px; }
.figure { margin: 14px 0; overflow-x: auto; }
.viz-root { --surface-1: #ffffff; --text-primary: #191919; --text-secondary: #666666; --series-1: #257de0; --grid: #e7e7e7; --base: #c2c2c2; max-width: none; }
.viz-root text { font: 13px system-ui, -apple-system, "Segoe UI", sans-serif; fill: var(--text-primary); }
.viz-root .grp { font-weight: 600; font-size: 14px; }
.viz-root .axt, .viz-root .tick { fill: var(--text-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
.viz-root .rid { font-weight: 600; }
.viz-root .val { font-variant-numeric: tabular-nums; }
.viz-root .bar { fill: var(--series-1); }
.viz-root .grid { stroke: var(--grid); stroke-width: 1; }
.viz-root .base { stroke: var(--base); stroke-width: 1; }
.viz-root .hit { fill: transparent; }
.viz-root .row:hover .hit, .viz-root .row:focus .hit { fill: #f4f8fe; }
.viz-root .row:hover .bar, .viz-root .row:focus .bar { fill: #1b64be; }
.viz-root .row:focus { outline: none; }
#tip { position: fixed; display: none; max-width: 360px; background: #191919; color: #ffffff; padding: 8px 10px; border-radius: 6px; font-size: 13px; line-height: 1.4; pointer-events: none; z-index: 5; }
#tip b { display: block; font-size: 14px; }
.take { font-weight: 600; margin: 6px 0 14px; }
.cap { color: #666666; font-size: 14px; margin: 4px 0 12px; }
.tablewrap { overflow-x: auto; }
table { border-collapse: collapse; font-size: 14px; margin: 10px 0; }
th, td { border-bottom: 1px solid #e7e7e7; padding: 5px 10px; text-align: left; vertical-align: top; }
th { border-bottom: 1px solid #c2c2c2; font-weight: 600; }
td.r, th.r { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
tr.sum td { font-weight: 600; border-top: 1px solid #c2c2c2; }
details { margin: 12px 0; border: 1px solid #e7e7e7; border-radius: 6px; padding: 8px 14px; }
summary { cursor: pointer; font-weight: 600; }
.ref li { overflow-wrap: anywhere; }
.est { color: #666666; }
'''

JS = '''
(function () {
  var tip = document.getElementById('tip');
  function show(g, x, y) {
    var t = g.getAttribute('data-tip') || '';
    var cut = t.indexOf('. ');
    tip.textContent = '';
    var b = document.createElement('b');
    b.textContent = cut > 0 ? t.slice(0, cut + 1) : t;
    tip.appendChild(b);
    if (cut > 0) { tip.appendChild(document.createTextNode(t.slice(cut + 2))); }
    tip.style.display = 'block';
    var w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, x + 14)) + 'px';
    tip.style.top = Math.max(8, Math.min(window.innerHeight - h - 8, y + 14)) + 'px';
  }
  function hide() { tip.style.display = 'none'; }
  var rows = document.querySelectorAll('.viz-root .row');
  for (var i = 0; i < rows.length; i++) {
    (function (g) {
      g.addEventListener('pointermove', function (e) { show(g, e.clientX, e.clientY); });
      g.addEventListener('pointerleave', hide);
      g.addEventListener('focus', function () { var r = g.getBoundingClientRect(); show(g, r.left + 452, r.top + 4); });
      g.addEventListener('blur', hide);
    })(rows[i]);
  }
})();
'''


def ul(items):
    return '<ul>\n' + '\n'.join('<li>%s</li>' % x for x in items) + '\n</ul>'


def page(n):
    c = F.texts(n, fmt, pct)
    p = []
    w = p.append
    w('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">')
    w('<title>Line-by-line code pages: summary</title>\n<style>%s</style>\n</head>\n<body>\n<main>' % CSS)
    w('<h1>Line-by-line code pages: summary</h1>')
    w('<p class="sub">%s</p>' % c['sub'])
    w('<div class="short"><h2 style="border:0;margin:0;padding:0">Short version</h2>%s</div>' % ''.join('<p>%s</p>' % x for x in c['short']))
    w('<details><summary>Words used here</summary>%s</details>' % ul(c['words']))
    w('<h2>The puzzle: why no C page was in the rerun folder</h2>' + ul(c['puzzle']))
    w('<h2>What was built</h2>')
    w('<div class="flow"><div class="box"><b>Source</b>%s</div><div class="arrow">&rarr;</div><div class="box"><b>Explanations</b>%s</div>'
      '<div class="arrow">&rarr;</div><div class="box"><b>Pages</b>%s</div></div>' % (c['flow'][0], c['flow'][1], c['flow'][2]))
    w(ul(c['built']))
    w('<div class="tablewrap"><table class="num"><thead><tr><th>Language</th><th class="r">Files</th><th class="r">Rows (lines that are not blank)</th></tr></thead><tbody>')
    names = {'python': 'Python', 'c': 'C', 'bash': 'Bash', 'text': 'Text input files', 'make': 'Makefile'}
    for k, (a, b) in n['by'].items():
        w('<tr><td>%s</td><td class="r">%d</td><td class="r">%s</td></tr>' % (names[k], a, fmt(b)))
    w('<tr class="sum"><td>All</td><td class="r">%d</td><td class="r">%s</td></tr></tbody></table></div>' % (n['files'], fmt(n['rows'])))
    w('<h2>How the pages were checked</h2>' + ul(c['checked']))
    w('<h2>Results of the reviews</h2>' + ul(c['review_intro']))
    w('<div class="figure">%s</div>' % chart(n['reviews']))
    w('<p class="take">%s</p>' % c['take'])
    w('<p class="cap">%s</p>' % c['cap'])
    w('<div class="tablewrap">%s</div>' % table(n['reviews'], n))
    w(ul(c['review_after']))
    w('<h2>What is not done, and limits</h2>' + ul(c['limits']))
    w('<h2>Rules that were not kept during the work</h2>' + ul(c['rules']))
    w('<h2>Findings about the source code</h2>' + ul(c['findings_intro']))
    w('<h3>Points that touch a measurement or an analysis result</h3>' + ul(c['findings']))
    w('<h2>How to change a page</h2>' + ul(c['howto']))
    w('<h2>References</h2><ul class="ref">%s</ul>' % '\n'.join('<li>%s</li>' % x for x in c['refs']))
    w('</main>\n<div id="tip" role="tooltip"></div>\n<script>%s</script>\n</body>\n</html>' % JS)
    return '\n'.join(p)


def main(argv):
    n = numbers()
    if '--numbers' in argv:
        for k, v in n.items():
            if k != 'reviews':
                print(k, v)
        for r in n['reviews']:
            print(r)
        return 0
    text = page(n)
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(text)
    print('wrote %s: %d bytes' % (OUT, len(text.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
