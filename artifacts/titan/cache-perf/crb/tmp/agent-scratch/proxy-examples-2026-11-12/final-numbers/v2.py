import csv,collections,json,statistics as S,math
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
rows=[r for r in csv.DictReader(open(R+'full/latency.csv'))]
pos=json.load(open(R+'core-positions.json'))['pos']
cores=sorted(set(int(r['core']) for r in rows)); print('cores',len(cores),cores[0],cores[-1], 'lines',collections.Counter(r['lines'] for r in rows))
cm={int(c):(p['mesh'],p['x'],p['y']) for c,p in pos.items()}
print('cpu0',cm[0],'cpu64',cm[64], 'mesh by cpu ok',all((c>=64)==(cm[c][0]==1) for c in cores))
for m in (0,1):
    xs=collections.Counter(cm[c][1:] for c in cores if cm[c][0]==m); print('mesh',m,'cores',sum(xs.values()),'xps',len(xs),set(xs.values()), 'cols',sorted(set(k[0] for k in xs)))
L={}
for r in rows:
    if r['mesh']=='-1': continue
    L[(int(r['core']),int(r['mesh']),int(r['node_id_hex'],16))]=float(r['ns_median'])
own=[v for (c,m,n),v in L.items() if m==cm[c][0]]; oth=[v for (c,m,n),v in L.items() if m!=cm[c][0]]
print('own',min(own),max(own),len(own),'other',min(oth),max(oth),len(oth))
for c,m,n in [(0,0,0x128),(0,1,0x290),(0,1,0x390),(64,0,0x128),(0,0,0x129),(0,1,0x291),(0,1,0x391),(64,0,0x129),(64,1,0x290),(64,1,0x291)]: print(c,m,hex(n),L[(c,m,n)])
nodes={(int(r['mesh']),int(r['node_id_hex'],16)):(int(r['x']),int(r['y'])) for r in csv.DictReader(open(R+'full/nodes.csv'))}
# cpu0 grid per xp: min of two devs? list
for m in (0,1):
    g=collections.defaultdict(list)
    for (c,mm,n),v in L.items():
        if c==0 and mm==m: g[nodes[(mm,n)]].append(v)
    print('cpu0 mesh',m,'min-of-dev lowest',sorted((min(v),k) for k,v in g.items())[:3],'highest',sorted((min(v),k) for k,v in g.items())[-2:])
    print('   mean-of-dev lowest',sorted((sum(v)/2,k) for k,v in g.items())[:3], sorted((sum(v)/2,k) for k,v in g.items())[-2:])
    print('   all',sorted((round(min(v),1),round(max(v),1),k) for k,v in g.items())[:4])
# fit: per node, reader mesh 0, values = per reader XP min of 2 cores
def fit(reader,hm):
    rx=collections.defaultdict(list)
    for c in cores:
        if cm[c][0]==reader: rx[cm[c][1:]].append(c)
    cands=sorted(set(nodes[k] for k in nodes if k[0]==reader))
    out={}
    for (m,n),xy in nodes.items():
        if m!=hm: continue
        pts=[(k,min(L[(c,m,n)] for c in cs)) for k,cs in rx.items()]
        best=[]
        for cand in cands:
            d=[abs(k[0]-cand[0])+abs(k[1]-cand[1]) for k,_ in pts]; y=[v for _,v in pts]
            md=sum(d)/len(d); my=sum(y)/len(y)
            sl=sum((a-md)*(b-my) for a,b in zip(d,y))/sum((a-md)**2 for a in d); ic=my-sl*md
            rms=math.sqrt(sum((ic+sl*a-b)**2 for a,b in zip(d,y))/len(y))
            best.append((rms,cand,sl,ic,len(pts)))
        best.sort(); out[(m,n)]=best
    return out
res={}
for reader in (0,1):
    for hm in (0,1):
        o=fit(reader,hm); res[(reader,hm)]=o
        rm=[v[0][0] for v in o.values()]
        ties=sum(1 for v in o.values() if abs(v[1][0]-v[0][0])<1e-9)
        print('reader',reader,'home mesh',hm,'npts',list(o.values())[0][0][4],'rms med %.3f worst %.3f slope med %.3f icpt med %.3f ties %d'%(S.median(rm),max(rm),S.median(v[0][2] for v in o.values()),S.median(v[0][3] for v in o.values()),ties))
        if reader==hm: print('  true recovered',sum(v[0][1]==nodes[k] or (abs(v[1][0]-v[0][0])<1e-9 and v[1][1]==nodes[k]) for k,v in o.items()))
M10={"1,1":"5,4","1,2":"5,5","1,3":"6,3","1,4":"5,1","2,1":"6,4","2,2":"6,5","2,3":"5,3","2,4":"6,1","2,5":"5,2","3,1":"7,4","3,2":"7,3","3,3":"7,2","3,4":"7,1","3,5":"6,2","4,1":"2,3","4,2":"4,4","4,3":"4,3","4,4":"4,2","5,1":"1,4","5,2":"2,5","5,3":"4,1","5,4":"1,1","5,5":"1,2","6,1":"2,4","6,2":"3,5","6,3":"3,2","6,4":"2,1","6,5":"2,2","7,1":"3,4","7,2":"1,3","7,3":"3,3","7,4":"3,1"}
M={tuple(map(int,k.split(','))):tuple(map(int,v.split(','))) for k,v in M10.items()}
o=res[(0,1)]; print('map agrees (per node)',sum(M[nodes[k]]==v[0][1] for k,v in o.items()),len(o))
inv={v:k for k,v in M.items()}
o=res[(1,0)]; u=t=tin=0; cols=[]
for k,v in o.items():
    tie=abs(v[1][0]-v[0][0])<1e-9
    if tie:
        t+=1; tin+= inv[nodes[k]] in (v[0][1],v[1][1]); cols.append((nodes[k],v[0][1],v[1][1]))
    else: u+= inv[nodes[k]]==v[0][1]
print('reader1: unique agree',u,'ties',t,'tie contains',tin, sorted(set(cols)))
# affine best
best=0
for tr in (0,1):
 for sx in (1,-1):
  for ax in range(-10,11):
   for sy in (1,-1):
    for ay in range(-10,11):
      n=0
      for (x,y),p in M.items():
        a,b=(y,x) if tr else (x,y)
        n+= (sx*a+ax,sy*b+ay)==p
      best=max(best,n)
print('best affine',best)
# hop distance cpu0 -> proxies
print('cpu0 to (1,3) hops', abs(1-1)+abs(2-3), 'to (2,5)',1+3,'cpu64',cm[64],'to (5,2)')
