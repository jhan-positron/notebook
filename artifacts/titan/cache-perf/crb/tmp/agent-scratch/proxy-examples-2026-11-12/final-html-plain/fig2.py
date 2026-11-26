import json,re
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/proxy-examples-2026-11-12/'
js=open('a780.txt').read()
M10=json.loads(re.search(r'M10 = (\{.*?\})',js).group(1))
pp=json.load(open(S+'proxyfit/proxy-positions.json'))
cp=json.load(open(R+'core-positions.json'))
print('cpu0',cp['pos']['0'],'\ncpu64',cp['pos']['64'])
bad=0;n=0
for e in pp['per_xp']:
    if e['reader_mesh']==0 and e['home_mesh']==1:
        n+=1; k='%d,%d'%tuple(e['home_xp']); v='%d,%d'%tuple(e['best'])
        if M10.get(k)!=v or e['ambiguous']: bad+=1; print('diff',k,v,M10.get(k),e['ambiguous'])
print('m0 readers of mesh1 homes',n,'bad',bad,len(M10), 'injective',len(set(M10.values())))
M01={v:k for k,v in M10.items()}
agree=amb=0
for e in pp['per_xp']:
    if e['reader_mesh']==1 and e['home_mesh']==0:
        k='%d,%d'%tuple(e['home_xp']); ties=['%d,%d'%tuple(t) for t in e['ties']]
        if len(ties)==1 and ties[0]==M01[k]: agree+=1
        else: amb+=1; print(k,'map',M01[k],'ties',ties,e['best'],e['ambiguous'])
print(agree,amb)
