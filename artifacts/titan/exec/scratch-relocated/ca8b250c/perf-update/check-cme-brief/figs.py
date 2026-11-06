import re,html
R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
D={'E':R+'membench-jibin-010/results/bootE/','R3':R+'membench-jibin-004/results/19700101T000000Z/','B':R+'membench-jibin-006/results/bootB/'}
def rows(path):
    out=[]; hdr=None
    for ln in open(path):
        ln=ln.strip()
        if not ln or ln.startswith('#'): continue
        f=ln.split(',')
        if f[0]=='mem': hdr=f; continue
        out.append(dict(zip(hdr,f)))
    return out
def lat(boot,prefix):
    d={}
    for fn in ('dram-small','dram-large'):
        for r in rows(D[boot]+f'{prefix}latency-{fn}.csv'):
            if r['mode'] in ('best','cme-best'): d[int(r['size_bytes'])]=float(r['ns_per_load'])
    return d
def bw(boot,fn,k):
    return {int(r['bytes_per_thread']):float(r['aggregate_GBps']) for r in rows(D[boot]+fn) if r['kernel']==k and r['rep']=='best'}
def sz(s):
    n=float(s.split()[0]); return int(n*(1024*1024 if 'MiB' in s else 1024))
s=open('/home/jhan/workspace/titan/cache-perf/asimov/asimov-cme-perf-brief.html').read()
titles=re.findall(r'<title>(.*?)</title>',s)
series={'C1-Nano core, CPU 2, boot E ':lat('E',''),'CME ':None,'through the CME, run 3 (L3 off) ':lat('R3','cme-'),'through the CME, boot B (CME prefetcher off) ':lat('B','cme-'),
 'core read (run 3, L3 off) ':bw('R3','bandwidth-dram-1core.csv','read'),'CME read (run 3, L3 off) ':bw('R3','cme-bandwidth-dram-1core.csv','cme-read'),
 'core write (run 3, L3 off) ':bw('R3','bandwidth-dram-1core.csv','write'),'CME write (run 3, L3 off) ':bw('R3','cme-bandwidth-dram-1core.csv','cme-write')}
cmeE=lat('E','cme-')
n=0; miss=0
for t in titles[1:]:
    t=html.unescape(t)
    m=re.match(r'CME (\d+(?:\.\d+)? [KM]iB), boot E: ([\d.]+) ns',t)
    if m:
        v=cmeE[sz(m.group(1))]; n+=1
        if abs(v-float(m.group(2)))>0.0005: miss+=1; print('MISS',t,v)
        continue
    for pre,d in series.items():
        if d and t.startswith(pre):
            size,val=t[len(pre):].split(': '); v=d[sz(size)]; n+=1
            if abs(v-float(val))>0.0005: miss+=1; print('MISS',t,v)
            break
    else: print('unmatched',t)
print('figure values checked',n,'miss',miss)
