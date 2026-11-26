import re,json,collections
html=open('crb-memory-hierarchy.html').read()
D=json.loads(re.search(r'const D = (\[\[.*?\]\]);',html).group(1))
m=re.search(r'const POS = (\[\[.*?\]\]);',html)
POS=json.loads(m.group(1)) if m else None
def parse(path):
    lines=open(path).read().split('\n'); out={}; y=None
    for i,l in enumerate(lines):
        mm=re.match(r'^(\d)\s+\|(.*XP #.*)\|\s*$',l)
        if mm:
            y=int(mm.group(1))
            for x,c in enumerate(mm.group(2).split('|')): out[(x,y,'xp')]=int(c.strip()[4:])
            continue
        mm=re.match(r'^  (\d)  \|(.*)\|\s*$',l)
        if mm and y is not None:
            port=int(mm.group(1)); cells=[c.strip() for c in mm.group(2).split('|')]
            d0=[c.strip() for c in lines[i+1].split('|')[1:-1]]; d1=[c.strip() for c in lines[i+2].split('|')[1:-1]]
            for x,c in enumerate(cells):
                out[(x,y,port)]=(c,[int(v[1:]) for v in (d0[x],d1[x]) if v])
    return out
p=parse('results/map')
print('max port idx',max(k[2] for k in p if k[2]!='xp'), 'port lines', collections.Counter(k[2] for k in p if k[2]!='xp'))
diff=0
for x,y,n,p0,i0,p1,i1 in D:
    if p[(x,y,'xp')]!=n or p[(x,y,0)]!=(p0,i0) or p[(x,y,1)]!=(p1,i1): diff+=1; print('DIFF',x,y,n,p0,i0,p1,i1,p[(x,y,0)],p[(x,y,1)])
print('cells',len(D),'diff',diff)
rn=[(x,y,n) for x,y,n,p0,i0,p1,i1 in D if p1=='RN-F_F_E']
print('RNF',len(rn),sorted(set(a for a,b,c in rn)),sorted(set(b for a,b,c in rn)), 'p0 RNF',[d for d in D if d[3].startswith('RN-F')])
hs=[d for d in D if d[3]=='HN-S']; print('HN-S ports',len(hs),'2ids',sum(len(d[4])==2 for d in hs),'none',[d[2] for d in hs if not d[4]])
print('types of non-core XPs',collections.Counter((d[3],d[5]) for d in D if d[5]!='RN-F_F_E'))
J=json.load(open('results/sudo-20261102T054936Z/core-positions.json'))
print(J['method']); print(J['candidates'] if not isinstance(J['candidates'],list) or len(J['candidates'])<10 else len(J['candidates'])); print(list(J['pos'].items())[:3]); print(str(J['far'])[:300])
pos=J['pos']
print('ncpu',len(pos),'min',min(map(int,pos)),'max',max(map(int,pos)))
bym=collections.defaultdict(lambda:collections.defaultdict(list))
for c,v in pos.items(): bym[v['mesh']][(v['x'],v['y'])].append(int(c))
for mesh in bym:
    print('mesh',mesh,'ports',len(bym[mesh]),'sizes',collections.Counter(len(v) for v in bym[mesh].values()),'cpus',min(min(v) for v in bym[mesh].values()),max(max(v) for v in bym[mesh].values()))
rnset={(a,b) for a,b,c in rn}
xp={(d[0],d[1]):d[2] for d in D}
print('mesh0 empty',sorted(xp[k] for k in rnset-set(bym[0])), 'mesh1 empty',sorted(xp[k] for k in rnset-set(bym[1])))
bad=[c for c,v in pos.items() if int(c)>=64 and (str(int(c)-64) not in pos or (pos[str(int(c)-64)]['x'],pos[str(int(c)-64)]['y'])!=(v['x'],v['y']) or v['mesh']!=1)]
print('n+64 violations',bad)
print('mesh0 cpus not 0..63',[c for c,v in pos.items() if v['mesh']==0 and int(c)>=64],'mesh1 <64',[c for c,v in pos.items() if v['mesh']==1 and int(c)<64])
print('pairs not (2k,2k+1)',[(k,v) for mesh in bym for k,v in bym[mesh].items() if len(v)!=2 or sorted(v)[0]%2 or sorted(v)[1]!=sorted(v)[0]+1])
print('XP20 cpus',bym[0].get((2,2)))
if POS:
    print('POS n',len(POS),POS[:2]); d=[q for q in POS if (pos[str(q[0])]['mesh'],pos[str(q[0])]['x'],pos[str(q[0])]['y'])!=tuple(q[1:4])]; print('POS vs json diff',d)
