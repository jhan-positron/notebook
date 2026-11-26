#!/usr/bin/env python3
"""Recompute every number of the cross-chiplet paragraph from the raw CSVs. Read-only on inputs."""
import re, json, glob, os
R='/home/jhan/workspace/titan/cache-perf/crb/results/'
cross=R+'followup2-20261031T073513Z/cross.csv'
blocks=[]; cpu=None
for ln,l in enumerate(open(cross),1):
    l=l.strip()
    m=re.match(r'# latency pointer chase.*cpu=(\d+).*fresh=(\d+)',l)
    if m: cpu=int(m.group(1)); continue
    m=re.match(r'# size_bytes=(\d+) AnonHugePages_kB=(\d+) build_cpu=(-?\d+)',l)
    if m: cur=dict(walk=cpu,build=int(m.group(3)),size=int(m.group(1))>>20,thp_kb=int(m.group(2)),line=ln); blocks.append(cur); continue
    m=re.match(r'(\d+),(fresh\d|best),(\d+),([\d.]+)',l)
    if m: cur[m.group(2)]=float(m.group(4)); cur['loads']=int(m.group(3))
chip=lambda c:0 if c<64 else 1
print('cross.csv blocks (line = row number of the "# size_bytes" comment; fresh1/fresh2 are the next 2 rows)')
for b in blocks:
    b['kind']='same' if chip(b['build'])==chip(b['walk']) else 'cross'
    print(f"  line {b['line']:2d} build {b['build']:3d} -> walk {b['walk']:3d} {b['kind']:5s} {b['size']:2d} MiB thp_kB={b['thp_kb']} loads={b['loads']} first={b['fresh1']} second={b['fresh2']}")
pairs=[]
for b in blocks:
    p=(b['build'],b['walk'],b['kind'])
    if p not in pairs: pairs.append(p)
print('pairs in file order:',pairs)
rng=lambda xs:(min(xs),max(xs))
for sz in (16,32,64):
    c=[b for b in blocks if b['size']==sz and b['kind']=='cross']; s=[b for b in blocks if b['size']==sz and b['kind']=='same']
    print(f"{sz} MiB: cross first {rng([b['fresh1'] for b in c])} cross second {rng([b['fresh2'] for b in c])} "
          f"same first {rng([b['fresh1'] for b in s])} same second {rng([b['fresh2'] for b in s])} same all {rng([b[k] for b in s for k in ('fresh1','fresh2')])}")
c16=[b for b in blocks if b['size']==16 and b['kind']=='cross']; s16=[b for b in blocks if b['size']==16 and b['kind']=='same']
sall=[b[k] for b in s16 for k in ('fresh1','fresh2')]
f=[b['fresh1'] for b in c16]
print('16 MiB first-walk extra: min(first)-max(same) = %.3f, max(first)-min(same) = %.3f'%(min(f)-max(sall),max(f)-min(sall)))
print('   using rounded ends 85.0-29.3=%.1f, 88.5-29.0=%.1f ; 85.0-29.0=%.1f ; 88.5-29.3=%.1f'%(85.0-29.3,88.5-29.0,85.0-29.0,88.5-29.3))
for b in c16:
    w=b['walk']; own=[x for x in s16 if x['walk']==w]
    print(f"   {b['build']}->{b['walk']}: first-second = {b['fresh1']-b['fresh2']:.3f}", 'first minus same-core control (cross.csv) = '+', '.join('%.3f'%(b['fresh1']-o[k]) for o in own for k in ('fresh1','fresh2')) if own else '(no same-core control for walker in cross.csv)')
# own-mesh figures from percore sweep
own={}
for fn in ('percore-latency-1.csv','percore-latency-2.csv'):
    cpu=None;fresh=None
    for ln,l in enumerate(open(R+'followup3-20261102T031936Z/'+fn),1):
        l=l.strip()
        m=re.match(r'-- cpu (\d+)',l)
        if m: cpu=int(m.group(1)); continue
        m=re.match(r'# latency pointer chase.*fresh=(\d+)',l)
        if m: fresh=int(m.group(1)); continue
        m=re.match(r'16777216,(fresh1|fresh2|best),\d+,([\d.]+)',l)
        if m and fresh==3: own.setdefault((fn,cpu),{})[m.group(1)]=(float(m.group(2)),ln)
print('own-mesh 16 MiB fresh figures, percore sweep (value, row):')
for fn in ('percore-latency-1.csv','percore-latency-2.csv'):
    for c in (3,64,67,119): print('  ',fn,c,own[(fn,c)])
    print('   range of best over 3,64,67,119:',rng([own[(fn,c)]['best'][0] for c in (3,64,67,119)]),' range of all fresh rows:',rng([own[(fn,c)][k][0] for c in (3,64,67,119) for k in ('fresh1','fresh2')]))
print('remainder = cross second walk (cross.csv, 16 MiB) minus walker own-mesh figure:')
for fn in ('percore-latency-1.csv','percore-latency-2.csv'):
    rs=[]
    for b in c16:
        o=own[(fn,b['walk'])]; r=b['fresh2']-o['best'][0]; rs.append(r)
        print(f"   {fn} {b['build']}->{b['walk']}: {b['fresh2']} - best {o['best'][0]} = {r:.3f} ; vs fresh1 {b['fresh2']-o['fresh1'][0]:.3f} ; vs fresh2 {b['fresh2']-o['fresh2'][0]:.3f}")
    print('   range vs best: %.3f to %.3f'%rng(rs))
print('remainder vs cross.csv same-core control second walk (only walkers 3 and 67 have one):')
for b in c16:
    o=[x for x in s16 if x['walk']==b['walk']]
    if o: print(f"   {b['build']}->{b['walk']}: {b['fresh2']-o[0]['fresh2']:.3f} (vs control first {b['fresh2']-o[0]['fresh1']:.3f})")
for sz in (32,64):
    for b in blocks:
        if b['size']==sz and b['kind']=='cross':
            o=[x for x in blocks if x['size']==sz and x['kind']=='same']
            print(f"{sz} MiB {b['build']}->{b['walk']}: first {b['fresh1']} second {b['fresh2']} first-second {b['fresh1']-b['fresh2']:.3f}")
print('L2 share: 2 MiB L2 / chain size:',{sz:'%d/%d = 1/%d = %.4f'%(2,sz,sz//2,2/sz) for sz in (16,32,64)})
# DRAM label
d=json.load(open('/home/jhan/workspace/titan/cache-perf/crb/data-all.json'))
for k in ('latency_fresh','latency_repeated'):
    for s in ('1073741824','2147483648'):
        v=d[k][s]; print(k,int(s)>>30,'GiB',v,'ns x 2.8 GHz =',round(v*2.8,2),'cycles')
print('148 x 2.8 =',148*2.8,'; 30 x 2.8 =',30*2.8,'; 30.18 x 2.8 =',round(30.18*2.8,2),'; 30.4 x 2.8 =',round(30.4*2.8,2))
