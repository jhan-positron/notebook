#!/usr/bin/env python3
"""test_analyze_bwx.py - synthetic tests of analyze_bwx.py. Run: python3 test_analyze_bwx.py

The tests write csv files in the format of handoff B.3 (header line of run_bwx.sh, then the I, T, P and C rows
as bwx prints them), run the analysis on them, and assert the decisions. Each test says WHY the rule matters.
No test uses measured data. All rates are invented.
"""
import json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_bwx as ab  # noqa: E402

B1SEQ = 'asmread,copy,asmcopy,asmread,asmcopy,copy,asmread,asmcopy,asmcopy2,asmread,asmcopy2,asmcopy,asmread'
B6SEQ = 'asmread,oldread,oldread@1M,asmread,oldread@1M,oldread,asmread,oldread,oldread2,asmread,oldread2,oldread,asmread'
B7SEQ = 'oldread,read,asmread,asmread2,asmread2,asmread,read,oldread'
B8SEQ = 'oldread,asmread,asmread2,asmread2,asmread,oldread'
B5SEQ = 'oldread,read,read_sparse,read_nop4,read_nop8,read_nop16,read_nop32,asmread,asmread2'
B10SEQ = 'oldwrite,write,asmwrite,asmwrite2,asmwrite2,asmwrite,write,oldwrite'
ALL = '--threads 120 --cpus 0-63,64-119 --bytes 256M'


def size(s):
    return int(s[:-1]) << {'K': 10, 'M': 20, 'G': 30}[s[-1]]


def cpus_of(s):
    out = []
    for part in s.split(','):
        a, _, b = part.partition('-')
        out += range(int(a), int(b or a) + 1)
    return out


def block(step, tag, args, rate, binary='bwx', elapsed=None, flag=None, page=None, counts=None, tail=None, drop=0, load='0.52 0.40 0.30 1/913'):
    """One process as run_bwx.sh and bwx write it. rate(r, pos, entry, tid, cpu) -> GB/s of the thread."""
    a = args.split()
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    seq, rounds, cpus = opt('--seq').split(','), int(opt('--rounds', '1')), cpus_of(opt('--cpus'))
    nbytes, ms, stop = size(opt('--bytes', '1M')), int(opt('--min-ms')), opt('--stop', 'pass')
    L = ['-- step %s tag %s binary %s waited_s 0 loadavg %s logins 1 utc 12:00:00 args %s' % (step, tag, binary, load, args),
         '# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); synthetic']
    multi, t, kb = len(cpus) > 1, 1.0, nbytes // 1024
    vm = '1000,5,7,90'
    if multi:
        L += ['P,0,-1,%d,a,%d,%d,%s' % (tid, kb, kb, vm) for tid in range(len(cpus))]
    for r in range(rounds):
        for pos, entry in enumerate(seq):
            name = entry.split('@')[0]
            esize = size(entry.split('@')[1]) if '@' in entry else nbytes
            rows = []
            for tid, cpu in enumerate(cpus):
                el = (elapsed(r, pos, entry, tid) if elapsed else None) or ms / 1000.0
                b = int(round(rate(r, pos, entry, tid, cpu) * 1e9 * el))
                ts = t + 0.002
                rows.append((tid, cpu, b, el, t + 0.002 if stop == 'common' else ts, ts, ts + el, flag(r, pos, tid) if flag else '-'))
            pg = page(r, pos) if page else (kb, kb)
            if not multi:
                L.append('P,%d,%d,0,a,%s,%s,%s' % (r, pos, pg[0], pg[1], vm))
            total, longest = sum(x[2] for x in rows), max(x[3] for x in rows)
            L.append('I,%d,%d,%s,%d,%d,%d,%.6f,%.2f' % (r, pos, name, esize, len(cpus), total, longest, total / longest / 1e9))
            for x in rows:
                L.append('T,%d,%d,%s,%d,%d,%d,%.6f,%.6f,%.6f,%.6f,%.3f,%s' % (r, pos, name, x[0], x[1], x[2], x[3], x[4], x[5], x[6],
                                                                         x[2] / esize / (2 if 'copy' in name else 1), x[7]))
            if counts:
                for x in rows:
                    L.append('C,%d,%d,%s,%d,%d,%s' % (r, pos, name, x[0], x[1], counts(r, pos, entry, x[0], x[2])))
            if multi:
                L += ['P,%d,%d,%d,a,%d,%d,%s' % (r, pos, tid, kb, kb, vm) for tid in range(len(cpus))]
                L.append('# page_read,%d,%d,3.210 ms' % (r, pos))
            t += longest + 0.01
    if drop:
        L = L[:-drop]
    if tail:
        L.append(tail)
    return '\n'.join(L) + '\n'


TMP = tempfile.mkdtemp(prefix='bwx-test-')
N = [0]


def analyze(sessions):
    """sessions: {session name: {csv name: [block text, ...]}} -> summary."""
    N[0] += 1
    loaded = {}
    for s, files in sessions.items():
        d = os.path.join(TMP, 'case%d' % N[0], s)
        os.makedirs(d)
        for name, blocks in files.items():
            with open(os.path.join(d, name), 'w') as fh:
                fh.write(''.join(blocks))
        loaded[s] = ab.load_session(s, [d])
    out = ab.analyze(loaded)
    json.dumps(out, default=str)                 # the summary must be writable as json
    for s, res in out['sessions'].items():
        for step, r in res.items():
            ab.text_step(s, step, r)             # and as text
    return out


def near(a, b, tol=0.05):
    return abs(a - b) <= tol


# ------------------------------------------------------------ one thread

def copy_rate(ref=67.5, copy=56.0, asm=58.0, asm2=58.1, ref_by_round=None):
    def f(r, pos, entry, tid, cpu):
        if entry == 'asmread':
            return ref_by_round[r] if ref_by_round else ref
        return {'copy': copy, 'asmcopy': asm, 'asmcopy2': asm2}.get(entry, copy)
    return f


def b1(cpu, i, rate, bytes_='8M', rounds=4, step='B1', seq=B1SEQ, binary='bwx', **kw):
    return block(step, '%s-cpu%d-p%d' % (bytes_, cpu, i), '--threads 1 --cpus %d --bytes %s --seq %s --rounds %d --min-ms 300 --stop pass' % (cpu, bytes_, seq, rounds),
                 rate, binary=binary, **kw)


def test_parse_and_left_out():
    """WHY: a killed or cut process must not give a value, and the report must name it."""
    good = b1(2, 1, copy_rate())
    killed = b1(2, 2, copy_rate(), tail='-- killed tag 8M-cpu2-p2 status 3 utc 12:00:09')
    cut = b1(2, 3, copy_rate(), drop=1)            # the last T row is missing
    s = analyze({'s1': {'B1.csv': [good, killed, cut]}})['sessions']['s1']['B1']
    assert s['n_processes'] == 3 and s['n_used'] == 1, s['n_used']
    assert {x['tag']: x['reason'] for x in s['left_out']}['8M-cpu2-p2'] == 'killed'
    assert 'intervals' in {x['tag']: x['reason'] for x in s['left_out']}['8M-cpu2-p3'] or 'T rows' in str(s['left_out'])
    assert s['load']['loadavg_1min_max'] == 0.52                     # the load of the launches is reported
    p = ab.load_session('x', [os.path.join(TMP, 'case%d' % N[0], 's1')])[0]
    assert len(p.iv) == 52 and len(p.P) == 52 and p.cpu == 2 and p.bytes == 8 << 20 and p.stop == 'pass'
    assert near(p.iv[(0, 1)].rate, 56.0, 0.001) and p.iv[(0, 1)].entry == 'copy'


def test_b1_resolved_per_cpu():
    """WHY: a difference is resolved only per CPU, with the sign kept, against the A/A spread of the same processes."""
    blocks = [b1(c, i, copy_rate(asm2=58.0 + 0.02 * i)) for c in (0, 2, 41, 94) for i in range(1, 5)]
    blocks += [b1(c, i, copy_rate(ref=30.0), bytes_='16M') for c in (0, 2) for i in range(1, 5)]
    g = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']
    low = g['8M']['labels']['low']
    assert low['decision'] == 'resolved' and low['sign'] == -1 and low['n_processes'] == 16
    c = low['per_cpu'][41]
    assert c['n_processes'] == 4 and near(c['median_d'], -2.0, 0.01) and near(c['aa_spread'], 0.08, 0.011)
    # no process was at the high level: "high" is "not observed", with the reason, and is not filled from "low"
    assert g['8M']['labels']['high']['decision'] == 'not observed' and 'Insufficient data' in g['8M']['labels']['high']['note']
    # at 16 MiB no level is defined: the label is "none" and every process gives a value
    assert list(g['16M']['labels']) == ['none'] and g['16M']['labels']['none']['decision'] == 'resolved'


def test_cpus_are_not_pooled():
    """WHY: 6 processes that all say -2 GB/s are enough only if 2 CPUs have 3 each. A pooled count would pass."""
    blocks = [b1(0, i, copy_rate()) for i in range(1, 5)] + [b1(2, i, copy_rate()) for i in range(1, 3)]
    low = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']['8M']['labels']['low']
    assert low['decision'] == 'not observed' and low['per_cpu'][0]['decision'] == 'resolved' and low['per_cpu'][2]['decision'] == 'not observed'
    # opposite signs on two CPUs do not cancel and do not add: the label is not resolved
    blocks = [b1(0, i, copy_rate()) for i in range(1, 5)] + [b1(2, i, copy_rate(copy=60.0)) for i in range(1, 5)]
    low = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']['8M']['labels']['low']
    assert low['decision'] == 'not resolved' and low['per_cpu'][0]['sign'] == -1 and low['per_cpu'][2]['sign'] == 1


def test_one_process_counts_once():
    """WHY: a process with 10 times more intervals must not outvote three processes (plan, rule 4)."""
    blocks = []
    for c in (0, 2):
        blocks += [b1(c, i, copy_rate(copy=58.5)) for i in range(1, 4)]           # d = +0.5 in 3 processes, 8 pairs each
        blocks += [b1(c, 4, copy_rate(copy=53.0), rounds=40)]                     # d = -5 in 1 process, 80 pairs
    low = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']['8M']['labels']['low']
    assert low['per_cpu'][0]['n_processes'] == 4 and low['decision'] == 'not resolved'       # the signs differ
    assert near(low['per_cpu'][0]['median_d'], 0.5, 0.01)        # median over 4 processes; over the 104 pairs it would be -5


def test_changing_process_gives_no_value():
    """WHY: a process whose references change level gives no process value at 8 MiB (plan, rules 4 and 5)."""
    blocks = []
    for c in (0, 2):
        blocks += [b1(c, i, copy_rate()) for i in range(1, 4)]
        blocks += [b1(c, 4, copy_rate(copy=67.0, ref_by_round=[67.5, 67.5, 71.2, 71.2]))]      # d = +9, but the level changes
    g = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']['8M']
    assert g['labels']['low']['decision'] == 'resolved' and g['labels']['low']['sign'] == -1 and g['labels']['low']['per_cpu'][0]['n_processes'] == 3
    odd = [p for p in g['processes'] if not p['used']]
    assert len(odd) == 2 and 'not all at one level' in odd[0]['reason'] and {x['label'] for x in odd[0]['pairs']} == {'low', 'high'}


def b6_rate(ref, old8, old1=None, old2=None):
    def f(r, pos, entry, tid, cpu):
        return {'asmread': ref, 'oldread': old8, 'oldread@1M': old1 if old1 else old8 + 0.01, 'oldread2': old2 if old2 else old8 + 0.02}[entry]
    return f


def b6(cpu, i, rate):
    return block('B6', 'cpu%d-p%d' % (cpu, i), '--threads 1 --cpus %d --seq %s --bytes 8M --rounds 4 --min-ms 300 --stop pass' % (cpu, B6SEQ), rate)


def test_b6_cpu_difference_is_not_a_level_difference():
    """WHY: CPU 2 always low at 67.0 and CPU 41 always high at 68.0 says nothing about the level (handoff B.10)."""
    blocks = [b6(2, i, b6_rate(67.5, 67.0)) for i in range(1, 5)] + [b6(41, i, b6_rate(71.2, 68.0)) for i in range(1, 5)]
    r = analyze({'s1': {'B6.csv': blocks}})['sessions']['s1']['B6']
    assert r['state'][2]['decision'] == 'not observed' and r['state'][41]['decision'] == 'not observed'
    assert 'Insufficient data' in r['state'][2]['note']
    # the second comparison (8 MiB against 1 MiB) uses all processes, label "none": 0.01 GB/s against an A/A of 0.02 is not resolved
    assert r['size']['labels']['none']['decision'] == 'not resolved'
    # both levels on ONE CPU with separate old read rates: resolved on that CPU
    blocks = [b6(2, i, b6_rate(67.5, 67.0)) for i in (1, 2)] + [b6(2, i, b6_rate(71.2, 69.0)) for i in (3, 4)]
    r = analyze({'s1': {'B6.csv': blocks}})['sessions']['s1']['B6']
    assert r['state'][2]['decision'] == 'resolved' and near(r['state'][2]['difference'], -2.0, 0.01)
    # a resolved difference between 8 MiB and 1 MiB needs 2 CPUs, as in B1
    blocks = [b6(c, i, b6_rate(67.5, 67.0, old1=60.0)) for c in (2, 41) for i in range(1, 4)]
    r = analyze({'s1': {'B6.csv': blocks}})['sessions']['s1']['B6']
    assert r['size']['labels']['none']['decision'] == 'resolved' and r['size']['labels']['none']['sign'] == 1


def test_b3_change_against_b1():
    """WHY: H6 is about the CHANGE of the difference when the offset changes, per CPU, against both A/A spreads."""
    base = [b1(c, i, copy_rate()) for c in (0, 2) for i in range(1, 5)]                                         # d = -2
    gone = [b1(c, i, copy_rate(copy=57.9), step='B3', binary='bwx_o52') for c in (0, 2) for i in range(1, 5)]   # d = -0.1
    same = [b1(c, i, copy_rate(copy=55.95), step='B3', binary='bwx_o36') for c in (0, 2) for i in range(1, 5)]  # d = -2.05
    few = [b1(0, i, copy_rate(copy=57.9), step='B3', binary='bwx_o0') for i in range(1, 3)]
    out = analyze({'s1': {'B1.csv': base, 'B3.csv': gone + same + few}})
    ch = out['sessions']['s1']['B3']['change_against_B1']
    assert ch['bwx_o52']['low/cpu0']['decision'] == 'resolved' and near(ch['bwx_o52']['low/cpu0']['change'], -1.9, 0.01)
    assert ch['bwx_o36']['low/cpu2']['decision'] == 'not resolved'      # 0.05 GB/s is inside 0.1 + 0.1
    assert ch['bwx_o0']['low/cpu0']['decision'] == 'not observed'       # 2 processes are not enough
    assert out['hypotheses']['H6 (B3)']['per_session'] == {'s1': 'not observed'}    # bwx_o0 has no CPU with 3 processes
    # without B1 of the same session there is nothing to compare with
    ch = analyze({'s1': {'B3.csv': gone}})['sessions']['s1']['B3']['change_against_B1']
    assert ch['bwx_o52']['low/cpu0']['decision'] == 'not observed' and 'B1' in ch['bwx_o52']['low/cpu0']['note']


def b4(cpu, tag, n_low, n_high, cov, nothp=False):
    kb = 8192
    pg = {'full': (kb, kb), 'none': (kb, 0), 'NA': ('NA', 'NA'), 'partial': (kb, 2048)}[cov]
    return block('B4', '%s-cpu%d' % (tag, cpu), '--threads 1 --cpus %d --bytes 8M --seq asmread --rounds %d --min-ms 300 --stop pass%s' % (cpu, n_low + n_high, ' --no-thp' if nothp else ''),
                 lambda r, pos, e, tid, c: 67.5 if r < n_low else 71.2, page=lambda r, pos: pg)


def test_b4_cases():
    """WHY: H3a is contradicted only by 10 low AND 10 high intervals with the SAME known coverage on one CPU."""
    s = analyze({'s1': {'B4.csv': [b4(2, 'thp-p1', 15, 15, 'full'), b4(2, 'nothp-p1', 30, 0, 'none', True),
                                   b4(41, 'thp-p1', 25, 5, 'full'), b4(41, 'nothp-p1', 12, 18, 'none', True),
                                   b4(94, 'thp-p1', 15, 15, 'NA'), b4(94, 'thp-p2', 15, 15, 'partial')]}})['sessions']['s1']['B4']['per_cpu']
    assert s[2]['cases'] == ['a'] and s[2]['intervals']['low']['none'] == 30
    assert s[41]['cases'] == ['b'] and s[41]['intervals']['high']['full'] == 5       # 5 high intervals are fewer than 10
    assert s[94]['decision'] == 'not observed' and s[94]['intervals']['low']['unknown'] == 15   # NA coverage proves nothing
    assert s[2]['level_changes_low_high'] == 1 and s[2]['level_changes_with_no_sign_of_a_page_change'] == 1
    # "rejected" needs the same CPU in two sessions
    one = {'B4.csv': [b4(2, 'thp-p1', 15, 15, 'full')]}
    other = {'B4.csv': [b4(41, 'thp-p1', 15, 15, 'full')]}
    assert analyze({'s1': one, 's2': one})['hypotheses']['H3a (B4)']['word'] == 'rejected'
    assert 'one session only' in analyze({'s1': one})['hypotheses']['H3a (B4)']['word']


def test_b4_session_flag_does_not_depend_on_the_other_session():
    """WHY: a per-session result must be the result of that session (plan, rule 10), and "not observed" means that the
    event did not occur (rule 11). A case on CPU 2 in one session and on CPU 41 in the other is a failed prediction in
    each session. Before A32 both sessions got the flag "not observed" and the word was "not observed"."""
    one = {'B4.csv': [b4(2, 'thp-p1', 15, 15, 'full')]}
    other = {'B4.csv': [b4(41, 'thp-p1', 15, 15, 'full')]}
    none = {'B4.csv': [b4(2, 'thp-p1', 30, 0, 'full')]}
    h = analyze({'s1': one, 's2': other})['hypotheses']['H3a (B4)']
    assert h['per_session'] == {'s1': 'fail', 's2': 'fail'}
    assert h['word'] == 'not rejected'                                  # no CPU has a case in both sessions (A13)
    assert h['word_without_the_same_cpu_condition'] == 'rejected'       # the other reading is kept next to it, not chosen
    assert h['cpus_with_a_case'] == {'s1': [2], 's2': [41]} and h['cpus_with_a_case_in_every_session'] == []
    h = analyze({'s1': one, 's2': one})['hypotheses']['H3a (B4)']
    assert h['word'] == 'rejected' and h['cpus_with_a_case_in_every_session'] == [2]
    h = analyze({'s1': one, 's2': none})['hypotheses']['H3a (B4)']
    assert h['per_session'] == {'s1': 'fail', 's2': 'not observed'} and h['word'] == 'not rejected'
    h = analyze({'s1': none, 's2': none})['hypotheses']['H3a (B4)']
    assert h['per_session'] == {'s1': 'not observed', 's2': 'not observed'} and h['word'] == 'not observed'


# ------------------------------------------------------------ 120 threads

def split(total_fast=5.0, slow=2.7):
    return lambda cpu: total_fast if cpu < 64 else slow


def read_rate(old=split(), read=2.5, asm=2.5, asm2=2.52):
    """Old read split (mesh 0 fast), the other kernels uniform. Totals: old 471.2, read 300, asmread2 - asmread +2.4 GB/s."""
    def f(r, pos, entry, tid, cpu):
        return old(cpu) if entry == 'oldread' else {'read': read, 'asmread': asm, 'asmread2': asm2}.get(entry, read)
    return f


def b7(setting, i, rate, seq=B7SEQ, rounds=2, step='B7', **kw):
    stop, ms, start = setting.split('/')
    return block(step, '%s-p%d' % (setting.replace('/', '-'), i), '%s --seq %s --rounds %d --stop %s --min-ms %s --start %s' % (ALL, seq, rounds, stop, ms, start), rate, **kw)


def test_b7_setting_and_meshes():
    """WHY: D is one value per process, decided against the A/A spread; mesh 0 is CPUs 0-63 and mesh 1 is CPUs 64-119."""
    S = 'pass/500/common'
    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(asm2=2.5 + 0.005 * i)) for i in range(1, 5)]}})['sessions']['s1']['B7']
    d = r['settings'][S]
    assert d['decision'] == 'resolved' and d['sign'] == 1 and r['reproduction_in_one_process'] == 'reproduced'
    m = d['metrics']
    assert m['M_hist']['n_processes'] == 4 and near(m['M_hist']['median_D'], 171.2) and near(m['M_hist']['aa_spread'], 2.4)
    assert near(m['M_hist_mesh0']['median_D'], 64 * 2.5) and near(m['M_hist_mesh1']['median_D'], 56 * 0.2)      # CPU 63 is mesh 0, CPU 64 is mesh 1
    # 3 processes hold 12 intervals of each kernel, but they are 3 values: not observed
    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate()) for i in range(1, 4)]}})['sessions']['s1']['B7']
    assert r['settings'][S]['decision'] == 'not observed' and '3 processes' in r['settings'][S]['note']
    # a difference inside the A/A spread is not resolved
    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(old=lambda c: 2.51)) for i in range(1, 5)]}})['sessions']['s1']['B7']
    assert r['settings'][S]['decision'] == 'not resolved' and r['reproduction_in_one_process'].startswith('not reproduced')


def test_b7_irregular_intervals():
    """WHY: with the common stop, an interval with a late thread or an end skew above 5 ms is listed and not used."""
    S = 'common/6000/common'
    late = lambda r, pos, tid: 'late' if (r, pos, tid) == (1, 0, 17) else '-'
    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(), flag=late if i == 2 else None) for i in range(1, 5)]}})['sessions']['s1']['B7']
    assert r['settings'][S]['decision'] == 'not observed'             # the process with the late thread gives no D: 3 values
    assert [(x['tag'], x['round'], x['pos'], x['late_threads']) for x in r['irregular_intervals']] == [('common-6000-common-p2', 1, 0, 1)]
    assert 'irregular' in r['settings'][S]['processes_without_value'][0]['reason']
    # the same data without the flag is resolved: the flag alone made the difference
    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate()) for i in range(1, 5)]}})['sessions']['s1']['B7']
    assert r['settings'][S]['decision'] == 'resolved' and r['irregular_intervals'] == []
    # end skew: one thread ends 8 ms after the others
    slow = lambda r, pos, e, tid: 6.008 if (r, pos, tid) == (0, 1, 5) else None
    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(), elapsed=slow if i == 1 else None) for i in range(1, 5)]}})['sessions']['s1']['B7']
    assert r['settings'][S]['decision'] == 'not observed' and r['irregular_intervals'][0]['end_skew_ms'] == 8.0
    # with --stop pass the threads end at pass borders: an end skew of 80 ms is the method, not a defect
    S = 'pass/500/common'
    slow = lambda r, pos, e, tid: 0.58 if tid % 2 else None
    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(), elapsed=slow) for i in range(1, 5)]}})['sessions']['s1']['B7']
    assert r['irregular_intervals'] == [] and r['settings'][S]['decision'] == 'resolved'


def test_b7_m_hist_against_m_sum():
    """WHY: if the two metrics lead to different results for D, the result is "not resolved" and both are reported."""
    S = 'pass/500/common'
    # read: 3.5 GB/s per thread, but thread 0 needs 1.0 s for its last pass. M_sum = 420, M_hist = 211.75. Old read: 360 by both.
    slow = lambda r, pos, e, tid: 1.0 if e == 'read' and tid == 0 else None
    rate = read_rate(old=lambda c: 3.0, read=3.5)
    d = analyze({'s1': {'B7.csv': [b7(S, i, rate, elapsed=slow) for i in range(1, 5)]}})['sessions']['s1']['B7']['settings'][S]
    assert (d['metrics']['M_hist']['decision'], d['metrics']['M_hist']['sign']) == ('resolved', 1) and near(d['metrics']['M_hist']['median_D'], 148.25)
    assert (d['metrics']['M_sum']['decision'], d['metrics']['M_sum']['sign']) == ('resolved', -1) and near(d['metrics']['M_sum']['median_D'], -60.0)
    assert d['decision'] == 'not resolved' and 'M_sum' in d['note']


def test_b7_changes_and_single_kernel():
    """WHY: a factor "contributes" only if D changes by more than both A/A spreads and the two sets of D do not overlap."""
    big, small = read_rate(), read_rate(old=lambda c: 2.7)                 # D = 171.2 and D = 24
    blocks = [b7('pass/500/common', i, big) for i in range(1, 5)] + [b7('common/500/common', i, small) for i in range(1, 5)] + \
             [b7('pass/500/offset', i, big) for i in range(1, 5)] + [b7('common/6000/offset', i, small) for i in range(1, 5)]
    for k in ('oldread', 'read', 'asmread', 'asmread2'):
        blocks += [b7('pass/500/common', i, read_rate(), seq=k, rounds=3).replace('tag pass-500-common', 'tag single-%s' % k) for i in range(1, 5 if k != 'read' else 4)]
    out = analyze({'s1': {'B7.csv': blocks}})
    r = out['sessions']['s1']['B7']
    ch = r['changes']
    assert sorted(ch) == ['start: pass/500/common -> pass/500/offset', 'stop: pass/500/common -> common/500/common']    # only pairs that differ in ONE factor
    c = ch['stop: pass/500/common -> common/500/common']
    assert c['decision'] == 'resolved' and near(c['metrics']['M_hist']['change'], 147.2) and near(c['metrics']['M_hist']['sum_of_aa_spreads'], 4.8)
    assert ch['start: pass/500/common -> pass/500/offset']['decision'] == 'not resolved'
    assert out['hypotheses']['H7a (B7, read)']['per_session'] == {'s1': 'hold'} and out['hypotheses']['H7b (B7, read)']['per_session'] == {'s1': 'fail'}
    assert 'one session only' in out['hypotheses']['H7b (B7, read)']['word']          # one session never rejects
    # one kernel per process: 3 processes of read are not 4
    assert r['single_kernel']['decision'] == 'not observed' and r['single_kernel']['n_processes']['read'] == 3
    blocks.append(b7('pass/500/common', 4, read_rate(), seq='read', rounds=3).replace('tag pass-500-common', 'tag single-read'))
    sk = analyze({'s1': {'B7.csv': blocks}})['sessions']['s1']['B7']['single_kernel']
    assert sk['decision'] == 'resolved' and sk['sign'] == 1 and near(sk['D'], 171.2) and near(sk['aa_value'], 2.4)


def b8(b, i, old_split, asm_split):
    def rate(r, pos, entry, tid, cpu):
        s = old_split if entry == 'oldread' else asm_split
        return (5.0 if cpu < 64 else 2.6) if s else 3.0
    return block('B8', '64+%d-p%d' % (b, i), '--threads %d --cpus 0-63,64-%d --bytes 256M --seq %s --rounds 1 --stop common --min-ms 6000 --start common' % (64 + b, 63 + b, B8SEQ), rate)


def test_b8_brackets():
    """WHY: a bracket needs ordered counts. It is never built from the highest split count alone (handoff B.10)."""
    assert ab.bracket({36: 'split', 40: 'mixed', 44: 'uniform'}) == (36, 44)
    assert ab.bracket({36: 'split', 40: 'untested', 44: 'uniform', 48: 'uniform'}) == (36, 44)
    assert ab.bracket({36: 'split', 40: 'uniform', 44: 'split', 48: 'uniform'}) is None       # a split count above a uniform count
    assert ab.bracket({36: 'uniform', 40: 'uniform'}) is None and ab.bracket({36: 'split', 40: 'split'}) is None and ab.bracket({36: 'mixed'}) is None
    plan = {36: (True, True), 40: (True, False), 44: (False, False)}       # old read changes between 40 and 44, asm read between 36 and 40
    r = analyze({'s1': {'B8.csv': [b8(b, i, *plan[b]) for i in (1, 2) for b in plan]}})['sessions']['s1']['B8']
    assert r['kernels']['oldread']['bracket'] == (40, 44) and r['kernels']['asmread']['bracket'] == (36, 40) and r['H8'] == 'supported'
    assert r['kernels']['oldread']['counts'][36]['label'] == 'split' and near(r['kernels']['oldread']['counts'][36]['q'][0], 0.52, 0.001)
    plan = {36: (True, True), 40: (False, True), 44: (False, False)}
    two = {'B8.csv': [b8(b, i, *plan[b]) for i in (1, 2) for b in plan]}
    out = analyze({'s1': two, 's2': two})
    assert out['sessions']['s1']['B8']['H8'] == 'contradicted' and out['hypotheses']['H8 (B8)']['word'] == 'rejected (contradicted)'
    # one process split and one uniform at a count: the count is "mixed", and equal brackets are not resolved
    blocks = [b8(36, i, True, True) for i in (1, 2)] + [b8(40, 1, True, True), b8(40, 2, False, False)] + [b8(44, i, False, False) for i in (1, 2)]
    r = analyze({'s1': {'B8.csv': blocks}})['sessions']['s1']['B8']
    assert r['kernels']['oldread']['counts'][40]['label'] == 'mixed' and r['kernels']['oldread']['bracket'] == (36, 44) and r['H8'] == 'not resolved at this grid'
    # old read never uniform: no bracket and no decision
    r = analyze({'s1': {'B8.csv': [b8(b, i, True, b < 44) for i in (1, 2) for b in (36, 40, 44)]}})['sessions']['s1']['B8']
    assert r['kernels']['oldread']['bracket'] is None and r['H8'] == 'not resolved'


def b5(i, sparse_split, sparse_rate=None):
    def rate(r, pos, entry, tid, cpu):
        if entry == 'oldread':
            return 5.0 if cpu < 64 else 2.7
        if entry == 'read_sparse':
            return (sparse_rate or 4.97 if cpu < 64 else 2.7) if sparse_split else 2.5
        return 2.525 if entry == 'asmread2' else 2.5
    seq = B5SEQ if i % 2 else ','.join(reversed(B5SEQ.split(',')))
    return block('B5', 'b5-%s-p%d' % ('fwd' if i % 2 else 'rev', i), '%s --seq %s --rounds 1 --stop common --min-ms 6000 --start offset' % (ALL, seq), rate)


def test_b5():
    """WHY: a variant "shows the pattern and total of old read" only if BOTH hold: same pattern label in the same
    process, and a total difference that is not resolved against the A/A spread."""
    yes = {'B5.csv': [b5(i, True) for i in range(1, 5)]}
    out = analyze({'s1': yes, 's2': yes})
    v = out['sessions']['s1']['B5']['variants']
    assert v['read_sparse']['shows_pattern_and_total_of_oldread'] == 'yes'            # split, and 1.92 GB/s below old read against an A/A of 3
    assert v['read_nop4']['shows_pattern_and_total_of_oldread'] == 'no' and v['read_nop4']['same_pattern'] is False
    assert out['hypotheses']['B5 statement "vector adds are needed for the split pattern of old read"']['word'] == 'rejected'
    # same pattern but a resolved lower total: not "the pattern and total of old read"
    v = analyze({'s1': {'B5.csv': [b5(i, True, sparse_rate=4.5) for i in range(1, 5)]}})['sessions']['s1']['B5']['variants']
    assert v['read_sparse']['same_pattern'] is True and v['read_sparse']['shows_pattern_and_total_of_oldread'] == 'no'
    out = analyze({'s1': {'B5.csv': [b5(i, False) for i in range(1, 5)]}, 's2': yes})
    assert out['hypotheses']['B5 statement "vector adds are needed for the split pattern of old read"']['word'] == 'not rejected'
    v = analyze({'s1': {'B5.csv': [b5(i, True) for i in range(1, 4)]}})['sessions']['s1']['B5']['variants']
    assert v['read_sparse']['shows_pattern_and_total_of_oldread'] == 'not observed'     # 3 processes


def b9(i, two, is_split):
    return block('B9', '%s-p%d' % ('twobuf' if two else 'onebuf', i), '%s --seq oldread --rounds 3 --stop common --min-ms 6000 --start common%s' % (ALL, ' --two-buffers' if two else ''),
                 lambda r, pos, e, tid, cpu: ((5.0 if cpu < 64 else 2.7) if is_split else 3.0) + 0.001 * i)


def test_b9():
    """WHY: H9a is rejected only if the pattern is the same with one and with two buffers, in both sessions."""
    pred = {'B9.csv': [b9(i, two, not two) for i in (1, 2, 3) for two in (False, True)]}
    same = {'B9.csv': [b9(i, two, True) for i in (1, 2, 3) for two in (False, True)]}
    r = analyze({'s1': pred})['sessions']['s1']['B9']
    assert r['pattern_result'] == 'pattern as H9a predicts' and r['total']['decision'] == 'resolved' and near(r['total']['aa_value'], 0.24, 0.01)
    out = analyze({'s1': same, 's2': same})
    assert out['sessions']['s1']['B9']['pattern_result'] == 'same pattern' and out['sessions']['s1']['B9']['total']['decision'] == 'not resolved'
    assert out['hypotheses']['H9a (B9)']['word'] == 'rejected'
    assert analyze({'s1': same, 's2': pred})['hypotheses']['H9a (B9)']['word'] == 'not rejected'


def test_label_entries_carry_the_word_without_labels():
    """WHY: the user decided on 2026-11-13 that the labels split and uniform are not used, and that a rule which needs a
    label gives "not resolved" (decisions.md, item 2). The label rule of B.10 is still computed. So every entry that rests
    on a label must carry the word without labels next to it, and the text output must say so at the entry. Without
    this, hypotheses.txt presents "H9a: rejected" as a decision (A33)."""
    same = {'B9.csv': [b9(i, two, True) for i in (1, 2, 3) for two in (False, True)],
            'B8.csv': [b8(b, i, b < 40, b < 24) for b in (16, 24, 32, 40, 48, 56) for i in (1, 2)],
            'B5.csv': [b5(i, True) for i in range(1, 5)]}
    out = analyze({'s1': same, 's2': same})
    h = out['hypotheses']
    assert h['H9a (B9)']['word'] == 'rejected' and h['H9a (B9)']['word_without_labels'] == 'not resolved'
    assert h['H8 (B8)']['word_without_labels'] == 'not resolved'
    name = 'B5 statement "vector adds are needed for the split pattern of old read"'
    # read_sparse equal to old read in pattern and total: the label rule rejects, and without labels nothing decides.
    assert h[name]['word'] == 'rejected' and h[name]['word_without_labels'] == 'not resolved'
    # A resolved lower total of read_sparse decides without any label.
    low = {'B5.csv': [b5(i, False) for i in range(1, 5)]}
    h2 = analyze({'s1': low, 's2': low})['hypotheses'][name]
    assert h2['word_without_labels'] == 'not rejected' and h2['per_session_without_labels'] == {'s1': 'hold', 's2': 'hold'}
    # An entry that uses no label carries no such word.
    assert all('word_without_labels' not in v for k, v in h.items() if not k.startswith(('H8', 'H9a', 'B5 statement')))
    t = ab.text_hypotheses(out)
    assert t.count('LABELS NOT USED') == 3 and 'Without labels the word is "not resolved"' in t
    assert 'NOT USED' in ab.text_step('s1', 'B9', out['sessions']['s1']['B9']) and any('NOT USED' in x for x in out['limits'])


def b10(setting, i, kind):
    """kind 'levels': write has one interval (round 1, pos 6) in which mesh 1 is faster; old write has one in which
    both meshes are faster. kind 'flat': every interval is the same. kind 'aa-mesh': the A/A copies differ per mesh."""
    def rate(r, pos, entry, tid, cpu):
        hi = kind != 'flat' and r == 1 and pos in (6, 7)
        if entry == 'write':
            return 1.5 if hi and cpu >= 64 and kind == 'levels' else 1.01 if hi and cpu >= 64 else 1.0
        if entry == 'oldwrite':
            return 1.3 if hi and kind == 'levels' else 1.0
        if kind == 'aa-mesh' and entry == 'asmwrite2':
            return 1.05 if cpu < 64 else 0.942857142857                 # mesh 0 +3.2 GB/s, mesh 1 -3.2 GB/s, total equal
        return 1.0 + (0.002 if entry == 'asmwrite2' and r == 1 else 0.0)
    return b7(setting, i, rate, seq=B10SEQ, step='B10')


def test_b10():
    """WHY: the spread is one value per process; H11 judges each mesh with the control of ITS OWN rate."""
    A, B = 'pass/500/common', 'common/15000/common'
    files = {'B10a-x.csv': [b10(A, i, 'levels') for i in (1, 2)] + [b10(B, i, 'flat') for i in (1, 2)],
             'B10b-x.csv': [b10(A, i, 'levels') for i in (3, 4)] + [b10(B, i, 'flat') for i in (3, 4)]}       # the two halves of one session
    out = analyze({'s1': files, 's2': files})
    r = out['sessions']['s1']['B10']
    a = r['settings'][A]
    assert a['n_processes'] == 4 and near(a['control_total'], 0.24, 0.01) and near(a['control_spread'], 0.24, 0.01)
    assert near(a['kernels']['write']['median_spread'], 28.0) and a['kernels']['write']['H11'] == 'supported'           # only mesh 1 rose
    assert near(a['kernels']['write']['high_minus_low'][0]['mesh1'], 28.0) and near(a['kernels']['write']['high_minus_low'][0]['mesh0'], 0.0)
    assert a['kernels']['oldwrite']['H11'] == 'contradicted'                                                            # both meshes rose
    assert r['settings'][B]['kernels']['write']['H11'] == 'not observed'                                                # no interval with a higher total
    assert r['spread_changes'] == {}                         # A and B differ in two factors: no change is computed between them
    assert out['hypotheses']['H11 (B10, %s, write)' % A]['word'] == 'not rejected (supported)'
    assert out['hypotheses']['H11 (B10, %s, oldwrite)' % A]['word'] == 'rejected (contradicted)'
    # settings that differ in one factor: the spread of write changes from 28 to 0 GB/s
    C = 'common/500/common'
    r = analyze({'s1': {'B10.csv': [b10(A, i, 'levels') for i in range(1, 5)] + [b10(C, i, 'flat') for i in range(1, 5)]}})['sessions']['s1']['B10']
    c = r['spread_changes']['write stop: %s -> %s' % (A, C)]
    assert c['decision'] == 'resolved' and near(c['change_of_spread'], 28.0) and c['n_first'] == 4
    assert r['spread_changes']['asmwrite stop: %s -> %s' % (A, C)]['decision'] == 'not resolved'
    # A/A copies with equal totals and opposite mesh rates: the control of each mesh is 3.2 GB/s. A rise of 0.56 GB/s on mesh 1 is not support.
    r = analyze({'s1': {'B10.csv': [b10(A, i, 'aa-mesh') for i in range(1, 5)]}})['sessions']['s1']['B10']['settings'][A]
    assert r['control_total'] < 0.01 and near(r['control_mesh0'], 3.2) and near(r['control_mesh1'], 3.2)
    assert r['kernels']['write']['H11'] == 'not resolved'
    # 3 processes: no change of the spread can be decided
    r = analyze({'s1': {'B10.csv': [b10(A, i, 'levels') for i in range(1, 4)] + [b10(C, i, 'flat') for i in range(1, 5)]}})['sessions']['s1']['B10']
    assert r['spread_changes']['write stop: %s -> %s' % (A, C)]['decision'] == 'not observed'


# ------------------------------------------------------------ counters, SHORT, sessions, files

def test_counters():
    """WHY: a C row whose running time is below its enabled time was multiplexed and is not used (handoff B.8)."""
    def counts(r, pos, entry, tid, nbytes):
        run = 290000000 if r == 1 else 300000000
        return '300000000,%d,299000000,%d,%d,%d,NA,%d' % (run, 897000000, nbytes * 11 // 256, nbytes // 64, nbytes // 640)
    blk = block('C1', 'cpu2-p1', '--threads 1 --cpus 2 --bytes 8M --seq asmread --rounds 4 --min-ms 300 --stop pass --count', lambda *a: 67.5, counts=counts)
    r = analyze({'s1': {'C1.csv': [blk]}})['sessions']['s1']['C1']
    assert r['rows_C'] == 4 and r['rows_C_not_used'] == 1
    g = r['groups'][0]
    assert g['level'] == 'low' and g['n_rows'] == 3 and near(g['median_instructions_per_line'], 2.75, 0.001) and near(g['median_clock_GHz'], 3.0, 0.001)
    assert g['not_supported'] == ['l2d_refill'] and near(g['median_ll_read_miss_per_line'], 0.1, 0.001)


def test_short_step_gives_no_decision():
    """WHY: the short run checks the output of bwx; nothing in it may look like a result."""
    blk = block('SHORT', 'b4-nothp', '--threads 1 --cpus 2 --min-ms 100 --stop pass --bytes 8M --seq asmread --rounds 5 --no-thp', lambda *a: 67.5, page=lambda r, pos: ('NA', 'NA'))
    out = analyze({'s1': {'SHORT.csv': [blk]}})
    r = out['sessions']['s1']['SHORT']
    assert r['processes'][0]['complete'] and r['processes'][0]['P_rows_NA'] == 5 and r['page_rows_NA'] == 5 and out['hypotheses'] == {}


def test_two_sessions_words():
    """WHY: "rejected" needs the failed prediction in both sessions (plan, rule 11)."""
    assert ab.two_sessions({'s1': 'fail', 's2': 'fail'}) == 'rejected'
    assert ab.two_sessions({'s1': 'fail', 's2': 'hold'}) == 'not rejected'
    assert ab.two_sessions({'s1': 'fail', 's2': 'not observed'}) == 'not rejected'
    assert ab.two_sessions({'s1': 'not observed', 's2': 'not observed'}) == 'not observed'
    assert 'one session only' in ab.two_sessions({'s1': 'fail'})
    # H4: resolved with the same sign in both sessions is the failure of its prediction; opposite signs are not
    neg = {'B1.csv': [b1(c, i, copy_rate()) for c in (0, 2) for i in range(1, 5)]}
    pos = {'B1.csv': [b1(c, i, copy_rate(copy=60.0)) for c in (0, 2) for i in range(1, 5)]}
    assert analyze({'s1': neg, 's2': neg})['hypotheses']['H4 (B1, 8 MiB, label low)']['word'] == 'rejected'
    assert analyze({'s1': neg, 's2': pos})['hypotheses']['H4 (B1, 8 MiB, label low)']['word'] == 'not rejected'
    assert analyze({'s1': neg, 's2': neg})['hypotheses']['H4 (B1, 8 MiB, label high)']['word'] == 'not observed'


def test_command_line_writes_json_and_tables():
    """WHY: the lead needs a json summary and a text table per step, each decision with its processes and A/A spread."""
    d = os.path.join(TMP, 'cli', 'B1-20261114T000000Z')
    os.makedirs(d)
    with open(os.path.join(d, 'B1.csv'), 'w') as fh:
        fh.write(''.join(b1(c, i, copy_rate()) for c in (0, 2) for i in range(1, 5)))
    out = os.path.join(TMP, 'cli-out')
    stdout, sys.stdout = sys.stdout, open(os.devnull, 'w')
    try:
        assert ab.main(['--session', 's1', d, '--out', out]) == 0
    finally:
        sys.stdout.close()
        sys.stdout = stdout
    s = json.load(open(os.path.join(out, 'summary.json')))
    assert s['sessions']['s1']['B1']['groups']['8M']['labels']['low']['decision'] == 'resolved'
    t = open(os.path.join(out, 'B1.txt')).read()
    assert 'A/A spread GB/s' in t and 'processes' in t and 'system load' in t and 'resolved (-)' in t
    assert 'H4' in open(os.path.join(out, 'hypotheses.txt')).read()

# ------------------------------------------------------------ preconditions and metric disagreements (review of 2026-11-13)

H7A, H7B, H6, B5STMT = 'H7a (B7, read)', 'H7b (B7, read)', 'H6 (B3)', 'B5 statement "vector adds are needed for the split pattern of old read"'


def test_h7_needs_the_reproduction():
    """WHY: the plan assigns no cause when B7 reproduces no difference. "No factor changed D" must then not be
    the word "rejected" for H7a and H7b: there was no D that a factor could change."""
    flat = lambda i: (lambda r, pos, e, tid, cpu: 3.0 + (0.0005 * i if e == 'asmread2' else 0))
    sets = ['%s/%s/%s' % (a, b, c) for a in ('pass', 'common') for b in ('500', '6000') for c in ('common', 'offset')]
    files = {'B7.csv': [b7(s, i, flat(i)) for i in range(1, 5) for s in sets]}
    out = analyze({'s1': files, 's2': files})
    r = out['sessions']['s1']['B7']
    assert r['reproduced_in_either_way'] is False and all(c['decision'] == 'not resolved' for c in r['changes'].values())
    for h in (H7A, H7B):
        assert out['hypotheses'][h]['per_session'] == {'s1': 'not observed', 's2': 'not observed'} and out['hypotheses'][h]['word'] == 'not observed'
    # with the reproduction, the same "no resolved change" in two sessions IS the failure of the prediction
    files = {'B7.csv': [b7(s, i, read_rate()) for i in range(1, 5) for s in sets]}
    out = analyze({'s1': files, 's2': files})
    assert out['sessions']['s1']['B7']['reproduced_in_either_way'] is True
    assert out['hypotheses'][H7A]['word'] == 'rejected' and out['hypotheses'][H7B]['word'] == 'rejected'


def test_h7_metric_disagreement_is_not_a_failure():
    """WHY: a change of D that M_hist resolves and M_sum does not is "not resolved" (handoff B.10). It is not
    evidence that the factor has no effect, so it must not count as the failed prediction of H7b."""
    # offset start: in the read intervals thread 0 needs 1.0 s for its last pass. M_sum of read is unchanged, M_hist halves.
    slow = lambda r, pos, e, tid: 1.0 if e == 'read' and tid == 0 else None
    files = {'B7.csv': [b7('pass/500/common', i, read_rate()) for i in range(1, 5)] +
                       [b7('pass/500/offset', i, read_rate(), elapsed=slow) for i in range(1, 5)]}
    out = analyze({'s1': files, 's2': files})
    c = out['sessions']['s1']['B7']['changes']['start: pass/500/common -> pass/500/offset']
    assert c['metrics']['M_hist']['decision'] == 'resolved' and c['metrics']['M_sum']['decision'] == 'not resolved'
    assert c['decision'] == 'not resolved' and c['metrics_disagree'] is True and 'M_sum' in c['note']
    assert out['hypotheses'][H7B]['per_session'] == {'s1': 'not resolved', 's2': 'not resolved'} and out['hypotheses'][H7B]['word'] == 'not rejected'


def test_h6_needs_a_resolved_b1():
    """WHY: the plan runs B3 only after a resolved difference in B1. With copy = asmcopy in B1 and in all builds,
    "the offset changed nothing" must not reject H6 (H5 has the same guard)."""
    def sess(copy):
        cr = lambda: copy_rate(copy=copy)
        return {'B1.csv': [b1(c, i, cr()) for c in (0, 2, 41, 94) for i in range(1, 5)],
                'B3.csv': [b1(c, i, cr(), step='B3', binary=b) for b in ('bwx_o0', 'bwx_o36', 'bwx_o52') for c in (0, 2, 41, 94) for i in range(1, 5)]}
    out = analyze({'s1': sess(58.0), 's2': sess(58.0)})
    assert out['sessions']['s1']['B1']['groups']['8M']['labels']['low']['decision'] == 'not resolved'
    assert out['hypotheses'][H6]['per_session'] == {'s1': 'not observed', 's2': 'not observed'} and out['hypotheses'][H6]['word'] == 'not observed'
    # with a resolved difference in B1 that no build changes, the prediction of H6 fails in both sessions
    out = analyze({'s1': sess(56.0), 's2': sess(56.0)})
    assert out['sessions']['s1']['B1']['groups']['8M']['labels']['low']['decision'] == 'resolved'
    assert out['hypotheses'][H6]['word'] == 'rejected'


def test_b5_metric_disagreement_is_not_yes():
    """WHY: "shows the pattern and total of old read" rejects the B5 statement. If M_hist resolves a total
    difference and M_sum does not, the total of old read is not shown: the variant must not get "yes"."""
    def blk(i):
        seq = B5SEQ if i % 2 else ','.join(reversed(B5SEQ.split(',')))
        rate = lambda r, pos, e, tid, cpu: (5.0 if cpu < 64 else 2.7) + (0.004 * i if e == 'asmread2' else 0)
        late_pass = lambda r, pos, e, tid: 0.75 if e == 'oldread' and tid == 0 else None      # whole passes: one thread ends 0.25 s later
        return block('B5', 'b5-p%d' % i, '%s --seq %s --rounds 1 --stop pass --min-ms 500 --start common' % (ALL, seq), rate, elapsed=late_pass)
    files = {'B5.csv': [blk(i) for i in range(1, 5)]}
    out = analyze({'s1': files, 's2': files})
    v = out['sessions']['s1']['B5']['variants']['read_sparse']
    m = v['total_difference']['metrics']
    assert m['M_hist']['decision'] == 'resolved' and m['M_sum']['decision'] == 'not resolved' and v['same_pattern'] is True
    assert v['shows_pattern_and_total_of_oldread'] == 'not resolved' and 'M_hist gives' in v['note']
    assert out['hypotheses'][B5STMT]['per_session'] == {'s1': 'not resolved', 's2': 'not resolved'} and out['hypotheses'][B5STMT]['word'] == 'not rejected'


def test_b7_single_kernel_uses_both_metrics():
    """WHY: handoff B.10 makes M_hist the decision metric "for the reproduction condition" too, and a different
    word under M_sum gives "not resolved". With whole passes one late thread changes M_hist and not M_sum."""
    blocks = []
    for k in ('oldread', 'read', 'asmread', 'asmread2'):
        for i in range(1, 5):
            rate = lambda r, pos, e, tid, cpu, i=i: 3.0 + 0.0001 * i
            el = (lambda r, pos, e, tid: 0.75 if tid == 0 else None) if k == 'read' else None
            blocks.append(block('B7', 'single-%s-p%d' % (k, i), '%s --seq %s --rounds 3 --stop pass --min-ms 500 --start common' % (ALL, k), rate, elapsed=el))
    r = analyze({'s1': {'B7.csv': blocks}})['sessions']['s1']['B7']
    sk = r['single_kernel']
    assert sk['metrics']['M_hist']['decision'] == 'resolved' and sk['metrics']['M_sum']['decision'] == 'not resolved'
    assert sk['decision'] == 'not resolved' and sk['sign'] is None and 'M_sum' in sk['note'] and near(sk['D'], 119.0, 0.1)
    assert r['reproduced_in_either_way'] is False


def test_counter_tables_count_processes_and_keep_sequences_apart():
    """WHY: the column "processes" of every table is the number of processes (plan, rule 4: one value per process),
    and the rows of the B7 sequence and of the B5 sequence of C3 are different experiments."""
    counts = lambda r, pos, entry, tid, nbytes: '300000000,300000000,299000000,%d,%d,%d,%d,%d' % (897000000, nbytes * 11 // 256, nbytes // 64, 0, nbytes // 640)
    one = [block('C1', 'cpu2-p%d' % i, '--threads 1 --cpus 2 --bytes 32K --seq asmread --rounds 3 --min-ms 100 --stop pass --count', lambda *a: 60.0, counts=counts) for i in (1, 2)]
    r = analyze({'s1': {'C1.csv': one}})['sessions']['s1']['C1']
    assert len(r['groups']) == 1 and r['groups'][0]['n_rows'] == 6 and r['groups'][0]['n_processes'] == 2
    assert r['rows'][0]['n_processes'] == 2 and '6 C rows' in r['rows'][0]['note']
    opts = '--rounds 1 --stop common --min-ms 6000 --start common --count'
    c3 = [block('C3', 'common-6000-common-p1', '%s --seq %s %s' % (ALL, B7SEQ, opts), lambda *a: 2.5, counts=counts),
          block('C3', 'b5-fwd-p1', '%s --seq %s %s' % (ALL, B5SEQ, opts), lambda *a: 2.5, counts=counts)]
    g = analyze({'s1': {'C3.csv': c3}})['sessions']['s1']['C3']['groups']
    old = {x['group']: (x['n_rows'], x['n_processes']) for x in g if x['entry'] == 'oldread' and x['mesh'] == 'mesh0'}
    assert old == {'common/6000/common B7 sequence': (128, 1), 'common/6000/common B5 sequence': (64, 1)}, old


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    try:
        for t in tests:
            t()
            print('ok   %s' % t.__name__)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    print('test_analyze_bwx.py: all %d tests passed' % len(tests))


if __name__ == '__main__':
    main()
