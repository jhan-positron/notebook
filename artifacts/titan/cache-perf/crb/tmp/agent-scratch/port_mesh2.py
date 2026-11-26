import re, json, sys
src = open('crb-memory-hierarchy.html').read().split('\n')
# ids defined before script
for i,l in enumerate(src,1):
    for m in re.finditer(r'id="(lat|db|agg|slc|dram|pair|lattab|pipes|ways|waysex|wgrid|percore|coremap|dist|mesh|mesh2)"', l):
        print('id', m.group(1), 'line', i)
txt = '\n'.join(src)
POS = json.loads(re.search(r"POS = (\[\[.*?\]\])[,;]", txt).group(1))
D = json.loads(re.search(r"const D = (\[\[0,0,0,.*?\]\]);", txt).group(1))
print('POS', len(POS), 'D', len(D), D[0], D[20])
INK='#1b1f24'; MUTED='#5b6470'; S1='#2a78d6'; GREEN='#1baf7a'
els=[]
def el(tag, a, text=None): els.append((tag, dict(a), text))
def t(x,y,s,a=None):
    d={'x':x,'y':y,'font-size':11,'fill':INK}; d.update(a or {}); el('text',d,s)
cpus={}
for p in POS:
    if p[1]==0: cpus.setdefault('%d,%d'%(p[2],p[3]),[]).append(p[0])
X0,Y0,DX,DY,CW,CH=46,42,92,66,78,58
cx=lambda x:X0+x*DX
cy=lambda y:Y0+(7-y)*DY
for x in range(9): t(cx(x)+CW/2,34,'X %d'%x,{'text-anchor':'middle','fill':MUTED})
for y in range(8): t(X0-8,cy(y)+CH/2+4,'Y %d'%y,{'text-anchor':'end','fill':MUTED})
for y in range(8):
    for x in range(9):
        if x<8: el('line',dict(x1=cx(x)+CW,y1=cy(y)+CH/2,x2=cx(x+1),y2=cy(y)+CH/2))
        if y<7: el('line',dict(x1=cx(x)+CW/2,y1=cy(y),x2=cx(x)+CW/2,y2=cy(y+1)+CH))
cells={}
for row in D:
    x,y,n,p0,ids0,p1=row[:6]
    X,Y=cx(x),cy(y); port = p1=='RN-F_F_E'; cs=cpus.get('%d,%d'%(x,y),[])
    fill='#f5f7f9'; stroke='#9aa3ad'; dash=None
    if p0=='HN-S' and len(ids0): l2='HN-S #'+' #'.join(map(str,ids0))
    elif p0=='HN-S': l2='HN-S, no node'; dash='3 2'
    elif p0=='SN-F_F': l2='SN-F (memory)'
    else: l2=(p0+(' / '+p1 if p1 else '')).replace('????','?',1)
    if port:
        stroke=S1; fill='#eef3fa' if cs else '#fff'
        l3='core port'; l4='CPUs '+', '.join(map(str,cs)) if cs else 'no CPU found'
    else: l3='no core port'; l4=''
    a=dict(x=X,y=Y,width=CW,height=CH,cell=n)
    if dash: a['stroke-dasharray']=dash
    el('rect',a)
    m={'text-anchor':'middle','font-size':9,'cellw':CW,'cellx':X}
    t(X+CW/2,Y+12,'XP %d'%n,dict(m,fill=MUTED))
    t(X+CW/2,Y+25,l2,m)
    t(X+CW/2,Y+38,l3,dict(m,**({'fill':S1,'font-weight':600} if port else {'fill':MUTED})))
    if l4: t(X+CW/2,Y+51,l4,dict(m,**({'font-weight':600} if cs else {'fill':MUTED})))
    cells[n]=dict(x=x,y=y,l2=l2,l3=l3,l4=l4,dash=dash,cs=cs,p0=p0,p1=p1,ids0=ids0)
LY=586
leg=['core port with 2 CPUs found on it: 32 crosspoints. CPU numbers are mesh 0, placed by the latency fit.',
'core port with no CPU found on it: 3 crosspoints (XP 10, 46, 52)',
'no core port: 37 crosspoints (memory ports, chip links, I/O nodes)',
'dashed border: port 0 has type HN-S and the driver lists no home node on it (XP 46, 49, 52)']
for i,g in enumerate(leg):
    y=LY+i*17; el('rect',dict(x=8,y=y-10,width=14,height=12)); t(28,y,g,{'font-size':11.5})
t(8,676,'Inside one crosspoint: XP 20 at (2,2). A port and the devices on it are separate things.',{'font-size':12.5,'font-weight':600})
el('rect',dict(x=40,y=700,width=150,height=140,box='XP'))
bx={'boxx':40,'boxw':150}
t(115,760,'XP 20',dict({'text-anchor':'middle','font-size':13,'font-weight':600},**bx))
t(115,777,'crosspoint (router)',dict({'text-anchor':'middle','fill':MUTED},**bx))
t(115,793,'4 mesh links, to',dict({'text-anchor':'middle','fill':MUTED,'font-size':10},**bx))
t(115,806,'XP 11, 19, 21, 29',dict({'text-anchor':'middle','fill':MUTED,'font-size':10},**bx))
def rowf(yc,label,typ,calDash,calText,devs,fill,stroke,notes):
    el('circle',dict(cx=190,cy=yc,r=5)); el('line',dict(x1=190,y1=yc,x2=330,y2=yc))
    t(260,yc-7,label,{'text-anchor':'middle','font-size':10.5,'font-weight':600,'boxx':195,'boxw':135})
    t(260,yc+14,typ,{'text-anchor':'middle','font-size':10,'boxx':195,'boxw':135})
    el('rect',dict(x=330,y=yc-17,width=70,height=34))
    t(365,yc+4,calText,{'text-anchor':'middle','font-size':10.5,'boxx':330,'boxw':70})
    for i,d in enumerate(devs):
        y=yc-31+i*34
        el('line',dict(x1=400,y1=yc,x2=440,y2=y+14)); el('rect',dict(x=440,y=y,width=140,height=28))
        t(510,y+18,d,{'text-anchor':'middle','font-weight':600,'boxx':440,'boxw':140})
    for i,n in enumerate(notes): t(596,yc-14+i*15,n,{})
rowf(735,'port 0: HN-S port','type HN-S',False,'CAL2',['HN-S #16','HN-S #17'],'#eef3fa',S1,
 ['2 home nodes, inside the mesh (CMN).','Each holds one slice of the mesh cache.','The map prints both ids, #16 and #17.'])
rowf(805,'port 1: core port','type RN-F_F_E',True,'CAL2 ?',['CPU 8','CPU 9'],'#eaf7f1',GREEN,
 ['2 cores, outside the mesh (Arm: RN-F).','Each has its own L1 and L2.','The map prints no id here. CPUs: latency fit.'])
t(8,866,'Arm allows 1, 2 or 4 cores on one core port (no CAL, CAL2, CAL4). CRB: 2 on each used port, by the fit and the pair test. Not read from hardware.',{'fill':MUTED})

# ---- checks
def bbox(a,s):
    fs=a['font-size']; k=0.6 if a.get('font-weight') else 0.55
    w=k*fs*len(s); anc=a.get('text-anchor','start')
    x0 = a['x'] if anc=='start' else a['x']-w/2 if anc=='middle' else a['x']-w
    return (x0,a['y']-0.8*fs,x0+w,a['y']+0.2*fs,w)
texts=[]
for tag,a,s in els:
    if tag=='text':
        b=bbox(a,s); texts.append((b,a,s))
        if b[0]<0 or b[2]>880 or b[1]<0 or b[3]>880: print('OUT OF VIEWBOX text %r x0=%.1f x1=%.1f y=%s'%(s,b[0],b[2],a['y']))
        if 'cellw' in a and (b[4]>a['cellw']): print('WIDER THAN CELL %r w=%.1f'%(s,b[4]))
        if 'cellw' in a and b[4]>a['cellw']-6: print('  tight in cell %r w=%.1f'%(s,b[4]))
        if 'boxw' in a and (b[0]<a['boxx'] or b[2]>a['boxx']+a['boxw']): print('WIDER THAN BOX %r w=%.1f box=%s'%(s,b[4],a['boxw']))
    elif tag=='rect':
        if a['x']<0 or a['y']<0 or a['x']+a['width']>880 or a['y']+a['height']>880: print('OUT rect',a)
    elif tag=='line':
        for k in ('x1','x2','y1','y2'):
            if not 0<=a[k]<=880: print('OUT line',a)
for i in range(len(texts)):
    for j in range(i+1,len(texts)):
        A=texts[i][0];B=texts[j][0]
        if A[0]<B[2] and B[0]<A[2] and A[1]<B[3] and B[1]<A[3]: print('OVERLAP %r <-> %r'%(texts[i][2],texts[j][2]), A[:4],B[:4])
# text vs rect edges (text crossing a rect border it is not inside)
rects=[a for tag,a,s in els if tag=='rect']
for b,a,s in texts:
    for r in rects:
        rx0,ry0,rx1,ry1=r['x'],r['y'],r['x']+r['width'],r['y']+r['height']
        inter = b[0]<rx1 and rx0<b[2] and b[1]<ry1 and ry0<b[3]
        inside = b[0]>=rx0 and b[2]<=rx1 and b[1]>=ry0 and b[3]<=ry1
        if inter and not inside: print('TEXT CROSSES RECT EDGE %r bbox=%s rect=%s'%(s,[round(v,1) for v in b[:4]],(rx0,ry0,rx1,ry1)))
# long widths
for b,a,s in texts:
    if b[4]>400: print('long text w=%.1f end=%.1f : %s'%(b[4],b[2],s[:50]))
for b,a,s in texts:
    if a['x']==596: print('note end=%.1f : %s'%(b[2],s))
c=cells
print('core port',sum(v['l3']=='core port' for v in c.values()),
 'with CPUs',sum(bool(v['cs']) and v['l3']=='core port' for v in c.values()),
 'no CPU found',sorted(n for n,v in c.items() if v['l4']=='no CPU found'),
 'no core port',sum(v['l3']=='no core port' for v in c.values()),
 'dashed',sorted(n for n,v in c.items() if v['dash']))
print('cpus on non-port cells', [(n,v['cs']) for n,v in c.items() if v['cs'] and v['l3']!='core port'])
print('cpu count != 2', [(n,v['cs']) for n,v in c.items() if v['cs'] and len(v['cs'])!=2])
J=json.load(open('results/sudo-20261102T054936Z/core-positions.json'))['pos']
ref={}
for k,v in J.items():
    if v['mesh']==0: ref.setdefault((v['x'],v['y']),[]).append(int(k))
got={(v['x'],v['y']):v['cs'] for v in c.values() if v['cs']}
print('json mesh0 cpus',sum(len(v) for v in ref.values()),'cells',len(ref),'match', {k:sorted(v) for k,v in ref.items()}=={k:sorted(v) for k,v in got.items()}, 'order same', all(got[k]==sorted(got[k]) for k in got))
print('json mesh1 cpus', sorted(int(k) for k,v in J.items() if v['mesh']==1)[:3], len([1 for v in J.values() if v['mesh']==1]), 'total', len(J))
m1ok=all(J[str(n+64)]['mesh']==1 and (J[str(n+64)]['x'],J[str(n+64)]['y'])==(J[str(n)]['x'],J[str(n)]['y']) for n in range(0,56) if str(n+64) in J); print('mesh1 n+64 rule', m1ok, [n for n in range(64,128) if str(n) not in J])
print('XP20',c[20]); 
xy={(v['x'],v['y']):n for n,v in c.items()}
print('neigh',sorted(xy[p] for p in [(1,2),(3,2),(2,1),(2,3)]))
print('n == y*9+x', all(n==v['y']*9+v['x'] for n,v in c.items()))
print('l2 set', sorted(set(v['l2'] for v in c.values() if not v['l2'].startswith('HN-S #'))))
print('non RN p1 on HN-S cells', [(n,v['p1']) for n,v in c.items() if v['p0']=='HN-S' and v['p1']!='RN-F_F_E'])
print('RN on non-HN-S', [(n,v['p0']) for n,v in c.items() if v['p1']=='RN-F_F_E' and v['p0']!='HN-S'])
print('max text widths in cell', sorted(((round(b[4],1),s) for b,a,s in texts if 'cellw' in a), reverse=True)[:6])
print('nelements', len(els))
