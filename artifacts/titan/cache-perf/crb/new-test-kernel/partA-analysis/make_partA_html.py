#!/usr/bin/env python3
"""make_partA_html.py [partA-summary.json] [-o partA-result.html] [--banner TEXT]

Builds one self-contained HTML result page of Part A (screening) from the json that analyze_partA.py writes.
No external script, font or image. Light background only.

Every sentence that interprets data is built from the values in the json. Typed text is limited to:
the list "Words used here", the two questions under the Short version, the columns quoted from plan.md,
the section "Limits of this page", the captions that say how a chart is drawn, the sentences that say
what the plan, the handoff, the run script or the analysis script ask for or do (with their reference),
and the references. A typed sentence that depends on the data is printed only under the computed condition.
Numbers are printed with fx(): a median that lies in the middle of two printed values keeps its third decimal.
Part A is screening: the page says "observed in screening". The sentences built from data use none of the
decision words of rule 11 of the plan. The column copied from the plan quotes some of them in negated form
("not observed", "does not reject H2", "rejects nothing", "not resolved at this grid").
"""
import sys, json, html, statistics as st
from decimal import Decimal, ROUND_HALF_UP

C0, C1, C2 = '#2a78d6', '#eb6834', '#1baf7a'      # mesh 0 / first series, mesh 1 / second series, third
INK, MUTED, GRID, BAND = '#0b0b0b', '#52514e', '#e6e5e0', '#f1f0ec'
ID = 'Insufficient data'
KNAME = dict(read_old='old read', read_new='new read', asmread='asm read', write_old='old write', write_new='new write', asmwrite='asm write')
KORDER = ['read_old', 'read_new', 'asmread', 'write_old', 'write_new', 'asmwrite']
PLAN = dict(
    A1='Which CPUs are the fast threads of old read and of the faster write repetitions.',
    A2='If the totals change with the long interval, H7a gets priority in B7. If they stay, the short interval alone is not sufficient to explain Q2a. H7b is untouched: the common start stays.',
    A3='Whether the second buffer changes the pattern in this session. H9b is untouched.',
    A4='For each kernel, the two neighbouring thread counts between which the pattern changes. Equal brackets for both kernels are "not resolved at this grid", and the grid is then refined in B8.',
    A5='Whether a change of level is observed in 30 intervals, in which direction, and after how many intervals. No change in 30 intervals is "not observed". It does not reject H2. A different level in the second process says nothing about H2, because the buffer is a new allocation.',
    A6='The rate of a buffer on 4 KiB pages, as a reference value for B4. Alone it rejects nothing: it does not show which coverage the low and the high intervals had.',
    A7='- (the plan gives no entry: the step collects the vector length and the event names for parts C and D)')
LOOKS = dict(A1='H8, H11, item 13', A2='H7a only', A3='H9a only', A4='H8', A5='H2', A6='H3a', A7='-')

e = html.escape


def pl(n, one, many):
    return f'{n} {one if n == 1 else many}'


def fx(v, nd=2):
    """Number with nd decimals. A value with 2 decimals that lies exactly in the middle of two printed values (a median of an
    even count of rates, or a difference of such medians) is printed with 3 decimals (0.995), so that printed values agree
    with each other. Other half values are rounded upward."""
    d6 = Decimal(f'{v:.6f}')
    if nd == 2 and d6 == d6.quantize(Decimal('0.001')) and d6 != d6.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) and abs(d6 * 1000) % 10 == 5:
        nd = 3
    d = d6.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    if d == 0:
        d = abs(d)
    return f'{d:.{nd}f}'


def fs(v, nd=2):
    """As fx, with a sign."""
    t = fx(v, nd)
    return t if t.startswith('-') else '+' + t


def f2(v, nd=2):
    return '-' if v is None else fx(v, nd)


def rtxt(r, nd=2, unit=''):
    """Text of a range dict {n,min,median,max}."""
    if not r or not r.get('n'):
        return '-'
    u = f' {unit}' if unit else ''
    a, b = fx(r['min'], nd), fx(r['max'], nd)
    return f"{a}{u}" if a == b else f"{a} to {b}{u}"


def missing(what):
    return f'<p class="miss"><b>{ID}.</b> {what}</p>'


def svg_open(W, H, aria):
    return [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{e(aria)}" style="max-width:{W}px">']


def marker(x, y, shape, color, title, r=5):
    t = f'<title>{e(title)}</title>'
    if shape == 'diamond':
        return f'<path d="M{fx(x, 1)},{fx(y-r-1, 1)} l{r+1},{r+1} l-{r+1},{r+1} l-{r+1},-{r+1} Z" fill="{color}" stroke="#fff" stroke-width="1.5">{t}</path>'
    return f'<circle cx="{fx(x, 1)}" cy="{fx(y, 1)}" r="{r}" fill="{color}" stroke="#fff" stroke-width="1.5">{t}</circle>'


def strip_chart(rows, xmin, xmax, ticks, xlabel, aria, vlines=(), band=None, nd=2, unit=''):
    """rows: [(name, [(value, title)], right_label)]. One row of dots per name."""
    W, L, R, rh, top = 840, 230, 230, 28, 30
    H = top + len(rows) * rh + 48; PW = W - L - R
    x = lambda v: L + (min(max(v, xmin), xmax) - xmin) / (xmax - xmin) * PW
    o = svg_open(W, H, aria)
    if band:
        o.append(f'<rect x="{fx(x(band[0]), 1)}" y="{top-6}" width="{fx(x(band[1])-x(band[0]), 1)}" height="{len(rows)*rh+6}" fill="{BAND}"/>')
        o.append(f'<text x="{fx((x(band[0])+x(band[1]))/2, 1)}" y="{top-12}" text-anchor="middle" class="ax">{e(band[2])}</text>')
    for t in ticks:
        o.append(f'<line x1="{fx(x(t), 1)}" y1="{top-6}" x2="{fx(x(t), 1)}" y2="{H-48}" stroke="{GRID}"/>')
        o.append(f'<text x="{fx(x(t), 1)}" y="{H-32}" text-anchor="middle" class="ax">{t:g}</text>')
    for v, lab in vlines:
        o.append(f'<line x1="{fx(x(v), 1)}" y1="{top-6}" x2="{fx(x(v), 1)}" y2="{H-48}" stroke="{MUTED}" stroke-dasharray="4 3"/>')
        if lab:
            o.append(f'<text x="{fx(x(v), 1)}" y="{top-12}" text-anchor="middle" class="ax">{e(lab)}</text>')
    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">{e(xlabel)}</text>')
    for i, (name, pts, right) in enumerate(rows):
        y = top + i * rh + rh / 2
        o.append(f'<text x="{L-10}" y="{fx(y+4, 1)}" text-anchor="end" class="lab">{e(name)}</text>')
        o.append(f'<line x1="{L}" y1="{fx(y+rh/2, 1)}" x2="{L+PW}" y2="{fx(y+rh/2, 1)}" stroke="{GRID}"/>')
        for j, (v, title) in enumerate(pts):
            o.append(f'<circle cx="{fx(x(v), 1)}" cy="{fx(y + ((j*7)%5-2)*2.5, 1)}" r="4" fill="{C0}" fill-opacity="0.65" stroke="#fff" stroke-width="1"><title>{e(title)}</title></circle>')
        o.append(f'<text x="{L+PW+10}" y="{fx(y+4, 1)}" class="val">{e(right)}</text>')
    o.append('</svg>')
    return '\n'.join(o)


# ---------------------------------------------------------------- sections

def sec_load(s):
    o = ['<h2 id="load">System load of the run</h2>']
    envs = [x for x in s['env'] if x['present']]
    if not envs and not s['load']:
        return '\n'.join(o) + missing('The system load: no <code>env.txt</code> and no header line of a launch was found in the result folders.')
    lc = s.get('load_check') or {}
    high = bool(lc.get('n_launches')) and lc['load1_max'] is not None and lc['load1_max'] > 2
    if lc.get('n_launches'):
        own = lc['own_user']
        o.append('<p class="take">' + ('No reading of this run shows load from another user.' if lc['no_other_load_seen'] else
                                       'The readings of this run do not exclude load from another user. They are listed below.') + '</p>')
        o.append('<p>The script took these readings directly before each launch [Ref3]:</p><ul>')
        t = '<li>Runnable tasks in the header line of each launch: '
        if lc['n_many_threads']:
            t += f"at most {lc['runnable_header_max_many']} at the {pl(lc['n_many_threads'], 'launch', 'launches')} with many threads"
        if lc['n_one_thread']:
            t += (', and ' if lc['n_many_threads'] else '') + f"at most {lc['runnable_header_max_one']} at the {pl(lc['n_one_thread'], 'launch', 'launches')} with one thread"
        o.append(t + '. One of these tasks is the script that reads the value.</li>')
        if lc['n_with_launches_txt']:
            o.append(f"<li>The file <code>launches.txt</code> holds a second reading of the runnable tasks, taken a moment before the header line. Its highest value was {lc['runnable_launches_txt_max']}. "
                     f"It differs from the header line at {lc['n_runnable_differ']} of {pl(lc['n_with_launches_txt'], 'launch', 'launches')}.</li>")
        o.append('<li>0 users were logged in at every launch.</li>' if lc['logins_max'] == 0 else f"<li>Logged-in users: at most {lc['logins_max']} at a launch.</li>")
        o.append(f"<li>Waits: {lc['n_waited']} of {pl(lc['n_launches'], 'launch', 'launches')} had to wait for a quiet system.</li>")
        if own and lc['busiest_own']:
            names = [b['comm'] for b in lc['busiest_own']]
            t = (f"<li>Busiest processes in <code>launches.txt</code>: the highest values belong to the account <code>{e(own)}</code>, which ran the script: "
                 + ', '.join(f"{e(b['comm'])} {fx(b['pcpu'], 1)} %" for b in lc['busiest_own']) + ' of one CPU at most. ')
            if 'ps' in names:
                t += 'The script starts <code>ps</code> to write this list, so <code>ps</code> is the script itself [Ref3]. '
            if 'bash' in names:
                t += 'The script is a <code>bash</code> script [Ref3]. '
            if lc['busiest_other']:
                b = lc['busiest_other'][0]
                t += f"The busiest process of another account was {e(b['comm'])} of {e(b['user'])} with {fx(b['pcpu'], 1)} % of one CPU."
            o.append(t + '</li>')
        elif lc['busiest_other']:
            o.append('<li>Busiest processes in <code>launches.txt</code>: ' + ', '.join(f"{e(b['comm'])} of {e(b['user'])} {fx(b['pcpu'], 1)} %" for b in lc['busiest_other'])
                     + ' of one CPU at most. The account of the script could not be read from the list.</li>')
        o.append('</ul>')
        if high:
            o.append(f"<p>The 1-minute load went up to {fx(lc['load1_max'])} tasks. This value is an average over about the last minute. "
                     f"Hypothesis: the high values are left from the threads of our own benchmark process that ended directly before the launch (up to {lc['threads_max']} threads). "
                     + ('The readings above agree with the hypothesis. ' if lc['no_other_load_seen'] else '')
                     + f"It is not measured. {ID}: no reading was taken while a benchmark ran. A reading of the runnable tasks of each account during an interval would decide it.</p>")
    o.append('<ul>')
    for x in s['env']:
        if not x['present']:
            o.append(f"<li>Folder <code>{e(x['folder'])}</code>: {ID}. The file <code>env.txt</code> is missing, so the load at the start of this script is not known.</li>"); continue
        la = (x.get('start_loadavg') or '').split()
        end = (x.get('end_loadavg') or '').split()
        t = f"<li>Folder <code>{e(x['folder'])}</code> (steps {e(x.get('steps') or '-')}), started at {e(x.get('start_utc') or '-')}. "
        t += (f"The 1-minute load at the start of the script was {e(la[0])} tasks, with {e(x.get('start_logins') or '-')} logged-in users. " if la else '')
        t += (f"The 1-minute load at the end was {e(end[0])} tasks. " if end else 'The script wrote no end line, so it did not reach its end. ')
        if end and high and float(end[0]) > 2:
            t += 'The hypothesis above covers this value too. '
        t += ''.join(f'The script wrote: "{e(k)}". ' for k in x.get('skipped', []))
        o.append(t + '</li>')
    o.append('</ul>')
    if s['load']:
        o.append('<p>The table gives the readings per step. The load, the runnable tasks, the waits and the logged-in users are from the header lines of the csv files. '
                 'The second reading of the runnable tasks and the busiest processes are from <code>launches.txt</code> [Ref3].</p>')
        o.append('<div class="tw"><table><tr><th>Step</th><th>Launches used</th><th>UTC first to last</th><th>1-minute load (tasks), lowest to highest</th>'
                 '<th>Runnable tasks in the header line, highest</th><th>Runnable tasks in launches.txt, highest</th><th>Launches that waited</th><th>Longest wait (s)</th><th>Launches that waited the full 20 s</th><th>Logged-in users, highest</th><th>Busiest processes seen (highest % of one CPU)</th></tr>')
        for st_, L in s['load'].items():
            busy = ', '.join(f"{e(b['comm'])} of {e(b['user'])} {fx(b['max_pcpu'], 1)} %" for b in L['busiest'][:3]) or f'{ID}: launches.txt has no entry'
            r2 = L.get('runnable_launches_txt') or {}
            o.append(f"<tr><td>{st_}</td><td>{L['launches']}</td><td>{e(L['first_utc'])} to {e(L['last_utc'])}</td><td>{rtxt(L['load1'])}</td><td>{L['runnable']['max']}</td>"
                     f"<td>{r2['max'] if r2.get('n') else '-'}</td>"
                     f"<td>{L['n_waited']}</td><td>{L['waited_s']['max']:g}</td><td>{L['n_waited_20s']}</td><td>{L['logins']['max']}</td><td>{busy}</td></tr>")
        o.append('</table></div>')
        o.append('<details><summary>Load of every launch</summary><div class="tw"><table><tr><th>Folder</th><th>Step</th><th>Tag</th><th>UTC</th><th>Waited (s)</th><th>1-minute load</th><th>5-minute load</th><th>Runnable tasks, header line</th><th>Runnable tasks, launches.txt</th><th>Logged-in users</th></tr>')
        for l in s['launches']:
            r2 = l.get('runnable_launches_txt')
            o.append(f"<tr><td>{e(l['folder'])}</td><td>{l['step']}</td><td>{e(l['tag'])}</td><td>{l['utc']}</td><td>{l['waited_s']:g}</td><td>{fx(l['load1'], 2)}</td><td>{fx(l['load5'], 2)}</td><td>{l['runnable']}</td><td>{'-' if r2 is None else r2}</td><td>{l['logins']}</td></tr>")
        o.append('</table></div></details>')
    return '\n'.join(o)


def sec_blocks(s):
    c = s['counts']
    o = ['<h2 id="blocks">Processes that were stopped, failed or repeated</h2>']
    o.append(f"<p>The result folders hold {c['blocks_found']} process blocks. {c['blocks_used']} are used on this page. "
             f"{pl(c['killed'], 'was', 'were')} stopped by the script, {c['failed']} failed, and {pl(c['repeated_tags'], 'launch exists', 'launches exist')} more than once.</p>")
    if s['not_used']:
        o.append('<p>If a launch exists more than once, the page uses its last complete block [Ref5].</p>')
        o.append('<div class="tw"><table><tr><th>Folder</th><th>Step</th><th>Tag</th><th>UTC</th><th>Why it is not used</th><th>A complete block of the same launch is used</th></tr>')
        for x in s['not_used']:
            o.append(f"<tr><td>{e(x['folder'])}</td><td>{x['step']}</td><td>{e(x['tag'])}</td><td>{x['utc']}</td><td>{e(x['reason'])}</td><td>{'yes' if x['replaced'] else 'no: this launch has no data'}</td></tr>")
        o.append('</table></div>')
    for st_ in s['steps_missing']:
        why = '; '.join(k for x in s['env'] for k in x.get('skipped', []) if k.startswith(st_))
        o.append(missing(f"Step {st_} has no usable data in these folders." + (f' The script wrote: "{e(why)}".' if why else '') + f" The measurement that is missing: the launches of step {st_} of <code>run_partA.sh</code>."))
    return '\n'.join(o)


def sec_passes(s):
    lim = s['limits']['min_passes']
    o = ['<h2 id="passes">Passes per thread (the 2 % check)</h2>',
         f'<p>Rule 7 of the plan asks that one pass takes at most 2 % of the interval. That means at least {lim} passes per thread [Ref1]. '
         'A thread stops only after a whole pass. So with fewer passes, the last pass alone can change the rate of a repetition by more than 2 %.</p>'
         '<p>Passes per thread = total bytes / (threads x bytes per thread), and half of that for a copy kernel. This is an average over the threads [Ref2]. '
         'The handoff expected about 52 to 86 passes in 6 s for read kernels and about 55 to 67 in 15 s for write kernels (est.) [Ref2].</p>']
    rows = []
    for st_ in ('A1', 'A2'):
        for k in KORDER:
            if k in s[st_]:
                x = s[st_][k]; rows.append((st_, KNAME[k], x['min_ms'], x['passes_per_thread'], x['n_below_50_passes'], len(x['reps'])))
    for g, x in s['A3']['groups'].items():
        pp = [r['passes_per_thread'] for p in x['processes'] for r in p['reps']]
        rows.append(('A3', f"old read, {x['buffers']} buffer{'s' if x['buffers'] > 1 else ''}", x['min_ms'], dict(n=len(pp), min=min(pp), max=max(pp)) if pp else None, x['n_below_50_passes'], len(pp)))
    for k, x in s['A4']['kernels'].items():
        pp = [r['passes_per_thread'] for c in x['counts'].values() for r in c['reps']]
        rows.append(('A4', KNAME.get(k, k), 6000, dict(n=len(pp), min=min(pp), max=max(pp)) if pp else None, sum(c['n_below_50_passes'] for c in x['counts'].values()), len(pp)))
    if not rows:
        return '\n'.join(o) + missing('No repetition with more than one thread is in the result folders, so no pass count can be given.')
    o.append('<div class="tw"><table><tr><th>Step</th><th>Kernel</th><th>Shortest interval (ms)</th><th>Passes per thread, lowest to highest</th>'
             f'<th>Repetitions below {lim} passes</th><th>Repetitions</th></tr>')
    for st_, k, ms, r, nb, n in rows:
        o.append(f"<tr><td>{st_}</td><td>{e(k)}</td><td>{f2(ms, 0)}</td><td>{rtxt(r, 1)}</td><td>{nb}</td><td>{n}</td></tr>")
    o.append('</table></div>')
    low = s['passes']['below_50']; n = s['passes']['n_below_50']; ntab = sum(r[4] for r in rows)
    t = f"<p>{pl(n, 'repetition', 'repetitions')} with more than one thread {'has' if n == 1 else 'have'} fewer than {lim} passes per thread. The table has {ntab} of them. "
    left = [x for x in low if x['step'] == 'A3' and x['kernel'] != 'read']
    if n - ntab > 0:
        t += (f"The other {n - ntab} are the write and copy repetitions of the A3 processes with two buffers. This page does not compare these rows. " if len(left) == n - ntab
              else f"The other {n - ntab} are not in the table. ")
    o.append(t + '</p>')
    if low:
        li = []
        for ms in sorted(set(x['min_ms'] or 0 for x in low)):
            xs = [x for x in low if (x['min_ms'] or 0) == ms]
            steps = sorted(set(x['step'] for x in xs))
            li.append(f"<li>Interval {ms/1000:g} s: {len(xs)}. " + ' '.join(f"Step {a}: {sum(1 for x in xs if x['step'] == a)}." for a in steps)
                      + f" Their passes per thread are {fx(min(x['passes_per_thread'] for x in xs), 1)} to {fx(max(x['passes_per_thread'] for x in xs), 1)}.</li>")
        o.append('<p>By interval:</p><ul>' + ''.join(li) + '</ul>')
        a1n = sum(len(s['A1'][k]['reps']) for k in s['A1']); a1low = sum(1 for x in low if x['step'] == 'A1')
        if a1n and a1low:
            pmin = min(x['passes_per_thread'] for x in low if x['step'] == 'A1')
            o.append(f"<p>What this means for A1: {a1low} of its {a1n} repetitions fail the check. At the lowest count ({fx(pmin, 1)} passes per thread), one whole pass is {fx(100 / pmin, 0)} % of the bytes of a thread in the interval. "
                     'So no total of A1 meets rule 7. A1 uses the default 0.5 s interval of the earlier run [Ref1]. A2 repeats the kernels with the long interval.</p>')
        longlow = [x for x in low if (x['min_ms'] or 0) >= 6000]
        if longlow:
            o.append(f'<details><summary>The {len(longlow)} repetitions below {lim} passes with an interval of 6 s or longer</summary><ul>'
                     + ''.join(f"<li>Step {x['step']}, launch <code>{e(x['tag'])}</code>, kernel {e(x['kernel'])}, repetition {x['rep']}: {fx(x['passes_per_thread'], 1)} passes per thread.</li>" for x in longlow) + '</ul></details>')
    return '\n'.join(o)


def qrow_name(r):
    k = r['tag'].rsplit('-r', 1)[0]
    if r['step'] in ('A1', 'A2'):
        return f"{r['step']} {KNAME.get(k, k)}"
    if r['step'] == 'A3':
        b = 'one buffer' if r['tag'].startswith('onebuf') else 'two buffers'
        ms = r['tag'].split('-')[1][2:]
        return f"A3 old read, {b}, {int(ms)/1000:g} s" if r['kernel'] == 'read' else 'A3 write and copy rows'
    if r['step'] == 'A4':
        k = r['tag'].rsplit('-', 1)[0]
        return f"A4 {KNAME.get(k, k)}, all counts"
    return r['step']


def sec_q(s):
    d = s['q']['decision']; lim = s['limits']
    o = ['<h2 id="q">Distribution of q over all repetitions with many threads</h2>',
         f"<p>q is the rate of the thread at the 10th percentile divided by the rate of the thread at the 90th percentile, in one repetition. "
         f"The provisional rule of the handoff calls a repetition split if q is below {lim['q_split_below']}, uniform if q is above {lim['q_uniform_above']}, and between otherwise [Ref2]. "
         "The handoff asks to look at the distribution first. If q does not fall into two groups, the labels are not used [Ref2].</p>"]
    if not s['q']['rows']:
        return '\n'.join(o) + missing('No repetition with per-thread lines is in the result folders, so q cannot be computed. The measurement that is missing: steps A1 to A4 with <code>--per-thread</code>.')
    groups = {}
    for r in s['q']['rows']:
        groups.setdefault(qrow_name(r), []).append((r['q'], f"{r['step']} {r['tag']} {r['kernel']} repetition {r['rep']}: q {fx(r['q'], 3)}"))
    rows = [(n, p, f"{len(p)} repetitions: {fx(min(v for v, _ in p), 2)}" + (f" to {fx(max(v for v, _ in p), 2)}" if max(v for v, _ in p) - min(v for v, _ in p) >= 0.005 else '')) for n, p in groups.items()]
    o.append(strip_chart(rows, 0, 1, [0, 0.25, 0.5, 0.65, 0.85, 1], 'q (no unit: a ratio of two rates)', 'q of every repetition, one row per step and kernel',
                         band=(lim['q_split_below'], lim['q_uniform_above'], 'between'), nd=2))
    o.append('<p class="cap">One dot is one repetition. Dots are moved a little up or down so that equal values stay visible. The grey band is the range that the rule calls "between". Each row is labelled with its lowest and highest q.</p>')
    gmin = lim.get('q_gap_min', 0.10)
    if d['labels_usable']:
        o.append(f"<p class=\"take\">Observed in screening: the {d['n']} values of q fall into two groups. {d['n_lower']} values lie from {fx(d['lower_min'], 2)} to {fx(d['lower_max'], 2)}, and {d['n_upper']} values lie from {fx(d['upper_min'], 2)} to {fx(d['upper_max'], 2)}. "
                 f"No value lies between {fx(d['gap_from'], 2)} and {fx(d['gap_to'], 2)}. The lower group is below {lim['q_split_below']} and the upper group is above {lim['q_uniform_above']}. So this page uses the labels split and uniform.</p>")
    else:
        t = f"Observed in screening: the {d['n']} values of q do not fall into two groups by the test below. "
        if 'gap' in d:
            t += f"The values lie from {fx(d['q_min'], 2)} to {fx(d['q_max'], 2)}. The rule alone would give {d['n_split']} split, {d['n_between']} between and {d['n_uniform']} uniform. "
            t += f"The largest distance between two neighbouring q values is {fx(d['gap'], 3)} (from {fx(d['gap_from'], 3)} to {fx(d['gap_to'], 3)}). "
            if d['gap'] < gmin:
                t += f"The test asks for at least {fx(gmin, 2)}. "
            if min(d['n_lower'], d['n_upper']) < 2:
                t += 'One side of the largest distance has fewer than 2 values. '
            wl, wu = d['lower_max'] - d['lower_min'], d['upper_max'] - d['upper_min']
            if d['gap'] <= wu:
                t += f"The values above the distance span {fx(d['upper_min'], 2)} to {fx(d['upper_max'], 2)}, which is wider than the distance. "
            if d['gap'] <= wl:
                t += f"The values below the distance span {fx(d['lower_min'], 2)} to {fx(d['lower_max'], 2)}, which is wider than the distance. "
            if d['two_groups'] and not d['limits_fit']:
                t += f"The two groups do not lie on the two sides of the limits {lim['q_split_below']} and {lim['q_uniform_above']}. "
        else:
            t += f"Reason: {e(d['reason'])}. "
        t += "So this page does not use the labels split and uniform. It gives q itself."
        o.append(f'<p class="take">{t}</p>')
    g = s['q'].get('groups')
    if g and not d['labels_usable']:
        li = []
        if g['below_split']:
            li.append(f"<li>The {sum(x['n'] for x in g['below_split'])} values below {lim['q_split_below']} are: "
                      + ', '.join(f"{x['n']} of {KNAME.get(x['kname'], x['kname'])} at {x['count']} threads" for x in g['below_split']) + '.</li>')
        a, b = g['read_old'], g['load_only_read']
        if a['n'] and b['n']:
            t = (f"<li>For the read kernels at {g['count']} threads alone: q is {rtxt(a['q'], 3)} for old read ({pl(a['n'], 'repetition', 'repetitions')} of all steps). "
                 f"It is {rtxt(b['q'], 3)} for new read and asm read ({pl(b['n'], 'repetition', 'repetitions')}). ")
            if g['ranges_separate']:
                lo_, hi_ = sorted([a['q'], b['q']], key=lambda z: z['min'])
                t += f"The two ranges do not overlap: no q of these kernels at this count lies between {fx(lo_['max'], 3)} and {fx(hi_['min'], 3)}."
            else:
                t += 'The two ranges overlap.'
            li.append(t + '</li>')
        if g['between']:
            li.append(f"<li>The {sum(x['n'] for x in g['between'])} values from {lim['q_split_below']} to {lim['q_uniform_above']} come from: "
                      + ', '.join(f"{KNAME.get(x['kname'], x['kname'])} in {x['step']} ({x['n']})" for x in g['between']) + '.</li>')
        li.append('<li>The handoff asks for the test over all repetitions of Part A [Ref2]. So the labels stay unused for every step and kernel on this page.</li>')
        o.append('<p>Where the values lie, observed in screening:</p><ul>' + ''.join(li) + '</ul>')
    o.append('<p>The handoff gives no test for "two groups". The analysis script uses this one (choice C2) [Ref5]:</p><ul>'
             '<li>The q values are sorted. The largest distance between two neighbours divides them into a lower and an upper group.</li>'
             f'<li>The values count as two groups if three conditions hold. Each group has at least 2 values. The distance is at least {fx(gmin, 2)}. The distance is larger than the width of each group.</li>'
             f"<li>The labels are used only if, in addition, the lower group is below {lim['q_split_below']} and the upper group is above {lim['q_uniform_above']}.</li></ul>")
    left = s['q'].get('rows_left_out') or []
    if left:
        o.append(f"<p>{len(left)} repetitions are not in this chart and not in the test. They are the write and copy repetitions of the A3 processes with two buffers. "
                 'The handoff says to compare only the read rows of A3 [Ref2]. They are listed in the file <code>partA-summary.json</code> under the key <code>q.rows_left_out</code> [Ref4].</p>')
    return '\n'.join(o)


def mesh_pairs_chart(s):
    rows = []
    for k in KORDER:
        for st_, lab in (('A1', '0.5 s'), ('A2', 'long')):
            if k in s[st_] and s[st_][k]['mesh0_median']['n']:
                x = s[st_][k]
                ms = x['min_ms']
                rows.append((f"{KNAME[k]}, {ms/1000:g} s ({st_})", x['mesh0_median']['median'], x['mesh1_median']['median'] if x['mesh1_median']['n'] else None, k))
    if not rows:
        return ''
    W, L, R, rh, top = 780, 190, 60, 34, 20
    H = top + len(rows) * rh + 48; PW = W - L - R
    xmax = max(max(a, b or 0) for _, a, b, _ in rows) * 1.12
    step = 1 if xmax > 4 else 0.5
    x = lambda v: L + v / xmax * PW
    o = svg_open(W, H, 'Median thread rate on mesh 0 and on mesh 1, one row per kernel and interval')
    t = 0
    while t <= xmax:
        o.append(f'<line x1="{fx(x(t), 1)}" y1="{top-6}" x2="{fx(x(t), 1)}" y2="{H-48}" stroke="{GRID}"/><text x="{fx(x(t), 1)}" y="{H-32}" text-anchor="middle" class="ax">{t:g}</text>')
        t += step
    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">median rate of one thread, GB/s (axis starts at 0)</text>')
    prev = None
    for i, (name, a, b, k) in enumerate(rows):
        y = top + i * rh + rh / 2
        if prev and prev != k:
            o.append(f'<line x1="10" y1="{fx(y-rh/2, 1)}" x2="{W-R}" y2="{fx(y-rh/2, 1)}" stroke="{GRID}"/>')
        prev = k
        o.append(f'<text x="{L-10}" y="{fx(y+4, 1)}" text-anchor="end" class="lab">{e(name)}</text>')
        if b is None:
            o.append(marker(x(a), y, 'circle', C0, f'{name}: mesh 0 {fx(a, 2)} GB/s'))
            o.append(f'<text x="{fx(x(a)+10, 1)}" y="{fx(y+4, 1)}" class="val">{fx(a, 2)}</text>'); continue
        if abs(x(a) - x(b)) < 14:          # the two dots would cover each other: draw them one above the other, with one label
            o.append(marker(x(a), y - 6, 'circle', C0, f'{name}: mesh 0, {fx(a, 2)} GB/s', r=4))
            o.append(marker(x(b), y + 6, 'diamond', C1, f'{name}: mesh 1, {fx(b, 2)} GB/s', r=4))
            o.append(f'<text x="{fx(max(x(a), x(b))+12, 1)}" y="{fx(y+4, 1)}" class="val">mesh 0 {fx(a, 2)}, mesh 1 {fx(b, 2)}</text>'); continue
        o.append(f'<line x1="{fx(x(a), 1)}" y1="{y}" x2="{fx(x(b), 1)}" y2="{y}" stroke="#8a8984" stroke-width="2"/>')
        o.append(marker(x(a), y, 'circle', C0, f'{name}: mesh 0, {fx(a, 2)} GB/s'))
        o.append(marker(x(b), y, 'diamond', C1, f'{name}: mesh 1, {fx(b, 2)} GB/s'))
        lo, hi = (a, b) if a <= b else (b, a)
        o.append(f'<text x="{fx(x(lo)-11, 1)}" y="{fx(y+4, 1)}" text-anchor="end" class="val">{fx(lo, 2)}</text>')
        o.append(f'<text x="{fx(x(hi)+11, 1)}" y="{fx(y+4, 1)}" class="val">{fx(hi, 2)}</text>')
    o.append('</svg>')
    leg = (f'<p><span class="lg"><i style="background:{C0}"></i>mesh 0 (CPUs 0 to 63), circle</span>'
           f'<span class="lg"><i style="background:{C1};border-radius:0;transform:rotate(45deg)"></i>mesh 1 (CPUs 64 to 119), diamond</span></p>')
    return leg + '\n'.join(o)


def cpu_panels(s, st_):
    """Small multiples: rate of each thread against its CPU, median over the repetitions of both rounds."""
    data = {}
    for r in s['thread_rates'].get(st_, []):
        k = r['tag'].rsplit('-r', 1)[0]
        for cpu, rate in r['threads']:
            data.setdefault(k, {}).setdefault(cpu, []).append(rate)
    ks = [k for k in KORDER if k in data]
    if not ks:
        return ''
    pw, ph, gx, gy, L, top = 215, 110, 40, 72, 60, 26
    cols = 3; rows = (len(ks) + cols - 1) // cols
    W = L + cols * pw + (cols - 1) * gx + 10; H = top + rows * (ph + gy)
    o = svg_open(W, H, f'Rate of each thread against its CPU number, step {st_}')
    for i, k in enumerate(ks):
        med = {c: st.median(v) for c, v in data[k].items()}
        row_ks = ks[(i // cols) * cols:(i // cols) * cols + cols]
        ymax = max(st.median(v) for kk in row_ks for v in data[kk].values()) * 1.15
        x0 = L + (i % cols) * (pw + gx); y0 = top + (i // cols) * (ph + gy)
        X = lambda c: x0 + c / 119 * pw
        Y = lambda v: y0 + ph - v / ymax * ph
        o.append(f'<rect x="{x0}" y="{y0}" width="{pw}" height="{ph}" fill="none" stroke="{GRID}"/>')
        o.append(f'<line x1="{fx(X(63.5), 1)}" y1="{y0}" x2="{fx(X(63.5), 1)}" y2="{y0+ph}" stroke="{MUTED}" stroke-dasharray="3 3"/>')
        o.append(f'<text x="{x0}" y="{y0-8}" class="lab">{e(KNAME[k])}</text>')
        for tv, tl in ((0, '0'), (ymax / 1.15, f'{fx(ymax/1.15, 2)}')):
            o.append(f'<text x="{x0-5}" y="{fx(Y(tv)+(4 if tv else 0), 1)}" text-anchor="end" class="ax">{tl}</text>')
        if i % cols == 0:
            o.append(f'<text x="10" y="{y0+ph/2}" text-anchor="middle" class="ax" transform="rotate(-90 10 {y0+ph/2})">thread rate, GB/s</text>')
        for c, lab in ((0, 'CPU 0'), (64, '64'), (119, '119')):
            o.append(f'<text x="{fx(X(c), 1)}" y="{y0+ph+13}" text-anchor="middle" class="ax">{lab}</text>')
        for c, v in sorted(med.items()):
            o.append(f'<circle cx="{fx(X(c), 1)}" cy="{fx(Y(v), 1)}" r="2" fill="{C0 if c < 64 else C1}"><title>CPU {c}: {fx(v, 2)} GB/s</title></circle>')
        x = s[st_].get(k, {})
        for j, m in enumerate(m for m in (0, 1) if x.get(f'mesh{m}_median', {}).get('n')):
            t = f"mesh {m}: {fx(x[f'mesh{m}_median']['median'], 2)} GB/s"
            o.append(f'<text x="{x0}" y="{y0+ph+28+14*j}" class="val">{e(t)}</text>')
    o.append('</svg>')
    return '\n'.join(o)


def fh_one(r):
    """Count of mesh-0 threads in the fastest half of one repetition. A range comes from equal rates at the limit (choice C3)."""
    f = r.get('fastest_half')
    if not f:
        return '-'
    lo, hi = f['mesh0']
    return f'{lo}' if lo == hi else f'{lo} to {hi}'


def fh_reps(reps):
    """The counts of all repetitions, in order, with the size of the half: '4, 4, 6 of 60'."""
    v = [r for r in reps if r.get('fastest_half')]
    if not v:
        return '-'
    return ', '.join(fh_one(r) for r in v) + f" of {v[0]['fastest_half']['n_half']}"


def fh_txt(reps):
    return fh_reps(reps)


def faster_mesh(reps):
    """Repetitions grouped by the mesh with the higher median thread rate. Returns {'0': [...], '1': [...], '=': [...]}."""
    out = {'0': [], '1': [], '=': []}
    for r in reps:
        a, b = r['mesh0']['median'], r['mesh1']['median']
        if a is None or b is None:
            continue
        out['0' if a > b else '1' if b > a else '='].append(r)
    return out


def mesh_change_txt(reps):
    """Sentences for a kernel or count whose faster mesh is not the same in all repetitions. Empty if it is the same."""
    g = faster_mesh(reps)
    if not g['0'] or not g['1']:
        return ''
    n = len(g['0']) + len(g['1']) + len(g['='])
    t = []
    for m in ('0', '1'):
        other = '1' if m == '0' else '0'
        part = f"The median thread rate was higher on mesh {m} in {len(g[m])} of {n} repetitions"
        if len(g[m]) <= 2:
            part += ' (' + '; '.join(f"launch {r['tag']}, repetition {r['rep']}: {fx(r['mesh' + m]['median'])} against {fx(r['mesh' + other]['median'])} GB/s, "
                                     f"fastest half on mesh 0: {fh_reps([r])}" for r in g[m]) + ')'
        t.append(part + '.')
    return ' '.join(t)


def write_hi_lo(s):
    """For each write kernel of A1 and A2: the repetition with the highest total against the one with the lowest."""
    out = []
    for st_ in ('A1', 'A2'):
        for k in ('write_old', 'write_new', 'asmwrite'):
            rr = s[st_].get(k, {}).get('reps', [])
            rr = [r for r in rr if r['mesh0']['sum'] is not None and r['mesh1']['sum'] is not None]
            if len(rr) < 2: continue
            hi = max(rr, key=lambda r: r['total_GBps']); lo = min(rr, key=lambda r: r['total_GBps'])
            out.append(dict(step=st_, k=k, n=len(rr), lo=lo['total_GBps'], hi=hi['total_GBps'], d0=hi['mesh0']['sum'] - lo['mesh0']['sum'], d1=hi['mesh1']['sum'] - lo['mesh1']['sum']))
    return out


def write_hi_lo_txt(w):
    n0 = sum(1 for x in w if x['d0'] > x['d1']); n1 = sum(1 for x in w if x['d1'] > x['d0'])
    both = sum(1 for x in w if x['d0'] > 0 and x['d1'] > 0)
    t = (f"In {both} of the {pl(len(w), 'case', 'cases')} (kernel and step) the sum of the thread rates was higher on both meshes in the repetition with the highest total. "
         f"The larger part of the change was on mesh 0 in {n0} and on mesh 1 in {n1}.")
    if n0 and n1:
        t += ' So no single mesh was observed as the source of the higher write totals.'
    return t


def sec_a12(s):
    o = ['<h2 id="a1">A1 and A2: six kernels with 64+56 threads, short and long interval</h2>']
    if not s['A1'] and not s['A2']:
        return '\n'.join(o) + missing('Steps A1 and A2 have no usable data. The measurement that is missing: the 12 launches of A1 and the 12 launches of A2 of <code>run_partA.sh</code>.')
    for st_ in ('A1', 'A2'):
        if not s[st_]:
            o.append(missing(f'Step {st_} has no usable data. The measurement that is missing: the 12 launches of step {st_}.'))
    o.append('<h3>Median thread rate of each mesh</h3>')
    o.append(mesh_pairs_chart(s))
    o.append('<p class="cap">Each dot is the median over the repetitions of the median thread rate of one mesh. A long line between the two dots means that the threads of the two meshes ran at different rates.</p>')
    # generated statement on which mesh is fast
    li = []; half = None; n1 = None
    for st_ in ('A1', 'A2'):
        for k in KORDER:
            if k not in s[st_]: continue
            x = s[st_][k]
            if not x['mesh1_median']['n']: continue
            a, b = x['mesh0_median']['median'], x['mesh1_median']['median']
            rel = ('The two rates were equal.' if fx(a) == fx(b) else
                   f"The rate on mesh {'0' if a > b else '1'} was higher by {fx(abs(a-b), 2)} GB/s, which is {fx(abs(a-b)/min(a,b)*100, 0)} %.")
            f = next((r['fastest_half'] for r in x['reps'] if r['fastest_half']), None)
            if f and half is None:
                half, n1 = f['n_half'], x['reps'][0]['mesh1']['n']
            li.append(f"<li>{st_}, {KNAME[k]}, {x['min_ms']/1000:g} s: the median thread rate was {fx(a, 2)} GB/s on mesh 0 and {fx(b, 2)} GB/s on mesh 1. {rel} "
                      f"Threads of the fastest half on mesh 0, per repetition: {fh_reps(x['reps'])}. q was {rtxt(x['q'])}. {mesh_change_txt(x['reps'])}</li>")
    o.append('<p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')
    if half is not None:
        o.append(f'<p>How to read the count of the fastest half. The fastest half is the {half} threads with the highest rates of one repetition. Mesh 1 has {n1} threads. '
                 + (f'So {half - n1} of {half} is the lowest possible count on mesh 0: all {n1} threads of mesh 1 are then in the fastest half. ' if half > n1 else '')
                 + f'{half} of {half} means that the fastest half is on mesh 0 only. One count is given for each repetition. '
                 'A range inside one repetition, such as "4 to 7", means that several threads have the same printed rate at the limit of the fastest half. The count of each mesh is then not defined by the rates [Ref5].</p>')
    for st_ in ('A1', 'A2'):
        c = cpu_panels(s, st_)
        if c:
            ms = sorted(set(x['min_ms'] for x in s[st_].values()))
            o.append(f"<h3>{st_}: rate of each thread against its CPU number (interval {' or '.join(f'{m/1000:g} s' for m in ms)})</h3>" + c)
            o.append('<p class="cap">One dot is one thread: the median of its rates over all repetitions of the kernel. The dashed line is the border between mesh 0 and mesh 1. '
                     'The vertical axis starts at 0 GB/s. The three panels of one row share one scale, and the two rows have different scales. '
                     'Under each panel: the median thread rate of each mesh, the same number as in the list above and in the table below. It is the median over the repetitions of the median over the threads of one repetition.</p>')
    # table per kernel
    o.append('<h3>Numbers per kernel</h3><div class="tw"><table><tr><th>Step</th><th>Kernel</th><th>Binary</th><th>Interval (s)</th><th>Repetitions</th><th>Total GB/s, lowest to highest</th><th>Median total GB/s</th>'
             '<th>Sum of thread rates mesh 0, GB/s</th><th>Sum of thread rates mesh 1, GB/s</th><th>Median thread rate mesh 0, GB/s</th><th>Median thread rate mesh 1, GB/s</th><th>q</th><th>Pattern</th><th>Threads of the fastest half on mesh 0, per repetition</th></tr>')
    for st_ in ('A1', 'A2'):
        for k in KORDER:
            if k not in s[st_]: continue
            x = s[st_][k]
            o.append(f"<tr><td>{st_}</td><td>{KNAME[k]}</td><td>{e(x['binary'])}</td><td>{x['min_ms']/1000:g}</td><td>{len(x['reps'])}</td><td>{rtxt(x['total_GBps'])}</td><td>{f2(x['total_GBps']['median'])}</td>"
                     f"<td>{rtxt(x['mesh0_sum'])}</td><td>{rtxt(x['mesh1_sum'])}</td><td>{rtxt(x['mesh0_median'])}</td><td>{rtxt(x['mesh1_median'])}</td><td>{rtxt(x['q'])}</td>"
                     f"<td>{', '.join(x['labels']) if x['labels'] else 'labels not used'}</td><td>{fh_reps(x['reps'])}</td></tr>")
    o.append('</table></div>')
    o.append('<details><summary>Every repetition of A1 and A2</summary><div class="tw"><table><tr><th>Step</th><th>Launch</th><th>Repetition</th><th>Total GB/s</th><th>Passes per thread</th><th>Sum mesh 0, GB/s</th><th>Sum mesh 1, GB/s</th><th>Median mesh 0, GB/s</th><th>Median mesh 1, GB/s</th><th>q</th><th>Fastest half on mesh 0</th></tr>')
    for st_ in ('A1', 'A2'):
        for k in KORDER:
            for r in s[st_].get(k, {}).get('reps', []):
                o.append(f"<tr><td>{st_}</td><td>{e(r['tag'])}</td><td>{r['rep']}</td><td>{fx(r['total_GBps'], 2)}</td><td>{fx(r['passes_per_thread'], 1)}{' (below 50)' if r['below_50_passes'] else ''}</td>"
                         f"<td>{f2(r['mesh0']['sum'])}</td><td>{f2(r['mesh1']['sum'])}</td><td>{f2(r['mesh0']['median'])}</td><td>{f2(r['mesh1']['median'])}</td><td>{f2(r['q'], 3)}</td><td>{fh_reps([r])}</td></tr>")
    o.append('</table></div></details>')
    # write repetitions: highest against lowest total (plan: "the faster write repetitions")
    w = write_hi_lo(s)
    if w:
        li = [f"<li>{x['step']}, {KNAME[x['k']]}: the totals of the {x['n']} repetitions were {fx(x['lo'], 2)} to {fx(x['hi'], 2)} GB/s. "
              f"From the repetition with the lowest total to the one with the highest, the sum of the thread rates changed by {fs(x['d0'], 2)} GB/s on mesh 0 and by {fs(x['d1'], 2)} GB/s on mesh 1.</li>" for x in w]
        o.append('<h3>Write kernels: the repetition with the highest total against the one with the lowest</h3><p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')
        o.append(f'<p class="take">Observed in screening: {write_hi_lo_txt(w)[0].lower() + write_hi_lo_txt(w)[1:]}</p>')
    # A1 against A2
    c = s['A1_A2']
    o.append('<h3>Totals with the short and with the long interval</h3>')
    if not c['kernels']:
        o.append(missing('The comparison of the totals needs both A1 and A2. The measurement that is missing: the step that has no data above.'))
    else:
        o.append('<div class="tw"><table><tr><th>Kernel</th><th>Short interval (s)</th><th>Total GB/s, short: lowest to highest</th><th>Median, short</th><th>Long interval (s)</th><th>Total GB/s, long: lowest to highest</th><th>Median, long</th><th>Change of the median, GB/s</th><th>Change, %</th><th>The two ranges overlap</th><th>Long totals outside the short range</th></tr>')
        for k in KORDER:
            if k not in c['kernels']: continue
            x = c['kernels'][k]
            o.append(f"<tr><td>{KNAME[k]}</td><td>{x['short_ms']/1000:g}</td><td>{rtxt(x['short'])}</td><td>{fx(x['short']['median'], 2)}</td><td>{x['long_ms']/1000:g}</td><td>{rtxt(x['long'])}</td><td>{fx(x['long']['median'], 2)}</td>"
                     f"<td>{fs(x['change_GBps'], 2)}</td><td>{fs(x['change_pct'], 1)}</td><td>{'yes' if x['ranges_overlap'] else 'no'}</td><td>{x['n_long_outside_short']} of {x['n_long']}</td></tr>")
        o.append('</table></div>')
        no = [KNAME[k] for k in KORDER if k in c['kernels'] and not c['kernels'][k]['ranges_overlap']]
        t = f"Observed in screening: for {len(no)} of the {len(c['kernels'])} kernels, the range of the totals with the long interval does not overlap the range with the short interval" + (f" ({', '.join(no)})." if no else '.')
        t += ' Count of the single long totals that lie outside the short range: ' + ', '.join(f"{KNAME[k]} {c['kernels'][k]['n_long_outside_short']} of {c['kernels'][k]['n_long']}" for k in KORDER if k in c['kernels']) + '.'
        o.append(f'<p class="take">{t}</p>')
        o.append(order_b7_b8(s))
        o.append(f'<p class="miss"><b>{ID}.</b> The difference between two copies of one loop. Part A has no such control. So this page does not say whether a change is larger than that difference. Steps B7 and B10 measure it [Ref1].</p>')
    return '\n'.join(o)


def order_b7_b8(s):
    """Consequence of A2 for the order of B7 and B8 (plan, 'Order and decision points', item 2)."""
    c = s['A1_A2']; d = c['old_minus_new_read_GBps']; rd = c.get('order_reading')
    o = ['<h3 id="order">Consequence for the order of B7 and B8</h3>',
         '<p>The plan sets the order of the next read steps from A2: "if A2 changed the totals, B7 comes first; otherwise B7 and B8 are run together" [Ref1]. '
         'The plan gives no number for "changed". B7 and B8 are steps for the difference between old read and new read (Q2a).</p>']
    if not rd:
        return '\n'.join(o) + missing('The reading of A2 needs the totals of old read and of new read with both intervals. At least one of them has no data.')
    ks = c['kernels']; so, sn = ks['read_old'], ks['read_new']
    sh, lg = f"{so['short_ms']/1000:g} s", f"{so['long_ms']/1000:g} s"
    li = [f"<li>The median total of old read minus the median total of new read was {fs(d['short'])} GB/s with the {sh} interval. It was {fs(d['long'])} GB/s with the {lg} interval. "
          + ('So the difference of Q2a got smaller with the long interval.' if rd['difference_smaller_with_long'] else 'So the difference of Q2a did not get smaller with the long interval.') + '</li>',
          f"<li>From the lowest and highest totals, this difference can lie from {fx(d['short_range'][0])} to {fx(d['short_range'][1])} GB/s with the {sh} interval. "
          f"It can lie from {fx(d['long_range'][0])} to {fx(d['long_range'][1])} GB/s with the {lg} interval. The two ranges {'do not overlap' if rd['changed'] else 'overlap'}.</li>"]
    for k in ('read_old', 'read_new'):
        x = ks[k]
        li.append(f"<li>{KNAME[k].capitalize()}: the median total moved by {fs(x['change_pct'], 1)} %. {x['n_long_outside_short']} of its {x['n_long']} totals with the long interval lie outside its range with the short interval.</li>")
    o.append('<p>Observed in screening, in <code>A1.csv</code> and <code>A2.csv</code> [Ref4]:</p><ul>' + ''.join(li) + '</ul>')
    if rd['changed']:
        t = ('Reading of this page (choice C11 of the analysis script [Ref5]): A2 changed the totals. By item 2 of the plan, B7 then comes first'
             + (', and H7a gets priority in B7 [Ref1].' if rd['difference_smaller_with_long'] else '. The difference did not get smaller, so the change is not in the direction that H7a names [Ref1].'))
    else:
        t = ('Reading of this page (choice C11 of the analysis script [Ref5]): the totals stayed. By item 2 of the plan, H7a then gets no priority, and B7 and B8 are run together [Ref1]. '
             'The plan says for this case that the short interval alone is not sufficient to explain Q2a [Ref1].')
    o.append(f'<p class="take">{t} Part A has no control with two copies of one loop, so this reading is screening only.</p>')
    o.append('<p>One conflict is open. The handoff, section B.9 "Settings after B7", takes the settings of B8 from the analysis of B7. So B8 cannot start before B7 is analysed [Ref2]. '
             'Item 3 of the same list of the plan also says "B7 first" [Ref1]. The user decides which rule applies.</p>')
    wk = [k for k in ('write_old', 'write_new', 'asmwrite') if k in ks]
    if wk:
        o.append('<p>Item 2 does not use the write totals. The plan runs the write step B10 whatever B7 shows [Ref1]. Observed in screening for the write kernels: '
                 + ' '.join(f"{KNAME[k].capitalize()}: median total {fs(ks[k]['change_pct'], 1)} %, {ks[k]['n_long_outside_short']} of {ks[k]['n_long']} long totals outside the short range." for k in wk) + '</p>')
    return '\n'.join(o)


def sec_a3(s):
    o = ['<h2 id="a3">A3: old read with one and with two buffers per thread</h2>']
    g = s['A3']['groups']
    if not g:
        why = '; '.join(k for x in s['env'] for k in x.get('skipped', []) if k.startswith('A3'))
        return '\n'.join(o) + missing('Step A3 has no usable data.' + (f' The script wrote: "{e(why)}".' if why else '') + ' The measurement that is missing: old read with <code>--kernel read</code> and with <code>--kernel all</code>, 3 processes for each of the 4 cases.')
    o.append('<p>Only the rows of the read kernel are compared. With two buffers the process also times write and copy [Ref2].</p>')
    rows = []
    for name, x in g.items():
        pts = [(r['q'], f"{r['tag']} repetition {r['rep']}: q {fx(r['q'], 3)}, total {fx(r['total_GBps'], 2)} GB/s") for p in x['processes'] for r in p['reps'] if r['q'] is not None]
        rows.append((f"{x['buffers']} buffer{'s' if x['buffers'] > 1 else ''}, {x['min_ms']/1000:g} s", pts, f"q {rtxt(x['q'])}; total {f2(x['total_GBps']['median'], 0)} GB/s"))
    o.append(strip_chart(rows, 0, 1, [0, 0.25, 0.5, 0.65, 0.85, 1], 'q of the read rows (no unit)', 'q of old read with one and with two buffers',
                         band=(s['limits']['q_split_below'], s['limits']['q_uniform_above'], 'between')))
    o.append('<p class="cap">One dot is one repetition of the read kernel. Each row is labelled with its range of q and its median total.</p>')
    o.append('<div class="tw"><table><tr><th>Case</th><th>Processes</th><th>Read repetitions</th><th>Total GB/s, lowest to highest</th><th>Median total GB/s</th><th>q</th><th>Pattern</th><th>Repetitions below 50 passes</th></tr>')
    for name, x in g.items():
        o.append(f"<tr><td>{x['buffers']} buffer{'s' if x['buffers'] > 1 else ''}, {x['min_ms']/1000:g} s</td><td>{len(x['processes'])}</td><td>{x['q']['n']}</td><td>{rtxt(x['total_GBps'])}</td><td>{f2(x['total_GBps']['median'])}</td><td>{rtxt(x['q'])}</td><td>{x['label'] or 'labels not used'}</td><td>{x['n_below_50_passes']}</td></tr>")
    o.append('</table></div>')
    if not s['A3']['compare']:
        return '\n'.join(o) + missing('The comparison needs both cases at one interval. One of them has no data.')
    o.append(f'<p class="take">{a3_answer(s)}</p>')
    li = []
    for ms, c in s['A3']['compare'].items():
        t = f"<li>Interval {int(ms)/1000:g} s: q was {rtxt(c['q_one'])} with one buffer. It was {rtxt(c['q_two'])} with two buffers. The two ranges of q {'overlap' if c['q_ranges_overlap'] else 'do not overlap'}. "
        if c['same_label'] is not None:
            t += f"The pattern label was {c['one_label']} with one buffer and {c['two_label']} with two. "
        t += f"The median total changed by {fs(c['total_change_GBps'], 2)} GB/s from one buffer to two.</li>"
        li.append(t)
    o.append('<p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')
    return '\n'.join(o)


def a4_chart(k, x, lim, usable):
    W, H, top, bot = 780, 250, 34, 190
    panels = [('64+b', 60, 470), ('a+a', 540, 750)]
    Y = lambda q: bot - q * (bot - top)
    o = svg_open(W, H, f'q against thread count, {KNAME.get(k, k)}')
    for sname, xa, xb in panels:
        ser = x['series'][sname]; cs = ser['counts']
        o.append(f'<rect x="{xa}" y="{fx(Y(lim["q_uniform_above"]), 1)}" width="{xb-xa}" height="{fx(Y(lim["q_split_below"])-Y(lim["q_uniform_above"]), 1)}" fill="{BAND}"/>')
        for t in (0, 0.25, 0.5, lim['q_split_below'], lim['q_uniform_above'], 1):
            o.append(f'<line x1="{xa}" y1="{fx(Y(t), 1)}" x2="{xb}" y2="{fx(Y(t), 1)}" stroke="{GRID}"/>')
            o.append(f'<text x="{xa-6}" y="{fx(Y(t)+4, 1)}" text-anchor="end" class="ax">{t:g}</text>')
        o.append(f'<text x="{xa}" y="{top-18}" class="lab">{"64 threads on mesh 0, b threads on mesh 1" if sname == "64+b" else "a threads on each mesh"}</text>')
        if not cs:
            o.append(f'<text x="{(xa+xb)/2}" y="{(top+bot)/2}" text-anchor="middle" class="lab">{ID}: no count of this series</text>'); continue
        X = lambda i: xa + (i + 0.5) * (xb - xa) / len(cs)
        pts = []
        for i, c in enumerate(cs):
            cc = x['counts'][c]; qs = [r['q'] for r in cc['reps'] if r['q'] is not None]
            if not qs: continue
            pts.append((X(i), Y(st.median(qs))))
        if len(pts) > 1:
            o.append(f'<polyline points="{" ".join(f"{fx(a, 1)},{fx(b, 1)}" for a, b in pts)}" fill="none" stroke="#8a8984" stroke-width="1.5"/>')
        for i, c in enumerate(cs):
            cc = x['counts'][c]; qs = [r['q'] for r in cc['reps'] if r['q'] is not None]
            for j, r in enumerate(cc['reps']):
                if r['q'] is not None:
                    o.append(marker(X(i) + (j - (len(qs) - 1) / 2) * 7, Y(r['q']), 'circle', C0, f"{c} threads, repetition {r['rep']}: q {fx(r['q'], 3)}, total {fx(r['total_GBps'], 2)} GB/s", r=4))
            if qs:
                ylab = Y(max(qs)) - 10
                if ylab < top - 2: ylab = Y(min(qs)) + 18
                o.append(f'<text x="{fx(X(i), 1)}" y="{fx(ylab, 1)}" text-anchor="middle" class="val">{fx(st.median(qs), 2)}</text>')
            o.append(f'<text x="{fx(X(i), 1)}" y="{bot+16}" text-anchor="middle" class="ax">{c}</text>')
            o.append(f'<text x="{fx(X(i), 1)}" y="{bot+31}" text-anchor="middle" class="val">{(cc["label"] or "") if usable else ""}</text>')
        o.append(f'<text x="{(xa+xb)/2}" y="{H-4}" text-anchor="middle" class="ax">threads on mesh 0 + threads on mesh 1</text>')
    o.append(f'<text x="14" y="{(top+bot)/2}" text-anchor="middle" class="ax" transform="rotate(-90 14 {(top+bot)/2})">q (ratio)</text>')
    o.append('</svg>')
    return '\n'.join(o)


def a3_answer(s):
    """The answer to the plan's question of A3: whether the second buffer changes the pattern in this session."""
    cmp = s['A3']['compare']
    apart = [ms for ms, c in cmp.items() if not c['q_ranges_overlap']]
    two = [(g['q']['max'], g['min_ms']) for g in s['A3']['groups'].values() if g['buffers'] == 2 and g['q']['n']]
    if apart:
        t = ('Observed in screening: q changed with the second buffer. The range of q with two buffers does not overlap the range with one buffer at the interval '
             + ' and '.join(f'{int(ms)/1000:g} s' for ms in apart) + '.')
    else:
        t = ('Observed in screening: no change of q with the second buffer. At ' + ('each of the ' + str(len(cmp)) + ' intervals' if len(cmp) > 1 else 'the one interval')
             + ' the range of q with two buffers overlaps the range with one buffer.')
    if two:
        q, ms = max(two)
        t += f" The highest q of old read with two buffers in this session was {fx(q, 2)} (interval {ms/1000:g} s)."
    return t


def a4_facts(x):
    """For one kernel of A4, series 64+b: the largest step of the median q between neighbouring counts with threads on both meshes, and the lowest median q."""
    cs = [c for c in x['series']['64+b']['counts'] if not c.endswith('+0') and x['counts'][c]['q']['n']]
    if len(cs) < 2:
        return None
    med = {c: x['counts'][c]['q']['median'] for c in cs}
    i = max(range(len(cs) - 1), key=lambda j: abs(med[cs[j + 1]] - med[cs[j]]))
    low = min(cs, key=lambda c: med[c])
    b = lambda c: int(c.split('+')[1])
    return dict(lower=cs[i], upper=cs[i + 1], q_lower=med[cs[i]], q_upper=med[cs[i + 1]], apart=b(cs[i + 1]) - b(cs[i]), lowest=low, q_lowest=med[low], last=cs[-1], q_last=med[cs[-1]])


def b8_consequence(s):
    """Consequence of A4 for B8 (handoff B.9 row B8 and B.10 item B8)."""
    ks = s['A4']['kernels']; usable = s['q']['decision']['labels_usable']
    o = ['<h3 id="b8">Consequence for B8</h3>']
    if usable:
        li = []
        for k, x in ks.items():
            br = x['series']['64+b']['bracket']
            li.append(f"<li>{KNAME.get(k, k)}: " + (f"the pattern changed between {br[0]} and {br[1]} threads. B8 refines the grid around these two counts in steps of 4 threads [Ref2]." if br
                                                 else f"{ID}. A4 gives no pair of counts for this kernel ({e(x['series']['64+b']['note'])}). So Part A gives no thread counts of this kernel for B8.") + '</li>')
        o.append('<p>B8 needs "the two counts between which A4 saw the pattern change", for each kernel [Ref2].</p><ul>' + ''.join(li) + '</ul>')
        return '\n'.join(o)
    lim = s['limits']
    o.append(f'<p class="miss"><b>{ID}.</b> Part A gives no thread counts for B8. B8 needs "the two counts between which A4 saw the pattern change" [Ref2]. '
             f"The pattern rule of the handoff, with the limits {lim['q_split_below']} and {lim['q_uniform_above']}, is not used on this page. The handoff says not to use the labels if q does not fall into two groups [Ref2]. "
             'By the test of the analysis script (choice C2) q does not fall into two groups [Ref5]. So A4 gives no pair of counts between which the pattern changes. '
             'What is needed before B8: a pattern rule that fits the measured q. The steps B5 and B9 use the same label, so they need it too [Ref2].</p>')
    li = []
    for k, x in ks.items():
        f = a4_facts(x)
        if not f: continue
        t = (f"<li>{KNAME.get(k, k).capitalize()}, series 64+b: the largest step of the median q between two neighbouring counts is from {fx(f['q_lower'])} at {f['lower']} to {fx(f['q_upper'])} at {f['upper']}. "
             f"These two counts are {f['apart']} threads apart" + ('. That is already the step of B8 [Ref2]. ' if f['apart'] == 4 else ', and B8 uses a step of 4 threads [Ref2]. ')
             + f"The lowest median q of the series is {fx(f['q_lowest'])} at {f['lowest']}. At {f['last']} the median q is {fx(f['q_last'])}.</li>")
        li.append(t)
    if li:
        o.append('<p>What <code>A4.csv</code> shows without labels, observed in screening (counts with threads on both meshes) [Ref4]:</p><ul>' + ''.join(li) + '</ul>')
    return '\n'.join(o)


def sec_a4(s):
    o = ['<h2 id="a4">A4: pattern against the thread count</h2>']
    ks = s['A4']['kernels']; usable = s['q']['decision']['labels_usable']
    if not ks:
        return '\n'.join(o) + missing('Step A4 has no usable data. The measurement that is missing: old read and asm read at the 11 thread counts of <code>run_partA.sh</code>.')
    for k, x in ks.items():
        o.append(f'<h3>{KNAME.get(k, k)} (<code>{e(x["binary"])}</code>)</h3>' + a4_chart(k, x, s['limits'], usable))
    o.append('<p class="cap">One dot is one repetition. The line joins the medians of the counts, and the number at each count is that median. The grey band is the range "between". '
             + ('Under each count: the pattern label of the count.' if usable else 'No pattern label is shown, because the labels are not used on this page.') + '</p>')
    li = []
    for k, x in ks.items():
        for sname, ser in x['series'].items():
            n = f"{KNAME.get(k, k)}, series {sname}"
            if ser['missing']:
                li.append(f"<li>{n}: {ID} for the counts {', '.join(ser['missing'])}. These launches have no usable block.</li>")
            if not usable:
                qs = ', '.join(f"{c}: {f2(x['counts'][c]['q']['median'])}" for c in ser['counts'])
                li.append(f"<li>{n}: the labels are not used, so no change of pattern is given. Median q per count: {qs}.</li>")
            elif ser['bracket']:
                li.append(f"<li>{n}: the pattern changed between {ser['bracket'][0]} and {ser['bracket'][1]} threads. The labels in the order of the counts: {', '.join(f'{c} {l}' for c, l in zip(ser['counts'], ser['labels']))}.</li>")
            else:
                li.append(f"<li>{n}: {e(ser['note'])}. The labels in the order of the counts: {', '.join(f'{c} {l}' for c, l in zip(ser['counts'], ser['labels']))}.</li>")
    for sname, v in s['A4']['bracket_compare'].items():
        if v == 'equal':
            li.append(f"<li>Series {sname}: the two kernels changed between the same two counts. The plan calls this \"not resolved at this grid\" [Ref1].</li>")
        elif v == 'different':
            li.append(f"<li>Series {sname}: the two kernels changed between different counts.</li>")
    for k, x in ks.items():
        for c, cc in x['counts'].items():
            t = mesh_change_txt(cc['reps'])
            if t:
                li.append(f"<li>{KNAME.get(k, k)} at {c} threads: the faster mesh was not the same in the {len(cc['reps'])} repetitions. {t}</li>")
    o.append('<p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')
    if usable:
        o.append('<p>The count 64+0 has threads on one mesh only. It keeps its own label, and the change of pattern is looked for among the counts with threads on both meshes [Ref5].</p>')
    else:
        o.append('<p>The count 64+0 has threads on one mesh only. Its q is shown, and it is not compared with the counts that have threads on both meshes [Ref5].</p>')
    o.append('<div class="tw"><table><tr><th>Kernel</th><th>Threads</th><th>Total GB/s (each repetition)</th><th>q (each repetition)</th><th>Median thread rate mesh 0, GB/s (each repetition)</th><th>Median thread rate mesh 1, GB/s (each repetition)</th><th>Threads of the fastest half on mesh 0 (each repetition)</th><th>Pattern</th><th>Passes per thread (each repetition)</th></tr>')
    for k, x in ks.items():
        for sname in ('64+b', 'a+a'):
            for c in x['series'][sname]['counts']:
                cc = x['counts'][c]; rr = cc['reps']
                o.append(f"<tr><td>{KNAME.get(k, k)}</td><td>{c}</td><td>{', '.join(f2(r['total_GBps']) for r in rr)}</td><td>{', '.join(f2(r['q'], 3) for r in rr)}</td>"
                         f"<td>{', '.join(f2(r['mesh0']['median']) for r in rr)}</td><td>{', '.join(f2(r['mesh1']['median']) for r in rr)}</td><td>{fh_reps(rr)}</td>"
                         f"<td>{(cc['label'] or '-') if usable else 'labels not used'}</td><td>{', '.join(f2(r['passes_per_thread'], 1) for r in rr)}</td></tr>")
    o.append('</table></div>')
    o.append('<p class="cap">The fastest half of a count is half of its threads. A range such as "26 to 32" inside one repetition comes from equal printed rates at the limit of the fastest half [Ref5].</p>')
    o.append(b8_consequence(s))
    return '\n'.join(o)


def box_hits(box, boxes, segs, hlines, plot):
    """True if the text box touches an earlier box, a dashed line or the data line. box = (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    if any(x0 < b[2] + 2 and b[0] - 2 < x1 and y0 < b[3] + 2 and b[1] - 2 < y1 for b in boxes):
        return True
    if x1 > plot[0] and x0 < plot[1] and any(y0 - 2 <= y <= y1 + 2 for y in hlines):
        return True
    for ax, ay, bx, by in segs:
        lo, hi = max(ax, x0 - 3), min(bx, x1 + 3)
        if lo > hi:
            continue
        f = lambda x: ay if bx == ax else ay + (by - ay) * (x - ax) / (bx - ax)
        ya, yb = sorted((f(lo), f(hi)))
        if ya <= y1 + 3 and yb >= y0 - 3:
            return True
    return False


def place_label(px, py, w, first, last, below_first, y_top, y_bot, boxes, segs, hlines, plot):
    """Find a free place for the value label of the point (px, py). Returns (anchor, x, baseline) or None."""
    cands = []
    dys = (16, -8, 28, -20, 40, -32) if below_first else (-8, 16, -20, 28, -32, 40)
    main = 'start' if first else 'end' if last else 'middle'
    for anchor, tx in [(main, px)] + ([] if first else [('end', px - 5)]) + ([] if last else [('start', px + 5)]):
        for dy in dys:
            cands.append((anchor, tx, py + dy, True))
    if first:
        cands.insert(2, ('end', px - 7, py + 4, False))          # in the left margin, beside the point
    for anchor, tx, base, inside in cands:
        bx0 = tx if anchor == 'start' else tx - w if anchor == 'end' else tx - w / 2
        box = (bx0, base - 9, bx0 + w, base + 2)
        if inside and (box[1] < y_top + 1 or box[3] > y_bot - 1 or box[0] < plot[0] - 1 or box[2] > plot[1] + 1):
            continue
        if not box_hits(box, boxes, segs, hlines, plot):
            boxes.append(box)
            return anchor, tx, base
    return None


def a5_chart(procs, lim):
    allr = [v for p in procs for v in p['rates_GBps']]
    ymin = min(min(allr), lim['low_below_GBps']) - 0.6; ymax = max(max(allr), lim['high_above_GBps']) + 0.9
    W, L, R, ph, gap, top = 780, 64, 170, 120, 46, 30
    H = top + len(procs) * (ph + gap)
    nmax = max(max(p['n_intervals'] for p in procs), 2)
    X = lambda i: L + i / (nmax - 1) * (W - L - R)
    o = svg_open(W, H, 'Rate against interval number for each A5 process')
    left_out = 0
    for pi, p in enumerate(procs):
        y0 = top + pi * (ph + gap)
        Y = lambda v: y0 + ph - (v - ymin) / (ymax - ymin) * ph
        o.append(f'<rect x="{L}" y="{y0}" width="{W-L-R}" height="{ph}" fill="none" stroke="{GRID}"/>')
        o.append(f'<rect x="{L}" y="{fx(Y(lim["high_above_GBps"]), 1)}" width="{W-L-R}" height="{fx(Y(lim["low_below_GBps"])-Y(lim["high_above_GBps"]), 1)}" fill="{BAND}"/>')
        o.append(f'<text x="{L}" y="{y0-8}" class="lab">CPU {p["cpu"]}, process {p["proc"]} (started {p["utc"]} UTC, waited {p["waited_s"]:g} s)</text>')
        for v, lab in ((lim['high_above_GBps'], f'{lim["high_above_GBps"]:g} GB/s: above is high'), (lim['low_below_GBps'], f'{lim["low_below_GBps"]:g} GB/s: below is low')):
            o.append(f'<line x1="{L}" y1="{fx(Y(v), 1)}" x2="{W-R}" y2="{fx(Y(v), 1)}" stroke="{MUTED}" stroke-dasharray="4 3"/>')
            o.append(f'<text x="{W-R+8}" y="{fx(Y(v)+4, 1)}" class="ax">{lab}</text>')
        boxes = []
        for v in (ymin, ymax):
            o.append(f'<text x="{L-6}" y="{fx(Y(v)+4, 1)}" text-anchor="end" class="ax">{fx(v, 1)}</text>')
            boxes.append((L - 36, Y(v) - 6, L - 6, Y(v) + 6))
        for i in range(0, nmax, 5):
            o.append(f'<text x="{fx(X(i), 1)}" y="{y0+ph+14}" text-anchor="middle" class="ax">{i}</text>')
        r = p['rates_GBps']
        if not r: continue
        o.append(f'<polyline points="{" ".join(f"{fx(X(i), 1)},{fx(Y(v), 1)}" for i, v in enumerate(r))}" fill="none" stroke="{C0}" stroke-width="2"/>')
        usable = p.get('labels_usable', True)
        for i, v in enumerate(r):
            tip = f'interval {i}: {fx(v, 2)} GB/s' + (f' ({p["levels"][i]})' if usable else '')
            o.append(f'<circle cx="{fx(X(i), 1)}" cy="{fx(Y(v), 1)}" r="3" fill="{C0}" stroke="#fff" stroke-width="1"><title>{tip}</title></circle>')
        segs = [(X(i), Y(r[i]), X(i + 1), Y(r[i + 1])) for i in range(len(r) - 1)]
        hl = [Y(lim['high_above_GBps']), Y(lim['low_below_GBps'])]
        want = list(dict.fromkeys([r.index(min(r)), r.index(max(r)), 0, len(r) - 1] + [c['at_interval'] for c in p['changes']]))
        for i in want:
            txt = fx(r[i], 2)
            got = place_label(X(i), Y(r[i]), 6.4 * len(txt) + 2, i == 0, i == len(r) - 1, r[i] == min(r), y0, y0 + ph, boxes, segs, hl, (L, W - R))
            if not got:
                left_out += 1; continue
            anchor, tx, base = got
            o.append(f'<text x="{fx(tx, 1)}" y="{fx(base, 1)}" text-anchor="{anchor}" class="val">{txt}</text>')
    o.append(f'<text x="{L+(W-L-R)/2}" y="{H-8}" text-anchor="middle" class="ax">interval number in the process (each interval is at least 0.3 s)</text>')
    o.append(f'<text x="14" y="{top+ph/2}" text-anchor="middle" class="ax" transform="rotate(-90 14 {top+ph/2})">rate, GB/s</text>')
    o.append('</svg>')
    return '\n'.join(o), ymin, left_out


def level_check_items(s):
    """One list item per CPU: the result of the check of the two level limits against the rates of this run (choice C9)."""
    lv = s.get('level_check') or {}
    li = []
    for cpu, c in (lv.get('cpus') or {}).items():
        t = f"<li>CPU {cpu} ({pl(c['n'], 'interval', 'intervals')}, {fx(c['min'])} to {fx(c['max'])} GB/s). "
        for x in c['limits']:
            if x['empty_range'] is None:
                t += f"Limit {x['limit']:g} GB/s: all rates lie on one side of it. "
            elif x['separates']:
                t += (f"Limit {x['limit']:g} GB/s: it separates the rates. The nearest rates are {fx(x['nearest_below'])} and {fx(x['nearest_at_or_above'])} GB/s, "
                      f"so the empty range around the limit is {fx(x['empty_range'])} GB/s wide. ")
            else:
                t += (f"Limit {x['limit']:g} GB/s: it does not separate the rates. {x['n_below']} rates are below it and {x['n_at_or_above']} are at or above it. "
                      f"The nearest rates are {fx(x['nearest_below'])} and {fx(x['nearest_at_or_above'])} GB/s. {x['n_within']} of the {c['n']} rates lie within {fx(lv['gap_min_GBps'])} GB/s of the limit. ")
        t += ('The level labels are used for this CPU. They stay provisional.' if c['labels_usable'] else
              'So the level labels are not usable for this CPU in this run. This page reports the CPU by its rates.')
        li.append(t + '</li>')
    return li


def a5_usable(p):
    return p.get('labels_usable', True)


def a5_other_labels(p):
    """For a process with usable labels and no change between low and high: which labels its intervals have."""
    have = [l for l in ('low', 'changing', 'high') if p['n_' + l]]
    if len(have) == 1:
        return f"All its intervals were {have[0]}."
    return f"Its intervals changed only between {' and '.join(have)}."


def sec_a5(s):
    o = ['<h2 id="a5">A5: asm read with one thread at 8 MiB, 30 intervals</h2>']
    procs = s['A5']['processes']; lim = s['limits']
    if not procs:
        return '\n'.join(o) + missing('Step A5 has no usable data. The measurement that is missing: 2 processes on CPU 2 and 2 processes on CPU 41, 30 intervals each.')
    lv = s.get('level_check') or {}; lo, hi = lim['low_below_GBps'], lim['high_above_GBps']
    o.append(f"<p>An interval is low below {lo:g} GB/s, high above {hi:g} GB/s, and changing otherwise. These limits are provisional. The plan asks to check them against the new data before they are used [Ref1].</p>")
    li = level_check_items(s)
    if li:
        o.append(f"<h3>Check of the two limits against the rates of this run</h3><p>The plan gives no test for this check. The analysis script uses this one (choice C9) [Ref5]. "
                 f"A limit does not separate the rates of a CPU if rates lie on both sides of it and the empty range around it is smaller than {fx(lv['gap_min_GBps'])} GB/s. "
                 "The rates of A5 and A6 on one CPU are taken together.</p><ul>" + ''.join(li) + '</ul>')
        lc = s['level_counts_8MiB']
        nch = sum(p['n_changing'] for p in procs if not a5_usable(p))
        t = (f"Over all {lc['n']} intervals of A5 and A6, the rates were {rtxt(lc['rate'], unit='GB/s')}. The widest empty ranges of these rates are "
             + ' and '.join(f"{fx(g['low'])} to {fx(g['high'])} GB/s ({fx(g['width'])} GB/s wide)" for g in lv['largest_empty_ranges']) + '. '
             f"By the two provisional limits alone, {lc['low']} intervals would be low, {lc['changing']} changing and {lc['high']} high. ")
        if nch:
            t += f"{nch} of the {lc['changing']} changing intervals are on a CPU whose labels are not usable. "
        o.append(f'<p>{t}The A6 processes without 2 MiB pages are included in these counts.</p>')
    c, ymin, left_out = a5_chart(procs, lim)
    o.append(c)
    o.append(f'<p class="cap">One panel per process, in time order. All panels share one vertical scale. The vertical axis starts at {fx(ymin, 1)} GB/s, not at 0, so that a change between the two levels is visible. The grey band lies between the two provisional limits. '
             'Labelled points: first, last, highest, lowest, and the first interval after a change between low and high.'
             + (f' {pl(left_out, "label was", "labels were")} left out, because no free place was found.' if left_out else '') + '</p>')
    o.append('<div class="tw"><table><tr><th>CPU</th><th>Process</th><th>Waited before start (s)</th><th>Intervals</th><th>Rate GB/s, lowest to highest</th><th>Rate of interval 0, GB/s</th><th>Rate of the last interval, GB/s</th>'
             f'<th>Intervals below {lo:g} GB/s</th><th>Low</th><th>Changing</th><th>High</th><th>Changes between low and high</th><th>Sequence (L low, c changing, H high)</th></tr>')
    for p in procs:
        r = p['rates_GBps']
        head = (f"<tr><td>{p['cpu']}</td><td>{p['proc']}</td><td>{p['waited_s']:g}</td><td>{p['n_intervals']}</td><td>{rtxt(p['rate'])}</td><td>{f2(r[0] if r else None)}</td><td>{f2(r[-1] if r else None)}</td>"
                f"<td>{p.get('n_below_low_limit', p['n_low'])}</td>")
        if a5_usable(p):
            ch = '; '.join(f"{x['from_level']} to {x['to_level']} at interval {x['at_interval']} (counted from 0)" for x in p['changes']) or 'none'
            seq = ''.join(dict(low='L', high='H', changing='c')[l] for l in p['levels'])
            o.append(head + f"<td>{p['n_low']}</td><td>{p['n_changing']}</td><td>{p['n_high']}</td><td>{ch}</td><td><code>{seq}</code></td></tr>")
        else:
            o.append(head + '<td>-</td><td>-</td><td>-</td><td>-</td><td>labels not used for this CPU</td></tr>')
    o.append('</table></div>')
    li = []
    for p in procs:
        n = f"CPU {p['cpu']}, process {p['proc']}"; r = p['rates_GBps']
        if not a5_usable(p):
            li.append(f"<li>{n}: the labels are not used. The rate was {fx(r[0])} GB/s in interval 0 and {fx(r[-1])} GB/s in the last interval. "
                      f"The lowest rate was {fx(min(r))} GB/s (interval {r.index(min(r))}), and the highest was {fx(max(r))} GB/s (interval {r.index(max(r))}). "
                      f"{p['n_below_low_limit']} of the {p['n_intervals']} rates were below {lo:g} GB/s. Intervals are counted from 0.</li>")
        elif p['changes']:
            li.append(f"<li>{n}: " + '; '.join(f"a change from {x['from_level']} to {x['to_level']} was observed. The first {x['to_level']} interval was number {x['at_interval']} (counted from 0)." for x in p['changes'])
                      + f" {p['n_low']} intervals were low, {p['n_changing']} changing and {p['n_high']} high.</li>")
        else:
            li.append(f"<li>{n}: no change between low and high was observed in {p['n_intervals']} intervals. {p['n_low']} intervals were low, {p['n_changing']} changing and {p['n_high']} high. {a5_other_labels(p)}</li>")
    by = {(p['cpu'], p['proc']): p for p in procs}
    for pr in s['A5']['pairs']:
        if not pr['have_both']:
            li.append(f"<li>CPU {pr['cpu']}: {ID}. One of the two processes of the pair has no usable block.</li>"); continue
        p1, p2 = by[(pr['cpu'], 1)], by[(pr['cpu'], 2)]
        t = (f"<li>CPU {pr['cpu']}: the second process did not follow at once. It waited {pr['second_waited_s']:g} s for a quiet system. " if pr['second_not_at_once']
             else f"<li>CPU {pr['cpu']}: the second process followed with a wait of 0 s. ")
        t += f"The last interval of the first process had {fx(p1['rates_GBps'][-1])} GB/s, and interval 0 of the second had {fx(p2['rates_GBps'][0])} GB/s"
        t += f" ({pr['last_level_first']}, then {pr['first_level_second']}).</li>" if a5_usable(p1) else '.</li>'
        li.append(t)
    o.append('<p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')
    return '\n'.join(o)


def sec_a6(s):
    o = ['<h2 id="a6">A6: with and without 2 MiB pages</h2>']
    a = s['A6']
    if not a['processes']:
        return '\n'.join(o) + missing('Step A6 has no usable data. The measurement that is missing: 8 processes with and 8 processes without <code>--no-thp</code>.')
    rows = []; allv = []
    for kind, name in (('thp', '2 MiB pages allowed'), ('nothp', '--no-thp (4 KiB pages)')):
        pp = [p for p in a['processes'] if p['kind'] == kind]
        pts = [(p['median_GBps'], f"{p['tag']}: median {fx(p['median_GBps'], 2)} GB/s of {len(p['rates_GBps'])} intervals ({', '.join(f2(v) for v in p['rates_GBps'])})") for p in pp]
        allv += [v for v, _ in pts]
        m = a[kind]['process_medians']
        rows.append((name, pts, f"median {f2(m['median'])} GB/s ({rtxt(m)})" if m['n'] else ID))
    lo, hi = min(allv), max(allv); pad = max((hi - lo) * 0.08, 0.5)
    xmin, xmax = int(lo - pad), int(hi + pad) + 1
    stp = max(1, round((xmax - xmin) / 8))
    lim = s['limits']
    vl = [(v, f'{v:g}') for v in (lim['low_below_GBps'], lim['high_above_GBps']) if xmin < v < xmax]
    o.append(strip_chart(rows, xmin, xmax, list(range(xmin, xmax + 1, stp)), f'median rate of one process, GB/s (axis starts at {xmin}, not at 0)', 'Rate with and without 2 MiB pages', vlines=vl))
    cap = 'One dot is one process: the median of its 3 intervals. Each row is labelled with the median of its processes and their range.'
    if len(vl) == 2:
        cap += f' The two dashed lines are the provisional limits of the level, {vl[0][1]} and {vl[1][1]} GB/s.'
    elif len(vl) == 1:
        cap += f' The dashed line is one provisional limit of the level, {vl[0][1]} GB/s. The other limit lies outside the range of the axis.'
    o.append(f'<p class="cap">{cap}</p>')
    cpus = (s.get('level_check') or {}).get('cpus') or {}
    labels_ok = all(cpus.get(str(p.get('cpu')), {}).get('labels_usable', True) for p in a['processes'])
    t = "Observed in screening: "
    if 'nothp_minus_thp_GBps' in a:
        t += (f"the median rate was {fx(a['thp']['process_medians']['median'], 2)} GB/s with 2 MiB pages allowed and {fx(a['nothp']['process_medians']['median'], 2)} GB/s with <code>--no-thp</code>. "
              f"The difference is {fs(a['nothp_minus_thp_GBps'], 2)} GB/s ({fs(a['nothp_minus_thp_pct'], 1)} %). The two ranges of the process medians {'overlap' if a['process_ranges_overlap'] else 'do not overlap'}. ")
        if labels_ok:
            for kind, name in (('thp', 'With 2 MiB pages allowed'), ('nothp', 'With <code>--no-thp</code>')):
                t += f"{name}, {a[kind]['n_low']} intervals were low, {a[kind]['n_changing']} changing and {a[kind]['n_high']} high. "
        else:
            t += 'The level labels are not used for the CPU of this step (see the check in section A5). '
    else:
        t = f"{ID}. One of the two kinds has no usable process."
    o.append(f'<p class="take">{t}</p>')
    bad = [p['tag'] for p in a['processes'] if not p['thp_line_ok']]
    o.append(f"<p>The benchmark prints its page setting in each block. {len(a['processes']) - len(bad)} of {len(a['processes'])} blocks show the setting that their launch asked for." + (f" Not as asked: {', '.join(bad)}." if bad else '') + '</p>')
    o.append(f'<p class="miss"><b>{ID}.</b> The share of the buffer that was on 2 MiB pages. "2 MiB pages allowed" means only that the program asked for them. Step B4 records the share before every interval [Ref1].</p>')
    o.append('<details><summary>Every A6 process</summary><div class="tw"><table><tr><th>Launch</th><th>Page setting printed</th><th>Waited (s)</th><th>Rate of the 3 intervals, GB/s</th><th>Median, GB/s</th><th>Levels (provisional)</th></tr>')
    for p in a['processes']:
        o.append(f"<tr><td>{e(p['tag'])}</td><td>{e(p['thp_line'] or '-')}</td><td>{p['waited_s']:g}</td><td>{', '.join(f2(v) for v in p['rates_GBps'])}</td><td>{f2(p['median_GBps'])}</td><td>{', '.join(p['levels']) if labels_ok else 'not used'}</td></tr>")
    o.append('</table></div></details>')
    return '\n'.join(o)


def a7_files(s):
    """{file name: (folder, entry)} of the A7 files. If a file exists in several folders, the last folder is used."""
    return {n: (x['folder'], v) for x in s['env'] for n, v in x['a7'].items()}


def a7_codes_txt(p):
    """One sentence group with the PMU type and the event codes of the five events of handoff B.8."""
    t = f"PMU {p['name']}, type number {p['type'] or 'not listed'}. "
    t += ' '.join(f"{x['event'].capitalize()} = {x['name']} {x['code']}." if x['code'] else f"{x['event'].capitalize()}: {ID}, the file has no event named {x['name']}." for x in p['b8'])
    return t


def sec_a7(s):
    o = ['<h2 id="a7">A7: vector length and event lists</h2>']
    files = a7_files(s)
    if not files:
        return '\n'.join(o) + missing('Step A7 has no files. The measurement that is missing: the files <code>A7-sve.txt</code>, <code>A7-perf-list.txt</code>, <code>A7-pmu-devices.txt</code> and <code>A7-core-events.txt</code>.')
    o.append('<p>This step measures no rate. It reads values that later steps need.</p>')
    o.append('<h3 id="codes">Consequence for Part C: the counter codes</h3>')
    o.append('<p>The counter runs of Part C take the PMU type and the event codes from the file <code>A7-core-events.txt</code> (handoff, section B.8) [Ref2]. '
             'PMU means performance monitoring unit: the counter hardware of a core.</p>')
    ce = files.get('A7-core-events.txt')
    pmus = (ce[1].get('pmu_list') or []) if ce else []
    if not pmus:
        o.append(missing('The PMU type and the event codes for Part C. The file <code>A7-core-events.txt</code> is missing or lists no core PMU. The measurement that is missing: the <code>type</code> file and the <code>events/</code> files of the core PMU in <code>/sys/bus/event_source/devices/</code>.'))
    else:
        o.append(f"<p>The file <code>{e(ce[0])}/A7-core-events.txt</code> lists {pl(len(pmus), 'core PMU', 'core PMUs')} [Ref7].</p>")
        for p in pmus:
            o.append(f"<p>Name of the PMU: <code>{e(p['name'])}</code>. Its type number for <code>perf_event_open</code> is {e(p['type'] or ID)} (line {p['line']} of the file). The file lists {pl(p['n_events'], 'event', 'events')} for it. "
                     'The five events of section B.8 have these codes in the file:</p>')
            o.append('<div class="tw"><table class="pt"><tr><th>Event of B.8</th><th>Name in the file</th><th>Code (<code>event=</code>)</th><th>Line of the file</th></tr>'
                     + ''.join(f"<tr><td>{e(x['event'])}</td><td><code>{e(x['name'])}</code></td><td>{'<code>' + e(x['code']) + '</code>' if x['code'] else ID + ': the file has no event of this name'}</td><td>{x['line'] or '-'}</td></tr>" for x in p['b8'])
                     + '</table></div>')
            for x in p['b8_other']:
                o.append(f"<p>The file also lists <code>{e(x['name'])}</code> with the code <code>{e(x['code'])}</code> (line {x['line']}). It is a second candidate for the {e(x['event'])}. This page does not choose between the two names.</p>")
        o.append('<p>The handoff names the five events in words. Which name of the file belongs to each event is a choice of the analysis script (choice C10) [Ref5].</p>')
        o.append(f'<p class="miss"><b>{ID}.</b> Whether these events can be opened without root on CRB. Part A did not try it. The short test of section B.8 (<code>bwx --count</code> with one thread) shows it [Ref2].</p>')
    o.append('<h3>Vector length and lists</h3><ul>')
    sve = files.get('A7-sve.txt')
    if sve and sve[1].get('sve_vector_length_bytes'):
        b = int(sve[1]['sve_vector_length_bytes'])
        o.append(f"<li>The default SVE vector length of a process is {b} bytes ({b * 8} bits) [Ref8]." + (' 128 bits is the smallest SVE vector length.' if b == 16 else '')
                 + ' The plan needs this value for the old write kernel. The bytes of one loop turn of that kernel are not recorded [Ref1].</li>')
    else:
        o.append(f"<li>{ID}: the SVE vector length. The file <code>A7-sve.txt</code> is missing or holds no number.</li>")
    for n, what, ref in (('A7-perf-list.txt', 'The list of <code>perf</code> events', 'Ref9'), ('A7-pmu-devices.txt', 'The list of counter devices', 'Ref10')):
        o.append(f"<li>{what} has {files[n][1]['lines']} lines [{ref}].</li>" if n in files else f"<li>{ID}: the file <code>{n}</code> is missing.</li>")
    o.append('</ul>')
    return '\n'.join(o)


def points_to(s):
    """One generated sentence group per step for the table 'What each result points to'."""
    d = s['q']['decision']; out = {}
    def miss(st_):
        return f'{ID}: step {st_} has no usable data.'
    # A1
    if s['A1']:
        t = []
        rr = [r for st_ in ('A1', 'A2') for r in s[st_].get('read_old', {}).get('reps', []) if r['fastest_half']]
        if rr:
            allm0 = sum(1 for r in rr if r['fastest_half']['mesh0'] == [r['fastest_half']['n_half']] * 2)
            t.append(f"Old read: all {rr[0]['fastest_half']['n_half']} threads of the fastest half were on mesh 0 in {allm0} of the {len(rr)} repetitions of A1 and A2.")
        w = write_hi_lo(s)
        if w:
            t.append('Write kernels: ' + write_hi_lo_txt(w)[0].lower() + write_hi_lo_txt(w)[1:])
        for k in ('read_old', 'write_old', 'write_new', 'asmwrite'):
            if k in s['A1'] and s['A1'][k]['mesh1_median']['n']:
                x = s['A1'][k]
                t.append(f"{KNAME[k].capitalize()} in A1: median thread rate {fx(x['mesh0_median']['median'], 2)} GB/s on mesh 0 and {fx(x['mesh1_median']['median'], 2)} GB/s on mesh 1.")
        out['A1'] = 'Observed in screening. ' + ' '.join(t)
    else: out['A1'] = miss('A1')
    c = s['A1_A2']['kernels']
    if c:
        no = [KNAME[k] for k in KORDER if k in c and not c[k]['ranges_overlap']]
        t = ('Observed in screening. Change of the median total from the short to the long interval: '
             + ' '.join(f"{KNAME[k]} {fs(c[k]['change_GBps'], 2)} GB/s ({fs(c[k]['change_pct'], 1)} %)." for k in KORDER if k in c)
             + f" The range of the long totals does not overlap the range of the short totals for {len(no)} of {len(c)} kernels" + (f" ({', '.join(no)})" if no else '') + '. '
             + 'Long totals outside the short range: ' + ', '.join(f"{KNAME[k]} {c[k]['n_long_outside_short']} of {c[k]['n_long']}" for k in KORDER if k in c) + '. ')
        rd = s['A1_A2'].get('order_reading')
        if rd:
            dd = s['A1_A2']['old_minus_new_read_GBps']
            t += (f"Old read minus new read: {fs(dd['short'])} GB/s with the short interval and {fs(dd['long'])} GB/s with the long interval. "
                  + ('Reading for the order of B7 and B8: A2 changed the totals, so B7 comes first. ' if rd['changed'] else 'Reading for the order of B7 and B8: the totals stayed, so by item 2 of the plan B7 and B8 are run together. ')
                  + 'A conflict with the handoff is open. See the section "Consequence for the order of B7 and B8".')
        else:
            t += f'{ID} for the order of B7 and B8: old read or new read has no totals with both intervals.'
        out['A2'] = t
    else: out['A2'] = miss('A1 or A2')
    if s['A3']['compare']:
        out['A3'] = a3_answer(s) + ' ' + ' '.join(f"Interval {int(ms)/1000:g} s: q was {rtxt(v['q_one'])} with one buffer. It was {rtxt(v['q_two'])} with two buffers." for ms, v in s['A3']['compare'].items())
    else: out['A3'] = miss('A3')
    if s['A4']['kernels']:
        if not d['labels_usable']:
            t = [f'Observed in screening. {ID} for B8: the pattern labels are not used, so A4 gives no pair of counts. Median q without labels, series 64+b:']
            for k, x in s['A4']['kernels'].items():
                f = a4_facts(x)
                if f:
                    t.append(f"{KNAME.get(k, k)}: largest step from {fx(f['q_lower'])} at {f['lower']} to {fx(f['q_upper'])} at {f['upper']}, lowest {fx(f['q_lowest'])} at {f['lowest']}.")
            out['A4'] = ' '.join(t) + ' See the section "Consequence for B8".'
        else:
            t = []
            for k, x in s['A4']['kernels'].items():
                for sname, ser in x['series'].items():
                    t.append(f"{KNAME.get(k, k)}, {sname}: " + (f"change between {ser['bracket'][0]} and {ser['bracket'][1]}" if ser['bracket'] else ser['note']))
            out['A4'] = 'Observed in screening. ' + '. '.join(t) + '.'
    else: out['A4'] = miss('A4')
    if s['A5']['processes']:
        pp = s['A5']['processes']; ok = [p for p in pp if a5_usable(p)]; bad = [p for p in pp if not a5_usable(p)]
        ch = [p for p in ok if p['changes']]
        t = 'Observed in screening. '
        if ok:
            t += f"A change between low and high was observed in {len(ch)} of the {pl(len(ok), 'process', 'processes')} with usable labels. "
            t += ' '.join(f"CPU {p['cpu']}, process {p['proc']}: {x['from_level']} to {x['to_level']}, the first {x['to_level']} interval is number {x['at_interval']} (counted from 0)." for p in ch for x in p['changes'])
            t += ''.join(f" CPU {p['cpu']}, process {p['proc']}: no change between low and high. {a5_other_labels(p)}" for p in ok if not p['changes'])
        cpus = (s.get('level_check') or {}).get('cpus') or {}
        for cpu in sorted(set(p['cpu'] for p in bad)):
            c = cpus[str(cpu)]
            lims = ' and '.join(f"{x['limit']:g} GB/s" for x in c['limits'] if not x['separates'])
            t += f" CPU {cpu} ({pl(sum(1 for p in bad if p['cpu'] == cpu), 'process', 'processes')}): the labels are not used, because the limit {lims} lies inside its rates ({fx(c['min'])} to {fx(c['max'])} GB/s)."
        out['A5'] = t
    else: out['A5'] = miss('A5')
    a = s['A6']
    if 'nothp_minus_thp_GBps' in a:
        out['A6'] = f"Observed in screening. Median rate with --no-thp: {fx(a['nothp']['process_medians']['median'], 2)} GB/s ({rtxt(a['nothp']['process_medians'])}). With 2 MiB pages allowed: {fx(a['thp']['process_medians']['median'], 2)} GB/s ({rtxt(a['thp']['process_medians'])})."
    else: out['A6'] = miss('A6')
    files = a7_files(s)
    if files:
        ce = files.get('A7-core-events.txt'); pmus = (ce[1].get('pmu_list') or []) if ce else []
        t = ('Counter codes for Part C: ' + ' '.join(a7_codes_txt(p) for p in pmus)) if pmus else f'{ID}: no counter codes for Part C, the file A7-core-events.txt is missing or lists no core PMU.'
        sve = files.get('A7-sve.txt')
        if sve and sve[1].get('sve_vector_length_bytes'):
            t += f" SVE vector length: {sve[1]['sve_vector_length_bytes']} bytes."
        out['A7'] = t + f" {pl(len(files), 'file was', 'files were')} written."
    else: out['A7'] = miss('A7')
    return out


CSS = """
:root{color-scheme:light}
body{font-family:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;background:#ffffff;color:#0b0b0b;max-width:920px;margin:0 auto;padding:24px 16px 60px;line-height:1.5;font-size:15px}
h1{font-size:26px;margin:0 0 12px} h2{font-size:20px;margin-top:40px;border-top:1px solid #e6e5e0;padding-top:20px} h3{font-size:16px;margin-top:24px}
.ax{font-size:11px;fill:#52514e} .lab{font-size:12px;fill:#0b0b0b} .val{font-size:11px;fill:#0b0b0b;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}
svg text{font-family:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
.lg{display:inline-flex;align-items:center;margin-right:18px;font-size:13px;color:#52514e} .lg i{width:11px;height:11px;border-radius:50%;margin-right:8px;display:inline-block}
table{border-collapse:collapse;font-size:13px;margin:8px 0} td,th{border-bottom:1px solid #e6e5e0;padding:4px 8px;text-align:right;vertical-align:bottom;font-variant-numeric:tabular-nums} td:first-child,th:first-child,td:nth-child(2),th:nth-child(2){text-align:left} td:first-child,td:nth-child(2){white-space:nowrap}
.take{background:#f1f0ec;padding:10px 14px;border-radius:6px} .cap{font-size:13px;color:#52514e;margin-top:2px} .tw{overflow-x:auto}
.miss{background:#fdf3e7;border-left:4px solid #b85c00;padding:8px 12px} .banner{background:#fdf3e7;border:2px solid #b85c00;padding:10px 14px;font-weight:600}
code{font-size:13px} details{margin:10px 0} summary{cursor:pointer;color:#52514e} .pt td,.pt th{text-align:left;vertical-align:top} .pt td:nth-child(2){white-space:normal}
"""

WORDS = [
    ('CRB', 'the Arm Phoenix Reference Server (128 cores, AArch64). All measurements ran there.'),
    ('Plan', 'the file <code>plan.md</code>, the reviewed test plan for the two questions [Ref1].'),
    ('Handoff', 'the file <code>handoff.md</code>, the instructions for the execution of the plan [Ref2].'),
    ('Part A, screening', 'the first part of the plan. It uses the existing benchmark programs. It can show where to look next. It decides no hypothesis.'),
    ('Part B, Part C, Part D', 'the later parts of the plan. Part B uses a changed copy of the benchmark (<code>bwx</code>). Part C reads the counters of the cores. Part D needs root.'),
    ('Observed in screening', 'the wording for every result of Part A. It means that the result was seen in this run. No control ran with it.'),
    ('Kernel', 'one timed loop of the benchmark <code>bandwidth.c</code>. It is not the Linux kernel.'),
    ('Old read, old write', 'the C kernels before 2026-11-13, from the program <code>bw_old</code>.'),
    ('New read, new write', 'the C kernels since 2026-11-13, from the program <code>bw_new</code>.'),
    ('asm read, asm write', 'the kernels written in assembly, here always from <code>bw_new</code>.'),
    ('Process, launch', 'one start of the benchmark program. The tag of a launch is its name in the run script.'),
    ('Process block', 'the lines of one process in a csv file of a result folder.'),
    ('Repetition, interval', 'one timed period inside a process. Its shortest length is set by the option <code>--min-ms</code>.'),
    ('Pass', 'one sweep of a thread over its whole buffer. A thread runs whole passes until the interval is over.'),
    ('2 % check', 'rule 7 of the plan: one pass must take at most 2 % of the interval. That means at least 50 passes per thread.'),
    ('Rate', 'bytes moved per second, in GB/s (1 GB = 10<sup>9</sup> bytes).'),
    ('Total', 'the rate of a repetition as the benchmark prints it: the bytes of all threads divided by the longest time of a thread.'),
    ('Thread rate', 'the bytes of one thread divided by its own time. The benchmark prints it with 2 decimals.'),
    ('Sum of thread rates', 'the thread rates of one mesh added. It is not the same number as the total.'),
    ('Median', 'the middle value of a sorted list. With an even count it is the mean of the two middle values. Such a median can lie in the middle of two printed values. It is then printed with 3 decimals.'),
    ('Mesh 0, mesh 1', 'the two halves of the chip. CPUs 0 to 63 are on mesh 0. CPUs 64 to 127 are on mesh 1, and we use 64 to 119.'),
    ('a+b threads', 'a threads on mesh 0 (CPUs 0 to a-1) and b threads on mesh 1 (CPUs 64 to 64+b-1).'),
    ('q', 'the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one repetition. The percentile rule is "nearest rank": the P-th percentile is value number ceil(P/100 x n) of the n rates sorted upward. With 120 threads these are the 12th and the 108th value [Ref5].'),
    ('Fastest half', 'the n/2 threads with the highest rates of one repetition with n threads.'),
    ('Split, uniform, between', 'the provisional pattern labels of a repetition: q below 0.65, q above 0.85, or neither.'),
    ('Low, high, changing', 'the provisional level labels of an interval with one thread at 8 MiB: below 69 GB/s, above 70.5 GB/s, or neither.'),
    ('2 MiB pages, <code>--no-thp</code>', 'Linux can back memory with pages of 2 MiB instead of 4 KiB (transparent huge pages, THP). With <code>--no-thp</code> the benchmark asks for 4 KiB pages.'),
    ('<code>madvise</code>, <code>nohugepage</code>', 'the page setting that the benchmark prints. <code>madvise</code>: it asked for 2 MiB pages. <code>nohugepage</code>: it asked for 4 KiB pages.'),
    ('Load', 'the Linux 1-minute load average: the average count of tasks that run or wait to run.'),
    ('Runnable tasks', 'the count of tasks that can run at one moment (4th field of <code>/proc/loadavg</code>).'),
    ('Waited', 'the time the script waited for at most 2 runnable tasks before a launch, 20 s at most.'),
    ('Q1', 'the first question of the plan: why one thread with an 8 MiB buffer behaves differently from the other sizes.'),
    ('Q2a', 'a part of the second question: why old read has a higher total than new read with 120 threads.'),
    ('Q2b', 'the other part: why the write kernels give several separate totals between repetitions.'),
    ('Item 13', 'item 13 of the list "What the existing files already show" of the plan: which threads are the fast ones was not recorded before Part A.'),
    ('H2', 'hypothesis: the low level can change to the high level while the stream runs.'),
    ('H3a', 'hypothesis: the coverage of the buffer with 2 MiB pages decides the level.'),
    ('H7a', 'hypothesis: a part of the difference at 120 threads is made by the stop method and the short interval.'),
    ('H7b', 'hypothesis: a part of the difference is made by the common start of all threads.'),
    ('H8', 'hypothesis: with threads on both meshes the chip has two states, split and uniform. A loop that only loads reaches the uniform state at a lower thread count than old read.'),
    ('H9a', 'hypothesis: the second buffer per thread moved old read to the uniform pattern on 2026-10-30.'),
    ('H9b', 'hypothesis: the pattern of old read differs between sessions for a reason other than the kernel.'),
    ('H11', 'hypothesis: the write totals differ because the threads of one mesh run faster in some intervals.'),
    ('B4', 'step of Part B: asm read at 8 MiB for 200 intervals, with the page state before every interval.'),
    ('B7', 'step of Part B: the read kernels at 64+56 threads with two stop methods, two intervals and two start methods, and with a control of two copies of one loop.'),
    ('B8', 'step of Part B: the thread counts of A4 in steps of 4 threads around the counts where the pattern changes.'),
    ('B5, B9, B10', 'more steps of Part B. B5: read loops with added <code>nop</code> instructions. B9: old read with one and with two buffers. B10: the write kernels with the settings of B7.'),
    ('D2', 'step of Part D: the physical addresses of the buffer pages.'),
    ('PMU', 'performance monitoring unit: the counter hardware of a core.'),
    ('<code>perf_event_open</code>', 'the Linux system call that opens a counter.'),
    ('SVE', 'the scalable vector instruction set of AArch64.'),
    ('Choice C1 to C11', 'a definition that the analysis script had to fix where the plan and the handoff give none. All are listed at the top of <code>analyze_partA.py</code> [Ref5].'),
    ('est.', 'an estimate, not a measurement.'),
]


def short_version(s):
    """At most three sentences. Built from computed values."""
    d = s['q']['decision']; g = s['q'].get('groups') or {}
    sv = 'Part A ran the existing benchmark programs on CRB (the Arm test server) as a first look, and it decides no hypothesis. '
    a, b = g.get('read_old') or {}, g.get('load_only_read') or {}
    if d['n'] == 0:
        sv += f"{ID}: no repetition with per-thread lines exists, so the pattern of the threads cannot be described. "
    elif a.get('n') and b.get('n'):
        lo = min(b['mesh0_median']['min'], b['mesh1_median']['min']); hi = max(b['mesh0_median']['max'], b['mesh1_median']['max'])
        sv += (f"Observed in screening: with {g['count']} threads on the two halves of the chip (mesh 0 and mesh 1), the median thread of old read ran at {rtxt(a['mesh0_median'])} GB/s on mesh 0 "
               f"and at {rtxt(a['mesh1_median'])} GB/s on mesh 1 in all {a['n']} repetitions, and the median thread of new read and asm read ran at {fx(lo)} to {fx(hi)} GB/s on both meshes ({b['n']} repetitions). ")
    elif d['labels_usable']:
        sv += f"Observed in screening: the ratio q of slow to fast threads falls into two groups over {d['n']} repetitions ({fx(d['lower_min'], 2)} to {fx(d['lower_max'], 2)}, and {fx(d['upper_min'], 2)} to {fx(d['upper_max'], 2)}). "
    else:
        sv += (f"Observed in screening: the ratio q of slow to fast threads does not fall into two groups over {d['n']} repetitions"
               + (f" ({fx(d['q_min'], 2)} to {fx(d['q_max'], 2)})" if 'q_min' in d else '') + '. ')
    parts = []
    rd = s['A1_A2'].get('order_reading')
    if rd:
        parts.append(('the long interval made' if rd['difference_smaller_with_long'] else 'the long interval did not make') + ' the difference between old read and new read smaller (A2)')
    else:
        parts.append(f'{ID.lower()} for the order of B7 and B8 (A2)')
    if not s['A4']['kernels']:
        parts.append(f'{ID.lower()} for the thread counts of B8 (A4)')
    elif not d['labels_usable']:
        parts.append('Part A gives no thread counts for B8 because the pattern rule of the handoff does not fit the data (A4)')
    else:
        nb = sum(1 for x in s['A4']['kernels'].values() if x['series']['64+b']['bracket'])
        parts.append(f"A4 gives the thread counts for B8 for {nb} of {pl(len(s['A4']['kernels']), 'kernel', 'kernels')}")
    ce = a7_files(s).get('A7-core-events.txt')
    parts.append('the counter codes for Part C are listed under A7' if ce and ce[1].get('pmu_list') else f'{ID.lower()} for the counter codes of Part C (A7)')
    return sv + 'For the next steps: ' + ', '.join(parts[:-1]) + ', and ' + parts[-1] + '.'


def build(s, banner=None):
    c = s['counts']
    present = [x for x in s['steps_present'] if x != 'A7']
    n7 = len(a7_files(s))
    pt = points_to(s)
    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>Part A screening result</title>', f'<style>{CSS}</style></head><body>']
    if banner:
        o.append(f'<p class="banner">{e(banner)}</p>')
    o.append('<h1>Part A: screening of the two open questions of the new C kernels</h1>')
    o.append(f'<p class="take"><b>Short version.</b> {short_version(s)}</p>')
    o.append('<p>The two questions come from the benchmark run of 2026-11-13 [Ref1]. Q1: why one thread with an 8 MiB buffer behaves differently from the other buffer sizes. '
             'Q2: why the old read kernel has a higher total than the new one when 120 threads run, and why the write kernels give several separate totals.</p>')
    t = f"<p>Result folders: {', '.join(f'<code>{e(f)}</code>' for f in s['folders'])} [Ref4]. "
    t += f"The page is built from {pl(c['blocks_used'], 'process', 'processes')} of the steps {', '.join(present) if present else 'none'}" + (f", and from the {pl(n7, 'file', 'files')} of step A7. " if n7 else '. ')
    t += ('Every process block of the folders is used. ' if not c['blocks_not_used'] else f"{pl(c['blocks_not_used'], 'process block is', 'process blocks are')} not used. ")
    t += (f"No data: {', '.join(s['steps_missing'])}." if s['steps_missing'] else 'No step is missing.')
    o.append(t + '</p>')
    o.append('<h2 id="words">Words used here</h2><ul>' + ''.join(f'<li><b>{k}</b>: {v}</li>' for k, v in WORDS) + '</ul>')
    o.append('<h2 id="points">What each step points to</h2>')
    o.append('<p>The two middle columns are quoted from the plan [Ref1]. The last column is built from the data of this run. '
             'Three results set later work: the order of B7 and B8 (row A2), the thread counts of B8 (row A4), and the counter codes of Part C (row A7).</p>')
    o.append('<div class="tw"><table class="pt"><tr><th>Step</th><th>Looks at (quoted from the plan)</th><th>What the result points to (quoted from the plan)</th><th>This run</th></tr>')
    for st_ in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7'):
        o.append(f"<tr><td>{st_}</td><td>{e(LOOKS[st_])}</td><td>{e(PLAN[st_])}</td><td>{e(pt[st_])}</td></tr>")
    o.append('</table></div>')
    o += [sec_load(s), sec_blocks(s), sec_q(s), sec_passes(s), sec_a12(s), sec_a3(s), sec_a4(s), sec_a5(s), sec_a6(s), sec_a7(s)]
    o.append('<h2 id="limits">Limits of this page</h2><ul>'
             f'<li>{ID}: the difference between two copies of one loop. Part A has no such control. So no difference on this page is compared with it. Steps B7 and B10 measure it [Ref1].</li>'
             '<li>An old kernel and an asm kernel come from two programs (<code>bw_old</code> and <code>bw_new</code>) [Ref2].</li>'
             '<li>The limits for the pattern (0.65 and 0.85) and for the level (69 and 70.5 GB/s) are provisional [Ref2].</li>'
             '<li>Thread rates are printed with 2 decimals. So the sum of 64 thread rates can differ from the exact sum by up to 0.32 GB/s (64 x 0.005 GB/s).</li>'
             f'<li>{ID}: the passes of each thread. The pass count on this page is an average over the threads. The existing programs do not print the passes of each thread [Ref2]. The changed benchmark of Part B prints the passes of each thread [Ref2].</li>'
             '<li>All threads start an interval together, and each thread stops after a whole pass. Part A does not change this timing method.</li>'
             f'<li>{ID}: the page state of the buffers and their physical pages. Part A did not record them. Step B4 gives the page state, and step D2 gives the physical pages [Ref1].</li>'
             f'<li>{ID}: load readings during a benchmark. The script reads the load only directly before each launch [Ref3].</li>'
             '<li>The chart colours were not checked with the palette checker of the chart rules. The checker needs Node.js. Node.js is not installed on the machine where this page was built. Every chart also uses position, shape or a text label.</li>'
             '</ul>')
    f7 = a7_files(s)
    def a7ref(n):
        return f"<code>{e(f7[n][0])}/{n}</code>" if n in f7 else f"<code>{n}</code> (not present in these result folders)"
    o.append('<h2 id="refs">References</h2><ul>'
             '<li>[Ref1] <code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md</code>: sections "The two questions", "What the existing files already show" (item 13), "Hypotheses", "Rules for the deciding measurements" (rules 5 and 7), "Part A" (the table with the column "What the result points to"), "Part B", and "Order and decision points" (items 2 to 4).</li>'
             '<li>[Ref2] <code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md</code>: sections "What each step runs", "Output format", "How to analyse Part A", B.3 (output rows of <code>bwx</code>), B.8 (counters), B.9 (row B8 and "Settings after B7") and B.10 (items B8 and B5).</li>'
             '<li>[Ref3] <code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/run_partA.sh</code>: the launches, the wait before each launch, the header line of each process, <code>launches.txt</code> and <code>env.txt</code>.</li>'
             f"<li>[Ref4] The result folders {', '.join(f'<code>{e(f)}</code>' for f in s['folders'])} and the file <code>partA-summary.json</code> that <code>analyze_partA.py</code> wrote from them. Every measured rate, q, count and load on this page comes from that file.</li>"
             '<li>[Ref5] <code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partA-analysis/analyze_partA.py</code>: the choices C1 to C11 at the top of the file (percentile, test for two groups, fastest half, repeated launches, label of a count, change of level, change of pattern in A4, rows of A3 used for q, check of the level limits, event names, reading of A2 for the order of the steps).</li>'
             '<li>[Ref6] <code>/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c</code>, function <code>main()</code>: the output lines of a process.</li>'
             f"<li>[Ref7] {a7ref('A7-core-events.txt')}: the type and the event codes of the core PMU.</li>"
             f"<li>[Ref8] {a7ref('A7-sve.txt')}: the default SVE vector length.</li>"
             f"<li>[Ref9] {a7ref('A7-perf-list.txt')}: the output of <code>perf list</code>.</li>"
             f"<li>[Ref10] {a7ref('A7-pmu-devices.txt')}: the names of the counter devices.</li>"
             '</ul></body></html>')
    return '\n'.join(o)


def main(argv):
    out = 'partA-result.html'; banner = None
    for opt in ('-o', '--banner'):
        if opt in argv:
            i = argv.index(opt); v = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
            if opt == '-o': out = v
            else: banner = v
    src = argv[0] if argv else 'partA-summary.json'
    s = json.load(open(src))
    open(out, 'w').write(build(s, banner))
    print(f'wrote {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
