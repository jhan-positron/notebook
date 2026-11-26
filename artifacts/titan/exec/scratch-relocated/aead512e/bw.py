import glob,os,re,sys
R='/home/jhan/workspace/titan/cache-perf/asimov/results'
rows=[]
for f in sorted(glob.glob(R+'/membench-jibin-0*/results/*/*bandwidth*.csv')):
    hdr={}
    for ln,line in enumerate(open(f),1):
        line=line.rstrip('\n')
        if line.startswith('# bandwidth:'):
            hdr=dict(re.findall(r'(\w+)=(\S+)',line))
        if line.startswith('#') or line.startswith('mem,'): continue
        p=line.split(',')
        if len(p)<8: continue
        if p[4]!='best': continue
        rows.append(dict(file=f.replace(R+'/',''),ln=ln,mem=p[0],k=p[1],t=int(p[2]),b=int(p[3]),agg=float(p[7]),hdr=hdr,raw=line))
for r in rows:
    if r['mem']!='dram': continue
    h=r['hdr']
    print(f"{r['file']}:{r['ln']} | {r['raw']} | tot={r['t']*r['b']/1048576:g}MiB passes={h.get('passes')} fb={h.get('flush_before')} fa={h.get('flush_after')} cme={h.get('cme')} asmp={h.get('asm_passes')}")
print("=====LARGE")
big=[r for r in rows if r['mem']=='dram' and r['b']>=8*1048576]
for r in big:
    print(f"{r['file']}:{r['ln']} | {r['raw']} | per-thread={r['b']/1048576:g}MiB total={r['t']*r['b']/1048576:g}MiB passes={r['hdr'].get('passes')}")
print("=====MAX by kernel (per-thread>=8MiB)")
for k in sorted(set(r['k'] for r in big)):
    m=max((r for r in big if r['k']==k),key=lambda r:r['agg'])
    print(k,m['agg'],m['file'],m['ln'],m['raw'])
print("=====over 38.4 with per-thread >= 8MiB:",sum(r['agg']>38.4 for r in big),"of",len(big))
print("=====mid: per-thread 1-8MiB")
for r in rows:
    if r['mem']=='dram' and 1048576<=r['b']<8*1048576: print(f"{r['file']}:{r['ln']} | {r['raw']} | total={r['t']*r['b']/1048576:g}MiB passes={r['hdr'].get('passes')} fb={r['hdr'].get('flush_before')}")
