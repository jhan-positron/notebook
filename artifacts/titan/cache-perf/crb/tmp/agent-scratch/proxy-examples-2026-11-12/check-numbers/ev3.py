import re
B='/home/jhan/workspace/titan/cache-perf/crb/results/'
blk={};idle={};cur=None
for L in open(B+'sudo-20261102T054936Z/writebw.csv'):
    L=L.strip()
    if L.startswith('-- background'): cur=('idle',);continue
    m=re.match(r'-- (\S+) (short|long) events (\S+) args (.*)',L)
    if m: cur=(m.group(1),m.group(2),m.group(3)); blk[cur]={'args':m.group(4),'ev':{}}; continue
    p=L.split(',')
    if cur==('idle',) and len(p)>=5 and '/' in p[2]: idle[p[2]]=int(p[0])/(int(p[3])/1e9)
    elif cur and cur!=('idle',):
        if p[0]=='asmread' and len(p)>4 and p[3]=='0': blk[cur]['bytes']=int(p[4])
        elif len(p)>=5 and '/' in p[2]: blk[cur]['ev'][p[2]]=(int(p[0]),int(p[3])/1e9,p[4])
for k in sorted({(a,c) for a,b,c in blk if a=='asmread-8M-1'}):
    s,l=blk[(k[0],'short',k[1])],blk[(k[0],'long',k[1])]; dl=(l['bytes']-s['bytes'])/64
    for ev in l['ev']:
        a,b=l['ev'][ev],s['ev'][ev]
        print('%-44s per line %.4f (raw %.4f, bg %.4f, counted %s/%s %%) lines %.0f args %s'%(ev,(a[0]-b[0])/dl-idle[ev]*(a[1]-b[1])/dl,(a[0]-b[0])/dl,idle[ev]*(a[1]-b[1])/dl,b[2],a[2],dl,l['args']))
