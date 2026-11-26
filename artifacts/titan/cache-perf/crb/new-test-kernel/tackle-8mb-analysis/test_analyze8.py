#!/usr/bin/env python3
"""test_analyze8.py - checks of analyze8.py on synthetic result folders.

The builder below writes result folders in the format of DECISIONS-bwx8.md (header line, M, K, S, P, W, B,
C, E, X rows, plan.<key> rows). Every check goes through the parser. Where practical a check runs twice:
on a case that the rule must accept and on the opposite case that it must reject.
Prints one line per check. Exit status 0 only if every check passed.
"""
import contextlib, io, itertools, json, os, random, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze8 as A  # noqa: E402

OLD, NEW, ASM = A.OLD, A.NEW, A.ASM
K32, M1, M4, M8, M16 = 32768, A.M1, 4 * A.MIB, A.M8, A.M16
EVENTS = 'cycles=0x11,instructions=0x8,l1d_refill=0x3,l2d_refill=0x17,ll_miss_rd=0x37'
B6SEQ = 'asmread,oldread,oldread@1M,asmread,oldread@1M,oldread,asmread,oldread,oldread2,asmread,oldread2,oldread,asmread'
FAILS = []


def check(name, ok, detail=''):
    print('%s  %s%s' % ('ok  ' if ok else 'FAIL', name, '  [%s]' % detail if detail and not ok else ''))
    if not ok:
        FAILS.append(name)


def near(a, b, tol=1e-5):
    return a is not None and abs(a - b) <= tol


# ---------------------------------------------------------------- the synthetic-data builder

def noise(amp, *key):
    return random.Random(repr(key)).uniform(-amp, amp)


def sp(kernel, size, ms=None):
    return '%s@%s' % (kernel, A.size_name(size)) + (':%d' % ms if ms else '')


def trial(cond, rep, tgt, pfx='-', pred='-', prev='-', nwin=4, count='closed', bins=0):
    return dict(cond=cond, rep=rep, tgt=tgt, pfx=pfx, pred=pred, prev=prev, nwin=nwin, count=count, bins=bins)


def header(step, session, idx, cpu, args):
    return ('-- step %s session %d idx %d tag t%d waited_s 0 loadavg 1.00 1.68 23.10 1/1082 logins 0 '
            'utc 01:48:25 args %s' % (step, session, idx, idx, args))


def process(step, session, cpu, proc, trials, rate, plan=(), test=0, ntrials=None):
    """The lines of one trial-mode process. rate(c) gives the rate in GB/s of one window; c holds
    step, cpu, session, proc, n, cond, rep, phase, widx, kernel, size, tgt, pred, prev, prev_tgt."""
    L = [header(step, session, proc, cpu, '--trial --cpus %d --bytes %d --plan p%d.plan' % (cpu, M16, proc))]
    meta = [('mode', 'trial'), ('cpu', cpu), ('ctl_cpu', 0), ('bytes', M16), ('thp', 'madvise'),
            ('madvise_ok', 1), ('check_bytes', M8), ('kernels', 'STAND-IN'), ('plan_fnv1a64', '0123456789abcdef'),
            ('ntrials', len(trials) if ntrials is None else ntrials), ('rec_windows', 4096), ('rec_bins', 0),
            ('rec_bytes', 1 << 20), ('trace', 0), ('pmu_type', 11), ('events', EVENTS),
            ('plan.step', step), ('plan.session', session), ('plan.cpu', cpu), ('plan.bytes', M16),
            ('plan.proc', proc)] + [('plan.' + k, v) for k, v in plan] + [('plan.seed', 1), ('plan.test', test)]
    L += ['M,%s,%s' % kv for kv in meta]
    kernels = sorted({A.spec(t[f])[0] for t in trials for f in ('prev', 'pfx', 'pred', 'tgt') if t[f] != '-'})
    L += ['K,%s,%x,%d' % (k, 0x401000 + 256 * i, 0) for i, k in enumerate(kernels)]
    now, before = 1000000, ('none', 'none')
    for n, t in enumerate(trials):
        L.append('S,%d,%s,%d,%s,%s,%s,%s,%d,300,%s,%d,%s,%s' % (
            n, t['cond'], t['rep'], t['prev'], t['pfx'], t['pred'], t['tgt'], t['nwin'], t['count'], t['bins'],
            before[0], before[1]))
        L.append('P,%d,pre,16384,16384,100,0,5,0' % n)
        rows, first = [], now
        for phase, f, nw in (('prev', 'prev', 1), ('prefix', 'pfx', 4), ('pred', 'pred', 1), ('target', 'tgt', t['nwin'])):
            if t[f] == '-':
                continue
            kernel, size, ms = A.spec(t[f])
            ms = 300 if phase == 'target' else ms // nw
            for widx in range(nw):
                r = rate(dict(step=step, cpu=cpu, session=session, proc=proc, n=n, cond=t['cond'], rep=t['rep'],
                              phase=phase, widx=widx, kernel=kernel, size=size, tgt=t['tgt'], pred=t['pred'],
                              prev=t['prev'], prev_tgt=before[1], count=t['count'], bins=t['bins']))
                nbytes = max(1, round(r * ms * 1e6 / size)) * size
                ns = round(nbytes / r)
                rows.append('W,%d,%s,%d,%s,%d,%d,%d,%d' % (n, phase, widx, kernel, size, nbytes, now, now + ns))
                if phase == 'target' and t['bins']:
                    rows += ['B,%d,%d,%d,%d,%d' % (n, widx, b, now + ns * (b + 1) // 30,
                                                   (nbytes // size) * (b + 1) // 30 * size) for b in range(30)]
                if phase == 'target' and t['count'] == 'read':
                    rows.append('C,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d' % (
                        n, widx, ns, ns, ns - 100, 3 * ns, nbytes // 8, nbytes // 128, nbytes // 64, 7))
                now += ns + 40
        wall = now - 40 - first
        old = any(t[f].startswith(OLD) for f in ('prev', 'pfx', 'pred', 'tgt'))
        L += rows
        L.append('P,%d,post,16384,16384,100,0,5,0' % n)
        L.append('E,%d,%d,%d,0,0,%s,40,%s,%s' % (n, wall, wall - 1000, 40 if len(rows) > t['nwin'] else 'NA',
                                               '1' if old else 'NA', t['count']))
        before = (t['cond'], t['tgt'])
        now += 5000000
    return L


def put(root, name, step, procs):
    os.makedirs(os.path.join(root, name), exist_ok=True)
    with open(os.path.join(root, name, step + '.csv'), 'w') as fh:
        for p in procs:
            fh.write('\n'.join(p) + '\n')
    return os.path.join(root, name)


def edit(lines, start, fn):
    """Replace the lines that start with the given text by fn(line). fn may return a list or None."""
    out = []
    for line in lines:
        if line.startswith(start):
            r = fn(line)
            out += r if isinstance(r, list) else [] if r is None else [r]
        else:
            out.append(line)
    return out


def setf(line, i, value):
    f = line.split(',')
    f[i] = str(value)
    return ','.join(f)


BASE = {OLD: {K32: 66.8, M1: 67.05, M4: 67.0, M8: 67.0, M16: 66.0},
        NEW: {K32: 133.0, M1: 85.0, M4: 74.0, M8: 67.6, M16: 65.0},
        ASM: {K32: 134.0, M1: 86.0, M4: 75.0, M8: 68.5, M16: 65.5}}


def s2_rate(amp=0.01, shift=None):
    """Stage 2 rates: the table above, plus noise, plus shift(c) if given."""
    def f(c):
        r = BASE[c['kernel']][c['size']] + (shift(c) if shift else 0.0)
        return r + (noise(amp, c['session'], c['cpu'], c['proc'], c['n'], c['phase'], c['widx']) if amp else 0.0)
    return f


def s2(root, session, rate, sizes=(M1, M8), cpus=(2, 41), name=None, test=0, hook=None, kernels=A.KERNELS):
    """One S2 folder. hook(lines, cpu, size, rep_set, kernel) may change or drop a process."""
    procs, idx = [], 0
    for cpu in (cpus if session == 1 else cpus[::-1]):
        for r in range(1, 7):
            for size in sizes:
                for k in kernels:
                    idx += 1
                    ts = [trial('K=%s|S=%s' % (k, A.size_name(size)), rep, sp(k, size), sp(k, size, 1200))
                          for rep in (1, 2, 3, 4)]
                    rate_p = lambda c, r=r: rate(dict(c, rep_set=r))
                    L = process('S2', session, cpu, idx, ts, rate_p, test=test,
                                plan=(('rep_set', r), ('kernel', k), ('size', size)))
                    if hook:
                        L = hook(L, cpu, size, r, k)
                    if L:
                        procs.append(L)
    return put(root, name or 'bwx8-S2-s%d-20261115T0%d0000Z' % (session, session), 'S2', procs)


def s2_both(root, rate, **kw):
    return [s2(root, 1, rate, **kw), s2(root, 2, rate, **kw)]


def s3_schedule(seed):
    """The schedule of design line 242: 6 processes x 4 cycles of the 12 conditions."""
    rng = random.Random(seed)
    base = [0, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6]
    relabel = list(range(12))
    rng.shuffle(relabel)
    rows = [[relabel[(x + r) % 12] for x in base] for r in range(12)] * 2
    rng.shuffle(rows)
    return [rows[4 * p:4 * p + 4] for p in range(6)]


S3_CONDS = [(pk, ps, t) for pk, ps in ((OLD, M8), (NEW, M8), (ASM, M8), (OLD, M1)) for t in A.KERNELS]
MEAN = {OLD: 67.0, NEW: 67.6, ASM: 68.5}


def s3(root, session, effect, seed=1, cpus=(2, 41), name=None, amp=0.01):
    """One S3 folder. effect(c) is added to the rate of the kernel; c also has 'tgt_kernel'."""
    procs, idx = [], 0
    for cpu in (cpus if session == 1 else cpus[::-1]):
        for p, cycles in enumerate(s3_schedule((seed, session, cpu))):
            idx += 1
            ts = []
            for rep, row in enumerate(cycles, 1):
                for ci in row:
                    pk, ps, t = S3_CONDS[ci]
                    ts.append(trial('P=%s|T=%s' % (sp(pk, ps), t), rep, sp(t, M8), sp(OLD, M8, 1200), sp(pk, ps, 300)))
            f = lambda c, p=p: (MEAN[c['kernel']] + effect(dict(c, p=p, tgt_kernel=c['tgt'].split('@')[0]))
                                + noise(amp, seed, c['session'], c['cpu'], c['proc'], c['n'], c['phase'], c['widx']))
            procs.append(process('S3', session, cpu, idx, ts, f))
    return put(root, name or 'bwx8-S3-s%d-%s' % (session, seed), 'S3', procs)


def p3(root, session, rate, cpus=(2, 41), name='bwx8-P3-s%d'):
    procs, idx = [], 0
    perms = list(itertools.permutations(A.KERNELS))
    for cpu in (cpus if session == 1 else cpus[::-1]):
        for p in range(6):
            idx += 1
            ts = [trial('K=%s|S=8M' % k, rep, sp(k, M8), sp(k, M8, 1200))
                  for rep in (1, 2, 3, 4) for k in perms[(p + rep) % 6]]
            procs.append(process('P3', session, cpu, idx, ts, lambda c, p=p: rate(dict(c, p=p))))
    return put(root, name % session, 'P3', procs)


def prefix_gate(root, step, session, rate, cpus=(2, 41), name=None):
    """P3G (9 conditions) or S3G (3 conditions), 4 repeats each, 6 processes per CPU."""
    procs, idx = [], 0
    for cpu in (cpus if session == 1 else cpus[::-1]):
        for p in range(6):
            idx += 1
            ts = []
            for rep in (1, 2, 3, 4):
                for j in A.KERNELS:
                    for k in (A.KERNELS if step == 'P3G' else (OLD,)):
                        ts.append(trial('J=%s|K=%s' % (j, k), rep, sp(k, M8), sp(k, M8, 1200),
                                        sp(OLD, M8, 300) if step == 'S3G' else '-',
                                        sp(j, M8, 2400 if step == 'P3G' else 1200)))
            procs.append(process(step, session, cpu, idx, ts, lambda c, p=p: rate(dict(c, p=p))))
    return put(root, name or 'bwx8-%s-s%d' % (step, session), step, procs)


def aa_rate(effect, a):
    """Rates with an exact A/A value a in every condition, and effect[kernel of the previous activity]."""
    def f(c):
        prev = c['prev'].split('@')[0]
        return 67.0 + effect.get(prev, 0.0) + (a / 2 if c['rep'] in (1, 3) else -a / 2)
    return f


def margins_file(root, uses, sources=(), name='margins.json'):
    m = dict(format='bwx8-margins v1', test=False, sources=list(sources),
             uses={k: dict(quantity=q, margin=v, clipped=False, forecast='feasible') for k, (q, v) in uses.items()})
    path = os.path.join(root, name)
    with open(path, 'w') as fh:
        json.dump(m, fh)
    return m


def mode_gate(root, step, session, rate=None, cpus=(2, 41)):
    """BIN, CS (one kernel and size) or CM, 4 repeats per cell."""
    procs, idx = [], 0
    rate = rate or (lambda c: MEAN[c['kernel']] + noise(0.005, c['session'], c['cpu'], c['proc'], c['n'], c['widx'], c['phase']))
    for cpu in (cpus if session == 1 else cpus[::-1]):
        for p in range(6):
            idx += 1
            ts = []
            for rep in (1, 2, 3, 4):
                if step == 'BIN':
                    ts += [trial('K=oldread|S=8M|bins=%d' % b, rep, sp(OLD, M8), sp(OLD, M8, 1200), bins=b) for b in (0, 1)]
                elif step == 'CS':
                    ts += [trial('K=oldread|S=8M|count=%s' % m, rep, sp(OLD, M8), sp(OLD, M8, 1200), count=m)
                           for m in A.MODES]
                else:
                    ts += [trial('P=%s@8M|T=%s|count=%s' % (pk, t, m), rep, sp(t, M8), sp(OLD, M8, 1200),
                                 sp(pk, M8, 300), count=m) for m in A.MODES for pk in (OLD, NEW) for t in (OLD, NEW)]
            plan = (('kernel', OLD), ('size', M8)) if step != 'CM' else ()
            procs.append(process(step, session, cpu, idx, ts, lambda c, p=p: rate(dict(c, p=p)), plan=plan))
    return put(root, 'bwx8-%s-s%d' % (step, session), step, procs)


def s4(root, step, rate, count='closed', hook=None, name=None):
    procs = []
    for i, k in enumerate(A.KERNELS, 1):
        L = process(step, 1, 2, i, [trial('K=%s|S=8M' % k, 1, sp(k, M8), nwin=20, count=count)], rate,
                    plan=(('kernel', k), ('size', M8)))
        procs.append(hook(L, k) if hook else L)
    return put(root, name or 'bwx8-%s-s1' % step, step, procs)


def b6w(root, session, slow=3.0, bad_pair=None, nproc=2, cpus=(2, 41)):
    """Old interval mode. The first old read after assembly read is slower by 'slow' GB/s."""
    seq, procs, idx = B6SEQ.split(','), [], 0
    for cpu in cpus:
        for p in range(nproc):
            idx += 1
            L = [header('B6W', session, idx, cpu, '--threads 1 --cpus %d --seq %s --bytes 8M --rounds 4 '
                        '--min-ms 300 --stop pass' % (cpu, B6SEQ)),
                 '# bwx: seq=%s rounds=4 stop=pass' % B6SEQ]
            t = 0.001
            for rnd in range(4):
                for pos, e in enumerate(seq):
                    k, size = e.split('@')[0], A.parse_size(e.split('@')[1]) if '@' in e else M8
                    r = 68.5 if k == ASM else 67.0
                    if pos in (7, 10):
                        r -= slow if (cpu, p, rnd, pos) != bad_pair else -0.2
                    nbytes = round(r * 0.3e9 / size) * size
                    el = nbytes / r / 1e9
                    L.append('P,%d,%d,0,a,8192,8192,1,0,1,0' % (rnd, pos))
                    L.append('I,%d,%d,%s,%d,1,%d,%.6f,%.2f' % (rnd, pos, k.rstrip('2'), size, nbytes, el, r))
                    L.append('T,%d,%d,%s,0,%d,%d,%.9f,%.6f,%.6f,%.6f,%.3f,-' % (
                        rnd, pos, k.rstrip('2'), cpu, nbytes, el, t, t, t + el, nbytes / size))
                    t += el + 0.0003
            procs.append(L)
    return put(root, 'bwx8-B6W-s%d' % session, 'B6W', procs)


def cell(s, key='cpu2/s1'):
    return s['cells'][key]


def rewrite(folder, step, fn):
    """Replace the lines of the csv file of a folder by fn(lines)."""
    path = os.path.join(folder, step + '.csv')
    with open(path) as fh:
        lines = fn(fh.read().split('\n'))
    with open(path, 'w') as fh:
        fh.write('\n'.join(lines))
    return folder


def chunks(lines):
    """The lines of a csv file, one list per process."""
    out = []
    for line in lines:
        if line.startswith('-- step '):
            out.append([])
        if out:
            out[-1].append(line)
    return out


def stopped(folder, step, n, trial, name):
    """Emulate a step that was stopped in process n (counted from 0) at the S row of the given trial and
    continued with --from: the folder keeps the processes up to the killed one, a new folder gets the rest."""
    with open(os.path.join(folder, step + '.csv')) as fh:
        ch = chunks(fh.read().split('\n'))
    cut = ch[n].index([x for x in ch[n] if x.startswith('S,%d,' % trial)][0])
    with open(os.path.join(folder, step + '.csv'), 'w') as fh:
        fh.write('\n'.join(sum(ch[:n], []) + ch[n][:cut + 1] + ['W,%d,prefix,0,oldr-- killed tag t status 143 utc 01:02:03' % trial]) + '\n')
    return put(os.path.dirname(folder), name, step, ch[n:])


def run_cli(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = A.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


# ---------------------------------------------------------------- the checks

def test_parser_and_quality(root):
    d = os.path.join(root, 'q')
    procs = A.load(s2_both(d, s2_rate(), sizes=(K32, M1, M4, M8, M16)))
    check('parser: 360 Stage 2 processes in two folders, sessions from M,plan.session',
          len(procs) == 360 and sorted({p.session for p in procs}) == [1, 2] and all(len(p.trials) == 4 for p in procs))
    check('parser: clean data has an empty exclusion table', A.exclusions(procs) == [])
    w = procs[0].trials[0].W[('target', 3)]
    check('rate of a window is bytes over nanoseconds', near(procs[0].trials[0].rate('fourth'), w['bytes'] / (w['t1'] - w['t0']), 1e-12)
          and 60 < procs[0].trials[0].rate('fourth') < 140)

    # defects of single trials, all in one folder; the hook picks the process by CPU, size, set and kernel
    def hook(L, cpu, size, r, k):
        if cpu != 2 or size != M8:
            return L
        if (r, k) == (1, OLD):                                   # interrupted trial 3, then the kill line
            i = L.index([x for x in L if x.startswith('S,3,')][0])
            return L[:i + 1] + ['W,3,prefix,0,oldr-- killed tag t1 status 143 utc 01:02:03']
        if (r, k) == (1, NEW):                                   # bytes not a whole number of passes
            return edit(L, 'W,1,target,2,', lambda x: setf(x, 6, int(x.split(',')[6]) + 4096))
        if (r, k) == (1, ASM):                                   # a missing window
            return edit(L, 'W,2,target,1,', lambda x: None)
        if (r, k) == (2, OLD):                                   # a duplicated W row
            return edit(L, 'W,0,target,3,', lambda x: [x, x])
        if (r, k) == (2, NEW):                                   # disturbed: an involuntary context switch
            return edit(L, 'E,1,', lambda x: setf(x, 5, 1))
        if (r, k) == (2, ASM):                                   # disturbed: CPU time 98.5 % of the wall time
            return edit(L, 'E,1,', lambda x: setf(x, 3, int(int(x.split(',')[2]) * 0.985)))
        if (r, k) == (3, OLD):                                   # disturbed: a gap of 100001 ns
            return edit(L, 'E,1,', lambda x: setf(x, 6, 100001))
        if (r, k) == (5, OLD):                                   # not disturbed: CPU time 99.5 % of the wall time
            return edit(L, 'E,1,', lambda x: setf(x, 3, int(int(x.split(',')[2]) * 0.995)))
        if (r, k) == (5, NEW):                                   # not disturbed: a gap of exactly 100000 ns
            return edit(L, 'E,1,', lambda x: setf(x, 6, 100000))
        if (r, k) == (5, ASM):                                   # coverage not readable in one snapshot
            return edit(L, 'P,1,post', lambda x: setf(x, 4, 'NA'))
        if (r, k) == (6, OLD):                                   # E row without the gap; the W rows give 150 us
            t0 = int([x for x in L if x.startswith('W,1,target,0,')][0].split(',')[7])
            L = edit(L, 'W,1,prefix,3,', lambda x: setf(x, 8, t0 - 150000))
            return edit(L, 'E,1,', lambda x: setf(x, 6, 'NA'))
        if (r, k) == (6, NEW):                                   # repeat number 1 occurs twice
            return edit(L, 'S,1,', lambda x: setf(x, 3, 1))
        if (r, k) == (6, ASM):                                   # a run of the trace test
            return edit(L, 'M,trace,', lambda x: 'M,trace,1')
        if (r, k) == (3, NEW):                                   # coverage change
            return edit(L, 'P,1,post', lambda x: setf(x, 4, 14336))
        if (r, k) == (3, ASM):                                   # process failed with exit status
            return L[:30] + ['-- failed tag t9 exit 1']
        if (r, k) == (4, OLD):                                   # sink check failed
            return edit(L, 'E,2,', lambda x: setf(x, 8, 0))
        if (r, k) == (4, NEW):                                   # pinning: the M row has another CPU
            return edit(L, 'M,cpu,', lambda x: 'M,cpu,3')
        if (r, k) == (4, ASM):                                   # required record missing
            return edit(L, 'P,0,pre', lambda x: None)
        return L
    procs = A.load([s2(d, 1, s2_rate(), hook=hook, name='defects')])
    ex = A.exclusions(procs)
    by = {(p.rep_set, p.one[0]): p for p in procs if p.cpu == 2 and p.one[1] == M8}
    why = lambda r, k, n: '; '.join(by[(str(r), k)].trials[n].reject)
    check('interrupted trial (S row without E row) is rejected', 'interrupted' in why(1, OLD, 3)
          and not by[('1', OLD)].trials[2].reject)
    check('killed process is recognised after a row that the kill cut short', by[('1', OLD)].status == 'killed'
          and any(e['kind'] == 'process killed' for e in ex))
    check('failed process is recognised', by[('3', ASM)].status == 'failed'
          and any(e['kind'] == 'process failed' for e in ex))
    check('lost bytes: bytes not a multiple of pass_bytes is rejected', 'whole number of passes' in why(1, NEW, 1)
          and not by[('1', NEW)].trials[0].reject)
    check('lost bytes: a missing window is rejected', 'missing' in why(1, ASM, 2) and not by[('1', ASM)].trials[1].reject)
    check('duplicated bytes: a W row that occurs twice is rejected', 'occurs twice' in why(2, OLD, 0)
          and not by[('2', OLD)].trials[1].reject)
    check('sink failure is rejected', 'sink' in why(4, OLD, 2))
    check('pinning failure rejects every trial of the process', all('pinning' in why(4, NEW, n) for n in range(4)))
    check('missing page snapshot is rejected', 'P row pre' in why(4, ASM, 0))
    t = by[('2', NEW)].trials[1]
    check('disturbed: involuntary context switch marks, does not reject', t.disturbed and not t.reject
          and t.usable(False) and not t.usable(True) and not by[('2', NEW)].trials[0].disturbed)
    old_limit, A.NIVCSW_PER_S = A.NIVCSW_PER_S, 3.0
    try:
        q = A.load([os.path.join(d, 'defects')])
        marks = sorted(len(x.disturbed) for p in q for x in p.trials.values() if any('involuntary' in m for m in x.disturbed))
        check('disturbed: with a host limit of 3 switches per second, 1 switch in a trial no longer marks it',
              not marks and any('involuntary' in m for m in t.disturbed), str(marks))
        A.NIVCSW_PER_S = 0.1
        q = A.load([os.path.join(d, 'defects')])
        check('disturbed: a host limit below the measured count per second still marks the trial',
              any('involuntary' in m for p in q for x in p.trials.values() for m in x.disturbed))
    finally:
        A.NIVCSW_PER_S = old_limit
    check('disturbed: thread CPU time of 98.5 % of the wall time is marked, 99.5 % is not',
          'CPU time' in by[('2', ASM)].trials[1].disturbed[0] and not by[('5', OLD)].trials[1].disturbed
          and by[('5', OLD)].trials[1].usable(True))
    check('disturbed: a gap of 100001 ns is marked, a gap of 100000 ns is not',
          'gap' in by[('3', OLD)].trials[1].disturbed[0] and not by[('5', NEW)].trials[1].disturbed)
    t = by[('6', OLD)].trials[1]
    check('disturbed: a gap that the E row does not give is taken from the W rows',
          t.measured()['gap_ns'] == 150000 and 'gap' in t.disturbed[0] and not t.reject
          and by[('6', OLD)].trials[0].measured()['gap_ns'] == 40)
    t = by[('5', ASM)].trials[1]
    check('coverage that is not readable (NA) marks the trial', 'not readable' in t.coverage[0] and not t.reject
          and not t.usable(True) and not by[('5', ASM)].trials[0].coverage)
    check('a repeat number that occurs twice rejects both trials',
          'occurs twice' in why(6, NEW, 0) and 'occurs twice' in why(6, NEW, 1) and not by[('6', NEW)].trials[2].reject)
    p = by[('6', ASM)]
    check('a trace run (M,trace,1) is rejected: its rates are not used',
          'trace run' in p.reject[0] and all('trace run' in why(6, ASM, n) for n in range(4))
          and not any(t.usable(False) for t in p.trials.values()) and not by[('5', ASM)].reject)
    t = by[('3', NEW)].trials[1]
    check('coverage change marks, does not reject', t.coverage and not t.reject and not t.usable(True))
    row = [e for e in ex if e['kind'] == 'disturbed' and e['proc'] == by[('3', OLD)].proc]
    check('exclusion table holds each marked trial with reason and measured values',
          len(row) == 1 and row[0]['measured']['gap_ns'] == 100001 and row[0]['trial'] == 1
          and 60 < row[0]['measured']['rate_fourth'] < 70
          and {e['kind'] for e in ex} >= {'rejected', 'disturbed', 'coverage change', 'process killed'})
    c = A.counts_of(procs)['S2']
    check('counts: unfiltered and filtered trial counts differ by the marked trials',
          c['unfiltered'] - c['filtered'] == 6 and c['disturbed'] == 4 and c['coverage_change'] == 2 and c['rejected'] >= 15,
          str(c))


def test_completeness(root):
    d = os.path.join(root, 'c')

    def hook(L, cpu, size, r, k):                               # one disturbed trial of old read, 8 MiB, set 3
        return edit(L, 'E,1,', lambda x: setf(x, 5, 2)) if (cpu, size, r, k) == (2, M8, 3, OLD) else L
    s = A.stage2(A.load(s2_both(d, s2_rate(), hook=hook)))
    c = cell(s)
    f, u = (c['sizes']['8M']['new_minus_old']['fourth'][x] for x in ('filtered', 'unfiltered'))
    check('5 valid units gives incomplete, with the partial values kept',
          f['state'] == 'incomplete' and f['n_valid'] == 5 and f['repeatable'] is None and near(f['median'], 0.6, 0.05)
          and f['trials_used'] == 40 and '3 of 4' in [r for r in f['units'] if r['value'] is None][0]['why'], str(f['state']))
    check('filtered and unfiltered estimates stand side by side with counts',
          u['state'] == 'repeatable' and u['n_valid'] == 6 and u['trials_used'] == 48)
    check('an invalid unrelated condition does not discard the unit',
          c['P2'][ASM]['filtered']['complete'] and c['sizes']['1M']['new_minus_old']['fourth']['filtered']['complete'])
    check('a four-rate contrast with a failed required trial is incomplete for that unit',
          c['size_contrast']['filtered']['n_valid'] == 5 and c['size_contrast']['unfiltered']['n_valid'] == 6
          and c['size_contrast']['unfiltered']['trials_required'] == 96)
    other = cell(s, 'cpu41/s1')['sizes']['8M']['new_minus_old']['fourth']['filtered']
    check('the opposite case (no mark) is complete and repeatable', other['complete'] and other['repeatable'])


def test_shared_rule(root):
    d = os.path.join(root, 'r')
    reps = {1: 67.0, 2: 67.2, 3: 67.4, 4: 67.1}

    def rate(c):                                                # exact rates: old 8 MiB of set 1 on CPU 2, session 1
        if (c['cpu'], c['session'], c['rep_set'], c['kernel'], c['size']) == (2, 1, 1, OLD, M8):
            return reps[c['rep']]
        return BASE[c['kernel']][c['size']]
    s = A.stage2(A.load(s2_both(d, rate)))
    f = cell(s)['sizes']['8M']['new_minus_old']['fourth']['filtered']
    check('A/A value is median(repeat 1, 3) - median(repeat 2, 4); spread is the largest; limit is the sum',
          near(f['spreads'][1], 0.05) and near(f['spreads'][0], 0.0) and near(f['limit'], 0.05), str(f['spreads']))
    check('unit value is the difference of the medians of four trials',
          near(f['units'][0]['value'], 67.6 - 67.15) and near(f['units'][1]['value'], 0.6))
    check('all six unit values, median and range are reported',
          len(f['units']) == 6 and near(f['range'], 0.15) and near(f['median'], 0.6) and near(f['min'], 0.45))
    g = f['gain_pct']
    check('percentage gain per matched set', near(f['units'][1]['gain_pct'], 100 * (67.6 / 67.0 - 1)) and g['n'] == 6)
    check('first-window values stand beside the fourth-window values',
          cell(s)['sizes']['8M']['new_minus_old']['first']['filtered']['n_valid'] == 6)

    def zero(eps):                                              # set 3 on CPU 2, session 1: new equals old + eps
        def rate(c):
            if (c['cpu'], c['session'], c['rep_set'], c['kernel'], c['size']) == (2, 1, 3, NEW, M8):
                return 67.0 + eps
            return BASE[c['kernel']][c['size']]
        return cell(A.stage2(A.load(s2_both(os.path.join(d, 'z%s' % eps), rate))))['sizes']['8M']['new_minus_old']['fourth']['filtered']
    z, nz = zero(0.0), zero(0.01)
    check('sign rule: a unit value of exactly 0 has no sign and fails',
          z['units'][2]['value'] == 0.0 and z['repeatable'] is False and z['state'] == 'signs differ between units')
    check('sign rule: the same case with a small positive value is repeatable', nz['repeatable'] is True and nz['sign'] == 1)
    s = A.stage2(A.load(s2_both(os.path.join(d, 'cf'), s2_rate())))
    cf = s['confirm']['new_minus_old@8M']
    check('confirmed per CPU and on both CPUs when both sessions agree in sign',
          cf['per_cpu']['cpu2']['confirmed'] and cf['per_cpu']['cpu41']['confirmed'] and cf['confirmed_both'] and cf['sign'] == 1)
    flip = lambda c: -1.2 if (c['kernel'], c['size'], c['session'], c['cpu']) == (NEW, M8, 2, 41) else 0.0
    cf = A.stage2(A.load(s2_both(os.path.join(d, 'fl'), s2_rate(shift=flip))))['confirm']['new_minus_old@8M']
    check('not confirmed on a CPU whose two sessions differ in sign',
          cf['per_cpu']['cpu2']['confirmed'] and not cf['per_cpu']['cpu41']['confirmed'] and not cf['confirmed_both'])
    flip = lambda c: -1.2 if (c['kernel'], c['size'], c['cpu']) == (NEW, M8, 41) else 0.0
    cf = A.stage2(A.load(s2_both(os.path.join(d, 'f2'), s2_rate(shift=flip))))['confirm']['new_minus_old@8M']
    check('confirmed positive on CPU 2 and confirmed negative on CPU 41 is not confirmed on both tested CPUs',
          cf['per_cpu']['cpu2'] == dict(confirmed=True, sign=1) and cf['per_cpu']['cpu41'] == dict(confirmed=True, sign=-1)
          and cf['confirmed_both'] is False and cf['sign'] is None)


def test_mixing(root):
    d = os.path.join(root, 'm')
    a = s2(d, 1, s2_rate(), name='first')
    b = s2(d, 1, s2_rate(), name='copy', cpus=(2,))
    procs = A.load([a, b])
    dup = [p for p in procs if p.duplicate]
    f = cell(A.stage2(procs))['sizes']['8M']['new_minus_old']['fourth']['filtered']
    check('mixing: duplicate process keys are refused', len(dup) == 72 and f['n_valid'] == 0
          and all('mixing' in t.reject[-1] for t in dup[0].trials.values()))
    f = cell(A.stage2(A.load([a])))['sizes']['8M']['new_minus_old']['fourth']['filtered']
    check('mixing: the same folder alone is accepted', f['n_valid'] == 6)

    def drop(L, cpu, size, r, k):                               # matched set 2 has no new-read process
        return None if (cpu, size, r, k) == (2, M8, 2, NEW) else L
    c = cell(A.stage2(A.load([s2(d, 1, s2_rate(), hook=drop, name='nokernel')])))['sizes']['8M']
    f = c['new_minus_old']['fourth']['filtered']
    check('mixing: a matched set with a missing kernel gives no value for that set',
          f['n_valid'] == 5 and f['state'] == 'incomplete' and 'no process' in f['units'][1]['why']
          and c['asm_minus_old']['fourth']['filtered']['n_valid'] == 6)

    def twice(L, cpu, size, r, k):                              # the new-read process of set 2 claims set 1
        if (cpu, size, r, k) == (2, M8, 2, NEW):
            return edit(L, 'M,plan.rep_set,', lambda x: 'M,plan.rep_set,1')
        return L
    f = cell(A.stage2(A.load([s2(d, 1, s2_rate(), hook=twice, name='twice')])))['sizes']['8M']['new_minus_old']['fourth']['filtered']
    check('mixing: two processes for one kernel in a matched set are refused',
          f['units'][0]['value'] is None and 'mixing' in f['units'][0]['why'] and f['n_valid'] == 4)
    z = cell(A.stage2(A.load([os.path.join(d, 'twice')])))
    f = z['sizes']['8M']['asm_minus_old']['fourth']['filtered']
    check('mixing: the refusal holds for that kernel only; a contrast without it keeps the matched set (design line 278)',
          f['n_valid'] == 6 and f['units'][0]['value'] is not None and z['P1']['filtered']['complete']
          and z['P2'][NEW]['filtered']['units'][0]['value'] is None)

    # a step that was stopped and continued with --from: the killed process and its rerun have one key
    a = s2(d, 1, s2_rate(), name='stop-A')
    b = stopped(a, 'S2', 10, 2, 'stop-B')                      # process 11: new read at 8M of set 2 on CPU 2
    for order in ([a, b], [b, a]):
        procs = A.load(order)
        z = cell(A.stage2(procs))
        killed = [p for p in procs if p.status == 'killed']
        ex = [e for e in A.exclusions(procs) if e['proc'] == killed[0].proc and e['folder'] == 'stop-A']
        sm = A.summary(procs)
        check('a stopped and continued Stage 2 step (folders in the order %s): the complete rerun is used, the '
              'killed process stays in the exclusion table' % [os.path.basename(x) for x in order],
              len(killed) == 1 and killed[0].replaced_by == 'stop-B' and len(procs) == 73
              and all(z['sizes']['8M'][n]['fourth'][e]['n_valid'] == 6 for n in ('new_minus_old', 'asm_minus_old')
                      for e in ('filtered', 'unfiltered')) and z['P1']['filtered']['complete']
              and [e['kind'] for e in ex] == ['process killed', 'rejected', 'rejected', 'rejected']
              and 'replaced by' in ex[0]['reasons'][1] and all('partial observation' in e['reasons'][-1] for e in ex[1:])
              and ex[1]['measured']['rate_fourth'] is not None
              and sm['replaced'] == [dict(killed[0].ident(), replaced_by='stop-B', trials=3)]
              and 'replaced: S2 session 1 cpu 2 proc 11 of folder stop-A did not end' in A.text(sm)
              and sm['counts']['S2']['unfiltered'] == 288 and sm['counts']['S2']['rejected'] == 3)
    z = cell(A.stage2(A.load([a])))['sizes']['8M']
    f = z['new_minus_old']['fourth']['unfiltered']
    check('the stopped folder alone gives no value for the killed process, and names no replacement',
          f['n_units'] == 2 and f['n_valid'] == 1 and '2 of 4' in f['units'][1]['why'] and f['state'] == 'incomplete'
          and A.replacements(A.load([a])) == [])
    eff = lambda c: -3.0 if (c['phase'], c['tgt_kernel'], c['pred']) == ('target', OLD, 'read@8M:300') else 0.0
    a = s3(d, 1, eff, cpus=(2,), name='stop3-A')
    b = stopped(a, 'S3', 2, 30, 'stop3-B')
    r = cell(A.stage3(A.load([a, b])))['primary']['new_predecessor_on_old']['first']['filtered']
    r0 = cell(A.stage3(A.load([a])))['primary']['new_predecessor_on_old']['first']['filtered']
    check('a stopped and continued Stage 3 step has 6 units, one per process key',
          r['n_units'] == 6 and r['n_valid'] == 6 and r['repeatable'] and [u['unit'] for u in r['units']] == list('123456')
          and r0['n_units'] == 3 and r0['state'] == 'incomplete')
    g = A.gate(A.load([rewrite(prefix_gate(d, 'S3G', 1, aa_rate({}, 0.02), cpus=(2,), name='seven'), 'S3G', lambda L: L + [
        x.replace(' idx 6 tag t6 ', ' idx 7 tag t7 ').replace('M,plan.proc,6', 'M,plan.proc,7') for x in chunks(L)[5]])]),
        'S3G', margins_file(d, {'S3G': ('one_rate', 0.30)}))
    r = cell(g['uses']['S3G'])['contrasts'][0]
    check('a CPU and session with 7 processes is incomplete: the number of units is not changed silently',
          all(r[e]['n_units'] == 7 and r[e]['n_valid'] == 7 and r[e]['state'] == 'incomplete' and r[e]['outcome'] == 'incomplete'
              for e in ('filtered', 'unfiltered')) and not cell(g['uses']['S3G'])['passed'])

    def two_kernels(L, cpu, size, r, k):                        # a Stage 2 process that also ran another kernel
        if (cpu, size, r, k) == (2, M8, 1, OLD):
            L = edit(L, 'S,3,', lambda x: x.replace(',oldread@8M,4,', ',read@8M,4,'))
            return edit(L, 'W,3,target', lambda x: setf(x, 4, 'read'))
        return L
    procs = A.load([s2(d, 1, s2_rate(), hook=two_kernels, name='twok')])
    p = [p for p in procs if p.reject][0]
    check('mixing: a single-kernel process that ran two kernels is refused',
          'mixing' in p.reject[0] and all(t.reject for t in p.trials.values()))
    one, two = [p for p in procs if not p.reject][:2]
    terms = [(1, 'a', {}, 'fourth'), (-1, 'b', {}, 'fourth')]
    try:
        A.contrast([dict(id=1, procs={'a': one, 'b': two})], terms, one_process=True)
        ok = False
    except A.MixError:
        ok = True
    r = A.contrast([dict(id=1, procs={'a': one, 'b': one})], terms, one_process=True)
    check('mixing: a unit built from two processes where one is required is refused', ok and r['n_units'] == 1)

    def halves(seed):                                           # Stage 3 conditions split over two processes
        folder = s3(d, 1, lambda c: 0.0, cpus=(2,), name='half%d' % seed)
        fn = os.path.join(folder, 'S3.csv')
        out, proc = [], 0
        for line in open(fn).read().split('\n'):
            proc += line.startswith('-- step')
            f = line.split(',')
            if seed and proc == 1 and f[0] in 'SPWEBC' and f[0] and f[1].isdigit() and int(f[1]) >= 24:
                continue                                        # process 1 loses its last two cycles
            out.append(line)
        open(fn, 'w').write('\n'.join(out))
        return cell(A.stage3(A.load([folder])))['primary']['new_predecessor_on_old']['first']['unfiltered']
    h, full = halves(1), halves(0)
    check('mixing: half of a process is not completed from another process',
          h['n_valid'] == 5 and h['units'][0]['value'] is None and full['n_valid'] == 6)


def test_stage2(root):
    d = os.path.join(root, 's2')
    s = A.stage2(A.load(s2_both(d, s2_rate(), sizes=(K32, M1, M4, M8, M16))))
    c = cell(s)
    check('Stage 2: old-to-new difference and gain at every size, fourth and first window',
          s['sizes'] == ['32K', '1M', '4M', '8M', '16M']
          and all(near(c['sizes'][n]['new_minus_old']['fourth']['filtered']['median'], BASE[NEW][z] - BASE[OLD][z], 0.03)
                  for n, z in (('32K', K32), ('1M', M1), ('4M', M4), ('8M', M8), ('16M', M16)))
          and near(c['sizes']['1M']['new_minus_old']['first']['filtered']['gain_pct']['median'], 100 * (85 / 67.05 - 1), 0.1))
    check('Stage 2: the same for assembly read minus old read',
          near(c['sizes']['8M']['asm_minus_old']['fourth']['filtered']['median'], 1.5, 0.03))
    p = c['P1']['filtered']
    check('P1: equivalent when every set difference plus the limit is within 0.30 GB/s',
          p['outcome'] == 'equivalent' and len(p['abs_plus_limit']) == 6 and p['largest_abs_plus_limit'] <= 0.30
          and s['P1']['overall'] == 'meets its equivalence margin' and s['P1']['per_cpu']['cpu2']['outcome'] == 'equivalent')
    check('P2: a confirmed decrease supports the prediction, for new read and for assembly read',
          all(s['P2'][k]['per_cpu']['cpu%d' % cpu]['outcome'] == 'supported' for k in (NEW, ASM) for cpu in (2, 41))
          and c['P2'][NEW]['filtered']['n_terms'] == 2)
    check('candidate is supported when P1 is equivalent and P2 shows the decreases', s['candidate'] == 'supported')
    sc = c['size_contrast']['filtered']
    check('size contrast of the old-to-new difference uses four spreads',
          sc['n_terms'] == 4 and len(sc['spreads']) == 4 and near(sc['median'], 0.6 - 17.95, 0.05) and sc['repeatable'])
    dc = c['decomposition']['filtered']
    sh = dc['shares']
    check('decomposition: dG with both terms, and signed shares when dG is resolved',
          dc['resolved'] and near(dc['dG']['median'], 17.35, 0.05) and near(dc['new_term']['median'], 17.4, 0.03)
          and near(dc['old_term']['median'], 0.05, 0.03)
          and all(near(u['new_share_pct'] + u['old_share_pct'], 100.0, 1e-6) for u in sh['units'])
          and sh['old_share_pct']['median'] < 0 < 100 < sh['new_share_pct']['median'])
    x = c['crossing'][NEW]
    check('load-only minus old read: sign and repeatability at 8 and 16 MiB, crossing found',
          x['8M']['median_sign'] == 1 and x['16M']['median_sign'] == -1 and x['8M']['repeatable'] and x['16M']['repeatable']
          and x['word'] == 'crossed between 8 and 16 MiB' and near(x['change'], -1.6, 0.05))
    r = c['range_8M'][ASM]['filtered']
    check('8 MiB rate range of each kernel', r['n_valid'] == 6 and near(r['min'], 68.5, 0.02) and r['max'] >= r['min'])
    t = c['sentence']
    check('result sentence values of design line 222',
          near(t['old_GBps'], 67.0, 0.02) and near(t['new_GBps'], 67.6, 0.02) and near(t['gain_pct'], 0.8955, 0.05)
          and 'oldread@8M for 1200 ms' in t['preparation'] and 'old read was 67.0' in t['text'])
    check('preceding process and trial rates are kept per process',
          len(s['processes']) == 360 and s['processes'][1]['preceding_kernel'] == OLD and len(s['processes'][0]['fourth']) == 4)

    # opposite cases
    out = lambda c: -0.35 if (c['kernel'], c['size'], c['cpu'], c['session'], c['rep_set']) == (OLD, M8, 2, 1, 4) else 0.0
    s = A.stage2(A.load(s2_both(os.path.join(d, 'p1'), s2_rate(shift=out))))
    p, r = cell(s)['P1']['filtered'], cell(s)['P1_contrast']['filtered']
    check('P1 fails equivalence when one matched set is outside the margin although the median is small',
          p['outcome'] == 'undecided' and abs(r['median']) < 0.10 and p['largest_abs_plus_limit'] > 0.30
          and s['P1']['overall'] == 'does not meet its equivalence margin' and s['P1']['per_cpu']['cpu2']['outcome'] == 'undecided'
          and s['P1']['per_cpu']['cpu41']['outcome'] == 'equivalent' and s['candidate'] == 'undecided')

    def p1_case(name, d1, aa, d2=None):
        """Exact rates on CPU 2: old 8M minus old 1M is d1 in session 1 and d2 in session 2 for every set;
        the old 8M process of set 1 has the A/A value aa, every other A/A value is 0."""
        def rate(c):
            if (c['kernel'], c['cpu']) != (OLD, 2):
                return BASE[c['kernel']][c['size']]
            if c['size'] == M1:
                return 67.0
            wob = (aa / 2 if c['rep'] in (1, 3) else -aa / 2) if c['rep_set'] == 1 else 0.0
            return 67.0 + (d1 if c['session'] == 1 or d2 is None else d2) + wob
        s = A.stage2(A.load(s2_both(os.path.join(d, name), rate)))
        return s, cell(s)['P1']['filtered'], cell(s)['P1_contrast']['filtered']
    s, p, r = p1_case('p1-lim', -0.25, 0.08)
    s2_, p2_, _ = p1_case('p1-lim-ok', -0.25, 0.04)
    check('P1: the limit is part of the equivalence test: |d| 0.25 with limit 0.08 is undecided, with limit 0.04 equivalent',
          p['outcome'] == 'undecided' and near(p['largest_abs_plus_limit'], 0.33, 1e-6) and near(r['limit'], 0.08, 1e-6)
          and all(abs(u['value']) < 0.26 for u in r['units']) and r['repeatable']
          and p2_['outcome'] == 'equivalent' and near(p2_['largest_abs_plus_limit'], 0.29, 1e-6))
    s, p, r = p1_case('p1-norep', -0.5, 0.6)
    s2_, p2_, _ = p1_case('p1-rep', -0.5, 0.1)
    check('P1: a difference of 0.5 inside a limit of 0.6 is undecided, not contradicted; with limit 0.1 it is contradicted',
          p['outcome'] == 'undecided' and near(r['median'], -0.5, 1e-6) and near(r['limit'], 0.6, 1e-6) and r['repeatable'] is False
          and p2_['outcome'] == 'contradicted' and s2_['P1']['per_cpu']['cpu2']['outcome'] == 'contradicted')
    s, p, r = p1_case('p1-signs', -1.0, 0.0, d2=1.0)
    check('P1: contradicted in both sessions with opposite signs is undecided on that CPU',
          p['outcome'] == 'contradicted' and cell(s, 'cpu2/s2')['P1']['filtered']['outcome'] == 'contradicted'
          and p['sign'] == -1 and cell(s, 'cpu2/s2')['P1']['filtered']['sign'] == 1
          and s['P1']['per_cpu']['cpu2']['outcome'] == 'undecided' and s['P1']['per_cpu']['cpu41']['outcome'] == 'equivalent'
          and s['candidate'] == 'undecided')
    hand = lambda vals, lim: A.p1_cell(dict(units=[dict(value=v) for v in vals], limit=lim, complete=True, repeatable=False,
                                            median=vals[0], sign=None))['outcome']
    check('P1: |d| + limit of exactly 0.30 GB/s is equivalent, also when the binary sum is 0.30000000000000004',
          hand([0.25] * 6, 0.05) == 'equivalent' and 0.2 + 0.1 > 0.30 and hand([0.2] * 6, 0.1) == 'equivalent'
          and hand([-0.2] * 6, 0.1) == 'equivalent' and hand([0.2] * 6, 0.1001) == 'undecided')
    drop = lambda c: -1.0 if (c['kernel'], c['size']) == (OLD, M8) else 0.0
    s = A.stage2(A.load(s2_both(os.path.join(d, 'p1c'), s2_rate(shift=drop))))
    check('P1 is contradicted by a repeatable difference above 0.30 GB/s in both sessions',
          cell(s)['P1']['filtered']['outcome'] == 'contradicted' and s['P1']['per_cpu']['cpu2']['outcome'] == 'contradicted'
          and s['candidate'] == 'contradicted')
    up = lambda c: 20.0 if (c['kernel'], c['size']) == (NEW, M8) else 0.0
    s = A.stage2(A.load(s2_both(os.path.join(d, 'p2'), s2_rate(shift=up))))
    check('P2: a confirmed increase contradicts the prediction',
          s['P2'][NEW]['per_cpu']['cpu2']['outcome'] == 'contradicted' and s['P2'][ASM]['per_cpu']['cpu2']['outcome'] == 'supported')
    one = lambda c: 20.0 if (c['kernel'], c['size'], c['session'], c['cpu']) == (NEW, M8, 2, 2) else 0.0
    s = A.stage2(A.load(s2_both(os.path.join(d, 'p2u'), s2_rate(shift=one))))
    check('P2: a direction that differs between the sessions is undecided',
          s['P2'][NEW]['per_cpu']['cpu2']['outcome'] == 'undecided' and s['P2'][NEW]['per_cpu']['cpu41']['outcome'] == 'supported')
    flat = lambda c: 67.0 + noise(0.05, c['session'], c['cpu'], c['proc'], c['n'], c['phase'], c['widx'])
    dc = cell(A.stage2(A.load(s2_both(os.path.join(d, 'flat'), flat))))['decomposition']['filtered']
    check('decomposition: the shares are hidden when dG is not resolved',
          dc['resolved'] is False and dc['shares'] is None and 'not resolved' in dc['shares_why']
          and dc['dG']['median'] is not None and dc['new_term']['median'] is not None)
    s = A.stage2(A.load(s2_both(os.path.join(d, 'nx'), s2_rate(shift=lambda c: 2.0 if (c['kernel'], c['size']) == (NEW, M16) else 0.0),
                                sizes=(M8, M16))))
    check('no crossing is reported when the sign is the same at 8 and 16 MiB', cell(s)['crossing'][NEW]['word'] == 'not crossed')


def test_p3(root):
    d = os.path.join(root, 'p3')
    new = [65.0, 65.5, 66.0, 66.5, 67.0, 68.0]

    def rate(old=lambda c: 0.0, extra=lambda c: 0.0, asm=0.1, newv=new):
        def f(c):
            k = c['kernel']
            base = newv[c['p']] if k == NEW else 68.5 + asm * c['p'] if k == ASM else \
                67.0 + old(c) + noise(0.01, c['session'], c['cpu'], c['proc'], c['n'], c['phase'], c['widx'])
            return base + extra(c)
        return f

    def run(name, gate=True, **kw):
        s = A.p3(A.load([p3(d, 1, rate(**kw), name=name + '%d')]), gate)
        return cell(s)['filtered']
    r = run('ok')
    x = r[NEW]
    check('P3: compatible when coverage is present, traces are stable and the old range plus control limit is small',
          x['outcome'] == 'compatible' and near(x['load_range'], 3.0, 1e-4) and x['old_range'] + x['control_limit'] <= 0.30
          and near(x['control_limit'], 2 * max(abs(p['kernels'][OLD]['aa']) for p in r['processes']), 1e-9))
    check('P3 without coverage gives Insufficient data, not undecided',
          r[ASM]['outcome'] == 'Insufficient data' and 'below 2.0' in r[ASM]['why'] and near(r[ASM]['load_range'], 0.5, 1e-4))
    check('P3: new read and assembly read are decided separately; with coverage the assembly comparison is compatible',
          run('asmcov', asm=0.5)[ASM]['outcome'] == 'compatible')
    check('P3: every process keeps its trial rates, medians and marks',
          len(r['processes']) == 6 and len(r['processes'][0]['kernels'][NEW]['fourth']) == 4
          and r['processes'][0]['kernels'][OLD]['unstable'] is False)
    u = run('span', extra=lambda c: 0.5 if (c['kernel'], c['p'], c['rep']) == (NEW, 2, 3) else 0.0)
    check('P3 does not call unstable traces compatible (fourth-window span above 0.30 GB/s)',
          u[NEW]['outcome'] == 'Insufficient data' and len(u[NEW]['unstable']) == 1 and 'unstable' in u[NEW]['why']
          and u['processes'][2]['kernels'][NEW]['unstable'] is True and u[ASM]['unstable'] == [])
    u = run('drift', extra=lambda c: -0.5 if (c['kernel'], c['p'], c['rep'], c['phase'], c['widx']) == (OLD, 1, 2, 'target', 0) else 0.0)
    check('P3 does not call unstable traces compatible (first and fourth window differ by more than 0.30 GB/s)',
          u[NEW]['outcome'] == 'Insufficient data' and u[ASM]['outcome'] == 'Insufficient data'
          and u['processes'][1]['kernels'][OLD]['unstable'] is True)
    o = run('outlier', old=lambda c: -0.8 if c['p'] == 2 else 0.0)[NEW]
    check('P3 does not call a non-endpoint old-rate outlier compatible',
          o['outcome'] == 'undecided' and o['old_range'] > 0.7 and abs(o['old_endpoint_change']) < 0.1)
    o = run('endpoint', old=lambda c: -0.8 if c['p'] == 5 else 0.0)[NEW]
    check('P3: an old endpoint change beyond margin and control is contrary',
          o['outcome'] == 'contrary' and near(o['old_endpoint_change'], -0.8, 0.05))
    o = run('tie', newv=[65.0, 65.0, 66.0, 66.5, 68.0, 68.0])[NEW]
    procs = [p['proc'] for p in r['processes']]
    check('P3: a tie takes the earlier process of the schedule', o['endpoint_max'] == procs[4] and o['endpoint_min'] == procs[0])
    check('P3: a prefix gate that did not pass, or was not evaluated, gives Insufficient data',
          run('g0', gate=False)[NEW]['outcome'] == 'Insufficient data' and 'gate' in run('g1', gate=None)[NEW]['why'])

    def exact(name, oldp, aa, extra=lambda c: 0.0):
        """Old read without noise: process p has the median 67 + oldp[p]; process 0 has the A/A value aa."""
        def f(c):
            if c['kernel'] == OLD:
                wob = (aa / 2 if c['rep'] in (1, 3) else -aa / 2) if c['p'] == 0 else 0.0
                return 67.0 + oldp[c['p']] + wob
            return (new[c['p']] if c['kernel'] == NEW else 68.5 + 0.1 * c['p']) + extra(c)
        return cell(A.p3(A.load([p3(d, 1, f, name=name + '%d')]), True))['filtered']
    o = exact('lc-range', [0, 0.1, 0, 0, 0, 0], 0.12)[NEW]
    o2 = exact('lc-range-ok', [0, 0.1, 0, 0, 0, 0], 0.08)[NEW]
    check('P3: the control limit is part of compatibility: old range 0.10 with control limit 0.24 is undecided, with 0.16 compatible',
          o['outcome'] == 'undecided' and near(o['old_range'], 0.10, 1e-6) and near(o['control_limit'], 0.24, 1e-6)
          and o['unstable'] == [] and o2['outcome'] == 'compatible' and near(o2['control_limit'], 0.16, 1e-6))
    o = exact('lc-end', [0, 0, 0, 0, 0, 0.5], 0.12)[NEW]
    o2 = exact('lc-end-c', [0, 0, 0, 0, 0, 0.5], 0.05)[NEW]
    check('P3: an old endpoint change of 0.5 is undecided with control limit 0.24 and contrary with control limit 0.10',
          o['outcome'] == 'undecided' and near(o['old_endpoint_change'], 0.5, 1e-6) and near(o['control_limit'], 0.24, 1e-6)
          and o2['outcome'] == 'contrary' and near(o2['control_limit'], 0.10, 1e-6))
    bump = lambda v: lambda c: v if (c['kernel'], c['p'], c['rep']) == (NEW, 2, 3) else 0.0
    u, u2 = exact('span35', [0] * 6, 0.02, bump(0.35)), exact('span25', [0] * 6, 0.02, bump(0.25))
    check('P3: a fourth-window span of 0.35 GB/s is unstable, a span of 0.25 GB/s is not',
          u[NEW]['outcome'] == 'Insufficient data' and u['processes'][2]['kernels'][NEW]['unstable'] is True
          and near(u['processes'][2]['kernels'][NEW]['span'], 0.35, 1e-6)
          and u2[NEW]['outcome'] == 'compatible' and u2['processes'][2]['kernels'][NEW]['unstable'] is False)
    rows = lambda xm: [dict(proc=i, kernels={NEW: dict(median=m, unstable=False, aa=0.0), OLD: dict(median=67.0, unstable=False, aa=0.0)})
                       for i, m in enumerate(xm)]
    check('P3: a load-only range of exactly 2.0 GB/s has coverage, a range of 1.99 GB/s has not',
          A.p3_decide(rows([65.0, 65.5, 66.0, 66.5, 66.8, 67.0]), NEW, True)['outcome'] == 'compatible'
          and A.p3_decide(rows([65.01, 65.5, 66.0, 66.5, 66.8, 67.0]), NEW, True)['outcome'] == 'Insufficient data')


def test_stage3(root):
    d = os.path.join(root, 's3')
    real = lambda c: (-3.0 if c['widx'] == 0 else -1.0) if (c['phase'], c['tgt_kernel'], c['pred']) == ('target', OLD, 'read@8M:300') else 0.0
    s = A.stage3(A.load([s3(d, 1, real, name='real1'), s3(d, 2, real, name='real2')]))
    c = cell(s)
    p = c['primary']['new_predecessor_on_old']
    check('a real predecessor effect is found', p['first']['filtered']['repeatable'] and p['first']['filtered']['sign'] == -1
          and near(p['first']['filtered']['median'], -3.0, 0.05) and p['first']['filtered']['n_terms'] == 2
          and s['confirm']['new_predecessor_on_old']['first']['confirmed_both'])
    check('persistence: the same contrast is reported in the fourth window',
          near(p['fourth']['filtered']['median'], -1.0, 0.05) and s['confirm']['new_predecessor_on_old']['fourth']['confirmed_both'])
    h = c['primary']['history_interaction']['first']['filtered']
    check('history interaction uses four spreads and has the sign of the gain change',
          h['n_terms'] == 4 and near(h['median'], 3.0, 0.08) and h['repeatable'])
    a = c['primary']['asm_predecessor_on_old']['first']['filtered']
    check('the assembly-predecessor replication is tested alone and is not found here',
          a['repeatable'] is False and not s['confirm']['asm_predecessor_on_old']['first']['confirmed_both'])
    g = c['gain_pct']['new']['first']['filtered']['gain_pct']
    check('percentage gain per process, predecessor and window', g['n'] == 6 and near(g['median'], 100 * (67.6 / 64.0 - 1), 0.1))
    pp = c['gain_change_pp']['new']['first']['filtered']
    go = c['gain_pct']['old']['first']['filtered']['gain_pct']['median']
    check('change of gain between predecessors in percentage points, per process (design line 222)',
          pp['n'] == 6 and len(pp['units']) == 6 and near(pp['median'], 100 * (67.6 / 64.0 - 1) - go, 0.1)
          and pp['median'] > 4 and near(c['gain_change_pp']['asm']['first']['filtered']['median'], 0.0, 0.1)
          and 'old' not in c['gain_change_pp'], str(pp))
    check('other contrasts are labelled exploratory', len(c['exploratory']) == 18
          and all(e['filtered']['label'].startswith('exploratory') for e in c['exploratory']))
    check('R(T|P,w) is given for all 12 conditions', len(c['R']) == 12 and near(c['R']['old|new']['first']['filtered']['median'], 64.0, 0.03))
    quiet = c['previous_target'][OLD]['first']['span']

    def not_found(name, effect, seeds=(1, 2, 3, 4, 5)):
        res = []
        for seed in seeds:
            cc = cell(A.stage3(A.load([s3(d, 1, effect, seed=seed, cpus=(2,), name='%s%d' % (name, seed))])))
            res.append(cc)
        return res
    trend = not_found('trend', lambda c: -0.02 * c['n'])
    check('an order trend alone is not called a predecessor effect (5 schedules)',
          all(x['primary'][n]['first']['filtered']['repeatable'] is False for x in trend for n in x['primary']))
    offs = [-2.0, -1.0, 0.0, 0.5, 1.0, 2.0]
    alloc = not_found('alloc', lambda c: offs[c['p']])
    check('an allocation-only difference between processes is not called a predecessor effect (5 schedules)',
          all(x['primary'][n][w]['filtered']['repeatable'] is False for x in alloc for n in x['primary'] for w in ('first', 'fourth'))
          and alloc[0]['R']['old|old']['first']['filtered']['range'] > 3.5)
    prev = not_found('prev', lambda c: -3.0 if (c['phase'], c['tgt_kernel'], c['prev_tgt']) == ('target', OLD, 'read@8M') else 0.0)
    check('an effect caused solely by the target of the previous trial is not attributed to the predecessor (5 schedules)',
          all(x['primary'][n]['first']['filtered']['repeatable'] is False for x in prev for n in x['primary']))
    spans = [x['previous_target'][OLD]['first']['span'] for x in prev]
    check('that effect is visible in the previous-target diagnostic, and the diagnostic is quiet without it',
          min(spans) > 0.30 and quiet < 0.03 and 'read' in prev[0]['previous_target'][OLD]['first']['by_previous_target'],
          '%s %s' % (spans, quiet))


def test_gates(root):
    d = os.path.join(root, 'g')
    m = A.margin_for(0.07, 'one_rate')
    check('margin: twice L0 rounded up to the next 0.05 GB/s', m['margin'] == 0.15 and not m['clipped'] and m['forecast'] == 'feasible'
          and A.margin_for(0.051, 'one_rate')['margin'] == 0.15 and A.margin_for(0.075, 'one_rate')['margin'] == 0.15
          and A.margin_for(0.0751, 'one_rate')['margin'] == 0.2)
    check('margin: a product that is 0.075 or 0.15 on paper is not rounded up one step too far',
          0.025 * 3 > 0.075 and A.margin_for(0.025 * 3, 'one_rate')['margin'] == 0.15
          and 0.05 * 3 > 0.15 and A.margin_for(0.05 * 3, 'four_rate')['margin'] == 0.30)
    m = A.margin_for(0.25, 'one_rate')
    check('clipped margin (note 2): 2 x L0 above the upper bound is clipped to it',
          m['margin'] == 0.30 and m['clipped'] and m['unclipped'] == 0.5 and m['forecast'] == 'feasible'
          and A.margin_for(0.0, 'two_rate')['margin'] == 0.10 and A.margin_for(0.4, 'four_rate')['margin'] == 0.60
          and A.margin_for(0.12, 'four_rate')['margin'] == 0.25)
    check('forecast is precision insufficient when L0 is at or above the margin',
          A.margin_for(0.30, 'one_rate')['forecast'] == 'precision insufficient'
          and A.margin_for(0.29, 'one_rate')['forecast'] == 'feasible'
          and A.margin_for(0.7, 'four_rate')['forecast'] == 'precision insufficient')

    def s3g(name, effect, a, sessions=(1, 2), margin=0.30, sources=()):
        folders = [prefix_gate(d, 'S3G', s, aa_rate(effect, a), name='%s-s%d' % (name, s)) for s in sessions]
        return A.gate(A.load(folders), 'S3G', margins_file(d, {'S3G': ('one_rate', margin)}, sources))
    g = s3g('clip-pass', {NEW: 0.04, ASM: 0.02}, 0.125)
    u = g['uses']['S3G']
    r = cell(u)['contrasts'][0]['filtered']
    check('gate S3G: 6 contrasts per CPU and session, two spreads each',
          len(cell(u)['contrasts']) == 6 and r['n_terms'] == 2 and len(u['cells']) == 4)
    check('clipped margin (note 2): a limit of 0.25 under a margin of 0.30 passes a median of 0.04',
          g['passed'] and u['overall'] == 'pass' and near(r['limit'], 0.25) and near(abs(r['median']), 0.04)
          and g['statement'] == 'equivalence established')
    check('the largest median that could pass is printed: margin minus limit', near(r['max_passing_median'], 0.05)
          and 'largest median that could pass +0.050' in A.text(dict(test_data=False, folders=[], counts={}, exclusions=[], gates={'S3G': g})))
    g = s3g('clip-fail', {NEW: 0.10}, 0.125)
    words = {c['filtered']['label']: c['filtered']['outcome'] for c in cell(g['uses']['S3G'])['contrasts']}
    check('clipped margin (note 2): a median of 0.10 inside the limit does not pass; no condition is relaxed',
          not g['passed'] and g['uses']['S3G']['overall'] == 'precision insufficient'
          and words['oldread first: after oldread - after read'] == 'precision insufficient'
          and words['oldread first: after oldread - after asmread'] == 'pass')
    g = s3g('noisy', {}, 0.40)
    u = g['uses']['S3G']
    check('a noisy equivalence check fails, and is called precision insufficient, not a mode effect',
          not g['passed'] and u['overall'] == 'precision insufficient' and u['counts'] == {'precision insufficient': 24}
          and cell(u)['contrasts'][0]['filtered']['max_passing_median'] is None
          and g['statement'] == 'prefix equivalence not established')
    g = s3g('quiet', {}, 0.02)
    check('the same check with quiet repeats passes', g['passed'] and g['uses']['S3G']['counts'] == {'pass': 24})
    g = s3g('carry', {NEW: -0.5}, 0.02)
    check('a repeatable previous-activity difference is called a resolved difference',
          not g['passed'] and g['uses']['S3G']['overall'] == 'resolved difference'
          and g['uses']['S3G']['counts'] == {'pass': 8, 'resolved difference': 16})
    g = s3g('half', {}, 0.02, sessions=(1,))
    check('a gate needs both CPUs in both sessions: one session alone does not pass',
          not g['passed'] and g['uses']['S3G']['counts'] == {'incomplete': 12, 'pass': 12}
          and g['uses']['S3G']['overall'] == 'not established')

    g = s3g('above-limit', {NEW: 0.06}, 0.01)
    u = g['uses']['S3G']
    r = [c['filtered'] for c in cell(u)['contrasts'] if c['filtered']['label'] == 'oldread first: after oldread - after read'][0]
    check('a median of 0.06 above a limit of 0.02 does not pass although median plus limit is inside the margin of 0.30',
          near(abs(r['median']), 0.06) and near(r['limit'], 0.02) and r['outcome'] == 'resolved difference'
          and not g['passed'] and u['counts'] == {'pass': 8, 'resolved difference': 16}
          and cell(u)['passed'] is False and all(c['passed'] is False for c in u['cells'].values()))
    gd = lambda m, lim, margin: A.gate_decide(dict(complete=True, median=m, limit=lim, repeatable=False), margin)['outcome']
    check('gate boundaries: a limit equal to the margin does not pass; median plus limit of exactly the margin passes, '
          'also when the binary sum is 0.30000000000000004',
          gd(0.0, 0.30, 0.30) == 'precision insufficient' and gd(0.0, 0.29, 0.30) == 'pass'
          and gd(0.15, 0.15, 0.30) == 'pass' and 0.1 + 0.2 > 0.30 and gd(0.1, 0.2, 0.30) == 'pass'
          and gd(-0.1, 0.2, 0.30) == 'pass' and gd(0.1001, 0.2, 0.30) == 'precision insufficient')

    def mark(L):                                                # one involuntary context switch in the first trial
        i = [i for i, x in enumerate(L) if x.startswith('E,0,')][0]
        return L[:i] + [setf(L[i], 5, 1)] + L[i + 1:]
    folders = [prefix_gate(d, 'S3G', s, aa_rate({}, 0.02), name='marked-s%d' % s) for s in (1, 2)]
    rewrite(folders[0], 'S3G', mark)
    g = A.gate(A.load(folders), 'S3G', margins_file(d, {'S3G': ('one_rate', 0.30)}))
    u = g['uses']['S3G']
    cs_ = cell(u)['contrasts']
    check('a gate decides on the filtered estimate: one disturbed trial leaves its contrasts incomplete and the gate '
          'does not pass, although the unfiltered estimate passes',
          not g['passed'] and u['counts'] == {'incomplete': 4, 'pass': 20} and u['overall'] == 'not established'
          and all(c['unfiltered']['outcome'] == 'pass' and c['unfiltered']['n_valid'] == 6 for c in cs_)
          and sorted(c['filtered']['n_valid'] for c in cs_) == [5, 5, 5, 5, 6, 6] and cell(u)['passed'] is False
          and cell(u, 'cpu41/s1')['passed'] is True)

    def refused(fn):
        try:
            fn()
            return False
        except A.GateError:
            return True
    check('the gate refuses a margins file that names the gated batch as its source',
          refused(lambda: s3g('src', {}, 0.02, sources=['src-s1'])) and not refused(lambda: s3g('src', {}, 0.02, sources=['other'])))
    folders = [prefix_gate(d, 'P3G', s, aa_rate({}, 0.02)) for s in (1, 2)]
    procs = A.load(folders)
    check('the gate refuses to run without a frozen margin for its use',
          refused(lambda: A.gate(procs, 'P3G', margins_file(d, {'S3G': ('one_rate', 0.3)}))))
    check('the gate refuses margins that were made from test data when the gated batch is real',
          refused(lambda: A.gate(procs, 'P3G', dict(margins_file(d, {'P3G': ('one_rate', 0.10)}), test=True))))
    g = A.gate(procs, 'P3G', margins_file(d, {'P3G': ('one_rate', 0.10)}))
    check('gate P3G: 18 contrasts per CPU and session', len(cell(g['uses']['P3G'])['contrasts']) == 18 and g['passed'])
    s = A.summary(procs + A.load([p3(d, 1, lambda c: 67.0 + c['p'] * (c['kernel'] == NEW), name='p3gate%d')]),
                  margins_file(d, {'P3G': ('one_rate', 0.10)}))
    s0 = A.summary(A.load([os.path.join(d, 'p3gate1')]))
    check('the gate status is passed to P3: passed gate decides, no gate gives Insufficient data',
          s['P3']['gate_passed'] is True and cell(s['P3'])['filtered'][NEW]['outcome'] == 'compatible'
          and cell(s0['P3'])['filtered'][NEW]['outcome'] == 'Insufficient data')

    f1 = [mode_gate(d, 'BIN', s) for s in (1, 2)]
    g = A.gate(A.load(f1), 'BIN', margins_file(d, {'BIN:oldread@8M': ('one_rate', 0.10)}))
    labels = [c['filtered']['label'] for c in cell(g['uses']['BIN:oldread@8M'])['contrasts']]
    check('gate BIN: the first and the last target window', g['passed'] and len(labels) == 2
          and 'first' in labels[0] and 'fourth' in labels[1])
    cs = A.load([mode_gate(d, 'CS', s) for s in (1, 2)])
    g = A.gate(cs, 'CS', margins_file(d, {'CS:oldread@8M:fourth': ('one_rate', 0.10)}))
    u = g['uses']['CS:oldread@8M:fourth']
    check('gate CS: three mode pairs, one rate uses two spreads',
          g['passed'] and len(cell(u)['contrasts']) == 3 and cell(u)['contrasts'][0]['filtered']['n_terms'] == 2
          and refused(lambda: A.gate(cs, 'CS', margins_file(d, {'CS:read@8M:fourth': ('one_rate', 0.1)}))))
    eff = lambda c: MEAN[c['kernel']] + (-0.5 if (c['count'], c['phase']) == ('read', 'target') else 0.0) \
        + noise(0.005, c['session'], c['cpu'], c['proc'], c['n'], c['widx'], c['phase'])
    os.rename(os.path.join(d, 'bwx8-CS-s1'), os.path.join(d, 'cs-quiet-1'))
    os.rename(os.path.join(d, 'bwx8-CS-s2'), os.path.join(d, 'cs-quiet-2'))
    g = A.gate(A.load([mode_gate(d, 'CS', s, eff) for s in (1, 2)]), 'CS', margins_file(d, {'CS:oldread@8M:fourth': ('one_rate', 0.10)}))
    check('gate CS: a counter mode that changes the rate is a resolved difference, not a pass',
          not g['passed'] and g['uses']['CS:oldread@8M:fourth']['overall'] == 'resolved difference'
          and g['statement'] == 'mode equivalence not established')

    def no_counter(state, xrow):
        """Every trial with count open or read reports that its counter group did not open."""
        def fn(L):
            out = []
            for line in L:
                a = line.split(',')
                if a[0] == 'E' and a[9] in ('open', 'read'):
                    out += ['X,%s,count_open,5 of 5 events did not open' % a[1]] if xrow else []
                    line = setf(line, 9, state or a[9])
                out.append(','.join(a[:3] + ['NA', 'NA', a[5]] + ['NA'] * 5) if a[0] == 'C' else line)
            return out
        return fn
    for state, xrow, what in (('fail', True, 'count_state fail and an X row count_open'),
                              ('fail', False, 'count_state fail alone'), (None, True, 'an X row count_open alone')):
        root = os.path.join(d, 'nocount-%s-%s' % (state, xrow))
        procs = A.load([rewrite(mode_gate(root, 'CS', s), 'CS', no_counter(state, xrow)) for s in (1, 2)])
        g = A.gate(procs, 'CS', margins_file(d, {'CS:oldread@8M:fourth': ('one_rate', 0.10)}))
        u = g['uses']['CS:oldread@8M:fourth']
        r = cell(u)['contrasts'][0]
        check('gate CS: an unreported counter failure cannot pass: with %s no mode comparison has its trials' % what,
              not g['passed'] and g['statement'] == 'mode equivalence not established' and u['counts'] == {'incomplete': 12}
              and all(r[e]['n_valid'] == 0 for e in ('filtered', 'unfiltered'))
              and 'did not run the counter mode of the plan' in r['filtered']['units'][0]['why']
              and all(t.usable(True) for t in procs[0].trials.values())
              and A.cell_rate(procs[0], {'tgt': (OLD, M8), 'count': 'closed'}, 'fourth', True)['R'] is not None
              and any(e['kind'] == 'counts not interpreted' for e in A.exclusions(procs)))
    cm = A.load([mode_gate(d, 'CM', s) for s in (1, 2)])
    g = A.gate(cm, 'CM', margins_file(d, {'CM:rate:first': ('one_rate', 0.10), 'CM:history:first': ('two_rate', 0.10),
                                          'CM:interaction:first': ('four_rate', 0.20)}))
    n = {k: (len(cell(u)['contrasts']), cell(u)['contrasts'][0]['filtered']['n_terms']) for k, u in g['uses'].items()}
    check('gate CM: one rate 2 spreads, two-rate contrast 4, four-rate interaction 8, three mode pairs each',
          n == {'CM:rate:first': (12, 2), 'CM:history:first': (3, 4), 'CM:interaction:first': (3, 8)} and g['passed'], str(n))

    # forecast: L0 per selected use (note 3)
    wobble = lambda c: (0.25 if c['rep'] in (1, 3) else -0.25) if c['kernel'] == ASM else 0.0
    src = s2_both(os.path.join(d, 'fc'), s2_rate(shift=wobble), sizes=(M8,))
    out = os.path.join(d, 'margins-fc.json')
    rc, txt, _ = run_cli('forecast', *src, '--use', 'P3G', '--use', 'S3G', '--use', 'CS:oldread@8M:fourth',
                         '--use', 'CS:asmread@8M:fourth', '-o', out)
    mj = json.load(open(out))
    u = mj['uses']
    check('forecast: L0 per selected use (note 3); a calm use is not failed by a noisier condition it does not need',
          rc == 0 and u['S3G']['forecast'] == 'feasible' and u['S3G']['margin'] == 0.10 and u['S3G']['L0'] < 0.05
          and u['CS:oldread@8M:fourth']['forecast'] == 'feasible'
          and u['P3G']['forecast'] == 'precision insufficient' and u['P3G']['margin'] == 0.30 and u['P3G']['clipped']
          and near(u['P3G']['L0'], 1.0, 0.05) and u['CS:asmread@8M:fourth']['forecast'] == 'precision insufficient', txt)
    check('forecast writes margins.json with the names of its source batches, and prints one line per use',
          mj['sources'] == sorted(os.path.basename(x) for x in src) and mj['format'] == 'bwx8-margins v1'
          and 'P3G: L0' in txt and 'precision insufficient' in txt and u['S3G']['spreads'] == 2
          and len(u['P3G']['cells']) == 24)
    check('forecast: 6 processes per CPU, session and condition, stated in the printed line',
          u['S3G']['n_processes'] == 6 and u['S3G']['n_processes_filtered_min'] == 6
          and all(p['n_processes'] == 6 for c in u['P3G']['cells'] for p in c['parts'])
          and near(u['S3G']['L0_filtered'], u['S3G']['L0'], 1e-12) and '6 processes per CPU, session and condition' in txt)

    def loud(c):                                                # old read of sets 2 to 6: A/A value 1.0 GB/s
        big = c['rep_set'] != 1 and c['kernel'] == OLD
        return 67.0 + (0.5 if big else 0.01) * (1 if c['rep'] in (1, 3) else -1)
    marks = lambda L, cpu, size, r, k: edit(L, 'E,1,', lambda x: setf(x, 5, 1)) if (r != 1 and k == OLD) else L
    fm = os.path.join(d, 'fc-marked.json')
    rc, txt, _ = run_cli('forecast', *s2_both(os.path.join(d, 'fcm'), loud, sizes=(M8,), hook=marks), '--use', 'S3G', '-o', fm)
    u = json.load(open(fm))['uses']['S3G']
    check('forecast is not softened: a process with a disturbed trial stays in the maximum of L0',
          near(u['L0'], 2.0, 1e-6) and u['margin'] == 0.30 and u['forecast'] == 'precision insufficient'
          and near(u['L0_filtered'], 0.04, 1e-6) and u['n_processes_filtered_min'] == 1 and u['n_processes'] == 6
          and 'L0 2.000 GB/s' in txt and 'with marked trials left out L0 is 0.040 GB/s' in txt
          and 'the fewest: 1 of 6 processes' in txt, txt)
    five = lambda L, cpu, size, r, k: None if (cpu, r, k) == (41, 4, OLD) else L
    cutE = lambda L, cpu, size, r, k: edit(L, 'E,3,', lambda x: None) if (cpu, r, k) == (41, 4, OLD) else L
    res = [A.forecast(A.load(s2_both(os.path.join(d, n), s2_rate(), sizes=(M8,), hook=h)), ['S3G', 'CS:read@8M:first'], [])['uses']
           for n, h in (('fc5', five), ('fc5e', cutE))]
    check('forecast: a CPU and session with 5 processes, or 5 processes with all trials, gives Insufficient data and no margin',
          all(u['S3G']['forecast'] == 'Insufficient data' and u['S3G']['margin'] is None and len(u['S3G']['why']) == 4
              and 'cpu41/s1' in u['S3G']['why'][0] and u['CS:read@8M:first']['forecast'] == 'feasible' for u in res)
          and '5 processes ran' in res[0]['S3G']['why'][0] and '6 processes ran' in res[1]['S3G']['why'][0]
          and '5 of them' in res[1]['S3G']['why'][0], str(res[0]['S3G'].get('why')))
    quiet = [os.path.join(d, 'quiet-s%d' % s) for s in (1, 2)]
    rc, txt, _ = run_cli('summary', *quiet, '--margins', out, '-o', os.path.join(d, 'sum.json'))
    rc2, _, err = run_cli('summary', *quiet, *src, '--margins', out, '-o', os.path.join(d, 'sum2.json'))
    check('command line: a gate runs with the forecast margins of an earlier batch',
          rc == 0 and json.load(open(os.path.join(d, 'sum.json')))['gates']['S3G']['passed'] is True and 'gate S3G' in txt
          and rc2 == 0)
    with open(out, 'w') as fh:
        json.dump(dict(mj, sources=mj['sources'] + ['quiet-s1']), fh)
    rc, _, err = run_cli('summary', *quiet, '--margins', out, '-o', os.path.join(d, 'sum3.json'))
    check('command line: the summary refuses a margins file whose source is the gated batch', rc == 2 and 'refused' in err)
    rc, txt, _ = run_cli('forecast', *src, '--use', 'CM:rate:first', '-o', os.path.join(d, 'm2.json'))
    check('forecast without same-condition data gives Insufficient data and no margin',
          json.load(open(os.path.join(d, 'm2.json')))['uses']['CM:rate:first']['margin'] is None and 'Insufficient data' in txt)
    real = lambda c: 0.0
    m3 = A.forecast(A.load([s3(d, 1, real, name='fc-s3')]), ['CM:rate:first', 'CM:history:fourth', 'CM:interaction:first'], ['fc-s3'])
    q = {k: (v['quantity'], v['spreads'], len(v['cells'][0]['parts'])) for k, v in m3['uses'].items()}
    check('forecast for mixed-sequence counters comes from the Stage 3 batch, with 2, 4 and 8 spreads',
          q == {'CM:rate:first': ('one_rate', 2, 1), 'CM:history:fourth': ('two_rate', 4, 2),
                'CM:interaction:first': ('four_rate', 8, 4)}, str(q))


def test_sustained_counters_bins(root):
    d = os.path.join(root, 's4')
    step = lambda c: MEAN[c['kernel']] + (3.0 if c['kernel'] == ASM and c['widx'] >= 10 else 0.0) + noise(0.01, c['proc'], c['widx'])
    r = A.sustained(A.load([s4(d, 'S4', step)]))
    asm = [x for x in r if x['kernel'] == ASM][0]
    old = [x for x in r if x['kernel'] == OLD][0]
    t = asm['transitions']
    check('sustained: the full window trace, its median and range per process',
          len(r) == 3 and len(asm['trace']) == 20 and near(asm['min'], 68.5, 0.02) and near(asm['max'], 71.5, 0.02)
          and near(asm['median'], 70.0, 0.05) and near(asm['trace'][-1]['t_end_s'], 6.0, 0.01))
    check('sustained: a transition is described by its time and its two rates, without a level label',
          len(t) == 1 and t[0]['widx'] == 10 and near(t[0]['rate_before'], 68.5, 0.02) and near(t[0]['rate_after'], 71.5, 0.02)
          and near(t[0]['at_s'], 3.0, 0.01) and sorted(t[0]) == ['at_s', 'change', 'rate_after', 'rate_before', 'widx']
          and old['transitions'] == [])

    def hook(L, k):
        if k == OLD:                                            # state fail, but the C rows still hold numbers
            return edit(L, 'E,0,', lambda x: setf(x, 9, 'fail'))
        if k == NEW:                                            # window 3 multiplexed, window 4 lost its C row,
            L = edit(L, 'C,0,3,', lambda x: setf(x, 4, int(x.split(',')[4]) // 2))
            L = edit(L, 'C,0,4,', lambda x: None)               # window 5: one event did not open, window 6: all NA
            L = edit(L, 'C,0,6,', lambda x: ','.join(x.split(',')[:3] + ['NA'] * 8))
            return edit(L, 'C,0,5,', lambda x: setf(x, 8, 'NA'))
        return L
    flat = lambda c: MEAN[c['kernel']]
    r = A.sustained(A.load([s4(d, 'C4', flat, count='read', hook=hook)]))
    old, new, asm = ([x for x in r if x['kernel'] == k][0] for k in A.KERNELS)
    w = asm['counter_windows'][0]
    check('counters: counts per 64 B read, instructions per byte, cycles per byte, cycles per thread CPU second',
          asm['counters']['interpretable'] == 20 and near(w['per_64B']['l2d_refill'], 1.0, 1e-6)
          and near(w['per_64B']['l1d_refill'], 0.5, 1e-6) and near(w['instructions_per_byte'], 0.125, 1e-6)
          and near(w['cycles_per_byte'], 3 / 68.5, 1e-4) and near(w['cycles_per_cpu_s'], 3e9, 2000))
    check('an unreported counter failure cannot pass: count_state fail and NA counts are never interpreted',
          old['counters']['interpretable'] == 0 and all(x['per_64B'] == {} and x['cycles_per_byte'] is None
                                                        for x in old['counter_windows'])
          and old['counters']['cycles_per_byte']['n'] == 0)
    check('the timing rows of a failed count are kept', len(old['trace']) == 20 and near(old['median'], 67.0, 0.01)
          and all(near(x['rate'], 67.0, 0.01) for x in old['counter_windows']))
    cw = new['counter_windows']
    check('multiplexed counts and a missing C row are rejected for interpretation; an event that did not open is None',
          new['counters']['interpretable'] == 17 and 'multiplexed' in cw[3]['why'][0] and cw[4]['why'] == ['no C row']
          and 'NA' in cw[6]['why'][0] and cw[6]['per_64B'] == {}
          and cw[5]['interpretable'] and cw[5]['per_64B']['l1d_refill'] is None and cw[5]['per_64B']['l2d_refill'] is not None
          and new['counters']['per_64B']['l1d_refill']['n'] == 16 and cw[3]['rate'] is not None)
    ex = A.exclusions(A.load([os.path.join(d, 'bwx8-C4-s1')]))
    check('the failed count is in the exclusion table', any(e['kind'] == 'counts not interpreted' for e in ex))

    procs = A.load([mode_gate(os.path.join(d, 'bin'), 'BIN', 1, cpus=(2,))])
    t = [t for t in procs[0].trials.values() if t.bins][0]
    parts = A.bin_parts(t, 0)
    w = t.W[('target', 0)]
    check('bins: 30 bins per window, read with their real boundaries', len(parts) == 30 and parts[0][0] == w['t0']
          and sum(p[2] for p in parts) == w['bytes'] and parts[-1][1] == w['t1'])
    uneven = [(0, 10, 1000), (10, 110, 1000)]
    check('bins are aggregated by summing bytes and time, never by averaging rates',
          near(A.sum_rate(parts), t.rate('first'), 1e-12) and near(A.sum_rate(uneven), 2000 / 110)
          and not near(A.sum_rate(uneven), (100 + 10) / 2, 1.0)
          and A.rebin(uneven + [(110, 120, 500)], 2) == [(0, 110, 2000), (110, 120, 500)])
    L = [open(os.path.join(d, 'bin', 'bwx8-BIN-s1', 'BIN.csv')).read().split('\n')]
    L[0] = edit(L[0], 'B,1,0,29,', lambda x: setf(x, 5, int(x.split(',')[5]) + M8))
    procs = A.load([put(os.path.join(d, 'bin'), 'badbin', 'BIN', L)])
    check('bins that hold more bytes than their window are caught',
          'bin 29' in '; '.join(procs[0].trials[1].reject) and not procs[0].trials[0].reject)


def test_b6w(root):
    d = os.path.join(root, 'b6')
    s = A.b6w(A.load([b6w(os.path.join(d, 'a'), 1)]))
    c = cell(s)
    check('B6W: 8 old-read pairs after assembly read per process, positions 7,8 and 10,11 in 4 rounds',
          len(c['processes']) == 2 and all(len(p['pairs']) == 8 for p in c['processes'])
          and c['processes'][0]['pairs'][1]['positions'] == [10, 11] and near(c['processes'][0]['pairs'][0]['difference'], -3.0, 0.01)
          and near(c['processes'][0]['pairs'][0]['asm_before'], 68.5, 0.01))
    check('B6W: reproduced when the first interval is slower in all 8 pairs in both processes',
          c['reproduced'] is True and cell(s, 'cpu41/s1')['reproduced'] is True)
    s = A.b6w(A.load([b6w(os.path.join(d, 'b'), 1, bad_pair=(2, 1, 3, 10))]))
    check('B6W: not reproduced on a CPU and session where one of the 16 pairs is not slower',
          cell(s)['reproduced'] is False and cell(s, 'cpu41/s1')['reproduced'] is True)
    s = A.b6w(A.load([b6w(os.path.join(d, 'c'), 1, nproc=1)]))
    check('B6W: one process alone gives no verdict', cell(s)['reproduced'] is None and 'needs 2' in cell(s)['why'])
    c = cell(A.b6w(A.load([os.path.join(d, 'c', 'bwx8-B6W-s1')] * 2)))
    check('B6W: one process that is read twice is not counted as two fresh processes',
          len(c['processes']) == 2 and c['reproduced'] is None and 'needs 2' in c['why']
          and all('mixing' in p['why'][0] and p['all_slower'] is None for p in c['processes']))


def test_test_data_and_cli(root):
    d = os.path.join(root, 't')
    real = s2_both(os.path.join(d, 'real'), s2_rate(), sizes=(M1, M8, M16))
    test = s2_both(os.path.join(d, 'test'), s2_rate(), sizes=(M1, M8, M16), test=1)
    out = os.path.join(d, 'summary.json')
    rc, txt, _ = run_cli('summary', *test, '-o', out)
    s = json.load(open(out))

    def decisions(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in A.DECISION_KEYS and not isinstance(v, (dict, list)):
                    yield v
                else:
                    yield from decisions(v)
        elif isinstance(x, list):
            for v in x:
                yield from decisions(v)

    # every step, a margins file and the forecast command, once with test=1 and once with test=0
    WORDS = ('equivalen', 'contradicted', 'undecided', 'supported', 'compatible', 'contrary', 'nsufficient', 'feasible',
             'resolved', 'established', 'repeatable', 'distinguished', 'signs differ', 'crossed', 'incomplete', 'unstable',
             'reproduced: True', 'reproduced: False', 'pass')
    OUTCOME_KEYS = ('pass', 'resolved difference', 'precision insufficient', 'not established', 'incomplete', 'equivalent',
                    'contradicted', 'undecided', 'supported', 'compatible', 'contrary', 'feasible', 'Insufficient data')
    PLAIN_BOOLS = ('test_data', 'test', 'complete', 'clipped', 'interpretable', 'first_slower')
    USES = ('P3G', 'S3G', 'BIN:oldread@8M', 'CS:oldread@8M:fourth', 'CM:rate:first', 'CM:history:first', 'CM:interaction:first')

    def leaks(x, key=None):
        """Decision words in the strings, outcome words used as keys, and booleans outside the plain facts."""
        if isinstance(x, dict):
            for k, v in x.items():
                if k in OUTCOME_KEYS:
                    yield 'key %s' % k
                yield from leaks(v, k)
        elif isinstance(x, list):
            for v in x:
                yield from leaks(v, key)
        elif isinstance(x, bool):
            if key not in PLAIN_BOOLS:
                yield 'boolean %s' % key
        elif isinstance(x, str) and key != 'banner':
            yield from ('string %s: %s' % (key, w) for w in WORDS if w in x)

    def text_leaks(txt):
        txt = txt.replace(A.BANNER, '').replace('largest median that could pass', '')
        return [w for w in WORDS + ('True', 'False') if w in txt]

    def chain(name, flag):
        root = os.path.join(d, name)
        quiet = lambda c: MEAN[c['kernel']]
        fs = s2_both(root, s2_rate()) + [s3(root, s, lambda c: 0.0, name='s3-%d' % s) for s in (1, 2)]
        gated = [prefix_gate(root, st, s, aa_rate({}, 0.02)) for st in ('P3G', 'S3G') for s in (1, 2)]
        gated += [mode_gate(root, st, s) for st in ('BIN', 'CS', 'CM') for s in (1, 2)]
        gated += [p3(root, 1, lambda c: 67.0 + c['p'] * (c['kernel'] == NEW)), b6w(root, 1), s4(root, 'S4', quiet),
                  s4(root, 'C4', quiet, count='read')]
        for f in fs + gated:
            step = [x[:-4] for x in os.listdir(f) if x.endswith('.csv')][0]
            rewrite(f, step, lambda L: [x.replace('M,plan.test,0', 'M,plan.test,%d' % flag) for x in L])
        mf, sf = os.path.join(root, 'margins.json'), os.path.join(root, 'summary.json')
        rc1, t1, _ = run_cli('forecast', *fs, *sum((['--use', x] for x in USES), []), '-o', mf)
        rc2, t2, err = run_cli('summary', *fs, *gated, '--margins', mf, '-o', sf)
        hand = os.path.join(root, 'hand')                       # margins that carry the word feasible
        os.makedirs(hand)
        margins_file(hand, {u: (A.use_plan(u)[0], 0.20) for u in USES})
        rc3, t3, _ = run_cli('summary', *fs, *gated, '--margins', os.path.join(hand, 'margins.json'), '-o', sf + '2')
        return rc1, rc2 or rc3, t1, t2 + t3, [json.load(open(mf)), json.load(open(sf + '2'))], json.load(open(sf)), err
    rc1, rc2, t1, t2, (mj, sj2), sj, err = chain('chain1', 1)
    found = sorted(set(leaks(sj)) | set(leaks(mj)) | set(leaks(sj2)))
    check('test=1, every step with margins: no decision word, outcome key or decision boolean in the summary and the forecast',
          rc1 == 0 and rc2 == 0 and found == [] and text_leaks(t1) == [] and text_leaks(t2) == []
          and t1.startswith('TEST DATA') and t2.startswith('TEST DATA') and sj['test_data'] is True and mj['test'] is True
          and sj['steps'] == ['B6W', 'BIN', 'C4', 'CM', 'CS', 'P3', 'P3G', 'S2', 'S3', 'S3G', 'S4'],
          '%s %s %s %s' % (found[:8], text_leaks(t1), text_leaks(t2), err))
    g = sj['gates']['P3G']['uses']['P3G']
    check('test=1 keeps the numbers of the gates, of P3 and of the forecast',
          g['margin'] == 0.10 and g['counts'] is None and near(cell(g)['contrasts'][0]['filtered']['limit'], 0.04)
          and near(cell(sj['P3'])['filtered'][NEW]['load_range'], 5.0, 1e-6) and sj['P3']['gate_passed'] is None
          and mj['uses']['S3G']['margin'] == 0.10 and mj['uses']['S3G']['L0'] > 0 and mj['uses']['S3G']['forecast'] is None
          and len(cell(sj['B6W'])['processes'][0]['pairs']) == 8 and 'forecast: no decision' in t1)
    whys = lambda s: [c[e][x]['why'] for c in s['P3']['cells'].values() for e in ('filtered', 'unfiltered') for x in (NEW, ASM)]
    dc = cell(sj['stage2'])['decomposition']['filtered']
    check('test=1 empties what shows a decision without a decision word: the reason of a P3 comparison, the list of '
          'unstable processes, the shares of dG and the reason for their absence',
          whys(sj) == [None] * 8 and cell(sj['P3'])['filtered'][NEW]['unstable'] is None
          and dc['shares'] is None and dc['shares_why'] is None and dc['dG']['median'] is not None
          and A.scrub(dict(a=[dict(shares=dict(n=1), shares_why='dG is not resolved', unstable=[3], median=1.5)]))
          == dict(a=[dict(shares=None, shares_why=None, unstable=None, median=1.5)]))
    rc1, rc2, t1, t2, (mj, sj2), sj, err = chain('chain0', 0)
    found = sorted(set(leaks(sj)) | set(leaks(mj)))
    kinds = {x.split()[0] for x in found}
    check('the same search on the same data with test=0 finds decisions of every kind, so the search can fail',
          rc1 == 0 and rc2 == 0 and kinds == {'key', 'boolean', 'string'} and len(text_leaks(t1)) >= 1 and len(text_leaks(t2)) >= 6
          and sj['P3']['gate_passed'] is True and sj['gates']['CS']['passed'] is True and 'key pass' in found
          and 'boolean gate_passed' in found and 'boolean all_slower' in found and 'string margin_forecast: feasible' in found
          and 'boolean unstable' in found and 'string forecast: feasible' in found
          and cell(sj['P3'])['filtered'][NEW]['outcome'] == 'compatible' and cell(sj['B6W'])['reproduced'] is True
          and 'below 2.0' in whys(sj)[1] and cell(sj['stage2'])['decomposition']['filtered']['shares'] is not None, str(found)[:300])
    c = cell(s['stage2'])
    check('test=1 gives a banner and no decision', rc == 0 and s['test_data'] is True and txt.startswith('TEST DATA')
          and all(v is None for v in decisions(s)) and len(list(decisions(s))) > 100
          and s['stage2']['candidate'] is None and c['P1']['filtered']['outcome'] is None and 'no decision' in txt
          and 'equivalent' not in txt and 'supported' not in txt)
    check('test=1 keeps the numbers', near(c['sizes']['8M']['new_minus_old']['fourth']['filtered']['median'], 0.6, 0.03))
    rc, txt, _ = run_cli('summary', *real, '-o', out)
    s = json.load(open(out))
    check('the same data with test=0 gives decisions and no banner',
          rc == 0 and s['test_data'] is False and s['banner'] is None and 'TEST DATA' not in txt
          and s['stage2']['candidate'] == 'supported' and 'P1: meets its equivalence margin' in txt
          and any(v is not None for v in decisions(s)))
    check('command line: summary prints a text summary and writes the json file',
          'Stage 2 cpu2/s1' in txt and 'gain' in txt and 'unfiltered median' in txt and 'old read was 67.0' in txt
          and s['counts']['S2']['processes'] == 216 and s['folders'] == sorted(os.path.basename(x) for x in real))
    mixed = os.path.join(d, 'all')
    folders = [s3(mixed, 1, lambda c: 0.0, cpus=(2,), name='s3'), b6w(mixed, 1),
               s4(mixed, 'S4', lambda c: MEAN[c['kernel']]), p3(mixed, 1, lambda c: MEAN[c['kernel']], cpus=(2,)),
               prefix_gate(mixed, 'S3G', 1, aa_rate({}, 0.02))]
    rc, txt, _ = run_cli('summary', *folders, '-o', out)
    s = json.load(open(out))
    check('command line: one summary of several steps; a gate without margins is not evaluated',
          rc == 0 and s['steps'] == ['B6W', 'P3', 'S3', 'S3G', 'S4'] and 'not evaluated' in s['gates']['S3G']['statement']
          and all(k in s for k in ('B6W', 'P3', 'stage3', 'sustained')) and 'sustained S4 asmread' in txt
          and 'P3 cpu2/s1 selected by read: Insufficient data' in txt)


def main():
    with tempfile.TemporaryDirectory() as root:
        for t in (test_parser_and_quality, test_completeness, test_shared_rule, test_mixing, test_stage2, test_p3,
                  test_stage3, test_gates, test_sustained_counters_bins, test_b6w, test_test_data_and_cli):
            try:
                t(root)
            except Exception as e:                              # a crash is a failed check, not a silent stop
                import traceback
                traceback.print_exc()
                check('%s ran to its end' % t.__name__, False, repr(e))
    print('%d checks failed' % len(FAILS) if FAILS else 'all checks passed')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
