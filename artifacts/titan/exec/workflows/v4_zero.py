import glob,os,csv
R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
B={'F1':R+'membench-jibin-011/results/bootF1/','F2':R+'membench-jibin-012/results/bootF2/'}
def rows(f):
    hdr=None
    for ln in open(f):
        ln=ln.rstrip('\n')
        if not ln or ln.startswith('#'): continue
        p=ln.split(',')
        if p[0]=='mem': hdr=p; continue
        if hdr and len(p)>=len(hdr)-2 and p[3] not in ('-',''):
            yield dict(zip(hdr,p))
for b,d in B.items():
    print('==',b)
    for f in sorted(glob.glob(d+'cme-latency-*.csv')):
        n=0; hw=[]; rd=[]; base=[]; l3ne=0; l3n=0
        for r in rows(f):
            mode=r['mode']
            cols=[k for k in r if 'refill' in k]
            if mode.startswith('cme-roundtrip') or mode.startswith('cme-call'):
                for k in cols:
                    if float(r[k])!=0: base.append((mode,k,r[k]))
                continue
            n+=1
            for k in cols:
                if 'hwprf' in k: hw.append(float(r[k])*int(r['loads']) if False else float(r[k]))
                if k.endswith('refill_rd_per_load'): rd.append((float(r[k]),int(r['loads'])))
            l3=[k for k in r if 'l3' in k.lower() and 'refill' in k]
            out=[k for k in r if 'refill_outer' in k]
            if l3 and out:
                l3n+=1
                if r[l3[0]]!=r[out[0]]: l3ne+=1
        print(os.path.basename(f),'reps',n,'hwprf min/max',(min(hw),max(hw)) if hw else None,'nonzero base',base[:3],'l3!=outer',l3ne,'/',l3n)
        if 'ocm-region' in f:
            print('   rd*loads',sorted(set(round(a*l,3) for a,l in rd)))
