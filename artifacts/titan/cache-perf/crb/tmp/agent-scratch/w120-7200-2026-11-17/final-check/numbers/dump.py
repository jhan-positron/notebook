#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *

print('=== PART A style files')
for name, path in [('T72A1', R + '/k120-T72A1-20261117T221209Z/threads120.csv'),
                   ('T72A2', R + '/k120-T72A2-20261117T221518Z/threads120.csv'),
                   ('T72A3', R + '/k120-T72A3-20261117T221827Z/threads120.csv'),
                   ('A-1', R + '/kernels-20261113T181222Z/threads120.csv'),
                   ('A-2', R + '/partA-20261113T205055Z/A1.csv'),
                   ('A-3', R + '/partA-20261113T205055Z/A3.csv')]:
    ps = parse_bandwidth(path)
    print('--', name, path, 'processes', len(ps))
    for p in ps:
        if p['kernel'] != 'read':
            continue
        print('   line %5d %-7s %-5s round %s tag %s load %6.2f utc %s minms %s | %s | passes %s' % (
            p['line'], p['binary'], p['kernel'], p['round'], p['tag'], p['load'], p['utc'], p['minms'],
            ', '.join('%.2f' % i['agg'] for i in p['iv']), ', '.join('%g' % i['passes'] for i in p['iv'])))

print('=== bwx12 files')
files = [('T72L1', '/w120-T72L1-20261117T221329Z/a6456.csv'), ('T72L2', '/w120-T72L2-20261117T221638Z/a6456.csv'),
         ('T72L3', '/w120-T72L3-20261117T221947Z/a6456.csv'),
         ('T72C1', '/w120-T72C1-20261117T221436Z/cfwd.csv'), ('T72C2', '/w120-T72C2-20261117T221745Z/crev.csv'),
         ('T72C3', '/w120-T72C3-20261117T222054Z/cfwd.csv'), ('T72C4', '/w120-T72C4-20261117T222136Z/crev.csv'),
         ('T72I1', '/w120-T72I1-20261117T222700Z/a6456.csv'), ('T72I2', '/w120-T72I2-20261117T223227Z/a6456.csv'),
         ('F72d12', '/w120-w120-F72d12-20261117T200231Z/a6456.csv'),
         ('L-1 R8', '/w120-R8-20261117T020549Z/a6456.csv'),
         ('L-2 p1nop', '/w120-R1-20261115T185140Z/p1nop.csv'), ('L-2 p2add', '/w120-R1-20261115T185140Z/p2add.csv'),
         ('L-3 thp', '/w120-R5-20261115T203152Z/thp.csv'),
         ('L-4 st1', '/w120-R6-20261115T203438Z/st1.csv'), ('L-4 st2', '/w120-R6-20261115T203438Z/st2.csv'), ('L-4 st3', '/w120-R6-20261115T203438Z/st3.csv'),
         ('X2d12', '/w120-X2d12-20261117T040922Z/a6456.csv'), ('X1d10', '/w120-X1d10-20261117T034916Z/a6456.csv'),
         ('X1d10b', '/w120-X1d10b-20261117T040407Z/a6456.csv'), ('BASEd10', '/w120-BASEd10-20261117T041738Z/a6456.csv')]
for name, f in files:
    ps = parse_bwx(R + f)
    assert len(ps) == 1
    p = ps[0]
    print('--', name, f, p['meta'])
    for iv in p['iv']:
        print('   line %5s rd %d pos %d %-12s n %3d ok %s rate %.4f I_agg %s diff %+.3f' % (
            iv['line'], iv['round'], iv['pos'], iv['kernel'], iv['n'], iv['ok6456'], iv['rate'], iv['I_agg'], iv['rate'] - iv['I_agg']))
