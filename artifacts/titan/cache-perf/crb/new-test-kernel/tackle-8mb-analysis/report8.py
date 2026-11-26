#!/usr/bin/env python3
"""report8.py - the HTML report of new bwx8 runs (design tackle-8mb.md, deliverable 4).

Usage: report8.py FOLDER... [--margins FILE] [--note TEXT] -o report.html

FOLDER is a result folder of run_bwx8.sh. The page is self-contained: inline SVG drawn here, no script,
no external file, light background only.

This file decides nothing. Every decision word and every number of a rule comes from analyze8.summary().
A decision is printed through dec() only. A value that analyze8 left empty is printed as "no decision".
Raw rows (window rates of single trials, the load in the launch lines, schedule.tsv) are read here only
to draw the individual observations and to count the scheduled processes.
--note adds one more banner line (used for the synthetic example page).
"""
import argparse, json, math, os, re, sys
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze8 as A  # noqa: E402
from stage0 import (CSS, C0, C1, C2, INK, MUTED, GRID, LINE, e, table, svg, text, dot, ticks, xaxis, jit,  # noqa: E402
                    hist_lines)

OLD, NEW, ASM = A.OLD, A.NEW, A.ASM
KN = {OLD: 'old read', NEW: 'new read', ASM: 'assembly read'}
KS = {OLD: 'old', NEW: 'new', ASM: 'asm'}
KC = {OLD: C0, NEW: C1, ASM: C2}
DASH = '–'
TEST_BANNER = 'TEST DATA: stand-in kernels or shortened durations; no decision'
MAX_TRANSITIONS = 60        # rows of the transition list that the page prints; the count of every process is always printed
CSS8 = CSS + """
.banner{background:#fdecea;border:2px solid #b3261e;border-radius:6px;padding:10px 14px;margin:12px 0;font-weight:600}
.dec{font-weight:600} .nodec{color:#52514e}
.scroll{max-height:440px;overflow:auto;border:1px solid #e6e5e0;margin:8px 0} .scroll table{margin:0} .scroll.nw th{white-space:nowrap}
.lg b{width:11px;height:11px;margin-right:8px;display:inline-block} .lg u{width:18px;height:0;border-top:2px solid #0b0b0b;margin-right:8px;display:inline-block}
.lg em{width:9px;height:9px;border-radius:50%;margin-right:8px;display:inline-block;border:2px solid #52514e;background:#fff}
p.rule,div.rule{font-size:13px;color:#52514e}
"""


# ---------------------------------------------------------------- formats

def num(v, nd=2):
    return DASH if v is None else ('%.*f' % (nd, v)).replace('-', '−')


def sg(v, nd=2):
    return DASH if v is None else ('%+.*f' % (nd, v)).replace('-', '−')


def dec(x, none='no decision'):
    """The only place that prints a decision of analyze8."""
    if x is None:
        return '<span class="nodec">%s</span>' % none
    if x is True or x is False:
        x = 'yes' if x else 'no'
    return '<span class="dec">%s</span>' % e(str(x))


def dtext(x):
    """A decision as plain text, for a label inside a chart."""
    return 'no decision' if x is None else ('yes' if x is True else 'no' if x is False else str(x))


def ref(*n):
    return ''.join(' [Ref%d]' % i for i in n)


def several(values, nd=2, signed=True):
    return ', '.join((sg if signed else num)(v, nd) for v in values) if values else DASH


def rng(a, b, nd=2, signed=False):
    """'a to b', or one dash when there is no value."""
    fmt = sg if signed else num
    return DASH if a is None or b is None else '%s to %s' % (fmt(a, nd), fmt(b, nd))


def size_label(name):
    return '%s %s' % (name[:-1], {'K': 'KiB', 'M': 'MiB', 'G': 'GiB'}.get(name[-1], '')) if name[-1:] in 'KMG' else name + ' B'


def cell_parts(key):
    m = re.match(r'cpu(\d+)/s(\d+)', key)
    return int(m.group(1)), int(m.group(2))


def cell_name(key):
    return 'CPU %d, session %d' % cell_parts(key)


def cells_sorted(d):
    return sorted(d, key=cell_parts)


def sign_word(sign):
    return {1: 'positive', -1: 'negative'}.get(sign, DASH)


def scroll(t, nowrap=False):
    return '<div class="scroll%s">%s</div>' % (' nw' if nowrap else '', t)


def cap(s):
    return '<p class="cap">%s</p>' % s


def legend(items):
    """items: (kind, colour, label). kind: dot, ring, square, line, dash."""
    o = []
    for kind, col, lab in items:
        mark = {'dot': '<i style="background:%s"></i>' % col,
                'ring': '<em style="border-color:%s"></em>' % col,
                'square': '<b style="background:%s"></b>' % col,
                'line': '<u style="border-top-color:%s"></u>' % col,
                'dash': '<u style="border-top-color:%s;border-top-style:dashed"></u>' % col}[kind]
        o.append('<span class="lg">%s%s</span>' % (mark, e(lab)))
    return '<p>%s</p>' % ''.join(o)


# ---------------------------------------------------------------- chart helpers

def span(values, pad=0.08, floor0=False, min_width=0.2):
    v = [x for x in values if x is not None]
    if not v:
        return 0.0, 1.0
    lo, hi = min(v), max(v)
    if hi - lo < min_width:                 # a narrow range is widened around its centre, so that noise is not magnified
        mid = (lo + hi) / 2
        lo, hi = mid - min_width / 2, mid + min_width / 2
    w = hi - lo
    lo, hi = lo - pad * w, hi + pad * w
    return (min(0.0, lo) if floor0 else lo), hi


def nd_for(lo, hi):
    w = hi - lo
    return 0 if w >= 12 else 1 if w >= 1.2 else 2


def ring(x, y, r, col, title=None):
    t = '<title>%s</title>' % e(title) if title else ''
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#fff" stroke="%s" stroke-width="1.6">%s</circle>' % (x, y, r, col, t)


def square(x, y, r, col, title=None):
    t = '<title>%s</title>' % e(title) if title else ''
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="#fff" stroke-width="1.5">%s</rect>' % (
        x - r, y - r, 2 * r, 2 * r, col, t)


def vline(x, y0, y1, col=INK, w=1.5, dash=None):
    return '<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"%s/>' % (
        x, x, y0, y1, col, w, ' stroke-dasharray="%s"' % dash if dash else '')


def hline(x0, x1, y, col=LINE, w=1.0, dash=None, op=1.0):
    return '<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f" stroke-opacity="%.2f"%s/>' % (
        x0, x1, y, y, col, w, op, ' stroke-dasharray="%s"' % dash if dash else '')


def strip_chart(rows, xlabel, aria, L=250, R=250, W=920, rh=26, zero=False, marks=(), col=C0, lo=None, hi=None):
    """One row per item: small dots for the single values, a tick for the median, an optional band.
    rows: dict(label, values=[(v, title)], median, right, band=(a, b) or None, group=text or None).
    marks: (value, label) vertical annotation lines."""
    vals = [v for r in rows for v, _ in r['values']] + [r.get('median') for r in rows]
    vals += [x for r in rows if r.get('band') for x in r['band']] + [m[0] for m in marks]
    a, b = span(vals + ([0.0] if zero else []))
    lo, hi = (a if lo is None else lo), (b if hi is None else hi)
    top = 22 if marks else 12
    X = lambda v: L + (W - L - R) * (v - lo) / (hi - lo)
    n_grp = sum(1 for r in rows if r.get('group'))
    H = top + len(rows) * rh + n_grp * 20
    o = xaxis(X, lo, hi, top, H, xlabel, 6, nd_for(lo, hi))
    if zero and lo < 0 < hi:
        o.append(vline(X(0), top, H))
    for v, lab in marks:
        if lo <= v <= hi:
            o.append(vline(X(v), top, H, INK, 1.2, '4 3'))
            o.append(text(X(v), top - 6, lab, 'ax', 'middle'))
    y = top
    for r in rows:
        if r.get('group'):
            o.append(text(4, y + 14, r['group'], 'lab', 'start', ' font-weight="600"'))
            y += 20
        yc = y + rh / 2
        o.append(text(L - 10, yc + 4, r['label'], 'lab', 'end'))
        if r.get('band'):
            x0, x1 = X(max(lo, r['band'][0])), X(min(hi, r['band'][1]))
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#e6e5e0"><title>%s</title></rect>' % (
                x0, yc - 9, max(0.0, x1 - x0), 18, e(r.get('band_title', ''))))
        for j, (v, title) in enumerate(r['values']):
            if v is not None and lo <= v <= hi:
                o.append(dot(X(v), yc + jit(j) * 0.8, 2.8, r.get('col', col), title, 0.6, False))
        m = r.get('median')
        if m is not None and lo <= m <= hi:
            o.append(vline(X(m), yc - 10, yc + 10, INK, 2))
        if r.get('right2'):
            o.append(text(W - R + 12, yc - 2, r.get('right', ''), 'lab'))
            o.append(text(W - R + 12, yc + 11, r['right2'], 'ax'))
        else:
            o.append(text(W - R + 12, yc + 4, r.get('right', ''), 'lab'))
        y += rh
    return svg(W, H + 36, o, aria)


def panel(ox, oy, w, h, title, series, xmax, ymin, ymax, xlabel, sub=None, ylab=True, annot=True, R=8, endlabels=None):
    """A small line panel. series: (colour, [(x, y)], name, opacity, width, dash)."""
    L, T, B = 38, (34 if sub else 20), 28
    X = lambda v: ox + L + (w - L - R) * v / xmax
    Y = lambda v: oy + T + (h - T - B) * (ymax - v) / (ymax - ymin)
    nd = nd_for(ymin, ymax)
    o = [text(ox + L, oy + 12, title, 'lab', 'start', ' font-weight="600"')]
    if sub:
        o.append(text(ox + L, oy + 25, sub, 'ax'))
    for t in ticks(ymin, ymax, 4):
        o.append(hline(X(0), X(xmax), Y(t), GRID))
        if ylab:
            o.append(text(ox + L - 5, Y(t) + 4, num(t, nd), 'ax', 'end'))
    if annot:
        o += hist_lines(X(0), X(xmax), Y, ymin, ymax, label=False)
    for t in ticks(0, xmax, 4):
        o.append(text(X(t), oy + h - B + 13, num(t, nd_for(0, xmax)), 'ax', 'middle'))
    o.append(text(X(xmax), oy + h - 2, xlabel, 'ax', 'end'))
    for col, pts, name, op, sw, dash in series:
        if len(pts) > 1:
            o.append('<polyline fill="none" stroke="%s" stroke-width="%.1f" stroke-opacity="%.2f"%s points="%s">%s</polyline>' % (
                col, sw, op, ' stroke-dasharray="%s"' % dash if dash else '',
                ' '.join('%.1f,%.1f' % (X(a), Y(min(max(b, ymin), ymax))) for a, b in pts),
                '<title>%s</title>' % e(name) if name else ''))
    if annot:                                # the labels of the two annotation lines, drawn over the traces with a white edge
        for v, name in ((69.0, '69'), (70.5, '70.5')):
            if ymin < v < ymax:
                o.append(text(X(xmax) - 3, Y(v) - 4, name, 'val', 'end'))
    if endlabels:
        ends = sorted([Y(min(max(v, ymin), ymax)), name, col, dash] for v, name, col, dash in endlabels)
        for i in range(1, len(ends)):
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + 12)
        over = max(0, ends[-1][0] - (oy + h - B)) if ends else 0
        for y, name, col, dash in ends:
            o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2.2"%s/>' % (
                X(xmax) + 5, X(xmax) + 19, y - over, y - over, col, ' stroke-dasharray="%s"' % dash if dash else ''))
            o.append(text(X(xmax) + 23, y - over + 4, name, 'ax'))
    return o, X, Y


# ---------------------------------------------------------------- raw rows that the charts need

def proc_load(p):
    """(1 min load, runnable tasks, waited seconds, logins) of the launch line of one process."""
    f = (p.head.get('loadavg') or '').split()
    try:
        return float(f[0]), int(f[3].split('/')[0]), int(p.head.get('waited_s', '0')), int(p.head.get('logins', '0'))
    except (ValueError, IndexError):
        return None


def load_rows(procs):
    groups = {}
    for p in procs:
        groups.setdefault((p.step, p.session), []).append(p)
    out = []
    for (step, ses), ps in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
        v = [x for x in map(proc_load, ps) if x]
        d = dict(step=step, session=ses, n=len(ps), n_read=len(v), values=[(x[0], p.tag) for x, p in zip(v, ps)])
        if v:
            one = [x[0] for x in v]
            d.update(median=median(one), min=min(one), max=max(one), runnable_max=max(x[1] for x in v),
                     waited_max=max(x[2] for x in v), waited_sum=sum(x[2] for x in v), logins_max=max(x[3] for x in v))
        out.append(d)
    return out


def remaining_work(procs, paths):
    """Per step and session: the processes of schedule.tsv, those with complete output, and the rest."""
    sched, has, start = {}, {}, {}
    by_name = {os.path.basename(os.path.normpath(p)): p for p in paths}
    for p in procs:
        key = (p.step, p.session)
        if p.folder not in has.setdefault(key, {}):
            fn = os.path.join(by_name.get(p.folder, ''), 'schedule.tsv')
            has[key][p.folder] = os.path.isfile(fn)
            if has[key][p.folder]:
                with open(fn) as fh:
                    for line in fh.read().splitlines()[1:]:
                        f = line.split('\t')
                        if len(f) >= 2 and f[0].isdigit():
                            sched.setdefault(key, {})[int(f[0])] = f[1]
            env = os.path.join(by_name.get(p.folder, ''), 'env.txt')
            if os.path.isfile(env):
                with open(env) as fh:
                    m = re.search(r'## settings:.*?\bfrom=(\d+)', fh.read())
                    if m:
                        start.setdefault(key, {})[p.folder] = int(m.group(1))
    out = []
    for key in sorted(has, key=lambda k: (k[0], k[1] or 0)):
        ps = [p for p in procs if (p.step, p.session) == key]
        idx = lambda p: int(p.head['idx']) if p.head.get('idx', '').isdigit() else None
        done = {idx(p) for p in ps if p.status == 'ok'}
        d = dict(step=key[0], session=key[1], folders=sorted(has[key]), started=len(ps), complete=len(done),
                 not_ended=[p for p in ps if p.status != 'ok'], scheduled=None, remaining=None,
                 from_idx=start.get(key, {}))
        if all(has[key].values()) and key in sched:
            d['scheduled'] = len(sched[key])
            d['remaining'] = [(i, sched[key][i]) for i in sorted(sched[key]) if i not in done]
        out.append(d)
    return out


def ranges(ints):
    out, ints = [], sorted(ints)
    for i in ints:
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return ', '.join('%d' % a if a == b else '%d to %d' % (a, b) for a, b in out)


# ---------------------------------------------------------------- sections

WORDS = [
    ('8 MiB', '8,388,608 bytes. This is the buffer size called "8 MB" in the question.'),
    ('Rate', 'bytes read divided by measured elapsed time, in GB/s. One GB is 1,000,000,000 bytes.'),
    ('Old read, new read, assembly read', 'the read loops before the rewrite, after the rewrite, and written in assembly. Their names in the program are <code>oldread</code>, <code>read</code> and <code>asmread</code>. New read and assembly read are the load-only kernels.'),
    ('Kernel', 'one of these benchmark loops. It is not the Linux kernel.'),
    ('CRB', 'the Arm Phoenix Reference Server where the measurements run.'),
    ('bwx8', 'the benchmark program of this design. <b>run_bwx8.sh</b> starts its processes. <b>analyze8</b> is the analysis program that computes every number and decision of this page.'),
    ('Process', 'one start of bwx8. It has one fresh buffer (one allocation).'),
    ('Session', 'one complete set of processes. Session 2 starts at least 3 hours after session 1 ends.'),
    ('Trial', 'prefix, optional predecessor, and target, in that order, on one buffer and one CPU.'),
    ('Prefix', 'the same preparation loop before each trial. It is not assumed to reset the hardware.'),
    ('Predecessor', 'the loop deliberately run immediately before the loop being measured.'),
    ('Target', 'the loop whose subsequent rate is measured.'),
    ('Window', 'one measured period inside the prefix or target. The target has four windows. The fourth window is the primary value. The first window is shown beside it.'),
    ('Process rate', 'the median of the window rate over the four trials (repeats) of one condition in one process.'),
    ('Matched set', 'in Stage 2, the three processes (one per kernel) with the same replicate number, size, CPU and session. A CPU and session has six sets.'),
    ('Unit', 'the thing counted six times per CPU and session: a matched set in Stage 2, one process elsewhere.'),
    ('Gain', '100 × (new / old − 1), in percent.'),
    ('A/A value', 'median(repeat 1, repeat 3) − median(repeat 2, repeat 4) of one process, condition and window. Both halves ran the same condition.'),
    ('A/A spread', 'the largest absolute A/A value over the six processes of one CPU and session.'),
    ('Limit', 'the sum of the A/A spreads of the rates in a contrast. It measures variation inside processes only.'),
    ('Repeatable', 'the word for a contrast on one CPU and session whose median over the six units is above the limit in absolute value, with six values of one sign.'),
    ('Confirmed', 'repeatable in both sessions with the same sign on a CPU.'),
    ('P1', 'prediction 1: old read stays nearly constant from 1 MiB to 8 MiB. Equivalent means that every one of the six |difference| + limit values is at most 0.30 GB/s.'),
    ('P2', 'prediction 2: the load-only kernels lose rate from 1 MiB to 8 MiB.'),
    ('P3', 'prediction 3: old read stays stable across the variation of the load-only rate at 8 MiB, on one allocation.'),
    ('ΔG', 'the lost advantage, (new at 1 MiB − new at 8 MiB) − (old at 1 MiB − old at 8 MiB), in GB/s. Its two brackets are the new-read term and the old-read term.'),
    ('Gate', 'an acceptance check. It passes on a CPU and session only if |median difference| is at most the limit, the limit is below the margin, and |median difference| + limit is at most the margin.'),
    ('Margin', 'the largest difference that a gate may overlook, frozen in a file before the gate batch ran.'),
    ('Filtered, unfiltered', 'filtered leaves out trials with a disturbed mark or a coverage mark. Unfiltered keeps every trial with valid accounting. Decisions use the filtered estimate.'),
    ('Rejected', 'a trial left out of every estimate: interrupted, or its accounting or required records failed.'),
    ('Disturbed', 'a mark on a trial: thread CPU time below 99 % of the wall time, an involuntary context switch, or a gap above 100 µs before the target.'),
    ('Coverage change', 'a mark on a trial whose huge-page coverage (the part of the buffer on 2 MiB pages) differs between its two page readings.'),
    ('Steps', 'B6W: replay of the earlier B6 sequence. S2: Stage 2, one kernel and size per process. S4: Stage 4, 60 s of one kernel. P3G and S3G: prefix gates. P3: three kernels on one allocation. S3: Stage 3, mixed sequences. BIN: 10 ms bins against window records. CS, CM, C4: runs with counters.'),
    ('Counter', 'a hardware event count for the worker thread.'),
    ('System load', 'the 1 minute load average of Linux (mean number of runnable tasks), read directly before each process starts.'),
    ('est.', 'an estimate, not a measurement.'),
]


def sec_inputs(D):
    s = D['s']
    o = ['<h2>1. What this page is built from</h2><ul>',
         '<li>The page reports new runs of the design "explain the small read-bandwidth gain at 8 MiB"%s.</li>' % ref(1),
         '<li>The analysis program computed every number of a rule and every decision word%s. This page only draws them.</li>' % ref(3),
         '<li>The result folders are listed in the references%s.</li>' % ref(4),
         '<li>A dash (%s) in a table means that the analysis has no value there. The count columns and the exclusion table show why.</li></ul>' % DASH]
    rows = []
    for step, c in sorted(s['counts'].items()):
        rows.append([step, c['processes'], c['processes_not_ended'], c['trials'], c['rejected'], c['disturbed'],
                     c['coverage_change'], c['unfiltered'], c['filtered']])
    o.append(table(['step', 'processes', 'processes that did not end', 'trials', 'rejected trials', 'disturbed trials',
                    'trials with a coverage change', 'trials in the unfiltered estimate', 'trials in the filtered estimate'], rows))
    o.append(cap('Counts per step over all folders. B6W uses the old interval mode and has no trials.'))
    return o


def sec_load(D):
    rows = load_rows(D['procs'])
    o = ['<h2>2. System load before each process</h2>',
         '<p>run_bwx8.sh reads the system load directly before it starts each process and writes it into the launch line of that process%s. '
         'The chart shows the 1 minute load of every launch. The table gives the exact summary per step and session.</p>' % ref(8)]
    chart = [dict(label='%s, session %s' % (r['step'], r['session']), values=r['values'], median=r.get('median'),
                  right='median %s, highest %s, %d launches' % (num(r.get('median')), num(r.get('max')), r['n'])) for r in rows]
    o.append(strip_chart(chart, '1 minute load average before the launch (runnable tasks)', 'System load before each process, per step and session',
                         L=130, R=280, rh=20, lo=0.0))
    o.append(cap('One dot per launch. The black tick is the median of the row.'))
    o.append(table(['step', 'session', 'launches', 'load: median', 'lowest', 'highest', 'most runnable tasks at a launch',
                    'longest wait before a launch, s', 'all waits together, s', 'most users logged in'],
                   [[r['step'], r['session'], r['n'], num(r.get('median')), num(r.get('min')), num(r.get('max')),
                     r.get('runnable_max', DASH), r.get('waited_max', DASH), r.get('waited_sum', DASH), r.get('logins_max', DASH)] for r in rows], left=(0,)))
    o.append(cap('The run script waits up to 20 s before a launch while more than 2 tasks are runnable. The wait columns show how often that happened.'))
    return o


def kernel_medians(z, w, est='filtered'):
    return {k: z['rates'][k][w][est]['median'] for k in A.KERNELS}


def chart_s2(c, sizes, zoom):
    """Dumbbell per size: old read and new read (fourth window), assembly read as a third mark,
    the six process rates as small dots, the first-window medians as rings below."""
    W, L, R, top, rh = 920, 70, 215, 14, 58
    vals = []
    for z in sizes:
        for k in A.KERNELS:
            for w in ('fourth', 'first'):
                t = c['sizes'][z]['rates'][k][w]['filtered']
                vals += [t['median']] + [u['rate'] for u in t['units']]
    if zoom:
        lo, hi = span(vals, 0.06)
    else:
        lo, hi = 0.0, max([x for x in vals if x is not None] or [1.0]) * 1.02
    padl, padr = 70, 105           # px inside the plot for the value labels left and right of the marks
    X = lambda v: L + padl + (W - L - R - padl - padr) * (v - lo) / (hi - lo)
    H = top + len(sizes) * rh
    o = xaxis(X, lo, hi, top, H, 'rate, GB/s' + (' (the axis does not start at 0)' if zoom else ''), 7, nd_for(lo, hi))
    for i, z in enumerate(sizes):
        zz = c['sizes'][z]
        y = top + rh * i + rh / 2 - 6
        o.append(text(L - 10, y + 4, size_label(z), 'lab', 'end'))
        m4, m1 = kernel_medians(zz, 'fourth'), kernel_medians(zz, 'first')
        for k in A.KERNELS:
            for j, u in enumerate(zz['rates'][k]['fourth']['filtered']['units']):
                if u['rate'] is not None and lo <= u['rate'] <= hi:
                    o.append(dot(X(u['rate']), y + jit(j) * 0.5, 2.2, KC[k], '%s, set %s, fourth window: %s GB/s' % (KN[k], u['unit'], num(u['rate'])), 0.35, False))
        if m4[OLD] is not None and m4[NEW] is not None:
            o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (X(m4[OLD]), X(m4[NEW]), y, y, LINE))
        have = sorted((m4[k], k) for k in A.KERNELS if m4[k] is not None)
        for v, k in have:
            mk = square if k == ASM else dot
            o.append(mk(X(v), y, 4.5 if k == ASM else 5, KC[k], '%s, fourth window, median of %d processes: %s GB/s' % (
                KN[k], zz['rates'][k]['fourth']['filtered']['n_valid'], num(v))))
        for n, (v, k) in enumerate(have):
            lab = '%s %s' % (KS[k], num(v))
            if n == 0 and len(have) > 1 or len(have) == 1:
                o.append(text(X(v) - 9, y + 4, lab, 'val', 'end'))
            elif n == len(have) - 1:
                o.append(text(X(v) + 9, y + 4, lab + ' GB/s', 'val'))
            else:
                o.append(text(X(v), y - 9, lab, 'val', 'middle'))
        for k in A.KERNELS:
            if m1[k] is not None and lo <= m1[k] <= hi:
                o.append(ring(X(m1[k]), y + 17, 3.2, KC[k], '%s, first window, median: %s GB/s' % (KN[k], num(m1[k]))))
        g = zz['new_minus_old']['fourth']['filtered']['gain_pct']
        g1 = zz['new_minus_old']['first']['filtered']['gain_pct']
        if g['median'] is None:
            o.append(text(W - R + 14, y + 1, 'gain: no value', 'lab', 'start', ' font-weight="600"'))
            o.append(text(W - R + 14, y + 15, 'no set with all trials (filtered)', 'ax'))
        else:
            o.append(text(W - R + 14, y + 1, 'gain %s %%' % sg(g['median']), 'lab', 'start', ' font-weight="600"'))
            o.append(text(W - R + 14, y + 15, 'sets %s to %s %% (%d of 6)' % (sg(g['min']), sg(g['max']), g['n']), 'ax'))
        if g1['median'] is not None:
            o.append(text(W - R + 14, y + 28, 'first window %s %%' % sg(g1['median']), 'ax'))
    return svg(W, H + 36, o, 'Old-read, new-read and assembly-read rate by buffer size, fourth window, with the gain of new read over old read')


def contrast_rows(name, r, rate_names=None, gain=False):
    """Table cells of one contrast: filtered values, then the unfiltered median and the counts."""
    f, u = r['filtered'], r['unfiltered']
    cells = [name, sg(f['median'], 3), num(f['limit'], 3), several([x['value'] for x in f['units']], 3),
             rng(f['min'], f['max'], 3, True), num(f['range'], 3)]
    if gain:
        g = f['gain_pct']
        cells += [sg(g['median']), several([x.get('gain_pct') for x in f['units']]), rng(g['min'], g['max'], 2, True)]
    cells += [dec(f['state']), sg(u['median'], 3), '%d / %d' % (f['n_valid'], u['n_valid'])]
    return cells


CONTRAST_HEAD = ['contrast', 'median, GB/s', 'limit, GB/s', 'six unit values, GB/s', 'lowest to highest', 'range']
CONTRAST_TAIL = ['word of the rule', 'unfiltered median, GB/s', 'units with a value: filtered / unfiltered']


def s2_tables(c, sizes):
    o = []
    rows = []
    for z in sizes:
        zz = c['sizes'][z]
        rows.append(('grp', size_label(z)))
        for k in A.KERNELS:
            f4, u4 = zz['rates'][k]['fourth']['filtered'], zz['rates'][k]['fourth']['unfiltered']
            f1 = zz['rates'][k]['first']['filtered']
            rows.append([KN[k], num(f4['median'], 3), several([x['rate'] for x in f4['units']], 2, False),
                         rng(f4['min'], f4['max'], 3), num(f4['range'], 3), num(f4['spread'], 3),
                         num(f1['median'], 3), num(u4['median'], 3), '%d / %d' % (f4['n_valid'], u4['n_valid'])])
    o.append(table(['kernel', 'fourth window: median, GB/s', 'six process rates, GB/s', 'lowest to highest', 'range', 'A/A spread',
                    'first window: median, GB/s', 'unfiltered median, fourth window', 'processes with a rate: filtered / unfiltered'], rows, wrap=True))
    o.append(cap('Rates. Each process rate is the median of four trials. The six processes of one kernel are six different allocations.'))
    rows = []
    for z in sizes:
        zz = c['sizes'][z]
        rows.append(('grp', size_label(z)))
        for nm, lab in (('new_minus_old', 'new − old'), ('asm_minus_old', 'assembly − old')):
            for w in ('fourth', 'first'):
                rows.append(contrast_rows('%s, %s window' % (lab, w), zz[nm][w], gain=True))
    o.append(table(CONTRAST_HEAD + ['gain: median, %', 'six set gains, %', 'gain: lowest to highest, %'] + CONTRAST_TAIL, rows, wrap=True))
    o.append(cap('Differences and gains of the six matched sets. The limit omits the variation between processes, so it is not a bound on the uncertainty of the difference.'))
    return o


def sec_stage2(D):
    s2 = D['s'].get('stage2')
    o = ['<h2>3. Stage 2: old read against new read by buffer size</h2>']
    if not s2:
        return o + ['<p class="miss"><b>Insufficient data.</b> The folders hold no process of step S2. Next measurement: the Stage 2 size sweep (step S2).</p>']
    sizes = s2['sizes']
    o.append('<p>Each process ran one kernel at one size: a 1.2 s prefix of that kernel, then four target windows of 0.3 s, four times%s. '
             'The charts show the fourth window. The first window is shown as rings below it.</p>' % ref(1, 2))
    o.append(legend([('dot', C0, 'old read (median of the processes)'), ('dot', C1, 'new read'), ('square', C2, 'assembly read'),
                     ('ring', MUTED, 'first-window median, same colours'), ('line', LINE, 'old-to-new gap')]))
    for ck in cells_sorted(s2['cells']):
        c = s2['cells'][ck]
        o.append('<h3>%s</h3>' % cell_name(ck))
        if c.get('sentence', {}).get('text'):
            o.append('<p class="take">%s</p>' % e(c['sentence']['text']))
        o.append(chart_s2(c, sizes, False))
        o.append(cap('All sizes on one axis from 0. Small faint dots are the six process rates. The labels at the right give the gain of new read over old read: the median of the matched sets, their range, and the first-window median.'))
        near = [z for z in ('8M', '16M') if z in sizes]
        if near:
            o.append(chart_s2(c, near, True))
            o.append(cap('The same data at %s only, on a narrow axis. It shows whether the load-only rates approach or cross the old-read rate.' % ' and '.join(size_label(z) for z in near)))
        o.append('<details><summary>Exact tables for %s: rates, differences, gains, all six set values</summary>' % cell_name(ck))
        o += s2_tables(c, sizes)
        o.append('</details>')
    o += s2_predictions(s2)
    return o


def s2_predictions(s2):
    cells = cells_sorted(s2['cells'])
    o = ['<h3>P1: is old read nearly constant from 1 MiB to 8 MiB?</h3>']
    have = [ck for ck in cells if 'P1' in s2['cells'][ck]]
    if not have:
        return o + ['<p class="miss"><b>Insufficient data.</b> P1, P2 and the decomposition need the sizes 1 MiB and 8 MiB. Next measurement: step S2 at both sizes.</p>']
    o.append('<p class="rule">Rule: d is old read at 8 MiB minus old read at 1 MiB in one matched set, fourth window. L is the limit (two A/A spreads). '
             'P1 is "equivalent" on a CPU and session only if every one of the six |d| + L values is at most %.2f GB/s. It is "contradicted" if the contrast is repeatable and its median is above %.2f GB/s in absolute value. Otherwise it is "undecided"%s.</p>' % (A.P1_MARGIN, A.P1_MARGIN, ref(1, 2)))
    rows, trows = [], []
    for ck in have:
        c = s2['cells'][ck]
        p, r = c['P1']['filtered'], c['P1_contrast']['filtered']
        vals = [(abs(u['value']) + r['limit'], 'set %s: |d| + L = %s GB/s' % (u['unit'], num(abs(u['value']) + r['limit'], 3)))
                for u in r['units'] if u['value'] is not None and r['limit'] is not None]
        rows.append(dict(label=cell_name(ck), values=vals, median=None,
                         right=('largest %s GB/s: %s' % (num(p['largest_abs_plus_limit'], 3), dtext(p['outcome']))) if vals
                         else 'no set with a value: %s' % dtext(p['outcome'])))
        pu = c['P1']['unfiltered']
        trows.append([cell_name(ck), several([u['value'] for u in r['units']], 3), num(p['limit'], 3),
                      several([abs(u['value']) + r['limit'] if u['value'] is not None and r['limit'] is not None else None for u in r['units']], 3, False),
                      num(p['largest_abs_plus_limit'], 3), num(p['margin']), dec(p['outcome']), sg(p['median'], 3), dec(r['state']),
                      num(pu['largest_abs_plus_limit'], 3), dec(pu['outcome']), '%d / %d' % (r['n_valid'], c['P1_contrast']['unfiltered']['n_valid'])])
    o.append(strip_chart(rows, '|d| + L of each matched set, GB/s', 'P1: the six values of |difference| + limit per CPU and session against the 0.30 GB/s margin',
                         L=150, R=300, marks=((A.P1_MARGIN, 'margin %.2f GB/s' % A.P1_MARGIN),), lo=0.0))
    o.append(cap('One dot per matched set. The dashed line is the margin of P1.'))
    o.append(table(['CPU and session', 'six d values, GB/s', 'L, GB/s', 'six |d| + L values, GB/s', 'largest |d| + L', 'margin', 'P1', 'median d', 'word of the rule for d',
                    'unfiltered: largest |d| + L', 'unfiltered: P1', 'sets with a value: filtered / unfiltered'], trows, wrap=True))
    o.append('<p>P1 per CPU: %s. Over all four CPU and session cells: %s.</p>' % (
        ', '.join('%s %s' % (k.replace('cpu', 'CPU '), dec(v['outcome'])) for k, v in sorted(s2['P1']['per_cpu'].items(), key=lambda kv: int(kv[0][3:]))),
        dec(s2['P1']['overall'])))
    o.append('<h3>P2: do the load-only kernels lose rate from 1 MiB to 8 MiB?</h3>')
    o.append('<p class="rule">Rule: d is the rate at 8 MiB minus the rate at 1 MiB in one matched set, fourth window. P2 is "supported" on a CPU if the contrast is repeatable and negative in both sessions, "contradicted" if repeatable and positive in both, otherwise "undecided"%s.</p>' % ref(1, 2))
    rows = []
    for k in (NEW, ASM):
        rows.append(('grp', KN[k]))
        for ck in have:
            rows.append(contrast_rows(cell_name(ck), s2['cells'][ck]['P2'][k]))
    o.append(table(['CPU and session'] + CONTRAST_HEAD[1:] + CONTRAST_TAIL, rows, wrap=True))
    for k in (NEW, ASM):
        o.append('<p>P2 for %s, per CPU: %s.</p>' % (KN[k], ', '.join(
            '%s %s' % (c.replace('cpu', 'CPU '), dec(v['outcome'])) for c, v in sorted(s2['P2'][k]['per_cpu'].items(), key=lambda kv: int(kv[0][3:])))))
    o.append('<p>Candidate explanation of the size comparison (old read at a core limit, new read limited by data supply at 8 MiB): the analysis returns %s%s.</p>' % (dec(s2['candidate']), ref(1)))
    o += s2_decomposition(s2, have)
    return o


def s2_decomposition(s2, have):
    o = ['<h3>Where the advantage of new read is lost between 1 MiB and 8 MiB</h3>',
         '<p>ΔG = (new at 1 MiB − new at 8 MiB) − (old at 1 MiB − old at 8 MiB), per matched set, fourth window%s. The bars show the median of each bracket.</p>' % ref(1)]
    W, L, R, top, rh = 920, 150, 300, 14, 50
    vals = [0.0]
    for ck in have:
        d = s2['cells'][ck]['decomposition']['filtered']
        vals += [d['new_term']['median'], d['old_term']['median']]
    lo, hi = span(vals, 0.12, floor0=True, min_width=1.0)
    X = lambda v: L + (W - L - R) * (v - lo) / (hi - lo)
    H = top + len(have) * rh
    b = xaxis(X, lo, hi, top, H, 'GB/s', 6, nd_for(lo, hi))
    b.append(vline(X(0), top, H))
    rows = []
    for i, ck in enumerate(have):
        d = s2['cells'][ck]['decomposition']
        f = d['filtered']
        y = top + rh * i + rh / 2
        b.append(text(L - 10, y + 4, cell_name(ck), 'lab', 'end'))
        for dy, key, col, name in ((-9, 'new_term', C1, 'new-read term'), (9, 'old_term', C0, 'old-read term')):
            v = f[key]['median']
            if v is None:
                continue
            x0, x1 = sorted((X(0), X(v)))
            b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="12" rx="3" fill="%s"><title>%s: %s GB/s</title></rect>' % (x0, y + dy - 6, max(x1 - x0, 1.0), col, name, sg(v, 3)))
            b.append(text(x1 + 6 if v >= 0 else x0 - 6, y + dy + 4, sg(v), 'val', 'start' if v >= 0 else 'end'))
        if f['dG']['median'] is None:
            b.append(text(W - R + 14, y + 4, 'ΔG: no value (no set with all trials)', 'lab', 'start', ' font-weight="600"'))
        else:
            b.append(text(W - R + 14, y - 4, 'ΔG median %s GB/s' % sg(f['dG']['median']), 'lab', 'start', ' font-weight="600"'))
            b.append(text(W - R + 14, y + 11, 'limit %s GB/s (four spreads)' % num(f['dG']['limit'], 3), 'ax'))
        sh = f['shares']
        rows.append([cell_name(ck), sg(f['new_term']['median'], 3), several([u['value'] for u in f['new_term']['units']], 3),
                     sg(f['old_term']['median'], 3), several([u['value'] for u in f['old_term']['units']], 3),
                     sg(f['dG']['median'], 3), num(f['dG']['limit'], 3), dec(f['resolved']),
                     ('%s %%' % num(sh['new_share_pct']['median'], 1)) if sh else DASH,
                     ('%s %%' % num(sh['old_share_pct']['median'], 1)) if sh else DASH,
                     sg(d['unfiltered']['dG']['median'], 3), '%d / %d' % (f['dG']['n_valid'], d['unfiltered']['dG']['n_valid'])])
    o.append(legend([('square', C1, 'new-read term: new at 1 MiB − new at 8 MiB'), ('square', C0, 'old-read term: old at 1 MiB − old at 8 MiB')]))
    o.append(svg(W, H + 36, b, 'The new-read term and the old-read term of the lost advantage, in GB/s, per CPU and session'))
    o.append(table(['CPU and session', 'new-read term: median, GB/s', 'six set values', 'old-read term: median, GB/s', 'six set values', 'ΔG median, GB/s', 'limit, GB/s',
                    'ΔG resolved', 'share of the new-read term', 'share of the old-read term', 'unfiltered ΔG median', 'sets with a value: filtered / unfiltered'], rows, wrap=True))
    o.append(cap('A share is printed only where the analysis returns ΔG as resolved. A share is the median over the sets of 100 × term / ΔG. It can be negative or above 100 %.'))
    o.append('<h3>The 8 MiB rate range of each kernel, and 8 MiB against 16 MiB</h3>')
    rows = []
    for ck in have:
        c = s2['cells'][ck]
        if 'range_8M' not in c:
            continue
        rows.append(('grp', cell_name(ck)))
        for k in A.KERNELS:
            f, u = c['range_8M'][k]['filtered'], c['range_8M'][k]['unfiltered']
            rows.append([KN[k], num(f['median'], 3), num(f['min'], 3), num(f['max'], 3), num(f['range'], 3), f['n_valid'],
                         num(u['min'], 3), num(u['max'], 3), num(u['range'], 3), u['n_valid']])
    o.append(table(['kernel', 'median, GB/s', 'lowest', 'highest', 'range', 'processes', 'unfiltered: lowest', 'highest', 'range', 'processes'], rows))
    o.append(cap('Fourth-window process rates at 8 MiB. The processes are different allocations. This is not a same-buffer test of P3.'))
    rows = []
    for ck in have:
        c = s2['cells'][ck]
        for k in (NEW, ASM):
            x = c.get('crossing', {}).get(k)
            if x:
                rows.append([cell_name(ck), '%s − old' % KS[k], sg(x['8M']['median'], 3), num(x['8M']['limit'], 3), sg(x['16M']['median'], 3),
                             num(x['16M']['limit'], 3), sg(x['change'], 3), dec(x.get('word'))])
    o.append(table(['CPU and session', 'difference', 'median at 8 MiB, GB/s', 'limit', 'median at 16 MiB, GB/s', 'limit', 'change from 8 to 16 MiB', 'word of the analysis'], rows, left=(0, 1)))
    o.append('<p class="rule">A change of sign between two repeatable differences means that the load-only rate crossed the old-read rate between 8 and 16 MiB. The grid has no size between them, so the crossing is not located more precisely.</p>')
    rows = []
    for name, cf in sorted(s2['confirm'].items()):
        rows.append([e(name.replace('_', ' ').replace('@', ' at ')), ] + [dec(v['confirmed']) + (' (%s)' % sign_word(v['sign']) if v['sign'] else '')
                                                                         for _, v in sorted(cf['per_cpu'].items(), key=lambda kv: int(kv[0][3:]))] + [dec(cf['confirmed_both'])])
    cpus = sorted({int(k[3:]) for cf in s2['confirm'].values() for k in cf['per_cpu']})
    o.append(table(['contrast, fourth window'] + ['confirmed on CPU %d' % c for c in cpus] + ['on both CPUs with one sign'], rows))
    o.append('<p class="rule">"Confirmed" needs the word repeatable in both sessions with the same sign. A gain that differs between the CPUs is a result per CPU.</p>')
    return o


def sec_stage4(D):
    S = [d for d in D['s'].get('sustained', []) if d['step'] == 'S4']
    o = ['<h2>4. Stage 4: sustained reads of one kernel</h2>']
    if not S:
        return o + ['<p class="miss"><b>Insufficient data.</b> The folders hold no process of step S4. Next measurement: the fixed sustained batch (step S4), 3 processes per kernel, CPU and session.</p>']
    o += sustained_block(S, 'S4')
    return o


def sustained_block(S, step):
    o = ['<p>Each process ran one kernel on one 8 MiB allocation, without a prefix and without another kernel%s. '
         'Each panel shows every window of every process of one kernel, CPU and session, in time order. The dashed lines at 69 and 70.5 GB/s are annotations from earlier reports. They classify nothing.</p>' % ref(1, 2)]
    ok = [d for d in S if d['trace']]
    cells = sorted({(d['cpu'], d['session']) for d in S})
    if ok:
        W = 920
        pw, ph = W // max(len(cells), 1), 158
        xmax = max(d['trace'][-1]['t_end_s'] for d in ok)
        b = []
        for ki, k in enumerate(A.KERNELS):
            mine = [d for d in ok if d['kernel'] == k]
            if not mine:
                continue
            lo, hi = span([x for d in mine for x in (d['min'], d['max'])], 0.15, min_width=1.0)
            for ci, (cpu, ses) in enumerate(cells):
                ser = [(KC[k], [((t['t_start_s'] + t['t_end_s']) / 2, t['rate']) for t in d['trace']],
                        'process %s (%s): median %s GB/s' % (d['proc'], d['tag'], num(d['median'])), 0.85, 1.2, None)
                       for d in mine if (d['cpu'], d['session']) == (cpu, ses)]
                pb, _, _ = panel(ci * pw, ki * ph, pw, ph, '%s, CPU %s, s%s' % (KN[k], cpu, ses), ser, xmax, lo, hi, 'seconds',
                                 sub='%d processes' % len(ser))
                b += pb
        o.append(svg(W, len(A.KERNELS) * ph, b, 'Step %s: the rate of every window of every sustained process, per kernel, CPU and session' % step))
        o.append(cap('Rate in GB/s against the time since the first window of the process. One line per process. The y axis is shared inside a kernel row and does not start at 0.'))
    rows = []
    for d in S:
        if d['trace'] is None:
            rows.append([KN.get(d['kernel'], DASH), d['cpu'], d['session'], d['proc'], e(str(d['tag'])), 'no trace: ' + e('; '.join(map(str, d['why']))), DASH, DASH, DASH, DASH, DASH, DASH, e(d['load'] or DASH)])
        else:
            rows.append([KN[d['kernel']], d['cpu'], d['session'], d['proc'], e(str(d['tag'])), d['n'], num(d['median'], 3), num(d['min'], 3), num(d['max'], 3),
                         num(d['whole_rate'], 3), len(d['transitions']), e('; '.join(d['marks']) or 'none'), e((d['load'] or DASH).split()[0])])
    o.append(scroll(table(['kernel', 'CPU', 'session', 'process', 'tag', 'windows', 'median, GB/s', 'lowest', 'highest', 'bytes over time, whole trace',
                           'steps above %.2f GB/s' % A.STEP_CHANGE, 'marks of the trial', '1 minute load before'], rows, left=(0, 4, 11), wrap=True)))
    o.append(cap('"Steps" counts the pairs of successive windows whose rates differ by more than %.2f GB/s. This limit is a choice of the analysis program, not a hardware constant.' % A.STEP_CHANGE))
    tr = [(d, t) for d in ok for t in d['transitions']]
    o.append('<h3>Transitions of step %s</h3>' % step)
    if not tr:
        o.append('<p>No pair of successive windows differs by more than %.2f GB/s in any of the %d traces.</p>' % (A.STEP_CHANGE, len(ok)))
    else:
        shown = tr[:MAX_TRANSITIONS]
        o.append(scroll(table(['kernel', 'CPU', 'session', 'process', 'at, s', 'rate before, GB/s', 'rate after, GB/s', 'change, GB/s'],
                              [[KN[d['kernel']], d['cpu'], d['session'], d['proc'], num(t['at_s'], 2), num(t['rate_before'], 3), num(t['rate_after'], 3), sg(t['change'], 3)] for d, t in shown])))
        if len(tr) > len(shown):
            o.append(cap('<b>Cut:</b> the list shows the first %d of %d transitions. The table above gives the count of every process, and the summary of analyze8 holds all of them.' % (len(shown), len(tr))))
        else:
            o.append(cap('All %d transitions. A transition is descriptive evidence until a controlled intervention can change it.' % len(tr)))
    return o


def p3_trials(procs, cpu, ses):
    """Raw trial rates of the P3 processes of one CPU and session, in time order."""
    out = []
    for u in A.proc_units(procs, 'P3', cpu, ses):
        p = u['procs'][None]
        out.append((p, [(n, t.tgt[0], t.rate('first'), t.rate('fourth'), bool(t.disturbed or t.coverage))
                        for n, t in sorted(p.trials.items()) if t.usable(False)]))
    return out


def sec_p3(D):
    P = D['s'].get('P3')
    if not P:
        return []
    o = ['<h2>5. P3: old read against the load-only kernels on one allocation</h2>',
         '<p>Each process ran old read, new read and assembly read on one 8 MiB allocation, each with its own 1.2 s prefix, four times%s. '
         'This is a relation across preparations on the same allocation. It is not proof that a hidden state persisted while the kernels changed.</p>' % ref(1),
         '<p class="rule">Rules, per CPU and session and per selecting kernel X (new read, then assembly read): without a passed prefix gate P3G the result is "Insufficient data". '
         'A process is unstable if its four fourth-window rates span more than %.2f GB/s or a trial has |first − fourth window| above %.2f GB/s: then "Insufficient data". '
         'A range of the six X medians below %.1f GB/s: "Insufficient data". Control limit = 2 × the largest |A/A value| of old read. '
         '"compatible" if the old-read range plus the control limit is at most %.2f GB/s. "contrary" if |old at the process of highest X − old at the process of lowest X| minus the control limit is above %.2f GB/s. Otherwise "undecided"%s.</p>'
         % (A.UNSTABLE, A.UNSTABLE, A.P3_COVERAGE, A.P3_MARGIN, A.P3_MARGIN, ref(2)),
         '<p>Prefix gate P3G passed: %s.</p>' % dec(P.get('gate_passed'), 'no decision (not evaluated, or test data)')]
    cells = cells_sorted(P['cells'])
    # scatter: old median against load-only median, one mark per process
    W, pw, ph = 920, 460, 300
    b = []
    for i, ck in enumerate(cells):
        rows = P['cells'][ck]['filtered']['processes']
        xs = [r['kernels'][k]['median'] for r in rows for k in (NEW, ASM)]
        ys = [r['kernels'][OLD]['median'] for r in rows]
        (xlo, xhi), (ylo, yhi) = span(xs, 0.12, min_width=0.6), span(ys, 0.25, min_width=0.4)
        ox, oy = (i % 2) * pw, (i // 2) * ph
        L, R, T, B = 52, 16, 40, 40
        X = lambda v: ox + L + (pw - L - R) * (v - xlo) / (xhi - xlo)
        Y = lambda v: oy + T + (ph - T - B) * (yhi - v) / (yhi - ylo)
        b.append(text(ox + L, oy + 14, cell_name(ck), 'lab', 'start', ' font-weight="600"'))
        for t in ticks(ylo, yhi, 4):
            b.append(hline(X(xlo), X(xhi), Y(t), GRID))
            b.append(text(ox + L - 6, Y(t) + 4, num(t, nd_for(ylo, yhi)), 'ax', 'end'))
        for t in ticks(xlo, xhi, 5):
            b.append(vline(X(t), Y(ylo), Y(yhi), GRID, 1))
            b.append(text(X(t), oy + ph - B + 14, num(t, nd_for(xlo, xhi)), 'ax', 'middle'))
        b.append(text(X(xhi), oy + ph - 8, 'load-only rate of the process, GB/s', 'ax', 'end'))
        b.append(text(ox + L, oy + 28, 'y: old-read rate of the process, GB/s', 'ax'))
        for r in rows:
            yv = r['kernels'][OLD]['median']
            for k, mk in ((NEW, dot), (ASM, square)):
                xv = r['kernels'][k]['median']
                if xv is None or yv is None:
                    continue
                bad = r['kernels'][k]['unstable'] or r['kernels'][OLD]['unstable']
                if bad:
                    b.append('<circle cx="%.1f" cy="%.1f" r="9" fill="none" stroke="%s" stroke-width="1.5"/>' % (X(xv), Y(yv), INK))
                b.append(mk(X(xv), Y(yv), 4.5, KC[k], 'process %s: %s %s GB/s, old read %s GB/s%s' % (r['proc'], KN[k], num(xv), num(yv), ', unstable' if bad else '')))
    o.append(legend([('dot', C1, 'x = new-read rate of the process'), ('square', C2, 'x = assembly-read rate of the process'), ('ring', INK, 'process with an instability mark')]))
    o.append(svg(W, ((len(cells) + 1) // 2) * ph, b, 'P3: fourth-window old-read rate of each process against its new-read and assembly-read rate, per CPU and session'))
    o.append(cap('One mark per process and load-only kernel. Each value is the median of four trials, fourth window, filtered estimate. Both axes do not start at 0.'))
    # trial traces
    o.append('<h3>Individual trials in time order, first and fourth window</h3>')
    o.append(legend([('dot', C0, 'old read, fourth window'), ('dot', C1, 'new read'), ('dot', C2, 'assembly read'), ('ring', MUTED, 'first window of the same trial'),
                     ('line', MUTED, 'median of the four fourth-window rates')]))
    for ck in cells:
        cpu, ses = cell_parts(ck)
        tr = p3_trials(D['procs'], cpu, ses)
        if not tr:
            continue
        rates = [x for _, ts in tr for t in ts for x in t[2:4]]
        lo, hi = span(rates, 0.08, min_width=1.0)
        nmax = max([t[0] for _, ts in tr for t in ts] + [1])
        n = len(tr)
        pw2, ph2 = W // max(n, 6), 170
        b = []
        med = {r['proc']: r for r in P['cells'][ck]['filtered']['processes']}
        for i, (p, ts) in enumerate(tr):
            pb, X, Y = panel(i * pw2, 0, pw2, ph2, 'process %s' % p.proc, [], nmax + 1, lo, hi, 'trial number', annot=False, ylab=(i == 0))
            b += pb
            for k in A.KERNELS:
                m = med.get(p.proc, {}).get('kernels', {}).get(k, {}).get('median')
                if m is not None:
                    b.append(hline(X(0), X(nmax + 1), Y(m), KC[k], 1.2, None, 0.55))
            for nn, k, r1, r4, marked in ts:
                if r1 is None or r4 is None:
                    continue
                x = X(nn + 0.5)
                b.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (x, x, Y(r1), Y(r4), KC[k]))
                b.append(ring(x, Y(r1), 2.4, KC[k], 'trial %d, %s, first window: %s GB/s' % (nn, KN[k], num(r1))))
                b.append(dot(x, Y(r4), 3.2, KC[k], 'trial %d, %s, fourth window: %s GB/s%s' % (nn, KN[k], num(r4), ' (marked trial)' if marked else ''), 1.0, False))
        o.append('<p><b>%s</b></p>' % cell_name(ck))
        o.append(svg(W, ph2, b, 'P3 %s: first-window and fourth-window rate of every trial of every process, in time order' % cell_name(ck)))
    o.append(cap('Rate in GB/s against the number of the trial in its process. One panel per process (one allocation). A thin line joins the first and fourth window of one trial. Every trial with valid accounting is drawn.'))
    # tables
    for ck in cells:
        c = P['cells'][ck]
        rows = []
        for r, ru in zip(c['filtered']['processes'], c['unfiltered']['processes']):
            for k in A.KERNELS:
                d, du = r['kernels'][k], ru['kernels'][k]
                rows.append([r['proc'], KN[k], num(d['median'], 3), several([d['fourth'].get(str(i), d['fourth'].get(i)) for i in A.REPS], 2, False),
                             several([d['first'].get(str(i), d['first'].get(i)) for i in A.REPS], 2, False), num(d.get('span'), 3), num(d.get('first_fourth'), 3),
                             sg(d['aa'], 3), dec(d['unstable']), num(du['median'], 3), e(d['why'] or '')])
        o.append('<details><summary>Exact table for %s: every process and kernel</summary>' % cell_name(ck))
        o.append(table(['process', 'kernel', 'median, fourth window, GB/s', 'four trials, fourth window', 'four trials, first window', 'span of the four fourth-window rates',
                        'largest |first − fourth|', 'A/A value', 'unstable', 'unfiltered median', 'why no value'], rows, left=(0, 1, 10), wrap=True))
        o.append('</details>')
    rows = []
    for ck in cells:
        c = P['cells'][ck]
        rows.append(('grp', cell_name(ck)))
        for x in (NEW, ASM):
            d, u = c['filtered'][x], c['unfiltered'][x]
            rows.append(['selected by ' + KN[x], dec(d['outcome']), e(d['why'] or ''), num(d.get('load_range'), 3), num(d.get('old_range'), 3), num(d.get('control_limit'), 3),
                         e(str(d.get('endpoint_max', DASH))), e(str(d.get('endpoint_min', DASH))), sg(d.get('old_endpoint_change'), 3),
                         e(', '.join(map(str, d['unstable'])) if d['unstable'] else ('none' if d['unstable'] is not None else DASH)), dec(u['outcome']), d['n_processes']])
    o.append('<h3>The two endpoint checks per CPU and session</h3>')
    o.append(table(['comparison', 'P3', 'reason', 'load-only range, GB/s', 'old-read range, GB/s', 'control limit, GB/s', 'process of the highest load-only rate',
                    'process of the lowest', 'old-read change between them, GB/s', 'unstable processes', 'unfiltered: P3', 'processes'], rows, left=(0, 2), wrap=True))
    o.append(cap('The endpoints are selected observations, not six confirmed interventions. A state dependence needs a new controlled batch before a mechanism is assigned.'))
    return o


S3_PRED = (('old', 'old read at 8 MiB', C0, None), ('new', 'new read at 8 MiB', C1, None), ('asm', 'assembly read at 8 MiB', C2, None),
           ('old1M', 'old read on the first 1 MiB', C0, '5 3'))
S3_NAMES = {'new_predecessor_on_old': 'old read after new read − after old read', 'asm_predecessor_on_old': 'old read after assembly read − after old read',
            'history_interaction': '(new − old) after new read − (new − old) after old read'}


def s3_traces(procs, cpu, ses):
    """{(target kernel, predecessor name): [[(elapsed s, rate) x 4 windows] per trial]} of every trial with valid accounting."""
    names = {v: k for k, v in A.PRED.items()}
    out = {}
    for u in A.proc_units(procs, 'S3', cpu, ses):
        for t in u['procs'][None].trials.values():
            if not t.usable(False) or not t.pred or ('pred', 0) not in t.W:
                continue
            end = t.W[('pred', 0)]['t1']
            pts = []
            for i in range(t.nwin):
                w = t.W.get(('target', i))
                if w and w['t1'] > w['t0']:
                    pts.append((((w['t0'] + w['t1']) / 2 - end) / 1e9, w['bytes'] / (w['t1'] - w['t0'])))
            if len(pts) == t.nwin and t.pred[:2] in names:
                out.setdefault((t.tgt[0], names[t.pred[:2]]), []).append(pts)
    return out


def sec_stage3(D):
    s3 = D['s'].get('stage3')
    if not s3:
        return []
    o = ['<h2>6. Stage 3: does the predecessor change the next measurement?</h2>',
         '<p>Every trial ran the common old-read prefix (1.2 s), one predecessor (0.3 s), then the target in four windows of 0.3 s%s. '
         'The panels show the target rate against the actual time since the end of the predecessor.</p>' % ref(1, 2),
         legend([('line', C0, 'after old read at 8 MiB'), ('line', C1, 'after new read at 8 MiB'), ('line', C2, 'after assembly read at 8 MiB'),
                 ('dash', C0, 'after old read on the first 1 MiB')])]
    W = 920
    for ck in cells_sorted(s3['cells']):
        cpu, ses = cell_parts(ck)
        tr = s3_traces(D['procs'], cpu, ses)
        if not tr:
            continue
        pw, ph = W // 3, 210
        xmax = max(p[0] for v in tr.values() for pts in v for p in pts) * 1.06
        b = []
        for ti, tk in enumerate(A.KERNELS):
            allr = [p[1] for (t, _), v in tr.items() if t == tk for pts in v for p in pts]
            lo, hi = span(allr, 0.08, min_width=1.0)
            ser, ends = [], []
            for pn, plab, col, dash in S3_PRED:
                v = tr.get((tk, pn), [])
                ser += [(col, pts, None, 0.10, 0.8, dash) for pts in v]
            for pn, plab, col, dash in S3_PRED:
                v = tr.get((tk, pn), [])
                if v:
                    med = [(median(pts[i][0] for pts in v), median(pts[i][1] for pts in v)) for i in range(len(v[0]))]
                    ser.append((col, med, 'target %s after %s: median of %d trials per window' % (KN[tk], plab, len(v)), 1.0, 2.2, dash))
                    ends.append((med[-1][1], {'old': 'after old', 'new': 'after new', 'asm': 'after asm', 'old1M': 'after old 1M'}[pn], col, dash))
            pb, X, Y = panel(ti * pw, 0, pw, ph, 'target: %s' % KN[tk], ser, xmax, lo, hi, 'seconds since the predecessor ended', annot=False, R=94, endlabels=ends)
            b += pb
        o.append('<p><b>%s</b></p>' % cell_name(ck))
        o.append(svg(W, ph, b, 'Stage 3 %s: target rate in the four windows after each predecessor' % cell_name(ck)))
    o.append(cap('Rate in GB/s. Thin lines: every trial with valid accounting. Thick lines: the median of those trials in each window, at the median of the actual window centres. The y axis does not start at 0.'))
    o.append('<h3>Primary contrasts with their limits</h3>')
    o.append('<p class="rule">Rule: a contrast is "repeatable" on a CPU and session if its median over the six processes is outside the grey band (± the limit) and all six values have one sign. '
             'The first window is the primary test of immediate history. The fourth window is the persistence check%s.</p>' % ref(1))
    for ck in cells_sorted(s3['cells']):
        c = s3['cells'][ck]
        rows = []
        for name in ('new_predecessor_on_old', 'asm_predecessor_on_old', 'history_interaction'):
            for w in ('first', 'fourth'):
                f = c['primary'][name][w]['filtered']
                rows.append(dict(label='%s, %s window' % ({'new_predecessor_on_old': 'new predecessor on old read', 'asm_predecessor_on_old': 'assembly predecessor on old read',
                                                          'history_interaction': 'history interaction of the gain'}[name], w),
                                 values=[(u['value'], 'process %s: %s GB/s' % (u['unit'], sg(u['value'], 3))) for u in f['units'] if u['value'] is not None],
                                 median=f['median'], band=(-f['limit'], f['limit']) if f['limit'] is not None else None,
                                 band_title='limit ± %s GB/s' % num(f['limit'], 3),
                                 right='median %s, limit %s GB/s' % (sg(f['median']), num(f['limit'])), right2=dtext(f['state'])))
        o.append('<p><b>%s</b></p>' % cell_name(ck))
        o.append(strip_chart(rows, 'difference, GB/s', 'Stage 3 %s: the six process values of each primary contrast, with the limit band' % cell_name(ck), L=290, R=250, rh=34, zero=True))
    o.append(cap('One dot per process. Black tick: median. Grey band: from −limit to +limit. A negative value in the first two rows means that old read is slower after that predecessor than after old read.'))
    rows = []
    for ck in cells_sorted(s3['cells']):
        c = s3['cells'][ck]
        rows.append(('grp', cell_name(ck)))
        for name in ('new_predecessor_on_old', 'asm_predecessor_on_old', 'history_interaction'):
            for w in ('first', 'fourth'):
                rows.append(contrast_rows('%s, %s window' % (S3_NAMES[name], w), c['primary'][name][w]))
    o.append('<details><summary>Exact table of the primary contrasts</summary>' + table(CONTRAST_HEAD + CONTRAST_TAIL, rows, wrap=True) + '</details>')
    rows = []
    for name in ('new_predecessor_on_old', 'asm_predecessor_on_old', 'history_interaction'):
        for w in ('first', 'fourth'):
            cf = s3['confirm'].get(name, {}).get(w)
            if cf:
                rows.append([S3_NAMES[name], w] + [dec(v['confirmed']) + (' (%s)' % sign_word(v['sign']) if v['sign'] else '')
                                                    for _, v in sorted(cf['per_cpu'].items(), key=lambda kv: int(kv[0][3:]))] + [dec(cf['confirmed_both'])])
    cpus = sorted({int(k[3:]) for ws in s3['confirm'].values() for cf in ws.values() for k in cf['per_cpu']})
    o.append(table(['contrast', 'window'] + ['confirmed on CPU %d' % c for c in cpus] + ['on both CPUs with one sign'], rows, left=(0, 1)))
    o.append(cap('The assembly-predecessor contrast is a secondary replication. It does not replace the new-predecessor contrast.'))
    o.append('<h3>Gain of new read over old read after each predecessor</h3>')
    rows = []
    for ck in cells_sorted(s3['cells']):
        c = s3['cells'][ck]
        rows.append(('grp', cell_name(ck)))
        for pn, plab, _, _ in S3_PRED:
            for w in ('first', 'fourth'):
                r = c['gain_pct'][pn][w]
                f, u = r['filtered'], r['unfiltered']
                g = f['gain_pct']
                rows.append(['after ' + plab, w, sg(g['median']), several([x.get('gain_pct') for x in f['units']]), rng(g['min'], g['max'], 2, True),
                             sg(f['median'], 3), num(f['limit'], 3), sg(u['gain_pct']['median']), '%d / %d' % (f['n_valid'], u['n_valid'])])
    o.append(table(['predecessor', 'window', 'gain: median, %', 'six process gains, %', 'lowest to highest, %', 'new − old: median, GB/s', 'limit, GB/s', 'unfiltered gain: median, %',
                    'processes with a value: filtered / unfiltered'], rows, left=(0, 1), wrap=True))
    o.append(cap('Rate differences in GB/s are decided first. The percentages describe their size.'))
    rows = []
    for ck in cells_sorted(s3['cells']):
        c = s3['cells'][ck]
        rows.append(('grp', cell_name(ck)))
        for pn, plab, _, _ in S3_PRED:
            for w in ('first', 'fourth'):
                d = c.get('gain_change_pp', {}).get(pn, {}).get(w)
                if d:
                    f, u = d['filtered'], d['unfiltered']
                    rows.append(['after ' + plab, w, sg(f['median']), several(f['units']), rng(f['min'], f['max'], 2, True),
                                 sg(u['median']), '%d / %d' % (f['n'], u['n'])])
    o.append('<h3>Change of the gain against the old-read predecessor</h3>')
    o.append(table(['predecessor', 'window', 'change of gain: median, percentage points', 'six process values, percentage points',
                    'lowest to highest, percentage points', 'unfiltered: median, percentage points',
                    'processes with a value: filtered / unfiltered'], rows, left=(0, 1), wrap=True))
    o.append(cap('Each value is the gain of one process after the named predecessor minus its gain after old read. '
                 'The decision on the history contrast is made in GB/s above, not on these values.'))
    rows = []
    for ck in cells_sorted(s3['cells']):
        for k, ws in sorted(s3['cells'][ck].get('previous_target', {}).items()):
            for w in ('first', 'fourth'):
                x = ws.get(w)
                if x:
                    rows.append([cell_name(ck), KN.get(k, k), w, num(x['span'], 3), e('; '.join('after target %s: %s (%d trials)' % (KN.get(p, p), sg(v['median_deviation'], 3), v['n'])
                                                                                                 for p, v in sorted(x['by_previous_target'].items())))])
    o.append('<details><summary>Diagnostic: does the target of the previous trial matter? (descriptive)</summary>')
    o.append(table(['CPU and session', 'target', 'window', 'span of the group medians, GB/s', 'median deviation from the own process and condition, by the target of the previous trial, GB/s'], rows, left=(0, 1, 2, 4), wrap=True))
    o.append('</details>')
    rows = []
    for ck in cells_sorted(s3['cells']):
        rows.append(('grp', cell_name(ck)))
        for r in s3['cells'][ck]['exploratory']:
            f = r['filtered']
            rows.append([e(f['label'].replace('exploratory: ', '')), sg(f['median'], 3), num(f['limit'], 3), rng(f['min'], f['max'], 3, True), dec(f['state']),
                         sg(r['unfiltered']['median'], 3), '%d / %d' % (f['n_valid'], r['unfiltered']['n_valid'])])
    o.append('<details><summary>Other predecessor and target contrasts (exploratory: a mechanism chosen from them needs a new confirmation schedule)</summary>')
    o.append(table(['contrast', 'median, GB/s', 'limit, GB/s', 'lowest to highest', 'word of the rule', 'unfiltered median', 'processes: filtered / unfiltered'], rows))
    o.append('</details>')
    return o


def sec_gates(D):
    G = D['s'].get('gates') or {}
    if not G:
        return []
    o = ['<h2>7. Gates: acceptance checks before a conclusion may use a prefix or a measurement mode</h2>',
         '<p class="rule">Rule: a gate contrast is the difference inside a process between two previous activities or two measurement modes. It gets the word "pass" on a CPU and session only if |median| is at most the limit, the limit is below the frozen margin, and |median| + limit is at most the margin. '
         '"precision insufficient": the limit is at or above the margin, or the median is inside the limit but |median| + limit is above the margin. "resolved difference": the contrast is repeatable. "not established": the rest. '
         'Every contrast of a use must pass on both CPUs in both sessions%s.</p>' % ref(1, 2)]
    if D['margins']:
        o.append('<p>The margins come from the frozen file of the forecast command%s.</p>' % ref(5))
    for step in A.GATE_STEPS:
        g = G.get(step)
        if not g:
            continue
        o.append('<h3>Gate step %s</h3>' % step)
        o.append('<p>Statement of the analysis: %s.</p>' % dec(g.get('statement')))
        uses = g.get('uses') or {}
        if not uses:
            continue
        rows, chart = [], []
        for name in sorted(uses):
            u = uses[name]
            cnt = u.get('counts')
            rows.append([e(name), {'one_rate': 'one rate (2 spreads)', 'two_rate': 'two-rate difference (4 spreads)', 'four_rate': 'four-rate interaction (8 spreads)'}.get(u['quantity'], u['quantity']),
                         num(u['margin']), 'yes' if u.get('clipped') else 'no', dec(u.get('margin_forecast')), dec(u.get('overall')),
                         e(', '.join('%s: %d' % kv for kv in sorted(cnt.items()))) if cnt else dec(None)])
            first = True
            for ck in cells_sorted(u['cells']):
                cs = u['cells'][ck]['contrasts']
                vals = [(abs(r['filtered']['median']) + r['filtered']['limit'], '%s: |median| + limit = %s GB/s' % (r['filtered']['label'], num(abs(r['filtered']['median']) + r['filtered']['limit'], 3)))
                        for r in cs if r['filtered']['median'] is not None and r['filtered']['limit'] is not None and r['filtered']['complete']]
                chart.append(dict(group='%s, margin %s GB/s' % (name, num(u['margin'])) if first else None, label=cell_name(ck), values=vals, median=None,
                                  right='%d of %d contrasts with 6 units' % (len(vals), len(cs))))
                first = False
        o.append(table(['use', 'quantity', 'margin, GB/s', 'margin clipped', 'forecast of the margins file', 'overall', 'contrasts per word'], rows, left=(0, 1, 6)))
        margins = sorted({uses[n]['margin'] for n in uses})
        o.append(strip_chart(chart, '|median| + limit of each contrast, GB/s', 'Gate step %s: |median| + limit of every complete contrast per use, CPU and session' % step,
                             L=150, R=250, rh=20, marks=tuple((m, 'margin %s' % num(m)) for m in margins), lo=0.0))
        o.append(cap('One dot per contrast with six complete units. A contrast can pass only if its dot lies at or left of the margin of its use (dashed line). '
                     'The analysis evaluates a gate on the CPUs %s only.' % ' and '.join(str(c) for c in A.CPUS)))
        rows = []
        for name in sorted(uses):
            u = uses[name]
            for ck in cells_sorted(u['cells']):
                rows.append(('grp', '%s, %s' % (e(name), cell_name(ck))))
                for r in u['cells'][ck]['contrasts']:
                    f, un = r['filtered'], r['unfiltered']
                    rows.append([e(f['label']), sg(f['median'], 3), num(f['limit'], 3), num(f['margin']), sg(None if f['median'] is None or f['limit'] is None else f['margin'] - abs(f['median']) - f['limit'], 3),
                                 num(f['max_passing_median'], 3), dec(f['outcome']), sg(un['median'], 3), dec(un['outcome']), '%d / %d' % (f['n_valid'], un['n_valid'])])
        o.append('<details><summary>Every contrast of gate step %s (%d rows)</summary>' % (step, sum(1 for r in rows if not isinstance(r, tuple))))
        o.append(scroll(table(['contrast', 'median, GB/s', 'limit, GB/s', 'margin, GB/s', 'margin − |median| − limit', 'largest median that could pass', 'outcome',
                               'unfiltered median', 'unfiltered outcome', 'processes with a value: filtered / unfiltered'], rows)))
        o.append('</details>')
    return o


def sec_b6w(D):
    B = D['s'].get('B6W')
    if not B:
        return []
    o = ['<h2>8. B6W: replay of the earlier B6 sequence</h2>',
         '<p>Each process replayed the 13-entry sequence of the earlier experiment B6 for four rounds with the unchanged interval wrapper%s. '
         'It holds 8 pairs of consecutive old-read intervals directly after assembly read.</p>' % ref(1, 2),
         '<p class="rule">Rule: the positional effect is "reproduced" on a CPU and session only if the first interval is slower in all 8 pairs in both processes. This check is descriptive and exempt from the six-process rule.</p>']
    chart, rows = [], []
    for ck in cells_sorted(B['cells']):
        c = B['cells'][ck]
        for p in c['processes']:
            n = sum(1 for x in p['pairs'] if x['first_slower'])
            d = [x['difference'] for x in p['pairs']]
            chart.append(dict(label='%s, process %s' % (cell_name(ck), p['proc']), values=[(x['difference'], 'round %d, positions %s: first %s, second %s GB/s' % (
                x['round'], x['positions'], num(x['first']), num(x['second']))) for x in p['pairs']], median=median(d) if d else None,
                right='%d of %d below 0, median %s' % (n, len(d), sg(median(d)) if d else DASH)))
            rows.append([cell_name(ck), p['proc'], e(str(p['tag'])), len(p['pairs']), n, sg(median(d), 3) if d else DASH,
                         '%s to %s' % (sg(min(d), 3), sg(max(d), 3)) if d else DASH,
                         num(median(x['first'] for x in p['pairs']), 3) if d else DASH, num(median(x['second'] for x in p['pairs']), 3) if d else DASH,
                         num(median(x['asm_before'] for x in p['pairs']), 3) if d else DASH, dec(p.get('all_slower')), e('; '.join(p['why']))])
    o.append(strip_chart(chart, 'first interval minus second interval, GB/s', 'B6W: paired difference of the first and second old-read interval after assembly read, per process', L=220, R=250, zero=True))
    o.append(cap('One dot per pair. A dot left of 0 means that the first old-read interval after assembly read was the slower one.'))
    o.append(table(['CPU and session', 'process', 'tag', 'pairs', 'pairs with the first interval slower', 'difference: median, GB/s', 'lowest to highest', 'first interval: median rate',
                    'second interval: median rate', 'assembly read before: median rate', 'first slower in all pairs', 'why not usable'], rows, left=(0, 2, 11), wrap=True))
    o.append('<p>%s</p>' % ' '.join('%s: reproduced %s%s.' % (cell_name(ck), dec(B['cells'][ck]['reproduced']), ' (%s)' % e(B['cells'][ck]['why']) if B['cells'][ck]['why'] else '')
                                    for ck in cells_sorted(B['cells'])))
    return o


def sec_counters(D):
    s = D['s']
    C = s.get('counters') or []
    C4 = [d for d in s.get('sustained', []) if d['step'] == 'C4']
    if not C and not C4:
        return []
    o = ['<h2>9. Counters</h2>',
         '<p class="miss"><b>Insufficient data: authoritative event definitions.</b> The table gives raw event names and counts. No cache mechanism is assigned to any event. '
         'Next source: the event definitions of the processor vendor for the event codes of these runs%s.</p>' % ref(1, 2),
         '<p>Counts are read once per target window in the mode with counter reads. A window with a failed, unsupported or multiplexed count is not interpreted and is left out of the count columns. '
         'Cycles per thread CPU second is a clock estimate (est.).</p>']
    one = {(p.folder, p.tag): p for p in D['procs']}
    items = [(c, c) for c in C] + [(d, d['counters']) for d in C4 if d.get('counters')]
    events = sorted({k for _, c in items for k in c['per_64B']})
    rows = []
    for ident, c in items:
        p = one.get((ident['folder'], ident['tag']))
        what = '%s at %s' % (KN[p.one[0]], size_label(A.size_name(p.one[1]))) if p is not None and p.one else 'predecessor and target in old read, new read'
        st = lambda x: '%s (%s to %s)' % (num(x['median'], 4), num(x['min'], 4), num(x['max'], 4)) if x and x['n'] else DASH
        rows.append([ident['step'], ident['cpu'], ident['session'], ident['proc'], what, c['windows'], c['interpretable']] +
                    [st(c['per_64B'].get(k)) for k in events] + [st(c['instructions_per_byte']), st(c['cycles_per_byte']),
                                                                 '%s' % (num(c['cycles_per_cpu_s']['median'] / 1e9, 4) if c['cycles_per_cpu_s']['n'] else DASH)])
    o.append(scroll(table(['step', 'CPU', 'session', 'process', 'kernel and size', 'windows with counter reads', 'windows interpreted'] +
                          ['%s per 64 B read' % e(k) for k in events] + ['instructions per byte', 'cycles per byte', 'cycles per thread CPU second, 1e9 (est.)'], rows, left=(0, 4)), True))
    o.append(cap('Each cell: median over the interpreted windows of the process (lowest to highest). Event names are the names given to bwx8 on its command line. A count is used for a conclusion only after the mode gate of its step passed (section 7).'))
    if C4:
        o.append('<h3>Sustained reads with counters (step C4)</h3>')
        o += sustained_block(C4, 'C4')
    return o


def sec_exclusions(D):
    s = D['s']
    ex = s['exclusions']
    o = ['<h2>10. Exclusion table</h2>',
         '<p>The table lists every process that did not end, every rejected trial and every marked trial, with the reason and the measured values%s. '
         'A rejected trial enters no estimate. A disturbed trial or a trial with a coverage change stays in the unfiltered estimate and is left out of the filtered one.</p>' % ref(1, 3)]
    count = {}
    for r in ex:
        count[(r['step'], r['kind'])] = count.get((r['step'], r['kind']), 0) + 1
    o.append(table(['step', 'kind of row', 'rows'], [[a, b, n] for (a, b), n in sorted(count.items())] or [[DASH, 'no row', 0]], left=(0, 1)))
    if ex:
        rows = []
        for r in ex:
            m = r.get('measured') or {}
            rows.append([r['step'], r['session'], r['cpu'], r['proc'], e(str(r['tag'])), DASH if r['trial'] is None else r['trial'], e(r.get('cond') or ''), r.get('rep', DASH), r['kind'],
                         e('; '.join(str(x) for x in r['reasons'])), num(None if m.get('cpu_fraction') is None else 100 * m['cpu_fraction'], 2), m.get('nivcsw', DASH) if m else DASH,
                         m.get('gap_ns', DASH) if m and m.get('gap_ns') is not None else DASH,
                         ('%s / %s' % (m.get('kB_huge_pre'), m.get('kB_huge_post'))) if m else DASH, num(m.get('rate_first')), num(m.get('rate_fourth')), e(r['folder'])])
        o.append(scroll(table(['step', 'session', 'CPU', 'process', 'tag', 'trial', 'condition', 'repeat', 'kind', 'reasons', 'thread CPU time, % of wall time', 'involuntary context switches',
                               'gap before the target, ns', 'huge pages before / after, kB', 'first window, GB/s', 'fourth window, GB/s', 'folder'], rows, left=(4, 6, 8, 9, 16)), True))
        o.append(cap('%d rows. The limits of the disturbed mark (99 %% of wall time, 0 involuntary context switches, 100,000 ns gap) are diagnostic choices of the design. The measured values are shown so that they can be judged directly.' % len(ex)))
    return o


def sec_stopped(D):
    s = D['s']
    R = remaining_work(D['procs'], D['paths'])
    o = ['<h2>11. Processes that did not end, and scheduled work that remains</h2>',
         '<p>The run script never repeats a process by itself. A stopped step keeps its folder. The count of scheduled processes comes from the copy of the schedule in each result folder%s.</p>' % ref(4, 8)]
    bad = [(d, p) for d in R for p in d['not_ended']]
    if bad:
        o.append(table(['step', 'session', 'CPU', 'process', 'tag', 'status', 'end line of the run script', 'trials with an S row', 'replaced by the complete process in folder', 'folder'],
                       [[p.step, p.session, p.cpu, p.proc, e(str(p.tag)), p.status, e(p.end_line or ''), len(p.trials), e(p.replaced_by or 'not replaced'), e(p.folder)] for _, p in bad], left=(4, 6, 8, 9), wrap=True))
    else:
        o.append('<p>Every process of every folder ended with status 0.</p>')
    for r in s.get('replaced', []):
        o.append('<p>Step %s, session %s, CPU %s, process %s of folder <code>%s</code> did not end (%s). Its %d trials are kept as partial observations and enter no estimate. '
                 'The complete process of folder <code>%s</code> is used in its place.</p>' % (r['step'], r['session'], r['cpu'], r['proc'], e(r['folder']), r['status'], r['trials'], e(r['replaced_by'])))
    rows = []
    for d in R:
        if d['scheduled'] is None:
            rem = '<b>Insufficient data</b>: a folder of this step has no schedule.tsv'
        elif not d['remaining']:
            rem = 'none'
        else:
            rem = '%d processes: idx %s' % (len(d['remaining']), ranges([i for i, _ in d['remaining']]))
        rows.append(('hi' if d['scheduled'] is not None and d['remaining'] else 'row', [d['step'], d['session'], DASH if d['scheduled'] is None else d['scheduled'], d['started'], d['complete'], len(d['not_ended']), rem,
                     e(', '.join('%s from idx %d' % (f, i) for f, i in sorted(d['from_idx'].items()) if i) or DASH)]))
    rows = [r if r[0] == 'hi' else r[1] for r in rows]
    o.append(table(['step', 'session', 'scheduled processes', 'launch lines in the folders', 'processes with complete output', 'processes that did not end', 'scheduled work that remains', 'continued with --from'], rows, left=(0, 6, 7), wrap=True))
    o.append(cap('A highlighted row has scheduled processes without complete output. Stop for a scheduling decision before a replacement batch is added.'))
    return o


def sec_explains(D):
    """The table of design lines 326 to 338. A conclusion is printed only where analyze8 returned its evidence."""
    s = D['s']
    s2, s3 = s.get('stage2'), s.get('stage3')
    test = s['test_data']
    ID = '<b>Insufficient data.</b> '
    rows = []

    def concl(t):
        return '<span class="concl">%s</span>' % t

    def cpus_confirmed(cf):
        return [(int(k[3:]), v['sign']) for k, v in sorted(cf['per_cpu'].items(), key=lambda kv: int(kv[0][3:])) if v['confirmed']]

    def medians(name, w):
        return '; '.join('%s: median %s GB/s, limit %s GB/s' % (cell_name(ck), sg(s3['cells'][ck]['primary'][name][w]['filtered']['median']), num(s3['cells'][ck]['primary'][name][w]['filtered']['limit']))
                         for ck in cells_sorted(s3['cells']))
    # row 1
    S4 = [d for d in s.get('sustained', []) if d['step'] == 'S4' and d['trace']]
    ev = ('%d sustained traces; %d of them have a step above %.2f GB/s between successive windows (section 4).' % (len(S4), sum(1 for d in S4 if d['transitions']), A.STEP_CHANGE)
          if S4 else 'No sustained trace.')
    rows.append(['Reproduced low and high rates', ev, ID + 'The analysis returns no decision that a low and a high rate were reproduced. The lines at 69 and 70.5 GB/s are annotations only. '
                 'Next measurement: ' + ('the fixed sustained batch (step S4).' if not S4 else 'a controlled intervention that changes a listed transition, chosen under Stage 5 of the design.')])
    # rows 2 and 3
    for name, result, allowed in (
            ('new_predecessor_on_old', 'Confirmed predecessor contrast', 'Recent execution history changes the rate of the target under this preparation.'),
            ('history_interaction', 'Confirmed change of the old-to-new gain in a mixed sequence',
             'History changes the gain measured in that mixed sequence. This does not explain the original run, which had no other read kernel as predecessor.')):
        if not s3:
            rows.append([result, 'No process of step S3.', ID + 'Next measurement: Stage 3 (step S3), after its prefix gate S3G, if the trigger of the design applies.'])
            continue
        cf = s3['confirm'][name]['first']
        got = cpus_confirmed(cf)
        ev = 'Contrast "%s", first window. Confirmed per CPU: %s. On both CPUs with one sign: %s. %s.' % (
            S3_NAMES[name], ', '.join('%s %s' % (k.replace('cpu', 'CPU '), dec(v['confirmed'])) for k, v in sorted(cf['per_cpu'].items(), key=lambda kv: int(kv[0][3:]))),
            dec(cf['confirmed_both']), medians(name, 'first'))
        if got and not test:
            fourth = s3['confirm'][name]['fourth']
            rows.append([result, ev, concl('%s Confirmed on %s. Persistence check in the fourth window, confirmed per CPU: %s.' % (
                allowed, ', '.join('CPU %d (sign %s)' % g for g in ((c, sign_word(sg_)) for c, sg_ in got)),
                ', '.join('%s %s' % (k.replace('cpu', 'CPU '), dec(v['confirmed'])) for k, v in sorted(fourth['per_cpu'].items(), key=lambda kv: int(kv[0][3:])))))])
        else:
            rows.append([result, ev, ID + ('Test data gives no decision. ' if test else 'The contrast is not confirmed on any CPU. ') +
                         'Next measurement: the Stage 3 batch with six complete processes per CPU in both sessions.'])
    # row 4
    if not s2:
        rows.append(['P1 establishes nearly constant old read and P2 establishes falling new and assembly rates', 'No process of step S2.', ID + 'Next measurement: the Stage 2 size sweep (step S2).'])
    else:
        ev = 'P1 over all cells: %s. P2 per CPU: %s. Candidate: %s.' % (
            dec(s2['P1']['overall']), '; '.join('%s %s' % (KN[k], ', '.join('%s %s' % (c.replace('cpu', 'CPU '), dec(v['outcome'])) for c, v in sorted(s2['P2'][k]['per_cpu'].items(), key=lambda kv: int(kv[0][3:])))) for k in (NEW, ASM)),
            dec(s2['candidate']))
        if s2['candidate'] == 'supported':
            rows.append(['P1 establishes nearly constant old read and P2 establishes falling new and assembly rates', ev,
                         concl('The size contrasts of each kernel support the bounded explanation of the shrinking advantage that the candidate gives: the new loop carries the loss of advantage. '
                               'The core resource that limits old read and the data-supply bottleneck are not identified.')])
        elif s2['candidate'] == 'contradicted':
            rows.append(['P1 establishes nearly constant old read and P2 establishes falling new and assembly rates', ev,
                         'The analysis returns "contradicted" for the candidate. The design says: stop using this candidate as the explanation. Next measurement: a new discriminating test, chosen and recorded before collection.'])
        else:
            worst = [(ck, s2['cells'][ck]['P1']['filtered']) for ck in cells_sorted(s2['cells']) if 'P1' in s2['cells'][ck]]
            rows.append(['P1 establishes nearly constant old read and P2 establishes falling new and assembly rates', ev,
                         ID + ('Test data gives no decision. ' if test else '') + 'Next measurement: Stage 2 with six complete matched sets per CPU and session at 1 MiB and 8 MiB. Largest |d| + L of P1 per cell: %s (needed: at most %.2f GB/s).' % (
                             '; '.join('%s %s GB/s' % (cell_name(ck), num(p['largest_abs_plus_limit'], 3)) for ck, p in worst) or DASH, A.P1_MARGIN)])
    # row 5
    if not s2 or 'size_contrast' not in s2['confirm']:
        rows.append(['Small gain remains under same-kernel preparation', 'No Stage 2 data at 1 MiB and 8 MiB.', ID + 'Next measurement: the Stage 2 size sweep (step S2).'])
    else:
        cf = s2['confirm']['size_contrast']
        got = [g for g in cpus_confirmed(cf) if g[1] == -1]
        gains = '; '.join('%s: %s %% (sets %s %%)' % (cell_name(ck), sg(c['sentence']['gain_pct']), rng(c['sentence']['gain_pct_min'], c['sentence']['gain_pct_max'], 2, True))
                          for ck, c in ((ck, s2['cells'][ck]) for ck in cells_sorted(s2['cells'])) if c.get('sentence'))
        ev = 'Gain at 8 MiB under same-kernel preparation: %s. Contrast (new − old at 8 MiB) − (new − old at 1 MiB), confirmed per CPU: %s.' % (
            gains or DASH, ', '.join('%s %s%s' % (k.replace('cpu', 'CPU '), dec(v['confirmed']), ' (%s)' % sign_word(v['sign']) if v['sign'] else '')
                                     for k, v in sorted(cf['per_cpu'].items(), key=lambda kv: int(kv[0][3:]))))
        if got and not test:
            rows.append(['Small gain remains under same-kernel preparation', ev, concl(
                'The original size behaviour persists under the specified preparation on %s: the advantage of new read is smaller at 8 MiB than at 1 MiB. A mixed-sequence predecessor effect is not needed to produce it.'
                % ', '.join('CPU %d' % c for c, _ in got))])
        else:
            rows.append(['Small gain remains under same-kernel preparation', ev, ID + ('Test data gives no decision. ' if test else 'The size contrast is not confirmed negative on any CPU. ') +
                         'Next measurement: Stage 2 with six complete matched sets per CPU in both sessions.'])
    # row 6
    cg = {k: v for k, v in (s.get('gates') or {}).items() if k in ('CS', 'CM')}
    ev = ('Mode gates: %s.' % '; '.join('%s: %s' % (k, dec(v.get('statement'))) for k, v in sorted(cg.items()))) if cg else 'No counter step with a mode gate.'
    rows.append(['Counter difference with validated measurement mode', ev, ID + 'The analysis returns no decision on a counter difference, and the event definitions are not validated. '
                 'Next measurement: authoritative event definitions, then a counter batch whose mode gate passed.'])
    # row 7
    rows.append(['A controlled mechanism change predicts and reproduces the gain change on both CPUs and sessions', 'No Stage 5 run exists. The implementation has no Stage 5 step.',
                 ID + 'Next measurement: one Stage 5 branch, chosen from the confirmed results and recorded before collection.'])
    o = ['<h2>12. What explains what</h2>',
         '<p>The table follows the design section "What counts as progress, and what counts as an answer"%s. A conclusion is printed only where the analysis returned the evidence of its row. '
         'This page adds no causal sentence of its own.</p>' % ref(1),
         table(['result named by the design', 'evidence in these runs', 'allowed conclusion, or what is missing'], rows, left=(0, 1, 2), wrap=True),
         '<p class="rule">The 8 MiB question is not solved because one hypothesis is not rejected. A complete answer needs the old and new rates under controlled conditions, the part of the gap explained by an intervention, and the remaining uncertainty%s.</p>' % ref(1)]
    return o


def references(D):
    R = [(1, os.path.join(os.path.dirname(HERE), 'tackle-8mb.md'), 'the design. Lines 201 to 222 (Stage 2), 224 to 228 (P3), 230 to 255 (Stage 3), 257 to 279 (rules and quality marks), 281 to 309 (Stage 4 and counters), 326 to 338 (allowed conclusions), 375 to 383 (this report).'),
         (2, os.path.normpath(os.path.join(HERE, '..', '..', 'tmp', 'agent-scratch', 'bwx8-2026-11-14', 'DECISIONS-bwx8.md')), 'the fixed readings of the rules and the file formats.'),
         (3, os.path.join(HERE, 'analyze8.py'), 'the analysis program. Functions load() and summary() computed the numbers and decision words of this page.'),
         (4, '; '.join(os.path.abspath(p) for p in D['paths']), 'the result folders of this page (%d).' % len(D['paths'])),
         (5, os.path.abspath(D['margins']) if D['margins'] else 'no margins file was given', 'the frozen margins of the gates, written by "analyze8.py forecast".'),
         (6, os.path.join(HERE, 'report8.py'), 'the script that drew this page.'),
         (7, os.path.join(HERE, 'stage0.html'), 'Stage 0: the saved evidence from before these runs.'),
         (8, os.path.normpath(os.path.join(HERE, '..', '..', 'tmp', 'agent-scratch', 'bwx8-2026-11-14', 'run_bwx8.sh')), 'the run script. Function one() writes the launch line with the load. The script copies the schedule into each result folder.')]
    o = ['<h2>References</h2><ul class="sm">']
    for n, path, what in R:
        o.append('<li>[Ref%d] <code>%s</code>: %s</li>' % (n, e(path), e(what)))
    o.append('</ul>')
    return o


def short_version(D):
    s = D['s']
    nproc = sum(c['processes'] for c in s['counts'].values())
    ntr = sum(c['trials'] for c in s['counts'].values())
    rej = sum(c['rejected'] for c in s['counts'].values())
    dist = sum(c['disturbed'] for c in s['counts'].values())
    notend = sum(c['processes_not_ended'] for c in s['counts'].values())
    counts = 'The folders hold %d processes and %d trials of the steps %s: %d trials are rejected, %d carry a disturbed mark, and %d processes did not end.' % (
        nproc, ntr, ', '.join(s['steps']), rej, dist, notend)
    if s['test_data']:
        return 'This page is built from test data: the kernels are stand-ins or the durations were shortened, so the rates mean nothing and no decision is given. ' + counts
    s2 = s.get('stage2')
    sen = [c['sentence'] for c in (s2['cells'][ck] for ck in cells_sorted(s2['cells'])) if c.get('sentence') and c['sentence']['gain_pct'] is not None] if s2 else []
    if not sen:
        return 'The folders hold no complete Stage 2 comparison at 8 MiB, so this page gives no old-to-new gain. ' + counts
    g, old, new = [x['gain_pct'] for x in sen], [x['old_GBps'] for x in sen], [x['new_GBps'] for x in sen]
    a = ('At 8 MiB, with each kernel as its own preparation, new read was %s %% to %s %% faster than old read (medians of the matched sets on %d CPU and session cells; old read %s to %s GB/s, new read %s to %s GB/s).'
         % (sg(min(g)), sg(max(g)), len(sen), num(min(old)), num(max(old)), num(min(new)), num(max(new))))
    b = ' The analysis returns %s for prediction P1 (old read nearly constant from 1 MiB to 8 MiB) and %s for the candidate explanation of the size comparison. ' % (
        dec(s2['P1']['overall']), dec(s2['candidate']))
    return a + b + counts


def build(D):
    s = D['s']
    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
         '<title>bwx8 run report</title><style>%s</style></head><body>' % CSS8,
         '<h1>New runs: the read gain at 8 MiB by size, history and time</h1>']
    if D['note']:
        o.append('<div class="banner">%s</div>' % e(D['note']))
    if s['test_data']:
        o.append('<div class="banner">%s</div>' % e(TEST_BANNER))
    o.append('<p><b>Short version.</b> %s</p>' % short_version(D))
    o.append('<h2>Words used here</h2><ul class="words">' + ''.join('<li><b>%s</b>: %s</li>' % kv for kv in WORDS) + '</ul>')
    for sec in (sec_inputs, sec_load, sec_stage2, sec_stage4, sec_p3, sec_stage3, sec_gates, sec_b6w, sec_counters, sec_exclusions, sec_stopped, sec_explains, references):
        o += sec(D)
    o.append('</body></html>')
    return '\n'.join(o)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('folders', nargs='+')
    ap.add_argument('--margins')
    ap.add_argument('--note', help='one more banner line at the top of the page')
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args(argv)
    procs = A.load(a.folders)
    margins = None
    if a.margins:
        with open(a.margins) as fh:
            margins = json.load(fh)
    try:
        s = A.summary(procs, margins)
    except A.GateError as err:
        print('refused: %s' % err, file=sys.stderr)
        return 2
    page = build(dict(s=s, procs=procs, paths=a.folders, margins=a.margins, note=a.note))
    with open(a.out, 'w') as fh:
        fh.write(page)
    print('wrote %s (%d bytes)%s' % (a.out, len(page), '; ' + s['banner'] if s['test_data'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
