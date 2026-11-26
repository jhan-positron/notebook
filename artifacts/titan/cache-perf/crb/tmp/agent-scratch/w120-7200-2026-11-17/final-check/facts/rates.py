# Own parser for bwx csv files (bwx12 / bwx11: one process per file; runner bwx: many "-- step" blocks per file).
import re, os, glob
from decimal import Decimal, ROUND_HALF_UP
R='/home/jhan/workspace/titan/cache-perf/crb/results'
def r2(x): return str(Decimal(repr(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
def parse(path):
    procs=[]; cur=None; iv=None
    for n,l in enumerate(open(path),1):
        if l.startswith('-- step'):
            cur=dict(tag=re.search(r' tag (\S+)',l)[1],load=re.search(r'loadavg (\S+)',l)[1],hdr=l.strip(),iv=[],line=n); procs.append(cur); continue
        if cur is None and (l.startswith('#') or l.startswith('P,') or l.startswith('I,')):
            cur=dict(tag=os.path.basename(path)[:-4],load=None,hdr='',iv=[],line=n); procs.append(cur)
        if l.startswith('# bwx:'):
            cur['seq']=re.search(r'seq=(\S+)',l)[1].split(','); cur['start']=re.search(r'start=(\S+)',l)[1]; cur['stop']=re.search(r'stop=(\S+)',l)[1]
        elif l.startswith('I,'):
            f=l.strip().split(','); iv=dict(line=n,round=int(f[1]),pos=int(f[2]),kernel=f[3],threads=int(f[5]),agg=float(f[8]),m0=0.0,m1=0.0,nT=0,n0=0,n1=0,flags=0,ts=1e99,te=-1); cur['iv'].append(iv)
        elif l.startswith('T,'):
            f=l.strip().split(','); cpu=int(f[5]); g=int(f[6])/float(f[7])/1e9
            assert int(f[1])==iv['round'] and int(f[2])==iv['pos']
            if cpu<64: iv['m0']+=g; iv['n0']+=1
            else: iv['m1']+=g; iv['n1']+=1
            iv['nT']+=1; iv['flags']+= (f[12]!='-'); iv['ts']=min(iv['ts'],float(f[9])); iv['te']=max(iv['te'],float(f[10]))
    for p in procs:
        for c in p['iv']: c['rate']=c['m0']+c['m1']; assert c['nT']==c['threads']
    return procs
def rng(v): return '%s to %s'%(r2(min(v)),r2(max(v)))
def sel(procs,kernel,pos=None,rounds=None):
    return [c for p in procs for c in p['iv'] if c['kernel']==kernel and (pos is None or c['pos'] in pos) and (rounds is None or c['round'] in rounds)]
F=lambda folder,name: glob.glob(os.path.join(R,folder,name))[0]
D={}
D['L']=[parse(F('w120-T72L%d-*'%i,'a6456.csv')) for i in (1,2,3)]
D['C']=[parse(F('w120-T72C%d-*'%i,'c*.csv')) for i in (1,2,3,4)]
D['I']=[parse(F('w120-T72I%d-*'%i,'a6456.csv')) for i in (1,2)]
D['F']=[parse(F('w120-w120-F72d12-20261117T200231Z','a6456.csv'))]
B12={'L-1 a6456':('w120-R8-20261117T020549Z','a6456'),'L-2 p1nop':('w120-R1-20261115T185140Z','p1nop'),'L-2 p2add':('w120-R1-20261115T185140Z','p2add'),
     'L-3 thp':('w120-R5-20261115T203152Z','thp'),'L-4 st1':('w120-R6-20261115T203438Z','st1'),'L-4 st2':('w120-R6-20261115T203438Z','st2'),'L-4 st3':('w120-R6-20261115T203438Z','st3')}
B11={'R0 p1':('w120-R0-20261115T165608Z','p1'),'R0 p2':('w120-R0-20261115T165608Z','p2'),'R0b cA':('w120-R0b-20261115T170342Z','cA'),'R0b cB':('w120-R0b-20261115T170342Z','cB'),'R0b cC':('w120-R0b-20261115T170342Z','cC')}
P12={k:parse(os.path.join(R,a,b+'.csv')) for k,(a,b) in B12.items()}
P11={k:parse(os.path.join(R,a,b+'.csv')) for k,(a,b) in B11.items()}
if __name__=='__main__':
    print('=== 7200 oldread, mesh sums (m0 = CPUs 0-63, m1 = CPUs 64-119)')
    G={}
    for k in 'LCIF':
        iv=[c for pp in D[k] for c in sel(pp,'oldread')]
        G[k]=iv
        assert all(c['n0']==64 and c['n1']==56 and c['flags']==0 for c in iv)
        print(k,'n',len(iv),'total',rng([c['rate'] for c in iv]),'m0',rng([c['m0'] for c in iv]),'m1',rng([c['m1'] for c in iv]))
    def show(name,iv): print(name,'n',len(iv),'m0',rng([c['m0'] for c in iv]),'m1',rng([c['m1'] for c in iv])); return iv
    a20=show('all 20 (F,L,C,I)',G['F']+G['L']+G['C']+G['I'])
    a12=show('12 without C (L,I,F)',G['L']+G['I']+G['F'])
    a8=show('8 without C and I (L,F)',G['L']+G['F'])
    print('=== 8000 oldread at position 0, bwx12 + bwx11')
    o12={k:sel(p,'oldread',pos=[0]) for k,p in P12.items()}; o11={k:sel(p,'oldread',pos=[0]) for k,p in P11.items()}
    for k,v in list(o12.items())+list(o11.items()):
        print('  ',k,'n',len(v),'total',[r2(c['rate']) for c in v],'m0',[r2(c['m0']) for c in v],'m1',[r2(c['m1']) for c in v])
    i12=[c for v in o12.values() for c in v]; i11=[c for v in o11.values() for c in v]
    b18=show('18 intervals bwx12+bwx11',i12+i11); show('11 bwx12',i12); show('7 bwx11',i11)
    lo1=max(c['m1'] for c in b18); hi0=min(c['m0'] for c in b18)
    for nm,g in (('20',a20),('12',a12),('8',a8)):
        print(' set',nm,': every m1 above 8000 max m1 (%s):'%r2(lo1), all(c['m1']>lo1 for c in g),'| every m0 below 8000 min m0 (%s):'%r2(hi0), all(c['m0']<hi0 for c in g),
              '| gaps m1 %+.2f m0 %+.2f'%(min(c['m1'] for c in g)-lo1, max(c['m0'] for c in g)-hi0))
    print('=== start-state view, oldread')
    after=['L-2 p2add','L-3 thp','L-4 st1','L-4 st2','L-4 st3']; idle=['L-1 a6456','L-2 p1nop']
    ga=[c['rate'] for k in after for c in o12[k]]; gi=[c['rate'] for k in idle for c in o12[k]]
    print('after-120 group n',len(ga),rng(ga),'| idle group n',len(gi),rng(gi),'| pool',rng(ga+gi), 'n',len(ga+gi))
    cL=[c['rate'] for c in G['L']]; cC=[c['rate'] for c in G['C']]
    print('part L',rng(cL),'n',len(cL),'| part C',rng(cC),'n',len(cC))
    print('part L below after-120 group by',r2(min(ga)-max(cL)),'| part C below by',r2(min(ga)-max(cC)),'| part C max < group min:',max(cC)<min(ga))
    cf=[c['rate'] for i in (0,2) for c in sel(D['C'][i],'oldread',pos=[0])]
    print('cfwd pos 0',rng(cf),'n',len(cf),'below by',r2(min(ga)-max(cf)))
    b11=[c['rate'] for k in ('R0 p2','R0b cB','R0b cC') for c in o11[k]]
    print('bwx11 after-120 (R0 p2, R0b cB, cC) n',len(b11),rng(b11),'| part C overlaps:',max(cC)>=min(b11) and min(cC)<=max(b11))
    # runner bwx position 0, tags common-6000-*
    bw=[]; np_=0; loads=[]
    for folder,name in (('B7-20261113T232859Z','B7.csv'),('B7-20261114T024352Z','B7.csv'),('C3-20261114T022708Z','C3.csv'),('C3-20261114T054116Z','C3.csv')):
        pp=[p for p in parse(os.path.join(R,folder,name)) if p['tag'].startswith('common-6000-')]
        np_+=len(pp); loads+= [float(p['load']) for p in pp]
        bw+= [c['rate'] for c in sel(pp,'oldread',pos=[0])]
    print('runner bwx pos 0: n',len(bw),'processes',np_,rng(bw),'load',min(loads),max(loads),'| part C overlaps:',max(cC)>=min(bw))
    print('part L max',r2(max(cL)),'< lowest of all:',r2(min(ga+gi+b11+bw)))
