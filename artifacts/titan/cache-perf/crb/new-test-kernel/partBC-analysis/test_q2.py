#!/usr/bin/env python3
"""test_q2.py [--keep DIR]: tests of make_q2_html.py on synthetic result folders in the row format of handoff.md B.3.

Each test states WHY its rule matters. The synthetic machine has 4 threads on mesh 0 (CPUs 0 to 3) and 4 on
mesh 1 (CPUs 64 to 67). Rates are invented. They only steer the decision rules.
Run: python3 test_q2.py
"""
import html, os, re, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_q2_html as Q  # noqa: E402

MIB = 1 << 20
BOOT = 1790000000          # boot time of the synthetic machine, seconds since 1970
SETTINGS = [(st, ms, sa) for st in ('pass', 'common') for ms in (500, 6000) for sa in ('common', 'offset')]
B7SEQ = 'oldread,read,asmread,asmread2,asmread2,asmread,read,oldread'
B10SEQ = 'oldwrite,write,asmwrite,asmwrite2,asmwrite2,asmwrite,write,oldwrite'
B5SEQ = 'oldread,read,read_sparse,read_nop4,read_nop8,read_nop16,read_nop32,asmread,asmread2'


def cpus(a, b):
    return list(range(a)) + list(range(64, 64 + b))


class Folder:
    """One result folder: <step>.csv, env.txt, launches.txt, stderr.txt."""

    def __init__(self, root, name, step, t0=None, busy=None):
        """t0: start of the folder in seconds since 1970 (it ends 590 s later). busy: one line of ps for the first launch."""
        self.dir = os.path.join(root, name); self.step = step; self.n = 0; self.busy = busy
        os.makedirs(self.dir)
        self.csv = open(os.path.join(self.dir, step + '.csv'), 'w')
        self.la = open(os.path.join(self.dir, 'launches.txt'), 'w')
        ts = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))
        a = ts(t0) if t0 is not None else '2026-01-01T00:00:00Z'; b = ts(t0 + 590) if t0 is not None else '2026-01-01T00:10:00Z'
        with open(os.path.join(self.dir, 'env.txt'), 'w') as fh:
            fh.write(f'## host=test utc={a} loadavg=0.50 1.00 1.00 1/900 123 logins=0 step={step} steps={step}\n'
                     + (f'## uptime={t0 - BOOT:.2f} MemFree: 1 kB\n' if t0 is not None else '')
                     + '## settings: STOP_AT=none BWX_STOP=common BWX_START=common BWX_MIN_MS=6000 BWX_EVENTS=cycles=0x11\n'
                     f'## end utc={b} loadavg=7.50 3.00 1.00 1/900 456\n')
        open(os.path.join(self.dir, 'stderr.txt'), 'w').close()

    def proc(self, tag, cp, seq, rounds, stop, ms, start, rate, extra='', late=None, count=False):
        """rate(kernel, cpu, round, pos) -> GB/s of one thread. late = (round, pos, tid) marks one late thread."""
        self.n += 1
        load = '99.00 50.00 20.00' if self.n > 1 else '0.50 1.00 1.00'
        self.la.write(f'== {self.step}.csv {tag} utc 00:00:{self.n:02d} loadavg {load} 1/900 logins 0\n%CPU USER     COMMAND\n'
                      + (self.busy + '\n' if self.busy and self.n == 1 else '') + ' 0.3 tester   bash\n 0.1 root     kworker/0:1-events\n')
        args = f'--threads {len(cp)} --cpus x --bytes 256M --seq {seq} --rounds {rounds} --stop {stop} --min-ms {ms} --start {start}{extra}' + (' --count' if count else '')
        w = self.csv.write
        w(f'-- step {self.step} tag {tag} binary bwx waited_s 0 loadavg {load} 1/900 logins 0 utc 00:00:{self.n:02d} args {args}\n# bandwidth: synthetic\n')
        el = ms / 1000.0
        for r in range(rounds):
            for i, k in enumerate(seq.split(',')):
                for tid, c in enumerate(cp):
                    b = int(rate(k, c, r, i) * 1e9 * el)
                    flag = 'late' if late == (r, i, tid) else '-'
                    w(f'T,{r},{i},{k},{tid},{c},{b},{el:.6f},1.000000,1.000000,{1 + el:.6f},{b / (256 * MIB):.3f},{flag}\n')
                    if count:
                        lines = b / 64
                        w(f'C,{r},{i},{k},{tid},{c},{int(el * 1e9)},{int(el * 1e9)},{int(el * 0.995e9)},{int(el * 2.8e9)},{int(lines * 3)},{int(lines * 0.95)},{int(lines)},{int(lines * 0.1)}\n')
                    w(f'P,{r},{i},{tid},a,262144,262144,1,0,0,0\n')

    def close(self):
        self.csv.close(); self.la.close()
        return self.dir


def session(root, name, steps=('B7', 'B10', 'B8', 'B5', 'B9', 'C3'), stop_effect=0.0, late=False, sparse_equal=False, b10='flat', old_m0=5.0, b9_two_uniform=False,
            boost=None, later_start='common', clock0=None, c3_busy=None):
    """Writes the folders of one session and returns their paths.
    stop_effect: GB/s per mesh-0 thread that old read loses with the common stop (a real effect of the stop method).
    b10: 'flat' (no higher interval), 'mesh1' (one interval of old write has a faster mesh 1), 'both' (both meshes faster).
    boost: a B7 setting (stop, ms, start) in which old read gains 0.5 GB/s per mesh-0 thread, so that the handoff rule selects it.
    later_start: the start mode of B8, B5 and B9. clock0: start of the session in seconds since 1970 (one folder per 600 s).
    c3_busy: a ps line of another account at the first launch of C3."""
    out, pn, fn = [], [0], [0]

    def Fo(nm, step, busy=None):
        fn[0] += 1
        return Folder(root, nm, step, t0=None if clock0 is None else clock0 + 600 * (fn[0] - 1), busy=busy)

    def eps():                                    # small deterministic A/A noise per process
        pn[0] += 1
        return ((pn[0] * 37) % 11 - 5) * 0.004

    def reader(stop, ep, sparse=False):
        def rate(k, c, r, i):
            m0 = c < 64
            if k == 'oldread' or (sparse and k == 'read_sparse'):
                return ((old_m0 - (stop_effect if stop == 'common' else 0)) if m0 else 2.8) + ep * 3 * (0.5 - (r + i) % 2)
            return (2.6 if m0 else 2.4) + (ep if k == 'asmread2' else 0) + (0.002 * (i % 3) if k.startswith('read') else 0)
        return rate
    C = cpus(4, 4)
    if 'B7' in steps:
        F = Fo(f'B7-{name}', 'B7')
        for p in range(1, 5):
            for st, ms, sa in SETTINGS:
                lt = (0, 0, 2) if late and p == 1 and (st, ms, sa) == ('common', 500, 'common') else None
                rd = reader(st, eps())
                if boost == (st, ms, sa):
                    rd = (lambda base: lambda k, c, r, i: base(k, c, r, i) + (0.5 if k == 'oldread' and c < 64 else 0))(rd)
                F.proc(f'{st}-{ms}-{sa}-p{p}', C, B7SEQ, 2, st, ms, sa, rd, late=lt)
            for k in ('oldread', 'read', 'asmread', 'asmread2'):
                F.proc(f'single-{k}-p{p}', C, k, 3, 'pass', 500, 'common', reader('pass', eps()))
        out.append(F.close())
    if 'B10' in steps:
        F = Fo(f'B10a-{name}', 'B10')
        for p in range(1, 5):
            for st, ms, sa in SETTINGS:
                ep = eps()
                def rate(k, c, r, i, ep=ep):
                    v = 1.0 + (ep if k == 'asmwrite2' else 0)
                    if k == 'oldwrite' and (r, i) == (1, 0) and b10 != 'flat' and (c >= 64 or b10 == 'both'):
                        v *= 1.5
                    return v
                F.proc(f'{st}-{15000 if ms == 6000 else 500}-{sa}-p{p}', C, B10SEQ, 2, st, 15000 if ms == 6000 else 500, sa, rate)
        out.append(F.close())
    if 'B8' in steps:
        F = Fo(f'B8-{name}', 'B8')
        for p in (1, 2):
            for b in (2, 3, 4):
                def rate(k, c, r, i, b=b):
                    if k == 'oldread':                       # by the label rule: split at 2 and 3, uniform at 4
                        return 2.6 if b == 4 else (5.0 if c < 64 else 2.8)
                    return 2.6 if b >= 3 else (5.0 if c < 64 else 2.8)      # asm read: split at 2, uniform at 3 and 4
                F.proc(f'4+{b}-p{p}', cpus(4, b), 'oldread,asmread,asmread2,asmread2,asmread,oldread', 1, 'common', 6000, later_start, rate)
        out.append(F.close())
    if 'B5' in steps:
        F = Fo(f'B5-{name}', 'B5')
        for p, seq in enumerate((B5SEQ, ','.join(reversed(B5SEQ.split(','))), B5SEQ, ','.join(reversed(B5SEQ.split(',')))), 1):
            F.proc(f'b5-{p}', C, seq, 1, 'common', 6000, later_start, reader('pass', eps(), sparse=sparse_equal))
        out.append(F.close())
    if 'B9' in steps:
        F = Fo(f'B9-{name}', 'B9')
        for p in (1, 2, 3):
            F.proc(f'onebuf-p{p}', C, 'oldread', 3, 'common', 6000, later_start, reader('pass', eps()))
            two = (lambda k, c, r, i: 2.6) if b9_two_uniform else reader('pass', eps())
            F.proc(f'twobuf-p{p}', C, 'oldread', 3, 'common', 6000, later_start, two, extra=' --two-buffers')
        out.append(F.close())
    if 'C3' in steps:
        F = Fo(f'C3-{name}', 'C3', busy=c3_busy)
        for p in (1, 2):
            F.proc(f'common-6000-common-p{p}', C, B7SEQ, 2, 'common', 6000, 'common', reader('pass', eps()), count=True)
        out.append(F.close())
    return out


def page(sessions):
    m = Q.compute(sessions, offsets=Q.OFFSETS)
    return m, Q.build(m)


def hyp(m):
    return {h['label']: h for h in m['hyp']}


def visible(h):
    h = re.sub(r'<style>.*?</style>', ' ', h, flags=re.S)
    h = re.sub(r'<title>.*?</title>', ' ', h, flags=re.S)        # tooltips of chart markers and the page title
    return html.unescape(re.sub(r'<[^>]+>', ' ', h))


def e_in(text, h):
    """True if the text stands on the page (escaped as the page escapes it)."""
    return html.escape(text) in h


def check_page_rules(h, m):
    """The standing rules of the user for a result page."""
    t = visible(h)
    # WHY: the page must be readable with no network and must not follow a dark OS theme.
    assert 'http' not in h and '<script' not in h and '<link' not in h and '<img' not in h, 'external resource or script'
    assert 'color-scheme:light' in h and 'background:#ffffff' in h and 'prefers-color-scheme' not in h
    # WHY: a newcomer reads only the Short version. More than three sentences is a defect by the user's rule.
    sv = visible(re.search(r'<b>Short version\.</b>(.*?)</p>', h, re.S).group(1))
    assert len(re.findall(r'[.!?]["\')]?(?:\s|$)', sv.strip())) <= 3, sv
    # WHY: a newcomer has not met the hypothesis labels yet. The Short version must do without them.
    assert not re.search(r'\bH\d', sv) and 'resolved' not in sv, sv
    # WHY (user's rule 5): a reference index stands at the end of the sentence, before its full stop, never after it.
    bad = re.search(r'[.!?]\s*\[Ref\d+\]', t.split('References')[0])
    assert not bad, t[max(0, bad.start() - 80):bad.end() + 20]
    assert not re.search(r'(\[Ref\d+\])\1', h), 'a reference is repeated in one group'
    # WHY: every row of the hypothesis table must show what the analysis rule gives as it stands, next to the word of the page.
    for x in m['hyp']:
        assert x['strict'] and x['meaning'] and x['short'], x['label']
        assert x['open'] == '' or 'Open for the user' in h, x['label']
    # WHY: semicolons join two claims in one sentence. The user's rule forbids them in prose.
    assert ';' not in t, t[max(0, t.index(';') - 80):t.index(';') + 40]
    # WHY: a claim with a reference number that is not in the list cannot be checked by the reader.
    used = {int(x) for x in re.findall(r'\[Ref(\d+)\]', h.split('<h2 id="refs">')[0])}
    listed = {int(x) for x in re.findall(r'<li>\[Ref(\d+)\]', h.split('<h2 id="refs">')[1])}
    assert used <= listed, used - listed
    assert listed <= used, ('listed and never cited', listed - used)
    # WHY: a label that runs out of the drawing is cut off in the browser and the reader loses a number.
    for mm in re.finditer(r'<svg viewBox="0 0 (\d+) (\d+)"(.*?)</svg>', h, re.S):
        W, H = int(mm.group(1)), int(mm.group(2))
        for tx in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)"([^>]*)>(.*?)</text>', mm.group(3), re.S):
            x, y, attr, s = float(tx.group(1)), float(tx.group(2)), tx.group(3), html.unescape(tx.group(4))
            size = 10 if 'font-size:10px' in attr else 12 if 'class="lab"' in attr else 11
            w = len(s) * size * (0.60 if 'font-weight' in attr else 0.56)
            x0 = x - w if 'text-anchor="end"' in attr else x - w / 2 if 'text-anchor="middle"' in attr else x
            assert x0 >= -6 and x0 + w <= W + 6, ('text outside the drawing', W, round(x0), round(x0 + w), s)
            assert 0 < y <= H, ('text above or below the drawing', s)
    # WHY: every step and every hypothesis label that the page uses must be defined in "Words used here".
    words = h.split('<h2 id="words">')[1].split('<h2')[0]
    for term in ('B7', 'B10', 'B8', 'B5', 'B9', 'C3', 'H7a', 'H7b', 'H8', 'H9a', 'H9b', 'H10', 'H11', 'M_hist', 'M_sum', 'A/A', 'CRB', '<b>q</b>', '<b>D</b>',
                 '<b>Pattern</b>', 'Bounded prediction', 'Cell (B10)', 'Group (C3)', '<b>Visit</b>', 'Short run', 'Open for the user', 'Limit, band', 'UTC', '<code>ps</code>'):
        assert term in words, term
    # WHY: "L1" and "L2" are cache levels on this page. A rule of the page must not carry the same name.
    assert not re.search(r'\brule L\d', t) and 'est.' not in words
    # WHY: the user asks for the load of every step.
    for s in m['sessions']:
        for st in m['S'][s]['steps']:
            assert st in m['S'][s]['load'], st


def main():
    keep = sys.argv[sys.argv.index('--keep') + 1] if '--keep' in sys.argv else None
    root = keep or tempfile.mkdtemp(prefix='q2test-')
    if keep:
        shutil.rmtree(keep, ignore_errors=True); os.makedirs(keep)
    n = [0]

    def mk(**kw):
        n[0] += 1
        d = os.path.join(root, f'set{n[0]}'); os.makedirs(d)
        return session(d, f's{n[0]}', **kw)

    # ---- 1. One session, no factor changes D.
    # WHY: rule 11 of the plan gives "rejected" only for a prediction that failed in BOTH sessions. A page built from
    # one session must never print that word as a result, whatever the data show.
    a1 = mk()
    m, h = page({'s1': a1})
    H = hyp(m)
    assert m['summary']['hypotheses']['H7a (B7, read)']['per_session'] == {'s1': 'fail'}
    assert all(x['word'] != 'rejected' for x in m['hyp']), [(x['label'], x['word']) for x in m['hyp']]
    assert H['H7a, read']['word'] == 'not rejected' and H['H7a, read']['one_session'] and H['H7b, read']['one_session']
    assert 'Every "rejected" is impossible with one session' in h and 'prediction failed in this session' in h
    assert '<b>rejected</b>' not in h
    assert H['H9b']['word'] == 'not tested' and H['H10']['word'] == 'not tested'
    check_page_rules(h, m)
    if keep:
        open(os.path.join(root, 'one-session.html'), 'w').write(h)
    # WHY: text that interprets data must come from the data. The median D of the synthetic input is known:
    # 4 threads x (5.0 - 2.6) + 4 threads x (2.8 - 2.4) = 11.2 GB/s (new read carries up to +0.004 GB/s per thread).
    md = m['S']['s1']['B7']['res']['settings']['pass/500/common']['metrics']['M_hist']['median_D']
    assert abs(md - 11.2) < 0.05, md
    assert Q.fx(md) in h
    assert m['S']['s1']['B7']['res']['reproduced_in_either_way'] and 'is reproduced in the changed benchmark' in h

    # ---- 2. Two sessions with the same failed prediction.
    # WHY: without this case test 1 could pass with a generator that can never say "rejected" at all.
    a2 = mk()
    m2, h2 = page({'s1': a1, 's2': a2})
    H2 = hyp(m2)
    assert H2['H7a, read']['word'] == 'rejected' and H2['H7b, read']['word'] == 'rejected', (H2['H7a, read'], H2['H7b, read'])
    assert not H2['H7a, read']['one_session'] and 'Every "rejected" is impossible' not in h2
    # WHY (L3): H9b compares sessions. Equal synthetic sessions give overlapping ranges of q, so no difference was seen.
    assert H2['H9b']['word'] == 'not observed', H2['H9b']
    # WHY: the overlap test of H9b is a rule of this page, not of the plan, and user decision 2 gives "not resolved" for a
    # rule that needs a label. The page must print both readings and leave the choice to the user.
    assert H2['H9b']['open'] and 'not resolved' in H2['H9b']['other'] and 'not approved' in H2['H9b']['other']
    # WHY: "rejected" for H7b rests on changes that all lie inside their limit, which rule 11 also calls "not resolved".
    # The word of the analysis rule is printed, with the limits, the other reading, and the mark "open for the user".
    b = H2['H7b, read']
    assert '"rejected" (s1: fail, s2: fail)' in b['strict'] and b['open'] == '"rejected" or "not resolved"' and 'no resolved contribution' in b['other']
    assert '8 of 8 lie inside the limit' in b['basis'] and 'could not show a contribution below its limit' in b['basis'], b['basis']
    assert h2.count('<b>open for the user</b>') == sum(1 for x in m2['hyp'] if x['open'])
    # WHY: a "not rejected" word must not carry the mark of an open judgment.
    assert not H2['H10']['open'] and not H2['B5 statement']['open']
    check_page_rules(h2, m2)
    if keep:
        open(os.path.join(root, 'two-sessions.html'), 'w').write(h2)

    # ---- 3. A real effect of the stop method in both sessions.
    # WHY: a factor that changes D by more than the control must keep H7a from being rejected, and must leave H7b alone.
    b1, b2 = mk(stop_effect=2.0), mk(stop_effect=2.0)
    m3, h3 = page({'s1': b1, 's2': b2})
    H3 = hyp(m3)
    assert H3['H7a, read']['word'] == 'not rejected' and H3['H7b, read']['word'] == 'rejected', (H3['H7a, read']['flags'], H3['H7b, read']['flags'])
    assert Q.fx(8.0) in h3 or Q.fx(-8.0) in h3 or '-8.0' in h3            # the change of D (4 threads x 2.0 GB/s) is printed
    # WHY: "not rejected" must not read as "the timing method explains the difference". The basis gives the direction and
    # the size of the resolved changes: here D is larger with whole passes (old read loses 2 GB/s per thread with the common stop).
    assert 'D is larger with whole passes' in H3['H7a, read']['basis'] and '% of the median D' in H3['H7a, read']['basis'], H3['H7a, read']['basis']
    assert not H3['H7a, read']['open'] and 'no timing setting removes it' in H3['H7a, read']['basis']

    # ---- 4. The pattern labels are not used (user decision of 2026-11-13).
    # WHY: q did not fall into two groups in Part A. A result that rests on the labels would be an artefact of two
    # provisional limits. The synthetic B8 gives a clean bracket by the label rule, B9 gives equal labels, and B5 gives a
    # sparse loop equal to old read. The analysis script calls these "supported" and "rejected". The page must not.
    c1, c2 = mk(sparse_equal=True), mk(sparse_equal=True)
    m4, h4 = page({'s1': c1, 's2': c2})
    H4, an = hyp(m4), m4['summary']['hypotheses']
    assert an['H8 (B8)']['word'].startswith('not rejected (supported)'), an['H8 (B8)']
    assert an['H9a (B9)']['word'] == 'rejected', an['H9a (B9)']
    assert an['B5 statement "vector adds are needed for the split pattern of old read"']['word'] == 'rejected'
    assert H4['H8']['word'] == 'not resolved' and H4['H9a']['word'] == 'not resolved' and H4['B5 statement']['word'] == 'not resolved'
    # WHY: the conflict between the label rule and the user decision is shown side by side, not hidden and not overridden silently.
    assert H4['H9a']['strict'].startswith('"rejected" (s1: fail, s2: fail)') and 'It is not used: user decision 2' in H4['H9a']['other']
    assert H4['H8']['strict'].startswith('"not rejected (supported)"') and H4['H8']['other']
    assert e_in(H4['H9a']['other'], h4) and e_in(H4['H9a']['strict'], h4)
    assert not H4['H9a']['open']                                                       # decided by the user, so it is not open
    assert not hyp(m2)['B5 statement']['other']                                        # no conflict where the total alone decides
    b8 = h4.split('<h2 id="b8">')[1].split('<h2')[0]
    assert not re.search(r'\b(split|uniform)\b', visible(b8).replace('labels split and uniform', '')), 'a label is printed in the B8 section'
    # WHY: where the totals alone decide the B5 rule, no label is needed and the result must not be weakened.
    assert hyp(m2)['B5 statement']['word'] == 'not rejected' and hyp(m2)['B5 statement']['flags'] == {'s1': 'hold', 's2': 'hold'}

    # ---- 5. An irregular interval.
    # WHY: handoff B.4: an interval with a late thread is not used for a decision. Its process then has no D, the
    # setting has 3 processes, and 3 are too few (B.10 asks for 4). The page must list the interval and say "not observed".
    d1 = mk(late=True)
    m5, h5 = page({'s1': d1})
    st = m5['S']['s1']['B7']['res']['settings']
    assert st['common/500/common']['decision'] == 'not observed' and st['pass/500/common']['decision'] == 'resolved'
    irr = h5.split('<h3>Irregular intervals</h3>')[1].split('<p>')[0]
    assert 'common-500-common-p1' in irr and 'old read' in irr
    assert 'D is resolved with old read above new read in 7 of 8 settings' in h5
    check_page_rules(h5, m5)

    # ---- 6. H11.
    # WHY: H11 says ONE mesh makes the higher totals. A higher interval in which only mesh 1 is faster supports it.
    # A higher interval in which both meshes are faster contradicts it, and only two such sessions reject it.
    e1 = mk(b10='mesh1')
    m6, h6 = page({'s1': e1})
    assert hyp(m6)['H11']['word'] == 'not rejected' and hyp(m6)['H11']['plan_word'] == 'supported', hyp(m6)['H11']
    f1, f2 = mk(b10='both'), mk(b10='both')
    assert hyp(page({'s1': f1})[0])['H11']['word'] != 'rejected'
    m7, h7 = page({'s1': f1, 's2': f2})
    assert hyp(m7)['H11']['word'] == 'rejected' and hyp(m7)['H11']['plan_word'] == 'contradicted', hyp(m7)['H11']
    assert '<b>rejected</b> (contradicted)' in h7
    # WHY: with no higher interval in any setting the plan says "not observed", not "rejected".
    assert hyp(m)['H11']['word'] == 'not observed', hyp(m)['H11']

    # ---- 7. Missing steps.
    # WHY: a step without data must show "Insufficient data" and the word "not tested". It must not be skipped silently.
    g1 = mk(steps=('B7', 'B10'))
    m8, h8 = page({'s1': g1})
    H8 = hyp(m8)
    assert H8['H8']['word'] == 'not tested' and H8['H9a']['word'] == 'not tested' and H8['B5 statement']['word'] == 'not tested'
    for stp in ('B8', 'B5', 'B9', 'C3'):
        sec = h8.split(f'<h2 id="{stp.lower()}">')[1].split('<h2')[0]
        assert 'Insufficient data' in sec and f'no process of step {stp}' in sec, stp
    assert 'Missing: B8 in session s1' in h8
    check_page_rules(h8, m8)

    # ---- 8. The command line, with folders of other steps in the input.
    # WHY: the lead calls the script with all folders of a session. Processes of the Q1 steps must not reach this page.
    other = Folder(os.path.join(root, 'set1'), 'B4-x', 'B4')
    other.proc('cpu2-p1', [2], 'asmread', 2, 'pass', 300, 'common', lambda k, c, r, i: 68.0)
    out = os.path.join(root, 'cli.html')
    assert Q.main(['--session', 's1'] + a1 + [other.close(), '-o', out]) == 0
    hc = open(out).read()
    assert 'B4-x' not in hc and 'Session s1 has 6 result folders for 6 steps' in hc

    # ---- 9. The load statement.
    # WHY: the 1-minute load is high after our own process. The page must name the readings that show an idle host.
    ld = h.split('<h2 id="load">')[1].split('<h2')[0]
    assert 'Our own benchmark process' in ld and 'Runnable tasks: 1 at each of the' in ld and '0 of ' in ld and 'Logged-in users: 0 at each of the' in ld
    assert 'above 10 % of one CPU at 0 launches' in visible(ld) and 'Another account' not in ld
    assert m['S']['s1']['load']['B7']['load_max'] == 99.0 and m['S']['s1']['load']['B7']['first_load'] == 0.5

    # ---- 10. A process of another account, the times of the sessions, and a deviation of the setting.
    # WHY: the user asks for the load of every step. A busy process of another account must be named with its launch, and
    # must not disappear behind a general sentence on an idle host.
    t0 = 1794600000
    i1 = mk(boost=('common', 6000, 'common'), clock0=t0)
    i2 = mk(boost=('common', 6000, 'offset'), clock0=t0 + 6 * 600 - 10 + 14, c3_busy='90.9 root     check-new-relea')
    m10, h10 = page({'s1': i1, 's2': i2})
    ld = visible(h10.split('<h2 id="load">')[1].split('<h2')[0])
    assert 'above 10 % of one CPU at 1 launch of' in ld and 'Another account, session s2, step C3' in ld and 'check-new-release' in ld and '90.9 %' in ld, ld[:900]
    assert 'at 1 of 2 launches of that step' in ld
    # WHY: rule 10 of the plan asks for sessions some hours apart. The page must give the real times, so that a reader
    # sees that the two sessions are one continuous run (session 2 starts 14 s after session 1 ends).
    v10 = visible(h10)
    assert 'Session s2 started 14 s after session s1 ended' in v10 and 'one continuous run' in v10, v10[v10.index('When the sessions ran'):][:700]
    assert 'each step of session s2 started 1 h 0 min after the same step of session s1' in v10
    assert 'so the machine was not restarted between the sessions' in v10
    assert 'Insufficient data: whether the machine was restarted' in visible(h2)       # no uptime reading in those folders
    # WHY: B8, B5 and B9 must run in the setting that the handoff rule selects from B7 of the same session. Where they
    # did not, the page must call it a deviation, name both settings and say that the user did not decide it.
    assert m10['S']['s1']['B7']['chosen'] == 'common/6000/common' and m10['S']['s2']['B7']['chosen'] == 'common/6000/offset'
    fa = visible(h10.split('<h2 id="facts">')[1].split('<h2')[0])
    assert fa.count('Deviation, session') == 1 and 'Deviation, session s2' in fa and 'The user did not decide this' in fa, fa[:1500]
    assert 'The handoff rule selects "common stop, 6 s, offset start"' in fa and 'It is the setting that the rule selects in session s1' in fa
    assert 'Deviation, session' not in h2 or m2['S']['s1']['B7']['chosen'] != 'common/6000/common' or m2['S']['s2']['B7']['chosen'] != 'common/6000/common'
    # WHY: the pair of intervals in the per-thread chart must come from the setting that the later steps really used.
    assert m10['S']['s2']['B7']['rep']['setting'] == 'common/6000/common' and m10['S']['s2']['B7']['rep']['why'] == 'used'
    check_page_rules(h10, m10)
    if keep:
        open(os.path.join(root, 'deviation.html'), 'w').write(h10)

    # ---- 11. The 2 % check of rule 7, a rounded zero, the shared axis of B8, and H11 over two sessions.
    # WHY: rule 7 of the plan applies to every run with whole passes. The synthetic threads make 9 passes or fewer in
    # 0.5 s, so every such interval fails, also with one kernel per process and in B10.
    b7 = m['S']['s1']['B7']
    assert b7['fail2_single'][0] == b7['fail2_single'][1] == 48 and '<td>48 of 48</td>' in h
    f10 = m['S']['s1']['B10']['fail2']
    assert set(f10) == {'pass/500/common', 'pass/500/offset', 'pass/15000/common', 'pass/15000/offset'} and f10['pass/500/common'][:2] == (64, 64)
    assert f10['pass/15000/common'][0] == 0                                           # 15 s at 1 GB/s: 55 passes
    b10h = h.split('<h2 id="b10">')[1].split('<h2')[0]
    assert '<td>64 of 64</td>' in b10h and '<td>0 of 64</td>' in b10h and 'Fewest passes of a thread' in b10h
    # WHY: "-0.00" and "+0.00" are the same number. A sign on a rounded zero looks like a direction.
    assert Q.fs(-0.001) == '0.00' and Q.fs(0.004) == '0.00' and Q.fs(-0.006) == '-0.01' and Q.fs(1.5) == '+1.50'
    # WHY: two sessions with the same thread rates must not look different because the charts chose different axes.
    assert m2['b8_ymax'] == 6.0 and h2.count('>6</text>') >= 6
    # WHY: H11 needs the same result in both sessions. A cell that is supported in one session only is "not resolved".
    m11, h11 = page({'s1': e1, 's2': a2})
    H11 = hyp(m11)['H11']
    assert H11['word'] == 'not resolved' and '0 of 32 cells are supported in every session' in H11['basis'], H11['basis']
    assert 'Mesh 1 rose by' in H11['basis'] and 'Supported in s1: old write' in H11['basis']
    # WHY: question Q2b must get a plain statement. With no rule for "separate levels" that statement is "Insufficient data".
    b10s = visible(h.split('<h2 id="b10">')[1].split('<h2')[0])
    assert 'Question Q2b, description and no decision' in b10s and 'set no rule for when two totals are separate levels' in b10s

    if not keep:
        shutil.rmtree(root)
    print('test_q2: all tests passed' + (f' (pages kept in {root})' if keep else ''))


if __name__ == '__main__':
    main()
