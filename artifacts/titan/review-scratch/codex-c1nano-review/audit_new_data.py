#!/usr/bin/env python3
"""Compare page data exports with independent CSV parsing and NumPy fits."""
import csv
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import re
import statistics
import sys
import numpy as np

ROOT = Path('/home/jhan/workspace/titan/cache-perf/asimov')
OUT = Path('/tmp/codex-c1nano-review')
source = ROOT / 'c1nano_page/data.py'
source_bytes = source.read_bytes()
sha = hashlib.sha256(source_bytes).hexdigest()
(OUT / ('data-' + sha[:12] + '.py')).write_bytes(source_bytes)
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from c1nano_page import data
D = data.load()
checks = 0
errors = []

def eq(label, got, want, tol=1e-9):
    global checks
    checks += 1
    if isinstance(got, (int, float, np.number)) and isinstance(want, (int, float, np.number)):
        good = math.isclose(float(got), float(want), rel_tol=tol, abs_tol=tol)
    else:
        good = got == want
    if not good:
        errors.append({'label': label, 'got': got, 'want': want})

def parse(path):
    out, columns, meta, block = [], None, {}, -1
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line:
            continue
        if line.startswith('#'):
            if line.startswith(('# latency:', '# bandwidth:')):
                block += 1
                meta = dict(re.findall(r'(\w+)=(\S+)', line))
            continue
        vals = next(csv.reader([line]))
        if vals[0] in ('mem', 'label'):
            columns = vals
            continue
        row = dict(zip(columns, vals))
        row.update(_line=n, _block=block, _meta=meta.copy())
        out.append(row)
    return out

raw = {}
lat, bw = {}, {}
raw_by_line = {}
short = {'ns_per_load': 'ns', 'cycles_per_load': 'cycles', 'cycles_per_line': 'cyc_line',
         'l1d_refill': 'l1', 'l2d_refill': 'l2', 'l3d_refill_rd': 'a2',
         'l1d_refill_hwprf': 'l1pf', 'l2d_refill_hwprf': 'l2pf',
         'l2d_refill_l1dhwprf': 'l2byl1pf', 'l2d_hit_rd': 'l2hit',
         'l3d_access_rd': 'l3acc', 'l3d_hit_rd': 'l3hit', 'l1d_tlb_refill': 'l1tlb',
         'l2d_tlb_refill': 'l2tlb', 'dtlb_walk': 'walk', 'dtlb_walk_block': 'walk_block',
         'dtlb_walk_page': 'walk_page', 'perf_cov': 'perf_cov'}

for boot in data.BOOTS:
    folder = Path(data.BOOTDIR[boot])
    for path in sorted(folder.glob('*.csv')):
        if not path.name.startswith(('latency-', 'bandwidth-')):
            continue
        rr = parse(path)
        raw[(boot,path.name)] = rr
        for r in rr:
            raw_by_line[(boot,path.name,r['_line'])] = r
        groups = {}
        islat = path.name.startswith('latency-')
        for r in rr:
            key = (r['_block'],int(r['size_bytes'])) if islat else (r['_block'],r['kernel'],int(r['bytes_per_thread']))
            groups.setdefault(key,[]).append(r)
        for key, reps in groups.items():
            best = next(r for r in reps if r.get('mode') == 'best' or r.get('rep') == 'best')
            timed = [r for r in reps if r is not best]
            field = 'ns_per_load' if islat else 'aggregate_GBps'
            vals = [float(r[field]) for r in timed]
            val = float(best[field])
            chosen = next(r for r in timed if float(r[field]) == val)
            if islat:
                r = D.latrow(boot,path.name,size=key[1],block=key[0])
                lat[(boot,path.name,*key)] = {'best':val,'timed':timed,'chosen':chosen,'row':r}
                eq(f'{boot}/{path.name}:{key}/median',r['median'],statistics.median(vals))
                eq(f'{boot}/{path.name}:{key}/min',val,min(vals))
            else:
                r = next(r for r in D.bw(boot,path.name) if (r['block'],r['kernel'],r['size']) == key)
                bw[(boot,path.name,*key)] = {'best':val,'timed':timed,'chosen':chosen,'row':r}
                eq(f'{boot}/{path.name}:{key}/max',val,max(vals))
                total=int(chosen['total_bytes'])
                passes=int(chosen['_meta']['passes'])
                threads=int(chosen['threads'])
                for attr,want in {'ns_rep':total/val,'ns_pass':total/val/passes,'per_thread':val/threads,
                                  'ns_per_64':64*threads/val,'bytes_per_cycle':val/threads/2,
                                  'eff_cycles_64':128*threads/val,'thr_min':float(chosen['per_thread_min_GBps']),
                                  'thr_max':float(chosen['per_thread_max_GBps'])}.items():
                    eq(f'{boot}/{path.name}:{key}/{attr}',r[attr],want)
            stem=f'{boot}/{path.name}:{key}'
            eq(stem+'/best',r['best'],val)
            eq(stem+'/line',r['line'],chosen['_line'])
            eq(stem+'/best_line',r['best_line'],best['_line'])
            eq(stem+'/n_reps',r['n_reps'],len(timed))
            eq(stem+'/spread',r['spread_pct'],100*(max(vals)-min(vals))/val)
            eq(stem+'/reps',r['reps'],vals)
            for col,rv in chosen.items():
                base=re.sub(r'_per_(?:load|line)$','',col)
                sk=short.get(col,short.get(base))
                if sk and sk in r:
                    want=None if rv=='-' else float(rv)
                    eq(stem+'/'+sk,r[sk],want)
                    if sk+'_reps' in r:
                        eq(stem+'/'+sk+'_reps',r[sk+'_reps'],[None if q[col]=='-' else float(q[col]) for q in timed])

# Every paired row must cite the appropriate source value and matching command shape.
for table, leftname, rightname, prefix, rightboot in [
    ('repeat','f1','e','e_','E'),('open_l3','f1','r3','r3_','R3'),
    ('open_ec','e','c','c_','C')]:
    for r in getattr(D,table):
        if r['file']=='cmn-counts.csv':
            continue
        a=raw_by_line[(r['boot'],r['file'],r['line'])]
        b=raw_by_line[(rightboot,r[prefix+'file'],r[prefix+'line'])]
        field='ns_per_load' if 'ns_per_load' in a else 'aggregate_GBps'
        per=r.get('threads',1)
        eq(table+'/'+r['id']+'/left',r[leftname],float(a[field])/per)
        eq(table+'/'+r['id']+'/right',r[rightname],float(b[field])/per)
        sizefield='size_bytes' if field=='ns_per_load' else 'bytes_per_thread'
        eq(table+'/'+r['id']+'/pair-size',a[sizefield],b[sizefield])
        eq(table+'/'+r['id']+'/pair-mode',re.sub(r'\d+$','',a.get('mode','')),re.sub(r'\d+$','',b.get('mode','')))
        eq(table+'/'+r['id']+'/pair-kernel',a.get('kernel'),b.get('kernel'))
        eq(table+'/'+r['id']+'/pair-threads',a.get('threads'),b.get('threads'))
        eq(table+'/'+r['id']+'/pair-flush',a['_meta'].get('flush',a['_meta'].get('flush_before')),b['_meta'].get('flush',b['_meta'].get('flush_before')))

# Fit independent times, normalized before NumPy least squares.
fits=[]
for f in D.bw_fit+D.bw_fit_extra:
    pp=[raw_by_line[(f['boot'],f['file'],ln)] for ln in f['lines']]
    sizes=np.array([float(r['bytes_per_thread']) for r in pp])
    ns=np.array([int(r['total_bytes'])/float(r['aggregate_GBps'])/int(r['_meta']['passes']) for r in pp])
    scale=max(sizes)
    coef=np.linalg.lstsq(np.column_stack([np.ones(len(sizes)),sizes/scale]),ns,rcond=None)[0]
    pred=coef[0]+coef[1]*sizes/scale
    resid=ns-pred
    rate=scale/coef[1]
    label=f"fit/{f['boot']}/{f['form']}/{f['kernel']}"
    for key,want in {'intercept_ns':coef[0],'rate':rate,'max_res':max(abs(resid)),'max_res_pct':max(abs(resid))/min(ns)*100,'valid':bool(max(abs(resid))<=min(ns)*.02)}.items():
        eq(label+'/'+key,f[key],want)
    fits.append({'fit':label,'intercept_ns':float(coef[0]),'rate_GBps':float(rate),'max_res_pct':float(max(abs(resid))/min(ns)*100),'valid':f['valid']})

# Refit the route map from all raw best values.
ports={2:(2,3),4:(3,2),6:(4,3),8:(5,2)}
nodes=[(1,3),(2,4),(3,3),(4,4),(5,3)]
route_fits=[]
for boot in ('B','D','E','F1'):
    matrix=[]; vals=[]
    for cpu,reg in itertools.product((2,4,6,8),range(5)):
        fn=f'latency-ocm-region{reg}-'+('' if boot=='F1' else 'route-')+f'cpu{cpu}.csv'
        rr=lat[(boot,fn,0,262144)]
        matrix.append([1,abs(ports[cpu][0]-nodes[reg][0]),abs(ports[cpu][1]-nodes[reg][1])])
        vals.append(rr['best'])
    matrix=np.array(matrix); vals=np.array(vals)
    coef=np.linalg.lstsq(matrix,vals,rcond=None)[0]
    resid=vals-matrix@coef
    f=D.ocm_fit[boot]
    for key,want in dict(a=coef[0],bx=coef[1],cy=coef[2],rms=np.sqrt(np.mean(resid**2)),max_res=max(abs(resid)),valid=bool(max(abs(resid))<=min(vals)*.02)).items():
        eq('route/'+boot+'/'+key,f[key],want)
    route_fits.append({'boot':boot,'coef_ns':coef.tolist(),'rms_ns':float(np.sqrt(np.mean(resid**2))),'max_res_pct':float(max(abs(resid))/min(vals)*100),'valid':f['valid']})

# Recompute the L3 mixtures directly from each rep, including L1 hits.
getlat=lambda b,fn,size:lat[(b,fn,0,size)]
t1=getlat('E','latency-dram-small.csv',4096)['best']
tout=getlat('E','latency-dram-large.csv',2097152)['best']
rr=getlat('E','latency-dram-small-l3.csv',98304)['timed']
t2=min((float(r['ns_per_load'])-(1-float(r['l1d_refill_per_load']))*t1)/float(r['l1d_refill_per_load']) for r in rr)
l3=[]
for f in D.l3_est:
    rr=getlat('E','latency-dram-small-l3.csv',f['size'])['timed']
    est=[(float(r['ns_per_load'])-(1-float(r['l1d_refill_per_load']))*t1-float(r['l2d_hit_rd_per_load'])*t2-float(r['l3d_refill_rd_per_load'])*tout)/float(r['l3d_hit_rd_per_load']) for r in rr]
    for i,want in enumerate(est):eq('L3/'+str(f['size'])+'/'+str(i),f['est'][i],want)
    l3.append({'size':f['size'],'est_ns':est,'majority_l3':f['majority_l3']})

endsha=hashlib.sha256(source.read_bytes()).hexdigest()
eq('source stable during audit',endsha,sha)
result={'source_sha256':sha,'api_sha256':hashlib.sha256((ROOT/'c1nano_page/API.md').read_bytes()).hexdigest(),'checks':checks,'latency_rows':len(lat),'bandwidth_rows':len(bw),'errors':errors,'bandwidth_fits':fits,'route_fits':route_fits,'l3_estimates':l3}
output=OUT/('new-data-audit-'+sha[:12]+'.json')
output.write_text(json.dumps(result,indent=2))
print(json.dumps({'file':str(output),'source_sha256':sha,'checks':checks,'latency_rows':len(lat),'bandwidth_rows':len(bw),'errors':errors},indent=2))
