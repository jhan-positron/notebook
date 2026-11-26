#!/usr/bin/env python3
"""Build all interval groups from raw files (round-3 reviewer)."""
import raw3, statistics
R = raw3.R
med = statistics.median

def bwx(folder, fn):
    return raw3.parse_bwx('%s/%s/%s' % (R, folder, fn))

def sel(ivs, kernel, pos=None, rnd=None):
    return [i for i in ivs if i['kernel'] == kernel and (pos is None or i['pos'] == pos) and (rnd is None or i['round'] == rnd)]

D = {}
# ---- bwx12 processes
PROC = {
 'L-1': ('w120-R8-20261117T020549Z', 'a6456.csv'),
 'L-2a': ('w120-R1-20261115T185140Z', 'p1nop.csv'),
 'L-2b': ('w120-R1-20261115T185140Z', 'p2add.csv'),
 'L-3': ('w120-R5-20261115T203152Z', 'thp.csv'),
 'L-4a': ('w120-R6-20261115T203438Z', 'st1.csv'),
 'L-4b': ('w120-R6-20261115T203438Z', 'st2.csv'),
 'L-4c': ('w120-R6-20261115T203438Z', 'st3.csv'),
 'F72d12': ('w120-w120-F72d12-20261117T200231Z', 'a6456.csv'),
 'T72L1': ('w120-T72L1-20261117T221329Z', 'a6456.csv'),
 'T72L2': ('w120-T72L2-20261117T221638Z', 'a6456.csv'),
 'T72L3': ('w120-T72L3-20261117T221947Z', 'a6456.csv'),
 'T72C1': ('w120-T72C1-20261117T221436Z', 'cfwd.csv'),
 'T72C2': ('w120-T72C2-20261117T221745Z', 'crev.csv'),
 'T72C3': ('w120-T72C3-20261117T222054Z', 'cfwd.csv'),
 'T72C4': ('w120-T72C4-20261117T222136Z', 'crev.csv'),
 'T72I1': ('w120-T72I1-20261117T222700Z', 'a6456.csv'),
 'T72I2': ('w120-T72I2-20261117T223227Z', 'a6456.csv'),
}
BW = {k: bwx(*v) for k, v in PROC.items()}

# ---- part A
def partA(folder):
    ps = raw3.parse_bandwidth('%s/%s/threads120.csv' % (R, folder))
    out = []
    for p in ps:
        h = raw3.hdr_ra(p['header']); h.update(line=p['line'], iv=p['iv'], path=p['path'])
        out.append(h)
    return out
A72 = {s: partA(f) for s, f in ((1, 'k120-T72A1-20261117T221209Z'), (2, 'k120-T72A2-20261117T221518Z'), (3, 'k120-T72A3-20261117T221827Z'))}
A1 = partA('kernels-20261113T181222Z')
def steps(fn):
    ps = raw3.parse_bandwidth('%s/partA-20261113T205055Z/%s' % (R, fn))
    out = []
    for p in ps:
        h = raw3.hdr_step(p['header']); h.update(line=p['line'], iv=p['iv'], path=p['path'])
        out.append(h)
    return out
A2 = steps('A1.csv')
A3 = steps('A3.csv')

def aread(procs, binary, rnd):
    r = [p for p in procs if p['binary'] == binary and p['kernel'] == 'read' and p['round'] == rnd]
    assert len(r) == 1, (binary, rnd, len(r))
    return r[0]
def a2read(binary, rnd):
    tag = {'bw_old': 'read_old', 'bw_new': 'read_new'}[binary] + '-r%d' % rnd
    r = [p for p in A2 if p['tag'] == tag]
    assert len(r) == 1
    return r[0]
def a3(n):
    r = [p for p in A3 if p['tag'] == 'onebuf-ms500-%d' % n]
    assert len(r) == 1
    return r[0]
