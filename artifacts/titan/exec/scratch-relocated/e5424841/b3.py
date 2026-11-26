import csv, os, collections, statistics as st, numpy as np, re
HERE='/home/jhan/workspace/titan/cache-perf/asimov'
NODES=[88,160,216,288,344]
NPOS={88:(1,3),160:(2,4),216:(3,3),288:(4,4),344:(5,3)}
CPOS={0:(1,2),2:(2,3),3:(2,3),4:(3,2),5:(3,2),6:(4,3),7:(4,3),8:(5,2),9:(5,2)}
KINDS=['ocm-flush','ocm-evict','slc','dram-flush']
C29=[2,3,4,5,6,7,8,9]
def steps(c,n): return abs(CPOS[c][0]-NPOS[n][0]),abs(CPOS[c][1]-NPOS[n][1])
def arm_select(pa,n=5):
    a=pa>>6; h=(a&0xfff)^((a>>12)&0xfff)^((a>>24)&0xfff)^((a>>36)&0x3ff); top=0
    for k in range(6): top|=(((h>>(11-k))^(h>>k))&1)<<(5-k)
    return (((top<<6)|(h&0x3f))*n)>>12
class Boot:
    def __init__(s,num,b):
        s.dir=os.path.join(HERE,'results/membench-jibin-%s/results/bootM%d'%(num,b)); s.b=b
        L=open(os.path.join(s.dir,'latency-map.csv')).read().split('\n')
        s.hash=[l for l in L if l.startswith('#')]
        rows=list(csv.reader(l for l in L if l and not l.startswith('#')))
        s.H={n:i for i,n in enumerate(rows[0])}; s.rows=rows[1:]
        s.cells=collections.defaultdict(list)
        for r in s.rows:
            if r[0]!='idle': s.cells[(r[0],int(r[1]),int(r[2]))].append(r)
    def col(s,k,c,n,name): return [float(r[s.H[name]]) for r in s.cells[(k,c,n)]]
    def best(s,k,c,n): return min(s.col(k,c,n,'ns_per_load'))
    def med(s,k,c,n,name='ns_per_load'): return st.median(s.col(k,c,n,name))
    def fit(s,kind,f=None):
        f=f or s.best
        A=np.array([[1,*steps(c,n)] for c in C29 for n in NODES],float)
        y=np.array([f(kind,c,n) for c in C29 for n in NODES])
        co=np.linalg.lstsq(A,y,rcond=None)[0]; r=y-A@co
        return co,float((r**2).mean()**.5),float(abs(r).max())
    def hashcheck(s):
        L=open(os.path.join(s.dir,'map-homes.txt')).read().split('\n')
        pfn=int(re.search(r'pfn=(0x[0-9a-f]+)',L[0]).group(1),16)
        t=''.join(x for x in L[1:] if not x.startswith('#'))
        m=collections.Counter()
        for i,ch in enumerate(t):
            if ch in '01234': m[(arm_select((pfn<<12)+64*i),int(ch))]+=1
        mp={}
        for (f,h),c in m.items():
            if c>mp.get(f,(0,0))[1]: mp[f]=(h,c)
        agree=sum(c for (f,h),c in m.items() if mp[f][0]==h)
        return hex(pfn),len(t),sum(m.values()),agree,[NODES[mp[f][0]] for f in range(5)],t.count('?'),collections.Counter(t)
B={1:Boot('014',1),2:Boot('015',2),3:Boot('016',3)}
if __name__=='__main__':
  for b,o in B.items():
    print('=== boot',b,len(o.rows),'rows', len(o.cells),'cells', {len(v) for v in o.cells.values()}, 'fields',{len(r) for r in o.rows})
    print(' perf_cov min',min(float(r[o.H['perf_cov']]) for r in o.rows))
    for l in o.hash: 
        if 'classify' in l or 'read_floor' in l or 'level' in l or 'pagemap' in l: print('  ',l[:150])
    print(' hash',o.hashcheck())
    for k in KINDS:
        co,rms,mx=o.fit(k); v=[o.best(k,c,n) for c in C29 for n in NODES]
        com,rmsm,_=o.fit(k,o.med)
        print(' %-10s best %.2f..%.2f fit %.2f+%.2fX+%.2fY rms %.2f max %.2f | medfit %.2f+%.2fX+%.2fY rms %.2f'%(k,min(v),max(v),*co,rms,mx,*com,rmsm))
        for name in ['l1d_refill','l2d_refill','l3d_refill_rd','l1d_refill_hwprf','l2d_refill_hwprf','l1d_tlb_refill']+(['mc_reqs','cache_miss','snp_sent'] if k!='ocm-flush' else []):
            x=[float(r[o.H[name]]) for (kk,c,n),rs in o.cells.items() if kk==k and c>=2 for r in rs]
            print('     %-18s min %.4f med %.4f max %.4f'%(name,min(x),st.median(x),max(x)))
        stp=[np.mean(o.col(k,c,n,'ns_per_load')[4:])-np.mean(o.col(k,c,n,'ns_per_load')[:4]) for c in C29 for n in NODES]
        sp=[max(o.col(k,c,n,'ns_per_load'))-min(o.col(k,c,n,'ns_per_load')) for c in C29 for n in NODES]
        print('     step4-6 mean %+.2f (%+.2f..%+.2f) spread %.2f..%.2f'%(np.mean(stp),min(stp),max(stp),min(sp),max(sp)))
    for cpu in (2,8):
        for reg in (0,4):
            p=os.path.join(o.dir,'latency-ocm-region%d-mapctl-cpu%d.csv'%(reg,cpu))
            bb=[float(l.split(',')[5]) for l in open(p) if ',best,' in l][0]
            print('  ctl cpu%d node%d %.3f map %.3f'%(cpu,NODES[reg],bb,o.best('ocm-flush',cpu,NODES[reg])))
    print(' cpu0:')
    for k in KINDS: print('   ',k,' '.join('%.2f'%o.best(k,0,n) for n in NODES), '| med',' '.join('%.2f'%o.med(k,0,n) for n in NODES))
    for k in KINDS:
        print('  table',k)
        for c in C29: print('    cpu',c,' '.join('%6.2f'%o.best(k,c,n) for n in NODES),' | med ',' '.join('%6.2f'%o.med(k,c,n) for n in NODES))
  for k in KINDS:
    for a,b in ((1,2),(2,3)):
        d=[B[b].best(k,c,n)-B[a].best(k,c,n) for c in C29 for n in NODES]
        print('diff best boot%d-boot%d %-10s mean %+.2f min %+.2f max %+.2f'%(b,a,k,np.mean(d),min(d),max(d)))
