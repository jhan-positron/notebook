import csv, glob, os, re, statistics as st, sys
R = '/home/jhan/workspace/titan/cache-perf/asimov/results'
D = {'E': R+'/membench-jibin-010/results/bootE', 'C': R+'/membench-jibin-007/results/bootC',
     'B': R+'/membench-jibin-006/results/bootB', 'A': R+'/membench-jibin-005/results/bootA',
     'D': R+'/membench-jibin-008/results/bootD', 'R3': R+'/membench-jibin-004/results/19700101T000000Z'}

def lat(path):
    """rows: list of dicts; header line is the first non-# line; best rows have fewer fields"""
    rows=[]; hdr=None
    for line in open(path):
        line=line.strip()
        if not line or line.startswith('#'): continue
        f=line.split(',')
        if f[0]=='mem': hdr=f; continue
        d={}
        for i,k in enumerate(hdr):
            if i<len(f): d[k]=f[i]
        d['size']=int(d['size_bytes']); 
        try: d['ns']=float(d['ns_per_load'])
        except: d['ns']=None
        rows.append(d)
    return rows

def best(rows,size,mode):
    for r in rows:
        if r['size']==size and r['mode']==mode: return r['ns']
def passes(rows,size,prefix):
    return [r for r in rows if r['size']==size and r['mode'].startswith(prefix) and r['rep']!='-']
def pm(rows,size,prefix,col):
    p=passes(rows,size,prefix); return sum(float(r[col]) for r in p)/len(p)

def bw(path):
    rows=[]; hdr=None
    for line in open(path):
        line=line.strip()
        if not line or line.startswith('#'): continue
        f=line.split(',')
        if f[0]=='mem': hdr=f; continue
        d=dict(zip(hdr,f)); d['bytes']=int(d['bytes_per_thread']); d['gbps']=float(d['aggregate_GBps']); rows.append(d)
    return rows
def bwbest(rows,kernel,b):
    for r in rows:
        if r['kernel']==kernel and r['bytes']==b and r['rep']=='best': return r['gbps']
def bwreps(rows,kernel,b):
    return [r['gbps'] for r in rows if r['kernel']==kernel and r['bytes']==b and r['rep']!='best']

K=1024; M=1024*1024
SM=[4*K,8*K,16*K,24*K,32*K,48*K,64*K,96*K,128*K,192*K,256*K,384*K]
LG=[512*K,768*K,M,int(1.5*M),2*M,3*M,4*M,6*M,8*M,16*M,32*M]

def cme_rows(b):
    s=lat(D[b]+'/cme-latency-dram-small.csv'); l=lat(D[b]+'/cme-latency-dram-large.csv')
    out={}
    for z in SM: out[z]=(best(s,z,'cme-best'), s)
    for z in LG: out[z]=(best(l,z,'cme-best'), l)
    return out
def core_rows(b):
    s=lat(D[b]+'/latency-dram-small.csv'); l=lat(D[b]+'/latency-dram-large.csv')
    out={}
    for z in SM: out[z]=best(s,z,'best')
    for z in LG: out[z]=best(l,z,'best')
    return out

print('== Short version / table 4.1 (E, C, run3, B)')
E=cme_rows('E'); C=cme_rows('C'); R3=cme_rows('R3'); B=cme_rows('B'); A=cme_rows('A'); coreE=core_rows('E')
for z in SM+LG:
    e=E[z][0]; c=C[z][0]; r=R3[z][0]; b=B[z][0]
    rows=E[z][1]; pre='cme-repeat' if z in SM else 'cme-fresh'
    inner=pm(rows,z,pre,'cme_l1d_refill_inner_per_load'); outer=pm(rows,z,pre,'cme_l1d_refill_outer_per_load')
    dem=pm(rows,z,pre,'cme_l1d_refill_rd_per_load'); pf=pm(rows,z,pre,'cme_l1d_refill_hwprf_per_load')
    crows=C[z][1]; cin=pm(crows,z,pre,'cme_l1d_refill_inner_per_load'); cout=pm(crows,z,pre,'cme_l1d_refill_outer_per_load')
    print(f'{z/K:8.0f}K core {coreE[z]:7.3f} E {e:7.3f} diff {e-coreE[z]:5.1f} R3 {r:7.3f} C {c:7.3f} E/C {e/c:.3f} inner {inner:.2f} outer {outer:.2f} dem {dem:.2f} pf {pf:.2f} | innershare E {100*inner/(inner+outer):.1f}% C {100*cin/(cin+cout):.1f}% | C inner {cin:.2f} outer {cout:.2f} Ctot {cin+cout:.2f} Etot {inner+outer:.2f} | B {b:.3f}')
# flushed, seq
for b in 'E','C','R3','A':
    f=lat(D[b]+'/cme-latency-dram-flushed.csv'); 
    print(b,'cme flushed best',best(f,8*M,'cme-best'), 'inner',round(pm(f,8*M,'cme-fresh','cme_l1d_refill_inner_per_load'),2),'outer',round(pm(f,8*M,'cme-fresh','cme_l1d_refill_outer_per_load'),2), 'dem', round(pm(f,8*M,'cme-fresh','cme_l1d_refill_rd_per_load'),2) if b!='R3' else '-', 'pf', round(pm(f,8*M,'cme-fresh','cme_l1d_refill_hwprf_per_load'),2) if b!='R3' else '-')
    cf=lat(D[b]+'/latency-dram-flushed.csv'); print(b,'core flushed best',best(cf,8*M,'best'))
    if b!='R3':
        q=lat(D[b]+'/cme-latency-dram-seq.csv'); print(b,'cme seq best',best(q,8*M,'cme-best'),'inner',round(pm(q,8*M,'cme-fresh','cme_l1d_refill_inner_per_load'),2),'outer',round(pm(q,8*M,'cme-fresh','cme_l1d_refill_outer_per_load'),2),'dem',round(pm(q,8*M,'cme-fresh','cme_l1d_refill_rd_per_load'),2),'pf',round(pm(q,8*M,'cme-fresh','cme_l1d_refill_hwprf_per_load'),2))
        cq=lat(D[b]+'/latency-dram-seq.csv'); print(b,'core seq best',best(cq,8*M,'best'))
# controls
for b in 'E','R3':
    rt=[];cc=[];cyc=[]
    for p in glob.glob(D[b]+'/cme-latency-*.csv'):
        for r in lat(p):
            if r['mode']=='cme-roundtrip': rt.append(r['ns']); cyc.append(float(r['cme_cycles_per_load']))
            if r['mode']=='cme-call': cc.append(r['ns'])
    print(b,'roundtrip',len(rt),min(rt),max(rt),'cycles',min(cyc),max(cyc),'| call',len(cc),min(cc),max(cc),sorted(cc)[-3:])
# clock E: cme_cycles/ns on 23 chase rows
rat=[]
for z in SM+LG:
    rows=E[z][1]; pre='cme-repeat' if z in SM else 'cme-fresh'
    for r in passes(rows,z,pre): rat.append(float(r['cme_cycles_per_load'])/r['ns'])
print('E cme cycles per ns on chase passes', min(rat), max(rat), len(rat))
rat=[]
for z in SM+LG:
    rows=R3[z][1]; pre='cme-repeat' if z in SM else 'cme-fresh'
    for r in passes(rows,z,pre): rat.append(float(r['cme_cycles_per_load'])/float(r['cycles_per_load']))
print('R3 cme cycles per core cycle', min(rat), max(rat))
# perf_cov count E, outer nonzero
n=0; nz=0; nd=0; nt=0; ncov=0
for p in glob.glob(D['E']+'/latency-*.csv')+glob.glob(D['E']+'/cme-latency-*.csv'):
    rows=lat(p)
    for r in rows:
        if 'perf_cov' in r and r['rep']!='-':
            n+=1
            if r['perf_cov']=='1.0000': ncov+=1
        if os.path.basename(p).startswith('cme-') and r['rep']!='-' and r['mode'] not in ('cme-roundtrip','cme-call') and 'perf_cov' in r:
            nt+=1
            if float(r['cme_l1d_refill_outer_per_load'])>0: nz+=1
            if float(r['cme_l1d_refill_rd_per_load'])>0: nd+=1
print('E counted latency rows',n,'cov=1',ncov,'| timed CME load reps',nt,'outer nonzero',nz,'demand nonzero',nd)

print('== 2.1 L3 hit set')
for b in 'E','C':
    h=lat(D[b]+'/latency-dram-small-l3.csv')
    for z in (192*K,256*K,384*K):
        p=passes(h,z,'repeat' if z<512*K else 'fresh')
        hits=[float(r['l3d_hit_rd_per_load']) for r in p]
        bz=best(h,z,'best')
        # best rep hit
        bp=min(p,key=lambda r:r['ns'])
        print(b,z//K,'KiB best',bz,'hits best-rep',bp['l3d_hit_rd_per_load'],'hits range',min(hits),max(hits))
print('== repeat check E vs R3 CME chase rows (same file+size)')
n=0;w1=w3=w5=0;mx=(0,None)
for z in SM+LG:
    e=E[z][0]; r=R3[z][0]; d=(e-r)/r*100; n+=1
    if abs(d)<=1: w1+=1
    if abs(d)<=3: w3+=1
    if abs(d)<=5: w5+=1
    if abs(d)>abs(mx[0]): mx=(d,z)
ef=best(lat(D['E']+'/cme-latency-dram-flushed.csv'),8*M,'cme-best'); rf=best(lat(D['R3']+'/cme-latency-dram-flushed.csv'),8*M,'cme-best'); d=(ef-rf)/rf*100; n+=1
if abs(d)<=1: w1+=1
if abs(d)<=3: w3+=1
if abs(d)<=5: w5+=1
print('rows',n,'within1',w1,'within3',w3,'within5',w5,'max',mx, 'flushed d',d)
# also with OCM rows? count 24 means 23 chase + flushed. ok.

print('== OCM table 4.2')
def ocm(b):
    out={}
    for i in range(5):
        c=lat(D[b]+f'/cme-latency-ocm-region{i}.csv'); z=256*K
        p=passes(c,z,'cme-fresh'); bst=best(c,z,'cme-best'); med=st.median([r['ns'] for r in p])
        inn=pm(c,z,'cme-fresh','cme_l1d_refill_inner_per_load'); out_=pm(c,z,'cme-fresh','cme_l1d_refill_outer_per_load')
        dem=pm(c,z,'cme-fresh','cme_l1d_refill_rd_per_load') if 'cme_l1d_refill_rd_per_load' in p[0] else None
        pf=pm(c,z,'cme-fresh','cme_l1d_refill_hwprf_per_load') if dem is not None else None
        row={'best':bst,'med':med,'inner':inn,'outer':out_,'dem':dem,'pf':pf,'passes':[r['ns'] for r in p]}
        if b!='R3':
            dn=lat(D[b]+f'/cme-latency-ocm-region{i}-dense.csv'); row['dense']=best(dn,z,'cme-best')
            vy=lat(D[b]+f'/cme-latency-ocm-region{i}-vary.csv'); row['vary']=best(vy,z,'cme-best')
            co=lat(D[b]+f'/latency-ocm-region{i}-cpu2.csv'); row['core']=best(co,z,'best'); row['core_l3']=pm(co,z,'fresh','l3d_refill_rd_per_load'); row['core_passes']=[r['ns'] for r in passes(co,z,'fresh')]
        else:
            co=lat(D[b]+f'/latency-ocm-region{i}-cpu2.csv'); row['core']=best(co,z,'best')
        out[i]=row
    a5=lat(D[b]+'/cme-latency-ocm-all5.csv'); z=5*256*K; p=passes(a5,z,'cme-fresh')
    out['a5']={'best':best(a5,z,'cme-best'),'med':st.median([r['ns'] for r in p]),'inner':pm(a5,z,'cme-fresh','cme_l1d_refill_inner_per_load'),'outer':pm(a5,z,'cme-fresh','cme_l1d_refill_outer_per_load'),'passes':[r['ns'] for r in p]}
    if b!='R3': out['a5']['dem']=pm(a5,z,'cme-fresh','cme_l1d_refill_rd_per_load'); out['a5']['pf']=pm(a5,z,'cme-fresh','cme_l1d_refill_hwprf_per_load')
    ca5=lat(D[b]+'/latency-ocm-all5-cpu2.csv'); out['a5']['core']=best(ca5,z,'best')
    if b!='R3': out['a5']['core_l3']=pm(ca5,z,'fresh','l3d_refill_rd_per_load')
    d5=lat(D[b]+'/cme-latency-ocm-all5-dense.csv'); p=passes(d5,z,'cme-fresh')
    out['d5']={'best':best(d5,z,'cme-best'),'med':st.median([r['ns'] for r in p]),'inner':pm(d5,z,'cme-fresh','cme_l1d_refill_inner_per_load'),'outer':pm(d5,z,'cme-fresh','cme_l1d_refill_outer_per_load')}
    if b!='R3': out['d5']['dem']=pm(d5,z,'cme-fresh','cme_l1d_refill_rd_per_load'); out['d5']['pf']=pm(d5,z,'cme-fresh','cme_l1d_refill_hwprf_per_load')
    cd5=lat(D[b]+'/latency-ocm-all5-dense-cpu2.csv'); out['d5']['core']=best(cd5,z,'best')
    if b!='R3': out['d5']['core_l3']=pm(cd5,z,'fresh','l3d_refill_rd_per_load')
    return out
OE=ocm('E'); OC=ocm('C'); O3=ocm('R3')
for k in list(range(5))+['a5','d5']:
    e=OE[k]; print(k,'core',e['core'],'coreL3',round(e.get('core_l3',0),2),'CME best',e['best'],'med',round(e['med'],2),'dense',e.get('dense'),'vary',e.get('vary'),'outer/dem/pf',round(e['outer'],2),round(e['dem'],2),round(e['pf'],2),'inner',round(e['inner'],3),'| R3',O3[k]['best'],'C',OC[k]['best'], '| E/R3',round(e['best']/O3[k]['best'],2))
    if k in range(5) or k=='a5':
        ps=e['passes']; print('   CME pass spread',round(max(ps)-min(ps),1),'median-best',round(e['med']-e['best'],1), 'core spread', round(max(e['core_passes'])-min(e['core_passes']),1) if 'core_passes' in e else '-')
print('E CME dense per-region', [OE[i]['dense'] for i in range(5)])
print('C sparse range',min(OC[i]['best'] for i in range(5)),max(OC[i]['best'] for i in range(5)),'C dense a5',OC['d5']['best'])
print('R3 sparse range',min(O3[i]['best'] for i in range(5)),max(O3[i]['best'] for i in range(5)),'R3 a5',O3['a5']['best'],'d5',O3['d5']['best'])
print('E CME-core sparse diffs',[round(OE[i]['best']-OE[i]['core'],2) for i in range(5)],'a5',round(OE['a5']['best']-OE['a5']['core'],2),'d5',round(OE['d5']['best']-OE['d5']['core'],2))
print('E dense-sparse CME',round(OE['d5']['best']-OE['a5']['best'],1),'core',round(OE['d5']['core']-OE['a5']['core'],1))
print('core sparse pass spread E',[round(max(OE[i]['core_passes'])-min(OE[i]['core_passes']),1) for i in range(5)])
print('== run 3 OCM bandwidth')
for i in range(5):
    c=bw(D['R3']+f'/cme-bandwidth-ocm-region{i}.csv'); k=bw(D['R3']+f'/bandwidth-ocm-region{i}.csv')
    cr=bwreps(c,'cme-read',256*K); kr=bwreps(k,'read',256*K)
    print(i,'CME read',bwbest(c,'cme-read',256*K),'core read',bwbest(k,'read',256*K),'ratio',round(bwbest(c,'cme-read',256*K)/bwbest(k,'read',256*K),2),'spread CME %',round((max(cr)-min(cr))/min(cr)*100,1),'core %',round((max(kr)-min(kr))/min(kr)*100,1))
c=bw(D['R3']+'/cme-bandwidth-ocm-all5.csv'); k=bw(D['R3']+'/bandwidth-ocm-all5.csv'); print('all5 read CME',bwbest(c,'cme-read',5*256*K),'core',bwbest(k,'read',5*256*K), 'spread',bwreps(c,'cme-read',5*256*K))
c=bw(D['R3']+'/cme-bandwidth-ocm-write.csv'); k=bw(D['R3']+'/bandwidth-ocm-write.csv'); print('all5 write CME',bwbest(c,'cme-write',5*256*K),'core',bwbest(k,'write',5*256*K))
print('== run 3 one-core bandwidth')
c=bw(D['R3']+'/cme-bandwidth-dram-1core.csv'); k=bw(D['R3']+'/bandwidth-dram-1core.csv')
print('CME kernels',sorted(set(r['kernel'] for r in c)),'sizes',sorted(set(r['bytes'] for r in c)))
print('core kernels',sorted(set(r['kernel'] for r in k)),'sizes',sorted(set(r['bytes'] for r in k)))
for z in sorted(set(r['bytes'] for r in c)):
    print(z//K,'K: core r/w/c',bwbest(k,'read',z),bwbest(k,'write',z),bwbest(k,'copy',z),'| CME r/w/c',bwbest(c,'cme-read',z),bwbest(c,'cme-write',z),bwbest(c,'cme-copy',z),'| ldr16',bwbest(c,'cme-ldr16',z),'str16',bwbest(c,'cme-str16',z))
rd=[bwbest(c,'cme-read',z) for z in (160*K,256*K,M,2*M,32*M)]; wr=[bwbest(c,'cme-write',z) for z in (160*K,256*K,M,2*M,32*M)]
print('reads 160K-32M',min(rd),max(rd),'writes',min(wr),max(wr))
wr_all=[bwbest(c,'cme-write',z) for z in sorted(set(r['bytes'] for r in c))]; print('writes all',min(wr_all),max(wr_all))
print('read fall 48->96',round((1-bwbest(c,'cme-read',96*K)/bwbest(c,'cme-read',48*K))*100,0),'96->160',round((1-bwbest(c,'cme-read',160*K)/bwbest(c,'cme-read',96*K))*100,0))
print('R3 chase 1M->32M rise',round((R3[32*M][0]/R3[M][0]-1)*100,0))
print('ratio CME/core 32M read',round(bwbest(c,'cme-read',32*M)/bwbest(k,'read',32*M),2),'write',round(bwbest(c,'cme-write',32*M)/bwbest(k,'write',32*M),2))
print('CME OCM read / warm DRAM (2M?)',round(23.178/bwbest(c,'cme-read',2*M),2), round(23.178/bwbest(c,'cme-read',32*M),2),'core',round(16.219/bwbest(k,'read',2*M),2),round(16.219/bwbest(k,'read',32*M),2))
cc=bw(D['R3']+'/cme-bandwidth-call-cost.csv'); 
for kn in ('cme-read','cme-write'):
    g=bwbest(cc,kn,1024); print(kn,'call cost ns/call',round(1024/g,1))
print('16K read pass ns',round(16384/bwbest(c,'cme-read',16*K),0),'call share',round(1024/bwbest(cc,'cme-read',1024)/(16384/bwbest(c,'cme-read',16*K))*100,0))
w23=bw(D['R3']+'/bandwidth-write-cpus2-3.csv'); print('cpus2-3 write',bwbest(w23,'write',16*M),'ratio',round(bwbest(c,'cme-write',32*M)/bwbest(w23,'write',16*M),2))
print('E core read 2M',bwbest(bw(D['E']+'/bandwidth-read-prefetch.csv'),'read',2*M),'R3 2M',bwbest(k,'read',2*M))
print('== cmn counts run 3')
cm={}
for r in csv.DictReader(open(D['R3']+'/cmn-counts.csv')):
    cm.setdefault(r['label'],{})[(r['event'],r['nodeid'])]=int(r['count']) if (r['count'] or '').isdigit() else r['count']
nodes=['88','160','216','288','344']
for i in range(5):
    for kind,cl,kl in (('sparse',f'cme-ocm-region{i}-cpu2',f'ocm-region{i}-cpu2'),('read',f'cme-ocm-read-region{i}',f'ocm-read-region{i}')):
        own=nodes[i]; a=cm[cl][('hns_pocq_reqs_recvd_all',own)]; b=cm[kl][('hns_pocq_reqs_recvd_all',own)]
        oth=[cm[cl][('hns_pocq_reqs_recvd_all',n)] for n in nodes if n!=own]
        print(i,kind,a,b,round(a/b,2),round(sum(oth)/4))
fl=[cm['cme-dram-flushed-8M-cpu2'][('hns_pocq_reqs_recvd_all',n)] for n in nodes]; print('flushed',min(fl),max(fl),sum(fl),'spread %',round((max(fl)-min(fl))/min(fl)*100,1))

print('== automated table compare against page text')
txt=open('/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/check-cme/page.txt').read().split('\n')
def row(prefix):
    for l in txt:
        if l.startswith(prefix): return [c.strip() for c in l.split('|')]
nchk=0; bad=[]
def cmp(label,page,calc,fmt):
    global nchk
    nchk+=1
    want=fmt%calc if calc is not None else '-'
    if page!=want: bad.append((label,page,want))
names={4*K:'4 KiB',8*K:'8 KiB',16*K:'16 KiB',24*K:'24 KiB',32*K:'32 KiB',48*K:'48 KiB',64*K:'64 KiB',96*K:'96 KiB',128*K:'128 KiB',192*K:'192 KiB',256*K:'256 KiB',384*K:'384 KiB',512*K:'512 KiB',768*K:'768 KiB',M:'1 MiB',int(1.5*M):'1.5 MiB',2*M:'2 MiB',3*M:'3 MiB',4*M:'4 MiB',6*M:'6 MiB',8*M:'8 MiB',16*M:'16 MiB',32*M:'32 MiB'}
for z in SM+LG:
    r=row(names[z]+' | '+('repeat' if z in SM else 'fresh'))
    e=E[z][0]; rows=E[z][1]; pre='cme-repeat' if z in SM else 'cme-fresh'
    vals=[coreE[z],e,e-coreE[z],R3[z][0],C[z][0],e/C[z][0],pm(rows,z,pre,'cme_l1d_refill_inner_per_load'),pm(rows,z,pre,'cme_l1d_refill_outer_per_load'),pm(rows,z,pre,'cme_l1d_refill_rd_per_load'),pm(rows,z,pre,'cme_l1d_refill_hwprf_per_load')]
    fm=['%.3f','%.3f','%.1f','%.3f','%.3f','%.3f','%.2f','%.2f','%.2f','%.2f']
    for i,(v,f) in enumerate(zip(vals,fm)): cmp(f'4.1 {names[z]} col{i+2}',r[2+i],v,f)
# flushed and seq rows
fE=lat(D['E']+'/cme-latency-dram-flushed.csv'); fC=lat(D['C']+'/cme-latency-dram-flushed.csv'); f3=lat(D['R3']+'/cme-latency-dram-flushed.csv'); cf=lat(D['E']+'/latency-dram-flushed.csv')
r=row('8 MiB | flushed'); e=best(fE,8*M,'cme-best')
vals=[best(cf,8*M,'best'),e,e-best(cf,8*M,'best'),best(f3,8*M,'cme-best'),best(fC,8*M,'cme-best'),e/best(fC,8*M,'cme-best'),pm(fE,8*M,'cme-fresh','cme_l1d_refill_inner_per_load'),pm(fE,8*M,'cme-fresh','cme_l1d_refill_outer_per_load'),pm(fE,8*M,'cme-fresh','cme_l1d_refill_rd_per_load'),pm(fE,8*M,'cme-fresh','cme_l1d_refill_hwprf_per_load')]
for i,(v,f) in enumerate(zip(vals,fm)): cmp(f'4.1 flushed col{i+2}',r[2+i],v,f)
qE=lat(D['E']+'/cme-latency-dram-seq.csv'); qC=lat(D['C']+'/cme-latency-dram-seq.csv'); cq=lat(D['E']+'/latency-dram-seq.csv')
r=row('8 MiB | seq'); e=best(qE,8*M,'cme-best')
vals=[best(cq,8*M,'best'),e,e-best(cq,8*M,'best'),None,best(qC,8*M,'cme-best'),e/best(qC,8*M,'cme-best'),pm(qE,8*M,'cme-fresh','cme_l1d_refill_inner_per_load'),pm(qE,8*M,'cme-fresh','cme_l1d_refill_outer_per_load'),pm(qE,8*M,'cme-fresh','cme_l1d_refill_rd_per_load'),pm(qE,8*M,'cme-fresh','cme_l1d_refill_hwprf_per_load')]
for i,(v,f) in enumerate(zip(vals,fm)): cmp(f'4.1 seq col{i+2}',r[2+i],v,f)
# 4.2
nodes=['88','160','216','288','344']
for i in range(5):
    r=row(f'OCM{i} (node {nodes[i]})'); e=OE[i]
    c=bw(D['R3']+f'/cme-bandwidth-ocm-region{i}.csv'); k=bw(D['R3']+f'/bandwidth-ocm-region{i}.csv')
    vals=[e['core'],e['core_l3'],e['best'],e['med'],e['dense'],e['vary']]; fm2=['%.3f','%.2f','%.3f','%.2f','%.3f','%.3f']
    for j,(v,f) in enumerate(zip(vals,fm2)): cmp(f'4.2 OCM{i} col{j+2}',r[2+j],v,f)
    cmp(f'4.2 OCM{i} refills',r[8],(e['outer'],e['dem'],e['pf']),'%.2f / %.2f / %.2f')
    cmp(f'4.2 OCM{i} run3',r[9],O3[i]['best'],'%.3f'); cmp(f'4.2 OCM{i} C',r[10],OC[i]['best'],'%.3f')
    cmp(f'4.2 OCM{i} CME bw',r[11],bwbest(c,'cme-read',256*K),'%.1f'); cmp(f'4.2 OCM{i} core bw',r[12],bwbest(k,'read',256*K),'%.1f')
r=row('All five, sparse'); e=OE['a5']
c=bw(D['R3']+'/cme-bandwidth-ocm-all5.csv'); k=bw(D['R3']+'/bandwidth-ocm-all5.csv')
cmp('4.2 a5 core',r[2],e['core'],'%.3f'); cmp('4.2 a5 coreL3',r[3],e['core_l3'],'%.2f'); cmp('4.2 a5 best',r[4],e['best'],'%.3f'); cmp('4.2 a5 med',r[5],e['med'],'%.2f')
cmp('4.2 a5 refills',r[8],(e['outer'],e['dem'],e['pf']),'%.2f / %.2f / %.2f'); cmp('4.2 a5 run3',r[9],O3['a5']['best'],'%.3f'); cmp('4.2 a5 C',r[10],OC['a5']['best'],'%.3f')
cmp('4.2 a5 CME bw',r[11],bwbest(c,'cme-read',5*256*K),'%.1f'); cmp('4.2 a5 core bw',r[12],bwbest(k,'read',5*256*K),'%.1f')
r=row('All five, dense'); e=OE['d5']
cmp('4.2 d5 core',r[2],e['core'],'%.3f'); cmp('4.2 d5 coreL3',r[3],e['core_l3'],'%.2f'); cmp('4.2 d5 best',r[4],e['best'],'%.3f'); cmp('4.2 d5 med',r[5],e['med'],'%.2f')
cmp('4.2 d5 refills',r[8],(e['outer'],e['dem'],e['pf']),'%.2f / %.2f / %.2f'); cmp('4.2 d5 run3',r[9],O3['d5']['best'],'%.3f'); cmp('4.2 d5 C',r[10],OC['d5']['best'],'%.3f')
r=row('Streaming write, all five'); c=bw(D['R3']+'/cme-bandwidth-ocm-write.csv'); k=bw(D['R3']+'/bandwidth-ocm-write.csv')
cmp('4.2 write CME',r[11],bwbest(c,'cme-write',5*256*K),'%.1f'); cmp('4.2 write core',r[12],bwbest(k,'write',5*256*K),'%.1f')
# 4.3 / 4.4
c=bw(D['R3']+'/cme-bandwidth-dram-1core.csv'); k=bw(D['R3']+'/bandwidth-dram-1core.csv')
for z,nm in ((16*K,'16 KiB'),(48*K,'48 KiB'),(96*K,'96 KiB'),(160*K,'160 KiB'),(256*K,'256 KiB'),(M,'1 MiB'),(2*M,'2 MiB'),(32*M,'32 MiB')):
    r=[l for l in txt if l.startswith(nm+' | ') and l.count('|')==8]
    r=[x.strip() for x in r[0].split('|')]
    vals=[bwbest(k,'read',z),bwbest(c,'cme-read',z),bwbest(k,'write',z),bwbest(c,'cme-write',z),bwbest(k,'copy',z),bwbest(c,'cme-copy',z)]
    for j,v in enumerate(vals): cmp(f'4.3 {nm} col{j+2}',r[1+j],v,'%.1f')
for z,nm in ((16*K,'16 KiB'),(2*M,'2 MiB'),(32*M,'32 MiB')):
    r=[l for l in txt if l.startswith(nm+' | ') and l.count('|')==7 and ('1.00' in l or '0.83' in l)]
    r=[x.strip() for x in r[0].split('|')]
    rd=bwbest(c,'cme-read',z); l16=bwbest(c,'cme-ldr16',z); wr=bwbest(c,'cme-write',z); s16=bwbest(c,'cme-str16',z)
    for j,(v,f) in enumerate(zip([rd,l16,l16/rd,wr,s16,s16/wr],['%.1f','%.1f','%.3f','%.1f','%.1f','%.3f'])): cmp(f'4.4 {nm} col{j+2}',r[1+j],v,f)
# 4.6
for i in range(5):
    for kind,cl,kl,nm in (('sparse',f'cme-ocm-region{i}-cpu2',f'ocm-region{i}-cpu2',f'OCM{i} sparse chase'),('read',f'cme-ocm-read-region{i}',f'ocm-read-region{i}',f'OCM{i} read')):
        r=row(nm+' |'); own=nodes[i]; a=cm[cl][('hns_pocq_reqs_recvd_all',own)]; b=cm[kl][('hns_pocq_reqs_recvd_all',own)]
        oth=[cm[cl][('hns_pocq_reqs_recvd_all',n)] for n in nodes if n!=own]
        cmp(f'4.6 {nm} a',r[1],'{:,}'.format(a),'%s'); cmp(f'4.6 {nm} b',r[2],'{:,}'.format(b),'%s'); cmp(f'4.6 {nm} ratio',r[3],a/b,'%.2f'); cmp(f'4.6 {nm} oth',r[4],'{:,}'.format(round(sum(oth)/4)),'%s')
print('table cells checked',nchk,'mismatches',len(bad))
for b_ in bad: print('  MISMATCH',b_)
