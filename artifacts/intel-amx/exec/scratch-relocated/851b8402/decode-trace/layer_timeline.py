"""Layer-window timeline from the lanes json (base-tp2 / base-tp4).

Classes are assigned by span name, not by the json 'cls' field:
  main      = thread with Save K / Save V / Free scratchpads
  helper    = spans named kernel_*  (main helpers running run_main_help)
  attention = Attention Ready / Attention Pending / attention: join
Time unit: us, relative to the json's Save K start of layer 10 (t=0).
"""
import json, sys, collections

DIR = '/home/jhan/workspace/intel-AMX/exec/results/vnnik-trace-20260914/'

def cls_of(s):
    n = s['name']
    if n in ('Save K', 'Save V', 'Free scratchpads'): return 'main'
    if n.startswith('kernel_'): return 'helper'
    if n.startswith('Attention') or n.startswith('attention'): return 'attention'
    return 'other'

def union(ivs):
    ivs = sorted(ivs)
    out = []
    for a, b in ivs:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]

def total(ivs): return sum(b - a for a, b in ivs)

def subtract(a_ivs, b_ivs):
    """a minus b, both unions."""
    out = []
    for a, b in a_ivs:
        cur = a
        for c, d in b_ivs:
            if d <= cur or c >= b: continue
            if c > cur: out.append((cur, c))
            cur = max(cur, d)
            if cur >= b: break
        if cur < b: out.append((cur, b))
    return out

def intersect(a_ivs, b_ivs):
    out = []
    for a, b in a_ivs:
        for c, d in b_ivs:
            lo, hi = max(a, c), min(b, d)
            if hi > lo: out.append((lo, hi))
    return out

def clip(spans, w0, w1):
    out = []
    for s in spans:
        a, b = s['start_us'], s['start_us'] + s['dur_us']
        a2, b2 = max(a, w0), min(b, w1)
        if b2 > a2:
            t = dict(s); t['a'] = a2; t['b'] = b2; t['c'] = cls_of(s); out.append(t)
    return out

def concurrency(ivs_per_thread, w0, w1):
    """Return list of (t_start, t_end, count) for the number of threads busy."""
    ev = []
    for ivs in ivs_per_thread:
        for a, b in ivs:
            ev.append((a, 1)); ev.append((b, -1))
    ev.sort()
    segs = []; cnt = 0; t = w0
    for x, d in ev:
        if x > t: segs.append((t, x, cnt))
        t = x; cnt += d
    if t < w1: segs.append((t, w1, cnt))
    return segs

def analyse(trace, kind, verbose_window=0):
    d = json.load(open(DIR + trace + '.perfetto-trace.lanes.json'))
    p = d[kind]
    spans = p['spans']
    savek = sorted(s['start_us'] for s in spans if s['name'] == 'Save K')
    if kind == 'decode':
        windows = list(zip(savek, savek[1:]))
        note = 'window = Save K start to next Save K start (full layers in json)'
    else:
        windows = [(savek[0], p['window_us'][1])]
        note = 'window = Save K start to end of json window (next Save K NOT in json)'
    print('#' * 78)
    print(f'# {trace} {kind}: pass {p["pass_index"]} pass_ms {p["pass_ms"]:.3f} '
          f'layer {p["layer"]}; {len(windows)} window(s); {note}')
    print(f'# pass_ms/36 = {p["pass_ms"]*1000/36:.1f} us per layer (mean over the pass)')
    agg = collections.defaultdict(list)
    for wi, (w0, w1) in enumerate(windows):
        L = w1 - w0
        sp = clip(spans, w0, w1)
        per_cls_thread = collections.defaultdict(lambda: collections.defaultdict(list))
        for s in sp:
            per_cls_thread[s['c']][s['utid']].append((s['a'], s['b']))
        cls_union = {c: union([iv for th in per_cls_thread[c].values() for iv in th])
                     for c in ('main', 'helper', 'attention')}
        any_union = union(cls_union['main'] + cls_union['helper'] + cls_union['attention'])
        nospan = subtract([(w0, w1)], any_union)
        serial = subtract(cls_union['main'], cls_union['helper'])       # main works, helpers idle
        serial_all = subtract(serial, cls_union['attention'])            # ... and attention idle too
        helper_during_attn = intersect(cls_union['helper'], cls_union['attention'])
        main_during_attn = intersect(cls_union['main'], cls_union['attention'])
        helper_idle_during_attn = subtract(cls_union['attention'], cls_union['helper'])
        att_conc = concurrency([union(v) for v in per_cls_thread['attention'].values()], w0, w1)
        hel_conc = concurrency([union(v) for v in per_cls_thread['helper'].values()], w0, w1)
        busy_time = sum((b - a) for a, b, n in att_conc if n > 0)
        thread_time = sum((b - a) * n for a, b, n in att_conc)
        n_att_threads = len(per_cls_thread['attention'])
        n_hel_threads = len(per_cls_thread['helper'])
        mean_conc = thread_time / busy_time if busy_time else 0
        max_conc = max((n for a, b, n in att_conc), default=0)
        # histogram of attention concurrency in buckets
        hist = collections.Counter()
        for a, b, n in att_conc:
            hist[n] += b - a
        # helper concurrency while attention busy
        hb = collections.Counter()
        for a, b, n in hel_conc:
            for c, dd in cls_union['attention']:
                lo, hi = max(a, c), min(b, dd)
                if hi > lo: hb[n] += hi - lo
        r = dict(L=L, main=total(cls_union['main']), helper=total(cls_union['helper']),
                 attention=total(cls_union['attention']), nospan=total(nospan),
                 serial=total(serial), serial_all=total(serial_all),
                 helper_during_attn=total(helper_during_attn),
                 helper_idle_during_attn=total(helper_idle_during_attn),
                 main_during_attn=total(main_during_attn),
                 mean_conc=mean_conc, max_conc=max_conc, n_att=n_att_threads, n_hel=n_hel_threads,
                 att_thread_time=thread_time)
        for k, v in r.items(): agg[k].append(v)
        print(f'\n== window {wi}: [{w0:.1f}, {w1:.1f}] us, L = {L:.1f} us')
        print(f'   threads seen: main 1, helper {n_hel_threads}, attention {n_att_threads}')
        print(f'   busy fraction (union over class threads): main {r["main"]/L:.4f} ({r["main"]:.1f} us), '
              f'helper {r["helper"]/L:.4f} ({r["helper"]:.1f} us), attention {r["attention"]/L:.4f} ({r["attention"]:.1f} us)')
        print(f'   NO-span time: {r["nospan"]:.1f} us = {100*r["nospan"]/L:.1f} %')
        print(f'   serial (main busy, helpers idle): {r["serial"]:.1f} us = {100*r["serial"]/L:.1f} %; '
              f'of which attention also idle: {r["serial_all"]:.1f} us = {100*r["serial_all"]/L:.1f} %')
        print(f'   attention busy {r["attention"]:.1f} us: helpers busy at same time {r["helper_during_attn"]:.1f} us, '
              f'helpers idle {r["helper_idle_during_attn"]:.1f} us; main busy at same time {r["main_during_attn"]:.1f} us')
        print(f'   attention concurrency: mean {mean_conc:.1f} of {n_att_threads} while busy, max {max_conc}, '
              f'thread-time {thread_time:.1f} us')
        if verbose_window == wi or verbose_window == 'all':
            print('   attention concurrency histogram (count: us):',
                  ', '.join(f'{n}:{t:.0f}' for n, t in sorted(hist.items())))
            print('   helper concurrency while attention busy (count: us):',
                  ', '.join(f'{n}:{t:.0f}' for n, t in sorted(hb.items())))
            print('   -- main thread sequence (start, dur):')
            for s in sorted((s for s in sp if s['c'] == 'main'), key=lambda s: s['a']):
                print(f'      {s["a"]-w0:8.1f} {s["b"]-s["a"]:7.1f}  {s["name"]}')
            print('   -- helper kernels (name: first start, last end, mean per-thread dur, n threads):')
            byname = collections.defaultdict(list)
            for s in sp:
                if s['c'] == 'helper': byname[s['name']].append(s)
            for n, ss in sorted(byname.items(), key=lambda kv: min(s['a'] for s in kv[1])):
                print(f'      {min(s["a"] for s in ss)-w0:8.1f} .. {max(s["b"] for s in ss)-w0:8.1f}  '
                      f'mean {sum(s["b"]-s["a"] for s in ss)/len(ss):6.1f} us x{len(ss)}  {n}')
            print('   -- serial segments (main busy, helpers idle): start, dur, what main runs')
            for a, b in serial:
                names = sorted({s['name'] for s in sp if s['c'] == 'main' and s['a'] < b and s['b'] > a})
                attn_busy = total(intersect([(a, b)], cls_union['attention']))
                print(f'      {a-w0:8.1f} {b-a:7.1f}  {"+".join(names)}  (attention busy during it: {attn_busy:.1f} us)')
            print('   -- no-span segments: start, dur')
            for a, b in nospan:
                print(f'      {a-w0:8.1f} {b-a:7.1f}')
            print('   -- attention: per-name totals and worker counts')
            byn = collections.defaultdict(lambda: [0.0, set(), 0])
            for s in sp:
                if s['c'] == 'attention':
                    e = byn[s['name']]; e[0] += s['b'] - s['a']; e[1].add(s['utid']); e[2] += 1
            for n, (t, ths, k) in byn.items():
                print(f'      {n:20s} thread-time {t:8.1f} us, {len(ths)} workers, {k} spans')
            print('   -- attention: window timeline in 25 us bins (attention busy count | helper busy count | main busy?)')
            step = 25.0 if kind == 'decode' else 500.0
            t = w0
            while t < w1:
                t2 = min(t + step, w1)
                ac = sum((min(b, t2) - max(a, t)) * n for a, b, n in att_conc if min(b, t2) > max(a, t)) / (t2 - t)
                hc = sum((min(b, t2) - max(a, t)) * n for a, b, n in hel_conc if min(b, t2) > max(a, t)) / (t2 - t)
                mb = total(intersect([(t, t2)], cls_union['main'])) / (t2 - t)
                print(f'      {t-w0:8.1f} att {ac:5.1f} hel {hc:4.1f} main {mb:4.2f}')
                t = t2
    print(f'\n== MEAN over {len(windows)} window(s): ' + ', '.join(
        f'{k} {sum(v)/len(v):.1f}' for k, v in agg.items()))
    Lm = sum(agg['L']) / len(agg['L'])
    print('   shares of L: ' + ', '.join(f'{k} {100*sum(v)/len(v)/Lm:.1f}%' for k, v in agg.items()
                                       if k in ('main', 'helper', 'attention', 'nospan', 'serial', 'serial_all',
                                                'helper_during_attn', 'helper_idle_during_attn')))
    return agg

if __name__ == '__main__':
    which = sys.argv[1:] or ['base-tp2 decode 0', 'base-tp4 decode 0', 'base-tp2 prefill 0', 'base-tp4 prefill 0']
    for w in which:
        t, k, v = w.split()
        analyse(t, k, 'all' if v == 'all' else int(v))
