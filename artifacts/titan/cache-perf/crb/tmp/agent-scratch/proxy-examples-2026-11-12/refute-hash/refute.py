import csv, numpy as np, itertools, sys
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/full/'
N=524288; C=16; L=32768
mesh=np.zeros(N,int); node=np.zeros(N,int)
for r in csv.DictReader(open(R+'homes.csv')):
    i=int(r['line']); mesh[i]=int(r['mesh']); node[i]=int(r['node_id_hex'],16)
ch=list(csv.DictReader(open(R+'chunks.csv')))
virt=[int(c['virt_hex'],16) for c in ch]; base=[int(c['pfn_hex'],16)*4096 for c in ch]
nodes={}
for r in csv.DictReader(open(R+'nodes.csv')):
    nodes[(int(r['mesh']),int(r['node_id_hex'],16))]=(int(r['x']),int(r['y']),int(r['dev']),int(r['port']))
print('chunks',len(ch),'contig',[c['contiguous'] for c in ch].count('1'),'low21 zero',all(b&0x1fffff==0 for b in base), 'virt low21 zero',all(v&0x1fffff==0 for v in virt))
home=mesh*4096+node
print('distinct homes',len(set(home.tolist())),'nodes.csv',len(nodes), 'all homes in nodes.csv', all((h>>12,h&4095) in nodes for h in set(home.tolist())))
print('node id = x<<7|y<<3|dev for', sum(1 for (m,n),(x,y,d,p) in nodes.items() if n==(x<<7|y<<3|d)),'of',len(nodes),'; ports',set(v[3] for v in nodes.values()))
print('same id set both meshes', {n for (m,n) in nodes if m==0}=={n for (m,n) in nodes if m==1})
H=home.reshape(C,L); M=mesh.reshape(C,L)
off=np.arange(L)
# (1) kernel
K0=off[H[0]==H[0,0]]; Ks=set(K0.tolist())
print('|K|',len(Ks),'closed',all((a^b) in Ks for a in K0 for b in K0))
def rank(vs):
    vs=list(vs); r=0; basis=[]
    for v in vs:
        for b in basis: v=min(v,v^b)
        if v: basis.append(v); r+=1
    return r
print('dim K',rank(K0.tolist()))
for c in range(C):
    Kc=off[H[c]==H[c,0]]
    assert set(Kc.tolist())==Ks, c
print('same K in all 16 chunks: yes')
# coset property: home(o)==home(o') iff o^o' in K. canonical rep = min over coset
Karr=np.array(sorted(Ks))
rep=np.min(off[:,None]^Karr[None,:],axis=1)
print('cosets',len(set(rep.tolist())))
ok=True
for c in range(C):
    pairs=set(zip(rep.tolist(),H[c].tolist()))
    if len(pairs)!=128 or len({p[0] for p in pairs})!=128 or len({p[1] for p in pairs})!=128: ok=False
print('home <-> coset bijection in every chunk',ok)
# claimed kernel basis
kb=[[8,20],[6,7,8,19],[6,7,9,18],[6,7,10,17],[6,7,11,16],[6,7,12,15],[6,14],[7,13]]
kv=[sum(1<<(b-6) for b in v) for v in kb]
print('claimed kernel vectors in K',[v in Ks for v in kv],'rank',rank(kv))
# chunk translation d_c: home_c(o)=home_0(o^d_c)
t0={h:r for r,h in zip(rep.tolist(),H[0].tolist())}
ds=[]
for c in range(C):
    d=t0[H[c,0]]; ds.append(d)
    assert np.array_equal(H[c],H[0][off^d]),c
print('translation offsets d_c (line offsets, coset reps)',ds,'distinct',len(set(ds)))
print('exhaustive: 524288 lines match home_0(o^d_c)')
# claimed masks
masks={6:0x155540,5:0xfa080,4:0x180100,3:0x40200,2:0x20400,1:0x10800,0:0x9000}
bl={6:[6,8,10,12,14,16,18,20],5:[7,13,15,16,17,18,19],4:[8,19,20],3:[9,18],2:[10,17],1:[11,16],0:[12,15]}
print('mask hex match bit lists',all(sum(1<<b for b in bl[k])==masks[k] for k in masks))
par=lambda x: bin(x).count('1')&1
def hsh(a,ms=masks): return sum(par(a&ms[k])<<k for k in ms)
h_off=np.array([hsh(o<<6) for o in range(L)])
print('hash values',len(set(h_off.tolist())),'kernel of hash == K',set(off[h_off==0].tolist())==Ks)
T={}
for o in range(L): T.setdefault(int(h_off[o]),set()).add(int(H[0,o]))
print('T single valued',all(len(v)==1 for v in T.values()),'bijection',len({next(iter(v)) for v in T.values()}))
T={k:next(iter(v)) for k,v in T.items()}
kc=[hsh(d<<6) for d in ds]
print('k_c',kc)
claimed=[0,41,61,108,50,76,114,51,55,60,16,42,37,26,91,18]
print('k_c match claim',kc==claimed,'distinct',len(set(kc)))
mm=0
for c in range(C):
    pred=np.array([T[h] for h in (h_off^kc[c]).tolist()]); mm+=int((pred!=H[c]).sum())
print('mismatches with masks+k_c',mm)
# (2) mesh
a6=np.array([par((o<<6)&masks[6]) for o in range(L)])
inv=[]
for c in range(C):
    x=M[c]^a6; assert len(set(x.tolist()))==1,c; inv.append(int(x[0]))
print('inv_c',inv,'inverted chunks',[c for c in range(C) if inv[c]])
print('first 16 lines mesh',''.join(map(str,M[0,:16])))
even=sum(1<<b for b in range(6,37,2)); odd_hi=sum(1<<b for b in range(21,37,2))
phys=np.array([base[c]+64*o for c in range(C) for o in range(L)],dtype=object)
pm=np.array([par(int(p)&even) for p in phys])
print('mesh == parity even bits 6..36: mismatches',int((pm!=mesh).sum()))
for c0 in (0,1):
    print('  with constant',c0, int(((pm^c0)!=mesh).sum()))
# odd alternative: even bits 6..20 + odd bits 21..35
alt=sum(1<<b for b in range(6,21,2))|odd_hi
for const in (0,1):
    bad=[c for c in range(C) if (par(base[c]&alt)^const)!=inv[c]]
    print('odd-high-bit alternative const',const,'fails in chunks',len(bad),bad)
# also relative to chunk 0
bad=[c for c in range(C) if (par((base[c]^base[0])&odd_hi))!=inv[c]^inv[0]]
print('odd alt relative to chunk0 fails',len(bad),bad)
# bit variation
vary=[b for b in range(64) if len({(x>>b)&1 for x in base})>1]
print('bits varying among chunks',vary)
print('bits 37..45 values',{b:sorted({(x>>b)&1 for x in base}) for b in range(37,46)})
print('top set bit max',max(x.bit_length()-1 for x in base))
diffs=[(base[c]^base[0])>>21 for c in range(1,C)]
print('rank of 15 diffs over bits 21..36',rank(diffs),'; rank of 16 bases (affine const included)',rank([(b>>21)|(1<<20) for b in base]))
# nullspace of diffs: vectors m (16 bits) with par(m&d)=0 for all d
ns=[m for m in range(1,1<<16) if all(par(m&d)==0 for d in diffs)]
print('undetectable masks',[[21+i for i in range(16) if m>>i&1] for m in ns])
evd=[sum(((d>>(2*i+1))&1)<<i for i in range(8)) for d in diffs]  # bits 22,24..36
print('rank restricted to even bits 22..36',rank(evd))
sol=[m for m in range(1<<8) if all(par(m&e)==(inv[c+1]^inv[0]) for c,e in enumerate(evd))]
print('even-only solutions',[[22+2*i for i in range(8) if m>>i&1] for m in sol])
allsol=[m for m in range(1<<16) if all(par(m&d)==(inv[c+1]^inv[0]) for c,d in enumerate(diffs))]
print('all solutions for mesh high mask',len(allsol),[[21+i for i in range(16) if m>>i&1] for m in allsol])
# absolute constant test: parity even bits 22..36 of base == inv_c absolute (inv_c computed absolute here)
print('absolute: par(base & even) == inv_c for all', all(par(base[c]&even)==inv[c] for c in range(C)))
# (3) table
print('h6==mesh',all((h>>6)==(T[h]>>12) for h in T),'h0==dev',all((h&1)==nodes[(T[h]>>12,T[h]&4095)][2] for h in T),
 'h,h^1 same XP',all(nodes[(T[h]>>12,T[h]&4095)][:2]==nodes[(T[h^1]>>12,T[h^1]&4095)][:2] for h in T))
def fmt(h): 
    x,y,d,p=nodes[(T[h]>>12,T[h]&4095)]; return '%d:0x%03x(%d,%d)'%(h,T[h]&4095,x,y)
print('mesh0:',' '.join(fmt(h) for h in range(0,64,2)))
print('mesh1:',' '.join(fmt(h) for h in range(64,128,2)))
same=[h for h in range(0,64,2) if nodes[(0,T[h]&4095)][:2]==nodes[(1,T[h+64]&4095)][:2]]
print('same XP for same low hash',len(same),[nodes[(0,T[h]&4095)][:2] for h in same])
print('XPs with home nodes per mesh',len({v[:2] for (m,n),v in nodes.items() if m==0}),len({v[:2] for (m,n),v in nodes.items() if m==1}))
# affine tests: is bit j of f(h) an affine fn of h bits (per mesh, 6 bits)?
def affine(vals):  # vals: dict h(0..63)->int ; test each bit
    res=[]
    for j in range(max(vals.values()).bit_length()):
        f=lambda h:(vals[h]>>j)&1
        c=f(0); co=[f(1<<i)^c for i in range(6)]
        res.append(all(f(h)==c^(sum(co[i]&(h>>i) for i in range(6))&1) for h in range(64)))
    return res
for m in (0,1):
    ids=sorted(n for (mm_,n) in nodes if mm_==m)
    g=lambda h:T[h+64*m]&4095
    print('mesh',m,'affine x',affine({h:nodes[(m,g(h))][0] for h in range(64)}),'y',affine({h:nodes[(m,g(h))][1] for h in range(64)}),
      'id',affine({h:g(h) for h in range(64)}),'rank',affine({h:ids.index(g(h)) for h in range(64)}))
# mesh1 table = mesh0 table shifted by constant? or affine re-index?
t0n={h:T[h]&4095 for h in range(64)}; t1n={h:T[h+64]&4095 for h in range(64)}
print('mesh1 = mesh0 xor-shift by constant:',[k for k in range(64) if all(t1n[h]==t0n[h^k] for h in range(64))])
inv0={v:k for k,v in t0n.items()}
perm={h:inv0[t1n[h]] for h in range(64)}
print('mesh1 = mesh0 o affine map:',all(affine(perm)), affine(perm))
# high-bit particular solution
hi={6:[22,24,26,28,30,32,34,36],5:[29,34,36],4:[31,32],3:[24,26,28,29,30,33,35],2:[22,29,34],1:[23,28,35],0:[24,27,36]}
full={k:masks[k]|sum(1<<b for b in hi[k]) for k in masks}
hf=np.array([hsh(int(p),full) for p in phys])
TT={}
for h,v in zip(hf.tolist(),home.tolist()): TT.setdefault(h,set()).add(v)
print('full masks: single table',all(len(v)==1 for v in TT.values()),len(TT),'mismatch lines',sum(1 for h,v in zip(hf.tolist(),home.tolist()) if next(iter(TT[h]))!=v) if all(len(v)==1 for v in TT.values()) else 'n/a')
# per hash bit, number of solutions in 16 high bits
for k in range(7):
    rhs=[(kc[c]>>k)&1 for c in range(1,C)]
    s=[m for m in range(1<<16) if all(par(m&d)==r for d,r in zip(diffs,rhs))]
    print(' h%d high-bit solutions'%k,len(s),'claimed in set',sum(1<<(b-21) for b in hi[k]) in s)
# (4) stats
tot=dm=dh=0
cp_m=0
for a,b in itertools.combinations(range(C),2):
    tot+=L; x=int((M[a]!=M[b]).sum()); dm+=x; dh+=int((H[a]!=H[b]).sum()); cp_m+= x==L
    assert x in (0,L)
print('same-offset pairs',tot,'diff mesh',dm,'%.4f%%'%(100*dm/tot),'chunk pairs diff mesh',cp_m,'diff home',dh,'%.4f%%'%(100*dh/tot))
Nn=node.reshape(C,L)
p=C*(L-1); a=int((M[:,1:]!=M[:,:-1]).sum()); b=int((H[:,1:]!=H[:,:-1]).sum()); n=int((Nn[:,1:]!=Nn[:,:-1]).sum())
print('in-chunk neighbours',p,'diff mesh',a,'%.4f%%'%(100*a/p),'diff home',b,'%.4f%%'%(100*b/p),'diff node id',n,'%.4f%%'%(100*n/p))
a=int((mesh[1:]!=mesh[:-1]).sum()); b=int((home[1:]!=home[:-1]).sum())
print('whole buffer',N-1,'diff mesh',a,'%.4f%%'%(100*a/(N-1)),'diff home',b,'%.4f%%'%(100*b/(N-1)))
print('boundary pairs: mesh differ',[int(mesh[c*L]!=mesh[c*L-1]) for c in range(1,C)],'home differ',[int(home[c*L]!=home[c*L-1]) for c in range(1,C)])
# examples
for name,l in [('A',0),('B',98304),('C',1),('D',32768),('E1',64),('E2',98368),('F1',3),('F2',4)]:
    c=l//L; o=l%L; x,y,d,pt=nodes[(int(mesh[l]),int(node[l]))]
    pa=base[c]+64*o
    print(name,'line',l,'chunk',c,'virt',hex(virt[c]+64*o),'phys',hex(pa),'phys>>21',hex(pa>>21),'mesh',mesh[l],'node',hex(node[l]),(x,y,d),'evenpar6..36',par(pa&even),'par6..20',par(pa&masks[6]),'inv',inv[c])
