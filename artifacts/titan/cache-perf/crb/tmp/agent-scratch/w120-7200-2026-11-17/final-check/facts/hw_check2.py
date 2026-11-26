import pickle, os
from decimal import Decimal, ROUND_HALF_UP
def r2(x): return str(Decimal(repr(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
ALL=pickle.load(open(os.path.dirname(os.path.abspath(__file__))+'/hw_all.pkl','rb'))
# intervals with records (inside / before-or-inside) and border intervals, from hw_check.py output
REC={('L-1','a6456'):[(0,0)],('L-2','p1nop'):[(0,5),(1,9)],('L-2','p2add'):[(1,1)],('R0','p1'):[(0,6),(0,7),(1,5),(1,10)]}
BORDER={('L-2','p1nop'):[(0,10),(0,11)],('L-2','p2add'):[(1,6),(1,7)]}
def get(p,r,pos): 
    x=[c for c in ALL[p]['iv'] if c['round']==r and c['pos']==pos]; assert len(x)==1; return x[0]
print('--- table')
td=[]
for p,lst in REC.items():
    for r,pos in lst:
        a=get(p,r,pos); b=get(p,1-r,pos); assert a['kernel']==b['kernel']
        d=a['rate']-b['rate']; td.append(d)
        print(p,a['kernel'],'r%d p%d'%(r,pos),'line',a['line'],r2(a['rate']),'other',r2(b['rate']),'(%d)'%b['line'],'diff %+.4f -> %s'%(d,r2(d)), 'Iagg',a['agg'],b['agg'])
print('below by >1:',sorted(r2(-d) for d in td if d<-1),' above by >1:',[r2(d) for d in td if d>1],' within 1:',sorted(r2(d) for d in td if abs(d)<=1))
print('--- border intervals')
bd=[]
for p,lst in BORDER.items():
    for r,pos in lst:
        a=get(p,r,pos); b=get(p,1-r,pos); d=a['rate']-b['rate']; bd.append(d)
        print(p,a['kernel'],'r%d p%d'%(r,pos),r2(a['rate']),'other',r2(b['rate']),'diff',r2(d))
print('border diff range',r2(min(bd)),r2(max(bd)))
print('--- positions without records in the 4 processes')
n=0; big=[]; alld=[]
for p in REC:
    seq=ALL[p]['seq']
    used=set(pos for r,pos in REC.get(p,[]))|set(pos for r,pos in BORDER.get(p,[]))
    for pos in range(len(seq)):
        if pos in used: continue
        a=get(p,0,pos); b=get(p,1,pos); d=b['rate']-a['rate']  # round1 - round0
        n+=1; alld.append((abs(d),p,a['kernel'],pos,d,a['rate'],b['rate']))
        if abs(d)>1: big.append((p,a['kernel'],pos,r2(d)))
    print(p,'positions',len(seq),'excluded',sorted(used), 'seq',','.join(seq))
print('positions without records',n,' with |diff|>1:',len(big))
for b in big: print('   ',b)
alld.sort(reverse=True)
print('largest:',[(x[1],x[2],x[3],'r1-r0=%s'%r2(x[4]),r2(x[5]),r2(x[6])) for x in alld[:4]])
# how many exceed 1.96, 3.69
print('n > 1.96:',sum(1 for x in alld if x[0]>1.9649),' n > 3.69:',sum(1 for x in alld if x[0]>3.6949),' n>10.07', sum(1 for x in alld if x[0]>10.07))
# exactly-1.00 edge cases
print('near 1.0:',[(x[1],x[2],r2(x[4])) for x in alld if 0.9<x[0]<1.1])
# all 12 processes: two-round processes without records
print('--- two-round processes with 0 records (not in the 34):')
for p,v in ALL.items():
    if p in REC or v['rounds']<2: continue
    ds=[]
    for pos in range(len(v['seq'])):
        a=get(p,0,pos); b=get(p,1,pos); ds.append(b['rate']-a['rate'])
    print(p,'positions',len(ds),'|d|>1:',sum(1 for d in ds if abs(d)>1),'max |d|',r2(max(abs(d) for d in ds)))
