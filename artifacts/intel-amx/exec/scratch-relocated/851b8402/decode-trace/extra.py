import json, collections, sys
sys.path.insert(0, '.')
from layer_timeline import DIR, cls_of, union, total, clip, subtract, intersect
for f in ['base-tp2', 'base-tp4']:
    d = json.load(open(DIR + f + '.perfetto-trace.lanes.json'))
    # prefill: what runs in [-1500, 0] before the Save K of layer 10
    p = d['prefill']; sp = clip(p['spans'], -1500.0, 0.0)
    u = {c: union([(s['a'], s['b']) for s in sp if s['c'] == c]) for c in ('main', 'helper', 'attention')}
    print(f'== {f} prefill pre-window [-1500, 0]: busy main {total(u["main"]):.1f} helper {total(u["helper"]):.1f} attention {total(u["attention"]):.1f} us')
    byname = collections.defaultdict(list)
    for s in sp:
        if s['c'] == 'helper': byname[s['name']].append(s)
    for n, ss in sorted(byname.items(), key=lambda kv: min(s['a'] for s in kv[1])):
        print(f'   helper {n}: {min(s["a"] for s in ss):8.1f} .. {max(s["b"] for s in ss):8.1f} mean {sum(s["b"]-s["a"] for s in ss)/len(ss):.1f} us x{len(ss)}')
    att = [s for s in sp if s['c'] == 'attention']
    if att: print(f'   attention spans in pre-window: {len(att)}, first start {min(s["a"] for s in att):.1f}, last end {max(s["b"] for s in att):.1f}')
    # prefill: attention timing relative to Save K/V
    p = d['prefill']; sp = clip(p['spans'], 0.0, p['window_us'][1])
    for nm in ('Attention Ready', 'Attention Pending', 'attention: join'):
        ss = [s for s in sp if s['name'] == nm]
        if ss: print(f'   prefill {nm:18s}: first start {min(s["a"] for s in ss):8.1f}, last end {max(s["b"] for s in ss):8.1f}, n {len(ss)}, mean dur {sum(s["b"]-s["a"] for s in ss)/len(ss):.1f}')
    # decode: per window Save K/V/Free durations, pending start, attention end
    p = d['decode']; spans = p['spans']
    savek = sorted(s['start_us'] for s in spans if s['name'] == 'Save K')
    print(f'== {f} decode per-window: L | SaveK dur | SaveV start,dur | Free start,dur | Pending first start..last end | Ready first..last | join last end | attention union end')
    for w0, w1 in zip(savek, savek[1:]):
        sp = clip(spans, w0, w1)
        g = lambda nm: [s for s in sp if s['name'] == nm]
        sk = g('Save K')[0]; sv = g('Save V')[0]; fr = g('Free scratchpads')
        pend = g('Attention Pending'); rdy = g('Attention Ready'); jn = g('attention: join')
        au = union([(s['a'], s['b']) for s in sp if s['c'] == 'attention'])
        print(f'   {w1-w0:6.1f} | {sk["b"]-sk["a"]:4.1f} | {sv["a"]-w0:5.1f},{sv["b"]-sv["a"]:4.1f} | '
              f'{fr[0]["a"]-w0 if fr else -1:6.1f},{fr[0]["b"]-fr[0]["a"] if fr else 0:4.1f} | '
              f'{min(s["a"] for s in pend)-w0 if pend else -1:6.1f}..{max(s["b"] for s in pend)-w0 if pend else -1:6.1f} ({len(pend)}) | '
              f'{min(s["a"] for s in rdy)-w0:6.1f}..{max(s["b"] for s in rdy)-w0:6.1f} | {max(s["b"] for s in jn)-w0:6.1f} | {au[-1][1]-w0:6.1f}')
    # decode: per-worker Ready/Pending/join split (thread-time) for the window ending at 0
    w0, w1 = savek[-2], savek[-1]
    sp = clip(spans, w0, w1)
    per = collections.defaultdict(lambda: collections.Counter())
    for s in sp:
        if s['c'] == 'attention': per[s['thread']][s['name']] += s['b'] - s['a']
    tot = collections.Counter()
    for th, c in per.items(): tot.update(c)
    print(f'   decode window ending at 0: attention thread-time by name: ' + ', '.join(f'{k} {v:.1f} us' for k, v in tot.items()) + f'; L={w1-w0:.1f}, workers {len(per)}')
    busy = sorted(sum(c.values()) for c in per.values())
    print(f'   per-worker busy time in that window: min {busy[0]:.1f}, median {busy[len(busy)//2]:.1f}, max {busy[-1]:.1f} us')
