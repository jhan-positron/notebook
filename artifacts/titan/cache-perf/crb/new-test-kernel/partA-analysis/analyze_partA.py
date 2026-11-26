#!/usr/bin/env python3
"""analyze_partA.py <result folder>... [--out partA-summary.json]

Analysis of Part A (screening) of new-test-kernel/plan.md, as handoff.md says in
"How to analyse Part A". Input: one or more folders partA-<UTC>/ written by run_partA.sh
(A1.csv ... A6.csv, env.txt, launches.txt, stderr.txt, A7-*.txt). Output: partA-summary.json.

Part A is screening. Nothing computed here closes a hypothesis.

Choices of this script where the handoff gives no exact definition (also written to the json,
key "choices"):
  C1 percentile: nearest rank. Rates sorted upward, the value at the P-th percentile is the
     value number ceil(P/100 x n), counted from 1. With 120 threads: number 12 and number 108.
  C2 "two groups" of q: all q of repetitions with at least 2 threads are sorted. The largest
     distance between two neighbouring values divides them into a lower and an upper group.
     q "falls into two groups" if each group has at least 2 values, the distance is at least
     0.10, and the distance is larger than the width of each group. The labels are used only
     if, in addition, every value of the lower group is below 0.65 and every value of the upper
     group is above 0.85.
  C3 fastest half: the n//2 threads with the highest rates. Thread rates are printed with 2
     decimals, so several threads can have the rate of the last place. The count of each mesh
     is then given as a lowest and a highest possible value.
  C4 repeated launch: if one (step, tag) has several blocks, the last complete block is used.
     The other blocks are listed under "not_used".
  C5 a count of A4 (for example 64+48) has the label of its repetitions if all have the same
     label, and "mixed" otherwise.
  C7 A4 bracket: looked for among the counts with threads on both meshes (64+0 is left out). A
     bracket is given only if there is exactly one change and it is between split and uniform.
  C8 q of A3: the write and copy repetitions of the A3 processes with two buffers
     (--kernel all) are not used for the test of the two groups. The handoff says to compare
     only the rows of the read kernel for A3. They are listed in the json under q.rows_left_out.
  C6 A5 level change: the labels "low" and "high" of the intervals in time order, with
     "changing" intervals left out. A change is a place where this sequence goes from one
     label to the other. Its position is the number of the first interval with the new label.
  C9 check of the level limits (plan rule 5: "checked against the distribution of the new data
     before they are used"): done for each CPU over its A5 and A6 rates. A limit does not
     separate the rates of a CPU if rates lie on both sides of it and the empty range around it
     (from the nearest rate below the limit to the nearest rate at or above it) is smaller than
     0.25 GB/s. The level labels of a CPU are usable only if both limits separate its rates.
     Level changes (C6) are given only for a CPU with usable labels.
  C10 event names for the five events of handoff B.8, looked up in A7-core-events.txt:
     cycles = cpu_cycles, instructions = inst_retired, L1 data refills = l1d_cache_refill,
     L2 data refills = l2d_cache_refill, last-level read misses = ll_cache_miss_rd.
     l3d_cache_refill is listed as a second candidate for the last one. No choice is made.
  C11 "A2 changed the totals" (plan, "Order and decision points", item 2; the plan gives no
     number): for each interval the range of the difference old read minus new read goes from
     (lowest old total - highest new total) to (highest old total - lowest new total). The
     totals count as changed only if the range with the long interval does not overlap the
     range with the short interval.
"""
import sys, os, re, json, math, glob, statistics as st

Q_SPLIT, Q_UNIFORM = 0.65, 0.85          # handoff, "How to analyse Part A", item 3 (provisional)
LOW_BELOW, HIGH_ABOVE = 69.0, 70.5       # GB/s, plan rule 5 (provisional)
MIN_PASSES = 50                          # plan rule 7: interval/passes <= 2 % of the interval
GAP_MIN = 0.10
LEVEL_GAP_MIN = 0.25                     # GB/s, choice C9
B8_EVENTS = [('cycles', 'cpu_cycles'), ('instructions', 'inst_retired'), ('L1 data refills', 'l1d_cache_refill'),
             ('L2 data refills', 'l2d_cache_refill'), ('last-level read misses', 'll_cache_miss_rd')]      # choice C10
B8_OTHER = [('last-level read misses', 'l3d_cache_refill')]
STEPS = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7']
A4_SERIES = {'64+b': ['64+0', '64+16', '64+32', '64+40', '64+48', '64+52', '64+56'],
             'a+a': ['32+32', '40+40', '48+48', '56+56']}
CHOICES = {
    'C1_percentile': 'nearest rank: value number ceil(P/100 x n) of the rates sorted upward',
    'C2_two_groups': 'largest distance between neighbouring q values divides them; two groups if each side has '
                     'at least 2 values, the distance is at least 0.10 and larger than the width of each group; '
                     'labels are used only if also the lower group is below 0.65 and the upper group above 0.85',
    'C3_fastest_half': 'n//2 fastest threads; with equal rates at the last place the count per mesh is a lowest and a highest value',
    'C4_repeated_launch': 'the last complete block of a (step, tag) is used; the others are listed under not_used',
    'C5_A4_count_label': 'label of a count = label of its repetitions if all are equal, else mixed',
    'C7_A4_bracket': 'the two neighbouring counts between which the label changes are looked for among the counts with threads '
                     'on both meshes; 64+0 keeps its own label and is left out; a bracket is given only if there is exactly one '
                     'change and it is between split and uniform',
    'C8_q_of_A3': 'the write and copy repetitions of the A3 processes with two buffers (--kernel all) are not used for the '
                  'test of the two groups, because the handoff says to compare only the rows of the read kernel for A3; '
                  'they are listed under q.rows_left_out',
    'C6_A5_change': 'low/high sequence without the changing intervals; position = first interval with the new label',
    'C9_level_limits': 'per CPU over its A5 and A6 rates: a limit does not separate the rates if rates lie on both sides of it and the '
                       'empty range around it is smaller than 0.25 GB/s; level labels and level changes are used only for a CPU '
                       'where both limits separate the rates',
    'C10_event_names': 'cycles = cpu_cycles, instructions = inst_retired, L1 data refills = l1d_cache_refill, L2 data refills = '
                       'l2d_cache_refill, last-level read misses = ll_cache_miss_rd; l3d_cache_refill is a second candidate for the last',
    'C11_A2_changed_totals': 'range of (old read total - new read total) per interval = lowest old - highest new to highest old - lowest new; '
                             'the totals count as changed only if the range with the long interval does not overlap the range with the short interval',
}

HDR = re.compile(r'^-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) '
                 r'logins (\S+) utc (\S+) args (.*)$')


def pct(sorted_vals, p):
    """Nearest-rank percentile (choice C1)."""
    n = len(sorted_vals)
    return sorted_vals[min(n, max(1, math.ceil(p / 100.0 * n))) - 1]


def mesh_of(cpu):
    return 0 if cpu < 64 else 1


def level(rate):
    return 'low' if rate < LOW_BELOW else 'high' if rate > HIGH_ABOVE else 'changing'


def rule_label(q):
    return 'split' if q < Q_SPLIT else 'uniform' if q > Q_UNIFORM else 'between'


def arg_of(args, name, default=None):
    a = args.split()
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def parse_csv(path, folder):
    """Return the list of blocks (one per process) of one csv file, in file order."""
    blocks, cur = [], None
    with open(path) as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip('\n')
            m = HDR.match(line)
            if m:
                step, tag, binary, waited, l1, l5, l15, run, logins, utc, args = m.groups()
                cur = dict(folder=folder, file=os.path.basename(path), line=ln, step=step, tag=tag, binary=binary,
                           waited_s=float(waited), load1=float(l1), load5=float(l5), load15=float(l15),
                           runnable=int(run.split('/')[0]), logins=int(logins), utc=utc, args=args,
                           min_ms=None, thp=None, killed=None, failed=None, rows={}, best={}, thr={}, bad_lines=[])
                blocks.append(cur)
                continue
            if cur is None:
                continue
            if line.startswith('-- killed'):
                cur['killed'] = line[3:]
                continue
            if line.startswith('-- failed'):
                cur['failed'] = line[3:]
                continue
            if line.startswith('# bandwidth:'):
                m = re.search(r'min_ms=(\S+) thp=(\S+)', line)
                if m:
                    cur['min_ms'] = float(m.group(1)); cur['thp'] = m.group(2)
                continue
            p = line.split(',')
            try:
                if p[0] == 'thread' and len(p) == 6:
                    cur['thr'].setdefault((p[3], int(p[4])), []).append((int(p[2]), float(p[5])))
                elif len(p) == 10 and p[3].isdigit():      # a data line: the 4th field is a number
                    cur['rows'][(p[0], int(p[3]))] = dict(threads=int(p[1]), bytes_per_thread=int(p[2]),
                                                           total_bytes=int(p[4]), elapsed_s=float(p[5]),
                                                           total_GBps=float(p[6]), thr_min=float(p[7]),
                                                           thr_max=float(p[8]), thr_avg=float(p[9]))
                elif len(p) == 10 and p[3] == 'best':
                    cur['best'][p[0]] = float(p[6])
                elif line.strip() and not line.startswith('kernel,'):
                    cur['bad_lines'].append(ln)
            except ValueError:
                cur['bad_lines'].append(ln)                 # a line cut by a kill
    return blocks


def fastest_half(threads):
    """Choice C3. threads: list of (cpu, rate). Lowest and highest possible count of each mesh."""
    n = len(threads); h = n // 2
    if h == 0:
        return None
    s = sorted(threads, key=lambda t: -t[1])
    cut = s[h - 1][1]
    sure = [t for t in s if t[1] > cut]; tied = [t for t in s if t[1] == cut]
    free = h - len(sure)
    out = dict(n_half=h, cut_rate=cut, tied_at_cut=len(tied) if len(tied) > free else 0)
    for m in (0, 1):
        a = sum(1 for t in sure if mesh_of(t[0]) == m); tm = sum(1 for t in tied if mesh_of(t[0]) == m)
        out[f'mesh{m}'] = [a + max(0, free - (len(tied) - tm)), a + min(free, tm)]
    return out


def analyse_rep(kernel, rep, row, threads):
    d = dict(kernel=kernel, rep=rep, **row)
    div = row['threads'] * row['bytes_per_thread'] * (2 if 'copy' in kernel else 1)
    d['passes_per_thread'] = row['total_bytes'] / div
    d['below_50_passes'] = d['passes_per_thread'] < MIN_PASSES
    d['thread_lines'] = len(threads)
    d['threads_cpu_rate'] = [[c, r] for c, r in threads]
    for m in (0, 1):
        v = [r for c, r in threads if mesh_of(c) == m]
        d[f'mesh{m}'] = dict(n=len(v), sum=round(sum(v), 2), median=st.median(v)) if v else dict(n=0, sum=None, median=None)
    if len(threads) >= 2:
        s = sorted(r for _, r in threads)
        d['p10'], d['p90'] = pct(s, 10), pct(s, 90)
        d['q'] = d['p10'] / d['p90'] if d['p90'] > 0 else None
        d['label_rule'] = rule_label(d['q']) if d['q'] is not None else None
        d['fastest_half'] = fastest_half(threads)
    else:
        d['p10'] = d['p90'] = d['q'] = d['label_rule'] = d['fastest_half'] = None
    d['label'] = None                                  # set later, only if the labels may be used
    return d


def finish_block(b):
    """Turn the raw rows of a block into repetitions, and decide whether the block is complete."""
    reps = [analyse_rep(k, r, row, b['thr'].get((k, r), [])) for (k, r), row in b['rows'].items()]
    want = arg_of(b['args'], '--reps'); want = int(want) if want else None
    kernels = list(dict.fromkeys(r['kernel'] for r in reps))
    problems = []
    if b['killed']: problems.append('killed')
    if b['failed']: problems.append('failed')
    if not reps: problems.append('no data line')
    for k in kernels:
        n = sum(1 for r in reps if r['kernel'] == k)
        if want and n != want: problems.append(f'{k}: {n} of {want} repetitions')
        if k not in b['best']: problems.append(f'{k}: no best line')
    if '--per-thread' in b['args'].split():
        for r in reps:
            if r['thread_lines'] != r['threads']:
                problems.append(f"{r['kernel']} rep {r['rep']}: {r['thread_lines']} of {r['threads']} thread lines")
    if b['bad_lines']: problems.append(f"{len(b['bad_lines'])} lines not understood")
    ak = arg_of(b['args'], '--kernel')
    if ak and ak != 'all' and kernels and kernels != [ak]: problems.append(f'kernel {kernels} is not --kernel {ak}')
    out = {k: b[k] for k in ('folder', 'file', 'line', 'step', 'tag', 'binary', 'waited_s', 'load1', 'load5', 'load15',
                             'runnable', 'logins', 'utc', 'args', 'min_ms', 'thp', 'killed', 'failed')}
    out.update(reps=reps, complete=not problems, problems=problems, cpus=arg_of(b['args'], '--cpus'))
    return out


def parse_launches(path, folder):
    out, cur = [], None
    if not os.path.exists(path):
        return out
    for line in open(path):
        m = re.match(r'^== (\S+)\.csv (\S+) utc (\S+) loadavg (\S+) (\S+) (\S+) (\S+) logins (\S+)', line)
        if m:
            cur = dict(folder=folder, step=m.group(1), tag=m.group(2), utc=m.group(3), load1=float(m.group(4)),
                       runnable=int(m.group(7).split('/')[0]), logins=int(m.group(8)), busiest=[])
            out.append(cur)
        elif cur is not None:
            p = line.split(None, 2)
            if len(p) == 3 and p[0] != '%CPU':
                try: cur['busiest'].append(dict(pcpu=float(p[0]), user=p[1], comm=p[2].strip()))
                except ValueError: pass
    return out


def parse_core_events(lines):
    """A7-core-events.txt: one line '== <path of the PMU> type=<n>' per core PMU, then '<path>/events/<name>:event=<code>'."""
    pmus = []
    for ln, l in enumerate(lines, 1):
        m = re.match(r'^== (\S+) type=(\S*)', l)
        if m:
            pmus.append(dict(name=os.path.basename(m.group(1)), type=m.group(2) or None, line=ln, events={}))
            continue
        m = re.match(r'^\S*/events/([^:/]+):event=(\S+)', l)
        if m and pmus:
            pmus[-1]['events'][m.group(1)] = dict(code=m.group(2), line=ln)
    for p in pmus:
        p['n_events'] = len(p['events'])
        p['b8'] = [dict(event=ev, name=nm, **(p['events'].get(nm) or dict(code=None, line=None))) for ev, nm in B8_EVENTS]
        p['b8_other'] = [dict(event=ev, name=nm, **p['events'][nm]) for ev, nm in B8_OTHER if nm in p['events']]
    return pmus


def parse_env(folder):
    d = dict(folder=os.path.basename(os.path.normpath(folder)), present=False, a7={})
    p = os.path.join(folder, 'env.txt')
    if os.path.exists(p):
        d['present'] = True
        t = open(p).read()
        for key, rx in (('host', r'## host=(\S+)'), ('start_utc', r'## host=\S+ utc=(\S+)'),
                        ('start_loadavg', r'## host=.* loadavg=(\S+ \S+ \S+ \S+)'), ('start_logins', r'## host=.* logins=(\d+)'),
                        ('steps', r' steps=(.*)'), ('thp', r'## thp=(.*?) defrag='), ('end_utc', r'## end utc=(\S+)'),
                        ('end_loadavg', r'## end utc=\S+ loadavg=(\S+ \S+ \S+ \S+)'), ('mem_available_kB', r'MemAvailable: (\d+)')):
            m = re.search(rx, t)
            d[key] = m.group(1) if m else None
        d['skipped'] = re.findall(r'^(A\d skipped.*)$', t, re.M)
        m = re.search(r'## busiest processes.*\n((?:.*\n){1,6})', t)
        d['busiest_at_start'] = [l.strip() for l in m.group(1).splitlines()[1:]] if m else []
    for f in sorted(glob.glob(os.path.join(folder, 'A7-*.txt'))):
        lines = open(f, errors='replace').read().splitlines()
        e = dict(lines=len(lines))
        if f.endswith('A7-sve.txt'):
            e['sve_vector_length_bytes'] = next((l.strip() for l in lines if l.strip().isdigit()), None)
        if f.endswith('A7-core-events.txt'):
            e['pmus'] = [l for l in lines if l.startswith('== ')]
            e['pmu_list'] = parse_core_events(lines)
        d['a7'][os.path.basename(f)] = e
    p = os.path.join(folder, 'stderr.txt')
    d['stderr_lines'] = len(open(p, errors='replace').read().splitlines()) if os.path.exists(p) else None
    return d


def two_groups(qs):
    """Choice C2. qs: list of q values. Returns the verdict and its numbers."""
    r = dict(n=len(qs), two_groups=False, limits_fit=False, labels_usable=False, reason='')
    if len(qs) < 4:
        r['reason'] = f'only {len(qs)} repetitions with a q value' if qs else 'no repetition with a q value'
        return r
    s = sorted(qs)
    gaps = [(s[i + 1] - s[i], i) for i in range(len(s) - 1)]
    g, i = max(gaps)
    lo, hi = s[:i + 1], s[i + 1:]
    r.update(gap=g, gap_from=lo[-1], gap_to=hi[0], n_lower=len(lo), n_upper=len(hi), lower_min=lo[0], lower_max=lo[-1],
             upper_min=hi[0], upper_max=hi[-1], q_min=s[0], q_max=s[-1],
             n_split=sum(q < Q_SPLIT for q in s), n_uniform=sum(q > Q_UNIFORM for q in s),
             n_between=sum(Q_SPLIT <= q <= Q_UNIFORM for q in s))
    why = []
    if min(len(lo), len(hi)) < 2: why.append('one side of the largest distance has fewer than 2 values')
    if g < GAP_MIN: why.append(f'the largest distance between neighbouring q values is {g:.3f}, below {GAP_MIN:.2f}')
    if g <= max(lo[-1] - lo[0], hi[-1] - hi[0]): why.append('the largest distance is not larger than the width of each group')
    r['two_groups'] = not why
    if r['two_groups']:
        r['limits_fit'] = lo[-1] < Q_SPLIT and hi[0] > Q_UNIFORM
        if not r['limits_fit']:
            why.append(f'the groups do not lie on the two sides of the limits {Q_SPLIT} and {Q_UNIFORM}')
    r['labels_usable'] = r['two_groups'] and r['limits_fit']
    r['reason'] = '; '.join(why)
    return r


def rng(v):
    return dict(n=len(v), min=min(v), median=st.median(v), max=max(v)) if v else dict(n=0, min=None, median=None, max=None)


def labels_of(reps):
    return [r['label'] for r in reps]


def one_label(labels):
    """Choice C5."""
    if not labels or any(l is None for l in labels): return None
    return labels[0] if len(set(labels)) == 1 else 'mixed'


def rep_brief(b, r):
    return dict(tag=b['tag'], rep=r['rep'], total_GBps=r['total_GBps'], q=r['q'], label=r['label'], label_rule=r['label_rule'],
                passes_per_thread=r['passes_per_thread'], below_50_passes=r['below_50_passes'],
                mesh0=r['mesh0'], mesh1=r['mesh1'], fastest_half=r['fastest_half'])


def kernel_name(tag):
    return tag.rsplit('-r', 1)[0]


def kname_of(b, r):
    """Kernel name as in the A1 tags (read_old, read_new, asmread, ...), for a repetition of any step."""
    if b['step'] in ('A1', 'A2'): return kernel_name(b['tag'])
    if b['step'] == 'A4': return b['tag'].rsplit('-', 1)[0]
    if b['step'] == 'A3': return r['kernel'] + ('_old' if b['binary'] == 'bw_old' else '_new')
    return r['kernel']


def q_groups(qrows):
    """Where the q values lie: the read kernels at the full count 64+56, and the rows below the split limit."""
    def grp(names):
        v = [x for x in qrows if x['count'] == '64+56' and x['kname'] in names]
        return dict(n=len(v), q=rng([x['q'] for x in v]), mesh0_median=rng([x['mesh0_median'] for x in v]), mesh1_median=rng([x['mesh1_median'] for x in v]),
                    n_split=sum(x['q'] < Q_SPLIT for x in v), n_uniform=sum(x['q'] > Q_UNIFORM for x in v))
    old, lo = grp(['read_old']), grp(['read_new', 'asmread'])
    below, between = {}, {}
    for x in qrows:
        if x['q'] < Q_SPLIT: below[(x['kname'], x['count'])] = below.get((x['kname'], x['count']), 0) + 1
        elif x['q'] <= Q_UNIFORM: between[(x['kname'], x['step'])] = between.get((x['kname'], x['step']), 0) + 1
    sep = bool(old['n'] and lo['n'] and (old['q']['max'] < lo['q']['min'] or lo['q']['max'] < old['q']['min']))
    return dict(count='64+56', read_old=old, load_only_read=lo, ranges_separate=sep,
                below_split=[dict(kname=k, count=c, n=n) for (k, c), n in sorted(below.items(), key=lambda z: -z[1])],
                between=[dict(kname=k, step=s_, n=n) for (k, s_), n in sorted(between.items(), key=lambda z: -z[1])])


def step_a12(blocks):
    """A1 or A2: per kernel (read_old ... asmwrite) the repetitions of both rounds."""
    out = {}
    for b in blocks:
        k = out.setdefault(kernel_name(b['tag']), dict(binary=b['binary'], min_ms=b['min_ms'], reps=[]))
        k['reps'] += [rep_brief(b, r) for r in b['reps']]
    for k in out.values():
        r = k['reps']
        k['total_GBps'] = rng([x['total_GBps'] for x in r])
        k['q'] = rng([x['q'] for x in r if x['q'] is not None])
        k['labels'] = sorted(set(str(x['label']) for x in r)) if all(x['label'] for x in r) else None
        k['passes_per_thread'] = rng([x['passes_per_thread'] for x in r])
        k['n_below_50_passes'] = sum(x['below_50_passes'] for x in r)
        for m in ('mesh0', 'mesh1'):
            k[m + '_median'] = rng([x[m]['median'] for x in r if x[m]['median'] is not None])
            k[m + '_sum'] = rng([x[m]['sum'] for x in r if x[m]['sum'] is not None])
    return out


def compare_a1_a2(a1, a2):
    out = {}
    for k in a1:
        if k in a2 and a1[k]['total_GBps']['n'] and a2[k]['total_GBps']['n']:
            s, l = a1[k]['total_GBps'], a2[k]['total_GBps']
            lt = [x['total_GBps'] for x in a2[k]['reps']]
            out[k] = dict(short_ms=a1[k]['min_ms'], long_ms=a2[k]['min_ms'], short=s, long=l, n_long=len(lt),
                          n_long_outside_short=sum(1 for v in lt if v < s['min'] or v > s['max']),
                          change_GBps=l['median'] - s['median'], change_pct=100 * (l['median'] / s['median'] - 1),
                          ranges_overlap=not (l['min'] > s['max'] or l['max'] < s['min']))
    d = {}
    for name, a in (('short', a1), ('long', a2)):
        if 'read_old' in a and 'read_new' in a and a['read_old']['total_GBps']['n'] and a['read_new']['total_GBps']['n']:
            d[name] = a['read_old']['total_GBps']['median'] - a['read_new']['total_GBps']['median']
            o, n = a['read_old']['total_GBps'], a['read_new']['total_GBps']
            d[name + '_range'] = [o['min'] - n['max'], o['max'] - n['min']]
    order = None
    if 'short_range' in d and 'long_range' in d:        # choice C11
        s, l = d['short_range'], d['long_range']
        changed = l[0] > s[1] or l[1] < s[0]
        order = dict(changed=changed, difference_smaller_with_long=abs(d['long']) < abs(d['short']))
    return dict(kernels=out, old_minus_new_read_GBps=d, order_reading=order)


def step_a3(blocks):
    groups = {}
    for b in blocks:
        m = re.match(r'(onebuf|twobuf)-ms(\d+)-(\d+)$', b['tag'])
        if not m: continue
        g = groups.setdefault(f'{m.group(1)}-ms{m.group(2)}', dict(buffers=1 if m.group(1) == 'onebuf' else 2, min_ms=int(m.group(2)), processes=[]))
        rr = [r for r in b['reps'] if r['kernel'] == 'read']          # compare only the rows of the read kernel
        g['processes'].append(dict(tag=b['tag'], reps=[rep_brief(b, r) for r in rr],
                                   total_median_GBps=st.median([r['total_GBps'] for r in rr]) if rr else None,
                                   q_median=st.median([r['q'] for r in rr if r['q'] is not None]) if rr else None,
                                   label=one_label(labels_of(rr)), other_kernels=sorted(set(r['kernel'] for r in b['reps']) - {'read'})))
    for g in groups.values():
        g['total_GBps'] = rng([r['total_GBps'] for p in g['processes'] for r in p['reps']])
        g['q'] = rng([r['q'] for p in g['processes'] for r in p['reps'] if r['q'] is not None])
        g['label'] = one_label([r['label'] for p in g['processes'] for r in p['reps']])
        g['n_below_50_passes'] = sum(r['below_50_passes'] for p in g['processes'] for r in p['reps'])
    cmp = {}
    for ms in sorted(set(g['min_ms'] for g in groups.values())):
        a, b2 = groups.get(f'onebuf-ms{ms}'), groups.get(f'twobuf-ms{ms}')
        if a and b2 and a['total_GBps']['n'] and b2['total_GBps']['n']:
            cmp[str(ms)] = dict(one_label=a['label'], two_label=b2['label'],
                                same_label=(a['label'] == b2['label']) if a['label'] and b2['label'] else None,
                                q_one=a['q'], q_two=b2['q'], total_one=a['total_GBps'], total_two=b2['total_GBps'],
                                total_change_GBps=b2['total_GBps']['median'] - a['total_GBps']['median'],
                                q_ranges_overlap=not (a['q']['min'] > b2['q']['max'] or a['q']['max'] < b2['q']['min']))
    return dict(groups=groups, compare=cmp)


def step_a4(blocks):
    out = {}
    for b in blocks:
        m = re.match(r'(.+)-(\d+\+\d+)$', b['tag'])
        if not m: continue
        k = out.setdefault(m.group(1), dict(binary=b['binary'], counts={}))
        k['counts'][m.group(2)] = dict(reps=[rep_brief(b, r) for r in b['reps']], label=one_label(labels_of(b['reps'])),
                                       q=rng([r['q'] for r in b['reps'] if r['q'] is not None]),
                                       total_GBps=rng([r['total_GBps'] for r in b['reps']]),
                                       n_below_50_passes=sum(r['below_50_passes'] for r in b['reps']))
    for k in out.values():
        k['series'] = {}
        for sname, order in A4_SERIES.items():
            have = [c for c in order if c in k['counts']]
            missing = [c for c in order if c not in k['counts']]
            labels = [k['counts'][c]['label'] for c in have]
            s = dict(counts=have, missing=missing, labels=labels, changes=[], bracket=None, note='')
            if not have or any(l is None for l in labels):
                s['note'] = 'labels not available'
            else:
                s['changes'] = [dict(lower=have[i], upper=have[i + 1], from_label=labels[i], to_label=labels[i + 1])
                                for i in range(len(have) - 1) if labels[i] != labels[i + 1]]
                # a change over a missing count is not a change between two neighbouring tested counts of the plan's grid
                for c in s['changes']:
                    c['counts_missing_between'] = [x for x in order[order.index(c['lower']) + 1:order.index(c['upper'])]]
                # choice C7: the bracket is looked for among the counts with threads on both meshes (64+0 is left out)
                both = [c for c in s['changes'] if not c['lower'].endswith('+0')]
                pure = len(both) == 1 and {both[0]['from_label'], both[0]['to_label']} == {'split', 'uniform'}
                if pure:
                    s['bracket'] = [both[0]['lower'], both[0]['upper']]
                elif not both:
                    two = [l for c, l in zip(have, labels) if not c.endswith('+0')]
                    s['note'] = f'no change of pattern: every count with threads on both meshes is {two[0]}' if two else 'no count with threads on both meshes'
                else:
                    s['note'] = 'more than one change, or a change that is not between split and uniform'
            k['series'][sname] = s
    cmp = {}
    ks = list(out)
    if 'read_old' in out and 'asmread' in out:
        for sname in A4_SERIES:
            a, b2 = out['read_old']['series'][sname], out['asmread']['series'][sname]
            if a['bracket'] and b2['bracket']:
                cmp[sname] = 'equal' if a['bracket'] == b2['bracket'] else 'different'
            else:
                cmp[sname] = 'no bracket for at least one kernel'
    return dict(kernels=out, bracket_compare=cmp, kernel_order=ks)


def limit_check(rates):
    """Choice C9. rates: all rates of one CPU. For each limit: the nearest rates on its two sides, and whether it separates them."""
    out = dict(n=len(rates), min=min(rates), max=max(rates), limits=[], labels_usable=True)
    for L in (LOW_BELOW, HIGH_ABOVE):
        below = [v for v in rates if v < L]; above = [v for v in rates if v >= L]
        e = dict(limit=L, n_below=len(below), n_at_or_above=len(above), nearest_below=max(below) if below else None,
                 nearest_at_or_above=min(above) if above else None, n_within=sum(1 for v in rates if abs(v - L) <= LEVEL_GAP_MIN))
        e['empty_range'] = e['nearest_at_or_above'] - e['nearest_below'] if below and above else None
        e['separates'] = e['empty_range'] is None or e['empty_range'] >= LEVEL_GAP_MIN
        out['labels_usable'] = out['labels_usable'] and e['separates']
        out['limits'].append(e)
    return out


def level_check(a5, a6):
    by = {}
    for p in a5['processes'] + a6['processes']:
        if p.get('cpu') is not None:
            by.setdefault(p['cpu'], []).extend(p['rates_GBps'])
    cpus = {str(c): limit_check(v) for c, v in sorted(by.items()) if v}
    allr = sorted(x for v in by.values() for x in v)
    gaps = sorted(((allr[i + 1] - allr[i], allr[i], allr[i + 1]) for i in range(len(allr) - 1)), reverse=True)[:2]
    for p in a5['processes']:
        ok = cpus.get(str(p['cpu']), {}).get('labels_usable', True)
        p['labels_usable'] = ok
        p['n_below_low_limit'] = sum(1 for v in p['rates_GBps'] if v < LOW_BELOW)
        if not ok:
            p['changes'] = []                      # choice C9: no level change is given where the limit does not separate the rates
    return dict(gap_min_GBps=LEVEL_GAP_MIN, cpus=cpus, largest_empty_ranges=[dict(width=g, low=a, high=b) for g, a, b in gaps])


def a5_changes(levels):
    seq = [(i, l) for i, l in enumerate(levels) if l != 'changing']
    return [dict(at_interval=seq[j][0], from_level=seq[j - 1][1], to_level=seq[j][1]) for j in range(1, len(seq)) if seq[j][1] != seq[j - 1][1]]


def step_a5(blocks):
    procs = []
    for b in blocks:
        m = re.match(r'cpu(\d+)-proc(\d+)$', b['tag'])
        if not m: continue
        rates = [r['total_GBps'] for r in b['reps']]
        lv = [level(x) for x in rates]
        procs.append(dict(tag=b['tag'], cpu=int(m.group(1)), proc=int(m.group(2)), waited_s=b['waited_s'], utc=b['utc'], thp=b['thp'],
                          rates_GBps=rates, levels=lv, n_low=lv.count('low'), n_changing=lv.count('changing'), n_high=lv.count('high'),
                          changes=a5_changes(lv), first_level=lv[0] if lv else None, last_level=lv[-1] if lv else None,
                          rate=rng(rates), n_intervals=len(rates)))
    pairs = []
    for cpu in sorted(set(p['cpu'] for p in procs)):
        p1 = next((p for p in procs if p['cpu'] == cpu and p['proc'] == 1), None)
        p2 = next((p for p in procs if p['cpu'] == cpu and p['proc'] == 2), None)
        pairs.append(dict(cpu=cpu, have_both=bool(p1 and p2), second_waited_s=p2['waited_s'] if p2 else None,
                          second_not_at_once=bool(p2 and p2['waited_s'] > 0),
                          last_level_first=p1['last_level'] if p1 else None, first_level_second=p2['first_level'] if p2 else None))
    return dict(processes=procs, pairs=pairs)


def step_a6(blocks):
    procs = []
    for b in blocks:
        m = re.match(r'(thp|nothp)-(\d+)$', b['tag'])
        if not m: continue
        rates = [r['total_GBps'] for r in b['reps']]
        want = 'nohugepage' if m.group(1) == 'nothp' else 'madvise'
        cpu = b['cpus'] if b['cpus'] and b['cpus'].isdigit() else None
        procs.append(dict(tag=b['tag'], kind=m.group(1), index=int(m.group(2)), cpu=int(cpu) if cpu else None, rates_GBps=rates, levels=[level(x) for x in rates],
                          median_GBps=st.median(rates) if rates else None, thp_line=b['thp'], thp_line_ok=b['thp'] == want,
                          waited_s=b['waited_s']))
    out = dict(processes=procs)
    for kind in ('thp', 'nothp'):
        pp = [p for p in procs if p['kind'] == kind and p['median_GBps'] is not None]
        lv = [l for p in pp for l in p['levels']]
        out[kind] = dict(process_medians=rng([p['median_GBps'] for p in pp]), all_intervals=rng([x for p in pp for x in p['rates_GBps']]),
                         n_low=lv.count('low'), n_changing=lv.count('changing'), n_high=lv.count('high'))
    a, b2 = out['thp']['process_medians'], out['nothp']['process_medians']
    if a['n'] and b2['n']:
        out['nothp_minus_thp_GBps'] = b2['median'] - a['median']
        out['nothp_minus_thp_pct'] = 100 * (b2['median'] / a['median'] - 1)
        out['process_ranges_overlap'] = not (a['min'] > b2['max'] or a['max'] < b2['min'])
    return out


def own_user_of(launches, envs):
    """The account of the run script: the user of the ps process that the script itself starts to write the list of busiest processes."""
    users = [p['user'] for l in launches for p in l['busiest'] if p['comm'] == 'ps']
    for x in envs:
        for l in x.get('busiest_at_start', []):
            p = l.split(None, 2)
            if len(p) == 3 and p[2].strip() == 'ps': users.append(p[1])
    return users[0] if users and len(set(users)) == 1 else None


def load_check(blocks, launches, envs):
    """Readings that can show load from other users: runnable tasks (two readings per launch), logins, waits, busiest processes."""
    own = own_user_of(launches, envs)
    lt = {(l['folder'], l['step'], l['tag']): l for l in launches}
    for b in blocks:
        l = lt.get((b['folder'], b['step'], b['tag']))
        b['runnable_launches_txt'] = l['runnable'] if l else None
    both = [b for b in blocks if b['runnable_launches_txt'] is not None]
    top = {}
    for l in launches:
        for p in l['busiest']:
            key = (p['user'], p['comm'])
            top[key] = max(top.get(key, 0), p['pcpu'])
    other = sorted(((v, u, c) for (u, c), v in top.items() if own is None or u != own), reverse=True)
    mine = sorted(((v, u, c) for (u, c), v in top.items() if own is not None and u == own), reverse=True)
    many = [b for b in blocks if (b['reps'][0]['threads'] if b['reps'] else 0) > 1]
    one = [b for b in blocks if (b['reps'][0]['threads'] if b['reps'] else 0) == 1]
    d = dict(own_user=own, n_launches=len(blocks), n_many_threads=len(many), n_one_thread=len(one),
             runnable_header_max_many=max((b['runnable'] for b in many), default=None),
             runnable_header_max_one=max((b['runnable'] for b in one), default=None),
             runnable_header_max=max((b['runnable'] for b in blocks), default=None),
             runnable_launches_txt_max=max((b['runnable_launches_txt'] for b in both), default=None),
             n_with_launches_txt=len(both), n_runnable_differ=sum(1 for b in both if b['runnable'] != b['runnable_launches_txt']),
             logins_max=max((b['logins'] for b in blocks), default=None), n_waited=sum(1 for b in blocks if b['waited_s'] > 0),
             load1_max=max((b['load1'] for b in blocks), default=None), threads_max=max((r['threads'] for b in blocks for r in b['reps']), default=None),
             busiest_other=[dict(pcpu=v, user=u, comm=c) for v, u, c in other[:3]], busiest_own=[dict(pcpu=v, user=u, comm=c) for v, u, c in mine[:4]])
    rmax = max([x for x in (d['runnable_header_max'], d['runnable_launches_txt_max']) if x is not None], default=None)
    d['runnable_max'] = rmax
    d['no_other_load_seen'] = bool(blocks) and own is not None and rmax is not None and rmax <= 2 and d['logins_max'] == 0 and d['n_waited'] == 0 \
        and (not other or other[0][0] < 1.0)
    return d


def load_summary(blocks, launches):
    """System load per step from the header lines; busiest processes from launches.txt."""
    out = {}
    for s in STEPS[:6]:
        bb = [b for b in blocks if b['step'] == s]
        if not bb: continue
        ll = [l for l in launches if l['step'] == s]
        top = {}
        for l in ll:
            for p in l['busiest']:
                key = (p['user'], p['comm'])
                top[key] = max(top.get(key, 0), p['pcpu'])
        out[s] = dict(launches=len(bb), load1=rng([b['load1'] for b in bb]), runnable=rng([b['runnable'] for b in bb]),
                      runnable_launches_txt=rng([b['runnable_launches_txt'] for b in bb if b.get('runnable_launches_txt') is not None]),
                      waited_s=rng([b['waited_s'] for b in bb]), n_waited=sum(b['waited_s'] > 0 for b in bb),
                      n_waited_20s=sum(b['waited_s'] >= 20 for b in bb), logins=rng([b['logins'] for b in bb]),
                      first_utc=bb[0]['utc'], last_utc=bb[-1]['utc'], launches_txt_entries=len(ll),
                      busiest=[dict(user=u, comm=c, max_pcpu=v) for (u, c), v in sorted(top.items(), key=lambda x: -x[1])[:5]])
    return out


def analyse(folders):
    folders = sorted(folders, key=lambda f: os.path.basename(os.path.normpath(f)))
    all_blocks, launches, envs = [], [], []
    for f in folders:
        name = os.path.basename(os.path.normpath(f))
        envs.append(parse_env(f))
        launches += parse_launches(os.path.join(f, 'launches.txt'), name)
        for s in STEPS[:6]:
            p = os.path.join(f, s + '.csv')
            if os.path.exists(p):
                all_blocks += [finish_block(b) for b in parse_csv(p, name)]
    # choice C4: the last complete block of each (step, tag) is used
    used, not_used, seen = [], [], {}
    for b in all_blocks:
        seen.setdefault((b['step'], b['tag']), []).append(b)
    for (step, tag), bb in seen.items():
        good = [b for b in bb if b['complete']]
        for b in bb:
            if good and b is good[-1]:
                used.append(b)
            else:
                why = '; '.join(b['problems']) if b['problems'] else 'a later complete block of the same step and tag exists'
                not_used.append(dict(folder=b['folder'], step=step, tag=tag, utc=b['utc'], reason=why, killed=b['killed'], failed=b['failed'],
                                     replaced=bool(good), n_blocks_of_tag=len(bb)))
    used.sort(key=lambda b: all_blocks.index(b))
    # q over all repetitions with at least 2 threads, and the decision whether the labels are used.
    # Choice C8: of A3 only the rows of the read kernel count (handoff: "Compare only the rows of the read kernel").
    qall = [dict(step=b['step'], tag=b['tag'], kernel=r['kernel'], rep=r['rep'], threads=r['threads'], q=r['q'], label_rule=r['label_rule'],
                 kname=kname_of(b, r), count=f"{r['mesh0']['n']}+{r['mesh1']['n']}", mesh0_median=r['mesh0']['median'], mesh1_median=r['mesh1']['median'])
            for b in used for r in b['reps'] if r['q'] is not None]
    qrows = [x for x in qall if not (x['step'] == 'A3' and x['kernel'] != 'read')]
    qleft = [x for x in qall if x['step'] == 'A3' and x['kernel'] != 'read']
    qd = two_groups([x['q'] for x in qrows])
    if qd['labels_usable']:
        for b in used:
            for r in b['reps']:
                r['label'] = r['label_rule']
    by = {s: [b for b in used if b['step'] == s] for s in STEPS[:6]}
    low_reps = [dict(step=b['step'], tag=b['tag'], kernel=r['kernel'], kname=kname_of(b, r), rep=r['rep'], passes_per_thread=r['passes_per_thread'], min_ms=b['min_ms'])
                for b in used for r in b['reps'] if r['below_50_passes'] and r['threads'] >= 2]
    a1, a2 = step_a12(by['A1']), step_a12(by['A2'])
    steps_present = [s for s in STEPS[:6] if by[s]] + (['A7'] if any(e['a7'] for e in envs) else [])
    lc_ = load_check(used, launches, envs)
    a5_, a6_ = step_a5(by['A5']), step_a6(by['A6'])
    lvl = level_check(a5_, a6_)
    summary = dict(
        generated_by='analyze_partA.py', folders=[os.path.basename(os.path.normpath(f)) for f in folders],
        limits=dict(q_split_below=Q_SPLIT, q_uniform_above=Q_UNIFORM, low_below_GBps=LOW_BELOW, high_above_GBps=HIGH_ABOVE, min_passes=MIN_PASSES,
                    q_gap_min=GAP_MIN, level_gap_min_GBps=LEVEL_GAP_MIN),
        choices=CHOICES, env=envs, steps_present=steps_present, steps_missing=[s for s in STEPS if s not in steps_present],
        counts=dict(blocks_found=len(all_blocks), blocks_used=len(used), blocks_not_used=len(not_used),
                    killed=sum(1 for b in all_blocks if b['killed']), failed=sum(1 for b in all_blocks if b['failed']),
                    repeated_tags=sum(1 for v in seen.values() if len(v) > 1), repetitions_used=sum(len(b['reps']) for b in used)),
        not_used=not_used, load=load_summary(used, launches), load_check=lc_, level_check=lvl,
        launches=[dict(folder=b['folder'], step=b['step'], tag=b['tag'], utc=b['utc'], waited_s=b['waited_s'], load1=b['load1'], load5=b['load5'],
                       load15=b['load15'], runnable=b['runnable'], runnable_launches_txt=b['runnable_launches_txt'], logins=b['logins'],
                       threads=b['reps'][0]['threads'] if b['reps'] else None) for b in used],
        q=dict(decision=qd, rows=qrows, rows_left_out=qleft, groups=q_groups(qrows)), passes=dict(n_below_50=len(low_reps), below_50=low_reps),
        A1=a1, A2=a2, A1_A2=compare_a1_a2(a1, a2), A3=step_a3(by['A3']), A4=step_a4(by['A4']), A5=a5_, A6=a6_,
        level_counts_8MiB=None,
        thread_rates={s: [dict(tag=b['tag'], kernel=r['kernel'], rep=r['rep'], threads=r['threads_cpu_rate']) for b in by[s] for r in b['reps']]
                      for s in ('A1', 'A2')},
        blocks=[{k: v for k, v in b.items() if k != 'reps'} | dict(n_reps=len(b['reps'])) for b in used],
    )
    lv = [l for p in summary['A5']['processes'] for l in p['levels']] + [l for p in summary['A6']['processes'] for l in p['levels']]
    rates = [x for p in summary['A5']['processes'] + summary['A6']['processes'] for x in p['rates_GBps']]
    summary['level_counts_8MiB'] = dict(n=len(lv), low=lv.count('low'), changing=lv.count('changing'), high=lv.count('high'), rate=rng(rates))
    return summary


def main(argv):
    out = 'partA-summary.json'
    if '--out' in argv:
        i = argv.index('--out'); out = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    if not argv:
        print(__doc__); return 2
    for f in argv:
        if not os.path.isdir(f):
            print(f'not a folder: {f}', file=sys.stderr); return 2
    s = analyse(argv)
    with open(out, 'w') as f:
        json.dump(s, f, indent=1)
    c = s['counts']; d = s['q']['decision']
    print(f"folders: {', '.join(s['folders'])}")
    print(f"blocks found {c['blocks_found']}, used {c['blocks_used']}, not used {c['blocks_not_used']} (killed {c['killed']}, failed {c['failed']}, repeated tags {c['repeated_tags']})")
    print(f"steps present: {' '.join(s['steps_present'])}; missing: {' '.join(s['steps_missing']) or 'none'}")
    print(f"q: n {d['n']}, two groups {d['two_groups']}, labels usable {d['labels_usable']}" + (f" ({d['reason']})" if d['reason'] else ''))
    print(f"repetitions with fewer than {MIN_PASSES} passes per thread (2 or more threads): {s['passes']['n_below_50']}")
    for x in s['not_used']:
        print(f"not used: {x['folder']} {x['step']} {x['tag']}: {x['reason']}")
    print(f'wrote {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
