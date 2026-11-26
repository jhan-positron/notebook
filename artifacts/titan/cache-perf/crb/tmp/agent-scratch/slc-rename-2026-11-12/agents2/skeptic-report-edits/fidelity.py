import re,html
S='/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc'
a=open(S+'/report.after-rename.before-fixes.html',encoding='utf-8').read().split('\n')
b=open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html',encoding='utf-8').read().split('\n')
def plain(s, drop_pre=True):
    if drop_pre:
        s=re.sub(r'<pre>.*?</pre>',' ',s,flags=re.S)
    # block boundaries -> sentence break marker
    s=re.sub(r'</(p|li|td|th|h3|tr)>','   ',s)
    s=re.sub(r'<[^>]+>','',s)
    s=html.unescape(s)
    s=re.sub(r'[ \t]+',' ',s)
    return s
old=' '.join(plain(a[i]) for i in (130,131,132))
new=' '.join(plain(b[i]) for i in (130,131,132))
def sents(t):
    out=[]
    for blk in t.split(' '):
        blk=blk.strip()
        if not blk: continue
        # split on ". " followed by capital or quote, keep citations with the sentence
        parts=re.split(r'(?<=[.:])\s+(?=[A-Z"“])',blk)
        out+= [p.strip() for p in parts if p.strip()]
    return out
so=sents(old); sn=sents(new)
newflat=re.sub(r'\s* \s*',' ',new)
newflat=re.sub(r'\s+',' ',newflat)
print('old sentences',len(so),'new units',len(sn))
k=0
for i,s in enumerate(so,1):
    s2=re.sub(r'\s+',' ',s)
    if s2 in newflat:
        k+=1
    else:
        print(f'[old {i}] NOT VERBATIM: {s2}')
print('verbatim',k,'of',len(so))
print()
print('---- new units not in old text')
oldflat=re.sub(r'\s* \s*',' ',old); oldflat=re.sub(r'\s+',' ',oldflat)
for i,s in enumerate(sn,1):
    s2=re.sub(r'\s+',' ',s)
    if s2 not in oldflat:
        print(f'[new {i}] {s2}')
# numbers
num=lambda t:sorted(set(re.findall(r'\d[\d,.]*\d|\d',t)))
no=num(oldflat); nn=num(newflat)
print('numbers only in old:',[x for x in no if x not in nn])
print('numbers only in new:',[x for x in nn if x not in no])
cit=lambda t:re.findall(r'\[[^\]]+\]',t)
print('old citations',cit(oldflat))
print('new citations',cit(newflat))
