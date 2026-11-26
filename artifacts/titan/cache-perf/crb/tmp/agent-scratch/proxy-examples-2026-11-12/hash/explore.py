import csv, numpy as np
D='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/full/'
ch=list(csv.DictReader(open(D+'chunks.csv')))
pfn=[int(r['pfn_hex'],16) for r in ch]
mesh=np.zeros(524288,int); node=np.zeros(524288,int)
for r in csv.DictReader(open(D+'homes.csv')):
    l=int(r['line']); mesh[l]=int(r['mesh']); node[l]=int(r['node_id_hex'],16)
home=mesh*4096+node
print('distinct homes',len(set(home)))
H=home.reshape(16,32768)
# kernel per chunk
Ks=[]
for c in range(16):
    K=np.nonzero(H[c]==H[c][0])[0]
    Ks.append(set(K.tolist()))
    print(c,hex(pfn[c]),len(K),'same as chunk0 kernel',Ks[c]==Ks[0], 'home(0)',hex(H[c][0]))
K=sorted(Ks[0]); Kset=Ks[0]
print('closed', all((a^b) in Kset for a in K for b in K))
# basis of K
def basis(vs):
    b=[]
    for v in vs:
        for x in b: v=min(v,v^x)
        if v: b.append(v)
    return b
B=basis(K); print('dim K',len(B),[bin(x) for x in sorted(B)])
