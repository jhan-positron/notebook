#!/usr/bin/env python3
"""facts_text4.py - sections 4, 5 and 6 of FACTS.md (7200 MT/s against 8000 MT/s, record-only tables, conclusions).

Used by facts_text.py. The templates hold words only; every number is formatted from the collected data.
"""
import os
import re

import facts_data as fd
from facts_data import R, sel, rng, overlap, gap, width_pct
from facts_text import (need, g, sp, pc, pcr, hm, hmd, dur, nn, nns, sess, table, compare, med, BW12, BW11, BWX, DIFFERS,
                        SAME, NO_READ, W15, ADDED, NOT_PLAN, H1_MEAS, FIRST, F2_NOTE, STANDIN, _q)

OWN = '(same boot, own row)'      # label of F72d12 and control I in the range tests of rule V1 point 2
OLD_OWN = '(same boot, not pooled)'   # the key of these rows in facts.json (kept from the earlier builds)


def secs(rs):
    """Interval length of a list of records, as text."""
    v = sorted({r['min_ms'] for r in rs})
    return ' and '.join('%g s' % (x / 1000) for x in v)


def section4(D, N, V, L, ref, q2row, c):
    recs = D['recs']
    w = L.append
    try6 = D['try6']
    rules = c['rules']
    evd = c['evd']
    pool = N['pool']
    cLo, cLa, cIo, cIa, cFo, cFa, cAo, cCo = (c[k] for k in ('cLo', 'cLa', 'cIo', 'cIa', 'cFo', 'cFa', 'cAo', 'cCo'))
    L72o, L72a, I72o, I72a, F72o, F72a = (c[k] for k in ('L72o', 'L72a', 'I72o', 'I72a', 'F72o', 'F72a'))
    P12o, P12a, PALLo, PALLa, A72o, A80o, C72o = (c[k] for k in ('P12o', 'P12a', 'PALLo', 'PALLa', 'A72o', 'A80o', 'C72o'))
    pa3, newread = c['pa3'], c['newread']
    C = sel(recs, dataset='rerun-C')
    first = FIRST
    CG = c['CG']
    f72la = D['rx']['F72d12']['launches']['a6456']
    fenv = D['rx']['F72d12']['env']
    f72dir = D['rx']['F72d12']['folder']
    S_ = os.path.dirname(rules)
    one_v = lambda rs: g(rs[0]['GBps']) if len(rs) == 1 else sp(rng(rs))      # a range, or the one value of one interval

    def src(rs):
        files = list(dict.fromkeys(os.path.join(R, r['folder'][2:], r['file']) for r in rs))
        return ' '.join(ref(f) for f in files)

    def ranges(rows):
        out = []
        for label, what, rs in rows:
            a = rng(rs)
            st = sorted({(r['speed_MTps'], r['modules']) for r in rs})
            need(len(st) == 1, 'one machine state per row: ' + label)
            out.append([label, what, '%d MT/s, %d modules' % st[0], nn(a, boots=False), sp(a), g(a['med']), src(rs)])
        return table(['Row', 'What it is', 'Memory speed, modules', 'n', 'Min to max, GB/s', 'Median, GB/s', 'Source'], out)

    def source(ds, rs):
        """Source cell of the row table: csv files, then where the load and the sha256 of the binary come from."""
        if ds in D['rx']:
            v = D['rx'][ds]
            sha = os.path.join(v['folder'], 'env.txt') if v['env']['has_binary_line'] else os.path.join(W15, 'r0.sh')
            return 'rates %s, load %s, sha256 %s' % (src(rs), ref(os.path.join(v['folder'], 'launches.txt')), ref(sha))
        if ds in D['step']:
            sha = os.path.join(D['step'][ds]['folder'], 'env.txt')
        elif ds == 'A-1':
            sha = D['probe13']['path']
        else:
            sha = os.path.join(D['base'][ds]['folder'], 'env.txt')
        return 'rates and load %s, sha256 %s' % (src(rs), ref(sha))

    def cmps(part, kernel, items, note='', notes=None):
        """items: (label of the 7200 MT/s row, records, [(label of the 8000 MT/s range, records, decides)]).
        A label may be a pair (key in facts.json, label in the table). The keys stay as they were in the earlier
        builds, because other tools find the rows of facts.json by them.
        note: text for the facts.json rows that carry a wording. notes: text per label for every row of that label."""
        out = []
        for label, r72, scopes in items:
            label, shown = label if isinstance(label, tuple) else (label, label)
            for scope, r80, decides in scopes:
                scope, scope_shown = scope if isinstance(scope, tuple) else (scope, scope)
                k = compare(r72, r80)
                q2row(part, kernel, label, scope, k, decides, (notes or {}).get(label, note if decides else ''),
                      row_label=shown, scope_label=scope_shown)
                out.append([shown, sp(k['a']), scope_shown, sp(k['b']), 'yes' if k['overlap'] else 'no',
                            '0' if k['overlap'] else '%+.2f' % k['dist'], pc(k['width']),
                            ('"%s"' % k['wording']) if decides else '-'])
        return table(['7200 MT/s row', 'Its range, GB/s', '8000 MT/s range used', 'That range, GB/s', 'Overlap',
                      'Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher)',
                      'Width of the 8000 MT/s range, % of its lower end (est. from one boot)',
                      'Wording by rule V1 point 2'], out)

    DESC = {
        'A-1': 'baseline: the test of 2026-11-13, same process order as part A',
        'A-2': 'baseline: same binaries and arguments, other process order',
        'A-3': 'baseline: bw_old read only, same arguments as A-2',
        'L-1': 'baseline: identical argument line',
        'L-2': 'supporting: bwx12, other counter events',
        'L-3': 'supporting: bwx12, other counter events',
        'L-4': 'supporting: bwx12, other counter events',
        'R0': 'other binary (bwx11)',
        'R0b': 'other binary (bwx11)',
        'X2d12': 'not a baseline (firmware test setting), shown and not used',
        'F72d12': 'sample of the same boot as the rerun, earlier visit (load %.2f at launch, %s after the first kernel '
                  'log line of the boot), kept as its own row in every range test of rule V1 point 2'
                  % (f72la['load1'], dur((f72la['utc'] - try6['first_log_utc']).total_seconds())),
        'B7a': 'other binary (bwx), tags common-6000-*',
        'B7b': 'other binary (bwx), tags common-6000-*',
        'C3a': 'other binary (bwx), tags common-6000-*',
        'C3b': 'other binary (bwx), tags common-6000-*',
        'B5a': 'other binary (bwx), tags b5-fwd-*',
        'B5b': 'other binary (bwx), tags b5-fwd-*',
        'B5a-rev': 'other binary (bwx), tags b5-rev-*, reverse kernel order, not in the list of rule V4, used only '
                   'for the highest values in section 4.6',
        'B5b-rev': 'other binary (bwx), tags b5-rev-*, reverse kernel order, not in the list of rule V4, used only '
                   'for the highest values in section 4.6',
        'X1d10': '10 modules, changed TXREQ firmware settings, used only for the text of rule V1 points 3 and 4',
        'X1d10b': '10 modules, the same changed TXREQ firmware settings, used only for the text of rule V1 points 3 and 4',
        'BASEd10': '10 modules, original firmware settings, used only for the text of rule V1 point 4',
    }

    # L-1 inside the tables of part C: its argument line is that of part L. The lines of part C differ in --seq.
    spec = {n: fd._open(os.path.join(S_, n + '.spec')).read().strip().split('|', 1)[1] for n in ('like', 'cfwd', 'crev')}
    noseq = lambda a: re.sub(r'--seq \S+', '--seq', a)
    need(len({noseq(a) for a in spec.values()}) == 1 and len(set(spec.values())) == 3
         and D['rx']['L-1']['launches']['a6456']['args'] == spec['like'],
         'the three spec lines differ in --seq only, and L-1 has the line of like.spec')
    L1C = 'baseline of part L: its argument line is that of like.spec. It differs from cfwd.spec and crev.spec in --seq'

    # =============================================================================== 4
    w('## 4. Q2: 7200 MT/s against 8000 MT/s')
    w('')
    w('### 4.1 The rules and the rows')
    w('')
    w('The rules were fixed before the run %s. In short:' % ref(rules))
    w('')
    w('- Rule V1 point 2: per part and kernel, compare the min-to-max range of the 7200 MT/s intervals with the '
      'min-to-max range of the like-for-like 8000 MT/s intervals. If the ranges do not overlap, write "%s". If they '
      'overlap, write "%s" and give the width of the 8000 MT/s range as the size that the test cannot exclude.' % (DIFFERS, SAME))
    w('- Rule V1 point 3: never give a percent change of the new read kernel (bw_new read, bwx12 read, asmread) as an '
      'effect of the memory speed.')
    w('- Rule V1 point 4: for the old read kernel a difference above about 1 % may be reported as a difference '
      'between the two boots.')
    w('- Rule V3: part A, load-only kernels: one row per process, session 1 against the 8000 MT/s processes of the '
      'same round, wording "inside" or "outside", no percent. Sessions 2 and 3 are used for Q1 only.')
    w('- Rule V2: part C is grouped by the kernel that ran directly before.')
    w('- Rules V4 and F2: the kernel `read` of part C has no bwx12 run at 8000 MT/s.')
    w('- The rules contradict each other on part C. Rule F2 points 2 and 3 would use part L only for bwx12 and would '
      'present part C at 7200 MT/s only. Rules V1 point 2, V2 point 4 and V4 ask for a comparison of part C with '
      '8000 MT/s. This sheet follows V1, V2 and V4 (decision (r) in section 2).')
    b80 = sorted({r['boot'] for r in recs if r['dataset'] in BW12 + BW11 + BWX + ('A-1', 'A-2', 'A-3', 'B5a', 'B5b')})
    b72 = sorted({r['boot'] for r in recs if r['speed_MTps'] == 7200})
    need(len(b80) == 1 and b72 == [try6['boot']], 'one boot per memory speed')
    w('- Each memory speed has exactly one boot. Every baseline row, supporting row and other-binary row at '
      '8000 MT/s comes from %s. Every 7200 MT/s row comes from boot %s. For the rerun the proof is in section 1.2. '
      'For row F72d12 it stands under the table below. The rows X2d12, X1d10, X1d10b and BASEd10 '
      'come from other boots. The table below names them.' % (b80[0], try6['boot'][:8]))
    gs = D['logs']['go']['states']
    w('- Label of the 7200 MT/s ranges of the rerun (rule V1 point 1): three sessions that ran within %s, all in '
      'boot %s. The rule text says "about 10 min (est.)". The value here is measured from the go.sh log.'
      % (dur((gs[-1]['utc'] - gs[0]['utc']).total_seconds()), try6['boot'][:8]))
    w('')
    w('Rows of earlier runs used in this section:')
    w('')
    rows = []
    for ds in ('A-1', 'A-2', 'A-3', 'L-1', 'L-2', 'L-3', 'L-4', 'R0', 'R0b', 'X2d12', 'F72d12', 'B7a', 'B7b', 'C3a',
               'C3b', 'B5a', 'B5b', 'B5a-rev', 'B5b-rev', 'X1d10', 'X1d10b', 'BASEd10'):
        rs = sel(recs, dataset=ds)
        procs = {}
        for r in rs:
            procs.setdefault(r['proc_key'], r)
        loads = [p['load1_at_launch'] for p in procs.values()]
        bins = sorted({'%s (%s)' % (r['binary'], r['binary_sha256'][:8]) for r in rs})
        files = list(dict.fromkeys(r['file'] for r in rs))
        tags = list(dict.fromkeys(r['tag'] for r in rs if r['tag']))
        where = '%s: %s' % (rs[0]['folder'], ', '.join(files))
        if ds in ('A-3', 'B7a', 'B7b', 'C3a', 'C3b', 'B5a', 'B5b', 'B5a-rev', 'B5b-rev'):
            where += ' (%d processes, tags %s to %s)' % (len(tags), tags[0], tags[-1])
        stop = sorted({'%s stop, %g s' % (r['stop'], r['min_ms'] / 1000) for r in rs})
        boot = rs[0]['boot'] if rs[0]['speed_MTps'] == 8000 else 'boot %s' % rs[0]['boot'][:8]
        srcs = source(ds, rs)
        if ds == 'F72d12':      # the folder holds no boot id: the proof stands under the table
            srcs += ', boot, modules and speed %s %s %s %s (proof under this table)' % (
                ref(try6['path']), ref(try6['gaps_path']), ref(try6['boots_path']), ref(D['logs']['go']['path']))
        rows.append([ds, DESC[ds], where, ', '.join(bins), ', '.join(stop),
                     '%d MT/s, %d modules, %s' % (rs[0]['speed_MTps'], rs[0]['modules'], boot),
                     ('%.2f' % loads[0]) if len(loads) == 1 else '%.2f to %.2f' % (min(loads), max(loads)),
                     '%d / %d' % (len(rs), len(procs)), srcs])
    L.extend(table(['Row', 'What it is', 'Folder and files', 'Binary (sha256, first 8 characters)', 'Stop rule, interval length',
                    'Memory speed, modules, boot', 'Load at launch (lowest to highest process)',
                    'Interval records in facts.json / processes', 'Source'], rows))
    w('- Column "Source": the csv files hold the rates. For the rows written by rx.sh or r0.sh the load is in '
      'launches.txt and the sha256 is in env.txt. For row R0 env.txt holds no sha256 %s, and the value comes from line %d '
      'of r0.sh %s. For the other rows the load is in the header lines of the csv file, and the sha256 is in probe.txt '
      'or env.txt of the run folder.'
      % (ref(os.path.join(D['rx']['R0']['folder'], 'env.txt')), D['rx']['R0']['env']['sha_line'], ref(os.path.join(W15, 'r0.sh'))))
    dimm_txt = fd._open(fd.DIMM_REPORT).read()
    x10 = {d: [r['GBps'] for r in sel(recs, dataset=d, kernel='oldread')] for d in ('X1d10', 'X1d10b', 'BASEd10')}
    need('Three more runs with changed TXREQ settings' in dimm_txt
         and all('%.1f / %.1f' % tuple(x10[d]) in dimm_txt for d in ('X1d10', 'X1d10b', 'BASEd10'))
         and 'One changed settings state gave 10 modules in two boots' in dimm_txt,
         'DIMM report: X1d10 and X1d10b are the runs with changed TXREQ settings, BASEd10 has the original settings')
    w('- Firmware settings of the 10-module rows: the DIMM report gives the old read values of X1d10 and X1d10b as '
      'runs with changed TXREQ settings, and those of BASEd10 as the run with the original settings (its sections '
      '6.1 and 6.2 %s). TXREQ is a group of firmware settings that were changed for another investigation.'
      % ref(fd.DIMM_REPORT))
    w('- The boot numbers are those of the boot history in the DIMM report %s.' % ref(fd.DIMM_REPORT))
    w('- From rows L-2 to L-4, R0 and R0b this sheet uses oldread at position 0 and asmread at position 1 only.')
    w('- The speed of the 2026-11-09 boot rests on the firmware setting, not on a reading of the applied speed '
      '(section 1.5, point 10).')
    fwx = c['fw']
    w('- Firmware settings of the two boots: section 1.5, point 13. In short: the two TXREQ settings were set back on '
      '%s. The settings list saved after that is equal to the list of the baseline boot in all %d readable values. '
      'No settings list exists from the boot of the rerun.' % (hmd(fwx['set_back']), fwx['readable']))
    # F72d12: its folder holds no boot id. Its process lies between two readings of the boot id of the rerun.
    f72env_txt = fd._open(os.path.join(f72dir, 'env.txt')).read()
    go0 = D['logs']['go']['states'][0]
    need(not re.search(r'boot|MemTotal|MT/s', f72env_txt) and fenv['n_lines'] == len(f72env_txt.splitlines()),
         'env.txt of F72d12 holds no boot id, no MemTotal and no memory speed')
    need(try6['utc'] < f72la['utc'] < f72la['rc_utc'] < go0['utc'] and go0['boot'] == try6['boot']
         and try6['boots_first'] <= f72la['utc'] and f72la['rc_utc'] <= try6['boots_last']
         and try6['first_log_utc'] <= f72la['utc'] and f72la['rc_utc'] <= try6['last_log_utc'],
         'the F72d12 process lies between two readings of the same boot id and inside row 0 of boots.txt and gaps.txt')
    w('- Boot, module count and speed of row F72d12. Its folder holds no boot id, no MemTotal and no memory speed: '
      'env.txt has %d lines with the date, the Linux release, the load, the process list and the binary %s. Its '
      'process ran from %s to %s %s. Line 1 of try6.txt holds the time %s, %.0f s before that launch. The file holds the boot id `%s` '
      '(line %d), MemTotal %d kB (line %d), "This system has %d DIMM sockets" (line %d) and "%d Configured Memory '
      'Speed: %d MT/s" (line %d) %s. The go.sh log holds the same boot id at %s (line %d) %s. Linux creates a boot id '
      'once per start (see the word list). So Linux was not started again between these two readings, and the F72d12 '
      'process ran in the boot of the rerun. Two more records fit this. Row 0 of boots.txt holds the same boot id '
      'with the times %s and %s (line %d) %s. Row 0 of gaps.txt spans %s to %s (line %d) %s. Limit, as for the rerun: '
      'the speed and the module count were not read during the process.'
      % (fenv['n_lines'], ref(os.path.join(f72dir, 'env.txt')), hm(f72la['utc']), hm(f72la['rc_utc']),
         ref(os.path.join(f72dir, 'launches.txt')), hm(try6['utc']), (f72la['utc'] - try6['utc']).total_seconds(),
         try6['boot'], try6['boot_line'], try6['memtotal_kB'], try6['memtotal_line'], try6['dimm_sockets'],
         try6['dimm_line'], try6['speed_count'], try6['speed_MTps'], try6['speed_line'], ref(try6['path']),
         hm(go0['utc']), go0['line'], ref(D['logs']['go']['path']), hm(try6['boots_first']), hm(try6['boots_last']),
         try6['boots_line'], ref(try6['boots_path']), hm(try6['first_log_utc']), hm(try6['last_log_utc']),
         try6['gaps_line'], ref(try6['gaps_path'])))
    w('')

    # ---- hardware error records during the bwx12 and bwx11 rows of the 2026-11-09 boot
    hw = D['hw']
    p13 = D['probe13']
    allrec = [e for h in hw for e in h['records']]
    need(allrec and {e['severity'] for e in allrec} == {'corrected'}, 'the records in the process windows are all "corrected"')
    w('Hardware error records during the bwx12 and bwx11 rows of the 2026-11-09 boot (rows L-1 to L-4, R0, R0b):')
    w('')
    w('- The journal is the one of section 1.5, point 8 %s. One record is one line "Hardware error from APEI ..." of '
      'the journal.' % ref(p13['h5']))
    w('- The window of a process is the time from its launch line to its rc line in launches.txt. rx.sh and r0.sh '
      'write the launch line directly before they start the process %s %s. In a table cell " / " separates the '
      'records of different seconds.'
      % (ref(os.path.join(W15, 'rx.sh')), ref(os.path.join(W15, 'r0.sh'))))
    w('- Time resolution. The journal and launches.txt give whole seconds. So a record that the journal dates N seconds '
      'after the launch line lies between N - 1 and N + 1 seconds after the process start (est.). The csv file gives '
      'the start and the end of every interval in seconds since the process start (T rows, columns t_start_s and '
      't_end_s). The journal time is the time of the log line. The time of the hardware event itself is not on record.')
    w('- The table below tests only the intervals that this sheet uses: oldread at position 0 and asmread at position 1. '
      'The second table of this block lists the intervals of all kernels and positions.')
    w('')

    def kind_txt(e):
        iv = e['interval']
        if e['kind'] == 'outside':
            return 'outside'
        span = '%s, round %d (%s s to %s s after the process start, I row in line %d)' % (
            iv['kernel'], iv['round'], g(iv['t_start']), g(iv['t_end']), iv['line'])
        if e['kind'] == 'inside':
            return 'inside ' + span
        need(e['offset_s'] - 1 < iv['t_start'], 'a record that may lie inside an interval lies at its start')
        return 'before or inside ' + span
    rows = []
    for h in hw:
        la = h['launch']
        by_t = {}
        for e in h['records']:
            by_t.setdefault(e['utc'], []).append(e)
        need(all(len({kind_txt(e) for e in es}) == 1 for es in by_t.values()), 'the records of one second have one position')
        groups = sorted(by_t.items())
        rows.append([h['dataset'], h['tag'], hmd(la['utc']), hmd(la['rc_utc']), len(h['records']),
                     ' / '.join('%s: %s' % (hmd(t), ', '.join(str(e['line']) for e in es)) for t, es in groups) or '-',
                     ' / '.join('%.0f' % es[0]['offset_s'] for t, es in groups) or '-',
                     ' / '.join(kind_txt(es[0]) for t, es in groups) or '-',
                     '%s %s' % (ref(os.path.join(h['folder'], 'launches.txt')), ref(h['file']))])
    L.extend(table(['Row', 'Process', 'Launch line', 'rc line', 'Records in the window',
                    'Journal time: journal lines of the records', 'Seconds after the launch line',
                    'Position against the intervals used', 'Source'], rows))
    ins = [(h, e) for h in hw for e in h['records'] if e['kind'] == 'inside']
    pos = [(h, e) for h in hw for e in h['records'] if e['kind'] == 'possible']
    n_out = sum(1 for e in allrec if e['kind'] == 'outside')
    need(len(ins) == 2 and ins[0][1]['interval'] is ins[1][1]['interval'] and ins[0][1]['utc'] == ins[1][1]['utc'],
         'two records of one second lie inside one used interval')
    need(len(pos) == 2 and pos[0][1]['interval'] is pos[1][1]['interval'] and pos[0][1]['utc'] == pos[1][1]['utc'],
         'two records of one second may lie inside one used interval')
    (hi_, ei), (hp, ep) = ins[0], pos[0]
    ivi, ivp = ei['interval'], ep['interval']
    low_a = min(P12a, key=lambda r: r['GBps'])
    need((ivi['kernel'], ivi['pos']) == ('asmread', 1) and hi_['dataset'] in BW12
         and (low_a['dataset'], low_a['tag'], low_a['line']) == (hi_['dataset'], hi_['tag'], ivi['line']),
         'the interval with records inside it is the lowest asmread interval of the pool L-1 to L-4')
    need((ivp['kernel'], ivp['pos'], ivp['round']) == ('oldread', 0, 0) and hp['dataset'] == 'L-1',
         'the interval that may hold records is oldread, round 0 of L-1')
    P12a_wo = [r for r in P12a if r is not low_a]
    c['hw'] = dict(inside=(hi_, ei), possible=(hp, ep), n_out=n_out, P12a_wo=P12a_wo, low_a=low_a)
    w('- All %d records in these windows have the severity "corrected".' % len(allrec))
    w('- Row %s: the %d records at %s (journal lines %s) are %.0f s after the launch line. %s, round %d was timed from '
      '%s s to %s s after the process start (T rows in lines %d to %d %s). So the records fall before this interval or '
      'inside it. The interval gave %s GB/s.'
      % (hp['dataset'], len(pos), hmd(ep['utc']), ' and '.join(str(e['line']) for _, e in pos), ep['offset_s'],
         ivp['kernel'], ivp['round'], g(ivp['t_start']), g(ivp['t_end']), ivp['T_first'], ivp['T_last'], ref(hp['file']),
         g(ivp['total'])))
    w('- Row %s, process %s: the %d records at %s (journal lines %s) are %.0f s after the launch line. %s, round %d '
      'was timed from %s s to %s s after the process start (T rows in lines %d to %d, I row in line %d %s). So the '
      'records fall inside this interval. It gave %s GB/s, the lowest asmread value of the pool L-1 to L-4 '
      '(section 4.4).'
      % (hi_['dataset'], hi_['tag'], len(ins), hmd(ei['utc']), ' and '.join(str(e['line']) for _, e in ins),
         ei['offset_s'], ivi['kernel'], ivi['round'], g(ivi['t_start']), g(ivi['t_end']), ivi['T_first'], ivi['T_last'],
         ivi['line'], ref(hi_['file']), g(ivi['total'])))
    w('- The other %d records of these windows fall outside the intervals that this sheet uses.' % n_out)
    w('- Processes with 0 records in their window: %s.'
      % ', '.join('%s %s' % (h['dataset'], h['tag']) for h in hw if not h['records']))
    need(try6['gaps_hwerr'] == 0 and try6['gaps_dimm'] == try6['dimm_sockets'], 'row 0 of gaps.txt: hwerr=0, 12 modules')
    w('- F72d12: line %d of gaps.txt shows "hwerr=%d" for row 0, with the kernel log times %s to %s %s. Row 0 of '
      'boots.txt holds the boot id of the rerun %s. The F72d12 process ran from %s to %s %s. By its name the field '
      'counts hardware error records. The script that wrote gaps.txt is not among the files of this task. So its '
      'count rule was not checked.'
      % (try6['gaps_line'], try6['gaps_hwerr'], hm(try6['first_log_utc']), hm(try6['last_log_utc']),
         ref(try6['gaps_path']), ref(try6['boots_path']), hm(f72la['utc']), hm(f72la['rc_utc']),
         ref(os.path.join(f72dir, 'launches.txt'))))
    w('- Rerun (parts A, L and C, control I): Insufficient data. The kernel log was not read (section 1.5, point 8).')
    w('- Not counted in this sheet: the records during the rows of runner bwx (B7a to B5b-rev) and during the rows of '
      'other boots (X2d12, X1d10, X1d10b, BASEd10). No wording by rule V1 point 2 rests on these rows. For the rows '
      'of runner bwx the same journal and the T rows of their csv files would give the count.')
    # ---- the hypothesis on corrected records. The csv files hold more than one interval with records: every interval
    # (all kernels and positions) of these processes with a record, against the same kernel at the same position in
    # the other round of the same process (build_facts.hw_compare).
    hc = D['hw_cmp']
    crow, cbor, ccl = hc['rows'], hc['border'], hc['clean']
    sg = lambda x: '0.00' if float(g(x)) == 0 else (g(x) if x < 0 else '+' + g(x))      # a signed difference
    need(not any(r['other_has_records'] for r in crow)
         and not any(x['other_has_records'] for b in cbor for x in b['intervals']),
         'no other-round interval of the comparison has a record inside it or at its border')
    rp = [r for r in crow if r['iv'] is ivp]
    ri = [r for r in crow if r['iv'] is ivi]
    more = [r for r in crow if not r['used']]
    need(len(rp) == 1 and len(ri) == 1 and len(more) + 2 == len(crow) and rp[0]['where'] == 'before or inside'
         and all(r['where'] == 'inside' for r in crow if r is not rp[0]),
         'the two used intervals with records are in the comparison; every other interval has its records inside it')
    rp, ri = rp[0], ri[0]
    n_more, n_bor = sum(len(r['records']) for r in more), sum(len(b['records']) for b in cbor)
    need(n_more + n_bor == n_out and len(crow) > 2 and cbor and all(len(b['intervals']) == 2 for b in cbor),
         'the records outside the used intervals lie inside other intervals or at the border of two intervals')
    LIM = 1.0       # GB/s: a difference between the two rounds above this value is counted as a difference
    low = sorted((r for r in crow if r['diff'] < -LIM), key=lambda r: r['diff'])
    rest = [r for r in crow if not r['diff'] < -LIM]
    cbig = [x for x in ccl if abs(x['diff']) > LIM]
    cmax = max(ccl, key=lambda x: abs(x['diff']))
    low_in = [r for r in low if abs(r['diff']) < abs(cmax['diff'])]
    need(low and low[0] is ri and rest and all(abs(r['diff']) < LIM for r in rest) and any(r is rp for r in rest)
         and rp['diff'] > 0 and min(r['diff'] for r in rest) < 0,
         'intervals with records: some lie more than 1 GB/s below their other round, the others differ by less than '
         '1 GB/s, and oldread of L-1 is higher with records')
    need(len(low) - len(low_in) == 1 and low_in and abs(ri['diff']) > abs(cmax['diff']) and cbig,
         'only the asmread interval of p2add differs by more than the largest difference between two rounds without records')
    need((cmax['dataset'], cmax['tag'], cmax['pos']) == (hi_['dataset'], hi_['tag'], ivi['pos'] + 1) and cmax['diff'] < 0
         and ivi['round'] == 1,
         'the largest difference without records is at the position directly after the asmread interval with records, '
         'lower in the round of the records')
    need({(x['dataset'], x['tag']) for x in ccl} == {(r['dataset'], r['tag']) for r in crow},
         'the positions without records are counted in the processes of the table')
    bdiff = [x['diff'] for b in cbor for x in b['intervals']]
    c['hw']['cmp'] = dict(n=len(crow), low=low, rest=rest, cmax=cmax, n_clean=len(ccl), n_big=len(cbig), lim=LIM)
    c['hw']['cmp']['lst'] = lambda xs: xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]
    w('- Hypothesis, not tested: a corrected record lowers the rate of the interval in which it falls. The files on '
      'hand hold more than one interval with records. The table below lists every interval of the processes above, '
      'of all kernels and positions, to which records can be assigned: the records fall inside it, or before or '
      'inside it. This view was added after the numbers were seen. It is not part of the fixed rules.')
    w('')
    w('Intervals with records, all kernels and positions (rows L-1 to L-4, R0, R0b). "Other round" is the interval of '
      'the same kernel at the same position in the other round of the same process. No other-round interval of this '
      'table has a record inside it or at its border. The position of the records follows the rule of the table '
      'above (1 s resolution, est.). A difference is computed from the values before rounding (first lines of this '
      'sheet).')
    w('')
    L.extend(table(['Row', 'Process', 'Interval with records', 'I row line', 'Journal lines of the records',
                    'Position of the records', 'Rate, GB/s', 'Other round: rate, GB/s (I row line)',
                    'With records minus other round, GB/s', 'Used by this sheet', 'Source'],
                   [[r['dataset'], r['tag'], '%s, round %d, position %d' % (r['iv']['kernel'], r['iv']['round'], r['iv']['pos']),
                     r['iv']['line'], ', '.join(str(e['line']) for e in r['records']), r['where'], g(r['iv']['total']),
                     '%s (%d)' % (g(r['other']['total']), r['other']['line']), sg(r['diff']),
                     'yes' if r['used'] else 'no', '%s %s' % (ref(r['file']), ref(p13['h5']))] for r in crow]))
    # the loop names of this block that the word list does not define (the names come from the csv files)
    in_words = {'oldread', 'asmread', 'read', 'read_nop96', 'read_nop256', 'read_1pl'}
    loops = ({r['iv']['kernel'] for r in crow} | {x['iv']['kernel'] for b in cbor for x in b['intervals']} | {cmax['kernel']}) - in_words
    loops = sorted(loops, key=lambda k: (re.sub(r'\d+$', '', k), int(re.search(r'\d*$', k).group(0) or 0)))     # by stem, then by number
    with open(os.path.join(W15, 'FINDINGS.md'), encoding='utf-8') as fh:
        f2 = re.search(r'^## F2\..*?(?=^## )', fh.read(), re.S | re.M)          # its section F2, up to the next heading
    need(loops and f2 and all(re.search(r'\b%s\b' % re.escape(k), f2.group(0)) for k in loops)
         and {r['dataset'] for r in crow} | {b['dataset'] for b in cbor} | {cmax['dataset']} <= set(BW12) | set(BW11),
         'the other loop names of the comparison are named in section F2 of FINDINGS.md, and their rows are rows of bwx12 and bwx11')
    w('%s are other test loops of bwx12 and bwx11. FINDINGS.md names them in its section F2 %s.'
      % (c['hw']['cmp']['lst'](loops), ref(os.path.join(W15, 'FINDINGS.md'))))
    w('')
    btxt = ['%d record%s of %s %s, %.0f s after the launch line (journal line%s %s), between %s of round %d'
            % (len(b['records']), '' if len(b['records']) == 1 else 's', b['dataset'], b['tag'], b['records'][0]['offset_s'],
               '' if len(b['records']) == 1 else 's', ' and '.join(str(e['line']) for e in b['records']),
               ' and '.join(x['iv']['kernel'] for x in b['intervals']), b['intervals'][0]['iv']['round']) for b in cbor]
    need(all(len({x['iv']['round'] for x in b['intervals']}) == 1
             and b['intervals'][1]['iv']['pos'] == b['intervals'][0]['iv']['pos'] + 1 for b in cbor),
         'a border lies between two neighbour intervals of one round')
    lst = lambda xs: xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]
    w('- Of the %d records outside the used intervals, %d fall inside the %d intervals of this table that the sheet '
      'does not use. The other %d lie at the border of two intervals. The 1 s resolution cannot assign them to one '
      'interval: %s. These %d intervals differ from their other round by %s to %s GB/s. They are not in the table.'
      % (n_out, n_more, len(more), n_bor, ', and '.join(btxt), sum(len(b['intervals']) for b in cbor),
         sg(min(bdiff)), sg(max(bdiff))))
    w('- What fits: %d of the %d intervals of the table are more than %g GB/s below their other round (%s GB/s). The '
      'largest difference belongs to the asmread interval of %s (%s GB/s), the lowest asmread value of the pool L-1 to '
      'L-4. No interval of the table is more than %g GB/s above its other round.'
      % (len(low), len(crow), LIM, lst([g(-r['diff']) for r in reversed(low)]), ri['tag'], g(ivi['total']), LIM))
    w('- What does not fit: the other %d intervals differ from their other round by less than %g GB/s (%s to %s GB/s). '
      'One of them is %s, round %d of row %s. It gave %s GB/s with records before or inside it. Round %d, without '
      'records, gave %s GB/s.'
      % (len(rest), LIM, sg(min(r['diff'] for r in rest)), sg(max(r['diff'] for r in rest)), ivp['kernel'], ivp['round'],
         rp['dataset'], g(ivp['total']), rp['other']['round'], g(rp['other']['total'])))
    w('- Limit: the two rounds of a process differ without records too. These %d processes have %d positions at '
      'which neither round has a record inside it or at its border. At %d of them the two rounds differ by more than '
      '%g GB/s. The largest difference is %s GB/s (%s of %s, lower in round %d, directly after the asmread interval '
      'with records). So %d of the %d lower intervals of the table (%s GB/s) are within the differences seen without '
      'records, and 1 (%s GB/s) is above them.'
      % (len({(r['dataset'], r['tag']) for r in crow}), len(ccl), len(cbig), LIM, g(abs(cmax['diff'])), cmax['kernel'],
         cmax['tag'], ivi['round'], len(low_in), len(low), ' and '.join(g(-r['diff']) for r in reversed(low_in)),
         g(-ri['diff'])))
    w('- This comparison is not a test of the hypothesis. Each interval has one other round to compare with. The '
      'comparison was chosen after the numbers were seen.')
    w('- Measurement that would confirm or reject it: a run that stores the kernel log time of every record beside the '
      'interval times, at both memory speeds (reading the kernel log needs root). More data are on hand and were not '
      'compared here: the records during the rows of runner bwx (see "Not counted in this sheet" above).')
    w('')

    # ---- 4.2 old read
    w('### 4.2 Old read kernel')
    w('')
    w('**Part A, bw_old read.**')
    w('')
    a1o, a2o, a3o = (sel(recs, dataset=d, binary='bw_old', kernel='read') for d in ('A-1', 'A-2', 'A-3'))
    L.extend(ranges([('part A, sessions 1 to 3', 'rerun (one row per process is in section 3.1)', A72o),
                     ('A-1', DESC['A-1'], a1o), ('A-2', DESC['A-2'], a2o), ('A-3', DESC['A-3'], a3o),
                     ('pool A-1 to A-3', 'all like-for-like 8000 MT/s intervals of bw_old read', A80o)]))
    L.extend(cmps('A', 'bw_old read', [('part A, sessions 1 to 3', A72o, [
        ('A-1', a1o, False), ('A-2', a2o, False), ('A-3', a3o, False), ('pool A-1 to A-3', A80o, True)])]))
    b80 = rng(A80o)
    outs = []
    for p in N['pa']:
        a = rng(p['old'])
        if a['lo'] > b80['hi']:
            outs.append('The process of session %d, round %d (%s GB/s) lies above it.' % (p['session'], p['round'], sp(a)))
        elif a['hi'] < b80['lo']:
            outs.append('The process of session %d, round %d (%s GB/s) lies below it.' % (p['session'], p['round'], sp(a)))
    w('- Wording by rule V1 point 2: "%s". n at 7200 MT/s: %s. n at 8000 MT/s: %s.'
      % (cAo['wording'], nn(cAo['a'], sessions=True), nn(cAo['b'])))
    w('- The test cannot exclude a difference of about %s %% (est. from one boot). That is the width of the 8000 MT/s '
      'range.' % pc(cAo['width']))
    if outs:
        w('- The 7200 MT/s range is wider than the 8000 MT/s range. %s The other %d processes overlap it.'
          % (' '.join(outs), len(N['pa']) - len(outs)))
    w('')

    w('**Part L, oldread (position 0, the first interval of each round).**')
    w('')
    lrows = lambda k, pos: [(d, DESC[d], sel(recs, dataset=d, kernel=k, pos=pos)) for d in BW12]
    orows = lambda k, pos: [(d, DESC[d], sel(recs, dataset=d, kernel=k, pos=pos)) for d in BW11]
    x2o, x2a = sel(recs, dataset='X2d12', kernel='oldread'), sel(recs, dataset='X2d12', kernel='asmread')
    sL = 'rerun, each process started %s' % evd['T72L1']['state'].replace('started ', '').replace(' (T72A1)', ' of its session')
    sI = 'control, %s, idle start' % ADDED
    L.extend(ranges([('part L (T72L1 to T72L3)', sL, L72o)] + lrows('oldread', 0)
                    + [('pool L-1 to L-4', 'all bwx12 rows of the fixed list', P12o)] + orows('oldread', 0)
                    + [('pool L-1 to L-4, R0, R0b', 'bwx12 rows and other-binary rows', PALLo),
                       ('X2d12', DESC['X2d12'], x2o), ('F72d12', DESC['F72d12'], F72o), ('control I (T72I1, T72I2)', sI, I72o)]))
    l1o, l1a = sel(recs, dataset='L-1', kernel='oldread'), sel(recs, dataset='L-1', kernel='asmread')
    sc_o = [('L-1 alone', l1o, False), ('pool L-1 to L-4', P12o, True), ('pool L-1 to L-4, R0, R0b', PALLo, False)]
    sc_a = [('L-1 alone', l1a, False), ('pool L-1 to L-4', P12a, True), ('pool L-1 to L-4, R0, R0b', PALLa, False)]
    L.extend(cmps('L', 'oldread', [('part L', L72o, sc_o), (('F72d12 ' + OLD_OWN, 'F72d12 ' + OWN), F72o, sc_o),
                                    (('control I ' + OLD_OWN, 'control I ' + OWN), I72o, sc_o)]))
    kLo1 = compare(L72o, l1o)
    need(not kLo1['overlap'] and not compare(L72o, PALLo)['overlap'], 'part L oldread below every 8000 MT/s scope')
    w('- Part L, wording by rule V1 point 2: "%s". Part L is lower. n at 7200 MT/s: %s. n at 8000 MT/s: %s.'
      % (cLo['wording'], nn(cLo['a'], sessions=True), nn(cLo['b'])))
    near, far, mid = -cLo['dist'], cLo['b']['hi'] - cLo['a']['lo'], cLo['b']['med'] - cLo['a']['med']
    c['oldL'] = dict(near=near, mid=mid, near_pct=near / cLo['b']['lo'] * 100, mid_pct=mid / cLo['b']['med'] * 100)
    need(c['oldL']['near_pct'] < 1 < c['oldL']['mid_pct'], 'old read, part L: nearest ends below 1 %, medians above 1 %')
    w('- Size against the pool L-1 to L-4: the nearest ends are %s GB/s apart (%s %% of the lower end of the '
      '8000 MT/s range, %s GB/s). The medians are %s GB/s apart (%s %% of the 8000 MT/s median, %s GB/s). The '
      'farthest ends are %s GB/s apart (%s %% of the same lower end). The 8000 MT/s range itself is %s %% wide.'
      % (g(near), pc(c['oldL']['near_pct']), g(cLo['b']['lo']), g(mid), pc(c['oldL']['mid_pct']), g(cLo['b']['med']),
         g(far), pc(far / cLo['b']['lo'] * 100), pc(cLo['width'])))
    w('- Rule V1 point 4 allows a report as "a difference between the two boots" above about 1 %. The rule does not '
      'say which distance counts. The distance of the nearest ends is below 1 %, and the distance of the medians is '
      'above 1 %.')
    w('- F72d12 and control I are runs of the same line in the same 7200 MT/s boot. Both were launched at a 1-minute '
      'load average below 1.0. Section 4.6 gives the differences of their start states. Control I was %s. Both '
      'overlap the 8000 MT/s range (%s and %s GB/s against %s GB/s).' % (ADDED, sp(cFo['a']), sp(cIo['a']), sp(cFo['b'])))
    hp, ep = c['hw']['possible']
    need(not any(e['kind'] != 'outside' and e['interval']['kernel'] == 'oldread' and e['interval'] is not ep['interval']
                 for h in D['hw'] for e in h['records']), 'no other oldread interval with a record in or near it')
    # the same for the oldread intervals at other positions (row R0 holds oldread at two positions)
    need(not any(iv['kernel'] == 'oldread' and iv is not ep['interval']
                 for h in D['hw'] for e in h['records'] for _, iv in e['every']),
         'no other oldread interval at any position with a record in or near it')
    w('- Hardware error records (section 4.1): 2 corrected records fall before or inside oldread, round %d of row %s '
      '(%s GB/s). No other oldread interval of the rows L-1 to L-4, R0 and R0b has a record inside it. For the rerun '
      'the records are not known.' % (ep['interval']['round'], hp['dataset'], g(ep['interval']['total'])))
    need(cCo['overlap'], 'part C oldread overlaps the pool')
    w('- So against the whole pool L-1 to L-4, only the range of part L lies below the 8000 MT/s range among the '
      'bwx12 runs at 7200 MT/s. Part L started %s. The view below splits the pool by start state. In that view part C '
      'lies below the bwx12 processes of the pool that started after 120-thread work too. Against the other-binary '
      'processes with that kind of start state part C overlaps (limit in the view). The data do not show that the '
      'boot or the memory speed is the cause: each memory speed has one boot.'
      % evd['T72L1']['state'].replace('started ', '').replace(' (T72A1)', ''))
    w('')

    # ---- view: the 8000 MT/s pool split by the start state of the process (added after the numbers were seen)
    allla = [la for d in BW12 for la in D['rx'][d]['launches'].values()]
    st = {}
    for d in BW12:
        v = D['rx'][d]
        for tag in v['secs']:
            la = v['launches'][tag]
            before = sorted((l for l in allla if l['rc_utc'] is not None and l['rc_utc'] <= la['utc']), key=lambda l: l['rc_utc'])
            prev = before[-1] if before else None
            st[(d, tag)] = dict(la=la, prev=prev, gap=(la['utc'] - prev['rc_utc']).total_seconds() if prev else None,
                                first=min(v['launches'].values(), key=lambda l: l['utc']) is la, folder=v['folder'])
    idle = [k for k in st if st[k]['la']['load1'] < 1.0]
    busy = [k for k in st if st[k]['la']['load1'] >= 1.0]
    need(idle and busy and all(st[k]['first'] for k in idle), 'the processes below load 1.0 are the first of their run folder')
    need(all(' --threads 120 ' in ' ' + st[k]['prev']['args'] + ' ' and '--cpus 0-63,64-119' in st[k]['prev']['args']
             and 0 < st[k]['gap'] <= 30 for k in busy),
         'every other process of the pool started at most 30 s after a 120-thread bwx12 process')
    grp = lambda keys, k, pos: [r for r in sel(recs, dataset=set(BW12), kernel=k, pos=pos) if (r['dataset'], r['tag']) in keys]
    Io, Ia, Bo, Ba = grp(idle, 'oldread', 0), grp(idle, 'asmread', 1), grp(busy, 'oldread', 0), grp(busy, 'asmread', 1)
    need(len(Io) + len(Bo) == len(P12o) and len(Ia) + len(Ba) == len(P12a), 'the two groups hold the whole pool')
    gaps_ = sorted(st[k]['gap'] for k in busy)
    loads = lambda keys: sorted(st[k]['la']['load1'] for k in keys)
    names = lambda keys: ', '.join('%s %s' % k for k in keys)
    lsrc = lambda keys: ' '.join(dict.fromkeys(ref(os.path.join(st[k]['folder'], 'launches.txt')) for k in keys))
    w('The pool L-1 to L-4 split by the start state of the process. This view was looked at after the numbers were '
      'seen. It is not part of the fixed rules.')
    w('')
    L.extend(table(['8000 MT/s group', 'Processes', 'Load at launch', 'Work before the launch', 'n', 'oldread, GB/s',
                    'asmread, GB/s', 'Source'], [
        ['started at a load below 1.0', names(idle), ' and '.join(dict.fromkeys('%.2f' % x for x in loads(idle))),
         'first process of its run folder', nn(rng(Io)), sp(rng(Io)), sp(rng(Ia)), 'rates %s, launch lines %s' % (src(Io), lsrc(idle))],
        ['started after 120-thread work', names(busy), '%.2f to %.2f' % (loads(busy)[0], loads(busy)[-1]),
         'a 120-thread bwx12 process had ended %.0f s to %.0f s before' % (gaps_[0], gaps_[-1]), nn(rng(Bo)), sp(rng(Bo)),
         sp(rng(Ba)), 'rates %s, launch lines %s' % (src(Bo), lsrc(busy))]]))
    aIo, aBo, aIa, aBa = rng(Io), rng(Bo), rng(Ia), rng(Ba)
    need(aBo['lo'] > aIo['hi'], '8000 MT/s: oldread after 120-thread work above oldread from a load below 1.0')
    need(overlap(aIa, aBa), '8000 MT/s: the two asmread groups overlap')
    kLB, kLaB = compare(L72o, Bo), compare(L72a, Ba)
    need(not kLB['overlap'] and kLB['dist'] < 0 and not kLaB['overlap'] and kLaB['dist'] > 0,
         'part L: oldread below and asmread above the 8000 MT/s group that started after 120-thread work')
    need(overlap(rng(F72o), aIo) and overlap(rng(I72o), aIo), 'F72d12 and control I overlap the 8000 MT/s group below load 1.0')
    c['byst'] = dict(Io=aIo, Bo=aBo, Ia=aIa, Ba=aBa, idle=idle, busy=busy, gaps=gaps_, loads_busy=loads(busy),
                     near=-kLB['dist'], near_pct=-kLB['dist'] / aBo['lo'] * 100, asm_near=kLaB['dist'], names=names)
    # part C in this view: its processes started after a 120-thread bwx12 process, like the second 8000 MT/s group
    Ctags = list(dict.fromkeys(r['tag'] for r in C72o))
    Cprev = [evd[t]['prev'] for t in Ctags]
    need(all(p_ is not None and p_['part'] in ('L', 'C') for p_ in Cprev)
         and all(0 < evd[t]['gap_s'] <= 30 for t in Ctags) and len({evd[t]['gap_s'] for t in Ctags}) == 1,
         'every part C process started at most 30 s after a 120-thread bwx12 process of the rerun, all after the same gap')
    Cf0 = sel(C72o, pos=0)
    Cf0tags = list(dict.fromkeys(r['tag'] for r in Cf0))
    need({r['kernel_before'] for r in sel(C72o, pos=2)} == {'read'} and len(Cf0) + len(sel(C72o, pos=2)) == len(C72o)
         and {next(x['spec'] for x in D['X'] if x['tag'] == t) for t in Cf0tags} == {'cfwd'},
         'oldread of part C: position 0 in cfwd, position 2 directly after read in crev')
    kCB, kCfB, kCIo = compare(C72o, Bo), compare(Cf0, Bo), compare(C72o, Io)
    need(not kCB['overlap'] and kCB['dist'] < 0 and not kCfB['overlap'] and kCfB['dist'] < 0 and kCIo['overlap'],
         'part C oldread: below the 8000 MT/s group that started after 120-thread work, overlap with the other group')
    Cload = sorted(evd[t]['load1'] for t in Ctags)
    c['partC_view'] = dict(all=kCB['a'], cf0=kCfB['a'], near=-kCB['dist'], near_pct=-kCB['dist'] / aBo['lo'] * 100,
                           near_cf0=-kCfB['dist'], gap=evd[Ctags[0]]['gap_s'], prev=[p_['tag'] for p_ in Cprev],
                           loads=Cload, both=rng(L72o + C72o))
    # the same kind of start state outside the pool: rows of bwx11 and of runner bwx (other binaries)
    alla11 = [la for d in BW11 for la in D['rx'][d]['launches'].values()]
    busy11 = []
    for d in BW11:
        v = D['rx'][d]
        for tag in v['secs']:
            la = v['launches'][tag]
            before = sorted((l for l in alla11 if l['rc_utc'] is not None and l['rc_utc'] <= la['utc']), key=lambda l: l['rc_utc'])
            prev = before[-1] if before else None
            if (prev and ' --threads 120 ' in ' ' + prev['args'] + ' ' and '--cpus 0-63,64-119' in prev['args']
                    and 0 < (la['utc'] - prev['rc_utc']).total_seconds() <= 30):
                busy11.append(dict(key=(d, tag), gap=(la['utc'] - prev['rc_utc']).total_seconds(), load=la['load1'],
                                   folder=v['folder']))
    B11o = [r for r in sel(recs, dataset=set(BW11), kernel='oldread', pos=0)
            if (r['dataset'], r['tag']) in {b['key'] for b in busy11}]
    bx0v = sel(recs, dataset=set(BWX), kernel='oldread', pos=0)
    prev120 = [s_['prev_step'] for n in BWX for s_ in D['step'][n]['secs']]
    need(busy11 and len(prev120) == rng(bx0v)['procs']
         and all(p_ is not None and ' --threads 120 ' in ' ' + p_['args'] + ' ' and p_['binary'] == 'bwx' for p_ in prev120),
         'every used process of runner bwx follows a 120-thread step of runner bwx in its csv file')
    aB11, aBx0 = rng(B11o), rng(bx0v)
    allo = sel(recs, speed_MTps=8000, modules=12, kernel='oldread')
    low_o = min(allo, key=lambda r: r['GBps'])
    need(overlap(rng(C72o), aB11) and overlap(rng(C72o), aBx0), 'part C oldread overlaps the other-binary rows of that start state')
    need(rng(L72o)['hi'] < low_o['GBps'] and {r['binary'] for r in allo} == {'bwx12', 'bwx11', 'bwx'},
         'part L oldread below every oldread interval at 8000 MT/s with 12 modules')
    c['byst_other'] = dict(b11=aB11, bx0=aBx0, busy11=busy11, low_o=low_o, n_allo=len(allo),
                           bx0_load=[min(r['load1_at_launch'] for r in bx0v), max(r['load1_at_launch'] for r in bx0v)])
    c['byst']['L_hi'] = rng(L72o)['hi']
    w('- oldread at 8000 MT/s: the %d processes of the pool that started after 120-thread work gave the %d highest '
      'values of the pool (%s GB/s). The %d processes that started at a load below 1.0 gave %s GB/s. The two groups do '
      'not overlap.' % (aBo['procs'], aBo['n'], sp(aBo), aIo['procs'], sp(aIo)))
    w('- Part L started %.0f s after part A. Against the group that started after 120-thread work, oldread of part L '
      '(%s GB/s) is lower by %s GB/s at the nearest ends (%s %% of %s GB/s). Against the whole pool this distance is '
      '%s GB/s.' % (evd['T72L1']['gap_s'], sp(cLo['a']), g(c['byst']['near']), pc(c['byst']['near_pct']), g(aBo['lo']), g(near)))
    pcv = c['partC_view']
    w('- Part C in this view. All %d part C processes started %.0f s after a 120-thread bwx12 process of the rerun '
      '(%s), at a load of %.2f to %.2f (sections 1.1 and 1.3). That is the kind of start state of the second '
      '8000 MT/s group (a 120-thread bwx12 process ended %.0f s to %.0f s before, load %.2f to %.2f). '
      'oldread of part C (%s GB/s, %s) lies below this group (%s GB/s, %s). The two ranges do not overlap. Part C is '
      'lower by %s GB/s at the nearest ends (%s %% of %s GB/s). Like the two wordings for part C, this comparison '
      'follows decision (r) in section 2.'
      % (len(Ctags), pcv['gap'], ', '.join(pcv['prev']), Cload[0], Cload[-1], gaps_[0], gaps_[-1], loads(busy)[0],
         loads(busy)[-1], sp(pcv['all']), nn(pcv['all']), sp(aBo),
         nn(aBo), g(pcv['near']), _q(pcv['near_pct'], '0.01'), g(aBo['lo'])))
    w('- The second group holds oldread at position 0 only. The position-matched intervals of part C are those of '
      'cfwd at position 0 (%s, load %s at launch): %s GB/s (%s). They are lower by %s GB/s at the nearest ends.'
      % (' and '.join(Cf0tags), ' and '.join('%.2f' % evd[t]['load1'] for t in Cf0tags), sp(pcv['cf0']),
         nn(pcv['cf0'], boots=False), g(pcv['near_cf0'])))
    w('- Against the group that started at a load below 1.0 (%s GB/s), oldread of part C overlaps.' % sp(aIo))
    w('- So in this view both 7200 MT/s parts that started after 120-thread work lie below the %d bwx12 processes of '
      'the pool L-1 to L-4 that started after 120-thread work (%s against %s, no overlap). For part C this holds '
      'against these %d processes only (see the limit below). The wording by rule V1 point 2 for part C '
      'does not change. It compares part C with the whole pool.'
      % (aBo['procs'], nn(pcv['both'], boots=False), nn(aBo, boots=False), aBo['procs']))
    w('- The rows that were launched at a load below 1.0 overlap. At 7200 MT/s F72d12 gave %s GB/s and control I (%s) '
      'gave %s GB/s. At 8000 MT/s the group gave %s GB/s.' % (sp(cFo['a']), ADDED, sp(cIo['a']), sp(aIo)))
    w('- asmread: part L (%s GB/s) lies %s GB/s above the group that started after 120-thread work (%s GB/s). The two '
      '8000 MT/s groups overlap for asmread.' % (sp(cLa['a']), g(kLaB['dist']), sp(aBa)))
    w('- So the 8000 MT/s rows do not show a lower oldread rate after 120-thread work. They show a higher one.')
    l11 = sorted(b['load'] for b in busy11)
    g11 = sorted({b['gap'] for b in busy11})
    lbx = sorted(r['load1_at_launch'] for r in bx0v)
    w('- Limit of the part C result in this view. The second group holds the %d bwx12 processes of the pool only. They '
      'are not all 8000 MT/s processes with that kind of start state. The other-binary rows hold more of them, and '
      'against these part C overlaps. %d bwx11 processes (%s) were launched %s s after a 120-thread bwx11 process, at '
      'a load of %.2f to %.2f. They gave oldread %s GB/s at position 0 (%s) %s, launch lines %s. The %d processes of '
      'runner bwx (rows %s) each follow a 120-thread process of runner bwx in their csv file. Their load at launch '
      'was %.2f to %.2f. They gave %s GB/s at position 0 (%s) %s. The highest oldread value of part C is %s GB/s.'
      % (aBo['procs'], len(busy11), ', '.join('%s %s' % b['key'] for b in busy11), ' or '.join('%.0f' % x for x in g11),
         l11[0], l11[-1], sp(aB11), nn(aB11, boots=False), src(B11o),
         ' '.join(dict.fromkeys(ref(os.path.join(b['folder'], 'launches.txt')) for b in busy11)), aBx0['procs'],
         ', '.join(BWX), lbx[0], lbx[-1], sp(aBx0), nn(aBx0, boots=False), src(bx0v), g(rng(C72o)['hi'])))
    w('- The part L result does not depend on this choice. The highest oldread value of part L (%s GB/s) is below '
      'every oldread interval at 8000 MT/s with 12 modules that this sheet holds (%d intervals of the binaries bwx12, '
      'bwx11 and bwx). The lowest of them is %s GB/s (row %s, process %s).'
      % (g(rng(L72o)['hi']), len(allo), g(low_o['GBps']), low_o['dataset'], low_o['tag']))
    w('- Limits of this view. For part L the work before the launch differs between the two speeds: part A (bw_old '
      'and bw_new) at 7200 MT/s, a bwx12 process at 8000 MT/s. For part C it is a bwx12 process at both speeds. The '
      'second group has intervals of %s and other counter events (rows L-2 to L-4). %d of the %d oldread intervals of '
      'part C are at position 2, directly after read. Each memory speed has one boot.'
      % (secs(Bo), len(sel(C72o, pos=2)), len(C72o)))
    w('- Insufficient data: why old read was lower in part L. ' + H1_MEAS)
    w('')

    w('**Part C, oldread.**')
    w('')
    Cf = sel(C, kernel='oldread', pos=0)
    Cr = sel(C, kernel='oldread', pos=2)
    bx0 = sel(recs, dataset=set(BWX), kernel='oldread', pos=0)
    bx7 = sel(recs, dataset=set(BWX), kernel='oldread', pos=7)
    scm = lambda rs: [r for r in rs if r['start'] == 'common']       # the processes of runner bwx with --start common
    need({r['start'] for r in C} == {'common'}, 'part C used --start common')
    nsc = rng(scm(bx0))['procs']
    L.extend(ranges([('part C, all oldread intervals', 'rerun, cfwd and crev', C72o),
                     ('part C, cfwd, position 0', 'first interval of each round', Cf),
                     ('part C, crev, position 2', 'directly after read', Cr),
                     ('L-1 alone', L1C + '. oldread at position 0', l1o),
                     ('pool L-1 to L-4', 'bwx12 rows, oldread at position 0', P12o),
                     ('pool L-1 to L-4, R0, R0b', 'bwx12 rows and other-binary rows, oldread at position 0', PALLo),
                     ('pool B7a, B7b, C3a, C3b, position 0', 'other binary (bwx), oldread at position 0', bx0),
                     ('the same, only the %d processes with --start common' % nsc, 'other binary (bwx), oldread at position 0', scm(bx0)),
                     ('pool B7a, B7b, C3a, C3b, position 7', 'other binary (bwx), oldread directly after read', bx7),
                     ('the same, only the %d processes with --start common' % nsc, 'other binary (bwx), oldread directly after read', scm(bx7))]))
    kC1, kCall = compare(C72o, l1o), compare(C72o, PALLo)
    L.extend(cmps('C', 'oldread', [
        ('part C, all oldread intervals', C72o, [('L-1 alone (position 0)', l1o, False),
                                                 ('pool L-1 to L-4 (position 0)', P12o, True),
                                                 ('pool L-1 to L-4, R0, R0b (position 0)', PALLo, False)]),
        ('part C, cfwd, position 0', Cf, [('pool L-1 to L-4 (position 0)', P12o, False),
                                          ('other binary bwx, position 0', bx0, False)]),
        ('part C, crev, position 2', Cr, [('other binary bwx, position 7 (after read)', bx7, False)])], F2_NOTE))
    w('- Wording by rule V1 point 2: "%s". n at 7200 MT/s: %s. n at 8000 MT/s: %s. %s'
      % (cCo['wording'], nns(C72o), nn(cCo['b']), F2_NOTE))
    w('- The test cannot exclude a difference of about %s %% (est. from one boot). That is the width of the 8000 MT/s '
      'range (%s GB/s).' % (pc(cCo['width']), sp(cCo['b'])))
    need(kC1['overlap'] and kCall['overlap'], 'part C oldread overlaps L-1 alone and the pool with the other-binary rows')
    w('- The ranges also overlap against L-1 alone and against the pool with the other-binary rows.')
    lowC = [r for r in C72o if r['GBps'] < cCo['b']['lo']]
    w('- %d of the %d intervals of part C lie below the lowest value of the pool%s.'
      % (len(lowC), len(C72o), (' (%s)' % ', '.join(dict.fromkeys(r['tag'] for r in lowC))) if lowC else ''))
    w('- In the view by start state above (added after the numbers were seen), all %d intervals of part C lie below '
      'the %d bwx12 processes of the pool L-1 to L-4 that started after 120-thread work (%s GB/s), by %s GB/s at the '
      'nearest ends. Against the other-binary processes with that kind of start state part C overlaps (limit in '
      'that view).'
      % (len(C72o), aBo['procs'], sp(aBo), g(pcv['near'])))
    w('- Only oldread at position 0 (cfwd) has a position-matched bwx12 baseline (rule V4). The rows of runner bwx '
      'are another binary. They are shown for the position after read.')
    w('')

    # ---- 4.3 new read, part A
    w('### 4.3 New read kernel in part A (rule V3)')
    w('')
    w('- Session 1 is compared with the 8000 MT/s processes of the same round in rows A-1 and A-2. bw_old asmread '
      'has a process in row A-1 only.')
    w('- A cell shows the three intervals in GB/s and, in brackets, their pass counts.')
    w('- No percent is given here (rules V3 and V1 point 3).')
    w('')
    rows = []
    cellt = lambda rs: ', '.join('%s (%d)' % (g(r['GBps']), r['passes']) for r in rs) if rs else 'no process in this row'
    for x in pa3:
        if x['inside'] == 3:
            word, dist = 'inside the range of the 8000 MT/s runs; no difference shown', '-'
        elif len(x['above']) == 3:
            word, dist = 'outside (above)', '%s to %s' % (g(min(x['above'])), g(max(x['above'])))
        elif len(x['below']) == 3:
            word, dist = 'outside (below)', '%s to %s' % (g(min(x['below'])), g(max(x['below'])))
        else:
            word = '%d of 3 intervals inside, %d above, %d below' % (x['inside'], len(x['above']), len(x['below']))
            dist = ', '.join(g(v) for v in x['above'] + x['below'])
        x['word'], x['dist_txt'] = word, dist
        rows.append(['%s %s' % (x['binary'], x['kernel']), x['round'], cellt(x['s1']), cellt(x['a1']), cellt(x['a2']),
                     sp(x['b80']), word, dist])
        V['q2_rows'].append(dict(part='A', kernel='%s %s' % (x['binary'], x['kernel']), row_7200='session 1, round %d' % x['round'],
                                 lo_7200=min(r['GBps'] for r in x['s1']), hi_7200=max(r['GBps'] for r in x['s1']), n_7200=3,
                                 processes_7200=1,
                                 scope_8000='%s, round %d' % (' and '.join(n for n, a in (('A-1', x['a1']), ('A-2', x['a2'])) if a),
                                                              x['round']), lo_8000=x['b80']['lo'],
                                 hi_8000=x['b80']['hi'], n_8000=x['b80']['n'], processes_8000=x['b80']['procs'],
                                 overlap=x['inside'] > 0, distance_GBps=round(min(x['above'] or [0]), 3), wording=word,
                                 decides=True, note='rule V3: inside or outside the 8000 MT/s range of the same round'))
        V['q2_rows'][-1].update(row_7200_label=V['q2_rows'][-1]['row_7200'], scope_8000_label=V['q2_rows'][-1]['scope_8000'])
    L.extend(table(['Binary and kernel', 'Round', '7200 MT/s, session 1', '8000 MT/s, A-1, same round',
                    '8000 MT/s, A-2, same round', '8000 MT/s range of the round, GB/s', 'Wording by rule V3',
                    'Distance to the nearer end of the range, GB/s'], rows))
    need(all(len(x['above']) == 3 for x in pa3), 'session 1 of every load-only cell above the 8000 MT/s range of its round')
    w('- All %d load-only cells of session 1 lie above the 8000 MT/s range of their round.' % len(pa3))
    s1new = sel(recs, dataset='rerun-A', session=1, binary='bw_new', kernel='read')
    a1n, a2n = sel(recs, dataset='A-1', binary='bw_new', kernel='read'), sel(recs, dataset='A-2', binary='bw_new', kernel='read')
    need(nn(rng(a1n)) == nn(rng(a2n)) and {r['round'] for r in a1n} == {r['round'] for r in a2n} ==
         {r['round'] for r in s1new} == {1, 2}, 'the three medians of bw_new read: the same n, rounds 1 and 2 together')
    w('- Rule V4 point 3 for bw_new read: the two 8000 MT/s medians are %s GB/s (A-1) and %s GB/s (A-2), %s GB/s '
      'apart. Each is the median of %s, rounds 1 and 2 taken together. The median of session 1 is %s GB/s (%s, rounds '
      '1 and 2 taken together). It is %s GB/s above A-1 and %s GB/s above A-2. Both distances are larger than the '
      'distance between the two baselines. The tables of this section keep the two rounds apart. These three medians '
      'take them together. Rule V4 point 3 quotes the two 8000 MT/s medians in this form %s.'
      % (g(med(a1n)), g(med(a2n)), g(abs(med(a2n) - med(a1n))), nn(rng(a1n)), g(med(s1new)), nns(s1new),
         g(med(s1new) - med(a1n)), g(med(s1new) - med(a2n)), ref(rules)))
    need(min(med(s1new) - med(a1n), med(s1new) - med(a2n)) > abs(med(a2n) - med(a1n)), 'session 1 median further than the two baselines apart')
    p72 = sorted({r['passes'] for x in pa3 for r in x['s1']})
    p80 = sorted({r['passes'] for x in pa3 for r in x['a1'] + x['a2']})
    n600 = sum(1 for x in pa3 for r in x['a1'] + x['a2'] if r['passes'] == min(p80))
    n80 = sum(len(x['a1'] + x['a2']) for x in pa3)
    w('- Pass counts differ: the 7200 MT/s intervals of this table completed %s passes. Of the %d intervals at '
      '8000 MT/s, %d completed %d passes, and the others %s. The whole-pass stop rule moves the rate together with '
      'the pass count (rule V3, effect a). So part A cannot give the size of a change.'
      % (' to '.join(map(str, [p72[0], p72[-1]])) if len(p72) > 1 else str(p72[0]), n80, n600, min(p80),
         ', '.join(map(str, p80[1:]))))
    a1la = D['base']['A-1']['procs'][0]
    w('- Limit: session 1 started from an idle machine, without the one-thread phase of 2026-11-13 (section 1.5). Row '
      'A-1 started directly after its one-thread phase, at a load of %.2f (section 1.5, point 1). Row A-2 started %s, '
      'at a load of %.2f (section 1.5, point 11).'
      % (a1la['load1'], c['a2pre_txt'], D['probe13']['a2_first']['load1']))
    w('')
    full = 64 * 6 + 56 * 5
    w('The same intervals, restricted to an equal pass count (%d or %d passes) and kept apart by round. This view is '
      'not part of rule V3. It was added while this sheet was built.' % (full - 1, full))
    w('')
    same = lambda rs: [r for r in rs if r['passes'] in (full - 1, full)]
    rows, eqr = [], []
    for x in pa3:
        b = x['a1'] + x['a2']
        s72, s80 = same(x['s1']), same(b)
        e = dict(x=x, s72=s72, s80=s80, k=compare(s72, s80) if s72 and s80 else None)
        eqr.append(e)
        if s80:
            per = ', '.join('%s %d' % (d, sum(r['dataset'] == d for r in s80)) for d in ('A-1', 'A-2') if any(r['dataset'] == d for r in s80))
            cell80 = '%s (n=%d: %s)' % (one_v(s80), len(s80), per)
        else:
            cell80 = 'no such interval (%d intervals, passes: %s)' % (len(b), ', '.join(map(str, sorted({r['passes'] for r in b}))))
        rows.append(['%s %s' % (x['binary'], x['kernel']), x['round'],
                     '%s (n=%d)' % (one_v(s72), len(s72)) if s72 else 'no such interval', cell80,
                     ('yes' if e['k']['overlap'] else 'no') if e['k'] else '-',
                     ('0' if e['k']['overlap'] else '%+.2f' % e['k']['dist']) if e['k'] else '-'])
    L.extend(table(['Binary and kernel', 'Round', '7200 MT/s, session 1, GB/s', '8000 MT/s, A-1 and A-2, same round, GB/s',
                    'Overlap', 'Distance of the nearest ends, GB/s'], rows))
    r1 = [e for e in eqr if e['x']['round'] == 1]
    r2 = [e for e in eqr if e['x']['round'] == 2]
    r1all = [r for e in r1 for r in e['x']['a1'] + e['x']['a2']]
    p1 = sorted({r['passes'] for r in r1all})
    need(not any(e['s80'] for e in r1) and len(p1) == 1, 'round 1 at 8000 MT/s: every interval has the same pass count, not the full one')
    both = [e for e in r2 if e['k']]
    need(both and all(not e['k']['overlap'] and e['k']['dist'] > 0 for e in both),
         'equal pass count, round 2: session 1 above the 8000 MT/s intervals in every cell that has both sides')
    none2 = [e for e in r2 if not e['k']]
    w('- Round 1: no 8000 MT/s interval has %d or %d passes. All %d have %d passes. So round 1 gives no comparison at '
      'an equal pass count.' % (full - 1, full, len(r1all), p1[0]))
    w('- Round 2: %s have such intervals at both speeds. Session 1 lies above the 8000 MT/s intervals in %s, by %s GB/s '
      'at the nearest ends.%s'
      % (' and '.join('%s %s' % (e['x']['binary'], e['x']['kernel']) for e in both),
         'both cells' if len(both) == 2 else 'each of these %d cells' % len(both),
         ' and '.join(g(e['k']['dist']) for e in both),
         (' %s has no such 8000 MT/s interval.' % ' and '.join('%s %s' % (e['x']['binary'], e['x']['kernel']) for e in none2)) if none2 else ''))
    n2 = [r for e in r2 for r in e['x']['a1'] + e['x']['a2']]
    w('- Limit: this view uses %d of the %d round-2 intervals at 8000 MT/s.' % (sum(len(e['s80']) for e in r2), len(n2)))
    w('')
    half = 120 * 0.005       # largest rounding error of 120 x (a value rounded to 0.01 GB/s)
    w('Rates of the threads in the same rows, kept apart by round. The column per_thread_avg_GBps of the csv gives '
      'the average rate of the 120 threads of an interval. 120 times this value is the sum of the thread rates. It '
      'is an estimate (est.): the column is rounded to 0.01 GB/s, so each sum is exact to %.1f GB/s.' % half)
    w('')
    rows, tr = [], []
    av = lambda rs: [r['per_thread_avg_GBps'] for r in rs]
    span = lambda v, f='%.2f': (f % min(v)) if min(v) == max(v) else (f + ' to ' + f) % (min(v), max(v))
    for x in pa3:
        s1, a1, a2 = av(x['s1']), av(x['a1']), av(x['a2'])
        b = a1 + a2
        t = dict(x=x, est=120 * (min(s1) - max(b)), agg=min(x['above']), above=min(s1) > max(b))
        tr.append(t)
        rows.append(['%s %s' % (x['binary'], x['kernel']), x['round'], span(s1), span(a1), span(a2) if a2 else 'no process',
                     span([120 * v for v in s1], '%.1f'), span([120 * v for v in b], '%.1f'), '%+.1f' % t['est'], '%+.2f' % t['agg']])
    L.extend(table(['Binary and kernel', 'Round', '7200 MT/s, session 1: average per thread, GB/s',
                    '8000 MT/s, A-1: average per thread, GB/s', '8000 MT/s, A-2: average per thread, GB/s',
                    '7200 MT/s: 120 x average, GB/s (est.)', '8000 MT/s, A-1 and A-2: 120 x average, GB/s (est.)',
                    'Distance of the nearest ends by 120 x average, GB/s (est.)',
                    'Distance of the nearest ends by aggregate_GBps, GB/s'], rows))
    need(all(t['above'] for t in tr), 'per-thread average of session 1 above the 8000 MT/s processes of the same round in every cell')
    larger = [t for t in tr if t['est'] > t['agg']]
    smaller = [t for t in tr if t['est'] <= t['agg']]
    need(all(t['agg'] - t['est'] <= 2 * half for t in smaller), 'a smaller estimated distance stays inside the rounding of the column')
    # check of the estimate on the file that holds one row per thread (row A-2, option --per-thread)
    chk_n, chk_max = 0, 0.0
    for p_ in D['base']['A-2']['procs']:
        for iv in p_['iv']:
            rows_ = p_['thr'][iv['rep']]
            need(len(rows_) == 120, '120 thread rows per interval in A1.csv')
            chk_n += 1
            chk_max = max(chk_max, abs(sum(rows_) - 120 * iv['tavg']))
    need(chk_max <= 2 * half + 1e-9, 'sum of the thread rows of A1.csv equal to 120 x per_thread_avg within the rounding')
    w('- In all %d cells every per-thread average of session 1 lies above every per-thread average of the 8000 MT/s '
      'processes of the same round.' % len(tr))
    w('- By 120 x average (est.) the distance of the nearest ends is larger than by aggregate_GBps in %d of the %d '
      'cells.%s' % (len(larger), len(tr),
                    (' In %s it is %s GB/s smaller. That is inside the rounding of the column (each end is exact to %.1f GB/s).'
                     % (' and '.join('%s %s, round %d' % (t['x']['binary'], t['x']['kernel'], t['x']['round']) for t in smaller),
                        ' and '.join('%.2f' % (t['agg'] - t['est']) for t in smaller), half)) if smaller else ''))
    w('- Check of the estimate: A1.csv (row A-2) holds one row per thread, rounded to 0.01 GB/s. Over its %d '
      'intervals the sum of the 120 thread rows differs from 120 x per_thread_avg_GBps by at most %.2f GB/s %s. Both '
      'sides are rounded, so a difference of up to %.1f GB/s fits.'
      % (chk_n, chk_max, ref(os.path.join(D['base']['A-2']['folder'], 'A1.csv')), 2 * half))
    w('- So by this estimate the sum of the thread rates is also higher in session 1 than in the 8000 MT/s rows of '
      'the same round. The estimate does not show a part of a distance that comes from the pass count alone.')
    w('- Insufficient data: how much of each distance in the first table comes from the pass-count step of the '
      'whole-pass stop rule. Part A with the option --per-thread at 7200 MT/s would resolve it. It prints the rate of '
      'every thread, as A1.csv does.')
    w('')
    c['thr'] = tr

    # ---- 4.4 asmread part L
    w('### 4.4 Load-only loop in part L (asmread, position 1, directly after oldread)')
    w('')
    w('- asmread is used in place of the new read kernel here. It is the same loop of 8 "ldp q" loads per 256 B %s.'
      % ref(os.path.join(W15, 'FINDINGS.md')))
    w('- F72d12 and control I are separate 7200 MT/s rows of the same boot. In every range test of rule V1 point 2 '
      'each of them is its own row. Other places of this sheet give one range over several of these rows, for example '
      'the three visits in section 4.6 and the sums per mesh in section 4.7. Such a place says which rows it takes '
      'together.')
    w('')
    L.extend(ranges([('part L (T72L1 to T72L3). ' + STANDIN, sL, L72a)] + lrows('asmread', 1)
                    + [('pool L-1 to L-4', 'all bwx12 rows of the fixed list', P12a)] + orows('asmread', 1)
                    + [('pool L-1 to L-4, R0, R0b', 'bwx12 rows and other-binary rows', PALLa),
                       ('X2d12', DESC['X2d12'], x2a), ('F72d12', DESC['F72d12'], F72a), ('control I (T72I1, T72I2)', sI, I72a)]))
    L.extend(cmps('L', 'asmread', [(('part L', 'part L. ' + STANDIN), L72a, sc_a),
                                    (('F72d12 ' + OLD_OWN, 'F72d12 ' + OWN), F72a, sc_a),
                                    (('control I ' + OLD_OWN, 'control I ' + OWN), I72a, sc_a)], notes={'part L': STANDIN}))
    need(not compare(L72a, l1a)['overlap'] and not compare(L72a, PALLa)['overlap'], 'part L asmread above every 8000 MT/s scope')
    need(not cIa['overlap'] and cIa['dist'] > 0, 'control I asmread above the 8000 MT/s pool')
    kF1, kI1 = compare(F72a, l1a), compare(I72a, l1a)
    need(not kF1['overlap'] and kF1['dist'] > 0 and not kI1['overlap'] and kI1['dist'] > 0,
         'asmread: F72d12 and control I above L-1 alone')
    c['kF1'], c['kI1'] = kF1, kI1
    l1la = D['rx']['L-1']['launches']['a6456']
    Ila = [x['launches'][0] for x in D['X'] if x['part'] == 'I']
    Igap = [evd[x['tag']]['gap_s'] for x in D['X'] if x['part'] == 'I']
    Iref = ' '.join(ref(os.path.join(x['folder'], 'launches.txt')) for x in D['X'] if x['part'] == 'I')
    need(max(la['load1'] for la in Ila) < 1.0 and l1la['load1'] < 1.0 and min(la['load5'] for la in Ila) > 1.0
         and max(l1la['load5'], l1la['load15']) < 1.0 and min(Igap) > 60,
         'control I and L-1: both below 1.0 in the 1-minute load, control I above 1.0 in the 5-minute load and more '
         'than 60 s after 120-thread work')
    w('- Part L, wording by rule V1 point 2: "%s". Part L is higher by %s GB/s at the nearest ends. n at 7200 MT/s: '
      '%s. n at 8000 MT/s: %s. The result is the same against L-1 alone and against the pool with the other-binary rows.'
      % (cLa['wording'], g(cLa['dist']), nn(cLa['a'], sessions=True), nn(cLa['b'])))
    w('- Control I (%s, idle start by the 1-minute load rule): "%s". It is higher by %s GB/s at the nearest ends '
      '(%s GB/s against L-1 alone). n at 7200 MT/s: %s. n at 8000 MT/s: %s. The start state of control I is not that '
      'of L-1. L-1 was launched at load averages of %.2f / %.2f / %.2f (1 / 5 / 15 min) %s. Control I was launched '
      '%s s after 120-thread work (section 4.6).'
      % (ADDED, cIa['wording'], g(cIa['dist']), g(kI1['dist']), nns(I72a), nn(cIa['b']), l1la['load1'], l1la['load5'],
         l1la['load15'], ref(os.path.join(D['rx']['L-1']['folder'], 'launches.txt')),
         ' s and '.join('%.0f' % v for v in Igap)))
    w('- F72d12 (same boot, same speed, load %.2f at launch): its range %s the pool L-1 to L-4%s.'
      % (f72la['load1'], 'overlaps' if cFa['overlap'] else 'does not overlap',
         ('. It does not overlap L-1 alone, where it is %s GB/s higher' % g(kF1['dist'])) if not kF1['overlap'] else ''))
    hwc = c['hw']
    wo = rng(hwc['P12a_wo'])
    kLw, kFw, kIw = compare(L72a, hwc['P12a_wo']), compare(F72a, hwc['P12a_wo']), compare(I72a, hwc['P12a_wo'])
    need(not kLw['overlap'] and kLw['dist'] > 0 and not kIw['overlap'] and kIw['dist'] > 0 and kFw['overlap']
         and wo['lo'] <= rng(F72a)['lo'] and rng(F72a)['hi'] <= wo['hi'] and wo['hi'] == cLa['b']['hi'],
         'without the interval with error records: part L and control I above the pool, F72d12 inside it')
    c['hw']['wo'] = wo
    w('- Hardware error records (section 4.1): 2 corrected records fall inside the interval that sets the lower end of '
      'the pool L-1 to L-4 (%s GB/s, row %s, process %s, round %d). Without this one interval the pool spans %s GB/s '
      '(%s GB/s wide, %s %% of its lower end, %s). No wording by rule V1 point 2 changes with it: part L and control I '
      'still lie above the pool, and F72d12 still lies inside its range. The upper end of the pool is the same. So '
      'the distances of the nearest ends do not change. For the rerun the records are not known (section 1.5, '
      'point 8).'
      % (g(hwc['low_a']['GBps']), hwc['low_a']['dataset'], hwc['low_a']['tag'], hwc['low_a']['round'], sp(wo),
         g(wo['hi'] - wo['lo']), pc(width_pct(wo)), nn(wo)))
    w('- By rule V1 point 3 no percent change is given. Section 4.6 states what follows.')
    w('')

    # ---- 4.5 part C load-only
    w('### 4.5 Load-only kernels in part C')
    w('')
    w('**Kernel `read` (new read kernel in bwx12).**')
    w('')
    w('- %s.' % NO_READ)
    w('- Text required by rule F2 point 3: The bwx12 kernel read (new C read loop) was never run with bwx12 at '
      '8000 MT/s. The 2026-11-15 investigation ran asmread (hand-written loop with the same 8 loads per 256 B) in its '
      'place.')
    w('- The nearest data come from another binary: the first runner bwx of 2026-11-13. They are not a like-for-like '
      'baseline. The like-for-like 8000 MT/s baseline of the new read kernel is part A (section 4.3).')
    w('')
    Rao = sel(C, kernel='read', kernel_before='oldread')
    Raa = sel(C, kernel='read', kernel_before='asmread')
    rows = [('part C, read after oldread (cfwd, position 1)', 'rerun', Rao)]
    for d in BWX:
        rows.append((d + ', read at position 1 (after oldread)', DESC[d], sel(recs, dataset=d, kernel='read', pos=1)))
    bx1 = sel(recs, dataset=set(BWX), kernel='read', pos=1)
    rows.append(('pool B7a, B7b, C3a, C3b, position 1', 'other binary (bwx)', bx1))
    rows.append(('the same, only the %d processes with --start common' % nsc, 'other binary (bwx)', scm(bx1)))
    for d in ('B5a', 'B5b'):
        rows.append((d + ', read at position 1 (after oldread)', DESC[d], sel(recs, dataset=d, kernel='read', pos=1)))
    rows.append(('part C, read after asmread (crev, position 1)', 'rerun', Raa))
    for d in BWX:
        rows.append((d + ', read at position 6 (after asmread)', DESC[d], sel(recs, dataset=d, kernel='read', pos=6)))
    bx6 = sel(recs, dataset=set(BWX), kernel='read', pos=6)
    rows.append(('pool B7a, B7b, C3a, C3b, position 6', 'other binary (bwx)', bx6))
    rows.append(('the same, only the %d processes with --start common' % nsc, 'other binary (bwx)', scm(bx6)))
    L.extend(ranges(rows))
    k1, k6 = compare(Rao, bx1), compare(Raa, bx6)
    q2row('C', 'read after oldread', 'part C, cfwd', 'other binary bwx, position 1 (not like-for-like)', k1, False, NO_READ)
    q2row('C', 'read after asmread', 'part C, crev', 'other binary bwx, position 6 (not like-for-like)', k6, False, NO_READ)
    w('- Against the other-binary pool of the same position, read after oldread is %s. Read after asmread is %s.'
      % tuple(('%s GB/s above its highest value' % g(k['dist'])) if k['dist'] > 0 else
              ('%s GB/s below its lowest value' % g(-k['dist'])) if k['dist'] < 0 else 'inside its range' for k in (k1, k6)))
    cnt = sorted({(r['dataset'], r['count']) for r in sel(recs, dataset=set(BWX))})
    w('- Difference of these references (rule V2 point 4): they used the binary bwx of 2026-11-13. The csv headers '
      'show the counter setting: %s (count=1 means with core counters). Part C used bwx12 with counters.'
      % ', '.join('%s count=%d' % (d, c_) for d, c_ in cnt))
    allp = {r['proc_key']: r for r in sel(recs, dataset=set(BWX))}
    noff = sum(1 for r in allp.values() if r['start'] == 'offset')
    need(noff + nsc == len(allp) and noff > 0, 'the processes of the bwx pool used --start common or --start offset')
    bx2 = sel(recs, dataset=set(BWX), kernel='asmread', pos=2)
    same_ends = all((rng(scm(v))['lo'], rng(scm(v))['hi']) == (rng(v)['lo'], rng(v)['hi']) for v in (bx1, bx2, bx6))
    w('- A second difference: %d of the %d processes of this pool (tags common-6000-offset-*) used --start offset. '
      'Part C used --start common %s %s. --start is an option of the runner. This sheet only notes that its value '
      'differs. The rows "only the %d processes with --start common" show the pool without them. %s'
      % (noff, len(allp), ref(os.path.join(S_, 'cfwd.spec')), ref(os.path.join(S_, 'crev.spec')), nsc,
         'At positions 1, 2 and 6 the lowest and the highest value stay the same, and the medians change.' if same_ends
         else 'Lowest and highest values change, see the rows.'))
    w('- Rule V4 and rule V2 point 4 name different process lists for these rows. Decision (p) in section 2 states '
      'the choice.')
    w('')
    w('**Kernel `asmread`.**')
    w('')
    Aao = sel(C, kernel='asmread', kernel_before='oldread')
    Aar = sel(C, kernel='asmread', kernel_before='read')
    Aaf = sel(C, kernel='asmread', kernel_before=first)
    L.extend(ranges([('part C, asmread after oldread (crev, round 1, position 0)', 'rerun, the condition of part L', Aao),
                     ('part C, asmread as first interval (crev, round 0, position 0)', 'rerun', Aaf),
                     ('part C, asmread after read (cfwd, position 2)', 'rerun', Aar),
                     ('L-1 alone', L1C + '. asmread at position 1 (after oldread)', l1a),
                     ('pool L-1 to L-4', 'bwx12 rows, asmread at position 1 (after oldread)', P12a),
                     ('pool L-1 to L-4, R0, R0b', 'bwx12 rows and other-binary rows, asmread at position 1 (after oldread)', PALLa),
                     ('pool B7a, B7b, C3a, C3b, position 2', 'other binary (bwx), asmread after read', bx2),
                     ('the same, only the %d processes with --start common' % nsc, 'other binary (bwx), asmread after read', scm(bx2))]))
    need({r['pos'] for r in Aao} == {0} == {r['pos'] for r in Aaf} and {r['pos'] for r in Aar} == {2}
         and {r['pos'] for r in PALLa} == {1} and {r['kernel_before'] for r in PALLa} == {'oldread'},
         'asmread: position 0 or 2 in part C, position 1 directly after oldread in the rows L-1 to L-4, R0, R0b')
    # The 8000 MT/s rows hold asmread at position 1, directly after oldread. The first group of part C matches them
    # in the kernel that ran directly before, not in the position. The other two groups match in neither.
    m_k = lambda name: (name + ' (after oldread)', name + ' (after oldread), asmread at position 1 against position 0 '
                        'in part C')
    m_0 = ('pool L-1 to L-4 (after oldread, position not matched)',
           'pool L-1 to L-4 (after oldread, at position 1): kernel before and position not matched')
    L.extend(cmps('C', 'asmread', [
        ('part C, asmread after oldread', Aao, [(m_k('L-1 alone'), l1a, False), (m_k('pool L-1 to L-4'), P12a, True),
                                                (m_k('pool L-1 to L-4, R0, R0b'), PALLa, False)]),
        ('part C, asmread as first interval', Aaf, [(m_0, P12a, False)]),
        ('part C, asmread after read', Aar, [(m_0, P12a, False),
                                             ('other binary bwx, position 2 (after read)', bx2, False)])],
        F2_NOTE + ' The 8000 MT/s rows match in the kernel that ran directly before, not in the position.'))
    kAao = compare(Aao, P12a)
    need(not compare(Aao, l1a)['overlap'] and not compare(Aao, PALLa)['overlap'], 'part C asmread after oldread above every 8000 MT/s scope')
    w('- asmread after oldread, wording by rule V1 point 2: "%s". n at 7200 MT/s: %s (%s). n at 8000 MT/s: %s. The '
      'result is the same against L-1 alone and against the pool with the other-binary rows. %s'
      % (kAao['wording'], nns(Aao), ', '.join(dict.fromkeys(r['tag'] for r in Aao)), nn(kAao['b']), F2_NOTE))
    c['kAao'], c['Aao'] = kAao, Aao
    w('- No asmread group of part C has a position-matched bwx12 baseline (rule V4). The group "asmread after oldread" '
      '(crev, round 1, position 0) matches rows L-1 to L-4 (asmread at position 1) only in the kernel that ran '
      'directly before (rule V2 points 1 and 4). The other two groups do not match in that kernel either. Their rows '
      'in the table carry no wording.')
    w('- The rows without a wording also show part C next to 8000 MT/s rows. Decision (r) in section 2 names them.')
    w('- Rule V2 point 5 asks to state that part L and the forward order measure the lower of the two conditions. '
      'At 8000 MT/s (runner bwx) the median of read after oldread is %s GB/s below the median of read after asmread '
      '(%s GB/s with the %d --start common processes only). At 7200 MT/s it is %s GB/s below, and the two ranges '
      'overlap. The reverse order comes from %d processes (%s).'
      % (g(med(bx6) - med(bx1)), g(med(scm(bx6)) - med(scm(bx1))), nsc, g(med(Raa) - med(Rao)),
         len({r['proc_key'] for r in Raa}), ', '.join(dict.fromkeys(r['tag'] for r in Raa))))
    need(med(Raa) > med(Rao) and overlap(rng(Raa), rng(Rao)), 'read after asmread above read after oldread, ranges overlap')
    kAA = compare(Aao, Aar)
    need(not kAA['overlap'] and kAA['dist'] > 0, 'part C: asmread after oldread above asmread after read, no overlap')
    w('- For asmread the order is the opposite at 7200 MT/s. asmread directly after oldread (crev, round 1, the '
      'condition of part L) gave %s GB/s. asmread after read (cfwd) gave %s GB/s. The two ranges do not overlap. They '
      'are %s GB/s apart. So the part C data at 7200 MT/s do not show that part L measures the lower condition. '
      'Order and process are not separated: each order has %d processes.'
      % (' and '.join(g(r['GBps']) for r in Aao), sp(rng(Aar)), g(kAA['dist']), rng(Aar)['procs']))
    w('')

    # ---- 4.6 same boot
    w('### 4.6 What the rows of the same boot show, and what follows for Q2')
    w('')
    allv = F72a + L72a + I72a
    av = rng(allv)
    kLI, kIF = compare(L72a, I72a), compare(I72a, F72a)
    need(not kLI['overlap'] and not kIF['overlap'] and kLI['dist'] > 0 and kIF['dist'] > 0, 'three visits in rising order without overlap')
    tI = [evd[t]['first'] for t in ('T72I1', 'T72I2')]
    tL = [evd[t]['first'] for t in ('T72L1', 'T72L2', 'T72L3')]
    w('The same argument line (like.spec) ran at three times in boot %s at 7200 MT/s. asmread at position 1 gave:'
      % try6['boot'][:8])
    w('')
    L.extend(table(['Visit', 'Launch times', 'Start state', 'Time since the first kernel log line of the boot',
                    'asmread, GB/s', 'oldread, GB/s', 'n per kernel'], [
        ['F72d12', hm(f72la['utc']), 'load %.2f at launch. Process list %.0f s before the launch: %s at %s %%CPU'
         % (f72la['load1'], (f72la['utc'] - fenv['start']).total_seconds(), fenv['top'][0][2], fenv['top'][0][1]),
         dur((f72la['utc'] - try6['first_log_utc']).total_seconds()),
         sp(rng(F72a)), sp(rng(F72o)), nn(rng(F72a), boots=False)],
        ['part L', '%s to %s' % (hm(tL[0]), hm(tL[-1])), '%.0f s after part A (load %.2f to %.2f)'
         % (evd['T72L1']['gap_s'], min(evd[t]['load1'] for t in ('T72L1', 'T72L2', 'T72L3')), max(evd[t]['load1'] for t in ('T72L1', 'T72L2', 'T72L3'))),
         '%s to %s' % (dur((tL[0] - try6['first_log_utc']).total_seconds()), dur((tL[-1] - try6['first_log_utc']).total_seconds())),
         sp(rng(L72a)), sp(rng(L72o)), nn(rng(L72a), boots=False)],
        ['control I (%s)' % ADDED, '%s and %s' % (hm(tI[0]), hm(tI[1])),
         'idle (load %.2f and %.2f), %.0f s and %.0f s after 120-thread work. Process lists: at most %s %%CPU'
         % (evd['T72I1']['load1'], evd['T72I2']['load1'], evd['T72I1']['gap_s'], evd['T72I2']['gap_s'],
            max(x['env']['pcpu_max'] for x in D['X'] if x['part'] == 'I')),
         '%s and %s' % (dur((tI[0] - try6['first_log_utc']).total_seconds()), dur((tI[1] - try6['first_log_utc']).total_seconds())),
         sp(rng(I72a)), sp(rng(I72o)), nn(rng(I72a), boots=False)]]))
    spread = av['hi'] - av['lo']
    ov = rng(F72o + L72o + I72o)
    w('- The three asmread ranges do not overlap each other.')
    need(av['lo'] == rng(F72a)['lo'] and av['hi'] == rng(L72a)['hi'], 'asmread: lowest value in F72d12, highest in part L')
    need(ov['lo'] == rng(L72o)['lo'] and ov['hi'] == rng(I72o)['hi'], 'oldread: lowest value in part L, highest in control I')
    w('- The lowest asmread value of the three visits is %s GB/s (F72d12). The highest is %s GB/s (part L). They are '
      '%s GB/s apart (%s %% of the lowest value), at one memory speed, inside one boot.'
      % (g(av['lo']), g(av['hi']), g(spread), pc(spread / av['lo'] * 100)))
    w('- The two visits that were launched at a load below 1.0 (F72d12 and control I) are at least %s GB/s apart.' % g(kIF['dist']))
    envI = [(x['tag'], x['env']['pcpu_max'], os.path.join(x['folder'], 'env.txt')) for x in D['X'] if x['part'] == 'I']
    t_env = (fenv['start'] - try6['first_log_utc']).total_seconds()
    need(t_env > 0 and fenv['top'][0][1] > 10 and max(v[1] for v in envI) < 1, 'process list: F72d12 busy, control I not')
    w('- F72d12 and control I differ in more than the time since boot. env.txt of F72d12 was written at %s, %.0f s after '
      'the first kernel log line of the boot and %.0f s before the launch. It lists %s at %s %%CPU and %s at %s %%CPU '
      '(lines %d and %d %s). env.txt of %s lists at most %s %%CPU %s. So F72d12 is an idle start only by the '
      'load-average rule of this sheet.'
      % (hm(fenv['start']), t_env, (f72la['utc'] - fenv['start']).total_seconds(), fenv['top'][0][2], fenv['top'][0][1],
         fenv['top'][1][2], fenv['top'][1][1], fenv['top'][0][3], fenv['top'][1][3], ref(os.path.join(f72dir, 'env.txt')),
         ' and '.join(v[0] for v in envI), max(v[1] for v in envI), ' '.join(ref(v[2]) for v in envI)))
    gt = [t for t in try6.get('gaps_top', []) if t[2] == fenv['top'][0][2]]
    need(len(gt) == 1 and 'gaps_uptime_utc' in try6, 'gaps.txt holds a later %CPU value of the same thread')
    t_gap = (try6['gaps_uptime_utc'] - try6['first_log_utc']).total_seconds()
    cpu1, cpu2 = fenv['top'][0][1] / 100 * t_env, gt[0][1] / 100 * t_gap
    f72end = D['rx']['F72d12']['launches']['a6456']['rc_utc']
    need(fenv['start'] < f72la['utc'] < f72end < try6['gaps_uptime_utc'] and cpu2 > cpu1,
         'the F72d12 process lies between the two readings of the thread')
    w('- Hypothesis (not tested): the thread %s was still busy during the first seconds of the F72d12 process. What '
      'fits: its %%CPU value was %s at %s and %s at %s (line %d of gaps.txt %s). With the assumption that the thread '
      'started at the first kernel log line (%s), these values mean about %.1f s of CPU time in the first %.0f s and '
      'about %.1f s in the first %.0f s (est.). That is about %.1f s of CPU time in the %.0f s between the two '
      'readings (est.). The F72d12 process ran inside this time, from %s to %s. Measurement that would confirm or '
      'reject it: a sample of the load of every CPU, once per second, in the first minutes after a boot.'
      % (fenv['top'][0][2], fenv['top'][0][1], hm(fenv['start']), gt[0][1], hm(try6['gaps_uptime_utc']), gt[0][3],
         ref(try6['gaps_path']), hm(try6['first_log_utc']), cpu1, t_env, cpu2, t_gap, cpu2 - cpu1,
         (try6['gaps_uptime_utc'] - fenv['start']).total_seconds(), hm(f72la['utc']), hm(f72end)))
    w('- The lowest oldread value of the three visits is %s GB/s (part L). The highest is %s GB/s (control I). They '
      'are %s GB/s apart (%s %% of the lowest value).' % (g(ov['lo']), g(ov['hi']), g(ov['hi'] - ov['lo']), pc((ov['hi'] - ov['lo']) / ov['lo'] * 100)))
    b12 = rng(P12a)
    w('- For comparison, the 8000 MT/s rows L-1 to L-4 span %s GB/s (%s GB/s wide, %s), also inside one boot.'
      % (sp(b12), g(b12['hi'] - b12['lo']), nn(b12)))
    lo_all = sel(recs, dataset=set(BWX), kernel={'read', 'asmread'})
    bxa = rng(lo_all)
    w('- The first runner bwx (other binary) gave %s GB/s for its load-only kernels read and asmread at 8000 MT/s in '
      'the processes with the tags common-6000-* (%s, %d folders of 2026-11-13 and 2026-11-14, same boot).'
      % (sp(bxa), nn(bxa), len(BWX)))
    w('- Rule V1 point 5: the 12-module data at 8000 MT/s reach %s GB/s (bw_new read, rows A-1 and A-2) and %s GB/s '
      '(bw_new asmread, rows A-1 and A-2). In the rows of runner bwx used in this sheet (B7a, B7b, C3a, C3b, tags '
      'common-6000-*) they reach %s GB/s (read) and %s GB/s (asmread).'
      % (g(rng(sel(recs, dataset={'A-1', 'A-2'}, binary='bw_new', kernel='read'))['hi']),
         g(rng(sel(recs, dataset={'A-1', 'A-2'}, binary='bw_new', kernel='asmread'))['hi']),
         g(rng(sel(recs, dataset=set(BWX), kernel='read'))['hi']), g(rng(sel(recs, dataset=set(BWX), kernel='asmread'))['hi'])))
    b5rev = sel(recs, dataset={'B5a-rev', 'B5b-rev'})
    top_r = max(sel(b5rev, kernel='read'), key=lambda r: r['GBps'])
    top_a = max(sel(b5rev, kernel='asmread'), key=lambda r: r['GBps'])
    b5read = rng(sel(recs, dataset={'B5a', 'B5b', 'B5a-rev', 'B5b-rev'}, kernel='read'))
    gro, gra = rng(CG['read after oldread'][0]), rng(CG['read after asmread'][0])
    in_ = lambda v, a: a['lo'] <= v <= a['hi']
    need(top_r['GBps'] > rng(sel(recs, dataset=set(BWX), kernel='read'))['hi']
         and top_a['GBps'] > rng(sel(recs, dataset=set(BWX), kernel='asmread'))['hi'],
         'the reverse-order B5 processes hold higher values than the common-6000-* rows')
    need(in_(top_r['GBps'], gro) and in_(top_r['GBps'], gra) and in_(top_a['GBps'], rng(L72a)),
         'the highest B5 values lie inside the 7200 MT/s ranges')
    where = lambda r: 'process %s of %s, position %d, directly after %s, I row in line %d' % (r['tag'], r['folder'], r['pos'], r['kernel_before'], r['line'])
    w('- Higher values of runner bwx exist outside these rows. The reverse-order processes of the two B5 folders '
      '(tags b5-rev-*, %d processes, one interval per kernel, common stop, %s) reach %s GB/s for read (%s) and %s GB/s '
      'for asmread (%s) %s. read_sparse and asmread2 are other kernels of runner bwx. Rule F2 point 4 quotes the range '
      'of read over the %d processes of the two B5 folders: %s GB/s %s.'
      % (rng(b5rev)['procs'], secs(b5rev), g(top_r['GBps']), where(top_r), g(top_a['GBps']), where(top_a),
         src([top_r, top_a]), b5read['procs'], sp(b5read), ref(rules)))
    w('- The read value of %s GB/s lies inside the 7200 MT/s ranges of both read groups of part C (%s and %s GB/s). The '
      'asmread value of %s GB/s lies inside the 7200 MT/s range of part L (%s GB/s). Both values come from another '
      'binary and another kernel order. They are not a like-for-like baseline.'
      % (g(top_r['GBps']), sp(gro), sp(gra), g(top_a['GBps']), sp(rng(L72a))))
    w('')
    w('What follows for Q2:')
    w('')
    aL, aF, aP = rng(L72a), rng(F72a), rng(P12a)
    dist = dict(near_boot=aL['lo'] - aF['hi'], near_pool=cLa['dist'], med_boot=aL['med'] - aF['med'],
                med_pool=aL['med'] - aP['med'], far_boot=aL['hi'] - aF['lo'], far_pool=aL['hi'] - aP['lo'])
    need(abs(dist['far_boot'] - spread) < 1e-9, 'the farthest ends inside the boot are the spread of the three visits')
    need(dist['near_boot'] > dist['near_pool'] and dist['med_boot'] > dist['med_pool'] and dist['far_boot'] < dist['far_pool'],
         'part L to F72d12 against part L to the 8000 MT/s pool: larger for nearest ends and medians, smaller for farthest ends')
    c['dist'] = dist
    w('- The same kind of distance is compared on both sides. Nearest ends: part L lies %s GB/s above the 8000 MT/s pool and %s GB/s above '
      'F72d12, the earlier visit of the same boot. Medians: %s GB/s and %s GB/s. Farthest ends: %s GB/s and %s GB/s.'
      % (g(dist['near_pool']), g(dist['near_boot']), g(dist['med_pool']), g(dist['med_boot']), g(dist['far_pool']), g(dist['far_boot'])))
    w('- So the move between two visits inside the 7200 MT/s boot is larger than the distance of part L to the '
      '8000 MT/s pool for the nearest ends and for the medians. It is smaller for the farthest ends.')
    need(cFa['b']['lo'] <= cFa['a']['lo'] and cFa['a']['hi'] <= cFa['b']['hi'], 'F72d12 asmread inside the range of the pool L-1 to L-4')
    w('- One of the three 7200 MT/s visits (F72d12) lies inside the range of the 8000 MT/s pool L-1 to L-4. Against '
      'L-1 alone it is %s GB/s higher. The other two visits (part L and control I) lie above every row of the pool, '
      'by %s and %s GB/s at the nearest ends.' % (g(kF1['dist']), g(cLa['dist']), g(cIa['dist'])))
    hp_, ep_ = c['hw']['possible']
    need(hp_['dataset'] == 'L-1' and ep_['offset_s'] + 1 <= 2, 'L-1: records in the first 2 s of the process')
    w('- The comparison of part L with L-1 changes four things at once: the memory speed, the boot, the start state '
      '(%.0f s after part A against a start at load %.2f), and the hardware error records. Row L-1 has 2 corrected '
      'records in the first 2 s of its process (est., section 4.1). For the rerun the records are not known. A fifth thing '
      'is not known: the firmware settings of the boot of the rerun were not read (section 1.5, point 13).'
      % (evd['T72L1']['gap_s'], l1la['load1']))
    w('- Control I (%s) reduces the difference of the start '
      'state against L-1. The data do not show that it removes it. Control I is like L-1 by the 1-minute load rule '
      'only (%s against %.2f, all below 1.0). It was launched %s s after a 120-thread process, at 5-minute load '
      'averages of %s %s. L-1 was launched at load averages of %.2f / %.2f / %.2f (1 / 5 / 15 min) %s. So control I '
      'does not rule out an effect of the earlier 120-thread work (hypothesis H1 in section 6, not tested).'
      % (ADDED, ' and '.join('%.2f' % la['load1'] for la in Ila), l1la['load1'],
         ' s and '.join('%.0f' % v for v in Igap), ' and '.join('%.2f' % la['load5'] for la in Ila), Iref,
         l1la['load1'], l1la['load5'], l1la['load15'], ref(os.path.join(D['rx']['L-1']['folder'], 'launches.txt'))))
    w('- The 8000 MT/s pool also holds %d processes that started after 120-thread work (section 4.2, view by start '
      'state). Part L lies %s GB/s above their asmread range too.' % (c['byst']['Ba']['procs'], g(c['byst']['asm_near'])))
    w('- So the rerun shows that the load-only loop ran above the 8000 MT/s intervals of the same round (rows A-1 and '
      'A-2) in session 1 of part A. It ran above every bwx12 row of the fixed 8000 MT/s list (L-1 to L-4) in part L, '
      'in control I (%s) and in the group "asmread after oldread" of part C (comparison by decision (r) in section 2). '
      'It does not show that the memory speed is the cause.' % ADDED)
    xa1 = next(x for x in pa3 if (x['binary'], x['kernel'], x['round']) == ('bw_new', 'asmread', 1))
    top2 = max(sel(recs, dataset='A-2', binary='bw_new', kernel='asmread'), key=lambda r: r['GBps'])
    low1 = [r for r in xa1['s1'] if r['GBps'] < top2['GBps']]
    need(top2['round'] == 2 and low1, 'part A: round-1 intervals of session 1 below the highest round-2 interval of A-2')
    w('- The statement for part A holds inside the same round only. %d intervals of bw_new asmread of session 1, round 1 '
      '(%s GB/s, lines %s %s) lie below the highest round-2 interval of row A-2 (%s GB/s, line %d %s).'
      % (len(low1), ' and '.join(g(r['GBps']) for r in low1), ' and '.join(str(r['line']) for r in low1), src(low1),
         g(top2['GBps']), top2['line'], src([top2])))
    x1 = sel(recs, dataset='X1d10', kernel='asmread')
    x1b = sel(recs, dataset='X1d10b', kernel='asmread')
    apart = (med(x1b) / med(x1) - 1) * 100
    o10 = rng(sel(recs, dataset={'X1d10', 'X1d10b', 'BASEd10'}, kernel='oldread'))
    ins = ('Insufficient data: whether a difference of the new read kernel comes from the memory speed. Speed and boot '
           'changed together. Two boots at equal settings (10 modules, one process each) gave asmread %s / %s and '
           '%s / %s GB/s, %s %% apart (medians). Runs in several boots per speed would resolve it (needs reboots, not '
           'part of this task).' % (g(x1[0]['GBps']), g(x1[1]['GBps']), g(x1b[0]['GBps']), g(x1b[1]['GBps']), pc(apart)))
    V['insufficient_data'].append(ins)
    w('- Text required by rule V1 point 3: %s %s' % (ins, src(x1 + x1b)))
    w('- Text of rule V1 point 4 for old read: three 10-module boots gave old read %s GB/s (%s %% wide, %s). So the '
      'boot alone moved old read by less than 1 %% there. %s'
      % (sp(o10), pc(width_pct(o10)), nn(o10), src(sel(recs, dataset={'X1d10', 'X1d10b', 'BASEd10'}, kernel='oldread'))))
    need(width_pct(o10) < 1, '10-module old read range below 1 %')
    o10x = {d: rng(sel(recs, dataset=d, kernel='oldread')) for d in ('X1d10', 'X1d10b', 'BASEd10')}
    o10p = rng(sel(recs, dataset={'X1d10', 'X1d10b'}, kernel='oldread'))
    w('- Limit of this text: the three boots did not differ by the boot alone. X1d10 and X1d10b ran with the same '
      'changed TXREQ firmware settings (old read %s and %s GB/s). BASEd10 ran with the original settings (%s GB/s) '
      '%s. So the words "the boot alone" rest on the pair X1d10 and X1d10b (%s GB/s, %s %% wide, %s).'
      % (sp(o10x['X1d10']), sp(o10x['X1d10b']), sp(o10x['BASEd10']), ref(fd.DIMM_REPORT), sp(o10p), pc(width_pct(o10p)), nn(o10p)))
    w('')

    # ---- 4.7 per mesh
    w('### 4.7 Sums per mesh (looked at after the numbers were seen, not part of the fixed rules)')
    w('')
    w('The table gives the lowest and highest sum per mesh over the intervals of each row. Mesh 0 holds 64 threads, '
      'mesh 1 holds 56.')
    w('')

    def mrow(label, rs):
        m0, m1 = rng(rs, 'mesh0_GBps'), rng(rs, 'mesh1_GBps')
        return [label, '%d MT/s' % rs[0]['speed_MTps'], len(rs), sp(m0), sp(m1), src(rs)]
    sets_o = [('part L', L72o), ('part C', C72o), ('control I (%s)' % ADDED, I72o), ('F72d12', F72o), ('pool L-1 to L-4 (bwx12)', P12o),
              ('R0, R0b (bwx11)', pool(BW11, 'oldread', 0)), ('B7a, B7b, C3a, C3b (bwx), positions 0 and 7', sel(recs, dataset=set(BWX), kernel='oldread'))]
    sets_a = [('part L, asmread', L72a),
              ('part C, read after oldread', CG['read after oldread'][0]), ('part C, read after asmread', CG['read after asmread'][0]),
              ('part C, asmread after read', CG['asmread after read'][0]),
              ('part C, asmread as first interval of the process', CG['asmread first'][0]),
              ('part C, asmread after oldread', CG['asmread after oldread'][0]),
              ('control I (%s), asmread' % ADDED, I72a), ('F72d12, asmread', F72a),
              ('pool L-1 to L-4 (bwx12), asmread at position 1', P12a),
              ('R0, R0b (bwx11), asmread at position 1', pool(BW11, 'asmread', 1)),
              ('B7a, B7b, C3a, C3b (bwx), read at positions 1 and 6 and asmread at positions 2 and 5', lo_all)]
    need({(r['kernel'], r['pos']) for r in lo_all} == {('read', 1), ('read', 6), ('asmread', 2), ('asmread', 5)},
         'positions of the load-only kernels of runner bwx')
    w('- The sums of every interval are in facts.json (fields mesh0_GBps and mesh1_GBps). The tables of sections 3.2 '
      'and 3.3 print them for parts L and C, control I and F72d12 (columns "m0 + m1").')
    w('- The part C rows are shown next to 8000 MT/s rows here. Rule F2 points 2 and 3 would not do this (decision '
      '(r) in section 2). The bullets under the tables give the oldread result with part C and without it.')
    w('')
    w('oldread:')
    w('')
    L.extend(table(['Row', 'Memory speed', 'Intervals', 'Mesh 0, GB/s', 'Mesh 1, GB/s', 'Source'], [mrow(a, b) for a, b in sets_o]))
    w('Load-only kernels. Part C has one row per group (rule V2). No bwx12 row at 8000 MT/s holds the kernel read:')
    w('')
    L.extend(table(['Row', 'Memory speed', 'Intervals', 'Mesh 0, GB/s', 'Mesh 1, GB/s', 'Source'], [mrow(a, b) for a, b in sets_a]))
    o72 = L72o + C72o + I72o + F72o
    o80 = P12o + pool(BW11, 'oldread', 0)
    oxx = sel(recs, dataset=set(BWX), kernel='oldread')
    m0_72, m1_72 = rng(o72, 'mesh0_GBps'), rng(o72, 'mesh1_GBps')
    m0_80, m1_80 = rng(o80, 'mesh0_GBps'), rng(o80, 'mesh1_GBps')
    m0_x, m1_x = rng(oxx, 'mesh0_GBps'), rng(oxx, 'mesh1_GBps')
    need(m1_72['lo'] > m1_80['hi'] and m0_72['hi'] < m0_80['lo'], 'oldread mesh split differs against bwx12 and bwx11 rows')
    o72n = L72o + I72o + F72o                   # the same without part C (rule F2 points 2 and 3)
    m0_n, m1_n = rng(o72n, 'mesh0_GBps'), rng(o72n, 'mesh1_GBps')
    need(m1_n['lo'] > m1_80['hi'] and m0_n['hi'] < m0_80['lo'], 'oldread mesh split differs without part C too')
    o72p = L72o + F72o                          # the same without part C and without control I
    m0_p, m1_p = rng(o72p, 'mesh0_GBps'), rng(o72p, 'mesh1_GBps')
    need(m1_p['lo'] > m1_80['hi'] and m0_p['hi'] < m0_80['lo'], 'oldread mesh split differs without part C and control I too')
    c['mesh'] = dict(n_all=len(o72), n_noC=len(o72n), n_noCI=len(o72p))
    F72_WHAT = 'the earlier run of the same boot'
    w('- oldread, all %d intervals at 7200 MT/s (F72d12, parts L and C, and control I, which was %s): mesh 1 gave '
      '%s GB/s and mesh 0 gave %s GB/s %s.' % (len(o72), ADDED, sp(m1_72), sp(m0_72), src(o72)))
    w('- oldread, the %d intervals of bwx12 and bwx11 at 8000 MT/s: mesh 1 gave %s GB/s and mesh 0 gave %s GB/s %s. '
      'Against these rows mesh 1 is higher and mesh 0 is lower in every 7200 MT/s interval.'
      % (len(o80), sp(m1_80), sp(m0_80), src(o80)))
    w('- The same without part C (rule F2 points 2 and 3, decision (r) in section 2): the %d oldread intervals of '
      'part L, of control I (%s) and of F72d12, %s, gave %s GB/s on mesh 1 and %s GB/s on mesh 0. Against the same '
      '8000 MT/s rows mesh 1 is higher and mesh 0 is lower in every one of these intervals too.'
      % (len(o72n), ADDED, F72_WHAT, sp(m1_n), sp(m0_n)))
    w('- The same without part C and without control I: the %d oldread intervals of part L and of F72d12 gave '
      '%s GB/s on mesh 1 and %s GB/s on mesh 0. Against the same 8000 MT/s rows mesh 1 is higher and mesh 0 is '
      'lower in every one of these intervals too. So the result does not rest on control I.'
      % (len(o72p), sp(m1_p), sp(m0_p)))
    need(overlap(m1_x, m1_72) and overlap(m0_x, m0_72) and overlap(m1_x, m1_n) and m0_n['hi'] < m0_x['lo'],
         'runner bwx rows: both mesh ranges overlap with part C; without part C mesh 1 overlaps and mesh 0 lies below')
    w('- This does not hold in full against the rows of the first runner bwx at 8000 MT/s. There mesh 1 gave %s GB/s '
      'and mesh 0 gave %s GB/s (%d intervals) %s. With part C, both 7200 MT/s ranges overlap these ranges. Without '
      'part C, the mesh 1 ranges overlap, and the mesh 0 range at 7200 MT/s ends %s GB/s below the mesh 0 range of '
      'runner bwx.' % (sp(m1_x), sp(m0_x), len(oxx), src(oxx), g(m0_x['lo'] - m0_n['hi'])))
    w('- So the split between the meshes also moved between visits at 8000 MT/s. Insufficient data: whether the '
      'memory speed changes the split. Runs in several boots per speed would resolve it.')
    w('')

    # ---- 4.8 record only
    w('### 4.8 Record only: read_nop96, read_nop256, read_1pl')
    w('')
    w('Total in GB/s, lowest to highest interval. No statement is made from this table.')
    w('')
    rows = []
    for k in ('read_nop96', 'read_nop256', 'read_1pl'):
        row = [k]
        for d in ('rerun-L', 'control-I', 'F72d12', 'L-1'):
            rs = sel(recs, dataset=d, kernel=k)
            row.append('%s (n=%d)' % (sp(rng(rs)), len(rs)))
        rows.append(row)
    L.extend(table(['Kernel', 'Part L, 7200 MT/s', 'Control I (%s), 7200 MT/s' % ADDED, 'F72d12, 7200 MT/s, same boot',
                    'L-1 (w120-R8), 8000 MT/s'], rows))

    # ---- 4.9 verdict
    w('### 4.9 Verdict for Q2')
    w('')
    by, dist = c['byst'], c['dist']
    oth = c['byst_other']
    pcv, kF1, kI1 = c['partC_view'], c['kF1'], c['kI1']
    # limit of the visit F72d12 (section 4.6): its process list shows a busy kernel thread shortly before the launch
    need(fenv['top'][0][1] > 10, 'process list of F72d12 shows a busy process')
    c['f72_limit'] = ('F72d12 is an idle start only by the load-average rule of this sheet: its process list, written '
                      '%.0f s before the launch, shows %s at %s %%CPU (section 4.6).'
                      % ((f72la['utc'] - fenv['start']).total_seconds(), fenv['top'][0][2], fenv['top'][0][1]))
    side = lambda k, n72: '7200 MT/s: %s GB/s, n = %s. 8000 MT/s: %s GB/s, n = %s' % (sp(k['a']), n72, sp(k['b']), nn(k['b']))
    V['q2_old_read'] = (
        'Old read kernel. Part A (bw_old read): "%s" (%s). The test cannot exclude a difference of about %s %% (est. '
        'from one boot), which is the width of the 8000 MT/s range. Part C (oldread): "%s" (%s). There the test '
        'cannot exclude a difference of about %s %% (est. from one boot). %s Part L (oldread): "%s" (%s). Part L is '
        'lower by %s GB/s at the nearest ends (%s %% '
        'of the lower end of the 8000 MT/s range, %s GB/s) and by %s GB/s between the medians (%s %% of the 8000 MT/s '
        'median, %s GB/s). Two other rows of the same line in the same 7200 MT/s boot overlap the 8000 MT/s range. '
        'F72d12 (%d process at %s UTC, before the rerun, load %.2f at launch) gave %s GB/s. Control I (%d processes, '
        'idle start, %s, %s) gave %s GB/s. So against the whole pool L-1 to L-4, only the range of part L, which '
        'started %.0f s after part A, lies below the 8000 MT/s range among the bwx12 runs. A view added after the '
        'numbers were seen splits the '
        '8000 MT/s pool by start state: the %d bwx12 processes of the pool that started %.0f s to %.0f s after a '
        '120-thread bwx12 process gave '
        '%s GB/s (%s), the highest oldread values of the pool. Part L is %s GB/s below them. Part C started %.0f s '
        'after 120-thread work too. It is %s GB/s below them at the nearest ends, and its %d position-matched '
        'intervals (cfwd, position 0) are %s GB/s below them. Limit: these %d processes are not all 8000 MT/s '
        'processes with that kind of start state. Against the other-binary processes that started after 120-thread '
        'work, part C overlaps (bwx11: %s GB/s, %s. Runner bwx, position 0: %s GB/s, %s). Part L lies below every '
        'oldread interval at 8000 MT/s with 12 modules that this sheet holds (the lowest is %s GB/s, row %s, process '
        '%s). So the 8000 MT/s rows do '
        'not show that a start after 120-thread work lowers the old read kernel. The data do not show that the boot '
        'or the memory speed is the cause: each memory speed has one boot. Insufficient data: why part L was lower. %s'
        % (cAo['wording'], side(cAo, nns(A72o)), pc(cAo['width']), cCo['wording'], side(cCo, nns(C72o)),
           pc(cCo['width']), F2_NOTE, cLo['wording'], side(cLo, nns(L72o)), g(c['oldL']['near']), pc(c['oldL']['near_pct']),
           g(cLo['b']['lo']), g(c['oldL']['mid']), pc(c['oldL']['mid_pct']), g(cLo['b']['med']), cFo['a']['procs'],
           hm(f72la['utc'])[:5], f72la['load1'], sp(cFo['a']), cIo['a']['procs'], ADDED, NOT_PLAN, sp(cIo['a']),
           evd['T72L1']['gap_s'], by['Bo']['procs'], by['gaps'][0], by['gaps'][-1], sp(by['Bo']), nn(by['Bo']),
           g(by['near']), pcv['gap'], g(pcv['near']), pcv['cf0']['n'], g(pcv['near_cf0']), by['Bo']['procs'],
           sp(oth['b11']), nn(oth['b11'], boots=False), sp(oth['bx0']), nn(oth['bx0'], boots=False),
           g(oth['low_o']['GBps']), oth['low_o']['dataset'], oth['low_o']['tag'], H1_MEAS))
    # new read kernel, part A: the two rounds are kept apart (rule V3)
    need([x['round'] for x in newread] == [1, 2] and all(len(x['above']) == 3 for x in newread),
         'bw_new read of session 1: one cell per round, every interval above the 8000 MT/s range of its round')
    rounds = ' '.join('Round %d: %s to %s GB/s above the upper end of the round-%d range (%s GB/s).'
                      % (x['round'], g(min(x['above'])), g(max(x['above'])), x['round'], g(x['b80']['hi'])) for x in newread)
    n72r = {nns(x['s1']) for x in newread}
    n80r = {nn(x['b80']) for x in newread}
    need(len(n72r) == 1 and len(n80r) == 1, 'bw_new read: the same n in both rounds')
    kAw = compare(Aao, c['hw']['P12a_wo'])
    need(not kAw['overlap'] and kAw['dist'] == kAao['dist'] > 0,
         'part C, asmread after oldread: above the pool without the interval with error records too')
    allv = rng(F72a + L72a + I72a)
    V['q2_new_read'] = (
        'New read kernel. Part A (bw_new read, session 1): outside the 8000 MT/s range of the same round in both '
        'rounds. %s n per round at 7200 MT/s: %s. n per round at 8000 MT/s: %s. The pass counts '
        'differ, so part A gives no exact size. '
        'Part L (asmread, the same loop, used in place of the new read kernel): "%s" (%s). Part C, asmread directly '
        'after oldread (crev, round 1, position 0): "%s" (%s). Part C is higher by %s GB/s at the nearest ends. This '
        'baseline matches in the kernel that ran directly before. It does not match in the position: asmread is at '
        'position 1 in rows L-1 to L-4. %s Two corrected hardware error records fall inside the 8000 MT/s interval '
        'with the lowest asmread value (%s GB/s). Without this interval the 8000 MT/s range is %s GB/s (%s), and no '
        'wording changes (sections 4.1 and 4.4). Part C '
        '(kernel read): %s. The same line in the same 7200 MT/s boot gave asmread %s GB/s at %s UTC (F72d12, before '
        'the rerun, n = %s). That is inside the range of the 8000 MT/s pool L-1 to L-4. Against L-1 alone it is '
        '%s GB/s higher. %s Control I (idle start, %s, %s) gave asmread %s GB/s (n = %s). That is also above every bwx12 '
        'row of the fixed 8000 MT/s list, by %s GB/s at the nearest ends (%s GB/s against L-1 alone). The three '
        'visits of the boot span %s GB/s. Inside '
        'this one boot at one memory speed, part L lies %s GB/s above F72d12 at the nearest ends and %s GB/s between '
        'the medians. That is more than the distance of part L to the 8000 MT/s range (%s GB/s at the nearest ends, '
        '%s GB/s between the medians). Between the farthest ends the order is the opposite (%s GB/s inside the boot '
        'against %s GB/s to the 8000 MT/s range). %s'
        % (rounds, sorted(n72r)[0], sorted(n80r)[0], cLa['wording'], side(cLa, nns(L72a)),
           kAao['wording'], side(kAao, nns(Aao)), g(kAao['dist']), F2_NOTE,
           g(c['hw']['low_a']['GBps']), sp(c['hw']['wo']), nn(c['hw']['wo']),
           NO_READ, sp(cFa['a']), hm(f72la['utc'])[:5], nns(F72a), g(kF1['dist']), c['f72_limit'], ADDED, NOT_PLAN, sp(cIa['a']),
           nns(I72a), g(cIa['dist']), g(kI1['dist']), sp(allv), g(dist['near_boot']),
           g(dist['med_boot']), g(dist['near_pool']), g(dist['med_pool']), g(dist['far_boot']), g(dist['far_pool']), ins))
    V['q2'] = V['q2_old_read'] + ' ' + V['q2_new_read']
    w('**Verdict, old read kernel.** ' + V['q2_old_read'])
    w('')
    w('**Verdict, new read kernel.** ' + V['q2_new_read'])
    w('')
    V['same_boot'] = dict(kernel='asmread, position 1, like.spec line', boot=try6['boot'], speed_MTps=try6['speed_MTps'],
                          F72d12=[rng(F72a)['lo'], rng(F72a)['hi']], part_L=[rng(L72a)['lo'], rng(L72a)['hi']],
                          control_I=[rng(I72a)['lo'], rng(I72a)['hi']], control_I_note='%s, %s' % (ADDED, NOT_PLAN),
                          spread_GBps=round(spread, 3), pool_8000_L1_to_L4=[b12['lo'], b12['hi']],
                          distance_part_L_to_pool_GBps=round(cLa['dist'], 3),
                          part_L_above_F72d12_GBps=dict(nearest_ends=dist['near_boot'], medians=dist['med_boot'],
                                                        farthest_ends=dist['far_boot']),
                          part_L_above_pool_8000_GBps=dict(nearest_ends=dist['near_pool'], medians=dist['med_pool'],
                                                           farthest_ends=dist['far_pool']),
                          F72d12_process_list=dict(file=fd.rel(os.path.join(f72dir, 'env.txt')), written=hm(fenv['start']),
                                                   launch=hm(f72la['utc']), load1_at_launch=f72la['load1'],
                                                   top=[dict(user=t[0], pcpu=t[1], command=t[2], line=t[3]) for t in fenv['top']]))
    V['pool_8000_by_start_state'] = dict(
        note='view added after the numbers were seen, not part of the rules fixed before the run',
        below_load_1=dict(processes=by['names'](by['idle']), oldread=[by['Io']['lo'], by['Io']['hi']],
                          asmread=[by['Ia']['lo'], by['Ia']['hi']], n_intervals=by['Io']['n'], n_processes=by['Io']['procs']),
        after_120_thread_work=dict(processes=by['names'](by['busy']), gap_s=[by['gaps'][0], by['gaps'][-1]],
                                   load1=[by['loads_busy'][0], by['loads_busy'][-1]], oldread=[by['Bo']['lo'], by['Bo']['hi']],
                                   asmread=[by['Ba']['lo'], by['Ba']['hi']], n_intervals=by['Bo']['n'],
                                   n_processes=by['Bo']['procs']),
        part_L_oldread_below_second_group_GBps=by['near'], part_L_asmread_above_second_group_GBps=by['asm_near'],
        part_C=dict(start_state='every process started %.0f s after a 120-thread bwx12 process of the rerun (%s)'
                                % (pcv['gap'], ', '.join(pcv['prev'])), load1=[pcv['loads'][0], pcv['loads'][-1]],
                    oldread=[pcv['all']['lo'], pcv['all']['hi']], n_intervals=pcv['all']['n'],
                    n_processes=pcv['all']['procs'], oldread_below_second_group_GBps=pcv['near'],
                    oldread_cfwd_position_0=[pcv['cf0']['lo'], pcv['cf0']['hi']],
                    n_intervals_cfwd_position_0=pcv['cf0']['n'],
                    oldread_cfwd_position_0_below_second_group_GBps=pcv['near_cf0'],
                    overlaps_group_below_load_1=True,
                    limit='"second group" is the group after_120_thread_work: bwx12 processes of the pool L-1 to L-4 '
                          'only. Against the other-binary processes with that kind of start state '
                          '(other_binary_after_120_thread_work) oldread of part C overlaps',
                    overlaps_other_binary_after_120_thread_work=True),
        other_binary_after_120_thread_work=dict(
            note='8000 MT/s processes of other binaries that started after a 120-thread process of the same binary. '
                 'They are not part of the pool L-1 to L-4. oldread at position 0',
            bwx11=dict(processes=', '.join('%s %s' % b['key'] for b in oth['busy11']),
                       gap_s=sorted({b['gap'] for b in oth['busy11']}),
                       load1=[min(b['load'] for b in oth['busy11']), max(b['load'] for b in oth['busy11'])],
                       oldread=[oth['b11']['lo'], oth['b11']['hi']], n_intervals=oth['b11']['n'],
                       n_processes=oth['b11']['procs'], part_C_oldread_overlaps=True),
            runner_bwx=dict(rows=', '.join(BWX), load1=oth['bx0_load'],
                            oldread=[oth['bx0']['lo'], oth['bx0']['hi']], n_intervals=oth['bx0']['n'],
                            n_processes=oth['bx0']['procs'], part_C_oldread_overlaps=True)),
        part_L_below_every_oldread_interval_8000_12_modules=dict(
            part_L_highest_GBps=by['L_hi'], lowest_8000_GBps=oth['low_o']['GBps'], lowest_8000_dataset=oth['low_o']['dataset'],
            lowest_8000_process=oth['low_o']['tag'], n_intervals_8000=oth['n_allo']))
    V['part_A_thread_rates'] = [dict(kernel='%s %s' % (t['x']['binary'], t['x']['kernel']), round=t['x']['round'],
                                     nearest_ends_by_120_x_avg_GBps_est=round(t['est'], 1),
                                     nearest_ends_by_aggregate_GBps=round(t['agg'], 2)) for t in c['thr']]

    # =============================================================================== 5
    w('## 5. Record only: write, copy, asmwrite, asmcopy of part A')
    w('')
    w('- No statement is made from these rows (rule V3). FINDINGS.md section F1 shows that the whole-pass stop rule '
      'at %s moves the write totals %s.' % (secs(sel(recs, dataset='rerun-A')), ref(os.path.join(W15, 'FINDINGS.md'))))
    w('- A cell shows n: lowest / median / highest rate in GB/s. The copy kernels count read plus written bytes.')
    w('')
    rows = []
    for k in ('write', 'copy', 'asmwrite', 'asmcopy'):
        for b in ('bw_old', 'bw_new'):
            row = [k, b]
            for cond in (dict(dataset='A-1'), dict(dataset='rerun-A', session=1), dict(dataset='rerun-A', session=2),
                         dict(dataset='rerun-A', session=3)):
                rs = sel(recs, binary=b, kernel=k, **cond)
                a = rng(rs)
                row.append('%d: %s / %s / %s' % (a['n'], g(a['lo']), g(a['med']), g(a['hi'])))
            rows.append(row)
    L.extend(table(['Kernel', 'Binary', '2026-11-13 (A-1), 8000 MT/s', 'Session 1, 7200 MT/s', 'Session 2, 7200 MT/s',
                    'Session 3, 7200 MT/s'], rows))

    # =============================================================================== 6
    w('## 6. What is established, what is not, and hypotheses')
    w('')
    w('### Established')
    w('')
    nck = len(D['checks'])
    need(all(k['ok'] for k in D['checks']), 'all integrity checks pass')
    r2 = 0
    cells = 0
    for s_ in (1, 2, 3):
        for b, k in (('bw_new', 'read'), ('bw_old', 'asmread'), ('bw_new', 'asmread')):
            a1_, a2_ = (sel(recs, dataset='rerun-A', session=s_, round=rd, binary=b, kernel=k) for rd in (1, 2))
            cells += 1
            r2 += rng(a2_)['lo'] > rng(a1_)['hi']
    est = [
        'The rerun ran in boot %s with 12 memory modules (MemTotal %d kB in every state line). The same boot was '
        'recorded with 12 modules at 7200 MT/s at %s (section 1.2).' % (try6['boot'][:8], try6['memtotal_kB'], hm(try6['utc'])),
        'The run is complete: all %d integrity checks pass (section 1.4).' % nck,
        'Q1: the new read kernel is below the old read kernel in every pair of parts A and C. asmread is below the '
        'old read kernel in every pair of parts L and C (section 3.4).',
        'The size of the drop is not one value. Part L (asmread): %s. Part C: read after oldread %s, read after '
        'asmread %s, asmread after read %s, asmread as first interval %s, asmread after oldread %s. Control I (%s): '
        '%s. F72d12, the earlier run of the same boot: %s (section 3.4).'
        % (pcr(c['dl']), pcr(CG['read after oldread'][1]), pcr(CG['read after asmread'][1]), pcr(CG['asmread after read'][1]),
           pcr(CG['asmread first'][1]), pcr(CG['asmread after oldread'][1]), ADDED, pcr(c['di']), pcr(c['df'])),
        'Q2, old read kernel: against the whole 8000 MT/s pool (A-1 to A-3 for part A, L-1 to L-4 for the bwx12 '
        'rows) its range overlaps in part A, in part C, in control I (%s) and in F72d12. Only the range of part L '
        'lies below the pool, by %s GB/s at the nearest ends and by %s GB/s between the medians. In the view by start '
        'state (added after the numbers were seen), part C also lies below the %d bwx12 processes of the pool L-1 to '
        'L-4 that started after 120-thread work, by %s GB/s at the nearest ends. Against the other-binary processes '
        'with that kind of start state part C overlaps (section 4.2). The comparison of part C with 8000 MT/s '
        'follows decision (r) in section 2: rule F2 points 2 and 3 would not make it.'
        % (ADDED, g(c['oldL']['near']), g(c['oldL']['mid']), by['Bo']['procs'], g(pcv['near'])),
        'Q2, load-only loop: in session 1 of part A it ran above the 8000 MT/s intervals of the same round (rows A-1 '
        'and A-2). In part L, in control I (%s) and in the group "asmread after oldread" of part C it ran above every '
        'bwx12 row of the fixed 8000 MT/s list, L-1 to L-4 (sections 4.3 to 4.5). The comparison of part C with '
        '8000 MT/s follows decision (r) in section 2: rule F2 points 2 and 3 would not make it.' % ADDED,
        'In the one 7200 MT/s boot the load-only loop gave %s GB/s at %s and %s GB/s at %s to %s for the same '
        'argument line (section 4.6).' % (sp(rng(F72a)), hm(f72la['utc']), sp(rng(L72a)), hm(tL[0]), hm(tL[-1])),
        'In part A the second-round process of a load-only kernel is above the first-round process, without overlap, '
        'in %d of %d cells (3 sessions x bw_new read, bw_old asmread, bw_new asmread, see the table of section 3.1).' % (r2, cells),
        'Against the bwx12 and bwx11 rows at 8000 MT/s, oldread at 7200 MT/s read more on mesh 1 and less on mesh 0 '
        'in every interval. This holds with part C (%d intervals) and without part C (%d intervals of part L, of '
        'control I (%s) and of F72d12, the earlier run of the same boot). It also holds without part C and without '
        'control I (%d intervals of part L and of F72d12). This sheet shows part C next to 8000 MT/s rows by '
        'decision (r) in section 2. Rule F2 points '
        '2 and 3 would not do it. Against the rows of runner bwx the result does not hold in full: the mesh 1 ranges overlap, '
        'and the mesh 0 ranges overlap when part C is included (section 4.7, looked at after the numbers were seen).'
        % (c['mesh']['n_all'], c['mesh']['n_noC'], ADDED, c['mesh']['n_noCI']),
        'The bwx12 row F72d12 ran in the boot of the rerun: its process lies between two readings of the same boot id '
        '(section 4.1).',
        'Hardware error records at 8000 MT/s: 2 corrected records fall inside the interval with the lowest asmread '
        'value of the pool L-1 to L-4, and 2 fall before or inside the first oldread interval of row L-1 (section '
        '4.1). No wording by rule V1 point 2 changes without the first of these intervals (section 4.4).',
    ]
    for i, t in enumerate(est, 1):
        w('%d. %s' % (i, t))
    w('')
    w('### Not established')
    w('')
    hwx = c['hw']['cmp']
    sgn = lambda x: '0.00' if float(g(x)) == 0 else (g(x) if x < 0 else '+' + g(x))      # a signed difference
    notest = [
        ins,
        'Insufficient data: why the load-only loop differs between the three visits of the same boot (section 4.6). '
        'The measurements named under H1 and H2 would resolve it.',
        'Insufficient data: why old read was %s GB/s in part L and %s GB/s in control I (%s). The 8000 MT/s rows do '
        'not point to the start state: there the %d bwx12 processes that started after 120-thread work gave higher '
        'oldread values (%s GB/s, %s) than the %d processes that started at a load below 1.0 (%s GB/s, %s) (section '
        '4.2, view added after the numbers were seen). The measurement named under H1 would resolve it.'
        % (sp(rng(L72o)), sp(rng(I72o)), ADDED, by['Bo']['procs'], sp(by['Bo']), nn(by['Bo'], boots=False),
           by['Io']['procs'], sp(by['Io']), nn(by['Io'], boots=False)),
        NO_READ + '. A run of cfwd.spec and crev.spec at 8000 MT/s would resolve it (needs a change of the firmware '
        'setting and a reboot, so root and approval).',
        'Insufficient data: whether hardware error records occurred during the rerun. A count of the "[Hardware Error]" '
        'lines of the kernel log would resolve it (needs root).',
        'Insufficient data: a direct reading of the memory speed during the rerun. `sudo dmidecode -t 17` would '
        'resolve it (needs root). The proof used here is the equal boot id.',
        'Insufficient data: whether the one-thread phase of 2026-11-13 changes the 120-thread rates (section 1.5).',
        'Insufficient data: whether the buffers of part A lay on 2 MiB pages. bandwidth.c does not record it. A run '
        'of the same kernels with bwx12 records it in "P" rows.',
        'Insufficient data: the applied memory speed in the boot of the 8000 MT/s baselines. That boot is over, so the '
        'reading cannot be taken any more. The firmware setting of that boot is on record (section 1.5, point 10).',
        'Insufficient data: the firmware settings in the boot of the rerun, apart from the memory speed. The two '
        'TXREQ settings were set back before the 7200 MT/s reboot test, and the settings list saved after that is '
        'equal to the list of the baseline boot in its %d readable values. No list was saved in the boot of the '
        'rerun. A settings list saved in that boot would resolve it (needs root) (section 1.5, point 13).'
        % c['fw']['readable'],
        'Insufficient data: whether a corrected hardware error record lowers the rate of an interval (hypothesis in '
        'section 4.1). The processes of rows L-1 to L-4, R0 and R0b hold %d intervals to which records can be '
        'assigned (all kernels and positions, view added after the numbers were seen). %d of them are more than '
        '%g GB/s below the same kernel at the same position in the other round of their process (%s GB/s). The other '
        '%d differ from it by less than %g GB/s (%s to %s GB/s). Without records the two rounds of the same processes '
        'differ by up to %s GB/s. This comparison is not a test. A run that stores the kernel log time of every '
        'record beside the interval times would resolve it (needs root).'
        % (hwx['n'], len(hwx['low']), hwx['lim'], hwx['lst']([g(-r['diff']) for r in reversed(hwx['low'])]),
           len(hwx['rest']), hwx['lim'], sgn(min(r['diff'] for r in hwx['rest'])),
           sgn(max(r['diff'] for r in hwx['rest'])), g(abs(hwx['cmax']['diff']))),
    ]
    V['insufficient_data'] = notest
    for i, t in enumerate(notest, 1):
        w('%d. %s' % (i, t))
    w('')
    w('### Hypotheses (not tested)')
    w('')
    r0 = {t: sel(recs, dataset='R0', tag=t, kernel='asmread') for t in ('p1', 'p2')}
    l2 = {t: sel(recs, dataset='L-2', tag=t, kernel='asmread', pos=1) for t in ('p1nop', 'p2add')}
    l2load = {t: D['rx']['L-2']['launches'][t]['load1'] for t in l2}
    need(rng(l2['p2add'])['hi'] < rng(l2['p1nop'])['lo'] and l2load['p2add'] > 1 > l2load['p1nop'],
         'row L-2: asmread of p2add (after 120-thread work) below p1nop (load below 1.0)')
    hyp = [
        'H1, start state. The rate of the load-only loop depends on the work that ran shortly before the launch. '
        'What fits: part L (launched %.0f s after part A) gave %s GB/s, and control I (idle start, %s, %s) gave '
        '%s GB/s. In part A '
        'the second round is above the first in %d of %d load-only cells. What does not fit: at 8000 MT/s process p2 '
        'of row R0 (other binary bwx11, load %.2f at launch) gave %s GB/s, below p1 (load %.2f) with %s GB/s. The '
        'bwx12 rows of the fixed list do not fit either (section 4.2, view by start state): the %d processes that started '
        '%.0f s to %.0f s after a 120-thread bwx12 process (%s, load %.2f to %.2f) gave asmread %s GB/s (%s), and the '
        '%d processes that started at a load below 1.0 (%s) gave %s GB/s (%s). The two ranges overlap. Inside row '
        'L-2, p2add (load %.2f) gave %s GB/s, below p1nop (load %.2f) with %s GB/s. For oldread the order is the '
        'opposite at 8000 MT/s: the same %d processes gave %s GB/s, above the %s GB/s of the %d processes at a load '
        'below 1.0. At 7200 MT/s oldread of part L (%s GB/s) was below control I (%s GB/s). Also, in part A the '
        'first-round process of bw_new read gave %s GB/s in session 1 (idle start), above session 2 (%s GB/s) and '
        'session 3 (%s GB/s), which started %.0f s after 120-thread work. Measurement that would confirm or reject '
        'it: the like.spec line, alternating between an idle start and a start directly after part A, at least 3 '
        'times each, in one boot.'
        % (evd['T72L1']['gap_s'], sp(rng(L72a)), ADDED, NOT_PLAN, sp(rng(I72a)), r2, cells, r0['p2'][0]['load1_at_launch'], sp(rng(r0['p2'])),
           r0['p1'][0]['load1_at_launch'], sp(rng(r0['p1'])),
           by['Ba']['procs'], by['gaps'][0], by['gaps'][-1], by['names'](by['busy']), by['loads_busy'][0], by['loads_busy'][-1],
           sp(by['Ba']), nn(by['Ba'], boots=False), by['Ia']['procs'], by['names'](by['idle']), sp(by['Ia']),
           nn(by['Ia'], boots=False), l2load['p2add'], ' and '.join(g(r['GBps']) for r in l2['p2add']), l2load['p1nop'],
           ' and '.join(g(r['GBps']) for r in l2['p1nop']), by['Bo']['procs'], sp(by['Bo']), sp(by['Io']), by['Io']['procs'],
           sp(rng(L72o)), sp(rng(I72o)),
           sp(rng(N['pa'][0]['new'])), sp(rng(N['pa'][2]['new'])),
           sp(rng(N['pa'][4]['new'])), evd['T72A2']['gap_s']),
        'H2, time since boot. The rate of the load-only loop rises with the time since boot or with the work done '
        'since boot. What fits: F72d12 ran %s after the first kernel log line of the boot and gave the lowest values. '
        'The first process of the rerun started %s after that line. Limit: F72d12 also differs from control I (%s, %s) '
        'in its process list (%s at %s %%CPU, %.0f s before the launch, section 4.6). So the time since boot and the '
        'start phase of the machine are not separated. Measurement: repeat the idle-start line of '
        'control I some hours later in the same boot, and once directly after a reboot (a reboot needs approval).'
        % (dur((f72la['utc'] - try6['first_log_utc']).total_seconds()), dur((c['evd']['T72A1']['first'] - try6['first_log_utc']).total_seconds()),
           ADDED, NOT_PLAN, fenv['top'][0][2], fenv['top'][0][1], (f72la['utc'] - fenv['start']).total_seconds()),
        'H3, memory speed. 7200 MT/s raises the rate of the load-only loop. The rerun cannot separate this from H1, '
        'H2 and the boot. Measurement: the like.spec line in several boots per speed (needs reboots and a change of '
        'the firmware setting).',
        'H4, pass counts in part A. An interval with %d passes has 6 passes on the %d threads of mesh 0 and 5 passes '
        'on the %d threads of mesh 1 (%d x 6 + %d x 5 = %d). threads120.csv has no row per thread, so the split is '
        'not proven. Measurement: part A with the option --per-thread.'
        % (64 * 6 + 56 * 5, 64, 56, 64, 56, 64 * 6 + 56 * 5),
        'H5, load values. The high load values at the launches come from the rerun\'s own earlier processes '
        '(section 1.3).',
    ]
    need((64 * 6 + 56 * 5) in {r['passes'] for r in sel(recs, dataset='rerun-A', binary='bw_new', kernel='read')}, 'pass count of H4 occurs')
    need((N['pa'][0]['session'], N['pa'][2]['session'], N['pa'][4]['session']) == (1, 2, 3) and N['pa'][0]['round'] == 1
         and rng(N['pa'][0]['new'])['lo'] > max(rng(N['pa'][2]['new'])['hi'], rng(N['pa'][4]['new'])['hi']),
         'first-round bw_new read of session 1 above sessions 2 and 3')
    V['hypotheses'] = hyp
    for t in hyp:
        w('- ' + t)
    w('')
