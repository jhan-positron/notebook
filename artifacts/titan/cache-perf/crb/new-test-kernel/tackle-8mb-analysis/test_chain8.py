#!/usr/bin/env python3
"""test_chain8.py - local test of the whole bwx8 chain, on the development machine only.

Usage: test_chain8.py [--divisor N] [--reuse] [--no-render]

The chain: gcc builds bwx8.c with stand-in kernels -> schedule8.py writes a schedule with --test-divisor ->
run_bwx8.sh runs session 1 and session 2 -> analyze8.py forecast and summary -> report8.py.
Then a second page is rendered from synthetic result folders without the test mark (builder of
test_analyze8.py), because test data never gives a decision word.

Everything is written under chain-test/ beside this file. That folder is generated: it is deleted and
rebuilt by every call (--reuse keeps the build, the schedule and the run results, and repeats the rest).
Prints one line per check. Exit status 0 only if every check passed.

Four things differ from a run on CRB (the Arm test machine). Each one is printed by the test.
- The kernels are the plain C stand-in loops of bwx8.c. The rates mean nothing.
- CPU 41 does not exist here. The copy of the schedule in chain-test/ is rewritten to another allowed CPU.
- run_bwx8.sh waits with "sleep 1" while a process runs and "sleep 2" (20 s at most per launch) while more
  than 2 tasks are runnable. It has no setting that shortens these waits. The test puts a "sleep" that
  returns after 0.02 s first in PATH. The script itself is not changed: chain-test/run_bwx8.sh is a link to it.
- The counter steps CS, CM and C4 use the generic hardware events cycles and instructions of this machine
  (perf type 0), not the Arm event codes. If they cannot be opened, the test says so and leaves the steps out.
"""
import argparse, datetime, glob, html, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
CRB = os.path.normpath(os.path.join(HERE, '..', '..'))
X = os.path.join(CRB, 'tmp', 'agent-scratch', 'bwx8-2026-11-14')
C = os.path.join(HERE, 'chain-test')
FONTS = os.path.join(CRB, 'tmp', 'agent-scratch', 'spec-row-2026-11-11', 'fonts')
CFLAGS = ('-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 '
          '-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4').split()        # the flags of build8.sh
STEPS = ['B6W', 'S2', 'S4', 'P3G', 'P3', 'S3G', 'S3', 'BIN']
COUNTER_STEPS = ['CS', 'CM', 'C4']
SELECT = 'oldread@8M'
PMU = dict(BWX_PMU_TYPE='0', BWX_EVENTS='cycles=0x0,instructions=0x1')
USES = ['P3G', 'S3G', 'BIN:oldread@8M', 'CS:oldread@8M:first', 'CS:oldread@8M:fourth',
        'CM:rate:first', 'CM:rate:fourth', 'CM:history:first', 'CM:history:fourth',
        'CM:interaction:first', 'CM:interaction:fourth']
sys.path.insert(0, HERE)
FAILS = []


def check(name, ok, detail=''):
    print('%s  %s%s' % ('ok  ' if ok else 'FAIL', name, '  [%s]' % str(detail)[:600] if detail and not ok else ''))
    if not ok:
        FAILS.append(name)
    return ok


def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, **kw)


def loadavg():
    with open('/proc/loadavg') as fh:
        return ' '.join(fh.read().split()[:4])


# ---------------------------------------------------------------- build, schedule, run

def build():
    os.makedirs(C, exist_ok=True)
    cmd = ['gcc'] + CFLAGS + ['-o', os.path.join(C, 'bwx8'), os.path.join(X, 'bwx8.c')]
    r = run(cmd)
    check('gcc builds bwx8.c (stand-in kernels)', r.returncode == 0, r.stderr)
    st = run([os.path.join(C, 'bwx8'), '--selftest'])
    check('bwx8 --selftest of the local build: status 0', st.returncode == 0, st.stdout[-300:] + st.stderr[-300:])
    with open(os.path.join(C, 'build.txt'), 'w') as fh:       # run_bwx8.sh copies this file into every result folder
        fh.write('## LOCAL TEST BUILD by test_chain8.py (stand-in kernels, not the CRB build of build8.sh)\n'
                 '## utc=%s load_before=%s\n## cmd=%s\n## compiler messages:\n%s## compiler messages end\n'
                 % (datetime.datetime.utcnow().strftime('%FT%TZ'), loadavg(), ' '.join(cmd), r.stderr))
    return r.returncode == 0


def other_cpu():
    """An allowed CPU that is not the controller CPU 0 and not CPU 2: the stand-in for CPU 41."""
    ok = sorted(c for c in os.sched_getaffinity(0) if c <= 119 and c not in (0, 2))
    return ok[len(ok) // 2] if ok else None


def schedule(div, alt):
    r = run([sys.executable, os.path.join(X, 'schedule8.py'), '--test-divisor', str(div), '--select', SELECT,
             '--out', os.path.join(C, 'sched')])
    check('schedule8.py --test-divisor %d --select %s: status 0' % (div, SELECT), r.returncode == 0, r.stderr)
    n = 0
    for fn in glob.glob(os.path.join(C, 'sched', 's?', '*.tsv')) + glob.glob(os.path.join(C, 'sched', 's?', '*', '*.plan')):
        with open(fn) as fh:
            old = fh.read()
        new = re.sub(r'(--cpus |\bcpu=|\bcpu|\t)41\b', lambda m: m.group(1) + str(alt), old)
        if new != old:
            n += 1
            with open(fn, 'w') as fh:
                fh.write(new)
    left = run(['grep', '-rlE', r'(--cpus |cpu=|\t)41\b', os.path.join(C, 'sched')]).stdout.strip()
    check('the copy of the schedule uses CPU %d in place of CPU 41 (%d files rewritten)' % (alt, n), n > 0 and not left, left)


def read_schedule(counter):
    """{(step, session): [dict(idx, tag, cpu, trials)]} of the schedule in chain-test/sched."""
    out = {}
    for ses in (1, 2):
        for step in STEPS + (COUNTER_STEPS if counter else []):
            rows = []
            with open(os.path.join(C, 'sched', 's%d' % ses, step + '.tsv')) as fh:
                for line in fh.read().splitlines()[1:]:
                    idx, tag, cpu, nbytes, plan, args = line.split('\t')
                    trials = 0
                    if plan != '-':
                        with open(os.path.join(C, 'sched', 's%d' % ses, step, plan)) as ph:
                            trials = sum(1 for x in ph if x.strip() and not x.startswith('#'))
                    rows.append(dict(idx=int(idx), tag=tag, cpu=int(cpu), trials=trials))
            out[step, ses] = rows
    return out


def counters_open():
    """Can this machine open the two generic hardware events for one thread without root?"""
    plan = os.path.join(C, 'probe.plan')
    with open(plan, 'w') as fh:
        fh.write('# bwx8-plan v1\n# step=CS session=1 cpu=2 bytes=8388608 proc=0 test=1\n'
                 '# trial cond rep prev pfx pred tgt nwin win_ms count bins\n'
                 '0 probe 1 - oldread@8M:4 - oldread@8M 1 1 read 0\n')
    r = run([os.path.join(C, 'bwx8'), '--trial', '--cpus', '2', '--bytes', '8388608', '--plan', plan,
             '--pmu-type', PMU['BWX_PMU_TYPE'], '--events', PMU['BWX_EVENTS']])
    rows = [x.split(',') for x in r.stdout.splitlines() if x.startswith('C,')]
    return r.returncode == 0 and bool(rows) and all(v.isdigit() and int(v) > 0 for v in rows[0][6:])


def run_sessions(steps, counter):
    os.makedirs(os.path.join(C, 'bin'), exist_ok=True)
    shim = os.path.join(C, 'bin', 'sleep')
    with open(shim, 'w') as fh:
        fh.write('#!/bin/sh\n# test_chain8.py: shortens the waits of run_bwx8.sh in the local test\nexec /usr/bin/sleep 0.02\n')
    os.chmod(shim, 0o755)
    link = os.path.join(C, 'run_bwx8.sh')
    if not os.path.islink(link):
        os.symlink(os.path.join(X, 'run_bwx8.sh'), link)       # the script takes sched/ and build.txt from the folder of $0
    env = {k: v for k, v in os.environ.items() if k not in ('_PINNED', 'SESSION1_END', 'RESERVE', 'BWX8_SHA256')}
    env.update(PATH=os.path.join(C, 'bin') + ':' + env['PATH'], STOP_AT='none',
               BWX8_MARKER=os.path.join(C, 'no-marker-file'), BWX8_STOPFILE=os.path.join(C, 'no-stop-file'),
               BWX8_BIN=os.path.join(C, 'bwx8'), BWX8_RESULTS=os.path.join(C, 'results'))
    if counter:
        env.update(PMU)
    early = dict(env, SESSION='2', SESSION1_END=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'))
    r = run([link, 'B6W'], env=early)
    check('run_bwx8.sh refuses session 2 when SESSION1_END is now: status 2, no result folder',
          r.returncode == 2 and not os.path.isdir(os.path.join(C, 'results')), (r.returncode, r.stderr[-200:]))
    for ses in (1, 2):
        e = dict(env, SESSION=str(ses))
        if ses == 2:
            e['SESSION1_END'] = (datetime.datetime.utcnow() - datetime.timedelta(hours=4)).strftime('%Y-%m-%dT%H:%MZ')
        t0, before = time.time(), loadavg()
        r = run([link] + steps, env=e)
        with open(os.path.join(C, 'run-s%d.log' % ses), 'w') as fh:
            fh.write(r.stdout + '\n---- stderr ----\n' + r.stderr)
        print('#     session %d: %.0f s wall; system load before (1, 5, 15 min, runnable/total): %s; after: %s'
              % (ses, time.time() - t0, before, loadavg()))
        warn = [x for x in r.stderr.splitlines() if not x.startswith('warning: BWX8_')]
        check('run_bwx8.sh session %d, steps %s: status 0, stderr holds only the 4 test warnings' % (ses, ' '.join(steps)),
              r.returncode == 0 and not warn and len(r.stderr.splitlines()) == 4, (r.returncode, warn[:5]))


def folders_of(steps):
    out = {}
    for ses in (1, 2):
        for step in steps:
            out[step, ses] = sorted(glob.glob(os.path.join(C, 'results', 'bwx8-%s-s%d-*' % (step, ses))))
    return out


def check_outputs(sched, folders):
    """Every scheduled process has its output, and the counts equal the schedule."""
    bad, nproc, ntrial = [], 0, 0
    for (step, ses), rows in sorted(sched.items()):
        fs = folders.get((step, ses), [])
        if len(fs) != 1:
            bad.append('%s s%d: %d result folders' % (step, ses, len(fs)))
            continue
        with open(os.path.join(fs[0], step + '.csv')) as fh:
            text = fh.read()
        parts = re.split(r'(?m)^(?=-- step )', text)[1:]
        if '-- killed ' in text or '-- failed ' in text:
            bad.append('%s s%d: a process was killed or failed' % (step, ses))
        heads = [(int(re.search(r' idx (\d+) ', p).group(1)), re.search(r' tag (\S+) ', p).group(1)) for p in parts]
        if heads != [(r['idx'], r['tag']) for r in rows]:
            bad.append('%s s%d: %d header lines for %d scheduled processes, or another order' % (step, ses, len(heads), len(rows)))
            continue
        for p, r in zip(parts, rows):
            lines = p.splitlines()
            s, e = sum(x.startswith('S,') for x in lines), sum(x.startswith('E,') for x in lines)
            t = sum(x.startswith('T,') for x in lines)
            if (step == 'B6W' and t != 52) or (step != 'B6W' and not (s == e == r['trials'])):
                bad.append('%s s%d idx %d: %d S rows, %d E rows, %d T rows; the plan has %d trials' % (step, ses, r['idx'], s, e, t, r['trials']))
            if ' --cpus %d ' % r['cpu'] not in lines[0] + ' ':
                bad.append('%s s%d idx %d: the header line does not have --cpus %d' % (step, ses, r['idx'], r['cpu']))
            nproc += 1
            ntrial += r['trials']
        for name in ('env.txt', 'launches.txt', 'stderr.txt', 'schedule.tsv', 'build.txt'):
            if not os.path.isfile(os.path.join(fs[0], name)):
                bad.append('%s s%d: %s is missing' % (step, ses, name))
    check('every scheduled process has its complete output (%d processes, %d trials, %d steps x sessions)'
          % (nproc, ntrial, len(sched)), not bad, bad[:6])
    return nproc, ntrial


# ---------------------------------------------------------------- analysis and report of the test run

DECISION_PHRASES = ('equivalent', 'contradicted', 'undecided', 'supported', 'repeatable', 'not distinguished from variation',
                    'signs differ between units', 'compatible', 'contrary', 'precision insufficient', 'resolved difference',
                    'not established', 'equivalence established', 'crossed between', 'not crossed', 'not resolved',
                    'meets its equivalence margin', 'feasible', 'incomplete')
SECTIONS = ('Short version', 'Words used here', 'System load before each process', 'Stage 2', 'Stage 4',
            'Exclusion table', 'Processes that did not end, and scheduled work that remains', 'What explains what', 'References')
OPTIONAL = {'P3': 'P3: old read against the load-only kernels on one allocation', 'S3': 'Stage 3', 'P3G': 'Gates',
            'B6W': 'B6W', 'CS': 'Counters'}


def visible_text(page, drop_rules=True):
    """The text of the page without tags, without the style block and without titles of SVG marks. With
    drop_rules the fixed texts that state a rule (word list, class "rule") are left out as well."""
    page = re.sub(r'(?s)<style>.*?</style>', ' ', page)
    if drop_rules:
        page = re.sub(r'(?s)<ul class="words">.*?</ul>', ' ', page)
        page = re.sub(r'(?s)<(p|div|li|span|td) class="rule">.*?</\1>', ' ', page)
    return html.unescape(re.sub(r'<[^>]+>', ' ', page))


def light_only(page):
    """No dark background: one colour scheme, no dark media query, and every background colour is light."""
    bad = []
    if 'prefers-color-scheme' in page or 'color-scheme:dark' in page.replace(' ', ''):
        bad.append('a dark colour scheme is named')
    if not re.search(r'body\{[^}]*background:#ffffff', page):
        bad.append('the body has no white background')
    marks = re.sub(r'<(i|b|u|em) style="[^"]*"></\1>', '', page)          # legend marks of 11 px are not a background
    for m in re.finditer(r'background(?:-color)?:\s*(#[0-9a-fA-F]{3,6})', marks):
        h = m.group(1)[1:]
        h = ''.join(c * 2 for c in h) if len(h) == 3 else h
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        if 0.2126 * r + 0.7152 * g + 0.0722 * b < 200:
            bad.append('background %s' % m.group(1))
    for m in re.finditer(r'<rect[^>]*fill="(#[0-9a-fA-F]{6})"[^>]*>', page):
        h = m.group(1)[1:]
        w = re.search(r'width="([0-9.]+)"', m.group(0))
        if sum(int(h[i:i + 2], 16) for i in (0, 2, 4)) < 150 and w and float(w.group(1)) > 300:
            bad.append('a dark rectangle wider than 300 px')
    return bad


def analyse_test(sched, folders, nproc, ntrial, counter):
    import analyze8 as A
    steps = sorted({k[0] for k in sched})
    allf = [f for k in sorted(folders) for f in folders[k]]
    src = [f for k in sorted(folders) if k[0] in ('S2', 'S3') for f in folders[k]]
    margins = os.path.join(C, 'margins.json')
    uses = [u for u in USES if counter or not u.startswith(('CS', 'CM'))]
    cmd = [sys.executable, os.path.join(HERE, 'analyze8.py'), 'forecast'] + src
    for u in uses:
        cmd += ['--use', u]
    r = run(cmd + ['-o', margins])
    with open(os.path.join(C, 'forecast.txt'), 'w') as fh:
        fh.write(r.stdout + r.stderr)
    m = json.load(open(margins)) if r.returncode == 0 else {}
    check('analyze8.py forecast from the S2 and S3 folders writes margins.json with %d uses (test data: no forecast word)' % len(uses),
          r.returncode == 0 and sorted(m.get('uses', {})) == sorted(uses) and m.get('test') is True
          and all(u['forecast'] is None and u['margin'] is not None for u in m['uses'].values()), r.stderr[-300:] or r.stdout[-300:])
    summary = os.path.join(C, 'summary.json')
    r = run([sys.executable, os.path.join(HERE, 'analyze8.py'), 'summary'] + allf + ['--margins', margins, '-o', summary])
    with open(os.path.join(C, 'summary.txt'), 'w') as fh:
        fh.write(r.stdout + r.stderr)
    if not check('analyze8.py summary with the margins file: status 0', r.returncode == 0, r.stderr[-400:]):
        return
    s = json.load(open(summary))
    check('summary: test_data is true and the banner is set', s['test_data'] is True and s['banner'] == A.BANNER)
    want = {}
    for (step, ses), rows in sched.items():
        w = want.setdefault(step, [0, 0])
        w[0] += len(rows)
        w[1] += sum(r['trials'] for r in rows)
    got = {k: [v['processes'], v['trials']] for k, v in s['counts'].items()}
    check('summary: processes and trials of every step equal the schedule (%d and %d)' % (nproc, ntrial), got == want, (got, want))
    check('summary: no process is counted as not ended, none is replaced',
          all(v['processes_not_ended'] == 0 for v in s['counts'].values()) and not s['replaced'])
    check('summary: no trial is rejected', all(v['rejected'] == 0 for v in s['counts'].values()),
          {k: v['rejected'] for k, v in s['counts'].items()})
    print('#     trials with a disturbed mark, per step: %s' % {k: v['disturbed'] for k, v in sorted(s['counts'].items())})
    check('summary: every gate step of the run has its uses evaluated', all(
        s['gates'].get(g, {}).get('uses') for g in A.GATE_STEPS if g in steps), sorted(s['gates']))
    out = os.path.join(C, 'report-test.html')
    r = run([sys.executable, os.path.join(HERE, 'report8.py')] + allf + ['--margins', margins, '-o', out])
    if not check('report8.py on the test run: status 0', r.returncode == 0, r.stderr[-800:]):
        return
    page = open(out).read()
    check_page('test page', page, steps, test=True)
    return out


def check_page(name, page, steps, test):
    txt = visible_text(page)
    heads = [html.unescape(re.sub(r'<[^>]+>', '', h)) for h in re.findall(r'(?s)<h2[^>]*>(.*?)</h2>', page)]
    need = list(SECTIONS) + [v for k, v in OPTIONAL.items() if k in steps]
    miss = [x for x in need if not any(h.split('. ', 1)[-1].startswith(x) for h in heads) and not (x == 'Short version' and 'Short version.' in txt)]
    check('%s: every required section is present (%d)' % (name, len(need)), not miss, miss)
    check('%s: light background only' % name, not light_only(page), light_only(page))
    check('%s: self-contained (no script, no link to a file, no image file)' % name,
          not re.search(r'<script|<link|<img|<iframe|url\(|src=|@import', page))
    check('%s: inline SVG charts are present (%d)' % (name, page.count('<svg')), page.count('<svg') >= 6)
    refs = set(re.findall(r'\[Ref(\d+)\]', txt))
    listed = set(re.findall(r'<li>\[Ref(\d+)\]', page))
    check('%s: every [RefN] in the text is in the reference list' % name, refs and refs <= listed, sorted(refs - listed))
    banner = 'TEST DATA: stand-in kernels or shortened durations; no decision'
    if test:
        check('%s: the TEST DATA banner is present' % name, banner in txt)
        check('%s: no decision value is printed (no element of class "dec")' % name, 'class="dec"' not in page)
        found = sorted({p for p in DECISION_PHRASES if re.search(r'\b%s\b' % re.escape(p), txt)})
        check('%s: no decision word in the text outside the fixed rule texts' % name, not found, found)
        check('%s: "What explains what" gives no allowed conclusion' % name, 'class="concl"' not in page)
    else:
        check('%s: no TEST DATA banner' % name, banner not in txt)
    return txt


# ---------------------------------------------------------------- the synthetic example (no test mark)

SYN_NOTE = ('SYNTHETIC DATA: every rate on this page was made up by test_chain8.py to show the report with decision words. '
            'Nothing on this page was measured on CRB or on any other machine.')


def synthetic():
    """Result folders with realistic rates and test=0, written with the builder of test_analyze8.py:
    old read 67 GB/s flat; new read 85 GB/s at 1 MiB falling to 67.7 GB/s at 8 MiB; a predecessor effect in
    Stage 3; one process with a disturbed trial; one process killed and continued; one step stopped."""
    import analyze8 as A
    import test_analyze8 as T
    OLD, NEW, ASM = A.OLD, A.NEW, A.ASM
    root = os.path.join(C, 'synthetic')
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    RATE = {OLD: {T.K32: 66.8, T.M1: 67.05, T.M4: 67.0, T.M8: 67.0, T.M16: 66.0},
            NEW: {T.K32: 133.2, T.M1: 85.0, T.M4: 74.4, T.M8: 67.7, T.M16: 65.0},
            ASM: {T.K32: 134.0, T.M1: 86.0, T.M4: 75.0, T.M8: 68.5, T.M16: 65.5}}
    faster41 = lambda c: 2.0 if c['cpu'] == 41 and c['kernel'] != OLD and c['size'] == T.M8 else 0.0   # CPU 41: higher load-only rate at 8 MiB

    def s2_rate(c):
        r = RATE[c['kernel']][c['size']] + faster41(c) + T.noise(0.04, 'allocation', c['session'], c['cpu'], c['proc'])
        if (c['session'], c['cpu'], c['size'], c['kernel'], c['rep_set'], c['n']) == (1, 2, T.M4, NEW, 3, 2):
            r -= 6.0                                                                 # the disturbed trial
        return r + T.noise(0.012, c['session'], c['cpu'], c['proc'], c['n'], c['phase'], c['widx'])

    def disturbed(L, cpu, size, rep_set, kernel):
        if (cpu, size, rep_set, kernel) == (2, T.M4, 3, NEW):
            L = T.edit(L, 'E,2,', lambda line: T.setf(T.setf(line, 5, 3), 3, int(int(line.split(',')[2]) * 0.93)))
        return L
    sizes = (T.K32, T.M1, T.M4, T.M8, T.M16)
    f1 = T.s2(root, 1, s2_rate, sizes=sizes, hook=disturbed)
    f2 = T.s2(root, 2, s2_rate, sizes=sizes)
    full = sched_rows(f2, 'S2')
    f2b = T.stopped(f2, 'S2', 100, 2, 'bwx8-S2-s2-20261115T023000Z')              # process idx 101 killed in trial 2, then continued
    for f, start in ((f2, 0), (f2b, 101)):
        write_sched(f, full, start)

    def s4_rate(c):
        k, w = c['kernel'], c['widx']
        r = {OLD: 67.0, NEW: 67.7, ASM: 68.6}[k] + (1.9 if c['cpu'] == 41 and k != OLD else 0.0)
        key = (k, c['session'], c['cpu'], c['proc'])            # proc is the idx of the launch line
        if key == (ASM, 1, 2, 9) and w >= 80:
            r += 2.3
        if key == (ASM, 2, 2, 6) and 30 <= w < 120:
            r += 2.2
        if key == (NEW, 1, 2, 14) and w >= 150:
            r += 1.5
        return r + T.noise(0.03, 'S4', c['session'], c['cpu'], c['proc'], w)
    for ses in (1, 2):
        procs, idx = [], 0
        for i in range(3):
            for cpu in ((2, 41) if ses == 1 else (41, 2)):
                for k in A.KERNELS:
                    idx += 1
                    procs.append(T.process('S4', ses, cpu, idx, [T.trial('K=%s|S=8M' % k, 1, T.sp(k, T.M8), nwin=200)], s4_rate,
                                           plan=(('kernel', k), ('size', T.M8))))
        rows = [(int(p[0].split()[6]), p[0].split()[8]) for p in procs]
        if ses == 2:                                                                 # a host stop during process 16 of 18
            cut = procs[15]
            keep = cut[:[i for i, x in enumerate(cut) if x.startswith('W,0,target,61,')][0]]
            procs = procs[:15] + [keep + ['W,0,target,61,asmr-- killed tag t16 status 4 utc 03:10:00']]
        f = T.put(root, 'bwx8-S4-s%d-20261115T0%d4000Z' % (ses, ses), 'S4', procs)
        write_sched(f, rows, 0)

    def s3_effect(c):
        if c['phase'] != 'target' or c['tgt_kernel'] != OLD or '@1M' in c['pred']:
            return 0.0
        return {NEW: -1.5, ASM: -3.2}.get(c['pred'].split('@')[0], 0.0) * (1.0, 0.45, 0.15, 0.0)[c['widx']]
    for ses in (1, 2):
        T.s3(root, ses, s3_effect, seed=20261115, amp=0.02)
        quiet = lambda c: T.MEAN[c['kernel']] + T.noise(0.008, 'gate', c['session'], c['cpu'], c['proc'], c['n'], c['phase'], c['widx'])
        T.prefix_gate(root, 'S3G', ses, quiet)
        T.prefix_gate(root, 'P3G', ses, quiet)
        T.b6w(root, ses)
        T.mode_gate(root, 'CS', ses)

        def p3_rate(c):
            k, p, cpu = c['kernel'], c['p'], c['cpu']
            r = {OLD: 67.0, NEW: 67.3 + 0.5 * p, ASM: 68.4 + (0.3 if cpu == 2 else 0.5) * p}[k]
            if k == OLD and cpu == 41:
                r += 0.12 * p                                                       # old read follows the load-only rate on CPU 41
            if (c['session'], cpu, p, k, c['rep'], c['phase'], c['widx']) == (2, 2, 4, NEW, 3, 'target', 0):
                r -= 0.6                                                            # one unstable trial
            return r + T.noise(0.01, 'P3', c['session'], cpu, c['proc'], c['n'], c['phase'], c['widx'])
        T.p3(root, ses, p3_rate)
    folders = sorted(glob.glob(os.path.join(root, 'bwx8-*')))
    for f in folders:
        if not os.path.isfile(os.path.join(f, 'schedule.tsv')):
            step = os.path.basename(f).split('-')[1]
            write_sched(f, sched_rows(f, step), 0)
    return root, folders


def sched_rows(folder, step):
    with open(os.path.join(folder, step + '.csv')) as fh:
        return [(int(x.split()[6]), x.split()[8]) for x in fh if x.startswith('-- step ')]


def write_sched(folder, rows, start):
    """schedule.tsv and the settings line of env.txt, as run_bwx8.sh leaves them in a result folder."""
    with open(os.path.join(folder, 'schedule.tsv'), 'w') as fh:
        fh.write('idx\ttag\tcpu\tbytes\tplan\targs\n' + ''.join('%d\t%s\t-\t-\t-\t-\n' % r for r in rows))
    with open(os.path.join(folder, 'env.txt'), 'w') as fh:
        fh.write('## SYNTHETIC folder written by test_chain8.py\n## settings: session=- from=%d\n' % start)


def analyse_synthetic():
    root, folders = synthetic()
    s2 = [f for f in folders if '-S2-' in f]
    margins = os.path.join(root, 'margins.json')
    cmd = [sys.executable, os.path.join(HERE, 'analyze8.py'), 'forecast'] + s2
    for u in ('P3G', 'S3G', 'CS:oldread@8M:first', 'CS:oldread@8M:fourth'):
        cmd += ['--use', u]
    r = run(cmd + ['-o', margins])
    m = json.load(open(margins)) if r.returncode == 0 else {'uses': {}}
    check('synthetic: forecast from the Stage 2 folders gives a margin and the word "feasible" for 4 uses',
          len(m['uses']) == 4 and all(u['forecast'] == 'feasible' for u in m['uses'].values()), r.stdout[-400:] + r.stderr[-300:])
    out = os.path.join(C, 'report-synthetic-example.html')
    r = run([sys.executable, os.path.join(HERE, 'report8.py')] + folders + ['--margins', margins, '--note', SYN_NOTE, '-o', out])
    if not check('report8.py on the synthetic folders: status 0', r.returncode == 0, r.stderr[-800:]):
        return None
    page = open(out).read()
    steps = sorted({os.path.basename(f).split('-')[1] for f in folders})
    txt = check_page('synthetic page', page, steps, test=False)
    check('synthetic page: the banner says that the data are synthetic', 'SYNTHETIC DATA' in txt.split('Short version.')[0])
    decs = [html.unescape(x) for x in re.findall(r'<span class="dec">(.*?)</span>', page)]
    need = ['equivalent', 'meets its equivalence margin', 'supported', 'repeatable', 'not distinguished from variation', 'yes', 'pass',
            'equivalence established', 'crossed between 8 and 16 MiB', 'compatible', 'contrary', 'Insufficient data']
    check('synthetic page: the decision words appear (%d decision values, %d different)' % (len(decs), len(set(decs))),
          all(w in decs for w in need), [w for w in need if w not in decs])
    check('synthetic page: "What explains what" prints an allowed conclusion for 4 rows and "Insufficient data" for the other 3',
          page.count('class="concl"') == 4 and page.split('What explains what')[-1].count('<b>Insufficient data.</b>') == 3,
          (page.count('class="concl"'), page.split('What explains what')[-1].count('<b>Insufficient data.</b>')))
    m = re.search(r'At 8 MiB, with each kernel as its own preparation, new read was \+([0-9.]+) % to \+([0-9.]+) % faster', txt)
    check('synthetic page: the Short version gives the 8 MiB gain from the analysis (about 1 % on CPU 2, about 4 % on CPU 41)',
          bool(m) and 0.8 < float(m.group(1)) < 1.3 and 3.7 < float(m.group(2)) < 4.4, m and m.groups())
    check('synthetic page: the result sentence of design line 222 is printed for 4 CPU and session cells',
          len(re.findall(r'old read was 6[67]\.\d\d GB/s and new read was 6[789]\.\d\d GB/s at 8 MiB', txt)) == 4)
    check('synthetic page: the killed and continued process is listed with the folder that replaces it',
          'status 143' in txt and 'bwx8-S2-s2-20261115T023000Z' in txt and 'is used in its place' in txt)
    check('synthetic page: the stopped step S4 of session 2 shows the scheduled work that remains (idx 16 to 18)',
          '3 processes: idx 16 to 18' in txt and 'status 4' in txt)
    check('synthetic page: the disturbed trial is in the exclusion table and changes the filtered count only',
          '3 involuntary context switches' in txt and '5 / 6' in txt)
    check('synthetic page: a transition of the sustained traces is listed', bool(re.search(r'assembly read\s+2\s+1\s+9\s+2[34]\.\d+\s+68\.\d+\s+7[01]\.\d+', txt)))
    for k, n in (('Stage 2 dumbbells', 'Old-read, new-read and assembly-read rate by buffer size'), ('P1 chart', 'P1: the six values'),
                 ('decomposition bars', 'The new-read term and the old-read term'), ('sustained traces', 'Step S4: the rate of every window'),
                 ('P3 scatter', 'P3: fourth-window old-read rate'), ('P3 trial traces', 'first-window and fourth-window rate of every trial'),
                 ('Stage 3 traces', 'target rate in the four windows after each predecessor'), ('Stage 3 contrasts', 'the six process values of each primary contrast'),
                 ('gate chart', 'Gate step P3G'), ('B6W chart', 'B6W: paired difference'), ('load chart', 'System load before each process')):
        check('synthetic page: chart present: %s' % k, bool(re.search(r'aria-label="[^"]*' + re.escape(n), page)))
    return out


# ---------------------------------------------------------------- rendering with the headless Chrome

CHROME = os.path.expanduser('~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell')
PIECE = 1500        # px of page height per screenshot


def chrome(work, mode, url, n=0):
    for d in ('home', 'tmp', 'profile-%d' % n, 'fontconfig'):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    conf = os.path.join(work, 'fontconfig', 'fonts.conf')
    with open(conf, 'w') as fh:
        fh.write('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>%s</dir><dir>/usr/share/fonts</dir>'
                 '<alias><family>monospace</family><prefer><family>DejaVu Sans Mono</family></prefer></alias><cachedir>%s</cachedir></fontconfig>'
                 % (FONTS, os.path.join(work, 'home', 'fc-cache')))
    env = dict(PATH='/usr/bin:/bin', HOME=os.path.join(work, 'home'), XDG_CONFIG_HOME=os.path.join(work, 'home', '.config'),
               XDG_CACHE_HOME=os.path.join(work, 'home', '.cache'), TMPDIR=os.path.join(work, 'tmp'), FONTCONFIG_FILE=conf)
    return run(['timeout', '120', CHROME, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--no-first-run',
                '--disable-background-networking', '--disable-component-update', '--disable-sync', '--disable-extensions',
                '--disable-crash-reporter', '--disable-breakpad', '--host-resolver-rules=MAP * ~NOTFOUND',
                '--user-data-dir=' + os.path.join(work, 'profile-%d' % n)] + mode + [url], env=env)


def render(page_path, name):
    """Screenshots of the whole page in pieces of PIECE px. The copies that are rendered have every <details> open.
    The height is read with a script that only the measuring copy holds."""
    work = os.path.join(C, 'render')
    out = os.path.join(work, name)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    page = open(page_path).read().replace('<details>', '<details open>')
    probe = os.path.join(out, 'measure.html')
    with open(probe, 'w') as fh:
        fh.write(page.replace('</body>', '<script>document.body.setAttribute("data-h", document.documentElement.scrollHeight);'
                                         'document.body.setAttribute("data-w", document.documentElement.scrollWidth)</script></body>'))
    r = chrome(work, ['--window-size=1000,1500', '--dump-dom'], 'file://' + probe)
    m = re.search(r'data-h="(\d+)" data-w="(\d+)"', r.stdout)
    if not check('%s: the headless Chrome renders the page' % name, r.returncode == 0 and bool(m), r.stderr[-300:]):
        return
    h, w = int(m.group(1)), int(m.group(2))
    check('%s: the page is not wider than the 1000 px window (no horizontal scroll)' % name, w <= 1000, w)
    n = (h + PIECE - 1) // PIECE
    for k in range(n):
        piece = os.path.join(out, 'piece.html')
        with open(piece, 'w') as fh:
            fh.write(page.replace('</style>', 'html{overflow:hidden}body{position:relative;top:-%dpx}</style>' % (k * PIECE), 1))
        chrome(work, ['--hide-scrollbars', '--window-size=1000,%d' % PIECE, '--screenshot=' + os.path.join(out, 'page-%02d.png' % k)], 'file://' + piece)
    os.remove(os.path.join(out, 'piece.html'))
    got = len(glob.glob(os.path.join(out, 'page-*.png')))
    check('%s: %d screenshots of %d px height cover the page height of %d px (in %s)' % (name, n, PIECE, h, out), got == n, got)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--divisor', type=int, default=150, help='--test-divisor of schedule8.py (default 150: windows of 2 ms)')
    ap.add_argument('--reuse', action='store_true', help='keep the build, the schedule and the run results of the last call')
    ap.add_argument('--no-render', action='store_true', help='do not render the two pages with the headless Chrome')
    a = ap.parse_args()
    t0 = time.time()
    print('# system load at the start (1, 5, 15 min, runnable/total): %s; CPUs allowed: %d' % (loadavg(), len(os.sched_getaffinity(0))))
    alt = other_cpu()
    if alt is None or 2 not in os.sched_getaffinity(0) or 0 not in os.sched_getaffinity(0):
        check('this machine has CPU 0, CPU 2 and one more CPU', False)
        return 1
    reuse = a.reuse and os.path.isdir(os.path.join(C, 'results'))
    if not reuse:
        shutil.rmtree(C, ignore_errors=True)
        if not build():
            return 1
        schedule(a.divisor, alt)
    counter = counters_open()
    print('#     counter steps %s: %s' % (' '.join(COUNTER_STEPS), 'run with the generic hardware events %s of perf type %s (stand-in for the Arm event codes)'
                                          % (PMU['BWX_EVENTS'], PMU['BWX_PMU_TYPE']) if counter else
                                          'NOT RUN: this machine cannot open the hardware events without root, and a software event cannot stand in for cycles and instructions'))
    steps = STEPS + (COUNTER_STEPS if counter else [])
    if not reuse:
        run_sessions(steps, counter)
    sched = read_schedule(counter)
    folders = folders_of(steps)
    nproc, ntrial = check_outputs(sched, folders)
    pages = [('test', analyse_test(sched, folders, nproc, ntrial, counter)), ('synthetic', analyse_synthetic())]
    if not a.no_render:
        if os.path.isfile(CHROME):
            for name, path in pages:
                if path:
                    render(path, name)
        else:
            check('the headless Chrome exists (%s)' % CHROME, False)
    print('# %.0f s in all' % (time.time() - t0))
    print('%d checks failed: %s' % (len(FAILS), FAILS) if FAILS else 'all checks passed')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
