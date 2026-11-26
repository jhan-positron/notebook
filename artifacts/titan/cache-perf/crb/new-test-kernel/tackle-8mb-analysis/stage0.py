#!/usr/bin/env python3
"""stage0.py [-o stage0.html] [--json stage0.json]

Stage 0 of the design tackle-8mb.md (lines 114 to 129): describe the saved evidence before any new code runs.
Reads only saved files on the development machine. Writes one light-background HTML page and one JSON file
with every computed table. Standard library only. No external script, font or image.

Every sentence of the page that interprets data is built from computed values. Typed text is limited to the
list "Words used here", what the design asks for, how a chart is drawn, the limits, and the references.
"""
import argparse, html, json, math, os, re, sys
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
CRB = os.path.normpath(os.path.join(HERE, '..', '..'))
RES = os.path.join(CRB, 'results')
BWX = os.path.join(CRB, 'tmp', 'agent-scratch', 'bwx-2026-11-13')
DESIGN = os.path.join(CRB, 'new-test-kernel', 'tackle-8mb.md')
SRC = {
    'orig': os.path.join(RES, 'kernels-20261113T181222Z', 'one-thread.csv'),
    'probe': os.path.join(RES, 'kernels-20261113T181222Z', 'probe.txt'),
    'cread': os.path.join(RES, 'cread-20261113T060510Z', 'cread.csv'),
    'bwx_c': os.path.join(BWX, 'bwx.c'),
    'run_sh': os.path.join(BWX, 'run_bwx.sh'),
    'listing': os.path.join(BWX, 'crb-build-2', 'listing.txt'),
    'offsets': os.path.join(BWX, 'crb-build-2', 'offsets.tsv'),
    'build': os.path.join(BWX, 'crb-build-2', 'build.txt'),
    'hier': os.path.join(CRB, 'crb-memory-hierarchy.html'),
}
SESSION = {  # step -> result folder of session 1 and of session 2
    'B1': ('B1-20261114T012315Z', 'B1-20261114T043752Z'),
    'B4': ('B4-20261114T014024Z', 'B4-20261114T045459Z'),
    'B6': ('B6-20261114T014825Z', 'B6-20261114T050300Z'),
    'C1': ('C1-20261114T022058Z', 'C1-20261114T053506Z'),
}
MIB = 1 << 20
SIZES = {'32K': 32 << 10, '1M': MIB, '4M': 4 * MIB, '8M': 8 * MIB, '16M': 16 * MIB, '32M': 32 * MIB, '1G': 1 << 30}
LOW_LINE, HIGH_LINE = 69.0, 70.5      # historical lines of the earlier analysis. They are drawn, never used to select data.
TRANSITION_SPAN = 0.30                # GB/s. A block of four intervals with a larger range is shown as a transition block.
NEW_CPUS = (2, 41)                    # the worker CPUs of the design
ID = 'Insufficient data'
B6_OLD_POS = (1, 2, 4, 5, 7, 8, 10, 11)
B6_REF_POS = (0, 3, 6, 9, 12)
B6_PAIRS = ((7, 8), (10, 11))         # first and second old-read interval after an assembly-read interval


def csv_path(step, session):
    return os.path.join(RES, SESSION[step][session - 1], step + '.csv')


# ---------------------------------------------------------------- parsers

def parse_bandwidth_csv(path, with_binary):
    """One process per '-- ' header line of one-thread.csv or cread.csv. Keeps the order of the file."""
    procs, cur = [], None
    for line in open(path):
        line = line.rstrip('\n')
        if line.startswith('-- '):
            w = line.split()
            f = {w[i]: w[i + 1] for i in range(1, len(w) - 1, 2)}
            cur = dict(order=len(procs), binary=f.get('binary', 'bw_new') if with_binary else '-', kernel=f.get('kernel'),
                       threads=int(f.get('threads', 1)), cpu=int(f['cpus'] if with_binary else f['cpu']), size=f['bytes'],
                       round=int(f['round']), load=float(f['load']), utc=f['utc'], reps=[], best={})
            procs.append(cur)
        elif line and line[0].isalpha() and not line.startswith('kernel,'):
            c = line.split(',')
            if c[3] == 'best':
                cur['best'][c[0]] = float(c[6])
            else:
                # The file prints the rate with 2 decimals and the time with 4 decimals. The printed rate is the finer value.
                cur['reps'].append(dict(kernel=c[0], rep=int(c[3]), bytes=int(c[4]), elapsed_s=float(c[5]), rate=float(c[6])))
    return procs


def parse_bwx(path):
    """Processes of a run_bwx.sh result file. The rate of an interval is bytes / elapsed_s of its T row."""
    procs, cur = [], None
    for line in open(path):
        line = line.rstrip('\n')
        if line.startswith('-- step'):
            head, args = line.split(' args ')
            w = head.split()
            la = w.index('loadavg')
            cur = dict(order=len(procs), tag=w[w.index('tag') + 1], utc=w[w.index('utc') + 1],
                       load1=float(w[la + 1]), runnable=w[la + 4], args=args, T=[], P=[])
            for key, rx in (('cpu', r'--cpus (\d+)'), ('seq', r'--seq (\S+)'), ('bytes', r'--bytes (\S+)')):
                cur[key] = re.search(rx, args).group(1)
            cur['cpu'] = int(cur['cpu'])
            cur['seq'] = cur['seq'].split(',')
            cur['thp'] = '--no-thp' not in args
            cur['count'] = '--count' in args
            procs.append(cur)
        elif line.startswith('-- '):
            cur['broken'] = line
        elif line.startswith('T,'):
            c = line.split(',')
            cur['T'].append(dict(round=int(c[1]), pos=int(c[2]), kernel=c[3], bytes=int(c[6]), elapsed_s=float(c[7]),
                                 t_start=float(c[9]), t_end=float(c[10]), rate=int(c[6]) / float(c[7]) / 1e9))
        elif line.startswith('P,'):
            c = line.split(',')
            cur['P'].append(dict(round=int(c[1]), pos=int(c[2]), buffer=c[4], kb_total=c[5], kb_huge=c[6]))
    return procs


def read_env(folder):
    """Start and end load of one result folder, from env.txt."""
    out = {}
    for line in open(os.path.join(RES, folder, 'env.txt')):
        m = re.match(r'## host=\S+ utc=(\S+) loadavg=(\S+) (\S+) (\S+)', line)
        if m:
            out.update(start_utc=m.group(1), start_load=[float(m.group(i)) for i in (2, 3, 4)])
        m = re.match(r'## end utc=(\S+) loadavg=(\S+) (\S+) (\S+)', line)
        if m:
            out.update(end_utc=m.group(1), end_load=[float(m.group(i)) for i in (2, 3, 4)])
    return out


def rate_at(p):
    return {(t['round'], t['pos']): t['rate'] for t in p['T']}


def rng(v):
    v = list(v)
    return [min(v), max(v)]


# ---------------------------------------------------------------- item 1: the original size comparison

def item1(orig):
    reads = [p for p in orig if p['kernel'] == 'read' and p['threads'] == 1]
    rows, best, pmed = [], {}, {}
    for p in reads:
        r = [x['rate'] for x in p['reps']]
        rows.append(dict(order=p['order'], binary=p['binary'], kernel='old read' if p['binary'] == 'bw_old' else 'new read',
                         cpu=p['cpu'], size=p['size'], round=p['round'], utc=p['utc'], load=p['load'], reps=r, median=median(r), best=max(r)))
        best.setdefault((p['size'], p['binary']), []).extend(r)
        pmed[(p['size'], p['cpu'], p['round'], p['binary'])] = median(r)
    table = []
    for size in ('32K', '1M', '8M', '1G'):
        o, n = max(best[(size, 'bw_old')]), max(best[(size, 'bw_new')])
        table.append(dict(size=size, n_old=len(best[(size, 'bw_old')]), n_new=len(best[(size, 'bw_new')]), old=o, new=n, gain_pct=100 * (n / o - 1)))
    pairs = []
    for size in ('32K', '1M', '8M', '1G'):
        for rnd in (1, 2):
            for cpu in (0, 2):
                o, n = pmed[(size, cpu, rnd, 'bw_old')], pmed[(size, cpu, rnd, 'bw_new')]
                pairs.append(dict(size=size, cpu=cpu, round=rnd, old=o, new=n, diff=n - o, gain_pct=100 * (n / o - 1)))
    one_kernel = all(x['kernel'] == p['kernel'] for p in orig for x in p['reps']) and all(len(p['reps']) == 3 for p in orig)
    return dict(rows=rows, best=table, pairs=pairs, one_kernel_per_process=one_kernel)


# ---------------------------------------------------------------- items 2 and 7: B6

def b6_facts(b6):
    """b6: {session: processes}. Pairs, positions, size differences, reference rates."""
    pairs, pos_rows, proc_rows, sizediff, pooled, gaps = [], [], [], [], [], []
    for s, procs in b6.items():
        cpus = sorted({p['cpu'] for p in procs})
        for cpu in cpus:
            ps = [p for p in procs if p['cpu'] == cpu]
            second = []
            for p in ps:
                r = rate_at(p)
                rounds = sorted({k[0] for k in r})
                for a, b in B6_PAIRS:
                    for rd in rounds:
                        pairs.append(dict(session=s, cpu=cpu, tag=p['tag'], round=rd, pos_first=a, pos_second=b,
                                          first=r[(rd, a)], second=r[(rd, b)], diff=r[(rd, a)] - r[(rd, b)]))
                        second.append(r[(rd, b)])
                ref = [r[(rd, q)] for rd in rounds for q in B6_REF_POS]
                proc_rows.append(dict(session=s, cpu=cpu, tag=p['tag'], utc=p['utc'], load1=p['load1'], ref_median=median(ref), ref_min=min(ref),
                                      ref_max=max(ref), old={q: median(r[(rd, q)] for rd in rounds) for q in B6_OLD_POS},
                                      d_first=median(r[(rd, 1)] - r[(rd, 2)] for rd in rounds),
                                      d_second=median(r[(rd, 5)] - r[(rd, 4)] for rd in rounds),
                                      huge_full=all(x['kb_total'] == x['kb_huge'] for x in p['P']), refs=ref,
                                      by_pos={q: [r[(rd, q)] for rd in rounds] for q in range(13)}))
                t = sorted(p['T'], key=lambda x: x['t_start'])
                for u, w in zip(t, t[1:]):
                    gaps.append(dict(session=s, cpu=cpu, pos=w['pos'], gap_ms=(w['t_start'] - u['t_end']) * 1000, size=p['seq'][w['pos']]))
            for q in range(13):
                v = [t['rate'] for p in ps for t in p['T'] if t['pos'] == q]
                pos_rows.append(dict(session=s, cpu=cpu, pos=q, entry=ps[0]['seq'][q], before=ps[0]['seq'][q - 1] if q else ps[0]['seq'][-1] + ' (previous round)',
                                     n=len(v), median=median(v), min=min(v), max=max(v)))
            mine = [x for x in proc_rows if x['session'] == s and x['cpu'] == cpu]
            sizediff.append(dict(session=s, cpu=cpu, first=median(x['d_first'] for x in mine), second=median(x['d_second'] for x in mine)))
            pooled.append(dict(session=s, cpu=cpu, n=len(second), median=median(second)))
    return dict(pairs=pairs, positions=pos_rows, processes=proc_rows, sizediff=sizediff, pooled_second=pooled, gaps=gaps)


def pair_summary(pairs):
    out = []
    keys = sorted({(x['session'], x['cpu'], x['pos_first']) for x in pairs})
    for s, cpu, a in keys:
        v = [x for x in pairs if (x['session'], x['cpu'], x['pos_first']) == (s, cpu, a)]
        d = [x['diff'] for x in v]
        out.append(dict(session=s, cpu=cpu, pos_first=a, pos_second=v[0]['pos_second'], n=len(v), first_slower=sum(x < 0 for x in d),
                        first_median=median(x['first'] for x in v), first_range=rng(x['first'] for x in v),
                        second_median=median(x['second'] for x in v), second_range=rng(x['second'] for x in v),
                        diff_median=median(d), diff_range=rng(d)))
    return out


def pairs_by_session(pairs):
    """Per session: the number of pairs, and the number of pairs whose first interval is slower than the second."""
    return {s: dict(n=sum(x['session'] == s for x in pairs), first_slower=sum(x['session'] == s and x['diff'] < 0 for x in pairs))
            for s in sorted({x['session'] for x in pairs})}


# ---------------------------------------------------------------- item 3 and 6: reference rates

def b1_facts(b1):
    rows, procs = [], []
    for s, ps in b1.items():
        for p in ps:
            ref = [t['rate'] for t in p['T'] if t['kernel'] == 'asmread']
            procs.append(dict(session=s, cpu=p['cpu'], size=p['bytes'], tag=p['tag'], utc=p['utc'], load1=p['load1'], n=len(ref),
                              median=median(ref), min=min(ref), max=max(ref), buffers=len({x['buffer'] for x in p['P']}), refs=ref))
        for size in sorted({p['bytes'] for p in ps}, key=lambda z: SIZES[z]):
            for cpu in sorted({p['cpu'] for p in ps}):
                m = [x for x in procs if (x['session'], x['size'], x['cpu']) == (s, size, cpu)]
                rows.append(dict(session=s, size=size, cpu=cpu, n_proc=len(m), n_int=sum(x['n'] for x in m), median=median(x['median'] for x in m),
                                 proc_medians=sorted(x['median'] for x in m), min=min(x['min'] for x in m), max=max(x['max'] for x in m)))
    return dict(rows=rows, processes=procs)


def cread_facts(cread):
    rows = []
    for p in cread:
        for k in ('read', 'asmread', 'cread'):
            r = [x['rate'] for x in p['reps'] if x['kernel'] == k]
            rows.append(dict(order=p['order'], round=p['round'], cpu=p['cpu'], size=p['size'], utc=p['utc'], load=p['load'], kernel=k, reps=r, median=median(r)))
    return rows


def cread_pairs(rows, size='8M'):
    out = []
    for o in sorted({x['order'] for x in rows if x['size'] == size}):
        m = {x['kernel']: x for x in rows if x['order'] == o}
        out.append(dict(round=m['read']['round'], cpu=m['read']['cpu'], old=m['read']['median'], asm=m['asmread']['median'], c=m['cread']['median'],
                        old_reps=m['read']['reps'], asm_reps=m['asmread']['reps'], c_reps=m['cread']['reps'],
                        asm_minus_old=m['asmread']['median'] - m['read']['median']))
    return out


def trace_facts(runs, step):
    """B4 and C1: one process = 200 assembly-read intervals at 8 MiB."""
    out = []
    for s, ps in runs.items():
        for p in ps:
            r = [t['rate'] for t in sorted(p['T'], key=lambda x: x['round'])]
            out.append(dict(step=step, session=s, cpu=p['cpu'], tag=p['tag'], thp=p['thp'], count=p['count'], utc=p['utc'], load1=p['load1'], n=len(r),
                            median=median(r), min=min(r), max=max(r), below_low=sum(x < LOW_LINE for x in r), above_high=sum(x > HIGH_LINE for x in r), rates=r))
    return out


# ---------------------------------------------------------------- item 8: same-condition variation

def aa_value(four):
    """Split {1, 3} against {2, 4} of four successive values of one condition."""
    return median((four[0], four[2])) - median((four[1], four[3]))


def block_aa(rates):
    """Successive blocks of four intervals. Returns one dict per whole block."""
    out = []
    for i in range(0, len(rates) - 3, 4):
        b = rates[i:i + 4]
        out.append(dict(block=i // 4, aa=aa_value(b), span=max(b) - min(b), transition=max(b) - min(b) > TRANSITION_SPAN))
    return out


def roundup05(x):
    return math.ceil(x / 0.05 - 1e-9) * 0.05


def margin_rule(L0, lower, upper):
    """Design lines 189 to 191. L0 is the largest projected limit of the selected use."""
    margin = min(max(roundup05(2 * L0), lower), upper)
    insufficient = L0 >= margin
    return dict(L0=L0, twice_rounded=roundup05(2 * L0), margin=margin, clipped=abs(margin - roundup05(2 * L0)) > 1e-9,
                forecast='precision insufficient' if insufficient else 'feasible', largest_passing_median=None if insufficient else margin - L0)


def feasibility(b6, b4, c1):
    """Per source, condition, CPU and session: the A/A spread and the projected limits."""
    rows, per_proc = [], []
    for s, procs in b6.items():
        for cpu in sorted({p['cpu'] for p in procs}):
            for pos, cond in ((5, 'old read at 8 MiB'), (2, 'old read at 1 MiB'), (4, 'old read at 1 MiB')):
                vals = []
                for p in procs:
                    if p['cpu'] != cpu:
                        continue
                    r = rate_at(p)
                    a = aa_value([r[(rd, pos)] for rd in range(4)])
                    vals.append(a)
                    per_proc.append(dict(source='B6 position %d' % pos, session=s, cpu=cpu, tag=p['tag'], aa=a, blocks=1, transitions=0, aa_no_transition=a))
                sp = max(abs(x) for x in vals)
                rows.append(dict(source='B6 position %d' % pos, condition=cond, session=s, cpu=cpu, n_proc=len(vals), n_values=len(vals),
                                 spread=sp, transitions=0, spread_no_transition=sp))
    for name, runs in (('B4', b4), ('C1', c1)):
        for s, procs in runs.items():
            for thp in (True, False):
                for cpu in sorted({p['cpu'] for p in procs}):
                    mine = [p for p in procs if p['cpu'] == cpu and p['thp'] == thp]
                    if not mine:
                        continue
                    pm, calm, nval, ntr = [], [], 0, 0
                    for p in mine:
                        bl = block_aa([t['rate'] for t in sorted(p['T'], key=lambda x: x['round'])])
                        m = max(abs(b['aa']) for b in bl)
                        q = [abs(b['aa']) for b in bl if not b['transition']]
                        tr = sum(b['transition'] for b in bl)
                        pm.append(m)
                        calm.append(max(q) if q else None)
                        nval += len(bl)
                        ntr += tr
                        per_proc.append(dict(source=name if thp else name + ' without huge pages', session=s, cpu=cpu, tag=p['tag'], aa=m, blocks=len(bl),
                                             transitions=tr, aa_no_transition=max(q) if q else None))
                    cm = [x for x in calm if x is not None]
                    rows.append(dict(source=name if thp else name + ' without huge pages', session=s, cpu=cpu, n_proc=len(mine), n_values=nval,
                                     condition='assembly read at 8 MiB' + ('' if thp else ', no huge pages') + (', counters open' if name == 'C1' else ''),
                                     spread=max(pm), transitions=ntr, spread_no_transition=max(cm) if cm else None))
    for r in rows:
        r['limit2'], r['limit4'], r['limit8'] = 2 * r['spread'], 4 * r['spread'], 8 * r['spread']
    return dict(rows=rows, per_process=per_proc)


def limit_of(rows, sources, k=2, cpus=NEW_CPUS):
    """Largest projected k-spread limit over the named sources, the CPUs of the design and both sessions."""
    v = [k * r['spread'] for r in rows if r['source'] in sources and r['cpu'] in cpus]
    return max(v) if v else None


OLD8, OLD1, ASM8 = ('B6 position 5',), ('B6 position 2', 'B6 position 4'), ('B4', 'C1')
STAGE2_SIZES = ('32K', '1M', '4M', '8M', '16M')                                  # design line 205
STAGE2_KERNELS = ('old read', 'new read', 'assembly read')
SAVED_SELECTIONS = (('old read', '1M'), ('old read', '8M'), ('assembly read', '8M'))   # the conditions of design item 8


def other_selections():
    """Kernel and size selections of Stage 2 for which the sources of design item 8 hold no repeats: {kernel: [size]}."""
    return {k: [z for z in STAGE2_SIZES if (k, z) not in SAVED_SELECTIONS] for k in STAGE2_KERNELS}


SIZE_NAME = {'32K': '32 KiB', '1M': '1 MiB', '4M': '4 MiB', '8M': '8 MiB', '16M': '16 MiB', '32M': '32 MiB', '1G': '1 GiB'}
OTHER_N = sum(len(v) for v in other_selections().values())
OTHER_MISSING = ('%d of the %d kernel and size selections of Stage 2 (%s): the sources of design item 8 (B4, C1, B6) hold no repeats of these conditions. '
                 'Needed: the A/A values of each selection from the uncounted step S2.' % (
                     OTHER_N, len(STAGE2_SIZES) * len(STAGE2_KERNELS),
                     '; '.join('%s at %s' % (k, ', '.join(SIZE_NAME[z] for z in v)) for k, v in other_selections().items())))


def uses(rows):
    """The margin rule per selected use (contract: fixed readings, notes 1 to 3)."""
    out = []

    def add(use, quantity, k, lower, upper, parts, missing, default):
        have = {name: limit_of(rows, src, k) for name, src in parts}
        L0 = max(have.values()) if have else None
        u = dict(use=use, quantity=quantity, spreads=k, lower=lower, upper=upper, parts=have, missing=missing, default=default)
        if L0 is not None:
            u.update(margin_rule(L0, lower, upper))
        if missing and (L0 is None or u['forecast'] == 'feasible'):
            u['forecast'] = ID          # a missing condition can only raise L0
            u['largest_passing_median'] = None
        out.append(u)

    new8 = ('new read at 8 MiB: no saved process has four repeats of it (the original run has 3 repetitions per process). '
            'Needed: the A/A values of new read at 8 MiB from the uncounted step S2.')
    add('P3G', 'one rate', 2, 0.10, 0.30, [('old read at 8 MiB', OLD8), ('assembly read at 8 MiB', ASM8)], new8, 'gate')
    add('S3G', 'one rate', 2, 0.10, 0.30, [('old read at 8 MiB', OLD8)], '', 'gate')
    for step in ('BIN', 'CS'):
        add(step + ' old read at 1 MiB', 'one rate', 2, 0.10, 0.30, [('old read at 1 MiB', OLD1)], '', 'mode')
        add(step + ' old read at 8 MiB', 'one rate', 2, 0.10, 0.30, [('old read at 8 MiB', OLD8)], '', 'mode')
        add(step + ' assembly read at 8 MiB', 'one rate', 2, 0.10, 0.30, [('assembly read at 8 MiB', ASM8)], '', 'mode')
        add(step + ' other selections', 'one rate', 2, 0.10, 0.30, [], OTHER_MISSING, 'mode')
    newt = 'rates with new read as target at 8 MiB: no saved data. Needed: the uncounted step S3 (design line 191).'
    add('CM one rate', 'one rate', 2, 0.10, 0.30, [('old read at 8 MiB', OLD8)], newt, 'mode')
    add('CM history contrast', 'two-rate difference', 4, 0.10, 0.30, [('old read at 8 MiB', OLD8)], '', 'mode')
    # Four of the eight spreads of the interaction belong to rates with old read as target. The other four have no saved data.
    add('CM interaction', 'four-rate interaction', 4, 0.20, 0.60, [('old read at 8 MiB', OLD8)], newt, 'mode')
    out[-1]['spreads'], out[-1]['spreads_known'] = 8, 4
    for u in out:
        u['scheduled_by_default'] = False if u['forecast'] != 'feasible' else None   # None: the forecast does not block it
    return out


def p1_emulation(b6):
    """Position 5 (old read at 8 MiB) minus position 4 (old read at 1 MiB) of one process, with the two-rate limit."""
    out = []
    for s, procs in b6.items():
        for cpu in sorted({p['cpu'] for p in procs}):
            d, a5, a4 = [], [], []
            for p in procs:
                if p['cpu'] != cpu:
                    continue
                r = rate_at(p)
                d.append(median(r[(rd, 5)] for rd in range(4)) - median(r[(rd, 4)] for rd in range(4)))
                a5.append(abs(aa_value([r[(rd, 5)] for rd in range(4)])))
                a4.append(abs(aa_value([r[(rd, 4)] for rd in range(4)])))
            L = max(a5) + max(a4)
            out.append(dict(session=s, cpu=cpu, n=len(d), diffs=d, diff_min=min(d), diff_max=max(d), limit=L,
                            worst=max(abs(x) for x in d) + L, within_030=max(abs(x) for x in d) + L <= 0.30))
    return out


# ---------------------------------------------------------------- item 5: machine code

def parse_listing(path):
    """{(binary, section name): [(address, instruction text)]} of an objdump listing with '=== binary name ===' heads."""
    out, cur = {}, None
    for line in open(path):
        m = re.match(r'=== (\S+) (\S+) ===', line)
        if m:
            cur = out.setdefault((m.group(1), m.group(2)), [])
            continue
        m = re.match(r'\s+([0-9a-f]+):\t(.*)$', line.rstrip('\n'))
        if m and cur is not None:
            cur.append((int(m.group(1), 16), re.sub(r'\s*//.*$', '', m.group(2)).replace('\t', ' ').strip()))
    return out


def normalise(ins, start):
    """Instruction text without link addresses: a branch inside the function becomes its offset, another symbol keeps its name."""
    out = []
    for addr, text in ins:
        m = re.search(r'([0-9a-f]+) <([^>+]+)(\+0x[0-9a-f]+)?>', text)
        if m:
            target = int(m.group(1), 16)
            if start <= target <= ins[-1][0]:
                text = text[:m.start()] + '<self+0x%x>' % (target - start)
            else:
                text = text[:m.start()] + '<%s>' % ('page' if m.group(2).startswith('__FRAME_END__') else m.group(2))
        out.append(text)
    return out


def loop_of(ins):
    """The first backward branch of the function: (loop start address, branch address)."""
    start = ins[0][0]
    for addr, text in ins:
        m = re.match(r'b\S*\s+([0-9a-f]+) <', text)
        if m and start <= int(m.group(1), 16) < addr:
            return int(m.group(1), 16), addr
    return None


def code_compare(listing, probe, offsets_path):
    """bwx (the saved build of the existing experiment program) against the original binaries bw_old and bw_new."""
    off = {}
    for line in open(offsets_path):
        c = line.split()
        if c and c[0] == 'bwx':
            off[c[1]] = dict(start=int(c[3], 16), loop_start=int(c[4], 16), mod64=int(c[5]))
    rows = []
    for label, bname, refs in (('old read', 'oldread', [('bw_old', 'k_read')]), ('old read, second copy', 'oldread2', [('bw_old', 'k_read')]),
                               ('new read', 'read', [('bw_new', 'k_read')]),
                               ('assembly read', 'asmread', [('bw_new', 'k_asmread'), ('bw_old', 'k_asmread')])):
        a = listing[('bwx', bname)]
        la = loop_of(a)
        na = normalise(a, a[0][0])
        for ref in refs:
            b = probe[ref]
            lb = loop_of(b)
            nb = normalise(b, b[0][0])
            raw_a, raw_b = [t for _, t in a], [t for _, t in b]
            rows.append(dict(kernel=label, bwx_function='k_' + bname, reference='%s %s' % ref, n_bwx=len(a), n_ref=len(b),
                             primary=ref != ('bw_old', 'k_asmread'),     # the size comparison used bw_old only for old read
                             sequence_equal=na == nb,
                             raw_differ=[i for i in range(min(len(a), len(b))) if raw_a[i] != raw_b[i]],
                             norm_differ=[i for i in range(min(len(a), len(b))) if na[i] != nb[i]],
                             bwx_start=a[0][0], ref_start=b[0][0], bwx_start_mod64=a[0][0] % 64, ref_start_mod64=b[0][0] % 64,
                             bwx_loop=la[0], ref_loop=lb[0], bwx_loop_mod64=la[0] % 64, ref_loop_mod64=lb[0] % 64,
                             loop_instructions_bwx=(la[1] - la[0]) // 4 + 1, loop_instructions_ref=(lb[1] - lb[0]) // 4 + 1,
                             loop_rel_bwx=la[0] - a[0][0], loop_rel_ref=lb[0] - b[0][0],
                             offsets_tsv_mod64=off[bname]['mod64'], offsets_tsv_agrees=off[bname]['loop_start'] == la[0] and off[bname]['mod64'] == la[0] % 64,
                             loop_body=na[(la[0] - a[0][0]) // 4:(la[1] - a[0][0]) // 4 + 1]))
    return rows


# ---------------------------------------------------------------- item 4: what lies between two timed kernels

OPS = [  # (order, where, file key, anchor, needle, kind, what happens)
    ('worker, once per process', 'bwx_c', 'static void *worker', 'pin_cpu(t->cpu)', 'pin', 'The worker pins itself to its CPU.'),
    ('worker, once per process', 'bwx_c', 'static void *worker', 'open_counters(t)', 'counter', 'With --count only: the worker opens its counter group.'),
    ('worker, once per process', 'bwx_c', 'static void *worker', 'k_write(t->a', 'first touch', 'The worker allocates the buffer and writes every byte of it (first touch).'),
    ('worker, before each interval', 'bwx_c', 'static void *worker', '/* warm-up */', 'warm-up', 'One untimed pass of the kernel of this interval over the size of this interval.'),
    ('worker, before each interval', 'bwx_c', 'static void *worker', 'read_smaps(r.pg', 'page read', 'One-thread runs: the worker reads /proc/self/smaps for its buffers.'),
    ('worker, before each interval', 'bwx_c', 'static void *worker', 'read_vmstat(r.vm)', 'page read', 'One-thread runs: the worker reads four counters of /proc/vmstat.'),
    ('worker, before each interval', 'bwx_c', 'static void *worker', 'pthread_barrier_wait(&bar);\n            if (cfg.stop_common)', 'barrier', 'The worker waits on a barrier until the main thread releases the interval.'),
    ('main thread, before each interval', 'bwx_c', 'int main(', 'pthread_barrier_wait(&bar); /* release the workers */', 'barrier', 'The main thread joins the barrier and so releases the worker.'),
    ('worker, before each interval', 'bwx_c', 'static void *worker', 'read_group(t, &r.c0)', 'counter read', 'With --count only: one read of the counter group, then one read of the thread CPU clock.'),
    ('worker, start of the timed interval', 'bwx_c', 'static void *worker', 't0 = now_ns();', 'clock', 'Clock read. The timed interval starts.'),
    ('worker, inside the timed interval', 'bwx_c', 'static void *worker', 'call(kd, t, off, size - off, v + p, &sink);', 'kernel', 'Whole passes of the kernel. The old-read sum goes to a volatile variable on the worker stack.'),
    ('worker, inside the timed interval', 'bwx_c', 'static void *worker', 't1 = now_ns();\n                } while (t1 - t0 < min_ns);', 'clock', 'Clock read after at least 8 MiB of reads. The interval ends at the first read at or after --min-ms.'),
    ('worker, after each interval', 'bwx_c', 'static void *worker', 'r.c1.cpu_ns = cpu_ns();', 'counter read', 'With --count only: one read of the thread CPU clock, then one read of the counter group.'),
    ('worker, after each interval', 'bwx_c', 'static void *worker', 't->res = r;\n            pthread_barrier_wait(&bar);', 'barrier', 'The worker stores its result and waits on the barrier for the main thread.'),
    ('main thread, after each interval', 'bwx_c', 'int main(', 'pthread_barrier_wait(&bar); /* all workers finished this interval */', 'barrier', 'The main thread joins the barrier. The worker goes on to the warm-up pass of the next interval.'),
    ('main thread, after each interval', 'bwx_c', 'int main(', 'print_p(round, pos, 0, \'a\'', 'output', 'The main thread prints the P row (page state that the worker read before the interval).'),
    ('main thread, after each interval', 'bwx_c', 'int main(', 'printf("I,%d,%d,%s,%lu,%d,%lu,%.6f,%.2f\\n"', 'output', 'The main thread prints the I row and then the T row (and the C row with --count).'),
    ('main thread, after each interval', 'bwx_c', 'int main(', 'fflush(stdout);\n        }\n    }', 'output', 'The main thread flushes the output. This runs while the worker already does its next warm-up pass.'),
    ('sink of old read', 'bwx_c', 'static void call(', '*sink = ((oldread_fn)kd->fn)(a, n);', 'kernel', 'The returned sum of old read is stored through a pointer to a volatile variable.'),
    ('sink of old read', 'bwx_c', 'static void *worker', 'volatile uint64_t sink;', 'kernel', 'The volatile variable is local to the worker.'),
    ('run script, the sequence', 'run_sh', '', 'B6SEQ=', 'sequence', 'The 13 entries of the B6 sequence.'),
    ('run script, the sequence', 'run_sh', '', 'ONE8=(', 'sequence', 'Options of every B6 process: 8 MiB, 4 rounds, 300 ms, whole passes.'),
    ('run script, the sequence', 'run_sh', '', 'step_B6()', 'sequence', '8 processes on each of the CPUs 2, 41 and 94, one after the other.'),
    ('run script, between processes', 'run_sh', '', 'settle() {', 'wait', 'Wait until at most 2 tasks are runnable, 20 s at most.'),
    ('run script, between processes', 'run_sh', 'one() {', '>> "$OUT/launches.txt"', 'output', 'Record the load and the 5 busiest processes of this launch.'),
    ('run script, between processes', 'run_sh', 'one() {', 'echo "-- step', 'output', 'Write the header line of the process, with the load, to the result file.'),
    ('run script, between processes', 'run_sh', 'one() {', 'setsid "$SRC/$bin"', 'launch', 'Start the benchmark process in its own process group.'),
    ('run script, between processes', 'run_sh', 'one() {', 'sleep 1 & wait $!', 'wait', 'Poll the marker file and the stop file once per second while the process runs.'),
]


def find_line(text, anchor, needle):
    """1-based line number of the first occurrence of needle after anchor. None if absent."""
    a = text.find(anchor) if anchor else 0
    i = text.find(needle, a) if a >= 0 else -1
    return None if i < 0 else text.count('\n', 0, i) + 1 + needle.count('\n') * 0


def operations():
    texts = {k: open(SRC[k]).read() for k in ('bwx_c', 'run_sh')}
    rows = []
    for where, fk, anchor, needle, kind, what in OPS:
        rows.append(dict(where=where, file='bwx.c' if fk == 'bwx_c' else 'run_bwx.sh', line=find_line(texts[fk], anchor, needle), kind=kind, what=what))
    return rows


def gap_facts(gaps, positions):
    """Measured time from the end of one timed interval to the start of the next, by sequence position."""
    out = []
    for q in sorted({g['pos'] for g in gaps}):
        v = [g['gap_ms'] for g in gaps if g['pos'] == q]
        entry = [g['size'] for g in gaps if g['pos'] == q][0]
        size = MIB if entry.endswith('@1M') else 8 * MIB
        rate = median(x['median'] for x in positions if x['pos'] == q)
        out.append(dict(pos=q, entry=entry, n=len(v), median_ms=median(v), min_ms=min(v), max_ms=max(v), pass_ms_est=size / (rate * 1e9) * 1000))
    return out


def cache_sizes():
    """The three cache sizes that the local hardware report states. Each is searched in the text of the report."""
    t = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style|svg)[\s\S]*?</\1>', '', open(SRC['hier']).read())))
    t = re.sub(r'\s+', ' ', t)
    out = []
    for name, pat, size in (('L1 data', r'L1 data 64 KiB, private', 64 << 10), ('L2', r'L2 2 MiB, private', 2 * MIB),
                            ('SLC', r'SLC \(L3\) 128 MiB, shared by 128 cores', 128 * MIB)):
        out.append(dict(level=name, bytes=size, found=bool(re.search(pat, t)), text=pat.replace('\\', '')))
    return out


def level_of(size_bytes, caches):
    for c in caches:
        if size_bytes <= c['bytes']:
            return 'fits ' + c['level']
    return 'larger than SLC'


# ---------------------------------------------------------------- everything

def compute():
    orig = parse_bandwidth_csv(SRC['orig'], True)
    cread = parse_bandwidth_csv(SRC['cread'], False)
    runs = {st: {s: parse_bwx(csv_path(st, s)) for s in (1, 2)} for st in SESSION}
    D = dict(item1=item1(orig))
    b6 = b6_facts(runs['B6'])
    D['b6'] = b6
    D['pair_summary'] = pair_summary(b6['pairs'])
    D['pairs_by_session'] = pairs_by_session(b6['pairs'])
    D['pos5_range'] = rng(t['rate'] for ps in runs['B6'].values() for p in ps for t in p['T'] if t['pos'] == 5)
    D['b1'] = b1_facts(runs['B1'])
    D['cread'] = cread_facts(cread)
    D['cread_8m'] = cread_pairs(D['cread'])
    D['orig_asm'] = [dict(order=p['order'], binary=p['binary'], cpu=p['cpu'], size=p['size'], round=p['round'], utc=p['utc'], load=p['load'],
                          reps=[x['rate'] for x in p['reps']], median=median(x['rate'] for x in p['reps']))
                     for p in orig if p['kernel'] == 'asmread' and p['threads'] == 1]
    D['b4'] = trace_facts(runs['B4'], 'B4')
    D['c1'] = trace_facts(runs['C1'], 'C1')
    fe = feasibility(runs['B6'], runs['B4'], runs['C1'])
    D['feasibility'] = fe
    pooled = []
    for s in (1, 2):
        for cpu in NEW_CPUS:
            v = [r for r in fe['rows'] if r['source'] in ASM8 and r['session'] == s and r['cpu'] == cpu]
            pooled.append(dict(session=s, cpu=cpu, n_values=sum(r['n_values'] for r in v), spread=max(r['spread'] for r in v), limit2=max(r['limit2'] for r in v)))
    D['asm_pooled'] = pooled
    D['uses'] = uses(fe['rows'])
    D['p1'] = p1_emulation(runs['B6'])
    D['code'] = code_compare(parse_listing(SRC['listing']), parse_listing(SRC['probe']), SRC['offsets'])
    D['operations'] = operations()
    D['gaps'] = gap_facts(b6['gaps'], b6['positions'])
    D['caches'] = cache_sizes()
    D['load'] = load_facts(orig, cread, runs)
    D['stop'] = stop_decision(D)
    return D


def load_facts(orig, cread, runs):
    out = []
    probe = open(SRC['probe']).read()
    m = re.search(r'load_before=(\S+) (\S+) (\S+)', probe)
    reads = [p['load'] for p in orig if p['threads'] == 1]
    out.append(dict(run='original run, one thread', where='header line of each process (1-minute load)', n=len(reads), load_min=min(reads), load_max=max(reads),
                    start='%s %s %s' % m.groups(), end=re.search(r'one-thread done load=(\S+ \S+ \S+)', probe).group(1)))
    cl = [p['load'] for p in cread]
    out.append(dict(run='06:05 UTC run', where='header line of each process (1-minute load)', n=len(cl), load_min=min(cl), load_max=max(cl), start=None, end=None))
    for st in ('B1', 'B4', 'B6', 'C1'):
        for s in (1, 2):
            e = read_env(SESSION[st][s - 1])
            l1 = [p['load1'] for p in runs[st][s]]
            out.append(dict(run='%s session %d' % (st, s), where='header line of each process (1-minute load)', n=len(l1), load_min=min(l1), load_max=max(l1),
                            start=' '.join('%.2f' % x for x in e['start_load']), end=' '.join('%.2f' % x for x in e['end_load']),
                            runnable_max=max(int(p['runnable'].split('/')[0]) for p in runs[st][s])))
    return out


CANDIDATE_MARGIN = 0.30      # GB/s. The margin that design line 80 gives prediction P1 ("nearly constant").


def candidate_facts(D):
    """Design line 129, second condition: what the original run shows on the two parts of the candidate (design lines 72, 80, 81).
    Each value is a process median at 8 MiB minus the process median at 1 MiB of the same binary, CPU and round."""
    old = [p['old'] for p in D['item1']['pairs'] if p['size'] == '8M']
    pm = {(p['size'], p['cpu'], p['round']): p for p in D['item1']['pairs']}
    keys = sorted((c, r) for z, c, r in pm if z == '8M')
    d_old = [pm[('8M', c, r)]['old'] - pm[('1M', c, r)]['old'] for c, r in keys]
    d_new = [pm[('8M', c, r)]['new'] - pm[('1M', c, r)]['new'] for c, r in keys]
    am = {(a['size'], a['binary'], a['cpu'], a['round']): a['median'] for a in D['orig_asm']}
    d_asm = [am[k] - am[('1M',) + k[1:]] for k in sorted(am) if k[0] == '8M']
    old_ok = bool(d_old) and all(abs(x) <= CANDIDATE_MARGIN for x in d_old)
    new_ok = bool(d_new) and all(x < 0 for x in d_new)
    asm_ok = bool(d_asm) and all(x < 0 for x in d_asm)
    return dict(old_8m=rng(old), old_diff=d_old, new_diff=d_new, asm_diff=d_asm, old_nearly_constant=old_ok, new_lower_at_8m=new_ok,
                asm_lower_at_8m=asm_ok, not_contradicted=old_ok and new_ok and asm_ok)


def stop_decision(D):
    """Design line 129, as facts."""
    best = {r['size']: r for r in D['item1']['best']}
    design = {'32K': (66.76, 133.22, 99.55), '1M': (67.13, 85.26, 27.01), '8M': (67.08, 67.71, 0.94), '1G': (28.72, 30.89, 7.56)}
    table_ok = all(abs(best[k]['old'] - v[0]) < 0.005 and abs(best[k]['new'] - v[1]) < 0.005 and abs(best[k]['gain_pct'] - v[2]) < 0.005 for k, v in design.items())
    g8 = sorted(round(p['gain_pct'], 2) for p in D['item1']['pairs'] if p['size'] == '8M')
    gains_ok = g8 == [0.51, 0.51, 0.69, 0.94]
    one_kernel = D['item1']['one_kernel_per_process']
    prim = [r for r in D['code'] if r['primary']]
    n_eq = sum(r['sequence_equal'] and r['bwx_loop_mod64'] == r['ref_loop_mod64'] for r in prim)
    code_ok = bool(prim) and n_eq == len(prim)
    cand = candidate_facts(D)
    parts = dict(
        evidence_table=bool(D['item1']['rows'] and D['cread'] and D['b1']['rows'] and all(c['found'] for c in D['caches'])),
        position_traces=len(D['b6']['positions']) == 2 * 3 * 13 and all(x['n'] == 32 for x in D['b6']['positions']),
        source_and_loop_checks=all(o['line'] for o in D['operations']) and len(D['code']) == 5,
        feasibility_table=bool(D['feasibility']['rows'] and D['uses']))
    return dict(parts=parts, complete=all(parts.values()), table_reproduced=table_ok, median_gains_reproduced=gains_ok, gains_8m=g8,
                loops_equal_to_original=code_ok, loops_compared=len(prim), loops_equal=n_eq, one_kernel_per_process=one_kernel,
                consistent=table_ok and gains_ok and code_ok and one_kernel, candidate=cand,
                proceed=all(parts.values()) and table_ok and gains_ok and code_ok and one_kernel and cand['not_contradicted'],
                missing=[u['use'] for u in D['uses'] if u['forecast'] == ID])


# ================================================================ the page

C0, C1, C2 = '#2a78d6', '#eb6834', '#1baf7a'     # blue, orange, aqua: validated together for a light surface
INK, MUTED, GRID, LINE = '#0b0b0b', '#52514e', '#e6e5e0', '#8a8983'
e = html.escape
CSS = """
:root{color-scheme:light}
body{font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;background:#ffffff;color:#0b0b0b;max-width:960px;margin:0 auto;padding:24px 16px 60px;line-height:1.5;font-size:15px}
h1{font-size:26px;margin:0 0 12px} h2{font-size:20px;margin-top:40px;border-top:1px solid #e6e5e0;padding-top:20px} h3{font-size:16px;margin-top:24px}
svg{display:block;max-width:100%;height:auto} svg text{font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
.ax{font-size:11px;fill:#52514e} .lab{font-size:12px;fill:#0b0b0b} .val{font-size:11px;fill:#0b0b0b;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}
.lg{display:inline-flex;align-items:center;margin-right:18px;font-size:13px;color:#52514e} .lg i{width:11px;height:11px;border-radius:50%;margin-right:8px;display:inline-block}
table{border-collapse:collapse;font-size:13px;margin:8px 0} td,th{border-bottom:1px solid #e6e5e0;padding:4px 6px;text-align:right;vertical-align:top;font-variant-numeric:tabular-nums}
th{vertical-align:bottom;font-weight:600} td{white-space:nowrap} table.wr td{white-space:normal} td.l,th.l{text-align:left} td.w{white-space:normal;text-align:left;min-width:180px} tr.grp td{background:#f1f0ec;font-weight:600;text-align:left}
tr.hi td{background:#fdf3e7} .tw{overflow-x:auto}
.take{background:#f1f0ec;padding:10px 14px;border-radius:6px} .cap{font-size:13px;color:#52514e;margin-top:2px}
.miss{background:#fdf3e7;border-left:4px solid #b85c00;padding:8px 12px;margin:10px 0}
code{font-size:13px} details{margin:10px 0} summary{cursor:pointer;color:#52514e}
ul.words{columns:2;column-gap:28px;font-size:13px;padding-left:18px} ul.words li{break-inside:avoid;margin-bottom:3px}
.sm{font-size:12px;color:#52514e}
"""


def f(v, nd=2):
    return ID if v is None else ('%.*f' % (nd, v)).replace('-', '−')


def sg(v, nd=2):
    return ('%+.*f' % (nd, v)).replace('-', '−')


def ref(*n):
    return ''.join(' [Ref%d]' % i for i in n)


def table(head, rows, left=(0,), wrap=False):
    """head: column titles. rows: lists of cells, or ('grp', text), or ('hi', cells)."""
    o = ['<div class="tw"><table%s><thead><tr>' % (' class="wr"' if wrap else '') + ''.join('<th%s>%s</th>' % (' class="l"' if i in left else '', h) for i, h in enumerate(head)) + '</tr></thead><tbody>']
    for r in rows:
        tr = ''
        if isinstance(r, tuple) and r[0] == 'grp':
            o.append('<tr class="grp"><td colspan="%d">%s</td></tr>' % (len(head), r[1]))
            continue
        if isinstance(r, tuple) and r[0] == 'hi':
            tr, r = ' class="hi"', r[1]
        o.append('<tr%s>' % tr + ''.join('<td%s>%s</td>' % (' class="l"' if i in left else '', c) for i, c in enumerate(r)) + '</tr>')
    o.append('</tbody></table></div>')
    return ''.join(o)


def svg(w, h, body, aria):
    return '<svg viewBox="0 0 %d %d" width="%d" role="img" aria-label="%s">%s</svg>' % (w, h, w, e(aria), ''.join(body))


def text(x, y, s, cls='lab', anchor='start', extra=''):
    return '<text x="%.1f" y="%.1f" class="%s" text-anchor="%s"%s>%s</text>' % (x, y, cls, anchor, extra, e(s))


def dot(x, y, r, fill, title=None, opacity=1.0, ring=True):
    t = '<title>%s</title>' % e(title) if title else ''
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" fill-opacity="%.2f"%s>%s</circle>' % (
        x, y, r, fill, opacity, ' stroke="#fff" stroke-width="1.5"' if ring else '', t)


def ticks(lo, hi, n=6):
    step = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(step))
    step = min((m * mag for m in (1, 2, 5, 10) if m * mag >= step), default=step)
    v, out = math.ceil(lo / step - 1e-9) * step, []
    while v <= hi + 1e-9:
        out.append(round(v, 6))
        v += step
    return out


def xaxis(X, lo, hi, y0, y1, unit, n=6, nd=0):
    o = []
    for t in ticks(lo, hi, n):
        o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s"/>' % (X(t), X(t), y0, y1, GRID))
        o.append(text(X(t), y1 + 14, f(t, nd), 'ax', 'middle'))
    o.append(text(X(hi), y1 + 30, unit, 'ax', 'end'))
    return o


def jit(i):
    return ((i * 7) % 11 - 5) * 1.5


def sname(z):
    return SIZE_NAME[z]


def entry_name(x):
    return {'asmread': 'assembly read at 8 MiB', 'oldread': 'old read at 8 MiB', 'oldread2': 'old read at 8 MiB (second copy of the loop)',
            'oldread@1M': 'old read at 1 MiB'}[x]


# ---- charts

def chart_sizes(D):
    W, L, R, top, rh = 900, 70, 250, 14, 44
    X = lambda v: L + (W - L - R) * v / 140.0
    rows = D['item1']['rows']
    o = xaxis(X, 0, 140, top, top + 4 * rh, 'rate, GB/s', 7)
    for i, b in enumerate(D['item1']['best']):
        y = top + rh * i + rh / 2
        o.append(text(L - 10, y + 4, sname(b['size']), 'lab', 'end'))
        for k, (kn, col) in enumerate((('old read', C0), ('new read', C1))):
            reps = [(r, x) for r in rows if r['size'] == b['size'] and r['kernel'] == kn for x in r['reps']]
            for j, (r, x) in enumerate(reps):
                o.append(dot(X(x), y + (6 if k else -6) + jit(j) * 0.4, 2.2, col, '%s, CPU %d, round %d: %s GB/s' % (kn, r['cpu'], r['round'], f(x)), 0.35, False))
        o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (X(b['old']), X(b['new']), y, y, LINE))
        o.append(dot(X(b['old']), y, 5, C0, 'old read, best of %d: %s GB/s' % (b['n_old'], f(b['old']))))
        o.append(dot(X(b['new']), y, 5, C1, 'new read, best of %d: %s GB/s' % (b['n_new'], f(b['new']))))
        o.append(text(X(b['old']) - 9, y + 4, 'old ' + f(b['old']), 'val', 'end'))
        o.append(text(X(b['new']) + 9, y + 4, 'new ' + f(b['new']) + ' GB/s', 'val'))
        o.append(text(W - R + 130, y + 4, 'gain ' + sg(b['gain_pct']) + ' %', 'lab', 'start', ' font-weight="600"'))
    return svg(W, top + 4 * rh + 36, o, 'Best old-read and new-read rate of the original run by buffer size')


def chart_8m_pairs(D):
    W, L, R, top, rh = 900, 130, 250, 14, 36
    pr = [p for p in D['item1']['pairs'] if p['size'] == '8M']
    rows = D['item1']['rows']
    allv = [x for r in rows if r['size'] == '8M' for x in r['reps']]
    lo, hi = math.floor(min(allv) * 10) / 10 - 0.1, math.ceil(max(allv) * 10) / 10 + 0.1
    X = lambda v: L + (W - L - R) * (v - lo) / (hi - lo)
    o = xaxis(X, lo, hi, top, top + len(pr) * rh, 'rate, GB/s (the axis does not start at 0)', 6, 1)
    for i, p in enumerate(pr):
        y = top + rh * i + rh / 2
        o.append(text(L - 10, y + 4, 'CPU %d, round %d' % (p['cpu'], p['round']), 'lab', 'end'))
        for kn, col, dy in (('old read', C0, -10), ('new read', C1, 10)):
            r = [x for x in rows if x['size'] == '8M' and x['kernel'] == kn and x['cpu'] == p['cpu'] and x['round'] == p['round']][0]
            for x in r['reps']:
                o.append(dot(X(x), y + dy, 2.5, col, '%s repetition: %s GB/s' % (kn, f(x)), 0.4, False))
        o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (X(p['old']), X(p['new']), y, y, LINE))
        o.append(dot(X(p['old']), y, 5, C0, 'old read, process median: %s GB/s' % f(p['old'])))
        o.append(dot(X(p['new']), y, 5, C1, 'new read, process median: %s GB/s' % f(p['new'])))
        o.append(text(X(p['old']) - 9, y + 4, f(p['old']), 'val', 'end'))
        o.append(text(X(p['new']) + 9, y + 4, f(p['new']) + ' GB/s', 'val'))
        o.append(text(W - R + 100, y + 4, 'gain ' + sg(p['gain_pct']) + ' %', 'lab', 'start', ' font-weight="600"'))
    return svg(W, top + len(pr) * rh + 36, o, 'Process medians of old read and new read at 8 MiB in the original run')


def chart_pair_diff(D):
    W, L, R, top, rh = 920, 250, 250, 14, 30
    S = D['pair_summary']
    lo = math.floor(min(x['diff_range'][0] for x in S)) - 0.0
    hi = 1.0
    X = lambda v: L + (W - L - R) * (v - lo) / (hi - lo)
    H = top + len(S) * rh
    o = xaxis(X, lo, hi, top, H, 'first interval minus second interval, GB/s', 8)
    o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s" stroke-width="1.5"/>' % (X(0), X(0), top, H, INK))
    for i, s in enumerate(S):
        y = top + rh * i + rh / 2
        o.append(text(L - 10, y + 4, 'session %d, CPU %d, positions %d and %d' % (s['session'], s['cpu'], s['pos_first'], s['pos_second']), 'lab', 'end'))
        v = [x for x in D['b6']['pairs'] if (x['session'], x['cpu'], x['pos_first']) == (s['session'], s['cpu'], s['pos_first'])]
        for j, x in enumerate(v):
            o.append(dot(X(x['diff']), y + jit(j), 2.6, C0, '%s, round %d: first %s, second %s, difference %s GB/s' % (x['tag'], x['round'], f(x['first']), f(x['second']), sg(x['diff'])), 0.55, False))
        m = X(s['diff_median'])
        o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (m, m, y - 11, y + 11, INK))
        o.append(text(W - R + 12, y + 4, 'median %s GB/s, %d of %d below 0' % (sg(s['diff_median']), s['first_slower'], s['n']), 'lab'))
    return svg(W, H + 36, o, 'Paired difference of the first and second old-read interval after assembly read, by session, CPU and position')


def chart_pair_abs(D):
    W, L, R, top, rh = 920, 250, 250, 14, 30
    S = D['pair_summary']
    lo = math.floor(min(x['first_range'][0] for x in S))
    hi = math.ceil(max(x['second_range'][1] for x in S))
    X = lambda v: L + (W - L - R) * (v - lo) / (hi - lo)
    H = top + len(S) * rh
    o = xaxis(X, lo, hi, top, H, 'rate, GB/s (the axis does not start at 0)', 8)
    for i, s in enumerate(S):
        y = top + rh * i + rh / 2
        o.append(text(L - 10, y + 4, 'session %d, CPU %d, positions %d and %d' % (s['session'], s['cpu'], s['pos_first'], s['pos_second']), 'lab', 'end'))
        v = [x for x in D['b6']['pairs'] if (x['session'], x['cpu'], x['pos_first']) == (s['session'], s['cpu'], s['pos_first'])]
        for j, x in enumerate(v):
            o.append(dot(X(x['first']), y + jit(j), 2.6, C0, '%s, round %d, first interval: %s GB/s' % (x['tag'], x['round'], f(x['first'])), 0.55, False))
            o.append(dot(X(x['second']), y + jit(j), 2.6, C1, '%s, round %d, second interval: %s GB/s' % (x['tag'], x['round'], f(x['second'])), 0.55, False))
        o.append(text(W - R + 12, y + 4, 'medians: first %s, second %s GB/s' % (f(s['first_median']), f(s['second_median'])), 'lab'))
    return svg(W, H + 36, o, 'Absolute rates of the first and second old-read interval after assembly read')


def hist_lines(X0, X1, Y, ymin, ymax, label=True):
    o = []
    for v, name in ((LOW_LINE, '69'), (HIGH_LINE, '70.5')):
        if ymin < v < ymax:
            o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-dasharray="4 3"/>' % (X0, X1, Y(v), Y(v), LINE))
            if label:
                o.append(text(X1 - 3, Y(v) - 3, name, 'ax', 'end'))
    return o


def label_y(y_above, y_below, prefer_below, line_ys):
    """Baseline of a median label. The label goes above or below its dots. The other side is used if a dashed line would cross the text."""
    crossed = lambda y: any(y - 12 <= ly <= y + 3 for ly in line_ys)      # an 11 px label covers about 10 px above and 2 px below its baseline
    first, second = (y_below, y_above) if prefer_below else (y_above, y_below)
    return second if crossed(first) and not crossed(second) else first


def panel(ox, oy, w, h, title, series, xmax, ymin, ymax, xlabel, ylab=True, endlabels=False, sub=None):
    """series: (colour, [(x, y)], name). One line per process."""
    L, R, T, B = 34, (86 if endlabels else 8), (34 if sub else 20), 28
    X = lambda v: ox + L + (w - L - R) * v / xmax
    Y = lambda v: oy + T + (h - T - B) * (ymax - v) / (ymax - ymin)
    o = [text(ox + L, oy + 12, title, 'lab', 'start', ' font-weight="600"')]
    if sub:
        o.append(text(ox + L, oy + 25, sub, 'ax'))
    for t in ticks(ymin, ymax, 5):
        o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s"/>' % (X(0), X(xmax), Y(t), Y(t), GRID))
        if ylab:
            o.append(text(ox + L - 5, Y(t) + 4, f(t, 0), 'ax', 'end'))
    o += hist_lines(X(0), X(xmax), Y, ymin, ymax)
    for t in ticks(0, xmax, 4):
        o.append(text(X(t), oy + h - B + 13, f(t, 0), 'ax', 'middle'))
    o.append(text(X(xmax), oy + h - 2, xlabel, 'ax', 'end'))
    ends = []
    for col, pts, name in series:
        o.append('<polyline fill="none" stroke="%s" stroke-width="1.3" stroke-opacity="0.85" points="%s"><title>%s</title></polyline>' % (
            col, ' '.join('%.1f,%.1f' % (X(a), Y(b)) for a, b in pts), e(name)))
        ends.append([Y(pts[-1][1]), name])
    if endlabels:
        ends.sort()
        for i in range(1, len(ends)):                   # keep 12 px between the labels at the end of the lines
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + 12)
        for y, name in ends:
            o.append(text(X(xmax) + 4, y + 4, name, 'ax'))
    return o


def chart_traces(D, key, title):
    """B4 or C1: every interval of every process, in time order."""
    runs = D[key]
    W, pw, ph = 920, 460, 190
    cells = [(s, c) for s in (1, 2) for c in NEW_CPUS]
    lo = math.floor(min(x['min'] for x in runs))
    hi = math.ceil(max(x['max'] for x in runs))
    o = []
    for i, (s, c) in enumerate(cells):
        ser = []
        for p in runs:
            if (p['session'], p['cpu']) == (s, c):
                short = ('huge pages' if p['thp'] else 'no huge pages') + ' ' + p['tag'].split('-')[-1] if key == 'b4' else p['tag'].split('-')[-1]
                ser.append((C0 if p['thp'] else C1, list(enumerate(p['rates'])), '%s: %s' % (short.replace('huge pages', 'hp'), f(p['median']))))
        o += panel((i % 2) * pw, (i // 2) * ph, pw, ph, '%s, session %d, CPU %d' % (title, s, c), ser, 200, lo, hi, 'interval number in the process', endlabels=True)
    return svg(W, 2 * ph, o, '%s: assembly-read rate of every interval, by session and CPU' % title)


def chart_refs(D, which, size='8M'):
    """Reference intervals (assembly read) of the B6 processes, or of the B1 processes of one size, against their number in the process."""
    if which == 'b6':
        cpus, title = (2, 41, 94), 'B6'
        rows = [(p['session'], p['cpu'], p['tag'], p['refs']) for p in D['b6']['processes']]
    else:
        cpus, title = (0, 2, 41, 94), 'B1 at ' + sname(size)
        rows = [(p['session'], p['cpu'], p['tag'], p['refs']) for p in D['b1']['processes'] if p['size'] == size]
    n = len(cpus)
    W, ph = 920, 186
    pw = W // n
    lo = math.floor(min(min(r[3]) for r in rows))
    hi = math.ceil(max(max(r[3]) for r in rows))
    o = []
    for si, s in enumerate((1, 2)):
        for ci, c in enumerate(cpus):
            mine = [r for r in rows if r[0] == s and r[1] == c]
            ser = [(C0, list(enumerate(r[3])), '%s: median %s GB/s' % (r[2], f(median(r[3])))) for r in mine]
            med = [median(r[3]) for r in mine]
            o += panel(ci * pw, si * ph, pw, ph, 'session %d, CPU %d' % (s, c), ser, 19, lo, hi, 'reference interval number',
                       sub='process medians %s to %s GB/s' % (f(min(med)), f(max(med))))
    return svg(W, 2 * ph, o, '%s: rate of every assembly-read reference interval of every process' % title)


def chart_positions(D):
    W, pw, ph = 920, 460, 250
    P = D['b6']['positions']
    lo, hi = math.floor(min(x['min'] for x in P)), math.ceil(max(x['max'] for x in P))
    cells = [(s, c) for c in (2, 41, 94) for s in (1, 2)]
    col = {'asmread': C1, 'oldread': C0, 'oldread2': C0, 'oldread@1M': C2}
    short = {'asmread': 'asm', 'oldread': 'old', 'oldread2': 'old', 'oldread@1M': 'old 1M'}
    o = []
    for i, (s, c) in enumerate(cells):
        ox, oy = (i % 2) * pw, (i // 2) * ph
        L, R, T, B = 34, 8, 22, 40
        X = lambda q: ox + L + (pw - L - R) * (q + 0.5) / 13
        Y = lambda v: oy + T + (ph - T - B) * (hi - v) / (hi - lo)
        o.append(text(ox + L, oy + 12, 'session %d, CPU %d' % (s, c), 'lab', 'start', ' font-weight="600"'))
        for t in ticks(lo, hi, 5):
            o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s"/>' % (ox + L, ox + pw - R, Y(t), Y(t), GRID))
            o.append(text(ox + L - 5, Y(t) + 4, f(t, 0), 'ax', 'end'))
        o += hist_lines(ox + L, ox + pw - R, Y, lo, hi, label=False)
        for q in range(13):
            row = [x for x in P if (x['session'], x['cpu'], x['pos']) == (s, c, q)][0]
            v = [(p['tag'], x) for p in D['b6']['processes'] if (p['session'], p['cpu']) == (s, c) for x in p['by_pos'][q]]
            for j, (tag, x) in enumerate(v):
                o.append(dot(X(q) + jit(j) * 0.9, Y(x), 2.2, col[row['entry']], '%s, position %d: %s GB/s' % (tag, q, f(x)), 0.5, False))
            my = Y(row['median'])
            o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (X(q) - 11, X(q) + 11, my, my, INK))
            ly = label_y(Y(row['max']) - 6, Y(row['min']) + 13, row['entry'].startswith('oldread') and row['median'] < 66.5,
                         [Y(v) for v in (LOW_LINE, HIGH_LINE) if lo < v < hi])
            o.append(text(X(q), ly, f(row['median'], 1), 'val', 'middle'))
            o.append(text(X(q), oy + ph - B + 13, str(q), 'ax', 'middle'))
            o.append(text(X(q), oy + ph - B + 25, short[row['entry']], 'ax', 'middle', ' style="font-size:9px"'))
        o.append(text(ox + pw - R, oy + ph - 2, 'position in the sequence; the label is the median in GB/s', 'ax', 'end'))
    return svg(W, 3 * ph, o, 'B6: rate of every interval by sequence position, session and CPU')


def chart_limits(D):
    rows = [r for r in D['feasibility']['rows'] if r['cpu'] in NEW_CPUS and 'without' not in r['source']]
    W, L, R, top, rh = 920, 330, 130, 26, 22
    lo, hi = math.log10(0.003), math.log10(5)
    X = lambda v: L + (W - L - R) * (math.log10(v) - lo) / (hi - lo)
    H = top + len(rows) * rh
    o = []
    for t in (0.01, 0.03, 0.1, 0.3, 1, 3):
        o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s"/>' % (X(t), X(t), top, H, GRID))
        o.append(text(X(t), H + 14, ('%g' % t), 'ax', 'middle'))
    o.append(text(W - R, H + 30, 'projected two-spread limit, GB/s, est. for the new trial wrapper (logarithmic axis)', 'ax', 'end'))
    for v, name in ((0.10, 'lowest margin 0.10'), (0.30, 'highest margin 0.30')):
        o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s" stroke-dasharray="4 3" stroke-width="1.5"/>' % (X(v), X(v), top - 4, H, INK))
        o.append(text(X(v) + (4 if v > 0.2 else -4), top - 8, name, 'ax', 'start' if v > 0.2 else 'end'))
    colour = {'old read at 8 MiB': C0, 'old read at 1 MiB': C2}
    for i, r in enumerate(rows):
        y = top + rh * i + rh / 2
        o.append(text(L - 10, y + 4, '%s, %s, session %d, CPU %d' % (r['source'], r['condition'].split(',')[0], r['session'], r['cpu']), 'lab', 'end'))
        o.append(dot(X(r['limit2']), y, 5, colour.get(r['condition'], C1), '%s: spread %s, two-spread limit %s GB/s est.' % (r['source'], f(r['spread'], 4), f(r['limit2'], 4))))
        o.append(text(W - R + 12, y + 4, f(r['limit2'], 3) + ' GB/s est.', 'lab'))
    return svg(W, H + 36, o, 'Projected two-spread limits from saved same-condition repeats against the permitted margins')


# ---- sections

WORDS = [
    ('8 MiB', '8,388,608 bytes. This is the buffer size called "8 MB" in the question.'),
    ('Rate', 'bytes read divided by the measured elapsed time, in GB/s. One GB is 1,000,000,000 bytes.'),
    ('Kernel', 'one benchmark loop. It is not the Linux kernel.'),
    ('Old read, new read, assembly read', 'the read loop before the rewrite, the read loop after the rewrite, and a read loop written in assembly.'),
    ('CRB', 'the Arm Phoenix Reference Server on which all saved measurements ran.'),
    ('CPU', 'a processor core to which the worker thread is pinned.'),
    ('Process', 'one run of a benchmark program. It allocates its own buffer.'),
    ('Original run', 'the run of 2026-11-13 18:12 UTC. Each process ran one kernel at one size on one CPU. The binary <code>bw_old</code> holds old read and <code>bw_new</code> holds new read.'),
    ('06:05 UTC run', 'a run of 2026-11-13 in which one process ran old read, assembly read and a C load-only loop one after the other.'),
    ('<code>bwx</code>', 'the existing experiment program. It runs a sequence of kernels in one process and times each entry as one interval.'),
    ('Interval', 'one timed entry of a <code>bwx</code> sequence, about 0.3 s long.'),
    ('Position', 'the place of an entry in the sequence, counted from 0.'),
    ('Round', 'one pass through the whole sequence. A <code>bwx</code> process of B1 or B6 runs 4 rounds.'),
    ('Session', 'one complete set of processes. The two sessions started about 3 hours apart.'),
    ('B1, B4, B6, C1', 'earlier experiment steps. B1 mixed copy loops with assembly-read reference intervals and held two buffers. B4 timed assembly read 200 times per process. B6 alternated old read at two sizes with assembly-read reference intervals. C1 repeated B4 with hardware counters open.'),
    ('Reference interval', 'an assembly-read interval at the full buffer size inside a B1 or B6 sequence.'),
    ('A/A value', 'the difference between two halves of repeats of one condition: the median of repeats 1 and 3 minus the median of repeats 2 and 4.'),
    ('A/A spread', 'the largest absolute A/A value over the processes of one CPU and session.'),
    ('Two-, four-, eight-spread limit', 'two, four or eight times the A/A spread. The design uses it as the limit of a comparison of one, two or four rates between two modes.'),
    ('Margin', 'the largest difference that an equivalence gate of the design is allowed to overlook.'),
    ('Gate', 'an acceptance check of the design that must pass before a later stage may use a method.'),
    ('P3G, S3G, BIN, CS, CM', 'names of planned steps. P3G and S3G are checks of the preparation before the paired-allocation and the mixed-sequence experiment. BIN checks 10 ms time bins. CS and CM check hardware counters for the size and the mixed-sequence experiment.'),
    ('Huge pages', 'memory pages of 2 MiB. "No huge pages" marks processes that asked for 4 KiB pages.'),
    ('L1, L2, SLC', 'the cache levels of one core. SLC is the system-level cache shared by all cores.'),
    ('Loop offset', "the address of a loop's first instruction modulo 64."),
    ('Load', 'the 1-minute load average of Linux at the launch of a process.'),
    ('T row, P row, I row, C row', 'the line types of a <code>bwx</code> result file, per interval. A T row holds the bytes, the elapsed time, and the start and end time of the worker. '
                                   'A P row holds the page state of the buffer (total and huge-page kilobytes). An I row holds the rate rounded to 2 decimals. A C row holds hardware counter values.'),
    ('Interval wrapper', 'the existing code of <code>bwx</code> around one interval. It runs a warm-up pass, file reads and barrier waits before each timed interval.'),
    ('Trial wrapper', 'the planned code of the new runner around one trial. A trial runs one kernel as a prefix of 1.2 s and then timed target windows of 0.3 s, with no such work between them.'),
    ('Window-only records', 'trial output that holds one time record per target window and no 10 ms time bins.'),
    ('Step S2, step S3', 'the planned timing steps without counters. S2 is the size experiment of Stage 2: one kernel and one size per process. S3 is the mixed-sequence experiment of Stage 3: a predecessor kernel before the target kernel.'),
    ('P3 branch', 'the conditional paired-allocation experiment of the design (step P3) with its check P3G. It runs old, new and assembly read on the same buffer.'),
    ('Trigger of Stage 3', 'the observation that the design requires before Stage 3 is scheduled: a relation of a Stage 2 rate to trial order or to the kernel of the preceding process, or a named later comparison that needs different kernels in one sequence.'),
    ('est.', 'an estimate, not a measurement.'),
]


def sec_item1(D):
    I = D['item1']
    b = {x['size']: x for x in I['best']}
    g8 = sorted(p['gain_pct'] for p in I['pairs'] if p['size'] == '8M')
    o = ['<h2>1. The original size comparison (design item 1)</h2>']
    o.append('<p>The design asks to recompute the comparison from every repetition and from the best rates%s. '
             'The original run has %d one-thread read processes. Each process ran one kernel and has 3 repetitions of 0.5 s%s.</p>' % (ref(13), len(I['rows']), ref(1, 8)))
    o.append('<p><span class="lg"><i style="background:%s"></i>old read</span><span class="lg"><i style="background:%s"></i>new read</span>'
             '<span class="sm">Large dot: best of 12 repetitions. Small dots: every repetition.</span></p>' % (C0, C1))
    o.append(chart_sizes(D))
    o.append('<p class="take">At 8 MiB the best new-read rate is %s %% above the best old-read rate. At 1 MiB it is %s %% above.</p>' % (f(b['8M']['gain_pct']), f(b['1M']['gain_pct'])))
    o.append(table(['Buffer size', 'Repetitions per kernel', 'Old read, best', 'New read, best', 'New-read gain'],
                   [[sname(x['size']), x['n_old'], f(x['old']) + ' GB/s', f(x['new']) + ' GB/s', f(x['gain_pct']) + ' %'] for x in I['best']]))
    o.append('<p class="cap">Gain = 100 × (new / old − 1). The rate of a repetition is the value that the file prints (2 decimals).</p>')
    o.append('<h3>Process medians at 8 MiB</h3>')
    o.append(chart_8m_pairs(D))
    o.append('<p class="take">The gain of the four pairs of process medians at 8 MiB is %s %% to %s %%. The small gain does not depend on the choice of the best repetition.</p>' % (f(g8[0]), f(g8[-1])))
    o.append(table(['Buffer size', 'CPU', 'Round', 'Old read, process median', 'New read, process median', 'New minus old', 'Gain'],
                   [[sname(p['size']), p['cpu'], p['round'], f(p['old']) + ' GB/s', f(p['new']) + ' GB/s', sg(p['diff']) + ' GB/s', f(p['gain_pct']) + ' %'] for p in I['pairs']]))
    o.append('<details><summary>Every repetition, in run order (%d processes)</summary>' % len(I['rows']))
    o.append(table(['Run order', 'UTC', 'Binary', 'Kernel', 'CPU', 'Size', 'Round', 'Load', 'Repetitions, GB/s', 'Median', 'Best'],
                   [[r['order'], r['utc'], r['binary'], r['kernel'], r['cpu'], sname(r['size']), r['round'], f(r['load']), ', '.join(f(x) for x in r['reps']),
                     f(r['median']), f(r['best'])] for r in I['rows']], left=(1, 2, 3)))
    o.append('<p class="cap">Run order counts the processes of the file from 0. Processes of other kernels (write, copy, assembly loops) lie between these rows.</p></details>')
    return o


def sec_item6(D):
    caches = D['caches']
    lv = lambda z: level_of(SIZES[z], caches)
    o = ['<h2>2. One table of the three sources by size, CPU, kernel and run (design item 6)</h2>']
    o.append('<p>The cache sizes come from the local hardware report: %s%s.</p>' % (
        ', '.join('%s %s' % (c['level'], '%d KiB' % (c['bytes'] >> 10) if c['bytes'] < MIB else '%d MiB' % (c['bytes'] >> 20)) for c in caches), ref(9)))
    hi = [x for x in D['cread_8m'] if x['asm_minus_old'] > 2.0]
    o.append('<p class="take">In the 06:05 UTC run, %d of %d processes at 8 MiB have assembly read more than 2.0 GB/s above old read. Their old-read medians are %s to %s GB/s and their assembly-read medians are %s to %s GB/s%s.</p>' % (
        len(hi), len(D['cread_8m']), f(min(x['old'] for x in hi)), f(max(x['old'] for x in hi)), f(min(x['asm'] for x in hi)), f(max(x['asm'] for x in hi)), ref(11)))

    def rows_for(sizes):
        rows = [('grp', 'Original run: one kernel per process, one buffer, 3 repetitions of 0.5 s')]
        for z in sizes:
            for r in D['item1']['rows']:
                if r['size'] == z:
                    rows.append([sname(z), lv(z), r['cpu'], r['kernel'], 'round %d' % r['round'], 3, f(r['median']), f(min(r['reps'])), f(max(r['reps']))])
            for r in D['orig_asm']:
                if r['size'] == z:
                    rows.append([sname(z), lv(z), r['cpu'], 'assembly read (%s)' % r['binary'], 'round %d' % r['round'], 3, f(r['median']), f(min(r['reps'])), f(max(r['reps']))])
        rows.append(('grp', '06:05 UTC run: old read, assembly read and the C load-only loop in one process, one buffer, 3 repetitions of 0.5 s each'))
        names = {'read': 'old read', 'asmread': 'assembly read', 'cread': 'C load-only loop'}
        flagged = {(x['round'], x['cpu']) for x in hi}
        for z in sizes:
            for r in D['cread']:
                if r['size'] == z:
                    cells = [sname(z), lv(z), r['cpu'], names[r['kernel']], 'round %d' % r['round'], 3, f(r['median']), f(min(r['reps'])), f(max(r['reps']))]
                    rows.append(('hi', cells) if z == '8M' and (r['round'], r['cpu']) in flagged else cells)
        rows.append(('grp', 'B1 reference intervals: assembly read inside a copy sequence, TWO buffers per process. Kept separate from the one-buffer rows.'))
        for z in sizes:
            for r in D['b1']['rows']:
                if r['size'] == z:
                    rows.append([sname(z), lv(z), r['cpu'], 'assembly read (reference)', 'session %d' % r['session'], '%d in %d processes' % (r['n_int'], r['n_proc']),
                                 f(r['median'], 3), f(r['proc_medians'][0], 3), f(r['proc_medians'][-1], 3)])
        return rows
    head = ['Size', 'Cache level', 'CPU', 'Kernel', 'Run', 'Intervals', 'Median, GB/s', 'Lowest, GB/s', 'Highest, GB/s']
    o.append('<h3>Rows at 8 MiB</h3>')
    o.append(table(head, rows_for(['8M']), left=(0, 1, 3, 4)))
    o.append('<p class="cap">Shaded rows: the 06:05 UTC processes named above. For the original run and the 06:05 UTC run, lowest and highest are repetitions of one process. '
             'For B1, the median is the median of the process medians, and lowest and highest are the lowest and highest process median.</p>')
    b1 = D['b1']['rows']
    q = lambda z, cpus: [x for r in b1 if r['size'] == z and r['cpu'] in cpus for x in r['proc_medians']]
    o.append('<p>B1 process medians of the assembly-read reference at 8 MiB are %s to %s GB/s on CPUs 41 and 94, and %s to %s GB/s on CPUs 0 and 2. '
             'At 4 MiB they are %s to %s GB/s. At 16 MiB they are %s to %s GB/s%s.</p>' % (
                 f(min(q('8M', (41, 94))), 3), f(max(q('8M', (41, 94))), 3), f(min(q('8M', (0, 2))), 3), f(max(q('8M', (0, 2))), 3),
                 f(min(q('4M', (0, 2, 41, 94))), 3), f(max(q('4M', (0, 2, 41, 94))), 3), f(min(q('16M', (0, 2, 41, 94))), 3), f(max(q('16M', (0, 2, 41, 94))), 3), ref(10)))
    o.append('<p class="cap">These values use bytes / elapsed time of each T row. The design quotes the same medians from the rate column that the file rounds to 2 decimals. The two differ by at most 0.005 GB/s.</p>')
    o.append('<details><summary>The whole table, all sizes</summary>')
    sizes = sorted({r['size'] for r in D['item1']['rows']} | {r['size'] for r in b1}, key=lambda z: SIZES[z])
    o.append(table(head, rows_for(sizes), left=(0, 1, 3, 4)))
    o.append('</details>')
    return o


def sec_item2(D):
    S, B = D['pair_summary'], D['pairs_by_session']
    o = ['<h2>3. First and second old-read interval after assembly read (design item 2)</h2>']
    o.append('<p>The B6 sequence holds two places where assembly read is followed by two old-read intervals on the same 8 MiB buffer: positions 7 and 8, and positions 10 and 11. '
             'The two intervals call two copies of the same loop. Each process gives 4 rounds, so each session has %d pairs%s.</p>' % (B[1]['n'], ref(4, 12)))
    o.append('<p><span class="lg"><i style="background:%s"></i>one pair: first interval minus second interval</span><span class="lg"><i style="background:%s;border-radius:0;width:3px"></i>median of the row</span></p>' % (C0, INK))
    o.append(chart_pair_diff(D))
    o.append('<p class="take">The first interval is slower than the second in %d of %d pairs in session 1 and in %d of %d pairs in session 2. The row medians of the difference are %s to %s GB/s.</p>' % (
        B[1]['first_slower'], B[1]['n'], B[2]['first_slower'], B[2]['n'], sg(min(x['diff_median'] for x in S)), sg(max(x['diff_median'] for x in S))))
    o.append('<p class="cap">This is the direct difference of the two 8 MiB intervals. It is not the old-8-MiB-minus-old-1-MiB value. The observation describes an order in the saved sequence. It does not show what causes it.</p>')
    o.append('<h3>Absolute rates of the same pairs</h3>')
    o.append('<p><span class="lg"><i style="background:%s"></i>first interval (directly after assembly read)</span><span class="lg"><i style="background:%s"></i>second interval</span></p>' % (C0, C1))
    o.append(chart_pair_abs(D))
    P = D['b6']['pooled_second']
    o.append('<p class="take">The second intervals, pooled over positions 8 and 11, have medians of %s to %s GB/s per CPU and session (%d intervals each). The intervals of position 5, after old read at 1 MiB, are %s to %s GB/s%s.</p>' % (
        f(min(x['median'] for x in P)), f(max(x['median'] for x in P)), P[0]['n'], f(D['pos5_range'][0]), f(D['pos5_range'][1]), ref(12)))
    o.append(table(['Session', 'CPU', 'Positions', 'Pairs', 'First slower', 'First: median (lowest to highest), GB/s', 'Second: median (lowest to highest), GB/s', 'Difference: median (lowest to highest), GB/s'],
                   [[x['session'], x['cpu'], '%d and %d' % (x['pos_first'], x['pos_second']), x['n'], '%d of %d' % (x['first_slower'], x['n']),
                     '%s (%s to %s)' % (f(x['first_median']), f(x['first_range'][0]), f(x['first_range'][1])),
                     '%s (%s to %s)' % (f(x['second_median']), f(x['second_range'][0]), f(x['second_range'][1])),
                     '%s (%s to %s)' % (sg(x['diff_median']), sg(x['diff_range'][0]), sg(x['diff_range'][1]))] for x in S]))
    o.append('<details><summary>Every pair (%d rows)</summary>' % len(D['b6']['pairs']))
    o.append(table(['Session', 'CPU', 'Process', 'Round', 'Positions', 'First, GB/s', 'Second, GB/s', 'Difference, GB/s'],
                   [[x['session'], x['cpu'], x['tag'], x['round'], '%d and %d' % (x['pos_first'], x['pos_second']), f(x['first'], 3), f(x['second'], 3), sg(x['diff'], 3)]
                    for x in D['b6']['pairs']], left=(2,)))
    o.append('</details>')
    return o


def sec_item7(D):
    b6 = D['b6']
    o = ['<h2>4. Old-read rate at every B6 position, with the reference rate of the same process (design item 7)</h2>']
    seq = [x['entry'] for x in b6['positions'][:13]]
    o.append('<p>The sequence has 13 entries. Positions %s are assembly-read reference intervals. Positions %s are old read at 8 MiB. Positions %s are old read on the first 1 MiB of the same buffer%s.</p>' % (
        ', '.join(str(i) for i, x in enumerate(seq) if x == 'asmread'), ', '.join(str(i) for i, x in enumerate(seq) if x in ('oldread', 'oldread2')),
        ', '.join(str(i) for i, x in enumerate(seq) if x == 'oldread@1M'), ref(4)))
    o.append('<p><span class="lg"><i style="background:%s"></i>old read at 8 MiB</span><span class="lg"><i style="background:%s"></i>old read at 1 MiB</span><span class="lg"><i style="background:%s"></i>assembly read at 8 MiB</span>'
             '<span class="lg"><i style="background:%s;border-radius:0;height:3px"></i>median of the position</span><span class="sm">Dashed lines: 69 and 70.5 GB/s, historical lines, annotation only.</span></p>' % (C0, C2, C1, INK))
    o.append(chart_positions(D))
    after_asm = [x['median'] for x in b6['positions'] if x['pos'] in (1, 7, 10)]
    p5 = [x['median'] for x in b6['positions'] if x['pos'] == 5]
    o8 = [p['old'] for p in D['item1']['pairs'] if p['size'] == '8M']
    o.append('<p class="take">Old read at 8 MiB directly after assembly read (positions 1, 7 and 10) has medians of %s to %s GB/s. At position 5, after old read at 1 MiB, the medians are %s to %s GB/s. '
             'The process medians of old read at 8 MiB in the original run are %s to %s GB/s.</p>' % (f(min(after_asm)), f(max(after_asm)), f(min(p5)), f(max(p5)), f(min(o8)), f(max(o8))))
    sd = b6['sizediff']
    o.append('<p>Old read at 8 MiB minus old read at 1 MiB depends on the position. Directly after assembly read (position 1 minus position 2) the per-CPU medians are %s to %s GB/s. '
             'After old read at 1 MiB (position 5 minus position 4) they are %s to %s GB/s%s.</p>' % (
                 sg(min(x['first'] for x in sd)), sg(max(x['first'] for x in sd)), sg(min(x['second'] for x in sd)), sg(max(x['second'] for x in sd)), ref(2, 12)))
    o.append('<p class="cap">Each per-CPU median is the median over 8 processes of the process median over 4 rounds. All %d B6 processes had full huge-page coverage in every page record: %s.</p>' % (
        len(b6['processes']), 'yes' if all(p['huge_full'] for p in b6['processes']) else 'no'))
    cells = [(sx, c) for sx in (1, 2) for c in (2, 41, 94)]
    short = {'asmread': 'assembly read, 8 MiB', 'oldread': 'old read, 8 MiB', 'oldread2': 'old read, 8 MiB', 'oldread@1M': 'old read, 1 MiB'}
    rows = []
    for q in range(13):
        row = [q, short[seq[q]]]
        for sx, c in cells:
            x = [x for x in b6['positions'] if (x['session'], x['cpu'], x['pos']) == (sx, c, q)][0]
            row.append('%s (%s\u2013%s)' % (f(x['median']), f(x['min'], 1), f(x['max'], 1)))
        rows.append(row)
    o.append(table(['Position', 'Entry'] + ['Session %d, CPU %d' % k for k in cells], rows, left=(1,)))
    o.append('<p class="cap">Each cell: median rate in GB/s of the 32 intervals of the position (8 processes \u00d7 4 rounds), with the lowest and highest interval in brackets.</p>')
    o.append('<details><summary>Every process: its reference rate beside its old-read medians (%d processes)</summary>' % len(b6['processes']))
    o.append(table(['Session', 'CPU', 'Process', 'UTC', 'Load', 'Assembly-read reference: median (lowest to highest), GB/s'] + ['Old, pos. %d' % q for q in B6_OLD_POS],
                   [[p['session'], p['cpu'], p['tag'], p['utc'], f(p['load1']), '%s (%s to %s)' % (f(p['ref_median']), f(p['ref_min']), f(p['ref_max']))] +
                    [f(p['old'][q]) for q in B6_OLD_POS] for p in b6['processes']], left=(2, 3)))
    o.append('<p class="cap">Old-read cells: median over the 4 rounds of the process, in GB/s. Positions 2 and 4 are old read at 1 MiB.</p></details>')
    return o


def sec_item3(D):
    o = ['<h2>5. All assembly-read reference rates, plotted continuously (design item 3)</h2>']
    o.append('<p>Every interval of every process is drawn. No process is removed. The dashed lines at 69 and 70.5 GB/s are the limits of the earlier analysis. Here they are annotations only%s.</p>' % ref(2, 17, 18))
    o.append('<h3>B4: 200 intervals of assembly read at 8 MiB per process</h3>')
    o.append('<p><span class="lg"><i style="background:%s"></i>huge pages allowed (hp)</span><span class="lg"><i style="background:%s"></i>no huge pages (no hp)</span><span class="sm">The label at the end of a line is the process and its median in GB/s.</span></p>' % (C0, C1))
    o.append(chart_traces(D, 'b4', 'B4'))
    hp = [p for p in D['b4'] if p['thp']]
    o.append('<p class="take">The %d B4 processes with huge pages have medians of %s to %s GB/s. Single intervals are %s to %s GB/s.</p>' % (
        len(hp), f(min(p['median'] for p in hp)), f(max(p['median'] for p in hp)), f(min(p['min'] for p in hp)), f(max(p['max'] for p in hp))))
    o.append('<h3>C1: the same with hardware counters open</h3>')
    o.append(chart_traces(D, 'c1', 'C1'))
    o.append('<p class="take">The highest C1 interval is %s GB/s. C1 has %d of %d intervals above 70.5 GB/s.</p>' % (
        f(max(p['max'] for p in D['c1'])), sum(p['above_high'] for p in D['c1']), sum(p['n'] for p in D['c1'])))
    o.append('<p class="cap">The absence of a higher interval in C1 does not show that the counters caused its absence.</p>')
    trow = lambda p: [p['step'], p['session'], p['cpu'], p['tag'], p['utc'], f(p['load1']), p['n'], f(p['median']), f(p['min']), f(p['max']), p['below_low'], p['n'] - p['below_low'] - p['above_high'], p['above_high']]
    o.append(table(['Step', 'Session', 'CPU', 'Process', 'UTC', 'Load', 'Intervals', 'Median, GB/s', 'Lowest, GB/s', 'Highest, GB/s', 'Intervals below 69 GB/s', 'Intervals at 69 to 70.5 GB/s', 'Intervals above 70.5 GB/s'],
                   [trow(p) for p in D['b4'] + D['c1']], left=(0, 3, 4)))
    o.append('<h3>B6: the 20 reference intervals of each process</h3>')
    o.append(chart_refs(D, 'b6'))
    pm = [p['ref_median'] for p in D['b6']['processes']]
    o.append('<p class="take">The %d B6 processes have reference medians of %s to %s GB/s. Single reference intervals are %s to %s GB/s.</p>' % (
        len(pm), f(min(pm)), f(max(pm)), f(min(p['ref_min'] for p in D['b6']['processes'])), f(max(p['ref_max'] for p in D['b6']['processes']))))
    b1sizes = sorted({p['size'] for p in D['b1']['processes']}, key=lambda z: SIZES[z])
    for z in ['8M'] + [x for x in b1sizes if x != '8M']:
        bz = [p for p in D['b1']['processes'] if p['size'] == z]
        o.append('<h3>B1 at %s: the %d reference intervals of each process (two buffers, copy in the same sequence)</h3>' % (sname(z), bz[0]['n']))
        o.append(chart_refs(D, 'b1', z))
        o.append('<p class="take">The %d B1 processes at %s have reference medians of %s to %s GB/s. Single reference intervals are %s to %s GB/s%s.</p>' % (
            len(bz), sname(z), f(min(p['median'] for p in bz)), f(max(p['median'] for p in bz)), f(min(p['min'] for p in bz)), f(max(p['max'] for p in bz)), ref(10)))
    o.append('<p class="cap">In the B6 and B1 panels, one line is one process and the x axis counts its reference intervals in time order. Other kernels ran between two reference intervals. '
             'Each B1 chart has its own rate axis. The 69 and 70.5 GB/s lines are drawn only where the axis holds them.</p>')
    return o


def sec_item4(D):
    ops, G = D['operations'], D['gaps']
    o = ['<h2>6. What runs between two timed kernels in B6 (design item 4)</h2>']
    o.append('<p>The table lists every operation of the worker path and of the run script, in the order of execution, with the line of the source file%s.</p>' % ref(3, 4))
    o.append(table(['Where', 'File', 'Line', 'Kind', 'What happens'], [[x['where'], x['file'], x['line'], x['kind'], x['what']] for x in ops], left=(0, 1, 3, 4), wrap=True))
    g8 = [g for g in G if not g['entry'].endswith('@1M')]
    g1 = [g for g in G if g['entry'].endswith('@1M')]
    o.append('<p class="take">The measured time from the end of one timed interval to the start of the next is %s to %s ms (median per position) before an 8 MiB entry, and %s to %s ms before a 1 MiB entry.</p>' % (
        f(min(g['median_ms'] for g in g8), 3), f(max(g['median_ms'] for g in g8), 3), f(min(g['median_ms'] for g in g1), 3), f(max(g['median_ms'] for g in g1), 3)))
    wk = [x for x in ops if x['where'].startswith('worker, before') or x['where'].startswith('worker, after')]
    o.append('<p>So the nominal predecessor of a B6 interval is not the last loop that ran before it. In the worker path between the two timed loops, the table lists %d warm-up pass of the target kernel, %d file reads and %d barrier waits.</p>' % (
        sum(x['kind'] == 'warm-up' for x in wk), sum(x['kind'] == 'page read' for x in wk), sum(x['kind'] == 'barrier' for x in wk)))
    o.append(table(['Position', 'Entry', 'Gaps', 'Gap before the entry: median, ms', 'Lowest, ms', 'Highest, ms', 'One pass of the entry at its median rate, ms (est.)'],
                   [[g['pos'], entry_name(g['entry']), g['n'], f(g['median_ms'], 3), f(g['min_ms'], 3), f(g['max_ms'], 3), f(g['pass_ms_est'], 3)] for g in G], left=(1,)))
    o.append('<p class="cap">Gap = start time of the T row minus end time of the T row before it, both sessions, all CPUs. The times in the file have a resolution of 0.001 ms. '
             'The last column is the size of the entry divided by the median rate of the position. It estimates the warm-up pass alone.</p>')
    return o


def sec_item5(D):
    C = D['code']
    o = ['<h2>7. Instruction sequences and loop offsets (design item 5)</h2>']
    o.append('<p>The saved listing of <code>bwx</code> is compared with the listing of the original binaries. The comparison reads both files. '
             'Before the comparison, a branch target inside the function is replaced by its offset from the function start, and the address of another symbol is replaced by its name%s.</p>' % ref(5))
    rows = []
    for r in C:
        rows.append([r['kernel'], r['bwx_function'], r['reference'], '%d / %d' % (r['n_bwx'], r['n_ref']), 'equal' if r['sequence_equal'] else 'NOT equal (%d differ)' % len(r['norm_differ']),
                     len(r['raw_differ']), '%d / %d' % (r['loop_instructions_bwx'], r['loop_instructions_ref']),
                     '0x%x / 0x%x' % (r['bwx_loop'], r['ref_loop']),
                     '%d / %d: %s' % (r['bwx_loop_mod64'], r['ref_loop_mod64'], 'equal' if r['bwx_loop_mod64'] == r['ref_loop_mod64'] else 'NOT equal')])
    o.append(table(['Kernel', 'Function in bwx', 'Original function', 'Instructions', 'Sequence without link addresses', 'Instructions with a different link address',
                    'Instructions in the loop', 'Loop start address', 'Loop offset modulo 64, bytes'], rows, left=(0, 1, 2)))
    o.append('<p class="cap">Cells with two values: <code>bwx</code> / original binary. The loop is found as the first backward branch of the function. '
             'The loop offset is the listed address modulo 64. A program is loaded at a multiple of the page size, so the offset modulo 64 at run time is the same. '
             'The saved offsets file of the <code>bwx</code> build gives the same loop start and offset in %d of %d rows.</p>' % (sum(r['offsets_tsv_agrees'] for r in C), len(C)))
    eq = [r for r in C if r['primary']]
    ne = [r for r in C if r['sequence_equal'] and r['bwx_loop_mod64'] != r['ref_loop_mod64']]
    o.append('<p class="take">Equal: in %d of %d comparisons with the binary that the size comparison used, the instruction sequence and the loop offset modulo 64 are the same.</p>' % (
        sum(r['sequence_equal'] and r['bwx_loop_mod64'] == r['ref_loop_mod64'] for r in eq), len(eq)))
    o.append('<ul>')
    for r in ne:
        o.append('<li>Not equal: assembly read in <code>%s</code> has the same instructions, and its loop offset is %d. In <code>bwx</code> the loop offset is %d. '
                 'The original size comparison did not use this function.</li>' % (e(r['reference'].split()[0]), r['ref_loop_mod64'], r['bwx_loop_mod64']))
    o.append('<li>Not equal in every row: function addresses, and the text of the instructions that hold a link address (branches, the stack-check call, one page address).</li>')
    o.append('<li>Not compared here: the new runner <code>bwx8</code>. Its instructions and offsets must be compared again after it is linked on CRB. That is later work.</li></ul>')
    o.append('<details><summary>The loop bodies of <code>bwx</code></summary>')
    for r in C:
        if r['primary'] and 'second' not in r['kernel']:
            o.append('<p><b>%s</b> (%d instructions, loop offset %d)</p><pre class="sm">%s</pre>' % (e(r['kernel']), len(r['loop_body']), r['bwx_loop_mod64'], e('\n'.join(r['loop_body']))))
    o.append('</details>')
    return o


USE_NOTE = {
    'P3G': 'The check of the preparation before the paired-allocation experiment. It needs old read, new read and assembly read at 8 MiB.',
    'S3G': 'The check of the old-read preparation before the mixed-sequence experiment. It needs old read at 8 MiB only.',
    'BIN': 'The check of 10 ms time bins against window-only records, for one kernel and size.',
    'CS': 'The check of the counter modes for the size experiment, for one kernel and size.',
    'CM one rate': 'The check of the counter modes in mixed sequences, one rate, all four conditions of old and new read.',
    'CM history contrast': 'The same check for the two-rate history contrast with old read as target.',
    'CM interaction': 'The same check for the four-rate interaction. Four of its eight spreads belong to rates with new read as target.',
}


def default_words(u):
    step = u['use'].split()[0]
    if u['forecast'] == 'precision insufficient':
        s = 'No. Not scheduled by default.'
        if step == 'P3G':
            s += ' So the P3 branch is not scheduled by default either.'
        return s + ' The branch stays descriptive, or a separately reviewed pilot is proposed.'
    if u['forecast'] == ID:
        return 'Not decided from saved data. Not scheduled until the named measurement exists.'
    return {'S3G': 'The forecast does not block it. It still needs the trigger of Stage 3.',
            'BIN': 'The forecast does not block it. The step is optional. It runs only if 10 ms bins are needed.',
            'CS': 'The forecast does not block it. The design updates the forecast from the uncounted Stage 2 rates before this batch.',
            'CM': 'The forecast does not block it. The design decides it from the uncounted Stage 3 batch.'}[step]


def sec_item8(D):
    F, U = D['feasibility'], D['uses']
    o = ['<h2>8. Can the planned equivalence checks resolve their margins? (design item 8)</h2>']
    o.append('<p>The design forecasts the limit of each gate from saved repeats of one condition. For B6, the 4 rounds of a position are split into rounds 1 and 3 against rounds 2 and 4. '
             'For B4 and C1, each process is cut into %d successive blocks of 4 intervals, and each block is split the same way. The largest absolute value per process is kept, then the largest per CPU and session%s.</p>' % (
                 F['per_process'][-1]['blocks'], ref(13, 12, 17, 18)))
    o.append('<p class="miss">Every limit in this section is <b>est. for the new trial wrapper</b>. The saved intervals come from the old interval wrapper, which runs a warm-up pass, file reads and barrier waits before each interval.</p>')
    o.append('<p><span class="lg"><i style="background:%s"></i>old read at 8 MiB</span><span class="lg"><i style="background:%s"></i>old read at 1 MiB</span><span class="lg"><i style="background:%s"></i>assembly read at 8 MiB</span></p>' % (C0, C2, C1))
    o.append(chart_limits(D))
    ap = D['asm_pooled']
    o5 = [r['limit2'] for r in F['rows'] if r['source'] == 'B6 position 5' and r['cpu'] == 2]
    o.append('<p class="take">For assembly read at 8 MiB, the two-spread limit per CPU and session (B4 and C1 together) is est. %s to %s GB/s. The highest permitted margin is 0.30 GB/s. '
             'For old read at 8 MiB (B6 position 5) on CPU 2 it is est. %s and %s GB/s in the two sessions.</p>' % (
                 f(min(x['limit2'] for x in ap), 3), f(max(x['limit2'] for x in ap), 3), f(o5[0], 4), f(o5[1], 4)))
    o.append('<h3>A/A spread and projected limits by source, CPU and session</h3>')
    rows = []
    for r in F['rows']:
        cells = [r['source'].replace(' without huge pages', ', no huge pages'), r['condition'].split(',')[0], r['session'], r['cpu'], r['n_proc'], r['n_values'], f(r['spread'], 4), f(r['limit2'], 4), f(r['limit4'], 4), f(r['limit8'], 4),
                 r['transitions'], f(r['spread_no_transition'], 4) if r['transitions'] else 'same']
        rows.append(cells)
    o.append(table(['Source', 'Condition', 'Session', 'CPU', 'Processes', 'A/A values', 'A/A spread, GB/s', 'Two-spread limit, GB/s est.', 'Four-spread limit, GB/s est.', 'Eight-spread limit, GB/s est.',
                    'Transition blocks', 'Spread without them, GB/s (shown only)'], rows, left=(0, 1)))
    o.append('<p class="cap">All limits: est. for the new trial wrapper. A transition block is a block of 4 intervals whose rates span more than %s GB/s. Transition blocks stay in the spread and in every limit. '
             'The last column only shows what the other blocks alone would give. Rows of CPU 94 and rows without huge pages are shown and do not enter the forecast: the design uses CPUs 2 and 41 and requests huge pages.</p>' % f(TRANSITION_SPAN))
    o.append(table(['Session', 'CPU', 'A/A values (B4 and C1)', 'A/A spread, GB/s', 'Two-spread limit, GB/s est.'],
                   [('grp', 'Assembly read at 8 MiB: B4 and C1 together, per CPU and session')] +
                   [[x['session'], x['cpu'], x['n_values'], f(x['spread'], 4), f(x['limit2'], 4)] for x in ap], left=()))
    o.append('<details><summary>Largest absolute A/A value of every process</summary>')
    o.append(table(['Source', 'Session', 'CPU', 'Process', 'Blocks', 'Largest absolute A/A value, GB/s', 'Transition blocks', 'Largest value without transition blocks, GB/s'],
                   [[x['source'], x['session'], x['cpu'], x['tag'], x['blocks'], f(abs(x['aa']), 4), x['transitions'], f(x['aa_no_transition'] if x['aa_no_transition'] is None else abs(x['aa_no_transition']), 4)]
                    for x in F['per_process']], left=(0, 3)))
    o.append('</details>')
    o.append('<h3>The margin rule per selected use</h3>')
    o.append('<p>L0 is the largest projected limit over the conditions, CPUs (2 and 41) and sessions that one use needs. The margin is twice L0, rounded up to the next 0.05 GB/s, then clipped to the permitted range. '
             'If L0 is at or above the margin, the forecast is "precision insufficient"%s.</p>' % ref(13, 15))
    rows = []
    for u in U:
        parts = '<br>'.join('%s: %s GB/s est.' % (k, f(v, 4)) for k, v in u['parts'].items())
        if u['missing']:
            parts += ('<br>' if parts else '') + '<b>%s</b>: %s' % (ID, e(u['missing']))
        sp = '%d' % u['spreads'] + (' (%d with saved data)' % u['spreads_known'] if u.get('spreads_known') else '')
        partial = u['forecast'] == ID
        rows.append([u['use'], u['quantity'], sp, parts, 'unknown' if u.get('L0') is None else ('at&nbsp;least ' if u['missing'] else '') + f(u['L0'], 4), 'not fixed' if partial else f(u['twice_rounded']),
                     'not fixed (%s to %s)' % (f(u['lower']), f(u['upper'])) if partial else '%s (%s to %s)%s' % (f(u['margin']), f(u['lower']), f(u['upper']), ', clipped' if u['clipped'] else ''),
                     '<b>%s</b>' % u['forecast'], f(u['largest_passing_median'], 3) if u['largest_passing_median'] is not None else 'none', default_words(u)])
    o.append(table(['Use', 'Quantity', 'Spreads in the limit', 'Projected limit per condition', 'L0, GB/s est.', 'Twice L0, rounded up, GB/s', 'Margin, GB/s (permitted range)', 'Forecast',
                    'Largest median that can pass, GB/s est.', 'Scheduled by default?'], rows, left=(0, 1, 3, 7, 9), wrap=True))
    o.append('<p class="cap">"feasible" means that L0 is below the margin. Largest median that can pass = margin minus L0. The gate keeps its three conditions. '
             '"at least": a condition of the use has no saved data, and a missing condition can only raise L0. For the CM interaction, L0 holds only the four spreads that have saved data.</p>')
    o.append('<ul>' + ''.join('<li><b>%s</b>: %s</li>' % (k, e(v)) for k, v in USE_NOTE.items()) + '</ul>')
    p3g = [u for u in U if u['use'] == 'P3G'][0]
    o.append('<p class="take">P3G: L0 is est. %s GB/s and the margin is %s GB/s. The forecast is "%s". Even the lowest two-spread limit of assembly read (est. %s GB/s) is at or above the margin%s.</p>' % (
        f(p3g['L0'], 3), f(p3g['margin']), p3g['forecast'], f(min(x['limit2'] for x in ap), 3), ref(14, 15)))
    o.append('<p class="miss"><b>%s</b>: no saved one-thread run in these sources repeats new read at 8 MiB under one condition. So the projected limit of new read is unknown. '
             'The measurement that resolves it: the A/A values of new read at 8 MiB from the uncounted size experiment (step S2), or from the uncounted mixed-sequence experiment (step S3) for rates with a predecessor.</p>' % ID)
    o.append('<h3>Can P1 reach its 0.30 GB/s margin? An emulation on B6</h3>')
    P = [x for x in D['p1'] if x['cpu'] in NEW_CPUS]
    o.append('<p>P1 of the design compares old read at 8 MiB with old read at 1 MiB. B6 holds a similar pair in one process: position 5 minus position 4. Each process gives one difference (median over 4 rounds). '
             'The limit is the A/A spread of position 5 plus the A/A spread of position 4.</p>')
    o.append('<p class="take">On CPUs 2 and 41 the single differences are %s to %s GB/s. The largest absolute difference plus the limit is %s to %s GB/s per CPU and session. All are at most 0.30 GB/s: %s%s.</p>' % (
        sg(min(x['diff_min'] for x in P), 3), sg(max(x['diff_max'] for x in P), 3), f(min(x['worst'] for x in P), 3), f(max(x['worst'] for x in P), 3), 'yes' if all(x['within_030'] for x in P) else 'no', ref(12, 14)))
    o.append(table(['Session', 'CPU', 'Processes', 'Lowest difference, GB/s', 'Highest difference, GB/s', 'Two-rate limit, GB/s est.', 'Largest absolute difference plus limit, GB/s est.', 'At most 0.30 GB/s'],
                   [[x['session'], x['cpu'], x['n'], sg(x['diff_min'], 3), sg(x['diff_max'], 3), f(x['limit'], 3), f(x['worst'], 3), 'yes' if x['within_030'] else 'no'] for x in D['p1']], left=()))
    o.append('<p class="cap">This is an emulation in one process of the old interval wrapper. P1 itself compares separate processes of the new runner, so these values are est.</p>')
    return o


def sec_load(D):
    o = ['<h2>9. System load of each source run</h2>']
    o.append('<p>Every source file records the 1-minute load average at the launch of each process. The result folders of the <code>bwx</code> steps also record the load at the start and the end of the step%s.</p>' % ref(1, 5, 10, 11, 12, 17, 18))
    o.append(table(['Run', 'Processes', 'Lowest load at a launch', 'Highest load at a launch', 'Load at the start (1, 5, 15 minutes)', 'Load at the end (1, 5, 15 minutes)'],
                   [[x['run'], x['n'], f(x['load_min']), f(x['load_max']), x['start'] or 'not recorded', x['end'] or 'not recorded'] for x in D['load']], left=(0,)))
    b1 = [x for x in D['load'] if x['run'].startswith('B1')]
    o.append('<p class="take">B1 started while the load average was still high: %s in session 1 and %s in session 2 at the first launch. The other steps launched at a load of %s to %s.</p>' % (
        f(b1[0]['load_max']), f(b1[1]['load_max']), f(min(x['load_min'] for x in D['load'] if not x['run'].startswith('B1'))),
        f(max(x['load_max'] for x in D['load'] if not x['run'].startswith('B1')))))
    o.append('<p class="cap">A load average falls slowly after work ends. The run script waited until at most 2 tasks were runnable before each launch. The files do not record which earlier work raised the load average.</p>')
    return o


def sec_stop(D):
    S = D['stop']
    K = S['candidate']
    yn = lambda b: 'yes' if b else 'NO'
    o = ['<h2>10. Stage 0 stop decision (design line 129)</h2>']
    o.append(table(['Check', 'Result'], [
        ['Evidence table complete (original run, 06:05 UTC run, B1 reference rows, cache sizes found in the report)', yn(S['parts']['evidence_table'])],
        ['Position traces complete (13 positions × 3 CPUs × 2 sessions, 32 intervals each)', yn(S['parts']['position_traces'])],
        ['Source and loop checks complete (every listed operation found in the source, 5 listing comparisons made)', yn(S['parts']['source_and_loop_checks'])],
        ['Equivalence-feasibility table complete', yn(S['parts']['feasibility_table'])],
        ['The files reproduce the size table of the design (4 sizes, rates and gains)', yn(S['table_reproduced'])],
        ['The files reproduce the four process-median gains at 8 MiB (%s %%)' % ', '.join(f(x) for x in S['gains_8m']), yn(S['median_gains_reproduced'])],
        ['Every process of the original run ran one kernel, with 3 repetitions', yn(S['one_kernel_per_process'])],
        ['The loops of <code>bwx</code> equal the loops of the binaries that the size comparison used: old read in <code>bw_old</code>, new read and assembly read in <code>bw_new</code> '
         '(instructions and loop offset, %d of %d comparisons).%s' % (S['loops_equal'], S['loops_compared'], ''.join(
             ' Not in this count: assembly read of <code>%s</code> has loop offset %d bytes, and <code>bwx</code> has %d bytes (section 7).' % (
                 e(r['reference'].split()[0]), r['ref_loop_mod64'], r['bwx_loop_mod64']) for r in D['code'] if not r['primary'] and r['bwx_loop_mod64'] != r['ref_loop_mod64'])),
         yn(S['loops_equal_to_original'])],
        ('grp', 'The candidate of the design (old read at a core limit near 67 GB/s, the load-only loops lose rate as the buffer grows), against the original run'),
        ['Old read at 8 MiB minus old read at 1 MiB is at most %s GB/s in absolute value in every pair of process medians (%d pairs: %s GB/s). '
         'The process medians of old read at 8 MiB are %s to %s GB/s.' % (f(CANDIDATE_MARGIN), len(K['old_diff']), ', '.join(sg(x) for x in K['old_diff']), f(K['old_8m'][0]), f(K['old_8m'][1])),
         yn(K['old_nearly_constant'])],
        ['New read is lower at 8 MiB than at 1 MiB in every pair of process medians (%d pairs: %s GB/s)' % (len(K['new_diff']), ', '.join(sg(x) for x in K['new_diff'])), yn(K['new_lower_at_8m'])],
        ['Assembly read is lower at 8 MiB than at 1 MiB in every pair of process medians (%d pairs, both binaries: %s to %s GB/s)' % (
            len(K['asm_diff']), sg(min(K['asm_diff'])), sg(max(K['asm_diff']))), yn(K['asm_lower_at_8m'])],
    ], left=(0, 1), wrap=True))
    o.append('<p class="cap">Candidate rows: one pair is the same binary, CPU and round of the original run at 1 MiB and at 8 MiB%s. %s GB/s is the margin that the design gives its prediction P1. '
             'These rows are not the test of P1 or P2. A process of the original run has 3 repetitions, so the files give no A/A limit for these differences.</p>' % (ref(1, 13), f(CANDIDATE_MARGIN)))
    if S['proceed']:
        o.append('<p class="take">All four parts of the Stage 0 output are complete. The sources do not contradict the claimed size comparison. '
                 'The original run does not contradict the candidate. By the rule of the design, the work proceeds through runner acceptance to the size experiment.</p>')
    elif S['complete'] and S['consistent']:
        o.append('<p class="miss">Stage 0 does not proceed: the original run contradicts a part of the candidate (a row above says NO). '
                 'The rule of the design allows the size experiment only if the candidate remains consistent with the files. The design names no next step for this case.</p>')
    else:
        o.append('<p class="miss">Stage 0 does not pass: a part is incomplete, or a source contradicts the claimed size comparison. By the rule of the design, stop for reconciliation before a machine run.</p>')
    o.append('<p>What this page does not decide:</p><ul>'
             '<li>It describes existing data. It establishes no causal history effect. The B6 order effect is an observation in one fixed sequence.</li>'
             '<li>It does not test the candidate explanation of the design. The candidate rows above only show that the original run does not contradict it. The test needs the size experiment.</li>'
             '<li>The forecast leaves these uses at "%s": %s.</li>'
             '<li>The B6 effect alone does not make the mixed-sequence stage the first experiment (design line 129).</li></ul>' % (ID, ', '.join(S['missing']) or 'none'))
    return o


def references():
    R = [
        (1, RES + '/kernels-20261113T181222Z/one-thread.csv', 'original per-process repetitions'),
        (2, CRB + '/new-test-kernel/results.md', 'the earlier result handoff. This page recomputes its numbers and copies no conclusion.'),
        (3, SRC['bwx_c'], 'functions call, worker and main'),
        (4, SRC['run_sh'], 'B6SEQ, step_B6 and the process wrapper'),
        (5, SRC['listing'] + ', ' + SRC['offsets'] + ', ' + SRC['build'] + '; original loops: ' + SRC['probe'], 'machine-code listings. The second file also holds the load at the start and the end of the original run.'),
        (8, CRB + '/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh', 'the script of the original run'),
        (9, SRC['hier'], 'cache sizes of the local hardware report'),
        (10, csv_path('B1', 1) + ' and ' + csv_path('B1', 2), 'B1 raw files'),
        (11, SRC['cread'], 'the 06:05 UTC run'),
        (12, csv_path('B6', 1) + ' and ' + csv_path('B6', 2), 'B6 raw files. The file env.txt in the result folder of each B1, B4, B6 and C1 file holds the load at the start and the end.'),
        (13, DESIGN, 'the design. Stage 0 is lines 114 to 129. The margin rule is lines 183 to 191.'),
        (14, DESIGN + '.review.md', 'review record. The last entry (line 344 to the end) holds the four notes for the implementer and the check values.'),
        (15, CRB + '/tmp/agent-scratch/bwx8-2026-11-14/DECISIONS-bwx8.md', 'the fixed readings of the four notes'),
        (16, os.path.join(HERE, 'stage0.py') + ', ' + os.path.join(HERE, 'stage0.json') + ', ' + os.path.join(HERE, 'test_stage0.py'), 'the script that wrote this page, every computed table, and the tests'),
        (17, csv_path('B4', 1) + ' and ' + csv_path('B4', 2), 'B4 raw files'),
        (18, csv_path('C1', 1) + ' and ' + csv_path('C1', 2), 'C1 raw files'),
    ]
    o = ['<h2>References</h2><p class="sm">Ref1 to Ref12 keep the numbers of the design. Ref6 and Ref7 of the design are not used on this page.</p><ul class="sm">']
    for n, path, what in R:
        o.append('<li>[Ref%d] <code>%s</code>: %s</li>' % (n, e(path), e(what)))
    o.append('</ul>')
    return o


def build(D):
    I = D['item1']
    b8 = [x for x in I['best'] if x['size'] == '8M'][0]
    g8 = sorted(p['gain_pct'] for p in I['pairs'] if p['size'] == '8M')
    B, ap = D['pairs_by_session'], D['asm_pooled']
    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
         '<title>Stage 0 evidence</title><style>%s</style></head><body>' % CSS,
         '<h1>Stage 0: the saved evidence on the small read gain at 8 MiB</h1>']
    o.append('<p><b>Short version.</b> The saved files reproduce the original size comparison: at 8 MiB new read is %s %% faster than old read by best rates, and %s %% to %s %% by process medians. '
             'In the B6 sequences, the first old-read interval after assembly read is slower than the second in %d of %d pairs in session 1 and in %d of %d pairs in session 2. '
             'The forecast for every gate that includes assembly read at 8 MiB is "precision insufficient": its two-spread limit is est. %s to %s GB/s, and the highest permitted margin is 0.30 GB/s.</p>' % (
                 f(b8['gain_pct']), f(g8[0]), f(g8[-1]), B[1]['first_slower'], B[1]['n'], B[2]['first_slower'], B[2]['n'], f(min(x['limit2'] for x in ap), 3), f(max(x['limit2'] for x in ap), 3)))
    o.append('<h2>Words used here</h2><ul class="words">' + ''.join('<li><b>%s</b>: %s</li>' % kv for kv in WORDS) + '</ul>')
    o.append('<h2>What this page is</h2><ul>'
             '<li>It is the output of Stage 0 of the design "explain the small read-bandwidth gain at 8 MiB"%s.</li>'
             '<li>It reads only saved files on the development machine. No program ran on CRB for it.</li>'
             '<li>It describes existing data. It does not establish a causal history effect.</li>'
             '<li>Every number in a sentence, chart or table is computed by the script from the files in the reference list%s.</li></ul>' % (ref(13), ref(16)))
    for sec in (sec_item1, sec_item6, sec_item2, sec_item7, sec_item3, sec_item4, sec_item5, sec_item8, sec_load, sec_stop):
        o += sec(D)
    o += references()
    o.append('</body></html>')
    return '\n'.join(o)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('-o', default=os.path.join(HERE, 'stage0.html'))
    ap.add_argument('--json', default=os.path.join(HERE, 'stage0.json'))
    a = ap.parse_args(argv)
    D = compute()
    with open(a.o, 'w') as fh:
        fh.write(build(D))
    slim = json.loads(json.dumps(D))
    for p in slim['b4'] + slim['c1']:
        p['rates'] = [round(x, 4) for x in p['rates']]
    with open(a.json, 'w') as fh:
        json.dump(slim, fh, indent=1, sort_keys=True)
    S = D['stop']
    print('wrote %s and %s' % (a.o, a.json))
    print('Stage 0 complete: %s. Sources consistent with the claimed size comparison: %s. Candidate not contradicted by the original run: %s.' % (
        'yes' if S['complete'] else 'no', 'yes' if S['consistent'] else 'no', 'yes' if S['candidate']['not_contradicted'] else 'no'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
