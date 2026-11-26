import csv,json,collections
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
lat=[r for r in csv.DictReader(open(R+'full/latency.csv')) if r['mesh']!='-1']
pos=json.load(open(R+'core-positions.json'))
print([k for k in pos][:10])
def g(core,mesh,node):
    return [float(r['ns_median']) for r in lat if r['core']==str(core) and r['mesh']==str(mesh) and r['node_id_hex']==node]
print('cpu0 0x128',g(0,0,'0x128'),'0x129',g(0,0,'0x129'))
print('cpu0 m1 0x290',g(0,1,'0x290'),'0x291',g(0,1,'0x291'))
print('cpu0 m1 0x390',g(0,1,'0x390'))
print('cpu64 m0 0x128',g(64,0,'0x128'), 'cpu64 m1 0x290/291',g(64,1,'0x290'),g(64,1,'0x291'))
for x,y,m in [(1,2,0),(5,5,1),(2,5,0),(5,2,1)]:
    print('cpu0',m,x,y,[(r['node_id_hex'],r['ns_median']) for r in lat if r['core']=='0' and r['mesh']==str(m) and r['x']==str(x) and r['y']==str(y)])
cores=sorted({int(r['core']) for r in lat}); print(len(cores))
own=[];oth=[]
for r in lat:
    c=int(r['core']); cm=0 if c<64 else 1
    (own if int(r['mesh'])==cm else oth).append(float(r['ns_median']))
print('own',min(own),max(own),'other',min(oth),max(oth))
# verify.csv
for r in csv.DictReader(open(R+'full/verify.csv')): print({k:r[k] for k in ['core','mesh','node_id_hex','home_acc','home_miss','l2_refills_a','ns_median_a','acc_mesh0','miss_mesh0','acc_mesh1','miss_mesh1','l2_refills_b','ns_median_b']})
