#!/usr/bin/env python3
# Independent recompute of the home-node statements of sec232.html from homes.csv / chunks.csv / nodes.csv.
import csv, itertools, collections
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z'
ch=list(csv.DictReader(open(R+'/full/chunks.csv')))
homes=[(int(r['mesh']),r['node_id_hex']) for r in csv.DictReader(open(R+'/full/homes.csv'))]
nodes={(int(r['mesh']),r['node_id_hex']):(int(r['x']),int(r['y']),int(r['dev']),int(r['lines'])) for r in csv.DictReader(open(R+'/full/nodes.csv'))}
N=len(homes); print('lines',N,'chunks',len(ch),'nodes',len(nodes), 'contiguous all', all(c['contiguous']=='1' for c in ch))
LPC=32768
va=[int(c['virt_hex'],16) for c in ch]; pa=[int(c['pfn_hex'],16)<<12 for c in ch]
print('pfn low 9 bits zero (2 MiB aligned):',all(p%(1<<21)==0 for p in pa), 'va step 2MiB:',all(va[i+1]-va[i]==1<<21 for i in range(15)))
def par(x): return bin(x).count('1')&1
EVEN=sum(1<<b for b in range(6,37,2))
def PA(i): return pa[i//LPC]+(i%LPC)*64
def VA(i): return va[i//LPC]+(i%LPC)*64
for name,i in (('A',0),('B',1),('C',3*LPC)):
    m,n=homes[i]; print(name,'line',i,'VA',hex(VA(i)),'PA',hex(PA(i)),'xor even 6..36 =',par(PA(i)&EVEN),'home mesh',m,'node',n,'xy/dev/lines',nodes[(m,n)])
print('VA C-A MiB',(VA(3*LPC)-VA(0))/2**20,' PA A-C GiB',(PA(0)-PA(3*LPC))/2**30, 'PA B^A',hex(PA(1)^PA(0)))
print('PA rule wrong:',sum(par(PA(i)&EVEN)!=homes[i][0] for i in range(N)))
w=[sum(par(VA(c*LPC+o)&EVEN)!=homes[c*LPC+o][0] for o in range(LPC)) for c in range(16)]
print('VA rule (bits 6..36) wrong total',sum(w),'per chunk',w)
EVENALL=sum(1<<b for b in range(6,48,2))
print('VA rule (even bits 6..46) wrong total',sum(par(VA(i)&EVENALL)!=homes[i][0] for i in range(N)))
print('per chunk mesh0/mesh1 counts:',sorted(collections.Counter((sum(homes[c*LPC+o][0]==0 for o in range(LPC)),sum(homes[c*LPC+o][0]==1 for o in range(LPC))) for c in range(16)).items()))
print('csv per chunk columns:',sorted(collections.Counter((c['lines_mesh0'],c['lines_mesh1'],c['lines_unknown']) for c in ch).items()))
# neighbour pairs inside a chunk (VA and PA neighbours) and across chunk borders (VA neighbours only)
inp=[(i,i+1) for i in range(N-1) if (i+1)%LPC]; dm=sum(homes[a][0]!=homes[b][0] for a,b in inp); sn=sum(homes[a]==homes[b] for a,b in inp)
print('pairs inside chunks',len(inp),'different mesh',dm,'= %.4f %%'%(100*dm/len(inp)),'same home node',sn)
allp=[(i,i+1) for i in range(N-1)]; dm2=sum(homes[a][0]!=homes[b][0] for a,b in allp)
print('all VA-neighbour pairs',len(allp),'different mesh',dm2,'= %.4f %%'%(100*dm2/len(allp)),'same node',sum(homes[a]==homes[b] for a,b in allp))
# analytic: neighbour o,o+1 differ in bits 6..6+k (k trailing ones of o): parity flips iff number of even bits among them is odd
# high bits
print('PA bits >=37 per chunk:',sorted({p>>37 for p in pa}),' bit41:',sorted({(p>>41)&1 for p in pa}),'bits 37..40:',sorted({(p>>37)&15 for p in pa}))
print('max PA bit set:',max(p.bit_length()-1 for p in pa))
# mesh rule: low part (bits 6..20) parity per chunk constant c_k = mesh(line0 of chunk) ; which masks over bits 21..36 give par(mask&pa_k)==c_k (or == c_k^1) for all k
c0=[homes[c*LPC][0] for c in range(16)]
# first check low rule inside each chunk
low=sum(1<<b for b in range(6,21,2))
print('inside-chunk: mesh == mesh(line0)^parity(even bits 6..20 of offset) wrong:',sum((homes[c*LPC+o][0]!=(c0[c]^par((o*64)&low))) for c in range(16) for o in range(LPC)))
sol=[];solinv=[]
for mk in range(1<<16):
    mask=mk<<21
    v=[par(p&mask) for p in pa]
    if v==c0: sol.append(mask)
    if [x^1 for x in v]==c0: solinv.append(mask)
bits=lambda m:[b for b in range(64) if m>>b&1]
print('masks over PA bits 21..36 that fit the 16 chunks (result 0 = mesh 0):',len(sol)); [print('  ',bits(m)) for m in sol]
print('masks that fit with the result inverted:',len(solinv))
print('rank check: distinct high-bit patterns (bits 21..36) of the 16 chunks:',len({(p>>21)&0xffff for p in pa}))
# rank of the 16 chunk vectors over GF(2) (bits 21..36)
def rank(vs):
    vs=list(vs);r=0
    for b in range(16):
        piv=next((i for i in range(r,len(vs)) if vs[i]>>b&1),None)
        if piv is None: continue
        vs[r],vs[piv]=vs[piv],vs[r]
        for i in range(len(vs)):
            if i!=r and vs[i]>>b&1: vs[i]^=vs[r]
        r+=1
    return r
print('GF(2) rank of the 16 chunk bit vectors (bits 21..36):',rank([(p>>21)&0xffff for p in pa]),'; with a constant column:',rank([(((p>>21)&0xffff)<<1|1)&0x1ffff if False else ((p>>21)&0xffff) for p in pa]))
# 7 XOR sums: structure test without the worker's masks.
# kernel K = offsets o (15 bits) in chunk 0 with home(o)==home(0); linear hash => K is a subspace of size 2^(15-7)=256, and home constant on cosets
H0=[homes[o] for o in range(LPC)]
K=[o for o in range(LPC) if H0[o]==H0[0]]
print('chunk 0: |K|=',len(K),'closed under xor:',all((a^b) in set(K) for a in K[:40] for b in K))
Ks=set(K)
# basis of K
def span_rank(vs):
    basis=[]
    for v in vs:
        for b in basis: v=min(v,v^b)
        if v: basis.append(v)
    return len(basis)
print('dim K =',span_rank(K))
# home is a function of coset in every chunk: map coset representative -> home
bas=[]
for v in K:
    x=v
    for b in bas: x=min(x,x^b)
    if x: bas.append(x)
def red(o):
    for b in sorted(bas,reverse=True):
        o=min(o,o^b)
    return o
# proper reduction: build echelon basis
ech={}
for v in K:
    x=v
    while x:
        h=x.bit_length()-1
        if h in ech: x^=ech[h]
        else: ech[h]=x; break
def red(o):
    while True:
        ch_=False
        for h in sorted(ech,reverse=True):
            if o>>h&1: o^=ech[h]; ch_=True
        if not ch_: return o
    return o
def red(o):
    for h in sorted(ech,reverse=True):
        if o>>h&1: o^=ech[h]
    return o
bad=0; ncos=set()
for c in range(16):
    mp={}
    for o in range(LPC):
        r=red(o); ncos.add(r)
        if mp.setdefault(r,homes[c*LPC+o])!=homes[c*LPC+o]: bad+=1
    if len(set(mp.values()))!=128: print('chunk',c,'distinct homes',len(set(mp.values())))
print('cosets',len(ncos),'lines whose home differs from the home of their coset in the same chunk:',bad)
# linearity across cosets: home(o1^o2^o3) determined: check the map coset->home is "affine": home(a)^... cannot xor homes; test instead that for chunk c vs chunk 0 the map is a translation: exists t with home_c(o)==home_0(o^t)
ok=0
for c in range(16):
    tgt=homes[c*LPC]; t=next(o for o in range(LPC) if H0[o]==tgt)
    if all(homes[c*LPC+o]==H0[o^t] for o in range(LPC)): ok+=1
print('chunks whose home map is the chunk-0 map shifted by a constant XOR of the offset:',ok,'of 16')
print('distinct homes',len(set(homes)),'lines per home',sorted(collections.Counter(collections.Counter(homes).values()).items()))
# verify with the worker's masks (cross-check)
import json
T=json.load(open('../hash/table.json'))
print('table.json keys',list(T.keys())[:10])
