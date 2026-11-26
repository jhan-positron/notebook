#!/usr/bin/env python3
"""facts.py ASCT.json BASELINE.json OUT.json: every derived number and every verdict of the report,
computed by the rules of DECISIONS.md. The report generator only formats what this file computes."""
import json
import statistics as st
import sys

SIZES = [32768, 1048576, 1572864, 2097152, 2621440, 3145728, 4194304, 5242880, 6291456, 8388608, 12582912,
         16777216, 25165824, 33554432, 268435456, 1073741824]
FIT_SIZES = [b for b in SIZES if 1048576 <= b <= 33554432]
CPUS = [2, 41]
NOPS = [0, 1, 2, 3, 4, 6, 8, 10, 15, 20, 30, 40, 50, 70, 100, 180]
PREFETCH = ['l1d_cache_hwprf', 'l2d_cache_hwprf', 'l2d_cache_l1hwprf', 'l2d_cache_refill_l1hwprf', 'l1d_cache_prfm',
            'l2d_cache_prfm', 'l1d_cache_refill_prfm', 'l2d_cache_refill_prfm', 'prf_spec']
M1, M8 = 1048576, 8388608


def label(b):
    for unit, n in (('GiB', 1 << 30), ('MiB', 1 << 20), ('KiB', 1 << 10)):
        if b >= n:
            v = b / n
            return f'{v:g} {unit}'
    return f'{b} B'


def stat(v):
    return {'median': st.median(v), 'lo': min(v), 'hi': max(v), 'n': len(v)} if v else None


def linfit(pts):
    n = len(pts)
    mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    b = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    a = my - b * mx
    return a, b, max(abs(p[1] - (a + b * p[0])) for p in pts)


def main():
    A = json.load(open(sys.argv[1]))
    B = json.load(open(sys.argv[2]))
    F = {'sizes': SIZES, 'labels': {str(b): label(b) for b in SIZES}, 'cpus': CPUS}

    # ---------------- one core ----------------
    S = next((x for x in A['single'] if x['cells']), None)
    NC = next((x for x in A['single'] if x.get('nops_counted')), None)     # part NC ran in its own folder
    one = {}
    if S:
        for cpu in CPUS:
            c = {'asct': {}, 'old': {}, 'new': {}, 'newc': {}, 'cnt': {}}
            for b in SIZES:
                c['asct'][b] = stat(S['cells'].get(f'{cpu}.{b}', []))
                for key, name in (('old', 'oldread'), ('new', 'asmread'), ('newc', 'read')):
                    v = B['single'].get(f'{name}.{cpu}.{b}')
                    c[key][b] = {'median': v['median'], 'lo': v['lo'], 'hi': v['hi'], 'n': v['processes'], 'src': 'final8'} if v else None
                if b == 1 << 30 and cpu == 2:   # only the first run of 2026-11-13 has 1 GiB, and only CPUs 0 and 2
                    for key, name in (('old', 'bw_old'), ('newc', 'bw_new')):
                        v = B['first'].get(f'{name}.read.{cpu}.{b}')
                        if v:
                            c[key][b] = {'median': v['median'], 'lo': v['lo'], 'hi': v['hi'], 'n': v['n'], 'src': 'first'}
                cc = S['counted'].get(f'{cpu}.{b}')
                if cc:
                    c['cnt'][b] = {n: st.median(v) for n, v in cc['ev'].items()}
                    c['cnt'][b]['_rate'] = st.median(cc['rate'])
                    c['cnt'][b]['_rate_lo'], c['cnt'][b]['_rate_hi'] = min(cc['rate']), max(cc['rate'])
            a1, a8 = c['asct'][M1], c['asct'][M8]
            c['ratio_asct'] = a8['median'] / a1['median'] if a1 and a8 else None
            c['ratio_new'] = c['new'][M8]['median'] / c['new'][M1]['median']
            c['ratio_old'] = c['old'][M8]['median'] / c['old'][M1]['median']
            c['PA1'] = None if c['ratio_asct'] is None else c['ratio_asct'] < 0.90
            pts = [(c['cnt'][b]['l2d_cache_refill'], c['cnt'][b]['cpu_cycles']) for b in FIT_SIZES
                   if b in c['cnt'] and 'l2d_cache_refill' in c['cnt'][b] and 'cpu_cycles' in c['cnt'][b]]
            if len(pts) >= 3:
                a, bb, res = linfit(pts)
                c['fit'] = {'a': a, 'b': bb, 'maxres': res, 'n': len(pts)}
            zpts = [(B['zs'][f'asmread.{cpu}.{b}']['r'], B['zs'][f'asmread.{cpu}.{b}']['cyc']) for b in FIT_SIZES if f'asmread.{cpu}.{b}' in B['zs']]
            a, bb, res = linfit(zpts)
            c['fit_new'] = {'a': a, 'b': bb, 'maxres': res, 'n': len(zpts)}
            # clock implied by counted cycles and the rate of the same processes
            ghz = [c['cnt'][b]['cpu_cycles'] * c['cnt'][b]['_rate'] / 64 for b in SIZES if b in c['cnt'] and 'cpu_cycles' in c['cnt'][b]]
            c['ghz'] = [min(ghz), max(ghz)] if ghz else None
            # counted against uncounted rate
            dev = [abs(c['cnt'][b]['_rate'] / c['asct'][b]['median'] - 1) * 100 for b in SIZES if b in c['cnt'] and c['asct'][b]]
            c['counted_vs_plain_maxpct'] = max(dev) if dev else None
            # rule R-A3
            pf = {}
            for name in PREFETCH:
                try:
                    v6, v8, v12 = (c['cnt'][b][name] for b in (6291456, M8, 12582912))
                except KeyError:
                    continue
                lo, hi = min(v6, v12), max(v6, v12)
                ext = 0.10 * (v6 + v12) / 2
                pf[name] = {'v6': v6, 'v8': v8, 'v12': v12, 'different': not (lo - ext <= v8 <= hi + ext)}
            c['prefetch'] = pf
            one[cpu] = c
        # part N and prediction P-A4
        pad = {}
        for cpu in CPUS:
            for nn in (1, 2, 4, 8):
                row = {b: stat(S.get('nops', {}).get(f'{nn}.{cpu}.{b}', [])) for b in (32768, M1, M8)}
                if row[M1] and row[M8]:
                    row['ratio'] = row[M8]['median'] / row[M1]['median']
                    row['applies'] = row[M1]['median'] < 60
                    row['holds'] = abs(row['ratio'] - 1) <= 0.03 if row['applies'] else None
                    pad[f'{cpu}.{nn}'] = row
        F['pad'] = pad
        F['PA4'] = {str(cpu): (None if not any(v['applies'] for k, v in pad.items() if k.startswith(f'{cpu}.')) else
                               all(v['holds'] for k, v in pad.items() if k.startswith(f'{cpu}.') and v['applies'])) for cpu in CPUS}
        # part NC: the padded loop with counters, and prediction P-A5
        padcnt = {}
        for cpu in CPUS:
            for nn in (1, 2, 4):
                for b in (M1, M8):
                    cc = (NC or S).get('nops_counted', {}).get(f'{nn}.{cpu}.{b}')
                    if cc:
                        d = {n: st.median(v) for n, v in cc['ev'].items()}
                        d['_rate'] = st.median(cc['rate'])
                        d['_rate_lo'], d['_rate_hi'], d['_n'] = min(cc['rate']), max(cc['rate']), len(cc['rate'])
                        padcnt[f'{cpu}.{nn}.{b}'] = d
        F['padcnt'] = padcnt
        pa5 = {}
        for cpu in CPUS:
            k = padcnt.get(f'{cpu}.2.{M8}')
            base = one[cpu]['cnt'].get(M8, {}).get('l2d_cache_lmiss_rd')
            if k and 'l2d_cache_lmiss_rd' in k and base:
                pa5[str(cpu)] = {'n0': base, 'n2': k['l2d_cache_lmiss_rd'], 'ratio': k['l2d_cache_lmiss_rd'] / base,
                                 'holds': k['l2d_cache_lmiss_rd'] < 0.8 * base}
        F['PA5'] = pa5
        F['RA3_different'] = sorted(n for n in PREFETCH if all(n in one[c]['prefetch'] and one[c]['prefetch'][n]['different'] for c in CPUS))
        F['RA3_counted'] = sorted(n for n in PREFETCH if all(n in one[c]['prefetch'] for c in CPUS))
        F['single_launch'] = S['launches']
        F['single_problems'] = S['problems']
        F['single_folder'] = S['folder']
        if NC:
            F['nc_launch'], F['nc_problems'], F['nc_folder'] = NC['launches'], NC['problems'], NC['folder']
    if S:
        F['cpu41_over_cpu2_pct'] = {b: (one[41]['asct'][b]['median'] / one[2]['asct'][b]['median'] - 1) * 100 for b in SIZES}
    F['one'] = {str(k): v for k, v in one.items()}
    F['vendor_ratio'] = {}
    for name, v in B['vendor'].items():
        d = dict(v['sweep'])
        F['vendor_ratio'][name] = {'m1': d[M1], 'm8': d[M8], 'ratio': d[M8] / d[M1]}

    # ---------------- whole chip ----------------
    Cc = None
    if A['chip']:        # several whole-chip folders: every surviving process of every folder counts
        Cc = {'runs': {}, 'mix': {}, 'counted': {}, 'problems': [], 'folder': [c['folder'] for c in A['chip']], 'launches': {}}
        for c in A['chip']:
            for k, v in c['runs'].items():
                Cc['runs'].setdefault(k, []).extend(v)
            for k, v in c.get('mix', {}).items():
                Cc['mix'].setdefault(k, []).extend(v)
            Cc['counted'].update(c['counted'])
            Cc['problems'] += [f'{c["folder"]}: {x}' for x in c['problems']]
        ls = [c['launches'] for c in A['chip']]
        Cc['launches'] = {'n': sum(x['n'] for x in ls), 'load1_min': min(x['load1_min'] for x in ls), 'load1_max': max(x['load1_max'] for x in ls),
                          'runnable_max': max(x['runnable_max'] for x in ls), 'rc_nonzero': sum(x['rc_nonzero'] for x in ls),
                          'rc_count': sum(x['rc_count'] for x in ls), 'per_folder': {c['folder']: c['launches'] for c in A['chip']}}
    chip = {}
    if Cc:
        def cell(key):
            runs = Cc['runs'].get(key)
            if not runs:
                return None
            d = stat([r['total'] for r in runs])
            d['mesh0'] = st.median(r['mesh0'] for r in runs)
            d['mesh1'] = st.median(r['mesh1'] for r in runs)
            for m in ('thr0', 'thr1'):
                v = [r[m] for r in runs if r[m]]
                d[m] = [min(x[0] for x in v), st.median(x[1] for x in v), max(x[2] for x in v)] if v else None
            d['sec'] = [min(r['sec'][0] for r in runs), max(r['sec'][1] for r in runs)]
            d['floor'] = st.median(r['floor'] for r in runs)
            return d
        dur = None
        for k in Cc['runs']:
            if k.startswith('6456.n0.d') and not k.endswith('d0.25'):
                dur = k.split('.d', 1)[1]
        chip['dur'] = dur
        chip['base'] = cell(f'6456.n0.d{dur}')
        chip['default'] = cell('6456.n0.d0.25')
        chip['nops'] = {n: cell(f'6456.n{n}.d{dur}') for n in NOPS if cell(f'6456.n{n}.d{dur}')}
        chip['layouts'] = {lay: {n: cell(f'{lay}.n{n}.d{dur}') for n in (0, 20)} for lay in ('6400', '0056', '5656')}
        fast = [n for n in NOPS if 1 <= n <= 40 and n in chip['nops'] and chip['nops'][n]['median'] >= 459]
        chip['PB1'] = None if not chip['base'] else chip['base']['median'] < 334
        chip['PB1_fail_hard'] = bool(chip['base'] and chip['base']['median'] >= 459)
        chip['PB2'] = bool(fast)
        chip['fastN'] = fast
        best = max(chip['nops'], key=lambda n: chip['nops'][n]['median']) if chip['nops'] else None
        chip['bestN'] = best
        l64, l56 = chip['layouts']['6400'][0], chip['layouts']['0056'][0]
        chip['PB3'] = {'6400': None if not l64 else 348.0 * 0.95 <= l64['median'] <= 351.0 * 1.05,
                       '0056': None if not l56 else 318.0 * 0.95 <= l56['median'] <= 321.7 * 1.05}
        chip['mix'] = {t: stat(v) for t, v in Cc.get('mix', {}).items()}
        cnt = {}
        for key, cc in Cc['counted'].items():
            ev = {}
            for name, per_set in cc['ev'].items():
                m0 = [v['mesh0'][1] for v in per_set.values() if v['mesh0']]
                m1 = [v['mesh1'][1] for v in per_set.values() if v['mesh1']]
                lo0 = [v['mesh0'][0] for v in per_set.values() if v['mesh0']]
                hi0 = [v['mesh0'][2] for v in per_set.values() if v['mesh0']]
                lo1 = [v['mesh1'][0] for v in per_set.values() if v['mesh1']]
                hi1 = [v['mesh1'][2] for v in per_set.values() if v['mesh1']]
                ev[name] = {'mesh0': st.median(m0) if m0 else None, 'mesh1': st.median(m1) if m1 else None,
                            'r0': [min(lo0), max(hi0)] if m0 else None, 'r1': [min(lo1), max(hi1)] if m1 else None}
            cnt[key] = {'ev': ev, 'totals': {s: v['total'] for s, v in cc['sets'].items()},
                        'mesh0': {s: v['mesh0'] for s, v in cc['sets'].items()}, 'mesh1': {s: v['mesh1'] for s, v in cc['sets'].items()}}
        chip['cnt'] = cnt
        F['chip_launch'] = Cc['launches']
        F['chip_problems'] = Cc['problems']
        F['chip_folder'] = Cc['folder']
    F['chip'] = chip

    # ---------------- mesh counters (root) ----------------
    mesh = {}
    for Mm in A['mesh']:
        for tag, t in Mm['tags'].items():
            per = {}
            for name, d in t['ev'].items():
                if name == 'dtc_cycles':
                    continue
                row = {}
                for m in ('mesh0', 'mesh1'):
                    if m in d:
                        row[m + '_per_s'] = d[m]['count'] / d[m]['sec']
                        if t['rate']:
                            row[m] = d[m]['count'] / (t['rate'] * 1e9 / 64 * d[m]['sec'])
                per[name] = row
            mesh[tag] = {'spec': t['spec'], 'rate': t['rate'], 'ev': per, 'folder': Mm['folder']}
        F.setdefault('mesh_problems', []).extend(f'{Mm["folder"]}: {p}' for p in Mm['problems'])
        F.setdefault('mesh_launch', {})[Mm['folder']] = Mm['launches']
    F['mesh'] = mesh
    F['prep'] = A['prep'][0] if A['prep'] else None
    json.dump(F, open(sys.argv[3], 'w'), indent=1)

    # short console view
    for cpu in CPUS:
        c = one.get(cpu)
        if not c:
            continue
        print(f'CPU {cpu}: ASCT 1 MiB {c["asct"][M1]["median"]:.2f} 8 MiB {c["asct"][M8]["median"]:.2f} ratio {c["ratio_asct"]:.3f} '
              f'P-A1 {c["PA1"]}; new ratio {c["ratio_new"]:.3f}; old ratio {c["ratio_old"]:.3f}; fit {c.get("fit")}; new fit {c["fit_new"]}')
        print('   GHz', c['ghz'], 'counted vs plain max %', c['counted_vs_plain_maxpct'])
    print('R-A3 different at 8 MiB:', F.get('RA3_different'), 'of', F.get('RA3_counted'))
    print('P-A4', F.get('PA4'), {k: (round(v[M1]['median'], 1), round(v[M8]['median'], 1), round(v['ratio'], 3)) for k, v in F.get('pad', {}).items()})
    if chip:
        print('chip base', chip['base'], 'P-B1', chip['PB1'], 'P-B2', chip['PB2'], chip['fastN'], 'best N', chip['bestN'], 'P-B3', chip['PB3'])
        print('nops', {n: round(v['median'], 1) for n, v in chip['nops'].items()})
        print('mix', {t: round(v['median'], 1) for t, v in chip['mix'].items()})
    print('mesh tags', list(mesh))


if __name__ == '__main__':
    main()
