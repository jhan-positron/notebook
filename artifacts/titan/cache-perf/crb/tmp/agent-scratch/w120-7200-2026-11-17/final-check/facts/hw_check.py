# Independent recomputation of the "intervals with records" block of FACTS.md section 4.1.
# Own parser; does not import build_facts.py / facts_data.py.
import re, os, datetime, collections
from decimal import Decimal, ROUND_HALF_UP
R='/home/jhan/workspace/titan/cache-perf/crb/results'
def r2(x): return str(Decimal(repr(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
PROCS=[('L-1','w120-R8-20261117T020549Z','a6456'),
       ('L-2','w120-R1-20261115T185140Z','p1nop'),('L-2','w120-R1-20261115T185140Z','p2add'),
       ('L-3','w120-R5-20261115T203152Z','thp'),
       ('L-4','w120-R6-20261115T203438Z','st1'),('L-4','w120-R6-20261115T203438Z','st2'),('L-4','w120-R6-20261115T203438Z','st3'),
       ('R0','w120-R0-20261115T165608Z','p1'),('R0','w120-R0-20261115T165608Z','p2'),
       ('R0b','w120-R0b-20261115T170342Z','cA'),('R0b','w120-R0b-20261115T170342Z','cB'),('R0b','w120-R0b-20261115T170342Z','cC')]
# journal
J=[]
for n,l in enumerate(open(R+'/dimm-check-20261117/h-5.txt'),1):
    if 'Hardware error from APEI' in l:
        t=datetime.datetime.strptime(l[:19],'%Y-%m-%dT%H:%M:%S')
        assert l[19:25]=='+00:00', l[:30]
        J.append((t,n))
sev={}
lines=open(R+'/dimm-check-20261117/h-5.txt').read().splitlines()
for t,n in J:
    # severity line follows within the next 3 lines
    s=[x for x in lines[n:n+3] if 'event severity' in x]
    sev[n]=s[0].split('event severity:')[1].strip() if s else '?'
print('records in journal', len(J))
def csv(folder,tag):
    p=os.path.join(R,folder,tag+'.csv'); iv=[]; cur=None; seq=None
    for n,l in enumerate(open(p),1):
        if l.startswith('# bwx:'):
            seq=re.search(r'seq=(\S+)',l)[1].split(','); rounds=int(re.search(r'rounds=(\d+)',l)[1])
        if l.startswith('I,'):
            f=l.strip().split(',')
            cur=dict(line=n,round=int(f[1]),pos=int(f[2]),kernel=f[3],agg=float(f[8]),T=[],threads=int(f[5]))
            iv.append(cur)
        elif l.startswith('T,'):
            f=l.strip().split(',')
            assert int(f[1])==cur['round'] and int(f[2])==cur['pos'] and f[3]==cur['kernel']
            cur['T'].append((int(f[4]),int(f[5]),int(f[6]),float(f[7]),float(f[9]),float(f[10]),f[12]))
    for c in iv:
        assert len(c['T'])==c['threads'], (p,c['line'])
        c['rate']=sum(b/e for _,_,b,e,_,_,_ in c['T'])/1e9
        c['ts']=min(x[4] for x in c['T']); c['te']=max(x[5] for x in c['T'])
        c['tsmax']=max(x[4] for x in c['T']); c['temin']=min(x[5] for x in c['T'])
    return iv,seq,rounds
def launches(folder,tag):
    d0=datetime.datetime.strptime(re.search(r'-(\d{8})T',folder)[1],'%Y%m%d')
    L=None;E=None
    for l in open(os.path.join(R,folder,'launches.txt')):
        m=re.match(r'launch (\S+) utc (\d\d:\d\d:\d\d)',l)
        if m and m[1]==tag:
            L=datetime.datetime.combine(d0.date(),datetime.datetime.strptime(m[2],'%H:%M:%S').time()); load=l.split(' load ')[1].split()[0]
        m=re.match(r'rc (\S+) (\S+) utc (\d\d:\d\d:\d\d)',l)
        if m and m[2]==tag:
            E=datetime.datetime.combine(d0.date(),datetime.datetime.strptime(m[3],'%H:%M:%S').time()); rc=m[1]
    return L,E,load,rc
ALL={}
tot=0
for row,folder,tag in PROCS:
    iv,seq,rounds=csv(folder,tag)
    L,E,load,rc=launches(folder,tag)
    recs=[(t,n) for t,n in J if L<=t<=E]
    tot+=len(recs)
    ALL[(row,tag)]=dict(iv=iv,seq=seq,rounds=rounds,L=L,E=E,recs=recs,load=load)
    print('\n==',row,tag,'launch',L,'rc',E,rc,'load',load,'positions',len(seq),'rounds',rounds,'intervals',len(iv),'records',len(recs), 'sev', set(sev[n] for _,n in recs))
    bysec=collections.OrderedDict()
    for t,n in recs: bysec.setdefault(t,[]).append(n)
    for t,ns in bysec.items():
        N=int((t-L).total_seconds()); lo,hi=N-1,N+1
        # classify against intervals: record lies in (lo,hi) s after process start
        touch=[c for c in iv if not (hi<=c['ts'] or lo>=c['te'])]
        inside=[c for c in iv if c['ts']<=lo and hi<=c['te']]
        desc=[]
        for c in touch:
            desc.append('%s r%d p%d [%.2f..%.2f] line %d rate %s'%(c['kernel'],c['round'],c['pos'],c['ts'],c['te'],c['line'],r2(c['rate'])))
        kind='inside' if inside else ('before or inside' if len(touch)==1 and lo<touch[0]['ts'] and touch[0] is iv[0] else 'border/other')
        print('  ',t,'N=%d'%N,'journal lines',ns,'->',kind,'|',' ; '.join(desc))
print('\ntotal records in windows',tot)
import pickle
pickle.dump(ALL,open(os.path.dirname(os.path.abspath(__file__))+'/hw_all.pkl','wb'))
