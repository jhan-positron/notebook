import csv,json,itertools
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
homes=[(int(r['mesh']),int(r['node_id_hex'],16)) for r in csv.DictReader(open(R+'full/homes.csv'))]
ch=list(csv.DictReader(open(R+'full/chunks.csv')))
nodes={(int(r['mesh']),int(r['node_id_hex'],16)):(int(r['x']),int(r['y'])) for r in csv.DictReader(open(R+'full/nodes.csv'))}
T=json.load(open('hash/table.json')); mk=T['full_masks_particular']
masks={k:sum(1<<b for b in v) for k,v in mk.items()}
print({k:len(v) for k,v in mk.items()}, 'distinct sets',len(set(masks.values())))
par=lambda v:bin(v).count('1')&1
tab={};bad=0
for i,h in enumerate(homes):
    pa=(int(ch[i//32768]['pfn_hex'],16)<<12)+(i%32768)*64
    key=tuple(par(pa&masks['h%d'%j]) for j in range(7))
    if tab.setdefault(key,h)!=h: bad+=1
print('keys',len(tab),'conflicts',bad,'distinct homes',len(set(tab.values())))
print('h6==mesh',all(k[6]==v[0] for k,v in tab.items()))
M10={"1,1":"5,4","1,2":"5,5","1,3":"6,3","1,4":"5,1","2,1":"6,4","2,2":"6,5","2,3":"5,3","2,4":"6,1","2,5":"5,2","3,1":"7,4","3,2":"7,3","3,3":"7,2","3,4":"7,1","3,5":"6,2","4,1":"2,3","4,2":"4,4","4,3":"4,3","4,4":"4,2","5,1":"1,4","5,2":"2,5","5,3":"4,1","5,4":"1,1","5,5":"1,2","6,1":"2,4","6,2":"3,5","6,3":"3,2","6,4":"2,1","6,5":"2,2","7,1":"3,4","7,2":"1,3","7,3":"3,3","7,4":"3,1"}
M={tuple(map(int,k.split(','))):tuple(map(int,v.split(','))) for k,v in M10.items()}
ok=sum(M[nodes[tab[k[:6]+(1,)]]]==nodes[tab[k[:6]+(0,)]] for k in tab if k[6]==0)
print('same six -> proxy pair',ok,'of 64')
# x,y bits affine in 6 bits?
for m in (0,1):
  for name,f in [('x',lambda n:n>>7),('y',lambda n:(n>>3)&15)]:
    for bit in range(3):
      found=False
      for coef in range(128):
        if all((par(sum(k[j]<<j for j in range(6))&(coef&63))^(coef>>6))==((f(v[1])>>bit)&1) for k,v in tab.items() if k[6]==m): found=True
      print(m,name,bit,'affine',found)
