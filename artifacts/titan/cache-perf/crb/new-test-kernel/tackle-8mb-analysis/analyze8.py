#!/usr/bin/env python3
"""analyze8.py - analysis of the bwx8 runs of the design tackle-8mb.md.

Usage:
  analyze8.py summary FOLDER... [--margins FILE] -o summary.json
  analyze8.py forecast FOLDER... --use NAME [--use NAME...] -o margins.json

FOLDER is a result folder of run_bwx8.sh (all its *.csv files are read). The file formats and the fixed
readings of the rules are in DECISIONS-bwx8.md ("the contract"). "Design line N" is line N of tackle-8mb.md.

Words: a "process" is one start of bwx8 (one "-- step ..." line). A "trial" is one S row with its W, P and E
rows. A "unit" is the thing counted 6 times per CPU and session: a matched set of processes in Stage 2,
one process elsewhere. Rates are in GB/s (1 GB = 1e9 bytes), so a rate is bytes / nanoseconds.
A/A value = median(repeat 1, repeat 3) - median(repeat 2, repeat 4) of one process, condition and window.
A/A spread = the largest absolute A/A value over the processes of one CPU and session.
Limit of a contrast = the sum of the spreads of its constituent rates.

Every estimate is given twice: "filtered" (trials with a disturbed or coverage mark left out) and
"unfiltered" (every trial with valid accounting). Decisions use the filtered estimate.
Data with test=1 in its plan gives numbers and a banner, and no decision word.

Use names of the gates (one margin each, in margins.json):
  P3G                      prefix check of the paired-allocation branch (forecast from S2 folders)
  S3G                      prefix check of the mixed sequences (forecast from S2 folders)
  BIN:<kernel>@<size>      10 ms bins against window-only records (forecast from S2 folders)
  CS:<kernel>@<size>:<w>   size counters, w is first or fourth (forecast from S2 folders)
  CM:rate:<w>  CM:history:<w>  CM:interaction:<w>   mixed-sequence counters (forecast from S3 folders)
"""
import argparse, glob, json, math, os, sys
from collections import namedtuple
from statistics import median

MIB = 1 << 20
CPUS, SESSIONS, UNITS, REPS = (2, 41), (1, 2), 6, (1, 2, 3, 4)
OLD, NEW, ASM = 'oldread', 'read', 'asmread'
KERNELS = (OLD, NEW, ASM)
M1, M8, M16 = MIB, 8 * MIB, 16 * MIB
P1_MARGIN = 0.30            # GB/s, design line 80
P3_MARGIN = 0.30            # GB/s, design line 82
P3_COVERAGE = 2.0           # GB/s, design line 82
UNSTABLE = 0.30             # GB/s, design line 88
CPU_FRACTION = 0.99         # design line 276
GAP_NS = 100000             # 100 us, design line 276
# Involuntary context switches per second of trial wall time that a trial may have without the disturbed mark.
# 0 is the rule of design line 276 (any rise marks). The design calls its limits diagnostic proposals, so a
# host with a steady background count can set BWX8_NIVCSW_PER_S; the value must be fixed before rates are read.
NIVCSW_PER_S = float(os.environ.get('BWX8_NIVCSW_PER_S', '0'))
EPS_DIGITS = 9              # a sum is rounded to 1e-9 GB/s before it is compared with a margin (as in margin_for)
STEP_CHANGE = 0.30          # GB/s between two successive windows of a sustained trace (choice of this file)
WIN = {'first': ('target', 0), 'fourth': ('target', 3), 'prefix_last': ('prefix', 3)}
# quantity -> (spreads in the gate limit, lowest margin, highest margin), design lines 183 to 187
QUANT = {'one_rate': (2, 0.10, 0.30), 'two_rate': (4, 0.10, 0.30), 'four_rate': (8, 0.20, 0.60)}
MODES = ('closed', 'open', 'read')
MODE_PAIRS = (('open', 'closed'), ('read', 'open'), ('read', 'closed'))
SINGLE_KERNEL_STEPS = ('S2', 'S4', 'C4', 'BIN', 'CS')
GATE_STEPS = ('P3G', 'S3G', 'BIN', 'CS', 'CM')
# keys that hold a decision; they are emptied for test data
DECISION_KEYS = ('outcome', 'overall', 'passed', 'repeatable', 'sign', 'state', 'confirmed', 'confirmed_both',
                 'reproduced', 'candidate', 'word', 'statement', 'resolved', 'gate_passed', 'margin_forecast',
                 'forecast', 'all_slower', 'shares_why')
DECISION_PARTS = ('unstable', 'shares')    # emptied whatever their type: their content shows a decision
MODE_FAILURES = ('count_open', 'count_read', 'count_close')   # X codes: the counter mode of the plan did not run
BANNER = 'TEST DATA (test=1): the durations were divided, the rates mean nothing, no decision is given'
B6_PAIRS = ((7, 8), (10, 11))   # positions of the old-read A/A pairs after assembly read, counted from 0
B6_REF = (6, 9)                 # positions of the assembly read before each pair

Cond = namedtuple('Cond', 'prev pfx pred tgt count bins')


class GateError(Exception):
    """A gate cannot be evaluated with this margins file."""


class MixError(Exception):
    """A unit that must be one process holds more than one."""


def parse_size(s):
    mult = {'K': 10, 'M': 20, 'G': 30}.get(s[-1:])
    return int(s[:-1]) << mult if mult else int(s)


def size_name(n):
    return '%dM' % (n // MIB) if n % MIB == 0 else '%dK' % (n // 1024) if n % 1024 == 0 else str(n)


def spec(s):
    """'-' gives None. 'KERNEL@SIZE' or 'KERNEL@SIZE:MS' gives (kernel, bytes, ms or None)."""
    if s == '-':
        return None
    body, _, ms = s.partition(':')
    kernel, _, size = body.partition('@')
    return (kernel, parse_size(size), int(ms) if ms else None)


def num(s):
    return None if s == 'NA' else int(s)


def cell_key(cpu, session):
    return 'cpu%s/s%s' % (cpu, session)


# ---------------------------------------------------------------- parsing

class Trial:
    """One trial: its S row and the rows that follow it."""

    def __init__(self, f):
        self.n, self.cond, self.rep = int(f[1]), f[2], int(f[3])
        self.prev, self.pfx, self.pred, self.tgt = (spec(x) for x in f[4:8])
        self.nwin, self.win_ms, self.count, self.bins = int(f[8]), int(f[9]), f[10], int(f[11])
        self.prev_cond, self.prev_tgt = f[12], f[13]
        two = lambda x: x[:2] if x else None
        self.key = Cond(two(self.prev), two(self.pfx), two(self.pred), two(self.tgt), self.count, self.bins)
        self.W, self.B, self.C, self.P, self.E, self.X = {}, {}, {}, {}, None, []
        self.dup = []                        # rows that occur twice
        self.reject, self.disturbed, self.coverage, self.count_bad = [], [], [], []
        self.mode_bad = []                   # the counter mode that ran is not the mode of the plan

    def phases(self):
        return (('prev', self.prev, 1), ('prefix', self.pfx, 4), ('pred', self.pred, 1),
                ('target', self.tgt, self.nwin))

    def rate(self, win):
        w = self.W.get(WIN.get(win, win))
        return w['bytes'] / (w['t1'] - w['t0']) if w and w['t1'] > w['t0'] else None

    def usable(self, filtered):
        return not self.reject and not (filtered and (self.disturbed or self.coverage))

    def check(self, proc):
        """Fill the reject list and the marks (design lines 275 to 277)."""
        r = self.reject
        r.extend('%s row occurs twice' % d for d in self.dup)
        if self.E is None:
            r.append('interrupted: S row without E row')
            return
        want, last = [], None
        for phase, sp, n in self.phases():
            if sp:
                want.extend((phase, i, sp) for i in range(n))
        for phase, i, sp in want:
            w = self.W.get((phase, i))
            if w is None:
                r.append('window %s %d is missing' % (phase, i))
                continue
            if w['kernel'] != sp[0] or w['pass_bytes'] != sp[1]:
                r.append('window %s %d ran %s over %d bytes, the S row has %s over %d'
                         % (phase, i, w['kernel'], w['pass_bytes'], sp[0], sp[1]))
            if w['bytes'] <= 0 or w['pass_bytes'] <= 0 or w['bytes'] % w['pass_bytes']:
                r.append('window %s %d: %d bytes is not a whole number of passes' % (phase, i, w['bytes']))
            if w['t1'] <= w['t0'] or (last is not None and w['t0'] < last):
                r.append('window %s %d: timestamps are not in order' % (phase, i))
            last = w['t1']
        extra = set(self.W) - {(p, i) for p, i, _ in want}
        if extra:
            r.append('windows that the S row does not have: %s' % sorted(extra))
        for (widx, b), row in sorted(self.B.items()):
            w = self.W.get(('target', widx))
            before = self.B.get((widx, b - 1))
            if not w or row['bytes'] > w['bytes'] or row['t1'] > w['t1'] or (
                    before and (row['bytes'] < before['bytes'] or row['t1'] <= before['t1'])):
                r.append('bin %d of window %d does not fit its window' % (b, widx))
        for k in {x[0] for x in (self.prev, self.pfx, self.pred, self.tgt) if x} - set(proc.K):
            r.append('required record missing: K row of %s' % k)
        for when in ('pre', 'post'):
            if when not in self.P:
                r.append('required record missing: P row %s' % when)
        e = self.E
        if any(e[k] is None for k in ('wall_ns', 'cpu_ns', 'nvcsw', 'nivcsw')):
            r.append('required record missing: a field of the E row is NA')
        ran_old = any(x and x[0] == OLD for x in (self.prev, self.pfx, self.pred, self.tgt))
        if e['sink_ok'] == '0' or any(x[0] == 'sink' for x in self.X):
            r.append('the check of the old-read sink failed')
        elif ran_old and e['sink_ok'] != '1':
            r.append('required record missing: sink_ok of a trial that ran old read')
        if e['gap_ns'] is None and len(want) > self.nwin:
            first, before = self.W.get(('target', 0)), self.W.get(want[-self.nwin - 1][:2])
            e['gap_ns'] = first['t0'] - before['t1'] if first and before else None
            if e['gap_ns'] is None:
                r.append('required record missing: the gap before the target')
        if e['wall_ns'] and e['cpu_ns'] is not None and e['cpu_ns'] < CPU_FRACTION * e['wall_ns']:
            self.disturbed.append('thread CPU time is %.2f %% of the wall time' % (100.0 * e['cpu_ns'] / e['wall_ns']))
        if e['nivcsw'] and e['nivcsw'] > NIVCSW_PER_S * (e['wall_ns'] or 0) / 1e9:
            self.disturbed.append('%d involuntary context switches' % e['nivcsw'])
        if e['gap_ns'] is not None and e['gap_ns'] > GAP_NS:
            self.disturbed.append('gap before the target is %d ns' % e['gap_ns'])
        huge = [self.P.get(w, {}).get('kB_huge') for w in ('pre', 'post')]
        if None in huge:
            self.coverage.append('huge-page coverage is not readable')
        elif huge[0] != huge[1]:
            self.coverage.append('huge-page coverage changed from %d to %d kB' % tuple(huge))
        if e['count_state'] != self.count:
            self.count_bad.append('counter state is %s, the plan has %s' % (e['count_state'], self.count))
            self.mode_bad.append(self.count_bad[-1])
        self.mode_bad.extend('reported failure %s: %s' % (x[0], x[1]) for x in self.X + proc.X
                             if x[0] in MODE_FAILURES)
        self.count_bad.extend('reported failure %s: %s' % (x[0], x[1]) for x in self.X
                              if x[0].startswith('count'))

    def measured(self):
        """The measured values that the exclusion table shows."""
        e = self.E or {}
        frac = e['cpu_ns'] / e['wall_ns'] if e.get('wall_ns') and e.get('cpu_ns') is not None else None
        return dict(wall_ns=e.get('wall_ns'), cpu_ns=e.get('cpu_ns'), cpu_fraction=frac, nvcsw=e.get('nvcsw'),
                    nivcsw=e.get('nivcsw'), gap_ns=e.get('gap_ns'),
                    kB_huge_pre=self.P.get('pre', {}).get('kB_huge'),
                    kB_huge_post=self.P.get('post', {}).get('kB_huge'),
                    rate_first=self.rate('first'), rate_fourth=self.rate('fourth'))


class Proc:
    """One bwx8 process: its header line and its rows."""

    def __init__(self, folder, line, order):
        self.folder, self.header, self.order = folder, line, order
        tok = line.split()
        self.step = tok[2] if len(tok) > 2 else '?'
        self.head, self.args, i = {}, [], 3
        while i < len(tok):
            if tok[i] == 'args':
                self.args = tok[i + 1:]
                break
            n = 4 if tok[i] == 'loadavg' else 1
            self.head[tok[i]] = ' '.join(tok[i + 1:i + 1 + n])
            i += 1 + n
        self.tag = self.head.get('tag')
        self.status, self.end_line = 'ok', None           # ok, killed or failed
        self.M, self.plan, self.K, self.X = {}, {}, {}, []
        self.trials, self.intervals = {}, {}               # trial number -> Trial; (round, pos) -> old T row
        self.problems, self.reject = [], []
        self.session = self.cpu = self.proc = self.rep_set = self.one = None
        self.test, self.duplicate, self.preceding_kernel = False, False, None
        self.replaced_by = None                            # folder of the complete process that replaces this one

    def opt(self, name):
        return self.args[self.args.index(name) + 1] if name in self.args[:-1] else None

    def add(self, line):
        f = line.split(',')
        try:
            if f[0] == 'M':
                key, value = line.split(',', 2)[1:]
                (self.plan if key.startswith('plan.') else self.M)[key[5:] if key.startswith('plan.') else key] = value
            elif f[0] == 'K' and len(f) == 4:
                self.K[f[1]] = dict(address=f[2], mod64=int(f[3]))
            elif f[0] == 'S' and len(f) == 14:
                t = Trial(f)
                if t.n in self.trials:
                    self.trials[t.n].dup.append('S')
                else:
                    self.trials[t.n] = t
            elif f[0] == 'X':
                x = line.split(',', 3)
                (self.X if int(x[1]) < 0 else self.trials[int(x[1])].X).append((x[2], x[3] if len(x) > 3 else ''))
            elif f[0] == 'T' and len(f) == 13 and '--trial' not in self.args:
                k = (int(f[1]), int(f[2]))
                if k in self.intervals:
                    self.problems.append('T row of round %d position %d occurs twice' % k)
                self.intervals[k] = dict(kernel=f[3], cpu=int(f[5]), bytes=int(f[6]), elapsed=float(f[7]))
            elif f[0] in ('I', 'P', 'C') and '--trial' not in self.args:
                pass                                        # rows of the old interval mode that are not used here
            elif f[0] in ('P', 'W', 'B', 'C', 'E', 'TR'):
                self._trial_row(f, self.trials[int(f[1])])
            else:
                self.problems.append('row not understood: ' + line[:60])
        except (ValueError, IndexError, KeyError):
            self.problems.append('row not understood: ' + line[:60])

    def _trial_row(self, f, t):
        if f[0] == 'P' and len(f) == 9:
            if f[2] in t.P:
                t.dup.append('P ' + f[2])
            t.P[f[2]] = dict(zip(('kB_total', 'kB_huge', 'thp_fault_alloc', 'thp_fault_fallback',
                                  'thp_collapse_alloc', 'pgmigrate_success'), (num(x) for x in f[3:])))
        elif f[0] == 'W' and len(f) == 9:
            k = (f[2], int(f[3]))
            if k in t.W:
                t.dup.append('W %s %d' % k)
            t.W[k] = dict(kernel=f[4], pass_bytes=int(f[5]), bytes=int(f[6]), t0=int(f[7]), t1=int(f[8]))
        elif f[0] == 'B' and len(f) == 6:
            k = (int(f[2]), int(f[3]))
            if k in t.B:
                t.dup.append('B %d %d' % k)
            t.B[k] = dict(t1=int(f[4]), bytes=int(f[5]))
        elif f[0] == 'C' and len(f) >= 6:
            if int(f[2]) in t.C:
                t.dup.append('C %s' % f[2])
            t.C[int(f[2])] = dict(enabled=num(f[3]), running=num(f[4]), cputime=num(f[5]),
                                  counts=[num(x) for x in f[6:]])
        elif f[0] == 'E' and len(f) == 10:
            if t.E is not None:
                t.dup.append('E')
            t.E = dict(wall_ns=num(f[2]), cpu_ns=num(f[3]), nvcsw=num(f[4]), nivcsw=num(f[5]), gap_ns=num(f[6]),
                       max_boundary_gap_ns=num(f[7]), sink_ok=f[8], count_state=f[9])
        elif f[0] != 'TR':
            raise ValueError

    def finish(self):
        """Derive the identity of the process and check every trial."""
        hs, ps = self.head.get('session'), self.plan.get('session')
        if hs and ps and hs != ps:
            self.reject.append('session is %s in the header line and %s in the plan' % (hs, ps))
        s = ps or hs
        self.session = int(s) if s and s.isdigit() else None
        self.proc = self.plan.get('proc', self.head.get('idx'))
        self.rep_set = self.plan.get('rep_set')
        self.test = self.plan.get('test') == '1'
        cpus = {x for x in (self.M.get('cpu'), self.plan.get('cpu'), self.opt('--cpus')) if x is not None}
        self.cpu = int(min(cpus)) if cpus and all(x.isdigit() for x in cpus) else None
        if '--trial' not in self.args:
            return
        if len(cpus) > 1:
            self.reject.append('pinning: the CPU is not the same in the M row, the plan and the command: %s'
                               % sorted(cpus))
        if self.status == 'ok':
            if self.M.get('mode') != 'trial' or 'cpu' not in self.M:
                self.reject.append('required record missing: M rows of the trial mode')
            if self.problems:
                self.reject.append('the process has rows that are not understood')
            if self.M.get('ntrials', '').isdigit() and int(self.M['ntrials']) != len(self.trials):
                self.problems.append('%d trials, the M row has %s' % (len(self.trials), self.M['ntrials']))
        if any(x[0] == 'sink' for x in self.X):
            self.reject.append('the check of the old-read sink failed')
        if self.M.get('trace', '0') != '0':
            self.reject.append('trace run: rates are not used')
        ran = {x for t in self.trials.values() for x in (t.key.prev, t.key.pfx, t.key.pred, t.key.tgt) if x}
        if self.plan.get('kernel') and self.plan.get('size', '').isdigit():
            planned = (self.plan['kernel'], int(self.plan['size']))
            ran.add(planned)
        if self.step in SINGLE_KERNEL_STEPS:
            if len(ran) == 1:
                self.one = ran.pop()
            else:
                self.reject.append('mixing: %d kernel and size pairs in a process that must have one' % len(ran))
        if self.step == 'S2' and self.rep_set is None:
            self.reject.append('required record missing: plan.rep_set')
        labels, keys, reps = {}, {}, {}
        for t in self.trials.values():
            labels.setdefault(t.cond, set()).add(t.key)
            keys.setdefault(t.key, set()).add(t.cond)
            reps.setdefault((t.key, t.rep), []).append(t)
        for t in self.trials.values():
            t.check(self)
            if len(labels[t.cond]) > 1 or len(keys[t.key]) > 1:
                t.reject.append('the condition label and the fields of the S row do not agree')
            if t.rep not in REPS or len(reps[(t.key, t.rep)]) > 1:
                t.reject.append('repeat number %d is out of range or occurs twice' % t.rep)
            t.reject.extend(self.reject)

    def by_key(self, pattern):
        """Condition keys of this process that match the pattern (a dict of Cond fields)."""
        return sorted({t.key for t in self.trials.values()
                       if all(getattr(t.key, k) == v for k, v in pattern.items())}, key=repr)

    def ident(self):
        return dict(folder=self.folder, step=self.step, session=self.session, cpu=self.cpu, proc=self.proc,
                    tag=self.tag, status=self.status)


def read_folder(path):
    """All processes of one result folder, in file order."""
    name = os.path.basename(os.path.normpath(path))
    files = sorted(glob.glob(os.path.join(path, '*.csv')))
    if not files:
        raise SystemExit('no csv file in ' + path)
    procs = []
    for fn in files:
        cur = None
        with open(fn) as fh:
            for line in fh:
                line = line.rstrip('\n')
                cut = max(line.find('-- killed '), line.find('-- failed '))
                if cut >= 0:                 # the line may follow a row that the kill cut short
                    if cur:
                        cur.status, cur.end_line = line[cut + 3:cut + 9], line[cut:]
                    continue
                if line.startswith('-- step '):
                    cur = Proc(name, line, len(procs))
                    if procs and procs[-1].folder == name:
                        cur.preceding_kernel = procs[-1].plan.get('kernel')
                    procs.append(cur)
                elif cur and line and not line.startswith('#'):
                    cur.add(line)
    for p in procs:
        p.finish()
    return procs


def load(paths):
    """Read several folders. A process key that two complete processes share is refused for both.
    A process that did not end is replaced by a complete process with its key (a step that was stopped and
    continued with --from): its trials are rejected, so they stay in the exclusion table and enter no estimate."""
    procs = [p for path in paths for p in read_folder(path)]
    seen = {}
    for p in procs:
        if p.status == 'ok':
            seen.setdefault((p.step, p.session, p.cpu, p.proc), []).append(p)
    for group in seen.values():
        if len(group) > 1:
            for p in group:
                p.duplicate = True
                why = 'mixing: %d processes have the key step %s session %s cpu %s proc %s' % (
                    len(group), p.step, p.session, p.cpu, p.proc)
                p.reject.append(why)
                for t in p.trials.values():
                    t.reject.append(why)
    for p in procs:
        group = seen.get((p.step, p.session, p.cpu, p.proc))
        if p.status != 'ok' and group:
            p.replaced_by = group[0].folder
            for t in p.trials.values():
                t.reject.append('partial observation: the process did not end, the complete process of folder %s '
                                'replaces it' % p.replaced_by)
    return procs


def replacements(procs):
    """Every process that did not end and that a complete process with the same key replaces."""
    return [dict(p.ident(), replaced_by=p.replaced_by, trials=len(p.trials)) for p in procs if p.replaced_by]


def is_test(procs):
    return any(p.test for p in procs)


def exclusions(procs):
    """Every process that did not end, and every rejected or marked trial, with reason and measured values."""
    rows = []
    for p in procs:
        if p.status != 'ok':
            rows.append(dict(p.ident(), trial=None, kind='process ' + p.status, reasons=[p.end_line] + (
                ['replaced by the complete process with the same key in folder %s' % p.replaced_by]
                if p.replaced_by else [])))
        if p.reject:
            rows.append(dict(p.ident(), trial=None, kind='process rejected', reasons=list(p.reject)))
        notes = ['reported failure %s: %s' % x for x in p.X]
        if p.M.get('madvise_ok') == '0':
            notes.append('the page-policy request failed (madvise_ok is 0)')
        if notes or (p.problems and not p.reject):
            rows.append(dict(p.ident(), trial=None, kind='process reported', reasons=notes + p.problems))
        for n in sorted(p.trials):
            t = p.trials[n]
            for kind, why in (('rejected', t.reject), ('disturbed', t.disturbed), ('coverage change', t.coverage),
                              ('counts not interpreted', t.count_bad)):
                if why:
                    rows.append(dict(p.ident(), trial=n, cond=t.cond, rep=t.rep, kind=kind, reasons=list(why),
                                     measured=t.measured()))
    return rows


def counts_of(procs):
    """Trial counts per step: all, rejected, marked, and the two numbers that the estimates use."""
    out = {}
    for p in procs:
        c = out.setdefault(p.step, dict(processes=0, processes_not_ended=0, trials=0, rejected=0, disturbed=0,
                                        coverage_change=0, unfiltered=0, filtered=0))
        c['processes'] += 1
        c['processes_not_ended'] += p.status != 'ok'
        for t in p.trials.values():
            c['trials'] += 1
            c['rejected'] += bool(t.reject)
            c['disturbed'] += bool(t.disturbed) and not t.reject
            c['coverage_change'] += bool(t.coverage) and not t.reject
            c['unfiltered'] += t.usable(False)
            c['filtered'] += t.usable(True)
    return out


# ---------------------------------------------------------------- the shared repeatability rule

def cell_rate(proc, pattern, win, filtered):
    """R and the A/A value of one process, condition and window. R needs all 4 repeats."""
    keys = proc.by_key(pattern)
    if len(keys) != 1:
        return dict(R=None, aa=None, reps={}, why='%d conditions match %s' % (len(keys), pattern))
    reps, mode = {}, 0
    for t in proc.trials.values():
        if t.key != keys[0]:
            continue
        if 'count' in pattern and t.mode_bad:       # a comparison of counter modes needs the mode of the plan
            mode += 1
        elif t.usable(filtered) and t.rate(win) is not None:
            reps[t.rep] = t.rate(win)
    if sorted(reps) != list(REPS):
        return dict(R=None, aa=None, reps=reps, why='%d of 4 trials usable' % len(reps) + (
            ' (%d did not run the counter mode of the plan)' % mode if mode else ''))
    v = [reps[i] for i in REPS]
    return dict(R=median(v), aa=(v[0] + v[2]) / 2 - (v[1] + v[3]) / 2, reps=reps, why=None)


def stats(values):
    v = [x for x in values if x is not None]
    if not v:
        return dict(n=0, median=None, min=None, max=None, range=None)
    return dict(n=len(v), median=median(v), min=min(v), max=max(v), range=max(v) - min(v))


def contrast(units, terms, filtered=True, label=None, one_process=False):
    """Apply the rule of design lines 261 to 264 to one contrast.

    units: list of dict(id, procs={role: Proc}, bad=reason or None, bad_roles={role: reason}). 'bad' refuses
    the unit for every contrast. 'bad_roles' refuses it only for a contrast that uses one of these roles.
    terms: list of (coefficient, role, condition pattern, window). Each term is one constituent rate.
    """
    if one_process and any(len({id(p) for p in u['procs'].values()}) > 1 for u in units):
        raise MixError('a unit that must be one process holds several processes')
    rows, aas = [], [[] for _ in terms]
    for u in units:
        row = dict(unit=u['id'], value=None, why=u.get('bad'), rates=[None] * len(terms))
        if not row['why']:
            whys = []
            for i, (coef, role, pattern, win) in enumerate(terms):
                p = u['procs'].get(role)
                if role in u.get('bad_roles', {}):
                    c = dict(R=None, aa=None, why=u['bad_roles'][role])
                else:
                    c = cell_rate(p, pattern, win, filtered) if p else dict(R=None, aa=None,
                                                                             why='no process for %s' % (role,))
                row['rates'][i] = c['R']
                if c['aa'] is not None:
                    aas[i].append(abs(c['aa']))
                if c['why']:
                    whys.append(c['why'])
            if whys:
                row['why'] = '; '.join(sorted(set(whys)))
            else:
                row['value'] = sum(t[0] * r for t, r in zip(terms, row['rates']))
        rows.append(row)
    spreads = [max(a) if a else None for a in aas]
    limit = sum(spreads) if None not in spreads else None
    out = dict(label=label, n_terms=len(terms), units=rows, n_units=len(units), spreads=spreads, limit=limit,
               trials_required=4 * len(terms) * UNITS)
    out.update(stats(r['value'] for r in rows))
    out['n_valid'] = out.pop('n')
    out['trials_used'] = 4 * len(terms) * out['n_valid']
    out['complete'] = len(units) == UNITS and out['n_valid'] == UNITS and limit is not None
    out['repeatable'] = out['sign'] = None
    if not out['complete']:
        out['state'] = 'incomplete'
        return out
    v, med = [r['value'] for r in rows], out['median']
    one_sign = all(x > 0 for x in v) or all(x < 0 for x in v)     # a value of exactly 0 has no sign
    out['repeatable'] = abs(med) > limit and one_sign
    out['sign'] = (1 if med > 0 else -1) if out['repeatable'] else None
    out['state'] = ('repeatable' if out['repeatable'] else
                    'not distinguished from variation' if abs(med) <= limit else 'signs differ between units')
    return out


def add_gain(res):
    """For a contrast a - b: the percentage gain 100 x (a / b - 1) of every unit."""
    g = []
    for row in res['units']:
        a, b = row['rates'][:2]
        row['gain_pct'] = 100.0 * (a / b - 1) if row['value'] is not None and b else None
        g.append(row['gain_pct'])
    res['gain_pct'] = stats(g)
    return res


def both(units, terms, label=None, one_process=False, gain=False):
    out = {}
    for name, f in (('filtered', True), ('unfiltered', False)):
        out[name] = contrast(units, terms, f, label, one_process)
        if gain:
            add_gain(out[name])
    return out


def rate_table(units, role, pattern, win):
    """The six rates of one condition and window, without a decision."""
    out = {}
    for name, f in (('filtered', True), ('unfiltered', False)):
        c = contrast(units, [(1, role, pattern, win)], f)
        out[name] = dict(units=[dict(unit=r['unit'], rate=r['value'], why=r['why']) for r in c['units']],
                         spread=c['spreads'][0], n_valid=c['n_valid'], median=c['median'], min=c['min'],
                         max=c['max'], range=c['range'])
    return out


def confirm(cells):
    """cells: {(cpu, session): filtered contrast}. Design line 265."""
    per = {}
    for cpu in sorted({k[0] for k in cells}):
        s = [cells.get((cpu, x)) for x in SESSIONS]
        ok = all(r is not None and r['repeatable'] for r in s) and s[0]['sign'] == s[1]['sign']
        per[cpu] = dict(confirmed=bool(ok), sign=s[0]['sign'] if ok else None)
    ok = all(c in per and per[c]['confirmed'] for c in CPUS) and len({per[c]['sign'] for c in CPUS}) == 1
    return dict(per_cpu={'cpu%s' % c: v for c, v in per.items()}, confirmed_both=bool(ok),
                sign=per[CPUS[0]]['sign'] if ok else None)


def cells_of(procs, step):
    return sorted({(p.cpu, p.session) for p in procs
                   if p.step == step and p.cpu is not None and p.session is not None})


def proc_units(procs, step, cpu, session, one=None):
    """Units of one process each, in the order of the schedule."""
    ps = [p for p in procs if p.step == step and p.cpu == cpu and p.session == session
          and (one is None or p.one == one) and not p.replaced_by]
    ps.sort(key=lambda p: (int(p.proc) if str(p.proc).isdigit() else 0, p.order))
    return [dict(id=p.proc, procs={None: p}, bad=None) for p in ps]


# ---------------------------------------------------------------- Stage 2

def s2_units(procs, cpu, session, sizes):
    """Matched sets: the processes with one rep_set, per (kernel, size) role."""
    sets = {}
    for p in procs:
        if p.step == 'S2' and p.cpu == cpu and p.session == session and p.one and p.one[1] in sizes \
                and p.rep_set is not None and (p.status == 'ok' or p.trials) and not p.replaced_by:
            sets.setdefault(p.rep_set, {}).setdefault(p.one, []).append(p)
    units = []
    for r in sorted(sets, key=lambda x: (len(x), x)):
        u = dict(id=r, procs={}, bad=None, bad_roles={})
        for role, ps in sets[r].items():
            if len(ps) > 1:                  # only the contrasts that use this kernel and size lose the set
                u['bad_roles'][role] = 'mixing: %d processes for %s at %s in one matched set' % (
                    len(ps), role[0], size_name(role[1]))
            u['procs'][role] = ps[0]
        units.append(u)
    return units


def term(kernel, size, win, coef=1):
    return (coef, (kernel, size), {'tgt': (kernel, size)}, win)


def p1_cell(res):
    """P1 on one CPU and session, from the contrast old 8 MiB minus old 1 MiB (contract, 'P1')."""
    lim = res['limit']
    worst = [abs(r['value']) + lim for r in res['units'] if r['value'] is not None and lim is not None]
    if res['complete'] and round(max(worst), EPS_DIGITS) <= P1_MARGIN:
        word = 'equivalent'
    elif res['repeatable'] and abs(res['median']) > P1_MARGIN:
        word = 'contradicted'
    else:
        word = 'undecided'
    return dict(outcome=word, margin=P1_MARGIN, limit=lim, abs_plus_limit=worst,
                largest_abs_plus_limit=max(worst) if worst else None, complete=res['complete'],
                median=res['median'], sign=res['sign'])


def decomposition(units, w='fourth'):
    """dG = (new_1 - new_8) - (old_1 - old_8) with both terms. Shares only when dG is repeatable."""
    out = {}
    for name, f in (('filtered', True), ('unfiltered', False)):
        dg = contrast(units, [term(NEW, M1, w), term(NEW, M8, w, -1), term(OLD, M1, w, -1), term(OLD, M8, w)],
                      f, 'dG')
        tn = contrast(units, [term(NEW, M1, w), term(NEW, M8, w, -1)], f, 'new_1 - new_8')
        to = contrast(units, [term(OLD, M1, w), term(OLD, M8, w, -1)], f, 'old_1 - old_8')
        d = dict(dG=dg, new_term=tn, old_term=to, resolved=dg['repeatable'], shares=None,
                 shares_why='dG is not resolved, so no share is given')
        if dg['repeatable']:
            sets = [dict(unit=a['unit'], new_share_pct=100.0 * b['value'] / a['value'],
                         old_share_pct=-100.0 * c['value'] / a['value'])
                    for a, b, c in zip(dg['units'], tn['units'], to['units'])]
            d['shares'] = dict(units=sets, new_share_pct=stats(s['new_share_pct'] for s in sets),
                               old_share_pct=stats(s['old_share_pct'] for s in sets))
            d['shares_why'] = None
        out[name] = d
    return out


def crossing(at8, at16):
    """Load-only minus old read at 8 and 16 MiB: has the sign changed?"""
    out = dict(change=None)
    for name, r in (('8M', at8), ('16M', at16)):
        m = r and r['median']
        out[name] = dict(median=m, median_sign=None if m is None else (m > 0) - (m < 0),
                         repeatable=r['repeatable'] if r else None, limit=r and r['limit'])
    if at8 and at16 and at8['complete'] and at16['complete']:
        out['change'] = at16['median'] - at8['median']
        if at8['repeatable'] and at16['repeatable']:
            out['word'] = 'crossed between 8 and 16 MiB' if at8['sign'] != at16['sign'] else 'not crossed'
        else:
            out['word'] = 'not resolved'
    else:
        out['word'] = 'incomplete'
    return out


def stage2(procs):
    s2 = [p for p in procs if p.step == 'S2']
    sizes = sorted({p.one[1] for p in s2 if p.one})
    out = dict(cells={}, sizes=[size_name(s) for s in sizes], processes=[])
    p1, p2, conf = {}, {NEW: {}, ASM: {}}, {}
    for cpu, ses in cells_of(procs, 'S2'):
        c = dict(cpu=cpu, session=ses, sizes={})
        for size in sizes:
            U = s2_units(s2, cpu, ses, [size])
            z = dict(rates={k: {w: rate_table(U, (k, size), {'tgt': (k, size)}, w) for w in ('fourth', 'first')}
                            for k in KERNELS})
            for name, k in (('new_minus_old', NEW), ('asm_minus_old', ASM)):
                z[name] = {w: both(U, [term(k, size, w), term(OLD, size, w, -1)], name, gain=True)
                           for w in ('fourth', 'first')}
                conf.setdefault('%s@%s' % (name, size_name(size)), {})[(cpu, ses)] = z[name]['fourth']['filtered']
            c['sizes'][size_name(size)] = z
        if M1 in sizes and M8 in sizes:
            U = s2_units(s2, cpu, ses, [M1, M8])
            c['P1_contrast'] = both(U, [term(OLD, M8, 'fourth'), term(OLD, M1, 'fourth', -1)], 'old 8M - old 1M')
            c['P1'] = {n: p1_cell(r) for n, r in c['P1_contrast'].items()}
            p1[(cpu, ses)] = c['P1']['filtered']
            c['P2'] = {}
            for k in (NEW, ASM):
                c['P2'][k] = both(U, [term(k, M8, 'fourth'), term(k, M1, 'fourth', -1)], '%s 8M - %s 1M' % (k, k))
                p2[k][(cpu, ses)] = c['P2'][k]['filtered']
            c['size_contrast'] = both(U, [term(NEW, M8, 'fourth'), term(OLD, M8, 'fourth', -1),
                                          term(NEW, M1, 'fourth', -1), term(OLD, M1, 'fourth')],
                                      '(new - old at 8M) - (new - old at 1M)')
            conf.setdefault('size_contrast', {})[(cpu, ses)] = c['size_contrast']['filtered']
            c['decomposition'] = decomposition(U)
        z8, z16 = c['sizes'].get('8M'), c['sizes'].get('16M')
        if z8:
            c['crossing'] = {k: crossing(z8[n]['fourth']['filtered'], z16 and z16[n]['fourth']['filtered'])
                             for n, k in (('new_minus_old', NEW), ('asm_minus_old', ASM))}
            c['range_8M'] = {k: {n: {x: t[x] for x in ('n_valid', 'median', 'min', 'max', 'range')}
                                 for n, t in z8['rates'][k]['fourth'].items()} for k in KERNELS}
            c['sentence'] = sentence(s2, cpu, ses, z8)
        out['cells'][cell_key(cpu, ses)] = c
    for p in sorted(s2, key=lambda p: (p.folder, p.order)):
        out['processes'].append(dict(p.ident(), rep_set=p.rep_set, kernel=p.one and p.one[0],
                                     size=p.one and p.one[1], preceding_kernel=p.preceding_kernel,
                                     load=p.head.get('loadavg'),
                                     fourth=[p.trials[n].rate('fourth') if p.trials[n].usable(False) else None
                                             for n in sorted(p.trials)]))
    # P1 per CPU and overall (contract, 'P1')
    per = {}
    for cpu in sorted({k[0] for k in p1}):
        s = [p1.get((cpu, x)) for x in SESSIONS]
        words = [r['outcome'] if r else None for r in s]
        if words == ['equivalent'] * 2:
            w = 'equivalent'
        elif words == ['contradicted'] * 2 and s[0]['sign'] == s[1]['sign']:
            w = 'contradicted'
        else:
            w = 'undecided'
        per['cpu%s' % cpu] = dict(outcome=w)
    cells_ok = all(p1.get((c, s), {}).get('outcome') == 'equivalent' for c in CPUS for s in SESSIONS)
    out['P1'] = dict(per_cpu=per, overall='meets its equivalence margin' if cells_ok
                     else 'does not meet its equivalence margin')
    out['P2'] = {}
    for k in (NEW, ASM):
        cf = confirm(p2[k])
        for v in cf['per_cpu'].values():
            v['outcome'] = ('undecided' if not v['confirmed'] else 'supported' if v['sign'] < 0 else 'contradicted')
        out['P2'][k] = cf
    out['confirm'] = {name: confirm(c) for name, c in sorted(conf.items())}
    # design line 218
    p2w = [out['P2'][k]['per_cpu'].get('cpu%s' % c, {}).get('outcome') for k in (NEW, ASM) for c in CPUS]
    if cells_ok and p2w == ['supported'] * 4:
        out['candidate'] = 'supported'
    elif 'contradicted' in p2w or any(v['outcome'] == 'contradicted' for v in per.values()):
        out['candidate'] = 'contradicted'
    else:
        out['candidate'] = 'undecided'
    return out


def sentence(s2, cpu, ses, z8):
    """The values of the result sentence of design line 222, from the filtered 8 MiB estimate."""
    old, new = (z8['rates'][k]['fourth']['filtered'] for k in (OLD, NEW))
    gain = z8['new_minus_old']['fourth']['filtered']['gain_pct']
    prep = sorted({'%s@%s for %s ms' % (t.pfx[0], size_name(t.pfx[1]), t.pfx[2]) for p in s2
                   for t in p.trials.values()
                   if p.cpu == cpu and p.session == ses and p.one and p.one[1] == M8 and t.pfx})
    d = dict(preparation='same-kernel prefix ' + ' / '.join(prep), old_GBps=old['median'], new_GBps=new['median'],
             gain_pct=gain['median'], gain_pct_min=gain['min'], gain_pct_max=gain['max'],
             n_sets=gain['n'], text=None)
    if None not in (d['old_GBps'], d['new_GBps'], d['gain_pct']):
        d['text'] = ('Under preparation "%s" on CPU %s in session %s, old read was %.2f GB/s and new read was '
                     '%.2f GB/s at 8 MiB (medians of %d and %d processes). The gain was %.2f %% (median of %d '
                     'matched sets, range %.2f to %.2f %%).'
                     % (d['preparation'], cpu, ses, d['old_GBps'], d['new_GBps'], old['n_valid'], new['n_valid'],
                        d['gain_pct'], d['n_sets'], d['gain_pct_min'], d['gain_pct_max']))
    return d


# ---------------------------------------------------------------- P3

def p3_process(p, filtered):
    """Per kernel: the trial rates, the median, the instability mark, and the A/A value."""
    row = dict(proc=p.proc, kernels={})
    for k in KERNELS:
        c4 = cell_rate(p, {'tgt': (k, M8)}, 'fourth', filtered)
        c1 = cell_rate(p, {'tgt': (k, M8)}, 'first', filtered)
        d = dict(fourth=c4['reps'], first=c1['reps'], median=c4['R'], aa=c4['aa'], unstable=None, why=c4['why'])
        if c4['R'] is not None:
            span = max(c4['reps'].values()) - min(c4['reps'].values())
            drift = max(abs(c1['reps'][r] - c4['reps'][r]) for r in REPS)
            d.update(span=span, first_fourth=drift, unstable=span > UNSTABLE or drift > UNSTABLE)
        row['kernels'][k] = d
    return row


def p3_decide(rows, x, gate_passed):
    """One P3 comparison, selected by load-only kernel x. rows are in the order of the schedule."""
    out = dict(kernel=x, outcome='Insufficient data', why=None, n_processes=len(rows))
    xm = [r['kernels'][x]['median'] for r in rows]
    om = [r['kernels'][OLD]['median'] for r in rows]
    aa = [r['kernels'][OLD]['aa'] for r in rows]
    full = len(rows) == UNITS and None not in xm + om
    out['unstable'] = [r['proc'] for r in rows if r['kernels'][x]['unstable'] or r['kernels'][OLD]['unstable']]
    if full:
        hi, lo = xm.index(max(xm)), xm.index(min(xm))            # index() takes the earlier process on a tie
        out.update(load_range=max(xm) - min(xm), old_range=max(om) - min(om),
                   control_limit=2 * max(abs(a) for a in aa),
                   endpoint_max=rows[hi]['proc'], endpoint_min=rows[lo]['proc'], old_endpoint_change=om[hi] - om[lo])
    if gate_passed is not True:
        out['why'] = 'the prefix gate P3G ' + ('did not pass' if gate_passed is False else 'was not evaluated')
    elif not full:
        out['why'] = 'fewer than 6 processes with all trials for %s and old read' % x
    elif out['unstable']:
        out['why'] = 'unstable process trace: process %s' % ', '.join(map(str, out['unstable']))
    elif out['load_range'] < P3_COVERAGE:
        out['why'] = 'load-only range %.3f GB/s is below %.1f GB/s' % (out['load_range'], P3_COVERAGE)
    elif round(out['old_range'] + out['control_limit'], EPS_DIGITS) <= P3_MARGIN:
        out['outcome'] = 'compatible'
    elif round(abs(out['old_endpoint_change']) - out['control_limit'], EPS_DIGITS) > P3_MARGIN:
        out['outcome'] = 'contrary'
    else:
        out['outcome'] = 'undecided'
    return out


def p3(procs, gate_passed=None):
    """gate_passed: True, False, or None when the gate P3G was not evaluated."""
    out = dict(cells={}, gate_passed=gate_passed)
    for cpu, ses in cells_of(procs, 'P3'):
        c = dict(cpu=cpu, session=ses)
        for name, f in (('filtered', True), ('unfiltered', False)):
            rows = [p3_process(u['procs'][None], f) for u in proc_units(procs, 'P3', cpu, ses)]
            c[name] = dict(processes=rows, **{x: p3_decide(rows, x, gate_passed) for x in (NEW, ASM)})
        out['cells'][cell_key(cpu, ses)] = c
    return out


# ---------------------------------------------------------------- Stage 3

PRED = {'old': (OLD, M8), 'new': (NEW, M8), 'asm': (ASM, M8), 'old1M': (OLD, M1)}
TGT = {'old': OLD, 'new': NEW, 'asm': ASM}


def r3(t, p, w, coef=1, count=None):
    """The term R(T | P, w) of design line 249."""
    pattern = {'pred': PRED[p], 'tgt': (TGT[t], M8)}
    if count:
        pattern['count'] = count
    return (coef, None, pattern, w)


def interaction(w, a='new', count=None, coef=1):
    """G(a, w) - G(old, w), with G(P, w) = R(new | P, w) - R(old | P, w)."""
    return [r3('new', a, w, coef, count), r3('old', a, w, -coef, count),
            r3('new', 'old', w, -coef, count), r3('old', 'old', w, coef, count)]


def previous_target(procs, cpu, ses, step='S3'):
    """Per target and window: the trial rate minus the median of its own process and condition,
    grouped by the target of the previous trial (design line 179). Descriptive."""
    dev = {}
    for p in procs:
        if p.step != step or p.cpu != cpu or p.session != ses:
            continue
        for key in p.by_key({}):
            ts = [t for t in p.trials.values() if t.key == key and t.usable(False)]
            for w in ('first', 'fourth'):
                rates = [(t, t.rate(w)) for t in ts if t.rate(w) is not None]
                if len(rates) < 2:
                    continue
                m = median(r for _, r in rates)
                for t, r in rates:
                    prev = t.prev_tgt.split('@')[0]
                    dev.setdefault((key.tgt[0], w), {}).setdefault(prev, []).append(r - m)
    out = {}
    for (k, w), groups in sorted(dev.items()):
        g = {prev: dict(n=len(v), median_deviation=median(v)) for prev, v in sorted(groups.items())}
        meds = [x['median_deviation'] for x in g.values()]
        out.setdefault(k, {})[w] = dict(by_previous_target=g, span=max(meds) - min(meds))
    return out


def stage3(procs):
    out, conf = dict(cells={}), {}
    for cpu, ses in cells_of(procs, 'S3'):
        U = proc_units(procs, 'S3', cpu, ses)
        c = dict(cpu=cpu, session=ses, primary={}, exploratory=[], gain_pct={}, R={})
        for w in ('first', 'fourth'):
            named = (('new_predecessor_on_old', [r3('old', 'new', w), r3('old', 'old', w, -1)]),
                     ('asm_predecessor_on_old', [r3('old', 'asm', w), r3('old', 'old', w, -1)]),
                     ('history_interaction', interaction(w)))
            for name, terms in named:
                res = both(U, terms, name, one_process=True)
                c['primary'].setdefault(name, {})[w] = res
                conf.setdefault((name, w), {})[(cpu, ses)] = res['filtered']
            for pn in PRED:
                c['gain_pct'].setdefault(pn, {})[w] = both(U, [r3('new', pn, w), r3('old', pn, w, -1)],
                                                           'G(%s, %s)' % (pn, w), True, gain=True)
                for tn in TGT:
                    c['R'].setdefault('%s|%s' % (tn, pn), {})[w] = rate_table(
                        U, None, {'pred': PRED[pn], 'tgt': (TGT[tn], M8)}, w)
                    if pn != 'old' and (tn, pn) not in (('old', 'new'), ('old', 'asm')):
                        res = both(U, [r3(tn, pn, w), r3(tn, 'old', w, -1)],
                                   'exploratory: R(%s|%s,%s) - R(%s|old,%s)' % (tn, pn, w, tn, w), True)
                        c['exploratory'].append(res)
            for pn in ('asm', 'old1M'):
                c['exploratory'].append(both(U, interaction(w, pn),
                                             'exploratory: G(%s,%s) - G(old,%s)' % (pn, w, w), True))
        # Design line 222: the change in gain in percentage points, per process, against the old predecessor.
        c['gain_change_pp'] = {}
        for pn in PRED:
            if pn == 'old':
                continue
            for w in ('first', 'fourth'):
                d = {}
                for name in ('filtered', 'unfiltered'):
                    x, y = (c['gain_pct'][q][w][name]['units'] for q in (pn, 'old'))
                    v = [None if None in (i['gain_pct'], j['gain_pct']) else i['gain_pct'] - j['gain_pct']
                         for i, j in zip(x, y)]
                    d[name] = dict(units=v, **stats(v))
                c['gain_change_pp'].setdefault(pn, {})[w] = d
        c['previous_target'] = previous_target(procs, cpu, ses)
        out['cells'][cell_key(cpu, ses)] = c
    out['confirm'] = {}
    for (name, w), cells in sorted(conf.items()):
        out['confirm'].setdefault(name, {})[w] = confirm(cells)
    return out


# ---------------------------------------------------------------- gates

def margin_for(L0, quantity):
    """Design line 189: twice L0, rounded up to the next 0.05 GB/s, clipped to the bounds of the quantity."""
    _, lo, hi = QUANT[quantity]
    raw = math.ceil(round(2 * L0 / 0.05, 9)) * 0.05
    m = round(min(max(raw, lo), hi), 2)
    return dict(L0=L0, quantity=quantity, spreads=QUANT[quantity][0], unclipped=round(raw, 2), margin=m,
                clipped=m != round(raw, 2),
                forecast='precision insufficient' if L0 >= m else 'feasible')


def use_plan(name):
    """quantity, source step, and the planned contrasts of a use. A planned contrast is a list of
    (condition pattern, window, how many spreads of that rate its gate limit holds)."""
    part = name.split(':')
    same = lambda k, s, wins: [[({'tgt': (k, s)}, w, 2)] for w in wins]
    if name == 'P3G':
        return 'one_rate', 'S2', [x for k in KERNELS for x in same(k, M8, ('prefix_last', 'first'))]
    if name == 'S3G':
        return 'one_rate', 'S2', same(OLD, M8, ('prefix_last', 'first'))
    if part[0] in ('BIN', 'CS') and len(part) == (2 if part[0] == 'BIN' else 3):
        k, s = part[1].split('@')
        wins = ('first', 'fourth') if part[0] == 'BIN' else (part[2],)
        if k in KERNELS and all(w in ('first', 'fourth') for w in wins):
            return 'one_rate', 'S2', same(k, parse_size(s), wins)
    if part[0] == 'CM' and len(part) == 3 and part[2] in ('first', 'fourth'):
        cond = lambda t, p: {'pred': PRED[p], 'tgt': (TGT[t], M8)}
        four = [(t, p) for p in ('old', 'new') for t in ('old', 'new')]
        if part[1] == 'rate':
            return 'one_rate', 'S3', [[(cond(t, p), part[2], 2)] for t, p in four]
        if part[1] == 'history':
            return 'two_rate', 'S3', [[(cond('old', p), part[2], 2) for p in ('new', 'old')]]
        if part[1] == 'interaction':
            return 'four_rate', 'S3', [[(cond(t, p), part[2], 2) for t, p in four]]
    raise GateError('unknown use name: ' + name)


def forecast(procs, uses, sources):
    """L0 and the margin of each selected use, from the A/A values of earlier same-condition trials.

    L0 uses every trial with valid accounting (the unfiltered A/A values), so a process with a marked trial
    cannot leave the maximum. Each condition needs its 6 processes on every CPU and session that the folders
    hold. The value with the marked trials left out is given beside it. Test data gets no forecast word."""
    out = dict(format='bwx8-margins v1', test=is_test(procs), sources=sorted(sources), uses={})
    for name in uses:
        quantity, step, planned = use_plan(name)
        rows, missing = [], []
        for cpu, ses in cells_of(procs, step):
            ps = [p for p in procs if p.step == step and p.cpu == cpu and p.session == ses and not p.replaced_by]
            for terms in planned:
                lim, limf, parts = 0.0, 0.0, []
                for pattern, w, mult in terms:
                    own = [p for p in ps if len(p.by_key(pattern)) == 1]
                    aa, aaf = ([abs(c['aa']) for c in (cell_rate(p, pattern, w, f) for p in own)
                                if c['aa'] is not None] for f in (False, True))
                    if len(own) != UNITS or len(aa) != UNITS:
                        missing.append('%s: %d processes ran %s, %d of them have an A/A value in the %s window, '
                                       '%d are needed' % (cell_key(cpu, ses), len(own), pattern, len(aa), w, UNITS))
                        continue
                    lim += mult * max(aa)
                    limf = None if limf is None or not aaf else limf + mult * max(aaf)
                    parts.append(dict(condition=repr(pattern), window=w, spread=max(aa), n_processes=len(aa),
                                      spread_filtered=max(aaf) if aaf else None, n_processes_filtered=len(aaf)))
                rows.append(dict(cell=cell_key(cpu, ses), projected_limit=lim, projected_limit_filtered=limf,
                                 parts=parts))
        if missing or not rows:
            out['uses'][name] = dict(quantity=quantity, source_step=step, L0=None, margin=None,
                                     forecast='Insufficient data',
                                     why=missing or ['no %s process in the given folders' % step])
            continue
        d = margin_for(max(r['projected_limit'] for r in rows), quantity)
        lf = [r['projected_limit_filtered'] for r in rows]
        d.update(source_step=step, cells=rows, n_processes=UNITS, L0_filtered=None if None in lf else max(lf),
                 n_processes_filtered_min=min(p['n_processes_filtered'] for r in rows for p in r['parts']))
        out['uses'][name] = d
    if out['test']:
        for d in out['uses'].values():
            d['forecast'] = None
    return out


def gate_decide(res, margin):
    """The outcome word of one gate contrast on one CPU and session (design line 193, contract 'Gates')."""
    out = dict(margin=margin, max_passing_median=None)
    if not res['complete']:
        out['outcome'] = 'incomplete'
        return out
    m, lim = abs(res['median']), res['limit']
    if lim < margin:
        out['max_passing_median'] = min(lim, margin - lim)
    if m <= lim and lim < margin and round(m + lim, EPS_DIGITS) <= margin:
        out['outcome'] = 'pass'
    elif res['repeatable']:
        out['outcome'] = 'resolved difference'
    elif lim >= margin or m <= lim:
        out['outcome'] = 'precision insufficient'
    else:
        out['outcome'] = 'not established'
    return out


def gate_contrasts(step, procs, cpu, ses, margins):
    """{use name: [(label, units, terms)]} for one CPU and session of a gate step."""
    out = {}
    pairs = [(a, b) for i, a in enumerate(KERNELS) for b in KERNELS[i + 1:]]
    if step in ('P3G', 'S3G'):
        U = proc_units(procs, step, cpu, ses)
        for k in (KERNELS if step == 'P3G' else (OLD,)):
            for a, b in pairs:
                for w in ('prefix_last', 'first'):
                    terms = [(c, None, {'prev': (j, M8), 'tgt': (k, M8)}, w) for c, j in ((1, a), (-1, b))]
                    out.setdefault(step, []).append(('%s %s: after %s - after %s' % (k, w, a, b), U, terms))
        return out
    if step in ('BIN', 'CS'):
        for one in sorted({p.one for p in procs if p.step == step and p.one}):
            U = proc_units(procs, step, cpu, ses, one)
            tag = '%s@%s' % (one[0], size_name(one[1]))
            names = []
            for w in ('first', 'fourth'):
                name = 'BIN:' + tag if step == 'BIN' else 'CS:%s:%s' % (tag, w)
                if name not in margins['uses']:
                    continue
                names.append(name)
                modes = ((('bins', 1), ('bins', 0)),) if step == 'BIN' else \
                    tuple((('count', a), ('count', b)) for a, b in MODE_PAIRS)
                for a, b in modes:
                    terms = [(c, None, {'tgt': one, m[0]: m[1]}, w) for c, m in ((1, a), (-1, b))]
                    out.setdefault(name, []).append(('%s %s: %s %s - %s' % (tag, w, a[0], a[1], b[1]), U, terms))
            if not names:
                raise GateError('no margin for %s of step %s in the margins file' % (tag, step))
        return out
    U = proc_units(procs, 'CM', cpu, ses)
    for w in ('first', 'fourth'):
        for a, b in MODE_PAIRS:
            lab = '%s: %s - %s' % (w, a, b)
            if 'CM:rate:' + w in margins['uses']:
                for t in ('old', 'new'):
                    for p in ('old', 'new'):
                        out.setdefault('CM:rate:' + w, []).append(
                            ('R(%s|%s) %s' % (t, p, lab), U, [r3(t, p, w, 1, a), r3(t, p, w, -1, b)]))
            if 'CM:history:' + w in margins['uses']:
                out.setdefault('CM:history:' + w, []).append(
                    ('R(old|new) - R(old|old) ' + lab, U,
                     [r3('old', 'new', w, 1, a), r3('old', 'old', w, -1, a),
                      r3('old', 'new', w, -1, b), r3('old', 'old', w, 1, b)]))
            if 'CM:interaction:' + w in margins['uses']:
                out.setdefault('CM:interaction:' + w, []).append(
                    ('G(new) - G(old) ' + lab, U, interaction(w, 'new', a) + interaction(w, 'new', b, -1)))
    if not out:
        raise GateError('no CM use in the margins file')
    return out


def gate(procs, step, margins):
    """Evaluate one gate step. Every contrast must pass on both CPUs in both sessions."""
    mine = sorted({p.folder for p in procs if p.step == step})
    both_named = set(mine) & set(margins.get('sources', []))
    if both_named:
        raise GateError('the margins file names the gated batch as its source: %s' % sorted(both_named))
    if margins.get('test') and not is_test(procs):
        raise GateError('the margins file was made from test data')
    out = dict(step=step, folders=mine, uses={})
    for cpu, ses in [(c, s) for c in CPUS for s in SESSIONS]:
        for name, items in gate_contrasts(step, procs, cpu, ses, margins).items():
            m = margins['uses'].get(name)
            if not m or m.get('margin') is None:
                raise GateError('no frozen margin for the use %s' % name)
            want = QUANT[m['quantity']][0]
            u = out['uses'].setdefault(name, dict(margin=m['margin'], quantity=m['quantity'],
                                                  clipped=m.get('clipped'), margin_forecast=m.get('forecast'),
                                                  cells={}))
            rows = []
            for label, U, terms in items:
                assert len(terms) == want, 'spreads of %s' % label
                res = both(U, terms, label, one_process=True)
                for r in res.values():
                    r.update(gate_decide(r, m['margin']))
                rows.append(res)
            u['cells'][cell_key(cpu, ses)] = dict(
                contrasts=rows, passed=all(r['filtered']['outcome'] == 'pass' for r in rows))
    for u in out['uses'].values():
        words = [r['filtered']['outcome'] for c in u['cells'].values() for r in c['contrasts']]
        fails = [w for w in words if w != 'pass']
        u['counts'] = {w: words.count(w) for w in sorted(set(words))}
        u['overall'] = ('pass' if not fails else 'resolved difference' if 'resolved difference' in fails else
                        'precision insufficient' if set(fails) == {'precision insufficient'} else 'not established')
    out['passed'] = all(u['overall'] == 'pass' for u in out['uses'].values())
    out['statement'] = 'equivalence established' if out['passed'] else (
        '%s equivalence not established' % ('prefix' if step in ('P3G', 'S3G') else 'mode'))
    return out


# ---------------------------------------------------------------- bins, counters, sustained reads

def bin_parts(trial, widx):
    """The 10 ms bins of one target window as (t_start_ns, t_end_ns, bytes)."""
    w, parts = trial.W[('target', widx)], []
    t, b = w['t0'], 0
    for k in sorted(x for x in trial.B if x[0] == widx):
        row = trial.B[k]
        parts.append((t, row['t1'], row['bytes'] - b))
        t, b = row['t1'], row['bytes']
    return parts


def sum_rate(parts):
    """Rate of several bins together: the sum of the bytes over the sum of the time (design line 158)."""
    ns = sum(p[1] - p[0] for p in parts)
    return sum(p[2] for p in parts) / ns if ns > 0 else None


def rebin(parts, n):
    """Join every n successive bins by summing bytes and time."""
    return [(parts[i][0], parts[min(i + n, len(parts)) - 1][1], sum(p[2] for p in parts[i:i + n]))
            for i in range(0, len(parts), n)]


def counter_rows(proc):
    """Per target window of every trial with counter reads: the timing, and the counts if they can be
    interpreted. A failed, unsupported or multiplexed count gives None values and a reason."""
    names = [x.split('=')[0] for x in proc.M.get('events', '').replace(';', ',').split(',') if x and x != 'none']
    proc_bad = ['reported failure %s: %s' % x for x in proc.X if x[0].startswith('count')]
    rows = []
    for n in sorted(proc.trials):
        t = proc.trials[n]
        if t.count != 'read' or t.reject:
            continue
        for widx in range(t.nwin):
            w, c = t.W[('target', widx)], t.C.get(widx)
            why = proc_bad + t.count_bad
            if c is None:
                why = why + ['no C row']
            elif c['enabled'] is None or c['running'] is None:
                why = why + ['enabled or running time is NA']
            elif c['running'] < c['enabled']:
                why = why + ['multiplexed: running %d ns of %d ns enabled' % (c['running'], c['enabled'])]
            elif len(c['counts']) != len(names):
                why = why + ['%d counts for %d event names' % (len(c['counts']), len(names))]
            row = dict(trial=n, cond=t.cond, widx=widx, rate=t.rate(('target', widx)), bytes=w['bytes'],
                       interpretable=not why, why=why, counts={}, per_64B={}, instructions_per_byte=None,
                       cycles_per_byte=None, cycles_per_cpu_s=None)
            if not why:
                row['counts'] = dict(zip(names, c['counts']))                 # None: the event did not open
                row['per_64B'] = {k: None if v is None else v * 64.0 / w['bytes'] for k, v in row['counts'].items()}
                cyc, ins = row['counts'].get('cycles'), row['counts'].get('instructions')
                row['instructions_per_byte'] = None if ins is None else ins / w['bytes']
                row['cycles_per_byte'] = None if cyc is None else cyc / w['bytes']
                if cyc is not None and c['cputime']:
                    row['cycles_per_cpu_s'] = cyc * 1e9 / c['cputime']
            rows.append(row)
    return rows


def counter_summary(rows):
    ok = [r for r in rows if r['interpretable']]
    out = dict(windows=len(rows), interpretable=len(ok), per_64B={})
    for k in sorted({k for r in ok for k in r['per_64B']}):
        out['per_64B'][k] = stats(r['per_64B'][k] for r in ok)
    for k in ('instructions_per_byte', 'cycles_per_byte', 'cycles_per_cpu_s'):
        out[k] = stats(r[k] for r in ok)
    return out


def sustained(procs):
    """Stage 4: per process the full window trace, its median and range, and every step between two
    successive windows above STEP_CHANGE, described by its two rates."""
    out = []
    for p in sorted((p for p in procs if p.step in ('S4', 'C4')), key=lambda p: (p.folder, p.order)):
        d = dict(p.ident(), kernel=p.one and p.one[0], size=p.one and p.one[1], load=p.head.get('loadavg'),
                 trace=None, marks=[], why=list(p.reject))
        ts = [p.trials[n] for n in sorted(p.trials)]
        if len(ts) != 1 or ts[0].reject:
            d['why'] = d['why'] or (ts[0].reject if len(ts) == 1 else ['%d trials, 1 expected' % len(ts)])
            out.append(d)
            continue
        t = ts[0]
        ws = [t.W[('target', i)] for i in range(t.nwin)]
        rates = [w['bytes'] / (w['t1'] - w['t0']) for w in ws]
        d['trace'] = [dict(widx=i, t_start_s=(w['t0'] - ws[0]['t0']) / 1e9, t_end_s=(w['t1'] - ws[0]['t0']) / 1e9,
                           rate=r) for i, (w, r) in enumerate(zip(ws, rates))]
        d.update(stats(rates))
        d['whole_rate'] = sum(w['bytes'] for w in ws) / sum(w['t1'] - w['t0'] for w in ws)
        d['step_limit'] = STEP_CHANGE
        d['transitions'] = [dict(widx=i + 1, at_s=d['trace'][i + 1]['t_start_s'], rate_before=a, rate_after=b,
                                 change=b - a)
                            for i, (a, b) in enumerate(zip(rates, rates[1:])) if abs(b - a) > STEP_CHANGE]
        d['marks'] = t.disturbed + t.coverage
        if t.count == 'read':
            rows = counter_rows(p)
            d['counter_windows'], d['counters'] = rows, counter_summary(rows)
        out.append(d)
    return out


# ---------------------------------------------------------------- B6W

def b6w(procs):
    """Stage 1 item 2: the 8 old-read A/A pairs after assembly read, per process."""
    out = dict(cells={})
    for cpu, ses in cells_of(procs, 'B6W'):
        rows = []
        for p in sorted((p for p in procs if p.step == 'B6W' and p.cpu == cpu and p.session == ses
                         and not p.replaced_by), key=lambda p: p.order):
            seq = (p.opt('--seq') or '').split(',')
            row = dict(p.ident(), pairs=[], why=list(p.problems) + list(p.reject))
            ok = len(seq) > 11 and all(seq[i] == ASM for i in B6_REF) and all(
                seq[i].startswith(OLD) and '@' not in seq[i] for pr in B6_PAIRS for i in pr)
            if not ok:
                row['why'].append('the sequence is not the B6 sequence')
            if p.status != 'ok':
                row['why'].append('process ' + p.status)
            for rnd in sorted({k[0] for k in p.intervals}):
                for a, b in B6_PAIRS:
                    x, y, ref = (p.intervals.get((rnd, i)) for i in (a, b, a - 1))
                    if x and y and ref and x['elapsed'] > 0 and y['elapsed'] > 0:
                        r1, r2 = x['bytes'] / x['elapsed'] / 1e9, y['bytes'] / y['elapsed'] / 1e9
                        row['pairs'].append(dict(round=rnd, positions=[a, b], first=r1, second=r2,
                                                 difference=r1 - r2, first_slower=r1 < r2,
                                                 asm_before=ref['bytes'] / ref['elapsed'] / 1e9))
            if len(row['pairs']) != 8:
                row['why'].append('%d pairs, 8 expected' % len(row['pairs']))
            row['all_slower'] = None if row['why'] else all(x['first_slower'] for x in row['pairs'])
            rows.append(row)
        c = dict(cpu=cpu, session=ses, processes=rows, reproduced=None, why=None)
        if len(rows) != 2 or any(r['why'] for r in rows):
            c['why'] = 'needs 2 complete processes with 8 pairs each'
        else:
            c['reproduced'] = all(r['all_slower'] for r in rows)
        out['cells'][cell_key(cpu, ses)] = c
    return out


# ---------------------------------------------------------------- summary

def scrub(x):
    """Empty every decision of a summary of test data."""
    if isinstance(x, dict):
        return {k: (None if k in DECISION_PARTS or (k in DECISION_KEYS and not isinstance(v, (dict, list)))
                    else scrub(v)) for k, v in x.items()}
    return [scrub(v) for v in x] if isinstance(x, list) else x


def scrub_summary(s):
    """scrub(), and the two places where a decision is not under a key of its own: the outcome words that
    are the keys of the gate counts, and the reason text of a P3 comparison."""
    s = scrub(s)
    for g in s['gates'].values():
        for u in g.get('uses', {}).values():
            u['counts'] = None
    for c in s.get('P3', {}).get('cells', {}).values():
        for name in ('filtered', 'unfiltered'):
            for x in (NEW, ASM):
                c[name][x]['why'] = None
    return s


def summary(procs, margins=None):
    """Everything the report needs, as plain dicts and lists."""
    steps = sorted({p.step for p in procs})
    out = dict(test_data=is_test(procs), banner=BANNER if is_test(procs) else None,
               folders=sorted({p.folder for p in procs}), steps=steps, counts=counts_of(procs),
               exclusions=exclusions(procs), replaced=replacements(procs), gates={})
    for step in GATE_STEPS:
        if step in steps:
            out['gates'][step] = gate(procs, step, margins) if margins else dict(
                step=step, passed=None, statement='not evaluated: no margins file was given')
    if 'B6W' in steps:
        out['B6W'] = b6w(procs)
    if 'S2' in steps:
        out['stage2'] = stage2(procs)
    if 'P3' in steps:
        out['P3'] = p3(procs, out['gates'].get('P3G', {}).get('passed'))
    if 'S3' in steps:
        out['stage3'] = stage3(procs)
    if 'S4' in steps or 'C4' in steps:
        out['sustained'] = sustained(procs)
    counted = [p for p in procs if p.step in ('CS', 'CM')]
    if counted:
        out['counters'] = [dict(p.ident(), **counter_summary(counter_rows(p))) for p in counted]
    return scrub_summary(out) if out['test_data'] else out


def fx(x, nd=3):
    return 'NA' if x is None else '%+.*f' % (nd, x)


def word(x):
    return 'no decision' if x is None else str(x)


def line_of(name, r):
    """One text line for a contrast: both estimates side by side."""
    f, u = r['filtered'], r['unfiltered']
    vals = ' '.join(fx(x['value']) for x in f['units'])
    return ('  %-44s median %s limit %s range %s..%s [%s] %s | unfiltered median %s (%d of %d units; filtered %d)'
            % (name, fx(f['median']), fx(f['limit']), fx(f['min']), fx(f['max']), vals, word(f['state']),
               fx(u['median']), u['n_valid'], u['n_units'], f['n_valid']))


def text(s):
    """A plain text view of a summary. Rates and differences are in GB/s."""
    L = []
    if s['test_data']:
        L.append(s['banner'])
    L.append('folders: ' + ', '.join(s['folders']))
    for step, c in sorted(s['counts'].items()):
        L.append('%s: %d processes (%d not ended), %d trials: %d rejected, %d disturbed, %d coverage change; '
                 'unfiltered %d, filtered %d' % (step, c['processes'], c['processes_not_ended'], c['trials'],
                                                c['rejected'], c['disturbed'], c['coverage_change'],
                                                c['unfiltered'], c['filtered']))
    L.append('exclusion table: %d rows (in the json file)' % len(s['exclusions']))
    for r in s.get('replaced', []):
        L.append('replaced: %s session %s cpu %s proc %s of folder %s did not end (%s, %d trials kept as partial '
                 'observations); the complete process of folder %s is used in its place' % (
                     r['step'], r['session'], r['cpu'], r['proc'], r['folder'], r['status'], r['trials'],
                     r['replaced_by']))
    for step, g in sorted(s['gates'].items()):
        L.append('gate %s: %s' % (step, word(g['statement'])))
        for name, u in sorted(g.get('uses', {}).items()):
            L.append('  use %s: margin %.2f GB/s%s, %s, outcomes %s' % (
                name, u['margin'], ' (clipped)' if u['clipped'] else '', word(u['overall']), word(u['counts'])))
            for ck, c in sorted(u['cells'].items()):
                for r in c['contrasts']:
                    f = r['filtered']
                    L.append('    %s %-40s median %s limit %s largest median that could pass %s: %s' % (
                        ck, f['label'], fx(f['median']), fx(f['limit']), fx(f['max_passing_median']),
                        word(f['outcome'])))
    for ck, c in sorted(s.get('B6W', {}).get('cells', {}).items()):
        n = sum(x['first_slower'] for r in c['processes'] for x in r['pairs'])
        L.append('B6W %s: first interval slower in %d of %d pairs; reproduced: %s%s' % (
            ck, n, sum(len(r['pairs']) for r in c['processes']), word(c['reproduced']),
            ' (%s)' % c['why'] if c['why'] else ''))
    s2 = s.get('stage2')
    if s2:
        for ck, c in sorted(s2['cells'].items()):
            L.append('Stage 2 %s (fourth window; six set values in brackets)' % ck)
            for size, z in c['sizes'].items():
                for name in ('new_minus_old', 'asm_minus_old'):
                    g = z[name]['fourth']['filtered']['gain_pct']
                    L.append(line_of('%s %s' % (size, name), z[name]['fourth']) + '; gain %s %% (%s..%s)' % (
                        fx(g['median'], 2), fx(g['min'], 2), fx(g['max'], 2)))
                    L.append(line_of('%s %s first window' % (size, name), z[name]['first']))
            if 'P1' in c:
                p = c['P1']['filtered']
                L.append(line_of('P1 old 8M - old 1M', c['P1_contrast']))
                L.append('  P1: %s (largest |difference| + limit %s, margin %.2f)' % (
                    word(p['outcome']), fx(p['largest_abs_plus_limit']), p['margin']))
                for k in (NEW, ASM):
                    L.append(line_of('P2 %s 8M - 1M' % k, c['P2'][k]))
                L.append(line_of('size contrast of new - old', c['size_contrast']))
                d = c['decomposition']['filtered']
                L.append(line_of('dG', dict(filtered=d['dG'], unfiltered=c['decomposition']['unfiltered']['dG'])))
                L.append('  dG terms: new_1 - new_8 median %s, old_1 - old_8 median %s; shares: %s' % (
                    fx(d['new_term']['median']), fx(d['old_term']['median']),
                    'new %s %%, old %s %% (medians of the sets)' % (
                        fx(d['shares']['new_share_pct']['median'], 1), fx(d['shares']['old_share_pct']['median'], 1))
                    if d['shares'] else word(d['shares_why'])))
            for k, x in c.get('crossing', {}).items():
                L.append('  %s - old: 8M %s, 16M %s: %s' % (k, fx(x['8M']['median']), fx(x['16M']['median']),
                                                            word(x['word'])))
            for k, x in c.get('range_8M', {}).items():
                L.append('  8M rate of %s: %s to %s (filtered, %d processes)' % (
                    k, fx(x['filtered']['min']), fx(x['filtered']['max']), x['filtered']['n_valid']))
            if c.get('sentence', {}).get('text'):
                L.append('  ' + c['sentence']['text'])
        L.append('P1: %s; per CPU %s' % (word(s2['P1']['overall']),
                                         {k: word(v['outcome']) for k, v in s2['P1']['per_cpu'].items()}))
        for k, v in s2['P2'].items():
            L.append('P2 %s: %s' % (k, {c: word(x['outcome']) for c, x in v['per_cpu'].items()}))
        L.append('candidate explanation of the size comparison: %s' % word(s2['candidate']))
    for ck, c in sorted(s.get('P3', {}).get('cells', {}).items()):
        for x in (NEW, ASM):
            d = c['filtered'][x]
            L.append('P3 %s selected by %s: %s%s; load-only range %s, old range %s, control limit %s' % (
                ck, x, word(d['outcome']), ' (%s)' % d['why'] if d['why'] else '', fx(d.get('load_range')),
                fx(d.get('old_range')), fx(d.get('control_limit'))))
    s3 = s.get('stage3')
    if s3:
        for ck, c in sorted(s3['cells'].items()):
            L.append('Stage 3 %s' % ck)
            for name, ws in c['primary'].items():
                for w, r in ws.items():
                    L.append(line_of('%s %s' % (name, w), r))
            for k, ws in c['previous_target'].items():
                L.append('  previous-target diagnostic, target %s: span first %s, fourth %s' % (
                    k, fx(ws.get('first', {}).get('span')), fx(ws.get('fourth', {}).get('span'))))
            L.append('  %d other contrasts are exploratory (in the json file)' % len(c['exploratory']))
        for name, ws in s3['confirm'].items():
            for w, cf in ws.items():
                L.append('%s %s: confirmed per CPU %s; on both CPUs: %s' % (
                    name, w, {k: word(v['confirmed']) for k, v in cf['per_cpu'].items()},
                    word(cf['confirmed_both'])))
    for d in s.get('sustained', []):
        if d['trace'] is None:
            L.append('sustained %s cpu %s s%s proc %s: no trace (%s)' % (d['step'], d['cpu'], d['session'],
                                                                         d['proc'], '; '.join(d['why'])))
            continue
        L.append('sustained %s %s cpu %s s%s proc %s: %d windows, median %s, range %s to %s, %d steps above '
                 '%.2f GB/s between successive windows' % (
                     d['step'], d['kernel'], d['cpu'], d['session'], d['proc'], d['n'], fx(d['median']),
                     fx(d['min']), fx(d['max']), len(d['transitions']), d['step_limit']))
        for t in d['transitions']:
            L.append('    at %.1f s: %s to %s' % (t['at_s'], fx(t['rate_before']), fx(t['rate_after'])))
        if 'counters' in d:
            c = d['counters']
            L.append('    counts interpreted in %d of %d windows; cycles per byte %s, instructions per byte %s' % (
                c['interpretable'], c['windows'], fx(c['cycles_per_byte']['median'], 4),
                fx(c['instructions_per_byte']['median'], 4)))
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description='analysis of bwx8 result folders')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('summary')
    a.add_argument('folders', nargs='+')
    a.add_argument('--margins')
    a.add_argument('-o', '--out', required=True)
    b = sub.add_parser('forecast')
    b.add_argument('folders', nargs='+')
    b.add_argument('--use', action='append', required=True)
    b.add_argument('-o', '--out', required=True)
    args = ap.parse_args(argv)
    procs = load(args.folders)
    try:
        if args.cmd == 'forecast':
            res = forecast(procs, args.use, {p.folder for p in procs})
            if res['test']:
                print(BANNER)
            for name, u in res['uses'].items():
                if u['margin'] is None:
                    print('%s: %s: %s' % (name, word(u['forecast']), '; '.join(u['why'])))
                else:
                    lf = 'not available' if u['L0_filtered'] is None else '%.3f GB/s' % u['L0_filtered']
                    print('%s: L0 %.3f GB/s (largest projected limit, %d spreads, %d processes per CPU, session '
                          'and condition, every trial with valid accounting), margin %.2f GB/s%s, forecast: %s; '
                          'with marked trials left out L0 is %s (the fewest: %d of %d processes)'
                          % (name, u['L0'], u['spreads'], u['n_processes'], u['margin'],
                             ' (clipped)' if u['clipped'] else '', word(u['forecast']), lf,
                             u['n_processes_filtered_min'], u['n_processes']))
        else:
            margins = None
            if args.margins:
                with open(args.margins) as fh:
                    margins = json.load(fh)
            res = summary(procs, margins)
            print(text(res))
    except GateError as e:
        print('refused: %s' % e, file=sys.stderr)
        return 2
    with open(args.out, 'w') as fh:
        json.dump(res, fh, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
