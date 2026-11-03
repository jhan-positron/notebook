import csv, json, sys, glob, os
R='/home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-001/results/19700101T000000Z'
def rows(f):
    out=[]
    with open(os.path.join(R,f)) as fh:
        for ln,line in enumerate(fh,1):
            if line.startswith('#') or line.startswith('mem,'): continue
            p=line.strip().split(',')
            out.append((ln,p))
    return out
def lat(f):
    best={}; reps={}
    for ln,p in rows(f):
        size=int(p[1])
        if p[2]=='best': best[size]=(float(p[5]),ln)
        else: reps.setdefault(size,[]).append(dict(line=ln,mode=p[2],rep=p[3],loads=int(p[4]),ns=float(p[5]),cyc=float(p[6]),l1=float(p[7]),l2=float(p[8]),l3=float(p[9])))
    return best,reps
out={}
for f in ['latency-dram-small.csv','latency-dram-large.csv','latency-dram-flushed.csv']+[f'latency-ocm-region{i}.csv' for i in range(5)]+['latency-ocm-all5-flushed.csv','latency-ocm-all5-fresh.csv']:
    b,r=lat(f)
    out[f]={}
    for s in sorted(b):
        rr=r[s]
        bestrow=min(rr,key=lambda d:d['ns'])
        out[f][s]=dict(best=b[s][0],best_line=b[s][1],best_row=bestrow,l3_range=(min(d['l3'] for d in rr),max(d['l3'] for d in rr)),l2_range=(min(d['l2'] for d in rr),max(d['l2'] for d in rr)),ns_range=(min(d['ns'] for d in rr),max(d['ns'] for d in rr)))
def bw(f):
    res={}
    for ln,p in rows(f):
        key=(p[1],int(p[2]),int(p[3]))
        if p[4]=='best': res.setdefault(key,{})['best']=(float(p[7]),ln)
        else:
            d=res.setdefault(key,{}); d.setdefault('reps',[]).append(dict(line=ln,total=int(p[5]),el=float(p[6]),agg=float(p[7]),mn=float(p[8]),mx=float(p[9])))
    return res
for f in ['bandwidth-dram-1core.csv','bandwidth-pair.csv','bandwidth-perdsu.csv','bandwidth-all8.csv','bandwidth-ocm-write.csv','bandwidth-ocm-copy.csv','bandwidth-ocm-all5.csv','bandwidth-ocm-4core.csv']+[f'bandwidth-ocm-region{i}.csv' for i in range(5)]:
    out[f]={str(k):v for k,v in bw(f).items()}
# derived
d={}
d['ocm_write_us']=[r['el']*1e6 for r in bw('bandwidth-ocm-write.csv')[('write',1,262144)]['reps']]
d['ocm_write_ns_per_line_if_all_flush']=[r['el']*1e9/4096 for r in bw('bandwidth-ocm-write.csv')[('write',1,262144)]['reps']]
d['dram_write_1core_32M_us_per_256K']=262144/ (bw('bandwidth-dram-1core.csv')[('write',1,33554432)]['best'][0]*1e9)*1e6
# hop groups
one=[out[f'latency-ocm-region{i}.csv'][262144]['best'] for i in (0,1,2)]
three=[out[f'latency-ocm-region{i}.csv'][262144]['best'] for i in (3,4)]
d['ocm_1hop_best']=one; d['ocm_3hop_best']=three
d['ocm_gap_est']=(sum(three)/2 - sum(one)/3)
# bytes per cycle for L1 read
d['l1_read_B_per_cycle']=bw('bandwidth-dram-1core.csv')[('read',1,16384)]['best'][0]*1e9/2e9
d['write_B_per_cycle']=bw('bandwidth-dram-1core.csv')[('write',1,33554432)]['best'][0]*1e9/2e9
# outstanding lines est
for s,ns in ((2097152,23.98),(33554432,52.3)):
    g=bw('bandwidth-dram-1core.csv')[('read',1,s)]['best'][0]
    d[f'outstanding_lines_est_{s}']=g*1e9/64*ns*1e-9
out['derived']=d
json.dump(out,open('/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/summary.json','w'),indent=1,default=str)
# compact print
for f in out:
    if f.startswith('latency'):
        print('==',f)
        for s,v in out[f].items():
            br=v['best_row']; print(f"  {s:>9} best {v['best']:7.3f} ns (line {v['best_line']}) refills l1 {br['l1']:.3f} l2 {br['l2']:.3f} l3 {br['l3']:.3f}; ns range {v['ns_range']}; l3 range {v['l3_range']}")
    elif f.startswith('bandwidth'):
        print('==',f)
        for k,v in out[f].items():
            print(f"  {k:<32} best {v['best'][0]:8.3f} GB/s (line {v['best'][1]}) per-thread min/max of best rep: ", min(r['mn'] for r in v['reps']), max(r['mx'] for r in v['reps']))
print('== derived'); print(json.dumps(d,indent=1))
