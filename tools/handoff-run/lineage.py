import json,ast,re,os,glob,sys,collections
WS='/home/jhan/workspace/intel-AMX'; NB='/home/jhan/workspace/notebook'
ROWS=f'{WS}/exec/results/vnnik-20260914/mirror-vs-vnni-rows.json'
d=json.load(open(ROWS)); rows=d['rows']
MEAS=re.compile(r'prefill|decode|tok/s|ttft|average|parsing|tps|samples|rep \d|reps?\b|generat|power|pkgwatt|watt|ramwatt|per-request|request',re.I)
IDENT=re.compile(r'header|placement|binary|sha256|version|numa|fpga|commit|footprint|mirror size|settings|config|cores|model path|build',re.I)
cites=collections.defaultdict(list)  # path -> list of (lines, desc, source_id, row_idx)
unexpanded=[]
def _emit(paths,lines,desc,r,ri):
    sib=re.search(r'and (?:the )?(?:__)?rep(\d)\s*[-–]\s*(?:rep)?(\d)',desc)
    extra=[]
    for p in paths:
        if sib:
            a,b=int(sib.group(1)),int(sib.group(2))
            for k in range(a,b+1):
                q=re.sub(r'rep\d',f'rep{k}',p)
                if q!=p and os.path.exists(q): extra.append(q)
        for m2 in re.finditer(r'(__rep\d)',desc):
            q=re.sub(r'__rep\d',m2.group(1),p)
            if q!=p and os.path.exists(q): extra.append(q)
    for p in paths+extra: cites[p].append((lines,desc,r.get('source_id'),ri))
def expand(path):
    m=re.search(r'\{([^{}]+)\}',path)
    if not m: return [path]
    out=[]
    for alt in m.group(1).split(','):
        out+=expand(path[:m.start()]+alt.strip()+path[m.end():])
    return out
for ri,r in enumerate(rows):
    sf=r.get('source_files')
    try: lst=ast.literal_eval(sf) if isinstance(sf,str) else (sf or [])
    except Exception: lst=[s.strip(" '") for s in sf.strip('[]').split("', '")]
    for ent in lst:
        ent=ent.strip()
        dm=re.match(r'^(.*?)(?:\s+\((.*)\))?$',ent,re.S); body,desc=dm.group(1),dm.group(2) or ''
        specs=[]
        for b2 in expand(body):
            specs+=re.findall(r'(\S+?\.(?:log|txt|json|md|xml|out|csv|py|sh|js|hpp|cpp|patch))(?::(\S+))?',b2)
        if not specs: unexpanded.append((ri,ent)); continue
        basedir=None
        for path,lines in specs:
            if not path.startswith('/'):
                path = f'{basedir}/{path}' if basedir and '/' not in path else f'{WS}/{path}'
            basedir=os.path.dirname(path)
            lines=re.sub(r'\([^)]*\)','',lines or '') or None
            paths=expand(path)
            _emit(paths,lines,desc,r,ri)
        continue
        paths=[]
print("distinct cited files:",len(cites),"| unparsed entries:",len(unexpanded))
for u in unexpanded[:5]: print("  unparsed:",u)
# classify
def cls(p):
    b=os.path.basename(p); dn=os.path.dirname(p)
    if b=='rinzler.log' or b.startswith('rinzler'): return 'server-log'
    if re.match(r'perf.*\.log$',b): return 'ci-client-log'
    if re.match(r'perf.*\.json$',b): return 'compact-perf-json'
    if b in ('rt-results.txt',) or re.match(r'perf-round.*\.txt$',b) or (b.endswith('.txt') and '/rt/' not in p and not re.search(r'power\d*\.txt|cap\d*\.txt',b) and 'results' in p and b not in ('summary.txt','build.txt','tests.txt','fence.txt','ctxfill.txt')): return 'compact-text'
    if b in ('summary.json','summary.md','summary.txt','build.txt','meta.json','proof.txt','tests.txt','smoke.txt') or re.match(r't4-power\.txt|power_capture.*',b): return 'small-record'
    if b.startswith('ci-run-'): return 'campaign-log'
    if b.endswith('.log') and (re.search(r'rep\d',b) or '/rt/' in p or re.match(r'(cap|power|run-)',b)): return 'per-rep-log'
    if b.endswith('.log'): return 'per-rep-log'
    if b.endswith('.md') or b.endswith('.html'): return 'notes'
    if b.endswith('.xml'): return 'xml'
    if b.endswith('.done') or '/logs/' in p: return 'campaign-log'
    if b.endswith('.json'): return 'small-record'
    return 'other'
def repo_path(p):
    rel=os.path.relpath(p,WS)
    cands=[f'{NB}/artifacts/intel-amx/{rel}']
    if rel.startswith('exec/results/'): cands.append(f'{NB}/artifacts/intel-amx/amx-decode-boost-202608/{rel[len("exec/results/"):]}')
    if rel.startswith('PR3879/'): cands.append(f'{NB}/artifacts/intel-amx/pr3879/{rel[len("PR3879/"):]}')
    for c in cands:
        if os.path.isfile(c): return c
    return None
def measured_lines(p,lines):
    """lines from a per-rep log that carry the page's numbers: runtron 'average tok/s' and 'Parsing the prompt took'"""
    try: L=open(p,errors='replace').read().split('\n')
    except Exception: return []
    sel=[]
    if lines:
        for part in lines.split(','):
            if '-' in part: a,b=part.split('-'); sel+=L[int(a)-1:int(b)]
            elif part.isdigit(): sel.append(L[int(part)-1] if int(part)-1<len(L) else '')
    else: sel=L
    out=[]
    for l in sel:
        if re.search(r'average tok/s|Parsing the prompt took',l):
            i=l.find('[Request'); out.append(l[i:] if i>=0 else l.strip())
    return out
files=[]
for p,cl in cites.items():
    exists=os.path.exists(p); size=os.path.getsize(p) if exists else None
    STRONG=re.compile(r'prefill|decode|tok/s|tokens/s|ttft|average|parsing|\btps\b|pkgwatt|ramwatt|watt|samples|last line|mmlu|score|per-request',re.I)
    MEASLINE=re.compile(r'Parsing the prompt took|average tok/s|tok/s|tokens/s|TTFT|PkgWatt|RAMWatt|tps_results|ttfts|"tps"|accuracy|score',re.I)
    def cited_content(path,lines):
        if not lines: return None
        try: L=open(path,errors='replace').read().split('\n')
        except Exception: return None
        sel=[]
        for part in lines.split(','):
            part=part.strip()
            if not part: continue
            if '-' in part:
                a,b=part.split('-')[:2]
                if a.isdigit() and b.isdigit(): sel+=L[int(a)-1:int(b)]
            elif part.isdigit() and int(part)-1<len(L): sel.append(L[int(part)-1])
        return sel
    def used(lines,desc):
        if STRONG.search(desc): return True
        if IDENT.search(desc) and not STRONG.search(desc): return False
        sel=cited_content(p,lines)
        if sel is None: return False          # bare path, no wording: no evidence of a value
        return any(MEASLINE.search(l) for l in sel)
    measured=any(used(l,desc) for l,desc,_,_ in cl)
    ident_only=not measured
    c=cls(p); rp=repo_path(p)
    decision=None; note=''
    if not exists: decision='left behind (missing on 2026-09-20)'
    elif '/ai-runs/' in p or '/tron-VNNIed-K/' in p: decision='left behind (in git)'
    elif rp and open(rp,'rb').read()==open(p,'rb').read(): decision=f'duplicate ({os.path.relpath(rp,NB)})'
    elif size>5*1024*1024: decision='left behind (size)'
    elif c=='server-log':
        decision='proposed (override: measured lines)' if measured else 'left behind (provenance)'
    elif c=='ci-client-log':
        cell=os.path.dirname(p); pj=glob.glob(cell+'/perf*.json')
        decision=('proposed (override: measured lines)' if measured and not pj else 'left behind (provenance)'); note=f'{len(pj)} perf*.json beside'
    elif c=='per-rep-log':
        # duplicate if the measured lines cited are held by a compact text in the same result tree
        tree=p.split('/rt/')[0] if '/rt/' in p else os.path.dirname(p)
        compact=[x for x in glob.glob(tree+'/*.txt') if cls(x)=='compact-text']
        ml=[]; 
        for lines,desc,_,_ in cl: ml+=measured_lines(p,lines)
        ml=list(dict.fromkeys(ml))
        held=None
        for ct in compact:
            T=open(ct,errors='replace').read()
            if ml and all(l.strip() in T for l in ml): held=ct; break
        if ml and held: decision=f'duplicate (held by {os.path.relpath(held,WS)})'; note=f'{len(ml)} measured lines checked'
        elif measured: decision='proposed (override: measured lines not held by a compact text)'; note=f'{len(ml)} measured lines; compact texts: {[os.path.basename(x) for x in compact]}'
        else: decision='left behind (provenance)'
    elif c in ('compact-text','compact-perf-json','small-record'): decision='proposed'
    elif c=='notes': decision='proposed' if measured else 'left behind (no value used)'
    elif c in ('xml','campaign-log'): decision='left behind (provenance)'
    elif c=='notes' and not measured: decision='left behind (no value used)'
    else: decision='proposed' if measured else 'left behind (no value used)'
    files.append(dict(path=p,cls=c,size=size,measured=measured,decision=decision,note=note,n_cites=len(cl),sample_desc=cl[0][1][:90]))
# adjacency: small records beside proposed measured files
prop_dirs={os.path.dirname(f['path']) for f in files if f['decision'].startswith('proposed') and f['cls'] in ('compact-text','compact-perf-json')}
adj=[]
for dn in sorted(prop_dirs):
    for b in ('summary.json','summary.md','summary.txt','build.txt','meta.json','proof.txt','tests.txt'):
        q=f'{dn}/{b}'
        if os.path.isfile(q) and q not in cites:
            rp=repo_path(q); dec=f'duplicate ({os.path.relpath(rp,NB)})' if rp and open(rp,'rb').read()==open(q,'rb').read() else 'proposed (adjacent record)'
            adj.append(dict(path=q,cls='small-record',size=os.path.getsize(q),measured=False,decision=dec,note='adjacency',n_cites=0,sample_desc=''))
files+=adj
# input + builder
inp=dict(path=ROWS,cls='input',size=os.path.getsize(ROWS),measured=True,decision='proposed (input)',note='',n_cites=0,sample_desc='')
wf=glob.glob(os.path.expanduser('~/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/*/workflows/scripts/pull-mirror-vs-vnni-data-*.js'))
files=[inp]+files
json.dump(dict(files=files,workflow_script=wf),open(sys.argv[1],'w'),indent=1)
C=collections.Counter(re.sub(r' \(.*','',f['decision']) if not f['decision'].startswith('duplicate (held') else 'duplicate (held by compact text)' for f in files)
print("\n== decisions =="); [print(f"  {k}: {v}") for k,v in C.most_common()]
prop=[f for f in files if f['decision'].startswith('proposed')]
print(f"\n== PROPOSED: {len(prop)} files, {sum(f['size'] for f in prop)/1048576:.2f} MiB ==")
bytree=collections.defaultdict(lambda:[0,0])
for f in prop:
    t=os.path.relpath(f['path'],WS).split('/')[:3]; k='/'.join(t[:3]) if t[0]=='exec' else '/'.join(t[:2]); bytree[k][0]+=1; bytree[k][1]+=f['size']
for k,(n,b) in sorted(bytree.items()): print(f"  {k}: {n} files, {b/1024:.0f} KiB")
print("\n== overrides (proposed by measured-line citation despite class) =="); [print(f"  {os.path.relpath(f['path'],WS)} {f['size']} B | {f['note']} | e.g. {f['sample_desc']}") for f in files if 'override' in f['decision']]
print("\n== per-rep logs not held (would be proposed) =="); [print(f"  {os.path.relpath(f['path'],WS)} | {f['note']}") for f in files if f['cls']=='per-rep-log' and f['decision'].startswith('proposed')][:15]
print("\n== left behind by reason (count, MiB) =="); 
lb=collections.defaultdict(lambda:[0,0])
for f in files:
    if f['decision'].startswith('left behind') or f['decision'].startswith('duplicate'): lb[re.sub(r'\(.*','',f['decision']).strip()+(' held' if 'held by' in f['decision'] else ' repo' if f['decision'].startswith('duplicate') else '')][0]+=1; lb[re.sub(r'\(.*','',f['decision']).strip()+(' held' if 'held by' in f['decision'] else ' repo' if f['decision'].startswith('duplicate') else '')][1]+=(f['size'] or 0)
for k,(n,b) in sorted(lb.items()): print(f"  {k}: {n} files, {b/1048576:.2f} MiB")
print("\n== class x decision (top) =="); CC=collections.Counter((f['cls'],re.sub(r' \(.*','',f['decision'])) for f in files); [print(f"  {k[0]:<18} {k[1]:<22} {v}") for k,v in CC.most_common(30)]
print("\nworkflow script:",wf)
