import csv
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z'
m=[int(r['mesh']) for r in csv.DictReader(open(R+'/full/homes.csv'))]
N=len(m)
print('aligned pairs (2k,2k+1) with different mesh:',sum(m[i]!=m[i+1] for i in range(0,N,2)),'of',N//2)
print('pairs (2k+1,2k+2) inside a chunk with different mesh:',sum(m[i]!=m[i+1] for i in range(1,N-1,2) if (i+1)%32768),'of',sum(1 for i in range(1,N-1,2) if (i+1)%32768))
# worst imbalance |mesh0-mesh1| over every window of w consecutive lines
import itertools
pre=[0]
for x in m: pre.append(pre[-1]+(1 if x else -1))
for w in (2,3,4,8,16,63,64,65,128,1024,4096,32768):
    worst=max(abs(pre[i+w]-pre[i]) for i in range(0,N-w+1))
    print('window',w,'lines: largest |mesh1 - mesh0| =',worst)
