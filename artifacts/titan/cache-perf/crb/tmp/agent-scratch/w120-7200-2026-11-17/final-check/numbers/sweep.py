import sys, os, re, statistics, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *
D = os.path.dirname(os.path.abspath(__file__))
known = {}
def add(v, what):
    known.setdefault('%.2f' % v, set()).add(what)
# every interval of every file the page cites
bwfiles = ['w120-T72L1-20261117T221329Z/a6456.csv','w120-T72L2-20261117T221638Z/a6456.csv','w120-T72L3-20261117T221947Z/a6456.csv',
 'w120-T72C1-20261117T221436Z/cfwd.csv','w120-T72C2-20261117T221745Z/crev.csv','w120-T72C3-20261117T222054Z/cfwd.csv','w120-T72C4-20261117T222136Z/crev.csv',
 'w120-T72I1-20261117T222700Z/a6456.csv','w120-T72I2-20261117T223227Z/a6456.csv','w120-w120-F72d12-20261117T200231Z/a6456.csv','w120-R8-20261117T020549Z/a6456.csv',
 'w120-R1-20261115T185140Z/p1nop.csv','w120-R1-20261115T185140Z/p2add.csv','w120-R5-20261115T203152Z/thp.csv','w120-R6-20261115T203438Z/st1.csv','w120-R6-20261115T203438Z/st2.csv','w120-R6-20261115T203438Z/st3.csv',
 'w120-X2d12-20261117T040922Z/a6456.csv','w120-X1d10-20261117T034916Z/a6456.csv','w120-X1d10b-20261117T040407Z/a6456.csv','w120-BASEd10-20261117T041738Z/a6456.csv',
 'B7-20261113T232859Z/B7.csv','B7-20261114T024352Z/B7.csv','C3-20261114T022708Z/C3.csv','C3-20261114T054116Z/C3.csv','B5-20261114T011723Z/B5.csv','B5-20261114T043213Z/B5.csv']
for f in bwfiles:
    for p in parse_bwx(R + '/' + f):
        add(p['load'], 'load ' + f) if p['load'] is not None else None
        for iv in p['iv']:
            if iv['kernel'] in ('oldread', 'asmread', 'read'):
                add(iv['rate'], 'rate %s line %s' % (f, iv['line']))
                add(iv['I_agg'], 'I_agg %s line %s' % (f, iv['line']))
        by = {}
        for iv in p['iv']:
            by.setdefault(iv['kernel'], []).append(iv['rate'])
        for k in ('oldread', 'asmread', 'read'):
            if k in by: add(statistics.median(by[k]), 'median %s %s' % (k, f))
for f in ['k120-T72A1-20261117T221209Z/threads120.csv','k120-T72A2-20261117T221518Z/threads120.csv','k120-T72A3-20261117T221827Z/threads120.csv','kernels-20261113T181222Z/threads120.csv','partA-20261113T205055Z/A1.csv','partA-20261113T205055Z/A3.csv']:
    for p in parse_bandwidth(R + '/' + f):
        add(p['load'], 'load %s line %d' % (f, p['line']))
        for iv in p['iv']:
            add(iv['agg'], 'agg %s line %d' % (f, iv['line']))
# loads from launches.txt
for f in glob.glob(R + '/w120-*/launches.txt'):
    for l in open(f):
        m = re.match(r'launch (\S+) utc (\S+) load (\S+)', l)
        if m: add(float(m[3]), 'load ' + f.split('/')[-2] + ' ' + m[1])
txt = open(D + '/page_nosvg.txt').read()
txt = txt[:txt.index('{#refs}References')] + ' ' + ' '.join(re.findall(r'prints ([\d.]+) GB/s|rows, ([\d.]+) GB/s', txt[txt.index('{#refs}References'):]) and [''])
nums = re.findall(r'(?<![\d.])(\d+\.\d\d)(?![\d])', txt)
from collections import Counter
c = Counter(nums)
unk = [n for n in c if n not in known]
print('distinct 2-decimal numbers in page text:', len(c), ' not directly a raw rate/median/load:', len(unk))
for n in sorted(unk, key=float):
    i = txt.index(n)
    print('  %8s x%d  ...%s...' % (n, c[n], txt[max(0, i - 70): i + 30].replace('\n', ' ')))
