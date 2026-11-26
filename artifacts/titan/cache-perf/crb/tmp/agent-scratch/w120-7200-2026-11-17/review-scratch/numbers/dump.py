import os, glob, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *
def f2(x): return '%.2f' % x
print('==== PART A 7200')
A = {}
for s, d in ((1,'k120-T72A1-20261117T221209Z'),(2,'k120-T72A2-20261117T221518Z'),(3,'k120-T72A3-20261117T221827Z')):
    ps = parse_bw(f'{R}/{d}/threads120.csv')
    print(d, 'nproc', len(ps))
    for p in ps:
        h = hdr_new(p['hdr'])
        if h['kernel'] == 'read':
            vals = [i['agg'] for i in p['iv']]
            print(' s%d r%d %-6s load %6.2f utc %s line %d: ' % (s, h['round'], h['binary'], h['load'], h['utc'], p['line']), vals, 'med', f2(med(vals)), 'passes', [i['passes'] for i in p['iv']], 'lines', [i['line'] for i in p['iv']])
            A[(s, h['round'], h['binary'])] = (vals, p, h)
for s in (1,2,3):
    for r in (1,2):
        o = med(A[(s,r,'bw_old')][0]); n = med(A[(s,r,'bw_new')][0])
        print('  drop s%d r%d: %.3f %%' % (s, r, (1-n/o)*100))
allold = [v for k,(vals,_,_) in A.items() if k[2]=='bw_old' for v in vals]
print(' bw_old all', len(allold), f2(min(allold)), f2(max(allold)), 'med', f2(med(allold)))
print('==== PART A 8000: A-1')
ps = parse_bw(f'{R}/kernels-20261113T181222Z/threads120.csv')
B = {}
for p in ps:
    h = hdr_new(p['hdr'])
    if h['kernel']=='read':
        vals=[i['agg'] for i in p['iv']]
        print(' A-1 r%d %-6s load %6.2f utc %s line %d:'%(h['round'],h['binary'],h['load'],h['utc'],p['line']), vals,'med',f2(med(vals)),'passes',[i['passes'] for i in p['iv']])
        B[('A-1',h['round'],h['binary'])]=vals
print('==== A-2')
ps = parse_bw(f'{R}/partA-20261113T205055Z/A1.csv')
for p in ps:
    h = hdr_step(p['hdr'])
    if h['kernel']=='read':
        vals=[i['agg'] for i in p['iv']]
        rnd = int(h['tag'][-1])
        print(' A-2 %s %-6s load %6.2f utc %s line %d:'%(h['tag'],h['binary'],h['load'],h['utc'],p['line']), vals,'med',f2(med(vals)),'passes',[i['passes'] for i in p['iv']])
        B[('A-2',rnd,h['binary'])]=vals
print('==== A-3')
ps = parse_bw(f'{R}/partA-20261113T205055Z/A3.csv')
for p in ps:
    h = hdr_step(p['hdr'])
    if h['tag'].startswith('onebuf-ms500-'):
        vals=[i['agg'] for i in p['iv']]
        print(' A-3 %s %-6s load %6.2f utc %s line %d:'%(h['tag'],h['binary'],h['load'],h['utc'],p['line']), vals,'med',f2(med(vals)),'passes',[i['passes'] for i in p['iv']])
        B[('A-3',int(h['tag'][-1]),h['binary'])]=vals
for row in ('A-1','A-2'):
    for r in (1,2):
        o=med(B[(row,r,'bw_old')]); n=med(B[(row,r,'bw_new')])
        print('  drop %s r%d: %.3f %%'%(row,r,(1-n/o)*100))
pool=[v for k,vals in B.items() if k[2]=='bw_old' for v in vals]
print(' pool A-1..A-3 bw_old', len(pool), f2(min(pool)), f2(max(pool)), 'med', f2(med(pool)), 'width%%of min %.3f of med %.3f of max %.3f'%((max(pool)-min(pool))/min(pool)*100,(max(pool)-min(pool))/med(pool)*100,(max(pool)-min(pool))/max(pool)*100))
p12=[v for k,vals in B.items() if k[2]=='bw_old' and k[0] in ('A-1','A-2') for v in vals]
print(' A-1,A-2 bw_old', len(p12), f2(min(p12)), f2(max(p12)))
for r in (1,2):
    v=[x for k,vals in B.items() if k[2]=='bw_new' and k[1]==r for x in vals]
    print(' bw_new round',r,len(v),f2(min(v)),f2(max(v)))
print('==== BWX')
def show(label, path, kernels=None, posfilter=None):
    ivs = parse_bwx(path)
    res=[]
    for d in ivs:
        if kernels and d['kernel'] not in kernels: continue
        if posfilter and not posfilter(d): continue
        ok = d['n']==120 and len(set(d['cpus']))==120 and max(d['cpus'])<=119 and sum(1 for c in d['cpus'] if c<64)==64
        print(' %-10s %-28s r%d p%d %-8s total %.4f (I_agg %.2f) n=%d ok=%s h0 %.2f h1 %.2f Iline %d T %d-%d flags=%s tstart %.3f tend %.3f'%(label, os.path.basename(path), d['round'], d['pos'], d['kernel'], d['total'], d['I_agg'], d['n'], ok, d['h0'], d['h1'], d['line_I'], d['first_T'], d['last_T'], sorted(set(d.get('flags',[]))), min(d['tstart']), max(d['tend'])))
        res.append(d)
    return res
D={}
for name, path in (('T72L1','w120-T72L1-20261117T221329Z/a6456.csv'),('T72L2','w120-T72L2-20261117T221638Z/a6456.csv'),('T72L3','w120-T72L3-20261117T221947Z/a6456.csv'),
                   ('T72C1','w120-T72C1-20261117T221436Z/cfwd.csv'),('T72C2','w120-T72C2-20261117T221745Z/crev.csv'),('T72C3','w120-T72C3-20261117T222054Z/cfwd.csv'),('T72C4','w120-T72C4-20261117T222136Z/crev.csv'),
                   ('T72I1','w120-T72I1-20261117T222700Z/a6456.csv'),('T72I2','w120-T72I2-20261117T223227Z/a6456.csv'),
                   ('F72d12','w120-w120-F72d12-20261117T200231Z/a6456.csv'),('L-1','w120-R8-20261117T020549Z/a6456.csv'),
                   ('L-2a','w120-R1-20261115T185140Z/p1nop.csv'),('L-2b','w120-R1-20261115T185140Z/p2add.csv'),('L-3','w120-R5-20261115T203152Z/thp.csv'),
                   ('L-4a','w120-R6-20261115T203438Z/st1.csv'),('L-4b','w120-R6-20261115T203438Z/st2.csv'),('L-4c','w120-R6-20261115T203438Z/st3.csv')):
    D[name]=show(name, f'{R}/{path}', kernels=('oldread','read','asmread'))
import pickle
pickle.dump({'A':{k:(v[0],v[2],[i for i in v[1]['iv']],v[1]['line']) for k,v in A.items()},'B':B,'D':D}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'raw.pkl'),'wb'))
