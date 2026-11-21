R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
F1=R+'membench-jibin-011/results/bootF1/'; F2=R+'membench-jibin-012/results/bootF2/'
def best(p,tag):
    d={}
    for l in open(p):
        r=l.strip().split(',')
        if len(r)>5 and r[2]==tag: d[int(r[1])]=float(r[5])
    return d
core={**best(F1+'latency-dram-small.csv','best'),**best(F1+'latency-dram-large.csv','best')}
c2={**best(F2+'cme-latency-dram-small.csv','cme-best'),**best(F2+'cme-latency-dram-large.csv','cme-best')}
c1={**best(F1+'cme-latency-dram-small.csv','cme-best'),**best(F1+'cme-latency-dram-large.csv','cme-best')}
ab=[];be=[]
for k in sorted(c2):
    d=round(c2[k]-21.005-core[k],3); (ab if d>0 else be).append((k//1024,d))
print(len(c2),'above',ab); print('below',len(be),min(d for _,d in be),max(d for _,d in be))
d1=[round(c1[k]-core[k],3) for k in c1]; print('F1 cme-core',min(d1),max(d1))
print('core L1 4-32K',min(core[k] for k in core if k<=32768),max(core[k] for k in core if k<=32768), 'core 4-64K',min(core[k] for k in core if k<=65536),max(core[k] for k in core if k<=65536))
cf=best(F1+'latency-dram-flushed.csv','best'); f1=best(F1+'cme-latency-dram-flushed.csv','cme-best'); print(cf,f1,{k:round(f1[k]-cf[k],3) for k in cf})
co=best(F1+'latency-ocm-all5-dense-cpu2.csv','best'); print('core ocm dense',co, round(45.532-list(co.values())[0],3), round(21.001-(45.532-list(co.values())[0]),3))
