exec(open('chk.py').read().split('# ---------- Short version ----------')[0])
import statistics as st
# L1 refills max over best reps only, and which rows exceed 0.0121
mx=0; over=[]
for bt in ('C','E'):
    for nm in ('bandwidth-l1-passes','bandwidth-l1-asmpasses'):
        for kn in ('read','write'):
            for s in (4,8,16,24):
                rr=bwrows(bt,nm,kn,s*KB); b=max(rr,key=lambda r:r['aggregate_GBps'])
                mx=max(mx,b['l1d_refill_per_line'])
                for r in rr:
                    if r['l1d_refill_per_line']>0.0121: over.append((bt,nm,kn,s,r['rep'],r['l1d_refill_per_line']))
print('max L1 refill best reps', mx); print('reps over 0.0121', over)
# sec10 others ratio variant: mean of others R3 / mean of others R2
c3=cmn('R3'); c2=cmn('R2')
def reqs(cm,label): return {int(r['nodeid']):int(r['count']) for r in cm[label] if r['event']=='hns_pocq_reqs_recvd_all'}
node={0:88,1:160,2:216,3:288,4:344}
v=[]
for c in (2,4,6,8):
    for r in range(5):
        q3=reqs(c3,f'ocm-region{r}-cpu{c}'); q2=reqs(c2,f'ocm-region{r}-cpu{c}'); own=node[r]
        v.append(st.mean(x for k,x in q3.items() if k!=own)/st.mean(x for k,x in q2.items() if k!=own))
print('others mean ratio', round(min(v),3), round(max(v),3))
# control helper times
def ev(cm,label,e): return int([r for r in cm[label] if r['event']==e][0]['count'])
for cm,nm in ((c3,'R3'),(c2,'R2')):
    print(nm,'helper diff', ev(cm,'control-cpu2','helper_elapsed_ns')-ev(cm,'control-nocount-cpu2','helper_elapsed_ns'), 'child diff', ev(cm,'control-cpu2','child_elapsed_ns')-ev(cm,'control-nocount-cpu2','child_elapsed_ns'))
# sec 8 figure first/last deltas (R3-R2 GB/s)
print('pair write 16K', bwbest('R3','bandwidth-pair','write',16*KB)-bwbest('R2','bandwidth-pair','write',16*KB))
print('writers 2468', bwbest('R3','bandwidth-write-cpus2-4-6-8','write',16*MB)-bwbest('R2','bandwidth-write-cpus2-4-6-8','write',16*MB))
print('all8 write 16M', bwbest('R3','bandwidth-all8','write',16*MB)-bwbest('R2','bandwidth-all8','write',16*MB))
# D walk pass means
for bt in ('D','E'):
    for nm in ('latency-dram-tlb-cpu2','latency-dram-walk-cpu2'):
        print(bt,nm,'walk pass mean',round(pmean(bt,nm,32*MB,'dtlb_walk_per_load'),4),'best',bestrow(bt,nm,32*MB)['dtlb_walk_per_load'])
