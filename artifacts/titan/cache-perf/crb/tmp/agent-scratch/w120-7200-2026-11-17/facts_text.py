#!/usr/bin/env python3
"""facts_text.py - text and tables of FACTS.md, and the verdict object of facts.json.

Used by build_facts.py: render(D) returns (verdicts, text of FACTS.md).
The templates below hold words only. Every number is formatted from the data that build_facts.py collected.
Sentences that depend on the pattern of the data are guarded by `need(...)`: the script stops when the data
do not show the pattern that the sentence states.
"""
import os
import re
import statistics
from decimal import Decimal, ROUND_HALF_UP

import facts_data as fd
from facts_data import R, S, rel, sel, rng, overlap, gap, width_pct

W15, K13 = fd.W15, fd.K13
BW12 = ('L-1', 'L-2', 'L-3', 'L-4')            # baseline row and supporting rows of runner bwx12
BW11 = ('R0', 'R0b')                           # rows of the other binary bwx11
BWX = ('B7a', 'B7b', 'C3a', 'C3b')             # rows of the first runner bwx
DIFFERS = 'differs between the 8000 MT/s boot and the 7200 MT/s boot'
SAME = 'no difference seen'
NO_READ = 'Insufficient data: no 8000 MT/s run of kernel read with bwx12'
ADDED = 'added after the first numbers were seen'
NOT_PLAN = 'not part of the plan fixed before the run'
H1_MEAS = ('The like.spec line, run in turn from an idle start and directly after part A, at least 3 times each, in '
           'one boot, would resolve it (the measurement of hypothesis H1 in section 6).')
FIRST = 'none (first interval of the process)'
# rule V4, part L: "asmread stands in for the new read kernel (same loop: 8 ldp q per 256 B). Say so in the row label."
STANDIN = 'asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B)'
# Rules F2 points 2 and 3 against rules V1 point 2, V2 point 4 and V4 (part C list): see decision (r) in section 2.
F2_NOTE = ('This comparison of part C with 8000 MT/s follows rules V1 point 2, V2 point 4 and V4. Rule F2 points 2 '
           'and 3 would present part C at 7200 MT/s only (decision (r) in section 2).')


def need(cond, what):
    if not cond:
        raise SystemExit('facts_text.py: the data do not show the pattern of a sentence: ' + what)


def _q(x, step):
    """Decimal rounding, half up. Rounding to 6 places first removes binary floating-point noise."""
    return str(Decimal(repr(round(x, 6))).quantize(Decimal(step), rounding=ROUND_HALF_UP))


def g(x):
    return _q(x, '0.01')


def sp(a):
    return '%s to %s' % (g(a['lo']), g(a['hi']))


def pc(x):
    return _q(x, '0.1')


def pcr(ds):
    """Lowest and highest of a list of percent values, as text with the unit."""
    lo, hi = pc(min(ds)), pc(max(ds))
    return ('%s %%' % lo) if lo == hi else '%s %% to %s %%' % (lo, hi)


def hm(t):
    return t.strftime('%H:%M:%S')


RERUN_DAY = '2026-11-17'      # a time without a date is on this day (first lines of the sheet)
OTHER_DAY = set()             # every time of day that the sheet prints for another day


def hmd(t):
    """Date and time. Used for every time that is not on the day of the rerun, and where the date helps."""
    if t.strftime('%Y-%m-%d') != RERUN_DAY:
        OTHER_DAY.add(t.strftime('%H:%M:%S'))
    return t.strftime('%Y-%m-%d %H:%M:%S')


def check_dates(text):
    """A time of another day must carry its date in the same sentence or table cell (rule in the first lines of
    the sheet). Returns the pieces of text that break the rule."""
    bad = []
    for line in text.split('\n'):
        for piece in re.split(r'\.\s+|\s\|\s', line):
            if any(t in piece for t in OTHER_DAY) and not re.search(r'\b2026-\d\d-\d\d\b', piece):
                bad.append(piece)
    return bad


def dur(sec):
    sec = int(round(sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    if h:
        return '%d h %d min %d s' % (h, m, s)
    return ('%d min %d s' % (m, s)) if m else '%d s' % s


def nn(a, sessions=False, boots=True):
    """n as intervals / processes (/ sessions) / boots."""
    t = '%d intervals / %d process%s' % (a['n'], a['procs'], '' if a['procs'] == 1 else 'es')
    if sessions:
        t += ' / %d sessions' % a['sessions']
    if boots:
        t += ' / %d boot%s' % (a['boots'], '' if a['boots'] == 1 else 's')
    return t


def sess(rs):
    """Sessions of a list of rerun records, as text. T72C4 ran after the three sessions: it counts as an extra process."""
    rr = [r for r in rs if r['dataset'].startswith('rerun-')]      # control I and F72d12 belong to no session
    ss = sorted({r['session'] for r in rr if r['session'] is not None})
    extra = len({r['proc_key'] for r in rr if r['session'] is None})
    if len(ss) > 2 and ss == list(range(ss[0], ss[-1] + 1)):
        t = '%d sessions' % len(ss)
    elif ss:
        t = 'session%s %s' % ('' if len(ss) == 1 else 's', ' and '.join(map(str, ss)))
    else:
        t = 'no session'
    if extra:
        t += ' and %d extra process%s' % (extra, '' if extra == 1 else 'es')
    return t


def nns(rs):
    """n of rerun records as intervals / processes / sessions / boots (rule V1 point 1)."""
    a = rng(rs)
    return '%d interval%s / %d process%s / %s / %d boot%s' % (
        a['n'], '' if a['n'] == 1 else 's', a['procs'], '' if a['procs'] == 1 else 'es', sess(rs), a['boots'],
        '' if a['boots'] == 1 else 's')


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---' for _ in head) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    out.append('')
    return out


class Refs:
    """The file list of section 7. A file gets its number when it is registered."""

    def __init__(self):
        self.d = {}

    def add(self, path, desc):
        key = path if path.startswith('ext:') else os.path.abspath(path)
        if key not in self.d:
            self.d[key] = [len(self.d) + 1, desc]

    def __call__(self, path):
        key = path if path.startswith('ext:') else os.path.abspath(path)
        return '[Ref%d]' % self.d[key][0]


def register(D):
    ref = Refs()
    a = ref.add
    a(os.path.join(S, 'build_facts.py'), 'script: builds this sheet and facts.json (records, integrity checks)')
    a(os.path.join(S, 'facts_data.py'), 'script: parsers of the raw files, range and overlap functions')
    a(os.path.join(S, 'facts_text.py'), 'script: text, tables, statistics and verdicts of sections 0 to 3 and 7')
    a(os.path.join(S, 'facts_text4.py'), 'script: text, tables, statistics and verdicts of sections 4 to 6')
    a(os.path.join(S, 'stat_k120.py'), 'existing tool: statistics of a threads120.csv, used here as a cross-check')
    a(os.path.join(S, 'stat_bwx.py'), 'existing tool: statistics of bwx csv files, used here as a cross-check')
    a(os.path.join(S, 'baselines-and-rules.txt'), 'the fixed list of 8000 MT/s baselines and the comparison rules '
      '(V1 to V4, F1, F2), written before the run')
    a(os.path.join(S, 'review-w1.json'), 'record of the review that produced the rules (findings F1 and F9 list the '
      'differences to the 2026-11-13 procedure). Read by the author, not by the script')
    a(os.path.join(S, 'go.sh'), 'driver script of the rerun: three sessions of parts A, L, C and a fourth C process')
    a(os.path.join(S, 'ra.sh'), 'script of part A: the 120-thread part of run_kernels.sh with the binaries of 2026-11-13')
    a(os.path.join(S, 'go2.sh'), 'script of control I: the part L line twice, each time from an idle machine')
    a(os.path.join(S, 'like.spec'), 'argument line of parts L and I for rx.sh (tag a6456)')
    a(os.path.join(S, 'cfwd.spec'), 'argument line of part C, order oldread, read, asmread')
    a(os.path.join(S, 'crev.spec'), 'argument line of part C, order asmread, read, oldread')
    a(os.path.join(S, 'local.sha'), 'sha256 list of go.sh, ra.sh and the spec files, written at launch')
    a(os.path.join(S, 'go2.sha'), 'sha256 of go2.sh, written at launch')
    a(os.path.join(S, 'base8000', 'partA-A1', 'threads120.csv'), 'copy of A1.csv with converted header lines, '
      'used only for the cross-check with stat_k120.py')
    a(os.path.join(S, 'base8000', 'partA-A3-onebuf500', 'threads120.csv'), 'copy of the three onebuf-ms500 processes '
      'of A3.csv with converted header lines, used only for the cross-check')
    a(os.path.join(W15, 'rx.sh'), 'runner script of bwx12 processes (parts L, C, I). It writes env.txt, launches.txt and '
      'stderr.txt. Read by the author. Check %d of section 1.4 compares its sha256 with the value that go.sh and '
      'go2.sh test on CRB'
      % ([c['key'] for c in D['checks']].index('sha-rx') + 1))
    a(os.path.join(W15, 'r0.sh'), 'run script of row R0. It holds the sha256 of bwx11 (line %d)' % D['rx']['R0']['env']['sha_line'])
    a(os.path.join(W15, 'FINDINGS.md'), 'facts sheet of the investigation of 2026-11-15 (sections "The question", '
      'F1, F2). Read by the author')
    a(os.path.join(K13, 'run_kernels.sh'), 'the run script of 2026-11-13 ("whole chip test"). Read by the author. '
      'Check %d of section 1.4 compares its function one() with ra.sh'
      % ([c['key'] for c in D['checks']].index('A-args') + 1))
    a(D['logs']['go']['path'], 'log of go.sh: Linux command line, governor, huge page setting, 12 state lines')
    a(D['logs']['go2']['path'], 'log of go2.sh: 6 state lines')
    for x in D['A']:
        a(x['csv'], 'part A, session %d: 24 processes, 72 interval rows' % x['session'])
        a(x['probe']['path'], 'part A, session %d: boot id, MemTotal, load, sha256 of bw_old, bw_new, ra.sh' % x['session'])
    names = dict(L='part L', C='part C', I='control I')
    for x in D['X']:
        what = '%s, %s' % (names[x['part']], x['tag'])
        a(x['csv'], what + ': rows per interval (I), per thread (T), page state (P), counters (C)')
        a(os.path.join(x['folder'], 'env.txt'), what + ': start time, Linux release, load, busiest processes, sha256 of bwx12')
        a(os.path.join(x['folder'], 'launches.txt'), what + ': launch line with load and arguments, rc line')
        a(os.path.join(x['folder'], 'stderr.txt'), what + ': error output of bwx12')
    b = D['base']
    a(os.path.join(b['A-1']['folder'], 'threads120.csv'), 'row A-1: the original whole-chip test of 2026-11-13, 24 processes')
    a(D['probe13']['path'], 'row A-1: sha256 of bw_old and bw_new, times of the 2026-11-13 run')
    a(D['probe13']['one_path'], 'one-thread part of the 2026-11-13 run (only its process count and times are used)')
    a(os.path.join(b['A-2']['folder'], 'A1.csv'), 'row A-2: 12 processes of 2026-11-13 20:50 UTC')
    a(os.path.join(b['A-3']['folder'], 'A3.csv'), 'row A-3: tags onebuf-ms500-1, -2, -3 (bw_old read)')
    a(os.path.join(b['A-2']['folder'], 'env.txt'), 'rows A-2, A-3: sha256 of bw_old and bw_new')
    for name, v in D['rx'].items():
        for t in v['secs']:
            a(os.path.join(v['folder'], t + '.csv'), 'row %s: bwx csv of process %s' % (name, t))
        if v['env']['has_binary_line']:
            a(os.path.join(v['folder'], 'env.txt'), 'row %s: start time, load, process list, sha256 of the binary' % name)
        else:
            a(os.path.join(v['folder'], 'env.txt'), 'row %s: start time, load, process list (%d lines, no sha256: the '
              'sha256 of %s is in r0.sh)' % (name, v['env']['n_lines'], fd.SHA_NAMES[v['env']['sha'][:8]]))
        a(os.path.join(v['folder'], 'launches.txt'), 'row %s: launch lines with load and arguments, rc lines' % name)
        a(os.path.join(v['folder'], 'stderr.txt'), 'row %s: error output' % name)
    for name, v in D['step'].items():
        same = [(n, x['prefix']) for n, x in D['step'].items() if (x['folder'], x['file']) == (v['folder'], v['file'])]
        a(os.path.join(v['folder'], v['file']), 'row%s %s: csv of runner bwx, processes with tag %s'
          % ('' if len(same) == 1 else 's', ' and '.join(n for n, _ in same), ' and '.join(x + '*' for _, x in same)))
        a(os.path.join(v['folder'], 'env.txt'), 'row%s %s: sha256 of runner bwx'
          % ('' if len(same) == 1 else 's', ' and '.join(n for n, _ in same)))
    t = D['try6']
    a(t['path'], 'record of boot %s: 12 modules, 12 x "Configured Memory Speed: 7200 MT/s", MemTotal' % t['boot'][:8])
    a(t['gaps_path'], 'first and last kernel log time of the boots of the 7200 MT/s reboot test (row 0 is the boot of '
      'the rerun), the field hwerr of row 0, and the time line and the process list after the rows (lines %d to %d)'
      % (t['gaps_uptime_line'], t['gaps_top'][-1][3]))
    a(t['boots_path'], 'boot list of the journal: row 0 holds the boot id of try6.txt, which links gaps.txt to this boot')
    a(fd.DIMM_REPORT, 'DIMM report: boot history with module counts (section 3), change to 7200 MT/s (section 6.3)')
    a(D['probe13']['h5'], 'saved journal of the boot of 2026-11-09: Linux start, module count line, error records')
    a(D['probe13']['k5'], 'saved kernel log of the same boot: its last line and the line "Memory: ... available" '
      '(line %d)' % D['mod']['k-5']['line'])
    qt = fd.dt.datetime.utcfromtimestamp(os.path.getmtime(D['probe13']['q_path']))
    a(D['probe13']['q_path'], 'firmware settings list (file time %s UTC): the entry counts and the settings '
      '"DIMM Frequency", "TXREQ Max" and "TXREQ Min"' % qt.strftime('%Y-%m-%d %H:%M'))
    a('ext:cpufreq', 'external source: Linux kernel documentation, Documentation/admin-guide/pm/cpufreq.rst '
      '(scaling_cur_freq is given in kHz)')
    a('ext:proc5', 'external source: Linux manual page proc(5), entry /proc/loadavg (meaning of the load average '
      'fields)')
    # files and sources added with the corrections of the review (numbered after the earlier entries)
    p13 = D['probe13']
    a(p13['a2_csv2'], 'second file of the run partA-20261113T205055Z: only the launch time of its first process is used '
      '(end of the time window of row A-2)')
    a(p13['pre']['when_path'], 'settings saved in the 2026-11-09 boot before the firmware test: time of the save')
    a(p13['pre']['cmdline_path'], 'same save: Linux kernel command line')
    a(p13['pre']['gov_path'], 'same save: two lines, "%s" and "%s" (the file does not name them)' % tuple(p13['pre']['gov']))
    a(p13['pre']['thp_path'], 'same save: transparent_hugepage/enabled')
    a('ext:ps1', 'external source: manual page ps(1) of procps-ng, entry "%cpu" (alias pcpu): the CPU time used, '
      'divided by the time the process has been running. The ps version on CRB was not checked (no ssh in this task)')
    # files added with the corrections of verification round 3 (numbered after the earlier entries)
    ap = D['a2pre']
    a(ap['env_path'], 'run folder of 2026-11-13 20:49 UTC that ended 8 s before the first process of row A-2: start '
      'line and end line')
    a(ap['files']['A5.csv']['path'], 'same folder: %d one-thread processes (header lines only)' % ap['files']['A5.csv']['n'])
    a(ap['files']['A6.csv']['path'], 'same folder: %d one-thread processes (header lines only)' % ap['files']['A6.csv']['n'])
    a(ap['launches_path'], 'same folder: one line per process')
    md = D['mod']
    a(md['h1'], 'saved journal of the 10-module boot of 2026-11-17 04:17 UTC: its first two lines')
    a(md['k-1']['path'], 'saved kernel log of the same 10-module boot: the line "Memory: ... available"')
    a(md['dmi']['path'], 'module list (output of dmidecode, type 17) saved in the boot of the rerun')
    fw = D['fw']
    a(fw['sets']['x1']['path'], 'reply of the firmware settings tool: change of "TXREQ Min" for another test')
    a(fw['sets']['x2']['path'], 'reply of the firmware settings tool: change of "TXREQ Max" for another test')
    a(fw['sets']['revert']['path'], 'replies of the firmware settings tool: both TXREQ settings set back and read back')
    a(fw['lists']['revert']['path'], 'firmware settings list saved after the set-back (file time %s UTC)'
      % fw['lists']['revert']['mtime'].strftime('%Y-%m-%d %H:%M:%S'))
    a(fw['lists']['x1']['path'], 'firmware settings list saved after the first change (file time %s UTC)'
      % fw['lists']['x1']['mtime'].strftime('%Y-%m-%d %H:%M:%S'))
    a(fw['sets']['dimm']['path'], 'reply of the firmware settings tool: "DIMM Frequency" set to 7200 MT/s')
    a(fw['final']['path'], 'last reading of the memory speed setting in the boot of the rerun (one line)')
    return ref


# ----------------------------------------------------------------------------- statistics for all sections

def med(rs):
    return statistics.median(r['GBps'] for r in rs)


def analyse(D):
    recs = D['recs']
    N = {}
    one = lambda rs: (need(len(rs) == 1, 'one record expected, got %d' % len(rs)), rs[0])[1]

    # ---- Q1, part A: one pair per session and round
    pa = []
    for s in (1, 2, 3):
        for rd in (1, 2):
            cell = lambda b, k: sorted(sel(recs, dataset='rerun-A', session=s, round=rd, binary=b, kernel=k),
                                       key=lambda r: r['interval'])
            old, new, ao, an = cell('bw_old', 'read'), cell('bw_new', 'read'), cell('bw_old', 'asmread'), cell('bw_new', 'asmread')
            need(all(len(c) == 3 for c in (old, new, ao, an)), 'three intervals per process in part A')
            vo, vn = [r['GBps'] for r in old], [r['GBps'] for r in new]
            pa.append(dict(session=s, round=rd, old=old, new=new, ao=ao, an=an, old_med=med(old), new_med=med(new),
                           ratio=med(new) / med(old), drop=(1 - med(new) / med(old)) * 100,
                           ratio_lo=min(vn) / max(vo), ratio_hi=max(vn) / min(vo),
                           ao_ratio=med(ao) / med(old), an_ratio=med(an) / med(old)))
    N['pa'] = pa

    # ---- Q1, runner bwx12: pairs inside the same process and round
    def pairs(dataset, kernels):
        out = []
        tags = list(dict.fromkeys(r['tag'] for r in sel(recs, dataset=dataset)))
        for tag in tags:
            for rd in (0, 1):
                o = one(sel(recs, dataset=dataset, tag=tag, round=rd, kernel='oldread'))
                p = dict(dataset=dataset, tag=tag, round=rd, old=o)
                for k in kernels:
                    r = one(sel(recs, dataset=dataset, tag=tag, round=rd, kernel=k))
                    p[k] = r
                    p['drop_' + k] = (1 - r['GBps'] / o['GBps']) * 100
                out.append(p)
        return out
    N['pl'] = pairs('rerun-L', ['asmread'])
    N['pi'] = pairs('control-I', ['asmread'])
    N['pf'] = pairs('F72d12', ['asmread'])
    N['pc'] = pairs('rerun-C', ['read', 'asmread'])
    N['p80'] = pairs('L-1', ['asmread'])

    # ---- Q2: ranges
    def pool(names, kernel, pos=None):
        c = dict(dataset=set(names), kernel=kernel)
        if pos is not None:
            c['pos'] = pos
        return sel(recs, **c)
    N['pool'] = pool
    return N


def compare(r72, r80):
    a, b = rng(r72), rng(r80)
    ov = overlap(a, b)
    return dict(a=a, b=b, overlap=ov, dist=gap(a, b), wording=SAME if ov else DIFFERS, width=width_pct(b))


# ----------------------------------------------------------------------------- the sheet

def render(D):
    recs = D['recs']
    N = analyse(D)
    ref = register(D)
    V = dict(q1=None, q2=None, q1_parts=[], q2_rows=[], insufficient_data=[], hypotheses=[], rule_wordings=dict(
        differs=DIFFERS, same=SAME, no_read=NO_READ))
    try6 = D['try6']
    go, go2 = D['logs']['go'], D['logs']['go2']
    A, X = D['A'], D['X']
    ev = D['events']
    evd = {e['tag']: e for e in ev}
    p13 = D['probe13']
    rules = os.path.join(S, 'baselines-and-rules.txt')
    L = []
    w = L.append
    extra = {}       # short texts and values of sections 1 to 3 that section 4 quotes
    OTHER_DAY.clear()

    def q2row(part, kernel, row72, scope, c, decides, note='', row_label=None, scope_label=None):
        # row_7200 and scope_8000 are the keys of the row. They stay as they were in the earlier builds, so that a
        # tool can find a row. row_7200_label and scope_8000_label are the labels that FACTS.md prints.
        V['q2_rows'].append(dict(part=part, kernel=kernel, row_7200=row72, lo_7200=c['a']['lo'], hi_7200=c['a']['hi'],
                                 n_7200=c['a']['n'], processes_7200=c['a']['procs'], scope_8000=scope,
                                 lo_8000=c['b']['lo'], hi_8000=c['b']['hi'], n_8000=c['b']['n'],
                                 processes_8000=c['b']['procs'], overlap=c['overlap'],
                                 distance_GBps=round(c['dist'], 3), wording=c['wording'] if decides else None,
                                 decides=decides, note=note, row_7200_label=row_label or row72,
                                 scope_8000_label=scope_label or scope))

    # =============================================================================== numbers used in several places
    go_start, go_end = go['states'][0]['utc'], go['states'][-1]['utc']
    one_len = lambda ds: (need(len({r['min_ms'] for r in sel(recs, dataset=ds)}) == 1, 'one interval length in ' + ds),
                          '%g s' % (sel(recs, dataset=ds)[0]['min_ms'] / 1000))[1]
    secA, secX = one_len('rerun-A'), one_len('rerun-L')      # interval lengths: part A, bwx12 parts
    need(one_len('rerun-C') == secX == one_len('control-I'), 'parts L, C, I use the same interval length')
    need(len(D['P_kB']) == 1, 'one buffer size in the P rows')
    mib = '%g MiB' % (D['P_kB'][0] / 1024)
    go2_start, go2_end = go2['states'][0]['utc'], go2['states'][-1]['utc']
    f72t = D['rx']['F72d12']['launches']['a6456']['utc']
    rules_time = fd.dt.datetime.strptime(re.search(r'# Written (\S+)Z', fd._open(rules).read())[1], '%Y-%m-%dT%H:%M:%S')
    rules_lead = (go_start - rules_time).total_seconds()
    need(rules_lead > 0, 'rules written before go.sh started')
    # file times on the clock of the agent's server (the start of go.sh above is on the clock of CRB)
    mtime = lambda p: fd.dt.datetime.utcfromtimestamp(int(os.path.getmtime(p)))
    rules_mtime, sha_mtime = mtime(rules), mtime(os.path.join(S, 'local.sha'))
    need(rules_mtime == rules_time, 'file time of the rules file equal to the time in its line 2')
    need('BEFORE the run (go.sh not yet started)' in fd._open(rules).read().splitlines()[1], 'line 2 of the rules file')
    need(sha_mtime > rules_mtime, 'local.sha is newer than the rules file')

    dl = [p['drop_asmread'] for p in N['pl']]
    di = [p['drop_asmread'] for p in N['pi']]
    df = [p['drop_asmread'] for p in N['pf']]
    dcr = [p['drop_read'] for p in N['pc']]
    dca = [p['drop_asmread'] for p in N['pc']]
    dpa = [p['drop'] for p in N['pa']]
    need(min(dl + di + df + dcr + dca + dpa) > 0, 'new kernel below old kernel in every pair')
    need(all(p['ratio_hi'] < 1 for p in N['pa']), 'every bw_new read interval below every bw_old read interval of its pair')

    # part C grouped by the kernel that ran directly before (rule V2): name -> (records, drops against oldread)
    Crec = sel(recs, dataset='rerun-C')

    def cgroup(kernel, before):
        rs = sel(Crec, kernel=kernel, kernel_before=before)
        ds = [p['drop_' + kernel] for r in rs for p in N['pc'] if p[kernel] is r]
        need(len(ds) == len(rs) > 0, 'one drop per interval of a part C group')
        return rs, ds
    CG = {'read after oldread': cgroup('read', 'oldread'), 'read after asmread': cgroup('read', 'asmread'),
          'asmread after read': cgroup('asmread', 'read'), 'asmread first': cgroup('asmread', FIRST),
          'asmread after oldread': cgroup('asmread', 'oldread')}
    N['CG'] = CG
    need(sum(len(v[0]) for v in CG.values()) == len(sel(Crec, kernel={'read', 'asmread'})), 'the five groups hold every load-only interval of part C')

    pool = N['pool']
    L72o, L72a = sel(recs, dataset='rerun-L', kernel='oldread'), sel(recs, dataset='rerun-L', kernel='asmread')
    I72o, I72a = sel(recs, dataset='control-I', kernel='oldread'), sel(recs, dataset='control-I', kernel='asmread')
    F72o, F72a = sel(recs, dataset='F72d12', kernel='oldread'), sel(recs, dataset='F72d12', kernel='asmread')
    P12o, P12a = pool(BW12, 'oldread', 0), pool(BW12, 'asmread', 1)
    PALLo, PALLa = pool(BW12 + BW11, 'oldread', 0), pool(BW12 + BW11, 'asmread', 1)
    A72o = sel(recs, dataset='rerun-A', binary='bw_old', kernel='read')
    A80o = sel(recs, dataset={'A-1', 'A-2', 'A-3'}, binary='bw_old', kernel='read')
    C72o = sel(recs, dataset='rerun-C', kernel='oldread')
    cLo, cLa = compare(L72o, P12o), compare(L72a, P12a)
    cIo, cIa = compare(I72o, P12o), compare(I72a, P12a)
    cFo, cFa = compare(F72o, P12o), compare(F72a, P12a)
    cAo, cCo = compare(A72o, A80o), compare(C72o, P12o)

    # part A, load-only kernels, session 1 against the same round at 8000 MT/s (rule V3)
    pa3 = []
    for b, k in (('bw_new', 'read'), ('bw_new', 'asmread'), ('bw_old', 'asmread')):
        for rd in (1, 2):
            s1 = sorted(sel(recs, dataset='rerun-A', session=1, round=rd, binary=b, kernel=k), key=lambda r: r['interval'])
            a1 = sorted(sel(recs, dataset='A-1', round=rd, binary=b, kernel=k), key=lambda r: r['interval'])
            a2 = sorted(sel(recs, dataset='A-2', round=rd, binary=b, kernel=k), key=lambda r: r['interval'])
            b80 = rng(a1 + a2)
            above = [r['GBps'] - b80['hi'] for r in s1 if r['GBps'] > b80['hi']]
            below = [b80['lo'] - r['GBps'] for r in s1 if r['GBps'] < b80['lo']]
            pa3.append(dict(binary=b, kernel=k, round=rd, s1=s1, a1=a1, a2=a2, b80=b80, above=above, below=below,
                            inside=3 - len(above) - len(below)))
    newread = [x for x in pa3 if (x['binary'], x['kernel']) == ('bw_new', 'read')]

    # =============================================================================== title
    w('# Facts sheet: whole-chip read test at 7200 MT/s, rerun of 2026-11-17')
    w('')
    w('- This sheet is the source for the report of the rerun.')
    w('- The script `S/build_facts.py` wrote this file from the raw files of section 7. No measured number was typed by '
      'hand.')
    w('- GB = 1e9 bytes. All times are UTC. A time without a date is on %s. A time on another day carries its date '
      'in the same sentence or table cell.' % RERUN_DAY)
    w('- R = `%s`' % R)
    w('- S = `%s`' % S)
    w('- A reference such as [Ref5] points to the file list in section 7.')
    w('- Rates are shown to 0.01 GB/s, rounded half up. A median of an even number of values can therefore differ by '
      '0.01 GB/s from the output of stat_k120.py. A difference of two rates is computed from the values before '
      'rounding. It can therefore differ by 0.01 GB/s from the difference of the two rounded values.')
    w('- Fixed properties of the setup are written as the task and the run scripts give them: the CPU numbers of the '
      'two meshes, the loads per 256 B of each kernel, the two memory speeds, and the dates of earlier runs.')
    w('')

    # =============================================================================== 0
    w('## 0. Short version')
    w('')
    need(not cLa['overlap'] and cLa['dist'] > 0, 'part L asmread above the 8000 MT/s pool')
    need(cFa['overlap'], 'F72d12 asmread inside the 8000 MT/s pool')
    need(cAo['overlap'] and cCo['overlap'], 'old read: parts A and C overlap the 8000 MT/s range')
    need(not cLo['overlap'] and cLo['dist'] < 0, 'old read: part L below the 8000 MT/s pool')
    need(cIo['overlap'] and cFo['overlap'], 'old read: control I and F72d12 overlap the 8000 MT/s pool')
    need(all(x['inside'] == 0 and not x['below'] for x in newread), 'bw_new read of session 1 above the 8000 MT/s range')
    inside = lambda k: k['b']['lo'] <= k['a']['lo'] and k['a']['hi'] <= k['b']['hi']
    need(inside(cFo) and inside(cIo), 'old read: F72d12 and control I inside the 8000 MT/s pool')
    c_ro, c_ra = CG['read after oldread'], CG['read after asmread']
    need(len(c_ro[1]) == len(c_ra[1]), 'equal number of pairs in both read groups of part C')
    # The three sentences and the detail list quote numbers of section 4 (the view by start state). They are built
    # after section 4 by short_version() and are inserted at this place.
    i_short = len(L)
    V['short_version'] = None

    def short_version(c):
        by, pcv, kF1, kI1 = c['byst'], c['partC_view'], c['kF1'], c['kI1']
        kAao, oth = c['kAao'], c['byst_other']
        need(not kAao['overlap'] and kAao['dist'] > 0, 'part C: asmread after oldread above the 8000 MT/s pool')
        a_lo = sum(1 for r in A72o if r['GBps'] < cAo['b']['lo'])
        a_hi = sum(1 for r in A72o if r['GBps'] > cAo['b']['hi'])
        need(a_lo > 0 and a_hi > 0 and cAo['a']['hi'] - cAo['a']['lo'] > cAo['b']['hi'] - cAo['b']['lo'],
             'part A, old read: the 7200 MT/s range is wider than the 8000 MT/s range on both sides')
        need(inside(cFa), 'asmread: F72d12 inside the range of the 8000 MT/s pool')
        nL, nP = nns(L72o), nn(cLo['b'])
        need(nns(L72a) == nL and nn(cLa['b']) == nP, 'part L: the same n for oldread and asmread on both sides')
        short = [
            'Q1: yes, at 7200 MT/s with 12 memory modules the new read kernel was still below the old read kernel: %s '
            'lower when it ran directly after the old read kernel and %s lower when it ran directly after asmread '
            '(part C, %s runs, %d pairs each).' % (pcr(c_ro[1]), pcr(c_ra[1]), secX, len(c_ro[1])),
            'Q2, old read kernel: by the rule fixed before the run the result against the 8000 MT/s runs is "%s" in '
            'the repeat of the 2026-11-13 test (part A, where the test cannot exclude a difference of about %s %%, '
            'est.) and in part C (about %s %%, est.), and the rate was lower in part L (%s GB/s, n = %s, against '
            '%s GB/s, n = %s), but the data do not show that the boot or the memory speed is the cause.'
            % (SAME, pc(cAo['width']), pc(cCo['width']), sp(cLo['a']), nL, sp(cLo['b']), nP),
            'Q2, new read kernel: asmread (the hand-written loop with the same loads, used in place of the new read '
            'kernel) ran above every bwx12 row of the fixed 8000 MT/s list in part L (%s GB/s, n = %s, against %s GB/s, '
            'n = %s), in control I (%s GB/s, n = %s, %s) and in the %d part C intervals that ran directly after the old '
            'read kernel (%s GB/s), but an earlier run of the same line in the same 7200 MT/s boot gave %s GB/s '
            '(F72d12, n = %s), and each memory speed has one boot, so the data do not show an effect of the memory '
            'speed.'
            % (sp(cLa['a']), nL, sp(cLa['b']), nP, sp(cIa['a']), nns(I72a), ADDED, kAao['a']['n'], sp(kAao['a']),
               sp(cFa['a']), nns(F72a)),
        ]
        detail = [
            'Q1, part L (%s runs): asmread was %s below the old read kernel (%d pairs).' % (secX, pcr(dl), len(dl)),
            'Q1, part A (the repeat of the 2026-11-13 test, whole-pass stop, %s): the new read kernel was %s below the '
            'old read kernel (%d pairs of process medians). These percent values are less exact than those of parts L '
            'and C (section 3.1).' % (secA, pcr(dpa), len(dpa)),
            'Q2, old read kernel, the two comparisons with the wording "%s": part A gave %s GB/s (n = %s) against '
            '%s GB/s (n = %s). Part C gave %s GB/s (n = %s) against %s GB/s (n = %s). The size that the test cannot '
            'exclude is the width of the 8000 MT/s range: %s %% of its lower end in part A and %s %% in part C (est. '
            'from one boot). In part A the 7200 MT/s range is wider than the 8000 MT/s range (%s GB/s against '
            '%s GB/s): %d of its %d intervals lie below that range and %d lie above it (section 4.2).'
            % (SAME, sp(cAo['a']), nns(A72o), sp(cAo['b']), nn(cAo['b']), sp(cCo['a']), nns(C72o), sp(cCo['b']),
               nn(cCo['b']), pc(cAo['width']), pc(cCo['width']), g(cAo['a']['hi'] - cAo['a']['lo']),
               g(cAo['b']['hi'] - cAo['b']['lo']), a_lo, cAo['a']['n'], a_hi),
            'Q2, part C: the fixed rules contradict each other here. Rule F2 points 2 and 3 would present part C at '
            '7200 MT/s only. This sheet follows rules V1 point 2, V2 point 4 and V4 and compares part C with the '
            '8000 MT/s rows (decision (r) in section 2).',
            'Q2, old read kernel: two other rows of the same line in the same 7200 MT/s boot lie inside the range of '
            'the 8000 MT/s pool L-1 to L-4. F72d12 (%d process at %s UTC, before the rerun) gave %s GB/s. Control I '
            '(%d processes, idle start, %s, %s) gave %s GB/s.'
            % (cFo['a']['procs'], hm(f72t)[:5], sp(cFo['a']), cIo['a']['procs'], ADDED, NOT_PLAN, sp(cIo['a'])),
            'Q2, old read kernel, view added after the numbers were seen (section 4.2): the %d bwx12 processes of the '
            'pool L-1 to L-4 that started %.0f s to %.0f s after a 120-thread bwx12 process gave %s GB/s (%s). Part L '
            'and part C also started after 120-thread work. Both lie below these %d processes: part L by %s GB/s and '
            'part C by %s GB/s at the nearest ends. Limit: these %d processes are not all 8000 MT/s processes with that '
            'kind of start state. Against the other-binary processes that started after 120-thread work, part C '
            'overlaps (bwx11: %s GB/s, %s. Runner bwx, position 0: %s GB/s, %s). Part L lies below these rows too.'
            % (by['Bo']['procs'], by['gaps'][0], by['gaps'][-1], sp(by['Bo']), nn(by['Bo']), by['Bo']['procs'],
               g(by['near']), g(pcv['near']), by['Bo']['procs'], sp(oth['b11']), nn(oth['b11'], boots=False),
               sp(oth['bx0']), nn(oth['bx0'], boots=False)),
            'Q2, old read kernel: Insufficient data: why part L was lower. ' + H1_MEAS,
            'Q2, new read kernel, asmread in the three visits of the 7200 MT/s boot: F72d12 lies inside the range of '
            'the 8000 MT/s pool L-1 to L-4. Against L-1 alone (the baseline row with the identical argument line) it '
            'is %s GB/s higher. %s Control I (idle start, %s, %s) lies above every bwx12 row of the fixed 8000 MT/s '
            'list, by %s GB/s at the nearest ends (%s GB/s against L-1 alone). The three visits (F72d12, part L, '
            'control I) span %s GB/s.'
            % (g(kF1['dist']), c['f72_limit'], ADDED, NOT_PLAN, g(cIa['dist']), g(kI1['dist']),
               sp(rng(F72a + L72a + I72a))),
            'Q2, new read kernel, part C: asmread directly after oldread (crev, round 1, position 0) gave %s GB/s '
            '(n = %s). By rule V1 point 2 the wording is "%s" against the pool L-1 to L-4 (%s GB/s, n = %s). Part C is '
            'higher by %s GB/s at the nearest ends. The baseline matches in the kernel that ran directly before. It '
            'does not match in the position: asmread is at position 1 in rows L-1 to L-4. This comparison follows '
            'decision (r) in section 2.'
            % (sp(kAao['a']), nns(c['Aao']), kAao['wording'], sp(kAao['b']), nn(kAao['b']), g(kAao['dist'])),
            'Q2, new read kernel: the new read kernel itself (bw_new read) lies outside (above) the 8000 MT/s range of '
            'the same round in session 1 of part A. The bwx12 kernel read has no 8000 MT/s run.',
            'Q2, machine state: the hardware error records during the rerun are not known (the kernel log was not '
            'read). At 8000 MT/s, 2 corrected records fall inside the interval with the lowest asmread value of the '
            'pool L-1 to L-4 (%s GB/s). Without this interval the pool spans %s GB/s, and no wording changes '
            '(sections 4.1 and 4.4). The firmware settings of the boot of the rerun were not read, apart from the '
            'memory speed (section 1.5, point 13).' % (g(c['hw']['low_a']['GBps']), sp(c['hw']['wo'])),
            'Q2, new read kernel: Insufficient data: whether a difference comes from the memory speed. Runs in several '
            'boots per speed would resolve it.',
        ]
        V['short_version'] = dict(sentences=short, detail=detail)
        out = []
        for s_ in short:
            out += [s_, '']
        out += ['More detail for these three sentences:', ''] + ['- ' + d_ for d_ in detail] + ['']
        return out
    w('<details>')
    w('<summary>Words used here</summary>')
    w('')
    words = [
        ('CRB', 'the Arm reference server under test. It has 128 CPUs.'),
        ('Mesh 0, mesh 1', 'the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.'),
        ('Whole chip, 120 threads, 64+56', 'our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on '
         'mesh 1. Each thread reads its own buffer of %s from memory.' % mib),
        ('MT/s', 'million transfers per second, the unit of memory speed.'),
        ('Memory module', 'one DIMM. CRB has 12 slots.'),
        ('Read kernel', 'the inner loop of the benchmark that reads memory. In this sheet "kernel" means this loop. '
         'The operating system kernel is always written "Linux kernel".'),
        ('Old read kernel', 'portable C code with 16 running sums. Each load is followed by an add. Its name is '
         '`read` in the binary bw_old and `oldread` in the runner bwx12.'),
        ('New read kernel', 'NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name '
         'is `read` in the binary bw_new and `read` in bwx12.'),
        ('asmread', 'a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. '
         '"ldp q" is the Arm instruction that loads two 16-byte vector registers.'),
        ('Load-only loop', 'the new read kernel or asmread.'),
        ('read_nop96, read_nop256, read_1pl', 'test loops of bwx12: the asmread loop with 96 or 256 no-operation '
         'instructions per 256 B, and a loop with one load per 64 B line.'),
        ('bandwidth.c, bw_old, bw_new', 'the benchmark and its two binaries of 2026-11-13. bw_old was built from the '
         'old source, bw_new from the new source.'),
        ('bwx12, bwx11, bwx', 'later runner programs for the same loops. They print one row per thread. bwx12 is the '
         'runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.'),
        ('Process, interval, round, position', 'a process is one start of a benchmark binary. An interval is one timed '
         'measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a '
         'round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In '
         'part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.'),
        ('Session', 'one pass of go.sh through part A, part L and part C.'),
        ('Part A', 'the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.'),
        ('Part L', 'one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.'),
        ('Part C', 'one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).'),
        ('Control I', 'the part L line, started from an idle machine, twice. It was %s. It is %s.' % (ADDED, NOT_PLAN)),
        ('Line, argument line', 'the arguments of one bwx12 process, as a spec file holds them. "The same line" means '
         'a process with the same arguments.'),
        ('Idle start', 'a launch at a 1-minute load average below 1.0.'),
        ('Visit', 'one time at which the same line was run. A later visit is the same line run again at a later time.'),
        ('State line', 'a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins '
         'and the processes per user.'),
        ('I, T, P, C rows', 'the row kinds of a bwx csv file: one I row per interval, one T row per thread and '
         'interval, one P row per thread before the first interval and after each interval (it holds the page state '
         'of the buffer), and one C row per thread and interval with counter values.'),
        ('Whole-pass stop', 'the stop rule of bandwidth.c: after the minimum time (%s here) each thread finishes '
         'the pass over its buffer that it is in. The threads stop at different times.' % secA),
        ('Common stop', 'the stop rule used with bwx12 here: all threads stop at the same time (after %s).' % secX),
        ('Pass count', 'total_bytes / bytes_per_thread of an interval row of part A. For the kernels read and asmread '
         'this is the number of buffer passes that all 120 threads completed in the interval. This sheet prints a pass '
         'count for these two kernels only. For copy and asmcopy the same division gives 2 x the number of buffer '
         'passes, because the binary counts read plus written bytes (header line of each process in threads120.csv: '
         '"copy counts read+write bytes"). facts.json holds that value in the field "passes".'),
        ('Rate, total', 'part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the '
         'threads of bytes / elapsed time. Unit GB/s.'),
        ('Load average', 'the number of tasks that are runnable or wait for disk input and output, averaged by Linux '
         'over the last 1, 5 and 15 minutes (file /proc/loadavg %s). "Load at launch" is the 1-minute value read '
         'directly before a process starts. The fourth field of the file gives the tasks that are runnable now and '
         'the number of all tasks.' % ref('ext:proc5')),
        ('%CPU', 'the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is the CPU time '
         'that a process has used, divided by the time since the process started %s. So it is an average over the '
         'life of the process. It is not the use at the moment of the reading.' % ref('ext:ps1')),
        ('pr/ttyAMA-1', 'a Linux kernel thread in the process lists. By its name it prints kernel messages to the '
         'serial console ttyAMA. This meaning was not checked on CRB.'),
        ('Boot id', 'a random identifier that Linux creates at each start. Equal boot ids mean the same boot.'),
        ('MemTotal', 'the usable memory that Linux reports, in kB.'),
        ('GiB', '2^30 bytes. A "32 GB" module holds 32 GiB %s.' % ref(fd.DIMM_REPORT)),
        ('Module list', 'the output of the command `dmidecode -t 17`, which prints the hardware table of the firmware. '
         'It holds one entry "Memory Device" per memory module: %d entries in the list saved in the boot of the rerun '
         '%s, and 10 entries in a 10-module boot by the DIMM report %s.'
         % (D['mod']['dmi']['devices'], ref(D['mod']['dmi']['path']), ref(fd.DIMM_REPORT))),
        ('Journal', 'the log store of Linux. It keeps the kernel log of earlier boots %s.' % ref(fd.DIMM_REPORT)),
        ('Hardware error record', 'a message that the firmware passes to Linux when hardware reports an error. Linux '
         'prints it in the kernel log with the tag "[Hardware Error]". Its severity is "corrected" (the hardware '
         'repaired it) or "recoverable" (not repaired, the system continues) %s.' % ref(fd.DIMM_REPORT)),
        ('TXREQ settings', 'firmware settings that limit the read requests of the cores. They are not memory settings '
         '%s. The saved replies of the settings tool name two of them: "TXREQ Max" and "TXREQ Min" (section 1.5, '
         'point 13).' % ref(fd.DIMM_REPORT)),
        ('2 MiB pages', 'transparent huge pages. The "P" rows of bwx12 report how many kB of each buffer lie on them.'),
        ('Marker file', '`/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts '
         'stop when it exists.'),
        ('Governor', 'the Linux policy that sets the CPU frequency.'),
        ('rc', 'the exit status of a process. 0 means success.'),
        ('sha256', 'a checksum. Two files with the same sha256 have the same content.'),
        ('Baseline, like-for-like', 'an earlier 8000 MT/s run with 12 modules that used the same binary and method as '
         'a part of the rerun. The list was fixed before the run.'),
        ('Supporting row, other-binary row', 'earlier 8000 MT/s runs that differ in interval length or counter setup '
         '(supporting), or that used another runner binary (other binary).'),
        ('Ranges overlap', 'two min-to-max ranges share at least one value.'),
        ('n', 'the number of measurements that a range comes from. It is written as intervals / processes / sessions / '
         'boots (rule V1 point 1). "No session" marks a row that is not part of a session of go.sh.'),
        ('Pool', 'the intervals of several rows taken together as one range.'),
        ('Distance of the nearest ends', 'for two ranges that do not overlap: the lowest value of the higher range '
         'minus the highest value of the lower range.'),
        ('Rules V1 to V4, F1, F2', 'the comparison rules in `baselines-and-rules.txt`.'),
        ('FINDINGS.md', 'the facts sheet of the investigation of 2026-11-15 into the drop of the read rate.'),
        ('est.', 'estimated, not measured directly.'),
    ]
    wl_txt = fd._open(fd.DIMM_REPORT).read()
    need('A "32 GB" module holds 32 GiB.' in wl_txt
         and '- **Journal**: the log store of Linux. It keeps the kernel log of earlier boots.' in wl_txt
         and 'a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the kernel '
             'log with the tag `[Hardware Error]`. Its severity is "corrected" (hardware repaired it) or "recoverable" '
             '(not repaired, system continues).' in wl_txt
         and '- **TXREQ settings**: firmware settings that limit the read requests of the cores. They are not memory '
             'settings.' in wl_txt
         and 'the table in which the firmware lists the hardware for the operating system. The command `dmidecode` '
             'prints it.' in wl_txt
         and '10 entries in a 10-module boot, 12 entries otherwise' in wl_txt,
         'DIMM report: the definitions that the word list quotes')
    for k, v in words:
        w('- **%s**: %s' % (k, v))
    w('')
    w('</details>')
    w('')
    w('The request of 2026-11-17: "Given that the DIMM issue is resolved at 7200 MT/s, let\'s rerun the whole chip '
      'test. Please run old kernel which used portable C code and had read and add, and run new kernel which '
      'performed worse than old kernel. Compare the results."')
    w('')
    w('- **Q1**: at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below '
      'that of the old read kernel, and by how much.')
    w('- **Q2**: did either kernel\'s rate differ from the earlier runs with 12 modules at 8000 MT/s.')
    w('')

    # =============================================================================== 1
    w('## 1. Run record')
    w('')
    w('### 1.1 Steps and times')
    w('')
    w('- go.sh (the driver script) ran from %s to %s %s.' % (hm(go_start), hm(go_end), ref(go['path'])))
    w('- go2.sh (the control, added after the first numbers of parts A, L and C were seen, %s) ran from %s to %s %s.'
      % (NOT_PLAN, hm(go2_start), hm(go2_end), ref(go2['path'])))
    w('- One session is part A, then part L, then part C. Three sessions ran one after the other. A fourth part C '
      'process (T72C4) followed %s.' % ref(os.path.join(S, 'go.sh')))
    w('')
    rows = []
    for e in ev:
        o = e['obj']
        if e['part'] == 'A':
            what = 'part A, session %d: 24 processes of bw_old and bw_new' % e['session']
            src = '%s %s' % (ref(o['csv']), ref(o['probe']['path']))
            last = hm(e['last'])
        else:
            what = {'L': 'part L', 'C': 'part C (%s)' % o['spec'], 'I': 'control I (%s)' % ADDED}[e['part']]
            what += (', session %d' % e['session']) if e['part'] in 'LC' and e['session'] else ''
            what += ': 1 process of bwx12'
            src = ref(os.path.join(o['folder'], 'launches.txt'))
            last = '-'
        rows.append([e['tag'], what, hm(e['start']), hm(e['first']), last, hm(e['end']),
                     '-' if e['gap_s'] is None else '%.0f' % e['gap_s'], src])
    L.extend(table(['Folder tag', 'What ran', 'Script start', 'First process launch', 'Last process launch',
                    'End of last process', 'Gap before the first launch, s', 'Source'], rows))
    w('- "Script start" is the time in the folder name. ra.sh and rx.sh take it when they start.')
    w('- "End of last process" is the `load_after` line of probe.txt for part A. For bwx12 it is the `rc` line of '
      'launches.txt.')
    w('- "Gap" is the first launch minus the end of the previous 120-thread process of the rerun.')
    w('- The time stamps have a resolution of 1 s. rx.sh checks once per second whether its process still runs %s. '
      'So a gap can be up to 2 s longer than the value shown (est.).' % ref(os.path.join(W15, 'rx.sh')))
    w('- T72A1 has no gap value. It was the first step, and the three load averages at its start were %.2f, %.2f and '
      '%.2f %s.' % (go['states'][0]['load1'], go['states'][0]['load5'], go['states'][0]['load15'], ref(go['path'])))
    w('')

    # ---- 1.2
    w('### 1.2 Machine state and its proof')
    w('')
    w('The table lists every state line of the two logs and the two state lines of every probe.txt.')
    w('')
    rows = []

    def procs_str(p):
        other = {k: v for k, v in p.items() if k not in ('jhan', 'root')}
        return 'jhan %d, root %d, %d system accounts with %d processes' % (p.get('jhan', 0), p.get('root', 0), len(other),
                                                                       sum(other.values()))
    ra_txt = fd._open(os.path.join(S, 'ra.sh')).read()
    ra_limit, ra_sleep = re.search(r'\$r -le (\d+)', ra_txt)[1], re.search(r'^sleep (\d+)', ra_txt, re.M)[1]
    statelist = []
    for lg in (go, go2):
        for s_ in lg['states']:
            statelist.append((s_['utc'], [os.path.basename(lg['path']).split('-')[0] + ' log, line %d: %s' % (s_['line'], s_['label']),
                              hm(s_['utc']), s_['boot'][:8], s_['memtotal_kB'],
                              '%.2f / %.2f / %.2f' % (s_['load1'], s_['load5'], s_['load15']),
                              '%d / %d' % (s_['runnable'], s_['tasks']), s_['logins'], s_['marker'], procs_str(s_['procs'])]))
    for a_ in A:
        p = a_['probe']
        statelist.append((p['utc'], ['probe.txt of %s, start' % a_['tag'], hm(p['utc']), p['boot'][:8], p['memtotal_kB'],
                                     '%.2f / %.2f / %.2f' % p['load_before'],
                                     '%d (read at least %s s before this time) / not recorded' % (p['runnable'], ra_sleep),
                                     p['logins'],
                                     'not recorded', 'not recorded']))
        statelist.append((p['utc_after'], ['probe.txt of %s, end' % a_['tag'], hm(p['utc_after']), 'not recorded', p['memtotal_after_kB'],
                                           '%.2f / %.2f / %.2f' % p['load_after'], 'not recorded', 'not recorded', 'not recorded',
                                           'not recorded']))
    statelist.sort(key=lambda t: t[0])
    L.extend(table(['State line', 'Time', 'Boot id, first 8 characters', 'MemTotal, kB', 'Load average 1 / 5 / 15 min',
                    'Runnable / all tasks', 'Logins', 'Marker file', 'Processes per user'], [r for _, r in statelist]))
    sysacc = sorted({k for s_ in go['states'] + go2['states'] for k in s_['procs'] if k not in ('jhan', 'root')})
    users = sorted({k for s_ in go['states'] + go2['states'] for k in s_['procs']})
    nst = len(go['states']) + len(go2['states'])
    w('- **Boot.** All %d state lines and all %d probe.txt files hold the full boot id `%s`. This is the boot id in '
      'line 2 of try6.txt %s.' % (nst, len(A), try6['boot'], ref(try6['path'])))
    w('- **12 modules.** MemTotal is %d kB in every line of the table. try6.txt holds the same value in line %d and '
      'the kernel message "This system has %d DIMM sockets" in line %d %s.'
      % (try6['memtotal_kB'], try6['memtotal_line'], try6['dimm_sockets'], try6['dimm_line'], ref(try6['path'])))
    md = D['mod']
    dimm_txt = fd._open(fd.DIMM_REPORT).read()
    b10 = [b for b in D['boot_table']['boots'] if b['start'].strftime('%Y-%m-%d %H:%M') == md['h1_start'].strftime('%Y-%m-%d %H:%M')]
    need(len(b10) == 1 and b10[0]['modules'] == md['h1_dimm'] == 10 and p13['boot_dimm'] == 12,
         'the journal h-1.txt is the 10-module boot of the DIMM report, the journal h-5.txt a 12-module boot')
    need('The module count comes from the kernel line `ghes_edac: This system has N DIMM sockets`' in dimm_txt
         and 'differs by exactly 64 GiB between the two states. That equals two modules.' in dimm_txt
         and 'CRB has 12 memory modules of 32 GiB each.' in dimm_txt
         and 'sudo dmidecode -t 17 | grep "Configured Memory Speed" | sort | uniq -c' in dimm_txt,
         'DIMM report: source of the module count, the 64 GiB step, the module size, the command of the speed line')
    need(md['k-1']['stamp'] == md['h1_start'].strftime('%b %d %H:%M:%S')
         and md['k-5']['stamp'] == p13['boot_start'].strftime('%b %d %H:%M:%S'),
         'the "Memory:" lines belong to the boots of the two journals')
    need(md['k-5']['total_K'] - md['k-1']['total_K'] == 64 * 1024 * 1024, 'the two totals differ by 64 x 1024 x 1024 K')
    dm = md['dmi']
    need(dm['devices'] == dm['speed'] == dm['size'] == dm['volatile'] == try6['speed_count'] == 12
         and dm['size_any'] == dm['size'] + dm['volatile'] == md['try6_modules'],
         'module list of the boot of the rerun: 12 entries, 24 lines with the text "Size: 32 GB"')
    need(try6['boots_first'] <= dm['mtime'] <= try6['boots_last'], 'file time of the module list inside row 0 of boots.txt')
    w('- **Why these two values mean 12 modules.** The number in the kernel message is the number of modules that the '
      'firmware reports. It is not the number of slots of the board. The saved journal of the boot that started on %s '
      'reads "This system has %d DIMM sockets" in line %d %s. The DIMM report lists that boot with %d modules. It '
      'takes the module count of every boot from this kernel line (its section 3) %s.'
      % (hmd(md['h1_start']), md['h1_dimm'], md['h1_dimm_line'], ref(md['h1']), b10[0]['modules'], ref(fd.DIMM_REPORT)))
    w('- **Direct count.** Line %d of try6.txt reads "%d Configured Memory Speed: %d MT/s" %s. The first number is the '
      'number of lines with this text in the module list, one line per module. The DIMM report gives the command: '
      '`dmidecode -t 17 | grep "Configured Memory Speed" | sort | uniq -c` (its section 6.3) %s. The module list that '
      'was saved later in the same boot has the file time %s. That is inside the span of row 0 of boots.txt %s. It '
      'holds %d entries "Memory Device" and %d lines "Configured Memory Speed: %d MT/s" %s.'
      % (try6['speed_line'], try6['speed_count'], try6['speed_MTps'], ref(try6['path']), ref(fd.DIMM_REPORT),
         hm(dm['mtime']), ref(try6['boots_path']), dm['devices'], dm['speed'], try6['speed_MTps'], ref(dm['path'])))
    w('- **Memory size.** With 1 kB = 1024 bytes, %d kB are %s GiB. 12 modules of 32 GiB are 384 GiB %s. The kernel '
      'log of the 12-module boot of 2026-11-09 holds the line "Memory: %dK/%dK available" (line %d %s). The kernel log '
      'of the 10-module boot named above holds "Memory: %dK/%dK available" (line %d %s). The second numbers of the '
      'two lines differ by %d K. That is 64 x 1024 x 1024 K. The DIMM report reads this as exactly 64 GiB, the size '
      'of two modules %s.'
      % (try6['memtotal_kB'], g(try6['memtotal_kB'] / 1024 / 1024), ref(fd.DIMM_REPORT), md['k-5']['avail_K'],
         md['k-5']['total_K'], md['k-5']['line'], ref(md['k-5']['path']), md['k-1']['avail_K'], md['k-1']['total_K'],
         md['k-1']['line'], ref(md['k-1']['path']), md['k-5']['total_K'] - md['k-1']['total_K'], ref(fd.DIMM_REPORT)))
    w('- Line %d of try6.txt reads "modules=%d". This is not the module count. The module list holds %d lines that '
      'contain the text "Size: 32 GB": %d lines "Size: 32 GB" and %d lines "Volatile Size: 32 GB" %s. Hypothesis, not '
      'checked: the script that wrote try6.txt counted these %d lines. That script is not among the files of this '
      'task.' % (md['try6_modules_line'], md['try6_modules'], dm['size_any'], dm['size'], dm['volatile'], ref(dm['path']),
                 dm['size_any']))
    w('- **7200 MT/s.** Line %d of try6.txt reads "%d Configured Memory Speed: %d MT/s". It was recorded at %s in the '
      'same boot %s. The speed was not read again during the rerun, because that needs root. The proof for the '
      'rerun is the equal boot id. Assumption, not measured: the speed does not change inside one boot. The firmware '
      'applies the setting at the next start %s.'
      % (try6['speed_line'], try6['speed_count'], try6['speed_MTps'], hm(try6['utc']), ref(try6['path']), ref(fd.DIMM_REPORT)))
    w('- **Time since boot.** The first kernel log line of this boot is from %s %s. go.sh started %s later.'
      % (hm(try6['first_log_utc']), ref(try6['gaps_path']), dur((go_start - try6['first_log_utc']).total_seconds())))
    w('- **Linux kernel command line** (line %d of the go.sh log %s): `%s`'
      % (go['other']['cmdline'][1], ref(go['path']), go['other']['cmdline'][0]))
    gv = go['other']['governors'][0]
    gov = re.findall(r'(\d+) (\w+);', gv)
    cur = int(re.search(r'scaling_cur_freq (\d+)', gv)[1])
    need(len(gov) == 1, 'one governor value')
    w('- **Governor.** %s of the CPUs 0-119 use the governor "%s". `scaling_cur_freq` of CPU 0 was %d (line %d of the '
      'go.sh log %s). The unit of that file is kHz %s, so the value is %.1f GHz.'
      % (gov[0][0], gov[0][1], cur, go['other']['governors'][1], ref(go['path']), ref('ext:cpufreq'), cur / 1e6))
    thp = re.match(r'thp enabled (.*) defrag (.*)', go['other']['thp'][0])
    w('- **Huge page setting.** `transparent_hugepage/enabled` = `%s`. `defrag` = `%s` (line %d of the go.sh log %s). '
      'The value in brackets is the active one.' % (thp[1], thp[2], go['other']['thp'][1], ref(go['path'])))
    w('- **Runnable tasks in probe.txt.** ra.sh reads the value in its wait loop, then sleeps %s s, and then writes '
      'the probe line with a new time and a new load average %s. So the value %s is from at least %s s before the '
      'time shown in the table. The count at the first launch of part A is not recorded.'
      % (ra_sleep, ref(os.path.join(S, 'ra.sh')), '/'.join(sorted({str(a_['probe']['runnable']) for a_ in A})), ra_sleep))
    w('- **Logins.** Every state line shows 0 logins. Every probe.txt and every launch line of rx.sh shows 0 logins too.')
    w('- **Processes per user.** Only these users own processes in the %d state lines: %s. No other user appears.'
      % (nst, ', '.join(users)))
    jh = sorted({s_['procs'].get('jhan', 0) for s_ in go['states'] + go2['states']})
    rt = [s_['procs'].get('root', 0) for s_ in go['states'] + go2['states']]
    w('- The user jhan owns %s processes in every state line. root owns %d to %d. The %d system accounts own 1 each.'
      % ('/'.join(map(str, jh)), min(rt), max(rt), len(sysacc)))
    w('- **Marker file.** It is "absent" in all %d state lines.' % nst)
    w('- **CPU affinity of go.sh.** `%s` (line %d of the go.sh log %s).'
      % (go['other']['affinity'][0], go['other']['affinity'][1], ref(go['path'])))
    w('- **Hardware error records.** The kernel log was not read during or after the rerun (no root). try6.txt shows '
      '`hwerr=%d` at %s, at the start of this boot %s.' % (try6['hwerr'], hm(try6['utc']), ref(try6['path'])))
    w('')

    # ---- 1.3
    w('### 1.3 System load at every launch')
    w('')
    w('The value is the 1-minute load average of Linux, read by the run script directly before it starts a process.')
    w('')
    w('Part A. ra.sh writes the value into the "-- binary" line of each of the 24 processes.')
    w('')
    rows = []
    for a_ in A:
        ls = [p['load1'] for p in a_['procs']]
        pr = a_['probe']
        rows.append([a_['tag'], '%.2f / %.2f / %.2f' % pr['load_before'], pr['runnable'], '%.2f' % ls[0], '%.2f' % min(ls),
                     '%.2f' % max(ls), len(ls), '%.2f / %.2f / %.2f' % pr['load_after'], pr['pcpu_max'],
                     '%s %s' % (ref(a_['csv']), ref(pr['path']))])
    L.extend(table(['Session', 'Load average 1 / 5 / 15 min before the first process (probe.txt)',
                    'Runnable tasks at the end of the wait of ra.sh (at least %s s before the probe line)' % ra_sleep,
                    'Load at the first process', 'Lowest load of the 24 launches', 'Highest load of the 24 launches',
                    'Launches', 'Load average after the last process', 'Highest %CPU in the process list of probe.txt', 'Source'], rows))
    w('Parts L and C and control I. rx.sh writes the value into the launch line of launches.txt.')
    w('')
    rows = []
    for x in sorted(X, key=lambda x: x['launches'][0]['utc']):
        la = x['launches'][0]
        rows.append([x['tag'], hm(la['utc']), '%.2f' % la['load1'], '%.2f' % la['load5'], '%.2f' % la['load15'],
                     '%d / %d' % (la['runnable'], la['tasks']), la['logins'], x['env']['pcpu_max'],
                     '%s, process list %s' % (ref(os.path.join(x['folder'], 'launches.txt')), ref(os.path.join(x['folder'], 'env.txt')))])
    L.extend(table(['Folder tag', 'Launch', 'Load 1 min', 'Load 5 min', 'Load 15 min', 'Runnable / all tasks', 'Logins',
                    'Highest %CPU in the process list of env.txt', 'Source'], rows))
    hi = [x for x in X if x['launches'][0]['load1'] >= 1.0]
    lo = [x for x in X if x['launches'][0]['load1'] < 1.0]
    need({x['part'] for x in lo} == {'I'} and len(lo) == 2, 'only control I started below load 1.0')
    s1l = [p['load1'] for p in A[0]['procs']]
    rest = [p['load1'] for a_ in A[1:] for p in a_['procs']] + [x['launches'][0]['load1'] for x in hi]
    need(s1l == sorted(s1l), 'load rises from process to process in session 1')
    w('- In session 1 of part A the load at launch rose from %.2f at the first process to %.2f at the last process.'
      % (s1l[0], s1l[-1]))
    w('- All launches of sessions 2 and 3 of part A and all launches of parts L and C saw a load of %.2f to %.2f.'
      % (min(rest), max(rest)))
    w('- The two launches of control I started at a load of %s.' % ' and '.join('%.2f' % x['launches'][0]['load1'] for x in lo))
    need({x['launches'][0]['runnable'] for x in X} == {1}, '1 runnable task at every bwx12 launch')
    w('- At every bwx12 launch 1 task was runnable (launch line of launches.txt).')
    envgap = sorted({(x['launches'][0]['utc'] - x['env']['start']).total_seconds() for x in X})
    need(min(envgap) > 0, 'env.txt written before the launch')
    w('- The process lists of env.txt show at most %s %%CPU. rx.sh writes env.txt when it starts %s. That was %s s '
      'before each of the %d launches (first line of env.txt against the launch line). %%CPU is an average over the '
      'life of a process (see the word list). So the lists would show a new busy process. They cannot show a short '
      'busy phase of a process that has run since the boot.'
      % (max(x['env']['pcpu_max'] for x in X), ref(os.path.join(W15, 'rx.sh')),
         ' to '.join('%.0f' % v for v in sorted({envgap[0], envgap[-1]})), len(X)))
    w('- The process lists of probe.txt (part A) were written at the time of the probe line, directly before the '
      'first process %s. The same limit of %%CPU holds for them.' % ref(os.path.join(S, 'ra.sh')))
    ev_near = [e for e in ev if e['gap_s'] is not None and e['part'] != 'I']      # steps of go.sh after the first one
    ev_far = [e for e in ev if e['part'] == 'I']                                  # the two control steps of go2.sh
    need(ev[0]['gap_s'] is None and ev[0]['tag'] == 'T72A1' and len(ev_near) + len(ev_far) + 1 == len(ev)
         and max(e['gap_s'] for e in ev_near) < 10 < min(e['gap_s'] for e in ev_far),
         'gaps: the first step has none, the other steps of go.sh have a short one, the control steps a long one')
    w('- Hypothesis: the high load values come from the rerun\'s own 120-thread processes. Linux averages the load '
      'over the last 1, 5 and 15 minutes %s, so the value stays high for some time after a process ends. The first '
      'launch of each of the %d steps from %s to %s came %s s after such an end (table of section 1.1). %s had no '
      'earlier process of the rerun (load %.2f at launch). %s came %s s after one (load %s at launch). The later '
      'launches of part A followed the previous part A '
      'process with no wait %s. The runnable counts and the 0 logins fit this. The process lists cannot test it (see '
      'the limit of %%CPU above). A check that would confirm or reject it: sample /proc/loadavg and the list of '
      'running processes once per second between two steps. This was not done.'
      % (ref('ext:proc5'), len(ev_near), ev_near[0]['tag'], ev_near[-1]['tag'],
         ' or '.join('%.0f' % v for v in sorted({e['gap_s'] for e in ev_near})), ev[0]['tag'], ev[0]['load1'],
         ' and '.join(e['tag'] for e in ev_far), ' s and '.join('%.0f' % e['gap_s'] for e in ev_far),
         ' and '.join('%.2f' % e['load1'] for e in ev_far), ref(os.path.join(S, 'ra.sh'))))
    w('')

    # ---- 1.4
    w('### 1.4 Integrity checks')
    w('')
    for i, c in enumerate(D['checks'], 1):
        w('%d. %s: %s.' % (i, 'pass' if c['ok'] else 'FAILED', c['text']))
    w('')
    w('- Were the buffers on 2 MiB pages? Parts L, C and I: yes. Every "P" row shows the whole buffer (%s kB) on huge '
      'pages (check %d). Part A: not recorded. bandwidth.c prints only the setting `thp=madvise` in its header line.'
      % ('/'.join(map(str, D['P_kB'])), [c['key'] for c in D['checks']].index('P-rows') + 1))
    w('')

    # ---- 1.5
    a1p = D['base']['A-1']['procs']
    a1first = fd.clock(D['base']['A-1']['folder'], a1p[0]['utc'])
    w('### 1.5 Limits: differences between the procedure of 2026-11-13 and part A')
    w('')
    w('The timed part is the same: same two binaries (check %d), same arguments (check %d), same order of the 24 '
      'processes (check %d). The list below holds the differences that were found. It is not proven to be complete. '
      'Point 12 holds the Linux settings that were compared without a difference. Point 13 holds what is on record '
      'about the firmware settings. The list follows findings F9 and F1 of the review %s.'
      % ([c['key'] for c in D['checks']].index('sha-bw') + 1, [c['key'] for c in D['checks']].index('A-args') + 1,
         [c['key'] for c in D['checks']].index('A-order') + 1, ref(os.path.join(S, 'review-w1.json'))))
    w('')
    OTHER_DAY.update([p13['one_first'], p13['one_last']])      # printed below with the date in the same sentence
    need(fd.folder_date(D['base']['A-1']['folder']).strftime('%Y-%m-%d') == '2026-11-13', 'date of the A-1 folder')
    w('1. **One-thread phase.** On 2026-11-13 the script first ran %d one-thread processes, from %s to %s %s. The '
      'first 120-thread process started at %s with a load of %.2f %s. Part A has no one-thread phase.'
      % (p13['one_n'], p13['one_first'], p13['one_last'], ref(p13['one_path']), hmd(a1first), a1p[0]['load1'],
         ref(os.path.join(D['base']['A-1']['folder'], 'threads120.csv'))))
    w('2. **Start state of the sessions.** Session 1 %s. Session 2 %s. Session 3 %s.'
      % (evd['T72A1']['state'], evd['T72A2']['state'], evd['T72A3']['state']))
    w('3. **Wait before the first process.** ra.sh waits until %s or fewer tasks are runnable and then sleeps %s s %s. '
      'The script of 2026-11-13 built the binaries, ran a self-test and the one-thread phase, and had no wait %s.'
      % (ra_limit, ra_sleep, ref(os.path.join(S, 'ra.sh')), ref(os.path.join(K13, 'run_kernels.sh'))))
    w('4. **Memory speed.** 8000 MT/s then, 7200 MT/s now. This is the intended change.')
    # records of the same journal during the baselines A-2 and A-3 (one record = one line "Hardware error from APEI ...")
    a2r = p13['a2_records']
    sev = sorted({e['severity'] for e in a2r})
    parts = []
    for t in sorted({e['utc'] for e in a2r}):
        es = [e for e in a2r if e['utc'] == t]
        pr = es[0]['proc']
        need(all(e['proc'] is pr for e in es), 'records of one second belong to one process of A1.csv')
        name = '%s (%s %s)' % (pr['tag'], pr['binary'], pr['kernel'])
        if pr['utc'] == t:
            where = 'the second in which the process %s was launched' % name
        else:
            where = 'during the process %s, launched at %s' % (name, hmd(pr['utc']))
        parts.append('%d at %s, %s (journal lines %s)' % (len(es), hmd(t), where, ' and '.join(str(e['line']) for e in es)))
    a2csv = os.path.join(D['base']['A-2']['folder'], 'A1.csv')
    if a2r:
        a2txt = ('During baseline A-2 (A1.csv, %s to %s %s %s) the same journal holds %d record%s with the severity '
                 '"%s": %s.' % (hmd(p13['a2_window'][0]), hmd(p13['a2_window'][1]), ref(a2csv),
                                ref(p13['a2_csv2']), len(a2r), '' if len(a2r) == 1 else 's', '" or "'.join(sev),
                                ', and '.join(parts)))
    else:
        a2txt = ('During baseline A-2 (A1.csv, %s to %s %s %s) the same journal holds 0 records.'
                 % (hmd(p13['a2_window'][0]), hmd(p13['a2_window'][1]), ref(a2csv), ref(p13['a2_csv2'])))
    a3txt = ('During the three processes of baseline A-3 (%s to %s %s) it holds %d record%s.'
             % (hmd(p13['a3_window'][0]), hmd(p13['a3_window'][1]), ref(os.path.join(D['base']['A-3']['folder'], 'A3.csv')),
                len(p13['a3_records']), '' if len(p13['a3_records']) == 1 else 's'))
    w('5. **Boot and time since boot.** The run of 2026-11-13 was in the boot that started on %s %s. Its first '
      '120-thread process started %.1f days after that. The rerun started %s after the start of its boot.'
      % (p13['boot_start'].strftime('%Y-%m-%d %H:%M:%S'), ref(p13['h5']),
         (a1first - p13['boot_start']).total_seconds() / 86400, dur((go_start - try6['first_log_utc']).total_seconds())))
    w('6. **Speed and boot changed together.** Each memory speed has exactly one boot in this comparison.')
    w('7. **2 MiB pages.** Neither script records the page state of the buffers for part A.')
    w('8. **Hardware error records.** The journal of the 2026-11-09 boot holds its first record at %s (line %d), '
      'during the one-thread phase of that run. It holds %d records between %s and %s, the 120-thread part of '
      'baseline A-1 %s. %s %s For '
      'the rerun the kernel log was not read (no root). Insufficient data: whether records occurred during the '
      'rerun. A count of the "[Hardware Error]" lines of the kernel log after the run would resolve it (needs root). '
      'Section 4.1 gives the records during the bwx12 and bwx11 rows of the same boot.'
      % (hmd(p13['first_record_utc']), p13['first_record_line'], p13['records_in_120'],
         hmd(p13['one_done_utc']), hmd(p13['utc_after']), ref(p13['h5']), a2txt, a3txt))
    w('9. **Module count of the 2026-11-13 run.** Its probe.txt holds no MemTotal and no boot id %s. The count comes '
      'from the saved journal: the boot started on %s with the line "This system has %d DIMM sockets" %s, and the '
      'saved kernel log of that boot ends with a line dated "%s" %s.'
      % (ref(p13['path']), p13['boot_start'].strftime('%Y-%m-%d %H:%M:%S'), p13['boot_dimm'], ref(p13['h5']),
         p13['k5_last'], ref(p13['k5'])))
    need(not p13['has_memtotal'] and not p13['has_boot_id'], 'probe.txt of 2026-11-13 has no MemTotal and no boot id')
    qt = fd.dt.datetime.utcfromtimestamp(os.path.getmtime(p13['q_path']))
    bts = D['boot_table']['boots']
    inboot = lambda t: [b for b in bts if b['start'] <= t][-1]['no']
    need(inboot(qt) == inboot(a1first), 'file time of the settings list lies in the boot of the 2026-11-13 run')
    w('10. **Memory speed of the baseline boot.** No reading of the applied speed was saved in that boot. The '
      'firmware settings list with the file time %s, which lies inside that boot, shows "DIMM Frequency" = '
      '"%d MT/s" %s. The DIMM report gives %d MT/s as the setting until %s %s.'
      % (qt.strftime('%Y-%m-%d %H:%M'), p13['q_speed'], ref(p13['q_path']), D['boot_table']['until']['speed'],
         D['boot_table']['until']['utc'].strftime('%Y-%m-%d %H:%M'), ref(fd.DIMM_REPORT)))
    a2p = D['base']['A-2']['procs']
    a2opts = sorted({' '.join(re.findall(r'--cpus \S+|--per-thread', p['args'])) for p in a2p})
    need(len(a2opts) == 1 and not any('copy' in p['kernel'] for p in a2p), 'A-2: one option set, no copy kernel')
    ap = D['a2pre']
    a2gap = (p13['a2_first']['utc'] - ap['end']).total_seconds()
    need(ap['threads'] == ['1'] and ap['binaries'] == ['bw_new'] and ap['launches_n'] == len(ap['hdr'])
         and ap['launches_files'] == sorted(ap['files']) and ap['start'] <= ap['first'] <= ap['last'] <= ap['end']
         and 0 < a2gap < 60 and p13['a2_first']['line'] == 1 and p13['a2_first']['utc'] == p13['a2_window'][0]
         and ap['steps'][-2:] == ['A5', 'A6'],
         'the folder before A-2 holds one-thread processes of bw_new only, and it ended shortly before A-2 started')
    extra['a2pre_txt'] = ('%.0f s after the end of a run of %.0f s that held one-thread processes only'
                      % (a2gap, (ap['end'] - ap['start']).total_seconds()))
    w('11. **Second baseline A-2.** It ran the same binaries with `%s` in another process order, %d processes, no '
      'copy kernels %s. It started %s. That run is the folder %s. It started at %s and ended at %s (lines %d and %d '
      'of its env.txt %s). It ran %d processes of %s, all with `--threads %s`: %d in A5.csv and %d in A6.csv, launched '
      'from %s to %s %s %s. Its launches.txt lists these %d processes and no other %s. The first process of A1.csv '
      'started at %s with a 1-minute load average of %.2f %s.'
      % (a2opts[0], len(a2p), ref(os.path.join(D['base']['A-2']['folder'], 'A1.csv')), extra['a2pre_txt'], rel(ap['folder']),
         hmd(ap['start']), hmd(ap['end']), ap['start_line'], ap['end_line'], ref(ap['env_path']), len(ap['hdr']),
         ap['binaries'][0], ap['threads'][0], ap['files']['A5.csv']['n'], ap['files']['A6.csv']['n'], hmd(ap['first']),
         hmd(ap['last']), ref(ap['files']['A5.csv']['path']), ref(ap['files']['A6.csv']['path']), ap['launches_n'],
         ref(ap['launches_path']), hmd(p13['a2_first']['utc']), p13['a2_first']['load1'],
         ref(os.path.join(D['base']['A-2']['folder'], 'A1.csv'))))
    # settings that were compared between the two boots and found equal
    pre = p13['pre']
    cmd72 = go['other']['cmdline'][0]
    rel72 = re.search(r'vmlinuz-(\S+)', cmd72)[1]
    thp80 = re.search(r'^## thp=(.*) defrag=(.*)$', D['env_partA'], re.M)
    need(inboot(pre['when']) == inboot(a1first), 'the settings were saved in the boot of the 8000 MT/s baselines')
    need(p13['journal_release'] == rel72, 'same Linux kernel release in both boots')
    need(pre['cmdline'] == cmd72, 'same Linux kernel command line in both boots')
    need(pre['gov'] == ['128 %s' % gov[0][1], str(cur)], 'gov.txt holds the governor and the frequency value of the go.sh log')
    need((thp80[1].strip(), thp80[2].strip()) == (thp[1].strip(), thp[2].strip()) and pre['thp'] == thp[1].strip(),
         'same huge page setting in both boots')
    w('12. **Compared between the two boots, no difference found.** Only these four settings of Linux were compared. '
      'Point 13 gives the firmware settings.')
    w('    - Linux kernel release: `%s` in line 1 of the saved journal of the 2026-11-09 boot %s and in the command '
      'line of the rerun (line %d of the go.sh log %s).' % (rel72, ref(p13['h5']), go['other']['cmdline'][1], ref(go['path'])))
    w('    - Linux kernel command line: the file cmdline.txt was saved on %s %s %s. By the boot history of the DIMM '
      'report that time lies inside the 2026-11-09 boot %s. Its text is equal to line %d of the go.sh log %s.'
      % (pre['when'].strftime('%Y-%m-%d %H:%M:%S'), ref(pre['when_path']), ref(pre['cmdline_path']), ref(fd.DIMM_REPORT),
         go['other']['cmdline'][1], ref(go['path'])))
    w('    - Governor: gov.txt of the same save holds the two lines "%s" and "%s" %s. The file does not name them. The '
      'go.sh log holds "%s %s" for the CPUs 0-119 and `scaling_cur_freq` %d for CPU 0 (line %d %s). So the governor '
      'name is equal. The number %d is equal too, but gov.txt does not say which CPU and which value it is.'
      % (pre['gov'][0], pre['gov'][1], ref(pre['gov_path']), gov[0][0], gov[0][1], cur, go['other']['governors'][1],
         ref(go['path']), cur))
    w('    - Huge page setting: line %d of env.txt of the A-2 run holds `%s` and defrag `%s` %s. thp.txt of the save '
      'named above holds `%s` %s. Line %d of the go.sh log holds the same values %s.'
      % (D['env_partA'][:thp80.start()].count('\n') + 1, thp80[1].strip(), thp80[2].strip(),
         ref(os.path.join(D['base']['A-2']['folder'], 'env.txt')), pre['thp'],
         ref(pre['thp_path']), go['other']['thp'][1], ref(go['path'])))
    # firmware settings: what the saved replies and lists of the settings tool show
    fw = D['fw']
    fb, fx, fr = fw['lists']['base'], fw['lists']['x1'], fw['lists']['revert']
    sx1, sx2, srv, sdm, fin = fw['sets']['x1'], fw['sets']['x2'], fw['sets']['revert'], fw['sets']['dimm'], fw['final']
    one_set = lambda v: (need(len(v['set']) == 1 and v['set'][0]['modified'] is True, 'one set reply, modified: true'), v['set'][0])[1]
    x1s, x2s, dms = one_set(sx1), one_set(sx2), one_set(sdm)
    rvs = {x['name']: x for x in srv['set']}
    rvg = {x['name']: x for x in srv['get']}
    need(fb['path'] == p13['q_path'] and fb['n'] == fr['n'] == fx['n'] and fw['same_entries'] and not fw['same_order']
         and fb['unavailable'] == fr['unavailable'] and fb['val'] == fr['val'],
         'the settings list after the set-back holds the same entries as the list of the baseline boot')
    need((x1s['name'], x2s['name'], dms['name']) == ('TXREQ Min', 'TXREQ Max', 'DIMM Frequency')
         and sorted(rvs) == sorted(rvg) == ['TXREQ Max', 'TXREQ Min'] and all(x['modified'] is True for x in srv['set'])
         and all(rvs[n]['answer'] == rvg[n]['answer'] == fb['val'][n] for n in rvs)
         and x1s['answer'] != fb['val']['TXREQ Min'] and x2s['answer'] != fb['val']['TXREQ Max'],
         'TXREQ Min and TXREQ Max were changed and then set back to the values of the list of the baseline boot')
    need(sx1['when'] < sx2['when'] < srv['when'] < fr['mtime'] < sdm['mtime'] < try6['first_log_utc'] < fin['mtime']
         and fb['mtime'] < sx1['when'] < fx['mtime'] < sx2['when'] and sdm['when'] is None
         and try6['boots_first'] <= fin['mtime'] <= try6['boots_last'],
         'order in time of the replies and lists of the settings tool')
    need([k for k in fx['val'] if fx['val'][k] != fb['val'][k]] == ['TXREQ Min'] and fx['val']['TXREQ Min'] == x1s['answer']
         and len(fw['x1_diff']) == 2, 'the list after the first change differs in TXREQ Min only')
    need(dms['answer'] == '%d MT/s' % try6['speed_MTps'] == fin['answer'] and fb['val']['DIMM Frequency'] == '%d MT/s' % p13['q_speed'],
         'DIMM Frequency: 8000 MT/s in the lists, set to 7200 MT/s, read as 7200 MT/s')
    need('It needs root rights.' in dimm_txt and 'reads and writes firmware settings' in dimm_txt
         and 'State of CRB after the test (2026-11-17 20:06): "DIMM Frequency" = `7200 MT/s`' in dimm_txt,
         'DIMM report: the settings tool needs root, and the last reading is the setting "DIMM Frequency"')
    w('13. **Firmware settings.** No settings list was saved in the boot of the rerun. The settings tool '
      '(`uefisettings`, a tool of Arm that reads and writes firmware settings) needs root %s. The saved records of '
      'the tool show this:' % ref(fd.DIMM_REPORT))
    w('    - Baseline boot. The settings list with the file time %s holds %d entries. %d have a readable value, %d '
      'show "ValueUnavailable", and %d show "VStoreError" (the tool could not read the value). It shows '
      '"TXREQ Max" = "%s", "TXREQ Min" = "%s" and "DIMM Frequency" = "%s" %s.'
      % (hmd(fb['mtime']), fb['n'], fb['readable'], fb['unavailable'], fb['store_error'], fb['val']['TXREQ Max'], fb['val']['TXREQ Min'],
         fb['val']['DIMM Frequency'], ref(fb['path'])))
    w('    - Changes for another test. Line %d of set.txt of the folder x1 holds the date %s. The file holds the reply '
      '"%s" = "%s" (answer in line %d) with "modified: true" %s. Line %d of set.txt of the folder x2 holds the date '
      '%s. The file holds the reply "%s" = "%s" with "modified": true (line %d) %s.'
      % (sx1['when_line'], hmd(sx1['when']), x1s['name'], x1s['answer'], x1s['line'], ref(sx1['path']),
         sx2['when_line'], hmd(sx2['when']), x2s['name'], x2s['answer'], x2s['line'], ref(sx2['path'])))
    w('    - Set back. Line %d of set.txt of the folder revert holds the date %s. The file holds the replies '
      '"TXREQ Max" = "%s" (line %d) and "TXREQ Min" = "%s" (line %d), both with "modified": true. Both values were read '
      'back in lines %d and %d %s. They are the values of the list of the baseline boot.'
      % (srv['when_line'], hmd(srv['when']), rvs['TXREQ Max']['answer'], rvs['TXREQ Max']['line'],
         rvs['TXREQ Min']['answer'], rvs['TXREQ Min']['line'], rvg['TXREQ Max']['line'], rvg['TXREQ Min']['line'],
         ref(srv['path'])))
    w('    - After the set-back. The settings list with the file time %s holds the same %d entries as the list of the '
      'baseline boot: the two lists are equal in the name, the answer, the options and the help text of every entry. '
      'The order of the entries differs %s. So the %d readable values are equal. The %d other values were not '
      'compared.' % (hmd(fr['mtime']), fr['n'], ref(fr['path']), fr['readable'], fr['unavailable'] + fr['store_error']))
    w('    - Memory speed. set.txt of the folder dimm7200-20261117 has the file time %s. It holds one reply: "%s" = '
      '"%s" (answer in line %d) with "modified: true" %s. setting-final.txt of that folder has the file time %s. That is inside '
      'the span of row 0 of boots.txt, the boot of the rerun %s. It holds the one line `%s` %s. The file does not '
      'name the setting. The DIMM report gives this reading as the setting "DIMM Frequency" (its section 6.3) %s.'
      % (hmd(sdm['mtime']), dms['name'], dms['answer'], dms['line'], ref(sdm['path']), hm(fin['mtime']),
         ref(try6['boots_path']), fin['text'], ref(fin['path']), ref(fd.DIMM_REPORT)))
    w('    - Search. A search of R by file name finds %d files set.txt and %d files questions.json. These are the %d '
      'reply files and the %d lists named in this point, and one more list with the file time %s, saved after the '
      'first change. That list differs from the list of the baseline boot in one entry: "TXREQ Min" = "%s" %s. Among '
      'the %d reply files, the only one that is later than the set-back is the change of "DIMM Frequency". A change '
      'that was made without a saved reply would not be on record here.'
      % (len(fw['sets']), len(fw['lists']), len(fw['sets']), len(fw['lists']) - 1, hmd(fx['mtime']),
         fx['val']['TXREQ Min'], ref(fx['path']), len(fw['sets'])))
    need(fx['unavailable'] == fb['unavailable'], 'the same number of entries without a value in all three lists')
    w('    - Limits. The newest settings list has the file time %s. That is before the first kernel log line of the '
      'boot of the rerun (%s, section 1.2). In each of the %d saved lists %d of the %d entries show "ValueUnavailable" '
      'in place of a value. The file times are those of the saved files. Insufficient data: the firmware settings in '
      'boot %s, apart from the memory speed. A settings list saved in that boot would resolve it (needs root).'
      % (hmd(fr['mtime']), hm(try6['first_log_utc']), len(fw['lists']), fr['unavailable'], fr['n'], try6['boot'][:8]))
    extra['fw'] = dict(set_back=srv['when'], readable=fr['readable'], unavailable=fr['unavailable'])
    w('')
    a12o = sel(recs, dataset={'A-1', 'A-2'}, binary='bw_old', kernel='read')
    need({(r['dataset'], r['round'], r['process']) for r in a12o}
         == {('A-1', 1, 1), ('A-1', 2, len(D['base']['A-1']['procs'])), ('A-2', 1, 1), ('A-2', 2, len(a2p))},
         'bw_old read of A-1 and A-2: the first process of the file in round 1, the last process in round 2')
    w('Text required by rule F1 point 5 %s: The one-thread phase of the 2026-11-13 run was not repeated. Whether the '
      'work before the first 120-thread process changes the rate of the new read kernel is not known (Insufficient '
      'data: a run with the new kernel at several positions, after an idle start and after 120-thread work, would '
      'settle it). At 8000 MT/s the old read kernel gave %s GB/s after one-thread work and directly after 120-thread '
      'work (rows A-1 and A-2, %s).' % (ref(rules), sp(rng(a12o)), nn(rng(a12o))))
    need({r['kernel_before'] for r in a12o if r['round'] == 2} == {'bw_new read'},
         'bw_old read, round 2 of A-1 and A-2: the process before it in the file is bw_new read')
    lgap = lambda folder, procs: (fd.clock(folder, procs[-1]['utc']) - fd.clock(folder, procs[-2]['utc'])).total_seconds()
    g1, g2 = lgap(D['base']['A-1']['folder'], a1p), lgap(D['base']['A-2']['folder'], a2p)
    need(0 < g1 < 10 and 0 < g2 < 10, 'the last process of A-1 and A-2 was launched a few seconds after the one before')
    w('- Where the words of the last sentence come from. In both rows the round-1 process of bw_old read is the first '
      'process of the file. It started after one-thread work (points 1 and 11). The round-2 process is the last '
      'process of the file. The process before it in the file is the 120-thread process of bw_new read. That process '
      'was launched %.0f s before it in row A-1 and %.0f s before it in row A-2 %s %s.'
      % (g1, g2, ref(os.path.join(D['base']['A-1']['folder'], 'threads120.csv')),
         ref(os.path.join(D['base']['A-2']['folder'], 'A1.csv'))))
    w('')

    # =============================================================================== 2
    w('## 2. Decisions made by the agent for this run')
    w('')
    w('These are decisions. They are not facts about the machine.')
    w('')
    w('Decisions made before or during the run:')
    w('')
    dec = [
        '"Whole chip test" was read as the 120-thread part of run_kernels.sh of 2026-11-13 %s. The one-thread part '
        'was not repeated.' % ref(os.path.join(K13, 'run_kernels.sh')),
        '"Old kernel" = the kernel `read` of bw_old. "New kernel" = the kernel `read` of bw_new. Both binaries are the '
        'files of 2026-11-13 by sha256 (check %d).' % ([c['key'] for c in D['checks']].index('sha-bw') + 1),
        'Part A ran all six kernels (read, write, copy, asmread, asmwrite, asmcopy) to keep the process order of '
        '2026-11-13. Statements are made for the read kernels only (rule V3 %s).' % ref(rules),
        'Parts L and C were added. Reason: FINDINGS.md section F1 shows that the %s whole-pass stop rule of '
        'bandwidth.c distorts totals %s.' % (secA, ref(os.path.join(W15, 'FINDINGS.md'))),
        'Three sessions ran one after the other without a pause, plus a fourth part C process. So part C has 2 '
        'processes per kernel order.',
        'No root was used. So the memory speed is proven through the boot id only, and the kernel log was not read.',
        'Control I was added after the first numbers of parts A, L and C were seen. Reason: an earlier run of the same '
        'line in the same boot (F72d12, %s UTC) gave a lower asmread total than part L. Control I is therefore not '
        'part of the plan fixed before the run.' % hm(f72t)[:5],
        'The baseline list and the comparison rules were fixed before go.sh started. The rules file has the file '
        'time %s on the clock of the agent\'s server, and its line 2 says that go.sh had not yet started %s. '
        'S/local.sha, the sha256 list of the run files, has the file time %s on the same clock, %.0f s later %s. '
        'go.sh started at %s by the clock of CRB %s. That is about %.0f s after the rules file (est.: the two clocks '
        'were not compared).'
        % (hm(rules_mtime), ref(rules), hm(sha_mtime), (sha_mtime - rules_mtime).total_seconds(),
           ref(os.path.join(S, 'local.sha')), hm(go_start), ref(go['path']), rules_lead),
    ]
    for i, d in enumerate(dec):
        w('- (%s) %s' % ('abcdefgh'[i], d))
    w('')
    w('Decisions made while this sheet was built, after the numbers were seen:')
    w('')
    bwxp = {r['proc_key']: r['start'] for r in sel(recs, dataset=set(BWX))}
    bwx_off = sum(1 for v in bwxp.values() if v == 'offset')
    need(set(bwxp.values()) == {'common', 'offset'}, 'the processes of the bwx pool used --start common or --start offset')
    dec2 = [
        'Rate per interval. Part A uses the column aggregate_GBps of the file. The bwx runners use the sum over the '
        'threads of bytes / elapsed time. This is the method of stat_k120.py and stat_bwx.py. facts.json holds the '
        'rates rounded to 0.001 GB/s.',
        'Ratio new/old in part A = median of the 3 intervals of the bw_new process divided by the median of the 3 '
        'intervals of the bw_old process of the same session and round. The lowest and the highest ratio of single '
        'intervals are given beside it. The lowest ratio is the lowest bw_new interval divided by the highest bw_old '
        'interval of the same session and round. The highest ratio is the highest bw_new interval divided by the '
        'lowest bw_old interval. These are the two extremes over all 9 pairs of one bw_new interval and one bw_old '
        'interval. They are not the ratios of the intervals with the same number.',
        'Range of the 8000 MT/s side in the overlap test of rule V1 point 2, parts L and C: the pool of the baseline '
        'row L-1 and the supporting rows L-2 to L-4 (all bwx12). The result against L-1 alone and against the pool '
        'with the other-binary rows is shown beside it, so the reader can see whether this choice matters.',
        'From every earlier bwx12 and bwx11 row only oldread at position 0 and asmread at position 1 are used. These '
        'are the positions of part L.',
        'Row X2d12 is shown and not used. Rule V4 lists it as "not a baseline" (firmware test setting). Rules V2 '
        'point 4 and F2 point 2 name it as a baseline. The two texts contradict each other. This sheet follows V4, '
        'because V4 is the fixed list.',
        'The sums per mesh in section 4.7 were compared after the numbers were seen. That comparison is not part of '
        'the rules fixed before the run.',
        'The view "equal pass count" in section 4.3 and the table of thread rates under it were added after the '
        'numbers were seen. They are not part of rule V3. Both keep the two rounds apart.',
        'Rows of runner bwx (other binary) as the reference of part C. Rule V4 names for the two B7 folders the '
        'tags common-6000-common-p1 to p4. Rule V2 point 4 names the tags common-6000-* (%d processes in the %d '
        'folders %s). The two texts contradict each other. This sheet uses the %d processes of rule '
        'V2 point 4, because that rule defines the comparison per position and quotes the ranges of these %d '
        'processes. This is the opposite choice to decision (m). %d of the %d processes used --start offset. '
        'Section 4.5 shows the values of the %d processes with --start common beside the pool. No verdict rests on '
        'these rows.' % (len(bwxp), len(BWX), ', '.join(BWX), len(bwxp), len(bwxp), bwx_off, len(bwxp), len(bwxp) - bwx_off),
        'The view "pool L-1 to L-4 split by the start state" in section 4.2 was added after the numbers were seen. It '
        'is not part of the rules fixed before the run.',
        'Part C against 8000 MT/s. Rule F2 point 2 says: "bwx12, 7200 against 8000 MT/s: use part L only". Rule F2 '
        'point 3 says: "Part C: present it as old against new at 7200 MT/s only." Rule V1 point 2 asks for the '
        'comparison "Per part (A, L, C) and kernel". Rule V2 point 4 names the 8000 MT/s reference of each group of '
        'part C. The part C list of rule V4 says: "oldread, asmread: the part L list". The texts contradict each '
        'other %s. This sheet follows V1, V2 and V4. It gives a wording by rule V1 point 2 for two rows of part C: '
        'oldread, and asmread directly after oldread. Reason 1: V4 is the fixed list of baselines, and it names a '
        'baseline for these two kernels of part C. Decision (m) follows V4 on the same ground. Reason 2: finding F2 '
        'is about the kernel `read`, which has no bwx12 run at 8000 MT/s, and this sheet gives no wording for `read`. '
        'Reason 3: point 3 of F2 itself speaks of an 8000 MT/s column for part C. Its second sentence reads: "In any '
        '8000 MT/s column, the cell of "read" must say "no bwx12 run" and must not hold the asmread value." '
        'If F2 points 2 and 3 are followed instead, this sheet gives neither of the two wordings, and the view by '
        'start state of section 4.2 has no part C row. Each place that gives one of the two wordings names this '
        'decision. For the three sentences of the Short version the detail list under them names it. The part C rows '
        'of the view by start state name it too. Part C would then still be shown next to 8000 MT/s rows in at '
        'least three kinds of places. First, the sums per mesh of section 4.7 and item 9 of "Established" in section '
        '6: both name this decision and give the oldread result without part C too. Second, the comparisons with the '
        'rows of runner bwx in sections 4.2, 4.5 and 4.6: rules V2 point 4 and F2 point 4 name such rows as '
        'references, and this sheet labels them as rows of another binary. Third, the rows without a wording in the '
        'two part C tables of sections 4.2 and 4.5. So this sheet does not claim that part C would then answer Q1 '
        'only.' % ref(rules),
    ]
    need(len(dec2) == len('ijklmnopqr'), 'one letter per decision')
    for i, d in enumerate(dec2):
        w('- (%s) %s' % ('ijklmnopqr'[i], d))
    w('')

    # =============================================================================== 3
    w('## 3. Q1: old against new at 7200 MT/s')
    w('')
    w('### 3.1 Part A: bw_old and bw_new, whole-pass stop, %s, 3 intervals per process' % secA)
    w('')
    w('Start state of the sessions:')
    w('')
    for a_ in A:
        w('- Session %d (%s) %s.' % (a_['session'], a_['tag'], evd[a_['tag']]['state']))
    w('')
    w('One row is one process. A cell shows the rate in GB/s and, in brackets, the pass count of the interval.')
    w('')
    rows = []
    # rule F1 point 2: the start state of the session is part of the row label (the column beside the session number)
    slabel = {a_['session']: evd[a_['tag']]['state'] for a_ in A}
    for p in N['pa']:
        for label, cell in (('bw_old read (old read kernel)', p['old']), ('bw_new read (new read kernel)', p['new']),
                            ('bw_old asmread', p['ao']), ('bw_new asmread', p['an'])):
            r0 = cell[0]
            rows.append([p['session'], slabel[p['session']], p['round'], label, r0['launch_utc'][11:19],
                         '%.2f' % r0['load1_at_launch']]
                        + ['%s (%d)' % (g(r['GBps']), r['passes']) for r in cell]
                        + [g(med(cell)), '%.2f to %.2f' % (min(r['per_thread_min_GBps'] for r in cell),
                                                           max(r['per_thread_max_GBps'] for r in cell)),
                           '%s, lines %d-%d' % (ref(os.path.join(R, r0['folder'][2:], r0['file'])), cell[0]['line'], cell[-1]['line'])])
    L.extend(table(['Session', 'Start state of the session', 'Round', 'Binary and kernel', 'Launch', 'Load at launch',
                    'Interval 1, GB/s (passes)', 'Interval 2', 'Interval 3', 'Median, GB/s',
                    'Slowest to fastest thread, GB/s', 'Source'], rows))
    w('New against old per session and round:')
    w('')
    rows = []
    for p in N['pa']:
        rows.append([p['session'], slabel[p['session']], p['round'], g(p['old_med']), g(p['new_med']), '%.3f' % p['ratio'],
                     pc(p['drop']),
                     '%.3f to %.3f' % (p['ratio_lo'], p['ratio_hi']), '%.3f' % p['ao_ratio'], '%.3f' % p['an_ratio']])
    L.extend(table(['Session', 'Start state of the session', 'Round', 'bw_old read, median GB/s', 'bw_new read, median GB/s',
                    'Ratio new/old', 'New below old, %',
                    'Lowest to highest ratio of single intervals (lowest bw_new / highest bw_old to highest bw_new / '
                    'lowest bw_old)', 'bw_old asmread / bw_old read', 'bw_new asmread / bw_old read'], rows))
    passes_new = sorted({r['passes'] for p in N['pa'] for r in p['new']})
    passes_old = [r['passes'] for p in N['pa'] for r in p['old']]
    top = max(N['pa'], key=lambda p: p['ratio_hi'])
    w('- The new read kernel is below the old read kernel in all %d pairs. The highest single-interval ratio is %.3f '
      '(session %d, round %d). It is the highest bw_new interval divided by the lowest bw_old interval of that '
      'session and round (%s GB/s divided by %s GB/s). Decision (j) in section 2 gives the definition.'
      % (len(N['pa']), top['ratio_hi'], top['session'], top['round'], g(max(r['GBps'] for r in top['new'])),
         g(min(r['GBps'] for r in top['old']))))
    w('- The columns "bw_old asmread / bw_old read" and "bw_new asmread / bw_old read" are ratios of process medians.')
    w('- asmread gives %.3f to %.3f of the old read kernel in both binaries. So the lower rate belongs to the '
      'load-only loop, not to the binary.' % (min(min(p['ao_ratio'], p['an_ratio']) for p in N['pa']),
                                              max(max(p['ao_ratio'], p['an_ratio']) for p in N['pa'])))
    w('- Pass counts: bw_new read completed %s passes per interval. bw_old read completed %d to %d.'
      % (', '.join(map(str, passes_new[:-1])) + ' or %d' % passes_new[-1] if 1 < len(passes_new) <= 4 else
         '%d to %d' % (passes_new[0], passes_new[-1]),
         min(passes_old), max(passes_old)))
    w('- Limit of part A (rule V3 %s): with the whole-pass stop the pass count moves in steps, and the rate moves '
      'with it. So the percent values of part A are less exact than those of parts L and C.' % ref(rules))
    w('')

    # ---- 3.2
    w('### 3.2 Parts L and I: bwx12, common stop, %s, oldread then asmread' % secX)
    w('')
    w('- In these parts asmread is used in place of the new read kernel. It is the same loop: 8 "ldp q" loads per 256 B.')
    w('- The drop is computed inside the same process and round: (1 - asmread / oldread) x 100.')
    w('- "m0 + m1" are the sums over the threads of mesh 0 and of mesh 1.')
    w('')
    rows = []

    def lrow(p, what):
        o, a_ = p['old'], p['asmread']
        return [p['tag'] if p['dataset'] != 'F72d12' else 'F72d12', what, p['round'], '%.2f' % o['load1_at_launch'], g(o['GBps']),
                '%s + %s' % (g(o['mesh0_GBps']), g(o['mesh1_GBps'])), g(a_['GBps']),
                '%s + %s' % (g(a_['mesh0_GBps']), g(a_['mesh1_GBps'])), pc(p['drop_asmread']),
                '%s, I rows in lines %d and %d' % (ref(os.path.join(R, o['folder'][2:], o['file'])), o['line'], a_['line'])]
    for p in N['pl']:
        rows.append(lrow(p, 'part L, session %d. %s' % (p['old']['session'], STANDIN)))
    for p in N['pi']:
        rows.append(lrow(p, 'control I (idle start, added later)'))
    for p in N['pf']:
        rows.append(lrow(p, 'earlier visit of the same boot (%s), not part of the rerun' % hm(f72t)[:5]))
    L.extend(table(['Folder tag or row', 'What', 'Round', 'Load at launch', 'oldread, GB/s', 'oldread m0 + m1', 'asmread, GB/s',
                    'asmread m0 + m1', 'asmread below oldread, %', 'Source'], rows))
    gl = sorted({evd[t]['gap_s'] for t in ('T72L1', 'T72L2', 'T72L3')})
    w('- Every part L process started %s s after the last 120-thread process of part A of its session.'
      % ' or '.join('%.0f' % x for x in gl))
    w('- The two control I processes started from an idle machine: the load at launch was %s, and the previous '
      '120-thread process had ended %s s before.'
      % (' and '.join('%.2f' % evd[t]['load1'] for t in ('T72I1', 'T72I2')),
         ' and '.join('%.0f' % evd[t]['gap_s'] for t in ('T72I1', 'T72I2'))))
    w('- F72d12 started %.0f s after the first kernel log line of the boot, at a load of %.2f %s %s. Section 4.1 '
      'gives the proof that it ran in the boot of the rerun.'
      % ((D['rx']['F72d12']['launches']['a6456']['utc'] - try6['first_log_utc']).total_seconds(),
         D['rx']['F72d12']['launches']['a6456']['load1'], ref(os.path.join(D['rx']['F72d12']['folder'], 'launches.txt')),
         ref(try6['gaps_path'])))
    fenv = D['rx']['F72d12']['env']
    need(len(fenv['top']) >= 2 and fenv['top'][0][1] > 10 * max(x['env']['pcpu_max'] for x in X),
         'process list of F72d12 shows a busy process, the lists of the rerun do not')
    w('- The process list of F72d12 differs from those of the rerun. Its env.txt was written at %s, %.0f s before the '
      'launch. It lists %s at %s %%CPU and %s at %s %%CPU (lines %d and %d %s). The env.txt files of the %d bwx12 '
      'launches of the rerun show at most %s %%CPU. So F72d12 is an idle start only by the load-average rule of '
      'this sheet (section 4.6).'
      % (hm(fenv['start']), (D['rx']['F72d12']['launches']['a6456']['utc'] - fenv['start']).total_seconds(),
         fenv['top'][0][2], fenv['top'][0][1], fenv['top'][1][2], fenv['top'][1][1], fenv['top'][0][3], fenv['top'][1][3],
         ref(os.path.join(D['rx']['F72d12']['folder'], 'env.txt')), len(X), max(x['env']['pcpu_max'] for x in X)))
    w('')

    # ---- 3.3
    w('### 3.3 Part C: bwx12, common stop, %s, oldread, read and asmread in one process' % secX)
    w('')
    w('- `read` is the new read kernel in bwx12. `oldread` is the old read kernel.')
    w('- cfwd runs oldread, read, asmread. crev runs asmread, read, oldread. Each process runs its sequence twice '
      '(rounds 0 and 1).')
    w('- Each drop is computed against oldread of the same process and round.')
    w('- "m0 + m1" are the sums over the threads of mesh 0 and of mesh 1, in GB/s. Section 4.7 uses them.')
    w('')
    rows = []
    for p in N['pc']:
        x = next(x for x in X if x['tag'] == p['tag'])
        cellf = lambda r: '%s (position %d, after %s)' % (g(r['GBps']), r['pos'], r['kernel_before'].replace(
            'none (first interval of the process)', 'nothing: first interval'))
        mm = lambda r: '%s + %s' % (g(r['mesh0_GBps']), g(r['mesh1_GBps']))
        rows.append([p['tag'], x['spec'], p['round'], '%.2f' % p['old']['load1_at_launch'], cellf(p['old']), mm(p['old']),
                     cellf(p['read']), mm(p['read']), cellf(p['asmread']), mm(p['asmread']), pc(p['drop_read']),
                     pc(p['drop_asmread']),
                     '%s, I rows in lines %d, %d, %d' % (ref(x['csv']), p['old']['line'], p['read']['line'], p['asmread']['line'])])
    L.extend(table(['Folder tag', 'Order', 'Round', 'Load at launch', 'oldread, GB/s', 'oldread m0 + m1', 'read, GB/s',
                    'read m0 + m1', 'asmread, GB/s', 'asmread m0 + m1', 'read below oldread, %',
                    'asmread below oldread, %', 'Source'], rows))
    w('Groups by the kernel that ran directly before (rule V2 %s):' % ref(rules))
    w('')
    C = Crec
    groups = [
        ('read after oldread', CG['read after oldread'], 'cfwd, rounds 0 and 1'),
        ('read after asmread', CG['read after asmread'], 'crev, rounds 0 and 1'),
        ('asmread after read', CG['asmread after read'], 'cfwd, rounds 0 and 1'),
        ('asmread as first interval of the process', CG['asmread first'], 'crev, round 0'),
        ('asmread after oldread (the condition of part L)', CG['asmread after oldread'], 'crev, round 1'),
        ('oldread, all positions', (sel(C, kernel='oldread'), None), 'cfwd position 0, crev position 2'),
    ]
    rows = []
    for name, (rs, ds), where in groups:
        a_ = rng(rs)
        dtxt = '%s to %s' % (pc(min(ds)), pc(max(ds))) if ds else '-'
        rows.append([name, where, ', '.join(dict.fromkeys(r['tag'] for r in rs)), nn(a_, boots=False), sp(a_), dtxt])
    L.extend(table(['Group', 'Where', 'Folder tags', 'n', 'Min to max, GB/s', 'Below oldread of the same process and round, %'], rows))
    w('- Limit (rule V2 point 5): the reverse order comes from 2 processes (T72C2 in session 2, T72C4 after session 3). '
      'With 2 processes per order, order and session are still not fully separated.')
    w('')

    # ---- 3.4
    w('### 3.4 Verdict for Q1')
    w('')
    gL, gI, gC, gA = rng(L72a), rng(I72a), rng(sel(C, kernel='read')), rng(sel(recs, dataset='rerun-A', binary='bw_new', kernel='read'))
    tags = lambda rs: ', '.join(dict.fromkeys(r['tag'] for r in rs))
    cpair = lambda key, what: ('C', key, what, CG[key][1], '%d pairs: %d intervals per kernel / %d processes (%s) / %s / 1 boot'
                               % (len(CG[key][1]), len(CG[key][0]), rng(CG[key][0])['procs'], tags(CG[key][0]), sess(CG[key][0])))
    q1p = [
        cpair('read after oldread', 'bwx12 `read` (new read kernel) directly after `oldread` (cfwd), against `oldread` of '
              'the same process and round'),
        cpair('read after asmread', 'bwx12 `read` (new read kernel) directly after `asmread` (crev), against `oldread` of '
              'the same process and round'),
        cpair('asmread after read', 'bwx12 `asmread` directly after `read` (cfwd), against `oldread` of the same process '
              'and round'),
        cpair('asmread first', 'bwx12 `asmread` as first interval of the process (crev, round 0), against `oldread` of '
              'the same process and round'),
        cpair('asmread after oldread', 'bwx12 `asmread` directly after `oldread` (crev, round 1), against `oldread` of '
              'the same process and round'),
        ('L', None, 'bwx12 `asmread` (used in place of the new read kernel) against `oldread`, same process and round', dl,
         '%d pairs: %d intervals per kernel / %d processes / %d sessions / 1 boot' % (len(dl), gL['n'], gL['procs'], gL['sessions'])),
        ('A', None, 'bw_new `read` against bw_old `read`, medians of 3 intervals, same session and round', dpa,
         '%d pairs of process medians: %d intervals per kernel / %d processes per kernel / %d sessions / 1 boot' % (len(dpa), gA['n'], gA['procs'], gA['sessions'])),
        ('I (control, %s)' % ADDED, None, 'bwx12 `asmread` against `oldread`, same process and round', di,
         '%d pairs: %d intervals per kernel / %d processes / no session / 1 boot' % (len(di), gI['n'], gI['procs'])),
        ('F72d12 (earlier visit, not part of the rerun)', None, 'bwx12 `asmread` against `oldread`, same process and round', df,
         '%d pairs: %d intervals per kernel / 1 process / no session / 1 boot' % (len(df), len(df))),
    ]
    rows = []
    for part, group, what, ds, n in q1p:
        rows.append([part, what, pc(min(ds)), pc(max(ds)), n])
        V['q1_parts'].append(dict(part=part, group=group, pair=what.replace('`', ''), smallest_drop_pct=round(min(ds), 2),
                                  largest_drop_pct=round(max(ds), 2), n=n))
    L.extend(table(['Part', 'Pair', 'Smallest drop, %', 'Largest drop, %', 'n'], rows))
    w('- Part C has one row per group (rule V2 %s). No range is given over all read intervals or over all asmread '
      'intervals of part C.' % ref(rules))
    w('')
    g_ro, g_ra = CG['read after oldread'], CG['read after asmread']
    V['q1'] = (
        'Yes. At 7200 MT/s with 12 memory modules the new read kernel is still below the old read kernel. Part C '
        '(bwx12 kernel read against oldread of the same process and round, common stop, %s): %s lower when read ran '
        'directly after oldread (%d pairs, %d processes: %s), and %s lower when read ran directly after asmread '
        '(%d pairs, %d processes: %s). Part L, asmread (the same loop, used in place of the new read kernel) against '
        'oldread: %s lower (%d pairs, %d processes, %d sessions). Part A, the repeat of the 2026-11-13 test, bw_new '
        'read against bw_old read, whole-pass stop, %s: %s lower (%d pairs of process medians, %d sessions). The '
        'percent values of part A are less exact than those of parts L and C. The new read kernel is below the old '
        'read kernel in all %d pairs of part C and in all %d pairs of part A. asmread is below the old read kernel in '
        'all %d pairs of part L and in all %d pairs of part C (%s after read, %s as first interval, %s after oldread). '
        'The size is not one fixed value: control I (idle start, %s, %s) gave %s, and the earlier run F72d12 of the '
        'same boot (not part of the rerun) gave %s. All values come from 1 boot.'
        % (secX, pcr(g_ro[1]), len(g_ro[1]), rng(g_ro[0])['procs'], tags(g_ro[0]), pcr(g_ra[1]), len(g_ra[1]),
           rng(g_ra[0])['procs'], tags(g_ra[0]), pcr(dl), len(dl), gL['procs'], gL['sessions'], secA, pcr(dpa), len(dpa),
           gA['sessions'], len(dcr), len(dpa), len(dl), len(dca), pcr(CG['asmread after read'][1]),
           pcr(CG['asmread first'][1]), pcr(CG['asmread after oldread'][1]), ADDED, NOT_PLAN, pcr(di), pcr(df)))
    w('**Verdict.** ' + V['q1'])
    w('')
    so, sa = rng(L72o + I72o + F72o), rng(L72a + I72a + F72a)
    w('- In the table of section 3.2 the lowest and the highest oldread value are %s GB/s apart (%s and %s GB/s). The '
      'lowest and the highest asmread value are %s GB/s apart (%s and %s GB/s). So the size of the drop follows the '
      'load-only loop.' % (g(so['hi'] - so['lo']), g(so['lo']), g(so['hi']), g(sa['hi'] - sa['lo']), g(sa['lo']), g(sa['hi'])))
    w('')

    # =============================================================================== 4
    from facts_text4 import section4
    ctx = dict(
        cLo=cLo, cLa=cLa, cIo=cIo, cIa=cIa, cFo=cFo, cFa=cFa, cAo=cAo, cCo=cCo, pa3=pa3, newread=newread,
        L72o=L72o, L72a=L72a, I72o=I72o, I72a=I72a, F72o=F72o, F72a=F72a, P12o=P12o, P12a=P12a, PALLo=PALLo,
        PALLa=PALLa, A72o=A72o, A80o=A80o, C72o=C72o, rules=rules, evd=evd, dl=dl, di=di, df=df, CG=CG)
    ctx.update(extra)
    section4(D, N, V, L, ref, q2row, ctx)
    need(sum(1 for r_ in V['q2_rows'] if r_['part'] == 'C' and r_['decides']) == 2,
         'two rows of part C carry a wording by rule V1 point 2 (decision (r))')
    L[i_short:i_short] = short_version(ctx)       # section 0, written last

    # =============================================================================== 7
    w('## 7. Files')
    w('')
    w('Every raw file and script that this sheet uses, one line each. R and S are the folders named at the top.')
    w('')
    missing = [p for p in dict.fromkeys(fd.OPENED) if os.path.abspath(p) not in ref.d]
    need(not missing, 'every file that the script opened is in the file list: %s' % missing)
    for key, (n, desc) in ref.d.items():
        if key.startswith('ext:'):
            w('- [Ref%d] %s' % (n, desc))
        else:
            w('- [Ref%d] `%s`: %s' % (n, rel(key), desc))
    w('')
    w('Output files of this sheet: `S/FACTS.md` (this file) and `S/facts.json` (every interval as one record, plus '
      '"meta" and "verdicts").')
    w('')
    text = '\n'.join(L)
    bad = check_dates(text)
    need(OTHER_DAY and not bad, 'a time of another day stands without its date in the same sentence or cell: %s' % bad[:3])
    return V, text
