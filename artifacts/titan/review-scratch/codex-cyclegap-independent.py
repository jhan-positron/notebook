from pathlib import Path
from statistics import median
import csv,json
root=Path('/home/jhan/workspace/titan/cache-perf/asimov/results')
groups={}
for boot,run in [('F1','011'),('F2','012')]:
 for p in sorted((root/f'membench-jibin-{run}/results/boot{boot}').glob('cme-latency-*.csv')):
  cols=[]
  for n,l in enumerate(p.read_text().splitlines(),1):
   if l.startswith('mem,'):cols=l.split(',');continue
   if not l or l.startswith('#'):continue
   a=dict(zip(cols,next(csv.reader([l]))))
   if a['mode']=='cme-call': key='cme-call'
   elif p.name.startswith('cme-latency-ocm-') and a['mode'].startswith('cme-fresh') and a['loads'] in ['64','320']:key='ocm-'+a['loads']
   else:continue
   L=int(a['loads']);W=float(a['cycles_per_load'])*L/2;C=float(a['cme_cycles_per_load'])*L/2;B=float(a['ns_per_load'])*L;S=float(a['ns_per_load_span'])*L
   groups.setdefault((boot,key),[]).append(dict(path=str(p),line=n,W=W,C=C,B=B,S=S,gap=W-C,gapcyc=2*(W-C),wb=W-B,bc=B-C,cs=C-S))
for (boot,key),rr in groups.items():
 print(boot,key,'n',len(rr),'gap_cycles',min(x['gapcyc'] for x in rr),max(x['gapcyc'] for x in rr))
 print({k:median(x[k] for x in rr) for k in ['W','C','B','S','gap','gapcyc','wb','bc','cs']})
 if boot=='F1' and key=='ocm-64':
  for k in ['W','C','B','S','gap','wb','bc','cs']:
   ss=sorted(rr,key=lambda x:x[k]);x=ss[len(ss)//2];print(k,x[k],x['path'],x['line'])
