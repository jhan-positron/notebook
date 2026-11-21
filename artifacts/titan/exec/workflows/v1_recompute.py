import csv, os
R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
B={'F1':R+'membench-jibin-011/results/bootF1/','F2':R+'membench-jibin-012/results/bootF2/'}
def rows(boot,f):
    out=[]; hdr=None
    for ln in open(B[boot]+f):
        ln=ln.strip()
        if not ln or ln.startswith('#'): continue
        p=ln.split(',')
        if p[0]=='mem': hdr=p; continue
        out.append(dict(zip(hdr,p)))
    return out
def best(boot,f):
    d={}
    rs=rows(boot,f)
    for r in rs:
        if r['rep']=='best':
            k=(r['kernel'],int(r['bytes_per_thread']))
            # span of first rep whose aggregate equals best
            sp=[x for x in rs if x['rep']!='best' and x['kernel']==r['kernel'] and x['bytes_per_thread']==r['bytes_per_thread'] and x['aggregate_GBps']==r['aggregate_GBps']]
            d.setdefault(k,[]).append((float(r['aggregate_GBps']), float(sp[0]['span_GBps']) if sp and 'span_GBps' in sp[0] else None, float(r.get('span_GBps','nan')) if r.get('span_GBps','-')!='-' else None, float(sp[0]['elapsed_s']) if sp else None, sp[0] if sp else None))
    return d
K=1024
for b in B:
    print('==',b)
    d={}
    for f in ('cme-bandwidth-l1-asmpasses.csv','cme-bandwidth-dram-1core-asmpasses.csv'):
        for k,v in best(b,f).items():
            d.setdefault(k,[]).extend([(f,)+x[:3] for x in v])
    for k in sorted(d): print(k, d[k])
    sizes=[4*K,8*K,16*K,24*K,48*K]
    def one(kern,s): 
        v=d[(kern,s)]; assert len(v)==1,(kern,s,v); return v[0]
    rd=[one('cme-read',s)[1] for s in sizes]; wr=[one('cme-write',s)[1] for s in sizes]
    print('read GB/s %.1f-%.1f B/cyc %.2f-%.2f vec/cyc %.2f-%.2f cyc/KiB %.1f-%.1f ldinstr/cyc %.2f-%.2f'%(min(rd),max(rd),min(rd)/2,max(rd)/2,min(rd)/128,max(rd)/128,1024/(max(rd)/2),1024/(min(rd)/2),min(rd)/2/256,max(rd)/2/256))
    print('write GB/s %.1f-%.1f B/cyc %.2f-%.2f effcyc/64 %.2f-%.2f'%(min(wr),max(wr),min(wr)/2,max(wr)/2,128/max(wr),128/min(wr)))
    wr2=[d[('cme-write',s)][0][1] for s in sizes+[96*K,160*K,256*K]]
    print('write 4K-256K effcyc %.2f-%.2f'%(128/max(wr2),128/min(wr2)), 'write GB/s 4K-256K %.1f-%.1f'%(min(wr2),max(wr2)))
    rs=[one('cme-read',s)[2] for s in sizes]; ws=[one('cme-write',s)[2] for s in sizes]
    print('span ratios', ['%.2f'%(a/c) for a,c in zip(rs,ws)], 'check span(first rep)==best-row span', [one('cme-read',s)[2]==one('cme-read',s)[3] for s in sizes],[one('cme-write',s)[2]==one('cme-write',s)[3] for s in sizes])
    r16=one('cme-read',16*K); w16=one('cme-write',16*K)
    print('16K span', r16[2], w16[2], 'ratio %.4f'%(r16[2]/w16[2]), 'effcyc %.3f %.3f'%(128/r16[2],128/w16[2]))
    # looped
    L=best(b,'cme-bandwidth-dram-1core.csv')
    for k in sorted(L): print(' looped',k,[x[:3] for x in L[k]])
