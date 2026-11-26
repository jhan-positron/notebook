import json, sys, os, collections, datetime
R='/home/jhan/workspace/titan/cache-perf/crb/results'
files={'base':R+'/uefisettings-20261117/questions.json','revert':R+'/fwtest-20261117/revert/questions.json','x1post':R+'/fwtest-20261117/x1/post/questions.json'}
L={}
for k,p in files.items():
    q=json.load(open(p))
    L[k]=q
    st=os.stat(p)
    print(k, p, 'entries', len(q), 'mtime UTC', datetime.datetime.utcfromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S'))
    kinds=collections.Counter()
    types=collections.Counter()
    for e in q:
        a=e.get('answer')
        types[type(a).__name__]+=1
        if isinstance(a,str) and a.startswith('<'):
            kinds[a.split(':')[0]]+=1
        else:
            kinds['readable']+=1
    print('  kinds', dict(kinds), 'answer types', dict(types))
    # distinct forms of answers starting with '<'
    forms=collections.Counter(a['answer'] for a in q if isinstance(a['answer'],str) and a['answer'].startswith('<'))
    for f,c in forms.items(): print('   ',c,repr(f))
    # keys
    print('  keys', collections.Counter(tuple(sorted(e.keys())) for e in q))
    for n in ('DIMM Frequency','TXREQ Max','TXREQ Min'):
        print('  ',n,[e['answer'] for e in q if e['name']==n])
    # other odd readable answers: empty etc
    rd=[e for e in q if not (isinstance(e['answer'],str) and e['answer'].startswith('<'))]
    print('  readable empties', sum(1 for e in rd if e['answer'] in ('',None)), 'sample', [ (e['name'],e['answer']) for e in rd[:5]])
# compare base and revert as multisets
def key(e): return json.dumps(e,sort_keys=True)
cb=collections.Counter(map(key,L['base'])); cr=collections.Counter(map(key,L['revert'])); cx=collections.Counter(map(key,L['x1post']))
print('base==revert multiset', cb==cr, 'same order', L['base']==L['revert'])
print('base vs x1post diff', [json.loads(k)['name']+'='+str(json.loads(k)['answer']) for k in (cb-cx)], [json.loads(k)['name']+'='+str(json.loads(k)['answer']) for k in (cx-cb)])
# readable subset equality
def rdset(q): return collections.Counter(key(e) for e in q if not (isinstance(e['answer'],str) and e['answer'].startswith('<')))
print('readable multiset equal base/revert', rdset(L['base'])==rdset(L['revert']), sum(rdset(L['base']).values()))
# VStoreError entries
for e in L['base']:
    if isinstance(e['answer'],str) and e['answer'].startswith('<VStore'): print('  VS', e['name'], '|', e['answer'])
