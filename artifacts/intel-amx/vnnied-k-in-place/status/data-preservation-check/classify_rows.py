import json, os, re, collections
NB='/home/jhan/workspace/notebook/artifacts'
d=json.load(open(os.environ['SP']+'/cited_paths.json'))
RELOC={'/home/jhan/workspace/intel-AMX/exec/results/':NB+'/intel-amx/amx-decode-boost-202608/'}
def in_nb(p):
    o=next(x for x in d if x['path']==p)
    if o['notebook']: return o['notebook']
    for k,v in RELOC.items():
        if p.startswith(k):
            c=v+p[len(k):]
            if os.path.exists(c): return c
    return None
# numeric source = a file under exec/results (or PR3879/more-testing status) that is not a script/log marker
def is_numeric_source(p):
    if '/exec/results/' not in p: return False
    b=os.path.basename(p)
    if b in ('build.txt','platformd-instance-1.env.txt','notes.md','proof.txt','rinzler-amx-lines.txt','functional.xml','meta.json','rinzler.log'): return False
    if b.startswith('power') and b.endswith('.log'): return False
    if b.startswith('run-f') and b.endswith('.log'): return False  # perfstat footprint lines only
    if b=='cell.log': return False
    return True
rows=collections.defaultdict(lambda: dict(num=[],num_nb=[],scripts=[],scripts_nb=[],other=[],other_nb=[]))
for o in d:
    p=o['path']; nb=in_nb(p)
    for k in o['rows']:
        cls='num' if is_numeric_source(p) else ('scripts' if p.endswith(('.sh','.py')) else 'other')
        rows[k][cls].append(p)
        if nb: rows[k][cls+'_nb'].append(p)
def key(k): return (k[0],int(k[1:]))
print('key  numeric_sources  in_notebook  status  | missing numeric sources (dir/file)')
status=collections.Counter()
for k in sorted(rows,key=key):
    r=rows[k]; n=len(r['num']); m=len(r['num_nb'])
    st='FULL' if n and m==n else ('PARTIAL' if m else 'NONE')
    status[(k[0],st)]+=1
    miss=sorted(set('/'.join(p.split('/')[-2:]) if '/rt/' in p or '/cells/' in p else '/'.join(p.split('/')[6:]) for p in r['num'] if p not in r['num_nb']))
    # compress rep/cell lists
    short=[]
    for x in miss:
        if re.search(r'__rep\d|__u\d|cells/|rt/',x): 
            short.append(x.split('/')[0]+'/…') if x.split('/')[0]+'/…' not in short else None
        else: short.append(x)
    print(f'{k:4s} {n:3d} {m:3d}  {st:7s} | '+', '.join(short))
print(dict(status))
json.dump({k:dict(numeric=rows[k]['num'],numeric_in_notebook=rows[k]['num_nb']) for k in rows},open(os.environ['SP']+'/row_status.json','w'),indent=1)
