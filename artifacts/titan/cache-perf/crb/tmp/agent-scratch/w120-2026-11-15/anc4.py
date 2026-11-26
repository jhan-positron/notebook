#!/usr/bin/env python3
"""anc4.py FOLDER: share of DAT and RSP flits delivered to core ports that carry each CBusy level (0..3), per mesh (sum of 4 core ports)."""
import sys,glob,os,re,collections
fold=sys.argv[1]
groups=[re.match(r'launch (\S+)',l).group(1) for l in open(fold+'/launches.txt') if l.startswith('launch')]
def rows(f):
    for l in open(f):
        if l.startswith('#') or not l.strip(): continue
        a=l.strip().rsplit(',',4); h=a[0].split(',',2)
        yield [h[0],h[1],h[2],a[1],a[2]]
for g in groups:
    rate={}
    for f in glob.glob(f'{fold}/{g}.m?.csv'):
        m=int(os.path.basename(f).split('.')[-2][1]); r=[]
        for l in open(f):
            p=l.split(',')
            if p[0]=='T': r.append(float(p[6])/float(p[7])/1e9)
        rate[m]=sum(r)/len(r)
    acc=collections.defaultdict(float); mux=0; ns=0
    for f in sorted(glob.glob(f'{fold}/{g}.*.perf')):
        for p in rows(f):
            m=re.match(r'arm_cmn_(\d)/watchpoint_down.*wp_chn_sel=(\d).*wp_val=(\w+),wp_mask=(\w+)',p[2])
            if not m: continue
            if p[0].startswith('<'): ns+=1; continue
            mesh=int(m.group(1)); ch='DAT' if m.group(2)=='3' else 'RSP'; val=int(m.group(3),16); mask=int(m.group(4),16)
            lvl='all' if mask==0xffffffffffffffff else str((val>>(44 if ch=='DAT' else 28))&3)
            acc[(mesh,ch,lvl,os.path.basename(f).split('.')[-2])]+=float(p[0])/(float(p[3])/1e9)/1e6
            if float(p[4])<99.9: mux+=1
    out=f'{g:26}'
    for mesh in (0,1):
        out+=f' | m{mesh} {rate.get(mesh,0):4.2f}GB/s/thr'
        for ch in ('DAT','RSP'):
            lv={l:sum(v for k,v in acc.items() if k[0]==mesh and k[1]==ch and k[2]==l and not k[3].endswith('A3')) for l in '0123'}
            tot=sum(lv.values()); al=sum(v for k,v in acc.items() if k[0]==mesh and k[1]==ch and k[2]=='all')
            out+=f' {ch} {tot:6.1f}M/s(all {al:6.1f}) %c0-3:'+' '.join(f'{100*lv[l]/tot:5.1f}' if tot else '  -  ' for l in '0123')
    print(out+(f' MUX{mux}' if mux else '')+(f' NS{ns}' if ns else ''))
