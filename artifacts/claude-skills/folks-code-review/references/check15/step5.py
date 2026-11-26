import re, sys, subprocess
WT, HEAD, prose = sys.argv[1:4]
from spellchecker import SpellChecker
sp=SpellChecker()
def git(*a): return subprocess.run(['git','-C',WT,*a],capture_output=True,text=True).stdout
toks={}
for line in open(prose, encoding='utf-8', errors='replace'):
    loc,_,rest=line.rstrip('\n').partition('\t'); kind,_,text=rest.partition('\t')
    if kind not in 'CM': continue
    text=re.sub(r'`[^`]*`',' ',text)
    for t in re.findall(r'\b[A-Za-z]+(?:_[A-Za-z0-9]+)+\b|\b[A-Z]{2,}[A-Z0-9_]+\b', text): toks.setdefault(t,loc)
base=set(p.rsplit('/',1)[-1].split('.')[0].lower() for p in git('ls-tree','-r','--name-only',HEAD).splitlines())
ids={}
for w in git('grep','-ohE',r'\b[A-Za-z_][A-Za-z0-9_]{2,}\b',HEAD,'--','h','src','t').split():
    ids[w]=ids.get(w,0)+1
def lev(a,b):
    if abs(len(a)-len(b))>1: return 3
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1): cur.append(min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]
def transposed(a,b):
    if len(a)!=len(b): return False
    d=[i for i in range(len(a)) if a[i]!=b[i]]
    return len(d)==2 and d[1]==d[0]+1 and a[d[0]]==b[d[1]] and a[d[1]]==b[d[0]]
for t,loc in sorted(toks.items()):
    lc=t.lower()
    if '_' not in t and not re.search(r'\d',t) and sp.known([lc]): continue
    if lc in base: continue
    n=sum(int(x.rsplit(':',1)[1]) for x in git('grep','-c','-i','-w','-E',f'{t}|{t.rstrip("s")}',HEAD).splitlines())
    if n>1: continue
    nb=[]
    for w,c in ids.items():
        wl=w.lower()
        if c<2 or wl==lc or wl.replace('_','')==lc.replace('_',''): continue
        if wl.startswith(lc) or lc.startswith(wl): continue
        if lev(lc,wl)==1 or transposed(lc,wl): nb.append((w,c))
    print(('FIND' if nb else 'cand'), t, loc, 'hits=%d'%n, 'neighbour=%s'%nb)
