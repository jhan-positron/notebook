import re,json,sys
def parse(lines):
    cells={}; hdr=None; y=None; port=None; bad=[]; ports=set(); drows={}
    for ln in lines:
        ln=ln.rstrip('\n')
        if not ln.strip(): continue
        if re.match(r'\s+X\s+0',ln): hdr=ln.split()[1:]; continue
        if ln.startswith('Y P D+') or ln.startswith('-----+'): continue
        pre,rest=ln[:5],ln[5:]
        f=[c.strip() for c in rest.strip().strip('|').split('|')]
        if len(f)!=9: bad.append(ln); continue
        if re.match(r'\d    ',pre):
            y=int(pre[0])
            for x,c in enumerate(f):
                cells[(x,y)]={'xp':int(c.replace('XP #','')),'p':{0:['',[]],1:['',[]]}}
        elif pre.strip()=='' :
            continue  # DTC / dots
        elif re.match(r'  \d  ',pre):
            port=int(pre[2]); ports.add(port)
            for x,c in enumerate(f): cells[(x,y)]['p'][port][0]=c
        elif re.match(r'    \d',pre):
            d=int(pre[4]); drows.setdefault(port,set()).add(d)
            for x,c in enumerate(f):
                if c: cells[(x,y)]['p'][port][1].append(int(c.lstrip('#')))
        else: bad.append(ln)
    return cells,hdr,ports,drows,bad
L=open('results/cmn-map.txt').read().split('\n')
i1=[i for i,l in enumerate(L) if 'arm-cmn/map' in l]
print('cmd lines',[(i+1,L[i]) for i in i1])
s0=L[i1[0]+1:i1[1]]; s1=L[i1[1]+1:]
m0=parse(s0); m1=parse(s1)
r0=parse(open('results/map').read().split('\n')); r1=parse(open('results/map_1').read().split('\n'))
for n,m in [('s0',m0),('s1',m1),('r0',r0),('r1',r1)]:
    c=m[0]; print(n,len(c),'cols',len({k[0] for k in c}),'rows',len({k[1] for k in c}),'ports',m[2],'drows',m[3],'bad',len(m[4]),m[1])
print('cell-identical s0==s1',m0[0]==m1[0],'s0==r0',m0[0]==r0[0],'s1==r1',m1[0]==r1[0])
print('nonblank lines equal', [l for l in s0 if l.strip()]==[l for l in s1 if l.strip()])
print('rstrip lines equal to raw', [l.rstrip() for l in s0 if l.strip()]==[l.rstrip() for l in open('results/map').read().split('\n') if l.strip()])
c=m0[0]
print('xp=9y+x',all(v['xp']==9*y+x for (x,y),v in c.items()))
h=open('crb-memory-hierarchy.html').read().split('\n')
ln=[i for i,l in enumerate(h) if l.strip().startswith('const D = [[')]
print('D line',[i+1 for i in ln])
D=json.loads(re.search(r'const D = (\[\[.*\]\]);',h[ln[0]]).group(1))
print('D n',len(D),len({(d[0],d[1]) for d in D}))
mm=[]
for x,y,n,p0,i0,p1,i1_ in D:
    v=c[(x,y)]
    if (n,p0,i0,p1,i1_)!=(v['xp'],v['p'][0][0],v['p'][0][1],v['p'][1][0],v['p'][1][1]): mm.append((x,y))
print('mismatch',mm)
hs2=[k for k,v in c.items() if v['p'][0][0]=='HN-S' and len(v['p'][0][1])==2]
hs0=sorted((v['xp'],k) for k,v in c.items() if v['p'][0][0]=='HN-S' and not v['p'][0][1])
hsall=[k for k,v in c.items() if v['p'][0][0]=='HN-S']
rn1=sorted(k for k,v in c.items() if v['p'][1][0].startswith('RN-F'))
rn0=[k for k,v in c.items() if v['p'][0][0].startswith('RN-F')]
print('hs2',len(hs2),'hs0',hs0,'hsall',len(hsall),'rn1',len(rn1),'rn0',rn0,'rect',set(rn1)=={(x,y) for x in range(1,8) for y in range(1,6)},'rn==hs',set(rn1)==set(hsall))
print('rn with ids',[k for k in rn1 if c[k]['p'][1][1]])
ids=sorted(i for k in hs2 for i in c[k]['p'][0][1])
print(len(ids),len(set(ids)),ids[0],ids[-1],sorted(set(range(ids[0],ids[-1]+1))-set(ids)))
print('rule',all(c[(x,y)]['p'][0][1]==[2*(7*(y-1)+x-1),2*(7*(y-1)+x-1)+1] for x,y in hs2))
from collections import Counter
print(Counter(v['p'][0][0] for v in c.values())); print(Counter(v['p'][1][0] for v in c.values()))
print('raw type strings incl. any other text', sorted({v['p'][p][0] for v in c.values() for p in (0,1)}))
out=[[v['xp'],x,y,v['p'][0][0],v['p'][0][1],v['p'][1][0],v['p'][1][1]] for (x,y),v in sorted(c.items(),key=lambda t:t[1]['xp'])]
claimed=json.loads(open(sys.argv[1]).read()) if len(sys.argv)>1 else None
print(json.dumps(out,separators=(',',':')))
