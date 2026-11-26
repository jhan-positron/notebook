import re,sys
R='/home/jhan/workspace/titan/cache-perf/crb/results/'
for f in ['sudo-20261102T054936Z/writebw.csv','sudo-20261102T040631Z/writebw.csv','sudo-20261102T034539Z/writebw.csv']:
    try:
        L=open(R+f).read().split('\n')
    except Exception as e:
        print(f,'ERR',e); continue
    print('=====',f,len(L))
    case=None; runs=[]
    cur=None
    for i,x in enumerate(L,1):
        if x.startswith('-- '):
            m=re.match(r'-- (\S+) (short|long) events (\S+) args (.*)',x)
            if m:
                cur=dict(case=m.group(1),kind=m.group(2),events=m.group(3),args=m.group(4),line=i,rows=[],bw=None)
                runs.append(cur)
            else:
                cur=None
            continue
        if cur is None: continue
        p=x.split(',')
        if len(p)>=10 and p[3]=='0' and p[0] in('asmread','asmwrite','asmcopy','read','write','copy'):
            cur['bw']=(i,int(p[4]),float(p[5]),float(p[6]),float(p[7]),float(p[8]),float(p[9]))
        elif len(p)>=5 and '/' in p[2]:
            cur['rows'].append((i,int(p[0]),p[2],int(p[3]),float(p[4])))
    sel=[r for r in runs if r['case']=='asmread-8M-4']
    print('case asmread-8M-4 runs:',len(sel))
    for r in sel:
        print(r['line'],r['kind'],r['events'],'bwline',r['bw'][0],'GBps',r['bw'][3],'min/max/avg',r['bw'][4:],[ (a,c,e) for a,b,c,d,e in r['rows'] if 'slc_sf_cache_access' in c])
    aggs=[r['bw'][3] for r in sel]
    if aggs:
        print('all runs agg min/max',min(aggs),max(aggs),'half',min(aggs)/2,max(aggs)/2)
        longs=[r['bw'][3] for r in sel if r['kind']=='long']
        print('long runs',longs, min(longs)/2,max(longs)/2)
    # share
    acc=[r for r in sel if 'hns_slc_sf_cache_access_all' in r['events']]
    if len(acc)==2:
        s=[r for r in acc if r['kind']=='short'][0]; l=[r for r in acc if r['kind']=='long'][0]
        def cnt(r,mesh):
            return [b for a,b,c,d,e in r['rows'] if c=='arm_cmn_%d/hns_slc_sf_cache_access_all/'%mesh][0]
        lines=(l['bw'][1]-s['bw'][1])/64
        for mesh in (0,1):
            print('mesh',mesh,'acc diff',cnt(l,mesh)-cnt(s,mesh),'per line',(cnt(l,mesh)-cnt(s,mesh))/lines)
        print('both',(cnt(l,0)-cnt(s,0)+cnt(l,1)-cnt(s,1))/lines)
        print('long alone mesh0', cnt(l,0)/(l['bw'][1]/64), 'short alone', cnt(s,0)/(s['bw'][1]/64))
        print('rates of the runs with the count: short',s['bw'][3],'long',l['bw'][3], 'col5',[e for a,b,c,d,e in s['rows']+l['rows']])
    # all column-5 values
    c5=set()
    for x in L:
        p=x.split(',')
        if len(p)>=5 and '/' in p[2]:
            c5.add(p[4])
    print('column5 values in file:',sorted(c5))
    # cases list
    print('cases:',sorted(set(r['case'] for r in runs)))
