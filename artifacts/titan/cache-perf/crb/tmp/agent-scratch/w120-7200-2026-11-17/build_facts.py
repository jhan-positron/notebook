#!/usr/bin/env python3
"""build_facts.py - builds the facts sheet of the 7200 MT/s whole-chip rerun of 2026-11-17.

Reads:  raw result files under R, the converted baseline copies under S/base8000, the scripts in S,
        and three records outside R (the DIMM report, FINDINGS.md of 2026-11-15, run_kernels.sh of 2026-11-13).
Writes: S/facts.json and S/FACTS.md. It changes no other file.

Every number in FACTS.md is formatted by this script from a value that it read or computed.
No measured number is typed by hand in the text templates of facts_text.py and facts_text4.py.

Usage: python3 build_facts.py            write both files, print the checks and the verdicts
       python3 build_facts.py --print    also print FACTS.md

Files: facts_data.py (parsers, range functions), build_facts.py (records, integrity checks, facts.json),
       facts_text.py and facts_text4.py (statistics, verdicts, text of FACTS.md).
"""
import glob
import json
import os
import re
import sys

sys.dont_write_bytecode = True

import facts_data as fd                     # noqa: E402
from facts_data import R, S, rel            # noqa: E402

GO_LOG = os.path.join(R, 'go-T72-20261117T221209Z.log')
GO2_LOG = os.path.join(R, 'go2-T72-20261117T222335Z.log')
POS01 = {('oldread', 0), ('asmread', 1)}    # the positions of part L: oldread first, asmread directly after it
READ3 = ('oldread', 'read', 'asmread')


def iso(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def r3(x):
    return None if x is None else round(x, 3)


# ----------------------------------------------------------------------------- collection

def boot_of(table, t):
    """Boot of the DIMM report table that contains time t."""
    cand = [b for b in table['boots'] if b['start'] <= t]
    return cand[-1]


def collect():
    D = dict(recs=[], checks=[])
    recs = D['recs']
    try6 = D['try6'] = fd.read_try6()
    bt = D['boot_table'] = fd.read_boot_table()
    logs = D['logs'] = dict(go=fd.read_log(GO_LOG), go2=fd.read_log(GO2_LOG))
    boot72 = dict(speed_MTps=try6['speed_MTps'], modules=try6['dimm_sockets'], boot=try6['boot'])

    def state_of(folder):
        """speed, modules and boot label of an earlier result folder, from the boot table of the DIMM report."""
        t = fd.folder_date(folder)
        assert t < bt['until']['utc'], folder
        b = boot_of(bt, t)
        return dict(speed_MTps=bt['until']['speed'], modules=b['modules'],
                    boot='boot %d of the DIMM report (Linux start %s UTC)' % (b['no'], b['start'].strftime('%Y-%m-%d %H:%M')))

    # ---- the rerun: part A
    A = D['A'] = []
    for tag, s in fd.RERUN_A:
        folder = fd.find('k120-' + tag)
        A.append(dict(part='A', tag=tag, session=s, folder=folder, csv=os.path.join(folder, 'threads120.csv'),
                      probe=fd.read_probe(os.path.join(folder, 'probe.txt')),
                      procs=fd.read_k120(os.path.join(folder, 'threads120.csv'))))
    # ---- the rerun: parts L, C and the control I (runner bwx12)
    X = D['X'] = []
    for part, items in (('L', fd.RERUN_L), ('C', fd.RERUN_C), ('I', fd.RERUN_I)):
        for it in items:
            folder = fd.find('w120-' + it[0])
            csvs = sorted(glob.glob(os.path.join(folder, '*.csv')))
            assert len(csvs) == 1, csvs
            secs = fd.read_bwx(csvs[0])
            assert len(secs) == 1
            err = os.path.join(folder, 'stderr.txt')
            fd.OPENED.append(err)
            X.append(dict(part=part, tag=it[0], session=it[1], spec=it[2] if part == 'C' else 'like', folder=folder,
                          csv=csvs[0], sec=secs[0], ivs=fd.bwx_intervals(secs[0]), env=fd.read_env(folder),
                          launches=fd.read_launches(folder), stderr_bytes=os.path.getsize(err)))

    # ---- order in time, gap since the previous 120-thread process, start state
    ev = []
    for a in A:
        ev.append(dict(part='A', tag=a['tag'], session=a['session'], obj=a, start=fd.folder_date(a['folder']),
                       first=fd.clock(a['folder'], a['procs'][0]['utc']),
                       last=fd.clock(a['folder'], a['procs'][-1]['utc']), end=a['probe']['utc_after'],
                       load1=a['procs'][0]['load1']))
    for x in X:
        la = x['launches'][0]
        ev.append(dict(part=x['part'], tag=x['tag'], session=x['session'], obj=x, start=fd.folder_date(x['folder']),
                       first=la['utc'], last=la['utc'], end=la['rc_utc'], load1=la['load1']))
    ev.sort(key=lambda e: e['first'])
    go_start = logs['go']['states'][0]['utc']
    prev = None
    for e in ev:
        e['prev'] = prev
        e['gap_s'] = None if prev is None else (e['first'] - prev['end']).total_seconds()
        if prev is None:
            e['state'] = ('started from an idle machine, %.0f s after go.sh started (1-minute load average %.2f)'
                          % ((e['first'] - go_start).total_seconds(), e['load1']))
        elif e['part'] == 'I':
            e['state'] = ('started from an idle machine (1-minute load average %.2f), %.0f s after the 120-thread '
                          'bwx12 process %s' % (e['load1'], e['gap_s'], prev['tag']))
        elif prev['part'] == 'A':
            e['state'] = 'started %.0f s after the last 120-thread process of part A (%s)' % (e['gap_s'], prev['tag'])
        else:
            e['state'] = 'started %.0f s after the 120-thread bwx12 process %s' % (e['gap_s'], prev['tag'])
        prev = e
    D['events'] = ev
    evd = {e['tag']: e for e in ev}

    def add_k120(procs, folder, order_known=True, **common):
        for n, p in enumerate(procs, 1):
            before = 'none (first process of the file)'
            if n > 1:
                before = '%s %s' % (procs[n - 2]['binary'], procs[n - 2]['kernel'])
            if not order_known:
                # The list holds only a part of the processes of the file. A process whose header line is line 1
                # of the file is the first process of the file. Before every other one, processes ran that are
                # not in the list.
                before = ('none (first process of the file)' if p['hdr_line'] == 1 else
                          'not listed (other processes of the file ran in between)')
            for iv in p['iv']:
                rec = fd.base_record(
                    folder=rel(folder), file=os.path.basename(p['file']), line=iv['line'], process=n,
                    round=p['round'], interval=iv['rep'], kernel=p['kernel'], kernel_before=before,
                    binary=p['binary'], GBps=iv['agg'], rate_kind=fd.KIND_A, passes=iv['passes'],
                    per_thread_min_GBps=iv['tmin'], per_thread_max_GBps=iv['tmax'], per_thread_avg_GBps=iv['tavg'],
                    threads=iv['threads'], stop='whole pass', min_ms=500, load1_at_launch=p['load1'],
                    launch_utc=iso(fd.clock(folder, p['utc'])), tag=p['tag'])
                rec.update(common)
                rec['proc_key'] = '%s|%s|%d' % (rec['folder'], rec['file'], n) + ('|' + p['tag'] if p['tag'] else '')
                recs.append(rec)

    def add_bwx(sec, folder, proc_tag, kernels=None, positions=None, **common):
        nseq = len(sec['hdr']['seq'].split(','))
        h = sec['hdr']
        for iv in fd.bwx_intervals(sec):
            if kernels and iv['kernel'] not in kernels:
                continue
            if positions and (iv['kernel'], iv['pos']) not in positions:
                continue
            rec = fd.base_record(
                folder=rel(folder), file=os.path.basename(sec['file']), line=iv['line'], round=iv['round'],
                pos=iv['pos'], interval=iv['round'] * nseq + iv['pos'], kernel=iv['kernel'],
                kernel_before=iv['kernel_before'] or 'none (first interval of the process)', GBps=iv['total'],
                rate_kind=fd.KIND_X, mesh0_GBps=iv['mesh0'], mesh1_GBps=iv['mesh1'], threads=iv['threads'],
                is_64_56=iv['is_64_56'], flagged=iv['flagged'], stop=h.get('stop'), start=h.get('start'),
                min_ms=int(h['min_ms']),
                count=int(h.get('count', 0)), thp=h.get('thp'), tag=proc_tag)
            rec.update(common)
            rec['proc_key'] = '%s|%s|%s' % (rec['folder'], rec['file'], proc_tag)
            recs.append(rec)

    # ---- records of the rerun
    for a in A:
        e = evd[a['tag']]
        n0 = len(recs)
        add_k120(a['procs'], a['folder'], dataset='rerun-A', part='A', role='rerun', session=a['session'],
                 gap_s=e['gap_s'], start_state=e['state'], **boot72)
        for rec in recs[n0:]:
            rec['tag'] = a['tag']
            rec['binary_sha256'] = a['probe']['sha'][rec['binary']]
            if rec['process'] > 1:      # ra.sh starts processes 2 to 24 directly after the previous one, with no wait
                rec['gap_s'] = None
    role_of = dict(L='rerun', C='rerun', I='control, added after the first numbers of parts A, L and C were seen')
    for x in X:
        e = evd[x['tag']]
        la = x['launches'][0]
        add_bwx(x['sec'], x['folder'], x['tag'], dataset='control-I' if x['part'] == 'I' else 'rerun-' + x['part'],
                part=x['part'], role=role_of[x['part']], session=x['session'], binary='bwx12',
                binary_sha256=x['env']['sha'], load1_at_launch=la['load1'], launch_utc=iso(la['utc']),
                gap_s=e['gap_s'], start_state=e['state'], **boot72)

    # ---- 8000 MT/s baselines of part A (fixed list of baselines-and-rules.txt)
    D['base'] = base = {}
    kfolder = os.path.join(R, 'kernels-20261113T181222Z')
    pfolder = os.path.join(R, 'partA-20261113T205055Z')
    base['A-1'] = dict(folder=kfolder, file='threads120.csv', procs=fd.read_k120(os.path.join(kfolder, 'threads120.csv')))
    base['A-2'] = dict(folder=pfolder, file='A1.csv', procs=fd.read_k120(os.path.join(pfolder, 'A1.csv')))
    base['A-3'] = dict(folder=pfolder, file='A3.csv', procs=fd.read_k120(
        os.path.join(pfolder, 'A3.csv'), only_tags=lambda t: re.fullmatch(r'onebuf-ms500-[123]', t) is not None))
    # The copy kernels count read plus written bytes. The header line of every copy and asmcopy process must say so,
    # because facts.json gives the meaning of the field "passes" from it.
    cp = [p for procs in [a['procs'] for a in A] + [b['procs'] for b in base.values()] for p in procs
          if p['kernel'] in ('copy', 'asmcopy')]
    assert cp and all(p.get('copy_note') for p in cp), 'a copy process without the header note on read+write bytes'
    D['probe13'] = open_probe13(kfolder)
    D['env_partA'] = fd._open(os.path.join(pfolder, 'env.txt')).read()
    sha13 = D['probe13']['sha']
    for name, order_known in (('A-1', True), ('A-2', True), ('A-3', False)):
        b = base[name]
        n0 = len(recs)
        add_k120(b['procs'], b['folder'], order_known=order_known, dataset=name, part='A', role='baseline',
                 **state_of(b['folder']))
        for rec in recs[n0:]:
            rec['binary_sha256'] = sha13[rec['binary']]

    # ---- bwx folders written by rx.sh or r0.sh (one csv per process)
    rx_sets = [
        # dataset, role, folder prefix, files, positions
        ('L-1', 'baseline (identical argument line)', 'w120-R8', ['a6456.csv'], None),
        ('L-2', 'supporting (4 s, other counter events)', 'w120-R1', ['p1nop.csv', 'p2add.csv'], POS01),
        ('L-3', 'supporting (4 s, other counter events)', 'w120-R5', ['thp.csv'], POS01),
        ('L-4', 'supporting (4 s, other counter events)', 'w120-R6', ['st1.csv', 'st2.csv', 'st3.csv'], POS01),
        ('R0', 'other binary (bwx11)', 'w120-R0', ['p1.csv', 'p2.csv'], POS01),
        ('R0b', 'other binary (bwx11), 4 s', 'w120-R0b', ['cA.csv', 'cB.csv', 'cC.csv'], POS01),
        ('X2d12', 'not a baseline (firmware test setting)', 'w120-X2d12', ['a6456.csv'], None),
        ('X1d10', '10 modules', 'w120-X1d10', ['a6456.csv'], POS01),
        ('X1d10b', '10 modules', 'w120-X1d10b', ['a6456.csv'], POS01),
        ('BASEd10', '10 modules', 'w120-BASEd10', ['a6456.csv'], POS01),
        ('F72d12', '7200 MT/s sample of the same boot, earlier visit, not part of the rerun', 'w120-w120-F72d12',
         ['a6456.csv'], None),
    ]
    D['rx'] = {}
    for name, role, prefix, files, positions in rx_sets:
        folder = fd.find(prefix)
        env = fd.read_env(folder)
        env['has_binary_line'] = env['sha'] is not None
        if env['sha'] is None:      # r0.sh wrote no binary line to env.txt; the script itself holds the checksum
            txt = fd._open(os.path.join(fd.W15, 'r0.sh')).read()
            env['sha'] = re.search(r'echo "([0-9a-f]{64})  \$BW"', txt)[1]
            env['sha_line'] = next(i for i, l in enumerate(txt.splitlines(), 1) if env['sha'] in l)
            env['binary'] = re.search(r'^BW=(\S+)', txt, re.M)[1]
        la = {l['tag']: l for l in fd.read_launches(folder)}
        err = os.path.join(folder, 'stderr.txt')
        fd.OPENED.append(err)
        if name == 'F72d12':
            # The folder holds no boot id. Its process lies between two readings of the boot id of the rerun:
            # try6.txt before it and the first state line of go.sh after it. The text of section 4.1 states this.
            st = dict(boot72)
            assert fd.folder_date(folder) > try6['first_log_utc']
            f72 = la[files[0][:-4]]
            go0 = logs['go']['states'][0]
            assert try6['utc'] < f72['utc'] < f72['rc_utc'] < go0['utc'] and go0['boot'] == try6['boot'], 'F72d12'
            assert try6['boots_first'] <= f72['utc'] and f72['rc_utc'] <= try6['boots_last'], 'F72d12, boots.txt'
            assert try6['first_log_utc'] <= f72['utc'] and f72['rc_utc'] <= try6['last_log_utc'], 'F72d12, gaps.txt'
        else:
            st = state_of(folder)
        D['rx'][name] = dict(folder=folder, env=env, launches=la, files=files, role=role, state=st, secs={},
                             stderr_bytes=os.path.getsize(err))
        for fn in files:
            sec = fd.read_bwx(os.path.join(folder, fn))[0]
            tag = fn[:-4]
            D['rx'][name]['secs'][tag] = sec
            add_bwx(sec, folder, tag, positions=positions, dataset=name, part='L', role=role,
                    binary=fd.SHA_NAMES[env['sha'][:8]], binary_sha256=env['sha'], load1_at_launch=la[tag]['load1'],
                    launch_utc=iso(la[tag]['utc']), **st)

    # ---- folders of the first runner bwx (2026-11-13/14): one csv with one section per process
    step_sets = [
        ('B7a', 'B7-20261113T232859Z', 'B7.csv', 'common-6000-'),
        ('B7b', 'B7-20261114T024352Z', 'B7.csv', 'common-6000-'),
        ('C3a', 'C3-20261114T022708Z', 'C3.csv', 'common-6000-'),
        ('C3b', 'C3-20261114T054116Z', 'C3.csv', 'common-6000-'),
        ('B5a', 'B5-20261114T011723Z', 'B5.csv', 'b5-fwd-'),
        ('B5b', 'B5-20261114T043213Z', 'B5.csv', 'b5-fwd-'),
        ('B5a-rev', 'B5-20261114T011723Z', 'B5.csv', 'b5-rev-'),
        ('B5b-rev', 'B5-20261114T043213Z', 'B5.csv', 'b5-rev-'),
    ]
    D['step'] = {}
    for name, fname, csv, prefix in step_sets:
        folder = os.path.join(R, fname)
        envtxt = fd._open(os.path.join(folder, 'env.txt')).read()
        sha = re.search(r'^([0-9a-f]{64})  bwx$', envtxt, re.M)[1]
        allsecs = fd.read_bwx(os.path.join(folder, csv))
        for i, s in enumerate(allsecs):
            s['prev_step'] = allsecs[i - 1]['step'] if i else None
        secs = [s for s in allsecs if s['step']['tag'].startswith(prefix)]
        D['step'][name] = dict(folder=folder, file=csv, sha=sha, secs=secs, prefix=prefix)
        for sec in secs:
            st = sec['step']
            add_bwx(sec, folder, st['tag'], kernels=READ3, dataset=name, part='C',
                    role='other binary (bwx)' + (', reverse kernel order, not in the list of rule V4'
                                                 if name.endswith('-rev') else ''),
                    binary=fd.SHA_NAMES[sha[:8]], binary_sha256=sha, load1_at_launch=st['load1'],
                    launch_utc=iso(fd.clock(folder, st['utc'])), **state_of(folder))
    D['hw'] = hw_records(D)
    D['hw_cmp'] = hw_compare(D['hw'])
    D['fw'] = open_fw()
    D['a2pre'] = open_a2pre()
    D['mod'] = open_mod()
    return D


HW_ROWS = ('L-1', 'L-2', 'L-3', 'L-4', 'R0', 'R0b')     # the bwx12 and bwx11 rows of the 2026-11-09 boot


def hw_records(D):
    """Hardware error records of the saved journal of the 2026-11-09 boot inside the process windows of the
    rows HW_ROWS. The window of a process runs from its launch line to its rc line in launches.txt.
    Both the journal and launches.txt give whole seconds. So a record with the journal time J and a launch
    line with the time L lies between J - L - 1 and J - L + 1 seconds after the process start.
    A record is 'inside' an interval when this whole span lies between the start and the end of the interval,
    'possible' when the span and the interval share a part, and 'outside' otherwise.
    The fields 'kind' and 'interval' of a record test only the intervals that the sheet uses: oldread at position 0
    and asmread at position 1. The field 'every' holds the same test against every interval of the process."""
    errs = fd.read_error_records(D['probe13']['h5'])
    boots = {D['rx'][n]['state']['boot'] for n in HW_ROWS}
    assert len(boots) == 1, boots
    out = []
    for name in HW_ROWS:
        v = D['rx'][name]
        for tag, sec in v['secs'].items():
            la = v['launches'][tag]
            assert D['probe13']['boot_start'] < la['utc'] < la['rc_utc']
            allv = fd.bwx_intervals(sec)
            used = [iv for iv in allv if (iv['kernel'], iv['pos']) in POS01]
            hits = []
            for e in errs:
                if not la['utc'] <= e['utc'] <= la['rc_utc']:
                    continue
                off = (e['utc'] - la['utc']).total_seconds()
                kind, where = 'outside', None
                for iv in used:
                    if iv['t_start'] <= off - 1 and off + 1 <= iv['t_end']:
                        kind, where = 'inside', iv
                    elif off - 1 < iv['t_end'] and iv['t_start'] < off + 1 and kind != 'inside':
                        kind, where = 'possible', iv
                # the same test against every interval of the process (all kernels and positions), for hw_compare()
                every = []
                for iv in allv:
                    if iv['t_start'] <= off - 1 and off + 1 <= iv['t_end']:
                        every.append(('inside', iv))
                    elif off - 1 < iv['t_end'] and iv['t_start'] < off + 1:
                        every.append(('possible', iv))
                hits.append(dict(e, offset_s=off, kind=kind, interval=where, every=every))
            out.append(dict(dataset=name, tag=tag, folder=v['folder'], file=sec['file'], launch=la, used=used,
                            all=allv, records=hits))
    return out


def hw_compare(hw):
    """Every interval (all kernels and positions) of the processes of hw_records() that has a record, against the
    interval of the same kernel at the same position in the other round of the same process.
    rows:   the records lie inside the interval, or the interval is the only one that their span of +-1 s touches.
    border: records whose span touches two intervals. The 1 s resolution cannot assign them to one of them.
    clean:  the positions at which neither round has a record inside it or at its border, with round 1 minus round 0.
    This is a view added after the numbers were seen. The sheet draws no wording by rule V1 point 2 from it."""
    rows, border, clean = [], [], []
    for h in hw:
        if not h['records']:
            continue
        ivs = h['all']
        assert {iv['round'] for iv in ivs} == {0, 1}, (h['dataset'], h['tag'])
        mark = {}                                   # id(interval) -> every record that touches it
        for e in h['records']:
            for kind, iv in e['every']:
                mark.setdefault(id(iv), []).append(e)

        def other(iv):
            o = [x for x in ivs if (x['pos'], x['kernel']) == (iv['pos'], iv['kernel']) and x['round'] != iv['round']]
            assert len(o) == 1, (h['dataset'], h['tag'], iv['pos'])
            return o[0]

        def cmp_(iv):
            o = other(iv)
            return dict(iv=iv, other=o, other_has_records=id(o) in mark, diff=iv['total'] - o['total'])
        owner = {}                                  # id(interval) -> (interval, where, records assigned to it)
        by_t = {}
        for e in h['records']:
            kinds = [k for k, _ in e['every']]
            assert 1 <= len(kinds) <= 2, (h['dataset'], h['tag'], e['line'], kinds)
            if len(kinds) == 1:
                iv = e['every'][0][1]
                if kinds[0] == 'inside':
                    where = 'inside'
                else:
                    assert e['offset_s'] - 1 < iv['t_start'] and iv is ivs[0], (h['dataset'], h['tag'], e['line'])
                    where = 'before or inside'
                slot = owner.setdefault(id(iv), (iv, where, []))
                assert slot[1] == where
                slot[2].append(e)
            else:
                assert kinds == ['possible', 'possible'], (h['dataset'], h['tag'], e['line'], kinds)
                by_t.setdefault(e['utc'], []).append(e)
        for iv, where, es in owner.values():
            rows.append(dict(cmp_(iv), dataset=h['dataset'], tag=h['tag'], file=h['file'], where=where, records=es,
                             used=(iv['kernel'], iv['pos']) in POS01))
        for t, es in sorted(by_t.items()):
            pair = [iv for _, iv in es[0]['every']]
            assert all([iv for _, iv in e['every']] == pair for e in es)
            border.append(dict(dataset=h['dataset'], tag=h['tag'], file=h['file'], records=es,
                               intervals=[cmp_(iv) for iv in pair]))
        for pos in sorted({iv['pos'] for iv in ivs}):
            a, b = sorted((iv for iv in ivs if iv['pos'] == pos), key=lambda iv: iv['round'])
            if id(a) not in mark and id(b) not in mark:
                clean.append(dict(dataset=h['dataset'], tag=h['tag'], file=h['file'], pos=pos, kernel=a['kernel'],
                                  r0=a, r1=b, diff=b['total'] - a['total']))
    return dict(rows=rows, border=border, clean=clean)


def hw_compare_json(hc):
    """hw_compare() as a record of facts.json (meta.hardware_error_records.all_intervals)."""
    iv_ = lambda x: dict(kernel=x['kernel'], round=x['round'], pos=x['pos'], line=x['line'],
                         t_start_s=round(x['t_start'], 3), t_end_s=round(x['t_end'], 3), GBps=r3(x['total']))
    cmp_ = lambda x: dict(iv_(x['iv']), other_round=dict(iv_(x['other']), has_records=x['other_has_records']),
                          minus_other_round_GBps=r3(x['diff']))
    recs_ = lambda es: dict(journal_lines=[e['line'] for e in es], offset_s=sorted({e['offset_s'] for e in es}))
    cmax = max(hc['clean'], key=lambda x: abs(x['diff']))
    return dict(
        note='view added after the numbers were seen, not part of the rules fixed before the run. Every interval '
             '(all kernels and positions) of the processes above that has a record, by the same rule as "kind": the '
             'span offset_s - 1 to offset_s + 1 against the interval. other_round = the interval of the same kernel at '
             'the same position in the other round of the same process. minus_other_round_GBps = rate of the interval '
             'with records minus the rate of other_round. The comparison is not a test: the hypothesis that a '
             'corrected record lowers the rate of its interval is not tested',
        with_records=[dict(dataset=r['dataset'], tag=r['tag'], file=rel(r['file']), where=r['where'],
                           used_by_the_sheet=r['used'], **recs_(r['records']), **cmp_(r)) for r in hc['rows']],
        at_the_border_of_two_intervals=[dict(dataset=b['dataset'], tag=b['tag'], file=rel(b['file']),
                                             intervals=[cmp_(x) for x in b['intervals']], **recs_(b['records']))
                                        for b in hc['border']],
        positions_without_records=dict(
            note='positions of the processes with records at which neither round has a record inside it or at its '
                 'border. Difference = round 1 minus round 0',
            n_positions=len(hc['clean']),
            n_positions_above_1_GBps=sum(abs(x['diff']) > 1.0 for x in hc['clean']),
            largest=dict(dataset=cmax['dataset'], tag=cmax['tag'], kernel=cmax['kernel'], pos=cmax['pos'],
                         round_1_minus_round_0_GBps=r3(cmax['diff']))))


def open_fw():
    """Records of the firmware settings tool (uefisettings) under R: the saved settings lists, the replies of
    every 'set' call, and the last reading of the memory speed setting."""
    mtime = lambda p: fd.dt.datetime.utcfromtimestamp(int(os.path.getmtime(p)))
    out = dict(lists={}, sets={})
    # every file with one of the two names under R, so that the text can say that no other one exists
    found = dict(set=[], q=[])
    for root, dirs, names in os.walk(R):
        dirs.sort()
        for n in sorted(names):
            if n == 'set.txt':
                found['set'].append(os.path.join(root, n))
            elif n == 'questions.json':
                found['q'].append(os.path.join(root, n))
    lists = dict(base=os.path.join(R, 'uefisettings-20261117', 'questions.json'),
                 x1=os.path.join(R, 'fwtest-20261117', 'x1', 'post', 'questions.json'),
                 revert=os.path.join(R, 'fwtest-20261117', 'revert', 'questions.json'))
    sets = dict(x1=os.path.join(R, 'fwtest-20261117', 'x1', 'set.txt'),
                x2=os.path.join(R, 'fwtest-20261117', 'x2', 'set.txt'),
                revert=os.path.join(R, 'fwtest-20261117', 'revert', 'set.txt'),
                dimm=os.path.join(R, 'dimm7200-20261117', 'set.txt'))
    assert sorted(found['q']) == sorted(lists.values()), found['q']
    assert sorted(found['set']) == sorted(sets.values()), found['set']
    key = lambda e: (e['name'], e['answer'], json.dumps(e['options']), e['help'])
    for k, path in lists.items():
        q = json.loads(fd._open(path).read())
        assert all(sorted(e) == ['answer', 'help', 'name', 'options'] for e in q), path
        val = {}
        for n in ('TXREQ Max', 'TXREQ Min', 'DIMM Frequency'):
            hit = [e['answer'] for e in q if e['name'] == n]
            assert len(hit) == 1, (path, n)
            val[n] = hit[0]
        un = sum(1 for e in q if e['answer'].startswith('<ValueUnavailable'))
        err = sum(1 for e in q if e['answer'].startswith('<VStoreError'))      # a read error of the tool, not a value
        out['lists'][k] = dict(path=path, mtime=mtime(path), n=len(q), unavailable=un, store_error=err,
                               readable=len(q) - un - err,
                               val=val, keys=sorted(map(key, q)), order=[key(e) for e in q])
    b, r = out['lists']['base'], out['lists']['revert']
    out['same_entries'] = b['keys'] == r['keys']
    out['same_order'] = b['order'] == r['order']
    out['x1_diff'] = sorted(set(out['lists']['x1']['keys']) ^ set(b['keys']))
    # the replies of the 'set' calls. Two forms exist: one JSON object per line, or the debug print of the tool.
    for k, path in sets.items():
        lines = fd._open(path).read().splitlines()
        try:
            when, when_line = fd.dt.datetime.strptime(lines[0], '%a %b %d %I:%M:%S %p UTC %Y'), 1
        except ValueError:
            when, when_line = None, None
        rep = []
        block = None
        for ln, l in enumerate(lines, 1):
            t = l.strip()
            if t.startswith('{"responses"'):
                for x in json.loads(t)['responses']:
                    rep.append(dict(kind='set' if 'modified' in x else 'get', name=x['question']['name'],
                                    answer=x['question']['answer'], modified=x.get('modified'), line=ln))
            elif t in ('SetResponse {', 'GetResponse {'):
                block = dict(kind=t[:3].lower(), name=None, answer=None, modified=None, line=None)
            elif block is not None:
                m = re.match(r'(name|answer): "(.*)",$', t)
                if m and block[m[1]] is None:
                    block[m[1]] = m[2]
                    if m[1] == 'answer':
                        block['line'] = ln
                m = re.match(r'modified: (true|false),$', t)
                if m:
                    block['modified'] = m[1] == 'true'
                if t.startswith('is_translated:'):
                    rep.append(block)
                    block = None
        assert rep and all(x['name'] and x['answer'] for x in rep), path
        out['sets'][k] = dict(path=path, when=when, when_line=when_line, mtime=mtime(path), replies=rep,
                              set=[x for x in rep if x['kind'] == 'set'], get=[x for x in rep if x['kind'] == 'get'])
    fin = os.path.join(R, 'dimm7200-20261117', 'setting-final.txt')
    fl = fd._open(fin).read().splitlines()
    assert len(fl) == 1, fin
    out['final'] = dict(path=fin, mtime=mtime(fin), text=fl[0].strip(), answer=re.search(r'answer: "(.*)",', fl[0])[1])
    return out


def open_a2pre():
    """The run folder that ended 8 s before the first process of baseline A-2: its times and its processes."""
    folder = os.path.join(R, 'partA-20261113T204939Z')
    T = lambda s: fd.dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
    env_path = os.path.join(folder, 'env.txt')
    env = fd._open(env_path).read().splitlines()
    m = re.match(r'## host=\S+ utc=(\S+) loadavg=(\S+) .* steps=(.*)$', env[0])
    end = [(ln, re.match(r'## end utc=(\S+) loadavg=(\S+) ', l)) for ln, l in enumerate(env, 1) if l.startswith('## end utc=')]
    assert m and len(end) == 1 and end[0][1], env_path
    out = dict(folder=folder, env_path=env_path, start=T(m[1]), start_line=1, steps=m[3].split(),
               end=T(end[0][1][1]), end_line=end[0][0], load_end=float(end[0][1][2]), files={})
    hdr = []
    for n in ('A5.csv', 'A6.csv'):
        h = fd.step_headers(os.path.join(folder, n))
        out['files'][n] = dict(path=os.path.join(folder, n), n=len(h))
        hdr += h
    out['hdr'] = hdr
    out['threads'] = sorted({re.search(r'--threads (\S+)', h['args'])[1] for h in hdr})
    out['binaries'] = sorted({h['binary'] for h in hdr})
    out['first'], out['last'] = min(h['utc'] for h in hdr), max(h['utc'] for h in hdr)
    # launches.txt of that folder: one '== file tag' line per process
    lp = os.path.join(folder, 'launches.txt')
    ll = [l.split()[1] for l in fd._open(lp) if l.startswith('== ')]
    out['launches_path'], out['launches_n'], out['launches_files'] = lp, len(ll), sorted(set(ll))
    return out


def open_mod():
    """What a boot with 10 modules shows in the two lines that the sheet uses as proof of 12 modules:
    the saved journal and kernel log of the 10-module boot of 2026-11-17 04:17, and the module list that
    was saved in the boot of the rerun."""
    C = os.path.join(R, 'dimm-check-20261117')
    h1 = os.path.join(C, 'h-1.txt')
    hl = fd._open(h1).read().splitlines()
    out = dict(h1=h1, h1_start=fd.dt.datetime.strptime(hl[0][:19], '%Y-%m-%dT%H:%M:%S'),
               h1_dimm=int(re.search(r'This system has (\d+) DIMM sockets', hl[1])[1]), h1_dimm_line=2)
    for k in ('k-1.txt', 'k-5.txt'):
        path = os.path.join(C, k)
        kl = fd._open(path).read().splitlines()
        hit = [(ln, re.search(r'kernel: Memory: (\d+)K/(\d+)K available', l)) for ln, l in enumerate(kl, 1)
               if 'kernel: Memory: ' in l]
        assert len(hit) == 1 and hit[0][1], path
        out[k[:3]] = dict(path=path, line=hit[0][0], avail_K=int(hit[0][1][1]), total_K=int(hit[0][1][2]),
                          stamp=kl[hit[0][0] - 1][:15])
    dmi = os.path.join(R, 'dimm7200-20261117', 'dmi17-7200.txt')
    dl = fd._open(dmi).read().splitlines()
    out['dmi'] = dict(path=dmi, mtime=fd.dt.datetime.utcfromtimestamp(int(os.path.getmtime(dmi))),
                      devices=sum(1 for l in dl if l.strip() == 'Memory Device'),
                      speed=sum(1 for l in dl if l.strip() == 'Configured Memory Speed: 7200 MT/s'),
                      size=sum(1 for l in dl if l.strip() == 'Size: 32 GB'),
                      volatile=sum(1 for l in dl if l.strip() == 'Volatile Size: 32 GB'),
                      size_any=sum(1 for l in dl if 'Size: 32 GB' in l))
    t6 = fd._open(os.path.join(R, 'dimm7200-20261117', 'try6.txt')).read().splitlines()
    m = [(ln, re.fullmatch(r'modules=(\d+)', l)) for ln, l in enumerate(t6, 1) if l.startswith('modules=')]
    assert len(m) == 1 and m[0][1]
    out['try6_modules'], out['try6_modules_line'] = int(m[0][1][1]), m[0][0]
    return out


def open_probe13(kfolder):
    """probe.txt and one-thread.csv of the 2026-11-13 run: checksums, times, one-thread phase."""
    path = os.path.join(kfolder, 'probe.txt')
    lines = fd._open(path).read().splitlines()
    sha, sha_line = {}, {}
    for ln, l in enumerate(lines, 1):
        m = re.match(r'^([0-9a-f]{64})  (\S+)$', l)
        if m:
            sha[m[2]] = m[1]
            sha_line[m[2]] = ln
    T = lambda s: fd.dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
    out = dict(path=path, sha=sha, sha_line=sha_line)
    for ln, l in enumerate(lines, 1):
        m = re.match(r'## host=\S+ utc=(\S+) load_before=(\S+) (\S+) (\S+) logins=(\d+)', l)
        if m:
            out['utc'], out['load_before'], out['logins'] = T(m[1]), (m[2], m[3], m[4]), int(m[5])
        m = re.match(r'## one-thread done load=(\S+) \S+ \S+ utc=(\S+)', l)
        if m:
            out['one_done_load'], out['one_done_utc'], out['one_done_line'] = float(m[1]), T(m[2]), ln
        m = re.match(r'## load_after=(\S+) \S+ \S+ utc=(\S+)', l)
        if m:
            out['load_after'], out['utc_after'], out['after_line'] = float(m[1]), T(m[2]), ln
    out['has_memtotal'] = any('MemTotal' in l for l in lines)
    out['has_boot_id'] = any('boot_id' in l for l in lines)
    one = os.path.join(kfolder, 'one-thread.csv')
    hdr = [l for l in fd._open(one) if l.startswith('-- binary')]
    out['one_path'], out['one_n'] = one, len(hdr)
    out['one_first'] = re.search(r'utc (\S+)', hdr[0])[1]
    out['one_last'] = re.search(r'utc (\S+)', hdr[-1])[1]
    # journal of that boot (saved 2026-11-17): start, module line, error records during the run
    h5 = os.path.join(R, 'dimm-check-20261117', 'h-5.txt')
    hl = fd._open(h5).read().splitlines()
    out['h5'] = h5
    out['boot_start'] = fd.dt.datetime.strptime(hl[0][:19], '%Y-%m-%dT%H:%M:%S')
    out['boot_dimm'] = int(re.search(r'This system has (\d+) DIMM sockets', hl[1])[1])
    day = out['utc'].strftime('%Y-%m-%dT')
    first_rec = next(i for i, l in enumerate(hl, 1) if '[Hardware Error]' in l)
    out['first_record_line'] = first_rec
    out['first_record_utc'] = fd.dt.datetime.strptime(hl[first_rec - 1][:19], '%Y-%m-%dT%H:%M:%S')
    lo, hi = out['one_done_utc'], out['utc_after']
    out['records_in_120'] = sum(1 for l in hl if l.startswith(day) and '[Hardware Error]' in l
                                and lo <= fd.dt.datetime.strptime(l[:19], '%Y-%m-%dT%H:%M:%S') <= hi)
    # the same journal for the baselines A-2 and A-3 (one record = one line 'Hardware error from APEI ...')
    errs = fd.read_error_records(h5)
    pfolder = os.path.join(R, 'partA-20261113T205055Z')
    h1 = fd.step_headers(os.path.join(pfolder, 'A1.csv'))
    h2 = fd.step_headers(os.path.join(pfolder, 'A2.csv'))
    h3 = fd.step_headers(os.path.join(pfolder, 'A3.csv'))
    out['a2_csv2'] = os.path.join(pfolder, 'A2.csv')
    out['a2_window'] = (h1[0]['utc'], h2[0]['utc'])
    out['a2_first'] = h1[0]
    # The first A-3 process is the first process of A3.csv. run_partA.sh ran the steps in the order of
    # 'steps=' in env.txt, so the process directly before it is the last process of A2.csv.
    steps = re.search(r' steps=(.*)$', fd._open(os.path.join(pfolder, 'env.txt')).read().splitlines()[0])[1].split()
    assert steps.index('A2') + 1 == steps.index('A3') and h3[0]['line'] == 1 and h2[-1]['utc'] < h3[0]['utc']
    out['a3_prev'] = h2[-1]
    out['a3_first'] = h3[0]
    out['a2_records'] = []
    for e in errs:
        if out['a2_window'][0] <= e['utc'] <= out['a2_window'][1]:
            i = max(k for k, h in enumerate(h1) if h['utc'] <= e['utc'])
            out['a2_records'].append(dict(e, proc=h1[i], next=h1[i + 1] if i + 1 < len(h1) else None))
    i3 = [k for k, h in enumerate(h3) if re.fullmatch(r'onebuf-ms500-[123]', h['tag'])]
    out['a3_window'] = (h3[i3[0]]['utc'], h3[i3[-1] + 1]['utc'])
    out['a3_records'] = [e for e in errs if out['a3_window'][0] <= e['utc'] <= out['a3_window'][1]]
    out['n_records_boot'] = len(errs)
    out['journal_release'] = re.search(r'Linux version (\S+)', hl[0])[1]
    # machine settings saved in the same boot (2026-11-17 03:43 UTC, before the firmware test)
    pre = os.path.join(R, 'fwtest-20261117', 'pre')
    rd = lambda n: fd._open(os.path.join(pre, n)).read().strip()
    out['pre'] = dict(folder=pre, when_path=os.path.join(pre, 'when.txt'), cmdline_path=os.path.join(pre, 'cmdline.txt'),
                      gov_path=os.path.join(pre, 'gov.txt'), thp_path=os.path.join(pre, 'thp.txt'),
                      when=fd.dt.datetime.strptime(rd('when.txt'), '%a %b %d %I:%M:%S %p UTC %Y'),
                      cmdline=rd('cmdline.txt'), gov=[l.strip() for l in rd('gov.txt').splitlines()], thp=rd('thp.txt'))
    k5 = os.path.join(R, 'dimm-check-20261117', 'k-5.txt')
    kl = fd._open(k5).read().splitlines()
    out['k5'], out['k5_last_line'], out['k5_last'] = k5, len(kl), kl[-1][:15]
    q = os.path.join(R, 'uefisettings-20261117', 'questions.json')
    m = re.search(r'"name":"DIMM Frequency","answer":"(\d+) MT/s"', fd._open(q).read())
    out['q_path'], out['q_speed'] = q, int(m[1])
    return out


# ----------------------------------------------------------------------------- integrity checks

def run_checks(D):
    """Integrity checks. One line of text per check; the line names every folder that it covers."""
    C = D['checks']
    recs = D['recs']
    try6 = D['try6']
    A, X = D['A'], D['X']
    yn = lambda b: 'yes' if b else 'NO'

    def chk(key, ok, text):
        C.append(dict(key=key, ok=bool(ok), text=text))

    def per(items, fn):
        """'T72L1 10, T72L2 10, ...' for a list of rerun folders."""
        return ', '.join('%s %s' % (i['tag'], fn(i)) for i in items)

    # logs
    for name in ('go', 'go2'):
        lg = D['logs'][name]
        chk('log-' + name, lg['alldone'] and not lg['failed'],
            '%s: the last line is ALLDONE: %s. Lines that start with FAILED: %d'
            % (rel(lg['path']), yn(lg['lines'][-1] == 'ALLDONE'), len(lg['failed'])))
    # boot id and MemTotal of every state line and every probe.txt
    states = D['logs']['go']['states'] + D['logs']['go2']['states']
    boots = {s['boot'] for s in states} | {a['probe']['boot'] for a in A}
    mems = {s['memtotal_kB'] for s in states} | {a['probe']['memtotal_kB'] for a in A} | \
           {a['probe']['memtotal_after_kB'] for a in A}
    chk('boot', boots == {try6['boot']},
        'boot id: %d state lines of the two logs and %d probe.txt files hold %d distinct value(s). Equal to line 2 of '
        'try6.txt: %s' % (len(states), len(A), len(boots), yn(boots == {try6['boot']})))
    chk('memtotal', mems == {try6['memtotal_kB']},
        'MemTotal: %d state lines and %d probe.txt values (start and end of each session) hold %d distinct value(s): '
        '%s kB. Equal to line %d of try6.txt: %s'
        % (len(states), 2 * len(A), len(mems), ', '.join(str(m) for m in sorted(mems)), try6['memtotal_line'],
           yn(mems == {try6['memtotal_kB']})))
    ok = (all(s['logins'] == 0 and s['marker'] == 'absent' for s in states)
          and all(a['probe']['logins'] == 0 for a in A) and all(x['launches'][0]['logins'] == 0 for x in X))
    chk('logins', ok,
        'logins and marker file: logins = 0 and marker "absent" in %d of %d state lines. Logins = 0 in %d of %d '
        'probe.txt files and in %d of %d launch lines'
        % (sum(s['logins'] == 0 and s['marker'] == 'absent' for s in states), len(states),
           sum(a['probe']['logins'] == 0 for a in A), len(A),
           sum(x['launches'][0]['logins'] == 0 for x in X), len(X)))
    # part A: 24 processes x 3 intervals, same process order as on 2026-11-13
    order13 = [(p['binary'], p['kernel'], p['round']) for p in D['base']['A-1']['procs']]
    shape = lambda a: (len(a['procs']), sorted({len(p['iv']) for p in a['procs']}),
                       sorted({iv['threads'] for p in a['procs'] for iv in p['iv']}))
    ok = all(shape(a) == (24, [3], [120]) and all([iv['rep'] for iv in p['iv']] == [0, 1, 2] for p in a['procs'])
             for a in A)
    chk('A-shape', ok, 'part A, processes x intervals per threads120.csv (expected 24 x 3, 120 threads in every row): '
        + per(A, lambda a: '%d x %s, %d rows, threads %s' % (shape(a)[0], '/'.join(map(str, shape(a)[1])),
                                                              sum(len(p['iv']) for p in a['procs']),
                                                              '/'.join(map(str, shape(a)[2])))))
    same = lambda a: [(p['binary'], p['kernel'], p['round']) for p in a['procs']] == order13
    chk('A-order', all(same(a) for a in A),
        'part A, order of the 24 processes (binary, kernel, round) equal to threads120.csv of 2026-11-13: '
        + per(A, lambda a: yn(same(a))))
    # bwx12 folders of the rerun
    want_i = dict(L=10, I=10, C=6)
    chk('I-rows', all(len(x['sec']['I']) == want_i[x['part']] == len(x['ivs']) for x in X),
        '"I" rows per bwx12 csv (expected 10 for parts L and I, 6 for part C): ' + per(X, lambda x: len(x['sec']['I'])))
    chk('rc', all(len(x['launches']) == 1 and x['launches'][0]['rc'] == '0' for x in X),
        'launches.txt, one launch line with "rc 0" per folder: '
        + per(X, lambda x: 'rc ' + '/'.join(str(l['rc']) for l in x['launches'])))
    chk('stderr', all(x['stderr_bytes'] == 0 for x in X),
        'stderr.txt, bytes per folder (expected 0): ' + per(X, lambda x: x['stderr_bytes']))
    ok6456 = lambda x: sum(iv['is_64_56'] and iv['threads'] == 120 for iv in x['ivs'])
    chk('6456', all(ok6456(x) == len(x['ivs']) for x in X),
        'intervals with 120 threads = 64 on CPUs 0-63 + 56 on CPUs 64-119, on 120 different CPUs: '
        + per(X, lambda x: '%d of %d' % (ok6456(x), len(x['ivs']))))
    nflag = lambda x: sum(iv['flagged'] for iv in x['ivs'])
    D['n_T_rows'] = sum(iv['threads'] for x in X for iv in x['ivs'])
    vals = sorted({f for x in X for iv in x['ivs'] for f in iv['flags']})
    chk('flags', vals == ['-'],
        'flags column of the T rows (one row per thread and interval): %d rows in the 9 files, distinct values %s, '
        'rows that are not "-": %s' % (D['n_T_rows'], vals, per(X, nflag)))
    huge = lambda x: sum(1 for p in x['sec']['P'] if p[5] == p[4])
    tot = sorted({p[4] for x in X for p in x['sec']['P']})
    fb = sorted({p[7] for x in X for p in x['sec']['P']})
    D['P_kB'] = tot
    chk('P-rows', all(huge(x) == len(x['sec']['P']) > 0 for x in X),
        '"P" rows (one per thread before the first interval and after each interval): kB_total %s in all rows. Rows '
        'with kB_huge equal to kB_total: %s. Values of thp_fault_fallback: %s'
        % (tot, per(X, lambda x: '%d of %d' % (huge(x), len(x['sec']['P']))), fb))
    dmax = lambda x: max(abs(iv['total'] - iv['I_agg']) for iv in x['ivs'])
    agg_limit = 0.05        # GB/s; the pass limit of this check
    chk('I-agg', max(dmax(x) for x in X) < agg_limit,
        'total of the T rows against aggregate_GBps of the "I" row of the same interval, largest difference in GB/s '
        '(pass limit set by this script: below %.2f GB/s): ' % agg_limit + per(X, lambda x: '%.3f' % dmax(x)))
    # spec lines
    spec = {n: fd._open(os.path.join(S, n + '.spec')).read().strip().split('|', 1) for n in ('like', 'cfwd', 'crev')}
    okarg = lambda x: [x['launches'][0]['tag'], x['launches'][0]['args']] == spec[x['spec']]
    chk('args', all(okarg(x) for x in X),
        'tag and arguments of the launch line equal to the spec file: '
        + per(X, lambda x: '%s.spec %s' % (x['spec'], yn(okarg(x)))))
    r8 = D['rx']['L-1']['launches']['a6456']['args']
    f72 = D['rx']['F72d12']['launches']['a6456']['args']
    chk('args-R8', spec['like'][1] == r8 == f72,
        'argument line of like.spec equal to the a6456 launch line of L-1 (w120-R8) and of F72d12: %s'
        % yn(spec['like'][1] == r8 == f72))
    # checksums of the binaries
    p13 = D['probe13']
    ok = all(a['probe']['sha'][b] == p13['sha'][b] for a in A for b in ('bw_old', 'bw_new'))
    ok2 = all(re.search(r'^%s  %s$' % (p13['sha'][b], b), D['env_partA'], re.M) for b in ('bw_old', 'bw_new'))
    chk('sha-bw', ok and ok2,
        'sha256 of bw_old (%s...) and bw_new (%s...): the 3 probe.txt files of part A equal lines %d and %d of '
        'probe.txt of 2026-11-13: %s. env.txt of partA-20261113T205055Z holds the same two values: %s'
        % (p13['sha']['bw_old'][:8], p13['sha']['bw_new'][:8], p13['sha_line']['bw_old'], p13['sha_line']['bw_new'],
           yn(ok), yn(ok2)))
    ra = fd.sha256(os.path.join(S, 'ra.sh'))
    ok = all(a['probe']['sha']['ra.sh'] == ra for a in A)
    chk('sha-ra', ok, 'sha256 of ra.sh in the 3 probe.txt files equal to S/ra.sh (%s...): %s' % (ra[:8], yn(ok)))
    shas = {x['env']['sha'] for x in X}
    same12 = [n for n in ('L-1', 'L-2', 'L-3', 'L-4', 'X2d12', 'F72d12', 'X1d10', 'X1d10b', 'BASEd10')
              if D['rx'][n]['env']['sha'] in shas]
    go_sha = re.search(r'^SHA=([0-9a-f]{64})', fd._open(os.path.join(S, 'go.sh')).read(), re.M)[1]
    chk('sha-bwx12', len(shas) == 1 and len(same12) == 9 and {go_sha} == shas,
        'sha256 of bwx12 in env.txt: %d distinct value(s) in the %d folders of parts L, C, I (%s...). Equal to SHA= '
        'in go.sh: %s. The same value is in env.txt of %s'
        % (len(shas), len(X), sorted(shas)[0][:8], yn({go_sha} == shas), ', '.join(same12)))
    listed = {}
    for f in ('local.sha', 'go2.sha'):
        for l in fd._open(os.path.join(S, f)):
            h, n = l.split()
            listed[os.path.basename(n)] = h
    bad = [n for n, h in listed.items() if fd.sha256(os.path.join(S, n)) != h]
    chk('sha-local', not bad,
        'sha256 of the %d local run files (%s) equal to the lists local.sha and go2.sha: %s'
        % (len(listed), ', '.join(sorted(listed)), yn(not bad)))
    # Linux kernel release, runnable tasks
    rel_ = {a['probe']['kernel'] for a in A} | {x['env']['kernel'] for x in X}
    cmd_rel = re.search(r'vmlinuz-(\S+)', D['logs']['go']['other']['cmdline'][0])[1]
    chk('uname', rel_ == {cmd_rel},
        'Linux kernel release: %d distinct value(s) in the %d probe.txt and %d env.txt files. Equal to the image '
        'name of the command line: %s' % (len(rel_), len(A), len(X), yn(rel_ == {cmd_rel})))
    run_ = [x['launches'][0]['runnable'] for x in X] + [a['probe']['runnable'] for a in A]
    limit = int(re.search(r'\$r -le (\d+)', fd._open(os.path.join(S, 'ra.sh')).read())[1])
    rx_, ra_ = [x['launches'][0]['runnable'] for x in X], [a['probe']['runnable'] for a in A]
    sleep_ = int(re.search(r'^sleep (\d+)', fd._open(os.path.join(S, 'ra.sh')).read(), re.M)[1])
    span = lambda v: str(min(v)) if min(v) == max(v) else '%d to %d' % (min(v), max(v))
    chk('runnable', max(run_) <= limit,
        'runnable tasks: %s at the %d bwx12 launches (launch line of rx.sh). Part A: the value runnable=%s of the %d '
        'probe.txt files is the last value of the wait loop of ra.sh (ra.sh waits for %d or fewer). ra.sh reads it, '
        'then sleeps %d s, then writes the time and the load of the probe line. So the value is from at least %d s '
        'before the time of the probe line, and the count at the first launch of part A is not recorded'
        % (span(rx_), len(X), span(ra_), len(A), limit, sleep_, sleep_))
    # cross-check against the existing tools
    n_k, bad_k = 0, 0
    pairs = [(a['folder'], a['procs']) for a in A] + [
        (D['base']['A-1']['folder'], D['base']['A-1']['procs']),
        (os.path.join(S, 'base8000', 'partA-A1'), D['base']['A-2']['procs']),
        (os.path.join(S, 'base8000', 'partA-A3-onebuf500'), D['base']['A-3']['procs'])]
    for folder, mine in pairs:
        fd.OPENED.append(os.path.join(folder, 'threads120.csv'))
        theirs = fd.stat_k120.load(folder)
        assert len(theirs) == len(mine), folder
        for t, m in zip(theirs, mine):
            a = [(iv['agg'], iv['tmin'], iv['tmax'], iv['passes']) for iv in m['iv']]
            n_k += len(a)
            bad_k += a != [tuple(i) for i in t['iv']] or (t['binary'], t['kernel']) != (m['binary'], m['kernel'])
    chk('x-k120', bad_k == 0,
        'cross-check with stat_k120.py: %d interval rows (3 sessions of part A, A-1, and the copies of A-2 and A-3 '
        'under S/base8000, while this script reads the raw A1.csv and A3.csv) are equal in rate, per-thread minimum '
        'and maximum, and pass count: %s' % (n_k, yn(bad_k == 0)))
    n_x, bad_x, n_rerun = 0, 0, 0
    folders = [(x['folder'], {os.path.basename(x['csv'])[:-4]: x['sec']}) for x in X] + \
              [(v['folder'], v['secs']) for v in D['rx'].values()]
    for i, (folder, secs) in enumerate(folders):
        theirs = {(r['file'], r['round'], r['pos'], r['kernel']): r for r in fd.stat_bwx.interval_rows(folder)}
        for tag, sec in secs.items():
            for iv in fd.bwx_intervals(sec):
                t = theirs[(tag + '.csv', iv['round'], iv['pos'], iv['kernel'])]
                n_x += 1
                n_rerun += i < len(X)
                bad_x += (abs(t['total'] - iv['total']) > 1e-9 or abs(t['h0_sum'] - iv['mesh0']) > 1e-9
                          or abs(t['h1_sum'] - iv['mesh1']) > 1e-9 or t['is_64_56'] != iv['is_64_56']
                          or t['flagged'] != iv['flagged'])
    chk('x-bwx', bad_x == 0,
        'cross-check with stat_bwx.py: %d intervals of %d folders (the %d folders of parts L, C, I with %d intervals, '
        'and the %d csv files that section 7 lists from the %d earlier rx.sh and r0.sh folders with %d intervals) are '
        'equal in total, sum per mesh, the 64+56 test and the count of flagged rows: %s'
        % (n_x, len(folders), len(X), n_rerun, sum(len(v['secs']) for v in D['rx'].values()), len(D['rx']),
           n_x - n_rerun, yn(bad_x == 0)))
    # earlier intervals
    b = [r for r in recs if r['is_64_56'] is not None and r['dataset'] not in ('rerun-L', 'rerun-C', 'control-I')]
    okb = sum(1 for r in b if r['is_64_56'] and r['flagged'] == 0)
    errs = sum(v['stderr_bytes'] for v in D['rx'].values())
    rcs = sorted({v['launches'][t]['rc'] for v in D['rx'].values() for t in v['secs']})
    chk('earlier', okb == len(b) and errs == 0 and rcs == ['0'],
        'earlier bwx intervals used in sections 3 and 4: %d of %d are 64+56 intervals with 0 flagged T rows. The %d '
        'earlier rx.sh and r0.sh folders hold %d bytes of stderr.txt in total. The rc values of their %d processes used: %s'
        % (okb, len(b), len(D['rx']), errs, sum(len(v['secs']) for v in D['rx'].values()), '/'.join(rcs)))
    # rx.sh: the local copy against the checksum that go.sh and go2.sh test on CRB (added last, so that the
    # numbers of the checks above stay as they were)
    rx = fd.sha256(os.path.join(fd.W15, 'rx.sh'))
    scripts = {n: fd._open(os.path.join(S, n)).read() for n in ('go.sh', 'go2.sh')}
    rxsha = {n: re.search(r'^RXSHA=([0-9a-f]{64})$', t, re.M)[1] for n, t in scripts.items()}
    stop_msg = 'rx.sh is not the script of 2026-11-15'
    stop_line = 'echo "$RXSHA  $RX" | sha256sum -c - > /dev/null || fail "%s"' % stop_msg
    has_stop = all(stop_line in t and 'fail() { echo "FAILED: $1";' in t for t in scripts.values())
    n_failed = sum(len(D['logs'][n]['failed']) for n in ('go', 'go2'))
    # limit of this check: no record of the rerun holds a checksum of rx.sh, go.sh or go2.sh that was taken on CRB
    crb_texts = ['\n'.join(D['logs'][n]['lines']) for n in ('go', 'go2')] + \
                [fd._open(a['probe']['path']).read() for a in A] + \
                [fd._open(os.path.join(x['folder'], 'env.txt')).read() for x in X]
    local_sha = [rx] + [fd.sha256(os.path.join(S, n)) for n in ('go.sh', 'go2.sh')]
    assert not any(h in t for h in local_sha for t in crb_texts), 'a CRB record holds one of these checksums: revise the text'
    chk('sha-rx', set(rxsha.values()) == {rx} and has_stop and n_failed == 0,
        'sha256 of the local rx.sh (%s...) equal to RXSHA= in go.sh and go2.sh: %s. Both scripts hold the line that '
        'tests this value with sha256sum on CRB and stops with "FAILED: %s" when the copy on CRB differs: %s. Lines '
        'that start with FAILED in the two logs: %d. Limit: the %d logs, the %d probe.txt files and the %d env.txt '
        'files of the rerun hold no sha256 of rx.sh, go.sh or go2.sh. So this check uses the local copies of go.sh '
        'and go2.sh (check %d)'
        % (rx[:8], yn(set(rxsha.values()) == {rx}), stop_msg, yn(has_stop), n_failed, len(D['logs']), len(A), len(X),
           [c['key'] for c in C].index('sha-local') + 1))
    # arguments of part A against the test of 2026-11-13 (added after the checks above, so that their numbers stay)
    a1 = D['base']['A-1']['procs']
    hdr = lambda p: (p['binary'], p['kernel'], p['hdr_threads'], p['hdr_cpus'], p['hdr_bytes'], p['round'])
    n_all = sum(len(a['procs']) for a in A)
    n_same = sum(hdr(p) == hdr(q) for a in A if len(a['procs']) == len(a1) for p, q in zip(a['procs'], a1))
    every = [p for a in A for p in a['procs']] + a1
    hv = sorted({(p['hdr_threads'], p['hdr_cpus'], p['hdr_bytes']) for p in every})
    bw = sorted({p.get('bw_hdr') for p in every}, key=str)
    ra_lines = fd._open(os.path.join(S, 'ra.sh')).read().splitlines()
    rk_path = os.path.join(fd.K13, 'run_kernels.sh')
    rk_lines = fd._open(rk_path).read().splitlines()
    i_ra = next(i for i, l in enumerate(ra_lines) if l.startswith('one() {'))
    i_rk = next(i for i, l in enumerate(rk_lines) if l.startswith('one() {'))
    same_fn = ra_lines[i_ra:i_ra + 5] == rk_lines[i_rk:i_rk + 5] and ra_lines[i_ra + 4] == '}'
    opts = '--reps 3 --min-ms 500'
    has_opts = ra_lines[i_ra + 3].rstrip().endswith(opts + ' >> "$1"')
    rk_ok = p13['sha'].get('run_kernels.sh') == fd.sha256(rk_path)
    ok = n_same == n_all and len(hv) == 1 and len(bw) == 1 and bw[0] and same_fn and has_opts and rk_ok
    chk('A-args', ok,
        'part A, arguments. The "-- binary" header lines of the %d threads120.csv files of part A are equal to those '
        'of threads120.csv of 2026-11-13 in binary, kernel, threads, cpus, bytes and round: %d of %d lines (threads %s, '
        'cpus %s, bytes %s in every line). The header line that the binary prints ends with "%s" in all %d processes of '
        'the %d files. The function one() of ra.sh (lines %d to %d) is equal to lines %d to %d of run_kernels.sh: %s. '
        'Its process line ends with the options "%s": %s. sha256 of the local run_kernels.sh equal to line %d of '
        'probe.txt of 2026-11-13: %s'
        % (len(A), n_same, n_all, hv[0][0], hv[0][1], hv[0][2], bw[0], len(every), len(A) + 1, i_ra + 1, i_ra + 5,
           i_rk + 1, i_rk + 5, yn(same_fn), opts, yn(has_opts), p13['sha_line'].get('run_kernels.sh', 0), yn(rk_ok)))
    return C


# ----------------------------------------------------------------------------- facts.json

def write_json(D, V, path):
    recs = D['recs']
    try6 = D['try6']
    meta = dict(
        title='Facts of the whole-chip read rerun at 7200 MT/s, CRB, 2026-11-17',
        written_by='S/build_facts.py (with S/facts_data.py, S/facts_text.py and S/facts_text4.py)',
        R=R, S=S,
        units=dict(GBps='GB/s with GB = 1e9 bytes', load1_at_launch='1-minute load average of Linux at the launch of '
                   'the process', gap_s='seconds between the end of the previous 120-thread process of the rerun and '
                   'this launch (1 s resolution). bwx12 records: the launch of their process. Part A: set on the '
                   'first process of a session only; null for processes 2 to 24, which ra.sh starts directly after '
                   'the previous part A process with no wait', passes='part A only: total_bytes / bytes_per_thread of the '
                   'interval row. For read, asmread, write and asmwrite this is the number of buffer passes of all '
                   'threads in the interval. For copy and asmcopy (%d records) it is 2 x that number, because the '
                   'binary counts read plus written bytes for these two kernels: the header line of each of their '
                   'processes in the csv says "copy counts read+write bytes"'
                   % len(fd.sel(recs, part='A', kernel={'copy', 'asmcopy'})), min_ms='shortest length of one interval, milliseconds',
                   speed_MTps='memory speed, million transfers per second'),
        rate_kinds=dict(part_A=fd.KIND_A, bwx=fd.KIND_X + '. This file rounds it to 0.001 GB/s. FACTS.md formats the '
                        'unrounded value'),
        fields=dict(dataset='rerun-A, rerun-L, rerun-C, control-I, F72d12, or the label of an earlier row '
                    '(A-1..A-3, L-1..L-4, R0, R0b, X2d12, X1d10, X1d10b, BASEd10, B7a, B7b, C3a, C3b, B5a, B5b, '
                    'B5a-rev, B5b-rev)',
                    role='rerun, control, baseline, supporting, other binary, not a baseline, 10 modules',
                    round='part A: round of the script (1 or 2). In A-3 it is the repeat number. bwx: round of the '
                          'kernel sequence inside the process, from 0',
                    pos='bwx only: position of the kernel in the sequence of the process, from 0',
                    interval='number of the interval inside the process, from 0',
                    kernel_before='bwx: the kernel timed directly before in the same process. Part A: binary and '
                                  'kernel of the process that ran directly before in the same csv file. "none (first '
                                  'process of the file)" says nothing about the work before the file. Row A-3 holds 3 '
                                  'of the 12 processes of A3.csv: its first process is the first process of that file '
                                  '(the process directly before it is the last process of A2.csv: %s %s, tag %s, '
                                  'launched %s, arguments "%s"). Before each of the other two, a process ran that '
                                  'is not in the list ("not listed ...")'
                                  % (D['probe13']['a3_prev']['binary'], D['probe13']['a3_prev']['kernel'],
                                     D['probe13']['a3_prev']['tag'], iso(D['probe13']['a3_prev']['utc']),
                                     D['probe13']['a3_prev']['args']),
                    mesh0_GBps='bwx only: sum over the threads on CPUs 0-63',
                    mesh1_GBps='bwx only: sum over the threads on CPUs 64-127',
                    line='line number of the interval row in the file (part A) or of its "I" row (bwx)',
                    proc_key='one value per process',
                    session='rerun: session of go.sh (1 to 3); null for T72C4, which ran after session 3. '
                            'control-I: number of the control process (1 or 2); it is not a session',
                    start='bwx only: value of the option --start in the csv header (common or offset)',
                    start_state='start state of the step that holds the record: the session of part A, or the '
                                'bwx12 process. In part A it describes the first process of the session',
                    per_thread_avg_GBps='part A only: column per_thread_avg_GBps of the csv, rounded to 0.01 GB/s '
                                        'by the binary',
                    q2_rows='verdicts.q2_rows: row_7200 and scope_8000 are the keys of a row. They are kept as in '
                            'the earlier builds of this file, so that a tool can find a row. row_7200_label and '
                            'scope_8000_label are the labels that FACTS.md prints. Where a key says "not pooled", '
                            'the label says "own row": the row is its own row in every range test of rule V1 point '
                            '2. Where a key says "(after oldread)", the label adds that the 8000 MT/s rows hold '
                            'asmread at position 1 and part C holds it at position 0'),
        rerun=dict(boot_id=try6['boot'], modules=try6['dimm_sockets'], speed_MTps=try6['speed_MTps'],
                   memtotal_kB=try6['memtotal_kB'],
                   speed_proof='%s line %d, read at %s in the same boot. Not read during the rerun (no root)'
                               % (rel(try6['path']), try6['speed_line'], iso(try6['utc'])),
                   go_start=iso(D['logs']['go']['states'][0]['utc']), go_end=iso(D['logs']['go']['states'][-1]['utc']),
                   go2_start=iso(D['logs']['go2']['states'][0]['utc']), go2_end=iso(D['logs']['go2']['states'][-1]['utc']),
                   kernel_log_read=False, root_used=False),
        launches=[dict(tag=e['tag'], part=e['part'], session=e['session'], script_start=iso(e['start']),
                       first_launch=iso(e['first']), end=iso(e['end']), gap_s=e['gap_s'], load1_at_first_launch=e['load1'],
                       start_state=e['state']) for e in D['events']],
        checks=[dict(key=c['key'], ok=c['ok'], text=c['text']) for c in D['checks']],
        counts=dict(intervals=len(recs), by_dataset={k: len(fd.sel(recs, dataset=k))
                                                     for k in dict.fromkeys(r['dataset'] for r in recs)}),
        rules='S/baselines-and-rules.txt (fixed before the run)',
        control_note='control-I was added after the first numbers of parts A, L and C were seen. It is not part of '
                     'the plan fixed before the run',
        F72d12_boot=dict(
            note='the folder of F72d12 holds no boot id. Its process lies between two readings of the same boot id',
            process=[iso(D['rx']['F72d12']['launches']['a6456']['utc']), iso(D['rx']['F72d12']['launches']['a6456']['rc_utc'])],
            boot_id_before=dict(file=rel(try6['path']), line=try6['boot_line'], utc=iso(try6['utc'])),
            boot_id_after=dict(file=rel(GO_LOG), line=D['logs']['go']['states'][0]['line'],
                               utc=iso(D['logs']['go']['states'][0]['utc'])),
            boots_txt_row_0=dict(file=rel(try6['boots_path']), line=try6['boots_line'],
                                 first=iso(try6['boots_first']), last=iso(try6['boots_last'])),
            gaps_txt_row_0=dict(file=rel(try6['gaps_path']), line=try6['gaps_line'], first=iso(try6['first_log_utc']),
                                last=iso(try6['last_log_utc']), hwerr=try6['gaps_hwerr'])),
        hardware_error_records=dict(
            journal=rel(D['probe13']['h5']),
            note='records of the journal of the 2026-11-09 boot inside the window of each process (launch line to rc '
                 'line of launches.txt). One record = one line "Hardware error from APEI ...". offset_s = journal time '
                 'minus launch time; both have a resolution of 1 s. kind: "inside" = the span offset_s - 1 to '
                 'offset_s + 1 lies inside a used interval (oldread at position 0 or asmread at position 1), '
                 '"possible" = the span and a used interval share a part, "outside" = neither',
            processes=[dict(dataset=h['dataset'], tag=h['tag'], file=rel(h['file']), launch=iso(h['launch']['utc']),
                            rc=iso(h['launch']['rc_utc']), n_records=len(h['records']),
                            records=[dict(journal_line=e['line'], utc=iso(e['utc']), record=e['id'],
                                          severity=e['severity'], offset_s=e['offset_s'], kind=e['kind'],
                                          interval=None if e['interval'] is None else dict(
                                              kernel=e['interval']['kernel'], round=e['interval']['round'],
                                              pos=e['interval']['pos'], line=e['interval']['line'],
                                              t_start_s=round(e['interval']['t_start'], 3),
                                              t_end_s=round(e['interval']['t_end'], 3),
                                              GBps=r3(e['interval']['total'])))
                                     for e in h['records']]) for h in D['hw']],
            F72d12=dict(file=rel(try6['gaps_path']), line=try6['gaps_line'], hwerr=try6['gaps_hwerr'],
                        first=iso(try6['first_log_utc']), last=iso(try6['last_log_utc'])),
            rerun='Insufficient data: the kernel log was not read during or after the rerun (no root)',
            all_intervals=hw_compare_json(D['hw_cmp'])),
        firmware_settings=dict(
            note='no settings list was saved in the boot of the rerun (the settings tool needs root). File times are '
                 'those of the saved files. "line" of a reply is the line of the file that holds its answer',
            lists={k: dict(file=rel(v['path']), file_time=iso(v['mtime']), entries=v['n'], readable=v['readable'],
                           value_unavailable=v['unavailable'], vstore_error=v['store_error'], values=v['val']) for k, v in D['fw']['lists'].items()},
            base_and_revert_hold_the_same_entries=D['fw']['same_entries'],
            set_replies={k: dict(file=rel(v['path']), time_in_line_1=iso(v['when']) if v['when'] else None,
                                 file_time=iso(v['mtime']),
                                 replies=[dict(kind=x['kind'], name=x['name'], answer=x['answer'], modified=x['modified'],
                                               line=x['line']) for x in v['replies']])
                         for k, v in D['fw']['sets'].items()},
            last_reading=dict(file=rel(D['fw']['final']['path']), file_time=iso(D['fw']['final']['mtime']),
                              text=D['fw']['final']['text'])))
    # The file is written under another name and then renamed, so that a reader never sees a part of it.
    with open(path + '.tmp', 'w') as f:
        def r3all(o):
            if isinstance(o, float):
                return r3(o)
            if isinstance(o, dict):
                return {k: r3all(v) for k, v in o.items()}
            if isinstance(o, list):
                return [r3all(v) for v in o]
            return o
        f.write('{\n"meta": ' + json.dumps(meta, indent=1) + ',\n"verdicts": ' + json.dumps(r3all(V), indent=1)
                + ',\n"intervals": [\n')
        rounded = lambda r: {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
        f.write(',\n'.join(json.dumps(rounded(r), separators=(',', ':')) for r in recs))
        f.write('\n]\n}\n')
    os.replace(path + '.tmp', path)


def main():
    import facts_text
    D = collect()
    run_checks(D)
    V, text = facts_text.render(D)
    write_json(D, V, os.path.join(S, 'facts.json'))
    with open(os.path.join(S, 'FACTS.md.tmp'), 'w') as f:
        f.write(text)
    os.replace(os.path.join(S, 'FACTS.md.tmp'), os.path.join(S, 'FACTS.md'))
    if '--print' in sys.argv:
        print(text)
    bad = [c for c in D['checks'] if not c['ok']]
    print('checks: %d, failed: %d' % (len(D['checks']), len(bad)))
    for c in bad:
        print('  FAILED', c['key'], c['text'])
    print('intervals in facts.json: %d' % len(D['recs']))
    print('Q1:', V['q1'])
    print('Q2:', V['q2'])
    if bad:
        sys.exit(1)


if __name__ == '__main__':
    main()
