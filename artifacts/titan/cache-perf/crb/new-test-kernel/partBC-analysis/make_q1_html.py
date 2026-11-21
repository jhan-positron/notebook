#!/usr/bin/env python3
"""make_q1_html.py --session NAME FOLDER [FOLDER...] [--session NAME FOLDER...] -o PAGE.html [--banner TEXT] [--offsets FILE]

Builds one self-contained HTML result page for question Q1 (one thread) of Parts B and C:
steps B1, B2, B3, B4, B6, C1, C2 and hypotheses H1, H2, H3a, H3b, H4, H5, H6 of plan.md.
FOLDER is a result folder of run_bwx.sh (<step>.csv, env.txt, launches.txt, stderr.txt). Folders of other steps
may be named too: only their header lines and env.txt are read, for the system load. Any number of sessions is accepted.

The decisions come from analyze_bwx.py (its parser and its functions are imported, not written again).
This file adds a DESCRIPTION without level labels (process values d and e of every process), because the
provisional level limits do not give stable processes at 8 MiB. A description is never turned into a decision.

Where a second reading of the plan and analyze_bwx.py give different words, the page prints the strict output of the script, the
other reading and its reason side by side, under "Open for the user". It chooses neither.

Every sentence that interprets data is built from computed values. Typed text is limited to: the list
"Words used here", the questions, what the plan, the handoff and the scripts ask for or do, the limits, the
captions that say how a chart is drawn, and the references. No external script, font or image. Light background only.
"""
import argparse, calendar, glob, html, math, os, re, sys, time
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
CRB = os.path.normpath(os.path.join(HERE, '..', '..'))
BWX = os.path.join(CRB, 'tmp', 'agent-scratch', 'bwx-2026-11-13')
for _d in (BWX, os.path.join(HERE, '..', 'partA-analysis'), os.path.join(HERE, '..')):
    if _d not in sys.path:
        sys.path.insert(0, _d)
import analyze_bwx as ab          # noqa: E402  parser, decision analysis
import make_partA_html as pa      # noqa: E402  style, number format, label placement
decide = ab.decide

Q1_STEPS = ['B1', 'B2', 'B3', 'B4', 'B6', 'C1', 'C2']
LOW, HIGH = decide.LOW_MAX, decide.HIGH_MIN
MIB = 1 << 20
ID = 'Insufficient data'
C0, C1c, C2c, RED = pa.C0, pa.C1, pa.C2, '#c22f2f'
TD, TE = '#1b5fb0', '#a8431a'      # text colours of the d and e values in a chart (darker than the markers, for small text)
NEAR = 0.2                         # GB/s: an interval nearer than this to a level limit is "near the limit" (a choice of this page)
INK, MUTED, GRID, BAND = pa.INK, pa.MUTED, pa.GRID, pa.BAND
e, fx, fs, pl = html.escape, pa.fx, pa.fs, pa.pl
KN = {'copy': 'new C copy', 'asmcopy': 'asm copy', 'asmcopy2': 'asm copy 2', 'asmread': 'asm read', 'oldread': 'old read at 8 MiB',
      'oldread2': 'old read 2 at 8 MiB', 'oldread@1M': 'old read at 1 MiB', 'asmcopy_c': 'asmcopy_c', 'asmcopy_c_add': 'asmcopy_c_add',
      'asmcopy_c_reg': 'asmcopy_c_reg'}
EV = [('cycles', 'cycles'), ('instructions', 'instructions'), ('l1d_refill', 'L1D refill'), ('l2d_refill', 'L2D refill'),
      ('ll_read_miss', 'LL read miss')]
CSS = pa.CSS + """
table.c td,table.c th{padding:3px 6px;font-size:12px} .nw{white-space:nowrap} td.l,th.l{text-align:left}
td.wr{white-space:normal;text-align:left;min-width:170px}
.sm{font-size:12px;color:#52514e} ul.words{columns:2;column-gap:28px;font-size:13px;padding-left:18px} ul.words li{break-inside:avoid;margin-bottom:3px}
table.hy{table-layout:fixed;width:100%} .hy td{font-size:13px} .hy td:nth-child(2){white-space:nowrap} h4{font-size:14px;margin:18px 0 4px}
.how{border:1px solid #c9c8c2;border-radius:6px;padding:4px 14px;margin-top:32px;font-size:14px} .open{background:#fdf3e7;border-left:4px solid #b85c00;padding:4px 14px;margin:10px 0}
"""
WORDS5 = ('rejected', 'not rejected', 'not observed', 'not resolved', 'not tested')


def kn(k):
    return KN.get(k, k)


def f2(v, nd=2):
    return '-' if v is None else fx(v, nd)


def s2(v, nd=2):
    return '-' if v is None else fs(v, nd)


def rng(a, b, nd=2, signed=False):
    """'a to b' with nd decimals, or one value if both print the same."""
    g = zs if signed else fx
    return g(a, nd) if g(a, nd) == g(b, nd) else f'{g(a, nd)} to {g(b, nd)}'


def zs(v, nd=2):
    """A signed number. A value that prints as zero is printed without a sign."""
    t = fs(v, nd)
    return t.lstrip('+-') if float(t) == 0 else t


def yn(b):
    return 'yes' if b else 'no'


def miss(what):
    return f'<p class="miss"><b>{ID}.</b> {what}</p>'


class Refs:
    """Reference list. ref(key) gives the text [RefN]. Only references that the page uses are printed."""

    def __init__(self):
        self.text, self.order = {}, []

    def add(self, key, text):
        self.text[key] = text

    def __call__(self, *keys):
        out = ''
        for k in keys:
            if k not in self.text:
                continue
            if k not in self.order:
                self.order.append(k)
            out += '[Ref%d]' % (self.order.index(k) + 1)
        return out

    def html(self):
        return '<ul>' + ''.join('<li>[Ref%d] %s</li>' % (i + 1, self.text[k]) for i, k in enumerate(self.order)) + '</ul>'


# ---------------------------------------------------------------- loading

LAUNCH = re.compile(r'^== (\S+) (\S+) utc (\S+) loadavg (\S+) (\S+) (\S+) (\d+)/(\d+) logins (\S+)')


def read_launches(path):
    """launches.txt -> {(csv name, tag): dict(runnable, busiest=[(pcpu, user, comm)])}."""
    out, cur = {}, None
    if not os.path.exists(path):
        return out
    for line in open(path, errors='replace'):
        m = LAUNCH.match(line)
        if m:
            cur = out.setdefault((m.group(1), m.group(2)), dict(runnable=int(m.group(7)), busiest=[], own_users=set()))
            continue
        f = line.split(None, 2)
        if cur is not None and len(f) == 3 and re.fullmatch(r'[\d.]+', f[0]):
            cur['busiest'].append((float(f[0]), f[1], f[2].strip()))
            if f[2].strip() in ('ps', 'bash'):
                cur['own_users'].add(f[1])                    # ps and bash are the run script itself
    return out


def read_env(path):
    out = dict(present=os.path.exists(path))
    if not out['present']:
        return out
    t = open(path, errors='replace').read()
    m = re.search(r'^## host=\S+ utc=(\S+) loadavg=(\S+) \S+ \S+ (\d+)/\d+ \S+ logins=(\S+) step=(\S+)', t, re.M)
    if m:
        out.update(start_utc=m.group(1), start_load1=float(m.group(2)), start_runnable=int(m.group(3)), logins=m.group(4), step=m.group(5))
    m = re.search(r'^## end utc=(\S+) loadavg=(\S+)', t, re.M)
    if m:
        out.update(end_utc=m.group(1), end_load1=float(m.group(2)))
    m = re.search(r'BWX_PMU_TYPE=(\S*) BWX_EVENTS=(\S*)', t)
    if m:
        out.update(pmu_type=m.group(1), events=m.group(2))
    return out


def scan_headers(path):
    """The header lines of the csv files of a folder -> [(step, threads)]. Cheap: no row is parsed."""
    out = []
    for f in (sorted(glob.glob(os.path.join(path, '*.csv'))) if os.path.isdir(path) else [path]):
        with open(f, errors='replace') as fh:
            for line in fh:
                if line.startswith('-- step '):
                    m = re.search(r'--threads (\d+)', line)
                    out.append((line.split()[2], int(m.group(1)) if m else 1))
    return out


def load(spec):
    """spec: [(session name, [paths])] -> {name: dict(procs, folders, other)}. Only the Q1 steps give processes."""
    sessions = {}
    for name, paths in spec:
        s = sessions.setdefault(name, dict(procs=[], folders=[], other=[]))
        for path in paths:
            path = os.path.abspath(path)
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            head = scan_headers(path)
            procs = ab.load_session(name, [path]) if any(st in Q1_STEPS for st, _ in head) else []
            mine = [p for p in procs if p.step in Q1_STEPS]
            env = read_env(os.path.join(folder, 'env.txt'))
            err = os.path.join(folder, 'stderr.txt')
            info = dict(path=folder, name=os.path.basename(folder), env=env, steps=sorted({st for st, _ in head}),
                        stderr_bytes=os.path.getsize(err) if os.path.exists(err) else None,
                        threads_max=max((n for _, n in head), default=0), launches=read_launches(os.path.join(folder, 'launches.txt')))
            if not mine:
                s['other'].append(info)
                continue
            for p in mine:
                p.folder = info
                l = info['launches'].get((os.path.basename(p.file), p.tag))
                p.launch = l
            s['procs'] += mine
            s['folders'].append(info)
    return sessions


# ---------------------------------------------------------------- computed values

def level_counts(rates):
    lv = [decide.level(r) for r in rates]
    return dict(n=len(lv), low=lv.count('low'), between=lv.count('changing'), high=lv.count('high'))


def stable_label(refs):
    """The label of a process by the rule (plan, rule 4): low or high if ALL reference intervals have it, else None."""
    lab = {decide.level(r) for r in refs}
    return lab.pop() if len(lab) == 1 and lab != {'changing'} else None


def describe_pairs(procs, first, second, aa1, aa2):
    """Description without labels. One record per process: d = median of (first - second) over its pairs, e = median of
    (aa1 - aa2). Per CPU: the values that rule 3 of the plan names, as numbers, with no decision word."""
    recs, no_pair = [], []
    for p in procs:
        kp, ap = ab.pair_values(p, first, second), ab.pair_values(p, aa1, aa2)
        if not kp or not ap:
            no_pair.append(p.tag)
            continue
        refs = [iv.rate for iv in p.ordered if iv.entry == ab.REF]
        aa_pos = [x['value'] if p.seq[x['pos']] == aa1 else -x['value'] for x in ap]      # the copy timed first minus the copy timed second
        f1 = [x['value'] for x in kp if p.seq[x['pos']] == first]
        f2_ = [x['value'] for x in kp if p.seq[x['pos']] != first]
        recs.append(dict(tag=p.tag, cpu=p.cpu, session=p.session, d=median(x['value'] for x in kp), e=median(x['value'] for x in ap),
                         n_pairs=len(kp), n_aa_pairs=len(ap), aa_single_max=max(abs(x['value']) for x in ap), aa_pos=aa_pos,
                         d_first=median(f1) if f1 else None, d_second=median(f2_) if f2_ else None,
                         second_rate=median(iv.rate for iv in p.rate_by_entry[second]), first_rate=median(iv.rate for iv in p.rate_by_entry[first]),
                         refs=refs, first_ref=refs[0] if refs else None, stable=stable_label(refs),
                         stable_without_first=stable_label(refs[1:]) if len(refs) > 1 else None))
    per_cpu = {}
    for cpu in sorted({r['cpu'] for r in recs}):
        g = [r for r in recs if r['cpu'] == cpu]
        d = [r['d'] for r in g]
        spread = max(abs(r['e']) for r in g)
        per_cpu[cpu] = dict(n=len(g), d=d, median_d=median(d), d_min=min(d), d_max=max(d), aa_spread=spread,
                            aa_single_max=max(r['aa_single_max'] for r in g), above=abs(median(d)) > spread,
                            one_sign=all(x > 0 for x in d) or all(x < 0 for x in d),
                            pct=100 * median(d) / median(r['second_rate'] for r in g),
                            d_first=median([r['d_first'] for r in g if r['d_first'] is not None] or [0]),
                            d_second=median([r['d_second'] for r in g if r['d_second'] is not None] or [0]),
                            aa_pos_n=sum(len(r['aa_pos']) for r in g), aa_pos_neg=sum(1 for r in g for v in r['aa_pos'] if v < 0),
                            aa_pos_median=median([v for r in g for v in r['aa_pos']]),
                            n_low=sum(1 for r in g if r['stable'] == 'low'), n_high=sum(1 for r in g if r['stable'] == 'high'),
                            n_not_stable=sum(1 for r in g if r['stable'] is None),
                            n_stable_without_first=sum(1 for r in g if r['stable_without_first'] is not None),
                            first_rate=median(r['first_rate'] for r in g), second_rate=median(r['second_rate'] for r in g))
    return dict(recs=recs, per_cpu=per_cpu, no_pair=no_pair, first=first, second=second, aa=(aa1, aa2))


def copy_groups(procs, step):
    """The groups of a_copy of analyze_bwx.py: B1 and C2 by size, B2 by variant, B3 by binary. -> {key: (first kernel, size, procs)}."""
    groups = {}
    for p in procs:
        if not p.complete:
            continue
        other = [x for x in p.seq if x not in (ab.REF, 'asmcopy', 'asmcopy2')]
        first = other[0] if other else None
        key = p.binary if step == 'B3' else first if step == 'B2' else ab.size_name(p.bytes)
        groups.setdefault(key, (first, p.bytes, []))[2].append(p)
    return groups


def b4_process(p):
    """One process of B4 or C1: rates, coverage, and the intervals before which a vmstat counter rose."""
    rates = [iv.rate for iv in p.ordered]
    pages = [p.page_before(iv) for iv in p.ordered]
    cov = [ab.coverage(x) for x in pages]
    ev = {'thp_collapse_alloc': [], 'pgmigrate_success': []}
    for i in range(1, len(pages)):
        for k in ev:
            a, b = pages[i - 1], pages[i]
            if a and b and a[k] is not None and b[k] is not None and b[k] > a[k]:
                ev[k].append(i)
    lv = [decide.level(r) for r in rates]
    changes, prev = [], None
    for i, l in enumerate(lv):
        if l == 'changing':
            continue
        if prev and prev[1] != l:
            changes.append((prev[0], i))
        prev = (i, l)
    info = [dict(frm=a, to=b, from_level=lv[a], to_level=lv[b], from_rate=rates[a], to_rate=rates[b], gap=b - a - 1) for a, b in changes]
    kb = [(x['kB_huge'], x['kB_total']) for x in pages if x and x['kB_total'] is not None and x['kB_huge'] is not None]
    steps = [rates[i] - rates[i - 1] for i in range(1, len(rates))]
    si = max(range(len(steps)), key=lambda i: abs(steps[i])) + 1 if steps else None
    after = rates[si:] if si else rates
    return dict(step_at=si, step_size=steps[si - 1] if si else None, after_min=min(after), after_max=max(after), tag=p.tag, cpu=p.cpu, no_thp=p.no_thp, utc=p.utc, rates=rates, median=median(rates), min=min(rates), max=max(rates),
                cov={c: cov.count(c) for c in ('full', 'partial', 'none', 'unknown')}, events=ev, levels=level_counts(rates),
                changes=changes, change_info=info, cov_list=cov, kb_total=kb[0][1] if kb else None, kb_huge_min=min((x[0] for x in kb), default=None),
                kb_huge_max=max((x[0] for x in kb), default=None), step=p.step)


def b6_by_previous(procs):
    """B6: the rate of every interval of an old read entry, grouped by CPU, entry and the entry that ran directly before it."""
    out = {}
    for p in procs:
        for iv in p.ordered:
            if iv.entry == ab.REF or iv.pos == 0:
                continue
            prev = p.seq[iv.pos - 1]
            kind = 'asm read' if prev == ab.REF else 'an old read entry'
            out.setdefault(p.cpu, {}).setdefault((iv.entry, kind), []).append(iv.rate)
    return out


def counter_facts(procs):
    """C1 and C2: facts from the C rows that the group table of analyze_bwx.py does not give."""
    n = used = read_rows = l1_lt_l2 = 0
    cpu_share = []
    for p in procs:
        for c in p.C:
            n += 1
            iv = p.raw.get((c['round'], c['pos']))
            t = next((x for x in iv.rows if x['tid'] == c['tid']), None) if iv else None
            if t is None or None in (c['running'], c['enabled'], c['cputime']) or c['running'] < c['enabled'] or c['enabled'] <= 0:
                continue
            used += 1
            cpu_share.append(c['cputime'] / (t['elapsed'] * 1e9))
            cnt = dict(zip(ab.EVENTS, c['counts'] + [None] * 5))
            if iv.entry == ab.REF and cnt['l1d_refill'] is not None and cnt['l2d_refill'] is not None:
                read_rows += 1
                l1_lt_l2 += cnt['l1d_refill'] < cnt['l2d_refill']
    return dict(rows=n, used=used, read_rows=read_rows, l1_lt_l2=l1_lt_l2,
                cpu_share_min=min(cpu_share) if cpu_share else None, cpu_share_median=median(cpu_share) if cpu_share else None)


def load_facts(sess):
    """Per step: the load readings of the launches (header lines of the csv files and launches.txt)."""
    out = {}
    for step in Q1_STEPS:
        g = [p for p in sess['procs'] if p.step == step]
        if not g:
            continue
        l1 = [p.load1 for p in g if p.load1 is not None]
        run = [int(p.runnable.split('/')[0]) for p in g if re.fullmatch(r'\d+/\d+', p.runnable or '')]
        run2 = [p.launch['runnable'] for p in g if p.launch]
        waits = [p.waited_s for p in g if p.waited_s is not None]
        logins = [int(p.logins) for p in g if (p.logins or '').isdigit()]
        busy = [b for p in g if p.launch for b in p.launch['busiest'] if b[2] not in ('ps', 'bash')]
        own = {u for p in g if p.launch for u in p.launch['own_users']}
        ts = [utc_seconds(p.folder['env'].get('start_utc')) for p in g]
        top = max(busy, default=None)
        out[step] = dict(n=len(g), first_utc=g[0].utc, last_utc=g[-1].utc, load_first=l1[0] if l1 else None, load_last=l1[-1] if l1 else None,
                         load_min=min(l1) if l1 else None, load_max=max(l1) if l1 else None, runnable_max=max(run) if run else None,
                         runnable2_max=max(run2) if run2 else None, n_launch_txt=len(run2), n_waited=sum(1 for w in waits if w > 0),
                         wait_max=max(waits) if waits else None, logins_max=max(logins) if logins else None, top=top, own_users=own, busy_all=busy,
                         t_start=min([v for v in ts if v is not None], default=None),
                         folders=sorted({p.folder['name'] for p in g}))
    return out


def utc_seconds(t):
    """'2026-11-14T01:23:15Z' -> seconds since 1970, or None."""
    try:
        return calendar.timegm(time.strptime(t, '%Y-%m-%dT%H:%M:%SZ'))
    except (TypeError, ValueError):
        return None


def b4_case_facts(P, cpu):
    """Case (a) of a CPU: where the low and the high intervals with full coverage lie, and how near the limits they are."""
    g = [p for p in P if p['cpu'] == cpu]
    lows = [r for p in g for r, c in zip(p['rates'], p['cov_list']) if c == 'full' and r < LOW]
    highs = [r for p in g for r, c in zip(p['rates'], p['cov_list']) if c == 'full' and r > HIGH]
    lo_p = [p for p in g if sum(1 for r, c in zip(p['rates'], p['cov_list']) if c == 'full' and r < LOW) >= 10]
    hi_p = [p for p in g if sum(1 for r, c in zip(p['rates'], p['cov_list']) if c == 'full' and r > HIGH) >= 10]
    near_lo = sum(1 for r in lows if r > LOW - NEAR)
    near_hi = sum(1 for r in highs if r < HIGH + NEAR)
    both = [p for p in lo_p if p in hi_p]
    return dict(cpu=cpu, n_low=len(lows), n_high=len(highs), low_min=min(lows, default=None), low_max=max(lows, default=None),
                high_min=min(highs, default=None), high_max=max(highs, default=None), near_lo=near_lo, near_hi=near_hi,
                label_dependent=bool(lows and highs) and (near_lo * 2 > len(lows) or near_hi * 2 > len(highs)),
                n_lo_procs=len(lo_p), n_hi_procs=len(hi_p), both=both)


def compute(sessions):
    """Everything the page prints. sessions: the output of load()."""
    D = dict(sessions={}, names=list(sessions))
    summary = ab.analyze({n: s['procs'] for n, s in sessions.items()})
    D['summary'] = summary
    for name, s in sessions.items():
        res = summary['sessions'].get(name, {})
        used = [p for p in s['procs'] if p.complete]
        by = lambda st: [p for p in used if p.step == st]
        x = dict(res=res, steps=[st for st in Q1_STEPS if any(p.step == st for p in s['procs'])], folders=s['folders'], other=s['other'],
                 n_procs=len(s['procs']), n_used=len(used), left_out=[(p.step, p.tag, p.status if p.status != 'ok' else '; '.join(p.problems[:2]) or 'no interval')
                                                                     for p in s['procs'] if not p.complete])
        x['missing'] = [st for st in Q1_STEPS if st not in x['steps']]
        x['load'] = load_facts(s)
        x['pairs'] = {}
        for step in ('B1', 'B2', 'B3', 'C2'):
            x['pairs'][step] = {k: dict(size=size, **describe_pairs(g, f, 'asmcopy', 'asmcopy2', 'asmcopy'))
                                for k, (f, size, g) in copy_groups(by(step), step).items()}
        b18 = [p for p in by('B1') if p.bytes == 8 * MIB]
        # the rule of a size without level, applied to 8 MiB: a description, never a decision
        x['b1_nolabel'] = ab.one_thread_group(b18, 'copy', 'asmcopy', 'asmcopy2', 'asmcopy', labelled=False)[0]['none'] if b18 else None
        x['b6'] = describe_pairs(by('B6'), 'oldread', 'oldread@1M', 'oldread2', 'oldread') if by('B6') else None
        x['b6_prev'] = b6_by_previous(by('B6'))
        x['b4'] = [b4_process(p) for p in by('B4')]
        x['c1'] = [b4_process(p) for p in by('C1')]
        x['b4_cases'] = {c: b4_case_facts(x['b4'], c) for c, v in res.get('B4', {}).get('per_cpu', {}).items() if 'a' in v['cases']}
        # reference rates per step and CPU: the reference intervals, and for B4 and C1 the intervals themselves
        refs = []
        for step in ('B1', 'B2', 'B3', 'B6', 'C2'):
            for cpu in sorted({p.cpu for p in by(step) if p.bytes == 8 * MIB}):
                g = [p for p in by(step) if p.cpu == cpu and p.bytes == 8 * MIB]
                first = [iv.rate for p in g for iv in p.ordered[:1] if iv.entry == ab.REF]
                rest = [iv.rate for p in g for iv in p.ordered[1:] if iv.entry == ab.REF]
                st = [stable_label([iv.rate for iv in p.ordered if iv.entry == ab.REF]) for p in g]
                refs.append(dict(step=step, cpu=cpu, kind='reference intervals', first=first, rest=rest, n_procs=len(g),
                                 n_stable_low=st.count('low'), n_stable_high=st.count('high'), **level_counts(first + rest),
                                 median=median(first + rest), min=min(first + rest), max=max(first + rest)))
        for step in ('B4', 'C1'):
            for cpu in sorted({p.cpu for p in by(step)}):
                for nothp in (False, True):
                    g = [p for p in by(step) if p.cpu == cpu and p.no_thp == nothp]
                    if not g:
                        continue
                    r = [iv.rate for p in g for iv in p.ordered]
                    st = [stable_label([iv.rate for iv in p.ordered]) for p in g]
                    refs.append(dict(step=step, cpu=cpu, kind='4 KiB pages asked' if nothp else '2 MiB pages asked', first=[], rest=r, n_procs=len(g),
                                     n_stable_low=st.count('low'), n_stable_high=st.count('high'), **level_counts(r), median=median(r), min=min(r), max=max(r)))
        x['refs'] = refs
        x['cfacts'] = {st: counter_facts(by(st)) for st in ('C1', 'C2') if by(st)}
        x['b1_8m_medians'] = [(p.cpu, k, p.no_thp, median(iv.rate for iv in v)) for p in by('B1') if p.bytes == 8 * MIB for k, v in p.rate_by_entry.items()]
        x['proc_medians'] = {st: [(p.cpu, k, p.no_thp, median(iv.rate for iv in v)) for p in by(st) for k, v in p.rate_by_entry.items()] for st in Q1_STEPS}
        starts = [utc_seconds(f['env'].get('start_utc')) for f in s['folders']]
        x['t_start'] = min([t for t in starts if t is not None], default=None)
        D['sessions'][name] = x
    D['hyp'] = hypotheses(D)
    return D


def rule_word(h):
    """The word of analyze_bwx.two_sessions as one of the five words of rule 11, and a note."""
    w = h['word']
    if w.startswith('not rejected (one session only'):
        return 'not rejected', 'One session only. The word "rejected" needs two sessions.'
    return w, ''


TR = {'fail': 'The bounded prediction failed', 'hold': 'The bounded prediction held', 'not observed': 'Not observed', 'not resolved': 'Not resolved'}


def cpu_list(pairs, nd=2):
    return ', '.join('CPU %s: %s' % (c, f2(a, nd)) for c, a in pairs)


def b6_position(D):
    """The position effect of B6 over all sessions, as computed values. None without B6."""
    G = [(s, x['b6'], x['b6_prev']) for s, x in D['sessions'].items() if x['b6']]
    if not G:
        return None
    pcs = [v for _, g, _ in G for v in g['per_cpu'].values()]
    one_mib = [median(bp[c][('oldread@1M', 'asm read')]) - median(bp[c][('oldread@1M', 'an old read entry')])
               for _, _, bp in G for c in bp if bp[c].get(('oldread@1M', 'asm read')) and bp[c].get(('oldread@1M', 'an old read entry'))]
    return dict(d=[v['median_d'] for v in pcs], first=[v['d_first'] for v in pcs], second=[v['d_second'] for v in pcs],
                spread=[v['aa_spread'] for v in pcs], single=[v['aa_single_max'] for v in pcs],
                second_inside=all(abs(v['d_second']) < v['aa_spread'] for v in pcs),
                first_outside=all(abs(v['d_first']) > v['aa_spread'] for v in pcs),
                aa_n=sum(v['aa_pos_n'] for v in pcs), aa_neg=sum(v['aa_pos_neg'] for v in pcs), aa_med=[v['aa_pos_median'] for v in pcs], one_mib=one_mib)


def b6_caveat(D):
    """Sentences on what the resolved difference of B6 part 2 consists of. Every sentence is built from computed values."""
    q = b6_position(D)
    if not q:
        return [], False
    t = [f'The median d per CPU is {rng(min(q["d"]), max(q["d"]), signed=True)} GB/s. It is the median over pairs in two orders.',
         f'With old read at 8 MiB timed first, directly after an asm read interval, the median pair value per CPU is {rng(min(q["first"]), max(q["first"]), signed=True)} GB/s.',
         f'With old read at 8 MiB timed second, after old read at 1 MiB, it is {rng(min(q["second"]), max(q["second"]), signed=True)} GB/s.']
    if q['second_inside']:
        t.append(f'The second value is inside the A/A spread on every CPU (A/A spreads: {rng(min(q["spread"]), max(q["spread"]))} GB/s).')
    if q['aa_n']:
        t.append(f'The A/A pairs are two old read intervals at 8 MiB, one directly after the other, after an asm read interval. In {q["aa_neg"]} of {q["aa_n"]} such pairs the first interval is slower than the second '
                 f'(median per CPU: {rng(min(q["aa_med"]), max(q["aa_med"]), signed=True)} GB/s). The A/A spread is a median over both orders, so it does not show this difference.')
    if q['one_mib']:
        t.append(f'Old read at 1 MiB after asm read minus old read at 1 MiB after old read is {rng(min(q["one_mib"]), max(q["one_mib"]), signed=True)} GB/s (median per CPU).')
    effect = q['second_inside'] and q['first_outside'] and q['aa_n'] and q['aa_neg'] * 10 >= q['aa_n'] * 9
    if effect:
        t.append('So these data do not show that the rate of old read depends on the buffer size. They show that old read at 8 MiB is slower in the interval directly after an asm read interval.')
    return t, bool(effect)


def change_words(p):
    out = []
    for ch in p['change_info']:
        gap = f', with {pl(ch["gap"], "interval", "intervals")} between the limits between them' if ch['gap'] else ''
        out.append(f'Process {p["tag"]} (step {p["step"]}, CPU {p["cpu"]}) goes from {ch["from_level"]} ({fx(ch["from_rate"])} GB/s, interval {ch["frm"]}) '
                   f'to {ch["to_level"]} ({fx(ch["to_rate"])} GB/s, interval {ch["to"]}){gap}.')
    return out


def hypotheses(D):
    """One row per hypothesis (H4 has one row per level label). Each row: the word of rule 11 over all sessions, per session the
    result, the processes that the rule uses and the A/A spread, notes (description and limits), and items open for the user."""
    S, hy = D['sessions'], D['summary']['hypotheses']
    one = len(S) < 2
    rows = []

    def add(h, step, word, per=None, notes=(), open_=(), n=0):
        per = per or {}
        basis = ' '.join('Session %s: %s' % (s, v['result']) for s, v in per.items())
        rows.append(dict(h=h, step=step, word=word, per=per, notes=[t for t in notes if t], open=[t for t in open_ if t], n=n,
                         basis=(basis + ' ' + ' '.join(t for t in notes if t)).strip()))

    limits_note = lambda cpus: ('The word depends on the provisional level limits, which are not validated. '
                                + ('Stable processes exist only on CPU %s, and all of them are stable low.' % ', '.join(map(str, cpus)) if cpus else 'No process is stable at one level.'))

    # ---- H1
    h = hy.get('H1 (B6)')
    if h:
        w, note = rule_word(h)
        per = {}
        for s, x in S.items():
            if 'B6' not in x['res']:
                continue
            r = x['res']['B6']
            sz = r['size']['labels']['none']
            p1 = sorted({v['decision'] for v in r['state'].values()})
            nres = sum(1 for v in sz['per_cpu'].values() if v['decision'] == 'resolved')
            per[s] = dict(result='%s. Part 1 (low against high level): %s (stable high processes: %d). Part 2 (8 MiB against 1 MiB): %s%s, with %d of %s resolved.' % (
                TR.get(h['per_session'].get(s), h['per_session'].get(s)), ' and '.join(p1), sum(v['n_high'] for v in r['state'].values()),
                sz['decision'], ab.sign_txt(sz['sign']), nres, pl(len(sz['per_cpu']), 'CPU', 'CPUs')),
                used='%d of %d (part 2 uses every process)' % (len(x['b6']['recs']), len(x['b6']['recs'])),
                spread=cpu_list((c, v['aa_spread']) for c, v in x['b6']['per_cpu'].items()))
        cav, effect = b6_caveat(D)
        part1_none = all(v['decision'] == 'not observed' for x in S.values() if 'B6' in x['res'] for v in x['res']['B6']['state'].values())
        notes = ['The result comes from part 2 only. Part 1 is "not observed": no CPU has stable high processes.' if part1_none else ''] + cav + [note]
        open_ = []
        if effect and w == 'rejected':
            open_.append('H1. Strict output of the rule: "rejected", because part 2 is resolved in every session. A recount of the words by a second agent gives the same word and adds the limit that the difference is a position effect. No file holds that recount. '
                         'The check of this page proposes "not resolved" under the last paragraph of handoff B.10, because the pair definition does not fit the B6 data: a pair value contains the position difference. '
                         'The choice between the two words is a judgment.')
        add('H1', 'B6', w, per, notes, open_, n=sum(len(x['b6']['recs']) for x in S.values() if x['b6']))
    else:
        add('H1', 'B6', 'not tested', notes=['No process of step B6 is in the input.'])
    # ---- H2: the plan names no bounded prediction for H2 in Parts B and C, so rule 11 gives "not tested"
    per = {}
    for s, x in S.items():
        P = x['b4'] + x['c1']
        if not P:
            continue
        ch = [t for p in P for t in change_words(p)]
        nh = sum(1 for p in P if p['levels']['high'] == p['levels']['n'])
        big = sum(1 for p in P if p['step_size'] is not None and abs(p['step_size']) > 1)
        per[s] = dict(result='Description, no decision. %s between low and high inside a process, in %s of B4 and C1. %s%s high in all intervals. In %s the largest step between two neighbouring intervals is above 1 GB/s.' % (
            pl(sum(len(p['change_info']) for p in P), 'change', 'changes'), pl(len(P), 'process', 'processes'), ''.join(t + ' ' for t in ch), pl(nh, 'process was', 'processes were'), pl(big, 'process', 'processes')),
            used='none (no rule)', spread='no A/A pair')
    if per:
        add('H2', 'B4, C1', 'not tested', per, ['The plan gives H2 no bounded prediction in Parts B and C. So no rule gives a word, and the word of rule 11 is "not tested". '
                                                'The second half of H2 (the high level can stay for the next process) has no test here, because each process allocates a new buffer.'],
            n=sum(len(x['b4']) + len(x['c1']) for x in S.values()))
    else:
        add('H2', 'B4, C1', 'not tested', notes=['No process of steps B4 and C1 is in the input.'])
    # ---- H3a
    h = hy.get('H3a (B4)')
    if h:
        w, note = rule_word(h)
        per, notes, dep = {}, [], {}
        for s, x in S.items():
            pc = x['res'].get('B4', {}).get('per_cpu', {})
            if not pc:
                continue
            flag = h['per_session'].get(s)
            casec = [c for c, v in pc.items() if v['cases']]
            all_dep = bool(casec) and all(x['b4_cases'].get(c, {}).get('label_dependent') for c in casec)
            t = ('The rule finds a case, and the case depends on the provisional limits.' if flag == 'fail' and all_dep else
                 'The bounded prediction failed.' if flag == 'fail' else 'Not observed: neither case occurred on a CPU.')
            for c, v in pc.items():
                if not v['cases']:
                    continue
                iv = v['intervals']
                t += ' CPU %s: case (%s).' % (c, ') and ('.join(v['cases']))
                if 'a' in v['cases']:
                    t += ' %d low and %d high intervals with full coverage.' % (iv['low']['full'], iv['high']['full'])
                if 'b' in v['cases']:
                    t += ' %d low and %d high intervals with no huge page.' % (iv['low']['none'], iv['high']['none'])
                f = x['b4_cases'].get(c)
                if f:
                    if f['label_dependent']:
                        if f['near_lo'] * 2 > f['n_low']:
                            t += ' %d of the %d low intervals lie less than %g GB/s below the limit of %g GB/s.' % (f['near_lo'], f['n_low'], NEAR, LOW)
                        if f['near_hi'] * 2 > f['n_high']:
                            t += ' %d of the %d high intervals lie less than %g GB/s above the limit of %g GB/s.' % (f['near_hi'], f['n_high'], NEAR, HIGH)
                    notes.append('Session %s, CPU %s: %s' % (s, c, 'one process has at least 10 low and at least 10 high intervals with full coverage.' if len(f['both']) == 1 else '%d processes have at least 10 low and at least 10 high intervals with full coverage.' % len(f['both']) if f['both'] else 'the low and the high intervals are in different processes. No process has both.'))
            dep[s] = [c for c, f in x['b4_cases'].items() if f['label_dependent']], [c for c, v in pc.items() if v['cases']]
            per[s] = dict(result=t, used='%d of %d' % (len(x['b4']), len(x['b4'])), spread='no A/A pair')
        # low intervals with full coverage on one CPU in every session: the first half of the prediction
        lowfull = {s: {c: v['intervals']['low']['full'] for c, v in x['res'].get('B4', {}).get('per_cpu', {}).items()} for s, x in S.items() if x['res'].get('B4')}
        if len(lowfull) > 1:
            for c in sorted(set.intersection(*[set(v) for v in lowfull.values()])):
                if all(v[c] >= 10 for v in lowfull.values()):
                    notes.append('CPU %s has low intervals with full coverage in every session (%s). H3a predicts that every low interval has less than full coverage. The rule of the handoff counts this only together with high intervals.' % (
                        c, ', '.join('%s: %d' % (s, v[c]) for s, v in lowfull.items())))
        open_ = []
        other = h.get('word_without_the_same_cpu_condition')
        if other and other != w:
            where = ', '.join('session %s: CPU %s' % (s, ' and '.join(map(str, c)) or 'none') for s, c in h['cpus_with_a_case'].items())
            open_.append(f'H3a. Strict output of the analysis script: "{w}". The handoff gives "rejected" only if one CPU shows a case in both sessions (handoff B.10, deviation A13). No CPU does ({where}). '
                         f'Second reading: "{other}". The analysis script prints this word as the word without the same-CPU condition. Reason: step B4 of the plan has no same-CPU condition ("H3a is rejected if low and high intervals are both observed with full coverage"), '
                         'and by rule 11 the bounded prediction failed in both sessions. Which wording applies is a judgment.')
        only_dep = [s for s, (d, allc) in dep.items() if allc and set(d) == set(allc)]
        if only_dep:
            open_.append('H3a and the limits. In session %s every case depends on the provisional limits (see the row above and section B4). If such a case is not counted, that session has no case, and the word is "not rejected" under both readings.' % ' and '.join(only_dep))
        add('H3a', 'B4', w, per, notes + [note], open_, n=sum(len(x['b4']) for x in S.values()))
    else:
        add('H3a', 'B4', 'not tested', notes=['No process of step B4 is in the input.'])
    add('H3b', 'D2 (not run)', 'not tested', notes=['Part D was not run. No file has the physical addresses of the buffer pages.'])
    # ---- H4
    any_h4 = False
    for lab in ('low', 'high'):
        h = hy.get('H4 (B1, 8 MiB, label %s)' % lab)
        if not h:
            continue
        any_h4 = True
        w, note = rule_word(h)
        per, cpus_st = {}, set()
        for s, x in S.items():
            g = x['pairs']['B1'].get('8M')
            r = x['res'].get('B1', {}).get('groups', {}).get('8M', {}).get('labels', {}).get(lab)
            if not g or not r:
                continue
            n = sum(v['n_' + lab] for v in g['per_cpu'].values())
            cpus_st |= {c for c, v in g['per_cpu'].items() if v['n_low'] + v['n_high']}
            t = '%s. Stable %s processes: %s.' % (TR.get(h['per_session'].get(s), h['per_session'].get(s)), lab, ', '.join('CPU %s: %d' % (c, v['n_' + lab]) for c, v in g['per_cpu'].items()))
            alone = [(c, v) for c, v in r['per_cpu'].items() if v['decision'] != 'not observed']
            if alone and r['decision'] == 'not observed':
                t += ' %s alone: %s. The rule needs 2 CPUs with 3 stable processes.' % (
                    ', '.join('CPU %s' % c for c, _ in alone), ', '.join(v['decision'] + ab.sign_txt(v['sign']) for _, v in alone))
            sp = ', '.join('CPU %s: %s over the %s (%s over all %d processes)' % (c, f2(v['aa_spread']), pl(v['n_processes'], 'stable %s process' % lab, 'stable %s processes' % lab),
                                                                                 f2(g['per_cpu'][c]['aa_spread']), g['per_cpu'][c]['n'])
                           for c, v in r['per_cpu'].items() if v['aa_spread'] is not None)
            per[s] = dict(result=t, used='%d of %d' % (n, len(g['recs'])), spread=sp or 'no stable %s process' % lab)
        notes = []
        if lab == 'low':
            notes.append(limits_note(sorted(cpus_st)))
            recs = [r for x in S.values() for r in x['pairs']['B1'].get('8M', {}).get('recs', [])]
            if recs:
                notes.append('Description without labels, no decision: d is below 0 in %d of %s.' % (sum(1 for r in recs if r['d'] < 0), pl(len(recs), 'process', 'processes')))
            nl = ['%s "%s%s" (%d of %s resolved)' % (s, x['b1_nolabel']['decision'], ab.sign_txt(x['b1_nolabel']['sign']), sum(1 for v in x['b1_nolabel']['per_cpu'].values() if v['decision'] == 'resolved'),
                                                    pl(len(x['b1_nolabel']['per_cpu']), 'CPU', 'CPUs')) for s, x in S.items() if x['b1_nolabel']]
            if nl:
                notes.append('Description, no decision: the rule for a size without level, applied to all processes at 8 MiB, gives ' + ', '.join(nl) + '.')
            others = {}
            for s, x in S.items():
                for k, gr in x['res'].get('B1', {}).get('groups', {}).items():
                    if k != '8M' and 'none' in gr['labels']:
                        others.setdefault(k, {})[s] = gr['labels']['none']['decision'] + ab.sign_txt(gr['labels']['none']['sign'])
            if others:
                notes.append('Other sizes, by the rule: ' + '. '.join('%s MiB: %s' % (k.rstrip('M'), ', '.join('%s %s' % (s, v) for s, v in d.items())) for k, d in sorted(others.items(), key=lambda kv: ab.parse_size(kv[0])))
                             + '. H4 predicts 8 MiB only.')
        add('H4, %s intervals' % lab, 'B1 at 8 MiB', w, per, notes + [note], n=sum(int(v['used'].split()[0]) for v in per.values()))
    if not any_h4:
        add('H4', 'B1 at 8 MiB', 'not tested', notes=['No process of step B1 at 8 MiB is in the input.'])
    # ---- H5, H6
    for name, key, step, grp in (('H5', 'H5 (B2, asmcopy_c, label low)', 'B2', 'asmcopy_c'), ('H6', 'H6 (B3)', 'B3', None)):
        h = hy.get(key)
        if not h:
            add(name, step, 'not tested', notes=['No process of step %s is in the input.' % step])
            continue
        w, note = rule_word(h)
        per, cpus_st, no_b1 = {}, set(), []
        for s, x in S.items():
            gs = [(k, g) for k, g in x['pairs'][step].items() if grp in (None, k)]
            if not gs:
                continue
            n = sum(len(g['recs']) for _, g in gs)
            nst = sum(1 for _, g in gs for r in g['recs'] if r['stable'])
            cpus_st |= {c for _, g in gs for c, v in g['per_cpu'].items() if v['n_low'] + v['n_high']}
            sps = {}
            for k, _ in gs:
                for lab, r in x['res'].get(step, {}).get('groups', {}).get(k, {}).get('labels', {}).items():
                    for c, v in r['per_cpu'].items():
                        if v['aa_spread'] is not None:
                            sps.setdefault(c, []).append(v['aa_spread'])
            b1l = x['res'].get('B1', {}).get('groups', {}).get('8M', {}).get('labels', {})
            if not any(v['decision'] == 'resolved' for v in b1l.values()):
                no_b1.append(s)
            per[s] = dict(result='%s. %d of %s %s stable at one level.' % (TR.get(h['per_session'].get(s), h['per_session'].get(s)), nst, pl(n, 'process', 'processes'), 'is' if nst == 1 else 'are'),
                          used='%d of %d' % (nst, n),
                          spread=', '.join('CPU %s: %s over the stable processes' % (c, rng(min(v), max(v))) for c, v in sorted(sps.items())) or 'no stable process')
        notes = [limits_note(sorted(cpus_st))]
        if no_b1:
            notes.append('Step B1 has no resolved difference at 8 MiB by the rule in %s %s. The plan runs step %s only after a resolved difference in B1. The step was run so that the data exist if the limits are revised.' % ('session' if len(no_b1) == 1 else 'sessions', ' and '.join(no_b1), step))
        if grp:
            recs = [r for x in S.values() for r in x['pairs'][step].get(grp, {}).get('recs', [])]
            if recs:
                notes.append('Description without labels, no decision: d is below 0 in %d of %s.' % (sum(1 for r in recs if r['d'] < 0), pl(len(recs), 'process', 'processes')))
        add(name, step, w, per, notes + [note], n=sum(int(v['used'].split()[0]) for v in per.values()))
    for r in rows:
        assert r['word'] in WORDS5, r
        if one:
            assert r['word'] != 'rejected'
    return rows


# ---------------------------------------------------------------- charts

def nice_ticks(lo, hi, n=7):
    span = hi - lo
    step = next((s for s in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50) if span / s <= n), 100)
    t, v = [], (int(lo / step) - 1) * step
    while v <= hi + 1e-9:
        if v >= lo - 1e-9:
            t.append(round(v, 6))
        v += step
    return t


def axis_floor(v):
    """The start of a rate axis: the next lower multiple of 0.5 GB/s, so that the first tick is at the left edge."""
    return math.floor(v * 2) / 2


def strip(rows, xmin, xmax, xlabel, aria, L=250, R=250, groups=None, right_head=None, zero=False):
    """rows: [(name, [(value, title, kind)], right_label)]. kind 0: blue dot. kind 1: orange diamond.
    The band between the two provisional limits is shaded if it lies inside the axis. zero: a dashed line at 0."""
    W, rh, top = 900, 24, 34
    H = top + len(rows) * rh + 46
    PW = W - L - R
    X = lambda v: L + (min(max(v, xmin), xmax) - xmin) / (xmax - xmin) * PW
    o = pa.svg_open(W, H, aria)
    band = xmin < LOW and xmax > HIGH and not zero
    if band:
        o.append(f'<rect x="{fx(X(LOW), 1)}" y="{top-6}" width="{fx(X(HIGH)-X(LOW), 1)}" height="{len(rows)*rh+6}" fill="{BAND}"/>')
        o.append(f'<text x="{fx(X(LOW)-4, 1)}" y="{top-12}" text-anchor="end" class="ax">low: below {LOW:g}</text>')
        o.append(f'<text x="{fx(X(HIGH)+4, 1)}" y="{top-12}" class="ax">high: above {HIGH:g}</text>')
    for t in nice_ticks(xmin, xmax):
        o.append(f'<line x1="{fx(X(t), 1)}" y1="{top-6}" x2="{fx(X(t), 1)}" y2="{H-46}" stroke="{GRID}"/>')
        o.append(f'<text x="{fx(X(t), 1)}" y="{H-30}" text-anchor="middle" class="ax">{t:g}</text>')
    if band:
        for v in (LOW, HIGH):
            o.append(f'<line x1="{fx(X(v), 1)}" y1="{top-6}" x2="{fx(X(v), 1)}" y2="{H-46}" stroke="{MUTED}" stroke-dasharray="4 3"/>')
    if zero:
        o.append(f'<line x1="{fx(X(0), 1)}" y1="{top-6}" x2="{fx(X(0), 1)}" y2="{H-46}" stroke="{MUTED}" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">{e(xlabel)}</text>')
    if right_head:
        o.append(f'<text x="{L+PW+10}" y="{top-12}" class="ax">{e(right_head)}</text>')
    for i, (name, pts, right) in enumerate(rows):
        y = top + i * rh + rh / 2
        o.append(f'<text x="{L-10}" y="{fx(y+4, 1)}" text-anchor="end" class="lab">{e(name)}</text>')
        heavy = groups and i + 1 in groups
        o.append(f'<line x1="{0 if heavy else L}" y1="{fx(y+rh/2, 1)}" x2="{W if heavy else L+PW}" y2="{fx(y+rh/2, 1)}" stroke="{MUTED if heavy else GRID}"/>')
        for kind_now in (1, 0):                                   # diamonds first, so that a dot is never hidden by a diamond
            for j, (v, title, kind) in enumerate(pts):
                if kind != kind_now:
                    continue
                yy = y + ((j * 7) % 5 - 2) * 2.2
                if kind:
                    o.append(f'<path d="M{fx(X(v), 1)},{fx(yy-5, 1)} l5,5 l-5,5 l-5,-5 Z" fill="{C1c}" stroke="#fff" stroke-width="1"><title>{e(title)}</title></path>')
                else:
                    o.append(f'<circle cx="{fx(X(v), 1)}" cy="{fx(yy, 1)}" r="3.5" fill="{C0}" fill-opacity="0.6" stroke="#fff" stroke-width="0.8"><title>{e(title)}</title></circle>')
        o.append(f'<text x="{L+PW+10}" y="{fx(y+4, 1)}" class="val">{e(right)}</text>')
    o.append('</svg>')
    return '\n'.join(o)


def short_tag(tag):
    m = re.search(r'cpu(\d+)-p(\d+)', tag)
    return 'CPU %s, process %s' % (m.group(1), m.group(2)) if m else tag


def dumbbell(items, aria):
    """items: [(session name, desc)]. One row per process: d (blue dot) and e (orange diamond), joined by a line.
    The value of d is printed in blue in a fixed column left of the plot, the value of e in orange in a fixed column right of it.
    One block per CPU and session: the band from minus to plus the A/A spread of that block, and the median d as a faint line."""
    W, L, R, rh, gap, top = 900, 196, 256, 16, 8, 26
    blocks = [(s, c, [r for r in d['recs'] if r['cpu'] == c], d['per_cpu'][c]) for c in sorted({c for _, d in items for c in d['per_cpu']})
              for s, d in items if c in d['per_cpu']]
    many = len(items) > 1
    xmin, xmax = axis_of([d for _, d in items])
    nrows = sum(len(b[2]) for b in blocks)
    H = top + nrows * rh + len(blocks) * gap + 44
    PW = W - L - R
    X = lambda v: L + 8 + (v - xmin) / (xmax - xmin) * (PW - 16)
    o = pa.svg_open(W, H, aria)
    ybot = H - 44
    for t in nice_ticks(xmin, xmax, 9):
        o.append(f'<line x1="{fx(X(t), 1)}" y1="{top}" x2="{fx(X(t), 1)}" y2="{ybot}" stroke="{GRID}"/>')
        o.append(f'<text x="{fx(X(t), 1)}" y="{ybot+14}" text-anchor="middle" class="ax">{t:g}</text>')
    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">difference of the rates of two neighbouring intervals, GB/s (one value per process: the median of its pairs)</text>')
    o.append(f'<text x="{L-6}" y="{top-10}" text-anchor="end" class="lab" style="fill:{TD};font-weight:600">d, GB/s</text>')
    o.append(f'<text x="{L+PW+6}" y="{top-10}" class="lab" style="fill:{TE};font-weight:600">e, GB/s</text>')
    y = top
    for bi, (s, c, g, pc) in enumerate(blocks):
        y0, y1 = y + 2, y + len(g) * rh + 2
        o.append(f'<rect x="{fx(X(-pc["aa_spread"]), 1)}" y="{y0}" width="{fx(max(X(pc["aa_spread"])-X(-pc["aa_spread"]), 1), 1)}" height="{y1-y0}" fill="#f6d9c9"><title>A/A spread of CPU {c}: plus and minus {fx(pc["aa_spread"])} GB/s</title></rect>')
        o.append(f'<line x1="{fx(X(0), 1)}" y1="{y0}" x2="{fx(X(0), 1)}" y2="{y1}" stroke="{MUTED}" stroke-dasharray="3 3"/>')
        ym = (y0 + y1) / 2
        o.append(f'<line x1="{fx(X(pc["median_d"]), 1)}" y1="{y0}" x2="{fx(X(pc["median_d"]), 1)}" y2="{y1}" stroke="{C0}" stroke-width="1.5" stroke-opacity="0.4"/>')
        name = (f'{s}, ' if many else '') + f'CPU {c}'
        o.append(f'<text x="{L+PW+52}" y="{fx(ym-3, 1)}" class="val">{e(name)}: median d {fs(pc["median_d"])} GB/s</text>')
        o.append(f'<text x="{L+PW+52}" y="{fx(ym+11, 1)}" class="val">A/A spread {fx(pc["aa_spread"])} GB/s (shaded)</text>')
        for i, r in enumerate(g):
            yy = y + 2 + i * rh + rh / 2
            m = re.search(r'p(\d+)$', r['tag'])
            o.append(f'<text x="{L-50}" y="{fx(yy+4, 1)}" text-anchor="end" class="ax">{e(name)}, process {m.group(1) if m else e(r["tag"])}</text>')
            xd, xe = X(r['d']), X(r['e'])
            o.append(f'<line x1="{fx(xd, 1)}" y1="{fx(yy, 1)}" x2="{fx(xe, 1)}" y2="{fx(yy, 1)}" stroke="{MUTED}" stroke-width="1"/>')
            o.append(pa.marker(xe, yy, 'diamond', C1c, f'{r["tag"]}: e {fs(r["e"], 3)} GB/s', r=3))
            o.append(pa.marker(xd, yy, 'dot', C0, f'{r["tag"]}: d {fs(r["d"], 3)} GB/s', r=4))        # the dot is drawn last, above the diamond
            o.append(f'<text x="{L-6}" y="{fx(yy+4, 1)}" text-anchor="end" class="val" style="fill:{TD}">{fs(r["d"])}</text>')
            o.append(f'<text x="{L+PW+6}" y="{fx(yy+4, 1)}" class="val" style="fill:{TE}">{fs(r["e"])}</text>')
        y = y1 + gap - 2
        last_of_cpu = bi + 1 == len(blocks) or blocks[bi + 1][1] != c
        o.append(f'<line x1="0" y1="{fx(y-gap/2+1, 1)}" x2="{W}" y2="{fx(y-gap/2+1, 1)}" stroke="{MUTED if last_of_cpu and many else GRID}"/>')
    o.append('</svg>')
    return '\n'.join(o)


def legend_pairs(dname, ename):
    return (f'<p><span class="lg"><i style="background:{C0}"></i>d = {e(dname)}</span>'
            f'<span class="lg"><i style="background:{C1c};border-radius:0;transform:rotate(45deg)"></i>e = {e(ename)} (two copies of one loop)</span>'
            f'<span class="lg"><i style="background:#f6d9c9;border-radius:0"></i>from minus to plus the A/A spread</span></p>')


def seq_chart(procs, ymin, ymax, aria):
    """One panel per process: rate against interval number. Red lines: a vmstat counter rose before that interval.
    -> (svg text, [(process tag, interval) of every value label that found no free place])."""
    W, L, R, ph, gap, top = 900, 60, 190, 84, 38, 26
    H = top + len(procs) * (ph + gap)
    nmax = max(max(len(p['rates']) for p in procs), 2)
    X = lambda i: L + i / (nmax - 1) * (W - L - R)
    o = pa.svg_open(W, H, aria)
    left_out = []
    for pi, p in enumerate(procs):
        y0 = top + pi * (ph + gap)
        Y = lambda v: y0 + ph - (v - ymin) / (ymax - ymin) * ph
        o.append(f'<rect x="{L}" y="{y0}" width="{W-L-R}" height="{ph}" fill="none" stroke="{GRID}"/>')
        o.append(f'<rect x="{L}" y="{fx(Y(HIGH), 1)}" width="{W-L-R}" height="{fx(Y(LOW)-Y(HIGH), 1)}" fill="{BAND}"/>')
        asked = '4 KiB pages asked (--no-thp)' if p['no_thp'] else '2 MiB pages asked'
        cov = 'no page reading' if p['kb_total'] is None else (
            f"kB_huge {p['kb_huge_min']} of {p['kb_total']} kB before every interval" if p['kb_huge_min'] == p['kb_huge_max']
            else f"kB_huge {p['kb_huge_min']} to {p['kb_huge_max']} of {p['kb_total']} kB")
        o.append(f'<text x="{L}" y="{y0-7}" class="lab">CPU {p["cpu"]}, process {e(p["tag"])}, started {e(p["utc"])} UTC. {asked}. {cov}.</text>')
        for v in (HIGH, LOW):
            o.append(f'<line x1="{L}" y1="{fx(Y(v), 1)}" x2="{W-R}" y2="{fx(Y(v), 1)}" stroke="{MUTED}" stroke-dasharray="4 3"/>')
        boxes = []
        for v in (ymin, LOW, HIGH, ymax):
            o.append(f'<text x="{L-6}" y="{fx(Y(v)+4, 1)}" text-anchor="end" class="ax">{fx(v, 1)}</text>')
            boxes.append((L - 36, Y(v) - 6, L - 6, Y(v) + 6))
        for i in range(0, nmax, 25):
            o.append(f'<text x="{fx(X(i), 1)}" y="{y0+ph+13}" text-anchor="middle" class="ax">{i}</text>')
        for k, col in (('thp_collapse_alloc', RED), ('pgmigrate_success', '#7a3fb5')):
            for i in p['events'][k]:
                o.append(f'<line x1="{fx(X(i), 1)}" y1="{y0}" x2="{fx(X(i), 1)}" y2="{y0+ph}" stroke="{col}" stroke-width="1.5"><title>{k} rose before interval {i}</title></line>')
        r = p['rates']
        o.append(f'<polyline points="{" ".join(f"{fx(X(i), 1)},{fx(Y(v), 1)}" for i, v in enumerate(r))}" fill="none" stroke="{C0}" stroke-width="1.5"/>')
        segs = [(X(i), Y(r[i]), X(i + 1), Y(r[i + 1])) for i in range(len(r) - 1)]
        hl = [Y(HIGH), Y(LOW)]
        want = list(dict.fromkeys([r.index(min(r)), r.index(max(r)), 0, len(r) - 1]))
        for i in want:
            txt = fx(r[i], 2)
            o.append(f'<circle cx="{fx(X(i), 1)}" cy="{fx(Y(r[i]), 1)}" r="3" fill="{C0}" stroke="#fff" stroke-width="1"><title>interval {i}: {txt} GB/s</title></circle>')
            got = pa.place_label(X(i), Y(r[i]), 6.4 * len(txt) + 2, i == 0, i == len(r) - 1, r[i] == min(r), y0, y0 + ph, boxes, segs, hl, (L, W - R))
            if not got:
                left_out.append((p['tag'], i, r[i]))
                continue
            anchor, tx, base = got
            o.append(f'<text x="{fx(tx, 1)}" y="{fx(base, 1)}" text-anchor="{anchor}" class="val">{txt}</text>')
        nev = len(p['events']['thp_collapse_alloc']) + len(p['events']['pgmigrate_success'])
        lv = p['levels']
        for j, t in enumerate((f'median {fx(p["median"])} GB/s', f'{fx(p["min"])} to {fx(p["max"])} GB/s',
                               f'low {lv["low"]}, between {lv["between"]}, high {lv["high"]}', f'counter increases: {nev}')):
            o.append(f'<text x="{W-R+8}" y="{y0+24+j*14}" class="val">{t}</text>')
        o.append(f'<text x="14" y="{y0+ph/2}" text-anchor="middle" class="ax" transform="rotate(-90 14 {y0+ph/2})">GB/s</text>')
    o.append(f'<text x="{L+(W-L-R)/2}" y="{H-8}" text-anchor="middle" class="ax">interval number in the process (each interval is at least 0.3 s)</text>')
    o.append('</svg>')
    return '\n'.join(o), left_out


def counter_chart(groups, aria):
    """Small multiples: one panel per value, one row per group (CPU, kernel, level). The rate panel prints the number only.
    Every other panel has its own axis from 0 to the value printed under it."""
    cols = [('median_thread_GBps', 'rate, GB/s', 2)] + [('median_%s_per_line' % k, n + ' per line', 3) for k, n in EV]
    W, L, rh, top = 900, 236, 19, 40
    pw = (W - L - 8) / len(cols)
    H = top + len(groups) * rh + 30
    o = pa.svg_open(W, H, aria)
    for ci, (key, name, nd) in enumerate(cols):
        x0 = L + ci * pw
        vals = [g[key] for g in groups if g[key] is not None]
        vmax = max(vals + [1e-12])
        words = name.split(' per line')
        o.append(f'<text x="{fx(x0+4, 1)}" y="14" class="lab">{e(words[0])}</text>')
        o.append(f'<text x="{fx(x0+4, 1)}" y="28" class="ax">{"per 64 B line" if len(words) > 1 else "median"}</text>')
        if ci:
            o.append(f'<line x1="{fx(x0+4, 1)}" y1="{top-4}" x2="{fx(x0+4, 1)}" y2="{H-26}" stroke="{GRID}"/>')
            o.append(f'<text x="{fx(x0+4, 1)}" y="{H-10}" class="ax">{"all values are 0" if max(vals + [0]) == 0 else "axis: 0 to " + small(vmax, nd, chart=True)}</text>')
        for gi, g in enumerate(groups):
            y = top + gi * rh + rh / 2
            if ci == 0:
                o.append(f'<text x="{L-8}" y="{fx(y+4, 1)}" text-anchor="end" class="lab">{e(g["_name"])}</text>')
                heavy = g.get('_last')
                o.append(f'<line x1="{0 if heavy else L}" y1="{fx(y+rh/2, 1)}" x2="{W}" y2="{fx(y+rh/2, 1)}" stroke="{MUTED if heavy else GRID}"/>')
            v = g[key]
            if v is None:
                o.append(f'<text x="{fx(x0+10, 1)}" y="{fx(y+4, 1)}" class="ax">not supported</text>')
                continue
            if ci == 0:
                o.append(f'<text x="{fx(x0+4, 1)}" y="{fx(y+4, 1)}" class="val">{fx(v, nd)}</text>')
                continue
            xv = x0 + 4 + v / vmax * (pw - 62)
            o.append(f'<line x1="{fx(x0+4, 1)}" y1="{fx(y, 1)}" x2="{fx(xv, 1)}" y2="{fx(y, 1)}" stroke="{C0}" stroke-width="1.5"/>')
            o.append(f'<circle cx="{fx(xv, 1)}" cy="{fx(y, 1)}" r="3.5" fill="{C0}" stroke="#fff" stroke-width="1"/>')
            o.append(f'<text x="{fx(xv+6, 1)}" y="{fx(y+4, 1)}" class="val">{small(v, nd, chart=True)}</text>')
    o.append('</svg>')
    return '\n'.join(o)


def small(v, nd=3, chart=False):
    """A count per line with nd decimals. A value below 0.000001 is printed as 'below 1 per million' (lines).
    Another value that would print as 0 keeps two significant digits."""
    if v is None:
        return '-'
    if v == 0:
        return '0'
    if abs(v) < 1e-6:
        return 'below 10^-6' if chart else 'below 1 per million'
    if abs(v) < 0.5 * 10 ** -nd:
        digits = 1 - math.floor(math.log10(abs(v)))
        return '%.*f' % (digits, v)
    return fx(v, nd)


# ---------------------------------------------------------------- sections

def many(D):
    return len(D['names']) > 1


def fref(R, D, name, step):
    return R(*[('folder', name, f) for f in D['sessions'][name]['load'].get(step, {}).get('folders', [])])


def frefs(R, D, *steps):
    return ''.join(fref(R, D, n, st) for n in D['names'] for st in steps)


def sec_hyp(D, R):
    o = ['<h2 id="hyp">Result for each hypothesis</h2>']
    one = not many(D)
    o.append('<p>The last column gives one of the five words of rule 11 of the plan ' + R('plan') + '. The word comes from the decision functions of the analysis script, with the provisional level limits unchanged ' + R('analyze', 'decide') + '. '
             'Each session has its own column with the result of that session, the processes that the rule uses, and the A/A spread.</p>')
    if one:
        o.append('<p class="take">This page has one session. Rule 11 of the plan needs the failed prediction in two sessions for the word "rejected" ' + R('plan') + '. '
                 'So no row of this table can say "rejected". A row can say that the bounded prediction failed in this session.</p>')
    o.append('<div class="tw"><table class="pt hy"><tr><th style="width:12%">Hypothesis</th><th style="width:9%">Step</th>' + ''.join(f'<th>Session {e(n)}: result</th>' for n in D['names'])
             + f'<th style="width:11%">Word over {"both sessions" if len(D["names"]) == 2 else "all sessions" if many(D) else "the session"} (rule 11)</th></tr>')
    for r in D['hyp']:
        cells = ''
        for n in D['names']:
            v = r['per'].get(n)
            cells += ('<td>-</td>' if not v else f"<td>{e(v['result'])}<br><span class=\"sm\">Processes used by the rule (of all processes): {e(v['used'])}. A/A spread, GB/s: {e(v['spread'])}.</span></td>")
        o.append(f"<tr><td>{e(r['h'])}</td><td>{e(r['step'])}</td>{cells}<td><b>{e(r['word'])}</b></td></tr>")
    o.append('</table></div>')
    notes = [r for r in D['hyp'] if r['notes']]
    if notes:
        o.append('<p><b>Notes to the rows.</b> A note is a limit of the word or a description. It changes no word.</p><ul>'
                 + ''.join(f"<li><b>{e(r['h'])}.</b> {e(' '.join(r['notes']))}</li>" for r in notes) + '</ul>')
    opens = [t for r in D['hyp'] for t in r['open']]
    o.append('<div class="open"><p><b>Open for the user.</b></p><ul>' + ''.join(f'<li>{e(t)} ' + R('plan', 'handoff', 'devscripts') + '</li>' for t in opens)
             + '<li>The level limits. Every word that needs a label uses the provisional limits of ' f'{LOW:g}' ' and ' f'{HIGH:g}' ' GB/s. The section on the reference rate describes how they fit the data. This page does not change them.</li></ul></div>')
    o.append('<p class="cap">The hypotheses are quoted in "Words used here". H4 has one row per level label, because the rule decides each label alone ' + R('handoff') + '.</p>')
    return '\n'.join(o)


def sec_load(D, R):
    o = ['<h2 id="load">System load of every step</h2>']
    rows, takes, extra = [], [], []
    any_high = False
    for name in D['names']:
        x = D['sessions'][name]
        L = x['load']
        if not L:
            o.append(miss(f'The system load{" of session " + e(name) if many(D) else ""}: no process of a step of this page is in the input.'))
            continue
        run = max(max(v['runnable_max'] or 0, v['runnable2_max'] or 0) for v in L.values())
        waited = sum(v['n_waited'] for v in L.values())
        n = sum(v['n'] for v in L.values())
        logins = max((v['logins_max'] for v in L.values() if v['logins_max'] is not None), default=None)
        refs = R(*[('folder', name, f['name']) for f in x['folders']])
        takes.append(f'{"Session " + e(name) + ". " if many(D) else ""}Before each of the {pl(n, "launch", "launches")} the script read at most {pl(run, "runnable task", "runnable tasks")}. '
                     f'{waited} of the {pl(n, "launch", "launches")} waited for an idle system (at most 2 runnable tasks). '
                     + ('' if logins is None else 'No user was logged in at any launch. ' if logins == 0 else f'At most {pl(logins, "user was", "users were")} logged in at a launch. ') + refs)
        hi = max(L.items(), key=lambda kv: kv[1]['load_max'] or 0)
        if hi[1]['load_max'] is not None and hi[1]['load_max'] > 2:
            any_high = True
            v = hi[1]
            before = [f for f in x['other'] + x['folders'] if f['env'].get('end_utc') and f['threads_max'] > 1]
            start = next((f['env'].get('start_utc') for f in x['folders'] if hi[0] in f['steps']), None)
            prev = max((f for f in before if start and f['env']['end_utc'] <= start), key=lambda f: f['env']['end_utc'], default=None)
            extra.append(f'<p>{"Session " + e(name) + ". " if many(D) else ""}The 1-minute load average was high at some launches. Its highest value was {fx(v["load_max"])} tasks, in step {hi[0]}. '
                         f'In that step it was {fx(v["load_first"])} tasks at the first launch and {fx(v["load_last"])} tasks at the last launch. '
                         + (f'The step before, in folder <code>{e(prev["name"])}</code>, ran {prev["threads_max"]} threads of our own benchmark and ended at {e(prev["env"]["end_utc"])} {R(("folder", name, prev["name"]))}. '
                            f'Step {hi[0]} started at {e(start)}. ' if prev else
                            f'Hypothesis: the high values are left from a process with 120 threads of our own benchmark that ended before the launch. The <code>env.txt</code> of the step before would show it. That folder is not in the input of this page. ')
                         + '</p>')
        for st, v in sorted(L.items(), key=lambda kv: (kv[1]['t_start'] is None, kv[1]['t_start'] or 0, Q1_STEPS.index(kv[0]))):
            top = f"{fx(v['top'][0], 1)} %: {e(v['top'][2])} ({e(v['top'][1])})" if v['top'] else f'{ID}: no launches.txt entry'
            rows.append((f"<td>{e(name)}</td>" if many(D) else '') + f"<td>{st}</td><td>{v['n']}</td><td class=\"nw\">{e(v['first_utc'])} to {e(v['last_utc'])}</td>"
                        f"<td class=\"nw\">{f2(v['load_min'])} to {f2(v['load_max'])}</td><td>{v['runnable_max']} / {'-' if v['runnable2_max'] is None else v['runnable2_max']}</td>"
                        f"<td>{v['n_waited']}</td><td>{'-' if v['wait_max'] is None else '%g' % v['wait_max']}</td><td>{'-' if v['logins_max'] is None else v['logins_max']}</td><td class=\"wr\">{top}</td>")
            t = v['top']
            if t and t[0] > 5:
                own = t[1] in v['own_users']
                oth = [b[0] for b in v['busy_all'] if b != t]
                s = (f'<p>{"Session " + e(name) + ", step " if many(D) else "Step "}{st}. The busiest other process is <code>{e(t[2])}</code> of the account <code>{e(t[1])}</code>, with {fx(t[0], 1)} % of one CPU at one launch. '
                     + (f'At the other launches of the step no other process is above {fx(max(oth), 1)} %. ' if oth else ''))
                if own:
                    s += ('The run script runs under the same account, so this is not another user. The tool <code>ps</code> gives the CPU time of a process divided by the time since its start. '
                          'Hypothesis: this process started seconds before the launch, with the login of our own visit. The start time of the process (<code>ps -o lstart</code>) would confirm or reject it.')
                else:
                    s += f'{ID}: what this process did. Its command line and its CPU time during the step would show it.'
                extra.append(s + '</p>')
        if x['left_out']:
            extra.append('<p>Processes that the analysis left out: ' + ' '.join(f'{st} {e(tag)} ({e(why)}).' for st, tag, why in x['left_out']) + '</p>')
        err = [f for f in x['folders'] if f['stderr_bytes']]
        if err:
            extra.append('<p>The file <code>stderr.txt</code> is not empty in: ' + ', '.join(f"<code>{e(f['name'])}</code>" for f in err) + '.</p>')
    if takes:
        o.append('<p class="take">' + '<br>'.join(takes) + '</p>')
    if rows:
        o.append('<div class="tw"><table class="c">' + '<tr>' + ('<th>Session</th>' if many(D) else '') + '<th>Step</th><th>Launches</th><th>UTC, first to last launch</th><th>1-minute load (tasks), lowest to highest</th>'
                 '<th>Runnable tasks, highest: header line / launches.txt</th><th>Launches that waited</th><th>Longest wait, s</th>'
                 '<th>Logged-in users, highest</th><th class="l">Busiest other process (% of one CPU)</th></tr>' + ''.join(f'<tr>{r}</tr>' for r in rows) + '</table></div>')
        o.append('<p class="cap">The rows are in the order in which the steps ran. The script reads the runnable tasks twice before a launch: first for <code>launches.txt</code>, then for the header line of the process. '
                 'So the two values can differ. One of the runnable tasks is the script that reads the value. "Busiest other process" leaves out <code>ps</code> and <code>bash</code>, which are the script itself ' + R('runscript') + '. '
                 'A name that starts with <code>kworker</code> or <code>rcu</code> is a thread of the Linux kernel.</p>')
    o += extra
    if any_high:
        o.append('<p>The 1-minute load average is an average over about the last minute. So it still counts the threads of a process that has ended. '
                 'It is therefore no evidence of another user. The evidence of an otherwise idle system is the three readings above: the runnable tasks, the waits and the logged-in users.</p>')
    elif rows:
        o.append('<p>No launch on this page had a 1-minute load average above 2 tasks.</p>')
    o.append(f'<p>{ID}: load readings during an interval. The script reads the load only directly before each launch ' + R('runscript') + '. A reading of the runnable tasks of each account during an interval would give it.</p>')
    return '\n'.join(o)


COPY_STEPS = ('B1', 'B2', 'B3', 'C2')


def sec_refs(D, R):
    o = ['<h2 id="level">The reference rate and the two level limits</h2>']
    o.append('<p>Rule 5 of the plan labels an interval at 8 MiB by its neighbouring reference intervals of asm read: low below ' f'{LOW:g}' ' GB/s, high above ' f'{HIGH:g}' ' GB/s ' + R('plan') + '. '
             'The handoff then uses a process only if all its reference intervals have one label ' + R('handoff') + '. The plan calls the two limits provisional. It asks to check them against the new data before they are used ' + R('plan') + '. '
             'This section is that check. The limits were not changed.</p>')
    o.append(f'<p><span class="lg"><i style="background:{C0}"></i>one interval</span><span class="lg"><i style="background:{C1c};border-radius:0;transform:rotate(45deg)"></i>first reference interval of a process</span>'
             f'<span class="lg"><i style="background:{BAND};border-radius:0"></i>between the two limits: no label</span></p>')
    allv = [v for x in D['sessions'].values() for r in x['refs'] for v in r['first'] + r['rest']]
    takes, tables, desc = [], [], []
    thin = False
    for name in D['names']:
        x = D['sessions'][name]
        rows = x['refs']
        if not rows:
            o.append(miss(f'The reference rates{" of session " + e(name) if many(D) else ""}: no process at 8 MiB is in the input.'))
            continue
        xmin, xmax = axis_floor(min(min(allv), LOW) - 0.2), max(max(allv), HIGH) + 0.4
        chart, groups = [], set()
        for i, r in enumerate(rows):
            pts = [(v, f'{fx(v)} GB/s', 0) for v in r['rest'][::max(1, len(r['rest']) // 120)]] + [(v, f'first reference interval of a process: {fx(v)} GB/s', 1) for v in r['first']]
            chart.append((f"{r['step']} CPU {r['cpu']}, {r['kind']}", pts, f"{fx(r['median'])} GB/s. {r['low']} / {r['between']} / {r['high']}"))
            if i + 1 < len(rows) and rows[i + 1]['step'] != r['step']:
                groups.add(i + 1)
        if many(D):
            o.append(f'<h3>Session {e(name)}</h3>')
        o.append(strip(chart, xmin, xmax, f'rate of asm read at 8 MiB, GB/s (the axis starts at {xmin:g} GB/s, not at 0)', 'Distribution of the reference rate per step and CPU', groups=groups, right_head='median. low / between / high'))
        thin = thin or max(len(r['rest']) for r in rows) > 120
        between = [r for r in rows if r['between'] * 2 > r['n']]
        rr = [r for r in rows if r['kind'] == 'reference intervals']
        t = f'{"Session " + e(name) + ". " if many(D) else ""}In {len(between)} of the {pl(len(rows), "row", "rows")}, more than half of the intervals lie between the two limits, where the rule gives no label. '
        if rr:
            nst = sum(r['n_stable_low'] + r['n_stable_high'] for r in rr)
            steps = list(dict.fromkeys(r['step'] for r in rr))
            t += (f'Over the {pl(len(rr), "row", "rows")} of {", ".join(steps)} (the steps with reference intervals), the median reference rate of a row is between {fx(min(r["median"] for r in rr))} and {fx(max(r["median"] for r in rr))} GB/s. '
                  f'Over all {pl(len(rows), "row", "rows")} it is between {fx(min(r["median"] for r in rows))} and {fx(max(r["median"] for r in rows))} GB/s. '
                  f'{nst} of the {pl(sum(r["n_procs"] for r in rr), "process", "processes")} with reference intervals {"is" if nst == 1 else "are"} stable at one level. ')
        takes.append(t + fref(R, D, name, 'B1') + fref(R, D, name, 'B4'))
        tb = ['<div class="tw"><table class="c"><tr><th>Step</th><th>CPU</th><th class="l">Intervals</th><th>Count</th><th>Lowest, GB/s</th><th>Median, GB/s</th><th>Highest, GB/s</th><th>Low</th><th>Between</th><th>High</th>'
              '<th>Processes</th><th>Stable low</th><th>Stable high</th><th>Not stable</th></tr>']
        for r in rows:
            tb.append(f"<tr><td>{r['step']}</td><td>{r['cpu']}</td><td class=\"l nw\">{e(r['kind'])}</td><td>{r['n']}</td><td>{fx(r['min'])}</td><td>{fx(r['median'])}</td><td>{fx(r['max'])}</td>"
                      f"<td>{r['low']}</td><td>{r['between']}</td><td>{r['high']}</td><td>{r['n_procs']}</td><td>{r['n_stable_low']}</td><td>{r['n_stable_high']}</td>"
                      f"<td>{r['n_procs']-r['n_stable_low']-r['n_stable_high']}</td></tr>")
        tables.append(f'<details><summary>Counts of every row{", session " + e(name) if many(D) else ""}</summary>' + ''.join(tb) + '</table></div></details>')
        # how the limits miss: rows of the copy steps whose median lies between the limits, and the first reference interval
        mid = [r for r in rr if r['step'] in COPY_STEPS and LOW <= r['median'] <= HIGH]
        d = f'{"Session " + e(name) + ". " if many(D) else ""}'
        if mid:
            sh = [100 * r['between'] / r['n'] for r in mid]
            d += (f'In {len(mid)} of the {pl(sum(1 for r in rr if r["step"] in COPY_STEPS), "row", "rows")} of the copy steps ({", ".join(s for s in COPY_STEPS if any(r["step"] == s for r in rr))}) the median reference rate lies between the two limits. '
                  f'These rows are on {cpus_words(sorted({r["cpu"] for r in mid}))}. Their medians are {rng(min(r["median"] for r in mid), max(r["median"] for r in mid))} GB/s. '
                  f'That is {rng(HIGH - max(r["median"] for r in mid), HIGH - min(r["median"] for r in mid))} GB/s below the high limit. In these rows {rng(min(sh), max(sh), 0)} % of the intervals get no label. ')
        allrecs = [r2 for st in COPY_STEPS for g in x['pairs'][st].values() if g['size'] == 8 * MIB for r2 in g['recs']]
        firsts = [r2 for r2 in allrecs if len(r2['refs']) > 2]
        if firsts:
            nd = sum(1 for r2 in firsts if decide.level(r2['first_ref']) != decide.level(median(r2['refs'][1:])))
            sw = sum(1 for r2 in allrecs if r2['stable_without_first'])
            d += (f'In {nd} of {pl(len(firsts), "copy process", "copy processes")} at 8 MiB the first reference interval has another label than the median of the later ones. '
                  f'Without the first reference interval, {sw} of the {len(allrecs)} processes would have all reference intervals at one level. ')
        desc.append(d)
    if takes:
        o.append('<p class="take">' + '<br>'.join(takes) + '</p>')
        o.append('<p class="cap">Each row has the reference intervals of all processes of one step on one CPU. For B4 and C1 each interval is its own reference, so the row has all intervals. '
                 + ('A row with more than 120 intervals shows every n-th interval, and the numbers at the right count all intervals. ' if thin else '')
                 + 'The dots are spread vertically so that they do not hide each other.</p>')
        o += tables
    o.append('<p><b>Open decision for the user.</b> The limits ' f'{LOW:g}' ' and ' f'{HIGH:g}' ' GB/s come from the sweep of 2026-11-02 ' + R('plan') + '. '
             + ('The list gives how they fit the reference rates of this page (description, no decision).</p><ul>' + ''.join(f'<li>{t}</li>' for t in desc if t) + '</ul><p>' if any(desc) else '')
             + 'The first reference interval is the first timed interval of a new process, and all later ones follow a copy interval. The rule does not leave it out, and this page does not either. '
             'This page does not decide whether the limits are revised, or to which values. Until the user decides, every decision that needs a label uses the limits as they are. '
             'Each step below also gives a description without labels, marked "description, no decision".</p>')
    return '\n'.join(o)


def cpus_words(cpus):
    c = [str(x) for x in cpus]
    return 'CPU ' + c[0] if len(c) == 1 else 'CPUs ' + ', '.join(c[:-1]) + ' and ' + c[-1]


def sec_howto(D, R):
    return ('<div class="how"><p><b>How to read the charts and tables of B1, B2, B3 and B6.</b></p><ul>'
            '<li>One row of a chart is one process. The blue dot is d and the orange diamond is e. The blue number at the left is d. The orange number at the right is e. Both are in GB/s.</li>'
            '<li>The shaded band goes from minus to plus the A/A spread of one CPU in one session. The faint blue line marks the median d of that CPU. Each chart has its own axis.</li>'
            '<li>In a table, the A/A spread is the largest absolute e of the CPU. "Largest single A/A pair" is the largest absolute difference of one pair of the two copies, before the median of the process is taken.</li>'
            '<li>"Order" gives the median pair value with the first loop of "d = X minus Y" timed first, and with it timed second.</li>'
            '<li>All columns before the column "Rule" describe all processes of the CPU and decide nothing. The column "Rule" gives the strict result of the decision rule: the number of processes that the rule uses, and its word. '
            'A CPU needs 3 processes for a word. A result over the CPUs needs 2 such CPUs with one sign ' + R('handoff') + '.</li>'
            '<li>At 8 MiB the rule uses only stable processes. The labels behind "stable" come from the provisional limits, which are not validated. So a word in the column "Rule" at 8 MiB is not a validated decision.</li>'
            '</ul></div>')


def stable_sentence(D):
    """Where stable processes exist, over all steps and sessions. Built from the reference rows."""
    rows = [(n, r) for n, x in D['sessions'].items() for r in x['refs'] if r['kind'] == 'reference intervals']
    if not rows:
        return ''
    hi = sum(r['n_stable_high'] for _, r in rows)
    lo = sorted({r['cpu'] for _, r in rows if r['n_stable_low']})
    t = ('No CPU has a stable high process in any step with reference intervals. ' if hi == 0 else f'{pl(hi, "process is", "processes are")} stable high. ')
    if lo:
        main = max(lo, key=lambda c: sum(r['n_stable_low'] for _, r in rows if r['cpu'] == c))
        rest = [(n, r) for n, r in rows if r['n_stable_low'] and r['cpu'] != main]
        t += f'Stable low processes exist on CPU {main}' + (
            ' only.' if not rest else ', and ' + ', '.join(f'{r["n_stable_low"]} on CPU {r["cpu"]} in step {r["step"]}{" of session " + n if many(D) else ""}' for n, r in rest) + '.')
    else:
        t += 'No process is stable low.'
    return t


def pair_table(items, labelled):
    """items: [(session, desc, labels of the rule)]. Per session and CPU: the description (all processes) and the strict result of the rule."""
    multi = len(items) > 1
    lab_list = ('low', 'high') if labelled else ('none',)
    if labelled and not any(v['n_high'] for _, d, _ in items for v in d['per_cpu'].values()):
        lab_list = ('low',)
    head = {'none': 'Rule: processes, word', 'low': 'Rule, stable low (labels not validated): processes, word', 'high': 'Rule, stable high (labels not validated): processes, word'}
    o = ['<div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if multi else '') + '<th>CPU</th><th>Processes</th><th>Median d, GB/s</th><th>d, lowest to highest, GB/s</th><th>Median d, % of the second loop</th>'
         '<th>A/A spread, GB/s</th><th>Largest single A/A pair, GB/s</th><th>|Median d| above the A/A spread</th><th>All d have one sign</th>'
         '<th>Order: first loop timed first / second, GB/s</th>' + ''.join(f'<th>{head[lab]}</th>' for lab in lab_list) + '</tr>']
    words = []
    for s, desc, labels in items:
        for c, v in desc['per_cpu'].items():
            t = ('<tr>' + (f'<td>{e(s)}</td>' if multi else '') + f"<td>{c}</td><td>{v['n']}</td><td>{fs(v['median_d'])}</td><td class=\"nw\">{fs(v['d_min'])} to {fs(v['d_max'])}</td><td>{fs(v['pct'])}</td><td>{fx(v['aa_spread'])}</td>"
                 f"<td>{fx(v['aa_single_max'])}</td><td>{yn(v['above'])}</td><td>{yn(v['one_sign'])}</td><td class=\"nw\">{fs(v['d_first'])} / {fs(v['d_second'])}</td>")
            for lab in lab_list:
                pc = (labels or {}).get(lab, {}).get('per_cpu', {}).get(c)
                t += f"<td class=\"nw\">{pc['n_processes']}: {e(pc['decision'] + ab.sign_txt(pc['sign']))}</td>" if pc else '<td>-</td>'
            o.append(t + '</tr>')
        for lab in lab_list:
            r = (labels or {}).get(lab)
            if r:
                words.append(f'{"Session " + e(s) + ", " if multi else ""}{"all CPUs together" if lab == "none" else "label " + lab + ", all CPUs together"}: <b>{e(r["decision"] + ab.sign_txt(r["sign"]))}</b>.')
    o.append('</table></div>')
    if words:
        o.append('<p class="cap">Result of the rule. ' + ' '.join(words) + '</p>')
    return '\n'.join(o)


def desc_takeaway(desc):
    pc = desc['per_cpu']
    recs = desc['recs']
    neg = sum(1 for r in recs if r['d'] < 0)
    pos = sum(1 for r in recs if r['d'] > 0)
    meds = [v['median_d'] for v in pc.values()]
    n_above = sum(1 for v in pc.values() if v['above'])
    n_both = sum(1 for v in pc.values() if v['above'] and v['one_sign'])
    side = f'below 0 in {neg}' if neg >= pos else f'above 0 in {pos}'
    t = (f'd is {side} of {pl(len(recs), "process", "processes")}. The median d of a CPU is between {fs(min(meds))} and {fs(max(meds))} GB/s. '
         f'On {n_above} of {pl(len(pc), "CPU", "CPUs")} the absolute value of the median d is larger than the A/A spread.')
    if n_above:
        t += ' On those CPUs all d have one sign.' if n_both == n_above else f' On {n_both} of those CPUs all d have one sign.'
    return t + order_words(desc)


def order_words(desc):
    """Sentences if the order of the two loops inside a pair changes the pair value by more than the A/A spread."""
    pc = desc['per_cpu']
    big = [abs(v['d_first'] - v['d_second']) for v in pc.values() if abs(v['d_first'] - v['d_second']) > v['aa_spread']]
    if not big:
        return ''
    return (f' The order of the two loops inside a pair changes the pair value on {len(big)} of {pl(len(pc), "CPU", "CPUs")}. There the two orders differ by more than the A/A spread. '
            f'The largest difference is {fx(max(big))} GB/s.')


def axis_of(descs):
    v = [r[k] for d in descs for r in d['recs'] for k in ('d', 'e')] + [s * v2['aa_spread'] for d in descs for v2 in d['per_cpu'].values() for s in (1, -1)]
    return min(v + [0]) - 0.1, max(v + [0]) + 0.1


def group_block(D, R, step, key, title, dname, ename, labelled, res_of, heading='h3', marked=True):
    """One compared group (a size, a variant or a build) over all sessions: chart, takeaway, table. key None: step B6."""
    if key is None:
        items = [(n, D['sessions'][n]['b6'], D['sessions'][n]['res']['B6']['size']['labels']) for n in D['names'] if D['sessions'][n]['b6']]
    else:
        items = [(n, D['sessions'][n]['pairs'][step][key], res_of(D['sessions'][n]).get(key, {}).get('labels')) for n in D['names'] if key in D['sessions'][n]['pairs'][step]]
    if not items:
        return ''
    o = [f'<{heading}>{e(title)}' + (' (the chart is a description, no decision)' if marked else '') + f'</{heading}>']
    o.append(legend_pairs(dname, ename))
    o.append(dumbbell([(n, d) for n, d, _ in items], f'{step} {key}: d and e per process'))
    o.append('<p class="take">' + ('Description, no decision. ' if marked else '')
             + '<br>'.join((f'Session {e(n)}: ' if many(D) else '') + desc_takeaway(d) + ' ' + fref(R, D, n, step) for n, d, _ in items) + '</p>')
    o.append(pair_table(items, labelled))
    return '\n'.join(o)


def proc_details(D, step, groups_of, title):
    o = [f'<details><summary>{title}</summary><div class="tw"><table><tr>' + ('<th>Session</th>' if many(D) else '') + '<th>Group</th><th>Process</th><th>CPU</th><th>d, GB/s</th><th>e, GB/s</th><th>Pairs</th>'
         '<th>Reference rate, lowest to highest, GB/s</th><th>Stable label by the rule</th></tr>']
    for n in D['names']:
        for k, g in groups_of(D['sessions'][n]):
            for r in g['recs']:
                lab = (r['stable'] or 'not stable') if g.get('size', 8 * MIB) == 8 * MIB else 'no level defined at this size'
                o.append('<tr>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{e(k)}</td><td>{e(r['tag'])}</td><td>{r['cpu']}</td><td>{fs(r['d'], 3)}</td><td>{fs(r['e'], 3)}</td><td>{r['n_pairs']}</td>"
                         f"<td>{fx(min(r['refs']))} to {fx(max(r['refs']))}</td><td>{lab}</td></tr>")
    o.append('</table></div></details>')
    return '\n'.join(o)


def sec_b1(D, R):
    o = ['<h2 id="b1">B1: new C copy against asm copy inside one process</h2>']
    o.append('<p>Each process times new C copy, asm copy and a second copy of asm copy (asm copy 2) on the same two buffers, with reference intervals of asm read between the pairs ' + R('handoff') + '. '
             'The loop of new C copy starts at 36 modulo 64 and the loop of asm copy at 52 modulo 64, as in the benchmark of 2026-11-13 ' + R('offsets') + '. '
             'The plan asks whether the difference of 2026-11-13 exists inside one process. In that run new C copy was 2.91 % below asm copy at 8 MiB, with the two loops in different processes ' + R('plan') + '.</p>')
    have = [n for n in D['names'] if D['sessions'][n]['pairs']['B1']]
    for n in D['names']:
        if n not in have:
            o.append(miss(f'Step B1{" of session " + e(n) if many(D) else ""}: no process is in the input. A run of step B1 would give it.'))
    if not have:
        return '\n'.join(o)
    res_of = lambda x: x['res'].get('B1', {}).get('groups', {})
    sizes = sorted({(g['size'], k) for n in have for k, g in D['sessions'][n]['pairs']['B1'].items()})
    dn, en = 'new C copy minus asm copy', 'asm copy 2 minus asm copy'
    if any(s == 8 * MIB for s, _ in sizes):
        o.append(group_block(D, R, 'B1', '8M', '8 MiB', dn, en, True, res_of))
        recs = [r for n in have for r in D['sessions'][n]['pairs']['B1'].get('8M', {}).get('recs', [])]
        n_st = sum(1 for r in recs if r['stable'])
        o.append(f'<p>At 8 MiB the rule uses only a process whose reference intervals are all low or all high. The rule can use {n_st} of the {pl(len(recs), "process", "processes")}. '
                 'The other processes are in the chart and in the description columns, and in no decision. ' + stable_sentence(D) + '</p>')
    rest = [(s, k) for s, k in sizes if s != 8 * MIB]
    if rest:
        o.append('<h3>4, 16 and 32 MiB: sizes without a level</h3>' if [s // MIB for s, _ in rest] == [4, 16, 32] else '<h3>The other sizes: no level is defined</h3>')
        o.append('<div class="tw"><table class="c"><tr><th>Size</th>' + ('<th>Session</th>' if many(D) else '') + '<th>Processes</th><th>Median d per CPU, GB/s</th><th>Median d per CPU, % of asm copy</th><th>Largest A/A spread of a CPU, GB/s</th><th>Rule: word over the CPUs</th></tr>')
        for s, k in rest:
            for n in have:
                g = D['sessions'][n]['pairs']['B1'].get(k)
                if not g:
                    continue
                pc = g['per_cpu'].values()
                r = res_of(D['sessions'][n]).get(k, {}).get('labels', {}).get('none')
                o.append(f'<tr><td>{s // MIB} MiB</td>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{len(g['recs'])}</td><td class=\"nw\">{rng(min(v['median_d'] for v in pc), max(v['median_d'] for v in pc), signed=True)}</td>"
                         f"<td class=\"nw\">{rng(min(v['pct'] for v in pc), max(v['pct'] for v in pc), signed=True)}</td><td>{fx(max(v['aa_spread'] for v in pc))}</td><td class=\"l\">{e(r['decision'] + ab.sign_txt(r['sign'])) if r else '-'}</td></tr>")
        o.append('</table></div><p class="cap">At these sizes the rule uses every process. ' + frefs(R, D, 'B1') + '</p>')
        o.append('<details><summary>Charts and tables per CPU for these sizes</summary>' + ''.join(group_block(D, R, 'B1', k, f'{s // MIB} MiB', dn, en, False, res_of, heading='h4', marked=False) for s, k in rest) + '</details>')
    o.append(proc_details(D, 'B1', lambda x: sorted(x['pairs']['B1'].items(), key=lambda kv: kv[1]['size']), 'Values of every process of B1'))
    return '\n'.join(o)


def sec_variants(D, R, step, title, intro, dname_of, gname):
    o = [f'<h2 id="{step.lower()}">{title}</h2>', intro]
    have = [n for n in D['names'] if D['sessions'][n]['pairs'][step]]
    for n in D['names']:
        if n not in have:
            o.append(miss(f'Step {step}{" of session " + e(n) if many(D) else ""}: no process is in the input. A run of step {step} would give it.'))
    if not have:
        return '\n'.join(o)
    keys = sorted({k for n in have for k in D['sessions'][n]['pairs'][step]})
    res_of = lambda x: x['res'].get(step, {}).get('groups', {})
    # summary chart: every process value of every group, with B1 at 8 MiB as the first block
    blocks = [('B1: new C copy', lambda x: x['pairs']['B1'].get('8M'))] + [(gname(k), (lambda k: lambda x: x['pairs'][step].get(k))(k)) for k in keys]
    rows, groups, descs = [], set(), []
    for bname, get in blocks:
        cpus = sorted({c for n in have for g in [get(D['sessions'][n])] if g for c in g['per_cpu']})
        for c in cpus:
            for n in have:
                g = get(D['sessions'][n])
                if not g or c not in g['per_cpu']:
                    continue
                descs.append(g)
                v = g['per_cpu'][c]
                pts = [(r['e'], f'{r["tag"]}: e {fs(r["e"], 3)} GB/s', 1) for r in g['recs'] if r['cpu'] == c] + [(r['d'], f'{r["tag"]}: d {fs(r["d"], 3)} GB/s', 0) for r in g['recs'] if r['cpu'] == c]
                rows.append((f'{bname}, CPU {c}' + (f', {n}' if many(D) else ''), pts, f'{fs(v["median_d"])} GB/s, A/A {fx(v["aa_spread"])} GB/s'))
        groups.add(len(rows))
    xmin, xmax = axis_of(descs)
    o.append(f'<h3>All process values of {step}, next to B1 at 8 MiB (description, no decision)</h3>')
    o.append(f'<p><span class="lg"><i style="background:{C0}"></i>d of one process: the named loop minus asm copy</span>'
             f'<span class="lg"><i style="background:{C1c};border-radius:0;transform:rotate(45deg)"></i>e of one process: asm copy 2 minus asm copy</span></p>')
    o.append(strip(rows, xmin, xmax, 'difference of the rates of two neighbouring intervals, GB/s (one value per process)', f'{step}: d and e of every process per group, CPU and session',
                   L=250, R=220, groups=groups, right_head='median d, A/A spread', zero=True))
    # one table row per group and session
    o.append('<div class="tw"><table class="c"><tr><th>Group</th>' + ('<th>Session</th>' if many(D) else '') + '<th>Processes with d below 0</th><th>Median d per CPU, GB/s</th>'
             '<th>CPUs with |median d| above the A/A spread and one sign</th><th>Stable low processes (labels not validated)</th><th>Rule, label low: word over the CPUs</th></tr>')
    for k in keys:
        for n in have:
            g = D['sessions'][n]['pairs'][step].get(k)
            if not g:
                continue
            pc = g['per_cpu'].values()
            r = res_of(D['sessions'][n]).get(k, {}).get('labels', {}).get('low')
            o.append(f'<tr><td>{e(gname(k))}</td>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{sum(1 for q in g['recs'] if q['d'] < 0)} of {len(g['recs'])}</td>"
                     f"<td class=\"nw\">{rng(min(v['median_d'] for v in pc), max(v['median_d'] for v in pc), signed=True)}</td><td>{sum(1 for v in pc if v['above'] and v['one_sign'])} of {len(g['per_cpu'])}</td>"
                     f"<td>{sum(v['n_low'] for v in pc)} of {len(g['recs'])}</td><td class=\"l\">{e(r['decision'] + ab.sign_txt(r['sign'])) if r else '-'}</td></tr>")
    o.append('</table></div>')
    o.append('<p class="cap">One dot or diamond is one process. The dashed line is 0. The first block repeats B1 at 8 MiB for comparison. All columns before "Stable low processes" are a description. ' + frefs(R, D, step, 'B1') + '</p>')
    # comparison with B1 at 8 MiB, description
    n_all = n_big = 0
    tb = ['<div class="tw"><table><tr><th>Group</th>' + ('<th>Session</th>' if many(D) else '') + '<th>CPU</th><th>Median d of B1, GB/s</th><th>Median d of the group, GB/s</th><th>B1 minus group, GB/s</th>'
          '<th>Sum of the two A/A spreads, GB/s</th><th>Difference above that sum</th><th>The d of B1 and of the group do not overlap</th></tr>']
    strict = set()
    for n in have:
        x = D['sessions'][n]
        base = x['pairs']['B1'].get('8M')
        for k in keys:
            g = x['pairs'][step].get(k)
            if not base or not g:
                continue
            for c, v in g['per_cpu'].items():
                b = base['per_cpu'].get(c)
                if not b:
                    continue
                ch, sp = b['median_d'] - v['median_d'], b['aa_spread'] + v['aa_spread']
                sep = max(b['d']) < min(v['d']) or min(b['d']) > max(v['d'])
                n_all += 1
                n_big += abs(ch) > sp and sep
                tb.append(f'<tr><td>{e(gname(k))}</td>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{c}</td><td>{fs(b['median_d'])}</td><td>{fs(v['median_d'])}</td><td>{fs(ch)}</td><td>{fx(sp)}</td><td>{yn(abs(ch) > sp)}</td><td>{yn(sep)}</td></tr>")
        chg = x['res'].get(step, {}).get('change_against_B1')
        if chg:
            strict |= {v['decision'] for b in chg.values() for v in b.values()}
    if n_all:
        o.append(f'<p class="take">Description, no decision. In {n_big} of {pl(n_all, "row", "rows")} (one row per group, CPU and session) the median d differs from B1 at 8 MiB by more than the sum of the two A/A spreads, with no overlap of the process values.'
                 + (' Strict result of the rule for the change against B1, per build, label and CPU: ' + ', '.join(f'"{w}"' for w in sorted(strict)) + '. The rule compares only stable processes with one label, and needs 3 of them on a CPU in B1 and in the build ' + R('devscripts') + '.' if strict else '') + '</p>')
        o.append(f'<details><summary>Median d of {step} next to B1 at 8 MiB, per CPU</summary>' + ''.join(tb) + '</table></div></details>')
    o.append(f'<details><summary>Chart and table per CPU for each group of {step}</summary>'
             + ''.join(group_block(D, R, step, k, gname(k), dname_of(k), 'asm copy 2 minus asm copy', True, res_of, heading='h4') for k in keys) + '</details>')
    o.append(proc_details(D, step, lambda x: sorted(x['pairs'][step].items()), f'Values of every process of {step}'))
    return '\n'.join(o)


def proc_table(D, key):
    """B4 or C1: one row per process, all sessions."""
    o = ['<div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if many(D) else '') + '<th>Process</th><th>CPU</th><th>Pages asked</th><th>Started, UTC</th><th>Median, GB/s</th><th>Lowest to highest, GB/s</th><th>Intervals low / between / high</th>'
         '<th>Intervals with full / partial / no coverage</th><th>Counter increases, collapse / migrate</th><th>Changes low to high or back</th><th>Largest step between neighbours, GB/s</th></tr>']
    for n in D['names']:
        for p in D['sessions'][n][key]:
            o.append('<tr>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{e(p['tag'])}</td><td>{p['cpu']}</td><td>{'4 KiB' if p['no_thp'] else '2 MiB'}</td><td>{e(p['utc'])}</td><td>{fx(p['median'])}</td><td class=\"nw\">{fx(p['min'])} to {fx(p['max'])}</td>"
                     f"<td class=\"nw\">{p['levels']['low']} / {p['levels']['between']} / {p['levels']['high']}</td><td class=\"nw\">{p['cov']['full']} / {p['cov']['partial']} / {p['cov']['none']}</td>"
                     f"<td>{len(p['events']['thp_collapse_alloc'])} / {len(p['events']['pgmigrate_success'])}</td><td>{len(p['changes'])}</td><td class=\"nw\">{s2(p['step_size'])}{'' if p['step_at'] is None else ' into interval %d' % p['step_at']}</td></tr>")
    o.append('</table></div>')
    o.append('<p class="cap">Intervals are numbered from 0. "Counter increases" counts the intervals before which <code>thp_collapse_alloc</code> or <code>pgmigrate_success</code> was higher than at the reading before. '
             '"Largest step" is the largest absolute difference between two neighbouring intervals, with the number of the later interval.</p>')
    return '\n'.join(o)


def sec_b4(D, R):
    o = ['<h2 id="b4">B4: 200 intervals of asm read on one buffer, with the page state</h2>']
    o.append('<p>One process maps one 8 MiB buffer and times asm read 200 times. Before every interval it reads the huge-page coverage of the buffer (<code>kB_huge</code> of <code>kB_total</code>) and four counters of <code>/proc/vmstat</code> ' + R('handoff') + '. '
             'Half of the processes ask for 4 KiB pages with <code>--no-thp</code>. Each interval is its own reference: its label comes from its own rate. '
             'H3a predicts that every low interval has less than full coverage and every high interval has full coverage ' + R('plan') + '.</p>')
    have = [n for n in D['names'] if D['sessions'][n]['b4']]
    for n in D['names']:
        if n not in have:
            o.append(miss(f'Step B4{" of session " + e(n) if many(D) else ""}: no process is in the input. A run of step B4 would give it.'))
    if not have:
        return '\n'.join(o)
    allr = [v for n in have for p in D['sessions'][n]['b4'] for v in p['rates']]
    ymin, ymax = axis_floor(min(min(allr), LOW) - 0.3), math.ceil((max(max(allr), HIGH) + 0.5) * 2) / 2
    o.append(f'<p><span class="lg"><i style="background:{C0}"></i>rate of one interval</span><span class="lg"><i style="background:{RED};border-radius:0;width:3px"></i>thp_collapse_alloc rose before the interval</span>'
             f'<span class="lg"><i style="background:#7a3fb5;border-radius:0;width:3px"></i>pgmigrate_success rose before the interval</span><span class="lg"><i style="background:{BAND};border-radius:0"></i>between the two limits ({LOW:g} and {HIGH:g} GB/s)</span></p>')
    takes, lost, case_txt, h3b = [], [], [], []
    for n in have:
        x = D['sessions'][n]
        P = x['b4']
        if many(D):
            o.append(f'<h3>Session {e(n)}</h3>')
        chart, left_out = seq_chart(P, ymin, ymax, 'B4: rate against interval number for each process')
        o.append(chart)
        lost += [(n, t, i, v) for t, i, v in left_out]
        nev = sum(len(p['events'][k]) for p in P for k in p['events'])
        nch = sum(len(p['changes']) for p in P)
        full = [p for p in P if p['cov']['full'] == len(p['rates'])]
        none = [p for p in P if p['cov']['none'] == len(p['rates'])]
        t = f'{"Session " + e(n) + ". " if many(D) else ""}{pl(len(full), "process", "processes")} had full huge-page coverage before every interval, and {pl(len(none), "process", "processes")} had none before every interval. '
        if full:
            t += f'The median rates of the processes with full coverage are between {fx(min(p["median"] for p in full))} and {fx(max(p["median"] for p in full))} GB/s. '
        if none:
            t += f'The median rates of the processes with no huge page are between {fx(min(p["median"] for p in none))} and {fx(max(p["median"] for p in none))} GB/s. '
        t += f'The two vmstat counters rose before {pl(nev, "interval", "intervals")}. {pl(nch, "change", "changes")} between low and high occurred inside a process. '
        big = [p for p in P if p['step_size'] is not None and abs(p['step_size']) > 1]
        if big:
            up = sum(1 for p in big if p['step_size'] > 0)
            t += (f'Description, no decision: in {len(big)} of {pl(len(P), "process", "processes")} the largest step between two neighbouring intervals is above 1 GB/s. {up} of these steps {"goes" if up == 1 else "go"} upward. '
                  f'All of them occur within the first {max(p["step_at"] for p in big) + 1} intervals of a process. After its largest step, the rate of such a process stays within {fx(max(p["after_max"] - p["after_min"] for p in big))} GB/s. ')
        takes.append(t + fref(R, D, n, 'B4'))
        pc = x['res'].get('B4', {}).get('per_cpu', {})
        pre = f'Session {e(n)}. ' if many(D) else ''
        cases = [(c, v['cases']) for c, v in pc.items() if v['cases']]
        if not cases:
            case_txt.append(pre + 'Neither case occurred on a CPU. The result of this session for H3a is "not observed".')
        for c, cs in cases:
            t = pre + f'On CPU {c}, case ({") and (".join(cs)}) occurred by the rule. '
            f = x['b4_cases'].get(c)
            if f:
                t += (f'{pl(f["n_lo_procs"], "process has", "processes have")} at least 10 low intervals with full coverage, and {pl(f["n_hi_procs"], "process has", "processes have")} at least 10 high ones. '
                      + ('At least one process has at least 10 of each. ' if f['both'] else 'No process has both: the level differs between processes, not inside one. '))
                t += f'The low intervals with full coverage are between {fx(f["low_min"])} and {fx(f["low_max"])} GB/s. The high ones are between {fx(f["high_min"])} and {fx(f["high_max"])} GB/s. '
                if f['label_dependent']:
                    t += (f'<b>This case depends on the provisional limits.</b> {f["near_lo"]} of the {f["n_low"]} low intervals lie less than {NEAR:g} GB/s below the limit of {LOW:g} GB/s. '
                          'So this page does not state that the bounded prediction failed on this CPU before the limits are decided. Description without labels: ')
                    for p in f['both']:
                        for ch in p['change_info']:
                            a, b = p['rates'][:ch['frm'] + 1], p['rates'][ch['to']:]
                            t += (f'with full coverage in all intervals and {pl(sum(len(v) for v in p["events"].values()), "increase", "increases")} of the two vmstat counters, the rate of process {e(p["tag"])} '
                                  f'went from a median of {fx(median(a))} GB/s (intervals 0 to {ch["frm"]}) to a median of {fx(median(b))} GB/s (intervals {ch["to"]} to {len(p["rates"]) - 1}). ')
                else:
                    t += 'So the bounded prediction of H3a failed in this session on this CPU. '
            case_txt.append(t)
        if nch == 0 and nev == 0:
            h3b.append(pre + 'No interval shows a level change, and none follows an increase of <code>thp_collapse_alloc</code> or <code>pgmigrate_success</code>. So this session has no case of "a level change with no sign of a page change" to report for H3b ' + R('plan') + '.')
        elif nch:
            ns = sum(v['level_changes_with_no_sign_of_a_page_change'] for v in pc.values())
            nn = sum(v['level_changes_low_high'] for v in pc.values())
            h3b.append(pre + f'{ns} of the {pl(nn, "level change", "level changes")} between two neighbouring labelled intervals had equal coverage and no increase of the two counters between the two intervals. The plan calls this "no sign of a page change". It is not proof that the physical pages stayed the same ' + R('plan') + '.')
    o.append('<p class="take">' + '<br>'.join(takes) + '</p>')
    o.append('<p class="cap">One panel is one process. The vertical axis is the rate in GB/s, and it is the same in all panels of all sessions. It starts at ' f'{ymin:g}' ' GB/s, not at 0. The four numbers at the right of a panel are computed from all intervals. Value labels mark the first, the last, the lowest and the highest interval. '
             + (f'{pl(len(lost), "value label was", "value labels were")} left out, because no free place was found: '
                + ', '.join(f'{"session " + e(n) + ", " if many(D) else ""}process {e(t)}, interval {i} ({fx(v)} GB/s)' for n, t, i, v in lost) + '. ' if lost else '') +
             'The vmstat counters count for the whole system, not for the buffer ' + R('handoff') + '. The limit of 1 GB/s for a step is a choice of this page for the description.</p>')
    o.append('<h3>The counts behind cases (a) and (b)</h3>')
    o.append('<p>The handoff names two cases that contradict H3a, each per CPU and session. Case (a): at least 10 low and at least 10 high intervals with full coverage. '
             'Case (b): at least 10 low and at least 10 high intervals with no huge page ' + R('handoff', 'devscripts') + '.</p>')
    o.append('<div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if many(D) else '') + '<th>CPU</th><th>Processes</th><th>Of them with --no-thp</th><th>Low, full coverage</th><th>High, full coverage</th><th>Case (a)</th>'
             '<th>Low, no huge page</th><th>High, no huge page</th><th>Case (b)</th><th>Between the limits, full / none</th><th>Partial or unknown coverage</th><th>Result of the rule for this CPU</th></tr>')
    for n in have:
        for c, v in D['sessions'][n]['res'].get('B4', {}).get('per_cpu', {}).items():
            iv = v['intervals']
            other = sum(iv[l][k] for l in iv for k in ('partial', 'unknown'))
            o.append('<tr>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{c}</td><td>{v['n_processes']}</td><td>{v['n_processes_no_thp']}</td><td>{iv['low']['full']}</td><td>{iv['high']['full']}</td><td>{yn('a' in v['cases'])}</td>"
                     f"<td>{iv['low']['none']}</td><td>{iv['high']['none']}</td><td>{yn('b' in v['cases'])}</td><td>{iv['changing']['full']} / {iv['changing']['none']}</td><td>{other}</td>"
                     f"<td class=\"l\">{e(v['decision'])}</td></tr>")
    o.append('</table></div>')
    o.append('<p class="take">' + '<br>'.join(case_txt) + '</p>')
    o.append(f'<p class="cap">"Depends on the provisional limits" means: more than half of the low intervals with full coverage lie less than {NEAR:g} GB/s below {LOW:g} GB/s, or more than half of the high ones lie less than {NEAR:g} GB/s above {HIGH:g} GB/s. The value {NEAR:g} GB/s is a choice of this page.</p>')
    o += [f'<p>{t}</p>' for t in h3b]
    o.append('<details><summary>Values of every process of B4</summary>' + proc_table(D, 'b4') + '</details>')
    return '\n'.join(o)


B6N = {'oldread': 'old read 8 MiB', 'oldread2': 'old read 2, 8 MiB', 'oldread@1M': 'old read 1 MiB'}


def sec_b6(D, R):
    o = ['<h2 id="b6">B6: old read at 8 MiB and at 1 MiB, with references</h2>']
    o.append('<p>Each process times old read at 8 MiB, old read at 1 MiB (a size that fits L2) and a second copy of old read at 8 MiB, with reference intervals of asm read at 8 MiB between the pairs ' + R('handoff') + '. '
             'H1 predicts two things: the rate of old read at 8 MiB does not differ between low and high intervals, and it does not differ from its rate at 1 MiB ' + R('plan') + '.</p>')
    have = [n for n in D['names'] if D['sessions'][n]['b6']]
    for n in D['names']:
        if n not in have:
            o.append(miss(f'Step B6{" of session " + e(n) if many(D) else ""}: no process is in the input. A run of step B6 would give it.'))
    if not have:
        return '\n'.join(o)
    o.append('<h3>Part 1: old read in low against high intervals</h3>')
    o.append('<div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if many(D) else '') + '<th>CPU</th><th>Stable low processes</th><th>Stable high processes</th><th>Processes that are not stable</th><th>A/A spread, GB/s</th><th>Low minus high, GB/s</th>'
             '<th>Old read at 8 MiB, GB/s</th><th>Old read at 1 MiB, GB/s</th><th>Reference (asm read at 8 MiB), GB/s</th><th>Rule: word</th></tr>')
    nobs = nall = 0
    for n in have:
        x = D['sessions'][n]
        g = x['b6']
        for c, v in x['res']['B6']['state'].items():
            nall += 1
            nobs += v['decision'] == 'not observed'
            pc = g['per_cpu'].get(c)
            rf = [median(r['refs']) for r in g['recs'] if r['cpu'] == c]
            o.append('<tr>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{c}</td><td>{v['n_low']}</td><td>{v['n_high']}</td><td>{v['n_changing']}</td><td>{fx(v['aa_spread'])}</td><td>{s2(v['difference'])}</td>"
                     + (f"<td>{fx(pc['first_rate'])}</td><td>{fx(pc['second_rate'])}</td><td>{fx(median(rf))}</td>" if pc and rf else '<td>-</td><td>-</td><td>-</td>') + f"<td class=\"l nw\">{e(v['decision'])}</td></tr>")
    o.append('</table></div>')
    o.append(f'<p class="take">In {nobs} of {pl(nall, "row", "rows")} the result is "not observed". The rule needs 2 stable low and 2 stable high processes on one CPU. '
             + (f'{ID}: old read in stable high intervals. A session in which a CPU has both stable low and stable high processes would give it. ' if nobs else '') + frefs(R, D, 'B6') + '</p>')
    o.append('<p class="cap">The three rate columns give the median over the processes of the CPU of the median rate of each process.</p>')
    o.append(group_block(D, R, 'B6', None, 'Part 2: old read at 8 MiB minus old read at 1 MiB', 'old read at 8 MiB minus old read at 1 MiB', 'old read 2 minus old read, both at 8 MiB', False, None, marked=False))
    # by previous entry
    o.append('<h3>Old read by the loop that ran directly before it (description, no decision)</h3>')
    allv = [q for n in have for c in D['sessions'][n]['b6_prev'].values() for v in c.values() for q in v]
    xmin, xmax = axis_floor(min(allv) - 0.2), max(allv) + 0.4
    takes = []
    for n in have:
        x = D['sessions'][n]
        bp, g = x['b6_prev'], x['b6']
        rows, facts, groups = [], [], set()
        for c in sorted(bp):
            for ent in ('oldread', 'oldread2', 'oldread@1M'):
                for kind in ('asm read', 'an old read entry'):
                    v = bp[c].get((ent, kind))
                    if not v:
                        continue
                    other = bp[c].get((ent, 'an old read entry' if kind == 'asm read' else 'asm read'))
                    right = f'{fx(median(v))} GB/s'
                    if kind == 'asm read' and other:
                        diff = median(v) - median(other)
                        right = f'{fx(median(v))} GB/s: {zs(diff)} against next row'
                        facts.append((c, ent, diff))
                    rows.append((f'CPU {c}: {B6N[ent]}, after {"asm read" if kind == "asm read" else "old read"}', [(q, f'{fx(q)} GB/s', 0) for q in v], right))
            groups.add(len(rows))
        if not rows:
            continue
        if many(D):
            o.append(f'<h4>Session {e(n)}</h4>')
        o.append(strip(rows, xmin, xmax, f'rate of one interval, GB/s (the axis starts at {xmin:g} GB/s, not at 0)', 'B6: rate of old read by the loop that ran before', L=262, R=230, groups=groups, right_head='median of the row'))
        big = [f[2] for f in facts if f[1] in ('oldread', 'oldread2')]
        if big:
            takes.append(f'{"Session " + e(n) + ". " if many(D) else ""}An interval of old read at 8 MiB that follows an asm read interval differs from one that follows an old read interval by {rng(min(big), max(big), signed=True)} GB/s (median, per CPU and copy). '
                         f'The largest A/A spread of a CPU is {fx(max(v["aa_spread"] for v in g["per_cpu"].values()))} GB/s, and the largest single A/A pair is {fx(max(v["aa_single_max"] for v in g["per_cpu"].values()))} GB/s. ' + fref(R, D, n, 'B6'))
    if takes:
        o.append('<p class="take">Description, no decision. ' + '<br>'.join(takes) + '</p>')
    o.append('<p class="cap">One dot is one interval. "After old read" means that the interval before was old read at 8 MiB, its second copy, or old read at 1 MiB. The first interval of a process is not shown, because nothing ran before it.</p>')
    cav, effect = b6_caveat(D)
    if cav:
        o.append('<p><b>What this means for part 2.</b> In the B6 sequence one loop of each pair follows a reference interval of asm read, and the other follows an old read interval ' + R('handoff') + '. '
                 'So a pair value contains the difference between the two loops and the difference between the two positions.</p><ul>' + ''.join(f'<li>{e(c)}</li>' for c in cav) + '</ul>')
        if effect:
            o.append('<p>The position difference is measured. Its cause is a hypothesis: the loop that ran before leaves a state (cache contents or prefetcher state) that changes the rate of old read at 8 MiB in the next 0.3 s interval. '
                     'A counter run of the B6 sequence, as in Part C, would confirm or reject it: it would show whether the refills per line differ between the two positions. The rule and its result were not changed.</p>')
    o.append(proc_details(D, 'B6', lambda x: [('B6', x['b6'])] if x['b6'] else [], 'Values of every process of B6'))
    return '\n'.join(o)


ENTRY_ORDER = ['asmcopy', 'asmcopy2', 'copy', 'asmread']
LEVEL_ORDER = ['-', 'low', 'changing', 'high']


def group_name(g):
    lev = '' if g['level'] == '-' else ', ' + ('between the limits' if g['level'] == 'changing' else g['level'])
    return f"{g['group'].replace('cpu', 'CPU ')}: {kn(g['entry'])}{lev}"


def counter_groups(r):
    cpu_no = lambda g: int(re.sub(r'\D', '', g['group']) or 0)
    groups = sorted((dict(g, _name=group_name(g)) for g in r['groups']),
                    key=lambda g: (cpu_no(g), ENTRY_ORDER.index(g['entry']) if g['entry'] in ENTRY_ORDER else 9, LEVEL_ORDER.index(g['level']) if g['level'] in LEVEL_ORDER else 9))
    for i, g in enumerate(groups):
        g['_last'] = i + 1 < len(groups) and groups[i + 1]['group'] != g['group']
    return groups


def c2_words(groups):
    """C2: the counts per line of new C copy next to asm copy, as ranges over the CPUs. Description only."""
    cp = [g for g in groups if g['entry'] == 'copy']
    ac = [g for g in groups if g['entry'] == 'asmcopy']
    if not cp or not ac:
        return ''
    t = []
    for k, name, nd in (('cycles', 'Cycles per line', 2), ('l2d_refill', 'L2D refills per line', 3), ('l1d_refill', 'L1D refills per line', 3), ('instructions', 'Instructions per line', 3)):
        a = [g['median_%s_per_line' % k] for g in cp if g['median_%s_per_line' % k] is not None]
        b = [g['median_%s_per_line' % k] for g in ac if g['median_%s_per_line' % k] is not None]
        if a and b:
            rel = ('equal at this precision' if rng(min(a), max(a), nd) == rng(min(b), max(b), nd) else 'new C copy is higher on every CPU' if min(a) > max(b) else
                   'new C copy is lower on every CPU' if max(a) < min(b) else 'the ranges overlap')
            t.append(f'{name}: new C copy {rng(min(a), max(a), nd)}, asm copy {rng(min(b), max(b), nd)} ({rel}).')
    return ' '.join(t)


def sec_c(D, R):
    o = ['<h2 id="c">C1 and C2: core counters per 64 B line</h2>']
    o.append('<p>The counter runs repeat the schedule of B4 (C1) and of B1 at 8 MiB (C2). Each thread reads five counters of its own core directly before and after every interval. The counters count only the code of the benchmark, not the Linux kernel ' + R('handoff') + '. '
             'A line is 64 B of the bytes that the interval counts. A copy interval counts the bytes read plus the bytes written ' + R('analyze') + '. '
             'The clock is the cycle count divided by the CPU time of the thread. Part C gives a description. The handoff has no decision rule for it ' + R('devscripts') + '. '
             'The plan asks C1 for the counts per line at the low and at the high level, and C2 whether the memory-side counts per line differ between the two copy loops ' + R('plan') + '.</p>')
    l1 = []
    for step, bstep, what in (('C1', 'B4', 'asm read, 200 intervals'), ('C2', 'B1', 'the copy loops at 8 MiB')):
        o.append(f'<h3>{step}: {what}</h3>')
        takes, tables, comp, comp_n, no_high = [], [], [], [0, 0], []
        for name in D['names']:
            x = D['sessions'][name]
            r = x['res'].get(step)
            pre = f'Session {e(name)}. ' if many(D) else ''
            if not r or not r['groups']:
                o.append(miss(f'Step {step}{" of session " + e(name) if many(D) else ""}: no counter row is in the input. A run of step {step} would give it.'))
                continue
            groups = counter_groups(r)
            f = x['cfacts'][step]
            if many(D):
                o.append(f'<h4>Session {e(name)}</h4>')
            o.append(counter_chart(groups, f'{step}: counter values per line for each CPU, kernel and level group'))
            ipl = [g['median_instructions_per_line'] for g in groups if g['median_instructions_per_line'] is not None]
            clk = [g['median_clock_GHz'] for g in groups if g['median_clock_GHz'] is not None]
            t = (f'{pre}{f["used"]} of the {pl(f["rows"], "counter row", "counter rows")} are used. '
                 + (f'The clock of the busy core is {rng(min(clk), max(clk), 3)} GHz over the groups. ' if clk else '')
                 + (f'Instructions per line: {rng(min(ipl), max(ipl), 3)} over the groups. ' if ipl else ''))
            if f['cpu_share_min'] is not None:
                t += f'The lowest CPU time of a thread was {fx(math.floor(1e4 * f["cpu_share_min"]) / 100, 2)} % of the elapsed time of its interval (rounded down). '
            if step == 'C2':
                w = c2_words(groups)
                if w:
                    t += 'Description, no decision. ' + w + ' '
            takes.append(t + fref(R, D, name, step))
            if step == 'C1' and not any(g['level'] == 'high' for g in groups):
                no_high.append((name, sorted({'between the limits' if g['level'] == 'changing' else g['level'] for g in groups})))
            if f['read_rows']:
                l1.append((name, step, f['l1_lt_l2'], f['read_rows']))
            tb = ['<div class="tw"><table class="c"><tr><th>CPU</th><th>Kernel</th><th>Level group</th><th>Processes</th><th>Intervals</th><th>Rate, GB/s</th><th>Clock, GHz</th>' + ''.join(f'<th>{n} per line</th>' for _, n in EV) + '</tr>']
            for g in groups:
                lev = {'-': 'no level', 'changing': 'between the limits'}.get(g['level'], g['level'])
                tb.append(f"<tr><td>{e(g['group'].replace('cpu', ''))}</td><td>{e(kn(g['entry']))}</td><td class=\"nw\">{lev}</td><td>{g['n_processes']}</td><td>{g['n_rows']}</td><td>{f2(g['median_thread_GBps'])}</td><td>{f2(g['median_clock_GHz'], 3)}</td>"
                          + ''.join(f"<td class=\"nw\">{small(g['median_%s_per_line' % k], 4) if g['median_%s_per_line' % k] is not None else 'not supported'}</td>" for k, _ in EV) + '</tr>')
            tables.append(f'<details><summary>Values of every group of {step}{", session " + e(name) if many(D) else ""}</summary>' + ''.join(tb) + '</table></div></details>')
            # rates of the counter run next to Part B
            cm, bm = x['proc_medians'][step], x['proc_medians'][bstep]
            if bstep == 'B1':
                bm = x['b1_8m_medians']
            for c, k in sorted({(c, k) for c, k, nt, _ in cm if not nt}):
                a = [v for cc, kk, nt, v in cm if (cc, kk) == (c, k) and not nt]
                b = [v for cc, kk, nt, v in bm if (cc, kk) == (c, k) and not nt]
                if a and b:
                    ov = min(a) <= max(b) and min(b) <= max(a)
                    comp_n[0] += ov
                    comp_n[1] += 1
                    comp.append('<tr>' + (f'<td>{e(name)}</td>' if many(D) else '') + f"<td>{c}</td><td>{e(kn(k))}</td><td>{len(a)}</td><td>{fx(min(a))} to {fx(max(a))}</td><td>{len(b)}</td><td>{fx(min(b))} to {fx(max(b))}</td><td>{yn(ov)}</td></tr>")
            if not any(1 for c, k, nt, _ in bm if not nt):
                o.append(miss(f'{pre}The rates of step {bstep}, to compare with the counter run.'))
        if no_high:
            o.append(miss(f'Counters at the high level in a long run. No interval of C1 was above {HIGH:g} GB/s' + (f' in {"session" if len(no_high) == 1 else "sessions"} {" and ".join(e(n) for n, _ in no_high)}' if many(D) else '')
                          + f'. The level groups that were seen are: {", ".join(sorted({v for _, lv in no_high for v in lv}))}. A C1 process that reaches the high level would give them.'))
        if takes:
            o.append('<p class="take">' + '<br>'.join(takes) + '</p>')
        if comp:
            o.append(f'<p>In {comp_n[0]} of {pl(comp_n[1], "row", "rows")} (one per CPU, kernel and session) the process medians of the counter run overlap those of step {bstep} without counters. ' + frefs(R, D, step, bstep) + '</p>')
            tables.append(f'<details><summary>Rates of {step} next to step {bstep} without counters</summary><div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if many(D) else '') + f'<th>CPU</th><th>Kernel</th><th>{step}: processes</th><th>{step}: process medians, GB/s</th><th>{bstep}: processes</th><th>{bstep}: process medians, GB/s</th><th>The two ranges overlap</th></tr>'
                          + ''.join(comp) + '</table></div></details>')
        o += tables
    if l1:
        low = [q for q in l1 if q[2]]
        if low:
            o.append('<p>Observation: the count of <code>l1d_refill</code> is lower than the count of <code>l2d_refill</code> in '
                     + ', '.join(f'{a} of the {pl(b, "asm read interval", "asm read intervals")} of {st}{" in session " + e(n) if many(D) else ""}' for n, st, a, b in l1) + '. '
                     'A line that enters L2 from the SLC and is then loaded would be expected to enter L1 too. '
                     'Hypothesis: for this loop the two event names do not count what they say (for example, lines that the prefetcher brings into L1 may not count as L1D refills). '
                     f'{ID} to decide it: the event definitions of this core, or a run of the same loop on a buffer that fits L1 and one that fits L2, would show what each event counts. The observation was first made in the short run before session 1, in 970 of 973 counter rows of asm read ' + R('short') + '.</p>')
        else:
            o.append(f'<p>In none of the {pl(sum(q[3] for q in l1), "asm read interval", "asm read intervals")} is the count of <code>l1d_refill</code> lower than the count of <code>l2d_refill</code>.</p>')
    o.append('<p class="cap">Every value is the median over the intervals of the group. The level group of an asm read interval comes from its own rate and the provisional limits. Copy intervals get no level ' + R('devscripts') + '. '
             '"LL read miss" is the event <code>ll_miss_rd</code>, a read that misses the last cache level. A value below 0.000001 is printed as "below 10^-6" in a chart and as "below 1 per million" (lines) in a table. '
             'The rate panel of a chart prints the number only, because all rates are within a few percent of each other. Every other panel has its own axis from 0 to the value printed under it.</p>')
    return '\n'.join(o)


WORDS = [
    ('CRB', 'the Arm Phoenix Reference Server (128 cores of the Arm 64-bit instruction set AArch64). All measurements ran there.'),
    ('Plan, handoff', 'the files <code>plan.md</code> (the reviewed test plan) and <code>handoff.md</code> (the instructions for its execution, with the numeric decision rules).'),
    ('Part A, B, C, D', 'the parts of the plan. Part A was screening with the existing benchmark. Part B uses the changed benchmark <code>bwx</code>. Part C reads counters of the cores. Part D needs root and was not run.'),
    ('Q1', 'the first question of the plan: why one thread with an 8 MiB buffer behaves differently from the other buffer sizes. Q1a is about old read, Q1b about copy, Q1c about two rates of one loop. The second question, Q2, is about many threads and has its own page.'),
    ('Kernel, loop', 'one timed loop of the benchmark. It is not the Linux kernel.'),
    ('<code>bwx</code>', 'the changed copy of the benchmark <code>bandwidth.c</code> that Parts B and C use. <code>bwx_o0</code>, <code>bwx_o36</code>, <code>bwx_o52</code> are three more builds for step B3.'),
    ('asm read (<code>asmread</code>)', 'the read loop written in assembly. Per 256 B it runs 8 load instructions and no add.'),
    ('Old read (<code>oldread</code>), old read 2 (<code>oldread2</code>)', 'the C read loop from before 2026-11-13, and a second copy of the same source. <code>oldread@1M</code> is old read on the first 1 MiB of the buffer.'),
    ('New C copy (<code>copy</code>)', 'the C copy loop since 2026-11-13.'),
    ('asm copy (<code>asmcopy</code>), asm copy 2 (<code>asmcopy2</code>)', 'the copy loop written in assembly, and a second copy of the same source.'),
    ('<code>asmcopy_c</code>', 'step B2: an assembly loop with the machine code of the new C copy loop (same instruction order, same registers q16 to q31), placed at the loop offset of asm copy.'),
    ('<code>asmcopy_c_add</code>', 'as <code>asmcopy_c</code>, but the two <code>add</code> instructions are placed after the 8 stores, as in asm copy.'),
    ('<code>asmcopy_c_reg</code>', 'as <code>asmcopy_c</code>, but with the registers q0 to q15, as in asm copy.'),
    ('Loop offset, "modulo 64"', 'the address of the first instruction of a loop, as the remainder after division by 64 B. 64 B is the size of one cache line.'),
    ('<code>-falign-loops=1</code>', 'an option of the C compiler gcc that stops the compiler from moving a loop start to an aligned address.'),
    ('Process, launch, tag', 'a process is one start of <code>bwx</code>. It allocates its own buffers. A launch is that start by the run script. The tag of a process is its name in the run script, for example <code>8M-cpu2-p1</code>.'),
    ('Header line', 'the line that the run script writes before the output of each process. It has the tag, the load readings and the options.'),
    ('Interval', 'one timed period of one loop inside a process, here at least 0.3 s. Before the timed period the loop runs once over the buffer without timing (the warm-up pass).'),
    ('Session', 'one run of all steps. The plan asks for two sessions some hours apart.'),
    ('Rate', 'bytes moved per second, in GB/s (1 GB = 10<sup>9</sup> bytes). A copy counts the bytes read plus the bytes written.'),
    ('Median', 'the middle value of a sorted list. With an even count it is the mean of the two middle values.'),
    ('L1, L2, SLC', 'the three cache levels of a core. SLC is the system-level cache (L3), shared by all cores. An 8 MiB buffer fits the SLC and does not fit L2. A 1 MiB buffer fits L2.'),
    ('Prefetcher', 'the part of a core that fetches cache lines before the loop asks for them.'),
    ('Level', 'asm read at 8 MiB runs at one of two rates: a lower one (about 67 to 69 GB/s in the sweep of 2026-11-02) or a higher one (about 70.5 to 71.7 GB/s). Which one occurs can differ between processes and can change inside a process.'),
    ('Reference interval', 'an interval of asm read at 8 MiB that is timed directly before or after a compared pair. It shows the level at that time.'),
    ('Low, high, between', 'the provisional level labels of an asm read interval at 8 MiB: below 69 GB/s, above 70.5 GB/s, or neither. The analysis script prints "changing" for "between".'),
    ('Stable process', 'a process whose reference intervals all have one label, low or high. Only a stable process gives a value to a decision at 8 MiB.'),
    ('Group', 'the processes of one size, one variant or one build that are compared together. A level group of a counter table is the intervals of one CPU, one loop and one label.'),
    ('Pair, pair value', 'two neighbouring intervals of two loops between the same two reference intervals, and the rate of the first loop of "X minus Y" minus the rate of the second.'),
    ('d, e', 'the two values of one process. d is the median of its pair values of the two compared loops. e is the median of its pair values of the two copies of one loop.'),
    ('A/A control, A/A spread', 'a loop that exists twice in the program under two names. The A/A spread of a CPU is the largest absolute e of its processes. It shows how much two equal loops differ.'),
    ('Resolved', 'the plan\'s word for a difference whose median is larger than the A/A spread and that has one sign in all processes. It needs 3 processes on a CPU, and 2 such CPUs with the same sign. "(-)" and "(+)" give the sign.'),
    ('The five words', '"rejected" (the bounded prediction failed in both sessions), "not rejected", "not observed" (an event that the test could have shown did not occur), "not resolved" (the difference is inside the A/A spread), "not tested".'),
    ('Bounded prediction', 'the one statement of a hypothesis that a step tests, as the plan words it.'),
    ('Description, no decision', 'values that this page computes for all processes without level labels. They are given next to the rule. They never change a word of the rule.'),
    ('THP, 2 MiB pages, <code>--no-thp</code>', 'Linux can back memory with pages of 2 MiB instead of 4 KiB (transparent huge pages, THP). With <code>--no-thp</code> the benchmark asks for 4 KiB pages.'),
    ('Huge-page coverage, <code>kB_huge</code>, <code>kB_total</code>', 'how many kB of the buffer are backed by 2 MiB pages, of how many kB in total. "Full" means all, "none" means 0 kB.'),
    ('<code>thp_collapse_alloc</code>, <code>pgmigrate_success</code>', 'two counters of <code>/proc/vmstat</code> for the whole system. The first counts huge pages that Linux built from small pages. The second counts pages that Linux moved.'),
    ('Page state', 'the huge-page coverage of the buffer and the counters of <code>/proc/vmstat</code>, read before an interval.'),
    ('Case (a), case (b)', 'the two outcomes of step B4 that contradict H3a. Case (a): one CPU has at least 10 low and at least 10 high intervals with full coverage. Case (b): the same with no huge page.'),
    ('Counter, PMU', 'a hardware event counter of a core, read with the Linux call <code>perf_event_open</code>. PMU is the counter unit of the core.'),
    ('<code>l1d_refill</code>, <code>l2d_refill</code>, <code>ll_miss_rd</code>', 'the event names of the core for a line that is brought into the L1 data cache, into the L2 cache, and for a read that misses the last cache level.'),
    ('Per line', 'a count divided by the number of 64 B lines that the interval moved.'),
    ('Clock', 'cycles of the interval divided by the CPU time of the thread in that interval, in GHz.'),
    ('Load, runnable tasks, waited', 'the Linux 1-minute load average (the average count of tasks that run or wait to run), the count of tasks that can run at one moment, and the time the script waited for at most 2 runnable tasks before a launch.'),
    ('B1', 'step: new C copy against asm copy with the A/A pair, sizes 4, 8, 16, 32 MiB, CPUs 0, 2, 41, 94, 4 processes each.'),
    ('B2', 'step: the three variants <code>asmcopy_c</code>, <code>asmcopy_c_add</code>, <code>asmcopy_c_reg</code> against asm copy, at 8 MiB.'),
    ('B3', 'step: new C copy against asm copy with both loops at offset 0, 36 or 52 modulo 64, at 8 MiB.'),
    ('B4', 'step: asm read at 8 MiB for 200 intervals with the page state, CPUs 2 and 41, half of the processes with <code>--no-thp</code>.'),
    ('B6', 'step: old read at 8 MiB and at 1 MiB with reference intervals, CPUs 2, 41, 94.'),
    ('B9', 'a step for question Q2 that runs 120 threads. It ran directly before B1. This page uses only its end time, for the system load.'),
    ('C1, C2', 'steps: the schedule of B4 and of B1 at 8 MiB with core counters.'),
    ('D2', 'step of Part D: the physical addresses of the buffer pages. Not run.'),
    ('H1', 'hypothesis: old read is limited inside the core at every cache size, and its rate at 8 MiB does not depend on the level of the load-only loop.'),
    ('H2', 'hypothesis: the low level can change to the high level while the stream runs, and the high level can stay for the next process.'),
    ('H3a', 'hypothesis: huge-page coverage decides the level. The low level is a buffer that is not fully on 2 MiB pages.'),
    ('H3b', 'hypothesis: the physical address of the pages decides the level.'),
    ('H4', 'hypothesis: the copy difference does not come from the kernel code. It comes from something that differs between processes.'),
    ('H5', 'hypothesis: the copy difference comes from the instruction order of the C loop.'),
    ('H6', 'hypothesis: the copy difference comes from the address of the loop (36 against 52 modulo 64).'),
    ('est.', 'an estimate, not a measurement.'),
]


def main_table(D, R):
    """The main numbers: one row per step, one column per session. Every cell is built from computed values."""
    rows = []

    def cells(fn):
        out = []
        for name in D['names']:
            out.append(fn(D['sessions'][name]) or '-')
        return out

    def b1(x):
        G = x['pairs']['B1']
        if not G:
            return ''
        res, t = x['res'].get('B1', {}).get('groups', {}), []
        for k in sorted(G, key=lambda k: G[k]['size']):
            meds = [v['median_d'] for v in G[k]['per_cpu'].values()]
            lab = res.get(k, {}).get('labels', {})
            if G[k]['size'] == 8 * MIB:
                w = sorted({v['decision'] + ab.sign_txt(v['sign']) for v in lab.values()})
                t.append(f'<b>8 MiB: {rng(min(meds), max(meds), signed=True)} GB/s</b> (description, no decision). Rule at 8 MiB: {", ".join(w)}.')
            else:
                r = lab.get('none')
                t.append(f'{G[k]["size"]//MIB} MiB: {rng(min(meds), max(meds), signed=True)} GB/s. Rule: {r["decision"] + ab.sign_txt(r["sign"]) if r else "-"}.')
        return 'Median d per CPU (new C copy minus asm copy).<br>' + '<br>'.join(t)

    def variants(step):
        def f(x):
            G = x['pairs'][step]
            t = []
            for k in sorted(G):
                meds = [v['median_d'] for v in G[k]['per_cpu'].values()]
                t.append(f'{e(k)}: {rng(min(meds), max(meds), signed=True)} GB/s.')
            return 'Median d per CPU against asm copy (description, no decision).<br>' + '<br>'.join(t) if t else ''
        return f

    def b4(x):
        if not x['b4']:
            return ''
        t = []
        for c, v in x['res']['B4']['per_cpu'].items():
            full = [p for p in x['b4'] if p['cpu'] == c and p['cov']['full'] == len(p['rates'])]
            s = f'CPU {c}: ' + (f'{pl(len(full), "process", "processes")} with full huge-page coverage, medians {rng(min(p["median"] for p in full), max(p["median"] for p in full))} GB/s. ' if full else '')
            f = x['b4_cases'].get(c)
            if v['cases']:
                s += f'Case ({") and (".join(v["cases"])}) by the rule' + (', which depends on the provisional limits.' if f and f['label_dependent'] else '. This contradicts H3a in this session.')
            else:
                s += 'No case.'
            t.append(s)
        return '<br>'.join(t)

    def b6(x):
        g = x['b6']
        if not g:
            return ''
        pc = g['per_cpu'].values()
        sz = x['res']['B6']['size']['labels']['none']
        return (f'Median d per CPU (old read at 8 MiB minus old read at 1 MiB): {rng(min(v["median_d"] for v in pc), max(v["median_d"] for v in pc), signed=True)} GB/s. Rule: {sz["decision"] + ab.sign_txt(sz["sign"])}.<br>'
                f'With old read at 8 MiB timed first: {rng(min(v["d_first"] for v in pc), max(v["d_first"] for v in pc), signed=True)} GB/s. Timed second: {rng(min(v["d_second"] for v in pc), max(v["d_second"] for v in pc), signed=True)} GB/s.')

    def c1(x):
        r = x['res'].get('C1')
        if not r or not r['groups']:
            return ''
        cy = [g['median_cycles_per_line'] for g in r['groups'] if g['median_cycles_per_line'] is not None]
        lv = sorted({'between' if g['level'] == 'changing' else g['level'] for g in r['groups']})
        return f'asm read: {rng(min(cy), max(cy))} cycles per line. Levels seen: {", ".join(lv)}.' if cy else ''

    def c2(x):
        r = x['res'].get('C2')
        if not r or not r['groups']:
            return ''
        a = [g['median_cycles_per_line'] for g in r['groups'] if g['entry'] == 'copy' and g['median_cycles_per_line'] is not None]
        b = [g['median_cycles_per_line'] for g in r['groups'] if g['entry'] == 'asmcopy' and g['median_cycles_per_line'] is not None]
        return f'Cycles per line: new C copy {rng(min(a), max(a))}, asm copy {rng(min(b), max(b))} (description).' if a and b else ''

    for step, what, fn in (('B1', 'copy loops, 4 sizes', b1), ('B2', 'three assembly variants, 8 MiB', variants('B2')), ('B3', 'three loop offsets, 8 MiB', variants('B3')),
                           ('B4', 'asm read, 200 intervals', b4), ('B6', 'old read, 8 MiB and 1 MiB', b6), ('C1', 'counters, schedule of B4', c1), ('C2', 'counters, schedule of B1', c2)):
        c = cells(fn)
        if any(v != '-' for v in c):
            rows.append(f'<tr><td>{step}</td><td>{what}</td>' + ''.join(f'<td>{v}</td>' for v in c) + '</tr>')
    if not rows:
        return ''
    return ('<div class="tw"><table class="pt hy"><tr><th style="width:6%">Step</th><th style="width:17%">What it compares</th>' + ''.join(f'<th>Session {e(n)}</th>' for n in D['names']) + '</tr>' + ''.join(rows) + '</table></div>'
            '<p class="cap">d is a difference of rates inside one process. A negative d means that the first loop is slower. The sections below give the charts, the processes and the A/A spread of every value ' + frefs(R, D, *Q1_STEPS) + '</p>')


def limits_fit(D):
    """True if fewer than half of the processes with reference intervals are stable under the provisional limits. None without data."""
    rr = [r for x in D['sessions'].values() for r in x['refs'] if r['kind'] == 'reference intervals']
    n = sum(r['n_procs'] for r in rr)
    return None if not n else sum(r['n_stable_low'] + r['n_stable_high'] for r in rr) * 2 >= n


def short_version(D):
    """At most three sentences, built from computed values."""
    n = len(D['names'])
    recs = [r for x in D['sessions'].values() for r in x['pairs']['B1'].get('8M', {}).get('recs', [])]
    if not recs:
        steps = sorted({st for x in D['sessions'].values() for st in x['steps']}, key=Q1_STEPS.index)
        return (f'This page reports the one-thread steps {", ".join(steps) if steps else "(none in the input)"} of {pl(n, "test session", "test sessions")}. '
                f'{ID} for the copy comparison at 8 MiB: no process of step B1 at 8 MiB is in the input.')
    neg = sum(1 for r in recs if r['d'] < 0)
    pcs = [v for x in D['sessions'].values() for v in x['pairs']['B1'].get('8M', {}).get('per_cpu', {}).values()]
    md, pct = [v['median_d'] for v in pcs], [v['pct'] for v in pcs]
    if max(md) < 0:
        size = f'median per CPU: {rng(-max(md), -min(md))} GB/s slower, which is {rng(-max(pct), -min(pct), 1)} %'
    else:
        size = f'median difference per CPU: {rng(min(md), max(md), signed=True)} GB/s'
    st = sum(1 for r in recs if r['stable'])
    h4 = sorted({r['word'] for r in D['hyp'] if r['h'].startswith('H4')})
    s1 = (f'With one thread and an 8 MiB buffer, the new C copy loop was slower than the assembly copy loop in {neg} of {len(recs)} program runs over {pl(n, "test session", "test sessions")} ({size}). ')
    s2_ = (f'The agreed decision rule could use only {st} of these {len(recs)} runs, and its formal result for the copy question is "{", ".join(h4)}"' + (' (one session cannot give "rejected")' if n < 2 else '') + '. ')
    fit = limits_fit(D)
    s3 = ('The two rate limits that the rule uses do not fit the data, and the user must decide whether to change them.' if fit is False else
          'The two rate limits that the rule uses are provisional, and the user must decide whether to keep them.')
    return s1 + s2_ + s3


def h1_line(D):
    """The line under the Short version: what the word of H1 consists of."""
    r = next((r for r in D['hyp'] if r['h'] == 'H1'), None)
    q = b6_position(D)
    if not r or not q or r['word'] == 'not tested':
        return ''
    a = sorted(abs(v) for v in q['first'])
    b = sorted(abs(v) for v in q['second'])
    return (f'<p>H1 (the rate of the old read loop does not depend on the buffer size) gets the word "{e(r["word"])}" by the rule. '
            f'The measured difference depends on which loop ran directly before. Its absolute value is {rng(a[0], a[-1])} GB/s in one order of the two loops and {rng(b[0], b[-1])} GB/s in the other. '
            'The hypothesis table and section B6 give the details.</p>')


def session_gap(D):
    t = [(n, x['t_start']) for n, x in D['sessions'].items() if x['t_start'] is not None]
    if len(t) < 2:
        return None
    gap = max(v for _, v in t) - min(v for _, v in t)
    return gap, time.strftime('%Y-%m-%d %H:%M', time.gmtime(min(v for _, v in t))), time.strftime('%Y-%m-%d %H:%M', time.gmtime(max(v for _, v in t)))


def build(D, banner=None, offsets=None):
    R = Refs()
    R.add('plan', '<code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md</code>: the questions Q1 and Q2, the hypotheses H1 to H11, rules 1 to 11, steps B1 to B10 and C1 to C3, Part D.')
    R.add('handoff', '<code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md</code>: sections B.3 (output rows), B.6 (page state), B.8 (counters), B.9 (sequences of each step), B.10 (numeric decision rules).')
    R.add('analyze', '<code>/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/analyze_bwx.py</code>: the parser and the decision analysis. This page imports its functions.')
    R.add('decide', '<code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/decide.py</code>: the decision rules of handoff B.10 as code, with the two level limits.')
    R.add('devscripts', '<code>/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/DEVIATIONS-scripts.md</code>: choices of the run script and of the analysis (points A12 to A16, A19, A20, A22, A30, A32).')
    R.add('offsets', '<code>/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/crb-build-2/offsets.tsv</code> (loop start of every kernel in the four builds) and <code>build.txt</code> in the same folder (compiler flags, <code>EXTRA_bwx_o52=-falign-loops=1</code>).')
    R.add('runscript', '<code>/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/run_bwx.sh</code>: the launches, the wait before each launch, the header line of each process, <code>launches.txt</code> and <code>env.txt</code>.')
    R.add('short', '<code>/home/jhan/workspace/titan/cache-perf/crb/results/SHORT-20261113T214338Z/SHORT.csv</code>: the short run of every sequence before session 1.')
    R.add('self', '<code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partBC-analysis/make_q1_html.py</code> and <code>test_q1.py</code>: the script that built this page, and its tests.')
    for name in D['names']:
        x = D['sessions'][name]
        for f in x['folders'] + x['other']:
            R.add(('folder', name, f['name']), f"<code>{e(f['path'])}/</code>: " + ', '.join(f'<code>{st}.csv</code>' for st in f['steps']) + f", <code>env.txt</code>, <code>launches.txt</code>, <code>stderr.txt</code>. Session {e(name)}, {'step' if len(f['steps']) == 1 else 'steps'} {', '.join(f['steps'])}.")
    R('plan', 'handoff', 'analyze', 'decide')
    for name in D['names']:
        for st in Q1_STEPS:
            fref(R, D, name, st)
    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>Parts B and C, question Q1: result</title>', f'<style>{CSS}</style></head><body>']
    if banner:
        o.append(f'<p class="banner">{e(banner)}</p>')
    o.append('<h1>Parts B and C, question Q1: one thread at 8 MiB</h1>')
    o.append(f'<p class="take"><b>Short version.</b> {short_version(D)}</p>')
    o.append(h1_line(D))
    mt = main_table(D, R)
    if mt:
        o.append('<p><b>Main numbers of this page.</b> All values are in GB/s unless a unit is given.</p>' + mt)
    for name in D['names']:
        x = D['sessions'][name]
        t = f'<p>Session {e(name)}: {pl(x["n_procs"], "process", "processes")} of the steps {", ".join(x["steps"]) if x["steps"] else "(none)"} in {pl(len(x["folders"]), "result folder", "result folders")} ' + R(*[('folder', name, f['name']) for f in x['folders']]) + '. '
        t += ('Every process is used. ' if x['n_used'] == x['n_procs'] else f'{x["n_procs"] - x["n_used"]} of them are not used, see the section on the system load. ')
        if x['missing']:
            t += f'{ID} for {", ".join(x["missing"])}: no process of {"this step is" if len(x["missing"]) == 1 else "these steps are"} in the input. A run of {"that step" if len(x["missing"]) == 1 else "those steps"} would give it. '
        o.append(t + '</p>')
    o.append('<h2 id="words">Words used here</h2><ul class="words">' + ''.join(f'<li><b>{k}</b>: {v}</li>' for k, v in WORDS) + '</ul>')
    o.append(sec_hyp(D, R))
    o.append(sec_load(D, R))
    o.append(sec_refs(D, R))
    o.append(sec_howto(D, R))
    o.append(sec_b1(D, R))
    o.append(sec_variants(D, R, 'B2', 'B2: three assembly variants of the C copy loop against asm copy',
                          '<p>Each variant replaces new C copy in the B1 sequence at 8 MiB. All three variants and asm copy have their loop at 52 modulo 64 ' + R('offsets') + '. '
                          'H5 predicts that <code>asmcopy_c</code>, the assembly loop with the instruction order of the C loop, differs from asm copy by a resolved amount of the sign of B1 ' + R('plan') + '. '
                          'The plan runs B2 only after a resolved difference in B1. B2 was run although B1 at 8 MiB is not formally resolved. This is a deviation. Its purpose is that the data exist if the level limits are revised.</p>',
                          lambda k: f'{k} minus asm copy', lambda k: k))
    off = offsets_table(offsets)
    o.append(sec_variants(D, R, 'B3', 'B3: new C copy and asm copy with both loops at one offset',
                          '<p>Three more builds place the loops of new C copy, asm copy and asm copy 2 at 0, 36 or 52 modulo 64. H6 predicts that the difference between the two loops changes by a resolved amount when both are at one offset ' + R('plan') + '. '
                          'The build <code>bwx_o52</code> uses the added compiler option <code>-falign-loops=1</code>. Without it gcc moved the C copy loop from offset 52 to offset 0 ' + R('offsets') + '. '
                          'B3 was run although B1 at 8 MiB is not formally resolved, for the same reason as B2.</p>' + off,
                          lambda k: f'new C copy minus asm copy in {k}', lambda k: k))
    o.append(sec_b4(D, R))
    o.append(sec_b6(D, R))
    o.append(sec_c(D, R))
    o.append('<h2 id="other">Deviations and decisions that concern this page</h2><ul>'
             '<li>Level limits. The limits of rule 5 of the plan were not changed. The section on the reference rate gives their strict result and the open decision.</li>'
             '<li>B2, B3 and C2 were run although B1 at 8 MiB is not formally resolved. The plan runs them only after a resolved difference in B1 ' + R('plan') + '.</li>'
             '<li>H3a in the analysis script, corrected on 2026-11-14. Before, the script gave each session the result "not observed" when the two sessions had their case on different CPUs. '
             'Now the result of a session comes from that session alone. The word over the sessions still needs one CPU with a case in every session (points A13 and A32) ' + R('devscripts') + '.</li>'
             '<li>H2. The plan gives H2 no bounded prediction in Parts B and C, so its word is "not tested". The level changes that B4 and C1 show are given as a description.</li>'
             '</ul>')
    gap = session_gap(D)
    o.append('<h2 id="limits">Limits of this page</h2><ul>'
             '<li>The level limits (' f'{LOW:g}' ' and ' f'{HIGH:g}' ' GB/s) are provisional and are not validated against the reference rates of this page. Every word in the hypothesis table uses them unchanged. A description is not a decision.</li>'
             '<li>B1, B2 and B3 have 4 processes per CPU and group. The rule needs 3 stable processes on each of 2 CPUs. ' + stable_sentence(D) + ' So under the present limits this design could not give H4, H5 and H6 a word other than "not observed".</li>'
             '<li>The first reference interval of a process is the first timed interval after its start. The section on the reference rate gives the number of processes in which it has another label than the later ones.</li>'
             + (f'<li>The one-thread steps of the sessions started at {gap[1]} and {gap[2]} UTC, {gap[0] // 3600} h {gap[0] % 3600 // 60} min apart. So "two sessions" does not cover a different day or a restart of the machine.</li>' if gap else '')
             + '<li>The word for H3a depends on the same-CPU condition of the handoff, which step B4 of the plan does not have. The hypothesis table lists this as open for the user.</li>'
             '<li>H3b is "not tested". Part D (counters that need root, physical addresses of the pages) was not run ' + R('plan') + '. This limit applies to every statement on the cause of the two levels.</li>'
             '<li>The vmstat counters count for the whole system. No increase is no proof that the physical pages of the buffer stayed the same ' + R('plan') + '.</li>'
             '<li>A thread that does not run on its CPU for a part of an interval is not flagged in a run without counters. This was found in the short run: one thread of a process with 120 threads had a CPU time of 87.2 % of its elapsed time, and its row has no flag ' + R('short') + '. '
             'B1, B2, B3, B4 and B6 ran without counters, so this page cannot exclude such an interval in them. The counter runs C1 and C2 give the CPU time of each interval.</li>'
             '<li>The event names of the counters are taken as the core names them. The section on the counters gives one observation that does not fit the names.</li>'
             '<li>In step B6 the two loops of a pair are at different positions after the reference interval. Section B6 shows that the position changes the rate of old read at 8 MiB.</li>'
             f'<li>{ID}: the load during an interval. The script reads it only before each launch.</li>'
             '<li>The chart colours were not checked with the palette checker of the chart rules. Every chart also uses position, shape or a text label.</li>'
             '</ul>')
    o.append('<p class="cap">The script <code>make_q1_html.py</code> built this page, and <code>test_q1.py</code> tests it ' + R('self') + '.</p>')
    o.append('<h2 id="refs">References</h2>' + R.html() + '</body></html>')
    return '\n'.join(t for t in o if t)


def offsets_table(path):
    if not path or not os.path.exists(path):
        return miss('The loop offsets of the builds: the file <code>offsets.tsv</code> was not found.')
    rows = [l.rstrip('\n').split('\t') for l in open(path)][1:]
    want = ('copy', 'asmcopy', 'asmcopy2', 'asmcopy_c', 'asmcopy_c_add', 'asmcopy_c_reg', 'asmread', 'oldread', 'oldread2')
    bins = list(dict.fromkeys(r[0] for r in rows))
    get = {(r[0], r[1]): r[5] for r in rows if len(r) >= 6}
    o = ['<details><summary>Loop start of every kernel in the four builds</summary><div class="tw"><table><tr><th>Kernel</th>' + ''.join(f'<th>{e(b)}: loop start modulo 64</th>' for b in bins) + '</tr>']
    for k in want:
        o.append(f'<tr><td>{e(k)}</td>' + ''.join(f'<td>{e(get.get((b, k), "-"))}</td>' for b in bins) + '</tr>')
    o.append('</table></div><p class="cap">Loop offsets from the build on CRB. Steps B1, B2, B4, B6, C1 and C2 use <code>bwx</code>.</p></details>')
    return '\n'.join(o)


def make(spec, banner=None, offsets=os.path.join(BWX, 'crb-build-2', 'offsets.tsv')):
    sessions = load(spec)
    D = compute(sessions)
    return D, build(D, banner, offsets)


def main(argv=None):
    ap = argparse.ArgumentParser(description='result page of question Q1 (one thread) of Parts B and C')
    ap.add_argument('--session', nargs='+', action='append', required=True, metavar=('NAME', 'FOLDER'))
    ap.add_argument('-o', '--out', default='partB-q1-result.html')
    ap.add_argument('--banner')
    ap.add_argument('--offsets', default=os.path.join(BWX, 'crb-build-2', 'offsets.tsv'))
    a = ap.parse_args(argv)
    spec = []
    for s in a.session:
        if len(s) < 2:
            ap.error('--session needs a name and at least one folder')
        spec.append((s[0], s[1:]))
    D, page = make(spec, a.banner, a.offsets)
    with open(a.out, 'w') as fh:
        fh.write(page)
    print('wrote %s (%d bytes), sessions: %s' % (a.out, len(page), ', '.join(D['names'])))
    for r in D['hyp']:
        print('  %-20s %-14s %s' % (r['h'], r['word'], r['step']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
