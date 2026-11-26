import csv,collections
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
h=[(r['mesh'],r['node_id_hex']) for r in csv.DictReader(open(R+'full/homes.csv'))]
pairs=collections.Counter()
for k in range(0,len(h),2):
    a,b=h[k],h[k+1]
    if a[0]=='1': a,b=b,a
    pairs[(a,b)]+=1
print(len(pairs)); 
m=collections.defaultdict(set)
for (a,b) in pairs: m[a].add(b)
print(max(len(v) for v in m.values()))
for a in [('0','0x90'),('0','0x91'),('0','0x128'),('0','0x129')]: print(a,m[a])
lat=[r for r in csv.DictReader(open(R+'full/latency.csv')) if r['mesh']!='-1']
L={(int(r['core']),r['mesh'],r['node_id_hex']):float(r['ns_median']) for r in lat}
# node-level: for cores of mesh 0, compare lat to remote node b with lat to paired own node a, vs other node on same xp
import math
def sib(n): v=int(n,16); return hex(v^1)
d1=[];d2=[];dmin=[]
for a,bs in m.items():
    b=list(bs)[0]
    for c in range(64):
        x=L[(c,'1',b[1])]; d1.append(x-L[(c,'0',a[1])]); d2.append(x-L[(c,'0',sib(a[1]))]); dmin.append(x-min(L[(c,'0',a[1])],L[(c,'0',sib(a[1]))]))
rms=lambda d: math.sqrt(sum(x*x for x in d)/len(d))
print('rms paired node',rms(d1),'sibling',rms(d2),'min of two',rms(dmin))
# sizes of dev differences
dd=[L[(c,'0',n)]-L[(c,'0',sib(n))] for c in range(64) for (mm,n) in m if int(n,16)%2==0]
print('own dev0-dev1 rms',rms(dd), min(dd),max(dd))
big=[(c,n,round(L[(c,'0',n)]-L[(c,'0',sib(n))],2)) for c in range(64) for (mm,n) in m if int(n,16)%2==0 and abs(L[(c,'0',n)]-L[(c,'0',sib(n))])>2]
print(len(big),big[:40])
