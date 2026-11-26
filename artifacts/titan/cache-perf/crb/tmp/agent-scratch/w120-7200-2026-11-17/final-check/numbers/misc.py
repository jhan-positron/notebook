import sys, os, re, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *
p = parse_bwx(R + '/w120-R1-20261115T185140Z/p2add.csv')[0]
iv = [i for i in p['iv'] if i['kernel'] == 'asmread' and i['round'] == 1][0]
ts = [t['t_start'] for t in iv['T']]; te = [t['t_end'] for t in iv['T']]
print('p2add asmread rd1: line', iv['line'], 'rate %.6f' % iv['rate'], 'I_agg', iv['I_agg'], 't_start %.3f..%.3f t_end %.3f..%.3f' % (min(ts), max(ts), min(te), max(te)))
import datetime
base = datetime.datetime(2026, 11, 15, 18, 53, 45)
print('  start', base + datetime.timedelta(seconds=min(ts)), 'end', base + datetime.timedelta(seconds=max(te)), '(launch line second + offset; launch line has 1 s resolution)')
L3 = parse_bwx(R + '/w120-T72L3-20261117T221947Z/a6456.csv')[0]
mx = max(i['rate'] for i in L3['iv'] if i['kernel'] == 'asmread')
print('farthest ends L vs pool: %.6f - %.6f = %.6f' % (mx, iv['rate'], mx - iv['rate']))
# one-thread csv
f = R + '/kernels-20261113T181222Z/one-thread.csv'
hd = [(n, l.rstrip()) for n, l in enumerate(open(f), 1) if l.startswith('-- ')]
print('one-thread.csv headers', len(hd), 'first line', hd[0][0], hd[0][1][:140], '| last line', hd[-1][0], hd[-1][1][:140])
import collections
print(collections.Counter(re.search(r'threads (\d+)', h[1])[1] for h in hd), collections.Counter(re.search(r'cpus (\S+)', h[1])[1] for h in hd))
# precise check of rounding-sensitive values
def bw(path):
    return parse_bwx(R + path)[0]
F = bw('/w120-w120-F72d12-20261117T200231Z/a6456.csv'); L1 = bw('/w120-R8-20261117T020549Z/a6456.csv')
fa = [i['rate'] for i in F['iv'] if i['kernel'] == 'asmread']; la = [i['rate'] for i in L1['iv'] if i['kernel'] == 'asmread']
print('F asm min %.6f L-1 asm max %.6f diff %.6f' % (min(fa), max(la), min(fa) - max(la)))
C1 = bw('/w120-T72C1-20261117T221436Z/cfwd.csv')
print('C1 read', ['%.6f' % i['rate'] for i in C1['iv'] if i['kernel'] == 'read'], 'asmread', ['%.6f' % i['rate'] for i in C1['iv'] if i['kernel'] == 'asmread'])
B = [p for p in parse_bwx(R + '/B7-20261113T232859Z/B7.csv') if p['tag'] == 'common-6000-common-p1'][0]
for i in B['iv']:
    if i['kernel'] in ('read', 'asmread'):
        print('  B7 p1 rd %d pos %d %-8s %.6f line %d' % (i['round'], i['pos'], i['kernel'], i['rate'], i['line']))
