import re,sys
from html.parser import HTMLParser
t=open(sys.argv[1],encoding='utf-8').read()
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.stack=[]; s.items=[]; s.inmain=False
    def handle_starttag(s,tag,attrs):
        if tag in ('br','meta','link','img','col','hr','SVG','svg'): 
            return
        a=dict(attrs); s.stack.append((tag,a.get('class',''),a.get('id','')))
    def handle_startendtag(s,tag,attrs): pass
    def handle_endtag(s,tag):
        for i in range(len(s.stack)-1,-1,-1):
            if s.stack[i][0]==tag: del s.stack[i:]; break
    def handle_data(s,d):
        if not d.strip(): return
        s.items.append((tuple(s.stack),d))
p=P(); p.feed(t)
import collections
cat=collections.Counter(); samples=collections.defaultdict(list)
def classify(stack):
    tags=[x[0] for x in stack]; cls=[x[1] for x in stack]; ids=[x[2] for x in stack]
    if 'main' not in tags: return 'outside-main'
    if 'table' in tags: return 'table'
    if 'details' in tags: return 'details(word list / table views)'
    if 'figcaption' in tags: return 'figcaption'
    if any(c.startswith('tcap') for c in cls): return 'table caption'
    if any('hint' in c for c in cls): return 'hint'
    if any(c=='legend' for c in cls): return 'legend'
    if any(c=='how' for c in cls): return 'reading notes under figure (ul.how)'
    if 'ol' in tags and 'refs' in cls: return 'references list'
    if any(c=='note' for c in cls): return 'p.note'
    if tags[-1] in ('h1','h2','h3') or 'h1' in tags or 'h2' in tags or 'h3' in tags: return 'heading'
    if any(c=='short' for c in cls): return 'PROSE short version box'
    if any(c=='more' for c in cls): return 'PROSE p.more'
    if any(c=='sub' for c in cls): return 'PROSE dateline (p.sub)'
    return 'PROSE '+'>'.join(f"{a}.{b}" if b else a for a,b,c in stack[stack.index(next(x for x in stack if x[0]=='main'))+1:][:2])
def nwords(s):
    s=re.sub(r'\[Ref\d+\]','',s)
    return len(re.findall(r"\S+",s))
for st,d in p.items:
    k=classify(st); cat[k]+=nwords(d); 
    if len(samples[k])<3: samples[k].append(d.strip()[:70])
tot=0
for k,v in sorted(cat.items()):
    print(f"{v:6d}  {k}   e.g. {samples[k][:2]}")
    if k.startswith('PROSE'): tot+=v
print('PROSE total',tot)
