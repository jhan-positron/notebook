#!/usr/bin/env python3
"""Recount of the numbers that results.md gives and that no page or analysis file holds in that form.
Reads only the raw csv files of the two sessions. Usage: python3 recount_results_md.py > recount_results_md.txt
Rates come from the T rows (bytes / elapsed time), as in analyze_bwx.py (choice A2)."""
import statistics as st, collections, re
R = '/home/jhan/workspace/titan/cache-perf/crb/results/'
N = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/'
LOW, HIGH = 69.0, 70.5


def folders(s):
    return {f.split('-')[0]: f for f in open(N + 'session%d-folders.txt' % s).read().split()}


def procs(path):
    out, cur = [], None
    for l in open(path):
        l = l.rstrip('\n')
        if l.startswith('-- step'):
            p, a = l.split(), l.split(' args ')[1]
            cur = dict(tag=p[p.index('tag') + 1], bin=p[p.index('binary') + 1], args=a, T=[], C=[])
            for k, rx in (('cpu', r'--cpus (\d+)'), ('seq', r'--seq (\S+)'), ('bytes', r'--bytes (\S+)'), ('stop', r'--stop (\S+)'),
                          ('ms', r'--min-ms (\S+)'), ('start', r'--start (\S+)')):
                m = re.search(rx, a)
                cur[k] = m.group(1) if m else None
            cur['seq'] = cur['seq'].split(',')
            out.append(cur)
        elif l.startswith('T,'):
            cur['T'].append(l.split(','))
        elif l.startswith('C,'):
            cur['C'].append(l.split(','))
    return out


def rate(t):
    return float(t[6]) / float(t[7]) / 1e9


def one_thread_rates(p):
    return {(int(t[1]), int(t[2])): rate(t) for t in p['T']}


def d_and_e(p, X, Y, A='asmcopy2', B='asmcopy'):
    """d = median pair value X - Y, e = median pair value A - B (handoff B.10)."""
    seq, r = p['seq'], one_thread_rates(p)
    dv, ev = [], []
    for rd in sorted({k[0] for k in r}):
        for i in range(len(seq) - 1):
            if {seq[i], seq[i + 1]} == {X, Y}:
                dv.append(r[(rd, seq.index(X, i, i + 2))] - r[(rd, seq.index(Y, i, i + 2))])
            if {seq[i], seq[i + 1]} == {A, B}:
                ev.append(r[(rd, seq.index(A, i, i + 2))] - r[(rd, seq.index(B, i, i + 2))])
    return st.median(dv), st.median(ev)


def group(ps, X, Y, label):
    by = collections.defaultdict(list)
    for p in ps:
        by[int(p['cpu'])].append(d_and_e(p, X, Y))
    med = {c: st.median(x[0] for x in v) for c, v in by.items()}
    aa = {c: max(abs(x[1]) for x in v) for c, v in by.items()}
    n = sum(len(v) for v in by.values())
    print('%s: %d processes (%s per CPU), d below 0 in %d, median d per CPU %.2f to %.2f GB/s, A/A spread per CPU %.2f to %.2f GB/s' % (
        label, n, '/'.join(str(len(v)) for v in by.values()), sum(x[0] < 0 for v in by.values() for x in v),
        min(med.values()), max(med.values()), min(aa.values()), max(aa.values())))


for s in (1, 2):
    F = folders(s)
    print('== session s%d' % s)
    print('-- B4: intervals per process by level (low below 69, high above 70.5 GB/s)')
    for p in procs(R + F['B4'] + '/B4.csv'):
        r = [rate(t) for t in p['T']]
        lo, hi = sum(x < LOW for x in r), sum(x > HIGH for x in r)
        print('   %-15s intervals %d low %d high %d between %d lowest %.2f highest %.2f first %.2f' % (p['tag'], len(r), lo, hi, len(r) - lo - hi, min(r), max(r), r[0]))
    r = [rate(t) for p in procs(R + F['C1'] + '/C1.csv') for t in p['T']]
    print('-- C1: %d intervals, highest %.2f GB/s, above 70.5 GB/s: %d' % (len(r), max(r), sum(x > HIGH for x in r)))
    print('-- C2: asm read reference intervals with counters, by their own rate; medians per 64 B line')
    g = collections.defaultdict(list)
    for p in procs(R + F['C2'] + '/C2.csv'):
        tm = {(t[1], t[2]): t for t in p['T']}
        for c in p['C']:
            if c[3] != 'asmread':
                continue
            t = tm[(c[1], c[2])]
            x, lines = rate(t), float(t[6]) / 64
            en, ru, cpu, cy, ins, l1, l2 = [float(v) for v in c[6:13]]
            assert en == ru
            g['high' if x > HIGH else 'low' if x < LOW else 'between'].append((x, ins / lines, l1 / lines, l2 / lines, cy / cpu))
    for k in ('low', 'between', 'high'):
        v = g[k]
        print('   %-7s %3d intervals, %.3f to %.3f GB/s, instructions %.4f, L1 refills %.4f, L2 refills %.4f, clock %.4f GHz' % (
            k, len(v), min(x[0] for x in v), max(x[0] for x in v), *[st.median(x[i] for x in v) for i in (1, 2, 3, 4)]))
    print('-- B1 at 8 MiB, B2, B3: d and A/A spread over all processes of a CPU (description without labels)')
    group([p for p in procs(R + F['B1'] + '/B1.csv') if p['bytes'] == '8M'], 'copy', 'asmcopy', '   B1 8 MiB copy - asmcopy')
    b2 = procs(R + F['B2'] + '/B2.csv')
    for v in ('asmcopy_c', 'asmcopy_c_add', 'asmcopy_c_reg'):
        group([p for p in b2 if v in p['seq']], v, 'asmcopy', '   B2 %s - asmcopy' % v)
    b3 = procs(R + F['B3'] + '/B3.csv')
    for b in ('bwx_o0', 'bwx_o36', 'bwx_o52'):
        group([p for p in b3 if p['bin'] == b], 'copy', 'asmcopy', '   B3 %s copy - asmcopy' % b)
    print('-- B6: old read at 8 MiB by position (sequence positions count from 0)')
    first, second, aa_first_slower, aa_n = collections.defaultdict(list), collections.defaultdict(list), 0, 0
    b6 = procs(R + F['B6'] + '/B6.csv')
    for p in b6:                                                      # per CPU: median over the processes of the process median
        r = one_thread_rates(p)
        rounds = sorted({k[0] for k in r})
        first[int(p['cpu'])].append(st.median(r[(rd, 1)] - r[(rd, 2)] for rd in rounds))      # oldread directly after asmread, minus oldread@1M
        second[int(p['cpu'])].append(st.median(r[(rd, 5)] - r[(rd, 4)] for rd in rounds))     # oldread after oldread@1M, minus oldread@1M
        for rd in rounds:
            for a, b in ((7, 8), (10, 11)):                           # two old read intervals at 8 MiB after an asm read interval
                aa_n += 1
                aa_first_slower += r[(rd, a)] < r[(rd, b)]
    print('   %d processes (%s per CPU); pair value per CPU, old read timed first: %.2f to %.2f GB/s; timed second: %.2f to %.2f GB/s; A/A pairs with the first interval slower: %d of %d' % (
        len(b6), '/'.join(str(sum(int(p['cpu']) == c for p in b6)) for c in sorted(first)),
        min(st.median(v) for v in first.values()), max(st.median(v) for v in first.values()),
        min(st.median(v) for v in second.values()), max(st.median(v) for v in second.values()), aa_first_slower, aa_n))
    print('-- B7: median D of a setting as a share of the median old read total of the same processes (M_hist)')
    res = collections.defaultdict(list)
    for p in procs(R + F['B7'] + '/B7.csv'):
        if len(p['seq']) != 8:
            continue
        iv = collections.defaultdict(lambda: [0.0, 0.0])
        for t in p['T']:
            k = (int(t[1]), int(t[2]))
            iv[k][0] += float(t[6])
            iv[k][1] = max(iv[k][1], float(t[7]))
        m = {k: v[0] / v[1] / 1e9 for k, v in iv.items()}
        ds, olds = [], []
        for rd in sorted({k[0] for k in m}):
            o = [m[(rd, i)] for i, k in enumerate(p['seq']) if k == 'oldread']
            n = [m[(rd, i)] for i, k in enumerate(p['seq']) if k == 'read']
            ds.append(st.mean(o) - st.mean(n))
            olds.append(st.mean(o))
        res[(p['stop'], p['ms'], p['start'])].append((st.mean(ds), st.mean(olds)))
    pct = []
    for k, v in sorted(res.items()):
        D, O = st.median(x[0] for x in v), st.median(x[1] for x in v)
        pct.append(100 * D / O)
        print('   %-22s %d processes, median D %.2f GB/s, median old read total %.2f GB/s, share %.1f %%' % ('/'.join(k), len(v), D, O, 100 * D / O))
    print('   share over the 8 settings: %.1f to %.1f %%' % (min(pct), max(pct)))
    print('-- B10: largest end skew with whole passes')
    best = (0, None)
    for h in ('B10a', 'B10b'):
        for p in procs(R + F[h] + '/B10.csv'):
            if p['stop'] != 'pass':
                continue
            ends = collections.defaultdict(list)
            for t in p['T']:
                ends[(t[1], t[2])].append(float(t[10]))
            for k, v in ends.items():
                if max(v) - min(v) > best[0]:
                    best = (max(v) - min(v), '%s %s interval %s/%s, --min-ms %s' % (h, p['tag'], k[0], k[1], p['ms']))
    print('   %.1f ms in %s' % (best[0] * 1000, best[1]))
    print('-- B7, B10: intervals with whole passes and an end skew above 5 ms (choice A5)')
    for step, hs in (('B7', ('B7',)), ('B10', ('B10a', 'B10b'))):
        n = over = 0
        for h in hs:
            for p in procs(R + F[h] + '/%s.csv' % step):
                if p['stop'] != 'pass':
                    continue
                ends = collections.defaultdict(list)
                for t in p['T']:
                    ends[(t[1], t[2])].append(float(t[10]))
                n += len(ends)
                over += sum(max(v) - min(v) > 0.005 for v in ends.values())
        print('   %s: %d of %d intervals' % (step, over, n))


print('== checks that only a build on CRB could make (DEVIATIONS-bwx.md), from the raw files of both sessions and of the short run')
big = rows = 0
worst_read = (0.0, None)
late = trows = 0
for s in (1, 2):
    F = folders(s)
    for h, f in F.items():
        step = 'B10' if h.startswith('B10') else h
        for l in open(R + f + '/%s.csv' % step):
            if l.startswith('C,'):
                c = l.rstrip().split(',')
                rows += 1
                big += any(v != 'NA' and float(v) > 1e13 for v in c[9:14])
            elif l.startswith('T,'):
                trows += 1
                late += 'late' in l.rstrip().split(',')[12]
            elif l.startswith('# page_read'):
                ms = float(l.split(',')[3].split()[0])
                if ms > worst_read[0]:
                    worst_read = (ms, 's%d %s' % (s, h))
print('   C rows: %d, of them with a count above 1e13 (a value near 2^47 is 1.4e14): %d' % (rows, big))
print('   T rows: %d, of them with the flag late: %d' % (trows, late))
print('   longest page reading of the main thread: %.2f ms (%s)' % worst_read)
cur = None
for l in open(R + 'SHORT-20261113T214338Z/SHORT.csv'):
    if l.startswith('-- step'):
        cur = l.split(' args ')[1].strip()
    elif l.startswith('T,') and '32K' in cur:
        t = l.split(',')
        tb = float(t[6])
    elif l.startswith('C,') and '32K' in cur:
        c = l.rstrip().split(',')
        print('   short run, %s interval %s/%s (%s): %.4f instructions per 256 B' % (c[3], c[1], c[2], cur[:60], float(c[10]) / (tb / 256)))
