import re,sys,collections
C='/home/jhan/workspace/titan/cache-perf/crb/results/'
def parse(path):
    runs=[]; cur=None
    for i,l in enumerate(open(path,encoding='utf-8').read().split('\n')):
        ln=i+1
        if l.startswith('-- '):
            m=re.match(r'-- (\S+) (short|long) events (\S+) args (.*)',l)
            if m:
                cur={'case':m.group(1),'len':m.group(2),'events':m.group(3),'args':m.group(4),'line':ln,'rows':[],'counts':{},'scaled':{}}
                runs.append(cur)
            else:
                cur={'case':l,'len':None,'events':None,'args':None,'line':ln,'rows':[],'counts':{},'scaled':{}}; runs.append(cur)
            continue
        if cur is None: continue
        f=l.split(',')
        if len(f)>=10 and f[3] not in ('rep','best') and f[0] not in ('kernel',) and f[4].isdigit():
            cur['rows'].append({'line':ln,'kernel':f[0],'threads':int(f[1]),'bytes':int(f[2]),'total':int(f[4]),'el':float(f[5]),'agg':float(f[6]),'mn':float(f[7]),'mx':float(f[8]),'avg':float(f[9])})
        elif len(f)>=5 and '/' in f[2]:
            try: cur['counts'][f[2]]=(int(f[0]),ln); cur['scaled'][f[2]]=float(f[4])
            except ValueError: cur['counts'][f[2]]=(f[0],ln); cur['scaled'][f[2]]=None
    return runs
for d in ('sudo-20261102T054936Z','sudo-20261102T040631Z'):
    runs=parse(C+d+'/writebw.csv')
    print('=====',d,'runs',len(runs))
    cases=collections.OrderedDict()
    for r in runs: cases.setdefault(r['case'],[]).append(r)
    allsc=[v for r in runs for v in r['scaled'].values()]
    print('  counter-running share (column 5): min',min(x for x in allsc if x is not None),'max',max(x for x in allsc if x is not None),'none:',sum(1 for x in allsc if x is None))
    for case in ('asmread-8M-1','asmread-8M-2','asmread-8M-4'):
        if case not in cases: print('  no case',case); continue
        rs=cases[case]
        aggs=[(r['len'],r['events'],row['agg'],row['line'],row['mn'],row['mx']) for r in rs for row in r['rows']]
        print('  case',case,'args:',rs[0]['args'])
        for a in aggs: print('     %-5s %-55s agg=%.2f (line %d) per-thread min=%.2f max=%.2f half=%.2f'%(a[0],a[1],a[2],a[3],a[4],a[5],a[2]/2))
        print('     aggregate range %.2f..%.2f ; half %.2f..%.2f ; 2*thread-min %.2f, 2*thread-max %.2f'%(min(a[2] for a in aggs),max(a[2] for a in aggs),min(a[2] for a in aggs)/2,max(a[2] for a in aggs)/2,2*min(a[4] for a in aggs),2*max(a[5] for a in aggs)))
        # share: slc_sf_cache_access_all long - short
        sh=[r for r in rs if 'hns_slc_sf_cache_access_all' in (r['events'] or '')]
        S_=[r for r in sh if r['len']=='short'][0]; L_=[r for r in sh if r['len']=='long'][0]
        for meshes in (('arm_cmn_0',),('arm_cmn_0','arm_cmn_1')):
            da=sum(L_['counts'][m+'/hns_slc_sf_cache_access_all/'][0]-S_['counts'][m+'/hns_slc_sf_cache_access_all/'][0] for m in meshes)
            db=L_['rows'][0]['total']-S_['rows'][0]['total']
            print('     share with',meshes,': d_access=%d d_lines=%d share=%.4f ; long only: %.4f'%(da,db//64,da/(db/64), sum(L_['counts'][m+'/hns_slc_sf_cache_access_all/'][0] for m in meshes)/(L_['rows'][0]['total']/64)))
        print('     lines used: short row',S_['rows'][0]['line'],'short count',S_['counts']['arm_cmn_0/hns_slc_sf_cache_access_all/'][1],'long row',L_['rows'][0]['line'],'long count',L_['counts']['arm_cmn_0/hns_slc_sf_cache_access_all/'][1], 'scaled%',S_['scaled']['arm_cmn_0/hns_slc_sf_cache_access_all/'],L_['scaled']['arm_cmn_0/hns_slc_sf_cache_access_all/'])
