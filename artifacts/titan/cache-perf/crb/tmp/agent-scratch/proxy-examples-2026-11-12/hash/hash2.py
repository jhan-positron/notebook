#!/usr/bin/env python3
"""Addendum to hash.py: mesh-1 table vs mesh-0 table, null space of the high-bit system."""
import csv, json, numpy as np
D='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/full/'
pfn=[int(r['pfn_hex'],16) for r in csv.DictReader(open(D+'chunks.csv'))]
nodes={(int(r['mesh']),int(r['node_id_hex'],16)):(int(r['x']),int(r['y']),int(r['dev'])) for r in csv.DictReader(open(D+'nodes.csv'))}
home=np.zeros(524288,int)
for r in csv.DictReader(open(D+'homes.csv')): home[int(r['line'])]=int(r['mesh'])*4096+int(r['node_id_hex'],16)
MASKS=[[6,8,10,12,14,16,18,20],[7,13,15,16,17,18,19],[8,19,20],[9,18],[10,17],[11,16],[12,15]]
def h(a): 
    v=0
    for m in MASKS: v=v<<1|(sum(a>>b&1 for b in m)&1)
    return v
T={}
for o in range(32768): T[h(o*64)]=int(home[o])
T0=[T[i]&4095 for i in range(64)]; T1=[T[i+64]&4095 for i in range(64)]
ds=[d for d in range(64) if all(T1[i]==T0[i^d] for i in range(64))]
print('constants d with T1[h]==T0[h^d] for all 64 h:',ds)
p0={n:i for i,n in enumerate(T0)}; perm=[p0[n] for n in T1]
aff=all(perm[a^b]^perm[a]^perm[b]^perm[0]==0 for a in range(64) for b in range(64))
print('mesh-1 table = mesh-0 table composed with a GF(2)-affine map of the 6 node bits:',aff,' perm[0]=',perm[0],' images of unit bits (xor perm[0]):',[perm[1<<i]^perm[0] for i in range(6)])
print('dev bit: T[h]&1 == h&1 for all 128 h:',all((T[i]&1)==(i&1) for i in range(128)))
print('h and h^1 share the crosspoint for all 128 h:',all((T[i]>>3)==(T[i^1]>>3) and (T[i]>>12)==(T[i^1]>>12) for i in range(128)))
print('mesh 1 table (hash 64+h -> node id (x,y,dev)):')
for i in range(64):
    print('  h=%3d -> 0x%03x %s'%(i+64,T1[i],nodes[(1,T1[i])]),end='\n' if i%4==3 else ' |')
# is mesh-1 node the mirror of the mesh-0 node at the same low hash? list (x0,y0)->(x1,y1) for even h
pairs=sorted({(nodes[(0,T0[i])][:2],nodes[(1,T1[i])][:2]) for i in range(0,64,2)})
print('crosspoint on mesh 0 at low hash h  ->  crosspoint on mesh 1 at the same low hash:',pairs)
print('same crosspoint for same low hash in %d of 32 cases'%sum(a==b for a,b in pairs))
# null space of high-bit system
hi=[p>>9 for p in pfn]; diffs=[a^hi[0] for a in hi[1:]]
nb=16
null=[w for w in range(1,1<<nb) if all(bin(w&d).count('1')%2==0 for d in diffs)]
print('masks over addr bits 21..36 whose parity is the same in all 16 chunks (cannot be detected):',[[i+21 for i in range(nb) if w>>i&1] for w in null])
print('so every solution = particular solution XOR any of these',len(null)+1,'(incl. empty) masks; bits 37..40 are 0 and bit 41 is 1 in every chunk, untestable')
# per-bit: which single high bits are forced? a bit b is "determined" if it is not in support of any null vector
sup=0
for w in null: sup|=w
print('bits whose membership is ambiguous (in the support of the null space):',[i+21 for i in range(nb) if sup>>i&1])
# full check with one particular full-address mask set (bits 6..36), absolute constant only from untestable bits
HI=[[22,24,26,28,30,32,34,36],[29,34,36],[31,32],[24,26,28,29,30,33,35],[22,29,34],[23,28,35],[24,27,36]]
FULL=[a+b for a,b in zip(MASKS,HI)]
def hf(a):
    v=0
    for m in FULL: v=v<<1|(sum(a>>b&1 for b in m)&1)
    return v
G={}; bad=0
for l in range(524288):
    a=pfn[l>>15]*4096+(l&32767)*64
    if G.setdefault(hf(a),int(home[l]))!=home[l]: bad+=1
print('full-address check, masks over bits 6..36 (one particular solution): lines 524288, mismatches',bad,', distinct hash values',len(G),', distinct homes',len(set(G.values())))
print('mesh == parity(addr bits 6,8,...,36) XOR c for all lines; c =',{int(home[l]>>12)^(sum((pfn[l>>15]*4096+(l&32767)*64)>>b&1 for b in range(6,37,2))&1) for l in range(0,524288,1)})
json.dump(dict(full_masks_particular={'h%d'%(6-i):m for i,m in enumerate(FULL)},table_full_hash_to_home={str(k):dict(mesh=v>>12,node_id=hex(v&4095),xyd=nodes[(v>>12,v&4095)]) for k,v in sorted(G.items())}),open('table.json','w'),indent=0)
print('example hashes (full masks): ',[(hex(a),hf(a),hex(G[hf(a)])) for a in (0x21dd7e00000,0x21dd7e00040,0x211c3c00000,0x211c3c01000,0x21dd7e01000,0x21669a00000)])
