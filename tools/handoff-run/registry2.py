import os,re,json,glob,subprocess,sys
NB='/home/jhan/workspace/notebook'; LOCAL={'claude-agentsrv','agentsrv','claude-box'}
WS='/home/jhan/workspace/intel-AMX'
REMAP={'pr3879/':'PR3879/','vnnied-k-in-place/':'VNNIed-K-in-place/','amx-decode-boost-202608/':'exec/results/'}
def layout_candidates(topic,rel):
    if topic!='intel-amx': return []
    c=[f'{WS}/{rel}']
    for a,b in REMAP.items():
        if rel.startswith(a): c.append(f'{WS}/{b}{rel[len(a):]}')
    return c
def strip_comment(a):
    return re.sub(rb'^\s*<!--.*?-->\s*',b'',a,count=1,flags=re.S)
out=[]; remote=[]
for readme in sorted(glob.glob(f'{NB}/artifacts/*/README.md')):
    topic=os.path.basename(os.path.dirname(readme)); tdir=os.path.dirname(readme)
    lines=open(readme,encoding='utf-8',errors='replace').read().split('\n')
    wsdef={}
    for l in lines:
        for m in re.finditer(r'`?\b(WS|ROOT)\b`?\s*=\s*`?([\w.-]+:/[^\s`)]+)', l): wsdef[m.group(1)]=m.group(2).rstrip('/')
    for p in sorted(x for x in glob.glob(f'{tdir}/**/*',recursive=True) if os.path.isfile(x) and not x.endswith('README.md')):
        rel=os.path.relpath(p,tdir); base=os.path.basename(p)
        rec=dict(topic=topic,repo=os.path.relpath(p,NB),canon_host=None,canon_path=None,status=None,how=None)
        canon=None
        # 1) layout rule (intel-amx)
        for cand in layout_candidates(topic,rel):
            if os.path.isfile(cand): canon=('claude-agentsrv',cand); rec['how']='layout'; break
        # 2) README line containing the exact rel path (or a parent dir token) with a canonical token whose basename matches
        if not canon:
            for i,l in enumerate(lines):
                if rel in l or (('/'+rel.split('/')[0]+'/') in l and '/' in rel):
                    blk='\n'.join(lines[i:i+6])
                    for m in re.finditer(r'([\w.-]+):((?:/|[A-Z]:/)[^\s`)|,]+)', blk):
                        h,cp=m.group(1),m.group(2)
                        if h in ('https','http'): continue
                        if os.path.basename(cp)==base: canon=(h,cp); rec['how']='readme-exact'; break
                        if cp.endswith('/') or (h in LOCAL and os.path.isdir(cp)):
                            # directory entry: append suffix after the repo dir token found in blk
                            for tok in re.findall(r'`([\w./-]+/)`', blk):
                                if rel.startswith(tok): canon=(h,cp.rstrip('/')+'/'+rel[len(tok):]); rec['how']='readme-dir'; break
                            if canon: break
                    if not canon:
                        for w in re.finditer(r'\b(WS|ROOT)/([^\s`)|,]+)', blk):
                            if w.group(1) in wsdef:
                                h,b=wsdef[w.group(1)].split(':',1); cp=b+'/'+w.group(2)
                                if os.path.basename(cp)==base: canon=(h,cp); rec['how']='readme-ws'; break
                    if canon: break
        if not canon: rec['status']='unmapped'; out.append(rec); continue
        rec['canon_host'],rec['canon_path']=canon
        if canon[0] in LOCAL:
            cp=canon[1]
            if not os.path.isfile(cp): rec['status']='canonical-missing'
            else:
                a=open(p,'rb').read(); b=open(cp,'rb').read()
                same = a==b or (p.endswith('.html') and strip_comment(a)==b)
                rec['status']='identical' if same else 'different'
                if not same: rec['sizes']=(len(a),len(b)); rec['mtimes']=(int(os.path.getmtime(p)),int(os.path.getmtime(cp)))
        elif canon[0]=='delphi-3bda': rec['status']='remote-3bda'; remote.append(rec)
        else: rec['status']='unreachable-host'
        out.append(rec)
# batch md5 on delphi-3bda (light): compare
if remote:
    paths=[r['canon_path'] for r in remote]
    try:
        res=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','delphi-3bda','bash','-c',"'for f in \"$@\"; do if [ -f \"$f\" ]; then md5sum \"$f\"; else echo \"MISSING  $f\"; fi; done' _ "+' '.join(f'"{p}"' for p in paths)],capture_output=True,text=True,timeout=120)
        m={}
        for l in res.stdout.splitlines():
            parts=l.split(None,1)
            if len(parts)==2: m[parts[1].strip()]=parts[0]
        import hashlib
        for r in remote:
            h=m.get(r['canon_path'])
            if h is None: r['status']='remote-3bda-unknown'
            elif h=='MISSING': r['status']='canonical-missing'
            else:
                a=open(f"{NB}/{r['repo']}",'rb').read()
                la=hashlib.md5(a).hexdigest(); lb=hashlib.md5(strip_comment(a)).hexdigest() if r['repo'].endswith('.html') else la
                r['status']='identical' if h in (la,lb) else 'different'
    except Exception as e:
        print("ssh batch failed:",e)
json.dump(out,open(sys.argv[1],'w'),indent=1)
from collections import Counter
print("files:",len(out)); print(Counter(r['status'] for r in out)); print("mapping method:",Counter(r['how'] for r in out if r['how']))
print("\n-- DIFFERENT:"); [print('  ',r['repo'],'<-',f"{r['canon_host']}:{r['canon_path']}",r.get('sizes'),r['how']) for r in out if r['status']=='different']
print("\n-- CANONICAL MISSING:"); [print('  ',r['repo'],'<-',f"{r['canon_host']}:{r['canon_path']}",r['how']) for r in out if r['status']=='canonical-missing']
print("\n-- UNMAPPED by topic/dir:"); um=Counter(r['repo'].rsplit('/',1)[0] for r in out if r['status']=='unmapped'); [print(f'   {k}: {v}') for k,v in sorted(um.items())]
