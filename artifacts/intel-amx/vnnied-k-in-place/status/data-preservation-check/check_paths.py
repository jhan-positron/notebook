import re, os, sys, json, html, collections
PAGE='/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/mirror-vs-VNNI-K.html'
NB='/home/jhan/workspace/notebook/artifacts'
s=open(PAGE,encoding='utf-8').read()
s=re.sub(r'<script.*?</script>','',s,flags=re.S); s=re.sub(r'<style.*?</style>','',s,flags=re.S)
s=re.sub(r'<(br|/p|/h[1-6]|/li|/tr|/div)[^>]*>','\n',s); s=re.sub(r'</t[dh]>',' | ',s); s=re.sub(r'<[^>]+>','',s); s=html.unescape(s)
lines=[l.strip() for l in s.split('\n') if l.strip()]
# walk "Raw data by row key" sections: a row key line (R\d+|C\d+ ...) followed by path lines
rowkey=re.compile(r'^(R\d+|C\d+) ')
cur=None; cited=collections.OrderedDict(); rows_seen=[]
in_raw=False
for l in lines:
    if l=='Raw data by row key': in_raw=True; continue
    if l.startswith('Notes on the data'): in_raw=False
    if not in_raw: continue
    m=rowkey.match(l)
    if m: cur=m.group(1); rows_seen.append(cur); continue
    if l.startswith('/home/'):
        # strip trailing annotations after a space or ' ('
        p=l.split(' ')[0]
        # brace expansion form: dir/{a,b,c}
        mb=re.match(r'^(.*)/\{([^}]*)\}$',p)
        paths=[]
        if mb:
            for x in mb.group(2).split(','): paths.append(mb.group(1)+'/'+x.strip())
        else: paths=[p]
        for p in paths:
            cited.setdefault(p,set()).add(cur)
def nb_path(p):
    # map local absolute path to notebook artifact path (case-insensitive dir names tried)
    cands=[]
    if p.startswith('/home/jhan/workspace/intel-AMX/'):
        rel=p[len('/home/jhan/workspace/intel-AMX/'):]
        parts=rel.split('/')
        top=parts[0]
        for t in (top, top.lower()):
            cands.append(os.path.join(NB,'intel-amx',t,*parts[1:]))
        # exec/results/... also may be preserved elsewhere
    elif p.startswith('/home/jhan/workspace/ai-runs/systems_test/'):
        rel=p[len('/home/jhan/workspace/ai-runs/systems_test/'):]
        cands.append(os.path.join(NB,'tron','systems_test',rel)); cands.append(os.path.join(NB,'systems_test',rel))
    for c in cands:
        if os.path.exists(c): return c
    return None
# also search the notebook by basename+parent as a fallback (report separately)
nb_index=collections.defaultdict(list)
for root,dirs,files in os.walk(NB):
    for f in files: nb_index[f].append(os.path.join(root,f))
out=[]
for p,keys in cited.items():
    local=os.path.exists(p)
    nb=nb_path(p)
    base=os.path.basename(p)
    parent=os.path.basename(os.path.dirname(p))
    fuzzy=[x for x in nb_index.get(base,[]) if os.path.basename(os.path.dirname(x))==parent] if nb is None else []
    out.append(dict(path=p,rows=sorted(keys,key=lambda k:(k[0],int(k[1:]))),local=local,notebook=nb,fuzzy=fuzzy))
json.dump(out,open(sys.argv[1],'w'),indent=1)
# summary
tot=len(out); loc=sum(1 for o in out if o['local']); nb=sum(1 for o in out if o['notebook']); fz=sum(1 for o in out if not o['notebook'] and o['fuzzy'])
print(f'row keys seen: {len(rows_seen)} ({rows_seen[0]}..{rows_seen[-1]})')
print(f'distinct cited paths: {tot}; exist locally: {loc}; exist in notebook (mapped): {nb}; fuzzy basename+parent hit only: {fz}')
# per row-key coverage
byrow=collections.defaultdict(lambda: [0,0,0])
for o in out:
    for k in o['rows']:
        byrow[k][0]+=1; byrow[k][1]+=o['local']; byrow[k][2]+=bool(o['notebook'])
print('rowkey cited local notebook')
for k in sorted(byrow,key=lambda k:(k[0],int(k[1:]))): print(k,*byrow[k])
# group missing-from-notebook by top dir
miss=collections.Counter()
for o in out:
    if not o['notebook']:
        parts=o['path'].split('/'); miss['/'.join(parts[:7])]+=1
print('--- not in notebook, grouped by dir prefix ---')
for k,v in miss.most_common(): print(v,k)
print('--- not local ---')
for o in out:
    if not o['local']: print(o['path'], o['rows'])
