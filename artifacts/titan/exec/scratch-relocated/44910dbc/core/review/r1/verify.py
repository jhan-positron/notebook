import csv,sys,os
P=sys.argv[1]
F1=P+'/results/membench-jibin-011/results/bootF1/'; E=P+'/results/membench-jibin-010/results/bootE/'
def reps(path):
    out=[]
    for i,l in enumerate(open(path),1):
        if l.startswith('#') or l.startswith('mem,'): continue
        f=l.strip().split(',')
        if f[2]=='best': continue
        out.append((i,float(f[5]),f))
    return out
print('R1-1')
for shape,fn in (('one line per page','latency-ocm-all5-cpu%d.csv'),('every line','latency-ocm-all5-dense-cpu%d.csv')):
    for cpu in (2,8):
        a=[v for _,v,_ in reps(F1+fn%cpu)]; b=[v for _,v,_ in reps(E+fn%cpu)]
        gap=max(min(a),min(b))-min(max(a),max(b))
        print(' %s cpu%d F1 %.3f..%.3f (%.3f%%) E %.3f..%.3f (%.3f%%) ratio %.4f best diff %.3f%% gap %.3f %s'%(shape,cpu,min(a),max(a),(max(a)-min(a))/min(a)*100,min(b),max(b),(max(b)-min(b))/min(b)*100,min(b)/min(a),(min(b)/min(a)-1)*100,gap,'DISJOINT' if gap>0 else 'overlap'))
print('R1-2 F1 latency-dram-large.csv')
hdr=None
for i,l in enumerate(open(F1+'latency-dram-large.csv'),1):
    if l.startswith('mem,'): hdr=l.strip().split(',')
    if i in (5,6,7,8,9,10,11,12):
        f=l.strip().split(',')
        if len(f)>8 and f[2]!='best':
            d=dict(zip(hdr,f)); print(' line',i,d['size_bytes'],d['mode'],'ns',d['ns_per_load'],'a2',d['l3d_refill_rd_per_load'],'l2pf',d['l2d_refill_hwprf_per_load'],'l2',d['l2d_refill_per_load'],'l2byl1pf',d.get('l2d_refill_l1dhwprf_per_load'))
print('R1-4 F1 bandwidth-dram-1core.csv header + 48/96 KiB')
for i,l in enumerate(open(F1+'bandwidth-dram-1core.csv'),1):
    if 16<=i<=37 or i<=3: print(' %d: %s'%(i,l.strip()[:230]))
