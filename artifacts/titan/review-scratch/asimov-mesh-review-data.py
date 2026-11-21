import csv, collections, hashlib, json, re, statistics
from pathlib import Path
import numpy as np
from bs4 import BeautifulSoup

root=Path('/home/jhan/workspace/titan/cache-perf/asimov')
soup=BeautifulSoup((root/'asimov-mesh-map.html').read_text(),'html.parser')
data={}
for boot in (1,2,3):
    path=root/f'results/membench-jibin-0{13+boot}/results/bootM{boot}/latency-map.csv'
    rows=list(csv.DictReader(l for l in path.read_text().splitlines() if l and not l.startswith('#')))
    assert len(rows)==1269
    groups=collections.defaultdict(list)
    for row in rows:
        if row['kind']!='idle': groups[(row['kind'],int(row['cpu']),int(row['node']))].append(row)
    assert len(groups)==180 and all(len(v)==7 for v in groups.values())
    data[boot]=groups

nodes={88:(1,3),160:(2,4),216:(3,3),288:(4,4),344:(5,3)}
cpus={2:(2,3),3:(2,3),4:(3,2),5:(3,2),6:(4,3),7:(4,3),8:(5,2),9:(5,2)}
cells=[(c,n) for c in cpus for n in nodes]
def vals(b,k,c,n,col='ns_per_load'):
    return [float(r[col]) for r in data[b][k,c,n]]
def best(b,k,c,n): return min(vals(b,k,c,n))
def steps(c,n): return [abs(cpus[c][i]-nodes[n][i]) for i in range(2)]
def fit(a,y):
    a=np.array(a,float);y=np.array(y,float)
    co=np.linalg.lstsq(a,y,rcond=None)[0];e=y-a@co
    return [*co,np.sqrt(np.mean(e**2)),max(abs(e))]

tables=soup.find_all('table')
for row in tables[2].select('tbody tr'):
    t=[x.get_text(' ',strip=True) for x in row.find_all('td')]
    c=int(re.search(r'CPUs (\d+)',t[0])[1]);n=int(t[1].split()[0]);dx,dy=steps(c,n)
    assert t[2:6]==[str(dx),str(dy),str(2*dx+dy),f'{20.6+2*dx+dy:.2f}'],t
    for col,k in zip(t[6:],['ocm-evict','slc','dram-flush']):
        assert col==f'{best(1,k,c,n):.2f} / {best(1,k,c+1,n):.2f}',t
for row in tables[3].select('tbody tr'):
    t=[x.get_text(' ',strip=True) for x in row.find_all('td')]
    b=int(t[0][-1]);k=t[1]
    result=fit([[1,*steps(c,n)] for c,n in cells],[best(b,k,c,n) for c,n in cells])
    assert t[2:]==[f'{v:.2f}' for v in result],(t,result)
for row in tables[6].select('tbody tr'):
    t=[x.get_text(' ',strip=True) for x in row.find_all('td')]
    b=int(t[0][-1]);c=int(t[1].split()[1]);n=int(t[2].split()[1]);reg=list(nodes).index(n)
    p=root/f'results/membench-jibin-0{13+b}/results/bootM{b}/latency-ocm-region{reg}-mapctl-cpu{c}.csv'
    control=float(next(l for l in p.read_text().splitlines() if ',best,' in l).split(',')[5])
    v=best(b,'ocm-flush',c,n)
    assert t[3:]==[f'{control:.3f}',f'{v:.3f}',f'{v-control:+.3f}'],t
for row in tables[7].select('tbody tr'):
    t=[x.get_text(' ',strip=True) for x in row.find_all('td')]
    b=int(t[0][-1]);k=t[1]
    for text,col in zip(t[2:4],['l3d_refill_rd','l2d_refill_hwprf']):
        v=[v for c,n in cells for v in vals(b,k,c,n,col)]
        assert text==' / '.join(f'{v:.2f}' for v in [min(v),statistics.median(v),max(v)]),(t,col)
    if k=='ocm-flush': assert t[4]=='-'
    else:
        v=[statistics.median(vals(b,k,c,n,'mc_reqs')) for c,n in cells]
        assert t[4]==f'{min(v):.4f} to {max(v):.4f}',t

checked_titles=0
for title in soup.select('svg title'):
    text=title.get_text()
    m=re.search(r'(?:(?:boot (\d), )?)(ocm-flush|ocm-evict|slc|dram-flush), CPU (\d+) to node (\d+): best ([\d.]+) ns, median ([\d.]+) ns',text)
    if m:
        b,k,c,n,v,med=m.groups();b=int(b or 1);c=int(c);n=int(n)
        assert v==f'{best(b,k,c,n):.2f}' and med==f'{statistics.median(vals(b,k,c,n)):.2f}',text
        checked_titles+=1
    m=re.search(r'boot (\d),.*\((ocm-evict|ocm-flush|slc)\), CPU (\d+) to node (\d+) \((\d+) units\): ([\d.]+) ns',text)
    if m:
        b,k,c,n,u,v=m.groups();b=int(b);c=int(c);n=int(n);dx,dy=steps(c,n)
        assert u==str(2*dx+dy) and v==f'{best(b,k,c,n):.2f}',text
        checked_titles+=1
assert checked_titles==660,checked_titles
hash_results=[]
for b in (1,2,3):
    p=root/f'results/membench-jibin-0{13+b}/results/bootM{b}/map-homes.txt'
    lines=p.read_text().splitlines();base=int(re.search(r'pfn=(0x[0-9a-f]+)',lines[0])[1],16)<<12
    sequence=''.join(l for l in lines if not l.startswith('#'))
    assert len(sequence)==10255
    counts=collections.Counter()
    for i,ch in enumerate(sequence):
        if ch=='?':continue
        addr=base+64*i
        h=((addr>>6)&4095)^((addr>>18)&4095)^((addr>>30)&4095)^((addr>>42)&1023)
        folded=(h&63)
        for j in range(6): folded|=(((h>>(11-j))^(h>>j))&1)<<(11-j)
        index=(folded*5)>>12
        expected=[88,216,344,160,288][index]
        assert expected==list(nodes)[int(ch)],(b,i)
        counts[expected]+=1
    hash_results.append({'boot':b,'classified':sum(counts.values()),'unused':sequence.count('?'),'node_counts':dict(counts)})

report={'digest':hashlib.sha256((root/'asimov-mesh-map.html').read_bytes()).hexdigest(),
 'verified_tables':['20 distance rows','4 fit rows','12 control rows','12 counter rows'],
 'verified_data_tooltips':checked_titles,'hash':hash_results,
 'max_printed_formula_error_ns':max(abs(best(1,k,c,n)-(20.6+2*steps(c,n)[0]+steps(c,n)[1])) for k in ['ocm-evict','slc'] for c,n in cells),
 'pair_max_cache_ns':max(abs(best(1,k,c,n)-best(1,k,c+1,n)) for k in ['ocm-evict','slc'] for c in [2,4,6,8] for n in nodes)}
for b in [1,2]:
    fits=[]
    for mx in range(6):
        for my in range(6):
            a=[]
            for c,n in cells:
                xy=[abs(cpus[c][i]-nodes[n][i])+abs(nodes[n][i]-[mx,my][i])+abs([mx,my][i]-cpus[c][i]) for i in [0,1]]
                a.append([1,*xy])
            if np.linalg.matrix_rank(a)==3:
                result=fit(a,[best(b,'dram-flush',c,n) for c,n in cells]);fits.append([result[-2],[mx,my],result[:3]])
    report[f'boot{b}_best_memory_fits']=sorted(fits,key=lambda t:(round(t[0],6),t[1]))[:4]
print(json.dumps(report,indent=2))
Path('/tmp/asimov-mesh-review-data.json').write_text(json.dumps(report,indent=2))
