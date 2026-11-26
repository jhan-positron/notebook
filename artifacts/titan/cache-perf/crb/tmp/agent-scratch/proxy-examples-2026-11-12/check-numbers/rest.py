import csv, json, re, statistics as st
B='/home/jhan/workspace/titan/cache-perf/crb/results/'
# --- fit digits
J=json.load(open('../proxyfit/proxy-positions.json'))
for kind in ('local','remote'):
    r=[s for s in J['per_node'] if s['reader_mesh']==0 and s['kind']==kind]
    print(kind,'rms med',st.median(s['rms'] for s in r),'worst',max(s['rms'] for s in r),'slope med',st.median(s['slope'] for s in r),'intercept med',st.median(s['intercept'] for s in r))
# --- fig.js map against proxy-positions.json per_xp
js=open('../worker/fig.js').read(); M10=json.loads(re.search(r'M10 = (\{[^}]*\})',js).group(1))
ref={'%d,%d'%tuple(s['home_xp']):'%d,%d'%tuple(s['best']) for s in J['per_xp'] if s['reader_mesh']==0 and s['kind']=='remote'}
print('fig.js M10 equals per_xp reader-0 remote map:',M10==ref,len(M10))
# --- cross.csv
blocks=[];cpu=None
for L in open(B+'followup2-20261031T073513Z/cross.csv'):
    m=re.match(r'# latency pointer chase.*cpu=(\d+)',L)
    if m: cpu=int(m.group(1)); continue
    m=re.match(r'# size_bytes=(\d+).*build_cpu=(-?\d+)',L)
    if m: cur=dict(size=int(m.group(1))>>20,b=int(m.group(2)),w=cpu); blocks.append(cur); continue
    p=L.strip().split(',')
    if len(p)==4 and p[1].startswith('fresh'): cur[p[1]]=float(p[3])
print('blocks',len(blocks),'pairs',sorted({(b['b'],b['w']) for b in blocks}))
for sz in (16,32,64):
    same=[v for b in blocks if b['size']==sz and (b['b']<64)==(b['w']<64) for v in (b['fresh1'],b['fresh2'])]
    f1=[b['fresh1'] for b in blocks if b['size']==sz and (b['b']<64)!=(b['w']<64)]
    f2=[b['fresh2'] for b in blocks if b['size']==sz and (b['b']<64)!=(b['w']<64)]
    print(sz,'MiB same %.3f..%.3f | first %.3f..%.3f mean %.2f| second %.3f..%.3f mean %.2f'%(min(same),max(same),min(f1),max(f1),sum(f1)/len(f1),min(f2),max(f2),sum(f2)/len(f2)), ' first-same: %.2f..%.2f'%(min(f1)-max(same),max(f1)-min(same)))
ctl={b['b']:(b['fresh1'],b['fresh2']) for b in blocks if b['size']==16 and b['b']==b['w']}
for b in blocks:
    if b['size']==16 and b['b']!=b['w']:
        print('  16 MiB %d->%d first %.3f second %.3f'%(b['b'],b['w'],b['fresh1'],b['fresh2']),' first minus control of the builder chiplet (cpu 3 / 67 rows):',[round(b['fresh1']-v,2) for k in ctl if (k<64)==(b['b']<64) for v in ctl[k]],' vs walker chiplet control:',[round(b['fresh1']-v,2) for k in ctl if (k<64)==(b['w']<64) for v in ctl[k]])
# --- percore
own={};cpu=None;sz=None
for f in ('followup3-20261102T031936Z/percore-latency-1.csv',):
    for L in open(B+f):
        m=re.match(r'-- cpu (\d+)',L)
        if m: cpu=int(m.group(1)); continue
        m=re.match(r'# latency pointer chase.*(reps=\d+ fresh=\d+)',L)
        if m: mode=m.group(1); continue
        m=re.match(r'# size_bytes=(\d+)',L)
        if m: sz=int(m.group(1))>>20; continue
        p=L.strip().split(',')
        if len(p)==4 and p[0].isdigit() and sz==16 and cpu in (3,64,67,119): own.setdefault(cpu,[]).append((mode,p[1],float(p[3])))
for c in own: print('cpu',c,own[c])
fr={c:[v for m,r,v in own[c] if r.startswith('fresh')] for c in own}; bst={c:min(fr[c]) for c in own}
print('own 16 MiB fresh range all rows %.3f..%.3f ; best %.3f..%.3f'%(min(min(v) for v in fr.values()),max(max(v) for v in fr.values()),min(bst.values()),max(bst.values())))
d=[]
for b in blocks:
    if b['size']==16 and b['b']!=b['w']:
        lo=b['fresh2']-max(fr[b['w']]); hi=b['fresh2']-min(fr[b['w']]); d+= [lo,hi]; print('  %d->%d second %.3f minus walker own: %.3f..%.3f'%(b['b'],b['w'],b['fresh2'],lo,hi))
print('remainder range, any fresh row %.3f..%.3f'%(min(d),max(d)))
# --- evidence 3
blk={};idle={};cur=None
for L in open(B+'sudo-20261102T054936Z/writebw.csv'):
    L=L.strip()
    if L.startswith('-- background'): cur=('idle',);continue
    m=re.match(r'-- (\S+) (short|long) events (\S+) args (.*)',L)
    if m: cur=(m.group(1),m.group(2),m.group(3)); blk[cur]={'args':m.group(4)}; continue
    p=L.split(',')
    if cur==('idle',) and len(p)>=5 and '/' in p[2]: idle[p[2]]=int(p[0])/(int(p[3])/1e9)
    elif cur and cur!=('idle',) and cur[0]=='asmread-8M-1':
        if p[0]=='asmread' and p[3]=='0': blk[cur]['bytes']=int(p[4])
        elif len(p)>=5 and '/' in p[2]: blk[cur][p[2]]=(int(p[0]),int(p[3])/1e9,p[4])
for k in sorted({(a,c) for a,b,c in blk}):
    s,l=blk[(k[0],'short',k[1])],blk[(k[0],'long',k[1])]; dl=(l['bytes']-s['bytes'])/64
    for ev in l:
        if 'slc_sf_cache_access' in ev or 'cache_miss' in ev or 'reqs_recvd_read' in ev:
            print(ev,'per line %.4f'%((l[ev][0]-s[ev][0])/dl-idle[ev]*(l[ev][1]-s[ev][1])/dl),'(raw %.4f, pct %s/%s) args %s'%((l[ev][0]-s[ev][0])/dl,s[ev][2],l[ev][2],l['args']))
