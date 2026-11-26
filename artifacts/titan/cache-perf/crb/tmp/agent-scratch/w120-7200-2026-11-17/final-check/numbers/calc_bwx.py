#!/usr/bin/env python3
import sys, os, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *

folders = ['B7-20261113T232859Z/B7.csv', 'B7-20261114T024352Z/B7.csv', 'C3-20261114T022708Z/C3.csv', 'C3-20261114T054116Z/C3.csv']
procs = []
for f in folders:
    ps = parse_bwx(R + '/' + f)
    tags = collections.Counter(p['tag'].rsplit('-p', 1)[0] for p in ps)
    print(f, 'processes', len(ps), dict(tags))
    for p in ps:
        if p['tag'].startswith('common-6000-'):
            p['file'] = f
            procs.append(p)
print('common-6000-* processes:', len(procs))
for p in procs:
    print('  %s line %d tag %s load %.2f utc %s seq=%s rounds=%s stop=%s start=%s count=%s min_ms=%s nIV=%d' % (
        p['file'], p['line'], p['tag'], p['load'], p['utc'], p['meta'].get('seq'), p['meta'].get('rounds'), p['meta'].get('stop'), p['meta'].get('start'), p['meta'].get('count'), p['meta'].get('min_ms'), len(p['iv'])))
print('start option count:', collections.Counter(p['meta'].get('start') for p in procs), 'count:', collections.Counter((p['file'][:2], p['meta'].get('count')) for p in procs))
print('loads: %.2f to %.2f' % (min(p['load'] for p in procs), max(p['load'] for p in procs)))
by = collections.defaultdict(list)
bad = 0
for p in procs:
    for iv in p['iv']:
        if not iv['ok6456']:
            bad += 1
        by[(iv['kernel'], iv['pos'])].append((iv['rate'], iv['I_agg'], p['file'], iv['line'], p['tag']))
print('intervals not 64+56:', bad)
for k in sorted(by, key=lambda x: x[1]):
    v = [x[0] for x in by[k]]
    mx = max(by[k])
    print('  %-9s pos %d n=%d  %.2f to %.2f median %.2f   max at %s line %s tag %s (I_agg %.2f)' % (k[0], k[1], len(v), min(v), max(v), statistics.median(v), mx[2], mx[3], mx[4], mx[1]))
for kern in ('read', 'asmread', 'oldread'):
    v = [x for k in by if k[0] == kern for x in by[k]]
    mx = max(v)
    print(' kernel %-8s all positions n=%d  %.4f to %.4f ; max at %s line %s tag %s' % (kern, len(v), min(x[0] for x in v), mx[0], mx[2], mx[3], mx[4]))
print(' max |sum - I_agg| : %.4f' % max(abs(x[0] - x[1]) for k in by for x in by[k]))

print('=== B5')
b5 = []
for f in ['B5-20261114T011723Z/B5.csv', 'B5-20261114T043213Z/B5.csv']:
    ps = parse_bwx(R + '/' + f)
    for p in ps:
        p['file'] = f
        print('  %s line %d tag %s load %.2f utc %s seq=%s rounds=%s stop=%s count=%s min_ms=%s' % (f, p['line'], p['tag'], p['load'], p['utc'], p['meta'].get('seq'), p['meta'].get('rounds'), p['meta'].get('stop'), p['meta'].get('count'), p['meta'].get('min_ms')))
        for iv in p['iv']:
            if iv['kernel'] in ('read', 'asmread', 'oldread'):
                print('       line %d pos %d %-8s rate %.4f I_agg %.2f ok %s' % (iv['line'], iv['pos'], iv['kernel'], iv['rate'], iv['I_agg'], iv['ok6456']))
        b5.append(p)
for grp in ('b5-rev', 'b5-fwd'):
    ps = [p for p in b5 if p['tag'].startswith(grp)]
    for kern in ('read', 'asmread'):
        v = [iv['rate'] for p in ps for iv in p['iv'] if iv['kernel'] == kern]
        print(' %s %s n=%d %.2f to %.2f' % (grp, kern, len(v), min(v), max(v)))
    print('  loads %.2f to %.2f ; utc %s' % (min(p['load'] for p in ps), max(p['load'] for p in ps), [p['utc'] for p in ps]))
allb5 = [iv['rate'] for p in b5 for iv in p['iv'] if iv['kernel'] == 'read']
print(' all B5 read n=%d %.2f to %.2f' % (len(allb5), min(allb5), max(allb5)))
