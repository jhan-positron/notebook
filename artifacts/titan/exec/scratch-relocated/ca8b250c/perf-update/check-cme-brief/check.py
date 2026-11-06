import csv, glob, os, re, statistics as st
R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
D={'E':R+'membench-jibin-010/results/bootE/','R3':R+'membench-jibin-004/results/19700101T000000Z/',
   'A':R+'membench-jibin-005/results/bootA/','B':R+'membench-jibin-006/results/bootB/','C':R+'membench-jibin-007/results/bootC/','D':R+'membench-jibin-008/results/bootD/'}
def rows(path):
    out=[]; hdr=None
    for ln in open(path):
        ln=ln.strip()
        if not ln or ln.startswith('#'): continue
        f=ln.split(',')
        if f[0]=='mem': hdr=f; continue
        out.append(dict(zip(hdr,f)) if hdr else f)
    return out
def best(boot,fn,size,mode=None):
    for r in rows(D[boot]+fn):
        if int(r['size_bytes'])==size and r['mode'] in ((mode,) if mode else ('best','cme-best')): return float(r['ns_per_load'])
def passes(boot,fn,size,col):
    return [float(r[col]) for r in rows(D[boot]+fn) if int(r['size_bytes'])==size and r['rep'] not in ('-',) and r['mode'] not in ('best','cme-best','cme-roundtrip-best')]
def bw(boot,fn,kernel,size):
    for r in rows(D[boot]+fn):
        if r['kernel']==kernel and int(r['bytes_per_thread'])==size and r['rep']=='best': return float(r['aggregate_GBps'])
def bwall(boot,fn,kernel):
    return {int(r['bytes_per_thread']):float(r['aggregate_GBps']) for r in rows(D[boot]+fn) if r['kernel']==kernel and r['rep']=='best'}
K=1024; M=1024*1024
res=[]
def chk(label,page,val,fmt='%.1f'):
    s=fmt%val if isinstance(val,float) else str(val)
    ok = (s==page) if isinstance(page,str) else page(s)
    res.append((ok,label,page if isinstance(page,str) else '(fn)',s,val))
# Short version
chk('SV CME 4K E','21.4',best('E','cme-latency-dram-small.csv',4*K))
chk('SV core 4K E','2.0',best('E','latency-dram-small.csv',4*K))
rt=[float(r['ns_per_load']) for f in glob.glob(D['E']+'cme-*.csv') for r in rows(f) if r['mode']=='cme-roundtrip']
chk('SV roundtrip E min','21.0',min(rt)); chk('SV roundtrip E max','21.0',max(rt)); print('roundtrip range',min(rt),max(rt),len(rt))
bs=[best('B','cme-latency-dram-small.csv',s) for s in (4*K,8*K,16*K,24*K,32*K,48*K,64*K)]
chk('SV B 4-64K min','21.0',min(bs)); chk('SV B 4-64K max','21.3',max(bs)); chk('SV B 96K','37.2',best('B','cme-latency-dram-small.csv',96*K))
cr=bwall('R3','cme-bandwidth-dram-1core.csv','cme-read'); cw=bwall('R3','cme-bandwidth-dram-1core.csv','cme-write')
r160=[v for s,v in cr.items() if s>=160*K]; w16=[v for s,v in cw.items() if s>=16*K]; w160=[v for s,v in cw.items() if s>=160*K]
print('cme read >=160K',sorted(cr.items()),'write',sorted(cw.items()))
chk('SV about 37 GB/s reads (mean 160K+)','37',st.mean(r160),'%.0f')
chk('SV writes 62 to 64 min','62',min(w160),'%.0f'); chk('SV writes max','64',max(w160),'%.0f')
core_r=bwall('R3','bandwidth-dram-1core.csv','read'); core_w=bwall('R3','bandwidth-dram-1core.csv','write')
chk('SV 4 times (32M)','4',cr[32*M]/core_r[32*M],'%.0f'); chk('SV 2 times (32M)','2',cw[32*M]/core_w[32*M],'%.0f')
# Fig 1 caption
chk('fig1 climb +3.6 (8K-4K E)','3.6',best('E','cme-latency-dram-small.csv',8*K)-best('E','cme-latency-dram-small.csv',4*K))
chk('fig1 64-96 step +2.5 E','2.5',best('E','cme-latency-dram-small.csv',96*K)-best('E','cme-latency-dram-small.csv',64*K))
chk('fig1 B step +15.9','15.9',best('B','cme-latency-dram-small.csv',96*K)-best('B','cme-latency-dram-small.csv',64*K))
chk('fig1 core 192K 7.8','7.8',best('E','latency-dram-small.csv',192*K))
cyc=[float(r['cme_cycles_per_load']) for f in glob.glob(D['E']+'cme-*.csv') for r in rows(f) if r['mode']=='cme-roundtrip']
chk('fig1 control 42 cycles','42',st.mean(cyc),'%.0f')
# Fig 2 caption
chk('fig2 CME read 48K 105','105',cr[48*K],'%.0f'); chk('fig2 core writes 32','32',max(core_w.values()),'%.0f')
cc=bwall('R3','cme-bandwidth-dram-1core.csv','cme-copy'); print('cme copy',sorted(cc.items()))
chk('fig2 copy 126 at 16K','126',cc[16*K],'%.0f'); chk('fig2 copy 126 at 48K','126',cc[48*K],'%.0f'); chk('fig2 copy 49 from 160K (min)','49',min(v for s,v in cc.items() if s>=160*K),'%.0f'); chk('fig2 copy 49 from 160K (max)','49',max(v for s,v in cc.items() if s>=160*K),'%.0f')
# Table
chk('T 4K core','2.0',best('E','latency-dram-small.csv',4*K)); chk('T 4K CME','21.4',best('E','cme-latency-dram-small.csv',4*K))
rtbest=[float(r['ns_per_load']) for r in rows(D['E']+'cme-latency-dram-small.csv') if r['mode']=='cme-roundtrip-best'][0]
chk('T control 21.0','21.0',rtbest); chk('T chase minus control 0.37','0.37',best('E','cme-latency-dram-small.csv',4*K)-rtbest,'%.2f')
chk('T run3 4K 21.4','21.4',best('R3','cme-latency-dram-small.csv',4*K))
for s,pc,pm,pr,pb in ((8*K,'2.0','24.9','24.2','21.0'),(16*K,'2.0','35.1','31.6','21.1'),(64*K,'5.1','45.6','47.6','21.3')):
    chk(f'T {s//K}K core E',pc,best('E','latency-dram-small.csv',s)); chk(f'T {s//K}K CME E',pm,best('E','cme-latency-dram-small.csv',s))
    chk(f'T {s//K}K CME run3',pr,best('R3','cme-latency-dram-small.csv',s)); chk(f'T {s//K}K CME B',pb,best('B','cme-latency-dram-small.csv',s))
chk('T 2M core E','24.2',best('E','latency-dram-large.csv',2*M)); chk('T 2M CME E','56.7',best('E','cme-latency-dram-large.csv',2*M)); chk('T 2M CME run3','57.6',best('R3','cme-latency-dram-large.csv',2*M))
chk('T 8M flushed core E','52.7',best('E','latency-dram-flushed.csv',8*M)); chk('T 8M flushed CME E','62.1',best('E','cme-latency-dram-flushed.csv',8*M)); chk('T flushed run3','62.6',best('R3','cme-latency-dram-flushed.csv',8*M)); chk('T flushed C','62.6',best('C','cme-latency-dram-flushed.csv',8*M))
chk('T seq core E','2.5',best('E','latency-dram-seq.csv',8*M)); chk('T seq CME E','21.4',best('E','cme-latency-dram-seq.csv',8*M))
hw=passes('E','cme-latency-dram-seq.csv',8*M,'cme_l1d_refill_hwprf_per_load'); print('seq hwprf per load E',hw)
chk('T seq hwprf 1.00','1.00',min(hw),'%.2f')
chk('T seq A 21.4','21.4',best('A','cme-latency-dram-seq.csv',8*M)); chk('T seq C 21.4','21.4',best('C','cme-latency-dram-seq.csv',8*M)); chk('T seq B 71.7','71.7',best('B','cme-latency-dram-seq.csv',8*M))
coreocm=[best('E',f'latency-ocm-region{i}-cpu2.csv',256*K) for i in range(5)]; cmeocm=[best('E',f'cme-latency-ocm-region{i}.csv',256*K) for i in range(5)]
r3cme=[best('R3',f'cme-latency-ocm-region{i}.csv',256*K) for i in range(5)]
print('core ocm E',coreocm,'cme ocm E',cmeocm,'r3 cme',r3cme)
chk('T OCM core min 19.1','19.1',min(coreocm)); chk('T OCM core max 20.4','20.4',max(coreocm)); chk('T OCM CME min 29.0','29.0',min(cmeocm)); chk('T OCM CME max 37.7','37.7',max(cmeocm))
chk('T OCM run3 CME min 35.5','35.5',min(r3cme)); chk('T OCM run3 CME max 38.5','38.5',max(r3cme))
chk('T all5 dense core E 26.1','26.1',best('E','latency-ocm-all5-dense-cpu2.csv',1310720)); chk('T all5 dense CME E 43.3','43.3',best('E','cme-latency-ocm-all5-dense.csv',1310720)); chk('T all5 dense CME run3 44.7','44.7',best('R3','cme-latency-ocm-all5-dense.csv',1310720))
hops=[int(r['loads']) for r in rows(D['E']+'cme-latency-ocm-all5-dense.csv') if r['rep'] not in ('-',) and r['mode'] not in ('cme-roundtrip','cme-roundtrip-best','cme-best')]; print('dense hops',set(hops))
hops2=[int(r['loads']) for r in rows(D['E']+'cme-latency-ocm-region0.csv') if r['rep'] not in ('-',) and r['mode'] not in ('cme-roundtrip','cme-roundtrip-best','cme-best')]; print('sparse region hops/passes',hops2,len(hops2))
chk('T read 48K core 17.5','17.5',core_r[48*K]); chk('T read 48K CME 104.9','104.9',cr[48*K])
callr=bw('R3','cme-bandwidth-call-cost.csv','cme-read',1024); callw=bw('R3','cme-bandwidth-call-cost.csv','cme-write',1024)
chk('T per-call read 97 ns','97',1024/callr,'%.0f'); chk('T per-call write 39 ns','39',1024/callw,'%.0f')
chk('T 44 % of 16K row','44',100*(1024/callr)/(16384/cr[16*K]),'%.0f')
chk('T read 32M core 9.2','9.2',core_r[32*M]); chk('T read 160K-32M CME min 36.6','36.6',min(r160)); chk('T read max 37.2','37.2',max(r160)); chk('T 4.0 times','4.0',cr[32*M]/core_r[32*M])
chk('T write core min 30.1','30.1',min(core_w.values())); chk('T write core max 32.0','32.0',max(core_w.values())); chk('T write CME min 62.0','62.0',min(w16)); chk('T write CME max 63.9','63.9',max(w16))
chk('T 32 bytes per cycle (63.9GB/s / 2GHz)','32',max(w16)/2,'%.0f')
chk('T OCM read all5 core 16.0','16.0',bw('R3','bandwidth-ocm-all5.csv','read',1310720)); chk('T OCM write all5 core 20.3','20.3',bw('R3','bandwidth-ocm-write.csv','write',1310720))
chk('T OCM read all5 CME 23.2','23.2',bw('R3','cme-bandwidth-ocm-all5.csv','cme-read',1310720)); chk('T OCM write all5 CME 19.8','19.8',bw('R3','cme-bandwidth-ocm-write.csv','cme-write',1310720))
# Section 4
chk('S4 adds 19.4 to dependent','19.4',best('E','cme-latency-dram-small.csv',4*K)-best('E','latency-dram-small.csv',4*K))
chk('S4 adds 9.4 flushed','9.4',best('E','cme-latency-dram-flushed.csv',8*M)-best('E','latency-dram-flushed.csv',8*M))
w23=bw('R3','bandwidth-write-cpus2-3.csv','write',16*M); chk('S4 CPUs 2,3 40.9','40.9',w23); chk('S4 1.51 times','1.51',cw[32*M]/w23,'%.2f'); chk('S4 62.0 at 32M','62.0',cw[32*M])
chk('S4 B 21.02','21.02',best('B','cme-latency-dram-small.csv',4*K),'%.2f'); chk('S4 B 21.26','21.26',max(bs),'%.2f'); chk('S4 B 37.16','37.16',best('B','cme-latency-dram-small.csv',96*K),'%.2f')
def inner_share(boot,s):
    i=passes(boot,'cme-latency-dram-small.csv',s,'cme_l1d_refill_inner_per_load'); o=passes(boot,'cme-latency-dram-small.csv',s,'cme_l1d_refill_outer_per_load')
    return 100*st.mean(i)/(st.mean(i)+st.mean(o)), 100*st.mean([a/(a+b) for a,b in zip(i,o)])
for s in (8*K,16*K,24*K,32*K,64*K): print('inner share E',s//K,inner_share('E',s),'C',inner_share('C',s))
chk('S4 inner 100 % at 8K E','100',inner_share('E',8*K)[1],'%.0f'); chk('S4 inner 88 % at 24K E','88',inner_share('E',24*K)[1],'%.0f')
chk('S4 C 17 % or less (max 8-24K)',lambda v: float(v)<=17.0,max(inner_share('C',s)[1] for s in (8*K,16*K,24*K)),'%.1f')
for s,pe,pc in ((8*K,'0.02','3.33'),(16*K,'1.25','6.55')):
    chk(f'S4 outer pass-mean E {s//K}K',pe,st.mean(passes('E','cme-latency-dram-small.csv',s,'cme_l1d_refill_outer_per_load')),'%.2f')
    chk(f'S4 outer pass-mean C {s//K}K',pc,st.mean(passes('C','cme-latency-dram-small.csv',s,'cme_l1d_refill_outer_per_load')),'%.2f')
chk('S4 E/C 8K 1.019','1.019',best('E','cme-latency-dram-small.csv',8*K)/best('C','cme-latency-dram-small.csv',8*K),'%.3f')
chk('S4 E/C 16K 1.120','1.120',best('E','cme-latency-dram-small.csv',16*K)/best('C','cme-latency-dram-small.csv',16*K),'%.3f')
ec=[best('E','cme-latency-dram-small.csv',s)/best('C','cme-latency-dram-small.csv',s) for s in (48*K,64*K,96*K,128*K,192*K,256*K,384*K)]; print('E/C 48-384',ec)
chk('S4 E/C 48-384 min 0.940','0.940',min(ec),'%.3f'); chk('S4 E/C 48-384 max 0.977','0.977',max(ec),'%.3f')
chk('S4 dense 17.2 above core','17.2',best('E','cme-latency-ocm-all5-dense.csv',1310720)-best('E','latency-ocm-all5-dense-cpu2.csv',1310720))
ocmr=[bw('R3',f'cme-bandwidth-ocm-region{i}.csv','cme-read',256*K)/bw('R3',f'bandwidth-ocm-region{i}.csv','read',256*K) for i in range(5)]
ocmr.append(bw('R3','cme-bandwidth-ocm-all5.csv','cme-read',1310720)/bw('R3','bandwidth-ocm-all5.csv','read',1310720)); print('OCM cme/core read ratios',ocmr)
chk('S4 OCM 1.4 times min','1.4',min(ocmr)); chk('S4 OCM 1.6 times max','1.6',max(ocmr))
# Words
chk('W 42 cycles','42',st.mean(cyc),'%.0f')
n=0
for ok,label,page,s,val in res:
    n+=1
    print(('OK  ' if ok else 'MISS'),label,'page',page,'csv',s,'(%r)'%val)
print('checked',n,'miss',sum(1 for r in res if not r[0]))
