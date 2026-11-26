import json,csv,re
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/proxy-examples-2026-11-12/'
js=open('a780.txt').read()
M10=json.loads(re.search(r'M10 = (\{.*?\})',js).group(1))
pp=json.load(open(S+'proxyfit/proxy-positions.json'))
print(pp.keys())
for k,v in pp.items():
    if k!='method': print(k, str(v)[:400])
cp=json.load(open(R+'core-positions.json'))
print([k for k in cp])
def show(o,d=0):
    if isinstance(o,dict):
        for k,v in list(o.items())[:6]: print(' '*d,k,str(v)[:200])
show(cp)
nodes={ (r['mesh'],r['node_id_hex']):(r['x'],r['y']) for r in csv.DictReader(open(R+'full/nodes.csv'))}
for k in [('0','0x128'),('1','0x290'),('1','0x390'),('0','0x288'),('1','0xa0')]: print(k,nodes.get(k))
lat=list(csv.DictReader(open(R+'full/latency.csv')))
for core,mesh,nid in [('0','0','0x128'),('0','1','0x290'),('0','1','0x390'),('64','0','0x128')]:
    print(core,mesh,nid,[ (r['ns_median'],r['lines']) for r in lat if r['core']==core and r['mesh']==mesh and r['node_id_hex']==nid])
# 779: lowest other-mesh cell for CPU 0
o=[(float(r['ns_median']),r['x'],r['y'],r['node_id_hex']) for r in lat if r['core']=='0' and r['mesh']=='1']
print(sorted(o)[:4])
print(len(set(r['core'] for r in lat)))
h=[l.split(',') for l in open(R+'full/homes.csv').read().split()[1:]]
print(h[0],h[1],h[98304])
ch=list(csv.DictReader(open(R+'full/chunks.csv'))); print(ch[0],ch[3])
print((0x21dd7e00000-0x211c3c00000)/2**30)
