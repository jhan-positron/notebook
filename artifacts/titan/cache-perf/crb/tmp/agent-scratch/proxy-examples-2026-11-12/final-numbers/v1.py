import csv,collections,json
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
homes=[(int(r['mesh']),int(r['node_id_hex'],16)) for r in csv.DictReader(open(R+'full/homes.csv'))]
ch=list(csv.DictReader(open(R+'full/chunks.csv')))
nodes={(int(r['mesh']),int(r['node_id_hex'],16)):(int(r['x']),int(r['y'])) for r in csv.DictReader(open(R+'full/nodes.csv'))}
print(len(homes),collections.Counter(m for m,_ in homes), len(ch), len(nodes))
print('contig',set(c['contiguous'] for c in ch))
pa=[];va=[]
for i in range(len(homes)):
    c=ch[i//32768]; off=(i%32768)*64
    pa.append((int(c['pfn_hex'],16)<<12)+off); va.append(int(c['virt_hex'],16)+off)
def rule(a): 
    r=0
    for b in range(6,37,2): r^=(a>>b)&1
    return r
print('pa rule ok',sum(rule(p)==h[0] for p,h in zip(pa,homes)))
vw=[sum(rule(va[i])!=homes[i][0] for i in range(c*32768,(c+1)*32768)) for c in range(16)]
print('va wrong per chunk',vw,sum(vw))
for n,i in [('A',0),('B',1),('C',6*1024*1024//64)]:
    print(n,i,hex(va[i]),hex(pa[i]),rule(pa[i]),homes[i],hex(homes[i][1]),nodes[homes[i]])
print('PA A - PA C GiB',(pa[0]-pa[6*16384])/2**30)
# high bits
print('bits>=37',set(p>>37 for p in pa))
print('pairs diff mesh',sum(homes[2*k][0]!=homes[2*k+1][0] for k in range(262144)), 'pa differ bit6 only',sum(pa[2*k]^pa[2*k+1]==64 for k in range(262144)))
print('neighbours same node',sum(homes[i]==homes[i+1] for i in range(len(homes)-1)))
print('per chunk',[(collections.Counter(h[0] for h in homes[c*32768:(c+1)*32768])[0]) for c in range(16)])
print('lines per node',collections.Counter(collections.Counter(homes).values()))
xps={m:set(xy for (mm,_),xy in nodes.items() if mm==m) for m in (0,1)}
print(len(xps[0]),len(xps[1]),sorted(set((x,y) for x in range(1,8) for y in range(1,6))-xps[0]),sorted(set((x,y) for x in range(1,8) for y in range(1,6))-xps[1]))
# proxy map
M10={"1,1":"5,4","1,2":"5,5","1,3":"6,3","1,4":"5,1","2,1":"6,4","2,2":"6,5","2,3":"5,3","2,4":"6,1","2,5":"5,2","3,1":"7,4","3,2":"7,3","3,3":"7,2","3,4":"7,1","3,5":"6,2","4,1":"2,3","4,2":"4,4","4,3":"4,3","4,4":"4,2","5,1":"1,4","5,2":"2,5","5,3":"4,1","5,4":"1,1","5,5":"1,2","6,1":"2,4","6,2":"3,5","6,3":"3,2","6,4":"2,1","6,5":"2,2","7,1":"3,4","7,2":"1,3","7,3":"3,3","7,4":"3,1"}
M={tuple(map(int,k.split(','))):tuple(map(int,v.split(','))) for k,v in M10.items()}
print('map',len(M),len(set(M.values())),set(M)==xps[1],set(M.values())==xps[0])
# bit6 rule: for pair, mesh1 line home xp -> M -> equals mesh0 line home xp
ok=0;bad=collections.Counter()
for k in range(262144):
    a,b=homes[2*k],homes[2*k+1]
    if a[0]==1: a,b=b,a
    if M[nodes[b]]==nodes[a]: ok+=1
    else: bad[(nodes[b],nodes[a])]+=1
print('bit6 rule ok',ok,len(bad))
# dev equal?
print('same dev in pair',sum((homes[2*k][1]&1)==(homes[2*k+1][1]&1) for k in range(262144)))
import itertools
# geometric rules
best={}
for name,f in {'id':lambda x,y:(x,y),'mx':lambda x,y:(8-x,y),'my':lambda x,y:(x,6-y),'rot180':lambda x,y:(8-x,6-y),'tr':lambda x,y:(y,x)}.items():
    best[name]=sum(M[k]==f(*k) for k in M)
print(best)
