#!/usr/bin/env python3
"""Per-token attention phase counters (kvwait stamps 7606-7627, worker 0) plus the
fence stamps, from one or more kvwait .bin files. Decode-only windows: between two
consecutive F3 ends (7600) with exactly one 7601, 7602, 7603, 7604, 7605 and exactly
one of each 7606..7627. Prints medians (us) of per-token sums and per-unit costs.

Tags (payload = value for this token on attention worker 0):
 7606 units_amx  7607 units_dotter  7608 units_empty  7609 k_tokens_dotter
 7610 pages  7611 ranges  7612 qpacks
 7613 cyc_qk_amx  7614 cyc_softmax_amx  7615 cyc_pv_amx  7616 cyc_state_amx
 7617 cyc_qk_dotter  7618 cyc_common_dotter  7619 cyc_pv_dotter
 7620 cyc_qpack  7621 cyc_region  7622 cyc_range  7623 cyc_sections_ready
 7624 cyc_sections_pending  7625 cyc_upstream_wait  7626 cyc_joins  7627 cyc_barrier
Usage: extract-sa.py [--check --arm mirror|canon|disable] [--tsc-ghz=2.7] file.bin [...]
"""
import struct, sys, statistics as st, json
NAMES = ['units_amx','units_dotter','units_empty','k_tokens_dotter','pages','ranges','qpacks',
         'cyc_qk_amx','cyc_softmax_amx','cyc_pv_amx','cyc_state_amx',
         'cyc_qk_dotter','cyc_common_dotter','cyc_pv_dotter',
         'cyc_qpack','cyc_region','cyc_range','cyc_sections_ready','cyc_sections_pending',
         'cyc_upstream_wait','cyc_joins','cyc_barrier']
TAG = {7606 + i: n for i, n in enumerate(NAMES)}
FENCE = (7600, 7601, 7602, 7603, 7604, 7605)

def load(path):
    b = open(path, 'rb').read()
    n = struct.unpack('<Q', b[:8])[0]
    recs = [struct.unpack_from('<QQQ', b, 8 + 24 * i) for i in range(min(n, (len(b) - 8) // 24))]
    recs.sort(key=lambda r: r[0])
    return recs

def windows(recs, ghz):
    c = 1e6 / (ghz * 1e9)
    by = {}
    for r in recs: by.setdefault(r[2], []).append(r)
    f3 = [t0 + d for t0, d, _ in by.get(7600, [])]
    need = list(FENCE[1:]) + list(TAG)
    idx = {t: 0 for t in need}
    rows = []
    for i in range(1, len(f3)):
        lo, hi = f3[i - 1], f3[i]
        got = {}
        ok = True
        for t in need:
            lst = by.get(t, [])
            sel = [r for r in lst if lo < r[0] <= hi]
            if len(sel) != 1: ok = False; break
            got[t] = sel[0]
        if not ok: continue
        row = {'period': (hi - lo) * c, 'attn': got[7605][1] * c}
        for t, n in TAG.items():
            v = got[t][1]
            row[n] = v * c if n.startswith('cyc_') else v
        rows.append(row)
    return rows

def med(v): return st.median(v) if v else float('nan')

def summarize(rows):
    out = {'windows': len(rows), 'period_us': med([r['period'] for r in rows]),
           'attn_us_7605': med([r['attn'] for r in rows])}
    for n in NAMES: out[n] = med([r[n] for r in rows])
    # per-unit costs (us) from per-token sums: divide medians of the sums (robust; ratios of medians)
    def ratio(a, b): return out[a] / out[b] if out[b] else float('nan')
    out['per_unit'] = {
        'amx_qk': ratio('cyc_qk_amx', 'units_amx'), 'amx_softmax': ratio('cyc_softmax_amx', 'units_amx'),
        'amx_pv': ratio('cyc_pv_amx', 'units_amx'), 'amx_state': ratio('cyc_state_amx', 'units_amx'),
        'dotter_qk': ratio('cyc_qk_dotter', 'units_dotter'), 'dotter_common': ratio('cyc_common_dotter', 'units_dotter'),
        'dotter_pv': ratio('cyc_pv_dotter', 'units_dotter'),
        'qpack': ratio('cyc_qpack', 'qpacks'),
    }
    out['per_unit']['amx_total'] = sum(out['per_unit'][k] for k in ('amx_qk','amx_softmax','amx_pv','amx_state'))
    out['per_unit']['dotter_total'] = sum(out['per_unit'][k] for k in ('dotter_qk','dotter_common','dotter_pv'))
    out['per_unit']['dotter_qk_per_ktoken_ns'] = 1e3 * out['cyc_qk_dotter'] / out['k_tokens_dotter'] if out['k_tokens_dotter'] else float('nan')
    hot = sum(out[n] for n in NAMES if n.startswith('cyc_') and n not in ('cyc_range','cyc_sections_ready','cyc_sections_pending'))
    out['sum_of_phases_us'] = hot
    out['coverage_of_7605'] = hot / out['attn_us_7605'] if out['attn_us_7605'] else float('nan')
    return out

if __name__ == '__main__':
    ghz = 2.7; check = False; arm = None; files = []
    a = sys.argv[1:]
    while a:
        x = a.pop(0)
        if x == '--check': check = True
        elif x == '--arm': arm = a.pop(0)
        elif x.startswith('--tsc-ghz='): ghz = float(x.split('=')[1])
        else: files.append(x)
    recs = []
    for f in files: recs += load(f)
    if check:
        present = {t for _, _, t in recs}
        missing = [t for t in list(FENCE) + list(TAG) if t not in present]
        rows = windows(recs, ghz)
        print('records:', len(recs), 'missing tags:', missing, 'decode windows:', len(rows))
        if missing or not rows: sys.exit(1)
        ua = med([r['units_amx'] for r in rows]); ud = med([r['units_dotter'] for r in rows])
        print(f'median units_amx {ua:.0f} units_dotter {ud:.0f}')
        if arm == 'disable' and ua != 0: print('FAIL: kill switch reports AMX units'); sys.exit(1)
        if arm in ('mirror', 'canon') and ua <= 0: print('FAIL: AMX arm reports no AMX units'); sys.exit(1)
        sys.exit(0)
    rows = windows(recs, ghz)
    if not rows: print('no decode windows'); sys.exit(1)
    print(json.dumps(summarize(rows), indent=1))
