import glob,os,csv
R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
BO={'F1':R+'membench-jibin-011/results/bootF1/','F2':R+'membench-jibin-012/results/bootF2/'}
def parse(p):
    rows=[]
    for l in open(p):
        l=l.strip()
        if not l or l[0]=='#' or l.startswith('mem,'): continue
        rows.append(l.split(','))
    return rows
def best(p):
    return {int(r[1]):float(r[5]) for r in parse(p) if r[2]=='cme-best'}
def reps(p,modepref='cme-'):
    return [r for r in parse(p) if r[3]!='-']
KiB=1024
for b in BO:
    fs=sorted(glob.glob(BO[b]+'cme-latency-*.csv'))
    rt=[float(r[5]) for f in fs for r in parse(f) if r[2]=='cme-roundtrip-best']
    call=[float(r[5]) for f in fs for r in parse(f) if r[2]=='cme-call-best']
    rr=[r for f in fs for r in parse(f) if r[2]=='cme-roundtrip']
    print(b,'files',len(fs),'rt best',set(rt),'call best',min(call),max(call))
    print('  rt reps n',len(rr),'ns',min(float(r[5]) for r in rr),max(float(r[5]) for r in rr),'span',set(r[6] for r in rr),
      'cyc',{c:sum(1 for r in rr if r[7]==c) for c in set(r[7] for r in rr)},'cmecyc',min(float(r[8]) for r in rr),max(float(r[8]) for r in rr),
      'refills nonzero',sum(1 for r in rr if any(float(x)!=0 for x in r[9:14])))
    cs=[r for f in fs for r in parse(f) if r[2]=='cme-call']; print('  call span',set(r[6] for r in cs))
    s=best(BO[b]+'cme-latency-dram-small.csv'); l=best(BO[b]+'cme-latency-dram-large.csv'); fl=best(BO[b]+'cme-latency-dram-flushed.csv')
    base=21.005
    def rng(d,lo,hi):
        v=[d[k] for k in d if lo<=k<=hi]; return min(v),max(v),round(min(v)-base,3),round(max(v)-base,3)
    print('  L1 4-64K',rng(s,4*KiB,64*KiB)); print('  96-384K',rng(s,96*KiB,384*KiB))
    for k in sorted(s): print('   ',k//KiB,s[k],round(s[k]-base,3))
    for k in sorted(l): print('   L',k//KiB,l[k],round(l[k]-base,3))
    print('  flushed',fl,{k:round(v-base,3) for k,v in fl.items()})
    # l3 file
    p=BO[b]+'cme-latency-dram-small-l3.csv'
    hdr=[x for x in open(p) if x.startswith('mem,')][0].strip().split(',')
    s3=best(p); print('  l3 best',{k//KiB:(v,round(v-base,3)) for k,v in s3.items() if 96*KiB<=k<=384*KiB})
    ih=[i for i,h in enumerate(hdr) if 'hit' in h]; print('  hdr',hdr[9:])
    for r in parse(p):
        if r[3]!='-' and r[1]!='0' and 96*KiB<=int(r[1])<=384*KiB: print('    ',int(r[1])//KiB,r[3],r[5],round(float(r[5])-base,3),[r[i] for i in ih])
    # ocm
    for f in sorted(glob.glob(BO[b]+'cme-latency-ocm-*.csv')):
        rows=[r for r in parse(f) if r[3]!='-' and r[1]!='0']
        sp=min(float(r[6]) for r in rows); bb=[float(r[5]) for r in parse(f) if r[2]=='cme-best']
        rts=set(r[6] for r in parse(f) if r[2]=='cme-roundtrip')
        print('  ',os.path.basename(f),'minspan',sp,'best',bb,'span-21.001',round(sp-21.001,3),'best-21.005',round(bb[0]-21.005,3),'rtspan',rts)
