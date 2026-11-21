#!/usr/bin/env python3
"""make_q2_html.py --session NAME FOLDER [FOLDER...] [--session NAME FOLDER...] -o PAGE.html [--banner TEXT] [--offsets FILE]

Builds one self-contained HTML result page for question Q2 of the plan (64+56 threads at 256 MiB):
steps B7, B10, B8, B5, B9 and C3, hypotheses H7a, H7b, H8, H9a, H9b, H10 and H11.
FOLDER is a result folder of run_bwx.sh. Folders of other steps may be given. Their processes are not used here.
The page works with one session. "rejected" then cannot occur, because rule 11 of the plan needs two sessions.

The parser and every decision rule come from analyze_bwx.py (which imports decide.py). This file adds only:
  - descriptions without a decision (q, median thread rates per mesh, totals of every interval, counters),
  - the mapping of the results to one of the five words of rule 11, with these page rules, all marked on the page:
      1  the pattern labels split and uniform are not used (user decision 2 of 2026-11-13, decisions.md). A rule that
         needs a label gives "not resolved" (H8, H9a, and the B5 statement when the totals do not decide it).
      2  H11 has one result per kernel and setting (a cell). The word of the page is: "not observed" if every cell is
         "not observed", "rejected" if every cell with another word is "rejected", "not rejected" if at least one
         cell is "not rejected" and none is "rejected", and "not resolved" otherwise.
      3  H9b: with fewer than 2 sessions "not tested". With 2 or more: "not observed" if the ranges of q of
         old read at 64+56 threads overlap between all sessions, and "not resolved" otherwise (no label).
         The user has not approved this rule. The page marks H9b "open for the user".
      4  H10 is "not tested": no step of Parts B and C tests a bounded prediction of H10, and Part D was not run.
  - for every hypothesis: the output of the analysis script as it stands, next to the word of the page, and the
    other reading with its reason where two readings exist. A judgment is marked "open for the user".
Text that interprets data is built from computed values. Typed text is limited to definitions, the wording of
the plan and of the handoff, the limits, and the references.
"""
import argparse, calendar, glob, html, os, re, sys, time
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
CRB = os.path.abspath(os.path.join(HERE, '..', '..'))
BWX_DIR = os.environ.get('BWX_ANALYSIS_DIR') or os.path.join(CRB, 'tmp', 'agent-scratch', 'bwx-2026-11-13')
for _d in (BWX_DIR, os.path.join(HERE, '..', 'partA-analysis')):
    sys.path.insert(0, os.path.abspath(_d))
import analyze_bwx as A            # noqa: E402  parser and decisions
import make_partA_html as PA       # noqa: E402  style and number format of the Part A page

fx, fs, e, pl, CSS, ID = PA.fx, PA.fs, PA.e, PA.pl, PA.CSS, PA.ID
C0, C1, C2, INK, MUTED, GRID, BAND = PA.C0, PA.C1, PA.C2, PA.INK, PA.MUTED, PA.GRID, PA.BAND
STEPS = ['B7', 'B10', 'B8', 'B5', 'B9', 'C3']
OFFSETS = os.path.join(BWX_DIR, 'crb-build-2', 'offsets.tsv')
KN = dict(oldread='old read', read='new read', asmread='asm read', asmread2='asm read 2', oldwrite='old write', write='new write',
          asmwrite='asm write', asmwrite2='asm write 2', read_sparse='read_sparse', read_nop4='read_nop4', read_nop8='read_nop8',
          read_nop16='read_nop16', read_nop32='read_nop32')
EVN = dict(cycles='cycles', instructions='instructions', l1d_refill='L1 refills', l2d_refill='L2 refills', ll_read_miss='last-level read misses')
REPRO = 'pass/500/common'


def med(v):
    v = [x for x in v if x is not None]
    return median(v) if v else None


def f(v, nd=2):
    return '-' if v is None else fx(v, nd)


def rng(vals, nd=2):
    v = [x for x in vals if x is not None]
    if not v:
        return '-'
    a, b = fx(min(v), nd), fx(max(v), nd)
    return a if a == b else f'{a} to {b}'


def fs(v, nd=2):
    """As fx, with a sign. A value that prints as zero carries no sign."""
    t = PA.fs(v, nd)
    return t.lstrip('+-') if float(t) == 0 else t


def utc(t):
    """'2026-11-14T02:43:52Z' -> seconds since 1970, or None."""
    try:
        return calendar.timegm(time.strptime(t, '%Y-%m-%dT%H:%M:%SZ'))
    except (TypeError, ValueError):
        return None


def hm(sec):
    """A duration in plain words."""
    sec = int(round(sec))
    if sec < 120:
        return f'{sec} s'
    h, mnt = divmod(int(round(sec / 60)), 60)
    return (f'{h} h {mnt} min' if h else f'{mnt} min')


def clock(t):
    return time.strftime('%H:%M:%S', time.gmtime(t))


def folder_step(path):
    return os.path.basename(path.rstrip('/')).split('-')[0]


def sname(s):
    """Plain name of a setting stop/min_ms/start."""
    stop, ms, start = s.split('/')
    return f"{'whole passes' if stop == 'pass' else 'common stop'}, {int(ms) / 1000:g} s, {'common start' if start == 'common' else 'offset start'}"


def skey(s):
    stop, ms, start = s.split('/')
    return (stop != 'pass', int(ms), start != 'common')


# ---------------------------------------------------------------- model (computed values only)

def ivstat(iv):
    r = [(x['cpu'], x['bytes'] / x['elapsed'] / 1e9) for x in iv.rows]
    a = [v for c, v in r if c in A.MESH0_CPUS]
    b = [v for c, v in r if c not in A.MESH0_CPUS]
    return dict(hist=iv.hist, msum=iv.msum, q=iv.q, m0=med(a), m1=med(b), mh0=iv.mesh_hist[0], mh1=iv.mesh_hist[1],
                minpass=min(x['passes'] for x in iv.rows), entry=iv.entry, round=iv.round, pos=iv.pos)


def agg(stats):
    if not stats:
        return None
    g = lambda k: [s[k] for s in stats]
    return dict(n=len(stats), hist=med(g('hist')), hist_min=min(g('hist')), hist_max=max(g('hist')), msum=med(g('msum')),
                q=med(g('q')), q_min=min(g('q')), q_max=max(g('q')), m0=med(g('m0')), m1=med(g('m1')),
                mh0=med(g('mh0')), mh1=med(g('mh1')))


def regular(p, entry=None):
    return [iv for iv in p.ordered if not iv.irregular and (entry is None or iv.entry == entry)]


def read_env(folder):
    out = dict(folder=os.path.basename(folder.rstrip('/')), present=False, busy=[])
    path = os.path.join(folder, 'env.txt')
    if not os.path.exists(path):
        return out
    out['present'] = True
    inbusy = False
    for line in open(path, errors='replace'):
        m = re.match(r'## host=\S+ utc=(\S+) loadavg=(\S+) \S+ \S+ (\d+)/(\d+) \S+ logins=(\S+) step=(\S+) steps=(.*)', line)
        if m:
            out.update(start_utc=m.group(1), start_load=float(m.group(2)), start_runnable=int(m.group(3)), start_logins=m.group(5), steps=m.group(7).strip())
        m = re.match(r'## end utc=(\S+) loadavg=(\S+)', line)
        if m:
            out.update(end_utc=m.group(1), end_load=float(m.group(2)))
        m = re.match(r'## uptime=([\d.]+)', line)
        if m:
            out['uptime'] = float(m.group(1))
        if line.startswith('## settings:'):
            out['settings'] = dict(kv.split('=', 1) for kv in re.findall(r'(\w+=(?:[^=]*?))(?= \w+=|$)', line[len('## settings:'):].strip()))
        if line.startswith('##'):
            inbusy = line.startswith('## busiest processes')
        elif inbusy:
            m = re.match(r'\s*([\d.]+)\s+(\S+)\s+(\S.*)$', line)
            if m:
                out['busy'].append((float(m.group(1)), m.group(2), m.group(3).strip()))
    return out


def read_launches(folder):
    """launches.txt: the second reading before each launch, and the 5 busiest processes."""
    path = os.path.join(folder, 'launches.txt')
    out = []
    if not os.path.exists(path):
        return out
    cur = None
    for line in open(path, errors='replace'):
        m = re.match(r'== (\S+) (\S+) utc (\S+) loadavg (\S+) \S+ \S+ (\d+)/(\d+) logins (\S+)', line)
        if m:
            cur = dict(step=m.group(1).split('.')[0], tag=m.group(2), utc=m.group(3), load=float(m.group(4)), runnable=int(m.group(5)), logins=m.group(7), busy=[],
                       folder=os.path.basename(folder.rstrip('/')))
            out.append(cur)
            continue
        m = re.match(r'\s*([\d.]+)\s+(\S+)\s+(\S.*)$', line)
        if m and cur is not None:
            cur['busy'].append((float(m.group(1)), m.group(2), m.group(3).strip()))
    return out


BUSY_LIMIT = 10.0          # % of one CPU: a process of another account above this value is listed by name


def load_model(procs, folders):
    out = {}
    launches = [x for fo in folders for x in read_launches(fo)]
    own = {u for x in launches for _, u, c in x['busy'] if re.sub(r'[/:].*$', '', c) in ('bash', 'ps', 'bwx')}
    for step in STEPS:
        g = [p for p in procs if p.step == step]
        if not g:
            continue
        run = [int(p.runnable.split('/')[0]) for p in g if re.fullmatch(r'\d+/\d+', p.runnable or '')]
        la = [x for x in launches if x['step'] == step]
        busy = {}
        for x in la:
            for pc, user, comm in x['busy']:
                k = (user, re.sub(r'[/:].*$', '', comm))
                busy[k] = max(busy.get(k, 0.0), pc)
        other = sorted(((v, u, c) for (u, c), v in busy.items() if u not in own), reverse=True)
        mine = sorted(((v, u, c) for (u, c), v in busy.items() if u in own), reverse=True)
        logins = [int(p.logins) for p in g if str(p.logins).isdigit()]
        # every launch at which a process of another account is above BUSY_LIMIT
        ev = [dict(step=step, tag=x['tag'], utc=x['utc'], load=x['load'], runnable=x['runnable'], pc=pc, user=u, comm=re.sub(r'[/:].*$', '', c), n_launches=len(la))
              for x in la for pc, u, c in x['busy'] if u not in own and pc > BUSY_LIMIT]
        runs = run + [x['runnable'] for x in la]
        logs = logins + [int(x['logins']) for x in la if x['logins'].isdigit()]
        out[step] = dict(n=len(g), utc=(g[0].utc, g[-1].utc), load_min=min((p.load1 for p in g if p.load1 is not None), default=None),
                         load_max=max((p.load1 for p in g if p.load1 is not None), default=None), first_load=g[0].load1,
                         runnable_max=max(run) if run else None, n_waited=sum(1 for p in g if p.waited_s),
                         wait_max=max((p.waited_s for p in g if p.waited_s is not None), default=None), logins_max=max(logins) if logins else None,
                         n_launches_txt=len(la), runnable_txt_max=max((x['runnable'] for x in la), default=None),
                         logins_txt_max=max((int(x['logins']) for x in la if x['logins'].isdigit()), default=None),
                         runnable_min=min(runs) if runs else None, runnable_all_max=max(runs) if runs else None,
                         logins_all_max=max(logs) if logs else None, n_log_readings=len(logs),
                         busy_other=other[:2], busy_own=mine[:2], threads_max=max(p.threads for p in g), other_events=ev)
    return out


def timing_model(env_all, names):
    """env_all {session: [env of every folder given]} -> start, end and distances of the sessions (from env.txt)."""
    out = dict(sessions={}, gaps=[], same_step=None, same_boot=None, visits={})
    allv = []
    for s in names:
        ev = [x for x in env_all[s] if x['present'] and utc(x.get('start_utc')) is not None]
        for x in ev:
            allv.append(dict(x, session=s, t0=utc(x['start_utc']), t1=utc(x.get('end_utc'))))
        if ev:
            ends = [utc(x.get('end_utc')) for x in ev if utc(x.get('end_utc')) is not None]
            out['sessions'][s] = dict(t0=min(utc(x['start_utc']) for x in ev), t1=max(ends) if ends else None, n=len(ev))
    allv.sort(key=lambda x: x['t0'])
    # the visit before each folder: the folder that ended last before this one started (any session, any step given)
    for i, x in enumerate(allv):
        prev = [y for y in allv[:i] if y['t1'] is not None and y['t1'] <= x['t0']]
        p = max(prev, key=lambda y: y['t1']) if prev else None
        out['visits'][(x['session'], x['folder'])] = dict(gap=(x['t0'] - p['t1']) if p else None, prev_steps=p.get('steps') if p else None,
                                                          prev_folder=p['folder'] if p else None, prev_session=p['session'] if p else None)
    have = [s for s in names if s in out['sessions']]
    for a, b in zip(have, have[1:]):
        if out['sessions'][a]['t1'] is not None:
            out['gaps'].append((a, b, out['sessions'][b]['t0'] - out['sessions'][a]['t1']))
    if len(have) >= 2:
        a, b = have[0], have[1]
        fa = {folder_step(x['folder']): utc(x['start_utc']) for x in env_all[a] if x['present'] and 'start_utc' in x}
        fb = {folder_step(x['folder']): utc(x['start_utc']) for x in env_all[b] if x['present'] and 'start_utc' in x}
        d = [fb[k] - fa[k] for k in fa if k in fb]
        if d:
            out['same_step'] = (a, b, min(d), max(d), len(d))
    boots = [x['t0'] - x['uptime'] for x in allv if x.get('uptime') is not None]
    if len(boots) == len(allv) and boots:
        out['same_boot'] = (max(boots) - min(boots)) < 30          # the boot time computed from each reading agrees within 30 s
        out['boot_n'] = len(boots)
    return out


def b7_model(procs, res):
    main = [p for p in procs if p.complete and len(p.seq) > 1]
    single = [p for p in procs if p.complete and len(p.seq) == 1]
    out = dict(res=res, n_main=len(main), n_single=len(single), kern={}, single={}, fail2={}, skew_pass_ms=None, procs=main)
    for s in sorted({p.setting for p in main}, key=skey):
        g = [p for p in main if p.setting == s]
        out['kern'][s] = {k: agg([ivstat(iv) for p in g for iv in regular(p, k)]) for k in ('oldread', 'read', 'asmread', 'asmread2')}
        if s.startswith('pass/'):
            ivs = [ivstat(iv) for p in g for iv in regular(p)]
            out['fail2'][s] = (sum(1 for x in ivs if x['minpass'] < 50), len(ivs), min((x['minpass'] for x in ivs), default=None))
    for k in ('oldread', 'read', 'asmread', 'asmread2'):
        out['single'][k] = agg([ivstat(iv) for p in single if p.seq[0] == k for iv in regular(p)])
    ivs = [ivstat(iv) for p in single if p.stop == 'pass' for iv in regular(p)]          # the 2 % check of rule 7 also applies here
    out['fail2_single'] = (sum(1 for x in ivs if x['minpass'] < 50), len(ivs), min((x['minpass'] for x in ivs), default=None)) if ivs else None
    sk = [iv.skew * 1e3 for p in main + single if p.stop == 'pass' for iv in p.ordered]
    out['skew_pass_ms'] = max(sk) if sk else None
    # The setting for the later steps (handoff B.9, "Settings after B7"): resolved, --stop common, largest |median D|.
    cand = [(abs(v['metrics']['M_hist']['median_D']), s) for s, v in res['settings'].items() if v['decision'] == 'resolved' and s.startswith('common/')]
    out['chosen'] = max(cand)[1] if cand else None
    out['rep'] = None
    return out


def b7_rep(b, used):
    """Representative interval pair. The setting: the one that B8, B5 and B9 of the session ran in (used, from their header
    lines) if it is one setting of B7. Else the setting that the handoff rule selects, else the reproduction condition,
    else the first setting. The process: the first in the file. Its first regular old read and new read interval."""
    kern = b['kern']
    if used and used in kern:
        rs, why = used, 'used'
    elif b['chosen']:
        rs, why = b['chosen'], 'chosen'
    else:
        rs, why = (REPRO if REPRO in kern else (sorted(kern, key=skey)[0] if kern else None)), 'fallback'
    for p in b['procs']:
        if p.setting == rs and regular(p, 'oldread') and regular(p, 'read'):
            o, n = regular(p, 'oldread')[0], regular(p, 'read')[0]
            pts = lambda iv: sorted((x['cpu'], x['bytes'] / x['elapsed'] / 1e9) for x in iv.rows)
            b['rep'] = dict(setting=rs, why=why, tag=p.tag, file=p.file, old=pts(o), new=pts(n), old_s=ivstat(o), new_s=ivstat(n))
            break


def b10_model(procs, res):
    used = [p for p in procs if p.complete]
    out = dict(res=res, settings={}, fail2={})
    for s in sorted(res['settings'], key=skey):
        g = [p for p in used if p.setting == s]
        ks = {}
        for k in ('oldwrite', 'write', 'asmwrite', 'asmwrite2'):
            tot, hl = [], []
            for p in g:
                ivs = p.rate_by_entry.get(k, [])
                tot += [(iv.hist, p.tag, iv.round, iv.pos, sum(x['passes'] for x in iv.rows)) for iv in ivs if not iv.irregular]
                if ivs and not any(iv.irregular for iv in ivs):
                    hi, lo = max(ivs, key=lambda iv: iv.hist), min(ivs, key=lambda iv: iv.hist)      # as a_b10 does
                    hl.append(dict(tag=p.tag, hi=hi.hist, lo=lo.hist, hi_mesh=hi.mesh_hist, lo_mesh=lo.mesh_hist))
            v = sorted(t[0] for t in tot)
            ks[k] = dict(totals=tot, hl=hl, gap=max((b - a for a, b in zip(v, v[1:])), default=None),
                         lo=v[0] if v else None, hi=v[-1] if v else None, med=med(v))
        out['settings'][s] = ks
        if s.startswith('pass/'):                               # the 2 % check of rule 7 (whole passes only)
            mp = [min(x['passes'] for x in iv.rows) for p in g for iv in regular(p)]
            out['fail2'][s] = (sum(1 for x in mp if x < 50), len(mp), min(mp, default=None), max(mp, default=None))
    return out


def b8_model(procs, res):
    used = [p for p in procs if p.complete]
    out = dict(res=res, kern={}, counts=sorted({p.threads_mesh1 for p in used}), mesh0=sorted({p.threads_mesh0 for p in used}),
               settings=sorted({p.setting for p in used}), n=len(used), aa_q=None)
    for k in ('oldread', 'asmread', 'asmread2'):
        out['kern'][k] = {b: [ivstat(iv) for p in used if p.threads_mesh1 == b for iv in regular(p, k)] for b in out['counts']}
    dq = []
    for p in used:                                             # A/A description: q of neighbouring asm read and asm read 2 intervals
        for a, b in zip(p.ordered, p.ordered[1:]):
            if {a.entry, b.entry} == {'asmread', 'asmread2'} and not (a.irregular or b.irregular):
                dq.append(abs(a.q - b.q))
    out['aa_q'] = max(dq) if dq else None
    return out


def b5_model(procs, res):
    used = [p for p in procs if p.complete]
    entries = list(dict.fromkeys(en for p in used for en in (p.seq if 'oldread' in p.seq[:1] else p.seq[::-1])))
    return dict(res=res, n=len(used), entries=entries, settings=sorted({p.setting for p in used}),
                kern={k: [dict(ivstat(iv), tag=p.tag) for p in used for iv in regular(p, k)] for k in entries})


def b9_model(procs, res):
    used = [p for p in procs if p.complete]
    out = dict(res=res, kinds={}, settings=sorted({p.setting for p in used}))
    for name, flag in (('one_buffer', False), ('two_buffers', True)):
        g = [p for p in used if p.two_buffers == flag]
        out['kinds'][name] = dict(n=len(g), ivs=[dict(ivstat(iv), tag=p.tag) for p in g for iv in regular(p)],
                                  pv=[(p.tag, median(iv.hist for iv in p.ordered)) for p in g if not any(iv.irregular for iv in p.ordered)])
    return out


def c3_model(procs, res):
    used = [p for p in procs if p.complete]
    out = dict(res=res, n=len(used), cpu={}, lowest=None, n_rows=0, n_below99=0)
    for p in used:
        for c in p.C:
            iv = p.raw.get((c['round'], c['pos']))
            t = next((x for x in iv.rows if x['tid'] == c['tid']), None) if iv else None
            if t is None or not c['cputime'] or c['cputime'] <= 0:
                continue
            share = c['cputime'] / (t['elapsed'] * 1e9)
            off_ms = t['elapsed'] * 1e3 - c['cputime'] / 1e6
            g = out['cpu'].setdefault(p.min_ms, dict(n=0, share_min=share, off_max=off_ms, below99=0))
            g['n'] += 1
            g['share_min'], g['off_max'] = min(g['share_min'], share), max(g['off_max'], off_ms)
            g['below99'] += share < 0.99
            out['n_rows'] += 1
            out['n_below99'] += share < 0.99
            if out['lowest'] is None or share < out['lowest']['share']:
                out['lowest'] = dict(share=share, off_ms=off_ms, cpu=c['cpu'], kernel=c['kernel'], tag=p.tag, elapsed=t['elapsed'])
    # per kernel and mesh: the group medians of the analysis (one group = one setting and sequence)
    out['km'] = {}
    for g in res.get('groups', []):
        out['km'].setdefault((g['entry'], g['mesh']), []).append(g)
    return out


def old_q_at_full(procs):
    """(q, total) of every regular old read interval with one buffer at the full thread count (64+56 on CRB), for H9b."""
    full = max((p.threads for p in procs), default=0)
    return [(iv.q, iv.hist) for p in procs if p.complete and p.step in ('B7', 'B5', 'B9', 'B8') and not p.two_buffers and p.threads == full
            for iv in regular(p, 'oldread')]


def norm(word):
    """A word of the analysis -> one of the five words of rule 11 (plus the plan's word in brackets, kept apart)."""
    for w in ('not rejected', 'rejected', 'not observed', 'not resolved', 'not tested'):
        if word.startswith(w):
            return w
    return 'not resolved'


def word_of(flags):
    """flags {session: fail | hold | not observed | not resolved} -> one of the five words. The rule is two_sessions() of
    analyze_bwx.py. Added here: if no session gives 'fail' or 'hold' and at least one gives 'not resolved', the word is 'not resolved'."""
    f_ = list(flags.values())
    if not f_:
        return 'not tested'
    if all(x in ('not resolved', 'not observed') for x in f_) and 'not resolved' in f_:
        return 'not resolved'
    return norm(A.two_sessions(flags))


PLAN_OLD_LOW = (365.10, 368.25)     # plan, item 10: totals of old read on 2026-10-30 (GB/s). A number of an earlier folder, for H9b only.


def join_and(items):
    items = list(items)
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1] if items else ''


def rngs(vals, nd=2):
    v = [x for x in vals if x is not None]
    return '-' if not v else fs(min(v), nd) if len(v) == 1 or fs(min(v), nd) == fs(max(v), nd) else f'{fs(min(v), nd)} to {fs(max(v), nd)}'


def larger_with(c, change):
    """The factor value of the setting with the larger value (change = first minus second)."""
    stop, ms, start = (c['second'] if change < 0 else c['first']).split('/')
    if c['factor'] == 'stop':
        return 'the common stop' if stop == 'common' else 'whole passes'
    if c['factor'] == 'interval':
        return f'the {int(ms) / 1000:g} s interval'
    return 'the offset start' if start == 'offset' else 'the common start'


def isare(n):
    return 'is' if n == 1 else 'are'


def flag_txt(flags):
    return ', '.join(f'{s}: {v}' for s, v in flags.items()) or '-'


TWO_WORDS = ('Rule 11 of the plan has two words that fit this case. "rejected": the bounded prediction (a resolved change) failed in every session. '
             '"not resolved": the difference is inside the A/A spread. The plan words the outcome of this step as "no resolved contribution". '
             'The analysis script maps "no resolved change" to a failed prediction, and its authors call that mapping their own reading.')


def hypotheses(m):
    """One row per hypothesis of Q2. Every word is computed.
    word   = the word of this page.            strict = the output of the analysis script (or of the plan's rule) as it stands.
    other  = another reading of the same data, with its reason.     open = what the user must decide ('' if nothing)."""
    S, hyp, names = m['S'], m['summary']['hypotheses'], m['sessions']
    one = len(names) < 2
    rows = []

    def have(step):
        return [s for s in names if step in S[s]]

    def add(label, meaning, text, step, word, n, aa, basis, flags, plan_word='', strict='-', other='', open_='', short=''):
        rows.append(dict(label=label, meaning=meaning, text=text, step=step, word=word, n=n, aa=aa, basis=basis, flags=flags, plan_word=plan_word,
                         strict=strict, other=other, open=open_, short=short,
                         one_session=one and word == 'not rejected' and any(v == 'fail' for v in flags.values())))

    def strict_of(key):
        h = hyp.get(key)
        return f'"{h["word"]}" ({flag_txt(h["per_session"])})' if h else 'no entry'

    # ---- H7a, H7b for read (B7)
    for hl, key, meaning, text, factors in (
            ('H7a, read', 'H7a (B7, read)', 'the stop method and the short interval make a part of the read difference', 'D changes by a resolved amount when the stop method or the interval changes', ('stop', 'interval')),
            ('H7b, read', 'H7b (B7, read)', 'the common start makes a part of the read difference', 'D changes by a resolved amount when the start changes', ('start',))):
        ss = have('B7')
        if not ss:
            add(hl, meaning, text, 'B7', 'not tested', '-', '-', f'{ID}: no B7 process in the input.', {}, short='no B7 process in the input'); continue
        flags = hyp.get(key, {}).get('per_session', {})
        parts, allch, allres, medD = [], [], [], {}
        for s in ss:
            res = S[s]['B7']['res']
            ch = [c for c in res['changes'].values() if c['factor'] in factors and c['metrics']['M_hist']['change'] is not None]
            r = [c for c in ch if c['decision'] == 'resolved']
            medD[s] = med([v['metrics']['M_hist']['median_D'] for v in res['settings'].values()])
            allch += [(s, c) for c in ch]; allres += [(s, c) for c in r]
            parts.append(f"Session {s}: {len(r)} of {len(ch)} comparisons of two settings {isare(len(r))} resolved"
                         + (f" ({join_and(fs(c['metrics']['M_hist']['change']) for c in r)} GB/s, first setting minus second)" if r else '') + '.')
        chg = lambda c: c['metrics']['M_hist']['change']
        lim = lambda c: c['metrics']['M_hist']['sum_of_aa_spreads']
        if allres:
            cnt = {}
            for s, c in allres:
                cnt[larger_with(c, chg(c))] = cnt.get(larger_with(c, chg(c)), 0) + 1
            parts.append('In the resolved comparisons D is larger with ' + join_and(f'{k} ({n} of {len(allres)})' for k, n in cnt.items()) + '.')
            bs, bc = max(allres, key=lambda t: abs(chg(t[1])))
            if medD[bs]:
                parts.append(f'The largest resolved change is {fx(abs(chg(bc)) / abs(medD[bs]) * 100, 1)} % of the median D of session {bs}.')
        unres = [(s, c) for s, c in allch if c['decision'] != 'resolved']
        if unres:
            inside = sum(1 for _, c in unres if abs(chg(c)) <= lim(c))
            parts.append(f"The {pl(len(unres), 'change that is not resolved is', 'changes that are not resolved are')} {rngs([chg(c) for _, c in unres])} GB/s. "
                         f"{'Its limit (sum of the two A/A spreads) is' if len(unres) == 1 else 'Their limits (sum of the two A/A spreads) are'} {rng([lim(c) for _, c in unres])} GB/s. "
                         f"{inside} of {len(unres)} {'lies' if inside == 1 else 'lie'} inside the limit.")
        if allch and not allres and all(medD.values()):
            parts.append(f"So this test could not show a contribution below its limit, which is up to {fx(max(lim(c) for _, c in allch) / min(abs(v) for v in medD.values()) * 100, 1)} % of the median D.")
        nset = sum(len(S[s]['B7']['res']['settings']) for s in ss); nresD = sum(1 for s in ss for v in S[s]['B7']['res']['settings'].values() if v['decision'] == 'resolved')
        parts.append(f"D itself is resolved in {nresD} of {nset} settings" + (', so no timing setting removes it.' if nresD == nset else '.'))
        aa = [v['metrics']['M_hist']['aa_spread'] for s in ss for v in S[s]['B7']['res']['settings'].values()]
        w = word_of(flags)
        add(hl, meaning, text, 'B7', w, ', '.join(f"{s}: {S[s]['B7']['n_main']} with all kernels, {S[s]['B7']['n_single']} with one kernel" for s in ss),
            f'{rng(aa)} GB/s over the settings', ' '.join(parts), flags, strict=strict_of(key),
            other=TWO_WORDS if w == 'rejected' else '', open_='"rejected" or "not resolved"' if w == 'rejected' else '',
            short='resolved comparisons of two settings: ' + join_and(f"{sum(1 for x, _ in allres if x == s)} of {sum(1 for x, _ in allch if x == s)} in {s}" for s in ss))
    # ---- H7a, H7b for write (B10)
    for hl, key, meaning, text, factors in (
            ('H7a, write', 'H7a (B10, write)', 'the stop method and the short interval make a part of the separate write totals', 'the spread of a write kernel changes by a resolved amount when the stop method or the interval changes', ('stop', 'interval')),
            ('H7b, write', 'H7b (B10, write)', 'the common start makes a part of the separate write totals', 'the spread of a write kernel changes by a resolved amount when the start changes', ('start',))):
        ss = have('B10')
        if not ss:
            add(hl, meaning, text, 'B10', 'not tested', '-', '-', f'{ID}: no B10 process in the input.', {}, short='no B10 process in the input'); continue
        flags = hyp.get(key, {}).get('per_session', {})
        parts, allch, allres = [], [], []
        for s in ss:
            sc = S[s]['B10']['res']['spread_changes']
            ch = [c for c in sc.values() if c['factor'] in factors and c['change_of_spread'] is not None]
            r = [c for c in ch if c['decision'] == 'resolved']
            allch += [(s, c) for c in ch]; allres += [(s, c) for c in r]
            parts.append(f"Session {s}: {len(r)} of {len(ch)} comparisons (one kernel, two settings) {isare(len(r))} resolved.")
            for c in r:
                parts.append(f"The resolved one: {KN[c['kernel']]}, {c['factor']}, \"{sname(c['first'])}\" minus \"{sname(c['second'])}\": the median spread changes by {fs(c['change_of_spread'])} GB/s, limit {f(c['sum_of_controls'])} GB/s.")
                twin = {'asmwrite': 'asmwrite2', 'asmwrite2': 'asmwrite'}.get(c['kernel'])
                t = next((x for x in sc.values() if x['kernel'] == twin and (x['factor'], x['first'], x['second']) == (c['factor'], c['first'], c['second'])), None)
                if t and t['change_of_spread'] is not None:
                    parts.append(f"The second copy of the same loop ({KN[twin]}) in the same two settings: {fs(t['change_of_spread'])} GB/s, {t['decision']}.")
        if allres:
            none = [k for k in ('oldwrite', 'write', 'asmwrite', 'asmwrite2') if not any(c['kernel'] == k for _, c in allres)]
            if none:
                parts.append(f"No comparison of {join_and(KN[k] for k in none)} is resolved in any session.")
            parts.append(f"{len(allch)} comparisons were made, with no correction for their number.")
        unres = [(s, c) for s, c in allch if c['decision'] != 'resolved']
        if unres:
            inside = sum(1 for _, c in unres if abs(c['change_of_spread']) <= c['sum_of_controls'])
            parts.append(f"The {len(unres)} changes that are not resolved are {rngs([c['change_of_spread'] for _, c in unres])} GB/s. Their limits (sum of the two controls of the spread) are {rng([c['sum_of_controls'] for _, c in unres])} GB/s. "
                         f"{inside} of {len(unres)} {'lies' if inside == 1 else 'lie'} inside the limit.")
        if allch and not allres:
            sp = [x for s in ss for v in S[s]['B10']['res']['settings'].values() for kk in v['kernels'].values() for x in [kk['median_spread']] if x is not None]
            parts.append(f"The median spread of a kernel in a setting is {rng(sp)} GB/s. So only a change as large as most spreads could have been resolved.")
        cs = [v['control_spread'] for s in ss for v in S[s]['B10']['res']['settings'].values()]
        w = word_of(flags)
        add(hl, meaning, text, 'B10', w, ', '.join(f"{s}: {S[s]['B10']['res']['n_used']}" for s in ss), f'{rng(cs)} GB/s (control of the spread, over the settings)',
            ' '.join(parts), flags, strict=strict_of(key),
            other=('' if w != 'rejected' else TWO_WORDS if not any(r['other'] == TWO_WORDS for r in rows) else 'The same two readings of rule 11 as for H7b, read.'),
            open_='"rejected" or "not resolved"' if w == 'rejected' else '',
            short='resolved comparisons of two settings: ' + join_and(f"{sum(1 for x, _ in allres if x == s)} of {sum(1 for x, _ in allch if x == s)} in {s}" for s in ss))
    # ---- H11 (page rule 2)
    ss = have('B10')
    cells = {k: v for k, v in hyp.items() if k.startswith('H11 (B10')}
    meaning, text = 'the higher write totals come from the threads of one mesh', 'in an interval with a higher total, one mesh is faster by a resolved amount and the other is not'
    if not ss or not cells:
        add('H11', meaning, text, 'B10', 'not tested', '-', '-', f'{ID}: no B10 process in the input.', {}, short='no B10 process in the input')
    else:
        w = [norm(v['word']) for v in cells.values()]
        cnt = {x: w.count(x) for x in ('not rejected', 'rejected', 'not observed', 'not resolved')}
        word = 'not observed' if cnt['not observed'] == len(w) else 'rejected' if cnt['rejected'] and cnt['rejected'] == len(w) - cnt['not observed'] else \
            'not rejected' if cnt['not rejected'] and not cnt['rejected'] else 'not resolved'
        per = {s: {x: sum(1 for v in cells.values() if v['per_session'].get(s) == x) for x in ('supported', 'contradicted', 'not observed', 'not resolved')} for s in ss}
        both = sum(1 for v in cells.values() if len(v['per_session']) > 1 and all(x == 'supported' for x in v['per_session'].values()))
        ct = [v['control_total'] for s in ss for v in S[s]['B10']['res']['settings'].values() if v['control_total'] is not None]
        parts = ['A cell is one kernel in one setting. ' + ' '.join(
            f"Session {s}: " + join_and(f"{n} {x}" for x, n in per[s].items() if n) + '.' for s in ss)]
        sup = []
        for s in ss:
            b = S[s]['B10']
            for st in b['settings']:
                v = b['res']['settings'][st]
                for k in b['settings'][st]:
                    if v['kernels'][k]['H11'] != 'supported':
                        continue
                    hl_ = [h for h in b['settings'][st][k]['hl'] if (h['hi'] - h['lo']) > v['control_total']]
                    d = {0: [h['hi_mesh'][0] - h['lo_mesh'][0] for h in hl_], 1: [h['hi_mesh'][1] - h['lo_mesh'][1] for h in hl_]}
                    c = {0: v['control_mesh0'], 1: v['control_mesh1']}
                    rose = [i for i in (0, 1) if all(abs(x) > c[i] for x in d[i])]
                    sup.append(dict(s=s, st=st, k=k, rose=rose, d=d, c=c, n=len(hl_)))
        if not one:
            parts.append(f"{both} of {len(w)} cells are supported in every session. The merged cells are: " + join_and(f"{n} {x}" for x, n in cnt.items() if n) + '.')
        for x in sup:
            if len(x['rose']) == 1:
                i = x['rose'][0]; j = 1 - i
                parts.append(f"Supported in {x['s']}: {KN[x['k']]} with \"{sname(x['st'])}\". Mesh {i} rose by {rng(x['d'][i])} GB/s (control {f(x['c'][i])} GB/s) in its {x['n']} counted processes. "
                             f"Mesh {j} changed by {rngs(x['d'][j])} GB/s, below its control of {f(x['c'][j])} GB/s.")
        rs = {x['rose'][0] for x in sup if len(x['rose']) == 1}
        if len(sup) > 1:
            parts.append('The supported cells name different meshes.' if len(rs) > 1 else f"The supported cells all name mesh {next(iter(rs))}." if rs else '')
        add('H11', meaning, text, 'B10', word, ', '.join(f"{s}: {S[s]['B10']['res']['n_used']} (4 per setting)" for s in ss), f'{rng(ct)} GB/s (control of the total, over the settings)',
            ' '.join(p for p in parts if p), {s: join_and(f"{n} {x}" for x, n in per[s].items() if n) for s in ss},
            plan_word='supported' if word == 'not rejected' else 'contradicted' if word == 'rejected' else '',
            strict='one word per cell: ' + join_and(f'{n} "{x}"' for x, n in cnt.items() if n),
            short='one mesh rose alone in ' + join_and(f"{per[s]['supported']} of {len(w)} cells in {s}" for s in ss) + ('' if one else f'. Cells in which it did so in every session: {both}'))
        rows[-1]['cells'] = cnt
    # ---- H8 (page rule 1)
    ss = have('B8')
    meaning, text = 'a loop that only loads reaches the uniform state at a lower thread count than old read', 'asm read changes to the uniform pattern at a lower count of mesh-1 threads than old read'
    if not ss:
        add('H8', meaning, text, 'B8', 'not tested', '-', '-', f'{ID}: no B8 process in the input.', {}, short='no B8 process in the input')
    else:
        aq = [S[s]['B8']['aa_q'] for s in ss if S[s]['B8']['aa_q'] is not None]
        nb = sum(1 for s in ss for kv in S[s]['B8']['res'].get('kernels', {}).values() if kv.get('bracket'))
        parts = ['The bracket rule needs the labels split and uniform, which are not used. ' + ('No bracket was formed by the label rule in any session.' if not nb else f'The label rule formed {pl(nb, "bracket", "brackets")}.')]
        counts = sorted({c for s in ss for c in S[s]['B8']['counts']})
        if counts:
            qat = lambda k, c: [i['q'] for s in ss for i in S[s]['B8']['kern'][k].get(c, [])]
            c0, cN = counts[0], counts[-1]
            m0 = S[ss[0]]['B8']['mesh0'][0] if S[ss[0]]['B8']['mesh0'] else 64
            parts.append(f"Without labels: at {m0}+{c0} threads q is {rng(qat('asmread', c0), 3)} for asm read and {rng(qat('oldread', c0), 3)} for old read. "
                         f"At {m0}+{cN} threads q is {rng(qat('asmread', cN), 3)} for asm read and {rng(qat('oldread', cN), 3)} for old read.")
        w8 = hyp.get('H8 (B8)', {}).get('word', '')
        add('H8', meaning, text, 'B8', 'not resolved', ', '.join(f"{s}: {S[s]['B8']['n']}" for s in ss),
            (f'{f(max(aq), 3)} (largest difference of q between neighbouring asm read and asm read 2 intervals, no unit)' if aq else '-'),
            ' '.join(parts), {s: 'not resolved' for s in ss}, plan_word='labels not used' + ('' if nb else ', no bracket formed'), strict=strict_of('H8 (B8)') + ', from the label rule',
            other=('' if w8.endswith('not resolved') else 'The label rule gives another word. It is not used: user decision 2 of 2026-11-13.'),
            short='the rule needs the pattern labels, which are not used')
    # ---- B5 statement
    ss = have('B5')
    meaning, text = 'B5 tests whether a loop without vector adds can show the total of old read', 'statement of B5: vector adds are needed for the pattern and total of old read'
    b5key = next((k for k in hyp if k.startswith('B5 statement')), None)
    if not ss:
        add('B5 statement', meaning, text, 'B5', 'not tested', '-', '-', f'{ID}: no B5 process in the input.', {}, short='no B5 process in the input')
    else:
        flags, aa, parts = {}, [], []
        for s in ss:
            v = S[s]['B5']['res']['variants'].get('read_sparse')
            if not v or v['total_difference']['decision'] == 'not observed':
                flags[s] = 'not observed'; parts.append(f'Session {s}: read_sparse has fewer than 4 processes with a value.'); continue
            d = v['total_difference']; h = d['metrics']['M_hist']
            aa.append(h['aa_spread'])
            qs_, qo_ = [x['q'] for x in S[s]['B5']['kern'].get('read_sparse', [])], [x['q'] for x in S[s]['B5']['kern'].get('oldread', [])]
            if d['decision'] == 'resolved' and not d['metrics_disagree']:
                flags[s] = 'hold'
                parts.append(f"Session {s}: old read minus read_sparse is {fs(h['median_D'])} GB/s (median of {h['n_processes']} processes, A/A spread {f(h['aa_spread'])} GB/s), which is resolved. "
                             f"q is {rng(qs_, 3)} for read_sparse and {rng(qo_, 3)} for old read.")
            else:
                flags[s] = 'not resolved'
                parts.append(f"Session {s}: old read minus read_sparse is {fs(h['median_D'])} GB/s, which is not resolved. The rule then asks whether the pattern labels are equal, and the labels are not used.")
        if flags and all(x == 'hold' for x in flags.values()):
            parts.append('So read_sparse does not show the total of old read, and no label is needed.')
        w = word_of(flags)
        ws = hyp.get(b5key, {}).get('word', '') if b5key else ''
        add('B5 statement', meaning, text, 'B5', w, ', '.join(f"{s}: {S[s]['B5']['n']}" for s in ss), (f'{rng(aa)} GB/s' if aa else '-'), ' '.join(parts), flags,
            strict=(strict_of(b5key) if b5key else 'no entry') + ', from the label rule and the totals',
            other=('' if norm(ws) == w else 'The label rule gives another word. It is not used: user decision 2 of 2026-11-13.'),
            short=('the total of read_sparse differs from old read by a resolved amount in ' + join_and(flags) if flags and all(x == 'hold' for x in flags.values())
                   else 'result per session: ' + flag_txt(flags)))
    # ---- H9a (page rule 1)
    ss = have('B9')
    meaning, text = 'the second buffer per thread changed the pattern of old read on 2026-10-30', 'old read is uniform with two buffers per thread and split with one'
    if not ss:
        add('H9a', meaning, text, 'B9', 'not tested', '-', '-', f'{ID}: no B9 process in the input.', {}, short='no B9 process in the input')
    else:
        aa = [S[s]['B9']['res']['total']['aa_value'] for s in ss if S[s]['B9']['res']['total']['aa_value'] is not None]
        q1 = [x['q'] for s in ss for x in S[s]['B9']['kinds']['one_buffer']['ivs']]; q2 = [x['q'] for s in ss for x in S[s]['B9']['kinds']['two_buffers']['ivs']]
        ivs = [x for s in ss for kk in S[s]['B9']['kinds'].values() for x in kk['ivs']]
        parts = ['The prediction is worded with the labels split and uniform, which are not used.']
        if q1 and q2:
            parts.append(f"Without labels: q of old read is {rng(q1, 3)} with one buffer ({len(q1)} intervals) and {rng(q2, 3)} with two ({len(q2)} intervals). "
                         f"The median thread rate is {rng([x['m0'] for x in ivs])} GB/s on mesh 0 and {rng([x['m1'] for x in ivs])} GB/s on mesh 1 in all {len(ivs)} intervals of both kinds.")
        for s in ss:
            t = S[s]['B9']['res']['total']
            if t['difference'] is not None:
                parts.append(f"Session {s}: the total with one buffer minus the total with two is {fs(t['difference'])} GB/s (A/A value {f(t['aa_value'])} GB/s, {t['decision']}).")
        w9 = hyp.get('H9a (B9)', {}).get('word', '')
        add('H9a', meaning, text, 'B9', 'not resolved', ', '.join(f"{s}: {S[s]['B9']['kinds']['one_buffer']['n']} with one buffer, {S[s]['B9']['kinds']['two_buffers']['n']} with two" for s in ss),
            (f'{rng(aa)} GB/s (largest difference of the total between two processes of one kind)' if aa else '-'),
            ' '.join(parts), {s: 'not resolved' for s in ss}, plan_word='labels not used', strict=strict_of('H9a (B9)') + ', from the label rule',
            other=('' if norm(w9) == 'not resolved' else f'The label rule gives "{w9}". It is not used: user decision 2 of 2026-11-13 says that a rule which needs a label gives "not resolved". '
                   'The word of the label rule would need the labels, or a decision of the user to accept q for this step.'),
            short='the prediction is worded with the pattern labels, which are not used')
    # ---- H9b (page rule 3)
    qs = {s: S[s]['old_q'] for s in names if S[s]['old_q']}
    meaning, text = 'old read behaves differently between days or sessions for a reason other than the kernel', 'the pattern of old read differs between days or sessions for a reason other than the kernel'
    if len(qs) < 2:
        add('H9b', meaning, text, 'B7, B5, B8, B9', 'not tested', '-', '-',
            (f"One session ({', '.join(qs)}) has data. A comparison between sessions needs at least two." if qs else f'{ID}: no old read interval at 64+56 threads in the input.'), {},
            short='a comparison between sessions needs two sessions')
    else:
        lo, hi = max(min(q for q, _ in v) for v in qs.values()), min(max(q for q, _ in v) for v in qs.values())
        overlap = lo <= hi
        tmin = min(t for v in qs.values() for _, t in v)
        parts = [' '.join(f'Session {s}: q of old read is {f(min(q for q, _ in v), 3)} to {f(max(q for q, _ in v), 3)}, and its total is {rng([t for _, t in v])} GB/s ({len(v)} intervals).' for s, v in qs.items())]
        parts.append('The ranges of q overlap.' if overlap else 'The ranges of q do not overlap.')
        parts.append(f"No interval has a total at or below {fx(PLAN_OLD_LOW[1])} GB/s, the highest total of old read on 2026-10-30." if tmin > PLAN_OLD_LOW[1] else
                     f"The lowest total is {f(tmin)} GB/s. The totals of old read on 2026-10-30 were {fx(PLAN_OLD_LOW[0])} to {fx(PLAN_OLD_LOW[1])} GB/s.")
        ts = m['timing'].get('same_step')
        if ts:
            parts.append(f"Each step of {ts[1]} started {hm(ts[2])}" + ('' if hm(ts[2]) == hm(ts[3]) else f' to {hm(ts[3])}') + f" after the same step of {ts[0]}, in one continuous run.")
        add('H9b', meaning, text, 'B7, B5, B8, B9', 'not observed' if overlap else 'not resolved', ', '.join(f'{s}: {len(v)} intervals of old read' for s, v in qs.items()), '-',
            ' '.join(parts), {s: 'described' for s in qs},
            strict='no entry of the analysis script. Plan, step B9: H9b can only be "observed" or "not observed" over the sessions that were run',
            other=('H9b is worded with the pattern, and the pattern labels are not used. Under user decision 2 of 2026-11-13 the word would then be "not resolved". '
                   'The test of this page (overlapping ranges of q, page rule 3) is not a rule of the plan or of the handoff, and the user has not approved it.'),
            open_='"not observed" (page rule 3) or "not resolved" (user decision 2)' if overlap else '',
            short='the ranges of q of old read overlap between the sessions' if overlap else 'the ranges of q of old read do not overlap, and no label names the change')
    # ---- H10 (page rule 4)
    ss = have('C3')
    add('H10', 'the memory system fetches lines that the loop does not consume', 'in the uniform state the memory system fetches lines that the loop does not consume', 'C3 (description), D1 (not run)', 'not tested',
        ', '.join(f"{s}: {S[s]['C3']['n']} with counters" for s in ss) or '-', '-',
        'No step of Parts B and C tests a bounded prediction of H10. The core counters of C3 are a description. Step D1 (mesh counters, root) was not run.', {},
        strict='no entry of the analysis script', short='the counters that need root were not run')
    return rows


def compute(session_paths, offsets=OFFSETS):
    """session_paths: {name: [folders]} -> the model (computed values only)."""
    names = list(session_paths)
    procs, folders, env_all = {}, {}, {}
    for s, paths in session_paths.items():
        allp = A.load_session(s, paths)
        procs[s] = [p for p in allp if p.step in STEPS]
        used = {p.file.split('/')[0] for p in procs[s]}
        folders[s] = [x for x in paths if os.path.basename(x.rstrip('/')) in used]
        env_all[s] = [read_env(x) for x in paths]
    summary = A.analyze(procs)
    m = dict(sessions=names, summary=summary, S={}, folders=folders, offsets={}, offsets_path=offsets, timing=timing_model(env_all, names))
    for s in names:
        res, P = summary['sessions'][s], procs[s]
        by = lambda st: [p for p in P if p.step == st]
        d = dict(load=load_model(P, folders[s]), env=[read_env(x) for x in folders[s]], old_q=old_q_at_full(P), steps=[st for st in STEPS if st in res],
                 integ={st: res[st] for st in STEPS if st in res},
                 page={st: dict(rows=sum(len(p.P) for p in by(st)), na=sum(1 for p in by(st) for x in p.P if x['kB_total'] is None or x['kB_huge'] is None),
                                not_full=sum(1 for p in by(st) for x in p.P if x['kB_total'] is not None and x['kB_huge'] != x['kB_total']))
                       for st in STEPS if st in res},
                 skew={st: (max([iv.skew * 1e3 for p in by(st) if p.complete and p.stop == 'common' for iv in p.ordered], default=None),
                            max([iv.skew * 1e3 for p in by(st) if p.complete and p.stop == 'pass' for iv in p.ordered], default=None),
                            sum(iv.late for p in by(st) if p.complete for iv in p.ordered)) for st in STEPS if st in res})
        for st, fn in (('B7', b7_model), ('B10', b10_model), ('B8', b8_model), ('B5', b5_model), ('B9', b9_model), ('C3', c3_model)):
            if st in res:
                d[st] = fn(by(st), res[st])
        d['later_settings'] = {st: d[st]['settings'] for st in ('B8', 'B5', 'B9') if st in d}
        ls = {x for v in d['later_settings'].values() for x in v}
        d['used_setting'] = next(iter(ls)) if len(ls) == 1 else None          # the one setting of B8, B5 and B9, if it is one
        if 'B7' in d:
            b7_rep(d['B7'], d['used_setting'])
        m['S'][s] = d
    # one y axis for the B8 panels of all sessions, so that two sessions can be compared at a glance
    r8 = [v for s in names if 'B8' in m['S'][s] for k in m['S'][s]['B8']['kern'].values() for iv in k.values() for x in iv for v in (x['m0'], x['m1']) if v is not None]
    m['b8_ymax'] = float(max(2, 2 * __import__('math').ceil(max(r8) * 1.02 / 2))) if r8 else None
    if offsets and os.path.exists(offsets):
        for line in open(offsets):
            c = line.split()
            if len(c) == 6 and c[0] != 'binary':
                m['offsets'][(c[0], c[1])] = int(c[5])
    m['hyp'] = hypotheses(m)
    return m


# ---------------------------------------------------------------- charts

def ticks_for(lo, hi, n=6):
    span = (hi - lo) or 1.0
    raw = span / n
    mag = 10 ** __import__('math').floor(__import__('math').log10(raw))
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    t0 = __import__('math').ceil(lo / step - 1e-9) * step
    out = []
    while t0 <= hi + 1e-9:
        out.append(round(t0, 10)); t0 += step
    return out


def wrap(text, n):
    """Break a text into lines of at most n characters, at spaces."""
    out, cur = [], ''
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    return out + ([cur] if cur else [])


def dot(x, y, color, shape, title, r=4.5, op=1.0):
    t = f'<title>{e(title)}</title>' if title else ''
    if shape == 'ring':
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r - 0.75:.1f}" fill="#fff" stroke="{color}" stroke-width="1.5">{t}</circle>'
    if shape == 'diamond':
        return f'<path d="M{x:.1f},{y - r - 1:.1f} l{r + 1},{r + 1} l-{r + 1},{r + 1} l-{r + 1},-{r + 1} Z" fill="{color}" fill-opacity="{op}" stroke="#fff" stroke-width="1">{t}</path>'
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" fill-opacity="{op}" stroke="#fff" stroke-width="1">{t}</circle>'


def rowchart(rows, xmin, xmax, xlabel, aria, L=250, R=250, W=880, rh=24, note=None, vlines=(), ticks=None):
    """rows: dict(head=text) or dict(name, pts=[dict(v, c, shape, t, dy, lab, side)], right, bar=(a, b), seg=(a, b)).
    A bar is a grey band (a control). A seg joins two points of one row (a dumbbell)."""
    nl = wrap(note, int((W - 16) / 7.3)) if note else []
    top = 30 + 16 * len(nl) if nl else 26
    H = top + len(rows) * rh + 46
    PW = W - L - R
    X = lambda v: L + (min(max(v, xmin), xmax) - xmin) / ((xmax - xmin) or 1) * PW
    o = PA.svg_open(W, H, aria)
    for i, ln in enumerate(nl):
        o.append(f'<text x="8" y="{16 + 16 * i}" class="lab" font-weight="600">{e(ln)}</text>')
    for t in (ticks or ticks_for(xmin, xmax)):
        o.append(f'<line x1="{X(t):.1f}" y1="{top - 4}" x2="{X(t):.1f}" y2="{H - 46}" stroke="{GRID}"/>')
        o.append(f'<text x="{X(t):.1f}" y="{H - 30}" text-anchor="middle" class="ax">{t:g}</text>')
    for v, lab in vlines:
        o.append(f'<line x1="{X(v):.1f}" y1="{top - 4}" x2="{X(v):.1f}" y2="{H - 46}" stroke="{MUTED}" stroke-dasharray="4 3"/>')
        if lab:
            o.append(f'<text x="{X(v):.1f}" y="{top - 8}" text-anchor="middle" class="ax">{e(lab)}</text>')
    o.append(f'<text x="{L + PW / 2:.1f}" y="{H - 8}" text-anchor="middle" class="ax">{e(xlabel)}</text>')
    for i, r in enumerate(rows):
        y = top + i * rh + rh / 2
        if 'head' in r:
            o.append(f'<text x="8" y="{y + 4:.1f}" class="lab" font-weight="600" style="paint-order:stroke;stroke:#fff;stroke-width:4px">{e(r["head"])}</text>')
            continue
        o.append(f'<text x="{L - 10}" y="{y + 4:.1f}" text-anchor="end" class="lab">{e(r["name"])}</text>')
        o.append(f'<line x1="{L}" y1="{y + rh / 2:.1f}" x2="{L + PW}" y2="{y + rh / 2:.1f}" stroke="{GRID}"/>')
        if r.get('bar'):
            a, b = sorted(r['bar'])
            o.append(f'<rect x="{X(a):.1f}" y="{y - rh / 2 + 3:.1f}" width="{max(X(b) - X(a), 1):.1f}" height="{rh - 6}" fill="#d9d7cf"><title>{e(r.get("bar_t", "control"))}</title></rect>')
        if r.get('seg'):
            a, b = r['seg']
            o.append(f'<line x1="{X(a):.1f}" y1="{y:.1f}" x2="{X(b):.1f}" y2="{y:.1f}" stroke="{MUTED}" stroke-width="2"/>')
        for p in r.get('pts', []):
            px, py = X(p['v']), y + p.get('dy', 0)
            o.append(dot(px, py, p.get('c', C0), p.get('shape', 'circle'), p.get('t', ''), p.get('r', 4.5), p.get('op', 0.8)))
            if p.get('lab'):
                side = p.get('side', 'r')
                if side in ('a', 'b'):
                    o.append(f'<text x="{px:.1f}" y="{py + (-9 if side == "a" else 17):.1f}" text-anchor="middle" class="val">{e(p["lab"])}</text>')
                    continue
                o.append(f'<text x="{px + (9 if side == "r" else -9):.1f}" y="{py + 4:.1f}" text-anchor="{"start" if side == "r" else "end"}" class="val">{e(p["lab"])}</text>')
        if r.get('right'):
            o.append(f'<text x="{L + PW + 10}" y="{y + 4:.1f}" class="val">{e(r["right"])}</text>')
    o.append('</svg>')
    return '\n'.join(o)


def spread_labels(items, gap=12):
    """items: [(y, payload)] -> [(y_label, payload)] with at least gap px between labels."""
    out, last = [], None
    for y, p in sorted(items, key=lambda t: t[0]):
        y = y if last is None else max(y, last + gap)
        out.append((y, p)); last = y
    return out


def linechart(series, xs, ymin, ymax, xlabel, ylabel, aria, W=300, H=260, R=74, title=None, label_pts=()):
    """series: dict(name, c, med=[(x, y)], pts=[(x, y, title)]). Lines join the medians. Dots are the single intervals.
    label_pts: names of series whose median values are printed at the points ('above' or 'below')."""
    L, top, bot = 40, 30, 40
    PW, PH = W - L - R, H - top - bot
    X = lambda v: L + (v - xs[0]) / ((xs[-1] - xs[0]) or 1) * PW
    Y = lambda v: top + PH - (min(max(v, ymin), ymax) - ymin) / ((ymax - ymin) or 1) * PH
    o = PA.svg_open(W, H, aria)
    if title:
        o.append(f'<text x="{L}" y="14" class="lab" font-weight="600">{e(title)}</text>')
    for t in ticks_for(ymin, ymax, 5):
        o.append(f'<line x1="{L}" y1="{Y(t):.1f}" x2="{L + PW}" y2="{Y(t):.1f}" stroke="{GRID}"/>')
        o.append(f'<text x="{L - 6}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{t:g}</text>')
    for x in xs:
        o.append(f'<text x="{X(x):.1f}" y="{H - bot + 14}" text-anchor="middle" class="ax">{x:g}</text>')
    o.append(f'<text x="{L + PW / 2:.1f}" y="{H - 8}" text-anchor="middle" class="ax">{e(xlabel)}</text>')
    o.append(f'<text x="{L - 34}" y="{top - 8}" class="ax">{e(ylabel)}</text>')
    ends = []
    for s in series:
        md = [(x, y) for x, y in s['med'] if y is not None]
        if len(md) > 1:
            o.append(f'<polyline fill="none" stroke="{s["c"]}" stroke-width="2" points="' + ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in md) + '"/>')
        for x, y, t in s.get('pts', []):
            o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="2.6" fill="{s["c"]}" fill-opacity="0.55" stroke="#fff" stroke-width="0.6"><title>{e(t)}</title></circle>')
        if md:
            ends.append((Y(md[-1][1]), (s, md[-1][1])))
    # Values at the points of the series named in label_pts. At each x the higher series is labelled above its
    # point and the lower one below. The last x is left out: its value stands in the label at the line end.
    lab = [s for s in series if s['name'] in label_pts]
    for i, x in enumerate(xs[:-1]):
        here = sorted(((dict(s['med']).get(x), s) for s in lab if dict(s['med']).get(x) is not None), key=lambda t: t[0])
        for j, (y, s) in enumerate(here):
            up = j == len(here) - 1 and len(here) > 1 or (len(here) == 1)
            o.append(f'<text x="{X(x) + (3 if i == 0 else 0):.1f}" y="{Y(y) + (-7 if up else 15):.1f}" text-anchor="{"start" if i == 0 else "middle"}" class="val" style="font-size:10px">{f(y, s.get("nd", 2))}</text>')
    for y, (s, v) in spread_labels(ends, 13):
        o.append(f'<text x="{L + PW + 7}" y="{min(max(y + 4, top + 4), H - bot + 4):.1f}" class="val" style="fill:{s["c"]}">{e(s["name"])} {f(v, s.get("nd", 2))}</text>')
    o.append('</svg>')
    return '\n'.join(o)


def cpu_scatter(rep, aria):
    W, H, L, R, top, bot = 880, 350, 52, 20, 82, 44
    PW, PH = W - L - R, H - top - bot
    cmax = max(c for c, _ in rep['old'] + rep['new'])
    ymax = max(v for _, v in rep['old'] + rep['new']) * 1.08
    X = lambda c: L + c / cmax * PW
    Y = lambda v: top + PH - v / ymax * PH
    o = PA.svg_open(W, H, aria)
    for t in ticks_for(0, ymax, 6):
        o.append(f'<line x1="{L}" y1="{Y(t):.1f}" x2="{L + PW}" y2="{Y(t):.1f}" stroke="{GRID}"/><text x="{L - 6}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{t:g}</text>')
    for c in range(0, cmax + 1, 8):
        o.append(f'<text x="{X(c):.1f}" y="{H - bot + 14}" text-anchor="middle" class="ax">{c}</text>')
    has1 = any(c >= 64 for c, _ in rep['old'])
    if has1:
        xb = (X(63) + X(64)) / 2
        o.append(f'<line x1="{xb:.1f}" y1="{top - 6}" x2="{xb:.1f}" y2="{H - bot}" stroke="{MUTED}" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{L + PW / 2:.1f}" y="{H - 8}" text-anchor="middle" class="ax">CPU number of the thread</text>')
    o.append(f'<text x="8" y="{top - 12}" class="ax">thread rate (GB/s)</text>')
    for pts, col, shape in ((rep['old'], C0, 'circle'), (rep['new'], C1, 'diamond')):
        for c, v in pts:
            o.append(dot(X(c), Y(v), col, shape, f'CPU {c}: {fx(v)} GB/s', 3.2, 0.8))
    so, sn = rep['old_s'], rep['new_s']
    xa, xc = X(4), L + PW
    o.append(f'<text x="{xa:.1f}" y="16" class="lab" font-weight="600">mesh 0 (CPUs 0 to 63)</text>')
    o.append(f'<text x="{xa:.1f}" y="32" class="val" style="fill:{C0}">old read, median thread {f(so["m0"])} GB/s</text>')
    o.append(f'<text x="{xa:.1f}" y="47" class="val" style="fill:{C1}">new read, median thread {f(sn["m0"])} GB/s</text>')
    if has1:
        o.append(f'<text x="{xc:.1f}" y="16" text-anchor="end" class="lab" font-weight="600">mesh 1 (CPUs 64 to {cmax})</text>')
        o.append(f'<text x="{xc:.1f}" y="32" text-anchor="end" class="val" style="fill:{C0}">old read, median thread {f(so["m1"])} GB/s</text>')
        o.append(f'<text x="{xc:.1f}" y="47" text-anchor="end" class="val" style="fill:{C1}">new read, median thread {f(sn["m1"])} GB/s</text>')
    o.append('</svg>')
    return '\n'.join(o)


def legend(items):
    return '<p>' + ''.join(f'<span class="lg"><i style="background:{c};{st}"></i>{e(t)}</span>' for c, t, st in items) + '</p>'


def table(head, rows, cls=''):
    o = [f'<div class="tw"><table{" class=" + chr(34) + cls + chr(34) if cls else ""}><tr>' + ''.join(f'<th>{h}</th>' for h in head) + '</tr>']
    o += ['<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows]
    o.append('</table></div>')
    return '\n'.join(o)


def NW(t):
    return f'<span style="white-space:nowrap">{t}</span>'


def missing(what):
    return f'<p class="miss"><b>{ID}.</b> {what}</p>'


# ---------------------------------------------------------------- references

class Refs:
    """References are defined first and get their number at the first citation. Only cited ones are listed."""

    def __init__(self):
        self.text, self.items, self.idx = {}, [], {}

    def add(self, key, text):
        self.text.setdefault(key, text)
        return self

    def __call__(self, *keys):
        out = ''
        for k in keys:
            if k not in self.text:
                continue
            if k not in self.idx:
                self.items.append(self.text[k]); self.idx[k] = len(self.items)
            out += f'[Ref{self.idx[k]}]'
        return out


def make_refs(m):
    R = Refs()
    N = os.path.join(CRB, 'new-test-kernel')
    two = len(m['sessions']) > 1
    R.add('plan', f'<code>{N}/plan.md</code>: the two questions, the hypotheses H1 to H11, the rules 1 to 11 for the deciding measurements, and the tables of the steps B7, B8, B5, B9, B10, C3 and D1.')
    R.add('handoff', f'<code>{N}/handoff.md</code>: sections B.3 (output rows), B.4 (stop methods, irregular interval), B.6 (page state), B.8 (counters), B.9 (sequences, "Settings after B7") and B.10 (numeric decision procedure, the two metrics, the pattern rule).')
    R.add('analyze', f'<code>{BWX_DIR}/analyze_bwx.py</code> and <code>{N}/decide.py</code>: the parser and the decision rules that this page uses.')
    R.add('devs', f'<code>{BWX_DIR}/DEVIATIONS-scripts.md</code>: the choices of the run script and of the analysis (S1 to S20, A1 to A33). A19 says that the mapping of a step result to a word is the reading of the authors of the analysis.')
    R.add('devb', f'<code>{BWX_DIR}/DEVIATIONS-bwx.md</code>: the deviations of <code>bwx</code> from the specification, and its known limits (main thread without a CPU of its own, loop offset of <code>read_sparse</code>).')
    R.add('partA', f'<code>{CRB}/results/partA-20261113T205055Z/partA-result.html</code>: the result page of Part A (screening). It shows that q did not fall into two groups.')
    R.add('offsets', f'<code>{m["offsets_path"]}</code>: the start address of every loop of the four <code>bwx</code> binaries, and <code>build.txt</code> in the same folder (compiler options).')
    R.add('short', f'<code>{CRB}/results/SHORT-20261113T214338Z/</code>: the short run of every sequence before session 1.')
    R.add('antxt', (f'<code>{CRB}/results/partBC-20261114/analysis/</code>: the text tables, <code>hypotheses.txt</code> and <code>summary.json</code> that <code>analyze_bwx.py</code> wrote for both sessions (all steps of Parts B and C).' if two else
                    f'<code>{CRB}/results/partB-s1-analysis/</code>: the text tables, <code>hypotheses.txt</code> and <code>summary.json</code> that <code>analyze_bwx.py</code> wrote for session 1 (all steps of Parts B and C).'))
    R.add('decisions', f'<code>{N}/decisions.md</code>: the decisions of the user during the execution (2026-11-13), and the open decision on the level limits at 8 MiB.')
    R.add('session2', f'<code>{N}/session2.sh</code>: the run script of session 2. Its line 2 says that it repeats the visits of session 1 with the same settings, and its line 6 sets the common stop, the common start and 6 s.')
    R.add('q1page', f'<code>{CRB}/results/partBC-20261114/partB-q1-result.html</code>: the result page of question Q1 (the steps with one thread).')
    R.add('gen', f'<code>{HERE}/make_q2_html.py</code> and <code>test_q2.py</code>: the generator of this page with its page rules 1 to 4, and its test.')
    for s in m['sessions']:
        for st in STEPS:
            fo = [x for x in m['folders'][s] if os.path.basename(x.rstrip('/')).split('-')[0].rstrip('ab') == st]
            if fo:
                R.add((s, st), f"Session {e(s)}, step {st}: " + ', '.join(f'<code>{e(os.path.abspath(x))}/</code>' for x in fo)
                      + f" (<code>{st}.csv</code> with the header line of every launch and the rows I, T, P" + (', C' if st == 'C3' else '') + ', and <code>env.txt</code>, <code>launches.txt</code>, <code>stderr.txt</code>).')
    return R


def tidy_refs(h):
    """Rule of the user: a reference index stands at the end of the sentence that carries the claim, before its full stop.
    'claim. [Ref3]' becomes 'claim [Ref3].', and 'claim [Ref2]. [Ref3]' becomes 'claim [Ref2][Ref3].'. A reference is never repeated in one group."""
    def uniq(t):
        seen = []
        for x in re.findall(r'\[Ref\d+\]', t):
            if x not in seen:
                seen.append(x)
        return ''.join(seen)
    h = re.sub(r'\s*((?:\[Ref\d+\])*)\.(</code>)?\s+((?:\[Ref\d+\])+)(?=\s*</(?:p|li|div)>|\s+[A-Z("<])', lambda mm: (mm.group(2) or '') + ' ' + uniq(mm.group(1) + mm.group(3)) + '.', h)
    return re.sub(r'(?:\[Ref\d+\]){2,}', lambda mm: uniq(mm.group(0)), h)


# ---------------------------------------------------------------- sections

def per_session(m, step, fn, what):
    """One block per session. A session without the step gets 'Insufficient data'."""
    o = []
    for s in m['sessions']:
        if len(m['sessions']) > 1:
            o.append(f'<h3>Session {e(s)}</h3>')
        if step not in m['S'][s]:
            o.append(missing(f'Session {e(s)} has no process of step {step}. {what}'))
        else:
            o.append(fn(m, s, m['S'][s][step]))
    return '\n'.join(o)


def details(summary, body):
    return f'<details><summary>{summary}</summary>{body}</details>'


def hyp_bullets(m):
    """One line per hypothesis, directly under the Short version."""
    o = ['<ul>']
    for h in m['hyp']:
        w = f'"{h["word"]}"' + (f' ({h["plan_word"]})' if h['plan_word'] else '')
        o.append(f'<li><b>{e(h["label"])}</b> ({e(h["meaning"])}): <b>{e(w)}</b>' + (', open for the user' if h['open'] else '') + (f'. {e(h["short"][0].upper() + h["short"][1:])}.' if h['short'] else '.') + '</li>')
    o.append('</ul>')
    return '\n'.join(o)


def sec_hyp(m, R):
    one = len(m['sessions']) < 2
    o = ['<h2 id="hyp">Result per hypothesis</h2>']
    if one:
        o.append(f'<p class="take">This page is built from one session ({e(m["sessions"][0])}). Rule 11 of the plan gives "rejected" only when the bounded prediction failed in two sessions {R("plan")}. '
                 'So no row of this table can say "rejected". A row that says "not rejected" with the note "prediction failed in this session" becomes "rejected" if the second session shows the same.</p>')
    else:
        o.append(f'<p>The page is built from {len(m["sessions"])} sessions ({", ".join(map(e, m["sessions"]))}). "rejected" needs a failed prediction in every session {R("plan", "analyze")}.</p>')
    o.append(f'<p>The third column quotes the output of the analysis script as it stands in <code>hypotheses.txt</code> {R("antxt")}. Where the word of this page differs from it, or where two readings of a rule exist, the last column gives the other reading and its reason. '
             'An item marked "open for the user" is a judgment that this page does not make.</p>')
    rows, rec = [], []
    for h in m['hyp']:
        w = f'<b>{h["word"]}</b>' + (f' ({h["plan_word"]})' if h['plan_word'] else '')
        if h['one_session']:
            w += '<br>prediction failed in this session'
        if h['open']:
            w += '<br><b>open for the user</b>'
        other = e(h['other']) + (f' <b>Open for the user:</b> {e(h["open"])}.' if h['open'] else '')
        rows.append((f'<b>{e(h["label"])}</b><br>{e(h["meaning"])}', w, e(h['strict']), e(h['basis']), other or '-'))
        rec.append((e(h['label']), e(h['text']), h['step'], e(str(h['n'])), e(str(h['aa'])), e(flag_txt(h['flags']))))
    o.append(table(['Hypothesis, in plain words', 'Word of this page', 'Output of the analysis rule as it stands', 'Basis and caveat (computed)', 'Other reading and its reason'], rows, 'pt hy'))
    o.append(table(['Hypothesis', 'Bounded prediction that the step tests', 'Step', 'Processes', 'A/A spread or control', 'Result per session'], rec, 'pt hr'))
    o.append(f'<p class="cap">Result per session: "fail" means the prediction failed in that session, and "hold" means it held. "supported" and "contradicted" are the words of the plan for one cell of H11 in one session. '
             f'The words of H7a, H7b and of the cells of H11 come from the analysis script {R("analyze")}. That script maps each step result to a word, and its authors call the mapping their own reading {R("devs")}. '
             f'The words of H8, H9a, H9b, H10, the B5 statement and the merged word of H11 follow the page rules 1 to 4 {R("gen")}.</p>')
    o.append('<h3>Page rules (rules of this page, not of the plan)</h3><ul>'
             f'<li><b>Page rule 1.</b> The labels split and uniform are not used. This is decision 2 of the user of 2026-11-13: "Where a rule needs a label that the data do not give, the word is not resolved. No rule is adapted" {R("decisions")}. The reason is that q did not fall into two groups in Part A {R("partA")}. The page reports q and the median thread rate of each mesh in place of a label.</li>'
             '<li><b>Page rule 2.</b> The analysis gives H11 one result per cell (one kernel in one setting) and session. Over the sessions a cell is "not rejected (supported)" only if it is supported in every session. It is "rejected (contradicted)" only if it is contradicted in every session. It is "not observed" if it is not observed in every session. In every other case it is "not resolved". So a cell that is supported in one session only counts as "not resolved". '
             'The word of the table is "not observed" if every cell is "not observed". It is "rejected" if every cell with another word is "rejected". It is "not rejected" if at least one cell is "not rejected" and none is "rejected". Otherwise it is "not resolved".</li>'
             f'<li><b>Page rule 3.</b> H9b needs at least two sessions. The plan allows the words "observed" and "not observed" for it {R("plan")}. With two or more sessions this page writes "not observed" if the ranges of q of old read at 64+56 threads overlap between the sessions, and "not resolved" otherwise. The user has not approved this rule. It is marked "open for the user" in the table.</li>'
             f'<li><b>Page rule 4.</b> H10 is "not tested". The plan gives the counters of C3 no decision, and step D1 was not run {R("plan")}.</li></ul>')
    return '\n'.join(o)


ONE_THREAD_STEPS = {'B1', 'B2', 'B3', 'B4', 'B6', 'C1', 'C2'}


def sec_facts(m, R):
    o = ['<h2 id="facts">Decisions, deviations and settings of the runs</h2>']
    o.append(f'<p><b>Decision of the user (2026-11-13).</b> The labels split and uniform of the handoff are not used (page rule 1) {R("decisions", "partA", "handoff")}.</p>')
    o.append('<p class="miss"><b>Open decision (not made): level limits at 8 MiB.</b> The plan labels an interval with one thread at 8 MiB by the rate of asm read: low below 69 GB/s, high above 70.5 GB/s. '
             + ('These provisional limits do not fit the data of both sessions. ' if len(m['sessions']) > 1 else 'These provisional limits do not fit the data of this session. ')
             + f'The rate of asm read forms different groups per CPU and per step. The Q1 page gives the evidence {R("q1page", "antxt")}. The limits were not changed. The user decides on new limits {R("decisions")}. No result on this page uses these limits.</p>')
    sets, b8s, c3s = [], {}, {}
    for s in m['sessions']:
        d = m['S'][s]
        if 'B7' in d:
            ch = d['B7']['chosen']; res = d['B7']['res']
            if not ch:
                sets.append(f'<li>Session {e(s)}: D is resolved in no setting of B7 with the common stop. So the handoff gives no setting for B8, B5, B9 and C3 {R("handoff")}.</li>')
            else:
                md = res['settings'][ch]['metrics']['M_hist']['median_D']
                used = d['later_settings']; u = d['used_setting']
                if not used:
                    sets.append(f'<li>Session {e(s)}: the handoff rule selects "{sname(ch)}" (median D {fx(md)} GB/s) {R("handoff")}. No process of B8, B5 or B9 is in the input.</li>')
                elif u == ch:
                    sets.append(f'<li>Session {e(s)}: the handoff rule selects "{sname(ch)}" (median D {fx(md)} GB/s) {R("handoff")}. The header lines of {join_and(used)} show this setting for every process {R((s, "B7"))}.</li>')
                else:
                    t = f'<li><b>Deviation, session {e(s)}.</b> The handoff rule selects "{sname(ch)}" (median D {fx(md)} GB/s) {R("handoff")}. '
                    t += 'The header lines show another setting: ' + ', '.join(f"{st} ran with \"{' and '.join(sname(x) for x in v)}\"" for st, v in used.items()) + f' {R((s, "B8"))}. '
                    if u and u in res['settings']:
                        vu = res['settings'][u]
                        t += f"In B7 of this session D in that setting is {vu['decision']}, with a median of {fx(vu['metrics']['M_hist']['median_D'])} GB/s. "
                        c = next((c for c in res['changes'].values() if {c['first'], c['second']} == {u, ch}), None)
                        if c and c['metrics']['M_hist']['change'] is not None:
                            t += f"The change of D between the two settings is {fx(abs(c['metrics']['M_hist']['change']))} GB/s, with a limit of {fx(c['metrics']['M_hist']['sum_of_aa_spreads'])} GB/s ({c['decision']}). "
                    first = m['sessions'][0]
                    if s != first and 'B7' in m['S'][first] and u == m['S'][first]['B7']['chosen']:
                        t += f'It is the setting that the rule selects in session {e(first)}. The run script of session 2 repeats the settings of session 1, so the two sessions ran the same settings {R("session2")}. '
                    t += 'The user did not decide this.</li>'
                    sets.append(t)
        if 'B8' in d:
            b = d['B8']
            b8s.setdefault((tuple(b['mesh0']), tuple(b['counts'])), []).append(s)
        if 'C3' in d:
            seqs = sorted({g['group'] for g in d['C3']['res'].get('groups', [])})
            c3s.setdefault((sum(1 for x in seqs if x.endswith('B7 sequence')), tuple(x.split(' ')[0] for x in seqs if x.endswith('B5 sequence'))), []).append(s)
    who = lambda ss: ('Both sessions' if len(ss) == 2 and len(m['sessions']) == 2 else 'Session ' + join_and(map(e, ss)))
    o.append('<ul>' + ''.join(sets))
    for (m0, counts), ss in b8s.items():
        o.append(f'<li>{who(ss)}: B8 ran {" and ".join(str(a) for a in m0)} threads on mesh 0 with these counts of mesh-1 threads: {", ".join(map(str, counts))} {R(*[(s, "B8") for s in ss])}. '
                 f'Part A gave no pair of counts between which the pattern changes {R("partA")}.</li>')
    for (nb7, b5s), ss in c3s.items():
        o.append(f'<li>{who(ss)}: C3 ran the B7 sequence with counters in {pl(nb7, "setting", "settings")}' + (f', and the B5 sequence in the setting "{", ".join(sname(x) for x in b5s)}"' if b5s else '') + f' {R(*[(s, "C3") for s in ss])}.</li>')
    o.append('<li>The same sessions also ran the steps with one thread of question Q1 (B1 to B4, B6, C1, C2). Q1 asks why one thread with an 8 MiB buffer behaves differently from the other sizes. Those steps are on the Q1 page and not here ' + R('q1page') + '. Two more points of Q1 also matter for this page:'
             '<ul><li>B2, B3 and C2 were run although B1 at 8 MiB is not formally resolved. This is a deviation from the plan. Its purpose is that data exist if the limits are revised ' + R('plan') + '.</li>'
             f'<li>The binary <code>bwx_o52</code> (the build of <code>bwx</code> with both copy loops at offset 52) is built with the compiler option <code>-falign-loops=1</code>. Without it the compiler moved the C copy loop from offset 52 to offset 0 modulo 64 {R("offsets")}.</li></ul></li>')
    o.append('</ul>')
    o.append(sec_sessions(m, R))
    return '\n'.join(o)


def sec_sessions(m, R):
    """When the sessions ran, from env.txt. Rule 10 of the plan asks for two sessions some hours apart."""
    T = m['timing']
    if not T['sessions']:
        return missing('No <code>env.txt</code> with a start time was found, so the times of the sessions are not known.')
    t = '<p id="when"><b>When the sessions ran.</b> ' + ' '.join(
        f"Session {e(s)} ran from {clock(v['t0'])} to {clock(v['t1']) if v['t1'] else '-'} UTC (start on {time.strftime('%Y-%m-%d', time.gmtime(v['t0']))})." for s, v in T['sessions'].items())
    for a, b, g in T['gaps']:
        t += f' Session {e(b)} started {hm(g)} after session {e(a)} ended.'
    ts = T['same_step']
    if ts:
        t += f' So each step of session {e(ts[1])} started {hm(ts[2])}' + ('' if hm(ts[2]) == hm(ts[3]) else f' to {hm(ts[3])}') + f' after the same step of session {e(ts[0])}.'
        if T['same_boot'] is True:
            t += f' The uptime readings of all {T["boot_n"]} result folders give one boot time, so the machine was not restarted between the sessions.'
        elif T['same_boot'] is None:
            t += f' {ID}: whether the machine was restarted between the sessions. An uptime reading in every <code>env.txt</code> would give it.'
        short = [g for _, _, g in T['gaps'] if g < 3600]
        t += (f' Rule 10 of the plan asks for two sessions some hours apart {R("plan")}. The handoff reads this as: every deciding step is run twice with some hours between its two runs {R("handoff")}. '
              + ('That reading is met. The two sessions are still one continuous run of one night, and not two separate visits.' if short else 'That reading is met.'))
    return t + '</p>'


def sec_load(m, R):
    o = ['<h2 id="load">System load of every step</h2>']
    tot = dict(n=0, wait=0, lmax=0.0, thr=0)
    rmin, rmax, lgmax, nlog = [], [], [], 0
    rows, events = [], []
    for s in m['sessions']:
        for st, L in m['S'][s]['load'].items():
            tot['n'] += L['n']; tot['wait'] += L['n_waited']; tot['lmax'] = max(tot['lmax'], L['load_max'] or 0); tot['thr'] = max(tot['thr'], L['threads_max'])
            rmin += [L['runnable_min']] if L['runnable_min'] is not None else []; rmax += [L['runnable_all_max']] if L['runnable_all_max'] is not None else []
            lgmax += [L['logins_all_max']] if L['logins_all_max'] is not None else []; nlog += L['n_log_readings']
            events += [dict(x, session=s) for x in L['other_events']]
            bo = ', '.join(f'{e(c)} of {e(u)} {fx(v, 1)} %' for v, u, c in L['busy_other'][:1]) or '-'
            bm = ', '.join(f'{e(c)} of {e(u)} {fx(v, 1)} %' for v, u, c in L['busy_own']) or '-'
            rows.append((e(s), st, L['n'], NW(f'{L["utc"][0]} to {L["utc"][1]}'), NW(f'{f(L["load_min"])} to {f(L["load_max"])}'), f"{L['runnable_max']} / {'-' if L['runnable_txt_max'] is None else L['runnable_txt_max']}",
                         f"{L['n_waited']} / {L['wait_max']:g}" if L['wait_max'] is not None else '-', L['logins_max'], bm, bo, R((s, st))))
    if not rows:
        return '\n'.join(o) + missing('No header line of a launch was found. The header lines of the csv files give the load.')
    o.append(f'<p class="take">The 1-minute load average at a launch went up to {fx(tot["lmax"])} tasks. Our own benchmark process with up to {tot["thr"]} threads ended directly before such a launch. '
             'The load average covers about the last minute, so it still counts those threads. So the load average alone does not show whether another user ran something. The readings below do.</p>')
    run_t = (f'{min(rmin)} at each' if min(rmin) == max(rmax) else f'{min(rmin)} or {max(rmax)} at each' if max(rmax) - min(rmin) == 1 else f'{min(rmin)} to {max(rmax)} at each') if rmin and rmax else '-'
    o.append('<p>The run script took these readings directly before each launch:</p><ul>'
             f'<li>Runnable tasks: {run_t} of the {tot["n"]} launches, in the header line and in <code>launches.txt</code>. One of them is the script that reads the value.'
             + (' A second one, where present, is not identified by the reading.' if rmax and max(rmax) > 1 else '') + '</li>'
             f'<li>Waits: {tot["wait"]} of {tot["n"]} launches had to wait for an idle system (<code>waited_s</code> above 0).</li>'
             + (f'<li>Logged-in users: 0 at each of the {tot["n"]} launches ({nlog} readings).</li>' if lgmax and max(lgmax) == 0 else f'<li>Logged-in users: up to {max(lgmax) if lgmax else "-"} at a launch.</li>')
             + f'<li>Busiest processes: <code>ps</code> listed a process of another account above {BUSY_LIMIT:g} % of one CPU at {pl(len(events), "launch", "launches")} of {tot["n"]}.</li></ul>')
    for x in events:
        k = sum(1 for y in events if (y['session'], y['step'], y['comm']) == (x['session'], x['step'], x['comm']))
        t = (f"<p class=\"miss\"><b>Another account, session {e(x['session'])}, step {x['step']}.</b> At the launch <code>{e(x['tag'])}</code> ({e(x['utc'])} UTC), <code>ps</code> listed the process <code>{e(x['comm'])}</code> of the account {e(x['user'])} at {fx(x['pc'], 1)} % of one CPU. "
             f"It was listed above {BUSY_LIMIT:g} % at {k} of {x['n_launches']} launches of that step. The load average at that launch was {fx(x['load'])} tasks, with {pl(x['runnable'], 'runnable task', 'runnable tasks')}. "
             '<code>ps</code> divides the CPU time of a process by the time since its start, so a process that has just started can show a high value. ')
        if x['comm'].startswith('check-new-relea'):
            t += 'The name is cut to 15 characters by <code>ps</code>. The program is <code>check-new-release</code>, the check of the operating system for a new release. '
        c3 = m['S'][x['session']].get('C3')
        if x['step'] == 'C3':
            t += 'Step C3 gives a description and no decision. '
            if c3 and c3.get('lowest') and c3['lowest']['tag'] == x['tag']:
                lw = c3['lowest']
                t += (f"In the same process a thread has the lowest CPU share of the session: {fx(lw['share'] * 100, 2)} % on CPU {lw['cpu']} (section C3). "
                      'Hypothesis, not tested: this process took CPU time from that thread. A record of the CPU on which it ran would confirm or reject it. ')
        o.append(t + f"{R((x['session'], x['step']))}</p>")
    o.append(details('Load readings per session and step', table(
        ['Session', 'Step', 'Launches', 'UTC first to last', '1-minute load (tasks), lowest to highest', 'Runnable tasks, highest: header line / launches.txt',
         'Launches that waited / longest wait (s)', 'Logged-in users, highest', 'Busiest processes of our account (% of one CPU)', 'Busiest process of another account (% of one CPU)', 'Source'], rows, 'sm')
        + '<p class="cap">The process <code>ps</code> of our account is the reading itself: the script starts <code>ps</code> to write this list. A process name is cut to 15 characters by <code>ps</code>.</p>'))
    # visits
    env, cat = [], dict(pause=[], one=[], many=[])
    for s in m['sessions']:
        for x in m['S'][s]['env']:
            if x['present'] and 'start_utc' in x:
                v = m['timing']['visits'].get((s, x['folder']), {})
                g = v.get('gap')
                env.append((e(s), f'<code>{e(x["folder"])}</code>', e(x.get('steps', '-')), NW(e(x['start_utc'])), fx(x['start_load']), x['start_runnable'], ('-' if g is None else f'{g:g}'), e(v.get('prev_steps') or '-'),
                            NW(e(x.get('end_utc', '-'))), f(x.get('end_load'))))
                name = f"{folder_step(x['folder'])} of {s}"
                if g is None or g > 60:
                    cat['pause'].append((name, x['start_load'], g))
                elif set((v.get('prev_steps') or '').split()) <= ONE_THREAD_STEPS:
                    cat['one'].append((name, x['start_load'], g, v.get('prev_steps')))
                else:
                    cat['many'].append((name, x['start_load'], g))
            else:
                env.append((e(s), f'<code>{e(x["folder"])}</code>', '-', f'{ID}: env.txt is missing', '-', '-', '-', '-', '-', '-'))
    t = '<p>Each result folder starts with one reading in <code>env.txt</code>, taken before its first launch. '
    if cat['pause']:
        t += f"After a pause (no folder before it, or more than 60 s): {join_and(e(n) for n, _, _ in cat['pause'])}, with a start load of {rng([v for _, v, _ in cat['pause']])} tasks. "
    if cat['one']:
        t += (f"Directly after steps of question Q1 with one thread: {join_and(e(n) for n, _, _, _ in cat['one'])}, with a start load of {rng([v for _, v, _, _ in cat['one']])} tasks. "
              'That load is our own one-thread process. ')
    if cat['many']:
        t += (f"The other {pl(len(cat['many']), 'folder', 'folders')} started {rng([g for _, _, g in cat['many']], 0)} s after the end of a step with many threads, with a start load of {rng([v for _, v, _ in cat['many']])} tasks. "
              'That load still counts our own threads. ')
    o.append(t + '</p>')
    o.append(details('Readings at the start and the end of every result folder', table(
        ['Session', 'Folder', 'Steps of the visit (one login)', 'Start (UTC)', '1-minute load at the start (tasks)', 'Runnable tasks at the start', 'Seconds since the end of the folder before', 'Steps of the visit before',
         'End (UTC)', '1-minute load at the end (tasks)'], env, 'sm')))
    o.append(f'<p class="miss"><b>{ID}.</b> The load while an interval ran. The script reads the load only before a launch. A reading of the runnable tasks of each account during an interval would give it.</p>')
    return '\n'.join(o)


def sec_integrity(m, R):
    o = ['<h2 id="used">Processes used, irregular intervals and page state</h2>']
    rows, irr, left = [], [], []
    for s in m['sessions']:
        d = m['S'][s]
        for st in d['steps']:
            g, pg, sk = d['integ'][st], d['page'][st], d['skew'][st]
            rows.append((e(s), st, g['n_processes'], g['n_used'], len(g['irregular_intervals']), sk[2], f(sk[0], 3), f(sk[1], 1), pg['rows'], pg['na'], pg['not_full'], R((s, st))))
            irr += [(e(s), st, e(x['tag']), x['round'], x['pos'], e(KN.get(x['entry'], x['entry'])), x['late_threads'], f(x['end_skew_ms'], 3)) for x in g['irregular_intervals']]
            left += [(e(s), st, e(x['tag']), e(x['reason'].replace(';', ','))) for x in g['left_out']]
    if not rows:
        return '\n'.join(o) + missing('No process of the steps B7, B10, B8, B5, B9 or C3 is in the input.')
    sk0 = [float(r[6]) for r in rows if r[6] != '-']; sk1 = [float(r[7]) for r in rows if r[7] != '-']
    o.append(f'<p>{sum(r[3] for r in rows)} of {sum(r[2] for r in rows)} processes of these steps were used. {pl(len(irr), "interval is", "intervals are")} irregular, and {pl(sum(r[5] for r in rows), "thread start is", "thread starts are")} late. '
             + (f'The largest end skew with the common stop is {fx(max(sk0), 3)} ms (limit 5 ms). ' if sk0 else '') + (f'With whole passes it is {fx(max(sk1), 1)} ms, which is not a reason to leave an interval out {R("devs")}. ' if sk1 else '')
             + f'{sum(r[8] for r in rows)} page-state rows (P rows) were read: {sum(r[9] for r in rows)} without a value, and {sum(r[10] for r in rows)} with less than full coverage by 2 MiB pages.</p>')
    o.append(f'<p>An interval is irregular if a thread started late or if the end skew with the common stop is above 5 ms {R("handoff")}. An irregular interval is not used, and its process then gives no value for the quantity that needs it. '
             f'In a process with more than one thread, the page-state reading that belongs to an interval is the reading taken after the interval before it. The warm-up pass lies between that reading and the timed part {R("handoff")}.</p>')
    o.append('<h3>Irregular intervals</h3>' + (table(['Session', 'Step', 'Process', 'Round', 'Position', 'Kernel', 'Late threads', 'End skew (ms)'], irr) if irr else f'<p>No interval of these steps is irregular ({sum(r[2] for r in rows)} processes).</p>'))
    if left:
        o.append('<h3>Processes left out</h3>' + table(['Session', 'Step', 'Process', 'Reason'], left, 'pt'))
    o.append(details('Counts per session and step', table(
        ['Session', 'Step', 'Processes in the files', 'Processes used', 'Irregular intervals', 'Late thread starts', 'Largest end skew with the common stop (ms)', 'Largest end skew with whole passes (ms)',
         'P rows', 'P rows without a value', 'P rows with less than full coverage', 'Source'], rows, 'sm')))
    return '\n'.join(o)


def b7_block(R):
    def fn(m, s, b):
        res = b['res']; S = sorted(res['settings'], key=skey); ref = R((s, 'B7'))
        o = []
        allD = [x for v in res['settings'].values() for mm in ('M_hist', 'M_sum') for x in v['metrics'][mm]['D']]
        sk = res['single_kernel']
        if sk.get('D') is not None:
            allD += [sk['D'], sk['metrics']['M_sum']['D']]
        if not allD:
            return missing('No setting of B7 has a process with a value of D.')
        lo, hi = min(allD + [0.0]), max(allD + [0.0])
        pad = (hi - lo) * 0.06
        rows = []
        for st in S:
            v = res['settings'][st]; h, ms = v['metrics']['M_hist'], v['metrics']['M_sum']
            pts = [dict(v=x, c=C0, t=f'M_hist: D = {fx(x)} GB/s', dy=-4) for x in h['D']] + [dict(v=x, c=C0, shape='ring', t=f'M_sum: D = {fx(x)} GB/s', dy=5) for x in ms['D']]
            right = f"D {f(h['median_D'], 1)}, A/A {f(h['aa_spread'], 1)} GB/s: {v['decision']}{A.sign_txt(v['sign'])}" if h['median_D'] is not None else v['decision']
            rows.append(dict(name=sname(st) + (' *' if st == REPRO else ''), pts=pts, right=right, bar=(0, h['aa_spread']) if h['aa_spread'] else None, bar_t='A/A spread'))
        if sk.get('D') is not None:
            rows.append(dict(name='* with one kernel per process', pts=[dict(v=sk['D'], c=C0, shape='diamond', t=f"M_hist: D = {fx(sk['D'])} GB/s", dy=-4),
                                                                      dict(v=sk['metrics']['M_sum']['D'], c=C0, shape='ring', t='M_sum', dy=5)],
                             right=f"D {f(sk['D'], 1)}, A/A {f(sk['aa_value'], 1)} GB/s: {sk['decision']}{A.sign_txt(sk.get('sign'))}", bar=(0, sk['aa_value']), bar_t='A/A value'))
        nres = sum(1 for st in S if res['settings'][st]['decision'] == 'resolved' and res['settings'][st]['sign'] == 1)
        meds = [res['settings'][st]['metrics']['M_hist']['median_D'] for st in S if res['settings'][st]['metrics']['M_hist']['median_D'] is not None]
        aas = [res['settings'][st]['metrics']['M_hist']['aa_spread'] for st in S if res['settings'][st]['metrics']['M_hist']['aa_spread'] is not None]
        ratio = [md / aa for md, aa in zip(meds, aas) if aa]
        note = f'D is resolved with old read above new read in {nres} of {len(S)} settings.' + (f' Median D is {fx(min(ratio), 0)} to {fx(max(ratio), 0)} times the A/A spread.' if ratio and min(ratio) > 0 else '')
        o.append(rowchart(rows, lo - pad if lo < 0 else 0, hi + pad, 'D = total of old read minus total of new read (GB/s)', f'B7 session {s}: D per process and setting', note=note))
        o.append(legend([(C0, 'D of one process with M_hist (decision metric)', ''), ('#fff', 'D of one process with M_sum', f'border:1.5px solid {C0}'), ('#d9d7cf', 'A/A spread, drawn from 0', 'border-radius:0')]))
        o.append(f'<p class="cap">One row per setting. * marks the reproduction condition, the timing method of the run of 2026-11-13. The last row runs one kernel per process. Its marker is the difference of two medians, not a process. '
                 f'Median D is {rng(meds)} GB/s over the settings, and the A/A spread is {rng(aas)} GB/s. Data: {ref}.</p>')
        trs, trs2 = [], []
        for st in S:
            v = res['settings'][st]; h, ms = v['metrics']['M_hist'], v['metrics']['M_sum']
            f2 = b['fail2'].get(st)
            trs.append((sname(st) + (' *' if st == REPRO else ''), f"{v['decision']}{A.sign_txt(v['sign'])}", f(h['median_D']), f(h['aa_spread']), h['n_processes'], ', '.join(fx(x, 1) for x in h['D']),
                        ('does not apply' if f2 is None else f'{f2[0]} of {f2[1]}')))
            trs2.append((sname(st) + (' *' if st == REPRO else ''), f(ms['median_D']), f(ms['aa_spread'])))
        if sk.get('D') is not None:
            n = sk['n_processes']; f2 = b.get('fail2_single')
            trs.append(('* with one kernel per process', f"{sk['decision']}{A.sign_txt(sk.get('sign'))}", f(sk['D']), f(sk['aa_value']), '/'.join(str(x) for x in n.values()),
                        'old read ' + ', '.join(fx(x, 1) for x in sk['process_values']['oldread']) + '<br>new read ' + ', '.join(fx(x, 1) for x in sk['process_values']['read']),
                        ('-' if not f2 else f'{f2[0]} of {f2[1]}')))
            trs2.append(('* with one kernel per process', f(sk['metrics']['M_sum']['D']), f(sk['metrics']['M_sum']['aa_value'])))
        o.append(table(['Setting', 'Decision', 'Median D, M_hist (GB/s)', 'A/A spread, M_hist (GB/s)', 'Processes with a value', 'D of each process, M_hist (GB/s)', 'Intervals that fail the 2 % check'], trs, 'wr'))
        o.append(details('The same with M_sum', table(['Setting', 'Median D, M_sum (GB/s)', 'A/A spread, M_sum (GB/s)'], trs2)))
        # reproduction
        rp = res['settings'].get(REPRO)
        t = '<p><b>Reproduction condition.</b> '
        if rp:
            h = rp['metrics']['M_hist']
            t += f"With the kernels alternating in one process: D is {rp['decision']}{A.sign_txt(rp['sign'])}, median {f(h['median_D'])} GB/s over {h['n_processes']} processes, A/A spread {f(h['aa_spread'])} GB/s. "
        else:
            t += f'{ID}: no process ran the setting "{sname(REPRO)}" with all kernels. '
        if sk.get('D') is not None:
            t += f"With one kernel per process: D is {sk['decision']}{A.sign_txt(sk.get('sign'))}, {f(sk['D'])} GB/s, A/A value {f(sk['aa_value'])} GB/s. "
        else:
            t += f"With one kernel per process: {e(sk.get('note', 'no value'))}. "
        t += ('So the difference of 2026-11-13 is reproduced in the changed benchmark' if res.get('reproduced_in_either_way') else
              'So Q2a is not reproduced in the changed benchmark, and the plan assigns no cause in that case') + f' {ref}{R("plan")}.</p>'
        o.append(t)
        # change per factor
        ch = sorted(res['changes'].values(), key=lambda c: (('stop', 'interval', 'start').index(c['factor']), skey(c['first'])))
        if ch:
            vals = [abs(c['metrics']['M_hist']['change'] or 0) for c in ch] + [c['metrics']['M_hist']['sum_of_aa_spreads'] or 0 for c in ch]
            lim = max(vals) * 1.12 or 1
            rows, last = [], None
            FN = dict(stop='Stop method: whole passes minus common stop', interval='Interval: short minus long', start='Start: common minus offset')
            for c in ch:
                if c['factor'] != last:
                    rows.append(dict(head=FN[c['factor']])); last = c['factor']
                h = c['metrics']['M_hist']
                fixed = [x for i, x in enumerate(sname(c['first']).split(', ')) if i != ('stop', 'interval', 'start').index(c['factor'])]
                if h['change'] is None:
                    rows.append(dict(name=', '.join(fixed), pts=[], right='not observed')); continue
                rows.append(dict(name=', '.join(fixed), pts=[dict(v=h['change'], c=C0, t=f"change of median D: {fs(h['change'])} GB/s")], bar=(-h['sum_of_aa_spreads'], h['sum_of_aa_spreads']), bar_t='sum of the two A/A spreads',
                                 right=f"{fs(h['change'], 1)}, band {f(h['sum_of_aa_spreads'], 1)} GB/s: {c['decision']}"))
            nr = sum(1 for c in ch if c['decision'] == 'resolved')
            outside = sum(1 for c in ch if c['metrics']['M_hist']['change'] is not None and abs(c['metrics']['M_hist']['change']) > c['metrics']['M_hist']['sum_of_aa_spreads'])
            note = f"{nr} of {len(ch)} changes of D are resolved. {pl(outside, 'dot lies', 'dots lie')} outside the grey band of its row."
            o.append('<h4>Change of D per factor</h4>' + rowchart(rows, -lim, lim, 'change of median D between two settings that differ in one factor (GB/s)', f'B7 session {s}: change of D per factor', note=note, vlines=[(0, '')]))
            o.append(f'<p class="cap">The grey band is the limit: the sum of the A/A spreads of the two settings, drawn to both sides of 0. A change is resolved only if the dot lies outside the band and every D of one setting lies on one side of every D of the other {R("handoff")}. Data: {ref}.</p>')
            big = max(ch, key=lambda c: abs(c['metrics']['M_hist']['change'] or 0))
            FW = dict(stop='the stop method', interval='the interval', start='the start')
            fixed = [x for i, x in enumerate(sname(big['first']).split(', ')) if i != ('stop', 'interval', 'start').index(big['factor'])]
            o.append(f"<p class=\"take\">The largest change is {fs(big['metrics']['M_hist']['change'])} GB/s ({fx(abs(big['metrics']['M_hist']['change']) / max(abs(med(meds)), 1e-9) * 100, 1)} % of the median D of this session). "
                     f"It is the change of {FW[big['factor']]}, with {' and '.join(fixed)}. It is {big['decision']}.</p>")
            o.append(details(f'Exact numbers of the {len(ch)} comparisons', table(
                ['Factor', 'First setting', 'Second setting', 'Change of median D, M_hist (GB/s)', 'Sum of the two A/A spreads, M_hist (GB/s)', 'Change, M_sum (GB/s)', 'Sum of A/A spreads, M_sum (GB/s)', 'Decision'],
                [(c['factor'], sname(c['first']), sname(c['second']), ('-' if c['metrics']['M_hist']['change'] is None else fs(c['metrics']['M_hist']['change'])), f(c['metrics']['M_hist']['sum_of_aa_spreads']),
                  ('-' if c['metrics']['M_sum']['change'] is None else fs(c['metrics']['M_sum']['change'])), f(c['metrics']['M_sum']['sum_of_aa_spreads']), c['decision']) for c in ch], 'sm')))
        # per mesh
        o.append('<h4>Rates per mesh</h4>')
        rows, trs, vmax = [], [], 0
        for st in S:
            rows.append(dict(head=sname(st)))
            for k in ('oldread', 'read', 'asmread'):
                a = b['kern'][st].get(k)
                if not a:
                    continue
                vmax = max(vmax, a['m0'], a['m1'])
                l0, l1 = ('l', 'r') if a['m0'] <= a['m1'] else ('r', 'l')
                rows.append(dict(name=KN[k], seg=(a['m0'], a['m1']), pts=[dict(v=a['m0'], c=C0, lab=fx(a['m0']), side=l0, op=1, t='mesh 0'), dict(v=a['m1'], c=C1, shape='diamond', lab=fx(a['m1']), side=l1, op=1, t='mesh 1')],
                                 right=f"mesh 0 minus mesh 1: {fs(a['m0'] - a['m1'])} GB/s"))
                trs.append((sname(st), KN[k], a['n'], f(a['hist']), f(a['mh0']), f(a['mh1']), f(a['m0']), f(a['m1']), f'{f(a["q_min"], 3)} to {f(a["q_max"], 3)}'))
        ko, kr = [b['kern'][st]['oldread'] for st in S if b['kern'][st].get('oldread')], [b['kern'][st]['read'] for st in S if b['kern'][st].get('read')]
        note = ''
        if ko and kr:
            note = (f"Median thread of old read: {rng([a['m0'] for a in ko])} GB/s on mesh 0 and {rng([a['m1'] for a in ko])} GB/s on mesh 1. "
                    f"New read: {rng([a['m0'] for a in kr])} and {rng([a['m1'] for a in kr])} GB/s.")
        o.append(rowchart(rows, 0, vmax * 1.1, 'median thread rate (GB/s), median over the intervals of the setting', f'B7 session {s}: median thread rate per mesh', L=150, R=230, rh=22, note=note))
        o.append(legend([(C0, 'mesh 0 (CPUs 0 to 63)', ''), (C1, 'mesh 1 (CPUs 64 to 119)', 'border-radius:0;transform:rotate(45deg)')]))
        if ko and kr:
            d0 = med([a['m0'] for a in ko]) - med([a['m0'] for a in kr]); d1 = med([a['m1'] for a in ko]) - med([a['m1'] for a in kr])
            o.append(f"<p class=\"take\">Old read minus new read, median thread over the settings: {fs(d0)} GB/s on mesh 0 and {fs(d1)} GB/s on mesh 1. This is a description. Data: {ref}.</p>")
        o.append(details('Exact numbers per setting, kernel and mesh', table(
            ['Setting', 'Kernel', 'Intervals', 'Total, M_hist (GB/s)', 'Mesh 0, M_hist (GB/s)', 'Mesh 1, M_hist (GB/s)', 'Median thread, mesh 0 (GB/s)', 'Median thread, mesh 1 (GB/s)', 'q, lowest to highest'], trs, 'sm')
            + '<p class="cap">Every rate is the median over the intervals of the kernel in the setting. The value of a mesh uses the longest time of all threads as divisor.</p>'))
        # per-thread chart
        rep = b['rep']
        if rep:
            o.append('<h4>Thread rate against CPU number, one interval of each kernel</h4>' + cpu_scatter(rep, f'B7 session {s}: thread rate against CPU number'))
            o.append(legend([(C0, 'old read', ''), (C1, 'new read', 'border-radius:0;transform:rotate(45deg)')]))
            why = dict(used='the setting in which B8, B5 and B9 of this session ran', chosen='the setting that the handoff rule selects for the later steps', fallback='the first setting with data')[rep['why']]
            o.append(f"<p class=\"cap\">The pair shown: process <code>{e(rep['tag'])}</code> (setting \"{sname(rep['setting'])}\"), its first old read interval (round {rep['old_s']['round']}, position {rep['old_s']['pos']}) "
                     f"and its first new read interval (round {rep['new_s']['round']}, position {rep['new_s']['pos']}). The rule for the choice: the first process in the file of {why}. "
                     f"In this pair q is {f(rep['old_s']['q'], 3)} for old read and {f(rep['new_s']['q'], 3)} for new read, and the totals are {f(rep['old_s']['hist'])} and {f(rep['new_s']['hist'])} GB/s. Data: {ref}.</p>")
        return '\n'.join(o)
    return fn


def b10_block(R):
    def fn(m, s, b):
        res = b['res']; ref = R((s, 'B10')); S = list(b['settings'])
        allv = [t[0] for st in S for k in b['settings'][st].values() for t in k['totals']]
        if not allv:
            return missing('No regular interval of B10.')
        lo, hi = min(allv), max(allv); pad = (hi - lo) * 0.05 or 1
        rows = []
        for st in S:
            rows.append(dict(head=sname(st)))
            for k, v in b['settings'][st].items():
                pts = [dict(v=t[0], c=C0, r=3.5, op=0.6, dy=((j * 7) % 5 - 2) * 2.0, t=f'{t[1]} round {t[2]} position {t[3]}: {fx(t[0])} GB/s, {fx(t[4], 1)} passes of all threads') for j, t in enumerate(v['totals'])]
                rows.append(dict(name=KN[k], pts=pts, right=(f"{f(v['lo'], 1)} to {f(v['hi'], 1)}, gap {f(v['gap'], 1)} GB/s" if v['totals'] else '-')))
        gaps = [(v['gap'], st, k) for st in S for k, v in b['settings'][st].items() if v['gap'] is not None]
        g = max(gaps)
        note = f"Largest gap between two neighbouring totals of one row: {f(g[0], 1)} GB/s ({KN[g[2]]}, {sname(g[1])})."
        o = [rowchart(rows, lo - pad, hi + pad, 'total of one interval, M_hist (GB/s). The axis does not start at 0.', f'B10 session {s}: totals of every interval', L=120, R=230, rh=20, note=note)]
        o.append(f'<p class="cap">One dot per interval, {len(allv)} intervals. Dots are moved a little up or down so that equal totals stay visible. The right column gives the lowest and the highest total of the row, and the largest gap between two neighbouring totals of the row. Data: {ref}.</p>')
        # Q2b: description per setting. The plan sets no rule for "separate levels".
        trs, over = [], 0
        for st in S:
            v = res['settings'][st]; ks = b['settings'][st]
            allk = med([t[0] for k in ks.values() for t in k['totals']])
            n_over = [KN[k] for k, kv in ks.items() if kv['gap'] is not None and v['control_total'] is not None and kv['gap'] > v['control_total']]
            over += bool(n_over)
            f2 = b['fail2'].get(st)
            trs.append((sname(st), f(allk, 1), f(ks['oldwrite']['med'], 1) if 'oldwrite' in ks else '-', rng([kv['gap'] for kv in ks.values()], 1), f(v['control_total'], 1),
                        (join_and(n_over) if n_over else 'none'), ('does not apply' if f2 is None else f'{f2[0]} of {f2[1]}'), ('-' if f2 is None else f'{f2[2]:g} to {f2[3]:g}')))
        o.append(table(['Setting', 'Median total over the four kernels (GB/s)', 'Median total of old write (GB/s)', 'Largest gap of a kernel, lowest to highest (GB/s)', 'Control of the total (GB/s)',
                        'Kernels whose largest gap is above the control of the total', 'Intervals that fail the 2 % check', 'Fewest passes of a thread in an interval, lowest to highest'], trs, 'wr'))
        medt = [float(r[1]) for r in trs]
        ow = [kv['med'] for st in S for k, kv in b['settings'][st].items() if k == 'oldwrite' and kv['med'] is not None]
        o.append(f"<p class=\"take\"><b>Question Q2b, description and no decision.</b> {ID}: the plan and the handoff set no rule for when two totals are separate levels, so this page does not decide whether the levels of 2026-11-13 remain. "
                 f"A rule on the gap, set before the data are read, would give it. What the data show: the largest gap of a kernel is above the control of the total of its setting in {over} of {len(S)} settings. "
                 f"The median total over the four kernels of a setting is {f(min(medt), 1)} to {f(max(medt), 1)} GB/s" + (f", and old write alone is {rng(ow, 1)} GB/s" if ow else '') + f". The remaining gaps are not assigned to a cause {R('plan')}.</p>")
        trs = []
        for st in S:
            v = res['settings'][st]
            for k in b['settings'][st]:
                kk = v['kernels'][k]
                trs.append((sname(st), KN[k], kk['n_processes'], NW(', '.join(fx(x, 1) for x in kk['spreads'])), f(kk['median_spread']), f(kk['median_total']),
                            NW(' / '.join(f(v[c], 1) for c in ('control_spread', 'control_total', 'control_mesh0', 'control_mesh1'))), kk['H11']))
        o.append(details('Spread, the three A/A controls, and H11 per setting and kernel', table(
            ['Setting', 'Kernel', 'Processes', 'Spread of each process (GB/s)', 'Median spread (GB/s)', 'Median total (GB/s)', 'Controls: spread / total / mesh 0 / mesh 1 (GB/s)', 'H11 (word of the plan)'], trs, 'sm')
            + '<p class="cap">The spread of a process is the highest minus the lowest total of the 4 intervals of a kernel. The three controls come from asm write and asm write 2 in the same setting.</p>'))
        sc = sorted(res['spread_changes'].values(), key=lambda c: (c['kernel'], ('stop', 'interval', 'start').index(c['factor']), skey(c['first'])))
        rs = [c for c in sc if c['decision'] == 'resolved']
        o.append(f"<p><b>Change of the spread per factor (H7a and H7b for write).</b> {len(rs)} of {len(sc)} comparisons {'shows' if len(rs) == 1 else 'show'} a resolved change of the spread. "
                 + (' '.join(f"{KN[c['kernel']]}, {c['factor']}: the median spread changes by {fs(c['change_of_spread'])} GB/s from \"{sname(c['second'])}\" to \"{sname(c['first'])}\" (sum of the two controls {f(c['sum_of_controls'])} GB/s)." for c in rs))
                 + f' Data: {ref}.</p>')
        o.append(details('Exact numbers of every comparison of the spread', table(
            ['Kernel', 'Factor', 'First setting', 'Second setting', 'Change of the median spread, first minus second (GB/s)', 'Sum of the two controls (GB/s)', 'Change of the median total (GB/s), description', 'Decision'],
            [(KN[c['kernel']], c['factor'], sname(c['first']), sname(c['second']), '-' if c['change_of_spread'] is None else fs(c['change_of_spread']), f(c['sum_of_controls']),
              '-' if c['change_of_median_total'] is None else fs(c['change_of_median_total']), c['decision']) for c in sc], 'sm')))
        # H11 chart
        rows, vals = [], [0.0]
        for st in S:
            v = res['settings'][st]
            rows.append(dict(head=f"{sname(st)}: controls total {f(v['control_total'], 1)}, mesh 0 {f(v['control_mesh0'], 1)}, mesh 1 {f(v['control_mesh1'], 1)} GB/s"))
            for k, kv in b['settings'][st].items():
                pts = []
                for j, h in enumerate(kv['hl']):
                    counted = v['control_total'] is not None and (h['hi'] - h['lo']) > v['control_total']
                    d0, d1 = h['hi_mesh'][0] - h['lo_mesh'][0], h['hi_mesh'][1] - h['lo_mesh'][1]
                    vals += [d0, d1]
                    tt = f"{h['tag']}: totals {fx(h['hi'])} and {fx(h['lo'])} GB/s"
                    pts.append(dict(v=d0, c=C0, shape='circle' if counted else 'ring', dy=-4, t=tt + f', mesh 0 {fs(d0)} GB/s', op=0.9))
                    pts.append(dict(v=d1, c=C1, shape='diamond' if counted else 'ring', dy=5, t=tt + f', mesh 1 {fs(d1)} GB/s', op=0.9))
                nc = sum(1 for h in kv['hl'] if v['control_total'] is not None and (h['hi'] - h['lo']) > v['control_total'])
                rows.append(dict(name=KN[k], pts=pts, right=f"{nc} of {len(kv['hl'])} processes count: {v['kernels'][k]['H11']}"))
        lim = max(abs(min(vals)), abs(max(vals))) * 1.1 or 1
        cells = [res['settings'][st]['kernels'][k]['H11'] for st in S for k in b['settings'][st]]
        note = 'H11 per kernel and setting in this session: ' + ', '.join(f'{cells.count(w)} {w}' for w in dict.fromkeys(cells)) + '.'
        o.append('<h4>H11: rate of each mesh in the highest interval minus the lowest interval of a process</h4>'
                 + rowchart(rows, -lim, lim, 'rate of the mesh in the highest interval minus its rate in the lowest interval (GB/s)', f'B10 session {s}: change per mesh between the lowest and the highest interval', L=120, R=250, rh=22, note=note, vlines=[(0, '')]))
        o.append(legend([(C0, 'mesh 0, process counts', ''), (C1, 'mesh 1, process counts', 'border-radius:0;transform:rotate(45deg)'), ('#fff', 'process does not count (either mesh)', f'border:1.5px solid {MUTED}')]))
        o.append(f'<p class="cap">Two markers per process. A process counts only if its highest and lowest total differ by more than the control of the total. Data: {ref}.</p>')
        sup = [(st, k) for st in S for k in b['settings'][st] if res['settings'][st]['kernels'][k]['H11'] == 'supported']
        t = ''
        rose = set()
        for st, k in sup:
            v = res['settings'][st]
            hl = [h for h in b['settings'][st][k]['hl'] if (h['hi'] - h['lo']) > v['control_total']]
            d0, d1 = [h['hi_mesh'][0] - h['lo_mesh'][0] for h in hl], [h['hi_mesh'][1] - h['lo_mesh'][1] for h in hl]
            which = [nm for nm, d, c in (('mesh 0', d0, v['control_mesh0']), ('mesh 1', d1, v['control_mesh1'])) if all(abs(x) > c for x in d)]
            rose.update(which)
            t += (f"Supported: {KN[k]} with \"{sname(st)}\". In its {len(hl)} counted processes mesh 0 changed by {rngs(d0)} GB/s (control {f(v['control_mesh0'])} GB/s) "
                  f"and mesh 1 by {rngs(d1)} GB/s (control {f(v['control_mesh1'])} GB/s). So the mesh that changed by more than its control is {' and '.join(which) or 'none'}. ")
        if len(sup) > 1:
            t += ('The supported cells name different meshes. ' if len(rose) > 1 else f"The supported cells name the same mesh ({', '.join(rose)}). ")
        if sup:
            t += 'A change below the control of its mesh does not count as a change, also when it is large.'
            o.append(f'<p class="take">{t}</p>')
        det = []
        for st in S:
            for k, kv in b['settings'][st].items():
                for h in kv['hl']:
                    det.append((sname(st), KN[k], e(h['tag']), f(h['hi']), f(h['hi_mesh'][0]), f(h['hi_mesh'][1]), f(h['lo']), f(h['lo_mesh'][0]), f(h['lo_mesh'][1]), fs(h['hi_mesh'][0] - h['lo_mesh'][0]), fs(h['hi_mesh'][1] - h['lo_mesh'][1])))
        o.append(details('Rates of each mesh in the highest and in the lowest interval of every process', table(
            ['Setting', 'Kernel', 'Process', 'Highest total (GB/s)', 'its mesh 0 (GB/s)', 'its mesh 1 (GB/s)', 'Lowest total (GB/s)', 'its mesh 0 (GB/s)', 'its mesh 1 (GB/s)', 'Mesh 0, high minus low (GB/s)', 'Mesh 1, high minus low (GB/s)'], det, 'sm')))
        return '\n'.join(o)
    return fn


def b8_block(R):
    def fn(m, s, b):
        ref = R((s, 'B8')); xs = b['counts']
        if len(xs) < 2:
            return missing('B8 has fewer than 2 counts of mesh-1 threads, so no line can be drawn.')
        o = []
        m0n = b['mesh0'][0] if b['mesh0'] else 64
        qs = [x['q'] for k in b['kern'].values() for v in k.values() for x in v]
        ymin = max(0.0, __import__('math').floor(min(qs) * 10 - 1) / 10)
        ser = []
        for k, col in (('oldread', C0), ('asmread', C1), ('asmread2', C2)):
            ser.append(dict(name=KN[k], c=col, nd=2, med=[(x, med([i['q'] for i in b['kern'][k][x]])) for x in xs], pts=[(x, i['q'], f'{KN[k]}, {m0n}+{x}: q {fx(i["q"], 3)}') for x in xs for i in b['kern'][k][x]]))
        o.append(linechart(ser, xs, ymin, 1.0, f'threads on mesh 1 (with {m0n} threads on mesh 0)', 'q', f'B8 session {s}: q against the count of mesh-1 threads', W=880, H=320, R=116,
                           title='q (thread at the 10th percentile divided by thread at the 90th percentile)', label_pts=(KN['oldread'], KN['asmread'])))
        t = f'<p class="cap">The q axis starts at {ymin:g}, not at 0. '
        for k in ('oldread', 'asmread'):
            md = [(x, med([i['q'] for i in b['kern'][k][x]])) for x in xs]
            md = [(x, v) for x, v in md if v is not None]
            ups = sum(1 for (_, a), (_, c) in zip(md, md[1:]) if c > a); downs = sum(1 for (_, a), (_, c) in zip(md, md[1:]) if c < a)
            if md:
                lo_, hi_ = min(md, key=lambda z: z[1]), max(md, key=lambda z: z[1])
                t += (f"Median q of {KN[k]}: lowest {f(lo_[1], 3)} at {m0n}+{lo_[0]} threads, highest {f(hi_[1], 3)} at {m0n}+{hi_[0]} threads. From one count to the next it rises {pl(ups, 'time', 'times')} and falls {pl(downs, 'time', 'times')}. ")
        o.append(t + f'No label is given. Data: {ref}.</p>')
        panels = []
        ymax = m.get('b8_ymax') or max(v for k in b['kern'].values() for iv in k.values() for x in iv for v in (x['m0'], x['m1']) if v is not None) * 1.12
        for k in ('oldread', 'asmread', 'asmread2'):
            s0 = dict(name='mesh 0', c=C0, med=[(x, med([i['m0'] for i in b['kern'][k][x]])) for x in xs], pts=[(x, i['m0'], f'{KN[k]}, {m0n}+{x}, mesh 0: {fx(i["m0"])} GB/s') for x in xs for i in b['kern'][k][x]])
            s1 = dict(name='mesh 1', c=C1, med=[(x, med([i['m1'] for i in b['kern'][k][x]])) for x in xs], pts=[(x, i['m1'], f'{KN[k]}, {m0n}+{x}, mesh 1: {fx(i["m1"])} GB/s') for x in xs for i in b['kern'][k][x] if i['m1'] is not None])
            panels.append('<div style="flex:0 1 440px">' + linechart([s0, s1], xs, 0, ymax, 'threads on mesh 1', 'GB/s', f'B8 session {s}: median thread rate per mesh, {KN[k]}', W=440, H=270, R=80, title=KN[k], label_pts=('mesh 0', 'mesh 1')) + '</div>')
        o.append('<h4>Median thread rate of each mesh against the count of mesh-1 threads</h4><div style="display:flex;flex-wrap:wrap;gap:8px">' + ''.join(panels) + '</div>')
        t = '<p class="cap">'
        for k in ('oldread', 'asmread'):
            first, last = b['kern'][k][xs[0]], b['kern'][k][xs[-1]]
            if first and last:
                t += (f"{KN[k].capitalize()}: the median thread on mesh 0 goes from {f(med([i['m0'] for i in first]))} GB/s at {m0n}+{xs[0]} to {f(med([i['m0'] for i in last]))} GB/s at {m0n}+{xs[-1]}, "
                      f"and on mesh 1 from {f(med([i['m1'] for i in first]))} to {f(med([i['m1'] for i in last]))} GB/s. ")
        o.append(t + f"The largest difference of q between neighbouring intervals of asm read and asm read 2 is {f(b['aa_q'], 3)}. Data: {ref}.</p>")
        trs = []
        for k in ('oldread', 'asmread', 'asmread2'):
            for x in xs:
                v = b['kern'][k][x]
                if v:
                    trs.append((KN[k], f'{m0n}+{x}', len(v), NW(', '.join(fx(i['q'], 3) for i in v)), f(med([i['q'] for i in v]), 3), f(med([i['m0'] for i in v])), f(med([i['m1'] for i in v])), f(med([i['hist'] for i in v]))))
        o.append(details('Exact numbers per kernel and count', table(['Kernel', 'Threads', 'Intervals', 'q of each interval', 'Median q', 'Median thread, mesh 0 (GB/s)', 'Median thread, mesh 1 (GB/s)', 'Median total, M_hist (GB/s)'], trs, 'sm')))
        return '\n'.join(o)
    return fn


def b5_block(R):
    def fn(m, s, b):
        ref = R((s, 'B5')); res = b['res']; K = [k for k in b['entries'] if b['kern'].get(k)]
        if 'oldread' not in K:
            return missing('B5 has no regular interval of old read.')
        var = res['variants']
        tv = [x['hist'] for k in K for x in b['kern'][k]]
        old = med([x['hist'] for x in b['kern']['oldread']])
        dproc = lambda k: (var.get(k, {}).get('total_difference') or {}).get('metrics', {}).get('M_hist', {}).get('median_D')
        rows = []
        for k in K:
            v = b['kern'][k]; mk = med([x['hist'] for x in v])
            rows.append(dict(name=KN.get(k, k), pts=[dict(v=x['hist'], c=C0 if k == 'oldread' else C1, shape='circle' if k == 'oldread' else 'diamond', t=f"{x['tag']}: {fx(x['hist'])} GB/s") for x in v],
                             right=f"median {f(mk, 1)} GB/s" + ('' if dproc(k) is None else f", old read {fs(dproc(k), 1)}")))
        others = [med([x['hist'] for x in b['kern'][k]]) for k in K if k != 'oldread']
        note = f"Median total of old read {f(old, 1)} GB/s. Every other kernel of the sequence: {rng(others, 1)} GB/s."
        o = [rowchart(rows, 0, max(tv) * 1.06, 'total of one interval, M_hist (GB/s)', f'B5 session {s}: total of each variant', L=110, R=250, note=note)]
        rows = []
        for k in K:
            v = b['kern'][k]
            rows.append(dict(name=KN.get(k, k), pts=[dict(v=x['q'], c=C0 if k == 'oldread' else C1, shape='circle' if k == 'oldread' else 'diamond', t=f"{x['tag']}: q {fx(x['q'], 3)}") for x in v],
                             right=f"q {rng([x['q'] for x in v], 3)}"))
        qo = [x['q'] for x in b['kern']['oldread']]; qv = [x['q'] for k in K if k != 'oldread' for x in b['kern'][k]]
        o.append(rowchart(rows, 0, 1.0, 'q of one interval (no unit)', f'B5 session {s}: q of each variant', L=110, R=250, note=f"q of old read {rng(qo, 3)}. q of every other kernel {rng(qv, 3)}."))
        o.append(f'<p class="cap">One marker per process ({b["n"]} processes, one interval of each kernel per process). In the upper chart "old read +x" is old read minus the kernel, as the median of the process values. Setting: {", ".join(sname(x) for x in b["settings"])}. Data: {ref}.</p>')
        nres = [k for k, v in var.items() if v['total_difference']['decision'] == 'resolved' and v['total_difference']['sign'] == 1]
        aa = next((v['total_difference']['metrics']['M_hist']['aa_spread'] for v in var.values() if v['total_difference']['metrics']['M_hist']['aa_spread'] is not None), None)
        t = f"<p class=\"take\">Old read minus the variant is resolved with old read above for {len(nres)} of {len(var)} kernels (A/A spread {f(aa)} GB/s). "
        if 'read_sparse' in var and dproc('read_sparse') is not None:
            t += (f"Old read minus <code>read_sparse</code> is {fs(dproc('read_sparse'))} GB/s (median of the {var['read_sparse']['total_difference']['metrics']['M_hist']['n_processes']} process values). "
                  + (f"The difference of the two median totals is {fx(abs(med([x['hist'] for x in b['kern']['read_sparse']]) - old), 1)} GB/s, which is the same quantity computed in another way." if b['kern'].get('read_sparse') else ''))
        o.append(t + '</p>')
        trs = []
        for k in K:
            v = b['kern'][k]; d = var.get(k, {}).get('total_difference'); h = d['metrics']['M_hist'] if d else None
            off = m['offsets'].get(('bwx', k))
            trs.append((KN.get(k, k), len(v), f(med([x['hist'] for x in v])), f(med([x['msum'] for x in v])), NW(rng([x['q'] for x in v], 3)), f(med([x['m0'] for x in v])), f(med([x['m1'] for x in v])),
                        (fs(h['median_D']) if h and h['median_D'] is not None else '-'), (f(h['aa_spread']) if h else '-'), NW(f"{d['decision']}{A.sign_txt(d['sign'])}" if d else '-'), '-' if off is None else off))
        o.append(table(['Kernel', 'Intervals', 'Median total, M_hist (GB/s)', 'Median total, M_sum (GB/s)', 'q, lowest to highest', 'Median thread, mesh 0 (GB/s)', 'Median thread, mesh 1 (GB/s)',
                        'Old read minus kernel, median of the processes (GB/s)', 'A/A spread (GB/s)', 'Decision for the difference', 'Loop start modulo 64 (B)'], trs, 'sm'))
        return '\n'.join(o)
    return fn


def b5_intro(m, R):
    """Printed once, above the sessions."""
    t = (f'<p>The rule of the handoff asks two things of a variant: the pattern label of old read, and a total whose difference to old read is not resolved {R("handoff")}. '
         'The label is not used. Where the difference of the totals is resolved, the variant does not show the total of old read, and that part alone decides the rule.</p>')
    t += f'<p>Loop offsets are from the build listing {R("offsets")}. '
    ks = [k for k in ('read_sparse', 'read_nop4', 'read_nop8', 'read_nop16', 'read_nop32', 'asmread', 'asmread2')]
    o5 = {k: m['offsets'].get(('bwx', k)) for k in ks}
    if all(v is not None for v in o5.values()):
        groups = {}
        for k, v in o5.items():
            groups.setdefault(v, []).append(KN.get(k, k))
        t += ' '.join(f"{', '.join(g)}: loop at {v} modulo 64." for v, g in sorted(groups.items())) + (' So the variants do not all share one loop offset.' if len(groups) > 1 else '')
    else:
        t += f'{ID}: the offsets file was not found.'
    return t + f' {R("devb")}</p>'


def b9_block(R):
    def fn(m, s, b):
        ref = R((s, 'B9')); k1, k2 = b['kinds']['one_buffer'], b['kinds']['two_buffers']; tot = b['res']['total']
        if not k1['pv'] or not k2['pv']:
            return missing('B9 needs processes with one buffer and with two buffers. One kind is missing.')
        vals = [v for _, v in k1['pv'] + k2['pv']]
        lo, hi = min(vals), max(vals); pad = (hi - lo) * 0.25 or 1
        rows = [dict(name='one buffer per thread', pts=[dict(v=v, c=C0, t=f'{t}: {fx(v)} GB/s', lab=fx(v, 1), side='a' if i % 2 else 'b') for i, (t, v) in enumerate(sorted(k1['pv'], key=lambda z: z[1]))],
                     right=f"median {f(med([v for _, v in k1['pv']]))} GB/s"),
                dict(name='two buffers per thread', pts=[dict(v=v, c=C1, shape='diamond', t=f'{t}: {fx(v)} GB/s', lab=fx(v, 1), side='a' if i % 2 else 'b') for i, (t, v) in enumerate(sorted(k2['pv'], key=lambda z: z[1]))],
                     right=f"median {f(med([v for _, v in k2['pv']]))} GB/s")]
        if tot['difference'] is not None:
            note = f"Total with one buffer minus total with two: {fs(tot['difference'])} GB/s. A/A value: {f(tot['aa_value'])} GB/s."
        else:
            note = 'Fewer than 2 processes of a kind.'
        o = [rowchart(rows, lo - pad, hi + pad, 'median total of the intervals of one process, M_hist (GB/s). The axis does not start at 0.', f'B9 session {s}: total of old read with one and with two buffers', L=160, R=150, rh=46, note=note)]
        q1, q2 = [x['q'] for x in k1['ivs']], [x['q'] for x in k2['ivs']]
        t = f'<p class="take"><b>Description.</b> '
        if tot['difference'] is not None:
            t += (f"The total with one buffer minus the total with two is {fs(tot['difference'])} GB/s ({fx(abs(tot['difference']) / med(vals) * 100, 2)} % of the total). "
                  f"The largest difference between two processes of one kind is {f(tot['aa_value'])} GB/s. So the difference of the totals is {tot['decision']}. ")
        t += (f"q of old read is {rng(q1, 3)} with one buffer ({len(q1)} intervals) and {rng(q2, 3)} with two ({len(q2)} intervals). "
              + ('The two ranges of q overlap.' if q1 and q2 and max(min(q1), min(q2)) <= min(max(q1), max(q2)) else 'The two ranges of q do not overlap.'))
        o.append(t + f' One marker per process. Setting: {", ".join(sname(x) for x in b["settings"])}. Data: {ref}.</p>')
        o.append(table(['Kind', 'Processes', 'Median total of each process (GB/s)', 'Intervals', 'q, lowest to highest', 'Median thread, mesh 0 (GB/s)', 'Median thread, mesh 1 (GB/s)'],
                       [(nm, k['n'], ', '.join(fx(v) for _, v in k['pv']), len(k['ivs']), rng([x['q'] for x in k['ivs']], 3), f(med([x['m0'] for x in k['ivs']])), f(med([x['m1'] for x in k['ivs']])))
                        for nm, k in (('one buffer', k1), ('two buffers', k2))]))
        return '\n'.join(o)
    return fn


def c3_block(R):
    def fn(m, s, b):
        ref = R((s, 'C3')); km = b['km']
        if not km:
            return missing('C3 has no counter row that can be used.')
        kernels = [k for k in ('oldread', 'read', 'asmread', 'asmread2', 'read_sparse', 'read_nop4', 'read_nop8', 'read_nop16', 'read_nop32') if (k, 'mesh0') in km or (k, 'mesh1') in km]
        o = [f"<p>{b['res']['rows_C']} C rows were read (one per thread and interval), and {b['res']['rows_C_not_used']} were not used. Data: {ref}.</p>"]
        panels = []
        for key, lab, nd in (('median_l1d_refill_per_line', 'L1 refills per 64 B line', 4), ('median_l2d_refill_per_line', 'L2 refills per 64 B line', 4),
                             ('median_ll_read_miss_per_line', 'last-level read misses per 64 B line', 4), ('median_clock_GHz', 'clock of the busy core (GHz)', 4)):
            vals = [g[key] for gs in km.values() for g in gs if g[key] is not None]
            if not vals:
                panels.append(f'<div style="flex:1 1 400px">{missing(lab + ": the event is not supported or did not open. The event list of step A7 names the events.")}</div>'); continue
            lo, hi = min(vals), max(vals); pad = (hi - lo) * 0.15 or abs(hi) * 0.01 or 1
            rows = []
            for k in kernels:
                pts, rt = [], []
                for mesh, col, shp, dy in (('mesh0', C0, 'circle', -4), ('mesh1', C1, 'diamond', 5)):
                    gv = [g[key] for g in km.get((k, mesh), []) if g[key] is not None]
                    pts += [dict(v=x, c=col, shape=shp, dy=dy, r=3.5, op=0.7, t=f'{KN.get(k, k)} {mesh}: {fx(x, nd)}') for x in gv]
                    rt.append(f(med(gv), 4))
                rows.append(dict(name=KN.get(k, k), pts=pts, right=' / '.join(rt)))
            panels.append('<div style="flex:0 1 440px">' + rowchart(rows, lo - pad, hi + pad, lab + '. The axis does not start at 0.', f'C3 session {s}: {lab}', L=92, R=104, W=440, rh=22,
                                                                                    note=lab + ' (mesh 0 / mesh 1)', ticks=ticks_for(lo - pad, hi + pad, 4)) + '</div>')
        o.append('<div style="display:flex;flex-wrap:wrap;gap:8px">' + ''.join(panels) + '</div>')
        o.append(legend([(C0, 'mesh 0', ''), (C1, 'mesh 1', 'border-radius:0;transform:rotate(45deg)')]))
        # computed comparison old read against new read
        t = '<p class="take"><b>Description, and no rule of the plan decides on it.</b> '
        for key, lab in (('median_l2d_refill_per_line', 'L2 refills per line'), ('median_ll_read_miss_per_line', 'last-level read misses per line')):
            for mesh in ('mesh0', 'mesh1'):
                a = [g[key] for g in km.get(('oldread', mesh), []) if g[key] is not None]; c = [g[key] for g in km.get(('read', mesh), []) if g[key] is not None]
                if a and c:
                    per = lambda v: (f' (about 1 per {fx(1 / med(v), 1)} lines)' if med(v) and med(v) < 0.5 else '')
                    t += f"{lab.capitalize()} on {mesh.replace('mesh', 'mesh ')}: old read {rng(a, 4)}{per(a)}, new read {rng(c, 4)}{per(c)}. "
        ck = [g['median_clock_GHz'] for gs in km.values() for g in gs if g['median_clock_GHz'] is not None]
        if ck:
            t += f"The clock of a busy core is {rng(ck, 4)} GHz over all kernels and both meshes, a spread of {fx((max(ck) - min(ck)) / med(ck) * 100, 2)} %."
        o.append(t + '</p>')
        trs = []
        for k in kernels:
            for mesh in ('mesh0', 'mesh1'):
                gs = km.get((k, mesh), [])
                if gs:
                    r_ = lambda key, nd=4: rng([g[key] for g in gs], nd)
                    trs.append((KN.get(k, k), mesh.replace('mesh', 'mesh '), len(gs), sum(g['n_rows'] for g in gs), r_('median_thread_GBps', 2), r_('median_clock_GHz'), r_('median_instructions_per_line'),
                                r_('median_l1d_refill_per_line'), r_('median_l2d_refill_per_line'), r_('median_ll_read_miss_per_line')))
        o.append(details('Exact numbers per kernel and mesh', table(
            ['Kernel', 'Mesh', 'Groups', 'C rows', 'Median thread rate (GB/s)', 'Clock (GHz)', 'Instructions per line', 'L1 refills per line', 'L2 refills per line', 'Last-level read misses per line'], trs, 'sm')
            + '<p class="cap">Each cell gives the lowest and the highest group median. A line is 64 B of the bytes that the thread counted. The clock is the cycle count divided by the CPU time of the thread.</p>'))
        # cputime against elapsed
        if b['n_rows']:
            lw = b['lowest']
            o.append('<h4>CPU time against elapsed time (threads that lost their CPU for a part of an interval)</h4>')
            o.append(table(['Interval length (ms)', 'C rows', 'Lowest CPU time as a share of elapsed time (%)', 'Largest elapsed time minus CPU time in one interval (ms)', 'Rows below 99 %'],
                           [(ms, g['n'], fx(g['share_min'] * 100, 2), fx(g['off_max'], 2), g['below99']) for ms, g in sorted(b['cpu'].items())]))
            o.append(f"<p class=\"take\">In {b['n_below99']} of {b['n_rows']} rows the thread had its CPU for less than 99 % of the interval. The lowest share is {fx(lw['share'] * 100, 2)} %. "
                     f"That thread ran on CPU {lw['cpu']} ({KN.get(lw['kernel'], lw['kernel'])}, process <code>{e(lw['tag'])}</code>). It had {fx(lw['off_ms'], 2)} ms of its {fx(lw['elapsed'] * 1e3, 1)} ms without CPU time.</p>")
        return '\n'.join(o)
    return fn


def sec_h10_h9b(m, R):
    o = ['<h2 id="h10">H10 and H9b: what these data can and cannot say</h2>']
    h = {x['label']: x for x in m['hyp']}
    o.append(f'<h3>H10: "{h["H10"]["word"]}"</h3><ul>'
             '<li><b>Can say:</b> how many refills of its own caches a core counted for each 64 B line that the loop read, per kernel and mesh. The section of C3 gives these values.</li>'
             f'<li><b>Cannot say:</b> whether the memory system fetched lines that the loop did not consume. The core events count refills that the core saw. The plan states that H10 could still hold for traffic that these events do not count {R("plan")}.</li>'
             f'<li><b>{ID}:</b> memory requests per line read. Step D1 would give them (mesh counters <code>hns_mc_reqs_local_all</code> and <code>hns_mc_reqs_remote_all</code>, with root). Part D was not run. Even D1 can support H10 and cannot reject it {R("plan")}.</li></ul>')
    o.append(f'<h3>H9b: "{h["H9b"]["word"]}"' + (', open for the user' if h['H9b']['open'] else '') + '</h3><ul>'
             '<li>The hypothesis table gives the ranges of q and of the total of old read per session, and the two readings of the word.</li>'
             f'<li><b>Cannot say:</b> why old read gave totals of {fx(PLAN_OLD_LOW[0])} to {fx(PLAN_OLD_LOW[1])} GB/s on 2026-10-30 {R("plan")}. That run is a number from an earlier result folder. Rule 10 of the plan uses such a number for hypotheses only, not as evidence.</li>'
             '<li><b>Cannot say:</b> anything about another day or about the state after a restart of the machine. The section "When the sessions ran" gives the times.</li>'
             f'<li><b>{ID}:</b> the same steps on another day, and after a restart of the machine. They would show whether the values of old read change for a reason other than the kernel.</li></ul>')
    return '\n'.join(o)


WORDS = [
    ('CRB', 'the Arm Phoenix Reference Server (128 cores of the 64-bit Arm architecture). All measurements ran there.'),
    ('Plan, handoff', 'the files <code>plan.md</code> (the reviewed test plan) and <code>handoff.md</code> (the instructions for its execution).'),
    ('Part A, B, C, D', 'the parts of the plan. Part A: screening with the existing benchmark. Part B: the changed benchmark. Part C: core counters without root. Part D: counters and page addresses that need root. Part D was not run.'),
    ('Q2, Q2a, Q2b', 'the second question of the plan. Q2a: why old read has a higher total than new read with 120 threads. Q2b: why the write kernels give several separate totals.'),
    ('<code>bwx</code>', 'the changed copy of the benchmark <code>bandwidth.c</code> that Parts B and C use. It holds the old kernels, the new kernels and all variants in one program.'),
    ('Kernel', 'one timed loop of the benchmark. It is not the Linux kernel.'),
    ('Old read (<code>oldread</code>)', 'the read loop before 2026-11-13. Per 128 B it runs 4 load instructions (<code>ldp</code>, 32 B each) and 8 vector adds.'),
    ('New read (<code>read</code>)', 'the read loop since 2026-11-13, written in C. Per 256 B it runs 8 <code>ldp</code> and no add.'),
    ('asm read (<code>asmread</code>), asm read 2 (<code>asmread2</code>)', 'the read loop written in assembly, with the same loop body as new read, and a second copy of it under another name.'),
    ('Old write, new write, asm write, asm write 2', 'the write loops in the same four forms (<code>oldwrite</code>, <code>write</code>, <code>asmwrite</code>, <code>asmwrite2</code>).'),
    ('<code>nop</code>', 'an instruction that does nothing.'),
    ('<code>read_nop4</code>, <code>read_nop8</code>, <code>read_nop16</code>, <code>read_nop32</code>', 'the asm read loop with 4, 8, 16 or 32 <code>nop</code> instructions added per 256 B.'),
    ('<code>read_sparse</code>', 'a read loop with 4 <code>ldp</code> and 9 <code>nop</code> per 128 B. It has the 16 instructions per 128 B of old read and no vector add.'),
    ('Loop offset', 'the address of the first instruction of a loop modulo 64 B.'),
    ('Process, launch, tag', 'one start of <code>bwx</code>. Its name in the run script is its tag, for example <code>pass-500-common-p1</code>.'),
    ('Visit', 'one login to CRB that runs one or more steps. Each step writes its own result folder.'),
    ('Short run', 'one run of every sequence with 0.1 s intervals before session 1, made to test the scripts.'),
    ('Sequence, interval, round, position', 'a process times a list of kernels (the sequence), one interval per entry. A round is one run of the whole sequence. The position counts the entries from 0.'),
    ('Pass', 'one sweep of a thread over its whole buffer.'),
    ('Process value', 'one number per process, for example the median total of its intervals. Decisions use process values, never single intervals.'),
    ('Warm-up pass', 'one pass that a thread makes with the kernel before the timed interval starts. It is not timed.'),
    ('Header line, <code>env.txt</code>, <code>launches.txt</code>', 'the run script writes one header line per launch into the csv file, with the load readings. <code>env.txt</code> holds the readings at the start and the end of a visit. <code>launches.txt</code> holds a second reading and the 5 busiest processes before each launch.'),
    ('Root', 'administrator rights on CRB. Our scripts do not use them.'),
    ('Session', 'one run of all steps. The plan asks for two sessions some hours apart. The section "When the sessions ran" gives the times.'),
    ('256 MiB, GB/s', 'each thread has its own buffer of 256 MiB (1 MiB = 2<sup>20</sup> bytes), which is read from main memory. Rates are in GB/s (1 GB = 10<sup>9</sup> bytes).'),
    ('Mesh 0, mesh 1', 'the two halves of the chip. CPUs 0 to 63 are on mesh 0. CPUs 64 to 127 are on mesh 1, and we use 64 to 119.'),
    ('a+b threads, 64+56', 'a threads on mesh 0 and b threads on mesh 1. 64+56 is all 120 CPUs that we may use.'),
    ('Thread rate', 'the bytes of one thread divided by its own elapsed time.'),
    ('Total, M_hist', 'the bytes of all threads divided by the longest elapsed time of a thread. This is what the benchmark prints. It is the decision metric.'),
    ('M_sum', 'the sum of the thread rates. It is reported next to M_hist as a description.'),
    ('Median', 'the middle value of a sorted list. With an even count it is the mean of the two middle values.'),
    ('q', 'the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one interval. With 120 threads these are the 12th and the 108th smallest rate. q near 1 means that all threads have nearly the same rate.'),
    ('Pattern', 'how the thread rates of one interval are distributed over the threads.'),
    ('Split, uniform', 'the two pattern labels of the handoff (q below 0.65, q above 0.85). They are not used on this page.'),
    ('Bounded prediction', 'the one measurable statement of a hypothesis that a step tests.'),
    ('Setting', 'one combination of stop method, interval length and start.'),
    ('Stop method', '"whole passes": a thread stops after a whole pass, as in <code>bandwidth.c</code>. "common stop": all threads stop at one common time and count the bytes of the partial pass.'),
    ('Start', '"common start": every thread starts at the start of its buffer. "offset start": every thread starts at its own offset inside its buffer.'),
    ('Reproduction condition', 'the setting "whole passes, 0.5 s, common start". It is the timing method of the run of 2026-11-13.'),
    ('2 % check', 'rule 7 of the plan for whole passes: one pass must take at most 2 % of the interval. That means at least 50 passes per thread.'),
    ('D', 'the total of old read minus the total of new read, in GB/s. One value per process: the mean over its rounds.'),
    ('A/A control, A/A spread, E', 'an A/A control is one loop that exists twice in the program (asm read and asm read 2). E is the difference of the two copies in one process. The A/A spread is the largest absolute E over the processes of a setting.'),
    ('Resolved', 'the absolute median of the process values is larger than the A/A spread, and all process values have one sign. A change between two settings is resolved if it is larger than the sum of the two A/A spreads and the two sets of values do not overlap.'),
    ('Limit, band (of a change)', 'the sum of the two A/A spreads (B7) or of the two controls of the spread (B10) of the two settings that are compared. A chart draws it as a grey band around 0.'),
    ('A/A value', 'the A/A control of a comparison that has no A/A spread per setting: for B7 with one kernel per process, and for the totals of B9.'),
    ('Spread (B10)', 'for one write kernel in one process: the highest minus the lowest total of its 4 intervals.'),
    ('Controls (B10)', 'three values from asm write and asm write 2: the control of the spread, of the total, and of the rate of each mesh.'),
    ('Cell (B10), counted process', 'a cell is one kernel in one setting. A process counts for H11 only if its highest and lowest total differ by more than the control of the total.'),
    ('Level (of write totals), gap', 'the run of 2026-11-13 gave write totals in separate groups, called levels. The gap is the distance between two neighbouring totals of one kernel in one setting.'),
    ('Group (C3)', 'one setting and one sequence.'),
    ('Irregular interval, late, end skew', 'a thread is late if it starts more than 100 µs after the common start. The end skew is the latest end minus the earliest end of the threads. An interval is irregular if a thread is late or if the end skew with the common stop is above 5 ms.'),
    ('Page state, P row', 'how many bytes of a buffer are on 2 MiB pages (huge-page coverage), read from <code>/proc/self/smaps</code> and printed in a P row.'),
    ('I row, T row, C row', 'output rows of <code>bwx</code>. I: one per interval. T: one per thread and interval, with bytes and times. C: one per thread and interval with the counter values.'),
    ('Counter, cycles, refill, last-level read miss', 'a counter is a hardware event counter of one core. Cycles are clock ticks of the core. L1 and L2 are the first and the second cache level of a core. An L1 or L2 refill is a line that this cache level had to fetch. A last-level read miss is a read that the last cache level did not hold.'),
    ('Line', '64 B, the unit of a cache.'),
    ('Clock', 'cycles of an interval divided by the CPU time of the thread in that interval, in GHz.'),
    ('CPU time', 'the time for which a thread really ran on its CPU (the thread CPU clock of Linux).'),
    ('Load, runnable tasks, <code>waited_s</code>, logins', 'the Linux 1-minute load average (average count of tasks that run or wait to run), the count of tasks that can run at one moment, the seconds the script waited for an idle system before a launch, and the count of logged-in users.'),
    ('<code>ps</code>, <code>kworker</code>, <code>systemd</code>, <code>rcu_preempt</code>', '<code>ps</code> is the Linux tool that lists processes. The others are service tasks of the operating system.'),
    ('UTC', 'Coordinated Universal Time. All times of this page are in UTC.'),
    ('B7', 'step: the four read kernels at 64+56 threads in all 8 settings, and the reproduction condition with one kernel per process.'),
    ('B10', 'step: the four write kernels at 64+56 threads in 8 settings, with 0.5 s and 15 s as the two intervals.'),
    ('B8', 'step: old read, asm read and asm read 2 at 64 threads on mesh 0 and 32 to 56 threads on mesh 1.'),
    ('B5', 'step: old read against new read, <code>read_sparse</code>, the four <code>nop</code> variants and asm read at 64+56 threads.'),
    ('B9', 'step: old read with one buffer and with two buffers per thread.'),
    ('C3', 'step: the sequences of B7 and B5 with core counters.'),
    ('D1', 'step of Part D: counters of the mesh (the network that joins the cores and the memory), which need root. Not run.'),
    ('H7a', 'hypothesis: a part of the difference is made by the stop method and the short interval.'),
    ('H7b', 'hypothesis: a part of the difference is made by the common start.'),
    ('H8', 'hypothesis: with threads on both meshes the chip has two states. A loop that only loads reaches the uniform state at a lower thread count than old read.'),
    ('H9a', 'hypothesis: the second buffer per thread moved old read to the uniform pattern on 2026-10-30.'),
    ('H9b', 'hypothesis: the pattern of old read differs between days or sessions for a reason other than the kernel.'),
    ('H10', 'hypothesis: in the uniform state the memory system fetches lines that the loop does not consume.'),
    ('H11', 'hypothesis: the write totals differ because the threads of one mesh run faster in some intervals.'),
    ('H3b', 'hypothesis of question Q1: the physical address of the pages decides the level at 8 MiB.'),
    ('The five words', 'rule 11 of the plan. "rejected": the bounded prediction failed in both sessions. "not rejected". "not observed": an event that the test could have shown did not occur. "not resolved": the difference is inside the A/A spread, or the rule cannot be applied. "not tested".'),
    ('Fail, hold, described', 'results of one session. "fail": the bounded prediction failed in that session. "hold": it held. "described": the session gives values and no decision.'),
    ('Open for the user', 'a judgment between two readings of a rule. This page prints both readings and does not choose.'),
    ('Supported, contradicted', 'the words of the plan for B8 and for one cell of H11 in one session. For a word over the sessions this page writes "not rejected" and "rejected" and adds the word of the plan in brackets.'),
]


def short_version(m):
    """At most three sentences, built from computed values. No hypothesis label: the list under the box gives the words."""
    h = {x['label']: x for x in m['hyp']}
    ss = [s for s in m['sessions'] if 'B7' in m['S'][s]]
    if not ss:
        return f'{ID}: the input holds no process of step B7, so the difference between the old and the new read loop at 64+56 threads cannot be described.'
    sets = [(s, v) for s in ss for v in m['S'][s]['B7']['res']['settings'].values()]
    nres = sum(1 for _, v in sets if v['decision'] == 'resolved' and v['sign'] == 1)
    md = [v['metrics']['M_hist']['median_D'] for _, v in sets if v['metrics']['M_hist']['median_D'] is not None]
    nset = max(len(m['S'][s]['B7']['res']['settings']) for s in ss)
    where = (f"in all {nset} timing settings of {'both sessions' if len(ss) == 2 else pl(len(ss), 'session', 'sessions')}" if nres == len(sets) else f'in {nres} of {len(sets)} timing settings')
    s1 = (f"With 120 threads on the test server CRB (64 on one half of the chip and 56 on the other, each reading its own 256 MiB buffer), "
          f"the old read loop moved {rng(md, 1)} GB/s more in total than the new read loop {where}.")
    ch = [(s, c) for s in ss for c in m['S'][s]['B7']['res']['changes'].values() if c['metrics']['M_hist']['change'] is not None]
    s2 = ''
    if ch:
        bs, bc = max(ch, key=lambda t: abs(t[1]['metrics']['M_hist']['change']))
        mD = med([v['metrics']['M_hist']['median_D'] for v in m['S'][bs]['B7']['res']['settings'].values()])
        s2 = (f" The largest change of that difference between two timing methods (stop rule, interval length or start position) was {fx(abs(bc['metrics']['M_hist']['change']))} GB/s "
              f"({fx(abs(bc['metrics']['M_hist']['change']) / abs(mD) * 100, 1)} % of the difference)" + (', so no timing method removed it.' if nres == len(sets) else '.'))
    s3 = (' The cause inside the chip is not tested, because the counters that need root were not run.' if h['H10']['word'] == 'not tested' else '')
    return s1 + s2 + s3


def build(m, banner=None):
    R = make_refs(m)
    one = len(m['sessions']) < 2
    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>Parts B and C, question Q2: result</title>', f'<style>{CSS} h4{{font-size:14px;margin:22px 0 6px}} table.sm{{font-size:12px}} table.sm td,table.sm th{{padding:4px 5px}} '
         'table.wr td,table.hy td{white-space:normal} table.wr td:first-child{min-width:190px} table.wr td:nth-child(2){white-space:nowrap} table.hy td:first-child{min-width:110px} table.hy td:nth-child(2){min-width:80px} table.hy td:nth-child(3){min-width:120px} table.hy td:nth-child(4){min-width:290px} table.hy td:nth-child(5){min-width:220px} table.hr td{white-space:normal} table.hr td:nth-child(2){min-width:250px} table.hr td:nth-child(4){min-width:170px} ul.words{columns:2;column-gap:28px;font-size:13px} ul.words li{break-inside:avoid}</style></head><body>']
    if banner:
        o.append(f'<p class="banner">{e(banner)}</p>')
    o.append('<h1>Parts B and C, question Q2: 64+56 threads at 256 MiB</h1>')
    o.append(f'<p class="take"><b>Short version.</b> {short_version(m)}</p>')
    o.append('<p>The result per hypothesis in one line each. The section "Result per hypothesis" gives the basis.</p>' + hyp_bullets(m))
    o.append(f'<p>Question Q2 comes from the benchmark run of 2026-11-13 {R("plan")}. With 120 threads, old read totalled 464 to 467 GB/s. New read totalled 280 to 304 GB/s. The write kernels gave several separate totals. '
             f'This page gives the results of the steps B7, B10, B8, B5, B9 and C3 for that question. The decision rules are those of the handoff, applied by the analysis script {R("handoff", "analyze")}.</p>')
    parts = []
    for s in m['sessions']:
        nf, st = len(m['folders'][s]), m['S'][s]['steps']
        two = sorted({folder_step(x).rstrip('ab') for x in m['folders'][s] if folder_step(x)[-1:] in 'ab' and folder_step(x)[:-1] in STEPS})
        parts.append(f"Session {e(s)} has {pl(nf, 'result folder', 'result folders')} for {pl(len(st), 'step', 'steps')} ({', '.join(st) or 'no step of Q2'})" + (f". {join_and(two)} has two folders" if two and nf > len(st) else '') + '.')
    t = '<p>Input: ' + ' '.join(parts)
    miss = [(s, st) for s in m['sessions'] for st in STEPS if st not in m['S'][s]]
    t += (' No step is missing.' if not miss else ' Missing: ' + ', '.join(f'{st} in session {e(s)}' for s, st in miss) + '.')
    if one:
        t += ' The page holds one session. Every "rejected" is impossible with one session, because rule 11 of the plan needs both sessions.'
    o.append(t + '</p>')
    o.append('<h2 id="words">Words used here</h2><ul class="words">' + ''.join(f'<li><b>{k}</b>: {v}</li>' for k, v in WORDS) + '</ul>')
    o += [sec_hyp(m, R), sec_facts(m, R), sec_load(m, R), sec_integrity(m, R)]
    o.append('<h2 id="b7">B7: old read against new read in 8 timing settings</h2>'
             f'<p>Each process runs old read, new read, asm read and asm read 2 in alternating order on the same buffers, 2 rounds. D is one value per process {R("handoff")}. '
             'The last row of each chart and table has one kernel per process. Its process value is the median total of the 3 intervals of a process. Its D is the median of old read minus the median of new read. '
             f'Its A/A value is the median of asm read 2 minus the median of asm read {R("handoff")}. The 2 % check applies to whole passes only: an interval fails if a thread ran fewer than 50 passes {R("plan")}.</p>'
             + per_session(m, 'B7', b7_block(R), 'A run of step B7 would give D and its A/A spread.'))
    o.append('<h2 id="b10">B10: the write kernels in 8 timing settings</h2>'
             f'<p>Each process runs old write, new write, asm write and asm write 2, 2 rounds. Every kernel has 4 intervals per process and 16 per setting {R("handoff")}. '
             'A mesh "has changed" only if its change between the highest and the lowest interval of a process is larger than the control of that mesh. '
             'H11 is "supported" for one kernel in one setting if three things hold in every counted process. Exactly one mesh has changed. It has risen. It is the same mesh in every counted process. '
             f'With fewer than 2 counted processes the result is "not observed" {R("handoff")}.</p>'
             + per_session(m, 'B10', b10_block(R), 'A run of step B10 would give the totals of the write kernels.'))
    o.append('<h2 id="b8">B8: q and thread rates against the count of mesh-1 threads</h2>'
             f'<p>H8 is worded with a count of mesh-1 threads at which the pattern changes. The handoff finds that count from the labels split and uniform {R("handoff")}. The labels are not used, so the result for H8 is "not resolved" (page rule 1). '
             'In the charts, lines join the medians of the intervals of one count, and small dots are the single intervals. Printed values are medians. The value at the last count stands in the label at the end of each line.</p>'
             + per_session(m, 'B8', b8_block(R), 'A run of step B8 would give q per thread count.'))
    o.append('<h2 id="b5">B5: read variants against old read</h2>' + b5_intro(m, R)
             + per_session(m, 'B5', b5_block(R), 'A run of step B5 would give the totals of the variants.'))
    o.append('<h2 id="b9">B9: old read with one buffer and with two buffers per thread</h2>'
             f'<p><b>Decision.</b> H9a predicts the label uniform with two buffers and the label split with one. The labels are not used, so the result for H9a is "not resolved" (page rule 1). '
             f'The comparison of the totals needs no label, and it is a description. Its A/A value is the largest difference between two processes of one kind {R("devs")}.</p>'
             + per_session(m, 'B9', b9_block(R), 'A run of step B9 would give the comparison.'))
    o.append('<h2 id="c3">C3: core counters per kernel and mesh</h2>'
             f'<p>A C row is not used if its counter group did not run for the whole enabled time {R("handoff")}. The charts and the table give medians over the threads of one mesh. One group is one setting and one sequence. A chart has one marker per group. Its right column gives the median of the group medians for mesh 0 and for mesh 1, in the unit of the panel. '
             f'The CPU time of a thread exists only in runs with counters. A run without counters does not mark a thread that lost its CPU inside an interval. This was found in the short run {R("short")}.</p>'
             + per_session(m, 'C3', c3_block(R), 'A run of step C3 would give the counters.'))
    o.append(sec_h10_h9b(m, R))
    T = m['timing']
    o.append('<h2 id="limits">Limits of this page</h2><ul>'
             + (f'<li>The sessions are one continuous run of one night. Session {e(T["gaps"][0][1])} started {hm(T["gaps"][0][2])} after session {e(T["gaps"][0][0])} ended. No result of this page says anything about another day or about the state after a restart.</li>' if T['gaps'] and T['gaps'][0][2] < 3600 else '')
             + f'<li>No value on this page is the traffic of the time in which all threads ran. A thread records only its total, so the bytes of the common time are not measured {R("handoff")}. Rule 6 of the plan is met only in part.</li>'
             f'<li>The page state of an interval with many threads is the reading taken after the interval before it. A change during the warm-up pass shows only in the next reading {R("handoff")}.</li>'
             f'<li>A thread that loses its CPU inside an interval is not marked in a run without counters {R("short")}. Only C3 has the CPU time of each thread.</li>'
             f'<li>With 120 threads the main thread of <code>bwx</code> has no CPU of its own. It shares a CPU with a worker {R("devb")}. {ID}: the size of this effect on CRB. A run with the main thread on a spare CPU would give it, and the rules of the host allow CPUs 0 to 119 only.</li>'
             f'<li>The loop of <code>read_sparse</code> starts at 4 modulo 64, and the other asm read loops start at 20 {R("offsets", "devb")}. So B5 compares <code>read_sparse</code> at another loop offset.</li>'
             f'<li>Part D (root counters, physical pages) was not run. So H3b of question Q1 is "not tested", and H10 is "not tested" {R("plan")}.</li>'
             f'<li>The limits 100 µs and 5 ms for an irregular interval are provisional {R("handoff")}.</li>'
             '<li>The decisions use many comparisons of two settings. No correction for the number of comparisons is made.</li>'
             + (f'<li>One session only. Every result is the result of that session. "rejected" needs a second session {R("plan")}.</li>' if one else '')
             + f'<li>{ID}: load readings during an interval. The script reads the load only before each launch.</li>'
             '<li>The chart colours were not checked with the palette checker of the chart rules, because Node.js is not installed on the machine where this page was built. Every chart also uses position, marker shape or a text label.</li></ul>')
    o.append('<h2 id="refs">References</h2><ul>' + ''.join(f'<li>[Ref{i}] {t}</li>' for i, t in enumerate(R.items, 1)) + '</ul></body></html>')
    body = tidy_refs('\n'.join(o[:-1]))
    return body + '\n' + o[-1]


def main(argv=None):
    ap = argparse.ArgumentParser(description='result page of Q2 (steps B7, B10, B8, B5, B9, C3)')
    ap.add_argument('--session', nargs='+', action='append', required=True, metavar=('NAME', 'FOLDER'))
    ap.add_argument('-o', '--out', default='partB-q2-result.html')
    ap.add_argument('--banner')
    ap.add_argument('--offsets', default=OFFSETS)
    a = ap.parse_args(argv)
    sp = {}
    for s in a.session:
        if len(s) < 2:
            ap.error('--session needs a name and at least one folder')
        sp.setdefault(s[0], []).extend(s[1:])
    m = compute(sp, a.offsets)
    with open(a.out, 'w') as fh:
        fh.write(build(m, a.banner))
    print('wrote', a.out)
    for h in m['hyp']:
        print('  %-14s %s%s' % (h['label'], h['word'], ' (%s)' % h['plan_word'] if h['plan_word'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
