# Closer's own check of the numbers that the replies quote.  Reads the raw CSV files only.
import glob, os, statistics as st
R = '/home/jhan/workspace/titan/cache-perf/asimov/results/'
B = {'F1': R + 'membench-jibin-011/results/bootF1/', 'F2': R + 'membench-jibin-012/results/bootF2/'}

def rows(path):
    hdr, out = None, []
    for n, line in enumerate(open(path), 1):
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        f = line.split(',')
        if f[0] == 'mem':
            hdr = f
            continue
        d = dict(zip(hdr, f)); d['_line'] = n; d['_n'] = len(f)
        out.append(d)
    return out

def reps(path, mode_pred):
    return [r for r in rows(path) if r.get('rep', '-').isdigit() and mode_pred(r)]

print('== finding 1: 16 KiB single-call span rates')
for b in B:
    rs = rows(B[b] + 'cme-bandwidth-l1-asmpasses.csv')
    best = {r['kernel']: r for r in rs if r['rep'] == 'best' and r['bytes_per_thread'] == '16384'}
    rd, wr = float(best['cme-read']['span_GBps']), float(best['cme-write']['span_GBps'])
    print(b, 'read', rd, 'line', best['cme-read']['_line'], 'write', wr, 'line', best['cme-write']['_line'],
          'ratio %.4f' % (rd / wr), 'eff cycles per 64 B at 2.000 cycles/ns: %.3f %.3f' % (128 / rd, 128 / wr))

print('== findings 2 and 7: baseline and chain loads, boot F2 and F1')
for b in B:
    files = sorted(glob.glob(B[b] + 'cme-latency*.csv'))
    rt = [r for f in files for r in reps(f, lambda r: r['mode'] == 'cme-roundtrip')]
    rtb = [float(r['ns_per_load']) for f in files for r in rows(f) if r['mode'] == 'cme-roundtrip-best']
    refill_cols = sorted({k for r in rt for k in r if 'refill' in k or k.startswith('cme_l3') or 'l3' in k})
    nz = [(r['_line'], k, r[k]) for r in rt for k in refill_cols if k in r and float(r[k]) != 0.0]
    print(b, 'files', len(files), 'baseline reps', len(rt), 'best rows', sorted(set(rtb)),
          'rep ns %s..%s' % (min(r['ns_per_load'] for r in rt), max(r['ns_per_load'] for r in rt)),
          'core cycles %s..%s' % (min(r['cycles_per_load'] for r in rt), max(r['cycles_per_load'] for r in rt)),
          'CME cycles %s..%s' % (min(r['cme_cycles_per_load'] for r in rt), max(r['cme_cycles_per_load'] for r in rt)))
    print('   refill/L3 columns:', refill_cols, 'non-zero cells:', nz)
sm = rows(B['F2'] + 'cme-latency-dram-small.csv')
best = {int(r['size_bytes']): float(r['rep']) if False else float(r['loads'] if False else r['ns_per_load']) for r in sm if r['mode'] == 'cme-best'} if False else None
bestrows = [(int(r['size_bytes']), float(list(r.values())[5])) for r in sm if r['mode'] == 'cme-best']
l1 = [v for s, v in bestrows if s <= 65536]
print('F2 CME L1 best rows %.3f..%.3f ns, minus 21.005: %.3f..%.3f' % (min(l1), max(l1), min(l1) - 21.005, max(l1) - 21.005))
fl = rows(B['F2'] + 'cme-latency-dram-flushed.csv')
fb = [r for r in fl if r['mode'] == 'cme-best' and r['size_bytes'] == '8388608']
print('F2 flushed 8 MiB best', [(r['_line'], list(r.values())[5]) for r in fb], 'minus 21.005 = %.3f' % (float(list(fb[0].values())[5]) - 21.005))
print('F2 flushed 8 MiB rep rows:', [(r['_line'], r['loads'], r['cme_l1d_refill_inner_per_load'], r['cme_l1d_refill_outer_per_load'],
      r['cme_l1d_refill_rd_per_load'], r['cme_l1d_refill_hwprf_per_load']) for r in fl if r['size_bytes'] == '8388608' and r['rep'].isdigit()])

print('== finding 3: inner refills per line, boot F2, 4 KiB to 64 KiB')
vals = []
for r in sm:
    if r['rep'].isdigit() and r['mode'] == 'cme-repeat' and 4096 <= int(r['size_bytes']) <= 65536:
        lines = int(r['size_bytes']) // 64
        vals.append(float(r['cme_l1d_refill_inner_per_load']) * int(r['loads']) / lines)
print('rep rows', len(vals), 'per line %.2f..%.2f' % (min(vals), max(vals)))
for f in ('cme-latency-dram-small.csv', 'cme-latency-dram-large.csv'):
    for r in rows(B['F2'] + f):
        if r['rep'].isdigit() and r['size_bytes'] in ('1048576', '3145728') and r['mode'].startswith('cme-') and 'call' not in r['mode'] and 'round' not in r['mode']:
            print('  ', f, 'line', r['_line'], r['size_bytes'], r['mode'], 'rep', r['rep'], 'inner', r['cme_l1d_refill_inner_per_load'], 'outer', r['cme_l1d_refill_outer_per_load'])

print('== finding 4: address-order row')
p = R + 'membench-jibin-010/results/bootE/cme-latency-dram-seq.csv'
for n, line in enumerate(open(p), 1):
    if n in (13, 14):
        f = line.strip().split(',')
        print('line', n, 'loads', f[4], 'ns', f[5], 'read refill per load', f[10], 'x loads = %.6f' % (float(f[10]) * int(f[4])),
              'interval %.4f..%.4f' % ((float(f[10]) - 0.0005e-05) * int(f[4]), (float(f[10]) + 0.0005e-05) * int(f[4])))

print('== finding 6: four totals of one OCM pass of 64 loads, medians of the passes')
for b in B:
    P = []
    for f in sorted(glob.glob(B[b] + 'cme-latency-ocm-region*.csv')):
        for r in rows(f):
            if r['rep'].isdigit() and r['loads'] == '64' and r['mode'] not in ('cme-call', 'cme-roundtrip'):
                n = 64
                P.append((float(r['cycles_per_load']) * n / 2.0, float(r['ns_per_load']) * n,
                          float(r['cme_cycles_per_load']) * n / 2.0, float(r['ns_per_load_span']) * n))
    med = [st.median(x[i] for x in P) for i in range(4)]
    d = [st.median(x[i] - x[i + 1] for x in P) for i in range(3)]
    order = sum(1 for x in P if x[0] >= x[1] >= x[2] >= x[3])
    print(b, 'passes', len(P), 'medians core/bracket/CME/span ns: %.1f %.1f %.1f %.1f' % tuple(med),
          'median differences: %.1f %.1f %.1f' % tuple(d), 'ordered passes', order)

print('== finding 3: Table 62, (L3 miss - L3 refill) per load x footprint, boot F2, KiB')
for r in rows(B['F2'] + 'cme-latency-dram-small-l3.csv'):
    if r['rep'].isdigit() and r['mode'] == 'cme-repeat' and int(r['size_bytes']) >= 98304:
        mm = float(r['cme_l3d_miss_per_load']) - float(r['cme_l3d_refill_per_load'])
        print('  line', r['_line'], int(r['size_bytes']) // 1024, 'KiB rep', r['rep'], '%.1f KiB' % (mm * int(r['size_bytes']) / 1024),
              'hit', r['cme_l3d_hit_per_load'], 'ns', r['ns_per_load'])
