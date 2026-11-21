#!/usr/bin/env python3
"""test_q1.py [--keep DIR] - tests of make_q1_html.py. Run: python3 test_q1.py

The tests write result folders in the format of run_bwx.sh and bwx (handoff B.3) with INVENTED rates, build the
page from them and assert the computed values and the words. Each test says WHY its rule matters.
The row writer is the one of test_analyze_bwx.py (function block), so the format is the format that the tests of
the analysis already use. The last test runs on the real session 1 folders if they exist on this machine.
With --keep DIR the synthetic folders and pages stay in DIR.
"""
import html, json, os, re, shutil, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_q1_html as M                 # noqa: E402  (puts the folder of analyze_bwx.py on the path)
import test_analyze_bwx as T             # noqa: E402  block(), b1(), b4(), b6(), copy_rate(), b6_rate()

BANNER = 'SYNTHETIC TEST DATA. Every rate on this page is invented by test_q1.py. It is not a measurement.'
KEEP = sys.argv[sys.argv.index('--keep') + 1] if '--keep' in sys.argv else None
ROOT = KEEP or tempfile.mkdtemp(prefix='q1-test-')
N = [0]


def folder(session, step, blocks, load='0.52 0.40 0.30 1/913', end='2026-01-01T00:10:00Z', start='2026-01-01T00:00:00Z', busy=''):
    """One result folder of one step: <step>.csv, env.txt, launches.txt, stderr.txt."""
    N[0] += 1
    d = os.path.join(ROOT, 'case%03d' % N[0], session, '%s-20260101T0000%02dZ' % (step, N[0] % 60))
    os.makedirs(d)
    with open(os.path.join(d, step + '.csv'), 'w') as fh:
        fh.write(''.join(blocks))
    with open(os.path.join(d, 'env.txt'), 'w') as fh:
        fh.write('## host=test utc=%s loadavg=%s 123 logins=0 step=%s steps=%s\n## end utc=%s loadavg=0.40 0.40 0.30 1/913 456\n' % (start, load, step, step, end))
    with open(os.path.join(d, 'launches.txt'), 'w') as fh:
        for b in blocks:
            tag = b.split()[4]
            fh.write('== %s.csv %s utc 12:00:00 loadavg %s logins 1\n%%CPU USER     COMMAND\n 100 tester   ps\n%s 0.3 root     kworker/1\n' % (step, tag, load, busy))
    open(os.path.join(d, 'stderr.txt'), 'w').close()
    return d


def page(spec):
    """spec: {session: [folders]} -> (D, html text)."""
    D, text = M.make([(s, f) for s, f in spec.items()], BANNER)
    N[0] += 1
    with open(os.path.join(ROOT, 'page%03d.html' % N[0]), 'w') as fh:
        fh.write(text)
    return D, text


def word(D, h):
    rows = [r for r in D['hyp'] if r['h'] == h]
    assert len(rows) == 1, (h, [r['h'] for r in D['hyp']])
    return rows[0]


def visible(text):
    """The text a reader sees: no style block, no tags, entities decoded."""
    t = re.sub(r'<style>.*?</style>', ' ', text, flags=re.S)
    t = re.sub(r'<title>.*?</title>', ' ', t, flags=re.S)       # svg tooltips and the page title
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t)))


def near(a, b, tol=0.02):
    return abs(a - b) <= tol


# ------------------------------------------------------------ synthetic sessions

def strong_session(name):
    """A session in which every bounded prediction that can fail does fail, with stable low references."""
    b1 = [T.b1(c, i, T.copy_rate()) for c in (0, 2) for i in range(1, 5)]                       # d = -2, e = +0.1, references 67.5 (low)
    b4 = [T.b4(2, 'thp-p1', 15, 15, 'full')]                                                    # case (a) on CPU 2
    b6 = [T.b6(c, i, T.b6_rate(67.5, 67.0, old1=60.0)) for c in (2, 41) for i in range(1, 4)]   # 8 MiB minus 1 MiB = +7
    return [folder(name, 'B1', b1), folder(name, 'B4', b4), folder(name, 'B6', b6)]


def test_one_session_never_gives_rejected():
    """WHY: rule 11 of the plan defines "rejected" as a prediction that failed in BOTH sessions. A page built from one
    session must not use the word for any hypothesis, however clear the data are, and must say why."""
    D, text = page({'s1': strong_session('s1')})
    assert all(r['word'] != 'rejected' for r in D['hyp'])
    assert word(D, 'H3a')['word'] == 'not rejected' and 'The bounded prediction failed' in word(D, 'H3a')['per']['s1']['result']
    assert word(D, 'H4, low intervals')['word'] == 'not rejected' and word(D, 'H1')['word'] == 'not rejected'
    assert 'no row of this table can say "rejected"' in visible(text)
    assert 'one session cannot give "rejected"' in M.short_version(D)
    assert '<b>rejected</b>' not in text
    # the same data in two sessions: now the word is allowed, and the one-session sentence is gone
    D2, text2 = page({'s1': strong_session('s1'), 's2': strong_session('s2')})
    assert word(D2, 'H3a')['word'] == 'rejected' and word(D2, 'H4, low intervals')['word'] == 'rejected' and word(D2, 'H1')['word'] == 'rejected'
    assert 'no row of this table can say "rejected"' not in visible(text2)
    assert 'Session s2' in text2 and D2['names'] == ['s1', 's2']
    # one failing session and one that does not fail: not rejected
    weak = [folder('s2', 'B4', [T.b4(2, 'thp-p1', 30, 0, 'full')])]
    D3, _ = page({'s1': strong_session('s1'), 's2': weak})
    assert word(D3, 'H3a')['word'] != 'rejected'


def test_h3a_two_readings_are_printed_side_by_side():
    """WHY: case (a) on CPU 2 in one session and on CPU 41 in the other is a failed prediction in each session. The
    handoff gives "rejected" only for one CPU in both sessions, the plan has no such condition. The page must give the
    result of each session as it is, the strict word of the script, the other reading with its reason, and must leave
    the choice to the user. "not observed" is wrong under every reading, because the event occurred."""
    s2 = [folder('s2', 'B4', [T.b4(41, 'thp-p1', 15, 15, 'full'), T.b4(2, 'thp-p1', 30, 0, 'full')])]
    D, text = page({'s1': strong_session('s1'), 's2': s2})
    r = word(D, 'H3a')
    assert r['word'] == 'not rejected'
    assert 'The bounded prediction failed' in r['per']['s1']['result'] and 'CPU 2: case (a)' in r['per']['s1']['result']
    assert 'The bounded prediction failed' in r['per']['s2']['result'] and 'CPU 41: case (a)' in r['per']['s2']['result']
    assert len(r['open']) == 1 and 'Strict output of the analysis script: "not rejected"' in r['open'][0]
    assert 'Second reading: "rejected"' in r['open'][0] and 'word without the same-CPU condition' in r['open'][0] and 'judgment' in r['open'][0]
    v = visible(text)
    assert 'Open for the user' in v and 'session s1: CPU 2, session s2: CPU 41' in v
    assert 'CPU 2 has low intervals with full coverage in every session (s1: 15, s2: 30)' in v
    # the same CPU in both sessions: one word under both readings, nothing open
    D2, _ = page({'s1': strong_session('s1'), 's2': strong_session('s2')})
    assert word(D2, 'H3a')['word'] == 'rejected' and not word(D2, 'H3a')['open']


def test_b4_case_near_a_limit_is_marked():
    """WHY: the level limits are provisional. A case (a) whose low intervals lie just below 69 GB/s exists only because
    of that limit. The page must mark it, give the description without labels, and must not state that the prediction
    failed on that CPU. A case far from the limits is stated as failed."""
    args = '--threads 1 --cpus 41 --bytes 8M --seq asmread --rounds 40 --min-ms 300 --stop pass'
    near = T.block('B4', 'thp-p1-cpu41', args, lambda r, pos, e, tid, c: 71.5 if r < 17 else 68.9, page=lambda r, pos: (8192, 8192))
    D, text = page({'s1': [folder('s1', 'B4', [near])]})
    f = D['sessions']['s1']['b4_cases'][41]
    assert f['label_dependent'] and f['near_lo'] == 23 and f['n_low'] == 23 and f['near_hi'] == 0
    b4 = visible(M.sec_b4(D, M.Refs()))
    assert 'This case depends on the provisional limits. 23 of the 23 low intervals lie less than 0.2 GB/s below the limit of 69 GB/s' in b4
    assert 'went from a median of 71.50 GB/s (intervals 0 to 16) to a median of 68.90 GB/s (intervals 17 to 39)' in b4
    assert 'So the bounded prediction of H3a failed' not in b4
    assert 'The rule finds a case, and the case depends on the provisional limits' in word(D, 'H3a')['per']['s1']['result']
    D, _ = page({'s1': [folder('s1', 'B4', [T.b4(2, 'thp-p1', 15, 15, 'full')])]})
    assert not D['sessions']['s1']['b4_cases'][2]['label_dependent']
    assert 'So the bounded prediction of H3a failed in this session on this CPU' in visible(M.sec_b4(D, M.Refs()))


def test_unstable_process_is_described_and_not_decided():
    """WHY: at 8 MiB only a process whose references are all at one level may enter a decision (plan, rules 4 and 5).
    The other processes must still be visible, as a description, so that the user can judge the level limits."""
    blocks = []
    for c in (0, 2):
        blocks += [T.b1(c, i, T.copy_rate()) for i in range(1, 4)]
        blocks += [T.b1(c, 4, T.copy_rate(copy=67.0, ref_by_round=[67.5, 67.5, 71.2, 71.2]))]       # d = +9, the level changes
    D, text = page({'s1': [folder('s1', 'B1', blocks)]})
    x = D['sessions']['s1']
    g = x['pairs']['B1']['8M']
    rule = x['res']['B1']['groups']['8M']['labels']['low']
    assert g['per_cpu'][0]['n'] == 4 and rule['per_cpu'][0]['n_processes'] == 3         # 4 described, 3 decided
    assert g['per_cpu'][0]['n_not_stable'] == 1 and near(max(g['per_cpu'][0]['d']), 9.0)
    assert rule['decision'] == 'resolved' and rule['sign'] == -1                         # the odd process did not enter the rule
    assert not g['per_cpu'][0]['one_sign']                                               # and the description shows that it differs
    assert 'description, no decision' in text and 'Description, no decision' in text
    # all references between the two limits: the rule has no process at all, the description has all of them
    mid = [T.b1(c, i, T.copy_rate(ref=69.8)) for c in (0, 2) for i in range(1, 5)]
    D, text = page({'s1': [folder('s1', 'B1', mid)]})
    g = D['sessions']['s1']['pairs']['B1']['8M']
    assert word(D, 'H4, low intervals')['word'] == 'not observed' and word(D, 'H4, high intervals')['word'] == 'not observed'
    assert word(D, 'H4, low intervals')['n'] == 0
    assert all(v['n'] == 4 and v['above'] and v['one_sign'] and near(v['median_d'], -2.0) for v in g['per_cpu'].values())
    assert 'd is below 0 in 8 of 8 processes' in word(D, 'H4, low intervals')['basis']   # the description is next to the word, and is not the word
    assert 'Open decision for the user' in text and '0 of the 8 processes with reference intervals are stable' in visible(text)


def test_sizes_without_a_level_are_decided_for_all_processes():
    """WHY: at 4, 16 and 32 MiB no level is defined (handoff B.10), so the level limits must not remove a process there."""
    blocks = [T.b1(c, i, T.copy_rate(ref=69.8), bytes_='16M') for c in (0, 2) for i in range(1, 5)]
    D, text = page({'s1': [folder('s1', 'B1', blocks)]})
    r = D['sessions']['s1']['res']['B1']['groups']['16M']['labels']['none']
    assert r['decision'] == 'resolved' and r['per_cpu'][0]['n_processes'] == 4
    assert '16 MiB (the chart is a description' not in text and '<h4>16 MiB</h4>' in text


def test_b6_position_effect_is_shown():
    """WHY: in the B6 sequence one loop of a pair follows asm read and the other follows old read. If the loop before
    changes the rate, the median over both orders hides it and the A/A spread looks small. The page must show the
    rates by the loop before, and the largest single A/A pair, or the reader takes a position effect for a kernel effect."""
    seq = T.B6SEQ.split(',')

    def rate(r, pos, entry, tid, cpu):
        if entry == 'asmread':
            return 67.5
        if entry == 'oldread@1M':
            return 67.1
        if seq[pos - 1] == 'asmread':
            return 63.0                                                       # old read after asm read is 4 GB/s slower
        return 67.3 if entry == 'oldread2' else 67.0
    f = [folder('s1', 'B6', [T.b6(c, i, rate) for c in (2, 41) for i in range(1, 5)])]
    D, text = page({'s1': f})
    x = D['sessions']['s1']
    pc = x['b6']['per_cpu'][2]
    assert near(pc['aa_spread'], 0.15) and near(pc['aa_single_max'], 4.3)      # the spread of the rule is small, a single pair differs by 4.3
    assert near(pc['d_first'], 63.0 - 67.1) and near(pc['d_second'], 67.0 - 67.1)
    assert pc['aa_pos_n'] == 32 and pc['aa_pos_neg'] == 32                     # the copy timed first is slower in every A/A pair
    bp = x['b6_prev'][2]
    assert near(M.median(bp[('oldread', 'asm read')]), 63.0) and near(M.median(bp[('oldread', 'an old read entry')]), 67.0)
    v = visible(text)
    assert 'In 64 of 64 such pairs the first interval is slower than the second' in v
    assert 'So these data do not show that the rate of old read depends on the buffer size' in v
    assert 'Its cause is a hypothesis: the loop that ran before leaves a state' in v
    assert 'Its absolute value is 4.10 GB/s in one order of the two loops and 0.10 GB/s in the other' in v      # the line under the Short version
    assert 'Old read at 1 MiB after asm read minus old read at 1 MiB after old read is 0.00 GB/s' in v
    assert not word(D, 'H1')['open']                                           # one session: the word is not "rejected", nothing to choose
    # two sessions: the strict word is "rejected". It stays, with the limit next to it and the choice left to the user.
    D, text = page({'s1': f, 's2': [folder('s2', 'B6', [T.b6(c, i, rate) for c in (2, 41) for i in range(1, 5)])]})
    r = word(D, 'H1')
    assert r['word'] == 'rejected' and len(r['open']) == 1 and 'judgment' in r['open'][0] and '"not resolved"' in r['open'][0]
    assert 'The result comes from part 2 only' in r['basis']
    # no position effect: no such sentence, nothing open
    flat = lambda r, pos, entry, tid, cpu: 67.5 if entry == 'asmread' else 67.1 if entry == 'oldread@1M' else 60.0 if entry == 'oldread' else 60.1
    D, text = page({s: [folder(s, 'B6', [T.b6(c, i, flat) for c in (2, 41) for i in range(1, 5)])] for s in ('s1', 's2')})
    assert word(D, 'H1')['word'] == 'rejected' and not word(D, 'H1')['open'] and 'So these data do not show' not in text


def test_b4_marks_counter_increases_and_level_changes():
    """WHY: H3b cannot be tested without root. What B4 can show is whether a level change comes with a change of
    coverage or with an increase of thp_collapse_alloc or pgmigrate_success. So an increase must be found at the
    right interval. The plan gives H2 no bounded prediction in Parts B and C, so its word is "not tested" whatever the
    data show, and a change of level inside a process is described with its direction."""
    blk = T.b4(2, 'thp-p1', 30, 30, 'full')
    out = []
    for line in blk.splitlines():
        f = line.split(',')
        if f[0] == 'P' and int(f[1]) >= 30:
            f[9] = '8'                                    # thp_collapse_alloc 7 -> 8 before interval 30
        if f[0] == 'P' and int(f[1]) >= 45:
            f[10] = '95'                                  # pgmigrate_success 90 -> 95 before interval 45
        out.append(','.join(f))
    D, text = page({'s1': [folder('s1', 'B4', ['\n'.join(out) + '\n'])]})
    p = D['sessions']['s1']['b4'][0]
    assert p['events'] == {'thp_collapse_alloc': [30], 'pgmigrate_success': [45]}
    assert p['changes'] == [(29, 30)] and p['step_at'] == 30 and near(p['step_size'], 71.2 - 67.5)
    r = word(D, 'H2')
    assert r['word'] == 'not tested' and r['per']['s1']['result'].startswith('Description, no decision. 1 change between low and high')
    assert 'goes from low (67.50 GB/s, interval 29) to high (71.20 GB/s, interval 30).' in r['per']['s1']['result']
    assert 'no bounded prediction in Parts B and C' in r['basis']
    assert 'thp_collapse_alloc rose before interval 30' in text
    # no change of level inside a process: the event could have been shown and was not
    D, _ = page({'s1': [folder('s1', 'B4', [T.b4(2, 'thp-p1', 60, 0, 'full'), T.b4(2, 'thp-p2', 0, 60, 'full')])]})
    r = word(D, 'H2')
    assert r['word'] == 'not tested' and '0 changes between low and high' in r['per']['s1']['result'] and '1 process was high in all intervals' in r['per']['s1']['result']
    assert D['sessions']['s1']['res']['B4']['per_cpu'][2]['cases'] == ['a']        # low and high in two processes is still case (a)
    assert 'No process has both' in M.sec_b4(D, M.Refs())


def counters(l1_per_line, l2_per_line):
    def f(r, pos, entry, tid, nbytes):
        lines = nbytes // 64
        return '300000000,300000000,299000000,%d,%d,%d,%d,%d' % (840000000, nbytes * 11 // 256, int(lines * l1_per_line), int(lines * l2_per_line), 0)
    return f


def test_counter_observation_is_printed_only_when_computed():
    """WHY: "l1d_refill is lower than l2d_refill" is an observation of some runs. The sentence must come from the
    rows of the run on the page, not from the run in which it was first seen."""
    args = '--threads 1 --cpus 2 --bytes 8M --seq asmread --rounds 4 --min-ms 300 --stop pass --count'
    lower = T.block('C1', 'cpu2-p1', args, lambda *a: 67.5, counts=counters(0.37, 0.82))
    D, text = page({'s1': [folder('s1', 'C1', [lower])]})
    assert D['sessions']['s1']['cfacts']['C1']['l1_lt_l2'] == 4
    v = visible(text)
    assert 'Observation: the count of l1d_refill is lower than the count of l2d_refill in 4 of the 4 asm read intervals of C1' in v and 'Hypothesis: for this loop the two event names' in v
    # the plan asks C1 for both levels. A run with one level must say which measurement is missing.
    assert 'Insufficient data. Counters at the high level in a long run. No interval of C1 was above 70.5 GB/s. The level groups that were seen are: low.' in v
    # 299000000 ns of CPU time in 0.3 s is 99.666 %: the lowest value is rounded down, never up
    assert 'The lowest CPU time of a thread was 99.66 % of the elapsed time of its interval (rounded down)' in v
    higher = T.block('C1', 'cpu2-p1', args, lambda *a: 67.5, counts=counters(1.0, 0.82))
    D, text = page({'s1': [folder('s1', 'C1', [higher])]})
    assert 'Observation: in' not in text and 'In none of the 4 asm read intervals' in text
    g = D['sessions']['s1']['res']['C1']['groups'][0]
    assert near(g['median_instructions_per_line'], 2.75, 0.001) and near(g['median_clock_GHz'], 840 / 299, 0.001)


def test_missing_steps_and_part_d():
    """WHY: a step that is not in the input must read "Insufficient data" with the measurement that would give it,
    and H3b is "not tested" whatever the input, because Part D was not run."""
    D, text = page({'s1': [folder('s1', 'B4', [T.b4(2, 'thp-p1', 30, 0, 'full')])]})
    assert word(D, 'H3b')['word'] == 'not tested'
    for h in ('H1', 'H4', 'H5', 'H6'):
        assert word(D, h)['word'] == 'not tested', h
    assert D['sessions']['s1']['missing'] == ['B1', 'B2', 'B3', 'B6', 'C1', 'C2']
    v = visible(text)
    assert 'Insufficient data. Step B1: no process is in the input' in v and 'A run of step B1 would give it' in v
    assert 'Insufficient data. Step C2: no counter row' in v
    assert word(D, 'H3a')['word'] == 'not observed'               # one level only: neither case


def test_load_section():
    """WHY: the 1-minute load average stays high for a while after our own process with 120 threads. The page must
    not read that as another user: it names the step before, and gives the runnable tasks, waits and logins."""
    b1 = [T.block('B1', '8M-cpu%d-p%d' % (c, i), '--threads 1 --cpus %d --bytes 8M --seq %s --rounds 4 --min-ms 300 --stop pass' % (c, T.B1SEQ),
                  T.copy_rate(), load='%s 80.00 90.00 1/913' % ('88.50' if (c, i) == (0, 1) else '1.10')) for c in (0, 2) for i in (1, 2, 3)]
    f1 = folder('s1', 'B1', b1, start='2026-01-01T01:23:15Z', end='2026-01-01T01:40:00Z')
    big = [T.block('B9', 'one-p1', '--threads 120 --cpus 0-63,64-119 --bytes 256M --seq oldread --rounds 1 --min-ms 500 --stop common', lambda *a: 3.0)]
    f0 = folder('s1', 'B9', big, start='2026-01-01T01:21:00Z', end='2026-01-01T01:23:01Z')
    D, text = page({'s1': [f0, f1]})
    L = D['sessions']['s1']['load']['B1']
    assert L['n'] == 6 and near(L['load_max'], 88.5) and near(L['load_first'], 88.5) and near(L['load_last'], 1.1) and L['runnable_max'] == 1
    assert L['top'] == (0.3, 'root', 'kworker/1')                 # ps of the script itself is left out
    v = visible(text)
    assert 'ran 120 threads of our own benchmark and ended at 2026-01-01T01:23:01Z' in v
    assert 'It is therefore no evidence of another user' in v
    assert D['sessions']['s1']['other'][0]['steps'] == ['B9'] and D['sessions']['s1']['steps'] == ['B1']
    # without the folder of the step before, the cause is a labelled hypothesis
    _, text = page({'s1': [f1]})
    assert 'Hypothesis: the high values are left from a process with 120 threads' in visible(text)
    # no high value: the sentence is not printed
    _, text = page({'s1': [folder('s1', 'B4', [T.b4(2, 'thp-p1', 30, 0, 'full')])]})
    assert 'no evidence of another user' not in text and 'No launch on this page had a 1-minute load average above 2 tasks' in text
    # a busy process of the account that runs the script is not another user. One of another account is not explained by guessing.
    blk = [T.b4(2, 'thp-p1', 30, 0, 'full')]
    _, text = page({'s1': [folder('s1', 'B4', blk, busy='17.8 tester   systemd\n')]})
    assert 'with 17.8 % of one CPU at one launch' in visible(text) and 'The run script runs under the same account, so this is not another user' in visible(text)
    _, text = page({'s1': [folder('s1', 'B4', blk, busy='17.8 guest    python3\n')]})
    assert 'Insufficient data: what this process did' in visible(text) and 'same account' not in text


def test_tables_and_charts_keep_sessions_and_series_apart():
    """WHY: a reader must see the result of each session in its own column (plan, rule 10), and must know which number
    of a chart row is d and which is e, also when the two markers are close."""
    D, text = page({'s1': strong_session('s1'), 's2': strong_session('s2')})
    assert '<th>Session s1: result</th><th>Session s2: result</th>' in text
    r = word(D, 'H4, low intervals')
    assert set(r['per']) == {'s1', 's2'} and r['per']['s1']['used'] == '8 of 8'
    assert 'over the 4 stable low processes' in r['per']['s1']['spread'] and 'over all 4 processes' in r['per']['s1']['spread']
    svg = M.dumbbell([(s, D['sessions'][s]['pairs']['B1']['8M']) for s in ('s1', 's2')], 'test')
    assert svg.count('style="fill:%s">-2.00<' % M.TD) == 16 and svg.count('style="fill:%s">+0.10<' % M.TE) == 16     # d blue at the left, e orange at the right
    assert svg.index('e +0.100 GB/s') < svg.index('d -2.000 GB/s')              # the dot of d is drawn after the diamond of e, so it is on top
    assert 'How to read the charts and tables' in text and text.count('All columns before the column "Rule"') == 1


def check_page_rules(D, text):
    """The standing page rules that a script can check."""
    v = visible(text)
    assert ';' not in v, v[max(0, v.index(';') - 80):v.index(';') + 40]
    assert 'background:#ffffff' in text and 'prefers-color-scheme' not in text
    assert not re.search(r'(src|href)\s*=', text) and 'http://' not in text and 'https://' not in text and '@import' not in text
    body, refs = text.split('<h2 id="refs">')
    used = set(re.findall(r'\[Ref(\d+)\]', body))
    listed = re.findall(r'<li>\[Ref(\d+)\]', refs)
    assert used == set(listed) and listed == [str(i + 1) for i in range(len(listed))], (sorted(used, key=int), listed)
    sv = M.short_version(D)
    assert len(re.findall(r'[.!?](?:\s|$)', sv)) <= 3, sv
    assert text.index('Short version') < text.index('Words used here') < text.index('id="hyp"')
    for w in re.findall(r'<td><b>([^<]+)</b></td>', text):
        assert w in M.WORDS5, w
    assert text.count('<svg') == text.count('</svg>')
    for term in ('H1', 'H2', 'H3a', 'H3b', 'H4', 'H5', 'H6', 'B1', 'B2', 'B3', 'B4', 'B6', 'C1, C2', 'A/A control, A/A spread', 'est.'):
        assert '<li><b>%s</b>' % term in text, term


def test_page_rules_and_command_line():
    """WHY: the user's rules for a page (light background, no external resource, no semicolon, every reference listed,
    Short version of at most three sentences) hold for every input, also for an empty session."""
    f = strong_session('s1')
    for spec in ({'s1': f}, {'s1': f, 's2': strong_session('s2')}, {'s1': [folder('s1', 'B9', [])]}):
        D, text = page(spec)
        check_page_rules(D, text)
    out = os.path.join(ROOT, 'cli.html')
    argv = ['--session', 's1'] + f + ['--session', 's2'] + strong_session('s2') + ['-o', out, '--banner', BANNER]
    assert M.main(argv) == 0 and os.path.getsize(out) > 20000
    assert BANNER in open(out).read()


def test_real_session_1():
    """WHY: the page must give the same words as the analysis output of session 1 that the lead already has, and the
    numbers of the task that were known before the page was written."""
    R = os.path.join(M.CRB, 'results')
    names = ['B9-20261114T012105Z', 'B1-20261114T012315Z', 'B4-20261114T014024Z', 'B6-20261114T014825Z', 'B2-20261114T015517Z',
             'B3-20261114T020808Z', 'C1-20261114T022058Z', 'C2-20261114T022500Z']
    ref = os.path.join(R, 'partB-s1-analysis', 'summary.json')
    if not all(os.path.isdir(os.path.join(R, n)) for n in names) or not os.path.exists(ref):
        print('  skipped: the session 1 folders are not on this machine')
        return False
    D, text = M.make([('s1', [os.path.join(R, n) for n in names])])
    check_page_rules(D, text)
    lead = json.load(open(ref))['hypotheses']
    mine = D['summary']['hypotheses']
    for k in ('H4 (B1, 8 MiB, label low)', 'H4 (B1, 8 MiB, label high)', 'H5 (B2, asmcopy_c, label low)', 'H6 (B3)', 'H3a (B4)', 'H1 (B6)'):
        assert mine[k]['word'] == lead[k]['word'] and mine[k]['per_session'] == lead[k]['per_session'], k
    x = D['sessions']['s1']
    assert x['n_procs'] == 204 and x['n_used'] == 204 and not x['missing']
    assert all(r['word'] != 'rejected' for r in D['hyp'])
    assert word(D, 'H3a')['word'] == 'not rejected' and 'The bounded prediction failed' in word(D, 'H3a')['per']['s1']['result']
    assert sum(1 for r in x['pairs']['B1']['8M']['recs'] if r['d'] < 0) == 16
    assert [(c, v['cases']) for c, v in x['res']['B4']['per_cpu'].items()] == [(2, ['a']), (41, [])]
    assert 'B9-20261114T012105Z' in visible(text) and near(x['load']['B1']['load_max'], 90.41)
    assert sum(len(p['events'][k]) for p in x['b4'] for k in p['events']) == 0
    return True


def test_real_two_sessions():
    """WHY: the words and the main numbers of the delivered page, checked against values that were recomputed from the
    raw csv files by independent scripts during the review of 2026-11-14."""
    N = os.path.join(M.CRB, 'new-test-kernel')
    R = os.path.join(M.CRB, 'results')
    try:
        spec = [(s, [os.path.join(R, n) for n in open(os.path.join(N, f)).read().split()]) for s, f in (('s1', 'session1-folders.txt'), ('s2', 'session2-folders.txt'))]
    except OSError:
        spec = []
    if not spec or not all(os.path.isdir(p) for _, ps in spec for p in ps):
        print('  skipped: the folders of the two sessions are not on this machine')
        return False
    D, text = M.make(spec)
    check_page_rules(D, text)
    words = {r['h']: r['word'] for r in D['hyp']}
    assert words == {'H1': 'rejected', 'H2': 'not tested', 'H3a': 'not rejected', 'H3b': 'not tested', 'H4, low intervals': 'not observed',
                     'H4, high intervals': 'not observed', 'H5': 'not observed', 'H6': 'not observed'}, words
    assert D['summary']['hypotheses']['H3a (B4)']['per_session'] == {'s1': 'fail', 's2': 'fail'}
    assert len(word(D, 'H3a')['open']) == 2 and len(word(D, 'H1')['open']) == 1
    assert D['sessions']['s2']['b4_cases'][41]['label_dependent'] and not D['sessions']['s1']['b4_cases'][2]['label_dependent']
    v = visible(text)
    assert 'in 31 of 32 program runs over 2 test sessions (median per CPU: 1.18 to 2.61 GB/s slower' in v
    assert 'could use only 5 of these 32 runs' in v and 'In 384 of 384 such pairs the first interval is slower' in v
    for wrong in ('at least 99.94', 'at least 99.90'):
        assert wrong not in v
    assert v.count('99.93 % of the elapsed time') == 2 and '99.89 % of the elapsed time' in v and '99.91 % of the elapsed time' in v     # 99.9199 % is below 99.92 %
    assert 'Over the 19 rows of B1, B2, B3, B6, C2' in v and '3 h 14 min apart' in v
    return True


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    skipped = 0
    for t in tests:
        print(t.__name__)
        if t() is False:
            skipped += 1
    if not KEEP:
        shutil.rmtree(ROOT, ignore_errors=True)
    shutil.rmtree(T.TMP, ignore_errors=True)
    print('%d tests passed, %d skipped%s' % (len(tests) - skipped, skipped, '' if not KEEP else ', files kept in ' + KEEP))
