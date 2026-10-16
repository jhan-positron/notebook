import json, collections, sys
sys.path.insert(0, '.')
from layer_timeline import DIR, union, total, clip, concurrency, subtract
for f, nl in (('base-tp2', 36), ('base-tp4', 36)):
    d = json.load(open(DIR + f + '.perfetto-trace.lanes.json'))
    for kind in ('decode', 'prefill'):
        p = d[kind]; spans = p['spans']
        savek = sorted(s['start_us'] for s in spans if s['name'] == 'Save K')
        wins = list(zip(savek, savek[1:])) if kind == 'decode' else [(savek[0], p['window_us'][1])]
        rows = []
        for w0, w1 in wins:
            sp = clip(spans, w0, w1)
            per = collections.defaultdict(list)
            for s in sp:
                if s['c'] == 'attention': per[s['utid']].append((s['a'], s['b']))
            n = len(per)
            conc = concurrency([union(v) for v in per.values()], w0, w1)
            au = union([iv for v in per.values() for iv in v])
            a_end = au[-1][1]
            full = sum(b - a for a, b, c in conc if c == n)
            # first time after reaching full count that count drops below n
            reached = False; drop = None
            for a, b, c in conc:
                if c == n: reached = True
                elif reached and c < n and drop is None: drop = a
            tail = a_end - drop if drop is not None else 0
            # main-only spans: Save K/V/Free with their critical-path status unknown
            ms = {s['name']: (s['a'] - w0, s['b'] - s['a']) for s in sp if s['c'] == 'main'}
            rows.append((w1 - w0, n, full, drop - w0 if drop else -1, a_end - w0, tail, ms))
        print(f'== {f} {kind}: L | n_att | all-n-busy us | first drop at | attention end | tail us (end - first drop) | main spans')
        for r in rows:
            print(f'   {r[0]:7.1f} | {r[1]} | {r[2]:6.1f} | {r[3]:6.1f} | {r[4]:6.1f} | {r[5]:6.1f} | ' +
                  ', '.join(f'{k} @{v[0]:.1f}+{v[1]:.1f}' for k, v in r[6].items()))
        if kind == 'decode':
            L = sum(r[0] for r in rows) / len(rows)
            sk = sum(r[6]['Save K'][1] for r in rows) / len(rows)
            sv = sum(r[6]['Save V'][1] for r in rows) / len(rows)
            fr = sum(r[6]['Free scratchpads'][1] for r in rows) / len(rows)
            ae = sum(r[4] for r in rows) / len(rows)
            print(f'   mean: L {L:.1f}, Save K {sk:.1f}, Save V {sv:.1f}, Free {fr:.1f}, sum {sk+sv+fr:.1f} us/layer = {(sk+sv+fr)*nl/1000:.2f} ms/step of {p["pass_ms"]:.2f} ms ({100*(sk+sv+fr)*nl/1000/p["pass_ms"]:.1f} %); attention end mean {ae:.1f} us = {100*ae/L:.1f} % of L; x36 = {ae*nl/1000:.2f} ms')
