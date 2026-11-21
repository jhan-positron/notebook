#!/usr/bin/env python3
"""analyze_bwx.py - analysis of the bwx runs of Parts B and C (handoff.md, sections B.3 and B.10).

Usage:
  analyze_bwx.py --session NAME PATH [PATH...] [--session NAME PATH...] [--out DIR]
    PATH is a result folder of run_bwx.sh (all its *.csv files are read) or one csv file.
    NAME names the session (one visit plan run once; the plan asks for 2 sessions some hours apart).
    Without --out the text tables go to standard output. With --out DIR the script writes
    DIR/summary.json and DIR/<step>.txt, and prints the tables too.

Words: a "process" is one start of bwx (one "-- step ..." header line in a csv file). An "interval" is one
timed entry of the sequence. M_hist = (sum of the bytes of all threads) / (longest elapsed time of a thread).
M_sum = sum over the threads of (bytes / elapsed time). Rates are in GB/s (1 GB = 1e9 bytes).
q = rate of the thread at the 10th percentile / rate of the thread at the 90th percentile.
A/A spread = the largest absolute difference between two copies of one loop, over the processes of a group.

The decision rules are the functions of decide.py (new-test-kernel/decide.py). This file imports them.
Rules for which decide.py has no function are marked "local rule" below and listed in DEVIATIONS-scripts.md.
No rule is adapted to the data: where a definition does not fit, the result is "not observed" or
"not resolved", with the reason.
"""
import argparse, glob, json, math, os, re, sys
from statistics import median, mean

HERE = os.path.dirname(os.path.abspath(__file__))
for _d in (os.environ.get('DECIDE_DIR'), HERE, os.path.join(HERE, '..', '..', '..', 'new-test-kernel')):
    if _d and os.path.exists(os.path.join(_d, 'decide.py')):
        sys.path.insert(0, _d)
        break
import decide  # noqa: E402

MIB = 1 << 20
MESH0_CPUS = range(0, 64)                 # mesh 0 = CPUs 0-63, mesh 1 = CPUs 64-119 (handoff, machine table)
LATE_SKEW_S = 0.005                       # end skew above 5 ms makes an interval irregular (B.4, provisional)
Q_SPLIT, Q_UNIFORM = 0.65, 0.85           # pattern limits (handoff, Part A, rule 3, provisional)
B4_MIN_INTERVALS = 10                     # B4: at least 10 low and 10 high intervals
REF = 'asmread'                           # the reference kernel of the one-thread sequences
FLAG_OPTS = {'--no-thp', '--two-buffers', '--count'}
HEAD = re.compile(r'^-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) '
                  r'logins (\S+) utc (\S+) args ?(.*)$')


def parse_size(s):
    m = re.fullmatch(r'(\d+)([KMG]?)', s)
    if not m:
        raise ValueError('bad size ' + s)
    return int(m.group(1)) << {'': 0, 'K': 10, 'M': 20, 'G': 30}[m.group(2)]


def size_name(n):
    return '%dM' % (n // MIB) if n % MIB == 0 else '%dK' % (n // 1024) if n % 1024 == 0 else str(n)


# ---------------------------------------------------------------- parsing

class Interval:
    """One timed interval of one process, from its T rows."""

    def __init__(self, rnd, pos, entry):
        self.round, self.pos, self.entry = rnd, pos, entry
        self.rows, self.irow, self.problem = [], None, None

    def finish(self, threads, stop):
        r = self.rows
        if len(r) != threads:
            self.problem = '%d T rows, %d threads expected' % (len(r), threads)
            return
        if any(x['elapsed'] <= 0 for x in r):
            self.problem = 'elapsed time not above 0'
            return
        longest = max(x['elapsed'] for x in r)
        rates = sorted(x['bytes'] / x['elapsed'] / 1e9 for x in r)
        m0 = [x for x in r if x['cpu'] in MESH0_CPUS]
        m1 = [x for x in r if x['cpu'] not in MESH0_CPUS]
        self.hist = sum(x['bytes'] for x in r) / longest / 1e9
        self.msum = sum(rates)
        # per mesh: the same formulas over the threads of the mesh; M_hist keeps the longest time of ALL threads
        self.mesh_hist = tuple(sum(x['bytes'] for x in m) / longest / 1e9 for m in (m0, m1))
        self.mesh_sum = tuple(sum(x['bytes'] / x['elapsed'] / 1e9 for x in m) for m in (m0, m1))
        self.mesh_n = (len(m0), len(m1))
        self.rate = self.hist                                   # one thread: bytes / elapsed
        self.skew = max(x['t_end'] for x in r) - min(x['t_end'] for x in r)
        self.late = sum(1 for x in r if 'late' in x['flags'])
        # Irregular (B.4): a late thread, or an end skew above 5 ms. The end skew is a rule of the common
        # stop only: with --stop pass the threads end at pass borders, so their ends differ by design.
        self.irregular = bool(self.late) or (stop == 'common' and self.skew > LATE_SKEW_S)
        n = len(rates)                                          # nearest-rank percentiles
        self.q = rates[max(0, math.ceil(0.10 * n) - 1)] / rates[max(0, math.ceil(0.90 * n) - 1)]
        self.pattern = 'split' if self.q < Q_SPLIT else 'uniform' if self.q > Q_UNIFORM else 'between'


class Proc:
    """One bwx process: its header line and its rows."""

    def __init__(self, session, path, m):
        self.session, self.file = session, os.path.basename(os.path.dirname(path)) + '/' + os.path.basename(path)
        self.step, self.tag, self.binary = m.group(1), m.group(2), m.group(3)
        self.waited_s = float(m.group(4)) if re.fullmatch(r'[\d.]+', m.group(4)) else None
        self.load1 = float(m.group(5)) if re.fullmatch(r'[\d.]+', m.group(5)) else None
        self.runnable, self.logins, self.utc = m.group(8), m.group(9), m.group(10)
        self.args = m.group(11).split()
        self.opts, self.problems, self.status = {}, [], 'ok'
        t = self.args
        i = 0
        while i < len(t):
            if t[i] in FLAG_OPTS:
                self.opts[t[i]] = True
                i += 1
            elif t[i].startswith('--') and i + 1 < len(t):
                self.opts[t[i]] = t[i + 1]
                i += 2
            else:
                self.problems.append('option not understood: ' + t[i])
                i += 1
        o = self.opts
        self.bytes = parse_size(o.get('--bytes', '1M'))
        self.seq = [e for e in o.get('--seq', '').split(',') if e]
        self.rounds = int(o.get('--rounds', 1))
        self.threads = int(o.get('--threads', 1))
        self.stop, self.start = o.get('--stop', 'pass'), o.get('--start', 'common')
        self.min_ms = int(float(o.get('--min-ms', 0)))
        self.no_thp, self.two_buffers, self.count = (k in o for k in ('--no-thp', '--two-buffers', '--count'))
        self.cpu = int(o['--cpus']) if self.threads == 1 and o.get('--cpus', '').isdigit() else None
        self.setting = '%s/%d/%s' % (self.stop, self.min_ms, self.start)
        self.raw = {}             # (round as printed, pos) -> Interval
        self.P, self.C, self.n_I, self.other_lines = [], [], 0, 0
        self.iv, self.ordered, self.complete = {}, [], False

    def entry_size(self, entry):
        return parse_size(entry.split('@')[1]) if '@' in entry else self.bytes

    def add(self, line):
        f = line.split(',')
        try:
            if f[0] == 'I' and len(f) == 9:
                self.n_I += 1
                self._iv(int(f[1]), int(f[2]), f[3]).irow = dict(threads=int(f[5]), total_bytes=int(f[6]),
                                                                 max_elapsed=float(f[7]), aggregate=float(f[8]))
            elif f[0] == 'T' and len(f) == 13:
                self._iv(int(f[1]), int(f[2]), f[3]).rows.append(dict(
                    tid=int(f[4]), cpu=int(f[5]), bytes=int(f[6]), elapsed=float(f[7]), t_sched=float(f[8]),
                    t_start=float(f[9]), t_end=float(f[10]), passes=float(f[11]), flags=f[12]))
            elif f[0] == 'P' and len(f) == 11:
                num = lambda x: None if x == 'NA' else int(x)
                self.P.append(dict(round=int(f[1]), pos=int(f[2]), tid=int(f[3]), buffer=f[4], kB_total=num(f[5]),
                                   kB_huge=num(f[6]), thp_fault_alloc=num(f[7]), thp_fault_fallback=num(f[8]),
                                   thp_collapse_alloc=num(f[9]), pgmigrate_success=num(f[10])))
            elif f[0] == 'C' and len(f) >= 9:
                na = lambda x: None if x == 'NA' else int(x)      # NA: the group or the event did not open
                self.C.append(dict(round=int(f[1]), pos=int(f[2]), kernel=f[3], tid=int(f[4]), cpu=int(f[5]),
                                   enabled=na(f[6]), running=na(f[7]), cputime=na(f[8]), counts=[na(x) for x in f[9:]]))
            elif f[0] in ('I', 'T', 'P', 'C'):
                self.problems.append('row with a wrong number of fields: ' + line[:60])
            else:
                self.other_lines += 1
        except (ValueError, IndexError):
            self.problems.append('row not understood: ' + line[:60])

    def _iv(self, rnd, pos, kernel):
        if not 0 <= pos < len(self.seq):
            self.problems.append('position %d is outside the sequence' % pos)
            pos_entry = kernel
        else:
            pos_entry = self.seq[pos]
            if kernel.split('@')[0] != pos_entry.split('@')[0]:
                self.problems.append('kernel %s at position %d, the sequence has %s' % (kernel, pos, pos_entry))
        return self.raw.setdefault((rnd, pos), Interval(rnd, pos, pos_entry))

    def finish(self):
        rounds = sorted({k[0] for k in self.raw})                # rounds may be printed from 0 or from 1
        for (rnd, pos), iv in self.raw.items():
            iv.finish(self.threads, self.stop)
            if iv.problem:
                self.problems.append('round %d pos %d: %s' % (rnd, pos, iv.problem))
            iv.r = rounds.index(rnd)
            self.iv[(iv.r, pos)] = iv
        self.ordered = [self.iv[k] for k in sorted(self.iv)]
        want = len(self.seq) * self.rounds
        if self.status == 'ok' and len(self.iv) != want:
            self.problems.append('%d intervals, %d expected' % (len(self.iv), want))
        self.complete = self.status == 'ok' and not self.problems and want > 0
        self.rate_by_entry = {}
        if self.complete:
            for iv in self.ordered:
                self.rate_by_entry.setdefault(iv.entry, []).append(iv)

    def page_before(self, iv):
        """One-thread process: the P row read before the interval (same round and position), buffer a."""
        rows = [p for p in self.P if p['round'] == iv.round and p['pos'] == iv.pos]
        a = [p for p in rows if p['buffer'] in ('a', 'A', '0')]
        return a[0] if len(a) == 1 else rows[0] if len(rows) == 1 else None


def read_csv(session, path):
    procs, cur = [], None
    with open(path) as fh:
        for line in fh:
            line = line.rstrip('\n')
            if line.startswith('-- step '):
                m = HEAD.match(line)
                if not m:
                    raise ValueError('%s: header line not understood: %s' % (path, line[:80]))
                cur = Proc(session, path, m)
                procs.append(cur)
            elif line.startswith('-- killed') or line.startswith('-- failed'):
                if cur:
                    cur.status = line.split()[1]
            elif cur and line and not line.startswith('#'):
                cur.add(line)
    for p in procs:
        p.finish()
    return procs


def load_session(name, paths):
    procs = []
    for path in paths:
        files = sorted(glob.glob(os.path.join(path, '*.csv'))) if os.path.isdir(path) else [path]
        if not files:
            raise ValueError('no csv file in ' + path)
        for f in files:
            procs += read_csv(name, f)
    return procs


# ---------------------------------------------------------------- helpers

def med(v):
    return median(v) if v else None


def row(what, word, n, spread, value, note=''):
    """One line of the text table of a step: every decision with its number of processes and its A/A spread."""
    return dict(what=what, decision=word, n_processes=n, aa_spread=spread, value=value, note=note)


def integrity(procs):
    """What every step reports first: the processes used, the processes left out, the irregular intervals, the load."""
    used = [p for p in procs if p.complete]
    load = [p.load1 for p in procs if p.load1 is not None]
    waits = [p.waited_s for p in procs if p.waited_s is not None]
    out = dict(
        n_processes=len(procs), n_used=len(used),
        left_out=[dict(file=p.file, tag=p.tag, reason=(p.status if p.status != 'ok' else '; '.join(p.problems[:3]) or 'no interval'))
                  for p in procs if not p.complete],
        irregular_intervals=[dict(file=p.file, tag=p.tag, round=iv.round, pos=iv.pos, entry=iv.entry, late_threads=iv.late,
                                  end_skew_ms=round(iv.skew * 1e3, 3)) for p in used for iv in p.ordered if iv.irregular],
        load=dict(loadavg_1min_min=min(load) if load else None, loadavg_1min_max=max(load) if load else None,
                  waited_s_max=max(waits) if waits else None, logins=sorted({p.logins for p in procs})),
        page_rows_NA=sum(1 for p in procs for x in p.P if x['kB_total'] is None or x['kB_huge'] is None),
        page_rows=sum(len(p.P) for p in procs))
    return used, out


def pair_label(refs):
    """Rule 5 of the plan: low if both neighbouring references are low, high if both are high, else changing."""
    levels = {decide.level(r) for r in refs}
    return levels.pop() if len(levels) == 1 and levels != {'changing'} else 'changing'


def pair_values(p, first, second):
    """Pairs of the entries first and second that stand between the same two reference intervals.
    Value = rate of first minus rate of second (GB/s)."""
    out = []
    refpos = [i for i, e in enumerate(p.seq) if e == REF]
    for r in range(p.rounds):
        for a, b in zip(refpos, refpos[1:]):
            if b - a != 3 or {p.seq[a + 1], p.seq[a + 2]} != {first, second} or first == second:
                continue
            rate = {p.seq[i]: p.iv[(r, i)].rate for i in (a + 1, a + 2)}
            refs = (p.iv[(r, a)].rate, p.iv[(r, b)].rate)
            out.append(dict(round=r, pos=a + 1, value=rate[first] - rate[second], label=pair_label(refs)))
    return out


def one_thread_group(procs, first, second, aa_first, aa_second, labelled):
    """One size (or variant, or build) of a one-thread step. Process values with decide.process_value,
    decision per label and per CPU with decide.decide_one_thread. CPUs are never pooled."""
    plist, detail = [], []
    for p in procs:
        kp, ap = pair_values(p, first, second), pair_values(p, aa_first, aa_second)
        refs = [iv.rate for iv in p.ordered if iv.entry == REF]
        pv = decide.process_value(refs, [x['value'] for x in kp], [x['value'] for x in ap], labelled=labelled)
        rec = dict(file=p.file, tag=p.tag, cpu=p.cpu, reference_min=min(refs) if refs else None,
                   reference_median=med(refs), reference_max=max(refs) if refs else None,
                   n_kernel_pairs=len(kp), n_aa_pairs=len(ap))
        if pv is None:
            rec.update(used=False, reason='no pair found' if not kp or not ap else 'the reference intervals are not all at one level',
                       pairs=[dict(label=x['label'], value=round(x['value'], 3)) for x in kp])
        else:
            rec.update(used=True, label=pv[0], d=pv[1], e=pv[2])
            plist.append(dict(cpu=p.cpu, label=pv[0], d=pv[1], e=pv[2]))
        detail.append(rec)
    dec = decide.decide_one_thread(plist) if plist else {}
    out = {}
    for lab in (('low', 'high') if labelled else ('none',)):
        word, sign, per = dec.get(lab, ('not observed', None, {}))
        cpus = {}
        for cpu in sorted({p.cpu for p in procs}):
            g = [x for x in plist if x['cpu'] == cpu and x['label'] == lab]
            w = per.get(cpu, ('not observed', None))
            cpus[cpu] = dict(decision=w[0], sign=w[1], n_processes=len(g), d=[x['d'] for x in g],
                             median_d=med([x['d'] for x in g]), aa_spread=max((abs(x['e']) for x in g), default=None))
        out[lab] = dict(decision=word, sign=sign, per_cpu=cpus,
                        n_processes=sum(c['n_processes'] for c in cpus.values()),
                        note='' if word != 'not observed' else 'Insufficient data: fewer than 2 CPUs have 3 processes with this label; '
                        'processes per CPU: ' + ', '.join('CPU %s: %d' % (c, v['n_processes']) for c, v in cpus.items()))
    return out, detail, plist


def group_rows(name, res):
    rows = []
    for lab, r in res.items():
        rows.append(row('%s label %s, all CPUs' % (name, lab), r['decision'] + sign_txt(r['sign']), r['n_processes'], None, None, r['note']))
        for cpu, c in r['per_cpu'].items():
            rows.append(row('%s label %s CPU %s' % (name, lab, cpu), c['decision'] + sign_txt(c['sign']), c['n_processes'],
                            c['aa_spread'], c['median_d'], 'value = median d'))
    return rows


def sign_txt(s):
    return '' if s is None else ' (+)' if s > 0 else ' (-)'


# ---------------------------------------------------------------- one-thread steps

def a_copy(procs, ctx, step):
    """B1 (per size), B2 (per variant), B3 (per build), C2: kernel pair against asmcopy, A/A pair asmcopy2 - asmcopy."""
    used, out = integrity(procs)
    groups = {}
    for p in used:
        other = [e for e in p.seq if e not in (REF, 'asmcopy', 'asmcopy2')]
        first = other[0] if other else None
        key = p.binary if step == 'B3' else first if step == 'B2' else size_name(p.bytes)
        groups.setdefault((key, first, p.bytes), []).append(p)
    out['groups'], rows, plists = {}, [], {}
    for (key, first, size), g in sorted(groups.items(), key=lambda kv: str(kv[0])):
        res, detail, plist = one_thread_group(g, first, 'asmcopy', 'asmcopy2', 'asmcopy', labelled=(size == 8 * MIB))
        out['groups'][key] = dict(kernel_pair='%s - asmcopy' % first, aa_pair='asmcopy2 - asmcopy', size=size_name(size),
                                  labels=res, processes=detail)
        plists[key] = plist
        rows += group_rows('%s %s (%s - asmcopy)' % (step, key, first), res)
    ctx[step] = plists
    if step == 'B3':
        out['change_against_B1'] = {}
        base = ctx.get('B1', {}).get('8M')
        for key, plist in plists.items():
            ch = {}
            for lab in ('low', 'high'):
                for cpu in sorted({x['cpu'] for x in plist}):
                    y = [dict(D=x['d'], E=x['e']) for x in plist if x['cpu'] == cpu and x['label'] == lab]
                    x_ = [dict(D=x['d'], E=x['e']) for x in (base or []) if x['cpu'] == cpu and x['label'] == lab]
                    if base is None:
                        word, change, note = 'not observed', None, 'B1 at 8 MiB of the same session is missing'
                    else:
                        word, change = decide.decide_change(x_, y, min_n=3)
                        note = 'change = median d of B1 minus median d of the build' if change is not None else \
                            'fewer than 3 processes with this label on this CPU in B1 (%d) or in the build (%d)' % (len(x_), len(y))
                    spread = None if change is None else max(abs(v['E']) for v in x_) + max(abs(v['E']) for v in y)
                    ch['%s/cpu%s' % (lab, cpu)] = dict(decision=word, change=change, n_B1=len(x_), n_build=len(y), sum_of_aa_spreads=spread, note=note)
                    rows.append(row('B3 %s change against B1, label %s CPU %s' % (key, lab, cpu), word, '%d and %d' % (len(x_), len(y)), spread, change, note))
            out['change_against_B1'][key] = ch
    out['rows'] = rows
    return out


def a_b6(procs, ctx, step):
    used, out = integrity(procs)
    # first comparison: old read at 8 MiB in stable-low against stable-high processes on the same CPU
    state, detail = [], []
    for p in used:
        aa = [x['value'] for x in pair_values(p, 'oldread2', 'oldread')]
        refs = [iv.rate for iv in p.ordered if iv.entry == REF]
        pv = decide.process_value(refs, aa, aa, labelled=True)        # gives the label of the process, or None
        old = [iv.rate for iv in p.rate_by_entry.get('oldread', [])]
        if not aa or not old:
            detail.append(dict(file=p.file, tag=p.tag, used=False, reason='no old read interval or no A/A pair'))
            continue
        rec = dict(cpu=p.cpu, label=pv[0] if pv else 'changing', rate=median(old), e=median(aa))
        state.append(rec)
        detail.append(dict(file=p.file, tag=p.tag, used=True, **rec))
    st = decide.decide_b6_state(state) if state else {}
    out['state'] = {}
    rows = []
    for cpu, (word, diff) in st.items():
        g = [x for x in state if x['cpu'] == cpu]
        n = dict((lab, sum(1 for x in g if x['label'] == lab)) for lab in ('low', 'high', 'changing'))
        spread = max(abs(x['e']) for x in g)
        note = 'value = median old read of the low processes minus that of the high processes'
        if word == 'not observed':
            note = 'Insufficient data: a CPU needs 2 stable low and 2 stable high processes; this CPU has %d low, %d high, %d changing' % (n['low'], n['high'], n['changing'])
        out['state'][cpu] = dict(decision=word, difference=diff, n_low=n['low'], n_high=n['high'], n_changing=n['changing'], aa_spread=spread, note=note)
        rows.append(row('B6 old read at 8 MiB, low against high, CPU %s' % cpu, word, '%d low, %d high' % (n['low'], n['high']), spread, diff, note))
    out['state_processes'] = detail
    # second comparison: old read at 8 MiB minus old read at 1 MiB, decided as B1 with the label "none"
    res, detail2, _ = one_thread_group(used, 'oldread', 'oldread@1M', 'oldread2', 'oldread', labelled=False)
    out['size'] = dict(kernel_pair='oldread - oldread@1M', aa_pair='oldread2 - oldread', labels=res, processes=detail2)
    out['rows'] = rows + group_rows('B6 (oldread - oldread@1M)', res)
    return out


def coverage(p_row):
    if p_row is None or p_row['kB_total'] is None or p_row['kB_huge'] is None:
        return 'unknown'
    return 'full' if p_row['kB_huge'] == p_row['kB_total'] else 'none' if p_row['kB_huge'] == 0 else 'partial'


def a_b4(procs, ctx, step):
    """B4: every interval has the label of its own rate. Counts of intervals per CPU, label and coverage."""
    used, out = integrity(procs)
    out['per_cpu'], rows = {}, []
    for cpu in sorted({p.cpu for p in used}):
        counts, changes, no_sign = {}, 0, 0
        g = [p for p in used if p.cpu == cpu]
        for p in g:
            prev = None
            for iv in p.ordered:
                pr = p.page_before(iv)
                cur = (decide.level(iv.rate), coverage(pr), pr)
                counts[(cur[0], cur[1])] = counts.get((cur[0], cur[1]), 0) + 1
                if prev and {prev[0], cur[0]} == {'low', 'high'}:
                    changes += 1
                    a, b = prev[2], cur[2]
                    if a and b and prev[1] == cur[1] != 'unknown' and a['thp_collapse_alloc'] == b['thp_collapse_alloc'] \
                            and a['pgmigrate_success'] == b['pgmigrate_success'] and a['thp_collapse_alloc'] is not None:
                        no_sign += 1
                if cur[0] != 'changing':
                    prev = cur
        n = lambda lab, cov: counts.get((lab, cov), 0)
        cases = [c for c, cov in (('a', 'full'), ('b', 'none')) if n('low', cov) >= B4_MIN_INTERVALS and n('high', cov) >= B4_MIN_INTERVALS]
        word = 'contradicts H3a (case %s)' % ' and '.join(cases) if cases else 'not observed'
        table = {lab: {cov: n(lab, cov) for cov in ('full', 'partial', 'none', 'unknown')} for lab in ('low', 'changing', 'high')}
        note = 'intervals low/high with full coverage %d/%d, with coverage none %d/%d; a case needs 10 and 10' % (
            n('low', 'full'), n('high', 'full'), n('low', 'none'), n('high', 'none'))
        out['per_cpu'][cpu] = dict(decision=word, cases=cases, intervals=table, n_processes=len(g),
                                   n_processes_no_thp=sum(1 for p in g if p.no_thp),
                                   level_changes_low_high=changes, level_changes_with_no_sign_of_a_page_change=no_sign, note=note)
        rows.append(row('B4 CPU %s, H3a' % cpu, word, len(g), None, None, note + '; B4 has no A/A pair'))
    out['rows'] = rows
    return out


# ---------------------------------------------------------------- steps with many threads

METRICS = (('M_hist', lambda iv: iv.hist), ('M_sum', lambda iv: iv.msum),
           ('M_hist_mesh0', lambda iv: iv.mesh_hist[0]), ('M_hist_mesh1', lambda iv: iv.mesh_hist[1]))


def diff_value(p, a, b, key):
    """One process: the mean over its rounds of (mean of the intervals of entry a minus mean of those of b).
    No value if an interval that it needs is irregular."""
    vals = []
    for r in range(p.rounds):
        ia = [p.iv[(r, i)] for i, e in enumerate(p.seq) if e == a]
        ib = [p.iv[(r, i)] for i, e in enumerate(p.seq) if e == b]
        if not ia or not ib:
            return None, 'the sequence has no %s or no %s' % (a, b)
        bad = [iv for iv in ia + ib if iv.irregular]
        if bad:
            return None, 'irregular interval (round %d pos %d)' % (bad[0].round, bad[0].pos)
        vals.append(mean(key(iv) for iv in ia) - mean(key(iv) for iv in ib))
    return mean(vals), None


def setting_values(procs, a, b, aa2, aa):
    """-> {metric: [dict(D, E, tag)]} and the processes without a value."""
    vals, missing = {m: [] for m, _ in METRICS}, []
    for p in procs:
        for m, key in METRICS:
            D, why = diff_value(p, a, b, key)
            E, why2 = diff_value(p, aa2, aa, key)
            if D is None or E is None:
                if m == 'M_hist':
                    missing.append(dict(file=p.file, tag=p.tag, reason=why or why2))
                continue
            vals[m].append(dict(D=D, E=E, tag=p.tag))
    return vals, missing


def both_metrics(by_metric):
    """The decision metric is M_hist. If M_sum gives another word or another sign, the result is 'not resolved'."""
    h, s = by_metric['M_hist'], by_metric['M_sum']
    if (h['decision'], h.get('sign')) == (s['decision'], s.get('sign')):
        return h['decision'], h.get('sign'), ''
    return 'not resolved', None, 'M_hist gives "%s%s" and M_sum gives "%s%s": reported as not resolved' % (
        h['decision'], sign_txt(h.get('sign')), s['decision'], sign_txt(s.get('sign')))


def decide_d(vals, missing, min_n=4):
    by = {}
    for m, pl in vals.items():
        word, sign = decide.decide_setting(pl, min_n)
        by[m] = dict(decision=word, sign=sign, n_processes=len(pl), median_D=med([x['D'] for x in pl]),
                     aa_spread=max((abs(x['E']) for x in pl), default=None), D=[x['D'] for x in pl], E=[x['E'] for x in pl])
    word, sign, note = both_metrics(by)
    disagree = bool(note)                                       # M_hist and M_sum give another word or sign
    if word == 'not observed':
        note = '%d processes with a value, %d needed' % (by['M_hist']['n_processes'], min_n) + \
               (''.join('; %s has no value: %s' % (x['tag'], x['reason']) for x in missing))
    return dict(decision=word, sign=sign, note=note, metrics=by, metrics_disagree=disagree, processes_without_value=missing)


def factor_pairs(settings):
    """Pairs of settings (stop/min_ms/start) that differ in exactly one factor. The first of a pair is the one with
    pass, the shorter interval, or the common start."""
    names = ('stop', 'interval', 'start')
    order = lambda i, v: int(v) if i == 1 else int(v != ('pass', None, 'common')[i])
    out = []
    for x in settings:
        for y in settings:
            fx, fy = x.split('/'), y.split('/')
            d = [i for i in range(3) if fx[i] != fy[i]]
            if len(d) == 1 and order(d[0], fx[d[0]]) < order(d[0], fy[d[0]]):
                out.append((names[d[0]], x, y))
    return sorted(out)


def a_b7(procs, ctx, step):
    used, out = integrity(procs)
    main = [p for p in used if len(p.seq) > 1]
    single = [p for p in used if len(p.seq) == 1]
    out['settings'], rows, vals = {}, [], {}
    for s in sorted({p.setting for p in main}):
        g = [p for p in main if p.setting == s]
        vals[s], missing = setting_values(g, 'oldread', 'read', 'asmread2', 'asmread')
        d = decide_d(vals[s], missing)
        h = d['metrics']['M_hist']
        out['settings'][s] = d
        rows.append(row('B7 %s: D = oldread - read (M_hist)' % s, d['decision'] + sign_txt(d['sign']), h['n_processes'], h['aa_spread'], h['median_D'], d['note']))
        for m in ('M_sum', 'M_hist_mesh0', 'M_hist_mesh1'):
            x = d['metrics'][m]
            rows.append(row('B7 %s: D with %s (description)' % (s, m), x['decision'] + sign_txt(x['sign']), x['n_processes'], x['aa_spread'], x['median_D']))
    rep = out['settings'].get('pass/500/common')
    out['reproduction_in_one_process'] = 'not observed' if not rep else \
        'reproduced' if rep['decision'] == 'resolved' and rep['sign'] == 1 else 'not reproduced (D is %s%s)' % (rep['decision'], sign_txt(rep['sign']))
    out['changes'] = {}
    for factor, x, y in factor_pairs(list(vals)):
        by = {}
        for m in ('M_hist', 'M_sum'):
            word, change = decide.decide_change(vals[x][m], vals[y][m])
            spread = None if change is None else max(abs(v['E']) for v in vals[x][m]) + max(abs(v['E']) for v in vals[y][m])
            by[m] = dict(decision=word, change=change, sum_of_aa_spreads=spread, n_first=len(vals[x][m]), n_second=len(vals[y][m]))
        word, _, note = both_metrics(by)
        disagree = bool(note)
        if word == 'not observed':
            note = 'a setting has fewer than 4 processes with a value'
        h = by['M_hist']
        out['changes']['%s: %s -> %s' % (factor, x, y)] = dict(factor=factor, first=x, second=y, decision=word, note=note, metrics=by,
                                                              metrics_disagree=disagree)
        rows.append(row('B7 change of D, %s: %s minus %s' % (factor, x, y), word, '%d and %d' % (h['n_first'], h['n_second']),
                        h['sum_of_aa_spreads'], h['change'], note or 'A/A value = sum of the two A/A spreads'))
    out['single_kernel'] = sk = single_kernel(single, rows)
    # Plan, step B7: without a resolved D of the sign of 2026-11-13 in either way of running, no cause is assigned.
    out['reproduced_in_either_way'] = bool((rep and rep['decision'] == 'resolved' and rep['sign'] == 1) or
                                           (sk['decision'] == 'resolved' and sk.get('sign') == 1))
    out['rows'] = rows
    return out


def single_kernel(single, rows):
    """B7 with one kernel per process (local rule, B.10): process value = median of its intervals.
    D = median of the process values of oldread minus that of read. A/A value = |median asmread2 - median asmread|.
    Resolved if |D| is above the A/A value and every value of one kernel lies on one side of every value of the other.
    The decision metric is M_hist. The same rule is applied with M_sum, and another word or sign gives "not resolved"."""
    keys = dict(M_hist=lambda iv: iv.hist, M_sum=lambda iv: iv.msum)
    pv, left = {m: {} for m in keys}, []
    for p in single:
        if any(iv.irregular for iv in p.ordered):
            left.append(dict(file=p.file, tag=p.tag, reason='irregular interval'))
            continue
        for m, key in keys.items():
            pv[m].setdefault(p.seq[0], []).append(median(key(iv) for iv in p.ordered))
    n = {k: len(pv['M_hist'].get(k, [])) for k in ('oldread', 'read', 'asmread', 'asmread2')}
    res = dict(process_values=pv['M_hist'], process_values_M_sum=pv['M_sum'], n_processes=n, processes_without_value=left)
    if not single:
        return dict(decision='not observed', note='no process with one kernel in the input')
    if min(n.values()) < 4:
        res.update(decision='not observed', sign=None, D=None, aa_value=None,
                   note='4 processes of each kernel are needed; found ' + ', '.join('%s: %d' % kv for kv in n.items()))
    else:
        by = {}
        for m, v in pv.items():
            o, r = v['oldread'], v['read']
            D = median(o) - median(r)
            aa = abs(median(v['asmread2']) - median(v['asmread']))
            sep = max(o) < min(r) or min(o) > max(r)
            ok = abs(D) > aa and sep
            by[m] = dict(decision='resolved' if ok else 'not resolved', sign=(1 if D > 0 else -1) if ok else None, D=D, aa_value=aa)
        word, sign, note = both_metrics(by)
        if note:
            note += '; M_sum: D %s GB/s, A/A value %s GB/s' % (fmt(by['M_sum']['D']), fmt(by['M_sum']['aa_value']))
        res.update(decision=word, sign=sign, D=by['M_hist']['D'], aa_value=by['M_hist']['aa_value'], note=note, metrics=by,
                   metrics_disagree=bool(note))
    rows.append(row('B7 pass/500/common, one kernel per process: D (M_hist)', res['decision'] + sign_txt(res['sign']),
                    'per kernel: ' + '/'.join(str(v) for v in n.values()), res['aa_value'], res['D'], res['note']))
    return res


def a_b10(procs, ctx, step):
    used, out = integrity(procs)
    kernels = ('oldwrite', 'write', 'asmwrite', 'asmwrite2')
    out['settings'], rows, spreads = {}, [], {}
    for s in sorted({p.setting for p in used}):
        g = [p for p in used if p.setting == s]
        per_proc, aa_iv, missing = [], [], []
        for p in g:
            rec = dict(tag=p.tag)
            for k in kernels:
                ivs = p.rate_by_entry.get(k, [])
                if not ivs or any(iv.irregular for iv in ivs):
                    missing.append(dict(file=p.file, tag=p.tag, kernel=k, reason='irregular interval' if ivs else 'kernel not in the sequence'))
                    continue
                hi, lo = max(ivs, key=lambda iv: iv.hist), min(ivs, key=lambda iv: iv.hist)
                rec[k] = dict(spread=hi.hist - lo.hist, median_total=median(iv.hist for iv in ivs), median_total_M_sum=median(iv.msum for iv in ivs),
                              hi=hi.mesh_hist, lo=lo.mesh_hist)
            per_proc.append(rec)
            for r in range(p.rounds):                          # neighbouring intervals of the A/A pair
                for i in range(len(p.seq) - 1):
                    if {p.seq[i], p.seq[i + 1]} == {'asmwrite', 'asmwrite2'}:
                        x, y = p.iv[(r, i)], p.iv[(r, i + 1)]
                        if not (x.irregular or y.irregular):
                            a, a2 = (x, y) if x.entry == 'asmwrite' else (y, x)
                            aa_iv.append((a.mesh_hist, a2.mesh_hist))
        both = [r for r in per_proc if 'asmwrite' in r and 'asmwrite2' in r]
        for r in both:
            r['E'] = r['asmwrite2']['spread'] - r['asmwrite']['spread']
        ctrl_spread = max((abs(r['E']) for r in both), default=None)
        ctrl_total, ctrl_mesh = decide.controls_from_aa(aa_iv) if aa_iv else (None, (None, None))
        res = dict(n_processes=len(g), control_spread=ctrl_spread, control_total=ctrl_total, control_mesh0=ctrl_mesh[0], control_mesh1=ctrl_mesh[1],
                   n_aa_interval_pairs=len(aa_iv), values_missing=missing, kernels={})
        spreads[s] = {}
        for k in kernels:
            pk = [r for r in per_proc if k in r]
            spreads[s][k] = [dict(D=r[k]['spread'], E=r['E']) for r in pk if 'E' in r]
            h11p = [dict(hi=r[k]['hi'], lo=r[k]['lo']) for r in pk]
            if ctrl_total is None:
                h11, note = 'not observed', 'no regular neighbouring A/A intervals, so no control'
            else:
                h11, note = decide.decide_h11(h11p, ctrl_total, ctrl_mesh), ''
            res['kernels'][k] = dict(
                n_processes=len(pk), spreads=[r[k]['spread'] for r in pk], median_spread=med([r[k]['spread'] for r in pk]),
                median_total=med([r[k]['median_total'] for r in pk]), median_total_M_sum=med([r[k]['median_total_M_sum'] for r in pk]),
                H11=h11, H11_note=note,
                high_minus_low=[dict(total=sum(r[k]['hi']) - sum(r[k]['lo']), mesh0=r[k]['hi'][0] - r[k]['lo'][0], mesh1=r[k]['hi'][1] - r[k]['lo'][1]) for r in pk])
            rows.append(row('B10 %s %s: H11' % (s, k), h11, len(pk), ctrl_total, med([r[k]['spread'] for r in pk]),
                            'A/A value = control of the total; controls of mesh 0 and mesh 1: %s and %s; value = median spread. %s' % (fmt(ctrl_mesh[0]), fmt(ctrl_mesh[1]), note)))
        out['settings'][s] = res
    out['spread_changes'] = {}
    for factor, x, y in factor_pairs(list(spreads)):
        for k in kernels:
            word, change = decide.decide_change(spreads[x][k], spreads[y][k])
            cs = None if change is None else max(abs(v['E']) for v in spreads[x][k]) + max(abs(v['E']) for v in spreads[y][k])
            tx, ty = out['settings'][x]['kernels'][k]['median_total'], out['settings'][y]['kernels'][k]['median_total']
            note = 'a setting has fewer than 4 processes with a spread and a control' if word == 'not observed' else \
                'change of the median total (description, no rule): %s GB/s' % fmt(None if tx is None or ty is None else tx - ty)
            out['spread_changes']['%s %s: %s -> %s' % (k, factor, x, y)] = dict(
                kernel=k, factor=factor, first=x, second=y, decision=word, change_of_spread=change, sum_of_controls=cs,
                change_of_median_total=None if tx is None or ty is None else tx - ty, n_first=len(spreads[x][k]), n_second=len(spreads[y][k]), note=note)
            rows.append(row('B10 %s change of spread, %s: %s minus %s' % (k, factor, x, y), word,
                            '%d and %d' % (len(spreads[x][k]), len(spreads[y][k])), cs, change, note))
    out['rows'] = rows
    return out


def count_label(labels):
    return 'untested' if not labels else labels[0] if len(set(labels)) == 1 and labels[0] in ('split', 'uniform') else 'mixed'


def bracket(count_labels):
    """B8: count_labels = {mesh-1 threads: split | uniform | mixed | untested}. -> (x, y) or None.
    A bracket exists only if every tested count up to x is split, every tested count from y on is uniform,
    and the tested counts between them are mixed."""
    t = [(b, l) for b, l in sorted(count_labels.items()) if l != 'untested']
    i = 0
    while i < len(t) and t[i][1] == 'split':
        i += 1
    j = len(t)
    while j > 0 and t[j - 1][1] == 'uniform':
        j -= 1
    if i == 0 or j == len(t) or any(l != 'mixed' for _, l in t[i:j]):
        return None
    return t[i - 1][0], t[j][0]


def a_b8(procs, ctx, step):
    used, out = integrity(procs)
    rows, out['kernels'] = [], {}
    a_counts = sorted({p.threads_mesh0 for p in used}) if used else []
    out['mesh0_threads'] = a_counts
    for k in ('oldread', 'asmread', 'asmread2'):
        counts = {}
        for p in used:
            c = counts.setdefault(p.threads_mesh1, dict(labels=[], q=[], n_processes=0, left_out_irregular=0))
            c['n_processes'] += 1
            for iv in p.rate_by_entry.get(k, []):
                if iv.irregular:
                    c['left_out_irregular'] += 1
                else:
                    c['labels'].append(iv.pattern)
                    c['q'].append(round(iv.q, 4))
        for c in counts.values():
            c['label'] = count_label(c['labels'])
        br = bracket({b: c['label'] for b, c in counts.items()}) if len(a_counts) == 1 else None
        note = 'counts of mesh-1 threads and their labels: ' + ', '.join('%d %s' % (b, counts[b]['label']) for b in sorted(counts))
        if len(a_counts) > 1:
            note = 'the input has more than one count of mesh-0 threads (%s): no bracket is built. ' % a_counts + note
        out['kernels'][k] = dict(counts={b: counts[b] for b in sorted(counts)}, bracket=br, decision='bracket' if br else 'not resolved', note=note)
        rows.append(row('B8 %s: bracket of mesh-1 threads' % k, ('%d to %d' % br) if br else 'not resolved',
                        sum(c['n_processes'] for c in counts.values()), None, None, note + '; pattern labels need no A/A spread'))
    o, a = out['kernels']['oldread']['bracket'], out['kernels']['asmread']['bracket']
    out['H8'] = 'not resolved' if not o or not a else 'supported' if a[1] <= o[0] else 'contradicted' if o[1] <= a[0] else 'not resolved at this grid'
    rows.append(row('B8 H8: asm read changes at a lower count than old read', out['H8'], len(used), None, None, 'old read %s, asm read %s' % (o, a)))
    out['rows'] = rows
    return out


def a_b5(procs, ctx, step):
    used, out = integrity(procs)
    variants = [e for e in dict.fromkeys(e for p in used for e in p.seq) if e not in ('oldread', 'asmread2')]
    rows, out['variants'] = [], {}
    one = lambda p, e: p.rate_by_entry[e][0] if len(p.rate_by_entry.get(e, [])) == 1 else None
    old = {p.tag: one(p, 'oldread') for p in used}
    out['oldread_patterns'] = {t: (iv.pattern if iv and not iv.irregular else None) for t, iv in old.items()}
    out['oldread_q'] = {t: (round(iv.q, 4) if iv else None) for t, iv in old.items()}
    for v in variants:
        vals, missing = setting_values(used, 'oldread', v, 'asmread2', 'asmread')
        d = decide_d(vals, missing)
        pats = {}
        for p in used:
            iv, o = one(p, v), old[p.tag]
            pats[p.tag] = None if not iv or not o or iv.irregular or o.irregular else (iv.pattern, o.pattern)
        same = None if not pats or any(x is None for x in pats.values()) else all(x[0] == x[1] for x in pats.values())
        if d['decision'] == 'not observed' or same is None:
            shows, note = 'not observed', d['note'] or 'an interval of the variant or of old read is irregular or missing'
        else:
            # "yes" needs M_hist AND M_sum "not resolved". If the two metrics give another word or sign, the total
            # difference is neither shown nor excluded: the variant gets "not resolved", never "yes".
            shows = 'no' if not same else 'not resolved' if d['metrics_disagree'] else 'yes' if d['decision'] == 'not resolved' else 'no'
            note = 'pattern equal to old read in every process: %s; total difference old read minus variant: %s%s' % (
                'yes' if same else 'no', d['decision'], sign_txt(d['sign'])) + ('; ' + d['note'] if d['metrics_disagree'] else '')
        h = d['metrics']['M_hist']
        out['variants'][v] = dict(shows_pattern_and_total_of_oldread=shows, same_pattern=same, total_difference=d,
                                  patterns={t: (x[0] if x else None) for t, x in pats.items()}, note=note)
        rows.append(row('B5 %s shows the pattern and total of old read' % v, shows, h['n_processes'], h['aa_spread'], h['median_D'],
                        note + '; value = median of old read minus variant'))
    out['rows'] = rows
    return out


def a_b9(procs, ctx, step):
    """B9 (local rule): pattern of old read with one and with two buffers. The A/A value of the total is the
    largest difference between two processes of one kind."""
    used, out = integrity(procs)
    kinds, rows = {}, []
    for name, flag in (('one_buffer', False), ('two_buffers', True)):
        g = [p for p in used if p.two_buffers == flag]
        ivs = [iv for p in g for iv in p.ordered if not iv.irregular]
        pv = [median(iv.hist for iv in p.ordered) for p in g if not any(iv.irregular for iv in p.ordered)]
        kinds[name] = dict(n_processes=len(g), pattern=count_label([iv.pattern for iv in ivs]), q=[round(iv.q, 4) for iv in ivs],
                           process_values=pv, aa_value=(max(pv) - min(pv)) if len(pv) >= 2 else None)
    o, t = kinds['one_buffer'], kinds['two_buffers']
    pats = (o['pattern'], t['pattern'])
    if 'untested' in pats:
        word = 'not observed'
    elif pats[0] == pats[1] and pats[0] in ('split', 'uniform'):
        word = 'same pattern'
    elif pats == ('split', 'uniform'):
        word = 'pattern as H9a predicts'
    else:
        word = 'not resolved'
    out.update(kinds=kinds, pattern_result=word)
    rows.append(row('B9 pattern with one buffer and with two', word, '%d and %d' % (o['n_processes'], t['n_processes']), None, None,
                    'one buffer: %s, two buffers: %s; pattern labels need no A/A spread' % pats))
    if o['aa_value'] is None or t['aa_value'] is None:
        tot = dict(decision='not observed', difference=None, aa_value=None, note='2 processes of each kind are needed')
    else:
        diff, aa = median(o['process_values']) - median(t['process_values']), max(o['aa_value'], t['aa_value'])
        sep = max(o['process_values']) < min(t['process_values']) or min(o['process_values']) > max(t['process_values'])
        tot = dict(decision='resolved' if abs(diff) > aa and sep else 'not resolved', difference=diff, aa_value=aa, note='total with one buffer minus total with two (M_hist)')
    out['total'] = tot
    rows.append(row('B9 total rate, one buffer minus two', tot['decision'], '%d and %d' % (len(o['process_values']), len(t['process_values'])),
                    tot['aa_value'], tot['difference'], tot['note']))
    out['rows'] = rows
    return out


# ---------------------------------------------------------------- Part C and SHORT (description only)

EVENTS = ('cycles', 'instructions', 'l1d_refill', 'l2d_refill', 'll_read_miss')


def a_count(procs, ctx, step):
    """C1, C2, C3: counts per interval, kernel and thread. A row whose running time is below its enabled time is not used."""
    used, out = integrity(procs)
    groups, unused, total = {}, 0, 0
    for p in used:
        for c in p.C:
            total += 1
            iv = p.raw.get((c['round'], c['pos']))
            t = next((x for x in iv.rows if x['tid'] == c['tid']), None) if iv else None
            if t is None or None in (c['running'], c['enabled'], c['cputime']) or c['running'] < c['enabled'] or c['enabled'] <= 0 or c['cputime'] <= 0:
                unused += 1
                continue
            level = decide.level(iv.rate) if p.threads == 1 and p.entry_size(iv.entry) == 8 * MIB and iv.entry == REF else '-'
            mesh = '-' if p.threads == 1 else 'mesh0' if c['cpu'] in MESH0_CPUS else 'mesh1'
            group = p.setting if p.threads > 1 else 'cpu%s' % p.cpu
            if step == 'C3':                                    # C3 runs the B7 sequence and the B5 sequence: keep them apart
                group += ' B5 sequence' if 'read_sparse' in p.seq else ' B7 sequence'
            key = (group, iv.entry, level, mesh)
            g = groups.setdefault(key, dict({e: [] for e in EVENTS + ('clock_GHz', 'GBps')}, procs=set()))
            g['procs'].add(id(p))
            lines = t['bytes'] / 64.0
            cnt = dict(zip(EVENTS, c['counts'] + [None] * 5))
            if cnt['cycles'] is not None:
                g['clock_GHz'].append(cnt['cycles'] / c['cputime'])
            g['GBps'].append(t['bytes'] / t['elapsed'] / 1e9)
            for e in EVENTS:
                if cnt[e] is not None:
                    g[e].append(cnt[e] / lines)
    out['rows_C'], out['rows_C_not_used'] = total, unused
    out['groups'] = [dict(group=k[0], entry=k[1], level=k[2], mesh=k[3], n_rows=len(g['GBps']), n_processes=len(g['procs']), median_thread_GBps=med(g['GBps']),
                          median_clock_GHz=med(g['clock_GHz']), **{'median_%s_per_line' % e: med(g[e]) for e in EVENTS},
                          not_supported=[e for e in EVENTS if not g[e]]) for k, g in sorted(groups.items())]
    out['note'] = 'Description only, no decision. A line is 64 B of the bytes that the T row counts (a copy counts the bytes read plus the bytes written). ' \
                  'instructions per byte = median_instructions_per_line / 64.'
    out['rows'] = [row('%s %s %s level %s %s' % (step, g['group'], g['entry'], g['level'], g['mesh']), 'description', g['n_processes'], None, g['median_thread_GBps'],
                       '%d C rows (one per thread and interval); value = median rate of a thread; ' % g['n_rows'] +
                       'clock %s GHz; per line: instr %s, L1D refill %s, L2D refill %s, LL read miss %s' % tuple(
                           fmt(g[x], 4) for x in ('median_clock_GHz', 'median_instructions_per_line', 'median_l1d_refill_per_line',
                                                 'median_l2d_refill_per_line', 'median_ll_read_miss_per_line'))) for g in out['groups']]
    return out


def a_short(procs, ctx, step):
    """SHORT and unknown steps: no decision. One line per process, to check the output of bwx."""
    used, out = integrity(procs)
    out['processes'] = [dict(file=p.file, tag=p.tag, status=p.status, complete=p.complete, intervals=len(p.iv), expected=len(p.seq) * p.rounds,
                             I_rows=p.n_I, P_rows=len(p.P), P_rows_NA=sum(1 for x in p.P if x['kB_total'] is None), C_rows=len(p.C),
                             late_intervals=sum(1 for iv in p.iv.values() if not iv.problem and iv.late),
                             max_end_skew_ms=max((round(iv.skew * 1e3, 3) for iv in p.iv.values() if not iv.problem), default=None),
                             other_lines=p.other_lines, problems=p.problems[:5]) for p in procs]
    out['rows'] = [row('%s %s' % (step, x['tag']), 'complete' if x['complete'] else 'NOT complete', 1, None, None,
                       '%d of %d intervals, P rows %d (NA %d), C rows %d, late intervals %d, largest end skew %s ms %s' % (
                           x['intervals'], x['expected'], x['P_rows'], x['P_rows_NA'], x['C_rows'], x['late_intervals'], x['max_end_skew_ms'],
                           '; '.join(x['problems']))) for x in out['processes']]
    return out


ANALYZERS = dict(B1=a_copy, B2=a_copy, B3=a_copy, B4=a_b4, B6=a_b6, B7=a_b7, B10=a_b10, B8=a_b8, B5=a_b5, B9=a_b9,
                 C1=a_count, C2=a_count, C3=a_count)
ORDER = ['SHORT', 'B1', 'B2', 'B3', 'B4', 'B6', 'B7', 'B10', 'B8', 'B5', 'B9', 'C1', 'C2', 'C3']


# ---------------------------------------------------------------- the two sessions together

def two_sessions(flags):
    """flags: one per session: 'fail' (the bounded prediction failed), 'hold', 'not observed', 'not resolved'.
    'not resolved' is never a failure: with it the word is 'not rejected'.
    -> one of the words of rule 11 of the plan. 'rejected' needs the failure in at least 2 sessions and in all of them."""
    f = list(flags.values())
    if f and all(x == 'not observed' for x in f):
        return 'not observed'
    if len(f) < 2:
        return 'not rejected (one session only: "rejected" needs 2 sessions)' if f else 'not tested'
    return 'rejected' if all(x == 'fail' for x in f) else 'not rejected'


def cross(sessions):
    """Words for the hypotheses over all sessions. Each entry keeps the flag of every session."""
    out = {}

    def put(name, flags, basis):
        if flags:
            out[name] = dict(word=two_sessions(flags), per_session=flags, basis=basis)

    def per(step):
        return {s: r[step] for s, r in sessions.items() if step in r}

    b1 = per('B1')
    b1_low = {}
    for lab in ('low', 'high'):
        res = {s: r['groups'].get('8M', {}).get('labels', {}).get(lab) for s, r in b1.items()}
        res = {s: v for s, v in res.items() if v}
        signs = {v['sign'] for v in res.values()}
        flags = {s: 'fail' if v['decision'] == 'resolved' and len(signs) == 1 else 'not observed' if v['decision'] == 'not observed' else 'hold' for s, v in res.items()}
        put('H4 (B1, 8 MiB, label %s)' % lab, flags, 'H4 predicts no resolved difference copy - asmcopy inside one process; fail = resolved with one sign in all sessions')
        if lab == 'low':
            b1_low = res
    for s_name, v in (('asmcopy_c', 'H5 (B2, asmcopy_c, label low)'),):
        res = {s: r['groups'].get(s_name, {}).get('labels', {}).get('low') for s, r in per('B2').items()}
        flags = {}
        for s, x in res.items():
            if not x:
                continue
            ref = b1_low.get(s)
            flags[s] = 'not observed' if x['decision'] == 'not observed' or not ref or ref['sign'] is None else \
                'hold' if x['decision'] == 'resolved' and x['sign'] == ref['sign'] else 'fail'
        put(v, flags, 'H5 predicts a resolved difference asmcopy_c - asmcopy of the sign of B1; "not observed" also when B1 of the session has no resolved sign')
    flags = {}
    for s, r in per('B3').items():
        ch = [c for b in r['change_against_B1'].values() for c in b.values()]
        seen_all = r['change_against_B1'] and all(any(c['decision'] != 'not observed' for c in b.values()) for b in r['change_against_B1'].values())
        # Plan, step B3: "only after a resolved difference in B1". Without it there is no difference that an offset could change.
        b1_labels = b1.get(s, {}).get('groups', {}).get('8M', {}).get('labels', {})
        b1_resolved = any(v['decision'] == 'resolved' for v in b1_labels.values())
        flags[s] = 'not observed' if not b1_resolved or not seen_all or len(r['change_against_B1']) < 3 else \
            'hold' if any(c['decision'] == 'resolved' for c in ch) else 'fail'
    put('H6 (B3)', flags, 'H6 predicts a resolved change of d at one offset; fail = resolved on no CPU for all three builds; '
        'not observed = B1 at 8 MiB of the session has no resolved difference, or a build is missing or has no CPU with 3 processes of one label in B1 and in the build')
    b4 = per('B4')
    # The flag of a session comes from that session alone (plan, rule 10): a case on any CPU is a failed prediction there.
    # The word "rejected" also needs one CPU with a case in every session (handoff B.10, DEVIATIONS-scripts.md A13 and A32).
    with_case = {s: {c for c, v in r['per_cpu'].items() if v['cases']} for s, r in b4.items()}
    common = set.intersection(*with_case.values()) if with_case else set()
    flags = {s: 'fail' if c else 'not observed' for s, c in with_case.items()}
    if flags:
        any_cpu = two_sessions(flags)
        out['H3a (B4)'] = dict(
            word='not rejected' if any_cpu == 'rejected' and not common else any_cpu, per_session=flags,
            cpus_with_a_case={s: sorted(c) for s, c in with_case.items()}, cpus_with_a_case_in_every_session=sorted(common),
            word_without_the_same_cpu_condition=any_cpu,
            basis='fail = case (a) or (b) on a CPU of that session; "rejected" needs one CPU with a case in every session (such CPUs: %s; CPUs with a case: %s). '
                  'Without the same-CPU condition (plan, step B4) the word would be "%s"' % (
                      sorted(common), ', '.join('%s=%s' % (s, sorted(c)) for s, c in with_case.items()), any_cpu))
    b6 = per('B6')
    res6 = {s: {('state', c, 1 if v['difference'] > 0 else -1) for c, v in r['state'].items() if v['decision'] == 'resolved'} |
            ({('size', r['size']['labels']['none']['sign'])} if r['size']['labels']['none']['decision'] == 'resolved' else set()) for s, r in b6.items()}
    common6 = set.intersection(*res6.values()) if res6 else set()
    flags = {}
    for s, r in b6.items():
        nothing = all(v['decision'] == 'not observed' for v in r['state'].values()) and r['size']['labels']['none']['decision'] == 'not observed'
        flags[s] = 'not observed' if nothing else 'fail' if (common6 if len(b6) > 1 else res6[s]) else 'hold'
    put('H1 (B6)', flags, 'fail = a resolved difference (low against high on one CPU, or 8 MiB against 1 MiB); with 2 sessions the same result in both: %s. '
        'The two parts are reported apart in the tables of the step' % sorted(common6))
    b7 = per('B7')
    for hyp, factors in (('H7a (B7, read)', ('stop', 'interval')), ('H7b (B7, read)', ('start',))):
        flags = {}
        for s, r in b7.items():
            ch = [c for c in r['changes'].values() if c['factor'] in factors]
            seen = [c for c in ch if c['decision'] != 'not observed']
            # Plan, step B7: if the reproduction condition gives no resolved D in either way of running, no cause is assigned.
            flags[s] = 'not observed' if not seen or not r.get('reproduced_in_either_way') else \
                'hold' if any(c['decision'] == 'resolved' for c in seen) else \
                'not resolved' if any(c.get('metrics_disagree') for c in seen) else 'fail'
        put(hyp, flags, 'predicts a resolved change of D when %s changes; fail = no resolved change in any pair of settings, with M_hist and M_sum in agreement. '
            'not observed also when the reproduction condition (pass/500/common) gives no resolved D of the sign of 2026-11-13, '
            'neither with the kernels in one process nor with one kernel per process; '
            'not resolved = no resolved change, and M_hist and M_sum give another word or sign for a pair' % ' or '.join(factors))
    b10 = per('B10')
    for hyp, factors in (('H7a (B10, write)', ('stop', 'interval')), ('H7b (B10, write)', ('start',))):
        flags = {}
        for s, r in b10.items():
            seen = [c for c in r['spread_changes'].values() if c['factor'] in factors and c['decision'] != 'not observed']
            flags[s] = 'not observed' if not seen else 'hold' if any(c['decision'] == 'resolved' for c in seen) else 'fail'
        put(hyp, flags, 'predicts a resolved change of the spread of a kernel when %s changes; fail = no resolved change for any kernel and pair of settings' % ' or '.join(factors))
    keys = sorted({(st, k) for r in b10.values() for st, v in r['settings'].items() for k in v['kernels']})
    for st, k in keys:
        w = {s: r['settings'][st]['kernels'][k]['H11'] for s, r in b10.items() if st in r['settings'] and k in r['settings'][st]['kernels']}
        flags = {s: {'supported': 'hold', 'contradicted': 'fail', 'not observed': 'not observed'}.get(x, 'not resolved') for s, x in w.items()}
        word = two_sessions(flags)
        if len(w) > 1 and all(x == 'supported' for x in w.values()):
            word = 'not rejected (supported)'
        elif word == 'rejected':
            word = 'rejected (contradicted)'
        elif len(w) > 1 and word == 'not rejected':
            word = 'not resolved'
        out['H11 (B10, %s, %s)' % (st, k)] = dict(word=word, per_session=w, basis='decide.decide_h11 per session; the mesh that rose is not compared between sessions by this script')
    b8 = per('B8')
    if b8:
        w = {s: r['H8'] for s, r in b8.items()}
        word = 'not rejected (supported)' if len(w) > 1 and all(x == 'supported' for x in w.values()) else \
            'rejected (contradicted)' if len(w) > 1 and all(x == 'contradicted' for x in w.values()) else \
            'not resolved' if len(w) > 1 else 'one session only: %s' % list(w.values())[0]
        out['H8 (B8)'] = dict(word=word, per_session=w, basis='the bracket of asm read lies wholly below (supported) or wholly above (contradicted) the bracket of old read, in both sessions',
                              word_without_labels='not resolved', without_labels_basis='a bracket is built from the labels split and uniform')
    flags = {}
    for s, r in per('B5').items():
        v = r['variants'].get('read_sparse')
        olds = set(r['oldread_patterns'].values())
        flags[s] = 'not observed' if not v or v['shows_pattern_and_total_of_oldread'] == 'not observed' or olds != {'split'} else \
            'fail' if v['shows_pattern_and_total_of_oldread'] == 'yes' else \
            'not resolved' if v['shows_pattern_and_total_of_oldread'] == 'not resolved' else 'hold'
    put('B5 statement "vector adds are needed for the split pattern of old read"', flags,
        'fail = read_sparse shows the pattern and total of old read (total difference not resolved with M_hist and with M_sum); '
        'not observed also when old read is not split in every process; not resolved = same pattern, and M_hist and M_sum give another word or sign for the total')
    b5_name = 'B5 statement "vector adds are needed for the split pattern of old read"'
    if b5_name in out:
        # Without labels (A33) only the total can decide: a resolved difference old read - read_sparse under both metrics
        # means that read_sparse does not show the total of old read, whatever its pattern.
        nolab = {}
        for s, r in per('B5').items():
            d = (r['variants'].get('read_sparse') or {}).get('total_difference')
            nolab[s] = 'not observed' if not d or d['decision'] == 'not observed' else \
                'hold' if d['decision'] == 'resolved' and not d.get('metrics_disagree') else 'not resolved'
        out[b5_name].update(
            word_without_labels='not observed' if all(x == 'not observed' for x in nolab.values()) else
            'not rejected' if all(x == 'hold' for x in nolab.values()) else 'not resolved', per_session_without_labels=nolab,
            without_labels_basis='hold = old read - read_sparse is resolved with M_hist and with M_sum, so the total alone decides; otherwise the rule needs the label')
    flags = {s: {'same pattern': 'fail', 'pattern as H9a predicts': 'hold', 'not observed': 'not observed'}.get(r['pattern_result'], 'not resolved') for s, r in per('B9').items()}
    put('H9a (B9)', flags, 'fail = the same pattern with one buffer and with two')
    if 'H9a (B9)' in out:
        out['H9a (B9)'].update(word_without_labels='not resolved', without_labels_basis='the prediction is worded with the labels split and uniform')
    return out


LABEL_NOTE = ('The pattern labels split, mixed and uniform are NOT USED (user decision of 2026-11-13, decisions.md item 2: "Report q, no labels. '
              'Where a rule needs a label that the data do not give, the word is not resolved"). The tables of B8, B5 and B9 and the entries '
              'H8, H9a and the B5 statement still print what the provisional limits 0.65 and 0.85 give. Each such entry also carries its word without labels.')


def analyze(sessions):
    """sessions: {name: [Proc]} -> the summary (a dict that json can write)."""
    summary = dict(sessions={}, limits=[
        'No value here is the traffic of the time in which all threads ran: a thread records only its total (handoff B.10). Rule 6 of the plan is met only in part.',
        'Page state of a process with more than one thread: the reading for an interval is the reading after the interval before it; the warm-up pass lies between (handoff B.6).',
        'The limits 0.65 and 0.85 (pattern), 69 and 70.5 GB/s (level), 100 us and 5 ms (irregular interval) are provisional. Check the distributions (q and reference rates are in the json) before the labels are used.',
        'With --stop pass the end skew is reported and does not make an interval irregular (see DEVIATIONS-scripts.md).',
        LABEL_NOTE])
    for name, procs in sessions.items():
        res, ctx = {}, {}
        steps = {p.step for p in procs}
        for step in [s for s in ORDER if s in steps] + sorted(steps - set(ORDER)):
            g = [p for p in procs if p.step == step]
            if step == 'B8':
                for p in g:
                    cp = [x['cpu'] for iv in p.ordered[:1] for x in iv.rows]
                    p.threads_mesh0 = sum(1 for c in cp if c in MESH0_CPUS)
                    p.threads_mesh1 = len(cp) - p.threads_mesh0
            res[step] = ANALYZERS.get(step, a_short)(g, ctx, step)
        summary['sessions'][name] = res
    summary['hypotheses'] = cross(summary['sessions'])
    return summary


# ---------------------------------------------------------------- text output

def fmt(x, nd=2):
    return '-' if x is None else ('%.*f' % (nd, x)) if isinstance(x, float) else str(x)


def text_step(session, step, res):
    L = ['%s, session %s' % (step, session)]
    ld = res['load']
    L.append('system load: 1-minute load average %s to %s over the launches; longest wait for a quiet system %s s; logins %s' % (
        fmt(ld['loadavg_1min_min']), fmt(ld['loadavg_1min_max']), fmt(ld['waited_s_max']), ','.join(ld['logins'])))
    L.append('processes: %d in the files, %d used; P rows %d, of them with NA %d' % (res['n_processes'], res['n_used'], res['page_rows'], res['page_rows_NA']))
    for x in res['left_out']:
        L.append('  left out: %s %s: %s' % (x['file'], x['tag'], x['reason']))
    for x in res['irregular_intervals']:
        L.append('  irregular interval, not used: %s %s round %d pos %d %s, late threads %d, end skew %s ms' % (
            x['file'], x['tag'], x['round'], x['pos'], x['entry'], x['late_threads'], x['end_skew_ms']))
    head = ('what', 'decision', 'processes', 'A/A spread GB/s', 'value GB/s', 'note')
    rows = [(r['what'], r['decision'], str(r['n_processes']), fmt(r['aa_spread']), fmt(r['value']), r['note']) for r in res.get('rows', [])]
    w = [max(len(x[i]) for x in [head] + rows) for i in range(5)]
    for x in [head] + rows:
        L.append('  '.join(x[i].ljust(w[i]) for i in range(5)) + '  ' + x[5])
    for k in ('reproduction_in_one_process', 'H8', 'pattern_result', 'note'):
        if k in res:
            L.append('%s: %s' % (k, res[k]))
    if step in ('B8', 'B5', 'B9'):
        L.append('labels: ' + LABEL_NOTE)
    return '\n'.join(L) + '\n'


def text_hypotheses(summary):
    L = ['Hypotheses over all sessions (words of rule 11 of the plan; "rejected" needs 2 sessions)']
    for name, h in summary['hypotheses'].items():
        L.append('  %s: %s | per session: %s | %s' % (name, h['word'], ', '.join('%s=%s' % kv for kv in h['per_session'].items()), h['basis']))
        if 'word_without_labels' in h:
            L.append('      LABELS NOT USED (user decision of 2026-11-13): the word above is the output of the label rule. Without labels the word is "%s" (%s)' % (
                h['word_without_labels'], h['without_labels_basis']))
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='analysis of the bwx runs (handoff.md B.10)')
    ap.add_argument('--session', nargs='+', action='append', required=True, metavar=('NAME', 'PATH'))
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    sessions = {}
    for s in a.session:
        if len(s) < 2:
            ap.error('--session needs a name and at least one path')
        sessions.setdefault(s[0], []).extend(load_session(s[0], s[1:]))
    summary = analyze(sessions)
    texts = {}
    for name, res in summary['sessions'].items():
        for step, r in res.items():
            texts[step] = texts.get(step, '') + text_step(name, step, r) + '\n'
    texts['hypotheses'] = text_hypotheses(summary) + '\nLimits:\n' + '\n'.join('  - ' + x for x in summary['limits']) + '\n'
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, 'summary.json'), 'w') as fh:
            json.dump(summary, fh, indent=1, default=str)
        for step, t in texts.items():
            with open(os.path.join(a.out, step + '.txt'), 'w') as fh:
                fh.write(t)
    for t in texts.values():
        sys.stdout.write(t + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
