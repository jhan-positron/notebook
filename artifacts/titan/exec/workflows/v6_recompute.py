import glob, os, statistics as st
R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
B={'F1':R+'membench-jibin-011/results/bootF1/','F2':R+'membench-jibin-012/results/bootF2/'}
def rows(b):
    out=[]
    for p in sorted(glob.glob(B[b]+'cme-latency-*.csv')):
        hdr=None
        for ln in open(p):
            ln=ln.strip()
            if not ln or ln.startswith('#'): continue
            c=ln.split(',')
            if c[0]=='mem': hdr=c; continue
            if c[3]=='-' : continue
            d=dict(zip(hdr,c)); d['file']=os.path.basename(p); out.append(d)
    return out
def med(x): return st.median(x)
for b in ('F2','F1'):
    rs=rows(b)
    # clock ratio on long rows
    long=[r for r in rs if int(r['loads'])>=8192 and r['mode']!='cme-call']
    cr=[float(r['cycles_per_load'])/float(r['ns_per_load']) for r in long]
    mr=[float(r['cme_cycles_per_load'])/float(r['ns_per_load_span']) for r in long]
    print(b,'long rows',len(long),'core c/ns %.4f..%.4f med %.4f'%(min(cr),max(cr),med(cr)),'cme c/span %.4f..%.4f med %.4f'%(min(mr),max(mr),med(mr)))
    allr=cr+mr
    kinds={'ocm-64':[r for r in rs if r['file'].startswith('cme-latency-ocm') and r['loads']=='64' and r['mode']!='cme-call'],
           'ocm-320':[r for r in rs if r['file'].startswith('cme-latency-ocm') and r['loads']=='320' and r['mode']!='cme-call'],
           'cme-call':[r for r in rs if r['mode']=='cme-call']}
    for k,v in kinds.items():
        for cpn in (2.0,):
            L=[int(r['loads']) for r in v]
            core=[float(r['cycles_per_load'])*l/cpn for r,l in zip(v,L)]
            cme=[float(r['cme_cycles_per_load'])*l/cpn for r,l in zip(v,L)]
            brk=[float(r['ns_per_load'])*l for r,l in zip(v,L)]
            spn=[float(r['ns_per_load_span'])*l for r,l in zip(v,L)]
            dc=[(float(r['cycles_per_load'])-float(r['cme_cycles_per_load']))*l for r,l in zip(v,L)]
            ordn=sum(1 for a,c,e,g in zip(core,brk,cme,spn) if a>=c>=e>=g)
            strict=sum(1 for a,c,e,g in zip(core,brk,cme,spn) if a>c>e>g)
            print(' ',k,'n',len(v),'files',len(set(r['file'] for r in v)),'modes',sorted(set(r['mode'] for r in v))[:3])
            print('   med core %.1f brk %.1f cme %.1f span %.1f'%(med(core),med(brk),med(cme),med(spn)))
            print('   dcyc %.0f..%.0f med %.1f -> %.2f ns'%(min(dc),max(dc),med(dc),med(dc)/cpn))
            cb=[a-c for a,c in zip(core,brk)]; bc=[a-c for a,c in zip(brk,cme)]; cs=[a-c for a,c in zip(cme,spn)]; bs=[a-c for a,c in zip(brk,spn)]
            print('   core-brk %.2f  brk-cme %.2f  cme-span %.2f  brk-span med %.2f (%.1f..%.1f)'%(med(cb),med(bc),med(cs),med(bs),min(bs),max(bs)))
            print('   min of diffs: core-brk %.1f brk-cme %.1f cme-span %.1f'%(min(cb),min(bc),min(cs)))
            dev=max(abs(med(cb)-(med(core)-med(brk))),abs(med(bc)-(med(brk)-med(cme))),abs(med(cs)-(med(cme)-med(spn))))
            print('   ordered',ordn,'strict',strict,'dev %.2f'%dev)
            if k=='cme-call':
                o=[(float(r['ns_per_load'])-float(r['ns_per_load_span'])) for r in v]
                print('   outside-span per call med %.4f x64 = %.1f ; lowest rep total outside %.1f'%(med(o),med(o)*64,min(bs)))
                print('   lowest bracket %.3f, spans'%min(float(r['ns_per_load']) for r in v), sorted(set(r['ns_per_load_span'] for r in v)), 'min outside %.3f'%min(o))
