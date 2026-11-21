#!/usr/bin/env python3
"""Characterise the home-node hash of the CRB run sudo-20261102T054936Z. Reads full/homes.csv,
chunks.csv, nodes.csv. Writes examples.json next to this script. Read-only on the results."""
import csv, json, os, itertools, numpy as np
D='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/full/'
OUT=os.path.dirname(os.path.abspath(__file__))
ch=list(csv.DictReader(open(D+'chunks.csv')))
pfn=[int(r['pfn_hex'],16) for r in ch]; virt=[int(r['virt_hex'],16) for r in ch]
print('chunks contiguous flags:',[r['contiguous'] for r in ch])
nodes={(int(r['mesh']),int(r['node_id_hex'],16)):(int(r['x']),int(r['y']),int(r['dev'])) for r in csv.DictReader(open(D+'nodes.csv'))}
N=524288
mesh=np.zeros(N,int); node=np.zeros(N,int)
for r in csv.DictReader(open(D+'homes.csv')):
    l=int(r['line']); mesh[l]=int(r['mesh']); node[l]=int(r['node_id_hex'],16)
home=mesh*4096+node; H=home.reshape(16,32768); M_=mesh.reshape(16,32768)
off=np.arange(32768)                       # line offset in chunk; address bit = index bit + 6
pa=lambda c,o: pfn[c]*4096+o*64
par=lambda v: np.array([bin(int(x)).count('1')&1 for x in v]) if not np.isscalar(v) else bin(int(v)).count('1')&1
def parv(a):  # parity of int array
    a=a.copy(); p=np.zeros_like(a)
    while a.any(): p^=a&1; a>>=1
    return p
bits=lambda m,sh=6: [i+sh for i in range(64) if m>>i&1]
print('low 21 bits of every chunk physical base zero:',all((p*4096)&0x1fffff==0 for p in pfn))

print('\n=== (2) mesh bit ===')
alt=sum(1<<(b-6) for b in range(6,21,2))
inv=[]
for c in range(16):
    d=(parv(off&alt)!=M_[c]).sum()
    assert d in (0,32768); inv.append(int(d==32768))
print('mesh == XOR(addr bits 6,8,..,20) ^ inv_c for all 32768 lines of each chunk; inv_c =',inv,' inverted chunks:',[c for c in range(16) if inv[c]],'count',sum(inv))

print('\n=== (1)+(3) linear hash inside a chunk ===')
K=set(np.nonzero(H[0]==H[0][0])[0].tolist())
print('kernel K (offsets with the same home as offset 0, chunk 0): size',len(K),' closed under XOR:',all((a^b) in K for a in K for b in K))
def rref(vs,nb=15):
    b=[]
    for v in vs:
        for x in b:
            if v>>(x.bit_length()-1)&1: v^=x
        if v:
            b=[y^v if y>>(v.bit_length()-1)&1 else y for y in b]; b.append(v)
    return sorted(b,reverse=True)
KB=rref(sorted(K)); print('dim K =',len(KB)); 
for v in KB: print('   kernel vector: addr bits',bits(v))
# annihilator: masks m with parity(m&k)=0 for all k in KB
ann=[m for m in range(1,32768) if all(bin(m&k).count('1')%2==0 for k in KB)]
print('annihilator size (non-zero masks):',len(ann),'-> dim',(len(ann)+1).bit_length()-1)
assert alt in ann
print('mesh mask (bits 6,8..20) is in the annihilator: True')
# canonical basis: mesh mask first, then RREF of the rest reduced so each has a distinct lowest bit
def rref_low(vs):
    b=[]
    for v in vs:
        for x in b:
            if v&(x&-x): v^=x
        if v:
            b=[y^v if y&(v&-v) else y for y in b]; b.append(v)
    return sorted(b,key=lambda x:x&-x)
RB=rref_low(ann)
print('reduced basis of all 7 masks (each has a private lowest bit):')
for m in RB: print('   addr bits',bits(m))
# choose 6 masks independent of mesh mask: reduced basis with mesh mask's pivot removed
piv=alt&-alt
others=[m for m in RB if not (m&-m)==piv]
others=[m^alt if m&piv else m for m in others]  # none should contain pivot after rref
masks=[alt]+others
assert len(rref(masks))==7
print('chosen 7 masks: h6 = mesh mask, h5..h0 = node masks')
for i,m in enumerate(masks): print('   h%d: addr bits %s  (hex mask over address 0x%x)'%(6-i,bits(m),m<<6))
def hval(o):
    h=np.zeros_like(o)
    for m in masks: h=(h<<1)|parv(o&m)
    return h
hv=hval(off)
T={}
ok=True
for o in range(32768):
    if T.setdefault(int(hv[o]),int(H[0][o]))!=H[0][o]: ok=False
print('chunk 0: home is a function of the 7-bit hash:',ok,' distinct hash values',len(T),' distinct homes',len(set(T.values())))
inv_T={v:k for k,v in T.items()}
kc=[]; allok=True
for c in range(16):
    k=inv_T[int(H[c][0])]  # offset 0 has hash 0 -> T[k]
    pred=np.array([T[int(x)] for x in (hv^k)])
    good=(pred==H[c]).all(); allok&=bool(good); kc.append(k)
    print('  chunk %2d pfn 0x%x  constant k_c = %3d = %s  (mesh bit %d)  all 32768 lines match: %s'%(c,pfn[c],k,format(k,'07b'),k>>6,good))
print('SAME masks + per-chunk 7-bit XOR constant explain all 16 chunks (524,288 lines, 0 mismatches):',allok)
print('distinct k_c values:',len(set(kc)))

print('\n=== structure of table hash -> node ===')
# is node position (within mesh) an affine function of hash? try index encodings
m0=sorted(n for (m,n) in nodes if m==0); m1=sorted(n for (m,n) in nodes if m==1)
print('node id sets equal on both meshes:',m0==m1,' count',len(m0))
print('node id = x<<7 | y<<3 | dev for all nodes:',all(n==(x<<7|y<<3|d) for (m,n),(x,y,d) in nodes.items()))
rank={n:i for i,n in enumerate(m0)}
def affine(f,dom=range(128)):
    return all(f(a^b)^f(a)^f(b)^f(0)==0 for a in dom for b in dom)
print('mesh(T[h]) == h>>6 for all h:',all((T[h]>>12)==(h>>6) for h in T))
print('same node for hash h and h^64 (mesh 0 and mesh 1 tables identical):',all((T[h]&4095)==(T[h^64]&4095) for h in range(64)))
print('rank of node in sorted node-id list is an affine function of hash (low 6 bits):',affine(lambda h:rank[T[h]&4095],range(64)))
print('dev bit affine in hash:',affine(lambda h:T[h]&1,range(64)))
for nm,f in (('x',lambda h:(T[h]>>7)&31),('y',lambda h:(T[h]>>3)&15),('raw node id',lambda h:T[h]&4095)):
    print(nm,'affine in hash:',affine(f,range(64)))
# find linear change of basis so that rank = G.h (6x6) if affine
if affine(lambda h:rank[T[h]&4095],range(64)):
    r0=rank[T[0]&4095]
    print('rank(T[0]) =',r0)
    # new masks: bit j of rank = parity over hash bits -> address-bit mask
    cols=[rank[T[1<<i]&4095]^r0 for i in range(6)]  # image of hash bit i
    newm=[]
    for j in range(5,-1,-1):
        m=0
        for i in range(6):
            if cols[i]>>j&1: m^=masks[6-i]
        newm.append(m)
    print('re-based node masks so that (hash ^ const) = rank in sorted node-id order:')
    for j,m in zip(range(5,-1,-1),newm): print('   r%d: addr bits %s'%(j,bits(m)))
    def rv(o):
        h=np.zeros_like(o)
        for m in newm: h=(h<<1)|parv(o&m)
        return h
    rr=rv(off)
    for c in range(16):
        rk=np.array([rank[int(x)&4095] for x in H[c]])
        d=rk^rr; assert (d==d[0]).all()
    print('  verified on all 16 chunks: rank(node) = r(offset) XOR per-chunk constant; constants:',[int(rank[int(H[c][0])&4095]) for c in range(16)])
    masks_r=[alt]+newm
print('table, chunk-0-relative hash (low 6 bits) -> node id (x,y,dev); mesh = hash bit 6:')
for h in range(64):
    n=T[h]&4095; print('  h=%2d -> 0x%03x %s'%(h,n,nodes[(0,n)]),end='\n' if h%4==3 else ' |')
print('sorted node list (rank -> node id):',[hex(n) for n in m0])

print('\n=== (2b) do higher physical bits explain the per-chunk constant? ===')
hi=[p>>9 for p in pfn]   # physical address bits 21.. -> bit 0 = addr bit 21
allv=0
for a in hi: allv|=a^hi[0]
vb=[i+21 for i in range(40) if allv>>i&1]; cb=[i+21 for i in range(40) if not allv>>i&1 and (hi[0]>>i)]
print('address bits >=21 that differ between chunks:',vb,'(count %d)'%len(vb))
print('address bits >=21 set in every chunk (constant, cannot be tested):',[i+21 for i in range(40) if all(a>>i&1 for a in hi)])
diffs=[hi[c]^hi[0] for c in range(1,16)]
def gf2rank(vs):
    b=[]
    for v in vs:
        for x in b: v=min(v,v^x)
        if v: b.append(v)
    return len(b)
rk=gf2rank(diffs); print('rank of the 15 chunk differences over GF(2):',rk,' unknowns per hash bit:',len(vb),' -> free dimensions per hash bit:',len(vb)-rk)
# hypothesis A: alternating continued, bits 22,24,...
for name,mask in (('even bits 22,24,..,40',sum(1<<(b-21) for b in range(22,41,2))),('odd bits 21,23,..,41',sum(1<<(b-21) for b in range(21,42,2)))):
    pred=[bin(a&mask).count('1')&1 for a in hi]
    rel=[p^pred[0] for p in pred]; obs=[i^inv[0] for i in inv]
    print('hypothesis mesh inversion = XOR of',name,': predicted (relative to chunk 0)',rel,' observed',obs,' mismatching chunks',sum(a!=b for a,b in zip(rel,obs)))
# general solve per hash bit: find mask w over varying bits with parity(w & diff_c) = k_c bit ^ k_0 bit
def solve(rhs):
    # gaussian elimination: rows = diffs (as ints over varying bits), augmented rhs
    rows=[(d,r) for d,r in zip(diffs,rhs)]
    piv=[]
    for i in range(len(rows)):
        d,r=rows[i]
        for pd,pr,pb in piv:
            if d>>pb&1: d^=pd; r^=pr
        if d: 
            pb=d.bit_length()-1
            piv=[((qd^d,qr^r,qb) if qd>>pb&1 else (qd,qr,qb)) for qd,qr,qb in piv]
            piv.append((d,r,pb))
        elif r: return None,None
    # particular solution: free vars 0. rows are reduced on pivots; solve w with w&pivotbits
    # brute: w has only pivot bits; need parity(w&d)=r for each pivot row; rows reduced so pivot bit unique per row
    # solve by back substitution over pivot bits
    pbits=[pb for _,_,pb in piv]
    # matrix restricted to pivot bits is identity after full reduction? rows reduced wrt other pivots -> yes
    w=0
    for d,r,pb in piv:
        if r: w|=1<<pb
    # verify (non-pivot bits of d are multiplied by w=0)
    assert all((bin(w&d).count('1')&1)==r for d,r in zip(diffs,rhs))
    return w,len(piv)
print('general GF(2) solve over bits 21..: one equation per chunk pair (c,0), 15 equations')
for j in range(6,-1,-1):
    rhs=[((kc[c]^kc[0])>>j)&1 for c in range(1,16)]
    w,r=solve(rhs)
    print('  hash bit h%d: consistent=%s rank=%s; ONE particular solution (not unique, 2^%d solutions): addr bits %s'%(j,w is not None,r,len(vb)-rk, bits(w,21) if w is not None else None))
# count solutions that are sparse for the mesh bit: check whether a solution exists of the alternating shape within the family
# null space test: is any solution for the mesh bit a subset of even bits / odd bits?
rhs=[((kc[c]^kc[0])>>6)&1 for c in range(1,16)]
for name,allowed in (('even bits only',[b for b in vb if b%2==0]),('odd bits only',[b for b in vb if b%2==1])):
    # restrict unknowns
    al=sum(1<<(b-21) for b in allowed)
    dd=[d&al for d in diffs]
    # solve restricted
    rows=[];cons=True;basis=[]
    for d,r in zip(dd,rhs):
        for bd,br in basis:
            if d>>(bd.bit_length()-1)&1: d^=bd; r^=br
        if d: basis.append((d,r))
        elif r: cons=False
    print('  mesh bit, solution using %s (%d bits): consistent=%s, rank %d'%(name,len(allowed),cons,len(basis)))

print('\n=== (4) virtual vs physical ===')
V=lambda c,o: virt[c]+o*64
info=lambda c,o: dict(line=c*32768+o,chunk=c,offset_in_chunk_bytes=o*64,virt=hex(V(c,o)),virt_low21=hex(V(c,o)&0x1fffff),phys=hex(pa(c,o)),phys_low21=hex(pa(c,o)&0x1fffff),phys_bits_21_up=hex(pa(c,o)>>21),mesh=int(M_[c][o]),node_id=hex(int(H[c][o])&4095),**dict(zip(('x','y','dev'),nodes[(int(M_[c][o]),int(H[c][o])&4095)])),hash_rel_chunk0=int(hv[o]^kc[c]))
print('virtual low 21 bits == physical low 21 bits for every chunk start:',all((virt[c]&0x1fffff)==((pfn[c]*4096)&0x1fffff) for c in range(16)))
same_mesh=sum(1 for a,b in itertools.combinations(range(16),2) if inv[a]==inv[b]); diff_mesh=120-same_mesh
same_home=sum(1 for a,b in itertools.combinations(range(16),2) if kc[a]==kc[b])
print('chunk pairs (120): same offset -> same mesh for all offsets in %d pairs, different mesh for all offsets in %d pairs; same home node in %d pairs'%(same_mesh,diff_mesh,same_home))
# count over all line pairs with equal low-21 virtual bits
tot=120*32768
print('line pairs with identical low 21 virtual bits (same offset, two chunks): %d; different mesh: %d (%.2f %%); different home node (mesh,node): %d (%.2f %%)'%(tot,diff_mesh*32768,100*diff_mesh/120,(120-same_home)*32768,100*(120-same_home)/120))
# neighbours
dm=(mesh[1:]!=mesh[:-1]); dh=(home[1:]!=home[:-1])
print('neighbouring lines 64 B apart in VIRTUAL order, whole buffer: pairs %d; different mesh %d (%.3f %%); different home node %d (%.3f %%)'%(N-1,dm.sum(),100*dm.mean(),dh.sum(),100*dh.mean()))
inch=(np.arange(N-1)%32768)!=32767
print('  only pairs inside one 2 MiB chunk (also physically adjacent): pairs %d; different mesh %d (%.3f %%); different home node %d (%.3f %%)'%(inch.sum(),dm[inch].sum(),100*dm[inch].mean(),dh[inch].sum(),100*dh[inch].mean()))
print('  first 16 lines of chunk 0 mesh pattern:',''.join(map(str,M_[0][:16])))
dx=(node[1:]!=node[:-1])
print('  different node id ignoring mesh, inside chunk: %d (%.3f %%)'%(dx[inch].sum(),100*dx[inch].mean()))
# examples
cA=0; cB=next(c for c in range(1,16) if inv[c]!=inv[0]); cC=next(c for c in range(1,16) if inv[c]==inv[0])
o=0x1000//64  # offset 0x1000: a non-zero offset
ex=dict(
 source=dict(homes=D+'homes.csv',chunks=D+'chunks.csv',nodes=D+'nodes.csv',script=os.path.abspath(__file__)),
 note='physical address = pfn*4096 + offset in chunk; virtual = chunk virt + offset. hash_rel_chunk0 is the 7-bit hash relative to chunk 0 (bit 6 = mesh).',
 same_virtual_low21_different_mesh=[info(cA,0),info(cB,0)],
 same_virtual_low21_different_mesh_offset_0x1000=[info(cA,o),info(cB,o)],
 same_virtual_low21_same_mesh_different_node=[info(cA,0),info(cC,0)],
 neighbours_64B_different_mesh=[info(0,0),info(0,1)],
 neighbours_64B_same_mesh_different_node=None,
 neighbours_64B_same_home=None,
 masks_addr_bits={('h%d'%(6-i)):bits(m) for i,m in enumerate(masks)},
 masks_rank_basis_addr_bits=({'mesh':bits(alt),**{('r%d'%j):bits(m) for j,m in zip(range(5,-1,-1),newm)}} if 'newm' in dir() else None),
 chunk_constants=[dict(chunk=c,virt=hex(virt[c]),phys=hex(pfn[c]*4096),k=kc[c],mesh_inverted_vs_bits_6_to_20=inv[c],home_of_offset0=hex(int(H[c][0])&4095),mesh_of_offset0=int(M_[c][0])) for c in range(16)],
 neighbour_stats=dict(pairs_in_chunk=int(inch.sum()),diff_mesh=int(dm[inch].sum()),diff_home=int(dh[inch].sum()),pairs_all=N-1,diff_mesh_all=int(dm.sum()),diff_home_all=int(dh.sum())),
)
i=next(i for i in range(32767) if M_[0][i]==M_[0][i+1] and H[0][i]!=H[0][i+1]); ex['neighbours_64B_same_mesh_different_node']=[info(0,i),info(0,i+1)]
js=[i for i in range(32767) if H[0][i]==H[0][i+1]]
ex['neighbours_64B_same_home']=[info(0,js[0]),info(0,js[0]+1)] if js else 'none in chunk 0'
json.dump(ex,open(OUT+'/examples.json','w'),indent=1)
for k in ('same_virtual_low21_different_mesh','same_virtual_low21_different_mesh_offset_0x1000','same_virtual_low21_same_mesh_different_node','neighbours_64B_different_mesh','neighbours_64B_same_mesh_different_node','neighbours_64B_same_home'):
    print(k); 
    for e in (ex[k] if isinstance(ex[k],list) else [ex[k]]): print('   ',e)
# hand-check of example hash from masks
for c,o in ((0,0),(0,1),(cB,0)):
    a=pa(c,o); print('check line chunk %d off %d phys 0x%x: mesh-mask parity of low 21 bits = %d, chunk inv = %d, mesh = %d'%(c,o,a,bin((a&0x1fffff)&(alt<<6)).count('1')&1,inv[c],M_[c][o]))
print('wrote',OUT+'/examples.json')
