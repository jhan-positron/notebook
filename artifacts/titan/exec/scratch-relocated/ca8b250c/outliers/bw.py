import glob,os,re
R='/home/jhan/workspace/titan/cache-perf/asimov/results'
def bw(path):
    hdr=open(path).readline(); passes=int(re.search(r'passes=(\d+)',hdr).group(1)); asm=int(re.search(r'asm_passes=(\d)',hdr).group(1))
    rows=[]
    for line in open(path):
        if line.startswith('#') or line.startswith('mem,'): continue
        f=line.rstrip('\n').split(',')
        if f[4]=='best': continue
        tb=float(f[5]); agg=float(f[7]); span=float(f[10])
        rows.append(dict(k=f[1],bpt=int(f[3]),rep=int(f[4]),brk=tb/agg,span=span*1e9,passes=passes,asm=asm))
    return rows
for boot,run in (('bootF1','011'),('bootF2','012')):
    print('==',boot)
    for fn in sorted(glob.glob(f'{R}/membench-jibin-{run}/results/{boot}/cme-bandwidth-*asmpasses.csv')):
        rows=bw(fn); print(' ',os.path.basename(fn))
        first={};later={}
        for r in rows:
            out=r['brk']-r['span']; key=('read' if 'read' in r['k'] else 'write' if 'write' in r['k'] else r['k'])
            d=first if r['rep']==0 else later
            d.setdefault(key,[]).append(out)
            print(f"   {r['k']} {r['bpt']//1024}KiB rep{r['rep']} bracket {r['brk']:.1f} span {r['span']:.1f} outside {out:.1f}")
        for k in first: print(f"   {k}: first rep {min(first[k]):.1f}-{max(first[k]):.1f}; later reps {min(later[k]):.1f}-{max(later[k]):.1f}")
    looped=[]
    for base in ('cme-bandwidth-call-cost.csv','cme-bandwidth-l1-passes.csv','cme-bandwidth-l1-nofold.csv','cme-bandwidth-l1-dsb.csv','cme-bandwidth-dram-1core.csv'):
        fn=f'{R}/membench-jibin-{run}/results/{boot}/{base}'
        for r in bw(fn):
            if r['bpt']<=262144: looped.append((r['brk']-r['span'])/r['passes'])
    print(f'  looped 1-256 KiB outside per call over {len(looped)} reps: {min(looped):.1f}-{max(looped):.1f}')
